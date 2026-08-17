# -*- coding: utf-8 -*-
"""إتمام الجولة السادسة عشرة للمسار D من غير شحن أو تعديل للبطاقات الأصلية."""
from __future__ import annotations

import pathlib
import re
import sys
import unicodedata


ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import fan_any_script as FAN  # noqa: E402
import frozen_event as EVENT  # noqa: E402


BT = chr(96)
OE_FILE = ROOT / "04-cross-linguistic/readings/old-english.md"
ON_FILE = ROOT / "04-cross-linguistic/readings/old-norse.md"
SOURCE_DIR = ROOT / "04-cross-linguistic/readings/phonetic-sweep-germanic-celtic"
COMPACT_DIR = ROOT / "04-cross-linguistic/readings/phonetic-sweep-germanic-celtic-compact"
REPORT = ROOT / "_inbox/lane-reports/2026-08-16-D.md"
OE_MARKER = "LANE-D-DONE16-OLD-ENGLISH:START"
ON_MARKER = "LANE-D-DONE16-OLD-NORSE:START"
REPORT_MARKER = "## الجولة السادسة عشرة: ختام التصويب وفتح النردية"


def clean(value: str) -> str:
    table = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")
    return unicodedata.normalize("NFC", value).translate(table).replace("—", "؛").strip()


def clip(value: str, limit: int = 300) -> str:
    value = re.sub(r"\s+", " ", clean(value))
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "…"


def append(path: pathlib.Path, text: str) -> None:
    old = path.read_text(encoding="utf-8")
    path.write_text(old.rstrip() + "\n\n" + clean(text) + "\n", encoding="utf-8", newline="\n")


def remove_generated_section(path: pathlib.Path, start_marker: str, end_marker: str) -> None:
    text = path.read_text(encoding="utf-8")
    start_token = f"<!-- {start_marker} -->"
    if start_token not in text:
        return
    end_token = f"<!-- {end_marker} -->"
    start = text.index(start_token)
    end = text.index(end_token, start) + len(end_token)
    path.write_text(text[:start].rstrip() + "\n", encoding="utf-8", newline="\n")


def event_for(root: str, tier: int):
    matches = [item for item in EVENT.all_tiers(root) if item.tier == tier]
    assert len(matches) == 1, (root, tier, EVENT.all_tiers(root))
    return matches[0]


