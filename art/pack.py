# Packs rendered art into public/art/*.webp and writes art/map.json (sprite + texture rects, anchors).
import os, json, math, re
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out'); PUB = os.path.join(HERE, '..', 'public', 'art'); os.makedirs(PUB, exist_ok=True)

# must match sprites.py SPR: name -> (frames, wl, hl, bbox, pitch)
SPR = {
    'beetle': (2, 20, 14, (-1.1, 1.9, -.3, 1.8), 12), 'hedgehog': (2, 22, 15, (-1.3, 1.5, -.2, 1.75), 10),
    'bee': (2, 18, 16, (-1.3, 1.1, -.8, 1.3), 8), 'bird': (3, 28, 22, (-1.45, 1.4, -1.0, 1.4), 8),
    'icicle': (1, 8, 26, (-.4, .4, -2.4, .2), 0), 'gem': (1, 12, 12, (-.62, .62, -.62, .62), 0),
    'tree0': (2, 56, 66, (-2.8, 2.8, -.1, 6.5), 6), 'tree3': (1, 52, 58, (-2.6, 2.6, -.1, 5.7), 6),
    'pine2': (2, 34, 60, (-1.7, 1.7, -.1, 5.9), 6),
    'bush0': (2, 26, 15, (-1.3, 1.3, -.1, 1.4), 10), 'bush1': (1, 26, 15, (-1.3, 1.3, -.1, 1.4), 10),
    'bush3': (1, 26, 15, (-1.3, 1.3, -.1, 1.4), 10),
    'rock0': (1, 22, 13, (-1.1, 1.1, -.2, 1.1), 14), 'rock2': (1, 22, 13, (-1.1, 1.1, -.2, 1.1), 14),
    'shroom': (1, 16, 14, (-.8, .8, -.05, 1.35), 10),
}
SCALE = 0.75  # store sprites at 3 px per logical px (renders are 4)

def anchor(wl, hl, bbox, pitch):
    x0, x1, z0, z1 = bbox; bw, bh = x1 - x0, z1 - z0; asp = wl / hl
    sc = max(bw, bh * asp) if asp >= 1 else max(bh, bw / asp)
    fw = sc if asp >= 1 else sc * asp; fh = fw / asp
    cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
    u = -cx; v = -cz * math.cos(math.radians(pitch))
    return round((u / fw + .5) * wl, 2), round((.5 - v / fh) * hl, 2)

def shelf(items, width):
    x = y = rowh = 0; pos = []
    for w, h in items:
        if x + w > width: x = 0; y += rowh + 2; rowh = 0
        pos.append((x, y)); x += w + 2; rowh = max(rowh, h)
    return pos, y + rowh

# ---- sprites
ims, meta = [], []
for name, (fr, wl, hl, bbox, pitch) in SPR.items():
    ax, ay = anchor(wl, hl, bbox, pitch)
    for f in range(fr):
        im = Image.open(os.path.join(OUT, 'spr', '%s%d.png' % (name, f))).convert('RGBA')
        im = im.resize((max(1, round(im.width * SCALE)), max(1, round(im.height * SCALE))), Image.LANCZOS)
        ims.append(im); meta.append((name, wl, hl, ax, ay))
order = sorted(range(len(ims)), key=lambda i: -ims[i].height)
pos, H = shelf([ims[i].size for i in order], 1024)
atlas = Image.new('RGBA', (1024, H), (0, 0, 0, 0)); sprites = {}
for (px, py), i in zip(pos, order): atlas.alpha_composite(ims[i], (px, py))
P = dict(zip(order, pos))
for i, (name, wl, hl, ax, ay) in enumerate(meta):
    im = ims[i]; px, py = P[i]
    sprites.setdefault(name, []).append([px, py, im.width, im.height, wl, hl, ax, ay])
atlas.save(os.path.join(PUB, 'atlas.webp'), 'WEBP', quality=90, method=6)

# ---- textures (256 tiles) + fringes (256x64)
tx = ['soil0', 'soil1', 'soil3', 'rock2', 'cave', 'wood', 'stone']
fr = ['fringe_grass0', 'fringe_grass1', 'fringe_grass3', 'fringe_snow']
tim = [Image.open(os.path.join(OUT, 'tex', n + '.png')).convert('RGBA') for n in tx + fr]
for i, n in enumerate(tx): tim[i] = tim[i].convert('RGB').convert('RGBA')
pos, H = shelf([t.size for t in tim], 1024)
tex = Image.new('RGBA', (1024, H), (0, 0, 0, 0)); trect = {}
for n, t, (px, py) in zip(tx + fr, tim, pos):
    tex.alpha_composite(t, (px, py)); trect[n.replace('fringe_', 'f_')] = [px, py, t.width, t.height]
tex.save(os.path.join(PUB, 'tex.webp'), 'WEBP', quality=88, method=6)

# ---- backgrounds
sizes = {}
for w in range(4):
    for l in ('far', 'mid'):
        im = Image.open(os.path.join(OUT, 'bg%d_%s.png' % (w, l))).convert('RGBA')
        im.save(os.path.join(PUB, 'bg%d_%s.webp' % (w, l)), 'WEBP', quality=82, method=6)
        sizes['%d%s' % (w, l)] = [im.width // 2, im.height // 2]
json.dump({'spr': sprites, 'tex': trect, 'bg': sizes}, open(os.path.join(HERE, 'map.json'), 'w'), separators=(',', ':'))
tot = sum(os.path.getsize(os.path.join(PUB, f)) for f in os.listdir(PUB))
print('packed', len(ims), 'sprite frames; atlas', atlas.size, 'tex', tex.size, 'total KB', tot // 1024)
