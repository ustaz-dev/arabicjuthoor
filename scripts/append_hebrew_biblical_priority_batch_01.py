#!/usr/bin/env python3
"""Append the first ten exact-member biblical Hebrew cards.

The order is taken verbatim from the member-safe priority queue. Every family
gets a fate; the script does not select only positive comparisons. All
verdict-bearing cards remain local for the third-lens review.
"""
from __future__ import annotations

import json
import re
import sqlite3
import tempfile
import unicodedata
from pathlib import Path

from search_arabic_root_senses import (
    ARABIC_MARKS,
    DEFAULT_RESOURCES,
    independent_fan,
    matches_for_roots,
)


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
QUEUE = ROOT / "data" / "hebrew-biblical-priority-queue.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
AUDIT = (
    ROOT
    / "05-audits"
    / "2026-07-27-hebrew-biblical-unread-batch-01-local.md"
)
DATE = "2026-07-27"
MARKER = "<!-- HEBREW-BIBLICAL-UNREAD-BATCH-01 -->"

EXPECTED = [
    "hebrew:family:a746d0d6d7d7b5c2e7005525",
    "hebrew:family:755fb18dfd6cc6404a9d2bc1",
    "hebrew:family:2ed05901ee318e861014d864",
    "hebrew:family:023e350d6976cc29734737d5",
    "hebrew:family:318e7abf5e5ff50d74d4aec4",
    "hebrew:family:e3c1b795c502219e542c30cc",
    "hebrew:family:1159719a60fcb19316686677",
    "hebrew:family:f20abd325fbb060949428516",
    "hebrew:family:016b4520ca0b276ec8a0318f",
    "hebrew:family:700af3384ba185c4244d942b",
]

