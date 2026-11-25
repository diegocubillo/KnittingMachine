include<../modules/params.scad>;

// Knob for the clamp bolt. The bolt goes through the centre hole and its head
// sits in the blind hexagonal pocket, so the knob turns the bolt. Grip notches
// around the rim. Shown in print orientation: pocket up (no bridges); in use
// the pocket faces down, with the bolt head under the knob.

clampKnobDiam = 40;
clampKnobFloor = 4;                                     // plastic under the bolt head
clampKnobHeight = clampBoltHeadHeight + tolerance + clampKnobFloor;
clampKnobNotches = 16;
clampKnobNotchDiam = 5;
clampKnobChamfer = 1;

clampKnob();

module clampKnob() {
    $fn = 80;
    c = clampKnobChamfer;
    difference() {
        // disc with chamfered edges
        hull() {
            translate([0, 0, c]) cylinder(h = clampKnobHeight - 2*c, d = clampKnobDiam);
            cylinder(h = clampKnobHeight, d = clampKnobDiam - 2*c);
        }
        // grip notches, with their edges chamfered like the rim
        for (i = [0:clampKnobNotches - 1])
            rotate([0, 0, i * 360 / clampKnobNotches])
            translate([clampKnobDiam/2, 0, 0])
            union() {
                d = clampKnobNotchDiam;
                translate([0, 0, -1]) cylinder(h = clampKnobHeight + 2, d = d, $fn = 30);
                translate([0, 0, -0.01]) cylinder(h = c + 0.01, d1 = d + 2*c, d2 = d, $fn = 30);
                translate([0, 0, clampKnobHeight - c]) cylinder(h = c + 0.01, d1 = d, d2 = d + 2*c, $fn = 30);
            }
        // bolt hole, through
        translate([0, 0, -1])
        cylinder(h = clampKnobHeight + 2, d = clampBoltDiam + tolerance*2, $fn = 50);
        // bolt head pocket, blind, from the top face
        translate([0, 0, clampKnobFloor])
        cylinder(h = clampKnobHeight, d = (clampBoltHeadWidth + tolerance*2) / cos(30), $fn = 6);
    }
}
