#!/usr/bin/env python3
"""Isolate Coptic members whose pinned CCL etymology names a Greek donor.

The operation is member-scoped.  A family is closed as a loan route only
when every member in the pinned inventory carries a Greek etymology.  Mixed
families keep their existing live blocker and receive explicit member
overrides for the Greek members, so a loan member cannot close or taint its
native-looking neighbours.

All changes are local and require third-lens review before commit.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import build_status_snapshot as status


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "coptic.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
CACHE = (
    ROOT
    / "cache"
    / "recovery_pipeline"
    / "coptic-greek-loan-isolation.json"
)
AUDIT = (
    ROOT
    / "05-audits"
    / "2026-07-27-coptic-greek-loan-isolation.md"
)
DATE = "2026-07-27"
MARKER = "COPTIC-GREEK-LOAN-ISOLATION"
# U+03E2..U+03EF are the paired Coptic letters SHEI, FEI, KHEI, HORI,
# GANGIA, SHIMA, and DEI: Ϣ Ϥ Ϧ Ϩ Ϫ Ϭ Ϯ plus their lowercase forms.
# They descend from Demotic and are not evidence for a Greek donor.
GREEK = re.compile(r"[\u0370-\u03e1\u03f0-\u03ff\u1f00-\u1fff]")
FAMILY_ID = re.compile(r"coptic:family:[0-9a-f]+")
DEMOTIC_COPTIC_CAPITALS = "ϢϤϦϨϪϬϮ"
DEMOTIC_COPTIC = DEMOTIC_COPTIC_CAPITALS + DEMOTIC_COPTIC_CAPITALS.lower()


def assert_demotic_letters_are_not_greek() -> None:
    mistaken = [character for character in DEMOTIC_COPTIC if GREEK.search(character)]
    if mistaken:
        rendered = " ".join(f"U+{ord(character):04X}" for character in mistaken)
        raise RuntimeError(f"Demotic-derived Coptic letters classified as Greek: {rendered}")


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def inventory() -> dict[str, list[dict[str, object]]]:
    connection = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT fm.family_id, e.entry_id, e.headword, e.gloss,
                   e.etymology, e.loan_hint
            FROM family_members fm
            JOIN entries e ON e.entry_id = fm.entry_id
            WHERE e.language = 'coptic'
            ORDER BY fm.family_id, e.entry_id
            """
        ).fetchall()
    finally:
        connection.close()
    families: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        etymology = row["etymology"] or ""
        families[row["family_id"]].append(
            {
                "entry_id": row["entry_id"],
                "headword": row["headword"],
                "gloss": row["gloss"],
                "etymology": etymology,
                "greek": bool(GREEK.search(etymology)),
                "loan_hint": bool(row["loan_hint"]),
            }
        )
    return dict(families)


def first_line(section: str, pattern: str) -> str:
    match = re.search(pattern, section, re.M)
    return match.group(0) if match else ""


def replace_line(section: str, old: str, new: str) -> str:
    if not old:
        raise ValueError(
            "missing required live field in " + section.splitlines()[0]
        )
    return section.replace(old, new, 1)


def member_lines(members: list[dict[str, object]]) -> list[str]:
    lines = []
    for member in members:
        etymology = " ".join(str(member["etymology"]).split())
        lines.append(
            f"    - `{member['entry_id']}`، {member['headword']} "
            f"«{member['gloss']}»: `{etymology}`"
        )
    return lines


def close_pure_family(
    section: str,
    family: str,
    greek_members: list[dict[str, object]],
) -> tuple[str, dict[str, object]]:
    marker = f"<!-- {MARKER}:PURE:{family} -->"
    if marker in section:
        return section, {"family": family, "already_applied": True}
    old_blocker = first_line(section, r"^- عائق:[^\n]*$")
    old_scan = first_line(
        section,
        r"^- (?:مسحُ المعاني العربيّة|مسح المعاني العربية):[^\n]*$",
    )
    old_closure = first_line(
        section,
        r"^- (?:حالةُ الإغلاق|حالة الإغلاق):[^\n]*$",
    )
    old_verdict = first_line(
        section, r"^- الحكم \(استكشاف\):[^\n]*$"
    )
    updated = replace_line(
        section,
        old_blocker,
        "- عائق: النوع=LOAN-ROUTE-ISOLATED؛ يتطلب=لا شيء في نطاق "
        "الأسرة؛ كل عضو يحمل مانحًا يونانيًا مسمى في CCL؛",
    )
    updated = replace_line(
        updated,
        old_scan,
        "- مسحُ المعاني العربيّة: غير منطبق بعد عزل مسار القرض؛ لا "
        "تستعمل مروحة العربية لصنع حكم نسب من عضو يوناني منقول.",
    )
    updated = replace_line(
        updated,
        old_closure,
        "- حالةُ الإغلاق: LOAN-ROUTE-ISOLATED؛ الأسرة كلها معزولة "
        "بأعضاء يونانيين مسمين.",
    )
    updated = replace_line(
        updated,
        old_verdict,
        "- الحكم (استكشاف): LOANWORD؛ عزل مسار، لا صلة نسب.",
    )
    appendix = [
        "",
        marker,
        f"- ملحق عزل القرض اليوناني، {DATE}:",
        "  - النطاق: كل أعضاء الأسرة، بلا وراثة من عضو واحد.",
        "  - المصدر: Comprehensive Coptic Lexicon، حقل الأصل الفردي؛ "
        "المانح اليوناني مطبوع بالرسم اليوناني ومعه مرجع LSJ أو بديله حيث توفر.",
        "  - الأعضاء المعزولة:",
        *member_lines(greek_members),
        "  - الحقول الحاكمة السابقة، محفوظة بلا محو:",
        f"    - `{old_blocker}`",
        f"    - `{old_scan}`",
        f"    - `{old_closure}`",
        f"    - `{old_verdict}`",
    ]
    return updated.rstrip() + "\n" + "\n".join(appendix) + "\n", {
        "family": family,
        "title": section.splitlines()[0],
        "members_isolated": len(greek_members),
        "previous_blocker": status.live_blocker(section),
    }


