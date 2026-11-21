"""Normal briefing text and full-width narration wrapping; dry-run by default."""
import argparse
from functools import lru_cache
import json
from pathlib import Path
import re
import struct

import masm
import vwf
import wrap

ROOT=Path(__file__).resolve().parents[1]
BASE=0x800A97A8
CODE=0x800C6700
LIMIT=0x800C67A8
WIDTH=440  # native box (24,164,464,60), with 12-pixel side margins
ADVANCE=(0,1,3,4,5,7,8,9,11,12,13,15,16)
FLAGS=0x2200000C
HEADER_Y=19  # green bar y=16..30; center the visible 8-pixel capital glyphs
ASM=r'''
brief_text:
    lui t0, 0x2200
    or a3, a3, t0
    j 0x8004DDFC
    nop
brief_window_draw:
    lw t0, 0x30(a0)
    nop
    lw t0, 0(t0)
    li t1, 0xFFFFFF
    lw t2, 0x5C(t0)
    lui t3, 0x2200
    and t2, t2, t1
    or t2, t2, t3
    sw t2, 0x5C(t0)
    j 0x8005AC40
    nop
brief_setup:
    addiu sp, sp, -0x20
    sw ra, 0x1C(sp)
    sw a0, 0x18(sp)
    jal 0x8005BF60
    nop
    lw a0, 0x18(sp)
    jal 0x8003A304
    nop
    la t0, brief_window_draw
    sw t0, 0x28(v0)
    lw ra, 0x1C(sp)
    jr ra
    addiu sp, sp, 0x20
'''


@lru_cache(maxsize=256)
def char_width(ch):
    if 32<=ord(ch)<127:
        widths,_=vwf.width_tables()
        return ADVANCE[widths[ord(ch)-32]]
    return 16


def width(text):
    return sum(sum(char_width(c) for c in t) if k=='text' else 6*16 if k=='name' else 0
               for k,t in wrap.tokens(text))


def reflow(text):
    # Explicit line breaks are the branch-choice layouts; preserve them.
    if text.startswith('Episode ') or wrap.NL in text or text.endswith(' '):
        return text
    result=[];line=''
    # Keep quoted proper names together instead of orphaning "Jin" on a row.
    for word in re.findall(r'"[^"]*"\S*|\S+',text):
        candidate=(line+' '+word) if line else word
        if width(candidate)>WIDTH and line:
            result.append(line);line=word
        else:line=candidate
        if width(line)>WIDTH:raise ValueError('Briefing word exceeds the narration width')
    result.append(line)
    if len(result)>4:raise ValueError('Briefing narration exceeds four native rows')
    return wrap.NL.join(result)


def assemble():
    code,labels=masm.assemble(ASM,CODE)
    if CODE+len(code)>LIMIT:raise ValueError('Briefing typography overlaps flight overlay')
    return code,labels


def patch_overlay(data):
    code,labels=assemble()
    if len(data)>CODE-BASE:raise ValueError('Briefing helpers overlap typography code')
    out=bytearray(data).ljust(CODE-BASE,b'\0')+code
    # Only the episode title moves; projected place names retain their positions.
    assert struct.unpack_from('<I',out,0x800C3960-BASE)[0]==0x24050012
    struct.pack_into('<I',out,0x800C3960-BASE,0x24050000|HEADER_Y)
    for address,old,target in [(0x800C3978,0x8004DDFC,'brief_text'),
                               (0x800C4E98,0x8004DDFC,'brief_text'),
                               (0x800BE060,0x8005BF60,'brief_setup')]:
        assert struct.unpack_from('<I',out,address-BASE)[0]==vwf.jal(old),hex(address)
        struct.pack_into('<I',out,address-BASE,vwf.jal(labels[target]))
    return bytes(out)


def audit():
    rows=json.loads((ROOT/'work/translation/en/data.en.json').read_text())
    report=[]
    for r in rows:
        if not r['id'].startswith('BRF_'):continue
        new=reflow(r['en'])
        assert new.replace(wrap.NL,' ')==r['en'].replace(wrap.NL,' '),r['id']
        widths=[width(s.rstrip())for s in new.split(wrap.NL)]
        # Native headings start at x=34; the right edge is x=488.
        limit=454 if r['en'].startswith('Episode ') else WIDTH
        assert all(w<=limit for w in widths),(r['id'],widths)
        report.append(dict(id=r['id'],text=new,widths=widths,changed=new!=r['en']))
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--apply',action='store_true');a=p.parse_args()
    code,_=assemble();rows=audit()
    print(json.dumps(dict(rows=len(rows),code_bytes=len(code),code_end=hex(CODE+len(code)),
                         glyph=[16,10],narration_width=WIDTH,sample=next(r for r in rows if r['id']=='BRF_0310')),indent=2))
    if a.apply:
        out=ROOT/'work/ui/briefing/v0817';out.mkdir(parents=True,exist_ok=True)
        (out/'wrap-check.json').write_text(json.dumps(rows,indent=2)+'\n')
