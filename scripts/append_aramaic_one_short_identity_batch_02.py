#!/usr/bin/env python3
"""Read the first fifty one-short Aramaic families with an identity candidate."""
from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
REPORT = ROOT / "data" / "proof-eligible-families.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
BASE_PATH = ROOT / "scripts" / "append_aramaic_one_short_source_rich_batch_01.py"
AUDIT = (
    ROOT
    / "05-audits"
    / "2026-07-28-aramaic-one-short-identity-batch-02-local.md"
)
DATE = "2026-07-28"
MARKER = "<!-- ARAMAIC-ONE-SHORT-IDENTITY-BATCH-02 -->"


EXPECTED = [
    "aramaic:family:02c1b1dac8d711a07c6e900e",
    "aramaic:family:036ee5d4e41402194a6633f6",
    "aramaic:family:046f9203924ab8a11f70fa3d",
    "aramaic:family:05977cca85cb2a44db80bb46",
    "aramaic:family:0c0259773d0719a965e2d36a",
    "aramaic:family:0fbd54b9834166f7b8c738d5",
    "aramaic:family:1002b0477ed23b4bb5989447",
    "aramaic:family:12ae32444d7be4cb9b074e79",
    "aramaic:family:133bca0d84a94fa19c004f5b",
    "aramaic:family:186dad85e337205b8fdbc8a2",
    "aramaic:family:19866099a2555b8601763f0f",
    "aramaic:family:1ac57125f59653cf329a2bae",
    "aramaic:family:1f78386e88ebaebe00582b5f",
    "aramaic:family:1fce82d856cec629da7294f7",
    "aramaic:family:243165b2ec7e7a2b312602bb",
    "aramaic:family:248808daa7b1d22f2f5cec7c",
    "aramaic:family:248db59f64c8f76c37838baa",
    "aramaic:family:25d460ececdff6fa87268d5a",
    "aramaic:family:26cd4bee1901cd0d7b958057",
    "aramaic:family:2a8b380174a4d0be2c4bd4d1",
    "aramaic:family:2add4ae021a18aabd5c4cbe0",
    "aramaic:family:2c73bda01a0b7f7b1a1c2540",
    "aramaic:family:2d172090b8b473ab09ecd82a",
    "aramaic:family:2d50c9bb13f8e577efcda32f",
    "aramaic:family:2f91efae55dafaaf3ccad88d",
    "aramaic:family:347f1a2998872f4e1e99e59e",
    "aramaic:family:37879daa06faa13c958eddc0",
    "aramaic:family:37ef1c278ebee491dcfa8836",
    "aramaic:family:38fa380cb0c8248142e0214c",
    "aramaic:family:3999a63de633df66e4b35e6f",
    "aramaic:family:3cbd01108d18dee6dbc132c0",
    "aramaic:family:3e2e6b31cd6451713b164b85",
    "aramaic:family:3ef86a1b3e64562efdf60453",
    "aramaic:family:40a1421bfd0131bd301307f1",
    "aramaic:family:45798b084ba361db64bf0acd",
    "aramaic:family:4658edb0dbfaa36bed3dac48",
    "aramaic:family:4665365e9e11785bf1fe4406",
    "aramaic:family:48c7b257cdd32f0ca79ed616",
    "aramaic:family:490721c4b5f9074ad20a45b3",
    "aramaic:family:496ba1372fc005c37d10c969",
    "aramaic:family:499f9807141b9f844cd170fb",
    "aramaic:family:4a4289c5547f75d30020193d",
    "aramaic:family:4ab169463a3d99396110e8ba",
    "aramaic:family:4d2f878e7091de73fe5f1b74",
    "aramaic:family:4d53448cfb2f0d9b1ca2a1bc",
    "aramaic:family:4e034bf7558d70476cbf2f6e",
    "aramaic:family:4e4a6828c1b56f1f0df369d8",
    "aramaic:family:5122d64ddaac6c3e84f764de",
    "aramaic:family:54d6f50935ace9a5c9b292e4",
    "aramaic:family:5616d3264a1f361b4cb6e9d5",
]


def open_spec(root: str, contrast: str) -> dict[str, object]:
    return {
        "kind": "gap",
        "state": "OPEN-CANDIDATE",
        "root": root,
        "reason": contrast,
        "sound": "المرشح مطابق ذاتيًا أو مرخص، لكن الرجل الدلالية لا تكتمل بالهيكل وحده.",
        "bridge": "لا جسر مباشر مسمى بعد المروحة.",
    }


