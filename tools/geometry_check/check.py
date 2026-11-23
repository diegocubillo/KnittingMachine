#!/usr/bin/env python3
"""Functional geometry checks of the SCAD model, run on rendered STLs.

Checks, for the model in the working tree (optionally with parameter
overrides), compared with a reference git ref (upstream geometry):

  1. Assembly: every part is moved until it touches the part its screws pull
     it against (the SCAD model leaves `tolerance` gaps), then the parts are
     checked for interference.
  2. Needle: a needle in hold position (fully out) against the stripper plate:
     clearance under the hook, and the gap between stripper plate and
     needlebed that holds the knitting while the needles retract. Both are
     compared with the reference.
  3. Fasteners: for every screw described by the SCAD files (ECHO JOINT):
     insert hole depth and wall, plastic under the head, head recess on
     faces that must stay flush, and the screw lengths that fit.
  4. Tension cams (tension.py): travel and clearance of the tension screw in
     its slot, cams against the cam walls, and the path of a needle butt at
     both ends of the travel.

usage:
  python3 tools/geometry_check/check.py [--ref main] [--set camPlateHeight=4 ...]
                                        [--out DIR] [--no-plot]
Exit status 1 when a check fails. Needs openscad, numpy, shapely, matplotlib.
"""
import argparse
import json
import os
import sys

import numpy as np
from shapely.geometry import LineString, box
from shapely.ops import unary_union

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scad  # noqa: E402
import tension  # noqa: E402
from meshsec import load_stl, section  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# Needle (KR830/KR838/KR850), measured: back of the butt to the hook tip
BUTT_BACK_TO_TIP = 78.6
HOOK_LEN = 9.5

BED = ['needlebed', 'spongeBar', 'backCover']
CARRIAGE = ['backPlate', 'yarnCarrierCover', 'yarnFeeder', 'stripperPlate', 'tCam', 'tPointer', 'tensionLock']
GROUPS = {'bed': BED, 'carriage': CARRIAGE, 'rest': ['carriageRest']}
STD_SCREW_LENGTHS = [4, 5, 6, 8, 10, 12, 14, 16, 18, 20, 22, 25, 30, 35, 40]

# Pass limits
HOOK_GAP_RANGE = (0.1, 0.6)        # mm between the needle hook and the stripper plate blade
STRIPPER_BED_GAP_TOL = 0.5         # mm allowed deviation from the reference
PROFILE_TOL = 0.5                  # mm allowed deviation of stripper plate surfaces (needle frame)
INTERFERENCE_MAX = 1.0             # mm^3 (mesh noise)
HEAD_GRIP = (0.4, 1.0)             # mm plastic under a screw head: fail below, warn below
HEAD_RECESS_WARN = 0.2             # mm
HEAD_OVERHANG_WARN = 0.1           # mm a part of the head may float above a lower face


# ---------------------------------------------------------------- geometry utils

def zint(geom, y, z0=-300.0, z1=300.0):
    """Vertical material intervals (z0, z1) of a section at y."""
    if geom is None or geom.is_empty:
        return []
    c = geom.intersection(LineString([(y, z0), (y, z1)]))
    if c.is_empty:
        return []
    segs = c.geoms if hasattr(c, 'geoms') else [c]
    return sorted((s.bounds[1], s.bounds[3]) for s in segs if s.length > 1e-4)


def merge(iv, gap=0.3):
    out = []
    for a, b in sorted(iv):
        if out and a <= out[-1][1] + gap:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def tr(T, dy=0.0, dz=0.0):
    T = T.copy()
    T[:, :, 1] += dy
    T[:, :, 2] += dz
    return T


