"""Translation slices for agents (BASE_RULES.md: 80 consecutive rows per agent).

    python tools/slices.py make mform            -> work/translation/en/slices/mform_NN.json
    python tools/slices.py apply mform           merge slice 'en' bodies into mform.json
    python tools/slices.py status mform

A dialogue row is split into head + body + tail:
    jp   = $f21a$s00%2早乙女%0$s13「……」
    head = $f21a$s00%2{NAME}%0$s13      (codes and the speaker tag; name from the glossary)
    body = ……                           (what the agent translates; codes inside are kept)
    tail = 」                            (dropped in English)
English row = head (with the English speaker name) + ': ' + body, then word-wrapped.
Original line breaks (\\n) are removed from the bodies given to agents (English is re-wrapped
by tools/wrap.py); $/ (wait for button / new page) and $sNN (speed / pause) are kept.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TR = os.path.join(ROOT, 'work', 'translation', 'en')
SL = os.path.join(TR, 'slices')
SIZE = 80
BS = chr(92)
NL = BS + 'n'
HEAD = re.compile(r'^((?:\$[fm]\d\d[a-z])?(?:\$s\d\d)*%2)(.*?)(%0(?:\$s\d\d)*)「')


def split(jp):
    """(head_prefix, speaker, head_suffix, body, tail) — speaker '' for narration."""
    m = HEAD.match(jp)
    if not m:
        pre = re.match(r'^((?:\$[fm]\d\d[a-z]|\$s\d\d)*)', jp).group(1)
        body = jp[len(pre):]
        tail = ''
        if body.endswith('」'):
            body, tail = body[:-1], '」'
        return pre, '', '', body, tail
    body = jp[m.end():]
    tail = ''
    if body.endswith('」'):
        body, tail = body[:-1], '」'
    return m.group(1), m.group(2), m.group(3), body, tail


def glossary():
    p = os.path.join(ROOT, 'work', 'glossary', 'glossary.json')
    g = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else []
    return g


def speaker_names():
    p = os.path.join(ROOT, 'work', 'glossary', 'speakers.json')
    return json.load(open(p, encoding='utf-8')) if os.path.exists(p) else {}


BANNER = re.compile(r'^( ' + re.escape(NL) + r' +)- (.*) -(.*)$')
BANNERS = {'敵増援': 'Enemy Reinforcements', '作戦終了': 'Mission Complete',
           '作戦失敗': 'Mission Failed'}


def banner(jp):
    """' \n       - 敵増援 -' style banners -> centred English (None if not a banner)."""
    import wrap
    m = BANNER.match(jp)
    if not m or m.group(2) not in BANNERS:
        return None
    t = '- %s -' % BANNERS[m.group(2)]
    pad = max(0, (wrap.WIDTH - wrap.width(t)) // 2 // wrap.char_w(' '))
    return ' ' + NL + ' ' * pad + t, m.group(3)


def make(group):
    rows = json.load(open(os.path.join(TR, group + '.json'), encoding='utf-8'))
    names = speaker_names()
    os.makedirs(SL, exist_ok=True)
    n = 0
    for i in range(0, len(rows), SIZE):
        out = []
        for r in rows[i:i + SIZE]:
            b = banner(r['jp'])
            if b:
                if b[1]:      # banner followed by more text: translate the rest
                    out.append({'id': r['id'], 'speaker_jp': '', 'speaker_en': '',
                                'note': 'shown after a centred banner line; translate only this part',
                                'jp': b[1].replace(NL, ''), 'en': ''})
                continue
            pre, sp, suf, body, tail = split(r['jp'])
            item = {'id': r['id'], 'speaker_jp': sp, 'speaker_en': names.get(sp, '') if sp != '$n' else '$n (player)',
                    'jp': body.replace(NL, ''), 'en': ''}
            if r.get('gender'):
                item['gender_variant'] = 'male player' if r['gender'] == 'm' else 'female player'
            out.append(item)
        p = os.path.join(SL, '%s_%02d.json' % (group, n))
        if os.path.exists(p):
            old = {x['id']: x for x in json.load(open(p, encoding='utf-8'))}
            for x in out:
                if old.get(x['id'], {}).get('en'):
                    x['en'] = old[x['id']]['en']
        json.dump(out, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        n += 1
    print(n, 'slices of', SIZE)


CAPTION = re.compile(r'^(.*?)( *)(- .+ -)(.*)$')
EMBED = re.compile(r'(?<!^)(\$[fm]\d\d[a-z]\$s\d\d%2[^%]*%0\$s\d\d: )')


def fix_breaks(jp, en):
    """Restore line breaks the slices dropped: before an embedded speaker tag, and the
    leading break of centred captions (' \n   - Place -')."""
    import wrap
    en = EMBED.sub(lambda m: NL + m.group(1), en)
    if re.search(re.escape(NL) + r' +[-－] ', jp):
        m = CAPTION.match(en)
        if m and not m.group(1).endswith(NL):
            t = m.group(3)
            pad = max(0, (wrap.WIDTH - wrap.width(t)) // 2 // wrap.char_w(' '))
            head = m.group(1).rstrip()
            if head.endswith(NL):
                head = head[:-len(NL)].rstrip()
            en = head + ' ' + NL + ' ' * pad + t + m.group(4)
    return en


def compose(row, body_en, names):
    pre, sp, suf, body, tail = split(row['jp'])
    if not sp:
        return pre + body_en
    name = '$n' if sp == '$n' else names.get(sp, sp)
    return pre + name_tag(name) + suf + ': ' + body_en


def name_tag(name):
    return name        # the head prefix already ends with %2


def apply(group):
    import wrap
    p = os.path.join(TR, group + '.json')
    rows = json.load(open(p, encoding='utf-8'))
    byid = {r['id']: r for r in rows}
    names = speaker_names()
    n = 0
    for r in rows:
        b = banner(r['jp'])
        if b and not b[1]:
            r['en'] = b[0]
    od = os.path.join(TR, 'out')
    for f in sorted(os.listdir(od)) if os.path.isdir(od) else []:
        if not f.startswith(group + '_'):
            continue
        for x in json.load(open(os.path.join(od, f), encoding='utf-8')):
            if x.get('en') and x['id'] in byid:
                r = byid[x['id']]
                r['en_body'] = x['en']
                b = banner(r['jp'])
                if b:
                    r['en'] = b[0] + wrap.wrap(x['en'])
                else:
                    r['en'] = fix_breaks(r['jp'], wrap.wrap(compose(r, x['en'], names)))
                n += 1
    json.dump(rows, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('applied', n, 'rows')


def status(group):
    tot = done = 0
    od = os.path.join(TR, 'out')
    for f in sorted(os.listdir(SL)):
        if f.startswith(group + '_'):
            po = os.path.join(od, f)
            xs = json.load(open(po, encoding='utf-8')) if os.path.exists(po) else []
            d = sum(1 for x in xs if x.get('en'))
            print(f, d, '/', len(xs))
            tot += len(xs)
            done += d
    print('total', done, '/', tot)


if __name__ == '__main__':
    {'make': make, 'apply': apply, 'status': status}[sys.argv[1]](sys.argv[2])
