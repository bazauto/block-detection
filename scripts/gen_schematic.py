"""Generate bazauto-block-detection.kicad_sch (2-channel DCC block detector).

Symbol graphics are pulled from the installed KiCad libraries; every wire is
computed from real pin coordinates using the placement transform derived in
probe_transform.py, so connectivity is calculated rather than eyeballed.

Sheet plan (A4 landscape, 1.27 mm grid):
    channel 1   y ~= 33..75      channel 2   y ~= 109..151
    left..right: input terminal -> burden -> ESD clamp -> series R
                 -> precision peak detector -> comparator + threshold pot
    power / decoupling block along the bottom, output header centre-right.
"""
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kicadlib as K
from kicadlib import Q

KICAD_SYMS = r'C:/Program Files/KiCad/10.0/share/kicad/symbols'
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = 'bazauto-block-detection'
NS = uuid.UUID('7f2b1c04-8e3a-4c17-9b55-6d0e2a1f4c83')

# Placement transform: (angle, mirror) -> lambda mapping library (x, y) to the
# schematic-space offset from the symbol origin. Derived empirically from
# KiCad's own demo schematics (see probe_transform.py).
XFORM = {
    (0, None): lambda x, y: (x, -y),
    (90, None): lambda x, y: (-y, -x),
    (180, None): lambda x, y: (-x, y),
    (270, None): lambda x, y: (y, x),
    (0, 'x'): lambda x, y: (x, y),
    (90, 'x'): lambda x, y: (-y, x),
    (270, 'x'): lambda x, y: (y, -x),
    (0, 'y'): lambda x, y: (-x, -y),
}

FP = {
    'R0805': 'Resistor_SMD:R_0805_2012Metric',
    'R1206': 'Resistor_SMD:R_1206_3216Metric',
    'C0805': 'Capacitor_SMD:C_0805_2012Metric',
    'SOD123': 'Diode_SMD:D_SOD-123',
    'SOT23': 'Package_TO_SOT_SMD:SOT-23',
    'MSOP8': 'Package_SO:MSOP-8_3x3mm_P0.65mm',
    'TB2': 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-2-3.5-H_1x02_P3.50mm_Horizontal',
    'PH2': 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',
    'PH4': 'Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical',
    'POT': 'Potentiometer_SMD:Potentiometer_Bourns_3269W_Vertical',
    'TP': 'TestPoint:TestPoint_Pad_D1.5mm',
    'MH': 'MountingHole:MountingHole_2.2mm_M2',
}


def det_uuid(key):
    return Q(str(uuid.uuid5(NS, key)))


def r4(v):
    return round(v + 0.0, 4)


