# Changelog

## 0.8.26

- Published the verified `original → 0.8.26` route in Retro Trans Automatic.
  Fixed shared catalog ingestion of checksummed CUE sidecars and tested the
  existing 0.5.23 Automatic worker against the public patch download. The output
  matches the release target hash and includes a matching CUE; the original
  image is unchanged. Existing game release assets and app version are unchanged.
- Renamed the combination command from `Join` to `Combine`.
- Kept long command labels and their selection backgrounds inside the
  screen's left edge, including the longer `Combine` label.
- Removed the Japanese vehicle suffix `-Gou` from Get Machine names in
  unit data, menus, story dialogue and briefings. Updated the glossary and
  translation slices consistently; the character Go and Getter Robo Go
  retain their names. No event commands, placeholders or voice cues changed.
- Rebuilt from the current translation source, retaining the subtitle,
  battle-skip, Easy difficulty, UI layout and dialogue-font improvements
  from 0.8.1–0.8.25. Updated the title version to `v0.8.26`.
- Prepared the public patch release with installation instructions, source
  and target hashes, validation records and a verified patch round trip.
  Original Japanese disc images are not included.
- Translation still needs human proofreading/listening review and a full
  playthrough. Physical PlayStation testing remains outstanding.

## 0.8.25

- Fixed the clipped custom-pilot rank on the assignment page. It now uses
  the compact label font at the top right of the pilot panel, above the
  skill row. Kept its original red color and native rank values.
- Moved the stance label slightly left so `2x Move` and `Lv 1` no longer
  overlap. The six-character player name and two-digit skill level fit.
- Checked all six rank labels and a maximum-length name in the native
  renderer using temporary display fields, with no rank/assignment-rule
  changes. Reused existing drawing code; no code or allocation growth.
- Updated the title version to `v0.8.25`. EXE, dialogue font, briefing title,
  393 other VFS files, scripts and media remain unchanged. Loading limits
  and fixed disc extents pass.
- Archived 0.8.24 with a verified xdelta round trip and retained ten recent
  archives. Its BIN/CUE remains temporarily because another application has
  it open. Local testing build only; no public release. Physical
  PlayStation testing remains outstanding.

## 0.8.24

- Made dialogue lettering less tall while retaining even native-pixel
  strokes. Eligible characters omit a duplicate bitmap row using two
  unscaled native sprites; capitals are eight ink pixels high and lowercase
  bodies six. Punctuation with distinct strokes keeps its original shape.
- Kept dialogue widths, line wrapping, wording, colors, transparent
  backgrounds, typewriter behavior and paging. Menu fonts, the briefing
  font, assignment layout and the font texture remain unchanged.
- Checked every printable non-space ASCII character in ordinary/dialogue
  modes with 188 native geometry probes and captured the reported Episode 2
  line in-game. Updated the title version to `v0.8.24`; 394 other VFS files,
  media and scripts are unchanged. Loading limits and disc extents pass.
- Added audited resident helpers below the observed DF80 BIOS context
  boundary and below existing string pools, preserving debug scratch and
  fixtures. Each compacted glyph adds one native 20-byte sprite; physical
  PlayStation timing/BIOS testing remains outstanding.
- Archived 0.8.23 with a verified xdelta round trip and retained ten recent
  archives. Older locked files remain temporarily if open elsewhere.
- Local testing build only; no public release has been created.

## 0.8.23

- Lowered the episode title within the green briefing bar by one native
  pixel, centering the visible lettering vertically. Applies to all episode
  headings. Font size, left alignment, wording, colors and background remain
  unchanged.
- Only one coordinate byte changes in briefing.bin; updated the title version
  to `v0.8.23`. EXE, assignment typography, narration, place labels, scripts
  and media remain unchanged. No code growth or moved disc extents.
- Verified native briefing captures and loading limits, and archived 0.8.22
  with a successful xdelta round trip. Retained ten recent archives; older
  locked files remain temporarily if another application is using them.
- Local testing build only; no public release. Physical PlayStation testing
  remains outstanding.

## 0.8.22

- Reduced assignment-screen numbers to the same 11x13 font as their labels,
  including level, experience, skill level and all unit stats. Preserved right
  alignment and aligned the stat baselines and bars with the smaller text.
- Reduced `Sortie`, `1`, `2`, `3` and `Bench` to the compact font. Kept the
  pilot name, original panels, transparency, colors, portraits and icons.
