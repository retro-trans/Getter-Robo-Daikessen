"""Check native Start skipping during an active map battle. Dry-run default.

May test an older running build with --patch-ram; this changes only the checked
instruction in the muted project emulator, never the image or a saved game.
"""
import argparse
import json
from pathlib import Path
import struct

import gdbdbg

GATE = 0x800AE00C
POLL = 0x800AE004
SKIP = 0x800AEA5C
SYNC_ACTORS = 0x800B167C


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--patch-ram', action='store_true')
    parser.add_argument('--confirm-target', action='store_true', help='send Circle while waiting for the battle to start')
    parser.add_argument('--delay-frames', type=int, default=0, help='let the animation run before pressing Start')
    parser.add_argument('--out', type=Path, default=Path('work/ui/battle_skip/v081-native'))
    args = parser.parse_args()
    print('Check active map battle: native Start -> fast-finish -> actor synchronization.', flush=True)
    if not args.apply:
        return
    args.out.mkdir(parents=True, exist_ok=True)
    d = gdbdbg.Dbg()
    g = d.g
    g.s.settimeout(35)
    active = {d.bp}
    report = {}

    def add(at):
        g.cmd(f'Z0,{at:x},4'); active.add(at)

    def remove(at):
        g.cmd(f'z0,{at:x},4'); active.discard(at)

    def until(at):
        add(at)
        while True:
            g.s.sendall(b'$c#63'); g._recv_packet()
            r = d.regs()
            if r[37] == at:
                remove(at)
                return r

    def u32(at):
        return struct.unpack('<I', g.read(at, 4))[0]

    def u16(at):
        return struct.unpack('<H', g.read(at, 2))[0]

    try:
        remove(d.bp)
        if args.confirm_target:
            add(POLL); add(d.bp)
            frames = 0
            while True:
                g.s.sendall(b'$c#63'); g._recv_packet(); r = d.regs()
                if r[37] == POLL:
                    remove(POLL); remove(d.bp)
                    break
                if r[37] == d.bp and r[5] == r[29]:
                    if frames % 40 < 3:
                        d.setreg(gdbdbg.PAD_REG, r[gdbdbg.PAD_REG] | gdbdbg.BTN['circle'])
                    frames += 1
                    if frames > 600:
                        raise ValueError('Target confirmation did not start a battle')
        else:
            r = until(POLL)
        scene, root = r[16], r[17]
        if args.delay_frames:
            add(d.bp); d.wait(args.delay_frames); remove(d.bp)
            r = until(POLL)
            scene, root = r[16], r[17]
        report.update(phase_before=u16(scene + 0x62c), map_parent=hex(u32(root + 0x7e8)))
        report['delay_frames'] = args.delay_frames
        if u32(root + 0x7e8) == 0xffffffff:
            raise ValueError('Expected a map battle, not standalone practice')
        word = u32(GATE)
        if args.patch_ram:
            if word != 0x1462000a:
                raise ValueError('Unexpected old native input gate')
            g.write(GATE, bytes(4))
        elif word != 0:
            raise ValueError('Active battle overlay does not have the skip patch')
        report['debug_patch_ram'] = args.patch_ram
        add(d.bp); add(SKIP)
        inputs = 0
        while True:
            g.s.sendall(b'$c#63'); g._recv_packet(); r = d.regs()
            if r[37] == SKIP:
                remove(SKIP); remove(d.bp)
                until(r[31])
                break
            if r[37] == d.bp and r[5] == r[29]:
                d.setreg(gdbdbg.PAD_REG, r[gdbdbg.PAD_REG] | gdbdbg.BTN['start'])
                inputs += 1
                if inputs > 30:
                    raise ValueError('Start did not reach the native skip routine')
        report['start_poll_calls'] = inputs
        report['phase_after_start'] = u16(scene + 0x62c)
        if report['phase_after_start'] != 17:
            raise ValueError('Native fast-finish phase was not entered')
        r = until(SYNC_ACTORS)
        actors = r[4]
        expected = []
        for i in range(u16(actors + 0x84)):
            actor = u32(actors + i * 4)
            if not actor:
                continue
            flags = u32(actor + 0x70)
            if not flags & 1:
                continue
            dest = u32(u32(actor + 0x10) + 8)
            a = g.read(actor + (0x40 if flags & 0x40000 else 0x20), 6)
            b = g.read(actor + (0x48 if flags & 0x80000 else 0x28), 6)
            expected.append((dest, a, b))
        until(r[31])
        for dest, a, b in expected:
            if g.read(dest + 0x10, 6) != a or g.read(dest + 0x18, 6) != b:
                raise ValueError('Native actor synchronization differs from its source values')
        report['actor_positions_verified'] = len(expected)
        report['actor_positions'] = [dict(destination=hex(dest), values_a=a.hex(), values_b=b.hex()) for dest, a, b in expected]
        report['actor_sync_returned'] = True
        add(d.bp); d.wait(90); remove(d.bp)
        for y, suffix in [(0, 'a'), (240, 'b')]:
            gdbdbg.write_png(str(args.out / f'after_{suffix}.png'), 320, 240, d.grab(0, y, 320, 240))
        (args.out / 'native.json').write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report), flush=True)
    finally:
        for at in active:
            g.cmd(f'z0,{at:x},4')
        d.close()


if __name__ == '__main__':
    main()
