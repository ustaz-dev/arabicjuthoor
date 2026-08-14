# -*- coding: utf-8 -*-
"""استرد رؤوس «القبطية العربية» الموسومة بالسقوط، ولا تمس غيرها.

المصدر القديم أعاد 169 صفا باسم ``khashim-coptic``، وفي 143 منها كتب
الحاصد صراحة ``(سقطَ حرفُه في المسح)`` في حقل الرأس. يرصف هذا السكربت
الجزء القابل للتحقق من تلك الصفوف مع المعجم الثالث في المسح الرسمي الجديد.
الرصف رتيب، ولا يعاد استعمال مدخل جديد، ولا يقبل الرأس إلا مع شاهد دلالي
عربي قوي. الناتج Overlay مودع، أما ملف OCR فخارج Git.
"""
from __future__ import annotations

import argparse
import difflib
import json
import pathlib
import re
import sys
import unicodedata
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORE = ROOT.parent / "Resources" / "prior-art"
PAIR_STORE = ROOT / "data" / "khashim-pairs.json"
NEW = STORE / "ocr-khashim-coptic-recovery-20260814" / "full.md"
OUT = ROOT / "data" / "khashim-coptic-ocr-recoveries.json"

SOURCE = "khashim-coptic"
FALLEN = "(سقطَ حرفُه في المسح)"
DEFECT = "رأس المدخل القبطي اللاتيني مسجل بأنه سقط في المسح القديم"
DICTIONARY3_FIRST_ROW = 36
EXPECTED_OLD_ROWS = 169
PAGE_MARK = re.compile(r"^<!--\s*صفحة\s+(\d+)\s*-->$")
AR = re.compile(r"[\u0600-\u06ff]")
LATIN = r"A-Za-zÀ-žḏḥḫḳṣṭṯẖʿꜣꜥ"
HEAD_CHARS = rf"[{LATIN}() /,.'+\-]"
INLINE_REVERSED = re.compile(
    rf"^\s*\*\*\\?\*\s*(.+?)\*\*\s+({HEAD_CHARS}+)\s*$"
)
ARABIC_ROOT = re.compile(
    r"العربي(?:ة|ه)\s*[:：]?\s*[><()]*\s*([ء-ي\u064b-\u065fـ]{2,12})"
)


def bare_ar(value: str) -> str:
    value = unicodedata.normalize("NFKC", str(value or ""))
    value = re.sub(r"[\u064b-\u065fـ]", "", value)
    value = value.translate(str.maketrans({
        "أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه",
    }))
    return "".join(char for char in value if "\u0600" <= char <= "\u06ff")


def similarity(left: str, right: str) -> float:
    left, right = bare_ar(left), bare_ar(right)
    if not left or not right:
        return 0.0
    return difflib.SequenceMatcher(None, left, right, autojunk=False).ratio()


def strip_markdown(value: str) -> str:
    value = re.sub(r"<!--.*?-->", "", value)
    value = value.replace("\\*", "*").replace("**", "")
    value = re.sub(r"^#{1,6}\s*", "", value)
    return value.strip()


def pure_head(value: str) -> str | None:
    value = strip_markdown(value)
    if (not value or value.startswith(("*", "-", "(", "["))
            or AR.search(value) or len(value) > 60):
        return None
    if not re.fullmatch(HEAD_CHARS + "+", value):
        return None
    return value if re.search(rf"[{LATIN}]", value) else None


