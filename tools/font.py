"""Proportional Latin font for the VWF, built from the game's own FONT12_0 glyphs.

Each printable ASCII char 0x20-0x7E is taken from the full-width glyph the game already
draws for it (FONT12_0: 82xx cells, 81xx symbol cells in the right 5 columns), cropped to
its ink (incl. the drop shadow, palette index 10), and redrawn left-aligned in the same
cell. Advance = ink width + SPACING (space = SPACE_W). Characters without a game glyph
(apostrophe, quotes, # * < > ...) are drawn from GLYPH_EXTRA below with the game's row
gradient + (+1,+1) shadow.

    python tools/font.py preview out.png "Sample text"
    python tools/font.py widths            print the width table

Palette (FNT_CLUT row 0..7): index 11 = transparent, 0..9 row gradient, 10 = shadow.
"""
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETUP = os.path.join(ROOT, 'work', 'source', 'unpacked', 'bin', 'setup.pac')
BG = 11
SHADOW = 10
SPACING = 1
SPACE_W = 4
# gradient index by cell row (from the original glyphs)
ROWGRAD = [0, 0, 1, 2, 3, 4, 5, 6, 6, 8, 9, 9]

# ASCII -> SJIS code of the game glyph used as source (exe table 0x8007F5C4, corrected)
ASCII_SRC = {}
_t = [0x8140, 0x8149, None, None, 0x8190, 0x8193, 0x8195, None, 0x8169, 0x816A, None, 0x817B,
      0x8143, 0x817C, 0x8144, 0x815E]
for i, c in enumerate(_t):
    if c:
        ASCII_SRC[0x20 + i] = c
for i in range(10):
    ASCII_SRC[0x30 + i] = 0x824F + i
ASCII_SRC.update({0x3A: 0x8146, 0x3B: 0x8147, 0x3D: 0x8181, 0x3F: 0x8148})
for i in range(26):
    ASCII_SRC[0x41 + i] = 0x8260 + i
    ASCII_SRC[0x61 + i] = 0x8281 + i
ASCII_SRC.update({0x5B: 0x816D, 0x5D: 0x816E, 0x5F: 0x8151, 0x7E: 0x8160})

# hand-drawn glyphs ('#' ink) for chars the game font lacks or draws badly; top row in cell
GLYPH_EXTRA = {
    0x27: (2, ['#', '#', '#']),                     # '
    0x22: (2, ['#.#', '#.#', '#.#']),               # "
    0x23: (3, ['.#.#.', '#####', '.#.#.', '#####', '.#.#.']),
    0x2A: (3, ['#.#', '.#.', '#.#']),
    0x2C: (9, ['#', '#']),                          # ,  (full-width comma is centred low)
    0x2E: (9, ['#']),                               # .
    0x21: (2, ['#', '#', '#', '#', '#', '#', '.', '#']),   # !
    0x3A: (4, ['#', '.', '.', '.', '.', '#']),             # :
    0x3B: (4, ['#', '.', '.', '.', '.', '#', '#']),        # ;
    0x3C: (4, ['..#', '.#.', '#..', '.#.', '..#']),
    0x3E: (4, ['#..', '.#.', '..#', '.#.', '#..']),
    0x2D: (6, ['###']),                                    # -
    0x2F: (2, ['...#', '...#', '..#.', '..#.', '.#..', '.#..', '#...', '#...']),
    0x28: (2, ['.#', '#.', '#.', '#.', '#.', '#.', '#.', '.#']),
    0x29: (2, ['#.', '.#', '.#', '.#', '.#', '.#', '.#', '#.']),
    0x5B: (2, ['##', '#.', '#.', '#.', '#.', '#.', '#.', '##']),
    0x5D: (2, ['##', '.#', '.#', '.#', '.#', '.#', '.#', '##']),
    0x2B: (4, ['.#.', '###', '.#.']),
    0x3D: (4, ['###', '...', '###']),
    0x3F: (2, ['.##.', '#..#', '...#', '..#.', '.#..', '.#..', '....', '.#..']),
    0x5E: (2, ['.#.', '#.#']),
    0x60: (2, ['#.', '.#']),
    0x7B: (2, ['.#', '#.', '#.', '##', '#.', '#.', '#.', '.#']),
    0x7D: (2, ['#.', '.#', '.#', '##', '.#', '.#', '.#', '#.']),
    0x7C: (2, ['#'] * 9),
    0x5C: (2, ['#...', '#...', '.#..', '.#..', '..#.', '..#.', '...#', '...#']),
    0x26: (2, ['.##..', '#..#.', '#..#.', '.##..', '#.#.#', '#..#.', '#..#.', '.##.#']),
    0x40: (2, ['.###.', '#...#', '#.###', '#.#.#', '#.###', '#....', '.###.']),
    0x24: (1, ['..#..', '.####', '#.#..', '.###.', '..#.#', '####.', '..#..']),
    0x25: (2, ['##..#', '##.#.', '...#.', '..#..', '.#...', '.#.##', '#..##']),
}


