"""Build the patched disc image.

    python tools/build.py [--version 0.1.0] [--test-text] [--no-text] [--dry-run]

Steps:
  1. exe  : VWF hooks + ASCII table (tools/vwf.py), UI strings (tools/ui_text.py, later)
  2. GR.VFS: setup.pac (VWF font cells), mformNN.pac (translated scripts), other text files
  3. disc : copy of the original BIN, SLPS_022.32 and GR.VFS replaced (moved to the end of
            the image when they grow), new CUE.
Output: work/output/GetterRoboDaikessen_EN_v<ver>.bin/.cue. Older builds are turned into
work/output/patches/<name>.xdelta (VCDIFF against the original disc, tools/vcdiff.py) and deleted.
"""
import argparse
import json
import os
import re
import shutil
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_disc   # noqa: E402
import datatext     # noqa: E402
import mform        # noqa: E402
import pac          # noqa: E402
import textcodec    # noqa: E402
import ui_text      # noqa: E402
import vfs          # noqa: E402
import vwf          # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_BIN = os.path.join(ROOT, 'Getter Robo Daikessen! (Japan).bin')
DISC = os.path.join(ROOT, 'work', 'source', 'disc')
OUT = os.path.join(ROOT, 'work', 'output')
TR = os.path.join(ROOT, 'work', 'translation', 'en')
VERSION_FILE = os.path.join(ROOT, 'work', 'version.txt')


def read(p):
    return open(p, 'rb').read()


def vfs_file(orig_vfs, path):
    t, ents = vfs.parse(orig_vfs)
    for e in ents:
        if e['path'] == path:
            off = vfs.DATA_BASE + e['sector'] * 2048 + (e['flags'] & 7) * 0x100
            return orig_vfs[off:off + e['size']]
    raise KeyError(path)


def repack(pacdata, replace):
    """replace: {entry name: new unpacked bytes}."""
    items = pac.container_items(pacdata)
    out = []
    for it in items:
        if it['name'] in replace:
            it = pac.pack_entry(it, replace[it['name']])
        out.append(it)
    return pac.build_container(out)


def unpack_entry(pacdata, name):
    for e in pac.parse_container(pacdata, 0):
        if e['name'] == name:
            return pac.decode_entry(pacdata, e)
    raise KeyError(name)


def load_rows(name):
    p = os.path.join(TR, name)
    if not os.path.exists(p):
        return []
    return json.load(open(p, encoding='utf-8'))


def mform_texts(fname, m, test):
    """{string offset: encoded bytes} for one MFORM file."""
    import wrap
    new = {}
    if test:
        n = 0
        for o, s in m.strings.items():
            if not s or s.startswith(b'MapEf'):
                continue
            t = s.decode('cp932', 'replace')
            pre = re.match(r'^((?:\$[fm]\d\d[a-z]|\$s\d\d|%\d|\$n|%0)*)', t).group(1)
            name = re.match(r'^(?:\$[fm]\d\d[a-z])?(?:\$s\d\d)?%2([^%]*)%0', t)
            n += 1
            body = 'VWF test %d. The quick brown fox jumps over the lazy dog, again and again!' % n
            if name:
                body = '%2' + 'Ryoma' + '%0$s13"' + body + '"'
                pre = re.match(r'^((?:\$[fm]\d\d[a-z])?(?:\$s\d\d)?)', t).group(1)
            new[o] = textcodec.encode(pre + body)
        return new
    rows = load_rows('mform.json')
    for r in rows:
        if r['file'] != fname or not r.get('en'):
            continue
        # Reflow at build time, so a font change cannot leave stale word breaks.
        new[int(r['offset'], 16)] = textcodec.encode(wrap.reflow(r['en']))
    return new


