# Shared Blender helpers for Plum Hop art (backgrounds + sprites). Blender 5.2, Cycles.
import bpy, bmesh, math, random
from mathutils import noise, Vector

def reset():
    for o in list(bpy.data.objects): bpy.data.objects.remove(o, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.worlds):
        for b in list(coll): coll.remove(b)

def setup(wpx, hpx, samples=48, transparent=True):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    p = bpy.context.preferences.addons['cycles'].preferences
    try:
        p.compute_device_type = 'OPTIX'; p.get_devices()
        for d in p.devices: d.use = (d.type == 'OPTIX')
        sc.cycles.device = 'GPU'
    except Exception as e:
        print('GPU unavailable', e); sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    try: sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception: pass
    sc.cycles.max_bounces = 6
    sc.cycles.volume_bounces = 1
    sc.render.film_transparent = transparent
    sc.render.resolution_x = wpx; sc.render.resolution_y = hpx; sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.color_depth = '8'
    sc.view_settings.view_transform = 'AgX'
    for look in ('AgX - Medium High Contrast', 'Medium High Contrast', 'AgX - Base Contrast', 'None'):
        try: sc.view_settings.look = look; break
        except Exception: pass
    return sc

def camera(cx, cy, cz, pitch_deg, ortho_scale, yaw_deg=0):
    cd = bpy.data.cameras.new('cam'); cd.type = 'ORTHO'; cd.ortho_scale = ortho_scale
    cd.clip_start = 0.1; cd.clip_end = 5000
    o = bpy.data.objects.new('cam', cd); bpy.context.scene.collection.objects.link(o)
    o.location = (cx, cy, cz); o.rotation_euler = (math.radians(90 - pitch_deg), 0, math.radians(yaw_deg))
    bpy.context.scene.camera = o
    return o

def sky_world(elev, rot, strength=1.0, sun_disc=False, air=1.0, dust=1.0):
    w = bpy.data.worlds.new('W'); bpy.context.scene.world = w; w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    s = nt.nodes.new('ShaderNodeTexSky')
    try: s.sky_type = 'MULTIPLE_SCATTERING'
    except Exception: s.sky_type = 'HOSEK_WILKIE'
    for k, v in (('sun_elevation', math.radians(elev)), ('sun_rotation', math.radians(rot)), ('sun_disc', sun_disc),
                 ('air_density', air), ('aerosol_density', dust), ('dust_density', dust)):
        if hasattr(s, k):
            try: setattr(s, k, v)
            except Exception: pass
    b = nt.nodes.new('ShaderNodeBackground'); b.inputs['Strength'].default_value = strength
    o = nt.nodes.new('ShaderNodeOutputWorld')
    nt.links.new(s.outputs[0], b.inputs[0]); nt.links.new(b.outputs[0], o.inputs[0])

def sun(elev, rot, strength=4.0, color=(1, 1, 1), angle=1.5):
    ld = bpy.data.lights.new('sun', 'SUN'); ld.energy = strength; ld.color = color; ld.angle = math.radians(angle)
    o = bpy.data.objects.new('sun', ld); bpy.context.scene.collection.objects.link(o)
    # light travels along -Z of the lamp: point it from (rot, elev) toward the scene
    o.rotation_euler = (math.radians(90 - elev), 0, math.radians(rot))
    return o

def link(obj):
    bpy.context.scene.collection.objects.link(obj); return obj

def mesh_obj(name, bm, mat=None, smooth=True):
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    if smooth: me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    o = bpy.data.objects.new(name, me)
    if mat: me.materials.append(mat)
    return link(o)

def grid_mesh(name, x0, x1, y0, y1, nx, ny, hf, mat=None):
    me = bpy.data.meshes.new(name)
    verts = []
    for j in range(ny + 1):
        y = y0 + (y1 - y0) * j / ny
        for i in range(nx + 1):
            x = x0 + (x1 - x0) * i / nx
            verts.append((x, y, hf(x, y)))
    faces = []
    for j in range(ny):
        for i in range(nx):
            a = j * (nx + 1) + i
            faces.append((a, a + 1, a + nx + 2, a + nx + 1))
    me.from_pydata(verts, [], faces); me.update()
    me.polygons.foreach_set('use_smooth', [True] * len(me.polygons))
    if mat: me.materials.append(mat)
    o = bpy.data.objects.new(name, me); return link(o)

