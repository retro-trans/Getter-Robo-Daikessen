"""Capture native menu layouts in the muted project emulator; dry-run default."""
import argparse
import json
from pathlib import Path
import struct

import build
import gdbdbg
import menu_layout


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apply', action='store_true')
    p.add_argument('--hotpatch', choices=['flight','briefing'])
    p.add_argument('--script', default='')
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    print('Native menu capture; drawing reload:', args.hotpatch, 'buttons:', args.script, flush=True)
    if not args.apply: return
    args.out.mkdir(parents=True, exist_ok=True)
    d = gdbdbg.Dbg(); g = d.g; g.s.settimeout(45)
    try:
        if args.hotpatch:
            g.cmd(f'z0,{d.bp:x},4')
            g.cmd(f'Z0,{gdbdbg.DRAWSYNC:x},4')
            while True:
                g.s.sendall(b'$c#63'); g._recv_packet(); r = d.regs()
                if r[37] == gdbdbg.DRAWSYNC and r[32]&5 and 0x80010000 <= r[29]<0x80200000: break
            g.cmd(f'z0,{gdbdbg.DRAWSYNC:x},4')
            base = menu_layout.FLIGHT_BASE if args.hotpatch == 'flight' else menu_layout.BRIEF_BASE
            data = Path(f'work/build/{args.hotpatch}_v083.bin').read_bytes()
            old = build.vfs_file(Path('work/build/GR.VFS').read_bytes(), f'bin/{args.hotpatch}.bin')
            stack = struct.unpack('<64I', g.read(r[29],256))
            if args.hotpatch == 'briefing' and any(0x800B903C<=ra<0x800B90FC or menu_layout.CODE<=ra<menu_layout.LIMIT for ra in (r[31],*stack)):
                raise ValueError('A menu text wrapper is active; reload from the briefing menu')
            if g.read(base,32) != old[:32]: raise ValueError('Expected overlay is not loaded')
            for offset in range(0,len(data),4):
                if data[offset:offset+4] != old[offset:offset+4]:g.write(base+offset,data[offset:offset+4])
            g.cmd(f'Z0,{d.bp:x},4')
        for command in args.script.split(';'):
            words = command.strip().split()
            if not words:continue
            if words[0]=='press':d.press(words[1],int(words[2]) if len(words)>2 else 4)
            elif words[0]=='wait':d.wait(int(words[1]))
            else:raise ValueError(command)
        d.wait(10)
        mode = struct.unpack('<I',g.read(0x80089AA4,4))[0]
        w,h = struct.unpack('<2H',g.read(0x800111A8+mode*4,4))
        if (w,h) not in ((512,480),(320,240)):raise ValueError(f'Unexpected native menu mode: {w}x{h}')
        gdbdbg.write_png(str(args.out/'screen.png'),w,h,d.grab(0,0,w,h))
        from PIL import Image
        Image.open(args.out/'screen.png').resize((640,480),Image.Resampling.NEAREST).save(args.out/'screen_4x3.png')
        (args.out/'native.json').write_text(json.dumps(dict(mode=mode,native_size=[w,h],hotpatch=args.hotpatch,buttons=args.script),indent=2)+'\n')
        print('Captured',args.out,flush=True)
    finally:
        g.cmd(f'z0,{gdbdbg.DRAWSYNC:x},4')
        d.close()


if __name__=='__main__':main()
