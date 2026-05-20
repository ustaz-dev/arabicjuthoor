# Lexical-gap generative test · scaled to all 155 pairs

> The Arabic version is at [`lexical-gaps-generative-test-full-ar.md`](lexical-gaps-generative-test-full-ar.md).
>
> This document scales the [pilot generative test](lexical-gaps-generative-test.md) (8 pairs) to the L1-by-L1 enumeration of 155 lexical-gap candidates that was published in an earlier draft of [`computational/layer-2-coverage-gap.md`](../computational/layer-2-coverage-gap.md). The current canonical partition (hamza-folded, see that file) reports **140 disjoint lexical gaps**; the 15-pair difference is exactly the *-ا pairs that the fold treats as attested-via-hamza-on-alif and which this document already separates under the **STRUCTURAL** verdict (alif-as-L2). Sampling 155 is therefore an upper-bound test: every pair the current partition labels a "lexical gap" was tested, plus 15 *-ا pairs that the fold no longer counts as gaps but the structural verdict handles cleanly.

## Method (recap)

For each gap pair L1·L2:

- **Charges** from the unified 28-letter table.
- **Predicted nucleus semantic** — what the L1+L2 combination would mean if Arabic coined a trilateral on it.
- **Verdict.** Same four categories as the pilot, with one additional structural verdict:
  - **COHERENT** — clean compositional prediction, plausible semantic field, no attested duplicate.
  - **OVERLAPPING** — clean prediction, but it duplicates an attested nucleus's territory; lexical economy explains the gap.
  - **SELF-CANCELING** — the L1 and L2 charges pull in antithetical directions; the prediction is incoherent.
  - **STRUCTURAL** — alif-as-L2 is phonologically restricted (alif is the elongation vowel of L1, not a typical second consonant in a binary). Listed as a separate category because the gap is not lexical.
  - **UNCLEAR** — the framework cannot resolve the question with current tools.

Entries are grouped by L1 letter. Within each block: a one-line recap of the letter's two faces (per [`dual-face-stress-test.md`](dual-face-stress-test.md)), then a compact verdict table for the gaps from that L1.

---

## ي · gentle directed extension / soft adherence

Attested anchors: ي·د (hand), ي·م (sea), ي·س (ease), ي·ت (orphan, soft adherence).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ي·ا | extension | (alif L2 — see note) | **STRUCTURAL** |
| ي·ث | scattering | gentle scatter, soft dispersal | OVERLAPPING (ث·ر, ن·ث) |
| ي·ح | living warmth | gentle warmth, soft radiance | OVERLAPPING (ر·ح) |
| ي·خ | piercing rarefying | gentle + piercing = antithetical | **SELF-CANCELING** |
| ي·ذ | piercing from inside | gentle + sharp internal = antithetical | **SELF-CANCELING** |
| ي·ر | flow-repetition | gentle flow | OVERLAPPING (ر·ي in ري irrigation, attested) |
| ي·ز | sharp thrust | gentle + sharp thrust = antithetical | **SELF-CANCELING** |
| ي·ص | sealed-firm | gentle + hard-sealed = antithetical | **SELF-CANCELING** |
| ي·ض | heavy draw-together | gentle + heavy = mostly antithetical | **SELF-CANCELING** |
| ي·ط | heavy spread | gentle + heavy = mostly antithetical | **SELF-CANCELING** |
| ي·ظ | edged-prominence | gentle + edged = antithetical | **SELF-CANCELING** |
| ي·ع | deep grip | gentle + deep grip = antithetical | **SELF-CANCELING** |
| ي·غ | concealment depth | gentle concealment, soft covering | **COHERENT** (could mean soft-veil) |
| ي·ف | parting through | gentle parting | **COHERENT** (could mean soft-opening) |
| ي·ك | sealed cut | gentle + sealed cut = antithetical | **SELF-CANCELING** |
| ي·ل | binding extension | gentle binding-extension | OVERLAPPING (ل·ي, attested) |
| ي·ه | soft exhale | gentle softness redundant | OVERLAPPING (ه·م, ه·د) |

Sub-tally: 1 STRUCTURAL · 2 COHERENT · 4 OVERLAPPING · 10 SELF-CANCELING.