def build(version, test=False, no_text=False):
    # Movies keep their original sector slots and XA audio. Fail before creating a
    # disc if any translated asset is missing or stale.
    movies = {}
    if not no_text:
        import movie
        if movie.TRANSLATION.exists():
            movies = movie.ready_movies(require_decoded=True)
    orig_vfs = read(os.path.join(DISC, 'GR.VFS'))
    files = {}

    # font
    setup = vfs_file(orig_vfs, 'bin/setup.pac')
    files['bin/setup.pac'] = repack(setup, {'FONT12_0.TIM': vwf.patched_font_tim()})

    # map event scripts
    if not no_text:
        t, ents = vfs.parse(orig_vfs)
        for e in ents:
            if e['dir'] or not re.match(r'mapef/mform(\d+[ab]?|db)\.pac$', e['path']):
                continue
            pd = vfs_file(orig_vfs, e['path'])
            name = pac.parse_container(pd, 0)[0]['name']
            data = unpack_entry(pd, name)
            m = mform.MForm(data)
            new = mform_texts(name, m, test)
            if new:
                files[e['path']] = repack(pd, {name: mform.rebuild_strings(m, new)})

    # briefings, battle lines, unit / pilot data
    if not no_text:
        datatext.build_files(orig_vfs, files)
        # edited graphics (title cards, Game Over, ...): work/translation/en/gfx
        import gfx
        gfx.build_files(orig_vfs, files, vfs_file)
        # battle dialogue of every unit (prog00/*.pac)
        import battletext
        battletext.build_files(orig_vfs, files)
        import episode_preview
        if episode_preview.TRANSLATION.exists():
            episode_preview.build_files(orig_vfs, files, vfs_file)

    # UI strings (exe + overlays)
    ui_imgs, ui_blobs, probs = ({}, [], []) if no_text else ui_text.apply()
    for p_ in probs:
        print('UI PROBLEM', p_)
    for tag in vwf.OVERLAY_PATCHES:
        if tag not in ui_imgs:
            ui_imgs[tag] = read(ui_text.IMAGES[tag][0])
    for tag, data in ui_imgs.items():
        if tag != 'exe':
            patched = vwf.patch_overlay(tag, data, ui_text.IMAGES[tag][1])
            if tag == 'battle':
                import battle_hint
                patched = battle_hint.patch_overlay(patched)
            if tag == 'title':
                import title_credit
                import difficulty
                patched = title_credit.patch_overlay(patched, version)
                patched = difficulty.patch_title(patched)
            if tag == 'briefing' and not no_text:
                import episode_preview
                if episode_preview.TRANSLATION.exists():
                    patched = episode_preview.patch_overlay(patched)
            if tag == 'flight' and not no_text:
                import minigame_subtitles
                if minigame_subtitles.TRANSLATION.exists():
                    patched = minigame_subtitles.patch_overlay(patched)
            if tag == 'game' and not no_text:
                import status_layout
                patched = status_layout.patch_overlay(patched)
            if tag in ('briefing', 'flight') and not no_text:
                import menu_layout
                patched = (menu_layout.patch_briefing if tag == 'briefing' else menu_layout.patch_flight)(patched)
                if tag == 'briefing':
                    import briefing_layout
                    patched = briefing_layout.patch_overlay(patched)
            files['bin/%s.bin' % tag] = patched

    new_vfs = vfs.build(orig_vfs, files)
    exe_src = ui_imgs.get('exe') or read(os.path.join(DISC, 'SLPS_022.32'))
    import difficulty
    exe_src = difficulty.patch_core(exe_src)
    difficulty_code, _ = difficulty.resident()
    exe, labels = vwf.patch_exe(exe_src, ui_blobs + [(difficulty.RESIDENT, difficulty_code)])

    # keep the built pieces for hot patching (tools/hotpatch.py) / coverage checks; written
    # first so they exist even when the disc image is locked by a running emulator
    bd = os.path.join(ROOT, 'work', 'build')
    os.makedirs(bd, exist_ok=True)
    open(os.path.join(bd, 'SLPS_022.32'), 'wb').write(exe)
    open(os.path.join(bd, 'GR.VFS'), 'wb').write(new_vfs)
    json.dump({k: v for k, v in labels.items()}, open(os.path.join(bd, 'vwf_labels.json'), 'w'), indent=1)
    import loadlimits
    if loadlimits.main():
        raise SystemExit('a file is larger than the buffer the game reads it into')
    os.makedirs(OUT, exist_ok=True)
    base = 'GetterRoboDaikessen_EN_v%s' % version
    out_bin = os.path.join(OUT, base + '.bin')
    d = build_disc.Disc.open_copy(SRC_BIN, out_bin)
    print('exe moved' if d.replace('SLPS_022.32', exe) else 'exe in place', len(exe))
    print('vfs moved' if d.replace('GR.VFS', new_vfs) else 'vfs in place', len(new_vfs))
    for name, raw in movies.items():
        print('movie', name, d.write_raw_sectors(name, raw), 'sectors replaced')
    d.close()
    with open(os.path.join(OUT, base + '.cue'), 'w') as f:
        f.write('FILE "%s.bin" BINARY\n  TRACK 01 MODE2/2352\n    INDEX 01 00:00:00\n' % base)
    print('built', out_bin)
    archive_old(base)
    return out_bin


