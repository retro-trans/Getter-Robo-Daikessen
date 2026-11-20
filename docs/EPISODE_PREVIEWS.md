# Next-episode preview subtitles

The voiced episode-ending previews are native TIM slideshows with XA narration,
not STR movies. `flight/anno*.pac` contains 23 variants, including the two routes
through episodes 6 and 7. The earlier STR subtitle pass did not cover these.

English text and cue timing: `work/translation/en/episode_previews.en.json`.
Local audio, recognition transcripts and word timing remain in ignored
`work/source/preview_analysis/`. The build adds 168 timed cues.

## Implementation and hardware limits

- `tools/episode_preview.py` reads the native preview table in briefing.bin
  (base 0x800A97A8), including the original XA voice IDs. Slot 5 is unused.
- Each PAC gains a raw `SUBTITLE.BIN` entry with a 16-byte native prefix whose
  dispatch type is 0xFF (ignored by the original loader). The existing TIM and
  SEP entries retain their own loading behavior. English title graphics were
  already present; episode 19's fortress spelling is now Vega Zone.
- Native preview state allocation at 0x800B2678 grows from 0x24 to 0x824 bytes.
  A hook at 0x800B2830 copies at most 0x800 subtitle bytes into that allocated
  object before native PAC unpacking and release. The largest subtitle blob is
  545 bytes. The original destructor frees the same heap object.
- Drawing at 0x800B2980 calls the original native slide renderer, then the native
  proportional string renderer. Text uses the existing font and shadow, at
  y=208/221 with a maximum 292-pixel width. No background rectangle is emitted.
- The clock is the current native XA sector at 0x80089620 minus the selected
  track's first sector (selected record pointer at 0x80089600), at 150 sectors
  per second. It follows actual CD playback rather than a frame countdown.
  The selected record must match this preview's native voice ID before the
  code reads its position; disabled voices cannot reuse an old track's clock.
- New code occupies 0x800C6080–0x800C621B. The overlay ends at 0x800C621C,
  below the next fixed overlay address, 0x800C67A8. This uses ordinary PS1 RAM
  and native heap allocation; no emulator feature is part of the patch.
- Every rebuilt PAC is checked against its original per-preview heap allocation
  table at 0x800C54AC. General file-load bounds are checked by loadlimits.py.
- The entire raw GRXAP.XAP archive remains byte-identical at its original LBA;
  all 23 SEP music sequences are unchanged. Existing STR subtitle assets retain
  their 0.1.5 transparent style and original audio/layout.

Real-console playback has not been tested. The native heap, CD-sector timing,
GPU ordering and overlay boundaries have been checked in the project emulator;
these are the remaining hardware-sensitive parts to confirm on a console.

## Tools

Use 64-bit Python 3.11. Commands default to a dry-run unless they only validate.

```
py -3.11 tools/episode_preview.py prepare [--apply]
py -3.11 tools/episode_preview.py transcribe [--model large-v2] [--apply]
py -3.11 tools/episode_preview.py translate [--apply]
py -3.11 tools/episode_preview.py check
py -3.11 tools/preview_capture.py ANNO02 [--apply]
powershell -File tools/test_previews.ps1 [-Apply]
```

The last two commands only navigate a fresh project emulator for testing. They
do not write the debug navigation changes to the disc. The emulator must be
muted. Native captures and reports are under `work/ui/episode_previews/`.

The 0.1.6 verification report is `work/ui/episode_previews/v016/summary.json`.
All 23 preview assets were exercised with their native voice IDs. The final
track-ownership guard was rechecked on previews 02, 03, 04 and 21, plus the
disabled-voices path. The final episode's last cue was captured at 29 seconds;
its native destructor returned and the game continued for 30 controller frames.
The combined capture sheet is in `v016-final/contact.png`. Earlier failed
debugger-capture attempts were tooling failures and were rerun successfully;
the individual final reports and final summary include all 23 passing assets.

## Confirmation highlight

Name-entry confirmation uses fixed rectangles, separately from the list menus.
The original Yes/No rectangles were x=116/164, width=40. English labels are
drawn at x=124 and x=154 (`/No`, with No beginning near x=160). In 0.1.6 the
rectangles are x=122/158, width=24; their y=123 and height=16 stay unchanged.
Both selections were captured in-game with the 2x Move ability selected.
