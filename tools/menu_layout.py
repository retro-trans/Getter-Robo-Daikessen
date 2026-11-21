"""Aspect-correct sortie and flight-menu layouts; dry-run unless --apply."""
import argparse
import json
from pathlib import Path
import struct

import masm
import status_layout
import vwf

ROOT = Path(__file__).resolve().parents[1]
BRIEF_BASE = 0x800A97A8
CODE = 0x800C6220
LIMIT = 0x800C6700  # final 168 bytes are reserved for briefing typography
FLIGHT_BASE = 0x800C67A8

ASM = r'''
sortie_text:
    li t0, 0x800B8A64
    bne ra, t0, text_unit_name
    nop
    li t0, 118
    multu s1, t0
    mflo a0
    addiu a0, a0, 297
    li a1, 85
    li a3, 0x40042
    j fit_text
    nop
text_unit_name:
    li t0, 0x800B8880
    bne ra, t0, text_label
    nop
    lhu a0, 0(fp)
    lhu a1, 2(fp)
    addiu a0, a0, 34
    addiu a1, a1, 3
    li a3, 0x4004E
    j fit_text
    nop
sortie_ascii:
    la a2, text_level
    li t1, 0x800B8418
    beq ra, t1, text_skill
    nop
    li t1, 0x800B835C
    bne ra, t1, text_small
    nop
    la a2, text_exp
    b text_small
    nop
text_label:
    # The five assignment column headings share this native caller range.
    li t1, 0x800B84E4
    subu t1, ra, t1
    sltiu t1, t1, 0xC1
    bnez t1, text_small
    lui t0, 0x3800
    ori t0, t0, 0xC
    li t1, 0x800B87E8
    beq ra, t1, text_small
    nop
    li t1, 0x800B88B0
    beq ra, t1, text_small
    nop
    li t1, 0x800B8AC4
    beq ra, t1, text_small
    nop
    li t1, 0x800B83E0
    beq ra, t1, text_stance
    nop
    li t1, 0x800B8418
    beq ra, t1, text_skill
    nop
    b text_draw
    nop
text_stance:
    li a0, 162
    b text_small
    li a1, 79
text_skill:
    li a0, 207
    li a1, 79
text_small:
    li t0, 0x3400000C
text_draw:
    or a3, a3, t0
    j 0x8004DDFC
    nop

sortie_number:
    lw t0, 0x10(sp)
    addiu sp, sp, -0x70
    sw ra, 0x6C(sp)
    sw a0, 0x68(sp)
    sw a1, 0x64(sp)
    sw a3, 0x60(sp)
    move t1, a2
    la a1, fmt_number
    beqz t0, number_format
    nop
    la a1, fmt_two
    li t2, 2
    beq a3, t2, number_format
    nop
    la a1, fmt_three
    li t2, 3
    beq a3, t2, number_format
    nop
    la a1, fmt_number
number_format:
    move a2, t1
number_format_call:
    jal 0x8001ACB8
    addiu a0, sp, 0x20
    lw a0, 0x68(sp)
    lw a1, 0x64(sp)
    lw t0, 0x6C(sp)
    li t1, 0x800B832C
    li a3, 0x3400000C
    beq t0, t1, number_level
    nop
    li t1, 0x800B8390
    beq t0, t1, number_exp
    nop
    li t1, 0x800B844C
    beq t0, t1, number_skill
    nop
    li t1, 0x800B88F8
    beq t0, t1, number_stat
    nop
    li t1, 0x800B8B10
    beq t0, t1, number_stat
    nop
    lw t0, 0x60(sp)
    li t3, 6
    sll t0, t0, 3
    b number_align
    addu a0, a0, t0
number_level:
    li a0, 52
    b number_draw
    li a1, 79
number_exp:
    li a0, 112
    b number_draw
    li a1, 79
number_skill:
    li a0, 226
    b number_draw
    li a1, 79
number_stat:
    addiu a0, a0, 41
    li t3, 6
number_align:
    addiu t0, sp, 0x20
number_count:
    lbu t1, 0(t0)
    addiu t0, t0, 1
    beqz t1, number_draw
    nop
    b number_count
    subu a0, a0, t3
number_draw:
    jal 0x8004DDFC
    addiu a2, sp, 0x20
    lw ra, 0x6C(sp)
    jr ra
    addiu sp, sp, 0x70
fmt_number:
    .ascii "%d"
    .byte 0
fmt_two:
    .ascii "%02d"
    .byte 0
fmt_three:
    .ascii "%03d"
    .byte 0
text_level:
    .ascii "Lv"
    .byte 0
text_exp:
    .ascii "Exp"
    .byte 0
    .align 4
'''