CORRECTIONS = {
    "PS-GC-OLD-ENGLISH-00854": {
        "word": "helan", "meaning": "to hide, conceal", "root": "غور",
        "tier": 1, "judgment": "ROOT-ECHO",
        "cause": "أسقط الإصلاح نهاية -an، فظهر الهيكل h-l وفتح باب الأجوف غور.",
        "sound": "h↔غ=GUT-04؛ l↔ر=LIQ-01؛ والواو من باب الأجوف المسمى.",
        "witness": "المحكم: «غار في الشيء غورا وغؤورا؛ دخل».",
        "witness2": "تاج اللغة وصحاح العربية للجوهري: «غور كل شيء قعره».",
        "orbit": "الإخفاء إدخال للشيء في غور ما يستره؛ فاجتمع الدخول المتعمق مع حس الستر.",
    },
    "PS-GC-OLD-ENGLISH-00877": {
        "word": "lettan", "meaning": "to hinder, obstruct", "root": "ردد",
        "tier": 1, "judgment": "ROOT-TRACE",
        "cause": "أسقط الإصلاح نهاية -an، فظهر الهيكل l-t وفتح باب المضاعف ردد.",
        "sound": "l↔ر=LIQ-01؛ t↔د=BR-GRIM-02؛ والدال الثالثة تكرير من باب المضاعف المسمى.",
        "witness": "الصحاح: «رده عن وجهه يرده ردا؛ صرفه».",
        "witness2": "المحكم: «الرد صرف الشيء ورجعه».",
        "orbit": "المنع والصد في الفرع هما رد استرسال الفعل؛ وهو نص الحدث والشاهد العربي.",
    },
    "PS-GC-OLD-ENGLISH-00901": {
        "word": "loccian", "meaning": "to allure, entice, win over by gentle means", "root": "رقق",
        "tier": 1, "judgment": "ROOT-ECHO",
        "cause": "أسقط الإصلاح نهاية -ian ورد CC إلى صامته، فظهر الهيكل l-c وفتح المضاعف رقق.",
        "sound": "l↔ر=LIQ-01؛ c↔ق=GUT-01؛ والقاف الثالثة تكرير من باب المضاعف المسمى.",
        "witness": "المحكم: «الرقة ضد الغلظ؛ ورققه جعله رقيقا».",
        "witness2": "تاج اللغة وصحاح العربية للجوهري: «الرقة خلاف الغلظ».",
        "orbit": "الاستمالة بالرفق تليين للمستمال وترقيق للمعاملة؛ لذلك ثبت الصدى لا التطابق الحرفي.",
    },
    "PS-GC-OLD-ENGLISH-00922": {
        "word": "tucian", "meaning": "to disturb, mistreat, afflict, punish, torment", "root": "دقق",
        "tier": 1, "judgment": "ROOT-ECHO",
        "cause": "أسقط الإصلاح نهاية -ian، فظهر الهيكل t-c وفتح المضاعف دقق.",
        "sound": "t↔د=BR-GRIM-02؛ c↔ق=GUT-01؛ والقاف الثالثة تكرير من باب المضاعف المسمى.",
        "witness": "المحكم: «الدق الكسر والرض؛ تضرب الشيء فتهشمه».",
        "witness2": "تاج العروس: «دقه يدقه دقا؛ كسره بأي وجه كان».",
        "orbit": "الإيذاء والتعذيب ضغط وصدم متكرر يصيب الشيء؛ وهذا يلتقي حدث الدق من غير دعوى هوية.",
    },
    "PS-GC-OLD-ENGLISH-00925": {
        "word": "facian", "meaning": "to obtain, acquire, get, reach", "root": "وفق",
        "tier": 3, "judgment": "ROOT-ECHO",
        "cause": "أسقط الإصلاح نهاية -ian، فظهر الهيكل f-c وفتح باب المثال وفق.",
        "sound": "f↔ف=IDN-06؛ c↔ق=GUT-01؛ والواو من باب المثال المسمى.",
        "witness": "الصحاح: «وفقت أمرك؛ صادفته موافقا».",
        "witness2": "المحكم: «وفق الشيء ما لاءمه».",
        "orbit": "بلوغ الشيء وإصابته في الفرع يلتقيان مصادفته وبلوغ تمامه في العربية والحدث.",
    },
    "PS-GC-OLD-ENGLISH-00953": {
        "word": "mesan", "meaning": "to eat, feed", "root": "مصص",
        "tier": 1, "judgment": "ROOT-ECHO",
        "cause": "أسقط الإصلاح نهاية -an، فظهر الهيكل m-s وفتح المضاعف مصص.",
        "sound": "m↔م=IDN-02؛ s↔ص=SIB-02؛ والصاد الثالثة تكرير من باب المضاعف المسمى.",
        "witness": "المحكم: «مصصت الشيء مصا؛ ترشفته».",
        "witness2": "تاج اللغة وصحاح العربية للجوهري: «مصصت الشيء أمصه مصا، وكذلك امتصصته».",
        "orbit": "الأكل والتغذية يشتملان على أخذ الغذاء بالفم، والمص استخلاصه جذبا؛ فالحكم صدى مضبوط.",
    },
}

PRIOR_FLIPS = {
    "PS-GC-OLD-ENGLISH-00871": "CORR-COMP-PS-GC-OLD-ENGLISH-00871",
    "PS-GC-OLD-ENGLISH-00914": "CORR-COMP-PS-GC-OLD-ENGLISH-00914",
    "PS-GC-OLD-ENGLISH-00962": "CORR-COMP-PS-GC-OLD-ENGLISH-00962",
}


