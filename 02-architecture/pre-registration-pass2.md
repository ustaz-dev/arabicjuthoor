# Pre-registration · Pass 2 (Quadriliteral Catalogue 50 → 150)

> The Arabic version is at [`pre-registration-pass2-ar.md`](pre-registration-pass2-ar.md).
>
> **Status:** Registered before Pass 2 scoring begins. Once any of the next 100 quadriliterals is processed, this document is frozen. The predictions below are then evaluated against the actual results.

## Why pre-register

Pass 1 of the [pilot catalogue](quadriliteral-pilot-catalogue.md) processed 50 quadriliterals and found 49 of 50 (98%) readable under one of two proposed paths (binary-on-binary, or trilateral-plus-augment / stacked). Pass 2 expands the sample by another 100 entries.

If we expand and report results without committing to predictions first, we expose the framework to **confirmation bias**: it becomes too easy to read each new entry favourably and tally "98% again." Pre-registering specific numerical and structural predictions turns Pass 2 from a confirmatory exercise into a genuine test that the framework could fail.

The predictions below are written **before** any of the 100 next quadriliterals is selected or scored. They are committed to git with this document. After Pass 2 ships, an evaluation table reports the actual outcome against each prediction, and a follow-up audit doc records the verdict.

## The 100 next quadriliterals — selection rule

To avoid cherry-picking, the next 100 entries will be drawn by the following rule, **fixed before scoring starts**:

1. Begin from a canonical Arabic lexicon (Jabal al-Lisān al-ʿArab + Tāj al-ʿArūs) sorted by quadriliteral entry.
2. Skip any entry already in the 50-pilot catalogue.
3. Take the next 100 in lexicographic order that meet:
   - exactly four consonants in the root (after stripping derivational morphology — augments, broken-plural alif, fem. ـة, etc.)
   - not a transparent loan that the loanword audit already covered
   - has at least one attested classical form (not exclusively modern coinage)
4. Process all 100 under both decomposition paths, blind to verdict expectations.
5. No replacement of "awkward" entries. The 100 are the 100.

## Pre-registered predictions

### P1 · Native-readable rate

**Prediction:** ≥ 92% of the next 100 (i.e. **≥ 92 of 100**) will read cleanly under one of:
- INTENSIFY-on-binary (reduplicated XYXY / XYYX),
- binary-on-binary (true quadriliteral with coherent B1-on-B2 reading),
- trilateral-plus-augment (the first three letters form a clean trilateral; the fourth letter is one of the documented augment-letter functions),
- stacked (quintiliteral with two binaries + augment).

**Pass condition:** ≥ 92 of 100 receive a non-UNRESOLVED verdict.
**Failure condition:** ≥ 9 of 100 receive UNRESOLVED.

*Rationale:* The pilot ran 49/50 = 98%. Pass 2 will likely include harder entries (longer, rarer, more foreign-sounding) — a 6-point safety margin acknowledges that without conceding the headline claim.

### P2 · Distribution across the three paths

The pilot's 49 successful entries split as: 17 Reduplication / 15 B-on-B / 17 T+A or stacked. Roughly 35% / 31% / 34%.

**Prediction:** On the next 100, the distribution will fall within these ranges (each path's share among readable entries):
- Reduplication: 15% – 45%
- B-on-B: 20% – 45%
- T+A or stacked: 20% – 50%

**Pass condition:** All three observed shares fall within their predicted ranges.
**Failure condition:** Any path's share falls outside its range (the framework's path-attribution is unstable).

*Rationale:* These are wide bands because the lexicographic-order selection makes the path mix unpredictable. But if (say) only 5% reduplicate, the pilot's path mix wasn't representative.

### P3 · Top augment letters

The pilot's 9 T+A entries used these augments: ـوت (4×: جبروت, رحموت, ملكوت, عنكبوت), م (2×: جهنّم, إبراهيم), ف (1×: زخرف), ن (1×: فرعون / كركدن stem), ك (handled under stacked).

**Prediction:** Among Pass 2's T+A and stacked entries, the **three most-frequent augment letters** will come from the set **{م, ن, ر, ل, و, ت, ـوت}**.

**Pass condition:** Top-3 augment letters by frequency are all members of that set.
**Failure condition:** A novel augment letter outside that set appears in the top 3 (the augment-table is incomplete).

