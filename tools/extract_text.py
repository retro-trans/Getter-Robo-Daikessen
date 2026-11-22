"""Extract translatable text into work/translation/en/*.json (rows with jp + empty en).

    python tools/extract_text.py mform        map event scripts (mapef/mformNN.pac)

Row fields: id, file, offset (hex, in the unpacked BIN), kind, speaker (from %2..%0),
            gender ('m'/'f' for the two strings of a gendered pair, op 0x21), pair (id of the
            other half), jp, en.
Rows are in script order (order of first reference in the bytecode), so consecutive rows
read as the scene plays. Japanese stays in work/ (git-ignored); commit only the *.en.json
copies written by tools/strip_jp.py.
"""
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mform   # noqa: E402
import pac     # noqa: E402
import vfs     # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'work', 'translation', 'en')
SPEAKER = re.compile(r'%2(.*?)%0')


def vfs_files(pattern):
    data = open(os.path.join(ROOT, 'work', 'source', 'disc', 'GR.VFS'), 'rb').read()
    t, ents = vfs.parse(data)
    for e in ents:
        if not e['dir'] and re.match(pattern, e['path']):
            off = vfs.DATA_BASE + e['sector'] * 2048 + (e['flags'] & 7) * 0x100
            yield e['path'], data[off:off + e['size']]


def extract_mform():
    rows = []
    for path, pd in sorted(vfs_files(r'mapef/mform(\d+[ab]?|db)\.pac$'),
                           key=lambda x: (re.sub(r'\D', '', x[0]).zfill(3), x[0])):
        ent = pac.parse_container(pd, 0)[0]
        data = pac.decode_entry(pd, ent)
        m = mform.MForm(data)
        tag = ent['name'].replace('.BIN', '').replace('MFORM', 'MF')
        order = []
        gender = {}
        for p, op, n in m.ops:
            if op == 0x00:
                v = struct.unpack_from('<I', data, p + 4)[0]
                if v in m.strings and v not in order:
                    order.append(v)
            elif op == 0x21:
                a, b = struct.unpack_from('<II', data, p + 4)
                for v, g in ((a, 'm'), (b, 'f')):
                    if v in m.strings:
                        if v not in order:
                            order.append(v)
                        gender[v] = (g, b if g == 'm' else a)
        for v in order:
            jp = m.strings[v].decode('cp932')
            sp = SPEAKER.search(jp)
            row = {'id': '%s_%04X' % (tag, v), 'file': ent['name'], 'offset': '%04X' % v,
                   'kind': 'dialogue' if sp else 'narration',
                   'speaker': sp.group(1) if sp else '', 'jp': jp, 'en': ''}
            if v in gender:
                row['gender'] = gender[v][0]
                row['pair'] = '%s_%04X' % (tag, gender[v][1])
            rows.append(row)
    return rows


def merge(path, rows):
    """Keep existing English when re-extracting (matched by id and unchanged jp)."""
    if os.path.exists(path):
        old = {r['id']: r for r in json.load(open(path, encoding='utf-8'))}
        for r in rows:
            o = old.get(r['id'])
            if o and o.get('jp') == r['jp']:
                for k in ('en', 'note', 'status'):
                    if o.get(k):
                        r[k] = o[k]
    return rows


