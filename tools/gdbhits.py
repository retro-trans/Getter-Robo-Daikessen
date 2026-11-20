"""Count breakpoint hits over N stops: python tools/gdbhits.py <n_stops> <addr> [addr...]
Prints address -> hits and a sample of (ra, a0, a1, v0). Resumes the game afterwards."""
import os, sys, struct, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gdbmem import Gdb

def regs(g):
    r = g.cmd('g')
    while r[:1] in ('S', 'T'):
        r = g.cmd('g')
    return [struct.unpack('<I', bytes.fromhex(r[i*8:i*8+8].replace('x', '0')))[0] for i in range(len(r)//8)]

def main():
    n = int(sys.argv[1]); addrs = [int(a, 16) for a in sys.argv[2:]]
    g = Gdb()
    try:
        g.cmd('?')
        for a in addrs: g.cmd('Z0,%x,4' % a)
        hits = collections.Counter(); sample = {}
        for _ in range(n):
            g.s.sendall(b'$c#63'); g._recv_packet()
            r = regs(g); pc = r[37]
            hits[pc] += 1
            sample.setdefault(pc, (r[31], r[4], r[5], r[2]))
        for a in addrs: g.cmd('z0,%x,4' % a)
        for pc, c in hits.most_common():
            s = sample[pc]
            print('%08x %5d  ra=%08x a0=%08x a1=%08x v0=%08x' % (pc, c, *s))
    finally:
        g.close()
if __name__ == "__main__":
    main()
