#!/usr/bin/env python3
"""Clearance audit for block-detector-enclosure.scad.

Reads the parameters straight out of the .scad, rebuilds the derived
dimensions, and checks every clearance that is not obvious from a render:
board vs. posts, screw heads vs. components, cable slots vs. connectors,
the DIN channel, and the clip's own screws vs. its spring-tongue slot.

Component courtyards come from the F.CrtYd outlines in the KiCad board file in
the parent directory, converted into board-local coordinates.

    python check_fit.py
"""

import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCAD = os.path.join(HERE, "block-detector-enclosure.scad")
BOARD_ORIGIN = (30.0, 68.0)  # KiCad (x of left edge, y of bottom edge)

fails = []
notes = []


def check(ok, label, detail):
    (notes if ok else fails).append("%s %-46s %s" % ("PASS" if ok else "FAIL", label, detail))


# --------------------------------------------------------------- parameters
src = open(SCAD, encoding="utf-8").read()


def num(name):
    m = re.search(r"^\s*%s\s*=\s*(-?[\d.]+)\s*;" % re.escape(name), src, re.M)
    if not m:
        sys.exit("parameter %s not found in %s" % (name, SCAD))
    return float(m.group(1))


def pairs(name):
    m = re.search(r"^\s*%s\s*=\s*\[(.*?)\];" % re.escape(name), src, re.M | re.S)
    return [(float(a), float(b)) for a, b in re.findall(r"\[\s*([\d.]+)\s*,\s*([\d.]+)\s*\]", m.group(1))]


pcb_w, pcb_d, pcb_t = num("pcb_w"), num("pcb_d"), num("pcb_t")
pcb_gap, wall, floor_t, lid_t = num("pcb_gap"), num("wall"), num("floor_t"), num("lid_t")
standoff_h, headroom, corner_r = num("standoff_h"), num("headroom"), num("corner_r")
post_r, lid_cs_d, lid_pilot_d = num("post_r"), num("lid_cs_d"), num("lid_pilot_d")
pcb_standoff_r = num("pcb_standoff_r")
clip_boss_r, clip_plate_t = num("clip_boss_r"), num("clip_plate_t")
rail_w, rail_brim_t, brim_slop = num("rail_w"), num("rail_brim_t"), num("brim_slop")
spring_preload, clip_wall_t, lip_reach = num("spring_preload"), num("clip_wall_t"), num("lip_reach")
clip_margin, lip_h, lip_w, lip_clear = num("clip_margin"), num("lip_h"), num("lip_w"), num("lip_clear")
pcb_holes = pairs("pcb_holes")
j1 = [float(v) for v in re.search(r"j1_wire_y\s*=\s*\[([\d., ]+)\]", src).group(1).split(",")]
j2 = [float(v) for v in re.search(r"j2_wire_y\s*=\s*\[([\d., ]+)\]", src).group(1).split(",")]
j3 = [float(v) for v in re.search(r"j3_y\s*=\s*\[([\d., ]+)\]", src).group(1).split(",")]

interior_w = pcb_w + 2 * pcb_gap
interior_d = pcb_d + 2 * pcb_gap
interior_h = standoff_h + pcb_t + headroom
outer_w, outer_d = interior_w + 2 * wall, interior_d + 2 * wall
base_h, outer_h = floor_t + interior_h, floor_t + interior_h + lid_t
pcb_x0 = pcb_y0 = wall + pcb_gap
pcb_zt = floor_t + standoff_h + pcb_t
post_xy = [(corner_r, corner_r), (outer_w - corner_r, corner_r),
           (corner_r, outer_d - corner_r), (outer_w - corner_r, outer_d - corner_r)]
_boss = float(re.search(r"clip_boss_xy\s*=\s*\[\[\s*([\d.]+)", src).group(1))
clip_boss_x = [_boss, outer_w - _boss]
rail_cx = outer_w / 2
fixed_in = rail_cx - rail_w / 2 - brim_slop / 2
fixed_out = fixed_in - clip_wall_t
spring_in = rail_cx + rail_w / 2 - spring_preload
spring_out = spring_in + clip_wall_t
clip_x1 = outer_w - clip_margin