class Sheet:
    def __init__(self, libs):
        self.libs = libs
        self.lib_symbols = {}       # lib_id -> resolved symbol sexpr
        self.symbols = []           # placed symbol sexprs
        self.wires = []             # ((x1,y1),(x2,y2))
        self.labels = []            # (text, x, y, angle, justify)
        self.texts = []             # (text, x, y, size)
        self.pin_points = {}        # (x,y) -> [(ref, pin), ...]
        self.root_uuid = det_uuid('root-sheet')
        self.netmap = {}            # ref.pin -> intended net (documentation aid)

    # ---------------------------------------------------------------- symbols
    def define(self, lib_id, srclib, srcname, overrides=None):
        if lib_id in self.lib_symbols:
            return
        sym = self.libs.resolved(srclib, srcname, newname=lib_id)
        for name, value in (overrides or {}).items():
            hit = None
            for p in K.find_all(sym, 'property'):
                if str(p[1]) == name:
                    hit = p
                    break
            if hit is not None:
                hit[2] = Q(value)
            else:
                sym.insert(2, ['property', Q(name), Q(value),
                               ['at', 0, 0, 0], ['show_name', 'no'],
                               ['hide', 'yes'],
                               ['effects', ['font', ['size', 1.27, 1.27]]]])
        self.lib_symbols[lib_id] = sym

    def place(self, lib_id, ref, value, at, angle=0, mirror=None, unit=1,
              footprint='', datasheet='~', in_bom=True, ref_off=(2.54, -2.54),
              val_off=(2.54, 2.54), hide_value=False, hide_ref=False,
              extra_props=None, prop_angle=0, prop_justify='left'):
        """Place a symbol and register the absolute position of each of its pins."""
        x, y = at
        sym = self.lib_symbols[lib_id]
        pins = K.unit_pins(sym)
        plist = dict(pins.get(0, {}))
        plist.update(pins.get(unit, {}))
        fn = XFORM[(angle, mirror)]
        abs_pins = {}
        for num, (px, py, _pn, _pt) in plist.items():
            dx, dy = fn(px, py)
            pt = (r4(x + dx), r4(y + dy))
            abs_pins[num] = pt
            self.pin_points.setdefault(pt, []).append((ref, num))

        def prop(name, val, off, hide, justify=prop_justify):
            eff = ['effects', ['font', ['size', 1.27, 1.27]]]
            if justify:
                eff.append(['justify', justify])
            if hide:
                eff.append(['hide', 'yes'])
            return ['property', Q(name), Q(val),
                    ['at', r4(x + off[0]), r4(y + off[1]), prop_angle], eff]

        node = ['symbol',
                ['lib_id', Q(lib_id)],
                ['at', r4(x), r4(y), angle]]
        if mirror:
            node.append(['mirror', mirror])
        node += [['unit', unit],
                 ['exclude_from_sim', 'no'],
                 ['in_bom', 'yes' if in_bom else 'no'],
                 ['on_board', 'yes'],
                 ['dnp', 'no'],
                 ['uuid', det_uuid('sym:%s:%d' % (ref, unit))],
                 prop('Reference', ref, ref_off, hide_ref),
                 prop('Value', value, val_off, hide_value),
                 prop('Footprint', footprint, (0, 0), True),
                 prop('Datasheet', datasheet, (0, 0), True),
                 prop('Description', '', (0, 0), True)]
        for pname, pval in (extra_props or {}).items():
            node.append(prop(pname, pval, (0, 0), True))
        for num in sorted(plist):
            node.append(['pin', Q(num), ['uuid', det_uuid('pin:%s:%s:%d' % (ref, num, unit))]])
        node.append(['instances',
                     ['project', Q(PROJECT),
                      ['path', Q('/' + str(self.root_uuid)),
                       ['reference', Q(ref)], ['unit', unit]]]])
        self.symbols.append(node)
        return abs_pins

    # ------------------------------------------------------------------ wires
    def wire(self, p1, p2):
        a = (r4(p1[0]), r4(p1[1]))
        b = (r4(p2[0]), r4(p2[1]))
        if a != b:
            self.wires.append((a, b))
        return b

    def poly(self, *pts):
        for i in range(len(pts) - 1):
            self.wire(pts[i], pts[i + 1])
        return pts[-1]

    def label(self, text, at, angle=0, justify='left bottom'):
        self.labels.append((text, r4(at[0]), r4(at[1]), angle, justify))

    def note(self, text, at, size=1.27):
        self.texts.append((text, r4(at[0]), r4(at[1]), size))

    # -------------------------------------------------------------- junctions
    def junctions(self):
        """Insert a junction wherever KiCad would need one: 3+ wire ends at a
        point, or a wire end landing in the interior of another wire."""
        ends = {}
        for a, b in self.wires:
            ends[a] = ends.get(a, 0) + 1
            ends[b] = ends.get(b, 0) + 1
        out = []
        candidates = set(ends) | set(self.pin_points)
        for p in candidates:
            n = ends.get(p, 0)
            interior = 0
            for a, b in self.wires:
                if p in (a, b):
                    continue
                if _on_segment(p, a, b):
                    interior += 1
            total = n + 2 * interior
            if total >= 3:
                out.append(p)
        return sorted(out)


def _on_segment(p, a, b):
    (px, py), (ax, ay), (bx, by) = p, a, b
    if abs(ax - bx) < 1e-6:
        return abs(px - ax) < 1e-6 and min(ay, by) < py < max(ay, by)
    if abs(ay - by) < 1e-6:
        return abs(py - ay) < 1e-6 and min(ax, bx) < px < max(ax, bx)
    return False


