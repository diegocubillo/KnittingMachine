include<params.scad>;

camClearance = 2;

tCamCoords = [46.409 - xOffset, -90.875, camClearance]; // mk2
tPivotCoords = [93.191 - xOffset, -90.75, camHeight + camPlateHeight/2 - 1]; // mk2
nutCoords = [51.746 - xOffset, -72.624, camClearance]; // mk2
// centre of the tension screw hole in TCam_mk2.svg (the centre of Hex_mk2.svg placed at nutCoords)
tensionScrewCoords = [nutCoords[0] + 3.445, nutCoords[1] + 3.812, camClearance];
tSlotCoords = [53.62 - xOffset, -70.401, camHeight - 1]; // mk2
frontWallCoords = [19.5 - xOffset, -97, camClearance]; // mk2
backWallCoords = [16.5 - xOffset, -67.85, camClearance]; // mk2
bumperCoords = [91.5 - xOffset, -75.85, camClearance]; // mk

tPointerCoord = [40.724 - xOffset, -93.75, camHeight + camPlateHeight+ tolerance];
tensionMarksDist = -65;
tensionMarksStartAngle = 360-23.5;
tensionAngleInc = 1;