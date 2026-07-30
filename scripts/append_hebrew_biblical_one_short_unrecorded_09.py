#!/usr/bin/env python3
"""Read every biblical one-short Hebrew member still UNRECORDED."""
from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
REPORT = ROOT / "data" / "proof-eligible-families.json"
WITNESSES = ROOT / "data" / "hebrew-temporal-witnesses.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
BASE_PATH = ROOT / "scripts" / "append_hebrew_biblical_priority_batch_01.py"
AUDIT = ROOT / "05-audits" / "2026-07-28-hebrew-biblical-one-short-unrecorded-09-local.md"
MARKER = "<!-- HEBREW-BIBLICAL-ONE-SHORT-UNRECORDED-09 -->"
DATE = "2026-07-28"

EXPECTED = [
    "hebrew:family:02912c1cf41101f2836df6ed",
    "hebrew:family:07506d03428ce29e580c4883",
    "hebrew:family:07ea32397a218f2a4aba6a25",
    "hebrew:family:0e7e4b92ba78e6af64c86ce8",
    "hebrew:family:1321b036f009eb0338e9279f",
    "hebrew:family:14c0e576b3e8fec13f8bac12",
    "hebrew:family:32d76a601129e2faab838c32",
    "hebrew:family:619586dfb60e2e005a00d40b",
    "hebrew:family:6b4e922c41f7aef6396f8960",
    "hebrew:family:a82503cfe12f4d29c4ca40c8",
    "hebrew:family:ae481eb251c668760bd496c8",
    "hebrew:family:ef196a52e14a167bd941ed9c",
]

SPECS = {
    EXPECTED[0]: {
        "kind": "open",
        "state": "OPEN-CANDIDATE",
        "root": "عنق",
        "reason": "ענק للعملاق، وعنق العربية للرقبة؛ لا معنى مباشر في المروحة",
        "sound": "العين والنون والقاف هويات، ولا يحكم الهيكل مع افتراق المعنى.",
        "bridge": "لا جسر مسمى من العنق إلى العملاق.",
    },
    EXPECTED[1]: {
        "kind": "positive",
        "state": "READY",
        "root": "نطر",
        "terms": ("حفظ", "الكرم"),
        "verdict": "ROOT-TRACE",
        "reason": "נטר ونطر في حراسة الكرم",
        "sound": "النون والطاء والراء هويات؛ لا صف لازم.",
        "bridge": "مباشر في الحفظ والحراسة.",
    },
    EXPECTED[2]: {
        "kind": "positive",
        "state": "READY",
        "root": "عقد",
        "terms": ("عقد", "الربط"),
        "verdict": "ROOT-TRACE",
        "reason": "עקד وعقد في ربط الأطراف",
        "sound": "العين والقاف والدال هويات؛ لا صف لازم.",
        "bridge": "مباشر في العقد والربط.",
    },
    EXPECTED[3]: {
        "kind": "positive",
        "state": "READY",
        "root": "بشر",
        "terms": ("البشرة", "الجلد"),
        "verdict": "ROOT-ECHO",
        "reason": "בשר للحم وبشر العربية لظاهر الجلد",
        "sound": "SIB-07 يرخص שׂ العبرية أمام ش العربية؛ الباء والراء هويتان.",
        "bridge": "خطوة عضوية واحدة من اللحم إلى البشرة والجلد.",
    },
    EXPECTED[4]: {
        "kind": "positive",
        "state": "READY",
        "root": "نمر",
        "terms": ("النمر",),
        "verdict": "ROOT-TRACE",
        "reason": "נמר والنمر للحيوان نفسه",
        "sound": "النون والميم والراء هويات؛ لا صف لازم.",
        "bridge": "مباشر في النمر.",
    },
    EXPECTED[5]: {
        "kind": "positive",
        "state": "READY",
        "root": "حجج",
        "terms": ("الحج", "القصد"),
        "verdict": "ROOT-ECHO",
        "reason": "חגג للاحتفال وحج العربية للقصد والشعيرة",
        "sound": "GUT-03 يرخص ג ↔ ج في الرجلين؛ الحاء هوية.",
        "bridge": "الشعيرة المقصودة والاحتفال الديني سلسلة معنى واحدة.",
    },
    EXPECTED[6]: {
        "kind": "positive",
        "state": "READY",
        "root": "برك",
        "terms": ("برك", "البعير"),
        "verdict": "ROOT-TRACE",
        "reason": "ברך وبرك في ثني الركبة والبروك",
        "sound": "الباء والراء والكاف الجذرية هويات؛ احتكاك כ من صرف الفرع.",
        "bridge": "مباشر في الركوع والبروك.",
    },
    EXPECTED[7]: {
        "kind": "positive",
        "state": "READY",
        "root": "عنب",
        "terms": ("العنب",),
        "verdict": "ROOT-TRACE",
        "reason": "ענב والعنب للثمر نفسه",
        "sound": "العين والنون والباء الجذرية هويات؛ احتكاك ב من صرف الفرع.",
        "bridge": "مباشر في العنب.",
    },
    EXPECTED[8]: {
        "kind": "positive",
        "state": "READY",
        "root": "ركب",
        "terms": ("ركب", "الركوب"),
        "verdict": "ROOT-ECHO",
        "reason": "רכב للمركبة وركب العربية لفعل الركوب",
        "sound": "الراء والكاف والباء الجذرية هويات؛ احتكاك ב من صرف الفرع.",
        "bridge": "المركبة آلة الركوب، خطوة اسم آلة واحدة.",
    },
    EXPECTED[9]: {
        "kind": "positive",
        "state": "READY",
        "root": "نفس",
        "terms": ("النفس", "الروح"),
        "verdict": "ROOT-TRACE",
        "reason": "נפש والنفس للروح والذات",
        "sound": "LAB-07 يرخص פ ↔ ف وSIB-01 يرخص ש ↔ س؛ النون هوية.",
        "bridge": "مباشر في النفس والروح.",
    },
    EXPECTED[10]: {
        "kind": "positive",
        "state": "READY",
        "root": "بكر",
        "terms": ("البكر", "الفتي"),
        "verdict": "ROOT-TRACE",
        "reason": "בכר والبكر للصغير السابق في السن أو الولادة",
        "sound": "الباء والكاف والراء الجذرية هويات؛ احتكاك כ من صرف الفرع.",
        "bridge": "مباشر في البكر وصغير الإبل.",
    },
    EXPECTED[11]: {
        "kind": "positive",
        "state": "READY",
        "root": "عقب",
        "terms": ("العقب", "مؤخر القدم"),
        "verdict": "ROOT-TRACE",
        "reason": "עקב والعقب لمؤخر القدم",
        "sound": "العين والقاف والباء الجذرية هويات؛ احتكاك ב من صرف الفرع.",
        "bridge": "مباشر في العقب.",
    },
}


