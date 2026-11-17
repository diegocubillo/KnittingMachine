#!/usr/bin/env python3
"""Compare printed STLs with freshly rendered ones, to decide what to reprint.

For every part, the two meshes are cut with planes x = const and the
material that only one of them has is integrated:
  removed: material the printed part has and the new one does not
  added:   material the new part has and the printed one does not
Verdicts:
  identical    no difference above mesh noise
  keep         only the printed screw holes are wider than the new ones
  drill holes  the new part only has bigger or deeper screw holes
  reprint      the shape changed away from the screw holes

usage:
  python3 tools/geometry_check/compare_stl.py NEW_DIR PRINTED_DIR [--probe probe.json]
      [--map new=printed1+printed2 ...]
NEW_DIR holds <part>.stl as rendered from SCAD/parts/<part>.scad (for example
.geometry_check/tree-*/out); PRINTED_DIR holds the STLs that were printed.
Both must be in assembly coordinates (as exported from SCAD/parts). A part
that was only moved (same shape, other position) is aligned by its bounding box.
"""
import argparse
import json
import os
import sys

import numpy as np
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from meshsec import load_stl, section  # noqa: E402

DEFAULT_MAP = {
    'needlebed': ['needleBed_std', 'needlebed_std', 'needlebed'],
    'backCover': ['backCover_std', 'backCover'],
    'spongeBar': ['spongeBar_std', 'spongeBar'],
    'carriageRest': ['carriageRest_L+carriageRest_R+clamp', 'carriageRest'],
    'backPlate': ['backPlate', 'backPlate_mk2'],
    'tCam': ['tCam', 'tCam_mk2'],
    'tPointer': ['tPointer'],
    'stripperPlate': ['stripperPlate'],
    'yarnFeeder': ['yarnFeeder'],
    'yarnCarrierCover': ['yarnCarrierCover'],
}
HOLE_ZONE = 3.9    # mm around a screw axis (widest recess is 7.15 mm)
NOISE = 2.0        # mm^3 (mesh tessellation, 0.1 mm hole depth differences)


def load_many(d, spec):
    meshes = []
    for name in spec.split('+'):
        p = os.path.join(d, name + '.stl')
        if not os.path.exists(p):
            return None, None
        meshes.append(load_stl(p))
    return np.concatenate(meshes), spec


def bbox(T):
    P = T.reshape(-1, 3)
    return P.min(0), P.max(0)


def hole_zone(points, x):
    """Strips in y (as intervals) of the screw hole zones crossing plane x."""
    out = []
    for px, py in points:
        dx = abs(x - px)
        if dx < HOLE_ZONE:
            w = (HOLE_ZONE ** 2 - dx ** 2) ** 0.5
            out.append((py - w, py + w))
    return out