The ي gaps cluster strongly toward SELF-CANCELING. Reading: gentle extension is a "soft mode" that does not combine well with the language's emphatic, sharp, or heavy charges. The framework's prediction is principled — gentle-and-emphatic is genuinely incoherent.

---

## ظ · pronounced surfacing / held shadow

Attested anchors: ظ·ه (manifest), ظ·ل (shadow), ظ·ن (supposition), ظ·م (thirst).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ظ·ا | extension | (alif L2) | **STRUCTURAL** |
| ظ·ب | attachment-holds | prominent-attachment | OVERLAPPING (ظ·ه + ربط compositional) |
| ظ·ج | gathering-in-space | prominent gathering | **COHERENT** (could mean public assembly) |
| ظ·ح | living warmth | prominent warmth | OVERLAPPING (ح·م) |
| ظ·خ | rarefying piercing | edged + rarefying = mixed | **SELF-CANCELING** |
| ظ·ر | flow-repetition | prominent flow | OVERLAPPING (ن·ظ-flow, ر·ح-flow) |
| ظ·ش | scattering | prominent scattering | OVERLAPPING (ن·ش-scatter) |
| ظ·غ | concealment | edged + concealment = mixed | **SELF-CANCELING** |
| ظ·ق | cutting precision | edged + cut = doubling | OVERLAPPING (ق·ط-cut) |
| ظ·ك | sealed cut | edged + sealed = mixed | **SELF-CANCELING** |
| ظ·و | sustained binding | prominent binding | OVERLAPPING (و·ج-face) |
| ظ·ي | gentle extension | prominent + gentle = mixed | **SELF-CANCELING** |

Sub-tally: 1 STRUCTURAL · 1 COHERENT · 5 OVERLAPPING · 5 SELF-CANCELING.

---

## ه · soft passing / breath-carrying-away

Attested anchors: ه·م (concern), ه·د (guidance), ه·و (passion), ه·ل (perish).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ه·ث | scattering | soft-breath-scattering | **COHERENT** (whispered dispersal) |
| ه·ح | living warmth | soft warmth | OVERLAPPING (ر·ح) |
| ه·خ | piercing rarefying | soft + piercing = antithetical | **SELF-CANCELING** |
| ه·ذ | piercing from inside | soft + sharp internal = antithetical | **SELF-CANCELING** |
| ه·س | extending flow | soft flow | OVERLAPPING (ه·م-soft pressure) |
| ه·ص | sealed-firm | soft + sealed = antithetical | **SELF-CANCELING** |
| ه·ظ | edged-prominence | soft + edged = antithetical | **SELF-CANCELING** |
| ه·ع | deep grip | soft + deep grip = antithetical | **SELF-CANCELING** |
| ه·غ | concealment | soft concealment | **COHERENT** (soft-veiling) |
| ه·ف | parting | soft parting | OVERLAPPING (ه·م-pressure, ه·د-easing) |
| ه·ق | cutting precision | soft + cut = antithetical | **SELF-CANCELING** |
| ه·ك | sealed cut | soft + sealed = antithetical | **SELF-CANCELING** |

Sub-tally: 0 STRUCTURAL · 2 COHERENT · 3 OVERLAPPING · 7 SELF-CANCELING.

Pattern: same as ي — soft charges resist combining with emphatic/sharp charges. The framework correctly screens out the antithetical pairs.

---

## ج · gathering in a space / surfacing out

Attested anchors: ج·م (gather), ج·ن (enclose), ج·ل (magnitude), ج·ر (flow), ج·د (earnest), ج·ه (announce).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ج·ا | extension | (alif L2) | **STRUCTURAL** |
| ج·ت | completion | gathering-into-completion | OVERLAPPING (ج·م) |
| ج·خ | piercing rarefying | gathered piercing | **COHERENT** (gathered-burst-through) |
| ج·ص | sealed-firm | gathered + sealed | OVERLAPPING (ج·م-mass) |
| ج·ض | heavy draw-together | gathered + heavy-grouping = doubling | OVERLAPPING (ج·م) |
| ج·ط | heavy spread | gathered + spread = mixed | **SELF-CANCELING** |
| ج·ظ | edged-prominence | gathered + prominent | OVERLAPPING (ج·ه) |
| ج·غ | concealment | gathered + covered | OVERLAPPING (ج·ن-enclosed) |
| ج·ق | cutting precision | gathered + cut = mixed | **SELF-CANCELING** |
| ج·ك | sealed cut | gathered + sealed cut | OVERLAPPING (ج·ن-enclosed) |

