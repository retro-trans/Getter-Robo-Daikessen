"""PAC container reader (Getter Robo Daikessen).

A .pac/.dat file on GR.VFS holds one or more *containers*, often at 0x800-aligned
section offsets (e.g. mapsys/mapsub.pac: a 0x4000-byte raw block, then a container).

Container (little-endian):
  +0         u32 count
  +4         u32 off[count]           offset of entry i's payload, from container start
  payload-0x1C entry header (0x1C bytes):
     +0x00  char name[12]  encoded: 'A'-'Z' stored as c+0x60 (0xA1..0xBA), others as c+0x40
     +0x0C  u32  unpacked size
     +0x10  u32  packed size
     +0x14  u32  timestamp
     +0x18  u16  mode  (0 copy, 1/2/4 RLE, 3 LZ -> grlz.py)
     +0x1A  u16  prefix length / 8 (the legacy parser key is called 'type')
  payload: for mode 3 a 16-byte prefix (u32 psize+0x10 rounded, u32 3, u32 ?, u32 0),
           then the LZ stream (psize bytes) at payload+0x10.
  The loader's dispatch type is the low byte at prefix+8, read by 0x8003885C;
  it is separate from the entry header's prefix-length field.

Exe: entry getter 0x8003885C, iterator 0x8003897C, unpack 0x8003909C.

    python tools/pac.py scan <file>...          list containers and entries
    python tools/pac.py dump <file> <outdir>    unpack every entry
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import grlz  # noqa: E402


def dec_name(b):
    s = ''
    for c in b:
        if c == 0:
            break
        if 0xA1 <= c <= 0xBA:
            s += chr(c - 0x60)
        elif c >= 0x40:
            s += chr(c - 0x40)
        else:
            return None
    return s


def enc_name(s):
    out = bytearray()
    for ch in s:
        c = ord(ch)
        out.append(c + 0x60 if 'A' <= ch <= 'Z' else c + 0x40)
    return bytes(out).ljust(12, b'\0')


def parse_container(d, base):
    if base + 8 > len(d):
        return None
    cnt = struct.unpack_from('<I', d, base)[0]
    if not 1 <= cnt <= 4000 or base + 4 + 4 * cnt > len(d):
        return None
    offs = struct.unpack_from('<%dI' % cnt, d, base + 4)
    if offs[0] < 4 + 4 * cnt or offs[0] - 0x1C < 4 + 4 * cnt:
        return None
    ents = []
    prev = 0
    for i, o in enumerate(offs):
        if o <= prev or base + o > len(d):
            return None
        h = base + o - 0x1C
        name = dec_name(d[h:h + 12])
        if not name or '.' not in name:
            return None
        usize, psize, ts = struct.unpack_from('<III', d, h + 12)
        mode, typ = struct.unpack_from('<HH', d, h + 24)
        if mode > 4:
            return None
        ents.append({'index': i, 'name': name, 'hdr': h, 'data': base + o, 'usize': usize,
                     'psize': psize, 'time': ts, 'mode': mode, 'type': typ})
        prev = o
    return ents


def find_containers(d, step=4):
    found = []
    p = 0
    while p < len(d) - 8:
        ents = parse_container(d, p)
        if ents:
            end = max(e['data'] + e['psize'] for e in ents)
            found.append((p, ents, end))
            p = (end + 3) & ~3
            continue
        p += step
    return found


def decode_entry(d, e):
    raw = d[e['data']:e['data'] + e['psize'] + 0x12]
    if e['mode'] == 0:
        return raw[:e['usize']]
    if e['mode'] == 3:
        for skip in (0x10, 0):
            try:
                out, _ = grlz.lz_decompress(raw, skip)
                if len(out) == e['usize']:
                    return out
            except Exception:
                pass
        raise ValueError('LZ decode failed for ' + e['name'])
    if e['mode'] == 4:
        return grlz.rle4_decompress(raw)[0]
    return None


def main():
    cmd = sys.argv[1]
    if cmd == 'scan':
        for f in sys.argv[2:]:
            d = open(f, 'rb').read()
            for base, ents, end in find_containers(d):
                print('%s  container @%#x  %d entries  end %#x / size %#x' % (f, base, len(ents), end, len(d)))
                for e in ents:
                    print('   %3d %-12s mode %d type %2d  u%6x p%6x  @%#x' % (
                        e['index'], e['name'], e['mode'], e['type'], e['usize'], e['psize'], e['data']))
    elif cmd == 'dump':
        f, out = sys.argv[2], sys.argv[3]
        d = open(f, 'rb').read()
        os.makedirs(out, exist_ok=True)
        for base, ents, end in find_containers(d):
            for e in ents:
                data = decode_entry(d, e)
                if data is not None:
                    open(os.path.join(out, '%x_%02d_%s' % (base, e['index'], e['name'])), 'wb').write(data)


if __name__ == '__main__':
    main()


def raw_payload(d, e):
    """Stored payload bytes of an entry (prefix + packed data), up to the next header."""
    pre = 8 * struct.unpack_from('<H', d, e['hdr'] + 0x1A)[0]
    return d[e['data']:e['data'] + pre + e['psize']]


def build_container(items):
    """items: list of dicts {name, usize, psize, time, mode, prefsz (u16 at +0x1A), payload}.
    payload = prefix + packed data. Returns container bytes (layout as the originals)."""
    n = len(items)
    out = bytearray(4 + 4 * n)
    struct.pack_into('<I', out, 0, n)
    for i, it in enumerate(items):
        while len(out) % 4:
            out += b'\0'
        hdr = enc_name(it['name']) + struct.pack('<IIIHH', it['usize'], it['psize'], it['time'],
                                                  it['mode'], it['prefsz'])
        out += hdr
        struct.pack_into('<I', out, 4 + 4 * i, len(out))
        out += it['payload']
    return bytes(out)


def container_items(d, base=0):
    ents = parse_container(d, base)
    items = []
    for e in ents:
        prefsz = struct.unpack_from('<H', d, e['hdr'] + 0x1A)[0]
        items.append({'name': e['name'], 'usize': e['usize'], 'psize': e['psize'], 'time': e['time'],
                      'mode': e['mode'], 'prefsz': prefsz, 'payload': raw_payload(d, e)})
    return items


def pack_entry(item, data, best=False):
    """Re-pack new unpacked data into an item (mode 3 LZ, mode 0 copy); keeps prefix fields.
    best: optimal-parse LZ (smaller, slower; verified by decompressing)."""
    pre = bytearray(item['payload'][:8 * item['prefsz']])
    if item['mode'] == 3:
        packed = grlz.lz_compress_opt(data) if best else grlz.lz_compress(data)
        if best and grlz.lz_decompress(packed)[0][:len(data)] != data:
            raise ValueError('LZ round trip failed for ' + item['name'])
    elif item['mode'] == 0:
        packed = data
    else:
        raise ValueError('cannot pack mode %d' % item['mode'])
    if len(pre) >= 4:
        struct.pack_into('<I', pre, 0, (len(packed) + len(pre) + 3) & ~3)
    new = dict(item)
    new.update(usize=len(data), psize=len(packed), payload=bytes(pre) + packed)
    return new
