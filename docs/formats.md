# Getter Robo Daikessen! (SLPS-02232) — data formats

Disc: one MODE2/2352 data track. ISO9660 files: `SLPS_022.32` (exe), `GR.VFS` (all game
data, 18.7 MB), `GRXAP.XAP` (XA audio), `*.STR` movies, `SYSTEM.CNF`.

## GR.VFS (`tools/vfs.py`)

```
0x000  'VFS0'  u16 total_entries (404)  u16 root_count (12)  u32 8
0x800  directory table, 32-byte entries
         +0  u32  file: sector          | dir: byte offset of first child (from 0x800)
         +4  u32  file: size in bytes   | dir: number of children
         +8  char name[23]
         +31 u8   flags: 0x08 = directory; files: bits 0-2 = offset in 0x100 units
0x4000 data area
file byte offset = 0x4000 + sector * 0x800 + (flags & 7) * 0x100
```

Files are packed back to back on 0x200 boundaries (no gaps, no overlaps).
`gr.exe` (sector 0) is a placeholder: the real exe is `SLPS_022.32` on the ISO.

## PAC container (`tools/pac.py`)

Every `.pac` (and `mapsys/mapNN.dat`) is exactly one container covering the file:

```
+0      u32 count
+4      u32 off[count]          payload offset of entry i (from container start)
payload-0x1C  entry header:
   +0x00 char name[12]   encoded: 'A'-'Z' -> c+0x60, other chars -> c+0x40
   +0x0C u32  unpacked size
   +0x10 u32  packed size (LZ stream, without the 16-byte prefix)
   +0x14 u32  timestamp
   +0x18 u16  mode (0 copy, 1/2/4 RLE, 3 LZ)
   +0x1A u16  type (loader dispatch index, exe 0x8003897C)
payload: mode 3 -> 16-byte prefix (u32 psize+0x10 rounded, u32 3, u32 ?, u32 0) + LZ stream
```

Exe: entry getter 0x8003885C, iterator 0x8003897C, unpacker 0x8003909C (mode jump table
0x80011194), LZ decoder 0x80010004 (hand-written asm).

## LZ (mode 3, `tools/grlz.py`)

