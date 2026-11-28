"""English versions of the graphics with Japanese text that sit on artwork
(chapter title cards mapsys/mtNN.pac, Game Over mapsys/gameover.pac).

Needs OpenCV + numpy + Pillow (the 64-bit Python 3.11 here):
    py311 tools/gfx_cards.py            -> work/translation/en/gfx/<vfs pac path>/<entry file>
                                           + preview sheet work/ui/gfx_sheets/en_cards.png
The Japanese text is found (white or red glyphs with a dark outline inside a text box),
removed with OpenCV inpainting, the English text drawn in the same style, and the result
mapped back to the card's own 256-colour CLUT (palette and VRAM position unchanged), so
tools/build.py only has to repack the TIM (tools/gfx.py).
"""
import os
import struct

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UNPACKED = os.path.join(ROOT, 'work', 'source', 'unpacked')
OUT = os.path.join(ROOT, 'work', 'translation', 'en', 'gfx')
FONT = r'C:\Windows\Fonts\FRAMDCN.TTF'          # Franklin Gothic Medium Condensed
FONT_BIG = r'C:\Windows\Fonts\impact.ttf'

# card: (episode label, title lines). Titles follow the briefing translations (data.json).
CARDS = {
    'mt01': ('Episode 1', ['"Launch! Getter Robo"']),
    'mt02': ('Episode 2', ['"The Time Has Come!', 'We Are the', 'Dinosaur Empire"']),
    'mt03': ('Episode 3', ['"Getter', 'vs.', 'Getter"']),
    'mt04': ('Episode 4', ['"Operation:', 'Destroy Getter Robo"']),
    'mt05': ('Episode 5', ['"New Power,', 'New Enemy"']),
    'mt06': ('Episode 6', ['"Save the Institutes!', '(Part 1)"']),
    'mt06b': ('Episode 6', ['"Save the Institutes!', '(Part 2)"']),
    'mt07': ('Episode 7', ['"First', 'Contact"']),
    'mt08': ('Episode 8', ['"Texas, the Large', 'Mobile Battleship"']),
    'mt09': ('Episode 9', ['"Shin Getter Robo"']),
    'mt10': ('Episode 10', ['"The Terrifying', 'Germ Missiles"']),
    'mt11': ('Episode 11', ['"The Last Day of', 'the Hyakki Empire"']),
    'mt12': ('Episode 12', ['"Enter', 'Professor Lando!"']),
    'mt13': ('Episode 13', ['"Brother and Sister"']),
    'mt14': ('Episode 14', ['"The Black Getter"']),
    'mt15a': ('Episode 15', ['"The Terrifying', 'Giant Tornado"']),
    'mt15b': ('Episode 15', ['"Super Weapon Volga"']),
    'mt15c': ('Episode 15', ['"The Revived Emperor"']),
    'mt16a': ('Episode 16', ['"The Terrifying', 'Giant Tornado"']),
    'mt16b': ('Episode 16', ['"Super Weapon Volga"']),
    'mt16c': ('Episode 16', ['"The Revived Emperor"']),
    'mt17a': ('Episode 17', ['"The Terrifying', 'Giant Tornado"']),
    'mt17b': ('Episode 17', ['"Super Weapon Volga"']),
    'mt17c': ('Episode 17', ['"The Revived Emperor"']),
    'mt18': ('Episode 18', ['"Texas', 'vs.', 'Dragon Turtle"']),
    'mt19': ('Episode 19', ['"Final Battle at', 'Vega Zone"']),
    'mt20': ('Episode 20', ['"Into Space"']),
    'mt21': ('Final Episode', ['"The Great Battle!"']),
}


# ---------------------------------------------------------------- TIM (8 bpp + CLUT)
def tim_read(d):
    flags = struct.unpack_from('<I', d, 4)[0]
    assert struct.unpack_from('<I', d, 0)[0] == 0x10 and flags & 3 == 1 and flags & 8
    cl, cx, cy, cw, ch = struct.unpack_from('<IHHHH', d, 8)
    clut = np.array(struct.unpack_from('<%dH' % (cw * ch), d, 20), dtype=np.uint16)[:256]
    p = 8 + cl
    il, ix, iy, iw, ih = struct.unpack_from('<IHHHH', d, p)
    w = iw * 2
    idx = np.frombuffer(d, dtype=np.uint8, count=w * ih, offset=p + 12).reshape(ih, w).copy()
    return {'clut': clut, 'idx': idx, 'pix_off': p + 12}


