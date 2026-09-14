"""Check the schematic KiCad actually parses against the intended netlist.

Runs `kicad-cli sch export netlist`, then compares the extracted connectivity
with the design intent spelled out below. Any missing, extra, or unconnected
pin is reported. Exit code is non-zero if the board would not be built as
designed.
"""
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

CLI = r'C:/Program Files/KiCad/10.0/bin/kicad-cli.exe'
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCH = os.path.join(HERE, 'bazauto-block-detection.kicad_sch')

# --------------------------------------------------------------- design intent
# Each entry is a net and the exact set of pins that must be on it.
EXPECTED = {
    '+3V3': ['C1.1', 'C2.1', 'C5.1', 'D1.2', 'D2.2', 'J3.1',
             'RV1.1', 'RV2.1', 'U1.8', 'U2.8'],
    'GND': ['C1.2', 'C2.2', 'C3.2', 'C4.2', 'C5.2', 'D1.1', 'D2.1',
            'J1.2', 'J2.2', 'J3.4', 'JP1.2', 'R1.2', 'R3.2', 'R8.2', 'R9.2',
            'RV1.3', 'RV2.3', 'TP5.1', 'U1.4', 'U2.4'],

    # channel 1 -------------------------------------------------------------
    'CT1':   ['J1.1', 'R1.1', 'R2.1', 'D1.3', 'R4.1'],   # burden + clamp + series R
    'JP1BR': ['R2.2', 'JP1.1'],                          # 110R in series with the mode jumper
    'CT1F':  ['R4.2', 'U1.3'],                           # protected op-amp input
    'OA1':   ['U1.1', 'R6.1'],                           # op-amp output
    'RECT1': ['R6.2', 'D3.2'],                           # isolation R to rectifier anode
    'ENV1':  ['D3.1', 'C3.1', 'R8.1', 'U1.2', 'U2.3', 'R10.1', 'TP2.1'],
    'VREF1': ['RV1.2', 'U2.2', 'TP1.1'],
    'OUT1':  ['U2.1', 'R10.2', 'J3.2'],

    # channel 2 -------------------------------------------------------------
    'CT2':   ['J2.1', 'R3.1', 'D2.3', 'R5.1'],
    'CT2F':  ['R5.2', 'U1.5'],
    'OA2':   ['U1.7', 'R7.1'],
    'RECT2': ['R7.2', 'D4.2'],
    'ENV2':  ['D4.1', 'C4.1', 'R9.1', 'U1.6', 'U2.5', 'R11.1', 'TP4.1'],
    'VREF2': ['RV2.2', 'U2.6', 'TP3.1'],
    'OUT2':  ['U2.7', 'R11.2', 'J3.3'],
}


def extract():
    tmp = os.path.join(tempfile.gettempdir(), 'bd_net.xml')
    r = subprocess.run([CLI, 'sch', 'export', 'netlist', '--format', 'kicadxml',
                        '-o', tmp, SCH], capture_output=True, text=True)
    if r.returncode != 0:
        print('kicad-cli failed:', (r.stdout + r.stderr).strip())
        sys.exit(2)
    root = ET.parse(tmp).getroot()
    nets = {}
    for net in root.iter('net'):
        pins = frozenset('%s.%s' % (n.get('ref'), n.get('pin'))
                         for n in net.findall('node'))
        nets[net.get('name')] = pins
    return nets


def main():
    actual = extract()
    by_pins = {v: k for k, v in actual.items()}
    ok = True

    print('=== intended nets ===')
    for name, pins in EXPECTED.items():
        want = frozenset(pins)
        got_name = by_pins.get(want)
        if got_name is not None:
            print('  OK    %-7s (%2d pins)  kicad net "%s"' %
                  (name, len(want), got_name))
            continue
        ok = False
        # find whichever real net overlaps most, to explain the difference
        best, score = None, 0
        for n, p in actual.items():
            if len(want & p) > score:
                best, score = n, len(want & p)
        print('  BAD   %-7s expected %s' % (name, sorted(want)))
        if best:
            print('        closest kicad net "%s" = %s' % (best, sorted(actual[best])))
            print('        missing: %s   extra: %s' %
                  (sorted(want - actual[best]) or '-',
                   sorted(actual[best] - want) or '-'))
        else:
            print('        no overlapping net found')

    stray = [n for n in actual if n.startswith('unconnected-')]
    if stray:
        ok = False
        print('=== unconnected pins ===')
        for n in sorted(stray):
            print('  %s' % n)

    covered = set()
    for pins in EXPECTED.values():
        covered |= set(pins)
    all_pins = set()
    for pins in actual.values():
        all_pins |= set(pins)
    extra = all_pins - covered
    if extra:
        ok = False
        print('=== pins present in schematic but not in design intent ===')
        print('  %s' % sorted(extra))

    print()
    print('RESULT:', 'netlist matches design intent' if ok else 'MISMATCH')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
