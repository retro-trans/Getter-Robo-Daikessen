"""Log writes to a memory word (GDB write watchpoint, debug aid).

    python tools/gdbwatch.py <addr hex> [hits=50] [len=4]

For every write: pc, ra, the new value, and the registers a0-a3. Stops early when the new
value looks like text (four printable bytes), which is what a string overrun leaves.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gdbmem import Gdb      # noqa: E402
from gdbhits import regs    # noqa: E402


def main():
    addr = int(sys.argv[1], 16)
    hits = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    ln = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    g = Gdb()
    g.s.settimeout(3600)
    try:
        assert g.cmd('Z2,%x,%x' % (addr, ln)) == 'OK'
        for k in range(hits):
            g.s.sendall(b'$c#63')
            g._recv_packet()
            r = regs(g)
            v = g.read(addr, ln)
            txt = all(0x20 <= c < 0x7F for c in v)
            print('%3d pc=%08x ra=%08x val=%s %r a0=%08x a1=%08x a2=%08x a3=%08x s0=%08x s1=%08x'
                  % (k, r[37], r[31], v.hex(), v if txt else b'', r[4], r[5], r[6], r[7], r[16], r[17]),
                  flush=True)
            if txt:
                print('text written -> stop')
                break
        g.cmd('z2,%x,%x' % (addr, ln))
    finally:
        g.s.sendall(b'$c#63')
        g.close()


if __name__ == '__main__':
    main()
