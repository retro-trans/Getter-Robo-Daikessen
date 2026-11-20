"""English versions of the small text sprites (4/8 bpp TIMs on a transparent background):
flight minigame titles, HUD messages, result plates and stamps, seat-status icons.

    py311 tools/gfx_sprites.py      -> work/translation/en/gfx/<vfs pac>/<entry>
                                       + preview work/ui/gfx_sheets/en_sprites.png

Each sprite keeps its size, CLUT and VRAM position. Glyphs are drawn without
anti-aliasing and coloured with the sprite's own palette: the non-transparent colours are
sorted by brightness and used as a vertical ramp (white at the top of the glyphs), the
darkest one as outline / shadow. `rect` limits the redrawn area (frames and hazard stripes
outside it are kept); `bg` = 'clear' (transparent) or 'keep' (only glyph pixels replaced).
"""
import glob
import os
import struct

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNPACKED = os.path.join(ROOT, 'work', 'source', 'unpacked')
OUT = os.path.join(ROOT, 'work', 'translation', 'en', 'gfx')
IMPACT = r'C:\Windows\Fonts\impact.ttf'
COND = r'C:\Windows\Fonts\FRAMDCN.TTF'
ARIALBD = r'C:\Windows\Fonts\arialbd.ttf'

# 3x5 capitals for very small plates
TINY = {
    'A': '010101111101101', 'B': '110101110101110', 'C': '011100100100011', 'D': '110101101101110',
    'E': '111100110100111', 'F': '111100110100100', 'G': '011100101101011', 'H': '101101111101101',
    'I': '111010010010111', 'J': '001001001101010', 'K': '101101110101101', 'L': '100100100100111',
    'M': '101111111101101', 'N': '110101101101101', 'O': '010101101101010', 'P': '110101110100100',
    'Q': '010101101110011', 'R': '110101110101101', 'S': '011100010001110', 'T': '111010010010010',
    'U': '101101101101111', 'V': '101101101101010', 'W': '101101111111101', 'X': '101101010101101',
    'Y': '101101010010010', 'Z': '111001010100111', '0': '111101101101111', '1': '010110010010111',
    '2': '110001010100111', '3': '110001010001110', '4': '101101111001001', '5': '111100110001110',
    '6': '011100110101010', '7': '111001010010010', '8': '010101010101010', '9': '010101011001110',
    '.': '000000000000010', ' ': '000000000000000', '-': '000000111000000', '!': '010010010000010',
    'o': '000000010101010',
}