def clut_rgb(clut):
    c = clut.astype(np.int32)
    return np.stack([(c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3], -1).astype(np.uint8)


def tim_write(d, t, idx):
    d = bytearray(d)
    d[t['pix_off']:t['pix_off'] + idx.size] = idx.astype(np.uint8).tobytes()
    return bytes(d)


def quantize(rgb, clut):
    """Nearest CLUT entry per pixel (colour 0x0000 = transparent is avoided)."""
    pal = clut_rgb(clut).astype(np.int32)
    ok = np.nonzero(clut != 0)[0]
    flat = rgb.reshape(-1, 3).astype(np.int32)
    best = np.zeros(len(flat), dtype=np.int32)
    bestd = np.full(len(flat), 1 << 30, dtype=np.int64)
    for i in ok:
        dd = ((flat - pal[i]) ** 2 * np.array([3, 4, 2])).sum(1)
        m = dd < bestd
        best[m] = i
        bestd[m] = dd[m]
    return best.reshape(rgb.shape[:2])


# ---------------------------------------------------------------- text removal
def text_mask(rgb, kind):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    if kind == 'red':
        glyph = (((hsv[..., 0] < 8) | (hsv[..., 0] > 170)) & (hsv[..., 1] > 150) & (hsv[..., 2] > 150))
    else:
        glyph = (rgb.min(2) >= 205) & (hsv[..., 1] < 50)
    glyph = glyph.astype(np.uint8)
    dark = (rgb.max(2) < 70).astype(np.uint8)
    # glyph pixels count as text where a dark outline is close by on several sides
    near_dark = cv2.dilate(dark, np.ones((7, 7), np.uint8))
    g = glyph & near_dark
    # keep blobs that look like lines of text: merge glyphs horizontally, drop small blobs
    merged = cv2.morphologyEx(g, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (15, 9)))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(merged)
    keep = np.zeros_like(g)
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        dens = g[lab == i].sum()
        if w >= 24 and 10 <= h <= 160 and dens >= 60:
            keep[lab == i] = 1
    g = g & keep
    # glyph + its outline (+ soft shadow)
    return cv2.dilate(g, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))


# ---------------------------------------------------------------- text drawing
def draw_lines(img, x, y, lines, font, fill, outline=(16, 16, 16), stroke=3, gap=0, right=None):
    """lines: [(text, size, align)]; align 'l' or 'r' (r: right edge at `right`)."""
    d = ImageDraw.Draw(img)
    for text, size, align in lines:
        f = ImageFont.truetype(font, size)
        bb = d.textbbox((0, 0), text, font=f, stroke_width=stroke)
        w = bb[2] - bb[0]
        xx = x if align == 'l' else right - w if align == 'r' else (x + right - w) // 2
        # drop shadow, then the outlined glyphs
        d.text((xx + 2 - bb[0], y + 2 - bb[1]), text, font=f, fill=(0, 0, 0), stroke_width=stroke, stroke_fill=(0, 0, 0))
        d.text((xx - bb[0], y - bb[1]), text, font=f, fill=fill, stroke_width=stroke, stroke_fill=outline)
        y += bb[3] - bb[1] + gap
    return y


def fit_size(lines, size, maxw, font):
    d = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    while size > 12:
        f = ImageFont.truetype(font, size)
        if all(d.textbbox((0, 0), t, font=f, stroke_width=3)[2] <= maxw for t in lines):
            return size
        size -= 1
    return size


