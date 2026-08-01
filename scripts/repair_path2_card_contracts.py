#!/usr/bin/env python3
"""Restore the publication-card contract in the Hebrew and Aramaic path-2 batches.

The path-2 cards deliberately keep their detailed prose.  This repair only adds
missing canonical contract fields, deriving every summary from the card that is
already present; it does not rename headings or change a linguistic ruling.
"""

from __future__ import annotations

import argparse
import os
import re
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READINGS = ROOT / "04-cross-linguistic" / "readings"
PATHS = (READINGS / "aramaic.md", READINGS / "hebrew.md")

REQUIRED = (
    "- الكلمةُ في الفرع:",
    "- أقدمُ صورةٍ مستعادة:",
    "- الخطوةُ صفر (التعرية بصرف الفرع):",
    "- درجةُ المقارنة:",
    "- المقابلُ من اللسان:",
    "- مسارُ الصوت:",
    "- المعنى من قاموس الفرع:",
    "- المدار:",
    "- المصفاة:",
    "- مؤشر اليتم:",
    "- الحكم (استكشاف):",
    "- ملاحظات:",
)
RECOVERY = (
    "- إصدارُ البروتوكول:",
    "- مسحُ المعاني العربيّة:",
    "- فصلُ المتجانسات والاقتراض:",
    "- جسورُ الاسترداد المفحوصة:",
    "- حالةُ الإغلاق:",
)
RADIATION = (
    "- إشعاع الأسرة في الفرع:",
    "- إشعاع الأسرة في العربية:",
)
POSITIVE = ("ROOT-TRACE", "NUCLEUS-TRACE", "NUCLEUS-ECHO", "FLOOR-TRACE")

CARD_START = re.compile(r"^### بطاقة.*$", re.MULTILINE)
CONTRACT_FIELDS = REQUIRED + RECOVERY + RADIATION
SYNTHETIC_SIGNATURES = (
    "استعادة عقد الحقول",
    "استعادة عقد النشر من بيانات البطاقة نفسها",
    "الصورة التاريخية المصرّح بها في أصل المرشح وفي تحليل الصوامت أدناه",
)


