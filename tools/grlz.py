"""Unpacker codecs of Getter Robo Daikessen (exe 0x8003909C, mode = entry header +0x18 & 0xF).

  mode 0  plain copy
  mode 3  LZ (exe 0x80010004, hand-written asm). Kosinski-like:
          16-bit LE descriptor, bits taken LSB first; after the 16th bit is taken the next
          descriptor is read at once (before that item's data).
            1            literal byte
            0 0 b1 b0    short match: count = 2 + (b1 b0), offset = next byte (1..255)
            0 1          long match: lo, hi = next 2 bytes; offset = lo | (hi & 0xF8) << 5;
                         count = (hi & 7) + 2, or if (hi & 7) == 0: n = next byte:
                         n == 0 end, n == 1 no-op, else count = n + 1
          copy is byte-by-byte from dst - offset (overlap allowed).
  mode 1, 2, 4  RLE variants (images); decoded here only as far as needed (mode 4).
"""


def lz_decompress(src, pos=0, limit=None):
    """Return (data, end_pos)."""
    out = bytearray()
    end = len(src) if limit is None else pos + limit
    desc = src[pos] | src[pos + 1] << 8
    pos += 2
    left = 16

    def bit():
        nonlocal desc, left, pos
        left -= 1
        b = desc & 1
        desc >>= 1
        if left == 0:
            desc = src[pos] | src[pos + 1] << 8
            pos += 2
            left = 16
        return b

    while True:
        if bit():
            out.append(src[pos])
            pos += 1
            continue
        if bit():
            lo, hi = src[pos], src[pos + 1]
            pos += 2
            off = lo | (hi & 0xF8) << 5
            cnt = hi & 7
            if cnt:
                cnt += 2
            else:
                n = src[pos]
                pos += 1
                if n == 0:
                    break
                if n == 1:
                    continue
                cnt = n + 1
        else:
            cnt = (bit() << 1)
            cnt |= bit()
            cnt += 2
            off = src[pos]
            pos += 1
        s = len(out) - off
        if s < 0:
            raise ValueError('bad offset %d at out %d' % (off, len(out)))
        for i in range(cnt):
            out.append(out[s + i])
        if pos > end + 2:
            raise ValueError('overrun')
    return bytes(out), pos


class _BitWriter:
    """Emits descriptor words with the decoder's eager-reload rule."""

    def __init__(self):
        self.out = bytearray(b'\0\0')
        self.dpos = 0          # where the current descriptor lives
        self.desc = 0
        self.n = 0
        self.pending = bytearray()

    def bit(self, b):
        self.desc |= (b & 1) << self.n
        self.n += 1
        if self.n == 16:
            self.out[self.dpos:self.dpos + 2] = bytes((self.desc & 0xFF, self.desc >> 8))
            # next descriptor is read right after the 16th bit, before this item's bytes
            self.dpos = len(self.out)
            self.out += b'\0\0'
            self.desc = 0
            self.n = 0

    def data(self, bs):
        self.out += bs

    def finish(self):
        self.out[self.dpos:self.dpos + 2] = bytes((self.desc & 0xFF, self.desc >> 8))
        return bytes(self.out)


def lz_compress(data, window=0x1FFF, max_len=256):
    """Greedy LZ with hash chains. Output decodes with lz_decompress."""
    w = _BitWriter()
    n = len(data)
    i = 0
    heads = {}
    prev = [-1] * n

    def insert(p):
        if p + 2 < n:
            k = data[p:p + 3]
            prev[p] = heads.get(k, -1)
            heads[k] = p

    def best(p):
        bl, bo = 0, 0
        if p + 2 >= n:
            # only 2-byte matches possible
            if p + 1 < n:
                for off in range(1, min(255, p) + 1):
                    if data[p - off] == data[p] and data[p - off + 1] == data[p + 1]:
                        return 2, off
            return 0, 0
        c = heads.get(data[p:p + 3], -1)
        tries = 0
        while c >= 0 and p - c <= window and tries < 256:
            l = 0
            m = min(max_len, n - p)
            while l < m and data[c + l] == data[p + l]:
                l += 1
            if l > bl:
                bl, bo = l, p - c
                if l == m:
                    break
            c = prev[c]
            tries += 1
        if bl < 3 and p + 1 < n:
            for off in range(1, min(255, p) + 1):
                if data[p - off] == data[p] and data[p - off + 1] == data[p + 1]:
                    return 2, off
        return bl, bo

    while i < n:
        l, off = best(i)
        if l >= 2 and off <= 255 and l <= 5:
            w.bit(0); w.bit(0)
            c = l - 2
            w.bit(c >> 1); w.bit(c & 1)
            w.data(bytes((off,)))
        elif l >= 3:
            w.bit(0); w.bit(1)
            if l <= 9:
                w.data(bytes((off & 0xFF, ((off >> 5) & 0xF8) | (l - 2))))
            else:
                w.data(bytes((off & 0xFF, (off >> 5) & 0xF8, l - 1)))
        else:
            l = 1
            w.bit(1)
            w.data(data[i:i + 1])
        for k in range(i, i + l):
            insert(k)
        i += l
    # end marker: long match with count byte 0
    w.bit(0); w.bit(1)
    w.data(b'\0\0\0')
    return w.finish()


