#!/usr/bin/env python3
"""Lane C, week two: deterministic full-coverage Indo-European reading.

The six shared inventories are opened read-only.  Selection is by stable source
order, never by semantic score, so the denominator is not enriched for likely
successes.  Every selected lexical member receives one RECOVERY-v2 card.

Only lane-C-owned reading files and lane-C-prefixed data files are written.
The proof line stays frozen and no shared builder is invoked.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import lane_c_ie_discovery as prior


ROOT = Path(__file__).resolve().parents[1]
READINGS = ROOT / "04-cross-linguistic" / "readings"
DATA = ROOT / "04-cross-linguistic" / "data"
MEMBERS_OUTPUT = DATA / "lane_c_ie_week2_members.json"
RESULTS_OUTPUT = DATA / "lane_c_ie_week2_results.json"
DATE = "2026-07-30"


@dataclass(frozen=True)
class Language:
    key: str
    reading_file: str
    db_path: str
    source_label: str
    add_count: int = 800


LANGUAGES = (
    Language(
        "ancient_greek",
        "ancient-greek.md",
        "cache/recovery_pipeline/inventory-v5.sqlite",
        "Kaikki Ancient Greek",
    ),
    Language(
        "latin",
        "old-latin.md",
        "cache/recovery_pipeline/inventory-v5.sqlite",
        "Kaikki Latin",
    ),
    Language(
        "persian",
        "persian.md",
        "cache/recovery_pipeline/week17-day1-inventory.sqlite",
        "Kaikki Persian",
    ),
    Language(
        "gothic",
        "gothic.md",
        "cache/recovery_pipeline/week17-day1-inventory.sqlite",
        "Kaikki Gothic",
    ),
    Language(
        "old_norse",
        "old-norse.md",
        "cache/recovery_pipeline/week17-day1-inventory.sqlite",
        "Kaikki Old Norse",
    ),
    Language(
        "welsh",
        "welsh.md",
        "cache/recovery_pipeline/week17-day1-inventory.sqlite",
        "Kaikki Welsh",
    ),
)


# A positive is impossible unless it appears here after a human review of the
# selected member, its oldest published stem, its licensed route, its orbit,
# and both named classical Arabic sources.
POSITIVE_ALLOWLIST: dict[str, dict[str, str]] = {
    "kaikki_ancient_greek:217:en-γράφω-grc-verb-pVb8IsLd": {
        "kind": "root",
        "arabic_form": "جرف",
        "orbit": (
            "مباشر في القطع والكشط من جرم المادة؛ الفرع يحز السطح "
            "والعربية تقطع من أصل الجسم الرخو وتزيل"
        ),
        "rationale": (
            "الحكم على الساق المنشورة `*gerbʰ-` لا على اللاحقة؛ "
            "هيكل `g-r-ph` المرخص يقابل جرف، والمصدران القديمان "
            "يشهدان معنى القطع والإزالة"
        ),
    },
    "kaikki_latin:1749:en-cornu-la-noun-knzNHpqZ": {
        "kind": "root",
        "arabic_form": "قرن",
        "orbit": (
            "مباشر في القرن بوصفه نتوءًا صلبًا ممتدًا في أعلى البدن "
            "أو مقدمه"
        ),
        "rationale": (
            "الصورة الموروثة `*kornū` تحفظ الهيكل `k-r-n` بعد طرح "
            "الحركة الختامية، والمعنى المنشور horn/antler مطابق للمدار "
            "الذي يشهد به لسان العرب وتاج العروس"
        ),
    },
    "kaikki_old_norse_2026_07_23:665:en-kanna-non-noun-hsm4SaLi": {
        "kind": "root",
        "arabic_form": "كنن",
        "orbit": (
            "مدار الهيئة والوظيفة؛ الإناء جوف متين يضم ما يوضع فيه "
            "ويستره ويحميه"
        ),
        "rationale": (
            "أقدم صورة مسماة `*kannǭ` تحفظ `k-n-n` ولا يُستهلك فيها "
            "حرف من لاحقة منفصلة؛ معنى can/tankard يلتقي مباشرة بجوف "
            "الكن، والمصدران القديمان حاضران"
        ),
    },
    "kaikki_welsh_2026_07_23:821:en-mwg-cy-noun-BNWIy0G4": {
        "kind": "root",
        "arabic_form": "موج",
        "orbit": (
            "مدار المادة والحركة؛ الدخان كتلة لطيفة مضطربة تنتبر "
            "وتتموج في حيزها"
        ),
        "rationale": (
            "السلسلة المنشورة تبلغ `*(s)mewg-` وتحفظ النواة الجذرية "
            "`m-w-g` من غير استمداد حرف من لاحقة؛ مسار الجرد المطبع "
            "يقابل موج، والمصدران القديمان يشهدان حركة المائع واضطرابه"
        ),
    },
}


ADDITIONAL_LOAN_MARKERS: dict[str, tuple[str, ...]] = {
    "ancient_greek": (
        "from phoenician",
        "from canaanite",
        "from sumerian",
        "from sanskrit",
    ),
    "latin": (
        "from phoenician",
        "from punic",
        "from celtic",
        "from gaulish",
        "from oscan",
    ),
    "persian": (
        "from sanskrit",
        "from hindi",
        "from urdu",
        "from russian",
        "from turkish",
        "from ottoman turkish",
        "from mongolian",
        "from portuguese",
        "from spanish",
        "from pashto",
    ),
    "gothic": (
        "from old high german",
        "from old saxon",
    ),
    "old_norse": (
        "from old english",
        "from old saxon",
        "from old east slavic",
        "from old irish",
    ),
    "welsh": (
        "from old english",
        "from old irish",
        "from cornish",
        "from breton",
    ),
}


def contact_marker(language: str, etymology: str) -> str:
    marker = prior.loan_marker(language, etymology)
    if marker:
        return marker
    lowered = etymology.casefold()[:420]
    if lowered.startswith(("perhaps", "possibly", "probably")):
        return ""
    for candidate in ADDITIONAL_LOAN_MARKERS[language]:
        index = lowered.find(candidate)
        if index < 0:
            continue
        context = lowered[max(0, index - 56) : index]
        if any(
            hedge in context
            for hedge in ("perhaps", "possibly", "probably", "maybe")
        ):
            continue
        return candidate
    return ""


def nfc(value: str | None) -> str:
    return prior.nfc(value or "")


def ro_connection(relative: str) -> sqlite3.Connection:
    path = (ROOT / relative).resolve()
    con = sqlite3.connect(
        f"file:{path.as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    con.row_factory = sqlite3.Row
    return con


def source_ordinal(entry_id: str) -> int:
    match = re.search(r":(\d+):", entry_id)
    return int(match.group(1)) if match else 2**63 - 1


def existing_identity(reading_path: Path, language: str) -> tuple[set[str], set[str]]:
    _, entries, terms = prior.existing_ids(reading_path, language)
    return entries, terms


def lexical_members(
    con: sqlite3.Connection,
    language: Language,
    used_entries: set[str],
    used_terms: set[str],
) -> list[dict[str, Any]]:
    rows = con.execute(
        """
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
            e.alternative_of,
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
          AND e.form_of = 0
          AND e.alternative_of = 0
        """,
        (language.key,),
    ).fetchall()
    eligible: list[dict[str, Any]] = []
    for row in rows:
        entry_id = nfc(row["entry_id"])
        headword = nfc(row["headword"])
        romanization = nfc(row["romanization"])
        pos = nfc(row["pos"]).casefold()
        if entry_id in used_entries or pos in prior.BAD_POS:
            continue
        if not headword or headword.startswith("<"):
            continue
        # Legacy cards without an inventory ID still reserve their displayed
        # term.  Homonymous unseen members remain eligible when the file has an
        # explicit inventory ID for the older sense.
        if (
            prior.term_key(headword) in used_terms
            or (romanization and prior.term_key(romanization) in used_terms)
        ):
            continue
        eligible.append(
            {
                "entry_id": entry_id,
                "source_ordinal": source_ordinal(entry_id),
                "headword": headword,
                "romanization": romanization,
                "pos": nfc(row["pos"]),
                "gloss": nfc(row["gloss"]),
                "etymology": nfc(row["etymology"]),
                "source_stratum": nfc(row["source_stratum"]),
                "source_scope_note": nfc(row["source_scope_note"]),
                "loan_hint": bool(row["loan_hint"]),
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
    eligible.sort(
        key=lambda row: (
            row["source_ordinal"],
            row["entry_id"],
        )
    )
    if len(eligible) < language.add_count:
        raise RuntimeError(
            f"{language.key}: only {len(eligible)} unseen lexical members"
        )
    return eligible[: language.add_count]


def attach_zero_step(con: sqlite3.Connection, members: list[dict[str, Any]]) -> None:
    for member in members:
        rows = con.execute(
            """
            SELECT rule_id, surface_form, comparison_form,
                   surface_skeleton, comparison_skeleton, sources_json
            FROM zero_step_forms
            WHERE entry_id = ?
            ORDER BY rule_id, comparison_form
            """,
            (member["entry_id"],),
        ).fetchall()
        member["zero_step"] = [
            {
                "rule_id": nfc(row["rule_id"]),
                "surface_form": nfc(row["surface_form"]),
                "comparison_form": nfc(row["comparison_form"]),
                "surface_skeleton": nfc(row["surface_skeleton"]),
                "comparison_skeleton": nfc(row["comparison_skeleton"]),
                "sources": json.loads(row["sources_json"] or "[]"),
            }
            for row in rows
        ]


def attach_candidates(
    con: sqlite3.Connection,
    members: list[dict[str, Any]],
    english_definitions: dict[str, str],
    source_counts: dict[str, dict[str, int]],
) -> None:
    flat: list[dict[str, Any]] = []
    by_entry: dict[str, list[dict[str, Any]]] = {}
    for member in members:
        candidate_rows = con.execute(
            """
            SELECT c.kind, c.form, c.status, c.rule_ids_json,
                   c.route_flag, a.reading
            FROM candidates c
            LEFT JOIN arabic_forms a
              ON a.form = c.form AND a.kind = c.kind
            WHERE c.entry_id = ?
              AND c.status = 'licensed'
              AND c.route_flag = 0
            """,
            (member["entry_id"],),
        ).fetchall()
        candidates: list[dict[str, Any]] = []
        for row in candidate_rows:
            candidate = {
                "entry_id": member["entry_id"],
                "gloss": member["gloss"],
                "kind": nfc(row["kind"]),
                "arabic_form": nfc(row["form"]),
                "arabic_reading": nfc(row["reading"]),
                "rule_ids": json.loads(row["rule_ids_json"] or "[]"),
                "candidate_status": nfc(row["status"]),
                "route_flag": bool(row["route_flag"]),
                "classical_source_counts": source_counts.get(
                    nfc(row["form"]),
                    {},
                ),
            }
            candidates.append(candidate)
            flat.append(candidate)
        by_entry[member["entry_id"]] = candidates

    scores = prior.semantic_scores(flat, english_definitions)
    for candidate, score in zip(flat, scores):
        candidate["semantic_score"] = round(score, 6)

    for member in members:
        candidates = by_entry[member["entry_id"]]
        candidates.sort(
            key=lambda item: (
                item["semantic_score"],
                item["kind"] == "root",
                -len(item["rule_ids"]),
                item["arabic_form"],
            ),
            reverse=True,
        )
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
        member["tested_candidates"] = sorted(
            unique.values(),
            key=lambda item: (
                item["semantic_score"],
                item["kind"] == "root",
                -len(item["rule_ids"]),
                item["arabic_form"],
            ),
            reverse=True,
        )[:24]


def build_members() -> dict[str, Any]:
    english_definitions = prior.load_arabic_english_definitions()
    source_counts = prior.load_classical_source_counts()
    output: dict[str, Any] = {
        "schema": "lane-c-ie-week2-full-coverage-v1",
        "date": DATE,
        "contract": {
            "selection": (
                "first unseen independent lexical members in stable source "
                "order; semantic score never affects inclusion"
            ),
            "coverage": "one RECOVERY-v2 card per selected member",
            "proof_line": "frozen",
            "shared_databases": "read-only and immutable",
            "positive_verdicts": "explicit reviewed allowlist only",
        },
        "languages": {},
    }
    for language in LANGUAGES:
        print(f"lane-c week2: selecting {language.key}", file=sys.stderr)
        reading_path = READINGS / language.reading_file
        used_entries, used_terms = existing_identity(reading_path, language.key)
        con = ro_connection(language.db_path)
        try:
            members = lexical_members(
                con,
                language,
                used_entries,
                used_terms,
            )
            attach_zero_step(con, members)
            attach_candidates(
                con,
                members,
                english_definitions,
                source_counts,
            )
        finally:
            con.close()
        output["languages"][language.key] = {
            "reading_file": language.reading_file,
            "members_selected": len(members),
            "used_inventory_ids_before": len(used_entries),
            "selection_min_source_ordinal": min(
                member["source_ordinal"] for member in members
            ),
            "selection_max_source_ordinal": max(
                member["source_ordinal"] for member in members
            ),
            "members": members,
        }
    MEMBERS_OUTPUT.write_text(
        nfc(json.dumps(output, ensure_ascii=False, indent=2)) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output


def clean(value: str, limit: int = 480) -> str:
    return prior.clean_inline(value, limit)


def source_fan(member: dict[str, Any]) -> str:
    candidates = member["tested_candidates"]
    if not candidates:
        return (
            "فُحص مسارا لسان العرب لابن منظور وتاج العروس لمرتضى "
            "الزبيدي عبر الجرد، ولم يحمل العضو مرشحًا عربيًا مرخصًا"
        )
    previews: list[str] = []
    for candidate in candidates[:8]:
        counts = candidate["classical_source_counts"]
        lisan = counts.get("لسان العرب لابن منظور", 0)
        taj = counts.get("تاج العروس لمرتضى الزبيدي", 0)
        rules = "+".join(candidate["rule_ids"]) or "تطابق ذاتي"
        previews.append(
            f"{candidate['kind']} {candidate['arabic_form']} "
            f"«{clean(candidate['arabic_reading'], 100) or 'بلا قراءة'}» "
            f"[لسان العرب={lisan}؛ تاج العروس={taj}؛ {rules}]"
        )
    return (
        f"فُحص المصدران القديمان في {len(candidates)} مرشحًا مرخصًا؛ "
        + "؛ ".join(previews)
    )


def zero_step_line(member: dict[str, Any]) -> str:
    rows = member["zero_step"]
    if not rows:
        return (
            "لا تعرية آلية مسجلة للعضو؛ دخل المقارنة من "
            f"`{member['selected_input'] or 'الصورة الأصلية'}` بهيكل "
            f"`{member['skeleton'] or 'غير متاح'}`؛ لا يُؤخذ حرف سطحي "
            "جذريًا إذا خالف الأصل المنشور"
        )
    previews = []
    for row in rows[:4]:
        source_text = "، ".join(str(item) for item in row["sources"][:3])
        previews.append(
            f"`{row['surface_form']}` → `{row['comparison_form']}` "
            f"({row['surface_skeleton']} → {row['comparison_skeleton']}) "
            f"بالقاعدة `{row['rule_id']}`"
            + (f"؛ المصدر {clean(source_text, 120)}" if source_text else "")
        )
    return "؛ ".join(previews)


def candidate_for_positive(member: dict[str, Any]) -> dict[str, Any] | None:
    positive = POSITIVE_ALLOWLIST.get(member["entry_id"])
    if positive is None:
        return None
    for candidate in member["tested_candidates"]:
        if (
            candidate["kind"] == positive["kind"]
            and candidate["arabic_form"] == positive["arabic_form"]
        ):
            counts = candidate["classical_source_counts"]
            if not (
                counts.get("لسان العرب لابن منظور", 0)
                and counts.get("تاج العروس لمرتضى الزبيدي", 0)
            ):
                raise RuntimeError(
                    f"positive lacks two classical sources: {member['entry_id']}"
                )
            return candidate
    raise RuntimeError(
        f"positive candidate absent for {member['entry_id']}: "
        f"{positive['kind']} {positive['arabic_form']}"
    )


def render_card(
    language: Language,
    member: dict[str, Any],
    ordinal: int,
) -> tuple[str, str]:
    positive = POSITIVE_ALLOWLIST.get(member["entry_id"])
    positive_candidate = candidate_for_positive(member)
    loan = contact_marker(language.key, member["etymology"])
    if loan:
        # A named donor for an explicitly different sense does not close the
        # member currently being read.
        sense_matches = re.findall(
            r"in the [^.]{0,80}?sense of [“\"]([^”\"]+)[”\"]"
            r"[^.]{0,160}?semantic loan",
            member["etymology"],
            re.IGNORECASE,
        )
        if sense_matches and not any(
            sense.casefold() in member["gloss"].casefold()
            for sense in sense_matches
        ):
            loan = ""
    candidates = member["tested_candidates"]
    best = positive_candidate or (candidates[0] if candidates else None)
    if positive and loan:
        raise RuntimeError(
            f"positive conflicts with explicit loan: {member['entry_id']}"
        )

    if positive:
        state = "READY"
        verdict = (
            "ROOT-TRACE"
            if positive_candidate["kind"] == "root"
            else "NUCLEUS-TRACE"
        )
        orbit = positive["orbit"]
        skeptic = positive["rationale"]
        branch_supported = 1
        arabic_supported = 1
        outcome = "positive"
    elif loan:
        state = "READY"
        verdict = "LOANWORD"
        orbit = (
            "لم يُصدر مدار نسب مستقل؛ التشابه الممكن واقع داخل مسار "
            "تماس منشور لا داخل مقارنة وراثية"
        )
        skeptic = (
            f"أغلق حقل الاشتقاق العضو بعبارة تماس صريحة `{loan}`، "
            "ولم تُحوّل إلى صلة"
        )
        branch_supported = 0
        arabic_supported = 0
        outcome = "closure"
    elif not candidates:
        state = "OPEN-NO-LICENSED-CANDIDATE"
        verdict = "غير صادر"
        orbit = (
            "فُحص معنى العضو ولم يوجد مسار صوتي مرخص يوصله إلى مادة "
            "عربية؛ لذلك لا مدار موجب ولا NO-TRACE مختلق"
        )
        skeptic = (
            "غياب المرشح المرخص سبب إبقاء البطاقة مفتوحة، لا حكم "
            "نفي على اللسان أو الأسرة"
        )
        branch_supported = 0
        arabic_supported = 0
        outcome = "open"
    else:
        state = "OPEN-CANDIDATE"
        verdict = "غير صادر"
        orbit = (
            "قورنت جوارات المعنى للمرشحات الظاهرة، ولم يثبت التقاء "
            "بخطوة واحدة مع الساق الأقدم؛ بقيت البطاقة مفتوحة"
        )
        skeptic = (
            "منعت المراجعة ترقية التشابه الصامت أو الترجمة المفردة "
            "إلى صلة من غير مدار وساق تاريخية موافقة"
        )
        branch_supported = 0
        arabic_supported = 0
        outcome = "open"

    display = member["headword"]
    if member["romanization"]:
        display += f" ({member['romanization']})"
    oldest = (
        clean(member["etymology"])
        if member["etymology"]
        else "لا صورة أقدم مسماة في حقل الاشتقاق للعضو"
    )
    if best:
        degree = (
            "جذر ثلاثي كامل"
            if best["kind"] == "root"
            else f"مرشح من درجة {best['kind']}"
        )
        counterpart = (
            f"{best['arabic_form']} "
            f"«{clean(best['arabic_reading'], 220) or 'قراءة غير مسجلة'}»"
        )
        rules = " + ".join(best["rule_ids"]) or "تطابق ذاتي في الهيكل المطبع"
        sound = (
            f"{rules}؛ المرشح `licensed` و`route_flag=0`؛ "
            "لم يُنشأ صف صوتي جديد"
        )
    else:
        degree = "لا جذر ولا نواة مرخصة لهذا العضو"
        counterpart = "لا مقابل صادر؛ قائمة المرشحين المرخصين فارغة"
        sound = (
            "لا مسار صوتي مرخص في الجرد؛ لم تُستحدث قاعدة لعبور الفجوة"
        )
    filter_line = (
        f"مسار تماس منشور `{loan}`"
        if loan
        else "لا مانح أجنبي صريح حاسم في حقل الاشتقاق"
    )
    source_scope = (
        member["source_scope_note"]
        or "حدود لقطة المصدر المثبتة نافذة؛ لا ادعاء باستيعاب المعجم كله"
    )
    text = f"""
