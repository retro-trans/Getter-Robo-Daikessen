# VWF — Getter Robo Daikessen! (SLPS_022.32)

## Dialogue proportions — 0.8.24

Ordinary message-window text now uses a dialogue-only pixel-row compaction
mode. In the current hand-drawn font, row 7 repeats row 6 in every Latin
letter and digit, and in 20 other printable characters. Removing that one
duplicate row reduces capitals from nine ink rows to eight and lowercase
bodies from seven to six. Other character shapes remain intact.

This does not rescale the glyph texture. Two native SPRT commands draw rows
0..6 and 8..11, abutting at destination row 7. Each retained source pixel
occupies exactly one framebuffer pixel. This preserves the stroke widths,
transparent background, gradient and shadow. Font artwork, glyph advances,
word wrapping, window geometry, typewriter timing, colors and paging remain
unchanged. Ordinary menus and explicit font modes (including the briefing's
0x22 normal font) retain their existing rendering.

`tools/dialogue_font.py` redirects the message printer at 0x8005BCB4 and opts
only default-size window text into reserved high-byte mode 0x02. The glyph
hook at 0x8004DAAC sets bit 22 for eligible ASCII characters; sprite hooks
at 0x8004D910 and 0x8004D930 emit/link the extra unscaled strip. Other calls
execute their original geometry and use one sprite. The existing native
ordering-table and texture-page commands remain in use.

Resident blocks: DDC0..DDF4 (52 bytes), F5B8..F5FC (68 bytes), and
DE80..DF58 (216 bytes), all at 0x80000000. The build checks every bound,
including DF80's observed BIOS context boundary. The DE00..DE80 debug
fixture, screenshot scratch and original font helpers remain separate.
No new atlas, VRAM allocation, disc extent or executable size is needed.

Each compacted character adds one 20-byte SPRT to the native primitive
buffer. This adds CPU/GPU work, so physical PlayStation timing and BIOS
compatibility remain unverified. The patch uses native PS1 primitives and
does not depend on emulator rendering extensions.

Validation: 188 native CPU/packet probes cover all 94 non-space printable
ASCII glyphs in ordinary and dialogue modes. Strip sizes, positions, UVs,
palettes and allocation lengths are checked. Source-row checks prove the
omitted foreground rows are duplicates. The reported Episode 2 dialogue is
captured from the finished disc; menu artwork, all 394 other VFS files and
translated scripts stay byte-identical. Evidence: work/ui/dialogue/v0824/.

`tools/dialogue_font_check.py` defaults to a dry run and restores test RAM,
graphics pointers and CPU registers after its opt-in checks.

## Base font and renderer

### Command edge fit — 0.8.26

The longer `Combine` label can extend past the left edge when right-aligned
at a small hex-menu anchor. Both native menu paths now clamp the shared text
and highlight offset so the text starts at x>=1 and the highlight at x>=0.
Already-visible entries retain their coordinates. Width calculation, label
binding, input and command behavior remain native.

`tools/command_layout.py` adds a 36-byte helper at 0x8000DF58..0x8000DF7C,
immediately after the dialogue strips and below the observed DF80 BIOS
context boundary. Hooks are 0x80058104/108 and 0x80058310. The shared return
restores the second path's signed row-phase load, retaining the R3000 load
delay before division. No allocation, font or texture changes are added.
`command_layout_check.py --apply` tests 24 native cases across both hook
sites; test memory and CPU registers are restored afterward.

Generator: `tools/vwf.py` (called by `tools/build.py`). Font: `tools/fonts/gr_latin.txt`
(hand-drawn 1 px strokes; caps rows 0-8, x-height rows 2-8, descenders rows 9-10). The
renderer colours ink with the game's row gradient (FNT_CLUT indices 0-9 by row) and adds
the game's (+1,+1) drop shadow (index 10); index 11 is transparent. Advance = glyph width
+ shadow column + 1 px (space 4 px, digits all 7 px so numbers keep their columns).

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
0x8001A3E4. Early builds appended the enlarged executable to the end of the
disc. Starting with 0.8.30 the executable stays at retail sector 23 and the
archive shifts within the original disc footprint, as in the 0.8.28 PSP boot test.

