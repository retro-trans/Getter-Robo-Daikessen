"""GR.VFS archive reader / extractor.

Layout (all little-endian):
  0x000  'VFS0'  u16 total_entries  u16 root_count  u32 ? (8)
  0x800  directory table, 32-byte entries:
         +0  u32  file: sector (2048-byte units, from VFS start) | dir: byte offset of first child (from 0x800)
         +4  u32  file: size in bytes                            | dir: number of children
         +8  char name[23] (NUL padded)
         +31 u8   flags: 0x08 = directory; for files bits 0-2 = offset inside the sector in 0x100 units
         file byte offset = DATA_BASE (0x4000) + sector * 0x800 + (flags & 7) * 0x100

Usage: python tools/vfs.py list  [GR.VFS]
       python tools/vfs.py extract [GR.VFS] [outdir]
"""
import json
import os
import struct
import sys

DIR_BASE = 0x800
DATA_BASE = 0x4000      # sectors count from here (header + directory before it)
ENT = 32


def parse(data):
    assert data[:4] == b'VFS0'
    total, root_n = struct.unpack_from('<HH', data, 4)
    out = []

    def walk(off, n, path):
        for i in range(n):
            e = DIR_BASE + off + i * ENT
            a, b = struct.unpack_from('<II', data, e)
            name = data[e + 8:e + 31].split(b'\0')[0].decode('ascii')
            flags = data[e + 31]
            full = path + '/' + name if path else name
            if flags & 0x08:
                out.append({'path': full, 'dir': True, 'entry': e, 'child_off': a, 'count': b, 'flags': flags})
                walk(a, b, full)
            else:
                out.append({'path': full, 'dir': False, 'entry': e, 'sector': a, 'size': b, 'flags': flags})

    walk(0, root_n, '')
    return total, out


def main():
    cmd = sys.argv[1]
    src = sys.argv[2] if len(sys.argv) > 2 else 'work/source/disc/GR.VFS'
    data = open(src, 'rb').read()
    total, ents = parse(data)
    if cmd == 'list':
        print('total', total, 'parsed', len(ents))
        for e in ents:
            if e['dir']:
                print(f"{'DIR':>8} {e['count']:8d}      {e['path']}/")
            else:
                print(f"{e['sector']:8x} {e['size']:8x} f{e['flags']:02x}  {e['path']}")
    elif cmd == 'extract':
        out = sys.argv[3] if len(sys.argv) > 3 else 'work/source/vfs'
        # the size field is smaller than what the game reads for many .pac files (sections are
        # loaded by offset), so each file is extracted up to the next file's start ('span')
        files = sorted((e for e in ents if not e['dir']), key=lambda e: DATA_BASE + e['sector'] * 2048 + (e['flags'] & 7) * 0x100)
        for a, b in zip(files, files[1:] + [None]):
            ao = DATA_BASE + a['sector'] * 2048 + (a['flags'] & 7) * 0x100
            a['span'] = (DATA_BASE + b['sector'] * 2048 + (b['flags'] & 7) * 0x100 - ao) if b else len(data) - ao
        for e in ents:
            p = os.path.join(out, e['path'])
            if e['dir']:
                os.makedirs(p, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(p) or out, exist_ok=True)
            off = DATA_BASE + e['sector'] * 2048 + (e['flags'] & 7) * 0x100
            e['offset'] = off
            if off + e['size'] > len(data):
                e['missing'] = True
                continue
            with open(p, 'wb') as f:
                f.write(data[off:off + e['size']])
        with open(os.path.join(out, '_vfs.json'), 'w') as f:
            json.dump(ents, f, indent=1)
        print('extracted', sum(1 for e in ents if not e['dir'] and not e.get('missing')), 'files')


if __name__ == '__main__':
    main()


def build(orig, files):
    """Rebuild a VFS image. orig: original GR.VFS bytes; files: {path: bytes} replacing
    file contents (others are copied). Directory layout (entry order) is unchanged; data
    are re-laid out in the original order, 0x200-aligned. Returns new image bytes."""
    total, ents = parse(orig)
    out = bytearray(orig[:DATA_BASE])
    fl = [e for e in ents if not e['dir']]
    fl.sort(key=lambda e: DATA_BASE + e['sector'] * 2048 + (e['flags'] & 7) * 0x100)
    pos = DATA_BASE
    for e in fl:
        off = DATA_BASE + e['sector'] * 2048 + (e['flags'] & 7) * 0x100
        data = files.get(e['path'], orig[off:off + e['size']])
        assert pos % 0x200 == 0
        rel = pos - DATA_BASE
        sector, sub = divmod(rel, 0x800)
        struct.pack_into('<II', out, e['entry'], sector, len(data))
        out[e['entry'] + 31] = (orig[e['entry'] + 31] & ~7) | (sub // 0x100)
        out += data
        while len(out) % 0x200:
            out += b'\0'
        pos = len(out)
    return bytes(out)
