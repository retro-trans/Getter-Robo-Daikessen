"""Preview native next-episode subtitles in the muted project emulator.

Dry-run by default. Debugger-only navigation changes never enter the disc patch.
Start a fresh project DuckStation boot first; use --apply to select a preview.
"""
import argparse
import json
from pathlib import Path
import struct
import time

import episode_preview as ep
import gdbdbg
import masm


def capture(name, apply=False, times=(1,10), output=None, voice_off=False, complete=False):
    row = next(r for r in ep.inventory() if r['name'] == name)
    _, labels = masm.assemble(ep.ASM, ep.CODE)
    print(name, 'native preview index', row['index'], 'capture at',list(times),'seconds', flush=True)
    if voice_off:
        print('Also verify that disabled voices skip stale subtitle clocks.',flush=True)
    if complete:
        print('Also wait for native cleanup and subsequent game frames.',flush=True)
    if not apply:
        return
    d = gdbdbg.Dbg()
    g = d.g
    g.s.settimeout(50)
    active = {d.bp}
    def add(at):
        g.cmd(f'Z0,{at:x},4');active.add(at)
    def remove(at):
        g.cmd(f'z0,{at:x},4');active.discard(at)
    def until(at):
        add(at)
        while True:
            g.s.sendall(b'$c#63');g._recv_packet()
            r = d.regs()
            if voice_off and at == labels['draw_done'] and r[37] == labels['draw_cue']:
                raise ValueError('Disabled voices unexpectedly selected a subtitle cue')
            if r[37] == at:
                remove(at)
                return r
    target = (Path(output) if output else ep.ROOT/'work/ui/episode_previews/v016')/name
    target.mkdir(parents=True,exist_ok=True)
    try:
        remove(d.bp)
        until(0x8004CF48)
        d.setreg(4,10);d.setreg(5,2)
        # Native flow loads briefing.bin, then normally creates its briefing task.
        # For this isolated test, create the announcement task in that same slot.
        until(0x800B0AA0)
        d.setreg(37,0x800B2620)
        r = until(0x800B2648)
        if voice_off:
            # Runtime-only setting: exercise the native disabled-voices path.
            g.write(r[28]+0x908,bytes(4))
        if not r[5]:
            g.write(0x8000DD00,bytes(32));d.setreg(5,0x8000DD00)
        # Skip only route selection; all loading/drawing/audio remain native.
        until(0x800B26C8)
        d.setreg(2,row['index']+2);d.setreg(37,0x800B26D0)
        r = until(labels['copy_subtitles'])
        state = r[5]
        print('state',hex(state),'PAC',hex(r[4]),flush=True)
        if voice_off:
            add(labels['draw_cue'])
            r=until(labels['draw_done'])
            remove(labels['draw_cue'])
            if r[37] != labels['draw_done']:
                raise ValueError('Disabled voices unexpectedly drew a cue')
            (target/'voice-off.json').write_text(json.dumps({'preview':name,'stale_audio_skipped':True},indent=2)+'\n')
            print('Disabled voices: stale audio record skipped safely.',flush=True)
            return
        r = until(labels['draw_cue'])
        if g.read(state+0x24,4) != b'PSUB':
            raise ValueError('Native subtitle copy failed')
        reports=[]
        for seconds in times:
            # Let native playback run freely, then arm a breakpoint on the next
            # subtitle draw. This avoids rewriting already-cached game code.
            clock = struct.unpack('<I',g.read(0x80089620,4))[0]
            pointer = struct.unpack('<I',g.read(0x80089600,4))[0]
            first = struct.unpack('<I',g.read(pointer,4))[0]
            g.s.sendall(b'$c#63')
            time.sleep(max(0.1,seconds-(clock-first)/150)+0.05)
            add(labels['draw_cue'])
            while True:
                packet=g._recv_packet()
                r=d.regs()
                if r[37] == labels['draw_cue']:
                    break
            remove(labels['draw_cue'])
            clock = struct.unpack('<I',g.read(0x80089620,4))[0]
            pointer = struct.unpack('<I',g.read(0x80089600,4))[0]
            table = struct.unpack('<I',g.read(0x8008961C,4))[0]
            actual_voice = (pointer-table)//16
            if actual_voice != row['voice']:
                raise ValueError(f'Wrong native voice: {actual_voice:x} != {row["voice"]:x}')
            first = struct.unpack('<I',g.read(pointer,4))[0]
            elapsed = (clock-first)/150
            cue = struct.unpack('<6H',g.read(r[17],12))
            text = g.read(state+0x24+cue[4],100).split(b'\0')[0].decode('ascii')
            reports.append(dict(seconds=elapsed,first_line=text,state=hex(state),voice=actual_voice))
            print(elapsed,text,flush=True)
            for y,suffix in [(0,'a'),(240,'b')]:
                pixels=d.grab(0,y,320,240)
                gdbdbg.write_png(str(target/f'{seconds:02}_{suffix}.png'),320,240,pixels)
        (target/'native.json').write_text(json.dumps(reports,indent=2)+'\n')
        if complete:
            r=until(0x800B27B8)
            if struct.unpack('<I',g.read(r[4]+0x30,4))[0] != state:
                raise ValueError('Wrong preview object at cleanup')
            until(r[31])
            add(d.bp);d.wait(30);remove(d.bp)
            (target/'cleanup.json').write_text(json.dumps({'preview':name,'native_destructor_returned':True,'subsequent_pad_frames':30},indent=2)+'\n')
            print('Native preview cleanup returned; game continued for 30 frames.',flush=True)
    finally:
        for at in active:
            g.cmd(f'z0,{at:x},4')
        d.close()


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('preview',choices=[r['name'] for r in ep.inventory()])
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--seconds',nargs='+',type=int,default=[1,10])
    parser.add_argument('--output-dir')
    parser.add_argument('--voice-off',action='store_true')
    parser.add_argument('--complete',action='store_true')
    args=parser.parse_args()
    capture(args.preview,args.apply,args.seconds,args.output_dir,args.voice_off,args.complete)