def compare(new, old, points, step=0.3):
    (n0, n1), (o0, o1) = bbox(new), bbox(old)
    shift = np.zeros(3)
    if np.abs((n1 - n0) - (o1 - o0)).max() < 0.05 and np.abs(n0 - o0).max() > 0.05:
        shift = n0 - o0                      # same size, other place: align
        old = old + shift
    lo, hi = min(n0[0], o0[0] + shift[0]), max(n1[0], o1[0] + shift[0])
    vol = {'removed_at_holes': 0.0, 'removed_elsewhere': 0.0, 'added_at_holes': 0.0, 'added_elsewhere': 0.0}
    where = {'removed_elsewhere': [], 'added_elsewhere': []}
    holes_hit = {}
    from shapely.geometry import box
    for x in np.arange(lo + step / 2, hi, step):
        A, B = section(old, x), section(new, x)
        A = A if A is not None else None
        B = B if B is not None else None
        for kind, g in (('removed', A.difference(B) if A and B else A),
                        ('added', B.difference(A) if A and B else B)):
            if g is None or g.is_empty:
                continue
            g = g.buffer(-0.04).buffer(0.04)      # drop mesh slivers
            if g.is_empty:
                continue
            zone = unary_union([box(a, -500, b, 500) for a, b in hole_zone(points, x)]) if points else None
            at = g.intersection(zone) if zone is not None and not zone.is_empty else None
            a_at = at.area if at is not None else 0.0
            vol[f'{kind}_at_holes'] += a_at * step
            rest = g.area - a_at
            vol[f'{kind}_elsewhere'] += rest * step
            if rest > 0.05:
                el = g.difference(zone) if zone is not None and not zone.is_empty else g
                b = el.bounds
                where[f'{kind}_elsewhere'].append((x, b))
            if kind == 'removed' and a_at > 0.05:
                b = at.bounds
                for px, py in points:
                    if abs(x - px) < HOLE_ZONE and b[0] < py + HOLE_ZONE and b[2] > py - HOLE_ZONE:
                        k = (round(px, 2), round(py, 2))
                        z0, z1 = holes_hit.get(k, (np.inf, -np.inf))
                        holes_hit[k] = (min(z0, b[1]), max(z1, b[3]))
    vol = {k: round(v, 1) for k, v in vol.items()}
    ext = {}
    for k, lst in where.items():
        if lst:
            xs = [x for x, _ in lst]
            ext[k] = {'x': (round(min(xs), 1), round(max(xs), 1)),
                      'y': (round(min(b[0] for _, b in lst), 1), round(max(b[2] for _, b in lst), 1)),
                      'z': (round(min(b[1] for _, b in lst), 1), round(max(b[3] for _, b in lst), 1))}
    if all(v < NOISE for v in vol.values()):
        verdict = 'identical'
    elif vol['added_elsewhere'] >= NOISE or vol['removed_elsewhere'] >= NOISE:
        verdict = 'reprint'
    elif vol['removed_at_holes'] >= NOISE:
        verdict = 'drill holes'
    else:
        verdict = 'keep'     # only the printed holes are wider than the new ones
    if verdict != 'drill holes':
        holes_hit = {}
    return {'verdict': verdict, 'aligned_shift': [round(v, 2) for v in shift], 'volumes_mm3': vol,
            'extent_elsewhere': ext,
            'holes_to_open (x, y): z range': {f'{k}': [round(z, 2) for z in v] for k, v in sorted(holes_hit.items())}}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('new_dir')
    ap.add_argument('printed_dir')
    ap.add_argument('--probe', help='probe.json with the screw positions (default: NEW_DIR/probe.json)')
    ap.add_argument('--map', action='append', default=[], metavar='NEW=PRINTED[+PRINTED]')
    ap.add_argument('--json', help='write the results to this file')
    a = ap.parse_args()
    probe = json.load(open(a.probe or os.path.join(a.new_dir, 'probe.json')))
    points = [tuple(p) for j in probe['joints'] for p in j['points']]
    mapping = {k: list(v) for k, v in DEFAULT_MAP.items()}
    for m in a.map:
        k, v = m.split('=', 1)
        mapping[k] = [v]
    res = {}
    for part, specs in mapping.items():
        newf = os.path.join(a.new_dir, part + '.stl')
        if not os.path.exists(newf):
            continue
        old = name = None
        for s in specs:
            old, name = load_many(a.printed_dir, s)
            if old is not None:
                break
        if old is None:
            res[part] = {'verdict': 'not printed (no STL found)'}
            continue
        print(f'comparing {part} <-> {name}', file=sys.stderr, flush=True)
        res[part] = {'printed': name, **compare(load_stl(newf), old, points)}
    for part, r in res.items():
        print(f'{part:17s} {r["verdict"]:12s} {r.get("printed", "")}')
        if 'volumes_mm3' in r:
            print(f'{"":17s} {r["volumes_mm3"]}')
            for k, v in r['extent_elsewhere'].items():
                print(f'{"":17s} {k}: {v}')
            if r['verdict'] == 'drill holes':
                for k, v in r['holes_to_open (x, y): z range'].items():
                    print(f'{"":17s} hole at {k}: z {v}')
    if a.json:
        json.dump(res, open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
