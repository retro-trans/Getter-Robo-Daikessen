"""Variable-width font for Getter Robo Daikessen (SLPS_022.32). See docs/VWF.md.

Font: tools/fonts/gr_latin.txt, drawn into FONT12_0.TIM cells (bin/setup.pac).
  * '0'-'9', 'A'-'Z', 'a'-'z' replace the full-width Latin cells (so full-width text such
    as the name-entry grid and the player's name use the same glyphs);
  * punctuation goes into the matching symbol cells (right 5 columns) or, if the game has
    no such symbol, into unused 82xx cells (lo 0x59-0x5E, 0x7A-0x80);
  * the exe's ASCII -> SJIS table (0x8007F5C4) points every ASCII char at its cell.
Width tables + hooks live in kernel RAM at CAVE (copied there by an entry stub appended
to the exe; the stub then jumps to the original entry point).

Hooks:
  A 0x8004E0A8 (string drawer 0x8004DE34, per char)    pen += width - 12
  B 0x8005BC74 / 0x8005BC84 (dialogue draw loop)        x = left + pixel sum
  C 0x8005B8A0 (typewriter, SJIS) / 0x8005BA80 (ASCII)  column counter in pixels
  D 0x8005B168 / 0x8005B150 (window setup)              max columns = text width in pixels
  E 0x8004E104 (display length of a string)            ceil(pixel width / 12)
  F 0x8004E2A0 / 0x8004E2A4 (12px number printer)       digit step 12 -> 7 (24 -> 14)
  H 0x800580D0 / 0x80058280 (list / hex menu items)     label width in pixels (strpx)
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import font      # noqa: E402
import masm      # noqa: E402

CAVE = 0x8000F000          # kernel RAM, unused by BIOS / game (docs/VWF.md)
CAVE_END = 0x8000F600      # next resident UI string pool begins here
ASCII_TABLE = 0x8007F5C4   # u16[96] ASCII 0x20.. -> SJIS (LE)
EXE_BASE = 0x80010000
SECONDARY_CAVE = 0x8000DD40  # after preview scratch DD00..DD20, before DE00 fixture

# punctuation -> symbol code (81xx, must be in the symbol list) or None = needs a spare cell
PUNCT_SYM = {
    0x21: 0x8149, 0x22: 0x8168, 0x24: 0x8190, 0x25: 0x8193, 0x26: 0x8195, 0x27: 0x8166,
    0x28: 0x8169, 0x29: 0x816A, 0x2B: 0x817B, 0x2C: 0x8143, 0x2D: 0x817C, 0x2E: 0x8144,
    0x2F: 0x815E, 0x3A: 0x8146, 0x3B: 0x8147, 0x3D: 0x8181, 0x3F: 0x8148, 0x5B: 0x816D,
    0x5D: 0x816E, 0x5F: 0x8151, 0x7E: 0x8160,
}
SPARE_82 = [0x8259, 0x825A, 0x825B, 0x825C, 0x825D, 0x825E, 0x827A, 0x827B, 0x827C, 0x827D,
            0x8280]   # 0x827E/0x827F share cells with を/ん (82F0/82F1 -> lo-0x72)


def ascii_map():
    """{ascii: sjis code} for 0x20..0x7E."""
    m = {0x20: 0x8140}
    for i in range(10):
        m[0x30 + i] = 0x824F + i
    for i in range(26):
        m[0x41 + i] = 0x8260 + i
        m[0x61 + i] = 0x8281 + i
    syms = font.sym_codes()
    spare = list(SPARE_82)
    for c in range(0x21, 0x7F):
        if c in m:
            continue
        s = PUNCT_SYM.get(c)
        if s and s in syms:
            m[c] = s
        else:
            m[c] = spare.pop(0)
    return m


def patched_font_tim():
    """FONT12_0.TIM (bin/setup.pac) with the VWF glyphs drawn into their cells."""
    d, p, rows, W, H = font.load_tim('00000_000_FONT12_0.TIM')
    glyphs = font.build()
    m = ascii_map()
    for c, code in m.items():
        if c == 0x20:
            continue
        r, col = font.cell_of(code) if code >> 8 == 0x81 else divmod(
            (0x5F if (code & 0xFF) == 0x4F else (code & 0xFF)) - 0x50, 16)
        g, w = glyphs[c]
        for y in range(12):
            for x in range(12):
                rows[r * 12 + y][col * 12 + x] = g[y][x] if x < w else font.BG
    # repack pixels
    out = bytearray(d)
    ln = struct.unpack_from('<I', d, p)[0]
    px = bytearray(ln - 12)
    for y in range(H):
        for x in range(0, W, 2):
            px[(y * W + x) // 2] = rows[y][x] | rows[y][x + 1] << 4
    out[p + 12:p + ln] = px
    return bytes(out)


def width_tables():
    """(ascii widths 0x20..0x7F [96 bytes], 82xx widths by low byte [256 bytes])."""
    glyphs = font.build()
    wa = bytearray(96)
    for c in range(0x20, 0x80):
        wa[c - 0x20] = font.advance(glyphs, c) if c < 0x7F else 12
    w82 = bytearray([12] * 256)
    for i in range(10):
        w82[0x4F + i] = wa[0x30 + i - 0x20]
    for i in range(26):
        w82[0x60 + i] = wa[0x41 + i - 0x20]
        w82[0x81 + i] = wa[0x61 + i - 0x20]
    return bytes(wa), bytes(w82)


ASM = r'''
; ---- width(a0 = code: ASCII byte or SJIS 0xHHLL) -> v0 (1x pixels); uses t8, t9
width:
    sltiu t8, a0, 0x80
    beqz t8, w_sj
    nop
    la t8, WA - 0x20
    addu t8, t8, a0
    lbu v0, 0(t8)
    jr ra
    nop
w_sj:
    srl t8, a0, 8
    li t9, 0x82
    bne t8, t9, w_full
    andi t8, a0, 0xFF
    la t9, W82
    addu t9, t9, t8
    lbu v0, 0(t9)
    jr ra
    nop
w_full:
    jr ra
    li v0, 12

; ---- A: string drawer per-char draw (replaces jal 0x8004DA64 at 0x8004E0A8)
;      pen s3 += width - s7 (the drawer then adds s7); s7 = 12 or 24 (double width)
drawadv:
    addiu sp, sp, -24
    sw ra, 16(sp)
    jal 0x8004DA64
    sw a2, 20(sp)
    lw a0, 20(sp)
    jal width
    andi a0, a0, 0xFFFF
    lui t8, 0x0400
    and t8, s5, t8
    beqz t8, da_large_check
    nop
    la t8, STATUS_MED_ADV
    addu t8, t8, v0
    lbu v0, 0(t8)
    b da_1
    nop
da_large_check:
    lui t8, 0x0800
    and t8, s5, t8
    beqz t8, da_normal
    nop
    la t8, STATUS_ADV
    addu t8, t8, v0
    lbu v0, 0(t8)
    b da_1
    nop
da_normal:
    li t8, 12
    beq s7, t8, da_1
    nop
    sll v0, v0, 1
da_1:
    addu s3, s3, v0
    subu s3, s3, s7
    lw ra, 16(sp)
    jr ra
    addiu sp, sp, 24

; Aspect-correct 19x24 cells, opted into only by the status renderer.
status_glyph_width:
    lui v1, 0x0400
    and v1, a3, v1
    beqz v1, sgw_large
    nop
    addiu t0, zero, 11
    lui a2, 0xD
    b sgw_done
    nop
sgw_large:
    lui v1, 0x0800
    and v1, a3, v1
    beqz v1, sgw_done
    nop
    addiu t0, zero, 19
sgw_done:
    lw v1, 0x240(gp)
    jr ra
    nop
STATUS_ADV:
    .byte 0, 2, 3, 5, 6, 8, 10, 11, 13, 14, 16, 17, 19
    .align 4
STATUS_MED_ADV:
    .byte 0, 1, 2, 3, 4, 5, 6, 6, 7, 8, 9, 10, 11
    .align 4

; ---- B: dialogue draw loop (0x8005BB80): s0 = pixel x within the line, a2 = item
;      called instead of 'addiu s0, s0, 1'; must keep v0, v1, a0-a3, t1 and hi/lo
dlgadv:
    move t2, a2
dl_0:
    lbu t3, 0(t2)
    li t4, 0x25
    bne t3, t4, dl_1
    nop
    b dl_0
    addiu t2, t2, 2
dl_1:
    li t6, 12
    li t4, 0x40
    beq t3, t4, dl_add
    sltiu t4, t3, 0x80
    beqz t4, dl_sj
    nop
    la t5, WA - 0x20
    addu t5, t5, t3
    b dl_add
    lbu t6, 0(t5)
dl_sj:
    li t4, 0x82
    bne t3, t4, dl_add
    nop
    lbu t4, 1(t2)
    la t5, W82
    addu t5, t5, t4
    lbu t6, 0(t5)
dl_add:
    li t4, 12
    j dlgadv_body_check
    nop
dl_double:
    sll t6, t6, 1
dl_2:
    jr ra
    addu s0, s0, t6

; ---- C1: typewriter SJIS char (0x8005B8A0, replaces 'addiu v0, v0, 1'); s0 = src after char
;      keep v1, a0; v0 = column (pixels)
colsj:
    lbu t8, -2(s0)
    li t9, 0x82
    bne t8, t9, cs_full
    nop
    lbu t8, -1(s0)
    la t9, W82
    addu t9, t9, t8
    lbu t8, 0(t9)
    jr ra
    addu v0, v0, t8
cs_full:
    jr ra
    addiu v0, v0, 12

; ---- C2: typewriter single-byte char (0x8005BA80; the delay slot stores the old column)
;      s2 = char; store the new column at 0x24(s3)
cola:
    la t8, WA - 0x20
    sltiu t9, s2, 0x80
    beqz t9, ca_full
    addu t8, t8, s2
    lbu t8, 0(t8)
    nop
    addu v0, v0, t8
    jr ra
    sh v0, 0x24(s3)
ca_full:
    addiu v0, v0, 12
    jr ra
    sh v0, 0x24(s3)

; ---- E: display length of a string (replaces 0x8004E104): ceil(pixels / 12)
;      same parsing as the original: '%X' colour (skip 2), '@@' or '@XY' icon (1 char)
; ---- strpx: same parsing, returns the width in pixels (hex / list menus, hook H)
strpx:
    addiu sp, sp, -32
    sw ra, 16(sp)
    sw s0, 20(sp)
    sw s1, 24(sp)
    li t0, 1
    b sl_start
    sw t0, 28(sp)
strlen:
    addiu sp, sp, -32
    sw ra, 16(sp)
    sw s0, 20(sp)
    sw s1, 24(sp)
    sw zero, 28(sp)
sl_start:
    move s0, a0
    move s1, zero
sl_loop:
    lbu a0, 0(s0)
    nop
    beqz a0, sl_end
    li t0, 0x25
    beq a0, t0, sl_pct
    li t0, 0x40
    beq a0, t0, sl_at
    sltiu t0, a0, 0x80
    bnez t0, sl_one
    nop
    jal 0x8004DCF4
    nop
    beqz v0, sl_one
    lbu a0, 0(s0)
    lbu t0, 1(s0)
    sll a0, a0, 8
    or a0, a0, t0
    addiu s0, s0, 1
sl_one:
    jal width
    nop
    addu s1, s1, v0
    b sl_loop
    addiu s0, s0, 1
sl_pct:
    b sl_loop
    addiu s0, s0, 2
sl_at:
    lbu t0, 1(s0)
    addiu s1, s1, 12
    beq t0, a0, sl_loop
    addiu s0, s0, 2
    b sl_loop
    addiu s0, s0, 1
sl_end:
    lw t0, 28(sp)
    nop
    bnez t0, sl_ret
    move v0, s1
    addiu s1, s1, 11
    move v0, zero
sl_div:
    slti t0, s1, 12
    bnez t0, sl_ret
    addiu s1, s1, -12
    b sl_div
    addiu v0, v0, 1
sl_ret:
    lw ra, 16(sp)
    lw s0, 20(sp)
    lw s1, 24(sp)
    jr ra
    addiu sp, sp, 32

    .align 2
WA:
    .space 96
W82:
    .space 256
; Opt-in status body text. Existing entry points and advance tables stay put.
; Only the reserved 0x32 high-byte mode opts in; every other flag is unchanged.
    .align 4
status_body_glyph_width:
    srl v1, a3, 24
    addiu v1, v1, -0x32
    bnez v1, status_glyph_width
    nop
    li t0, 16
    lui a2, 0x14
    lw v1, 0x240(gp)
    jr ra
    nop
drawadv_sized:
    srl t8, s5, 24
    addiu t8, t8, -0x32
    bnez t8, drawadv
    nop
body_advance:
    addiu sp, sp, -24
    sw ra, 16(sp)
    jal 0x8004DA64
    sw a2, 20(sp)
    lw a0, 20(sp)
    jal width
    andi a0, a0, 0xFFFF
    la t8, STATUS_BODY_ADV
    addu t8, t8, v0
    lbu v0, 0(t8)
    j da_1
    nop
STATUS_BODY_ADV:
    .byte 0, 1, 3, 4, 5, 7, 8, 9, 11, 12, 13, 15, 16
    .align 4
; 512x240 briefing text: 16x10 cells display square at 4:3.
; Old entry points remain fixed. Only exact mode 0x22 opts into the new path.
briefing_glyph_width:
    srl v1, a3, 24
    addiu v1, v1, -0x22
    bnez v1, status_body_glyph_width
    nop
    li t0, 16
    lui a2, 0xA
    lw v1, 0x240(gp)
    jr ra
    nop
briefing_drawadv:
    srl t8, s5, 24
    addiu t8, t8, -0x22
    bnez t8, drawadv_sized
    nop
    j body_advance
    nop
dlgadv_body_check:
    lw t5, 0x5C(s2)
    nop
    srl t5, t5, 24
    ori t5, t5, 0x10
    addiu t5, t5, -0x32
    bnez t5, dlgadv_legacy
    nop
    la t5, STATUS_BODY_ADV
    addu t5, t5, t6
    lbu t6, 0(t5)
    j dl_2
    nop
dlgadv_legacy:
    beq s5, t4, dl_2
    nop
    j dl_double
    nop
CAVE_END_LABEL:
'''


def build_cave():
    wa, w82 = width_tables()
    code, labels = masm.assemble(ASM, CAVE)
    code = bytearray(code)
    o = labels['WA'] - CAVE
    code[o:o + 96] = wa
    o = labels['W82'] - CAVE
    code[o:o + 256] = w82
    assert CAVE + len(code) <= CAVE_END, hex(CAVE + len(code))
    return bytes(code), labels


def j(target):
    return 0x08000000 | ((target >> 2) & 0x3FFFFFF)


def build_secondary_font(primary=None):
    """Exact opt-in 0x36 = 14x17; every other font follows its old dispatcher."""
    if primary is None:
        _, primary = build_cave()
    code, labels = masm.assemble(r'''
secondary_glyph_width:
    srl v1, a3, 24
    addiu v1, v1, -0x36
    bnez v1, briefing_glyph_width
    nop
    li t0, 14
    lui a2, 0x11
    lw v1, 0x240(gp)
    jr ra
    nop
secondary_drawadv:
    srl t8, s5, 24
    addiu t8, t8, -0x36
    bnez t8, briefing_drawadv
    nop
    addiu sp, sp, -24
    sw ra, 16(sp)
    jal 0x8004DA64
    sw a2, 20(sp)
    lw a0, 20(sp)
    jal width
    andi a0, a0, 0xFFFF
    la t8, SECONDARY_ADV
    addu t8, t8, v0
    lbu v0, 0(t8)
    j da_1
    nop
SECONDARY_ADV:
    .byte 0,1,2,4,5,6,7,8,9,11,12,13,14
    .align 4
''', SECONDARY_CAVE, symbols=primary)
    assert SECONDARY_CAVE+len(code) <= 0x8000DE00
    return code, labels


def jal(target):
    return 0x0C000000 | ((target >> 2) & 0x3FFFFFF)


def exe_patches(labels):
    """{address: u32 instruction} applied to the exe image."""
    L = labels
    p = {}
    _, secondary = build_secondary_font(L)
    p[0x8004D7AC] = jal(secondary['secondary_glyph_width'])
    p[0x8004E0A8] = jal(secondary['secondary_drawadv'])       # A
    p[0x8005BC74] = 0x02004821                        # B: mflo t1 -> addu t1, s0, zero
    p[0x8005BC84] = jal(L['dlgadv'])                  #    addiu s0,s0,1 -> jal dlgadv
    p[0x8005B8A0] = jal(L['colsj'])                   # C1
    p[0x8005BA80] = jal(L['cola'])                    # C2
    p[0x8005B168] = 0x00801821                        # D: sra v1,a2,1 -> addu v1, a0, zero
    p[0x8005B150] = 0x00041843                        #    sra v1,a2,2 -> sra v1, a0, 1
    p[0x8004E104] = j(L['strlen'])                    # E
    p[0x8004E108] = 0x00000000
    p[0x8004E2A0] = 0x2451FFF6                        # F: addiu s1, v0, -0x18 -> -10
    p[0x8004E2A4] = 0x2451FFFB                        #    addiu s1, v0, -0xc  -> -5
    # G: message window struct (WINDOW.C) 0x3E8 -> 0x4E8 bytes. The page line buffer at
    # +0x368 had 128 bytes (Japanese pages reach 132, English 178); a longer page ran
    # into the next heap block header and crashed the heap later (Episode 2).
    p[0x8005A88C] = 0x240404E8                        # addiu a0, zero, 0x3e8 -> 0x4e8
    # H: list / hex menus (0x80058050, 0x80058240): item label width = pixels, not
    # display length x 12. Right-aligned items (left column of the map action menu) end at
    # the same x as the Japanese ones; the highlight box is text width + 2 as before.
    for call, a, b, c in ((0x800580D0, 0x800580D8, 0x800580DC, 0x800580F0),
                          (0x80058280, 0x80058288, 0x8005828C, 0x800582A0)):
        p[call] = jal(L['strpx'])                     # jal 0x8004e104 -> strpx
        p[a] = 0x00401821                             # sll v1,v0,1  -> addu v1, v0, zero
        p[b] = 0x00000000                             # addu v1,v1,v0 -> nop
        p[c] = 0x00603021                             # sll a2,v1,2  -> addu a2, v1, zero
    return p


# Overlay code patches: {overlay tag: {address: (original u32, new u32)}}. The build checks
# the original word, then writes the new one into bin/<tag>.bin (tools/build.py).
OVERLAY_PATCHES = {
    'battle': {
        # Native Start -> battle fast-finish already exists, but its caller only
        # permits standalone/demo battles (parent +0x7e8 == -1). Allow the same
        # cleanup path for map battles. Keep the phase <18 guard and all native
        # outcome/cleanup code; no battle data or timings are rewritten.
        0x800AE00C: (0x1462000A, 0x00000000),
    },
    'title': {
        # Name confirmation: labels use narrow Latin glyphs but these two native
        # selection rectangles still had Japanese-sized positions and widths.
        0x80092E2C: (116, 122),
        0x80092E34: (40, 24),
        0x80092E3C: (164, 158),
        0x80092E44: (40, 24),
    },
    'game': {
        # Map unit HUD: leave a gap between Lnd/Air/Sea/Spc and HP/energy.
        0x80096270: (0x24040009, 0x24040003),         # label x: 9 -> 3
        # unit status, weapon page (512x480, glyphs drawn 2x tall): the "HP" / "Getter Ray"
        # label (0x800982B8 -> string drawer) is drawn at y+3 like the 12 px digits next to
        # it. Kanji fill the cell, English capitals stop at row 8 and sat 3 lines below the
        # digits' bottom: label at y+0.
        0x80098474: (0x24A50003, 0x24A50000),         # addiu a1, a1, 3 -> addiu a1, a1, 0
    },
}


def patch_overlay(tag, data, base):
    d = bytearray(data)
    for a, (old, new) in OVERLAY_PATCHES.get(tag, {}).items():
        o = a - base
        cur = struct.unpack_from('<I', d, o)[0]
        if cur != old:
            raise ValueError('%s %#x: expected %08x, found %08x' % (tag, a, old, cur))
        struct.pack_into('<I', d, o, new)
    return bytes(d)


def stub(orig_entry, blobs):
    """Entry stub: copy each (src in the exe image, dst, len) blob, FlushCache, jump on."""
    src = ''
    for n, (a, d, ln) in enumerate(blobs):
        src += """
    la t0, %d
    la t1, %d
    li t2, %d
