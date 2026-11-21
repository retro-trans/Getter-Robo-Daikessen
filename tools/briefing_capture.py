"""Check normal briefing typography and full-box wrapping on a fresh local build.

Defaults to a dry run. Uses only the muted project emulator and native input.
"""
import argparse
import json
from pathlib import Path
import struct
import time

import briefing_layout as layout
import gdbdbg
import smoke


def run(apply=False,output=Path('work/ui/briefing/v0817/native')):
    print('Episode 2 briefing: verify two narration rows, normal glyphs and input transition.',flush=True)
    if not apply:return
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    with (output/'navigation.log').open('w',encoding='utf8')as log:
        for _ in range(100):
            try:r=smoke.Run(log);break
            except ConnectionRefusedError:time.sleep(.1)
        else:raise ConnectionError('Project debugger did not start')
        d=r.d;g=d.g;active={d.bp};report=dict(version='0.8.17',fresh_disc=True,pages=[])
        def add(a):g.cmd(f'Z0,{a:x},4');active.add(a)
        def remove(a):g.cmd(f'z0,{a:x},4');active.discard(a)
        def until(a):
            add(a)
            while True:
                g.s.sendall(b'$c#63');g._recv_packet();regs=d.regs()
                if regs[37]==a:remove(a);return regs
        def word(a):return struct.unpack('<I',g.read(a,4))[0]
        def page(row_id,name):
            remove(d.bp);regs=until(0x8005BB80);window=regs[4]
            assert word(0x80089AA4)==3
            assert word(window+0x5C)>>24==0x22,hex(word(window+0x5C))
            rect=struct.unpack('<4H',g.read(window+0x10,8));assert rect==(24,164,464,60),rect
            add(0x8004DA64);add(0x8004D7B4);add(0x8005BD00)
            chars=[];dimensions=[]
            while True:
                g.s.sendall(b'$c#63');g._recv_packet();regs=d.regs();pc=regs[37]
                if pc==0x8005BD00:break
                if pc==0x8004DA64:
                    assert regs[7]>>24==0x22,hex(regs[7])
                    assert 32<=regs[6]<127,hex(regs[6])
                    chars.append(dict(char=chr(regs[6]),x=regs[4],y=regs[5],flags=hex(regs[7])))
                elif pc==0x8004D7B4:
                    dimensions.append([regs[8],regs[6]>>16]);assert dimensions[-1]==[16,10],dimensions[-1]
            for a in (0x8004DA64,0x8004D7B4,0x8005BD00):remove(a)
            expected=next(x for x in layout.audit()if x['id']==row_id)
            lines=[]
            for y in sorted({c['y']for c in chars}):
                line=[c for c in chars if c['y']==y]
                text=''.join(c['char']for c in line);x=36
                for c in line:
                    assert c['x']==x,(text,c,x)
                    x+=layout.char_width(c['char'])
                assert x<=476,(text,x)
                lines.append(dict(text=text,y=y,width=x-36))
            assert [l['text']for l in lines]==expected['text'].split('\\n'),(lines,expected)
            assert [l['y']for l in lines]==[170+12*i for i in range(len(lines))]
            assert dimensions
            add(d.bp);d.wait(2);remove(d.bp)
            for y,suffix in [(0,'a'),(240,'b')]:
                target=output/f'{name}_{suffix}.png'
                gdbdbg.write_png(str(target),512,240,d.grab(0,y,512,240))
                from PIL import Image
                Image.open(target).resize((960,720),Image.Resampling.NEAREST).save(output/f'{name}_{suffix}-4x3.png')
            record=dict(row=row_id,window=hex(window),rect=list(rect),lines=lines,glyph=[16,10],
                        measured_width=440,character_positions_match=True)
            report['pages'].append(record);print('PASS:',row_id,[l['text']for l in lines],flush=True)
        try:
            r.switch(10,2)
            assert r.press_until('Next Map','circle',60,45)[0]is not None
            r.plain(20);r.press('down',6,12);r.press('circle',1,40);r.press('up',1,12);r.press('circle',1,60)
            r.plain(300);page('BRF_0310','first')
            add(d.bp);d.press('circle');d.wait(240);page('BRF_034C','second')
            add(d.bp);d.press('circle');d.wait(240);remove(d.bp)
            regs=until(0x8005BB80);window=regs[4]
            assert word(0x80089AA4)==1
            assert word(window+0x5C)>>24!=0x22
            report['story_dialogue_keeps_original_mode']=hex(word(window+0x5C))
            report['all_checks_passed']=True
            print('PASS: original story font mode restored after briefing.',flush=True)
        finally:
            for a in active:g.cmd(f'z0,{a:x},4')
            d.close();(output/'checks.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');p.add_argument('--output-dir',type=Path,default=Path('work/ui/briefing/v0817/native'));a=p.parse_args();run(a.apply,a.output_dir)
