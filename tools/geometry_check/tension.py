"""Tension cam checks, on plan sections (planes z = const) of the back plate
and the tension cam:

- travel of the tension screw along its slot in the back plate, and the
  clearance of an M3 screw in the slot;
- the tension cams at both ends of the travel must not touch the cam walls;
- path of a needle butt through the cams at both ends of the travel;
- the tension lock: the pointer tip must fit each notch of the lock block,
  the block must stop the pointer turning, and the lifted pointer must clear
  the heads of the lock screws.

The tension cam turns about its pivot; the tension screw (in an insert in the
cam) slides in the curved slot of the back plate. Only the left cam is
rendered; the right one is its mirror image about x = CAM_PLATE_WIDTH / 2 and
is set to the same angle.
"""
import numpy as np
from shapely import affinity
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from meshsec import section

CAM_Z = 5.0            # cut through the cams (z 2..15) and the needle butts (top at about 7.9)
SCREW_D = 3.0          # M3 shank
OLD_SCREW_D = 2.84     # #4-40 shank, for the travel of the upstream slot
SLOT_CLEARANCE = 0.2   # mm the slot must be wider than the screw (printed slots come out narrow)
HEAD_D = 5.5           # M3 socket head
LOCK_PLAY_MAX = 1.0    # deg the pointer may turn in a notch before the block stops it
LOCK_ENGAGEMENT_MIN = 1.5   # mm of pointer tip height inside the block
BUTT_W = 1.25          # NEEDLE_WIDTH, along x
BUTT_L = 3.85          # butt length along y, measured on the technical sketch
STEP = 0.05            # mm, butt simulation step along x
ANGLES = np.arange(-15.0, 5.0, 0.02)


def plan(T, z):
    """Section of mesh T with the plane z = const, in (x, y)."""
    return section(T[..., [2, 0, 1]], z)


def polys(g):
    if g is None or g.is_empty:
        return []
    return [g] if g.geom_type == 'Polygon' else [p for p in g.geoms if p.geom_type == 'Polygon']


def slot_polygon(back_plate, z, screw):
    for p in polys(plan(back_plate, z)):
        for h in p.interiors:
            q = Polygon(h)
            if q.contains(Point(screw)):
                return q
    return None


def travel(slot, pivot, screw, d, angles=ANGLES):
    """(min, max) angle in degrees at which a screw of diameter d fits in the slot."""
    ok = [a for a in angles
          if slot.contains(affinity.rotate(Point(screw), a, origin=pivot).buffer(d / 2, 64))]
    return (round(min(ok), 2), round(max(ok), 2)) if ok else None


def max_screw(slot, pivot, screw, rng):
    """Largest screw diameter that slides along the whole range rng (deg)."""
    if not rng:
        return None
    angles = np.linspace(rng[0], rng[1], int((rng[1] - rng[0]) / 0.1) + 2)
    lo, hi = 0.0, 6.0
    for _ in range(12):
        d = (lo + hi) / 2
        t = travel(slot, pivot, screw, d, angles)
        if t and t[0] <= rng[0] + 0.01 and t[1] >= rng[1] - 0.01:
            lo = d
        else:
            hi = d
    return round(lo, 2)


def cams(tcam, pivot, a, W):
    left = affinity.rotate(tcam, a, origin=pivot)
    right = affinity.scale(left, xfact=-1, yfact=1, origin=(W / 2, 0))
    return left, right


def butt_path(material, W, y_start):
    """A needle butt crossing the carriage from x = W + 5 to x = -5 (carriage
    moving +x). It only moves along y when a cam pushes it. Returns x, y of
    its centre, or raises RuntimeError if it jams."""
    yc = y_start
    xs, ys = [], []
    for x in np.arange(W + 5, -5, -STEP):
        slab = material.intersection(box(x - BUTT_W / 2, -400, x + BUTT_W / 2, 100))
        blocked = sorted((p.bounds[1], p.bounds[3]) for p in polys(slab))
        free, lo = [], -400.0
        for s, t in blocked:
            if s > lo:
                free.append((lo, s))
            lo = max(lo, t)
        free.append((lo, 100.0))
        cur = (yc - BUTT_L / 2, yc + BUTT_L / 2)
        cands = []
        for s, t in free:
            if t - s >= BUTT_L and t > cur[0] and s < cur[1]:
                ny = min(max(yc, s + BUTT_L / 2), t - BUTT_L / 2)
                cands.append((abs(ny - yc), ny))
        if not cands:
            raise RuntimeError(f'needle butt jams at x = {x:.1f}, y = {yc:.1f}')
        yc = min(cands)[1]
        xs.append(x)
        ys.append(yc)
    return np.array(xs), np.array(ys)


