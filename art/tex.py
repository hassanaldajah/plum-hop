# Seamless textures (4D torus-mapped noise) and horizontally tiling grass/snow fringes.
# usage: blender -b --factory-startup -P tex.py -- [preview]
import bpy, sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, lib; importlib.reload(lib)
from lib import *
from mathutils import Vector

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
PREVIEW = 'preview' in argv
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'tex'); os.makedirs(OUT, exist_ok=True)
G = srgb

def torus(m, ru, rv, off=0.0):
    """Returns (vector socket, w socket) that wrap seamlessly over UV 0..1."""
    tc = m.node('ShaderNodeTexCoord'); sp = m.node('ShaderNodeSeparateXYZ'); m.link(tc.outputs['Object'], sp.inputs[0])
    def f(op, a, b=None):
        n = m.node('ShaderNodeMath'); n.operation = op
        if isinstance(a, float): n.inputs[0].default_value = a
        else: m.link(a, n.inputs[0])
        if b is not None:
            if isinstance(b, float): n.inputs[1].default_value = b
            else: m.link(b, n.inputs[1])
        return n.outputs[0]
    u = f('MULTIPLY', sp.outputs['X'], 2 * math.pi); v = f('MULTIPLY', sp.outputs['Y'], 2 * math.pi)
    cu = f('MULTIPLY', f('COSINE', u), ru); su = f('MULTIPLY', f('SINE', u), ru)
    cv = f('MULTIPLY', f('COSINE', v), rv); sv = f('ADD', f('MULTIPLY', f('SINE', v), rv), off)
    cb = m.node('ShaderNodeCombineXYZ'); m.link(cu, cb.inputs[0]); m.link(su, cb.inputs[1]); m.link(cv, cb.inputs[2])
    return cb.outputs[0], sv

def n4(m, vec, w, scale, detail=6, rough=0.6, dist=0.0):
    t = m.node('ShaderNodeTexNoise'); t.noise_dimensions = '4D'
    m.link(vec, t.inputs['Vector']); m.link(w, t.inputs['W'])
    t.inputs['Scale'].default_value = scale; t.inputs['Detail'].default_value = detail; t.inputs['Roughness'].default_value = rough
    if 'Distortion' in t.inputs: t.inputs['Distortion'].default_value = dist
    return t

def v4(m, vec, w, scale, feature='F1', rand=1.0):
    t = m.node('ShaderNodeTexVoronoi'); t.voronoi_dimensions = '4D'; t.feature = feature
    m.link(vec, t.inputs['Vector']); m.link(w, t.inputs['W']); t.inputs['Scale'].default_value = scale
    if 'Randomness' in t.inputs: t.inputs['Randomness'].default_value = rand
    return t

def mix(m, fac, a, b):
    x = m.node('ShaderNodeMix'); x.data_type = 'RGBA'
    for sock, val in ((0, fac), (6, a), (7, b)):
        if isinstance(val, (int, float)): x.inputs[sock].default_value = val
        elif isinstance(val, tuple): x.inputs[sock].default_value = (*val, 1)
        else: m.link(val, x.inputs[sock])
    return x.outputs[2]

def mr(m, val, a, b, lo=0.0, hi=1.0):
    n = m.node('ShaderNodeMapRange'); m.link(val, n.inputs['Value'])
    n.inputs['From Min'].default_value = a; n.inputs['From Max'].default_value = b; n.inputs['To Min'].default_value = lo; n.inputs['To Max'].default_value = hi
    return n.outputs[0]

def addf(m, a, b, op='ADD'):
    n = m.node('ShaderNodeMath'); n.operation = op; m.link(a, n.inputs[0]); m.link(b, n.inputs[1]); return n.outputs[0]

