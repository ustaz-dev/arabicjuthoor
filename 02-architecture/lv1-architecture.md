# Juthoor LV1, Architecture, Vision & Methods
## المخطط المعماري لمشروع جُذور, المستوى الأول

**Author:** Yassine Temessek

---

## 1. Vision, الرؤية

Juthoor LV1 is a **computational engine for decoding the Arabic genome**, the pre-grammatical semantic layer where meaning is physically encoded in sound.

The Arabic language, unlike the Saussurean model of arbitrary signs, carries meaning at the sub-root level: individual letters have kinetic/physical semantic values, pairs of letters (binary nuclei) form semantic fields, and trilateral roots are compositions of these atoms. This is not metaphor, it is a testable, quantifiable system.

LV1's job is to **formalize, test, and score** this system using the combined insights of 7 independent scholars who each discovered parts of it, plus the empirical dataset of Sheikh Jabal's etymological dictionary (المعجم الاشتقاقي الموصل).

---

## 2. Core Principles, المبادئ الأساسية

### 2.1 Scholars Complement, Not Conflict
The 7 scholars reached different explanations from different angles. They are not competing, they are illuminating different facets of the same structure. LV1 does not arbitrate between them by opinion; it **tests each theory against data** and produces quantitative scores. Where scholars agree, confidence is high. Where they diverge, the data reveals which model has stronger predictive power, or reveals that different models work best for different phonetic classes.

### 2.2 Data vs. Theory
**Sheikh Jabal** occupies a unique position: he provides both a theory (his 28 letter meanings) and the **primary empirical dataset** (1,924 roots with full compositional analysis, 456 binary nuclei with shared meanings, 1,666 Quranic applications). His dictionary is the ground truth that all theories, including his own, are tested against.

The other scholars provide **theoretical frameworks** (letter semantics, composition rules, validation principles) that become predictive models within LV1.

### 2.3 Simple Layers, Rigorous Testing
Each layer of LV1 does one thing: **compose meanings and check the result.** The architecture grows by stacking layers, never by complicating existing ones. Each layer is independently testable.

### 2.4 Arabic Genome First
LV1's scope is strictly ordered:
1. **Core genome**, letter semantics → binary nuclei → trilateral roots (Arabic only)
2. **Intra-Semitic extension**, sound laws and phonetic shifts within the Semitic family
3. **Cross-linguistic projection**, universal language theories (future, separate layer)
4. **Quranic application**, entirely separate project, built on the completed genome

---

## 3. Goals, الأهداف

### 3.1 Immediate Goals (This Phase)
- Build the **Letter Semantics Registry** with all scholars' values decomposed into atomic features
- Build the **Binary Nucleus Registry** with testable composition predictions
- Establish the **scoring framework** (both computational and Claude-judged)
- Run first-pass tests on Jabal's 456 binary nuclei

### 3.2 Medium-Term Goals
- Complete **trilateral root prediction engine** (1,924 roots)
- Test عنبر's Golden Rule systematically across all reversible nuclei
- Integrate عباس's sensory classification as validation layer
- Quantify composition model accuracy per phonetic class

### 3.3 Long-Term Goals
- Extend to intra-Semitic comparisons using خشيم's sound laws + known phonetic shifts
- Build Quranic application system (separate project)
- Cross-linguistic extension (النيلي + ذوق + الشناوي)

---

## 4. The Scholars, المصادر العلمية

### 4.1 The Dataset Provider

| Scholar | Contribution | Data Points |
|---------|-------------|-------------|
| **الشيخ محمد حسن جبل** | المعجم الاشتقاقي الموصل, full etymological dictionary with compositional analysis | 28 letter meanings, 456 binary nuclei, 1,924 trilateral roots, 1,666 Quranic applications |

### 4.2 The Theorists

