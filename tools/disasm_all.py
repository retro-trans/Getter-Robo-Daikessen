"""Disassemble a PS-X EXE or a raw overlay to a text file.

python tools/disasm_all.py <file> <out.txt> [--base 0x80xxxxxx]   (raw overlay needs --base)
"""
import struct, sys, capstone
src, out = sys.argv[1], sys.argv[2]
d = open(src, 'rb').read()
if d[:8] == b'PS-X EXE':
    base = struct.unpack_from('<I', d, 0x18)[0]; body = d[0x800:]
else:
    base = int(sys.argv[sys.argv.index('--base') + 1], 16); body = d
md = capstone.Cs(capstone.CS_ARCH_MIPS, capstone.CS_MODE_MIPS32 + capstone.CS_MODE_LITTLE_ENDIAN)
with open(out, 'w') as f:
    for i in range(0, len(body) - 3, 4):
        w = struct.unpack_from('<I', body, i)[0]
        ins = list(md.disasm(body[i:i + 4], base + i))
        t = f'{ins[0].mnemonic} {ins[0].op_str}' if ins else f'.word 0x{w:08x}'
        f.write(f'{base + i:08x}: {w:08x}  {t}\n')
