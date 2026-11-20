"""Contact sheets of the TIM entries of unpacked pacs (for finding graphics with text).

    python tools/timsheet.py <unpacked dir> [...]   -> work/ui/gfx_sheets/<dir>.png

Each TIM is drawn with its first CLUT (4/8 bpp) or as 15-bit colour, labelled by entry name.
"""
import os
import struct
import sys

from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def tim_image(d):
    if len(d) < 20 or struct.unpack_from('<I', d, 0)[0] != 0x10:
        return None
    flags = struct.unpack_from('<I', d, 4)[0]
    bpp = flags & 3
    p = 8
    clut = None
    if flags & 8:
        ln, cx, cy, cw, ch = struct.unpack_from('<IHHHH', d, p)
        clut = struct.unpack_from('<%dH' % (cw * ch), d, p + 12)
        p += ln
    ln, x, y, w, h = struct.unpack_from('<IHHHH', d, p)
    px = d[p + 12:p + 12 + w * h * 2]

    def col(c):
        if c == 0:
            return (40, 40, 40)
        return ((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3)
    if bpp == 0:
        W = w * 4
        im = Image.new('RGB', (W, h))
        im.putdata([col(clut[(px[(yy * W + xx) // 2] >> (4 * (xx & 1))) & 15]) for yy in range(h) for xx in range(W)])
    elif bpp == 1:
        W = w * 2
        im = Image.new('RGB', (W, h))
        im.putdata([col(clut[px[yy * W + xx]]) for yy in range(h) for xx in range(W)])
    elif bpp == 2:
        im = Image.new('RGB', (w, h))
        im.putdata([col(struct.unpack_from('<H', px, (yy * w + xx) * 2)[0]) for yy in range(h) for xx in range(w)])
    else:
        return None
    return im


def sheet(folder, out):
    tiles = []
    for fn in sorted(os.listdir(folder)):
        if not fn.upper().endswith('.TIM'):
            continue
        try:
            im = tim_image(open(os.path.join(folder, fn), 'rb').read())
        except Exception:
            im = None
        if im and im.width * im.height > 0:
            tiles.append((fn, im))
    if not tiles:
        return False
    W = 1024
    x = y = rowh = 0
    pos = []
    for fn, im in tiles:
        im.thumbnail((256, 256))
        if x + im.width > W:
            x = 0
            y += rowh + 12
            rowh = 0
        pos.append((x, y, fn, im))
        x += im.width + 4
        rowh = max(rowh, im.height)
    sh = Image.new('RGB', (W, y + rowh + 12), (0, 0, 60))
    d = ImageDraw.Draw(sh)
    for x, y, fn, im in pos:
        sh.paste(im, (x, y + 10))
        d.text((x, y), fn.split('_', 2)[-1][:14], fill=(255, 255, 0))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sh.save(out)
    return True


if __name__ == '__main__':
    for f in sys.argv[1:]:
        name = f.rstrip('/\\').replace('\\', '/').split('unpacked/')[-1].replace('/', '__')
        out = os.path.join(ROOT, 'work', 'ui', 'gfx_sheets', name + '.png')
        if sheet(f, out):
            print(out)
