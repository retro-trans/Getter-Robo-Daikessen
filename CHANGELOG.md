# Changelog

## 0.8.0

First public release (same content as 0.1.8, plus one fix).
- Lando's Episode 19 line still named the fortress "Jaga Castle" (the 0.1.6 rename
  missed it because the name wrapped across a line break); it now reads "Vega Zone".
- Release packaging: VCDIFF patch for the original disc image (SLPS-02232), checksums,
  build manifest and instructions. GitHub social preview made with
  `tools/social_preview.py`.

## 0.1.8

- Flight minigame subtitles moved to the bottom of the screen (rows 214/226 instead
  of 84/96); one-line captions use the lowest row. Menu-screen captions unchanged.
  Checked in the practice flow: the two-line radar line and the one-line Square
  line (`work/ui/minigame/v018-bottom/`). Code grew by 16 bytes, still inside the
  audited overlay extension.

## 0.1.7

- Added 70 transparent subtitle cues for all 32 flight-minigame instruction and
  coaching clips: screen explanation, time limit, machine status, radar rules,
  controls, combination timing, success/failure feedback and later drills.
- Captions follow the original voice playback position. Their layout adapts
  to the flight view and taller menus, leaving the flight HUD clear.
- Recovered a short congratulatory line missed by the first recognition pass.
  Accuracy, editorial and proofreading reports are included for the new text.
- Original speech, gameplay, controls and tutorial timing are retained. The
  native draw hook and bounded overlay extension are documented in
  `docs/MINIGAME_SUBTITLES.md`; real-console testing remains outstanding.
- Previous movie/episode-preview subtitles and UI fixes are preserved. Archived
  0.1.6 as xdelta; 0.1.7 is the latest full testing image.
- Verified all 32 native voice IDs and caption text, menu scaling, unknown-voice
  filtering and unavailable-voice handling. In-order tutorial captures confirm
  the time-limit, radar, Square and X instructions during actual practice.
- All 70 cues pass fit/timing checks. Original XA speech remains byte-identical,
  all 18 final-disc movie streams pass verification, and the 0.1.6 archive
  decodes to its recorded image hash.

## 0.1.6

- Fixed the name-confirmation Yes/No selection backgrounds: the rectangles now
  align with the narrow English labels. Both selections were checked in-game.
- Added 168 transparent English subtitle cues to all 23 voiced next-episode
  preview variants, including the branching episodes. These native slideshows
  use separate XA narration and were outside the earlier STR movie pass.
- Subtitles follow the native audio-sector position and use the existing font
  and shadow. Original narration, music sequences and slideshow timing remain
  unchanged; the transparent STR subtitles from 0.1.5 are retained.
- A track-ownership check prevents stale captions when voices are disabled.
- Corrected the previously guessed fortress name "Jaga Castle" to "Vega Zone"
  using its spoken name and corroborating game-guide evidence. Updated the
  active glossary, UI/data text, review exports and episode 19 title graphics.
- Added preview extraction, validation and muted native-capture tools, plus
  accuracy, editorial and proofreading reports. Hardware boundaries and the
  remaining real-console/human-listening checks are documented in
  `docs/EPISODE_PREVIEWS.md` and the review reports.
- Checked native PAC allocation limits, subtitle bounds and final-disc data;
  the full raw XA archive and all 23 music sequences remain byte-identical.
  All 18 final-disc STR streams pass the content/audio/layout/checksum checks.
- All 23 native preview assets load with the correct voice IDs and visible
  captions. The final guard also passes disabled-voice and late final-episode
  checks; native preview cleanup returns and the game continues afterward.
- Archived 0.1.5 as xdelta; the old 0.1.4 image lock has cleared and its redundant
  full image was removed by normal archive cleanup. Only 0.1.6 remains as BIN/CUE.

## 0.1.5

Movie subtitle presentation
- Removed the solid subtitle background across dialogue and both songs. The
  original video remains visible behind white text with a one-pixel black outline.
- The ending's credit layout still reserves space for lyrics, using the credit
  roll's natural black background instead of a separate gray subtitle panel.
- Subtitle wording, cue times, original audio and movie sector placement are
  unchanged. Render style is now included in asset fingerprints so an older
  subtitle appearance cannot silently be reused by the builder.
- All 17,309 edited movie frames independently decode, all 212 outlined text
  bounds fit the screen, and all 18 final-disc streams pass content/audio/layout
  checks plus 90 sector checksum samples.