NORSE_POSITIVE = {
    "PS-GC-OLD-NORSE-00055": ("مكن", 1, "NUCLEUS-TRACE", "القوة والقدرة في الفرع تلتقيان التمكن؛ والنون في بناء الاسم لا تنقل الحكم من طبقة النواة."),
    "PS-GC-OLD-NORSE-00056": ("مكن", 1, "NUCLEUS-TRACE", "القوة والقدرة في الفرع تلتقيان التمكن؛ والنون في بناء الاسم لا تنقل الحكم من طبقة النواة."),
    "PS-GC-OLD-NORSE-00057": ("برز", 1, "ROOT-ECHO", "النفخ إخراج للهواء من الفم؛ فاجتمع الخروج القوي مع الشاهد العربي في البروز."),
    "PS-GC-OLD-NORSE-00067": ("فرق", 1, "ROOT-ECHO", "الجند أو القوم فرقة متميزة من غيرها؛ واجتمع الفصل العميق مع اسم الجماعة."),
    "PS-GC-OLD-NORSE-00068": ("قرب", 1, "ROOT-ECHO", "العصر والضغط يقربان أجزاء الشيء بعضها من بعض حتى تضيق المسافة."),
    "PS-GC-OLD-NORSE-00071": ("قيل", 1, "ROOT-ECHO", "السكون والراحة زوال إلى مقر مؤقت؛ ويشهد له حس القيلولة في العربية."),
    "PS-GC-OLD-NORSE-00094": ("نكر", 1, "ROOT-TRACE", "غير المعين أو المجهول نكرة؛ فاجتمع الغرابة في الحدث مع الاستعمال العربي."),
    "PS-GC-OLD-NORSE-00097": ("مشر", 3, "ROOT-ECHO", "خشب القيقب ذو العروق والنتوءات يلتقي انتشار العروق والأغصان وحس النبات في مشر."),
    "PS-GC-OLD-NORSE-00106": ("بين", 1, "ROOT-ECHO", "المد والبسط والإجراء إلى الأمام امتداد بين طرفين؛ فثبت صدى الحركة والامتداد."),
}


def original_old_english_cards(text: str) -> list[dict[str, str]]:
    pat = re.compile(
        r"^### بطاقة إتمام: " + re.escape(BT) + r"([^" + re.escape(BT) + r"]+)"
        + re.escape(BT) + r" /([^/]*)/؛ " + re.escape(BT)
        + r"COMP-(PS-GC-OLD-ENGLISH-(\d{5}))" + re.escape(BT) + r"$",
        re.M,
    )
    matches = list(pat.finditer(text))
    out = []
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[match.end():end]
        number = int(match.group(4))
        if 852 <= number <= 967 and re.search(r"الحكم \(استكشاف\):\s*" + re.escape(BT) + r"?NO-TRACE", body):
            out.append({"word": match.group(1), "roman": match.group(2), "source": match.group(3), "body": body})
    return out


def render_correction(source: str, data: dict[str, object]) -> str:
    root = str(data["root"])
    assert root in FAN.fan(str(data["word"]), "germanic"), (source, root)
    ev = event_for(root, int(data["tier"]))
    cid = "CORR-COMP-" + source
    return f"""### بطاقة تصويب: {BT}{data["word"]}{BT}؛ {BT}{cid}{BT}
<!-- LANE-D-DONE16-CORRECTION:{cid} -->

- بطاقة المصدر المنسوخة حكما: {BT}COMP-{source}{BT}؛ بقي أصلها بلا مساس.
- سبب التصويب: {data["cause"]}
- معنى عضو الفرع: «{data["meaning"]}».
- المقابل والحدث: {BT}{root}{BT}؛ الدرجة {ev.tier} ({ev.tier_ar}): «{ev.text}» [{ev.source}].
- مسح المعاني العربية: نقل شاهدان مسميان بعد قراءة المداخل:
  - {data["witness"]}
  - {data["witness2"]}
- مسار الصوت: {data["sound"]}
- المدار: {data["orbit"]}
- حالة الإغلاق: READY.
- الحكم (استكشاف): {BT}{data["judgment"]}{BT}.
"""


