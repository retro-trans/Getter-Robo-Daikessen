"""Capture the reported Episode 2 dialogue in the muted project emulator.

Start the new disc first. Dry-run by default; no disc or save-file writes.
"""
import argparse
import json
from pathlib import Path

import gdbdbg
import smoke


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--out', type=Path, default=Path('work/ui/dialogue/v0811/native'))
    args = parser.parse_args()
    print('Episode 2: briefing -> reported Ryoma dialogue; capture both explicit pages.', flush=True)
    if not args.apply:
        return
    args.out.mkdir(parents=True, exist_ok=True)
    with (args.out / 'navigation.log').open('w', encoding='utf8') as log:
        run = smoke.Run(log)
        try:
            run.d.g.cmd(f'z0,{smoke.DRAW:x},4')
            print('Opening chapter briefing...', flush=True)
            run.switch(10, 2)
            if run.press_until('Next Map', 'circle', 60, 60)[0] is None:
                raise RuntimeError('Briefing menu not reached')
            run.plain(30)
            run.press('down', 6, 12)
            run.press('circle', 1, 40)
            run.press('up', 1, 12)
            run.press('circle', 1, 60)
            print('Finding the reported dialogue...', flush=True)
            if run.press_until("I don't get the", 'circle', 250, 45)[0] is None:
                raise RuntimeError('Reported line not reached')
            run.plain(420)
            run.shot(str(args.out / 'ryoma-page1.png'))
            run.press('circle', 1, 20)
            run.plain(420)
            run.shot(str(args.out / 'ryoma-page2.png'))
            from PIL import Image
            for name in ('ryoma-page1', 'ryoma-page2'):
                Image.open(args.out / f'{name}.png').resize(
                    (960, 720), Image.Resampling.NEAREST).save(args.out / f'{name}-3x.png')
            (args.out / 'native.json').write_text(json.dumps(dict(
                version='0.8.11', row='MF02_047D', cold_disc_navigation=True,
                explicit_pages_captured=2), indent=2) + '\n', encoding='utf8')
            print('Captured both native dialogue pages.', flush=True)
        finally:
            run.d.close()


if __name__ == '__main__':
    main()
