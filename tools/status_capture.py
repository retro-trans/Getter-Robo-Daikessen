"""Preview the status layout in the muted project emulator; dry-run default.

Hot-patching is limited to a main-loop DrawSync stop, outside text/layout code.
The current build must be loaded freshly and the game overlay must be active.
"""
import argparse
import json
from pathlib import Path
import struct

import build
import gdbdbg
import status_layout as layout
import vwf


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--hotpatch', action='store_true')
    parser.add_argument('--open', action='store_true', help='select Status from the selected map unit')
    parser.add_argument('--check-controls', action='store_true', help='check page and weapon navigation, then return to map')
    parser.add_argument('--check-icons', action='store_true', help='record native form-icon draws on each page')
    parser.add_argument('--check-text', action='store_true', help='record actual text sizes and positions on each page')
    parser.add_argument('--fixture', choices=['lady-command', 'getter-1', 'getter-2'], help='debug-only data for layout checks')
    parser.add_argument('--out', type=Path, default=Path('work/ui/status/v082-preview'))
    args = parser.parse_args()
    print('Status preview: optional safe drawing-code reload; capture native 512x480 pages.', flush=True)
    if not args.apply:
        return
    args.out.mkdir(parents=True, exist_ok=True)
    d = gdbdbg.Dbg(); g = d.g; g.s.settimeout(40); active = {d.bp}

    def add(at): g.cmd(f'Z0,{at:x},4'); active.add(at)
    def remove(at): g.cmd(f'z0,{at:x},4'); active.discard(at)
    def until(at):
        add(at)
        while True:
            g.s.sendall(b'$c#63'); g._recv_packet(); r = d.regs()
            if r[37] == at:
                remove(at); return r

    def u32(at): return struct.unpack('<I', g.read(at, 4))[0]

    try:
        remove(d.bp)
        if args.hotpatch:
            r = until(gdbdbg.DRAWSYNC)
            if not r[32] & 5 or not 0x80010000 <= r[29] < 0x80200000:
                raise ValueError('Expected a main-loop DrawSync stop')
            stack = struct.unpack('<64I', g.read(r[29], 256))
            if any(vwf.CAVE <= p < 0x8000F600 or layout.START <= p < layout.END for p in (r[31], *stack)):
                raise ValueError('A text/layout return is still active; reload from the map')
            data = (layout.ROOT/'work/build/status_preview.bin').read_bytes()
            old = build.vfs_file((layout.ROOT/'work/build/GR.VFS').read_bytes(), 'bin/game.bin')
            if len(old) != len(data): raise ValueError('Overlay size changed')
            # Include all audited sites, so another preview can restore an edit
            # that has returned to the original value.
            g.write(layout.START, data[layout.START-layout.BASE:layout.END-layout.BASE])
            for addr, size in [(0x80097AB8, 4), (0x8009746C, 12), (0x80097A28, 8),
                               (0x80097B24, 4), (0x8008CE44, 4), (0x8008CDD0, 8),
                               (0x8008C470, 0x8C0)]:
                g.write(addr, data[addr-layout.BASE:addr-layout.BASE+size])
            cave, labels = vwf.build_cave()
            if vwf.CAVE + len(cave) > 0x8000F600: raise ValueError('Cave overlaps a UI string pool')
            g.write(vwf.CAVE, cave)
            secondary, _ = vwf.build_secondary_font(labels)
            g.write(vwf.SECONDARY_CAVE, secondary)
            for addr, word in vwf.exe_patches(labels).items(): g.write(addr, struct.pack('<I', word))
        add(d.bp)
        if args.open:
            d.press('circle'); d.wait(8)
            for _ in range(3): d.press('down')
            d.press('circle'); d.wait(120)  # allow the native asynchronous model load
        remove(d.bp)
        r = until(0x80097A8C)
        task = r[4]
        state = u32(task+0x30)
        if args.fixture:
            manager = u32(state+0x44)
            pilot_base = u32(manager)
            name_table = u32(u32(pilot_base+4))
            count = u32(name_table)
            if not 1 <= count <= 100: raise ValueError('Unexpected native pilot-name table')
            wanted = ['Michiru'] if args.fixture == 'lady-command' else (['Hayato', 'Musashi', 'Ryoma'] if args.fixture == 'getter-2' else ['Ryoma', 'Hayato', 'Musashi'])
            matches = {name: [] for name in wanted}
            for i in range(count):
                pointer = name_table + u32(name_table+4+i*4)
                name = g.read(pointer, 32).split(b'\0')[0]
                for wanted_name in wanted:
                    if wanted_name.encode() in name: matches[wanted_name].append(i)
            if any(len(ids) != 1 for ids in matches.values()):
                raise ValueError(f'Expected unique native pilot IDs, found {matches}')
            pilot_ids = [matches[name][0] for name in wanted]
            unit_id = 36 if args.fixture == 'lady-command' else (1 if args.fixture == 'getter-2' else 0)
            unit_index = struct.unpack('<h', g.read(state+0x34, 2))[0]
            map_state = u32(state+0x38)
            unit_manager = u32(map_state+0x54)
            unit_record = u32(unit_manager)+0x11C+unit_index*0x80
            for record in (unit_record, state+0x4C):
                g.write(record+0xA, struct.pack('<h', unit_id))
                g.write(record+0x10, struct.pack('<II6H', 829, 431, 197, 40, 134, 80, 55, 130))
                g.write(record+0x5C, struct.pack('<3h', *(pilot_ids+[-1]*3)[:3]))
            if args.fixture == 'lady-command':
                pilot = pilot_base+0x14C+pilot_ids[0]*28
                g.write(pilot+6, struct.pack('<hI', 1, 193))
                g.write(pilot+0x10, struct.pack('<5H', 29, 20, 52, 181, 55))
            original = d.regs()
            saved = g.read(gdbdbg.STUB, 16)
            stub = struct.pack('<3I', vwf.jal(0x80097BF4), 0, 0)
            g.write(gdbdbg.STUB, stub)
            d.setreg(4, task); d.setreg(5, 1); d.setreg(6, unit_id); d.setreg(7, 0)
            d.setreg(37, gdbdbg.STUB)
            until(gdbdbg.STUB+8)
            g.write(gdbdbg.STUB, saved)
            for i in [*range(1, 32), 33, 34, 37]: d.setreg(i, original[i])
        report = {'state': hex(state), 'task': hex(task), 'unit_id': struct.unpack('<h', g.read(state+0x4A, 2))[0], 'fixture': args.fixture, 'pages': []}
        # Finish the stopped callback before arming it again.
        until(0x80097B7C)
        for page, name in enumerate(('pilot', 'unit', 'weapons')):
            g.write(state+0xC, struct.pack('<I', page))
            add(d.bp); d.wait(12); remove(d.bp)
            mode = u32(0x80089AA4)
            if mode != 8: raise ValueError(f'Unexpected native video mode: {mode}')
            if args.check_icons:
                _, labels = layout.assemble()
                until(labels['status_draw'])
                add(labels['native_unit_icon']); add(0x80097AC0)
                icons = []
                while True:
                    g.s.sendall(b'$c#63'); g._recv_packet(); regs = d.regs()
                    if regs[37] == 0x80097AC0:break
                    if regs[37] == labels['native_unit_icon']:
                        icons.append(dict(x=regs[4], y=regs[5], unit=regs[6]))
                        remove(labels['native_unit_icon'])
                        until(regs[31])
                        add(labels['native_unit_icon'])
                remove(labels['native_unit_icon']); remove(0x80097AC0)
                if args.fixture in ('getter-1', 'getter-2'):
                    assert len(icons) == 4, icons
                elif args.fixture == 'lady-command':
                    assert len(icons) == 1, icons
                report.setdefault('icons', {})[name] = icons
            if args.check_text:
                _, labels = layout.assemble()
                until(labels['status_draw'])
                add(0x8004DDFC); add(0x80097AC0)
                calls = []
                while True:
                    g.s.sendall(b'$c#63'); g._recv_packet(); regs = d.regs()
                    if regs[37] == 0x80097AC0: break
                    if regs[37] == 0x8004DDFC:
                        pointer = regs[6]
                        if not 0x80000000 <= pointer < 0x80200000:
                            raise ValueError(f'Invalid text pointer: {pointer:#x}')
                        text = g.read(pointer, min(128, 0x80200000-pointer)).split(b'\0')[0].decode('cp932')
                        mode = regs[7] >> 24
                        calls.append(dict(text=text, x=regs[4], y=regs[5], flags=hex(regs[7]),
                                          cell={0x32:[16,20], 0x34:[11,13], 0x36:[14,17], 0x38:[19,24]}.get(mode)))
                        remove(0x8004DDFC)
                        if mode == 0x36:
                            ret = regs[31]
                            add(0x8004DA64); add(0x8004D7B4); add(ret)
                            glyphs = []; dimensions = []
                            while True:
                                g.s.sendall(b'$c#63'); g._recv_packet(); glyph = d.regs()
                                if glyph[37] == ret: break
                                if glyph[37] == 0x8004DA64:
                                    glyphs.append(dict(char=chr(glyph[6]), x=glyph[4], y=glyph[5]))
                                elif glyph[37] == 0x8004D7B4:
                                    dimensions.append([glyph[8], glyph[6] >> 16])
                            for at in (0x8004DA64, 0x8004D7B4, ret): remove(at)
                            assert dimensions and all(cell == [14,17] for cell in dimensions), dimensions
                            calls[-1].update(native_glyphs=glyphs, native_dimensions=dimensions)
                        else:
                            until(regs[31])
                        add(0x8004DDFC)
                remove(0x8004DDFC); remove(0x80097AC0)
                report.setdefault('text_calls', {})[name] = calls
            gdbdbg.write_png(str(args.out/f'{name}.png'), 512, 480, d.grab(0, 0, 512, 480))
            from PIL import Image
            Image.open(args.out/f'{name}.png').resize((640, 480), Image.Resampling.NEAREST).save(args.out/f'{name}_4x3.png')
            report['pages'].append(name)
        if args.check_controls:
            add(d.bp)
            d.press('left'); d.wait(8)
            left_page = u32(state+0xC)
            d.press('right'); d.wait(8)
            right_page = u32(state+0xC)
            if (left_page, right_page) != (1, 2):
                raise ValueError(f'Native page controls changed: {(left_page, right_page)}')
            g.write(state+0x12, b'\0\0')
            d.press('down'); d.wait(8)
            down_weapon = struct.unpack('<h', g.read(state+0x12, 2))[0]
            remove(d.bp)
            gdbdbg.write_png(str(args.out/'weapon_selected.png'), 512, 480, d.grab(0, 0, 512, 480))
            Image.open(args.out/'weapon_selected.png').resize((640, 480), Image.Resampling.NEAREST).save(args.out/'weapon_selected_4x3.png')
            add(d.bp)
            d.press('up'); d.wait(8)
            up_weapon = struct.unpack('<h', g.read(state+0x12, 2))[0]
            if down_weapon not in (0, 1) or up_weapon != 0:
                raise ValueError(f'Native weapon controls changed: {(down_weapon, up_weapon)}')
            d.press('cross'); d.wait(20)
            mode = u32(0x80089AA4)
            if mode == 8: raise ValueError('Status did not return to the map')
            report['controls'] = dict(left_page=left_page, right_page=right_page,
                                      down_weapon=down_weapon, up_weapon=up_weapon,
                                      return_video_mode=mode)
        (args.out/'native.json').write_text(json.dumps(report, indent=2)+'\n')
        summary = {k:v for k,v in report.items() if k != 'text_calls'}
        if args.check_text:
            summary['text_call_counts'] = {k:len(v) for k,v in report['text_calls'].items()}
        print(json.dumps(summary), flush=True)
    finally:
        for at in active: g.cmd(f'z0,{at:x},4')
        d.close()


if __name__ == '__main__': main()
