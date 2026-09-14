"""Route bazauto-block-detection.kicad_pcb.

Loads the existing board (preserving hand-adjusted placement and silkscreen),
strips any previous tracks/vias/zones, then lays down the routing and the
ground pours. Re-runnable: it always rebuilds routing from this description.

Layer plan
----------
B.Cu is a ground pour. The only copper on it besides the pour is one 2 mm
hop that lets /OUT1 cross the +3V3 feed next to J3 -- in the connector corner,
clear of every analog node, so the reference plane stays solid under the CT
rails, the op-amp inputs and the envelope filters.

Run with KiCad's bundled Python:
  "C:/Program Files/KiCad/10.0/bin/python.exe" scripts/route_pcb.py
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(HERE, 'bazauto-block-detection.kicad_pcb')

W_SIG = 0.25       # signal tracks
W_PWR = 0.50       # +3V3 distribution
VIA_D, VIA_DRILL = 0.8, 0.4
CLEARANCE = 0.2
EDGE_KEEPOUT = 0.3

# --------------------------------------------------------------------------
# Routes: (net, width, [(x, y), ...]) in board-local mm, on F.Cu unless the
# net name is prefixed 'B:' for the bottom-layer hop.
ROUTES = [
    # ---- channel 1 input -------------------------------------------------
    ('/CT1', W_SIG, [(6.0, 10.0), (14.0, 9.998), (16.087, 9.998), (18.0, 9.75)]),
    ('/CT1', W_SIG, [(16.087, 9.998), (16.087, 13.6)]),          # tap to R4
    ('Net-(JP1-Pin_1)', W_SIG,
     [(14.0, 12.922), (14.0, 15.4), (13.4, 15.4), (13.4, 16.9)]),
    ('Net-(U1A-+)', W_SIG,
     [(17.913, 13.6), (17.913, 15.5), (18.675, 15.5), (18.675, 16.888)]),

    # ---- channel 1 peak detector ----------------------------------------
    ('Net-(R6-Pad1)', W_SIG,                                      # op-amp out
     [(19.975, 16.888), (19.975, 15.8), (22.175, 15.8), (22.175, 8.5)]),
    ('Net-(D3-A)', W_SIG,
     [(24.0, 8.5), (24.0, 10.5), (23.0, 10.5), (23.0, 12.5)]),
    ('/ENV1', W_SIG,                          # feedback, under the U1 body
     [(19.325, 16.888), (19.325, 18.4), (23.28, 18.4), (23.28, 16.788)]),
    ('/ENV1', W_SIG, [(23.28, 16.788), (25.6, 16.788), (26.75, 16.75)]),
    ('/ENV1', W_SIG, [(25.6, 16.788), (25.6, 12.5), (26.3, 12.5)]),
    ('/ENV1', W_SIG, [(26.3, 12.5), (29.25, 12.5), (29.25, 11.0)]),
    ('/ENV1', W_SIG, [(29.25, 11.0), (29.25, 7.0)]),              # TP2
    ('/ENV1', W_SIG,
     [(26.75, 16.75), (30.0, 16.75), (30.0, 15.4), (32.675, 15.4),
      (32.675, 16.888)]),

    # ---- channel 1 comparator -------------------------------------------
    ('/VREF1', W_SIG,
     [(40.215, 10.0), (40.215, 14.0), (31.75, 14.0)]),            # via TP1
    ('/VREF1', W_SIG, [(33.325, 14.0), (33.325, 16.888)]),
    ('/OUT1', W_SIG, [(31.075, 11.0), (31.075, 8.8), (42.0, 8.8), (42.0, 18.3)]),
    ('/OUT1', W_SIG,
     [(33.975, 16.888), (36.5, 16.888), (36.5, 18.3), (42.2, 18.3)]),
    # cross the +3V3 feed to J3 pin 1 on the bottom layer
    ('B:/OUT1', W_SIG, [(42.2, 18.3), (43.8, 18.3)]),
    ('/OUT1', W_SIG, [(43.8, 18.3), (45.0, 18.3)]),

    # ---- channel 2 input -------------------------------------------------
    ('/CT2', W_SIG, [(6.0, 28.0), (14.0, 28.002), (16.087, 28.002), (18.0, 27.5)]),
    ('/CT2', W_SIG, [(16.087, 28.002), (16.087, 24.4)]),          # tap to R5
    ('Net-(U1B-+)', W_SIG,
     [(17.913, 24.4), (17.913, 22.9), (18.025, 22.9), (18.025, 21.112)]),

    # ---- channel 2 peak detector ----------------------------------------
    ('/ENV2', W_SIG,                                              # feedback
     [(18.675, 21.112), (18.675, 23.3), (21.0, 23.3), (21.0, 25.538),
      (23.28, 25.538)]),
    ('/ENV2', W_SIG, [(23.28, 25.538), (25.6, 25.538), (26.75, 25.5)]),
    ('/ENV2', W_SIG, [(25.6, 25.538), (25.6, 27.75), (26.3, 27.75)]),
    ('/ENV2', W_SIG, [(26.3, 27.75), (29.25, 27.75), (29.25, 26.7)]),
    ('/ENV2', W_SIG, [(29.25, 27.75), (29.25, 31.25)]),           # TP4
    ('/ENV2', W_SIG,          # into U2 through the gap between its pad rows
     [(26.75, 25.5), (30.0, 25.5), (30.0, 19.9), (32.025, 19.9),
      (32.025, 21.112)]),
    # op-amp output crosses the feedback trace; 1.3 mm dip to B.Cu
    ('Net-(R7-Pad1)', W_SIG,
     [(19.325, 21.112), (19.325, 22.75), (21.5, 22.75)]),
    ('B:Net-(R7-Pad1)', W_SIG, [(21.5, 22.75), (21.5, 26.2)]),
    ('Net-(R7-Pad1)', W_SIG, [(21.5, 26.2), (21.5, 30.6), (21.425, 30.8)]),
    ('Net-(D4-A)', W_SIG,
     [(23.25, 31.5), (24.0, 31.5), (24.0, 29.6), (23.0, 29.6), (23.0, 27.75)]),

    # ---- channel 2 comparator -------------------------------------------
    ('/VREF2', W_SIG,
     [(32.675, 21.112), (32.675, 23.4), (40.215, 23.4), (40.215, 28.0)]),
    # the hysteresis tap dips under U2's VREF2 escape
    ('/OUT2', W_SIG, [(31.075, 26.7), (31.075, 22.6), (31.9, 22.6)]),
    ('B:/OUT2', W_SIG, [(31.9, 22.6), (33.45, 22.6)]),
    ('/OUT2', W_SIG,
     [(33.45, 22.6), (42.0, 22.6), (42.0, 20.27), (45.0, 20.27)]),
    ('/OUT2', W_SIG, [(33.325, 21.112), (33.325, 22.6)]),

    # ---- +3V3 distribution ------------------------------------------------
    # spine tucked between the two pad rows of U1 and U2
    ('+3V3', W_PWR, [(19.975, 19.2), (43.0, 19.2)]),
    ('+3V3', W_PWR, [(43.0, 19.2), (43.0, 13.0), (46.4, 13.0)]),
    ('+3V3', W_PWR, [(19.975, 21.112), (19.975, 19.2)]),          # U1 V+
    ('+3V3', W_PWR, [(22.50, 21.4), (22.50, 19.2)]),              # C1
    ('+3V3', W_PWR, [(26.05, 21.4), (26.05, 19.2)]),              # C5
    ('+3V3', W_PWR, [(33.975, 21.112), (33.975, 19.2)]),          # U2 V+
    ('+3V3', W_PWR, [(36.35, 21.25), (36.35, 19.2)]),             # C2
    # ring: up the right edge to J3, along the top, and back underneath
    ('+3V3', W_PWR, [(46.4, 5.6), (46.4, 33.0)]),
    ('+3V3', W_PWR, [(46.4, 15.19), (45.0, 15.19)]),              # J3 pin 1
    ('+3V3', W_PWR, [(46.4, 5.6), (19.875, 5.6)]),
    ('+3V3', W_PWR, [(19.875, 5.6), (19.875, 8.8)]),              # D1 clamp
    ('+3V3', W_PWR, [(35.385, 5.6), (35.385, 7.46)]),             # RV1 top
    ('+3V3', W_PWR, [(46.4, 33.0), (33.0, 33.0)]),
    ('+3V3', W_PWR, [(33.0, 33.0), (33.0, 25.46), (33.99, 25.46)]),  # RV2 top
    # clamp D2 sits inside the channel-2 routing; feed it under the two
    # traces that box it in
    ('+3V3', W_SIG, [(19.975, 21.912), (20.2, 22.0)]),
    ('B:+3V3', W_SIG, [(20.2, 22.0), (20.2, 24.0)]),
    ('+3V3', W_SIG, [(20.2, 24.0), (20.2, 26.55)]),
]

# Vias that carry a net between layers: (net, (x, y)), small 0.6/0.3 vias.
HOP_VIAS = [
    ('/OUT1', (42.2, 18.3)), ('/OUT1', (43.8, 18.3)),
    ('/OUT2', (31.9, 22.6)), ('/OUT2', (33.45, 22.6)),
    ('Net-(R7-Pad1)', (21.5, 22.75)), ('Net-(R7-Pad1)', (21.5, 26.2)),
    ('+3V3', (20.2, 22.0)), ('+3V3', (20.2, 24.0)),
]

# GND stitching: (pad ref.pin, via position). Through-hole pads reach the
# pour directly and need none.
GND_VIAS = [
    ('R1.2', (11.2, 14.4)),
    ('R3.2', (11.2, 23.6)),
    ('D1.1', (21.4, 10.7)),
    ('D2.1', (19.878, 29.8)),
    ('C3.2', (24.55, 14.888)),
    ('C4.2', (24.55, 23.638)),
    ('R8.2', (26.75, 13.9)),
    ('R9.2', (26.75, 22.6)),
    ('C1.2', (24.40, 20.5)),
    ('C5.2', (27.95, 20.5)),
    ('C2.2', (38.25, 20.3)),
    ('U1.4', (16.8, 16.888)),
    ('U2.4', (30.8, 16.888)),
    ('RV1.3', (35.385, 10.5)),
    ('RV2.3', (35.385, 29.0)),
    ('TP5.1', (39.6, 16.25)),
]

# Extra plane stitching so the two pours stay tied together across the board.
STITCH = [(9.0, 19.2), (9.0, 6.0), (9.0, 34.0), (31.0, 2.6), (31.0, 35.8),
          (24.0, 2.6), (24.0, 35.8), (44.0, 2.6), (44.0, 35.8), (12.0, 22.0),
          (28.0, 35.8), (36.0, 35.8), (36.0, 2.6), (12.0, 32.5)]


# Silkscreen legends: (text, (x, y), height mm)
SILK = [
    ('BAZAUTO DCC BLOCK DETECTOR', (17.5, 1.6), 0.8),
    ('CT1', (1.6, 6.9), 0.9),
    ('CT2', (1.6, 24.9), 0.9),
    ('JP1 FIT=100R', (1.6, 19.0), 0.8),
    ('OPEN=1.1k', (1.6, 20.4), 0.8),
    ('HIGH=OCCUPIED', (19.2, 35.4), 0.8),
    ('J3 PINOUT', (2.0, 34.6), 0.8),
    ('3V3 O1 O2 GND', (2.0, 36.2), 0.8),
]


def mm(v):
    return pcbnew.FromMM(v)


def main():
    board = pcbnew.LoadBoard(PCB)
    mmv = pcbnew.ToMM
    xs, ys = [], []
    for d in board.GetDrawings():
        if d.GetLayer() == pcbnew.Edge_Cuts:
            for p in (d.GetStart(), d.GetEnd()):
                xs.append(mmv(p.x)); ys.append(mmv(p.y))
    ox, oy = min(xs), min(ys)
    bw, bh = max(xs) - ox, max(ys) - oy

    def vec(x, y):
        return pcbnew.VECTOR2I(mm(ox + x), mm(oy + y))

    # wipe previous routing so this script is the single source of truth
    for t in list(board.GetTracks()):
        board.Delete(t)
    for z in list(board.Zones()):
        board.Delete(z)

    # C1 shifts 0.65 mm right so channel 2's feedback and op-amp output each
    # get their own corridor past it.
    for fp in board.Footprints():
        if fp.GetReference() == 'C1':
            fp.SetPosition(vec(23.45, 21.40))

    nets = {}
    for code, ni in board.GetNetsByNetcode().items():
        nets[ni.GetNetname()] = ni

    def netof(name):
        if name not in nets:
            raise SystemExit('unknown net %r; have %s' % (name, sorted(nets)))
        return nets[name]

    def add_track(net, layer, p1, p2, width):
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(vec(*p1))
        t.SetEnd(vec(*p2))
        t.SetWidth(mm(width))
        t.SetLayer(layer)
        t.SetNet(net)
        board.Add(t)

    def add_via(net, pt, dia=VIA_D, drill=VIA_DRILL):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(vec(*pt))
        v.SetWidth(mm(dia))
        v.SetDrill(mm(drill))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(net)
        board.Add(v)
        return v

    ntracks = 0
    for name, width, pts in ROUTES:
        layer = pcbnew.F_Cu
        if name.startswith('B:'):
            layer, name = pcbnew.B_Cu, name[2:]
        net = netof(name)
        for a, b in zip(pts, pts[1:]):
            add_track(net, layer, a, b, width)
            ntracks += 1

    gnd = netof('GND')
    # layer-change vias for the three bottom-layer hops
    nhops = 0
    for name, pt in HOP_VIAS:
        add_via(netof(name), pt, dia=0.6, drill=0.3)
        nhops += 1

    # ground stitching from SMD pads down to the pour
    pads = {}
    for fp in board.Footprints():
        for pad in fp.Pads():
            pads['%s.%s' % (fp.GetReference(), pad.GetNumber())] = pad
    nvias = nhops
    for key, pt in GND_VIAS:
        pad = pads[key]
        p = pad.GetPosition()
        start = (mmv(p.x) - ox, mmv(p.y) - oy)
        add_track(gnd, pcbnew.F_Cu, start, pt, W_SIG)
        add_via(gnd, pt)
        nvias += 1
    for pt in STITCH:
        add_via(gnd, pt)
        nvias += 1

    # legends -- added as new items so the hand-placed designators stay put
    for txt, (tx, ty), size in SILK:
        t = pcbnew.PCB_TEXT(board)
        t.SetText(txt)
        t.SetLayer(pcbnew.F_SilkS)
        t.SetPosition(vec(tx, ty))
        t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
        t.SetTextThickness(mm(size * 0.15))
        t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        board.Add(t)

    # ground pours, both layers
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        zone = pcbnew.ZONE(board)
        zone.SetLayer(layer)
        zone.SetNet(gnd)
        zone.SetLocalClearance(mm(CLEARANCE))
        zone.SetMinThickness(mm(0.15))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
        zone.SetThermalReliefGap(mm(0.3))
        zone.SetThermalReliefSpokeWidth(mm(0.4))
        outline = zone.Outline()
        outline.NewOutline()
        k = EDGE_KEEPOUT
        for (x, y) in ((k, k), (bw - k, k), (bw - k, bh - k), (k, bh - k)):
            outline.Append(mm(ox + x), mm(oy + y))
        board.Add(zone)

    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

    board.BuildListOfNets()
    pcbnew.SaveBoard(PCB, board)
    print('routed: %d segments, %d vias (%d layer-change), 2 pours, %.0f x %.0f mm'
          % (ntracks, nvias, nhops, bw, bh))


if __name__ == '__main__':
    main()