| Scholar | Core Theory | Letters Covered (verified) | Key Framework | Relationship to Others |
|---------|-------------|--------------------------|---------------|----------------------|
| **عاصم المصري** | جدلية التناقض, dialectical contradiction in letter names; الفصل المعجمي, binary nucleus defines semantic field | **28 letters** (complete table in جدول معاني الحروف) | Contradiction of letter names reveals المعنى الحركي; binary nucleus is the semantic atom | **Explicitly continued النيلي's work.** States: "هذه رؤية كان بدأها عالم سبيط النيلي." Cites النيلي 30+ times. Used same القصدية framework, completed what النيلي started. |
| **عالم سبيط النيلي** | قصدية الإشارة, intentionality of linguistic signs; الدلالة الحركية, kinetic meaning; المنهج اللفظي, verbal method | **10 letters** (د,ح,ر,ت,ك,م,ب,ع,ل,ي). The remaining 18 are NOT in available sources. | المعنى المفهومي (conceptual/kinetic) vs المصداق (conventional instance); 6 rules of no-metaphor interpretation | **Founder of the القصدية framework.** His 10 letters are important, but his bigger value is methodological. عاصم المصري completed his 28-letter project. |
| **حسن عباس** | خصائص الحروف العربية, sensory articulation profiles; statistical validation across 9,767 sources | **23 letters** (detailed) **+ 3 جوفية** (أ,و,ي treated as special group = "directions": أ=للأعلى, و=للأمام, ي=للأسفل). Total: 26 entries. | 6 sensory categories; triple mechanism: هيجانية (exclamatory) / إيمائية (imitative gesture) / إيحائية (suggestive resonance) | **Independent work.** No citation of النيلي. Came from sensory/articulatory/statistical direction. Best used as validation/routing layer, not primary scoring prior. |
| **محمد عنبر** | جدلية الحرف, dialectics of the letter; القاعدة الذهبية, reversing consonant order reverses meaning | **25 letters** (21 explicit + 4 contextual). Explicit: م,ف,ب (شفوية) + ص,ق,ض (تفخيم) + ر,ل,ن (ذلقية) + س,ز,ش (صفيرية) + ح,ع,خ (حلقية) + د (شديدة) + و,ي,ا/ء (مد+همزة). Contextual: ج (ستر/خفاء), ك (انطواء/منع), ت (قطع/فصل), غ (خفاء/غموض). Only ط,ث,ظ truly missing. NOTE: raw source PDF is heavily OCR-damaged; extracted data from NotebookLM (4 notes) is clean. | Golden Rule is a **hypothesis to test**, not confirmed law: قرأ↔رقأ, فكر↔كفر; letter meaning derived from articulatory physics | **Independent work.** Primary role = reversal/inversion testing + articulatory-physical letter definitions. |
| **علي فهمي خشيم** | 9 قوانين الإبدال, sound substitution laws; Sumerian-Arabic shared roots | Phonetic shift rules (not letter semantics) | Arabic→European transitions: ق→C/K, ع→vowel, ح→H, etc. | For Layer 3 (intra-Semitic) only |
| **محمد رشيد ناصر ذوق** | لغة آدم, Phoenician pictographic origins; letters as visual symbols of meaning | **3 letters** (examples only: تاء, هاء, أليف) | Pictographic letter origins: تاء=صليب=تابوت, هاء=رجل يصلي=هدى, أليف=حيوان أليف | For Layer 4 (cross-linguistic) only |
| **خالد نعيم الشناوي** | اللغات العروبية, Arabic as closest to proto-language; phonetic/morphological/syntactic evidence | Comparative data (not letter semantics) | Rejects "Semitic" label; Arabic preserves original phonetic inventory better than all sister languages | For Layer 3-4 only |

---

## 5. Layer Architecture, البنية الطبقية

