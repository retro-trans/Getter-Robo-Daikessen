"""Native title-screen version and translation credit (dry run by default).

Append a small draw wrapper to title.bin and redirect only its draw callback.
No title textures, menus, copyright art or resident font code are replaced.
"""
import argparse
import json
from pathlib import Path
import re
import struct

import masm
import vwf

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x8008B7A8
ORIGINAL_SIZE = 31508
START = 0x800932C0
DRAW = 0x8008CD20
CALLBACK = 0x8008B7BC
RIGHT = 500
CREDIT = 'github.com / retro-trans'
FLAGS = 0x3400000E


def layout(version):
    if not re.fullmatch(r'0\.\d+\.\d+', version):
        raise ValueError('Expected a build version such as 0.8.14')
    wa, _ = vwf.width_tables()
    scale = (0, 1, 2, 3, 4, 5, 6, 6, 7, 8, 9, 10, 11)
    rows = []
    for text, y in [('v' + version, 414), (CREDIT, 430)]:
        width = sum(scale[wa[ord(c) - 32]] for c in text)
        rows.append(dict(text=text, x=RIGHT-width, y=y, width=width, height=13))
    assert all(0 <= r['x'] and r['x']+r['width'] <= 500 and r['y']+13 < 480 for r in rows)
    return rows


def assemble(version):
    rows = layout(version)
    source = '''
credit_draw:
addiu sp, sp, -0x28
sw ra, 0x24(sp)
sw s0, 0x20(sp)
move s0, a0
jal 0x8008CD20
nop
sw v0, 0x18(sp)
sw v1, 0x1C(sp)
lw t0, 0x30(s0)
nop
lw t0, 4(t0)
nop
andi t0, t0, 3
li t1, 3
bne t0, t1, credit_return
nop
'''
    for i, row in enumerate(rows):
        source += f"li a0, {row['x']}\nli a1, {row['y']}\nla a2, credit_text_{i}\nli a3, {FLAGS}\njal 0x8004DDFC\nnop\n"
    source += '''
li t0, 0x80089A8C
lw a0, 0(t0)
nop
addiu a0, a0, 56
jal 0x8003BBDC
move a1, zero
credit_return:
lw v0, 0x18(sp)
lw v1, 0x1C(sp)
lw s0, 0x20(sp)
lw ra, 0x24(sp)
jr ra
addiu sp, sp, 0x28
'''
    for i, row in enumerate(rows):
        source += f'credit_text_{i}:\n.ascii "{row["text"]}"\n.byte 0\n'
    source += '.align 4\n'
    code, labels = masm.assemble(source, START)
    assert len(code) <= 512
    return code, labels


def patch_overlay(data, version):
    data = bytearray(data)
    assert len(data) >= ORIGINAL_SIZE
    callback = struct.unpack_from('<I', data, CALLBACK-BASE)[0]
    assert callback in (DRAW, START), hex(callback)
    if len(data) > ORIGINAL_SIZE:
        assert callback == START, 'Unexpected data beyond original title overlay'
    code, _ = assemble(version)
    data = data[:ORIGINAL_SIZE]
    data.extend(bytes(START-BASE-len(data)))
    data.extend(code)
    struct.pack_into('<I', data, CALLBACK-BASE, START)
    return bytes(data)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version', default=(ROOT/'work/version.txt').read_text().strip())
    p.add_argument('--input', type=Path, default=ROOT/'work/source/vfs/bin/title.bin')
    p.add_argument('--output', type=Path, default=ROOT/'work/build/title_preview.bin')
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    patched = patch_overlay(a.input.read_bytes(), a.version)
    print(json.dumps(dict(version=a.version, rows=layout(a.version), overlay_bytes=len(patched), wrapper_bytes=len(assemble(a.version)[0]), end=hex(BASE+len(patched))), indent=2))
    if a.apply:
        a.output.parent.mkdir(parents=True, exist_ok=True)
        a.output.write_bytes(patched)


if __name__ == '__main__':
    main()
