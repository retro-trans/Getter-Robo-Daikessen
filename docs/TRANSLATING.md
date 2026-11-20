# Translating Getter Robo Daikessen! — brief for translation agents

Japanese PS1 strategy game (Bandai, 1999) gathering the Getter Robo casts: the original
Getter team (Ryoma, Hayato, Musashi, Benkei), Getter Robo G, Getter Robo Go (Go, Sho, Gai),
Shin Getter and game originals, against the Dinosaur Empire, the Hyakki Empire,
Professor Lando and others. The player is a new pilot candidate (named by the player,
male or female) who joins Dr. Saotome's team. Story scenes play on the battle maps
between turns, with portraits and two dialogue windows.

Read first: `BASE_RULES.md` (binding), `work/glossary/glossary.json` (names, units, weapons,
terms: always use its `en` spelling) and `work/glossary/speakers.json` (speaker tags).
If a name is missing from the glossary, give your best Hepburn reading and say so in `note`.

## Input

`work/translation/en/slices/mform_NN.json`: up to 80 rows in script order (the order the
lines are first used by the map's event script; consecutive rows are usually consecutive
lines of a scene). Row ids look like `MF08_02AE` = map script 08, string offset 0x2AE.

| field | meaning |
| --- | --- |
| `id` | copy to the output |
| `speaker_jp` / `speaker_en` | who speaks (empty = narration or the continuation of the previous line). `$n (player)` = the player character, whose name the player chose |
| `gender_variant` | `male player` / `female player`: the line is one of two versions of the player's line, shown according to the player's gender. Translate each in its own register |
| `jp` | the line's text without the speaker tag and the 「」 quotes |
| `note` | (sometimes) a hint from the extractor |

For context read the rows before and after yours, and the neighbouring slices
(`mform_NN-1.json`, `mform_NN+1.json`). The full script is in `work/translation/en/mform.json`.

## Output

`work/translation/en/out/mform_NN.json` (same NN): a JSON list, one object per input row,
same order:

```json
{"id": "MF08_02AE", "en": "English text", "note": "optional: decisions / doubts"}
```

Use `note` for every non-obvious decision (who a line is aimed at, a kept ambiguity, a
restored subject you were unsure of, a guessed name reading, a tie you broke). Leave it out
when there is nothing to say. Report rows-examined vs rows-in-slice in your final reply.

## Format

* Write only the line itself: no speaker name, no quotation marks around the speech (the
  game shows `Name: text`). Printable ASCII only: no curly quotes, no accents or macrons
  ("Ryoma", "Hyakki", not "Ryōma"). `...` for 「…」/「……」, `--` for a dash or a cut-off line.
* Control codes in `jp` must all appear in `en`, same number of each, at the matching
  place in the sentence:
  * `$sNN` speed / pause codes (`$s80$s13` = a dramatic pause, `$s05` = fast); keep them at
    the corresponding point of the English sentence;
  * `$/` = wait for a button, then a new page: keep every one;
  * `%1`...`%0`, `%2`...`%0`, `%3`...`%0` = coloured text (names of robots, people): wrap the
    English words that correspond;
  * `$n` = the player's name; `$fNNx` / `$mNNx` = portrait change.
* Do not insert line breaks (`\n`): the build word-wraps every line to the 210 px window
  (about 37 characters per line) and pages every 4 lines. Long speeches just run on to
  more pages, which is fine.
* Speech should sound spoken. Keep each character's voice: Ryoma rough and hot-blooded,
  Hayato cool and sardonic, Musashi cheerful and boastful, Dr. Saotome gruff and
  old-fashioned (he says わし/じゃ), Jack King's broken English-Japanese stays playful
  ("Me", "No problem-desu!" style is fine, keep it readable).

Check your file before finishing and fix every problem it reports:

    python tools/check_slice.py work/translation/en/out/mform_NN.json
