# Status screen layout — 0.8.2

Version 0.8.3 keeps this geometry and restores the original transparent panels,
green grid and colorful text, following the user's preference. Current style
and build checks are documented in `MENU_LAYOUT.md`; the notes below record
the initial 0.8.2 implementation and validation.

The Pilot, Unit and Weapons pages use new panels, proportional lettering and a
smaller model preview. The moving grid is subdued. Live HP/energy and the four
unit stats share a consistent footer. Weapon names wrap over two lines.

## Native implementation

The game retains its 512×480 video mode and existing framebuffer/texture VRAM
allocation. In a 4:3 display its pixels are wider than they are tall. The old
status font doubled only the height of a 12×12 cell. Status text now opts into
19×24 cells, or 13×16 cells for secondary labels and pilot stats, with matching
variable-width advances. Portrait rectangles are 38×48 native pixels so that
they appear square at 4:3. Other screens retain their existing font dimensions.

`tools/status_layout.py` replaces the drawing-only span
`0x800982B8..0x8009A2D8` in `game.bin`; the replacement occupies 5952 bytes of
the available 8224 bytes. Its only external overlay call site, `0x80097AB8`,
is redirected after an audit of references into that span. Overlay length and
allocation are unchanged. Native input/update routines, unit/pilot getters,
weapon damage calculations and model loading remain in use. Panel draws use
the native GPU queue with explicit draw-environment resets for their buckets.

The core glyph hook at `0x8004D7AC` recognizes two status-only flag bits. Its
default path preserves the previous dimensions. The resident VWF code and
tables end below `0x8000F600`, where the next UI string pool starts. Code uses
the original R3000 instruction set and observes load/branch delays.

The preview origin moves from (356,248) to (380,208). The 112 native camera
presets keep their individual offsets and rotations; their position vectors
are uniformly increased by up to 25%, bounded by the native ±16384 input range.
Mesh scaling and assets are unchanged. The existing grid changes color only.

All values retain their native sources, including modified attack power,
base/bonus power, EN versus Getter energy, terrain coefficients, special
weapons and multi-pilot records. The build checks all translated unit and
weapon names against the same two-line wrapping rules used by the renderer.
All 111 unit records have at most six ordinary weapons; allowing the two native
special actions keeps the list within eight rows and its original capacity.

Real-console testing remains outstanding. The drawing replacement changes the
number/order of primitives and adds work per status glyph; timing on hardware
and every model/weapon combination have not been tested. No extra framebuffer,
texture allocation, overlay extension, CD reads or new model assets are added.

## Review and validation

UI wording was checked in three passes: field/enum accuracy against the native
draw routines, editorial review for clear labels, and proofreading of the
rendered pages. Expanded labels include Range shape, Area shape and Area size;
the operating-terrain names follow the original six-value mapping. Established
unit, pilot and weapon translations are retained. No dialogue script changed.

`tools/status_capture.py` defaults to a dry run. `--apply` captures native
512×480 VRAM; `_4x3.png` files are display-aspect exports at 640×480. The optional
`--hotpatch` reloads only audited drawing/code sites at a main-loop DrawSync
stop, rejecting active text/layout return addresses. Debug-only Lady Command
and Getter-1 fixtures cover the reported stats, portrait and three-pilot layout.
They change emulator RAM, never the disc or a save. Close and reopen Status
after changing a fixture to let the native loader replace the model.

Final-disc validation and captures are recorded under
`work/ui/status/v082-final-disc/`; build checks are in
`work/ui/status/v082-validation.json`.

The finished image was booted without drawing hot patches. Native chapter-2
navigation reached the map, and Lady Command and Getter-1 fixtures were
reopened through the game's model loader. Their three pages, the three-pilot
cards and an alternate weapon were captured. Left/Right changed pages, Down/Up
changed weapons, and Cross returned to map video mode 1. A RAM-only long-name
fixture checks two-line wrapping; its name is restored afterward. These are
representative checks, rather than an all-unit playthrough.

The final image changes 17 raw sectors from 0.8.1, confined to the EXE and the
status overlay in GR.VFS. Disc file positions and sizes are identical. The other
394 VFS files, movie/audio sectors and the battle-skip patch are preserved.
The load-limit checks and the archived
0.8.1 image's hash round trip pass; ten old build patches are retained.

## Restored form indicators — 0.8.6

The redraw had omitted the native form/combination icons and linked translucent
panels. Their original drawing routines (0x800985B4..0x8009864F and
0x80098980..0x80098D1B) are now copied into the same drawing allocation, with
internal absolute jumps relocated and external native calls preserved. The
original unit-count, combination/alternate-form flags, pilot-presence checks,
icons, panel colors and connector branches remain intact.

Rows align with the three pilot cards at y=52,156,260; native icon positions
are x=268 (forms) and x=329 (combined unit), with 24x30 sprite rectangles.
The Weapons page uses a horizontal strip below its details: the three form
icons sit at x=268,383,437 and the combined icon at x=329, all at y=335.
Its detail rows are tightened to leave room for the original panels.
The renderer occupies 8188 of the existing 8224 bytes, ending at 0x8009A2B4.
The overlay size, heap allocations, VRAM layout and gameplay logic do not change.
The existing original-hardware timing limitation still applies.

