include<params.scad>;
include<inserts.scad>;
//include<needlebed.scad>;

// Screw holes shared by the needlebed, the back cover and the sponge bar.
// The screws go in from the top, through the back cover or the sponge bar,
// into heat-set inserts in the needlebed.
//
// The back cover screws sit in the 3 mm wall between two needle slots, which
// is too thin for an insert, so their inserts are pressed in from the bottom
// face of the needlebed. The sponge bar screws are under the sponge bar,
// where the bed is solid below the slots, so their inserts go in from the top.

SPONGE_BAR_SCREW_Y = -(NEEDLE_BED_DEPTH-COMB) + SPONGE_BAR/2;
BACK_COVER_SCREW_YS = [-5, -BACK_COVER + 5];

module screwHoles(screw) {

    // "screw" is passed in during the loop to place holes at either end of the assembly
    // (screw > 0: left half, screw < 0: right half)
    x = screw > 0 ? gauge/2 : -gauge/2;

    // spongebar screw
    translate([x, SPONGE_BAR_SCREW_Y, 0]) {
        cylinder(h = needleBedHeight*2 + 1, d = screwDiamSm, center = true, $fn = 25);
        translate([0,0,railHeight])
            cylinder(h = screwHeadHeight*2 + tolerance, d = screwHeadDiamSm, center = true, $fn = 25);
        insertHole(-needleSlotHeight, -1);
    }
    // back cover screws, back and front
    for (y = BACK_COVER_SCREW_YS) translate([x, y, 0]) {
        cylinder(h = needleBedHeight*2 + 1, d = screwDiamSm, center = true, $fn = 25);
        cylinder(h = screwHeadHeight*2 + tolerance, d = screwHeadDiamSm, center = true, $fn = 25);
        insertHole(-needleBedHeight, +1);
    }
}

// x positions of the screws, same loop as needleBedScrews(). Both branches
// of the loop give the same x (the wall between two needle units), so the
// list is deduplicated.
function needleBedScrewXs() = let(xs = [
    for (i = [0:numNeedles-1])
        if (i==screwPlacement || i==numNeedles-screwPlacement) gauge*i - gauge/2
        else if (i == screwPlacement - 1 || i==numNeedles-(screwPlacement + 1)) gauge*i + gauge/2
]) [for (k = [0:len(xs)-1]) if (len([for (m = [0:k]) if (abs(xs[m] - xs[k]) < 0.01) 1]) == 1) xs[k]];

//screwHoles(screw = 1);
module needleBedScrews() {
    for(i = [0:numNeedles-1]) {
        if (i==screwPlacement || i==numNeedles-screwPlacement) {
              translate([gauge*i, 0, 0]) {
              screwHoles(screw = -1);
              }
        } else if (i == screwPlacement - 1 || i==numNeedles-(screwPlacement + 1)) {
            //LS screw holes
                translate([gauge*i, 0, 0])
                screwHoles(screw = 1);
        }
    }
}

module needleBedScrewsReport() {
    hd = screwHeadDiamSm - tolerance*2;
    hh = screwHeadHeight - tolerance*2;
    reportJoint("sponge bar", [for (x = needleBedScrewXs()) [x, SPONGE_BAR_SCREW_Y]],
                "top", "spongeBar", "needlebed", -needleSlotHeight, -1, hd, hh, true);
    reportJoint("back cover", [for (x = needleBedScrewXs()) for (y = BACK_COVER_SCREW_YS) [x, y]],
                "top", "backCover", "needlebed", -needleBedHeight, +1, hd, hh, true);
}

needleBedScrews() {
}
