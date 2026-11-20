"""Glossary name consistency for the story script (BASE_RULES: run AFTER agent fixes).

    python tools/fix_names.py report      rows whose Japanese has a glossary term but whose
                                          English has none of its accepted forms
    python tools/fix_names.py fix [--dry]  apply VARIANTS replacements to out/mform_*.json

VARIANTS: known wrong spellings -> glossary spelling (word-boundary, case-sensitive).
Add an entry here when a report shows the same wrong form in several rows; then the
name is on the agents' do-not-touch list (docs/REVIEW.md).
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'work', 'translation', 'en', 'out')
SL = os.path.join(ROOT, 'work', 'translation', 'en', 'slices')

VARIANTS = {
    'Ryouma': 'Ryoma', 'Randou': 'Lando', 'Nion': 'Neon', 'Him Shatner': 'Heim Shatner',
    'Gustav': 'Gustaf', 'Schwarz': 'Schwartz', 'Gimbag': 'Gimbug', 'Gyimbag': 'Gimbug',
    'Uzara': 'Uzahra', 'Dragon Tortoise': 'Dragon Turtle', 'Hyakki Imperial': 'Hyakki Empire',
}


def glossary():
    g = json.load(open(os.path.join(ROOT, 'work', 'glossary', 'glossary.json'), encoding='utf-8'))
    terms = []
    for e in g:
        jps = [j.strip() for j in e['jp'].split('/')]
        ens = [x.strip() for x in e['en'].split('/')]
        for j in jps:
            if len(j) >= 2:
                terms.append((j, ens))
    terms.sort(key=lambda t: -len(t[0]))
    return terms


def load():
    rows = {}
    for f in sorted(glob.glob(os.path.join(SL, 'mform_*.json'))):
        for x in json.load(open(f, encoding='utf-8')):
            rows[x['id']] = x
    return rows


def report():
    terms = glossary()
    src = load()
    n = 0
    for f in sorted(glob.glob(os.path.join(OUT, 'mform_*.json'))):
        for x in json.load(open(f, encoding='utf-8')):
            jp = src.get(x['id'], {}).get('jp', '')
            seen = set()
            for j, ens in terms:
                if j in jp and j not in seen:
                    seen.update(k for k, _ in terms if k in j)
                    forms = set(ens)
                    for e in ens:
                        forms.update(w for w in e.split() if len(w) > 3 and w[0].isupper())
                    if not any(fm in x['en'] for fm in forms):
                        print('%s\t%s -> %s\t%s' % (x['id'], j.encode('unicode_escape').decode(), '/'.join(ens), x['en'][:90]))
                        n += 1
    print(n, 'rows to look at')


def fix(dry):
    pat = {k: re.compile(r'\b%s\b' % re.escape(k)) for k in VARIANTS}
    total = 0
    for f in sorted(glob.glob(os.path.join(OUT, 'mform_*.json'))):
        xs = json.load(open(f, encoding='utf-8'))
        changed = False
        for x in xs:
            new = x['en']
            for k, p in pat.items():
                new = p.sub(VARIANTS[k], new)
            if new != x['en']:
                print('%s: %s\n    -> %s' % (x['id'], x['en'][:100], new[:100]))
                total += 1
                if not dry:
                    x['en'] = new
                    changed = True
        if changed:
            json.dump(xs, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(total, 'rows', '(dry run)' if dry else 'changed')


if __name__ == '__main__':
    if sys.argv[1] == 'report':
        report()
    else:
        fix('--dry' in sys.argv)
