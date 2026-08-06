#!/usr/bin/env python3
"""ابن محضر إعادة تحكيم مستخرجات العائق بعد توقيع صفوف الهوية.

المستخرجات مدخلات قراءة فقط. لا يغير هذا البرنامج شبكة الإبدالات ولا ملفات
القراءات القديمة. يكتب طبقة نسخ صريحة تحفظ الحكم السابق وسببه، وتفرق بين
عائق الهوية الذي رفعته IDN-01..IDN-24 وبين صفوف التحول التي لم توقع.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPLORATION = ROOT / "04-cross-linguistic" / "exploration"
NETWORK = ROOT / "04-cross-linguistic" / "shift-network-draft.md"
ARAMAIC_READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
OUTPUT = EXPLORATION / "reopened-identity-cards.md"

DATE = "2026-08-05"
IDENTITY_ROWS = {f"IDN-{number:02d}" for number in range(1, 25)}

LANGUAGE_NAMES = {
    "akkadian": "الأكادية",
    "ancient-greek": "اليونانية القديمة",
    "aramaic": "الآرامية",
    "coptic": "القبطية",
    "egyptian": "المصرية القديمة",
    "hebrew": "العبرية",
    "nucleus-echoes-week17": "أصداء النوى، الأسبوع 17",
    "old-english": "الإنجليزية القديمة",
    "old-irish": "الأيرلندية القديمة",
    "old-latin": "اللاتينية",
    "old-norse": "النوردية القديمة",
    "persian": "الفارسية",
    "phoenician-punic-scout": "الفينيقية والبونية، الاستطلاع",
    "punic": "البونية",
    "welsh": "الويلزية",
}

POSITIVE_TAGS = (
    "ROOT-TRACE",
    "ROOT-ECHO",
    "NUCLEUS-TRACE",
    "NUCLEUS-ECHO",
    "READY",
)

HARD_TAGS = (
    "LOANWORD",
    "LOAN-ROUTE-ISOLATED",
    "SEMITIC-SOURCE-TRANSMISSION",
    "DIRECTIONAL-TRANSMISSION",
    "THIRD-PARTY-TO-BRANCH",
    "INTRA-HOUSE-TRANSFER",
    "MORPHOLOGY-GAP",
    "SOURCE-GAP",
    "ORIGINAL-CONSONANT-DROP",
    "BELOW-NUCLEUS",
    "PROPER-NAME-ISOLATED",
    "NONLEXICAL-ISOLATED",
    "FORM-OF-ISOLATED",
    "CONSTRUCTED-SEMANTIC-BRIDGE",
)

IDENTITY_CUES = (
    "تطابق صامتي مباشر",
    "تطابق صامت",
    "مطابقة صامت",
    "مطابقة ثلاثية تامة",
    "هوية صامت",
    "هويات",
    "صف هوية",
    "صفوف الهوية",
    "نظيره المباشر",
    "لا يحتاج إبدال",
    "خارج الأداة",
)

UNSIGNED_CHANGE_CUES = (
    "قلب مكاني",
    "سقوط صامت",
    "إسقاط صامت",
    "صفين",
    "صفان",
    "خارج نطاق",
    "غير نافذ",
    "توسيع نطاق",
    "انعكاس",
    "اندماج",
    "scope-gap",
    "شرط الصف",
    "بشرطه",
    "حذف",
    "إلى الصفر",
    "↔ Ø",
)


def clean(value: object, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = text.replace("\u2014", "-").replace("\u2013", "-").replace("|", "¦")
    return text[:limit] if len(text) > limit else text


def network_row_count() -> int:
    text = NETWORK.read_text(encoding="utf-8")
    rows = set(re.findall(r"(?m)^\| ((?:IDN|[A-Z]+(?:-[A-Z]+)*)-\d{2}) \|", text))
    if len(rows) != 71:
        raise RuntimeError(f"عدد صفوف الشبكة {len(rows)}، والمطلوب 71")
    missing = sorted(IDENTITY_ROWS - rows)
    if missing:
        raise RuntimeError(f"صفوف الهوية الناقصة: {missing}")
    return len(rows)


def aramaic_samekh_tool_gap_cards() -> int:
    """أعد عد الأسر من جدول المصير نفسه، لا من ورقة القرار."""
    text = ARAMAIC_READING.read_text(encoding="utf-8")
    start = text.index("### سجل الأسرة الواحدة")
    end = text.index("\n## ", start)
    count = 0
    for line in text[start:end].splitlines():
        if not re.match(r"^\| \d+ \|", line):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) >= 4 and cells[3] == "TOOL-GAP" and "ס" in cells[2]:
            count += 1
    if count != 147:
        raise RuntimeError(f"عد أسر السامخ المعلقة {count}، والمثبت 147")
    return count


def previous_status(text: str) -> tuple[str, str]:
    blocker = re.search(r"عائق: النوع=([^؛\n]+)", text)
    closure = re.search(r"حالةُ الإغلاق:\s*([^؛\n]+)", text)
    tags = [tag for tag in (*POSITIVE_TAGS, *HARD_TAGS, "LAW-GAP", "TOOL-GAP") if tag in text]
    status = clean(blocker.group(1) if blocker else closure.group(1) if closure else " + ".join(tags))
    if not status:
        status = "NETWORK-BLOCKED بحسب عقد المستخرج"
    reason_match = re.search(r"(?:يتطلب=|السبب:|سبب عدم الإصدار:)([^\n]+)", text)
    reason = clean(reason_match.group(1) if reason_match else status, 240)
    return status, reason


def classify(text: str, head: str) -> tuple[str, str, bool]:
    """أعد الحالة الجديدة وسببها وهل تغير الحكم."""
    old_status, old_reason = previous_status(text)

    if "סהרא" in text or "kaikki_aramaic:164:en-סהרא" in text:
        return (
            "AUTHOR-RESERVED-SOUND-GAP",
            "اكتملت تهيئة شهر مقابل סהרא، لكن الرجل الآرامية من SIB-07 لم توقع بعد",
            old_status != "AUTHOR-RESERVED-SOUND-GAP",
        )

    # هذان حكمان نصت البطاقتان نفسيهما على أن عائقهما صار موقّعًا في
    # الشبكة النافذة. لا يجوز أن يعيد جامع الكلمات المفتاحية العائق القديم.
    if "treîs" in head:
        return (
            "OPEN-CANDIDATE",
            "رفع BR-GREC-01 الموقع عائق النطاق اليوناني، وبقيت القراءة الدلالية عضوية",
            old_status != "OPEN-CANDIDATE",
        )
    if "aed-v1.0:164020" in text and "`kp`" in text:
        return (
            "OPEN-CANDIDATE",
            "أثبت IDN-13 هوية k/ك وأثبت IDN-06 مقابلة p/ف، فارتفع عائق المسار عن كف",
            old_status != "OPEN-CANDIDATE",
        )
    if "kaikki_old_norse_2026_07_23:553:en-drepa" in text:
        return (
            "ROOT-TRACE + OPEN-CANDIDATE",
            "حفظ الحكم الموجب في طبقته، ورفع عائق الهوية عن الطبقة الأخرى",
            old_status != "ROOT-TRACE + OPEN-CANDIDATE",
        )

    positives = [tag for tag in POSITIVE_TAGS if tag in text]
    hard = [tag for tag in HARD_TAGS if tag in text]
    has_gap = any(tag in text for tag in ("LAW-GAP", "TOOL-GAP")) or "غير مدرج في الشبكة" in text
    identity = any(cue in text for cue in IDENTITY_CUES)
    unsigned_change = any(cue in text for cue in UNSIGNED_CHANGE_CUES)

    if positives and not has_gap:
        return (positives[0], "الحكم الموجب السابق قائم، وصفوف الهوية لا تنسخه", False)

    if hard:
        new_status = " + ".join(dict.fromkeys(hard))
        if has_gap and identity:
            return (
                new_status,
                "رفع عائق الهوية، وبقي العائق المستقل المسمى في البطاقة",
                clean(old_status) != clean(new_status),
            )
        return (new_status, "العائق غير الصوتي مستقل عن صفوف الهوية", clean(old_status) != clean(new_status))

    if has_gap and unsigned_change and not identity:
        return (
            "LAW-GAP",
            "العائق صف تحول أو نطاق أو حذف، ولا ترفعه صفوف الهوية",
            old_status != "LAW-GAP",
        )

    if positives and has_gap:
        return (
            f"{positives[0]} + OPEN-CANDIDATE",
            "حفظ الحكم الموجب في طبقته، ورفع عائق الهوية عن الطبقة الأخرى",
            True,
        )

    # عقد blocked-*.jsonl هو نطاق الدفعة. حين لا يحمل السطر عائقا مستقلا
    # يبطل رد الشبكة القديمة، لكن لا يصدر موجب دلالي آلي.
    return (
        "OPEN-CANDIDATE",
        "ألغت IDN-01 إلى IDN-24 رد التطابق المباشر، وبقي الحكم الدلالي عضويًا بلا ترقية آلية",
        old_status != "OPEN-CANDIDATE",
    )


def main() -> int:
    row_count = network_row_count()
    samekh_cards = aramaic_samekh_tool_gap_cards()
    source_files = sorted(EXPLORATION.glob("blocked-*.jsonl"))
    records: list[dict[str, object]] = []

    for source in source_files:
        language = source.stem.removeprefix("blocked-")
        with source.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                excerpt = str(row.get("excerpt") or "")
                head = clean(row.get("head") or row.get("word") or f"السطر {line_number}")
                old_status, old_reason = previous_status(excerpt)
                new_status, reason, changed = classify(excerpt, head)
                records.append(
                    {
                        "language": language,
                        "source": source.name,
                        "line": line_number,
                        "head": head,
                        "old": old_status,
                        "old_reason": old_reason,
                        "new": new_status,
                        "reason": reason,
                        "changed": changed,
                    }
                )

    if len(records) != 851:
        raise RuntimeError(f"عدد سجلات الدفعة {len(records)}، والمطلوب 851")

    by_language = Counter(str(record["language"]) for record in records)
    by_new = Counter(str(record["new"]) for record in records)
    changed_count = sum(bool(record["changed"]) for record in records)

    lines = [
        "# محضر فك أسر بطاقات شبكة الإبدالات",
        "",
        f"- التاريخ: {DATE}.",
        f"- الشبكة النافذة عند المرور: {row_count} صفًا، وفيها IDN-01 إلى IDN-24 كاملة.",
        "- النطاق: كل سطر في مستخرجات blocked-*.jsonl، وعددها 851.",
        "- القاعدة: صفوف الهوية ترفع رد التطابق المباشر فقط. لا توسع صف تحول، ولا تسقط صامتًا، ولا تنشئ حكم نسب آليًا.",
        f"- الأحكام التي تغيرت ولها سطر نسخ أدناه: {changed_count}.",
        "- البطاقات التي لم يتغير حكمها بقيت ظاهرة بسبب عائق مستقل أو حكم موجب سابق.",
        "",
        "## ضبط العدد بحسب المستخرج",
        "",
        "| اللسان | البطاقات |",
        "|---|---:|",
    ]
    for language, amount in sorted(by_language.items()):
        lines.append(f"| {LANGUAGE_NAMES.get(language, language)} | {amount} |")
    lines.extend(
        [
            f"| المجموع | {sum(by_language.values())} |",
            "",
            "## حالة סהרא المحجوزة للمؤلف",
            "",
            "- العضو: `kaikki_aramaic:164:en-סהרא-arc-noun-nni0PqAO`، والصورة `סהרא` sahrā، ومعناها القمر.",
            "- بعد نزع ألف الحالة يبقى `s-h-r`، ولا يسقط صامت من الطرفين.",
            "- المقابل المهيأ: `شهر`. يثبت لسان العرب: «يُسَمَّى القمر شَهْراً لأَنه يُشْهَرُ به».",
            "- المسار المهيأ: `ס الآرامية ↔ ش العربية` بوصفه الرجل الآرامية المقترحة في SIB-07، ثم IDN-20 للهاء وIDN-01 للراء.",
            "- الحكم: غير صادر. الحالة AUTHOR-RESERVED-SOUND-GAP حتى توقيع المؤلف للرجل الآرامية.",
            f"- العد من جدول الأسر: {samekh_cards} بطاقة أسرية آرامية من نوع TOOL-GAP تحمل السامخ وتنتظر فحص أثر هذه الرجل. والذخيرة الكاملة تحمل 245 مدخلًا بالسامخ.",
            "- مرجع القرار: `_inbox/2026-08-04-decision-paper-sound-rows.md`، البند الأول.",
            "",
            "## حصيلة الحالات الجديدة",
            "",
            "| الحالة بعد المرور | البطاقات |",
            "|---|---:|",
        ]
    )
    for status, amount in by_new.most_common():
        lines.append(f"| `{clean(status)}` | {amount} |")

    lines.extend(
        [
            "",
            "## سجل البطاقات وأسطر النسخ",
            "",
            "| رقم | اللسان والمصدر | البطاقة | الحكم السابق وسببه | الحكم بعد المرور | سطر النسخ |",
            "|---:|---|---|---|---|---|",
        ]
    )
    for index, record in enumerate(records, start=1):
        source_ref = f"{LANGUAGE_NAMES.get(str(record['language']), record['language'])}، `{record['source']}:{record['line']}`"
        previous = f"{clean(record['old'])}: {clean(record['old_reason'], 150)}"
        current = f"{clean(record['new'])}: {clean(record['reason'], 160)}"
        if record["changed"]:
            copy = f"سطر النسخ: السابق {previous}؛ الجديد {current}."
        else:
            copy = "لا سطر نسخ: الحكم لم يتغير."
        lines.append(
            f"| {index} | {source_ref} | {clean(record['head'], 120)} | {previous} | {current} | {copy} |"
        )

    lines.extend(
        [
            "",
            "## قيد عدم الترقية الآلية",
            "",
            "`OPEN-CANDIDATE` هنا حكم إعادة فتح لا حكم نسب. كل بطاقة تحتاج بعد رفع العائق قراءة معناها ومصدرها ومصافيها العضوية. أما `LAW-GAP` الباقي فهو صف تحول أو نطاق أو حذف لم توقعه صفوف الهوية.",
            "",
        ]
    )

    text = "\n".join(lines)
    if "\u2014" in text or "\u2013" in text:
        raise RuntimeError("تسربت شرطة طويلة إلى المحضر")
    OUTPUT.write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({"cards": len(records), "changed": changed_count, "samekh_cards": samekh_cards, "states": by_new}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
