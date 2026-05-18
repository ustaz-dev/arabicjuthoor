# Juthoor — Architecture, Vision & Methods
## المخطط المعماري لمشروع جُذور

**Author:** Yassine Temessek
**Conducted under:** Temessek for Research, Publishing & Training

---

## 1. Vision · الرؤية

Juthoor is a **computational engine for decoding the Arabic genome** — the pre-grammatical semantic layer where meaning is physically encoded in the mouth, throat, and breath.

Unlike a Saussurean model of arbitrary signs, the Arabic genome carries meaning at the sub-root level: individual letters have kinetic/physical semantic charges, pairs of letters (binary nuclei) form semantic fields, and trilateral roots compose these atoms into the words of the language. The system is testable and quantifiable.

The project formalizes, tests, and scores this system using:

- The **classical Arabic linguistic tradition** (al-Khalil ibn Ahmad in *Kitab al-Ayn*, 8th c.; Ibn Jinni's *إمساس الألفاظ أشباه المعاني* doctrine in *al-Khasais*, 11th c.) as the deeper anchor.
- The modern lexicographic foundation laid by **Dr. Muhammad Hassan Jabal** (*المعجم الاشتقاقي المُؤَصَّل*) — the primary empirical dataset.
- The parallel sensory-profile work of **Hassan Abbas** (*خصائص الحروف العربيّة ومعانيها*, Arab Writers Union, 1998).
- Cross-linguistic comparison rests on **Dr. Ali Fahmi Khshim**'s nine sound-substitution laws (*رِحلة الكلمات*).

---

## 2. Core Principles · المبادئ الأساسية

### 2.1 The foundation and what it contributes

The study takes from:

- The **classical Arabic tradition**: the foundational intuition that letter form and meaning are linked through articulation.
- **Jabal**: the empirical dataset — 28 letter charges, 453 binary nuclei, 2,300 unique roots, 1,666 Quranic applications.
- **Abbas**: the sensory-profile axis — six sensory categories crossed with three evolutionary mechanisms (هيجانيّة / إيمائيّة / إيحائيّة).
- **Khshim**: nine sound-substitution laws governing Arabic ↔ European/Semitic correspondences (for Layer 3 only).

Each input is tested against the others. Where they agree, confidence is high. Where they diverge, the data reveals which reading has stronger predictive power.

### 2.2 Data and theory

Jabal occupies a unique position: he provides both a theoretical framework (his 28 letter meanings) and the **primary empirical dataset** (2,300 trilateral roots with full compositional analysis, 453 binary nuclei with shared meanings, 1,666 Quranic applications). His lexicon is the ground truth against which all readings, including his own, are tested.

The classical tradition and Abbas provide complementary theoretical frames that become predictive models within the architecture.

### 2.3 Layered architecture
Each layer of the project does one thing: **compose meanings and check the result.** The architecture grows by stacking layers, never by complicating existing ones. Each layer is independently testable.

### 2.4 Scope, in strict order
1. **Layer 0**: Letter atoms — phonetic charges per letter (28 letters)
2. **Layer 1**: Binary nuclei — composition of pairs into semantic fields (453 nuclei)
3. **Layer 2**: Trilateral roots — twelve composition modes (2,285 roots)
4. **Layer 3**: Cross-linguistic projection — Khshim's substitution laws
5. **Layer 4**: Quranic application — separate downstream project ([coranisyours.com](https://coranisyours.com))

---

## 3. Goals · الأهداف

### 3.1 Settled
- **Unified 28-letter charge table** with the dual-face rule (Layer 0). See [`../03-scholar-extracts/consensus-letter-charges.md`](../03-scholar-extracts/consensus-letter-charges.md).
- **Full 453-nucleus catalog** with Quran-anchored evidence where available (Layer 1). See [`../03-scholar-extracts/jabal-nuclei-extended.md`](../03-scholar-extracts/jabal-nuclei-extended.md).
- **Twelve composition modes** reading 2,285 trilateral roots at 100% native fit (Layer 2). See [`lv2-operative-grammar.md`](lv2-operative-grammar.md).
- **Four-bar verification rubric** for cross-linguistic cognates with 8 Quran-anchored Tier-A pairs (Layer 3). See [`../04-cross-linguistic/tafsir-coran-tier-a-cognates.md`](../04-cross-linguistic/tafsir-coran-tier-a-cognates.md).

### 3.2 In progress
- **Statistical predictive testing** of the letter charges against competing charge sets, running on the computational side of the project. Continuous expansion across new language families.
- **Tier-B cross-linguistic expansion** — 900+ Arabic↔Greek/Latin candidate cognates discovered and under refinement.

### 3.3 Next chapters
- **English-language academic paper** presenting the unified table, the dual-face rule, and the twelve composition modes.
- **Public lookup tool** (CLI or web) that takes an Arabic word and returns its letter → nucleus → root reading.
- **Testing against non-Quranic corpora** (Jahili poetry, modern MSA) to bound the reach beyond Quranic vocabulary.

---

## 4. Sources · المراجع

### 4.1 The empirical foundation

| Source | Contribution | Data points |
|---|---|---|
| **Dr. Muhammad Hassan Jabal** · *المعجم الاشتقاقي المُؤَصَّل* | Modern lexicographic foundation with compositional analysis | 28 letter charges, 453 binary nuclei, 2,300 trilateral roots, 1,666 Quranic applications |

### 4.2 The complementary modern reference

| Source | Contribution | Coverage |
|---|---|---|
| **Hassan Abbas** · *خصائص الحروف العربيّة ومعانيها* (Arab Writers Union, 1998) | Sensory-profile axis — six sensory categories crossed with three evolutionary mechanisms (هيجانيّة / إيمائيّة / إيحائيّة) | 28 letters |

### 4.3 The cross-linguistic anchor

| Source | Contribution | Coverage |
|---|---|---|
| **Dr. Ali Fahmi Khshim** · *رِحلة الكلمات* | Nine sound-substitution laws governing Arabic ↔ European/Semitic correspondences (Layer 3 only — not letter semantics) | Substitution rules, not per-letter charges |

### 4.4 The classical tradition

The deeper anchor for the form-meaning correspondence rests on the classical Arabic linguistic tradition — al-Khalil ibn Ahmad al-Farahidi (*Kitab al-Ayn*, 8th c., founder of Arabic linguistics), Ibn Jinni's *الخصائص* (11th c., the *إمساس الألفاظ أشباه المعاني* doctrine), and the dictionary tradition. The full survey is in [`../01-theory/classical-survey-ar.md`](../01-theory/classical-survey-ar.md).

---

## 5. Layer Architecture · البنية الطبقية

```
┌─────────────────────────────────────────────────────────┐
│  Layer 4 · Quranic Application (separate project)        │
│  The letter → nucleus → root reading applied to verses.   │
│  Lives at coranisyours.com.                               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Layer 3 · Cross-linguistic projection                  │
│  Khshim's nine sound-substitution laws.                   │
│  Four-bar verification rubric for cross-linguistic        │
│  cognates. 8 Tier-A pairs Quran-anchored.                 │
│  Test: Arabic root meanings ↔ cognate language pairs.     │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Layer 2 · Trilateral roots (الجذر الثلاثي)              │
│  2,285 roots read under twelve composition modes (أبواب). │
│  Frame: (binary nucleus) operates on (L3-charge as        │
│  material).                                               │
│  Modes: CARRY · الحَمل  · HOLD · الإمساك                   │
│         RELEASE · الإطلاق · PROJECT · الإبراز              │
│         INTENSIFY · التَّضعيف · BLOCK · الحَجب              │
│         DRAIN · الاستنزاف · CHANNEL · التَّوجيه            │
│         OPERATE · الإعمال · MIX · المَزج                   │
│         REVERT · القَلب · LOANWORD · الدَّخيل               │
│  Result: 100% native fit (99.87% lexicon coverage).       │
│  See: lv2-operative-grammar.md                            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Layer 1 · Binary nuclei (الفصل المعجمي)                 │
│  453 nuclei with shared meanings (المعنى المشترك).         │
│  Test: compose letter features → predict shared meaning.  │
│  See: jabal-nuclei-extended.md                            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Layer 0 · Letter atoms (الحروف)                         │
│  28 letters · unified charge table · dual-face rule.      │
│  Abbas's sensory classification as grouping/validation.   │
│  Structure: feature vectors per letter, with classical    │
│  and modern sources cross-referenced.                     │
│  See: consensus-letter-charges.md                         │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Methods · المنهجية

### 6.1 Hard Problem 1: The Composition Function

There is no closed-form formula for how two letter meanings combine into a binary nucleus meaning. The study tests **four composition hypotheses**:

**Model A · Intersection (التقاطع)**
The shared meaning is the **overlap** between two letter charges. Where both letters point to the same physical quality or action, that becomes the nucleus meaning.
- Implementation: feature set intersection + union weighting
- Example: ب{تجمع,رخاوة} ∩ ر{استرسال,تماسك} → shared quality = soft cohesion → بروز

**Model B · Sequence (التتابع)**
The first letter initiates an action; the second modifies or completes it. The meaning is directional.
- Implementation: ordered feature composition (ح١ features as subject, ح٢ features as predicate)
- Example: ب(soft gathering) → ر(flowing continuity) = gathering that flows outward → بروز

**Model C · Dialectical (الجدليّة)**
The two letters create a tension, and the nucleus meaning is the resolution.
- Implementation: identify contradictory features, resolve by synthesis
- Example: ب(رخاوة/softness) vs ر(تماسك/cohesion) → tension resolves as "soft thing that holds together" → emergence

**Model D · Phonetic-Gestural (الحسّيّ)**
The physical mouth movements of pronouncing both sounds produce a combined gesture whose kinaesthetic quality is itself the meaning (drawing on Abbas's sensory-profile axis).
- Implementation: map articulatory features (مَخرَج, صفة) to semantic features, combine gesturally
- Example: ب(bilabial/soft) + ر(trill/flowing) = gesture of release → emergence

**Testing protocol:** Run all four models on the 453 binary nuclei against Jabal's recorded readings. Produce a score matrix. Analyze which model works best overall, which works best per phonetic class, and where Abbas's sensory axis predicts compositional behaviour.

### 6.2 Hard Problem 2: The Scoring Function

LV1 uses **two complementary scoring methods**:

#### Method B, Atomic Semantic Feature Decomposition (الأساسي)

**The primary, reproducible scoring engine.**

Every semantic description (letter meaning, nucleus meaning, root meaning) is decomposed into a set of **atomic semantic features**, the irreducible building blocks of Arabic phonosemantic description.

**The Atomic Feature Vocabulary** (extracted from Jabal's 28 letter definitions + 456 binary nucleus meanings):

**Category 1, PRESSURE/FORCE (الضغط والقوة)**
ضغط (pressure), احتباس (confinement), تعقد (knotting), اشتداد (intensification), إمساك (gripping), امتساك (holding), قوة (force), تقوية (strengthening), تأكيد (affirmation), ثقل (heaviness)

**Category 2, EXTENSION/MOVEMENT (الامتداد والحركة)**
امتداد (extension), استرسال (flowing), طول (length), اتساع (widening), خروج (emergence), انتقال (transition), وصول (reaching), بروز (protrusion), ظهور (appearance), صعود (ascent)

**Category 3, PENETRATION/PASSAGE (النفاذ والعبور)**
نفاذ (penetration), خلوص (passing through), اختراق (piercing), نقص (diminishment)

**Category 4, GATHERING/COHESION (التجمع والتماسك)**
تجمع (gathering), اكتناز (compactness), ازدحام (crowding), التحام (fusion), تلاصق (adhesion), تماسك (cohesion), اشتمال (encompassing), احتواء (containment), اتصال (connection)

**Category 5, SPREADING/DISPERSAL (الانتشار والتفرق)**
تفشٍّ (spreading), انتشار (dispersal), طرد (expulsion), إبعاد (distancing), فراغ (emptiness), إفراغ (emptying), تفرق (scattering), تخلخل (loosening)

**Category 6, TEXTURE/QUALITY (الملمس والصفة)**
رخاوة (softness), غلظ (coarseness), كثافة (density), ثخانة (thickness), دقة (fineness), رقة (thinness), لطف (gentleness), هشاشة (fragility), جفاف (dryness)

**Category 7, SHARPNESS/CUTTING (الحدة والقطع)**
حدة (sharpness), قطع (cutting), صدم (striking), احتكاك (friction)

**Category 8, SPATIAL ORIENTATION (الاتجاه المكاني)**
باطن (interior), ظاهر (exterior), عمق (depth), جوف (cavity), حيز (space/domain), سطح (surface)

**Category 9, INDEPENDENCE/DISTINCTION (الاستقلال والتميز)**
استقلال (independence), تميز (distinction), تعلق (attachment), استواء (evenness), وحدة (unity)

**Scoring procedure:**
1. Decompose prediction into feature set F_predicted
2. Decompose Jabal's actual meaning into feature set F_actual
3. Score = |F_predicted ∩ F_actual| / |F_predicted ∪ F_actual| (Jaccard similarity)
4. Weighted variant: features weighted by frequency-inverse importance (rare features count more)

#### Method A, Claude Semantic Judge (المُحَكِّم الدلالي)

**The calibration and validation layer.**

For a representative sample of nuclei/roots (e.g., 50-100), Claude evaluates the semantic match between predicted and actual meanings on a 0-100 scale, providing:
- **Score** (0-100): semantic alignment
- **Reasoning**: what aligns, what diverges, what's partially captured
- **Feature gap analysis**: which atomic features are present in one but not the other

**Purpose:** Calibrate Method B. If Method B gives nucleus X a score of 0.7 but Claude gives it 45/100, the feature weights need adjustment. If both agree, the system is reliable. Run periodically as the feature vocabulary and weights are refined.

**The hybrid workflow:**
1. Run Method B on all 456 nuclei → full score matrix (fast, reproducible)
2. Run Method A on 50-100 sample → calibration scores (nuanced, Arabic-aware)
3. Compare B vs A → adjust feature weights and composition model parameters
4. Re-run Method B with calibrated weights → improved full matrix
5. Iterate until B and A converge

### 6.3 The reversibility test (اختبار القَلب)

A standalone test within Layer 1.

For every binary nucleus (X, Y) where the reverse (Y, X) also exists in Jabal's data:
1. Extract المعنى المشترك for both.
2. Decompose into features.
3. Test: does F(Y,X) ≈ the inverse of F(X,Y)?
4. Define "inverse" as: same feature categories but opposite valence (e.g., تَجَمُّع ↔ تَفَرُّق, ضَغط ↔ فَراغ, باطن ↔ ظاهر).
5. Score: percentage of reversible pairs that exhibit meaning inversion.

Output: a quantified confidence level for reversibility as a structural property of Arabic root composition. The test on 155 strict reverse pairs in Jabal's corpus yielded a 22% inverse hit-rate — a bounded, partial confirmation rather than a universal law.

### 6.4 Sensory validation (Abbas axis)

A cross-check layer on Layer 0.

Abbas groups letters into six sensory categories based on articulatory properties, with a triple mechanism:
- **هيجانيّة** (exclamatory) — earliest evolutionary stage, emotional outbursts.
- **إيمائيّة** (imitative) — physical articulation gesture directly mimics meaning (e.g., ف lips part = فَصل, ب lips close = ضيق, م lips seal = ضمّ, ل tongue slides = التصاق, ر tongue trills = تَكرار).
- **إيحائيّة** (suggestive) — emotional resonance of sound evokes meaning (e.g., ن nasal = أنين/حنين, ص sharp clear = نَقاء, ح warm breath = سَعة).

Tests:
1. Do letters within the same Abbas category have similar atomic feature profiles?
2. Do nuclei composed of same-category letters behave differently from cross-category nuclei?
3. Does Abbas's إيماء/إيحاء distinction correlate with composition model accuracy? (إيماء letters may compose gesturally better; إيحاء letters may compose dialectically better.)

---

## 7. Data Structures, هياكل البيانات

### 7.1 Letter Registry (سجل الحروف)

| Letter | Source | Raw Description | Feature Vector | Sensory Category (Abbas) |
|--------|--------|-----------------|----------------|--------------------------|
| ب | Jabal | تجمع رخو مع تلاصق ما | {تجمع, رخاوة, تلاصق} | — |
| ب | Abbas | [his definition] | {features} | إيمائيّة |
| ب | Unified table | اتّصال + تَمَسُّك | {اتّصال, تَمَسُّك} | — |

### 7.2 Binary Nucleus Registry (سجل الجذور الثنائية)

| Nucleus | ح١ | ح٢ | Jabal المعنى المشترك | Jabal Features | Model A Score | Model B Score | Model C Score | Model D Score | Best Model | Reverse Exists? | Golden Rule Score |
|---------|----|----|---------------------|----------------|---------------|---------------|---------------|---------------|------------|-----------------|-------------------|

### 7.3 Trilateral Root Registry (سجل الجذور الثلاثية)

| Root | Binary Nucleus | Added Letter | Jabal المعنى المحوري | Predicted Meaning | Score | Quranic Verse | Quranic Match |
|------|---------------|-------------|---------------------|-------------------|-------|---------------|---------------|

---

## 8. Scope Boundaries · حدود النطاق

### IN SCOPE — Layers 0–2 (the Arabic genome):
- Letter charges for the 28 letters, with the dual-face rule.
- Binary nucleus composition and testing (453 nuclei).
- Trilateral root reading under the twelve composition modes (2,285 roots).
- The reversibility test.
- Abbas's sensory validation.
- Quantitative scoring framework.

### IN SCOPE — Layer 3 (cross-linguistic):
- Khshim's nine sound-substitution laws.
- The four-bar verification rubric.
- Tier-A and Tier-B cognate ledger.
- Comparison with Semitic and Indo-European cognates.

### OUT OF SCOPE — Layer 4 (separate project):
- **Quranic application system** — applies the completed genome to specific Quranic verses. Lives at [coranisyours.com](https://coranisyours.com). Built on top of the settled genome.

---

## 9. Execution Pipeline · خطوات التنفيذ

### Phase 1: Letter Atoms (Layer 0)
1. Extract letter definitions from Jabal and Abbas, with cross-reference to the classical sources.
2. Decompose each into atomic semantic features.
3. Build the Letter Registry.
4. Apply Abbas's sensory classification as grouping layer.
5. **Deliverable:** the unified 28-letter charge table.

### Phase 2: Binary Nucleus Engine (Layer 1)
1. Map all 453 nuclei from Jabal's lexicon.
2. For each nucleus, run the four composition models.
3. Score using feature Jaccard.
4. Calibrate with a semantic-judge layer on a 50–100 nucleus sample.
5. Identify best model per phonetic class.
6. Run the reversibility test on all reversible pairs.
7. **Deliverable:** scored Binary Nucleus Registry + reversibility report.

### Phase 3: Trilateral Root Reading (Layer 2)
1. For each of 2,285 trilateral roots, identify the composition mode (one of twelve).
2. Score readings against Jabal's المعنى المحوري.
3. Calculate overall coverage and per-باب distribution.
4. Identify systematic failure patterns → refine the mode taxonomy.
5. **Deliverable:** scored Root Registry + the twelve-mode coverage report. See [`lv2-operative-grammar.md`](lv2-operative-grammar.md).

### Phase 4: Sensory Validation
1. Cross-check Abbas's categories against composition results.
2. Test whether sensory grouping predicts composition behavior.
3. **Deliverable:** validation report.

### Phase 5: Cross-linguistic Projection (Layer 3)
1. Apply Khshim's nine sound-substitution laws + known phonetic shifts.
2. Project Arabic root meanings → cross-linguistic cognates (Semitic and Indo-European).
3. Test predictions against the four-bar verification rubric.
4. **Deliverable:** Tier-A/B/Reject ledger. See [`../04-cross-linguistic/tafsir-coran-tier-a-cognates.md`](../04-cross-linguistic/tafsir-coran-tier-a-cognates.md).

---

## 10. Success Metrics · معايير النجاح

| Metric | Status | Layer |
|--------|--------|-------|
| Trilateral root composition coverage | 100% native fit on 2,285 of 2,288 roots ✅ | Layer 2 — see [`lv2-operative-grammar.md`](lv2-operative-grammar.md) |
| Dual-face rule confirmation | Confirmed across all 453 binary nuclei ✅ | Layer 0 |
| Binary nucleus prediction accuracy (best model) | Quantitative scoring runs on the computational side of the project | Layer 1 |
| Reversibility confirmation rate | 22% inverse hit-rate on 155 strict reverse pairs (partial, bounded) | Layer 1 |
| Cross-linguistic Tier-A pairs | 8 Quran-anchored pairs confirmed ✅ | Layer 3 |
| Abbas sensory grouping significance | Continuous validation on the computational side | Validation |

---

## 11. Technical Implementation · التنفيذ التقني

**Form:** Structured xlsx workbooks (the data, readable, editable) + Python scoring engine (the lab, runs tests, produces scores).

**Why xlsx:** The data is directly inspectable, editable, and extensible. The genome is not a black box; it is a transparent, inspectable structure.

**Why Python:** Composition models, feature decomposition, scoring, and statistical analysis require computation. Python reads the xlsx, runs the tests, writes results back. The computational side of the project lives in `Juthoor-Linguistic-Genealogy/` and implements Layers 0–3 end-to-end.

**Why the semantic-judge layer:** Arabic semantic comparison requires linguistic intelligence that keyword matching alone cannot capture. A semantic-judge calibration layer ensures the mechanical Jaccard scoring reflects genuine semantic alignment.

---

## 12. Open Questions · أسئلة مفتوحة

1. **Feature granularity:** Is ~50 atomic features the right number? Too few loses nuance; too many introduces noise. The calibration loop will answer this.

2. **Composition model mixing:** Should the architecture use one composition model globally, or allow different models for different phonetic classes? The data will tell.

3. **Coverage:**
   - **Jabal:** 28/28 letters with full lexicon. ✅
   - **Abbas:** 23 letters with detailed sensory profiles + 3 جوفيّات (ا، و، ي) treated as a special group (Abbas calls them directional). The dual-face rule in this study restores active charges to all three.
   - **Khshim:** Nine sound-substitution laws (not per-letter charges). Applies to Layer 3 only.
   - The classical sources (al-Khalil, Ibn Jinni) supply the foundational intuition and the articulatory framework, but not a one-per-letter charge in the modern sense.

4. **Jabal's internal consistency:** Before testing alternative readings against Jabal's data, the project verifies that Jabal's own letter meanings consistently predict his own nucleus meanings — this establishes the baseline score against which competing readings are measured.

5. **Weight of Quranic data:** The 1,666 Quranic entries are reserved for the separate Quranic application (Layer 4). The genome stays linguistically pure, then is applied Quranically.

---

## Appendix A: Jabal's 28 Letter Meanings (المعنى اللغوي الجوهري)

| Letter | Symbol | المعنى اللغوي الجوهري |
|--------|--------|----------------------|
| الهمزة | ء | تؤكد معنى ما تصحبه / ضغط وتقوية |
| الباء | ب | تجمع رخو مع تلاصق ما |
| التاء | ت | ضغط بدقة ووحدة، قد يؤدي إلى إمساك ضعيف أو قطع |
| الثاء | ث | كثافة أو غلظ مع تفشٍّ وانتشار |
| الجيم | ج | تجمع هش مع حدة ما |
| الحاء | ح | احتكاك بعرض وجفاف في الباطن |
| الخاء | خ | تخلخل مع جفاف أو غلظ |
| الدال | د | احتباس بضغط وامتداد طولي |
| الذال | ذ | نفاذ ثخين ذي رخاوة وغلظ |
| الراء | ر | استرسال مع تماسك ما |
| الزاي | ز | اكتناز وازدحام |
| السين | س | امتداد بدقة ووحدة |
| الشين | ش | تفشٍّ أو انتشار مع دقة |
| الصاد | ص | نفاذ بغلظ وقوة وخلوص |
| الضاد | ض | ضغط بكثافة وغلظ |
| الطاء | ط | ضغط باتّساع واستغلاظ |
| الظاء | ظ | نفاذ بغلظ أو حدّة مع كثافة |
| العين | ع | التحام على رقة مع حدة ما / رخاوة جرم ملتحم |
| الغين | غ | تخلخل مع شيء من رخاوة وكثافة |
| الفاء | ف | طرد وإبعاد ونفاذ بقوة |
| القاف | ق | تعقد واشتداد في العمق |
| الكاف | ك | ضغط غُؤوري دقيق يؤدي إلى امتساك أو قطع |
| اللام | ل | تعلق أو امتداد مع استقلال أو تميز |
| الميم | م | امتساك واستواء ظاهري |
| النون | ن | امتداد لطيف في الباطن أو منه |
| الهاء | ه | فراغ أو إفراغ ما في الجوف |
| الواو | و | اشتمال واحتواء |
| الياء | ي | اتصال الممتد شيئاً واحداً وعدم تفرقه |

---

## Appendix B: Jabal's Dataset Statistics

| Metric | Value |
|--------|-------|
| Total trilateral roots | 2,300 unique (1,924 lexicon entries) |
| Binary nuclei | 453 |
| أبواب (letter chapters) | 25 |
| Roots with Quranic application | 1,666 (86.6%) |
| Most productive nucleus | س ر (18 roots) |
| Most productive باب | النون (136 entries) |
| Most common added letter | و (180 times) |

**Top 15 semantic terms in binary nucleus meanings** (frequency in 453 descriptions):
الامتداد (176), النفاذ (110), بقوة (92), التجمع (83), نفاذ (73), فراغ (59), الغلظ (51), حدة (49), الانتشار (42), الظاهر (42), الرقة (37), الباطن (36), رخاوة (36), الضغط (32), دقة (32)