def edit_rgb(rgb, label, title, min_h=96):
    """Remove the white title text of an RGB image and draw `label` (may be None) + `title`."""
    mask = text_mask(rgb, 'white')
    ys, xs = np.nonzero(mask)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
    clean = cv2.inpaint(np.ascontiguousarray(rgb), mask * 255, 6, cv2.INPAINT_TELEA)
    img = Image.fromarray(clean)
    title = [x.replace('"', '“', 1) if i == 0 else x for i, x in enumerate(title)]
    title[-1] = title[-1][::-1].replace('"', '”', 1)[::-1]
    H, W = rgb.shape[:2]
    left = max(8, x0)
    right = min(W - 8, max(x1, left + 200) if len(title) > 1 else W - 8)
    centre = label is None and len(title) == 1
    if centre:
        left, right = 12, W - 12
    d = ImageDraw.Draw(img)

    def block(sz):
        f = ImageFont.truetype(FONT, sz)
        bbs = [d.textbbox((0, 0), s_, font=f, stroke_width=3) for s_ in title]
        return max(b[2] for b in bbs), sum(b[3] - b[1] + 4 for b in bbs)
    lab = 24
    lab_h = d.textbbox((0, 0), label, font=ImageFont.truetype(FONT, lab), stroke_width=3)[3] + 4 if label else 0
    sz = 48
    while sz > 16:
        bw, bh = block(sz)
        if bw <= right - left and lab_h + bh <= max(y1 - y0 + 30, min_h) and bw <= W - 16:
            break
        sz -= 1
    bw, bh = block(sz)
    lines = [(label, lab, 'l')] if label else []
    n = len(title)
    for i, s_ in enumerate(title):
        lines.append((s_, sz, 'c' if centre else 'l' if i == 0 or n == 1 else 'r' if i == n - 1 else 'c'))
    ytop = int(max(6, min(H - lab_h - bh - 6, (y0 + y1) / 2 - (lab_h + bh) / 2)))
    draw_lines(img, left, ytop, lines, FONT, (255, 255, 255), gap=4,
               right=right if centre else max(left + bw, right))
    return np.array(img)


def make_card(name, path):
    raw = open(path, 'rb').read()
    t = tim_read(raw)
    rgb = clut_rgb(t['clut'])[t['idx']]
    label, title = CARDS[name]
    out = edit_rgb(rgb, label, title)
    return tim_write(raw, t, quantize(out, t['clut'])), out, rgb


# "Next episode" previews (flight/annoNN.pac): YOKOKU = 次回予告 panel; the last panel of each
# pac carries the episode title. Images are 320 wide, stored as a 256 + 64 pixel TIM pair.
ANNO_TITLE = {'06': 'mt06', '06a': 'mt06b', '06b': 'mt06b', '07a': 'mt07', '07b': 'mt07',
              '15': 'mt15a', '16': 'mt16b', '17': 'mt17c'}


def split_pair(dirpath, stem):
    lf = [f for f in os.listdir(dirpath) if f.endswith('_%sL.TIM' % stem)][0]
    rf = [f for f in os.listdir(dirpath) if f.endswith('_%sR.TIM' % stem)][0]
    lr, rr = open(os.path.join(dirpath, lf), 'rb').read(), open(os.path.join(dirpath, rf), 'rb').read()
    lt, rt = tim_read(lr), tim_read(rr)
    rgb = np.concatenate([clut_rgb(lt['clut'])[lt['idx']], clut_rgb(rt['clut'])[rt['idx']]], 1)
    return (lf, lr, lt), (rf, rr, rt), rgb


def join_back(pair_l, pair_r, out):
    (lf, lr, lt), (rf, rr, rt) = pair_l, pair_r
    wl = lt['idx'].shape[1]
    return ((lf, tim_write(lr, lt, quantize(out[:, :wl], lt['clut']))),
            (rf, tim_write(rr, rt, quantize(out[:, wl:], rt['clut']))))


