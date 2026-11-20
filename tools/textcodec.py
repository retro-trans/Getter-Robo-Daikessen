"""Text encoding for inserted (English) strings.

Translation files hold Unicode text with the game's control codes kept as ASCII:
  $fNNx $mNNx (portrait), $sNN (speed), $/ (page), $n (player name), $pNN,
  %N (colour; %0 = default), \\n (line break, written as backslash + n), @XY (icon).
Encoding: ASCII as is; a few typographic characters are folded to ASCII; any remaining
Japanese is encoded as Shift-JIS (names / glyphs the font still has).
"""
FOLD = {
    '’': "'", '‘': "'", '“': '"', '”': '"', '—': '-', '–': '-',
    '…': '...', ' ': ' ', '　': ' ',
}


def encode(s):
    out = bytearray()
    for ch in s:
        ch = FOLD.get(ch, ch)
        for c in ch:
            if ord(c) < 0x80:
                out.append(ord(c))
            else:
                out += c.encode('cp932')
    return bytes(out)


def decode(b):
    return b.decode('cp932', 'replace')
