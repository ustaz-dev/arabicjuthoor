# Pass 3 · Generative Test on Open (Unused) Quadriliterals

## What Pass 3 tests

Pass 1 and Pass 2 showed the framework can *read* attested quadriliterals at ~98% native fit. That is interpretive power: given any existing Arabic 4-letter root, the framework produces a coherent compositional reading.

Pass 3 asks the harder, generative question: **for a quadriliteral the framework has never seen, can it predict what the word would mean if Arabic used it?**

This is the quadriliteral-level analogue of the [16 COHERENT binary held-out test](../05-audits/2026-05-20-coherent-gaps-held-out.md), which validated the framework's generative claim at the binary-nucleus level (≥0.65 hit rate, 6 strong matches out of 16). At the quadriliteral level the test has more degrees of freedom (the mode-selection rule under B-on-B, the augment-letter functions under T+A) and therefore is a tougher discipline.

## Method

1. **Select 20 quadriliteral skeletons** that combine two attested binaries into a B-on-B pattern the framework has not catalogued. Each skeleton is phonotactically permissible (no XX repetition, no same-articulator-class clash, no alif as L1).
2. **For each skeleton, apply the framework's grammar in advance:**
   - Identify B1 (L1·L2) and B2 (L3·L4) with their charges.
   - Apply the interface-charge mode-selection rule (Pass 2 finding): flow interface → CHANNEL/CARRY, mass interface → HOLD, sharp interface → OPERATE, etc.
   - Write a specific semantic prediction.
3. **Pre-register** the prediction with the selection rule, the charge analysis, the predicted mode, and the predicted semantic field — *before* searching for attestation.
4. **Search classical Arabic lexicography** (Lisān al-ʿArab, Tāj al-ʿArūs, Maqāyīs al-Lughah, Tāj al-Lughah, classical dialect dictionaries) for any attested word matching the skeleton.
5. **Grade each candidate** blind to the framework's prediction:
   - **HIT** — attested word's meaning matches the predicted semantic field within ±1 conceptual step
   - **PARTIAL** — attested word exists with this skeleton but means something the framework did not predict
   - **PHONOMIMETIC** — attested but the word is sound-symbolic and outside the semantic-composition scope
   - **MISS** — no attested word at this skeleton in classical sources

## Honest preamble on rater identity

The Pass 2 model is the rater here. As a Pass 2 model trained on classical Arabic lexicography, it likely has implicit lexical knowledge of which of these skeletons exist. The audit discipline is therefore not "score blind to attestation" but rather: **register a specific predicted semantic before checking; grade strictly on whether the attestation matches the specific prediction, not on whether *something* is attested**. The harder discipline is the prediction's specificity, not the rater's amnesia.

## Pre-registered scoring threshold

| Aggregate result | Verdict for the framework's generative claim at the quadriliteral level |
|---|---|
| ≥ 8 of 20 HIT | 🟢 **VALIDATED** — framework predicts quadriliteral semantics with material accuracy |
| 4–7 of 20 HIT | 🟡 **PARTIAL** — generative signal present but weaker than at the binary level |
| ≤ 3 of 20 HIT | 🔴 **NOT VALIDATED** — the framework is interpretive at the quadriliteral level, not generative |

Pure-chance prediction across ~10 broad semantic fields would yield roughly 2 of 20 by chance. The 8-hit threshold is ~4× chance.

## The 20 pre-registered predictions

For each, the table records: skeleton · binaries · charges · framework's predicted mode and semantic.

