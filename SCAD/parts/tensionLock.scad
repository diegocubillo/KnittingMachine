include <../modules/camplate_coords_mk2.scad>;
include <../modules/inserts.scad>;
use <tPointer.scad>;

// Tension lock block, left side (print 2: with tensionLockAngles symmetric
// about their middle value the block is symmetric about the middle notch, so
// the right one, placed mirrored in camplate.scad, is the same part). It is screwed on top of the back plate, around the tip of the
// tension pointer, with one M3 screw at each end into heat-set inserts in the
// back plate. The face towards the pivot has one notch per entry of
// tensionLockAngles (the tip of the pointer, negative, with
// tensionLockClearance); the opposite face is an arc about the pivot; the two
// ends are semicircles. Print flat, bottom face on the bed.

tensionLock();

// z of the top face of the back plate, where the blocks sit
function tensionLockBaseZ() = camHeight + camPlateHeight;

// Block outline in the pivot frame (as tPointer2D()).
module tensionLock2D() {
    ri = tensionLockInner();
    ro = tensionLockOuter();
    rm = tensionLockMid();
    a = tensionLockScrewAngles();
    difference() {
        // round the crests between the notches
        offset(r = 0.5, $fn = 20) offset(delta = -0.5)
        difference() {
            union() {
                // arc band between the screws, closed by two semicircles
                // the arc is sampled from end to end, so the block stays
                // symmetric about the middle notch
                let (n = ceil((a[0] - a[1]) / 0.5), arc = [for (i = [0:n]) a[1] + i * (a[0] - a[1]) / n])
                polygon(concat([for (t = arc) ri * [cos(t), sin(t)]],
                               [for (i = [n:-1:0]) ro * [cos(arc[i]), sin(arc[i])]]));
                for (t = a) translate(rm * [cos(t), sin(t)]) circle(d = ro - ri, $fn = 50);
            }
            for (t = tensionLockAngles)
                rotate(t) offset(r = tensionLockClearance, $fn = 20) tPointer2D();
        }
        for (t = a) translate(rm * [cos(t), sin(t)]) circle(d = screwDiamSm, $fn = 30);
    }
}

module tensionLock() {
    translate([tPivotCoords[0], tPivotCoords[1], tensionLockBaseZ()])
    rotate([0, 0, tPointerDir()])
    linear_extrude(tPointerThickness)
    tensionLock2D();
}

// inserts in the back plate for the lock screws (both sides)
module tensionLockInserts() {
    for (p = tensionLockScrewsXY()) {
        translate(p) insertHole(tensionLockBaseZ(), -1);
        translate([CAM_PLATE_WIDTH - p[0], p[1]]) insertHole(tensionLockBaseZ(), -1);
    }
}

module tensionLockReport() {
    hd = screwHeadDiamSm - tolerance*2;
    hh = screwHeadHeight - tolerance*2;
    // left block only (tensionLock.stl holds one block; the right side is its
    // mirror image). The TENSION echo of tCamReport() gives the screws of
    // both sides to the STL comparison.
    reportJoint("tension lock to back plate", tensionLockScrewsXY(),
                "top", "tensionLock", "backPlate", tensionLockBaseZ(), -1, hd, hh, false);
}