# --------------------------------------------------------------------- build
def build():
    libs = K.SymbolLibs(KICAD_SYMS)
    s = Sheet(libs)

    s.define('Device:R', 'Device', 'R')
    s.define('Device:C', 'Device', 'C')
    s.define('Device:R_Potentiometer_Trim', 'Device', 'R_Potentiometer_Trim')
    s.define('Diode:BAT54S', 'Diode', 'BAT54S')
    s.define('Diode:1N4148W', 'Diode', '1N4148W')
    s.define('Connector:Screw_Terminal_01x02', 'Connector', 'Screw_Terminal_01x02')
    s.define('Connector_Generic:Conn_01x02', 'Connector_Generic', 'Conn_01x02')
    s.define('Connector_Generic:Conn_01x04', 'Connector_Generic', 'Conn_01x04')
    s.define('Connector:TestPoint', 'Connector', 'TestPoint')
    s.define('Mechanical:MountingHole', 'Mechanical', 'MountingHole')
    s.define('power:GND', 'power', 'GND')
    s.define('power:+3V3', 'power', '+3V3')

    # Project parts: the exact ordered devices, drawn on vetted generic bodies.
    s.define('%s:TLV9002IDGKR' % PROJECT, 'Amplifier_Operational', 'LM2904',
             overrides={
                 'Value': 'TLV9002IDGKR',
                 'Footprint': FP['MSOP8'],
                 'Datasheet': 'https://www.ti.com/lit/ds/symlink/tlv9002.pdf',
                 'Description': 'Dual RRIO op-amp, 1 MHz, 1.8-5.5 V, VSSOP-8 (DGK)',
                 'ki_fp_filters': 'MSOP*3x3mm*P0.65mm*'})
    s.define('%s:TLV3212IDGKR' % PROJECT, 'Comparator', 'MCP6562',
             overrides={
                 'Value': 'TLV3212IDGKR',
                 'Footprint': FP['MSOP8'],
                 'Datasheet': 'https://www.ti.com/lit/ds/symlink/tlv3212.pdf',
                 'Description': 'Dual push-pull rail-to-rail comparator, VSSOP-8 (DGK)',
                 'ki_fp_filters': 'MSOP*3x3mm*P0.65mm*'})

    OPA = '%s:TLV9002IDGKR' % PROJECT
    CMP = '%s:TLV3212IDGKR' % PROJECT

    pwr_n = [0]

    def gnd(at):
        pwr_n[0] += 1
        s.place('power:GND', '#PWR%02d' % pwr_n[0], 'GND', at,
                hide_ref=True, hide_value=True, in_bom=False,
                val_off=(0, 2.54))

    def vcc(at):
        pwr_n[0] += 1
        s.place('power:+3V3', '#PWR%02d' % pwr_n[0], '+3V3', at,
                hide_ref=True, hide_value=True, in_bom=False,
                val_off=(0, -2.54))

    # ------------------------------------------------------------- a channel
    def channel(ch, Y):
        prog = (ch == 1)
        refs = {
            1: dict(J='J1', Rb='R1', Rj='R2', JP='JP1', Dc='D1', Rs='R4',
                    Ri='R6', Dr='D3', Ce='C3', Rbl='R8', RV='RV1', Rh='R10',
                    TPv='TP1', TPe='TP2', op_unit=1, op=('1', '2', '3'),
                    cp_unit=1, cp=('1', '2', '3')),
            2: dict(J='J2', Rb='R3', Rj=None, JP=None, Dc='D2', Rs='R5',
                    Ri='R7', Dr='D4', Ce='C4', Rbl='R9', RV='RV2', Rh='R11',
                    TPv='TP3', TPe='TP4', op_unit=2, op=('7', '6', '5'),
                    cp_unit=2, cp=('7', '6', '5')),
        }[ch]
        o_out, o_inv, o_pos = refs['op']
        c_out, c_inv, c_pos = refs['cp']

        # --- input terminal block (pins face right: angle 0 + mirror y)
        j = s.place('Connector:Screw_Terminal_01x02', refs['J'],
                    'CT%d In' % ch, (25.4, Y), mirror='y', footprint=FP['TB2'],
                    ref_off=(-2.54, -8.89), val_off=(-2.54, 6.35))
        rail_y = Y
        # CT hot rail: terminal -> burden network -> clamp -> series resistor
        s.wire(j['1'], (58.42, rail_y))
        s.label('CT%d' % ch, (34.29, rail_y))
        # cold side of the CT winding to ground
        s.poly(j['2'], (33.02, Y + 2.54), (33.02, Y + 7.62))
        gnd((33.02, Y + 7.62))

        # --- burden network
        burden_val = '1.1k' if prog else '100R'
        rb = s.place('Device:R', refs['Rb'], burden_val, (38.1, Y + 11.43),
                     footprint=FP['R1206'], ref_off=(2.54, -1.27),
                     val_off=(2.54, 1.27),
                     extra_props={'Tolerance': '1%', 'Power': '0.25W'})
        s.wire((38.1, rail_y), rb['1'])
        s.wire(rb['2'], (38.1, Y + 17.78))
        gnd((38.1, Y + 17.78))

        if prog:
            rj = s.place('Device:R', refs['Rj'], '110R', (45.72, Y + 10.16),
                         footprint=FP['R1206'], ref_off=(2.54, -1.27),
                         val_off=(2.54, 1.27),
                         extra_props={'Tolerance': '1%', 'Power': '0.25W'})
            s.wire((45.72, rail_y), rj['1'])
            jp = s.place('Connector_Generic:Conn_01x02', refs['JP'],
                         'MODE', (50.8, Y + 16.51), footprint=FP['PH2'],
                         ref_off=(3.81, -1.27), val_off=(3.81, 2.54))
            s.wire(rj['2'], jp['1'])
            s.wire(jp['2'], (45.72, Y + 24.13))
            gnd((45.72, Y + 24.13))

        # --- ESD / over-range clamp to the rails (BAT54S series pair)
        dc = s.place('Diode:BAT54S', refs['Dc'], 'BAT54S', (58.42, Y),
                     angle=90, footprint=FP['SOT23'], prop_angle=90,
                     prop_justify='right',
                     ref_off=(2.54, -12.7), val_off=(2.54, -10.16))
        s.wire((58.42, rail_y), dc['3'])     # COM sits on the rail
        s.wire(dc['2'], (58.42, Y - 10.16))
        vcc((58.42, Y - 10.16))
        s.wire(dc['1'], (58.42, Y + 10.16))
        gnd((58.42, Y + 10.16))

        # --- series input protection resistor
        rs = s.place('Device:R', refs['Rs'], '1k', (69.85, Y), angle=90,
                     footprint=FP['R0805'], prop_angle=90,
                     prop_justify='right',
                     ref_off=(-1.27, -3.81), val_off=(-1.27, 5.08))
        s.wire((63.5, rail_y), rs['1'])

        # --- precision peak detector (diode inside the op-amp feedback loop)
        op = s.place(OPA, 'U%s' % 1, 'TLV9002IDGKR', (86.36, Y + 2.54),
                     unit=refs['op_unit'], footprint=FP['MSOP8'],
                     ref_off=(-2.54, -8.89), val_off=(-2.54, 8.89))
        s.wire(rs['2'], op[o_pos])

        ri = s.place('Device:R', refs['Ri'], '100R', (101.6, Y + 2.54),
                     angle=90, footprint=FP['R0805'], prop_angle=90,
                     prop_justify='right',
                     ref_off=(-1.27, -6.35), val_off=(-1.27, -3.81))
        s.wire(op[o_out], ri['1'])
        dr = s.place('Diode:1N4148W', refs['Dr'], '1N4148W',
                     (111.76, Y + 2.54), angle=180, footprint=FP['SOD123'],
                     prop_justify='right',
                     ref_off=(-2.54, -6.35), val_off=(-2.54, -3.81))
        s.wire(ri['2'], dr['2'])                     # anode
        env = s.wire(dr['1'], (127.0, Y + 2.54))     # cathode -> ENV rail

        ce = s.place('Device:C', refs['Ce'], '10uF', (121.92, Y + 11.43),
                     footprint=FP['C0805'], ref_off=(2.54, -1.27),
                     val_off=(2.54, 1.27),
                     extra_props={'Voltage': '25V', 'Dielectric': 'X7R'})
        s.wire((121.92, Y + 2.54), ce['1'])
        s.wire(ce['2'], (121.92, Y + 17.78))
        gnd((121.92, Y + 17.78))

        rbl = s.place('Device:R', refs['Rbl'], '100k', (132.08, Y + 11.43),
                      footprint=FP['R0805'], ref_off=(2.54, -1.27),
                      val_off=(2.54, 1.27))
        s.wire(ce['1'], rbl['1'])
        s.wire(rbl['2'], (132.08, Y + 17.78))
        gnd((132.08, Y + 17.78))

        s.label('ENV%d' % ch, (127.0, Y + 2.54))
        tpe = s.place('Connector:TestPoint', refs['TPe'], 'ENV%d' % ch,
                      (127.0, Y - 6.35), footprint=FP['TP'], in_bom=False,
                      ref_off=(2.54, -2.54), val_off=(2.54, 0))
        s.wire(env, tpe['1'])

        # peak-detector feedback: cap junction back to the inverting input
        s.wire((78.74, Y + 5.08), op[o_inv])
        s.label('ENV%d' % ch, (78.74, Y + 5.08), justify='right bottom')

        # --- comparator
        cp = s.place(CMP, 'U%s' % 2, 'TLV3212IDGKR', (152.4, Y + 2.54),
                     unit=refs['cp_unit'], footprint=FP['MSOP8'],
                     ref_off=(-2.54, -8.89), val_off=(-2.54, 8.89))
        s.wire((139.7, Y), cp[c_pos])
        s.label('ENV%d' % ch, (139.7, Y), justify='right bottom')
        s.wire((139.7, Y + 5.08), cp[c_inv])
        s.label('VREF%d' % ch, (139.7, Y + 5.08), justify='right bottom')

        # threshold pot
        rv = s.place('Device:R_Potentiometer_Trim', refs['RV'], '10k',
                     (152.4, Y + 22.86), footprint=FP['POT'],
                     ref_off=(-8.89, -1.27), val_off=(-8.89, 1.27),
                     extra_props={'Type': '10k multi-turn SMD trimmer'})
        s.wire(rv['1'], (152.4, Y + 16.51))
        vcc((152.4, Y + 16.51))
        s.wire(rv['3'], (152.4, Y + 29.21))
        gnd((152.4, Y + 29.21))
        tpv = s.place('Connector:TestPoint', refs['TPv'], 'VREF%d' % ch,
                      (168.91, Y + 22.86), footprint=FP['TP'], in_bom=False,
                      ref_off=(0, -3.81), val_off=(0, 3.81))
        s.wire(rv['2'], tpv['1'])
        s.label('VREF%d' % ch, (157.48, Y + 22.86))

        # comparator output + hysteresis back to the envelope node
        s.wire(cp[c_out], (173.99, Y + 2.54))
        s.label('OUT%d' % ch, (173.99, Y + 2.54))
        rh = s.place('Device:R', refs['Rh'], '10M', (152.4, Y - 11.43),
                     angle=90, footprint=FP['R0805'], prop_angle=90,
                     prop_justify='right',
                     ref_off=(-1.27, -6.35), val_off=(-1.27, -3.81))
        s.poly(rh['1'], (144.78, Y - 11.43), (144.78, Y))
        s.poly(rh['2'], (163.83, Y - 11.43), (163.83, Y + 2.54))

    channel(1, 45.72)
    channel(2, 121.92)

    # ------------------------------------------------------- power / decoupling
    VRAIL, GRAIL = 170.18, 190.5
    # Rails stop at the last thing on them, so no wire end is left dangling.
    s.wire((30.48, VRAIL), (99.06, VRAIL))
    s.wire((30.48, GRAIL), (106.68, GRAIL))
    vcc((30.48, VRAIL))
    gnd((30.48, GRAIL))

    # The board is fed from J3, whose pins are passive, so ERC needs telling
    # that these rails really are driven.
    s.define('power:PWR_FLAG', 'power', 'PWR_FLAG')
    for ref, at, ang in (('#FLG01', (35.56, 165.1), 0),
                         ('#FLG02', (35.56, 195.58), 180)):
        s.place('power:PWR_FLAG', ref, 'PWR_FLAG', at, angle=ang,
                in_bom=False, hide_ref=True, hide_value=True,
                val_off=(0, -2.54))
    s.wire((35.56, VRAIL), (35.56, 165.1))
    s.wire((35.56, GRAIL), (35.56, 195.58))

    for ref, lib, val, x in (('U1', OPA, 'TLV9002IDGKR', 50.8),
                             ('U2', CMP, 'TLV3212IDGKR', 81.28)):
        p = s.place(lib, ref, val, (x, 180.34), unit=3, footprint=FP['MSOP8'],
                    ref_off=(2.54, -5.08), val_off=(2.54, 6.35),
                    hide_value=True)
        s.wire(p['8'], (x - 2.54, VRAIL))
        s.wire(p['4'], (x - 2.54, GRAIL))

    for ref, val, x in (('C1', '100nF', 58.42), ('C2', '100nF', 88.9),
                        ('C5', '10uF', 99.06)):
        c = s.place('Device:C', ref, val, (x, 180.34), footprint=FP['C0805'],
                    ref_off=(2.54, -1.27), val_off=(2.54, 1.27),
                    extra_props={'Voltage': '25V'})
        s.wire(c['1'], (x, VRAIL))
        s.wire(c['2'], (x, GRAIL))

    tp5 = s.place('Connector:TestPoint', 'TP5', 'GND', (106.68, 187.96),
                  footprint=FP['TP'], in_bom=False, ref_off=(2.54, -2.54),
                  val_off=(2.54, 0))
    s.wire(tp5['1'], (106.68, GRAIL))

    # ---------------------------------------------------------- output header
    j3 = s.place('Connector_Generic:Conn_01x04', 'J3', 'OUT', (215.9, 95.25),
                 footprint=FP['PH4'], ref_off=(0, -10.16), val_off=(0, 8.89))
    s.wire(j3['1'], (203.2, 92.71))
    vcc((203.2, 92.71))
    s.wire(j3['2'], (203.2, 95.25))
    s.label('OUT1', (203.2, 95.25), justify='right bottom')
    s.wire(j3['3'], (203.2, 97.79))
    s.label('OUT2', (203.2, 97.79), justify='right bottom')
    s.wire(j3['4'], (203.2, 100.33))
    gnd((203.2, 100.33))

    # ------------------------------------------------------------ mounting holes
    for i, (x, y) in enumerate(((228.6, 70.87), (241.3, 70.87),
                                (228.6, 83.57), (241.3, 83.57)), start=1):
        s.place('Mechanical:MountingHole', 'H%d' % i, 'MountingHole', (x, y),
                footprint=FP['MH'], in_bom=False, ref_off=(0, -5.08),
                val_off=(0, 5.08), hide_value=True)

    # ---------------------------------------------------------------- notes
    s.note('2-CHANNEL DCC BLOCK DETECTOR - ACTIVE HIGH', (25.4, 22.86), 2.0)
    s.note('CH1 burden: JP1 OPEN = 1.1k (programming-track ACK)  /  '
           'JP1 FITTED = 1.1k || 110R = 100R (standard track)', (25.4, 27.94))
    s.note('CH2 burden: 100R fixed (standard track only)', (25.4, 31.75))

    notes = [
        'THRESHOLD SET-UP: with the block clear, turn RVn until OUTn just '
        'goes low, then back off ~10%.',
        'Probe TP1/TP3 (VREF) against TP2/TP4 (envelope), ground at TP5.',
        'OUT = HIGH (3.3 V push-pull) when the block is OCCUPIED, '
        'LOW (0 V) when CLEAR.',
        'Envelope decay = R8/R9 x C3/C4 = 100k x 10uF ~= 1 s. '
        'Drop the bleed resistor to 10k for a ~100 ms release.',
        'Hysteresis: Vhyst ~= 3.3 V x Rbleed / Rhyst ~= 33 mV with '
        '100k / 10M. Lower R10/R11 for more.',
        'Board is powered from J3 pin 1 (+3V3) and pin 4 (GND).',
    ]
    for i, txt in enumerate(notes):
        s.note(txt, (176.53, 22.86 + 3.81 * i))

    return s


