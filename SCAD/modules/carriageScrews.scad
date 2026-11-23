include<params.scad>;
include<inserts.scad>;

// Screw holes shared by the carriage parts (backPlate, yarnCarrierCover,
// yarnFeeder, stripperPlate). Every part subtracts the whole set, so each cut
// is placed in z so that it only removes material from the part it is meant for.

// Screw positions
function camplateScrewsXY() = [
    for (y = [-6, -(NEEDLE_BED_DEPTH - COMB - 6)])
        for (x = [screwHeadDiam*1.5, CAM_PLATE_WIDTH/2, CAM_PLATE_WIDTH - screwHeadDiam*1.5])
            [x, y]
];
function stripperScrewsXY() = [
    for (x = [screwHeadDiamSm*1.5, screwHeadDiamSm*1.5 + 35,
              CAM_PLATE_WIDTH - screwHeadDiamSm*1.5 - 35, CAM_PLATE_WIDTH - screwHeadDiamSm*1.5])
        [x, stripperScrewY]
];
function feederScrewsXY() = [
    for (x = [screwHeadDiam*1.5, screwHeadDiam*1.5 + 35,
              CAM_PLATE_WIDTH - screwHeadDiam*1.5 - 35, CAM_PLATE_WIDTH - screwHeadDiam*1.5])
        [x, -(NEEDLE_BED_DEPTH - COMB/2)]
];

// z of the face the stripper plate screw heads sit on (inside the yarn carrier cover)
function stripperScrewSeatZ() = YARN_FEEDER_Z + camPlateHeight + stripperScrewSeat;

module carriageScrews() {
    // Back plate: screws from the top, into inserts in the top face of the
    // back plate. The front row goes through the yarn carrier cover; the
    // middle screw of the back row holds the yarn guide.
    for (p = camplateScrewsXY()) translate(p) {
        translate([0, 0, camHeight + camPlateHeight/2])
        cylinder(h = 12*2, d = screwDiam, center = true);
        insertHole(camHeight + camPlateHeight, -1);
    }

    // Stripper plate: screws from the top, through the yarn carrier cover and
    // the yarn feeder, into the top face of the stripper plate (insert or
    // pilot hole, see stripperPlateInserts).
    for (p = stripperScrewsXY()) translate(p) {
        // clearance, from the top face of the stripper plate up through the top of the cover
        translate([0, 0, YARN_FEEDER_Z - tolerance - 0.01])
        cylinder(h = camPlateHeight + 20, d = screwDiamSm);
        // head recess, open to the top
        translate([0, 0, stripperScrewSeatZ()])
        cylinder(h = 20, d = screwHeadDiamSm);
        if (stripperPlateInserts)
            insertHole(YARN_FEEDER_Z - tolerance, -1);
        else
            pilotHole(YARN_FEEDER_Z - tolerance, -1);
    }

    // Yarn feeder: screws from below, head recessed in the feeder, into
    // inserts in the bottom face of the yarn carrier cover.
    for (p = feederScrewsXY()) translate(p) {
        translate([0, 0, YARN_FEEDER_Z - tolerance]) {
            cylinder(h = screwHeight - 2, d = screwDiam);
            cylinder(h = screwHeadHeight + tolerance, d = screwHeadDiam);
        }
        insertHole(YARN_FEEDER_Z + camPlateHeight, +1);
    }
}

module carriageScrewsReport() {
    hd = screwHeadDiamSm - tolerance*2;
    hh = screwHeadHeight - tolerance*2;
    reportJoint("camplate back row", [for (i = [0:2]) camplateScrewsXY()[i]],
                "top", "backPlate", "backPlate", camHeight + camPlateHeight, -1, hd, hh, false);
    reportJoint("camplate front row (yarn carrier)", [for (i = [3:5]) camplateScrewsXY()[i]],
                "top", "yarnCarrierCover", "backPlate", camHeight + camPlateHeight, -1, hd, hh, false);
    reportJoint("stripper plate", stripperScrewsXY(),
                "top", "yarnCarrierCover", "stripperPlate", YARN_FEEDER_Z - tolerance, -1, hd, hh, false,
                stripperPlateInserts ? "insert" : "pilot");
    reportJoint("yarn feeder", feederScrewsXY(),
                "bottom", "yarnFeeder", "yarnCarrierCover", YARN_FEEDER_Z + camPlateHeight, +1, hd, hh, true);
}
