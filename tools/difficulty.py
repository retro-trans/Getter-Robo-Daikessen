"""Native new-game difficulty menu and saved Easy level rules (dry run default)."""
import argparse
import json
from pathlib import Path
import struct

import masm
import title_credit
import vwf

ROOT = Path(__file__).resolve().parents[1]
BASE = title_credit.BASE
TITLE_CODE = 0x80093400
# After the debug StoreImage stub (ends DC20), before preview scratch DD00.
# E000..E6FF is BIOS thread/exception storage and MUST NOT hold injected code.
RESIDENT = 0x8000DC40
EASY_BIT = 0x8000  # unused bit of the existing serialized player flags
TITLE_TEXT = [('DIFFICULTY', 171, 0x3205000F),
              ('Normal', 220, 0x3200000F), ('Easy', 252, 0x3200000F),
              ('Circle / Start: Confirm', 340, 0x3400000F),
              ('Cross: Back', 359, 0x3400000F)]


def text_x(text, flags):
    wa, _ = vwf.width_tables()
    scale = ((0, 1, 3, 4, 5, 7, 8, 9, 11, 12, 13, 15, 16)
             if flags >> 24 == 0x32 else (0, 1, 2, 3, 4, 5, 6, 6, 7, 8, 9, 10, 11))
    return (512 - sum(scale[wa[ord(c)-32]] for c in text)) // 2

CORE_ASM = r'''
; s4 is the pilot manager; t0 is the pilot record in AwardExperience.
; t8/t9 are caller-scratch and not live at the hook. Keep a2 and t0 intact.
level_limit:
lw t8, 0(s4)
nop
lhu t8, 8(t8)
li t9, 40
andi t8, t8, 0x8000
beqz t8, limit_ready
nop
li t9, 99
limit_ready:
lh v0, 6(t0)
jr ra
nop

; Native player-record initialization, including name/sex/skill, continues.
; A jump (not jal) preserves this leaf function's original return address.
init_difficulty:
la t8, pending_easy
lw t8, 0(t8)
andi v0, v0, 0x7FFF
or v0, v0, t8
sh v0, 0(a0)
j 0x8005D69C
sb a3, 0x110(a0)

; Chapter preparation normally sets all continuing pilots to a stage level.
; Easy retains both their earned level and partial EXP if already at/above it.
; Newly joined pilots still receive the native starting level.
stage_level:
lw t8, 0(a0)
nop
lhu t9, 8(t8)
nop
andi t9, t9, 0x8000
beqz t9, native_stage_level
nop
sll v0, a1, 3
subu v0, v0, a1
sll v0, v0, 2
addu t8, t8, v0
lh t9, 0x152(t8)
nop
slt t9, t9, a2
bnez t9, native_stage_level
nop
jr ra
nop
native_stage_level:
j 0x8005CE84
nop
.align 4
pending_easy:
.word 0
'''


def resident():
    code, labels = masm.assemble(CORE_ASM, RESIDENT)
    assert RESIDENT + len(code) <= 0x8000DD00
    return code, labels


def patch_core(exe):
    """Apply to the UI-patched original EXE before vwf.patch_exe boot packing."""
    out = bytearray(exe)
    base = struct.unpack_from('<I', out, 0x18)[0]
    _, labels = resident()
    changes = {
        0x8005D320: (0x85020006, vwf.jal(labels['level_limit'])),
        0x8005D324: (0, 0),
        0x8005D328: (0x28420028, 0x0059102A),  # slt v0,v0,t9
        0x8005D694: (0xA4820000, vwf.j(labels['init_difficulty'])),
        0x8005D698: (0xA0870110, 0),
        0x800566C4: (vwf.jal(0x8005CE84), vwf.jal(labels['stage_level'])),
    }
    for addr, (old, new) in changes.items():
        off = 0x800 + addr - base
        actual = struct.unpack_from('<I', out, off)[0]
        assert actual == old, (hex(addr), hex(actual), hex(old))
        struct.pack_into('<I', out, off, new)
    return bytes(out)


