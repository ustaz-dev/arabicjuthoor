#!/usr/bin/env python3
"""Resolve every live Old-Latin TOOL-GAP without forcing a cognate verdict.

The pass applies the old-Arabic fan to licensed root candidates, but the fan is
retrieval evidence only.  Named, unambiguous foreign donors are isolated before
comparison.  Finite forms, compounds, and phrases remain morphology gaps.  A
family is closed for a loan only when all of its non-form lexical lemmas have
named donor routes; otherwise donor members are recorded as member overrides
and the rest of the family stays open.

All output is local and requires third-lens review before commit.
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


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "old-latin.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
COMPLETENESS = ROOT / "data" / "arabic-root-lexicon-completeness.json"
CACHE = (
    ROOT / "cache" / "recovery_pipeline" / "arabic-fan-campaign-old-latin.json"
)
AUDIT = ROOT / "05-audits" / "2026-07-27-arabic-fan-campaign-old-latin.md"
DATE = "2026-07-27"
MARKER = "ARABIC-FAN-CAMPAIGN:OLD-LATIN-2026-07-27"
FAMILY_ID = re.compile(r"latin:family:[0-9a-f]+")
RANK_HEADING = re.compile(
    r"^### بطاقة: `(?P<family>latin:family:[0-9a-f]+)`، "
    r"(?P<headword>.+?) \(الرتبة (?P<rank>\d+)\)$"
)
BLOCKER = re.compile(r"^-\s*عائق:\s*.+$", re.MULTILINE)
SCAN = re.compile(
    r"^-\s*(?:مسحُ المعاني العربيّة|مسح المعاني العربية):\s*.+$",
    re.MULTILINE,
)
CLOSURE = re.compile(r"^-\s*حالةُ الإغلاق:\s*.+$", re.MULTILINE)
VERDICT = re.compile(r"^-\s*الحكم \(استكشاف\):\s*.+$", re.MULTILINE)
FILTER = re.compile(r"^-\s*المصفاة:\s*.+$", re.MULTILINE)

# The donor must be asserted, not merely floated as "perhaps/probably".
NAMED_DONOR = re.compile(
    r"(?:^|[.;]\s*)(?:"
    r"Borrowed from|Borrowed all-together from|From|"
    r"Calque of|Ultimately borrowed from"
    r")\s+(?:"
    r"Ancient Greek|Koine Greek|Byzantine Greek|Arabic|French|"
    r"Old French|Anglo-Norman|Italian|Bengali|Old Norse|"
    r"Biblical Hebrew|Hebrew|Aramaic|Etruscan|Gaulish|Sardinian|"
    r"Turkic|Proto-Germanic"
    r")\b",
    re.IGNORECASE,
)
SEMITIC_DONOR = re.compile(r"\ba Semitic borrowing\b", re.IGNORECASE)
UNCERTAIN_DONOR = re.compile(
    r"\b(?:perhaps|probably|possibly|maybe|uncertain|suggested)\b",
    re.IGNORECASE,
)
MORPHOLOGY_GLOSS = re.compile(
    r"(?:first|second|third)-person|"
    r"(?:present|future|imperfect|perfect)\s+"
    r"(?:active|passive)|"
    r"inflection of|alternative spelling of|ellipsis of",
    re.IGNORECASE,
)
LATE_SCOPE = re.compile(
    r"first attested in the 1[6-9]\d0|"
    r"photoengraving|11th[–-]13th century|modern Latin",
    re.IGNORECASE,
)
GRAMMAR_POS = {
    "prep",
    "conj",
    "pronoun",
    "particle",
    "interj",
}
FUNCTION_ADVERBS = {"cur", "quur", "reapse"}


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


def inventory() -> tuple[
    dict[str, list[dict[str, object]]],
    dict[str, list[dict[str, object]]],
]:
    connection = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        member_rows = connection.execute(
            """
            SELECT fm.family_id,e.entry_id,e.headword,e.pos,e.gloss,
                   e.etymology,e.loan_hint,e.form_of
            FROM family_members fm
            JOIN entries e ON e.entry_id=fm.entry_id
            WHERE e.language='latin'
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
            WHERE e.language='latin'
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
                "pos": row["pos"] or "",
                "gloss": row["gloss"] or "",
                "etymology": row["etymology"] or "",
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


