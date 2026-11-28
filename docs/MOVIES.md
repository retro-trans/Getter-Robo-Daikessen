# Movie translation and build workflow

Version 0.1.4 adds English subtitles to the spoken movie scenes, both theme songs,
the three Getter Zan pilot captions, the credit roll and the final end card.
The audio remains the original Japanese performance. The title logo remains the
original artwork. C03, C13 and CG1 contain no supported translatable words and
are left byte-identical. Coverage and provisional readings are in
`work/translation/en/review/accuracy_movies.md`.

Version 0.1.5 removes the solid subtitle panel. Subtitle glyphs are drawn directly
on each original image with a one-pixel black outline. "Transparent background"
means the movie picture is preserved around the text; STR video itself has no
alpha channel. The credit roll keeps its own black background and reserves its
lower area for the song lyrics. The renderer's style settings participate in the
asset fingerprint, alongside the translation, so a style change requires a rebuild.
The 0.1.5 clips pass full decoding and final-disc checks. The 0.1.4 archive is
round-trip verified; its old full image remains temporarily while an external
emulator holds it open. Normal archive cleanup can remove it after that lock ends.
A muted native capture in `work/ui/movies/v015/C04_native_fb240.png` confirms the
transparent subtitle appearance in the real movie player. Validation details and
the final disc hash are stored in the same versioned folder.

## Subtitle visibility in 0.8.31

On v0.8.30, opening movie C01 frames 142–144 show the same lyric. The middle
frame spends so few bits on the subtitle that the letters almost disappear.
The comparison in `work/ui/movies/v0831/opening-comparison.png` shows
v0.8.30 on the top row and v0.8.31 below.

After partial replacement, the patcher decodes the output using FFmpeg. For
each active cue it measures the mean brightness of the letter interiors and
their black outlines against masks drawn with the subtitle font. If their
difference falls below 175 on the 0–255 scale, jPSXdec re-encodes that frame
from its edited source PNG, sharing the original sector allocation across the
whole picture. This can change compression detail outside the letters on
those frames. Validation measures the final stream again before the disc
builder accepts it. The contrast check requires NumPy and Pillow.

## Files

- `work/translation/en/movies.en.json`: all 18 movies, 212 timed English cues,
  three name-caption frame ranges, and explicit notes for unchanged clips.
- `work/translation/en/movie_credits.en.json`: 322 rows of English credits.
- `work/translation/en/movies/*.srt`: English review subtitles, one per voiced clip.
- `work/source/movies/*.STR`: untouched original raw 2352-byte movie sectors.
- `work/source/movie_analysis/`: local audio, Japanese transcripts, decoded frames,
  edited frame images, replacement XML, contact sheets, tool logs and verification.
- `work/build/movies/*.STR`: validated translated movie assets for the disc builder.
- `work/ui/movies/`: versioned emulator captures and test summaries.

Japanese script and recognition output must stay in ignored working directories.
The new manifests are already English-only. The normal `strip_jp.py` workflow
still applies before any future commit of other translation working files.

## Local tools

Use 64-bit Python 3.11, Pillow, FFmpeg and Java. jPSXdec v2.1 beta is downloaded
locally under `tools/vendor/jpsxdec/jpsxdec_v2.1-beta/`; its license and manual
remain with it. Downloaded binaries are ignored by git. Optional transcription
uses the already-cached faster-whisper large-v3/large-v2 models and local CUDA.
No game audio is uploaded to a transcription service.

