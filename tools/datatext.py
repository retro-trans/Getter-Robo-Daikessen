"""Text inside data files of GR.VFS containers (not scripts, not code).

    python tools/datatext.py extract        -> work/translation/en/data.json

Sources (pac path, entry name, method):
  BRF   mapsys/briefing.pac  BRIEFING.BIN   chapter titles, briefings, choices (tools/briefing.py)
  HT    prog00/kt15v.pac     HT15V.BIN      battle lines; u32 pointers -> relocate by appending
  MCN   mapsys/mcn_prm.pac   MCN_PRM2.BIN   weapon (32-byte) / unit (24-byte) names, in place
  PIL   mapsys/mcn_prm.pac + mapsys/mapalway.pac  PIL_PRM.BIN  pilot names (20-byte), in place
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import briefing   # noqa: E402
import find_sjis  # noqa: E402
import pac        # noqa: E402
import refscan    # noqa: E402
import textcodec  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR = os.path.join(ROOT, 'work', 'translation', 'en')

SOURCES = [
    ('BRF', 'mapsys/briefing.pac', 'BRIEFING.BIN', 'briefing'),
    # HT15V.BIN (battle lines) is now handled with every other unit file by tools/battletext.py
    ('MCN', 'mapsys/mcn_prm.pac', 'MCN_PRM2.BIN', 'fixed'),
    ('PIL', 'mapsys/mcn_prm.pac', 'PIL_PRM.BIN', 'fixed'),
    ('PIL', 'mapsys/mapalway.pac', 'PIL_PRM.BIN', 'fixed'),
]


# files read into a fixed-size buffer (tools/loadlimits.py): briefing.bin 0x800BE020 reads
# MAPSYS/BRIEFING.PAC with max size 0x1E000 - a larger file overruns the heap (Episode 2 crash)
FIXED_BUFFER = {'mapsys/briefing.pac': 0x1E000}


def field_size(tag, off):
    if tag == 'PIL':
        return 20
    if tag == 'MCN':
        return 24 if off >= 0x3034 else 32
    return None


def real_strings(d):
    real = {o for o, m, c, t in find_sjis.scan(d, 1) if m == 'be'}
    return {o: s for o, s in refscan.strings(d) if any(o <= r < o + len(s) for r in real)}


def ptr_slots(d, S):
    inside = set()
    for o, s in S.items():
        inside.update(range(o, o + len(s) + 1))
    out = {}
    for i in range(0, len(d) - 3, 4):
        if i in inside:
            continue
        v = struct.unpack_from('<I', d, i)[0]
        if v in S:
            out.setdefault(v, []).append(i)
    return out


def extract():
    import vfs
    v = open(os.path.join(ROOT, 'work', 'source', 'disc', 'GR.VFS'), 'rb').read()
    rows = []
    seen = set()
    for tag, path, ent, method in SOURCES:
        pd = vfs_file(v, path)
        data = entry(pd, ent)
        S = briefing.strings(data) if method == 'briefing' else real_strings(data)
        for o in sorted(S):
            rid = '%s_%04X' % (tag, o)
            if rid in seen:
                continue
            seen.add(rid)
            r = {'id': rid, 'src': tag, 'offset': '%04X' % o, 'jp': S[o].decode('cp932'), 'en': ''}
            fs = field_size(tag, o)
            if fs:
                r['max_bytes'] = fs - 1
            rows.append(r)
    return rows


def vfs_file(v, path):
    import vfs
    t, ents = vfs.parse(v)
    for e in ents:
        if e['path'] == path:
            off = vfs.DATA_BASE + e['sector'] * 2048 + (e['flags'] & 7) * 0x100
            return v[off:off + e['size']]
    raise KeyError(path)


def entry(pd, name):
    for e in pac.parse_container(pd, 0):
        if e['name'] == name:
            return pac.decode_entry(pd, e)
    raise KeyError(name)


def rebuild_entry(tag, method, data, rows, wrapw=None):
    """Return the entry bytes with translations applied."""
    import wrap
    mine = {int(r['offset'], 16): r for r in rows if r['src'] == tag and r.get('en')}
    if method == 'briefing':
        new = {}
        for o, r in mine.items():
            # chapter titles are drawn on one line in the briefing header (~280 px, no \n)
            if r['en'].startswith('Episode ') or '\\n' in r['en']:
                en = r['en']
            else:
                en = wrap.wrap(r['en'], wrapw or wrap.WIDTH)
            new[o] = textcodec.encode(en)
        return briefing.rebuild(data, new)
    d = bytearray(data)
    S = real_strings(data)
    slots = ptr_slots(data, S) if method == 'pointers' else {}
    for o, r in mine.items():
        if o not in S:
            continue
        b = textcodec.encode(r['en'])
        old = S[o]
        if method == 'fixed':
            room = r['max_bytes'] + 1
        else:
            room = (len(old) + 4) & ~3
        if len(b) + 1 <= room:
            d[o:o + max(len(old) + 1, len(b) + 1)] = b.ljust(max(len(old) + 1, len(b) + 1), b'\0')
            continue
        if method == 'fixed':
            raise ValueError('%s_%04X longer than its field' % (tag, o))
        if not slots.get(o):
            raise ValueError('%s_%04X does not fit and has no pointer' % (tag, o))
        while len(d) % 4:
            d += b'\0'
        na = len(d)
        d += b + b'\0'
        for at in slots[o]:
            struct.pack_into('<I', d, at, na)
    while len(d) % 4:
        d += b'\0'
    return bytes(d)


def build_files(orig_vfs, files):
    """Add rebuilt pacs to files {vfs path: bytes} (repacks entries in place)."""
    p = os.path.join(TR, 'data.json')
    if not os.path.exists(p):
        return
    rows = json.load(open(p, encoding='utf-8'))
    by_pac = {}
    for tag, path, ent, method in SOURCES:
        by_pac.setdefault(path, []).append((tag, ent, method))
    for path, lst in by_pac.items():
        pd = files.get(path) or vfs_file(orig_vfs, path)
        items = pac.container_items(pd)
        changed = False
        for tag, ent, method in lst:
            data = entry(pd, ent)
            new = rebuild_entry(tag, method, data, rows)
            if new != data:
                items = [pac.pack_entry(it, new, best=path in FIXED_BUFFER) if it['name'] == ent else it for it in items]
                changed = True
        if changed:
            if path in FIXED_BUFFER:
                # read into a fixed-size buffer: re-pack every entry as small as possible
                ents = pac.parse_container(pd, 0)
                done = []
                for it, e in zip(items, ents):
                    if it['payload'] == pac.raw_payload(pd, e):
                        it = pac.pack_entry(it, pac.decode_entry(pd, e), best=True)
                    done.append(it)
                items = done
            files[path] = pac.build_container(items)
            if path in FIXED_BUFFER and len(files[path]) > FIXED_BUFFER[path]:
                raise ValueError('%s: %d bytes, the game reads it into a %d-byte buffer'
                                 % (path, len(files[path]), FIXED_BUFFER[path]))


if __name__ == '__main__':
    if sys.argv[1] == 'extract':
        p = os.path.join(TR, 'data.json')
        rows = extract()
        if os.path.exists(p):
            old = {r['id']: r for r in json.load(open(p, encoding='utf-8'))}
            for r in rows:
                if old.get(r['id'], {}).get('jp') == r['jp'] and old[r['id']].get('en'):
                    r['en'] = old[r['id']]['en']
            # rows of sources handled elsewhere (HT: tools/battletext.py reads them) stay
            mine = {s[0] for s in SOURCES}
            rows += [r for r in old.values() if r['src'] not in mine]
        json.dump(rows, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        import collections
        print(len(rows), 'rows', collections.Counter(r['src'] for r in rows))
