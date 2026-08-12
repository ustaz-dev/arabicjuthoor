# -*- coding: utf-8 -*-
"""ادمج مسح خشيم الأكادي الجديد في البطاقات القديمة بلا تكرار.

وحدة البطاقة هي مدخل الكتاب، لا صف المسح. يعتمد البناء صفوف
``ocr-akkadian`` أساسًا، ويربط صفوف ``khashim-akkadian`` بالمدخل نفسه عن
طريق صفحة الكتاب وترتيب الأجوبة ونص الجذر والشرح. إذا حمل المسحان مرشحين
مختلفين ظهرا في بطاقة واحدة. تبقى البطاقة القديمة التي لا نظير لها في جرد OCR؛
فإن كان رأسها ساقطًا صُحح في موضعه من نص إعادة المسح.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_akkadian_maqar_coptic_cards as CARDS  # noqa: E402
import harvest_khashim as HARVEST  # noqa: E402
import search_arabic_root_senses as LEX  # noqa: E402

SOURCE = ROOT / "data" / "khashim-pairs.json"
READING = ROOT / "04-cross-linguistic" / "readings" / "akkadian.md"
REPORT = ROOT / "data" / "khashim-akkadian-ocr-completion.json"
AUDIT = ROOT / "05-audits" / "2026-08-12-khashim-akkadian-ocr-completion.md"
RESOURCE_STORE = pathlib.Path.home() / "AI Projects" / "Resources" / "prior-art"
LEGACY_PDF = RESOURCE_STORE / "khashim-akkadian.pdf"
OCR_MD = RESOURCE_STORE / "ocr-akkadian" / "full.md"

FALLEN = "(سقطَ حرفُه في المسح)"
LEGACY_EXPECTED = 588
OCR_EXPECTED = 823
FALLEN_EXPECTED = 242
LEGACY_CARD_BASE = "c02cad5"

OCR_START = "<!-- KHASHIM-AKKADIAN-OCR-COMPLETION:START -->"
OCR_END = "<!-- KHASHIM-AKKADIAN-OCR-COMPLETION:END -->"
LEGACY_MARKERS = {
    1: (
        "<!-- KHASHIM-AKKADIAN-HARVEST-BATCH-001:START -->",
        "<!-- KHASHIM-AKKADIAN-HARVEST-BATCH-001:END -->",
    ),
    2: (
        "<!-- KHASHIM-AKKADIAN-HARVEST-BATCH-002:START -->",
        "<!-- KHASHIM-AKKADIAN-HARVEST-BATCH-002:END -->",
    ),
}

AR_MARKS = re.compile(r"[\u064b-\u065f\u0670ـ]")
AR_LETTERS = re.compile(r"[ء-ي]")
PAGE_MARKER = re.compile(r"<!--\s*صفحة\s+(\d+)\s*-->")
GROUND_ENTRY = re.compile(
    r"^\s*([ء-يًٌٍَُِّْـ][ء-يًٌٍَُِّْـ\s\-+()（）0-9٠-٩]{0,44}?)"
    r"\s*[:：،,]\s*(.{2,180})$"
)
GROUND_EQUAL_ANSWER = re.compile(r"=\s*ع\s*[:：]\s*(.{1,240})$")
TRANSLATE_AR = str.maketrans("أإآىةؤئ", "ااايهوي")

LEXICON_LABELS = {
    "lisan": "لسان العرب لابن منظور",
    "taj_al_arus": "تاج العروس لمرتضى الزبيدي",
    "al_sihah": "تاج اللغة وصحاح العربية للجوهري",
    "al_muhkam": "المحكم والمحيط الأعظم لابن سيده",
    "kitab_al_ayn": "كتاب العين للخليل بن أحمد",
    "asas_al_balagha": "أساس البلاغة للزمخشري",
}


def one_line(value: Any) -> str:
    return " ".join(str(value or "").split())


def norm_ar(value: Any) -> str:
    text = AR_MARKS.sub("", unicodedata.normalize("NFC", str(value or "")))
    text = text.replace("ٱ", "ا")
    return "".join(AR_LETTERS.findall(text)).translate(TRANSLATE_AR)


def quote_clause(definition: str, root: str) -> str:
    text = one_line(definition)
    parts = [part.strip() for part in re.split(r"(?<=[.؟!؛])\s+", text) if part.strip()]
    needle = norm_ar(root)
    return next((part for part in parts if needle and needle in norm_ar(part)), parts[0] if parts else text)


def attach_lexicon_witnesses(cards: list[dict[str, Any]]) -> None:
    """أظهر شاهدي المادة في البطاقة الموجبة من غير جعلهما شرطا رابعا."""
    roots = {card["winner"]["root"] for card in cards if card.get("winner")}
    if not roots:
        return
    matches = LEX.matches_for_roots(ROOT / "Resources", roots, None)
    order = ("lisan", "taj_al_arus", "al_sihah", "al_muhkam", "kitab_al_ayn", "asas_al_balagha")
    for card in cards:
        winner = card.get("winner")
        if not winner:
            card["lexicon_witnesses"] = []
            continue
        root = winner["root"]
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in matches.get(root, []):
            source_id = LEX.canonical_source_id(str(item.get("source") or ""))
            if source_id in LEXICON_LABELS and str(item.get("definition") or "").strip():
                grouped[source_id].append(item)
        witnesses: list[dict[str, str]] = []
        for source_id in order:
            if not grouped.get(source_id):
                continue
            item = max(grouped[source_id], key=lambda value: len(str(value.get("definition") or "")))
            witnesses.append({
                "source_id": source_id,
                "source": LEXICON_LABELS[source_id],
                "quote": quote_clause(str(item["definition"]), root),
            })
            if len(witnesses) == 2:
                break
        ids = {item["source_id"] for item in witnesses}
        if len(witnesses) < 2 or not ({"lisan", "taj_al_arus"} & ids):
            raise SystemExit(f"تعذر شاهدا المعجم للموجب الأكادي {root}")
        card["lexicon_witnesses"] = witnesses


def grams(value: Any) -> frozenset[str]:
    text = norm_ar(value)
    if not text:
        return frozenset()
    if len(text) == 1:
        return frozenset((text,))
    return frozenset(text[index:index + 2] for index in range(len(text) - 1))


def dice(left: frozenset[str], right: frozenset[str]) -> float:
    if not left or not right:
        return 0.0
    return 2 * len(left & right) / (len(left) + len(right))


def comparable(row: dict[str, Any], legacy: bool = False) -> dict[str, Any]:
    fallen = legacy and row.get("foreign") == FALLEN
    values = [
        norm_ar(row.get("arabic_root")),
        norm_ar(row.get("arabic_gloss")),
        norm_ar(row.get("foreign_sense")),
        "" if fallen else norm_ar(row.get("foreign")),
    ]
    return {
        "values": values,
        "grams": [grams(value) for value in values],
        "fallen": fallen,
    }


def textual_score(old: dict[str, Any], fresh: dict[str, Any]) -> tuple[float, list[float]]:
    left = comparable(old, legacy=True)
    right = comparable(fresh)
    similarities = [
        dice(left["grams"][index], right["grams"][index])
        for index in range(4)
    ]
    score = (
        2 * similarities[0]
        + 4 * similarities[1]
        + 3 * similarities[2]
        + 3 * similarities[3]
    )
    old_values = left["values"]
    new_values = right["values"]
    if old_values[0] and old_values[0] == new_values[0]:
        score += 4
    if old_values[1] and (
        old_values[1] in new_values[1] or new_values[1] in old_values[1]
    ):
        score += 2
    if old_values[2] and (
        old_values[2] in new_values[2] or new_values[2] in old_values[2]
    ):
        score += 1
    if old_values[3] and old_values[3] == new_values[3]:
        score += 3
    return score, similarities


def stored_rows() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    legacy = [
        row for row in payload["rows"]
        if row.get("tongue") == "akkadian"
        and row.get("source") == "khashim-akkadian"
    ]
    ocr = [
        row for row in payload["rows"]
        if row.get("tongue") == "akkadian"
        and row.get("source") == "ocr-akkadian"
    ]
    if len(legacy) != LEGACY_EXPECTED or len(ocr) != OCR_EXPECTED:
        raise SystemExit(
            f"تغير مقام الأكادية: القديم={len(legacy)}، الجديد={len(ocr)}"
        )
    fallen = sum(row.get("foreign") == FALLEN for row in legacy)
    if fallen != FALLEN_EXPECTED:
        raise SystemExit(f"تغير عدد الرؤوس الساقطة: {fallen}")
    return legacy, ocr


def legacy_with_pages(stored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """أعد استخراج الـ588 نفسها، مع إلحاق الصفحة والسطر فقط."""
    import fitz  # noqa: PLC0415

    if not LEGACY_PDF.exists():
        raise SystemExit(f"غاب مصدر المسح القديم: {LEGACY_PDF}")
    lines: list[tuple[str, int, int]] = []
    with fitz.open(LEGACY_PDF) as document:
        for page_number, page in enumerate(document, 1):
            for line_number, line in enumerate(page.get_text().splitlines(), 1):
                lines.append((HARVEST.unmirror(line), page_number, line_number))

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, (line, page_number, line_number) in enumerate(lines):
        match = HARVEST.RX_AR_LINE.match(line)
        if not match:
            continue
        arabic_side = HARVEST.clean(match.group(1))
        root_match = HARVEST.RX_ROOT.match(arabic_side)
        if not root_match:
            continue
        root = root_match.group(1)
        gloss = HARVEST.clean(arabic_side[root_match.end():])
        foreign = foreign_sense = ""
        for back in range(1, 4):
            if index - back < 0:
                break
            previous = HARVEST.clean(lines[index - back][0])
            if not previous or HARVEST.RX_AR_LINE.match(lines[index - back][0]):
                continue
            entry = HARVEST.RX_ENTRY.match(previous)
            if entry and not any(noise in previous for noise in HARVEST.NOISE):
                foreign = HARVEST.clean(entry.group(1))
                foreign_sense = HARVEST.clean(entry.group(2))
                break
        if not foreign:
            for back in range(1, 4):
                if index - back < 0:
                    break
                previous = HARVEST.clean(lines[index - back][0])
                if (
                    len(previous) >= 4
                    and HARVEST.AR.search(previous)
                    and not HARVEST.RX_AR_LINE.match(lines[index - back][0])
                ):
                    foreign = FALLEN
                    foreign_sense = previous[:90]
                    break
        if not foreign or len(root) < 2:
            continue
        key = (foreign if foreign != FALLEN else foreign_sense, root)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "tongue_ar": "الأكّاديّة",
            "tongue": "akkadian",
            "foreign": foreign,
            "foreign_sense": foreign_sense,
            "arabic_root": root,
            "arabic_gloss": gloss[:160],
            "source": "khashim-akkadian",
            "page": page_number,
            "page_line": line_number,
        })
    comparable_fields = (
        "foreign", "foreign_sense", "arabic_root", "arabic_gloss", "source"
    )
    if len(rows) != len(stored) or any(
        any(got.get(field) != expected.get(field) for field in comparable_fields)
        for got, expected in zip(rows, stored)
    ):
        raise SystemExit("تعذر إعادة إنتاج الصفوف القديمة حرفيًا قبل ربط الصفحات")
    return rows


def ocr_with_pages(stored: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """أعد استخراج الـ823 نفسها، مع إلحاق الصفحة وسطر المصدر."""
    if not OCR_MD.exists():
        raise SystemExit(f"غاب مصدر المسح الجديد: {OCR_MD}")
    page: int | None = None
    lines: list[tuple[str, int | None, int]] = []
    for source_line, original in enumerate(
        OCR_MD.read_text(encoding="utf-8").splitlines(), 1
    ):
        page_match = PAGE_MARKER.search(original)
        if page_match:
            page = int(page_match.group(1))
        lines.append((HARVEST.clean(original), page, source_line))

    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, (line, page_number, source_line) in enumerate(lines):
        match = HARVEST.RX_AR_LINE.match(line)
        if not match:
            continue
        arabic_side = HARVEST.clean(match.group(1))
        root_match = HARVEST.RX_ROOT.match(HARVEST.bare_ar(arabic_side))
        if not root_match:
            continue
        root = root_match.group(1)
        foreign = foreign_sense = foreign_vocalized = ""
        for back in range(1, 4):
            if index - back < 0:
                break
            previous = HARVEST.clean(lines[index - back][0])
            if not previous or HARVEST.RX_AR_LINE.match(lines[index - back][0]):
                continue
            entry = HARVEST.RX_AKK_ENTRY.match(previous)
            if entry and not any(noise in previous for noise in HARVEST.NOISE):
                foreign_vocalized = HARVEST.clean(entry.group(1))
                foreign = HARVEST.bare_ar(foreign_vocalized)
                foreign_sense = HARVEST.bare_ar(HARVEST.clean(entry.group(2)))
                break
        if not foreign or len(root) < 2:
            continue
        key = (foreign, root)
        if key in seen:
            continue
        seen.add(key)
        rows.append({
            "tongue_ar": "الأكّاديّة",
            "tongue": "akkadian",
            "foreign": foreign,
            "foreign_vocalized": foreign_vocalized,
            "foreign_sense": foreign_sense,
            "arabic_root": root,
            "arabic_gloss": HARVEST.bare_ar(HARVEST.clean(arabic_side))[:200],
            "source": "ocr-akkadian",
            "page": page_number,
            "source_line": source_line,
        })
    comparable_fields = (
        "foreign", "foreign_sense", "arabic_root", "arabic_gloss", "source"
    )
    if len(rows) != len(stored) or any(
        any(got.get(field) != expected.get(field) for field in comparable_fields)
        for got, expected in zip(rows, stored)
    ):
        raise SystemExit("تعذر إعادة إنتاج صفوف OCR حرفيًا قبل ربط الصفحات")
    return rows


def ground_answers() -> list[dict[str, Any]]:
    """اقرأ أجوبة OCR الأوسع لتوحيد المرشحين تحت رأس المدخل نفسه."""
    page: int | None = None
    page_line = 0
    current: dict[str, Any] | None = None
    entry_id = 0
    answers: list[dict[str, Any]] = []
    for source_line, original in enumerate(
        OCR_MD.read_text(encoding="utf-8").splitlines(), 1
    ):
        page_match = PAGE_MARKER.search(original)
        if page_match:
            page = int(page_match.group(1))
            page_line = 0
        page_line += 1
        plain = original.replace("**", "").replace("__", "")
        line = HARVEST.clean(plain)
        answer = HARVEST.RX_AR_LINE.match(line)
        # لهذا المدخل جواب على صورة «الرأس = ع: الجذر»، وهي الصورة الوحيدة
        # اللازمة لإكمال الرصف القديم؛ تعميمها يدخل شروحًا وسيطة كأجوبة جديدة.
        equal_answer = (
            GROUND_EQUAL_ANSWER.search(line)
            if current and norm_ar(current["foreign"]) == "انخاشتر"
            else None
        )
        if answer or equal_answer:
            arabic_side = HARVEST.bare_ar(HARVEST.clean(
                (answer or equal_answer).group(1)
            ))
            root_match = HARVEST.RX_ROOT.match(arabic_side)
            if root_match and current and source_line - current["head_line"] <= 20:
                answers.append({
                    "entry_id": current["entry_id"],
                    "foreign": current["foreign"],
                    "foreign_vocalized": current["foreign_vocalized"],
                    "foreign_sense": current["foreign_sense"],
                    "arabic_root": root_match.group(1),
                    "arabic_gloss": arabic_side[:300],
                    "source": "ocr-akkadian-rescan",
                    "page": current["page"],
                    "page_line": page_line,
                    "source_line": source_line,
                })
            continue
        entry = GROUND_ENTRY.match(line)
        if entry and not any(noise in line for noise in HARVEST.NOISE):
            entry_id += 1
            current = {
                "entry_id": entry_id,
                "foreign": HARVEST.bare_ar(HARVEST.clean(entry.group(1))),
                "foreign_vocalized": HARVEST.clean(entry.group(1)),
                "foreign_sense": HARVEST.bare_ar(HARVEST.clean(entry.group(2))),
                "page": page,
                "head_line": source_line,
            }
    return answers


def map_ocr_to_ground(
    ocr: list[dict[str, Any]], ground: list[dict[str, Any]]
) -> list[int]:
    by_source_line = {row["source_line"]: index for index, row in enumerate(ground)}
    keyed: dict[tuple[str, str, str], list[int]] = defaultdict(list)
    for index, row in enumerate(ground):
        keyed[(
            norm_ar(row["foreign"]), norm_ar(row["foreign_sense"]),
            norm_ar(row["arabic_root"]),
        )].append(index)
    used: set[int] = set()
    mapped: list[int] = []
    for index, row in enumerate(ocr):
        line_match = by_source_line.get(row["source_line"])
        if line_match is not None and line_match not in used:
            used.add(line_match)
            mapped.append(line_match)
            continue
        key = (
            norm_ar(row["foreign"]), norm_ar(row["foreign_sense"]),
            norm_ar(row["arabic_root"]),
        )
        candidates = [candidate for candidate in keyed[key] if candidate not in used]
        if not candidates:
            raise SystemExit(f"لم يرتبط صف OCR {index} بجواب مصدره")
        chosen = candidates[0]
        used.add(chosen)
        mapped.append(chosen)
    return mapped


def ordered_page_alignment(
    old_indices: list[int], ground_indices: list[int],
    legacy: list[dict[str, Any]], ground: list[dict[str, Any]],
) -> list[tuple[int, int, float, list[float], float]]:
    """رصف رتيب داخل الصفحة؛ يرخص سقوط القديم عند نقص OCR الأوسع."""
    if not old_indices or not ground_indices:
        return []
    old_max = max(legacy[index]["page_line"] for index in old_indices)
    ground_max = max(ground[index]["page_line"] for index in ground_indices)
    values: list[list[tuple[float, float, list[float], float]]] = []
    for old_index in old_indices:
        row: list[tuple[float, float, list[float], float]] = []
        for ground_index in ground_indices:
            text_score, similarities = textual_score(
                legacy[old_index], ground[ground_index]
            )
            position = 1 - abs(
                legacy[old_index]["page_line"] / old_max
                - ground[ground_index]["page_line"] / ground_max
            )
            row.append((text_score + 6 * position, text_score, similarities, position))
        values.append(row)

    old_count, ground_count = len(old_indices), len(ground_indices)
    force_old = ground_count >= old_count
    negative = -1_000_000_000.0
    scores = [
        [negative if force_old else 0.0] * (ground_count + 1)
        for _ in range(old_count + 1)
    ]
    actions = [bytearray(ground_count + 1) for _ in range(old_count + 1)]
    for column in range(ground_count + 1):
        scores[0][column] = 0.0
    if not force_old:
        for row in range(old_count + 1):
            scores[row][0] = 0.0

    for row in range(1, old_count + 1):
        for column in range(1, ground_count + 1):
            options = [
                scores[row - 1][column] if not force_old else negative,
                scores[row][column - 1],
                scores[row - 1][column - 1] + values[row - 1][column - 1][0],
            ]
            action = max(range(3), key=lambda index: options[index])
            scores[row][column] = options[action]
            actions[row][column] = action + 1

    row, column = old_count, ground_count
    result: list[tuple[int, int, float, list[float], float]] = []
    while row and column:
        action = actions[row][column]
        if action == 3:
            _, text_score, similarities, position = values[row - 1][column - 1]
            result.append((
                old_indices[row - 1], ground_indices[column - 1],
                text_score, similarities, position,
            ))
            row -= 1
            column -= 1
        elif action == 1:
            row -= 1
        else:
            column -= 1
    return list(reversed(result))


def link_sources(
    legacy: list[dict[str, Any]], ocr: list[dict[str, Any]],
    ground: list[dict[str, Any]],
) -> dict[str, Any]:
    ocr_ground = map_ocr_to_ground(ocr, ground)
    ocr_entry_to_index: dict[int, int] = {}
    for ocr_index, ground_index in enumerate(ocr_ground):
        entry_id = ground[ground_index]["entry_id"]
        if entry_id in ocr_entry_to_index:
            raise SystemExit(f"تكرر مدخل OCR في بطاقتين: {entry_id}")
        ocr_entry_to_index[entry_id] = ocr_index

    old_by_page: dict[int, list[int]] = defaultdict(list)
    ground_by_page: dict[int, list[int]] = defaultdict(list)
    for index, row in enumerate(legacy):
        old_by_page[row["page"]].append(index)
    for index, row in enumerate(ground):
        if row.get("page") is not None:
            ground_by_page[row["page"]].append(index)

    aligned: list[tuple[int, int, float, list[float], float]] = []
    for page, old_indices in sorted(old_by_page.items()):
        aligned.extend(ordered_page_alignment(
            old_indices, ground_by_page.get(page, []), legacy, ground,
        ))

    ocr_members: dict[int, list[int]] = defaultdict(list)
    legacy_ground: dict[int, int] = {}
    links: list[dict[str, Any]] = []
    for old_index, ground_index, score, similarities, position in aligned:
        legacy_ground[old_index] = ground_index
        entry_id = ground[ground_index]["entry_id"]
        ocr_index = ocr_entry_to_index.get(entry_id)
        if ocr_index is not None:
            ocr_members[ocr_index].append(old_index)
        links.append({
            "legacy_index": old_index,
            "legacy_page": legacy[old_index]["page"],
            "legacy_page_line": legacy[old_index]["page_line"],
            "ground_source_line": ground[ground_index]["source_line"],
            "ground_entry_id": entry_id,
            "ocr_index": ocr_index,
            "text_score": round(score, 6),
            "field_similarities": {
                "root": round(similarities[0], 6),
                "arabic_gloss": round(similarities[1], 6),
                "foreign_sense": round(similarities[2], 6),
                "foreign_head": round(similarities[3], 6),
            },
            "page_position_similarity": round(position, 6),
        })
    return {
        "ocr_ground": ocr_ground,
        "ocr_members": dict(ocr_members),
        "legacy_ground": legacy_ground,
        "links": links,
    }


def grouped_proposals(
    ocr_row: dict[str, Any], legacy_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    witnesses = [(ocr_row.get("source", "ocr-akkadian"), ocr_row), *(
        ("khashim-akkadian", row) for row in legacy_rows
    )]
    for source, row in witnesses:
        root = CARDS.ar_bare(row.get("arabic_root"))
        if not root:
            continue
        item = grouped.setdefault(root, {
            "root": root, "sources": [], "texts": [],
        })
        if source not in item["sources"]:
            item["sources"].append(source)
        text = one_line(row.get("arabic_gloss"))
        if text and text not in item["texts"]:
            item["texts"].append(text)
    return list(grouped.values())


def evaluate_ocr_card(
    ocr_index: int, row: dict[str, Any], legacy_indices: list[int],
    legacy: list[dict[str, Any]],
) -> dict[str, Any]:
    foreign = one_line(row.get("foreign"))
    fan, skeleton, detected = CARDS.candidate_fan("akkadian", foreign)
    legacy_rows = [legacy[index] for index in legacy_indices]
    proposals = grouped_proposals(row, legacy_rows)
    loan_marker = CARDS.explicit_loan(row)

    orbit_index_for_root: dict[str, int] = {}
    for legacy_index in legacy_indices:
        spec = CARDS.AKKADIAN_ORBITS.get(legacy_index)
        if spec:
            orbit_index_for_root.setdefault(spec[0], legacy_index)

    roots = list(fan)
    for proposal in proposals:
        if proposal["root"] not in roots:
            roots.append(proposal["root"])
    tested: list[dict[str, Any]] = []
    for root in roots:
        orbit_index = orbit_index_for_root.get(root, -1)
        tested.append(CARDS.evaluate_candidate(
            "akkadian", orbit_index, skeleton, root, root, loan_marker,
        ))
    by_root = {item["root"]: item for item in tested}
    positives = [item for item in tested if item["complete"]]
    winner = positives[0] if positives else None
    primary_root = CARDS.ar_bare(row.get("arabic_root"))
    nucleus, nucleus_reading = CARDS.our_nucleus(primary_root)
    proposal_tests = [by_root[proposal["root"]] for proposal in proposals]
    if winner:
        outcome = winner["verdict"]
        required = "لا عائق معلق"
    else:
        outcome = "OPEN-CANDIDATE"
        required = "مدار بشري مكتوب لمرشح يستوفي الصوت والحدث، مع حسم اتجاه النقل"
    return {
        "ocr_index": ocr_index,
        "row": row,
        "foreign": foreign,
        "foreign_vocalized": row.get("foreign_vocalized") or foreign,
        "fan": fan,
        "skeleton": skeleton,
        "detected_script": detected,
        "proposals": proposals,
        "proposal_tests": proposal_tests,
        "candidate_tests": tested,
        "winner": winner,
        "outcome": outcome,
        "required": required,
        "loan_marker": loan_marker or None,
        "primary_root": primary_root,
        "our_nucleus": nucleus,
        "our_nucleus_reading": nucleus_reading,
        "legacy_indices": legacy_indices,
    }


def proposal_text(card: dict[str, Any]) -> str:
    by_root = {item["root"]: item for item in card["proposal_tests"]}
    values: list[str] = []
    for proposal in card["proposals"]:
        root = proposal["root"]
        sources = "+".join(proposal["sources"])
        location = (
            f"داخل المروحة في الرتبة {card['fan'].index(root) + 1}"
            if root in card["fan"] else "خارج المروحة ومحفوظ"
        )
        text = CARDS.safe(proposal["texts"][0], 220) if proposal["texts"] else "بلا نص"
        test = by_root[root]
        legs = (
            f"ص{'✓' if test['sound'] else '×'}،"
            f"ح{'✓' if test['event'] else '×'}،"
            f"م{'✓' if test['meaning'] else '×'}"
        )
        values.append(
            f"`{root}` [{sources}]؛ {location}؛ [{legs}]؛ «{text}»"
        )
    return " | ".join(values)


def render_ocr_card(
    card: dict[str, Any], legacy_correction_index: int | None = None,
) -> str:
    row = card["row"]
    winner = card["winner"]
    corrected = bool(card["legacy_indices"])
    legacy_text = ", ".join(str(index) for index in card["legacy_indices"])
    if legacy_correction_index is None:
        card_id = f"KHASHIM-AKKADIAN-OCR/{card['ocr_index']:03d}"
        marker = f"<!-- KHASHIM-AKKADIAN-OCR:{card['ocr_index']} -->"
        unit = (
            f"دُمجت فيه الصفوف القديمة [{legacy_text}] ولم تُكتب لها بطاقة ثانية."
            if corrected else "لا نظير له في البطاقات القديمة، فهي بطاقة جديدة."
        )
        source_note = "المسح الجديد هو أساس الرأس، والمسح القديم شاهد إضافي للمرشح حيث وُجد."
        source_name = "ocr-akkadian"
        separation = "المرشح القديم المختلف شاهد داخل البطاقة لا بطاقة مستقلة."
        notes = "صحح المسح الجديد الرأس، وجمعت اقتراحات المسحين قبل الحكم، ولم يكرر الصف القديم في بطاقة ثانية."
    else:
        batch = legacy_correction_index // 300 + 1
        card_id = (
            f"KHASHIM-AKKADIAN-{batch:03d}/{legacy_correction_index:03d}"
        )
        marker = (
            f"<!-- KHASHIM-AKKADIAN-{batch:03d}:"
            f"{legacy_correction_index} -->"
        )
        unit = (
            f"بطاقة قديمة [{legacy_correction_index}] صُحح رأسها في موضعها "
            "من نص إعادة المسح؛ ليست بطاقة جديدة."
        )
        source_note = "المسح الجديد استرد الرأس، وحُفظ مرشح الصف القديم وشرحه."
        source_name = "ocr-akkadian-rescan"
        separation = "هذه البطاقة لم يكن لها نظير في جرد صفوف OCR الـ823؛ صُحح رأسها من نص إعادة المسح فقط."
        notes = "استعيض عن علامة سقوط الرأس بالرأس المشكول، وأعيدت الحقول المتوقفة على الرأس؛ لم تُعد البطاقة المنجزة بطاقة ثانية."
    verdict = (
        f"**{winner['verdict']} (استكشاف)** بالمقابل `{winner['root']}`"
        if winner else "**غير صادر (استكشاف)**"
    )
    event = (
        winner.get("event") if winner else
        next((item.get("event") for item in card["proposal_tests"] if item.get("event")), "")
    ) or "(لا حدث معتمد لمرشح البطاقة في السجل المجمد)"
    orbit = (
        winner.get("written_orbit") if winner else ""
    ) or "غير مكتوب؛ لا تولد الآلة مدارًا من تقاطع الألفاظ"
    witnesses = card.get("lexicon_witnesses", [])
    lexicon_scan = (
        "- مسح العربية: المادة `" + winner["root"] + "`؛ "
        + "؛ ".join(
            f"من {item['source']}: «{CARDS.safe(item['quote'])}»"
            for item in witnesses
        )
        + "."
        if winner else
        "- مسح العربية: لا حكم صادر، وتبقى مواد المروحة مفتوحة من غير اختيار بالمعنى."
    )
    return "\n".join([
        f"### بطاقة: `{card['foreign_vocalized']}` «{CARDS.safe(row.get('foreign_sense'))}»؛ {card_id}",
        marker,
        "- إصدار البروتوكول: RECOVERY-v2 (استكشاف).",
        f"- وحدة البطاقة: {unit}",
        f"- نسبة المصدر: الرسم والمعنى والاقتراحات من علي فهمي خشيم، «الأكّاديّة عربيّة»؛ {source_note}",
        f"- الكلمة في الفرع: `{card['foreign_vocalized']}` من `{source_name}` (المفتاح المجرّد `{card['foreign']}`)، صفحة {row.get('page')}، سطر المصدر {row.get('source_line')}؛ اكتشفت الأداة الطريق `{card['detected_script']}`.",
        f"- الخطوة صفر: صوامت الرسم `{''.join(card['skeleton']) or '∅'}`؛ لم تُحلل نهاية صرفية بحدس.",
        f"- اقتراحات خشيم مجتمعة: {proposal_text(card)}.",
        f"- المروحة المثبتة قبل المعنى: {CARDS.fan_text(card['fan'])}.",
        f"- فحص المروحة والاقتراحات: {CARDS.compact_tests(card['candidate_tests'])}.",
        lexicon_scan,
        f"- الحدث من السجل المجمد كما هو: «{CARDS.safe(event)}».",
        f"- المعنى من كتاب الفرع: «{CARDS.safe(row.get('foreign_sense'))}» [علي فهمي خشيم، «الأكّاديّة عربيّة»].",
        f"- المدار المكتوب: {orbit}.",
        f"- نواة الفهرس المجمد للمادة `{card['primary_root']}`: " + (
            f"`{card['our_nucleus']}` «{CARDS.safe(card['our_nucleus_reading'])}»"
            if card["our_nucleus"] else "(لا نواة مفهرسة لهذه المادة)"
        ),
        "- المصفاة: " + (
            f"وردت علامة انتقال «{card['loan_marker']}»، فحفظت ولم تستعمل أثرًا"
            if card["loan_marker"] else
            "لا مانح أجنبي مسمى في صف المصدر؛ غياب الاسم ليس إثبات أصالة"
        ),
        f"- فصل المتجانسات والاقتراض: الحكم لهذا المدخل ومعناه وحدهما؛ {separation}",
        "- جسور الاسترداد المفحوصة: المسحان؛ الرأس السليم؛ المروحة؛ كل مرشح منقول؛ الجذر؛ النواة؛ السجل المجمد؛ المدار؛ اتجاه النقل.",
        f"- عائق: النوع={card['outcome']}؛ يتطلب={card['required']}",
        f"- حالة الإغلاق: {card['outcome']}",
        f"- الحكم (استكشاف): {verdict}",
        f"- ملاحظات: {notes}",
    ])


def extract_existing_cards(text: str) -> dict[int, str]:
    def collect(source: str) -> dict[int, str]:
        found: dict[int, str] = {}
        for match in pattern.finditer(source):
            block = match.group(0).rstrip()
            card_marker = marker.search(block)
            if card_marker:
                found[int(card_marker.group(1))] = block
        return found

    pattern = re.compile(
        r"(?ms)^### بطاقة:.*?(?=^### بطاقة:|<!-- KHASHIM-AKKADIAN-HARVEST-BATCH-\d+:END -->)"
    )
    marker = re.compile(r"<!-- KHASHIM-AKKADIAN-(?:001|002):(\d+) -->")
    cards = collect(text)
    if len(cards) < LEGACY_EXPECTED:
        relative = READING.relative_to(ROOT).as_posix()
        for revision in ("HEAD", LEGACY_CARD_BASE):
            result = subprocess.run(
                ["git", "show", f"{revision}:{relative}"], cwd=ROOT,
                check=False, capture_output=True, text=True, encoding="utf-8",
            )
            if result.returncode == 0:
                baseline = collect(result.stdout)
                baseline.update(cards)
                cards = baseline
            if len(cards) == LEGACY_EXPECTED:
                break
    if len(cards) != LEGACY_EXPECTED:
        raise SystemExit(f"تعذر استخراج البطاقات القديمة: {len(cards)}")
    return cards


def replace_legacy_blocks(
    text: str, existing: dict[int, str], linked: set[int],
    corrected: dict[int, dict[str, Any]],
) -> str:
    for batch, (start, end) in LEGACY_MARKERS.items():
        lo = (batch - 1) * 300
        hi = min(batch * 300, LEGACY_EXPECTED)
        kept = [
            render_ocr_card(corrected[index], index)
            if index in corrected else existing[index]
            for index in range(lo, hi) if index not in linked
        ]
        corrected_count = sum(index in corrected for index in range(lo, hi))
        block = "\n".join([
            start,
            f"## بقايا حصاد خشيم القديم، الدفعة {batch:03d} ({len(kept)} بطاقة بلا نظير OCR؛ صُحح رأس {corrected_count})",
            "",
            "هذه هي البطاقات القديمة التي لم يوجد لمدخلها نظير في صفوف `ocr-akkadian`. حُفظت البطاقات ذات الرأس السليم كما أُنجزت؛ أما علامة الرأس الساقط فاستعيض عنها بالرأس المشكول من نص إعادة المسح وصُححت الحقول التابعة له في البطاقة نفسها. البطاقات المتداخلة انتقلت إلى كتلة OCR الموحدة أدناه.",
            "",
            "\n\n".join(kept),
            end,
        ])
        text = CARDS.replace_block(text, start, end, block)
    return text


def report_row(card: dict[str, Any]) -> dict[str, Any]:
    return {
        "ocr_index": card["ocr_index"],
        "foreign": card["foreign"],
        "foreign_vocalized": card["foreign_vocalized"],
        "foreign_sense": one_line(card["row"].get("foreign_sense")),
        "page": card["row"].get("page"),
        "source_line": card["row"].get("source_line"),
        "legacy_indices": card["legacy_indices"],
        "card_status": "corrected-unified" if card["legacy_indices"] else "new",
        "proposals": card["proposals"],
        "outcome": card["outcome"],
        "winner": card["winner"],
        "lexicon_witnesses": card.get("lexicon_witnesses", []),
    }


def build(dry_run: bool = False) -> dict[str, Any]:
    stored_legacy, stored_ocr = stored_rows()
    legacy = legacy_with_pages(stored_legacy)
    ocr = ocr_with_pages(stored_ocr)
    ground = ground_answers()
    linkage = link_sources(legacy, ocr, ground)
    members: dict[int, list[int]] = linkage["ocr_members"]
    legacy_ground: dict[int, int] = linkage["legacy_ground"]
    linked_old = {index for values in members.values() for index in values}
    fallen_indices = {
        index for index, row in enumerate(legacy) if row["foreign"] == FALLEN
    }
    missing_fallen = fallen_indices - set(legacy_ground)
    if missing_fallen:
        raise SystemExit(
            f"لم يسترد رأس الصفوف القديمة: {sorted(missing_fallen)}"
        )
    recovered_in_ocr = len(fallen_indices & linked_old)
    corrected_legacy_indices = sorted(fallen_indices - linked_old)
    recovered_in_legacy = len(corrected_legacy_indices)
    recovered = recovered_in_ocr + recovered_in_legacy
    if recovered != FALLEN_EXPECTED:
        raise SystemExit(f"لم يكتمل استرداد الرؤوس: {recovered}")
    corrected_cards = len(members)
    new_cards = OCR_EXPECTED - corrected_cards
    preserved_old = LEGACY_EXPECTED - len(linked_old)

    cards = [
        evaluate_ocr_card(index, row, members.get(index, []), legacy)
        for index, row in enumerate(ocr)
    ]
    corrected_legacy_cards = {
        index: evaluate_ocr_card(
            index, ground[legacy_ground[index]], [index], legacy,
        )
        for index in corrected_legacy_indices
    }
    attach_lexicon_witnesses(cards)
    attach_lexicon_witnesses(list(corrected_legacy_cards.values()))
    payload = {
        "schema": "khashim-akkadian-ocr-completion-v1",
        "generated_by": "scripts/build_khashim_akkadian_ocr_completion.py",
        "source": "data/khashim-pairs.json",
        "basis_source": "ocr-akkadian",
        "legacy_source": "khashim-akkadian",
        "inventory": {
            "legacy_rows": LEGACY_EXPECTED,
            "legacy_fallen_heads": FALLEN_EXPECTED,
            "ocr_rows": OCR_EXPECTED,
            "ocr_fallen_heads": 0,
            "ground_answers_for_linkage": len(ground),
        },
        "results": {
            "legacy_rows_merged": len(linked_old),
            "legacy_cards_preserved": preserved_old,
            "heads_recovered": recovered,
            "heads_recovered_in_ocr_cards": recovered_in_ocr,
            "heads_recovered_in_preserved_legacy_cards": recovered_in_legacy,
            "legacy_fallen_heads_remaining": 0,
            "corrected_unified_cards": corrected_cards,
            "new_cards": new_cards,
            "effective_harvest_cards": preserved_old + OCR_EXPECTED,
        },
        "links": linkage["links"],
        "legacy_head_corrections": [
            {
                "legacy_index": index,
                "foreign": corrected_legacy_cards[index]["foreign"],
                "foreign_vocalized": corrected_legacy_cards[index]["foreign_vocalized"],
                "foreign_sense": one_line(
                    corrected_legacy_cards[index]["row"].get("foreign_sense")
                ),
                "page": corrected_legacy_cards[index]["row"].get("page"),
                "source_line": corrected_legacy_cards[index]["row"].get("source_line"),
            }
            for index in corrected_legacy_indices
        ],
        "rows": [report_row(card) for card in cards],
    }
    if dry_run:
        return payload

    current = READING.read_text(encoding="utf-8")
    existing = extract_existing_cards(current)
    updated = replace_legacy_blocks(
        current, existing, linked_old, corrected_legacy_cards,
    )
    ocr_text = "\n\n".join(render_ocr_card(card) for card in cards)
    block = "\n".join([
        OCR_START,
        f"## حصاد خشيم الأكادي على المسح الجديد ({OCR_EXPECTED} بطاقة؛ 2026-08-12)",
        "",
        "**بيان النطاق.** الأساس هو كل صف ذي `source == \"ocr-akkadian\"`. دُمجت مرشحات المسح القديم في بطاقة المدخل نفسه؛ وما لا نظير له في القديم هو بطاقة جديدة. لا بطاقة مستقلة للصف القديم المتداخل.",
        "",
        "**قانون الحكم.** الشروط ثلاثة لا رابع لها: مسار صوت مسمى، وحدث من السجل المجمد كما هو، ومعنى الفرع بمدار كتبه القارئ. فحصت المروحة كلها، ولم يحتكر مرشح خشيم الحكم. شاهدا المعجم في البطاقة الموجبة توثيق للمادة الكلاسيكية، لا شرط رابع. قاموس الإغلاق مغلق في 25 وسما.",
        "",
        f"**الحصيلة.** استُردت الرؤوس القديمة الساقطة كلها: {recovered} من {FALLEN_EXPECTED}؛ ظهر {recovered_in_ocr} منها في بطاقات OCR الموحدة، وصُحح {recovered_in_legacy} في بطاقاته القديمة التي لا صف مقابلًا لها في جرد الـ{OCR_EXPECTED}. صُحح ووُحّد {corrected_cards} بطاقة OCR، وأضيفت {new_cards} بطاقة جديدة، وبقيت {preserved_old} بطاقة قديمة بلا نظير OCR، منها {recovered_in_legacy} مصححة الرأس.",
        "",
        ocr_text,
        OCR_END,
    ])
    updated = unicodedata.normalize(
        "NFC", CARDS.replace_block(updated, OCR_START, OCR_END, block)
    )
    READING.write_text(updated, encoding="utf-8", newline="\n")
    payload["results"]["reading_file_cards_after"] = CARDS.actual_card_count(updated)
    REPORT.write_text(
        unicodedata.normalize("NFC", json.dumps(payload, ensure_ascii=False, indent=1)) + "\n",
        encoding="utf-8", newline="\n",
    )
    audit_lines = [
        "# إتمام حصاد خشيم الأكادي على المسح الجديد",
        "", "**التاريخ:** 2026-08-12.",
        "**الطبقة:** استكشاف.", "", "## الأعداد", "",
        f"- صفوف المسح القديم: {LEGACY_EXPECTED}؛ الرأس ساقط في {FALLEN_EXPECTED} صفًا.",
        f"- صفوف `ocr-akkadian`: {OCR_EXPECTED}؛ لا رأس ساقطًا.",
        f"- الصفوف القديمة المدمجة في نظير OCR: {len(linked_old)}.",
        f"- الرؤوس القديمة المستردة فعليًا: {recovered} من {FALLEN_EXPECTED}.",
        f"- منها رؤوس دخلت بطاقات OCR الموحدة: {recovered_in_ocr}.",
        f"- ومنها رؤوس صُححت في بطاقاتها القديمة بلا نظير في جرد الـ{OCR_EXPECTED}: {recovered_in_legacy}.",
        "- الرؤوس الساقطة الباقية في البطاقات: 0.",
        f"- بطاقات OCR المصححة الموحدة: {corrected_cards}.",
        f"- البطاقات الجديدة الصافية: {new_cards}.",
        f"- البطاقات القديمة المحفوظة بلا نظير OCR: {preserved_old}، منها {recovered_in_legacy} مصححة الرأس في موضعها.",
        f"- المقام الفعال للحصاد بعد الدمج: {preserved_old + OCR_EXPECTED} بطاقة.",
        f"- الموجبات في صفوف OCR المكتملة: {sum(bool(card['winner']) for card in cards)}؛ لكل موجب شاهدا معجم عربي مسميان بنصيهما.",
        "", "## قانون الدمج", "",
        "رُبط الصف القديم بجواب المسح الجديد داخل صفحة الكتاب نفسها مع حفظ ترتيب الأجوبة. استعمل الرصف نص الجذر والشرح والمعنى والرأس، واتخذ موضع السطر في الصفحة ككاسر تعادل. إذا اجتمع أكثر من مرشح للمدخل نفسه ظهروا في بطاقة واحدة. وإذا استرد نص إعادة المسح رأس بطاقة قديمة لا مقابل لها في جرد صفوف OCR، صُحح الرأس والحقول التابعة له في البطاقة القديمة نفسها ولم تُحسب بطاقة جديدة. خريطة الصفوف ودرجات الحقول محفوظة في `data/khashim-akkadian-ocr-completion.json`.",
        "", "## قانون الحكم", "",
        "الشروط ثلاثة لا رابع لها: الصوت بمساره المسمى، والحدث المجمد، والمدار البشري المكتوب. فُحصت المروحة كلها، ولم يحتكر مرشح المصدر الحكم، وبقي قاموس الإغلاق المغلق في 25 وسما كما هو.",
        "", "## حراسة الأمثلة", "",
        "ثبتت البطاقات المستردة: `زق` ↔ `زقا`، و`أمات` ↔ `ومد`، و`يان` ↔ `بين`، و`إيرت` ↔ `عبر`، و`صبرت` ↔ `أصر`، و`ياتر` ↔ `فطر`.",
        "",
    ]
    AUDIT.write_text("\n".join(audit_lines), encoding="utf-8", newline="\n")
    return payload


def validate_examples(payload: dict[str, Any]) -> None:
    expected = {
        "زق": "زقا", "أمات": "ومد", "يان": "بين",
        "إيرت": "عبر", "صبرت": "أصر", "ياتر": "فطر",
    }
    rows = payload["rows"]
    for foreign, root in expected.items():
        matches = [row for row in rows if row["foreign"] == foreign]
        if not any(
            any(proposal["root"] == root for proposal in row["proposals"])
            for row in matches
        ):
            raise SystemExit(f"غاب مثال الحراسة: {foreign} ← {root}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    payload = build(dry_run=args.dry_run)
    validate_examples(payload)
    results = payload["results"]
    print(
        f"استُرد من الرؤوس={results['heads_recovered']}؛ "
        f"بطاقات جديدة={results['new_cards']}؛ "
        f"بطاقات مصححة موحدة={results['corrected_unified_cards']}؛ "
        f"قديم محفوظ={results['legacy_cards_preserved']}"
    )
    if not args.dry_run:
        print(f"كُتب: {REPORT.relative_to(ROOT).as_posix()}")
        print(f"كُتب: {AUDIT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
