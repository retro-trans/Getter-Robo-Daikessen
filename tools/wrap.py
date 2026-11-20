"""Word wrap for the VWF dialogue windows (pixel widths from tools/vwf.py).

Message windows (exe 0x8005B0C0 setup): 288 px wide, portrait 48 px -> 210 px of text,
4 lines per page; the engine pages by itself after 4 lines and breaks lines on its own
(mid-word) only when a line is wider than the window, so every line is wrapped here.

    python tools/wrap.py "text with codes"        print the wrapped text and line widths

Codes that take no room: $fNNx $mNNx $sNN $pNN %N $/ (page; resets the line count).
$n (player name) counts as NAME_W pixels. Existing \\n are kept as forced breaks.
"""
import re
import sys

sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath(__file__)))
import vwf   # noqa: E402

WIDTH = 210
LINES = 4
NAME_W = 6 * 7       # longest player name (6 chars) in the full-width Latin cells
BS = chr(92)
NL = BS + 'n'
CODE = re.compile(r'\$[fm]\d\d[a-z]|\$[sp][0-9A-Fa-f]{2}|%\d|\$/|\$n|' + re.escape(NL))

_WA = None


def char_w(ch):
    global _WA
    if _WA is None:
        _WA, _ = vwf.width_tables()
    c = ord(ch)
    if 0x20 <= c < 0x7F:
        return _WA[c - 0x20]
    return 12


def tokens(s):
    """[(kind, text)] kind: 'code', 'nl', 'page', 'name', 'text'."""
    out = []
    pos = 0
    for m in CODE.finditer(s):
        if m.start() > pos:
            out.append(('text', s[pos:m.start()]))
        t = m.group()
        out.append(('nl' if t == NL else 'page' if t == '$/' else 'name' if t == '$n' else 'code', t))
        pos = m.end()
    if pos < len(s):
        out.append(('text', s[pos:]))
    return out


def width(s):
    w = 0
    for k, t in tokens(s):
        if k == 'text':
            w += sum(char_w(c) for c in t)
        elif k == 'name':
            w += NAME_W
    return w


def wrap(s, limit=WIDTH):
    """Return s with \\n inserted at spaces so that no line is wider than limit."""
    # split into words keeping codes glued to the following word
    out = []
    line_w = 0
    pending = ''           # codes waiting for the next word
    for k, t in tokens(s):
        if k in ('nl', 'page'):
            out.append(pending + t)
            pending = ''
            line_w = 0
            continue
        if k in ('code',):
            pending += t
            continue
        if k == 'name':
            words = [('$n', NAME_W)]
        else:
            words = []
            for part in re.split(r'( )', t):
                if part:
                    words.append((part, sum(char_w(c) for c in part)))
        for wtext, ww in words:
            if wtext == ' ':
                if line_w == 0:
                    continue
                out.append(pending + ' ')
                pending = ''
                line_w += ww
                continue
            if line_w + ww > limit and line_w > 0:
                # drop the space before the break
                if out and out[-1].endswith(' '):
                    out[-1] = out[-1][:-1]
                out.append(NL)
                line_w = 0
            out.append(pending + wtext)
            pending = ''
            line_w += ww
    if pending:
        out.append(pending)
    return ''.join(out)


def lines(s):
    """Rendered lines (codes removed, $n shown as NAME) for checks."""
    res = []
    cur = ''
    for k, t in tokens(s):
        if k in ('nl', 'page'):
            res.append(cur)
            cur = ''
        elif k == 'text':
            cur += t
        elif k == 'name':
            cur += '$n'
    res.append(cur)
    return res


if __name__ == '__main__':
    w = wrap(sys.argv[1])
    print(w)
    for ln in lines(w):
        print('%4d  %s' % (width(ln.replace('$n', '\0')) + ln.count('$n') * NAME_W, ln))
