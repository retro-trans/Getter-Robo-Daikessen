"""Debug aid: set the HP of every enemy unit record to 1 (unit table 0x800FF800, 0x80 per
record, max HP +0x30, HP +0x34). Allies are recognised by their max HP (map 1 roster)."""
import os
import struct
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gdbmem import Gdb      # noqa: E402
ALLY_MAX = {883, 769, 937, 1133, 829, 1800, 1880}
g = Gdb()
try:
    d = g.read(0x800FF800, 0x500)
    for k in range(0, 0x500, 0x80):
        mx, hp = struct.unpack_from('<II', d, k + 0x30)
        if 0 < mx < 100000 and 0 < hp <= mx and mx not in ALLY_MAX:
            g.write(0x800FF800 + k + 0x34, (1).to_bytes(4, 'little'))
            print('enemy record %08X: %d/%d -> 1' % (0x800FF800 + k, hp, mx))
finally:
    g.s.sendall(b'$c#63')
    g.close()
