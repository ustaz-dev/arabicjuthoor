#!/usr/bin/env python3
"""Exhaust the Egyptian and Coptic snapshots with both layers in parallel.

The frozen recovery inventory is read-only.  Every member receives an
independent root-layer and nucleus-layer retrieval status in a lane-B ledger.
Only hand-reviewed rows in ``lane_b_two_layer_promotions.jsonl`` may become
prose judgments; every such card must satisfy the complete publication
contract before any file is written.  Retrieval alone never issues a verdict.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
DATA = ROOT / "04-cross-linguistic" / "data"
LEDGER = DATA / "lane_b_two_layer_coverage.jsonl"
PROMOTIONS = DATA / "lane_b_two_layer_promotions.jsonl"
LEGACY_COVERAGE = DATA / "lane_b_coverage.jsonl"
PROGRESS = DATA / "lane_b_two_layer_progress.json"
AUDIT = ROOT / "05-audits" / "lane-b-2026-08-01-egyptian-coptic-two-layer-completion.md"
BATCH_SIZE = 500
DATE = "2026-08-01"
PROTOCOL = "RECOVERY-v2 (2026-07-14)"
FIELDS = (
    "- إصدارُ البروتوكول:",
    "- الكلمةُ في الفرع:",
    "- أقدمُ صورةٍ مستعادة:",
    "- الخطوةُ صفر (التعرية بصرف الفرع):",
    "- درجةُ المقارنة:",
    "- مسحُ المعاني العربيّة:",
    "- المقابلُ من اللسان:",
    "- مسارُ الصوت:",
    "- المعنى من قاموس الفرع:",
    "- المدار:",
    "- المصفاة:",
    "- فصلُ المتجانسات والاقتراض:",
    "- مؤشر اليتم:",
    "- إشعاع الأسرة في الفرع:",
    "- إشعاع الأسرة في العربية:",
    "- جسورُ الاسترداد المفحوصة:",
    "- حالةُ الإغلاق:",
    "- الحكم (استكشاف):",
    "- ملاحظات:",
)
OUTCOME_RE = re.compile(
    r"\b(?:ROOT-TRACE|ROOT-ECHO|NUCLEUS-TRACE|NUCLEUS-ECHO|FLOOR-TRACE)\b"
)


@dataclass(frozen=True)
class Spec:
    language: str
    arabic_name: str
    source_label: str
    reading: Path


SPECS = (
    Spec(
        "egyptian",
        "المصرية",
        "AED v1.0",
        ROOT / "04-cross-linguistic" / "readings" / "egyptian.md",
    ),
    Spec(
        "coptic",
        "القبطية",
        "Comprehensive Coptic Lexicon 1.2",
        ROOT / "04-cross-linguistic" / "readings" / "coptic.md",
    ),
)


def compact(value: object, limit: int = 700) -> str:
    text = " ".join(str(value or "").replace("`", "ˋ").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def rows(connection: sqlite3.Connection, spec: Spec) -> list[sqlite3.Row]:
    order = (
        "CAST(e.source_entry_id AS INTEGER)"
        if spec.language == "egyptian"
        else "CAST(SUBSTR(e.source_entry_id, 2) AS INTEGER)"
    )
    return connection.execute(
        f"""
        SELECT e.entry_id, e.source_entry_id, e.headword, e.romanization,
               e.pos, e.gloss, e.etymology, e.loan_hint, e.form_of,
               e.alternative_of, e.selected_input, e.skeleton,
               fm.family_id, fm.role, f.member_count, f.lemma_count,
               f.candidate_bearing_member_count,
               (SELECT COUNT(DISTINCT e2.gloss)
                  FROM family_members fm2
                  JOIN entries e2 ON e2.entry_id=fm2.entry_id
                 WHERE fm2.family_id=fm.family_id AND e2.gloss<>'')
                 AS family_gloss_count
          FROM entries e
          LEFT JOIN family_members fm ON fm.entry_id=e.entry_id
          LEFT JOIN families f ON f.family_id=fm.family_id
         WHERE e.language=?
         ORDER BY {order}, e.entry_id
        """,
        (spec.language,),
    ).fetchall()


def candidate_map(
    connection: sqlite3.Connection, member_ids: Iterable[str]
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    output = {
        member_id: {"root": [], "nucleus": []} for member_id in member_ids
    }
    seen: dict[str, dict[str, set[tuple[str, str, str]]]] = {
        member_id: {"root": set(), "nucleus": set()} for member_id in output
    }
    for row in connection.execute(
        """
        SELECT c.entry_id, c.kind, c.form, c.status, c.positions_json,
               c.rule_ids_json, c.route_flag
          FROM candidates c
          JOIN entries e ON e.entry_id=c.entry_id
         WHERE e.language IN ('egyptian', 'coptic')
           AND c.status='licensed' AND c.route_flag=0
         ORDER BY c.entry_id, c.kind, c.form, c.positions_json, c.rule_ids_json
        """,
    ):
        member_id = str(row["entry_id"])
        layer = "nucleus" if row["kind"] == "nucleus" else "root"
        key = (row["form"], row["positions_json"], row["rule_ids_json"])
        if key in seen[member_id][layer]:
            continue
        seen[member_id][layer].add(key)
        output[member_id][layer].append(
            {
                "form": row["form"],
                "positions": json.loads(row["positions_json"]),
                "rules": json.loads(row["rule_ids_json"]),
            }
        )
    return output


def load_promotions() -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    with PROMOTIONS.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            item = json.loads(line)
            member_id = str(item["member_id"])
            if member_id in output:
                raise RuntimeError(f"duplicate promotion {member_id} at line {line_number}")
            if len(set(item.get("arabic_sources", []))) < 2:
                raise RuntimeError(f"promotion {member_id} lacks two named Arabic sources")
            output[member_id] = item
    return output


def completed_state(spec: Spec, text: str) -> tuple[int, int]:
    closes = [
        int(value)
        for value in re.findall(
            rf"<!-- /lane-b-two-layer-month:{spec.language}:(\d{{3}}) -->", text
        )
    ]
    headers = [
        (int(start), int(end))
        for start, end in re.findall(
            rf"الدفعة {spec.arabic_name} \d{{3}} \(المواضع (\d+)[–-](\d+)\)", text
        )
    ]
    if not closes or not headers:
        raise RuntimeError(f"no completed two-layer batch found for {spec.language}")
    return max(closes), max(end for _, end in headers)


def marker_outcomes(spec: Spec, text: str) -> dict[str, set[str]]:
    marker = re.compile(
        rf"<!-- lane-b-two-layer-month:{spec.language}:([^ >]+) -->"
    )
    matches = list(marker.finditer(text))
    output: dict[str, set[str]] = {}
    for index, match in enumerate(matches):
        value = match.group(1)
        following = text[match.end() : match.end() + 180]
        if re.match(r"\s*## القراءةُ الثنائيّة المتزامنة", following):
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        fragment = text[match.end() : end]
        output[value] = set(OUTCOME_RE.findall(fragment))
    return output


def cumulative_counts(text: str) -> tuple[int, int]:
    matches = re.findall(
        r"القياس التراكمي[^\n]*الجذور \*\*(\d+)\*\*، والنوى \*\*(\d+)\*\*",
        text,
    )
    if not matches:
        raise RuntimeError("two-layer cumulative root/nucleus count is missing")
    root, nucleus = matches[-1]
    return int(root), int(nucleus)


def validate_promotion(
    promotion: dict[str, Any], row: sqlite3.Row, layer_candidates: dict[str, list[dict[str, Any]]]
) -> None:
    expected_prefix = "aed-v1.0:" if promotion["language"] == "egyptian" else "kellia_coptic_lexicon:"
    if not str(row["entry_id"]).startswith(expected_prefix):
        raise RuntimeError(f"promotion language drift for {row['entry_id']}")
    if str(promotion.get("root_outcome", "UNISSUED")).startswith("ROOT-"):
        if promotion["arabic_root"] not in {item["form"] for item in layer_candidates["root"]}:
            raise RuntimeError(f"unlicensed root promotion for {row['entry_id']}")
    if str(promotion.get("nucleus_outcome", "UNISSUED")).startswith("NUCLEUS-"):
        if promotion["nucleus"] not in {item["form"] for item in layer_candidates["nucleus"]}:
            raise RuntimeError(f"unlicensed nucleus promotion for {row['entry_id']}")


def render_card(
    spec: Spec,
    row: sqlite3.Row,
    position: int,
    total: int,
    promotion: dict[str, Any],
) -> str:
    root_outcome = str(promotion.get("root_outcome", "UNISSUED"))
    nucleus_outcome = str(promotion.get("nucleus_outcome", "UNISSUED"))
    outcomes = [value for value in (root_outcome, nucleus_outcome) if value != "UNISSUED"]
    if not outcomes:
        raise RuntimeError(f"promotion without an issued layer: {row['entry_id']}")
    degree = (
        "الجذر والنواة معًا؛ صدر الحكم في الطبقتين مستقلًا"
        if root_outcome != "UNISSUED" and nucleus_outcome != "UNISSUED"
        else "الجذر؛ فُحصت النواة مستقلة وبقيت غير صادرة"
        if root_outcome != "UNISSUED"
        else "النواة؛ فُحص الجذر مستقلًا وبقي غير صادر"
    )
    headword = compact(row["headword"]) or "بلا رسم"
    gloss = compact(row["gloss"]) or "بلا شرح منشور"
    family = compact(row["family_id"]) or "بلا أسرة في الجرد"
    members = int(row["member_count"] or 1)
    lemmas = int(row["lemma_count"] or 1)
    glosses = int(row["family_gloss_count"] or 0)
    candidate_members = int(row["candidate_bearing_member_count"] or 0)
    role = compact(row["role"]) or "غير معيّن"
    selected = compact(row["selected_input"]) or "غير معيّن"
    skeleton = compact(row["skeleton"]) or "غير مستعاد"
    etymology = compact(row["etymology"])
    source_reference = (
        f"{etymology} [{spec.source_label}، `{row['source_entry_id']}`]"
        if etymology
        else f"لا صورة أقدم منشورة في الحقل الفردي [{spec.source_label}، `{row['source_entry_id']}`]"
    )
    counterpart_bits = []
    if root_outcome != "UNISSUED":
        counterpart_bits.append(f"الجذر `{promotion['arabic_root']}` ({root_outcome})")
    if nucleus_outcome != "UNISSUED":
        counterpart_bits.append(f"النواة `{promotion['nucleus']}` ({nucleus_outcome})")
    if nucleus_outcome == "UNISSUED":
        counterpart_bits.append(f"النواة `{promotion['nucleus']}` مفحوصة بلا حكم")
    source_names = "؛ ".join(promotion["arabic_sources"])
    filter_text = (
        "لا وسم قرض ولا مانح مسمى في سجل العضو؛ لا اتجاه نقل مثبت"
        if not row["loan_hint"]
        else "إشارة المصدر إلى النقل مفحوصة في البطاقة، ولم تستعمل وحدها لإصدار الصلة"
    )
    if spec.language == "coptic":
        filter_text += "؛ U+03E2–U+03EF حروف قبطية أصيلة ولم تُحسب يونانية"
    lines = [
        f"### بطاقة: `{headword}` «{gloss}» — جرد اللقطة {position}/{total}",
        f"<!-- lane-b-two-layer-month:{spec.language}:{row['source_entry_id']} -->",
        f"- إصدارُ البروتوكول: {PROTOCOL}؛ قراءة الجذر والنواة متزامنة.",
        (
            f"- الكلمةُ في الفرع: `{headword}`؛ {compact(row['romanization']) or 'بلا رومنة منشورة'}؛ "
            f"{compact(row['pos']) or 'بلا نوع منشور'}؛ العضو `{row['entry_id']}` في الأسرة `{family}`."
        ),
        f"- أقدمُ صورةٍ مستعادة: {source_reference}.",
        (
            f"- الخطوةُ صفر (التعرية بصرف الفرع): حُفظ مدخل `{selected}` بلا نزع تخميني؛ "
            f"الهيكل المنشور `{skeleton}`."
        ),
        f"- درجةُ المقارنة: {degree}.",
        f"- مسحُ المعاني العربيّة: {promotion['arabic_evidence']} [{source_names}].",
        f"- المقابلُ من اللسان: {'؛ '.join(counterpart_bits)}.",
        f"- مسارُ الصوت: {promotion['sound_path']}",
        f"- المعنى من قاموس الفرع: «{gloss}» [{spec.source_label}، `{row['source_entry_id']}`].",
        f"- المدار: {promotion['orbit']}",
        f"- المصفاة: {filter_text}.",
        (
            f"- فصلُ المتجانسات والاقتراض: الحكم للعضو `{row['entry_id']}` ومعناه المذكور وحدهما؛ "
            "لا يرثه متحد رسم أو جار أسرة."
        ),
        (
            f"- مؤشر اليتم: حجم الأسرة={members}؛ دور العضو=`{role}`؛ "
            "الحكم عضوي وحق النقض محفوظ."
        ),
        (
            f"- إشعاع الأسرة في الفرع: أعضاء الأسرة في اللقطة={members}؛ اللمم={lemmas}؛ "
            f"سلاسل المعنى={glosses}؛ الدعم الحكمي في هذه البطاقة للعضو الواحد فقط."
        ),
        (
            f"- إشعاع الأسرة في العربية: المقابل الجذري=`{promotion['arabic_root']}`؛ "
            f"المقابل النووي=`{promotion['nucleus']}`؛ أعضاء الأسرة ذوو مرشح آلي={candidate_members}؛ "
            "لا يستند الحكم إلى اتساع بقية المروحة ولا يورث إليها."
        ),
        (
            "- جسورُ الاسترداد المفحوصة: المصدر الفردي؛ التعرية؛ الجذر مستقلًا؛ "
            "النواة مستقلًا؛ مرشحا السجل المرخصان؛ المصدران العربيان؛ القرض؛ المدار."
        ),
        f"- حالةُ الإغلاق: READY في الطبقة/الطبقات الصادرة؛ غير الصادر باقٍ مفتوحًا.",
        f"- الحكم (استكشاف): **{' + '.join(outcomes)}**.",
        (
            f"- ملاحظات: {promotion['notes']} موضع العضو {position}/{total}؛ "
            "خط البرهان المجمّد لم يُمس."
        ),
        "",
    ]
    rendered = "\n".join(lines)
    missing = [field for field in FIELDS if field not in rendered]
    if missing or not rendered.startswith("### بطاقة:"):
        raise RuntimeError(f"publication contract failed for {row['entry_id']}: {missing}")
    return rendered


def append_section(
    spec: Spec,
    batch_number: int,
    start: int,
    batch_rows: list[sqlite3.Row],
    total: int,
    promotion_cards: list[str],
    layer_data: dict[str, dict[str, list[dict[str, Any]]]],
    cumulative_root: int,
    cumulative_nucleus: int,
) -> str:
    end = start + len(batch_rows) - 1
    root_members = sum(bool(layer_data[row["entry_id"]]["root"]) for row in batch_rows)
    nucleus_members = sum(bool(layer_data[row["entry_id"]]["nucleus"]) for row in batch_rows)
    promoted_root = sum("ROOT-" in card for card in promotion_cards)
    promoted_nucleus = sum("NUCLEUS-" in card for card in promotion_cards)
    remaining = total - end
    lines = [
        f"<!-- lane-b-two-layer-month:{spec.language}:{batch_number:03d} -->",
        "",
        f"## القراءةُ الثنائيّة المتزامنة — الدفعة {spec.arabic_name} {batch_number:03d} (المواضع {start}–{end})",
        "",
        (
            f"- قُرئ {len(batch_rows)} عضوًا في طبقة الجذر وطبقة النواة استقلالًا؛ "
            f"حمل {root_members} عضوًا مرشح جذر مرخصًا، وحمل {nucleus_members} عضوًا مرشح نواة مرخصًا."
        ),
        (
            "- الاسترجاع لا يصدر حكمًا آليًا: بقي غير المحكوم في سجل التغطية، "
            "ولم تُنشأ بطاقة إلا لقرار دلالي يدوي ذي مصدرين وصف موقع ومدار مسمى."
        ),
        "",
    ]
    lines.extend(promotion_cards)
    lines.extend(
        [
            "### محضر الدفعة",
            "",
            f"- المقام المقروء بالطبقتين: **{len(batch_rows)} عضوًا**؛ بقي بعده **{remaining}** عضوًا في اللقطة.",
            f"- الصلات الجديدة: الجذر={promoted_root}؛ النواة={promoted_nucleus}؛ لا حكم آلي من مجرد المرشحين.",
            f"- القياس التراكمي: الجذور **{cumulative_root}**، والنوى **{cumulative_nucleus}**.",
            "- الإغلاقات الجديدة: 0؛ لم يتحول غياب الدليل إلى NO-TRACE.",
            (
                f"- سطر الموضع: من `{batch_rows[0]['entry_id']}` ({start}/{total}) "
                f"إلى `{batch_rows[-1]['entry_id']}` ({end}/{total})."
            ),
            "",
            f"<!-- /lane-b-two-layer-month:{spec.language}:{batch_number:03d} -->",
            "",
        ]
    )
    return "\n".join(lines)


def write_jsonl(path: Path, values: Iterable[dict[str, Any]]) -> None:
    text = "\n".join(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")) for value in values
    )
    atomic_write(path, text + ("\n" if text else ""))


def remove_promotions_from_legacy_coverage(promotion_ids: set[str]) -> int:
    kept: list[str] = []
    removed = 0
    with LEGACY_COVERAGE.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            if str(item["member_id"]) in promotion_ids:
                removed += 1
                continue
            kept.append(json.dumps(item, ensure_ascii=False, separators=(",", ":")))
    atomic_write(LEGACY_COVERAGE, "\n".join(kept) + ("\n" if kept else ""))
    return removed


def build_ledger(
    all_rows: dict[str, list[sqlite3.Row]],
    all_candidates: dict[str, dict[str, list[dict[str, Any]]]],
    outcomes: dict[str, dict[str, set[str]]],
    promotions: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    ledger: list[dict[str, Any]] = []
    for spec in SPECS:
        for position, row in enumerate(all_rows[spec.language], start=1):
            member_id = str(row["entry_id"])
            layer = all_candidates[member_id]
            tags = set(outcomes[spec.language].get(str(row["source_entry_id"]), set()))
            promotion = promotions.get(member_id)
            if promotion:
                tags.update(
                    value
                    for value in (
                        promotion.get("root_outcome"),
                        promotion.get("nucleus_outcome"),
                    )
                    if value and value != "UNISSUED"
                )
            root_issued = sorted(tag for tag in tags if tag.startswith("ROOT-"))
            nucleus_issued = sorted(tag for tag in tags if tag.startswith("NUCLEUS-"))
            ledger.append(
                {
                    "member_id": member_id,
                    "language": spec.language,
                    "source_entry_id": str(row["source_entry_id"]),
                    "source_position": position,
                    "headword": compact(row["headword"], 180),
                    "branch_gloss": compact(row["gloss"], 360),
                    "root_layer": {
                        "status": root_issued[0] if root_issued else "OPEN-CANDIDATE" if layer["root"] else "NO-LICENSED-CANDIDATE",
                        "candidate_count": len(layer["root"]),
                        "candidates": layer["root"][:12],
                    },
                    "nucleus_layer": {
                        "status": nucleus_issued[0] if nucleus_issued else "OPEN-CANDIDATE" if layer["nucleus"] else "NO-LICENSED-CANDIDATE",
                        "candidate_count": len(layer["nucleus"]),
                        "candidates": layer["nucleus"][:12],
                    },
                    "direction_hint": bool(row["loan_hint"]),
                    "semantic_verdict_issued": bool(root_issued or nucleus_issued),
                }
            )
    return ledger


def completed_noop_payload() -> dict[str, Any] | None:
    if not PROGRESS.exists() or not LEDGER.exists():
        return None
    saved = json.loads(PROGRESS.read_text(encoding="utf-8"))
    for spec in SPECS:
        state = saved.get("languages", {}).get(spec.language, {})
        expected = int(state.get("inventory", 0))
        if not expected:
            return None
        _, completed = completed_state(
            spec, spec.reading.read_text(encoding="utf-8")
        )
        if completed != expected or int(state.get("remaining", -1)) != 0:
            return None
    payload = json.loads(json.dumps(saved, ensure_ascii=False))
    for state in payload["languages"].values():
        state["completed_before"] = state["inventory"]
        state["completed_after"] = state["inventory"]
        state["batches_added"] = 0
        state["cards_added"] = 0
        state["remaining"] = 0
    payload["promotion_cards"] = 0
    payload["legacy_coverage_rows_removed"] = 0
    payload["idempotent_noop"] = True
    return payload


def run(apply: bool) -> dict[str, Any]:
    completed = completed_noop_payload()
    if completed is not None:
        return completed
    promotions = load_promotions()
    connection = connect()
    try:
        all_rows = {spec.language: rows(connection, spec) for spec in SPECS}
        row_by_id = {
            str(row["entry_id"]): row
            for language_rows in all_rows.values()
            for row in language_rows
        }
        all_candidates = candidate_map(connection, row_by_id)
    finally:
        connection.close()
    extra_promotions = sorted(set(promotions) - set(row_by_id))
    if extra_promotions:
        raise RuntimeError(f"promotion members absent from inventory: {extra_promotions}")
    for member_id, promotion in promotions.items():
        validate_promotion(promotion, row_by_id[member_id], all_candidates[member_id])

    payload: dict[str, Any] = {"languages": {}, "promotion_cards": 0}
    rendered_texts: dict[str, str] = {}
    outcome_maps: dict[str, dict[str, set[str]]] = {}
    for spec in SPECS:
        text = spec.reading.read_text(encoding="utf-8")
        batch_number, completed_end = completed_state(spec, text)
        cumulative_root, cumulative_nucleus = cumulative_counts(text)
        cumulative_before = (cumulative_root, cumulative_nucleus)
        total = len(all_rows[spec.language])
        if completed_end > total:
            raise RuntimeError(f"completed position exceeds inventory for {spec.language}")
        existing_markers = marker_outcomes(spec, text)
        language_promotions = {
            member_id: item
            for member_id, item in promotions.items()
            if item["language"] == spec.language
        }
        positions = {
            str(row["entry_id"]): position
            for position, row in enumerate(all_rows[spec.language], start=1)
        }
        sections: list[str] = []
        new_cards = 0
        start = completed_end + 1
        while start <= total:
            batch_rows = all_rows[spec.language][start - 1 : start - 1 + BATCH_SIZE]
            batch_number += 1
            promotion_cards: list[str] = []
            for row in batch_rows:
                member_id = str(row["entry_id"])
                promotion = language_promotions.get(member_id)
                if promotion is None:
                    continue
                source_id = str(row["source_entry_id"])
                if source_id in existing_markers:
                    continue
                promotion_cards.append(
                    render_card(spec, row, positions[member_id], total, promotion)
                )
                new_cards += 1
            cumulative_root += sum("ROOT-" in card for card in promotion_cards)
            cumulative_nucleus += sum("NUCLEUS-" in card for card in promotion_cards)
            sections.append(
                append_section(
                    spec,
                    batch_number,
                    start,
                    batch_rows,
                    total,
                    promotion_cards,
                    all_candidates,
                    cumulative_root,
                    cumulative_nucleus,
                )
            )
            start += len(batch_rows)
        rendered = text.rstrip() + "\n\n" + "\n".join(sections) if sections else text
        rendered_texts[spec.language] = rendered
        outcome_maps[spec.language] = marker_outcomes(spec, rendered)
        payload["languages"][spec.language] = {
            "inventory": total,
            "completed_before": completed_end,
            "completed_after": total,
            "batches_added": len(sections),
            "cards_added": new_cards,
            "root_before": cumulative_before[0],
            "root_after": cumulative_root,
            "nucleus_before": cumulative_before[1],
            "nucleus_after": cumulative_nucleus,
            "remaining": 0,
        }
        payload["promotion_cards"] += new_cards

    ledger = build_ledger(all_rows, all_candidates, outcome_maps, promotions)
    payload["ledger_rows"] = len(ledger)
    if apply:
        for spec in SPECS:
            atomic_write(spec.reading, rendered_texts[spec.language])
        removed = remove_promotions_from_legacy_coverage(set(promotions))
        payload["legacy_coverage_rows_removed"] = removed
        write_jsonl(LEDGER, ledger)
        atomic_write(PROGRESS, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
        audit_lines = [
            "# ختم اللقطتين المصرية والقبطية بالطبقتين",
            "",
            "- فُحص الجذر والنواة استقلالًا لكل عضو؛ لا fallback بينهما.",
            "- الاسترجاع الآلي لا يصدر حكمًا؛ البطاقات الجديدة محصورة في سجل الترقيات اليدوي.",
            f"- أعضاء السجل الثنائي: {len(ledger)}.",
            f"- البطاقات الجديدة: {payload['promotion_cards']}؛ الإغلاقات الجديدة: 0.",
            (
                f"- المصرية بعد الختم: الجذور {payload['languages']['egyptian']['root_after']}، "
                f"النوى {payload['languages']['egyptian']['nucleus_after']}."
            ),
            (
                f"- القبطية بعد الختم: الجذور {payload['languages']['coptic']['root_after']}، "
                f"النوى {payload['languages']['coptic']['nucleus_after']}."
            ),
            "- بقي في مقامي اللقطتين بعد الختم: 0 عضو.",
            "- خط البرهان والشبكة وفهرس النوى وقاعدة الجرد بقيت للقراءة فقط.",
            "",
        ]
        atomic_write(AUDIT, "\n".join(audit_lines))
    return payload


def validate() -> dict[str, Any]:
    if not LEDGER.exists() or not PROGRESS.exists():
        raise RuntimeError("two-layer completion artifacts are missing")
    counts = Counter()
    seen: set[str] = set()
    with LEDGER.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            item = json.loads(line)
            member_id = str(item["member_id"])
            if member_id in seen:
                raise RuntimeError(f"duplicate ledger member at line {line_number}: {member_id}")
            seen.add(member_id)
            counts[item["language"]] += 1
            for layer in ("root_layer", "nucleus_layer"):
                if not item[layer]["status"]:
                    raise RuntimeError(f"empty {layer} status for {member_id}")
    for spec in SPECS:
        text = spec.reading.read_text(encoding="utf-8")
        _, completed = completed_state(spec, text)
        expected = 33417 if spec.language == "egyptian" else 11284
        if completed != expected or counts[spec.language] != expected:
            raise RuntimeError(
                f"{spec.language} completion drift: completed={completed}, ledger={counts[spec.language]}, expected={expected}"
            )
    return {"valid": True, "ledger_rows": len(seen), "languages": dict(counts)}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("plan", "apply", "validate"), nargs="?", default="plan")
    args = parser.parse_args()
    payload = validate() if args.command == "validate" else run(args.command == "apply")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
