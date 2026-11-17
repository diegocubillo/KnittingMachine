include<../modules/params.scad>;
include<../modules/camplate_coords_mk2.scad>;
include<../modules/utils.scad>;
include<../modules/inserts.scad>;
//include<../modules/camPinHoles.scad>;

// height of the top face of the tension cam
function tCamTopZ() = camHeight - tolerance;
// height of the top face of the pivot (it sticks out of the back plate)
function tPivotTopZ() = tPivotCoords[2] + (camPlateHeight + 3)/2;

module tCam() {
    // adjustable tension cams
    difference() {
            linear_extrude(camHeight - (camClearance + tolerance))
            import("../../SVG/TCam_mk2.svg");

        // insert for the tension screw (upstream: a hex nut trap for a #4-40 nut)
        translate([tensionScrewCoords[0] - tCamCoords[0], tensionScrewCoords[1] - tCamCoords[1], 0])
        insertHole(tCamTopZ() - tCamCoords[2], -1);
    }
}

module tPivot(tol = 0, solid = false) {
     // pivot
    difference() {
        cylinder(camPlateHeight + 3, d = 8 + tol , center = true);
        if(solid) {
            // insert for the tension pointer screw, pressed in from the top
            insertHole((camPlateHeight + 3)/2, -1);
        }
    }
}

module tCamReport() {
    hd = screwHeadDiamSm - tolerance*2;
    hh = screwHeadHeight - tolerance*2;
    // only the left cam is modelled; the right one is printed mirrored
    reportJoint("tension pointer to pivot", [[tPivotCoords[0], tPivotCoords[1]]],
                "top", "tPointer", "tCam", tPivotTopZ(), -1, hd, hh, false);
    reportJoint("tension screw to cam", [[tensionScrewCoords[0], tensionScrewCoords[1]]],
                "top", "tPointer", "tCam", tCamTopZ(), -1, hd, hh, false);
}


// print 2, mirrored

translate(tCamCoords)
tCam();

translate(tPivotCoords)
tPivot(solid = true);