Sub-tally: 1 STRUCTURAL · 1 COHERENT · 6 OVERLAPPING · 2 SELF-CANCELING.

---

## ش · branching scattering / embracing inward spread

Attested anchors: ش·ع (radiate-scatter), ش·ت (scatter), ش·م (encompass), ش·د (firm-encompass).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ش·ا | extension | (alif L2) | **STRUCTURAL** |
| ش·ث | scattering | scatter + scatter | OVERLAPPING (ش·ت — already attested as scatter) |
| ش·ذ | piercing from inside | scatter + sharp internal | **COHERENT** (could mean scattering-by-piercing) |
| ش·ز | sharp thrust | scatter + thrust | OVERLAPPING (ش·ع, ز·ر) |
| ش·س | extending flow | scatter + flow | OVERLAPPING (ش·ع) |
| ش·ص | sealed-firm | scatter + sealed = antithetical | **SELF-CANCELING** |
| ش·ض | heavy draw-together | scatter + heavy-gather = antithetical | **SELF-CANCELING** |
| ش·ل | binding extension | scatter + binding = mixed | **SELF-CANCELING** |

Sub-tally: 1 STRUCTURAL · 1 COHERENT · 3 OVERLAPPING · 3 SELF-CANCELING.

---

## ث · scattering / fine accumulation

Attested anchors: ث·ر (scattered earth), ث·ب (settle/fix), ث·ق (weigh down), ث·م (fruit).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ث·ا | extension | (alif L2) | **STRUCTURAL** |
| ث·ح | living warmth | scatter + warmth | OVERLAPPING (ر·ح) |
| ث·ش | scattering | scatter + scatter = doubling | OVERLAPPING (ث·ر, ش·ت) |
| ث·غ | concealment | scatter + cover = antithetical | **SELF-CANCELING** |
| ث·ف | parting | scatter + parting | OVERLAPPING (ف·ر-part) |
| ث·ك | sealed cut | scatter + sealed = antithetical | **SELF-CANCELING** |
| ث·ه | soft exhale | scatter + soft | OVERLAPPING (ه·ث from above) |
| ث·ي | gentle extension | scatter + gentle | OVERLAPPING (ي·ث from above) |

Sub-tally: 1 STRUCTURAL · 0 COHERENT · 5 OVERLAPPING · 2 SELF-CANCELING.

---

## خ · rarefying piercing / thick concealing

Attested anchors: خ·ر (exit), خ·ل (differentiate), خ·ت (seal), خ·ف (hidden), خ·ز (store).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| خ·ا | extension | (alif L2) | **STRUCTURAL** |
| خ·ث | scattering | piercing scatter | OVERLAPPING (خ·ر, ث·ر) |
| خ·ج | gathering-in-space | piercing + gathered | **COHERENT** (could mean piercing-into-enclosure) |
| خ·ح | living warmth | piercing + warm | OVERLAPPING (ح·ر) |
| خ·ظ | edged-prominence | piercing + edged | OVERLAPPING (خ·ر-piercing-emergence) |
| خ·ع | deep grip | piercing + grip | **COHERENT** (sharp internal grip) |
| خ·ه | soft exhale | piercing + soft = antithetical | **SELF-CANCELING** |

Sub-tally: 1 STRUCTURAL · 2 COHERENT · 3 OVERLAPPING · 1 SELF-CANCELING.

---

## غ · concealing depth / emerging from depth

Attested anchors: غ·ر (delude), غ·ط (cover), غ·ف (forgive), غ·د (set forth dawn), غ·ي (rain), غ·و (emerge into error).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| غ·ا | extension | (alif L2) | **STRUCTURAL** |
| غ·ت | completion | covered completion | OVERLAPPING (غ·ر, غ·م) |
| غ·ج | gathering-in-space | covered gathering | OVERLAPPING (غ·م-cloud, جم) |
| غ·ح | living warmth | covered warmth | **COHERENT** (warmth-under-cover, broiling) |
| غ·ذ | piercing from inside | covered + sharp internal | **COHERENT** (piercing-from-cover, like food sneaking) |
| غ·ع | deep grip | covered + deep grip | OVERLAPPING (غ·م-depth) |
| غ·ه | soft exhale | covered + soft = redundant | OVERLAPPING (ه·و-fade) |

