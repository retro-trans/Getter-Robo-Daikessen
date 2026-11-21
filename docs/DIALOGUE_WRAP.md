# Story dialogue wrapping — 0.8.11

Story text previously retained line breaks calculated before the main Latin
font was enlarged. The native renderer then broke overwide lines inside words.
The reported example is MF02_047D in MFORM02.BIN.

`tools/wrap.py` now provides `reflow`, which recalculates soft line breaks from
the current proportional width table. `tools/build.py` uses it for every story
string at build time. Existing `wrap` behavior for other text is retained.
`tools/rewrap_dialogue.py` previews and applies the same layout to the working
story file and its Japanese-free English copy. It defaults to a dry run.

The limit is the native 210-pixel portrait text area. A runtime player name
reserves six 12-pixel full-width cells. Formatting-only invariants preserve
words, row boundaries and the exact non-line-break control sequence. Explicit
pages, pauses, portrait changes and embedded speaker changes are retained.
Blank lines and centered-caption placement remain structural. No font size,
message window size or text speed changes are needed.

The audit covers 959 entries; 568 change, with no final line over 210 pixels.
Only the 24 story PAC containers change. Their original bytecode and headers
remain byte-identical except for relocated string-pointer words. Script text
uses the existing relocation/packing path, normal VFS loading and existing
loading limits; no executable, heap, framebuffer or VRAM patch is introduced.
Physical-console timing is untested. Build/audit/capture files are under
work/ui/dialogue/v0811/.
