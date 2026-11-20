"""Switch the running game to another program (debug aid).

    python tools/gdbprog.py <id> [param]     next program switch runs program <id>

Every program change goes through the dispatcher 0x8004CF48(a0 = program id, a1 = param),
jump table 0x800113D4 (id -1..11). Ids: 0 battle (+game), 1 = 0x8005DB30 (+game/battle),
2 debug menu (bin/debug.bin, "RUN PROGRAM"), 3 = 0x80053750, 4 / 5 exe programs,
6 title, 7 = 0x8004EA6C, 8 game, 9 flight minigame, 10 = 0x8004E320.
The tool waits for the next call of the dispatcher (e.g. leave the title screen or let the
intro movie end), rewrites a0 / a1 and resumes.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gdbmem import Gdb      # noqa: E402

DISPATCH = 0x8004CF48


def main():
    pid = int(sys.argv[1], 0)
    param = int(sys.argv[2], 0) if len(sys.argv) > 2 else None
    g = Gdb()
    try:
        g.cmd('Z0,%x,4' % DISPATCH)
        g.s.settimeout(600)
        g.s.sendall(b'$c#63')
        g._recv_packet()
        g.s.settimeout(10)
        g.cmd('P4=' + pid.to_bytes(4, 'little', signed=True).hex())
        if param is not None:
            g.cmd('P5=' + param.to_bytes(4, 'little', signed=True).hex())
        g.cmd('z0,%x,4' % DISPATCH)
        g.s.sendall(b'$c#63')
    finally:
        g.close()
    print('program ->', pid)


if __name__ == '__main__':
    main()
