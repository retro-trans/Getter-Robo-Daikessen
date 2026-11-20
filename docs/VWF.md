# VWF — Getter Robo Daikessen! (SLPS_022.32)

Generator: `tools/vwf.py` (called by `tools/build.py`). Font: `tools/fonts/gr_latin.txt`
(hand-drawn 1 px strokes; caps rows 2-8, x-height rows 4-8, descenders rows 9-10). The
renderer colours ink with the game's row gradient (FNT_CLUT indices 0-9 by row) and adds
the game's (+1,+1) drop shadow (index 10); index 11 is transparent. Advance = glyph width
+ shadow column + 1 px (space 4 px, digits all 6 px so numbers keep their columns).

## How the game draws text

Every glyph is one 12x12 sprite (SPRT, or POLY_FT4 for the double sizes) from the font
sheets kept in VRAM (`bin/setup.pac`: FONT12_0 at (960,385), katakana, kanji pages).

| addr | routine |
| --- | --- |
| 0x8004DE34 | string drawer (`PrintStr` 0x8004DDFC = max count 0xFF): `%X` colour, `@XY` icon, SJIS pairs, ASCII; pen += 12 (24 for double width) |
| 0x8004DA64 | draw one code: ASCII -> full-width SJIS via the table at 0x8007F5C4, 82xx -> FONT12_0 cell `lo - 0x50` (`０` 0x824F -> cell 15, lo >= 0xF0 -> lo - 0x72), 83xx -> katakana, 81xx -> symbol list (0x8008078C, 5 columns at u 192), kanji pages |
| 0x8004D6DC | sprite emit from a descriptor {tpage, u0, v0, clut, per row} |
| 0x8005B43C | message copy: `$n` -> player name, `\n` -> 0x0A |
| 0x8005B7F4 | typewriter: one item per tick into the line buffer, column counter +0x24, auto wrap at +0x18 columns (kinsoku), page after +0x1A lines |
| 0x8005BB80 | message draw: one call of 0x8004DE34 per character at `x = left + index * 12` |
| 0x8005B0C0 | window setup: columns = text width / 12, lines = (height - 12) / 12 |

Dialogue windows: 288 x 60, portrait 48 px -> 210 px of text, 4 lines.

## Font cells

The ASCII table (0x8007F5C4, u16 per char 0x20-0x7E) maps every ASCII char to an SJIS
code whose cell now holds the English glyph:

* `0-9 A-Z a-z` -> the full-width Latin cells (0x824F.., 0x8260.., 0x8281..), so full-width
  text (name entry grid, the player's name) shows the same glyphs;
* punctuation with a full-width twin in the symbol list -> that symbol cell
  (`! " $ % & ' ( ) + , - . / : ; = ? [ ] _ ~`);
* the rest (`# * < > @ \ ^ ` { | }`) -> unused 82xx cells (0x8259-0x825E, 0x827A-0x827D,
  0x8280). 0x827E/0x827F are not free: を/ん (0x82F0/0x82F1) are drawn from them.
* the original table maps `x` to 0x8290 (`p`); fixed.

`%` and `@` are control characters of the string drawer and `$`, `\` of the message
copier: do not use them as text.

## Hooks

Code + width tables at 0x8000F000 (kernel RAM, unused: zero in every RAM dump; the
sibling projects use 0x8000EF00-0x80010000 with SCPH-1001). An entry stub appended to the
exe copies them there, calls BIOS FlushCache (A 44h) and jumps to the original entry
0x8001A3E4. The exe grows by one sector, so the disc builder moves it to the end of the image.

| site | change |
| --- | --- |
| 0x8004E0A8 `jal 0x8004DA64` -> `jal drawadv` | after drawing, pen += width - s7 (the drawer then adds s7) |
| 0x8005BC74 `mflo t1` -> `addu t1, s0, zero` | dialogue: x = left + pixel sum |
| 0x8005BC84 `addiu s0, s0, 1` -> `jal dlgadv` | dialogue: pixel sum += width of the item (skips `%X`) |
| 0x8005B8A0 `addiu v0, v0, 1` -> `jal colsj` | typewriter column += width (SJIS) |
| 0x8005BA80 `addiu v0, v0, 1` -> `jal cola` | typewriter column += width (single byte) |
| 0x8005B168 / 0x8005B150 | window columns = text width in pixels (/2 for double size) |
| 0x8004E104 -> `j strlen` | display length = ceil(pixel width / 12) (centring, box sizes) |
| 0x8004E2A0 / 0x8004E2A4 | 12 px number printer: digit step 24/12 -> 12/6 |
| 0x800580D0 / 0x80058280 -> `jal strpx` | list / hex menu items: label width in pixels (right-aligned items, highlight box = width + 2) |

Widths: `WA` (96 bytes, ASCII 0x20-0x7F) and `W82` (256 bytes by 82xx low byte, so
full-width Latin uses the ASCII widths; other codes 12). Double size doubles the width.

The engine's own auto wrap now works in pixels but breaks mid-word; English is
word-wrapped offline by `tools/wrap.py` (210 px) so it never triggers.

## Overlay code patches

`OVERLAY_PATCHES` in `tools/vwf.py` ({tag: {address: (original, new)}}), written into
`bin/<tag>.bin` by the build after checking the original word.

| overlay | address | change |
| --- | --- | --- |
| game | 0x80098474 | status weapon page: "HP" / "Getter Ray" label y+3 -> y+0 (English capitals end 3 lines lower than kanji in the 2x-tall glyphs of the 512x480 screen) |

## Not covered (yet)

* `0x8004D49C` 8x8 FONT8 printer (numbers, small labels): fixed 8 px, unchanged.
* Name entry grid: fixed 12 px cells (the letters are the new narrow glyphs).
