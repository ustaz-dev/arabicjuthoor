#!/usr/bin/env python3
"""Read every UNRECORDED Aramaic member on the official one-short list."""
from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
REPORT = ROOT / "data" / "proof-eligible-families.json"
POPULATION = ROOT / "data" / "proof-family-population.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
BASE_PATH = ROOT / "scripts" / "append_aramaic_one_short_source_rich_batch_01.py"
AUDIT = (
    ROOT
    / "05-audits"
    / "2026-07-28-aramaic-one-short-unrecorded-batch-04-local.md"
)
DATE = "2026-07-28"
MARKER = "<!-- ARAMAIC-ONE-SHORT-UNRECORDED-BATCH-04 -->"


def load_base():
    specification = importlib.util.spec_from_file_location(
        "aramaic_source_base", BASE_PATH
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load Aramaic source base")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


base = load_base()

SPECS = {
    "aramaic:family:04a9002f976e7eb15bfdef3b": base.gap(
        "OPEN-CANDIDATE", "سوم",
        "סום للوضع والجعل، وسوم العربية للمساومة أو الرعي؛ لا جسر مباشر.",
        "SIB-01 يرخص ס ↔ س؛ الواو والميم هويتان.",
        "لا جسر دلالي مباشر.",
    ),
    "aramaic:family:6e24bcffb99d468ad96df254": base.positive(
        "حصد",
        ("حصد", "الزرع"),
        "ROOT-TRACE",
        "חצד وحصد في قطع الزرع وجمعه",
        "الحاء والصاد والدال هويات تاريخية؛ لا صف إبدال لازم.",
        "مباشر في الحصاد.",
    ),
    "aramaic:family:71dddf17a0724233ff4f9ff4": base.gap(
        "OPEN-CANDIDATE", "نصب",
        "נסב للأخذ والتلقي، ونصب العربية للإقامة أو التعب؛ لا معنى مباشر.",
        "النون والصاد والباء هويات تاريخية؛ لا يكفي الصوت.",
        "لا جسر دلالي مباشر.",
    ),
    "aramaic:family:80f5600222f00dd2427732df": base.positive(
        "كتب",
        ("الكتاب", "الكتابة"),
        "ROOT-TRACE",
        "כתבא وكتب في الكتاب والكتابة",
        "الكاف والتاء والباء هويات، وألف الحالة خارج الجذر.",
        "مباشر في الكتاب والكتابة.",
    ),
}


def main() -> int:
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        print("Aramaic one-short unrecorded batch 04: already present")
        return 0
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    one_short = {
        item["family_id"]: item
        for item in report["languages"]["aramaic"]["one_member_short"]
        if item["current_state"] == "UNRECORDED"
    }
    if set(one_short) != set(SPECS):
        raise ValueError(f"UNRECORDED one-short drift: {sorted(one_short)}")
    population = json.loads(POPULATION.read_text(encoding="utf-8"))
    families = {
        item["family_id"]: item
        for item in population["languages"]["aramaic"]["families"]
    }
    base.SPECS = SPECS
    fan_map = base.fans()
    selected = []
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    try:
        for family_id, item in one_short.items():
            entry_id = item["missing_entry_id"]
            row = connection.execute(
                "SELECT entry_id,headword,romanization,pos,gloss,etymology,"
                "loan_hint FROM entries WHERE entry_id=?",
                (entry_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"missing inventory entry: {entry_id}")
            if families[family_id]["member_count"] < 1:
                raise ValueError(f"empty family: {family_id}")
            selected.append((family_id, dict(row)))
    finally:
        connection.close()
    cards = [
        base.render_card(rank, family_id, entry, SPECS[family_id], fan_map)
        for rank, (family_id, entry) in enumerate(selected, 1)
    ]
    block = "\n".join(
        [
            "",
            MARKER,
            "",
            f"## حملة المقام الآرامية، كنس غير المسجل ({DATE}، محلي)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "النطاق هو كل أعضاء الأسر الناقصة واحدًا التي أعاد العداد حالتها UNRECORDED، وعددها أربعة. دخلت الأربعة بلا انتقاء.",
            "",
            *cards,
            "<!-- ARAMAIC-ONE-SHORT-UNRECORDED-BATCH-04:END -->",
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
                "# حملة المقام الآرامية، كنس غير المسجل",
                "",
                "## النطاق",
                "",
                "قُرئ كل عضو UNRECORDED في قائمة الأسر الناقصة واحدًا، وعددها أربعة.",
                "",
                "## الرقمان المفصولان",
                "",
                f"- الصلات الموجبة: {positives}.",
                f"- الإغلاقات النهائية: {closures}.",
                "",
                "## الباقي",
                "",
                f"- مرشحات مفتوحة بلا حكم: {held}.",
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
