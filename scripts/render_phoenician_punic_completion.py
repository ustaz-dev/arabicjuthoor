#!/usr/bin/env python3
"""Render the local member-by-member completion blocks for the bounded scouts.

The mappings below are the manually reviewed results of the 2026-07-23
completion pass.  The script only renders those recorded readings.  It never
infers a verdict, refreshes a shared ledger, or runs the proof line.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

from recovery_pipeline.inventory import DEFAULT_DB, connect
from search_arabic_root_senses import DEFAULT_RESOURCES, root_sense_fan


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-07-23"
FAN_CACHE_PATH = (
    ROOT / "cache" / "recovery_pipeline" / "phoenician-punic-root-fans.json"
)
LANGUAGES = {
    "phoenician": {
        "arabic": "الفينيقية",
        "reading": ROOT / "04-cross-linguistic" / "readings" / "phoenician-punic-scout.md",
        "source": ROOT / "Resources" / "phn" / "kaikki.org-phn-bounded-scout.jsonl",
        "scope_note": "استطلاع Kaikki محدود؛ لا يمثل معجم اللغة الفينيقية التاريخي كاملًا.",
    },
    "punic": {
        "arabic": "البونيقية",
        "reading": ROOT / "04-cross-linguistic" / "readings" / "punic.md",
        "source": ROOT / "Resources" / "xpu" / "kaikki.org-xpu-bounded-scout.jsonl",
        "scope_note": "استطلاع Kaikki محدود؛ لا يمثل معجم اللغة البونيقية التاريخي كاملًا.",
    },
}


# Direct or near-direct opportunities found by the human reading.  They remain
# non-verdicts unless they also occur in POSITIVES below.
TARGETS: dict[str, dict[int, str]] = {
    "phoenician": {
        3: "أرض", 4: "بيت", 5: "بعل", 7: "حلب", 8: "اسم", 9: "سلم",
        10: "شمس", 12: "دم", 14: "يد", 16: "لب", 17: "لسن",
        18: "كلب", 19: "بن", 21: "أخ", 24: "ضرر", 27: "ذقن",
        28: "أحد", 50: "بيت", 51: "عين", 52: "أنا", 53: "أنا",
        54: "أنت", 55: "أنت", 58: "نحن", 59: "هم", 60: "هم",
        63: "بن", 64: "جلجل", 65: "كوكب", 66: "قوم", 67: "ملك",
        69: "أربع", 70: "عكبر", 72: "سنة", 73: "كهن", 74: "أب",
        75: "إله", 76: "قدس", 77: "سماء", 79: "يم", 81: "لبن",
        82: "رب", 83: "ثني", 84: "ثلاث", 85: "ثلاث", 86: "أربع",
        87: "خمس", 88: "خمس", 89: "ست", 90: "ثمن", 91: "ثمن",
        92: "عشر", 93: "عشر", 94: "عشر", 95: "ثلاث", 96: "مئة",
        97: "ثلاث", 99: "أكل", 101: "حرث", 102: "رأس", 105: "ليل",
        117: "رب", 118: "كهن", 123: "قول", 124: "دبر", 126: "عصا",
        127: "إله", 128: "بنت", 129: "قرأ", 132: "باء", 133: "رجز",
        136: "قرن", 137: "بشر", 138: "يتم", 139: "مجن", 140: "عظم",
        141: "فعل", 146: "كمون", 149: "زيت", 150: "قعب",
        151: "نحن", 152: "أنا", 153: "أنتم", 155: "ثغر", 156: "جمل",
        159: "أي", 160: "قبر", 164: "بن", 166: "من", 167: "تحت",
        170: "نحاس",
    },
    "punic": {
        1: "أب", 2: "أرض", 3: "بيت", 4: "بعل", 5: "حلب", 6: "اسم",
        7: "سلم", 8: "هم", 9: "شمس", 10: "ماء", 11: "دم", 12: "لب",
        13: "لسن", 14: "كلب", 15: "بن", 16: "أخ", 19: "أخت",
        21: "فم", 22: "أنا", 23: "أنا", 25: "أنت", 26: "هي",
        28: "بن", 29: "قدس", 30: "قوم", 32: "أربع", 33: "سنة",
        35: "يوم", 36: "لبن", 37: "أحد", 38: "أحد",
        39: "ثني", 40: "ثلاث", 41: "ثلاث", 42: "سبع", 43: "تسع",
        44: "عشر", 45: "عشر", 46: "مئة", 48: "رأس",
        49: "أرض", 53: "زرع", 54: "عبد", 56: "ست", 57: "نذر",
        60: "ثور", 64: "قول", 65: "دبر", 67: "عصا", 68: "إله",
        69: "بنت", 70: "قرأ", 71: "باء", 74: "لي",
        85: "كمون", 87: "قثأ", 90: "حصر", 91: "ثغر", 92: "تين",
        98: "لبن",
    },
}


POSITIVES: dict[tuple[str, int], dict[str, str]] = {
    ("phoenician", 133): {
        "arabic": "رجز",
        "restored": "𐤓𐤂𐤆 rgz",
        "zero": "لا تعرية؛ الرسم النقشي ثلاثي كامل",
        "sound": "GUT-03 وحده: g الفينيقية ↔ ج العربية",
        "orbit": "مدار 1: الحدث؛ الإزعاج في الفرع هو إحداث الاضطراب المثبت في العربية",
        "judgment": "ROOT-TRACE",
        "filter": "لا مسار قرض منشور؛ اقتراح التأثيل الآخر في المصدر احتمالي لا يلغي فحص رجز المستقل",
    },
    ("phoenician", 160): {
        "arabic": "قبر",
        "restored": "𐤒𐤁𐤓 qbr",
        "zero": "لا تعرية؛ الرسم النقشي والجذر العربي متطابقان",
        "sound": "تطابق ذاتي q-b-r ↔ ق-ب-ر؛ لا صف لازم",
        "orbit": "مباشر: القبر ومدفن الميت",
        "judgment": "ROOT-TRACE",
        "filter": "لا مسار قرض معروف؛ المصدر نفسه يقارن العربية قَبْر",
    },
    ("phoenician", 167): {
        "arabic": "تحت",
        "restored": "𐤕𐤇𐤕 tḥt",
        "zero": "لا تعرية؛ اللفظ الوظيفي مثبت كاملًا في النقش",
        "sound": "تطابق ذاتي t-ḥ-t ↔ ت-ح-ت؛ لا صف لازم",
        "orbit": "مباشر: أسفل الشيء أو تحته",
        "judgment": "ROOT-TRACE",
        "filter": "لا مسار قرض معروف؛ المصدر نفسه يقارن العربية تحت",
    },
    ("punic", 36): {
        "arabic": "لبن",
        "restored": "𐤋𐤁𐤍 lbn < Proto-West Semitic *laban-",
        "zero": "لا تعرية؛ الصفة الثلاثية مثبتة في النقش",
        "sound": "تطابق ذاتي l-b-n ↔ ل-ب-ن؛ لا صف لازم",
        "orbit": "مدار 7: الصفة؛ البياض في الفرع تقابله مادة اللبن البيضاء في العائلة العربية",
        "judgment": "ROOT-TRACE",
        "filter": "المصدر يصرح بالميراث من السامية الغربية الأم، ولا ينشر مسار قرض",
    },
    ("punic", 54): {
        "arabic": "عبد",
        "restored": "𐤏𐤁𐤃 ʿbd",
        "zero": "لا تعرية؛ الرسم النقشي والجذر العربي متطابقان",
        "sound": "تطابق ذاتي ʿ-b-d ↔ ع-ب-د؛ لا صف لازم",
        "orbit": "مباشر: العبد المملوك أو الخادم",
        "judgment": "ROOT-TRACE",
        "filter": "المصدر يسميها ابتكارًا ساميًا مركزيًا ويقارن العربية عبد؛ لا مسار قرض خاص",
    },
    ("punic", 92): {
        "arabic": "تين",
        "restored": "𐤕𐤉𐤍 tyn < Proto-Semitic *tiʔin-",
        "zero": "لا تعرية؛ الياء مكتوبة في اللفظ الثلاثي",
        "sound": "تطابق ذاتي t-y-n ↔ ت-ي-ن؛ لا صف لازم",
        "orbit": "مباشر: ثمر التين",
        "judgment": "ROOT-TRACE",
        "filter": "المصدر يرده إلى السامية الأم ولا ينشر مسار قرض خاص",
    },
}


LOAN_ROWS = {
    ("phoenician", 144): "كلمة جوالة؛ اتجاه النقل غير محسوم",
    ("phoenician", 146): "من الأكادية kamūnu",
    ("phoenician", 148): "من مركب أكادي لمعنى نبات الزيت",
    ("phoenician", 149): "كلمة حضارية؛ يلزم حسم اتجاه الانتقال",
    ("punic", 80): "المصدر يسمي العربية كولان قرضًا آراميًا",
    ("punic", 82): "من الأكادية qanûm",
    ("punic", 85): "عبر الفينيقية من الأكادية kamūnu",
    ("punic", 86): "قرض إيراني يقارن الفارسية گزر",
    ("punic", 98): "سلعة عطرية مشتركة بين فروع ولغات؛ يلزم حسم اتجاه النقل قبل حكم النسب",
}


PROPER_NAME_ROWS = {
    ("phoenician", 106): "اسم الإلهة إيزيس، لا اسم جنس معجمي",
    ("punic", 104): "قادس اسم موضع، وإن صنفته اللقطة اسم جنس",
    ("punic", 106): "Sexi اسم مستعمرة، وإن صنفته اللقطة اسم جنس",
}


FUNCTION_POS = {"pron", "prep", "particle", "article", "adv", "conj"}


LAW_GAPS = {
    ("phoenician", 3): "تقابل ʾrṣ ↔ أرض يحتاج صف الصاد/الضاد في الفرع",
    ("phoenician", 24): "تقابل ṣrt ↔ ضرة يحتاج صف الصاد/الضاد وتحليل التاء",
    ("phoenician", 27): "تقابل zqn ↔ ذقن يحتاج صفًا شماليًّا غربيًّا موقعًا للذال",
    ("phoenician", 65): "كوكب يحتاج تحليل الواو الداخلية من الصورة السامية المنشورة",
    ("phoenician", 83): "تقابل šnm ↔ اثنان يحتاج DENT-02 وتحليل بنية العدد",
    ("phoenician", 84): "تقابل šlšt ↔ ثلاث يحتاج نطاقًا فينيقيًا لـDENT-02 وتحليل التاء",
    ("phoenician", 85): "تقابل šlš ↔ ثلاث يحتاج نطاقًا فينيقيًا لـDENT-02",
    ("phoenician", 95): "العدد المركب šlšm يحتاج تحليل ثلاث + علامة العشرات ونطاقًا فينيقيًا لـDENT-02",
    ("phoenician", 97): "العدد المركب šlšmʾt يحتاج تحليل ثلاث + مئة ونطاقًا فينيقيًا لـDENT-02",
    ("phoenician", 101): "تقابل ḥrš ↔ حرث يحتاج صف š ↔ ث خاصًا بالسلسلة التاريخية",
    ("phoenician", 124): "دبور يحتاج تحليل التاء الاسمية والواو الداخلية قبل الحكم",
    ("phoenician", 150): "تقابل qbʿ ↔ قعب يحتاج قانون قلب صوامت منشورًا لا تشابهًا حرًا",
    ("phoenician", 155): "تقابل šʿr ↔ ثغر يحتاج صفين تاريخيين ولا يرخّص بالتشابه وحده",
    ("phoenician", 170): "نحاس يحتاج تفسير t الفينيقية أمام س العربية",
    ("punic", 2): "تقابل ʾrṣ ↔ أرض يحتاج صف الصاد/الضاد في الفرع",
    ("punic", 21): "تقابل p «الفم» ↔ فم يحتاج صف p ↔ ف وتحليل الميم العربية",
    ("punic", 39): "تقابل šn ↔ اثنان يحتاج نطاقًا بونيقيًا لـDENT-02 وتحليل بنية العدد",
    ("punic", 40): "تقابل šlš ↔ ثلاث يحتاج نطاقًا بونيقيًا لـDENT-02",
    ("punic", 41): "صيغة العدد šʿlš تحتاج تحليلًا منشورًا ونطاقًا بونيقيًا لـDENT-02",
    ("punic", 49): "الصورة ʾrs تحتاج صف الصفير/الإطباق قبل ردها إلى أرض",
    ("punic", 53): "تقابل zrʾ ↔ زرع يحتاج صف الهمزة/العين في هذا الفرع",
    ("punic", 56): "صيغة الستين ššm تحتاج تحليلًا صرفيًا وصوتيًا منشورًا",
    ("punic", 57): "تقابل ndr ↔ نذر يحتاج نطاقًا بونيقيًا لصف الذال",
    ("punic", 60): "تقابل šr ↔ ثور يحتاج DENT-02 واستعادة الواو بمصدر صرفي",
    ("punic", 65): "دبور يحتاج تحليل التاء الاسمية والواو الداخلية قبل الحكم",
    ("punic", 87): "المصدر يقارن قثاء مباشرة، لكن DENT-02 لا يسمي البونيقية في نطاقه الحالي",
    ("punic", 91): "تقابل šʿr ↔ ثغر يحتاج صفين تاريخيين ولا يرخّص بالتشابه وحده",
}


# Regression witnesses for row-drift errors caught by the second manual audit.
# These are deliberately semantic, not merely syntactic: a future edit must not
# silently restore any of the known wrong source-row/Arabic-target pairings.
FORBIDDEN_TARGETS = {
    ("phoenician", 68): "أربع",  # source row 68 is a band, not the numeral
    ("phoenician", 138): "فعل",  # source row 138 is an orphan
    ("punic", 47): "يرح",        # source row 47 is the moon, not an approved Arabic root
    ("punic", 76): "فلش",        # source row 76 is an architect
    ("punic", 77): "شتل",        # source row 77 is a coffin
}


def validate_manual_tables() -> None:
    for (language, row), forbidden_target in FORBIDDEN_TARGETS.items():
        actual = TARGETS.get(language, {}).get(row)
        if actual == forbidden_target:
            raise ValueError(
                f"forbidden row-drift mapping restored: "
                f"{language}:{row} ↔ {actual}"
            )
    target_keys = {
        (language, row)
        for language, rows in TARGETS.items()
        for row in rows
    }
    missing_targets = sorted(set(POSITIVES) - target_keys)
    if missing_targets:
        raise ValueError(f"positive cards without reviewed targets: {missing_targets}")


def clean(value: Any, limit: int | None = None) -> str:
    text = unicodedata.normalize("NFC", str(value or ""))
    text = " ".join(text.replace("\u2013", "-").replace("\u2014", "-").split())
    if limit and len(text) > limit:
        return text[: limit - 1].rstrip() + "…"
    return text


def source_rows(path: Path) -> dict[int, dict[str, Any]]:
    return {
        index: json.loads(line)
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
    }


def source_line(entry_id: str) -> int:
    match = re.search(r":(\d+):", entry_id)
    if not match:
        raise ValueError(f"source row missing from entry id: {entry_id}")
    return int(match.group(1))


def first_reference(raw: dict[str, Any]) -> str:
    for sense in raw.get("senses", []):
        for example in sense.get("examples", []):
            reference = example.get("ref")
            if reference is not None:
                if not isinstance(reference, str):
                    reference = json.dumps(reference, ensure_ascii=False)
                return clean(reference, 520)
    return ""


def candidate_ladder(connection: sqlite3.Connection, entry_id: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    rows = connection.execute(
        """
        SELECT c.kind,c.form,c.status,c.rule_ids_json,c.route_flag,a.reading
        FROM candidates c
        LEFT JOIN arabic_forms a ON a.form=c.form AND a.kind=c.kind
        WHERE c.entry_id=?
        ORDER BY CASE c.status WHEN 'licensed' THEN 0 WHEN 'manual-condition' THEN 1 ELSE 2 END,
                 CASE c.kind WHEN 'root' THEN 0 WHEN 'hollow-root' THEN 1 ELSE 2 END,
                 c.form
        """,
        (entry_id,),
    ).fetchall()
    for row in rows:
        if row["status"] != "licensed" or row["route_flag"]:
            continue
        rules = json.loads(row["rule_ids_json"])
        route = "مباشر" if not rules else "+".join(rules)
        reading = clean(row["reading"]) or "بلا قراءة نصية"
        result[row["kind"]].append(f"{row['form']} «{reading}» [{route}]")
    return result


def fan_summary(root: str, cache: dict[str, dict[str, Any]]) -> str:
    if root not in cache:
        cache[root] = root_sense_fan(DEFAULT_RESOURCES, root, 360)
    fan = cache[root]["independent_fan"]
    selected = fan["selected_sources"]
    if not selected:
        return f"{root}: لا مدخلين عربيين قديمين مستقلين غير فارغين في الذخيرة المحلية."
    return (
        f"{root}: المصدران المستعملان: "
        + "، ".join(clean(item["source_label"]) for item in selected)
        + "؛ "
        + "؛ ".join(
            f"{clean(item['source_label'])}: «{clean(item['definition'], 300)}»"
            for item in selected
        )
    )


def frozen_reading(connection: sqlite3.Connection, root: str) -> str:
    row = connection.execute(
        "SELECT reading FROM arabic_forms WHERE form=? AND kind='root'",
        (root,),
    ).fetchone()
    return clean(row["reading"]) if row else "(لا مقابل من الأداة المجمدة)"


def source_note(raw: dict[str, Any], row: int) -> str:
    reference = first_reference(raw)
    etymology = clean(raw.get("etymology_text"), 520)
    parts = [f"Kaikki bounded scout، السطر {row}"]
    if reference:
        parts.append(reference)
    if etymology:
        parts.append(f"نص التأثيل: {etymology}")
    return "؛ ".join(parts)


def render_positive(
    language: str,
    entry: sqlite3.Row,
    raw: dict[str, Any],
    ruling: dict[str, str],
    connection: sqlite3.Connection,
    fan_cache: dict[str, dict[str, Any]],
) -> list[str]:
    root = ruling["arabic"]
    reading = frozen_reading(connection, root)
    reference = source_note(raw, source_line(entry["entry_id"]))
    return [
        f"### بطاقة: {entry['romanization'] or entry['headword']} «{clean(entry['gloss'])}»",
        "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)",
        f"- معرّف العضو: `{entry['entry_id']}`",
        f"- معرّف الأسرة: `{entry['family_id']}`",
        f"- الكلمةُ في الفرع: {entry['headword']} `{clean(entry['romanization'])}`",
        f"- أقدمُ صورةٍ مستعادة: {ruling['restored']} [{reference}]",
        f"- الخطوةُ صفر (التعرية بصرف الفرع): {ruling['zero']} ← اللب: {entry['romanization'] or entry['headword']}",
        "- درجةُ المقارنة: جذر كامل",
        f"- مسحُ المعاني العربيّة: {fan_summary(root, fan_cache)}",
        f"- المقابلُ من اللسان: {root} «{reading}»",
        f"- مسارُ الصوت: {ruling['sound']}",
        f"- المعنى من قاموس الفرع: «{clean(entry['gloss'])}» [Kaikki bounded scout، السطر {source_line(entry['entry_id'])}]",
        f"- المدار: {ruling['orbit']}",
        f"- المصفاة: {ruling['filter']}",
        "- فصلُ المتجانسات والاقتراض: الحكم خاص بهذا العضو وسلسلة معناه؛ لا يرثه متجانس أو مركب أو صورة أخرى.",
        "- مؤشر اليتم: العضو مثبت في أسرته الحية، ولا صورة صرفية يتيمة لازمة للحكم.",
        "- إشعاع الأسرة في الفرع: الأعضاء المعجمية المدعومة=1؛ سلاسل المعنى المدعومة=1؛ العد خاص بهذا العضو بعد حق النقض.",
        "- إشعاع الأسرة في العربية: الأعضاء المعجمية المدعومة=1؛ سلاسل المعنى المدعومة=1؛ العد خاص بالمعنى العربي المستشهد به من المروحة.",
        "- جسورُ الاسترداد المفحوصة: الجذر الكامل؛ الجذر الأجوف؛ النواة؛ الأخت السامية؛ شاهد المصدر الفردي؛ الجسر الدلالي المباشر أو المدار الواحد المسمى.",
        "- حالةُ الإغلاق: READY",
        f"- الحكم (استكشاف): {ruling['judgment']}",
        "- القراءة الدلالية العضوية: اكتملت المروحة العربية وفُصل العضو ومعناه، فصدر الحكم المحلي أعلاه وحده.",
        "- ملاحظات: عدسة الاسترداد أثبتت أقدم صورة والجذر والمروحة والجسر. عدسة التشكيك فحصت القرض والمتجانسات ونطاق المصدر، ولم تجد مانعًا بعد القيد المعلن. الحكم محلي ينتظر المراجعة الثالثة قبل أي إيداع.",
        "",
    ]


def render_review(
    language: str,
    entry: sqlite3.Row,
    raw: dict[str, Any],
    connection: sqlite3.Connection,
    fan_cache: dict[str, dict[str, Any]],
) -> list[str]:
    row = source_line(entry["entry_id"])
    target = TARGETS.get(language, {}).get(row)
    ladder = candidate_ladder(connection, entry["entry_id"])
    roots = "؛ ".join(ladder.get("root", [])[:4]) or "لا جذر كامل مرخص من الفهرس"
    hollows = "؛ ".join(ladder.get("hollow-root", [])[:4]) or "لا أجوف مرخص من الفهرس"
    nuclei = "؛ ".join(ladder.get("nucleus", [])[:5]) or "لا نواة مرخصة ظاهرة"
    key = (language, row)
    reference = first_reference(raw)
    etymology = clean(raw.get("etymology_text"), 460)

    if key in PROPER_NAME_ROWS:
        result = "PROPER-NAME-ISOLATED"
        blocker = "لا حكم نسب في المعجم العام؛ يفتح فقط في حملة أسماء مستقلة"
        organic = PROPER_NAME_ROWS[key]
        filter_note = "عزل علم صريح بعد القراءة البشرية، ولو أخطأ وسم الجزء النحوي في اللقطة."
    elif key in LOAN_ROWS:
        result = "LOAN-ROUTE-ISOLATED"
        blocker = "توثيق اتجاه النقل وطبقته بمصدر تأثيل فردي مستقل قبل أي حكم نسب"
        organic = f"المصدر يصرح بمسار اتصال: {LOAN_ROWS[key]}. فُحص الشبه العربي ولم يُحوّل القرض إلى قرابة."
        filter_note = "مصفاة الاقتراض سبقت الحكم وأبقت المسار ظاهرًا."
    elif key in LAW_GAPS:
        result = "LAW-GAP"
        blocker = LAW_GAPS[key]
        fan = fan_summary(target, fan_cache) if target else "لا هدف عربي مسمى"
        organic = f"الفرصة الأقوى هي `{entry['headword']} ↔ {target}`. مروحتها: {fan} لكن القانون الصوتي أو الصرفي الناقص يمنع الحكم."
        filter_note = "لا قرض منشور حاكم، لكن غياب القانون المرخص كاف لإيقاف الحكم."
    elif entry["pos"] in FUNCTION_POS:
        result = "SOURCE-GAP"
        blocker = "شاهد نحوي تاريخي فردي ومقارنة وظيفية منشورة؛ لا تُقاس الأداة بوصفها جذر اسم جنس"
        organic = "قُرئ العضو بوصفه ضميرًا أو أداة أو حرفًا، وفُصل عن المتجانسات الاسمية. التشابه السطحي لا يمنحه حكم جذر."
        filter_note = "المصفاة النحوية تمنع خلط الأداة باسم أو فعل يشترك معها في الرسم."
    elif target:
        result = "SOURCE-GAP"
        blocker = "إسناد فينيقي أو بونيقي منشور فردي وراء اللمة قبل إصدار الحكم المحلي"
        fan = fan_summary(target, fan_cache)
        organic = f"الفرصة الأقوى بعد نزول السلم هي `{entry['headword']} ↔ {target}`. المروحة العربية: {fan} بقيت فرصة قوية غير منفية، لكن شاهد الفرع الفردي غائب."
        filter_note = "لا مسار قرض صريح في الحقل، وغيابه لا يثبت الأصالة."
    else:
        result = "SOURCE-GAP"
        blocker = "إسناد فرعي فردي ومقابل عربي معتمد بعد استنفاد السلم؛ لا يصدر NO-TRACE من لقطة محدودة"
        organic = (
            f"قُرئ معنى «{clean(entry['gloss'])}» على الكامل والأجوف والنواة. "
            "لم تمنح المخرجات الحالية جسرًا دلاليًا مباشرًا أو مدارًا واحدًا مسمى، "
            "فحُفظت المرشحات ولم تتحول إلى رفض تاريخي."
        )
        filter_note = "لا مسار قرض صريح في الحقل، وغيابه لا يثبت الأصالة."

    source_status = (
        f"شاهد مسمى: {reference}" if reference else "لا يحمل السطر شاهدًا فرديًا مسمى"
    )
    return [
        f"### مراجعة عضوية: {entry['headword']} `{clean(entry['romanization'])}` «{clean(entry['gloss'])}»",
        f"- معرّف العضو: `{entry['entry_id']}`",
        f"- معرّف الأسرة: `{entry['family_id']}`",
        f"- قيد النطاق: {LANGUAGES[language]['scope_note']}",
        f"- القراءة الدلالية العضوية: {organic}",
        f"- السلم الكامل: الجذر={roots}؛ الأجوف={hollows}؛ النواة={nuclei}؛ المدار={'مسمى في القراءة أعلاه' if target else 'لا مدار واحد صالح في المخرجات الحالية'}.",
        f"- المصدر الفردي: {source_status} [Kaikki bounded scout، السطر {row}]"
        + (f"؛ نص التأثيل: {etymology}" if etymology else ""),
        f"- المصفاة: {filter_note}",
        "- فصل المتجانسات: الحكم أو العائق خاص بهذا العضو؛ لا وراثة من عضو آخر في الأسرة ولا من مركب.",
        f"- النتيجة العضوية: {result}",
        f"- عائق: النوع={result if result in {'LAW-GAP', 'SOURCE-GAP', 'TOOL-GAP', 'MORPHOLOGY-GAP'} else 'SOURCE-GAP'}؛ يتطلب={blocker}",
        "- الحكم (استكشاف): غير صادر.",
        "- عدسة الاسترداد: جُرب الكامل والأجوف والنواة والمروحة والشاهد والتأثيل، وسميت أقوى فرصة بدل إسقاطها.",
        "- عدسة التشكيك: فُحص المصدر والقرض والمتجانسات والقانون الصوتي وحق النقض العضوي، فمنع الحكم حيث بقي مانع.",
        "",
    ]


def entries(connection: sqlite3.Connection, language: str) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT fm.family_id,fm.entry_id,fm.role,e.headword,e.romanization,
               e.pos,e.gloss,e.source_stratum,e.source_scope_note
        FROM family_members fm
        JOIN entries e ON e.entry_id=fm.entry_id
        WHERE e.language=?
          AND fm.role<>'nonlexical'
          AND e.source_stratum NOT IN ('proper-name','reconstruction')
        ORDER BY fm.family_id,e.entry_id
        """,
        (language,),
    ).fetchall()


