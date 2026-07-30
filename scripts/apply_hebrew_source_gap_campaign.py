#!/usr/bin/env python3
"""Resolve only evidence-complete Hebrew SOURCE-GAP cards.

This pass is deliberately conservative.  It:

* refers an older card to an already issued member-level verdict;
* isolates whole families that are names, nonlexical phrases, or a named
  intra-house transfer;
* issues three explicitly specified links with an old Hebrew witness and a
  two-source old-Arabic semantic fan;
* moves q-t-r to LAW-GAP because Hebrew tet against Arabic ta is not licensed
  by a signed Hebrew sound row;
* leaves every other SOURCE-GAP card untouched and records why.

All verdict-bearing output remains local for third-lens review.
"""
from __future__ import annotations

import json
import re
import sqlite3
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import build_status_snapshot as status
from search_arabic_root_senses import (
    ARABIC_MARKS,
    DEFAULT_RESOURCES,
    independent_fan,
    matches_for_roots,
)


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
WITNESSES = ROOT / "data" / "hebrew-temporal-witnesses.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
CACHE = (
    ROOT
    / "cache"
    / "recovery_pipeline"
    / "hebrew-source-gap-campaign-2026-07-27.json"
)
AUDIT = (
    ROOT
    / "05-audits"
    / "2026-07-27-hebrew-source-gap-campaign-local.md"
)
DATE = "2026-07-27"
BATCH = "HEBREW-SOURCE-GAP-01"

SECTION = re.compile(r"(?=^### )", re.MULTILINE)
CARD = re.compile(
    r"^### بطاقة: `(?P<family>hebrew:family:[0-9a-f]+)`، "
    r"(?P<title>[^\n]+)$",
    re.MULTILINE,
)
BLOCKER = re.compile(r"^-\s*عائق:\s*.+$", re.MULTILINE)
SCAN = re.compile(r"^-\s*مسحُ?\s*المعاني العربيّة:\s*.+$", re.MULTILINE)
OLDEST = re.compile(r"^-\s*أقدمُ?\s*صورةٍ مستعادة:\s*.+$", re.MULTILINE)
CLOSURE = re.compile(r"^-\s*حالةُ الإغلاق:\s*.+$", re.MULTILINE)
VERDICT = re.compile(r"^-\s*الحكم \(استكشاف\):\s*.+$", re.MULTILINE)
FAMILY_ID = re.compile(r"hebrew:family:[0-9a-f]+")
POSITIVE_PREFIXES = ("ROOT-", "NUCLEUS-")


# family: entry, Arabic root, verdict, required semantic terms in each old
# Arabic source, exact member scope, and the named semantic bridge.
POSITIVE_SPECS: dict[str, dict[str, object]] = {
    "hebrew:family:c907725dc16afee129272bd3": {
        "entry": "kaikki_hebrew:9882:en-ביכר-he-verb-7m49XH6K",
        "root": "بكر",
        "verdict": "ROOT-TRACE",
        "terms": ("أول ولد",),
        "scope": "ביכר «ولدت أول مرة» وحده، مع صورته الناقصة בכר",
        "bridge": "مباشر: البكر أول ولد، والفعل ولادة البكر أول مرة",
        "sound": "تطابق صوامت الجذر ב־כ־ר مع بكر بعد حفظ ياء الرسم في ביכר؛ لا صف إبدال لازم",
    },
    "hebrew:family:8fd3002ca26b804067cc33a7": {
        "entry": "kaikki_hebrew:917:en-קדם-he-noun-LY1pMXes",
        "root": "قدم",
        "verdict": "ROOT-TRACE",
        "terms": ("تقدم", "سابقة"),
        "scope": "קדם «المقدمة والجهة الأمامية» وحده",
        "bridge": "مباشر على جذر السبق والتقدم إلى الأمام",
        "sound": "تطابق صوامت ק־ד־ם مع قدم؛ لا صف إبدال لازم",
    },
    "hebrew:family:32d76a601129e2faab838c32": {
        "entry": "kaikki_hebrew:596:en-ברך-he-verb-g4vsx5Df",
        "root": "برك",
        "verdict": "ROOT-TRACE",
        "terms": ("برك البعير", "ركبتي"),
        "scope": "ברך «ركع على ركبتيه» وحده",
        "bridge": "مباشر: بروك البعير وقوعه على ركبتيه",
        "sound": "تطابق صوامت ב־ר־ך مع برك؛ لا صف إبدال لازم",
    },
}