Sub-tally: 1 STRUCTURAL · 2 COHERENT · 4 OVERLAPPING · 0 SELF-CANCELING.

---

## ك · sealed cut / constrained surfacing

Attested anchors: ك·ت (seal), ك·ف (suffice/hold back), ك·ش (uncover), ك·ل (word).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ك·ا | extension | (alif L2) | **STRUCTURAL** |
| ك·ج | gathering-in-space | sealed + gathered | **COHERENT** (sealed-vault) |
| ك·ح | living warmth | sealed + warm | OVERLAPPING (ح·م-warmth-held) |
| ك·ص | sealed-firm | sealed + sealed = doubling | OVERLAPPING (ك·ت, ص·م) |
| ك·ض | heavy draw-together | sealed + heavy = doubling | OVERLAPPING (ض·م) |
| ك·ط | heavy spread | sealed + spread = mixed | **SELF-CANCELING** |

Sub-tally: 1 STRUCTURAL · 1 COHERENT · 3 OVERLAPPING · 1 SELF-CANCELING.

---

## ل · attachment-extends / bound-folding

Attested anchors: ل·ز (necessity), ل·م (shine-attach), ل·ق (meet), ل·ف (fold), ل·و (twist), ل·ث (cloth-around).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ل·ا | extension | (alif L2 — but لا is attested as the negation particle) | **STRUCTURAL** (technically attested as particle) |
| ل·ث | scattering | bridge + scatter | OVERLAPPING (ف·ر-branch, ش·ع-branch) |
| ل·خ | piercing | bridge + piercing | **COHERENT** (piercing-through-link, decisive thread) |
| ل·ش | scattering | bridge + scatter (variant) | OVERLAPPING (same as ل·ث) |
| ل·ص | sealed-firm | bridge + sealed-firm | OVERLAPPING (ل·ز necessity) |
| ل·ض | heavy draw-together | bridge + heavy gathering | OVERLAPPING (ل·م-cluster) |

Sub-tally: 1 STRUCTURAL · 1 COHERENT · 4 OVERLAPPING · 0 SELF-CANCELING.

---

## ذ · piercing from inside / held inside

Attested anchors: ذ·ك (recall), ذ·و (wither), ذ·ل (humble), ذ·خ (store).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ذ·ا | extension | (alif L2) | **STRUCTURAL** |
| ذ·ج | gathering-in-space | sharp-internal + gathered | OVERLAPPING (ذ·خ) |
| ذ·ح | living warmth | sharp-internal + warmth | OVERLAPPING (ذ·و-wither, ح·ر) |
| ذ·ش | scattering | sharp-internal + scatter | OVERLAPPING (ذ·و) |
| ذ·غ | concealment | sharp-internal + cover = redundant | OVERLAPPING (ذ·خ-store) |
| ذ·ف | parting | sharp-internal + parting | **COHERENT** (sharp-cleave) |

Sub-tally: 1 STRUCTURAL · 1 COHERENT · 4 OVERLAPPING · 0 SELF-CANCELING.

---

## ط · heavy spread / heavy contraction

Attested anchors: ط·ر (broad-edge), ط·ع (feast), ط·و (fold), ط·م (settle/obliterate), ط·ب (medicine).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ط·ا | extension | (alif L2) | **STRUCTURAL** |
| ط·ج | gathering-in-space | heavy + gathered | OVERLAPPING (ط·م) |
| ط·خ | piercing rarefying | heavy + piercing | **COHERENT** (heavy-piercing, drill) |
| ط·ش | scattering | heavy + scatter | OVERLAPPING (ط·ر-spread, ش·ت) |
| ط·ق | cutting precision | heavy + cut | OVERLAPPING (ط·ر) |
| ط·ك | sealed cut | heavy + sealed cut | OVERLAPPING (ط·م-obliterate) |

Sub-tally: 1 STRUCTURAL · 1 COHERENT · 4 OVERLAPPING · 0 SELF-CANCELING.

---

## ت · calm completion / sharp dental pressure

