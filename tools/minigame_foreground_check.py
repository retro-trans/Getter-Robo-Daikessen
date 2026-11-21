"""Verify captions against the final native GPU list in paused flight practice.

First run minigame_capture.py --tutorial on a fresh muted local build.
Dry run by default. Uses original XA playback calls; no game/save-file edits.
"""
import argparse
import json
from pathlib import Path
import struct

import gdbdbg
import minigame_subtitles as mini


def run(apply=False, output=Path('work/ui/minigame/v0816/flight')):
    print('Check single/two-line captions: final HUD layer, full-screen clip/origin and native GPU order.', flush=True)
    if not apply: return
    output=Path(output); output.mkdir(parents=True,exist_ok=True)
    d=gdbdbg.Dbg();g=d.g;g.s.settimeout(45);active={d.bp};_,labels=mini.assemble()
    doc=json.loads(mini.TRANSLATION.read_text());results=[]
    def add(a):g.cmd(f'Z0,{a:x},4');active.add(a)
    def remove(a):g.cmd(f'z0,{a:x},4');active.discard(a)
    def until(a):
        add(a)
        while True:
            g.s.sendall(b'$c#63');g._recv_packet();r=d.regs()
            if r[37]==a:remove(a);return r
    def word(a):return struct.unpack('<I',g.read(a,4))[0]
    def select(v):
        until(0x800C7A54);d.setreg(4,1);d.setreg(37,0x8002EBF4)
        until(0x800C7A54);d.setreg(4,v);d.setreg(37,0x8002ECB4)
        until(0x800C7A54);d.setreg(37,0x8002EC80)
    try:
        remove(d.bp)
        for voice,index,name in [(0x541,2,'hud_overlap'),(0x54D,1,'two_lines')]:
            select(voice);cue=doc['voices'][f'V{voice:04X}'][index]
            for _ in range(1200):
                r=until(labels['draw_cue']);record=struct.unpack('<6H',g.read(r[17],12))
                text=g.read(r[18]+record[4],128).split(b'\0')[0].decode('ascii')
                if text==cue['lines'][0]:break
                until(labels['draw_done'])
            else:raise ValueError('Requested native cue not reached')
            assert word(0x80089AA4)==1
            ranges=[];calls=[]
            for i,text in enumerate(cue['lines']):
                r=until(0x8004DDFC)
                actual=g.read(r[6],128).split(b'\0')[0].decode('ascii')
                assert actual==text and r[7]==mini.FOREGROUND
                assert r[5]==(190 if len(cue['lines'])==2 and i==0 else 204)
                start=word(0x80089A90)&0x1FFFFF
                calls.append(dict(text=text,x=r[4],y=r[5],flags=hex(r[7])))
                until(r[31]);end=word(0x80089A90)&0x1FFFFF
                assert end>start;ranges.append((start,end))
            # All game tasks have emitted their primitives at this point.
            until(0x8003B490)
            ram=g.read(0x80000000,0x200000)
            u32=lambda a:struct.unpack_from('<I',ram,a&0x1FFFFF)[0]
            base=u32(0x80089A8C)&0x1FFFFF;count=1<<u32(0x80089A9C)
            assert count==16,count
            p=base;seen=set();bucket=-1;packets=[];caption=[];other=[];clip={}
            for order in range(50000):
                if p==0xFFFFFF:break
                assert p<0x200000 and p not in seen,hex(p);seen.add(p)
                if base<=p<base+count*4:bucket=(p-base)//4
                tag=u32(p);n=tag>>24;words=[u32(p+4+i*4)for i in range(n)]
                if n:
                    cmd=words[0]>>24
                    if 0xE0<=cmd<=0xE6:
                        for w in words:
                            c=w>>24
                            if c==0xE3:clip['top_left']=[w&1023,(w>>10)&1023]
                            elif c==0xE4:clip['bottom_right']=[w&1023,(w>>10)&1023]
                            elif c==0xE5:
                                signed=lambda v:v-2048 if v&1024 else v
                                clip['offset']=[signed(w&2047),signed((w>>11)&2047)]
                    is_caption=any(lo<=p<hi for lo,hi in ranges)
                    draw=0x20<=cmd<0x80
                    packets.append(dict(order=order,address=hex(p),bucket=bucket,command=hex(cmd),caption=is_caption,draw=draw))
                    if draw and is_caption:
                        assert bucket==mini.FOREGROUND
                        assert clip.get('offset',[None])[0]==0,clip
                        y=clip['offset'][1]
                        assert clip['top_left']==[0,y] and clip['bottom_right']==[319,y+239],clip
                        caption.append(order)
                    elif draw:other.append(order)
                p=tag&0xFFFFFF
            else:raise ValueError('GPU list did not terminate')
            assert caption and other
            assert max(other)<min(caption),(max(other),min(caption))
            report=dict(cue=cue['id'],calls=calls,primary_buckets=count,caption_primitives=len(caption),
                        last_noncaption_draw=max(other),first_caption_draw=min(caption),caption_is_foremost=True,
                        full_screen_clip_and_native_offset=True,packets=packets)
            (output/f'{name}-gpu.json').write_text(json.dumps(report,indent=2)+'\n')
            add(d.bp);d.wait(2);remove(d.bp)
            for y,suffix in [(0,'a'),(240,'b')]:
                gdbdbg.write_png(str(output/f'{name}_{suffix}.png'),320,240,d.grab(0,y,320,240))
            results.append({k:v for k,v in report.items()if k!='packets'})
            print('PASS:',name,': all caption glyphs follow every HUD/world primitive.',flush=True)
        (output/'checks.json').write_text(json.dumps(dict(captures=results,all_checks_passed=True),indent=2)+'\n')
    finally:
        for a in active:g.cmd(f'z0,{a:x},4')
        d.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');p.add_argument('--output-dir',type=Path,default=Path('work/ui/minigame/v0816/flight'));a=p.parse_args();run(a.apply,a.output_dir)
