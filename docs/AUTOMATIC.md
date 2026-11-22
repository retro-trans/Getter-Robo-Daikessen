# Retro Trans Automatic

The public catalog includes Getter Robo Daikessen English **0.8.27**.

1. Open [Retro Trans](https://github.com/retro-trans/retro-trans-tools/releases/latest)
   and click **Refresh catalog**.
2. In **Automatic**, use **Browse…** to select your original Japanese
   SLPS-02232 raw BIN, with its CUE alongside it.
3. Keep **Target: Latest** and check the route is `original → 0.8.27`.
4. Choose a new **Patched copy** path and click **Patch**.
5. Boot the generated CUE. Keep both generated files together.

Automatic downloads the public patch and verifies its hash and the complete
patched image. This route requires the original Japanese BIN; it does not
upgrade an earlier English build. No new Retro Trans app release is needed.

## Verification — 2026-11-21

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
