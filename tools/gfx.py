"""Put edited graphics back into their PAC files at build time.

work/translation/en/gfx/<vfs pac path>/<unpacked entry file> (made by tools/gfx_cards.py, ...)
replaces that entry: the file name is the one tools/pac.py gives when unpacking,
<container offset>_<index>_<NAME>. The entry is re-packed with its original method.

Packed sizes are compared with the originals: a pac that grows is reported, because the
game loads pacs into fixed buffers (check docs/formats.md before shipping a larger one).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pac          # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GFX = os.path.join(ROOT, 'work', 'translation', 'en', 'gfx')


def edits():
    """{vfs pac path: [(container offset, entry name, data)]}"""
    out = {}
    for dp, dn, fn in os.walk(GFX):
        for f in fn:
            rel = os.path.relpath(dp, GFX).replace(os.sep, '/')
            off, idx, name = f.split('_', 2)
            out.setdefault(rel, []).append((int(off, 16), name, open(os.path.join(dp, f), 'rb').read()))
    return out


def build_files(orig_vfs, files, vfs_file, log=print):
    for path, lst in sorted(edits().items()):
        pd = files.get(path) or vfs_file(orig_vfs, path)
        offs = {o for o, _, _ in lst}
        if offs != {0}:
            raise ValueError('%s: only container offset 0 is supported' % path)
        items = pac.container_items(pd)
        names = {it['name'] for it in items}
        for _, name, data in lst:
            if name not in names:
                raise KeyError('%s: no entry %s' % (path, name))
            items = [pac.pack_entry(it, data) if it['name'] == name else it for it in items]
        new = pac.build_container(items)
        if len(new) > len(pd):
            log('gfx %s grew %d -> %d bytes' % (path, len(pd), len(new)))
        files[path] = new
    return files
