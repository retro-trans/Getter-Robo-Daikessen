"""Exercise every minigame voice through the native caption renderer. Dry-run default.

Debugger-only calls play the original XA clips in the minigame's static menu.
This checks rendering/track selection; the tutorial is separately tested in order.
"""
import argparse
import json
from pathlib import Path
import struct

import gdbdbg
import minigame_subtitles as mini


def run(apply=False,only=None,output=None,current=False):
    print(f'Check all {len(mini.VOICE_IDS)} native voice IDs, both caption lines, menu scaling, unknown voices and voices disabled.',flush=True)
    if not apply:return
    _,labels=mini.assemble();doc=json.loads(mini.TRANSLATION.read_text());d=gdbdbg.Dbg();g=d.g;g.s.settimeout(45);active={d.bp}
    def add(a):g.cmd(f'Z0,{a:x},4');active.add(a)
    def remove(a):g.cmd(f'z0,{a:x},4');active.discard(a)
    def until(a,reject=None):
        add(a)
        while True:
            g.s.sendall(b'$c#63');g._recv_packet();r=d.regs()
            if reject is not None and r[37]==reject:raise ValueError('Unexpected caption for excluded voice')
            if r[37]==a:remove(a);return r
    def select_voice(v):
        until(0x800C7A54)
        d.setreg(4,1);d.setreg(37,0x8002EBF4)
        until(0x800C7A54)
        d.setreg(4,v);d.setreg(37,0x8002ECB4)
        until(0x800C7A54)
        d.setreg(37,0x8002EC80)
    target=Path(output)if output else mini.ROOT/'work/ui/minigame/v017-native';target.mkdir(parents=True,exist_ok=True);results=[]
    try:
        remove(d.bp)
        if not current:
            until(0x8004CF48);d.setreg(4,9);d.setreg(5,-1)
        until(0x800C7A54);add(d.bp);d.wait(120);remove(d.bp)
        for voice in (only or mini.VOICE_IDS):
            select_voice(voice);r=until(labels['draw_cue'])
            pointer,table=struct.unpack('<I',g.read(0x80089600,4))[0],struct.unpack('<I',g.read(0x8008961C,4))[0]
            if (pointer-table)//16!=voice:raise ValueError('Wrong active XA voice')
            cue=doc['voices'][f'V{voice:04X}'][0];lines=[]
            for expected in cue['lines']:
                r=until(0x8004DDFC)
                text=g.read(r[6],120).split(b'\0')[0].decode('ascii')
                if text!=expected:raise ValueError((voice,text,expected))
                if r[7]!=(0x38000000|mini.FOREGROUND) or r[5]not in (350,376):raise ValueError('Menu caption scale/position mismatch')
                lines.append(dict(text=text,x=r[4],y=r[5],flags=hex(r[7])))
                until(r[31])
            results.append(dict(voice=voice,lines=lines))
            (target/'progress.json').write_text(json.dumps(results,indent=2)+'\n')
            print(f'V{voice:04X}',lines[0]['text'],flush=True)
            if voice==0x48E:
                # Font packets are only queued at the call above. Let complete
                # frames reach the GPU before reading either horizontal buffer.
                add(d.bp);d.wait(6);remove(d.bp)
                gdbdbg.write_png(str(target/'menu_a.png'),512,480,d.grab(0,0,512,480))
        select_voice(1);add(labels['draw_cue']);until(labels['draw_done'],labels['draw_cue']);remove(labels['draw_cue'])
        until(0x800C7A54);r=d.regs();g.write(r[28]+0x908,bytes(4));add(labels['draw_cue']);until(labels['draw_done'],labels['draw_cue']);remove(labels['draw_cue'])
        (target/'voices.json').write_text(json.dumps({'voices':results,'unknown_voice_skipped':True,'disabled_voices_skipped':True},indent=2)+'\n')
    finally:
        for a in active:g.cmd(f'z0,{a:x},4')
        d.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--apply',action='store_true');parser.add_argument('--only',nargs='+',type=lambda s:int(s,0));parser.add_argument('--output-dir');parser.add_argument('--current',action='store_true');a=parser.parse_args();run(a.apply,a.only,a.output_dir,a.current)
