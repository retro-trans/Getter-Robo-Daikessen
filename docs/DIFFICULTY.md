# New-game difficulty (0.8.18)

Game Start opens a Normal / Easy selector before the original player setup.
Normal is selected initially. Up/Down (or Left/Right) changes the choice;
Circle or Start confirms, and Cross returns to the title menu. Data Load
continues directly to the original load screen.

Normal preserves the original stage level assignments and level-40 ceiling.
Easy raises the experience-award ceiling to 99 and retains returning pilots'
earned levels and partial experience when the next stage's assigned level
would lower or equal their current level. Pilots below a stage's assigned
starting level still receive the original starting level. Experience awards,
stat-growth interpolation, enemy stats, starting roster and skill rules are
otherwise native.

The stage behavior is separate from the hard ceiling: core `0x8005661C`
prepares a chapter using the level/roster table at `0x800120CC`; its call at
`0x800566C4` originally sets returning pilots to the stage level. Easy guards
that call. The experience routine at `0x8005D2A8` has a separate `level < 40`
comparison at `0x8005D328`, changed to a comparison against 40 or 99.

## Persistence

The choice uses bit 15 (`0x8000`) of the existing 16-bit player flags. The
player record starts at manager-block +8 and is already serialized at save
offset `0xB0`. Native initialization at `0x8005D674`, chapter preparation,
save (`0x8005285C`) and load (`0x80052D90`) preserve the other flag bits.
The saved-data size remains `0x1A70`, with the original checksums, card slots
and I/O. No emulator setting or external sidecar is needed. Existing saves
without this bit use Normal. Starting a new game always writes the confirmed
choice; loading a save derives the rules from that save's player record.

## Implementation and hardware boundaries

- `tools/difficulty.py` generates the native MIPS code and asserts the
  original instructions at every hook before patching.
- The title update/draw wrappers start at `0x80093400`, after the version/
  credit wrapper. They freeze title-menu input/idle processing while the
  selector is open, then use the original confirm cleanup and fade sequence.
  The original title art, menu, player setup and load code remain in place.
- Three resident helpers plus the pending new-game choice occupy
  `0x8000DC40..0x8000DCE7` (168 bytes). This is after the debug StoreImage stub
  ending at `0x8000DC20` and before preview scratch at `0x8000DD00`.
  **`0x8000E000..0x8000E6FF` is BIOS thread/exception storage, not free code
  space.** An initial local candidate there failed the boot check and was
  discarded before validation.
- The existing EXE boot loader copies these bytes and invokes BIOS
  FlushCache. No live instruction rewriting, emulator API, CD streaming
  shortcut, extra RAM or new hardware behavior is shipped.
- The native growth function bounds its growth-table indices and handles
  the stored level as a signed halfword. Level 99 fits the original two-digit
  displays and save fields. The original interpolation is used unchanged;
  the patch does not invent additional stat-growth data.
- Physical PlayStation hardware has not been tested. The resident low-RAM
  technique is shared with the existing VWF patch; BIOS compatibility beyond
  the project's tested configuration remains a hardware-validation limit.

## Validation tools

All tools default to dry run. Use only the muted project DuckStation.

- `tools/difficulty_title_check.py --choice easy|normal|load --apply`:
  fresh-boot native menu navigation, cancellation, selector rendering and
  transition to the original setup/load flow. Screens and reports go to
  `work/ui/difficulty/v0818/`.
- `tools/difficulty_check.py --apply`: native CPU probes at the title, using
  the game's actual pilot definitions and level/save routines. Probes cover
  Normal/Easy boundaries, consecutive leveling to 99, growth records, stage
  retention, player initialization, native checksum and serialized save/load
  round trips. Test fixtures, pending choice and registers are restored.
  It writes no memory card or disc. Fixtures temporarily occupy the unused
  tail of the title overlay slot; do not run this tool during another overlay.

The full build integrates difficulty after the title credit patch and before
the resident EXE boot packing. Other game scripts and audiovisual data do
not need rebuilding for this feature.

The 0.8.18 native CPU run passed all 98 consecutive level-ups, six boundary
cases, 20 levelable pilot growth records plus the custom player, five stage
assignment cases, player initialization and both Normal/Easy save/checksum/
reload cases. Fresh-boot title runs cover both selections, cancellation and
Data Load without a difficulty prompt. The rendered selection highlight and
text centering were inspected in the game framebuffer.
The real Easy new-game flow also initialized its live saved player flags to
`0x8002`, confirming the menu choice reaches the original setup record.
