# Translating briefings and battle lines — brief for translation agents

Read first: `BASE_RULES.md`, `docs/TRANSLATING.md` (game, voices, control codes, ASCII only),
`work/glossary/glossary.json`, `work/glossary/speakers.json`. For how the story names things,
see the English (`en`) of `work/translation/en/mform.json`.

Input `work/translation/en/slices/data_*.json`, output `work/translation/en/out/data_*.json`
(same ids and order, `{"id", "en", "note"}`). Check and fix every problem:

    python tools/data_slices.py check work/translation/en/out/data_NAME.json

Kinds:
* `chapter title`: e.g. 第１話「発進ゲッターロボ」 -> `Episode 1: "Launch, Getter Robo!"`. Use the
  same episode titles as the chapter-title rows of `work/translation/en/out/ui_00.json` when
  that file exists (same Japanese titles); keep any full-width space padding as plain spaces
  only if the Japanese pads (the header is drawn in a fixed panel).
* `narration`: the briefing before each map (narrator's voice, past/present as the Japanese).
  Write prose; no `\n` (the build wraps it).
* `lines`: text with `\n` line breaks (headers, choice prompts such as `Which one will you
  rescue?\n  1. Tachibana Institute\n  2. Saotome Institute`): keep exactly the same number of
  `\n`, one English line per Japanese line, each line short (about 34 characters).
* `battle line`: shouts and short lines spoken in battle animations (attack names with `!`,
  grunts, taunts). Short and punchy; attack names from the glossary / weapon names; grunts as
  English interjections ("Ngh!", "Gaah!"). Some rows are a character name alone (the name
  tag): use speakers.json. No `\n`.
