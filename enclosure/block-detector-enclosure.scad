// ============================================================================
//  Enclosure for the bazauto 2-Channel DCC Block Detector
//  PCB: 48 x 38 x 1.6 mm, 4 x M2 mounting holes.
//
//  Three printed parts, selected with the "part" variable below:
//    base  - box body, prints floor-down, no supports
//    lid   - solid lid, prints outside-face-down, no supports
//    clip  - DIN TH35 rail clip, prints mating-face-down, no supports
//
//  Orientation in the model: X is the PCB's 48 mm axis, Y its 38 mm axis,
//  Z up out of the board. The DIN rail runs along Y, so modules stack along
//  the rail and every cable leaves through an X-facing wall.
// ============================================================================

part = "assembly";  // [base, lid, clip, assembly, section_x, section_y]
section_at = 30;    // cut plane, used by the section views only

// ---------------------------------------------------------------- PCB facts
pcb_w        = 48.0;    // board X
pcb_d        = 38.0;    // board Y
pcb_t        = 1.6;     // board thickness
pcb_hole_d   = 2.2;     // M2 clearance holes in the board
pcb_holes    = [[14, 2.8], [14, 35.2], [38, 2.8], [38, 35.2]];

// Connector positions, in board coordinates (origin = board lower-left corner)
j1_wire_y    = [24.5, 28.0];   // CT1 terminal block, wire axes
j2_wire_y    = [ 6.5, 10.0];   // CT2 terminal block, wire axes
j3_y         = [15.19, 22.81]; // OUT header, pin 1 .. pin 4

// ------------------------------------------------------------- Box envelope
pcb_gap      = 4.6;     // board edge to interior wall
wall         = 2.4;
floor_t      = 2.0;
lid_t        = 2.0;
standoff_h   = 5.0;     // board underside above the floor (clears THT leads)
headroom     = 22.0;    // clear height above the board, under the lid.
                        //   Set by the 1x4 Dupont housing on J3 (~17 mm) plus
                        //   room for the wires to turn out through the wall.
                        //   Solder the cable direct and 12 is enough.
corner_r     = 4.5;     // outer corner radius. The lid screws sit on this
                        //   axis, so it also sets the wall left around their
                        //   countersinks - do not reduce it below ~4.4.

// ------------------------------------------------------------------ Fixings
lid_pilot_d   = 2.5;    // M3 self-tapping into the corner posts
lid_clear_d   = 3.4;
lid_cs_d      = 6.4;    // countersink major diameter
post_r        = 3.0;    // screw axis sits at the centre of the corner radius,
                        //   which is the point furthest from the outer surface

pcb_screw_pilot_d = 1.6; // M2 self-tapping into the board standoffs
pcb_standoff_r    = 2.5;

clip_screw_pilot_d = 2.5; // M3 self-tapping, clip -> box floor
clip_boss_r        = 3.0;

lip_h        = 2.0;     // lid register lip
lip_w        = 1.5;
lip_clear    = 0.35;

// ------------------------------------------------------------- DIN TH35 clip
clip_plate_t = 3.0;
rail_w       = 35.0;    // brim-to-brim width of a TH35 rail
rail_brim_t  = 1.0;     // brim sheet thickness
brim_slop    = 0.2;
spring_preload = 0.5;   // interference the spring tongue must take up
clip_wall_t  = 2.4;
lip_reach    = 2.0;     // how far the hooks reach in under the brims
clip_margin  = 0.4;     // clip plate inset from the box outline
anchor_len   = 8.0;     // rooted length of the spring tongue
tab_len      = 6.0;
tab_reach    = 7.0;

// --------------------------------------------------------------- Derived
interior_w = pcb_w + 2*pcb_gap;              // 55.0
interior_d = pcb_d + 2*pcb_gap;              // 45.0
interior_h = standoff_h + pcb_t + headroom;  // 28.6
outer_w    = interior_w + 2*wall;            // 59.8
outer_d    = interior_d + 2*wall;            // 49.8
base_h     = floor_t + interior_h;           // 30.6
outer_h    = base_h + lid_t;                 // 32.6
interior_r = max(corner_r - wall, 0.6);

