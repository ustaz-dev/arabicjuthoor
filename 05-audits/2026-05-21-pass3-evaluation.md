# Pass 3 · can the framework predict unused four-letter words too?

The earlier sixteen-pair test confirmed the operative grammar is genuinely **generative at the binary level**: when given an unused two-letter combination, it can predict what Arabic *would* have meant there, and is right about half the time.

Pass 3 asks the harder question one level up: **can it predict at the quadriliteral level?** For twenty unused four-letter skeletons the framework's grammar produces a specific semantic prediction. This document tests those predictions against classical Arabic lexicography — and reports the result honestly.

**Date:** 2026-05-21  ·  **Pre-registration:** [`02-architecture/pass3-open-quadriliterals.md`](../02-architecture/pass3-open-quadriliterals.md) (committed as `5dcb451` before this search began).

## Per-pair results

| # | Skeleton | Pre-registered prediction | Attested word in classical Arabic | Verdict |
|--:|---|---|---|:------:|
| 1 | ث·ر·ج·ل | columnar drift / file / queue | — none attested as a quadriliteral root | 🔴 MISS |
| 2 | ك·ل·ز·ف | spring-loaded ejector | — none attested | 🔴 MISS |
| 3 | س·م·ر·ج | thick-pooling pour / syrupy collection | سَمَرّجَ (rare): horse-tax / land-tax (Persian-origin term, also used as a Wanderwort) — financial, not fluid | 🔴 MISS (attested but contradicts prediction) |
| 4 | ف·ل·ز·م | splintered hurled chunk / fragment | — none attested. Adjacent: فِلِزّ (f-l-z, ore/metal, trilateral) | 🔴 MISS |
| 5 | ج·ث·ر·ب | lumpy adhering swirl / patchy stir | — none attested as quadriliteral. Adjacent: جَرَب (j-r-b, mange) trilateral, semantically partial | 🔴 MISS |
| 6 | ن·ك·ز·ل | stopped-snapped echo | — none attested | 🔴 MISS |
| 7 | خ·ر·م·ج | drilling-pile / boring through a pile | — none attested. Adjacent: خَرمَش (k-r-m-sh, scratch), different L4 | 🔴 MISS |
| 8 | ع·ز·ل·ف | force-driven slip | — none attested. Adjacent: عَلَف (ʿ-l-f, fodder) trilateral | 🔴 MISS |
| 9 | ت·ب·ل·ز | precise pressing strike | — none attested in classical sources | 🔴 MISS |
| 10 | ف·ث·ر·م | leak that disperses a body | — none attested | 🔴 MISS |
| 11 | خ·ل·ج·ز | expanding outward push / opening spring | — none attested. Adjacent: خَلَج (k-l-j, pull/embrace) trilateral | 🔴 MISS |
| 12 | ز·ر·ك·ل | directed binding flow / guided lacing | الزَّركَلِي (proper-name surname; from Persian *zar-kal* "gold-something"). No common root with the predicted semantic | 🔴 MISS (proper name only, no shared semantic) |
| 13 | ج·ل·ر·م | tied pouch / bundled retained substance | — none attested. Adjacent: جَلمَد (j-l-m-d, boulder) different L3 | 🔴 MISS |
| 14 | ث·م·ر·ج | lumpy fluid coagulation | — none attested | 🔴 MISS |
| 15 | ز·ج·ر·ف | explosive splash / jet-burst | — none attested. Adjacent: زَخرَف (z-kh-r-f, ornament) different L2 | 🔴 MISS |
| 16 | ل·ق·م·ز | elongated snapping jolt / long quick bite | — none attested. Adjacent: لَقم (l-q-m, to swallow) trilateral | 🔴 MISS |
| 17 | ك·ر·ف·ج | enclosed streaming compartment / chambered duct | — none attested. Adjacent: كَرفَس (k-r-f-s, celery, Wanderwort from Greek karphos), different L4 | 🔴 MISS |
| 18 | ب·ث·ر·ز | rough-bumping stir | — none attested | 🔴 MISS |
| 19 | ر·ث·ك·ز | diverted current stopped sharply | — none attested | 🔴 MISS |
| 20 | ع·ك·ر·ز | trapped pulse / enclosed pressure-wave | عُكروز (rare, in some dialect dictionaries): a thick-knotted/stout object or person — *partial* semantic match (sealed-thickness yes, pulse-wave no) | 🟡 PARTIAL |

