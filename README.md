# Getter Robo Daikessen! — translation project

An open toolchain for translating **Getter Robo Daikessen!** (PlayStation, SLPS-02232),
plus the English translation built with it.

## Contribute

The story, menus, unit and pilot data, battle dialogue, title cards and movies are
translated, and every chapter has been checked to load and reach its map, but the game has
not been played through to the end yet, and no human has proofread the English against the
Japanese. If you want to contribute to this project or the next in any way — be it bug
reports, proofreading or playtesting — please join my Discord:

**[discord.gg/nZBZfTDfCP](https://discord.gg/nZBZfTDfCP)**

## Play it

The latest release is **[v0.8.26](https://github.com/retro-trans/Getter-Robo-Daikessen/releases/tag/v0.8.26)**,
a full patch for the Japanese release (**SLPS-02232**): the story scenes, briefings, menus,
unit and pilot data, every pilot's battle lines, the title cards and interface graphics are in
English, drawn with a variable-width font. The movies, the next-episode previews and the
flight training minigame have English subtitles over the original Japanese voices.

### Apply

Use [Retro Trans](https://github.com/retro-trans/retro-trans-tools), or apply the `.xdelta`
with DeltaPatcher or xdelta3. You need your own Japanese disc image as a raw single-track BIN
(MODE2/2352) with its CUE.

| Your source image | Patch |
|---|---|
| Japanese release, SLPS-02232 | `GetterRoboDaikessen-English-v0.8.26.xdelta` |

Check the source hashes in `README-v0.8.26.txt` if your patcher reports a mismatch; keep
checksum verification enabled.

For example:

```
xdelta3 -d -s "Getter Robo Daikessen! (Japan).bin" GetterRoboDaikessen-English-v0.8.26.xdelta "Getter Robo Daikessen! (English v0.8.26).bin"
```

The patched BIN is larger than the original, so load it through a CUE that names
the new file: use `GetterRoboDaikessen-English-v0.8.26.cue` from the release (rename it, or
the BIN, so the `FILE` line matches), or copy your own CUE and edit its `FILE` line. For a
CHD, extract it to BIN/CUE first (`chdman extractcd`).

**Boot the new image fresh.** Old emulator save states keep the previous executable and
data; memory-card saves work.

## Translate it

Fork it to fix the English, or to take the game into another language. Start with
**[docs/TRANSLATING.md](docs/TRANSLATING.md)** (story scripts), then
[TRANSLATING_UI.md](docs/TRANSLATING_UI.md), [TRANSLATING_DATA.md](docs/TRANSLATING_DATA.md)
and [TRANSLATING_BATTLE.md](docs/TRANSLATING_BATTLE.md). The binding rules are in
[BASE_RULES.md](BASE_RULES.md).

The English lives in `work/translation/en/*.en.json`. Those are the committed copies of the
working files with the Japanese removed (`tools/strip_jp.py`): to rebuild, extract the game
from your own disc (`tools/extract_iso.py`, `tools/vfs.py extract`), re-run the extractors to
get the working files back, then `python tools/build.py`. Every build checks each file the
game loads into a fixed-size buffer and refuses to write an image that would overflow one.

You need your own copy of the game. This repository contains no disc image, no game data
and no dump of the original Japanese script.

## What is here

| Path | Contents |
|---|---|
| `docs/TRANSLATING*.md` | **start here** — the translation briefs and the rules the build enforces |
| `docs/VWF.md` | the variable-width font: hooks, width tables, menu and overlay patches |
| `docs/formats.md` | GR.VFS, PAC/LZ containers, MFORM scripts, briefing and battle files |
| `docs/MOVIES.md` `EPISODE_PREVIEWS.md` `MINIGAME_SUBTITLES.md` | movie subtitles, the voiced next-episode previews and the flight minigame captions |
| `docs/GRAPHICS.md` | title cards, sprites and how translated graphics are packed |
| `docs/debug_tools.md` | DuckStation + GDB tools: virtual pad, string logging, chapter smoke test, crash diagnosis |
| `tools/` | extractors, LZ codec, the build, VCDIFF patcher, emulator and debugger tools |
| `work/translation/en/*.en.json` | the English translation |
| `work/glossary/` | names, units, weapons and terms, speaker tags |
| `CHANGELOG.md` | every build, what changed, and what broke |

## Do not sell this

This patch is free. Do not sell it, and do not sell anything made with it - no
pre-patched discs or images, no loaded memory cards or consoles, no paywalled or ad-gated
downloads.

It is an unofficial fan translation of a game Dynamic Planning and Bandai Visual own.
Selling it takes money for work that was given away, and it is the surest way to get a
project like this shut down.

## Credits

| Role | |
|---|---|
| Project lead | binhlt0402 |
| Proofreading | *none yet - see [Status](#status)* |
| Playtesting | binhlt0402 |

Translation passes, tooling and reverse engineering used Claude (Anthropic) and Codex
(OpenAI), directed by binhlt0402. The translation is machine-produced and then edited - see the
release notes for what that means in practice.

The English letters are a hand-drawn pixel font made for this project.

## Status

The translation is in progress. `CHANGELOG.md` is the honest record, including the builds
that crashed and why.

Every line was machine-translated and then put through separate machine review passes
(accuracy, editorial, proofreading) with a shared glossary. **No human has proofread it
against the Japanese yet.** Movie, preview and minigame subtitles come from assisted
transcripts of the Japanese voices; a human listening pass is still outstanding.

In-game checks so far: map 1 (menus, battles, joining units, experience, Game Over), the
briefing menu, save/load, settings, the flight minigame tutorial, and an automated run of
every chapter (2-25) from its briefing through its story to the map, logging every string
drawn. **No full playthrough yet. Real PlayStation hardware has not been tested.**
