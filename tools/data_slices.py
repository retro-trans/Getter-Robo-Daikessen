"""Slices for data-file text (work/translation/en/data.json).

    python tools/data_slices.py make          BRF -> slices/data_brf.json, HT -> data_ht_0/1.json
    python tools/data_slices.py autofill      MCN/PIL names from ui.json / glossary (exact jp)
    python tools/data_slices.py check out/data_*.json
    python tools/data_slices.py apply
"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR = os.path.join(ROOT, 'work', 'translation', 'en')
BS = chr(92)
CODE = re.compile(r'\$[fm]\d\d[a-z]|\$[sp][0-9A-Fa-f]{2}|%\d|\$/|\$n|%[cs]\d?|%d|%s')


def load():
    return json.load(open(os.path.join(TR, 'data.json'), encoding='utf-8'))


def save(rows):
    json.dump(rows, open(os.path.join(TR, 'data.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def kind(r):
    if r['src'] == 'BRF':
        if r['jp'].startswith('第') and '話' in r['jp'][:5]:
            return 'chapter title'
        return 'lines' if BS + 'n' in r['jp'] or '　　' in r['jp'] else 'narration'
    if r['src'] == 'HT':
        return 'battle line'
    return 'name'


def make():
    rows = load()
    os.makedirs(os.path.join(TR, 'slices'), exist_ok=True)
    groups = {'data_brf': [r for r in rows if r['src'] == 'BRF']}
    ht = [r for r in rows if r['src'] == 'HT']
    groups['data_ht_0'] = ht[:98]
    groups['data_ht_1'] = ht[98:]
    left = [r for r in rows if r['src'] in ('MCN', 'PIL') and not r.get('en')]
    if left:
        groups['data_names'] = left
    for name, rs in groups.items():
        out = [{'id': r['id'], 'kind': kind(r), 'max_bytes': r.get('max_bytes'), 'jp': r['jp'], 'en': ''} for r in rs]
        json.dump(out, open(os.path.join(TR, 'slices', name + '.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print(name, len(out))


def autofill():
    rows = load()
    ui = {}
    for r in json.load(open(os.path.join(TR, 'ui.json'), encoding='utf-8')):
        if r.get('en'):
            ui.setdefault(r['jp'], r['en'])
    gl = {}
    for e in json.load(open(os.path.join(ROOT, 'work', 'glossary', 'glossary.json'), encoding='utf-8')):
        jps = [j.strip() for j in e['jp'].split('/')]
        ens = [x.strip() for x in e['en'].split('/')]
        for i, j in enumerate(jps):
            gl.setdefault(j, ens[min(i, len(ens) - 1)])
    n = 0
    for r in rows:
        if r['src'] not in ('MCN', 'PIL') or r.get('en'):
            continue
        en = ui.get(r['jp']) or gl.get(r['jp']) or gl.get(r['jp'].replace('・', ''))
        if en and len(en) <= r.get('max_bytes', 99):
            r['en'] = en
            n += 1
    save(rows)
    print('filled', n, 'left', sum(1 for r in rows if r['src'] in ('MCN', 'PIL') and not r.get('en')))


def check(path):
    out = json.load(open(path, encoding='utf-8'))
    src = {x['id']: x for x in json.load(open(os.path.join(TR, 'slices', os.path.basename(path)), encoding='utf-8'))}
    errs = []
    if [x['id'] for x in out] != list(src):
        errs.append('ids differ from the input slice')
    for x in out:
        s = src.get(x['id'])
        en = x.get('en', '')
        if not s:
            continue
        if not en:
            errs.append('%s: empty' % x['id'])
            continue
        if any(not (0x20 <= ord(c) < 0x7F) for c in en):
            errs.append('%s: non-ASCII' % x['id'])
        if collections.Counter(CODE.findall(en)) != collections.Counter(CODE.findall(s['jp'])):
            errs.append('%s: control codes differ' % x['id'])
        if s['max_bytes'] is not None and len(en) > s['max_bytes']:
            errs.append('%s: %d bytes > %d' % (x['id'], len(en), s['max_bytes']))
        if s['kind'] == 'lines' and en.count(BS + 'n') != s['jp'].count(BS + 'n'):
            errs.append('%s: keep the same number of \\n line breaks' % x['id'])
        if s['kind'] in ('narration', 'battle line') and BS + 'n' in en:
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
        if f.startswith('data_'):
            for x in json.load(open(os.path.join(od, f), encoding='utf-8')):
                if x.get('en') and x['id'] in by:
                    by[x['id']]['en'] = x['en']
                    n += 1
    # PIL copies share the same offsets: same id, already one row
    save(rows)
    print('applied', n)


if __name__ == '__main__':
    c = sys.argv[1]
    if c == 'make':
        make()
    elif c == 'autofill':
        autofill()
    elif c == 'apply':
        apply()
    else:
        sys.exit(0 if all(check(p) for p in sys.argv[2:]) else 1)