LAW_GAP_SPECS: dict[str, dict[str, str]] = {
    "hebrew:family:40f6b2ad4791a305b8682930": {
        "entry": "kaikki_hebrew:13191:en-קיטר-he-verb-2FOitYfB",
        "root": "قتر",
        "reason": (
            "الشاهد التوراتي والمروحة الدلالية مكتملان، لكن ק־ט־ר "
            "يقابل قتر بهيكل طاء عبرية ט أمام تاء عربية، ولا صف عبري "
            "موقع يرخص هذا الاتجاه؛ DENT-05 لا يحول هذا الموضع إلى "
            "تطابق عبري عربي"
        ),
    }
}


PROPER_NAME_FAMILIES = {
    "hebrew:family:1cf3413430869f8d45ceef7d",
    "hebrew:family:2fcd8eb180812a6b31271b93",
    "hebrew:family:68a68d44a6d08adf87f488d6",
    "hebrew:family:9751fa410f170ed439d1b1b9",
    "hebrew:family:dbee04e1ec4168350f777d29",
    "hebrew:family:4ad421719ce0a70ae5f7e991",
}
TRANSFER_FAMILY = "hebrew:family:c1facb0cf948d1b8e0507ac8"
NONLEXICAL_FAMILY = "hebrew:family:cf9cbb8439a3f1728ae92460"


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


def replace_one(
    section: str, pattern: re.Pattern[str], replacement: str
) -> tuple[str, str]:
    match = pattern.search(section)
    if not match:
        raise ValueError(f"missing field: {pattern.pattern}")
    old = match.group(0)
    return (
        section[: match.start()] + replacement + section[match.end() :],
        old,
    )


def fold_arabic(value: str) -> str:
    value = ARABIC_MARKS.sub("", unicodedata.normalize("NFKC", value))
    value = value.translate(str.maketrans("أإآؤئ", "اااوي"))
    return " ".join(value.split())


def old_witnesses() -> dict[str, list[dict[str, object]]]:
    payload = json.loads(WITNESSES.read_text(encoding="utf-8"))
    result: dict[str, list[dict[str, object]]] = defaultdict(list)
    for witness in payload["witnesses"]:
        if witness["stratum"] in {"biblical", "mishnaic"}:
            result[str(witness["entry_id"])].append(witness)
    return result


def family_members(
    connection: sqlite3.Connection, family: str
) -> list[dict[str, object]]:
    return [
        {
            "entry_id": row[0],
            "headword": row[1],
            "pos": row[2],
            "gloss": row[3],
            "etymology": row[4],
            "loan_hint": bool(row[5]),
        }
        for row in connection.execute(
            """
            SELECT e.entry_id,e.headword,e.pos,e.gloss,e.etymology,e.loan_hint
            FROM family_members fm
            JOIN entries e ON e.entry_id=fm.entry_id
            WHERE fm.family_id=?
            ORDER BY e.entry_id
            """,
            (family,),
        )
    ]


def card_states(text: str) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = defaultdict(list)
    for section in SECTION.split(text):
        match = CARD.match(section)
        if not match:
            continue
        result[match.group("family")].append(
            {
                "title": match.group("title"),
                "blocker": status.live_blocker(section),
                "verdict": status.live_verdict(section),
            }
        )
    return result


def ready_sibling(
    family: str,
    title: str,
    states: dict[str, list[dict[str, str]]],
) -> dict[str, str] | None:
    for row in states.get(family, []):
        if row["blocker"] != "READY":
            continue
        if row["verdict"].startswith(POSITIVE_PREFIXES):
            return row
    return None


def semantic_excerpt(definition: str, terms: tuple[str, ...]) -> str:
    folded = fold_arabic(definition)
    positions = [
        folded.find(fold_arabic(term))
        for term in terms
        if folded.find(fold_arabic(term)) >= 0
    ]
    if not positions:
        raise ValueError("named semantic terms absent from old-Arabic source")
    start = max(0, min(positions) - 90)
    end = min(len(folded), min(positions) + 260)
    return folded[start:end]


def fan_for(root: str, terms: tuple[str, ...]) -> dict[str, object]:
    matches = matches_for_roots(DEFAULT_RESOURCES, {root}, None)
    fan = independent_fan(matches[root])
    selected = fan["selected_sources"]
    if not fan["judgment_ready"] or len(selected) < 2:
        raise ValueError(f"incomplete old-Arabic fan for {root}")
    enriched = []
    for witness in selected:
        enriched.append(
            {
                "source": witness["source_label"],
                "excerpt": semantic_excerpt(
                    str(witness["definition"]),
                    terms,
                ),
            }
        )
    return {
        "root": root,
        "sources": enriched,
    }


