# Juthoor · The Arabic Tongue

🌐 **Live site:** [**arabicjuthoor.com**](https://arabicjuthoor.com/)

🖥️ **Local dashboard:** [`index.html`](index.html) — a single-page overview of the methodology, the letter-face registry (every letter as a full articulation event with its witnessed faces), the full nucleus catalog, the eleven native composition modes (plus the LOANWORD label), the cross-tongue windows, and the scholarly foundation.

🚀 **Deploying:** see [`DEPLOYMENT.md`](DEPLOYMENT.md) for the GitHub Pages + Cloudflare DNS setup.

**Author:** Yassine Temessek
**Conducted under:** **Temessek for Research, Publishing & Training** · [coranisyours.com](https://coranisyours.com) · [arabicjuthoor.com](https://arabicjuthoor.com/)

---

## What this study is

In most languages, letters are arbitrary sound-tokens; meaning emerges only when they are assembled into words. Arabic does not work that way. Each of its 28 letters carries a physical-semantic charge, drawn from the gesture of pronunciation itself, and the meaning of every word is built compositionally from the letters' meanings.

This is an empirical study of that meaning-composition system. It rests on twelve centuries of Arabic linguistic scholarship — from al-Khalil ibn Ahmad and Ibn Jinni through the classical lexicographers — and on the modern lexicographic foundation laid by Dr. Muhammad Hassan Jabal and the parallel sensory-profile work of Hassan Abbas. It extends that foundation with three structural findings on the internal architecture of Arabic: a unified 28-letter charge table matured into the canonical letter-face registry (each letter a full-phased articulation event whose faces are witnessed by Jabal's own nucleus families, under the face-selection law: the nucleus partner selects the phase, and the third radical re-selects), and eleven native composition modes for trilateral roots (with a twelfth label, LOANWORD, reserved for non-native borrowings — 1 case in 2,285). These three results then led to a fourth, related but standing on its own: a four-bar verification rubric for cross-linguistic Quranic cognates, anchored by Dr. Ali Fahmi Khshim's nine sound-substitution laws.

## Layout

```
.
├── index.html                         ← 🌐 the unified dashboard (open in any browser)
├── README.md                          ← this file
├── 01-theory/                         ← classical Arabic linguistic survey
├── 02-architecture/                   ← methodology and findings papers
├── 03-scholar-extracts/               ← reference tables and catalogs
├── 04-cross-linguistic/               ← cognate corpus
├── 05-audits/                         ← empirical record
├── data/                              ← canonical JSON exports (registry, three levels, collation record)
├── scripts/                           ← exporter + permanent purity checker
├── _inbox/                            ← cross-session/project protocol messages
├── Data raw/                          ← primary sources (kept out of git)
└── Resources/                         ← raw dictionaries and corpora fuel (kept out of git; indexed by its README)
```

## File map

### `01-theory/` — Arabic linguistic foundation

| File | Description |
|------|-------------|
| [classical-survey-ar.md](01-theory/classical-survey-ar.md) | A multi-chapter Arabic survey of the classical linguistic tradition — al-Khalil ibn Ahmad al-Farahidi (*Kitab al-Ayn*), Ibn Jinni (*الخصائص*), through the dictionary tradition. The deeper anchor for the form-meaning correspondence. |

### `02-architecture/` — methodology and findings papers

| File | Description |
|------|-------------|
| [our-contributions-and-roadmap.md](02-architecture/our-contributions-and-roadmap.md) | **The shareable position paper.** What the study contributes, the foundations it rests on, the current state, and the next chapters. |
| [lv2-operative-grammar.md](02-architecture/lv2-operative-grammar.md) | **The eleven native composition modes for trilateral roots (+ LOANWORD label).** Full classification coverage across 2,285 roots: 2,284 native-mode calls plus one separately published LOANWORD label. |
| [lv1-architecture.md](02-architecture/lv1-architecture.md) | The architectural specification: the four-layer scope (Letter atoms → binary nuclei → trilateral roots → cross-linguistic projection) and the scoring framework. |

### `03-scholar-extracts/` — reference tables and catalogs

| File | Description |
|------|-------------|
| [canonical-letter-registry.md](03-scholar-extracts/canonical-letter-registry.md) | **The canonical letter-face registry v1.0 (frozen, print-collated).** Every letter's full articulation event, its witnessed faces with their family ballots, and the court verdicts. Machine form: `data/juthoor-canonical-registry.json`; per-letter courts in `letter-dossiers/`. |
| [jabal-phonetic-footnotes.md](03-scholar-extracts/jabal-phonetic-footnotes.md) | Jabal's own phonetic footnotes harvested from the full print (852 statements): an independent convergence witness for the registry. |
| [consensus-letter-charges.md](03-scholar-extracts/consensus-letter-charges.md) | The historical unified charge table (legacy layer, kept as provenance; superseded as canon by the registry above). |
| [jabal-nuclei-extended.md](03-scholar-extracts/jabal-nuclei-extended.md) | **The operational 455-nucleus catalog** with per-nucleus reading and source evidence: Jabal's historical 453-table, the dated source-repair layer, and the author-adopted non-Jabal nucleus وب kept distinct by provenance. |
| [jabal-nuclei-tc-anchored.md](03-scholar-extracts/jabal-nuclei-tc-anchored.md) | The 258 nuclei whose readings are anchored to published Quranic verse-readings. |
| [abbas-letter-classification.md](03-scholar-extracts/abbas-letter-classification.md) | Hassan Abbas's dual-axis classification (sensory category × articulatory mechanism). |
| `jabal-letters.html` | Per-letter empirical evidence from the earlier charge-table era (historical layer). |

### `04-cross-linguistic/` — cognate corpus

| File | Description |
|------|-------------|
| [tafsir-coran-tier-a-cognates.md](04-cross-linguistic/tafsir-coran-tier-a-cognates.md) | **The four-bar verification rubric** anchored by Dr. Ali Fahmi Khshim's nine sound-substitution laws, with Tier-A Quran-anchored cognate windows (kufu' ↔ copy, salām ↔ shalom, rabb ↔ rabbi, qul ↔ call...). Windows on a pervasive rate measured against chance, not a counted special list. |
| [beyond-the-word-examples.md](04-cross-linguistic/beyond-the-word-examples.md) | 17 popular Arabic↔English cognate cases retained for reference. |

| [exploration-charter.md](04-cross-linguistic/exploration-charter.md) | **The cross-tongue exploration charter**: three connection stages by branch depth, the per-language lessons, the uniform reading card, and the twin prohibitions (no fabrication, no self-sabotage). New language files open in `readings/`. |

### `05-audits/` — empirical record

The empirical evidence for every structural claim in the framework: the full nucleus test, the twelve-mode coverage report, the reversibility evaluation, and the data-quality verifications. The detailed letter-by-letter editorial decisions also live here. Researchers consulting the underlying evidence should start here.

### `Data raw/` — primary sources (frozen)

| Subfolder | Contents | Role |
|---|---|---|
| `Muajam Ishtiqaqi/` | `المعجم_الاشتقاقي_Juthoor_v2.xlsx` (2,300 unique roots, the full binary-nuclei catalog, 28 letters) and 26 per-letter باب tables | Jabal's empirical dataset — the canonical ground truth. |
| `Languistic theories/` | The modern Arabic letter-semantics field on which the study draws (primary: Jabal and Abbas; cross-linguistic: Khshim) and the archival material around it | Primary theoretical sources. |
| `facebook_posts_beyondthename/` and supporting files | The Beyond-the-Word source corpus | Raw material for the cross-linguistic layer. |

### Computational side of the project

The companion `Juthoor-Linguistic-Genealogy/` workspace is the computational side of the same project: a Python pipeline that implements the LV0–LV3 architecture, runs the eleven-native-mode trilateral reading, and produces the audits behind the claims on this page. Statistical and cross-linguistic expansion is continuously running there.

## Reading order

If you have time for **one file**, read [`02-architecture/our-contributions-and-roadmap.md`](02-architecture/our-contributions-and-roadmap.md). It is the shareable position paper.

If you have time for **two**, add [`03-scholar-extracts/canonical-letter-registry.md`](03-scholar-extracts/canonical-letter-registry.md), the frozen letter-face registry that everything composes from.

For the working constitution (how distant branches are read) see [`02-architecture/deep-decomposition-method.md`](02-architecture/deep-decomposition-method.md), and for continuing the language journey see the [exploration charter](04-cross-linguistic/exploration-charter.md).

For the **full picture**, read in folder order: 01 → 02 → 03 → 04.

## Conventions

- **Folder numbering** (`01-`, `02-`, …) reflects the natural reading order.
- **Filename language suffix:** `*-ar.md` means the document is written in Arabic; otherwise English.
- **Lowercase, hyphenated filenames** for shell-safe paths.
- **One canonical document per topic.** Where a derived companion exists, it cross-links to the canonical and declares its lower priority.

## Citation

> Temessek, Y. *The Arabic Tongue: Nature, Genome, Application.* Temessek for Research, Publishing & Training. [coranisyours.com](https://coranisyours.com) · [arabicjuthoor.com](https://arabicjuthoor.com/)
