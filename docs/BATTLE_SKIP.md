# Battle animation skipping — 0.8.1

Press **Start** during a battle attack animation to skip its remaining visuals.
The map's **Battle: OFF** option remains the choice for suppressing animations
throughout play.

## Native implementation

The battle state update at `0x800ADB24` already checks Start and calls the native
fast-finish routine at `0x800AEA5C`. That routine sets phase 17 and flag 8, then
uses the original actor completion, fade, result transfer and cleanup code.
The input check originally runs only when the parent at `+0x7E8` is -1 (standalone
battles); battles created from the map pass a parent instead.

`tools/vwf.py` replaces the `bne v1,v0,0x800AE038` at `0x800AE00C` with a NOP.
The preceding phase guard (phase <18) and every native result-handling function
remain intact. The builder verifies the original instruction before changing it.
The patch replaces one four-byte instruction in place and adds no code, RAM, assets,
disc reads, controller polling or GPU primitives. Movie and tutorial controls
are unchanged.

Real-console testing remains outstanding. This change uses the original R3000
instruction set and native battle teardown, within the existing loaded overlay.

## Validation

Two native chapter-2 map battles were checked in the muted project emulator:

- Start during phase 2 entered the native phase-17 fast-finish path on the first
  controller poll. The enemy's HP fell from 1740 to 1357, the attacker's HP from
  921 to 621, and the attacker's energy from 55 to 50; the map experience dialogue
  followed. This first run applied the same single instruction to the old build
  in debugger RAM.
- Start after 120 animation frames, during phase 5, also entered phase 17 on the
  first poll, using the already patched instruction. Enemy HP fell from 1357 to
  923, attacker HP from 781 to 511, and energy from 55 to 50. The map experience
  dialogue followed. Native actor-position synchronization returned normally.

The enemy was moved adjacent to the player in debugger RAM to set up these
checks. No such position, unit, stat or save changes are part of the patch.
These are representative native checks, not an all-unit or full-game playthrough.
Reports and captures are under `work/ui/battle_skip/`.

The final disc differs from 0.8.0 in exactly one raw sector: the original
instruction's sector in `GR.VFS`, including regenerated EDC/ECC. The EXE, movie
sectors, original audio and all other VFS content are unchanged. The overlay
keeps its original size (299728 bytes), and the fixed-load checks pass.

`tools/battle_capture.py` navigates a fresh project emulator to a chapter map;
`tools/battle_skip_check.py` checks Start during a selected battle and verifies
native actor synchronization. Both default to dry-run; add `--apply` to operate
the project emulator. The debugger connection disables TCP packet batching to
reduce delays while stepping the controller.

## Bottom-right skip hint — 0.8.19

Active attack animations now display `press START to skip` at (354,226) in
the 512x240 battle view. The normal proportional 16x10 font measures 150
pixels wide, leaving eight pixels on the right and four below the font cell.
The native white/gray ink and shadow have a transparent background.

The position is calculated from the current native display dimensions rather
than assuming the map's narrower 320x240 viewport.

`tools/battle_hint.py` appends a 284-byte drawing wrapper at `0x800F2A80`
and redirects the battle task's draw pointer at `0x800F1D00`. The original
draw callback `0x800AC968` runs first, with return values and callee-saved
registers preserved. Only visible, unpaused attack states (outer state 2,
animation phases 1–16) display the hint. It disappears during initialization,
fast-finish phase 17 and subsequent cleanup.

The hint uses the foremost native ordering bucket, with native full-screen
clip and buffer-origin resets. It adds no background rectangle, texture,
controller handling or changes to damage/results. Start still follows the
previously restored native skip path. The eight-byte gap after the
overlay's data is padded to the next code alignment; the patched overlay ends
at `0x800F2B9C`, below the map overlay boundary `0x800F87A8`. The main EXE and
the Easy/Normal feature remain byte-identical to 0.8.18.

`tools/battle_hint_check.py` defaults to a dry run. In an active battle,
`--apply` checks the loaded code and actual text-renderer arguments, captures
the framebuffer and runs the shipped visibility guards on the emulated CPU.
Its temporary RAM/register fixtures are restored. `--confirm-target` may be
used when a valid enemy target is already selected. Evidence is stored in
`work/ui/battle_skip/v0819/`. Real-console testing remains outstanding.

`--ram-preview` replaces only the drawing wrapper at its first instruction,
before its prologue executes, for rapid iteration after loading a battle.
The unchanged prologue/caller is verified first; this option is a debug-only
fixture and is reported explicitly. `--skip` also checks the native Start,
phase-17 fast-finish, actor synchronization and disappearance of the hint.

Validation passed at native 512x240 resolution: text at (354,226), transparent
16x10 glyphs, 29 CPU visibility cases, Start entering phase 17 on the first
pad read, synchronization of two actors, and no hint during the following
90 frames. An initial cold-boot candidate established the unchanged native
draw path; the final position/font iteration used the recorded RAM-preview
option. The final disc's generated wrapper is byte-identical to the tested
preview. No debug unit positions or refreshed action flags are shipped.
