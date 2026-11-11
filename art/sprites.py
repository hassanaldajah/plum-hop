# 3D-rendered sprites (enemies, gem, decor). usage: blender -b --factory-startup -P sprites.py -- [preview] [name ...]
import bpy, sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import importlib, lib; importlib.reload(lib)
from lib import *
from mathutils import Vector, Matrix, noise

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
PREVIEW = 'preview' in argv; ONLY = [a for a in argv if a != 'preview']
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out', 'spr'); os.makedirs(OUT, exist_ok=True)
G = srgb
PX = 4  # render pixels per logical pixel (1 BU = 10 logical px)

def frame_cam(x0, x1, z0, z1, pitch=10, asp=1.0):
    w, h = x1 - x0, z1 - z0; cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    p = math.radians(pitch)
    sc = max(w, h * asp) if asp >= 1 else max(h, w / asp)
    camera(cx, -30 * math.cos(p), cz + 30 * math.sin(p), pitch, sc)

def scene(wl, hl, bbox, pitch=10, light=(50, 330, 4.2), sky=0.32):
    reset(); setup(int(wl * PX * (0.5 if PREVIEW else 1)), int(hl * PX * (0.5 if PREVIEW else 1)), 24 if PREVIEW else 96)
    frame_cam(*bbox, pitch=pitch, asp=wl / hl)
    for lk in ('AgX - Punchy', 'Punchy'):
        try: bpy.context.scene.view_settings.look = lk; break
        except Exception: pass
    sky_world(40, 330, sky); sun(light[0], light[1], light[2], (1, .97, .92))
    # soft fill from the right so dark sides keep detail
    f = sun(25, 150, 0.8, (.8, .87, 1)); f.data.angle = math.radians(30)

def sph(bm_t, c, r, sc=(1, 1, 1), sub=3, rot=None):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    for v in bm.verts:
        v.co = Vector((v.co.x * sc[0], v.co.y * sc[1], v.co.z * sc[2]))
        if rot: v.co = rot @ v.co
        v.co += Vector(c)
    me = bpy.data.meshes.new('t'); bm.to_mesh(me); bm.free(); bm_t.from_mesh(me); bpy.data.meshes.remove(me)

def obj(bm, mat, name='o', smooth=True): return mesh_obj(name, bm, mat, smooth)

def gloss(name, col, rough=0.3, metal=0.0, coat=0.0, sheen=0.0):
    m = mat_simple(name, G(col), rough, metal, coat=coat)
    if sheen: m.node_tree.nodes['Principled BSDF'].inputs['Sheen Weight'].default_value = sheen
    return m

