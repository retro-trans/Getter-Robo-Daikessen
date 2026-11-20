# Graphics with text

All edited images are produced as TIM files under `work/translation/en/gfx/<vfs pac>/<entry>`
(entry name as unpacked: `<container offset>_<index>_<NAME>`) and packed by `tools/gfx.py`
during `tools/build.py`. The generators need OpenCV + numpy (64-bit Python 3.11 here):

    py311 tools/gfx_cards.py     title cards, Game Over, previews, reports, copyright, promo
    py311 tools/gfx_sprites.py   small text sprites (flight minigame, result plates, seat icons)

Previews: `work/ui/gfx_sheets/en_cards.png`, `en_sprites.png` (original | English).

| file | content | method |
| --- | --- | --- |
| mapsys/mt*.pac | chapter title cards (8 bpp 320x240) | white text found by outline, inpainted, redrawn (Franklin Gothic Cond.) |
| mapsys/gameover.pac OVER02 | ゲームオーバー | red text inpainted, "GAME OVER" (Impact) |
| flight/anno*.pac | 次回予告 + episode title (320 wide = 256 + 64 TIM pair) | stitched, inpainted, split, each half to its own CLUT |
| flight/title.pac, flight.pac, result.pac | minigame titles, HUD, plates, stamps | non-antialiased glyphs on the sprite's own 16-colour ramp |
| flight/result.pac REP_1/2/3 | paper reports | text in fixed rectangles inpainted, redrawn in sampled ink |
| entry/change.pac EMPTY, FUKA | 空席 / 不可 seat icons | box kept, glyph colour kept |
| demo/title.pac, title2.pac COPY0/1 | copyright | line 2 continues in COPY1 on screen: sized so it ends inside COPY0 |
| flight/show.pac FACE000-003 | promo screen (512x480 in four TIMs) | inpainted per line rectangle |

Kept: the game logo, GAME START / DATA LOAD (already English), button icons.
Palettes and VRAM positions never change; packed sizes are reported if a pac grows.
