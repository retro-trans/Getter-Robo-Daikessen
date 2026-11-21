# Assignment and flight-menu layout — 0.8.3

## Custom-pilot rank fit — 0.8.25

The red custom-pilot rank now uses the existing compact 11x13 font at
native (190,60), beside the name and above the metadata row. Its widest
label ends at x=227, inside the pilot panel (25,50,219,54). The original red
palette and all six native rank strings/values remain unchanged.

The special draw call at 0x800B84A4 now targets the existing `text_small`
entry directly. Two native coordinate immediates move the label; no helper
code is added. The stance label moves from x=172 to x=162, leaving five
pixels between `2x Move` and `Lv` at x=207. Skill numbers remain at x=226.

Native checks temporarily seed display-only fields for every rank (-, D,
C, B, A, S), then a six-character name and two-digit skill level. All fields
and scratch are restored afterward; rank/assignment logic and save data are
not patched. Captures and bounds checks: work/ui/menu_layout/v0825/.
The EXE, dialogue font, briefing typography, panels and 393 other VFS files
remain unchanged. Physical console testing remains outstanding.

## Assignment typography correction — 0.8.22

Assignment numeric values now use the labels' existing 11x13 cell, including
pilot level/experience/skill and every unit stat. Digits advance six native
pixels, preserving the stat column's right edge. Stat values align vertically
with their labels; their bars are centered alongside the compact text.
`Sortie`, `1`, `2`, `3`, and `Bench` use the same compact cell. The pilot name
retains its 19x24 cell. Native selection, rank checks, data, panels, colors,
transparency, portraits and unit icons are preserved.

The helper still occupies exactly `0x800C6220..0x800C6700`; size-neutral
instruction changes leave the normal briefing typography at `0x800C6700`
untouched. The only earlier changes are the number-wrapper target, two
numeric baseline constants and assignment bar coordinates. No new memory or
GPU allocation is needed. Physical console testing remains outstanding.

Fresh-disc captures and text-call traces cover four forms (24 stat pairs),
Lady Command (six stat pairs), five column headings, level/EXP, skill, native
confirmation/continue and exit to briefing. Labels and values use identical
font flags and top edges; digit advances retain their original right anchors.
Reports and 4:3 screenshots: `work/ui/menu_layout/v0822/`.

## Original layout work

These changes retain the original panel colors, semitransparency, text palettes
and button icons. The work changes lettering, spacing and icon size.

The assignment page uses the existing 512×480 framebuffer. Text opts into the
19×24 and 13×16 cells introduced in 0.8.2, correcting its proportions on a 4:3
display. The pilot name has a separate row from level, experience and skill.
Unit names use two lines when needed. Unit icons use 24×30 native pixels so
they appear square, and the six stat rows have consistent spacing. The native
assignment grid, pilot portraits, selection, comparisons, rank checks, undo,
confirmation and assignment calculations remain in use.

`tools/menu_layout.py` redirects only the three assignment text/number wrappers
at `0x800B903C`, `0x800B9074` and `0x800B90AC`. The helpers occupy
`0x800C6220..0x800C66A4`, after episode-preview captions and below the flight
overlay at `0x800C67A8`. The build rejects any overlap. Native FONT8's internal
Lv/Exp glyph codes are replaced with equivalent English labels; numeric values
still come from the same native fields. Existing panel palette and blend/style
tables are retained byte-for-byte.

Flight Stage/Controls text uses 19×24 cells; the longer unavailable-test notice
uses 13×16 cells. Label and value columns align within the existing panels.
Thirty-two original font-flag instructions and 26 coordinate constants,
including their animation targets, are audited before replacement. The
320×240 flight renderer is unchanged. The
voice-caption draw routine uses the same corrected font in 480-line menus and
centers each line using its actual width. Caption text, timing, audio and
flight-view placement remain unchanged.

The status pages retain 0.8.2's geometry while restoring native palette values:
blue `(94,96,207)`, pilot green `(88,200,128)`, weapon red `(255,80,120)` and
footer blue `(47,48,103)`. Panel fills use the native half-blend mode. Borders
are separate thin strips, so fills blend once with the original green grid.
The preview panel stays behind the model at the native background ordering
depth; it does not tint the model's textures.
HP maxima are red, energy maxima blue, and the four unit stats retain amber,
green, yellow and blue. Native text gradient palettes are reused.

No extra framebuffer, texture allocation, model assets or audio reads are
introduced. Assignment helpers remain below the next loaded overlay; caption
code stays below `0x800F0000`. Added drawing work and physical-drive timing have
not been tested on a real console. Emulator checks are representative rather
than an all-pilot/all-unit playthrough.

`tools/sortie_capture.py` navigates a fresh muted project emulator to its
briefing. `tools/menu_capture.py` captures native frames and can reload audited
drawing edits. `tools/minigame_capture.py --menu` seeds a standalone debug user
record and default controller mapping because this entry bypasses the title's
setup. These debug settings exist only in emulator RAM; they do not enter the
patch or a save. All tools default to a dry run. Native-resolution captures and
4:3 display exports are under `work/ui/menu_layout/`.

## Validation

Fresh-disc assignment captures cover four forms, a single unit, pilot details,
the native confirmation window and return to the briefing. The final status
layer-order correction was checked with a native drawing reload: all three
pages, original translucent palettes, an untinted model, and page/weapon/exit
controls. The final packed renderer matches those checked drawing bytes.

A fresh boot of the finished image covers Stage, Controls, the normal/inverted
toggle and quit/cancel. A RAM-only index-4 fixture verifies that Stratosphere
fits; the original index is restored. Native caption checks cover one- and
two-line clips, correct centering/font flags, unknown-voice filtering and
disabled voices. All 79 menu caption lines fit, with a maximum width of 465
pixels against a 488-pixel limit. Unit names fit two 78-pixel rows; all seven
group/rank headers fit their 226-pixel allowance.

Label accuracy was checked against the original Lv/Exp fields, followed by an
editorial pass retaining existing terms and a rendered proofreading pass. No
dialogue, caption wording or translation rows changed.

The final image matches generated code, keeps the EXE byte-identical to 0.8.2,
and changes only game.bin, briefing.bin and flight.bin content within GR.VFS.
The other 392 VFS files and all movie/audio sectors are preserved. Loading
limits pass. The 0.8.2 archive restores to its recorded hash, and ten archives
are retained. Reports: `v083-validation.json` and `v083-native-summary.json`
under `work/ui/menu_layout/`.

Version 0.8.7 enlarges the underlying Latin glyph artwork. Compact text switches
from 13x16 to 11x13 cells with matching advance tables, keeping its visible size
near 0.8.6 while primary text grows. See VWF.md and work/ui/font/v087/.
