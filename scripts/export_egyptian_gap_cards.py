#!/usr/bin/env python3
"""Export one deterministic rank window of non-verdict Egyptian gap cards."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

from recovery_pipeline.families import family_card, family_review_queue
from recovery_pipeline.inventory import DEFAULT_DB, connect


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_READING = ROOT / "04-cross-linguistic" / "readings" / "egyptian.md"
FAMILY_ID_PATTERN = re.compile(r"egyptian:family:[0-9a-f]+")


def clean(value: object) -> str:
    text = unicodedata.normalize("NFC", str(value or ""))
    return " ".join(text.replace("\u2013", "-").replace("\u2014", "-").split())


def rank_window(queue: list[dict[str, Any]], start_rank: int, end_rank: int) -> list[dict[str, Any]]:
    if start_rank < 1:
        raise ValueError("start rank must be at least 1")
    if end_rank < start_rank:
        raise ValueError("end rank must not precede start rank")
    if len(queue) < end_rank:
        raise ValueError(
            f"rank window {start_rank}-{end_rank} requires {end_rank} families; queue returned {len(queue)}"
        )
    selected = queue[start_rank - 1:end_rank]
    expected = end_rank - start_rank + 1
    if len(selected) != expected:
        raise ValueError(f"rank window expected {expected} families; selected {len(selected)}")
    ids = [item["family_id"] for item in selected]
    if len(ids) != len(set(ids)):
        raise ValueError("rank window contains duplicate family IDs")
    return selected


def existing_family_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return set(FAMILY_ID_PATTERN.findall(path.read_text(encoding="utf-8")))


def ensure_no_overlap(selected: list[dict[str, Any]], reading: Path) -> None:
    overlap = sorted(
        {item["family_id"] for item in selected} & existing_family_ids(reading)
    )
    if overlap:
        preview = ", ".join(overlap[:3])
        raise ValueError(
            f"rank window overlaps {len(overlap)} families already in {reading}: {preview}"
        )


def member_metadata(connection, entry_ids: list[str]) -> dict[str, dict[str, Any]]:
    if not entry_ids:
        return {}
    marks = ",".join("?" for _ in entry_ids)
    rows = connection.execute(
        "SELECT entry_id, etymology, source_entry_id FROM entries "
        f"WHERE entry_id IN ({marks})",
        entry_ids,
    )
    return {
        row[0]: {"etymology": row[1], "source_entry_id": row[2]}
        for row in rows
    }


def route_label(candidate: dict[str, Any]) -> str:
    rules = candidate.get("rule_ids") or []
    if not rules:
        return "مباشر"
    route = "، ".join(rules)
    if candidate.get("route_required"):
        return f"{route}؛ شرط مسار"
    return route


def candidate_text(
    candidates: list[dict[str, Any]],
    kinds: set[str],
    limit: int,
) -> str:
    selected = [
        candidate for candidate in candidates
        if candidate.get("kind") in kinds
    ]
    selected.sort(
        key=lambda candidate: (
            0 if candidate.get("status") == "licensed" else 1,
            1 if candidate.get("route_required") else 0,
            len(candidate.get("rule_ids") or []),
            clean(candidate.get("form")),
        )
    )
    shown = selected[:limit]
    if not shown:
        return "لا مرشح في هذه الدرجة."
    parts = []
    for candidate in shown:
        reading = clean(candidate.get("reading")) or "بلا قراءة نصية"
        parts.append(
            f"{candidate['kind']} {clean(candidate['form'])} «{reading}» "
            f"({clean(candidate['status'])}؛ {route_label(candidate)})"
        )
    if len(selected) > limit:
        parts.append(f"وحُفظ {len(selected) - limit} مسارًا آخر في الجرد")
    return "؛ ".join(parts)


def sound_path_text() -> str:
    return (
        "غير صادر؛ لا يذكر صف حكم قبل اختيار عضو أو سلسلة معنى ومقابل محدد. "
        "الصفوف الظاهرة أعلاه مخرجات استرداد فقط، ولا تورث حكمًا."
    )


def source_blockers(payload: dict[str, Any], metadata: dict[str, dict[str, Any]]) -> str:
    blockers = [
        "النوع=TOOL-GAP؛ يتطلب=مسح مروحة معجمين عربيين قديمين لكل مقابل كامل"
    ]
    members = payload["members"]
    if len(members) > 1 or payload["family"]["construction"] != "singleton":
        blockers.append(
            "عائق إضافي=MORPHOLOGY-GAP: فصل الأعضاء وسلاسل المعنى قبل أي حكم"
        )
    if any(member.get("loan_hint") for member in members):
        blockers.append(
            "عائق إضافي=SOURCE-GAP: تثبيت اتجاه القرض وطبقته من مصدر فردي"
        )
    else:
        etymologies = [
            clean(metadata.get(member["entry_id"], {}).get("etymology"))
            for member in members
        ]
        if not any("Wb " in item or "TLA" in item for item in etymologies):
            blockers.append(
                "عائق إضافي=SOURCE-GAP: تثبيت Wb أو TLA أو شاهد قبطي منشور"
            )
        else:
            blockers.append(
                "عائق إضافي=SOURCE-GAP: تحقق فردي من الإحالة المحمولة قبل الترقية"
            )
    return "؛ ".join(blockers)


def member_source_text(
    payload: dict[str, Any],
    metadata: dict[str, dict[str, Any]],
) -> tuple[str, str, str, str]:
    branch_parts = []
    source_parts = []
    loan_parts = []
    meanings = []
    for member in payload["members"]:
        entry_id = member["entry_id"]
        extra = metadata.get(entry_id, {})
        headword = clean(member["headword"])
        romanization = clean(member["romanization"])
        pos = clean(member["pos"])
        gloss = clean(member["gloss"])
        etymology = clean(extra.get("etymology")) or "لا إحالة محمولة"
        source_id = clean(extra.get("source_entry_id")) or entry_id
        branch_parts.append(
            f"{headword} `{romanization}`، {pos}، «{gloss}» [AED v1.0، {source_id}]"
        )
        source_parts.append(
            f"{entry_id}: الرسم={headword}؛ إحالة={etymology}؛ قبطي=غير محمول"
        )
        loan_parts.append(
            f"{entry_id}: وسم القرض={'موجود' if member.get('loan_hint') else 'غير موجود آليًا'}؛ "
            f"الإحالة={etymology}"
        )
        meanings.append(f"«{gloss}» [AED v1.0، {source_id}]")
    return (
        "؛ ".join(branch_parts),
        "؛ ".join(source_parts),
        "؛ ".join(loan_parts),
        "؛ ".join(meanings),
    )


def render_card(
    rank: int,
    payload: dict[str, Any],
    metadata: dict[str, dict[str, Any]],
) -> list[str]:
    family = payload["family"]
    members = payload["members"]
    candidates = payload["unified_candidates"]
    branch, sources, loans, meanings = member_source_text(payload, metadata)
    roots = candidate_text(candidates, {"root", "hollow-root"}, 6)
    nuclei = candidate_text(candidates, {"nucleus"}, 6)
    return [
        f"### بطاقة: `{family['family_id']}`، {clean(family['anchor_headword'])} (الرتبة {rank})",
        f"- عائق: {source_blockers(payload, metadata)}.",
        "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)",
        f"- الكلمةُ في الفرع: {branch}",
        f"- أقدمُ صورةٍ مستعادة: الصور كما في AED v1.0: {branch}. لا تخترع صورة أو حركة.",
        f"- إحالة Wb/TLA والقبطية: {sources}. لا تثليث بغير حقل مثبت.",
        "- الخطوةُ صفر (التعرية بصرف الفرع): لا تعرية آلية غير مسماة؛ تحفظ الصوامت المنشورة، ولكل عضو هويته.",
        "- درجةُ المقارنة: الجذر الكامل أولًا، ثم الجذر الأجوف، ثم النواة عند قصر الصورة أو غياب كامل محفوظ.",
        f"- مسار الجذر الكامل أولًا: {roots}",
        "- مسحُ المعاني العربيّة: لم يجر مسح معجمين عربيين قديمين؛ لا ينتقى معنى من الأداة وحدها.",
        f"- المقابلُ من اللسان: {nuclei}",
        f"- مسارُ الصوت: {sound_path_text()}",
        f"- المعنى من قاموس الفرع: {meanings}",
        "- المدار: غير صادر؛ يلزم معنى عضو محدد وسند مباشر أو مدار واحد مسمى.",
        f"- المصفاة: {loans}. غياب الوسم الآلي ليس حكم أصالة أو نفي قرض.",
        f"- فصلُ المتجانسات والاقتراض: تضم الأسرة {len(members)} عضوًا. "
        "الأسرة وحدة تغطية وعرض؛ العضو أو سلسلة المعنى وحدة الحكم، ولكل عضو حق نقض مستقل، "
        "ولا يرث المركب حكم رأسه ولا الرأس حكم مركباته.",
        "- مؤشر اليتم: "
        + (
            "للأسرة صور صرفية؛ تبقى روابطها للعرض ولا تورث الحكم."
            if family["form_count"] else "لا صورة صرفية مسماة في الأسرة."
        ),
        "- جسورُ الاسترداد المفحوصة: الصورة؛ الجذر الكامل؛ الأجوف؛ النواة؛ أعضاء الأسرة؛ القرض؛ إحالات AED المحمولة.",
        "- حالةُ الإغلاق: TOOL-GAP",
        "- الحكم (استكشاف): غير صادر؛ لا `NO-TRACE`.",
        "- عدسة الاسترداد: أبقت المرشحات والأعضاء ظاهرين بترتيب الجذر الكامل أولًا.",
        "- عدسة التشكيك: منعت الحكم ووراثته حتى تمسح المروحة وتثبت الإحالة ويفصل كل متجانس أو مركب.",
        "- ملاحظات: بطاقة استرجاع غير حكمية؛ لا تدخل خط البرهان.",
        "",
    ]


def render(
    connection,
    start_rank: int,
    end_rank: int,
) -> tuple[str, list[str]]:
    queue = family_review_queue(
        connection,
        "recovery",
        language="egyptian",
        limit=end_rank,
        order="strength",
    )
    selected = rank_window(queue, start_rank, end_rank)
    family_ids = [item["family_id"] for item in selected]
    digest = hashlib.sha256("\n".join(family_ids).encode("utf-8")).hexdigest()
    lines = [
        f"# الموجة المصرية: الرتب {start_rank}-{end_rank}",
        "",
        "### بيان النطاق: الخطوة 14",
        "",
        f"- الرتب: {start_rank}-{end_rank} من طابور الاسترداد المصري الحالي بترتيب القوة.",
        "- المعيار: ترتيب القوة الاسترجاعي فقط؛ لا حكم ولا خط برهان.",
        f"- العدد: {len(selected)} أسرة.",
        "- المصدر: AED v1.0؛ لا تضاف Wb أو TLA أو قبطية إلا من حقل المادة.",
        f"- أول معرف: `{family_ids[0]}`.",
        f"- آخر معرف: `{family_ids[-1]}`.",
        f"- بصمة ترتيب المعرفات SHA-256: `{digest}`.",
        "- قانون الحكم: الأسرة للتغطية والعرض؛ العضو أو سلسلة المعنى للحكم، ولا وراثة عبر المركبات.",
        "",
    ]
    for offset, item in enumerate(selected):
        payload = family_card(connection, item["family_id"], candidate_limit=500)
        metadata = member_metadata(
            connection,
            [member["entry_id"] for member in payload["members"]],
        )
        lines.extend(render_card(start_rank + offset, payload, metadata))
    text = unicodedata.normalize("NFC", "\n".join(lines))
    if "\u2013" in text or "\u2014" in text:
        raise ValueError("rendered output contains a long dash")
    if re.search(r"[\u0660-\u0669]", text):
        raise ValueError("rendered output contains Arabic-Indic digits")
    return text, family_ids


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
            temporary = handle.name
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary:
            Path(temporary).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--start-rank", type=int, required=True)
    parser.add_argument("--end-rank", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--reading",
        type=Path,
        default=DEFAULT_READING,
        help="Reading file checked for overlapping family IDs before a new export.",
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    connection = connect(args.db, create=False)
    try:
        rendered, family_ids = render(
            connection,
            args.start_rank,
            args.end_rank,
        )
    finally:
        connection.close()

    if args.check:
        if not args.output.exists():
            print(f"FAIL: missing Egyptian gap-card export: {args.output}")
            return 1
        current = args.output.read_text(encoding="utf-8")
        if current != rendered:
            print(f"FAIL: stale Egyptian gap-card export: {args.output}")
            return 1
        print(
            f"Egyptian gap cards: CLEAN "
            f"({args.start_rank}-{args.end_rank}, {len(family_ids)} families)"
        )
        return 0

    ensure_no_overlap(
        [{"family_id": family_id} for family_id in family_ids],
        args.reading,
    )
    atomic_write(args.output, rendered)
    print(
        f"wrote {args.output} "
        f"({args.start_rank}-{args.end_rank}, {len(family_ids)} families)"
    )
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
