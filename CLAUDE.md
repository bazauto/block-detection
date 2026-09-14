# Block Detection — Working Agreement

KiCad 10 design for a two-channel DCC block detector for the Westgate Hollow layout: CT → burden →
clamp → precision peak detector → comparator → **active-high** push-pull output (occupied = 3.3 V,
clear = 0 V). Plus a 3D-printed DIN-rail enclosure. `README.md` is the design record: circuit, tuning,
known concerns, verification, fabrication revisions, licence.

**Why it exists, and why that matters when changing it.** The off-the-shelf detectors are active low
into pulled-up expander inputs, so a broken wire under the layout reads as a *clear* block
(`bazauto/layout-feedback#9`). This board exists so that the same fault reads as *occupied*. Any
change that could let a wiring fault read as clear defeats the point of the board. Say so explicitly
rather than trading it away quietly.

## Status

Revision 1.0: 10 boards ordered from PCBWay (2026-09), **not yet received or bench-tested**. Nothing in
this repo is a measured result. The threshold-resolution concern in the README is analysis. Do not
describe the design as working or verified on hardware until the owner has tested it.

## Layout

```
bazauto-block-detection.kicad_{pro,sch,pcb,sym}   KiCad project; must stay together in the root
sym-lib-table                                      project symbol library (no fp-lib-table: none needed)
bom.csv                                            BOM source of truth
fab/rev-X.Y/                                       outputs as sent to fab, one folder per revision
enclosure/                                         OpenSCAD source, STLs, previews, check_fit.py
scripts/                                           generators and checkers (see README "Regenerating")
```

## Commands

```powershell
$K = 'C:\Program Files\KiCad\10.0'
& "$K\bin\kicad-cli.exe" sch erc --exit-code-violations --severity-all bazauto-block-detection.kicad_sch
& "$K\bin\kicad-cli.exe" pcb drc --exit-code-violations --schematic-parity --severity-error bazauto-block-detection.kicad_pcb
$env:KICAD_CLI = "$K\bin\kicad-cli.exe"; python scripts\check_fab_outputs.py
```

These are exactly what CI runs (`.github/workflows/ci.yml`, job `ERC and DRC`, required on `main`).
Run them before a PR, and quote the real output.

## Rules

1. **Never commit `PCBWay/`.** It holds the proforma invoice, quotations and order files, which carry
   personal and payment details. It is git-ignored; keep it that way. The same goes for PCBWay's BOM
   template (`Sample_BOM_PCBWay.xlsx`) and the generated `BOM_PCBWay_*.xlsx`: PCBWay's file, with no
   licence to redistribute.
2. **A `fab/rev-X.Y/` folder is a historical record and is never regenerated in place.** A design change
   that goes to fab gets a new revision folder, `SOURCE.txt` via `check_fab_outputs.py --record`, and a
   `rev-X.Y` tag on the merge commit. The procedure is in the README.
3. **KiCad is pinned to 10.0.5** in CI, the release the board was designed in. A different release
   can move the rule set. Bump it deliberately, in its own PR, and re-check ERC/DRC output.
4. **DRC gates on errors, not warnings, on purpose.** The board carries 80 warning-level
   schematic-parity mismatches from being script-generated: footprints saved without their library
   prefix, and Datasheet `''` against `~`. None is a net or connection mismatch. Do not "fix" CI by
   lowering ERC to errors; ERC is clean at every severity and stays that way.
5. **`route_pcb.py` preserves hand placement and silkscreen**; it rebuilds only tracks, vias and zones.
   `gen_schematic.py` regenerates the schematic *and* `bazauto-block-detection.kicad_sym`.
6. **Licensing is split**: the design is CERN-OHL-P-2.0 (`LICENSE`), and `scripts/` plus
   `enclosure/check_fit.py` are MIT (`LICENSE-MIT`). The two project symbols are derived from stock
   KiCad symbols and are attributed in `THIRD-PARTY-NOTICES.md`. Keep that file current if more are
   derived.
7. **Docs move with the design, in the same PR.** If a change falsifies the README's circuit
   description, BOM, tuning numbers or verification block, fix it in the same branch.

## Cross-repo

- **`bazauto/layout-feedback`** reads these outputs on MCP23017 inputs. Its `config.py` has a single
  global `ACTIVE_LOW = True` covering every sensor, because today's detectors are active low. Fitting
  this board means that flag has to become per-sensor there. That change belongs in `layout-feedback`,
  not here.
- **`bazauto/bazauto-website`** has the Block Detector project page and the "Build our own active-high
  block detector" decision record. Update them when the status changes (boards received, bench results,
  a new revision).
