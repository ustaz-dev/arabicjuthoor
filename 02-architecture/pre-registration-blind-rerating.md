# Pre-registration: blind second reading of the 2,285 trilateral roots (Pass 2)

**Date registered:** 2026-07-05 (committed before any Pass 2 batch was run; the git timestamp of this file is the proof)
**Companion data:** `computational/data/layer_2_results_v2.jsonl` (2,285 records, Pass 1)
**Canon rubric:** [`lv2-operative-grammar.md`](lv2-operative-grammar.md) (the 11 modes + LOANWORD) and [`../03-scholar-extracts/consensus-letter-charges.md`](../03-scholar-extracts/consensus-letter-charges.md) (the 28 fixed charges)

## لماذا هذه الجولة، بقراءةِ الإطار

القانونُ ثابتٌ بالاستقراءِ على المعجمِ كلِّه: الشحناتُ في اللغةِ لا في عينِ القارئ. وهذا يُنتِجُ تنبّؤًا قابلًا للقياس: **قارئٌ أعمى، مُسلَّحٌ بالجدولِ الثابتِ نفسِه وتعريفاتِ الأبوابِ نفسِها، يجبُ أن يصِلَ إلى البابِ نفسِه في الغالبِ الأعمّ.** الجولةُ الثانيةُ تقيسُ قابليّةَ القراءةِ لأيِّ قارئٍ منضبط، وترفعُ قيدَ «مُقيِّمٍ واحد» المُعلَنَ في الورقة. وحيثُ يختلفُ القارئان، فذلك خريطةُ صقلٍ لتعريفاتِ الأبواب، وقد نَصَّ الإطارُ نفسُه على أنّ الأبوابَ «مفتوحةٌ للصقل، قد يندمجُ بعضُها أو ينشطر». الجولةُ مُثمِرةٌ في الحالتَين؛ ما يُنشَرُ هو ما يُقاس.

## Protocol

### What the second reader sees, per root
`tri_root`, `binary`, `third`, `binary_reading_ar/en` (the canon nucleus reading), `L3_charge_ar/en` (the fixed charge of the third radical), and `jabal_axial` (the attested axial meaning from Jabal's lexicon, the lexical anchor).

### What is withheld
`mode`, `reason`, `mode_category`, and every other Pass 1 judgment. The second reader never sees how Pass 1 classified anything.

### The task
For each root, assign exactly one mode from the closed inventory below (the canon definitions in `lv2-operative-grammar.md` govern), plus a one-line reason:

- POSITIVE stance: **CARRY, HOLD, RELEASE, PROJECT, INTENSIFY**
- NEGATIVE stance: **BLOCK, DRAIN**
- TRANSFORM stance: **CHANNEL, OPERATE, MIX, REVERT**
- Exception label: **LOANWORD** (only if no native composition fits)

### Mechanics
Batches of ~50 roots per blind run, every batch carrying the same fixed rubric text; output schema-forced (`tri_root`, `mode_2`, `reason_2`); results assembled into `computational/data/layer_2_pass2.jsonl`. The runs are labelled Pass 2; no model-vendor names appear in data or docs.

## Pre-registered metrics (declared before running)

1. **Primary: raw mode agreement** (Pass 2 mode == Pass 1 mode) over all 2,285.
2. **Chance-corrected agreement: Cohen's kappa** computed from the full 12x12 confusion matrix (Pass 1 marginals are skewed, OPERATE 24.4% ... MIX 0.6%, so kappa is the honest number).
3. **Stance-level agreement** (positive / negative / transform), a coarser secondary read.
4. **Confusion clusters:** the mode pairs that absorb most disagreements, reported in full.

## Pre-registered prediction

High agreement, with the residual disagreements concentrated in adjacent-stance pairs (e.g. OPERATE/CHANNEL, CARRY/PROJECT) rather than scattered uniformly. Uniform scatter would indict the mode definitions; concentrated clusters mark exactly which boundaries need sharpening.

## Pre-registered adjudication protocol

Every disagreement goes to a third adjudication reading that sees the root data and the two candidate modes **unlabelled** (not knowing which pass produced which), picks the better-fitting mode or flags "both defensible", and gives one line of grounds. All adjudications are logged in the audit file. The master data is only changed where adjudication rules against Pass 1, and every such change is listed.

## Publication commitment

The audit (`05-audits/`) will publish: both agreement numbers (raw + kappa), the stance-level number, the full confusion matrix, the complete disagreement list with adjudications, and the resulting paper-text change (the "single-rater" caveat in `01-theory/the-original-tongue.md` §I replaced by the measured result). Nothing is trimmed to look better; the numbers are reported as measured.
