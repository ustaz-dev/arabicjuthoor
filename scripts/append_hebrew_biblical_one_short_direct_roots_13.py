#!/usr/bin/env python3
"""Resolve a final conservative batch of direct Hebrew biblical roots."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter

from append_hebrew_biblical_one_short_source_named_12 import (
    DB,
    DEFAULT_RESOURCES,
    QUEUE,
    READING,
    REPORT,
    atomic_write,
    fold,
    independent_fan,
    item,
    matches_for_roots,
)


ROOT = READING.parents[2]
AUDIT = ROOT / "05-audits" / "2026-07-28-hebrew-biblical-one-short-direct-roots-13-local.md"
MARKER = "<!-- HEBREW-BIBLICAL-ONE-SHORT-DIRECT-ROOTS-13 -->"
DATE = "2026-07-28"
EXPECTED_SHA256 = "756e0f20a3e629e706c9762eff78657ac56fbfdef1a08386d93f70997a736652"

POSITIVE = {
    "kaikki_hebrew:16277:en-קיצץ-he-verb-VS4HGwp1": item(
        "قصص", "قص", "ROOT-TRACE",
        "קיצץ وقص العربية للقطع والفصل",
        "القاف والصادان هويات؛ الياء من بناء السطح.",
        "مباشر في القص والقطع.",
    ),
    "kaikki_hebrew:1405:en-עשור-he-noun-458KGcCy": item(
        "عشر", "عشر", "ROOT-TRACE",
        "עשור وعشر العربية لجملة العشرة",
        "العين والشين والراء هويات؛ الواو من بناء الاسم.",
        "مباشر في مدة الأيام العشرة.",
    ),
    "kaikki_hebrew:13047:en-בקעה-he-noun-aXPnb~As": item(
        "بقع", "بقعة", "ROOT-ECHO",
        "בקעה وبقعة العربية للقطعة المتميزة من الأرض",
        "الباء والقاف والعين هويات؛ اللاحقة من بناء الاسم.",
        "الوادي الواسع بقعة أرض محددة، خطوة دلالية واحدة.",
    ),
    "kaikki_hebrew:9308:en-קדחת-he-noun-HkShxFOI": item(
        "قدح", "قدح", "ROOT-ECHO",
        "קדחת للحمى وقدح العربية لاستخراج النار",
        "القاف والدال والحاء هويات؛ التاء من بناء الاسم.",
        "حرارة الحمى والنار المقدوحة مدار الحرارة.",
    ),
    "kaikki_hebrew:767:en-חרה-he-verb-NT~blP07": item(
        "حرر", "حر", "NUCLEUS-ECHO",
        "חרה لاحتراق الغضب وحر العربية للسخونة",
        "نواة الحاء والراء هوية؛ الرجل الأخيرة لا تدخل حكم النواة.",
        "الغضب المحترق والحرارة مدار واحد سماه معنى الفرع.",
    ),
    "kaikki_hebrew:4203:en-פסח-he-verb-he:pass_over": item(
        "فسخ", "فسخ", "ROOT-ECHO",
        "المصدر يقارن פסח بفسخ العربية في الإبطال والتجاوز",
        "LAB-07 يرخص פ ↔ ف، وGUT-05 يرخص ח ↔ خ؛ السين هوية.",
        "الإبطال وتجاوز الشيء دون إنفاذه خطوة دلالية واحدة.",
    ),
    "kaikki_hebrew:6492:en-דהר-he-verb-eCXHa31H": item(
        "دحر", "دحر", "ROOT-ECHO",
        "المصدر يقارن דהר بدحر العربية في الدفع والحركة السريعة",
        "GUT-04 يرخص ح ↔ ה؛ الدال والراء هويتان.",
        "العدو السريع والدحر دفع في حركة واحدة.",
    ),
    "kaikki_hebrew:1965:en-נוזל-he-noun-MfauD2Tf": item(
        "نزل", "نزل", "ROOT-ECHO",
        "נוזל للسائل ونزل العربية لحركة الانحدار",
        "النون والزاي واللام هويات؛ الواو من بناء السطح.",
        "السائل مادة تنزل وتجري، خطوة دلالية واحدة.",
    ),
    "kaikki_hebrew:13247:en-כסיל-he-noun-fIdNrNQC": item(
        "كسل", "كسل", "ROOT-ECHO",
        "כסיל للأحمق وكسل العربية لثقل الفهم والعمل",
        "الكاف والسين واللام هويات؛ لا صف لازم.",
        "الكسل الذهني والحمق مدار قصور الفعل والفهم.",
    ),
    "kaikki_hebrew:4479:en-פשט-he-verb-615Q~p1R": item(
        "فشط", "فشط", "ROOT-TRACE",
        "פשט وفشط العربية لنزع الغطاء والجلد",
        "LAB-07 يرخص פ ↔ ف؛ الشين والطاء هويتان.",
        "مباشر في نزع الثوب أو الجلد.",
    ),
    "kaikki_hebrew:4849:en-הראה-he-verb-HGMzUJ3r": item(
        "رأي", "رأى", "NUCLEUS-TRACE",
        "المصدر يرد הראה إلى ר־א־ה، ورأى العربية للإبصار والإظهار",
        "نواة الراء والهمزة هوية؛ الهاء السابقة سببية والرجل الضعيفة خارج حكم النواة.",
        "الإراءة جعل الغير يرى، سلسلة الفعل نفسها.",
    ),
    "kaikki_hebrew:7264:en-נזיר-he-noun-ND9fpPgo": item(
        "نذر", "نذر", "ROOT-ECHO",
        "المصدر يرد נזיר إلى נזר للانفصال، ونذر العربية للتكريس الملزم",
        "DENT-04 يرخص ذ ↔ ז؛ النون والراء هويتان.",
        "النذر يفصل صاحبه ويكرسه، وهو وصف النذير في المصدر.",
    ),
    "kaikki_hebrew:10988:en-קציר-he-noun-3auaraA8": item(
        "قصر", "قصر", "ROOT-ECHO",
        "קציר للحصاد وقصر الزرع العربية لقطعه",
        "القاف والصاد والراء هويات؛ الياء من بناء الاسم.",
        "الحصاد قطع الزرع، مباشر في فعل العضو.",
    ),
    "kaikki_hebrew:7381:en-חתונה-he-noun-qeaFVdfV": item(
        "ختن", "ختن", "ROOT-ECHO",
        "חתונה للزواج وختن العربية لقرابة الزواج",
        "GUT-05 يرخص ח ↔ خ؛ التاء والنون هويتان، والواو واللاحقة من بناء الاسم.",
        "الزواج ينشئ قرابة الختن، خطوة دلالية واحدة.",
    ),
}


def main() -> int:
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        print("Hebrew biblical one-short direct roots 13: already present")
        return 0
    proof = json.loads(REPORT.read_text(encoding="utf-8"))
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))["unread_biblical_lexical_queue"]
    biblical = {str(item["entry_id"]): item for item in queue}
    pending = {
        str(row["missing_entry_id"]): row
        for row in proof["languages"]["hebrew"]["one_member_short"]
    }
    selected = [
        entry_id
        for entry_id in POSITIVE
        if entry_id in pending and entry_id in biblical
    ]
    digest = hashlib.sha256("\n".join(selected).encode("utf-8")).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError(f"direct-root selection drifted: {len(selected)} {digest}")

    roots_needed = {str(spec["root"]) for spec in POSITIVE.values()}
    matches = matches_for_roots(DEFAULT_RESOURCES, roots_needed, None)
    fans = {root: independent_fan(matches[root]) for root in roots_needed}
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    cards = []
    counts: Counter[str] = Counter()
    try:
        for rank, entry_id in enumerate(selected, 1):
            row = pending[entry_id]
            queue_item = biblical[entry_id]
            entry = connection.execute(
                "SELECT headword,pos,gloss,etymology FROM entries WHERE entry_id=?",
                (entry_id,),
            ).fetchone()
            if entry is None:
                raise ValueError(f"missing entry: {entry_id}")
            references = "؛ ".join(
                str(witness["reference"])
                for witness in queue_item["biblical_witnesses"]
                if witness["entry_id"] == entry_id
            )
            if not references:
                raise ValueError(f"{entry_id}: exact biblical witness missing")
            spec = POSITIVE[entry_id]
            root = str(spec["root"])
            fan = fans[root]
            sources = list(fan["selected_sources"])
            if not fan["judgment_ready"] or len(sources) < 2:
                raise ValueError(f"{entry_id}: incomplete fan")
            fan_lines = []
            for source in sources[:2]:
                definition = fold(str(source["definition"]))
                positions = [
                    definition.find(fold(term))
                    for term in spec["terms"]
                    if definition.find(fold(term)) >= 0
                ]
                if not positions:
                    raise ValueError(
                        f"{entry_id}: named sense absent in {source['source_label']}"
                    )
                start = max(0, min(positions) - 55)
                end = min(len(definition), min(positions) + 220)
                fan_lines.append(
                    f"  - {source['source_label']}: «{definition[start:end]}»"
                )
            headword = str(entry["headword"])
            pos = str(entry["pos"])
            gloss = str(entry["gloss"])
            etymology = str(entry["etymology"] or "").strip() or "لا أصل مسمى في الحقل"
            state = str(spec["verdict"])
            outcome = f"{state}؛ العضو `{entry_id}` وحده؛ {spec['reason']}."
            cards.append(
                "\n".join(
                    [
                        f"### بطاقة: `{row['family_id']}`، {headword}، الجذور التوراتية المباشرة 13، الرتبة {rank}",
                        f"- عائق: النوع={state}؛ يتطلب=المراجعة الثالثة؛ العضو=`{entry_id}`.",
                        "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)",
                        f"- الكلمةُ في الفرع: {headword}، {pos}، «{gloss}» [Kaikki Hebrew، `{entry_id}`].",
                        f"- أقدمُ صورةٍ مستعادة: شاهد توراتي للعضو نفسه: {references}؛ الأصل المنشور: {etymology}.",
                        "- الخطوةُ صفر (التعرية بصرف الفرع): لم تنزع زيادة إلا إذا سماها المصدر أو بقي الجذر ظاهرًا كاملًا في الصورة.",
                        "- درجةُ المقارنة: الجذر الكامل أولًا، ثم الأجوف والنواة والمدار.",
                        f"- مسارُ الجذر الكامل أولًا: `{root}`؛ لا يحكم المرشح الآلي.",
                        f"- مسحُ المعاني العربيّة: مروحة `{root}` مكتملة من {sources[0]['source_label']} + {sources[1]['source_label']}، والمعنى المسمى حاضر في المصدرين.",
                        *fan_lines,
                        f"- المقابلُ من اللسان: `{root}`.",
                        f"- مسارُ الصوت: {spec['sound']}",
                        f"- المعنى من قاموس الفرع: «{gloss}» [Kaikki Hebrew، `{entry_id}`].",
                        f"- المدار: {spec['bridge']}",
                        "- المصفاة: الزمن والأصل والقرض والعلم والصورة والمركب فُحصت قبل الحكم.",
                        f"- فصلُ المتجانسات والاقتراض: العضو `{entry_id}` وحده؛ لا وراثة.",
                        "- مؤشر اليتم: عضو واحد راقد كان يسقط الأسرة كلها.",
                        "- إشعاع الأسرة في الفرع: لا يرث هذا العضو حكم عضو آخر.",
                        "- إشعاع الأسرة في العربية: المعنى المستشهد به وحده.",
                        "- جسورُ الاسترداد المفحوصة: الشاهد؛ الأصل؛ الجذر؛ الأجوف؛ النواة؛ المدار؛ الصفوف؛ الصورة؛ القرض.",
                        f"- حالةُ الإغلاق: {state}.",
                        f"- الحكم (استكشاف): {outcome}",
                        "- عدسة الاسترداد: استعملت الشاهد والمروحة والدرجة الأدنى.",
                        "- عدسة التشكيك: منعت وراثة الحكم والسالب المصنوع والصف الجديد.",
                        "- ملاحظات: محلي للمراجعة الثالثة؛ لا خط برهان ولا سجل مركزي.",
                        "",
                    ]
                )
            )
            counts["positive"] += 1
    finally:
        connection.close()

    block = "\n".join(
        [
            "",
            MARKER,
            "",
            f"## الجذور التوراتية المباشرة في الأسر الناقصة عضوًا ({DATE}، محلي)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "النطاق هو الجذور المباشرة المحكمة فقط من الأسر التوراتية الناقصة عضوًا واحدًا. كل احتمال احتاج صرفًا غير مسمى أو صفًا جديدًا بقي معلقًا.",
            "",
            *cards,
            "<!-- HEBREW-BIBLICAL-ONE-SHORT-DIRECT-ROOTS-13:END -->",
            "",
        ]
    )
    atomic_write(READING, text.rstrip() + "\n" + block)
    atomic_write(
        AUDIT,
        "\n".join(
            [
                "# الجذور العبرية التوراتية المباشرة",
                "",
                "## النطاق",
                "",
                f"- بطاقات تغير المصير: {len(selected)}.",
                f"- بصمة الترتيب: `{EXPECTED_SHA256}`.",
                "",
                "## الرقمان المفصولان",
                "",
                f"- الصلات الموجبة: {counts['positive']}.",
                "- الإغلاقات النهائية: 0.",
                "",
                "## الحالة",
                "",
                "- محلي للمراجعة الثالثة.",
                "- لا خط برهان ولا سجل مركزي.",
                "",
            ]
        ),
    )
    print(
        json.dumps(
            {
                "cards": len(selected),
                "positive_connections": counts["positive"],
                "terminal_closures": 0,
                "selection_sha256": EXPECTED_SHA256,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
