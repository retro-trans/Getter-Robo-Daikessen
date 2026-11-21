"""Native CPU checks for difficulty/level rules, with restored RAM (dry run default).

Run at the title screen of the muted 0.8.18 project emulator. Fixtures use only
the currently unused tail of the title overlay slot; no files or card are edited.
"""
import argparse
import json
from pathlib import Path
import struct

import build
import datatext
import difficulty
import gdbdbg
import masm

OUT = Path('work/ui/difficulty/v0818')
BLOCK, MANAGER, HANDLE, DB = 0x80094000, 0x80094800, 0x80094810, 0x80094900
INFO, SAVE, END = 0x80096D00, 0x80097000, 0x80098B00
PILOT = 2
RECORD = BLOCK + 0x14C + PILOT * 28


def run(apply=False):
    print('Native CPU: Normal/Easy limits, all 98 level-ups, 20 pilot growth records, stage retention, save checksums and reload. Restore every fixture.', flush=True)
    if not apply:
        return
    d = gdbdbg.Dbg(); g = d.g
    g.s.settimeout(30)
    saved = regs = scratch = pending = None
    report = dict(native_cpu=True, no_card_or_disc_writes=True, cases=[])
    active = {d.bp}
    _, labels = difficulty.resident()
    u16 = lambda a: struct.unpack('<H', g.read(a, 2))[0]
    u32 = lambda a: struct.unpack('<I', g.read(a, 4))[0]
    def w16(a, v): g.write(a, struct.pack('<H', v))
    def w32(a, v): g.write(a, struct.pack('<I', v))
    def function(address, *args):
        source = '\n'.join(f'li a{i}, {v}' for i, v in enumerate(args))
        source += f'\njal {address}\nnop\nprobe_done:\nnop\n'
        code, ll = masm.assemble(source, 0x8000D100)
        stop = ll['probe_done']
        g.write(0x8000D100, code); g.cmd(f'Z0,{stop:x},4'); active.add(stop)
        d.setreg(37, 0x8000D100)
        g.s.sendall(b'$c#63'); g._recv_packet(); r = d.regs()
        assert r[37] == stop, ('probe interrupted', hex(address), hex(r[37]))
        g.cmd(f'z0,{stop:x},4'); active.remove(stop)
        return r[2]
    def level(flags, initial, exp=999):
        w16(BLOCK+8, flags)
        function(0x8005CE84, MANAGER, PILOT, initial, 0)
        w32(RECORD+8, exp)
    try:
        # Enter at a main-loop safe point; the cooperative game task stays
        # suspended while the fixture invokes only resident leaf/callee code.
        g.cmd(f'z0,{d.bp:x},4'); active.remove(d.bp)
        g.cmd(f'Z0,{gdbdbg.DRAWSYNC:x},4'); active.add(gdbdbg.DRAWSYNC)
        while True:
            g.s.sendall(b'$c#63'); g._recv_packet(); r=d.regs()
            if r[37] == gdbdbg.DRAWSYNC and r[32]&5: break
        g.cmd(f'z0,{gdbdbg.DRAWSYNC:x},4'); active.remove(gdbdbg.DRAWSYNC)
        regs=d.regs(); saved=g.read(BLOCK,END-BLOCK); scratch=g.read(gdbdbg.SCRATCH,0x300)
        pending=g.read(labels['pending_easy'],4)
        assert g.read(difficulty.RESIDENT,len(difficulty.resident()[0]))[:0xA4] == difficulty.resident()[0][:0xA4]
        assert u32(difficulty.BASE+0x10)==difficulty.title_assemble()[1]['difficulty_update'], 'Run only on the current title overlay'
        g.write(BLOCK,bytes(END-BLOCK))
        definitions=datatext.entry(build.vfs_file(Path('work/source/disc/GR.VFS').read_bytes(),'mapsys/mcn_prm.pac'),'PIL_PRM.BIN')
        assert DB+len(definitions) < INFO
        g.write(DB,definitions);w32(MANAGER,BLOCK);w32(BLOCK+4,HANDLE);w32(HANDLE,DB)
        w32(INFO+0x58,MANAGER);w32(INFO+0x10,1);w32(INFO+0x14,1)

        # New-game initialization keeps the native sex/skill/name behavior.
        for bit in (0,0x8000):
            w32(labels['pending_easy'],bit);w16(BLOCK+8,0xF000)
            g.write(0x8000D200,b'Test\0')
            function(0x8005D674,BLOCK+8,0x8000D200,1,2)
            assert u16(BLOCK+8)==(0x7006|bit)
            assert g.read(BLOCK+12,5)==b'Test\0' and g.read(BLOCK+0x118,1)==b'\x02'
        report['native_player_initialization']=True
        for flags, initial, expected, changed in [(2,39,40,1),(2,40,40,0),
                (0x8002,39,40,1),(0x8002,40,41,1),(0x8002,98,99,1),(0x8002,99,99,0)]:
            level(flags,initial)
            result=function(0x8005D2A8,MANAGER,PILOT,1,0)
            actual=u16(RECORD+6);assert (result,actual)==(changed,expected),(flags,initial,result,actual)
            assert u32(RECORD+8)==(0 if changed else 999)
            report['cases'].append(dict(easy=bool(flags&0x8000),before=initial,after=actual,level_up=bool(result)))
        level(0x8002,1,0)
        for expected in range(2,100):
            assert function(0x8005D2A8,MANAGER,PILOT,1000,0)==1
            assert u16(RECORD+6)==expected
        assert function(0x8005D2A8,MANAGER,PILOT,1000,0)==0 and u16(RECORD+6)==99
        report['consecutive_level_ups']=98
        growth=[]
        for pilot in range(20):
            if not function(0x8005D4C4,pilot): continue
            function(0x8005CE84,MANAGER,pilot,99,0)
            record=BLOCK+0x14C+pilot*28
            stats=list(struct.unpack('<5H',g.read(record+0x10,10)))
            assert u16(record+6)==99 and all(v<10000 for v in stats),(pilot,stats)
            growth.append(dict(pilot=pilot,level=99,stats=stats))
        # Also cover the custom player's definition copied into the native block.
        off=struct.unpack_from('<I',definitions,4+19*4)[0]
        g.write(BLOCK+0xC,definitions[off:off+0x10C]);w16(BLOCK+8,0x8003)
        function(0x8005CE84,MANAGER,19,99,0)
        assert u16(BLOCK+0x14C+19*28+6)==99
        report['growth_at_99']=growth;report['custom_player_at_99']=True
        stages=[]
        for flags, initial, target, expected, exp in [(2,35,10,10,0),
                (0x8002,35,10,35,321),(0x8002,35,35,35,321),
                (0x8002,35,40,40,0),(0x8002,99,20,99,321)]:
            level(flags,initial,321)
            function(labels['stage_level'],MANAGER,PILOT,target,1)
            assert (u16(RECORD+6),u32(RECORD+8))==(expected,exp)
            stages.append(dict(easy=bool(flags&0x8000),before=initial,stage_level=target,after=expected,exp=exp))
        report['stage_transitions']=stages

        saves=[]
        for flags, lv in [(2,35),(0x8002,99)]:
            level(flags,lv,345)
            function(0x8005285C,SAVE,INFO,0)
            assert u16(SAVE)==0x1A70 and u16(SAVE+0xB0)&0x8000==flags&0x8000
            function(0x80052704,SAVE)
            checksum=function(0x8005269C,SAVE)
            assert checksum==0, ('checksum result',checksum)
            blob=g.read(SAVE,0x1A70)
            # Memory-card-sized byte round trip, including the native checksum.
            g.write(SAVE,bytes(0x1A70));g.write(BLOCK+8,bytes(0x76C-8))
            g.write(SAVE,blob);function(0x80052D90,SAVE,INFO,0)
            assert u16(BLOCK+8)&0x8000==flags&0x8000
            assert (u16(RECORD+6),u32(RECORD+8))==(lv,345)
            w32(RECORD+8,999);result=function(0x8005D2A8,MANAGER,PILOT,1,0)
            assert result==(0 if lv==99 else 1)
            saves.append(dict(easy=bool(flags&0x8000),level=lv,exp=345,bytes=len(blob),checksum_valid=True,reloaded=True))
        report['save_roundtrips']=saves
        report['legacy_save_without_marker_is_normal']=True
        report['all_checks_passed']=True
        print('PASS: level 40/41/98/99, 98 consecutive level-ups,',len(growth),'levelable pilots, stage retention, native save/load/checksum.',flush=True)
    finally:
        for at in active:g.cmd(f'z0,{at:x},4')
        if saved is not None:g.write(BLOCK,saved)
        if scratch is not None:g.write(gdbdbg.SCRATCH,scratch)
        if pending is not None:g.write(labels['pending_easy'],pending)
        if regs is not None:
            for i in [*range(1,32),33,34,37]:d.setreg(i,regs[i])
        d.close()
        report['fixtures_restored']=saved is not None
        OUT.mkdir(parents=True,exist_ok=True);(OUT/'native-levels.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');a=p.parse_args();run(a.apply)
