/*

Values in `camelCase` are user-variable (within reason); 
values like numNeedles and screwDiam, etc.,  can be modified to
accommodate user preference or hardware subsitution. 

Values in `ALL_CAPS` should be considered CONSTANTS and should
only be modified with *extreme caution* as they will affect the 
relationship between the needles and the cams, which could
prevent stitches from forming correctly.

I recommend only modifying these constants if you are also 
making changes to the cam design in the technical sketch.
*/

$fn = 50;

STANDARD_GAUGE = 4.5;
MID_GAUGE = 6.5;
BULKY_GAUGE = 9.0;

gauge = STANDARD_GAUGE; // I recommend using one of the predefined gauges above
numNeedles = 25;
tolerance = 0.2; // allows a bit of room for parts that have to fit together; adjust according to your printer's precision

// ---
// Hardware dimensions
// (actual measurements, no tolerances)
//
// Metric version: M3 socket head cap screws (ISO 4762, head 5.5 x 3.0 mm)
// threaded into M3 heat-set inserts. The upstream design used #6-32 and
// #4-40 pan head screws that self-tapped into the printed parts. Here screw
// holes are clearance holes and the thread is in an insert, except for the
// stripper plate screws (see stripperPlateInserts).

// - M3 screws (replace the #6-32 screws)
screwDiam = 3.2; // clearance hole
screwHeight = 18;
// The head diameter also sets how far the screws sit from the part edges
// (screwHeadDiam * 1.5), so it is kept from the #6-32 design: changing it
// moves every carriage screw hole.
screwHeadDiam = 6.75 + tolerance * 2;
screwHeadHeight = 3.0 + tolerance * 2;

// - M3 screws (replace the #4-40 screws)
screwDiamSm = 3.2; // clearance hole
screwHeightSm = 14.62;
screwHeadHeightSm = 3.0 + tolerance * 2;
screwHeadDiamSm = 5.68 + tolerance * 2;

// - M3 heat-set inserts
insertDiameter = 4.0; // hole diameter recommended by the insert vendor
insertLength = 5.7;
insertDepth = insertLength + 1; // the vendor recommends 1 mm of extra hole depth
insertWallMin = 1.2; // minimum plastic around an insert hole (used by the checks)
// Pilot hole for M3 screws that thread straight into the plastic
screwTapDiam = 2.5;
// Width of the curved slot in the back plate that the tension screw slides in
// (upstream: 2.96, for #4-40 screws)
tensionSlotWidth = screwDiamSm + tolerance;

// ---
// Needle dimensions
// - Brother needles
BUTT_HEIGHT = 15;
NEEDLE_WIDTH = 1.25;
NEEDLE_LEG_HEIGHT = 1.85;
HOOK_DIAM = 3.5;

// ---
// Needle Bed Zones
BACK_COVER = 45;
OOW_TRACK = 8;
B_TRACK = 42; // will divvy up working tracks (B & C position) later
C_TRACK = 0;
WORKING_TRACK = B_TRACK + C_TRACK;
HOLD_TRACK = 8;
SPONGE_BAR = 12;
COMB = 29;
NEEDLE_EXTENSION = 34.5;

// ---
// Needle bed dimensions
NEEDLE_BED_DEPTH = BACK_COVER + OOW_TRACK + WORKING_TRACK + HOLD_TRACK + SPONGE_BAR + COMB;
needleBedHeight = screwHeight + 2;
needleSlotHeight = NEEDLE_LEG_HEIGHT * 2 + screwHeadHeight;
needleSlotWidth = NEEDLE_WIDTH + 0.25; // add a small amount of clearance
combWidth = gauge*2/3; // width of cutouts for stitch formation; this gives room for the thickness of the yarn looped around the needle when it pulls back into the slot, but has to balance leaving enough material for the remaining "teeth" to not be too fragile
spongeThickness = 2.5;
spongeBarThickness = needleSlotHeight - NEEDLE_LEG_HEIGHT - spongeThickness;
YARN_DEPOSIT_Y = -155.1;
YARN_DEPOSIT_Z = -needleSlotHeight + HOOK_DIAM;
connectorOffset = 20;

screwPlacement = 3; // how many needles from edge of bed; min 2, max floor(numNeedles/2)

// ---
// Carriage dimensions
// refer to technical sketch
camHeight = BUTT_HEIGHT; // thickness of the tracks the needles ride along
// Plate behind the cams (upstream: 4). It also sets the thickness of the
// yarn feeder and of the yarn carrier cover. 6.7 = insertDepth, so the
// heat-set inserts in the back plate and in the tension cam pivots fit.
camPlateHeight = 6.7;
CAM_PLATE_WIDTH = 91 * 2;
CAM_PLATE_DEPTH = NEEDLE_BED_DEPTH - COMB + 6;

// Size of the stripper plate and of the front edge of the yarn carrier
// (feeder, cover and stripper screw row). Upstream scaled these with
// camPlateHeight, but they hold the knitting against the needlebed and must
// clear the needle hook, so they are tied to the needle and not to the cam
// plate thickness. Keep the upstream value unless the needles change.
STRIPPER_PLATE_SIZE = 4;
// Height of the bottom face of the yarn feeder above the needlebed surface
// (the top face of the stripper plate sits `tolerance` below it).
YARN_FEEDER_Z = 2;
// Plastic left under the head of the stripper plate screws, at the bottom of
// the yarn carrier cover.
stripperScrewSeat = 1.0;
// The stripper plate screws sit next to the face that the needle hook passes
// at 0.2 mm. An insert there leaves only 0.8 mm of wall on that face, and
// pressing it in can bulge the face into the needle path, so by default these
// screws thread straight into a pilot hole (as upstream did with #4-40).
stripperPlateInserts = false;
// y of the front edge of the yarn feeder and of the yarn carrier cover
YARN_CARRIER_FRONT_Y = -(NEEDLE_BED_DEPTH + NEEDLE_EXTENSION + STRIPPER_PLATE_SIZE + 2);
// y of the back edge of the yarn feeder (the front edge of the back plate)
YARN_FEEDER_BACK_Y = -(NEEDLE_BED_DEPTH - COMB + 6 + tolerance);

railDepth = 8;
railHeight = 8; // ???
xOffset = 16.5;
//vCamScrews = [[34-xOffset, -90.25, 0],[58-xOffset, -74.25, 0],[86-xOffset,-90.25, 0]];

echo(needleSlotHeight);

assert(insertDiameter > screwDiam, "insertDiameter must be larger than the clearance hole");



