# Translating battle lines — brief for translation agents

Read first: `BASE_RULES.md` (binding), `docs/REVIEW.md` (project-wide decisions),
`work/glossary/glossary.json`, `work/glossary/speakers.json`.

## What these lines are

During a battle animation the attacking / defending pilot shouts a line: attack names
("ゲッタートマホーク！"), battle cries, taunts, reactions to being hit, death lines, and lines
for special events (a ship's captain going down with the ship, ...). Every battle unit has a
text file (`<UNIT>.BIN`); the same line occurs in many units, so each unique line is one row.

## Files

* Input (read only): `work/translation/en/slices/battle_NN.json` — `id`, `units` (unit files
  the line occurs in, e.g. GR1 = Getter-1, GRG1 = Getter Dragon, SGR = Shin Getter, ZAN =
  Getter Robo Zan, GRGO = Getter Robo Go, HT/HK/KT/RD = enemy units of the Dinosaur Empire /
  Hyakki Empire / Insects / Lando's army, TEXAS, KUJIR = the Kujira, KINGD = Kingdom 007,
  GUSTF = Gustaf, ...), `prev` / `next` (the lines stored before / after it in the first
  file: lines of one pilot are stored together), `jp`.
* Output (edit in place): `work/translation/en/out/battle_NN.json` — `id`, `en`, `note`.
  Rows that already have `en` were translated and reviewed earlier: keep them unless they
  contradict the glossary; fill every empty `en`.
* Check: `python tools/battletext.py check work/translation/en/out/battle_NN.json` (0 problems).

## Rules

* Attack names must match the weapon names already in the game: look them up by Japanese in
  `work/translation/en/data.json` (rows `MCN_*`, fields `jp` / `en`) and
  `work/translation/en/ui.json`. Shout them with the same punctuation as the Japanese
  ("Getter Tomahawk!", "Drill Arm!!").
* Pilots: identify who says the line from the unit list, `prev` / `next` and content; keep
  each character's voice as in the story script `work/translation/en/mform.json` (search it
  for the same character). If the speaker cannot be settled, keep the line neutral and say so.
* Spoken, punchy English; full force (taunts and insults at the same strength). Restore
  subjects and verbs (BASE_RULES pro-drop rules). One row in, one row out.
* Plain ASCII; no `\n` (the build wraps); `...` for ellipses, `--` for cut-offs, `?!` order.
* Length: write the full line. Lines that fit their Japanese byte length are written in
  place, longer ones are relocated automatically — there is no hard limit, but very long
  lines (over ~60 characters) may not fit the battle window: report them.
* Note every non-obvious decision (speaker inferred, attack name not found, ...) in `note`.

Report at the end: rows examined / rows in slice, rows filled, uncertainties.
