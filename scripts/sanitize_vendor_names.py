"""One-shot rewrite of vendor model names → generic 'Pass 1 / Pass 2' framing.

Applied to public-facing markdown in 05-audits/, 04-cross-linguistic/, 02-architecture/.
"""
from pathlib import Path
import re

VAULT = Path(r"C:\Users\yassi\AI Projects\The Arabic Tongue (nature-genome-application)")

# Order matters: do longer phrases first
REPLACEMENTS = [
    # English
    ("Sonnet 4.5 bulk + Opus deep-review pipeline",
     "Pass 1 (bulk discovery) + Pass 2 (deep-review) pipeline"),
    ("Sonnet 4.5 bulk + Opus deep-review",
     "Pass 1 bulk + Pass 2 deep-review"),
    ("Sonnet 4.5 bulk", "Pass 1 bulk"),
    ("Sonnet 4.5", "Pass 1 model"),
    ("Sonnet+Opus pipeline", "Pass 1 + Pass 2 pipeline"),
    ("Sonnet pipeline vs Opus 4.5 (calibrated)", "Pass 1 pipeline vs Pass 2 calibrated"),
    ("Sonnet pipeline vs calibrated Opus", "Pass 1 pipeline vs Pass 2 calibrated"),
    ("Sonnet pipeline (Sonnet 4.5 bulk + Opus deep-review)",
     "Pass 1 pipeline (bulk discovery + deep-review)"),
    ("calibrated Opus second pass", "Pass 2 calibrated re-read"),
    ("calibrated Opus re-scoring", "Pass 2 calibrated re-scoring"),
    ("calibrated Opus re-read", "Pass 2 calibrated re-read"),
    ("calibrated Opus", "Pass 2 calibrated"),
    ("Opus 4.5 (calibrated)", "Pass 2 calibrated"),
    ("Opus 4.5", "Pass 2 model"),
    ("Opus deep-review", "Pass 2 deep-review"),
    ("Opus calibrated", "Pass 2 calibrated"),
    ("Opus rater", "Pass 2 rater"),
    ("Opus scores", "Pass 2 scores"),
    ("scored by Opus", "scored by Pass 2"),
    ("re-scored by Opus", "re-scored by Pass 2"),
    ("the Sonnet pipeline", "the Pass 1 pipeline"),
    ("Sonnet bulk pass", "Pass 1 bulk pass"),
    ("the Sonnet", "Pass 1"),
    ("Opus, blind to A's scores", "the second rater, blind to A's scores"),
    ("by Opus, blind", "by the second rater, blind"),
    ("Gemini 2.5 Pro", "the un-calibrated alternate model"),
    ("Gemini 2.5 pro", "the un-calibrated alternate model"),
    ("Gemini, blind", "the alternate model, blind"),
    ("Gemini's", "the alternate model's"),
    ("Gemini scored", "the alternate model scored"),
    ("Gemini rated", "the alternate model rated"),
    ("Gemini agree", "the alternate model agree"),
    ("Gemini's lower scores", "the alternate model's lower scores"),
    # Standalone "Gemini" not preceded by /-Σ-/Latin would be model;
    # keep Gemini constellation references intact — those are spelled "Gemini star" or "Gemini constellation"
    # so a bare " Gemini " is the model when in audit-doc context
    (" Gemini ", " the alternate model "),
    (" Gemini.", " the alternate model."),
    (" Gemini,", " the alternate model,"),
    (" Gemini)", " the alternate model)"),
    # Arabic (the vendor names are mostly in Latin script even in AR docs)
    ("نُقاطِ Sonnet", "نُقاط التَّمريرة الأُولى"),
    ("نُقاط Sonnet", "نُقاط التَّمريرة الأُولى"),
    ("نِقاط Sonnet", "نِقاط التَّمريرة الأُولى"),
    ("أَنبوب Sonnet", "أَنبوب التَّمريرة الأُولى"),
    ("أَنبوبُ Sonnet", "أَنبوبُ التَّمريرة الأُولى"),
    ("نُقاطِ Opus", "نُقاط التَّمريرة الثانية"),
    ("نُقاط Opus", "نُقاط التَّمريرة الثانية"),
    ("Opus 4.5 (مُعايَر)", "التَّمريرة الثانية (مُعايَرة)"),
    ("Opus 4.5", "نَموذج التَّمريرة الثانية"),
    ("Opus المُعايَر", "التَّمريرة الثانية المُعايَرة"),
    ("بِـ Opus", "بِالتَّمريرة الثانية"),
    ("Opus، أَعمى", "المُقَيِّم الثاني، أَعمى"),
    ("Opus،", "التَّمريرة الثانية،"),
    ("Sonnet مُقابِل", "التَّمريرة الأُولى مُقابِل"),
    ("ضِدّ Sonnet", "ضِدّ التَّمريرة الأُولى"),
    ("Sonnet ↔", "التَّمريرة الأُولى ↔"),
    (" Sonnet ", " التَّمريرة الأُولى "),
    (" Sonnet.", " التَّمريرة الأُولى."),
    (" Sonnet،", " التَّمريرة الأُولى،"),
    (" Sonnet)", " التَّمريرة الأُولى)"),
    ("Gemini 2.5 Pro", "نَموذج مُغايِر غَير-مُعايَر"),
    (" Gemini ", " النَّموذج المُغايِر "),
    (" Gemini.", " النَّموذج المُغايِر."),
    (" Gemini،", " النَّموذج المُغايِر،"),
    (" Gemini)", " النَّموذج المُغايِر)"),
]

# Skip the wrong-test transparency doc (which explicitly documents the Gemini test)
# but we still rename Gemini there to "un-calibrated alternate model"
SKIP_PATHS = []  # Apply everywhere

# Skip the cross-linguistic Tier-A doc's "Gemini" line (it's the constellation cognate)
# We handle that case via context: if line contains "constellation" or "ج-م-ع" or "gemellus" → skip

count_changed = 0
for md_path in VAULT.rglob("*.md"):
    if any(s in str(md_path) for s in SKIP_PATHS):
        continue
    text = md_path.read_text(encoding="utf-8")
    orig = text
    for old, new in REPLACEMENTS:
        # Don't touch the Tier-A constellation line
        # Process line-by-line, skipping any line that contains 'constellation', 'gemellus', or 'ج-م-ع'
        new_lines = []
        for line in text.splitlines(keepends=True):
            if "Gemini" in old and any(marker in line for marker in ["gemellus", "ج-م-ع", "constellation", "Castor and Pollux"]):
                new_lines.append(line)
            else:
                new_lines.append(line.replace(old, new))
        text = "".join(new_lines)
    if text != orig:
        md_path.write_text(text, encoding="utf-8")
        count_changed += 1
        print(f"  updated: {md_path.relative_to(VAULT)}")

print(f"\nTotal files updated: {count_changed}")
