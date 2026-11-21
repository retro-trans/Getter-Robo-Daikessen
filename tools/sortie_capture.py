"""Navigate a fresh muted project emulator to chapter-2 assignment; dry-run."""
import argparse
from pathlib import Path
import time

import smoke


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apply',action='store_true')
    p.add_argument('--out',type=Path,default=Path('work/ui/menu_layout/v083-sortie-navigation'))
    a=p.parse_args()
    print('Native program 10 / chapter 2 -> briefing menu, ready for Assign.',flush=True)
    if not a.apply:return
    a.out.mkdir(parents=True,exist_ok=True)
    with (a.out/'navigation.log').open('w',encoding='utf8') as log:
        for _ in range(100):
            try:r=smoke.Run(log);break
            except ConnectionRefusedError:time.sleep(.1)
        else:raise ConnectionError('Project emulator debugger did not start')
        try:
            r.d.g.cmd(f'z0,{smoke.DRAW:x},4')
            r.switch(10,2)
            if r.press_until('Next Map','circle',60,60)[0] is None:raise ValueError('Briefing menu not reached')
            r.plain(30)
            r.shot(str(a.out/'briefing.png'))
        finally:r.d.close()
    print('Ready at native briefing menu.',flush=True)


if __name__=='__main__':main()