KEEP_PATCHES = 10


def archive_old(current):
    """Older builds -> work/output/patches/<name>.xdelta (VCDIFF from the original disc);
    only the latest .bin/.cue stay, and only the 10 newest patches are kept."""
    import re
    import vcdiff
    pd = os.path.join(OUT, 'patches')
    os.makedirs(pd, exist_ok=True)
    src = None
    for fn in sorted(os.listdir(OUT)):
        m = re.match(r'(GetterRoboDaikessen_EN_v[0-9.]+)\.bin$', fn)
        if not m or m.group(1) == current:
            continue
        patch = os.path.join(pd, m.group(1) + '.xdelta')
        if not os.path.exists(patch):
            src = src or read(SRC_BIN)
            tgt = read(os.path.join(OUT, fn))
            open(patch, 'wb').write(vcdiff.make(src, tgt))
            del tgt
        try:
            os.remove(os.path.join(OUT, fn))
        except PermissionError:
            print('saved archive; older image is still open in another application:', fn)
            continue
        cue = os.path.join(OUT, m.group(1) + '.cue')
        if os.path.exists(cue):
            os.remove(cue)
        print('archived', fn, '->', os.path.relpath(patch, ROOT))

    def ver(fn):
        return tuple(int(x) for x in re.findall(r'v([0-9.]+)\.xdelta$', fn)[0].split('.'))
    patches = sorted((f for f in os.listdir(pd) if f.endswith('.xdelta')), key=ver)
    for f in patches[:-KEEP_PATCHES]:
        os.remove(os.path.join(pd, f))
        print('dropped old patch', f)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--version', default=None)
    ap.add_argument('--test-text', action='store_true')
    ap.add_argument('--no-text', action='store_true')
    ap.add_argument('--dry-run', action='store_true', help='show outputs and movie inputs without writing files')
    a = ap.parse_args()
    v = a.version or open(VERSION_FILE).read().strip()
    if a.dry_run:
        base = 'GetterRoboDaikessen_EN_v%s' % v
        print('Build plan:', base)
        print('Original disc:', SRC_BIN)
        print('Outputs:', os.path.join(OUT, base+'.bin'), os.path.join(OUT, base+'.cue'))
        if not a.no_text:
            import movie
            if movie.TRANSLATION.exists():
                ready = movie.ready_movies(require_decoded=True)
                print('Validated movie inputs:', len(ready), ', '.join(ready))
        for fn in sorted(os.listdir(OUT)):
            if fn.endswith('.bin') and fn != base+'.bin':
                print('Archive previous build:', fn, 'as xdelta; keep at most', KEEP_PATCHES)
    else:
        build(v, a.test_text, a.no_text)
