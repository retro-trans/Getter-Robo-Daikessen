"""Navigate a fresh muted project emulator to a chapter's map; dry-run default."""
import argparse
from pathlib import Path
import time
import gdbdbg

import smoke


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chapter', type=int, default=2)
    parser.add_argument('--out', type=Path, default=Path('work/ui/battle_skip/v081'))
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--resume-story', action='store_true')
    parser.add_argument('--fast-story', action='store_true', help='advance story using native buttons and whole-string menu detection')
    args = parser.parse_args()
    print(f'Native chapter {args.chapter}: briefing -> story -> map. No save or disc writes.', flush=True)
    if not args.apply:
        return
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / 'navigation.log').open('w', encoding='utf8') as log:
        for attempt in range(100):
            try:
                run = smoke.Run(log)
                break
            except ConnectionRefusedError:
                time.sleep(.1)
        else:
            raise ConnectionError('Project emulator debugger did not start')
        try:
            run.d.g.cmd(f'z0,{smoke.DRAW:x},4')
            if not args.resume_story:
                print('Waiting for native program dispatch...', flush=True)
                run.switch(10, args.chapter)
                print('Opening chapter briefing...', flush=True)
                if run.press_until('Next Map', 'circle', 60, 60)[0] is None:
                    raise RuntimeError('Briefing menu not reached')
                run.plain(30)
                run.press('down', 6, 12)
                run.press('circle', 1, 40)
                run.press('up', 1, 12)
                run.press('circle', 1, 60)
            print('Advancing story to map...', flush=True)
            if args.fast_story:
                # Dialogue rendering calls DE34 once per glyph. Watching the
                # whole-string entry instead avoids thousands of unnecessary
                # debugger stops while still stopping at the first map menu.
                g=run.d.g;g.cmd(f'z0,{smoke.DRAW:x},4');g.cmd('Z0,8004ddfc,4')
                frames=0;found=False
                try:
                    while frames<9000:
                        g.s.sendall(b'$c#63');g._recv_packet();r=run.d.regs()
                        if r[37]==0x8004DDFC:
                            text=g.read(r[6],96).split(b'\0')[0]
                            if b'Choose action' in text:found=True;break
                        elif r[37]==run.d.bp and r[5]==r[29]:
                            if frames%12<3:run.d.setreg(gdbdbg.PAD_REG,r[gdbdbg.PAD_REG]|gdbdbg.BTN['circle'])
                            frames+=1
                finally:g.cmd('z0,8004ddfc,4')
                if not found:raise RuntimeError('Map not reached with native story input')
            elif run.press_until('Choose action', 'circle', 250, 45)[0] is None:
                raise RuntimeError('Map not reached')
            run.plain(10)
            run.shot(str(args.out / 'map.png'))
            print('Reached native map.', flush=True)
        finally:
            run.d.close()


if __name__ == '__main__':
    main()
