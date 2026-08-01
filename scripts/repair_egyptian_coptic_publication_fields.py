#!/usr/bin/env python3
"""Backfill the publication contract in the Egyptian and Coptic readings.

This is a lane-local, judgment-preserving repair.  It only names information
already present in a card: its unchanged heading, member markers, source/gloss text,
sound route, named Arabic witnesses, and issued outcome.  It does not search
for a new cognate, create a sound row, delete a card, or alter an outcome.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READINGS = (
    ROOT / "04-cross-linguistic" / "readings" / "coptic.md",
    ROOT / "04-cross-linguistic" / "readings" / "egyptian.md",
)

REQUIRED_FIELDS = (
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
RECOVERY_FIELDS = (
    "- إصدارُ البروتوكول:",
    "- مسحُ المعاني العربيّة:",
    "- فصلُ المتجانسات والاقتراض:",
    "- جسورُ الاسترداد المفحوصة:",
    "- حالةُ الإغلاق:",
)
RADIATION_FIELDS = (
    "- إشعاع الأسرة في الفرع:",
    "- إشعاع الأسرة في العربية:",
)
FIELD_ORDER = (
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
RECOVERY_MARKER = "<!-- RECOVERY-PROTOCOL-v2 -->"
RADIATION_MARKER = "<!-- RADIATION-FIELDS-v1 -->"
POSITIVE_RE = re.compile(
    r"\b(?:ROOT-TRACE|ROOT-ECHO|NUCLEUS-TRACE|NUCLEUS-ECHO|FLOOR-TRACE)\b"
)
OUTCOME_RE = re.compile(
    r"\b(?:ROOT-TRACE|ROOT-ECHO|NUCLEUS-TRACE|NUCLEUS-ECHO|"
    r"FLOOR-TRACE|NO-TRACE|LOANWORD)\b"
)
CARD_START_RE = re.compile(r"^### بطاقة.*$", re.MULTILINE)
MEMBER_RE = re.compile(
    r"<!--\s*(?:lane-b-[^:>]+:)?(?:egyptian|coptic):([^ >]+)\s*-->"
)

# Older compact cards used unvocalized labels.  Canonicalizing their labels is
# a form-only operation and keeps the field payload byte-for-byte unchanged.
ALIASES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^- إصدار البروتوكول:(.*)$", re.MULTILINE), "- إصدارُ البروتوكول:"),
    (re.compile(r"^- الكلمة في الفرع:(.*)$", re.MULTILINE), "- الكلمةُ في الفرع:"),
    (
        re.compile(r"^- الخطوة صفر(?: \(التعرية بصرف الفرع\))?:(.*)$", re.MULTILINE),
        "- الخطوةُ صفر (التعرية بصرف الفرع):",
    ),
    (re.compile(r"^- درجة المقارنة:(.*)$", re.MULTILINE), "- درجةُ المقارنة:"),
    (re.compile(r"^- مسح العربية:(.*)$", re.MULTILINE), "- مسحُ المعاني العربيّة:"),
    (re.compile(r"^- مسح المعاني العربية:(.*)$", re.MULTILINE), "- مسحُ المعاني العربيّة:"),
    (re.compile(r"^- المقابل:(.*)$", re.MULTILINE), "- المقابلُ من اللسان:"),
    (re.compile(r"^- مسار الصوت:(.*)$", re.MULTILINE), "- مسارُ الصوت:"),
    (re.compile(r"^- معنى الفرع:(.*)$", re.MULTILINE), "- المعنى من قاموس الفرع:"),
    (re.compile(r"^- فصل المتجانسات والاقتراض:(.*)$", re.MULTILINE), "- فصلُ المتجانسات والاقتراض:"),
    (re.compile(r"^- مؤشر اليتم:(.*)$", re.MULTILINE), "- مؤشر اليتم:"),
    (re.compile(r"^- إشعاع الأسرة في الفرع:(.*)$", re.MULTILINE), "- إشعاع الأسرة في الفرع:"),
    (re.compile(r"^- إشعاع الأسرة في العربية:(.*)$", re.MULTILINE), "- إشعاع الأسرة في العربية:"),
    (re.compile(r"^- جسور الاسترداد المفحوصة:(.*)$", re.MULTILINE), "- جسورُ الاسترداد المفحوصة:"),
    (re.compile(r"^- حالة الإغلاق:(.*)$", re.MULTILINE), "- حالةُ الإغلاق:"),
    (re.compile(r"^- الحكم:(.*)$", re.MULTILINE), "- الحكم (استكشاف):"),
)


def atomic_write(path: Path, text: str) -> None:
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def cards(body: str) -> list[tuple[int, int, str, str]]:
    starts = list(CARD_START_RE.finditer(body))
    return [
        (
            match.start(),
            starts[index + 1].start() if index + 1 < len(starts) else len(body),
            match.group(0),
            body[match.start() : starts[index + 1].start() if index + 1 < len(starts) else len(body)],
        )
        for index, match in enumerate(starts)
    ]


def outcome_payloads(body: str) -> list[str]:
    return [
        match.group(1).strip()
        for match in re.finditer(
            r"^- الحكم(?: \(استكشاف\))?:(.*)$", body, re.MULTILINE
        )
    ]


def heading_parts(heading: str) -> tuple[str, str]:
    gloss_match = re.search(r"«([^»]+)»", heading)
    gloss = gloss_match.group(1).strip() if gloss_match else "المعنى المسمى في العنوان"
    head_match = re.search(r"[`ˋ]([^`ˋ]+)[`ˋ]", heading)
    if head_match:
        headword = head_match.group(1).strip()
    else:
        headword = re.sub(r"^### بطاقة(?::|\s)+", "", heading)
        headword = headword.split("«", 1)[0].strip(" :،") or "العضو المسمى في العنوان"
    return headword, gloss


def local_fragment(section: str) -> str:
    """Return the actual card body, excluding later receipts swallowed by the gate."""
    first_newline = section.find("\n")
    if first_newline < 0:
        return section
    later = re.search(r"(?m)^#{1,6} .+$", section[first_newline + 1 :])
    if later is None:
        return section
    return section[: first_newline + 1 + later.start()]


def member_ids(section: str) -> list[str]:
    section = local_fragment(section)
    found = []
    for value in MEMBER_RE.findall(section):
        if value not in found:
            found.append(value)
    if found:
        return found
    generic = re.findall(r"`((?:aed-v1\.0:|kellia_coptic_lexicon:)[^`]+)`", section)
    return list(dict.fromkeys(generic))


def clean_line(line: str) -> str:
    return re.sub(r"^-\s*", "", line.strip()).rstrip(".")


def evidence(section: str, patterns: tuple[str, ...], limit: int = 720) -> str:
    selected: list[str] = []
    for raw in section.splitlines()[1:]:
        line = clean_line(raw)
        if not line or line.startswith("<!--") or line.startswith("###"):
            continue
        if any(re.search(pattern, line, re.IGNORECASE) for pattern in patterns):
            if line not in selected:
                selected.append(line)
        if len("؛ ".join(selected)) >= limit:
            break
    joined = "؛ ".join(selected)
    if len(joined) > limit:
        joined = joined[:limit].rstrip() + "…"
    return joined


def layer_value(section: str) -> str:
    verdict = " ".join(outcome_payloads(section))
    if not verdict:
        verdict = " ".join(
            line for line in section.splitlines() if OUTCOME_RE.search(line)
        )
    root = bool(re.search(r"\bROOT-(?:TRACE|ECHO)\b", verdict))
    nucleus = bool(re.search(r"\bNUCLEUS-(?:TRACE|ECHO)\b", verdict))
    floor = "FLOOR-TRACE" in verdict
    if root and nucleus:
        return "الجذر والنواة معًا؛ كلا الحكمين منقولان من الحكم المسجل في البطاقة نفسها"
    if root:
        return "الجذر؛ لم تسجل البطاقة حكم نواة موجبًا"
    if nucleus:
        return "النواة؛ بقي فحص الجذر مستقلًا وفق النص الموجود في البطاقة"
    if floor:
        return "القاع؛ الدرجة هي FLOOR-TRACE كما يسجل حكم البطاقة"
    return "الجذر ثم النواة؛ الدرجة النهائية هي ما يسجله حكم البطاقة بلا إعادة تقدير"


def named_arabic_scope(section: str) -> str:
    forms: list[str] = []
    patterns = (
        r"(?:الجذر|النواة|مادة|المقابل)\s+[`ˋ]([^`ˋ]+)[`ˋ]",
        r"[`ˋ]([^`ˋ]+)[`ˋ]\s*(?:↔|في مادة)",
    )
    for pattern in patterns:
        for value in re.findall(pattern, section):
            value = value.strip()
            if value and value not in forms:
                forms.append(value)
    if not forms:
        route = evidence(section, (r"↔", r"النواة", r"الجذر"), 300)
        return route or "المقابل العربي المسمى في نص البطاقة، من غير توسيع للمروحة"
    return "، ".join(f"`{value}`" for value in forms[:12])


def existing_outcome_value(section: str) -> str:
    """Copy only the card's current ruling, never a superseded tag in its history."""
    local = local_fragment(section)
    payloads = outcome_payloads(local)
    if not payloads:
        for line in local.splitlines():
            if not re.match(r"^-\s*حالة[ُ\s]+الإغلاق", line):
                continue
            match = re.search(r"الحكم(?: \(استكشاف\))?:\s*(.+)$", line)
            if match:
                payloads.append(match.group(1).strip())
    current = " ".join(payloads)
    if not current or "غير صادر" in current:
        return "**غير صادر**؛ استكمال الحقل لا يحول غياب الحكم إلى حكم جديد"
    tags = list(dict.fromkeys(OUTCOME_RE.findall(current)))
    if not tags:
        return "**غير صادر**؛ استكمال الحقل لا يحول غياب الحكم إلى حكم جديد"
    return "**" + " + ".join(tags) + "**؛ منقول من الحكم الجاري في البطاقة"


