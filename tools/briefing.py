"""BRIEFING.BIN (mapsys/briefing.pac): chapter titles, briefings, branch choices.

Strings are b'\0'-terminated Shift-JIS referenced by absolute u32 offsets inside a command
structure that is not fully decoded. A u32 equal to a string offset is treated as a string
pointer only in the contexts verified on the original file:
  P1  previous word == 1                (text command: 1, ptr, 8 ...)
  P2  next word == 2, previous word is not a small number (chapter title block: ptr, 2)
  P3  previous word in (2, 3) and the word before it is 0x00060000 (choice list)
Other matches (e.g. 0x00000C00, ptr, 0x0000FD80: coordinates) are left alone.
Translations that fit are written in place; longer ones are appended to the file and only
their P1-P3 pointers are rewritten.
"""
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import refscan   # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def strings(d):
    """refscan strings plus targets of chapter-title / choice slots (ptr, 2) that the text
    scanner misses (a title right after a pointer word, e.g. Episodes 1/4/9/11/19/21 and
    the destination-choice prompt)."""
    S = dict(refscan.strings(d))
    for i in range(4, len(d) - 7, 4):
        v = struct.unpack_from('<I', d, i)[0]
        if v in S or not 4 <= v < len(d) - 2 or d[v - 1] != 0:
            continue
        if struct.unpack_from('<I', d, i + 4)[0] != 2:
            continue
        if not (0x81 <= d[v] <= 0x9F or 0xE0 <= d[v] <= 0xEF):
            continue
        s = d[v:d.index(b'\0', v)]
        try:
            u = s.decode('cp932')
        except UnicodeDecodeError:
            continue
        if len(u) >= 2 and all(ord(c) >= 0x20 for c in u):
            S[v] = bytes(s)
    return S


def pointer_slots(d, S):
    out = {}
    for i in range(4, len(d) - 7, 4):
        v = struct.unpack_from('<I', d, i)[0]
        if v not in S:
            continue
        prev = struct.unpack_from('<I', d, i - 4)[0]
        nxt = struct.unpack_from('<I', d, i + 4)[0]
        pp = struct.unpack_from('<I', d, i - 8)[0] if i >= 8 else 0
        if prev == 1 or (nxt == 2 and (prev > 0x10 or prev == 0)) or (prev in (2, 3) and pp == 0x00060000):
            out.setdefault(v, []).append(i)
    return out


def other_refs(d, o, known):
    """Aligned u32 equal to o that are not recognised pointer slots and not the
    coordinate pattern (0x00000C00, value, 0x0000FD80)."""
    out = []
    for i in range(0, len(d) - 3, 4):
        if struct.unpack_from('<I', d, i)[0] != o or i in known:
            continue
        prev = struct.unpack_from('<I', d, i - 4)[0] if i >= 4 else 0
        nxt = struct.unpack_from('<I', d, i + 4)[0] if i + 8 <= len(d) else 0
        if prev == 0xC00 and nxt == 0xFD80:
            continue
        out.append(i)
    return out


def rebuild(d, new):
    """new: {string offset: bytes}. Returns patched bytes.

    The file is read into a fixed 0x1E000-byte buffer together with the rest of
    mapsys/briefing.pac (briefing.bin 0x800BE020), so it must stay small: strings that
    fit stay in place; longer ones go into the slots freed by other moved strings (their
    Japanese is zeroed, which also packs better) and only the rest is appended. A slot
    that some unrecognised value still points at is kept as it was."""
    d = bytearray(d)
    orig = bytes(d)
    S = strings(orig)
    slots = pointer_slots(orig, S)
    free = []
    pending = []
    for o, b in new.items():
        old = S[o]
        room = len(old) + 1
        while o + room < len(d) and d[o + room] == 0:
            room += 1
        room = min(room, (len(old) + 4) & ~3)          # stay inside the 4-byte padding
        if len(b) + 1 <= room:
            d[o:o + room] = b.ljust(room, b'\0')
            if room - len(b) - 1 >= 8:
                free.append([o + len(b) + 1, room - len(b) - 1])
            continue
        if not slots.get(o):
            raise ValueError('briefing string %#x does not fit and has no known pointer' % o)
        pending.append((o, b, room))
    for o, b, room in pending:
        if not other_refs(orig, o, set(slots[o])):
            d[o:o + room] = bytes(room)
            free.append([o, room])
    placed = {}         # identical strings (duplicated branch briefings) share one copy
    for o, b, room in sorted(pending, key=lambda x: -len(x[1])):
        need = len(b) + 1
        fits = [f for f in free if f[1] >= need]
        if b in placed:
            na = placed[b]
        elif fits:
            f = min(fits, key=lambda f: f[1])
            na = f[0]
            d[na:na + need] = b + b'\0'
            f[0] += need
            f[1] -= need
        else:
            while len(d) % 4:
                d += b'\0'
            na = len(d)
            d += b + b'\0'
        placed[b] = na
        for at in slots[o]:
            struct.pack_into('<I', d, at, na)
    while len(d) % 4:
        d += b'\0'
    return bytes(d)


if __name__ == '__main__':
    p = os.path.join(ROOT, 'work', 'source', 'unpacked', 'mapsys', 'briefing.pac', '00000_038_BRIEFING.BIN')
    d = open(p, 'rb').read()
    S = strings(d)
    sl = pointer_slots(d, S)
    print(len(S), 'strings,', len(sl), 'with recognised pointers')
    import collections
    allrefs = collections.Counter()
    for i in range(0, len(d) - 3, 4):
        v = struct.unpack_from('<I', d, i)[0]
        if v in S:
            allrefs[v] += 1
    for o in sorted(S):
        if o not in sl:
            print('  no pointer: %#x refs=%d %s' % (o, allrefs[o], S[o][:30].decode('cp932', 'replace').encode('unicode_escape')[:70]))
