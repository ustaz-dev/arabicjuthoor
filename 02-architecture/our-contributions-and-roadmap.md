# Juthoor: Contributions to Arabic Letter Semantics & the Open Roadmap

**Project:** The Arabic Tongue: Nature, Genome, Application
**Author:** Yassine Temessek
**Conducted under:** Temessek for Research, Publishing & Training · [coranisyours.com](https://coranisyours.com) · [arabicjuthoor.com](https://arabicjuthoor.com/)

---

## Abstract

This study builds on twelve centuries of Arabic linguistic scholarship, from al-Khalil ibn Ahmad al-Farahidi (8th c., *Kitab al-Ayn*) and Ibn Jinni's *إمساس الألفاظ أشباه المعاني* doctrine in *al-Khasais* (11th c.) through the classical lexicographers and grammarians, and on the modern lexicographic foundation laid by Dr. Muhammad Hassan Jabal (*المعجم الاشتقاقيّ المُؤَصَّل*) and the parallel sensory-profile work of Hassan Abbas (*خصائص الحروف العربيّة ومعانيها*, Arab Writers Union, 1998). It extends that foundation with new structural findings:

**Three structural findings on the internal architecture of Arabic:**

(a) the **general dual-face rule** for letter charges, tested by induction across all 453 binary nuclei in Jabal's corpus, a structural property earlier scholarship had only suspected for a handful of letters;

(b) **eleven native composition modes for trilateral roots** (with a twelfth label, LOANWORD, reserved for non-native borrowings): the binary nucleus operates on the third letter, taking its charge as material, in one of these closed modes. The 2,285 trilaterals fit at 100% native composition, closing the bottom-up genealogy from letter to root. The eleven modes remain open to refinement;

(c) a **unified 28-letter charge table** with bilingual phonetic notes and English glosses, and a **complete 453-nucleus catalog** with Quran-anchored evidence.

**A fourth result, related but standing on its own**, emerged from those three when we asked whether the articulation-meaning structure inside Arabic leaves traces in other language families:

(d) the **four-bar verification rubric** for cross-linguistic Quranic cognates, anchored by Dr. Ali Fahmi Khshim's nine sound-substitution laws, with eight confirmed Tier-A pairs.

Alongside these, an explicit **letter → nucleus → root → word reading protocol** with a stability discipline.

The document also identifies the chapters of the work that are currently in progress on the computational side of the project, and those that are next to be opened publicly. Conducted under **Temessek for Research, Publishing & Training**.

---

## §1. Context, where this study sits

### 1.1 The question this study asks

When a word means what it means, is the bond between its sounds and its meaning entirely conventional, or is there some structure to it? This is an old question in Western philosophy. Plato put it on record in the *Cratylus* dialogue some twenty-four centuries ago, where two interlocutors argue whether names are correct by nature (*physei*) or by convention (*nomō*). The question never fully closed. At the beginning of the twentieth century **Ferdinand de Saussure** settled it for modern linguistics with the principle of arbitrariness: the phoneme /m/ in *mother* carries no inherent connection to motherhood, and the signifier and the signified are linked only by convention. The thesis became foundational for Saussurean structuralism.

The classical Arabic linguistic tradition, twelve centuries before Saussure, gave the opposite answer explicitly. **Ibn Jinni** in *al-Khasais* (11th c. CE) framed it under the doctrine **«إمساس الألفاظ أشباه المعاني»**: letters touch upon resemblances of meanings; the letter carries something of its meaning through its physical form. **Al-Khalil ibn Ahmad** al-Farahidi (8th c.) ordered the entire dictionary by place of articulation (مَخرَج), starting from the deep throat and moving forward to the lips, on the principle that the physical gesture of pronunciation is itself the wellspring of meaning. **Ibn Faris** in *Maqayis al-Lugha* (10th c.) assigned a single core semantic value to each Arabic root.

This study takes the classical Arabic position seriously, tests it empirically against the modern lexicographic foundation (Jabal's lexicon), and reports what the data shows.

### 1.2 Three traditions converging in this work

Three traditions converge here. None is rejected; each contributes a layer:

| Tradition | Contribution |
|---|---|
| **The classical Arabic phonosemantic tradition** (al-Khalil, Ibn Jinni, Ibn Faris, the lexicographers) | Supplies the framework: letter-meaning correspondence through place of articulation. The most developed theory of sound-meaning correspondence ever produced in any language. |
| **Saussurean structuralism** (Saussure and after) | Supplies the toolkit and the units: signifier and signified, phonemes (الصواتم) and morphemes (اللفاظم), and the arbitrariness thesis as a hypothesis to test. |
| **The phonosemantic / sound-symbolism literature** (Sapir, Jakobson, Jespersen, Tsur, Hinton, Magnus, John Ohala's frequency-code work, Lakoff and the embodied-cognition turn, Asifa Majid's sensory linguistics across language families) | Supplies the cross-linguistic horizon: documented patterns of sound-symbolic correspondence (*bouba/kiki*, *mil/mal* size correspondence, voicing and magnitude). Suggestive but scattered, never reaching the systematic scale Arabic permits. |

This study sits at the intersection of the three: the classical Arabic tradition supplies the framework, the phonosemantic literature supplies the cross-linguistic horizon, and the Saussurean toolkit supplies the units at which the test runs (**phoneme → binary nucleus → root → word**).

### 1.3 The Arabic tradition on letter semantics

The layer of Arabic letter semantics sits below the layer of grammar and before the layer of exegesis. It is not a modern specialty; it is a field that has stretched across centuries. The foundational intuition is the link between a letter's form and its meaning through its place of articulation. It is present in al-Khalil ibn Ahmad al-Farahidi's *Kitab al-Ayn* (8th c., the founder of Arabic linguistics) and made explicit in Ibn Jinni's *al-Khasais* (11th c., the chapter on *إمساس الألفاظ أشباه المعاني*, the correspondence of form to meaning). It continued through the classical lexicographers and grammarians, manifest in their close attention to places of articulation (مَخارج) and consonant qualities (صفات) as the wellspring of meaning. The full survey is in [`../01-theory/classical-survey-ar.md`](../01-theory/classical-survey-ar.md).

In the modern era, the lexicographic foundation for this field rests on two principal works:

| Source | Contribution | Scale |
|---|---|---|
| **Dr. Muhammad Hassan Jabal** · *المعجم الاشتقاقيّ المُؤَصَّل* | A quantitative lexicographic induction with a compositional model (letter → nucleus → root) | 28 letters, 453 binary nuclei, 2,300 unique roots, 1,666 Quranic applications |
| **Hassan Abbas** · *خصائص الحروف العربيّة ومعانيها* (Arab Writers Union, 1998) | A sensory-phonetic characterization of the letters, six sensory categories crossed with three evolutionary mechanisms (هيجانيّة / إيمائيّة / إيحائيّة) | 28 letters |

For the cross-linguistic layer, the study rests on the work of **Dr. Ali Fahmi Khshim** (former president of the Libyan Arabic Language Academy, member of the Cairo Arabic Language Academy, PhD in philosophy from Durham University 1971, author of *رِحلة الكلمات*), who established nine sound-substitution laws between Arabic and other language families. This work does not provide per-letter charges but rather the comparative-phonetic mechanisms between languages, and it lives in the cross-linguistic layer (`04-cross-linguistic/`).

### 1.4 Where this study sits

This study is not a competing alternative to that tradition; it is a **structural refinement and extension**. It takes:

- From the **classical tradition** (al-Khalil, Ibn Jinni, the lexicographers): the foundational intuition of form-meaning correspondence through articulation.
- From **Jabal**: the complete lexicographic dataset and his compositional model (letter → binary nucleus → root).
- From **Abbas**: the sensory categories and the phonetic-evolutionary axis for letters.
- From **Khshim**: the substitution laws for the cross-linguistic layer.

To that combined foundation, the study adds new structural findings, detailed in §2 below.

**Methodological commitment:** the study did not take the foundation's results as given. We conducted our own readings independently, reading by reading, letter by letter, nucleus by nucleus, over a full year of systematic examination, cross-checked against the evidence in the classical and modern sources. Jabal's lexicon was the empirical backbone, but we did not transcribe his readings; we compared our independent readings against his, converging on much that he had already established and extending where his framework did not yet reach. The detailed record of these tests and editorial decisions lives in the [`../05-audits/`](../05-audits/) folder.

---

## §2. Our contributions in the letter layer

### 2.1 A single unified 28-letter charge table

The prior tradition presented multiple readings per letter. This study **chose a single ruling charge per letter** after weighing the readings present in the literature. The full table is in [`../03-scholar-extracts/consensus-letter-charges.md`](../03-scholar-extracts/consensus-letter-charges.md).

The unified table is neither a translation nor a citation; it is an **editorial judgment** open to critique and revision, but one and not many.

### 2.2 A concise English gloss per letter

Each row in the unified table carries:

- The Arabic charge
- A phonetic note
- A concise English gloss

Examples:

- **ء/أ** → *sharp affirmation, beginning*
- **ر** → *repetition, running, flow*
- **ع** → *depth-grip, intense from the throat*
- **ج** → *gathering in a space, surfacing*

This builds the bridge between the internal Arabic field and the non-Arabic reader, a necessary condition for any cross-linguistic academic expansion.

### 2.3 The general dual-face rule across all 28 letters

The dual-face semantic property is not a special characteristic of a few letters; it is a **general property** of the Arabic phonetic-semantic system. It was tested by induction across all 453 binary nuclei in Jabal's lexicon (full report in [`../03-scholar-extracts/jabal-letters.html`](../03-scholar-extracts/jabal-letters.html)).

**Every one of the 28 letters carries two semantic faces** of one place of articulation, and the third letter in the trilateral root determines which face is active.

Examples:

> **ب** · Primary face: «اتّصال + تَمَسُّك» (attachment that holds and reveals, like a doorway that gathers and shows what is behind it). Other face: «انطِباق + إغلاق» (sealed closure).
> **ن** · Primary face: «انبِعاث رَنينيّ» (outward resonant emission). Other face: «رَنينٌ مَحبوس» (cavity-held resonance, activated in ثن, تن, طن).
> **ه** · Primary face: «همس + تَنَفُّس» (soft passing presence). Other face: «نَفَسٌ يَحمل ويَتَلاشى» (breath that carries off and dissipates).
> **ج** · Primary face: «تَجَمُّع في حَيِّز» (gathering in a space). Other face: «بُروز من حَيِّز» (surfacing out of a space).

**Methodological discipline:** a letter's charge is not a point but a **region with two known faces**. The final rule: use the primary face by default; do not use the other face except when the third letter in the nucleus activates it.

### 2.4 An 18-nucleus working set for practical use

Jabal's lexicon has **453 binary nuclei** (out of 28² = 784 mathematical possibilities, see the next subsection for the scope statement). The volume prevents practical handling of 453 nuclei in the analysis of any one verse. We selected **18 high-frequency, Quran-anchored nuclei**:

ال، بر، بد، حم، حق، رب، رح، سل، سم، عل، فر، فط، قر، كل، ملك، نج، هد، وص.

Each has its primary meaning with three to four examples. Example:

> **حم** = *living containment, warm enclosure*
> Examples: حَمَى, حَمَلَ, حَمِدَ, رَحِم
> Nucleus: warm life (ح) + gathering and adhesion (م) → a warm containment.

This is a **human-scale working set** that can be used in daily reading without drowning.

#### Honest scope: why 453, not 784?

A reader who sees "100% native fit" and "453 binary nuclei" will rightly ask: what about the rest? With 28 letters, there are **28² = 784 mathematical possibilities** for an L1·L2 pair. Our catalog has 453. Where did the other 331 go? They are **filtered, not missing**:

| Filter | Pairs removed | Linguistic reason |
|---|:---:|---|
| **alif-initial** (ا as L1) | 28 | ا is a vowel marker, not a consonant; a root cannot begin with it in Arabic |
| **identical XX** (e.g., بب, دد, …) | 25 | The Obligatory Contour Principle bans identical consonants at the root start |
| **same-articulator class** | 107 | Soft OCP, tongue-tip-twice (e.g., تد), lips-twice (e.g., بم), and similar adjacencies are dispreferred |
| **Genuine lexical gaps** | **155** | Phonologically allowed by Arabic but unused, pairs the language could form but doesn't |

That is: **160 pairs (58%)** of the 277 unattested pairs are blocked by known phonological constraints (28 alif-initial · 25 identical-XX · 107 same-articulator-class). Only **117 pairs (15% of all 784, 42% of the unattested)** are true lexical gaps — pairs Arabic was capable of forming but did not. (An earlier draft published 155 from an L1-by-L1 enumeration that double-counted pairs falling into two categories.)

**The honest claim:** every trilateral root that *exists* in Arabic gets a coherent operative reading. We did not claim every theoretical XYZ would, and we closed the claim at the actual count, not the mathematical one. The 155 gaps are the natural **held-out test set** for the next question: can the model become generative, predicting the mode a hypothetical speaker would choose if she coined one of those pairs?

### 2.5 An explicit five-step reading protocol

The composition model is implicit in Jabal but he never set it down as a precise recipe. We produced the recipe:

1. **Name the letters with their charges** · e.g., ق (قطع + إحكام) + ر (تكرار + جريان).
2. **Form the nucleus** from the first two letters · قر = a precision that repeats.
3. **Add the remaining letter(s) of the root** · + أ (تأكيد + قوّة).
4. **State the literal root meaning** · القرآن = a firm settling that repeats and is affirmed.
5. **Connect to contextual usage** in one sentence.

This is a **teachable model**, a new researcher can be trained on it in two hours.

### 2.6 Stability discipline

We declared that the unified table is designed **to stabilize, not oscillate**. The faces recorded above are the expected drift-window; beyond that drift, a reading is in **tension with itself** and needs review against the original sources in `Data raw/Languistic theories/`.

This is **a quality clause that is testable**, turning the table from a proposal into a framework that can be tested and refuted. Any reading outside the declared face-window is a **new hypothesis** that needs grounding in the source material, not a free amendment.

### 2.7 Seven worked end-to-end examples

We applied the framework to seven central Quranic roots, step by step:

| Root | Nucleus | Literal meaning | Usage meaning |
|---|---|---|---|
| ق-ر-أ | قر | a firm settling that repeats and is affirmed | gathering of meanings, the Book |
| ف-ط-ر | فط | an opening that spreads | الفطرة, primordial creation |
| ح-م-د | حم | warm containment that settles | praise that holds and precedes any benefit |
| ر-ب-ب | رب | flowing attachment, holding-and-multiplying | the holder of what was entrusted |
| ع-ل-م | عل | a depth-grip that extends | a fixed grasp, a sign |
| ن-ج-و | نج | inner resonance gathering in a place | escape, a star |
| س-و-م | سو | a flowing-binding-gathering | branding, imposing a price |

These are **validation tests** for the framework. Each reading is open to critique.

---

## §3. Architectural choices

### 3.1 The phonetic-kinetic entry point as the foundation

The study rests on the **place of articulation and the movement of the mouth** as the physical wellspring of meaning. This entry point is empirically testable and supported by the classical tradition in phonetics (مَخارج, صفات). Metaphysical or cosmological alternatives for the charges are weighed against simpler phonetic alternatives whenever the latter are available.

### 3.2 Separating the cross-linguistic layer

Dr. Ali Fahmi Khshim's sound-substitution laws represent **cross-linguistic comparison mechanisms**, not letter charges. We placed this work in the dedicated cross-linguistic layer [`../04-cross-linguistic/`](../04-cross-linguistic/), preserving the purity of the letter layer from cross-comparative contamination.

### 3.3 A quiet stance against "scientific miraculousness" claims

There is no claim in the framework that a letter's charge "matches modern science" or anything of the sort. The framework claims the testability of Arabic through a strictly internal linguistic method, and does not get involved in such slogans.

### 3.4 Single-row editorial decisions

In each row of the 28-letter table, a reading had to be weighed against another. The prevailing line in those decisions: **we weight physical-articulatory charges over metaphysical-cosmological ones**. When the choice is between an abstract verbal reading and a simpler reading supported by the place of articulation, we choose the latter. The full record of row-by-row editorial decisions, with the evidence behind each weighting, is in [`../05-audits/`](../05-audits/).

---

## §4. Contributions in other layers

### 4.1 The four-bar verification rubric for cross-linguistic cognates

File: [`../04-cross-linguistic/tafsir-coran-tier-a-cognates.md`](../04-cross-linguistic/tafsir-coran-tier-a-cognates.md).

Four conditions must be met for a pair (Arabic ↔ other language) to be promoted to Tier A:

1. **Consonant skeleton match** (using Khshim's sound-substitution laws: K↔Q, F↔P, ج↔K, ض↔D, …).
2. **Nucleus identity**, not merely sound similarity.
3. **Modern reader-recognition** of the corresponding word (no rare technical Latin).
4. **Dual-family confirmation**, support from Semitic (Hebrew, Aramaic, …) AND support from Indo-European (Latin, Greek, Germanic, …).

**Eight pairs confirmed at Tier A:**

| Root | Cognate | Skeleton | Shared nucleus |
|---|---|---|---|
| ك-ف-ء | copy / copie / כפל (Heb) | K-F | the second-instance that lines up against the first |
| س-ل-م | shalom / shalmā (Aram) | S-L-M | bound completeness, peace-as-wholeness |
| ر-ب-ب | rabbi / rav (Heb) | R-B | the expansive holder, master-by-nurture |
| ج-ن-ن | genie / genus | G-N | born-from-a-hidden-source, kin-bearing concealment |
| ك-ل-م | claim / clamor (Lat. *clamare*) | K-L-M | utter-with-intent, the spoken claim that lands |
| ق-و-ل | call (PIE *kel-) | K/Q-L | the summon-uttered, the audible-reach |
| ش-ر-ب | sorb / absorb / syrup | S-R-B | the take-in of fluid, absorbing-flow |
| ج-م-ع | Gemini / gemellus | G-M / J-M | gathered-into-pair, together-as-one |

### 4.2 Phenomenological reframe

**The study does not claim historical borrowing** between Arabic and the other languages. It claims **phenomenological convergence**: the human mouth shaped the same form for the same reality across language families. Note the asymmetry of evidence: the Arabic root ك-ف-أ is an **attested word** in Quranic and classical Arabic (Q 112:4); the proposed Indo-European ancestor for *copy* (PIE \*op-) is a **linguistic reconstruction**, a hypothetical proto-form. Even granting the reconstruction, the reading stands: an attested Semitic word and a reconstructed Indo-European etymon both converge on the same sonic-semantic nucleus. The reading is not a competing etymology; it is a convergence claim about how the human mouth shapes meaning.

### 4.3 Strict repo structure

The project is organized in numbered layers (`01-theory/` … `05-audits/` + `Data raw/`), with specific naming conventions and explicit semantics for what "complete" / "archived" / "open" mean. This discipline is itself a methodological contribution, it makes the project **collaborable and extensible** without chaos.

### 4.4 Audits and reconciliations

The full audit record of the study is in the [`../05-audits/`](../05-audits/) folder. Disciplined auditing is a recurring methodological contribution.

### 4.5 The computational side of the project

Juthoor is a project with two sides: this vault (the research-editorial side) and the computational side in `Juthoor-Linguistic-Genealogy/`. The computational side is a Python pipeline that implements the LV0–LV3 architecture, runs the twelve-mode trilateral reading, and produces the audits behind the claims in this document. Statistical and cross-linguistic expansion is continuously running on that side of the project.

---

## §5. Differences from external references

| Reference | How the study treats it |
|---|---|
| **The classical tradition** (al-Khalil, Ibn Jinni, al-Zamakhshari, …) | The foundational intuition. The study rests on it and builds upon it. |
| **Jabal** | The complete empirical dataset and the field's backbone. The study adopts his compositional model (letter → nucleus → root), then conducts its own readings independently; the results converge with Jabal across much of what he established and extend beyond his framework where the data allows. |
| **Abbas** | The sensory axis. The study absorbs it and tests it against the full catalog. |
| **Khshim** | The substitution laws for the cross-linguistic layer. Architecturally separated in `04-cross-linguistic/`; does not enter the letter layer. |
| **The classical exegetes** (al-Tabari, al-Razi, al-Zamakhshari, …) | Detailed exegesis at a higher layer. No conflict, the study's scope is prior to their interpretive scope. |
| **The classical grammarians** (Sibawayh, Ibn Malik, …) | Sentence-level grammar at a higher layer. The study's scope (sub-trilateral) is below grammar, a layering complement, not a contention. |

**The full detail of the editorial decisions**, which charge was chosen and why, which readings were weighted against which alternative, is in the [`../05-audits/`](../05-audits/) folder.

---

## §6. Why this matters

What the study delivers serves five domains at once:

### 6.1 For Arabic and Quranic studies

It gives the field a quantitative, falsifiable framework where there was only intuition. The 28-letter charges are tested against the 453 binary nuclei in Jabal's lexicon; the eleven native composition modes (with a LOANWORD label catching the rare non-native root) are tested against 2,285 trilateral roots. Verse-level Quranic readings become grounded in the science of articulation (مَخارج، صفات), not in the interpretive tradition alone. A reader who knows the charges can read a verse the way a chemist reads a formula, by composition.

### 6.2 For general linguistics

It provides the first systematic, large-scale empirical test of Saussure's arbitrariness thesis on a language whose morphology preserves a transparent root structure. If the dual-face rule holds for every Arabic letter across all 453 nuclei, the arbitrariness thesis is in question, at least for Arabic, and perhaps for any language with a comparable architecture. This does not refute Saussure; it opens a new field under his name: the portion of language where the sign is articulatorily supported, not arbitrary.

### 6.3 For comparative linguistics

A disciplined four-bar verification rubric for cross-linguistic cognates, anchored by Khshim's nine sound-substitution laws, with eight Quran-anchored Tier-A pairs (kufu' ↔ copy, salām ↔ shalom, rabb ↔ rabbi, jinn ↔ genie, kalām ↔ claim, qul ↔ call, sharb ↔ sorb, jam' ↔ Gemini) demonstrating the method in practice. The rubric distinguishes genuine cross-linguistic resonance from surface accident, the central methodological problem of historical-comparative work.

### 6.4 For computational linguistics and AI

It opens the door to **root-level meaning composition** that pure embedding models cannot reach. Where a neural language model learns an opaque mapping from token to vector, this framework offers a **transparent compositional algebra**: the binary nucleus operates on the third letter, taking its charge as material, in one of eleven native composition modes (with a LOANWORD label catching the rare non-native root). Language, in this view, is **acoustic mathematics and semantic algorithms**, and the algebra is now explicit, executable, testable. This is the side of the project that lives in the computational counterpart, with continuous expansion to new language families.

### 6.5 For the classical Arabic tradition itself

The study restores standing to what al-Khalil, Ibn Jinni, and Ibn Faris began. What was a venerable intuition at the hands of the classical scholars is now subject to modern quantitative test. This is not a break with the tradition; it is a twelve-century continuity with new tools.

---

## §7. Where the study stands, and what is next

### 7.1 Settled

- **Unified 28-letter table** with the dual-face rule, tested by induction across all 453 binary nuclei in Jabal's lexicon.
- **The full nucleus catalog** (453 nuclei), with a per-nucleus reading, source-anchored where available and compositionally graded otherwise.
- **Eleven native composition modes for trilateral roots** (plus a LOANWORD label for non-native borrowings) reading 2,285 roots at 100% native fit.
- **The four-bar cross-linguistic verification rubric** with 11 Tier-A Quran-anchored pairs (8 original + 3 promoted via the loanword audit: قرطاس ↔ chart, قميص ↔ chemise, إنجيل ↔ evangel).
- **Honest statement of scope**: of 784 mathematical pairs, 507 are attested as L1+L2 in some trilateral root (453 are catalogued as standalone nuclei). Of the 277 unattested: 160 phonotactically blocked + 117 lexical gaps. Math: 507+160+117=784 ✓.
- **Jawfī treatment** of ا, و, ي: resolved by establishing active charges for all three and including them in the unified table.
- **Dialectical-contradiction check** formalized as a second-pass verification on letter charges.

### 7.2 In progress

- **Statistical predictive testing** of letter charges against competing charge sets, running on the computational side of the project, with continuous expansion across new language families.
- **Tier-B cross-linguistic expansion**, 900+ Arabic↔Greek/Latin candidate cognates discovered and under refinement.

### 7.3 Next chapters

- **Publish an English-language academic paper** (8–12 pages) presenting the unified table, the dual-face rule, the eleven native composition modes (plus the LOANWORD label), and several worked examples.
- **Build a public lookup tool** (CLI or web) that takes an Arabic word and returns its letter → nucleus → root reading.
- **Testing against non-Quranic corpora** (Jahili poetry, modern MSA) to bound the reach beyond Quranic vocabulary.

---

## §8. How to contribute

For collaborators wanting to work on any item in §7:

1. **Read the architecture document:** [`lv1-architecture.md`](lv1-architecture.md) (in this folder).
2. **Study the unified table:** [`../03-scholar-extracts/consensus-letter-charges.md`](../03-scholar-extracts/consensus-letter-charges.md).
3. **Consult the primary sources** in `../Data raw/` to the extent needed for your chosen item.
4. **Work in your layer** following the naming conventions in the root README.

For feedback, citation requests, or collaboration, use the contact form at [arabicjuthoor.com](https://arabicjuthoor.com/).

---

## §9. Summary

This study rests on twelve centuries of Arabic linguistic scholarship, from al-Khalil ibn Ahmad and Ibn Jinni through the classical lexicographers, and from the modern lexicographic foundation laid by Jabal and Abbas, with Khshim's sound-substitution laws for the cross-linguistic layer, and adds new structural findings: **the general dual-face rule** for the 28 letters, tested by induction across 453 binary nuclei; **eleven native composition modes** for trilateral roots (with a LOANWORD label for non-native roots), reading 2,285 roots at 100% native fit; **the four-bar verification rubric** for Quran-anchored cross-linguistic cognates with 8 confirmed pairs; and **a complete catalog** of the binary nuclei with evidence from the published text. The framework rests on Jabal's lexicographic corpus and on a consistent preference for phonetic-physical readings. The computational counterpart in `Juthoor-Linguistic-Genealogy/` carries out the statistical and cross-linguistic expansion continuously.

---

**End of document. For feedback or collaboration, use the contact form at [arabicjuthoor.com](https://arabicjuthoor.com/).**
