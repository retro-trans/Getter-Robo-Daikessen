"""Check native success-result speech, with a RAM-only test result. Dry-run default."""
import argparse
import json
from pathlib import Path
import struct
import time

import gdbdbg
import minigame_subtitles as mini


def run(apply=False,drill=0,output=None):
    print(f'Native success certificate for drill {drill}; female then male speech; all male cues.',flush=True)
    if not apply:return
    target=Path(output);target.mkdir(parents=True,exist_ok=True)
    for _ in range(100):
        try:d=gdbdbg.Dbg();break
        except ConnectionRefusedError:time.sleep(.1)
    else:raise ConnectionError('Project emulator debugger did not start')
    g=d.g;g.s.settimeout(45);active={d.bp}
    def add(a):g.cmd(f'Z0,{a:x},4');active.add(a)
    def remove(a):g.cmd(f'z0,{a:x},4');active.discard(a)
    def until(a):
        add(a)
        while True:
            g.s.sendall(b'$c#63');g._recv_packet();r=d.regs()
            if r[37]==a:remove(a);return r
    def word(a):return struct.unpack('<I',g.read(a,4))[0]
    try:
        remove(d.bp);until(0x8004CF48);d.setreg(4,9);d.setreg(5,-1)
        r=until(0x800C7574);state=word(r[4]+0x30)
        record=bytearray(0x80);struct.pack_into('<II',record,0x28,0x40000000,0x80)
        g.write(0x8000DE00,record);g.write(0x8008B6DC,struct.pack('<2H',0x20,0x40))
        for offset,value in [(8,0x40000000),(0xc,1),(0x14,drill),(0x1c,0x50000000),(0x20,0),(0x48,0x8000DE00)]:
            g.write(state+offset,struct.pack('<I',value))
        r=until(0x800E05BC);state=word(r[4]+0x30)
        # Equivalent to the native result notification: activate updates and
        # supply successful current/best times. This fixture never touches saves.
        g.write(state+0x968,struct.pack('<I',1))
        g.write(state+0x98E,struct.pack('<4H',35,13,20,0))
        r=until(0x8002ECB4);female=r[4]
        assert female==(0x3D8 if drill==4 else 0x3E4),hex(female)
        print('Female success voice',hex(female),flush=True)
        r=until(0x800E0BF0);male=r[4]
        assert male==(0x53A if drill==4 else 0x488),hex(male)
        print('Native shared call selected male voice',hex(male),flush=True)
        _,labels=mini.assemble();doc=json.loads(mini.TRANSLATION.read_text(encoding='utf8'))
        results=[]
        for cue in doc['voices'][f'V{male:04X}']:
            for attempt in range(1000):
                r=until(labels['draw_cue'])
                fields=struct.unpack('<6H',g.read(r[17],12))
                text=g.read(r[18]+fields[4],120).split(b'\0')[0].decode('ascii')
                if text==cue['lines'][0]:break
                until(labels['draw_done'])
            else:raise ValueError('Caption not reached: '+cue['id'])
            assert (word(0x80089600)-word(0x8008961C))//16==male
            lines=[]
            for expected in cue['lines']:
                r=until(0x8004DDFC);text=g.read(r[6],120).split(b'\0')[0].decode('ascii')
                assert text==expected,(text,expected)
                assert r[7]==(0x38000000|mini.FOREGROUND) and r[5] in (350,376)
                lines.append(dict(text=text,x=r[4],y=r[5],flags=hex(r[7])))
                until(r[31])
            add(d.bp);d.wait(6);remove(d.bp)
            name=cue['id']+'.png';gdbdbg.write_png(str(target/name),512,480,d.grab(0,0,512,480))
            from PIL import Image
            Image.open(target/name).resize((640,480),Image.Resampling.NEAREST).save(target/(cue['id']+'_4x3.png'))
            results.append(dict(id=cue['id'],lines=lines,screenshot=name))
            print(cue['id'],lines,flush=True)
        (target/'result.json').write_text(json.dumps(dict(drill=drill,female=female,male=male,shared_call='0x800E0BF0',cues=results,fixture='RAM-only success notification'),indent=2)+'\n',encoding='utf8')
    finally:
        for a in active:g.cmd(f'z0,{a:x},4')
        d.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');p.add_argument('--drill',type=int,choices=[0,4],default=0);p.add_argument('--output-dir',required=True);a=p.parse_args();run(a.apply,a.drill,a.output_dir)