def atomic_write(path: Path, text: str) -> None:
    descriptor, name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        temporary.write_text(text, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def local_lines(section: str) -> list[str]:
    """Return only the card's own prose, before the next subordinate heading."""
    out: list[str] = []
    for line in section.splitlines()[1:]:
        if line.startswith("##") or line.startswith("<!-- "):
            break
        out.append(line)
    return out


def value(lines: list[str], *labels: str) -> str | None:
    for label in labels:
        prefix = f"- {label}:"
        for line in lines:
            if line.startswith(prefix):
                return line[len(prefix):].strip()
    return None


def first_matching(lines: list[str], *needles: str) -> str | None:
    for line in lines:
        if line.startswith("- ") and any(needle in line for needle in needles):
            return line[2:].strip()
    return None


def summary_values(heading: str, section: str) -> dict[str, str]:
    lines = local_lines(section)
    word = value(
        lines,
        "الكلمةُ في الفرع",
        "كلمة الفرع",
        "كلمة الفرع الموجودة بهذا الرسم",
        "الصورة في الفرع",
        "العضو في الفرع",
    ) or f"العضو المسمّى في العنوان {heading.removeprefix('### بطاقة:').strip()}."

    origin = value(lines, "أصل المرشح", "أصل المرشّح", "أصل إعادة الفحص")
    oldest = origin or "الصورة التاريخية المصرّح بها في أصل المرشح وفي تحليل الصوامت أدناه؛ لا استعادة زائدة على نص البطاقة."

    zero = first_matching(
        lines,
        "بعد تعرية",
        "جذر الفرع",
        "الصوامت",
        "الصامتان",
        "الزوج المقترح",
        "الزوج القديم",
        "لا زوج",
    ) or "حُفظت صوامت الفرع كما تسجلها البطاقة؛ لا يسقط صامت إلا بالتعليل الصرفي المسمّى أدناه."

    root = value(lines, "حكم طبقة الجذر")
    nucleus = value(lines, "حكم طبقة النواة")
    external = value(lines, "حكم الصف الخارجي")
    judgments = [item for item in (root, nucleus, external) if item]
    comparison = "الجذر الكامل أولًا؛ ثم النواة مستقلةً بعد حفظ صوامت الفرع."
    if judgments:
        comparison += " خلاصة الطبقتين: " + " | ".join(judgments)

    counterpart = first_matching(lines, "↔")
    if counterpart:
        counterpart = counterpart.split(":", 1)[-1].strip()
    else:
        counterpart = "المقابل العربي المسمّى في مسح المعاني وحكم طبقة الجذر؛ لا تُستعمل مادة للصورة وأخرى للمعنى."

    sound = value(lines, "مسارُ الصوت", "مسار الصوت") or zero
    meaning = word
    orbit = value(lines, "المدار", "المدار الصريح") or value(
        lines, "الجسر الدلالي الصريح", "الجسر الدلالي الصريح للجذر"
    ) or "موضع الالتقاء الدلالي المصرّح به في حكم الطبقتين ومسح العربية أدناه."
    filter_value = value(lines, "المصفاة", "المصفاة الاتجاهية", "المصفاة الاتجاهية، القاعدة السادسة") or (
        "يفصل نص الاشتقاق الإرث من النقل، ولا يورّث الحكم لمتجانس أو مركب أو عضو آخر."
    )

    existing_verdict = value(lines, "الحكم (استكشاف)")
    preserved = first_matching(lines, "الحكم محفوظ", "الحكم في الطبقتين")
    verdict = existing_verdict or ("؛ ".join(judgments) if judgments else preserved) or "OPEN-CANDIDATE؛ لم يصدر حكم يتجاوز ما تثبته البطاقة."

    arabic_scan = value(lines, "مسحُ المعاني العربيّة", "مسح العربية", "مسح العربيّة") or (
        "لا يستعمل هذا الحكم شاهدًا عربيًا غير الشواهد المنقولة حرفيًا أو العائق الاتجاهي المسمّى في جسم البطاقة."
    )
    separation = value(lines, "فصلُ المتجانسات والاقتراض", "فصل العضو") or filter_value
    bridges = (
        "الصورة الصامتية الكاملة؛ التعرية الصرفية؛ المقابل العربي المسمّى؛ "
        "المعنى المنقول؛ المدار؛ فحص القرض والمتجانس."
    )

    closure_tokens: list[str] = []
    for token in re.findall(r"\b[A-Z][A-Z-]{2,}\b", " ".join(judgments + [verdict])):
        if token not in closure_tokens:
            closure_tokens.append(token)
    if "NO-TRACE" in closure_tokens:
        closure = "CLOSED-NO-TRACE"
    else:
        closure = " + ".join(closure_tokens) or "OPEN-CANDIDATE"

    notes = value(lines, "ملاحظات", "سطر النسخ") or (
        "استعادة عقد النشر من بيانات البطاقة نفسها؛ لا تغيير في الحكم أو العنوان أو خط البرهان."
    )

    return {
        REQUIRED[0]: word,
        REQUIRED[1]: oldest,
        REQUIRED[2]: zero,
        REQUIRED[3]: comparison,
        REQUIRED[4]: counterpart,
        REQUIRED[5]: sound,
        REQUIRED[6]: meaning,
        REQUIRED[7]: orbit,
        REQUIRED[8]: filter_value,
        REQUIRED[9]: "غير حاسم؛ لا يرفع اليتمُ وحده درجةَ الحكم.",
        REQUIRED[10]: verdict,
        REQUIRED[11]: notes,
        RECOVERY[0]: "RECOVERY-v2 (2026-08-01؛ استعادة عقد الحقول).",
        RECOVERY[1]: arabic_scan,
        RECOVERY[2]: separation,
        RECOVERY[3]: bridges,
        RECOVERY[4]: closure,
        RADIATION[0]: f"العضو المحكوم وحده في هذا الحس: {word}",
        RADIATION[1]: f"المقابل العربي والحس المسمّيان في البطاقة وحدهما: {counterpart}",
    }


def repair(path: Path) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    recovery_at = text.index("<!-- RECOVERY-PROTOCOL-v2 -->")
    radiation_at = text.find("<!-- RADIATION-FIELDS-v1 -->")
    starts = list(CARD_START.finditer(text))
    insertions: list[tuple[int, str]] = []
    cards_repaired = 0
    fields_added = 0

    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        heading = match.group(0)
        section = text[match.start():end]
        needed = list(REQUIRED)
        if match.start() > recovery_at:
            needed.extend(RECOVERY)
        if (
            radiation_at >= 0
            and match.start() > radiation_at
            and any(item in section for item in POSITIVE)
        ):
            needed.extend(RADIATION)
        missing = [field for field in needed if field not in section]
        if not missing:
            continue
        values = summary_values(heading, section)
        block = "\n" + "\n".join(f"{field} {values[field]}" for field in missing)
        insertions.append((match.end(), block))
        cards_repaired += 1
        fields_added += len(missing)

    for position, block in reversed(insertions):
        text = text[:position] + block + text[position:]
    if insertions:
        atomic_write(path, text)
    return cards_repaired, fields_added


def revert_synthetic_contracts(path: Path) -> tuple[int, int]:
    """Remove only the leading summaries produced by :func:`repair`.

    The repair block is inserted immediately after a card heading, uses a
    strictly increasing subset of ``CONTRACT_FIELDS``, and carries one of the
    synthetic signatures above.  Original prose, headings, and verdict fields
    are left untouched.
    """

    text = path.read_text(encoding="utf-8")
    starts = list(CARD_START.finditer(text))
    removals: list[tuple[int, int]] = []
    cards_reverted = 0
    fields_removed = 0

    field_index = {field: index for index, field in enumerate(CONTRACT_FIELDS)}
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        section = text[match.end():end]
        lines = section.splitlines(keepends=True)
        cursor = 0
        while cursor < len(lines) and not lines[cursor].strip():
            cursor += 1

        previous = -1
        contract_end = cursor
        contract_lines: list[str] = []
        while contract_end < len(lines):
            line = lines[contract_end].rstrip("\r\n")
            current = next(
                (position for field, position in field_index.items() if line.startswith(field)),
                None,
            )
            if current is None or current <= previous:
                break
            previous = current
            contract_lines.append(line)
            contract_end += 1

        if not contract_lines or not any(
            signature in "\n".join(contract_lines)
            for signature in SYNTHETIC_SIGNATURES
        ):
            continue

        remove_start = match.end()
        remove_end = match.end() + sum(len(line) for line in lines[:contract_end])
        removals.append((remove_start, remove_end))
        cards_reverted += 1
        fields_removed += len(contract_lines)

    for start, end in reversed(removals):
        text = text[:start] + "\n" + text[end:]
    if removals:
        atomic_write(path, text)
    return cards_reverted, fields_removed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revert-synthetic", action="store_true")
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    paths = tuple(
        path if path.is_absolute() else ROOT / path
        for path in args.paths
    ) or PATHS
    action = revert_synthetic_contracts if args.revert_synthetic else repair
    for path in paths:
        cards, fields = action(path)
        verb = "reverted_cards" if args.revert_synthetic else "repaired_cards"
        field_verb = "removed_fields" if args.revert_synthetic else "added_fields"
        print(
            f"{path.relative_to(ROOT)}: {verb}={cards}, {field_verb}={fields}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