def lz_compress_opt(data, window=0x1FFF, max_len=256, chain=512):
    """Optimal-parse LZ (same format as lz_compress, decodes with lz_decompress): costs in
    bits - literal 9, short match (2-5 bytes, offset <= 255) 12, long match 18 (3-9) or
    26 (10-256) - minimised by dynamic programming over the matches found by hash chains.
    Used where packed size matters (files read into fixed-size buffers)."""
    n = len(data)
    heads = {}
    prev = [-1] * n
    longest = [(0, 0)] * n      # (length, offset) longest long-range match
    short = [(0, 0)] * n        # (length <= 5, offset <= 255)
    for p in range(n):
        bl = bo = 0
        sl = so = 0
        if p + 2 < n:
            c = heads.get(data[p:p + 3], -1)
            tries = 0
            m = min(max_len, n - p)
            while c >= 0 and p - c <= window and tries < chain:
                l = 0
                while l < m and data[c + l] == data[p + l]:
                    l += 1
                if l > bl:
                    bl, bo = l, p - c
                if p - c <= 255 and min(l, 5) > sl:
                    sl, so = min(l, 5), p - c
                if l == m and (sl == 5 or p - c > 255):
                    break
                c = prev[c]
                tries += 1
        if sl < 2 and p + 1 < n:
            for off in range(1, min(255, p) + 1):
                if data[p - off] == data[p] and data[p - off + 1] == data[p + 1]:
                    sl, so = 2, off
                    break
        longest[p] = (bl, bo)
        short[p] = (sl, so)
        if p + 2 < n:
            prev[p] = heads.get(data[p:p + 3], -1)
            heads[data[p:p + 3]] = p
    INF = 1 << 60
    cost = [INF] * (n + 1)
    choice = [None] * (n + 1)
    cost[n] = 0
    for p in range(n - 1, -1, -1):
        best = cost[p + 1] + 9
        ch = ('lit', 1, 0)
        sl, so = short[p]
        for L in range(2, sl + 1):
            c = cost[p + L] + 12
            if c < best:
                best, ch = c, ('short', L, so)
        bl, bo = longest[p]
        for L in range(3, bl + 1):
            c = cost[p + L] + (18 if L <= 9 else 26)
            if c < best:
                best, ch = c, ('long', L, bo)
        cost[p] = best
        choice[p] = ch
    w = _BitWriter()
    i = 0
    while i < n:
        kind, l, off = choice[i]
        if kind == 'short':
            w.bit(0); w.bit(0)
            c = l - 2
            w.bit(c >> 1); w.bit(c & 1)
            w.data(bytes((off,)))
        elif kind == 'long':
            w.bit(0); w.bit(1)
            if l <= 9:
                w.data(bytes((off & 0xFF, ((off >> 5) & 0xF8) | (l - 2))))
            else:
                w.data(bytes((off & 0xFF, (off >> 5) & 0xF8, l - 1)))
        else:
            w.bit(1)
            w.data(data[i:i + 1])
        i += l
    w.bit(0); w.bit(1)
    w.data(bytes(3))
    return w.finish()


def rle4_decompress(src, pos=0):
    """mode 4 (exe 0x800399BC)."""
    import struct
    total = struct.unpack_from('<I', src, pos)[0]
    pos += 4
    out = bytearray()
    while len(out) < total:
        a, b = src[pos], src[pos + 1]
        pos += 2
        if a == 0:
            out += src[pos:pos + b]
            pos += b
        elif a == 0xFF:
            n = struct.unpack_from('<I', src, pos)[0]
            pos += 4
            out += bytes((b,)) * (n + 1)
        elif a == 0xFE:
            n = src[pos] | src[pos + 1] << 8
            pos += 2
            out += bytes((b,)) * (n + 1)
        else:
            out += bytes((b,)) * (a + 1)
    return bytes(out), pos


if __name__ == '__main__':
    import os
    import random
    import sys
    random.seed(1)
    tests = [b'', b'a', b'abcabcabcabc' * 50, bytes(random.randrange(4) for _ in range(5000)),
             os.urandom(3000), b'\0' * 9000]
    for t in tests:
        c = lz_compress(t)
        d, _ = lz_decompress(c)
        assert d == t, (len(t), len(d))
    print('selftest ok')