# ------------------------------------------------------------------ enemies
def beetle(fr):
    shell = M('shell'); geo = shell.node('ShaderNodeNewGeometry')
    lw = shell.node('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.35
    r = shell.ramp(lw.outputs['Facing'], [(0.0, G('#2a6a7a')), (0.6, G('#173848')), (1.0, G('#3a2a6a'))])
    shell.link(r.outputs['Color'], shell.bsdf.inputs['Base Color']); shell.set('Metallic', 0.7); shell.set('Roughness', 0.22); shell.set('Coat Weight', 1.0)
    nb = shell.noise(40, 4, 0.6, geo.outputs['Position']); shell.bump(nb.outputs['Fac'], 0.08, 0.02)
    dark = gloss('dark', '#15121a', 0.35, 0.2, 0.5); eye = gloss('eye', '#050505', 0.08, 0, 1)
    b = bmesh.new(); sph(b, (-.05, 0, .55), 1, (.85, .62, .5), 4); s = obj(b, shell.m)
    b = bmesh.new(); sph(b, (.72, 0, .55), .38, (.72, 1.25, .8), 3); obj(b, shell.m)
    b = bmesh.new(); sph(b, (1.02, 0, .47), .25, (1, 1, .9), 3)
    for sgn in (-1, 1):
        cyl(b, (1.12, .1 * sgn, .4), (1.38, .03 * sgn, .33), .05, .012, 6, 0, 0)
        cyl(b, (1.12, .13 * sgn, .6), (1.38, .3 * sgn, .9), .022, .012, 5, 0, 0); cyl(b, (1.38, .3 * sgn, .9), (1.62, .38 * sgn, .86), .02, .01, 5, 0, 0)
    obj(b, dark)
    b = bmesh.new()
    for sgn in (-1, 1): sph(b, (1.16, .17 * sgn, .53), .075)
    obj(b, eye)
    b = bmesh.new(); ph = (0.16 if fr == 0 else -0.16)
    for i, hx in enumerate((.55, .05, -.4)):
        for sgn in (-1, 1):
            off = ph * (1 if (i % 2 == 0) == (sgn > 0) else -1)
            hip = Vector((hx, .3 * sgn, .4)); knee = Vector((hx + off * .6 + (.15 if i == 0 else -.1 if i == 2 else 0), .72 * sgn, .52)); foot = Vector((hx + off + (.3 if i == 0 else -.25 if i == 2 else 0), .9 * sgn, .02))
            cyl(b, hip, knee, .06, .045, 6, 0, 0); cyl(b, knee, foot, .045, .02, 6, 0, 0)
    obj(b, dark)

def hedgehog(fr):
    skin = gloss('skin', '#a8784c', 0.7); face = gloss('face', '#c99a6c', 0.6, sheen=0.5); blk = gloss('nose', '#0a0806', 0.15, coat=1)
    sp1 = gloss('sp1', '#3a2618', 0.45); sp2 = gloss('sp2', '#d8c29a', 0.45)
    b = bmesh.new(); sph(b, (0, 0, .62), 1, (1.0, .78, .62), 4); obj(b, skin)
    rnd = random.Random(7); b1 = bmesh.new(); b2 = bmesh.new()
    for i in range(420):
        u = rnd.uniform(0, 6.283); v = math.acos(rnd.uniform(-0.15, 1)); n = Vector((math.sin(v) * math.cos(u), math.sin(v) * math.sin(u), math.cos(v)))
        p = Vector((n.x * 1.0, n.y * .78, n.z * .62 + .62))
        if p.x > .62 or p.z < .3: continue
        d = (n + Vector((-0.9, 0, 0.25))).normalized(); L = rnd.uniform(.42, .62)
        tgt = b1 if rnd.random() < .62 else b2
        cyl(tgt, p - d * .08, p + d * L, .045, .004, 5, 0, 0)
    obj(b1, sp1, smooth=False); obj(b2, sp2, smooth=False)
    b = bmesh.new(); cyl(b, (.62, 0, .5), (1.22, 0, .4), .36, .09, 16, 0, 0); sph(b, (.66, 0, .5), .38, (1, 1, .95), 3)
    for sgn in (-1, 1): sph(b, (.66, .36 * sgn, .82), .1, (1, .5, 1), 2)
    obj(b, face)
    b = bmesh.new(); sph(b, (1.24, 0, .41), .09)
    for sgn in (-1, 1): sph(b, (.95, .24 * sgn, .63), .07)
    obj(b, blk)
    b = bmesh.new(); ph = .14 if fr == 0 else -.14
    for k, (fx, sgn) in enumerate(((.5, -1), (.5, 1), (-.5, -1), (-.5, 1))):
        o = ph if (k in (0, 3)) else -ph
        sph(b, (fx + o, .42 * sgn, .07), .14, (1.3, .9, .6), 2)
    obj(b, face)

def bee(fr):
    st = M('stripe'); geo = st.node('ShaderNodeNewGeometry'); sp = st.node('ShaderNodeSeparateXYZ'); st.link(geo.outputs['Position'], sp.inputs[0])
    mu = st.node('ShaderNodeMath'); mu.operation = 'MULTIPLY'; mu.inputs[1].default_value = 11.0; st.link(sp.outputs['X'], mu.inputs[0])
    si = st.node('ShaderNodeMath'); si.operation = 'SINE'; st.link(mu.outputs[0], si.inputs[0])
    r = st.ramp(si.outputs[0], [(0.38, G('#1a1208')), (0.62, G('#f2b418'))])
    st.link(r.outputs['Color'], st.bsdf.inputs['Base Color']); st.set('Roughness', 0.55); st.set('Sheen Weight', 1.0); st.set('Coat Weight', 0.3)
    nb = st.noise(60, 3, 0.7, geo.outputs['Position']); st.bump(nb.outputs['Fac'], 0.25, 0.02)
    fuzz = gloss('fuzz', '#3a2a12', 0.8, sheen=1.0); blk = gloss('blk', '#0a0806', 0.1, coat=1)
    wing = mat_simple('wing', G('#e8f4ff'), 0.12); wn = wing.node_tree.nodes['Principled BSDF']; wn.inputs['Alpha'].default_value = 0.38
    b = bmesh.new(); sph(b, (-.42, 0, 0), .5, (1.3, .95, .95), 4); cyl(b, (-1.05, 0, -.02), (-1.25, 0, -.06), .05, .005, 6, 0, 0); obj(b, st.m)
    b = bmesh.new(); sph(b, (.26, 0, .04), .36, (1, .95, .95), 3)
    for sgn in (-1, 1):
        for k in range(3): cyl(b, (.2 - k * .2, .15 * sgn, -.25), (.12 - k * .28, .22 * sgn, -.62), .03, .015, 5, 0, 0)
    obj(b, fuzz)
    b = bmesh.new(); sph(b, (.62, 0, .02), .26, (.9, 1, 1), 3)
    for sgn in (-1, 1): cyl(b, (.72, .1 * sgn, .2), (.95, .2 * sgn, .45), .018, .012, 5, 0, 0)
    obj(b, blk)
    b = bmesh.new()
    for sgn in (-1, 1): sph(b, (.7, .16 * sgn, .08), .13, (.8, .7, 1.1), 2)
    obj(b, gloss('eye', '#1a1410', 0.05, coat=1))
    b = bmesh.new(); ang = math.radians(28 if fr == 0 else -32)
    for sgn in (-1, 1):
        for k, (L, off) in enumerate(((.62, 0.0), (.42, -.28))):
            R = Matrix.Rotation(ang * sgn * -1, 3, 'X') @ Matrix.Rotation(math.radians(-22 - k * 18), 3, 'Z')
            bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1)
            for v in bm.verts:
                q = Vector((v.co.x * L * .5, v.co.y * L + L * sgn * 1.0, v.co.z * .02))
                v.co = Matrix.Rotation(ang * -sgn, 3, 'X') @ q + Vector((.15 + off, .12 * sgn, .32))
            me = bpy.data.meshes.new('t'); bm.to_mesh(me); bm.free(); b.from_mesh(me); bpy.data.meshes.remove(me)
    obj(b, wing)