def run(M, info, design_range=None):
    """Tension results for model M. info: the TENSION echo of the tree
    under test (pivot, screw, slot_z). design_range: travel of the reference
    slot (None for the reference itself)."""
    W = M.P['CAM_PLATE_WIDTH']
    pivot, screw = tuple(info['pivot']), tuple(info['screw'])
    res = {}
    slot = slot_polygon(M.mesh['backPlate'], info['slot_z'], screw)
    if slot is None:
        return {'error': 'tension slot not found in the back plate'}
    res['travel_old_screw'] = travel(slot, pivot, screw, OLD_SCREW_D)
    res['travel_m3'] = travel(slot, pivot, screw, SCREW_D)
    rng = design_range or res['travel_old_screw']
    res['design_range'] = rng
    res['max_screw_over_travel'] = max_screw(slot, pivot, screw, rng)

    walls = plan(M.mesh['backPlate'], CAM_Z)
    tcam = plan(M.mesh['tCam'], CAM_Z)
    # the widened slot lets the cam turn a bit further than the upstream one
    res['travel_ends_cam_x_walls_mm2'] = {
        a: round(walls.intersection(unary_union(cams(tcam, pivot, a, W))).area, 3)
        for a in (res['travel_m3'] or ())}
    res['ends'] = {}
    y0 = None
    for a in (rng[1], rng[0]) if rng else ():
        L, R = cams(tcam, pivot, a, W)
        e = {'angle': a, 'cam_x_walls_mm2': round(walls.intersection(unary_union([L, R])).area, 3)}
        mat = unary_union([walls, L, R])
        try:
            # first pass from the middle of the track, second from where the
            # first one left the needle (its working position)
            if y0 is None:
                _, ys = butt_path(mat, W, -74.0)
                y0 = ys[-1]
            xs, ys = butt_path(mat, W, y0)
            e['butt_back_max'] = round(ys.max() + BUTT_L / 2, 2)
            e['butt_front_min'] = round(ys.min() - BUTT_L / 2, 2)
            e['path'] = (xs, ys)
        except RuntimeError as ex:
            e['error'] = str(ex)
        e['cams'] = (L, R)
        res['ends'][a] = e
    res['walls'], res['slot'], res['pivot'], res['screw'], res['W'] = walls, slot, pivot, screw, W
    res['lock'] = lock(M, info, res['travel_m3'])
    return res


def lock(M, info, travel):
    """Tension lock: pointer tip in the notches of the lock block (left side)."""
    if 'lock_angles' not in info or 'tPointer' not in M.mesh or 'tensionLock' not in M.mesh:
        return None
    pz, lz = info['pointer_z'], info['lock_z']
    lo, hi = max(pz[0], lz[0]), min(pz[1], lz[1])
    res = {'angles_deg': info['lock_angles'], 'engagement': round(hi - lo, 2),
           'lift': round(lz[1] - pz[0], 2), 'notches': {}}
    pivot = tuple(info['pivot'])
    if hi - lo > 0.1:
        z = (lo + hi) / 2
        ptr, blk = plan(M.mesh['tPointer'], z), plan(M.mesh['tensionLock'], z)

        def overlap(a):
            return affinity.rotate(ptr, a, origin=pivot).intersection(blk).area

        for a in info['lock_angles']:
            e = {'overlap_mm2': round(overlap(a), 3)}
            for sgn, k in ((1, 'play_ccw'), (-1, 'play_cw')):
                d = 0.0
                while d < 3.0 and overlap(a + sgn * (d + 0.02)) < 0.01:
                    d += 0.02
                e[k] = round(d, 2)          # 3.0: the block does not stop the pointer
            res['notches'][a] = e
    # the pointer, lifted above the block, turning over the whole travel
    heads = unary_union([Point(p).buffer(HEAD_D / 2, 32) for p in info['lock_screws']])
    ptr = plan(M.mesh['tPointer'], (pz[0] + pz[1]) / 2)
    angles = np.arange(travel[0], travel[1] + 0.01, 0.1) if travel else info['lock_angles']
    res['pointer_x_screw_heads_mm2'] = round(max(
        affinity.rotate(ptr, a, origin=pivot).intersection(heads).area for a in angles), 3)
    return res


