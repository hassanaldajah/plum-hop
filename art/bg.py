# Renders parallax background layers. usage: blender -b --factory-startup -P bg.py -- <world 0-3> <far|mid> [preview]
import bpy, sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, lib; importlib.reload(lib)
from lib import *
from mathutils import noise, Vector

argv = sys.argv[sys.argv.index('--') + 1:]
WI = int(argv[0]); LAYER = argv[1]; PREVIEW = len(argv) > 2 and argv[2] == 'preview'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out'); os.makedirs(OUT, exist_ok=True)
SIZES = {'far': (1100, 220), 'mid': (1700, 150)}
if WI == 1: SIZES = {'far': (1100, 300), 'mid': (1700, 300)}
Wl, Hl = SIZES[LAYER]; WB, HB = Wl * 0.1, Hl * 0.1
reset()
setup(int(Wl * 2 * (0.5 if PREVIEW else 1)), int(Hl * 2 * (0.5 if PREVIEW else 1)), 12 if PREVIEW else 64)
CAMY = -100
camera(WB / 2, CAMY, HB / 2, 0, WB)
rng = random.Random(WI * 100 + (LAYER == 'mid'))

def norm_fn(f, samples=400):
    vals = [f(i / samples * (WB + 20) - 10) for i in range(samples + 1)]
    lo, hi = min(vals), max(vals)
    return lambda x: (f(x) - lo) / (hi - lo + 1e-9)

def ridge(seed, freq, octaves=6, kind='ridged'):
    if kind == 'ridged':
        f = lambda x: noise.ridged_multi_fractal(Vector((x * freq, seed * 1.7, 0.3)), 0.9, 2.1, octaves, 1.0, 2.0)
    else:
        f = lambda x: noise.fractal(Vector((x * freq, seed * 1.7, 0.3)), 0.8, 2.0, octaves)
    return norm_fn(f)

def strip(name, yfront, yback, base, amp, prof, mat, nx=None, detail=0.0, dfreq=0.6, power=1.0):
    nx = nx or int(WB * 3)
    def hf(x, y):
        t = max(0.0, min(1.0, (y - yfront) / (yback - yfront)))
        t = t * t * (3 - 2 * t)
        z = base + amp * (prof(x) ** power) * t
        if detail: z += detail * noise.fractal(Vector((x * dfreq, y * dfreq, 7.1)), 0.7, 2.0, 5) * t
        return z if t > 0 else base - 2 + (y - yfront) * 0.02
    return grid_mesh(name, -12, WB + 12, yfront - 6, yback + 4, nx, 30, hf, mat), hf

def scatter(proto, hf, n, y0, y1, smin, smax, xr=(-5, None), tilt=0.0):
    xr = (xr[0], WB + 5 if xr[1] is None else xr[1])
    for i in range(n):
        x = rng.uniform(*xr); y = rng.uniform(y0, y1); s = rng.uniform(smin, smax)
        p = proto[i % len(proto)]
        for part in p: instance(part, (x, y, hf(x, y) - 0.15 * s), rng.uniform(0, 6.28), s)

def protos(kind, n, mats, **kw):
    out = []
    for i in range(n):
        parts = broadleaf(WI * 50 + i, 1.0, mats, **kw) if kind == 'tree' else pine(WI * 50 + i, 1.0, mats, **kw) if kind == 'pine' else (bush(WI * 50 + i, 1.0, mats[1]),)
        for p in parts: p.location.z = -500; hide(p)
        out.append(parts)
    return out

def show_inst():
    for o in bpy.data.objects:
        if o.name.endswith('_i'): o.hide_render = False; o.hide_viewport = False