class Model:
    """Rendered parts of one tree, with cached sections."""

    def __init__(self, tree, files, info):
        self.tree, self.info = tree, info
        self.P = info['params']
        self.mesh = {p: load_stl(f) for p, f in files.items()}
        self.dz = {p: 0.0 for p in self.mesh}
        self._sec = {}

    def sec(self, part, x, assembled=False):
        dz = self.dz.get(part, 0.0) if assembled else 0.0
        k = (part, round(float(x), 3), round(dz, 4))
        if k not in self._sec:
            T = self.mesh.get(part)
            self._sec[k] = None if T is None else section(tr(T, dz=dz) if dz else T, float(x))
        return self._sec[k]

    def material(self, parts, x, y, z):
        return any(a - 1e-6 <= z <= b + 1e-6 for p in parts for a, b in zint(self.sec(p, x), y))


# ---------------------------------------------------------------- 1. assembly

def gap(fixed, moving, xs, direction, dy=0.25):
    """How far `moving` can travel along z (direction -1 down, +1 up) before it
    touches `fixed`; negative when they already overlap. fixed/moving: x -> section."""
    best = np.inf
    for x in xs:
        A, B = fixed[x], moving[x]
        if A is None or B is None or A.is_empty or B.is_empty:
            continue
        lo, hi = max(A.bounds[0], B.bounds[0]), min(A.bounds[2], B.bounds[2])
        for y in np.arange(lo, hi, dy):
            for a0, a1 in zint(A, y):
                for b0, b1 in zint(B, y):
                    if direction < 0 and b1 > a1 + 1e-6:
                        best = min(best, b0 - a1)
                    if direction > 0 and b0 < a0 - 1e-6:
                        best = min(best, a0 - b1)
    return best


def solve_assembly(M):
    """Clamp chain: spongeBar/backCover screwed down onto the needlebed, the
    carriage rests on the rails, the yarn feeder is screwed up to the cover,
    the stripper plate up to feeder + cover, and that subassembly down onto
    the back plate. Sets M.dz and returns the clamp gaps."""
    xb = np.arange(1.0, 110.0, 3.0)
    xc = np.arange(0.5, M.P['CAM_PLATE_WIDTH'], 3.0)
    S = lambda p, xs, dz=0.0: {x: section(tr(M.mesh[p], dz=dz), x) for x in xs}  # noqa: E731
    bed = S('needlebed', xb)
    dz = {}
    for p in ('spongeBar', 'backCover'):
        dz[p] = -gap(bed, S(p, xb), xb, -1)
    rails = {p: S(p, xb, dz[p]) for p in ('spongeBar', 'backCover')}
    bedall = {x: unary_union([g for g in (bed[x], rails['spongeBar'][x], rails['backCover'][x]) if g])
              for x in xb}
    dz['backPlate'] = -gap(bedall, S('backPlate', xb), xb, -1)
    cover, feeder, plate = S('yarnCarrierCover', xc), S('yarnFeeder', xc), S('stripperPlate', xc)
    dfeed = gap(cover, feeder, xc, +1)
    feeder_up = S('yarnFeeder', xc, dfeed)
    cf = {x: unary_union([g for g in (cover[x], feeder_up[x]) if g]) for x in xc}
    dplate = gap(cf, plate, xc, +1)
    dsub = -gap(S('backPlate', xc, dz['backPlate']), cover, xc, -1)
    dz['yarnCarrierCover'] = dsub
    dz['yarnFeeder'] = dsub + dfeed
    dz['stripperPlate'] = dsub + dplate
    for p in ('tCam', 'tPointer', 'tensionLock'):
        dz[p] = dz['backPlate']
    M.dz.update(dz)
    return {'dz': {k: round(float(v), 3) for k, v in dz.items()},
            'feeder_to_cover': round(float(dfeed), 3), 'stripper_to_feeder': round(float(dplate), 3)}


