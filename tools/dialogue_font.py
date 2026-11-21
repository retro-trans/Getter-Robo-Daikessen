"""Dialogue-only native-pixel row compaction; no texture or width changes.

Row 7 duplicates row 6 in every Latin letter and digit in the current font.
Two unscaled native sprites omit it; the other font modes keep one sprite.
"""
import struct
from pathlib import Path
import font,masm
ROOT=Path(__file__).resolve().parents[1]
WINDOW=0x8000DDC0
CHAR=0x8000F5B8
RASTER=0x8000DE80
# DE00..DE80 belongs to the debug fixture. Observed BIOS context writes start
# at DF80, so all added code must end strictly below that boundary.
RASTER_LIMIT=0x8000DF80

def row_table():
 out=bytearray(128);report=[]
 for c,(top,rows,_) in font.parse_font().items():
  if not rows or c>=128:continue
  w=max(map(len,rows));full=['.'*w]*12
  for i,row in enumerate(rows):full[top+i]=row.ljust(w,'.')
  drop=7 if full[6]==full[7] else 0
  out[c]=drop
  report.append(dict(char=chr(c),drop_row=drop,identical_ink_rows=bool(drop),original_top=top))
 return bytes(out),report

def assemble():
 table,report=row_table()
 raster=r'''
filter_sprite:
    sh v0, 0x10(a1)
    sh v0, 0x12(a1)
    sw zero, 0(sp)
    srl t3, a3, 24
    addiu t3, t3, -2
    bnez t3, filter_done
    nop
    srl t3, a3, 22
    andi t3, t3, 1
    beqz t3, filter_done
    li t3, 7
    sh t4, 0xE(a1)
    sh t1, 0xC(a1)
    lw t7, 0x240(gp)
    nop
    lw t8, 0(t7)
    nop
    addiu v0, t8, 20
    sw v0, 0(t7)
    sw t8, 0(sp)
    move t9, a1
    li t7, 20
copy_sprite:
    lw v0, 0(t9)
    addiu t9, t9, 4
    sw v0, 0(t8)
    addiu t7, t7, -4
    bnez t7, copy_sprite
    addiu t8, t8, 4
    addiu t8, t8, -20
    sh t3, 0x12(a1)
    addu v0, t6, t3
    sh v0, 0xA(t8)
    addiu v0, t3, 1
    sll v0, v0, 8
    addu v0, t1, v0
    sh v0, 0xC(t8)
    li v0, 11
    subu v0, v0, t3
    sh v0, 0x12(t8)
filter_done:
    j 0x8004D918
    nop
insert_second:
    lw a1, 0(sp)
    nop
    beqz a1, insert_done
    nop
    lw a0, 0xC(s1)
    jal 0x8001E6E8
    addu a0, a0, s2
insert_done:
    lw v1, 0x240(gp)
    j 0x8004D938
    move a1, zero
'''

 rb,rl=masm.assemble(raster,RASTER);assert RASTER+len(rb)<=RASTER_LIMIT,(len(rb),hex(RASTER+len(rb)))
 cb,cl=masm.assemble(r'''
char_row:
    srl v0, fp, 24
    addiu v0, v0, -2
    bnez v0, char_original
    sltiu v0, a2, 128
    beqz v0, char_original
    srl v0, a2, 3
    la v1, row_mask
    addu v0, v0, v1
    lbu v0, 0(v0)
    andi v1, a2, 7
    srlv v0, v0, v1
    andi v0, v0, 1
    sll v0, v0, 22
    or fp, fp, v0
char_original:
    j 0x8004DAB0
    addiu v0, a2, -0x20
''',CHAR,symbols={'row_mask':WINDOW+36});assert CHAR+len(cb)<=0x8000F600
 wb,wl=masm.assemble(r'''
window_text:
    lw t0, 0x10(sp)
    nop
    srl t1, t0, 24
    bnez t1, window_original
    lui t1, 0x0200
    or t0, t0, t1
    sw t0, 0x10(sp)
window_original:
    j 0x8004DE34
    nop
''',WINDOW);wb+=bytes(sum(bool(table[i*8+j])<<j for j in range(8))for i in range(16));assert WINDOW+len(wb)<=0x8000DE00
 return [(WINDOW,wb),(CHAR,cb),(RASTER,rb)],{**rl,**cl,**wl},report

def patch_core(exe):
 import vwf
 out=bytearray(exe);_,l,_=assemble()
 for a,old,target in [(0x8005BCB4,vwf.jal(0x8004DE34),'window_text'),(0x8004DAAC,0x24C2FFE0,'char_row'),(0x8004D910,0xA4A20010,'filter_sprite'),(0x8004D930,0x8F830240,'insert_second')]:
  i=0x800+a-0x80010000;assert struct.unpack_from('<I',out,i)[0]==old,hex(a)
  struct.pack_into('<I',out,i,vwf.jal(l[target])if a==0x8005BCB4 else vwf.j(l[target]))
  if a not in (0x8005BCB4,0x8004DAAC):struct.pack_into('<I',out,i+4,0)
 return bytes(out)

if __name__=='__main__':
 b,_,r=assemble();print([(hex(a),len(d))for a,d in b]);print('Compacted',sum(x['identical_ink_rows']for x in r),'glyphs using duplicate ink rows.')
