"""OpenSCAD helpers: source trees, parameter overrides, cached renders, probes.

A "tree" is a directory holding copies of SCAD/ and SVG/. Overrides are
applied by rewriting assignments in SCAD/modules/params.scad, because
`openscad -D` does not reach files that are pulled in with `use<>`.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import io

PARTS = ['needlebed', 'backCover', 'spongeBar', 'carriageRest', 'backPlate', 'tCam', 'tPointer',
         'tensionLock', 'stripperPlate', 'yarnFeeder', 'yarnCarrierCover']

PARAMS = ['gauge', 'tolerance', 'needleSlotHeight', 'needleBedHeight', 'NEEDLE_BED_DEPTH',
          'NEEDLE_EXTENSION', 'NEEDLE_LEG_HEIGHT', 'HOOK_DIAM', 'COMB', 'camHeight',
          'camPlateHeight', 'CAM_PLATE_WIDTH', 'screwDiam', 'screwDiamSm', 'screwHeadHeight',
          'insertDiameter', 'insertLength', 'insertDepth', 'insertWallMin', 'screwTapDiam']


def _tree_hash(tree):
    h = hashlib.sha1()
    for sub in ('SCAD', 'SVG'):
        for root, _, files in sorted(os.walk(os.path.join(tree, sub))):
            for f in sorted(files):
                p = os.path.join(root, f)
                h.update(os.path.relpath(p, tree).encode())
                h.update(open(p, 'rb').read())
    return h.hexdigest()[:12]


def tree_from_git(repo, ref, dest):
    """Extract SCAD/ and SVG/ of a git ref into dest (cached by commit id)."""
    sha = subprocess.run(['git', '-C', repo, 'rev-parse', ref], capture_output=True, text=True,
                         check=True).stdout.strip()
    out = os.path.join(dest, 'ref-' + sha[:12])
    if not os.path.isdir(out):
        data = subprocess.run(['git', '-C', repo, 'archive', sha, 'SCAD', 'SVG'], capture_output=True,
                              check=True).stdout
        tmp = out + '.tmp'
        shutil.rmtree(tmp, ignore_errors=True)
        with tarfile.open(fileobj=io.BytesIO(data)) as t:
            t.extractall(tmp)
        _fix_case(tmp)
        os.rename(tmp, out)
    return out


def tree_from_dir(src, dest, overrides=None):
    """Copy SCAD/ and SVG/ of src into dest, applying parameter overrides."""
    tmp = os.path.join(dest, 'work.tmp')
    shutil.rmtree(tmp, ignore_errors=True)
    for sub in ('SCAD', 'SVG'):
        shutil.copytree(os.path.join(src, sub), os.path.join(tmp, sub))
    _fix_case(tmp)
    if overrides:
        apply_overrides(tmp, overrides)
    out = os.path.join(dest, 'tree-' + _tree_hash(tmp))
    if os.path.isdir(out):
        shutil.rmtree(tmp)
    else:
        os.rename(tmp, out)
    return out


def _fix_case(tree):
    # upstream includes "needleBed.scad" but the file is "needlebed.scad" (breaks on Linux)
    for root, _, files in os.walk(os.path.join(tree, 'SCAD')):
        for f in files:
            p = os.path.join(root, f)
            s = open(p).read()
            if 'needleBed.scad' in s:
                open(p, 'w').write(s.replace('needleBed.scad', 'needlebed.scad'))


def apply_overrides(tree, overrides):
    p = os.path.join(tree, 'SCAD', 'modules', 'params.scad')
    s = open(p).read()
    for name, value in overrides.items():
        s, n = re.subn(rf'^(\s*{re.escape(name)}\s*=\s*)[^;]*;', rf'\g<1>{value};', s, count=1, flags=re.M)
        if n == 0:
            raise SystemExit(f'parameter {name} not found in params.scad')
    open(p, 'w').write(s)


def render(tree, part, log=None):
    """Render SCAD/parts/<part>.scad to <tree>/out/<part>.stl (cached inside the tree)."""
    out = os.path.join(tree, 'out', part + '.stl')
    if os.path.exists(out):
        return out
    os.makedirs(os.path.dirname(out), exist_ok=True)
    src = os.path.join(tree, 'SCAD', 'parts', part + '.scad')
    if not os.path.exists(src):
        return None
    r = subprocess.run(['openscad', '-o', out + '.tmp.stl', src], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f'openscad failed on {part}:\n{r.stderr[-2000:]}')
    os.rename(out + '.tmp.stl', out)
    if log:
        log(f'  rendered {part}')
    return out


def render_all(tree, parts=PARTS, log=None):
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
        res = list(ex.map(lambda p: (p, render(tree, p, log)), parts))
    return {p: f for p, f in res if f}


def _echo_value(txt):
    # OpenSCAD echo values are JSON apart from undef/inf/nan
    txt = re.sub(r'\bundef\b', 'null', txt)
    txt = re.sub(r'\b-?inf\b', 'null', txt)
    txt = re.sub(r'\bnan\b', 'null', txt)
    return json.loads(txt)


def probe(tree):
    """Parameters and fastener descriptions (ECHO JOINT lines) of a tree."""
    cache = os.path.join(tree, 'out', 'probe.json')
    if os.path.exists(cache):
        return json.load(open(cache))
    reports = [('../modules/carriageScrews.scad', 'carriageScrewsReport'),
               ('../modules/needlebedScrews.scad', 'needleBedScrewsReport'),
               ('../parts/tCam.scad', 'tCamReport'),
               ('../parts/carriageRest.scad', 'carriageRestReport'),
               ('../parts/tensionLock.scad', 'tensionLockReport')]
    src = ['include<../modules/params.scad>;']
    for f, m in reports:
        src.append(f'use<{f}>;')
    for name in PARAMS:
        src.append(f'echo(P = ["{name}", is_undef({name}) ? undef : {name}]);')
    for f, m in reports:
        src.append(f'{m}();')
    src.append('cube(1);')
    f = os.path.join(tree, 'SCAD', 'parts', '_probe.scad')
    open(f, 'w').write('\n'.join(src) + '\n')
    os.makedirs(os.path.join(tree, 'out'), exist_ok=True)
    tmp = os.path.join(tree, 'out', '_probe.stl')
    r = subprocess.run(['openscad', '-o', tmp, f], capture_output=True, text=True)
    os.remove(f)
    if os.path.exists(tmp):
        os.remove(tmp)
    txt = r.stdout + r.stderr
    params, joints, tension = {}, [], None
    for line in txt.splitlines():
        m = re.match(r'ECHO: P = (.*)$', line)
        if m:
            k, v = _echo_value(m.group(1))
            params[k] = v
        m = re.match(r'ECHO: JOINT = (.*)$', line)
        if m:
            v = _echo_value(m.group(1))
            keys = ['name', 'points', 'head_side', 'head_part', 'insert_part', 'insert_face_z',
                    'insert_dir', 'head_diam', 'head_height', 'flush', 'thread', 'hole_diam']
            joints.append(dict(zip(keys, v)))
        m = re.match(r'ECHO: TENSION = (.*)$', line)
        if m:
            v = _echo_value(m.group(1))
            tension = dict(zip(['pivot', 'screw', 'slot_z', 'slot_path', 'lock_angles', 'pointer_z',
                                'lock_z', 'lock_screws'], v))
    res = {'params': params, 'joints': joints}
    if tension:
        res['tension'] = tension
    json.dump(res, open(cache, 'w'), indent=1)
    return res