def interference(M):
    """Overlap volume (mm^3) between carriage parts as assembled, and overlap
    area (mm^2, side view) of the carriage, swept along x, with the bed."""
    W = M.P['CAM_PLATE_WIDTH']
    xs = np.arange(0.5, W, 1.0)
    parts = ['backPlate', 'yarnCarrierCover', 'yarnFeeder', 'stripperPlate', 'tCam', 'tPointer', 'tensionLock']
    parts = [p for p in parts if p in M.mesh]
    res = {}
    for i, a in enumerate(parts):
        for b in parts[i + 1:]:
            v = 0.0
            for x in xs:
                A, B = M.sec(a, x, True), M.sec(b, x, True)
                if A is not None and B is not None:
                    v += A.intersection(B).area * 1.0
            res[f'{a} x {b}'] = round(v, 2)
    g = M.P['gauge']
    xu = np.linspace(10 * g - g / 2 + 0.01, 10 * g + g / 2 - 0.01, 9)
    bed = unary_union([s for p in BED for x in xu for s in [M.sec(p, x, True)] if s is not None])
    carr = unary_union([s for p in parts for x in np.arange(0.5, W, 2.0) for s in [M.sec(p, x, True)]
                        if s is not None])
    res['carriage (swept) x bed [mm2]'] = round(carr.intersection(bed).area, 2)
    return res


# ---------------------------------------------------------------- 2. needle

def needle_profile(P, tip_y):
    zb = -P['needleSlotHeight']
    stem = box(tip_y + HOOK_LEN, zb, tip_y + BUTT_BACK_TO_TIP + 44.0, zb + P['NEEDLE_LEG_HEIGHT'])
    hook = box(tip_y, zb, tip_y + HOOK_LEN, zb + P['HOOK_DIAM'])
    return unary_union([stem, hook])


def needle_checks(M):
    P = M.P
    W = P['CAM_PLATE_WIDTH']
    xs = np.arange(0.05, W, 0.25)
    sp = unary_union([s for x in xs for s in [M.sec('stripperPlate', x, True)] if s is not None])
    fe = unary_union([s for x in xs for s in [M.sec('yarnFeeder', x, True)] if s is not None])
    g = P['gauge']
    bed = unary_union([s for x in np.linspace(10 * g - g / 2 + .01, 10 * g + g / 2 - .01, 19)
                       for s in [M.sec('needlebed', x, True)] if s is not None])
    tip = -(P['NEEDLE_BED_DEPTH'] + P['NEEDLE_EXTENSION'])
    zb = -P['needleSlotHeight']
    nd = needle_profile(P, tip)
    under = []
    for y in np.arange(tip + 0.1, tip + HOOK_LEN, 0.25):
        c = [iv for iv in zint(sp, y) if iv[1] <= zb + 1.0]
        if c:
            under.append(zb - max(iv[1] for iv in c))
    # stripper plate surfaces in the needle frame (z' = z + needleSlotHeight)
    ys = np.arange(-178.0, -146.0, 2.0)
    blade = []
    for y in ys:
        c = zint(sp, y)
        blade.append(max(b for a, b in c if b <= zb + 1.0) - zb if any(b <= zb + 1.0 for a, b in c) else None)
    wall = []
    for zp in np.arange(0.0, 6.0, 1.0):
        c = sp.intersection(LineString([(tip - 20, zb + zp), (tip + 3, zb + zp)]))
        wall.append(None if c.is_empty else c.bounds[2] - tip)
    return {
        'hook_gap_at_tip': round(under[0], 3) if under else None,
        'hook_gap_min': round(min(under), 3) if under else None,
        'needle_x_stripper_area': round(nd.intersection(sp).area, 3),
        'stripper_to_bed_gap': round(sp.distance(bed), 3),
        'needle_to_feeder': round(nd.distance(fe), 3),
        'blade_top_needle_frame': [None if v is None else round(v, 3) for v in blade],
        'front_wall_from_tip': [None if v is None else round(v, 3) for v in wall],
    }, {'sp': sp, 'fe': fe, 'bed': bed, 'needle': nd, 'zb': zb}


# ---------------------------------------------------------------- 3. fasteners

def _probes(x, y, r):
    return [(x, y + r), (x, y - r), (x + r, y), (x - r, y)]


