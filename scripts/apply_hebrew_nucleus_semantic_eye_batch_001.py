#!/usr/bin/env python3
"""Apply the first genuine Hebrew semantic-eye batch, ranks 153 to 177.

Every changed layer receives a structured supersession. The two layers are
read independently in one display. The candidate and gate scans remain
preparation only; this script contains the manually authored semantic notes
that make the batch an eye reading.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "04-cross-linguistic" / "data"
COVERAGE = DATA / "lane_a_coverage.jsonl"
QUEUE = DATA / "lane_a_hebrew_nucleus_eye_family_queue.jsonl"
SCANS = DATA / "lane_a_hebrew_nucleus_eye_candidate_scans.jsonl"
LEDGER = DATA / "lane_a_hebrew_nucleus_semantic_eye_reviews.jsonl"
PROGRESS = DATA / "lane_a_hebrew_nucleus_semantic_eye_progress.json"
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
NUCLEI = ROOT / "data" / "juthoor-core-levels.json"
DATE = "2026-08-01"
FIRST_RANK = 153
LAST_RANK = 177
BATCH_NUMBER = 1
AUDIT = ROOT / "05-audits" / f"lane-a-hebrew-nucleus-semantic-eye-batch-{BATCH_NUMBER:03d}.md"


NOTES = {
    153: "قُرئ معنى المخدر مع النواة الموجبة القديمة `سم` ومادة `سمم`، فبقي الموجب النووي مستقلًا مع بقاء الجذر مفتوحًا.",
    154: "الفعل `עזב` ترك وغاب يلتقي الجذر العربي `عزب` كاملًا في الغيبة والترك. أما النوى المباشرة فلم تحمل هذا المدار استقلالًا؛ وصيغة الجمع المؤنث الماضي لا ترث حكم الأصل.",
    155: "الفعل `עבר` عبر واجتاز يلتقي `عبر` جذرًا كاملًا، ويلتقي استقلالًا النواة `مر` في مادة `مرر`: مر واجتاز. حُفظ الحكمان معًا.",
    156: "فُصلت معاني `עבר`: الماضي ما مر، والجانب أو الطريق موضع العبور، ومدخل الجذر حركة وعبور، أما الاسم العلم فلا يرث. ساند `عبر` طبقة الجذر و`مرر` طبقة النواة كلًا في مداره.",
    157: "العضو رسم ناقص محيل إلى لفظ الجنين؛ لا يحمل معنى العبور في هذا العضو ولا يرث حكم عضو مجاور، فبقي عائق الصرف.",
    158: "الرسم الناقص والصيغة السببية من `עיבר` وحدتان صرفيتان؛ لم يُنقل إليهما حكم `עבר` لمجرد القرابة، وبقيتا مفتوحتين على تحليل الأصل.",
    159: "أصل `הלך` يدل على المشي، لكن الجذر العربي السطحي `هلك` مختلف المدار، والنوى المرخصة المعروضة لا تسمي المشي. فُصلت الصيغ التابعة ولم ترث حكم اللمة.",
    160: "اسم اللغة مقتبس من اليديشية بنص الاشتقاق، فعزلته مصفاة الاتجاه عن الوراثة.",
    161: "صفة اليديشية مرشحة للاشتقاق من الاسم المقترض، لكن بطاقة العضو لا تسجل اشتقاقًا أو اتجاهًا؛ لم يُخترع اتجاه ولم يصدر موجب.",
    162: "الكسكس وصيغته الجمع منقولان في السجل، فبقي الانتقال معزولًا ولم تتحول المشابهة الصوتية إلى وراثة.",
    163: "المركب الذي يعني القيوط وعضو السهب لا يحملان في المرشحات المباشرة مدار الحيوان أو الأرض المنبسطة على نحو مسند؛ بقي كلا العضوين مفتوحًا.",
    164: "اسم الذئب موروث مع قلب صوتي بحسب الاشتقاق، لكن الأداة لم تخرج مرشح جذر كامل مرخص، والنوى المعروضة لا تحمل معنى الذئب. الاسم العلم بقي وحدة أسماء مستقلة.",
    165: "في `המריא` أي أقلع، النواة المباشرة `مر` من أصل اللمة تقابل `مرر`: الدخول في الحركة والمضي. الجسر نووي مستقل، أما الجذر الكامل فبقي مفتوحًا.",
    166: "مرشح `شق` يصف الصدع، وهو أثر محتمل للخطر لا معنى الخطر نفسه؛ رُد الجسر ولم يحول احتمال النتيجة إلى صلة.",
    167: "في صفة الخطورة بقي `شق` أثرًا ممكنًا لا مدارًا للصفة، ولم ترث الصفة حكم الاسم أو تُغلق سلبًا.",
    168: "بطاقة الضفدع تسجل قرابة رباعية مع العربية `ضفدع`، لكن درجة الجذر الثلاثي لا تستوعبها والنوى المعروضة لا تحمل معنى الحيوان؛ بقيت فجوة قانون مفتوحة.",
    169: "معنى الشرغوف لا يلتقي نوى الضم أو الامتداد أو الانتشار المعروضة إلا بعموم بعيد؛ رُد العموم وبقيت الصيغة الجمع تابعة بلا وراثة.",
    170: "مريم اسم علم ذو أصول مقترحة متعارضة في البطاقة؛ عُزل الاسم ولم يرجح اقتراح اشتقاقي بلا دليل.",
    171: "بابل من الأكادية بنص الاشتقاق، فبقي انتقال الاسم معزولًا عن أحكام الوراثة.",
    172: "ليئة اسم علم، وإن ذكرت البطاقة قرابة عربية بمعنى البقرة الوحشية؛ لا يرث الاسم حكم اسم الجنس بلا فصل اشتقاقي حاكم.",
    173: "النعجة تقابل العربية `رخل` اشتقاقيًا، لكن المرشح الجذري المرخص في الأداة هو `رحل` لا `رخل`، ومسار الخاء الكامل غير مرخص هنا؛ والنواة `رخ` تصف الطراوة لا النعجة. بقيت فجوة القانون مفتوحة.",
    174: "قفاز الملاكمة مركب صرفي؛ حضور معنى القبضة في أحد جزأيه لا يجيز توريث حكم الجزء إلى المركب، فبقي عائق الوحدة.",
    175: "القبضة `אגרוף` تلتقي النواة `كف` استقلالًا: الكف والقبض، وتسندها مادة `كفف` من مصدرين. بقي استخراج الجذر `جرف` من الصيغة الاسمية عائقًا منفصلًا.",
    176: "الرسم الناقص لا يرث، أما عضو الملاكمة نفسه فقُرئ مستقلا: الفعل الرياضي قائم على الكف والقبض، فصدر له صدى نووي `كف` بمادة `كفف`.",
    177: "كلب البحر بمعنى الفقمة ترجمة اقتراضية عن الألمانية بنص الاشتقاق؛ عُزل الاتجاه، ولم تحمل نواة أحد جزأي المركب حكم وراثة.",
}


ROOT_SPECS = {
    "kaikki_hebrew:183:en-עזב-he-verb-HD3Wx54V": {
        "outcome": "ROOT-TRACE", "root": "عزب", "positions": ["1-2-3"], "rules": [],
        "reason": "الفرع: ترك وغاب؛ العربية في عزب: الغيبة وترك النكاح، مع تطابق الجذر الكامل.",
    },
    "kaikki_hebrew:184:en-עבר-he-verb-KfvU0Xzc": {
        "outcome": "ROOT-TRACE", "root": "عبر", "positions": ["1-2-3"], "rules": [],
        "reason": "الفرع: عبر واجتاز؛ العربية عبر: جاز من جانب إلى جانب، بتطابق كامل.",
    },
    "kaikki_hebrew:185:en-עבר-he-noun-7eYmMBm6": {
        "outcome": "ROOT-ECHO", "root": "عبر", "positions": ["1-2-3"], "rules": [],
        "reason": "الماضي هو الزمن الذي عبر ومضى؛ صدى نتيجة زمنية من مدار العبور الكامل.",
    },
    "kaikki_hebrew:13233:en-ע־ב־ר-he-root-SWY7XD4b": {
        "outcome": "ROOT-TRACE", "root": "عبر", "positions": ["1-2-3"], "rules": [],
        "reason": "مدخل الجذر يصرح بالحركة والعبور، وهو مدار العربية عبر نفسه.",
    },
}


NUCLEUS_SPECS = {
    "kaikki_hebrew:184:en-עבר-he-verb-KfvU0Xzc": {
        "outcome": "NUCLEUS-TRACE", "nucleus": "مر", "witness": "مرر", "positions": ["2-3"], "rules": ["LAB-04"],
        "reason": "الفرع عبر واجتاز؛ العربية مر واجتاز؛ النواة مر هي الاسترسال والحركة.",
    },
    "kaikki_hebrew:185:en-עבר-he-noun-7eYmMBm6": {
        "outcome": "NUCLEUS-ECHO", "nucleus": "مر", "witness": "مرر", "positions": ["2-3"], "rules": ["LAB-04"],
        "reason": "الماضي ما مر؛ العربية تقول مر الدهر، فالعلاقة صدى حالة زمنية.",
    },
    "kaikki_hebrew:186:en-עבר-he-noun-INRAT-74": {
        "outcome": "NUCLEUS-ECHO", "nucleus": "مر", "witness": "مرر", "positions": ["2-3"], "rules": ["LAB-04"],
        "reason": "الطريق والجهة موضع المرور؛ صدى موضع من مدار مرر.",
    },
    "kaikki_hebrew:13233:en-ע־ב־ר-he-root-SWY7XD4b": {
        "outcome": "NUCLEUS-TRACE", "nucleus": "مر", "witness": "مرر", "positions": ["2-3"], "rules": ["LAB-04"],
        "reason": "مدخل الجذر يصرح بالحركة والعبور، والنواة مر تحقق الحركة والاجتياز.",
    },
    "kaikki_hebrew:199:en-המריא-he-verb-nyvHEIzE": {
        "outcome": "NUCLEUS-ECHO", "nucleus": "مر", "witness": "مرر", "positions": ["2-3"], "rules": [],
        "reason": "الإقلاع مفارقة السكون والدخول في المضي؛ صدى فعل من مدار مرر.",
    },
    "kaikki_hebrew:210:en-אגרוף-he-noun-kfSVmKw6": {
        "outcome": "NUCLEUS-ECHO", "nucleus": "كف", "witness": "كفف", "positions": ["2-5"], "rules": [],
        "reason": "القبضة هيئة اليد حين تكف وتنقبض؛ صدى نتيجة من مدار كفف.",
    },
    "kaikki_hebrew:8443:en-איגרוף-he-noun-caQuUS6m": {
        "outcome": "NUCLEUS-ECHO", "nucleus": "كف", "witness": "كفف", "positions": ["3-6"], "rules": [],
        "reason": "الملاكمة فعل بالكف المقبوضة؛ صدى فعل وآلة من مدار كفف.",
    },
}


OPEN_CHANGES = {
    ("kaikki_hebrew:183:en-עזב-he-verb-HD3Wx54V", "nucleus"): {
        "expected": "MORPHOLOGY-GAP", "new": "OPEN-CANDIDATE",
        "reason": "العضو لمة سطحية جاهزة لا صيغة إحالية؛ قُرئت نواته استقلالًا ولم يكتمل جسر نووي، فبقي مفتوحًا.",
    },
    ("kaikki_hebrew:190:en-הלך-he-verb-7QCjBabB", "root"): {
        "expected": "MORPHOLOGY-GAP", "new": "OPEN-CANDIDATE",
        "reason": "العضو لمة سطحية جاهزة؛ فُحص هلك العربي فخالف معنى المشي، فلا يبقى عائق صرف ولا يصدر موجب أو سالب.",
    },
    ("kaikki_hebrew:190:en-הלך-he-verb-7QCjBabB", "nucleus"): {
        "expected": "MORPHOLOGY-GAP", "new": "OPEN-CANDIDATE",
        "reason": "العضو لمة سطحية جاهزة؛ النوى المرخصة لم تحمل مدار المشي، فبقيت طبقة النواة مفتوحة بعد القراءة.",
    },
}


DIRECTION_SPEC = {
    "member_id": "kaikki_hebrew:212:en-כלב_ים-he-noun-iwM1fQwJ",
    "class": "THIRD-PARTY-TO-BRANCH",
    "reason": "بطاقة الاشتقاق تسمي اللفظ ترجمة اقتراضية من الألمانية Seehund؛ لا شهادة وراثية مستقلة.",
}
DIRECTION_SPECS = [DIRECTION_SPEC]


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def atomic_write(path: Path, text: str) -> None:
    descriptor, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        temporary.write_text(nfc(text), encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def fan_module() -> Any:
    path = ROOT / "scripts" / "search_arabic_root_senses.py"
    spec = importlib.util.spec_from_file_location("semantic_eye_fan", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load Arabic fan reader")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def readings() -> dict[str, str]:
    data = json.loads(NUCLEI.read_text(encoding="utf-8"))
    return {
        item["nucleus"]: item.get("jabal_lexicon_reading_ar") or ""
        for item in data["levels"]["level_2_binary_nuclei"]["nuclei"]
    }


def supersede(row: dict[str, Any], layer: str, previous: Any, new: Any, reason: str) -> None:
    row.setdefault("judgment_supersessions", []).append(
        {
            "schema": "lane-a-judgment-supersession-v1",
            "date": DATE,
            "member_id": row["member_id"],
            "layer": layer,
            "previous_outcome": previous,
            "new_outcome": new,
            "reason": reason,
            "evidence": f"05-audits/lane-a-hebrew-nucleus-semantic-eye-batch-{BATCH_NUMBER:03d}.md",
        }
    )


def candidate_ready(connection: sqlite3.Connection, member: str, kind: str, form: str, positions: list[str], rules: list[str]) -> None:
    rows = connection.execute(
        """SELECT positions_json, rule_ids_json FROM candidates
           WHERE entry_id=? AND kind=? AND form=? AND status='licensed' AND route_flag=0""",
        (member, kind, form),
    ).fetchall()
    wanted = (positions, rules)
    if wanted not in [(json.loads(p), json.loads(r)) for p, r in rows]:
        raise RuntimeError(f"candidate gate failed: {member} {kind} {form}")


def main() -> int:
    existing_reviews = load_jsonl(LEDGER) if LEDGER.exists() else []
    existing_ranks = [int(row["rank"]) for row in existing_reviews]
    if existing_ranks != list(range(153, FIRST_RANK)):
        raise RuntimeError("semantic eye ledger is not the expected contiguous prefix")
    progress = json.loads(PROGRESS.read_text(encoding="utf-8"))
    if progress["families_eye_read"] != FIRST_RANK - 1 or progress["next_rank"] != FIRST_RANK:
        raise RuntimeError("semantic eye progress is not at the expected prior rank")

    queue = {row["rank"]: row for row in load_jsonl(QUEUE) if FIRST_RANK <= row["rank"] <= LAST_RANK}
    if set(queue) != set(range(FIRST_RANK, LAST_RANK + 1)):
        raise RuntimeError("queue slice is incomplete")
    scan_by_rank: dict[int, dict[str, Any]] = {}
    with SCANS.open(encoding="utf-8") as handle:
        for line in handle:
            scan = json.loads(line)
            if FIRST_RANK <= scan["rank"] <= LAST_RANK:
                scan_by_rank[scan["rank"]] = scan
            if scan["rank"] > LAST_RANK:
                break
    if set(scan_by_rank) != set(queue):
        raise RuntimeError("candidate scan slice is incomplete")

    raw = COVERAGE.read_text(encoding="utf-8").splitlines()
    coverage = [json.loads(line) for line in raw if line.strip()]
    by_member = {row["member_id"]: row for row in coverage}
    index = {row["member_id"]: number for number, row in enumerate(coverage)}
    batch_members = {member for family in queue.values() for member in family["member_ids"]}
    direction_members = {spec["member_id"] for spec in DIRECTION_SPECS}
    if not (set(ROOT_SPECS) | set(NUCLEUS_SPECS) | {key[0] for key in OPEN_CHANGES} | direction_members) <= batch_members:
        raise RuntimeError("a change target lies outside the batch")

    connection = sqlite3.connect(DB)
    module = fan_module()
    witnesses = {spec["root"] for spec in ROOT_SPECS.values()} | {spec["witness"] for spec in NUCLEUS_SPECS.values()}
    matches = module.matches_for_roots(module.DEFAULT_RESOURCES, witnesses, None)
    fans = {root: module.independent_fan(matches[root], 2) for root in witnesses}
    for root, fan in fans.items():
        if not fan["judgment_ready"]:
            raise RuntimeError(f"Arabic fan is not judgment ready: {root}")
    frozen = readings()
    changes: list[dict[str, Any]] = []

    for member, spec in ROOT_SPECS.items():
        row = by_member[member]
        layer = row["root_layer"]
        previous = layer["outcome"]
        candidate_ready(connection, member, "root", spec["root"], spec["positions"], spec["rules"])
        sources = [item["source_label"] for item in fans[spec["root"]]["selected_sources"]]
        supersede(row, "root", previous, spec["outcome"], spec["reason"])
        row["root_layer"] = {
            "outcome": spec["outcome"],
            "issued": True,
            "basis": "حكم جذري من العين الدلالية العضوية، مستقل عن حكم النواة.",
            "selected": {
                "arabic_root": spec["root"], "positions": spec["positions"], "rule_ids": spec["rules"],
                "status": "licensed", "route_required": False, "old_arabic_sources": sources,
                "semantic_bridge": spec["reason"], "comparison_mode": "parallel-independent",
            },
        }
        changes.append({"member_id": member, "layer": "root", "previous": previous, "new": spec["outcome"], "reason": spec["reason"]})

    for member, spec in NUCLEUS_SPECS.items():
        row = by_member[member]
        layer = row["nucleus_layer"]
        previous = layer["outcome"]
        candidate_ready(connection, member, "nucleus", spec["nucleus"], spec["positions"], spec["rules"])
        sources = [item["source_label"] for item in fans[spec["witness"]]["selected_sources"]]
        supersede(row, "nucleus", previous, spec["outcome"], spec["reason"])
        old_retrieval = {key: value for key, value in layer.items() if key not in {"outcome", "issued", "basis", "selected"}}
        row["nucleus_layer"] = {
            "outcome": spec["outcome"], "issued": True,
            "basis": "حكم نووي من العين الدلالية العضوية، مستقل عن حكم الجذر.",
            "selected": {
                "nucleus": spec["nucleus"], "reading_ar": frozen[spec["nucleus"]], "status": "licensed",
                "positions": spec["positions"], "rule_ids": spec["rules"], "route_required": False,
                "arabic_root_witness": spec["witness"], "old_arabic_sources": sources,
                "semantic_bridge": spec["reason"], "comparison_mode": "parallel-independent",
                "direction_rule_six": "اجتاز: شاهد عربي قديم مستقل بمصدرين، ولا اتجاه نقل في العضو.",
            },
            **old_retrieval,
        }
        changes.append({"member_id": member, "layer": "nucleus", "previous": previous, "new": spec["outcome"], "reason": spec["reason"]})

    for (member, layer_name), spec in OPEN_CHANGES.items():
        row = by_member[member]
        key = f"{layer_name}_layer"
        layer = row[key]
        if layer["outcome"] != spec["expected"]:
            raise RuntimeError(f"unexpected open-change outcome: {member} {layer_name}")
        supersede(row, layer_name, spec["expected"], spec["new"], spec["reason"])
        layer["outcome"] = spec["new"]
        layer["issued"] = False
        layer["basis"] = spec["reason"]
        layer["selected"] = None
        changes.append({"member_id": member, "layer": layer_name, "previous": spec["expected"], "new": spec["new"], "reason": spec["reason"]})

    for direction_spec in DIRECTION_SPECS:
        direction_member = direction_spec["member_id"]
        row = by_member[direction_member]
        previous_direction = row.get("direction_class")
        supersede(row, "direction", previous_direction, direction_spec["class"], direction_spec["reason"])
        row["direction_class"] = direction_spec["class"]
        row["direction_evidence"] = direction_spec["reason"]
        changes.append({"member_id": direction_member, "layer": "direction", "previous": previous_direction, "new": direction_spec["class"], "reason": direction_spec["reason"]})
        for layer_name in ("root", "nucleus"):
            layer = row[f"{layer_name}_layer"]
            previous = layer["outcome"]
            supersede(row, layer_name, previous, direction_spec["class"], direction_spec["reason"])
            layer["outcome"] = direction_spec["class"]
            layer["issued"] = False
            layer["basis"] = direction_spec["reason"]
            layer["selected"] = None
            changes.append({"member_id": direction_member, "layer": layer_name, "previous": previous, "new": direction_spec["class"], "reason": direction_spec["reason"]})
    connection.close()

    review_rows: list[dict[str, Any]] = []
    change_by_member: dict[str, list[dict[str, Any]]] = {}
    for change in changes:
        change_by_member.setdefault(change["member_id"], []).append(change)
    db = sqlite3.connect(DB)
    for rank in range(FIRST_RANK, LAST_RANK + 1):
        family = queue[rank]
        scan = scan_by_rank[rank]
        members = []
        for member_id in family["member_ids"]:
            item = by_member[member_id]
            etymology = db.execute("SELECT etymology FROM entries WHERE entry_id=?", (member_id,)).fetchone()[0]
            members.append(
                {
                    "member_id": member_id, "orthography": item.get("orthography") or "",
                    "pos": item.get("pos") or "", "branch_meaning": item.get("branch_meaning") or "",
                    "etymology_read": etymology, "root_outcome_after_eye": item["root_layer"]["outcome"],
                    "nucleus_outcome_after_eye": item["nucleus_layer"]["outcome"],
                    "direction_class_after_eye": item.get("direction_class"),
                    "judgment_changes": change_by_member.get(member_id, []),
                }
            )
        review_rows.append(
            {
                "schema": "lane-a-hebrew-nucleus-semantic-eye-review-v1", "date": DATE,
                "batch_number": BATCH_NUMBER, "rank": rank, "family_id": family["family_id"],
                "member_ids": family["member_ids"], "comparison_mode": "parallel-independent",
                "root_and_nucleus_read_in_one_display": True, "semantic_eye_note": NOTES[rank],
                "candidate_scope": "complete licensed non-route universe in candidate scan ledger",
                "candidate_form_count": sum(member["licensed_nonroute_candidate_form_count"] for member in scan["members"]),
                "members": members, "coverage_rows_retained": family["member_ids"],
            }
        )
    db.close()

    for member_id, row in by_member.items():
        coverage[index[member_id]] = row
    identities = [row["member_id"] for row in coverage]
    if len(identities) != len(set(identities)):
        raise RuntimeError("coverage identity invariant failed")
    atomic_write(COVERAGE, "\n".join(json.dumps(row, ensure_ascii=False) for row in coverage) + "\n")
    all_reviews = existing_reviews + review_rows
    atomic_write(LEDGER, "\n".join(json.dumps(row, ensure_ascii=False) for row in all_reviews) + "\n")

    progress.update({"families_eye_read": LAST_RANK, "families_remaining": 11852 - LAST_RANK, "last_rank": LAST_RANK, "next_rank": LAST_RANK + 1})
    atomic_write(PROGRESS, json.dumps(progress, ensure_ascii=False, indent=2) + "\n")

    outcomes = Counter(change["new"] for change in changes)
    cards = []
    for change in changes:
        cards.append(
            f"- العضو `{change['member_id']}`، الطبقة={change['layer']}، السابق={change['previous']}، "
            f"الجديد={change['new']}، السبب: {change['reason']}"
        )
    report = (
        f"# العبرية بعين النواة الدلالية، الدفعة {BATCH_NUMBER:03d}\n\n"
        f"- التاريخ: {DATE}.\n"
        f"- النطاق: الرتب {FIRST_RANK} إلى {LAST_RANK}؛ 25 أسرة و"
        f"{sum(len(row['member_ids']) for row in review_rows)} عضوًا.\n"
        "- الجذر والنواة فُحصا استقلالًا في عرض واحد لكل عضو.\n"
        f"- تغييرات الحكم المسجلة={len(changes)}؛ الأحكام الجذرية الموجبة الجديدة={len(ROOT_SPECS)}؛ "
        f"الأحكام النووية الموجبة الجديدة={len(NUCLEUS_SPECS)}.\n"
        f"- مصائر التغيير: {json.dumps(dict(outcomes), ensure_ascii=False, sort_keys=True)}.\n"
        "- كل تغيير أدناه له سجل نسخ منظم في صف العضو، ولم يحذف أي معرّف من التغطية.\n\n"
        "## سطور النسخ\n\n" + "\n".join(cards) + "\n\n"
        "## محاضر الأسر\n\n" + "\n".join(f"- الرتبة {rank}: {NOTES[rank]}" for rank in range(FIRST_RANK, LAST_RANK + 1)) + "\n\n"
        f"- التقدم الحاكم بعد الدفعة: {LAST_RANK}/11,852؛ المتبقي={11852 - LAST_RANK}.\n"
        "- لم تُستعمل أوامر Git ولا خدمة مشتركة.\n"
    )
    if AUDIT.exists():
        raise RuntimeError("batch audit already exists")
    atomic_write(AUDIT, report)
    marker = f"HEBREW-NUCLEUS-SEMANTIC-EYE-BATCH-{BATCH_NUMBER:03d}"
    body = READING.read_text(encoding="utf-8")
    if f"<!-- {marker}:BEGIN -->" in body:
        raise RuntimeError("reading batch marker already exists")
    block = f"\n\n<!-- {marker}:BEGIN -->\n\n{report}\n<!-- {marker}:END -->\n"
    atomic_write(READING, body.rstrip() + block)
    print(json.dumps({"families": len(review_rows), "members": sum(len(row["member_ids"]) for row in review_rows), "changes": len(changes), "root_positive_new": len(ROOT_SPECS), "nucleus_positive_new": len(NUCLEUS_SPECS), "progress": LAST_RANK}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