def bird(fr):
    fe = M('feather'); geo = fe.node('ShaderNodeNewGeometry'); sp = fe.node('ShaderNodeSeparateXYZ'); fe.link(geo.outputs['Normal'], sp.inputs[0])
    mz = fe.node('ShaderNodeMapRange'); mz.inputs['From Min'].default_value = -1; fe.link(sp.outputs['Z'], mz.inputs['Value'])
    r = fe.ramp(mz.outputs[0], [(0.22, G('#efe6d6')), (0.34, G('#2e3c5a')), (0.8, G('#1a2640'))])
    fe.link(r.outputs['Color'], fe.bsdf.inputs['Base Color']); fe.set('Roughness', 0.6); fe.set('Sheen Weight', 0.6)
    nb = fe.noise(30, 4, 0.6, geo.outputs['Position']); fe.bump(nb.outputs['Fac'], 0.2, 0.03)
    wingm = gloss('wing', '#1e2a44', 0.55, sheen=0.5); beak = gloss('beak', '#f0a020', 0.35); blk = gloss('eye', '#050505', 0.05, coat=1)
    b = bmesh.new(); sph(b, (0, 0, 0), .55, (1.45, .78, .8), 4); sph(b, (.74, 0, .2), .34, (1, .95, .95), 3)
    obj(b, fe.m)
    b = bmesh.new(); cyl(b, (.98, 0, .17), (1.34, 0, .12), .11, .005, 10, 0, 0); obj(b, beak)
    b = bmesh.new(); sph(b, (.92, -.22, .3), .065); sph(b, (.92, .22, .3), .065); obj(b, blk)
    b = bmesh.new()
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1)
    for v in bm.verts: v.co = Vector((-.7 - (v.co.x + 1) * .4, v.co.y * .28 * (1 + (1 - v.co.x) * .4), v.co.z * .05 + .05))
    me = bpy.data.meshes.new('t'); bm.to_mesh(me); bm.free(); b.from_mesh(me); bpy.data.meshes.remove(me)
    lift = (1.15, 0.25, -0.85)[fr]
    for sgn in (-1, 1):
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1)
        for v in bm.verts:
            t = (v.co.y + 1) / 2  # 0 at shoulder .. 1 at tip
            q = Vector((v.co.x * .42 * (1 - t * .55) - t * .35, t * 1.5, v.co.z * .05))
            a = math.atan2(lift, 1.0)
            y = q.y * math.cos(a); z = q.y * math.sin(a) + q.z
            v.co = Vector((q.x + .05, (y + .25) * sgn, z + .22))
        me = bpy.data.meshes.new('t'); bm.to_mesh(me); bm.free(); b.from_mesh(me); bpy.data.meshes.remove(me)
    obj(b, wingm)