G = lambda h: srgb(h)
if WI == 0:  # ---------------- Green Meadow: sunny midday
    HAZE = G('#bcd9ee')
    sky_world(40, 335, 0.35); sun(40, 335, 4.2, (1, .95, .86))
    if LAYER == 'far':
        mtn = mat_ground('mtn', [(0.3, G('#6f7f92')), (0.7, G('#8a96a6'))], 0.05, 0.5, snow=(8.5, 2.5, 3.0), rock=([(0.3, G('#5f6b7a')), (0.7, G('#8c94a0'))], 0.75), fog=(HAZE, 380, 470, 0.5))
        strip('mtn', 330, 420, 0.5, 12, ridge(1, 0.028, 7), mtn, detail=2.2, dfreq=0.16)
        hil = mat_ground('hill', [(0.3, G('#4f8a3c')), (0.7, G('#7aa34f'))], 0.08, 0.3, fog=(HAZE, 240, 330, 0.3))
        _, hf = strip('hill', 200, 260, 0.2, 6, ridge(2, 0.03, 4, 'fbm'), hil, detail=0.6)
        fm = [mat_bark('bk1', G('#3b2c22'), G('#5a4433'), fog=(HAZE, 240, 330, 0.3)), mat_foliage('lf1', [(0.2, G('#2f5a24')), (0.8, G('#5b8a34'))], fog=(HAZE, 240, 330, 0.3))]
        scatter(protos('tree', 5, fm), hf, 260, 225, 262, 0.9, 1.5)
        near = mat_ground('near', [(0.3, G('#3f7a2f')), (0.7, G('#82ad4c'))], 0.1, 0.3, fog=(HAZE, 120, 240, 0.14))
        _, hf2 = strip('near', 120, 170, 0.0, 3.8, ridge(3, 0.022, 4, 'fbm'), near, detail=0.5)
        fm2 = [mat_bark('bk2', G('#3b2c22'), G('#5a4433'), fog=(HAZE, 120, 240, 0.14)), mat_foliage('lf2', [(0.2, G('#2c5a20')), (0.8, G('#69a03a'))], fog=(HAZE, 120, 240, 0.14))]
        scatter(protos('tree', 5, fm2), hf2, 110, 140, 172, 1.4, 2.4)
    else:
        gr = mat_ground('grass', [(0.25, G('#3d7a2a')), (0.55, G('#6ea53d')), (0.8, G('#a3b85a'))], 0.12, 0.4, fog=(HAZE, 100, 200, 0.05))
        _, hf = strip('mid', 40, 70, 0.0, 7.0, ridge(4, 0.024, 5, 'fbm'), gr, detail=1.0, dfreq=0.3)
        fm = [mat_bark('bk', G('#3a2a1f'), G('#6a5038'), fog=(HAZE, 100, 200, 0.05)), mat_foliage('lf', [(0.15, G('#24501b')), (0.5, G('#3f7a28')), (0.85, G('#7fae45'))], fog=(HAZE, 100, 200, 0.05))]
        scatter(protos('tree', 6, fm), hf, 46, 52, 74, 3.4, 5.6)
        scatter(protos('bush', 4, fm), hf, 60, 44, 62, 0.6, 1.3)
