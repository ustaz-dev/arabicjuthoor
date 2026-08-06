# -*- coding: utf-8 -*-
"""يسجل نقوض مراجعتي النواة والجذر المؤرختين 2026-08-01 و2026-08-02.

هذه أداة ترحيل تاريخية متعمدة. تقرأ مخرجي المراجعتين المحفوظين في مجلد
Claude المؤقت، تفك الأحكام المجمعة إلى بطاقات ملفات القراءة، ثم تنسخ الحكم
الموجب في طبقته وحدها. لا تحذف الأداة بطاقة ولا تغير حكم الطبقة الأخرى.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from count_links import bare as canonical_bare
from count_links import scan_card as canonical_scan_card


ROOT = Path(__file__).resolve().parent.parent
READINGS = ROOT / "04-cross-linguistic" / "readings"
NUCLEUS_RUN = Path(
    r"C:\Users\yassi\AppData\Local\Temp\claude\C--Users-yassi-AI-Projects-The-Arabic-Tongue--nature-genome-application-\8302db2b-a7e9-4c1a-9741-04aeb7a75613"
)
ROOT_RUN = Path(
    r"C:\Users\yassi\AppData\Local\Temp\claude\C--Users-yassi-AI-Projects-The-Arabic-Tongue--nature-genome-application-\dc141d91-99f7-4b59-9f0a-909a1fec60d2"
)
AUDIT_PATH = ROOT / "05-audits" / "2026-08-05-recorded-retractions.md"
DATA_PATH = ROOT / "data" / "recorded-retractions.json"

DEGREES = ("ROOT-TRACE", "ROOT-ECHO", "NUCLEUS-TRACE", "NUCLEUS-ECHO", "FLOOR-TRACE")
CANCELLED = ("غير صادر", "غير صادرة", "ناسخ", "منسوخ")
FIELD_LINE = re.compile(
    r"^-\s*(?:الحكم(?:\s*\([^)]*\))?|الحسم|حكم طبقة النواة|حكم طبقة الجذر|"
    r"نتيجة طبقة النواة|النتيجة)\s*[:：]\s*(.+)$"
)
FAMILY_RE = re.compile(r"[a-z_-]+:family:[0-9a-f]{8,}")
MEMBER_RE = re.compile(r"kaikki_[a-z0-9_]+:\d+:[^\s،؛,]+")
CCL_RE = re.compile(r"\bC\d{3,5}\b")
AED_RE = re.compile(r"\bAED\s*\d{4,6}\b")


@dataclass
class Target:
    language: str
    heading: str
    layer: str
    reasons: list[str] = field(default_factory=list)
    decisions: list[str] = field(default_factory=list)
    audit_id: str = ""
    card_ids: list[str] = field(default_factory=list)
    prior_degrees: list[str] = field(default_factory=list)
    was_counted: bool = False


def load_result(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    result = obj.get("result", obj)
    return json.loads(result) if isinstance(result, str) else result


def clean(text: str) -> str:
    return " ".join(str(text).replace("\u2014", "،").split())


def short_reason(text: str, limit: int = 360) -> str:
    text = clean(text)
    if len(text) <= limit:
        return text
    cut = max(text.rfind(mark, 0, limit) for mark in (".", "؛", "،"))
    if cut < 120:
        cut = limit
    return text[:cut].rstrip(" .،؛") + "."


def split_cards(text: str) -> list[str]:
    return re.split(r"(?m)(?=^### )", text)


def heading_of(block: str) -> str:
    return block.splitlines()[0] if block.startswith("### ") else ""


def active_degrees(block: str) -> set[str]:
    return canonical_scan_card(canonical_bare(block))


def layer_of(degree: str) -> str:
    if degree.startswith("ROOT"):
        return "root"
    if degree.startswith("NUCLEUS"):
        return "nucleus"
    return "floor"


def ids_of(block: str, heading: str) -> list[str]:
    ids: list[str] = []
    for pattern in (MEMBER_RE, FAMILY_RE, AED_RE, CCL_RE):
        for value in pattern.findall(block):
            value = value.rstrip("`.)]")
            if value not in ids:
                ids.append(value)
    if not ids:
        digest = hashlib.sha256(heading.encode("utf-8")).hexdigest()[:16]
        ids.append(f"reading-card:{digest}")
    return ids


def load_reading_blocks() -> tuple[dict[str, str], dict[str, list[str]]]:
    texts: dict[str, str] = {}
    blocks: dict[str, list[str]] = {}
    for path in sorted(READINGS.glob("*.md")):
        texts[path.stem] = path.read_text(encoding="utf-8")
        blocks[path.stem] = split_cards(texts[path.stem])
    return texts, blocks


def find_heading(blocks: dict[str, list[str]], language: str, needles: tuple[str, ...]) -> str:
    hits = []
    for block in blocks[language]:
        heading = heading_of(block)
        if heading and all(needle in heading for needle in needles):
            hits.append(heading)
    if len(hits) != 1:
        raise RuntimeError(f"تعذر تعيين بطاقة واحدة: {language} {needles!r}، المطابقات={len(hits)}")
    return hits[0]


def add_target(
    targets: dict[tuple[str, str, str], Target],
    blocks: dict[str, list[str]],
    language: str,
    layer: str,
    needles: tuple[str, ...],
    reason: str,
    decision: str,
) -> None:
    heading = find_heading(blocks, language, needles)
    key = (language, heading, layer)
    target = targets.setdefault(key, Target(language=language, heading=heading, layer=layer))
    reason = clean(reason)
    if reason not in target.reasons:
        target.reasons.append(reason)
    if decision not in target.decisions:
        target.decisions.append(decision)


def nucleus_targets(
    targets: dict[tuple[str, str, str], Target], blocks: dict[str, list[str]]
) -> Counter:
    result = load_result(NUCLEUS_RUN / "tasks" / "wqvwvkp39.output")
    languages = [
        "aramaic", "hebrew", "coptic", "egyptian", "old-irish", "old-english",
        "gothic", "ancient-greek", "old-latin", "old-norse", "welsh", "persian",
    ]
    counts: Counter = Counter()
    for language, review in zip(languages, result["reviews"]):
        sample_text = (NUCLEUS_RUN / "scratchpad" / "sample" / f"{language}.md").read_text(encoding="utf-8")
        sample_blocks = [
            block for block in split_cards(sample_text)
            if block.startswith("### ") and "<" not in heading_of(block)
        ]
        findings = review["findings"]
        if len(sample_blocks) != len(findings):
            raise RuntimeError(f"اختل ترتيب عينة النواة في {language}")
        for ordinal, (sample, finding) in enumerate(zip(sample_blocks, findings), 1):
            if finding["verdict"] != "REFUTED":
                continue
            heading = heading_of(sample)
            if sum(heading_of(block) == heading for block in blocks[language]) != 1:
                raise RuntimeError(f"عنوان عينة النواة غير فريد: {language}: {heading}")
            key = (language, heading, "nucleus")
            target = targets.setdefault(key, Target(language=language, heading=heading, layer="nucleus"))
            target.reasons.append(clean(finding["defect"]))
            target.decisions.append(f"NUC-{language}-{ordinal:02d}")
            counts[language] += 1
    if sum(counts.values()) != 69:
        raise RuntimeError(f"المتوقع 69 نقض نواة، ووجد {sum(counts.values())}")
    return counts


def root_targets(
    targets: dict[tuple[str, str, str], Target], blocks: dict[str, list[str]]
) -> tuple[list[dict], Counter]:
    result = load_result(ROOT_RUN / "tasks" / "wnobn86gv.output")
    reviews = result["refuted"]
    published = [13, 7, 21, 18, 14]
    if [review["refuted"] for review in reviews] != published:
        raise RuntimeError("تغيرت أرقام مخرج مراجعة الجذر")

    def reason(review: int, finding: int) -> str:
        return reviews[review - 1]["findings"][finding - 1]["defect"]

    specs: list[tuple[int, int, str, tuple[str, ...]]] = []

    # العدسة 1: البطاقات العشرون الموزعة في الآرامية، 13 منها مردودة.
    specs += [
        (1, 1, "aramaic", ("aramaic:family:070253db4f41371635d35e24", "الرتبة 581")),
        (1, 2, "aramaic", ("aramaic:family:f7e756241609d23ec7f643d7", "الرتبة 720")),
        (1, 3, "aramaic", ("aramaic:family:2b4b6c224a6768d7d40bfe18", "الرتبة 1131")),
        (1, 4, "aramaic", ("aramaic:family:647628b99d2ceadd05c66bfb", "الرتبة 1466")),
        (1, 5, "aramaic", ("petaḥā", "فتحة أو باب")),
        (1, 6, "aramaic", ("aramaic:family:4d2f878e7091de73fe5f1b74", "دفعة المقام الآرامية")),
        (1, 7, "aramaic", ("aramaic:family:bd2b433504bea4d873d37624", "دفعة المقام الآرامية")),
        (1, 8, "aramaic", ("aramaic:family:160df324aa9cf1125a56371b", "مراجعة عضوية")),
        (1, 9, "aramaic", ("kaikki_aramaic:1379:en-קטילתא-arc-adj-U5dQogc5", "مراجعة عضوية")),
        (1, 10, "aramaic", ("kaikki_aramaic:719:en-רטיבתא-arc-adj-HCU1C96R", "إعادة قراءة بطبقتين")),
        (1, 11, "aramaic", ("kaikki_aramaic:1062:en-טעם-arc-verb-2vkp6OfM", "إعادة قراءة بطبقتين")),
        (1, 12, "aramaic", ("kaikki_aramaic:1768:en-תגרתא-arc-noun-estAMW1w", "إعادة قراءة بطبقتين")),
        (1, 13, "aramaic", ("kaikki_aramaic:1808:en-חסינא-arc-adj-CIYDfj3f", "إعادة قراءة بطبقتين")),
    ]

    # العدسة 2: العينة العبرية.
    specs += [
        (2, 1, "hebrew", ("hebrew:family:4e6d0ff7f8e256db90b211b4", "מערה")),
        (2, 2, "hebrew", ("hebrew:family:3d1a812269dcc11383f991f3",)),
        (2, 3, "hebrew", ("hebrew:family:c543ecb7f131e9a7f64fbc6c", "التغطية التوراتية")),
        (2, 4, "hebrew", ("hebrew:family:282dd4dde40aa3827b318139", "الرتبة 13")),
        (2, 5, "hebrew", ("hebrew:family:c27d3342c239b7251fbdd4df",)),
        (2, 6, "hebrew", ("kaikki_hebrew:501:en-עץ-he-noun-3Jxe24st",)),
        (2, 7, "hebrew", ("hebrew:family:6c1b6627d2ae4c1c5d850835",)),
    ]

    # العدسة 3: فك الأحكام المجمعة إلى كتل القراءة الحية.
    egyptian_batch = [
        "egyptian:family:4d68ec8f384d1affcda8883d",
        "egyptian:family:cb142b8fc3d4d0fe5f534e01",
        "egyptian:family:138f129fa7fdbdf06a90bbb2",
        "egyptian:family:e6a61a43c9f76d081bde2d39",
        "egyptian:family:17e25d8f46e992b867625121",
        "egyptian:family:81f10caccd753df540b16970",
        "egyptian:family:5dd5579c7325050d2bdfb292",
        "egyptian:family:0ce06a2bd1ce74de485c4969",
        "egyptian:family:db878cdd7f23d8d5fd6d2f9b",
        "egyptian:family:e1b5e8d90f126e506579b392",
        "egyptian:family:1a62030c25bfc0fe96bce0d6",
        "egyptian:family:76a8078a6d23db0cb95d690d",
    ]
    for family in egyptian_batch:
        specs.append((3, 3, "egyptian", (family,)))
    specs += [
        (3, 1, "coptic", ("ϭⲓⲛⲱⲗ", "5457/11284")),
        (3, 1, "coptic", ("ϭⲓⲛⲱⲗ", "5458/11284")),
        (3, 5, "coptic", ("ⲙⲟⲩⲗϩ", "1876/11284")),
        (3, 5, "coptic", ("ⲙⲗϩ", "1877/11284")),
        (3, 5, "coptic", ("ⲙⲉⲗϩⲉ", "1878/11284")),
        (3, 6, "coptic", ("ϩⲁⲓⲃⲉⲥ", "1492/11284")),
        (3, 6, "coptic", ("ϩⲱⲃⲥ", "1494/11284")),
        (3, 6, "coptic", ("ϩⲱⲃⲥ", "1495/11284")),
        (3, 6, "coptic", ("ϩⲃⲟⲟⲥ", "1496/11284")),
        (3, 6, "coptic", ("ϩⲃⲟⲟⲥ", "1497/11284")),
        (3, 6, "coptic", ("ϩⲃⲥⲱ", "1498/11284")),
        (3, 7, "coptic", ("ⲕⲁϩ", "WEEK-DAY2")),
        (3, 8, "coptic", ("ⲥⲏϥⲉ", "3936")),
        (3, 9, "coptic", ("ⲥⲓⲙⲥⲓⲙ", "3553/11284")),
        (3, 10, "egyptian", ("mrkbt", "4170/33417")),
        (3, 10, "egyptian", ("mnn", "4023/33417")),
        (3, 11, "coptic", ("mou", "die")),
        (3, 11, "coptic", ("sōšf", "be despised")),
        (3, 12, "coptic", ("ⲥⲱⲗⲡ", "استدراك العيادة")),
        (3, 13, "akkadian", ("târu", "يرجع ويلتف")),
        (3, 14, "akkadian", ("naṣāru", "يحرس ويحمي")),
    ]

    # العدسة 4: الموجة الهندية الأوروبية، مع تفكيك البطاقتين المزدوجتين.
    specs += [
        (4, 1, "welsh", ("welsh:family:958c7cc9ea07e62761fcd20a",)),
        (4, 2, "gothic", ("gothic:family:67a534a1d94abb537cecaac8",)),
        (4, 3, "gothic", ("gothic:family:a3636f680ad0e8bc42badfb6",)),
        (4, 4, "gothic", ("gothic:family:bd46772d5dd1ce844e253136",)),
        (4, 5, "welsh", ("welsh:family:fdbefbde03690f9536fd215e", "الموجة ج")),
        (4, 6, "persian", ("persian:family:bd3496ebe1ee5352dc235b67", "الموجة ج")),
        (4, 7, "persian", ("persian:family:37e728b13bcd473142ad5349", "الموجة ج")),
        (4, 8, "welsh", ("welsh:family:2c7cec098628ff86da72cb67",)),
        (4, 9, "old-norse", ("old_norse:family:74898bde40585d09878b7dd5",)),
        (4, 10, "ancient-greek", ("ancient_greek:family:2ffe8ce3fe267e83f506948b",)),
        (4, 11, "old-latin", ("clāmō", "to cry out")),
        (4, 11, "old-latin", ("calō", "to call")),
        (4, 12, "old-english", ("god «good»",)),
        (4, 12, "old-english", ("god", "good (something")),
        (4, 13, "persian", ("persian:family:27b711b905e4c5916ca3e7a7", "الموجة ج")),
    ]

    extra_wave_reason = clean(
        "المخرج النهائي للمراجعة عد هذه البطاقة من الموجة ج المردودة: الهيكل الصامتي "
        "تجاوز صرف الفرع أو استعمل صفا خارج شرطه، ثم انتخب المتجانس العربي بالمعنى "
        "وصاغ مدارا واصلا بدل نقل معنى معجمي."
    )
    extra_specs = [
        ("welsh", ("welsh:family:6ddb0bf9739074f160660614",), "ROOT4-halogi"),
        ("old-norse", ("old_norse:family:a2a35472fea4d823173b3017",), "ROOT4-herda"),
        ("old-norse", ("old_norse:family:53d57d97abd5b0cf80c3fc2f",), "ROOT4-kanna"),
    ]

    # العدسة 5: المتجانسات. ثمانية أحكام تكرر بطاقات سبقت في العدسات 2 إلى 4.
    lens5 = [
        (5, 1, "old-latin", ("latin:family:4272e2c3a55cbd1216e0cd86",)),
        (5, 2, "gothic", ("gothic:family:67a534a1d94abb537cecaac8",)),
        (5, 3, "ancient-greek", ("ancient_greek:family:716c48464b7e0efc91040e97",)),
        (5, 4, "welsh", ("welsh:family:958c7cc9ea07e62761fcd20a",)),
        (5, 5, "persian", ("persian:family:37e728b13bcd473142ad5349", "الموجة ج")),
        (5, 6, "old-norse", ("old_norse:family:dfffe772361cc42e353a0e87",)),
        (5, 7, "egyptian", ("mrkbt", "4170/33417")),
        (5, 8, "egyptian", ("brkt", "3071/33417")),
        (5, 9, "egyptian", ("mnn", "4023/33417")),
        (5, 10, "coptic", ("ⲥⲓⲙⲥⲓⲙ", "3553/11284")),
        (5, 11, "coptic", ("ⲙⲟⲩⲗϩ", "1876/11284")),
        (5, 12, "aramaic", ("aramaic:family:5f3f53683c0fb8f5cbdedf6e", "الرتبة 1089")),
        (5, 13, "egyptian", ("ḥsb", "to count; to reckon")),
        (5, 14, "hebrew", ("hebrew:family:4e6d0ff7f8e256db90b211b4", "מערה")),
    ]

    root_rows: list[dict] = []
    root_counts: Counter = Counter()
    for review_no, finding_no, language, needles in specs:
        decision = f"ROOT{review_no}-{finding_no:02d}-{len(root_rows) + 1:03d}"
        add_target(targets, blocks, language, "root", needles, reason(review_no, finding_no), decision)
        root_rows.append({"review": review_no, "finding": finding_no, "language": language, "needles": needles})
        root_counts[language] += 1
    for language, needles, decision in extra_specs:
        add_target(targets, blocks, language, "root", needles, extra_wave_reason, decision)
        root_rows.append({"review": 4, "finding": "overall", "language": language, "needles": needles})
        root_counts[language] += 1
    for review_no, finding_no, language, needles in lens5:
        decision = f"ROOT5-{finding_no:02d}"
        add_target(targets, blocks, language, "root", needles, reason(review_no, finding_no), decision)
        root_rows.append({"review": review_no, "finding": finding_no, "language": language, "needles": needles})
        root_counts[language] += 1
    return root_rows, root_counts


def enrich_and_number(targets: list[Target], blocks: dict[str, list[str]]) -> None:
    counters = Counter()
    for target in targets:
        block = next(block for block in blocks[target.language] if heading_of(block) == target.heading)
        target.card_ids = ids_of(block, target.heading)
        target.prior_degrees = sorted(
            degree for degree in DEGREES if layer_of(degree) == target.layer and degree in block
        )
        if not target.prior_degrees:
            raise RuntimeError(f"لا حكم سابق من طبقة {target.layer}: {target.language}: {target.heading}")
        target.was_counted = any(
            layer_of(degree) == target.layer for degree in active_degrees(block)
        )
        counters[target.layer] += 1
        prefix = "N" if target.layer == "nucleus" else "R"
        target.audit_id = f"RET-{prefix}-{counters[target.layer]:03d}"


def restore_pre_migration_block(block: str) -> str:
    """يعيد كتلة سبق أن نفذتها هذه الأداة إلى صورتها قبل الترحيل في الذاكرة."""
    lines = []
    for line in block.splitlines():
        if line.startswith("- سطر النسخ (2026-08-05، RET-"):
            continue
        if "حكم باق كما كان، ولا يمسه قرار طبقة" in line:
            continue
        line = re.sub(r"غير صادر \[كان (ROOT-TRACE|ROOT-ECHO|NUCLEUS-TRACE|NUCLEUS-ECHO)\]", r"\1", line)
        lines.append(line)
    return "\n".join(lines) + ("\n" if block.endswith("\n") else "")


def supersede_block(block: str, target: Target) -> str:
    if f"سطر النسخ (2026-08-05، {target.audit_id})" in block:
        return block
    before = active_degrees(block)
    lines = block.splitlines()
    changed = False
    for index, line in enumerate(lines):
        # العدّاد يزيل التشكيل قبل تعرف اسم حقل الحكم، فلا بد أن يفعل الناسخ
        # الشيء نفسه وإلا بقيت حقول مثل الحكمُ أو النتيجةُ موجبة.
        match = FIELD_LINE.match(canonical_bare(line))
        if not match:
            continue
        value = match.group(1)
        hit = [degree for degree in target.prior_degrees if degree in value]
        if not hit:
            continue
        for degree in hit:
            line = line.replace(degree, f"غير صادر [كان {degree}]")
        lines[index] = line
        changed = True
    if not changed:
        raise RuntimeError(f"لم أجد سطر الحكم المراد نسخه: {target.audit_id}")
    provisional = "\n".join(lines)
    after = active_degrees(provisional)
    preserved = {degree for degree in before if layer_of(degree) != target.layer}
    for degree in sorted(preserved - after):
        lines.append(
            f"- الحكم (استكشاف): {degree}؛ حكم باق كما كان، ولا يمسه قرار طبقة {target.layer}."
        )
    old = "، ".join(target.prior_degrees)
    summary = short_reason("؛ ".join(target.reasons))
    lines.append(
        f"- سطر النسخ (2026-08-05، {target.audit_id}): الحكم السابق {old} منسوخ؛ السبب: {summary}"
    )
    return "\n".join(lines) + ("\n" if block.endswith("\n") else "")


def write_audit(targets: list[Target], nucleus_counts: Counter, root_rows: list[dict]) -> None:
    by_layer = Counter(target.layer for target in targets)
    active_by_layer = Counter(target.layer for target in targets if target.was_counted)
    duplicate_decisions = sum(max(0, len(target.decisions) - 1) for target in targets if target.layer == "root")
    expanded_root = by_layer["root"]
    lines = [
        "# محضر تسجيل النقوض، 2026-08-05",
        "",
        "## النطاق والنتيجة",
        "",
        "استعيد المخرجان الخامان للمراجعتين، وربط كل حكم بكتلة القراءة الحية. لم تحذف بطاقة واحدة. "
        "نسخ الحكم الموجب في طبقته وحدها، وحفظ حكم الطبقة الأخرى إن وجد.",
        "",
        f"- المراجعة الأولى: 82 بطاقة نواة، منها 69 مردودة. حلت البطاقات المردودة 69 كلها إلى 69 كتلة قراءة فريدة.",
        "- المراجعة الثانية: الرقم المنشور 73 حكم نقض بعد فحص 146 بطاقة جذر.",
        f"- بعد فك التجميع والازدواج: {expanded_root} كتلة جذر فريدة. تكررت {duplicate_decisions} قرارات على بطاقات سبقت في عدسة أخرى، "
        f"وكانت عدسة مصر والقبط تجمع بطاقات عدة في قرار واحد، فصار صافي الكتل المنسوخة {expanded_root} لا 73.",
        f"- مجموع أحكام الطبقات الفريدة المسجلة: {len(targets)}، منها {by_layer['nucleus']} نواة و{by_layer['root']} جذر.",
        f"- كان داخلا فعلا في عداد البطاقات قبل هذا النسخ: {sum(active_by_layer.values())}، منها {active_by_layer['nucleus']} نواة و{active_by_layer['root']} جذر. "
        "الفرق بطاقات حمل سطرها القديم لفظ إلغاء آخر فكان العداد يسقط السطر عرضا، مع بقاء النقض غير مدون.",
        "",
        "## مطابقة الأرقام المنشورة",
        "",
        "| المخرج | المفحوص | النقض المنشور | طريقة التسجيل |",
        "|---|---:|---:|---|",
        "| مراجعة النواة | 82 | 69 | 69 بطاقة فريدة |",
        "| مراجعة الجذر، العدسة 1 | 20 | 13 | 13 قرارا مفردا |",
        "| مراجعة الجذر، العدسة 2 | 25 | 7 | 7 قرارات مفردة |",
        "| مراجعة الجذر، العدسة 3 | 34 | 21 | فك الأحكام المجمعة إلى كتل القراءة المسماة |",
        "| مراجعة الجذر، العدسة 4 | 33 | 18 | فك البطاقتين المزدوجتين، واستعادة 3 أسماء من الخلاصة |",
        "| مراجعة الجذر، العدسة 5 | 34 | 14 | دمج التكرار عند البطاقة نفسها |",
        "| المجموع المنشور | 228 | 142 | قيد القرارات كلها، وتنفيذ النسخ على الكتل الفريدة |",
        "",
        "تفسير الفرق واجب للمحاسبة: 142 هو عدد أحكام المراجعين كما ورد في الملخصين. ليس عدد كتل القراءة الفريدة. "
        "المخرج الجذري جمع 12 بطاقة مصرية في نتيجة واحدة، و6 بطاقات قبطية في نتيجة واحدة، وجمع أعضاء أخرى، ثم أعاد في عدسة المتجانسات "
        "نقض بطاقات سبق نقضها. لذلك لا يجوز إنقاص العداد 142 إنقاصا أعمى، بل ينسخ كل حكم حي مرة واحدة.",
        "",
        "## توزيع نقوض النواة",
        "",
        "| اللسان | البطاقات المردودة |",
        "|---|---:|",
    ]
    for language, count in nucleus_counts.items():
        lines.append(f"| {language} | {count} |")
    lines += [
        f"| المجموع | {sum(nucleus_counts.values())} |",
        "",
        "## سجل البطاقات المنسوخة",
        "",
        "| رقم النسخ | الطبقة | اللسان | معرف البطاقة | الحكم السابق | سبب النقض | موضع البطاقة |",
        "|---|---|---|---|---|---|---|",
    ]
    for target in targets:
        ids = "؛ ".join(target.card_ids)
        prior = "، ".join(target.prior_degrees)
        reason_text = short_reason("؛ ".join(target.reasons), 520).replace("|", "\\|")
        heading = clean(target.heading).replace("|", "\\|")
        lines.append(
            f"| {target.audit_id} | {target.layer} | {target.language} | {ids} | {prior} | {reason_text} | "
            f"04-cross-linguistic/readings/{target.language}.md، {heading} |"
        )
    lines += [
        "",
        "## قاعدة التنفيذ",
        "",
        "كل بطاقة بقيت في مكانها. عطل سطر الحكم السابق بعبارة غير صادر مع حفظ الدرجة السابقة بين معقوفين، "
        "ثم أضيف سطر نسخ صريح يحمل رقم هذا المحضر وسبب النقض. إذا كان السطر القديم يجمع طبقتين، أعيد إثبات الطبقة غير المنقوضة "
        "في سطر حكم مستقل حتى لا يسقطها العداد تبعا.",
        "",
        "يحفظ الملف data/recorded-retractions.json الأسباب الكاملة ومراجع قرارات المراجعين بصيغة آلية.",
        "",
    ]
    AUDIT_PATH.write_text("\n".join(lines), encoding="utf-8")


def write_data(targets: list[Target]) -> None:
    payload = {
        "schema_version": "1.0",
        "date": "2026-08-05",
        "published_review_decisions": {"nucleus": 69, "root": 73, "total": 142},
        "unique_live_layer_targets": {
            "nucleus": sum(target.layer == "nucleus" for target in targets),
            "root": sum(target.layer == "root" for target in targets),
            "total": len(targets),
        },
        "records": [
            {
                "audit_id": target.audit_id,
                "layer": target.layer,
                "language": target.language,
                "source_file": f"04-cross-linguistic/readings/{target.language}.md",
                "heading": target.heading,
                "card_ids": target.card_ids,
                "prior_degrees": target.prior_degrees,
                "was_counted_before_recording": target.was_counted,
                "review_decisions": target.decisions,
                "reasons": target.reasons,
            }
            for target in targets
        ],
    }
    DATA_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="نفذ النسخ واكتب المحضر")
    parser.add_argument(
        "--language",
        action="append",
        choices=sorted(path.stem for path in READINGS.glob("*.md")),
        help="اكتب لسانا بعينه في دفعة مستقلة، ويجوز تكرار الخيار",
    )
    args = parser.parse_args()
    texts, blocks = load_reading_blocks()
    target_map: dict[tuple[str, str, str], Target] = {}
    nucleus_counts = nucleus_targets(target_map, blocks)
    root_rows, root_counts = root_targets(target_map, blocks)
    targets = sorted(
        target_map.values(),
        key=lambda target: (0 if target.layer == "nucleus" else 1, target.language, target.heading),
    )
    # يسمح بإعادة التشغيل بعد فحص أول: نستعيد الكتل التي لمستها هذه الأداة في
    # الذاكرة، ثم نعيد النسخ من الصورة السابقة نفسها ولا نضاعف سطور النسخ.
    target_keys = {(target.language, target.heading) for target in targets}
    for language, parts in blocks.items():
        for index, block in enumerate(parts):
            if (language, heading_of(block)) in target_keys:
                parts[index] = restore_pre_migration_block(block)
    enrich_and_number(targets, blocks)
    print(f"قرارات المراجعتين المنشورة: 142")
    print(f"أهداف النسخ الفريدة: {len(targets)}")
    print(f"  النواة: {sum(t.layer == 'nucleus' for t in targets)}")
    print(f"  الجذر: {sum(t.layer == 'root' for t in targets)}")
    print(f"الأهداف التي يعدها count_links الآن: {sum(t.was_counted for t in targets)}")
    print(f"صفوف فك مراجعة الجذر قبل دمج التكرار: {len(root_rows)}")
    print("توزيع أهداف الجذر قبل دمج التكرار:", dict(sorted(root_counts.items())))
    if not args.apply:
        print("فحص جاف فقط. أضف --apply للتنفيذ.")
        return 0

    by_language = {language: list(parts) for language, parts in blocks.items()}
    for target in targets:
        parts = by_language[target.language]
        indexes = [index for index, block in enumerate(parts) if heading_of(block) == target.heading]
        if len(indexes) != 1:
            raise RuntimeError(f"اختل تعيين البطاقة عند الكتابة: {target.audit_id}")
        index = indexes[0]
        parts[index] = supersede_block(parts[index], target)
    selected_languages = set(args.language or by_language)
    for language, parts in by_language.items():
        if language not in selected_languages:
            continue
        new_text = "".join(parts)
        if new_text != texts[language]:
            (READINGS / f"{language}.md").write_text(new_text, encoding="utf-8")
    if args.language:
        print("كتب ألسنة الدفعة: " + "، ".join(sorted(selected_languages)))
    else:
        write_audit(targets, nucleus_counts, root_rows)
        write_data(targets)
        print(f"كتب المحضر: {AUDIT_PATH.relative_to(ROOT)}")
        print(f"كتب السجل الآلي: {DATA_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
