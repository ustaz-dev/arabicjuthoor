#!/usr/bin/env python3
"""Exhaust lane C's six ordered discovery inventories under sections 25–26.

The recovery inventories and Arabic lexical resources are opened read-only.
Writes are limited to lane-C-owned readings, lane_c_coverage.jsonl, and a
lane-C-prefixed audit.  No shared builder, proof-line tool, or Git command is
invoked here.

The queue no longer closes or silently excludes a form-of record.  A form is
read in its own right unless its base has a written card and an issued verdict;
this implementation takes the conservative path and reads the form itself.
Numerals, pronouns, and function words use the same standard as other words.
Proper names remain outside the statistical denominator and are handled by the
lane-C names inventory.  Distinct source entry IDs remain distinct even when
their displayed headword is identical.  Positive verdicts and final closures
receive full RECOVERY-v2 cards.  A member without an issued verdict receives
one machine coverage row and no prose card.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import lane_c_ie_discovery as discovery
import lane_c_ie_week2_coverage as week2
from lane_c_section26_rules import named_donor
from lane_c_section27_direction import (
    CLASS_NO_DIRECTION,
    CLASS_SEMITIC,
    LANGUAGES as DIRECTION_LANGUAGES,
    direction_decision,
    rewrite_card as rewrite_direction_card,
)


# Section 26 replaces the old substring loan marker for every future batch.
week2.contact_marker = named_donor


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
READINGS = ROOT / "04-cross-linguistic" / "readings"
DATA = ROOT / "04-cross-linguistic" / "data"
COVERAGE = DATA / "lane_c_coverage.jsonl"
MORPH_QUEUE = DATA / "lane_c_morphology_queue.jsonl"
AUDIT = ROOT / "05-audits" / "lane-c-2026-07-31-section26-continuation.md"
DATE = "2026-07-31"
MARKER_PREFIX = f"LANE-C-STANDING-QUEUE-{DATE}"

ENTRY_RE = re.compile(
    r"(?:kaikki_[^:`\s]+(?::\d{4}_\d{2}_\d{2})?|kaikki_[^:`\s]+):"
    r"\d+:[^`\s\]]+"
)

REQUIRED_CARD_FIELDS = (
    "- إصدارُ البروتوكول:",
    "- الكلمةُ في الفرع:",
    "- أقدمُ صورةٍ مستعادة:",
    "- الخطوةُ صفر (التعرية بصرف الفرع):",
    "- درجةُ المقارنة:",
    "- مسحُ المعاني العربيّة:",
    "- المقابلُ من اللسان:",
    "- مسارُ الصوت:",
    "- المعنى من قاموس الفرع:",
    "- المدار:",
    "- المصفاة:",
    "- فصلُ المتجانسات والاقتراض:",
    "- مؤشر اليتم:",
    "- إشعاع الأسرة في الفرع:",
    "- إشعاع الأسرة في العربية:",
    "- جسورُ الاسترداد المفحوصة:",
    "- حالةُ الإغلاق:",
    "- الحكم (استكشاف):",
    "- ملاحظات:",
)

COVERAGE_FIELDS = (
    "member_id",
    "language",
    "form",
    "branch_meaning",
    "non_issuance_reason",
    "batch_number",
)

FUNCTION_POS = {
    "article",
    "conj",
    "conjunction",
    "det",
    "determiner",
    "intj",
    "num",
    "numeral",
    "particle",
    "postp",
    "prep",
    "pron",
    "pronoun",
}


# A member may enter this map only after direct review of its published oldest
# stem, licensed route, one-step semantic orbit, and the two named old Arabic
# sources.  An empty map would be an honest result; no yield target populates it.
POSITIVE_ALLOWLIST: dict[str, dict[str, str]] = {
    "kaikki_persian_2026_07_23:3355:en-کوتاه-fa-adj-jfHj~prJ": {
        "kind": "root",
        "arabic_form": "قطع",
        "orbit": (
            "مدار 1: النتيجة؛ القِصَر هو انتهاء الامتداد بعد قطعه، "
            "وهو انتقال دلالي واحد لا مساواة معجمية مصطنعة"
        ),
        "rationale": (
            "الصورة الفارسية الوسطى المنشورة `kotāh` تحفظ مواضع "
            "المقارنة الثلاثة، ومسار `GUT-04` مرخص؛ لم يؤخذ حرف من "
            "لاحقة، ولسان العرب وتاج العروس يشهدان مدار القطع"
        ),
    },
    "kaikki_gothic_2026_07_23:13397:en-𐌼𐌿𐌻𐌳𐌰-got-noun-RwrrkGuA": {
        "kind": "root",
        "arabic_form": "بلد",
        "orbit": (
            "مدار 5: المكان؛ التراب والتربة مادة السطح الأرضي "
            "المتسع المصمت"
        ),
        "rationale": (
            "الساق الجرمانية الأولى المنشورة `*muldō` تحفظ `m-l-d`، "
            "ومسار `LAB-04` مرخص، وهذا شاهد قوطي مستقل يثلث قراءة "
            "النوردية `mold` من غير أن يرث حكمها"
        ),
    },
    "kaikki_old_norse_2026_07_23:553:en-drepa-non-verb-0Xm~Y4pZ": {
        "kind": "root",
        "arabic_form": "ضرب",
        "orbit": (
            "مباشر في إيقاع الضرب والدفع على الشيء؛ معنى الفرع "
            "to beat/to hit يلتقي بالفعل العربي المسمى"
        ),
        "rationale": (
            "الساق الجرمانية الأولى `*drepaną` والجذر الهندوأوروبي "
            "`*dhrebh-` ينشران معنى الضرب ويحفظان هيكل المسار المرخص؛ "
            "لا لاحقة سطحية تمد المقارنة، والمصدران العربيان حاضران"
        ),
    },
}


def nfc(value: str | None) -> str:
    return unicodedata.normalize("NFC", value or "")


def chunks(values: list[Any], size: int) -> Iterable[list[Any]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def used_entry_ids(path: Path) -> set[str]:
    """Return only the member identity in each card's branch-word field.

    Source citations and cross-references elsewhere in a card are not coverage
    for the cited member.
    """

    result: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("- الكلمةُ في الفرع:"):
                result.update(ENTRY_RE.findall(line))
    return result


def coverage_entry_ids(language: str | None = None) -> set[str]:
    """Return member identities already registered in Lane C coverage."""

    if not COVERAGE.exists():
        return set()
    result: set[str] = set()
    with COVERAGE.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if tuple(row.keys()) != COVERAGE_FIELDS:
                raise RuntimeError(
                    f"{COVERAGE}:{line_number}: invalid coverage fields"
                )
            if language is not None and row["language"] != language:
                continue
            entry_id = nfc(str(row["member_id"]))
            if entry_id in result:
                raise RuntimeError(
                    f"{COVERAGE}:{line_number}: duplicate {entry_id}"
                )
            result.add(entry_id)
    return result


def non_issuance_reason(card: str) -> str:
    """Extract the explicit open state and any detailed non-verdict reason."""

    state_match = re.search(r"(?m)^- حالةُ الإغلاق:\s*(.+)$", card)
    verdict_match = re.search(r"(?m)^- الحكم \(استكشاف\):\s*(.+)$", card)
    parts: list[str] = []
    if state_match:
        parts.append(state_match.group(1).strip().rstrip("."))
    if verdict_match:
        verdict = verdict_match.group(1).strip().rstrip(".")
        if verdict not in {"غير صادر", "لا حكم"}:
            parts.append(verdict)
    return "؛ ".join(dict.fromkeys(parts)) or "الحكم غير صادر"


def coverage_row(
    language: week2.Language,
    member: dict[str, Any],
    card: str,
    batch_number: int,
) -> dict[str, Any]:
    reason = non_issuance_reason(card)
    if member.get("form_of"):
        targets = "، ".join(member.get("form_targets", ())) or "أصل غير مسمى"
        reason = (
            "OPEN-FORM-SELF-JUDGMENT؛ لم تغلق الصورة بالإحالة؛ "
            f"الأصل المنشور: {targets}؛ الحكم غير صادر"
        )
        if member.get("is_function_word"):
            reason += (
                "؛ SECTION26-NONLEXICAL-PRIORITY؛ "
                "قورن بالمعيار نفسه"
            )
    elif member.get("is_function_word"):
        reason = (
            f"{reason}؛ SECTION26-NONLEXICAL-INCLUDED؛ "
            "قورن بالمعيار نفسه ولم يستبعد من الاكتشاف"
        )
    return {
        "member_id": member["entry_id"],
        "language": language.key,
        "form": member["headword"],
        "branch_meaning": member["gloss"] or "(غير مسجل في المصدر)",
        "non_issuance_reason": reason,
        "batch_number": batch_number,
    }


def render_directional_card(
    language: week2.Language,
    member: dict[str, Any],
    ordinal: int,
) -> tuple[str, str]:
    """Render one future queue member under sections 26 and 27.

    The inherited week-2 renderer knows only open/positive/loan.  Section 27
    adds a kept transmission outcome and reopens any old contact label whose
    donor or incoming direction is not established for this member and sense.
    """

    decision = direction_decision(
        next(
            language_rule
            for language_rule in DIRECTION_LANGUAGES
            if language_rule.key == language.key
        ),
        member["entry_id"],
        member["etymology"],
    )
    original_marker = week2.contact_marker
    if decision["direction_class"] == CLASS_NO_DIRECTION:
        # A no-direction record must receive the ordinary comparison, not a
        # closure manufactured by the legacy substring screen.
        week2.contact_marker = lambda _language, _etymology: ""
    try:
        card, outcome = week2.render_card(language, member, ordinal)
    finally:
        week2.contact_marker = original_marker
    if outcome != "closure":
        return card, outcome

    decision = {
        **decision,
        "record_id": member["entry_id"],
        "direction_source": (
            f"{language.source_label}؛ `{member['entry_id']}`؛ "
            "حقل `etymology`"
        ),
    }
    card = rewrite_direction_card(card, decision, language.source_label)
    if decision["direction_class"] == CLASS_SEMITIC:
        return card, "transmission"
    return card, "closure"


def append_coverage_rows(
    rows: list[dict[str, Any]],
    known_ids: set[str],
) -> None:
    if not rows:
        return
    batch_ids: set[str] = set()
    for row in rows:
        if tuple(row.keys()) != COVERAGE_FIELDS:
            raise RuntimeError(
                f"invalid coverage fields for {row.get('member_id')}"
            )
        entry_id = nfc(str(row["member_id"]))
        if entry_id in known_ids or entry_id in batch_ids:
            raise RuntimeError(f"duplicate coverage identity: {entry_id}")
        batch_ids.add(entry_id)
    with COVERAGE.open("a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
                + "\n"
            )
    known_ids.update(batch_ids)


def queue_members(
    con: Any,
    language: week2.Language,
    used_ids: set[str],
    *,
    function_forms_only: bool = False,
) -> list[dict[str, Any]]:
    """Return every unseen member in the established week-two queue."""

    extra_where = ""
    extra_params: list[str] = []
    if function_forms_only:
        function_marks = ",".join("?" for _ in FUNCTION_POS)
        extra_where = (
            "\n          AND e.form_of = 1"
            f"\n          AND lower(e.pos) IN ({function_marks})"
        )
        extra_params.extend(sorted(FUNCTION_POS))
    rows = con.execute(
        f"""
        SELECT
            e.entry_id,
            e.headword,
            e.romanization,
            e.pos,
            e.gloss,
            e.etymology,
            e.source_stratum,
            e.source_scope_note,
            e.loan_hint,
            e.form_of,
            e.form_targets_json,
            e.selected_input,
            e.original_skeleton,
            e.romanization_skeleton,
            e.skeleton,
            e.licensed_candidate_count,
            fm.family_id,
            fm.role,
            fm.link_types_json,
            f.member_count,
            f.lemma_count
        FROM entries e
        JOIN family_members fm ON fm.entry_id = e.entry_id
        JOIN families f ON f.family_id = fm.family_id
        WHERE e.language = ?
          AND (e.alternative_of = 0 OR e.form_of = 1)
          {extra_where}
        """,
        (language.key, *extra_params),
    ).fetchall()
    members: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        entry_id = nfc(row["entry_id"])
        headword = nfc(row["headword"])
        pos = nfc(row["pos"])
        if entry_id in used_ids or entry_id in seen:
            continue
        if pos.casefold() in discovery.BAD_POS:
            continue
        if not headword or headword.startswith("<"):
            continue
        seen.add(entry_id)
        members.append(
            {
                "entry_id": entry_id,
                "source_ordinal": week2.source_ordinal(entry_id),
                "headword": headword,
                "romanization": nfc(row["romanization"]),
                "pos": pos,
                "gloss": nfc(row["gloss"]),
                "etymology": nfc(row["etymology"]),
                "source_stratum": nfc(row["source_stratum"]),
                "source_scope_note": nfc(row["source_scope_note"]),
                "loan_hint": bool(row["loan_hint"]),
                "form_of": bool(row["form_of"]),
                "form_targets": json.loads(
                    row["form_targets_json"] or "[]"
                ),
                "is_function_word": pos.casefold() in FUNCTION_POS,
                "selected_input": nfc(row["selected_input"]),
                "original_skeleton": nfc(row["original_skeleton"]),
                "romanization_skeleton": nfc(row["romanization_skeleton"]),
                "skeleton": nfc(row["skeleton"]),
                "licensed_candidate_count": int(
                    row["licensed_candidate_count"] or 0
                ),
                "family_id": nfc(row["family_id"]),
                "family_role": nfc(row["role"]),
                "family_links": json.loads(row["link_types_json"] or "[]"),
                "family_member_count": int(row["member_count"]),
                "family_lemma_count": int(row["lemma_count"]),
            }
        )
    members.sort(
        key=lambda item: (
            not item["is_function_word"],
            item["source_ordinal"],
            item["entry_id"],
        )
    )
    return members


def issued_referral_targets(
    con: Any,
    language: week2.Language,
    reading_text: str,
) -> set[str]:
    """Return base spellings that section 26 permits as referral targets."""

    import lane_c_section26_reopen as section26

    issued_ids = {
        card["entry_id"]
        for card in section26.parse_cards(reading_text)
        if section26.issued_verdict(card["verdict"])
    }
    bases: dict[str, list[str]] = {}
    for row in con.execute(
        """
        SELECT entry_id, headword
        FROM entries
        WHERE language = ? AND form_of = 0
        """,
        (language.key,),
    ):
        bases.setdefault(nfc(row["headword"]), []).append(
            nfc(row["entry_id"])
        )
    return {
        headword
        for headword, entry_ids in bases.items()
        if len(entry_ids) == 1 and entry_ids[0] in issued_ids
    }


def stream_queue_member_chunks(
    con: Any,
    language: week2.Language,
    used_ids: set[str],
    reading_text: str,
    batch_size: int,
) -> Iterable[list[dict[str, Any]]]:
    """Stream the morphology queue in stable order without materializing it."""

    function_sql = ",".join(
        "'" + pos.replace("'", "''") + "'" for pos in sorted(FUNCTION_POS)
    )
    ordinal_sql = (
        "CAST(substr(e.entry_id, instr(e.entry_id, ':') + 1, "
        "instr(substr(e.entry_id, instr(e.entry_id, ':') + 1), ':') - 1) "
        "AS INTEGER)"
    )
    referral_targets = issued_referral_targets(
        con,
        language,
        reading_text,
    )
    rows = con.execute(
        f"""
        SELECT
            e.entry_id,
            e.headword,
            e.romanization,
            e.pos,
            e.gloss,
            e.etymology,
            e.source_stratum,
            e.source_scope_note,
            e.loan_hint,
            e.form_of,
            e.form_targets_json,
            e.form_resolution_status,
            e.selected_input,
            e.original_skeleton,
            e.romanization_skeleton,
            e.skeleton,
            e.licensed_candidate_count,
            fm.family_id,
            fm.role,
            fm.link_types_json,
            f.member_count,
            f.lemma_count
        FROM entries e
        JOIN family_members fm ON fm.entry_id = e.entry_id
        JOIN families f ON f.family_id = fm.family_id
        WHERE e.language = ?
          AND e.form_of = 1
        ORDER BY
          CASE WHEN lower(e.pos) IN ({function_sql}) THEN 0 ELSE 1 END,
          {ordinal_sql},
          e.entry_id
        """,
        (language.key,),
    )
    member_chunk: list[dict[str, Any]] = []
    for row in rows:
        entry_id = nfc(row["entry_id"])
        headword = nfc(row["headword"])
        pos = nfc(row["pos"])
        if entry_id in used_ids:
            continue
        if pos.casefold() in discovery.BAD_POS:
            continue
        if not headword or headword.startswith("<"):
            continue
        form_targets = [
            nfc(target)
            for target in json.loads(row["form_targets_json"] or "[]")
        ]
        member_chunk.append(
            {
                "entry_id": entry_id,
                "source_ordinal": week2.source_ordinal(entry_id),
                "headword": headword,
                "romanization": nfc(row["romanization"]),
                "pos": pos,
                "gloss": nfc(row["gloss"]),
                "etymology": nfc(row["etymology"]),
                "source_stratum": nfc(row["source_stratum"]),
                "source_scope_note": nfc(row["source_scope_note"]),
                "loan_hint": bool(row["loan_hint"]),
                "form_of": True,
                "form_targets": form_targets,
                "is_function_word": pos.casefold() in FUNCTION_POS,
                "referral_eligible": (
                    row["form_resolution_status"] == "linked"
                    and any(
                        target in referral_targets
                        for target in form_targets
                    )
                ),
                "selected_input": nfc(row["selected_input"]),
                "original_skeleton": nfc(row["original_skeleton"]),
                "romanization_skeleton": nfc(row["romanization_skeleton"]),
                "skeleton": nfc(row["skeleton"]),
                "licensed_candidate_count": int(
                    row["licensed_candidate_count"] or 0
                ),
                "family_id": nfc(row["family_id"]),
                "family_role": nfc(row["role"]),
                "family_links": json.loads(row["link_types_json"] or "[]"),
                "family_member_count": int(row["member_count"]),
                "family_lemma_count": int(row["lemma_count"]),
            }
        )
        if len(member_chunk) == batch_size:
            yield member_chunk
            member_chunk = []
    if member_chunk:
        yield member_chunk


class SemanticScorer:
    """The established lexical-overlap score, with its corpus cached once."""

    def __init__(self, definitions: dict[str, str]) -> None:
        self.root_tokens: dict[str, set[str]] = {}
        self.document_frequency: Counter[str] = Counter()
        for root, definition in definitions.items():
            tokens = {
                token.lower()
                for token in discovery.TOKEN_RE.findall(definition)
                if token.lower() not in discovery.ENGLISH_STOP_WORDS
            }
            self.root_tokens[root] = tokens
            self.document_frequency.update(tokens)
        self.document_count = len(self.root_tokens)

    def score(self, gloss: str, kind: str, arabic_form: str) -> float:
        if kind != "root" or not gloss:
            return 0.0
        definition_tokens = self.root_tokens.get(arabic_form)
        if not definition_tokens:
            return 0.0
        gloss_tokens = {
            token.lower()
            for token in discovery.TOKEN_RE.findall(gloss)
            if token.lower() not in discovery.ENGLISH_STOP_WORDS
        }
        common = gloss_tokens & definition_tokens
        if not common:
            return 0.0

        def weight(token: str) -> float:
            return math.log(
                (self.document_count + 1)
                / (self.document_frequency[token] + 1)
            ) + 1.0

        numerator = sum(weight(token) for token in common)
        gloss_weight = sum(weight(token) for token in gloss_tokens)
        definition_weight = sum(weight(token) for token in definition_tokens)
        return numerator / math.sqrt(max(gloss_weight * definition_weight, 1.0))


def attach_auxiliary_data(
    con: Any,
    members: list[dict[str, Any]],
    source_counts: dict[str, dict[str, int]],
    scorer: SemanticScorer,
) -> None:
    """Attach zero-step rows and licensed candidates using batched SQL."""

    by_id = {member["entry_id"]: member for member in members}
    for member in members:
        member["zero_step"] = []
        member["tested_candidates"] = []
    ids = list(by_id)
    for id_chunk in chunks(ids, 450):
        marks = ",".join("?" for _ in id_chunk)
        zero_rows = con.execute(
            f"""
            SELECT entry_id, rule_id, surface_form, comparison_form,
                   surface_skeleton, comparison_skeleton, sources_json
            FROM zero_step_forms
            WHERE entry_id IN ({marks})
            ORDER BY entry_id, rule_id, comparison_form
            """,
            id_chunk,
        ).fetchall()
        for row in zero_rows:
            member = by_id[nfc(row["entry_id"])]
            member["zero_step"].append(
                {
                    "rule_id": nfc(row["rule_id"]),
                    "surface_form": nfc(row["surface_form"]),
                    "comparison_form": nfc(row["comparison_form"]),
                    "surface_skeleton": nfc(row["surface_skeleton"]),
                    "comparison_skeleton": nfc(row["comparison_skeleton"]),
                    "sources": json.loads(row["sources_json"] or "[]"),
                }
            )

        candidate_rows = con.execute(
            f"""
            SELECT c.entry_id, c.kind, c.form, c.status, c.rule_ids_json,
                   c.route_flag, a.reading
            FROM candidates c
            LEFT JOIN arabic_forms a
              ON a.form = c.form AND a.kind = c.kind
            WHERE c.entry_id IN ({marks})
              AND c.status = 'licensed'
              AND c.route_flag = 0
            """,
            id_chunk,
        ).fetchall()
        candidates_by_id: dict[str, list[dict[str, Any]]] = {
            entry_id: [] for entry_id in id_chunk
        }
        for row in candidate_rows:
            entry_id = nfc(row["entry_id"])
            member = by_id[entry_id]
            kind = nfc(row["kind"])
            arabic_form = nfc(row["form"])
            candidate = {
                "entry_id": entry_id,
                "gloss": member["gloss"],
                "kind": kind,
                "arabic_form": arabic_form,
                "arabic_reading": nfc(row["reading"]),
                "rule_ids": json.loads(row["rule_ids_json"] or "[]"),
                "candidate_status": nfc(row["status"]),
                "route_flag": bool(row["route_flag"]),
                "classical_source_counts": source_counts.get(arabic_form, {}),
                "semantic_score": round(
                    scorer.score(member["gloss"], kind, arabic_form),
                    6,
                ),
            }
            candidates_by_id[entry_id].append(candidate)
        for entry_id, candidates in candidates_by_id.items():
            unique: dict[tuple[str, str], dict[str, Any]] = {}
            for candidate in candidates:
                key = (candidate["kind"], candidate["arabic_form"])
                old = unique.get(key)
                if old is None or (
                    candidate["semantic_score"],
                    -len(candidate["rule_ids"]),
                ) > (
                    old["semantic_score"],
                    -len(old["rule_ids"]),
                ):
                    unique[key] = candidate
            by_id[entry_id]["tested_candidates"] = sorted(
                unique.values(),
                key=lambda item: (
                    item["semantic_score"],
                    item["kind"] == "root",
                    -len(item["rule_ids"]),
                    item["arabic_form"],
                ),
                reverse=True,
            )[:24]


def display_member(member: dict[str, Any]) -> str:
    display = member["headword"]
    if member["romanization"]:
        display += f" ({member['romanization']})"
    return display


def validate_card(card: str, entry_id: str) -> None:
    missing = [field for field in REQUIRED_CARD_FIELDS if field not in card]
    if missing:
        raise RuntimeError(f"{entry_id}: missing card fields: {missing}")
    if card.count(entry_id) != 1:
        raise RuntimeError(
            f"{entry_id}: expected one explicit identity in card, "
            f"found {card.count(entry_id)}"
        )


def batch_marker(
    language: week2.Language,
    batch_number: int,
    first: dict[str, Any],
    last: dict[str, Any],
) -> str:
    return (
        f"{MARKER_PREFIX}:{language.key}:{batch_number}:"
        f"{first['source_ordinal']}-{last['source_ordinal']}"
    )


def existing_batch_count(text: str, language_key: str) -> int:
    """Count this language's standing-queue batches across run dates."""

    pattern = re.compile(
        r"<!-- LANE-C-STANDING-QUEUE-\d{4}-\d{2}-\d{2}:"
        + re.escape(language_key)
        + r":\d+:"
    )
    return len(pattern.findall(text))


