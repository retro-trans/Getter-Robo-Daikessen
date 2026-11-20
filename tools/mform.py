"""Map event scripts MFORMnn.BIN (mapef/mformnn.pac): parse, extract strings, rebuild.

Layout (see docs/formats.md):
  u32 section_offset[] (0-terminated) | strings | code0 hdr0 code1 hdr1 ... (headers 0x50 bytes,
  +0x4C = code offset of that section; code_i ends at header_i)
Opcode 0x00 (8 bytes) holds the only string pointer (u32 file offset at +4).
Opcode lengths: exe table 0x80082990 (copied below).

Rebuild strategy: strings are re-emitted in a fresh string area right after the offset
table; bytecode and section headers are moved as one block after it, and every offset
that points into them is shifted by the same delta (section table, header +0x4C code
offsets, code-to-code operands are relative? -> see CODE_PTR_OPS). Op 0x00 pointers are
rewritten to the new string offsets.
"""
import struct

OPLEN = [8, 4, 4, 4, 4, 12, 12, 12, 4, 8, 12, 12, 4, 4, 8, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4,
         12, 8, 8, 8, 4, 4, 4, 16, 8, 4, 4, 4, 4, 8, 8, 4, 4, 4, 4, 4, 4, 4, 4, 4, 8, 4, 8, 8,
         4, 4, 4, 4, 4, 4, 4, 4]


class MForm:
    def __init__(self, data):
        self.d = data
        d = data
        self.sections = []
        i = 0
        while True:
            v = struct.unpack_from('<I', d, i)[0]
            if v == 0:
                break
            self.sections.append(v)
            i += 4
        self.table_end = i + 4
        self.codes = [struct.unpack_from('<I', d, s + 0x4C)[0] for s in self.sections]
        self.code_start = min(self.codes)
        self.code_end = min(self.sections)
        # strings: NUL-terminated runs between the table and the code
        self.strings = {}      # offset -> bytes
        p = self.table_end
        while p < self.code_start:
            while p < self.code_start and d[p] == 0:
                p += 1
            if p >= self.code_start:
                break
            q = d.index(b'\0', p)
            self.strings[p] = d[p:q]
            p = q + 1
        # walk code: section i = code at codes[i] .. its header at sections[i]
        # (file layout: code0 hdr0 code1 hdr1 ..., header 0x50 bytes)
        self.ops = []          # (offset, opcode, length)
        for c, s in zip(self.codes, self.sections):
            p = c
            while p < s:
                op = d[p]
                n = OPLEN[op]
                self.ops.append((p, op, n))
                p += n
            assert p == s, 'code walk mismatch at %#x' % c
        self.str_refs = []     # (op_offset, string_offset)
        for p, op, n in self.ops:
            if op == 0x00:
                v = struct.unpack_from('<I', d, p + 4)[0]
                if v in self.strings:
                    self.str_refs.append((p, v))

    def used_strings(self):
        """String offsets in file order that are referenced by op 0x00."""
        used = {v for _, v in self.str_refs}
        return [o for o in sorted(self.strings) if o in used]

    def operand_offsets(self):
        """Every (position, value) u32 in code/headers that is an offset into code or headers."""
        return

    def rebuild(self, new_strings):
        """new_strings: {old_offset: bytes}. Returns new file bytes."""
        d = self.d
        out = bytearray(d[:self.table_end])
        newoff = {}
        for o in sorted(self.strings):
            s = new_strings.get(o, self.strings[o])
            newoff[o] = len(out)
            out += s + b'\0'
        while len(out) % 4:
            out += b'\0'
        delta = len(out) - self.code_start
        block = bytearray(d[self.code_start:])
        base = self.code_start
        # string pointers
        for p, v in self.str_refs:
            struct.pack_into('<I', block, p - base + 4, newoff[v])
        # section table + code offsets in headers
        for i, s in enumerate(self.sections):
            struct.pack_into('<I', out, i * 4, s + delta)
            struct.pack_into('<I', block, s - base + 0x4C, self.codes[i] + delta)
        # code operands that point into code (jumps/calls): CODE_PTR_OPS
        for p, op, n in self.ops:
            for k in CODE_PTR_OPS.get(op, ()):
                v = struct.unpack_from('<I', d, p + k)[0]
                if self.code_start <= v < len(d):
                    struct.pack_into('<I', block, p - base + k, v + delta)
        out += block
        return bytes(out)


# opcode -> operand positions holding a file offset into the code area (found by scan_ptrs)
CODE_PTR_OPS = {}


def scan_code_pointers(forms):
    """Find (opcode, operand) slots whose u32 always lands on an op boundary in code."""
    import collections
    hit = collections.Counter()
    total = collections.Counter()
    for f in forms:
        starts = {p for p, _, _ in f.ops}
        for p, op, n in f.ops:
            for k in range(4, n - 3, 4):
                v = struct.unpack_from('<I', f.d, p + k)[0]
                total[(op, k)] += 1
                if v in starts:
                    hit[(op, k)] += 1
    return hit, total


# operand slots that hold string offsets: (opcode, byte offset in the instruction)
STR_SLOTS = {0x00: (4,), 0x21: (4, 8), 0x34: (4,)}


def string_refs(m):
    """[(position of the u32, string offset)] for every string pointer in the code."""
    out = []
    for p, op, n in m.ops:
        for k in STR_SLOTS.get(op, ()):
            v = struct.unpack_from('<I', m.d, p + k)[0]
            if v in m.strings:
                out.append((p + k, v))
    return out


def rebuild_strings(m, new):
    """new: {old string offset: bytes (without NUL)}. Code/headers stay in place; strings
    are packed into the original string area (table end .. code start), overflow is
    appended after the end of the file. Returns the new file bytes."""
    d = bytearray(m.d)
    area_lo, area_hi = m.table_end, m.code_start
    order = sorted(m.strings)
    newoff = {}
    pos = area_lo
    tail = bytearray()
    tail_base = (len(d) + 3) & ~3
    for o in order:
        s = new.get(o, m.strings[o]) + b'\0'
        if pos + len(s) <= area_hi:
            newoff[o] = pos
            d[pos:pos + len(s)] = s
            pos += len(s)
        else:
            newoff[o] = tail_base + len(tail)
            tail += s
    d[pos:area_hi] = b'\0' * (area_hi - pos)
    for at, v in string_refs(m):
        struct.pack_into('<I', d, at, newoff[v])
    if tail:
        d += b'\0' * (tail_base - len(d))
        d += tail
        while len(d) % 4:
            d += b'\0'
    return bytes(d)
