include<../modules/params.scad>;
use<../parts/needlebed.scad>;
include<../modules/inserts.scad>;
use<../parts/backCover.scad>;
use<../parts/spongeBar.scad>;
use<../modules/connector.scad>;

// TODO: needs refactoring!

clampWidth = 50;
clampDepth = NEEDLE_BED_DEPTH-clampWidth/2; 
clampThickness = 6;
clampHollow = 85; // adjust this for your table thickness
// bottom jaw: the whole M8 nut sits in a pocket open to the top face, on a
// 4 mm floor
clampJawThickness = clampNutHeight + tolerance + 4;

// LEFT
union() {
    translate([-gauge, 0, 0])
    carriageRest();
//    translate([-gauge/2,-connectorOffset,-needleBedHeight])
//    connector(tolerance = tolerance);
//    translate([-gauge/2,-(NEEDLE_BED_DEPTH-connectorOffset),-needleBedHeight])
//    connector(tolerance = tolerance);
}

//RIGHT
//difference() {
    translate([gauge*numNeedles, 0, 0])
    mirror([1,0,0])
    carriageRest();
//    translate([gauge*numNeedles - gauge/2 - tolerance,-connectorOffset,-needleBedHeight-tolerance])
//    connector();
//    translate([gauge*numNeedles - gauge/2 - tolerance,-(NEEDLE_BED_DEPTH-connectorOffset),-needleBedHeight - tolerance])
//    connector();
//}

////// CLAMP
translate([-gauge,0,0])
clampUnit();


module carriageRest() {
    union() {
        difference() {
            hull() {
                needleBase();   
                translate([-CAM_PLATE_WIDTH, -10, -needleBedHeight/2])
                cylinder(needleBedHeight, 10, 10, center = true); 
                
                translate([-CAM_PLATE_WIDTH, -NEEDLE_BED_DEPTH+10, -needleBedHeight/2])
                cylinder(needleBedHeight, 10, 10, center = true); 
            }
            for(i = [0:ceil(CAM_PLATE_WIDTH/gauge)]) {
               translate([-gauge*i, 0, 0])
               frontAngle(CAM_PLATE_WIDTH + 10);
            }
            // cutout for clamp
            translate([-CAM_PLATE_WIDTH/2, -NEEDLE_BED_DEPTH, -needleBedHeight])
                cube([clampWidth, clampDepth*2, clampThickness*2], center = true); 
            clampScrews();
        }
//        translate([gauge/2-CAM_PLATE_WIDTH/4,0,0]) {
//            frontRail(CAM_PLATE_WIDTH/2, rounded = true);
//            backRail(CAM_PLATE_WIDTH/2, rounded = true);
//        }
    }
}

// The clamp is screwed from below; the screws go into heat-set inserts in
// the bottom face of the carriage rest (the face the clamp sits against).
function clampScrewXs() = [- clampWidth/2 + screwHeadDiam*1.5, + clampWidth/2 - screwHeadDiam*1.5];
function clampScrewYs() = [-(NEEDLE_BED_DEPTH-clampWidth), -clampWidth*2/3];

module clampScrews() {
    // screwholes for clamp
    $fn = 50;
    for (x = clampScrewXs(), y = clampScrewYs())
        translate([-CAM_PLATE_WIDTH/2 + x, y, -needleBedHeight + clampThickness])
        insertHole(0, +1);
    translate([-CAM_PLATE_WIDTH/2,0,-needleBedHeight]) {
        translate([0,-(NEEDLE_BED_DEPTH-clampWidth),0]) {
            translate([- clampWidth/2 + screwHeadDiam*1.5, 0, 0])
            #cylinder(screwHeight*2, d = screwDiam, center = true); 
            
            translate([ - clampWidth/2 + screwHeadDiam*1.5, 0, 0])
            #cylinder((screwHeadHeight + tolerance)*2, d = screwHeadDiam, center = true); 
            
            translate([ + clampWidth/2 - screwHeadDiam*1.5, 0, 0])
            #cylinder(screwHeight*2, d = screwDiam, center = true); 
            
            translate([ + clampWidth/2 - screwHeadDiam*1.5, 0, 0])
            #cylinder((screwHeadHeight + tolerance)*2, d = screwHeadDiam, center = true); 
        }
        translate([0,-clampWidth*2/3,0]) {
            translate([- clampWidth/2 + screwHeadDiam*1.5, 0, 0])
            #cylinder(screwHeight*2, d = screwDiam, center = true); 
            
            translate([ - clampWidth/2 + screwHeadDiam*1.5, 0, 0])
            #cylinder((screwHeadHeight + tolerance)*2, d = screwHeadDiam, center = true); 
            
            translate([ + clampWidth/2 - screwHeadDiam*1.5, 0, 0])
            #cylinder(screwHeight*2, d = screwDiam, center = true); 
            
            translate([ + clampWidth/2 - screwHeadDiam*1.5, 0, 0])
            #cylinder((screwHeadHeight + tolerance)*2, d = screwHeadDiam, center = true); 
        }
    }
}

