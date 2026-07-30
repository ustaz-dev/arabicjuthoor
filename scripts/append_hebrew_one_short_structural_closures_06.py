#!/usr/bin/env python3
"""Close eight structural Hebrew members from the official one-short list."""
from __future__ import annotations

import json
import sqlite3
import tempfile
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
REPORT = ROOT / "data" / "proof-eligible-families.json"
POPULATION = ROOT / "data" / "proof-family-population.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
AUDIT = (
    ROOT
    / "05-audits"
    / "2026-07-28-hebrew-one-short-structural-closures-06-local.md"
)
MARKER = "<!-- HEBREW-ONE-SHORT-STRUCTURAL-CLOSURES-06 -->"
DATE = "2026-07-28"

SPECS = {
    "hebrew:family:016b4520ca0b276ec8a0318f": (
        "kaikki_hebrew:15808:en-קלי-he-name-P-PRrXG4",
        "PROPER-NAME-ISOLATED",
        "المصدر يصنف العضو اسم عائلة Kelly، لا لمة عبرية قديمة مستقلة",
    ),
    "hebrew:family:15f4b622c33117c40f266557": (
        "kaikki_hebrew:16933:en-לוז-he-name-Fc6AluEa",
        "PROPER-NAME-ISOLATED",
        "المصدر يصنف العضو اسم مدينتين، فيعزل عن اسم النبات",
    ),
    "hebrew:family:499d472e11f8b99504b135f8": (
        "kaikki_hebrew:10931:en-עכו״ם-he-noun-yhYiRpfH",
        "NONLEXICAL-ISOLATED",
        "المصدر يسمي العضو اختصارًا لعبارة، لا لمة جذرية مستقلة",
    ),
    "hebrew:family:714cdb64ac6188dffd14ac2a": (
        "kaikki_hebrew:13660:en-ק־נ־ה-he-root-it35kNQJ",
        "NONLEXICAL-ISOLATED",
        "العضو رأس جذري وصفي يحيل إلى الكلمات المشتقة، لا لمة معجمية مستقلة",
    ),
    "hebrew:family:a746d0d6d7d7b5c2e7005525": (
        "kaikki_hebrew:5630:en-תמרים-he-noun-w9ulqogb",
        "FORM-OF-ISOLATED",
        "المصدر يسمي العضو جمعًا غير معرف من תמר",
    ),
    "hebrew:family:a8f43475ca98f64f89f0c968": (
        "kaikki_hebrew:7037:en-הכה-he-verb-lQJ1kuTA",
        "FORM-OF-ISOLATED",
        "المصدر يسمي العضو تهجئة ناقصة من הוכה",
    ),
    "hebrew:family:d97c452dc34f7791826029f7": (
        "kaikki_hebrew:12785:en-שבי-he-name-h8YdwBAs",
        "PROPER-NAME-ISOLATED",
        "المصدر يصنف العضو اسم علم مذكر، فيعزل عن اسم السبي",
    ),
    "hebrew:family:b930643d04915762cdb86332": (
        "kaikki_hebrew:692:en-עזה-he-name-JHM-BswD",
        "PROPER-NAME-ISOLATED",
        "المصدر يصنف العضو اسم مدينة غزة، فيعزل بوصفه علمًا",
    ),
}


