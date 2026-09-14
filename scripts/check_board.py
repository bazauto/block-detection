"""Sanity-check the board as it stands: courtyard overlaps, off-board parts,
and any pad whose net does not match the schematic."""
import itertools, os, subprocess, sys, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLI = r'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe'
PCB = os.path.join(HERE, 'bazauto-block-detection.kicad_pcb')
SCH = os.path.join(HERE, 'bazauto-block-detection.kicad_sch')
mm = pcbnew.ToMM


def sch_nets():
    out = os.path.join(HERE, '_net.xml')
    r = subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadxml',
                        '-o', out, SCH], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit((r.stdout + r.stderr)[:400])
    root = ET.parse(out).getroot()
    os.remove(out)
    return {'%s.%s' % (n.get('ref'), n.get('pin')): net.get('name')
            for net in root.iter('net') for n in net.findall('node')}


def main():
    b = pcbnew.LoadBoard(PCB)
    xs, ys = [], []
    for d in b.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            for p in (d.GetStart(), d.GetEnd()):
                xs.append(mm(p.x)); ys.append(mm(p.y))
    ox, oy, bw, bh = min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)
    boxes, bad = {}, 0
    for fp in b.Footprints():
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox()
        if bb.GetWidth() == 0:
            bb = fp.GetBoundingBox(False, False)
        boxes[fp.GetReference()] = (mm(bb.GetLeft()) - ox, mm(bb.GetTop()) - oy,
                                    mm(bb.GetRight()) - ox, mm(bb.GetBottom()) - oy)
    for a, c in itertools.combinations(sorted(boxes), 2):
        ax1, ay1, ax2, ay2 = boxes[a]
        bx1, by1, bx2, by2 = boxes[c]
        w = min(ax2, bx2) - max(ax1, bx1)
        h = min(ay2, by2) - max(ay1, by1)
        if w > 0.001 and h > 0.001:
            bad += 1
            print('COURTYARD OVERLAP %-4s %-4s  %.2f x %.2f mm' % (a, c, w, h))
    for ref, (x1, y1, x2, y2) in sorted(boxes.items()):
        if x1 < -0.001 or y1 < -0.001 or x2 > bw + 0.001 or y2 > bh + 0.001:
            bad += 1
            print('OFF-BOARD %-4s x[%.2f,%.2f] y[%.2f,%.2f]' % (ref, x1, x2, y1, y2))

    want = sch_nets()
    for fp in b.Footprints():
        for pad in fp.Pads():
            key = '%s.%s' % (fp.GetReference(), pad.GetNumber())
            if key not in want:
                continue
            if pad.GetNetname() != want[key]:
                bad += 1
                print('NET MISMATCH %-8s board=%-18s sch=%s'
                      % (key, pad.GetNetname() or '<none>', want[key]))
    missing = [k for k in want if not any(
        '%s.%s' % (fp.GetReference(), p.GetNumber()) == k
        for fp in b.Footprints() for p in fp.Pads())]
    if missing:
        bad += 1
        print('PADS IN SCHEMATIC BUT NOT ON BOARD:', sorted(missing))
    print('board %.1f x %.1f mm, %d footprints, problems: %d'
          % (bw, bh, len(boxes), bad))
    return bad


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