- Native checks cover four-form and single-unit views, 30 stat label/value
  pairs, level/EXP/skill, all five headings and confirmation/continue/exit.
- Updated the title version to `v0.8.22`. EXE, 393 other VFS files, media,
  translated scripts and briefing narration typography remain unchanged.
  No file growth or moved disc extents; loading limits pass.
- Verified the 0.8.21 archive round trip and retained ten recent xdelta
  archives. Older 0.8.19 files remain temporarily if still open elsewhere.
- Local testing build only; no public release. Physical PlayStation testing
  remains outstanding.

## 0.8.21

- Increased the Weapons page's `Range` and `Area` secondary headers from
  11x13 to 14x17, between the 16x20 weapon name and 11x13 labels/values.
  Other names, labels and numbers retain their existing sizes.
- Balanced the weapon-details rows with a consistent 34-pixel center pitch,
  aligning labels and values and leaving 20/21 pixels of top/bottom padding.
  Original panels, transparency, colors, form links and weapon-list layout
  remain intact.
- Added an exact opt-in medium font mode, preserving the existing font code,
  tables and artwork. Native checks cover the new glyphs/advances, eight
  existing font modes, row spacing, all four form icons and page/weapon/exit
  controls. Status drawing outside the Weapons routine is byte-identical.
- Updated the title version to `v0.8.21`; retained the raised credit block,
  battle skip hint and Easy/Normal option. No file growth or moved disc
  extents. Other overlays, media and translated scripts remain unchanged.
- Verified loading limits and the 0.8.20 archive round trip; kept ten recent
  xdelta archives. The older 0.8.19 BIN/CUE remains temporarily because it is
  still open in another application.
- Local testing build only; no public release has been created. Physical
  PlayStation testing remains outstanding.

## 0.8.20

- Moved the title version and `github.com / retro-trans` credit upward by
  24 native pixels, to y=414 and y=430. The credit cell now leaves 37 pixels
  below it so the full line stays visible when the bottom edge is cropped.
- Preserved right alignment, text, font, shading, transparency and the
  spacing between the two lines. Updated the title version to `v0.8.20`.
- Changes are confined to the title credit wrapper. The EXE, battle skip
  hint, Easy/Normal option and all 394 other VFS files are unchanged.
- Verified both native text positions and a title capture with its bottom
  24 rows cropped; the full credit remains visible and menu navigation works.
- Verified loading limits and the previous-build archive round trip;
  retained ten previous xdelta archives. The 0.8.19 BIN/CUE could not be
  removed because another application still has it open; it is temporarily
  retained alongside 0.8.20 to avoid interrupting the running game.
- Local testing build only; no public release has been created.

## 0.8.19

- Added `press START to skip` at the bottom right of active battle attack
  animations. It uses the existing normal-proportioned 16x10 font, white/gray
  shading and shadow, with a transparent background.
- Anchored the prompt to the actual battle viewport (normally 512x240),
  leaving eight pixels at the right and four below the font cell. It is
  hidden during setup, pause, fast-finish and cleanup.
- Preserved native Start skipping, damage, actor synchronization and battle
  results. Native checks cover actual text placement, 29 visibility cases,
  first-input Start skipping and disappearance after skipping.
- Updated the title version to `v0.8.19`. The EXE, Easy/Normal difficulty,
  font assets, original audio/movies and 393 other VFS files are unchanged.
- Verified loading limits and the 0.8.18 archive round trip. Retained only
  the latest full BIN/CUE and ten previous xdelta archives.
- Local testing build only; no public release has been created. Physical
  PlayStation testing remains outstanding.

## 0.8.18

- Added a Normal / Easy choice at Game Start, before the original player
  setup. Circle or Start confirms; Cross returns to the title. Data Load
  bypasses the selector. The version/retro-trans credit remains visible.
- Easy keeps returning pilots' earned levels and partial experience between
  stages instead of resetting them to the stage's assigned level, and raises
  the level ceiling from 40 to 99. Newly joined/underleveled pilots still
  receive the original starting level. Normal retains the original rules.
- Saved the difficulty in the existing player record, preserving native save
  sizes and checksums. Older saves without the Easy flag continue as Normal.
  Kept experience awards, native stat growth, skill rules and enemies intact.
- Native CPU checks cover the 39/40, 40/41 and 98/99 boundaries, stopping at
  99, all 98 consecutive level-ups, 20 pilot growth records plus the custom
  player, stage-level/experience retention and native save/load/checksums.
