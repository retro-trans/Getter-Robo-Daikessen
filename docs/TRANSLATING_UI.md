# Translating the UI strings — brief for translation agents

Read first: `BASE_RULES.md`, `docs/TRANSLATING.md` (game, voices, control codes),
`work/glossary/glossary.json` and `work/glossary/speakers.json`. Every unit, weapon, place and
character name must use the glossary `en` spelling.

## Input / output

Input: `work/translation/en/slices/ui_NN.json`. Rows in address order (consecutive rows are
usually neighbours in the same table or menu). Fields:

| field | meaning |
| --- | --- |
| `id` | `<file>_<address>` (exe, game = map menus, title = new game / naming, briefing = between-map menus, flight = the flight mini game, battle, mapNN) |
| `kind` | `weapon name`, `unit name`, `skill level`, `dialogue`, `ui` |
| `max_bytes` | hard limit (the text sits in a fixed record field): the English must not be longer |
| `max_px` | width the game gave the Japanese (12 px per Japanese character). English letters are 3-7 px (about 6 on average): stay within max_px so menus and boxes do not overflow; abbreviate if needed (`Atk`, `Def`, `EN`, `HP`, `Lv`). Over the limit is reported as a warning: only accept it for text in a wide box |
| `jp` | the Japanese |

Output: `work/translation/en/out/ui_NN.json` — list of `{"id": ..., "en": ..., "note": ...}`,
same ids, same order. `note` for non-obvious decisions and for what you think the string is
(menu item, caption...). Check before finishing and fix every hard problem:

    python tools/ui_slices.py check work/translation/en/out/ui_NN.json

## Format

* Printable ASCII only. Keep every control code: `%0`-`%9` (colour), `%s` `%d` `%c2`
  (values inserted by the game: keep them, in the same order), `$fNNx $mNNx $sNN $/ $n`.
* `dialogue` rows (pilot shot down / Getter berserk lines, etc.) look like
  `$m01b%2隼人%0$s13「……」`: write them like the story: `$m01b%2Hayato%0$s13: ...` (speaker name
  from speakers.json, 「」 dropped, `: ` after the name). No line breaks: the build wraps them.
* Lines that are fragments of one sentence (e.g. Michiru's skill explanations in `title_*`,
  each fragment is one line of a two-line box; the game prints them one after another) must
  stay fragments that join into a correct English sentence in the same order; each fragment
  within its max_px.
* Weapon / unit names: glossary form; title case; no "No." / "Go"-suffix invention. Japanese
  full-width digits and letters become ASCII (`ＢＴ－２３` -> `BT-23`).
* Terrain flag strings like `空陸海` / `空・陸・海` are column markers (Air / Land / Sea): keep the
  positions: `空陸海` -> `ALS`, `空 海` -> `A S`, `空・陸・海` -> `A/L/S` style within max_bytes.
* Debug menu strings (`デバック`, `モデルプレビュー`...) are translated plainly.