def gap_spec(state: str, root: str, reason: str, sound: str) -> dict[str, object]:
    return {
        "kind": "gap",
        "state": state,
        "root": root,
        "reason": reason,
        "sound": sound,
        "bridge": "العائق المسمى يمنع الحكم ولا يصنع سالبًا.",
    }


def terminal_spec(state: str, root: str, reason: str) -> dict[str, object]:
    return {
        "kind": "terminal",
        "state": state,
        "root": root,
        "reason": reason,
        "sound": "العزل مسمى في المصدر؛ لا يستعمل صف صوت لإنتاج حكم نسب.",
        "bridge": "العزل لا يعد صلة.",
    }


def positive_spec(
    root: str,
    terms: tuple[str, ...],
    verdict: str,
    reason: str,
    sound: str,
    bridge: str,
) -> dict[str, object]:
    return {
        "kind": "positive",
        "state": "READY",
        "root": root,
        "terms": terms,
        "verdict": verdict,
        "reason": reason,
        "sound": sound,
        "bridge": bridge,
    }


SPECS: dict[str, dict[str, object]] = {
    EXPECTED[0]: open_spec("عمد", "עמד للغوص، وعمد العربية للقصد أو إقامة العمود."),
    EXPECTED[1]: open_spec("حور", "חור للنظر، وحور العربية لا تسمي فعل النظر نفسه."),
    EXPECTED[2]: open_spec("رهط", "רהט للجري، ورهط العربية للجماعة."),
    EXPECTED[3]: open_spec("حجر", "חגר للعرج، وحجر العربية للمنع أو الصخر."),
    EXPECTED[4]: open_spec("فلح", "פלחא للخادم من العمل، وفلح العربية تدور على الشق والفلاحة؛ مدار العامل محتمل غير مسمى."),
    EXPECTED[5]: open_spec("نفل", "נפל للسقوط، ونفل العربية للزيادة والعطاء."),
    EXPECTED[6]: gap_spec("LAW-GAP", "عشب", "עסבא للعشب نفسه، لكن ש أمام ش تحتاج الصف الموقع المناسب لا مرشح عصب الأسهل رسمًا.", "لا يستبدل عصب بعشب لمجرد أن المولد أخرجه."),
    EXPECTED[7]: gap_spec("LAW-GAP", "خطف", "חטף للأخذ السريع ويقابل خطف معنى، لكن ח أمام خ خارج الصف النافذ.", "GUT-05 لا يمد إلى الآرامية بلا توقيع."),
    EXPECTED[8]: terminal_spec("FORM-OF-ISOLATED", "سيب", "المصدر يسمي العضو تهجئة بديلة صريحة للمة סִפָּא."),
    EXPECTED[9]: open_spec("سكت", "סכתא للوتد، وسكت العربية للصمت."),
    EXPECTED[10]: positive_spec("صلب", ("صلبه", "الصليب"), "ROOT-TRACE", "צלב وصلب في فعل الصلب نفسه", "الصاد واللام والباء هويات.", "مباشر في الصلب."),
    EXPECTED[11]: positive_spec("حكم", ("الحكمة", "حكيم"), "ROOT-TRACE", "חכם وحكم في الحكمة", "الحاء والكاف والميم هويات.", "مباشر في الحكمة."),
    EXPECTED[12]: open_spec("زلم", "זלם للتشويه، وزلم العربية لا تسمي التشويه."),
    EXPECTED[13]: open_spec("حبط", "חפט للتحريض، وحبط العربية للبطلان والفساد."),
    EXPECTED[14]: positive_spec("حيي", ("الحياة", "حي"), "ROOT-TRACE", "חייא وحيي في الحياة", "الحاء والياءان هويات؛ ألف الحالة خارج الجذر.", "مباشر في الحياة."),
    EXPECTED[15]: open_spec("بعر", "פערא للشق والفجوة، وبعر العربية لا يسميهما."),
    EXPECTED[16]: open_spec("كيف", "כיפא للصخر، وكيف العربية للسؤال عن الحال."),
    EXPECTED[17]: open_spec("سبق", "ספק للكفاية، وسبق العربية للتقدم."),
    EXPECTED[18]: positive_spec("زوج", ("الزوج",), "ROOT-TRACE", "זוג وزوج في الاقتران", "GUT-03 يرخص ג ↔ ج؛ الزاي والواو هويتان.", "مباشر في الزوج والاقتران."),
    EXPECTED[19]: positive_spec("عزز", ("العز", "قوي"), "ROOT-TRACE", "עזז وعزز في القوة", "العين والزايان هويات.", "مباشر في العزة والقوة."),
    EXPECTED[20]: open_spec("نحت", "נחת للنزول، ونحت العربية للبري والقطع."),
    EXPECTED[21]: open_spec("فرح", "פרח للطيران، وفرح العربية للسرور."),
    EXPECTED[22]: open_spec("رحق", "רחק للبعد، ورحق العربية لا تثبت هذا المعنى في مروحة مستقلة."),
    EXPECTED[23]: open_spec("قدم", "גדם للقطع، وقدم العربية للتقدم أو القدم."),
    EXPECTED[24]: positive_spec("رمز", ("الإشارة", "رمز"), "ROOT-TRACE", "רמז ورمز في الإشارة", "الراء والميم والزاي هويات.", "مباشر في الرمز والإشارة."),
    EXPECTED[25]: terminal_spec("FUNCTION-WORD", "برم", "العضو أداة استدراك بمعنى لكن."),
    EXPECTED[26]: gap_spec("LAW-GAP", "ضحك", "צחק للضحك، والمقابل العربي ضحك مباشر لكن צ أمام ض غير موقع.", "DENT-08 خاص بظ ولا يمد إلى ض."),
    EXPECTED[27]: positive_spec("نمر", ("النمر",), "ROOT-TRACE", "נמרא ونمر للحيوان نفسه من *namir-", "النون والميم والراء هويات؛ ألف الحالة خارج الجذر.", "مباشر في النمر."),
    EXPECTED[28]: open_spec("سطو", "סתוא للشتاء، وسطو العربية للقهر أو الظهور."),
    EXPECTED[29]: positive_spec("عمق", ("العمق", "عميق"), "ROOT-TRACE", "עמק وعمق في العمق", "العين والميم والقاف هويات.", "مباشر في العمق."),
    EXPECTED[30]: open_spec("جيد", "גידא للعصب، وجيد العربية للعنق أو الحسن."),
    EXPECTED[31]: open_spec("نحل", "נחלא للسيل، ونحل العربية للحشرة أو العطاء."),
    EXPECTED[32]: terminal_spec("LOANWORD", "نبط", "المصدر يسمي الأصل اليوناني ثم الإيراني للنفط."),
    EXPECTED[33]: open_spec("قنت", "גנתא للحديقة، وقنت العربية للطاعة أو الدعاء."),
    EXPECTED[34]: open_spec("نقب", "נקף للالتصاق، ونقب العربية للثقب."),
    EXPECTED[35]: open_spec("فقر", "פגרא للجسد، وفقر العربية للحاجة أو فقار الظهر."),
    EXPECTED[36]: open_spec("كشط", "כשט للرمي والتسديد، وكشط العربية للنزع."),
    EXPECTED[37]: positive_spec("حمم", ("الحميم", "الحر"), "ROOT-TRACE", "חמם وحمم في الحرارة", "الحاء والميمان هويات.", "مباشر في الحرارة."),
    EXPECTED[38]: open_spec("حرج", "חרג لغبار الضوء من فعل الفرك، وحرج العربية للضيق."),
    EXPECTED[39]: open_spec("طلح", "טלח للتوقف، وطلح العربية للشجر أو الإعياء."),
    EXPECTED[40]: positive_spec("وعد", ("الموعد", "الوعد"), "ROOT-TRACE", "ועדא ووعد في الموعد", "الواو والعين والدال هويات؛ ألف الحالة خارج الجذر.", "مباشر في الموعد."),
    EXPECTED[41]: gap_spec("LAW-GAP", "حرق", "שרף للحرق، لكن المقابل العربي المباشر حرق لا يتولد من الصفوف الموقعة.", "لا يستبدل شرب بالحرق لمجرد الهوية الآلية."),
    EXPECTED[42]: open_spec("حلل", "חללא للثقب، وحلل العربية للفك والإباحة."),
    EXPECTED[43]: positive_spec("تجر", ("التجارة", "تاجر"), "ROOT-TRACE", "תגר وتجر في التجارة", "GUT-03 يرخص ג ↔ ج؛ التاء والراء هويتان.", "مباشر في التجارة."),
    EXPECTED[44]: gap_spec("LAW-GAP", "ظفر", "טפרא لظفر الإصبع، لكن DENT-08 يشترط إعادة بناء *ṯ̣ منشورة لهذا العضو.", "لا يستعمل ט ↔ ظ بلا شرط الصف."),
    EXPECTED[45]: open_spec("عيب", "עיבא للسحابة، وعيب العربية للنقص."),
    EXPECTED[46]: open_spec("زين", "זינא للسلاح، وزين العربية للحسن والزينة."),
    EXPECTED[47]: gap_spec("MORPHOLOGY-GAP", "مرر", "מורא للمر، والمر العربي يوافق المادة لكن المولد يعطي مور ولا يثبت الجذر المضعف.", "يلزم تحليل الواو والمضعف قبل الحكم."),
    EXPECTED[48]: open_spec("شمت", "שמט للسحب والإخراج، وشمت العربية للفرح بمصيبة."),
    EXPECTED[49]: positive_spec("عتد", ("أعتد", "العتاد"), "ROOT-TRACE", "עתד وعتد في الإعداد والتهيئة", "العين والتاء والدال هويات.", "مباشر في الإعداد."),
}


