# Briefing overview typography — 0.8.17

## Episode header alignment — 0.8.23

The green title bar runs from native y=16 to y=30. Episode-title text now
begins at y=19 rather than y=18, vertically centering the visible capital
letters. Its x=34 left alignment, normal 16x10 font, wording, shading and
green panel remain unchanged. This is the shared episode-header draw call,
so the correction applies to every episode, including Episode 2.

Only the y-coordinate immediate at `0x800C3960` changes in briefing.bin.
There is no added code, memory allocation, wrapping change or altered place
label position. The EXE, assignment page and all other overlays apart from
the title version are preserved. Evidence: `work/ui/briefing/v0823/`.

The map overview uses a 512x240 framebuffer (native video mode 3). Displaying
its old 12x12 glyphs at 4:3 made the letters tall. The new reserved 0x22 font
mode draws 16x10 cells with the existing proportional body-advance table.
At 4:3, both cell dimensions scale to the same visual size. Font artwork,
shadowing, palette and the original screen geometry remain unchanged.

The episode header and projected place names opt into this mode through two
local call-site hooks. Only the overview's narration window receives a local
draw callback that selects the new mode; its original update, typewriter,
continuation cursor, input, destruction and chapter flow remain native.

## Full-width narration

The native narration box is (24,164,464,60), with text beginning at (36,170).
Its inner width is 440 pixels. `tools/briefing_layout.py` measures wrapping
with the same 16-pixel advance table used by the game, replacing the generic
210-pixel story-dialogue limit for BRF data only. Line pitch remains 12 pixels,
with 10-pixel glyph cells. Up to four lines fit the existing window.

Quoted names remain together. The five authored branch-choice layouts retain
their explicit breaks and indentation; padded menu/header fields remain intact.
Titles remain on one line and fit the 454-pixel available header span. No words,
punctuation, row identities, script commands or branch pointers are removed.

All 108 BRF rows were checked in the project's review stages: accuracy by exact
word/control preservation, editorial review of line breaks and quoted-name
grouping, then final width/row/format proofreading. There are no substantive
translation edits. Existing English source files remain unchanged; reflow is
applied by `tools/datatext.py` at build time.

## Code and hardware boundaries

The 124-byte local wrapper occupies 0x800C6700–0x800C677B, leaving 44 bytes
before flight.bin's fixed 0x800C67A8 boundary. Sortie helpers are now explicitly
limited to end at 0x800C6700. The preview and sortie code retain their previous
bytes and addresses. Hook sites are 0x800BE060 (window setup), 0x800C3978
(title) and 0x800C4E98 (place labels).

The resident font block grows from 1,332 to 1,464 bytes, ending at 0x8000F5B8,
below the string pool at 0x8000F600. All previous function/table addresses stay
fixed. Two core glyph/advance hooks select appended mode-dispatch code. One
old dialogue-advance branch at 0x8000F1D4 now checks for opted-in body modes;
legacy modes retain their old advances. The hook preserves the live HI/LO
vertical-row calculation and the original window parser registers.

No extra window, heap or VRAM allocation is introduced. The executable remains
483,328 bytes, GR.VFS retains its size, and all disc extents remain unchanged.
MAPSYS/BRIEFING.PAC is 117,299 bytes, below its fixed 122,880-byte load buffer.
Other packed resources in that PAC are preserved. Real-console timing remains
untested; additional per-character dispatch instructions require hardware QA.

## Verification and tools

- `tools/briefing_layout.py [--apply]`: dry-run geometry and all 108 rows;
  `--apply` writes only the audit report.
- `tools/briefing_capture.py [--apply]`: cold-disc navigation to Episode 2,
  two original narration entries, actual character coordinates and 16x10 GPU
  dimensions, screenshots, and transition to the original story font mode.
- `tools/briefing_font_check.py [--apply]`: native CPU probes of six old/new
  glyph modes and 30 body/legacy dialogue-advance cases. Scratch RAM and all
  CPU registers are restored after the probes.

Evidence is under `work/ui/briefing/v0817/`. Native captures confirm every
character uses the measured advance, every line fits the full text box, and
ordinary story dialogue returns to its original mode. The older build's
xdelta archive round trip and fixed file-loading limits also pass.
