#!/usr/bin/env python3
"""Refine the 29 Hebrew temporal blockers covered by the witness inventory.

The pass is member-level and deliberately does not manufacture negatives.
It distinguishes an old witness for the judged member from a witness for a
homonym, compound head, inflected form, or modern sense. Verdict-bearing
output remains local for the third-lens review.
"""
from __future__ import annotations

import json
import re
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path

import build_status_snapshot as status
from search_arabic_root_senses import (
    ARABIC_MARKS,
    DEFAULT_RESOURCES,
    independent_fan,
    matches_for_roots,
)


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
QUEUE = ROOT / "data" / "hebrew-biblical-priority-queue.json"
AUDIT = (
    ROOT
    / "05-audits"
    / "2026-07-27-hebrew-biblical-priority-batch-01-local.md"
)
DATE = "2026-07-27"
BATCH = "HEBREW-BIBLICAL-01"

SECTION = re.compile(r"(?=^### )", re.MULTILINE)
CARD = re.compile(
    r"^### بطاقة: `(?P<family>hebrew:family:[0-9a-f]+)`، "
    r"(?P<title>[^\n]+)$",
    re.MULTILINE,
)
BLOCKER = re.compile(r"^-\s*عائق:\s*.+$", re.MULTILINE)
OLDEST = re.compile(r"^-\s*أقدمُ?\s*صورةٍ مستعادة:\s*.+$", re.MULTILINE)
LAYER = re.compile(r"^-\s*طبقة المصدر:\s*.+$", re.MULTILINE)
SCAN = re.compile(r"^-\s*مسحُ?\s*المعاني العربيّة:\s*.+$", re.MULTILINE)
CLOSURE = re.compile(r"^-\s*حالةُ الإغلاق:\s*.+$", re.MULTILINE)
VERDICT = re.compile(r"^-\s*الحكم \(استكشاف\):\s*.+$", re.MULTILINE)

LISAN_TAJ = "لسان العرب لابن منظور + تاج العروس لمرتضى الزبيدي"
LISAN_SIHAH = (
    "لسان العرب لابن منظور + تاج اللغة وصحاح العربية للجوهري"
)


POSITIVES = {
    "hebrew:family:38483fda89fd8b5f648c582a": {
        "entry": "kaikki_hebrew:2915:en-פשר-he-noun-~9Grm4ij",
        "root": "فسر",
        "terms": ("البيان", "التفسير"),
        "verdict": "ROOT-TRACE",
        "scope": "פשר الاسم «حل وتفسير وبيان» وحده، لا فعل الذوبان",
        "sound": (
            "LAB-07 في פ ↔ ف، وSIB-01 في ש ↔ س؛ الراء هوية"
        ),
        "bridge": "مباشر: التفسير بيان المعنى وكشفه",
    },
    "hebrew:family:6bd3d1998ce72f6d01894b75": {
        "entry": "kaikki_hebrew:9642:en-עופר-he-noun-ufjA216x",
        "root": "عفر",
        "terms": ("يعفور", "غزال"),
        "verdict": "ROOT-TRACE",
        "scope": "עופר «ولد الظبي أو الغزال» وحده",
        "sound": (
            "الصورة البديلة المنشورة עפר تثبت الجذر ע־פ־ר؛ "
            "LAB-07 وحده في פ ↔ ف، والعين والراء هويتان"
        ),
        "bridge": "مباشر: اليعفور ولد البقرة الوحشية أو الظبي",
    },
}

REFERRALS = {
    "hebrew:family:4a900ea234a9fe3b66df46db": (
        "بطاقة שטר، حسم الموجة 1 للرتبة 203"
    ),
    "hebrew:family:9455eef60a584bf43a52ea9d": (
        "بطاقة כור، حسم الموجة 1 للرتبة 208"
    ),
    "hebrew:family:49d7f0c08f18557cee421a5e": (
        "بطاقة כפר، حسم الموجة 1 للرتبة 298"
    ),
}

