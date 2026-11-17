"""Slicing of STL meshes with planes x = const -> 2D (y, z) shapely geometry."""
import struct
from functools import reduce

import numpy as np
from shapely.geometry import LineString, MultiLineString
from shapely.ops import polygonize, unary_union


def load_stl(path):
    d = open(path, 'rb').read()
    if d[:5] == b'solid' and b'facet' in d[:300]:
        v = [list(map(float, l.split()[1:4])) for l in d.decode().splitlines()
             if l.strip().startswith('vertex')]
        return np.array(v, dtype=float).reshape(-1, 3, 3)
    n = struct.unpack('<I', d[80:84])[0]
    a = np.frombuffer(d[84:84 + n * 50],
                      dtype=np.dtype([('n', '<3f4'), ('v', '<9f4'), ('a', '<u2')]))
    return a['v'].reshape(-1, 3, 3).astype(float)


def _edge_point(p, q, x):
    # canonical order so both triangles sharing an edge give identical points
    swap = (p[:, 0] > q[:, 0]) | ((p[:, 0] == q[:, 0]) & (p[:, 1] > q[:, 1]))
    a = np.where(swap[:, None], q, p)
    b = np.where(swap[:, None], p, q)
    t = (x - a[:, 0]) / (b[:, 0] - a[:, 0])
    return a[:, 1:] + t[:, None] * (b[:, 1:] - a[:, 1:])


def section(tris, x, eps=1e-4):
    """Cross-section of a closed mesh at plane x (y,z coords). Returns shapely geometry."""
    x = x + eps
    xs = tris[:, :, 0]
    above = xs > x
    cnt = above.sum(1)
    m = (cnt == 1) | (cnt == 2)
    T, A = tris[m], above[m]
    if len(T) == 0:
        return None
    # lone vertex = the one on the minority side
    lone = np.where(A.sum(1) == 1, A.argmax(1), (~A).argmax(1))
    i = np.arange(len(T))
    P = T[i, lone]
    Q = T[i, (lone + 1) % 3]
    R = T[i, (lone + 2) % 3]
    s1 = _edge_point(P, Q, x)
    s2 = _edge_point(P, R, x)
    lines = [LineString([tuple(a), tuple(b)]) for a, b in zip(s1, s2)
             if np.hypot(*(a - b)) > 1e-9]
    merged = unary_union(MultiLineString(lines))
    polys = list(polygonize(merged))
    if not polys:
        return None
    # even-odd fill
    g = reduce(lambda a, b: a.symmetric_difference(b), polys)
    return g.buffer(0)


def swept(tris, xs):
    """Union of sections over several x (envelope swept by a part moving along x)."""
    secs = [section(tris, x) for x in xs]
    secs = [s for s in secs if s is not None and not s.is_empty]
    return unary_union(secs) if secs else None