The native capture tool accepts --check-icons to record the actual icon draws
on Pilot, Unit and Weapons pages. Validation and screenshots are kept under
`work/ui/status/v086/`.

0.8.6 checks cover Getter-1 with all four icons on every page, the original
linked gray panels, horizontal Weapons strip, and native page/weapon/exit
controls. A Lady Command fixture checks the one-icon case. The final drawing
bytes were reloaded at a safe native DrawSync stop after a fresh 0.8.6 disc boot;
the reopened Getter-1 capture uses the native model loader. The final disc is
checked against those exact generated bytes. No dialogue wording changed.

Version 0.8.7 enlarges primary Latin glyphs within their existing atlas cells;
compact roles use 11x13 cells to preserve their visible size. All restored form
icons, panels and connecting lines are retained. The 8188-byte status renderer
and its original allocation are unchanged.

The four footer stat rows now use a 21-pixel pitch at y=380,401,422,443,
with compact labels centered beside the larger values. Native page, weapon
and exit controls and all four Getter form indicators were checked again.

## Original arrangement restored — 0.8.8

The user requested the reference layout while retaining the 0.8.7 font and
English HP/energy labels. The shared preview is now (218,34,258,336), ending
above the footer. On Weapons it is split around the detail panel so translucent
colors blend only once. It retains the native model origin (356,248) and all 112 original camera presets. The
unit-name tab uses the native sloped-quad drawing path.

Pilot cards are (30,50+97*i,184,94). Names sit over the portrait/details,
level/experience share the compact row, and the five stats sit at the right.
The original form column and combination links remain vertical on every page:
component icons at (230,65+97*i), the combined icon at (291,65).

The Unit page groups HP/EN and Armor/Move in two columns, followed by the
operating-terrain band and two-column terrain table. The Weapons page keeps
the list at the left and details at (280,104,194,260), with paired cost/kind
and sea/terrain rows, then separate Range and Area sections. Labels use Arm.,
Terr., Shp and Rng where the original groups require short field names.
No field values, native calculations or enum mappings change.

The footer is one (30,370,444,96) panel. Resource bars sit above the HP and
energy rows; their 0.8.7 labels, colors and font remain. Stat labels/values
sit beside them with the original 147-pixel bar scale. Main/compact cells
stay 19x24 and 11x13; no font atlas or resident-font bytes change.

The 8204-byte renderer remains wholly inside 0x800982B8..0x8009A2D7, with no
overlay, heap or VRAM growth. Native Getter-2 captures verify all three pages,
four form icons per page, page switching, weapon selection and return to map.
Only bin/game.bin changes from 0.8.7; the other 394 VFS files are identical.
Physical-console timing remains untested. Native captures and final comparison/
archive checks are stored under work/ui/status/v088/.

## Original background geometry restored — 0.8.9

Version 0.8.8 still used a bordered preview rectangle and rectangular pilot
cards. The native background is a reverse-L silhouette: the right block is
(229,46,247,312), with an 11-pixel strip at x=218. On Pilot, that strip begins
below the occupied pilot rows. These values come from the original rectangles
at 0x8008D214 and 0x8008D21C. The footer's four translucent blue frame pieces
and dark interior copy the native table at 0x800A944C..0x800A9473 exactly.

Pilot cards retain the native green 184x94 rectangle, opaque dark stat/skill
insets and right-facing arrow sprite from status resource +0x70, drawn at
(214,50+97*i). The original form-arrow cutouts and linked icon panels remain.
The title tab returns to y=19, with its text at y=22. The footer returns to
(30,358,446,96); its text and bars move upward 12 pixels to match the frame.
Fonts, label wording, models, cameras, input and gameplay calculations do not
change. No script translation was edited by this build.

The renderer uses 8044 bytes of the existing 8224-byte drawing allocation.
Shared drawing loops retain the native opaque dark insets on Pilot, Unit and
Weapons, with their original palette colors. The Unit/Weapons insets fit the
current larger text; the Weapons panel stops above the native footer frame.
It does not grow the overlay, heap or VRAM allocation. Physical-console timing is
untested. Captures and build verification are stored in work/ui/status/v089/.

## Status text hierarchy — 0.8.10

The status renderer explicitly separates body values/names (16x20 cells),
compact labels (11x13) and headings (19x24). Pilot names, both unit-name labels,
weapon list/detail names, all formerly large values/fractions/percentages,
Land/Sea and resource labels use the body mode. Unit HP/EN/Arm./Move labels
use the same compact mode as Flat/Sea/Ice. Existing compact labels and pilot
levels/skills/stats remain unchanged; Weapons/Range/Area headings retain their
heading size. Background coordinates, colors, models, bars and icon positions
are identical to 0.8.9.

The new body mode requires an exact 0x32 high flag byte. Its dispatcher and
advance table are appended after the old resident font code; every old routine,
advance table and glyph-width address is preserved. Calls using other modes
run the unchanged old paths. Font artwork and all subtitle/media assets are
unchanged. The resident block ends at 0x8000F534, below 0x8000F600. The status
renderer still uses 8044 of its existing 8224 bytes.

