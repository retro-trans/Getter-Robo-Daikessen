"""Probe command-menu edge clamps through both native hook sites; dry run."""
import argparse,json,struct
from pathlib import Path
import command_layout,gdbdbg
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');a=p.parse_args()
print('Native command clamp: both paths, screen edges and already-in-bounds labels; restore state.',flush=True)
if not a.apply:raise SystemExit()
d=gdbdbg.Dbg();g=d.g;regs=saved=None;points=[0x80058110,0x8005831C];rows=[]
try:
 g.cmd(f'z0,{d.bp:x},4');g.cmd(f'Z0,{gdbdbg.DRAWSYNC:x},4')
 while True:
  g.s.sendall(b'$c#63');g._recv_packet();r=d.regs()
  if r[37]==gdbdbg.DRAWSYNC and r[32]&5:break
 g.cmd(f'z0,{gdbdbg.DRAWSYNC:x},4');regs=d.regs();saved=g.read(gdbdbg.SCRATCH,0xB00)
 code,_=command_layout.assemble();assert g.read(command_layout.START,len(code))==code
 g.write(0x8000D704,struct.pack('<I',0xA55A0004));g.write(0x8000D714,struct.pack('<hhH',77,0,19))
 for entry,stop in [(0x80058104,points[0]),(0x80058310,points[1])]:
  g.cmd(f'Z0,{stop:x},4')
  for base in (0,8,16,32,100,300):
   for offset in (-31,4):
    g.write(0x8000D518,struct.pack('<H',base));d.setreg(29,0x8000D500);d.setreg(19,0x8000D700);d.setreg(17,offset);d.setreg(2,0x12345678);d.setreg(37,entry)
    g.s.sendall(b'$c#63');g._recv_packet();r=d.regs();assert r[37]==stop
    expected=offset if base+offset>0 else 1-base;actual=r[17]if r[17]<0x80000000 else r[17]-0x100000000
    assert actual==expected,(hex(entry),base,offset,actual,expected)
    assert r[3]==19
    assert r[2]==(4 if entry==0x80058104 else 77)
    if entry==0x80058104:assert r[4]==0xA55A0004
    rows.append(dict(entry=hex(entry),base=base,offset=offset,final_text_x=base+actual))
  g.cmd(f'z0,{stop:x},4')
 out=Path('work/ui/terminology/v0826');(out/'clamp-native-check.json').write_text(json.dumps(dict(all_checks_passed=True,cases=rows,restored_state=True),indent=2)+'\n');print('PASS:',len(rows),'native cases; labels and highlight offsets stay in bounds.')
finally:
 for bp in points+[gdbdbg.DRAWSYNC]:g.cmd(f'z0,{bp:x},4')
 if saved is not None:g.write(gdbdbg.SCRATCH,saved)
 if regs is not None:
  for i in [*range(1,32),33,34,37]:d.setreg(i,regs[i])
 d.close()
