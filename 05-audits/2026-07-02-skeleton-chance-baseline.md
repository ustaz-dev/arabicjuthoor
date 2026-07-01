# Skeleton-collision chance baseline for the first bar

**Date:** 2026-07-02
**Script:** [`scripts/layer_2/chance_baseline.py`](../scripts/layer_2/chance_baseline.py) (reproducible)
**Status:** first-order estimate, all assumptions stated below

## Why this exists

Once the cross-linguistic evidence is read as a pervasive distribution rather than a curated list, the load-bearing claim becomes "the correspondence is above chance." That word "chance" has to be a number, not a gesture. This audit computes the simplest honest one: under Khshim's substitution rules (the rubric's first bar), how often would two unrelated words share a consonant skeleton by accident? That figure bounds the false-positive rate of the skeleton bar on its own, and it is the reason the rubric does not stop at the skeleton.

## Method (first-order, assumptions stated)

1. **Substitution sets.** The 28 Arabic consonants are grouped into Khshim's classes (laws 1 to 9) plus the empirically-surfaced tenth (ط↔t): gutturals/laryngeals, the K/Q/j velars, the sibilant clade, the dental/emphatic group, liquids/nasals, labials, and the glides. Membership overlaps (م is both nasal and labial, ص both sibilant and velar-linked); that overlap is exactly what makes the laws permissive, and it is kept. `subs(a)` is the union of every set that contains `a`, plus identity.
2. **Frequency.** Each consonant's frequency `f(a)` is measured from the pooled Arabic forms of all nine cross-linguistic rosters (807 forms, 2,467 consonant tokens): a real, in-domain distribution, not an assumption.
3. **Match.** Two independently drawn consonants match iff each lies in the other's `subs` set. The per-position match probability is `q = Σ f(a) f(b) [match]`. Both draws are modelled from the Arabic inventory and frequency; that is the main simplification (a fuller model would use each target language's own inventory).
4. **Skeleton.** An aligned skeleton of length L matches by chance about `q**L`.

## Result

- Average substitution-set size is about 4.9 of 29 symbols: a consonant is "allowed" to match roughly 17% of the inventory. The laws are permissive by design.
- Per-position match probability: **q ≈ 0.188** (frequency-weighted; 0.168 uniform).

| skeleton length | chance of a random match |
|---|---|
| 2 consonants | **≈ 3.5%** |
| 3 consonants | **≈ 0.7%** |
| 4 consonants | **≈ 0.12%** |

A 3-consonant match is about **5x rarer** than a 2-consonant one. Every current dashboard window is 3 consonants or more (qarn, thawr, zawj, jamal, sabʿ, thalath = 4, salam, rabb).

## What this does and does not say

- **It bounds the skeleton bar's false-positive rate.** For a 3-consonant candidate the skeleton bar alone waves through a coincidence under 1% of the time; for a 2-consonant candidate, over 3%, which is not negligible. This is precisely why short-skeleton pairs (for example Gemini on a two-consonant G-M) are footnoted or dropped, and why the rubric requires three more bars (nucleus identity, reader-recognition, dual-family) on top of the skeleton.
- **It is a lower bound, not a ceiling.** The model assumes strict position-by-position alignment. Allowing metathesis or a length mismatch, which real matching does, only increases the chance rate, so the true false-positive figure is somewhat higher than `q**L`. The order of magnitude is the honest takeaway: 3-consonant matches are rare, 2-consonant matches are cheap.
- **It is about the skeleton, not the whole claim.** It is not a p-value for "one original tongue." It quantifies one bar. The nucleus-identity and dual-family bars, and the per-language top-tier rates over stated samples, carry the rest, and a random skeleton collision carries none of the shared meaning that those bars test.
- **It uses an Arabic-inventory model of the target.** Real target languages differ; refining with per-language inventories is the natural next step (see the rigor-upgrade plan).

## How it feeds the rigor upgrade

This is the "chance baseline" leg of [`cross-linguistic-rigor-upgrade.md`](../04-cross-linguistic/cross-linguistic-rigor-upgrade.md). It makes "above chance" concrete for the skeleton bar. The remaining legs are the per-branch regular-correspondence tables (replacing permissive swaps with predictive rules) and the borrowing screen. With those in place, each pair carries a stated rule, a chance figure, and an inheritance-versus-borrowing route.
