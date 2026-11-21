"""Compare the map terrain tag before/after its coordinate fix; dry-run default.

Run from the chapter map in the muted project emulator. Only the single
drawing-coordinate instruction is changed in RAM, at a main-loop DrawSync.
"""
import argparse
import json
from pathlib import Path
import struct

import gdbdbg
import wrap

SITE = 0x80096270
DRAW = 0x80096290
OLD = 0x24040009
NEW = 0x24040003


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--land-fixture', action='store_true',
                        help='temporarily show the selected unit as Land in RAM; restore after capture')
    parser.add_argument('--out', type=Path, default=Path('work/ui/map_hud/v0812/native'))
    args = parser.parse_args()
    print('Open the map unit menu; capture/trace terrain label at x=9 and x=3.', flush=True)
    if not args.apply:
        return
    args.out.mkdir(parents=True, exist_ok=True)
    d = gdbdbg.Dbg()
    g = d.g
    g.s.settimeout(45)
    active = {d.bp}
    saved_terrain = None

    def add(at):
        g.cmd(f'Z0,{at:x},4')
        active.add(at)

    def remove(at):
        g.cmd(f'z0,{at:x},4')
        active.discard(at)

    def until(at):
        remove(d.bp)
        add(at)
        while True:
            g.s.sendall(b'$c#63')
            g._recv_packet()
            regs = d.regs()
            if regs[37] == at:
                remove(at)
                return regs

    def label():
        until(DRAW)
        # Stop at the callee so the preceding LW and JAL delay slot have
        # completed; a2 is still the old value at the call instruction itself.
        regs = until(0x8004DDFC)
        assert regs[31] == DRAW + 8
        text = g.read(regs[6], 16).split(b'\0')[0].decode('ascii')
        delay = struct.unpack('<I', g.read(DRAW + 4, 4))[0]
        assert delay == 0x2407000C and regs[7] == 0xC
        return dict(text=text, x=regs[4], y=regs[5], flags=regs[7], unit_record=regs[22])

    def capture(name):
        add(d.bp)
        d.wait(3)
        pixels, _ = gdbdbg.displayed_rect(d)
        gdbdbg.write_png(str(args.out / f'{name}.png'), 320, 240, pixels)
        from PIL import Image
        Image.open(args.out / f'{name}.png').resize(
            (960, 720), Image.Resampling.NEAREST).save(args.out / f'{name}-3x.png')

    try:
        d.press('circle')
        d.wait(8)
        for _ in range(3):
            d.press('down')
        d.wait(8)
        before = label()
        if args.land_fixture and before['text'] != 'Lnd':
            record = before['unit_record']
            assert 0x80010000 <= record < 0x80200000
            until(gdbdbg.DRAWSYNC)
            saved_terrain = (record + 0xE, g.read(record + 0xE, 2))
            g.write(record + 0xE, struct.pack('<H', 1))
            before = label()
        assert before['text'] == 'Lnd', before
        assert before['x'] == 9, before
        capture('before')
        regs = until(gdbdbg.DRAWSYNC)
        assert regs[32] & 5 and 0x80010000 <= regs[29] < 0x80200000
        assert struct.unpack('<I', g.read(SITE, 4))[0] == OLD
        g.write(SITE, struct.pack('<I', NEW))
        after = label()
        assert after == dict(before, x=3), after
        capture('after')
        report = dict(version='0.8.12', before=before, after=after,
                      moved_left=6, label_width=wrap.width(after['text']),
                      resource_label_x=27,
                      gap=27-after['x']-wrap.width(after['text']),
                      patched_site=hex(SITE), land_fixture=args.land_fixture)
        assert report['gap'] > 0
        (args.out / 'native.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
        print(json.dumps(report), flush=True)
        if saved_terrain:
            until(gdbdbg.DRAWSYNC)
            g.write(*saved_terrain)
            saved_terrain = None
        add(d.bp)
        d.press('cross')
        d.wait(8)
    finally:
        if saved_terrain:
            g.write(*saved_terrain)
        for at in active:
            g.cmd(f'z0,{at:x},4')
        d.close()


if __name__ == '__main__':
    main()