def make_annos(previews):
    root = os.path.join(UNPACKED, 'flight')
    yokoku = None
    for pacn in sorted(f for f in os.listdir(root) if f.startswith('anno')):
        d = os.path.join(root, pacn)
        nn = pacn[4:-4]
        # 次回予告 panel (identical in every pac: edit once, reuse when the source matches)
        l, r, rgb = split_pair(d, 'YOKOKU')
        if yokoku is None or not np.array_equal(yokoku[0], rgb):
            yokoku = (rgb, edit_rgb(rgb, None, ['NEXT EPISODE'], min_h=40))
            previews.append((pacn + ' YOKOKU', rgb, yokoku[1]))
        for fn, data in join_back(l, r, yokoku[1]):
            save('flight/' + pacn, fn, data)
        # title panel = the last L/R pair (8 bpp)
        stems = sorted({f.split('_', 2)[2][:-5] for f in os.listdir(d) if f.endswith('L.TIM') and 'YOKOKU' not in f})
        last = stems[-1]
        l, r, rgb = split_pair(d, last)
        title = CARDS[ANNO_TITLE.get(nn, 'mt' + nn)][1]
        out = edit_rgb(rgb, None, title, min_h=72)
        for fn, data in join_back(l, r, out):
            save('flight/' + pacn, fn, data)
        previews.append((pacn + ' ' + last, rgb, out))


def make_gameover(path):
    raw = open(path, 'rb').read()
    t = tim_read(raw)
    rgb = clut_rgb(t['clut'])[t['idx']]
    mask = text_mask(rgb, 'red')
    ys, xs = np.nonzero(mask)
    y0, y1 = ys.min(), ys.max()
    clean = cv2.inpaint(np.ascontiguousarray(rgb), mask * 255, 6, cv2.INPAINT_TELEA)
    img = Image.fromarray(clean)
    W = rgb.shape[1]
    f = ImageFont.truetype(FONT_BIG, 44)
    d = ImageDraw.Draw(img)
    bb = d.textbbox((0, 0), 'GAME OVER', font=f, stroke_width=3)
    x = (W - (bb[2] - bb[0])) // 2
    y = int((y0 + y1) / 2 - (bb[3] - bb[1]) / 2)
    draw_lines(img, x, y, [('GAME OVER', 44, 'l')], FONT_BIG, (216, 24, 32), outline=(40, 0, 0))
    out = np.array(img)
    return tim_write(raw, t, quantize(out, t['clut'])), out, rgb


def save(vfs_pac, entry, data):
    p = os.path.join(OUT, vfs_pac, entry)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(data)


