"""Run font-compatibility probes on the game's CPU; restore scratch/registers.

Dry run by default. Expects the new build in the muted project emulator.
"""
import argparse
import json
from pathlib import Path
import struct

import gdbdbg
import masm
import vwf


def run(apply=False):
    print('Native CPU probe: normal briefing cells, existing font modes and every dialogue advance width; restore all test memory.',flush=True)
    if not apply:return
    _,l=vwf.build_cave();base=gdbdbg.SCRATCH+0x100;results=gdbdbg.SCRATCH
    glyphs=[(0x2200000C,24,12,16,10),(0x3200000C,24,24,16,20),
            (0x3400000C,24,24,11,13),(0x3800000C,24,24,19,24),
            (0x1000000C,12,24,12,24),(0x2000000C,24,12,24,12)]
    advance=(0,1,3,4,5,7,8,9,11,12,13,15,16)
    cases=[(mode,24,w,100+advance[w])for mode in (0x2200000C,0x3200000C)for w in range(13)]
    cases += [(mode,size,7,100+(14 if size==24 else 7))for mode,size in [(0xC,12),(0x1000000C,12),(0x2000000C,24),(0x3000000C,24)]]
    s=f'''la s3, glyph_cases
li s4, {results}
li s6, {len(glyphs)}
glyph_loop:
lw a3, 0(s3)
lw t0, 4(s3)
lw a2, 8(s3)
jal {l['briefing_glyph_width']}
nop
sw t0, 0(s4)
sw a2, 4(s4)
addiu s4, s4, 8
addiu s3, s3, 12
addiu s6, s6, -1
bnez s6, glyph_loop
nop
la s3, advance_cases
li s6, {len(cases)}
la s2, fake_window
advance_loop:
lw t5, 0(s3)
lw s5, 4(s3)
sw t5, 0x5C(s2)
lw t6, 8(s3)
li s0, 100
jal {l['dl_add']}
nop
sw s0, 0(s4)
addiu s4, s4, 4
addiu s3, s3, 12
addiu s6, s6, -1
bnez s6, advance_loop
nop
probe_done:
nop
glyph_cases:
'''
    for flags,x,y,_,_ in glyphs:s+=f'.word {flags}, {x}, {y<<16}\n'
    s+='advance_cases:\n'
    for flags,size,w,_ in cases:s+=f'.word {flags}, {size}, {w}\n'
    s+='fake_window:\n.space 0x68\n'
    code,labels=masm.assemble(s,base);assert len(code)<0x900
    d=gdbdbg.Dbg();g=d.g;saved=None;regs=None;bp=labels['probe_done'];end=base+len(code)
    try:
        g.cmd(f'z0,{d.bp:x},4');g.cmd(f'Z0,{gdbdbg.DRAWSYNC:x},4')
        while True:
            g.s.sendall(b'$c#63');g._recv_packet();r=d.regs()
            if r[37]==gdbdbg.DRAWSYNC and r[32]&5:break
        g.cmd(f'z0,{gdbdbg.DRAWSYNC:x},4');regs=d.regs()
        saved=g.read(gdbdbg.SCRATCH,end-gdbdbg.SCRATCH)
        g.write(base,code);g.cmd(f'Z0,{bp:x},4');d.setreg(37,base)
        g.s.sendall(b'$c#63');g._recv_packet();assert d.regs()[37]==bp
        raw=g.read(results,len(glyphs)*8+len(cases)*4);offset=0
        for flags,x,y,w,h in glyphs:
            actual=struct.unpack_from('<II',raw,offset);offset+=8
            assert actual==(w,h<<16),(hex(flags),actual,w,h)
        for flags,size,w,expected in cases:
            actual=struct.unpack_from('<I',raw,offset)[0];offset+=4
            assert actual==expected,(hex(flags),size,w,actual,expected)
        out=Path('work/ui/briefing/v0817');out.mkdir(parents=True,exist_ok=True)
        report=dict(glyph_modes=[dict(flags=hex(f),cell=[w,h])for f,_,_,w,h in glyphs],
                    advance_cases=len(cases),existing_modes_retained=True,all_checks_passed=True)
        (out/'font-compatibility.json').write_text(json.dumps(report,indent=2)+'\n')
        print('PASS:',len(glyphs),'glyph modes and',len(cases),'native dialogue-width probes.',flush=True)
    finally:
        for p in (bp,gdbdbg.DRAWSYNC):g.cmd(f'z0,{p:x},4')
        if saved is not None:g.write(gdbdbg.SCRATCH,saved)
        if regs is not None:
            for i in [*range(1,32),33,34,37]:d.setreg(i,regs[i])
        d.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');a=p.parse_args();run(a.apply)
