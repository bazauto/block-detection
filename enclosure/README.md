# Enclosure — 2-Channel DCC Block Detector

3D-printed DIN-rail box for the 48 × 38 mm block-detector PCB in the parent
directory. Three parts, all printable without supports.

**Outer size 62.0 × 52.0 × 32.6 mm**, plus the rail clip underneath.

| Part | STL | Prints |
|---|---|---|
| Box body | `stl/block-detector-base.stl` | floor down, as modelled |
| Lid | `stl/block-detector-lid.stl` | outside face down, as modelled |
| DIN TH35 clip | `stl/block-detector-clip.stl` | mating face down, as modelled |

Everything comes from one parametric source, `block-detector-enclosure.scad`.
`check_fit.py` audits the clearances against the actual KiCad board.

---

## How it goes together

The rail runs along the box's **52 mm axis**, so modules stack side by side
along the rail and every cable leaves through an end wall, not into the
neighbouring module.

- **Left wall** — two slots, one per CT terminal block. J1/J2 are Phoenix PT
  push-in blocks with the wire entry facing the wall, 5 mm behind it. Thread
  the CT leads through the slot before landing them.
- **Right wall** — one slot for the OUT cable, sitting high enough that the
  1×4 housing on J3 passes underneath it and the wires turn out over the top.
- **Board** sits on four 5 mm standoffs, 7 mm above the floor, screwed down at
  its own M2 holes. 22 mm of clear height above it.
- **Lid** has a register lip and four countersunk M3 screws into corner posts.
  Solid — take it off to set the thresholds on RV1/RV2 or move the MODE jumper.

### Hardware

| Qty | Screw | Into |
|---|---|---|
| 4 | M3 × 10 countersunk, self-tapping | lid → corner posts (2.5 mm pilot) |
| 4 | M2 × 6 pan head, self-tapping | board → standoffs (1.6 mm pilot) |
| 2 | M3 × 8 countersunk, self-tapping | DIN clip → box floor (2.5 mm pilot) |

Plain machine screws work as well as self-tappers — they cut their own thread
in the printed pilot holes. Do not over-torque the M2s; the standoffs are
5 mm tall and 5 mm across.

### The DIN clip

Screws to the outside of the box floor, so the box can be re-mounted flat later
by printing a different back plate. One hook is fixed, the other is a 35 mm
spring tongue with a release tab at one end — hook the fixed side over the rail
first, then push until the tongue snaps home. To remove, lever the tab away
from the rail with a small screwdriver.

The channel is 34.6 mm across a 35 mm rail, so the tongue is preloaded and the
module does not rattle. Clipping on needs 2.2 mm of tongue throw.

**Print the clip in PETG** if you have it. The tongue is a living spring and PLA
loses that over time.

---

## Print settings

0.2 mm layers, 3 perimeters, 4 top/bottom, 30 % infill. No supports on any part
— every overhang is either a 45° chamfer or a bridge under 13 mm.

The lid is designed to print with the **outside face on the bed**, so the
lettering is engraved rather than raised and comes out crisp on the first
layers. The `part="lid"` and `part="clip"` outputs are already in their print
orientation; drop the STLs straight into the slicer.

---

## Re-cutting the model

```sh
SCAD="/c/Program Files/OpenSCAD/openscad.exe"

# view it
"$SCAD" block-detector-enclosure.scad

# the printable parts
for p in base lid clip; do
  "$SCAD" -o "stl/block-detector-$p.stl" -D "part=\"$p\"" block-detector-enclosure.scad
done

# check nothing collides after changing a parameter
python check_fit.py
```

`part` also takes `assembly` (box + lid + clip + board + rail), `fit` (board in
the open box) and `section_x` / `section_y` with `section_at` for cutaways.

### Parameters worth touching

| Parameter | Default | Why you would change it |
|---|---|---|
| `headroom` | 22 | Clear height over the board. Set by the 1×4 Dupont housing on J3 (~17 mm) plus room for the wires to turn. Solder the OUT cable straight to the pins and 12 is enough — that takes 10 mm off the box height. |
| `pcb_gap` | 4.6 | Board edge to wall. Driven by the corner posts having to miss the board corners; below ~4.3 they clash. |
| `corner_r` | 4.5 | Outer corner radius. The lid screws sit on this axis, so it also sets the wall left around their countersinks. Do not go below ~4.4 with M3. |
| `spring_preload` | 0.5 | How hard the DIN tongue bears on the rail. Raise it if the module rattles, lower it if it will not clip on. |
| `rail_brim_t` | 1.0 | Rail sheet thickness. Heavy rail is 1.35 — set it and the hooks follow. |

`check_fit.py` reads these straight out of the `.scad`, so run it after any
change. Current result:

```
Enclosure  62.0 x 52.0 x 32.6 mm outer   (interior 57.2 x 47.2 x 28.6)
Board sits 7.0 mm above the floor, 22.0 mm clear above it under the lid.
read 28 component courtyards from the board file
all 37 checks pass
```

Tightest clearances it reports: 0.54 mm between each corner post and the board
corner, 3.77 mm from the M2 screw heads to the RV1/RV2 courtyards, and 1.30 mm
of wall outboard of the lid countersinks.

---

## Not done

Nothing has been printed or measured. The connector heights used to size the
box are nominal — in particular `headroom` assumes a generic 2.54 mm Dupont
housing at about 17 mm above the board. Measure yours before printing; it is
one parameter and the box height follows it directly.

The CT slots assume the Phoenix PT-1,5-2-3.5-H wire axes sit about 4.5 mm above
the board. The slots are 7.5 × 8.5 mm and centred on that, so a couple of
millimetres either way is absorbed.
