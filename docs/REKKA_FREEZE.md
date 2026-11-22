# Getter Rekka attack freeze — 0.8.27

The reported symptom was a freeze when attacking with Getter Rekka,
regardless of the selected weapon. A debug map fixture reproduced a BIOS
lock-up (`PC 0xA0`) while starting Hizanto in 0.8.26.

## Fixed buffer overrun

The unit-loading branch in the original `battle.bin` allocates **0x15000
(86,016) bytes** at `0x800ACB40..0x800ACB50`. It reads the pack at
`0x800ACB74..0x800ACB7C` through `0x8002E90C`, which obtains the full file
length via `0x80036F38` and passes it to the reader. There is no capacity
argument on that path.

| `prog00/zan1.pac` | Bytes |
|---|---:|
| Original Japanese pack | 85,496 |
| English 0.8.26 | 86,120 |
| Native allocation | 86,016 |
| English 0.8.27 | 85,748 |

The translated pack exceeded the allocation by **104 bytes**. All of
Rekka's attacks use this pack. The old build scanner only recognized
constant filename/capacity arguments to `0x8003A6FC`; it missed this separate
allocation and whole-file reader.

`battletext.fit_unit_pack` now uses the existing optimal LZ compressor for
the translated BIN and its enclosing TMV container when a unit pack is too
large. Decoded contents are preserved; no dialogue is shortened and no
animation, model, texture or audio is removed. Other unit packs keep their
existing packing. An oversized result fails the build.

`loadlimits.py` audits all **114** original unit packs against this buffer.
The shared `prog00/effect.pac` is checked against its separate native
126,976-byte allocation. These checks now run before the disc is written.

`py -3.11 tools/battle_pack_check.py` verifies the original allocation
instructions, reproduces the oversized translated pack, compares all its
decoded entries recursively, and tests exact-capacity/oversized rejection.
All checks passed.

## In-game verification

In DuckStation, a chapter 2 test battle made Getter Rekka and an adjacent
enemy available. Each of the four weapons available in that battle completed
its animation and returned control to the map without pressing START.

| Weapon | Returned to map |
|---|---|
| Hizanto | Yes |
| Flower Frenzy | Yes |
| Combined Windmill | Yes |
| Demonslayer Ray | Yes |

For each attack, the game loaded all 85,748 bytes from the disc and the
128 bytes immediately after the allocation retained their pre-load contents.
Applying the local xdelta to the original Japanese BIN reproduced the tested
English BIN byte for byte. Its SHA-256 is
`c8b74236cad15dc2cfc39034b94da603882aeffd0a0820b2f673af88af880f09`.

## Hardware boundary

The fix uses the original PAC/LZ formats and decoder. The heap allocation,
executable and battle routines are unchanged; extra console RAM is not
required. Real PlayStation testing remains outstanding.

Evidence and native test fixtures are under `work/ui/rekka/`. Unit identities,
positions and health changes in those fixtures exist only in the project
emulator, not in the patch or memory-card saves.
