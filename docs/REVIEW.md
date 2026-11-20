# Reviewing the story script — brief for review agents

Read first: `BASE_RULES.md` (binding; see "Shared review workflow" and the section for your
stage), `docs/TRANSLATING.md` (format, control codes, voices), `work/glossary/glossary.json`
and `work/glossary/speakers.json`.

## Files

* Japanese + context: `work/translation/en/slices/mform_NN.json` (fields `id`, `speaker_jp`,
  `speaker_en`, `gender_variant`, `jp`; `gender_variant` marks the two versions of a player
  line). Full script in script order: `work/translation/en/mform.json`.
* English to review: `work/translation/en/out/mform_NN.json` (`id`, `en`, `note`). **Edit
  this file in place**: change `en` only where your stage finds a problem; keep `id`s and
  order; you may update `note` (append, do not delete the translator's notes).
* Your report: `work/translation/en/review/<stage>_NN.md` (one per slice you review) with:
  rows examined / rows in slice, every edited row id with the reason, and every uncertainty
  (ties you broke, referents you inferred, voice/tone calls left open). Problems that belong
  to another stage go in the report under "for <stage>".

After editing run `python tools/check_slice.py work/translation/en/out/mform_NN.json` and fix
every problem it reports. Edit no other file.

## Stages

* **accuracy**: compare with the Japanese in scene order (read the rows before and after).
  Meaning, missing / added details, who speaks to whom, referents, restored subjects and
  verbs (pro-drop), emotional force, deliberate pauses / cut-off lines, gender-variant pairs
  (male and female player versions must each match their own Japanese). Do not soften.
* **editorial**: read the English in scene order for clarity, flow, natural spoken English and
  character voice; consistent terminology across your slices. Fix what is wrong, leave what
  is merely different. Return meaning doubts to accuracy (report). Make the debug placeholder
  lines uniform: `This here's MAP 01!` (two digits, letters upper case: `MAP 06A!`).
* **proofreading**: spelling, grammar, punctuation, typos, duplicated or missing words,
  glossary spellings, control codes intact. No stylistic rewrites.

Project-wide decisions already taken (do not change): speaker tags come from speakers.json;
Gore = "Emperor Gore"; Gimbug = "Petty Officer Gimbug"; 連合軍 = "Allied Forces";
クジラ = "the Kujira"; ランドウ様 = "Lord Lando"; -san honorifics dropped; Jack King keeps a
light broken-English voice ("Me", occasional "-desu"); no "~" tildes (stretch letters).
Also decided (after the accuracy pass): interrobang is written `?!` everywhere (not `!?`);
the Hyakki Empire's 鬼 are "Oni" (not "demons"); the debug placeholder lines take no extra
words ("This here's MAP 09!", no "baby"/"pal"/"y'all"); a space goes before a pause code
pair, not after it (`word. $s80$s13Next`).
Sho calls Dr. Tachibana "Father"; "Institute" is capitalised when it names one
(the Saotome / Tachibana Institute, "the Institute"); 量産型ゲッターロボ = "Mass-Production
Getter Robo" (plural "Mass-Production Getter Robos").
Rows without a speaker that continue the previous line are shown as a new message (new
window page): start them with a capital letter or with "..." (`...have come to destroy you all!`).
