"""Rebuild only the status screen's drawing routines, within their original span.

All input, model loading, unit data and battle calculations remain native.
Run without --apply to inspect the generated region and layout bounds.
"""
import argparse
import json
from pathlib import Path
import struct

import masm
import vwf

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x8008B7A8
START = 0x800982B8
END = 0x8009A2D8
FLAGS = 0x3800000E
BODY_FLAGS = 0x3200000E
COLORS = {'panel': (94, 96, 207), 'pilot': (88, 200, 128), 'weapon': (255, 80, 120), 'footer': (47, 48, 103),
          'border': (94, 96, 207), 'select': (48, 32, 160),
          'track': (31, 47, 62), 'hp': (229, 82, 86), 'en': (45, 201, 220),
          'stat': (255, 176, 80), 'stat_0': (255, 176, 80), 'stat_1': (80, 255, 96),
          'stat_2': (255, 240, 80), 'stat_3': (112, 128, 255)}
# Native blue reverse-L: original right block plus the narrow left strip.
# The strip starts below occupied pilot rows on Pilot; the footer completes
# the lower arm. Never replace this with a bordered preview rectangle.
RECTS = {'body_left': (30, 34, 184, 324), 'body_right': (229, 46, 247, 312),
         'weapon_detail': (280, 104, 194, 254), 'unit_tab': (218, 19, 120, 27),
         'operating': (36, 164, 172, 26),
         'preview_strip': (218, 46, 11, 312)}
# Keep the game's form/combination sprite logic, including its linked panels.
NATIVE_ICON_ROUTINES = {'native_unit_icon': (0x800985B4, 0x80098650),
                        'native_form_row': (0x80098980, 0x80098D1C)}


class Source:
    def __init__(self):
        self.lines = []
        self.strings = {}
        self.rects = dict(RECTS)

    def add(self, source):
        self.lines.append(source)

    def string(self, value):
        if value not in self.strings:
            self.strings[value] = f'text_{len(self.strings)}'
        return self.strings[value]

    def text(self, x, y, value, *, small=False, body=False, secondary=False, color=0):
        pointer = f'la a2, {self.string(value)}' if isinstance(value, str) else value[0]
        self.add(f'li a0, {x}\nli a1, {y-3 if small else y}\n{pointer}\nli a3, {(0x3600000E if secondary else 0x3400000E if small else BODY_FLAGS if body else FLAGS) | color << 16}\njal 0x8004DDFC\nnop')

    def fit(self, x, y, pointer, width=208, color=0):
        self.add(f'li a0, {x}\nli a1, {y}\n{pointer}\nli a3, {width | color << 16}\njal fit_text\nnop')

    def number(self, right, y, load, color=0, compact=False):
        self.add(f'li a0, {right}\nli a1, {y}\n{load}\nli a3, {48+color+(0x100 if compact else 0)}\njal right_number\nnop')

    def panel(self, name):
        self.add(f'la a0, rect_{name}\njal panel\nnop')

    def func(self, name, registers=range(8)):
        self.registers = tuple(registers)
        self.add(f'{name}:\naddiu sp, sp, -0xC0\nsw ra, 0xBC(sp)')
        for i in self.registers:
            self.add(f'sw s{i}, {0xB8-i*4}(sp)')

    def ret(self):
        for i in self.registers:
            self.add(f'lw s{i}, {0xB8-i*4}(sp)')
        self.add('lw ra, 0xBC(sp)\njr ra\naddiu sp, sp, 0xC0')


