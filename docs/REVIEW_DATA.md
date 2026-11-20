# Reviewing UI, briefings, battle lines and names — brief for review agents

Read first: `BASE_RULES.md` (binding: "Shared review workflow" and the three stage sections),
`docs/REVIEW.md` (project-wide decisions — they apply here too), `docs/TRANSLATING_UI.md`,
`docs/TRANSLATING_DATA.md`, `work/glossary/glossary.json`, `work/glossary/speakers.json`.
The story script (`work/translation/en/mform.json`, fields `jp` / `en`) is already reviewed:
use it as the reference for terms, names and character voices.

## Files

| set | Japanese + limits (read only) | English to edit in place | checker |
| --- | --- | --- | --- |
| UI | `work/translation/en/slices/ui_00..06.json` | `work/translation/en/out/ui_00..06.json` | `python tools/ui_slices.py check <out file>` |
| briefings | `slices/data_brf.json` | `out/data_brf.json` | `python tools/data_slices.py check <out file>` |
| battle lines | `slices/data_ht.json` | `out/data_ht.json` | same |
| unit / pilot names | `slices/data_names.json` | `out/data_names.json` | same |

Out files hold `id`, `en`, `note`. Change `en` only where your stage finds a problem; keep
ids and order; append to `note` (why you changed it). Run the checker after editing and fix
every **problem** it reports. Pixel **warnings** mean the English may be wider than the box
the Japanese used: prefer a shorter natural wording when one exists (abbreviations are fine
for menu labels), but never cut meaning; report rows you could not fit.

Reports go to `work/translation/en/review/<stage>_<set>.md` (`accuracy_ui.md`,
`editorial_brf.md`, `proof_names.md`, ...): rows examined / rows in set, every edited id with
the reason, every uncertainty. Problems for another stage go under "for <stage>".

Run the three stages in order on each set: **accuracy** (whole set), then **editorial**
(whole set), then re-check the accuracy of your substantive editorial changes, then
**proofreading**. Keep the stages separate in your reports. Edit no other files.

## Things that must not change

* Control codes and placeholders: `%0`-`%9`, `%d`, `%s`, `%c2`, `$f00a`, `$s13`, `$/`, `$n`,
  `\n` (count as in the Japanese where the checker says so), `@00`.
* Rows with a `max_bytes` value are fixed-size fields: the English must not exceed it
  (the checker enforces it). Unit names 23 bytes, weapon names 31, pilot names 19.
* Already fixed by measurement in game — **do not touch** these ids: `title_8008BC38`,
  `title_8008BC0C`, `title_8008C08C`, `title_8008C0B0`, `title_8008C190`, `title_8008C1A0`,
  `title_8008C1B0`, `game_8008BBFE` ("SFStatus": the menu shows it from byte 2 as "Status"),
  terrain names `game_8008B7F0` .. `game_8008B818` (4 bytes max), `game_8008D14C`,
  `title_8008C0F8` / `title_8008C0FC` (Male / Female), `map04_800F8838`, `map18_800F88CC`.
* Names fixed by script (do not re-spell): Ryoma Nagare, Hayato Jin, Musashi Tomoe,
  Benkei Kuruma, Michiru Saotome, Dr. Saotome, Sho Tachibana, Dr. Tachibana, Go, Gai Daido,
  Emperor Burai, Emperor Gore, Baron Rasetsu, P.O. Gimbug / Petty Officer Gimbug, Lando,
  Hellreza, Shatner, Lambert, Jack King, Mary King, Schwartz, Neon, the Texas, the Kujira,
  Allied Forces, Dinosaur Empire, Hyakki Empire, Oni, Jaga Castle, Getter-1/2/3 (unit names
  use hyphens), Shin Getter Robo, Getter Ray, Get Machine, Eagle-Gou / Jaguar-Gou / Bear-Gou.
* UI terms already unified: 逆境 Fury, 回避 Eva, 合体 menu command "Join" (story: "combine"),
  搭載 Board, 反撃 Cntr, 防御 Def.

## Per set

* **UI**: short labels, menus, help lines, victory/defeat conditions, name entry and ability
  descriptions (title.bin), map messages. Many are abbreviations by design (4-6 letters in
  narrow menus); keep consistent abbreviations across the set.
* **Briefings** (`kind`: chapter title / narration / lines): narration between episodes.
  Chapter titles use `Episode N: "..."`. Branch choice menus keep their line breaks.
* **Battle lines**: shouts during battle animations; spoken, short, full force.
* **Names**: unit, weapon, pilot names. Mostly proofreading and glossary consistency;
  accuracy only where a name is a translated term (attack names).