# ---------------- materials ----------------
class M:
    def __init__(self, name):
        self.m = bpy.data.materials.new(name); self.m.use_nodes = True
        self.nt = self.m.node_tree; self.n = self.nt.nodes; self.l = self.nt.links
        self.bsdf = self.n['Principled BSDF']; self.out = self.n['Material Output']
    def node(self, t, **kw):
        x = self.n.new(t)
        for k, v in kw.items(): setattr(x, k, v)
        return x
    def link(self, a, b): self.l.new(a, b)
    def set(self, name, v):
        if name in self.bsdf.inputs: self.bsdf.inputs[name].default_value = v
    def ramp(self, fac_socket, stops):
        r = self.node('ShaderNodeValToRGB')
        el = r.color_ramp.elements
        el[0].position = stops[0][0]; el[0].color = (*stops[0][1], 1)
        el[1].position = stops[-1][0]; el[1].color = (*stops[-1][1], 1)
        for p, c in stops[1:-1]:
            e = el.new(p); e.color = (*c, 1)
        self.link(fac_socket, r.inputs[0]); return r
    def noise(self, scale, detail=6, rough=0.55, coord=None, w=None):
        t = self.node('ShaderNodeTexNoise'); t.inputs['Scale'].default_value = scale
        t.inputs['Detail'].default_value = detail; t.inputs['Roughness'].default_value = rough
        if coord is not None: self.link(coord, t.inputs['Vector'])
        return t
    def bump(self, height_socket, strength=0.4, dist=0.1):
        b = self.node('ShaderNodeBump'); b.inputs['Strength'].default_value = strength
        b.inputs['Distance'].default_value = dist
        self.link(height_socket, b.inputs['Height']); self.link(b.outputs['Normal'], self.bsdf.inputs['Normal'])
        return b
    def fog(self, color, d0, d1, fmax):
        """Aerial perspective: blend toward a flat haze colour by view depth."""
        cam = self.node('ShaderNodeCameraData')
        mr = self.node('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = d0; mr.inputs['From Max'].default_value = d1
        mr.inputs['To Min'].default_value = 0; mr.inputs['To Max'].default_value = fmax
        self.link(cam.outputs['View Z Depth'], mr.inputs['Value'])
        em = self.node('ShaderNodeEmission'); em.inputs['Color'].default_value = (*color, 1); em.inputs['Strength'].default_value = 1.0
        mix = self.node('ShaderNodeMixShader')
        self.link(mr.outputs[0], mix.inputs[0]); self.link(self.bsdf.outputs[0], mix.inputs[1]); self.link(em.outputs[0], mix.inputs[2])
        self.link(mix.outputs[0], self.out.inputs['Surface'])
        return self

def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((v + 0.055) / 1.055) ** 2.4 if v > 0.04045 else v / 12.92 for v in c)

