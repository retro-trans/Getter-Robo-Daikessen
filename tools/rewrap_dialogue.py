"""Reflow current story text without changing words, cues or explicit pages.

Dry-run is the default. --apply backs up the working files locally, writes
the new wraps and a Japanese-free English copy, and records the fit audit.
"""
import argparse
import json
from pathlib import Path
import re

import strip_jp
import wrap

ROOT = Path(__file__).resolve().parents[1]


def canonical(text):
    return ' '.join(re.sub(r'\s*(\$/)\s*', r' \1 ',
                           text.replace(wrap.NL, ' ')).split())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    path = ROOT / 'work/translation/en/mform.json'
    raw = path.read_bytes()
    rows = json.loads(raw)
    changed, over_before, maximum = [], [], 0
    for row in rows:
        old = row.get('en', '')
        if not old:
            continue
        new = wrap.reflow(old)
        if canonical(old) != canonical(new):
            raise ValueError(f"Words or codes changed: {row['id']}")
        old_codes = [(k, t) for k, t in wrap.tokens(old) if k in ('code', 'name', 'page')]
        new_codes = [(k, t) for k, t in wrap.tokens(new) if k in ('code', 'name', 'page')]
        if old_codes != new_codes:
            raise ValueError(f"Control sequence changed: {row['id']}")
        if wrap.reflow(new) != new:
            raise ValueError(f"Wrap is not stable: {row['id']}")
        widths = [wrap.width(line) for line in wrap.lines(new)]
        if max(widths, default=0) > wrap.WIDTH:
            raise ValueError(f"Overwide line: {row['id']}")
        maximum = max(maximum, *widths)
        if any(wrap.width(line) > wrap.WIDTH for line in wrap.lines(old)):
            over_before.append(row['id'])
        if old != new:
            changed.append(dict(id=row['id'], before=old, after=new, widths=widths))
        row['en'] = new
    report = dict(version='0.8.11', examined=len(rows), changed=len(changed),
                  changed_ids=[r['id'] for r in changed],
                  overwide_before=len(over_before), overwide_after=0,
                  max_line_width=maximum, limit=wrap.WIDTH,
                  runtime_name_reserve=wrap.NAME_W,
                  wording_and_control_sequences_unchanged=True)
    print(json.dumps({k: v for k, v in report.items() if k != 'changed_ids'}, indent=2))
    for row in changed:
        if row['id'] in ('MF02_047D', 'MF16_0332', 'MF01_1689'):
            print(row['id'], row['after'])
    if not args.apply:
        return
    backup = ROOT / 'work/source/rewrap_v0811'
    backup.mkdir(parents=True, exist_ok=True)
    for target in (path, path.with_suffix('.en.json')):
        saved = backup / target.name
        if target.exists() and not saved.exists():
            saved.write_bytes(target.read_bytes())
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=1) + '\n', encoding='utf8')
    path.with_suffix('.en.json').write_text(
        json.dumps(strip_jp.strip(rows), ensure_ascii=False, indent=1) + '\n', encoding='utf8')
    out = ROOT / 'work/ui/dialogue/v0811'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'wrap-audit.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    (out / 'changes.json').write_text(json.dumps(changed, indent=2) + '\n', encoding='utf8')


if __name__ == '__main__':
    main()