def joint_point(M, j, x, y):
    P = M.P
    group = next(g for g in GROUPS.values() if j['insert_part'] in g)
    group = [p for p in group if p in M.mesh]
    ip, hp = j['insert_part'], j['head_part']
    face, idir = j['insert_face_z'], j['insert_dir']
    L, D = P['insertLength'], j['hole_diam']
    r_ins = D / 2
    # only look for the head within this distance of the thread (the carriage
    # rest clamp has a second jaw far below the screws)
    win = (face - 25.0, face + 25.0)

    def ints(part, px, py):
        return [(max(s, win[0]), min(t, win[1])) for s, t in zint(M.sec(part, px), py)
                if t > win[0] and s < win[1]]
    a, b = (face - L, face) if idir < 0 else (face, face + L)
    top = j['head_side'] == 'top'
    r = {}

    # insert hole depth, measured just inside the hole wall
    depths = []
    for px, py in _probes(x, y, r_ins - 0.25) + [(x, y)]:
        iv = ints(ip, px, py)
        if idir < 0:
            below = [t for s, t in iv if t < face - 0.05]
            depths.append(face - max(below) if below else np.inf)
        else:
            above = [s for s, t in iv if s > face + 0.05]
            depths.append(min(above) - face if above else np.inf)
    r['insert_hole_depth'] = round(min(depths), 2)

    # plastic around the insert (radial wall in 4 directions, over the insert length)
    walls = []
    for ux, uy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        w = 0.0
        while w < 6.0:
            px, py = x + ux * (r_ins + 0.1 + w), y + uy * (r_ins + 0.1 + w)
            if not all(M.material([ip], px, py, z) for z in np.linspace(a + 0.3, b - 0.3, 4)):
                break
            w += 0.2
        walls.append(round(w, 1))
    r['insert_wall'] = min(walls)

    # head seat: first material met by the head, just outside the clearance hole
    rp = (P['screwDiamSm'] / 2 + j['head_diam'] / 2) / 2
    seats, grips, stacks, seat_part = [], [], [], None
    for px, py in _probes(x, y, rp):
        allv = [(s, t, p) for p in group for s, t in ints(p, px, py)]
        if not allv:
            continue
        s, t, p = max(allv, key=lambda v: v[1]) if top else min(allv, key=lambda v: v[0])
        seat = t if top else s
        seats.append(seat)
        seat_part = p
        grips.append(t - s)
        blk = [m for m in merge([(s2, t2) for s2, t2, _ in allv]) if m[0] - 1e-6 <= seat <= m[1] + 1e-6]
        stacks.append(blk[0][1] - blk[0][0] if blk else 0.0)
    if not seats:
        r['error'] = 'no material around the head'
        return r
    seat = max(seats) if top else min(seats)
    r['head_seat_z'] = round(seat, 2)
    r['head_on'] = seat_part
    r['plastic_under_head'] = round(min(grips), 2)
    r['clamped_stack'] = round(min(stacks), 2)
    # how far part of the head hangs over a lower surface (0 = fully seated)
    r['head_overhang'] = round(abs(max(seats) - min(seats)), 2)

    # head recess on faces that must stay flush: the outer face of the head
    # part around the head (highest point for heads on top, lowest for heads
    # underneath) must be beyond the end of the head
    if j['flush']:
        rec = []
        for ux, uy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            # walk out of the head recess (it can be wider than the head)
            for rr in np.arange(j['head_diam'] / 2 + 0.2, j['head_diam'] / 2 + 3.0, 0.2):
                iv = ints(hp, x + ux * rr, y + uy * rr)
                if not iv:
                    continue
                face_z = max(t for s, t in iv) if top else min(s for s, t in iv)
                if abs(face_z - seat) > 0.05:
                    rec.append(face_z - (seat + j['head_height']) if top
                               else (seat - j['head_height']) - face_z)
                    break
        r['head_recess'] = round(max(rec), 2) if rec else None

    # screw lengths: the tip must stay in the hole and not leave the part
    axis = [(s, t) for p in group for s, t in ints(p, x, y)]
    outer = [(s, t) for px, py in _probes(x, y, r_ins + 0.6) for s, t in ints(ip, px, py)]
    if top:
        hole_end = max([t for s, t in axis if t < seat - 0.05], default=-np.inf)
        part_end = min([s for s, t in outer], default=-np.inf)
        max_len = seat - max(hole_end, part_end)
        eng = lambda Ls: max(0.0, min(b, seat) - max(seat - Ls, a))  # noqa: E731
    else:
        hole_end = min([s for s, t in axis if s > seat + 0.05], default=np.inf)
        part_end = max([t for s, t in outer], default=np.inf)
        max_len = min(hole_end, part_end) - seat
        eng = lambda Ls: max(0.0, min(seat + Ls, b) - max(a, seat))  # noqa: E731
    ok = [Ls for Ls in STD_SCREW_LENGTHS if Ls <= max_len - 0.3 and eng(Ls) >= 0.75 * L]
    full = [Ls for Ls in ok if eng(Ls) >= L - 0.01]
    r['max_screw_length'] = round(max_len, 1)
    r['screw'] = f'M3x{(full or ok)[0] if (full or ok) else "?"}'
    r['screw_options'] = ok
    return r


