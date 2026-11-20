"""Insert translated UI strings (work/translation/en/ui.json) into the exe and overlays.

Strings are written in place when they fit their room (bytes up to the next non-zero byte;
for fixed record fields the per-row max_bytes). Referenced strings that do not fit are moved
to string pools in kernel RAM (copied there at boot by the VWF entry stub) and every
reference is patched: aligned u32 pointers and lui + addiu/ori/load pairs (refscan.py).
A lui shared by several references is only rewritten when its high half does not change.
Once a string has been moved, its old slot is free and later moved strings of the same
image are placed there first (overlay text stays in its overlay), then in the pools.

    python tools/ui_text.py      dry run: what goes in place / to the pools / fails
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refscan      # noqa: E402
import textcodec    # noqa: E402
import ui_slices    # noqa: E402
import wrap         # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISC = os.path.join(ROOT, 'work', 'source', 'disc')
BIN = os.path.join(ROOT, 'work', 'source', 'vfs', 'bin')
# kernel RAM free in every RAM dump (docs/VWF.md); 0x8000D000-0x8000DC20 = gdbdbg scratch,
# 0x8000F000.. = VWF code + tables
POOLS = [(0x8000C000, 0x8000D000), (0x8000E700, 0x8000EF00), (0x8000F600, 0x80010000)]
IMAGES = {   # tag: (path, base, header bytes)
    'exe': (os.path.join(DISC, 'SLPS_022.32'), 0x80010000, 0x800),
    'game': (os.path.join(BIN, 'game.bin'), 0x8008B7A8, 0),
    'title': (os.path.join(BIN, 'title.bin'), 0x8008B7A8, 0),
    'debug': (os.path.join(BIN, 'debug.bin'), 0x8008B7A8, 0),     # developer menu (not reachable on retail)
    'battle': (os.path.join(BIN, 'battle.bin'), 0x800A97A8, 0),
    'briefing': (os.path.join(BIN, 'briefing.bin'), 0x800A97A8, 0),
    'flight': (os.path.join(BIN, 'flight.bin'), 0x800C67A8, 0),
    'map04': (os.path.join(BIN, 'map04.bin'), 0x800F87A8, 0),
    'map10': (os.path.join(BIN, 'map10.bin'), 0x800F87A8, 0),
    'map16': (os.path.join(BIN, 'map16.bin'), 0x800F87A8, 0),
    'map18': (os.path.join(BIN, 'map18.bin'), 0x800F87A8, 0),
}


class Pool:
    def __init__(self):
        self.regions = [[lo, hi, bytearray()] for lo, hi in POOLS]

    def alloc(self, data):
        data = data + b'\0'
        for r in self.regions:
            if r[0] + len(r[2]) + len(data) <= r[1]:
                a = r[0] + len(r[2])
                r[2] += data
                while len(r[2]) % 4:
                    r[2] += b'\0'
                return a
        raise MemoryError('UI string pools full')

    def blobs(self):
        return [(lo, bytes(b)) for lo, hi, b in self.regions if b]


def encode_row(r):
    en = r['en']
    if ui_slices.kind(r) == 'dialogue':
        en = wrap.wrap(en)
    elif chr(10) in r['jp']:
        # plain strings drawn line by line: real newline bytes, not the message system's \n
        en = en.replace(chr(92) + 'n', chr(10))
    return textcodec.encode(en)


def apply(rows=None, dry=False, log=print):
    """Returns ({tag: patched image bytes (exe: whole file)}, pool blobs, problems)."""
    if rows is None:
        rows = json.load(open(os.path.join(ROOT, 'work', 'translation', 'en', 'ui.json'), encoding='utf-8'))
    pool = Pool()
    out = {}
    problems = []
    for tag, (path, base, hdr) in IMAGES.items():
        mine = [r for r in rows if r['file'] == tag and r.get('en') and r['id'] not in ui_slices.SKIP]
        if not mine:
            continue
        data = bytearray(open(path, 'rb').read())
        body = memoryview(data)[hdr:]
        pairs, uses = refscan.code_ref_pairs(bytes(body), base)
        ptrs = {}
        for i in range(0, len(body) - 3, 4):
            v = struct.unpack_from('<I', body, i)[0]
            if base <= v < base + len(body):
                ptrs.setdefault(v, []).append(i)
        stats = {'inplace': 0, 'pool': 0, 'reused': 0}
        free = []       # [addr, len]: old slots of strings moved out of this image

        def need(r):
            mb, _ = ui_slices.limits(r)
            return len(encode_row(r)) > (r['room'] - 1 if mb is None else mb)
        # in-place rows first, then the moved ones largest first so their old slots are reused
        mine.sort(key=lambda r: (need(r), -len(encode_row(r))))
        for r in mine:
            a = int(r['addr'], 16)
            off = a - base
            old = bytes(body[off:body.tobytes().index(b'\0', off)]) if False else None
            end = off
            while body[end] != 0:
                end += 1
            oldlen = end - off
            new = encode_row(r)
            if len(r['en']) > ui_slices.MAX_CHARS.get(r['id'], 1 << 30):
                problems.append('%s: %d characters, typed budget %d' % (r['id'], len(r['en']), ui_slices.MAX_CHARS[r['id']]))
            mb, _ = ui_slices.limits(r)
            room = r['room'] - 1 if mb is None else mb
            if len(new) <= room:
                body[off:off + max(oldlen, len(new)) + 1] = new.ljust(max(oldlen, len(new)) + 1, b'\0')
                stats['inplace'] += 1
                continue
            if mb is not None or (not ptrs.get(a) and not pairs.get(a)):
                problems.append('%s: %d bytes, room %d, not relocatable' % (r['id'], len(new), room))
                continue
            na = None
            for sp in free:
                if sp[1] >= len(new) + 1:
                    na = sp[0]
                    body[na - base:na - base + len(new) + 1] = new + b'\0'
                    sp[0] += len(new) + 1
                    sp[1] -= len(new) + 1
                    break
            local = na is not None
            if not local:
                na = pool.alloc(new)
            ok = True
            for lui, use in pairs.get(a, []):
                li = lui - base
                ui = use - base
                hi_new = ((na + 0x8000) >> 16) & 0xFFFF
                lw = struct.unpack_from('<I', body, li)[0]
                uw = struct.unpack_from('<I', body, ui)[0]
                if (lw & 0xFFFF) != hi_new and uses.get(lui, 0) > 1:
                    problems.append('%s: shared lui at %08X needs hi %04X' % (r['id'], lui, hi_new))
                    ok = False
                    continue
                struct.pack_into('<I', body, li, (lw & 0xFFFF0000) | hi_new)
                struct.pack_into('<I', body, ui, (uw & 0xFFFF0000) | (na & 0xFFFF))
            for p in ptrs.get(a, []):
                struct.pack_into('<I', body, p, na)
            if ok:
                stats['reused' if local else 'pool'] += 1
                free.append([a, r['room']])     # nothing points at the old slot any more
        log('%-8s in place %3d, old slots reused %3d, pool %3d' % (tag, stats['inplace'], stats['reused'], stats['pool']))
        out[tag] = bytes(data)
    for lo, b in pool.blobs():
        log('pool %08X: %d bytes' % (lo, len(b)))
    return out, pool.blobs(), problems


if __name__ == '__main__':
    o, blobs, probs = apply(dry=True)
    for p in probs:
        print('PROBLEM', p)
