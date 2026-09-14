"""Audit the ground plane.

Lists every piece of bottom-layer copper that is not the pour (each one is a
void in the reference plane), and reports which nets run directly over it.
Used to substantiate the claim that the plane is continuous underneath the
analog signal path.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(HERE, 'bazauto-block-detection.kicad_pcb')

# Nets whose reference plane must not be interrupted: the CT rails, the
# op-amp inputs, the rectifier and everything on the envelope filter.
ANALOG = {'/CT1', '/CT2', '/ENV1', '/ENV2', '/VREF1', '/VREF2',
          'Net-(U1A-+)', 'Net-(U1B-+)', 'Net-(D3-A)', 'Net-(D4-A)',
          'Net-(R6-Pad1)', 'Net-(R7-Pad1)', 'Net-(JP1-Pin_1)'}

CLEAR = 0.2   # pour clearance either side of a bottom-layer track


def seg_boxes(t, mmv, ox, oy, grow):
    a, b = t.GetStart(), t.GetEnd()
    x1, y1 = mmv(a.x) - ox, mmv(a.y) - oy
    x2, y2 = mmv(b.x) - ox, mmv(b.y) - oy
    w = mmv(t.GetWidth()) / 2.0 + grow
    return (min(x1, x2) - w, min(y1, y2) - w,
            max(x1, x2) + w, max(y1, y2) + w)


def overlap(a, b):
    return (min(a[2], b[2]) - max(a[0], b[0]) > 1e-6 and
            min(a[3], b[3]) - max(a[1], b[1]) > 1e-6)


def main():
    board = pcbnew.LoadBoard(PCB)
    mmv = pcbnew.ToMM
    xs = [mmv(p.x) for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts
          for p in (d.GetStart(), d.GetEnd())]
    ys = [mmv(p.y) for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts
          for p in (d.GetStart(), d.GetEnd())]
    ox, oy = min(xs), min(ys)

    bottom, top = [], []
    for t in board.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            continue
        (bottom if t.GetLayer() == pcbnew.B_Cu else top).append(t)

    print('=== bottom-layer copper outside the pour (plane voids) ===')
    if not bottom:
        print('  none - the ground plane is completely unbroken')
    total = 0.0
    voids = []
    for t in bottom:
        a, b = t.GetStart(), t.GetEnd()
        x1, y1 = mmv(a.x) - ox, mmv(a.y) - oy
        x2, y2 = mmv(b.x) - ox, mmv(b.y) - oy
        length = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        total += length
        voids.append((t.GetNetname(), seg_boxes(t, mmv, ox, oy, CLEAR)))
        print('  %-16s (%5.2f,%5.2f) -> (%5.2f,%5.2f)   %4.2f mm'
              % (t.GetNetname(), x1, y1, x2, y2, length))
    print('  total bottom-layer track length: %.2f mm' % total)

    print()
    print('=== analog nets crossing a void ===')
    hits = 0
    for t in top:
        net = t.GetNetname()
        if net not in ANALOG:
            continue
        box = seg_boxes(t, mmv, ox, oy, 0.0)
        for vnet, vbox in voids:
            if vnet == net:
                continue          # a net passing over its own hop is not a void
            if overlap(box, vbox):
                hits += 1
                a, b = t.GetStart(), t.GetEnd()
                print('  %-14s segment (%5.2f,%5.2f)->(%5.2f,%5.2f) passes over '
                      'the %s void' % (net, mmv(a.x) - ox, mmv(a.y) - oy,
                                       mmv(b.x) - ox, mmv(b.y) - oy, vnet))
    if not hits:
        print('  none - every analog trace has continuous copper beneath it')
    return hits


if __name__ == '__main__':
    sys.exit(0 if main() == 0 else 1)