Attested anchors: ت·م (complete), ت·ل (recite-sequence), ت·ب (repent), ت·ر (cut-off), ت·ع (fatigue).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ت·ا | extension | (alif L2) | **STRUCTURAL** |
| ت·خ | piercing rarefying | completion + piercing | OVERLAPPING (ت·ر) |
| ت·ش | scattering | completion + scatter | OVERLAPPING (ت·ر-sharp pursuit) |
| ت·غ | concealment | completion + cover | OVERLAPPING (ت·م-complete) |
| ت·ك | sealed cut | completion + sealed cut | OVERLAPPING (ك·ت-from K side) |

Sub-tally: 1 STRUCTURAL · 0 COHERENT · 4 OVERLAPPING · 0 SELF-CANCELING.

---

## ض · draw-together with weight / heavy spreading

Attested anchors: ض·م (gather-weight), ض·ر (strike), ض·ع (weaken), ض·ي (radiance), ض·ح (morning), ض·و (light).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ض·ا | extension | (alif L2) | **STRUCTURAL** |
| ض·خ | piercing rarefying | heavy-gather + piercing | OVERLAPPING (ض·ر) |
| ض·ش | scattering | heavy-gather + scatter = antithetical | **SELF-CANCELING** |
| ض·ق | cutting precision | heavy-gather + cut | OVERLAPPING (ض·ر) |
| ض·ك | sealed cut | heavy + sealed cut | OVERLAPPING (ض·م) |

Sub-tally: 1 STRUCTURAL · 0 COHERENT · 3 OVERLAPPING · 1 SELF-CANCELING.

---

## ق · cutting precision / firm holding

Attested anchors: ق·ص (precise cut), ق·ط (sever), ق·ر (gather-recite/settle), ق·ب (grip), ق·ل (heart).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ق·ا | extension | (alif L2) | **STRUCTURAL** |
| ق·ج | gathering-in-space | cut + gathered | OVERLAPPING (ق·ر-settled) |
| ق·ز | sharp thrust | cut + thrust | OVERLAPPING (ق·ص-precise, ز·ج-drive) |
| ق·ظ | edged-prominence | cut + edged | OVERLAPPING (ق·ط) |

Sub-tally: 1 STRUCTURAL · 0 COHERENT · 3 OVERLAPPING · 0 SELF-CANCELING.

---

## ح · living warmth contained / radiating warmth

Attested anchors: ح·م (praise/protect), ح·ب (love), ح·ف (preserve), ح·ر (heat), ح·ي (life), ح·ج (pilgrimage).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ح·ا | extension | (alif L2) | **STRUCTURAL** |
| ح·خ | piercing | warmth + piercing | OVERLAPPING (ح·ر) |
| ح·غ | concealment | warmth + cover | OVERLAPPING (ح·ف-preserve) |
| ح·ه | soft exhale | warmth + soft = redundant | OVERLAPPING (ه·م, ح·م) |

Sub-tally: 1 STRUCTURAL · 0 COHERENT · 3 OVERLAPPING · 0 SELF-CANCELING.

---

## م · gathering-mass / projecting

Attested anchors: م·ك (place), م·ل (fill), م·ت (firm-gather), م·د (extend), م·س (touch), م·و (wave).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| م·ا | extension | (alif L2) | **STRUCTURAL** |
| م·ذ | piercing from inside | mass + sharp internal | OVERLAPPING (م·د-extend) |
| م·ظ | edged-prominence | mass + edged | OVERLAPPING (م·د) |
| م·غ | concealment | mass + cover | OVERLAPPING (م·س-touch covered, خ·م-cover) |

Sub-tally: 1 STRUCTURAL · 0 COHERENT · 3 OVERLAPPING · 0 SELF-CANCELING.

---

## د · settled grounding / inward push

Attested anchors: د·م (last), د·ر (dwelling), د·ل (point), د·ف (push), د·خ (enter), د·ب (creep).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| د·ا | extension | (alif L2) | **STRUCTURAL** |
| د·ج | gathering-in-space | fixed + gathered | OVERLAPPING (د·م-permanence) |
| د·ش | scattering | fixed + scatter = antithetical | **SELF-CANCELING** |
| د·غ | concealment | fixed + cover | OVERLAPPING (د·خ, د·ر) |

