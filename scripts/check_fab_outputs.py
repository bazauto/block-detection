"""Check that the newest fabrication revision under fab/ matches the board it claims to come from.

Each fab/rev-X.Y/ folder holds a SOURCE.txt recording the SHA-256 of the board file its outputs were
generated from (line endings normalised to LF, so a Windows checkout hashes the same as CI's Linux one).

  - Board unchanged since that revision: regenerate Gerbers, drill files and the position file with
    kicad-cli, and fail if the committed copies differ, or if the zipped Gerber set disagrees with the
    loose files. Gerbers are compared by the geometry they draw, because KiCad's primitive order is not
    stable between plots; drill, job and position files by their lines, less timestamps.
  - Board changed since then: work towards the next revision is in progress, so report that and pass.
    The committed outputs are a record of the revision that was sent to fab, not of the current board.

Usage:
  python scripts/check_fab_outputs.py                 check the newest revision
  python scripts/check_fab_outputs.py --record rev-1.1   write fab/rev-1.1/SOURCE.txt from the current board

kicad-cli is found on PATH, or set KICAD_CLI to its full path.
Plain Python 3 standard library; no pcbnew needed.
"""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT = 'bazauto-block-detection'
PCB = os.path.join(HERE, PROJECT + '.kicad_pcb')
FAB = os.path.join(HERE, 'fab')

# Lines that legitimately change between otherwise identical plots.
VOLATILE = ('CreationDate', 'G04 Created by', 'DRILL file', 'TF.GenerationSoftware',
            'TF.ProjectId', '"Version"')


def kicad_cli():
    exe = os.environ.get('KICAD_CLI') or shutil.which('kicad-cli')
    if not exe:
        sys.exit('kicad-cli not found: put it on PATH or set KICAD_CLI')
    return exe


def board_sha256():
    with open(PCB, 'rb') as f:
        return hashlib.sha256(f.read().replace(b'\r\n', b'\n')).hexdigest()


def kicad_version(cli):
    out = subprocess.run([cli, 'version'], capture_output=True, text=True, check=True).stdout.strip()
    return out.splitlines()[-1] if out else 'unknown'


def newest_revision():
    revs = []
    for name in os.listdir(FAB) if os.path.isdir(FAB) else []:
        m = re.fullmatch(r'rev-(\d+)\.(\d+)', name)
        if m and os.path.isdir(os.path.join(FAB, name)):
            revs.append(((int(m.group(1)), int(m.group(2))), name))
    if not revs:
        sys.exit('no fab/rev-X.Y/ folders found')
    return max(revs)[1]


def read_source(rev_dir):
    path = os.path.join(rev_dir, 'SOURCE.txt')
    if not os.path.exists(path):
        sys.exit('%s is missing; create it with --record' % os.path.relpath(path, HERE))
    fields = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            if ':' in line and not line.lstrip().startswith('#'):
                key, value = line.split(':', 1)
                fields[key.strip()] = value.strip()
    if 'board-sha256' not in fields:
        sys.exit('%s has no board-sha256 line' % os.path.relpath(path, HERE))
    return fields


def normalise(data):
    text = data.decode('utf-8', errors='replace').replace('\r\n', '\n')
    return [ln for ln in text.split('\n') if not any(v in ln for v in VOLATILE)]


COORD = re.compile(r'([XYIJ])(-?\d+)')


def gerber_geometry(data):
    """What a Gerber file draws, independent of the order it is written in.

    KiCad does not emit primitives in a stable order: two plots of an unchanged board can list the
    same silkscreen strokes in a different sequence. So compare the multiset of drawn primitives
    instead of the text: every draw (D01), flash (D03) and region contour, each keyed by its polarity
    and by the aperture *definition* it uses rather than the aperture number. Coordinates are the
    file's own integers, so there is no rounding. Aperture macros are compared as a set.
    """
    from collections import Counter
    text = data.decode('utf-8', errors='replace').replace('\r\n', '').replace('\n', '')
    tokens = re.findall(r'%[^%]*%|[^%*]*\*', text)

    apertures, macros, prims = {}, set(), Counter()
    aperture, mode, polarity = None, 'G01', 'D'
    x = y = 0
    in_region, contour = False, []

    def close_contour():
        if contour:
            prims[('region', polarity, frozenset(contour))] += 1
            contour.clear()

    for tok in tokens:
        if tok.startswith('%'):
            body = tok.strip('%')
            if body.startswith('ADD'):
                m = re.match(r'ADD(\d+)(.*)\*$', body, re.S)
                if m:
                    apertures[m.group(1)] = m.group(2)
            elif body.startswith('AM'):
                macros.add(body)
            elif body.startswith('LP'):
                polarity = body[2:3]
            continue

        stmt = tok.rstrip('*').strip()
        if not stmt or stmt.startswith('G04'):
            continue
        for g in re.findall(r'G0?([123]|36|37)(?!\d)', stmt):
            if g in ('1', '2', '3'):
                mode = 'G0' + g
            elif g == '36':
                in_region, contour = True, []
            elif g == '37':
                close_contour()
                in_region = False
        dsel = re.fullmatch(r'(?:G54)?D(\d{2,})', stmt)
        if dsel and int(dsel.group(1)) >= 10:
            aperture = apertures.get(dsel.group(1), 'D' + dsel.group(1))
            continue

        dop = re.search(r'D0?([123])$', stmt)
        if not dop:
            continue
        coords = dict((k, int(v)) for k, v in COORD.findall(stmt))
        nx, ny = coords.get('X', x), coords.get('Y', y)
        op = dop.group(1)
        if op == '1':
            if mode == 'G01':
                seg = ('line', frozenset(((x, y), (nx, ny))))
            else:
                seg = ('arc', mode, (x, y), (nx, ny), coords.get('I', 0), coords.get('J', 0))
            if in_region:
                contour.append(seg)
            else:
                prims[('draw', polarity, aperture) + seg] += 1
        elif op == '2':
            if in_region:
                close_contour()
        elif op == '3':
            prims[('flash', polarity, aperture, (nx, ny))] += 1
        x, y = nx, ny

    return prims, frozenset(macros)