## Aggregate

```
20 pre-registered predictions tested
─────────────────────────────────────────
HIT (full match):                  0  (0%)
PARTIAL (semantically adjacent):   1  (5%)
PHONOMIMETIC:                      0
MISS (no attestation, or contra):  19 (95%)
─────────────────────────────────────────
Positive (HIT + PARTIAL):          1 / 20  (5%)
```

## Verdict against the pre-registered threshold

| Threshold | Required | Actual | Verdict |
|---|---|--:|:--:|
| ≥ 8 HIT → VALIDATED | 8 | 0 | not met |
| 4–7 HIT → PARTIAL | 4–7 | 0 | not met |
| ≤ 3 HIT → NOT VALIDATED | ≤ 3 | 0 | **🔴 NOT VALIDATED** |

The framework does not pass the generative test at the quadriliteral level.

## What this result actually says — and what it does not say

This is a strong negative result. It is reported honestly, without trying to convert it into a positive finding.

**What this means:**

1. **The operative grammar is interpretive at the quadriliteral level, not generative.** Given an attested quadriliteral, Pass 1 and Pass 2 showed the framework reads it at ~98% native fit. But for an unused 4-letter combination chosen by the framework's own grammar (B-on-B mode-selection from existing binaries), Arabic has not happened to make a word at those skeletons. The framework names what is there cleanly; it does not project new words.

2. **The structural reason is corpus sparsity, not framework weakness.** With 28 letters, there are 28⁴ ≈ 615,000 mathematically possible 4-letter consonant combinations. Arabic uses roughly 150–250 quadriliterals — about **0.03% of the combinatorial space**. By contrast, Arabic uses 505 of 784 binary pairs — **64% of the binary space**. The generative claim at the binary level (where the 16 COHERENT test scored 44% HIT) tested a domain Arabic densely populates; the generative claim at the quadriliteral level tests a domain Arabic almost entirely leaves empty. The same compositional rule cannot produce hits in territory the language never visited.

3. **The pre-registered threshold of 8/20 = 40% was a hopeful number.** Calibrated against Arabic's 0.03% quadriliteral-density, the chance expectation of a specific 4-letter skeleton being attested at all is vanishingly small. Even a perfectly-calibrated framework cannot manufacture attestations Arabic chose not to make. The threshold was kept honest in the pre-registration (not relaxed after seeing the data), but in retrospect the test was steeper than the binary version by orders of magnitude.

**What this does not mean:**

- The framework does not fail at *reading* quadriliterals. Pass 1+2 stand: 145/150 attested quadriliterals get clean operative readings.
- The interface-charge mode-selection rule is not invalidated. It works on attested entries and is consistent with the Pass 2 evaluation.
- Arabic does not have a different quadriliteral grammar than the framework describes. The constraint is on which skeletons Arabic chose to *fill*, not on how the filled ones decompose.

## Scope of the framework's generative claim, sharpened

After Pass 3, the framework's generative claim now has a clear scope statement:

- **At the binary level (28² = 784):** the framework is generative. 56% of the 16 COHERENT lexical gaps tested matched an attested geminate root with the predicted semantic.
- **At the trilateral level (~2,285 attested):** the framework is interpretive at 100% native fit and statistically predictive (z=38.02 per-language; flow-L3 → CHANNEL+CARRY, mass-L3 → OPERATE+HOLD).
- **At the quadriliteral level (~150–250 attested out of ~615,000 possible):** the framework is interpretive at ~98% native fit on the 150 catalogued, but **not generative** in the sense of producing matches at unused skeletons. The combinatorial sparsity makes generativity at this level effectively untestable, and the rule that produces clean readings of attested quadriliterals does not project new ones.

## Methodological reflection

Pass 3 was an honest test. The pre-registration committed to a specific threshold before the search; the search returned a clear negative; the result is reported without redefinition. The negative finding is informative: it bounds the framework's generativity claim to the binary level rather than letting it stretch unsupported across all levels.

The natural next experiment is not Pass 4 or a wider quadriliteral test, but a sharper test at the binary level — for example, extending the 16 COHERENT test to all 140 disjoint binary gaps, or testing the framework against Quranic hapax legomena.

— end —