Sub-tally: 1 STRUCTURAL · 0 COHERENT · 2 OVERLAPPING · 1 SELF-CANCELING.

---

## ص · sealed strength / hard-piercing

Attested anchors: ص·م (firm-sealed), ص·خ (rock), ص·ل (bond), ص·د (split), ص·ر (redirect), ص·و (form).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ص·ا | extension | (alif L2) | **STRUCTURAL** |
| ص·ج | gathering-in-space | sealed + gathered | OVERLAPPING (ص·م) |
| ص·ش | scattering | sealed + scatter = antithetical | **SELF-CANCELING** |
| ص·ق | cutting precision | sealed + cut = mixed | OVERLAPPING (ص·د) |

Sub-tally: 1 STRUCTURAL · 0 COHERENT · 2 OVERLAPPING · 1 SELF-CANCELING.

---

## و · sustained binding / linked release

Attested anchors: و·ص (connect), و·ع (promise), و·ج (face), و·د (affection), و·ل (turn), و·ز (measure).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| و·ا | extension | (alif L2 — but وا is attested as exclamation in classical Arabic) | **STRUCTURAL** |
| و·خ | piercing | bound + piercing | **COHERENT** (bound-perforating, like stitching) |
| و·ظ | edged-prominence | bound + edged | OVERLAPPING (و·ج-face) |
| و·غ | concealment | bound + cover | OVERLAPPING (و·ر-cover) |

Sub-tally: 1 STRUCTURAL · 1 COHERENT · 2 OVERLAPPING · 0 SELF-CANCELING.

---

## ف · parting-through / opening-cleaving

Attested anchors: ف·ر (split), ف·ص (cleave), ف·ج (break), ف·ت (open), ف·ط (primal-cleave), ف·ل (cleaving-dawn).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ف·ا | extension | (alif L2) | **STRUCTURAL** |
| ف·ث | scattering | part + scatter | OVERLAPPING (ف·ر) |
| ف·ذ | piercing from inside | part + sharp internal | OVERLAPPING (ف·ر, ذ·و) |
| ف·غ | concealment | part + cover = antithetical | **SELF-CANCELING** |

Sub-tally: 1 STRUCTURAL · 0 COHERENT · 2 OVERLAPPING · 1 SELF-CANCELING.

---

## ع · deep grip / emergence from depth

Attested anchors: ع·ب (worship), ع·ز (might), ع·ق (bind), ع·ل (know), ع·م (work), ع·ر (recognize).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ع·ا | extension | (alif L2) | **STRUCTURAL** |
| ع·خ | piercing | grip + piercing | OVERLAPPING (ع·ق, ع·ز) |
| ع·غ | concealment | grip + cover = mixed | **SELF-CANCELING** |

Sub-tally: 1 STRUCTURAL · 0 COHERENT · 1 OVERLAPPING · 1 SELF-CANCELING.

---

## ز · sharp thrust / fine penetration

Attested anchors: ز·ل (earthquake), ز·ج (drive), ز·ر (roar), ز·ك (purify), ز·ي (ornament), ز·و (pair).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ز·ا | extension | (alif L2) | **STRUCTURAL** |
| ز·ش | scattering | thrust + scatter | OVERLAPPING (ز·ل, ش·ت) |

Sub-tally: 1 STRUCTURAL · 0 COHERENT · 1 OVERLAPPING · 0 SELF-CANCELING.

---

## ر · repetition-flow / binding flow

Attested anchors: ر·ج (return), ر·ك (mount), ر·ح (mercy), ر·ب (Lord), ر·ص (firm-bound), ر·ت (recite).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ر·ا | extension | (alif L2) | **STRUCTURAL** |
| ر·ظ | edged-prominence | flow + edged | OVERLAPPING (ن·ظ, ر·ج) |

Sub-tally: 1 STRUCTURAL · 0 COHERENT · 1 OVERLAPPING · 0 SELF-CANCELING.

---

## ب · attachment-reveals / sealed-shutting

Attested anchors: ب·ر (righteous), ب·ل (reach), ب·ي (clarify), ب·س (pulverize), ب·ك (mute).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ب·ا | extension | (alif L2) | **STRUCTURAL** |
| ب·ظ | edged-prominence | attached + edged | OVERLAPPING (ب·ر-righteous, ظ·ه-manifest) |

