#!/usr/bin/env python3
"""Apply one rank window of the old-Arabic fan campaign to Egyptian cards.

This is a judgment-producing local pass.  It promotes only a small, named set
whose branch sense, source citation, sound route, and two-source Arabic fan
have been checked explicitly.  The rest are not left behind as TOOL-GAP:
terminal names, grammar, and named loan routes are closed, while unresolved
cards receive the actual remaining SOURCE/LAW/OPEN blocker.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path

from search_arabic_root_senses import (
    ARABIC_MARKS,
    DEFAULT_RESOURCES,
    root_sense_fan,
)


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "egyptian.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
COMPLETENESS = ROOT / "data" / "arabic-root-lexicon-completeness.json"
DATE = "2026-07-25"
SECTION = re.compile(r"(?=^### )", re.MULTILINE)
RANK_HEADING = re.compile(
    r"^### بطاقة: `(?P<family>egyptian:family:[0-9a-f]+)`، "
    r".+? \(الرتبة (?P<rank>\d+)\)$"
)
BLOCKER = re.compile(r"^-\s*عائق:\s*.+$", re.MULTILINE)
CLOSURE = re.compile(r"^-\s*حالةُ الإغلاق:\s*.+$", re.MULTILINE)
VERDICT = re.compile(r"^-\s*الحكم \(استكشاف\):\s*.+$", re.MULTILINE)
POSITIVE_VERDICTS = {
    "ROOT-TRACE",
    "ROOT-ECHO",
    "NUCLEUS-TRACE",
    "NUCLEUS-ECHO",
}
TERMINAL_STATES = {
    "PROPER-NAME-ISOLATED",
    "NONLEXICAL-ISOLATED",
    "INTRA-HOUSE-TRANSFER",
    "LOANWORD",
}


# family: root, verdict, required terms in each old Arabic witness, scope note,
# and whether the root must be present among the generated licensed candidates.
POSITIVES = {
    "egyptian:family:60358698d60dfcff158b8e67": (
        "ثني",
        "NUCLEUS-ECHO",
        ("اثنان",),
        "sn.w «اثنان» وحده؛ الصف المقيد BR-EGYP-03 والتثليث القبطي المنشور",
        False,
    ),
    "egyptian:family:4d68ec8f384d1affcda8883d": (
        "حسب",
        "ROOT-TRACE",
        ("حساب",),
        "ḥsb «يعد ويحسب» وسلسلة الحساب وحدهما",
        True,
    ),
    "egyptian:family:cb142b8fc3d4d0fe5f534e01": (
        "مطر",
        "ROOT-ECHO",
        ("ماء السحاب",),
        "mtr «الفيضان» وحده؛ الماء المنسكب مباشر والمعنى أوسع من المطر",
        True,
    ),
    "egyptian:family:138f129fa7fdbdf06a90bbb2": (
        "سمر",
        "ROOT-TRACE",
        ("سمير",),
        "smr «الصديق والرفيق» وحده؛ الحيوان المتجانس منقوض",
        True,
    ),
    "egyptian:family:e6a61a43c9f76d081bde2d39": (
        "فرج",
        "ROOT-TRACE",
        ("الخلل",),
        "brg «ينفتح» وحده؛ معنى السعادة المقترض لا يرث الحكم",
        True,
    ),
    "egyptian:family:17e25d8f46e992b867625121": (
        "بسق",
        "ROOT-TRACE",
        ("البساق",),
        "psg «يبصق، بصاق» وسلسلته الاسمية وحدها",
        True,
    ),
    "egyptian:family:81f10caccd753df540b16970": (
        "خسف",
        "ROOT-TRACE",
        ("الذل",),
        "ḫsf «يعاقب ويذل» في المدخل AED 854535 وحده",
        True,
    ),
    "egyptian:family:5dd5579c7325050d2bdfb292": (
        "ختم",
        "ROOT-TRACE",
        ("ختم",),
        "ḫtm «الختم وأداة الختم» وحده",
        True,
    ),
    "egyptian:family:db878cdd7f23d8d5fd6d2f9b": (
        "ختم",
        "ROOT-TRACE",
        ("ختم",),
        "ḫtm «يختم ويغلق» وحده",
        True,
    ),
    "egyptian:family:b80d448d2bd6327cc97e366a": (
        "نفخ",
        "NUCLEUS-TRACE",
        ("أخرج منه الريح",),
        "nfi̯ «ينفخ ويتنفس» على النواة نف؛ الخاء العربية شاهد المروحة لا صامت مصري",
        False,
    ),
    "egyptian:family:e1b5e8d90f126e506579b392": (
        "حطم",
        "ROOT-TRACE",
        ("الكسر",),
        "ḥtm «يدمر» وحده؛ لا يخلط بالمصرية ḫtm «يختم»",
        True,
    ),
    "egyptian:family:1a62030c25bfc0fe96bce0d6": (
        "فتت",
        "ROOT-TRACE",
        ("الفت",),
        "ftt «يمحو ويفتت أثر الكتابة» وحده",
        True,
    ),
    "egyptian:family:0ce06a2bd1ce74de485c4969": (
        "موت",
        "ROOT-TRACE",
        ("الموت",),
        "mwt «الميت» وحده",
        True,
    ),
    "egyptian:family:76a8078a6d23db0cb95d690d": (
        "موت",
        "ROOT-TRACE",
        ("الموت",),
        "mwt «يموت ويكون ميتا» وحده",
        True,
    ),
}


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(unicodedata.normalize("NFC", text))
        temporary = Path(handle.name)
    temporary.replace(path)


def fold(value: str) -> str:
    value = ARABIC_MARKS.sub("", unicodedata.normalize("NFKC", value))
    return value.translate(str.maketrans("أإآؤئ", "اااوي"))


def replace_one(
    section: str, pattern: re.Pattern[str], replacement: str
) -> tuple[str, str]:
    match = pattern.search(section)
    if not match:
        raise ValueError(f"missing required field: {pattern.pattern}")
    old = match.group(0)
    section = section[: match.start()] + replacement + section[match.end() :]
    return section, old


def family_rows(
    connection: sqlite3.Connection, family: str
) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT e.entry_id,e.headword,e.pos,e.gloss,e.etymology,e.loan_hint,
               e.form_of
        FROM family_members fm
        JOIN entries e ON e.entry_id=fm.entry_id
        WHERE fm.family_id=?
        ORDER BY e.entry_id
        """,
        (family,),
    )
    return [
        {
            "entry_id": row[0],
            "headword": row[1],
            "pos": row[2],
            "gloss": row[3],
            "etymology": row[4],
            "loan_hint": bool(row[5]),
            "form_of": bool(row[6]),
        }
        for row in rows
    ]