OPEN = {
    "hebrew:family:62544dfa8e220a68238f2998": (
        "الشاهد التوراتي يثبت عضو נכס «الممتلكات» نفسه؛ المروحة "
        "مستنفدة، لكن لا جسر دلالي مباشر أو مدار واحد مسمى بعد"
    ),
    "hebrew:family:ae9fe2a5cc4e0dd7a6188f59": (
        "الشاهد المشناوي يثبت כותל «الجدار»؛ المروحة مستنفدة، "
        "ويبقى الجسر الدلالي العضوي غير محكوم"
    ),
    "hebrew:family:f1d0e2e0a18b2ae73445ac25": (
        "الشاهد التوراتي يثبت נקע «اغترب أو تناءى»؛ المروحة العربية "
        "لا تعطي معنى الخلع أو الاغتراب مباشرة"
    ),
    "hebrew:family:f40279852ba514a87eb5345a": (
        "الشاهد التوراتي يثبت חירף «شتم وازدرى»؛ المروحة مستنفدة "
        "ولا جسر معنى مباشر محكوم بعد"
    ),
    "hebrew:family:f47dbd03e3209cb600b751b9": (
        "الشاهد التوراتي يثبت בול اسم الشهر وحده؛ عضو طابع البريد "
        "الحديث قرض عربي ولا يرثه الاسم القديم"
    ),
    "hebrew:family:240f05b072512f6dce4725ee": (
        "الشاهد التوراتي يثبت צלל «غاص» وحده، لا סלל «عبّد الطريق»؛ "
        "المروحة لا تعطي جسرًا مباشرًا بعد"
    ),
    "hebrew:family:1d7e7dc2610a47c0da54622c": (
        "الشاهد التوراتي يثبت נפל «سقط»؛ المروحة مستنفدة ولا مقابل "
        "عربي مرخص مطابق دلاليًا بعد"
    ),
    "hebrew:family:9238f690df711487e0a4151c": (
        "الشاهد التوراتي يثبت הדר «بهاء ومجد»؛ العلم العضوي لا يرث "
        "حكم الاسم، ولا جسر معنى مباشر محكوم بعد"
    ),
    "hebrew:family:b4b1c86a02d90d27237036dd": (
        "الشاهد التوراتي يثبت חצב «قطع الحجر ونحته»؛ حصب العربية "
        "تعطي الحجر أو الرمي به، ويحتاج مدار المادة والفعل مراجعة ثالثة"
    ),
    "hebrew:family:3db152a9f23a5a276d59afd6": (
        "الشاهد التوراتي يثبت גידל «كبّر ونمّى»؛ جدل العربية والنواة "
        "جد تعطيان مرشح امتداد وقوة، لكن الجسر العضوي غير محكوم"
    ),
}

SOURCE_GAPS = {
    "hebrew:family:bc041095617275a9352abbde": (
        "شاهد 1891 حديث؛ يتطلب شاهدًا عبريًا قديمًا لعضو קרן «القرن» "
        "نفسه، ولا يرث المركب חד קרן شيئًا"
    ),
    "hebrew:family:46b8cef71b8f74c3fa545272": (
        "الشواهد التوراتية تخص לבד الظرف «وحده»؛ عضو اللباد لا شاهد "
        "قديمًا له ومسار العربية من الآرامية لا يحكم الظرف"
    ),
    "hebrew:family:52b64bd98786a4292a6f6304": (
        "أقدم الإحالات المسجلة تلمودية نحو 500 م، لا توراتية ولا "
        "مشنائية؛ يتطلب شاهد طبقة قديمة معتمدًا للعضو"
    ),
    "hebrew:family:8c561575cda5f5edd5453ea4": (
        "الشاهد التوراتي يخص רהב العلم الأسطوري؛ يعزل العلم، ويبقى "
        "اسم الكبر والغرور بلا شاهد قديم للعضو نفسه"
    ),
    "hebrew:family:948f42ae4b172d0a26963abb": (
        "أقدم شاهد مسجل سنة 1170 م؛ يتطلب شاهدًا توراتيًا أو مشنائيًا "
        "لعضو חיבר نفسه"
    ),
    "hebrew:family:e69ed3112810d1347b65dadf": (
        "الشاهد التوراتي يثبت קסת «المحبرة»، لكن اشتقاقه بين مشتق "
        "عبري وقرض مصري محتمل؛ يتطلب حسم المانح المنشور قبل حكم النسب"
    ),
    "hebrew:family:56cc63fb81a2d0592dad895b": (
        "الشاهد المسجل حديث من 2008؛ يتطلب شاهدًا توراتيًا أو مشنائيًا "
        "لعضو סיבה نفسه"
    ),
    "hebrew:family:997b8b6e04eca3c0a9885dc7": (
        "الشاهد المسجل حديث من 2019؛ يتطلب شاهدًا توراتيًا أو مشنائيًا "
        "لعضو סיקר نفسه"
    ),
    "hebrew:family:b9eb8946d7e71e5890e53dc6": (
        "الشاهد المسجل حديث من 1880؛ يتطلب شاهدًا توراتيًا أو مشنائيًا "
        "لعضو גבר «الديك» نفسه"
    ),
    "hebrew:family:8cce0b6400f5f3c2eb51ebd6": (
        "الشاهد المسجل حديث من 2016؛ يتطلب شاهدًا توراتيًا أو مشنائيًا "
        "لعضو תקן نفسه"
    ),
}