pcb_x0 = wall + pcb_gap;                     // board origin in box coords
pcb_y0 = wall + pcb_gap;
pcb_z0 = floor_t + standoff_h;               // board underside
pcb_zt = pcb_z0 + pcb_t;                     // board top

post_xy = [[corner_r,           corner_r],
           [outer_w - corner_r, corner_r],
           [corner_r,           outer_d - corner_r],
           [outer_w - corner_r, outer_d - corner_r]];

// Clip screws sit in the two bands the rail channel leaves free, clear of the
// spring tongue's slot on one side and the fixed hook on the other.
clip_boss_xy = [[5.2, outer_d/2], [outer_w - 5.2, outer_d/2]];
clip_boss_h  = standoff_h - 0.6;             // stops just under the board

rail_cx      = outer_w/2;
fixed_in     = rail_cx - rail_w/2 - brim_slop/2;
fixed_out    = fixed_in - clip_wall_t;
spring_in    = rail_cx + rail_w/2 - spring_preload;
spring_out   = spring_in + clip_wall_t;

clip_x0 = clip_margin;              clip_x1 = outer_w - clip_margin;
clip_y0 = clip_margin + 1.0;        clip_y1 = outer_d - clip_margin - 1.0;
clip_corner_r = max(corner_r - clip_margin, 1.0);

$fn = 64;

// ============================================================================
//  Helpers
// ============================================================================
module rrect(w, d, r) {
    translate([r, r]) offset(r = r) square([w - 2*r, d - 2*r]);
}

module outer_profile()    { rrect(outer_w, outer_d, corner_r); }
module interior_profile() { translate([wall, wall]) rrect(interior_w, interior_d, interior_r); }

// Countersunk clearance hole, drilled downward from z = top.
module countersunk(top, depth) {
    translate([0, 0, top - depth]) cylinder(h = depth + 0.1, d = lid_clear_d);
    translate([0, 0, top - (lid_cs_d - lid_clear_d)/2])
        cylinder(h = (lid_cs_d - lid_clear_d)/2 + 0.05, d1 = lid_clear_d, d2 = lid_cs_d);
}

// ============================================================================
//  Base
// ============================================================================
module base() {
    difference() {
        union() {
            // shell
            difference() {
                linear_extrude(base_h) outer_profile();
                translate([0, 0, floor_t])
                    linear_extrude(interior_h + 1) interior_profile();
            }
            // lid screw posts, blended into the corners
            for (p = post_xy)
                translate([p[0], p[1], floor_t]) cylinder(h = interior_h, r = post_r);
            // PCB standoffs
            for (h = pcb_holes)
                translate([pcb_x0 + h[0], pcb_y0 + h[1], floor_t])
                    cylinder(h = standoff_h, r = pcb_standoff_r);
            // bosses for the DIN clip screws (they live under the board)
            for (p = clip_boss_xy)
                translate([p[0], p[1], floor_t]) cylinder(h = clip_boss_h, r = clip_boss_r);
        }

        // lid screw pilots
        for (p = post_xy)
            translate([p[0], p[1], base_h - 12]) cylinder(h = 12.1, d = lid_pilot_d);

        // PCB screw pilots (blind, 1 mm of floor left)
        for (h = pcb_holes)
            translate([pcb_x0 + h[0], pcb_y0 + h[1], 1.0])
                cylinder(h = standoff_h + floor_t - 1.0 + 0.01, d = pcb_screw_pilot_d);

        // DIN clip screw pilots, right through the floor
        for (p = clip_boss_xy)
            translate([p[0], p[1], -0.1])
                cylinder(h = floor_t + clip_boss_h - 0.4 + 0.1, d = clip_screw_pilot_d);

        wall_openings();
    }
}

// Cable slots. Left wall: the two CT terminal blocks. Right wall: the OUT cable.
module wall_openings() {
    slot_z0 = pcb_zt + 0.9;
    slot_z1 = pcb_zt + 9.4;

    // CT1 / CT2, one slot each, centred on the pair of wire axes
    for (ys = [j1_wire_y, j2_wire_y]) {
        y0 = pcb_y0 + ys[0] - 2.0;
        y1 = pcb_y0 + ys[1] + 2.0;
        translate([-1, y0, slot_z0]) cube([wall + 1.6, y1 - y0, slot_z1 - slot_z0]);
    }

