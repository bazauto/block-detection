"""Populate PCBWay's BOM template from the project BOM.

Reads Sample_BOM_PCBWay.xlsx, rewrites only xl/worksheets/sheet1.xml, and
writes BOM_PCBWay_bazauto-block-detection.xlsx. Every other part of the
workbook (styles, the embedded PCBWay logo, the hyperlink rows) is copied
through byte-for-byte, so the file still looks like their template.

The line-item table below is curated -- descriptions and manufacturer part
numbers are not derivable from the schematic. It is cross-checked against
bom.csv on every run: if a designator appears, disappears or changes value in
the schematic BOM, this script fails rather than shipping a stale BOM.

    python scripts/make_pcbway_bom.py
"""
import csv
import os
import re
import shutil
import sys
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(HERE, 'Sample_BOM_PCBWay.xlsx')
BOM_CSV = os.path.join(HERE, 'bom.csv')
OUT = os.path.join(HERE, 'BOM_PCBWay_bazauto-block-detection.xlsx')

GENERIC = 'Any - spec in Description'

# designators, qty, manufacturer, mfg part #, description, package, type, notes
LINES = [
    ('C1,C2', 2, 'Any', GENERIC,
     'CAP CER 100NF 25V MIN X7R 0805', '0805', 'SMD',
     'Decoupling, one per IC'),
    ('C3,C4,C5', 3, 'Any', GENERIC,
     'CAP CER 10UF 25V X5R OR X7R 0805', '0805', 'SMD',
     'C3/C4 set envelope decay with R8/R9; C5 is bulk'),
    ('D1,D2', 2, 'Nexperia or equiv', 'BAT54S',
     'DIODE SCHOTTKY DUAL SERIES 30V 200MA SOT-23', 'SOT-23', 'SMD',
     'Input rail clamp - series pair, not common cathode'),
    ('D3,D4', 2, 'Any', '1N4148W',
     'DIODE SWITCHING 100V 300MA SOD-123', 'SOD-123', 'SMD',
     'Rectifier, sits inside the op-amp feedback loop'),
    ('J1,J2', 2, 'Phoenix Contact', 'PT 1,5/2-3,5-H',
     'TERM BLOCK 2POS 3.5MM PITCH THT', '3.5mm 2POS', 'thru-hole',
     'CT inputs. Generic 3.5mm 2-pos block is an acceptable substitute'),
    ('J3', 1, 'Any', GENERIC,
     'HEADER 1X4 2.54MM VERT PIN', '1X04 2.54MM', 'thru-hole',
     'Supply and outputs: 1=+3V3 2=OUT1 3=OUT2 4=GND'),
    ('JP1', 1, 'Any', GENERIC,
     'HEADER 1X2 2.54MM VERT PIN', '1X02 2.54MM', 'thru-hole',
     'Burden mode select - needs a 2.54mm jumper shunt (not fitted by PCBWay)'),
    ('R1', 1, 'Any', GENERIC,
     'RES 1.1K OHM 1% 0.25W 1206', '1206', 'SMD',
     'CH1 burden, programming-track leg'),
    ('R2', 1, 'Any', GENERIC,
     'RES 110 OHM 1% 0.25W 1206', '1206', 'SMD',
     'CH1 burden, standard-track leg via JP1'),
    ('R3', 1, 'Any', GENERIC,
     'RES 100 OHM 1% 0.25W 1206', '1206', 'SMD',
     'CH2 burden, fixed'),
    ('R4,R5', 2, 'Any', GENERIC,
     'RES 1K OHM 1% 0.125W 0805', '0805', 'SMD',
     'Op-amp input current limit'),
    ('R6,R7', 2, 'Any', GENERIC,
     'RES 100 OHM 1% 0.125W 0805', '0805', 'SMD',
     'Output isolation, inside the feedback loop'),
    ('R8,R9', 2, 'Any', GENERIC,
     'RES 100K OHM 1% 0.125W 0805', '0805', 'SMD',
     'Envelope bleed - sets the ~1s release time'),
    ('R10,R11', 2, 'Any', GENERIC,
     'RES 10M OHM 5% 0.125W 0805', '0805', 'SMD',
     'Comparator hysteresis, ~33mV'),
    ('RV1,RV2', 2, 'Bourns', '3269W-1-103LF',
     'TRIMMER 10K OHM 0.25W SMD MULTI-TURN', '3269W', 'SMD',
     'Threshold set. CONFIRM exact order code suffix'),
    ('U1', 1, 'Texas Instruments', 'TLV9002IDGKR',
     'IC OPAMP DUAL RRIO 1MHZ VSSOP-8', 'VSSOP-8 (DGK)', 'SMD',
     'Precision peak detector'),
    ('U2', 1, 'Texas Instruments', 'TLV3212IDGKR',
     'IC COMPARATOR DUAL PUSH-PULL VSSOP-8', 'VSSOP-8 (DGK)', 'SMD',
     'Alt: TLV7012DGKR (pin-to-pin). VERIFY TLV3212 pinout before ordering'),
]