LAW_GAPS = {
    "hebrew:family:38cbdb6465bbfff4a6e62207": (
        "العضو المشناوي צרה «الضرة» يقابل ضرة دلاليًا، لكن الشبكة لا "
        "تحمل صفًا موقعًا لـצ العبرية أمام ض العربية؛ DENT-08 خاص بظ"
    )
}

MORPHOLOGY_GAPS = {
    "hebrew:family:eeb0abf29e54740c5d7db43b": (
        "الشاهد التوراتي واقع على מטה الصيغة المصرفة؛ يتطلب ربطًا "
        "صرفيًا منشورًا يردها إلى הטה قبل تعرية البادئة أو الحكم"
    ),
    "hebrew:family:6009686422a880f5e5f0b702": (
        "الشاهد التوراتي يثبت מעוז، لكن مقارنة עוז أو عوز تتطلب "
        "تحليل الميم الاشتقاقية العبرية تحليلًا منشورًا لا حدسيًا"
    ),
}

TERMINALS = {
    "hebrew:family:68ef4409d6b92e623ac9d0ad": (
        "LOANWORD",
        "גיר «الجير والحجر الكلسي» ذو شاهد توراتي، ومصدره يسمي "
        "السومرية GIR مانحًا خارجيًا؛ يعزل عن النسب",
    )
}


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        delete=False,
    ) as handle:
        handle.write(unicodedata.normalize("NFC", text))
        temporary = Path(handle.name)
    temporary.replace(path)


def replace_one(
    section: str, pattern: re.Pattern[str], replacement: str
) -> tuple[str, str]:
    match = pattern.search(section)
    if not match:
        raise ValueError(f"missing field: {pattern.pattern}")
    old = match.group(0)
    return (
        section[: match.start()] + replacement + section[match.end() :],
        old,
    )


def fold_arabic(value: str) -> str:
    value = ARABIC_MARKS.sub("", unicodedata.normalize("NFKC", value))
    return " ".join(value.split())


def excerpt(definition: str, terms: tuple[str, ...]) -> str:
    folded = fold_arabic(definition)
    positions = [
        folded.find(fold_arabic(term))
        for term in terms
        if folded.find(fold_arabic(term)) >= 0
    ]
    if not positions:
        raise ValueError(f"semantic terms absent: {terms}")
    start = max(0, min(positions) - 70)
    end = min(len(folded), min(positions) + 240)
    return folded[start:end]


def positive_fans() -> dict[str, list[dict[str, str]]]:
    roots = {str(item["root"]) for item in POSITIVES.values()}
    matches = matches_for_roots(DEFAULT_RESOURCES, roots, None)
    result: dict[str, list[dict[str, str]]] = {}
    for specification in POSITIVES.values():
        root = str(specification["root"])
        fan = independent_fan(matches[root])
        if not fan["judgment_ready"]:
            raise ValueError(f"incomplete old-Arabic fan for {root}")
        rows = []
        for witness in fan["selected_sources"][:2]:
            rows.append(
                {
                    "source": str(witness["source_label"]),
                    "excerpt": excerpt(
                        str(witness["definition"]),
                        tuple(specification["terms"]),
                    ),
                }
            )
        if len(rows) != 2:
            raise ValueError(f"two independent sources required for {root}")
        result[root] = rows
    return result


def witness_summary(item: dict[str, object]) -> str:
    witnesses = item["witnesses"]
    return "؛ ".join(
        f"{row['headword']}، {row['stratum']}، {row['reference']}"
        for row in witnesses
    )