The tool and its frame replacement interface are documented by
[jPSXdec](https://github.com/m35/jpsxdec) and its bundled manual, chapter 10.

Every mutating movie command is a dry run unless `--apply` is supplied. Review the
dry-run output first. `--movies C05 C16` limits decoding/rendering/patching to those
clips. After changing a subtitle or credit:

```powershell
py -3.11 tools/movie.py check
py -3.11 tools/movie.py decode --apply
py -3.11 tools/movie.py render --apply
py -3.11 tools/movie.py patch --apply
py -3.11 tools/movie.py validate --apply
py -3.11 tools/movie.py export-srt --apply
py -3.11 tools/build.py --version 0.1.5 --dry-run
py -3.11 tools/build.py --version 0.1.5
py -3.11 tools/movie.py verify-disc --disc work/output/GetterRoboDaikessen_EN_v0.1.5.bin --apply
```

`prepare` extracts the local audio and sample sheets; `transcribe` is for Japanese
source recognition. `--no-vad` is essential for the songs and brief reactions;
recognition during music can invent text, so it is never accepted wholesale.

The builder checks per-movie translation hashes and asset hashes before creating
a disc. Old or missing movie assets fail the build. jPSXdec edits copies of the
original streams. `build_disc.Disc.write_raw_sectors` then writes only changed
video sectors in their original locations and regenerates sector EDC/ECC.

## Timing and hardware boundaries

The game reads at 2x CD speed: 150 physical sectors/second. C01–C16 and CG1 use
1001/100 sectors per frame (about 14.985 fps); CG2 uses 1001/200 (about 29.97 fps).
FFmpeg's default STR rate is 15 fps even for CG2; do not use it to calculate CG2
subtitle frame indices. Frame selection uses the original frame's sector position.
The first XA sectors occur within the first tenth of a second; subtitle timing
should still receive a human playback check for precise lip-sync.

Movie table: EXE `0x8001149C`, 44 bytes per entry. CG1/CG2 indices are 1/2;
C01–C16 are indices 10–25. Native movie launcher: `0x8004E9D4`.
Native program 7 calls the movie path without modifying the release executable.

The existing player allocates two 0x28000-byte VLC/RLE output buffers at
`0x8004EC28`–`0x8004EC60`, passed as the output of `0x80051568` at
`0x8004F420`. The compressed ring allocation is 0x10000 at `0x8004EC00`–
`0x8004EC10`, configured as 32 sectors at `0x8004F1B4`–`0x8004F1C0`.
The separate 0x11000-byte allocation at `0x8004EC64` is VLC workspace/table
storage, not permission to enlarge movie frames.

Verification rejects changed audio, changed CD/XA headers, changed dimensions,
frame numbers/chunk placement or bitstream version, compressed frames larger than
their original sector slots or the 64 KiB ring, and RLE output above 0x28000.
Full-frame credits use the original sector allocation; partial replacement keeps
the other picture macroblocks for dialogue. No executable movie-player changes,
extra runtime subtitle renderer, changed frame rate or relocated movie is needed.

Real PlayStation hardware has not been tested. Re-encoding changes quantization
and VLC workload even when file sizes and memory limits remain valid. Console
playback, especially CG2 and the credit roll, remains a hardware verification item.

## Preview and sources

`tools/movie_preview.py C04` prints the native movie selection; add `--apply` with
the project's muted DuckStation running from a fresh boot. It changes only the
next dispatcher arguments in emulator RAM, restores its breakpoint and resumes.
See `docs/debug_tools.md` for captures and emulator controls.

`tools/movie_capture.py C04 --out work/ui/movies/v014/C04 --ticks 120 --apply`
can attach during a fresh boot and redirect the first native movie-launch call.
It stops at `0x8004F028` in the movie main loop, runs StoreImage/DrawSync from
scratch RAM with registers/memory restored, and reads both 24-bit framebuffers.
Movies use 480 VRAM halfwords for 320 RGB pixels; the ordinary 16-bit screenshot
reader would produce incorrect colors/width. The two framebuffers are at y=0/240.
This path also works when native window screenshots are unavailable.

Version 0.1.4 verification: 17,309/17,309 edited frames independently decoded;
all 18 final-disc stream layouts/content and 90 sector checksum samples pass.
The three unchanged streams remain byte-identical. Native muted DuckStation
captures cover C04 dialogue, CG2's different frame rate, C16 credits plus lyrics,
and C05's pilot caption. These are samples rather than full-clip listening checks.
Results and native framebuffers are in `work/ui/movies/v014/`.

Credits were transcribed from the original C16 frame images. External comparisons:
[credit transcript](https://raido.moe/staff/ps1/ps1_getter_robo_daikessen.html),
[romanization comparison](https://www.mobygames.com/game/201580/getter-robo-daikessen/credits/playstation/).
The original game remains the primary source; several unconfirmed staff readings
are explicitly listed in the accuracy report. Existing glossary character names
take precedence over these sites' alternative spellings.

The theme identities are confirmed by
[Masaaki Endoh's official discography](https://endoh-masaaki.com/discography/cant-stop/).
Lyrics were translated from the game's local audio/recognition, with uncertain
phrases recorded in the accuracy report. The opening lyric wording was compared
with the licensed [JOYSOUND listing](https://www.joysound.com/web/search/song/35509);
the ending has a [secondary lyric comparison](https://moegirl.uk/Say_Good-bye_Loneliness).
