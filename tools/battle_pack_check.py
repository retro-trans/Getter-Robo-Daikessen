"""Read-only regression checks for the native battle unit pack size boundary.

Uses the original local disc data. No game assets or source script are printed.
"""
import json
from pathlib import Path
import struct
import battletext
import pac


def decoded_entries(data):
    rows = []
    for e in pac.parse_container(data, 0):
        raw = pac.decode_entry(data, e)
        if e['name'].upper() == 'TMV.PAC':
            raw = decoded_entries(battletext.tmv_bytes(data, e))
        rows.append((e['name'], raw))
    return rows


def main():
    root = Path(battletext.ROOT)
    original = (root / 'work/source/disc/GR.VFS').read_bytes()
    # Prove the documented allocation is the one in this retail executable.
    overlay = battletext.vfs_file(original, 'bin/battle.bin')
    at = 0x800ACB40 - 0x800A97A8
    assert struct.unpack_from('<4I', overlay, at) == (
        0x3C040001, 0x34845000, 0x3C05800B, 0x0C00B788)
    files = {}
    battletext.build_files(original, files)
    path = 'prog00/zan1.pac'
    fixed = files[path]
    assert len(fixed) <= battletext.UNIT_PACK_LIMIT
    # Recreate the previous ordinary-compression output from the translated BIN.
    orig_pack = battletext.vfs_file(original, path)
    tmv = battletext.tmv_bytes(orig_pack, battletext.entry_by_name(orig_pack, 'TMV.PAC'))
    tr = {r['jp']: r['en'] for r in battletext.load() if r.get('en')}
    stats = dict(inplace=0, moved=0)
    bin_entry = battletext.entry_by_name(tmv, 'ZAN1.BIN')
    text = battletext.rebuild_bin(pac.decode_entry(tmv, bin_entry), tr, stats)
    nested = pac.build_container([
        pac.pack_entry(it, text) if it['name'] == 'ZAN1.BIN' else it
        for it in pac.container_items(tmv)])
    old = pac.build_container([
        pac.pack_entry(it, nested) if it['name'] == 'TMV.PAC' else it
        for it in pac.container_items(orig_pack)])
    assert len(old) > battletext.UNIT_PACK_LIMIT
    assert decoded_entries(old) == decoded_entries(fixed), 'Compression changed decoded assets'
    # Unchanged packs and the exact capacity must pass without being rewritten.
    assert battletext.fit_unit_pack(b'X' * battletext.UNIT_PACK_LIMIT, 'capacity') == b'X' * battletext.UNIT_PACK_LIMIT
    items = pac.container_items(old)
    items[-1] = dict(items[-1], payload=items[-1]['payload'] + b'X' * 4096,
                    usize=items[-1]['usize'] + 4096, psize=items[-1]['psize'] + 4096)
    try:
        battletext.fit_unit_pack(pac.build_container(items), 'still-oversized')
    except ValueError as exc:
        assert 'native unit buffer' in str(exc)
    else:
        raise AssertionError('Oversized unit pack was accepted')
    paths = {p for p, _, _, _ in battletext.units(original)}
    assert 'prog00/effect.pac' not in paths
    assert all(len(files.get(p) or battletext.vfs_file(original, p)) <= battletext.UNIT_PACK_LIMIT for p in paths)
    result = dict(passed=True, allocation_instructions_verified=True,
                  unit_packs_checked=len(paths), previous_rekka_bytes=len(old),
                  fixed_rekka_bytes=len(fixed), limit=battletext.UNIT_PACK_LIMIT,
                  decoded_contents_identical=True, oversized_rejected=True)
    print(json.dumps(result, indent=2))
    return result


if __name__ == '__main__':
    main()