| site | change |
| --- | --- |
| 0x8004E0A8 `jal 0x8004DA64` -> `jal drawadv` | after drawing, pen += width - s7 (the drawer then adds s7) |
| 0x8005BC74 `mflo t1` -> `addu t1, s0, zero` | dialogue: x = left + pixel sum |
| 0x8005BC84 `addiu s0, s0, 1` -> `jal dlgadv` | dialogue: pixel sum += width of the item (skips `%X`) |
| 0x8005B8A0 `addiu v0, v0, 1` -> `jal colsj` | typewriter column += width (SJIS) |
| 0x8005BA80 `addiu v0, v0, 1` -> `jal cola` | typewriter column += width (single byte) |
| 0x8005B168 / 0x8005B150 | window columns = text width in pixels (/2 for double size) |
| 0x8004E104 -> `j strlen` | display length = ceil(pixel width / 12) (centring, box sizes) |
| 0x8004E2A0 / 0x8004E2A4 | 12 px number printer: digit step 24/12 -> 14/7 |
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

## Larger main font — 0.8.7

The Latin font now uses nine-pixel capitals (previously seven) and seven-pixel
lowercase bodies (previously five), with wider hand-drawn letters. A measured
original FONT12 kana sample has ten ink rows, so main English text now comes
within one pixel of its visible height. The glyphs remain inside the existing
12x12 cells. Baseline row 8 and descenders through row 10 are retained.
The original gradient palette, transparent pixels and shadow are unchanged.

Full-size status/assignment text still renders into 19x24 cells. Compact roles
use 11x13 cells with matching width advances, preserving roughly their former
visible size despite the larger glyph artwork. Native FONT8 is unchanged.
Digits use seven-pixel advances (14 when doubled), and the native numeric
printer follows those advances. No new atlas, framebuffer, VRAM allocation,
resident-code space or glyph flags are added. The resident block still ends
at 0x8000F4B8, below the next string pool at 0x8000F600.

Normal dialogue is rewrapped using the new width table by the existing build.
Four minigame and 21 preview captions have balanced new line breaks; joining
the lines gives identical words and punctuation, and every cue keeps its ID
and original timing. Baked movie captions use their existing separate font.
Static checks cover all 358 status names, assignment names, every native cue,
and the fixed overlay/load limits. Captures and build verification live in
`work/ui/font/v087/`. Real-console timing checks remain outstanding.

## Status body-text mode — 0.8.10

An exact 0x32 high-byte draw mode selects 16x20 cells and proportional body
advances for status names and values. Compact 11x13 labels and 19x24 headings
retain their previous modes; all other calls fall through to the unchanged
old routines. The new dispatchers/table are appended after the old resident
block. Existing resident bytes and label addresses (including both original
status advance tables) are unchanged, preserving other overlays' references.
The block now ends at 0x8000F534, below the 0x8000F600 string pool. Font artwork
is unchanged. Only the two font hook call targets and boot payload are updated
in the main executable. The boot file grows by 2048 bytes and is relocated
through the standard ISO9660/PS1 executable loading path.

## Map HUD terrain tag — 0.8.12

The native terrain tag is drawn by the call at 0x80096290 using local x=9,
y=7. Lnd and Sea have 21-pixel advances with the current font; at x=9 they
extend into the resource block beginning at x=27. The instruction at
0x80096270 changes from 0x24040009 to 0x24040003 (x=3). All terrain variants
share this anchor and now leave at least three pixels of horizontal space.
The label remains inside its existing viewport. No font, window, field-value,
branch, allocation or resource changes are introduced. Physical-console
validation is outstanding. Audit/capture files: work/ui/map_hud/v0812/.

## Opt-in medium secondary headers — 0.8.21

Exact high-byte mode `0x36` draws existing glyphs in 14x17 cells. Only the
Weapons page's Range/Area headings request it. Advances for original widths
0–12 are `0,1,2,4,5,6,7,8,9,11,12,13,14` (rounded 14/12 scaling).
Other modes branch to the existing briefing/body/compact/legacy dispatchers.

The old block at 0x8000F000 and its labels/tables are unchanged. The new
dispatcher/advance helper occupies 124 bytes at 0x8000DD40..0x8000DDBC,
after preview scratch 0x8000DD00..0x8000DD20 and before minigame debug
fixtures at 0x8000DE00. It is separate from screenshot scratch ending
0x8000DC20, difficulty code 0x8000DC40..0x8000DCE8 and BIOS thread storage
at 0x8000E000 onward. The boot stub copies it and calls BIOS FlushCache.
Only two original font-call targets change; other original text instructions
remain byte-identical. No texture/CLUT, heap, VRAM or EXE-load-size expansion.
Physical-console timing is untested.

Native `work/ui/status/v0821/font-check.json` verifies the medium mode and
eight old modes. Header traces also verify actual glyph sizes/positions in
the game. The status RAM reload tool copies the new block explicitly when
`--hotpatch` is requested.
