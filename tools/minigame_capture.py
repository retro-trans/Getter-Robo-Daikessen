"""Navigate the muted project emulator to native flight training. Dry-run default."""
import argparse
import json
from pathlib import Path
import struct

import gdbdbg
import minigame_subtitles as mini


def capture(apply=False,script='',output=None,tutorial=False):
    print('Native program 9 / standalone training (-1); optional controller script:',script,flush=True)
    if not apply:return
    d=gdbdbg.Dbg();g=d.g;g.s.settimeout(60);active={d.bp}
    def add(at):g.cmd(f'Z0,{at:x},4');active.add(at)
    def remove(at):g.cmd(f'z0,{at:x},4');active.discard(at)
    def until(at):
        add(at)
        while True:
            g.s.sendall(b'$c#63');g._recv_packet();r=d.regs()
            if r[37]==at:remove(at);return r
    target=Path(output or mini.ROOT/'work/ui/minigame/v017');target.mkdir(parents=True,exist_ok=True)
    try:
        remove(d.bp)
        until(0x8004CF48);d.setreg(4,9);d.setreg(5,-1)
        if tutorial:
            r=until(0x800C7574);root=r[4]
            state=struct.unpack('<I',g.read(root+0x30,4))[0]
            # Debug-only standalone user record; bypass the license menu and
            # select the native prototype practice task. No disc/save edits.
            record=bytearray(0x80)
            struct.pack_into('<II',record,0x28,0x44000000,0x80)
            g.write(0x8000DE00,record)
            for offset,value in [(8,0x44000000),(0xc,2),(0x20,0),(0x48,0x8000DE00)]:
                g.write(state+offset,struct.pack('<I',value))
        r=until(0x800C7A54);root=r[4]
        print('Native flight root',hex(root),flush=True)
        add(d.bp);d.wait(90)
        if script:
            for command in script.split(';'):
                words=command.strip().split()
                if not words:continue
                if words[0]=='press':d.press(words[1],int(words[2])if len(words)>2 else 4)
                elif words[0]=='wait':d.wait(int(words[1]))
                else:raise ValueError(command)
        for y,suffix in [(0,'a'),(240,'b')]:gdbdbg.write_png(str(target/f'screen_{suffix}.png'),320,240,d.grab(0,y,320,240))
        (target/'state.json').write_text(json.dumps({'root_task':hex(root),'state':hex(struct.unpack('<I',g.read(root+0x30,4))[0])},indent=2)+'\n')
        print('Captured',target,flush=True)
    finally:
        for at in active:g.cmd(f'z0,{at:x},4')
        d.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');parser.add_argument('--script',default='');parser.add_argument('--output-dir');parser.add_argument('--tutorial',action='store_true');a=parser.parse_args();capture(a.apply,a.script,a.output_dir,a.tutorial)