def witness_for(
    entry: str,
    witness_map: dict[str, list[dict[str, object]]],
) -> dict[str, object]:
    rows = witness_map.get(entry, [])
    if not rows:
        raise ValueError(f"missing old Hebrew witness for {entry}")
    return rows[0]


def terminal_decision(
    family: str,
    members: list[dict[str, object]],
) -> dict[str, object] | None:
    if family in PROPER_NAME_FAMILIES:
        if not members or any(str(row["pos"]) != "name" for row in members):
            raise ValueError(f"{family}: proper-name family contains lexical member")
        return {
            "kind": "terminal",
            "state": "PROPER-NAME-ISOLATED",
            "note": "كل أعضاء الأسرة أعلام؛ عزل محاسبي بلا حكم نسب",
        }
    if family == TRANSFER_FAMILY:
        if not members or any(
            "Borrowed from Aramaic" not in str(row["etymology"])
            for row in members
        ):
            raise ValueError(f"{family}: intra-house donor is not explicit")
        return {
            "kind": "terminal",
            "state": "INTRA-HOUSE-TRANSFER",
            "note": (
                "كل أعضاء الأسرة منقولة صراحة من الآرامية داخل البيت "
                "السامي؛ تحال إلى زوج المانح ولا تعد شاهد فرع مستقل"
            ),
        }
    if family == NONLEXICAL_FAMILY:
        if not members or any(str(row["pos"]) != "phrase" for row in members):
            raise ValueError(f"{family}: nonlexical family contains lexical member")
        return {
            "kind": "terminal",
            "state": "NONLEXICAL-ISOLATED",
            "note": "كل أعضاء الأسرة عبارات وظيفية؛ عزل محاسبي بلا حكم نسب",
        }
    return None


def decide(
    family: str,
    title: str,
    states: dict[str, list[dict[str, str]]],
    members: list[dict[str, object]],
    witness_map: dict[str, list[dict[str, object]]],
    fans: dict[str, dict[str, object]],
) -> dict[str, object] | None:
    sibling = ready_sibling(family, title, states)
    if sibling:
        return {
            "kind": "referral",
            "state": "REFERRED",
            "note": (
                "بطاقة أقدم أحيلت إلى الحكم العضوي الحي في الأسرة نفسها؛ "
                "لا تعد صلة ولا إغلاقًا في مقام القياس"
            ),
            "referred_to": sibling["title"],
        }
    terminal = terminal_decision(family, members)
    if terminal:
        return terminal
    if family in POSITIVE_SPECS:
        specification = POSITIVE_SPECS[family]
        entry = str(specification["entry"])
        witness = witness_for(entry, witness_map)
        if entry not in {str(row["entry_id"]) for row in members}:
            raise ValueError(f"{family}: positive entry is outside family")
        return {
            "kind": "positive",
            "state": "READY",
            **specification,
            "old_witness": witness,
            "fan": fans[str(specification["root"])],
        }
    if family in LAW_GAP_SPECS:
        specification = LAW_GAP_SPECS[family]
        entry = specification["entry"]
        witness = witness_for(entry, witness_map)
        if entry not in {str(row["entry_id"]) for row in members}:
            raise ValueError(f"{family}: law-gap entry is outside family")
        return {
            "kind": "law-gap",
            "state": "LAW-GAP",
            **specification,
            "old_witness": witness,
            "fan": fans[specification["root"]],
        }
    return None


