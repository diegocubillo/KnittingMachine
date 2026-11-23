include <../modules/camplate_coords_mk2.scad>;
use <tCam.scad>;

// Tension pointer, left side (print 2: it is symmetric about its axis, so
// the right one, placed mirrored in camplate.scad, is the same part). It is
// screwed to the pivot of the tension cam and to the tension screw, and its
// tip locks the cam in one of the notches of the tension lock block
// (tensionLock.scad).

tPointer();

// Outline in the pivot frame (pivot at the origin, pointer along +x).
// tensionLock.scad cuts the notches with this same outline.
module tPointer2D() {
    hull() {
        circle(d = tPointerWidth, $fn = 50);
        translate([tPointerShoulder(), 0]) circle(d = tPointerWidth, $fn = 50);
        translate([tPointerTipCentre(), 0]) circle(r = tPointerTipRadius, $fn = 30);
    }
}

module tPointer() {
    // it rests on top of the pivot, which sticks out of the back plate
    translate([tPivotCoords[0], tPivotCoords[1], tPivotTopZ()])
    rotate([0, 0, tPointerDir()])
    linear_extrude(tPointerThickness)
    difference() {
        tPointer2D();
        circle(d = screwDiamSm, $fn = 30);                                          // pivot screw
        translate([tensionScrewRadius(), 0]) circle(d = screwDiamSm, $fn = 30);     // tension screw
    }
}