def tile_mat(kind):
    m = M(kind)
    if kind in ('soil0', 'soil1', 'soil3', 'rock2', 'cave'):
        pal = {'soil0': ('#5a3a22', '#8a5a34', '#a8774a', '#8f8576'), 'soil1': ('#2e2118', '#4a3524', '#5e4a32', '#6a6a5a'),
               'soil3': ('#6a3424', '#a45a3a', '#c98a5a', '#b09a88'), 'rock2': ('#4a505c', '#6c7482', '#8e96a2', '#a8aeb8'),
               'cave': ('#1e2030', '#33364a', '#4a4e66', '#5a5e78')}[kind]
        strat = kind in ('rock2', 'soil3', 'cave')
        vec, w = torus(m, 1.0, 2.2 if strat else 1.0)
        nb = n4(m, vec, w, 1.6, 8, 0.62, 0.3)
        base = m.ramp(nb.outputs['Fac'], [(0.3, G(pal[0])), (0.55, G(pal[1])), (0.75, G(pal[2]))])
        col = base.outputs['Color']
        vo = v4(m, vec, w, 5.5 if kind != 'cave' else 3.0, 'F1')
        vd = v4(m, vec, w, 5.5 if kind != 'cave' else 3.0, 'DISTANCE_TO_EDGE')
        peb = mr(m, vd.outputs['Distance'], 0.02, 0.12)  # 0 near cell edges
        pn = n4(m, vec, w, 4.0, 2, 0.5)
        sel = mr(m, pn.outputs['Fac'], 0.52, 0.58)      # only some cells become pebbles
        pm = addf(m, peb, sel, 'MULTIPLY')
        pcol = m.ramp(vo.outputs['Color'] if False else vo.outputs['Distance'], [(0.0, G(pal[3])), (1.0, G(pal[1]))])
        col = mix(m, pm, col, pcol.outputs['Color'])
        m.link(col, m.bsdf.inputs['Base Color']); m.set('Roughness', 0.95)
        h = addf(m, nb.outputs['Fac'], addf(m, pm, mr(m, vd.outputs['Distance'], 0.0, 0.2), 'MULTIPLY'))
        if kind == 'cave' or kind == 'rock2':
            cr = mr(m, vd.outputs['Distance'], 0.0, 0.03)
            h = addf(m, h, cr, 'MULTIPLY'); col2 = mix(m, cr, G(pal[0]), col); m.link(col2, m.bsdf.inputs['Base Color'])
        m.bump(h, 0.9, 0.05)
    elif kind == 'wood':
        vec, w = torus(m, 0.35, 3.0)
        g = n4(m, vec, w, 2.0, 10, 0.55, 2.5)
        r = m.ramp(g.outputs['Fac'], [(0.35, G('#5a3a1e')), (0.5, G('#8a5c30')), (0.65, G('#b07a42'))])
        m.link(r.outputs['Color'], m.bsdf.inputs['Base Color']); m.set('Roughness', 0.7); m.bump(g.outputs['Fac'], 0.6, 0.05)
    elif kind == 'stone':
        vec, w = torus(m, 1.0, 1.0)
        vd = v4(m, vec, w, 1.1, 'DISTANCE_TO_EDGE', 0.7); vo = v4(m, vec, w, 1.1, 'F1', 0.7)
        nb = n4(m, vec, w, 6.0, 8, 0.6)
        r = m.ramp(nb.outputs['Fac'], [(0.3, G('#6a6660')), (0.7, G('#9a948a'))])
        cell = m.ramp(vo.outputs['Color'] if 'Color' in vo.outputs else vo.outputs['Distance'], [(0.0, G('#8a857c')), (1.0, G('#b0aaa0'))])
        col = mix(m, 0.5, r.outputs['Color'], cell.outputs['Color'])
        gap = mr(m, vd.outputs['Distance'], 0.0, 0.06)
        col = mix(m, gap, G('#2e2c28'), col)
        m.link(col, m.bsdf.inputs['Base Color']); m.set('Roughness', 0.9)
        m.bump(addf(m, gap, mr(m, nb.outputs['Fac'], 0, 1, 0, 0.3)), 1.0, 0.05)
    return m.m

def render_tile(kind, px):
    reset(); setup(px, px, 16 if PREVIEW else 64)
    sc = bpy.context.scene; sc.render.film_transparent = False
    w = bpy.data.worlds.new('W'); sc.world = w; w.use_nodes = True; w.node_tree.nodes['Background'].inputs['Color'].default_value = (0.25, 0.25, 0.27, 1)
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
    bpy.ops.mesh.primitive_plane_add(size=3.0); p = bpy.context.active_object; p.data.materials.append(tile_mat(kind))
    p.rotation_euler = (math.radians(90), 0, 0)  # face -Y (towards camera)
    camera(0, -5, 0, 0, 1.0)
    sun(55, 330, 2.6)
    render(os.path.join(OUT, kind + '.png'))

