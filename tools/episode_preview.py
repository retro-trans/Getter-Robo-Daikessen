"""Next-episode preview audio and subtitle tooling. Defaults to dry-run.

Original transcripts and extracted audio stay in ignored work/source/.
"""
import argparse
import json
from pathlib import Path
import struct
import subprocess

import build_disc
import movie
import masm
import pac
import vwf

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / 'work/source/preview_analysis'
JAR = ROOT / 'tools/vendor/jpsxdec/jpsxdec_v2.1-beta/jpsxdec.jar'
BASE = 0x800A97A8
TRANSLATION = ROOT/'work/translation/en/episode_previews.en.json'
STATE_SIZE = 0x824
CODE = 0x800C6080

# Subtitle data lives in the native preview heap object and is freed by its
# normal destructor. Code fits before flight.bin's fixed load address.
ASM = r'''
copy_subtitles:
    sw zero, 0x24(a1)
    lw t0, 0(a0)
    nop
    sll t0, t0, 2
    addu t0, a0, t0
    lw t0, 0(t0)
    nop
    addu t0, a0, t0
    lw t1, -0x10(t0)
    addiu t0, t0, 16
    sltiu t2, t1, 0x801
    beqz t2, copy_done
    nop
    lw t2, 0(t0)
    li t3, 0x42555350
    bne t2, t3, copy_done
    nop
    addiu t2, a1, 0x24
copy_loop:
    lbu t3, 0(t0)
    addiu t0, t0, 1
    sb t3, 0(t2)
    addiu t1, t1, -1
    bgtz t1, copy_loop
    addiu t2, t2, 1
copy_done:
    j 0x80038958
    nop

draw_subtitles:
    addiu sp, sp, -0x28
    sw ra, 0x24(sp)
    sw s0, 0x20(sp)
    sw s1, 0x1c(sp)
    sw s2, 0x18(sp)
    move s0, a0
    jal 0x800B2AE8
    nop
    lw t0, 0x24(s0)
    li t1, 0x42555350
    bne t0, t1, draw_done
    nop
    lw t0, 8(s0)
    nop
    bnez t0, draw_done
    nop
    move a0, s0
    jal 0x800B2DE4
    nop
    beqz v0, draw_done
    nop
    li t0, 0x8008961C
    lw t1, 0(t0)
    sll v0, v0, 4
    beqz t1, draw_done
    nop
    addu t1, t1, v0
    lw t3, -0x1C(t0)
    lw t2, 4(t0)
    bne t1, t3, draw_done
    nop
    lw t1, 0(t1)
    nop
    subu t2, t2, t1
    sltiu t0, t2, 6000
    beqz t0, draw_done
    nop
    lw t3, 0x28(s0)
    addiu s1, s0, 0x2c
    addiu s2, s0, 0x24
find_cue:
    beqz t3, draw_done
    nop
    lhu t0, 0(s1)
    lhu t1, 2(s1)
    sltu t0, t2, t0
    bnez t0, draw_done
    nop
    sltu t1, t2, t1
    bnez t1, draw_cue
    nop
    addiu t3, t3, -1
    b find_cue
    addiu s1, s1, 12
draw_cue:
    lhu a0, 4(s1)
    lhu a2, 8(s1)
    addiu a1, zero, 208
    addu a2, s2, a2
    jal 0x8004DDFC
    addiu a3, zero, 5
    lhu a2, 10(s1)
    nop
    beqz a2, draw_done
    nop
    lhu a0, 6(s1)
    addiu a1, zero, 221
    addu a2, s2, a2
    jal 0x8004DDFC
    addiu a3, zero, 5
draw_done:
    lw ra, 0x24(sp)
    lw s0, 0x20(sp)
    lw s1, 0x1c(sp)
    lw s2, 0x18(sp)
    jr ra
    addiu sp, sp, 0x28
'''