def main():
    previews = []
    for name in CARDS:
        d = os.path.join(UNPACKED, 'mapsys', name + '.pac')
        fn = [f for f in os.listdir(d) if f.upper().endswith('.TIM')][0]
        data, out, src = make_card(name, os.path.join(d, fn))
        save('mapsys/%s.pac' % name, fn, data)
        previews.append((name, src, out))
    d = os.path.join(UNPACKED, 'mapsys', 'gameover.pac')
    fn = [f for f in os.listdir(d) if 'OVER02' in f][0]
    data, out, src = make_gameover(os.path.join(d, fn))
    save('mapsys/gameover.pac', fn, data)
    previews.append(('gameover', src, out))
    make_annos(previews)
    make_reports(previews)
    make_copyright(previews)
    make_show(previews)
    # preview: original | English, 2 per row
    W, H = 320, 240
    sheet = Image.new('RGB', (W * 4, H * ((len(previews) + 1) // 2)), (0, 0, 40))
    for k, (name, src, out) in enumerate(previews):
        x = (k % 2) * W * 2
        y = (k // 2) * H
        sheet.paste(Image.fromarray(src), (x, y))
        sheet.paste(Image.fromarray(out), (x + W, y))
    sp = os.path.join(ROOT, 'work', 'ui', 'gfx_sheets', 'en_cards.png')
    sheet.save(sp)
    print(len(previews), 'images ->', OUT, '; preview', sp)



# ---------------------------------------------------------------- flight result reports (4 bpp)
# rect = (x0, y0, x1, y1) of the Japanese text, ink 'red' (header) or 'dark' (labels)
REPORTS = {
    'REP_1': [((20, 18, 236, 90), 'red', ['TRAINING', 'RESULTS'], FONT_BIG, 'c'),
              ((12, 96, 150, 122), 'dark', ['Difficulty'], FONT, 'l'),
              ((12, 124, 150, 151), 'dark', ['Combine Time'], FONT, 'l'),
              ((12, 153, 150, 181), 'dark', ['Best Time'], FONT, 'l')],
    'REP_3': [((20, 18, 236, 90), 'red', ['COMBINATION', 'TEST'], FONT_BIG, 'c'),
              ((12, 96, 150, 122), 'dark', ['Difficulty'], FONT, 'l'),
              ((12, 124, 150, 151), 'dark', ['Combine Time'], FONT, 'l'),
              ((12, 153, 150, 181), 'dark', ['Best Time'], FONT, 'l')],
    'REP_2': [((18, 160, 240, 198), 'dark', ['Saotome Institute', 'Getter Pilot Training Committee'], FONT, 'c')],
}


def make_reports(previews):
    import gfx_sprites
    d = os.path.join(UNPACKED, 'flight', 'result.pac')
    for name, parts in REPORTS.items():
        fn = [f for f in os.listdir(d) if f.endswith('_%s.TIM' % name)][0]
        t = gfx_sprites.tim_read(os.path.join(d, fn))
        rgb = gfx_sprites.rgb_of(t['clut'])[t['idx']]
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        mask = np.zeros(rgb.shape[:2], np.uint8)
        inks = []
        for (x0, y0, x1, y1), ink, lines, font, align in parts:
            sub = np.zeros_like(mask)
            if ink == 'red':
                sel = (hsv[..., 1] > 120) & (hsv[..., 2] > 90)
            else:
                sel = rgb.max(2) < 150
            sub[y0:y1, x0:x1] = sel[y0:y1, x0:x1]
            inks.append(np.median(rgb[sub.astype(bool)], 0).astype(int) if sub.any() else (0, 0, 0))
            mask |= cv2.dilate(sub, np.ones((5, 5) if ink == 'dark' else (3, 3), np.uint8))
        clean = cv2.inpaint(np.ascontiguousarray(rgb), mask * 255, 4, cv2.INPAINT_TELEA)
        img = Image.fromarray(clean)
        dr = ImageDraw.Draw(img)
        for ((x0, y0, x1, y1), ink, lines, font, align), col in zip(parts, inks):
            col = tuple(int(c) for c in col)
            if ink == 'dark':
                col = tuple(max(0, c - 20) for c in col)
            for sz in range(60 if ink == 'red' else 22, 6, -1):
                f = ImageFont.truetype(font, sz)
                bbs = [dr.textbbox((0, 0), ln, font=f) for ln in lines]
                tot = sum(b[3] - b[1] for b in bbs) + 3 * (len(lines) - 1)
                if max(b[2] - b[0] for b in bbs) <= x1 - x0 and tot <= y1 - y0:
                    break
            y = y0 + (y1 - y0 - tot) // 2
            for ln, b in zip(lines, bbs):
                w = b[2] - b[0]
                x = x0 if align == 'l' else x0 + (x1 - x0 - w) // 2
                dr.text((x - b[0], y - b[1]), ln, font=f, fill=col)
                y += b[3] - b[1] + 3
        out = np.array(img)
        idx = quantize(out, t['clut'].astype(np.uint16))
        save('flight/result.pac', fn, gfx_sprites.tim_write(t, idx))
        previews.append((name, np.pad(rgb, ((0, 24), (0, 64), (0, 0))),
                         np.pad(gfx_sprites.rgb_of(t['clut'])[idx], ((0, 24), (0, 64), (0, 0)))))



# ---------------------------------------------------------------- title screen copyright
SERIF = FONT
COPY_LINES = ['\u00a91999 Dynamic Planning', '\u00a91999 Bandai Visual /', 'Tecnosoft']


def _draw_shadowed(img, xy, text, font):
    d = ImageDraw.Draw(img)
    x, y = xy
    d.text((x + 1, y + 1), text, font=font, fill=(16, 16, 16, 255))
    d.text((x + 2, y + 2), text, font=font, fill=(16, 16, 16, 255))
    d.text((x, y), text, font=font, fill=(255, 255, 255, 255))


def _quant_alpha(rgba, clut):
    idx = quantize(rgba[..., :3], clut)
    tr = [i for i in range(len(clut)) if clut[i] == 0]
    if tr:
        idx[rgba[..., 3] < 128] = tr[0]
    return idx


def make_copyright(previews):
    import gfx_sprites
    d = os.path.join(UNPACKED, 'demo', 'title.pac')
    f0 = [f for f in os.listdir(d) if f.endswith('_COPY0.TIM')][0]
    f1 = [f for f in os.listdir(d) if f.endswith('_COPY1.TIM')][0]
    t0, t1 = gfx_sprites.tim_read(os.path.join(d, f0)), gfx_sprites.tim_read(os.path.join(d, f1))
    h0, w0 = t0['idx'].shape
    h1, w1 = t1['idx'].shape
    # Keep the established type size. The credit is drawn across two sprites.
    dr = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    for sz in range(20, 8, -1):
        fnt = ImageFont.truetype(SERIF, sz)
        if max(dr.textbbox((0, 0), s, font=fnt)[2] for s in COPY_LINES[:2]) <= w0 - 4:
            break
    # Native title origins are (101, 413) and (286, 432). Typeset the
    # second line once so a word can cross their seam at normal spacing.
    dx, dy = 185, 19
    credit = Image.new('RGBA', (dx + w1, max(h0, dy + h1)))
    _draw_shadowed(credit, (1, 0), COPY_LINES[0], fnt)
    _draw_shadowed(credit, (1, h0 // 2), ' '.join(COPY_LINES[1:]), fnt)
    a = Image.new('RGBA', (w0, h0))
    a.paste(credit.crop((0, 0, dx, h0)), (0, 0))
    b = credit.crop((dx, dy, dx + w1, dy + h1))
    i0 = _quant_alpha(np.array(a), t0['clut'].astype(np.uint16))
    i1 = _quant_alpha(np.array(b), t1['clut'].astype(np.uint16))
    save('demo/title.pac', f0, gfx_sprites.tim_write(t0, i0))
    save('demo/title.pac', f1, gfx_sprites.tim_write(t1, i1))
    rgb0 = gfx_sprites.rgb_of(t0['clut'])
    rgb1 = gfx_sprites.rgb_of(t1['clut'])
    src = np.zeros((240, 320, 3), np.uint8)
    out = np.zeros((240, 320, 3), np.uint8)
    src[:h0, :w0] = rgb0[t0['idx']]
    src[dy:dy + h1, dx:dx + w1] = rgb1[t1['idx']]
    out[:h0, :w0] = rgb0[i0]
    out[dy:dy + h1, dx:dx + w1] = rgb1[i1]
    previews.append(('copyright', src, out))
    # title2.pac: the same text on top of artwork (COPY0 256 + COPY1 60 wide, side by side)
    d = os.path.join(UNPACKED, 'demo', 'title2.pac')
    f0 = [f for f in os.listdir(d) if f.endswith('_COPY0.TIM')][0]
    f1 = [f for f in os.listdir(d) if f.endswith('_COPY1.TIM')][0]
    t0, t1 = gfx_sprites.tim_read(os.path.join(d, f0)), gfx_sprites.tim_read(os.path.join(d, f1))
    w0 = t0['idx'].shape[1]
    rgb = np.concatenate([gfx_sprites.rgb_of(t0['clut'])[t0['idx']], gfx_sprites.rgb_of(t1['clut'])[t1['idx']]], 1)
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    glyph = ((rgb.min(2) >= 190) & (hsv[..., 1] < 60)).astype(np.uint8)
    mask = cv2.dilate(glyph, np.ones((5, 5), np.uint8))
    clean = cv2.inpaint(np.ascontiguousarray(rgb), mask * 255, 4, cv2.INPAINT_TELEA)
    img = Image.fromarray(clean).convert('RGBA')
    H, W = rgb.shape[:2]
    for sz in range(20, 8, -1):
        fnt = ImageFont.truetype(SERIF, sz)
        if max(dr.textbbox((0, 0), s, font=fnt)[2] for s in (COPY_LINES[0], COPY_LINES[1] + ' ' + COPY_LINES[2])) <= W - 6:
            break
    _draw_shadowed(img, (3, 1), COPY_LINES[0], fnt)
    _draw_shadowed(img, (3, H // 2), COPY_LINES[1] + ' ' + COPY_LINES[2], fnt)
    o = np.array(img)[..., :3]
    save('demo/title2.pac', f0, gfx_sprites.tim_write(t0, quantize(o[:, :w0], t0['clut'].astype(np.uint16))))
    save('demo/title2.pac', f1, gfx_sprites.tim_write(t1, quantize(o[:, w0:], t1['clut'].astype(np.uint16))))
    src = np.zeros((240, 320, 3), np.uint8)
    out = np.zeros((240, 320, 3), np.uint8)
    src[:H, :W] = rgb
    out[:H, :W] = o
    previews.append(('copyright2', src, out))



# ---------------------------------------------------------------- promo screens (flight/show.pac)
# two 512x240 screens, each stored as two 256-wide 8 bpp TIMs (left, right)
SHOW = [
    (('FACE000', 'FACE002'), [((0, 22, 512, 66), ['SIMULATION RPG + COMBINATION SIMULATOR'], FONT, 30)]),
    (('FACE001_', 'FACE003_'), [((40, 40, 472, 140), ['COMING IN SEPTEMBER'], FONT_BIG, 64),
                                ((60, 136, 500, 160), ['PlayStation software (DualShock compatible)'], FONT, 22),
                                ((200, 160, 500, 180), ['Expected price: 6,800 yen (before tax)'], FONT, 22),
                                ((20, 178, 500, 202), ['©1999 Dynamic Planning   ©1999 Bandai Visual / Tecnosoft'], FONT, 16)]),
]


def make_show(previews):
    d = os.path.join(UNPACKED, 'flight', 'show.pac')
    for (ln, rn), parts in SHOW:
        lf = [f for f in os.listdir(d) if f.endswith('_%s.TIM' % ln)][0]
        rf = [f for f in os.listdir(d) if f.endswith('_%s.TIM' % rn)][0]
        lr, rr = open(os.path.join(d, lf), 'rb').read(), open(os.path.join(d, rf), 'rb').read()
        lt, rt = tim_read(lr), tim_read(rr)
        rgb = np.concatenate([clut_rgb(lt['clut'])[lt['idx']], clut_rgb(rt['clut'])[rt['idx']]], 1)
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        white = ((rgb.min(2) >= 200) & (hsv[..., 1] < 60)).astype(np.uint8)
        mask = np.zeros_like(white)
        for (x0, y0, x1, y1), _, _, _ in parts:
            mask[y0:y1, x0:x1] = white[y0:y1, x0:x1]
        mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
        clean = cv2.inpaint(np.ascontiguousarray(rgb), mask * 255, 6, cv2.INPAINT_TELEA)
        img = Image.fromarray(clean)
        dr = ImageDraw.Draw(img)
        for (x0, y0, x1, y1), lines, font, size in parts:
            for sz in range(size, 8, -1):
                f = ImageFont.truetype(font, sz)
                b = dr.textbbox((0, 0), lines[0], font=f, stroke_width=2)
                if b[2] - b[0] <= x1 - x0 and b[3] - b[1] <= y1 - y0:
                    break
            x = x0 + (x1 - x0 - (b[2] - b[0])) // 2
            y = y0 + (y1 - y0 - (b[3] - b[1])) // 2
            draw_lines(img, x, y, [(lines[0], sz, 'l')], font, (255, 255, 255), stroke=2)
        out = np.array(img)
        for (fn, raw, t), part in (((lf, lr, lt), out[:, :256]), ((rf, rr, rt), out[:, 256:])):
            save('flight/show.pac', fn, tim_write(raw, t, quantize(part, t['clut'])))
        previews.append(('show ' + ln, rgb[:, :320], out[:, :320]))
        previews.append(('show ' + rn, rgb[:, 192:], out[:, 192:]))


if __name__ == '__main__':
    main()
