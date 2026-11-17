include<../modules/params.scad>;
use<../modules/carriageScrews.scad>;
use<../parts/stripperPlate.scad>;

difference() {
    color("orchid", 0.5)

    yarnCarrierCover();
    yarnCarrierCutout();
    // room for the yarn feeder, anchored at the front edge (upstream centred
    // it on a fixed y, so it shifted when camPlateHeight changed)
    translate([-1, YARN_CARRIER_FRONT_Y - 1, 0])
    cube([CAM_PLATE_WIDTH + 2, YARN_FEEDER_BACK_Y - YARN_CARRIER_FRONT_Y + 2, YARN_FEEDER_Z + camPlateHeight]);
    carriageScrews();

}

module yarnCarrierCover() {
    hull() {
        // main
        translate([0,-(NEEDLE_BED_DEPTH - COMB + 6),camHeight + camPlateHeight])
        cube([CAM_PLATE_WIDTH, SPONGE_BAR + 6, camPlateHeight]);
        // rounded edge
        translate([CAM_PLATE_WIDTH/2,-(NEEDLE_BED_DEPTH - COMB + 6 + tolerance + camPlateHeight/2),camHeight + camPlateHeight * 1.5])
        rotate([0,90,0])
        cylinder(CAM_PLATE_WIDTH, d = camPlateHeight, center = true, $fn = 30);
    }

    hull() {
        // overhang
        translate([0,-(NEEDLE_BED_DEPTH),YARN_FEEDER_Z])
        cube([CAM_PLATE_WIDTH, COMB - 6 - tolerance, camPlateHeight]);

        // rounded edge
        translate([CAM_PLATE_WIDTH/2,-(NEEDLE_BED_DEPTH - COMB + 6 + tolerance + camPlateHeight/2),camHeight + camPlateHeight * 1.5])
        rotate([0,90,0])
        cylinder(CAM_PLATE_WIDTH, d = camPlateHeight, center = true, $fn = 30);

        // flat edge, over the stripper plate screws. Its top is 0.25 mm above
        // the seat of the screw heads, so the heads sit on a flat floor
        // (with stripperScrewSeat = 0.5 this is the upstream shape).
        translate([0, -(NEEDLE_BED_DEPTH + NEEDLE_EXTENSION + STRIPPER_PLATE_SIZE*1.5), YARN_FEEDER_Z - 0.25])
        cube([CAM_PLATE_WIDTH, STRIPPER_PLATE_SIZE, stripperScrewSeatZ() + 0.25 - (YARN_FEEDER_Z - 0.25)]);
    }
}
