"""Extract, translate and subtitle native flight-minigame speech. Dry-run default."""
import argparse
import json
from pathlib import Path
import struct

import episode_preview as ep
import movie
import masm

CODE=0x800E8B60
LIMIT=0x800F0000
ASM=r'''
draw_subtitles:
    addiu sp, sp, -0x30
    sw ra, 0x2c(sp)
    sw s0, 0x28(sp)
    sw s1, 0x24(sp)
    sw s2, 0x20(sp)
    sw s3, 0x1c(sp)
    jal 0x8002ED98
    nop
    beqz v0, draw_done
    nop
    li t0, 0x80089600
    lw t1, 0(t0)
    lw t3, 0x1c(t0)
    beqz t1, draw_done
    nop
    lw t2, 0x20(t0)
    subu t3, t1, t3
    srl t3, t3, 4
    la t4, voice_directory
find_voice:
    lw t5, 0(t4)
    nop
    bltz t5, draw_done
    nop
    beq t5, t3, found_voice
    nop
    b find_voice
    addiu t4, t4, 8
found_voice:
    lw t0, 0(t1)
    lw s2, 4(t4)
    subu s0, t2, t0
    sltiu t0, s0, 6000
    beqz t0, draw_done
    nop
    lw t3, 4(s2)
    addiu s1, s2, 8
find_cue:
    beqz t3, draw_done
    nop
    lhu t0, 0(s1)
    lhu t1, 2(s1)
    sltu t0, s0, t0
    bnez t0, draw_done
    nop
    sltu t1, s0, t1
    bnez t1, draw_cue
    nop
    addiu t3, t3, -1
    b find_cue
    addiu s1, s1, 12
draw_cue:
    li t0, 0x80089AA4
    lw t1, 0(t0)
    li t0, 0x800111A8
    sll t1, t1, 2
    addu t0, t0, t1
    lhu t1, 0(t0)
    lhu t2, 2(t0)
    addiu t1, t1, -320
    sra s3, t1, 1
    addiu s0, zero, 214
    addiu t3, zero, 226
    addiu t4, zero, 4
    addiu t1, zero, 480
    bne t2, t1, draw_lines
    nop
    addiu s0, zero, 350
    addiu t3, zero, 376
    li t4, 0x10000004
draw_lines:
    sw t3, 0x10(sp)
    sw t4, 0x14(sp)
    lhu t0, 10(s1)
    move a1, s0
    bnez t0, draw_first
    nop
    move a1, t3
draw_first:
    lhu a0, 4(s1)
    lhu a2, 8(s1)
    addu a0, a0, s3
    addu a2, s2, a2
    move a3, t4
    jal 0x8004DDFC
    nop
    lhu a2, 10(s1)
    nop
    beqz a2, draw_done
    nop
    lhu a0, 6(s1)
    lw a1, 0x10(sp)
    addu a0, a0, s3
    addu a2, s2, a2
    lw a3, 0x14(sp)
    jal 0x8004DDFC
    nop
draw_done:
    lw ra, 0x2c(sp)
    lw s0, 0x28(sp)
    lw s1, 0x24(sp)
    lw s2, 0x20(sp)
    lw s3, 0x1c(sp)
    jr ra
    addiu sp, sp, 0x30
voice_directory:
'''


def assemble():
    document=json.loads(TRANSLATION.read_text(encoding='utf8'))
    if set(document['voices'])!={r['name']for r in inventory()}:
        raise ValueError('Minigame voice inventory is incomplete')
    directory=''.join(f'    .word {v}, track_{v:04X}\n'for v in VOICE_IDS)+'    .word -1, 0\n'
    source=ASM+directory
    blobs=[]
    for v in VOICE_IDS:
        blob=ep.subtitle_blob(document['voices'][f'V{v:04X}'])
        source+=f'track_{v:04X}:\n    .space {(len(blob)+3)&~3}\n'
        blobs.append((v,blob))
    code,labels=masm.assemble(source,CODE)
    out=bytearray(code)
    for v,blob in blobs:
        o=labels[f'track_{v:04X}']-CODE;out[o:o+len(blob)]=blob
    if CODE+len(out)>LIMIT:
        raise ValueError('Minigame subtitles exceed the audited overlay extension')
    return bytes(out),labels


def patch_overlay(data):
    if len(data)>CODE-BASE:
        raise ValueError('Minigame code overlaps the original overlay')
    if struct.unpack_from('<2I',data,0x800C7A54-BASE)!=(0x03e00008,0):
        raise ValueError('Unexpected native minigame draw callback')
    code,labels=assemble()
    out=bytearray(data).ljust(CODE-BASE,b'\0')+code
    struct.pack_into('<I',out,0x800C7A54-BASE,0x08000000|((labels['draw_subtitles']>>2)&0x3ffffff))
    return bytes(out)

ROOT=Path(__file__).resolve().parents[1]
ANALYSIS=ROOT/'work/source/minigame_analysis'
TRANSLATION=ROOT/'work/translation/en/minigame.en.json'
BASE=0x800C67A8
# Direct native XA calls and their branch-selected constants in flight.bin.
VOICE_IDS=sorted({0x1c0,0x306,0x28e,0x541,0x524,0x482,0x54d,0x52e,
                  0x3fd,0x52b,0x52a,0x4ec,0x53d,0x351,
                  0x499,0x46d,0x4a0,0x3fc,0x4eb,0x4fe,0x3e4,0x3d8,0x3c4,
                  0x4cc,0x48e,0x4a6,0x4fc,0x52c,0x8b,0x4a7,0x22d,0x47f})


def inventory():
    xap=(ROOT/'work/source/disc/GRXAP.XAP').read_bytes()
    rows=[]
    for voice in VOICE_IDS:
        first,last,channel,_=struct.unpack_from('<4I',xap,0x800+voice*16)
        rows.append(dict(name=f'V{voice:04X}',voice=voice,first=first,last=last,channel=channel&65535))
    return rows


def check():
    import wave
    document=json.loads(TRANSLATION.read_text(encoding='utf8'))
    ids=set();count=0
    for row in inventory():
        cues=document['voices'][row['name']]
        ep.subtitle_blob(cues)
        with wave.open(str(ANALYSIS/row['name']/'audio.wav'),'rb')as audio:
            seconds=audio.getnframes()/audio.getframerate()
        if cues[-1]['end']>seconds+.05:
            raise ValueError('Cue outlasts native voice: '+row['name'])
        for cue in cues:
            if cue['id']in ids:raise ValueError('Duplicate cue ID')
            ids.add(cue['id'])
            for line in cue['lines']:
                if not all(32<=ord(ch)<127 for ch in line):raise ValueError('Invalid display character')
        count+=len(cues)
    code,_=assemble()
    print(f'Checked {count} cues / {len(VOICE_IDS)} voices; code/data end {CODE+len(code):#x}; flight subtitle rows 214/226, menu rows 350/376 (one-line cues on the lower row).')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','transcribe','translate','check'])
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--model',default='large-v3')
    args=parser.parse_args()
    if args.command=='prepare':
        ep.inventory=inventory
        ep.ANALYSIS=ANALYSIS
        ep.prepare(args.apply)
    elif args.command=='check':check()
    else:
        movie.ANALYSIS=ANALYSIS
        movie.transcribe(args.apply,args.model,args.command)
