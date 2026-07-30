#!/usr/bin/env python3
"""Repair the 61 live scan lines from Aramaic fan campaign batch 03.

The batch updated blocker, closure, and verdict fields but left the earlier
"fan not run" sentence in the live body.  This script updates only that
machine-scan sentence and appends the displaced sentence as history.
"""
from __future__ import annotations

import json
import re
import tempfile
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
SOURCE = (
    ROOT
    / "cache"
    / "recovery_pipeline"
    / "arabic-fan-campaign-aramaic-batch-03.json"
)
AUDIT = (
    ROOT
    / "05-audits"
    / "2026-07-28-aramaic-batch03-live-scan-repair.md"
)
DATE = "2026-07-28"
HEADING = re.compile(r"^### (?:بطاقة|إعادةُ توسيم).*$", re.MULTILINE)
SCAN = re.compile(
    r"^- مسحُ المعاني العربيّة: "
    r"لم يجر مسح مروحة المعاجم العربية القديمة[^\n]*$",
    re.MULTILINE,
)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(unicodedata.normalize("NFC", text))
        temporary = Path(handle.name)
    temporary.replace(path)


def card_blocks(text: str) -> list[tuple[int, int, str]]:
    headings = list(HEADING.finditer(text))
    result = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        result.append((heading.start(), end, text[heading.start():end]))
    return result


def main() -> int:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = payload["records"]
    if len(records) != 61:
        raise ValueError(f"expected 61 batch-03 records, found {len(records)}")
    by_family = {record["family"]: record for record in records}
    if len(by_family) != 61:
        raise ValueError("duplicate family in batch-03 audit")

    text = READING.read_text(encoding="utf-8")
    parts = []
    cursor = 0
    repaired = []
    already_consistent = []
    for start, end, block in card_blocks(text):
        target = None
        for family, record in by_family.items():
            marker = f"<!-- ARABIC-FAN-CAMPAIGN:ARAMAIC-03:{family} -->"
            if marker in block:
                target = (family, record, marker)
                break
        if target is None:
            continue
        family, record, marker = target
        repair_marker = f"<!-- LIVE-SCAN-REPAIR:ARAMAIC-03:{family} -->"
        if repair_marker in block:
            repaired.append(family)
            continue
        matches = list(SCAN.finditer(block))
        if not matches:
            live_scan = re.findall(
                r"^- مسحُ المعاني العربيّة: [^\n]+$", block, re.MULTILINE
            )
            if len(live_scan) != 1:
                raise ValueError(
                    f"{family}: expected one live scan line, found {len(live_scan)}"
                )
            already_consistent.append(family)
            repaired.append(family)
            continue
        if len(matches) != 1:
            raise ValueError(f"{family}: expected one stale scan line, found {len(matches)}")
        old = matches[0].group(0)
        if record["fan_root"]:
            sources = " + ".join(record["fan_sources"])
            new = (
                f"- مسحُ المعاني العربيّة: أُنجزت مروحة `{record['fan_root']}` "
                f"من {sources}؛ تفاصيل الشاهد محفوظة في ملحق الحملة."
            )
        else:
            new = (
                "- مسحُ المعاني العربيّة: لا تلزم مروحة لإصدار حكم نسب؛ "
                "العزل أو طريق النقل مسمى في حقل أصل المصدر وملحق الحملة."
            )
        appendix = "\n".join(
            [
                "",
                repair_marker,
                f"- مصالحةُ سطر المسح الحي، {DATE}:",
                f"  - السطر السابق المحفوظ: `{old}`",
                f"  - السطر الحي المصحح: `{new}`",
                "  - لم يتغير العائق ولا الإغلاق ولا الحكم.",
            ]
        )
        changed = block[: matches[0].start()] + new + block[matches[0].end():]
        changed = changed.rstrip() + "\n" + appendix + "\n\n"
        parts.append(text[cursor:start])
        parts.append(changed)
        cursor = end
        repaired.append(family)
    parts.append(text[cursor:])
    if set(repaired) != set(by_family):
        missing = sorted(set(by_family) - set(repaired))
        raise ValueError(f"unrepaired batch-03 families: {missing}")
    updated = "".join(parts)
    if unicodedata.normalize("NFC", updated) != updated:
        raise ValueError("repaired reading is not NFC")
    atomic_write(READING, updated)
    changed_records = [
        record for record in records if record["family"] not in already_consistent
    ]
    positives = sum(bool(record["fan_root"]) for record in changed_records)
    structural = len(changed_records) - positives
    atomic_write(
        AUDIT,
        "\n".join(
            [
                "# مصالحة سطر المسح الحي، دفعة الآرامية 03",
                "",
                "## النطاق",
                "",
                "راجع هذا المرور بطاقات دفعة الحملة 03 الإحدى والستين التي حددها محضر الحملة المبصوم. أصلح المتناقض منها فقط، وترك السطر المكتمل كما هو. لم يغير حكمًا ولا عائقًا ولا إغلاقًا.",
                "",
                "## النتيجة",
                "",
                f"- بطاقات كان سطرها مكتملًا أصلًا: {len(already_consistent)}.",
                f"- بطاقات موجبة صولح سطر مروحتها: {positives}.",
                f"- بطاقات عزل أو نقل صُرّح فيها أن المروحة لا تلزم: {structural}.",
                "- السطر السابق محفوظ حرفيًا في ملحق مؤرخ بكل بطاقة.",
                "",
                "## السلامة",
                "",
                "- الإصلاح عرضي بنيوي لا حكم لغوي جديد.",
                "- لا سجل مركزي ولا تشغيل لخط البرهان.",
                "",
            ]
        ),
    )
    print(
        json.dumps(
            {
                "reviewed": len(records),
                "already_consistent": len(already_consistent),
                "repaired": len(changed_records),
                "positive_fan_lines": positives,
                "structural_isolation_lines": structural,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