# ---------- fringes: blades/lumps along a strip that wraps every TW units ----------
TW = 12.8  # world units across the tile (=128 logical px)
def fringe(kind, pxw, pxh):
    reset(); setup(pxw, pxh, 16 if PREVIEW else 64)
    hb = TW * pxh / pxw
    camera(TW / 2, -20, 0, 0, TW)  # frame z from -hb/2..hb/2, ground line at z=0 (centre)
    sky_world(45, 330, 0.5); sun(50, 330, 3.0, (1, .96, .9))
    rnd = random.Random(hash(kind) & 0xffff)
    if kind == 'snow':
        mat = mat_simple('snow', G('#f4f8ff'), 0.45); mat.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = 0.3
        geo = bmesh.new()
        for i in range(70):
            x = rnd.uniform(0, TW); r = rnd.uniform(0.25, 0.6); z = rnd.uniform(-0.25, 0.05)
            for dx in (-TW, 0, TW): blob(geo, (x + dx, rnd.uniform(-0.3, 0.3), z), r, i, 0.3, 1.6, 2, 0.55)
        mesh_obj('snow', geo, mat)
        ice = mat_simple('ice', G('#bfe6ff'), 0.08, trans=0.7, ior=1.31); sc = bpy.context.scene; sc.render.film_transparent = True
        try: sc.cycles.film_transparent_glass = True
        except Exception: pass
        ic = bmesh.new()
        for i in range(10):
            x = rnd.uniform(0, TW); L = rnd.uniform(0.4, 1.2)
            for dx in (-TW, 0, TW): cyl(ic, (x + dx, -0.2, -0.3), (x + dx + rnd.uniform(-.03, .03), -0.2, -0.3 - L), 0.09, 0.005, 6, i, 0.0)
        mesh_obj('icicles', ic, ice)
    else:
        pal = {'grass0': ['#2f6b1f', '#4f8f2a', '#7ab23c', '#a8c85a'], 'grass1': ['#1c3d17', '#2f5a22', '#4a7a2a', '#6a8a3a'],
               'grass3': ['#5a6a1c', '#8a9a2a', '#c2b04a', '#d9a050']}[kind]
        mats = [mat_simple('g%d' % i, G(c), 0.6) for i, c in enumerate(pal)]
        for mm in mats: mm.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = 0.2
        gb = [bmesh.new() for _ in mats]
        n = 900 if kind != 'grass1' else 700
        for i in range(n):
            x = rnd.uniform(0, TW); y = rnd.uniform(-0.6, 0.6); hgt = rnd.uniform(0.35, 1.0) * (1.25 if kind == 'grass3' else 1.0)
            if rnd.random() < 0.08: hgt *= 1.6
            lean = rnd.uniform(-0.35, 0.35); k = min(3, int(rnd.random() * 4))
            for dx in (-TW, 0, TW):
                b = gb[k]; base = (x + dx, y, -0.25)
                v0 = b.verts.new((base[0] - 0.035, y, -0.25)); v1 = b.verts.new((base[0] + 0.035, y, -0.25))
                vm0 = b.verts.new((base[0] + lean * 0.4 - 0.025, y, -0.25 + hgt * 0.55)); vm1 = b.verts.new((base[0] + lean * 0.4 + 0.025, y, -0.25 + hgt * 0.55))
                vt = b.verts.new((base[0] + lean, y + rnd.uniform(-.05, .05), -0.25 + hgt))
                b.faces.new((v0, v1, vm1, vm0)); b.faces.new((vm0, vm1, vt))
        for b, mm in zip(gb, mats): mesh_obj('blades', b, mm, smooth=False)
        if kind == 'grass1':  # moss lumps and fallen leaves
            mo = mat_foliage('moss', [(0.2, G('#2a4a1c')), (0.8, G('#4f7a2c'))], scale=6)
            mb = bmesh.new()
            for i in range(40):
                x = rnd.uniform(0, TW)
                for dx in (-TW, 0, TW): blob(mb, (x + dx, rnd.uniform(-.3, .3), -0.3), rnd.uniform(.18, .35), i, 0.4, 2.0, 2, 0.5)
            mesh_obj('moss', mb, mo)
        if kind == 'grass0':  # a few tiny wild flowers
            fl = [mat_simple('f%d' % i, G(c), 0.5) for i, c in enumerate(['#ffffff', '#ffd23e', '#e85a8a'])]
            fb = [bmesh.new() for _ in fl]
            for i in range(26):
                x = rnd.uniform(0, TW); hgt = rnd.uniform(0.5, 0.9); k = i % 3
                for dx in (-TW, 0, TW): blob(fb[k], (x + dx, -0.5, -0.25 + hgt), 0.07, i, 0.2, 2, 1, 0.7)
            for b, mm in zip(fb, fl): mesh_obj('flowers', b, mm)
    render(os.path.join(OUT, 'fringe_' + kind + '.png'))

S = 0.5 if PREVIEW else 1
for k in ('soil0', 'soil1', 'soil3', 'rock2', 'cave', 'wood', 'stone'):
    render_tile(k, int(256 * S))
for k in ('grass0', 'grass1', 'grass3', 'snow'):
    fringe(k, int(256 * S), int(64 * S))