def source():
    s = Source()
    s.func('status_draw', (0, 1, 2, 3))
    s.add('move s0, a0\naddiu s1, s0, 0x4C\nlh a0, 0x4A(s0)\njal 0x80057154\nnop\nmove s2, v0')
    s.add('jal preview_background\nnop')
    # Each bucket gets a full-screen draw environment, after all its primitives
    # have been queued (the native linked lists execute in reverse insertion order).
    s.add('addiu a0, s0, 0x18\njal 0x80097E9C\nnop')
    s.add('lw t0, 0xC(s0)\nnop\nbeqz t0, main_pilot\nnop\nli t1, 1\nbeq t0, t1, main_unit\nnop\njal weapons_page\nnop\nb main_footer\nnop\nmain_pilot:\nlw t0, 0(s0)\nnop\nandi t0, t0, 0x10\nbeqz t0, main_footer\nnop\njal pilot_page\nnop\nb main_footer\nnop\nmain_unit:\njal unit_page\nnop\nmain_footer:\nlw t0, 0(s0)\nnop\nandi t0, t0, 0x10\nbeqz t0, main_header\nnop\njal footer\nnop\nmain_header:')
    s.add('jal form_icons\nnop')
    s.add('jal title_tab\nnop')
    s.fit(222, 22, 'move a2, s2', 224, color=5)
    s.add('li s3, 4\nenv_loop:\nli t0, 0x80089A8C\nlw t0, 0(t0)\nsll t1, s3, 2\naddu a0, t0, t1\njal 0x8003BBDC\nmove a1, zero\naddiu s3, s3, 1\nslti t0, s3, 16\nbnez t0, env_loop\nnop')
    s.ret()

    s.func('form_icons', (3, 4))
    s.add('lw t0, 0(s0)\nnop\nandi t0, t0, 0x10\nbeqz t0, form_icons_return\nnop\nmove s3, zero\nform_icons_loop:\nmove a0, s0\nmove a1, s3\nli a2, 30\nli t0, 97\nmultu s3, t0\nmflo a3\naddiu a3, a3, 50\nlw t0, 0xC(s0)\nnop\nsltiu t0, t0, 1\nsw t0, 0x10(sp)\njal native_form_row\nnop\nbeqz v0, form_icons_done\nnop\naddiu s3, s3, 1\nslti t0, s3, 3\nbnez t0, form_icons_loop\nnop\nform_icons_done:\nslti t0, s3, 2\nbnez t0, form_icons_return\nnop\nlhu t0, 0x2E(s2)\nnop\nandi t0, t0, 0x10\nbeqz t0, form_icons_return\nnop\naddiu t0, s3, -1\nli t1, 97\nmultu t0, t1\nmflo t0\nla s3, icon_links_vertical\nsh t0, 6(s3)\nli s4, 3\nicon_links_loop:\nmove a0, s3\nli a1, 0x8008CFB8\nli a2, 11\njal translucent_rectangle\nnop\naddiu s3, s3, 8\naddiu s4, s4, -1\nbnez s4, icon_links_loop\nnop\nform_icons_return:')
    s.ret()

    s.func('footer', (3, 4, 5))
    s.add('jal footer_background\nnop')
    s.add('li a0, 40\nli a1, 366\nlw a2, 0x14(s1)\nlw a3, 0x10(s1)\nla t0, color_hp\nsw t0, 0x10(sp)\njal resource_bar\nnop')
    s.text(40, 380, 'HP', body=True, color=1)
    s.add('addiu a0, sp, 0x20\nla a1, fmt_pair_hp\nlw a2, 0x14(s1)\nlw a3, 0x10(s1)\njal 0x8001ACB8\nnop\nli a0, 216\nli a1, 380\naddiu a2, sp, 0x20\njal right_text\nnop')
    s.add('li a0, 40\nli a1, 408\nlhu a2, 0x1A(s1)\nlhu a3, 0x18(s1)\nla t0, color_en\nsw t0, 0x10(sp)\njal resource_bar\nnop')
    s.add('lbu t0, 0x2D(s2)\nla a2, text_energy\nandi t0, t0, 1\nbeqz t0, footer_energy\nnop\nla a2, text_getter_ray\nfooter_energy:\nli a0, 40\nli a1, 422\nli a3, 0x3202000E\njal 0x8004DDFC\nnop')
    s.add('addiu a0, sp, 0x20\nla a1, fmt_pair_en\nlhu a2, 0x1A(s1)\nlhu a3, 0x18(s1)\njal 0x8001ACB8\nnop\nli a0, 216\nli a1, 422\naddiu a2, sp, 0x20\njal right_text\nnop')
    stat_labels = [s.string(name) for name in ('Def', 'Move', 'Accuracy', 'Eva')]
    s.add('move s3, zero\nli s4, 366\nla s5, footer_stat_rows\nfooter_stat_loop:\nli a0, 232\naddiu a1, s4, 5\nlw a2, 0(s5)\nlw t0, 4(s5)\nli a3, 0x3400000E\nsll t0, t0, 16\nor a3, a3, t0\njal 0x8004DDFC\nnop\nli a0, 316\naddiu a1, s4, 5\nsll t0, s3, 1\naddu t0, s1, t0\nlhu a2, 0x1C(t0)\nlw a3, 4(s5)\nnop\naddiu a3, a3, 304\njal right_number\nnop\nli a0, 322\naddiu a1, s4, 8\nsll t0, s3, 1\naddu t0, s1, t0\nlhu a2, 0x1C(t0)\nli a3, 1000\nlw t0, 8(s5)\nnop\nsw t0, 0x10(sp)\njal stat_bar\nnop\naddiu s3, s3, 1\naddiu s4, s4, 21\naddiu s5, s5, 12\nslti t0, s3, 4\nbnez t0, footer_stat_loop\nnop')
    s.ret()

    s.func('pilot_page', (3, 4, 5, 6, 7))
    s.add('move s3, zero\npilot_loop:\nsll t0, s3, 1\naddu t0, s0, t0\nlh s4, 0xA8(t0)\nnop\nbltz s4, pilot_done\nnop\nlw a0, 0x44(s0)\nmove a1, s4\njal 0x8005D284\nnop\nmove s5, v0\nli t0, 97\nmultu s3, t0\nmflo s6\naddiu s6, s6, 50')
    s.add('jal pilot_background\nnop')
    s.add('lw a0, 0x44(s0)\nmove a1, s4\njal 0x8005D25C\nnop\nmove a2, v0\nli a0, 34\naddiu a1, s6, 2\nli a3, 0x3200000E\njal 0x8004DDFC\nnop')
    s.add('move a2, s4\nmove a3, s3\nli a0, 32\naddiu a1, s6, 27\njal portrait\nnop')
    s.add('lh a0, 4(s5)\njal 0x8005D4C4\nnop\nla a1, fmt_pilot_no_exp\nbeqz v0, pilot_format\nnop\nla a1, fmt_pilot_exp\npilot_format:\naddiu a0, sp, 0x30\nlh a2, 6(s5)\nlw a3, 8(s5)\njal 0x8001ACB8\nnop\nli a0, 82\naddiu a1, s6, 30\naddiu a2, sp, 0x30\nli a3, 0x3400000E\njal 0x8004DDFC\nnop')
    s.add('lb a0, 0xC(s5)\njal 0x8005C9C0\nnop\nli a0, 80\naddiu a1, s6, 54\nmove a2, v0\nli a3, 0x3400000E\njal 0x8004DDFC\nnop')
    s.add('lb t0, 0xC(s5)\nnop\nbeqz t0, pilot_skill_done\nnop\naddiu a0, sp, 0x30\nla a1, fmt_level\nlb a2, 0xD(s5)\njal 0x8001ACB8\nnop\nli a0, 112\naddiu a1, s6, 76\naddiu a2, sp, 0x30\nli a3, 0xA\njal 0x8004DDFC\nnop\npilot_skill_done:')
    s.add('move s7, zero\npilot_stats:\nsll t0, s7, 2\nli t1, 0x800A9484\naddu t0, t0, t1\nlw a2, 0(t0)\nli t0, 14\nmultu s7, t0\nmflo t0\naddu a1, s6, t0\naddiu a1, a1, 22\nli a0, 160\nli a3, 0xA\njal 0x8004DDFC\nnop\nsll t0, s7, 1\naddu t0, s5, t0\nlhu a2, 0x10(t0)\nli t0, 14\nmultu s7, t0\nmflo t0\naddu a1, s6, t0\naddiu a1, a1, 22\nli a0, 210\njal medium_number\nnop\naddiu s7, s7, 1\nslti t0, s7, 5\nbnez t0, pilot_stats\nnop\naddiu s3, s3, 1\nslti t0, s3, 3\nbnez t0, pilot_loop\nnop\npilot_done:')
    s.ret()

    s.func('unit_page', (3, 4, 5))
    s.add('la a0, unit_blocks\nli a1, 5\nmove a2, zero\njal background_blocks\nnop')
    s.fit(34, 40, 'move a2, s2', 176, color=5)
    for x, right, y, name, off in ((40,124,84,'HP',0x18),(40,124,116,'EN',0x1A),(128,208,84,'Arm.',0x1C),(128,208,116,'Move',0x1E)):
        s.text(x, y+7, name, small=True)
        s.number(right, y+4, f'lh a2, {off}(s2)', compact=True)
    s.text(40, 148, 'Operates In', small=True, color=5)
    # Center the compact operating-terrain text in its native 172x26 box.
    s.add('lb t0, 0x20(s2)\nlb t1, 0x23(s2)\nnop\nbnez t1, unit_operating\nnop\naddiu t0, t0, 3\nunit_operating:\nsll t0, t0, 2\nla t1, operations_names\naddu t0, t0, t1\nlw a2, 0(t0)\nnop\nmove a0, a2\nla a1, status_small_advance\njal measure_text\nnop\nli a0, 244\nsubu a0, a0, v0\nsra a0, a0, 1\nli a1, 170\nli a3, 0x3400000E\njal 0x8004DDFC\nnop')
    s.text(40, 204, 'Terrain', small=True, color=5)
    s.add('move s3, zero\nterrain_loop:\nandi t0, s3, 1\nli t1, 88\nmultu t0, t1\nmflo s4\naddiu s4, s4, 40\nsrl t0, s3, 1\nli t1, 26\nmultu t0, t1\nmflo s5\naddiu s5, s5, 228\nmove a0, s3\njal 0x8008F6B4\nnop\nmove a2, v0\nmove a0, s4\naddiu a1, s5, 4\nli a3, 0xA\njal 0x8004DDFC\nnop\naddu t0, s2, s3\nlb t0, 0x21(t0)\nmove a2, zero\naddiu t1, t0, 1\nsltiu t1, t1, 2\nbnez t1, terrain_value\nnop\nli t1, 1600\ndiv t1, t0\nmflo a2\nterrain_value:\naddiu a0, sp, 0x20\nla a1, fmt_percent\njal 0x8001ACB8\nnop\naddiu a0, s4, 84\naddiu a1, s5, 4\naddiu a2, sp, 0x20\njal compact_right_text\nnop\naddiu s3, s3, 1\nslti t0, s3, 9\nbnez t0, terrain_loop\nnop')
    s.ret()

    s.func('weapons_page', (3, 4, 5, 6, 7))
    s.add('la a0, weapon_blocks\nli a1, 4\nmove a2, zero\njal background_blocks\nnop')
    s.text(36, 40, 'Weapons')
    s.add('lw t0, 0x38(s0)\nnop\nbeqz t0, weapons_done\nnop\nlw a0, 0x54(t0)\nlh a1, 0x34(s0)\naddiu a2, sp, 0x20\naddiu a3, sp, 0x40\njal 0x8009C614\nnop\nmove s3, v0\nblez s3, weapons_done\nnop\nmove s5, zero\nweapon_list:\nsll t0, s5, 2\naddiu t1, sp, 0x40\naddu t0, t0, t1\nlw s4, 0(t0)\nli t0, 36\nmultu s5, t0\nmflo s7\naddiu s7, s7, 64\nlh t0, 0x12(s0)\nnop\nbne t0, s5, weapon_list_text\nnop\nli t0, 38\nsh t0, 0x80(sp)\naddiu t0, s7, -2\nsh t0, 0x82(sp)\nli t0, 168\nsh t0, 0x84(sp)\nli t0, 34\nsh t0, 0x86(sp)\naddiu a0, sp, 0x80\nla a1, color_select\nli a2, 12\njal rectangle\nnop\nweapon_list_text:\nli a0, 40\nmove a1, s7\nmove a2, s4\nli a3, 0x1000A4\njal fit_text\nnop\naddiu s5, s5, 1\nslt t0, s5, s3\nbnez t0, weapon_list\nnop\nlh t0, 0x12(s0)\naddiu t1, sp, 0x40\nsll t2, t0, 2\naddu t1, t1, t2\nlw s4, 0(t1)\naddiu t1, sp, 0x20\nsll t2, t0, 1\naddu t1, t1, t2\nlh s6, 0(t1)')
    s.fit(288, 110, 'move a2, s4', 176)
    s.text(288, 153, 'Attack', small=True, color=5)
    s.add('lw t0, 0x38(s0)\nlh a1, 0x34(s0)\nlw a0, 0x54(t0)\nmove a2, s6\njal 0x800A0A00\nnop\nmove a2, v0\nbltz s6, weapon_power_plain\naddiu a0, sp, 0x60\nlh a3, 0x20(s4)\nla a1, fmt_power\nsubu t0, a2, a3\nsw t0, 0x10(sp)\njal 0x8001ACB8\nnop\nb weapon_power_text\nnop\nweapon_power_plain:\nla a1, fmt_number\njal 0x8001ACB8\nnop\nweapon_power_text:')
    s.text(328, 153, ('addiu a2, sp, 0x60',), small=True)
    s.add('lbu t0, 0x2D(s2)\nla a2, text_en_cost\nandi t0, t0, 1\nbeqz t0, cost_label\nnop\nla a2, text_ge_cost\ncost_label:\nli a0, 288\nli a1, 184\nli a3, 0xA\njal 0x8004DDFC\nnop')
    s.number(380, 184, 'lh a2, 0x26(s4)', compact=True)
    s.text(388, 187, 'Kind', small=True)
    s.add('lhu t0, 0x28(s4)\nli a2, 0x8008D1BC\nandi t1, t0, 0x400\nbnez t1, kind_label\nnop\nli a2, 0x8008D040\nandi t1, t0, 2\nbeqz t1, kind_label\nnop\nli a2, 0x8008D038\nkind_label:\nli a0, 468\nli a1, 184\njal compact_right_text\nnop')
    s.text(288, 221, 'Sea', small=True)
    s.add('lhu t0, 0x24(s4)\nmove a2, zero\nandi t0, t0, 8\nbeqz t0, sea_value\nnop\nlh a2, 0x22(s4)\nsea_value:\naddiu a0, sp, 0x60\nla a1, fmt_percent\njal 0x8001ACB8\nnop\nli a0, 380\nli a1, 218\naddiu a2, sp, 0x60\njal compact_right_text\nnop')
    s.text(388, 221, 'Terr.', small=True)
    s.add('lh a0, 0x24(s4)\njal 0x80057994\nnop\nli a0, 468\nli a1, 218\nmove a2, v0\njal compact_right_text\nnop')
    s.text(288, 250, 'Range', secondary=True)
    s.text(388, 250, 'Area', secondary=True)
    s.text(288, 289, 'Shp', small=True)
    s.add('lhu t0, 0x2A(s4)\nli a2, 0x8008D14C\nsll t1, t0, 3\nsubu t1, t1, t0\naddu a2, a2, t1\nli a0, 380\nli a1, 286\njal compact_right_text\nnop')
    s.text(288, 323, 'Rng', small=True)
    s.add('lbu a2, 0x2C(s4)\nlbu a3, 0x2D(s4)\njal range_format\naddiu a0, sp, 0x60\nli a0, 380\nli a1, 320\naddiu a2, sp, 0x60\njal compact_right_text\nnop')
    s.text(388, 289, 'Shp', small=True)
    s.add('lhu t0, 0x2E(s4)\nli a2, 0x8008D164\nsll t1, t0, 3\naddu t1, t1, t0\naddu a2, a2, t1\nli a0, 468\nli a1, 286\njal compact_right_text\nnop')
    s.text(388, 323, 'Size', small=True)
    s.add('lbu a2, 0x30(s4)\nlbu a3, 0x31(s4)\naddiu a2, a2, 1\naddiu a3, a3, 1\njal range_format\naddiu a0, sp, 0x60\nli a0, 468\nli a1, 320\naddiu a2, sp, 0x60\njal compact_right_text\nnop\nweapons_done:')
    s.ret()

    # Helpers preserve the status context in s0-s2, as do all native callees.
    s.add(HELPERS)
    for name, (start, end) in NATIVE_ICON_ROUTINES.items():
        s.add(f'.align 4\n{name}:\n.space {end-start}')
    s.add('footer_stat_rows:')
    for i, label in enumerate(stat_labels):
        s.add(f'.word {label}, {(5,3,4,2)[i]}, color_stat_{i}')
    # Color-pointer bit 0 selects translucency; opaque insets use native colors.
    for name, rows in {
        'pilot_blocks': [(30,0,184,94,0x8008CFA9), (158,4,54,89,0x8008CFAC), (72,48,84,45,0x8008CFAC)],
        'unit_blocks': [(30,34,184,324,0x8008CFC1), (80,80,46,64,0x8008CFC4), (172,80,38,64,0x8008CFC4), (36,164,172,26,0x8008CFC4), (36,222,172,132,0x8008CFC4)],
        'weapon_blocks': [(30,34,184,324,0x8008CFCD), (280,104,194,254,0x8008CFCD), (36,60,172,294,0x8008CFC8), (284,128,186,226,0x8008CFD0)],
    }.items():
        s.add(f'{name}:')
        for x,y,w,h,color in rows:
            s.add(f'.half {x},{y},{w},{h}\n.word {color}')
    s.add('native_footer_rects:\n.half 34,362,438,88, 30,358,446,4, 30,450,446,4, 30,362,4,88, 472,362,4,88')
    s.add('icon_links_vertical:\n.half 270,80,4,194, 261,76,22,4, 283,51,38,51')
    for value in ('Air', 'Air/Land', 'Land/Sea', 'Land'):
        s.string(value)
    aliases = {'text_energy': 'Energy', 'text_getter_ray': 'Getter Ray', 'text_en_cost': 'EN Cost',
               'text_ge_cost': 'GE Cost'}
    for name, value in aliases.items():
        s.add(f'{name}:\n.ascii {json.dumps(value)}\n.byte 0')
    s.add('fmt_pair_hp:\n.ascii "%d/%%1%d%%0"\n.byte 0\nfmt_pair_en:\n.ascii "%d/%%2%d%%0"\n.byte 0\nfmt_tinted_number:\n.ascii "%%%c%d%%0"\n.byte 0\nfmt_number:\n.ascii "%d"\n.byte 0\nfmt_level:\n.ascii "Lv %d"\n.byte 0\nfmt_power:\n.ascii "%d (%d+%d)"\n.byte 0\nfmt_range:\n.ascii "%d-%d"\n.byte 0\nfmt_percent:\n.ascii "%d"\n.byte 0x81, 0x93, 0\n.align 4')
    s.add('fmt_pilot_exp:\n.ascii "Lv%02d Ex%03d"\n.byte 0\nfmt_pilot_no_exp:\n.ascii "Lv%02d Ex---"\n.byte 0')
    s.add('.align 4\noperations_names:\n.word '+', '.join(s.strings[v] for v in ('Air', 'Air/Land', 'Land/Sea', 'Air', 'Air/Land', 'Land')))
    for value, label in s.strings.items():
        s.add(f'{label}:\n.ascii {json.dumps(value)}\n.byte 0')
    s.add('.align 4')
    for name, color in COLORS.items():
        s.add(f'color_{name}:\n.byte {color[0]}, {color[1]}, {color[2]}, 0')
    for name, rect in s.rects.items():
        if name in ('body_left', 'weapon_detail', 'operating'): continue
        s.add(f'rect_{name}:\n.half '+', '.join(map(str, rect)))
    return '\n'.join(s.lines).replace('0x3800000A', '0x3800000E').replace('0x3805000A', '0x3805000E').replace('li a3, 0xA\n', 'li a3, 0x3400000E\n').replace('addiu a1, a1, 26\nli a0, 176', 'addiu a1, a1, 22\nli a0, 176')