def mat_ground(name, stops, scale=0.08, bump=0.35, rough=0.9, snow=None, rock=None, fog=None, sss=0.0):
    """Natural ground: noise-mixed colours, optional rock on steep faces and snow on flat high faces."""
    m = M(name)
    geo = m.node('ShaderNodeNewGeometry')
    n1 = m.noise(scale, 8, 0.6, geo.outputs['Position'])
    r1 = m.ramp(n1.outputs['Fac'], stops)
    col = r1.outputs['Color']
    if rock:
        sep = m.node('ShaderNodeSeparateXYZ'); m.link(geo.outputs['Normal'], sep.inputs[0])
        st = m.node('ShaderNodeMapRange'); st.inputs['From Min'].default_value = rock[1]; st.inputs['From Max'].default_value = rock[1] - 0.12
        m.link(sep.outputs['Z'], st.inputs['Value'])
        n2 = m.noise(scale * 3, 10, 0.65, geo.outputs['Position'])
        r2 = m.ramp(n2.outputs['Fac'], rock[0])
        mx = m.node('ShaderNodeMix'); mx.data_type = 'RGBA'
        m.link(st.outputs[0], mx.inputs[0]); m.link(col, mx.inputs[6]); m.link(r2.outputs['Color'], mx.inputs[7]); col = mx.outputs[2]
    if snow:
        sep = m.node('ShaderNodeSeparateXYZ'); m.link(geo.outputs['Normal'], sep.inputs[0])
        sp = m.node('ShaderNodeSeparateXYZ'); m.link(geo.outputs['Position'], sp.inputs[0])
        n3 = m.noise(scale * 2.2, 6, 0.6, geo.outputs['Position'])
        add = m.node('ShaderNodeMath'); add.operation = 'MULTIPLY_ADD'
        m.link(n3.outputs['Fac'], add.inputs[0]); add.inputs[1].default_value = snow[2]; m.link(sp.outputs['Z'], add.inputs[2])
        hz = m.node('ShaderNodeMapRange'); hz.inputs['From Min'].default_value = snow[0]; hz.inputs['From Max'].default_value = snow[0] + snow[1]
        m.link(add.outputs[0], hz.inputs['Value'])
        nz = m.node('ShaderNodeMapRange'); nz.inputs['From Min'].default_value = 0.45; nz.inputs['From Max'].default_value = 0.7
        m.link(sep.outputs['Z'], nz.inputs['Value'])
        mul = m.node('ShaderNodeMath'); mul.operation = 'MULTIPLY'; m.link(hz.outputs[0], mul.inputs[0]); m.link(nz.outputs[0], mul.inputs[1])
        mx = m.node('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[7].default_value = (*srgb('#f4f8ff'), 1)
        m.link(mul.outputs[0], mx.inputs[0]); m.link(col, mx.inputs[6]); col = mx.outputs[2]
    m.link(col, m.bsdf.inputs['Base Color'])
    m.set('Roughness', rough)
    if sss: m.set('Subsurface Weight', sss)
    nb = m.noise(scale * 9, 4, 0.7, geo.outputs['Position'])
    m.bump(nb.outputs['Fac'], bump, 0.2)
    if fog: m.fog(*fog)
    return m.m

def mat_foliage(name, stops, fog=None, sss=0.15, scale=1.8):
    m = M(name)
    oi = m.node('ShaderNodeObjectInfo'); geo = m.node('ShaderNodeNewGeometry')
    n = m.noise(scale, 6, 0.65, geo.outputs['Position'])
    add = m.node('ShaderNodeMath'); add.operation = 'MULTIPLY_ADD'
    m.link(oi.outputs['Random'], add.inputs[0]); add.inputs[1].default_value = 0.45; m.link(n.outputs['Fac'], add.inputs[2])
    mp = m.node('ShaderNodeMath'); mp.operation = 'MULTIPLY'; m.link(add.outputs[0], mp.inputs[0]); mp.inputs[1].default_value = 0.72
    r = m.ramp(mp.outputs[0], stops)
    m.link(r.outputs['Color'], m.bsdf.inputs['Base Color'])
    m.set('Roughness', 0.75); m.set('Subsurface Weight', sss)
    if 'Subsurface Radius' in m.bsdf.inputs: m.bsdf.inputs['Subsurface Radius'].default_value = (0.3, 0.6, 0.15)
    nb = m.noise(scale * 7, 3, 0.8, geo.outputs['Position'])
    m.bump(nb.outputs['Fac'], 0.6, 0.1)
    if fog: m.fog(*fog)
    return m.m

def mat_simple(name, color, rough=0.6, metal=0.0, fog=None, bump=0.0, bscale=10, emission=None, coat=0.0, trans=0.0, ior=1.45):
    m = M(name); m.set('Base Color', (*color, 1)); m.set('Roughness', rough); m.set('Metallic', metal)
    if coat: m.set('Coat Weight', coat)
    if trans: m.set('Transmission Weight', trans); m.set('IOR', ior)
    if emission: m.set('Emission Color', (*emission[0], 1)); m.set('Emission Strength', emission[1])
    if bump:
        geo = m.node('ShaderNodeNewGeometry'); nb = m.noise(bscale, 8, 0.6, geo.outputs['Position']); m.bump(nb.outputs['Fac'], bump, 0.05)
    if fog: m.fog(*fog)
    return m.m

def mat_bark(name, c1, c2, fog=None, scale=3.0):
    m = M(name); geo = m.node('ShaderNodeNewGeometry')
    mp = m.node('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (6, 6, 0.8); m.link(geo.outputs['Position'], mp.inputs['Vector'])
    n = m.noise(scale, 10, 0.7, mp.outputs['Vector'])
    r = m.ramp(n.outputs['Fac'], [(0.35, c1), (0.65, c2)])
    m.link(r.outputs['Color'], m.bsdf.inputs['Base Color']); m.set('Roughness', 0.95)
    m.bump(n.outputs['Fac'], 0.9, 0.1)
    if fog: m.fog(*fog)
    return m.m

# ---------------- procedural props ----------------
def displace(bm, amp, freq, seed, octaves=4, axis_scale=(1, 1, 1)):
    bm.normal_update(); off = Vector((seed * 13.1, seed * 7.7, seed * 3.3))
    for v in bm.verts:
        p = Vector((v.co.x * freq * axis_scale[0], v.co.y * freq * axis_scale[1], v.co.z * freq * axis_scale[2])) + off
        d = noise.fractal(p, 0.8, 2.0, octaves)
        v.co += v.normal * d * amp

def blob(bm_target, center, radius, seed, amp=0.35, freq=1.4, sub=3, squash=1.0):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=radius)
    for v in bm.verts: v.co.z *= squash
    displace(bm, radius * amp, freq / radius, seed)
    for v in bm.verts: v.co += Vector(center)
    me = bpy.data.meshes.new('tmp'); bm.to_mesh(me); bm.free(); bm_target.from_mesh(me); bpy.data.meshes.remove(me)

def cyl(bm_target, base, top, r0, r1, seg=10, seed=0, bark=0.06):
    bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg, radius1=r0, radius2=r1, depth=1.0)
    a = Vector(base); b = Vector(top); d = b - a; L = d.length
    rot = Vector((0, 0, 1)).rotation_difference(d.normalized())
    for v in bm.verts:
        v.co.z = (v.co.z + 0.5) * L
        if bark: v.co.x += noise.noise(Vector((v.co.x * 5 + seed, v.co.y * 5, v.co.z * 2))) * bark * r0; v.co.y += noise.noise(Vector((v.co.y * 5, v.co.z * 2 + seed, v.co.x))) * bark * r0
        v.co = rot @ v.co + a
    me = bpy.data.meshes.new('tmp'); bm.to_mesh(me); bm.free(); bm_target.from_mesh(me); bpy.data.meshes.remove(me)

