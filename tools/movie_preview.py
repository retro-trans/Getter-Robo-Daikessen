"""Select a movie at the next native game-program dispatch (debug aid only).

    py -3.11 tools/movie_preview.py C04 [--apply]

Without --apply, prints the target. Requires the project DuckStation on GDB port
2351. Does not patch the game executable or disc. Start from a fresh boot; the
next dispatch runs native program 7 with its original movie-table index.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gdbmem import Gdb

MOVIES = {'CG1':1,'CG2':2, **{f'C{i:02d}':i+9 for i in range(1,17)}}
DISPATCH = 0x8004CF48


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('movie', choices=MOVIES)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(f'{args.movie}: native program 7, movie table index {MOVIES[args.movie]}', flush=True)
    if not args.apply:
        return
    g = Gdb()
    try:
        g.cmd(f'Z0,{DISPATCH:x},4')
        g.s.settimeout(45)
        g.s.sendall(b'$c#63')
        g._recv_packet()
        g.s.settimeout(10)
        g.cmd('P4='+(7).to_bytes(4,'little').hex())
        g.cmd('P5='+MOVIES[args.movie].to_bytes(4,'little').hex())
    finally:
        try:
            g.s.settimeout(10)
            g.cmd(f'z0,{DISPATCH:x},4')
            g.s.sendall(b'$c#63')
        finally:
            g.close()


if __name__ == '__main__':
    main()