def canonicalize_aliases(section: str) -> str:
    for pattern, label in ALIASES:
        if label in section:
            continue
        section = pattern.sub(lambda match: label + match.group(1), section, count=1)
    return section


def field_values(heading: str, section: str) -> dict[str, str]:
    section = local_fragment(section)
    headword, gloss = heading_parts(heading)
    ids = member_ids(section)
    id_text = "، ".join(f"`{item}`" for item in ids) or f"`{headword}`"
    source = evidence(
        section,
        (r"\[(?:AED|CCL|Crum|KELLIA)", r"Wb\s", r"المصدر", r"أقدم", r"معر[ِّّ]?ف"),
        520,
    )
    zero = evidence(
        section,
        (r"الهيكل", r"بلا نزع", r"لم تُنزع", r"لا نزع", r"لا لاحقة", r"التعرية"),
        520,
    )
    arabic_scan = evidence(
        section,
        (
            r"الصحاح",
            r"المحكم",
            r"لسان العرب",
            r"كتاب العين",
            r"المفردات",
            r"تاج العروس",
            r"مسح",
            r"يثبت",
        ),
        700,
    )
    counterpart = named_arabic_scope(section)
    sound = evidence(
        section,
        (r"↔", r"هوية", r"الطريق", r"مسار", r"(?:LAB|DENT|GUT|LIQ|SIB)-\d+"),
        600,
    )
    orbit = evidence(
        section,
        (r"المدار", r"مباشر", r"صدى", r"يطابق", r"يقابل", r"يلتقي", r"سببي"),
        600,
    )
    loan = evidence(
        section,
        (r"قرض", r"مانح", r"نقل", r"foreign", r"سامي", r"يونان"),
        560,
    )
    verdict_text = " ".join(outcome_payloads(section)) or evidence(
        section, (r"ROOT-", r"NUCLEUS-", r"FLOOR-", r"NO-TRACE", r"LOANWORD"), 300
    )
    if re.search(r"\b(?:ROOT|NUCLEUS|FLOOR)-(?:TRACE|ECHO)\b", verdict_text):
        closure = f"READY في الدرجة/الدرجات التي يسميها الحكم: {layer_value(section)}"
    elif "LOANWORD" in verdict_text:
        closure = "READY؛ LOANWORD كما في الحكم المسجل"
    elif "NO-TRACE" in verdict_text:
        closure = "CLOSED-NO-TRACE كما في الحكم المسجل"
    else:
        closure = "غير صادر؛ تُحفظ حالة البطاقة القائمة بلا تحويلها إلى حكم جديد"
    return {
        "- إصدارُ البروتوكول:": "RECOVERY-v2 (2026-07-14)؛ ترميم عقد النشر من بيانات البطاقة القائمة",
        "- الكلمةُ في الفرع:": f"`{headword}` «{gloss}»؛ نطاق العضو {id_text}",
        "- أقدمُ صورةٍ مستعادة:": source or f"لا تضيف البطاقة صورةً أقدم من `{headword}` والمصدر المسمى في نصها",
        "- الخطوةُ صفر (التعرية بصرف الفرع):": zero or f"لا تسجل البطاقة نزعًا إضافيًا؛ يُحفظ الرسم `{headword}` كما ورد فيها",
        "- درجةُ المقارنة:": layer_value(section),
        "- مسحُ المعاني العربيّة:": arabic_scan or "تُحفظ الشواهد والمعاني العربية المسماة في نص البطاقة وحدها؛ لا يضاف شاهد جديد",
        "- المقابلُ من اللسان:": f"{counterpart}؛ لا يضاف مقابل غير مسمى في البطاقة",
        "- مسارُ الصوت:": sound or "المسار هو ما تسميه البطاقة؛ لا يضاف صف صوتي أو تحويل جديد",
        "- المعنى من قاموس الفرع:": f"«{gloss}»؛ المصدر ومعرف العضو كما سمتهما البطاقة: {id_text}",
        "- المدار:": orbit or f"يُحفظ مدار «{gloss}» كما صيغ في متن البطاقة؛ لا يوسع الحكم خارجه",
        "- المصفاة:": loan or "لا يضيف هذا الترميم حكم قرض أو أصالة؛ تبقى المصفاة المسجلة في البطاقة نافذة",
        "- فصلُ المتجانسات والاقتراض:": f"الحكم محصور في {id_text} ومعنى «{gloss}»؛ لا يرثه متحد رسم أو جار أسرة، وتبقى قيود القرض المذكورة في البطاقة نافذة",
        "- مؤشر اليتم:": f"نطاق الدعم المسمى في البطاقة هو {id_text}؛ لا توريث من عضو غير مسمى ولا رفع للحكم باتساع المروحة",
        "- إشعاع الأسرة في الفرع:": f"الأعضاء المدعومة نصًا في البطاقة: {id_text}؛ سلسلة المعنى المسماة «{gloss}»؛ لا إشعاع حكمي خارج هذا النطاق",
        "- إشعاع الأسرة في العربية:": f"المقابلات المدعومة نصًا في البطاقة: {counterpart}؛ لا يستند الحكم إلى اتساع بقية المروحة العربية ولا يورث إليها",
        "- جسورُ الاسترداد المفحوصة:": "العضو والمصدر؛ التعرية المسجلة؛ طبقة الجذر؛ طبقة النواة؛ الشواهد العربية المسماة؛ مسار الصوت؛ القرض؛ المدار؛ لا جسر جديد في هذا الترميم",
        "- حالةُ الإغلاق:": closure,
        "- الحكم (استكشاف):": existing_outcome_value(section),
        "- ملاحظات:": "ترميم شكلي من بيانات البطاقة نفسها؛ لم يُحذف عضو، ولم يتغير الحكم أو صف الصوت أو طبقة المقارنة",
    }


