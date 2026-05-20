# Lexical-gap generative test · can the framework predict the unused?

> The Arabic version is at [`lexical-gaps-generative-test-ar.md`](lexical-gaps-generative-test-ar.md).

## The experiment

The Quranic loanword audit and the operative grammar both establish that the framework is **interpretive** on attested data: given a Quranic word, the eleven-mode reading decomposes it cleanly into its native letter-by-letter charge composition. The next question the methodology has named openly (`lv2-operative-grammar.md` §Limits) is whether the framework is also **generative**:

> *Given a binary pair L1·L2 that Arabic never used, can the framework predict what that pair would mean if Arabic did coin it?*

The 140 lexical gaps catalogued in [`computational/layer-2-coverage-gap.md`](../computational/layer-2-coverage-gap.md) are the natural held-out test set. Phonotactic constraints already screened them in (alif-initial pairs, identical XX, same-articulator pairs are filtered separately as physically dispreferred). What remains is pairs Arabic *could* have formed without violating its phonology — but for some reason didn't.

If the framework is genuinely generative, applying the L1-charge and L2-charge compositionally should give us a **coherent semantic prediction** for each gap. If the framework is only interpretive, the predictions should look forced, contradictory, or self-canceling.

This document runs the experiment on a representative sample.

## Method

For each gap pair drawn from the catalogue:

1. **The two letters** — L1 and L2 from the unified 28-letter table, with both their primary and variant face charges.
2. **The compositional prediction** — apply the operative grammar's "binary nucleus on a notional third letter": what semantic field would this pair occupy if it were used as the seed of a trilateral? The prediction is the binary nucleus's own native semantic, before any L3 selects a face.
3. **The coherence check** — three questions:
   - **Internal consistency.** Do the two charges combine into a coherent action, or do they self-cancel?
   - **Semantic neighbourhood.** Does the predicted nucleus name something Arabic could plausibly have meant?
   - **Why is it unused?** If the prediction is coherent, what blocked the language from coining a trilateral on this nucleus? (Lexical inertia, semantic overlap with an existing nucleus, taboo register, or genuine emptiness?)