HELPERS = r'''
; Plain colored rectangles, linked at an explicit native primary-OT depth.
rectangle:
    move t2, zero
    b rectangle_common
    nop
translucent_rectangle:
    addiu sp, sp, -0x18
    sw ra, 0x10(sp)
    li t2, 0x10
    jal rectangle_common
    nop
    move a2, a3
    move a0, zero
    jal 0x8004BDF0
    move a1, zero
    lw ra, 0x10(sp)
    jr ra
    addiu sp, sp, 0x18
rectangle_common:
    li t0, 0x80089A8C
    lw t0, 0(t0)
    sll a2, a2, 2
    addu a3, t0, a2
    j 0x8004BE74
    move a2, t2
footer_background:
    addiu sp, sp, -0x20
    sw ra, 0x1C(sp)
    la a0, native_footer_rects
    li a1, 0x8008CFB4
    li a2, 11
    jal translucent_rectangle
    nop
    la t0, native_footer_rects
    addiu t0, t0, 8
    sw t0, 0x10(sp)
    li t0, 4
    sw t0, 0x14(sp)
footer_frame_loop:
    lw a0, 0x10(sp)
    li a1, 0x8008CFB0
    li a2, 5
    jal translucent_rectangle
    nop
    lw t0, 0x10(sp)
    lw t1, 0x14(sp)
    addiu t0, t0, 8
    addiu t1, t1, -1
    sw t0, 0x10(sp)
    sw t1, 0x14(sp)
    bnez t1, footer_frame_loop
    nop
panel_return:
    lw ra, 0x1C(sp)
    jr ra
    addiu sp, sp, 0x20
preview_background:
    addiu sp, sp, -0x28
    sw ra, 0x24(sp)
    la a0, rect_body_right
    li a1, 0x8008CFB0
    li a2, 5
    jal translucent_rectangle
    nop
    la t0, rect_preview_strip
    lw t1, 0(t0)
    lw t2, 4(t0)
    sw t1, 0x18(sp)
    sw t2, 0x1C(sp)
    lw t0, 0xC(s0)
    nop
    bnez t0, preview_strip_draw
    nop
    lw t0, 0(s0)
    nop
    andi t0, t0, 0x10
    beqz t0, preview_strip_draw
    nop
    move t0, zero
preview_pilot_count:
    sll t1, t0, 1
    addu t1, s0, t1
    lh t1, 0xA8(t1)
    nop
    bltz t1, preview_count_done
    nop
    addiu t0, t0, 1
    slti t1, t0, 3
    bnez t1, preview_pilot_count
    nop
preview_count_done:
    li t1, 97
    multu t0, t1
    mflo t0
    lh t1, 0x1A(sp)
    lh t2, 0x1E(sp)
    addu t1, t1, t0
    subu t2, t2, t0
    sh t1, 0x1A(sp)
    sh t2, 0x1E(sp)
preview_strip_draw:
    addiu a0, sp, 0x18
    li a1, 0x8008CFB0
    li a2, 5
    jal translucent_rectangle
    nop
    lw ra, 0x24(sp)
    jr ra
    addiu sp, sp, 0x28
; Original pilot card layers and the native right-facing arrow texture
; (status resource +0x70), matching 0x80099134..0x8009922C.
pilot_background:
    addiu sp, sp, -0x30
    sw ra, 0x2C(sp)
    la a0, pilot_blocks
    li a1, 3
    move a2, s6
    jal background_blocks
    nop
    li t0, 214
    sh t0, 0x18(sp)
    sh s6, 0x1A(sp)
    addiu a0, sp, 0x18
    move a1, zero
    lw a2, 0x3C(s0)
    li a3, 0x10
    addiu a2, a2, 0x70
    li t0, 0x80089A8C
    lw t0, 0(t0)
    nop
    addiu t0, t0, 44
    sw t0, 0x10(sp)
    jal 0x8004BD04
    nop
    lw ra, 0x2C(sp)
    jr ra
    addiu sp, sp, 0x30
background_blocks:
    addiu sp, sp, -0x38
    sw ra, 0x34(sp)
    sw s3, 0x30(sp)
    sw s4, 0x2C(sp)
    sw s5, 0x28(sp)
    move s3, a0
    move s4, a1
    move s5, a2
background_block_loop:
    lw t0, 0(s3)
    lw t1, 4(s3)
    sw t0, 0x18(sp)
    sw t1, 0x1C(sp)
    lh t0, 0x1A(sp)
    lw a1, 8(s3)
    addu t0, t0, s5
    sh t0, 0x1A(sp)
    andi t0, a1, 1
    subu a1, a1, t0
    addiu a0, sp, 0x18
    beqz t0, background_opaque
    li a2, 11
    li a2, 10
    jal translucent_rectangle
    nop
    b background_block_done
    nop
background_opaque:
    jal rectangle
    nop
background_block_done:
    addiu s3, s3, 12
    addiu s4, s4, -1
    bnez s4, background_block_loop
    nop
    lw s5, 0x28(sp)
    lw s4, 0x2C(sp)
    lw s3, 0x30(sp)
    lw ra, 0x34(sp)
    jr ra
    addiu sp, sp, 0x38
title_tab:
    addiu sp, sp, -0x38
    sw ra, 0x34(sp)
    jal text_width
    move a0, s2
    li t0, 224
    slt t1, t0, v0
    beqz t1, tab_width_ready
    nop
    move v0, t0
tab_width_ready:
    la a0, rect_unit_tab
    addiu v0, v0, 8
    sh v0, 4(a0)
    addiu a1, sp, 0x10
    jal 0x8004CB7C
    nop
    lhu t0, 0x1C(sp)
    nop
    addiu t0, t0, 12
    sh t0, 0x1C(sp)
    addiu a0, sp, 0x10
    li a1, 0x8008CFB0
    li a2, 0x10
    li t0, 0x80089A8C
    lw a3, 0(t0)
    nop
    jal 0x8004C47C
    addiu a3, a3, 20
    li a2, 0x80089A8C
    lw a2, 0(a2)
    nop
    addiu a2, a2, 20
    move a0, zero
    jal 0x8004BDF0
    move a1, zero
    lw ra, 0x34(sp)
    jr ra
    addiu sp, sp, 0x38
; Widths for status body text only (16x20); headings/compact text use their own modes.
text_width:
    la a1, status_advance
measure_text:
    addiu sp, sp, -0x30
    sw ra, 0x2c(sp)
    sw s0, 0x28(sp)
    sw s1, 0x24(sp)
    move s0, a0
    move s1, zero
    sw a1, 0x20(sp)
tw_loop:
    lbu a0, 0(s0)
    nop
    beqz a0, tw_done
    nop
    li t0, 37
    beq a0, t0, tw_control
    nop
    sltiu t0, a0, 0x80
    bnez t0, tw_ascii
    nop
    sll a0, a0, 8
    lbu t0, 1(s0)
    addiu s0, s0, 1
    or a0, a0, t0
tw_ascii:
    jal font_width
    nop
    lw t0, 0x20(sp)
    nop
    addu t0, t0, v0
    lbu v0, 0(t0)
    addiu s0, s0, 1
    addu s1, s1, v0
    b tw_loop
    nop
tw_control:
    b tw_loop
    addiu s0, s0, 2
tw_done:
    move v0, s1
    lw ra, 0x2c(sp)
    lw s0, 0x28(sp)
    lw s1, 0x24(sp)
    jr ra
    addiu sp, sp, 0x30
medium_number:
    li a3, 304
    j right_number
    nop
right_number:
    addiu sp, sp, -0x60
    sw ra, 0x5c(sp)
    sw a0, 0x58(sp)
    sw a1, 0x54(sp)
    sw a3, 0x50(sp)
    addiu a0, sp, 0x20
    move t0, a2
    andi a2, a3, 0xFF
    move a3, t0
    la a1, fmt_tinted_number
    jal 0x8001ACB8
    nop
    lw a0, 0x58(sp)
    lw a1, 0x54(sp)
    addiu a2, sp, 0x20
    lw t0, 0x50(sp)
    la t1, right_text
    andi t0, t0, 0x100
    beqz t0, right_number_draw
    nop
    la t1, compact_right_text
right_number_draw:
    jalr t1
    nop
    lw ra, 0x5c(sp)
    jr ra
    addiu sp, sp, 0x60
right_text:
    li a3, 0x3200000E
    la t2, status_advance
    b sized_right_text
    nop
compact_right_text:
    li a3, 0x3400000E
    la t2, status_small_advance
sized_right_text:
    addiu sp, sp, -0x30
    sw ra, 0x2c(sp)
    sw a0, 0x28(sp)
    sw a1, 0x24(sp)
    sw a2, 0x20(sp)
    sw a3, 0x1C(sp)
    move a1, t2
    jal measure_text
    move a0, a2
    lw a0, 0x28(sp)
    lw a1, 0x24(sp)
    lw a2, 0x20(sp)
    lw a3, 0x1C(sp)
    subu a0, a0, v0
    jal 0x8004DDFC
    nop
    lw ra, 0x2c(sp)
    jr ra
    addiu sp, sp, 0x30
range_format:
    beq a2, a3, range_one
    nop
    la a1, fmt_range
    j 0x8001ACB8
    nop
range_one:
    la a1, fmt_number
    j 0x8001ACB8
    nop
; Colored bars: current/max is clamped, with a zero-max guard.
resource_bar:
    lw t0, 0x10(sp)
    li t1, 176
    b bar_start
    nop
stat_bar:
    lw t0, 0x10(sp)
    li t1, 147
bar_start:
    addiu sp, sp, -0x40
    sw ra, 0x3c(sp)
    sw a2, 0x30(sp)
    sw a3, 0x34(sp)
    sw t0, 0x38(sp)
    sw t1, 0x2c(sp)
    sh a0, 0x20(sp)
    sh a1, 0x22(sp)
    sh t1, 0x24(sp)
    li t0, 6
    sh t0, 0x26(sp)
    li t0, 147
    beq t1, t0, bar_no_track
    nop
    addiu a0, sp, 0x20
    la a1, color_track
    jal rectangle
    li a2, 12
bar_no_track:
    lw t0, 0x30(sp)
    lw t1, 0x34(sp)
    lw t2, 0x2c(sp)
    blez t1, bar_done
    nop
    blez t0, bar_done
    nop
    slt t3, t1, t0
    beqz t3, bar_ratio
    nop
    move t0, t1
bar_ratio:
    multu t0, t2
    mflo t0
    divu t0, t1
    mflo t0
    beqz t0, bar_done
    nop
    sh t0, 0x24(sp)
    addiu a0, sp, 0x20
    lw a1, 0x38(sp)
    jal rectangle
    li a2, 13
bar_done:
    lw ra, 0x3c(sp)
    jr ra
    addiu sp, sp, 0x40
; The native face descriptors stay in the already loaded portrait atlas.
portrait:
    addiu sp, sp, -0x70
    sw ra, 0x6c(sp)
    sw a2, 0x60(sp)
    sw a3, 0x64(sp)
    sh a0, 0x20(sp)
    sh a1, 0x22(sp)
    li t0, 38
    sh t0, 0x24(sp)
    li t0, 48
    sh t0, 0x26(sp)
    lw t0, 0x14(s0)
    nop
    beqz t0, portrait_fallback
    nop
    lw a0, 0x44(s0)
    move a1, a2
    jal 0x8005D3E4
    nop
    addiu a0, sp, 0x40
    sll a1, v0, 16
    sra a1, a1, 16
    li a2, -1
    lw a3, 0x64(sp)
    jal 0x8005C608
    nop
    beqz v0, portrait_done
    nop
    addiu t1, sp, 0x40
    b portrait_descriptor
    nop
portrait_fallback:
    lw a2, 0x60(sp)
    li t1, 19
    bne a2, t1, portrait_index
    nop
    lw a0, 0x44(s0)
    nop
    beqz a0, portrait_next
    nop
    jal 0x8005D6E8
    nop
    bnez v0, portrait_saved_index
    nop
portrait_next:
    lw a2, 0x60(sp)
    nop
    addiu a2, a2, 1
    b portrait_index
    nop
portrait_saved_index:
    lw a2, 0x60(sp)
    nop
portrait_index:
    sll t0, a2, 1
    addu t0, t0, a2
    sll t0, t0, 2
    li t1, 0x8008B5F8
    lw t1, 0(t1)
    nop
    beqz t1, portrait_done
    nop
    addiu t0, t0, 4
    addu t1, t1, t0
portrait_descriptor:
    sw t1, 0x58(sp)
    addiu a0, sp, 0x20
    addiu a1, sp, 0x30
    jal 0x8004CB7C
    nop
    addiu a0, sp, 0x30
    move a1, zero
    lw a2, 0x58(sp)
    li t0, 0x80089A8C
    lw t0, 0(t0)
    move a3, zero
    addiu t0, t0, 0x38
    sw t0, 0x10(sp)
    jal 0x8004C678
    nop
portrait_done:
    lw ra, 0x6c(sp)
    jr ra
    addiu sp, sp, 0x70
; Fit names in two lines, breaking at spaces. Bounded 128-byte line buffer.
fit_text:
    addiu sp, sp, -0xD0
    sw ra, 0xCC(sp)
    sw s0, 0xC8(sp)
    sw s1, 0xC4(sp)
    sw s2, 0xC0(sp)
    sw s3, 0xBC(sp)
    sw s4, 0xB8(sp)
    sw s5, 0xB4(sp)
    sw s6, 0xB0(sp)
    sw s7, 0xAC(sp)
    move s0, a0
    move s1, a1
    move s2, a2
    andi s3, a3, 0xFFFF
    lui t0, 0xF
    and t0, t0, a3
    sw t0, 0x1C(sp)
    lui t0, 0x10
    and t0, t0, a3
    sw t0, 0x18(sp)
    move s7, zero
fit_line:
    addiu s4, sp, 0x20
    move s5, zero
    move s6, zero
    sw zero, 0xA0(sp)
fit_char:
    lbu a0, 0(s2)
    nop
    beqz a0, fit_draw
    nop
    sw a0, 0xA4(sp)
    sltiu t0, a0, 0x80
    bnez t0, fit_width
    li t1, 1
    sll a0, a0, 8
    lbu t0, 1(s2)
    li t1, 2
    or a0, a0, t0
fit_width:
    sw t1, 0xA8(sp)
    jal font_width
    nop
    la t0, status_advance
    addu t0, t0, v0
    lbu t0, 0(t0)
    nop
    addu t0, s5, t0
    slt t1, s3, t0
    bnez t1, fit_break
    nop
    sw s5, 0x14(sp)
    move s5, t0
    lw t0, 0xA4(sp)
    li t1, 32
    bne t0, t1, fit_copy
    nop
    lw t0, 0x14(sp)
    move s6, s4
    sw t0, 0x10(sp)
    addiu t0, s2, 1
    sw t0, 0xA0(sp)
fit_copy:
    lw t1, 0xA8(sp)
    lbu t0, 0(s2)
    addiu s2, s2, 1
    sb t0, 0(s4)
    addiu s4, s4, 1
    li t0, 2
    bne t1, t0, fit_capacity
    nop
    lbu t0, 0(s2)
    addiu s2, s2, 1
    sb t0, 0(s4)
    addiu s4, s4, 1
fit_capacity:
    addiu t0, sp, 0x9C
    sltu t0, s4, t0
    bnez t0, fit_char
    nop
fit_break:
    beqz s6, fit_draw
    nop
    move s4, s6
    lw s2, 0xA0(sp)
    lw s5, 0x10(sp)
fit_draw:
    sb zero, 0(s4)
    move a0, s0
    lw t0, 0x18(sp)
    nop
    beqz t0, fit_positioned
    nop
    bnez s7, fit_center_x
    nop
    lbu t0, 0(s2)
    nop
    bnez t0, fit_two_lines
    nop
    b fit_center_x
    addiu s1, s1, 7
fit_two_lines:
    addiu s1, s1, -1
fit_center_x:
    subu t0, s3, s5
    sra t0, t0, 1
    addu a0, s0, t0
fit_positioned:
    move a1, s1
    addiu a2, sp, 0x20
    li a3, 0x3200000E
    lw t0, 0x1C(sp)
    nop
    or a3, a3, t0
    jal 0x8004DDFC
    nop
    addiu s7, s7, 1
    slti t0, s7, 2
    beqz t0, fit_done
    nop
    lbu t0, 0(s2)
    nop
    beqz t0, fit_done
    nop
    b fit_line
    addiu s1, s1, 16
fit_done:
    lw ra, 0xCC(sp)
    lw s0, 0xC8(sp)
    lw s1, 0xC4(sp)
    lw s2, 0xC0(sp)
    lw s3, 0xBC(sp)
    lw s4, 0xB8(sp)
    lw s5, 0xB4(sp)
    lw s6, 0xB0(sp)
    lw s7, 0xAC(sp)
    jr ra
    addiu sp, sp, 0xD0
'''


