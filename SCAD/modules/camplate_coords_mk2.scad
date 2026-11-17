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

tPointerCoord = [40.724 - xOffset, -93.75, camHeight + camPlateHeight+ tolerance];
tensionMarksDist = -65;
tensionMarksStartAngle = 360-23.5;
tensionAngleInc = 1;