def apply_decision(
    section: str,
    family: str,
    decision: dict[str, object],
) -> tuple[str, dict[str, str]]:
    marker = f"<!-- HEBREW-SOURCE-GAP:{BATCH}:{family} -->"
    if marker in section:
        return section, {"already_applied": "true"}
    if status.live_blocker(section) != "SOURCE-GAP":
        raise ValueError(f"{family}: target is no longer SOURCE-GAP")

    state = str(decision["state"])
    note = str(
        decision.get("note")
        or decision.get("scope")
        or decision.get("reason")
    )
    section, old_blocker = replace_one(
        section,
        BLOCKER,
        f"- عائق: النوع={state}؛ يتطلب={note}؛",
    )

    if decision["kind"] == "positive":
        fan = decision["fan"]
        source_names = " + ".join(
            str(row["source"]) for row in fan["sources"]
        )
        scan = (
            f"- مسحُ المعاني العربيّة: مروحة مستقلة مكتملة للجذر "
            f"`{decision['root']}` من {source_names}؛ تحقق المعنى "
            "المسمى في المصدرين."
        )
    elif decision["kind"] == "law-gap":
        fan = decision["fan"]
        source_names = " + ".join(
            str(row["source"]) for row in fan["sources"]
        )
        scan = (
            f"- مسحُ المعاني العربيّة: مروحة مستقلة مكتملة للجذر "
            f"`{decision['root']}` من {source_names}؛ رجل المعنى قائمة "
            "ويبقى عائق القانون الصوتي."
        )
    elif decision["kind"] == "referral":
        scan = (
            "- مسحُ المعاني العربيّة: محفوظ في بطاقة الحكم العضوي "
            "المحال إليها؛ لا يعاد عده هنا."
        )
    else:
        scan = (
            "- مسحُ المعاني العربيّة: غير لازم بعد العزل الصريح؛ "
            "لا يصدر حكم نسب."
        )
    section, old_scan = replace_one(section, SCAN, scan)

    old_oldest = ""
    if decision["kind"] in {"positive", "law-gap"}:
        witness = decision["old_witness"]
        oldest = (
            "- أقدمُ صورةٍ مستعادة: شاهد "
            f"{witness['stratum']} مسمى للعضو نفسه: "
            f"{witness['reference']}؛ لا يرثه عضو آخر."
        )
        section, old_oldest = replace_one(section, OLDEST, oldest)

    section, old_closure = replace_one(
        section,
        CLOSURE,
        f"- حالةُ الإغلاق: {state}.",
    )
    if decision["kind"] == "positive":
        verdict = (
            f"- الحكم (استكشاف): {decision['verdict']}؛ "
            f"{decision['scope']}؛ المدار={decision['bridge']}؛ "
            "لا وراثة عبر عضو مخالف."
        )
    elif decision["kind"] == "law-gap":
        verdict = (
            f"- الحكم (استكشاف): غير صادر؛ {decision['reason']}."
        )
    else:
        verdict = f"- الحكم (استكشاف): غير صادر؛ {note}."
    section, old_verdict = replace_one(section, VERDICT, verdict)

    appendix = [
        "",
        marker,
        f"- ملحق حسم فجوات المصدر العبرية، {DATE}:",
        f"  - المصير الجاري: `{state}`.",
    ]
    if decision["kind"] == "positive":
        witness = decision["old_witness"]
        appendix.extend(
            [
                f"  - العضو المحكوم: `{decision['entry']}`.",
                f"  - الشاهد العبري القديم: {witness['reference']}",
                f"  - الجذر العربي: `{decision['root']}`.",
                f"  - مسار الصوت اللازم وحده: {decision['sound']}.",
            ]
        )
        for row in decision["fan"]["sources"]:
            appendix.append(
                f"  - {row['source']}: «{row['excerpt']}»."
            )
    elif decision["kind"] == "law-gap":
        witness = decision["old_witness"]
        appendix.extend(
            [
                f"  - الشاهد العبري القديم: {witness['reference']}",
                f"  - نتيجة المروحة: مكتملة للجذر `{decision['root']}`.",
                f"  - العائق الحقيقي: {decision['reason']}.",
            ]
        )
    elif decision["kind"] == "referral":
        appendix.append(
            f"  - الإحالة الحية: {decision['referred_to']}."
        )
    else:
        appendix.append(f"  - سبب العزل: {decision['note']}.")
    appendix.extend(
        [
            "  - السجل التاريخي المحفوظ:",
            f"    - `{old_blocker}`",
            f"    - `{old_scan}`",
            f"    - `{old_closure}`",
            f"    - `{old_verdict}`",
        ]
    )
    if old_oldest:
        appendix.append(f"    - `{old_oldest}`")
    return section.rstrip() + "\n" + "\n".join(appendix) + "\n\n", {
        "old_blocker": old_blocker,
        "old_scan": old_scan,
        "old_oldest": old_oldest,
        "old_closure": old_closure,
        "old_verdict": old_verdict,
    }