# name: (pac, entry glob, spec)
SPRITES = {
    # flight minigame title screen
    'TITLE_00': ('flight/title.pac', '*TITLE_00.TIM', dict(lines=['PROTOTYPE', 'COMBINATION TRAINING'], font=IMPACT)),
    'TITLE_01': ('flight/title.pac', '*TITLE_01.TIM', dict(lines=['PROTOTYPE', 'COMBINATION TEST'], font=IMPACT)),
    'SOUSA': ('flight/title.pac', '*SOUSA.TIM', dict(lines=['Controls'], font=COND)),
    'SETTEI': ('flight/title.pac', '*SETTEI.TIM', dict(lines=['Config'], font=COND)),
    'ENSHUCHI': ('flight/title.pac', '*ENSHUCHI.TIM', dict(lines=['Stage'], font=COND)),
    'JYOUKYOU': ('flight/title.pac', '*JYOUKYOU.TIM', dict(lines=['Info'], font=COND)),
    # flight HUD
    'KEIKOKU': ('flight/flight.pac', '*KEIKOKU.TIM', dict(lines=['TOO FAR!'], font=IMPACT, rect=(0, 6, 80, 26))),
    'TOPPU': ('flight/flight.pac', '*TOPPU.TIM', dict(lines=['GUST ALERT'], font=IMPACT, rect=(0, 6, 80, 26))),
    'CORSEOUT': ('flight/flight.pac', '*CORSEOUT.TIM', dict(lines=['OFF COURSE'], font=IMPACT, outline=2)),
    'TIMEOVER': ('flight/flight.pac', '*TIMEOVER.TIM', dict(lines=['TIME UP'], font=IMPACT, outline=2)),
    'SEIKOU': ('flight/flight.pac', '*SEIKOU.TIM', dict(lines=['COMBINED!!'], font=IMPACT, outline=2)),
    'SIPPAI': ('flight/flight.pac', '*SIPPAI.TIM', dict(lines=['FAILED!!'], font=IMPACT, outline=2)),
    'GATTAI': ('flight/flight.pac', '*GATTAI.TIM', dict(lines=['COMBINE'], font=IMPACT, rect=(3, 3, 61, 29))),
    'HENKEITU': ('flight/flight.pac', '*HENKEITU.TIM', dict(lines=['CHANGING'], font=IMPACT, rect=(3, 3, 93, 29))),
    '1GOUKI': ('flight/flight.pac', '*1GOUKI.TIM', dict(tiny='UNIT 1')),
    '2GOUKI': ('flight/flight.pac', '*2GOUKI.TIM', dict(tiny='UNIT 2')),
    '3GOUKI': ('flight/flight.pac', '*3GOUKI.TIM', dict(tiny='UNIT 3')),
    'TIMEROGO': ('flight/flight.pac', '*TIMEROGO.TIM', dict(tiny_top='PROTOTYPE SHIN GETTER ROBO',
                                                            lines=['COMBINE TIME LIMIT'], font=IMPACT,
                                                            rect=(0, 8, 128, 24))),
    # flight results
    'SING': ('flight/result.pac', '*SING.TIM', dict(lines=['Shin Getter Robo G'], font=ARIALBD, shadow=True)),
    'G': ('flight/result.pac', '*_G.TIM', dict(lines=['Getter Robo G'], font=ARIALBD, shadow=True)),
    'GETTER': ('flight/result.pac', '*GETTER.TIM', dict(lines=['Getter Robo'], font=ARIALBD, shadow=True)),
    'SIN': ('flight/result.pac', '*SIN.TIM', dict(lines=['Shin Getter Robo'], font=ARIALBD, shadow=True)),
    'ZANGO': ('flight/result.pac', '*ZANGO.TIM', dict(lines=['Getter Robo Zan', 'and', 'Getter Robo Go'],
                                                       font=ARIALBD, shadow=True, sizes=(1, 0.6, 1))),
    'NINKA': ('flight/result.pac', '*NINKA.TIM', dict(lines=['PILOT LICENSED'], font=IMPACT, stamp=True)),
    'SAITAN': ('flight/result.pac', '*SAITAN.TIM', dict(lines=['NEW RECORD!'], font=IMPACT, stamp=True)),
    'DORYOKU': ('flight/result.pac', '*DORYOKU.TIM', dict(lines=['TRY HARDER!'], font=IMPACT, stamp=True, frame=True)),
    'SUKOSI': ('flight/result.pac', '*SUKOSI.TIM', dict(lines=['ALMOST!'], font=IMPACT, stamp=True, frame=True)),
    'GOUKAKU': ('flight/result.pac', '*GOUKAKU.TIM', dict(lines=['PASS'], font=IMPACT, stamp=True, frame=True, angle=12)),
    'FUGOU': ('flight/result.pac', '*FUGOU.TIM', dict(lines=['FAIL'], font=IMPACT, stamp=True, frame=True, angle=-8)),
    # battle HUD (prog00/effect.pac)
    'DAMAGE': ('prog00/effect.pac', '*DAMAGE.TIM', dict(tiny='DAMAGE', outline=1)),
    # unit select: seat status
    'EMPTY': ('entry/change.pac', '*EMPTY.TIM', dict(lines=['EMPTY'], font=IMPACT, bg='keep_box')),
    'FUKA': ('entry/change.pac', '*FUKA.TIM', dict(lines=['N/A'], font=IMPACT, bg='keep_box')),
}


# ---------------------------------------------------------------- TIM
def tim_read(path):
    d = open(path, 'rb').read()
    flags = struct.unpack_from('<I', d, 4)[0]
    bpp = flags & 3
    cl, cx, cy, cw, ch = struct.unpack_from('<IHHHH', d, 8)
    n = 16 if bpp == 0 else 256
    clut = np.array(struct.unpack_from('<%dH' % (cw * ch), d, 20)[:n], dtype=np.int32)
    p = 8 + cl
    il, ix, iy, iw, ih = struct.unpack_from('<IHHHH', d, p)
    px = np.frombuffer(d, np.uint8, iw * 2 * ih, p + 12)
    if bpp == 0:
        idx = np.stack([px & 15, px >> 4], -1).reshape(ih, iw * 4)
    else:
        idx = px.reshape(ih, iw * 2)
    return {'raw': d, 'bpp': bpp, 'clut': clut, 'idx': idx.astype(np.int32), 'off': p + 12}


def tim_write(t, idx):
    d = bytearray(t['raw'])
    if t['bpp'] == 0:
        b = (idx[:, 0::2] | (idx[:, 1::2] << 4)).astype(np.uint8)
    else:
        b = idx.astype(np.uint8)
    d[t['off']:t['off'] + b.size] = b.tobytes()
    return bytes(d)


def rgb_of(clut):
    return np.stack([(clut & 31) << 3, ((clut >> 5) & 31) << 3, ((clut >> 10) & 31) << 3], -1).astype(np.uint8)


