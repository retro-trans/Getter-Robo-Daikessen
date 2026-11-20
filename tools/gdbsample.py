"""Sample PC/RA by interrupting the CPU N times: python tools/gdbsample.py [n]"""
import os, sys, time, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gdbmem import Gdb
from gdbhits import regs
n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
g = Gdb(); c = collections.Counter()
try:
    for _ in range(n):
        g.s.sendall(b'\x03'); g._recv_packet()
        r = regs(g); c[(r[37] & ~0xff, r[31])] += 1
        g.s.sendall(b'$c#63'); time.sleep(0.05)
finally:
    g.close()
for (pc, ra), k in c.most_common(): print('pc~%08x ra=%08x x%d' % (pc, ra, k))