def render(
    language: str,
    connection: sqlite3.Connection,
    fan_cache: dict[str, dict[str, Any]],
) -> str:
    raw_by_row = source_rows(LANGUAGES[language]["source"])
    selected = entries(connection, language)
    positive_count = sum(
        (language, source_line(entry["entry_id"])) in POSITIVES
        for entry in selected
    )
    lines = [
        f"<!-- {language.upper()}-COMPLETE-{DATE}:BEGIN -->",
        "",
        f"## ملحق الإكمال العضوي للّقطة {LANGUAGES[language]['arabic']}",
        "",
        f"**التاريخ:** {DATE}. **الحالة:** دفعة أحكام محلية تنتظر المراجعة الثالثة.",
        "",
        f"- المقام الحي في هذا الملحق: {len(selected)} عضوًا معجميًا في كل الأسر المعجمية للّقطة.",
        f"- بطاقات الحكم الموجب المحلية: {positive_count}. بقية الأعضاء تحمل قراءة عضوية وعائقًا مسمى أو عزلًا.",
        f"- قيد الشمول: {LANGUAGES[language]['scope_note']}",
        "- لا تشغيل لخط البرهان، ولا تجديد للسجل المركزي، ولا تعديل لأداة مجمدة، ولا اعتماد لمصدر جديد.",
        "",
    ]
    for entry in selected:
        row = source_line(entry["entry_id"])
        raw = raw_by_row[row]
        ruling = POSITIVES.get((language, row))
        if ruling:
            lines.extend(
                render_positive(
                    language, entry, raw, ruling, connection, fan_cache
                )
            )
        else:
            lines.extend(
                render_review(
                    language, entry, raw, connection, fan_cache
                )
            )
    lines += [
        "## محضر الإغلاق",
        "",
        f"قُرئ كل عضو معجمي في لقطة {LANGUAGES[language]['arabic']} على سلم الجذر الكامل ثم الأجوف ثم النواة والمدار الواحد. اكتمل مقام اللقطة قراءة ومحاسبة، وبقي قيد عدم تمثيل المعجم التاريخي كاملًا نافذًا.",
        "",
        f"<!-- {language.upper()}-COMPLETE-{DATE}:END -->",
        "",
    ]
    return unicodedata.normalize("NFC", "\n".join(lines))


