# -*- coding: utf-8 -*-
"""قابل مسحي «البرهان» رتيبًا، واكتب إصلاحات العيوب المسجلة وحدها.

لا يعيد هذا السكربت حصاد الكتاب من الصفر، ولا يبدل صفًا سليمًا. مقامه هو
الفهارس الـ938 الموجودة في دفعات خشيم المصرية. يرد كل فهرس إلى سطره في
المسح القديم، ثم يرصفه بالمسح الجديد رصفًا عالميًا رتيبًا لا يعيد استعمال
صف جديد. ولا يقبل حقلًا جديدًا إلا إذا أزال سببًا مسجلًا في ملفات الدفعات.

الناتج Overlay مودع؛ أما ملفا OCR فخارج Git. يحمل كل إصلاح حقل ``legacy``
صريحًا، وموضع الصفحة والسطر في المسحين، ودرجة الرصف، والأسباب قبل وبعد.
"""
from __future__ import annotations

import argparse
import difflib
import json
import pathlib
import re
import sys
import unicodedata
from collections import Counter
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_khashim_egyptian_cards as CARDS  # noqa: E402
import harvest_khashim as KH  # noqa: E402

STORE = ROOT.parent / "Resources" / "prior-art"
OLD = STORE / "ocr-egyptian2" / "full.md"
NEW = STORE / "ocr-khashim-proof-recovery-20260814" / "full.md"
PAIR_STORE = ROOT / "data" / "khashim-pairs.json"
REPORTS = [ROOT / "data" / f"khashim-egyptian-batch-{n:03d}.json"
           for n in range(1, 5)]
OUT = ROOT / "data" / "khashim-egyptian-ocr-recoveries.json"

SENSE_DEFECT = "المعنى الإنجليزي لم يسلم من المسح"
HEAD_DEFECT = "رأس ذو فراغ: مركب أو التحمت به عبارة إنجليزية"
ENGLISH_HEAD = "الرأس إنجليزي لا رومنة مصرية"
GLYPH_DEFECT = "رمز هيروغليفي واحد مكرر بخلل المسح"
PAGE_MARK = re.compile(r"^<!--\s*صفحة\s+(\d+)\s*-->$")


def bare(value: str, alphabet: str = "") -> str:
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    value = re.sub(r"[\u064b-\u065fـ]", "", value).replace("ٱ", "ا")
    if alphabet == "ar":
        return re.sub(r"[^ء-ي]", "", value)
    if alphabet == "latin":
        return re.sub(r"[^a-zāēīōūḏḥḫḳṣṭṯẖʿꜣꜥ0-9]", "", value)
    return re.sub(r"\s+", "", value)


def similarity(left: str, right: str, alphabet: str = "") -> float:
    left, right = bare(left, alphabet), bare(right, alphabet)
    if not left or not right:
        return 0.0
    return difflib.SequenceMatcher(None, left, right, autojunk=False).ratio()


def located_rows(path: pathlib.Path) -> list[dict[str, Any]]:
    """نسخة موضعية من محلل الحصاد نفسه؛ ينبغي أن تعيد القديم 938 حرفيًا."""
    lines = path.read_text(encoding="utf-8").splitlines()
    pages: list[int | None] = []
    current_page: int | None = None
    for raw in lines:
        marker = PAGE_MARK.match(raw.strip())
        if marker:
            current_page = int(marker.group(1))
        pages.append(current_page)

    stripped = [line.strip() for line in lines]
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for i, line in enumerate(stripped):
        if KH.AR.search(line):
            continue
        match = KH.RX_EG_ENTRY.match(line)
        if not match:
            continue
        foreign = KH.clean(match.group(1))
        glyphs = match.group(2)
        sense = KH.clean(KH.RX_REFS.sub("", match.group(3)))
        if len(foreign) < 2 or len(sense) < 4:
            continue
        for forward in (1, 2, 3):
            if i + forward >= len(stripped):
                break
            answer = KH.RX_EG_ANSWER.match(stripped[i + forward])
            if not answer:
                continue
            root = KH.bare_ar(KH.clean(answer.group(1))).replace("/", "")
            gloss = KH.bare_ar(KH.clean(answer.group(2)))
            if len(re.sub(r"[^ء-ي]", "", root)) < 2:
                break
            key = (foreign, root)
            if key in seen:
                break
            seen.add(key)
            rows.append({
                "foreign": foreign,
                "glyphs": glyphs,
                "foreign_sense": sense[:110],
                "arabic_root": root,
                "arabic_gloss": gloss[:180],
                "source_line": i + 1,
                "answer_line": i + forward + 1,
                "source_page": pages[i],
            })
            break
    return rows


