include<params.scad>;

camClearance = 2;

tCamCoords = [46.409 - xOffset, -90.875, camClearance]; // mk2
tPivotCoords = [93.191 - xOffset, -90.75, camHeight + camPlateHeight/2 - 1]; // mk2
// centre of the tension screw hole in TCam_mk2.svg (upstream had a hex nut
// trap there; the screw now goes into a heat-set insert)
tensionScrewCoords = [55.191 - xOffset, -68.812, camClearance]; // mk2
tSlotCoords = [53.62 - xOffset, -70.401, camHeight - 1]; // mk2
// Usable width of the tension slot in TSlot.svg (drawn for #4-40 screws): the
// largest screw that slides along the whole slot as the cam turns (the slot
// is not exactly centred on the arc of the screw). tSlots() in backPlate.scad
// widens it to tensionSlotWidth.
TSLOT_SVG_WIDTH = 2.85;
// Position of the tension screw when the tension cam is turned by `a` degrees
// about its pivot (0 = the position modelled here, the tightest setting).
function tensionScrewAt(a) = let (p = tPivotCoords, s = tensionScrewCoords, c = cos(a), n = sin(a))
    [p[0] + (s[0] - p[0])*c - (s[1] - p[1])*n, p[1] + (s[0] - p[0])*n + (s[1] - p[1])*c, s[2]];
frontWallCoords = [19.5 - xOffset, -97, camClearance]; // mk2
backWallCoords = [16.5 - xOffset, -67.85, camClearance]; // mk2
bumperCoords = [91.5 - xOffset, -75.85, camClearance]; // mk

// Tension pointer and lock block (see the tension lock values in params.scad).
// Both are drawn in a frame centred on the pivot, with x along the pointer
// (towards the tension screw) at the tightest setting.
function tPointerDir() = atan2(tensionScrewCoords[1] - tPivotCoords[1], tensionScrewCoords[0] - tPivotCoords[0]);
function tensionScrewRadius() = norm([tensionScrewCoords[0] - tPivotCoords[0], tensionScrewCoords[1] - tPivotCoords[1]]);
// centres of the circles whose hull is the pointer: pivot end, the end of
// the straight part and the rounded tip
function tPointerTipCentre() = tPointerLength - tPointerTipRadius / sin(tPointerTipAngle/2);
function tPointerShoulder() = tPointerTipCentre() - (tPointerWidth/2 - tPointerTipRadius) / sin(tPointerTipAngle/2);
// lock block: inner face (crests), bottom of the notches, outer face
function tensionLockInner() = tPointerLength - tensionLockDepth;
function tensionLockNotchBottom() = tPointerTipCentre() + tPointerTipRadius + tensionLockClearance;
function tensionLockOuter() = tensionLockNotchBottom() + tensionLockWall;
function tensionLockMid() = (tensionLockInner() + tensionLockOuter()) / 2;
// The block is fixed with one M3 screw at each end, into inserts in the top
// face of the back plate, beyond the reach of the pointer: tip half width at
// the inner face + 0.5 mm of slot over-travel + screw head + 0.5 mm.
function tensionLockScrewOffset() =
    let (half = (tPointerLength - tensionLockInner()) * tan(tPointerTipAngle/2) + tensionLockClearance)
    (half + 0.5 + screwHeadDiamSm/2 + 0.5) / tensionLockMid() * 180 / PI;
function tensionLockScrewAngles() = [max(tensionLockAngles) + tensionLockScrewOffset(),
                                     min(tensionLockAngles) - tensionLockScrewOffset()];
// screw positions of the left block, in assembly coordinates
function tensionLockScrewsXY() = [for (a = tensionLockScrewAngles())
    [tPivotCoords[0] + tensionLockMid() * cos(tPointerDir() + a),
     tPivotCoords[1] + tensionLockMid() * sin(tPointerDir() + a)]];

assert(tPointerShoulder() > tensionScrewRadius() + tPointerWidth/2,
       "the pointer tip starts before the tension screw: make it longer or the tip sharper");