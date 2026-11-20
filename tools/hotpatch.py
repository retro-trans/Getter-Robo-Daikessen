"""Hot-patch text changes into the running game (debug aid, DuckStation via GDB).

    python tools/hotpatch.py <old GR.VFS> <old SLPS_022.32> [overlay tag]

Compares the previous build (the copies given) with work/build/ (the new build) and writes
only the differing bytes of the overlay currently loaded at its base (default: game) and the
kernel-RAM string pools / exe text. Runtime variables differ from the file anyway, so only
bytes that changed between the two builds are written.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vfs              # noqa: E402
from gdbmem import Gdb  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASES = {'game': 0x8008B7A8, 'title': 0x8008B7A8, 'battle': 0x800A97A8, 'briefing': 0x800A97A8,
         'flight': 0x800C67A8}


def vfs_file(data, path):
    for e in vfs.parse(data)[1]:
        if not e['dir'] and e['path'] == path:
            o = vfs.DATA_BASE + e['sector'] * 0x800 + (e['flags'] & 7) * 0x100
            return data[o:o + e['size']]
    raise KeyError(path)


def runs(a, b):
    i = 0
    n = min(len(a), len(b))
    while i < n:
        if a[i] != b[i]:
            j = i
            while j < n and (a[j] != b[j] or (j + 8 < n and a[j:j + 8] != b[j:j + 8])):
                j += 1
            yield i, b[i:j]
            i = j
        else:
            i += 1


def main():
    old_vfs, old_exe = open(sys.argv[1], 'rb').read(), open(sys.argv[2], 'rb').read()
    tag = sys.argv[3] if len(sys.argv) > 3 else 'game'
    bd = os.path.join(ROOT, 'work', 'build')
    new_vfs = open(os.path.join(bd, 'GR.VFS'), 'rb').read()
    new_exe = open(os.path.join(bd, 'SLPS_022.32'), 'rb').read()
    g = Gdb()
    n = 0
    try:
        a = vfs_file(old_vfs, 'bin/%s.bin' % tag)
        b = vfs_file(new_vfs, 'bin/%s.bin' % tag)
        for off, data in runs(a, b):
            g.write(BASES[tag] + off, data)
            n += len(data)
        # exe: changed bytes; kernel-RAM string pools: the stub copies them only at boot
        ea = struct.unpack_from('<I', new_exe, 0x18)[0]
        for off, data in runs(old_exe[0x800:], new_exe[0x800:]):
            g.write(ea + off, data)
            n += len(data)
        import ui_text
        _, blobs, _ = ui_text.apply(log=lambda *x: None)
        for lo, blob in blobs:
            g.write(lo, blob)
            n += len(blob)
    finally:
        g.close()
    print('wrote', n, 'bytes')


if __name__ == '__main__':
    main()