def check_fit():
    """Match the native two-line word wrapping for every translated unit/weapon."""
    # Native lists can prepend two special actions. Six ordinary weapons plus
    # those actions fit the eight 36-pixel rows and the local pointer array.
    core = (ROOT/'work/source/disc/SLPS_022.32').read_bytes()
    base = struct.unpack_from('<I', core, 0x18)[0]
    for unit in range(111):
        count = struct.unpack_from('<h', core, 0x800+0x80015BA8-base+unit*58+0x38)[0]
        if not 0 <= count <= 6: raise ValueError(f'Unexpected weapon-list capacity for unit {unit}: {count}')
    widths, _ = vwf.width_tables()
    scaled = (0, 1, 3, 4, 5, 7, 8, 9, 11, 12, 13, 15, 16)
    checked = 0
    for row in json.loads((ROOT/'work/translation/en/ui.en.json').read_text(encoding='utf8')):
        address = int(row['addr'], 16)
        if row['file'] != 'exe' or not 0x800126F4 <= address < 0x800174D0 or not row.get('en'):
            continue
        limit = 164 if address < 0x80015BA8 else 224
        text = row['en']
        if not text.isascii():
            raise ValueError(f"Status fit audit requires Latin text: {row['id']}")
        rest = text
        lines = []
        while rest:
            width = 0
            end = 0
            space = None
            for i, char in enumerate(rest):
                width += scaled[widths[ord(char)-32]]
                if width > limit:
                    break
                end = i+1
                if char == ' ': space = i
            else:
                end = len(rest)
            if end < len(rest) and space is not None:
                lines.append(rest[:space])
                rest = rest[space+1:]
            else:
                if not end: raise ValueError(f"Status glyph wider than panel: {row['id']}")
                lines.append(rest[:end])
                rest = rest[end:]
        if len(lines) > 2 or any(len(line) > 123 for line in lines):
            raise ValueError(f"Status name exceeds two lines: {row['id']}: {text}")
        checked += 1
    if checked < 100: raise ValueError(f'Unexpectedly few status names audited: {checked}')
    return checked


