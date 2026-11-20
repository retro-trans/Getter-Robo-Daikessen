"""Press a button repeatedly until the game draws a given string (debug aid).

    python tools/gdbuntil.py "<text>" [button=circle] [max presses=200] [frames between=45]

After each press it watches the string drawer (0x8004DE34) for the frames between presses;
it stops (without pressing again) as soon as a drawn string contains <text>.
Prints how many presses it took. Use it to skip dialogue up to a known prompt.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gdbdbg import Dbg      # noqa: E402

DRAW = 0x8004DE34


def seen(d, text, frames):
    d.g.cmd('Z0,%x,4' % DRAW)
    try:
        n = 0
        while n < frames:
            d.g.s.sendall(b'$c#63')
            d.g._recv_packet()
            r = d.regs()
            if r[37] == DRAW:
                p = r[6]
                if 0x80000000 <= p < 0x80200000:
                    s = d.g.read(p, 64).split(b'\0')[0].decode('cp932', 'replace')
                    if text in s:
                        return s
            elif r[37] == d.bp and r[5] == r[29]:
                n += 1
    finally:
        d.g.cmd('z0,%x,4' % DRAW)
    return None


def main():
    text = sys.argv[1]
    btn = sys.argv[2] if len(sys.argv) > 2 else 'circle'
    mx = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    fr = int(sys.argv[4]) if len(sys.argv) > 4 else 45
    d = Dbg()
    try:
        s = seen(d, text, 10)
        k = 0
        while not s and k < mx:
            d.press(btn, 3)
            k += 1
            s = seen(d, text, fr)
        print('found after %d presses: %s' % (k, s) if s else 'not found after %d presses' % k)
    finally:
        d.g.cmd('z0,%x,4' % d.bp)
        d.g.s.sendall(b'$c#63')
        d.g.close()


if __name__ == '__main__':
    main()