def update_block(path: Path, language: str, block: str, check: bool) -> bool:
    begin = f"<!-- {language.upper()}-COMPLETE-{DATE}:BEGIN -->"
    end = f"<!-- {language.upper()}-COMPLETE-{DATE}:END -->"
    current = path.read_text(encoding="utf-8")
    pattern = re.compile(re.escape(begin) + r".*?" + re.escape(end) + r"\n?", re.S)
    match = pattern.search(current)
    if check:
        return bool(match and match.group(0).rstrip() == block.rstrip())
    if match:
        updated = current[: match.start()] + block + current[match.end():]
    else:
        updated = current.rstrip() + "\n\n" + block
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(updated, encoding="utf-8", newline="\n")
    temporary.replace(path)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=sorted(LANGUAGES), action="append")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    validate_manual_tables()
    languages = args.language or sorted(LANGUAGES)
    connection = connect(args.db.resolve(), create=False)
    connection.row_factory = sqlite3.Row
    problems: list[str] = []
    fan_cache: dict[str, dict[str, Any]] = (
        json.loads(FAN_CACHE_PATH.read_text(encoding="utf-8"))
        if FAN_CACHE_PATH.exists()
        else {}
    )
    try:
        for language in languages:
            block = render(language, connection, fan_cache)
            path = LANGUAGES[language]["reading"]
            if not update_block(path, language, block, args.check):
                problems.append(f"stale or missing completion block: {language}")
            elif not args.check:
                print(f"wrote local completion block: {language}")
    finally:
        connection.close()
    if not args.check:
        FAN_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = FAN_CACHE_PATH.with_suffix(FAN_CACHE_PATH.suffix + ".tmp")
        temporary.write_text(
            json.dumps(fan_cache, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(FAN_CACHE_PATH)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1
    if args.check:
        print("bounded completion blocks: CLEAN (" + ", ".join(languages) + ")")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