def assemble():
    check_fit()
    _, resident = vwf.build_cave()
    code, labels = masm.assemble(source(), START, symbols={'font_width': resident['width'], 'status_advance': resident['STATUS_BODY_ADV'], 'status_small_advance': resident['STATUS_MED_ADV']})
    if labels['operations_names'] & 3:
        raise ValueError('Operating-terrain pointer table must be word aligned')
    # PC-relative branches retain their displacement. Relocate only absolute
    # jumps/calls within the copied routines; their native external calls stay.
    original = (ROOT/'work/source/vfs/bin/game.bin').read_bytes()
    code = bytearray(code)
    for name, (start, end) in NATIVE_ICON_ROUTINES.items():
        raw = bytearray(original[start-BASE:end-BASE])
        for offset in range(0, len(raw), 4):
            word = struct.unpack_from('<I', raw, offset)[0]
            if word >> 26 not in (2, 3):continue
            target = 0x80000000 | ((word & 0x3FFFFFF) << 2)
            for dest, (lo, hi) in NATIVE_ICON_ROUTINES.items():
                if lo <= target < hi:
                    target = labels[dest] + target-lo
                    struct.pack_into('<I', raw, offset, (word & 0xFC000000) | ((target >> 2) & 0x3FFFFFF))
                    break
            else:
                if START <= target < END:
                    raise ValueError(f'Unpreserved native icon dependency: {target:#x}')
        at = labels[name]-START
        code[at:at+len(raw)] = raw
    # Guard the original reverse-L silhouette and footer frame against a
    # future replacement with a rectangular preview panel.
    for name, address, size in (
        ('rect_body_right', 0x8008D214, 8),
        ('rect_preview_strip', 0x8008D21C, 8),
        ('native_footer_rects', 0x800A944C, 40),
    ):
        at = labels[name] - START
        if code[at:at+size] != original[address-BASE:address-BASE+size]:
            raise ValueError(f'Native status background geometry changed: {name}')
    if START + len(code) > END:
        raise ValueError(f'Status renderer exceeds original drawing region: {START+len(code):#x} > {END:#x}')
    return bytes(code), labels


