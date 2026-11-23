# Geometry checks

These scripts check that the SCAD model still works after you change
parameters. They render the parts with OpenSCAD and measure the STLs, so you
find problems before you print anything.

Requirements: OpenSCAD (tested with 2021.01) and Python 3 with `numpy`,
`shapely` and `matplotlib`.

## check.py

```
python3 tools/geometry_check/check.py                      # params.scad as it is
python3 tools/geometry_check/check.py --set camPlateHeight=4
python3 tools/geometry_check/check.py --ref upstream/main  # other reference
```

The script compares the model with a reference git ref (`main` by default)
and prints one line per check. It exits with status 1 if any check fails.
Renders are cached in `.geometry_check/`. The report (`report.json` and
`sections.png`) is written to `.geometry_check/report/`.

The script runs four groups of checks:

1. **Assembly.** The model leaves `tolerance` gaps between parts, so the
   script first moves each part along z until it touches the part its screws
   pull it against:
   - the sponge bar and the back cover move down onto the needlebed;
   - the carriage rests on the rails;
   - the yarn feeder moves up against the yarn carrier cover;
   - the stripper plate moves up against the feeder and the cover;
   - the yarn carrier assembly moves down onto the back plate.

   It then reports any overlap between carriage parts, and between the
   carriage (swept along x) and the needlebed.
2. **Needle.** A needle is placed in hold position (fully out): 78.6 mm from
   the back of the butt to the hook tip. The script measures:
   - the gap between the hook and the stripper plate blade;
   - the gap between the stripper plate and the needlebed (this holds the
     knitting while the needles move back);
   - the stripper plate surfaces relative to the bottom of the needle slot.

   Each value must stay close to the reference.
3. **Fasteners.** The SCAD files describe every screw with an `ECHO: JOINT`
   line (see `SCAD/modules/inserts.scad`). For each screw the script checks:
   - the depth of the insert or pilot hole;
   - the plastic wall around it;
   - the plastic under the head;
   - that the head stays below sliding faces, and that it sits flat;
   - which standard screw lengths fit.
4. **Tension cams** (`tension.py`, from the `ECHO: TENSION` line of
   `SCAD/parts/tCam.scad`). The tension cam turns about its pivot while the
   tension screw slides in the curved slot of the back plate. The script
   checks:
   - that an M3 screw slides along the whole travel of the upstream slot,
     with at least 0.2 mm of clearance;
   - that the cams do not touch the cam walls at either end of the travel;
   - the path of a needle butt (1.25 x 3.85 mm, from the technical sketch)
     through the cams at both ends of the travel. The butt must not jam, and
     the stitch cam must pull it back as far as in the reference.

   - the tension lock: the pointer tip must fit each notch of the lock
     block without touching it, the block must stop the pointer turning
     (play in degrees), the tip must go far enough into the block, and the
     pointer, lifted to change the setting, must clear the lock screw heads.

   `tension.png` shows the cams and the butt path at both ends.

## compare_stl.py

```
python3 tools/geometry_check/compare_stl.py .geometry_check/tree-*/out "STL M3 inserts"
```

This script compares freshly rendered parts with the STLs you printed. Both
must be in assembly coordinates, as exported from `SCAD/parts/*.scad`. Each
part gets one verdict:

| Verdict | Meaning |
|---|---|
| `identical` | No difference |
| `keep` | Only the printed screw holes are wider |
| `drill holes` | The new part only has bigger or deeper screw holes, or a wider tension slot; the script lists where |
| `reprint` | The shape changed away from the screw holes |

`check.py` writes the path of the rendered tree to `report.json`
(`test_tree`). Pass that path with `/out` added as the first argument.