def lexical_members(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [row for row in rows if not row["form_of"]]


def donor_kind(row: dict[str, object]) -> str | None:
    etymology = str(row["etymology"])
    if not etymology:
        return None
    if re.search(r"\bcalque of\b", etymology, re.IGNORECASE):
        return "contact"
    if SEMITIC_DONOR.search(etymology):
        if re.search(
            r"\b(?:more likely|probably|perhaps|possibly)\s+"
            r"a Semitic borrowing\b",
            etymology,
            re.IGNORECASE,
        ):
            return None
        return "loan"
    match = NAMED_DONOR.search(etymology)
    if not match:
        return None
    prefix = etymology[max(0, match.start() - 24) : match.end()]
    return "loan" if not UNCERTAIN_DONOR.search(prefix) else None


def anchor_member(
    rows: list[dict[str, object]], headword: str, section: str
) -> dict[str, object]:
    source_match = re.search(r"`(kaikki_latin:[^`]+)`", section)
    if source_match:
        by_id = [
            row
            for row in rows
            if row["entry_id"] == source_match.group(1)
        ]
        if len(by_id) == 1:
            return by_id[0]
    exact = [
        row
        for row in rows
        if str(row["headword"]).casefold() == headword.casefold()
        and not row["form_of"]
    ]
    if len(exact) == 1:
        return exact[0]
    starts = [
        row
        for row in rows
        if str(row["headword"]).casefold().startswith(headword.casefold())
        and not row["form_of"]
    ]
    if len(starts) == 1:
        return starts[0]
    raise ValueError(f"cannot identify unique anchor {headword}: {len(exact)}/{len(starts)}")


def ready_roots(
    rows: list[dict[str, object]],
    complete_roots: dict[str, dict[str, object]],
) -> list[str]:
    return sorted(
        {
            str(row["form"])
            for row in rows
            if row["status"] in {"licensed", "manual-condition"}
            and str(row["form"]) in complete_roots
        }
    )


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


def live_terminal_by_family(text: str) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = defaultdict(list)
    for section in re.split(r"(?=^### )", text, flags=re.MULTILINE):
        if not section.startswith("### "):
            continue
        verdict = status.live_verdict(section)
        if verdict not in status.POSITIVE_VERDICTS | {"LOANWORD", "NO-TRACE"}:
            continue
        for family in set(FAMILY_ID.findall(section)):
            result[family].append(
                {
                    "title": section.splitlines()[0],
                    "verdict": verdict,
                }
            )
    return dict(result)


def decide(
    family: str,
    anchor: dict[str, object],
    rows: list[dict[str, object]],
    generated: list[dict[str, object]],
    complete_roots: dict[str, dict[str, object]],
    existing_terminal: dict[str, list[dict[str, str]]],
) -> dict[str, object]:
    if family in existing_terminal:
        return {
            "state": "REFERRED",
            "positive": False,
            "closure": False,
            "verdict": "غير صادر",
            "note": "يحيل إلى بطاقة الحكم اللاحقة ولا يعد حكمًا ثانيًا",
            "references": existing_terminal[family],
            "ready_roots": [],
            "member_overrides": [],
        }

    lemmas = lexical_members(rows)
    donor_lemmas = [row for row in lemmas if donor_kind(row)]
    if donor_lemmas and len(donor_lemmas) == len(lemmas):
        route_kinds = {donor_kind(row) for row in donor_lemmas}
        state = (
            "CONTACT-ISOLATED"
            if route_kinds == {"contact"}
            else "LOAN-ROUTE-ISOLATED"
        )
        return {
            "state": state,
            "positive": False,
            "closure": True,
            "verdict": "LOANWORD" if state == "LOAN-ROUTE-ISOLATED" else "غير صادر",
            "note": (
                "كل اللمم المعجمية ذات مانح خارجي مسمى في المصدر"
                if state == "LOAN-ROUTE-ISOLATED"
                else "كل اللمم المعجمية ترجمة اقتراضية مسماة لا قرضا لفظيا"
            ),
            "ready_roots": [],
            "member_overrides": donor_lemmas,
        }

    member_overrides = donor_lemmas
    anchor_text = " ".join(
        [
            str(anchor["headword"]),
            str(anchor["gloss"]),
            str(anchor["etymology"]),
        ]
    )
    if LATE_SCOPE.search(anchor_text):
        if len(lemmas) == 1:
            return {
                "state": "OUT-OF-SCOPE",
                "positive": False,
                "closure": True,
                "verdict": "غير صادر",
                "note": "المصدر نفسه يؤرخ العضو بعد نطاق اللاتينية القديمة",
                "ready_roots": [],
                "member_overrides": [],
            }
        return {
            "state": "MORPHOLOGY-GAP",
            "positive": False,
            "closure": False,
            "verdict": "غير صادر",
            "note": "يعزل العضو المتأخر، وتفصل بقية اللمم المختلطة قبل الحكم",
            "ready_roots": [],
            "member_overrides": [],
        }

    if (
        MORPHOLOGY_GLOSS.search(str(anchor["gloss"]))
        or " " in str(anchor["headword"]).strip()
        or str(anchor["headword"]).endswith("-")
        or str(anchor["pos"]).casefold() == "phrase"
    ):
        return {
            "state": "MORPHOLOGY-GAP",
            "positive": False,
            "closure": False,
            "verdict": "غير صادر",
            "note": "يلزم رد الصورة المصرفة أو العبارة إلى اللمة المنشورة قبل الحكم",
            "ready_roots": [],
            "member_overrides": member_overrides,
        }

    lemma_positions = {str(row["pos"]).strip().casefold() for row in lemmas}
    if lemmas and all(
        (
            any(pos.startswith(kind) for kind in GRAMMAR_POS)
            or (
                pos.startswith("adv")
                and all(
                    str(row["headword"]).casefold() in FUNCTION_ADVERBS
                    for row in lemmas
                    if str(row["pos"]).strip().casefold() == pos
                )
            )
        )
        for pos in lemma_positions
    ):
        return {
            "state": "NONLEXICAL-ISOLATED",
            "positive": False,
            "closure": True,
            "verdict": "غير صادر",
            "note": "كل اللمم أدوات أو ظروف نحوية لا مادة معجمية للحكم",
            "ready_roots": [],
            "member_overrides": [],
        }

    roots = ready_roots(generated, complete_roots)
    if roots:
        return {
            "state": "OPEN-CANDIDATE",
            "positive": False,
            "closure": False,
            "verdict": "غير صادر",
            "note": "المروحة مكتملة؛ يلزم حسم عضو ومعنى بعينه بدرجة النواة والعدستين",
            "ready_roots": roots,
            "member_overrides": member_overrides,
        }
    if generated and all(row["status"] == "scope-gap" for row in generated):
        return {
            "state": "LAW-GAP",
            "positive": False,
            "closure": False,
            "verdict": "غير صادر",
            "note": "لا مرشح نافذ خارج صفوف النطاق المعلقة",
            "ready_roots": [],
            "member_overrides": member_overrides,
        }
    return {
        "state": "SOURCE-GAP",
        "positive": False,
        "closure": False,
        "verdict": "غير صادر",
        "note": "لا يملك المرشح مروحة مصدرين قديمين كاملة، أو لا يكفي إسناده الزمني",
        "ready_roots": [],
        "member_overrides": member_overrides,
    }


def member_override_lines(rows: list[dict[str, object]]) -> list[str]:
    return [
        "    - "
        + f"`{row['entry_id']}`، {row['headword']} «{row['gloss']}»: "
        + "`"
        + " ".join(str(row["etymology"]).split())
        + "`"
        for row in rows
    ]


def apply_decision(
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
        f"- عائق: النوع={state}؛ يتطلب={decision['note']}؛",
    )
    if "النوع=TOOL-GAP" not in old_blocker:
        raise ValueError(f"{family}: live blocker is not TOOL-GAP")
    roots = list(decision.get("ready_roots") or [])
    if state == "LOAN-ROUTE-ISOLATED":
        scan_line = (
            "- مسحُ المعاني العربيّة: غير منطبق بعد ثبوت مسار القرض؛ "
            "لا تستعمل المروحة لصنع حكم نسب من عضو منقول."
        )
    elif state == "REFERRED":
        scan_line = (
            "- مسحُ المعاني العربيّة: محفوظ في بطاقة الحكم اللاحقة المحال إليها."
        )
    else:
        scan_line = (
            "- مسحُ المعاني العربيّة: "
            + (
                "اكتملت المروحة غير المقتطعة للمرشحين "
                + "، ".join(f"`{root}`" for root in roots)
                + "؛ المصادر مسماة في الملحق؛ ولا يصدر من اكتمالها حكم."
                if roots
                else "استنفد جرد المروحة؛ بقي العائق الحقيقي المسمى."
            )
        )
    section, old_scan = replace_required(section, SCAN, scan_line)
    overrides = list(decision.get("member_overrides") or [])
    filter_match = FILTER.search(section)
    if not filter_match:
        raise ValueError(f"{family}: missing live loan filter")
    old_filter = filter_match.group(0)
    if state == "LOAN-ROUTE-ISOLATED":
        filter_line = (
            "- المصفاة: عزل مسار قرض بمانح خارجي مسمى في حقل الاشتقاق "
            "للعضو نفسه؛ لا يدخل العضو رصيد النسب."
        )
    elif state == "CONTACT-ISOLATED":
        filter_line = (
            "- المصفاة: عزل ترجمة اقتراضية مسماة في المصدر؛ اتصال مصطلحي "
            "لا قرض لفظي ولا صلة نسب."
        )
    elif overrides:
        filter_line = (
            f"- المصفاة: عزل {len(overrides)} عضوًا بمانح خارجي مسمى؛ "
            "بقية الأسرة لا ترث حكمه وتبقى على عائقها الجاري."
        )
    else:
        filter_line = old_filter
    section = (
        section[: filter_match.start()]
        + filter_line
        + section[filter_match.end() :]
    )
    section, old_closure = replace_required(
        section, CLOSURE, f"- حالةُ الإغلاق: {state}"
    )
    verdict_line = (
        "- الحكم (استكشاف): LOANWORD؛ عزل مسار، لا صلة نسب."
        if decision["verdict"] == "LOANWORD"
        else f"- الحكم (استكشاف): غير صادر؛ {decision['note']}."
    )
    section, old_verdict = replace_required(section, VERDICT, verdict_line)
    appendix = [
        "",
        marker,
        f"- ملحق حملة المروحة اللاتينية القديمة، {DATE}:",
        f"  - المصير الجاري: `{state}`.",
        "  - جذور المروحة المكتملة ومصادرها: "
        + json.dumps(
            source_summary(roots, complete_roots),
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    ]
    if overrides:
        appendix.extend(
            [
                "  - أعضاء ذات مانح خارجي مسمى، معزولة بلا وراثة:",
                *member_override_lines(overrides),
            ]
        )
    if decision.get("references"):
        appendix.append(
            "  - الإحالة إلى الحكم الحي: "
            + json.dumps(
                decision["references"],
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    appendix.extend(
        [
            "  - الحقول الحاكمة السابقة محفوظة بلا محو:",
            f"    - `{old_blocker}`",
            f"    - `{old_scan}`",
            f"    - `{old_filter}`",
            f"    - `{old_closure}`",
            f"    - `{old_verdict}`",
        ]
    )
    return section.rstrip() + "\n" + "\n".join(appendix) + "\n", {
        "old_blocker": old_blocker,
        "old_scan": old_scan,
        "old_filter": old_filter,
        "old_closure": old_closure,
        "old_verdict": old_verdict,
    }


def revert_prior_campaign(section: str) -> str:
    """Restore the four live fields stored by a prior run, then drop its appendix."""
    marker = f"\n<!-- {MARKER}:"
    marker_at = section.find(marker)
    if marker_at < 0:
        return section
    stored: dict[str, str] = {}
    for key, label in (
        ("blocker", "عائق"),
        ("scan", "(?:مسحُ المعاني العربيّة|مسح المعاني العربية)"),
        ("filter", "المصفاة"),
        ("closure", "حالةُ الإغلاق"),
        ("verdict", "الحكم \\(استكشاف\\)"),
    ):
        match = re.search(
            rf"^    - `(- {label}:[^\n]*)`$",
            section[marker_at:],
            re.MULTILINE,
        )
        if not match and key == "filter":
            # Campaign v1 did not rewrite the filter, so the current live
            # filter is already the historical value to preserve.
            current = FILTER.search(section[:marker_at])
            if not current:
                raise ValueError(
                    f"cannot preserve prior filter: {section.splitlines()[0]}"
                )
            stored[key] = current.group(0)
            continue
        if not match:
            raise ValueError(
                f"cannot restore prior {key}: {section.splitlines()[0]}"
            )
        stored[key] = match.group(1)
    restored = section[:marker_at].rstrip() + "\n"
    restored, _ = replace_required(restored, BLOCKER, stored["blocker"])
    restored, _ = replace_required(restored, SCAN, stored["scan"])
    restored, _ = replace_required(restored, FILTER, stored["filter"])
    restored, _ = replace_required(restored, CLOSURE, stored["closure"])
    restored, _ = replace_required(restored, VERDICT, stored["verdict"])
    return restored + "\n"


def main() -> int:
    members, candidates = inventory()
    complete_roots = complete_root_inventory()
    text = READING.read_text(encoding="utf-8")
    base_parts = [
        revert_prior_campaign(section)
        for section in re.split(r"(?=^### )", text, flags=re.MULTILINE)
    ]
    base_text = "".join(base_parts)
    terminal = live_terminal_by_family(base_text)
    output: list[str] = []
    records: list[dict[str, object]] = []
    for section in base_parts:
        if not section.startswith("### ") or status.live_blocker(section) != "TOOL-GAP":
            output.append(section)
            continue
        heading = section.splitlines()[0]
        match = RANK_HEADING.match(heading)
        if not match:
            raise ValueError(f"unexpected live TOOL-GAP heading: {heading}")
        family = match.group("family")
        headword = match.group("headword")
        anchor = anchor_member(members[family], headword, section)
        decision = decide(
            family,
            anchor,
            members[family],
            candidates.get(family, []),
            complete_roots,
            terminal,
        )
        changed, history = apply_decision(
            section, family, decision, complete_roots
        )
        output.append(changed)
        records.append(
            {
                "title": heading,
                "family": family,
                "rank": int(match.group("rank")),
                "anchor_entry_id": anchor["entry_id"],
                "anchor_headword": anchor["headword"],
                "anchor_gloss": anchor["gloss"],
                "anchor_etymology": anchor["etymology"],
                **decision,
                "history": history,
            }
        )

    updated = unicodedata.normalize("NFC", "".join(output))
    if unicodedata.normalize("NFC", updated) != updated:
        raise ValueError("Old Latin reading is not NFC")
    atomic_write(READING, updated)
    positives = [row for row in records if row["positive"]]
    closures = [row for row in records if row["closure"]]
    held = [
        row
        for row in records
        if not row["positive"]
        and not row["closure"]
        and row["state"] != "REFERRED"
    ]
    payload = {
        "schema": "arabic-fan-campaign-old-latin-v1",
        "status": "LOCAL-THIRD-LENS-REVIEW-REQUIRED",
        "date": DATE,
        "language": "latin",
        "summary": {
            "cards_reviewed": len(records),
            "positive_connections": len(positives),
            "closures": len(closures),
            "closure_states": dict(
                sorted(Counter(row["state"] for row in closures).items())
            ),
            "held_states": dict(
                sorted(Counter(row["state"] for row in held).items())
            ),
            "historical_referrals": sum(
                row["state"] == "REFERRED" for row in records
            ),
            "member_loan_overrides": sum(
                len(row.get("member_overrides") or []) for row in records
            ),
        },
        "records": records,
    }
    atomic_write(CACHE, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    closure_text = "، ".join(
        f"{key}={value}"
        for key, value in payload["summary"]["closure_states"].items()
    ) or "لا شيء"
    held_text = "، ".join(
        f"{key}={value}"
        for key, value in payload["summary"]["held_states"].items()
    ) or "لا شيء"
    atomic_write(
        AUDIT,
        "\n".join(
            [
                "# حملة المروحة للاتينية القديمة، 2026-07-27",
                "",
                "دفعة محلية للمراجعة المضادة الثالثة. المانح المحتمل لا يغلق بطاقة؛ المانح الصريح وحده يعزل، ولا تغلق الأسرة المختلطة بسبب عضو واحد.",
                "",
                "## الرقمان المفصولان",
                "",
                f"- الصلات الموجبة: {len(positives)}.",
                f"- الإغلاقات: {len(closures)} ({closure_text}).",
                "",
                f"- بقي معلقًا بسببه الحقيقي: {held_text}.",
                f"- إحالات تاريخية لا أحكام ثانية: {payload['summary']['historical_referrals']}.",
                f"- أعضاء قروض معزولة داخل أسر مختلطة أو مغلقة: {payload['summary']['member_loan_overrides']}.",
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