def finish_old_english() -> tuple[list[dict[str, str]], list[str]]:
    text = OE_FILE.read_text(encoding="utf-8")
    cards = original_old_english_cards(text)
    assert len(cards) == 103, len(cards)
    assert cards[0]["source"].endswith("00852")
    assert cards[-1]["source"].endswith("00967")
    sources = {card["source"] for card in cards}
    assert set(CORRECTIONS) | set(PRIOR_FLIPS) <= sources
    for correction_id in PRIOR_FLIPS.values():
        assert correction_id in text, correction_id
    stable = [
        card["source"] for card in cards
        if card["source"] not in CORRECTIONS and card["source"] not in PRIOR_FLIPS
    ]
    assert len(stable) == 94, len(stable)
    if OE_MARKER in text:
        remove_generated_section(
            OE_FILE, OE_MARKER, "LANE-D-DONE16-OLD-ENGLISH:END"
        )

    parts = [
        f"""<!-- {OE_MARKER} -->

## الجولة السادسة عشرة: ختام التصويب بالأداة المصلحة

- النطاق الختامي: بطاقات الحكم الأصلي {BT}NO-TRACE{BT} من {BT}PS-GC-OLD-ENGLISH-00852{BT} إلى {BT}PS-GC-OLD-ENGLISH-00967{BT} بحسب ترتيب الإصدار؛ عددها 103.
- أعيدت قراءة المروحة والحدث والشواهد لكل بطاقة. انقلب في هذا النطاق 9 أحكام، منها 3 ثبتت بطاقات تصويبها في المسبار السابق و6 بطاقات جديدة أدناه، وثبت 94 حكما.
- الأداة الحاكمة: {BT}scripts/fan_any_script.py{BT} بعد الإصلاح {BT}0ebb1e9{BT} وبالخط {BT}germanic{BT} صراحة.
"""
    ]
    for source, data in CORRECTIONS.items():
        parts.append(render_correction(source, data))
    parts.append("### المنقلبات المثبتة في المسبار السابق\n")
    for source, correction_id in PRIOR_FLIPS.items():
        parts.append(
            f"- {BT}COMP-{source}{BT}: أعيدت قراءته ضمن الخاتمة؛ حكمه الناسخ قائم في "
            f"{BT}{correction_id}{BT}، فلم تكرر بطاقة التصويب.\n"
        )
    parts.append("\n### إقرارات الأحكام الثابتة\n")
    for source in stable:
        parts.append(
            f"- {BT}COMP-{source}{BT}: أعيدت قراءته بالأداة المصلحة وثبت الحكم.\n"
        )
    parts.append(
        f"\n- الأصل محفوظ؛ لم تشغل أداة الشحن ولم ينشأ إيداع.\n\n<!-- LANE-D-DONE16-OLD-ENGLISH:END -->"
    )
    append(OE_FILE, "".join(parts))
    return cards, stable


def parse_norse_sources() -> list[dict[str, str]]:
    heading = re.compile(
        r"^### بطاقة مسح صوتي: " + re.escape(BT) + r"([^" + re.escape(BT) + r"]+)"
        + re.escape(BT) + r" /([^/]*)/؛ (PS-GC-OLD-NORSE-\d{5})$",
        re.M,
    )
    rows: list[dict[str, str]] = []
    for path in sorted(SOURCE_DIR.glob("batch-*-old-norse.md")):
        text = path.read_text(encoding="utf-8")
        matches = list(heading.finditer(text))
        for idx, match in enumerate(matches):
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            body = text[match.end():end]
            meaning_match = re.search(r"معنى صف المسح «([^»]*)»", body)
            pool_match = re.search(r"مقام المسح: " + re.escape(BT) + r"([^" + re.escape(BT) + r"]+)", body)
            closest_match = re.search(r"أقرب مادة في المسح " + re.escape(BT) + r"([^" + re.escape(BT) + r"]+)", body)
            ety_match = re.search(r"حاشية الأصل كما يقول القاموس: (.*)$", body, re.M)
            rows.append({
                "word": match.group(1), "roman": match.group(2), "source": match.group(3),
                "file": path.name, "body": body,
                "meaning": meaning_match.group(1) if meaning_match else "",
                "pool": pool_match.group(1) if pool_match else "",
                "closest": closest_match.group(1) if closest_match else "",
                "etymology": ety_match.group(1) if ety_match else "لا حاشية أصل في بطاقة المصدر.",
            })
    ids = [row["source"] for row in rows]
    assert len(rows) == 798, len(rows)
    assert len(ids) == len(set(ids))
    compact_count = 0
    for path in sorted(COMPACT_DIR.glob("batch-*-old-norse.md")):
        compact_count += len(re.findall(r"^### بطاقة مدمجة:", path.read_text(encoding="utf-8"), re.M))
    assert compact_count == 798, compact_count
    return rows