### بطاقة: `{member['family_id']}`، {display} (التغطية الكاملة ج2، {ordinal})
- إصدارُ البروتوكول: RECOVERY-v2؛ طور الاكتشاف؛ خط البرهان مجمد.
- الكلمةُ في الفرع: {display} [{member['pos']}؛ `{member['entry_id']}`].
- أقدمُ صورةٍ مستعادة: {oldest} [{language.source_label}، حقل `etymology_text`].
- الخطوةُ صفر (التعرية بصرف الفرع): {zero_step_line(member)}.
- درجةُ المقارنة: {degree}.
- مسحُ المعاني العربيّة: {source_fan(member)}.
- المقابلُ من اللسان: {counterpart}.
- مسارُ الصوت: {sound}.
- المعنى من قاموس الفرع: «{clean(member['gloss'], 360) or 'لا شرح منشور في لقطة العضو'}» [{language.source_label}، العضو المسمى].
- المدار: {orbit}.
- المصفاة: {filter_line}.
- فصلُ المتجانسات والاقتراض: الحكم خاص بهذا العضو وسلسلة معناه؛ لم يُورث من متحد الرسم ولا من عضو آخر في الأسرة.
- مؤشر اليتم: الأسرة `{member['family_id']}` تضم {member['family_member_count']} عضوًا، منها {member['family_lemma_count']} لمّة؛ دور العضو `{member['family_role'] or 'غير مسمى'}`؛ العدد وصف استرجاع لا قرينة حكم.
- إشعاع الأسرة في الفرع: الأعضاء المعجمية المدعومة={branch_supported}؛ سلاسل المعنى المدعومة={branch_supported}؛ حُد الدعم بالعضو المفحوص.
- إشعاع الأسرة في العربية: الأعضاء المعجمية المدعومة={arabic_supported}؛ سلاسل المعنى المدعومة={arabic_supported}؛ حُد الدعم بالمادة المسماة ومدارها.
- جسورُ الاسترداد المفحوصة: العضو المستقل؛ الخطوة صفر؛ الجذر الثلاثي؛ النواة؛ المرشحات المرخصة؛ لسان العرب؛ تاج العروس؛ الأصل المنشور؛ القرض؛ المدار.
- حالةُ الإغلاق: {state}.
- الحكم (استكشاف): {verdict}.
- عدسة الاسترداد: كُتبت بطاقة العضو سواء نجح أم لم ينجح؛ لم يؤثر الترتيب الدلالي في دخوله المقام.
- عدسة التشكيك: {skeptic}.
- ملاحظات: {source_scope}؛ لا تشغيل لخط البرهان، ولا توقيع صف، ولا بناء لملف مشترك.
"""
    return nfc(text), outcome


def complete_card_count(text: str) -> int:
    blocks = text.split("### بطاقة:")[1:]
    return sum(
        all(
            field in block.split("\n### بطاقة:", 1)[0]
            for field in (
                "- المدار:",
                "- أقدمُ صورةٍ مستعادة:",
                "- مؤشر اليتم:",
            )
        )
        for block in blocks
    )


def append_cards(output: dict[str, Any]) -> dict[str, Any]:
    selected_ids = {
        member["entry_id"]
        for block in output["languages"].values()
        for member in block["members"]
    }
    missing_positive = set(POSITIVE_ALLOWLIST) - selected_ids
    if missing_positive:
        raise RuntimeError(
            "positive allowlist outside deterministic sample: "
            + ", ".join(sorted(missing_positive))
        )

    summary: dict[str, Any] = {
        "schema": "lane-c-ie-week2-results-v1",
        "date": DATE,
        "selection": "stable source order, full coverage",
        "proof_line": "frozen",
        "languages": {},
        "totals": {
            "cards": 0,
            "positive": 0,
            "closures": 0,
            "open": 0,
        },
    }
    rendered_files: dict[Path, str] = {}
    for language in LANGUAGES:
        marker = f"LANE-C-WEEK2-FULL-COVERAGE-{DATE}:{language.key}"
        path = READINGS / language.reading_file
        old_text = path.read_text(encoding="utf-8")
        if marker in old_text:
            raise RuntimeError(f"append marker already exists in {path}")
        before = complete_card_count(old_text)
        if before != 200:
            raise RuntimeError(
                f"{language.key}: expected 200 complete cards before append, got {before}"
            )
        members = output["languages"][language.key]["members"]
        if len(members) != language.add_count:
            raise RuntimeError(
                f"{language.key}: expected {language.add_count}, got {len(members)}"
            )
        counts = {
            "cards": len(members),
            "positive": 0,
            "closures": 0,
            "open": 0,
        }
        card_texts: list[str] = []
        for ordinal, member in enumerate(members, 1):
            card_text, outcome = render_card(language, member, ordinal)
            card_texts.append(card_text)
            counts["closures" if outcome == "closure" else outcome] += 1
        section = f"""

