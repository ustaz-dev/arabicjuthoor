#!/usr/bin/env python3
"""Resolve stale Aramaic family cards through their current member identities."""
from __future__ import annotations

from collections import Counter
import json
import re
import sqlite3
import sys
import tempfile
import unicodedata
from pathlib import Path

from search_arabic_root_senses import ARABIC_MARKS, DEFAULT_RESOURCES, root_sense_fan


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
AUDIT_JSON = (
    ROOT / "cache" / "recovery_pipeline"
    / "arabic-fan-campaign-aramaic-batch-06.json"
)
AUDIT_MD = (
    ROOT / "05-audits"
    / "2026-07-25-arabic-fan-campaign-aramaic-batch-06.md"
)
DATE = "2026-07-25"
BATCH = "ARAMAIC-06"
CARD_HEADING = re.compile(r"^### (?:بطاقة|إعادةُ توسيم).*$", re.MULTILINE)
FAMILY_ID = re.compile(r"aramaic:family:[0-9a-f]+")
ENTRY_ID = re.compile(r"kaikki_aramaic:[^`؛\s,\]]+")
REVIEW = re.compile(
    r"(?ms)^### مراجعة عضوية: `?(aramaic:family:[0-9a-f]+)`?[^\n]*\n"
    r".*?(?=^### |\Z)"
)

OLD_SOURCE_NAMES = (
    "لسان العرب لابن منظور",
    "تاج العروس لمرتضى الزبيدي",
    "تاج اللغة وصحاح العربية للجوهري",
    "المحكم والمحيط الأعظم لابن سيده",
    "كتاب العين للخليل بن أحمد",
)
POSITIVE = ("ROOT-TRACE", "ROOT-ECHO", "NUCLEUS-TRACE", "NUCLEUS-ECHO")
ISOLATED = (
    "LOANWORD",
    "PROPER-NAME-ISOLATED",
    "NONLEXICAL-ISOLATED",
    "FORM-OF-ISOLATED",
    "ISOLATED-GRAMMAR",
    "NAME-ISOLATED",
    "MIXED-ISOLATED",
    "REFER-EXISTING",
)
OUTCOMES = POSITIVE + ISOLATED + (
    "MORPHOLOGY-GAP",
    "LAW-GAP",
    "SOURCE-GAP",
    "OPEN-CANDIDATE",
    "TOOL-GAP",
)
SPECIAL_SABAR = "aramaic:family:0c282c4d1d3074ef6ccd39ce"
SPECIAL_NAHAR = "aramaic:family:23d9025ee0c2079d9f5fffca"
SPECIAL_ZAYIN = "aramaic:family:f88688baac196830b79c3fc5"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(unicodedata.normalize("NFC", text))
        temporary = Path(handle.name)
    temporary.replace(path)


def replace_one(section: str, pattern: str, replacement: str) -> tuple[str, str]:
    match = re.search(pattern, section, re.MULTILINE)
    if not match:
        raise ValueError(f"missing field {pattern}")
    old = match.group(0)
    changed, count = re.subn(pattern, replacement, section, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"ambiguous field {pattern}")
    return changed, old