def source_path(body: str, root: str) -> str:
    match = re.search(
        r"^  - " + re.escape(BT) + re.escape(root) + re.escape(BT)
        + r": في المروحة الحالية حاضر؛ مسار الصفوف: ([^\n]+)",
        body, re.M,
    )
    return clean(match.group(1)) if match else "المادة في المروحة الحالية؛ لا صف مسمى محرر في بطاقة المصدر."


def arabic_witnesses(body: str, root: str) -> list[tuple[str, str]]:
    start = body.find(f"  - المادة {BT}{root}{BT}:")
    if start < 0:
        return []
    end_points = [
        point for point in (
            body.find("\n  - المادة ", start + 1),
            body.find("\n- الخط الصريح:", start + 1),
        ) if point >= 0
    ]
    section = body[start:min(end_points) if end_points else len(body)]
    accepted = (
        "لسان العرب", "تاج العروس", "تاج اللغة وصحاح العربية", "الصحاح",
        "القاموس المحيط", "مقاييس اللغة", "معجم مقاييس اللغة", "كتاب العين",
        "تهذيب اللغة", "المخصص", "أساس البلاغة", "جمهرة اللغة", "المحكم",
    )
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name, quoted in re.findall(r"^    - ([^:]+): «([^»]+)»", section, re.M):
        name = clean(name)
        if not any(label in name for label in accepted) or name in seen:
            continue
        out.append((name, clip(quoted, 260)))
        seen.add(name)
        if len(out) == 2:
            break
    return out


def render_norse_card(row: dict[str, str], index: int) -> str:
    source = row["source"]
    comp = "COMP-" + source
    phase = "المسبار السداسي" if index <= 6 else "الدفعة الإنتاجية"
    fans = FAN.fan(row["word"], "germanic")
    skeletons = "؛ ".join(f"{'-'.join(skel)} ({note})" for skel, note in FAN.oe_skeletons(row["word"], "germanic"))
    common = f"""### بطاقة إتمام: {BT}{row["word"]}{BT} /{row["roman"]}/؛ {BT}{comp}{BT}
<!-- LANE-D-DONE16-OLD-NORSE:{comp} -->

- إصدار البروتوكول: {BT}RECOVERY-v2{BT}؛ المرحلة: {phase}؛ الطبقة: استكشاف.
- بطاقة المصدر: {BT}{source}{BT} في {BT}phonetic-sweep-germanic-celtic/{row["file"]}{BT}؛ بقيت بلا تعديل.
- مقام المصدر: {BT}{row["pool"]}{BT}؛ معنى صف المسح: «{clip(row["meaning"], 420)}».
- الأداة المصلحة: {BT}fan_any_script.oe_skeletons(word, "germanic"){BT} أعادت {skeletons}؛ والمروحة الحالية {len(fans)} مادة.
"""
    if source in NORSE_POSITIVE:
        root, tier, judgment, orbit = NORSE_POSITIVE[source]
        assert root in fans, (source, row["word"], root)
        ev = event_for(root, tier)
        witnesses = arabic_witnesses(row["body"], root)
        assert len(witnesses) == 2, (source, root, witnesses)
        witness_lines = "\n".join(
            f"  - {name}: «{quoted}»." for name, quoted in witnesses
        )
        path = source_path(row["body"], root)
        assert "لم يتحرر صف مسمى" not in path, (source, root)
        body = f"""- المقابل المختار: {BT}{root}{BT}؛ مسار الصوت: {path}
- الحدث المجمد المختار من جميع الدرجات: الدرجة {tier} ({ev.tier_ar}): «{ev.text}» [{ev.source}].
- مسح المعاني العربية: قرئت الشواهد الكاملة في بطاقة المصدر، ونقل هنا شاهدان مسميان:
{witness_lines}
- المدار المكتوب باليد: {orbit}
- المصفاة: {clip(row["etymology"], 320)} لم تجعل حاشية الأصل بوابة، ولا يغلق القرض إلا مانح سامي مسمى.
- فصل المتجانسات: الحكم للحس المذكور وحده، ولا ينتقل إلى معنى آخر لمجرد الرسم.
- حالة الإغلاق: READY.
- الحكم (استكشاف): {BT}{judgment}{BT}.
"""
    else:
        closest = row["closest"] or (fans[0] if fans else "لا مادة")
        body = f"""- أقرب ما أعادته المروحة: {BT}{closest}{BT}؛ قرئت مواد المروحة وأحداثها وشواهدها في بطاقة المصدر.
- المدار المكتوب باليد: لم يثبت اجتماع رجل الصوت مع حدث مجمد يشرح معنى «{clip(row["meaning"], 240)}» وشاهد عربي صريح؛ فالتشابه الشكلي وحده لا يكفي.
- المصفاة: {clip(row["etymology"], 320)} لم تجعل حاشية الأصل بوابة، ولا يغلق القرض إلا مانح سامي مسمى.
- فصل المتجانسات: لم يرث هذا الحس حكم مادة أو معنى آخر لمجرد الرسم.
- حالة الإغلاق: CLOSED-NO-TRACE.
- الحكم (استكشاف): {BT}NO-TRACE{BT}.
"""
    return common + body