def candidates(
    connection: sqlite3.Connection, family: str
) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT DISTINCT c.kind,c.form,c.status,c.rule_ids_json,c.route_flag
        FROM family_members fm
        JOIN candidates c ON c.entry_id=fm.entry_id
        WHERE fm.family_id=? AND c.kind IN ('root','hollow-root')
        ORDER BY c.kind,c.status,c.form,c.rule_ids_json
        """,
        (family,),
    )
    return [
        {
            "kind": row[0],
            "form": row[1],
            "status": row[2],
            "rules": json.loads(row[3]),
            "route_required": bool(row[4]),
        }
        for row in rows
    ]


def source_anchor(rows: list[dict[str, object]]) -> str:
    anchors = [
        str(row["etymology"]).strip()
        for row in rows
        if str(row["etymology"]).strip()
    ]
    return anchors[0] if anchors else ""


def positive_decision(
    family: str,
    rows: list[dict[str, object]],
    generated: list[dict[str, object]],
) -> dict[str, object] | None:
    specification = POSITIVES.get(family)
    if not specification:
        return None
    root, verdict, terms, scope, require_generated = specification
    fan = root_sense_fan(DEFAULT_RESOURCES, root, None)["independent_fan"]
    selected = fan["selected_sources"]
    if not fan["judgment_ready"] or len(selected) < 2:
        raise ValueError(f"{family}: incomplete two-source fan for {root}")
    for witness in selected:
        definition = fold(str(witness["definition"]))
        if not any(fold(term) in definition for term in terms):
            raise ValueError(
                f"{family}: named sense absent from {witness['source_label']}"
            )
    licensed = [
        item
        for item in generated
        if item["form"] == root
        and item["status"] in {"licensed", "manual-condition"}
    ]
    if require_generated and not licensed:
        raise ValueError(f"{family}: positive root {root} is not licensed")
    anchor = source_anchor(rows)
    if "Wb " not in anchor and "TLA" not in anchor:
        raise ValueError(f"{family}: positive lacks individual Wb/TLA anchor")
    minimal_rules = min(
        (list(item["rules"]) for item in licensed),
        key=lambda value: (len(value), value),
        default=[],
    )
    return {
        "state": "READY",
        "released": True,
        "positive": True,
        "closure": False,
        "verdict": verdict,
        "root": root,
        "terms": list(terms),
        "scope": scope,
        "sources": [item["source_label"] for item in selected],
        "source_anchor": anchor,
        "sound_rules": minimal_rules,
    }


def terminal_decision(rows: list[dict[str, object]]) -> dict[str, object] | None:
    if not rows:
        raise ValueError("family has no members")
    proper_types = (
        "entity_name: person_name",
        "entity_name: place_name",
        "entity_name: gods_name",
        "entity_name: kings_name",
        "entity_name: org_name",
    )
    if all(str(row["pos"]).startswith(proper_types) for row in rows):
        return {
            "state": "PROPER-NAME-ISOLATED",
            "released": True,
            "positive": False,
            "closure": True,
            "verdict": "غير صادر",
            "note": "كل أعضاء الأسرة أعلام مسماة؛ عزلت من الحكم المعجمي",
        }
    grammar_types = (
        "pronoun",
        "particle",
        "preposition",
        "conjunction",
        "interjection",
    )
    if all(str(row["pos"]).startswith(grammar_types) for row in rows):
        return {
            "state": "NONLEXICAL-ISOLATED",
            "released": True,
            "positive": False,
            "closure": True,
            "verdict": "غير صادر",
            "note": "كل أعضاء الأسرة أدوات أو ضمائر؛ عزلت بلا حكم نسب",
        }
    if all(bool(row["loan_hint"]) for row in rows):
        evidence = " | ".join(
            str(row["gloss"]) + " " + str(row["etymology"]) for row in rows
        )
        state = (
            "INTRA-HOUSE-TRANSFER"
            if "Sem. loan word" in evidence or "Hoch, Sem. Words" in evidence
            else "LOANWORD"
        )
        return {
            "state": state,
            "released": True,
            "positive": False,
            "closure": True,
            "verdict": "LOANWORD" if state == "LOANWORD" else "غير صادر",
            "note": (
                "كل الأعضاء موسومة بانتقال سامي داخل البيت؛ لا تعد شاهد فرع مستقل"
                if state == "INTRA-HOUSE-TRANSFER"
                else "كل الأعضاء ذات مانح أجنبي مسمى؛ عزلت عن حكم النسب"
            ),
        }
    return None


def held_decision(
    rows: list[dict[str, object]],
    generated: list[dict[str, object]],
    complete_roots: set[str],
) -> dict[str, object]:
    if any(bool(row["loan_hint"]) for row in rows):
        return {
            "state": "SOURCE-GAP",
            "released": False,
            "positive": False,
            "closure": False,
            "verdict": "غير صادر",
            "note": "تفصل أعضاء القرض ويثبت اتجاه كل انتقال من الإحالة الفردية",
        }
    anchor = source_anchor(rows)
    if not anchor or not any(
        name in " ".join(str(row["etymology"]) for row in rows)
        for name in ("Wb ", "TLA", "KoptHWb", "FCD ", "Hoch,")
    ):
        return {
            "state": "SOURCE-GAP",
            "released": False,
            "positive": False,
            "closure": False,
            "verdict": "غير صادر",
            "note": "يثبت إسناد مصري فردي منشور قبل الحكم",
        }
    licensed = [
        item
        for item in generated
        if item["status"] in {"licensed", "manual-condition"}
    ]
    if not licensed and any(item["status"] == "scope-gap" for item in generated):
        return {
            "state": "LAW-GAP",
            "released": False,
            "positive": False,
            "closure": False,
            "verdict": "غير صادر",
            "note": "لا مرشح جذري نافذ خارج صفوف النطاق المعلقة",
        }
    ready_roots = sorted(
        {str(item["form"]) for item in licensed} & complete_roots
    )
    if ready_roots:
        return {
            "state": "OPEN-CANDIDATE",
            "released": False,
            "positive": False,
            "closure": False,
            "verdict": "غير صادر",
            "note": "المروحة كاملة؛ يلزم حسم عضو ومعنى بعينه بالعدستين",
            "ready_roots": ready_roots,
        }
    return {
        "state": "SOURCE-GAP",
        "released": False,
        "positive": False,
        "closure": False,
        "verdict": "غير صادر",
        "note": "لا يملك أي مرشح جذري مروحة مصدرين قديمين كاملة",
    }


def apply_decision(
    section: str, family: str, batch: str, decision: dict[str, object]
) -> tuple[str, dict[str, str]]:
    marker = f"<!-- ARABIC-FAN-CAMPAIGN:{batch}:{family} -->"
    if marker in section:
        return section, {"already_applied": "true"}
    state = str(decision["state"])
    section, old_blocker = replace_one(
        section,
        BLOCKER,
        f"- عائق: النوع={state}؛ يتطلب={decision.get('note') or decision.get('scope')}؛",
    )
    if "النوع=TOOL-GAP" not in old_blocker:
        raise ValueError(f"{family}: target no longer starts at TOOL-GAP")
    section, old_closure = replace_one(
        section, CLOSURE, f"- حالةُ الإغلاق: {state}"
    )
    if decision["positive"]:
        verdict_line = (
            f"- الحكم (استكشاف): {decision['verdict']}؛ "
            f"{decision['scope']}؛ لا وراثة عبر عضو مخالف."
        )
    elif decision["closure"] and decision["verdict"] == "LOANWORD":
        verdict_line = "- الحكم (استكشاف): LOANWORD؛ عزل بلا حكم نسب."
    else:
        verdict_line = f"- الحكم (استكشاف): غير صادر؛ {decision['note']}."
    section, old_verdict = replace_one(section, VERDICT, verdict_line)

    lines = [
        "",
        marker,
        f"- ملحق حملة المروحة المصرية، {DATE}:",
        f"  - المصير الجاري: `{state}`.",
    ]
    if decision["positive"]:
        lines.extend(
            [
                f"  - مروحة العربية: `{decision['root']}`؛ "
                + " + ".join(decision["sources"])
                + "؛ كاملة غير مقتطعة.",
                "  - تحقق المعنى في المصدرين: "
                + "، ".join(f"`{term}`" for term in decision["terms"])
                + ".",
                f"  - إسناد المصرية الفردي: {decision['source_anchor']}",
                "  - الصفوف اللازمة وحدها: "
                + (
                    "، ".join(decision["sound_rules"])
                    if decision["sound_rules"]
                    else "لا صف في المسار المولد؛ أو القيد اليدوي مسمى في نطاق الحكم"
                )
                + ".",
            ]
        )
    else:
        ready_roots = decision.get("ready_roots") or []
        lines.append(
            "  - نتيجة المروحة: "
            + (
                "مكتملة للمرشحين " + "، ".join(f"`{root}`" for root in ready_roots)
                if ready_roots
                else "استنفدت آليا؛ العائق الجاري مسمى أعلاه"
            )
            + "."
        )
    lines.extend(
        [
            "  - السجل التاريخي المحفوظ:",
            f"    - `{old_blocker}`",
            f"    - `{old_closure}`",
            f"    - `{old_verdict}`",
        ]
    )
    return section.rstrip() + "\n" + "\n".join(lines) + "\n\n", {
        "old_blocker": old_blocker,
        "old_closure": old_closure,
        "old_verdict": old_verdict,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-rank", type=int, required=True)
    parser.add_argument("--end-rank", type=int, required=True)
    args = parser.parse_args()
    if not (1 <= args.start_rank <= args.end_rank <= 600):
        raise SystemExit("rank window must be within 1-600")

    completeness = json.loads(COMPLETENESS.read_text(encoding="utf-8"))
    complete_roots = {
        row["root"]
        for row in completeness["roots"]
        if row["complete_two_source_fan"]
    }
    batch = f"EGYPTIAN-{args.start_rank:03d}-{args.end_rank:03d}"
    text = READING.read_text(encoding="utf-8")
    parts = SECTION.split(text)
    output: list[str] = []
    records: list[dict[str, object]] = []
    connection = sqlite3.connect(DB)
    try:
        for section in parts:
            heading = section.split("\n", 1)[0] if section else ""
            match = RANK_HEADING.match(heading)
            if not match:
                output.append(section)
                continue
            rank = int(match.group("rank"))
            if not (args.start_rank <= rank <= args.end_rank):
                output.append(section)
                continue
            family = match.group("family")
            rows = family_rows(connection, family)
            generated = candidates(connection, family)
            decision = (
                positive_decision(family, rows, generated)
                or terminal_decision(rows)
                or held_decision(rows, generated, complete_roots)
            )
            changed, history = apply_decision(
                section, family, batch, decision
            )
            output.append(changed)
            records.append(
                {
                    "family": family,
                    "rank": rank,
                    "members": [row["entry_id"] for row in rows],
                    "candidate_roots": sorted(
                        {str(item["form"]) for item in generated}
                    ),
                    **decision,
                    "history": history,
                }
            )
    finally:
        connection.close()

    expected = args.end_rank - args.start_rank + 1
    if len(records) != expected:
        raise ValueError(f"expected {expected} rank cards, found {len(records)}")
    updated = "".join(output)
    if unicodedata.normalize("NFC", updated) != updated:
        raise ValueError("Egyptian reading is not NFC")
    atomic_write(READING, updated)

    positives = [row for row in records if row["positive"]]
    closures = [row for row in records if row["closure"]]
    held = [row for row in records if not row["released"]]
    payload = {
        "schema": "arabic-fan-campaign-egyptian-v1",
        "status": "LOCAL-THIRD-LENS-REVIEW-REQUIRED",
        "date": DATE,
        "batch": batch,
        "language": "egyptian",
        "rank_window": [args.start_rank, args.end_rank],
        "summary": {
            "cards_reviewed": len(records),
            "positive_connections": len(positives),
            "positive_verdicts": dict(
                sorted(Counter(row["verdict"] for row in positives).items())
            ),
            "closures": len(closures),
            "closure_states": dict(
                sorted(Counter(row["state"] for row in closures).items())
            ),
            "held_states": dict(
                sorted(Counter(row["state"] for row in held).items())
            ),
        },
        "records": records,
    }
    cache = (
        ROOT
        / "cache"
        / "recovery_pipeline"
        / f"arabic-fan-campaign-egyptian-{args.start_rank:03d}-{args.end_rank:03d}.json"
    )
    audit = (
        ROOT
        / "05-audits"
        / f"2026-07-25-arabic-fan-campaign-egyptian-{args.start_rank:03d}-{args.end_rank:03d}.md"
    )
    atomic_write(cache, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    positive_text = "، ".join(
        f"{key}={value}" for key, value in payload["summary"]["positive_verdicts"].items()
    ) or "لا شيء"
    closure_text = "، ".join(
        f"{key}={value}" for key, value in payload["summary"]["closure_states"].items()
    ) or "لا شيء"
    held_text = "، ".join(
        f"{key}={value}" for key, value in payload["summary"]["held_states"].items()
    ) or "لا شيء"
    atomic_write(
        audit,
        "\n".join(
            [
                f"# حملة المروحة المصرية، الرتب {args.start_rank}-{args.end_rank}",
                "",
                "دفعة أحكام محلية للمراجعة المضادة الثالثة. المروحة أداة استرداد، ولا يصدر الحكم الموجب إلا للمقابلات المسماة في سجل الدفعة.",
                "",
                "## الرقمان المفصولان",
                "",
                f"- الصلات الموجبة: {len(positives)} ({positive_text}).",
                f"- الإغلاقات: {len(closures)} ({closure_text}).",
                "",
                f"- بقي معلقا بسببه الحقيقي: {held_text}.",
                "- لا رقم في هذا المحضر للنشر ولا تشغيل لخط البرهان.",
                "",
            ]
        ),
    )
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
