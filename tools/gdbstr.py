"""Log calls to the string drawer: python tools/gdbstr.py [n_hits] [addr=8004de34]
Prints caller (ra), x, y, string pointer and the string (to work/source/scan/strcalls.txt, UTF-8)."""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gdbmem import Gdb
from gdbhits import regs
n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
addr = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x8004DE34
g = Gdb(); out = []
try:
    g.cmd('Z0,%x,4' % addr)
    for _ in range(n):
        g.s.sendall(b'$c#63'); g._recv_packet()
        r = regs(g)
        p = r[6]
        s = g.read(p, 96) if 0x80000000 <= p < 0x80200000 else b''
        s = s.split(b'\0')[0]
        out.append('ra=%08x x=%d y=%d a3=%x ptr=%08x  %s' % (r[31], r[4] & 0xffff, r[5] & 0xffff, r[7], p, s.decode('cp932', 'replace')))
    g.cmd('z0,%x,4' % addr)
finally:
    g.close()
seen = []
for l in out:
    if l not in seen: seen.append(l)
open(os.path.join('work', 'source', 'scan', 'strcalls.txt'), 'w', encoding='utf-8').write('\n'.join(seen) + '\n')
print(len(out), 'calls,', len(seen), 'unique')
