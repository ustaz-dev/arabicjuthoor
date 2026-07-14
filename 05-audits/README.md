# Audits — the empirical record

This folder is the audit trail for the study. Every structural claim made in the dashboard and the position paper has its supporting evidence here: the data verifications, the predictive tests, the editorial decisions, and the data-quality reconciliations.

## What lives here

| File | What it documents |
|---|---|
| [`2026-03-24-lv1-data-audit.md`](2026-03-24-lv1-data-audit.md) | The verified-data audit: scholar coverage counts, dataset totals, and reconciliation of figures between the master xlsx, the per-file sources, and the computational pipeline. |
| [`2026-05-09-7.1.4-anbar-golden-rule-structural.md`](2026-05-09-7.1.4-anbar-golden-rule-structural.md) | The reversibility test — structural pass. Identifies all reverse-permutation pairs in Jabal's lexicon. |
| [`2026-05-09-7.1.4-anbar-golden-rule-graded.md`](2026-05-09-7.1.4-anbar-golden-rule-graded.md) | The reversibility test — full graded report. The 155 reverse-pairs graded across 4 levels (inverse / related / adjacent / unrelated), yielding the 22% inverse hit-rate cited in the position paper. |
| [`2026-05-09-7.2.5-fourteen-root-delta-resolved.md`](2026-05-09-7.2.5-fourteen-root-delta-resolved.md) | Reconciliation of root counts between the master xlsx (1,924 lexicon rows / 2,300 unique roots) and the computational pipeline. Traces two ingest bugs to the script that loads the xlsx into JSONL. |
| [`2026-05-10-not-earned-nuclei-deep-investigation.md`](2026-05-10-not-earned-nuclei-deep-investigation.md) | Deep manual investigation of the 4 nuclei whose composition-graded readings did not earn corroboration from Jabal's trilateral family. Yields 2 substantive variant findings for ن and ه. |
| [`2026-05-11-jabal-data-anomalies.md`](2026-05-11-jabal-data-anomalies.md) | The 4 entries in Jabal's lexicon that turned out to be data-quality artefacts (section headers, mojibake). Establishes the corrected total of 453 legitimate binary nuclei. |
| [`2026-07-13-egyptian-counter-audit-corrections.md`](2026-07-13-egyptian-counter-audit-corrections.md) | The append-only correction round for the Egyptian/Coptic readings: accepts mw and las, corrects ḫf and km, narrows BR-EGYP-02 to descendant-attested cases, reconciles the operational 455 count, and records the new CI guard. |
| [`2026-07-14-shnft-recovery-protocol.md`](2026-07-14-shnft-recovery-protocol.md) | The šnf.t case study and RECOVERY-v2 anti-self-sabotage gate: full Arabic sense-fan search, homonym/etymology separation, gap states distinct from verdicts, retrospective tests, and CI enforcement before NO-TRACE. |

## Why this folder exists

The dashboard and the position paper present **outcomes**. The audits folder records **how those outcomes were reached** — the cross-checks, the editorial reasoning behind which charge was chosen for each letter, the predictive tests, and the data verifications.

This is where a researcher who wants to push back on a specific claim should start. Every claim in the public-facing files has its evidence here.