def load_tim(name):
    d = open(os.path.join(SETUP, name), 'rb').read()
    p = 8
    if struct.unpack_from('<I', d, 4)[0] & 8:
        p += struct.unpack_from('<I', d, p)[0]
    ln, x, y, w, h = struct.unpack_from('<IHHHH', d, p)
    px = d[p + 12:p + ln]
    W = w * 4
    rows = [[(px[(yy * W + xx) // 2] >> (4 * (xx & 1))) & 15 for xx in range(W)] for yy in range(h)]
    return d, p, rows, W, h


SYM_CODES = None


def sym_codes():
    """81xx codes in symbol-column order (exe data 0x8008078C, 2-byte big-endian)."""
    exe = open(os.path.join(ROOT, 'work', 'source', 'disc', 'SLPS_022.32'), 'rb').read()
    o = 0x8008078C - 0x80010000 + 0x800
    out = []
    while exe[o]:
        out.append(exe[o] << 8 | exe[o + 1])
        o += 2
    return out


def cell_of(code):
    """(row, col) of a 12x12 cell in FONT12_0 for an SJIS code, as the game draws it."""
    hi, lo = code >> 8, code & 0xFF
    if hi == 0x82:
        idx = (0x5F if lo == 0x4F else (lo - 0x72 if lo >= 0xF0 else lo)) - 0x50
        return divmod(idx, 16)
    if hi == 0x81:
        i = sym_codes().index(code)
        r, c = divmod(i, 5)
        return r, 16 + c
    raise KeyError(hex(code))


def cell(rows, rc):
    r, c = rc
    return [rows[r * 12 + y][c * 12:c * 12 + 12] for y in range(12)]


def crop(cellpx):
    cols = [x for x in range(12) if any(cellpx[y][x] != BG for y in range(12))]
    if not cols:
        return [], 0
    x0, x1 = min(cols), max(cols)
    return [row[x0:x1 + 1] for row in cellpx], x1 - x0 + 1


def draw_extra(spec):
    top, lines = spec
    w = max(len(l) for l in lines)
    g = [[BG] * (w + 1) for _ in range(12)]
    for i, l in enumerate(lines):
        for x, ch in enumerate(l):
            if ch == '#':
                y = top + i
                g[y][x] = ROWGRAD[y]
    for i, l in enumerate(lines):
        for x, ch in enumerate(l):
            if ch == '#':
                y = top + i + 1
                if y < 12 and g[y][x + 1] == BG:
                    g[y][x + 1] = SHADOW
    return g, w + 1


FONT_FILE = os.path.join(ROOT, 'tools', 'fonts', 'gr_latin.txt')
ADV = {}


def parse_font(path=FONT_FILE):
    """{ascii: (top, rows, adv or None)} from the hand-drawn font file."""
    out = {}
    cur = None
    for line in open(path, encoding='utf-8'):
        line = line.rstrip(chr(10)).rstrip(chr(13))
        if line.startswith('#') and not cur or not line.strip():
            if not line.strip():
                cur = None
            continue
        if line.startswith('@ '):
            parts = line.split()
            ch = ' ' if parts[1] == 'space' else parts[1]
            adv = None
            for p_ in parts[3:]:
                if p_.startswith('adv='):
                    adv = int(p_[4:])
            cur = [int(parts[2]), [], adv]
            out[ord(ch)] = cur
            continue
        if cur is not None:
            cur[1].append(line)
    return {k: (v[0], v[1], v[2]) for k, v in out.items()}


def build():
    """Return {ascii: (glyph rows (12 x w), width)} from tools/fonts/gr_latin.txt."""
    ADV.clear()
    glyphs = {}
    for c, (top, rows, adv) in parse_font().items():
        if rows:
            g, w = draw_extra((top, rows))
        else:
            g, w = [[BG] for _ in range(12)], 0
        glyphs[c] = (g, w)
        if adv is not None:
            ADV[c] = adv
    for c in range(0x20, 0x7F):
        if c not in glyphs:
            glyphs[c] = draw_extra((2, ['###', '#.#', '#.#', '###']))
    return glyphs


def build_game():
    """Return {ascii: (glyph rows (12 x w), width)} from the game's own glyphs (unused)."""
    _, _, rows, _, _ = load_tim('00000_000_FONT12_0.TIM')
    glyphs = {0x20: ([[BG] * 1 for _ in range(12)], 0)}
    for c in range(0x21, 0x7F):
        if c in GLYPH_EXTRA:
            glyphs[c] = draw_extra(GLYPH_EXTRA[c])
        elif c in ASCII_SRC:
            g, w = crop(cell(rows, cell_of(ASCII_SRC[c])))
            glyphs[c] = (g, w)
        else:
            glyphs[c] = draw_extra((2, ['###', '#.#', '#.#', '###']))   # placeholder box
    return glyphs


def advance(glyphs, c):
    if c in ADV:
        return ADV[c]
    if c == 0x20:
        return SPACE_W
    return glyphs[c][1] + SPACING


def widths(glyphs=None):
    glyphs = glyphs or build()
    return bytes(advance(glyphs, c) for c in range(0x20, 0x80) if c < 0x7F) + b'\x0c'


def text_width(s, w=None):
    w = w or widths()
    return sum(w[ord(ch) - 0x20] if 0x20 <= ord(ch) < 0x7F else 12 for ch in s)


def render(text, glyphs=None, scale=3):
    from PIL import Image
    glyphs = glyphs or build()
    pal = [(255, 255, 255)] * 10 + [(40, 40, 40), (40, 70, 140)] + [(0, 0, 0)] * 4
    grad = [(255, 255, 255), (250, 250, 250), (240, 240, 240), (230, 230, 230), (220, 220, 220),
            (210, 210, 210), (200, 200, 200), (200, 200, 200), (190, 190, 190), (180, 180, 180)]
    pal[:10] = grad
    W = text_width(text) + 4
    im = Image.new('RGB', (W, 14), pal[11])
    x = 2
    for ch in text:
        c = ord(ch)
        g, w = glyphs.get(c, glyphs[0x3F])
        for y in range(12):
            for xx in range(w):
                v = g[y][xx]
                if v != BG:
                    im.putpixel((x + xx, y + 1), pal[v])
        x += advance(glyphs, c)
    return im.resize((im.width * scale, im.height * scale), Image.NEAREST)


if __name__ == '__main__':
    if sys.argv[1] == 'preview':
        render(sys.argv[3]).save(sys.argv[2])
    elif sys.argv[1] == 'widths':
        w = widths()
        for c in range(0x20, 0x7F):
            print(repr(chr(c)), w[c - 0x20], end='  ')
        print()