def parse_candidates(path: pathlib.Path) -> list[dict[str, Any]]:
    """اقرأ مداخل معجم شيرني في ترتيبها المطبوع.

    يخرج مِسترال بعض رؤوس أول الصفحة بعد المعنى في السطر نفسه، ثم يعود
    إلى البنية المعتادة: الرأس في سطر، والمعنى في السطر التالي. يقبل
    المحلل الصورتين ويثبت الصفحة والسطر لكل مدخل.
    """
    raw = path.read_text(encoding="utf-8").splitlines()
    start = next(i for i, line in enumerate(raw) if line.strip() == "# (3)")
    end = next(
        i for i, line in enumerate(raw[start + 1:], start + 1)
        if re.match(r"^##\s+مؤلفات", line.strip())
    )

    current_page: int | None = None
    pages: dict[int, int | None] = {}
    for index, line in enumerate(raw):
        marker = PAGE_MARK.match(line.strip())
        if marker:
            current_page = int(marker.group(1))
        pages[index] = current_page

    positions: list[tuple[int, str, str]] = []
    for index in range(start + 1, end):
        inline = INLINE_REVERSED.match(raw[index])
        if (inline and AR.search(inline.group(1))
                and re.fullmatch(HEAD_CHARS + "+", inline.group(2).strip())):
            positions.append((index, inline.group(2).strip(), inline.group(1).strip()))
            continue
        head = pure_head(raw[index])
        if not head:
            continue
        if any(AR.search(strip_markdown(line))
               for line in raw[index + 1:min(end, index + 5)]):
            positions.append((index, head, ""))

    unique: list[tuple[int, str, str]] = []
    seen_lines: set[int] = set()
    for position in positions:
        if position[0] in seen_lines:
            continue
        seen_lines.add(position[0])
        unique.append(position)
    positions = unique

    candidates: list[dict[str, Any]] = []
    for position, (line_index, head, inline_sense) in enumerate(positions):
        stop = positions[position + 1][0] if position + 1 < len(positions) else end
        block = [
            strip_markdown(line) for line in raw[line_index:stop]
            if strip_markdown(line) and not strip_markdown(line).startswith("<!--")
        ]
        sense = inline_sense
        if not sense:
            for line in block[1:]:
                if AR.search(line):
                    sense = line.lstrip("*- ").strip()
                    break
        body = " ".join(
            line.lstrip("*- ").strip() for line in block[1:] if AR.search(line)
        )
        roots = [bare_ar(match.group(1)) for match in ARABIC_ROOT.finditer(body)]
        candidates.append({
            "foreign": head,
            "foreign_sense": sense,
            "arabic_body": body,
            "arabic_roots": roots,
            "source_page": pages[line_index],
            "source_line": line_index + 1,
        })
    return candidates