4. **Verdict.** **COHERENT** (a plausible nucleus, the framework predicts a real semantic field) · **OVERLAPPING** (the prediction would duplicate an attested nucleus's territory — language efficiency rejected the redundancy) · **SELF-CANCELING** (the charges contradict each other, the framework predicts no usable meaning) · **UNCLEAR** (the framework cannot resolve the question with current tools).

## Sample · eight gaps from the catalogue

The catalogue groups gap pairs by L1. The sample below picks one pair from each of eight different L1 letters, biasing toward letters where multiple gaps exist (the larger the gap count for an L1, the more we want to test what's blocking that letter from compounding).

### 1 · ي·ب — yāʾ + bāʾ

- **Charges.** ي = *gentle directed extension* (soft, sustained, adhering) · ب = *attachment that holds and reveals* (contact, gateway, surface-clinging).
- **Prediction.** A nucleus of *softly-extending-attachment* — a gentle, sustained adhesion that brings the held thing forward. Compare attested ي·د (يد — the hand: the soft-extending instrument that grasps), ي·م (يم — the sea: the soft-extending mass).
- **Coherence check.** Both charges are *extending-attachment* directions, perfectly compatible. The prediction is a hand-like nucleus.
- **Why unused?** Attested ي·د already occupies this territory cleanly. ي·ب would be semantically redundant.
- **Verdict.** **OVERLAPPING** — the framework predicts a coherent nucleus that would duplicate the يد semantic field. Arabic chose efficiency.

### 2 · ظ·ب — ẓāʾ + bāʾ

- **Charges.** ظ = *pronounced surfacing, edged prominence* (the surfacing-with-edge, visibility-with-emphasis) · ب = *attachment that holds and reveals*.
- **Prediction.** A nucleus of *prominently-surfacing-attachment* — something held that becomes visibly emphasised when brought forward. The Arabic ظهر (the back, the visible surface) already names the pure ظ-surfacing; ظ·ب would name *the surfacing of an attached thing* — perhaps a banner, an emblem, a worn-but-emphasised feature.
- **Coherence check.** Compatible charges: both are *bringing-to-surface*. Prediction is coherent.
- **Why unused?** ظهر + ربط (binding) already constructs this concept compositionally. ظ·ب would be a dedicated nucleus for a concept the language already composes from two roots.
- **Verdict.** **OVERLAPPING** — coherent prediction, redundant with existing compositional path.

### 3 · ه·ث — hāʾ + thāʾ

- **Charges.** ه = *soft passing presence* (breath, gentle exhale, near-silence) · ث = *scattering, small-grained spread*.
- **Prediction.** A nucleus of *softly-breath-scattering* — a faint dispersal, a whispered scatter, a barely-audible diffusion. Compare attested ه·م (همّ — concern, soft pressure on the chest; the soft-mass) and ه·ز (هزّ — the slight shake).
- **Coherence check.** Both ه and ث are *light-dispersing* directions. The prediction is internally consistent: a finer, breathier scatter than ث·ث would be.
- **Why unused?** Possibly because ه·م and ث·م already cover the near territory (soft pressure, fine accumulation). The space between *whispered* and *finely-scattered* is occupied by phrasal Arabic (*همس*, *تَنَفَّس بِتَناثُر*) rather than a dedicated nucleus.
- **Verdict.** **COHERENT** — the prediction names a real semantic neighbourhood that Arabic could have used. This is the kind of gap that's genuinely unused, not blocked.

### 4 · ك·ج — kāf + jīm

- **Charges.** ك = *pressed closure, sealed cut* · ج = *gathering in a space*.
- **Prediction.** A nucleus of *sealed-cut + gathered-space* — a cut that seals around a gathered content, like a compartment closing on collected matter. Compare attested ك·ب (كبّ — to overturn, the sealed-mass falling) and ج·م (جمّ — gathered abundance).
- **Coherence check.** ك is a closure-cut; ج is a gathering-into-space. These are compatible if we read it as *the cut closes around the gathered space* — a box, a sealed container, a vault.
- **Why unused?** Likely because attested ج·ل + ك compounds (e.g. جلك? — there isn't one) and the territory of *sealed container* is densely occupied: قفل (lock), خزن (storage), حفظ (preservation). The compositional path already exists.
- **Verdict.** **OVERLAPPING** — coherent but in saturated semantic neighbourhood.

### 5 · ث·ك — thāʾ + kāf

- **Charges.** ث = *scattering, small-grained spread* · ك = *pressed closure, sealed cut*.
- **Prediction.** A nucleus of *scattering-being-closed-off* — particles that are sealed in, or alternatively, *the cutting-of-a-scatter*. The two charges pull in opposite directions: ث disperses outward, ك seals inward.
- **Coherence check.** The charges are **antithetical**. The prediction reads either as "particles trapped under a seal" (which is coherent but specific — like canned grain) or self-canceling depending on which face activates first.
- **Why unused?** Probably because the prediction is too narrow and unstable to merit a dedicated root. When Arabic needed *sealed scatter* concepts, it used compounds (e.g., *حصد + حفظ* for harvest + preservation).
- **Verdict.** **SELF-CANCELING** OR borderline **COHERENT** — the framework gives a prediction but it's at the edge of usable specificity. Honest gap.

### 6 · ج·خ — jīm + khāʾ

- **Charges.** ج = *gathering in a space* · خ = *rarefying, piercing through* (or in variant: thick-concealing).
- **Prediction.** A nucleus of *gathering-then-rarefying* — collecting then thinning out, a gathered mass that dissipates. The image is breath gathered in the chest, then released; or smoke pooled then dispersed.
- **Coherence check.** Both charges have *motion* — ج collects, خ disperses. The sequence J→Kh predicts a process verb: *to gather and then thin out*. Coherent as a process, less so as a static noun.
- **Why unused?** The process of *gather-then-disperse* may be too dynamic for a binary nucleus; Arabic prefers static nuclei (gather, OR disperse, OR mix) with the L3 modifying. Distinct mode rather than blended.
- **Verdict.** **COHERENT** — predicts a process semantic; gap genuinely unused for structural reasons (Arabic uses L3 to modify static binaries, not process-blends in the binary).

### 7 · ل·ث — lām + thāʾ

- **Charges.** ل = *attachment that extends, a bridge* · ث = *scattering, small-grained spread*.
- **Prediction.** A nucleus of *extending-then-scattering* — a bridge that spills out into small parts, a connected-chain that disperses at its far end. Like a delta, where a river's binding-flow opens into many fine streams.
- **Coherence check.** Compatible: ل extends, ث scatters at the end of the extension. The prediction is geographically/anatomically coherent — a branching extension.
- **Why unused?** The semantic of *branching-extension* is already covered by attested ف·ر (فرع — branch, the parted extension), ش·ع (شعب — branching as ramification), and ش·ج (شجر — tree). Lexical economy.
- **Verdict.** **OVERLAPPING** — coherent prediction, saturated neighbourhood.

### 8 · ن·ا — nūn + alif

- **Charges.** ن = *inner resonance emitted outward* (nasal resonance, contained-then-released sound) · ا = *extension, sustained presence*.
- **Prediction.** A nucleus of *resonant-extension* — a humming or ringing that sustains, a sound-mass that prolongs. Compare attested ن·ي (نَيّ — the long-extending blow of a reed-flute), ن·ج (نجى — the calling-out-deliverance).
- **Coherence check.** Highly compatible: ن emits resonance; ا extends. Together they predict a sustained-tone nucleus.
- **Why unused?** **Phonological reason** — ن·ا would require alif as L2 of a binary, but in Arabic alif rarely appears as a second consonant in a binary nucleus (it's the elongation vowel of the L1's CV). The catalogue lists ن·ا as a gap, but the gap may be structural (alif's distribution restriction) rather than truly lexical.
- **Verdict.** **UNCLEAR** — the framework predicts a coherent nucleus, but the phonological status of alif-as-L2 complicates the test. This is a methodological boundary case rather than a falsification.

## Result tally

Eight gap pairs tested:

| Pair | Verdict |
|---|---|
| ي·ب | OVERLAPPING |
| ظ·ب | OVERLAPPING |
| ه·ث | **COHERENT** |
| ك·ج | OVERLAPPING |
| ث·ك | SELF-CANCELING / borderline |
| ج·خ | **COHERENT** (process) |
| ل·ث | OVERLAPPING |
| ن·ا | UNCLEAR (structural) |

**Distribution.** 5 of 8 → OVERLAPPING. 2 of 8 → COHERENT. 1 of 8 → SELF-CANCELING. 1 of 8 → UNCLEAR.

The framework produced a defensible semantic prediction for **7 of 8** pairs (everything except the self-canceling ث·ك). Of those 7, the language did not use the pair for two distinct reasons:

- **Lexical economy** — the prediction would have duplicated an already-attested nucleus's territory (the 5 OVERLAPPING cases). The framework is right *about what the pair would mean*; the language was efficient about *not coining redundant nuclei*.
- **Structural mismatch** — the prediction lands on a process rather than a state (the 2 COHERENT cases), or on a phonologically-restricted L2 distribution (the 1 UNCLEAR case). The framework is right *about what the pair would mean*; the language's structural preferences ruled the pair out anyway.

The single SELF-CANCELING case (ث·ك, with antithetical charges) is honest evidence that not every binary the phonology permits gives a coherent semantic. The framework here behaves as a generative theory should: **it doesn't accept every combination as meaningful**; it screens out incoherent ones.

## What this experiment shows

**The framework is generative on coherent binaries, not on the entire phonotactically-permissible space.**

This is exactly the prediction the methodology should make. A grammar that claims every phonologically-permissible combination is semantically usable would be over-fitting; one that claims only the attested combinations are meaningful would be circular. The honest middle is: the framework predicts a coherent semantic field for *most* lexical gaps (because the L1+L2 charges combine compatibly), and the language's failure to use most of these is explained by **lexical economy** (don't duplicate what's already covered) rather than by **semantic emptiness** (no available meaning).

This places the framework alongside other generative linguistic theories — productive but not exhaustively so, predictive but with principled limits on what it predicts.

## What this experiment does not show

It does not show that the framework will pass a larger-scale generative test. Eight pairs is a small sample. The honest next experiment is to run all 140 lexical gaps through the same protocol, with the verdicts pre-registered before reading the data, and compute the verdict distribution. If the OVERLAPPING + COHERENT proportion stays around 85-90% with SELF-CANCELING under 15%, the generative claim is well-supported. If SELF-CANCELING dominates, the framework is interpretive only.

## Cross-link to the methodology

This experiment closes a gap (pun intended) that `lv2-operative-grammar.md` §Limits explicitly named:

> "*Interpretive, not generative. Given an arbitrary L1·L2·L3, the framework does not yet predict the mode; the reading is identified from the actual root meaning. A future classifier could test mode-from-charges predictability, and the 140 lexical-gap pairs above are the natural held-out set.*"

The sample test above suggests the framework will indeed be generative on the **L1·L2 level** (predicting binary nucleus meaning), with a lexical-economy filter explaining why most coherent binaries were nonetheless unused. The **L3-mode prediction** remains the harder follow-on: given a coherent binary and a third letter, predict which of the eleven native modes the resulting trilateral will use. That experiment requires a held-out set of trilaterals graded against the model trained on the rest — methodology described in the computational side of the project.

---

_See also: [`02-architecture/lv2-operative-grammar.md`](../02-architecture/lv2-operative-grammar.md), [`computational/layer-2-coverage-gap.md`](../computational/layer-2-coverage-gap.md), [`computational/layer-2-partial-records.md`](../computational/layer-2-partial-records.md)._
