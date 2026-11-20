"""Find how strings in a code image are referenced.

    python tools/refscan.py exe            -> work/source/scan/refs_exe.tsv
    python tools/refscan.py <overlay> <base_hex>

For each Shift-JIS string (find_sjis rules) reports: data pointers (aligned u32 equal to
its address), code references (lui+addiu / lui+ori pairs within 8 instructions, any
register), and the room up to the next non-zero byte (in-place budget).
"""
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREFIX = re.compile(rb'^(?:\$[fmFM](?:\d\d|%02d)[a-z]|%0?2?l?d|\$[sp][0-9A-Fa-f]{2}|%[0-9cs]\d?|%%\d|\$n|\$/| |@\d\d|[\x81-\x9f\xe0-\xef][\x40-\xfc]|[0-9A-Za-z:/()!?.,\x27-]|\x5cn|\x0a)*$')
PAT = re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\xfc]|[\x20-\x7e])+\x00')


def strings(img, lo=0, hi=None):
    """NUL-terminated strings that contain a find_sjis text run (any confidence, >= 2 chars).
    Each run is extended back to the byte after the previous NUL, so ASCII control-code
    prefixes ($m01b%2...) belong to the string."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import find_sjis
    hi = hi or len(img)
    starts = {}
    for off, mode, conf, t in find_sjis.scan(img[lo:hi], 2):
        if mode != 'be':
            continue
        o = lo + off
        st = o
        while st > lo and img[st - 1] != 0 and o - st < 64:
            st -= 1
        if st > lo and img[st - 1] != 0:
            st = o              # long non-zero run before the text (pointer table): start at the text
        if st < o and not PREFIX.match(img[st:o]):
            st = o                        # bytes before the text are not a code prefix: binary data
        end = img.index(b'\x00', o)
        s = img[st:end]
        try:
            u = s.decode('cp932')
        except UnicodeDecodeError:
            continue
        if any(ord(c) < 0x20 and c != chr(10) for c in u):
            continue
        starts[st] = s
    items = sorted(starts.items())
    out = []
    end = -1
    for st, s in items:
        if st < end:
            continue            # inside the previous string (a text run after a %d etc.)
        out.append((st, s))
        end = st + len(s)
    return out


def code_refs(img, base):
    """{address: [instruction address]} for lui/addiu(ori) pairs."""
    n = len(img) // 4
    w = struct.unpack_from('<%dI' % n, img)
    refs = {}
    for i in range(n):
        x = w[i]
        if x >> 26 != 0x0F:          # lui
            continue
        rt = (x >> 16) & 31
        hi = x & 0xFFFF
        for k in range(1, 9):
            if i + k >= n:
                break
            y = w[i + k]
            op = y >> 26
            rs = (y >> 21) & 31
            if rs == rt and op in (0x09, 0x0D, 0x23, 0x24, 0x21, 0x25, 0x20):   # addiu ori lw lbu lh lhu lb
                lo = y & 0xFFFF
                a = (hi << 16) + (lo - 0x10000 if lo & 0x8000 and op != 0x0D else lo)
                refs.setdefault(a & 0xFFFFFFFF, []).append(base + 4 * (i + k))
            if ((y >> 16) & 31) == rt and op not in (0x2B, 0x29, 0x28) and k > 0 and op != 0:
                if op in (0x09, 0x0D) and rs != rt:
                    break
    return refs


def scan(img, base, hdr=0):
    body = img[hdr:]
    crefs = code_refs(body, base)
    ptrs = {}
    for i in range(0, len(body) - 3, 4):
        v = struct.unpack_from('<I', body, i)[0]
        if base <= v < base + len(body):
            ptrs.setdefault(v, []).append(base + i)
    rows = []
    for off, s in strings(body):
        a = base + off
        room = len(s) + 1
        while off + room < len(body) and body[off + room] == 0:
            room += 1
        rows.append((a, s, ptrs.get(a, []), crefs.get(a, []), room))
    return rows


def main():
    if sys.argv[1] == 'exe':
        img = open(os.path.join(ROOT, 'work', 'source', 'disc', 'SLPS_022.32'), 'rb').read()
        rows = scan(img, 0x80010000, 0x800)
        out = os.path.join(ROOT, 'work', 'source', 'scan', 'refs_exe.tsv')
    else:
        img = open(sys.argv[1], 'rb').read()
        rows = scan(img, int(sys.argv[2], 16))
        out = os.path.join(ROOT, 'work', 'source', 'scan', 'refs_%s.tsv' % os.path.basename(sys.argv[1]))
    with open(out, 'w', encoding='utf-8') as f:
        for a, s, p, c, room in rows:
            f.write('%08X\t%d\t%d\t%d\t%s\t%s\t%s\n' % (a, len(p), len(c), room, s.decode('cp932'),
                                                      ','.join('%X' % x for x in p[:4]), ','.join('%X' % x for x in c[:4])))
    print(len(rows), 'strings;', sum(1 for r in rows if r[2]), 'with data ptrs;',
          sum(1 for r in rows if r[3]), 'with code refs;', sum(1 for r in rows if not r[2] and not r[3]), 'unreferenced ->', out)


if __name__ == '__main__':
    main()


def code_ref_pairs(img, base):
    """({target: [(lui_addr, use_addr)]}, {lui_addr: number of uses}) for lui + addiu/ori/load
    pairs within 8 instructions using the lui register as base, before it is overwritten."""
    n = len(img) // 4
    w = struct.unpack_from('<%dI' % n, img)
    refs = {}
    uses = {}
    for i in range(n):
        x = w[i]
        if x >> 26 != 0x0F:
            continue
        rt = (x >> 16) & 31
        hi = x & 0xFFFF
        for k in range(1, 9):
            if i + k >= n:
                break
            y = w[i + k]
            op = y >> 26
            rs = (y >> 21) & 31
            if op in (0x09, 0x0D, 0x23, 0x24, 0x21, 0x25, 0x20, 0x2B, 0x29, 0x28) and rs == rt:
                lo = y & 0xFFFF
                a = (hi << 16) + (lo - 0x10000 if lo & 0x8000 and op != 0x0D else lo)
                refs.setdefault(a & 0xFFFFFFFF, []).append((base + 4 * i, base + 4 * (i + k)))
                uses[base + 4 * i] = uses.get(base + 4 * i, 0) + 1
                if op in (0x09, 0x0D, 0x23, 0x24, 0x21, 0x25, 0x20) and ((y >> 16) & 31) == rt:
                    break          # register overwritten by the use itself
                continue
            # any other instruction writing rt ends the window
            if op == 0 and ((y >> 11) & 31) == rt and y != 0:
                break
            if op in (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F, 0x20, 0x21, 0x23, 0x24, 0x25) and ((y >> 16) & 31) == rt:
                break
            if op in (0x02, 0x03) or (op == 0 and (y & 0x3F) in (0x08, 0x09)):
                # the delay slot still executes: check it, then stop
                if i + k + 1 < n:
                    z = w[i + k + 1]
                    if (z >> 26) in (0x09, 0x0D) and ((z >> 21) & 31) == rt:
                        lo = z & 0xFFFF
                        a = (hi << 16) + (lo - 0x10000 if lo & 0x8000 and (z >> 26) != 0x0D else lo)
                        refs.setdefault(a & 0xFFFFFFFF, []).append((base + 4 * i, base + 4 * (i + k + 1)))
                        uses[base + 4 * i] = uses.get(base + 4 * i, 0) + 1
                break
    return refs, uses