*Rationale:* These are the eight augments the pilot induced. A surprise in the top 3 means our augment table is materially incomplete and needs updating — which is a finding, not a failure of the framework's grammar.

### P4 · Quranic-anchored entries

The pilot's 50 included 7 entries with explicit Quranic anchors (صَلصَل, سَلسَل, خَندَق, ضَفدَع, ملكوت, عنكبوت, فرعون). 7 of 7 read cleanly under one of the proposed paths.

**Prediction:** Among Pass 2's Quranic-anchored entries (expected count: 8–15 by lexicographic incidence), **≥ 95%** will read cleanly.

**Pass condition:** ≥ 95% of Quranic-anchored entries are non-UNRESOLVED.
**Failure condition:** ≥ 2 Quranic-anchored entries are UNRESOLVED (the framework breaks for Quranic vocabulary at this layer).

*Rationale:* The strong thesis of the project is that the Quranic vocabulary is fully native-readable. Pass 2 should not erode this for quadriliterals.

### P5 · UNRESOLVED residue and what it looks like

**Prediction:** The UNRESOLVED entries (expected ≤ 8 of 100) will fall into one of two patterns:
- **(a) Onomatopoeic / sound-symbolic** quadriliterals where neither B-on-B nor T+A yields a *semantic* reading because the word is essentially phonomimetic (e.g. animal calls, percussion sounds). These will be tagged `PHONOMIMETIC` rather than UNRESOLVED, and the framework will note them as outside its semantic-composition scope.
- **(b) Genuine residue** — entries where both paths can be attempted but neither closes cleanly. These are the honest gap and will be tagged UNRESOLVED.

**Pass condition:** ≤ 4 entries tagged UNRESOLVED (i.e. genuine residue ≤ 4%).
**Failure condition:** ≥ 5 entries tagged UNRESOLVED.

*Rationale:* The pilot's 1 UNRESOLVED (zanjabīl) was genuine path-competition, not phonomimetic. Pass 2 may surface more of both kinds, but genuine residue should remain small.

### P6 · Internal-consistency check on the augment-letter table

If the augment-letter table induced from 9 T+A entries is generalisable, then in Pass 2 the **same augment letter should perform the same function across new entries**.

**Prediction:** ≥ 80% of the augment-letter occurrences in Pass 2's T+A entries match the function in the pilot's induced table (e.g., final ـوت = abstract-state, final م = bounded-mass, final ف = surface-display, final ن = permanent-state, etc.).

**Pass condition:** ≥ 80% augment-function matches.
**Failure condition:** < 70% match (the augment table is over-fit to the 9 pilot entries).

## Falsification table

If Pass 2 results trigger any of the following, the framework needs revision before further claims rest on it:

| Trigger | Implication |
|--------|-------------|
| < 90 of 100 readable | Native-readable claim drops from "near-universal" to "strong majority" — recalibrate dashboard |
| Path-mix outside P2 ranges | Pilot path attribution was sample-specific, not structural |
| Top-3 augments include a novel letter | Augment table is incomplete; do not claim closure on T+A |
| ≥ 2 Quranic entries UNRESOLVED | Quranic-native thesis weakens at quadriliteral layer |
| ≥ 5 UNRESOLVED total | The framework has a class-of-residue we haven't characterised |
| Augment-function match < 70% | The augment-table generalises poorly; T+A path needs more grounding |

## How Pass 2 reports

After scoring, the team produces:

1. **`quadriliteral-pilot-catalogue.md` v2** — expanded to 150 entries.
2. **`pass2-evaluation.md` (+AR)** — a new audit doc with one row per prediction:
   - Prediction · Pass condition · Actual outcome · Verdict (PASS / FAIL / EDGE)
3. **Honest dashboard sweep** — any failed prediction is reflected on the dashboard's stat strip and the quadriliteral section.

## Reproducibility

- This file is committed to git **before** any of the 100 next entries is selected or scored.
- The lexicographic-order selection rule and exclusions are recorded here, so the 100 entries are deterministic given the lexicon.
- After Pass 2, the audit doc compares actuals against the pre-registered conditions. No condition is added or relaxed post-hoc.

— end —
