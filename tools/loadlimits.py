"""List file loads with a size limit and check the built files against them.

The game reads whole files with 0x8003A6FC(handle, mode, name, max size, ...). Where the
caller passes a constant max size (lui/ori/addiu into a3 just before the call) and a
constant file name (lui/addiu into a2), the buffer is fixed: a translated file must not
grow past it (BRIEFING.PAC overflowed its 0x1E000-byte buffer and crashed Episode 2).

    python tools/loadlimits.py
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build    # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOAD = 0x8003A6FC
IMAGES = [('exe', 'work/source/disc/SLPS_022.32', 0x80010000, 0x800),
          ('game', 'work/source/vfs/bin/game.bin', 0x8008B7A8, 0),
          ('title', 'work/source/vfs/bin/title.bin', 0x8008B7A8, 0),
          ('battle', 'work/source/vfs/bin/battle.bin', 0x800A97A8, 0),
          ('briefing', 'work/source/vfs/bin/briefing.bin', 0x800A97A8, 0),
          ('flight', 'work/source/vfs/bin/flight.bin', 0x800C67A8, 0)]


def calls(body, base):
    out = []
    n = len(body) // 4
    w = struct.unpack_from('<%dI' % n, body)
    target = 0x0C000000 | ((LOAD >> 2) & 0x3FFFFFF)
    for i in range(n):
        if w[i] != target:
            continue
        regs = {}
        for k in range(max(0, i - 14), i + 2):
            x = w[k]
            op, rs, rt, imm = x >> 26, (x >> 21) & 31, (x >> 16) & 31, x & 0xFFFF
            if op == 0x0F:
                regs[rt] = imm << 16
            elif op == 0x0D:
                regs[rt] = regs.get(rs, 0) | imm
            elif op == 0x09:
                regs[rt] = (regs.get(rs, 0) + (imm - 0x10000 if imm & 0x8000 else imm)) & 0xFFFFFFFF
        out.append((base + i * 4, regs.get(6), regs.get(7)))
    return out


def main():
    orig = open(os.path.join(ROOT, 'work', 'source', 'disc', 'GR.VFS'), 'rb').read()
    new = open(os.path.join(ROOT, 'work', 'build', 'GR.VFS'), 'rb').read()
    bad = 0
    for tag, path, base, hdr in IMAGES:
        img = open(os.path.join(ROOT, path), 'rb').read()
        body = img[hdr:]
        for at, a2, a3 in calls(body, base):
            if not a2 or not a3 or not (base <= a2 < base + len(body)):
                continue
            name = body[a2 - base:body.index(b'\0', a2 - base)].decode('ascii', 'replace')
            if not re.match(r'^[\w/.%]+$', name) or '%' in name:
                continue
            vpath = name.lower()
            try:
                o = len(build.vfs_file(orig, vpath))
                nn = len(build.vfs_file(new, vpath))
            except KeyError:
                continue
            flag = 'OVER' if nn > a3 else 'ok'
            bad += flag == 'OVER'
            print('%-8s %08X %-28s limit %6d  original %6d  built %6d  %s' % (tag, at, name, a3, o, nn, flag))
    # These loads go through a fixed heap allocation followed by the whole-file
    # reader, not LOAD(a3), so the instruction scan above cannot discover them.
    import battletext
    packs = battletext.unit_pack_sizes(orig, new)
    for path, old, size in packs:
        if size > battletext.UNIT_PACK_LIMIT:
            print('battle unit %-28s limit %6d  original %6d  built %6d  OVER' %
                  (path, battletext.UNIT_PACK_LIMIT, old, size))
            bad += 1
    largest = max(packs, key=lambda row: row[2])
    print('battle unit packs: %d checked, largest %s %d / %d bytes' %
          (len(packs), largest[0], largest[2], battletext.UNIT_PACK_LIMIT))
    print('%d file(s) over their load limit' % bad)
    return bad


if __name__ == '__main__':
    sys.exit(1 if main() else 0)
