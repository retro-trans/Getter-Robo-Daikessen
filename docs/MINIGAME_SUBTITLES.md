# Minigame subtitles — 0.8.16

Flight training's instructions and coaching use separate native XA voice clips.
They are not part of the STR movies or the next-episode preview slideshow.
`work/translation/en/minigame.en.json` contains 75 timed English cues for all
34 voice IDs called by flight.bin, including its branch-selected coaching lines.
Audio and assisted transcripts stay in ignored `work/source/minigame_analysis/`.

## Display and timing

The original empty draw callback at 0x800C7A54 now jumps to a native subtitle
routine. It checks the game's voice playback status, finds the currently
selected voice in a 34-entry whitelist, and compares original XA-sector position
with the cue intervals (150 sectors/second). Other voices are ignored, and no
caption is drawn when the native voice backend is unavailable. Speech, input,
simulation timing, tutorial progression and voice selection are unchanged.

The existing proportional font and shadow draw directly over the picture.
There is no background rectangle. Text uses native ordering bucket 15, the
final bucket in the game's forward-linked primary table. Captions therefore
draw over the HUD and menu panels. Native draw-area and draw-offset packets
reset HUD-local clipping/origins before caption glyphs. Text is at most 292 pixels wide. The current
native video mode at 0x80089AA4 selects dimensions from the game's existing
mode table at 0x800111A8:

- Flight view (320x240): text rows 190 and 204 (0.8.4); a one-line cue uses
  row 204. This raises captions from the earlier 214/226 placement so they stay
  above the bottom edge. The user explicitly accepts occasional HUD overlap.
- 480-line menus: center text to the actual viewport width, use rows 350 and
  376, and the 19×24 font proportions introduced in 0.8.3. These rows sit below the central
  notice panel and above the confirmation-button prompt.

## Hardware boundaries

The original flight overlay is at 0x800C67A8–0x800E8B53. New code and English
cue data occupy 0x800E8B60–0x800E9F07 (5032 bytes, including alignment).
The build rejects any extension reaching 0x800F0000, below the next map-overlay
slot at 0x800F87A8. The added range has no original literal data references.
All data is in the loaded overlay; no extra heap or movie-buffer allocation is
required. The callback preserves its callee-saved registers and uses the
native font renderer. The original voice archive remains at its original LBA
with identical raw sectors. No emulator-only feature is part of the patch.
Foreground clipping/origin resets consume 24 additional native primitive-pool
bytes only on frames with an active subtitle. Silence follows the old return
path without allocating these packets.

Real-console testing remains outstanding, particularly rendering-pool headroom
on busy flight scenes and CD timing on a physical drive. Native emulator checks
and fixed memory/line bounds are recorded under `work/ui/minigame/`.

## Tools

Use 64-bit Python 3.11. Mutating commands require `--apply`.

```
py -3.11 tools/minigame_subtitles.py prepare [--apply]
py -3.11 tools/minigame_subtitles.py transcribe [--model large-v2] [--apply]
py -3.11 tools/minigame_subtitles.py translate [--apply]
py -3.11 tools/minigame_subtitles.py check
py -3.11 tools/minigame_capture.py --tutorial [--apply]
py -3.11 tools/minigame_check_native.py [--apply]
py -3.11 tools/minigame_tutorial_check.py [--apply]
```

The capture tools use only the muted project emulator. Their standalone user
record and navigation changes exist only in debugger-controlled RAM, never in
the patch or saved game. The native clip checker invokes the original repeat,
prepare and playback routines; it verifies voice IDs, text and menu placement.
Tutorial-order captures are tested separately during the actual practice flow.

Final verification is in `work/ui/minigame/v017-validation/summary.json`.
`v017-native/voices.json` records all 32 checked native voice IDs and text;
`v017-menu-check/menu_a.png` verifies the menu's completed GPU frame. The live
tutorial captures and recorded voice order are in `v017-final-tutorial/`,
including the time limit, two-line radar explanation and Square/X controls.
Earlier navigation and capture experiments are retained as debug history.

Bottom placement (0.1.8) captures: `work/ui/minigame/v018-bottom/` (two-line radar cue
and one-line Square cue during the actual practice flow).

Raised placement (0.8.4): native time-limit, two-line radar, Square and Cross
instruction captures are under `work/ui/minigame/v084/tutorial/`. The renderer
arguments are checked against rows 190/204; all cues remain transparent. The
finished disc differs from 0.8.3 in one raw sector containing the two coordinate
words. Every other sector is byte-identical, and overlay size is unchanged.
The archived 0.8.3 image restores to its recorded hash; ten archives are retained.

Result speech (0.8.5): added V0488 and V053A, which jump into a shared XA call
with branch-selected arguments. The inventory now audits all 25 native selection
calls and the shared jump paths. Both normal and final-drill male evaluations
have captions; the previous 70 cues are unchanged. The briefing label is now
Combination Test, using normal string relocation. Audio is unchanged.

0.8.5 validation: `work/ui/minigame/v085/` contains the 87-line width audit,
unchanged-cue check, native result captures, and final disc/archive hashes.
Only `bin/briefing.bin` and `bin/flight.bin` change inside GR.VFS; all 393 other
VFS files, the EXE, movie streams and XA audio match 0.8.4. The previous image
restores from its xdelta to its recorded SHA-256; ten archives are retained.

`tools/minigame_result_check.py --drill 0|4 --output-dir <path> [--apply]`
creates a successful result notification in debugger RAM and lets the native
female-to-male result sequence select and play both clips. It checks every new
caption through the original font call and captures the certificate framebuffer.
It never changes game files or saves. Use a freshly booted muted project emulator.

Foreground order (0.8.16): all flight and 480-line menu captions use bucket 15.
The engine clears its primary list forward (0x8001BDD4..0x8001BDF4) and submits
the base pointer (0x8003B524..0x8003B52C), so bucket 15 executes last. Native
0x8003BA5C and 0x8003BBDC emit full-viewport clip and correct framebuffer-origin
packets. They are prepended after the text is queued so they execute before
the glyphs. Original artwork, HUD commands and caption positions are retained.

`tools/minigame_foreground_check.py [--apply]` runs in a native tutorial session
prepared by `minigame_capture.py --tutorial`. It replays the original XA clips,
checks one/two-line caption arguments, then walks the completed GPU list to
verify that every caption glyph follows every HUD/world drawing primitive
with a full-screen clip and native buffer origin. Evidence is stored under
`work/ui/minigame/v0816/`. No additional gameplay or saved-game change is used.