def summary(res):
    """JSON-friendly copy of run()'s result."""
    out = {k: v for k, v in res.items() if k not in ('walls', 'slot', 'ends')}
    out['travel_ends_cam_x_walls_mm2'] = {str(k): v for k, v in res.get('travel_ends_cam_x_walls_mm2', {}).items()}
    out['ends'] = {str(a): {k: v for k, v in e.items() if k not in ('path', 'cams')}
                   for a, e in res.get('ends', {}).items()}
    if res.get('lock'):
        out['lock'] = dict(res['lock'], notches={str(a): e for a, e in res['lock']['notches'].items()})
    return out


def verdict_rows(test, ref, add):
    if 'error' in test:
        add('tension slot', None, 'FAIL', test['error'])
        return
    rr, tr = ref.get('design_range'), test['travel_m3']
    ok = tr is not None and rr is not None and tr[0] <= rr[0] + 0.05 and tr[1] >= rr[1] - 0.05
    add('tension screw travel, M3 [deg]', tr, 'ok' if ok else 'FAIL', f'upstream slot with #4-40: {rr}')
    w, wr = test['max_screw_over_travel'], ref.get('max_screw_over_travel')
    add('tension slot: largest screw over the whole travel', w,
        'FAIL' if w is None or w < SCREW_D + SLOT_CLEARANCE else 'ok',
        f'M3 shank {SCREW_D} + {SLOT_CLEARANCE} clearance; upstream {wr}')
    for a, v in test['travel_ends_cam_x_walls_mm2'].items():
        add(f'tension cam at the end of the M3 travel ({a:+.1f} deg) x walls [mm2]', v,
            'FAIL' if v > 0.01 else 'ok')
    for a, e in test['ends'].items():
        name = f'tension cam at {a:+.1f} deg'
        add(f'{name}: cams x walls [mm2]', e['cam_x_walls_mm2'], 'FAIL' if e['cam_x_walls_mm2'] > 0.01 else 'ok')
        if 'error' in e:
            add(f'{name}: needle butt', None, 'FAIL', e['error'])
            continue
        r = ref.get('ends', {}).get(a, {}).get('butt_back_max')
        d = None if r is None else abs(e['butt_back_max'] - r)
        add(f'{name}: butt pulled back to y', e['butt_back_max'],
            'FAIL' if d is None or d > 0.05 else 'ok', f'reference {r}')


def lock_rows(test, add):
    lk = test.get('lock')
    if lk is None:
        add('tension lock', None, 'FAIL', 'no tPointer / tensionLock render or no lock data')
        return
    tr = test['travel_m3']
    for a in lk['angles_deg']:
        ok = tr is not None and tr[0] - 0.01 <= a <= tr[1] + 0.01
        add(f'tension lock notch at {a:+.1f} deg: inside the M3 travel', a, 'ok' if ok else 'FAIL', f'travel {tr}')
    add('tension lock: pointer tip height inside the block', lk['engagement'],
        'FAIL' if lk['engagement'] < LOCK_ENGAGEMENT_MIN else 'ok', f'min {LOCK_ENGAGEMENT_MIN}')
    for a, e in lk['notches'].items():
        add(f'tension lock notch at {a:+.1f} deg: pointer x block [mm2]', e['overlap_mm2'],
            'FAIL' if e['overlap_mm2'] > 0.01 else 'ok')
        play = max(e['play_ccw'], e['play_cw'])
        add(f'tension lock notch at {a:+.1f} deg: play [deg]', f'+{e["play_ccw"]}/-{e["play_cw"]}',
            'FAIL' if play >= 3.0 else 'warn' if play > LOCK_PLAY_MAX else 'ok',
            'the block does not stop the pointer' if play >= 3.0 else '')
    v = lk['pointer_x_screw_heads_mm2']
    add('tension lock: lifted pointer x lock screw heads [mm2]', v, 'FAIL' if v > 0.01 else 'ok')
    add('tension lock: lift the pointer by [mm] to change the setting', lk['lift'], 'ok')