- Fresh-boot menu checks cover Normal, Easy, cancellation and Data Load.
  Verified the actual Easy new-game player record carries the saved flag.
- Preserved 394 other VFS files and original audio/movies; updated the title
  version to `v0.8.18`. Fixed loading limits checked. Physical PlayStation
  hardware has not been tested; implementation and checks are documented in
  `docs/DIFFICULTY.md`.
- Archived 0.8.17 and verified its restored hash; retained the latest full
  BIN/CUE and ten previous xdelta archives.
- Local testing build only; no public release has been created.

## 0.8.17

- Replaced the 512x240 briefing overview's tall text with proportional 16x10
  cells, which display with normal proportions at 4:3. Applies to its episode
  title, map-location labels and narration, leaving other windows unchanged.
- Rewrapped narration across the full 440-pixel inner box width, using the
  actual font advances. Kept quoted names together and preserved branch-choice
  line breaks. All 108 briefing entries retain their wording and controls.
- Added an opt-in briefing font mode; old resident entry points and tables
  retain their addresses. Native checks cover six glyph modes and 30 dialogue
  width cases, plus two narration screens and the return to story dialogue.
- Preserved map models, backgrounds, palettes, status layout, subtitles, audio
  and movies. Updated the title version to `v0.8.17`; verified fixed loading
  limits and the 0.8.16 archive round trip. Ten older xdelta archives retained.
- Local testing build only; no public release has been created.

## 0.8.16

- Moved flight mini-game subtitles to the foremost native drawing bucket,
  ahead of the unit indicators, radar, portraits and menu panels.
- Reset the native draw area and origin before subtitle glyphs, preventing
  HUD-local clipping or offsets from affecting captions.
- Preserved transparent backgrounds, text, timings, font sizes and positions
  (flight rows 190/204, menu rows 350/376). All 75 cues remain unchanged.
- Updated the title-screen version to `v0.8.16`. Status layout, core, font
  assets, original audio and movies remain unchanged from 0.8.15.
- Native GPU-list checks confirm single- and two-line flight captions draw
  after every HUD/world primitive with a full-screen clip and correct buffer
  origin. Verified 480-line menu captions and unknown/disabled voice guards.
  Checked cue bounds, loading limits and the old-build archive round
  trip; retained ten older xdelta archives.
- Local testing build only; no public release has been created.

## 0.8.15

- Reduced the Weapons panel's `Range` and `Area` secondary headers to the
  compact 11x13 text mode, smaller than the 16x20 weapon-name header.
- Reduced operating-terrain text (`Land/Sea`, `Air/Land`, etc.) to 11x13
  and centered it horizontally and vertically within its original box.
- Kept all other status typography, values, colors, backgrounds and game
  data intact. Updated the title version automatically to `v0.8.15`.
- The renderer remains within its original 8,224-byte allocation. Core,
  font assets, audio, movies and subtitles are unchanged from 0.8.14.
- Verified native text sizes/positions, all three status pages, linked form
  icons, page controls and weapon selection. Land/Sea is centered within
  half a native pixel. Checked file loading limits and the older-build
  archive round trip; retained ten older xdelta archives.
- Local testing build only; no public release has been created.

## 0.8.14

- Added two right-aligned title-screen lines: `v0.8.14` and
  `github.com / retro-trans`. Small native shadowed text uses a transparent
  background, with a 12-pixel right margin in the 512x480 title framebuffer.
- The title version is generated from the build version automatically.
  Original title artwork, menu and copyright textures are preserved.
- Only `bin/title.bin` changes from 0.8.13. All 394 other VFS files, the
  executable, fonts, dialogue, movies, audio and subtitles are unchanged.
- Verified the wrapper loaded from disc, both native text positions, title
  Up/Down controls and entry into name setup. Credits do not appear in name
  setup. Restored the screenshot-only idle-timer fixture after capture.
- Checked file loading limits and the 0.8.13 xdelta archive round trip;
  retained the latest full image and ten older patch archives.
- Local testing build only; no public release has been created.

## 0.8.13

- Matched stat, terrain and weapon values to their compact labels, including
  shared numeric baselines. Kept HP/energy fractions at the same body size as
  their labels, and preserved numeric colors and right alignment.
- Centered weapon names horizontally and vertically within the existing
  selection rows, including names that wrap onto two lines.