elif WI == 1:  # ---------------- Deep Forest: misty, filtered light
    HAZE = G('#7fa88c') if LAYER == 'far' else G('#6f9a7c')
    sky_world(32, 320, 0.3); sun(32, 320, 3.6, (1, .9, .72))
    if LAYER == 'far':
        for k, (y, fm_, sc_) in enumerate([(330, .5, 1.0), (260, .34, 1.15), (190, .2, 1.3)]):
            fog = (HAZE, y - 30, y + 30, fm_ * 1.0)
            g = mat_ground('fg%d' % k, [(0.3, G('#2f4a28')), (0.7, G('#4f6a34'))], 0.1, 0.3, fog=(HAZE, 0, 1, fm_))
            _, hf = strip('fl%d' % k, y - 20, y, 0.0, 1.5, ridge(10 + k, 0.03, 3, 'fbm'), g)
            mats = [mat_bark('fb%d' % k, G('#2a2119'), G('#4a3a2c'), fog=(HAZE, 0, 1, fm_)), mat_foliage('ff%d' % k, [(0.2, G('#1d3d1c')), (0.8, G('#3f6a2c'))], fog=(HAZE, 0, 1, fm_))]
            pr = []
            for i in range(4):
                t, c = broadleaf(200 + k * 10 + i, 1.0, mats, wide=1.3)
                for v in t.data.vertices: v.co.z *= 1.0
                for p in (t, c): p.location.z = -500; hide(p)
                pr.append((t, c))
            for i in range(int(48 * sc_)):
                x = rng.uniform(-5, WB + 5); yy = rng.uniform(y - 18, y); s = rng.uniform(26, 36) * (0.8 + k * 0.1)
                t, c = pr[i % 4]; instance(t, (x, yy, hf(x, yy) - 1), rng.uniform(0, 6.28), s); instance(c, (x, yy, hf(x, yy) - 1), rng.uniform(0, 6.28), s)
    else:
        g = mat_ground('fg', [(0.25, G('#2c3a1e')), (0.6, G('#4a5a2a')), (0.85, G('#6a6a3a'))], 0.15, 0.5, fog=(HAZE, 100, 200, 0.06))
        _, hf = strip('fl', 40, 60, 0.0, 1.2, ridge(20, 0.04, 3, 'fbm'), g, detail=0.3)
        bark = mat_bark('tb', G('#2b221a'), G('#5b4a3a'), fog=(HAZE, 100, 200, 0.06))
        leaf = mat_foliage('tl', [(0.15, G('#16301a')), (0.6, G('#2f5a26')), (0.9, G('#5a8a3a'))], fog=(HAZE, 100, 200, 0.06))
        x = -4
        while x < WB + 6:
            yy = rng.uniform(46, 60); r0 = rng.uniform(0.7, 1.3)
            bm = bmesh.new(); cyl(bm, (0, 0, -1), (rng.uniform(-.6, .6), 0, HB + 4), r0, r0 * 0.7, 14, int(x * 10), 0.15)
            for k in range(3):
                z = rng.uniform(4, 6); cyl(bm, (0, 0, z), (rng.uniform(-1.8, 1.8), rng.uniform(-.5, .5), z - .6), r0 * .8, r0 * .3, 8, int(x * 10) + k, 0.1)
            o = mesh_obj('trunk', bm, bark); o.location = (x, yy, hf(x, yy))
            bc = bmesh.new()
            for k in range(4):
                blob(bc, (rng.uniform(-5, 5), rng.uniform(-2, 2), HB - rng.uniform(-1, 3)), rng.uniform(2.5, 4.5), int(x) * 5 + k, 0.4, 1.4, 3, 0.7)
            cc = mesh_obj('can', bc, leaf); cc.location = (x, yy, 0)
            x += rng.uniform(9, 17)
        fm = [bark, leaf]
        scatter(protos('bush', 4, fm), hf, 70, 40, 52, 0.8, 1.8)