def assemble():
    rows=json.loads((ROOT/'work/translation/en/ui.en.json').read_text(encoding='utf8'))
    widths,_=vwf.width_tables()
    advance=(0,1,2,3,4,5,6,6,7,8,9,10,11)
    def width(text):
        import re
        return sum(advance[widths[ord(c)-32]] for c in re.sub(r'%[0-9]','',text))
    for row in rows:
        address=int(row['addr'],16)
        if row['file']=='briefing' and 0x800AB09C<=address<=0x800AB180:
            if width(row['en'])>226:raise ValueError(f"Group header exceeds its panel: {row['id']}")
        if row['file']=='exe' and 0x80015BA8<=address<0x800174CE and row.get('en'):
            lines=['']
            for word in row['en'].split():
                candidate=(lines[-1]+' '+word).strip()
                if width(candidate)<=78:lines[-1]=candidate
                else:lines.append(word)
            if len(lines)>2 or any(width(line)>78 for line in lines):
                raise ValueError(f"Unit name exceeds two rows: {row['id']}")
    helper = status_layout.HELPERS.split('fit_text:\n', 1)[1]
    helper = 'fit_text:\n'+helper
    helper = helper.replace('0x3800000A', '0x3400000C').replace('0x3200000E', '0x3400000C').replace('addiu s1, s1, 16', 'addiu s1, s1, 14')
    _, resident = vwf.build_cave()
    code, labels = masm.assemble(ASM+helper, CODE, symbols={
        'font_width': resident['width'], 'status_advance': resident['STATUS_MED_ADV']})
    if CODE+len(code) > LIMIT: raise ValueError('Sortie helpers overlap briefing typography')
    return code, labels


def word(out, base, address, old, new):
    current = struct.unpack_from('<I', out, address-base)[0]
    if current != old: raise ValueError(f'{address:#x}: {current:08x} != {old:08x}')
    struct.pack_into('<I', out, address-base, new)


def patch_briefing(data):
    code, labels = assemble()
    if len(data) > CODE-BRIEF_BASE: raise ValueError('Existing briefing extension overlaps layout helpers')
    out = bytearray(data).ljust(CODE-BRIEF_BASE, b'\0')+code
    word(out, BRIEF_BASE, 0x800B903C, 0x27BDFFE8, vwf.j(labels['sortie_text']))
    word(out, BRIEF_BASE, 0x800B9040, 0x3C021000, 0)
    word(out, BRIEF_BASE, 0x800B9074, 0x27BDFFE8, vwf.j(labels['sortie_ascii']))
    word(out, BRIEF_BASE, 0x800B9078, 0x3C021000, 0)
    word(out, BRIEF_BASE, 0x800B90AC, 0x27BDFFE0, vwf.j(labels['sortie_number']))
    word(out, BRIEF_BASE, 0x800B90B0, 0x3C081000, 0)
    # Custom-pilot rank belongs beside the name, above the skill metadata.
    # Reuse the compact draw entry, retaining the native red palette/value.
    word(out, BRIEF_BASE, 0x800B84A4, vwf.jal(0x800B903C), vwf.jal(labels['text_small']))
    # The selected pilot's identity gets its own row; level/experience sit below.
    edits = {0x800B8298:(0x24840005,0x2404001E), 0x800B82A4:(0x24A50003,0x24050037),
             0x800B82D8:(0x2484007D,0x2404001E), 0x800B82E4:(0x24A50009,0x2405004F),
             0x800B8340:(0x248400A5,0x24040056), 0x800B834C:(0x24A50009,0x2405004F),
             0x800B8480:(0x2484FFBF,0x2484FFCA), 0x800B848C:(0x24A5001B,0x24A5000A),
             0x800B8834:(0x24150018,0x24150024), 0x800B8820:(0x2416001B,0x24160020),
             0x800B88E4:(0x24A50006,0x24A50007),
             0x800B8A78:(0x24150033,0x2415002D),
             0x800B8980:(0x26D60018,0x26D60016), 0x800B8994:(0x26B50018,0x26B50016)}
    for address,(old,new) in edits.items(): word(out, BRIEF_BASE, address, old, new)
    for i in range(4):
        x,y,_,_ = struct.unpack_from('<4h', out, 0x800C56D8-BRIEF_BASE+i*8)
        # Native model icons become square at the display's 4:3 pixel aspect.
        struct.pack_into('<8h', out, 0x800C5888-BRIEF_BASE+i*16,
                         x+5,y+3,x+29,y+3,x+5,y+33,x+29,y+33)
        for row in range(6):
            struct.pack_into('<4h', out, 0x800C57B8-BRIEF_BASE+(i*6+row)*8,
                             x+80,y+42+row*22,33,6)
    # Keep the original panel palette and semitransparency styles.
    return bytes(out)