def title_assemble():
    _, core = resident()
    source = f'''
difficulty_update:
addiu sp, sp, -0x28
sw ra, 0x24(sp)
sw s0, 0x20(sp)
sw s1, 0x1C(sp)
sw s2, 0x18(sp)
move s0, a0
lw s1, 0x30(s0)
la t0, modal_open
lw s2, 0(t0)
nop
bnez s2, modal_input
nop
lw t0, 0x34(s1)
li t1, 5
bne t0, t1, native_update
nop
lw t0, 0x18(s1)
nop
bnez t0, native_update
nop
lw t0, 4(s1)
nop
lui t1, 2
and t0, t0, t1
beqz t0, native_update
nop
move a0, zero
jal 0x80029F9C
li a1, 1
andi t0, v0, 0x820
beqz t0, native_update
nop
la t0, modal_open
li t1, 1
sw t1, 0(t0)
sw zero, 4(t0)
sw zero, 0x1C(s1)
b update_return
move v0, zero
native_update:
jal 0x8008C4E8
move a0, s0
b update_return
nop
modal_input:
move a0, zero
jal 0x80029F9C
li a1, 1
move s2, v0
andi t0, s2, 0x40
bnez t0, modal_cancel
nop
andi t0, s2, 0xF000
beqz t0, modal_confirm
nop
la t0, modal_choice
lw t1, 0(t0)
nop
xori t1, t1, 1
sw t1, 0(t0)
jal 0x8002ECB4
li a0, 0x2E7
modal_confirm:
andi t0, s2, 0x820
beqz t0, modal_idle
nop
la t0, modal_choice
lw t1, 0(t0)
la t0, {core['pending_easy']}
sll t1, t1, 15
sw t1, 0(t0)
la t0, modal_open
sw zero, 0(t0)
; The original confirm/cleanup sequence at CC80..CCAC, once per new game.
jal 0x8002ECB4
li a0, 0x2E8
jal 0x8001E888
move a0, zero
jal 0x8002EBF4
li a0, 1
jal 0x8002EDF8
nop
jal 0x8002EC80
nop
jal 0x8003D958
li a0, 1
li t0, 6
sw t0, 0x34(s1)
sw zero, 0x10(s1)
b modal_idle
nop
modal_cancel:
la t0, modal_open
sw zero, 0(t0)
jal 0x8002ECB4
li a0, 0x2E9
modal_idle:
sw zero, 0x1C(s1)
move v0, zero
update_return:
lw s2, 0x18(sp)
lw s1, 0x1C(sp)
lw s0, 0x20(sp)
lw ra, 0x24(sp)
jr ra
addiu sp, sp, 0x28

difficulty_draw:
addiu sp, sp, -0x28
sw ra, 0x24(sp)
jal {title_credit.START}
nop
sw v0, 0x20(sp)
sw v1, 0x1C(sp)
la t0, modal_open
lw t0, 0(t0)
nop
beqz t0, draw_return
nop
la t0, modal_choice
lw t0, 0(t0)
la a0, select_rect
sll t0, t0, 5
addiu t0, t0, 216
sh t0, 2(a0)
la a1, select_color
jal modal_rectangle
nop
; The native OT prepends primitives: emit the panel after the highlight so
; the GPU draws the panel first and the highlight over it.
la a0, modal_rect
la a1, modal_color
jal modal_rectangle
nop
'''
    for text, y, flags in TITLE_TEXT:
        x = text_x(text, flags)
        label = 'text_' + str(y)
        source += f'li a0, {x}\nli a1, {y}\nla a2, {label}\nli a3, {flags}\njal 0x8004DDFC\nnop\n'
    source += '''
la t0, modal_choice
lw t0, 0(t0)
la a2, normal_description
li a0, 163
beqz t0, description_ready
nop
la a2, easy_description
li a0, 157
description_ready:
li a1, 302
li a3, 0x3400000F
jal 0x8004DDFC
nop
; Full-screen drawing environment at foremost OT, same native title helper.
li t0, 0x80089A8C
lw a0, 0(t0)
nop
addiu a0, a0, 60
jal 0x8003BBDC
move a1, zero
draw_return:
lw v0, 0x20(sp)
lw v1, 0x1C(sp)
lw ra, 0x24(sp)
jr ra
addiu sp, sp, 0x28
modal_rectangle:
li t0, 0x80089A8C
lw a3, 0(t0)
nop
addiu a3, a3, 56
j 0x8004BE74
move a2, zero
.align 4
modal_open:
.word 0
modal_choice:
.word 0
modal_rect:
.half 104, 146, 304, 236
select_rect:
.half 144, 216, 224, 28
modal_color:
.byte 20, 28, 68, 0
select_color:
.byte 35, 109, 82, 0
normal_description:
.ascii "Original stage levels and level cap."
.byte 0
easy_description:
.ascii "Keep earned levels. Maximum level: 99."
.byte 0
'''
    for text, y, flags in TITLE_TEXT:
        source += f'text_{y}:\n.ascii {json.dumps(text)}\n.byte 0\n'
    source += '.align 4\n'
    code, labels = masm.assemble(source, TITLE_CODE)
    assert TITLE_CODE + len(code) < 0x80094000
    return code, labels


def patch_title(data):
    code, labels = title_assemble()
    data = bytearray(data)
    assert len(data) <= TITLE_CODE - BASE
    assert struct.unpack_from('<I', data, 0x10)[0] == 0x8008C4E8
    assert struct.unpack_from('<I', data, 0x14)[0] == title_credit.START
    data.extend(bytes(TITLE_CODE - BASE - len(data)))
    data.extend(code)
    struct.pack_into('<I', data, 0x10, labels['difficulty_update'])
    struct.pack_into('<I', data, 0x14, labels['difficulty_draw'])
    return bytes(data)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    import ui_text
    images, blobs, problems = ui_text.apply(log=lambda *a: None)
    assert not problems
    core = patch_core(images['exe'])
    code, labels = resident()
    core, _ = vwf.patch_exe(core, blobs + [(RESIDENT, code)])
    title = vwf.patch_overlay('title', images['title'], BASE)
    version = (ROOT/'work/version.txt').read_text().strip()
    title = patch_title(title_credit.patch_overlay(title, version))
    _, tl = title_assemble()
    print(json.dumps(dict(resident_bytes=len(code), resident_end=hex(RESIDENT+len(code)),
                         core_bytes=len(core), title_bytes=len(title),
                         labels={k: hex(v) for k, v in {**labels, **tl}.items()},
                         normal_cap=40, easy_cap=99, preserve_earned_levels_between_stages=True), indent=2))
    if a.apply:
        (ROOT/'work/build/SLPS_022.32').write_bytes(core)
        (ROOT/'work/build/title_preview.bin').write_bytes(title)


if __name__ == '__main__':
    main()
