"""Check/capture the native battle skip hint in a live battle; dry run default."""
import argparse
import json
from pathlib import Path
import struct

import battle_hint as hint
import gdbdbg


def run(apply=False, confirm=False, preview=False, skip=False):
    print('Native battle: verify disc hint code, active text/position, lifecycle guards and framebuffer; restore guard fixtures.',flush=True)
    if not apply:return
    out=Path('work/ui/battle_skip/v0819');out.mkdir(parents=True,exist_ok=True)
    d=gdbdbg.Dbg();g=d.g;g.s.settimeout(45);active={d.bp}
    code,labels=hint.assemble();row=hint.layout();report=dict(layout=row,native_cpu=True,debug_ram_preview=preview)
    def add(at):g.cmd(f'Z0,{at:x},4');active.add(at)
    def remove(at):g.cmd(f'z0,{at:x},4');active.discard(at)
    def u32(at):return struct.unpack('<I',g.read(at,4))[0]
    def u16(at):return struct.unpack('<H',g.read(at,2))[0]
    def resume():g.s.sendall(b'$c#63');g._recv_packet();return d.regs()
    try:
        # Wait at a core address until the overlay is actually loaded; an
        # early breakpoint on an unloaded overlay can be lost by recompilation.
        frames=0;state=None
        while frames<2400:
            r=resume()
            if r[37]==d.bp and r[5]==r[29]:
                if confirm and frames%40<3:d.setreg(gdbdbg.PAD_REG,r[gdbdbg.PAD_REG]|gdbdbg.BTN['circle'])
                frames+=1
                if frames%5==0 and u32(hint.CALLBACK)==hint.CODE:
                    if not preview:assert g.read(hint.CODE,len(code))==code
                    print('Battle overlay loaded; waiting for native draw.',flush=True)
                    add(hint.CODE);break
        else:raise RuntimeError('Battle overlay not loaded')
        while frames<4800:
            r=resume()
            if r[37]==hint.CODE:
                if preview:
                    # Before the first instruction of the wrapper executes:
                    # its caller/return and native battle code are unchanged.
                    assert g.read(hint.CODE,40)==code[:40]
                    g.write(hint.CODE,code);assert g.read(hint.CODE,len(code))==code
                    preview=False
                candidate=u32(r[4]+0x30)
                if u16(candidate+0x62C)>=5 and u16(candidate+0x62C)<17 and g.read(candidate+0x7F4,1)==b'\x02':
                    state=candidate;remove(hint.CODE);add(0x8004DDFC);break
            elif r[37]==d.bp and r[5]==r[29]:frames+=1
        assert state is not None,'Active attack phase not reached'
        print('Active battle phase',u16(state+0x62C),'state',hex(state),flush=True)
        while True:
            r=resume()
            if r[37]==0x8004DDFC and r[6]==labels['hint_text']:
                mode=u32(0x80089AA4);w,h=struct.unpack('<2H',g.read(0x800111A8+mode*4,4))
                row.update(viewport=[w,h],x=w-8-row['width'],y=h-row['height']-4)
                print('Native hint arguments:',r[4],r[5],hex(r[7]),'viewport',w,h,flush=True)
                assert (r[4],r[5],r[7])==(row['x'],row['y'],hint.FLAGS),(r[4],r[5],r[7],row)
                report['native_text_call']=dict(x=r[4],y=r[5],flags=hex(r[7]),text=g.read(r[6],32).split(b'\0')[0].decode('ascii'),phase=u16(state+0x62C))
                remove(0x8004DDFC);break
        report['disc_code_verified']=not report['debug_ram_preview']
        report['battle_parent']=hex(u32(state+0x7E8))
        mode=u32(0x80089AA4);w,h=struct.unpack('<2H',g.read(0x800111A8+mode*4,4))
        assert [w,h]==row['viewport'];report['native_viewport']=[w,h]

        # Run the exact shipped guard instructions in isolation, halting
        # before either text drawing or the wrapper epilogue. No code changes.
        remove(d.bp);add(gdbdbg.DRAWSYNC)
        while True:
            r=resume()
            if r[37]==gdbdbg.DRAWSYNC and r[32]&5:break
        remove(gdbdbg.DRAWSYNC);regs=d.regs();saved=g.read(gdbdbg.SCRATCH,0xC00)
        fixture=0x8000D300;cases=[]
        try:
            add(labels['hint_return']);add(labels['hint_visible_pass'])
            inputs=[(1,2,p,1)for p in range(1,17)]
            inputs +=[(1,2,p,0)for p in (0,17,18,21,65535)]
            inputs +=[(f,2,5,v)for f,v in ((0,0),(2,0),(3,0),(5,1))]
            inputs +=[(1,stage,5,0)for stage in (0,1,3,4)]
            for flags,stage,phase,expected in inputs:
                data=bytearray(0x7F8);struct.pack_into('<H',data,0x7F0,flags);data[0x7F4]=stage;struct.pack_into('<H',data,0x62C,phase)
                g.write(fixture,data);d.setreg(16,fixture);d.setreg(37,labels['hint_visibility_start'])
                r=resume();shown=int(r[37]==labels['hint_visible_pass'])
                assert r[37]in(labels['hint_visible_pass'],labels['hint_return'])
                assert shown==expected,(flags,stage,phase,shown,expected)
                cases.append(dict(flags=flags,stage=stage,phase=phase,shown=bool(shown)))
        finally:
            remove(labels['hint_return']);remove(labels['hint_visible_pass'])
            g.write(gdbdbg.SCRATCH,saved)
            for i in [*range(1,32),33,34,37]:d.setreg(i,regs[i])
        report['visibility_cases']=cases;report['fixtures_restored']=True
        add(d.bp);d.wait(2)
        for y,suffix in ((0,'a'),(h,'b')):
            target=out/f'battle-hint-{suffix}.png'
            gdbdbg.write_png(str(target),w,h,d.grab(0,y,w,h))
            from PIL import Image
            Image.open(target).resize((960,720),Image.Resampling.NEAREST).save(out/f'battle-hint-{suffix}-4x3.png')
        if skip:
            add(0x800AEA5C);inputs=0
            while True:
                r=resume()
                if r[37]==0x800AEA5C:
                    remove(0x800AEA5C);remove(d.bp);ret=r[31];add(ret)
                    while resume()[37]!=ret:pass
                    remove(ret);break
                if r[37]==d.bp and r[5]==r[29]:
                    d.setreg(gdbdbg.PAD_REG,r[gdbdbg.PAD_REG]|gdbdbg.BTN['start']);inputs+=1
                    assert inputs<30,'Start did not reach native skip'
            assert u16(state+0x62C)==17
            report['native_start_skip']=dict(phase_after=17,pad_reads=inputs)
            add(0x800B167C)
            while True:
                r=resume()
                if r[37]==0x800B167C:break
            remove(0x800B167C);actors=r[4];expected=[];ret=r[31]
            for i in range(u16(actors+0x84)):
                actor=u32(actors+i*4)
                if not actor:continue
                flags=u32(actor+0x70)
                if flags&1:
                    dest=u32(u32(actor+0x10)+8)
                    expected.append((dest,g.read(actor+(0x40 if flags&0x40000 else 0x20),6),g.read(actor+(0x48 if flags&0x80000 else 0x28),6)))
            add(ret)
            while resume()[37]!=ret:pass
            remove(ret)
            for dest,a,b in expected:
                assert g.read(dest+0x10,6)==a and g.read(dest+0x18,6)==b
            report['native_actor_sync_verified']=len(expected)
            add(d.bp);add(0x8004DDFC);frames=0
            while frames<90:
                r=resume()
                if r[37]==0x8004DDFC:assert r[6]!=labels['hint_text'],'Hint remained after skipping'
                elif r[37]==d.bp and r[5]==r[29]:frames+=1
            remove(0x8004DDFC);report['hint_hidden_after_skip']=True
        report['all_checks_passed']=True
        print('PASS: native battle hint at bottom right;',len(cases),'visibility cases; scratch/registers restored.',flush=True)
    finally:
        for at in active:g.cmd(f'z0,{at:x},4')
        d.close();(out/'native-hint.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');p.add_argument('--confirm-target',action='store_true');p.add_argument('--ram-preview',action='store_true');p.add_argument('--skip',action='store_true');a=p.parse_args();run(a.apply,a.confirm_target,a.ram_preview,a.skip)
