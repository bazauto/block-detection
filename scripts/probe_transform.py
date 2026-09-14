"""Derive KiCad's symbol placement transform empirically.

Reads KiCad's own demo schematics, then for each (angle, mirror) placement
scores all eight signed-permutation transforms by how often they put a symbol
pin exactly on a wire endpoint / junction. The winner is what KiCad actually
uses, so gen_schematic.py can compute wire routes from pin positions instead of
guessing them.
"""
import glob
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kicadlib as K

DEMOS = r'C:/Program Files/KiCad/10.0/share/kicad/demos'

CANDS = {
    'x,-y': lambda x, y: (x, -y),
    'x,y': lambda x, y: (x, y),
    '-x,y': lambda x, y: (-x, y),
    '-x,-y': lambda x, y: (-x, -y),
    'y,x': lambda x, y: (y, x),
    'y,-x': lambda x, y: (y, -x),
    '-y,x': lambda x, y: (-y, x),
    '-y,-x': lambda x, y: (-y, -x),
}


def main():
    score = defaultdict(lambda: defaultdict(int))
    total = defaultdict(int)
    for path in glob.glob(os.path.join(DEMOS, '**', '*.kicad_sch'), recursive=True):
        try:
            tree = K.parse(open(path, encoding='utf-8').read())
        except Exception:
            continue
        ls = K.find(tree, 'lib_symbols')
        if ls is None:
            continue
        libsyms = {str(s[1]): s for s in K.find_all(ls, 'symbol')}
        targets = set()
        for w in K.find_all(tree, 'wire'):
            for p in K.find_all(K.find(w, 'pts'), 'xy'):
                targets.add((round(float(p[1]), 3), round(float(p[2]), 3)))
        for j in K.find_all(tree, 'junction'):
            at = K.find(j, 'at')
            targets.add((round(float(at[1]), 3), round(float(at[2]), 3)))
        if not targets:
            continue
        for sym in K.find_all(tree, 'symbol'):
            lib_id, at, unit = K.find(sym, 'lib_id'), K.find(sym, 'at'), K.find(sym, 'unit')
            if lib_id is None or at is None:
                continue
            mir = K.find(sym, 'mirror')
            key_mir = str(mir[1]) if mir is not None else '-'
            defn = libsyms.get(str(lib_id[1]))
            if defn is None:
                continue
            pins = K.unit_pins(defn)
            u = int(unit[1]) if unit is not None else 1
            plist = dict(pins.get(0, {}))
            plist.update(pins.get(u, {}))
            plist = {k: v for k, v in plist.items()
                     if abs(v[0]) > 0.001 and abs(v[1]) > 0.001}
            if not plist:
                continue
            sx, sy, ang = float(at[1]), float(at[2]), int(float(at[3]))
            key = (ang, key_mir)
            total[key] += len(plist)
            for cname, fn in CANDS.items():
                for (px, py, _n, _t) in plist.values():
                    dx, dy = fn(px, py)
                    if (round(sx + dx, 3), round(sy + dy, 3)) in targets:
                        score[key][cname] += 1
    for key in sorted(score, key=lambda k: (k[1], k[0])):
        ranked = sorted(score[key].items(), key=lambda kv: -kv[1])
        print('angle %3d  mirror %-2s  (asymmetric pins sampled: %d)' %
              (key[0], key[1], total[key]))
        for cname, n in ranked[:3]:
            print('    %-6s %5d  %5.1f%%' % (cname, n, 100.0 * n / max(total[key], 1)))


if __name__ == '__main__':
    main()