def fastener_checks(M, joints):
    out = []
    for j in joints:
        for x, y in j['points']:
            r = joint_point(M, j, x, y)
            out.append({'joint': j['name'], 'x': round(x, 2), 'y': round(y, 2),
                        'thread': j['thread'], 'thread_part': j['insert_part'], **r})
    return out


# ---------------------------------------------------------------- verdicts

def verdicts(test, ref, P):
    rows = []

    def add(name, value, status, note=''):
        rows.append({'check': name, 'value': value, 'status': status, 'note': note})

    n, nr = test['needle'], ref['needle']
    hg = n['hook_gap_min']
    add('hook gap (min under hook)', hg,
        'FAIL' if hg is None or not HOOK_GAP_RANGE[0] <= hg <= HOOK_GAP_RANGE[1] else 'ok',
        f'range {HOOK_GAP_RANGE}, reference {nr["hook_gap_min"]}')
    add('needle x stripper plate [mm2]', n['needle_x_stripper_area'],
        'FAIL' if n['needle_x_stripper_area'] > 0.01 else 'ok')
    d = n['stripper_to_bed_gap'] - nr['stripper_to_bed_gap']
    add('stripper plate to needlebed gap', n['stripper_to_bed_gap'],
        'FAIL' if abs(d) > STRIPPER_BED_GAP_TOL else 'ok', f'reference {nr["stripper_to_bed_gap"]}')
    for key in ('blade_top_needle_frame', 'front_wall_from_tip'):
        diffs = [abs(u - v) for u, v in zip(n[key], nr[key]) if u is not None and v is not None]
        miss = sum((u is None) != (v is None) for u, v in zip(n[key], nr[key]))
        m = round(max(diffs), 3) if diffs else None
        add(f'{key} vs reference (max diff)', m,
            'FAIL' if m is None or m > PROFILE_TOL or miss else 'ok', f'{miss} samples missing' if miss else '')
    add('needle to yarn feeder', n['needle_to_feeder'], 'FAIL' if n['needle_to_feeder'] <= 0 else 'ok')

    a = test['assembly']
    for k in ('feeder_to_cover', 'stripper_to_feeder'):
        add(f'clamp gap {k}', a[k], 'FAIL' if a[k] < -0.05 or a[k] > 1.0 else 'ok',
            'gap closed by the screws; negative = overlap')
    for k, v in test['interference'].items():
        add(f'interference {k}', v, 'FAIL' if v > INTERFERENCE_MAX else 'ok')

    for f in test['fasteners']:
        name = f'{f["joint"]} @ ({f["x"]}, {f["y"]})'
        if 'error' in f:
            add(name, None, 'FAIL', f['error'])
            continue
        st, notes = 'ok', []
        th = f['thread']
        if f['insert_hole_depth'] < P['insertLength']:
            st = 'FAIL'
            notes.append(f'{th} hole {f["insert_hole_depth"]} < {P["insertLength"]}')
        elif f['insert_hole_depth'] < P['insertDepth'] - 0.05:
            st = 'warn'
            notes.append(f'{th} hole {f["insert_hole_depth"]} < recommended {P["insertDepth"]}')
        if f['insert_wall'] < 0.6:
            st = 'FAIL'
            notes.append(f'{th} wall {f["insert_wall"]}')
        elif f['insert_wall'] < P['insertWallMin']:
            st = st if st == 'FAIL' else 'warn'
            notes.append(f'{th} wall {f["insert_wall"]} < {P["insertWallMin"]}')
        g = f['plastic_under_head']
        if f['clamped_stack'] >= g + 1.0:
            pass  # the plastic under the head is backed by the next clamped part
        elif g < HEAD_GRIP[0]:
            st = 'FAIL'
            notes.append(f'{g} mm under head')
        elif g < HEAD_GRIP[1]:
            st = st if st == 'FAIL' else 'warn'
            notes.append(f'{g} mm under head')
        if f['head_overhang'] > HEAD_OVERHANG_WARN:
            st = st if st == 'FAIL' else 'warn'
            notes.append(f'head partly unsupported ({f["head_overhang"]} mm over a lower face)')
        rc = f.get('head_recess')
        if rc is not None and rc < 0:
            st = 'FAIL'
            notes.append(f'head sticks out {-rc} mm')
        elif rc is not None and rc < HEAD_RECESS_WARN:
            st = st if st == 'FAIL' else 'warn'
            notes.append(f'head recess only {rc} mm')
        if f['screw'].endswith('?'):
            st = 'FAIL'
            notes.append('no standard screw length fits')
        add(name, f'{f["screw"]} {th}', st, '; '.join(notes))
    return rows