def subtitle_blob(cues):
    widths, _ = vwf.width_tables()
    records = bytearray()
    strings = bytearray()
    head_size = 8+12*len(cues)
    previous = 0
    for cue in cues:
        start, end = round(cue['start']*150), round(cue['end']*150)
        if not previous <= start < end < 6000:
            raise ValueError(f'Overlapping or invalid cue: {cue}')
        previous = end
        lines = cue['lines']
        if not 1 <= len(lines) <= 2:
            raise ValueError(cue)
        coords, offsets = [], []
        for line in lines:
            raw = line.encode('ascii')
            if any(c in line for c in '%@$\\'):
                raise ValueError('Subtitle contains a native control character')
            width = sum(widths[c-32] for c in raw)
            if width > 292:
                raise ValueError(f'Line too wide ({width}px): {line}')
            coords.append((320-width)//2)
            offsets.append(head_size+len(strings))
            strings += raw+b'\0'
        if len(lines) == 1:
            coords.append(0)
            offsets.append(0)
        records += struct.pack('<6H', start,end,*coords,*offsets)
    blob = b'PSUB'+struct.pack('<I',len(cues))+records+strings
    if len(blob) > STATE_SIZE-0x24:
        raise ValueError('Subtitle data exceeds the native object allocation')
    return blob


def patch_overlay(data):
    code, labels = masm.assemble(ASM, CODE)
    if len(data) > CODE-BASE or CODE+len(code) > 0x800C67A8:
        raise ValueError('Preview code overlaps an overlay boundary')
    out = bytearray(data).ljust(CODE-BASE,b'\0')+code
    patches = {
        0x800B2678: (0x24040024, 0x24040000 | STATE_SIZE),
        0x800B2830: (0x0C00E256, 0x0C000000 | ((labels['copy_subtitles']>>2)&0x3ffffff)),
        0x800B2834: (0, 0x02002821), # a1 = native preview state
        0x800B2980: (0x0C02CABA, 0x0C000000 | ((labels['draw_subtitles']>>2)&0x3ffffff)),
    }
    for at,(old,new) in patches.items():
        current = struct.unpack_from('<I',out,at-BASE)[0]
        if current != old:
            raise ValueError(f'{at:08x}: unexpected hook word {current:08x} != {old:08x}')
        struct.pack_into('<I',out,at-BASE,new)
    return bytes(out)


def build_files(orig_vfs, files, vfs_file):
    document = json.loads(TRANSLATION.read_text(encoding='utf8'))
    if {r['name'] for r in inventory()} != set(document['previews']):
        raise ValueError('Incomplete episode preview subtitles')
    for name,cues in document['previews'].items():
        blob = subtitle_blob(cues)
        path = 'flight/'+name.lower()+'.pac'
        items = pac.container_items(files.get(path) or vfs_file(orig_vfs,path))
        prefix = struct.pack('<4I',len(blob)+16,0,255,0)
        items.append(dict(name='SUBTITLE.BIN',usize=len(blob),psize=len(blob),time=0,
                          mode=0,prefsz=2,payload=prefix+blob))
        rebuilt = pac.build_container(items)
        row = next(r for r in inventory() if r['name'] == name)
        overlay = (ROOT/'work/source/vfs/bin/briefing.bin').read_bytes()
        limit = struct.unpack_from('<I',overlay,0x800C54AC+row['index']*4-BASE)[0]
        if len(rebuilt) > limit:
            raise ValueError(f'{name}: {len(rebuilt)} bytes exceed native allocation {limit}')
        files[path] = rebuilt


def check():
    import wave
    document = json.loads(TRANSLATION.read_text(encoding='utf8'))
    total = 0
    for row in inventory():
        cues = document['previews'][row['name']]
        blob = subtitle_blob(cues)
        with wave.open(str(ANALYSIS/row['name']/'audio.wav'),'rb') as audio:
            duration = audio.getnframes()/audio.getframerate()
        if cues[-1]['end'] > duration+0.1:
            raise ValueError(f"{row['name']}: subtitles outlast original audio")
        total += len(cues)
        print(row['name'],len(cues),'cues',len(blob),'bytes',round(duration,2),'seconds')
    overlay = patch_overlay((ROOT/'work/source/vfs/bin/briefing.bin').read_bytes())
    print('Checked',total,'cues / 23 previews; code ends',hex(BASE+len(overlay)))


def inventory():
    overlay = (ROOT/'work/source/vfs/bin/briefing.bin').read_bytes()
    xap = (ROOT/'work/source/disc/GRXAP.XAP').read_bytes()
    def word(at):
        return struct.unpack_from('<I', overlay, at-BASE)[0]
    result = []
    for index in range(24):
        if index == 5:  # unused route: native XA switch returns zero
            continue
        branch = word(0x800AAFD4+index*4)
        voice = word(branch+4) & 65535
        pointer = word(0x800C556C+index*4)
        name = overlay[pointer-BASE:overlay.index(b'\0', pointer-BASE)].decode('ascii')
        first, last, channel, _ = struct.unpack_from('<4I', xap, 0x800+voice*16)
        result.append(dict(index=index, name=Path(name).stem, voice=voice,
                           first=first, last=last, channel=channel & 65535))
    return result


def prepare(apply=False):
    rows = inventory()
    if not apply:
        for r in rows:
            print(r['name'], 'voice', hex(r['voice']), 'sectors', r['first'], r['last'])
        print(f'Extract {len(rows)} unmodified XA streams; decode locally to WAV.')
        return
    disc = build_disc.Disc(str(ROOT/'Getter Robo Daikessen! (Japan).bin'), 'rb')
    try:
        lba = disc.entries['GRXAP.XAP'].lba
        for r in rows:
            target = ANALYSIS/r['name']
            target.mkdir(parents=True, exist_ok=True)
            raw = target/'voice.xa'
            if not raw.exists():
                with raw.open('wb') as out:
                    for n in range(r['first'], r['last']+1):
                        sector = disc.raw(lba+n)
                        if int.from_bytes(sector[16:18], 'little') == r['channel'] and sector[18] & 4:
                            out.write(sector)
            if not (target/'audio.wav').exists():
                with (target/'decode.log').open('w') as log:
                    subprocess.run(['java','-jar',str(JAR),'-f',str(raw),'-a','audio',
                                    '-dir',str(target)],stdout=log,stderr=subprocess.STDOUT,check=True)
                wavs = list(target.glob('*.wav'))
                if len(wavs) != 1:
                    raise ValueError(f'{target}: expected one decoded WAV, found {wavs}')
                wavs[0].rename(target/'audio.wav')
            print(r['name'], raw.stat().st_size//2352, 'XA sectors', flush=True)
        movie.write_json(ANALYSIS/'inventory.json', rows)
    finally:
        disc.f.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','transcribe','translate','check'])
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--model', default='large-v3')
    args = parser.parse_args()
    if args.command == 'prepare':
        prepare(args.apply)
    elif args.command == 'check':
        check()
    else:
        movie.ANALYSIS = ANALYSIS
        movie.transcribe(args.apply, args.model, args.command)
