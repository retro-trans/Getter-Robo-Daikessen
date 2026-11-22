"""Battle dialogue: the <UNIT>.BIN text table of every battle-animation pack in prog00/.

Each prog00/<unit>.pac holds the unit's battle animation; its TMV.PAC (stored or LZ-packed,
itself a PAC) contains <UNIT>.BIN (LZ) with the attack shouts and pilot lines used in that
unit's battles (kt15v.pac keeps HT15V.BIN at the top level instead). The same line occurs in
many files, so the table is translated once per unique Japanese line:

    python tools/battletext.py extract     -> work/translation/en/battle.json (keeps en by jp)
    python tools/battletext.py slices      -> slices/battle_NN.json + out/battle_NN.json
    python tools/battletext.py check <out>  checker for an out file
    python tools/battletext.py apply       out/battle_*.json -> battle.json
    python tools/battletext.py dry         what the build would do (fit in place / append)

Strings are NUL-terminated Shift-JIS, referenced by u32 offsets (datatext.ptr_slots). A
translation that does not fit its 4-byte-aligned slot is appended to the BIN and its
pointers rewritten (as HT15V in 0.1.0). Lines are word-wrapped by the build (WRAP_W) when a
width is set; the battle window was not measured yet (None = no wrap).
"""
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import datatext     # noqa: E402
import pac          # noqa: E402
import textcodec    # noqa: E402
import vfs          # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR = os.path.join(ROOT, 'work', 'translation', 'en')
DISC = os.path.join(ROOT, 'work', 'source', 'disc')
WRAP_W = 210      # battle lines go through the message window ($f%sa %s: %s, battle.bin 0x800AA4C4)
NAME_PX = None    # width of the widest "<pilot>: " prefix (computed from the label rows)
SLICE = 80
# battle.bin 0x800ACB40..0x800ACB7C allocates 0x15000 bytes before
# reading a unit PAC through 0x8002E90C. That reader uses the complete file
# size, not the allocation size. EFFECT.PAC has a separate, larger load.
UNIT_PACK_LIMIT = 0x15000
# in-place short forms for lines without a pointer (not relocatable) that do not fit
SHORT = {'超ウエポン砲発射！': 'Super Wpn Cannon!'}


def vfs_file(v, path):
    return datatext.vfs_file(v, path)


def entry_by_name(d, name, base=0):
    for e in pac.parse_container(d, base) or []:
        if e['name'] == name:
            return e
    raise KeyError(name)


def units(v):
    """[(pac path, tmv item name or None, bin name, bin bytes)]"""
    out = []
    paths = sorted(e['path'] for e in vfs.parse(v)[1] if not e['dir'] and e['path'].startswith('prog00/'))
    for p in paths:
        pd = vfs_file(v, p)
        ents = pac.parse_container(pd, 0) or []
        for e in ents:
            n = e['name'].upper()
            if n == 'TMV.PAC':
                t = tmv_bytes(pd, e)
                for e2 in pac.parse_container(t, 0) or []:
                    if e2['name'].upper().endswith('.BIN'):
                        out.append((p, e['name'], e2['name'], pac.decode_entry(t, e2)))
            elif n.endswith('.BIN'):
                out.append((p, None, e['name'], pac.decode_entry(pd, e)))
    return out


def tmv_bytes(pd, e):
    if e['mode'] == 0:
        it = [i for i in pac.container_items(pd) if i['name'] == e['name']][0]
        return it['payload'][8 * it['prefsz']:8 * it['prefsz'] + it['psize']]
    return pac.decode_entry(pd, e)