# ------------------------------------------------------------------ emit file
def emit(s):
    tree = ['kicad_sch',
            ['version', 20260306],
            ['generator', Q('bazauto-gen')],
            ['generator_version', Q('10.0')],
            ['uuid', s.root_uuid],
            ['paper', Q('A4')],
            ['title_block',
             ['title', Q('2-Channel DCC Block Detector (Active High)')],
             ['date', Q('2026-08-26')],
             ['rev', Q('1.0')],
             ['company', Q('bazauto')],
             ['comment', 1, Q('Westgate Hollow layout - CT-based occupancy detection')],
             ['comment', 2, Q('3.3 V single rail, push-pull outputs')]]]

    libnode = ['lib_symbols']
    for lib_id in sorted(s.lib_symbols):
        libnode.append(s.lib_symbols[lib_id])
    tree.append(libnode)

    for (a, b) in s.wires:
        tree.append(['wire',
                     ['pts', ['xy', a[0], a[1]], ['xy', b[0], b[1]]],
                     ['stroke', ['width', 0], ['type', 'default']],
                     ['uuid', det_uuid('wire:%s:%s' % (a, b))]])

    for p in s.junctions():
        tree.append(['junction', ['at', p[0], p[1]], ['diameter', 0],
                     ['color', 0, 0, 0, 0],
                     ['uuid', det_uuid('junc:%s' % (p,))]])

    for i, (text, x, y, ang, just) in enumerate(s.labels):
        tree.append(['label', Q(text), ['at', x, y, ang],
                     ['fields_autoplaced', 'yes'],
                     ['effects', ['font', ['size', 1.27, 1.27]],
                      ['justify'] + just.split()],
                     ['uuid', det_uuid('lbl:%s:%d' % (text, i))]])

    for i, (text, x, y, size) in enumerate(s.texts):
        tree.append(['text', Q(text), ['exclude_from_sim', 'no'],
                     ['at', x, y, 0],
                     ['effects', ['font', ['size', size, size]],
                      ['justify', 'left', 'bottom']],
                     ['uuid', det_uuid('txt:%d' % i)]])

    tree += s.symbols
    tree.append(['sheet_instances', ['path', Q('/'), ['page', Q('1')]]])
    tree.append(['embedded_fonts', 'no'])
    return K.dumps(tree) + '\n'