elif WI == 2:  # ---------------- Mountains: crisp alpine light
    HAZE = G('#c5d6ea')
    sky_world(32, 330, 0.35); sun(32, 330, 4.4, (1, .96, .9))
    if LAYER == 'far':
        rk = ([(0.3, G('#4f5866')), (0.7, G('#7d8594'))], 0.8)
        m1 = mat_ground('alp', [(0.3, G('#646e7d')), (0.7, G('#8892a0'))], 0.05, 0.6, snow=(10.5, 3, 5.0), rock=rk, fog=(HAZE, 380, 470, 0.38))
        strip('alp', 375, 410, 0.5, 17, ridge(30, 0.02, 8), m1, detail=3.0, dfreq=0.12)
        m2 = mat_ground('alp2', [(0.3, G('#56604f')), (0.7, G('#74806a'))], 0.06, 0.5, snow=(6, 2.5, 3.0), rock=rk, fog=(HAZE, 230, 330, 0.2))
        _, hf = strip('alp2', 240, 275, 0.2, 9, ridge(31, 0.026, 6, 'fbm'), m2, detail=1.6, dfreq=0.2)
        pm = [mat_bark('pb', G('#2e241c'), G('#46382b'), fog=(HAZE, 230, 330, 0.2)), mat_foliage('pf', [(0.2, G('#1b3326')), (0.8, G('#34553d'))], fog=(HAZE, 230, 330, 0.2))]
        pr = protos('pine', 4, pm)
        for i in range(220):
            x = rng.uniform(-5, WB + 5); yy = rng.uniform(246, 272)
            z = hf(x, yy)
            if z < 5.2:
                s = rng.uniform(1.0, 1.7)
                for part in pr[i % 4]: instance(part, (x, yy, z - 0.1), rng.uniform(0, 6.28), s)
    else:
        sn = mat_ground('snow', [(0.3, G('#dfe8f4')), (0.7, G('#f6f9ff'))], 0.1, 0.25, sss=0.2, fog=(HAZE, 100, 200, 0.05))
        _, hf = strip('mid', 40, 70, 0.0, 6.5, ridge(32, 0.024, 5, 'fbm'), sn, detail=1.0, dfreq=0.3)
        pm = [mat_bark('pb', G('#2e241c'), G('#46382b'), fog=(HAZE, 100, 200, 0.05)), mat_foliage('pf', [(0.15, G('#142a1e')), (0.6, G('#2a4a34')), (0.9, G('#4c6e50'))], fog=(HAZE, 100, 200, 0.05))]
        snowm = mat_simple('psnow', G('#f2f6ff'), 0.5, fog=(HAZE, 100, 200, 0.05))
        pr = []
        for i in range(5):
            t, c = pine(260 + i, 1.0, pm)
            # snow caps: a slightly shrunken copy of the upper surfaces, coloured white
            cap = c.copy(); cap.data = c.data.copy(); link(cap); cap.data.materials.clear(); cap.data.materials.append(snowm)
            import bmesh as _bm
            b = _bm.new(); b.from_mesh(cap.data); b.normal_update()
            kill = [f for f in b.faces if f.normal.z < 0.55]
            _bm.ops.delete(b, geom=kill, context='FACES')
            for v in b.verts: v.co.z += 0.012
            b.to_mesh(cap.data); b.free()
            for p in (t, c, cap): p.location.z = -500; hide(p)
            pr.append((t, c, cap))
        scatter(pr, hf, 46, 48, 72, 3.0, 5.6)
        rkm = mat_ground('rk', [(0.3, G('#5a6270')), (0.7, G('#8a92a0'))], 0.4, 0.8, snow=(-50, 1, 0.0), fog=(HAZE, 100, 200, 0.05))
        for i in range(26):
            x = rng.uniform(0, WB); yy = rng.uniform(42, 56); o = rock(400 + i, rng.uniform(.5, 1.4), rkm); o.location = (x, yy, hf(x, yy))