# ---------------------------------------------------------------- plot

def plot(path, results):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    def draw(ax, g, fc, ec, alpha):
        if g is None or g.is_empty:
            return
        for p in (g.geoms if hasattr(g, 'geoms') else [g]):
            if p.geom_type != 'Polygon':
                continue
            ax.fill(*p.exterior.xy, fc=fc, ec=ec, alpha=alpha, lw=0.6)
            for h in p.interiors:
                ax.fill(*h.xy, fc='white', ec=ec, lw=0.6)

    fig, axs = plt.subplots(2, len(results), figsize=(6.2 * len(results), 10),
                            gridspec_kw={'height_ratios': [1.25, 1]}, squeeze=False)
    for j, (title, res, G) in enumerate(results):
        n = res['needle']
        for i, ax in enumerate(axs[:, j]):
            draw(ax, G['bed'], '0.8', '0.35', 1)
            draw(ax, G['fe'], 'tab:red', 'darkred', 0.45)
            draw(ax, G['sp'], 'tab:blue', 'navy', 0.55)
            draw(ax, G['needle'], 'lime', 'darkgreen', 0.95)
            ax.axhline(G['zb'], color='green', lw=0.6, ls='--')
            ax.set_aspect('equal')
            ax.grid(lw=0.3)
            if i == 0:
                ax.set_xlim(-195, -138)
                ax.set_ylim(-17, 10)
                ax.set_title(f'{title}\nstripper plate to needlebed gap: {n["stripper_to_bed_gap"]:.2f} mm',
                             fontsize=10)
                ax.set_ylabel('z (mm)')
            else:
                ax.set_xlim(-182, -166)
                ax.set_ylim(G['zb'] - 2.2, G['zb'] + 4.2)
                hg = n['hook_gap_min']
                ax.set_title(f'under the hook - min gap: {hg:.2f} mm', fontsize=10,
                             color='red' if hg is None or hg < HOOK_GAP_RANGE[0] else 'black')
                ax.set_xlabel('y (mm), needle in hold position')
    fig.suptitle('Side section parallel to the needles, as assembled\n'
                 'blue: stripper plate, red: yarn feeder, grey: needlebed, green: needle', fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=110)