def outputs_match(name, committed, regenerated):
    if name.endswith('.gbr'):
        return gerber_geometry(committed) == gerber_geometry(regenerated)
    return normalise(committed) == normalise(regenerated)


def generate(cli, out):
    common = dict(check=True, capture_output=True, text=True)
    subprocess.run([cli, 'pcb', 'export', 'gerbers', '--board-plot-params', '-o', out + os.sep, PCB], **common)
    subprocess.run([cli, 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th',
                    '-o', out + os.sep, PCB], **common)
    subprocess.run([cli, 'pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both',
                    '-o', os.path.join(out, PROJECT + '-all-pos.csv'), PCB], **common)


def is_output(name):
    return name.endswith(('.gbr', '.drl', '.gbrjob')) or name.endswith('-all-pos.csv')


def record(rev):
    cli = kicad_cli()
    rev_dir = os.path.join(FAB, rev)
    os.makedirs(rev_dir, exist_ok=True)
    with open(os.path.join(rev_dir, 'SOURCE.txt'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('# Written by scripts/check_fab_outputs.py --record. The board these outputs were generated from.\n')
        f.write('revision: %s\n' % rev)
        f.write('board: %s.kicad_pcb\n' % PROJECT)
        f.write('board-sha256: %s\n' % board_sha256())
        f.write('generated-with: KiCad %s\n' % kicad_version(cli))
    print('recorded %s' % os.path.relpath(os.path.join(rev_dir, 'SOURCE.txt'), HERE))


def check():
    rev = newest_revision()
    rev_dir = os.path.join(FAB, rev)
    source = read_source(rev_dir)
    current = board_sha256()

    if current != source['board-sha256']:
        msg = ('board has changed since %s was generated; its outputs are that revision\'s record, '
               'not the current board. Not comparing.' % rev)
        print(('::notice::' if os.environ.get('GITHUB_ACTIONS') else '') + msg)
        return 0

    cli = kicad_cli()
    problems = []
    with tempfile.TemporaryDirectory() as tmp:
        generate(cli, tmp)
        committed = sorted(n for n in os.listdir(rev_dir) if is_output(n))
        regenerated = sorted(n for n in os.listdir(tmp) if is_output(n))

        for name in sorted(set(regenerated) - set(committed)):
            problems.append('missing from %s: %s' % (rev, name))
        for name in sorted(set(committed) - set(regenerated)):
            problems.append('in %s but not produced by the board: %s' % (rev, name))
        for name in sorted(set(committed) & set(regenerated)):
            with open(os.path.join(rev_dir, name), 'rb') as a, open(os.path.join(tmp, name), 'rb') as b:
                if not outputs_match(name, a.read(), b.read()):
                    problems.append('stale: %s differs from what the board produces' % name)

        zips = [n for n in os.listdir(rev_dir) if n.endswith('.zip')]
        for z in zips:
            with zipfile.ZipFile(os.path.join(rev_dir, z)) as zf:
                for entry in zf.namelist():
                    loose = os.path.join(rev_dir, entry)
                    if not os.path.exists(loose):
                        problems.append('%s contains %s, which is not in %s' % (z, entry, rev))
                    else:
                        with open(loose, 'rb') as f:
                            if not outputs_match(entry, zf.read(entry), f.read()):
                                problems.append('%s: %s differs from the loose copy' % (z, entry))

    print('%s: board matches SOURCE.txt; compared %d output files and %d zip(s)' % (rev, len(committed), len(zips)))
    if problems:
        for p in problems:
            print('  ' + p)
        return 1
    print('  all outputs match the board')
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--record', metavar='REV', help='write fab/REV/SOURCE.txt from the current board, e.g. rev-1.1')
    args = ap.parse_args()
    if args.record:
        if not re.fullmatch(r'rev-\d+\.\d+', args.record):
            sys.exit('revision must look like rev-1.1')
        record(args.record)
        return 0
    return check()


if __name__ == '__main__':
    sys.exit(main())