def source_rows(path: pathlib.Path) -> tuple[list[dict[str, Any]], list[int]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    all_rows = payload["rows"]
    positions = [index for index, row in enumerate(all_rows) if row.get("source") == SOURCE]
    rows: list[dict[str, Any]] = []
    for index in positions:
        row = dict(all_rows[index])
        legacy = row.get("legacy") or {}
        row["foreign"] = legacy.get("foreign", row.get("foreign", ""))
        rows.append(row)
    if len(rows) != EXPECTED_OLD_ROWS:
        raise SystemExit(f"تغير جرد القبطية القديم: {len(rows)} لا {EXPECTED_OLD_ROWS}")
    return rows, positions


def evidence(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    sense = similarity(old.get("foreign_sense", ""), new.get("foreign_sense", ""))
    gloss = similarity(old.get("arabic_gloss", ""), new.get("arabic_body", ""))
    root = bare_ar(old.get("arabic_root", ""))
    root_exact = bool(root and root in new.get("arabic_roots", []))
    score = 10.0 * sense + 6.0 * gloss + (10.0 if root_exact else 0.0) - 3.0
    return {
        "sense_similarity": sense,
        "arabic_gloss_similarity": gloss,
        "arabic_root_exact": root_exact,
        "score": score,
    }


def align(old: list[dict[str, Any]], new: list[dict[str, Any]]) -> tuple[list[tuple[int, int]], list[list[dict[str, Any]]]]:
    """أقصى رصف موزون رتيب، مع سماح بإسقاط الصف من أي الجانبين."""
    matrix = [[evidence(left, right) for right in new] for left in old]
    n, m = len(old), len(new)
    scores = [[0.0] * (m + 1) for _ in range(n + 1)]
    paths = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            match = max(0.0, matrix[i - 1][j - 1]["score"])
            choices = (
                scores[i - 1][j],
                scores[i][j - 1],
                scores[i - 1][j - 1] + match,
            )
            choice = max(range(3), key=lambda key: choices[key])
            scores[i][j], paths[i][j] = choices[choice], choice

    matches: list[tuple[int, int]] = []
    i, j = n, m
    while i and j:
        choice = paths[i][j]
        if choice == 2:
            if matrix[i - 1][j - 1]["score"] > 0:
                matches.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif choice == 0:
            i -= 1
        else:
            j -= 1
    matches.reverse()
    return matches, matrix


def acceptable(item: dict[str, Any]) -> bool:
    """لا يكفي الترتيب وحده؛ يلزم شاهد معنى أو شرح عربي قوي."""
    sense = item["sense_similarity"]
    gloss = item["arabic_gloss_similarity"]
    root = item["arabic_root_exact"]
    if item["score"] < 8.0:
        return False
    return bool(
        (root and (sense >= 0.60 or gloss >= 0.52
                   or (sense >= 0.45 and gloss >= 0.25)))
        or (sense >= 0.85 and gloss >= 0.20)
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--new", type=pathlib.Path, default=NEW)
    parser.add_argument("--pairs", type=pathlib.Path, default=PAIR_STORE)
    parser.add_argument("--out", type=pathlib.Path, default=OUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    rows, global_positions = source_rows(args.pairs)
    candidates = parse_candidates(args.new)
    dictionary_rows = rows[DICTIONARY3_FIRST_ROW:]
    matches, matrix = align(dictionary_rows, candidates)

    recoveries: list[dict[str, Any]] = []
    for local_dictionary_index, new_index in matches:
        source_index = local_dictionary_index + DICTIONARY3_FIRST_ROW
        old, new = rows[source_index], candidates[new_index]
        proof = matrix[local_dictionary_index][new_index]
        if old.get("foreign") != FALLEN or not acceptable(proof):
            continue
        recoveries.append({
            "source_index": source_index,
            "pair_index": global_positions[source_index],
            "source": SOURCE,
            "arabic_root": old.get("arabic_root"),
            "registered_scan_reasons": [DEFECT],
            "new_scan_reasons": [],
            "fields": {
                "foreign": {"legacy": FALLEN, "recovered": new["foreign"]},
            },
            "old_location": {"source_index": source_index},
            "new_location": {
                "page": new.get("source_page"),
                "line": new.get("source_line"),
            },
            "matched_new_row": new_index,
            "alignment_score": round(proof["score"], 6),
            "alignment_evidence": {
                "sense_similarity": round(proof["sense_similarity"], 6),
                "arabic_gloss_similarity": round(proof["arabic_gloss_similarity"], 6),
                "arabic_root_exact": proof["arabic_root_exact"],
                "new_foreign_sense": new.get("foreign_sense"),
            },
        })

    payload = {
        "schema": "khashim-coptic-ocr-recovery-v1",
        "generated_by": "scripts/recover_khashim_coptic_ocr.py",
        "book": "علي فهمي خشيم، «القبطية العربية»",
        "old_source": "Resources/prior-art/khashim-coptic.pdf",
        "new_source": "Resources/prior-art/ocr-khashim-coptic-recovery-20260814/full.md",
        "source_pdf_archive_item": "AAlexandrina-122567",
        "old_rows": len(rows),
        "registered_fallen_heads": sum(row.get("foreign") == FALLEN for row in rows),
        "dictionary3_first_source_index": DICTIONARY3_FIRST_ROW,
        "new_candidates": len(candidates),
        "aligned_rows": len(matches),
        "restored_unique_rows": len(recoveries),
        "restored_fields": {"foreign": len(recoveries)},
        "contract": (
            "رصف رتيب بلا إعادة استعمال داخل معجم شيرني؛ لا يبدل إلا الرأس "
            "الموسوم صراحة بأنه سقط؛ ويلزم تطابق الجذر مع شاهد معنى أو شرح "
            "قوي، أو اتفاق المعنى والشرح اتفاقا مستقلا"
        ),
        "recoveries": recoveries,
    }
    print(json.dumps({key: payload[key] for key in (
        "old_rows", "registered_fallen_heads", "new_candidates", "aligned_rows",
        "restored_unique_rows", "restored_fields",
    )}, ensure_ascii=False, indent=1))
    if not args.dry_run:
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                            encoding="utf-8", newline="\n")
        print(f"كتب: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
