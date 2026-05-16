# LV1, The Arabic Linguistic Genome: Complete Overview

**Project:** Juthoor Linguistic Genealogy
**Module:** Juthoor-ArabicGenome-LV1
**Author:** Yassine Temessek

> **Role:** plain-English public companion to [`lv1-architecture.md`](lv1-architecture.md). When the two disagree, the architecture doc wins.
>
> **Architecture & methods:** see [`lv1-architecture.md`](lv1-architecture.md) for the full layer architecture, composition models, scoring methods, execution pipeline, and scope boundaries.

---

## What Is LV1?

LV1 is a computational engine that decodes the **pre-grammatical semantic layer** of the Arabic language. It operates on a specific hypothesis: Arabic words are not arbitrary labels, they are built from meaningful components in a structured, testable way.

The Arabic language uses a **trilateral root system**: most words derive from 3-consonant roots (e.g. **ك-ت-ب** k-t-b = everything related to writing). LV1 goes deeper, it investigates what happens *inside* those roots, at the level of individual letters and two-letter combinations.

---

## The Core Theory

LV1 is built on the work of **Dr. Muhammad Hassan Jabal** (المعجم الاشتقاقي المؤصل, 2010), enriched by five other scholars. The theory has six pillars:

### 1. Every Letter Has a Semantic Value

Each of the 28 Arabic letters carries its own meaning. This is not metaphorical, it's a testable claim. Multiple scholars have independently assigned semantic values to Arabic letters:

| Scholar | Letters Covered | Method |
|---------|----------------|--------|
| **Jabal** | 28 letters + 456 binary nuclei + 1,924 roots | Lexical induction from المعجم الاشتقاقي الموصل |
| **Hassan Abbas** | 23 | Sensory/perceptual profiling: 6 categories (tactile, gustatory, visual, auditory, emotional non-pharyngeal, emotional pharyngeal). 9,767 sources reviewed, 38-95% concordance |
| **Neili** | 10 | Physical movement analysis: د=directed thrust, ح=self-amplification, ر=repetitive ordering, ت=attraction, ك=clustering, م=completion, ب=eruption, ع=clarification, ل=fusion, ي=temporal continuity |
| **Asim al-Masri** | 28 (complete) | Dialectical contradiction in letter names. 3 types: vs. hamza, vs. other letters, internal/cyclic |
| **Anbar** | All (qualitative) | Dialectical reversal: reversing letter order reverses meaning (قرأ=gather ↔ رقأ=cease) |
| **Hassan Abbas (stats)** | 23 | Dual mechanism: إيماء (articulatory mimicry) and إيحاء (acoustic evocation) |

Example from Jabal:
- **ب (ba)** = accumulative gathering with adhesion
- **ت (ta)** = precise pressure
- **ح (ha)** = internal dryness with friction across a surface
- **ف (fa)** = penetration with force to the exterior, with expansion

### 2. The First Two Consonants Define a Semantic Field (الفصل المعجمي)

This is Jabal's central innovation. The first two consonants of any Arabic root form a **binary nucleus** that defines the semantic field. All roots sharing the same binary nucleus cluster around a common abstract meaning.

Example, the binary nucleus **ح-س** (ha-sin):
- All roots starting with ح-س share the meaning: *"sharp penetration into a broad surface with removal of what spreads on it"*
- حسب (hasaba) = to reckon/count (gathering scattered things precisely)
- حسد (hasada) = envy (a sharp feeling trapped inside)
- حسر (hasara) = regret/exposure (continuous sharp removal)

Jabal identified **367 such binary fields** across 2,300+ Arabic roots.

### 3. The Third Letter Specializes Within the Field

The third consonant doesn't create new meaning, it **modifies** the field established by the first two. In the ح-س example:
- ب (adhesion) → حسب = accumulating/reckoning
- د (confinement) → حسد = trapped sharp feeling (envy)
- ر (flow/continuity) → حسر = continuous removal (regret)

One reviewer described this system as producing *"something like chemical equations"*, each letter contributes a known value, and the combination yields predictable results.

### 4. Position Matters, Meaning Is Order-Sensitive

Unlike Ibn Jinni's classical theory (where all 6 permutations of 3 letters share one meaning), Jabal's model is **position-sensitive**: ك-ت-ب and ب-ك-ت are different roots with different meanings, because the first two letters define different fields.

This was computationally confirmed by LV1's Research Factory:
- **H5 (order matters): Supported**, metathesis changes meaning
- **H8 (positional semantics): Supported**, 24 of 28 letters show statistically significant meaning shifts by position

### 5. Each Root Has One Abstract Conceptual Meaning (المعنى المحوري)

Following Ibn Faris (مقاييس اللغة, ~1004 CE), every root has a single abstract concept from which all surface meanings derive. This concept is **physical/sensory** at its base, with metaphorical extensions.

Example, root **ج-ن-ن** (j-n-n):
- Abstract concept: **concealment/covering** (ستر)
- جُنّة (junna) = shield → covers the body
- أجنّه الليل = night covered him
- جنين (janeen) = fetus → concealed in the womb
- جنّ (jinn) = invisible beings → concealed from sight
- جنون (junoon) = madness → the mind is covered/hidden