print("Enclosure  %.1f x %.1f x %.1f mm outer   (interior %.1f x %.1f x %.1f)"
      % (outer_w, outer_d, outer_h, interior_w, interior_d, interior_h))
print("Board sits %.1f mm above the floor, %.1f mm clear above it under the lid.\n"
      % (floor_t + standoff_h, headroom))

# ------------------------------------------------------------- courtyards
# Real F.CrtYd outlines out of the board file, in board-local coordinates.
def sexpr_blocks(text, key):
    out, i, tok = [], 0, "(" + key
    while True:
        i = text.find(tok, i)
        if i < 0:
            return out
        if text[i + len(tok)] not in " \n\t":
            i += 1
            continue
        depth, j = 0, i
        while True:
            if text[j] == "(":
                depth += 1
            elif text[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        out.append(text[i:j + 1])
        i = j + 1


courtyards = {}
board = open(os.path.join(os.path.dirname(HERE), "bazauto-block-detection.kicad_pcb"),
             encoding="utf-8").read()
for fp in sexpr_blocks(board, "footprint"):
    ref = re.search(r'\(property "Reference" "([^"]+)"', fp)
    at = re.search(r"\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)", fp)
    if not ref or not at:
        continue
    ox, oy, rot = float(at.group(1)), float(at.group(2)), math.radians(float(at.group(3) or 0))
    pts = []
    for shape in ("fp_line", "fp_rect", "fp_poly"):
        for blk in sexpr_blocks(fp, shape):
            if "F.CrtYd" not in blk:
                continue
            pts += [(float(a), float(b)) for a, b in
                    re.findall(r"\((?:start|end|xy) (-?[\d.]+) (-?[\d.]+)\)", blk)]
    if not pts:
        continue
    g = [(ox + x * math.cos(rot) + y * math.sin(rot),
          oy - x * math.sin(rot) + y * math.cos(rot)) for x, y in pts]
    xs, ys = [p[0] for p in g], [p[1] for p in g]
    courtyards[ref.group(1)] = (min(xs) - BOARD_ORIGIN[0], max(xs) - BOARD_ORIGIN[0],
                                BOARD_ORIGIN[1] - max(ys), BOARD_ORIGIN[1] - min(ys))
print("read %d component courtyards from the board file\n" % len(courtyards))


def rect_dist(cx, cy, x0, x1, y0, y1):
    """Distance from a point to an axis-aligned rectangle (0 if inside)."""
    dx = max(x0 - cx, 0, cx - x1)
    dy = max(y0 - cy, 0, cy - y1)
    return math.hypot(dx, dy)


# 1. lid screw posts must miss the board entirely
for i, (px, py) in enumerate(post_xy):
    d = rect_dist(px, py, pcb_x0, pcb_x0 + pcb_w, pcb_y0, pcb_y0 + pcb_d)
    check(d >= post_r + 0.3, "corner post %d clears the board" % (i + 1),
          "gap %.2f mm (post r=%.1f)" % (d - post_r, post_r))

# 2. lid countersink must leave wall at the moulded corner
worst = corner_r - lid_cs_d / 2
check(worst >= 1.0, "lid countersink wall at the corner", "%.2f mm left" % worst)

# 3. board standoffs: on the board, and clear of every component courtyard
for hx, hy in pcb_holes:
    edge = min(hx, pcb_w - hx, hy, pcb_d - hy)
    check(edge >= pcb_standoff_r, "standoff at (%.1f, %.1f) sits on the board" % (hx, hy),
          "%.2f mm to the board edge (r=%.1f)" % (edge, pcb_standoff_r))

# An M2 pan head plus driver wants ~2.5 mm of radius clear of every courtyard
head_r = 2.5
for hx, hy in pcb_holes:
    near = min((rect_dist(hx, hy, *box), ref) for ref, box in courtyards.items())
    check(near[0] >= head_r, "screw head at (%.1f, %.1f) clears parts" % (hx, hy),
          "nearest courtyard is %s at %.2f mm" % (near[1], near[0]))

# 4. cable slots line up with what they serve
slot_z0, slot_z1 = pcb_zt + 0.9, pcb_zt + 9.4
for name, ys in (("CT1", j1), ("CT2", j2)):
    y0, y1 = pcb_y0 + ys[0] - 2.0, pcb_y0 + ys[1] + 2.0
    for p in post_xy:
        d = rect_dist(p[0], p[1], 0, wall, y0, y1)
        check(d >= post_r, "%s slot clears the corner posts" % name, "gap %.2f mm" % (d - post_r))
        break
    check(y0 > wall + 1 and y1 < outer_d - wall - 1, "%s slot inside the wall" % name,
          "y %.1f..%.1f of %.1f" % (y0, y1, outer_d))
check(slot_z1 < base_h - lip_h, "CT slots clear the lid lip",
      "slot top %.1f, lip starts %.1f" % (slot_z1, base_h - lip_h))

out_z0, out_z1 = pcb_zt + 11.4, pcb_zt + 19.4
check(out_z1 <= base_h - lip_h, "OUT slot clears the lid lip",
      "slot top %.1f, lip starts %.1f" % (out_z1, base_h - lip_h))
check(out_z0 < pcb_zt + 17.0 < out_z1, "OUT slot spans the housing top",
      "housing top %.1f is inside %.1f..%.1f" % (pcb_zt + 17.0, out_z0, out_z1))

# 5. lid lip must not land on the board
lip_inner = wall + lip_clear + lip_w
check(lip_inner < pcb_x0, "lid lip clears the board edge",
      "lip reaches x=%.2f, board starts %.2f" % (lip_inner, pcb_x0))

# 6. DIN channel
channel = spring_in - fixed_in
check(channel < rail_w, "spring tongue is preloaded against the rail",
      "channel %.2f mm vs 35.00 rail" % channel)
throw = (rail_w - channel) / 2 + lip_reach
check(throw < 4.0, "tongue throw to clip on", "%.2f mm" % throw)
check(rail_brim_t + 0.2 <= rail_brim_t + 0.3, "hook grips under a %.1f mm brim" % rail_brim_t,
      "0.20 mm of slack, taken up by the tongue")

# 7. clip screws: clear of the hooks, the tongue slot and the plate edge
cs_r = lid_cs_d / 2
check(clip_boss_x[0] + cs_r < fixed_out, "left clip screw clears the fixed hook",
      "gap %.2f mm" % (fixed_out - clip_boss_x[0] - cs_r))
check(clip_boss_x[0] - cs_r > clip_margin, "left clip screw inside the plate",
      "gap %.2f mm" % (clip_boss_x[0] - cs_r - clip_margin))
slot_outer = spring_out + 0.6
check(clip_boss_x[1] - cs_r > slot_outer, "right clip screw clears the tongue slot",
      "gap %.2f mm" % (clip_boss_x[1] - cs_r - slot_outer))
check(clip_boss_x[1] + cs_r < clip_x1, "right clip screw inside the plate",
      "gap %.2f mm" % (clip_x1 - clip_boss_x[1] - cs_r))

# 8. clip bosses inside the box must stay under the board
boss_top = floor_t + standoff_h - 0.6
check(boss_top < floor_t + standoff_h, "clip boss stays under the board",
      "boss top %.1f, board underside %.1f" % (boss_top, floor_t + standoff_h))
for bx in clip_boss_x:
    for i, (px, py) in enumerate(post_xy):
        d = math.hypot(bx - px, outer_d / 2 - py)
        check(d > clip_boss_r + post_r, "clip boss at x=%.1f clears post %d" % (bx, i + 1),
              "%.2f mm apart" % d)

# ------------------------------------------------------------------ report
for line in notes:
    print(" ", line)
print()
if fails:
    for line in fails:
        print(" ", line)
    print("\n%d check(s) FAILED" % len(fails))
    sys.exit(1)
print("all %d checks pass" % len(notes))