def patch_flight(data):
    out = bytearray(data)
    sites = []
    # These are the 480-line menu's 12x24 text calls; gameplay's 240-line text
    # uses separate flags. Opt into the status screen's 19x24 cell dimensions.
    for offset in range(0x800E1C8C-FLIGHT_BASE, 0x800E4A00-FLIGHT_BASE, 4):
        if struct.unpack_from('<I', out, offset)[0] == 0x3C071000:
            struct.pack_into('<I', out, offset, 0x3C073800)
            sites.append(FLIGHT_BASE+offset)
    if len(sites) != 32: raise ValueError(f'Unexpected flight menu font sites: {len(sites)}')
    # The longer explanatory notice uses the same aspect at a smaller size.
    for address in (0x800E2884,0x800E28A4,0x800E28C0):
        word(out,FLIGHT_BASE,address,0x3C073800,0x3C073400)
    for address,old,new in ((0x800E550C,196,176),(0x800E5524,184,176),
                            (0x800E5530,208,176),(0x800E551C,280,276),
                            (0x800E5520,286,282),(0x800E5528,280,276),
                            (0x800E5568,184,176),(0x800E5574,280,292),
                            # Keep the native entrance animations' targets in
                            # agreement with the revised column positions.
                            (0x800E4A84,196,176),(0x800E4ACC,280,276),
                            (0x800E4AD0,286,282),(0x800E4B14,184,176),
                            (0x800E4B5C,-280,-276),(0x800E4B80,280,276),
                            (0x800E4B8C,208,176),(0x800E4BD4,-280,-276),
                            (0x800E4BF8,280,276),(0x800E4CA4,184,176),
                            (0x800E4CEC,-280,-292),(0x800E4D10,280,292),
                            (0x800E4D1C,184,176),(0x800E4D64,-280,-292),
                            (0x800E4D88,280,292),(0x800E4D94,184,176),
                            (0x800E4DDC,-280,-292),(0x800E4E00,280,292)):
        current=struct.unpack_from('<I',out,address-FLIGHT_BASE)[0]
        if current&0xFFFF != old&0xFFFF:raise ValueError(f'Unexpected menu coordinate at {address:#x}')
        struct.pack_into('<I',out,address-FLIGHT_BASE,(current&0xFFFF0000)|(new&0xFFFF))
    return bytes(out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    code, _ = assemble()
    report = dict(version='0.8.7', sortie_helper=[hex(CODE),hex(CODE+len(code))],
                  sortie_glyph=[19,24], sortie_secondary_glyph=[11,13], flight_menu_glyph=[19,24])
    print(json.dumps(report, indent=2))
    if args.apply:
        import ui_text
        import episode_preview
        import minigame_subtitles
        images,_,problems=ui_text.apply(log=lambda *args:None)
        if problems:raise ValueError(problems)
        brief=episode_preview.patch_overlay(vwf.patch_overlay('briefing',images['briefing'],BRIEF_BASE))
        flight=minigame_subtitles.patch_overlay(vwf.patch_overlay('flight',images['flight'],FLIGHT_BASE))
        (ROOT/'work/build/briefing_v083.bin').write_bytes(patch_briefing(brief))
        (ROOT/'work/build/flight_v083.bin').write_bytes(patch_flight(flight))
        folder = ROOT/'work/ui/menu_layout'; folder.mkdir(parents=True,exist_ok=True)
        (folder/'layout_v087.json').write_text(json.dumps(report,indent=2)+'\n')
