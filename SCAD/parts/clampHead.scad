include<../modules/params.scad>;

// Fits over the tip of the clamp bolt to secure the clamp to the table: the
// bolt tip threads into the ball (hole slightly under the bolt diameter), and
// the captive ball pivots inside the cone, so do not print with supports!
// The wide face of the cone goes against the underside of the table.

module clampHead() {
   $fn = 50;
   boltDiam = clampBoltDiam - tolerance;    // upstream: 7.8 for a 5/16" eyebolt
   
   // ball 
   difference() {
       sphere(d = boltDiam + 3);
       cylinder(h = boltDiam, d = boltDiam);
   }
   
   // socket
   difference() {
       translate([0,0,-(boltDiam) - tolerance *2]) 
       cylinder(h = boltDiam + 4, d1 = boltDiam * 4, d2 = boltDiam * 2);
       sphere(d = boltDiam + 3 + tolerance * 3);
   }
}

clampHead();