def atomic_write(path: Path, text: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(unicodedata.normalize("NFC", text))
        temporary = Path(handle.name)
    temporary.replace(path)


def render_card(
    rank: int,
    family_id: str,
    entry: dict[str, object],
    members: list[dict[str, object]],
    state: str,
    reason: str,
) -> str:
    member_list = "؛ ".join(
        f"{item['headword']} `{item['romanization'] or 'بلا رومنة'}`، "
        f"{item['pos']}، «{item['gloss']}» [`{item['entry_id']}`]"
        for item in members
    )
    entry_id = str(entry["entry_id"])
    return "\n".join(
        [
            f"### بطاقة: `{family_id}`، {entry['headword']}، كنس البنية العبرية 6، الرتبة {rank}",
            "- عائق: النوع=READY؛ يتطلب=المراجعة المضادة الثالثة قبل الإيداع.",
            "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)",
            f"- الكلمةُ في الفرع: {member_list}.",
            f"- أقدمُ صورةٍ مستعادة: لا استعادة جذرية للعضو `{entry_id}`؛ وصف المصدر الحي: {reason}.",
            "- الخطوةُ صفر (التعرية بصرف الفرع): يحفظ الرسم كما ورد، ويعزل العضو البنيوي باسمه من غير نقل حكم عضو آخر إليه.",
            "- درجةُ المقارنة: لا تصدر؛ العزل البنيوي يسبق الجذر والأجوف والنواة والمدار.",
            "- مسارُ الجذر الكامل أولًا: غير مطبق على العضو المعزول.",
            "- مسحُ المعاني العربيّة: غير لازم للإغلاق البنيوي، ولا يستعمل غيابه سالبًا لغويًا.",
            "- المقابلُ من اللسان: لا مقابل محكوم.",
            "- مسارُ الصوت: لا صف صوت مستعمل.",
            f"- المعنى من قاموس الفرع: «{entry['gloss']}» [Kaikki Hebrew، `{entry_id}`].",
            "- المدار: غير صادر.",
            "- المصفاة: تصنيف المصدر للعضو هو سبب العزل، ولا يرث العضو حكم الأسرة.",
            f"- فصلُ المتجانسات والاقتراض: العضو `{entry_id}` وحده؛ {reason}.",
            "- مؤشر اليتم: جميع أعضاء الأسرة باقون في مواضعهم، ولا يحذف العزل سجلًا.",
            "- إشعاع الأسرة في الفرع: الأعضاء المعجمية المدعومة=0 لهذا العضو؛ الإغلاق لا ينتقل.",
            "- إشعاع الأسرة في العربية: الأعضاء المعجمية المدعومة=0؛ العزل لا يعد صلة.",
            "- جسورُ الاسترداد المفحوصة: تصنيف العضو؛ الروابط الصرفية؛ المتجانسات؛ حق النقض العضوي.",
            f"- حالةُ الإغلاق: {state} للعضو `{entry_id}`.",
            f"- الحكم (استكشاف): غير صادر؛ {state} للعضو `{entry_id}`؛ {reason}.",
            "- عدسة الاسترداد: أبقت العضو ظاهرًا وربطته بوصف مصدره.",
            "- عدسة التشكيك: منعت عد الاسم أو الاختصار أو الصورة الصرفية شاهدًا معجميًا مستقلًا.",
            "- ملاحظات: بطاقة محلية للمراجعة المضادة الثالثة؛ لا خط برهان ولا سجل مركزي.",
            "",
        ]
    )


def main() -> int:
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        print("Hebrew one-short structural closures 06: already present")
        return 0
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    one_short = {
        item["family_id"]: item
        for item in report["languages"]["hebrew"]["one_member_short"]
    }
    for family_id, (entry_id, _, _) in SPECS.items():
        current = one_short.get(family_id)
        if current is None or current["missing_entry_id"] != entry_id:
            raise ValueError(f"target is not the expected one-short member: {family_id}")
    population = json.loads(POPULATION.read_text(encoding="utf-8"))
    families = {
        item["family_id"]: item
        for item in population["languages"]["hebrew"]["families"]
    }
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    cards = []
    try:
        for rank, (family_id, (entry_id, state, reason)) in enumerate(
            SPECS.items(), 1
        ):
            entry_row = connection.execute(
                "SELECT entry_id,headword,romanization,pos,gloss,etymology "
                "FROM entries WHERE entry_id=?",
                (entry_id,),
            ).fetchone()
            if entry_row is None:
                raise ValueError(f"missing entry: {entry_id}")
            members = []
            for member in families[family_id]["members"]:
                row = connection.execute(
                    "SELECT entry_id,headword,romanization,pos,gloss "
                    "FROM entries WHERE entry_id=?",
                    (member["entry_id"],),
                ).fetchone()
                if row is None:
                    raise ValueError(f"missing member: {member['entry_id']}")
                members.append(dict(row))
            cards.append(
                render_card(
                    rank,
                    family_id,
                    dict(entry_row),
                    members,
                    state,
                    reason,
                )
            )
    finally:
        connection.close()
    block = "\n".join(
        [
            "",
            MARKER,
            "",
            f"## كنس الأعضاء البنيوية في الأسر العبرية الناقصة واحدًا ({DATE}، محلي)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "النطاق هو التقاطع الكامل بين قائمة الأسر الناقصة عضوًا واحدًا والأعضاء الثمانية التي يسمي وصف المصدر فيها علمًا أو اختصارًا أو رأسًا جذريًا أو صورة صرفية محالة. لا حكم نسب في الدفعة.",
            "",
            *cards,
            "<!-- HEBREW-ONE-SHORT-STRUCTURAL-CLOSURES-06:END -->",
            "",
        ]
    )
    atomic_write(READING, text.rstrip() + "\n" + block)
    atomic_write(
        AUDIT,
        "\n".join(
            [
                "# كنس الأعضاء البنيوية في الأسر العبرية الناقصة واحدًا",
                "",
                "## النطاق",
                "",
                "أغلقت ثمانية أعضاء بنيويين سمى المصدر نوعهم صراحة، من غير حكم نسب أو سالب لغوي.",
                "",
                "## الرقمان المفصولان",
                "",
                "- الصلات الموجبة: 0.",
                "- الإغلاقات النهائية: 8.",
                "",
                "## الحالة",
                "",
                "- البطاقات محلية للمراجعة المضادة الثالثة.",
                "- لا سجل مركزي ولا تشغيل لخط البرهان.",
                "",
            ]
        ),
    )
    print(
        json.dumps(
            {"positive_connections": 0, "terminal_closures": len(SPECS)},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
