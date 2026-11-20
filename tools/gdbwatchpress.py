"""Press a button every N frames while watching a memory word for writes (debug aid).

    python tools/gdbwatchpress.py <addr hex> [presses=60] [frames=45] [button=circle]

Logs every write (pc, ra, value); stops when text (4 printable bytes) is written.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gdbdbg import Dbg, BTN, PAD_REG     # noqa: E402

addr = int(sys.argv[1], 16)
presses = int(sys.argv[2]) if len(sys.argv) > 2 else 60
frames = int(sys.argv[3]) if len(sys.argv) > 3 else 45
btn = BTN[sys.argv[4] if len(sys.argv) > 4 else 'circle']
d = Dbg()
d.g.s.settimeout(600)
assert d.g.cmd('Z2,%x,4' % addr) == 'OK'
done = False
try:
    for p in range(presses):
        for f in range(frames + 3):
            while True:
                d.g.s.sendall(b'$c#63')
                d.g._recv_packet()
                r = d.regs()
                if r[37] == d.bp and r[5] == r[29]:
                    if f < 3:
                        d.setreg(PAD_REG, r[PAD_REG] | btn)
                    break
                if r[37] != d.bp:
                    v = d.g.read(addr, 4)
                    txt = all(0x20 <= c < 0x7F for c in v)
                    print('press %d pc=%08x ra=%08x val=%s %r a0=%08x a1=%08x a2=%08x s0=%08x s1=%08x s2=%08x'
                          % (p, r[37], r[31], v.hex(), v if txt else b'', r[4], r[5], r[6], r[16], r[17], r[18]), flush=True)
                    if txt:
                        done = True
                        break
            if done:
                break
        if done:
            break
finally:
    d.g.cmd('z2,%x,4' % addr)
    d.g.cmd('z0,%x,4' % d.bp)
    d.g.s.sendall(b'$c#63')
    d.g.close()
print('end')
