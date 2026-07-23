#!/usr/bin/env python3
"""Classify every OCR page of Cooke 1903 as usable or contaminated, before anything cites it.

The batch OCR of this book failed on a large minority of pages in ways a Hebrew-only
repetition test cannot see. Measured failure modes:

1. Foreign-script hallucination. Cooke 1903 is an English book on North-Semitic epigraphy.
   Arabic and Urdu script has no place in it beyond the odd cited cognate, yet the raw output
   carries millions of Arabic-block characters in looping filler.
2. Model meta-commentary leaking as page content ("The Ground Truth image displays...",
   "According to Rule 2 (UNDERSCORE & LINE RULES)").
3. Vision-annotation JSON emitted instead of text (`box_2d`, `label`, `caption` objects).
4. Token or phrase repetition loops in any script.

A page failing any test is quarantined. Only pages passing all tests may be cited.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "Data raw" / "cooke1903_text" / "mistral_ocr" / "cooke1903_mistral_full.md"
OUT = ROOT / "Data raw" / "cooke1903_text" / "mistral_ocr" / "cooke1903_usable.md"
REPORT = ROOT / "Data raw" / "cooke1903_text" / "mistral_ocr" / "validation-report.json"

ARABIC = re.compile(r"[؀-ۿݐ-ݿ]")
HEBREW = re.compile(r"[֐-׿]")
NIQQUD = re.compile(r"[֑-ׇ]")
LETTER_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)
LATIN_WORD = re.compile(r"[A-Za-z]{2,}")

META_MARKERS = (
    "Ground Truth",
    "According to Rule",
    "UNDERSCORE",
    "box_2d",
    '"label"',
    "OCR RULES",
    "transcription rules",
)


def strip_points(s: str) -> str:
    return NIQQUD.sub("", unicodedata.normalize("NFD", s))


def max_repetition(body: str) -> tuple[float, str]:
    words = [w.casefold() for w in LETTER_WORD.findall(strip_points(body))]
    if len(words) < 8:
        return 0.0, ""
    best, token = 0.0, ""
    for width in (1, 2, 3, 4, 5, 6):
        n = len(words) - width + 1
        if n <= 0:
            break
        grams = Counter(tuple(words[i:i + width]) for i in range(n))
        gram, count = grams.most_common(1)[0]
        need = 8 if width == 1 else 4
        score = (count * width) / len(words)
        if count >= need and score > best:
            best, token = score, " ".join(gram)
    return min(best, 1.0), token


def classify(body: str) -> dict:
    stripped = strip_points(body)
    arabic = len(ARABIC.findall(stripped))
    hebrew = len(HEBREW.findall(stripped))
    latin = len(LATIN_WORD.findall(stripped))
    rep, token = max_repetition(body)
    meta = [m for m in META_MARKERS if m in body]

    reasons = []
    # An English book on Semitic epigraphy: a page swamped by Arabic script is hallucinating.
    if arabic > 40:
        reasons.append(f"arabic-script-flood:{arabic}")
    if meta:
        reasons.append("model-meta:" + ",".join(meta[:3]))
    if rep >= 0.30:
        reasons.append(f"repetition:{rep:.2f}:{token[:40]}")
    if latin < 5 and hebrew < 5:
        reasons.append("no-substantive-content")

    return {
        "arabic_chars": arabic,
        "hebrew_chars": hebrew,
        "latin_words": latin,
        "repetition_ratio": round(rep, 3),
        "repeated_token": token if rep >= 0.30 else "",
        "meta_markers": meta,
        "usable": not reasons,
        "reasons": reasons,
    }


def main() -> int:
    if not RAW.exists():
        sys.exit(f"missing raw OCR: {RAW}")
    text = RAW.read_text(encoding="utf-8")
    parts = re.split(r"<!-- PAGE (\d+) -->", text)
    pages = {int(parts[i]): parts[i + 1] for i in range(1, len(parts) - 1, 2)}

    rows, usable_chunks = [], []
    usable = 0
    heb_usable = 0

    for pno in sorted(pages):
        info = classify(pages[pno])
        info["page"] = pno
        rows.append(info)
        if info["usable"]:
            usable += 1
            heb_usable += info["hebrew_chars"]
            usable_chunks.append(f"\n\n<!-- PAGE {pno} -->\n" + strip_points(pages[pno]))

    with OUT.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("# Cooke 1903, Mistral batch OCR, validated usable pages only\n")
        fh.write("# Source: Data raw/Cooke 1903.pdf (Oxford Clarendon 1903, public domain)\n")
        fh.write("# Vowel points stripped: Cooke prints consonantal script, so OCR pointing is model-supplied.\n")
        fh.write("# Contaminated pages are excluded entirely; see validation-report.json for each exclusion reason.\n")
        fh.write("".join(usable_chunks))

    summary = {
        "pages_total": len(pages),
        "pages_usable": usable,
        "pages_quarantined": len(pages) - usable,
        "hebrew_chars_in_usable_pages": heb_usable,
        "reason_counts": dict(Counter(r.split(":")[0] for row in rows for r in row["reasons"])),
    }
    REPORT.write_text(json.dumps({"summary": summary, "pages": rows}, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"pages total:        {summary['pages_total']}")
    print(f"pages usable:       {summary['pages_usable']}")
    print(f"pages quarantined:  {summary['pages_quarantined']}")
    print(f"semitic chars kept: {heb_usable:,}")
    print("quarantine reasons:", summary["reason_counts"])
    print("wrote:", OUT.name, "and", REPORT.name)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