SPECS: dict[str, dict[str, object]] = {
    EXPECTED[0]: {
        "kind": "terminal",
        "state": "INTRA-HOUSE-TRANSFER",
        "root": "تمر",
        "reason": (
            "المصدر يسمي الآرامية مانحًا مبكرًا، ويسمي تمر العربية "
            "اقتراضًا موازيًا؛ يحال إلى زوج المانح ولا يعد شاهد فرع مستقل"
        ),
        "sound": "لا يستعمل صف صوت لإنتاج حكم نسب؛ طريق النقل المنشور حاكم.",
        "bridge": "المعنى مطابق للتمر، لكن قاعدة عمق القرض تسبق المطابقة.",
    },
    EXPECTED[1]: {
        "kind": "positive",
        "state": "READY",
        "root": "وهب",
        "terms": ("العطية", "أعطيت"),
        "verdict": "ROOT-TRACE",
        "reason": (
            "הבה الدعائية من صيغة الأمر المنشورة لفعل יהב «أعطى» "
            "تقابل وهب في العطاء"
        ),
        "sound": (
            "GLD-01 من الواو العربية الأولى إلى الياء الشمالية في יהב؛ "
            "الهاء والباء هويتان، واللاحقة ־ה مسماة في تحليل المصدر"
        ),
        "bridge": "مباشر في فعل الإعطاء، مع انتقال صيغة الأمر إلى الدعاء بالفعل.",
    },
    EXPECTED[2]: {
        "kind": "open",
        "state": "OPEN-CANDIDATE",
        "root": "حلب",
        "reason": (
            "الشاهد التوراتي للعضو חלב «الشحم المحرم»، أما حلب العربية "
            "فتثبت استخراج اللبن؛ علاقة مادة الدسم محتملة لا مباشرة"
        ),
        "sound": "هيكل ח־ל־ב أمام حلب قريب، ولا يكفي وحده لحكم المعنى.",
        "bridge": "مرشح مدار مادة الألبان والدسم، يحتاج تسمية أدق قبل الحكم.",
    },
    EXPECTED[3]: {
        "kind": "law-gap",
        "state": "LAW-GAP",
        "root": "آس",
        "reason": (
            "المصدر يقارن הדס بالآرامية آسא والعربية آس والأكدية asum، "
            "لكن حذف هاء ودال السطح العبري أو ردهما غير مرخص بصف موقع"
        ),
        "sound": "لا صف موقع يحول הדס إلى آس؛ المقارنة المنشورة تحفظ مرشحًا لا حكمًا.",
        "bridge": "مباشر في نبات الآس العطر.",
    },
    EXPECTED[4]: {
        "kind": "positive",
        "state": "READY",
        "root": "بني",
        "terms": ("نقيض الهدم", "بناء"),
        "verdict": "ROOT-TRACE",
        "reason": (
            "المصدر يعيد Proto-Semitic *banay- ويسمي العربية بنى "
            "مقابلًا، والمعنى البناء والإنشاء نفسه"
        ),
        "sound": (
            "الباء والنون هويتان، والياء الأصلية مثبتة في *banay-؛ "
            "السطح العبري בנה يعامل في هذا العضو بإعادة البناء المنشورة "
            "لا بصف عام جديد"
        ),
        "bridge": "مباشر في البناء والإنشاء.",
    },
    EXPECTED[5]: {
        "kind": "positive",
        "state": "READY",
        "root": "عشب",
        "terms": ("العشب", "الكلأ"),
        "verdict": "ROOT-TRACE",
        "reason": (
            "עשב النبات والعشب يقابل عشب العربية بنص المصدر ومروحة "
            "المعجمين القديمين"
        ),
        "sound": (
            "SIB-07 في שׂ العبرية أمام ش العربية؛ العين والباء هويتان"
        ),
        "bridge": "مباشر في العشب والكلأ الرطب.",
    },
    EXPECTED[6]: {
        "kind": "open",
        "state": "OPEN-CANDIDATE",
        "root": "رتل",
        "reason": (
            "נטל «حمّل وألقى حملًا» لا يطابق رتل العربية في انتظام "
            "الشيء أو الكلام، رغم ترخيص المرشح صوتيًا"
        ),
        "sound": "مرشح רטל ↔ رتل يحتاج LIQ-03 كما يسجل الجرد؛ لا صف زائد.",
        "bridge": "لا جسر دلالي مباشر؛ يبقى المرشح مفتوحًا دون سالب مصنوع.",
    },
    EXPECTED[7]: {
        "kind": "open",
        "state": "OPEN-CANDIDATE",
        "root": "يبم",
        "reason": (
            "יבם «أخو الزوج» قديم، لكن يبم العربية لم تعط مروحة مصدرين "
            "ولا معنى القرابة؛ الموجود في مصدر واحد اسم موضع"
        ),
        "sound": "الرسم ي־ב־ם لا يتحول إلى حكم من الهوية الشكلية وحدها.",
        "bridge": "لا معنى عربي مطابق بعد؛ لا يغلق المرشح سلبيًا قبل نزول لاحق.",
    },
    EXPECTED[8]: {
        "kind": "positive",
        "state": "READY",
        "root": "قلي",
        "terms": ("المقلاة", "أنضجه"),
        "verdict": "ROOT-TRACE",
        "reason": (
            "קלי الخبز أو الحب المحمص يرده المصدر إلى العربية قلى، "
            "والمعجمان يسميان إنضاج الشيء على المقلاة"
        ),
        "sound": (
            "القاف واللام هويتان، والياء محفوظة في الجذر المعتل؛ لا صف لازم"
        ),
        "bridge": "مباشر في التحميص والإنضاج على المقلاة.",
    },
    EXPECTED[9]: {
        "kind": "open",
        "state": "OPEN-CANDIDATE",
        "root": "فري",
        "reason": (
            "פרי «الثمر» يعاد إلى *piry- مع شواهد جعزية وأوغاريتية، "
            "أما فري العربية فتدور على الشق والقطع لا الثمر"
        ),
        "sound": "LAB-07 يرخص פ ↔ ف، والراء والياء هويتان في المرشح.",
        "bridge": "لا جسر دلالي مباشر؛ النواة لا تحكم بدل الجذر بلا مدار مسمى.",
    },
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


def fold_arabic(value: str) -> str:
    value = ARABIC_MARKS.sub("", unicodedata.normalize("NFKC", value))
    return " ".join(value.split())


def semantic_excerpt(
    definition: str, terms: tuple[str, ...]
) -> str:
    folded = fold_arabic(definition)
    positions = [
        folded.find(fold_arabic(term))
        for term in terms
        if folded.find(fold_arabic(term)) >= 0
    ]
    if not positions:
        raise ValueError(f"semantic terms absent: {terms}")
    start = max(0, min(positions) - 65)
    end = min(len(folded), min(positions) + 230)
    return folded[start:end]


def fan_map() -> dict[str, dict[str, object]]:
    roots = {str(item["root"]) for item in SPECS.values()}
    matches = matches_for_roots(DEFAULT_RESOURCES, roots, None)
    result: dict[str, dict[str, object]] = {}
    for root in roots:
        fan = independent_fan(matches[root])
        result[root] = {
            "judgment_ready": bool(fan["judgment_ready"]),
            "sources": [
                {
                    "source": str(row["source_label"]),
                    "definition": str(row["definition"]),
                }
                for row in fan["selected_sources"]
            ],
        }
    return result


def members_for(
    connection: sqlite3.Connection, family: str
) -> list[dict[str, object]]:
    return [
        {
            "entry_id": row[0],
            "headword": row[1],
            "romanization": row[2],
            "pos": row[3],
            "gloss": row[4],
            "etymology": row[5],
            "loan_hint": bool(row[6]),
            "role": row[7],
            "links": json.loads(row[8]),
        }
        for row in connection.execute(
            """
            SELECT e.entry_id,e.headword,e.romanization,e.pos,e.gloss,
                   e.etymology,e.loan_hint,fm.role,fm.link_types_json
            FROM family_members AS fm
            JOIN entries AS e ON e.entry_id=fm.entry_id
            WHERE fm.family_id=?
            ORDER BY e.entry_id
            """,
            (family,),
        )
    ]


def roots_for(
    connection: sqlite3.Connection, entry_id: str
) -> list[dict[str, object]]:
    return [
        {
            "form": row[0],
            "status": row[1],
            "rules": json.loads(row[2]),
            "route_flag": bool(row[3]),
        }
        for row in connection.execute(
            """
            SELECT DISTINCT form,status,rule_ids_json,route_flag
            FROM candidates
            WHERE entry_id=? AND kind='root'
            ORDER BY route_flag,status,form,rule_ids_json
            """,
            (entry_id,),
        )
    ]


def format_members(members: list[dict[str, object]]) -> str:
    return "؛ ".join(
        f"{item['headword']} `{item['romanization'] or 'بلا رومنة'}`، "
        f"{item['pos']}، «{item['gloss']}» "
        f"[Kaikki Hebrew، `{item['entry_id']}`]"
        for item in members
    )


def format_roots(roots: list[dict[str, object]]) -> str:
    if not roots:
        return "لا جذر كامل مولد للعضو في الجرد؛ تُحفظ المقارنة المنشورة مستقلة."
    return "؛ ".join(
        f"`{item['form']}` ({item['status']}؛ "
        f"{','.join(item['rules']) if item['rules'] else 'هوية'}"
        f"{'؛ مسار مشروط' if item['route_flag'] else ''})"
        for item in roots
    )


def fan_text(
    root: str,
    specification: dict[str, object],
    fans: dict[str, dict[str, object]],
) -> tuple[str, list[str]]:
    fan = fans[root]
    rows = list(fan["sources"])
    if specification["kind"] == "positive":
        if not fan["judgment_ready"] or len(rows) < 2:
            raise ValueError(f"positive root lacks two-source fan: {root}")
        excerpts = [
            semantic_excerpt(
                str(row["definition"]),
                tuple(specification["terms"]),
            )
            for row in rows[:2]
        ]
        sources = [str(row["source"]) for row in rows[:2]]
        return (
            f"مروحة مستقلة مكتملة للجذر `{root}` من "
            f"{' + '.join(sources)}؛ المعنى المسمى حاضر في المصدرين.",
            [
                f"{source}: «{excerpt}»"
                for source, excerpt in zip(sources, excerpts)
            ],
        )
    if not rows:
        return (
            f"لم يجد مسح المعاجم القديمة مدخلًا للجذر `{root}`؛ "
            "لا يحول الغياب إلى حكم سلبي.",
            [],
        )
    sources = [str(row["source"]) for row in rows]
    excerpts = [
        " ".join(str(row["definition"]).split())[:240] for row in rows
    ]
    return (
        f"مروحة `{root}`: {len(rows)} مصدر مستقل؛ "
        f"{' + '.join(sources)}؛ لا يصدر الحكم آليًا منها.",
        [
            f"{source}: «{excerpt}»"
            for source, excerpt in zip(sources, excerpts)
        ],
    )


def render_card(
    rank: int,
    queued: dict[str, object],
    specification: dict[str, object],
    members: list[dict[str, object]],
    roots: list[dict[str, object]],
    fans: dict[str, dict[str, object]],
) -> str:
    family = str(queued["family_id"])
    entry = str(queued["entry_id"])
    exact_witnesses = [
        item
        for item in queued["biblical_witnesses"]
        if item["entry_id"] == entry
    ]
    if not exact_witnesses:
        raise ValueError(f"{family}: queued member lacks exact witness")
    references = "؛ ".join(
        str(item["reference"]) for item in exact_witnesses
    )
    member = next(item for item in members if item["entry_id"] == entry)
    etymology = str(member["etymology"]).strip() or "لا أصل مسمى في الحقل"
    root = str(specification["root"])
    scan, fan_notes = fan_text(root, specification, fans)
    state = str(specification["state"])
    kind = str(specification["kind"])
    positive = kind == "positive"
    terminal = kind == "terminal"
    if positive:
        verdict = (
            f"{specification['verdict']}؛ العضو `{entry}` وحده؛ "
            f"{specification['reason']}."
        )
        branch_radiation = (
            "الأعضاء المعجمية المدعومة=1؛ سلاسل المعنى المدعومة=1؛ "
            "سائر أعضاء الأسرة بحق نقض مستقل."
        )
        arabic_radiation = (
            "الأعضاء المعجمية المدعومة=1؛ سلاسل المعنى المدعومة=1؛ "
            "العد للمعنى المستشهد به من المروحة فقط."
        )
    elif terminal:
        verdict = (
            f"غير صادر؛ `{state}` للعضو `{entry}`؛ "
            f"{specification['reason']}."
        )
        branch_radiation = (
            "الأعضاء المعجمية المدعومة=0؛ سلاسل المعنى المدعومة=0؛ "
            "العزل لا يعد صلة."
        )
        arabic_radiation = branch_radiation
    else:
        verdict = f"غير صادر؛ {specification['reason']}."
        branch_radiation = (
            "الأعضاء المعجمية المدعومة=0؛ سلاسل المعنى المدعومة=0؛ "
            "لا حكم."
        )
        arabic_radiation = branch_radiation

    filter_note = (
        "وسم القرض حاضر في بعض أعضاء الأسرة؛ فُصل كل عضو باسمه."
        if any(item["loan_hint"] for item in members)
        else "لا وسم قرض آلي في أعضاء الأسرة؛ غيابه ليس حكم أصالة."
    )
    notes = "\n".join(f"  - {item}" for item in fan_notes)
    return "\n".join(
        [
            f"### بطاقة: `{family}`، {queued['headword']}، "
            f"الطابور التوراتي العضوي 1، الرتبة {rank}",
            f"- عائق: النوع={state}؛ يتطلب="
            + (
                "المراجعة المضادة الثالثة قبل الإيداع."
                if positive
                else f"{specification['reason']}."
            )
            + f"؛ العضو=`{entry}`.",
            "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)",
            f"- الكلمةُ في الفرع: {format_members(members)}.",
            f"- أقدمُ صورةٍ مستعادة: الشاهد التوراتي للعضو نفسه: "
            f"{references}؛ الأصل المنشور: {etymology}.",
            "- الخطوةُ صفر (التعرية بصرف الفرع): العضو المشهود نفسه "
            "وحدة الحكم؛ الصور الصرفية والمتجانسات والمركبات لا ترثه. "
            "لا تنزع زيادة إلا إذا سماها المصدر.",
            "- درجةُ المقارنة: الجذر الكامل أولًا، ثم الأجوف والنواة "
            "والمدار عند تعذر الجذر؛ لا يقفز الحكم فوق درجة ناجحة.",
            f"- مسارُ الجذر الكامل أولًا: {format_roots(roots)}",
            f"- مسحُ المعاني العربيّة: {scan}",
            *([notes] if notes else []),
            f"- المقابلُ من اللسان: `{root}`؛ قراءته ومعانيه في المروحة "
            "أعلاه، وتبقى الأدوات المجمدة مرجع استرداد لا حكمًا آليًا.",
            f"- مسارُ الصوت: {specification['sound']}",
            f"- المعنى من قاموس الفرع: «{member['gloss']}» "
            f"[Kaikki Hebrew، `{entry}`].",
            f"- المدار: {specification['bridge']}",
            f"- المصفاة: {filter_note}",
            "- فصلُ المتجانسات والاقتراض: "
            + "؛ ".join(
                f"`{item['entry_id']}`: الدور={item['role']}، "
                f"الروابط={','.join(item['links']) or 'بلا رابط'}، "
                f"القرض={'موسوم' if item['loan_hint'] else 'غير موسوم'}"
                for item in members
            )
            + "؛ لكل عضو حق نقض مستقل.",
            "- مؤشر اليتم: كل أعضاء الأسرة محفوظة؛ لا تسقط صورة ولا "
            "تغلق فجوة بتخمين.",
            f"- إشعاع الأسرة في الفرع: {branch_radiation}",
            f"- إشعاع الأسرة في العربية: {arabic_radiation}",
            "- جسورُ الاسترداد المفحوصة: الشاهد التوراتي؛ العضو نفسه؛ "
            "الجذر الكامل؛ مروحة المعاجم القديمة؛ الأصل المنشور؛ "
            "الصفوف اللازمة وحدها؛ المتجانسات؛ القرض؛ الأجوف والنواة والمدار.",
            f"- حالةُ الإغلاق: {state}.",
            f"- الحكم (استكشاف): {verdict}",
            "- عدسة الاسترداد: بدأت بالجذر الكامل، وأبقت المقارنة "
            "المنشورة والمرشحات المرخصة والدرجات الأدنى ظاهرة.",
            "- عدسة التشكيك: اختبرت عضو الشاهد والقرض والمتجانس ومسار "
            "الصوت، ومنعت وراثة الحكم أو صناعة سالب من فجوة.",
            "- ملاحظات: بطاقة محلية للمراجعة المضادة الثالثة؛ لا خط "
            "برهان، ولا تحديث للسجل المركزي، ولا رقم للنشر.",
            "",
        ]
    )


def main() -> int:
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        print("Hebrew biblical unread batch 01: already present")
        return 0
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    batch = queue["unread_biblical_lexical_queue"][:10]
    families = [str(item["family_id"]) for item in batch]
    if families != EXPECTED:
        raise ValueError(f"priority order drifted: {families}")
    if any(str(item["entry_id"]) not in {
        str(witness["entry_id"]) for witness in item["biblical_witnesses"]
    } for item in batch):
        raise ValueError("the queue contains a non-witness member")

    if any(family in text for family in EXPECTED):
        raise ValueError("an unread batch family is already present")

    fans = fan_map()
    cards: list[str] = []
    connection = sqlite3.connect(DB)
    try:
        for rank, item in enumerate(batch, 1):
            family = str(item["family_id"])
            cards.append(
                render_card(
                    rank,
                    item,
                    SPECS[family],
                    members_for(connection, family),
                    roots_for(connection, str(item["entry_id"])),
                    fans,
                )
            )
    finally:
        connection.close()

    block = "\n".join(
        [
            "",
            MARKER,
            "",
            "## العبريّة التوراتية، دفعة العضو الصريح 1 "
            f"({DATE}، محلية للمراجعة الثالثة)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "الدفعة هي أول عشر أسر حرفيًا من طابور الشاهد التوراتي "
            "بعد إصلاحه ليشترط أن يحمل العضو المصطف نفسه الشاهد. لم "
            "تنتق الصلات: لكل أسرة من العشر مصير مسمى.",
            "",
            *cards,
            "<!-- HEBREW-BIBLICAL-UNREAD-BATCH-01:END -->",
            "",
        ]
    )
    updated = unicodedata.normalize("NFC", text.rstrip() + "\n" + block)
    if unicodedata.normalize("NFC", updated) != updated:
        raise ValueError("Hebrew reading is not NFC")
    atomic_write(READING, updated)
    atomic_write(
        AUDIT,
        "\n".join(
            [
                "# العبريّة التوراتية، دفعة العضو الصريح 1 المحلية",
                "",
                "## بيان النطاق",
                "",
                "قُرئت أول عشر أسر من الطابور الحتمي بعد اشتراط تطابق عضو الشاهد مع عضو القراءة. لم ينتق موجب ويترك غيره.",
                "",
                "## الرقمان المفصولان",
                "",
                "- الصلات الموجبة: 4، وهي הבה ↔ وهب، בנה ↔ بنى، עשב ↔ عشب، קלי ↔ قلي.",
                "- الإغلاقات النهائية: 1، وهو תמר انتقالًا داخل البيت من الآرامية، لا شاهد فرع مستقلًا.",
                "",
                "## الباقي",
                "",
                "- مرشحات مفتوحة بلا حكم: 4، وهي חלב وנטל وיבם وפרי.",
                "- فجوة قانون صوتي: 1، وهي הדס أمام آس.",
                "",
                "## الحالة",
                "",
                "- البطاقات العشر محلية للمراجعة المضادة الثالثة.",
                "- لم يشغل خط البرهان ولم يجدد سجل الاسترداد المركزي.",
                "- الأعداد محاسبية داخلية لا تصلح للنشر.",
                "",
            ]
        ),
    )
    print(
        json.dumps(
            {
                "cards": 10,
                "positive_connections": 4,
                "terminal_closures": 1,
                "open_candidates": 4,
                "law_gaps": 1,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