    // OUT cable, high on the right wall so it clears the connector housing
    oy0 = pcb_y0 + j3_y[0] - 2.6;
    oy1 = pcb_y0 + j3_y[1] + 2.6;
    translate([outer_w - wall - 0.6, oy0, pcb_zt + 11.4])
        cube([wall + 1.6, oy1 - oy0, 8.0]);
}

// ============================================================================
//  Lid  (modelled in place; part="lid" flips it for printing)
// ============================================================================
module lid() {
    difference() {
        union() {
            translate([0, 0, base_h]) linear_extrude(lid_t) outer_profile();
            // register lip
            translate([0, 0, base_h - lip_h]) linear_extrude(lip_h)
                difference() {
                    offset(r = -lip_clear) interior_profile();
                    offset(r = -(lip_clear + lip_w)) interior_profile();
                }
        }
        // clearance around the corner posts
        for (p = post_xy)
            translate([p[0], p[1], base_h - lip_h - 0.1])
                cylinder(h = lip_h + 0.2, r = post_r + 0.4);
        // screws
        for (p = post_xy)
            translate([p[0], p[1], 0]) countersunk(outer_h, lid_t + lip_h + 0.2);
        lid_engraving();
    }
}

module lid_engraving() {
    depth = 0.5;
    translate([0, 0, outer_h - depth]) linear_extrude(depth + 0.1) {
        translate([outer_w/2, outer_d/2 + 6.5])
            text("BLOCK", size = 7, halign = "center", valign = "center",
                 font = "Liberation Sans:style=Bold");
        translate([outer_w/2, outer_d/2 - 1.5])
            text("DETECT", size = 7, halign = "center", valign = "center",
                 font = "Liberation Sans:style=Bold");
        translate([outer_w/2, outer_d/2 - 9.5])
            text("2 CH   3V3", size = 3.6, halign = "center", valign = "center",
                 font = "Liberation Sans");
        // which slot is which, read from the connector side
        rotate(90) translate([pcb_y0 + j1_wire_y[0] + 1.75, -6.6])
            text("CT1", size = 3.4, halign = "center", valign = "center",
                 font = "Liberation Sans");
        rotate(90) translate([pcb_y0 + j2_wire_y[0] + 1.75, -6.6])
            text("CT2", size = 3.4, halign = "center", valign = "center",
                 font = "Liberation Sans");
        rotate(90) translate([outer_d/2, -(outer_w - 6.6)])
            text("OUT", size = 3.4, halign = "center", valign = "center",
                 font = "Liberation Sans");
    }
}

// ============================================================================
//  DIN TH35 rail clip  (modelled in place, hanging under the base)
// ============================================================================
z_plate  = -clip_plate_t;               // face that meets the rail brims
z_grip   = z_plate - rail_brim_t - 0.2; // gripping face, under the brims
z_lip    = z_grip - 1.0;                // 45 deg relief under the grip
z_bot    = z_grip - 2.5;                // tip of the lead-in ramp

// One hook, as a 2D profile. dir = +1 hooks inward from the -X side.
module hook_profile(x_out, x_in, dir, z_top) {
    polygon([[x_out,                z_top],
             [x_in,                 z_top],
             [x_in,                 z_grip],
             [x_in + dir*1.0,       z_grip],
             [x_in + dir*lip_reach, z_lip],
             [x_in,                 z_bot],
             [x_out,                z_bot]]);
}

// Extrude an XZ profile along Y, from y0 for len.
module extrude_xz(y0, len) {
    translate([0, y0, 0]) rotate([90, 0, 0]) linear_extrude(len) children();
}

module din_clip() {
    tongue_y0 = clip_y0 + anchor_len;

