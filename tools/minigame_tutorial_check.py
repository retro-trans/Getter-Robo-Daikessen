"""Capture real tutorial speech order in a running native practice session.

First use minigame_capture.py --tutorial on a fresh muted project emulator.
Default is a dry-run. This only sends native Start input and reads captions.
"""
import argparse
import json
from pathlib import Path
import struct
import time

import gdbdbg
import minigame_subtitles as mini


def run(apply=False):
    print('Trace the actual time-limit/radar tutorial; press Start after the introduction and capture Square/X instructions.',flush=True)
    if not apply:return
    _,labels=mini.assemble();d=gdbdbg.Dbg();g=d.g;g.s.settimeout(55);active={d.bp};events=[];captures=[]
    target=mini.ROOT/'work/ui/minigame/v017-final-tutorial';target.mkdir(parents=True,exist_ok=True)
    def add(a):g.cmd(f'Z0,{a:x},4');active.add(a)
    def remove(a):g.cmd(f'z0,{a:x},4');active.discard(a)
    def until(a):
        add(a)
        while True:
            g.s.sendall(b'$c#63');g._recv_packet();r=d.regs()
            if r[37]==a:remove(a);return r
    def clock():
        p=struct.unpack('<I',g.read(0x80089600,4))[0]
        first=struct.unpack('<I',g.read(p,4))[0]
        now=struct.unpack('<I',g.read(0x80089620,4))[0]
        return (now-first)/150
    def caption_after(seconds):
        delay=max(.05,seconds-clock())
        g.s.sendall(b'$c#63');time.sleep(delay+.05);add(labels['draw_cue'])
        g._recv_packet();r=d.regs()
        if r[37]!=labels['draw_cue']:raise ValueError('Unexpected caption stop')
        remove(labels['draw_cue']);return r
    def shot(name,r):
        record=struct.unpack('<6H',g.read(r[17],12));text=[]
        for off in record[4:]:
            if off:text.append(g.read(r[18]+off,120).split(b'\0')[0].decode('ascii'))
        mode=struct.unpack('<I',g.read(0x80089AA4,4))[0]
        if mode!=1:raise ValueError('Tutorial is not in native 320x240 mode')
        captures.append(dict(name=name,seconds=clock(),lines=text))
        add(d.bp);d.wait(6);remove(d.bp)
        for y,suffix in [(0,'a'),(240,'b')]:gdbdbg.write_png(str(target/f'{name}_{suffix}.png'),320,240,d.grab(0,y,320,240))
        print(name,text,flush=True)
    try:
        remove(d.bp)
        for _ in range(24):
            r=until(0x8002ECB4);voice=r[4];events.append(voice);print('Native tutorial voice',hex(voice),flush=True)
            # Return from this call before arming the same entry breakpoint
            # again; otherwise a removed/readded breakpoint repeats this stop.
            until(r[31])
            if voice==0x541:shot('time_limit',until(labels['draw_cue']))
            elif voice==0x54D:
                until(labels['draw_cue']);shot('radar',caption_after(2.6))
            elif voice==0x52E:
                until(labels['draw_cue'])
                g.s.sendall(b'$c#63');time.sleep(9.5);add(d.bp);g._recv_packet();d.regs()
                d.press('start',4);d.wait(30);remove(d.bp)
            elif voice==0x52B:
                until(labels['draw_cue']);shot('square',caption_after(4.7));shot('cross',caption_after(7.0));break
        if not {0x541,0x54D,0x52B}.issubset(events):raise ValueError('Required tutorial voices were not reached')
        (target/'tutorial.json').write_text(json.dumps({'native_voice_order':events,'captures':captures,'controller_input':'Start only'},indent=2)+'\n')
    finally:
        for a in active:g.cmd(f'z0,{a:x},4')
        d.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');a=parser.parse_args();run(a.apply)