- Native traces verify 55 label/value pairs and both name layouts. Checked
  all status pages, form icons and page/weapon/exit controls. Temporary long
  weapon-name test data was restored; no names or game data are changed.
- Font artwork, resident font code, backgrounds, models, Lnd positioning,
  dialogue wrapping, audio and movies remain unchanged from 0.8.12.
- Local testing build only; no public release has been created.

## 0.8.12

- Moved the map HUD terrain tag (Lnd/Air/Sea/Spc) six native pixels left,
  from local x=9 to x=3. The widest tag now ends at x=24, leaving three
  pixels before the HP/energy block at x=27.
- One coordinate byte changes in the existing game-overlay instruction.
  Font size, y position, colors, portraits, status pages, dialogue wrapping,
  gameplay and all other assets remain unchanged from 0.8.11.
- Compared the native HUD before/after with a temporary Land display fixture,
  then restored the fixture. Verified one changed disc sector, loading limits
  and the previous-build archive round trip.
- Local testing build only; no public release has been created.

## 0.8.11

- Reflowed story dialogue/narration for the current proportional font: 568 of
  959 entries have updated line breaks. Every rendered line fits 210 pixels,
  including a conservative six full-width-character player-name allowance.
- Preserved wording, row boundaries, explicit pages, portrait/speaker cues,
  pauses, blank lines and centered captions. Story wrapping is now refreshed
  at build time so later font changes cannot leave stale line breaks.
- Rebuilt 24 story script containers; their bytecode/headers are identical
  apart from relocated string pointers. Font, status UI, core, subtitle,
  movie and audio assets are unchanged from 0.8.10.
- Checked both pages of the reported Ryoma scene after a fresh disc boot,
  all compiled story containers, text fit, loading limits and archive restoration.
- Local testing build only; no public release has been created.

## 0.8.10

- Reduced status pilot/unit names, weapon names, resource labels/fractions,
  stat values, terrain percentages and operating-terrain text from 19x24 to
  16x20 cells. Unit HP/EN/Arm./Move labels now match the compact terrain labels.
- Kept the existing compact text, headings, gradients, restored arrow joins,
  reverse-L background, translucent panels and native form indicators.
- Added an opt-in status body-text mode without changing existing font artwork,
  resident routines or table addresses. Other text modes retain their sizes.
- Checked all three status pages, form indicators and page/weapon/exit controls,
  a fresh disc boot, text fit, loading limits and archive restoration. Verified
  old resident font bytes/addresses and all non-status VFS assets are unchanged.
- Local testing build only; no public release has been created.

## 0.8.9

- Restored the original status background shapes: the right-facing pilot-card
  arrows, dark inset blocks, blue reverse-L silhouette and translucent bottom
  frame. Removed the replacement rectangular preview outline.
- Reused the game's arrow artwork, native panel coordinates and blend colors.
  Kept the current font sizes, HP/Energy/Getter Ray wording and form icons.
  Returned the title tab and bottom frame to their original vertical positions.
- Compared against captures of the original native drawing routines. Checked
  all three pages, combined/single-unit icons and page/weapon/exit controls.
  Disc checks preserve the font, audio, movies and subtitle files from 0.8.8.
- Local testing build only; no public release has been created.

## 0.8.8

- Restored the referenced status-page arrangement: vertical form icons on all
  pages, native-sized model and preview origin, unit-name tab, grouped pilot
  fields, two-column unit/weapon details, and a shared footer with resource
  bars above the HP and energy rows.
- Kept the 0.8.7 font artwork/sizes and the HP, Energy and Getter Ray labels,
  with original translucent panel colors and colorful values.
- Checked all three pages, vertical form icons, page/weapon/exit controls,
  loading limits and the previous-build archive round trip. Only the status
  overlay changes; font assets, subtitles, movies and audio match 0.8.7.
- Local testing build only; no public release has been created.

## 0.8.7

- Enlarged the main Latin font from seven-pixel to nine-pixel capitals, with
  wider hand-drawn letters and seven-pixel lowercase bodies. Kept native cells,
  original color gradients and shadows. Updated proportional/digit spacing.
- Kept compact text near its previous visible size using 11x13 cells, and kept
  the native FONT8 text unchanged. Preserved the restored status form indicators.
- Reflowed 4 minigame and 21 preview captions to fit the larger font; wording,
  voice selection and cue timing are unchanged.
- Spaced the four status-stat rows for the taller digits. Checked the main
  map/briefing menus, dialogue, all status pages, restored form indicators and
  page/weapon/exit controls. Caption/name fits and loading limits pass; FONT8,
  movies and audio are unchanged.