### 6. No Synonymy in Quranic Arabic

Building on Neili's intentionality principle and Samarrai's contrastive analysis: every word in the Quran carries a unique meaning that no other word can replace. What appears as synonymy in translations is actually **precision**, each word captures a distinct conceptual shade.

Examples from Samarrai:
- **خوف** (khawf) = fear of the unknown vs **خشية** (khashya) = fear of the known with reverence
- **قلب** (qalb) = heart that alternates between states vs **فؤاد** (fu'aad) = heart burning with intensity
- **جاء** (ja'a) = came with difficulty vs **أتى** (ata) = came with ease

---

## What LV1 Has Built

### The Genome, Stable Data Foundation

| Asset | Count | What It Contains |
|-------|-------|-----------------|
| BAB files | 30 | 12,333 genome entries grouped by binary root |
| Muajam roots | 1,938 | Trilateral roots with binary nuclei, axial meanings, Quranic examples |
| Binary roots | 457 documented | Of 784 theoretical combinations |
| Letter meanings | 28 | Semantic axioms per letter |
| Muajam coverage | 68.9% | 1,335 of 1,938 roots matched to Jabal's dictionary |

### The Research Factory, Hypothesis Testing Engine

LV1 contains a computational research factory that tests the theory's claims using AI embeddings (BGE-M3), statistical tests, and controlled experiments.

**12 hypotheses tested, 11 experiments run:**

| Result | Hypotheses | What It Means |
|--------|-----------|---------------|
| **Supported** | H2, H5, H8, H12 | Binary fields are real (>11σ), order matters, position matters, meaning is partially predictable |
| **Weakly supported** | H4 | Metathesis preserves core meaning (small effect) |
| **Weak signal** | H3 | Third letter has some modifier consistency (needs more data) |
| **Not supported** | H6, H7, H11 | Phonetic substitution doesn't preserve meaning, missing roots aren't explained by semantic conflict, unsupervised discovery doesn't find binary structure |
| **Inconclusive** | H1 | Letter-level sound-meaning correlation (N=28 too small) |
| **Partial signal** | H9, H10 | Emphatics not stronger (H9); compositionality is real but not complete (H10) |

**Key finding:** Binary root families are **significantly more semantically coherent** than random groupings. Real coherence = 0.540 vs random baseline = 0.518, with >11 sigma separation. This is the strongest quantitative evidence for Jabal's theory to date.

### The Canon Restructure, In Progress

LV1 is being restructured into a **formal semantic canon** with four registries:

| Registry | Purpose | Status |
|----------|---------|--------|
| **Letter Semantics** | 28 letters with glosses from multiple scholars, provenance, confidence | Building |
| **Binary Field** | Binary root → semantic field mapping with coherence scores | Building |
| **Root Composition** | Trilateral root → binary field + third letter specialization | Planned |
| **Quranic Interpretation** | Lemma → conceptual meaning + letter trace + context constraints | Planned |

The architecture is **structure first, content later**: schemas and import pipelines are built now, curated theory content (letter meanings, binary field glosses) will be ingested through a dedicated inbox folder as it's prepared.

---

## Supplementary Scholars, Cross-Linguistic & Comparative Evidence

Beyond the core scholars who feed LV1's letter and root semantics, five additional researchers provide **cross-linguistic validation** and **comparative evidence**:

### Ali Fahmi Khashim, Arabic Roots in World Languages

Khashim demonstrates that Arabic roots survive in European languages through 9 systematic sound laws:

| Arabic Sound | European Equivalent | Example |
|:---:|:---:|:---|
| ف (fa) | P | فاطر → Pater → Father |
| ق (qaf) | C/K/G | ألق → Lux → Light |
| ط (ta) | T | قرطاس → Carta → Card |
| ص (sad) | S | بوص → Passus → Pass |
| ش (shin) | S | شبح → Spectator |
| ح (ha) | K/C/H |, (drops in Akkadian entirely) |
| ع (ayn) | drops or H | يد → Hand |
| غ (ghayn) | G | غلاف → Glove |
| خ (kha) | H/G | مخزن → Magazine |

**LV2 relevance:** These sound laws can be encoded as **phonetic substitution rules** for cross-lingual cognate discovery, supplementing the genome scorer features already promoted from LV1.

### Muhammad Anbar, Dialectical Letter Reversal

Anbar's "Golden Rule": reversing the letter order of any Arabic word reverses its meaning. This is a **testable prediction** that LV1's Research Factory could validate computationally:

- قَرَأَ (gather) ↔ رَقَأَ (cease/dry up)
- غَدَرَ (abandon) ↔ رَدَغَ (stay/adhere)
- سَلِمَ (separate safely) ↔ مَلَسَ (blend/connect)
- عَقَرَ (tear apart) ↔ رَقَعَ (patch/repair)

### Al-Shanawi, Shared Semitic Vocabulary

Al-Shanawi documents **core vocabulary shared across 6 Semitic languages** (Arabic, Akkadian, Hebrew, Aramaic, Ugaritic, Ethiopic): رأس, عين, لسان, سنّ, أخ, ماء, سماء, كلب, بيت, سلام. He confirms that Arabic alone preserves all pharyngeal (ع,غ,ح,خ,هـ,ء) and emphatic (ص,ض,ط,ظ) sounds, all other Semitic languages lost some.

### Dhawq, Pictographic Letter Origins

Dhawq traces 3 Phoenician letters to Arabic pictographic origins: التاء (cross = تابوت = stability), الهاء (praying figure = هدى = guidance), الأليف (calf head = أليف = domesticated). His key claim: the symbol+sound+meaning triple only resolves fully through Arabic.

---

## How LV1 Connects to Other Levels

```
LV0 (Data Core)
  │
  │  2.64M lexemes across 9 languages
  │
  ▼
LV1 (Arabic Genome)
  │
  ├──→ Promotes to LV2: field coherence scores (396),
  │    metathesis pairs (166), positional profiles (28)
  │
  ├──→ LV2 uses these as GenomeScorer features for
  │    cross-lingual cognate discovery
  │
  ├──→ Result: genome improves Semitic cognate ranking
  │    (MRR +0.029 Arabic-Hebrew, +0.109 Arabic-Aramaic)
  │
  └──→ Future: feeds LV3 (theory synthesis) with structured
       evidence cards and interpretation profiles
```

---

## The Scholars Behind LV1

| Scholar | Era | Contribution to LV1 |
|---------|-----|---------------------|
| **Al-Khalil ibn Ahmad** | 786 CE | First Arabic phonetic ordering (makhaarij), permutation system |
| **Ibn Jinni** | 1002 CE | "Greater derivation", all permutations share meaning; sound-meaning correspondence |
| **Ibn Faris** | 1004 CE | One conceptual meaning per root (مقاييس اللغة) |
| **Al-Suyuti** | 1505 CE | Acknowledged phonosemantics is real but not absolute |
| **Al-Aqqad** | 1964 | Positional semantics, same letter means different things in different positions |
| **Jabal** | 2010 | The binary field model, first two consonants define the semantic field (367 fields, 2,300 roots) |
| **Hassan Abbas** | 1998 | Sensory/perceptual letter profiling (23 letters tested on Quran) |
| **Neili** | 2000 | Intentionality principle, language is not arbitrary; physical movement semantics (10 letters) |
| **Asim al-Masri** | 2010 | Completed all 28 letters; dialectical analysis of letter names |
| **Samarrai** | 2003+ | No synonymy in Quran, every word is uniquely chosen; contrastive analysis |
| **Anbar** | Contemporary | "Golden Rule" of letter reversal, reversing letter order reverses meaning |
| **Khashim** | Contemporary | 9 sound laws mapping Arabic roots to European cognates (فاطر→Father, ألق→Light) |
| **Dhawq** | Contemporary | Pictographic origins of Phoenician letters traced to Arabic roots |
| **Al-Shanawi** | 2017 | Shared core vocabulary across 6 Semitic languages; Arabic preserves all pharyngeals |

---

## The Key Insight

Arabic is not just a language with roots. It is a language where **the roots themselves are composed of meaningful atoms**, letters and binary nuclei, that combine according to discoverable rules. LV1's job is to make those rules **computational, testable, and machine-readable**.

The Research Factory has already confirmed:
- Binary fields are real (H2, >11σ)
- Position matters (H8, 24/28 letters)
- Order matters (H5, supported)
- Meaning is partially predictable from components (H12, supported)

The Canon Restructure will turn these findings into **structured registries** that other systems (LV2 for cross-lingual discovery, LV3 for theory synthesis, QCA for Quranic analysis) can consume programmatically.

---

## Numbers at a Glance

| Metric | Value |
|--------|-------|
| Arabic letters with semantic values | 28 |
| Binary roots documented | 457 / 784 theoretical |
| Binary semantic fields (Jabal) | 367 |
| Trilateral roots with axial meanings | 1,938 |
| Genome entries | 12,333 |
| Hypotheses tested | 12 |
| Experiments run | 11 |
| Hypotheses supported | 4 (H2, H5, H8, H12) |
| Binary metathesis pairs | 166 |
| Promoted features to LV2 | 3 assets (coherence, metathesis, positional) |
| Supplementary scholars integrated | 5 (Anbar, Khashim, Dhawq, Al-Shanawi, Al-Alayili via Al-Shanawi) |
| Tests passing | 275 |

---

## Technical Stack

- **Python 3.11+**, managed with `uv`
- **BGE-M3** for multilingual semantic embeddings (1024-dim)
- **ByT5** for character-level form embeddings
- **NumPy/SciPy** for statistical tests
- **Frozen dataclasses** for type-safe data models
- **JSONL** for all data serialization
- **pytest** for 275 tests

---

*LV1, The Arabic Linguistic Genome*
*Part of the Juthoor Linguistic Genealogy project*
*Yassine Temessek, 2026*