def load_base():
    specification = importlib.util.spec_from_file_location(
        "aramaic_source_rich_base", BASE_PATH
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load Aramaic base")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def main() -> int:
    base = load_base()
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        print("Aramaic one-short identity batch 02: already present")
        return 0
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    try:
        selected = []
        for item in report["languages"]["aramaic"]["one_member_short"]:
            row = connection.execute(
                "SELECT entry_id,headword,romanization,pos,gloss,etymology,loan_hint "
                "FROM entries WHERE entry_id=?",
                (item["missing_entry_id"],),
            ).fetchone()
            if row is None or "Arabic" in str(row["etymology"] or ""):
                continue
            identity = connection.execute(
                "SELECT form FROM candidates WHERE entry_id=? AND kind='root' "
                "AND status='licensed' AND rule_ids_json='[]' ORDER BY form",
                (item["missing_entry_id"],),
            ).fetchall()
            if identity:
                selected.append((str(item["family_id"]), dict(row)))
            if len(selected) == 50:
                break
    finally:
        connection.close()
    families = [family for family, _ in selected]
    if families != EXPECTED:
        raise ValueError(f"identity selection drifted: {families}")
    base.SPECS = SPECS
    fan_map = base.fans()
    cards = [
        base.render_card(rank, family, entry, SPECS[family], fan_map)
        for rank, (family, entry) in enumerate(selected, 1)
    ]
    block = "\n".join(
        [
            "",
            MARKER,
            "",
            f"## حملة المقام الآرامية، دفعة المطابقة الذاتية 2 ({DATE}، محلية)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "النطاق هو أول خمسين أسرة، بترتيب قائمة الناقص عضوًا واحدًا الرسمية، لها مرشح جذر مرخص بلا صف إبدال ولم تدخل دفعة الأصل العربي الصريح. قُرئت الخمسون كلها، لا الموجبات وحدها.",
            "",
            *cards,
            "<!-- ARAMAIC-ONE-SHORT-IDENTITY-BATCH-02:END -->",
            "",
        ]
    )
    base.atomic_write(READING, text.rstrip() + "\n" + block)
    positives = sum(item["kind"] == "positive" for item in SPECS.values())
    closures = sum(item["kind"] == "terminal" for item in SPECS.values())
    held = len(SPECS) - positives - closures
    base.atomic_write(
        AUDIT,
        "\n".join(
            [
                "# حملة المقام الآرامية، دفعة المطابقة الذاتية 2 المحلية",
                "",
                "## بيان النطاق",
                "",
                "قُرئت أول خمسين أسرة ناقصة عضوًا واحدًا لها مرشح جذري مطابق ذاتيًا، مع حفظ ترتيب القائمة الرسمية.",
                "",
                "## الرقمان المفصولان",
                "",
                f"- الصلات الموجبة: {positives}.",
                f"- الإغلاقات النهائية: {closures}.",
                "",
                "## الباقي",
                "",
                f"- فجوات أو مرشحات بلا حكم: {held}.",
                "- لا NO-TRACE مصنوع من فجوة.",
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
            {
                "cards": len(SPECS),
                "positive_connections": positives,
                "terminal_closures": closures,
                "held": held,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
