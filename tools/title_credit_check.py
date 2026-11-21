"""Check a freshly booted local title build; mute the emulator first.

Dry run by default. Uses native game code/pad and temporarily extends the
attract-demo idle timer only in RAM while reading the framebuffer. Restores it.
"""
import argparse
import json
from pathlib import Path
import struct

from gdbdbg import Dbg, write_png
import title_credit


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--version', default='0.8.14')
    p.add_argument('--out', type=Path, default=Path('work/ui/title/v0814/native'))
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    print('Fresh boot: skip opening movie, verify title credits and menu, capture, then enter name setup.', flush=True)
    if not a.apply:
        return
    a.out.mkdir(parents=True, exist_ok=True)
    d = Dbg(); g = d.g; state = None; timer = None
    report = dict(version=a.version, fresh_boot=True, injected_code=False)
    u32 = lambda address: struct.unpack('<I', g.read(address, 4))[0]
    def trace(frames):
        calls = []; g.cmd('Z0,8004ddfc,4'); count = 0
        try:
            while count < frames:
                g.s.sendall(b'$c#63'); g._recv_packet(); r = d.regs()
                if r[37] == 0x8004DDFC:
                    calls.append(dict(x=r[4], y=r[5], flags=hex(r[7]), text=g.read(r[6], 96).split(b'\0')[0].decode('ascii', 'replace')))
                elif r[37] == d.bp and r[5] == r[29]: count += 1
        finally: g.cmd('z0,8004ddfc,4')
        return calls
    try:
        # Read the native task record after registration; pre-load code
        # breakpoints can be lost when the emulator recompiles a new overlay.
        signature = struct.pack('<5I', 0x8008C354, 0x8008C474,
                                0x8008C4E8, title_credit.START, 0x8008CEB0)
        for i in range(240):
            ram = g.read(0x80088000, 0x3000)
            at = -1
            while True:
                at = ram.find(signature, at+1)
                if at < 0: break
                candidate = 0x80088000+at-0x1C
                pointer = u32(candidate+0x30)
                if 0x80010000 <= pointer < 0x80200000:
                    task = candidate; state = pointer; break
            if state is not None: break
            d.wait(20)
        else: raise RuntimeError('Title callback not reached')
        assert u32(task+0x28) == title_credit.START
        code, _ = title_credit.assemble(a.version)
        assert g.read(title_credit.START, len(code)) == code
        report.update(task=hex(task), state=hex(state), wrapper_loaded_from_disc=True)
        print('Native title task and disc wrapper found', flush=True)
        for i in range(120):
            d.wait(10)
            if u32(state+0x34) == 5 and u32(state+4)&7 == 7: break
            if i%6 == 5 and u32(state+0x34) == 0: d.press('start')
        else: raise RuntimeError('Title menu did not become ready')
        print('Title menu ready', flush=True)
        # The slow VRAM read must not trigger the native 900-frame attract demo.
        timer = g.read(state+0x1C, 4); g.write(state+0x1C, struct.pack('<i', -100000))
        calls = trace(3)
        expected = title_credit.layout(a.version)
        for row in expected:
            assert any(c['text']==row['text'] and c['x']==row['x'] and c['y']==row['y'] and c['flags']==hex(title_credit.FLAGS) for c in calls), row
        report['title_calls'] = calls
        before = u32(state+0x18); d.press('down'); d.wait(8); down = u32(state+0x18)
        d.press('up'); d.wait(8); up = u32(state+0x18)
        assert before == up and down != before, (before,down,up)
        report['menu_navigation'] = dict(before=before, down=down, up=up, passed=True)
        write_png(str(a.out/'title.png'), 512, 480, d.grab(0,0,512,480))
        from PIL import Image
        Image.open(a.out/'title.png').resize((960,720), Image.Resampling.NEAREST).save(a.out/'title-4x3.png')
        g.write(state+0x1C, timer); assert g.read(state+0x1C,4)==timer; timer=None
        report['temporary_idle_timer_restored'] = True
        d.press('circle'); d.wait(180)
        after = trace(3)
        assert not any(c['text'] in [r['text'] for r in expected] for c in after), after
        report['credits_absent_after_start'] = True
        report['after_start_calls'] = after
        report['all_checks_passed'] = True
        print('PASS: native credits, title navigation, start transition, and restored timer.', flush=True)
    finally:
        if timer is not None and state is not None: g.write(state+0x1C,timer)
        for bp in (0x8008CD20, 0x8004DDFC): g.cmd('z0,%x,4'%bp)
        d.close()
        (a.out/'checks.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__ == '__main__':
    main()