def main() -> int:
    text = READING.read_text(encoding="utf-8")
    source_gap_live = [
        card
        for card in status.reading_cards(text)
        if status.live_blocker(card) == "SOURCE-GAP"
    ]
    existing_markers = text.count(
        f"<!-- HEBREW-SOURCE-GAP:{BATCH}:"
    )
    if len(source_gap_live) + existing_markers != 248:
        raise ValueError(
            f"expected a 248-card SOURCE-GAP baseline, got "
            f"{len(source_gap_live)} live plus {existing_markers} applied"
        )

    states = card_states(text)
    witness_map = old_witnesses()
    roots = {
        str(row["root"])
        for row in [*POSITIVE_SPECS.values(), *LAW_GAP_SPECS.values()]
    }
    fan_matches = matches_for_roots(DEFAULT_RESOURCES, roots, None)
    fans: dict[str, dict[str, object]] = {}
    for root in roots:
        terms = (
            tuple(
                str(term)
                for specification in POSITIVE_SPECS.values()
                if specification["root"] == root
                for term in specification["terms"]
            )
            or ("دخان", "بخور")
        )
        fan = independent_fan(fan_matches[root])
        selected = fan["selected_sources"]
        if not fan["judgment_ready"] or len(selected) < 2:
            raise ValueError(f"incomplete two-source fan for {root}")
        fans[root] = {
            "root": root,
            "sources": [
                {
                    "source": row["source_label"],
                    "excerpt": semantic_excerpt(
                        str(row["definition"]),
                        terms,
                    ),
                }
                for row in selected
            ],
        }

    output: list[str] = []
    records: list[dict[str, object]] = []
    unchanged: list[dict[str, object]] = []
    connection = sqlite3.connect(DB)
    try:
        for section in SECTION.split(text):
            match = CARD.match(section)
            if not match:
                output.append(section)
                continue
            family = match.group("family")
            marker = f"<!-- HEBREW-SOURCE-GAP:{BATCH}:{family} -->"
            if marker in section:
                current_state = status.live_blocker(section)
                members = family_members(connection, family)
                if current_state == "READY":
                    specification = POSITIVE_SPECS[family]
                    decision = {
                        "kind": "positive",
                        "state": "READY",
                        **specification,
                        "old_witness": witness_for(
                            str(specification["entry"]),
                            witness_map,
                        ),
                        "fan": fans[str(specification["root"])],
                    }
                elif current_state == "LAW-GAP":
                    specification = LAW_GAP_SPECS[family]
                    decision = {
                        "kind": "law-gap",
                        "state": "LAW-GAP",
                        **specification,
                        "old_witness": witness_for(
                            specification["entry"],
                            witness_map,
                        ),
                        "fan": fans[specification["root"]],
                    }
                elif current_state == "REFERRED":
                    sibling = ready_sibling(
                        family,
                        match.group("title"),
                        states,
                    )
                    if not sibling:
                        raise ValueError(
                            f"{family}: applied referral lost its target"
                        )
                    decision = {
                        "kind": "referral",
                        "state": "REFERRED",
                        "note": (
                            "بطاقة أقدم أحيلت إلى الحكم العضوي الحي في "
                            "الأسرة نفسها؛ لا تعد صلة ولا إغلاقًا في مقام القياس"
                        ),
                        "referred_to": sibling["title"],
                    }
                else:
                    decision = terminal_decision(family, members)
                    if not decision or decision["state"] != current_state:
                        raise ValueError(
                            f"{family}: unrecognized applied state "
                            f"{current_state}"
                        )
                records.append(
                    {
                        "family": family,
                        "heading": section.splitlines()[0],
                        "members": [row["entry_id"] for row in members],
                        **decision,
                        "history": {"already_applied": "true"},
                    }
                )
                output.append(section)
                continue
            if status.live_blocker(section) != "SOURCE-GAP":
                output.append(section)
                continue
            members = family_members(connection, family)
            decision = decide(
                family,
                match.group("title"),
                states,
                members,
                witness_map,
                fans,
            )
            if decision is None:
                family_has_old_witness = any(
                    witness_map.get(str(row["entry_id"])) for row in members
                )
                unchanged.append(
                    {
                        "family": family,
                        "heading": section.splitlines()[0],
                        "members": [row["entry_id"] for row in members],
                        "disposition": "SOURCE-GAP",
                        "reason": (
                            "يوجد شاهد قديم لبعض أعضاء الأسرة، لكن لا "
                            "يستوفي عضو البطاقة حكمًا أو عزلًا آمنًا"
                            if family_has_old_witness
                            else "لا شاهد عبري قديم مسمى للعضو في المصدر المثبت"
                        ),
                    }
                )
                output.append(section)
                continue
            changed, history = apply_decision(section, family, decision)
            output.append(changed)
            records.append(
                {
                    "family": family,
                    "heading": section.splitlines()[0],
                    "members": [row["entry_id"] for row in members],
                    **decision,
                    "history": history,
                }
            )
    finally:
        connection.close()

    updated = "".join(output)
    if unicodedata.normalize("NFC", updated) != updated:
        raise ValueError("updated Hebrew reading is not NFC")
    cards_after = status.reading_cards(updated)
    live_after = Counter(status.live_blocker(card) for card in cards_after)
    kinds = Counter(str(row["kind"]) for row in records)
    terminal_states = Counter(
        str(row["state"])
        for row in records
        if row["kind"] == "terminal"
    )
    positive_verdicts = Counter(
        str(row["verdict"])
        for row in records
        if row["kind"] == "positive"
    )
    summary = {
        "source_gap_before": 248,
        "cards_changed": len(records),
        "positive_connections": kinds["positive"],
        "positive_verdicts": dict(sorted(positive_verdicts.items())),
        "terminal_closures": kinds["terminal"],
        "terminal_states": dict(sorted(terminal_states.items())),
        "referrals_not_counted_as_closures": kinds["referral"],
        "reclassified_law_gap": kinds["law-gap"],
        "source_gap_after": live_after["SOURCE-GAP"],
        "unchanged_source_gap_audited": len(unchanged),
    }
    if summary != {
        "source_gap_before": 248,
        "cards_changed": 21,
        "positive_connections": 3,
        "positive_verdicts": {"ROOT-TRACE": 3},
        "terminal_closures": 8,
        "terminal_states": {
            "INTRA-HOUSE-TRANSFER": 1,
            "NONLEXICAL-ISOLATED": 1,
            "PROPER-NAME-ISOLATED": 6,
        },
        "referrals_not_counted_as_closures": 9,
        "reclassified_law_gap": 1,
        "source_gap_after": 227,
        "unchanged_source_gap_audited": 227,
    }:
        raise ValueError(f"unexpected campaign summary: {summary}")

    atomic_write(READING, updated)

    payload = {
        "schema": "hebrew-source-gap-campaign-v1",
        "status": "LOCAL-THIRD-LENS-REVIEW-REQUIRED",
        "date": DATE,
        "batch": BATCH,
        "summary": summary,
        "records": records,
        "unchanged": unchanged,
    }
    atomic_write(
        CACHE,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    atomic_write(
        AUDIT,
        "\n".join(
            [
                "# حملة فجوات المصدر العبرية، دفعة محلية للمراجعة الثالثة",
                "",
                "## بيان النطاق، الخطوة 14",
                "",
                "راجعت الدفعة كل بطاقات `SOURCE-GAP` العبرية الحية بالعضو، لا بالأسرة. لا يحول غياب الشاهد القديم إلى حكم سلبي، ولا ترث بطاقة قديمة حكم بطاقة لاحقة إلا بإحالة تمنع العد المزدوج.",
                "",
                "## الرقمان المفصولان",
                "",
                f"- الصلات الموجبة الجديدة: {summary['positive_connections']}، وكلها `ROOT-TRACE`.",
                f"- الإغلاقات النهائية: {summary['terminal_closures']}، موزعة على 6 أعلام و1 عبارة غير معجمية و1 انتقال داخل البيت السامي.",
                "",
                "## ما لا يدخل المقام",
                "",
                f"- إحالات إزالة التكرار: {summary['referrals_not_counted_as_closures']}؛ لا تعد صلات ولا إغلاقات.",
                f"- نقل إلى `LAW-GAP`: {summary['reclassified_law_gap']}، وهو קיטר أمام قتر لغياب صف عبري موقع يجيز ט أمام ت.",
                f"- بقي `SOURCE-GAP`: {summary['source_gap_after']}؛ غياب شاهد قديم أو عدم اكتمال حكم العضو لا يحول إلى سالب.",
                "",
                "## حالة الدفعة",
                "",
                "- كل أحكام هذه الدفعة محلية للمراجعة المضادة الثالثة.",
                "- لم يشغل خط البرهان، ولم يغير عداد التسجيل المسبق، ولا يصلح أي رقم هنا للنشر.",
                "",
            ]
        ),
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
