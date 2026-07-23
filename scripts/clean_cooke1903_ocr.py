#!/usr/bin/env python3
"""Quality-filter the Mistral OCR of Cooke 1903 before any card ever cites it.

Two defects were measured in the raw batch output and are handled here:

1. Added vocalisation. Cooke prints the inscriptions in unpointed Hebrew square script,
   as Phoenician epigraphy is consonantal. The OCR returns fully pointed text, so the
   niqqud is model-supplied, not source-attested. It is stripped, and the consonantal
   skeleton alone is kept.

2. Repetition loops. On dense philological commentary pages, the model can lock onto a
   short Semitic token and repeat it dozens of times. Such blocks are flagged, not silently
   kept, so no card is ever built on a hallucinated string.

Outputs a cleaned text plus a per-page quality report.
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "Data raw" / "cooke1903_text" / "mistral_ocr" / "cooke1903_mistral_full.md"
OUT = ROOT / "Data raw" / "cooke1903_text" / "mistral_ocr" / "cooke1903_clean.md"
REPORT = ROOT / "Data raw" / "cooke1903_text" / "mistral_ocr" / "quality-report.json"

HEB_RANGE = re.compile(r"[֐-׿]")
NIQQUD = re.compile(r"[֑-ׇ]")  # cantillation + vowel points
HEB_WORD = re.compile(r"[א-ת]{1,}")


def strip_points(s: str) -> str:
    """Remove Hebrew vowel points and cantillation, keep consonants."""
    return NIQQUD.sub("", unicodedata.normalize("NFD", s))


def repetition_score(body: str) -> tuple[float, str]:
    """Fraction of Hebrew tokens taken by the single most repeated token."""
    words = HEB_WORD.findall(strip_points(body))
    if len(words) < 8:
        return 0.0, ""
    counts = Counter(words)
    top, n = counts.most_common(1)[0]
    return n / len(words), top


def main() -> int:
    if not SRC.exists():
        sys.exit(f"missing OCR output: {SRC}")
    text = SRC.read_text(encoding="utf-8")

    parts = re.split(r"<!-- PAGE (\d+) -->", text)
    pages = {}
    for i in range(1, len(parts) - 1, 2):
        pages[int(parts[i])] = parts[i + 1]

    report = {"pages_total": len(pages), "pages": [], "summary": {}}
    clean_chunks = []
    flagged = 0
    pointed_pages = 0
    total_heb_before = 0
    total_heb_after = 0

    for pno in sorted(pages):
        body = pages[pno]
        heb_before = len(HEB_RANGE.findall(body))
        had_points = bool(NIQQUD.search(body))
        stripped = strip_points(body)
        heb_after = len(HEB_RANGE.findall(stripped))
        score, token = repetition_score(body)
        suspect = score >= 0.30

        total_heb_before += heb_before
        total_heb_after += heb_after
        if had_points:
            pointed_pages += 1
        if suspect:
            flagged += 1

        report["pages"].append({
            "page": pno,
            "semitic_chars": heb_after,
            "had_vowel_points": had_points,
            "repetition_ratio": round(score, 3),
            "repeated_token": token if suspect else "",
            "flagged_repetition": suspect,
        })

        header = f"\n\n<!-- PAGE {pno}"
        if suspect:
            header += f" | FLAGGED repetition ratio={score:.2f} token={token}"
        header += " -->\n"
        clean_chunks.append(header + stripped)

    with OUT.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("# Cooke 1903, Mistral batch OCR, quality-filtered\n")
        fh.write("# Source: Data raw/Cooke 1903.pdf (Oxford Clarendon 1903, public domain)\n")
        fh.write("# Vowel points removed: Cooke prints consonantal script, so OCR pointing is model-supplied.\n")
        fh.write("# Pages with a repetition loop are marked FLAGGED and must not be cited without checking the page image.\n")
        fh.write("".join(clean_chunks))

    report["summary"] = {
        "pages_with_vowel_points_removed": pointed_pages,
        "pages_flagged_for_repetition": flagged,
        "semitic_chars_raw": total_heb_before,
        "semitic_chars_after_stripping_points": total_heb_after,
    }
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"pages processed: {len(pages)}")
    print(f"pages carrying model-supplied vowel points: {pointed_pages}")
    print(f"pages flagged for repetition loops: {flagged}")
    print(f"semitic chars raw: {total_heb_before:,} -> consonantal only: {total_heb_after:,}")
    print("wrote:", OUT.name, "and", REPORT.name)
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
