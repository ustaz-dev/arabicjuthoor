# Calibrated التَّمريرة الثانية Re-Scoring of the Full 770 ≥0.65 Pool

**Date:** 2026-05-21  ·  **Pool:** 770 pairs (التَّمريرة الأُولى ≥0.65 output)  ·  **Rater B:** Pass 2 calibrated

Every pair in the ≥0.65 pool was re-scored by Pass 2 under the same calibrated Eye-2 prompt that التَّمريرة الأُولى had: Juthoor thesis, polysemy rule, multi-step chains, method tags, calibration anchors from confirmed Tier-A cognates. The original التَّمريرة الأُولى bulk pipeline produced 770 pairs at ≥0.65; the IRR-150 audit on this same pool found التَّمريرة الأُولى was lenient at the 0.65 boundary. This document replaces the IRR-150 estimate with the actual re-scoring of all 770. These are the calibrated numbers the dashboard headlines.

## Aggregate counts (Pass 2 calibrated on the 770 pool)

| Threshold | التَّمريرة الأُولى pipeline (original) | Pass 2 calibrated (corrected) | Change |
|---|--:|--:|---|
| ≥ 0.95 (near-identical) | 57 | **18** | -39 |
| ≥ 0.80 (strong) | 134 | **120** | -14 |
| ≥ 0.65 (likely) | 770 | **189** | -581 |
| ≥ 0.50 (plausible) | 770 | **242** | -528 |

**Statistics:** Pearson r = **+0.6678** · Mean absolute difference = 0.382

## Per-language calibrated counts

| Language | n | ≥0.65 | ≥0.8 | ≥0.95 |
|---|--:|--:|--:|--:|
| non | 349 | 38 | 23 | 0 |
| grc | 344 | 113 | 71 | 17 |
| cy | 24 | 4 | 2 | 0 |
| ang | 22 | 12 | 8 | 1 |
| lat | 15 | 9 | 5 | 0 |
| got | 10 | 8 | 7 | 0 |
| sga | 6 | 5 | 4 | 0 |

## Migration matrix (التَّمريرة الأُولى bucket → التَّمريرة الثانية bucket)

Read row-wise: of the pairs التَّمريرة الأُولى placed in this bucket, how many did Pass 2 calibrated place in each التَّمريرة الثانية bucket?

| التَّمريرة الأُولى ↓  /  التَّمريرة الثانية → | weak | plausible | likely | strong | row total |
|---|---:|---:|---:|---:|---:|
| **likely** | 522 | 46 | 40 | 28 | 636 |
| **strong** | 6 | 7 | 29 | 92 | 134 |

## Key findings

1. **Strong-bucket survival: 92/134 = 69%.** Pairs التَّمريرة الأُولى rated ≥0.8 that Pass 2 calibrated also rates ≥0.8.
2. **Likely-bucket drop-rate: 20/636 = 82% drop below 0.5.** Most of Pass 1 0.65-0.79 zone re-buckets to weak under calibrated re-read.
3. **New headline number at ≥0.65: 189** (was 770). The ~3.5× reduction confirms the IRR-150 extrapolation.
4. **New headline at ≥0.8: 120** (was 134, ≈ 90% retained).
5. **New headline at ≥0.95: 18** (was 57, ≈ 32% retained).

## What this audit settles

- The dashboard's published aggregate counts are now grounded in **a full pool re-scoring**, not an extrapolation from a sample.
- The Tier-A 19 and Tier-B 50 sit inside the ≥0.65 calibrated bucket and survive; the curated headline rosters remain intact.
- The 581 pairs that dropped below 0.65 under calibrated re-read are not deletions — they remain in the discoveries dashboard with both A and B scores visible, letting any reader see the calibration disagreement directly.
- This is the corrected baseline for any future cross-branch or per-language audit.

— end —