def icicle(fr):
    ice = mat_simple('ice', G('#cfeeff'), 0.06, trans=0.85, ior=1.31)
    b = bmesh.new(); bmesh.ops.create_cone(b, cap_ends=True, cap_tris=False, segments=14, radius1=.28, radius2=0.0, depth=2.2)
    bmesh.ops.subdivide_edges(b, edges=b.edges[:], cuts=8, use_grid_fill=True)
    for v in b.verts:
        v.co.z = -(v.co.z + 1.1)  # tip down, base at 0
        k = 1 + .12 * math.sin(v.co.z * 14) + .08 * noise.noise(v.co * 6)
        v.co.x *= k; v.co.y *= k
    obj(b, ice)
    sn = mat_simple('snow', G('#f6f9ff'), 0.5); sn.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = .3
    b = bmesh.new(); sph(b, (0, 0, .02), .38, (1.2, 1, .45), 3); obj(b, sn)

def gem(fr):
    b = bmesh.new()
    bmesh.ops.create_cone(b, cap_ends=True, cap_tris=True, segments=8, radius1=.52, radius2=.3, depth=.26)
    for v in b.verts: v.co.z += .13
    me = bpy.data.meshes.new('t'); b.to_mesh(me); b.free()
    b = bmesh.new(); b.from_mesh(me); bpy.data.meshes.remove(me)
    p = bmesh.new(); bmesh.ops.create_cone(p, cap_ends=True, cap_tris=True, segments=8, radius1=0.0, radius2=.52, depth=.62)
    for v in p.verts: v.co.z -= .31
    me = bpy.data.meshes.new('t'); p.to_mesh(me); p.free(); b.from_mesh(me); bpy.data.meshes.remove(me)
    bmesh.ops.remove_doubles(b, verts=b.verts[:], dist=0.001)
    for v in b.verts: v.co = Matrix.Rotation(math.radians(-55), 3, 'X') @ Matrix.Rotation(math.radians(fr * 22.5 + 11), 3, 'Z') @ v.co
    m = mat_simple('topaz', G('#ffb000'), 0.06, 0.35, coat=1.0)
    m.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (*G('#ff8c00'), 1)
    m.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 0.25
    obj(b, m, smooth=False)

# ------------------------------------------------------------------ decor
def tree0(fr):
    mats = [mat_bark('bk', G('#3a2a1f'), G('#6a5038')), mat_foliage('lf', [(0.15, G('#1a3c12')), (0.5, G('#2f6420')), (0.85, G('#6a9a38'))])]
    broadleaf(31 + fr * 7, 5.6, mats, 1.0 + fr * .15)
def tree3(fr):
    mats = [mat_bark('bk', G('#3a2a1f'), G('#5a4433')), mat_foliage('lf', [(0.15, G('#5a1e08')), (0.5, G('#a8481a')), (0.85, G('#e09a30'))])]
    broadleaf(77 + fr * 5, 5.0, mats, 1.1)
def pine2(fr):
    pm = [mat_bark('pb', G('#2e241c'), G('#46382b')), mat_foliage('pf', [(0.15, G('#142a1e')), (0.6, G('#2a4a34')), (0.9, G('#4c6e50'))])]
    t, c = pine(91 + fr * 3, 5.6, pm)
    cap = c.copy(); cap.data = c.data.copy(); link(cap); cap.data.materials.clear()
    sn = mat_simple('psnow', G('#f2f6ff'), 0.5); sn.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = .3; cap.data.materials.append(sn)
    b = bmesh.new(); b.from_mesh(cap.data); b.normal_update()
    bmesh.ops.delete(b, geom=[f for f in b.faces if f.normal.z < 0.5], context='FACES')
    for v in b.verts: v.co.z += 0.04
    b.to_mesh(cap.data); b.free()
def bush0(fr):
    bush(12 + fr, 1.0, mat_foliage('lf', [(0.15, G('#24501b')), (0.5, G('#3f7a28')), (0.85, G('#7fae45'))]))