<!-- {marker} -->
## أسبوع التغطية الكاملة: المسار ج ({DATE})

### بيان المقام

أُضيفت {len(members)} بطاقة، بطاقة واحدة لكل عضو معجمي مستقل فُحص. دخل الأعضاء بترتيب المصدر الثابت بعد استبعاد المقروء، ولم يؤثر التشابه الدلالي ولا وجود المرشح في اختيار المقام. الناجح والمغلق والمفتوح مكتوبة بطاقاتهم جميعًا. خط البرهان مجمد، ولم يُنشأ صف صوتي أو ملف مشترك.

<!-- RECOVERY-PROTOCOL-v2 -->
<!-- RADIATION-FIELDS-v1 -->
{''.join(card_texts)}
<!-- /{marker} -->
"""
        new_text = nfc(old_text.rstrip() + section + "\n")
        after = complete_card_count(new_text)
        if after != 1000:
            raise RuntimeError(
                f"{language.key}: expected 1000 complete cards after append, got {after}"
            )
        rendered_files[path] = new_text
        summary["languages"][language.key] = {
            **counts,
            "complete_cards_before": before,
            "complete_cards_after": after,
            "raw_card_headings_after": new_text.count("### بطاقة:"),
        }
        for key in ("cards", "positive", "closures", "open"):
            summary["totals"][key] += counts[key]

    if summary["totals"]["cards"] != 4800:
        raise RuntimeError("full-coverage denominator is not 4800")
    for path, text in rendered_files.items():
        path.write_text(text, encoding="utf-8", newline="\n")
    RESULTS_OUTPUT.write_text(
        nfc(json.dumps(summary, ensure_ascii=False, indent=2)) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return summary


def print_review(output: dict[str, Any], count: int) -> None:
    for language in LANGUAGES:
        members = output["languages"][language.key]["members"]
        ranked = sorted(
            (
                member
                for member in members
                if member["tested_candidates"]
            ),
            key=lambda member: (
                member["tested_candidates"][0]["semantic_score"],
                member["tested_candidates"][0]["kind"] == "root",
                -len(member["tested_candidates"][0]["rule_ids"]),
            ),
            reverse=True,
        )
        print(f"\n[{language.key}] deterministic denominator={len(members)}")
        for member in ranked[:count]:
            candidate = member["tested_candidates"][0]
            counts = candidate["classical_source_counts"]
            print(
                "\t".join(
                    (
                        f"{candidate['semantic_score']:.4f}",
                        member["entry_id"],
                        member["headword"],
                        member["romanization"],
                        member["pos"],
                        clean(member["gloss"], 160),
                        candidate["kind"],
                        candidate["arabic_form"],
                        clean(candidate["arabic_reading"], 120),
                        "+".join(candidate["rule_ids"]) or "IDENTITY",
                        str(counts.get("لسان العرب لابن منظور", 0)),
                        str(counts.get("تاج العروس لمرتضى الزبيدي", 0)),
                        clean(member["etymology"], 240),
                    )
                )
            )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rank", action="store_true")
    parser.add_argument("--review", type=int, metavar="N")
    parser.add_argument("--append", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.rank and args.review is None and not args.append:
        raise SystemExit("choose --rank, --review N, and/or --append")
    if args.rank:
        output = build_members()
    else:
        output = json.loads(MEMBERS_OUTPUT.read_text(encoding="utf-8"))
    if args.review is not None:
        print_review(output, args.review)
    if args.append:
        summary = append_cards(output)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
