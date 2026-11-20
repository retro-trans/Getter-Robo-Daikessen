"""UI translation slices (work/translation/en/ui.json -> slices/ui_NN.json, out/ui_NN.json).

    python tools/ui_slices.py make        150 rows per slice, with kind / limits
    python tools/ui_slices.py apply       merge out/ui_NN.json 'en' into ui.json
    python tools/ui_slices.py check out/ui_NN.json

Per row: max_bytes = hard limit (fixed field inside a record: the English must fit);
max_px = display width of the Japanese (12 px per Japanese char) = the box the game drew
for it; English over max_px may overflow menus (dialogue rows have no px limit: wrapped).
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR = os.path.join(ROOT, 'work', 'translation', 'en')
SIZE = 150
SKIP = {'exe_8002121E', 'exe_80082C68', 'exe_8003A7C6',   # binary noise
        'exe_8003A7C7', 'exe_8001E8ED', 'exe_8001ED0D', 'exe_8002E5FA',
        'flight_800DEF6D', 'flight_800E777D', 'briefing_800B1FA8', 'battle_800AA922',
        'exe_80080B6C', 'exe_80080B6D',
        'exe_8008078C',      # symbol glyph list (font)
        'battle_800AA8BC'}   # full-width digit table used to print numbers                  # kanji glyph lookup table (font)
WEAPONS = (0x800126F4, 0x80015B8C)               # weapon records 0x34, name field 32
UNITS = (0x80015BA8, 0x800174CF)                 # unit records 0x3A, name field 24
# referenced, but the lui is in another branch's delay slot: cannot be relocated
FIXED_ROOM = {'game_8008C2E8': 6, 'game_8008C368': 6, 'game_8008D1BC': 6,
              # the ability-select screen draws a computed pointer 0x8008BC60 (padding after
              # this string) as the empty last line of "None": keep that byte NUL
              'title_8008BC38': 39,
              # terrain names: table of 5-byte records, name = 0x8008B7F0 + index * 5
              **{'game_%08X' % (0x8008B7F0 + 5 * i): 4 for i in range(9)},
              # range shapes: 7-byte records from 0x8008D14C
              'game_8008D14C': 6,
              # the unit command menu points at +2 ("状態" = Status): keep in place, so
              # "SFStatus" + 2 reads "Status"
              'game_8008BBFE': 9}
# title.bin types these lines with a fixed character budget (counters at +0x32C.. of its
# work area): the English must not be longer or it is cut off
MAX_CHARS = {'title_8008C08C': 29, 'title_8008C0B0': 29,
             'title_8008C190': 15, 'title_8008C1A0': 15, 'title_8008C1B0': 22}


def kind(r):
    a = int(r['addr'], 16)
    jp = r['jp']
    if r['file'] == 'exe' and WEAPONS[0] <= a < WEAPONS[1]:
        return 'weapon name' if not re.search('レベル', jp) or '（' in jp else 'skill level'
    if r['file'] == 'exe' and UNITS[0] <= a < UNITS[1]:
        return 'unit name'
    if r['file'] == 'title':
        return 'ui'         # title.bin draws its Michiru lines with the plain string drawer (no wrap)
    if jp.startswith('$') or jp.startswith('「') or '」' in jp:
        return 'dialogue'
    return 'ui'


def jp_px(s):
    import wrap
    s = re.sub(r'\$[fm]\d\d[a-z]|\$s\d\d|%\d|%[cs]\d?|%d|\$/', '', s)
    return sum(12 if ord(c) >= 0x80 else wrap.char_w(c) for c in s)


def limits(r):
    a = int(r['addr'], 16)
    k = kind(r)
    if r['id'] in FIXED_ROOM:
        return FIXED_ROOM[r['id']], jp_px(r['jp'])
    if r['refs'] == 0:
        if k == 'weapon name' or k == 'skill level':
            mb = 31
        elif k == 'unit name':
            mb = 23
        else:
            mb = min(r['room'], (len(r['jp'].encode('cp932')) + 4) & ~3) - 1
    else:
        mb = None
    return mb, (None if k == 'dialogue' else jp_px(r['jp']))


def make():
    rows = [r for r in json.load(open(os.path.join(TR, 'ui.json'), encoding='utf-8')) if r['id'] not in SKIP]
    os.makedirs(os.path.join(TR, 'slices'), exist_ok=True)
    n = 0
    for i in range(0, len(rows), SIZE):
        out = []
        for r in rows[i:i + SIZE]:
            mb, px = limits(r)
            out.append({'id': r['id'], 'kind': kind(r), 'max_bytes': mb, 'max_px': px, 'jp': r['jp'], 'en': ''})
        json.dump(out, open(os.path.join(TR, 'slices', 'ui_%02d.json' % n), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        n += 1
    print(n, 'slices', len(rows), 'rows')


CODE = re.compile(r'\$[fm]\d\d[a-z]|\$[sp][0-9A-Fa-f]{2}|%\d|\$/|\$n|%[cs]\d?|%d|%s')


def check(path):
    import collections
    import wrap
    out = json.load(open(path, encoding='utf-8'))
    src = {x['id']: x for x in json.load(open(os.path.join(TR, 'slices', os.path.basename(path)), encoding='utf-8'))}
    errs = []
    if [x['id'] for x in out] != list(src):
        errs.append('ids differ from the input slice')
    for x in out:
        s = src.get(x['id'])
        if not s:
            continue
        en = x.get('en', '')
        if not en:
            errs.append('%s: empty' % x['id'])
            continue
        if any(not (0x20 <= ord(c) < 0x7F or (c == chr(10) and chr(10) in s['jp'])) for c in en):
            errs.append('%s: non-ASCII' % x['id'])
        if collections.Counter(CODE.findall(en)) != collections.Counter(CODE.findall(s['jp'])):
            errs.append('%s: control codes differ' % x['id'])
        if s['max_bytes'] is not None and len(en.encode('ascii', 'replace')) > s['max_bytes']:
            errs.append('%s: %d bytes > max_bytes %d' % (x['id'], len(en), s['max_bytes']))
        if s['max_px'] is not None:
            w = wrap.width(re.sub(r'%[cs]\d?|%d|%s', '', en))
            if w > s['max_px']:
                errs.append('%s: %d px > max_px %d (warning: may overflow its box)' % (x['id'], w, s['max_px']))
    for e in errs:
        print(e)
    hard = [e for e in errs if 'warning' not in e]
    print('%d rows, %d problems (%d warnings)' % (len(out), len(hard), len(errs) - len(hard)))
    return not hard


def apply():
    p = os.path.join(TR, 'ui.json')
    rows = json.load(open(p, encoding='utf-8'))
    byid = {r['id']: r for r in rows}
    n = 0
    od = os.path.join(TR, 'out')
    for f in sorted(os.listdir(od)):
        if f.startswith('ui_'):
            for x in json.load(open(os.path.join(od, f), encoding='utf-8')):
                if x.get('en') and x['id'] in byid:
                    byid[x['id']]['en'] = x['en']
                    n += 1
    json.dump(rows, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('applied', n)


if __name__ == '__main__':
    if sys.argv[1] == 'make':
        make()
    elif sys.argv[1] == 'apply':
        apply()
    else:
        sys.exit(0 if all(check(p) for p in sys.argv[2:]) else 1)