def plot(path, res, title=''):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    def draw(ax, g, **kw):
        for p in polys(g):
            ax.fill(*p.exterior.xy, **kw)
            for h in p.interiors:
                ax.fill(*h.xy, fc='white', ec=kw.get('ec', 'k'), lw=.5)

    ends = [e for e in res['ends'].values() if 'path' in e]
    if not ends:
        return
    tight = max(ends, key=lambda e: -e['butt_back_max'])
    loose = min(ends, key=lambda e: -e['butt_back_max'])
    style = [(tight, '#d62728', 'tightest'), (loose, '#1f77b4', 'loosest')]
    fig, axs = plt.subplots(2, 1, figsize=(15, 15), gridspec_kw={'height_ratios': [1, 1.1]})
    for ax in axs:
        draw(ax, res['walls'], fc='#c9b3e6', ec='indigo', lw=.6)
        for e, c, lab in style:
            for cam in e['cams']:
                draw(ax, cam, fc=c, alpha=.15, ec=c, lw=1.0)
            xs, ys = e['path']
            ax.fill_between(xs, ys - BUTT_L / 2, ys + BUTT_L / 2, color=c, alpha=.4, lw=0,
                            label=f'needle butt, {lab} ({e["angle"]:+.1f} deg)')
            ax.plot(xs, ys, color=c, lw=.8)
            p = affinity.rotate(Point(res['screw']), e['angle'], origin=res['pivot'])
            ax.add_patch(plt.Circle((p.x, p.y), SCREW_D / 2, fc='none', ec=c, lw=1.2))
        ax.plot(*res['slot'].exterior.xy, 'k--', lw=.6)
        ax.plot(*res['pivot'], 'ko', ms=4)
        ax.set_aspect('equal')
        ax.grid(alpha=.3)
        ax.set_xlabel('x (mm, carriage frame)')
        ax.set_ylabel('y (mm)')
    W = res['W']
    ax = axs[0]
    ax.set_xlim(-6, W + 6)
    ax.set_ylim(-104, -46)
    ax.annotate('', xy=(10, -100), xytext=(40, -100), arrowprops=dict(arrowstyle='->', lw=1.5))
    ax.text(42, -100.5, 'needle butts move this way relative to the carriage (carriage moving +x); '
            'the other direction is the mirror image', fontsize=9, va='center')
    ax.legend(loc='upper center', fontsize=9, ncol=2)
    ax.set_title(f'{title}\nPlan section at z = {CAM_Z}: back plate (violet), tension cams and the path of a '
                 f'needle butt ({BUTT_W} x {BUTT_L} mm)', fontsize=11)
    ax = axs[1]
    yt, yl = tight['butt_back_max'], loose['butt_back_max']
    ax.set_xlim(20, 95)
    ax.set_ylim(-98, -50)
    for e, c, _ in style:
        ax.axhline(e['butt_back_max'], color=c, ls=':', lw=1)
    ax.annotate('', xy=(24, yl), xytext=(24, yt), arrowprops=dict(arrowstyle='<->', lw=1.2))
    ax.text(24.5, (yt + yl) / 2, f'{yl - yt:.2f} mm', fontsize=10, va='center')
    ax.set_title(f'Stitch cam: the butt is pulled back to y = {yt} (tightest) or {yl} (loosest), back edge.\n'
                 f'Tension screw slot dashed, M3 screw at both ends of the travel', fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)
