"""Fresh-boot native title difficulty navigation/capture (dry run default)."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

import difficulty
from gdbdbg import Dbg, write_png


def run(choice='easy', apply=False):
    print('Fresh title: native menu navigation, difficulty cancel, select',choice,'and transition.',flush=True)
    if not apply:return
    d=Dbg();g=d.g;g.s.settimeout(30)
    _, labels=difficulty.title_assemble();_, core=difficulty.resident()
    out=Path('work/ui/difficulty/v0818');out.mkdir(parents=True,exist_ok=True)
    report=dict(choice=choice,fresh_boot=True,disc_code=True,
                title_code_sha256=hashlib.sha256(difficulty.title_assemble()[0]).hexdigest())
    u32=lambda a:struct.unpack('<I',g.read(a,4))[0]
    def capture(name):
        mode=u32(0x80089AA4)
        w,h=struct.unpack('<2H',g.read(0x800111A8+mode*4,4))
        write_png(str(out/(name+'.png')),w,h,d.grab(0,0,w,h))
        from PIL import Image
        Image.open(out/(name+'.png')).resize((960,720),Image.Resampling.NEAREST).save(out/(name+'-4x3.png'))
    try:
        signature=struct.pack('<5I',0x8008C354,0x8008C474,labels['difficulty_update'],labels['difficulty_draw'],0x8008CEB0)
        state=None
        for i in range(300):
            ram=g.read(0x80088000,0x3000);at=-1
            while True:
                at=ram.find(signature,at+1)
                if at<0:break
                task=0x80088000+at-0x1C;pointer=u32(task+0x30)
                if 0x80010000<=pointer<0x80200000:state=pointer;break
            if state is not None:break
            # Skip the native opening movie while waiting for the title task.
            if i%5==4:d.press('start')
            d.wait(20)
        assert state is not None,'Title not loaded'
        for i in range(140):
            d.wait(10)
            if u32(state+0x34)==5 and u32(state+4)&7==7:break
            if i%6==5 and u32(state+0x34)==0:d.press('start')
        else:raise RuntimeError('Title did not become ready')
        code,_=difficulty.title_assemble();assert g.read(difficulty.TITLE_CODE,len(code))==code
        print('Native title ready',hex(state),flush=True)
        assert u32(state+0x18)==0
        d.press('down');d.wait(5);assert u32(state+0x18)==1
        d.press('up');d.wait(5);assert u32(state+0x18)==0
        d.press('circle');d.wait(5);assert u32(labels['modal_open'])==1
        assert u32(labels['modal_choice'])==0
        d.press('down');d.wait(4);assert u32(labels['modal_choice'])==1
        d.press('up');d.wait(4);assert u32(labels['modal_choice'])==0
        d.press('cross');d.wait(5)
        assert u32(labels['modal_open'])==0 and u32(state+0x34)==5
        assert u32(core['pending_easy'])==0
        report.update(navigation=True,cancel=True,cancel_did_not_change_difficulty=True)
        if choice=='load':
            d.press('down');d.press('circle');d.wait(3)
            assert u32(labels['modal_open'])==0 and u32(state+0x34)!=5
            report['load_bypasses_difficulty']=True
        else:
            d.press('start');d.wait(4);assert u32(labels['modal_open'])==1
            if choice=='easy':d.press('down');d.wait(4)
            capture('difficulty-'+choice)
            d.press('circle');d.wait(4)
            assert u32(labels['modal_open'])==0
            assert u32(core['pending_easy'])==(0x8000 if choice=='easy' else 0)
            assert u32(state+0x34)!=5
            d.wait(180);capture('after-'+choice)
            report.update(selection_applied=True,continued_to_native_setup=True)
            # The original game-flow root has already initialized its live
            # saved player record by this point. Check the UI-to-record path.
            ram=g.read(0x80088000,0x3000)
            signature=struct.pack('<3I',0x8004E380,0x8004E4EC,0x8004E53C)
            at=-1;records=[]
            while True:
                at=ram.find(signature,at+1)
                if at<0:break
                root=0x80088000+at-0x1C;s=u32(root+0x30)
                if not 0x80010000<=s<0x80200000:continue
                handle=u32(s+0x10)
                if not 0x80010000<=handle<0x80200000:continue
                blob=u32(handle)
                flags=struct.unpack('<H',g.read(blob+0xB0,2))[0]
                assert bool(flags&0x8000)==(choice=='easy')
                records.append(dict(task=hex(root),player_flags=hex(flags),easy=bool(flags&0x8000)))
            assert records,'Live new-game player record not found'
            report['live_new_game_player_records']=records
        report['all_checks_passed']=True
        print('PASS: difficulty navigation/cancel/selection and native transition:',choice,flush=True)
    finally:
        d.close();(out/('native-title-'+choice+'.json')).write_text(json.dumps(report,indent=2)+'\n')
        if choice=='easy':(out/'native-title.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--choice',choices=('easy','normal','load'),default='easy');p.add_argument('--apply',action='store_true');a=p.parse_args();run(a.choice,a.apply)