def latest_reviews(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in REVIEW.finditer(text):
        result[match.group(1)] = match.group(0)
    return result


def entry_ids(section: str) -> list[str]:
    return sorted({match.rstrip(":;.") for match in ENTRY_ID.findall(section)})


def source_ready(review: str) -> bool:
    return sum(name in review for name in OLD_SOURCE_NAMES) >= 2 and "مروحة" in review


def linked_member_lines(
    identifiers: list[str],
    reviews: dict[str, str],
    connection: sqlite3.Connection,
) -> tuple[list[str], list[str]]:
    lines: list[str] = []
    linked_reviews: list[str] = []
    for identifier in identifiers:
        families = [
            row[0]
            for row in connection.execute(
                "SELECT family_id FROM family_members WHERE entry_id=?",
                (identifier,),
            )
        ]
        for family in families:
            review = reviews.get(family)
            if not review:
                continue
            linked_reviews.append(review)
            lines.extend(
                line.strip()
                for line in review.splitlines()
                if line.startswith("- العضو:") and identifier in line
            )
    return list(dict.fromkeys(lines)), list(dict.fromkeys(linked_reviews))


def outcome(line: str) -> str:
    return next((name for name in OUTCOMES if name in line), "OPEN-CANDIDATE")


def fan_sources(root: str, terms: tuple[str, ...]) -> list[str]:
    fan = root_sense_fan(DEFAULT_RESOURCES, root, None)["independent_fan"]
    if not fan["judgment_ready"] or len(fan["selected_sources"]) < 2:
        raise ValueError(f"incomplete fan for {root}")
    for witness in fan["selected_sources"]:
        definition = ARABIC_MARKS.sub(
            "", unicodedata.normalize("NFKC", str(witness["definition"]))
        )
        if not any(term in definition for term in terms):
            raise ValueError(
                f"{root}: named sense absent from {witness['source_label']}"
            )
    return [item["source_label"] for item in fan["selected_sources"]]


def special_decision(family: str) -> dict | None:
    if family == SPECIAL_SABAR:
        sources = fan_sources("سبر", ("سبر", "غور", "اختبر"))
        return {
            "state": "INTRA-HOUSE-TRANSFER",
            "verdict": "غير صادر",
            "released": True,
            "note": "المصدر يسمي انتقال سبر من الآرامية إلى العربية؛ يحفظ داخل البيت ولا يعد شاهد فرع مستقل",
            "evidence": "مروحة سبر كاملة، واتجاه الانتقال مسمى في البطاقة",
            "fan_sources": sources,
        }
    if family == SPECIAL_NAHAR:
        sources = fan_sources("نهر", ("ضياء", "النهار", "نهار"))
        return {
            "state": "READY",
            "verdict": "ROOT-TRACE",
            "released": True,
            "note": "נהר «يضيء» يقابل نهر في حقل الضياء والنهار بصوامت مطابقة",
            "evidence": "المعنى الضوئي مسمى في المصدرين العربيين لا مستنتج من النهر المائي",
            "fan_sources": sources,
        }
    if family == SPECIAL_ZAYIN:
        return {
            "state": "NONLEXICAL-ISOLATED",
            "verdict": "غير صادر",
            "released": True,
            "note": "المدخل حرف أبجدي لا مادة معجمية",
            "evidence": "Kaikki يصنف 𐡆 character",
            "fan_sources": [],
        }
    return None


def linked_decision(
    family: str,
    identifiers: list[str],
    reviews: dict[str, str],
    connection: sqlite3.Connection,
) -> dict:
    lines, linked_reviews = linked_member_lines(identifiers, reviews, connection)
    if not lines:
        raise ValueError(f"{family}: no linked current member review")
    states = [outcome(line) for line in lines]
    positives = [state for state in states if state in POSITIVE]
    if positives:
        evidence_reviews = [
            review
            for review in linked_reviews
            if any(identifier in review and any(p in review for p in POSITIVE)
                   for identifier in identifiers)
        ]
        if not any(source_ready(review) for review in evidence_reviews):
            raise ValueError(f"{family}: positive linked review lacks two-source fan")
        verdict = positives[0]
        source_names = [
            name for name in OLD_SOURCE_NAMES
            if any(name in review for review in evidence_reviews)
        ]
        return {
            "state": "READY",
            "verdict": verdict,
            "released": True,
            "note": "العضو الموجب موصول بمعرفه إلى مراجعته الحالية ومروحته الكاملة",
            "evidence": " | ".join(line for line in lines if verdict in line),
            "fan_sources": source_names,
        }
    if states and all(state in ISOLATED for state in states):
        if all(state == "LOANWORD" for state in states):
            state, verdict = "LOANWORD", "LOANWORD"
        elif len(set(states)) == 1:
            state, verdict = states[0], "غير صادر"
        else:
            state, verdict = "MIXED-ISOLATED", "غير صادر"
        return {
            "state": state,
            "verdict": verdict,
            "released": True,
            "note": "كل الأعضاء القديمة موصولة إلى تصنيف عزل أو إحالة مستنفد",
            "evidence": " | ".join(lines),
            "fan_sources": [],
        }
    combined = " | ".join(states)
    if "MORPHOLOGY-GAP" in states:
        state = "MORPHOLOGY-GAP"
        note = "تحليل الصيغة هو المانع الحقيقي بعد المروحة"
    elif "LAW-GAP" in states:
        state = "LAW-GAP"
        note = "المسار الصوتي الموقع هو المانع الحقيقي بعد المروحة"
    elif "SOURCE-GAP" in states:
        state = "SOURCE-GAP"
        note = "الإسناد الفردي هو المانع الحقيقي بعد المروحة"
    else:
        state = "OPEN-CANDIDATE"
        note = "المروحة مستنفدة ولم تكتمل المطابقة العضوية في الأعضاء الموصولة"
    return {
        "state": state,
        "verdict": "غير صادر",
        "released": False,
        "note": note,
        "evidence": f"مصائر الأعضاء الحالية: {combined}",
        "fan_sources": [],
    }


def apply(section: str, family: str, item: dict) -> tuple[str, dict]:
    marker = f"<!-- ARABIC-FAN-CAMPAIGN:{BATCH}:{family} -->"
    if marker in section:
        return section, {"already_applied": True}
    section, old_blocker = replace_one(
        section,
        r"^-\s*عائق:\s*.+$",
        f"- عائق: النوع={item['state']}؛ يتطلب={item['note']}",
    )
    if "النوع=TOOL-GAP" not in old_blocker:
        raise ValueError(f"{family}: not a TOOL-GAP card")
    section, old_closure = replace_one(
        section,
        r"^-\s*حالةُ الإغلاق:\s*.+$",
        f"- حالةُ الإغلاق: {item['state']}",
    )
    if item["verdict"] in POSITIVE:
        verdict_line = (
            f"- الحكم (استكشاف): {item['verdict']} للعضو المسمى وحده؛ "
            "لا وراثة عبر عضو مخالف."
        )
    elif item["verdict"] == "LOANWORD":
        verdict_line = "- الحكم (استكشاف): LOANWORD؛ عزل بلا حكم نسب."
    else:
        verdict_line = f"- الحكم (استكشاف): غير صادر؛ {item['note']}."
    section, old_verdict = replace_one(
        section, r"^-\s*الحكم \(استكشاف\):\s*.+$", verdict_line
    )
    appendix = "\n".join(
        [
            "",
            marker,
            f"- ملحقُ ربطِ الهويةِ القديمةِ بالمراجعة الحالية، {DATE}:",
            f"  - المصير: {item['state']}.",
            f"  - الدليل: {item['evidence']}",
            "  - مصادر المروحة: "
            + (" + ".join(item["fan_sources"]) if item["fan_sources"] else "محفوظة في المراجعة الموصولة أو لا تلزم للعزل")
            + ".",
            "  - الحسم: "
            + (
                f"{item['verdict']}؛ خرجت البطاقة من التعليق."
                if item["released"]
                else f"غير صادر؛ بقيت بسبب {item['state']} لا TOOL-GAP."
            ),
            "  - السجل التاريخي المحفوظ:",
            f"    - `{old_blocker}`",
            f"    - `{old_closure}`",
            f"    - `{old_verdict}`",
        ]
    )
    return section.rstrip() + "\n" + appendix + "\n\n", {
        "already_applied": False,
        "old_blocker": old_blocker,
        "old_closure": old_closure,
        "old_verdict": old_verdict,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    text = READING.read_text(encoding="utf-8")
    reviews = latest_reviews(text)
    starts = list(CARD_HEADING.finditer(text))
    connection = sqlite3.connect(DB)
    parts, records, seen = [], [], set()
    cursor = 0
    try:
        for index, heading in enumerate(starts):
            end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
            parts.append(text[cursor:heading.start()])
            section = text[heading.start():end]
            family_match = FAMILY_ID.search(heading.group(0))
            family = family_match.group(0) if family_match else ""
            marker = f"<!-- ARABIC-FAN-CAMPAIGN:{BATCH}:{family} -->"
            is_target = bool(
                re.search(r"^-\s*عائق:\s*النوع\s*=\s*TOOL-GAP\b", section, re.MULTILINE)
            ) or marker in section
            if family and is_target and family not in reviews:
                if family in seen:
                    raise ValueError(f"duplicate target card: {family}")
                seen.add(family)
                identifiers = entry_ids(section)
                item = special_decision(family) or linked_decision(
                    family, identifiers, reviews, connection
                )
                section, changes = apply(section, family, item)
                records.append({
                    "family": family,
                    "old_entry_ids": identifiers,
                    **item,
                    "changes": changes,
                })
            parts.append(section)
            cursor = end
        parts.append(text[cursor:])
    finally:
        connection.close()

    if len(records) != 204:
        raise ValueError(f"expected 204 stale-family records, found {len(records)}")
    updated = "".join(parts)
    if unicodedata.normalize("NFC", updated) != updated:
        raise ValueError("updated Aramaic reading is not NFC")
    atomic_write(READING, updated)

    released = [record for record in records if record["released"]]
    held = [record for record in records if not record["released"]]
    released_counts = Counter(
        record["verdict"] if record["verdict"] != "غير صادر" else record["state"]
        for record in released
    )
    held_counts = Counter(record["state"] for record in held)
    payload = {
        "schema": "arabic-fan-campaign-batch-v1",
        "status": "LOCAL-THIRD-LENS-REVIEW-REQUIRED",
        "date": DATE,
        "batch": BATCH,
        "language": "aramaic",
        "unit": "card-identity",
        "summary": {
            "cards_reviewed": len(records),
            "released_from_suspension": len(released),
            "released_verdict_counts": dict(sorted(released_counts.items())),
            "held_state_counts": dict(sorted(held_counts.items())),
        },
        "records": records,
    }
    atomic_write(AUDIT_JSON, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    released_text = "، ".join(
        f"{key}={value}" for key, value in sorted(released_counts.items())
    )
    held_text = "، ".join(f"{key}={value}" for key, value in sorted(held_counts.items()))
    atomic_write(
        AUDIT_MD,
        "\n".join(
            [
                "# محضر حملة فك الحبس، الآرامية، الدفعة 06",
                "",
                f"**التاريخ:** {DATE}.",
                "",
                "ربطت الدفعة معرفات الأعضاء القديمة بأسرها الحالية بعد تغير هوية الأسرة، ثم نقلت المصير العضوي دون توريث بين الأعضاء.",
                "",
                "## الرقمان المطلوبان",
                "",
                f"- خرج من التعليق: {len(released)}.",
                f"- توزيع الأحكام والتصنيفات الخارجة: {released_text}.",
                "",
                "## الباقي بسبب حقيقي",
                "",
                f"- {held_text}.",
                "",
                "لا رقم في هذا المحضر للنشر ولا تشغيل لخط البرهان.",
                "",
            ]
        ),
    )
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