| # | Skeleton (L1·L2·L3·L4) | B1·B2 split | Charges (L1·L2 / L3·L4) | Mode | Pre-registered semantic prediction |
|--:|---|---|---|---|---|
| 1 | ث·ر·ج·ل (th-r-j-l) | (ث·ر) · (ج·ل) | scatter-flow / gather-extend | CARRY | a stretched scattered-flow gathered into long thin column — *file, queue, columnar drift* |
| 2 | ك·ل·ز·ف (k-l-z-f) | (ك·ل) · (ز·ف) | seal-extend / thrust-part | OPERATE | sealed-extended thing operates a thrust-parting — *spring-loaded ejector, the latch that snaps open* |
| 3 | س·م·ر·ج (s-m-r-j) | (س·م) · (ر·ج) | flow-mass / flow-gather | CHANNEL | thick-streaming flow channels gathering — *thick-pooling-pour, syrupy collection* |
| 4 | ف·ل·ز·م (f-l-z-m) | (ف·ل) · (ز·م) | part-extend / thrust-mass | PROJECT | parted-extended thing projects a thrust-mass — *splintered hurled chunk, fragment hurled forward* |
| 5 | ج·ث·ر·ب (j-th-r-b) | (ج·ث) · (ر·ب) | gather-scatter / flow-attach | MIX | gather-scattering mixed with flow-attach — *patchy clinging stir, lumpy-adhering swirl* |
| 6 | ن·ك·ز·ل (n-k-z-l) | (ن·ك) · (ز·ل) | resonance-seal / thrust-extend | BLOCK | sealed-resonance blocks a thrust-extending — *stopped-snapped echo, muted ringing-cut* |
| 7 | خ·ر·م·ج (kh-r-m-j) | (خ·ر) · (م·ج) | pierce-flow / mass-gather | OPERATE | pierce-flow operates on a mass-gathering — *boring through a pile, drilling-pile* |
| 8 | ع·ز·ل·ف (ʿ-z-l-f) | (ع·ز) · (ل·ف) | deep-thrust / extend-part | PROJECT | deep-thrust projects an extending-parting — *force-driven slip, deep-shove slide-out* |
| 9 | ت·ب·ل·ز (t-b-l-z) | (ت·ب) · (ل·ز) | sharp-attach / extend-thrust | OPERATE | sharp-attaching operates an extending-thrust — *precise pressing strike, surgical push-out* |
| 10 | ف·ث·ر·م (f-th-r-m) | (ف·ث) · (ر·م) | part-scatter / flow-mass | DRAIN | part-scattering drains a flow-mass — *leak that disperses a body, breaking-down-drain* |
| 11 | خ·ل·ج·ز (kh-l-j-z) | (خ·ل) · (ج·ز) | rarefy-extend / gather-thrust | RELEASE | rarefied-extending releases a gathered-thrust — *expanding outward push, opening-spring* |
| 12 | ز·ر·ك·ل (z-r-k-l) | (ز·ر) · (ك·ل) | thrust-flow / seal-extend | CHANNEL | thrust-flow channels a sealed-extending — *directed binding flow, guided lacing* |
| 13 | ج·ل·ر·م (j-l-r-m) | (ج·ل) · (ر·م) | gather-extend / flow-mass | HOLD | gather-extending holds a flow-mass — *bundled retained substance, tied-pouch* |
| 14 | ث·م·ر·ج (th-m-r-j) | (ث·م) · (ر·ج) | scatter-mass / flow-gather | MIX | scatter-massing mixes a flow-gathering — *broken-fluid coagulation, lumpy mixture* |
| 15 | ز·ج·ر·ف (z-j-r-f) | (ز·ج) · (ر·ف) | thrust-gather / flow-part | PROJECT | thrust-gathering projects a flow-parting — *explosive splash, jet-burst* |
| 16 | ل·ق·م·ز (l-q-m-z) | (ل·ق) · (م·ز) | extend-cut / mass-thrust | OPERATE | extend-cutting operates a mass-thrust — *elongated snapping jolt, long quick bite* |
| 17 | ك·ر·ف·ج (k-r-f-j) | (ك·ر) · (ف·ج) | seal-flow / part-gather | CHANNEL | seal-flow channels a part-gathering — *enclosed streaming compartment, chambered duct* |
| 18 | ب·ث·ر·ز (b-th-r-z) | (ب·ث) · (ر·ز) | attach-scatter / flow-thrust | MIX | attach-scattering mixes with flow-thrust — *rough-bumping stir, uneven driving-mix* |
| 19 | ر·ث·ك·ز (r-th-k-z) | (ر·ث) · (ك·ز) | flow-scatter / seal-thrust | BLOCK | flow-scattering blocked by seal-thrust — *diverted current stopped sharply, sealed-stop* |
| 20 | ع·ك·ر·ز (ʿ-k-r-z) | (ع·ك) · (ر·ز) | deep-seal / flow-thrust | HOLD | deep-sealing holds a flow-thrust — *trapped pulse, enclosed pressure-wave* |

Each prediction is committed to git before the search begins. The corresponding search-results document is at [`../05-audits/2026-05-21-pass3-evaluation.md`](../05-audits/2026-05-21-pass3-evaluation.md).

## What this audit settles or does not settle

Settles: whether the operative grammar's binary-on-binary mode-selection rule, validated at the quadriliteral level on attested entries in Pass 1 and Pass 2, also produces *predictively correct* semantics for unused quadriliterals.

Does not settle: the framework's ability to predict the *exact* surface form an Arabic word would take — that depends on prosodic patterns (وزن), morphological constraints, and historical accident the operative-grammar layer does not model.

— end —
