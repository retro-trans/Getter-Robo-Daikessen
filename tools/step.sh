#!/bin/sh
# tools/step.sh <name> "<gdbdbg script>"  -> runs script, then shot work/ui/shots/<name>.png
cd "$(dirname "$0")/.." && timeout 300 python tools/gdbdbg.py run "$2; shot work/ui/shots/$1.png" | tail -1
