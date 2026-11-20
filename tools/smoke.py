"""Chapter smoke test: boot, jump to a chapter, play to its map, log every drawn string.

    python tools/smoke.py <cue> <first> <last> [outdir=work/ui/smoke]

For every chapter parameter N in first..last (game-flow program 10, parameter N = the
briefing screen at the end of episode N-1):
  restart the emulator, switch to program 10 / N, press Circle through the briefing,
  choose Next Map -> Yes, press Circle through the episode's story until the map prompt
  ("Choose action") is drawn, then take a screenshot.
Every string passed to the string drawer (0x8004DE34) is logged; strings with Shift-JIS
bytes are reported as untranslated. A stop without pad reads for 120 s, or the BIOS
lock-up (pc 0xA0), is reported as a crash with the saved exception context.

Results: <outdir>/chNN.png, <outdir>/chNN.log, summary on stdout and <outdir>/summary.txt.
Each chapter runs in this process with a watchdog (a hung GDB link ends the chapter).
"""
import os
import re
import struct
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gdbdbg               # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRAW = 0x8004DE34
DISPATCH = 0x8004CF48
# kana and kanji only (symbols such as the page arrow and full-width digits are font glyphs)
SJIS = re.compile(rb'(?:^|[\x00-\x7f]|[\x81-\x9f\xe0-\xef][\x40-\xfc])*?'
                  rb'(?:\x82[\x9f-\xf1]|\x83[\x40-\x96]|[\x88-\x9f\xe0-\xea][\x40-\xfc])')