def decision_for(family: str) -> tuple[str, str, str]:
    if family in POSITIVES:
        item = POSITIVES[family]
        return (
            "positive",
            "READY",
            f"{item['verdict']}؛ {item['scope']}؛ {item['bridge']}",
        )
    if family in REFERRALS:
        return (
            "referral",
            "REFERRED",
            f"إحالة إلى {REFERRALS[family]}؛ لا عد مزدوج",
        )
    if family in OPEN:
        return ("open", "OPEN-CANDIDATE", OPEN[family])
    if family in SOURCE_GAPS:
        return ("source-gap", "SOURCE-GAP", SOURCE_GAPS[family])
    if family in LAW_GAPS:
        return ("law-gap", "LAW-GAP", LAW_GAPS[family])
    if family in MORPHOLOGY_GAPS:
        return (
            "morphology-gap",
            "MORPHOLOGY-GAP",
            MORPHOLOGY_GAPS[family],
        )
    if family in TERMINALS:
        state, reason = TERMINALS[family]
        return ("terminal", state, reason)
    raise ValueError(f"no decision for {family}")


def main() -> int:
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    target_rows = [
        *queue["blocked_temporal_cards_with_references"],
        *queue.get("refined_temporal_cards_with_references", []),
    ]
    targets = {str(item["family_id"]): item for item in target_rows}
    if len(targets) != 29:
        raise ValueError(f"expected 29 temporal targets, got {len(targets)}")
    fans = positive_fans()
    text = READING.read_text(encoding="utf-8")
    output: list[str] = []
    records: list[dict[str, str]] = []

    for section in SECTION.split(text):
        match = CARD.match(section)
        if not match or match.group("family") not in targets:
            output.append(section)
            continue
        family = match.group("family")
        marker = f"<!-- HEBREW-TEMPORAL-PRIORITY:{BATCH}:{family} -->"
        if marker in section:
            output.append(section)
            records.append(
                {
                    "family": family,
                    "kind": decision_for(family)[0],
                    "state": decision_for(family)[1],
                }
            )
            continue
        old_blocker = BLOCKER.search(section)
        if not old_blocker or "وسم طبقة أو نطاق زمني منشور" not in (
            old_blocker.group(0)
        ):
            output.append(section)
            continue

        kind, state, reason = decision_for(family)
        history: list[str] = []
        section, old = replace_one(
            section,
            BLOCKER,
            f"- عائق: النوع={state}؛ يتطلب={reason}.",
        )
        history.append(old)

        witness = witness_summary(targets[family])
        section, old = replace_one(
            section,
            OLDEST,
            f"- أقدمُ صورةٍ مستعادة: {witness}؛ الحكم للعضو المشهود "
            "نفسه ولا يرثه متجانس أو مركب.",
        )
        history.append(old)
        section, old = replace_one(
            section,
            LAYER,
            f"- طبقة المصدر: جرد الشواهد المثبت يسجل: {witness}. "
            "يبقى تصنيف كل إحالة كما هو ولا تتحول الإحالة الحديثة إلى قديمة.",
        )
        history.append(old)

        source_names = (
            LISAN_SIHAH
            if family == "hebrew:family:f40279852ba514a87eb5345a"
            else LISAN_TAJ
        )
        if kind == "positive":
            specification = POSITIVES[family]
            fan_rows = fans[str(specification["root"])]
            source_names = " + ".join(row["source"] for row in fan_rows)
            new_scan = (
                f"- مسحُ المعاني العربيّة: مروحة مستقلة مكتملة للجذر "
                f"`{specification['root']}` من {source_names}؛ المعنى "
                "المسمى حاضر في المصدرين."
            )
        else:
            new_scan = (
                "- مسحُ المعاني العربيّة: المروحة السابقة مستنفدة "
                f"للمرشحات المرخصة من {source_names}؛ لا يصدر حكم "
                "آلي من مجرد اكتمالها."
            )
        section, old = replace_one(section, SCAN, new_scan)
        history.append(old)
        section, old = replace_one(
            section,
            CLOSURE,
            f"- حالةُ الإغلاق: {state}.",
        )
        history.append(old)

        if kind == "positive":
            specification = POSITIVES[family]
            verdict = (
                f"- الحكم (استكشاف): {specification['verdict']}؛ "
                f"{specification['scope']}؛ المدار={specification['bridge']}؛ "
                "لا وراثة لسائر الأسرة."
            )
        else:
            verdict = f"- الحكم (استكشاف): غير صادر؛ {reason}."
        section, old = replace_one(section, VERDICT, verdict)
        history.append(old)

        appendix = [
            "",
            marker,
            f"- ملحق ترتيب الشاهد العبري، {DATE}:",
            f"  - المصير الجاري: `{state}`.",
            f"  - الشاهد المسجل: {witness}.",
        ]
        if kind == "positive":
            specification = POSITIVES[family]
            appendix.extend(
                [
                    f"  - العضو المحكوم: `{specification['entry']}`.",
                    f"  - الجذر العربي: `{specification['root']}`.",
                    f"  - مسار الصوت اللازم وحده: {specification['sound']}.",
                ]
            )
            for row in fans[str(specification["root"])]:
                appendix.append(
                    f"  - {row['source']}: «{row['excerpt']}»."
                )
        appendix.extend(
            [
                f"  - سبب المصير: {reason}.",
                "  - السجل التاريخي المحفوظ:",
                *[f"    - `{line}`" for line in history],
            ]
        )
        section = (
            section.rstrip() + "\n" + "\n".join(appendix) + "\n\n"
        )
        output.append(section)
        records.append({"family": family, "kind": kind, "state": state})

    if len(records) != 29 or len({row["family"] for row in records}) != 29:
        raise ValueError(f"expected 29 refined cards, got {len(records)}")
    counts = Counter(row["kind"] for row in records)
    expected = {
        "positive": 2,
        "referral": 3,
        "open": 10,
        "source-gap": 10,
        "law-gap": 1,
        "morphology-gap": 2,
        "terminal": 1,
    }
    if dict(counts) != expected:
        raise ValueError(f"unexpected decision counts: {dict(counts)}")

    updated = "".join(output)
    if unicodedata.normalize("NFC", updated) != updated:
        raise ValueError("Hebrew reading is not NFC")
    atomic_write(READING, updated)
    atomic_write(
        AUDIT,
        "\n".join(
            [
                "# ترتيب الشواهد العبرية، الدفعة 1 المحلية",
                "",
                "## بيان النطاق، الخطوة 14",
                "",
                "أعيدت قراءة البطاقات الـ29 التي ظهر لأسرها مرجع في جرد الطبقة الزمنية. المعيار عضو لا أسرة: لا ينتقل شاهد من علم إلى اسم، ولا من ظرف إلى مادة، ولا من رأس إلى مركب، ولا يصير المرجع الحديث شاهدًا قديمًا.",
                "",
                "## الحصيلة المفصولة",
                "",
                "- الصلات الموجبة الجديدة: 2، وهما פשר ↔ فسر وעופר ↔ عفر.",
                "- الإغلاقات النهائية الجديدة: 1، وهو عزل גיר ذي المانح السومري المسمى.",
                "- الإحالات إلى أحكام عضوية سابقة: 3؛ لا تعد صلات ولا إغلاقات جديدة.",
                "- مرشحات مفتوحة بلا حكم: 10.",
                "- فجوات مصدر دقيقة باقية: 10.",
                "- فجوة قانون صوتي: 1.",
                "- فجوتا صرف: 2.",
                "",
                "## عيب ترتيب الطابور الذي سبق الدفعة",
                "",
                "كان الإصدار الأول من الطابور يختار أقوى عضو في الأسرة ولو كان الشاهد التوراتي لعضو متجانس آخر. أصلح قبل كتابة أي بطاقة: العضو المصطف نفسه يجب أن يحمل الشاهد، فصار 856 عضوًا في الطابور المباشر، و66 أسرة في طابور حل الشاهد إلى العضو، و170 أسرة عزل.",
                "",
                "## الحالة",
                "",
                "- الأحكام محلية للمراجعة الثالثة.",
                "- لم يشغل خط البرهان ولم يجدد سجل الاسترداد المركزي.",
                "- الأرقام داخلية محاسبية لا تصلح للنشر.",
                "",
            ]
        ),
    )
    print(
        json.dumps(
            {
                "cards_refined": 29,
                "positive_connections": 2,
                "terminal_closures": 1,
                "referrals": 3,
                "open_candidates": 10,
                "source_gaps": 10,
                "law_gaps": 1,
                "morphology_gaps": 2,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
