include<../modules/params.scad>;
use<../modules/carriageScrews.scad>;

// The stripper plate is placed relative to the needle (bottom of the needle
// slot) and sized with STRIPPER_PLATE_SIZE, so it keeps the same position
// under the needle hook and the same gap to the needlebed for any
// camPlateHeight.
module stripperPlate(col = "blue") {
    $fn = 50;
    color(col)
    hull() {
        // outer L: the outer end of the blade, square or with the lead-in
        // chamfer (two rounded corners, see stripperLeadInCorners())
        if (stripperLeadIn > 0)
            for (c = stripperLeadInCorners())
                translate([c[0], c[1], -STRIPPER_PLATE_SIZE])
                rotate_extrude($fn = 50)
                translate([stripperLeadInRadius - STRIPPER_PLATE_SIZE/4, 0])
                circle(d = STRIPPER_PLATE_SIZE/2);
        else
            translate([-CAM_PLATE_WIDTH/2,NEEDLE_EXTENSION-4,-STRIPPER_PLATE_SIZE])
            sphere(d = STRIPPER_PLATE_SIZE/2);
        
        // mid L
         translate([-STRIPPER_PLATE_SIZE * 2.5,NEEDLE_EXTENSION-STRIPPER_PLATE_SIZE/2,-STRIPPER_PLATE_SIZE])
         sphere(d = STRIPPER_PLATE_SIZE/2);
        
        // inner L
        translate([-STRIPPER_PLATE_SIZE * 1.5 - 0.5,NEEDLE_EXTENSION-STRIPPER_PLATE_SIZE * 1.5 -2,-STRIPPER_PLATE_SIZE])
         cylinder(h = STRIPPER_PLATE_SIZE/2, d = STRIPPER_PLATE_SIZE*3, center = true);
        
//        front rounded edge
        translate([-CAM_PLATE_WIDTH/2 + 55/2, -(STRIPPER_PLATE_SIZE)/2, -(STRIPPER_PLATE_SIZE + 1)/2])
    rotate([0,90,0])
        cylinder(55, d = STRIPPER_PLATE_SIZE + 1, center = true, $fn = 30);
    }
}

//stripperPlate("lime");

// Centres of the two rounded corners of the lead-in chamfer, in the frame of
// stripperPlate(). The blade edge is the hull of spheres of diameter
// STRIPPER_PLATE_SIZE/2 along a skeleton: the blade tip line (outer L to
// mid L), the outer end (x = -CAM_PLATE_WIDTH/2) and the chamfer, a 45 degree
// line that starts stripperLeadIn behind the tip at the outer end. Each
// corner is a torus whose outline has radius stripperLeadInRadius.
function stripperLeadInCorners() =
    let (r = stripperLeadInRadius - STRIPPER_PLATE_SIZE/4,   // corner radius of the skeleton
         x0 = -CAM_PLATE_WIDTH/2,
         y0 = NEEDLE_EXTENSION - 4,                           // outer L
         // slope of the tip line, from outer L to mid L
         s = ((NEEDLE_EXTENSION - STRIPPER_PLATE_SIZE/2) - y0) / (-STRIPPER_PLATE_SIZE*2.5 - x0),
         k = sqrt(1 + s*s),
         ua = (stripperLeadIn + r*sqrt(2) - r*k) / (1 - s))   // chamfer x tip corner
    [[x0 + r, y0 - stripperLeadIn + r - r*sqrt(2)],          // chamfer x outer end
     [x0 + ua, y0 + s*ua - r*k]];

assert(stripperLeadIn == 0 || stripperLeadInRadius > STRIPPER_PLATE_SIZE/4,
       "stripperLeadInRadius must be larger than the blade edge radius");

module stripperPlateNose() {
    color("blue")
    hull () {
//        translate([0, -(STRIPPER_PLATE_SIZE)/2, -(STRIPPER_PLATE_SIZE + 1)/2])
//        rotate([0,90,0])
//        cylinder(CAM_PLATE_WIDTH, d = STRIPPER_PLATE_SIZE + 1, center = true, $fn = 30);
        
        translate([-CAM_PLATE_WIDTH/2 + 55/2, -(STRIPPER_PLATE_SIZE)/2, -(STRIPPER_PLATE_SIZE + 1)/2])
    rotate([0,90,0])
        cylinder(55, d = STRIPPER_PLATE_SIZE + 1, center = true, $fn = 30);
    
        
        // line up with front edge of yarn carrier; the second copy widens
        // the post forward, as far as the yarn carrier reaches
        for (dy = [0, STRIPPER_MOUNT_EXTENSION])
        translate([-CAM_PLATE_WIDTH/2 + 55/2,-(STRIPPER_PLATE_SIZE + 1.5) - dy,needleSlotHeight + 2])
        rotate([0,90,0])
        cylinder(55, d = needleSlotHeight + 2.5, center = true, $fn = 50);
    }
}

module yarnCarrierCutout() {
        hull() {
//            translate([CAM_PLATE_WIDTH/2,0,0])
//            yarnFeeder();
            
            // back
            translate([CAM_PLATE_WIDTH/2,YARN_DEPOSIT_Y,(camHeight + camPlateHeight*2)])
            cylinder(h = 40, r = 29, center = true);
             
         // wide cone front   
            translate([CAM_PLATE_WIDTH/2,YARN_DEPOSIT_Y - 35,(camHeight + camPlateHeight)/2])
            cylinder(h = camHeight + camPlateHeight, r = (CAM_PLATE_WIDTH - 55*2)/2, center = true);
                
//            // small frontmost
//            translate([CAM_PLATE_WIDTH/2,YARN_DEPOSIT_Y - 35,-camPlateHeight])
//            cylinder(h = camHeight + camPlateHeight*2, r = 10, center = true);
        }
}


    difference() {
        translate([CAM_PLATE_WIDTH/2,-NEEDLE_BED_DEPTH - NEEDLE_EXTENSION - tolerance * 2,-needleSlotHeight]) {
            union() {
                stripperPlate();
                stripperPlateNose();
            }
        }
        translate([-1,-tolerance, -tolerance])
        // flat edge (the yarn feeder sits on it), from the front edge of the
        // yarn carrier back to where upstream had it
        translate([0, YARN_CARRIER_FRONT_Y, YARN_FEEDER_Z])
        cube([CAM_PLATE_WIDTH + 4, STRIPPER_PLATE_SIZE + 2 + STRIPPER_MOUNT_EXTENSION, needleSlotHeight + 10], center = false);
        
        
        yarnCarrierCutout();
        
        carriageScrews();
    }
    
    translate([CAM_PLATE_WIDTH, 0, 0])
    mirror([1,0,0])
    difference() {
        translate([CAM_PLATE_WIDTH/2,-NEEDLE_BED_DEPTH - NEEDLE_EXTENSION - tolerance * 2,-needleSlotHeight]) {
            union() {
                stripperPlate();
                stripperPlateNose();
            }
        }
        translate([-1,-tolerance, -tolerance])
        // flat edge (the yarn feeder sits on it), from the front edge of the
        // yarn carrier back to where upstream had it
        translate([0, YARN_CARRIER_FRONT_Y, YARN_FEEDER_Z])
        cube([CAM_PLATE_WIDTH + 4, STRIPPER_PLATE_SIZE + 2 + STRIPPER_MOUNT_EXTENSION, needleSlotHeight + 10], center = false);
        
        
        yarnCarrierCutout();
        
        carriageScrews();
    }