# ---------------------------------------------------------------- main

def run(tree, log):
    files = scad.render_all(tree, log=log)
    info = scad.probe(tree)
    M = Model(tree, files, info)
    asm = solve_assembly(M)
    needle, G = needle_checks(M)
    res = {'params': M.P, 'assembly': asm, 'needle': needle}
    return M, res, G


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--ref', default='main', help='git ref with the reference geometry (default: main)')
    ap.add_argument('--tree', default=REPO, help='directory holding SCAD/ and SVG/ (default: this repo)')
    ap.add_argument('--set', action='append', default=[], metavar='NAME=VALUE',
                    help='override a parameter of params.scad (repeatable)')
    ap.add_argument('--cache', default=os.path.join(REPO, '.geometry_check'), help='render cache')
    ap.add_argument('--out', default=None, help='report directory (default: <cache>/report)')
    ap.add_argument('--no-plot', action='store_true')
    a = ap.parse_args()
    log = lambda m: print(m, file=sys.stderr, flush=True)  # noqa: E731
    os.makedirs(a.cache, exist_ok=True)
    overrides = dict(s.split('=', 1) for s in a.set)

    log(f'reference: {a.ref}')
    rtree = scad.tree_from_git(REPO, a.ref, a.cache)
    Mr, ref, Gr = run(rtree, log)
    log(f'test: {a.tree} {overrides or ""}')
    ttree = scad.tree_from_dir(a.tree, a.cache, overrides)
    M, test, Gt = run(ttree, log)
    test['interference'] = interference(M)
    test['fasteners'] = fastener_checks(M, M.info['joints'])
    rows = verdicts(test, ref, M.P)

    # tension cams; the reference tree may predate the TENSION echo, and the
    # cam coordinates are the same in both
    tinfo = M.info.get('tension')
    if tinfo is None:
        rows.append({'check': 'tension cams', 'value': None, 'status': 'FAIL',
                     'note': 'no ECHO: TENSION from tCamReport()'})
    else:
        log('tension cams')
        tref = tension.run(Mr, tinfo)
        ttest = tension.run(M, tinfo, tref.get('design_range'))
        ref['tension'], test['tension'] = tension.summary(tref), tension.summary(ttest)
        add = lambda name, value, status, note='': rows.append(  # noqa: E731
            {'check': name, 'value': value, 'status': status, 'note': note})
        tension.verdict_rows(ttest, tref, add)
        tension.lock_rows(ttest, add)

    out = a.out or os.path.join(a.cache, 'report')
    os.makedirs(out, exist_ok=True)
    json.dump({'overrides': overrides, 'reference_tree': rtree, 'test_tree': ttree,
               'reference': ref, 'test': test, 'checks': rows},
              open(os.path.join(out, 'report.json'), 'w'), indent=1)
    if not a.no_plot:
        plot(os.path.join(out, 'sections.png'),
             [(f'reference ({a.ref})', ref, Gr), (f'test {overrides or ""}', test, Gt)])
        if tinfo is not None:
            tension.plot(os.path.join(out, 'tension.png'), ttest, f'test {overrides or ""}')

    w = max(len(r['check']) for r in rows)
    for r in rows:
        print(f'{r["status"]:4s}  {r["check"]:{w}s}  {r["value"]!s:>10s}  {r["note"]}')
    nfail = sum(r['status'] == 'FAIL' for r in rows)
    nwarn = sum(r['status'] == 'warn' for r in rows)
    print(f'\n{len(rows)} checks, {nfail} failed, {nwarn} warnings. Report: {out}')
    sys.exit(1 if nfail else 0)


if __name__ == '__main__':
    main()