def main():
    what = sys.argv[1]
    os.makedirs(OUT, exist_ok=True)
    if what == 'mform':
        p = os.path.join(OUT, 'mform.json')
        rows = merge(p, extract_mform())
        json.dump(rows, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(len(rows), 'rows ->', p)


if __name__ == '__main__':
    main()


def extract_ui():
    """UI strings of the exe and the overlays with known load addresses."""
    import refscan
    rows = []
    srcs = [('exe', os.path.join(ROOT, 'work', 'source', 'disc', 'SLPS_022.32'), 0x80010000, 0x800),
            ('game', os.path.join(ROOT, 'work', 'source', 'vfs', 'bin', 'game.bin'), 0x8008B7A8, 0),
            ('title', os.path.join(ROOT, 'work', 'source', 'vfs', 'bin', 'title.bin'), 0x8008B7A8, 0),
            ('debug', os.path.join(ROOT, 'work', 'source', 'vfs', 'bin', 'debug.bin'), 0x8008B7A8, 0),
            ('battle', os.path.join(ROOT, 'work', 'source', 'vfs', 'bin', 'battle.bin'), 0x800A97A8, 0),
            ('briefing', os.path.join(ROOT, 'work', 'source', 'vfs', 'bin', 'briefing.bin'), 0x800A97A8, 0),
            ('flight', os.path.join(ROOT, 'work', 'source', 'vfs', 'bin', 'flight.bin'), 0x800C67A8, 0)]
    for mp in ('map04', 'map10', 'map16', 'map18'):
        srcs.append((mp, os.path.join(ROOT, 'work', 'source', 'vfs', 'bin', mp + '.bin'), 0x800F87A8, 0))
    for tag, path, base, hdr in srcs:
        img = open(path, 'rb').read()
        found = refscan.scan(img, base, hdr)
        body = img[hdr:]
        for a in FORMATS.get(tag, ()):       # Japanese split by format codes (第%ld話%s, 「%s」)
            off = a - base
            end = body.index(b'\0', off)
            room = end - off + 1
            while off + room < len(body) and body[off + room] == 0:
                room += 1
            found.append((a, body[off:end], [], [a], room))
        for a in SINGLE.get(tag, ()):        # one-character labels (the scan needs >= 2 chars)
            off = a - base
            room = 3
            while off + room < len(body) and body[off + room] == 0:
                room += 1
            found.append((a, body[off:off + 2], [], [a], room))
        found += referenced_strings(body, base, found)
        if tag == 'exe':
            import ui_slices
            present = {row[0] for row in found}
            for address, name in ui_slices.unit_name_fields(body, base):
                if name and address not in present:
                    found.append((address, name, [], [], 24))
        for a, s, ptrs, crefs, room in found:
            rows.append({'id': '%s_%08X' % (tag, a), 'file': tag, 'addr': '%08X' % a, 'room': room,
                         'refs': len(ptrs) + len(crefs), 'kind': 'ui', 'jp': s.decode('cp932'), 'en': ''})
    return rows


def referenced_strings(body, base, found):
    """Strings the text-run detector misses (kanji-heavy ones): every code / pointer
    target that holds a NUL-terminated Shift-JIS string with at least two double-byte
    characters and is not inside a string already found."""
    import re
    import struct
    import refscan
    pairs, _ = refscan.code_ref_pairs(body, base)
    tg = {a for a in pairs if base <= a < base + len(body)}
    for i in range(0, len(body) - 3, 4):
        v = struct.unpack_from('<I', body, i)[0]
        if base <= v < base + len(body):
            tg.add(v)
    have = [(a, a + len(s) + 1) for a, s, _, _, _ in found]
    pat = re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\xfc]|[\x20-\x7e\x0a])+\x00')
    out = []
    for a in sorted(tg):
        if any(lo <= a < hi for lo, hi in have):
            continue
        m = pat.match(body, a - base)
        if not m:
            continue
        s = m.group()[:-1]
        if len(re.findall(rb'[\x81-\x9f\xe0-\xef][\x40-\xfc]', s)) < 2:
            continue
        try:
            s.decode('cp932')
        except UnicodeDecodeError:
            continue
        off = a - base
        room = len(s) + 1
        while off + room < len(body) and body[off + room] == 0:
            room += 1
        out.append((a, s, [], [a], room))
        have.append((a, a + len(s) + 1))
    return out


# referenced format strings whose Japanese is split by format codes (found by a scan for
# referenced strings with SJIS + %/$ that no row covers)
FORMATS = {'exe': (0x80011F24,),                                     # 第%ld話%s
           'game': (0x8008C460, 0x8008D1F8),                         # 「%s」, %d～%d
           'battle': tuple(0x800AA4C4 + 0x10 * i for i in range(14)),  # $f%sa %s「%s」 (battle lines)
           'briefing': (0x800A99E0, 0x800AA0F0)}                     # 「%s」

# referenced one-character strings that are labels (not name-entry characters or noise)
SINGLE = {'title': (0x8008C0F8, 0x8008C0FC),                          # 男 女 (name entry)
          'game': (0x8008B7F5, 0x8008B7FA, 0x8008B7FF,                # 森 海 山 (terrain table)
                   0x8008C27C, 0x8008C280, 0x8008C284, 0x8008C288,    # 宇 海 陸 空
                   0x8008C354, 0x8008D164, 0x8008D1E8),               # 橋 円 形
          'briefing': (0x800ABC08,),                                    # 月 (location)
          'flight': (0x800E87B1, 0x800E87B4, 0x800E87B7, 0x800E87BA, 0x800E87BD,  # Ｄ-Ｓ ranks
                     0x800E87C9)}                                     # 森


if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'ui':
    p = os.path.join(OUT, 'ui.json')
    rows = merge(p, extract_ui())
    json.dump(rows, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(rows), 'rows ->', p)