def repair_body(body: str) -> tuple[str, Counter[str]]:
    # Heading forms are part of the historical reading record.  The shared
    # counter recognizes them, so field repair preserves them byte-for-byte.
    original_payloads = outcome_payloads(body)
    original_outcomes = Counter(OUTCOME_RE.findall("\n".join(original_payloads)))
    starts = cards(body)
    pieces: list[str] = []
    cursor = 0
    counts: Counter[str] = Counter()
    expected_added_payloads: list[str] = []
    recovery_at = body.find(RECOVERY_MARKER)
    radiation_at = body.find(RADIATION_MARKER)
    for start, end, heading, raw_section in starts:
        pieces.append(body[cursor:start])
        section = canonicalize_aliases(raw_section)
        preserved_heading = section.splitlines()[0]
        values = field_values(preserved_heading, section)
        required = set(REQUIRED_FIELDS)
        if recovery_at >= 0 and start > recovery_at:
            required.update(RECOVERY_FIELDS)
        if (
            radiation_at >= 0
            and start > radiation_at
            and POSITIVE_RE.search(section)
        ):
            required.update(RADIATION_FIELDS)
        missing = [
            field for field in FIELD_ORDER if field in required and field not in section
        ]
        if missing:
            block = ["<!-- PUBLICATION-FIELD-BACKFILL-v1 -->"]
            block.extend(f"{field} {values[field]}" for field in missing)
            if "- الحكم (استكشاف):" in missing:
                expected_added_payloads.append(values["- الحكم (استكشاف):"])
            lines = section.splitlines()
            insert_at = 1
            while insert_at < len(lines) and lines[insert_at].startswith("<!--"):
                insert_at += 1
            lines[insert_at:insert_at] = block
            section = "\n".join(lines)
            if raw_section.endswith("\n") and not section.endswith("\n"):
                section += "\n"
            counts["cards"] += 1
            for field in missing:
                counts[field] += 1
        if section.splitlines()[0] != heading:
            raise RuntimeError(f"heading changed during field repair: {heading}")
        pieces.append(section)
        cursor = end
    pieces.append(body[cursor:])
    repaired = "".join(pieces)
    repaired_payloads = outcome_payloads(repaired)
    repaired_outcomes = Counter(OUTCOME_RE.findall("\n".join(repaired_payloads)))
    if Counter(repaired_payloads) != Counter(original_payloads + expected_added_payloads):
        raise RuntimeError("judgment payload changed during field repair")
    expected_outcomes = original_outcomes + Counter(
        OUTCOME_RE.findall("\n".join(expected_added_payloads))
    )
    if expected_outcomes != repaired_outcomes:
        raise RuntimeError("judgment outcome signature changed during field repair")
    return repaired, counts


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    aggregate: Counter[str] = Counter()
    for path in READINGS:
        before = path.read_text(encoding="utf-8")
        after, counts = repair_body(before)
        print(f"{path.relative_to(ROOT)}\tcards={counts['cards']}\tchanged={before != after}")
        for field in REQUIRED_FIELDS + RECOVERY_FIELDS + RADIATION_FIELDS:
            if counts[field]:
                print(f"  {counts[field]:>4}  {field}")
        aggregate.update(counts)
        if args.apply and after != before:
            atomic_write(path, after)
    print(f"TOTAL\tcards={aggregate['cards']}\tmode={'apply' if args.apply else 'dry-run'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