def annotate_mixed_family(
    section: str,
    family: str,
    greek_members: list[dict[str, object]],
    other_members: list[dict[str, object]],
) -> tuple[str, dict[str, object]]:
    marker = f"<!-- {MARKER}:MIXED:{family} -->"
    if marker in section:
        return section, {"family": family, "already_applied": True}
    appendix = [
        "",
        marker,
        f"- ملحق العزل العضوي للقرض اليوناني، {DATE}:",
        "  - المصير الجاري للأسرة لم يتغير؛ الأسرة مختلطة، فلا يرث "
        "العضو غير اليوناني حكم العضو المنقول.",
        "  - المصدر: Comprehensive Coptic Lexicon، حقل الأصل الفردي.",
        "  - الأعضاء اليونانية المعزولة بقرار عضو مستقل:",
        *member_lines(greek_members),
        f"  - الأعضاء الأخرى الباقية في نطاق القراءة: {len(other_members)}.",
        "  - لا تعد هذه الإضافة حكمًا موجبًا ولا إغلاقًا للأسرة.",
    ]
    return section.rstrip() + "\n" + "\n".join(appendix) + "\n", {
        "family": family,
        "title": section.splitlines()[0],
        "members_isolated": len(greek_members),
        "members_remaining": len(other_members),
        "blocker_retained": status.live_blocker(section),
    }


def main() -> int:
    assert_demotic_letters_are_not_greek()
    families = inventory()
    text = READING.read_text(encoding="utf-8")
    output: list[str] = []
    pure_records: list[dict[str, object]] = []
    mixed_records: list[dict[str, object]] = []

    for section in re.split(r"(?=^### )", text, flags=re.M):
        if not (
            section.startswith("### بطاقة")
            or section.startswith("### إعادةُ توسيم")
        ):
            output.append(section)
            continue
        ids = set(FAMILY_ID.findall(section))
        targets = [
            family
            for family in ids
            if family in families
            and any(member["greek"] for member in families[family])
        ]
        if not targets:
            output.append(section)
            continue
        if len(targets) != 1:
            raise ValueError(
                "card maps to multiple Greek-bearing families: "
                + section.splitlines()[0]
            )
        family = targets[0]
        members = families[family]
        greek_members = [member for member in members if member["greek"]]
        other_members = [member for member in members if not member["greek"]]
        if not other_members:
            changed, record = close_pure_family(
                section, family, greek_members
            )
            if not record.get("already_applied"):
                pure_records.append(record)
        else:
            changed, record = annotate_mixed_family(
                section, family, greek_members, other_members
            )
            if not record.get("already_applied"):
                mixed_records.append(record)
        output.append(changed)

    # CCL preserves some decomposed Coptic sequences in its pinned fields.
    # Normalize the generated document at the write boundary so a source
    # sequence cannot make the project reading violate the NFC house rule.
    rebuilt = unicodedata.normalize("NFC", "".join(output))
    if unicodedata.normalize("NFC", rebuilt) != rebuilt:
        raise ValueError("Coptic reading is not NFC")
    atomic_write(READING, rebuilt)

    payload = {
        "schema": "coptic-greek-loan-isolation-v1",
        "date": DATE,
        "status": "LOCAL-THIRD-LENS-REVIEW-REQUIRED",
        "pure_family_closures": len(pure_records),
        "mixed_families_annotated": len(mixed_records),
        "greek_members_isolated": sum(
            int(row["members_isolated"])
            for row in pure_records + mixed_records
        ),
        "previous_blockers_of_pure_closures": dict(
            Counter(row["previous_blocker"] for row in pure_records)
        ),
        "pure_records": pure_records,
        "mixed_records": mixed_records,
    }
    atomic_write(CACHE, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    audit = "\n".join(
        [
            "# عزل القروض اليونانية في القبطية، 2026-07-27",
            "",
            "دفعة محلية للمراجعة الثالثة. لا حكم نسب موجب فيها.",
            "",
            "## الرقمان المفصولان",
            "",
            "- الصلات الموجبة: 0.",
            f"- الإغلاقات: {len(pure_records)} من أسر كل أعضائها يونانيون.",
            "",
            (
                f"- الأسر المختلطة التي عزلت أعضاؤها فقط: "
                f"{len(mixed_records)}."
            ),
            (
                f"- مجموع الأعضاء اليونانية المعزولة: "
                f"{payload['greek_members_isolated']}."
            ),
            "",
            "لم تغلق أسرة مختلطة، ولم يرث عضو غير يوناني حكم جاره. "
            "المصدر في كل عضو هو حقل الأصل في Comprehensive Coptic "
            "Lexicon، وفيه الرسم اليوناني والمرجع المنشور.",
            "",
            "لا رقم للنشر ولا تشغيل لخط البرهان.",
            "",
        ]
    )
    atomic_write(AUDIT, audit)
    print(
        json.dumps(
            {
                "positive_connections": 0,
                "closures": len(pure_records),
                "mixed_families": len(mixed_records),
                "greek_members_isolated": payload[
                    "greek_members_isolated"
                ],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
