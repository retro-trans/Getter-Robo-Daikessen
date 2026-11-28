# Retro Trans Automatic

The public catalog includes Getter Robo Daikessen English **0.8.32**.

1. Open [Retro Trans](https://github.com/retro-trans/retro-trans-tools/releases/latest)
   and click **Refresh catalog**.
2. In **Automatic**, use **Browse…** to select your original Japanese
   SLPS-02232 raw BIN or the published English v0.8.30 BIN, with its CUE alongside it.
3. Keep **Target: Latest** and check the route ends at `0.8.32`.
4. Choose a new **Patched copy** path and click **Patch**.
5. Boot the generated CUE. Keep both generated files together.

Automatic downloads the public patch and verifies its hash and the complete
patched image. Both sources produce the same English disc. No new Retro Trans app release is needed.

## Verification for 0.8.30

Retro Trans 0.5.23 recognized both the original Japanese BIN and the published
v0.8.29 BIN. For each source, the Automatic worker selected the direct route to
0.8.30, downloaded the public patch into a fresh cache and generated the matching
CUE. Both runs produced the same 663,111,120-byte image with SHA-256
`003121a132bcd602d725b27b4ccbc0058c6263aae70008c7984406743ffa7fdb`.
[Catalog validation run](https://github.com/retro-trans/retro-trans-tools/actions/runs/45036841341).

## Verification for 0.8.29 — 2026-11-22

Retro Trans 0.5.23 recognized the original Japanese BIN and selected
`original → 0.8.29` after refreshing the public catalog. The Automatic worker
downloaded the patch into an empty cache, produced the matching CUE and
reproduced the tested 663,666,192-byte BIN with SHA-256
`d9a5b7c4f80c615773289a05e3cdc480e9b1989f8816029718746dbba5909cf8`. The original BIN retained
its checksum. [Catalog validation run](https://github.com/retro-trans/retro-trans-tools/actions/runs/45034841037).

## Verification for 0.8.27 — 2026-11-22

Retro Trans 0.5.23 refreshed the public catalog and selected `original → 0.8.27`.
Starting with an empty download cache, the Automatic worker downloaded the
public patch, applied it to the original Japanese BIN, and generated a matching
CUE. The output matched the disc used for the four Getter Rekka battle tests
byte for byte (663,666,192 bytes, SHA-256
`c8b74236cad15dc2cfc39034b94da603882aeffd0a0820b2f673af88af880f09`).
The original BIN retained its checksum. The
[hosted catalog validation](https://github.com/retro-trans/retro-trans-tools/actions/runs/44990094257)
also passed.

## Verification for 0.8.26 — 2026-11-21

- Tested using Retro Trans **0.5.23**, source commit `cbf7858`, through
  `retro_trans.catalog.recognize`, `Catalog.plan` and the same `apply_plan`
  worker used by the Automatic tab. This was a worker integration test;
  the frozen Windows GUI was not driven for this check.
- With an empty patch cache, downloaded the
  [public v0.8.26 patch](https://github.com/retro-trans/Getter-Robo-Daikessen/releases/tag/v0.8.26),
  applied it through native xdelta3, and verified the finished BIN and generated CUE.
- Refreshed the actual public catalog using the 0.5.23 client and confirmed
  it recognizes the original BIN and chooses 0.8.26 as Latest.
- Source remained **663111120 bytes**, SHA-256
  `08f189c914fa753af0ba690579712636f1d8b21eb7777c89b6fc10041c725807`.
- Output was **663666192 bytes**, SHA-256
  `38c012217f7ffcbc5ef88594eaa1514d8273a331df4c69d6cd6ae2a20fd82190`.
- Shared catalog ingestion now accepts CUE extras up to 64 KiB with full
  size/hash checks. All 18 catalog-builder tests and 16 catalog tests passed.
  The [hosted catalog refresh](https://github.com/retro-trans/retro-trans-tools/actions/runs/44913164704)
  passed after the fix. Historical patch identities and game release assets
  were preserved.

Local reports are under `work/ui/automatic/v0826/`.