def raw_strings(b):
    """Every text string of a battle BIN: real_strings, plus pointer targets holding a
    NUL-terminated Shift-JIS string that the text-run detector rejects (kanji-heavy attack
    names, record name fields such as 爬虫兵Ａ, full-width Latin), plus one-character labels
    (pilot names such as 茜) that a pointer refers to."""
    import re
    S = dict(datatext.real_strings(b))
    pat = re.compile(rb'(?:[\x81-\x9f\xe0-\xef][\x40-\xfc]|[\x20-\x7e])+\x00')
    dbl = re.compile(rb'[\x81-\x9f\xe0-\xef][\x40-\xfc]')
    inside = set()
    for o, t in S.items():
        inside.update(range(o, o + len(t) + 1))
    cand = {}
    for i in range(0, len(b) - 3, 4):
        if i in inside:
            continue
        v = struct.unpack_from('<I', b, i)[0]
        if 0 < v < len(b) and v % 4 == 0 and v not in S and v not in cand:
            m = pat.match(b, v)
            n2 = len(dbl.findall(m.group())) if m else 0
            if m and (n2 >= 2 or (n2 == 1 and len(m.group()) == 3)):
                t = m.group()[:-1]
                try:
                    t.decode('cp932')
                except UnicodeDecodeError:
                    continue
                if len(t) >= 2:
                    cand[v] = t
    for o in sorted(cand):
        if not any(so <= o < so + len(t) + 1 for so, t in S.items()):
            S[o] = cand[o]
    return S


def strings(b):
    return {o: s.decode('cp932') for o, s in raw_strings(b).items()}


