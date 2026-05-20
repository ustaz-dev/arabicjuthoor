# Held-out validation · 16 COHERENT lexical gaps

> The Arabic version is at [`2026-05-20-coherent-gaps-held-out-ar.md`](2026-05-20-coherent-gaps-held-out-ar.md).
>
> **Status:** Predictions registered. Dictionary search pending — see protocol below.

## The setup

The [scaled-up generative test](../03-scholar-extracts/lexical-gaps-generative-test-full.md) on the 155 alleged lexical-gap binaries identified **16 cases tagged COHERENT** — pairs where the framework produces a clean, internally-consistent compositional reading but no attested trilateral root uses the pair as L1·L2.

These 16 are the natural **held-out validation set** for the framework's generative power: each one is an *unforced* prediction the framework would make if asked "what would XY-something-mean if Arabic used it?" If Arabic in fact has rare or dialectal words at these slots — recorded in classical lexicons like *Lisān al-ʿArab* or *Tāj al-ʿArūs* but missed by Jabal's curated 453-nuclei list — the framework's prediction can be tested against actual attested semantics.

This document **pre-registers a specific semantic prediction for each of the 16**, then sets a protocol for a classical-lexicon search. The 16 predictions are committed to git **before** any lexicon search begins.

## The 16 COHERENT gaps with pre-registered semantic predictions

For each binary L1·L2, we register:
- **Reading:** the framework's compositional reading of the binary nucleus
- **Predicted semantic field:** one or two specific senses the framework expects
- **Predicted mode bias:** based on the L1·L2 charge profile, the mode any trilateral X·Y·L3 would tend toward

| # | Binary | Reading | Predicted semantic field | Predicted mode bias |
|--:|---|---|---|---|
| 1 | **ي·غ** | gentle concealment, soft covering | soft-veil, faint dimming, light haze | HOLD (the gentleness contains the cover) |
| 2 | **ي·ف** | gentle parting | soft opening, gentle separation, easy yielding | RELEASE (gentle parting outward) |
| 3 | **ظ·ج** | prominent gathering | public assembly, visible coming-together, manifest crowd | OPERATE (prominence acts on gathering) |
| 4 | **ه·ث** | soft-breath-scattering | whispered dispersal, slight breath-scatter, sigh-spreading | CHANNEL (breath directs scatter) |
| 5 | **ه·غ** | soft concealment | gentle veiling, soft hiding, faint cover (lighter than غـ alone) | HOLD |
| 6 | **ج·خ** | gathered piercing | gathered-burst-through, concentrated penetration, focused thrust | OPERATE / PROJECT |
| 7 | **ش·ذ** | scatter + sharp-internal | scattering-by-piercing, branching with sharp internal turn, splintering | CHANNEL (scatter directs sharp) |
| 8 | **خ·ج** | piercing + gathered | piercing-into-enclosure, breaching a contained space, penetrating a vessel | OPERATE |
| 9 | **خ·ع** | piercing + deep-grip | sharp internal grip, piercing-then-holding, sharp clamp | HOLD (after the pierce) |
| 10 | **غ·ح** | covered + warmth | warmth-under-cover, broiling, smouldering, hidden heat | HOLD (cover contains warmth) |
| 11 | **غ·ذ** | covered + sharp-internal | piercing-from-cover, hidden-sharp, stealth-strike (like food sneaking) | CHANNEL |
| 12 | **ك·ج** | sealed + gathered | sealed-vault, locked enclosure, sealed compartment | HOLD |
| 13 | **ل·خ** | bridge/extend + piercing | piercing-through-link, decisive thread, cutting through a connection | OPERATE |
| 14 | **ذ·ف** | sharp-internal + parting | sharp-cleave, decisive cleavage, sharp peeling | RELEASE / OPERATE |
| 15 | **ط·خ** | heavy + piercing | heavy-piercing, drill, forceful puncture | OPERATE (heavy drives pierce) |
| 16 | **و·خ** | bound + piercing | bound-perforating, stitching, threading-through | CHANNEL (bind directs pierce) |

## Search protocol (committed before the search)

To test these predictions against classical attestations:

1. **Sources** (in this order):
   - Ibn Manẓūr, *Lisān al-ʿArab*
   - al-Zabīdī, *Tāj al-ʿArūs*
   - Ibn Fāris, *Maqāyīs al-Lugha*
2. **Search method:** for each of the 16 binaries, look up any trilateral entry with that L1·L2 as the first two consonants. Many of these will be entries Jabal excluded (rare, dialectal, semi-attested, or with multiple variants).
3. **Per-attestation grading**, decided blind to the predicted semantic:
   - **HIT** — an attested word's meaning matches the predicted semantic field within ±1 conceptual step
   - **PARTIAL** — an attested word exists with this L1·L2 but means something the framework did not predict (the word exists; the prediction missed its sense)
   - **GHOST** — no real entry, only a denominal or onomatopoeic noun without core meaning
   - **MISS** — no attested entry at all under L1·L2 in any of the three lexicons
4. **Reporting:** a follow-up audit doc `2026-05-20-coherent-gaps-results.md` lists each of the 16 with its grade, plus an aggregate.

## Pre-registered scoring threshold

| Aggregate result | Verdict for the framework's generative claim |
|---|---|
| ≥ 6 of 16 HIT | 🟢 **VALIDATED** — the framework predicts unused-pair semantics with material accuracy |
| 3–5 of 16 HIT | 🟡 **PARTIAL** — the framework shows generative signal but is not yet a reliable predictor of held-out semantics |
| ≤ 2 of 16 HIT | 🔴 **NOT VALIDATED** — the framework is interpretive, not generative, at this granularity |

The thresholds are calibrated to chance: with ~10 broad semantic fields the framework distinguishes (cut, flow, bind, scatter, project, gather, hold, etc.), pure-chance prediction of one field per binary would yield roughly 1.6 HITs out of 16. Beating that comfortably (≥ 6 = ~4× chance) constitutes evidence; landing near or below chance (≤ 2) constitutes negative evidence.

## Why this matters

The framework already has the [scaled-up generative test](../03-scholar-extracts/lexical-gaps-generative-test-full.md) showing 74.4% of non-structural lexical gaps yield a defensible compositional reading. But "defensible" is internal coherence, scored by us. The HIT/MISS protocol here tests against an **external standard**: the classical-lexicographic corpus we did not consult when generating the predictions.

A high HIT rate would be the strongest evidence to date that the operative grammar is genuinely generative — predicting what unused binaries *should* mean, then being right about a non-trivial number of them when checked against attested but rare classical Arabic.

— end —