- A muted native DuckStation capture of C04 confirms that the original picture
  is visible behind the outlined subtitle, with no backing bar.
- The 0.1.4 xdelta archive was created and its full decoded image hash matches
  the recorded build hash. Its full BIN/CUE is temporarily retained because the
  user's separate emulator still holds the old image open; remove those two old
  files after that emulator closes (the next build's normal archive cleanup does so).

## 0.1.4

Movies
- Examined all 18 movie streams. Added 212 timed English subtitle cues for spoken
  scenes and both theme songs, translated the three Getter Zan pilot name captions,
  rebuilt the 322-row credit roll in English, and translated the final end card.
  Original Japanese audio and the stylized title logo are retained. C03, C13 and CG1
  have only effects/nonlexical voices and stay byte-identical.
- Accuracy, editorial and proofreading reports are in `work/translation/en/review/`.
  These use assisted transcripts and original scene images; a human listening pass
  remains outstanding for several explicitly flagged phrases and staff name readings.
- Incorporated the 0.1.3 UI fixes. The UI-only predecessor archive was reconstructed
  by restoring every original movie sector and its xdelta round trip was checked.

Tools and hardware boundaries
- `tools/movie.py`: inventory, local transcription, measured two-line subtitles,
  frame-based name captions, credits, jPSXdec replacement, English SRT exports and
  independent decoding of every patched frame. Full workflow: `docs/MOVIES.md`.
- The build includes only assets with current translation and verification hashes;
  movies stay at their original LBAs and every XA audio sector remains identical.
  Changed sectors receive regenerated EDC/ECC. CG2 keeps its native ~29.97 fps
  schedule; other movie streams use ~14.985 fps.
- Native player limits checked: original frame-sector slots, 0x10000-byte compressed
  ring and 0x28000-byte RLE buffers. No movie-player code or memory allocation changes.
  Real-console playback remains untested; quantization/VLC workload changes are
  documented as a hardware verification item.
- `tools/movie_preview.py`: select any real movie through native program 7 at the
  next dispatcher call, using only emulator RAM. Emulator startup now enforces mute.
- `tools/movie_capture.py`: safe 24-bit movie framebuffer captures from the native
  movie main loop, including when the emulator window is hidden.

Validation
- All 17,309 frames of the 15 edited streams independently decode without errors;
  original frame counts and every audio sector are preserved. All 18 streams were
  checked in the final disc image, with 90 sector checksum samples passing.
- Muted project DuckStation: native frame captures verify dialogue in C04, the
  29.97 fps CG2 scene, English credits with song subtitles in C16, and the moving
  pilot name caption in C05. These are representative playback checks, not a
  claim of a full game or real-console playthrough.

## 0.1.3

Fixes (reported in game)
- Map action menu: "Move" sat further left than "Wait". Items of list / hex menus were
  placed with the display length rounded up to 12 px cells (Move 25 px -> 36); they now use
  the pixel width (new VWF routine `strpx`, hook H at 0x800580D0 / 0x80058280), so the
  left column ends against its hexes and the highlight box fits the text.
- Unit status, weapon page: "HP" and "Getter Ray" stood lower than their numbers. The
  label is drawn at the digits' y; kanji fill the cell but English capitals end 3 lines
  lower on this 512x480 screen. Label moved up 3 lines (overlay patch, game 0x80098474;
  new `OVERLAY_PATCHES` table in `tools/vwf.py`, applied and checked by the build).
- The tall text on that screen is the original look (glyphs drawn 2x tall in 480-line
  mode; the Japanese is stretched the same way).

## 0.1.2

Translation
- Six chapter titles in the briefing header (Episodes 1, 4, 9, 11, 19, 21) and the branch
  header "Choose Destination" (3 copies) were still Japanese: each follows a pointer word
  directly, so the text scanner skipped them. `tools/briefing.py` now also reads the
  targets of title / choice slots (pointer followed by 2). Briefing rows: 99 -> 108.
- Debug overlay strings (37 rows) translated.
- Battle plates 1GOUKI/2GOUKI/3GOUKI read UNIT 1/2/3.

Verified in game (`tools/smoke.py`, every chapter from its briefing to its map)
- Chapters 2-25 load, play their story and reach the map with no crash. 14 stops at the
  sortie screen and 21 starts in attack targeting (the script does not handle either);
  both screens are English. Parameters 26-30 are not chapters (the original disc hangs
  on them in the same way).
- After the fix, no kana or kanji is drawn in any chapter except movie audio (voiced FMVs,
  no subtitles) and the credits roll burned into C16.STR (MDEC video, not re-encoded).

Tools
- `tools/smoke.py`: chapter smoke test (switches program 10 at the dispatcher, logs every
  drawn string, screenshot of the map, crash context).
- `tools/datatext.py extract` keeps the rows of sources it no longer extracts (HT, read by
  `tools/battletext.py`).

## 0.1.1

Translation
- Story scripts: accuracy, editorial and proofreading passes merged (reports in
  `work/translation/en/review/`).
- UI: all 933 rows of the exe and overlays translated, then reviewed in three passes (31
  edits: episode titles aligned with the cards, Large/Small weapon names, `?!`, ...).
  Single-character labels (Male/Female, terrain names, ranks) and strings that follow a
  pointer table (行動選択 "Choose action", Texas Mack, Empty, Black Getter prompt) added.
- Chapter briefings (99 rows) and unit / pilot names (429 rows) translated and reviewed in
  three passes. Names: 大型 Large, 小型 Small, 突進 Charge, 電撃 Electric Shock, Linda Tiramis
  (wiki spelling), ギィムバグ軍曹 P.O. Gimbug, ラセツ男爵 Baron Rasetsu.
- Battle dialogue: all 114 unit battle files (prog00/*.pac, `<UNIT>.BIN` inside TMV.PAC) —
  408 unique lines: attack calls, hit / defeat lines and taunts of every pilot, including the
  one-kanji name labels (Go, Sho, Gai, Akane, Tsubaki, Kaede). Translated in 4 slices and
  reviewed in three passes (`tools/battletext.py`, `docs/TRANSLATING_BATTLE.md`). 0.1.0 only
  covered one of these files (HT15V).
- Graphics (`tools/gfx_cards.py`, `tools/gfx_sprites.py`, packed by `tools/gfx.py`): 28
  chapter title cards, Game Over, 23 "Next episode" previews, flight minigame titles, HUD
  messages, result plates, stamps and reports, seat icons (Empty / N/A), title-screen
  copyright, promo screens. Logo kept. Movies have no subtitles (out of scope).
- Not translated, on purpose: `mapef/m_formNN.pac` (older scripts no code loads) and the three
  test lines of `MFormDb.pac` (no script command refers to them).

Fixes found in game
- Crash entering Episode 2 (BIOS "unresolved exception" after the title card): briefing.bin
  reads MAPSYS/BRIEFING.PAC into a fixed 0x1E000-byte buffer; the translated pack was
  125,079 bytes and overran the heap. BRIEFING.BIN now reuses the slots of moved strings,
  shares duplicated branch text and every entry of the pack is re-packed with an
  optimal-parse LZ (117,391 bytes). The build checks every fixed-size load
  (`tools/loadlimits.py`) and fails if a file is too big.
- Crash on map 2 after long dialogue pages: the message window struct (WINDOW.C, 0x3E8
  bytes) keeps the current page in a 128-byte line buffer at +0x368; English pages reach
  178 bytes and ran into the next heap block header. The window allocation is now 0x4E8
  bytes (exe 0x8005A88C). Hardware note: 5 windows x 256 bytes more heap; the original game
  already used part of the slack (Japanese pages up to 132 bytes).
- Briefing header showed a literal "
" in long chapter titles: titles are no longer
  word-wrapped; Episode 2's header title is shortened to fit one line (~280 px).
- Ability screen showed a stray "ht?": the game draws a computed pointer (0x8008BC60, the
  padding after the "Counter" description) as an empty line; that row is now capped.
- Long ability line showed a literal `
`: title.bin lines are drawn by the plain string
  drawer, never word-wrapped now.
- "Nice name" scene cut lines: title.bin types those lines with fixed character budgets
  (15/15/22, 29); the English fits them and the build checks it (`MAX_CHARS`).
- Targeting box showed Japanese story text: terrain names are a 5-byte record table
  (0x8008B7F0 + index*5) and must stay in place (4 bytes each); range shapes likewise.
- Unit menu showed "St.": the menu points 2 bytes into "SF状態"; the row is "SFStatus".
- Map prompt 行動選択 was missing from the tables (string after a long pointer table).
- Format strings split by codes were missing: 第%ld話%s (episode box, now "Episode %ld"),
  「%s」 (episode title, briefing), %d～%d, and the battle-line format $f%sa %s「%s」 (now
  "%s: %s", like story dialogue).
- Kanji-heavy strings rejected by the text-run detector were missing: map search help
  (Find Enemy/Ally), invincibility toggles, unknown-enemy name, briefing locations, three
  attack calls, Mary's "Oh! Great!", the enemy soldier labels (Reptilian / Hyakki / Lando /
  Rasetsu Soldier A/B) and two cries. UI and battle extraction now also take every pointer /
  code target that holds a Shift-JIS string.
- Battle HUD "ダメージ" (prog00/effect.pac DAMAGE.TIM) is now "DAMAGE".
- Battle lines are word-wrapped for the message window (first line leaves room for the
  pilot's name).

Tools
- `tools/ui_text.py`: strings that move out free their old slot; later moved strings of the
  same image reuse those slots before the kernel-RAM pools (pools were full).
- `tools/refscan.py`: string starts inside another string are dropped; prefixes with
  `$f%02da`, `%d`, `%ld` recognised; text after a long non-zero run is no longer skipped.
- `tools/battletext.py`: battle dialogue extract / slices / check / apply / build. Longer lines
  go into free space of the same file first; the rest is appended (~0.9 KB per file). The
  battle loader allocates entries on the heap by their header size (0x8002DE20).
- `tools/vcdiff.py`: VCDIFF (xdelta3 format) encoder/decoder; older builds are archived as
  `work/output/patches/*.xdelta` against the original disc (10 kept).
- `tools/hotpatch.py`: write changed overlay/exe/pool bytes into the running game.
- `tools/build.py` writes `work/build/` before the disc image (works while the emulator
  holds the .bin open).

Build
- `GetterRoboDaikessen_EN_v0.1.1.bin/.cue`. Tested in DuckStation: boot, title, name entry,
  gender / ability select, opening scenes, Episode 1 title card, map 1 menus, targeting,
  terrain box, unit / pilot / weapon status screens, roster, minimap.
- Battle verified in game (map 1, BT-23 vs. a Dinosaur Empire unit): attack call, pilot and
  enemy lines in the message window, HUD.

## 0.1.0

Analysis and tooling
- Disc / archive: GR.VFS reader + builder (`tools/vfs.py`; data area at 0x4000, offsets
  sector*0x800 + flags*0x100), PAC containers (`tools/pac.py`), the game's LZ codec
  (`tools/grlz.py`, compressor round-trip tested), disc patcher (`tools/build_disc.py`).
- Map event scripts (MFORMnn.BIN): bytecode parser, string extraction, string relocation
  (`tools/mform.py`, `tools/extract_text.py`), 959 rows.
- Debug kit: project DuckStation (GDB port 2351, muted), virtual pad + VRAM screenshots
  (`tools/gdbdbg.py`, pad hook 0x80029ED0), hit counter / string-call logger
  (`tools/gdbhits.py`, `tools/gdbstr.py`).

VWF
- Hand-drawn proportional Latin font (`tools/fonts/gr_latin.txt`) in the game's style
  (row gradient + drop shadow), drawn into FONT12_0 cells; ASCII table remapped (fixes the
  original `x` -> `p` bug); hooks for the string drawer, the dialogue draw loop, the
  typewriter column counter (pixels), window width, string length and the 12 px number
  printer (`tools/vwf.py`, docs/VWF.md). Word wrap to the 210 px dialogue window
  (`tools/wrap.py`).

Glossary and translation setup
- `work/glossary/glossary.json`: 163 sourced entries (Getter Robo wiki, ja.wikipedia);
  `work/glossary/speakers.json`: name tags for all 51 speakers.
- Translator brief `docs/TRANSLATING.md`, slicer (`tools/slices.py`, 12 slices of 80 rows),
  checker (`tools/check_slice.py`). UI strings extracted (`work/translation/en/ui.json`,
  648 rows; exe fixed fields translated in place, referenced strings relocatable).

Translation
- Story scripts (all 21 maps + branches, 959 rows) translated: 12 agent slices, all pass
  `tools/check_slice.py`; merged with speaker tags from the glossary, word-wrapped to
  210 px, centred banners/captions, restored speaker breaks (`tools/slices.py apply`).
- Not yet reviewed (accuracy / editorial / proofreading passes pending).
- Not translated yet: UI (exe/overlays), chapter briefings (BRIEFING.BIN), unit/pilot
  data (MCN_PRM2/PIL_PRM), battle shouts, graphics, movies.

Build
- `GetterRoboDaikessen_EN_v0.1.0.bin/.cue`: exe and GR.VFS moved to the end of the image.
  Tested from power-on (SCPH-1001) to the first story scene of map 1.
