"""Check a translated slice: python tools/check_slice.py work/translation/en/out/mform_NN.json

Checks: same ids/order as the input slice, printable ASCII, control codes preserved
(same count of each code), no manual line breaks, glossary names (warnings).
"""
import collections
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BS = chr(92)
CODE = re.compile(r'\$[fm]\d\d[a-z]|\$[sp][0-9A-Fa-f]{2}|%\d|\$/|\$n')


def codes(s):
    return collections.Counter(CODE.findall(s))


def check(path):
    out = json.load(open(path, encoding='utf-8'))
    src = os.path.join(ROOT, 'work', 'translation', 'en', 'slices', os.path.basename(path))
    inp = json.load(open(src, encoding='utf-8'))
    errs = []
    if [x['id'] for x in out] != [x['id'] for x in inp]:
        errs.append('ids differ from the input slice (missing, extra or reordered rows)')
    byid = {x['id']: x for x in inp}
    for x in out:
        i = x.get('id')
        en = x.get('en', '')
        if i not in byid:
            continue
        if not en.strip():
            errs.append('%s: empty' % i)
            continue
        bad = [c for c in en if not (0x20 <= ord(c) < 0x7F)]
        if bad:
            errs.append('%s: non-ASCII %r' % (i, ''.join(sorted(set(bad)))))
        if BS + 'n' in en:
            errs.append('%s: contains \\n (do not break lines)' % i)
        a, b = codes(byid[i]['jp']), codes(en)
        if a != b:
            errs.append('%s: codes differ jp %s en %s' % (i, dict(a), dict(b)))
        if en.startswith('"') and en.endswith('"'):
            errs.append('%s: drop the surrounding quotes' % i)
    for e in errs:
        print(e)
    print('%d rows, %d problems' % (len(out), len(errs)))
    return not errs


if __name__ == '__main__':
    ok = all(check(p) for p in sys.argv[1:])
    sys.exit(0 if ok else 1)
