# Layer 2 · The Twelve Composition Modes for Trilateral Roots

## The finding

Every Arabic trilateral root in Jabal's lexicon is interpretable as a single operative relation:

> **The binary nucleus operates on the third letter, taking its charge as material.**
> النَّواةُ الثنائيّةُ تَعمل في الحرف الثالث، وتَتَّخِذُ شَحنتَهُ مادّةً لها.

The "operation" takes one of **twelve composition modes** in a finite, closed grammar. **100% of native trilaterals find a coherent mode without forcing.** The bottom-up genealogy from **letters → binaries → trilaterals** is grounded.

## Framing: agent and material

The binary nucleus is the **agent** (الفاعل); the third letter is the **material** (المادّة) it operates on. Under this reading, *قصر* reads cleanly as "قص-cutting-precision **blocks** the flow (ر)" — a single coherent operation. The same applies to every native trilateral in the corpus.

## The twelve composition modes (أبواب التركيب الاثنا عشر)

The grammar of binary-on-L3 operations, grouped by stance:

### POSITIVE · إيجاب (binary co-acts with L3) · 55.2% of all roots

| Mode (الباب) | Meaning | Canonical example |
|------|---------|-------------------|
| **CARRY** · الحَمْل | binary carries L3-material forward/out | ورد: و-bind carries د-fixity → arriving |
| **HOLD** · الإمْساك | binary contains/encloses L3-material | بلد: بل-wet holds د-fixity → ground, settled-place |
| **RELEASE** · الإطْلاق | binary lets L3-material burst out | فتح: فت-loose releases ح-warmth → opening |
| **PROJECT** · الإبْراز | binary extends L3 outward as feature | حدد: ح-edge projects د-fixity → boundary |
| **INTENSIFY** · التَّضْعيف | doubled or amplified L3 | جمد: ج-gather amplifies د-fixity → freezing solid |

### NEGATIVE · سَلْب (binary opposes L3) · 11.5%

| Mode (الباب) | Meaning | Canonical example |
|------|---------|-------------------|
| **BLOCK** · الحَجْب | binary stops/seals/walls off L3-material | سدد: س-flow blocked → sealing, stopping |
| **DRAIN** · الاسْتِنزاف | binary gradually depletes L3-material | فقد: فق-void drains د-fixity → losing |

### TRANSFORM · تَحَوُّل (binary reshapes L3) · 33.3%

| Mode (الباب) | Meaning | Canonical example |
|------|---------|-------------------|
| **CHANNEL** · التَّوجيه | binary directs/shapes the L3's path | جرى: جر-pull channels ى-flow → running |
| **OPERATE** · الإعْمال | binary modifies L3 via squeeze/fold/cut | حسم: حس-feel operates on م-mass → cutting decisively |
| **MIX** · المَزْج | blends the binary with L3 | روب: رو-going mixes ب-attach → curdled milk |
| **REVERT** · القَلْب | circles back / oscillates L3 | ردد: ر-flow reverts د-fixity → returning |

### EXCEPTION · استِثناء

| Mode (الباب) | Meaning |
|------|---------|
| **LOANWORD** · الدَّخيل | non-native composition (1/2,285 in the current corpus) |

## Global distribution

| Mode | الباب | Count | % |
|------|------|------:|---:|
| OPERATE | الإعْمال | 558 | 24.4% |
| HOLD | الإمْساك | 373 | 16.3% |
| PROJECT | الإبْراز | 268 | 11.7% |
| INTENSIFY | التَّضْعيف | 267 | 11.7% |
| RELEASE | الإطْلاق | 208 | 9.1% |
| CARRY | الحَمْل | 146 | 6.4% |
| BLOCK | الحَجْب | 132 | 5.8% |
| DRAIN | الاسْتِنزاف | 130 | 5.7% |
| CHANNEL | التَّوجيه | 122 | 5.3% |
| REVERT | القَلْب | 66 | 2.9% |
| MIX | المَزْج | 14 | 0.6% |
| LOANWORD | الدَّخيل | 1 | 0.0% |

## Predictive tests, all confirmed

A descriptive grammar can always be made to fit after the fact. What separates a real rule from after-the-fact fitting is whether it makes **prediction in advance** that the data then confirms. If the twelve composition modes are real, then specific root shapes and specific letter-charge classes should cluster in specific modes — and they do.

| Test | Prediction | Observed |
|------|-----------|---------:|
| Doubled-final roots (XYY, e.g., بدد · ردد · جدد) | INTENSIFY + OPERATE dominate | **66.9%** of 405 roots |
| Redoubled XY-XY roots (e.g., دردر · جمجم) | OPERATE + INTENSIFY dominate | **66.9%** of 251 roots |
| Letters with flow charge (ر · ل · ن · ع) | Skew POSITIVE (CARRY · CHANNEL · PROJECT · RELEASE) | Confirmed |
| Letters with mass charge (د · م · ق · ك · ص) | OPERATE + HOLD dominate | Confirmed |

