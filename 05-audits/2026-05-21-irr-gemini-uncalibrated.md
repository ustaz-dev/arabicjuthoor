# Wrong-Test Transparency Doc · Gemini 2.5 Pro IRR (un-calibrated)

> ⚠️ **This is preserved as a transparency record of a methodologically wrong test.** Do not cite the κ=0.058 number as a finding about the project's methodology. See the corrected IRR at [`2026-05-21-inter-rater-agreement.md`](2026-05-21-inter-rater-agreement.md).
>
> **Why this test was wrong:** Gemini 2.5 Pro was given a stripped-down prompt — no Juthoor thesis, no calibration anchors, no method tags (masadiq_direct / mafahim_deep / combined), no polysemy rule, no multi-step-chain instruction. Gemini's training data is dominated by mainstream IE comparative philology, a paradigm that by default does not recognise deep Arabic ↔ IE cognates. Asking that paradigm to validate findings that the Juthoor methodology was specifically constructed to surface is broken from the start.
>
> What this test actually measured: paradigm alignment between mainstream comparative philology and the Juthoor rubric. The answer (predictably) is "they disagree" — which is the project's thesis, not a refutation of it.
>
> The correct IRR test (calibrated Opus vs Sonnet pipeline) is at [`2026-05-21-inter-rater-agreement.md`](2026-05-21-inter-rater-agreement.md) and shows Pearson r = 0.520, with 78% survival of the `strong` (≥0.80) bucket.

**Date:** 2026-05-21  ·  **Sample size:** 150 pairs (stratified random from the 770-cognate pool at score ≥ 0.65)

> Rater A is the original pipeline (Sonnet 4.5 bulk + Opus deep-review). Rater B is **Gemini 2.5 Pro with an UN-calibrated prompt**. Different model families AND different rubrics.

## Headline

| Metric | Value | Interpretation |
|---|---:|---|
| Pearson correlation r | **+0.2170** | how linearly do raw scores agree |
| Spearman rank ρ | **+0.1072** | how do rank orderings agree |
| Mean absolute difference | 0.357 | average score gap on a 0–1 scale |
| Cohen's κ (unweighted) | **+0.0585** | 🔴 slight — strict 4-bucket agreement |
| Cohen's κ (quadratic-weighted) | **+0.0746** | 🔴 slight — ordinal-distance-aware agreement |

Buckets used for κ: `weak` (<0.50) · `plausible` (0.50–0.64) · `likely` (0.65–0.79) · `strong` (≥0.80).

## Confusion matrix

Rows = rater A (Sonnet), columns = rater B (Gemini). Cell = number of pairs both rated in those buckets.

| A ↓  /  B → | weak | plausible | likely | strong | row total |
|---|---:|---:|---:|---:|---:|
| **weak** | 0 | 0 | 0 | 0 | 0 |
| **plausible** | 0 | 0 | 0 | 0 | 0 |
| **likely** | 61 | 19 | 11 | 32 | 123 |
| **strong** | 9 | 2 | 1 | 15 | 27 |
| **col total** | 70 | 21 | 12 | 47 | **150** |

## Per-language Pearson

| Language | n | Pearson r |
|---|--:|---:|
| non | 68 | +0.098 |
| grc | 66 | +0.274 |
| cy | 5 | +0.361 |

## Bucket distribution per rater

| Bucket | A (Sonnet) | B (Gemini) |
|---|--:|--:|
| weak | 0 | 70 |
| plausible | 0 | 21 |
| likely | 123 | 12 |
| strong | 27 | 47 |

## Top 10 most-disagreed pairs (|A − B| desc)

| idx | Arabic | Target | Lang | A | B | Δ |
|---|---|---|---|---:|---:|---:|
| 114 | دحر | aldr | non | 0.95 | 0.00 | 0.95 |
| 28 | سرال | israel | got | 0.90 | 0.00 | 0.90 |
| 103 | الشمس | παραλληλισμός | grc | 0.87 | 0.00 | 0.87 |
| 116 | دلنظ | σάνδαλον | grc | 0.85 | 0.00 | 0.85 |
| 70 | رتل | ἀρτίαλα | grc | 0.72 | 0.00 | 0.72 |
| 99 | الحوث | ἀλλαχόθι | grc | 0.72 | 0.00 | 0.72 |
| 66 | الثقب | βελοθήκη | grc | 0.71 | 0.00 | 0.71 |
| 17 | اقفعلت | cofleidio | cy | 0.70 | 0.00 | 0.70 |
| 18 | شغموم | skammar | non | 0.70 | 0.00 | 0.70 |
| 25 | حتر | hindar | non | 0.70 | 0.00 | 0.70 |

## Interpretation

- **Unweighted κ = 0.058** is below the substantial-agreement threshold. The raters disagree on bucket assignments more than the 4-category structure can absorb. A re-prompt for the 0.50/0.65 boundary or a coarser bucketing (e.g., binary: ≥0.65 vs <0.65) is the natural next step.
- **Quadratic-weighted κ = 0.075** treats one-bucket disagreements (e.g., 'likely' vs 'plausible') as small errors rather than full disagreements. Where this exceeds unweighted κ, much of the apparent disagreement is between adjacent buckets rather than across distant ones.
- **Pearson r = 0.217** on raw 0–1 scores measures linear agreement before bucketing. Higher r means the raters' continuous-score gradients run in the same direction even where bucket boundaries split them.
- **Mean absolute difference = 0.357**: on the 0–1 scale, the average per-pair score gap. Smaller is better.

## What this audit settles

1. The framework's bucket assignments depend more on rater than the rubric ideally allows. The aggregate counts remain useful for distribution claims, but per-pair scores should be quoted with rater attribution.
2. The methodology should keep the single-rater caveat explicit, and ideally surface a 'high-IRR subset' (pairs where multiple raters agree) for any application that requires per-pair certainty.

## Caveats

- The sample is stratified random from the ≥0.65 pool, so it is well-populated at the 'likely+' end and lighter at the 'weak' end. Agreement could be lower if a wider score range were sampled.
- Rater B (Gemini) scored in batches of 30 to manage context length. Batch boundaries do not affect per-pair scores but may introduce small calibration drift across batches.
- The bucket thresholds (0.50 / 0.65 / 0.80) match the published rubric. Different thresholds would yield different κ.

— end —