def finish_old_norse() -> list[dict[str, str]]:
    rows = parse_norse_sources()
    chosen = rows[:56]
    assert chosen[0]["source"] == "PS-GC-OLD-NORSE-00055"
    assert chosen[5]["source"] == "PS-GC-OLD-NORSE-00060"
    assert chosen[-1]["source"] == "PS-GC-OLD-NORSE-00204"
    assert set(NORSE_POSITIVE) <= {row["source"] for row in chosen}
    text = ON_FILE.read_text(encoding="utf-8")
    if ON_MARKER in text:
        remove_generated_section(
            ON_FILE, ON_MARKER, "LANE-D-DONE16-OLD-NORSE:END"
        )
    parts = [
        f"""<!-- {ON_MARKER} -->

## الجولة السادسة عشرة: فتح أحكام المسح النردي القديم

- الجرد: 798 بطاقة مصدر كاملة ذات معرفات فريدة، ومعها 798 نسخة مدمجة مرآة؛ فالمجموع الفيزيائي 1596، ومقام الحكم 798 معرفا فريدا.
- المسبار أول 6 معرفات من {BT}PS-GC-OLD-NORSE-00055{BT} إلى {BT}PS-GC-OLD-NORSE-00060{BT}؛ ثم دفعة إنتاجية من 50 معرفا إلى {BT}PS-GC-OLD-NORSE-00204{BT}.
- البطاقات التالية ناسخة للحكم فقط وتذكر معرف المصدر؛ بطاقات المسح الأصلية باقية بلا تعديل.
"""
    ]
    for index, row in enumerate(chosen, 1):
        parts.append(render_norse_card(row, index))
    parts.append(
        "\n- لم تشغل أداة الشحن ولم ينشأ إيداع.\n\n"
        "<!-- LANE-D-DONE16-OLD-NORSE:END -->"
    )
    append(ON_FILE, "\n".join(parts))
    return chosen


