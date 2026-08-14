# -*- coding: utf-8 -*-
"""قابل مسحي «البرهان» رتيبًا، واكتب إصلاحات العيوب المسجلة وحدها.

لا يعيد هذا السكربت حصاد الكتاب من الصفر، ولا يبدل صفًا سليمًا. مقامه هو
الفهارس الـ938 الموجودة في دفعات خشيم المصرية. يرد كل فهرس إلى سطره في
المسح القديم، ثم يرصف عمودي الصفحة في المسح الجديد رصفًا رتيبًا لا يعيد
استعمال صف جديد. ولا يقبل حقلًا جديدًا إلا إذا أزال سببًا مسجلًا في ملفات
الدفعات، وثبتت صفحة الجواب وقرينة شرحه العربي.

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
from collections import Counter, defaultdict
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_khashim_egyptian_cards as CARDS  # noqa: E402
import fan_any_script as FAN  # noqa: E402
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
VISUALLY_VERIFIED_GLYPH_ROWS: set[int] = set()
PAGE_MARK = re.compile(r"^<!--\s*صفحة\s+(\d+)\s*-->$")
LATIN_HEAD = "A-Za-zÀ-ÖØ-öø-ÿĀ-žḀ-ỿꜣꜥʿ"
RX_NEW_ENTRY = re.compile(
    rf"^\s*([{LATIN_HEAD}][{LATIN_HEAD}0-9\-\.\[\]\(\)\?\s]{{1,40}}?)\s*"
    rf"([^{LATIN_HEAD},\n]{{0,2000}})\s*,\s*(.{{2,2000}})$"
)
RX_NEW_ANSWER = re.compile(
    r"^[\s*⊕·•-]*([ء-ي\u064b-\u065fـ][ء-ي\u064b-\u065fـ/.\s]{0,28}?)"
    r"\s*[:：،,]\s*(.{2,2000})$"
)


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


def root_variants(value: str) -> set[str]:
    root = bare(value, "ar")
    variants = {root}
    if root.startswith(("ا", "ء")) and len(root) > 2:
        variants.add(root[1:])
    return {variant for variant in variants if len(variant) >= 2}


def phonetic_score(entry: dict[str, Any], answer: dict[str, Any]) -> int:
    """قرينة رصف لا بوابة حكم: هل يصل الرأس إلى مادة الجواب صوتيًا؟"""
    variants = root_variants(answer["arabic_root"])
    fan = set(FAN.fan(entry["foreign"], "egyptian", limit=400))
    hit = bool(variants & fan)
    ready = any(
        CARDS.sound_audit(entry["foreign"], root)[0] for root in variants
    )
    return (10 if hit else 0) + (6 if ready else 0)


def pair_page(entries: list[dict[str, Any]], answers: list[dict[str, Any]]) -> list[
        dict[str, Any]]:
    """ارصف تسلسل عمود بدج بتسلسل جواب خشيم داخل الصفحة مع فجوات."""
    n, m, gap = len(entries), len(answers), -1.5
    if not n or not m:
        return []
    scores = [[0.0] * (m + 1) for _ in range(n + 1)]
    paths = [bytearray(m + 1) for _ in range(n + 1)]
    pair_scores: dict[tuple[int, int], float] = {}
    for i in range(1, n + 1):
        scores[i][0], paths[i][0] = i * gap, 1
    for j in range(1, m + 1):
        scores[0][j], paths[0][j] = j * gap, 2
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            position = 2.0 * (
                1.0 - abs((i - 0.5) / n - (j - 0.5) / m)
            )
            match = 1.0 + phonetic_score(entries[i - 1], answers[j - 1]) + position
            pair_scores[i - 1, j - 1] = match
            choices = (
                scores[i - 1][j - 1] + match,
                scores[i - 1][j] + gap,
                scores[i][j - 1] + gap,
            )
            choice = max(range(3), key=lambda key: choices[key])
            scores[i][j], paths[i][j] = choices[choice], choice
    paired: list[dict[str, Any]] = []
    i, j = n, m
    while i or j:
        choice = paths[i][j]
        if i and j and choice == 0:
            entry, answer = entries[i - 1], answers[j - 1]
            paired.append({
                **entry,
                "arabic_root": answer["arabic_root"],
                "arabic_gloss": answer["arabic_gloss"],
                "answer_line": answer["answer_line"],
                "layout_pair_score": round(pair_scores[i - 1, j - 1], 6),
                "phonetic_pair_score": phonetic_score(entry, answer),
            })
            i, j = i - 1, j - 1
        elif i and (not j or choice == 1):
            i -= 1
        else:
            j -= 1
    paired.reverse()
    return paired


def layout_rows(path: pathlib.Path) -> list[dict[str, Any]]:
    """اقرأ عمودي الصفحة ولو فصل OCR كتلة بدج عن كتلة أجوبة خشيم."""
    page_blocks: dict[int, list[tuple[int, str]]] = defaultdict(list)
    current_page: int | None = None
    block_start = 0
    block_lines: list[str] = []

    def flush() -> None:
        nonlocal block_lines
        if current_page is not None and block_lines:
            page_blocks[current_page].append((block_start, " ".join(block_lines)))
        block_lines = []

    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        marker = PAGE_MARK.match(line)
        if marker:
            flush()
            current_page = int(marker.group(1))
            continue
        if not line:
            flush()
            continue
        if current_page is None:
            continue
        if not block_lines:
            block_start = line_no
        block_lines.append(line)
    flush()

    pages: dict[int, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: {"entries": [], "answers": []}
    )
    for page, blocks in page_blocks.items():
        for line_no, block in blocks:
            entry = RX_NEW_ENTRY.match(block)
            if entry:
                pages[page]["entries"].append({
                    "foreign": KH.clean(entry.group(1)),
                    "glyphs": entry.group(2).strip(),
                    "foreign_sense": KH.clean(entry.group(3))[:500],
                    "sense_tail_complete": not bool(
                        re.search(r"[,\-]\s*$", entry.group(3).strip())
                    ),
                    "source_line": line_no,
                    "source_page": page,
                })
            answer = RX_NEW_ANSWER.match(block)
            if answer:
                pages[page]["answers"].append({
                    "arabic_root": KH.bare_ar(KH.clean(answer.group(1)))
                    .replace("/", "").replace(".", ""),
                    "arabic_gloss": KH.bare_ar(KH.clean(answer.group(2)))[:500],
                    "answer_line": line_no,
                })
    rows: list[dict[str, Any]] = []
    for page in sorted(pages):
        rows.extend(pair_page(pages[page]["entries"], pages[page]["answers"]))
    return rows


def align_local(old: list[dict[str, Any]], new: list[dict[str, Any]]) -> list[
        tuple[int, int, float]]:
    """رصف رتيب في نافذة الصفحة المتناظرة، بلا إعادة استعمال."""
    candidates: dict[str, list[int]] = defaultdict(list)
    for new_index, row in enumerate(new):
        candidates[bare(row["arabic_root"], "ar")].append(new_index)
    used: set[int] = set()
    aligned: list[tuple[int, int, float]] = []
    last_new_line = -1
    for old_index, left in enumerate(old):
        expected_page = (left.get("source_page") or 0) + 3
        options: list[tuple[float, int]] = []
        for new_index in candidates.get(bare(left["arabic_root"], "ar"), []):
            if new_index in used:
                continue
            right = new[new_index]
            if right["source_line"] <= last_new_line:
                continue
            page_distance = abs((right.get("source_page") or 0) - expected_page)
            if page_distance > 2:
                continue
            score = (
                12.0
                + 7.0 * similarity(left["arabic_gloss"], right["arabic_gloss"], "ar")
                + 3.0 * similarity(left["foreign"], right["foreign"], "latin")
                + 3.0 * similarity(left["foreign_sense"], right["foreign_sense"])
                + float(right.get("phonetic_pair_score", 0))
                + max(0.0, 3.0 - page_distance)
            )
            options.append((score, new_index))
        if not options:
            continue
        score, new_index = max(options)
        used.add(new_index)
        last_new_line = new[new_index]["source_line"]
        aligned.append((old_index, new_index, score))
    return aligned


def registered_reasons() -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for path in REPORTS:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload["rows"]:
            index = int(row["index"])
            if index in out:
                raise SystemExit(f"تكرر فهرس مصري في تقارير الدفعات: {index}")
            recovery = row.get("ocr_recovery") or {}
            out[index] = list(
                recovery.get("registered_scan_reasons", row.get("scan_reasons", []))
            )
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
        legacy = row.get("legacy") or {}
        for key in ("foreign", "glyphs", "foreign_sense", "arabic_root", "arabic_gloss"):
            stored_value = legacy.get(key, row.get(key, ""))
            if source.get(key, "") != stored_value:
                raise SystemExit(
                    f"اختل رد الفهرس {index} إلى المسح القديم في {key}: "
                    f"{source.get(key)!r} != {stored_value!r}"
                )

    if args.new.resolve() == args.old.resolve():
        # شاهد الضبط: لا ينبغي للمحلل القديم نفسه أن يقترح استردادًا.
        new = located_rows(args.new)
        matches = align(old, new)
        parser = "direct-control"
    else:
        new = layout_rows(args.new)
        matches = align_local(old, new)
        parser = "page-column-layout"
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
        foreign_similarity = similarity(left["foreign"], right["foreign"], "latin")
        sense_similarity = similarity(left["foreign_sense"], right["foreign_sense"])
        gloss_similarity = similarity(
            left["arabic_gloss"], right["arabic_gloss"], "ar"
        )
        page_delta = (
            (right.get("source_page") or 0) - (left.get("source_page") or 0)
        )
        phonetic = int(right.get("phonetic_pair_score", 0))
        same_row_anchor = page_delta == 3 and gloss_similarity >= 0.8
        recovered_head = False
        if (HEAD_DEFECT in before and ENGLISH_HEAD not in before
                and HEAD_DEFECT not in after
                and ENGLISH_HEAD not in after and left["foreign"] != right["foreign"]
                and same_row_anchor
                and (phonetic >= 6
                     or (foreign_similarity >= 0.8
                         and left["foreign"].casefold().startswith(
                             right["foreign"].casefold()
                         )))):
            fields["foreign"] = {
                "legacy": left["foreign"], "recovered": right["foreign"]}
            recovered_head = True
        sense_complete = (
            len(re.findall(r"[A-Za-z]", right["foreign_sense"])) >= 8
            and bool(right.get("sense_tail_complete", True))
        )
        if (SENSE_DEFECT in before and SENSE_DEFECT not in after
                and left["foreign_sense"] != right["foreign_sense"]
                and same_row_anchor and sense_complete
                and (foreign_similarity >= 0.7 or recovered_head)):
            fields["foreign_sense"] = {
                "legacy": left["foreign_sense"], "recovered": right["foreign_sense"]}
        new_glyphs = CARDS.glyph_chars(right.get("glyphs", ""))
        if (GLYPH_DEFECT in before and GLYPH_DEFECT not in after
                and left.get("glyphs", "") != right.get("glyphs", "")
                and index in VISUALLY_VERIFIED_GLYPH_ROWS
                and same_row_anchor and foreign_similarity >= 0.75
                and sense_similarity >= 0.6 and len(set(new_glyphs)) >= 2):
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
            "alignment_evidence": {
                "foreign_similarity": round(foreign_similarity, 6),
                "sense_similarity": round(sense_similarity, 6),
                "arabic_gloss_similarity": round(gloss_similarity, 6),
                "page_delta": page_delta,
                "layout_pair_score": right.get("layout_pair_score"),
                "phonetic_pair_score": phonetic,
            },
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
        "new_parser": parser,
        "restored_unique_rows": len(recoveries),
        "restored_fields": dict(sorted(field_counts.items())),
        "contract": (
            "رصف عمودي رتيب داخل الصفحة بلا إعادة استعمال؛ الجذر والشرح "
            "العربيان مرساتان؛ ولا يبدل إلا حقل يزيل عيبًا مسجلًا؛ الرأس "
            "الإنجليزي البنيوي والرمز غير المتحقق بصريًا لا يبدلان"
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