def append_reading_batch(
    language: week2.Language,
    members: list[dict[str, Any]],
    batch_number: int,
    complete_before: int,
    remaining_after: int,
    known_coverage_ids: set[str],
) -> dict[str, int]:
    path = READINGS / language.reading_file
    first = members[0]
    last = members[-1]
    marker = batch_marker(language, batch_number, first, last)
    with path.open("rb") as handle:
        handle.seek(0, 2)
        handle.seek(max(0, handle.tell() - 8192))
        old_tail = handle.read().decode("utf-8", errors="ignore")
    if marker in old_tail:
        raise RuntimeError(f"duplicate batch marker in {path}: {marker}")

    counts = {
        "members": 0,
        "cards": 0,
        "positive": 0,
        "transmission": 0,
        "closures": 0,
        "open": 0,
    }
    card_texts: list[str] = []
    coverage_rows: list[dict[str, Any]] = []
    for offset, member in enumerate(members, 1):
        ordinal = complete_before + offset
        card, outcome = render_directional_card(language, member, ordinal)
        card = card.replace(
            f"(التغطية الكاملة ج2، {ordinal})",
            f"(الطابور الدائم ج، {ordinal})",
            1,
        )
        counts["members"] += 1
        if outcome == "open":
            coverage_rows.append(
                coverage_row(language, member, card, batch_number)
            )
            counts["open"] += 1
        else:
            validate_card(card, member["entry_id"])
            card_texts.append(card)
            counts["cards"] += 1
            counts["closures" if outcome == "closure" else outcome] += 1

    append_coverage_rows(coverage_rows, known_coverage_ids)

    start_text = f"{display_member(first)}؛ `{first['entry_id']}`"
    end_text = f"{display_member(last)}؛ `{last['entry_id']}`"
    section = nfc(
        f"""

<!-- {marker} -->
## الطابور الدائم: {language.source_label}، الدفعة {batch_number}

- موضع الدفعة: بدأت من {start_text} وانتهت عند {end_text}؛ بقي في الجرد بعدها {remaining_after}.
- المقام: {counts['members']} عضوًا من جرد الاكتشاف دخلوا بترتيب الطابور؛ بقيت بطاقة RECOVERY-v2 كاملة لـ{counts['cards']} صلة أو انتقال أو إغلاق، وسُجّل {counts['open']} عضوًا بلا حكم في `lane_c_coverage.jsonl`.
- انتقالات القسم 27 المحفوظة خارج بسط الإرث: {counts['transmission']}.
- الرقمان المفصولان: {counts['positive']} صلة موجبة؛ {counts['closures']} إغلاقًا.
- خط البرهان مجمد، ولم يُنشأ صف صوتي أو يُشغّل باني مشترك.

<!-- RECOVERY-PROTOCOL-v2 -->
<!-- RADIATION-FIELDS-v1 -->
{''.join(card_texts)}
<!-- /{marker} -->
"""
    )
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(section)
    return counts