def emit_symlib(s):
    tree = ['kicad_symbol_lib',
            ['version', 20251024],
            ['generator', Q('bazauto-gen')],
            ['generator_version', Q('10.0')]]
    for lib_id in sorted(s.lib_symbols):
        if not lib_id.startswith(PROJECT + ':'):
            continue
        sym = K.deepcopy(s.lib_symbols[lib_id])
        # Unit sub-symbols already carry the bare name; only the top-level
        # entry drops its library prefix in a standalone .kicad_sym.
        sym[1] = Q(lib_id.split(':', 1)[1])
        tree.append(sym)
    return K.dumps(tree) + '\n'


def main():
    s = build()
    out = os.path.join(HERE, PROJECT + '.kicad_sch')
    with open(out, 'w', encoding='utf-8') as fh:
        fh.write(emit(s))
    print('wrote', out)

    symlib = os.path.join(HERE, PROJECT + '.kicad_sym')
    with open(symlib, 'w', encoding='utf-8') as fh:
        fh.write(emit_symlib(s))
    print('wrote', symlib)

    tbl = os.path.join(HERE, 'sym-lib-table')
    with open(tbl, 'w', encoding='utf-8') as fh:
        fh.write(K.dumps(
            ['sym_lib_table',
             ['version', 7],
             ['lib', ['name', Q(PROJECT)], ['type', Q('KiCad')],
              ['uri', Q('${KIPRJMOD}/%s.kicad_sym' % PROJECT)],
              ['options', Q('')],
              ['descr', Q('Project symbols (ordered TI parts)')]]]) + '\n')
    print('wrote', tbl)

    print('symbols placed: %d   wires: %d   junctions: %d   labels: %d' %
          (len(s.symbols), len(s.wires), len(s.junctions()), len(s.labels)))


if __name__ == '__main__':
    main()