def sh(cmd):
    subprocess.run(cmd, shell=True, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def restart(cue):
    sh('taskkill /IM duckstation-qt-x64-ReleaseLTCG.exe /F')
    time.sleep(3)
    sh('powershell -ExecutionPolicy Bypass -File tools/emu.ps1 start "%s"' % cue)
    time.sleep(6)


class Run:
    def __init__(self, log):
        self.d = gdbdbg.Dbg()
        self.d.g.s.settimeout(120)
        self.log = log
        self.seen = set()
        self.jp = []

    def switch(self, pid, param):
        g = self.d.g
        g.cmd('z0,%x,4' % self.d.bp)
        g.cmd('Z0,%x,4' % DISPATCH)
        while True:
            g.s.sendall(b'$c#63')
            g._recv_packet()
            if self.d.regs()[37] == DISPATCH:
                break
        self.d.setreg(4, pid)
        self.d.setreg(5, param)
        g.cmd('z0,%x,4' % DISPATCH)
        g.cmd('Z0,%x,4' % self.d.bp)

    def frames(self, n, button=0, until=None):
        """Run n pad frames (button held for the first 3), logging drawn strings.
        Returns the matching string when `until` is drawn."""
        g = self.d.g
        g.cmd('Z0,%x,4' % DRAW)
        try:
            f = 0
            while f < n:
                g.s.sendall(b'$c#63')
                g._recv_packet()
                r = self.d.regs()
                if r[37] == DRAW:
                    p = r[6]
                    if 0x80000000 <= p < 0x80200000:
                        s = g.read(p, 96).split(b'\0')[0]
                        if s not in self.seen:
                            self.seen.add(s)
                            t = s.decode('cp932', 'replace')
                            self.log.write(t + '\n')
                            if SJIS.match(s):
                                self.jp.append(t)
                        if until and until.encode() in s:
                            return s.decode('cp932', 'replace')
                elif r[37] == self.d.bp and r[5] == r[29]:
                    if button and f < 3:
                        self.d.setreg(gdbdbg.PAD_REG, r[gdbdbg.PAD_REG] | button)
                    f += 1
        finally:
            g.cmd('z0,%x,4' % DRAW)
        return None

    def plain(self, n, button=0):
        """n pad frames without the draw breakpoint (fast)."""
        g = self.d.g
        f = 0
        while f < n:
            g.s.sendall(b'$c#63')
            g._recv_packet()
            r = self.d.regs()
            if r[37] == self.d.bp and r[5] == r[29]:
                if button and f < 3:
                    self.d.setreg(gdbdbg.PAD_REG, r[gdbdbg.PAD_REG] | button)
                f += 1

    def press_until(self, text, button='circle', presses=200, gap=45):
        """Press, let the game run gap-2 frames freely, then sample the drawn strings for
        2 frames (logging them) and stop when `text` is drawn."""
        b = gdbdbg.BTN[button]
        for k in range(presses):
            self.plain(gap - 2, b if k else 0)
            s = self.frames(2, until=text)
            if s:
                return k, s
        return None, None

    def press(self, button, n=1, gap=20):
        for _ in range(n):
            self.plain(gap, gdbdbg.BTN[button])

    def shot(self, path):
        a, b = gdbdbg.displayed_rect(self.d)
        gdbdbg.write_png(path, 320, 240, a)

    def crash_info(self):
        g = self.d.g
        r = self.d.regs()
        if r[37] not in (0xA0, 0xB0, 0xC0) and not (0xBFC00000 <= r[37] < 0xBFC80000):
            return None
        pcb = struct.unpack('<I', g.read(0x80000108, 4))[0]
        tcb = struct.unpack('<I', g.read(0x80000000 | pcb & 0x1FFFFFFF, 4))[0]
        R = struct.unpack('<40I', g.read(0x80000000 | (tcb & 0x1FFFFFFF), 0xA0))
        return 'epc %08x cause %08x ra %08x' % (R[34], R[38], R[33])


def chapter(cue, n, outdir):
    restart(cue)
    log = open(os.path.join(outdir, 'ch%02d.log' % n), 'w', encoding='utf-8')
    res = {'n': n}
    done = threading.Event()

    def watchdog():
        if not done.wait(1800):
            log.write('WATCHDOG\n')
            log.flush()
            os._exit(3)
    threading.Thread(target=watchdog, daemon=True).start()
    run = None
    try:
        run = Run(log)
        run.switch(10, n)
        k, s = run.press_until('Next Map', 'circle', 60, 60)
        res['menu'] = k is not None
        if k is None:
            res['error'] = 'briefing menu not reached'
            return res
        run.plain(30)
        run.press('down', 6, 12)
        run.press('circle', 1, 40)
        run.press('up', 1, 12)
        run.press('circle', 1, 60)
        k, s = run.press_until('Choose action', 'circle', 250, 45)
        res['map'] = k
        if k is None:
            res['error'] = 'map prompt not reached'
        run.plain(10)
        run.shot(os.path.join(outdir, 'ch%02d.png' % n))
    except Exception as ex:      # noqa: BLE001
        res['error'] = '%s: %s' % (type(ex).__name__, ex)
        try:
            if run:
                run.d.g.s.settimeout(10)
                res['crash'] = run.crash_info()
        except Exception:        # noqa: BLE001
            pass
    finally:
        done.set()
        if run:
            res['jp'] = run.jp
            res['strings'] = len(run.seen)
            try:
                run.d.g.cmd('z0,%x,4' % run.d.bp)
                run.d.g.close()
            except Exception:    # noqa: BLE001
                pass
        log.close()
    return res


def main():
    cue = sys.argv[1]
    first, last = int(sys.argv[2]), int(sys.argv[3])
    outdir = sys.argv[4] if len(sys.argv) > 4 else os.path.join(ROOT, 'work', 'ui', 'smoke')
    os.makedirs(outdir, exist_ok=True)
    summ = open(os.path.join(outdir, 'summary.txt'), 'a', encoding='utf-8')
    for n in range(first, last + 1):
        t = time.time()
        r = chapter(cue, n, outdir)
        line = 'ch%02d %4ds map=%s strings=%s jp=%d %s %s' % (
            n, time.time() - t, r.get('map'), r.get('strings'), len(r.get('jp', [])),
            r.get('error', ''), r.get('crash') or '')
        print(line, flush=True)
        summ.write(line + '\n')
        for j in r.get('jp', []):
            summ.write('   JP: %s\n' % j)
        summ.flush()


if __name__ == '__main__':
    main()
