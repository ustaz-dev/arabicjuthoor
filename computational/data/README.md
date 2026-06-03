# computational/data — the engine room

The master datasets behind the dashboard's computational claims. Everything the site
states about the Arabic core now lives **inside this repo** — no external folder needed.

## Files

- **`layer_2_results_v2.jsonl`** — the master: **2,285 graded trilateral roots**.
  Each record carries the binary nucleus, the third letter (L3), the composition `mode`,
  Jabal's axial meaning (`jabal_axial`), and the letter-by-letter `binary_reading_en` /
  `binary_reading_ar`. Status: **2,034 fully populated · 251 pending** (the remaining
  weak-letter nuclei — أ/و/ي/ء roots — are being filled batch by batch from the fixed charges).

## Where the rest of the core lives (already in this repo)

- **Letter charges (the 28 fixed charges):** [`../../03-scholar-extracts/consensus-letter-charges.md`](../../03-scholar-extracts/consensus-letter-charges.md) (+ `-ar`)
- **Nuclei dossiers:** `../../03-scholar-extracts/jabal-nuclei-*.md` (charge-only, extended, tc-anchored, undocumented)

## Regenerate the reports

```bash
python scripts/layer_2/audit_partial_records.py   # → computational/layer-2-partial-records.md
python scripts/layer_2/fill_partial_readings.py    # fills blank readings (blanks only; writes a .bak)
```

## Provenance

Migrated from the legacy `Juthoor-Linguistic-Genealogy` workspace (now archive-only).
This repo is the single source of truth going forward.