    difference() {
        union() {
            // plate, minus the slot that frees the spring tongue
            difference() {
                translate([0, 0, z_plate]) linear_extrude(clip_plate_t)
                    translate([clip_x0, clip_y0])
                        rrect(clip_x1 - clip_x0, clip_y1 - clip_y0, clip_corner_r);
                translate([spring_in - 0.6, tongue_y0, z_plate - 0.1])
                    cube([clip_wall_t + 1.2, clip_y1 - tongue_y0 + 1, clip_plate_t + 0.2]);
                translate([spring_in - 0.6, clip_y1 - tab_len - 1.4, z_plate - 0.1])
                    cube([clip_x1 + 1 - (spring_in - 0.6), tab_len + 2.4, clip_plate_t + 0.2]);
            }

            // fixed hook, rooted along its whole length
            extrude_xz(clip_y1, clip_y1 - clip_y0)
                hook_profile(fixed_out, fixed_in, +1, z_plate);

            // spring hook: full height, so it prints off the bed and can flex
            extrude_xz(clip_y1, clip_y1 - clip_y0)
                hook_profile(spring_out, spring_in, -1, 0);

            // release tab
            translate([spring_out - 0.01, clip_y1 - tab_len, z_plate])
                cube([tab_reach, tab_len, clip_plate_t]);
        }

        // screws up into the box floor
        for (p = clip_boss_xy) translate([p[0], p[1], 0]) {
            translate([0, 0, z_plate - 0.1]) cylinder(h = clip_plate_t + 0.2, d = lid_clear_d);
            translate([0, 0, z_plate - 0.01])
                cylinder(h = (lid_cs_d - lid_clear_d)/2 + 0.01, d1 = lid_cs_d, d2 = lid_clear_d);
        }
    }
}

// ============================================================================
//  Reference geometry, for checking fit only
// ============================================================================
module pcb_stack() {
    color("darkgreen")
    translate([pcb_x0, pcb_y0, pcb_z0]) difference() {
        cube([pcb_w, pcb_d, pcb_t]);
        for (h = pcb_holes)
            translate([h[0], h[1], -0.1]) cylinder(h = pcb_t + 0.2, d = pcb_hole_d);
    }
    translate([pcb_x0, pcb_y0, pcb_zt]) {
        // J1 / J2 terminal blocks (body 8.6 x 8.0, wire entry facing -X)
        color("darkorange") for (y = [j1_wire_y[0], j2_wire_y[0]])
            translate([1.0, y - 2.25, 0]) cube([8.6, 8.0, 9.5]);
        // J3 header + mating housing
        color("dimgray") translate([43.7, j3_y[0] - 1.3, 0]) cube([2.6, 10.2, 2.5]);
        color("ivory")   translate([43.2, j3_y[0] - 1.8, 2.5]) cube([3.6, 11.2, 14.5]);
        // JP1
        color("dimgray") translate([12.1, 15.5, 0]) cube([2.6, 5.1, 8.5]);
        // trimmers
        color("navy") for (y = [24.6, 6.6]) translate([33.8, y, 0]) cube([8.1, 6.9, 3.0]);
        // ICs and passives, as one low block
        color("gray") translate([15, 8, 0]) cube([18, 24, 1.2]);
    }
}

module din_rail() {
    color("silver") extrude_xz(outer_d + 6, outer_d + 12)
        polygon([[rail_cx - 17.5, z_plate],
                 [rail_cx + 17.5, z_plate],
                 [rail_cx + 17.5, z_plate - rail_brim_t],
                 [rail_cx + 13.5, z_plate - rail_brim_t],
                 [rail_cx + 13.5, z_plate - 7.5],
                 [rail_cx - 13.5, z_plate - 7.5],
                 [rail_cx - 13.5, z_plate - rail_brim_t],
                 [rail_cx - 17.5, z_plate - rail_brim_t]]);
}

// ============================================================================
//  Output
// ============================================================================
if (part == "base") base();
else if (part == "lid")
    translate([0, outer_d, outer_h]) rotate([180, 0, 0]) lid();
else if (part == "clip")
    translate([0, outer_d, 0]) rotate([180, 0, 0]) din_clip();
else if (part == "fit") { base(); pcb_stack(); }   // board in the open box
else if (part == "section_x")   // cut across the box, looking along +X
    difference() { assembly(); translate([-1, -20, -20]) cube([section_at + 1, 100, 100]); }
else if (part == "section_y")   // cut along the box, looking along +Y
    difference() { assembly(); translate([-20, -1, -20]) cube([100, section_at + 1, 100]); }
else assembly();

module assembly() {
    base();
    color("gainsboro", 0.55) lid();
    color("steelblue") din_clip();
    pcb_stack();
    %din_rail();
}