```
┌─────────────────────────────────────────────────────────┐
│              SEPARATE PROJECT: Quranic System            │
│         (النيلي المنهج اللفظي + عاصم جدلية التناقض)         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Layer 4, Cross-Linguistic (FUTURE)                     │
│  النيلي unified language + ذوق pictographs + الشناوي       │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Layer 3, Intra-Semitic Extension                       │
│  خشيم 9 sound laws + known phonetic shifts               │
│  الشناوي comparative evidence                            │
│  Test: Arabic root meanings → Semitic cognate prediction  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Layer 2, Trilateral Roots (الجذر الثلاثي)                │
│  2,285 roots graded under operative grammar               │
│  Frame: (binary) DOES X to (L3-charge as material)        │
│  12 modes: CARRY · HOLD · RELEASE · PROJECT · INTENSIFY ·  │
│             BLOCK · DRAIN · CHANNEL · OPERATE · MIX ·     │
│             REVERT · LOANWORD                              │
│  Result: 100% native composition (99.87% lexicon coverage)│
│  See: lv2-operative-grammar.md                            │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Layer 1, Binary Nuclei (الفصل المعجمي)                  │
│  456 nuclei with المعنى المشترك                           │
│  Test: compose letter features → predict shared meaning   │
│  Also: test عنبر Golden Rule on reversible pairs          │
│  Score: per scholar × per composition model               │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  Layer 0, Letter Atoms (الحروف)                         │
│  28 letters × 5+ scholars × atomic semantic features     │
│  عباس sensory classification as grouping/validation      │
│  Structure: feature vectors per letter per scholar        │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Methods, المنهجية

### 6.1 Hard Problem 1: The Composition Function

No scholar provides an explicit formula for how two letter meanings combine into a binary nucleus meaning. LV1 tests **four composition models**:

**Model A, Intersection (التقاطع)**
The shared meaning is the **overlap** between two letter meanings. Where both letters point to the same physical quality or action, that becomes the nucleus meaning.
- Implementation: feature set intersection + union weighting
- Example: ب{تجمع,رخاوة} ∩ ر{استرسال,تماسك} → shared quality = soft cohesion → بروز

**Model B, Sequence (التتابع)**
The first letter initiates an action, the second modifies or completes it. The meaning is directional.
- Implementation: ordered feature composition (ح١ features as subject, ح٢ features as predicate)
- Example: ب(soft gathering) → ر(flowing continuity) = gathering that flows outward = بروز

**Model C, Dialectical (الجدلية)**
Following عاصم المصري: the two letters create a tension, and the nucleus meaning is the resolution.
- Implementation: identify contradictory features, resolve by synthesis
- Example: ب(رخاوة/softness) vs ر(تماسك/cohesion) → tension resolves as "soft thing that holds together" = emergence

**Model D, Phonetic-Gestural (الحسّي)**
Following حسن عباس: the physical mouth movements of pronouncing both sounds produce a combined gesture whose kinaesthetic quality IS the meaning.
- Implementation: map articulatory features (مخرج, صفة) to semantic features, combine gesturally
- Example: ب(bilabial/soft) + ر(trill/flowing) = gesture of release = emergence

**Testing protocol:** Run all 4 models on all 456 binary nuclei using each scholar's letter values. Produce a **456 × 4 × N** score matrix. Analyze which model works best overall, which works best per phonetic class, and which scholar's values give highest accuracy per model.

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

### 6.3 عنبر's Golden Rule Test

**Standalone test within Layer 1.**

For every binary nucleus (X, Y) where the reverse (Y, X) also exists in Jabal's data:
1. Extract المعنى المشترك for both
2. Decompose into features
3. Test: does F(Y,X) ≈ inverse/opposite of F(X,Y)?
4. Define "inverse" as: same feature categories but opposite valence (e.g., تجمع↔تفرق, ضغط↔فراغ, باطن↔ظاهر)
5. Score: percentage of reversible pairs that exhibit meaning inversion

Output: A quantified confidence level for the Golden Rule as a structural law of Arabic.

### 6.4 عباس Sensory Validation

**Cross-check layer on Layer 0.**

عباس groups letters into 6 sensory categories based on articulatory properties, with a **triple mechanism** (verified from source):
- **هيجانية** (exclamatory), earliest evolutionary stage, emotional outbursts
- **إيمائية** (imitative), physical articulation gesture directly mimics meaning (e.g., ف lips part = فصل, ب lips close = ضيق, م lips seal = ضم, ل tongue slides = التصاق, ر tongue trills = تكرار)
- **إيحائية** (suggestive), emotional resonance of sound evokes meaning (e.g., ن nasal = أنين/حنين, ص sharp clear = نقاء, ح warm breath = سعة)

Test:
1. Do letters within the same عباس category have similar atomic feature profiles?
2. Do nuclei composed of same-category letters behave differently from cross-category nuclei?
3. Does عباس's إيماء/إيحاء distinction correlate with composition model accuracy? (e.g., إيماء letters may compose gesturally better, إيحاء letters may compose dialectically better)

---

## 7. Data Structures, هياكل البيانات

### 7.1 Letter Registry (سجل الحروف)

| Letter | Scholar | Raw Description | Feature Vector | Sensory Category (عباس) |
|--------|---------|-----------------|----------------|------------------------|
| ب | جبل | تجمع رخو مع تلاصق ما | {تجمع, رخاوة, تلاصق} | ... |
| ب | عاصم | [his definition] | {features} |, |
| ب | عباس | [his definition] | {features} | إيماء/إيحاء |
| ب | النيلي | [if covered] | {features} |, |
| ب | عنبر | [his definition] | {features} |, |

### 7.2 Binary Nucleus Registry (سجل الجذور الثنائية)

| Nucleus | ح١ | ح٢ | Jabal المعنى المشترك | Jabal Features | Model A Score | Model B Score | Model C Score | Model D Score | Best Model | Reverse Exists? | Golden Rule Score |
|---------|----|----|---------------------|----------------|---------------|---------------|---------------|---------------|------------|-----------------|-------------------|

### 7.3 Trilateral Root Registry (سجل الجذور الثلاثية)

| Root | Binary Nucleus | Added Letter | Jabal المعنى المحوري | Predicted Meaning | Score | Quranic Verse | Quranic Match |
|------|---------------|-------------|---------------------|-------------------|-------|---------------|---------------|

---

## 8. Scope Boundaries, حدود النطاق

### IN SCOPE for LV1 Core:
- Letter semantics (28 letters × all scholars)
- Binary nucleus composition and testing (456 nuclei)
- Trilateral root prediction (1,924 roots)
- عنبر Golden Rule testing
- عباس sensory validation
- Scoring framework (Method A + Method B)

### IN SCOPE for LV1 Final Layer:
- Intra-Semitic sound laws (خشيم's 9 + known phonetic shifts)
- Comparison with Semitic "dialects" (Aramaic, Hebrew, Akkadian, etc.)
- الشناوي's comparative evidence

### OUT OF SCOPE (Separate Projects):
- **Quranic Application System**, uses the completed genome to interpret Quranic roots via النيلي's المنهج اللفظي and عاصم's dialectical method. Built AFTER the genome is solid.
- **Universal Language Extension**, النيلي's unified language theory, ذوق's Phoenician pictographs, قانون الإزاحة. Built AFTER intra-Semitic layer is validated.

---

## 9. Execution Pipeline, خطوات التنفيذ

### Phase 1: Letter Atoms
1. Extract all scholars' letter definitions from NotebookLM notes and source files
2. Decompose each into atomic semantic features
3. Build the Letter Registry (28 × 5+ scholars)
4. Apply عباس sensory classification as grouping layer
5. **Deliverable:** Complete Letter Registry xlsx

### Phase 2: Binary Nucleus Engine
1. Map all 456 nuclei from Jabal's dictionary
2. For each nucleus, run 4 composition models × N scholar letter values
3. Score using Method B (feature Jaccard)
4. Calibrate with Method A (Claude judge) on 50-100 sample
5. Identify best model per phonetic class
6. Test Golden Rule on all reversible pairs
7. **Deliverable:** Scored Binary Nucleus Registry xlsx + Golden Rule report

### Phase 3: Trilateral Root Prediction
1. For each of 1,924 roots, predict meaning from binary nucleus + added letter
2. Score predictions against Jabal's المعنى المحوري
3. Calculate overall accuracy and per-باب accuracy
4. Identify systematic failure patterns → refine composition models
5. **Deliverable:** Scored Root Registry xlsx + accuracy report

### Phase 4: Sensory Validation
1. Cross-check عباس categories against composition results
2. Test whether sensory grouping predicts composition behavior
3. **Deliverable:** Validation report

### Phase 5: Intra-Semitic Extension
1. Apply خشيم's 9 sound laws + known phonetic shifts
2. Project Arabic root meanings → Semitic cognates
3. Test predictions against comparative data
4. **Deliverable:** Semitic projection registry

---

## 10. Success Metrics, معايير النجاح

| Metric | Target | Layer |
|--------|--------|-------|
| Binary nucleus prediction accuracy (best model) | >70% | Layer 1 |
| Trilateral root composition coverage | 100% native (99.87% lexicon) ✅ | Layer 2, see `lv2-operative-grammar.md` |
| Golden Rule confirmation rate | Quantified % | Layer 1 |
| Method A ↔ Method B correlation | >0.8 | Scoring |
| عباس sensory grouping significance | p < 0.05 | Validation |

---

## 11. Technical Implementation, التنفيذ التقني

**Form:** Structured xlsx workbooks (the data, readable, editable) + Python scoring engine (the lab, runs tests, produces scores)

**Why xlsx:** Yassine can see, edit, and extend the data directly. The genome is not a black box, it's a transparent, inspectable structure.

**Why Python:** Composition models, feature decomposition, scoring, and statistical analysis require computation. Python reads the xlsx, runs the tests, writes results back.

**Why Claude (Method A):** Arabic semantic comparison requires linguistic intelligence that keyword matching alone cannot capture. Claude serves as the calibration oracle, not the primary engine, but the quality control layer that ensures Method B's mechanical scoring reflects genuine semantic alignment.

---

## 12. Open Questions, أسئلة مفتوحة

1. **Feature granularity:** Is ~50 atomic features the right number? Too few = loss of nuance. Too many = noise. The calibration loop (Method A vs B) will answer this.

2. **Composition model mixing:** Should LV1 use one composition model globally, or allow different models for different phonetic classes? The data will tell us.

3. **Scholar coverage gaps (VERIFIED STATUS):**
   - **جبل:** 28/28, complete. ✅
   - **عاصم المصري:** 28/28, complete (continued النيلي's work). ✅
   - **النيلي:** 10/28, only 10 in available sources. The other 18 genuinely do NOT exist in our files. His main value is methodological (القصدية, المنهج اللفظي), not letter-by-letter coverage.
   - **عباس:** 23/28 detailed + 3 جوفية (أ,و,ي) as special group = 26 entries. و and ي ARE present but treated as directional/spatial rather than sensory. إيماء/إيحاء classification EXISTS in source data but needs systematic tabulation per letter.
   - **عنبر:** 25/28, 21 explicit + 4 contextual (ج,ك,ت,غ) from NotebookLM targeted queries. Only ط,ث,ظ truly missing. Raw PDF is OCR-damaged but extracted notes (4 notes) are clean and usable.
   - **ذوق:** 3/28, examples only (تاء, هاء, أليف). Do not expect more from available source.
   - **خشيم, الشناوي:** No individual letter semantics, they provide phonetic shift rules and comparative data.
   - **Handling gaps:** Where a scholar has no value for a letter, that cell is empty. Scores are calculated only on letters they defined. No fabrication.

4. **Jabal's internal consistency:** Before testing other scholars against Jabal's data, should we first verify that Jabal's own letter meanings consistently predict his own nucleus meanings? This would establish a baseline score.

5. **Weight of Quranic data:** The 1,666 Quranic entries (verified from xlsx, exactly 1,666 non-null out of 1,924 rows) are reserved for the separate Quranic project. Keep the genome linguistically pure, then apply Quranically.

6. **Codex pipeline discrepancy:** The Juthoor Codex project reports 1,938 roots with 1,739 quran_examples. Our xlsx canonical source has 1,924 roots with 1,666 Quranic entries. This mismatch (1,938 vs 1,924 roots; 1,739 vs 1,666 Quranic) needs an audit in the Codex ingestion pipeline. The xlsx is ground truth.

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
| Total trilateral roots | 1,924 |
| Binary nuclei | 456 |
| أبواب (letter chapters) | 25 |
| Roots with Quranic application | 1,666 (86.6%) |
| Most productive nucleus | س ر (18 roots) |
| Most productive باب | النون (136 entries) |
| Most common added letter | و (180 times) |

**Top 15 semantic terms in binary nucleus meanings** (frequency in 456 descriptions):
الامتداد (176), النفاذ (110), بقوة (92), التجمع (83), نفاذ (73), فراغ (59), الغلظ (51), حدة (49), الانتشار (42), الظاهر (42), الرقة (37), الباطن (36), رخاوة (36), الضغط (32), دقة (32)

---

## Appendix C: NotebookLM Notebooks (Reference)

| Scholar | Notebook ID | Notes |
|---------|-------------|-------|
| عاصم المصري | 033e13f9-12f0-4b2d-b072-274bca1ad260 | 4 |
| عالم سبيط النيلي | f2b9a010-d04b-443b-bc11-522202714b0c | 6 |
| حسن عباس | e9f5e1ab-171d-42f1-85b9-bc7955b3a029 | 4 |
| محمد عنبر | 59ad6f8f-56d3-4a19-bb37-342f65666c16 | 3 |
| علي فهمي خشيم | 8b435614-87f6-4e63-a35d-6619a674eb19 | 4 |
| محمد رشيد ناصر ذوق | 52ef0a2c-9e06-4757-9d0b-d9550e3d2247 | 3 |
| خالد نعيم الشناوي | 53ba035c-6603-4fe5-a173-389be46cd06e | 3 |

**Total:** 27 notes + 21 studio artifacts (7 mind maps + 7 data tables + 7 briefing reports)