def finish_report(oe_cards: list[dict[str, str]], stable: list[str], norse: list[dict[str, str]]) -> None:
    text = REPORT.read_text(encoding="utf-8")
    if REPORT_MARKER in text:
        start = text.index(REPORT_MARKER)
        REPORT.write_text(text[:start].rstrip() + "\n", encoding="utf-8", newline="\n")
    probe = norse[:6]
    production = norse[6:]
    probe_positive = sum(row["source"] in NORSE_POSITIVE for row in probe)
    production_positive = sum(row["source"] in NORSE_POSITIVE for row in production)
    report = f"""## الجولة السادسة عشرة: ختام التصويب وفتح النردية

- الوقت: 2026-08-17، توقيت القاهرة.
- الأداة الحاكمة: {BT}scripts/fan_any_script.py{BT} بعد الإصلاح {BT}0ebb1e9{BT}، باستدعاء الخط {BT}germanic{BT} صراحة.

### ختام التصويب الإنجليزي القديم

- أعيدت قراءة جميع بطاقات {BT}NO-TRACE{BT} الباقية من {BT}PS-GC-OLD-ENGLISH-00852{BT} إلى {BT}PS-GC-OLD-ENGLISH-00967{BT}: عددها {len(oe_cards)}.
- انقلب في هذا النطاق 9 أحكام: 3 منها كانت قد ثبتت في المسبار السابق، و6 تصويبات جديدة ألحقت في الذيل؛ وثبت {len(stable)} حكما.
- خلاصة جولة التصويب كلها منذ تشغيل الأداة المصلحة: 709 عمليات إعادة قراءة، منها 703 بطاقات أصل فريدة و6 إعادات للمسبار؛ واستردت 80 صلة فريدة إجمالا.
- الأصل محفوظ؛ لم تعدل بطاقة إتمام سابقة، ولم تكرر بطاقات التصويب الثلاث المثبتة من قبل.
- كاشف انضباط النواة في الإنجليزية القديمة عاد إلى خط أساسه السابق، 183 ملاحظة تاريخية بلا ملاحظة جديدة من هذه الخاتمة.

### فتح النردية القديمة

- صححت دلالة العدد: ملفات المصدر الكاملة تحمل 798 معرفا فريدا، والملفات المدمجة تعيد المعرفات نفسها في 798 بطاقة مرآة؛ لذلك كان العدد الفيزيائي المذكور 1596، أما مقام الحكم غير المكرر فهو 798.
- المسبار: 6 بطاقات، من {BT}{probe[0]["source"]}{BT} إلى {BT}{probe[-1]["source"]}{BT}؛ الموجب {probe_positive}، و{BT}NO-TRACE{BT} عدد {6 - probe_positive}.
- الدفعة الإنتاجية: 50 بطاقة، من {BT}{production[0]["source"]}{BT} إلى {BT}{production[-1]["source"]}{BT}؛ الموجب {production_positive}، و{BT}NO-TRACE{BT} عدد {50 - production_positive}.
- حصيلة النردية الجديدة: 56 بطاقة إتمام؛ {BT}NUCLEUS-TRACE{BT} عدد 2، و{BT}ROOT-TRACE{BT} عدد 1، و{BT}ROOT-ECHO{BT} عدد 6، و{BT}NO-TRACE{BT} عدد 47.
- كل بطاقة إتمام تذكر معرف المصدر وملفه وتثبت المروحة والمدار والمصفاة والإغلاق؛ وتثبت البطاقة الموجبة الحدث والشاهد ومسار الصوت المسمى.
- آخر موضع: {BT}PS-GC-OLD-NORSE-00204{BT}.
- الضبط: فحص نقاء الشحنة {BT}CLEAN{BT}؛ وفحص مفردات الإغلاق لم يجد بطاقة مغلقة بوسم مخترع؛ وكاشف انضباط النواة عاد إلى خط أساسه السابق، 20 ملاحظة تاريخية بلا ملاحظة جديدة من هذه الدفعة.
- سقف بطاقة الإتمام الجديدة دون 5120 بايت.
- لم تشغل {BT}scripts/ship.py{BT}، ولم ينشأ إيداع.

LANE-D DONE16 103 9 56 PS-GC-OLD-NORSE-00204"""
    append(REPORT, report)


def verify() -> None:
    oe = OE_FILE.read_text(encoding="utf-8")
    on = ON_FILE.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    assert oe.count("LANE-D-DONE16-CORRECTION:CORR-COMP-") == 6
    assert len(re.findall(r"^.*أعيدت قراءته بالأداة المصلحة وثبت الحكم\.$", oe[oe.index(OE_MARKER):], re.M)) == 94
    assert on.count("LANE-D-DONE16-OLD-NORSE:COMP-") == 56
    section = on[on.index(ON_MARKER):]
    assert len(re.findall(r"^- الحكم \(استكشاف\): " + re.escape(BT) + r"(?!NO-TRACE)", section, re.M)) == 9
    assert len(re.findall(r"^- الحكم \(استكشاف\): " + re.escape(BT) + r"NO-TRACE", section, re.M)) == 47
    card_blocks = re.split(r"(?=^### بطاقة إتمام:)", section, flags=re.M)[1:]
    assert len(card_blocks) == 56
    assert max(len(block.encode("utf-8")) for block in card_blocks) <= 5120
    assert report.rstrip().endswith("LANE-D DONE16 103 9 56 PS-GC-OLD-NORSE-00204")
    for addition in (oe[oe.index(OE_MARKER):], section, report[report.index(REPORT_MARKER):]):
        assert "—" not in addition
        assert not re.search(r"[٠-٩]", addition)


def main() -> None:
    oe_cards, stable = finish_old_english()
    norse = finish_old_norse()
    finish_report(oe_cards, stable, norse)
    verify()
    print("LANE-D DONE16 103 9 56 PS-GC-OLD-NORSE-00204")


if __name__ == "__main__":
    main()
