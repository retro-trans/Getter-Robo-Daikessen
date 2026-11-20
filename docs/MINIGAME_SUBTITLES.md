# Minigame subtitles — 0.1.8

Flight training's instructions and coaching use separate native XA voice clips.
They are not part of the STR movies or the next-episode preview slideshow.
`work/translation/en/minigame.en.json` contains 70 timed English cues for all
32 voice IDs called by flight.bin, including its branch-selected coaching lines.
Audio and assisted transcripts stay in ignored `work/source/minigame_analysis/`.

## Display and timing

The original empty draw callback at 0x800C7A54 now jumps to a native subtitle
routine. It checks the game's voice playback status, finds the currently
selected voice in a 32-entry whitelist, and compares original XA-sector position
with the cue intervals (150 sectors/second). Other voices are ignored, and no
caption is drawn when the native voice backend is unavailable. Speech, input,
simulation timing, tutorial progression and voice selection are unchanged.

The existing proportional font and shadow draw directly over the picture.
There is no background rectangle. Text uses native ordering depth 4 so the
menu background does not cover it. Text is at most 292 pixels wide. The current
native video mode at 0x80089AA4 selects dimensions from the game's existing
mode table at 0x800111A8:

- Flight view (320x240): text rows 214 and 226 at the bottom of the screen (0.1.8,
  moved from rows 84/96 at the user's request); a one-line cue uses the lower row.
  The upper row passes between the UNIT 3 plate and the radar.
- 480-line menus: center text to the actual viewport width, use rows 350 and
  376, and the native 2x-height font flag. These rows sit below the central
  notice panel and above the confirmation-button prompt.

## Hardware boundaries

The original flight overlay is at 0x800C67A8–0x800E8B53. New code and English
cue data occupy 0x800E8B60–0x800E9C6F (4368 bytes plus alignment padding).
The build rejects any extension reaching 0x800F0000, below the next map-overlay
slot at 0x800F87A8. The added range has no original literal data references.
All data is in the loaded overlay; no extra heap or movie-buffer allocation is
required. The callback preserves its callee-saved registers and uses the
native font renderer. The original voice archive remains at its original LBA
with identical raw sectors. No emulator-only feature is part of the patch.

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
