# In-game debug tools (DuckStation + GDB)

Method: `debug_tools_guide.md`. All tools talk to the project's DuckStation
(`work/emulator/duckstation`, portable, audio muted, `[Debug] GDBServerPort = 2351`,
env `GR_GDB_PORT`). `tools/emu.ps1` starts / stops only this copy (matched by path).

| Tool | What it does |
| --- | --- |
| `tools/emu.ps1 start <cue> [-StateFile s]` / `stop` / `keys "Return F1"` / `shot x.png` | emulator control; keys need the window (movies, savestate hotkeys F1 save / F3 load) |
| `tools/gdbdbg.py run "press circle 4; wait 60; shot x.png"` | virtual pad + VRAM screenshots, no window focus needed; also `vram x.png`, `until <addr> [frames]`, `dump r<reg>\|<addr> <len> <file>` |
| `tools/step.sh <name> "<script>"` | run a gdbdbg script and save `work/ui/shots/<name>.png` |
| `tools/gdbhits.py <stops> <addr>...` | count breakpoint hits (+ ra, a0, a1, v0 of the first hit) |
| `tools/gdbstr.py [n] [addr]` | log string-drawer calls (caller, x, y, string) to `work/source/scan/strcalls.txt` |
| `tools/gdbmem.py read/dumpram/regs` | memory access; `dumpram` = 2 MiB main RAM |
| `tools/gdbreset.py` | clear stale breakpoints and resume |
| `tools/gdbuntil.py "<text>" [button] [max] [frames]` | press a button until the game draws a string containing the text (skip dialogue to a prompt) |
| `tools/gdbprog.py <id> [param]` | make the next program switch run program <id> (dispatcher 0x8004CF48: 9 flight minigame, 10 game flow / chapter; 2 = debug menu crashes on retail hardware) |
| `tools/gdbweaken.py` | set every enemy unit's HP to 1 (unit table 0x800FF800, 0x80 per record) |
| `tools/smoke.py <cue> <first> <last> [outdir]` | chapter smoke test: program 10 / N, through the briefing and story to the map prompt; logs every drawn string, flags kana/kanji, screenshot + crash context per chapter (`work/ui/smoke/summary.txt`). Valid chapters: 2-25 |
| `tools/gdbwatch.py <addr>` / `tools/gdbwatchpress.py <addr> [presses] [frames] [button]` | write watchpoint on a word (with button presses); stops when text is written |
| `tools/loadlimits.py` | fixed-size file loads (0x8003A6FC with a constant max size) vs built file sizes; run by build.py |
| `tools/movie_preview.py C04 [--apply]` | dry-run/native movie selection at next dispatcher: program 7, CG1/CG2 indices 1/2, C01–C16 indices 10–25; use fresh boot and keep audio muted |
| `tools/movie_capture.py C04 --out work/ui/movies/v014/C04 --ticks 120 [--apply]` | fresh-boot native launcher selection and both 24-bit movie framebuffers, captured at the movie main-loop display point (works with the window hidden) |
| `tools/hotpatch.py <old GR.VFS> <old exe> [overlay]` | after a rebuild, write only the bytes that changed (overlay at its base, exe, kernel string pools) into the running game: keep copies of `work/build/` from before the build |

## Addresses (SLPS_022.32)

| addr | meaning |
| --- | --- |
| 0x80029E18 | pad read (BIOS InitPad buffers 0x800853AA / 0x800853CE); after `nor v1,zero,v0` at 0x80029ECC v1 = pressed bits. **Input hook: 0x80029ED0, OR bits into v1, port 1 when a1 == sp.** Runs once per frame while the game runs (also during movies) |
| 0x8001BC60 / 0x8001BC00 | StoreImage / LoadImage (libgpu, found by name string) |
| 0x8001B954 | DrawSync (not called while a movie plays: use it to detect "game is rendering") |
| 0x80082AC8 | overlay base pointer (0x8008B7A8) |
| 0x8008B7A8 | overlay slot: title / game / briefing (?) / flight / debug |
| 0x800A97A8 | battle.bin; 0x800F87A8 mapNN.bin |
| 0x8003909C | unpacker (dst, src, size, mode) |
| 0x8005B43C / 0x8005B7F4 / 0x8005BB80 | message copy / typewriter / draw (window struct in a0/s3: +0x10 x, +0x12 y, +0x14 w, +0x16 h, +0x18 columns, +0x1A lines, +0x24 column, +0x26 line, +0x3C portrait width, +0x68 text buffer, +0x368 line buffer) |
| 0x80070114 | map event (MFORM) bytecode interpreter, handler table 0x800829D0, lengths 0x80082990 |
| 0x8000D000-0x8000DC20 | screenshot scratch (gdbdbg) |
| 0x8000F000-0x80010000 | VWF code + tables (do not use as scratch) |

Screenshots: `gdbdbg.py shot` grabs both 320x240 framebuffers (y 0 and 240); the title
screen is high resolution and shows black there: use `tools/emu.ps1 shot` (window) for it.

## Savestates (`work/emulator/states/`)

| file | build | place |
| --- | --- | --- |
| `jp_map01_turn1.sav` | original | map 1, turn 1, player phase (after the opening scene) |
| `v001_map01_prescene.sav` | 0.0.1 VWF test | black screen before the map 1 opening scene (press Circle) |
| `v010_map01_prescene.sav` | 0.1.0 | same place, translated script (male player, name entered in kana) |

Savestates made with an older build keep the old exe and data in RAM: boot the new image
(or use hot reload, to do).

## Not done yet

Hot reload (step 6: replacing the MFORM buffer found by content did not change the scene, the live copy is elsewhere) and scene preview (step 7) of the guide; coverage check (step 8).

## Crash diagnosis

A crash ends in the BIOS lock-up A(40h) (pc 0xA0, ra 0x1B10). The faulting context is in
the current TCB: [0x80000108] -> PCB, [PCB] -> TCB, regs r0-r31 at TCB+0x08, EPC at +0x88,
cause at +0x98 (see the session notes in CHANGELOG 0.1.1: heap allocator 0x8002DE20, heap
table 0x8007E3F0, blocks carry a tag such as ./WINDOW.C after a 0x20-byte header).
The emulator must run as a single instance: two DuckStation processes share the GDB port.
