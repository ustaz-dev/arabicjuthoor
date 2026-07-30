#!/usr/bin/env python3
"""Resolve every live Coptic TOOL-GAP with the old-Arabic sense fan.

This is a judgment-producing local pass.  It promotes only two explicitly
checked member/sense pairs.  Every other card leaves TOOL-GAP for its actual
remaining blocker, so running retrieval cannot itself manufacture a verdict.
Greek members previously isolated by the member-scoped loan pass are excluded
from the native member decision.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import build_status_snapshot as status
from search_arabic_root_senses import ARABIC_MARKS, root_sense_fan


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "coptic.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
COMPLETENESS = ROOT / "data" / "arabic-root-lexicon-completeness.json"
CACHE = ROOT / "cache" / "recovery_pipeline" / "arabic-fan-campaign-coptic.json"
AUDIT = ROOT / "05-audits" / "2026-07-27-arabic-fan-campaign-coptic.md"
DATE = "2026-07-27"
MARKER = "ARABIC-FAN-CAMPAIGN:COPTIC-2026-07-27"
FAMILY_ID = re.compile(r"coptic:family:[0-9a-f]+")
# Exclude the legacy Coptic subrange U+03E2..U+03EF.
GREEK = re.compile(r"[\u0370-\u03e1\u03f0-\u03ff\u1f00-\u1fff]")
BLOCKER = re.compile(r"^-\s*عائق:\s*.+$", re.MULTILINE)
SCAN = re.compile(
    r"^-\s*(?:مسحُ المعاني العربيّة|مسح المعاني العربية):\s*.+$",
    re.MULTILINE,
)
CLOSURE = re.compile(r"^-\s*حالةُ الإغلاق:\s*.+$", re.MULTILINE)
VERDICT = re.compile(r"^-\s*الحكم \(استكشاف\):\s*.+$", re.MULTILINE)


POSITIVES = {
    "coptic:family:d110a2343ead37dcf5114a4d": {
        "member": "ⲃⲱⲣϭ",
        "gloss": "break asunder",
        "root": "فرج",
        "verdict": "ROOT-ECHO",
        "terms": ("الخلل", "الفرجة"),
        "scope": "عضو الكسر والانفراج وحده، ولا يرث عضو البرق حكمه",
    },
}

# These surface forms visibly contain a bound negative/agent/phrase element.
# A root fan cannot decide them before a published Coptic segmentation.
MORPHOLOGY_FAMILIES = {
    "coptic:family:08f436373a924e359cfbed1e",  # ⲁⲧⲟⲣⲃ⸗
    "coptic:family:58e2f6bbe35424efc549cef3",  # ϩⲏⲡⲡⲉ
    "coptic:family:95f9cfcfce69ee3b460c0726",  # ϭⲱⲟⲩ (ⲉⲃⲟⲗ)
    "coptic:family:b4ceb2a3821fb26c1c65f46b",  # bound form
    "coptic:family:6ebc8345e905ffd9545ef0b7",  # ⲣⲉϥ- agent
    "coptic:family:fd889d163c5341f4d4a6c613",  # ⲁⲧ- negative
}


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(unicodedata.normalize("NFC", text))
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def replace_required(
    section: str, pattern: re.Pattern[str], replacement: str
) -> tuple[str, str]:
    match = pattern.search(section)
    if not match:
        raise ValueError(
            f"missing live field {pattern.pattern}: {section.splitlines()[0]}"
        )
    old = match.group(0)
    return section[: match.start()] + replacement + section[match.end() :], old


def fold(value: str) -> str:
    value = ARABIC_MARKS.sub("", unicodedata.normalize("NFKC", value))
    return value.translate(str.maketrans("أإآؤئ", "اااوي"))


def inventory() -> tuple[
    dict[str, list[dict[str, object]]],
    dict[str, list[dict[str, object]]],
]:
    connection = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        member_rows = connection.execute(
            """
            SELECT fm.family_id,e.entry_id,e.headword,e.gloss,e.etymology,
                   e.loan_hint,e.form_of
            FROM family_members fm
            JOIN entries e ON e.entry_id=fm.entry_id
            WHERE e.language='coptic'
            ORDER BY fm.family_id,e.entry_id
            """
        ).fetchall()
        candidate_rows = connection.execute(
            """
            SELECT DISTINCT fm.family_id,c.kind,c.form,c.status,
                   c.rule_ids_json,c.route_flag
            FROM family_members fm
            JOIN entries e ON e.entry_id=fm.entry_id
            JOIN candidates c ON c.entry_id=e.entry_id
            WHERE e.language='coptic'
              AND c.kind IN ('root','hollow-root')
            ORDER BY fm.family_id,c.kind,c.form,c.rule_ids_json
            """
        ).fetchall()
    finally:
        connection.close()

    members: dict[str, list[dict[str, object]]] = defaultdict(list)
    candidates: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in member_rows:
        members[row["family_id"]].append(
            {
                "entry_id": row["entry_id"],
                "headword": row["headword"],
                "gloss": row["gloss"] or "",
                "etymology": row["etymology"] or "",
                "greek": bool(GREEK.search(row["etymology"] or "")),
                "loan_hint": bool(row["loan_hint"]),
                "form_of": bool(row["form_of"]),
            }
        )
    for row in candidate_rows:
        candidates[row["family_id"]].append(
            {
                "kind": row["kind"],
                "form": row["form"],
                "status": row["status"],
                "rules": json.loads(row["rule_ids_json"]),
                "route_required": bool(row["route_flag"]),
            }
        )
    return dict(members), dict(candidates)


def complete_root_inventory() -> dict[str, dict[str, object]]:
    payload = json.loads(COMPLETENESS.read_text(encoding="utf-8"))
    return {
        row["root"]: row
        for row in payload["roots"]
        if row["complete_two_source_fan"]
    }


def positive_decision(
    family: str,
    section: str,
    members: list[dict[str, object]],
    candidates: list[dict[str, object]],
) -> dict[str, object] | None:
    specification = POSITIVES.get(family)
    if not specification:
        return None
    native_members = [row for row in members if not row["greek"]]
    matching = [
        row
        for row in native_members
        if row["headword"] == specification["member"]
        and specification["gloss"] in str(row["gloss"])
    ]
    if not matching:
        raise ValueError(f"{family}: named Coptic member/sense is absent")
    if any(row["loan_hint"] for row in matching):
        raise ValueError(f"{family}: named member carries a loan hint")
    if "Crum" not in section or "KELLIA" not in section:
        raise ValueError(f"{family}: card lacks individual Crum/KELLIA citation")
    root = str(specification["root"])
    licensed = [
        row
        for row in candidates
        if row["form"] == root
        and row["status"] in {"licensed", "manual-condition"}
    ]
    if not licensed:
        raise ValueError(f"{family}: root {root} is not licensed")
    chosen = min(
        licensed, key=lambda row: (len(row["rules"]), list(row["rules"]))
    )
    fan = root_sense_fan(ROOT / "Resources", root, None)["independent_fan"]
    if not fan["judgment_ready"] or len(fan["selected_sources"]) < 2:
        raise ValueError(f"{family}: two-source fan incomplete for {root}")
    for witness in fan["selected_sources"]:
        definition = fold(str(witness["definition"]))
        if not any(fold(term) in definition for term in specification["terms"]):
            raise ValueError(
                f"{family}: named sense missing in {witness['source_label']}"
            )
    return {
        "state": "READY",
        "positive": True,
        "closure": False,
        "verdict": specification["verdict"],
        "root": root,
        "scope": specification["scope"],
        "sources": [
            row["source_label"] for row in fan["selected_sources"]
        ],
        "rules": list(chosen["rules"]),
    }


def held_decision(
    family: str,
    members: list[dict[str, object]],
    candidates: list[dict[str, object]],
    complete_roots: dict[str, dict[str, object]],
) -> dict[str, object]:
    native_members = [row for row in members if not row["greek"]]
    if not native_members:
        raise ValueError(f"{family}: pure Greek family survived isolation")
    glosses = " | ".join(str(row["gloss"]) for row in native_members)
    named_non_greek_loans = [
        row for row in native_members if row["loan_hint"]
    ]
    if named_non_greek_loans:
        routes = " | ".join(
            f"{row['headword']}: {row['etymology']}"
            for row in named_non_greek_loans
        )
        return {
            "state": "SOURCE-GAP",
            "positive": False,
            "closure": False,
            "verdict": "غير صادر",
            "note": "يعزل العضو الموسوم بقرض غير يوناني، ويثبت مسار بقية أعضاء الأسرة قبل الحكم",
            "ready_roots": [],
            "native_glosses": glosses + "؛ مسارات معزولة=" + routes,
        }
    if all(
        not str(row["gloss"]).strip()
        or "unknown" in str(row["gloss"]).casefold()
        or "unclear" in str(row["gloss"]).casefold()
        for row in native_members
    ):
        return {
            "state": "SOURCE-GAP",
            "positive": False,
            "closure": False,
            "verdict": "غير صادر",
            "note": "معنى العضو القبطي الأصيل غير مثبت بما يكفي للحكم",
            "ready_roots": [],
            "native_glosses": glosses,
        }
    if family in MORPHOLOGY_FAMILIES:
        return {
            "state": "MORPHOLOGY-GAP",
            "positive": False,
            "closure": False,
            "verdict": "غير صادر",
            "note": "يلزم تحليل صرفي قبطي منشور قبل مقارنة الصورة المركبة أو المقيدة",
            "ready_roots": [],
            "native_glosses": glosses,
        }
    licensed = [
        row
        for row in candidates
        if row["status"] in {"licensed", "manual-condition"}
    ]
    ready_roots = sorted(
        {
            str(row["form"])
            for row in licensed
            if str(row["form"]) in complete_roots
        }
    )
    if ready_roots:
        return {
            "state": "OPEN-CANDIDATE",
            "positive": False,
            "closure": False,
            "verdict": "غير صادر",
            "note": "المروحة مكتملة؛ يلزم حسم عضو ومعنى بعينه بالعدستين",
            "ready_roots": ready_roots,
            "native_glosses": glosses,
        }
    if candidates and all(row["status"] == "scope-gap" for row in candidates):
        return {
            "state": "LAW-GAP",
            "positive": False,
            "closure": False,
            "verdict": "غير صادر",
            "note": "لا مرشح جذري نافذ خارج صفوف النطاق المعلقة",
            "ready_roots": [],
            "native_glosses": glosses,
        }
    return {
        "state": "SOURCE-GAP",
        "positive": False,
        "closure": False,
        "verdict": "غير صادر",
        "note": "لا يملك المرشح الجذري مروحة مصدرين قديمين كاملة",
        "ready_roots": [],
        "native_glosses": glosses,
    }


def source_summary(
    roots: list[str], complete_roots: dict[str, dict[str, object]]
) -> list[dict[str, object]]:
    return [
        {
            "root": root,
            "sources": [
                source["source_label"]
                for source in complete_roots[root]["selected_sources"]
            ],
        }
        for root in roots
    ]


def apply_family(
    section: str,
    family: str,
    decision: dict[str, object],
    complete_roots: dict[str, dict[str, object]],
) -> tuple[str, dict[str, str]]:
    marker = f"<!-- {MARKER}:{family} -->"
    if marker in section:
        return section, {"already_applied": "true"}
    state = str(decision["state"])
    section, old_blocker = replace_required(
        section,
        BLOCKER,
        f"- عائق: النوع={state}؛ يتطلب={decision.get('note') or decision.get('scope')}؛",
    )
    if "النوع=TOOL-GAP" not in old_blocker:
        raise ValueError(f"{family}: live blocker is not TOOL-GAP")
    ready_roots = list(decision.get("ready_roots") or [])
    if decision["positive"]:
        scan_line = (
            f"- مسحُ المعاني العربيّة: اكتملت المروحة غير المقتطعة للجذر "
            f"`{decision['root']}` من {decision['sources'][0]} و"
            f"{decision['sources'][1]}، وثبت المعنى المسمى في كليهما."
        )
    else:
        scan_line = (
            "- مسحُ المعاني العربيّة: "
            + (
                "اكتملت المروحة غير المقتطعة للمرشحين "
                + "، ".join(f"`{root}`" for root in ready_roots)
                + "؛ المصدران المستعملان لكل جذر مسميان في ملحق الدفعة؛ "
                "اكتمال الاسترداد لا يصدر حكمًا."
                if ready_roots
                else "استنفد جرد المروحة؛ بقي العائق الحقيقي المسمى في البطاقة."
            )
        )
    section, old_scan = replace_required(section, SCAN, scan_line)
    section, old_closure = replace_required(
        section, CLOSURE, f"- حالةُ الإغلاق: {state}"
    )
    if decision["positive"]:
        verdict_line = (
            f"- الحكم (استكشاف): {decision['verdict']}؛ "
            f"{decision['scope']}؛ لا وراثة عبر الأسرة."
        )
    else:
        verdict_line = (
            f"- الحكم (استكشاف): غير صادر؛ {decision['note']}."
        )
    section, old_verdict = replace_required(section, VERDICT, verdict_line)
    appendix = [
        "",
        marker,
        f"- ملحق حملة المروحة القبطية، {DATE}:",
        f"  - المصير الجاري: `{state}`.",
    ]
    if decision["positive"]:
        appendix.extend(
            [
                f"  - الجذر العربي: `{decision['root']}`.",
                "  - المصدران القديمان المستقلان: "
                + "، ".join(decision["sources"])
                + ".",
                "  - الصفوف اللازمة وحدها: "
                + (
                    "، ".join(decision["rules"])
                    if decision["rules"]
                    else "لا صف؛ هوية صامتية"
                )
                + ".",
            ]
        )
    else:
        appendix.extend(
            [
                f"  - معنى الأعضاء غير اليونانية: {decision['native_glosses']}.",
                "  - جذور المروحة المكتملة ومصادرها: "
                + json.dumps(
                    source_summary(ready_roots, complete_roots),
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            ]
        )
    appendix.extend(
        [
            "  - الحقول الحاكمة السابقة محفوظة بلا محو:",
            f"    - `{old_blocker}`",
            f"    - `{old_scan}`",
            f"    - `{old_closure}`",
            f"    - `{old_verdict}`",
        ]
    )
    return section.rstrip() + "\n" + "\n".join(appendix) + "\n", {
        "old_blocker": old_blocker,
        "old_scan": old_scan,
        "old_closure": old_closure,
        "old_verdict": old_verdict,
    }


def refer_historical_shnfe(section: str) -> tuple[str, dict[str, object]]:
    marker = f"<!-- {MARKER}:SHNFE-REFERRED -->"
    if marker in section:
        return section, {"already_applied": True}
    section, old_blocker = replace_required(
        section,
        BLOCKER,
        "- عائق: النوع=REFERRED؛ يتطلب=لا شيء؛ الحكم الحي مثبت في بطاقة "
        "التوأم اللاحقة ϣⲛϥⲉ/šnf.t ↔ شنف؛",
    )
    section, old_closure = replace_required(
        section, CLOSURE, "- حالةُ الإغلاق: REFERRED"
    )
    appendix = [
        "",
        marker,
        f"- إحالة تصحيحية، {DATE}: هذه بطاقة تاريخية لا بطاقة حكم مستقلة.",
        "  - الحكم الحي: NUCLEUS-ECHO في إعادة التوسيم المؤرخة 2026-07-18.",
        f"  - العائق السابق: `{old_blocker}`",
        f"  - الإغلاق السابق: `{old_closure}`",
    ]
    return section.rstrip() + "\n" + "\n".join(appendix) + "\n", {
        "state": "REFERRED",
        "positive": False,
        "closure": False,
        "verdict": "غير صادر",
        "history": {"old_blocker": old_blocker, "old_closure": old_closure},
    }


def main() -> int:
    members, candidates = inventory()
    complete_roots = complete_root_inventory()
    text = READING.read_text(encoding="utf-8")
    output: list[str] = []
    records: list[dict[str, object]] = []
    for section in re.split(r"(?=^### )", text, flags=re.MULTILINE):
        if not section.startswith("### ") or status.live_blocker(section) != "TOOL-GAP":
            output.append(section)
            continue
        heading = section.splitlines()[0]
        family_ids = set(FAMILY_ID.findall(section))
        if not family_ids:
            if "šnfe" not in heading:
                raise ValueError(f"TOOL-GAP card lacks family id: {heading}")
            changed, record = refer_historical_shnfe(section)
            output.append(changed)
            records.append({"title": heading, "family": None, **record})
            continue
        if len(family_ids) != 1:
            raise ValueError(f"card maps to multiple Coptic families: {heading}")
        family = next(iter(family_ids))
        decision = positive_decision(
            family, section, members[family], candidates.get(family, [])
        ) or held_decision(
            family,
            members[family],
            candidates.get(family, []),
            complete_roots,
        )
        changed, history = apply_family(
            section, family, decision, complete_roots
        )
        output.append(changed)
        records.append(
            {
                "title": heading,
                "family": family,
                "native_members": [
                    row["entry_id"]
                    for row in members[family]
                    if not row["greek"]
                ],
                "greek_members_excluded": [
                    row["entry_id"]
                    for row in members[family]
                    if row["greek"]
                ],
                **decision,
                "history": history,
            }
        )

    updated = unicodedata.normalize("NFC", "".join(output))
    if unicodedata.normalize("NFC", updated) != updated:
        raise ValueError("Coptic reading is not NFC")
    atomic_write(READING, updated)
    positives = [row for row in records if row.get("positive")]
    closures = [row for row in records if row.get("closure")]
    held = [
        row
        for row in records
        if not row.get("positive")
        and not row.get("closure")
        and row.get("state") != "REFERRED"
    ]
    payload = {
        "schema": "arabic-fan-campaign-coptic-v1",
        "status": "LOCAL-THIRD-LENS-REVIEW-REQUIRED",
        "date": DATE,
        "language": "coptic",
        "summary": {
            "cards_reviewed": len(records),
            "positive_connections": len(positives),
            "positive_verdicts": dict(
                sorted(Counter(row["verdict"] for row in positives).items())
            ),
            "closures": len(closures),
            "held_states": dict(
                sorted(Counter(row["state"] for row in held).items())
            ),
            "historical_referrals": sum(
                row.get("state") == "REFERRED" for row in records
            ),
        },
        "records": records,
    }
    atomic_write(CACHE, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    positive_text = "، ".join(
        f"{key}={value}"
        for key, value in payload["summary"]["positive_verdicts"].items()
    ) or "لا شيء"
    held_text = "، ".join(
        f"{key}={value}"
        for key, value in payload["summary"]["held_states"].items()
    ) or "لا شيء"
    atomic_write(
        AUDIT,
        "\n".join(
            [
                "# حملة المروحة القبطية، 2026-07-27",
                "",
                "دفعة محلية للمراجعة المضادة الثالثة. عزل الأعضاء اليونانية سابق على الحكم، ولا يرث العضو غير اليوناني مصير جاره.",
                "",
                "## الرقمان المفصولان",
                "",
                f"- الصلات الموجبة: {len(positives)} ({positive_text}).",
                f"- الإغلاقات: {len(closures)}.",
                "",
                f"- بقي معلقًا بسببه الحقيقي: {held_text}.",
                f"- إحالات تاريخية لا بطاقات حكم: {payload['summary']['historical_referrals']}.",
                "- لا TOOL-GAP حي في بطاقات هذه الدفعة بعد المرور.",
                "- لا رقم للنشر ولا تشغيل لخط البرهان.",
                "",
            ]
        ),
    )
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