def bush1(fr):
    bush(40 + fr, 1.0, mat_foliage('lf', [(0.15, G('#12281a')), (0.5, G('#244a26')), (0.85, G('#3f6a30'))]))
def bush3(fr):
    bush(60 + fr, 1.0, mat_foliage('lf', [(0.15, G('#6a3a14')), (0.5, G('#a8602a')), (0.85, G('#d9a040'))]))
def rock0(fr):
    rock(5 + fr, 1.0, mat_ground('rk', [(0.3, G('#6a6660')), (0.7, G('#9a948a'))], 1.2, 0.8, rock=None), 0.65, 4, 0.4)
def rock2(fr):
    rock(15 + fr, 1.0, mat_ground('rk', [(0.3, G('#5a6270')), (0.7, G('#8a92a0'))], 1.2, 0.8, snow=(0.25, 0.3, 0.3)), 0.7, 4, 0.45)
def shroom(fr):
    stem = gloss('stem', '#efe6d0', 0.7, sheen=0.4)
    cap = M('cap'); geo = cap.node('ShaderNodeNewGeometry')
    vo = cap.node('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 5.0; cap.link(geo.outputs['Position'], vo.inputs['Vector'])
    r = cap.ramp(vo.outputs['Distance'], [(0.12, G('#f4efe6')), (0.16, G('#c81e1e'))])
    cap.link(r.outputs['Color'], cap.bsdf.inputs['Base Color']); cap.set('Roughness', 0.35); cap.set('Coat Weight', 0.6)
    for k, (x, h, s) in enumerate(((0, .9, 1.0), (.55, .55, .65), (-.45, .4, .5))):
        b = bmesh.new(); cyl(b, (x, 0, 0), (x + .04, 0, h * s + .1), .13 * s, .1 * s, 12, k, 0.0); obj(b, stem)
        b = bmesh.new(); sph(b, (x + .04, 0, h * s + .1), .42 * s, (1, 1, .55), 3)
        bm2 = b
        for v in bm2.verts:
            if v.co.z < h * s + .1: v.co.z = h * s + .1 - (h * s + .1 - v.co.z) * .25
        obj(b, cap.m)

SPR = {
    # name: (builder, frames, logical w, h, bbox x0,x1,z0,z1 (BU), pitch)
    'beetle': (beetle, 2, 20, 14, (-1.1, 1.9, -.3, 1.8), 12),
    'hedgehog': (hedgehog, 2, 22, 15, (-1.3, 1.5, -.2, 1.75), 10),
    'bee': (bee, 2, 18, 16, (-1.3, 1.1, -.8, 1.3), 8),
    'bird': (bird, 3, 28, 22, (-1.45, 1.4, -1.0, 1.4), 8),
    'icicle': (icicle, 1, 8, 26, (-.4, .4, -2.4, .2), 0),
    'gem': (gem, 1, 12, 12, (-.62, .62, -.62, .62), 0),
    'tree0': (tree0, 2, 56, 66, (-2.8, 2.8, -.1, 6.5), 6),
    'tree3': (tree3, 1, 52, 58, (-2.6, 2.6, -.1, 5.7), 6),
    'pine2': (pine2, 2, 34, 60, (-1.7, 1.7, -.1, 5.9), 6),
    'bush0': (bush0, 2, 26, 15, (-1.3, 1.3, -.1, 1.4), 10), 'bush1': (bush1, 1, 26, 15, (-1.3, 1.3, -.1, 1.4), 10),
    'bush3': (bush3, 1, 26, 15, (-1.3, 1.3, -.1, 1.4), 10),
    'rock0': (rock0, 1, 22, 13, (-1.1, 1.1, -.2, 1.1), 14), 'rock2': (rock2, 1, 22, 13, (-1.1, 1.1, -.2, 1.1), 14),
    'shroom': (shroom, 1, 16, 14, (-.8, .8, -.05, 1.35), 10),
}
for name, (fn, frames, wl, hl, bbox, pitch) in SPR.items():
    if ONLY and name not in ONLY: continue
    for fr in range(frames):
        scene(wl, hl, bbox, pitch)
        if name in ('icicle', 'gem'):
            try: bpy.context.scene.cycles.film_transparent_glass = (name == 'icicle')
            except Exception: pass
        fn(fr)
        render(os.path.join(OUT, '%s%d.png' % (name, fr)))
