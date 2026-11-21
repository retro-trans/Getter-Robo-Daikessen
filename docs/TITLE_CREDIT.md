# Title-screen build version and translation credit

Build 0.8.14 adds `v0.8.14` above `github.com / retro-trans`, right aligned
at native x=500 on the 512x480 title screen. Text origins are (464,438) and
(370,454). The two lines use the existing compact proportional font, with
the game's white/gray shading and black shadow. There is no background box.
The original menu, logo and copyright textures remain intact.

`tools/title_credit.py` generates the version line from the supplied build
version. `tools/build.py` calls it for the title overlay on every build.
Running the tool without `--apply` reports the generated geometry without
writing files. It also supports regenerating an already patched overlay.

## Implementation and hardware boundary

- Title overlay base: 0x8008B7A8. Original length: 31,508 bytes.
- Redirect the native draw callback at 0x8008B7BC from 0x8008CD20 to
  0x800932C0. The original callback runs first, with its return values and
  callee-saved registers preserved by the wrapper.
- Append 240 bytes of R3000 code/ASCII strings, with four bytes of alignment
  padding. New overlay length: 31,752 bytes; end: 0x800933B0, below the next
  overlay boundary at 0x800A97A8. No resident font/kernel code is changed.
- Draw only while the title callback's background/menu flags are active.
  Use native string renderer 0x8004DDFC, flags 0x3400000E, and native
  full-screen draw environment 0x8003BBDC for ordering-table bucket 14.
  No new texture, heap allocation, emulator-only opcode or host overlay.
- GR.VFS grows by 512 bytes but fits its existing ISO sector allocation.
  Disc file extents and total BIN length are unchanged. Updated sectors
  receive normal Mode 2 Form 1 EDC/ECC and directory sizes.
- Real hardware has not been tested. Extra title draw primitives and the
  slightly larger overlay remain a timing/loading risk pending a console
  test; cold boot and menu behavior are checked in the project emulator.

## Validation

`tools/title_credit_check.py --apply` expects a fresh boot of the local build
in the muted project emulator. It checks that the wrapper was loaded from
disc, records the two native string calls, checks Up/Down menu navigation
and the Start-to-name-entry transition, and captures the title screen.

The screenshot procedure temporarily extends the native attract-demo idle
timer in RAM so the slow framebuffer read cannot change screens mid-capture.
It restores the timer afterward. This fixture is absent from the disc patch.

Evidence: `work/ui/title/v0814/native/`; binary comparison and previous-build
archive round-trip: `work/ui/title/v0814/build.json`. Only the newest full
BIN/CUE is retained, together with ten previous xdelta archives.

## Composition with difficulty (0.8.18)

The title now appends `tools/difficulty.py` after the credit wrapper. The
outer update/draw callbacks start at `0x80093400`; its draw routine calls
the unchanged credit wrapper at `0x800932C0`, which still calls the original
title renderer. Generate credits from the original UI-patched overlay first,
then append difficulty; do not pass the combined overlay back into the
credit-only regeneration tool. The title version remains generated per build.
For this combined title use `tools/difficulty_title_check.py` and the checks
documented in [DIFFICULTY.md](DIFFICULTY.md); the original 0.8.14 credit-only
checker expects the older callback layout and immediate Start transition.

## Raised credit block (0.8.20)

Moved both rows up 24 native pixels: version (464,414), credit (370,430),
with the same font, right alignment, transparent background and 16-pixel
row spacing. The credit's 13-pixel cell ends at y=443, leaving 37 rows below
it on the 512x480 title screen. This keeps the full line inside a preview
that crops the bottom 24 rows, addressing the reported bottom-edge clipping.
Only the credit wrapper's position arguments and version string change;
the wrapper size, callbacks, difficulty selector and original art are intact.
Native capture/layout evidence is under `work/ui/title/v0820/`.