copy%d:
    lw t3, 0(t0)
    addiu t0, t0, 4
    sw t3, 0(t1)
    addiu t2, t2, -4
    bgtz t2, copy%d
    addiu t1, t1, 4
""" % (a, d, (ln + 3) & ~3, n, n)
    src += """
    li t2, 0xA0          ; BIOS A(44h) FlushCache: the copied code is safe to run
    jalr t2
    li t1, 0x44
    la t0, %d
    jr t0
    nop
""" % orig_entry
    return src


CAVE_FREE = None      # first free byte after the VWF cave (set by build_cave users)


def patch_exe(exe, extra=()):
    """Return the patched exe bytes (cave + extra blobs appended, entry stub, header updated).
    extra: [(dst address in kernel RAM, bytes)] copied at boot next to the cave."""
    exe = bytearray(exe)
    base = struct.unpack_from('<I', exe, 0x18)[0]
    tsize = struct.unpack_from('<I', exe, 0x1C)[0]
    entry = struct.unpack_from('<I', exe, 0x10)[0]
    if struct.unpack_from('<I', exe, 0x800+0x8004D7AC-base)[0] != 0x8F830240:
        raise ValueError('Unexpected native glyph-width hook instruction')
    import dialogue_font
    import command_layout
    exe = bytearray(command_layout.patch_core(dialogue_font.patch_core(exe)))
    cave, labels = build_cave()
    for a, ins in exe_patches(labels).items():
        struct.pack_into('<I', exe, 0x800 + a - base, ins)
    m = ascii_map()
    for c in range(0x20, 0x7F):
        struct.pack_into('<H', exe, 0x800 + ASCII_TABLE - base + (c - 0x20) * 2, m[c])
    img = bytearray(exe[0x800:0x800 + tsize])
    blobs = []
    secondary, _ = build_secondary_font(labels)
    dialogue_blobs, _, _ = dialogue_font.assemble()
    command_code, _ = command_layout.assemble()
    assert dialogue_font.RASTER+len(dialogue_blobs[2][1]) <= command_layout.START
    assert CAVE+len(cave) <= dialogue_font.CHAR
    assert SECONDARY_CAVE+len(secondary) <= dialogue_font.WINDOW
    for dst, data in [(CAVE, cave), (SECONDARY_CAVE, secondary)] + dialogue_blobs + [(command_layout.START, command_code)] + list(extra):
        while len(img) % 4:
            img += b'\x00'
        blobs.append((base + len(img), dst, len(data)))
        img += data
    while len(img) % 16:
        img += b'\x00'
    stub_addr = base + len(img)
    sc, _ = masm.assemble(stub(entry, blobs), stub_addr)
    img += sc
    while len(img) % 2048:
        img += b'\x00'
    out = exe[:0x800] + img
    struct.pack_into('<I', out, 0x10, stub_addr)
    struct.pack_into('<I', out, 0x1C, len(img))
    return bytes(out), labels


if __name__ == '__main__':
    cave, labels = build_cave()
    print('cave %#x bytes, ends %#x' % (len(cave), CAVE + len(cave)))
    for k in ('width', 'drawadv', 'dlgadv', 'colsj', 'cola', 'strlen', 'strpx', 'WA', 'W82'):
        print('  %-8s %#x' % (k, labels[k]))
    m = ascii_map()
    print(' '.join('%s=%04x' % (chr(c), m[c]) for c in sorted(m)))
