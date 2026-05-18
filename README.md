# Juthoor · The Arabic Tongue

> 🌐 **Live site:** [**arabicjuthoor.com**](https://arabicjuthoor.com/)
> 🖥️ **Local dashboard:** [`index.html`](index.html). A single-page overview of the methodology, the 28-letter table, the 18 nuclei, the 12 operative modes, the 8 Tier-A cognates, and the scholarly foundation.
> 🚀 **Deploying:** see [`DEPLOYMENT.md`](DEPLOYMENT.md) for the GitHub Pages + Cloudflare DNS setup.

**Author:** Yassine Temessek
**Conducted under:** **Temessek for Research, Publishing & Training** · [coranisyours.com](https://coranisyours.com) · [arabicjuthoor.com](https://arabicjuthoor.com/)

---

## What this study is

An empirical study of meaning-composition in the Arabic tongue, built on the foundation of seven independent letter-semantics scholars and extended with new structural findings. The study's core results are the universal dual-face structure of letter charges, a 12-mode operative grammar for trilateral composition, a four-bar verification rubric for cross-linguistic Quranic cognates, and a complete 453-nucleus catalog.

## Layout

```
.
├── index.html                         ← 🌐 unified dashboard (open in any browser)
├── README.md                          ← this file
├── 01-theory/                         ← Arabic linguistic survey and foundation
├── 02-architecture/                   ← methodology and findings papers
├── 03-scholar-extracts/               ← reference tables and catalogs
├── 04-cross-linguistic/               ← cognate corpus
├── 05-audits/                         ← empirical record
└── Data raw/                          ← primary scholar sources (frozen)
```

## File map

### `01-theory/` — Arabic linguistic foundation

| File | Description |
|------|-------------|
| [classical-survey-ar.md](01-theory/classical-survey-ar.md) | A 20-chapter Arabic survey from الخليل and ابن جني through Jabal, Abbas, Neili, Asim, Anbar, Khshim, and Dhouq. The reference compendium. |

### `02-architecture/` — methodology and findings papers

| File | Description |
|------|-------------|
| [our-contributions-and-roadmap.md](02-architecture/our-contributions-and-roadmap.md) | **The shareable position paper.** What the study contributes, where it stands in relation to prior work, and the agenda ahead. |
| [lv2-operative-grammar.md](02-architecture/lv2-operative-grammar.md) | **The operative grammar of trilateral composition.** The 12-mode taxonomy applied to 2,285 graded roots at 100% native fit. |
| [lv1-architecture.md](02-architecture/lv1-architecture.md) | The architectural specification: the four-layer scope (genome → Semitic → cross-linguistic → Quranic) and the scoring framework. |

### `03-scholar-extracts/` — reference tables and catalogs

| File | Description |
|------|-------------|
| [consensus-letter-charges.md](03-scholar-extracts/consensus-letter-charges.md) | **The harmonized 28-letter table** with the universal dual-face structure and the 18-nucleus working shortlist. |
| [jabal-nuclei-extended.md](03-scholar-extracts/jabal-nuclei-extended.md) | **The full 453-nucleus catalog** with per-nucleus reading and source evidence. |
| [jabal-nuclei-tc-anchored.md](03-scholar-extracts/jabal-nuclei-tc-anchored.md) | The 258 nuclei whose readings are anchored to published Quranic verse-readings. |
| [abbas-letter-classification.md](03-scholar-extracts/abbas-letter-classification.md) | Hassan Abbas's dual-axis classification (sensory category × articulatory mechanism). |
| `jabal-letters.html` | Per-letter empirical evidence for the dual-face structure. |

### `04-cross-linguistic/` — cognate corpus

| File | Description |
|------|-------------|
| [tafsir-coran-tier-a-cognates.md](04-cross-linguistic/tafsir-coran-tier-a-cognates.md) | **The four-bar verification rubric** with the 8 Tier-A Quranic-anchored cognate pairs (kufu' ↔ copy, salām ↔ shalom, rabb ↔ rabbi, jinn ↔ genie, kalām ↔ claim, qul ↔ call, sharb ↔ sorb, jam' ↔ Gemini). |
| [beyond-the-word-examples.md](04-cross-linguistic/beyond-the-word-examples.md) | 17 popular Arabic↔English cognate cases retained for reference. |

### `05-audits/` — empirical record

The empirical evidence for every structural claim in the framework: the full nucleus test, the operative grammar grading, the metathesis evaluation, and the data-quality verifications. Researchers consulting the underlying evidence should start here.

### `Data raw/` — primary scholar sources (frozen)

| Subfolder | Contents | Role |
|---|---|---|
| `Languistic theories/` | Seven scholars (عباس, الشناوي, عاصم, النيلي, خشيم, ذوق, عنبر), 17 files | Primary theoretical sources |
| `Muajam Ishtiqaqi/` | `المعجم_الاشتقاقي_Juthoor_v2.xlsx` (2,300 unique roots, 453 binary nuclei, 28 letters) and 26 per-letter باب tables | Jabal's empirical dataset, the canonical ground truth |
| `facebook_posts_beyondthename/` and supporting files | The Beyond-the-Word source corpus | Raw material for the cross-linguistic layer |

## Reading order

If you have time for **one file**, read [`02-architecture/our-contributions-and-roadmap.md`](02-architecture/our-contributions-and-roadmap.md). It is the shareable position paper.

If you have time for **two**, add [`02-architecture/lv2-operative-grammar.md`](02-architecture/lv2-operative-grammar.md) for the operative grammar of trilateral composition.

For the **full picture**, read in folder order: 01 → 02 → 03 → 04.

## Conventions

- **Folder numbering** (`01-`, `02-`, …) reflects the natural reading order.
- **Filename language suffix:** `*-ar.md` means the document is written in Arabic; otherwise English.
- **Lowercase, hyphenated filenames** for shell-safe paths.
- **One canonical document per topic.** Where a derived companion exists, it cross-links to the canonical and declares its lower priority.

## Citation

> Temessek, Y. *The Arabic Tongue: Nature, Genome, Application.* Temessek for Research, Publishing & Training. [coranisyours.com](https://coranisyours.com)
