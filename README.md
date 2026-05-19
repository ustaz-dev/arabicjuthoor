# Juthoor · The Arabic Tongue

🌐 **Live site:** [**arabicjuthoor.com**](https://arabicjuthoor.com/)

🖥️ **Local dashboard:** [`index.html`](index.html) — a single-page overview of the methodology, the 28-letter table, the 18 nuclei, the twelve composition modes, the 8 Tier-A cognates, and the scholarly foundation.

🚀 **Deploying:** see [`DEPLOYMENT.md`](DEPLOYMENT.md) for the GitHub Pages + Cloudflare DNS setup.

*Arabic version: [`README-ar.md`](README-ar.md)*

**Author:** Yassine Temessek
**Conducted under:** **Temessek for Research, Publishing & Training** · [coranisyours.com](https://coranisyours.com) · [arabicjuthoor.com](https://arabicjuthoor.com/)

---

## What this study is

An empirical study of meaning-composition in the Arabic tongue. Rooted in twelve centuries of Arabic linguistic scholarship — from al-Khalil ibn Ahmad and Ibn Jinni through the classical lexicographers — and on the modern lexicographic foundation laid by Dr. Muhammad Hassan Jabal and the parallel sensory-profile work of Hassan Abbas. The study extends that foundation with new structural findings: the general dual-face rule for letter charges, twelve composition modes for trilateral roots, a four-bar verification rubric for cross-linguistic Quranic cognates (anchored by Dr. Ali Fahmi Khshim's sound-substitution laws), and a complete 453-nucleus catalog.

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
└── Data raw/                          ← primary sources (frozen)
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
| [lv2-operative-grammar.md](02-architecture/lv2-operative-grammar.md) | **The twelve composition modes for trilateral roots.** The taxonomy applied to 2,285 roots at 100% native fit. |
| [lv1-architecture.md](02-architecture/lv1-architecture.md) | The architectural specification: the four-layer scope (Letter atoms → binary nuclei → trilateral roots → cross-linguistic projection) and the scoring framework. |

### `03-scholar-extracts/` — reference tables and catalogs

| File | Description |
|------|-------------|
| [consensus-letter-charges.md](03-scholar-extracts/consensus-letter-charges.md) | **The unified 28-letter charge table** with the general dual-face rule and the 18-nucleus working shortlist. |
| [jabal-nuclei-extended.md](03-scholar-extracts/jabal-nuclei-extended.md) | **The full 453-nucleus catalog** with per-nucleus reading and source evidence. |
| [jabal-nuclei-tc-anchored.md](03-scholar-extracts/jabal-nuclei-tc-anchored.md) | The 258 nuclei whose readings are anchored to published Quranic verse-readings. |
| [abbas-letter-classification.md](03-scholar-extracts/abbas-letter-classification.md) | Hassan Abbas's dual-axis classification (sensory category × articulatory mechanism). |
| `jabal-letters.html` | Per-letter empirical evidence for the dual-face rule. |

### `04-cross-linguistic/` — cognate corpus

| File | Description |
|------|-------------|
| [tafsir-coran-tier-a-cognates.md](04-cross-linguistic/tafsir-coran-tier-a-cognates.md) | **The four-bar verification rubric** anchored by Dr. Ali Fahmi Khshim's nine sound-substitution laws, with the 8 Tier-A Quran-anchored cognate pairs (kufu' ↔ copy, salām ↔ shalom, rabb ↔ rabbi, jinn ↔ genie, kalām ↔ claim, qul ↔ call, sharb ↔ sorb, jam' ↔ Gemini). |
| [beyond-the-word-examples.md](04-cross-linguistic/beyond-the-word-examples.md) | 17 popular Arabic↔English cognate cases retained for reference. |

### `05-audits/` — empirical record

The empirical evidence for every structural claim in the framework: the full nucleus test, the twelve-mode coverage report, the reversibility evaluation, and the data-quality verifications. The detailed letter-by-letter editorial decisions also live here. Researchers consulting the underlying evidence should start here.

### `Data raw/` — primary sources (frozen)

| Subfolder | Contents | Role |
|---|---|---|
| `Muajam Ishtiqaqi/` | `المعجم_الاشتقاقي_Juthoor_v2.xlsx` (2,300 unique roots, 453 binary nuclei, 28 letters) and 26 per-letter باب tables | Jabal's empirical dataset — the canonical ground truth. |
| `Languistic theories/` | The modern Arabic letter-semantics field on which the study draws (primary: Jabal and Abbas; cross-linguistic: Khshim) and the archival material around it | Primary theoretical sources. |
| `facebook_posts_beyondthename/` and supporting files | The Beyond-the-Word source corpus | Raw material for the cross-linguistic layer. |

### Computational side of the project

The companion `Juthoor-Linguistic-Genealogy/` workspace is the computational side of the same project: a Python pipeline that implements the LV0–LV3 architecture, runs the twelve-mode trilateral reading, and produces the audits behind the claims on this page. Statistical and cross-linguistic expansion is continuously running there.

## Reading order

If you have time for **one file**, read [`02-architecture/our-contributions-and-roadmap.md`](02-architecture/our-contributions-and-roadmap.md). It is the shareable position paper.

If you have time for **two**, add [`02-architecture/lv2-operative-grammar.md`](02-architecture/lv2-operative-grammar.md) for the twelve composition modes.

For the **full picture**, read in folder order: 01 → 02 → 03 → 04.

## Conventions

- **Folder numbering** (`01-`, `02-`, …) reflects the natural reading order.
- **Filename language suffix:** `*-ar.md` means the document is written in Arabic; otherwise English.
- **Lowercase, hyphenated filenames** for shell-safe paths.
- **One canonical document per topic.** Where a derived companion exists, it cross-links to the canonical and declares its lower priority.

## Citation

> Temessek, Y. *The Arabic Tongue: Nature, Genome, Application.* Temessek for Research, Publishing & Training. [coranisyours.com](https://coranisyours.com) · [arabicjuthoor.com](https://arabicjuthoor.com/)