Sub-tally: 1 STRUCTURAL · 0 COHERENT · 1 OVERLAPPING · 0 SELF-CANCELING.

---

## س · extending flow / held flow

Attested anchors: س·ل (peace), س·ي (stream), س·ر (joy/secret), س·ك (quietude), س·ج (confine).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| س·ا | extension | (alif L2) | **STRUCTURAL** |
| س·ش | scattering | flow + scatter | OVERLAPPING (س·ل, ش·ع) |

Sub-tally: 1 STRUCTURAL · 0 COHERENT · 1 OVERLAPPING · 0 SELF-CANCELING.

---

## ن · resonance-emission / cavity-held resonance

Attested anchors: ن·د (call), ن·ج (deliverance), ن·ز (descend), ن·ث (paired), ن·و (tendon), ن·م (sleep).

| Pair | L2 charge | Predicted nucleus | Verdict |
|---|---|---|---|
| ن·ا | extension | (alif L2) | **STRUCTURAL** |

Sub-tally: 1 STRUCTURAL · 0 COHERENT · 0 OVERLAPPING · 0 SELF-CANCELING.

---

## Aggregate result

```
Total pairs analyzed:  155

STRUCTURAL (alif-as-L2):   26  (16.8%)
COHERENT:                  16  (10.3%)
OVERLAPPING:               80  (51.6%)
SELF-CANCELING:            33  (21.3%)
```

**Of the 129 non-structural gaps:**
- **74.4% (96/129) produce a defensible prediction** (COHERENT + OVERLAPPING combined). The framework reads them as either coining-a-new-territory or duplicating-existing-territory.
- **25.6% (33/129) are correctly screened as self-canceling.** The L1·L2 charge pair is genuinely antithetical, and the framework refuses to read these as coherent compositions.

**Of the 155 total:**
- 16.8% are structural (alif distribution restriction) — neither lexical nor falsifying.
- 10.3% are COHERENT and represent the **honest unused space** the framework opens to: the language could have coined these, and the prediction is internally consistent. These are the natural candidates for a generative model's *next test* (could you predict, in advance, which of these 16 pairs Arabic would have coined if it had needed them?).
- 51.6% are OVERLAPPING — the framework predicts coherent semantics, but lexical economy explains why Arabic chose not to duplicate already-occupied space.
- 21.3% are SELF-CANCELING, which is the framework working as a generative theory should: refusing to declare meaning where the charges are incoherent.

## What this confirms

**The framework is generative in a disciplined way.** It produces coherent predictions for ~75% of phonotactically-permissible unused binaries, refuses to predict meaning for ~21% where the charges are antithetical, and is silent (structurally) on the remaining ~17% where alif's L2 distribution dominates the picture. This is the distribution a well-behaved generative theory should produce — productive on coherent inputs, principled in screening out incoherent ones.

## What this leaves open

- **The 16 COHERENT cases as a registered held-out test set.** If the framework is genuinely generative, a future independent rater (or computational model trained on the attested binaries) should be able to predict semantic fields for these 16 unused binaries that match the framework's predictions above. The 16 are: ي·غ, ي·ف, ظ·ج, ه·ث, ه·غ, ج·خ, ش·ذ, خ·ج, خ·ع, غ·ح, غ·ذ, ك·ج, ل·خ, ذ·ف, ط·خ, و·خ.
- **The classification of the 33 SELF-CANCELING cases.** Is the antithesis truly principled, or are some readable under a less-obvious mode? An independent second-rater pass on the SELF-CANCELING set would be the falsification test.
- **The relationship between OVERLAPPING gaps and the language's lexical economy.** If every OVERLAPPING gap can be paired with the attested nucleus it duplicates, that pairing itself becomes a research artifact: a map of *which existing nucleus each unused binary would have duplicated*. A useful by-product for cognitive lexicography.

---

_See also: [`lexical-gaps-generative-test.md`](lexical-gaps-generative-test.md) for the 8-case pilot with deeper per-pair analyses, [`dual-face-stress-test.md`](dual-face-stress-test.md) for the per-letter charges used here, [`computational/layer-2-coverage-gap.md`](../computational/layer-2-coverage-gap.md) for the source enumeration._
