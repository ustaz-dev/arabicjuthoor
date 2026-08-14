# -*- coding: utf-8 -*-
"""قابل مسح «رحلة الكلمات، الرحلة الأولى» الرسمي بالمسح القديم سطرًا بسطر.

هذا فاحص فقط: لا يكتب في مخزن خشيم ولا يستبدل حقلاً. يثبت إزاحة الصفحات،
ويحفظ قياس المحاذاة السطرية، ثم يفحص موضع كل صف محصود في صفحته الجديدة.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import pathlib
import re
import statistics
import unicodedata
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parent.parent
DEFAULT_OLD = pathlib.Path(
    r"C:\Users\yassi\AI Projects\Resources\prior-art\ocr-khashim-journey1\full.md"
)
DEFAULT_NEW = pathlib.Path(
    r"C:\Users\yassi\AI Projects\Resources\prior-art\ocr-khashim-journey1-recovery-20260814\full.md"
)
DEFAULT_PAIRS = ROOT / "data" / "khashim-pairs.json"
DEFAULT_OUT = ROOT / "data" / "khashim-journey1-official-ocr-comparison.json"
PAGE = re.compile(r"<!--\s*صفحة\s+(\d+)\s*-->")
IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
TAG = re.compile(r"<[^>]+>")
TOKEN = re.compile(r"[\w\u0600-\u06ff]+", re.UNICODE)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = IMAGE.sub(" ", text)
    text = TAG.sub(" ", text)
    text = "".join(
        char
        for char in unicodedata.normalize("NFD", text)
        if unicodedata.category(char) != "Mn"
    )
    text = re.sub(r"[^\w\u0600-\u06ff]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def parse_pages(path: pathlib.Path) -> tuple[
    list[str], dict[int, list[tuple[int, str]]], dict[int, int]
]:
    lines = path.read_text(encoding="utf-8").splitlines()
    pages: dict[int, list[tuple[int, str]]] = {}
    page_by_line: dict[int, int] = {}
    current = 0
    for line_number, line in enumerate(lines, 1):
        marker = PAGE.search(line)
        if marker:
            current = int(marker.group(1))
            pages.setdefault(current, [])
            page_by_line[line_number] = current
            continue
        if current:
            pages[current].append((line_number, line))
            page_by_line[line_number] = current
    return lines, pages, page_by_line


def normalized_lines(page: list[tuple[int, str]]) -> list[str]:
    return [clean for _, line in page if (clean := normalize(line))]


def token_set(page: list[tuple[int, str]]) -> set[str]:
    return set(TOKEN.findall(normalize("\n".join(line for _, line in page))))


def page_comparison(
    old_page: int,
    new_page: int,
    old: dict[int, list[tuple[int, str]]],
    new: dict[int, list[tuple[int, str]]],
) -> dict[str, Any]:
    left = normalized_lines(old.get(old_page, []))
    right = normalized_lines(new.get(new_page, []))
    matcher = difflib.SequenceMatcher(None, left, right, autojunk=False)
    opcodes = matcher.get_opcodes()
    exact = sum(a2 - a1 for tag, a1, a2, _, _ in opcodes if tag == "equal")
    tags = {
        tag: sum(1 for item in opcodes if item[0] == tag)
        for tag in ("equal", "replace", "delete", "insert")
    }
    left_tokens = token_set(old.get(old_page, []))
    right_tokens = token_set(new.get(new_page, []))
    union = left_tokens | right_tokens
    jaccard = len(left_tokens & right_tokens) / len(union) if union else 1.0
    return {
        "old_page": old_page,
        "new_page": new_page,
        "old_nonempty_lines": len(left),
        "new_nonempty_lines": len(right),
        "exact_normalized_lines": exact,
        "line_alignment_ratio": round(matcher.ratio(), 6),
        "token_jaccard": round(jaccard, 6),
        "opcode_blocks": tags,
    }


def registered_defects(row: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    recovery = row.get("ocr_recovery")
    if isinstance(recovery, dict):
        values = recovery.get("registered_scan_reasons") or []
        reasons.extend(str(value) for value in values if value)
    if row.get("legacy"):
        reasons.append("حقل legacy قائم في الصف")
    return list(dict.fromkeys(reasons))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old", type=pathlib.Path, default=DEFAULT_OLD)
    parser.add_argument("--new", type=pathlib.Path, default=DEFAULT_NEW)
    parser.add_argument("--pairs", type=pathlib.Path, default=DEFAULT_PAIRS)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--offset", type=int, default=2)
    args = parser.parse_args()

    _, old_pages, old_page_by_line = parse_pages(args.old)
    _, new_pages, _ = parse_pages(args.new)
    page_rows = [
        page_comparison(page, page + args.offset, old_pages, new_pages)
        for page in sorted(old_pages)
        if page + args.offset in new_pages
    ]

    store = json.loads(args.pairs.read_text(encoding="utf-8"))
    all_rows = store["rows"]
    source_rows = [
        (index, row)
        for index, row in enumerate(all_rows)
        if row.get("source") == "ocr-khashim-journey1"
    ]
    row_checks: list[dict[str, Any]] = []
    for source_index, row in source_rows:
        line = int(row["source_line"])
        old_page = old_page_by_line.get(line)
        new_page = old_page + args.offset if old_page is not None else None
        official_text = "\n".join(
            value for _, value in new_pages.get(new_page or -1, [])
        )
        foreign = normalize(row.get("foreign"))
        arabic_root = normalize(row.get("arabic_root"))
        defects = registered_defects(row)
        row_checks.append({
            "source_index": source_index,
            "source_line": line,
            "old_page": old_page,
            "new_page": new_page,
            "foreign": row.get("foreign"),
            "arabic_root": row.get("arabic_root"),
            "foreign_present_on_new_page": bool(
                foreign and foreign in normalize(official_text)
            ),
            "arabic_root_present_on_new_page": bool(
                arabic_root and arabic_root in normalize(official_text)
            ),
            "registered_scan_reasons": defects,
            "replacement_allowed": bool(defects),
        })

    old_line_count = sum(row["old_nonempty_lines"] for row in page_rows)
    new_line_count = sum(row["new_nonempty_lines"] for row in page_rows)
    exact_line_count = sum(row["exact_normalized_lines"] for row in page_rows)
    line_ratios = [row["line_alignment_ratio"] for row in page_rows]
    token_ratios = [row["token_jaccard"] for row in page_rows]
    defect_rows = sum(bool(row["registered_scan_reasons"]) for row in row_checks)
    mapped_new = {row["new_page"] for row in page_rows}
    result = {
        "schema": "khashim-journey1-official-ocr-comparison-v1",
        "generated_by": "scripts/audit_khashim_journey1_official_ocr.py",
        "contract": (
            "المقابلة سطرية، ولا يستبدل حقل إلا لعيب مسح مسجل؛ "
            "هذا الفاحص لا يكتب في المخزن"
        ),
        "old_source": str(args.old),
        "new_source": str(args.new),
        "pairs_source": str(args.pairs.relative_to(ROOT)),
        "input_sha256": {
            "old_markdown": sha256(args.old),
            "new_markdown": sha256(args.new),
            "pairs_store": sha256(args.pairs),
        },
        "page_mapping": {
            "old_pages": len(old_pages),
            "new_pages": len(new_pages),
            "offset": args.offset,
            "rule": "new_page = old_page + 2",
            "mapped_pages": len(page_rows),
            "unmapped_new_pages": sorted(set(new_pages) - mapped_new),
        },
        "line_comparison": {
            "old_nonempty_normalized_lines": old_line_count,
            "new_nonempty_normalized_lines": new_line_count,
            "exact_normalized_lines": exact_line_count,
            "exact_share_of_old": round(exact_line_count / old_line_count, 6),
            "mean_line_alignment_ratio": round(statistics.mean(line_ratios), 6),
            "median_line_alignment_ratio": round(statistics.median(line_ratios), 6),
            "mean_token_jaccard": round(statistics.mean(token_ratios), 6),
            "median_token_jaccard": round(statistics.median(token_ratios), 6),
            "pages_token_jaccard_at_least_0_8": sum(
                value >= 0.8 for value in token_ratios
            ),
        },
        "row_contract": {
            "structured_rows": len(row_checks),
            "registered_defect_rows": defect_rows,
            "foreign_present_on_mapped_page": sum(
                row["foreign_present_on_new_page"] for row in row_checks
            ),
            "arabic_root_present_on_mapped_page": sum(
                row["arabic_root_present_on_new_page"] for row in row_checks
            ),
            "both_present_on_mapped_page": sum(
                row["foreign_present_on_new_page"]
                and row["arabic_root_present_on_new_page"]
                for row in row_checks
            ),
            "replacements": 0,
            "reharvest_rows": 0,
        },
        "pages": page_rows,
        "rows": row_checks,
    }
    if len(page_rows) != len(old_pages):
        raise SystemExit("لم تغط المقابلة جميع صفحات المسح القديم")
    if defect_rows:
        raise SystemExit("ظهر عيب مسجل غير متوقع؛ يلزم مسار استرداد لا فحص فقط")
    args.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "mapped_pages": len(page_rows),
        "exact_lines": exact_line_count,
        "median_token_jaccard": result["line_comparison"]["median_token_jaccard"],
        "structured_rows": len(row_checks),
        "registered_defect_rows": defect_rows,
        "replacements": 0,
        "reharvest_rows": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
