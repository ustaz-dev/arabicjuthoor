# Blind second reading of the 2,285 mode assignments: measured result

**Date:** 2026-07-06
**Pre-registration:** [`02-architecture/pre-registration-blind-rerating.md`](../02-architecture/pre-registration-blind-rerating.md) (committed 2026-07-05, before any run)
**Data:** `computational/data/layer_2_pass2.jsonl` (Pass 2), `pass2_adjudications.json` (adjudication), `layer_2_results_v2.jsonl` (Pass 1)
**Scripts:** `scripts/layer_2/compare_pass2.py`, `scripts/layer_2/resolve_adjudication.py` (reproducible)

This is reported exactly as measured, per the pre-registration's commitment. It is neither softened nor inflated.

## What was tested, and what was not

The test targets one layer only: the assignment of one of the eleven operative modes (plus LOANWORD) to each root. It does **not** test the 28 letter-charges, the 453 nucleus readings, or Jabal's axial meanings; the blind reader received those as given and only judged the mode. So nothing here bears on whether the charges are real or the nucleus readings sound. What it measures is narrower and specific: **can an independent reader, holding the same rubric, reproduce the mode call?**

## The measurement

A blind second reader (Pass 2) re-rated all 2,285 roots, seeing only the root, its nucleus, the nucleus reading, Jabal's axial meaning, and the third radical's fixed charge. The Pass 1 mode was withheld. Full coverage, no invalid modes.

| Level of agreement | Result |
|---|---|
| Same exact mode | **866 / 2,285 = 37.9%** |
| Cohen's kappa (chance-corrected) | **0.305** (chance-expected 10.6%) |
| Same stance, different mode | 545 / 2,285 = 23.9% |
| Different stance entirely | 874 / 2,285 = 38.2% |
| Same stance (positive / negative / transform) | **1,411 / 2,285 = 61.8%** |

**The honest headline: fine-grained mode agreement is fair, not strong** (kappa 0.305 sits in the "fair" band, 0.2 to 0.4). The pre-registered prediction of *high* mode-level agreement did **not** hold. Stance is more reproducible than the specific mode (62% vs 38%), but even a third of roots are sorted to a different stance, so stance is only fairly reproducible too.

## Where the disagreement lives (the pre-registered structural prediction held)

The disagreements are not scattered uniformly; they concentrate, exactly as pre-registered. The single largest driver is one mode:

**Pass 1 assigned OPERATE to 558 roots (24.4% of the whole corpus), by far the most of any mode.** On the blind re-read, only 159 of those 558 (28.5%) stayed OPERATE. The other 399 were redistributed across the taxonomy, and across stances:

| Pass 2 re-sorted Pass 1's OPERATE to | count | stance |
|---|---|---|
| (kept) OPERATE | 159 | transform |
| DRAIN | 73 | negative |
| CHANNEL | 52 | transform |
| CARRY | 51 | positive |
| HOLD | 51 | positive |
| RELEASE | 48 | positive |
| MIX | 34 | transform |
| INTENSIFY | 26 | positive |
| REVERT | 23 | transform |
| PROJECT | 23 | positive |
| BLOCK | 18 | negative |

This is the signature of a **catch-all default**: OPERATE ("modifies L3 via squeeze, fold, or cut") is broad enough that Pass 1 reached for it when a more specific mode was arguable, and a fresh reader spreads those calls out. The other soft boundaries are the same shape: HOLD/BLOCK, HOLD/INTENSIFY, PROJECT/CHANNEL, HOLD/MIX.

## The adjudication, and its honest limit

Every one of the 1,419 disagreements went to a third blind reading that saw the two candidate modes **unlabelled and in randomized order** (50% flipped by a deterministic hash; the key was never shown to the adjudicator). Result over 1,419:

- Sided with the Pass 2 (fresh-reader) call: **1,206 = 85.0%**
- Sided with the Pass 1 (original) call: **168 = 11.8%**
- Judged both genuinely defensible: **45 = 3.2%**
- Within the 399 OPERATE-origin disputes: 89% to Pass 2, 9% to Pass 1, 2% both.

**Methodological limit, stated plainly.** The adjudicator is the same kind of reader as Pass 2 (a fresh reader working from the same thin rubric), so it shares Pass 2's priors. Therefore this 85% is **not** evidence that "Pass 2 is the truth", and the master data is **not** being rewritten toward Pass 2 on the strength of it. The one robust thing the adjudication adds, on top of the raw kappa (which needs no adjudicator at all), is corroboration that Pass 1's specific calls, above all its OPERATE calls, are usually not the best-fitting mode when re-examined, which points at the **mode definitions**, not the roots.

## What this means

1. **The core is untouched.** Charges, nucleus readings, and Jabal anchors were not tested here and are not in question.
2. **The eleven-mode assignment is single-rater-interpretive at the fine grain.** "Every root fits a mode without forcing" remains true in the weak sense (every root reads under some mode), but *which* mode is not reliably reproducible from the current rubric (kappa 0.305). The paper must say this.
3. **The framework predicted this.** `lv2-operative-grammar.md` already noted the eleven modes are "open to refinement, some may collapse together, others may split." The data now shows exactly where: OPERATE is over-broad and should be tightened or split, and its boundaries with DRAIN, CHANNEL, CARRY, HOLD are soft.

## The sharpening path (what earns a re-run)

- **An example-anchored coding manual.** The canon `lv2-operative-grammar.md` carries worked examples per mode; the Pass 2 / adjudication rubric carried only the one-line definitions. A manual that hands the reader two or three decided exemplars per mode, and explicit tie-break rules for the soft boundaries, is the first fix.
- **Reconsider OPERATE.** Either a narrower definition (reserve it for genuine squeeze/fold/cut and route the rest) or an explicit split.
- **Then re-rate blind** against the improved manual and re-measure kappa. That is the honest way to raise reproducibility, not by overwriting the data.

## Publication commitment honored

All figures above are the measured values. The full per-root Pass 2 calls, the disagreement list, and every adjudication with its grounds are in the data files named at the top. The position paper's honest-status note and the dashboard roadmap are updated to this measured result, not to a claimed success.