- Local testing build only; no public release has been created.

## 0.8.6

- Restored the status pages' native unit/form icons, combined-unit indicator
  and translucent connecting panels. Aligned their three rows with the updated
  pilot cards while keeping the corrected fonts, palettes and model preview.
- Reused the original sprite-selection routines inside the existing drawing
  allocation. No unit data, controls, model assets, audio or subtitle changes.
- Checked the restored indicators on all three pages, including combined and
  single-unit cases, plus page/weapon/exit controls. The main program, all other
  VFS files and movie/audio sectors are preserved. Loading limits and the
  previous-build archive round trip pass.
- Local testing build only; no public release has been created.

## 0.8.5

- Added five timed captions for both male Combination Test result speeches,
  including the final drill. Audited all 25 native voice-selection call sites
  and their shared branches; 34 clips now have 75 cues.
- Renamed the briefing menu label to Combination Test. Preserved the previous
  70 cues, raised flight caption placement, translucent UI and colored text.
- Checked both native success-result voice branches and all five added captions,
  plus the renamed menu label. All 87 caption lines fit; loading limits pass.
  Only briefing/flight overlays change; the EXE, other VFS files, movies and
  audio match 0.8.4. The previous build archive restores to its recorded hash.
- Original audio and gameplay behavior are unchanged. Local testing build only;
  no public release has been created.

## 0.8.4

- Raised flight-view subtitles to rows 190/204, with single-line cues on row 204,
  so the text stays above the bottom edge. HUD overlap is allowed as requested.
- Preserved transparent captions, text, timing, audio, font size and menu-screen
  placement. The change replaces two drawing coordinates without growing code.
- Checked single- and two-line captions during the native tutorial, including
  their actual draw coordinates. All other disc sectors match 0.8.3; loading
  limits and the previous build's archive hash round trip pass.
- Local testing build only; no public release has been created.

## 0.8.3

- Corrected font proportions and spacing in sortie assignment, its confirmation
  window, and flight training's Stage and Controls menus. Repositioned pilot
  details, wrapped unit names, resized unit icons and aligned the stat rows.
- Preserved the assignment and minigame menus' original panel palettes, blending
  styles and colored text/icons.
- Restored the status pages' original green grid, translucent blue/green/red
  panel colors, colored resource maxima and distinct stat colors, retaining the
  corrected font proportions and layout from 0.8.2.
- Centered 480-line minigame voice captions with the corrected font proportions;
  flight-view captions retain their original size and placement.
- Checked native assignment/status/menu layouts and controls, the longest stage
  label, caption scaling/centering and all 79 caption-line widths. The EXE,
  movies/audio and 392 unrelated VFS files are preserved. Loading-limit checks
  and the 0.8.2 archive hash round trip pass.
- Local testing build only; no public release has been created. Implementation,
  checks and real-console limits are documented in `docs/MENU_LAYOUT.md`.

## 0.8.2

- Rearranged the Pilot, Unit and Weapons status pages with consistent panels,
  aligned values, two-line weapon names and a quieter background grid.
- Corrected status font and portrait proportions for the native 4:3 display.
  Resized and repositioned the model preview while preserving native rotation
  and zoom controls. Three-pilot cards fit above the shared HP/energy footer.
- Kept the native video/VRAM layout, overlay size, stats, battle calculations
  and controls. Implementation and hardware limits are in `docs/STATUS_LAYOUT.md`.
- Checked all three pages on a fresh disc boot, one- and three-pilot layouts,
  long-name wrapping, page/weapon controls and return to the map. All 358 names
  pass fit checks; movie/audio sectors are unchanged, loading limits pass and
  the 0.8.1 archive restores to its recorded hash.
- Local testing build only; no public release has been created.

## 0.8.1

- Enabled Start to skip battle attack animations in map battles, using the
  game's existing fast-finish and cleanup path. The original implementation
  restricted this shortcut to standalone battles.
- Changed one instruction in `battle.bin`; the overlay size, memory allocation,
  battle calculations and result-handling routines are unchanged. Details and
  validation are in `docs/BATTLE_SKIP.md`.
- Local testing build only; no public release has been created.
- Native map-battle checks cover early skipping and skipping after the animation
  starts, with attack/counterattack damage, energy use and experience dialogue.
  Final-disc comparison preserves every other sector; fixed-load checks pass.

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
