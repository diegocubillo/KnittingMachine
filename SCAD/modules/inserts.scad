include<params.scad>;

// Hole for an M3 heat-set insert, centred on the local origin in x/y.
// faceZ: z of the face the insert is pressed in from.
// dir:   -1 when the hole goes down from that face, +1 when it goes up.
// The hole overshoots the face by 0.01 mm so the cut is clean.
module insertHole(faceZ, dir) {
    threadHole(faceZ, dir, insertDiameter);
}

// Pilot hole for an M3 screw threaded straight into the plastic, same depth
// as an insert hole.
module pilotHole(faceZ, dir) {
    threadHole(faceZ, dir, screwTapDiam);
}

module threadHole(faceZ, dir, d) {
    translate([0, 0, dir < 0 ? faceZ - insertDepth : faceZ - 0.01])
    cylinder(h = insertDepth + 0.01, d = d);
}

// Fastener descriptions read by tools/geometry_check (one ECHO line each).
// head_side: "top" when the screw goes in from above, "bottom" from below.
// flush:     true when the head must stay below the surface around it
//            (sliding faces or faces that sit on other parts).
// thread:    "insert" (heat-set insert) or "pilot" (screw threads into the plastic).
module reportJoint(name, points, head_side, head_part, insert_part, insert_face_z, insert_dir,
                   head_diam, head_height, flush, thread = "insert") {
    echo(JOINT = [name, points, head_side, head_part, insert_part, insert_face_z, insert_dir,
                  head_diam, head_height, flush, thread,
                  thread == "insert" ? insertDiameter : screwTapDiam]);
}