def registered_reasons() -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for path in REPORTS:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload["rows"]:
            index = int(row["index"])
            if index in out:
                raise SystemExit(f"تكرر فهرس مصري في تقارير الدفعات: {index}")
            out[index] = list(row.get("scan_reasons", []))
    if set(out) != set(range(938)):
        raise SystemExit("تقارير الدفعات لا تغطي الفهارس 0..937 مرة واحدة")
    return out


def stored_rows() -> list[dict[str, Any]]:
    payload = json.loads(PAIR_STORE.read_text(encoding="utf-8"))
    rows = [row for row in payload["rows"] if row.get("source") == "ocr-egyptian2"]
    if len(rows) != 938:
        raise SystemExit(f"تغير مقام صفوف المصرية: {len(rows)}، والمتوقع 938")
    return rows


def align(old: list[dict[str, Any]], new: list[dict[str, Any]]) -> list[tuple[int, int, float]]:
    """رصف عالمي رتيب؛ الجذر العربي شرط، والسياق يمنع سرقة المتشابهات."""
    n, m, gap = len(old), len(new), -2.5
    scores = [[0.0] * (m + 1) for _ in range(n + 1)]
    paths = [bytearray(m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        scores[i][0], paths[i][0] = i * gap, 1
    for j in range(1, m + 1):
        scores[0][j], paths[0][j] = j * gap, 2
    pair_scores: dict[tuple[int, int], float] = {}
    for i in range(1, n + 1):
        left = old[i - 1]
        for j in range(1, m + 1):
            right = new[j - 1]
            if bare(left["arabic_root"], "ar") != bare(right["arabic_root"], "ar"):
                match = -14.0
            else:
                page_delta = abs((right.get("source_page") or 0)
                                 - (left.get("source_page") or 0))
                page_bonus = max(0.0, 2.0 - 0.12 * abs(page_delta - 3))
                match = (
                    8.0
                    + 6.0 * similarity(left["arabic_gloss"], right["arabic_gloss"], "ar")
                    + 3.0 * similarity(left["foreign"], right["foreign"], "latin")
                    + 3.0 * similarity(left["foreign_sense"], right["foreign_sense"])
                    + page_bonus
                )
            pair_scores[i - 1, j - 1] = match
            choices = (
                scores[i - 1][j - 1] + match,
                scores[i - 1][j] + gap,
                scores[i][j - 1] + gap,
            )
            choice = max(range(3), key=lambda key: choices[key])
            scores[i][j], paths[i][j] = choices[choice], choice

    aligned: list[tuple[int, int, float]] = []
    i, j = n, m
    while i or j:
        choice = paths[i][j]
        if i and j and choice == 0:
            left, right = old[i - 1], new[j - 1]
            if bare(left["arabic_root"], "ar") == bare(right["arabic_root"], "ar"):
                aligned.append((i - 1, j - 1, pair_scores[i - 1, j - 1]))
            i, j = i - 1, j - 1
        elif i and (not j or choice == 1):
            i -= 1
        else:
            j -= 1
    aligned.reverse()
    return aligned


def reasons_for(row: dict[str, Any]) -> list[str]:
    candidate = {
        "foreign": row["foreign"],
        "foreign_sense": row["foreign_sense"],
        "glyphs": row.get("glyphs", ""),
    }
    return CARDS.scan_defect(candidate)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--old", type=pathlib.Path, default=OLD)
    parser.add_argument("--new", type=pathlib.Path, default=NEW)
    parser.add_argument("--out", type=pathlib.Path, default=OUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    old = located_rows(args.old)
    if len(old) != 938:
        raise SystemExit(f"المحلل الموضعي لم يرد المسح القديم إلى 938 صفًا: {len(old)}")
    stored = stored_rows()
    for index, (source, row) in enumerate(zip(old, stored)):
        for key in ("foreign", "glyphs", "foreign_sense", "arabic_root", "arabic_gloss"):
            if source.get(key, "") != row.get(key, ""):
                raise SystemExit(
                    f"اختل رد الفهرس {index} إلى المسح القديم في {key}: "
                    f"{source.get(key)!r} != {row.get(key)!r}"
                )

    new = located_rows(args.new)
    matches = align(old, new)
    by_old = {i: (j, score) for i, j, score in matches}
    registered = registered_reasons()
    recoveries: list[dict[str, Any]] = []
    field_counts: Counter[str] = Counter()
    for index, left in enumerate(old):
        if index not in by_old:
            continue
        new_index, score = by_old[index]
        right = new[new_index]
        before = registered[index]
        after = reasons_for(right)
        fields: dict[str, dict[str, str]] = {}
        if (SENSE_DEFECT in before and SENSE_DEFECT not in after
                and left["foreign_sense"] != right["foreign_sense"]):
            fields["foreign_sense"] = {
                "legacy": left["foreign_sense"], "recovered": right["foreign_sense"]}
        if (HEAD_DEFECT in before and HEAD_DEFECT not in after
                and ENGLISH_HEAD not in after and left["foreign"] != right["foreign"]):
            fields["foreign"] = {
                "legacy": left["foreign"], "recovered": right["foreign"]}
        if (GLYPH_DEFECT in before and GLYPH_DEFECT not in after
                and left.get("glyphs", "") != right.get("glyphs", "")):
            fields["glyphs"] = {
                "legacy": left.get("glyphs", ""), "recovered": right.get("glyphs", "")}
        # الرأس الإنجليزي بنيوي في الكتاب، فلا يبدل ولو اقترح الرصف غيره.
        if not fields:
            continue
        for field in fields:
            field_counts[field] += 1
        recoveries.append({
            "index": index,
            "arabic_root": left["arabic_root"],
            "registered_scan_reasons": before,
            "new_scan_reasons": after,
            "legacy": {field: spec["legacy"] for field, spec in fields.items()},
            "fields": fields,
            "old_location": {
                "page": left.get("source_page"), "line": left["source_line"]},
            "new_location": {
                "page": right.get("source_page"), "line": right["source_line"]},
            "matched_new_row": new_index,
            "alignment_score": round(score, 6),
        })

    payload = {
        "schema": "khashim-egyptian-ocr-recovery-v1",
        "generated_by": "scripts/recover_khashim_egyptian_ocr.py",
        "book": "علي فهمي خشيم، «البرهان على عروبة اللغة المصرية القديمة»",
        "old_source": "Resources/prior-art/ocr-egyptian2/full.md",
        "new_source": "Resources/prior-art/ocr-khashim-proof-recovery-20260814/full.md",
        "source_pdf_archive_item": "AAlexandrina-067891",
        "old_rows": len(old),
        "new_rows": len(new),
        "aligned_rows": len(matches),
        "restored_unique_rows": len(recoveries),
        "restored_fields": dict(sorted(field_counts.items())),
        "contract": (
            "رصف عالمي رتيب بلا إعادة استعمال؛ الجذر العربي شرط؛ ولا يبدل إلا "
            "حقل يزيل عيبًا مسجلًا؛ الرأس الإنجليزي البنيوي لا يبدل"
        ),
        "recoveries": recoveries,
    }
    print(json.dumps({key: payload[key] for key in (
        "old_rows", "new_rows", "aligned_rows", "restored_unique_rows", "restored_fields")},
        ensure_ascii=False, indent=1))
    if not args.dry_run:
        args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                            encoding="utf-8", newline="\n")
        print(f"كتب: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