The executable's boot payload grows by one 2048-byte sector; its ISO extent is
relocated by the existing disc writer. This uses normal PS1 executable/ISO
loading and does not change movie/audio extents or add runtime heap/VRAM use.
Physical-console timing remains untested. Captures and scope/bounds checks are
stored under work/ui/status/v0810/. No translation wording changed.

## Paired numeric sizes and weapon centering — 0.8.13

HP/Energy/Getter Ray resource labels and fractions remain 16x20. Footer stats,
Unit stats/terrain percentages and Weapons values use 11x13, exactly matching
their compact labels. Values share their label's y position. Existing pilot
stats/levels/experience were already compact and remain so. Colored values
retain their format controls and gradients. Names remain 16x20 and headings
remain 19x24.

Right alignment now measures with the actual body or compact advance table.
Compact numeric formatting uses the shared right-aligned text helper rather
than a separate digit-count approximation. Existing font artwork, resident
font code and advance tables are unchanged.

Weapon-list fit requests carry bit 20 in the layout flags. Each line is
centered in the 164-pixel inner width (x=40), sharing the selection box's
center at x=122. Single-line names move down 7 pixels; two-line names use the
existing 16-pixel line pitch, with the block starting one pixel above the old
text origin. Centering uses the actual truncated line width when wrapping at
a space. The original selection rectangle (x=38, y=row-2, w=168, h=34) stays.
The shared briefing fit helper retains its existing compact output mode and
fits its original code allocation; briefing assets are unchanged in this build.

Native font-call traces check 55 label/value pairs, normal weapon names and a
RAM-only Double Tomahawk Boomerang fixture. The fixture is restored after
capture and never enters the output disc. Screenshots/traces/check results
are in work/ui/status/v0813/. The renderer uses 8128 of its original 8224 bytes;
no overlay, resident-code, heap or VRAM expansion is introduced. Physical-
console timing remains untested.

## Secondary headers and operating-terrain centering — 0.8.15

Range and Area now use the compact 11x13 mode rather than the 19x24 heading
mode. The weapon-name header remains 16x20, so it has a clear size hierarchy.
The secondary headers retain their horizontal anchors at x=288 and x=388;
their compact draw origin is y=257, matching other compact text conventions.

The operating-terrain box remains (36,164,172,26). All six entries in the
native terrain-name table now use 11x13 cells and the matching compact
advance table. Draw x=floor((244-measured_width)/2), y=170. Land/Sea measures
48 pixels and draws at (98,170), centered at x=122 with 6/7-pixel vertical
margins around the 13-pixel cell. Shorter and longer terrain names use the
same centering logic. No wording, other text sizes or box dimensions change.

The renderer uses 8,136 of the existing 8,224 bytes; no overlay, resident font,
heap or VRAM growth. The local build also regenerates the title's version
line as v0.8.15, retaining its credit and geometry. Evidence and checks live
under work/ui/status/v0815/. Physical-console timing remains untested.

The native trace confirms Range/Area cells of 11x13 versus the Drill Arm
header's 16x20, and Land/Sea at (98,170). Page/weapon/exit controls and all
four linked form icons pass. Captures use the existing RAM-only Getter-2
data fixture; its values/model are test context, absent from the disc patch.
The renderer's `rect_unit_tab` width and form-link height are mutable runtime
data, so a whole drawing-region RAM/file equality check is inappropriate.
The built overlay is verified separately; native text calls verify execution.

## Medium secondary headers and row rhythm — 0.8.21

Range and Area use an exact opt-in 14x17 mode (`0x36`), above the compact
11x13 labels/values and below the 16x20 weapon name. Their draw origins are
(288,250) and (388,250). Font artwork, colors and backgrounds are unchanged.

All detail rows share a 34-pixel center pitch. Compact row origins are
y=150 (Attack), 184 (cost/kind), 218 (Sea/terrain), 286 (shape) and 320
(range/size); the 17-pixel secondary headers start at 250. Centers are
156.5, 190.5, 224.5, 258.5, 292.5 and 326.5. Labels and values align on each
row. The first body row has 20 pixels below the weapon-name cell, and the
last has 21 pixels above the inset bottom. Left-list spacing/centering,
selection boxes, footer, native panel silhouette and linked icons stay intact.

The renderer remains 8,136 bytes inside its original 8,224-byte allocation.
Code outside the Weapons drawing routine is byte-identical to 0.8.20.
A 124-byte font block at 0x8000DD40..0x8000DDBC supplies the medium mode;
the old font block and tables retain their bytes and addresses. See VWF.md.

Evidence: `work/ui/status/v0821/`. Native checks cover actual glyph dimensions
and proportional positions, all row centers and paired text sizes, eight
existing font modes, four linked icons on each page, weapon selection and
return to the map. Model/stats in the preview are the existing RAM-only
Getter-2 fixture, absent from the patch. No overlay/EXE size, disc extent,
heap or VRAM growth. Physical-console timing remains untested.
