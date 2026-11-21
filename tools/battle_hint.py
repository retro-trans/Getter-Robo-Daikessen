"""Add a transparent native battle skip hint; dry run unless --apply."""
import argparse
import json
from pathlib import Path
import struct

import masm
import vwf

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x800A97A8
ORIGINAL_SIZE = 299728
CODE = 0x800F2A80
CALLBACK = 0x800F1D00
DRAW = 0x800AC968
TEXT = 'press START to skip'
FLAGS = 0x2200000F  # Existing proportional 16x10 mode: normal at 512x240.
RIGHT = 504
Y = 226


def layout():
    widths, _ = vwf.width_tables()
    advance = (0,1,3,4,5,7,8,9,11,12,13,15,16)
    width = sum(advance[widths[ord(c)-32]] for c in TEXT)
    assert 0 < width < 200
    return dict(text=TEXT, x=RIGHT-width, y=Y, width=width, height=10,
                viewport=[512, 240], right_margin=8, bottom_margin=4,
                flags=hex(FLAGS), background='transparent')


def assemble():
    row = layout()
    source = f'''
battle_hint_draw:
addiu sp, sp, -0x28
sw ra, 0x24(sp)
sw s0, 0x20(sp)
move s0, a0
jal {DRAW}
nop
sw v0, 0x1C(sp)
sw v1, 0x18(sp)
lw s0, 0x30(s0)
nop
hint_visibility_start:
; Same visible/not-paused guard as the native battle renderer and update.
lhu t0, 0x7F0(s0)
li t1, 1
andi t0, t0, 3
bne t0, t1, hint_return
nop
lb t0, 0x7F4(s0)
li t1, 2
bne t0, t1, hint_return
nop
; Phase 0 initializes the scene; 17 fast-finishes it, 18+ cleans it up.
lh t0, 0x62C(s0)
nop
addiu t0, t0, -1
sltiu t0, t0, 16
beqz t0, hint_return
nop
hint_visible_pass:
; Anchor to the current native display mode (battle is normally 512x240).
li t0, 0x80089AA4
lw t0, 0(t0)
nop
sll t0, t0, 2
li t1, 0x800111A8
addu t1, t1, t0
lhu a0, 0(t1)
lhu a1, 2(t1)
addiu a0, a0, -{row['width']+8}
addiu a1, a1, -{row['height']+4}
la a2, hint_text
li a3, {FLAGS}
jal 0x8004DDFC
nop
; Native lists prepend primitives. Queue full-screen origin/clip resets last
; so they execute before the hint, above all battle-world/HUD primitives.
li t0, 0x80089A8C
lw a0, 0(t0)
nop
addiu a0, a0, 60
jal 0x8003BA5C
move a1, zero
li t0, 0x80089A8C
lw a0, 0(t0)
nop
addiu a0, a0, 60
jal 0x8003BBDC
move a1, zero
hint_return:
lw v0, 0x1C(sp)
lw v1, 0x18(sp)
lw s0, 0x20(sp)
lw ra, 0x24(sp)
jr ra
addiu sp, sp, 0x28
hint_text:
.ascii {json.dumps(TEXT)}
.byte 0
.align 4
'''
    code, labels = masm.assemble(source, CODE)
    assert CODE + len(code) < 0x800F87A8, 'Overlaps map overlay'
    return code, labels


def patch_overlay(data):
    data = bytearray(data)
    assert len(data) == ORIGINAL_SIZE, 'Expected original-sized translated battle overlay'
    assert struct.unpack_from('<I', data, CALLBACK-BASE)[0] == DRAW
    # The existing native skip patch must already be present.
    assert struct.unpack_from('<I', data, 0x800AE00C-BASE)[0] == 0
    code, labels = assemble()
    data.extend(bytes(CODE-BASE-len(data)))
    data.extend(code)
    struct.pack_into('<I', data, CALLBACK-BASE, labels['battle_hint_draw'])
    return bytes(data)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    import ui_text
    images, _, problems = ui_text.apply(log=lambda *a: None)
    assert not problems
    data = vwf.patch_overlay('battle', images['battle'], BASE)
    patched = patch_overlay(data)
    print(json.dumps(dict(layout=layout(), bytes_before=len(data), bytes_after=len(patched),
                         code_end=hex(BASE+len(patched))), indent=2))
    if a.apply:
        (ROOT/'work/build/battle_hint_preview.bin').write_bytes(patched)


if __name__ == '__main__':
    main()
