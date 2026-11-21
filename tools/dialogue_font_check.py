"""Probe every dialogue glyph's native sprite geometry; restore test RAM/state."""
import argparse,json,struct
from pathlib import Path
import dialogue_font,gdbdbg,masm

def run(apply=False,out=Path('work/ui/dialogue/v0824')):
 print('Native pixel-strip check: printable ASCII and unchanged ordinary sprites; restore all state.',flush=True)
 if not apply:return
 d=gdbdbg.Dbg();g=d.g;regs=saved=None;cursor_word=cursor=ot=None;done=0x8000D11C
 try:
  g.cmd(f'z0,{d.bp:x},4');g.cmd(f'Z0,{gdbdbg.DRAWSYNC:x},4')
  while True:
   g.s.sendall(b'$c#63');g._recv_packet();r=d.regs()
   if r[37]==gdbdbg.DRAWSYNC and r[32]&5:break
  g.cmd(f'z0,{gdbdbg.DRAWSYNC:x},4');regs=d.regs();saved=g.read(gdbdbg.SCRATCH,0xB00)
  blobs,_,_=dialogue_font.assemble()
  assert all(g.read(a,len(b))==b for a,b in blobs)
  cursor_word=struct.unpack('<I',g.read(regs[28]+0x240,4))[0];cursor=g.read(cursor_word,4);ot=g.read(0x80089A8C,4)
  g.write(0x80089A8C,struct.pack('<I',0x8000D300))
  drops=dialogue_font.row_table()[0];records=[]
  for mode in (0xC,0x0200000C):
   for ch in range(33,127):
    code,l=masm.assemble(f'li a0, 10\nli a1, 10\nli a2, {ch}\nli a3, {mode}\njal 0x8004DA64\nnop\nprobe_done:\nnop\n',0x8000D100)
    bp=l['probe_done'];g.write(0x8000D100,code);g.write(0x8000D300,b'\xff\xff\xff\x00'*32);g.write(cursor_word,struct.pack('<I',0x8000D500));g.cmd(f'Z0,{bp:x},4');d.setreg(37,0x8000D100)
    g.s.sendall(b'$c#63');g._recv_packet();assert d.regs()[37]==bp;g.cmd(f'z0,{bp:x},4')
    end=struct.unpack('<I',g.read(cursor_word,4))[0];raw=g.read(0x8000D500,end-0x8000D500)
    drop=drops[ch]if mode>>24==2 else 0
    assert len(raw)==(48 if drop else 28),(ch,hex(mode),len(raw),drop)
    def sprite(i):return struct.unpack_from('<hhBBHHH',raw,i+8)
    x,y,u,v,clut,w,h=sprite(0);assert (x,y,w,h)==(10,10,12,drop or 12),(ch,sprite(0),drop)
    if drop:
     xx,yy,uu,vv,cc,ww,hh=sprite(20)
     assert (xx,yy,uu,vv,cc,ww,hh)==(10,10+drop,u,(v+drop+1)&255,clut,12,11-drop),(ch,sprite(20))
    records.append(dict(char=chr(ch),mode=hex(mode),drop=drop,primitive_bytes=len(raw),first_size=[w,h]))
  assert all(g.read(a,len(b))==b for a,b in blobs)
  out=Path(out);out.mkdir(parents=True,exist_ok=True);(out/'native-glyph-check.json').write_text(json.dumps(dict(cases=len(records),all_checks_passed=True,cases_detail=records),indent=2)+'\n');print('PASS:',len(records),'native glyph geometry checks.',flush=True)
 finally:
  for bp in (done,locals().get('bp',done),gdbdbg.DRAWSYNC):g.cmd(f'z0,{bp:x},4')
  if cursor is not None:g.write(cursor_word,cursor)
  if ot is not None:g.write(0x80089A8C,ot)
  if saved is not None:g.write(gdbdbg.SCRATCH,saved)
  if regs is not None:
   for i in [*range(1,32),33,34,37]:d.setreg(i,regs[i])
  d.close()
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');p.add_argument('--out',type=Path,default=Path('work/ui/dialogue/v0824'));a=p.parse_args();run(a.apply,a.out)