def append_audit_batch(
    language: week2.Language,
    members: list[dict[str, Any]],
    batch_number: int,
    counts: dict[str, int],
    remaining_after: int,
) -> None:
    first = members[0]
    last = members[-1]
    text = nfc(
        f"""

## {language.source_label}: الدفعة {batch_number}

سطر الموضع: بدأت الدفعة من {display_member(first)} (`{first['entry_id']}`) وانتهت عند {display_member(last)} (`{last['entry_id']}`)، وبقي في الجرد بعدها {remaining_after}.

الأعضاء المفحوصة: {counts['members']}. البطاقات الكاملة المكتوبة: {counts['cards']}. أسطر التغطية للحكم غير الصادر: {counts['open']}. انتقالات القسم 27 المحفوظة خارج بسط الإرث: {counts['transmission']}.

الرقمان المفصولان: {counts['positive']} صلة موجبة؛ {counts['closures']} إغلاقًا.
"""
    )
    with AUDIT.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def append_language_complete(
    language: week2.Language,
    examined: int,
) -> None:
    marker = f"<!-- {MARKER_PREFIX}:LANGUAGE-COMPLETE:{language.key} -->"
    old = AUDIT.read_text(encoding="utf-8")
    if marker in old:
        if examined == 0:
            return
        marker = (
            f"<!-- {MARKER_PREFIX}:LANGUAGE-RECOMPLETE:"
            f"{language.key}:{examined} -->"
        )
        if marker in old:
            return
        heading = f"إعادة فراغ جرد {language.source_label}"
    else:
        heading = f"فراغ جرد {language.source_label}"
    text = nfc(
        f"""

{marker}
## {heading}

قيس الباقي بعد آخر دفعة فكان صفرًا. فُحص في تشغيل الطابور الدائم هذا {examined} عضوًا جديدًا، ولا عضو غير مقروء باق في الجرد المحدد.
"""
    )
    with AUDIT.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def inventory_plan(
    languages: tuple[week2.Language, ...] | list[week2.Language] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    covered_ids = coverage_entry_ids()
    selected = languages if languages is not None else week2.LANGUAGES
    for language in selected:
        path = READINGS / language.reading_file
        con = week2.ro_connection(language.db_path)
        try:
            result[language.key] = queue_members(
                con,
                language,
                used_entry_ids(path) | covered_ids,
            )
        finally:
            con.close()
    return result


def print_plan(
    plan: dict[str, list[dict[str, Any]]],
    languages: tuple[week2.Language, ...] | list[week2.Language] | None = None,
) -> None:
    total = 0
    selected = languages if languages is not None else week2.LANGUAGES
    for language in selected:
        members = plan[language.key]
        total += len(members)
        first = members[0]["entry_id"] if members else "EMPTY"
        last = members[-1]["entry_id"] if members else "EMPTY"
        print(
            f"{language.key}\tremaining={len(members)}"
            f"\tfirst={first}\tlast={last}"
        )
    print(f"TOTAL\tremaining={total}")


def print_morphology_manifest_plan() -> None:
    """Print the section-26 queue without materializing 800k Latin rows."""

    if not MORPH_QUEUE.exists():
        raise RuntimeError(f"missing morphology queue: {MORPH_QUEUE}")
    total = 0
    with MORPH_QUEUE.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            remaining = int(row["pending"])
            total += remaining
            print(
                f"{row['language']}\tremaining={remaining}"
                f"\tfirst={row['first_pending_member_id'] or 'EMPTY'}"
                f"\tlast={row['last_pending_member_id'] or 'EMPTY'}"
                f"\tnonlexical_priority={row['nonlexical_priority']}"
            )
    print(f"TOTAL\tremaining={total}")


def morphology_manifest_row(language_key: str) -> dict[str, Any]:
    with MORPH_QUEUE.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row["language"] == language_key:
                return row
    raise RuntimeError(f"missing morphology manifest row: {language_key}")


def update_morphology_manifest(
    language: week2.Language,
    members: list[dict[str, Any]],
    remaining_after: int,
    next_member_id: str,
) -> None:
    rows = [
        json.loads(line)
        for line in MORPH_QUEUE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    target = next(
        (row for row in rows if row["language"] == language.key),
        None,
    )
    if target is None:
        raise RuntimeError(
            f"missing morphology manifest row: {language.key}"
        )
    referral_examined = sum(
        bool(member.get("referral_eligible")) for member in members
    )
    void_examined = len(members) - referral_examined
    target["already_recorded"] = int(target["already_recorded"]) + len(
        members
    )
    target["referral_eligible"] = (
        int(target["referral_eligible"]) - referral_examined
    )
    target["void_closure_prevented"] = (
        int(target["void_closure_prevented"]) - void_examined
    )
    target["nonlexical_priority"] = int(
        target["nonlexical_priority"]
    ) - sum(bool(member["is_function_word"]) for member in members)
    target["pending"] = remaining_after
    target["first_pending_member_id"] = next_member_id
    if remaining_after == 0:
        target["last_pending_member_id"] = ""
    if (
        target["referral_eligible"] < 0
        or target["void_closure_prevented"] < 0
        or target["nonlexical_priority"] < 0
        or target["pending"] < 0
    ):
        raise RuntimeError(
            f"negative morphology manifest count: {language.key}"
        )
    if (
        target["already_recorded"] + target["pending"]
        != target["discovery_form_records"]
    ):
        raise RuntimeError(
            f"morphology manifest coverage imbalance: {language.key}"
        )
    if (
        target["referral_eligible"]
        + target["void_closure_prevented"]
        != target["pending"]
    ):
        raise RuntimeError(
            f"morphology manifest closure imbalance: {language.key}"
        )
    text_out = "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in rows
    )
    temporary = MORPH_QUEUE.with_suffix(".jsonl.lane-c-tmp")
    temporary.write_text(text_out, encoding="utf-8", newline="\n")
    temporary.replace(MORPH_QUEUE)


def print_review(
    plan: dict[str, list[dict[str, Any]]],
    count: int,
    batch_size: int,
    languages: tuple[week2.Language, ...] | list[week2.Language] | None = None,
) -> None:
    definitions = discovery.load_arabic_english_definitions()
    source_counts = discovery.load_classical_source_counts()
    scorer = SemanticScorer(definitions)
    selected = languages if languages is not None else week2.LANGUAGES
    for language in selected:
        ranked: list[tuple[float, dict[str, Any], dict[str, Any]]] = []
        con = week2.ro_connection(language.db_path)
        try:
            for member_chunk in chunks(plan[language.key], batch_size):
                attach_auxiliary_data(
                    con,
                    member_chunk,
                    source_counts,
                    scorer,
                )
                for member in member_chunk:
                    if week2.contact_marker(
                        language.key,
                        member["etymology"],
                    ):
                        continue
                    for candidate in member["tested_candidates"]:
                        counts = candidate["classical_source_counts"]
                        if (
                            candidate["kind"] == "root"
                            and candidate["semantic_score"] > 0
                            and counts.get("لسان العرب لابن منظور", 0)
                            and counts.get("تاج العروس لمرتضى الزبيدي", 0)
                        ):
                            ranked.append(
                                (
                                    candidate["semantic_score"],
                                    member,
                                    candidate,
                                )
                            )
                            break
        finally:
            con.close()
        ranked.sort(
            key=lambda item: (
                item[0],
                -len(item[2]["rule_ids"]),
                bool(item[1]["etymology"]),
            ),
            reverse=True,
        )
        print(
            f"\nREVIEW {language.key}: screened={len(ranked)} "
            f"showing={min(count, len(ranked))}"
        )
        for score, member, candidate in ranked[:count]:
            rules = "+".join(candidate["rule_ids"]) or "IDENTITY"
            print(
                "\t".join(
                    (
                        f"score={score:.6f}",
                        member["entry_id"],
                        display_member(member),
                        f"gloss={week2.clean(member['gloss'], 180)}",
                        f"oldest={week2.clean(member['etymology'], 260)}",
                        f"skeleton={member['skeleton']}",
                        f"root={candidate['arabic_form']}",
                        f"reading={week2.clean(candidate['arabic_reading'], 180)}",
                        f"rules={rules}",
                    )
                )
            )


def run_queue(
    plan: dict[str, list[dict[str, Any]]],
    batch_size: int,
    max_batches: int | None,
    languages: tuple[week2.Language, ...] | list[week2.Language] | None = None,
) -> None:
    week2.POSITIVE_ALLOWLIST.update(POSITIVE_ALLOWLIST)
    definitions = discovery.load_arabic_english_definitions()
    source_counts = discovery.load_classical_source_counts()
    scorer = SemanticScorer(definitions)
    known_coverage_ids = coverage_entry_ids()
    batches_written = 0
    selected = languages if languages is not None else week2.LANGUAGES
    for language in selected:
        pending = plan[language.key]
        path = READINGS / language.reading_file
        existing_text = path.read_text(encoding="utf-8")
        complete_before_language = len(
            used_entry_ids(path) | coverage_entry_ids(language.key)
        )
        prior_batches = existing_batch_count(existing_text, language.key)
        processed = 0
        if not pending:
            append_language_complete(language, 0)
            print(f"{language.key}\tEMPTY", flush=True)
            continue
        con = week2.ro_connection(language.db_path)
        try:
            for member_chunk in chunks(pending, batch_size):
                if max_batches is not None and batches_written >= max_batches:
                    return
                attach_auxiliary_data(
                    con,
                    member_chunk,
                    source_counts,
                    scorer,
                )
                batch_number = prior_batches + 1
                remaining_after = len(pending) - processed - len(member_chunk)
                counts = append_reading_batch(
                    language,
                    member_chunk,
                    batch_number,
                    complete_before_language + processed,
                    remaining_after,
                    known_coverage_ids,
                )
                append_audit_batch(
                    language,
                    member_chunk,
                    batch_number,
                    counts,
                    remaining_after,
                )
                processed += len(member_chunk)
                prior_batches += 1
                batches_written += 1
                print(
                    f"{language.key}\tbatch={batch_number}"
                    f"\tmembers={counts['members']}"
                    f"\tcards={counts['cards']}"
                    f"\tcoverage={counts['open']}"
                    f"\tpositive={counts['positive']}"
                    f"\ttransmission={counts['transmission']}"
                    f"\tclosures={counts['closures']}"
                    f"\tremaining={remaining_after}",
                    flush=True,
                )
        finally:
            con.close()
        append_language_complete(language, processed)


def run_streaming_language(
    language: week2.Language,
    batch_size: int,
    max_batches: int | None,
) -> None:
    """Run one large morphology queue with bounded resident memory."""

    week2.POSITIVE_ALLOWLIST.update(POSITIVE_ALLOWLIST)
    definitions = discovery.load_arabic_english_definitions()
    source_counts = discovery.load_classical_source_counts()
    scorer = SemanticScorer(definitions)
    known_coverage_ids = coverage_entry_ids()
    path = READINGS / language.reading_file
    existing_text = path.read_text(encoding="utf-8")
    language_coverage_ids = coverage_entry_ids(language.key)
    used_ids = used_entry_ids(path) | language_coverage_ids
    complete_before_language = len(used_ids)
    prior_batches = existing_batch_count(existing_text, language.key)
    pending_before = int(
        morphology_manifest_row(language.key)["pending"]
    )
    if pending_before == 0:
        append_language_complete(language, 0)
        print(f"{language.key}\tEMPTY", flush=True)
        return

    con = week2.ro_connection(language.db_path)
    processed = 0
    batches_written = 0
    try:
        iterator = iter(
            stream_queue_member_chunks(
                con,
                language,
                used_ids,
                existing_text,
                batch_size,
            )
        )
        current = next(iterator, None)
        while current is not None:
            following = next(iterator, None)
            if (
                max_batches is not None
                and batches_written >= max_batches
            ):
                break
            attach_auxiliary_data(
                con,
                current,
                source_counts,
                scorer,
            )
            batch_number = prior_batches + 1
            remaining_after = (
                pending_before - processed - len(current)
            )
            if remaining_after < 0:
                raise RuntimeError(
                    f"manifest undercounts streamed queue: {language.key}"
                )
            counts = append_reading_batch(
                language,
                current,
                batch_number,
                complete_before_language + processed,
                remaining_after,
                known_coverage_ids,
            )
            append_audit_batch(
                language,
                current,
                batch_number,
                counts,
                remaining_after,
            )
            update_morphology_manifest(
                language,
                current,
                remaining_after,
                following[0]["entry_id"] if following else "",
            )
            processed += len(current)
            prior_batches += 1
            batches_written += 1
            print(
                f"{language.key}\tbatch={batch_number}"
                f"\tmembers={counts['members']}"
                f"\tcards={counts['cards']}"
                f"\tcoverage={counts['open']}"
                f"\tpositive={counts['positive']}"
                f"\ttransmission={counts['transmission']}"
                f"\tclosures={counts['closures']}"
                f"\tremaining={remaining_after}",
                flush=True,
            )
            current = following
    finally:
        con.close()
    if processed == pending_before:
        append_language_complete(language, processed)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--plan", action="store_true")
    mode.add_argument("--review", type=int, metavar="N")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--max-batches", type=int)
    parser.add_argument(
        "--stream",
        action="store_true",
        help="stream one large language queue with bounded memory",
    )
    parser.add_argument(
        "--language",
        choices=tuple(language.key for language in week2.LANGUAGES),
        help="materialize and run only one language queue",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.batch_size < 1 or args.batch_size > 900:
        raise SystemExit("--batch-size must be between 1 and 900")
    if args.stream and not args.language:
        raise SystemExit("--stream requires --language")
    if args.review is None and not args.run:
        print_morphology_manifest_plan()
        return 0
    languages = (
        tuple(
            language
            for language in week2.LANGUAGES
            if language.key == args.language
        )
        if args.language
        else week2.LANGUAGES
    )
    if args.stream:
        if not args.run:
            raise SystemExit("--stream requires --run")
        run_streaming_language(
            languages[0],
            args.batch_size,
            args.max_batches,
        )
        return 0
    plan = inventory_plan(languages)
    if args.review is not None:
        print_review(plan, args.review, args.batch_size, languages)
    elif args.run:
        run_queue(plan, args.batch_size, args.max_batches, languages)
    else:
        print_plan(plan, languages)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
