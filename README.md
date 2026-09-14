# 2-Channel DCC Block Detector (Active High)

CT-based occupancy detection for the Westgate Hollow layout. Two independent
channels, each turning the current in an external current transformer into a
push-pull logic level: **HIGH (3.3 V) = block occupied, LOW (0 V) = clear**.

Single +3.3 V rail, fed in through the output header. Board is **48 × 38 mm**,
2 layers, four M2 mounting holes.

## Why build this

**So that a broken cable or connection under the layout doesn't register as a
clear block.**

The off-the-shelf detectors used so far are active low: they pull their output to
0 V when a block is occupied, and leave it open when clear. The feedback node's
inputs are pulled up, so a broken wire floats high, and that reads exactly like a
clear block, the permissive state (`bazauto/layout-feedback#9`).

This board is **active high**: occupied drives 3.3 V, clear drives 0 V. A broken
wire into a pulled-up input now floats to the *occupied* side.

## Status

**Revision 1.0: 10 boards ordered from PCBWay, awaiting delivery.** Nothing has
been measured on hardware yet.

---

## Files

| File | What it is |
|---|---|
| `bazauto-block-detection.kicad_sch` | Schematic (KiCad 10 format) |
| `bazauto-block-detection.kicad_pcb` | 2-layer PCB, fully routed |
| `bazauto-block-detection.kicad_sym` | Project symbols: `TLV9002IDGKR`, `TLV3212IDGKR` |
| `sym-lib-table` / `fp-lib-table` | Library tables (project-local symbols, ProtoFlow footprints) |
| `bom.csv` | Bill of materials, grouped |
| `BOM_PCBWay_bazauto-block-detection.xlsx` | `bom.csv` poured into PCBWay's template, ready to upload |
| `scripts/` | Generators and checkers — see [Regenerating](#regenerating) |

Everything else (resistors, caps, diodes, connectors, trimmers) comes from the
stock KiCad 10 libraries, so the project opens on any standard install.

---

## Circuit

Each channel is the same chain:

```
CT ─ terminal block ─ burden ─ ESD clamp ─ 1k ─ precision peak detector ─ comparator ─ OUT
     J1 / J2          R1,R2,R3  D1 / D2   R4/R5   U1 + D3/D4 + C3/C4 + R8/R9   U2      J3
                      + JP1
```

**Burden.** The CT secondary is loaded across the input terminals.
Channel 1 is switchable, channel 2 is fixed:

| Channel | JP1 | Burden | Use |
|---|---|---|---|
| 1 | open | 1.1 kΩ | Programming track (service-mode ACK pulse) |
| 1 | fitted | 1.1 k ∥ 110 R = **100.0 Ω** | Standard track |
| 2 | — | 100 Ω fixed | Standard track only |

The parallel combination is exact: 1100 × 110 / 1210 = 100.0 Ω.

**Clamp.** D1/D2 (BAT54S, series pair) clamp the input to roughly −0.3 V /
+3.6 V. R4/R5 (1 k) then limit the current into the op-amp's input structure on
the negative half-cycle — the CT output is bipolar and a single-supply op-amp
input sits at the very edge of its absolute maximum without them.

**Peak detector.** The op-amp drives D3/D4 with the diode *inside* the feedback
loop, so the forward drop is divided out by the loop gain — no 0.6 V loss on a
signal this small. R6/R7 (100 Ω) sit between the op-amp output and the diode:
they are inside the loop too, and stop the RRIO output from ringing into the
10 µF hold capacitor. C3/C4 hold the envelope, R8/R9 bleed it away.

**Comparator.** The envelope goes to +IN, the trimmer wiper to −IN, and the
push-pull output drives the header directly. R10/R11 (10 M) add positive
feedback so the output does not chatter as the envelope crosses the threshold.

---

## Setting up

Time constants and tuning, all measurable on the board:

- **Release time.** R8/R9 × C3/C4 = 100 kΩ × 10 µF ≈ **1 s** to decay. That
  doubles as debounce for dirty wheels. For a faster release drop the bleed
  resistor — 10 k gives ≈ 100 ms.
- **Hysteresis.** V_hyst ≈ 3.3 V × R_bleed / R_hyst = 3.3 × 100 k / 10 M
  ≈ **33 mV**. Lower R10/R11 for more.
- **Threshold.** With the block clear, turn RVn until OUTn just goes low, then
  back off about 10 %.

Test points, all on the top side:

| TP | Net | Use |
|---|---|---|
| TP1 / TP3 | VREF1 / VREF2 | Trimmer wiper — the threshold you have dialled in |
| TP2 / TP4 | ENV1 / ENV2 | Peak-detector output — the rectified envelope |
| TP5 | GND | Scope ground |

---

## ⚠ Known concerns with revision 1.0

**1. The signal chain has no gain, and that makes the threshold hard to set.**

This is the one thing worth changing. The detector is a unity-gain rectifier, so
the comparator threshold has to be set in the millivolt region. With a 1:100 CT
and a 100 Ω burden, 10 mA of track current gives about 10 mV at the envelope
node. The trimmer spans the full 0–3.3 V across 10 kΩ, so 10 mV is **0.3 % of
its travel** — a fraction of one turn on a 12-turn trimmer — and it is the same
order as the comparator's own input offset voltage. Setting it repeatably will
be unpleasant, and it will drift.

The cheap fix is one resistor: put ~330 kΩ in series between +3V3 and the top of
each trimmer (RV1 pin 1, RV2 pin 1). The wiper then covers roughly 0–100 mV
instead of 0–3.3 V, giving about 30× the resolution and swamping nothing else.
The alternative is to give the op-amp stage gain instead of running it at unity.

**Revision 1.0, as ordered, does not include this change** (there is no 330 kΩ
part in `bom.csv`). Sizing it properly needs the CT's actual turns ratio. It
affects two nets and about 4 mm of track.

**2. Verify the TLV3212IDGKR pinout against the datasheet.** The comparator
symbol uses the industry-standard 8-pin dual layout — 1=OUTA, 2=INA−, 3=INA+,
4=GND, 5=INB+, 6=INB−, 7=OUTB, 8=V+ — which is what TLV3202IDGKR uses in the
same DGK package. I could not confirm TLV3212's pin assignment from a datasheet
in this session. **TLV3202IDGKR is a verified drop-in** if you would rather not
check. Same for TLV9002IDGKR, though that one follows the universal dual-op-amp
pinout and is not in doubt.

**3. AGND is the plane, not a separate net.** The spec asked for the filter
returns to go to AGND *and* for a solid, unbroken ground plane. Those pull in
opposite directions — a genuine second net needs a split, and a split is exactly
what section 6 forbids. I used one continuous GND pour and kept the analog
returns physically local instead: C3/C4 and R8/R9 ground through their own vias
straight into the plane, a few millimetres from the op-amp's own ground via.

---

## Layout

- **B.Cu is a ground pour.** F.Cu carries the signals plus a second GND pour in
  the gaps. 30 ground vias tie the two together: 16 taking SMD ground pads
  straight down to the plane, 14 stitching the pours across the board.
- **+3V3** runs as a perimeter ring (top edge, right edge, bottom edge) with a
  spine threaded through the gap between the two pad rows of U1 and U2, so it
  never crosses a channel's signal path.
- The two channels are mirrored top and bottom about the board centreline, with
  the shared dual op-amp and comparator between them. Both ICs are rotated so
  channel A faces the top band and channel B the bottom.
- 0.1 µF decoupling (C1, C2) sits against each IC's V+ pin; C5 is the 10 µF bulk.

**Where the ground plane is interrupted.** Four short bottom-layer hops let
crossing nets pass each other, 8.60 mm of track in total on a 1824 mm² board:

| Net | From → to | Length |
|---|---|---|
| +3V3 | (20.20, 22.00) → (20.20, 24.00) | 2.00 mm |
| /OUT1 | (42.20, 18.30) → (43.80, 18.30) | 1.60 mm |
| /OUT2 | (31.90, 22.60) → (33.45, 22.60) | 1.55 mm |
| OA2 out | (21.50, 22.75) → (21.50, 26.20) | 3.45 mm |

`scripts/check_plane.py` audits this and reports which analog nets pass over a
void. Current result: **the CT input rails, both op-amp inputs, ENV1 and VREF1
have completely unbroken copper beneath them.** Four crossings remain, all in
channel 2's middle band — ENV2 twice, VREF2 once, channel 2's op-amp output
once — and in each the trace crosses a void under 1 mm wide. Those nets carry a
rectified DC envelope and a DC threshold reference, where a sub-millimetre
detour in the return path at DCC frequencies is not a real effect. If you want them gone, the honest fix is a 4-layer stack-up, not
more clever 2-layer routing.

One placement change from your version: **C1 moved 0.65 mm right** (to x = 23.45)
so that channel 2's feedback trace and op-amp output each get their own corridor
past it. Everything else is where you left it.

---

## Regenerating

Run with KiCad's bundled Python, from the project directory:

```sh
K="C:/Program Files/KiCad/10.0"

python scripts/gen_schematic.py         # schematic + project symbol lib
python scripts/verify_netlist.py        # netlist vs. design intent
"$K/bin/python.exe" scripts/route_pcb.py    # routing + pours (placement is preserved)
"$K/bin/python.exe" scripts/check_board.py  # placement + board-vs-schematic nets
"$K/bin/python.exe" scripts/check_plane.py  # ground-plane audit
```

`route_pcb.py` loads the existing board, so hand-adjusted placement and
silkscreen survive; it only rebuilds tracks, vias and zones.

| Script | Does |
|---|---|
| `gen_schematic.py` | Builds the schematic from real KiCad library symbols; wires are computed from actual pin coordinates |
| `kicadlib.py` | S-expression reader/writer and symbol-library helpers |
| `probe_transform.py` | Derives KiCad's symbol placement transform empirically from its own demo files |
| `verify_netlist.py` | Compares the extracted netlist against the intended one, net by net |
| `route_pcb.py` | Routing, ground pours, silkscreen legends |
| `check_board.py` | Courtyard overlaps, off-board parts, board nets vs. schematic |
| `check_plane.py` | Bottom-layer voids and which analog nets cross them |
| `make_pcbway_bom.py` | Fills PCBWay's BOM template; fails if it has drifted from `bom.csv` |

---

## Verification

Everything below was run against the files in this directory:

```
kicad-cli sch erc            0 errors, 0 warnings
verify_netlist.py            all 17 nets match design intent, no unconnected pins
kicad-cli pcb drc            0 violations, 0 unconnected items
check_board.py               37 footprints, 0 problems (no overlaps, nets match schematic)
check_plane.py               8.60 mm bottom-layer track; 4 analog crossings (see above)
```

CI re-runs the two `kicad-cli` checks on every pull request (see
`.github/workflows/ci.yml`). DRC there runs with `--schematic-parity` at error
severity. At warning severity the parity check reports 80 cosmetic mismatches:
footprints saved without their library prefix, and field text such as a
Datasheet of `''` against `~`. None is a net or connection mismatch.

Gerbers and drill files for revision 1.0 are in the project root, with the same
set zipped as `bazauto-block-detection.zip`. Nothing has been measured on
hardware yet. The threshold-resolution concern above is analysis, not a bench
result.