else:  # ---------------- Sky Islands: golden sunset
    HAZE = G('#f0b48c') if LAYER == 'far' else G('#e8a07c')
    sky_world(7, 290, 0.5, air=1.2, dust=2.0); sun(9, 290, 4.0, (1, .6, .32))
    def island(seed, cx, cy, cz, r, mats, trees, fogt):
        rnd = random.Random(seed)
        bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=40, radius1=r, radius2=0.0, depth=r * 1.6)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=6, use_grid_fill=True)
        for v in bm.verts:
            v.co.z = -(v.co.z + r * 0.8)  # apex down, flat top at z=0
            v.co.y *= 0.6
        displace(bm, r * 0.22, 1.2 / r, seed, 6)
        for v in bm.verts:
            if v.co.z > -r * 0.12: v.co.z = max(v.co.z, 0) * 0.3
        o = mesh_obj('isl', bm, mats[0]); o.location = (cx, cy, cz)
        g = bmesh.new(); bmesh.ops.create_circle(g, cap_ends=True, segments=40, radius=r * 1.03)
        for v in g.verts: v.co.y *= 0.62
        bmesh.ops.subdivide_edges(g, edges=g.edges[:], cuts=3, use_grid_fill=True)
        displace(g, r * 0.05, 2.0 / r, seed + 1, 3)
        for v in g.verts: v.co.z = abs(v.co.z) * 0.6 + 0.05
        go = mesh_obj('isg', g, mats[1]); go.location = (cx, cy, cz)
        for i in range(int(r * 2.5)):
            a = rnd.uniform(0, 6.28); rr = rnd.uniform(0, r * .8)
            p = trees[i % len(trees)]
            for part in p: instance(part, (cx + math.cos(a) * rr, cy + math.sin(a) * rr * .55, cz + 0.05), rnd.uniform(0, 6.28), rnd.uniform(.9, 1.6) * fogt)
    def clouds(name, z0, z1, y0, y1, dens, col, scale=0.08):
        bpy.ops.mesh.primitive_cube_add(location=(WB / 2, (y0 + y1) / 2, (z0 + z1) / 2))
        c = bpy.context.active_object; c.scale = (WB / 2 + 10, (y1 - y0) / 2, (z1 - z0) / 2)
        m = M(name); m.n.remove(m.bsdf)
        pv = m.node('ShaderNodeVolumePrincipled'); pv.inputs['Color'].default_value = (*col, 1)
        geo = m.node('ShaderNodeNewGeometry'); n = m.noise(scale, 7, 0.62, geo.outputs['Position'])
        sp = m.node('ShaderNodeSeparateXYZ'); m.link(geo.outputs['Position'], sp.inputs[0])
        hz = m.node('ShaderNodeMapRange'); hz.inputs['From Min'].default_value = z1; hz.inputs['From Max'].default_value = z0 + (z1 - z0) * 0.3
        m.link(sp.outputs['Z'], hz.inputs['Value'])
        mul = m.node('ShaderNodeMath'); mul.operation = 'MULTIPLY'; m.link(n.outputs['Fac'], mul.inputs[0]); m.link(hz.outputs[0], mul.inputs[1])
        th = m.node('ShaderNodeMapRange'); th.inputs['From Min'].default_value = 0.32; th.inputs['From Max'].default_value = 0.5; th.inputs['To Max'].default_value = dens
        m.link(mul.outputs[0], th.inputs['Value']); m.link(th.outputs[0], pv.inputs['Density'])
        if 'Anisotropy' in pv.inputs: pv.inputs['Anisotropy'].default_value = 0.3
        m.link(pv.outputs[0], m.out.inputs['Volume'])
        c.data.materials.append(m.m)
    if LAYER == 'far':
        fog = (HAZE, 260, 420, 0.4)
        rm = mat_ground('ir', [(0.3, G('#5a3428')), (0.7, G('#9a6446'))], 0.12, 0.9, fog=fog)
        gm = mat_ground('ig', [(0.3, G('#5c7a2c')), (0.7, G('#8aa040'))], 0.2, 0.3, fog=fog)
        fm = [mat_bark('ib', G('#3a2a1f'), G('#5a4433'), fog=fog), mat_foliage('il', [(0.2, G('#7a4a1a')), (0.8, G('#c27a2a'))], fog=fog)]
        tr = protos('tree', 4, fm)
        for i, (x, z, r, y) in enumerate([(12, 12, 6, 380), (38, 7, 4, 330), (60, 15, 8, 400), (85, 9, 5, 300), (100, 4, 3, 280), (25, 3.5, 2.5, 270), (72, 5, 3.5, 290)]):
            island(500 + i, x, y, z, r, (rm, gm), tr, 1.0)
        sc = bpy.context.scene; sc.cycles.volume_step_rate = 4 if PREVIEW else 2
    else:
        fog = (HAZE, 100, 220, 0.12)
        rm = mat_ground('ir', [(0.3, G('#6a3e30')), (0.7, G('#a06a48'))], 0.18, 0.7, fog=fog)
        gm = mat_ground('ig', [(0.3, G('#4f6e24')), (0.7, G('#86a23c'))], 0.3, 0.35, fog=fog)
        fm = [mat_bark('ib', G('#3a2a1f'), G('#5a4433'), fog=fog), mat_foliage('il', [(0.2, G('#6a3a14')), (0.6, G('#b0662a')), (0.9, G('#e0a040'))], fog=fog)]
        tr = protos('tree', 4, fm)
        for i, (x, z, r, y) in enumerate([(20, 9, 4, 120), (70, 11, 5, 140), (118, 7.5, 3.6, 110), (150, 10, 4.5, 130)]):
            island(600 + i, x, y, z, r, (rm, gm), tr, 1.4)
        sc = bpy.context.scene; sc.cycles.volume_step_rate = 4 if PREVIEW else 2
show_inst()
render(os.path.join(OUT, 'bg%d_%s%s.png' % (WI, LAYER, '_prev' if PREVIEW else '')))
