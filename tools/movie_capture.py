"""Capture both native 24-bit movie framebuffers through the project GDB link.

    py -3.11 tools/movie_capture.py C04 --out work/ui/movies/v014/C04 --apply

Attach during fresh boot, before the first movie launcher call. Redirect just that
call to an existing movie-table entry, then stop at the movie main-loop display
point. Use StoreImage/DrawSync from the main thread, preserving scratch memory and
registers, as in debug_tools_guide.md. No disc/executable changes are made.
"""
import argparse
from pathlib import Path
import struct
import sys
import time

sys.path.insert(0,str(Path(__file__).resolve().parent))
import gdbdbg
from movie_preview import MOVIES

LAUNCH = 0x8004E9D4
DISPLAY = 0x8004F028


def stop_at(d,address):
    d.g.cmd(f'Z0,{address:x},4')
    while True:
        d.g.s.sendall(b'$c#63');d.g._recv_packet()
        if d.regs()[37]==address:
            return


def grab(d,x,y,w,h):
    pieces=[]
    for yy in range(y,y+h,3):
        rows=min(3,y+h-yy)
        registers=d.regs()
        saved=d.g.read(gdbdbg.SCRATCH,16+w*rows*2)
        saved_stub=d.g.read(gdbdbg.STUB,32)
        jal=lambda addr:0x0C000000|((addr>>2)&0x3ffffff)
        stub=[jal(gdbdbg.STOREIMAGE),0,jal(gdbdbg.DRAWSYNC),0x00002021,0]
        end=gdbdbg.STUB+16
        try:
            d.g.write(gdbdbg.STUB,struct.pack('<5I',*stub))
            d.g.write(gdbdbg.SCRATCH,struct.pack('<4h',x,yy,w,rows))
            d.setreg(4,gdbdbg.SCRATCH);d.setreg(5,gdbdbg.SCRATCH+16)
            d.setreg(37,gdbdbg.STUB)
            stop_at(d,end)
            pieces.append(d.g.read(gdbdbg.SCRATCH+16,w*rows*2))
        finally:
            d.g.cmd(f'z0,{end:x},4')
            d.g.write(gdbdbg.SCRATCH,saved);d.g.write(gdbdbg.STUB,saved_stub)
            for i in list(range(1,32))+[33,34,37]:
                d.setreg(i,registers[i])
    return b''.join(pieces)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('movie',choices=MOVIES)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--ticks',type=int,default=120)
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    print('Native movie',args.movie,'after',args.ticks,'display-loop ticks ->',args.out,flush=True)
    if not args.apply:return
    from PIL import Image
    d=None
    for attempt in range(20):
        try:
            d=gdbdbg.Dbg();break
        except ConnectionRefusedError:
            time.sleep(.25)
    if d is None:raise ConnectionError('Project emulator GDB link did not start')
    d.g.s.settimeout(45)
    try:
        d.g.cmd(f'z0,{d.bp:x},4')
        stop_at(d,LAUNCH)
        d.setreg(4,MOVIES[args.movie]);d.g.cmd(f'z0,{LAUNCH:x},4')
        for _ in range(args.ticks):stop_at(d,DISPLAY)
        d.g.cmd(f'z0,{DISPLAY:x},4')
        args.out.parent.mkdir(parents=True,exist_ok=True)
        for y in [0,240]:
            rgb=grab(d,0,y,480,240)
            path=args.out.with_name(args.out.name+f'_fb{y}.png')
            Image.frombytes('RGB',(320,240),rgb).save(path)
            print(path,flush=True)
    finally:
        d.g.cmd(f'z0,{LAUNCH:x},4');d.g.cmd(f'z0,{DISPLAY:x},4');d.close()


if __name__=='__main__':main()