def load_base():
    specification = importlib.util.spec_from_file_location("hebrew_priority_base", BASE_PATH)
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load Hebrew priority base")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def main() -> int:
    base = load_base()
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        print("Hebrew biblical one-short unrecorded 09: already present")
        return 0
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    witness_rows = json.loads(WITNESSES.read_text(encoding="utf-8"))["witnesses"]
    by_entry: dict[str, list[dict[str, object]]] = {}
    for row in witness_rows:
        if row["stratum"] == "biblical":
            by_entry.setdefault(str(row["entry_id"]), []).append(row)
    batch = [
        item
        for item in report["languages"]["hebrew"]["one_member_short"]
        if item["current_state"] == "UNRECORDED"
        and item["missing_entry_id"] in by_entry
    ]
    families = [item["family_id"] for item in batch]
    if families != EXPECTED:
        raise ValueError(f"biblical unrecorded one-short queue drifted: {families}")
    base.SPECS = SPECS
    fans = base.fan_map()
    cards = []
    connection = sqlite3.connect(DB)
    try:
        for rank, item in enumerate(batch, 1):
            entry_id = str(item["missing_entry_id"])
            queued = {
                "family_id": item["family_id"],
                "entry_id": entry_id,
                "headword": item["missing_headword"],
                "biblical_witnesses": [
                    {
                        "entry_id": entry_id,
                        "reference": row["reference"],
                    }
                    for row in by_entry[entry_id]
                ],
            }
            cards.append(
                base.render_card(
                    rank,
                    queued,
                    SPECS[str(item["family_id"])],
                    base.members_for(connection, str(item["family_id"])),
                    base.roots_for(connection, entry_id),
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
            f"## العبريّة التوراتية، الأعضاء غير المسجلة الناقصة واحدًا ({DATE}، محلية)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "النطاق هو جميع الأعضاء الناقصة واحدًا التي بقيت UNRECORDED وتحمل شاهدًا توراتيًا صريحًا. قُرئت الاثنتا عشرة بالترتيب بلا انتقاء.",
            "",
            *cards,
            "<!-- HEBREW-BIBLICAL-ONE-SHORT-UNRECORDED-09:END -->",
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
                "# العبريّة التوراتية، الأعضاء غير المسجلة الناقصة واحدًا",
                "",
                "## النطاق",
                "",
                "جميع الأعضاء UNRECORDED الناقصة واحدًا ذات الشاهد التوراتي الصريح.",
                "",
                "## الرقمان المفصولان",
                "",
                f"- الصلات الموجبة: {positives}.",
                f"- الإغلاقات النهائية: {closures}.",
                "",
                "## الباقي",
                "",
                f"- فجوات صادقة: {held}.",
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