TITLE = 'bazauto-block-detection Rev 1.0 - 2-Channel DCC Block Detector - BOM'

FIRST_ROW = 7
STYLES = ['9', '10', '9', '10', '10', '11', '11', '12', '12']


def expand(designators):
    """'C3,C4,C5' -> ['C3','C4','C5'];  'C3-C5' -> ['C3','C4','C5']"""
    out = []
    for part in designators.split(','):
        part = part.strip()
        m = re.match(r'^([A-Za-z]+)(\d+)-(?:([A-Za-z]+))?(\d+)$', part)
        if m:
            pre, lo, hi = m.group(1), int(m.group(2)), int(m.group(4))
            out += ['%s%d' % (pre, n) for n in range(lo, hi + 1)]
        elif part:
            out.append(part)
    return out


def check_against_bom():
    """Fail loudly if the schematic BOM and this table have drifted apart."""
    with open(BOM_CSV, newline='', encoding='utf-8-sig') as fh:
        rows = list(csv.DictReader(fh))
    from_csv = {}
    for r in rows:
        for d in expand(r['Refs']):
            from_csv[d] = r['Value']
    from_table = {}
    for line in LINES:
        for d in expand(line[0]):
            if d in from_table:
                raise SystemExit('designator %s listed twice in LINES' % d)
            from_table[d] = line

    problems = []
    for d in sorted(set(from_csv) - set(from_table)):
        problems.append('  in bom.csv but missing here: %s (%s)' % (d, from_csv[d]))
    for d in sorted(set(from_table) - set(from_csv)):
        problems.append('  listed here but not in bom.csv: %s' % d)
    for d, line in sorted(from_table.items()):
        if d in from_csv and expand(line[0]) and len(expand(line[0])) != line[1]:
            problems.append('  %s: qty %d but %d designators'
                            % (line[0], line[1], len(expand(line[0]))))
    if problems:
        raise SystemExit('BOM mismatch:\n' + '\n'.join(sorted(set(problems))))
    return len(from_csv)


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;'))


def build_rows():
    xml = []
    for i, line in enumerate(LINES):
        r = FIRST_ROW + i
        designators, qty = line[0], line[1]
        values = [str(i + 1), designators, str(qty)] + list(line[2:])
        cells = []
        for col, (letter, val) in enumerate(zip('ABCDEFGHI', values)):
            s = STYLES[col]
            if letter in ('A', 'C'):            # numeric columns
                cells.append('<c r="%s%d" s="%s"><v>%s</v></c>' % (letter, r, s, val))
            else:
                cells.append('<c r="%s%d" s="%s" t="inlineStr"><is><t xml:space='
                             '"preserve">%s</t></is></c>' % (letter, r, s, esc(val)))
        xml.append('<row r="%d" spans="1:9">%s</row>' % (r, ''.join(cells)))
    return ''.join(xml)


def main():
    if not os.path.exists(TEMPLATE):
        raise SystemExit('template not found: %s' % TEMPLATE)
    n = check_against_bom()

    with zipfile.ZipFile(TEMPLATE) as zin:
        sheet = zin.read('xl/worksheets/sheet1.xml').decode('utf-8')
        names = zin.namelist()
        blobs = {name: zin.read(name) for name in names}

    head, rest = sheet.split('<sheetData>', 1)
    body, tail = rest.split('</sheetData>', 1)

    keep = []
    for row in re.findall(r'<row.*?</row>', body, re.S):
        r = int(re.match(r'<row r="(\d+)"', row).group(1))
        if r < FIRST_ROW or r >= 24:        # header block and footer rows
            keep.append((r, row))
    new_rows = build_rows()
    before = ''.join(row for r, row in keep if r < FIRST_ROW)
    after = ''.join(row for r, row in keep if r >= 24)

    last = FIRST_ROW + len(LINES) - 1
    if last >= 24:
        raise SystemExit('too many lines for the template footer at row 24')
    head = re.sub(r'<dimension ref="[^"]*"/>', '<dimension ref="A2:I26"/>', head)

    # replace the template's "xxxx xxxx xxxxx xxPCS BOM" placeholder title
    before = re.sub(r'<c r="D2"[^>]*?(?:/>|>.*?</c>)',
                    '<c r="D2" s="5" t="inlineStr"><is><t>%s</t></is></c>' % esc(TITLE),
                    before, count=1, flags=re.S)
    sheet = head + '<sheetData>' + before + new_rows + after + '</sheetData>' + tail

    blobs['xl/worksheets/sheet1.xml'] = sheet.encode('utf-8')
    tmp = OUT + '.tmp'
    with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
        for name in names:
            zout.writestr(name, blobs[name])
    shutil.move(tmp, OUT)

    print('%s' % os.path.basename(OUT))
    print('  %d line items, %d components (checked against bom.csv)'
          % (len(LINES), n))
    print('  rows %d-%d; template header, styles, logo and footer preserved'
          % (FIRST_ROW, last))


if __name__ == '__main__':
    sys.exit(main())
