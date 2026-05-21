"""Second-pass cleanup of awkward phrases from the first sanitizer run."""
from pathlib import Path

VAULT = Path(r"C:\Users\yassi\AI Projects\The Arabic Tongue (nature-genome-application)")

CLEANUPS = [
    # Wrong-test transparency doc — fix the doubled "un-calibrated"
    ("the un-calibrated alternate model IRR (un-calibrated)",
     "Alternate-model IRR · un-calibrated"),
    ("the un-calibrated alternate model was given a stripped-down prompt",
     "an alternate model was given a stripped-down prompt"),
    ("the alternate model's training data",
     "that model's training data"),
    ("Rater B (Gemini)", "Rater B (alternate model)"),
    ("rater B (Gemini)", "rater B (alternate model)"),
    ("A (Sonnet)", "A (Pass 1)"),
    ("B (Gemini)", "B (alternate model)"),
    # Awkward leftovers
    ("Sonnet/Codex blend", "Pass 1 (bulk discovery)"),
    ("Sonnet/Codex pipeline", "Pass 1 pipeline"),
    ("Sonnet+Codex+Opus pipeline", "Pass 1 + Pass 2 pipeline"),
    ("Sonnet+Codex pipeline", "Pass 1 pipeline"),
    ("Opus deep review", "Pass 2 deep review"),
    ("Opus deep-review", "Pass 2 deep-review"),
    ("Opus pass", "Pass 2"),
    ("Codex deep-review", "Pass 2 deep-review"),
    ("with Opus", "with Pass 2"),
    ("vs Opus", "vs Pass 2"),
    # AR leftover
    ("مُراجَعةَ Opus", "مُراجَعةَ التَّمريرة الثانية"),
    ("مُراجَعةُ Opus", "مُراجَعةُ التَّمريرة الثانية"),
    ("نَتائج Sonnet", "نَتائج التَّمريرة الأُولى"),
    ("نَتائج Opus", "نَتائج التَّمريرة الثانية"),
    ("تَدقيقُ Opus", "تَدقيقُ التَّمريرة الثانية"),
    ("Sonnet ", "التَّمريرة الأُولى "),
    ("Opus ", "التَّمريرة الثانية "),
    # Catch any standalone "Sonnet" or "Opus" left over
    (" Sonnet ", " Pass 1 "),
    (" Sonnet's", " Pass 1's"),
    (" Sonnet,", " Pass 1,"),
    (" Sonnet.", " Pass 1."),
    (" Sonnet)", " Pass 1)"),
    ("(Sonnet ", "(Pass 1 "),
    (" Opus ", " Pass 2 "),
    (" Opus's", " Pass 2's"),
    (" Opus,", " Pass 2,"),
    (" Opus.", " Pass 2."),
    (" Opus)", " Pass 2)"),
    ("(Opus ", "(Pass 2 "),
    (" Gemini ", " alternate model "),
    (" Gemini's", " alternate model's"),
    (" Gemini,", " alternate model,"),
    (" Gemini.", " alternate model."),
]

# Skip lines/files that should keep "Gemini" (the constellation cognate)
KEEP_GEMINI_MARKERS = ["gemellus", "ج-م-ع", "constellation", "Castor"]

count = 0
for md_path in VAULT.rglob("*.md"):
    text = md_path.read_text(encoding="utf-8")
    orig = text
    new_lines = []
    for line in text.splitlines(keepends=True):
        keep_gemini = any(m in line for m in KEEP_GEMINI_MARKERS)
        for old, new in CLEANUPS:
            if "Gemini" in old and keep_gemini:
                continue
            line = line.replace(old, new)
        new_lines.append(line)
    text = "".join(new_lines)
    if text != orig:
        md_path.write_text(text, encoding="utf-8")
        count += 1

print(f"Cleaned {count} files")