# ---------------------------------------------------------------- drawing
def text_mask(lines, font, box_w, box_h, sizes=None, max_size=200):
    """Binary mask (box_h, box_w) with the lines centred, the largest size that fits."""
    sizes = sizes or [1] * len(lines)
    best = None
    for s in range(min(max_size, box_h * 2), 5, -1):
        im = Image.new('L', (box_w, box_h), 0)
        d = ImageDraw.Draw(im)
        d.fontmode = '1'
        fs = [ImageFont.truetype(font, max(6, int(s * k))) for k in sizes]
        bbs = [d.textbbox((0, 0), ln, font=f) for ln, f in zip(lines, fs)]
        ws = [b[2] - b[0] for b in bbs]
        hs = [b[3] - b[1] for b in bbs]
        gap = max(1, s // 10)
        tot = sum(hs) + gap * (len(lines) - 1)
        if max(ws) <= box_w - 2 and tot <= box_h - 2:
            y = (box_h - tot) // 2
            for ln, f, b, w, h in zip(lines, fs, bbs, ws, hs):
                d.text(((box_w - w) // 2 - b[0], y - b[1]), ln, font=f, fill=255)
                y += h + gap
            best = np.array(im) > 127
            break
    return best


def tiny_mask(text, box_w, box_h):
    w = len(text) * 4 - 1
    m = np.zeros((box_h, box_w), bool)
    x0 = max(0, (box_w - w) // 2)
    y0 = max(0, (box_h - 5) // 2)
    for i, ch in enumerate(text):
        g = TINY[ch]
        for r in range(5):
            for c in range(3):
                if g[r * 3 + c] == '1' and x0 + i * 4 + c < box_w:
                    m[y0 + r, x0 + i * 4 + c] = True
    return m


def ramp(clut):
    """(transparent index, indices sorted bright -> dark)"""
    tr = [i for i in range(len(clut)) if clut[i] == 0]
    tr = tr[0] if tr else None
    rgb = rgb_of(clut).astype(np.int32)
    lum = rgb @ np.array([3, 6, 1])
    solid = [i for i in range(len(clut)) if clut[i] != 0]
    solid.sort(key=lambda i: -lum[i])
    return tr, solid


def colour(mask, solid, outline, shadow, flat=None):
    """index image (-1 = untouched) for glyph mask: vertical ramp (or one `flat` colour),
    outline, shadow."""
    h, w = mask.shape
    out = np.full((h, w), -1, np.int32)
    ys = np.nonzero(mask.any(1))[0]
    if len(ys) == 0:
        return out
    top, bot = ys.min(), ys.max()
    lights = solid[:max(2, len(solid) - 3)]
    dark = solid[-1]
    if shadow:
        sh = np.zeros_like(mask)
        sh[1:, 1:] = mask[:-1, :-1]
        sh2 = np.zeros_like(mask)
        sh2[2:, 2:] = mask[:-2, :-2]
        out[(sh | sh2) & ~mask] = dark
    if outline:
        k = np.ones((2 * outline + 1, 2 * outline + 1), np.uint8)
        ol = cv2.dilate(mask.astype(np.uint8), k).astype(bool) & ~mask
        out[ol] = dark
    for y in range(top, bot + 1):
        t = (y - top) / max(1, bot - top)
        out[y][mask[y]] = flat if flat is not None else lights[min(len(lights) - 1, int(t * 0.45 * len(lights)))]
    return out


def make(name, pac, pat, spec):
    path = glob.glob(os.path.join(UNPACKED, pac, pat))
    assert len(path) == 1, (name, path)
    path = path[0]
    t = tim_read(path)
    idx = t['idx'].copy()
    H, W = idx.shape
    tr, solid = ramp(t['clut'])
    x0, y0, x1, y1 = spec.get('rect', (0, 0, W, H))
    bgmode = spec.get('bg', 'clear')
    if bgmode == 'keep_box':
        # opaque icon: keep its border, fill the inside with its background colour
        inner = idx[3:H - 3, 3:W - 3]
        vals, cnt = np.unique(inner, return_counts=True)
        bgc = vals[cnt.argmax()]
        rgbs = rgb_of(t['clut']).astype(np.int32)
        sat = rgbs.max(1) - rgbs.min(1)
        present = [i for i in np.unique(inner) if i != bgc and t['clut'][i] != 0]
        glyph = max(present, key=lambda i: sat[i])
        idx[2:H - 2, 2:W - 2] = bgc
        x0, y0, x1, y1 = 2, 2, W - 2, H - 2
        m = text_mask(spec['lines'], spec['font'], x1 - x0 - 2, y1 - y0 - 2)
        m = np.pad(m, 1)
        sub = colour(m, solid, 0, False, flat=glyph)
        region = idx[y0:y1, x0:x1]
        region[sub >= 0] = sub[sub >= 0]
        return tim_write(t, idx), t, idx
    elif spec.get('stamp'):
        idx[:, :] = tr
    else:
        idx[y0:y1, x0:x1] = tr
    bw, bh = x1 - x0, y1 - y0
    if 'tiny' in spec:
        m = tiny_mask(spec['tiny'], bw, bh)
        sub = colour(m, solid, spec.get('outline', 0), False, flat=solid[0])
    else:
        if 'tiny_top' in spec:
            idx[0:8, :] = tr
            tm = tiny_mask(spec['tiny_top'], W, 7)
            sub0 = colour(tm, solid, 0, False, flat=solid[0])
            region = idx[0:7, :]
            region[sub0 >= 0] = sub0[sub0 >= 0]
        if spec.get('stamp'):
            m = stamp(spec, W, H)
            idx[:, :] = np.where(m == 1, solid[-1], np.where(m == 2, solid[0], np.where(m == 3, solid[-2], tr)))
            return tim_write(t, idx), t, idx
        pad = spec.get('outline', 1) + (2 if spec.get('shadow') else 0)
        m = text_mask(spec['lines'], spec['font'], bw - 2 * pad, bh - 2 * pad, spec.get('sizes'))
        m = np.pad(m, pad)
        sub = colour(m, solid, spec.get('outline', 1), spec.get('shadow', False))
    region = idx[y0:y1, x0:x1]
    region[sub >= 0] = sub[sub >= 0]
    return tim_write(t, idx), t, idx


def stamp(spec, W, H):
    """1 = dark ink (outline), 2 = white text / frame, 3 = speckle; 0 = transparent."""
    rng = np.random.default_rng(len(spec['lines'][0]) * 7 + W)
    big = 3
    cw, ch = W * big, H * big
    im = Image.new('L', (cw, ch), 0)
    d = ImageDraw.Draw(im)
    ang = spec.get('angle', 0)
    m = 10 * big if ang else 3 * big
    if spec.get('frame'):
        d.rectangle((m, m, cw - m, ch - m), outline=2, width=2 * big)
    tm = text_mask(spec['lines'], spec['font'], cw - 2 * m - 16 * big, ch - 2 * m - 14 * big)
    tm = np.pad(tm, ((m + 7 * big, m + 7 * big), (m + 8 * big, m + 8 * big)))[:ch, :cw]
    a = np.array(im)
    a[tm] = 2
    im = Image.fromarray(a)
    if ang:
        im = im.rotate(ang, resample=Image.NEAREST, expand=False)
    a = np.array(im.resize((W, H), Image.NEAREST))
    white = a == 2
    ol = cv2.dilate(white.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool) & ~white
    a[ol] = 1
    noise = rng.random(a.shape)
    inside = np.zeros_like(white)
    ys, xs = np.nonzero(white)
    inside[ys.min():ys.max() + 1, xs.min():xs.max() + 1] = True
    a[(a == 0) & inside & (noise < 0.22)] = 3
    a[(a == 0) & ~inside & (noise < 0.03)] = 3
    a[white & (noise < 0.06)] = 1
    return a


def preview(items):
    tiles = []
    for name, t, idx in items:
        rgb = rgb_of(t['clut'])
        for which in (t['idx'], idx):
            a = rgb[which].copy()
            a[t['clut'][which] == 0] = (255, 0, 255)
            im = Image.fromarray(a).resize((which.shape[1] * 2, which.shape[0] * 2), Image.NEAREST)
            tiles.append(im)
    W = 1100
    x = y = rowh = 0
    pos = []
    for k in range(0, len(tiles), 2):
        a, b = tiles[k], tiles[k + 1]
        w = a.width + b.width + 12
        if x + w > W:
            x, y, rowh = 0, y + rowh + 8, 0
        pos.append((x, y, a, b))
        x += w
        rowh = max(rowh, a.height)
    sh = Image.new('RGB', (W, y + rowh + 8), (30, 30, 60))
    for x, y, a, b in pos:
        sh.paste(a, (x, y))
        sh.paste(b, (x + a.width + 4, y))
    p = os.path.join(ROOT, 'work', 'ui', 'gfx_sheets', 'en_sprites.png')
    sh.save(p)
    return p


def main():
    items = []
    for name, (pac, pat, spec) in SPRITES.items():
        data, t, idx = make(name, pac, pat, spec)
        fn = os.path.basename(glob.glob(os.path.join(UNPACKED, pac, pat))[0])
        p = os.path.join(OUT, pac, fn)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'wb').write(data)
        items.append((name, t, idx))
    print(len(items), 'sprites; preview', preview(items))


if __name__ == '__main__':
    main()