def load():
    p = os.path.join(TR, 'battle.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else []


def save(rows):
    json.dump(rows, open(os.path.join(TR, 'battle.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def extract():
    v = open(os.path.join(DISC, 'GR.VFS'), 'rb').read()
    old = {r['jp']: r for r in load()}
    ht = {r['jp']: r['en'] for r in json.load(open(os.path.join(TR, 'data.json'), encoding='utf-8'))
          if r['src'] == 'HT' and r.get('en')}
    rows = {}
    for p, tmv, name, b in units(v):
        S = strings(b)
        offs = sorted(S)
        for i, o in enumerate(offs):
            jp = S[o]
            r = rows.get(jp)
            if r is None:
                r = rows[jp] = {'id': 'BT_%03d' % len(rows), 'jp': jp,
                                'en': (old.get(jp) or {}).get('en') or ht.get(jp, ''),
                                'units': [], 'prev': S[offs[i - 1]] if i else '',
                                'next': S[offs[i + 1]] if i + 1 < len(offs) else ''}
            u = name.rsplit('.', 1)[0]
            if u not in r['units']:
                r['units'].append(u)
    save(list(rows.values()))
    print(len(rows), 'unique lines,', sum(1 for r in rows.values() if r['en']), 'already translated')


def slices():
    rows = load()
    os.makedirs(os.path.join(TR, 'slices'), exist_ok=True)
    k = 0
    for i in range(0, len(rows), SLICE):
        part = rows[i:i + SLICE]
        json.dump([{'id': r['id'], 'units': r['units'][:6], 'prev': r['prev'], 'next': r['next'], 'jp': r['jp'],
                    'en': ''} for r in part],
                  open(os.path.join(TR, 'slices', 'battle_%02d.json' % k), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        json.dump([{'id': r['id'], 'en': r['en'], 'note': ''} for r in part],
                  open(os.path.join(TR, 'out', 'battle_%02d.json' % k), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        k += 1
    print(k, 'slices')


def check(path):
    out = json.load(open(path, encoding='utf-8'))
    src = {x['id']: x for x in json.load(open(os.path.join(TR, 'slices', os.path.basename(path)), encoding='utf-8'))}
    errs = []
    if [x['id'] for x in out] != list(src):
        errs.append('ids differ from the input slice')
    for x in out:
        en = x.get('en', '')
        if not en:
            errs.append('%s: empty' % x['id'])
        elif any(not (0x20 <= ord(c) < 0x7F) for c in en):
            errs.append('%s: non-ASCII' % x['id'])
        elif '\\n' in en:
            errs.append('%s: no \\n (the build wraps)' % x['id'])
    for e in errs:
        print(e)
    print('%d rows, %d problems' % (len(out), len(errs)))
    return not errs


def apply():
    rows = load()
    by = {r['id']: r for r in rows}
    n = 0
    od = os.path.join(TR, 'out')
    for f in sorted(os.listdir(od)):
        if f.startswith('battle_'):
            for x in json.load(open(os.path.join(od, f), encoding='utf-8')):
                if x.get('en') and x['id'] in by:
                    by[x['id']]['en'] = x['en']
                    n += 1
    save(rows)
    print('applied', n)


def wrap_line(en):
    """Word-wrap a battle line for the message window; the first line shares its row with
    the pilot's name ("Ryoma: ..."), so it is wrapped as if prefixed by the widest name."""
    import wrap
    global NAME_PX
    if NAME_PX is None:
        names = [r['en'] for r in load() if len(r['jp']) <= 6 and r.get('en') and ' ' not in r['en'][:0]
                 and not r['jp'].endswith(('！', '…', '。', '？', 'ッ', '!'))]
        NAME_PX = max(wrap.width(n + ': ') for n in names if len(n) <= 20)
    pre = 'M' * 40
    while wrap.width(pre) > NAME_PX and len(pre) > 1:
        pre = pre[:-1]
    s = wrap.wrap(pre + en, WRAP_W)
    assert s.startswith(pre)
    return s[len(pre):]


def rebuild_bin(b, tr, stats):
    """tr: {jp: en}. Returns new BIN bytes.

    Every string keeps its slot when the English fits. Longer ones are placed in free space
    inside the file first: the unused tail of shortened slots and the whole slot of strings
    that moved. Only what still does not fit is appended (the file grows)."""
    import wrap
    d = bytearray(b)
    S = raw_strings(b)
    slots = datatext.ptr_slots(b, S)

    def room_of(o, old):
        r = len(old) + 1
        while r < ((len(old) + 4) & ~3) and o + r < len(b) and b[o + r] == 0:
            r += 1
        return r
    free = []           # [start, size]
    pending = []
    for o, old in sorted(S.items()):
        jp = old.decode('cp932')
        en = tr.get(jp)
        room = room_of(o, old)
        if not en:
            continue
        if WRAP_W:
            en = wrap_line(en)
        nb = textcodec.encode(en)
        if len(nb) + 1 <= room:
            d[o:o + room] = nb.ljust(room, b'\0')
            stats['inplace'] += 1
            if room - len(nb) - 1 > 0:
                free.append([o + len(nb) + 1, room - len(nb) - 1])
            continue
        if not slots.get(o):
            # no pointer refers to it (unused / orphan string): use the short form if one
            # is given, otherwise leave the Japanese and report it
            short = SHORT.get(jp)
            if short and len(short) + 1 <= room:
                d[o:o + room] = textcodec.encode(short).ljust(room, b'\0')
                stats['inplace'] += 1
            else:
                stats.setdefault('unplaced', set()).add(jp)
            continue
        pending.append((o, nb, room))
    for o, nb, room in pending:
        d[o:o + room] = bytes(room)
        free.append([o, room])
    for o, nb, room in sorted(pending, key=lambda x: -len(x[1])):
        need = len(nb) + 1
        fits = [f for f in free if f[1] >= need]
        if fits:
            f = min(fits, key=lambda f: f[1])
            na = f[0]
            d[na:na + need] = nb + b'\0'
            f[0] += need
            f[1] -= need
            stats['packed'] = stats.get('packed', 0) + 1
        else:
            while len(d) % 4:
                d += b'\0'
            na = len(d)
            d += nb + b'\0'
            stats['moved'] += 1
        for at in slots[o]:
            struct.pack_into('<I', d, at, na)
    while len(d) % 4:
        d += b'\0'
    return bytes(d)


def fit_unit_pack(data, path, log=print):
    """Keep translated unit packs inside the native allocation without text edits.

    Only oversized packs are recompressed. Preserve all decoded contents and
    untouched graphics/audio payloads; never enlarge the game's heap allocation.
    """
    if len(data) <= UNIT_PACK_LIMIT:
        return data
    items = pac.container_items(data)
    for index, e in enumerate(pac.parse_container(data, 0)):
        if e['name'].upper() == 'TMV.PAC':
            tmv = tmv_bytes(data, e)
            nested = pac.container_items(tmv)
            for j, child in enumerate(pac.parse_container(tmv, 0)):
                if child['name'].upper().endswith('.BIN') and child['mode'] == 3:
                    nested[j] = pac.pack_entry(nested[j], pac.decode_entry(tmv, child), best=True)
            items[index] = pac.pack_entry(items[index], pac.build_container(nested), best=True)
        elif e['name'].upper().endswith('.BIN') and e['mode'] == 3:
            items[index] = pac.pack_entry(items[index], pac.decode_entry(data, e), best=True)
    packed = pac.build_container(items)
    if len(packed) > UNIT_PACK_LIMIT:
        raise ValueError('%s: %d bytes after optimal packing; native unit buffer is %d bytes'
                         % (path, len(packed), UNIT_PACK_LIMIT))
    log('battle pack: %s %d -> %d bytes (native limit %d)' %
        (path, len(data), len(packed), UNIT_PACK_LIMIT))
    return packed


def unit_pack_sizes(original, current):
    """Audit actual battle unit packs; shared effects do not use this buffer."""
    paths = sorted({p for p, _, _, _ in units(original)})
    return [(p, len(vfs_file(original, p)), len(vfs_file(current, p))) for p in paths]


def build_files(orig_vfs, files, log=print):
    tr = {r['jp']: r['en'] for r in load() if r.get('en')}
    if not tr:
        return files
    stats = {'inplace': 0, 'moved': 0, 'grown': 0}
    paths = sorted(e['path'] for e in vfs.parse(orig_vfs)[1] if not e['dir'] and e['path'].startswith('prog00/'))
    for p in paths:
        pd = files.get(p) or vfs_file(orig_vfs, p)
        ents = pac.parse_container(pd, 0) or []
        items = pac.container_items(pd)
        changed = False
        for e in ents:
            n = e['name'].upper()
            if n == 'TMV.PAC':
                t = tmv_bytes(pd, e)
                titems = pac.container_items(t)
                tch = False
                for e2 in pac.parse_container(t, 0) or []:
                    if e2['name'].upper().endswith('.BIN'):
                        b = pac.decode_entry(t, e2)
                        nb = rebuild_bin(b, tr, stats)
                        if nb != b:
                            stats['grown'] += len(nb) > len(b)
                            titems = [pac.pack_entry(it, nb) if it['name'] == e2['name'] else it for it in titems]
                            tch = True
                if tch:
                    nt = pac.build_container(titems)
                    items = [pac.pack_entry(it, nt) if it['name'] == e['name'] else it for it in items]
                    changed = True
            elif n.endswith('.BIN'):
                b = pac.decode_entry(pd, e)
                if not raw_strings(b):
                    continue
                nb = rebuild_bin(b, tr, stats)
                if nb != b:
                    stats['grown'] += len(nb) > len(b)
                    items = [pac.pack_entry(it, nb) if it['name'] == e['name'] else it for it in items]
                    changed = True
        if changed:
            files[p] = fit_unit_pack(pac.build_container(items), p, log)
    stats.setdefault('packed', 0)
    log('battle text: %(inplace)d lines in place, %(packed)d moved into free space, %(moved)d appended, '
        '%(grown)d BINs grew' % stats)
    for u in sorted(stats.get('unplaced', ())):
        log('  battle line left in Japanese (no pointer, does not fit): ' + u)
    return files


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'extract':
        extract()
    elif c == 'slices':
        slices()
    elif c == 'apply':
        apply()
    elif c == 'dry':
        build_files(open(os.path.join(DISC, 'GR.VFS'), 'rb').read(), {})
    else:
        sys.exit(0 if all(check(p) for p in sys.argv[2:]) else 1)