def patch_overlay(data):
    if struct.unpack_from('<I', data, 0x80097AB8-BASE)[0] != 0x0C0267DC:
        raise ValueError('Unexpected native status draw call')
    external = []
    for offset in range(0, len(data)-3, 4):
        address = BASE+offset
        word = struct.unpack_from('<I', data, offset)[0]
        if START <= address < END:
            continue
        target = 0x80000000 | ((word & 0x3FFFFFF) << 2)
        if (word >> 26 in (2, 3) and START <= target < END) or START <= word < END:
            external.append(address)
    if external != [0x80097AB8]:
        raise ValueError(f'Unexpected external reference into status drawing code: {external}')
    code, labels = assemble()
    out = bytearray(data)
    out[START-BASE:END-BASE] = code.ljust(END-START, b'\0')
    struct.pack_into('<I', out, 0x80097AB8-BASE, vwf.jal(labels['status_draw']))
    # Preserve the original model origin and all native camera presets.
    return bytes(out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='write only the generated debug overlay and layout report')
    args = parser.parse_args()
    code, labels = assemble()
    report = dict(version='0.8.21', renderer_start=hex(START), renderer_end=hex(START+len(code)),
                  original_region_end=hex(END), bytes=len(code), video_mode='native 512x480',
                  display_aspect='4:3', glyph_cell=[19, 24], body_glyph_cell=[16, 20], secondary_glyph_cell=[14, 17], compact_glyph_cell=[11,13],
                  weapon_detail_rows=dict(attack=150,cost_and_kind=184,sea_and_terrain=218,secondary_headers=250,shape=286,range_and_size=320),
                  weapon_detail_row_center_pitch=34,
                  glyph_advance='body: round(original width * 16/12); compact and heading advances unchanged', checked_names=check_fit(),
                  rectangles=RECTS, pilot_cards=[[30, 50+i*97, 184, 94] for i in range(3)],
                  portrait_cell=[38, 48], model_origin=[356, 248])
    print(json.dumps(report, indent=2))
    if args.apply:
        import ui_text
        images, _, problems = ui_text.apply(log=lambda *x: None)
        if problems:
            raise ValueError(problems)
        target = ROOT/'work/build/status_preview.bin'
        target.write_bytes(patch_overlay(vwf.patch_overlay('game', images['game'], BASE)))
        folder = ROOT/'work/ui/status'
        folder.mkdir(parents=True, exist_ok=True)
        (folder/'layout_v0821.json').write_text(json.dumps(report, indent=2)+'\n')