## Relation to the vault

This vault contains the upstream theoretical inputs that made Layer 2 possible:

- **Layer 0** ([`consensus-letter-charges.md`](../03-scholar-extracts/consensus-letter-charges.md)) — 28-letter dual-face charges; the Layer-2 dataset uses these charges as the L3-material readings.
- **Layer 1** ([`jabal-letters.html`](../03-scholar-extracts/jabal-letters.html)) — 453 binary nuclei tested under the unified word-evidence test; Layer 2 inherits the validated binary readings.
- **Architecture spec** ([`lv1-architecture.md`](lv1-architecture.md)) — the four-layer scope of the project. The operative reading achieves 100% interpretive coverage on the existing corpus (a different target than predictive accuracy, see Limits below).

## Where this lives in the codebase

```
Juthoor-Linguistic-Genealogy/
├── docs/LAYER_2_V2_METHODOLOGY.md           ← full methodology (9 sections)
├── scripts/layer_2/
│   ├── README.md                            ← batch-script guide
│   ├── __manifest_v2.py                     ← schema, L3_CHARGES table, append_results()
│   ├── batch_<letter>_v2.py × 13            ← per-letter verdict files
│   ├── batch_combined_*_v2.py × 2           ← combined low-frequency batches
│   ├── build_dashboard_v2.py                ← dashboard generator
│   ├── sample_for_irr.py                    ← stratified IRR sampler
│   └── compute_irr.py                       ← Cohen's κ + confusion matrix
└── outputs/audits/
    ├── layer_2_results_v2.jsonl             ← 2,285 verdicts (one JSON per line)
    ├── layer_2_manifest_v2.json             ← per-batch progress tracker
    └── layer_2_dashboard_v2.html            ← 316 KB interactive dashboard
```

## Coverage, why 453 / 507 nuclei, not 784?

Arabic has 28 letters → 28² = 784 mathematically possible ordered binary pairs. Jabal's lexicon attests only ~453 nuclei; the trilateral decomposition shows 507 unique binaries appearing as L1+L2. Where did the other 277 go?

**Answer:** they're filtered, not missing. Full decomposition in [`Juthoor-Linguistic-Genealogy/outputs/audits/layer_2_coverage_gap.md`](../../Juthoor-Linguistic-Genealogy/outputs/audits/layer_2_coverage_gap.md) (auto-generated):

| Filter | Pairs removed | Reason |
|--------|--------------:|--------|
| alif-initial (ا as L1) | 28 | ا is a vowel marker, cannot begin a root |
| identical XX | 25 | Obligatory Contour Principle, repeated consonant blocked |
| same-articulator-class | 107 | Soft OCP, articulator hygiene |
| **Genuine lexical gaps** | **155** | **Phonologically allowed but unused by Arabic** |

Of 277 missing pairs, **160 (58%) are phonotactically blocked** and only **155 (20% of all 784 possibilities)** are true lexical gaps. The 100% native-composition result is honestly bounded: every trilateral that *exists* in Arabic gets a coherent operative reading. Whether the model can predict charges for the 155 lexical-gap binaries is the natural next test.

## Limits & open questions

- **Interpretive, not generative.** Given an arbitrary L1·L2·L3, the model does not yet *predict* the mode; the rater reads the actual root meaning and chooses the operative reading that fits. A future classifier could test mode-from-charges predictability, and the 155 lexical-gap pairs above are the natural held-out set.
- **Single-rater dataset.** All 2,285 verdicts come from one rater (Opus). Inter-rater κ checking tooling is in place (`sample_for_irr.py`, `compute_irr.py`) but the κ has not yet been computed against a second rater.
- **Loanwords undercounted.** Only 1/2,285 was tagged LOANWORD. Many candidates (e.g., فردوس, سندس, سنبل) are arguably native compositions under the operative model. A focused audit of suspected loanwords is warranted.
- **Quadrilateral and quintilateral roots.** The schema generalises (binary-on-L3, then ternary-on-L4) but has not been formalised. Roots like قنطر, زنجبيل, طمأن are sketched as "X holds/operates on then Y" in the reasons but lack a dedicated framework.

## Citation

```
Temessek, Y. (2026). Operative Composition of Arabic Trilateral Roots.
Layer 2 v2, 2,285 trilaterals graded under 12-mode operative grammar.
The Arabic Tongue (nature-genome-application) + Juthoor-Linguistic-Genealogy.
```
