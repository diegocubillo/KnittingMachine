include<../modules/params.scad>;
use<../parts/carriageRest.scad>;
use<../parts/clampHead.scad>;
use<../parts/clampKnob.scad>;

/*
Left table clamp as used, for layout and checking: clamp, M8 nut, M8 bolt,
clamp head and knob, on a table `tableThickness` thick. See the part files to
export the models.
*/

tableThickness = 30;    // only for this view
knobGap = 5;            // knob to bottom jaw, before tightening

knobHeight = clampBoltHeadHeight + tolerance + 4;     // as in clampKnob.scad
headBoltDiam = clampBoltDiam - tolerance;             // as in clampHead.scad

bolt = [-gauge + clampBoltXY()[0], clampBoltXY()[1]];
tableUnderside = -(needleBedHeight - tolerance) - tableThickness;
ballZ = tableUnderside - headBoltDiam - tolerance*2;  // the wide face of the head touches the table
knobTop = clampJawBottomZ() - knobGap;
headTop = knobTop - 4;                                // bolt head against the floor of the knob pocket
boltLength = ballZ - headTop;                         // bolt tip at the centre of the ball
echo(str("M8 bolt length for a ", tableThickness, " mm table: about ", boltLength,
         " mm (at least ", boltLength - knobGap, ")"));

translate([-gauge, 0, 0]) clampUnit();

translate(bolt) {
    // clamp head, wide face up against the table
    translate([0, 0, ballZ]) rotate([180, 0, 0]) clampHead();
    // knob, pocket facing down
    translate([0, 0, knobTop]) mirror([0, 0, 1]) clampKnob();
    // hardware
    %translate([0, 0, clampJawTopZ() - clampNutHeight - tolerance])
        cylinder(h = clampNutHeight, d = clampNutWidth / cos(30), $fn = 6);
    %translate([0, 0, headTop]) cylinder(h = boltLength, d = clampBoltDiam, $fn = 30);
    %translate([0, 0, headTop - clampBoltHeadHeight])
        cylinder(h = clampBoltHeadHeight, d = clampBoltHeadWidth / cos(30), $fn = 6);
}

// table
%translate([-gauge - CAM_PLATE_WIDTH/2 - 60, -NEEDLE_BED_DEPTH + 12 + 6, tableUnderside])
    cube([120, NEEDLE_BED_DEPTH, tableThickness]);