module clampUnit() {
    difference() {
        // top
        translate([-CAM_PLATE_WIDTH/2 , -NEEDLE_BED_DEPTH + clampDepth/2, -needleBedHeight + clampThickness/2])
            cube([clampWidth - tolerance*2, clampDepth - tolerance, clampThickness-tolerance], center = true); 
        clampScrews();
        for(i = [0:ceil(CAM_PLATE_WIDTH/gauge)]) {
           translate([-gauge*i, 0, 0])
           frontAngle(CAM_PLATE_WIDTH + 10);
        }
    }
    // front
    hull () {
        translate([-CAM_PLATE_WIDTH/2 , -NEEDLE_BED_DEPTH + clampThickness/2 + 12, -(needleBedHeight - tolerance) - clampHollow/2]) {
                cube([clampWidth - tolerance*2, clampThickness, clampHollow], center = true);
            
            // rounded edge, at the bottom of the jaw
            translate([0,0,-clampHollow/2 - clampJawThickness + clampThickness/2])
            rotate([0,90,0])
            cylinder(clampWidth - tolerance*2, d = clampThickness, center = true, $fn = 30);
        }  
    }
    difference() {
        // bottom
        translate([-CAM_PLATE_WIDTH/2 , -NEEDLE_BED_DEPTH + clampDepth/2 +  clampThickness/2, clampJawTopZ() - clampJawThickness/2])
        cube([clampWidth - tolerance*2, clampDepth - 25, clampJawThickness], center = true);
        
        translate([clampBoltXY()[0], clampBoltXY()[1], clampJawTopZ()]) {
            // bolt hole
            cylinder(h = clampJawThickness*3, d = clampBoltDiam + tolerance*2, center = true, $fn = 50);
            
            // nut pocket
            translate([0, 0, -(clampNutHeight + tolerance)])
            hexagon(clampNutWidth + tolerance*2, clampNutHeight + tolerance + 1);
        }        
    }
}

// position of the clamp bolt (in the frame of clampUnit()) and z of the top
// face of the bottom jaw (the table goes between it and the carriage rest)
function clampBoltXY() = [-CAM_PLATE_WIDTH/2, -clampWidth*2/3 - 18];
function clampJawTopZ() = -(needleBedHeight - tolerance) - clampHollow;
function clampJawBottomZ() = clampJawTopZ() - clampJawThickness;

// hexagonal prism, `af` across flats, standing on z = 0
module hexagon(af, h) {
    cylinder(h = h, d = af / cos(30), $fn = 6);
}

module carriageRestReport() {
    hd = screwHeadDiamSm - tolerance*2;
    hh = screwHeadHeight - tolerance*2;
    // left carriage rest with its clamp, and the mirrored right carriage rest
    // (all of them are in carriageRest.stl)
    reportJoint("clamp to carriage rest", [for (x = clampScrewXs(), y = clampScrewYs()) [-gauge - CAM_PLATE_WIDTH/2 + x, y]],
                "bottom", "carriageRest", "carriageRest", -needleBedHeight + clampThickness, +1, hd, hh, true);
    reportJoint("right carriage rest (clamp holes)", [for (x = clampScrewXs(), y = clampScrewYs()) [gauge*numNeedles + CAM_PLATE_WIDTH/2 - x, y]],
                "bottom", "carriageRest", "carriageRest", -needleBedHeight + clampThickness, +1, hd, hh, true);
}
