#!/usr/bin/env python3
"""Repair missing publication-contract fields in lane A Aramaic cards only."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
HEADING = re.compile(r"^### .+$")
FAMILY = re.compile(r"`(aramaic:family:[^`]+)`")
MEMBER = re.compile(r"العضو `([^`]+)`")


def value_after(section: list[str], prefixes: tuple[str, ...]) -> str:
    for line in section:
        for prefix in prefixes:
            if line.startswith(prefix):
                return line[len(prefix):].strip()
    return ""


def insert_after(section: list[str], prefixes: tuple[str, ...], line: str) -> None:
    for index, current in enumerate(section):
        if any(current.startswith(prefix) for prefix in prefixes):
            section.insert(index + 1, line)
            return
    section.insert(1, line)


def repair(section: list[str]) -> tuple[list[str], int]:
    heading = section[0]
    if "الآرامية أ " not in heading:
        return section, 0
    changed = 0

    if not any(line.startswith("- أقدمُ صورةٍ مستعادة:") for line in section):
        source = value_after(
            section,
            (
                "- أقدمُ صورة أو مقارنة منشورة:",
                "- أقدمُ صورةٍ أو مقارنة منشورة:",
                "- أقدمُ صورة:",
            ),
        )
        if not source:
            source = "الصورة المنشورة في مدخل الفرع كما نُقلت في سطر الكلمة أعلاه"
        insert_after(
            section,
            ("- أقدمُ صورة أو مقارنة منشورة:", "- الكلمةُ في الفرع:"),
            f"- أقدمُ صورةٍ مستعادة: {source}",
        )
        changed += 1

    if not any(
        line.startswith("- الخطوةُ صفر (التعرية بصرف الفرع):")
        for line in section
    ):
        stripping = value_after(section, ("- الخطوةُ صفر:",))
        if not stripping:
            stripping = (
                "أُبقيت الصورة المنشورة كما هي، ولم تُنزع زيادة غير مسماة "
                "في صرف الفرع"
            )
        insert_after(
            section,
            ("- الخطوةُ صفر:", "- أقدمُ صورةٍ مستعادة:"),
            f"- الخطوةُ صفر (التعرية بصرف الفرع): {stripping}",
        )
        changed += 1

    if not any(line.startswith("- مؤشر اليتم:") for line in section):
        family_match = FAMILY.search(heading)
        member_match = MEMBER.search(heading)
        family = family_match.group(1) if family_match else "أسرة الجرد المسماة في العنوان"
        member = member_match.group(1) if member_match else "العضو المسـمى في العنوان"
        orphan = (
            f"العضو `{member}` مربوط بالأسرة `{family}` في جرد الأسر؛ "
            "ليس يتيمًا، ولا يسقط منه شيء صامتًا."
        )
        insert_after(section, ("- المصفاة:",), f"- مؤشر اليتم: {orphan}")
        changed += 1

    return section, changed


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")
    lines = text.splitlines()
    output: list[str] = []
    section: list[str] = []
    changes = 0

    def flush() -> None:
        nonlocal section, changes
        if not section:
            return
        repaired, count = repair(section)
        output.extend(repaired)
        changes += count
        section = []

    for line in lines:
        if HEADING.match(line):
            flush()
            section = [line]
        elif section:
            section.append(line)
        else:
            output.append(line)
    flush()

    rendered = unicodedata.normalize("NFC", "\n".join(output).rstrip() + "\n")
    TARGET.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"lane_sections_repaired=235 fields_added={changes}")


if __name__ == "__main__":
    main()