Kosinski-like. 16-bit LE descriptor, bits LSB first; after the 16th bit is consumed the
next descriptor is read immediately (before that item's data).

```
1            literal byte
0 0 b1 b0    short match: count 2 + b1b0, offset = next byte (1..255)
0 1          long match: lo, hi; offset = lo | (hi & 0xF8) << 5 (13 bit)
             count = (hi & 7) + 2; if (hi & 7) == 0: n = next byte; n=0 end, n=1 no-op, else n+1
```

`grlz.lz_compress` produces streams the game's decoder accepts (self-tested round trip).

## Overlays (`bin/*.bin`)

Raw code+data, no header. Load addresses: `title`, `game`, `briefing`, `flight`, `debug`
at 0x8008B7A8; `battle` at 0x800A97A8; `mapNN` at 0x800F87A8.

## Map event scripts (`mapef/mformNN.pac` -> `MFORMNN.BIN`)

Referenced by the exe as `MapEf/MFormNN.pac` (`MFormDb` = debug). The `m_formNN` files and
`mapedit/` are not referenced (unused leftovers).

```
+0      u32 section_offset[] terminated by 0
        strings (NUL-terminated Shift-JIS with control codes)
        bytecode of all sections
        section headers (0x54 bytes each; +0x4C u32 = code offset in this file)
```

Bytecode: 1-byte opcode, fixed length per opcode (table at exe 0x80082990, 62 opcodes;
handlers at 0x800829D0, interpreter 0x80070114). Opcode 0x00 (8 bytes) holds a u32 string
offset at +4; it is the only opcode that points at text. A linear decode of the code area
of every MFORM file ends exactly at the first section header.

### Text control codes (dialogue)

| code | meaning (provisional) |
| --- | --- |
| `$fNNx` | face / portrait NN, expression x |
| `$sNN` | speed / wait (`$s00`, `$s05`, `$s13`, `$s80`) |
| `$/` | wait for button / page |
| `%N` ... `%0` | colour N (speaker names use `%2`) |
| `\n` | literal backslash + n = line break |
| `@NN` | icon (string drawer) |

## Other text

| file | contents |
| --- | --- |
| `mapsys/briefing.pac` `BRIEFING.BIN` | chapter titles and briefings, offset table at start |
| `mapsys/mcn_prm.pac` `MCN_PRM2.BIN` | unit / weapon records with names (fixed fields) |
| `mapsys/mcn_prm.pac` / `mapalway.pac` `PIL_PRM.BIN` | pilot records with names |
| `prog00/kt15v.pac` `HT15V.BIN` | battle attack shouts |
| exe, `bin/briefing.bin`, `title.bin`, `game.bin`, `flight.bin`, `debug.bin`, `mapNN.bin` | UI strings, fixed slots |

## Font

`bin/setup.pac`: `FONT12_0` (digits, Latin, hiragana; symbols in the right 5 columns),
`FONT12_1` (katakana), `FONT12J0/1/2` (kanji), `FONT8` (8x8 ASCII/half-width kana),
`FNT_CLUT`. 4bpp, 12x12 cells. VRAM: FONT12_0 (960,385), FONT12_1 (960,316),
J0 (896,256), J1 (832,256), J2 (704,128), FONT8 (960,256), CLUT (960,505).

Exe text routines:

| addr | routine |
| --- | --- |
| 0x8004DDFC | `PrintStr(x, y, str, attr)` -> 0x8004DE34 with max count 0xFF |
| 0x8004DE34 | string drawer: `%X` colour, `@XY` icon, SJIS pairs, ASCII; fixed advance 12 (24 double) |
| 0x8004DA64 | draw one glyph (code): ASCII -> full-width via table 0x8007F5C4, 82xx -> FONT12_0, 83xx -> FONT12_1, 81xx symbol lookup, kanji tables |
| 0x8004D6DC | sprite emit: descriptor {+0 tpage, +2 u0, +3 v0, +4 clut, +6 per-row} |
| 0x8004D49C | 8x8 string (FONT8), advance 8 |
| 0x8004E104 | display length of a string (chars) |
| 0x8004E1B8 | 12px number printer |
| 0x8004DCF4 | is SJIS lead byte |

Font descriptors (exe data): 0x8007F544 symbols (u0 0xC0, 5/row, code list ptr +8),
0x8007F550 FONT12_0 (16/row, index = lo - 0x50), 0x8007F55C FONT12_1 (lo - 0x40),
0x8007F574.. kanji pages (0x14 each).

Original bug: ASCII table maps `x` to 0x8290 (ｐ).

## Battle dialogue (prog00/<unit>.pac)

Each battle unit pack holds `TMV.PAC` (a nested PAC, stored or LZ-packed) whose `<UNIT>.BIN`
(LZ) contains the pilot table used in that unit's battles; `kt15v.pac` keeps `HT15V.BIN` at
the top level. 114 files, 408 unique lines. A pilot block is a name label (often a single
kanji such as 號 / 翔 / 凱 / 茜 / 椿 / 楓, or a full name) followed by hit reactions, a defeat
line, then attack calls and taunts. Strings are NUL-terminated Shift-JIS in 4-byte slots and
referenced by u32 file offsets (no control codes, no line breaks). Two strings (超ウエポン砲発射！,
シュワルツ…。) have no pointer.

The battle loader (battle.bin, `TmdMocVmd_Unpac` / `UNPAC_Open2`) allocates each entry with
the tagged heap allocator 0x8002DE20(size, tag), so a BIN may grow; `tools/battletext.py`
packs longer lines into free space of the same file first (unused tails, slots of moved
lines) and appends only the rest (~0.9 KB per file with the current English).
