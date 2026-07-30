#!/usr/bin/env python3
"""Close only explicitly marked non-lexical Hebrew members.

This sweep is structural, not linguistic. It reads the current proof
completion queue and closes an UNRECORDED member only when the pinned
inventory itself marks it as a root/meta-entry, proper name, explicit form or
variant, or a textual compound. It never derives a closure from spelling or
semantic intuition.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
REPORT = ROOT / "data" / "proof-eligible-families.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
AUDIT = ROOT / "05-audits" / "2026-07-28-hebrew-explicit-structural-closures-08-local.md"
MARKER = "<!-- HEBREW-EXPLICIT-STRUCTURAL-CLOSURES-08 -->"
DATE = "2026-07-28"

FORM_LINKS = {
    "alt-of",
    "form-of",
    "variant-of",
    "via-form",
    "inflection-of",
}
FORM_PREFIXES = (
    "defective spelling of ",
    "alternative form of ",
    "plural indefinite form of ",
    "singular indefinite form of ",
    "plural of ",
    "singular of ",
    "construct state of ",
    "absolute state of ",
    "inflection of ",
    "masculine singular present participle",
    "feminine singular present participle",
    "masculine plural present participle",
    "feminine plural present participle",
    "past participle",
    "present participle",
)


def classify(row: sqlite3.Row) -> tuple[str, str] | None:
    pos = str(row["pos"] or "").lower()
    role = str(row["role"] or "").lower()
    gloss = str(row["gloss"] or "").strip()
    lowered = gloss.lower()
    links = set(json.loads(row["link_types_json"] or "[]"))
    headword = str(row["headword"] or "")

    if pos == "name":
        return "PROPER-NAME-ISOLATED", "المصدر يصنف العضو اسم علم."
    if pos == "root" or role in {"affix", "nonlexical"}:
        return "NONLEXICAL-ISOLATED", "المصدر يصنف العضو مدخل جذر أو عنصرًا غير معجمي."
    if links & FORM_LINKS or lowered.startswith(FORM_PREFIXES):
        return "FORM-OF-ISOLATED", "رابط المصدر أو نص المعنى يصرح بأنه صورة أو إحالة صرفية."
    if "textual-derived" in links and " " in headword:
        return "COMPOUND-BOUNDARY", "رابط المصدر يصرح بمركب نصي؛ لا يرث حكم رأسه."
    if pos in {"phrase", "prep_phrase", "conj", "article", "particle"}:
        return "FUNCTION-WORD", "المصدر يصنف العضو تركيبًا أو أداة نحوية."
    return None


def main() -> int:
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        print("Hebrew explicit structural closures 08: already present")
        return 0
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    incomplete = report["languages"]["hebrew"]["incomplete_family_queue"]
    candidates = [
        (family["family_id"], member["entry_id"])
        for family in incomplete
        for member in family["missing_members"]
        if member["current_state"] == "UNRECORDED"
    ]
    selected: dict[str, list[dict[str, str]]] = defaultdict(list)
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    try:
        for family_id, entry_id in candidates:
            row = connection.execute(
                """
                SELECT e.entry_id,e.headword,e.pos,e.gloss,fm.role,
                       fm.link_types_json
                FROM entries AS e
                JOIN family_members AS fm ON fm.entry_id=e.entry_id
                WHERE fm.family_id=? AND e.entry_id=?
                """,
                (family_id, entry_id),
            ).fetchone()
            if row is None:
                raise ValueError(f"missing inventory member: {entry_id}")
            disposition = classify(row)
            if disposition is None:
                continue
            state, reason = disposition
            selected[family_id].append(
                {
                    "entry_id": str(row["entry_id"]),
                    "headword": str(row["headword"]),
                    "pos": str(row["pos"]),
                    "gloss": str(row["gloss"]),
                    "state": state,
                    "reason": reason,
                }
            )
    finally:
        connection.close()
    if not selected:
        raise ValueError("structural sweep found no explicit closures")

    cards = []
    counts: Counter[str] = Counter()
    member_total = 0
    for rank, family_id in enumerate(sorted(selected), 1):
        members = selected[family_id]
        member_total += len(members)
        counts.update(item["state"] for item in members)
        member_lines = [
            f"- العضو: `{item['entry_id']}` | {item['headword']} | "
            f"{item['pos']} | «{item['gloss']}» | النتيجة: "
            f"{item['state']}، {item['reason']}"
            for item in members
        ]
        cards.append(
            "\n".join(
                [
                    f"### بطاقة: `{family_id}`، كنس بنيوي عبري 8، الرتبة {rank}",
                    "- عائق: النوع=STRUCTURAL-SWEEP؛ يتطلب=المراجعة المضادة الثالثة قبل إدخال الإغلاقات في السجل المركزي؛ الأعضاء=كل عضو مسمى أدناه.",
                    "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)",
                    "- الكلمةُ في الفرع: الأعضاء المسماة أدناه برسومها وتصنيفاتها من Kaikki Hebrew؛ لا تدمج في كلمة واحدة.",
                    "- أقدمُ صورةٍ مستعادة: رسم كل عضو في لقطة المصدر المثبتة أدناه؛ لا استعادة صرفية ولا تعرية في هذا الكنس.",
                    *member_lines,
                    "- الخطوةُ صفر (التعرية بصرف الفرع): لم تنزع الآلة حرفًا؛ استعملت تصنيف المصدر ورابط الأسرة حرفيًا.",
                    "- درجةُ المقارنة: لا مقارنة لغوية في هذه البطاقة؛ الإغلاق بنيوي سابق للحكم.",
                    "- مسحُ المعاني العربيّة: غير مشغل؛ لا يحتاج الإغلاق البنيوي مروحة عربية.",
                    "- المقابلُ من اللسان: غير صادر.",
                    "- مسارُ الصوت: غير مستعمل؛ لا ينشأ صف من إغلاق بنيوي.",
                    "- المعنى من قاموس الفرع: مثبت في سطر كل عضو أعلاه.",
                    "- المدار: غير مستعمل.",
                    "- المصفاة: الاسم والصورة والمركب والأداة تبقى ظاهرة بأسبابها ولا تعد صلة.",
                    "- فصلُ المتجانسات والاقتراض: كل عضو مسمى بمعرفه؛ لا يرث عضو إغلاق غيره.",
                    "- مؤشر اليتم: لم يسقط عضو من لقطة السكان.",
                    "- إشعاع الأسرة في الفرع: الأعضاء المغلقة هنا لا تورث حكمًا لأي عضو معجمي.",
                    "- إشعاع الأسرة في العربية: صفر؛ لا حكم نسب.",
                    "- جسورُ الاسترداد المفحوصة: تصنيف المصدر؛ دور العضو؛ روابط الصورة؛ حد المركب.",
                    "- حالةُ الإغلاق: مفصلة عضوًا عضوًا أعلاه.",
                    "- الحكم (استكشاف): غير صادر؛ الإغلاقات بنيوية فقط.",
                    "- عدسة الاسترداد: أبقت الأعضاء في السجل بدل إسقاطها من المقام صمتًا.",
                    "- عدسة التشكيك: رفضت استنتاج إغلاق من الرسم أو المعنى، وقبلت العلامات الصريحة وحدها.",
                    "- ملاحظات: محلي للمراجعة الثالثة؛ لا خط برهان ولا سجل مركزي.",
                    "",
                ]
            )
        )

    block = "\n".join(
        [
            "",
            MARKER,
            "",
            f"## كنس الإغلاقات البنيوية العبرية الصريحة ({DATE}، محلي)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "النطاق هو جميع الأعضاء غير المسجلين في الأسر العبرية الممثلة التي يحمل المصدر نفسه لها علامة بنيوية صريحة. لا يستعمل الرسم أو المعنى في التصنيف.",
            "",
            *cards,
            "<!-- HEBREW-EXPLICIT-STRUCTURAL-CLOSURES-08:END -->",
            "",
        ]
    )
    base = __import__("append_hebrew_biblical_priority_batch_01")
    base.atomic_write(READING, text.rstrip() + "\n" + block)
    audit_lines = [
        "# كنس الإغلاقات البنيوية العبرية الصريحة",
        "",
        "## النطاق",
        "",
        "أغلق الكنس الأعضاء غير المسجلين ذوي العلامة البنيوية الصريحة وحدهم.",
        "",
        "## الرقمان المفصولان",
        "",
        "- الصلات الموجبة: 0.",
        f"- الإغلاقات النهائية: {member_total}.",
        "",
        "## توزيع الإغلاقات",
        "",
    ]
    audit_lines.extend(f"- {state}: {count}." for state, count in sorted(counts.items()))
    audit_lines.extend(
        [
            "",
            "## الحالة",
            "",
            "- محلي للمراجعة المضادة الثالثة.",
            "- لا حكم نسب ولا تشغيل لخط البرهان.",
            "",
        ]
    )
    base.atomic_write(AUDIT, "\n".join(audit_lines))
    print(
        json.dumps(
            {
                "families_touched": len(selected),
                "positive_connections": 0,
                "terminal_closures": member_total,
                "by_state": dict(sorted(counts.items())),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