def broadleaf(seed, h=4.0, mats=None, wide=1.0):
    """Returns (trunk_obj, canopy_obj) at origin, base at z=0."""
    rnd = random.Random(seed)
    bt = bmesh.new()
    cyl(bt, (0, 0, -0.3), (rnd.uniform(-.15, .15) * h, 0, h * 0.62), h * 0.055, h * 0.03, 10, seed)
    for k in range(3):
        a = rnd.uniform(0, 6.28); z = h * rnd.uniform(.38, .55)
        cyl(bt, (0, 0, z), (math.cos(a) * h * .25 * wide, math.sin(a) * h * .12, z + h * .22), h * 0.025, h * 0.01, 6, seed + k)
    t = mesh_obj('trunk', bt, mats[0] if mats else None)
    bc = bmesh.new()
    n = rnd.randint(5, 8)
    for k in range(n):
        a = k / n * 6.28 + rnd.uniform(-.3, .3); rr = h * rnd.uniform(.12, .26) * wide
        c = (math.cos(a) * rr, math.sin(a) * rr * .6, h * rnd.uniform(.62, .86))
        blob(bc, c, h * rnd.uniform(.17, .25) * (wide ** .5), seed * 10 + k, 0.38, 1.6, 3, 0.85)
    blob(bc, (0, 0, h * .84), h * .24 * (wide ** .5), seed * 10 + 9, 0.38, 1.6, 3, 0.85)
    c = mesh_obj('canopy', bc, mats[1] if mats else None)
    return t, c

def pine(seed, h=5.0, mats=None, snow=False):
    rnd = random.Random(seed)
    bt = bmesh.new(); cyl(bt, (0, 0, -0.3), (0, 0, h * 0.9), h * 0.035, h * 0.012, 8, seed)
    t = mesh_obj('ptrunk', bt, mats[0] if mats else None)
    bc = bmesh.new(); tiers = 6
    for k in range(tiers):
        f = k / (tiers - 1); z0 = h * (0.18 + f * 0.62); rad = h * (0.26 - f * 0.19) * rnd.uniform(.9, 1.1)
        bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=24, radius1=rad, radius2=0.0, depth=h * 0.3)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=2, use_grid_fill=True)
        for v in bm.verts:
            ang = math.atan2(v.co.y, v.co.x); rad_v = math.hypot(v.co.x, v.co.y)
            jag = 1 + 0.18 * math.sin(ang * 9 + seed + k) + 0.1 * noise.noise(Vector((v.co.x * 3, v.co.y * 3, seed + k)))
            v.co.x *= jag; v.co.y *= jag
            v.co.z += z0 + h * 0.15 - (rad_v / max(rad, 1e-3)) * h * 0.05
        displace(bm, rad * 0.12, 2.5 / rad, seed + k * 3)
        me = bpy.data.meshes.new('tmp'); bm.to_mesh(me); bm.free(); bc.from_mesh(me); bpy.data.meshes.remove(me)
    c = mesh_obj('pcanopy', bc, mats[1] if mats else None)
    return t, c

def bush(seed, r=0.8, mat=None):
    rnd = random.Random(seed); bc = bmesh.new()
    for k in range(rnd.randint(3, 5)):
        blob(bc, (rnd.uniform(-r, r) * .8, rnd.uniform(-r, r) * .3, r * rnd.uniform(.3, .6)), r * rnd.uniform(.45, .7), seed * 7 + k, 0.35, 1.5, 3, 0.8)
    return mesh_obj('bush', bc, mat)

def rock(seed, r=1.0, mat=None, squash=0.7, sub=4, amp=0.45):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    for v in bm.verts: v.co.z *= squash
    displace(bm, r * amp, 0.9 / r, seed, 6)
    return mesh_obj('rock', bm, mat)

def instance(src, loc, rot_z=0.0, scale=1.0):
    o = bpy.data.objects.new(src.name + '_i', src.data); link(o)
    o.location = loc; o.rotation_euler = (0, 0, rot_z); o.scale = (scale, scale, scale)
    return o

def hide(o):
    o.hide_render = True; o.hide_viewport = True

def render(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('WROTE', path)
