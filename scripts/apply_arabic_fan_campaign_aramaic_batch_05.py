#!/usr/bin/env python3
"""Reconcile original Aramaic TOOL-GAP cards with their latest organic reviews."""
from __future__ import annotations

from collections import Counter
import json
import re
import sys
import tempfile
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
AUDIT_JSON = (
    ROOT / "cache" / "recovery_pipeline"
    / "arabic-fan-campaign-aramaic-batch-05.json"
)
AUDIT_MD = (
    ROOT / "05-audits"
    / "2026-07-25-arabic-fan-campaign-aramaic-batch-05.md"
)
DATE = "2026-07-25"
BATCH = "ARAMAIC-05"
CARD_HEADING = re.compile(r"^### (?:بطاقة|إعادةُ توسيم).*$", re.MULTILINE)
FAMILY_ID = re.compile(r"aramaic:family:[0-9a-f]+")
REVIEW = re.compile(
    r"(?ms)^### مراجعة عضوية: `?(aramaic:family:[0-9a-f]+)`?[^\n]*\n"
    r".*?(?=^### |\Z)"
)


# These latest reviews contain a named ROOT-TRACE member, a complete fan from
# two independent old Arabic works, and an explicit member-level semantic match.
POSITIVE_FAMILIES = {
    "aramaic:family:bd8dfd3e1e9023047342464f",
    "aramaic:family:9a999011c54fe83a6bece34c",
    "aramaic:family:031c93a55aa4879486d9f919",
    "aramaic:family:a36d11a56c6a5692951a1cb8",
    "aramaic:family:a63a0d1cfa15f5b698284d1c",
    "aramaic:family:a32827fae5532d0289e2366e",
    "aramaic:family:59d35ee0f532ff769047e21e",
    "aramaic:family:97bf06528ad2ee974ce089d4",
    "aramaic:family:9c1282e283fa5ef156b10124",
}

RELEASE_STATES = {
    "LOANWORD": ("LOANWORD", "LOANWORD"),
    "PROPER-NAME-ISOLATED": ("PROPER-NAME-ISOLATED", "غير صادر"),
    "NONLEXICAL-ISOLATED": ("NONLEXICAL-ISOLATED", "غير صادر"),
    "MIXED-ISOLATED": ("MIXED-ISOLATED", "غير صادر"),
    "FORM-OF-ISOLATED": ("FORM-OF-ISOLATED", "غير صادر"),
}

OLD_SOURCE_NAMES = (
    "لسان العرب لابن منظور",
    "تاج العروس لمرتضى الزبيدي",
    "تاج اللغة وصحاح العربية للجوهري",
    "المحكم والمحيط الأعظم لابن سيده",
    "كتاب العين للخليل بن أحمد",
)


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


def family_state(review: str) -> str:
    states = re.findall(r"^-\s*حالة الأسرة:\s*`?([^\n`]+)", review, re.MULTILINE)
    return states[-1].strip(" .؛") if states else ""


def positive_evidence(family: str, review: str) -> dict:
    lines = [
        line.strip()
        for line in review.splitlines()
        if line.startswith("- العضو:") and "ROOT-TRACE" in line
    ]
    if not lines:
        raise ValueError(f"{family}: no named ROOT-TRACE member in latest review")
    evidence = " | ".join(lines)
    named_sources = [name for name in OLD_SOURCE_NAMES if name in evidence]
    if len(named_sources) < 2 or "مروحة" not in evidence:
        raise ValueError(f"{family}: positive review lacks a complete two-source fan")
    return {
        "state": "READY",
        "verdict": "ROOT-TRACE",
        "released": True,
        "requires": "المراجعة المضادة الثالثة قبل الإيداع",
        "note": "أحدث مراجعة عضوية تسمي العضو الموجب ومطابقته ومروحته الكاملة",
        "evidence": evidence,
        "fan_sources": named_sources,
    }


def true_held_state(review_state: str, review: str) -> tuple[str, str]:
    combined = review_state + "\n" + review
    if "MORPHOLOGY-GAP" in combined or "تحليل صرفي" in combined:
        return (
            "MORPHOLOGY-GAP",
            "تحليل الصيغة أو فصل أعضائها هو المانع الحقيقي بعد استنفاد المروحة",
        )
    if "LAW-GAP" in combined or "المسار غير مرخص" in combined or "صف صوتي" in combined:
        return (
            "LAW-GAP",
            "المقابل محفوظ لكن المسار الصوتي المنشور الموقع هو المانع الحقيقي",
        )
    if "SOURCE-GAP" in combined or "مصدر فردي" in combined:
        return (
            "SOURCE-GAP",
            "الإسناد الفردي المنشور هو المانع الحقيقي بعد استنفاد المروحة",
        )
    return (
        "OPEN-CANDIDATE",
        "المروحة استنفدت ولم يلتق بعد جسر صوتي ودلالي عضوي مسمى",
    )


def decision(family: str, review: str) -> dict:
    state = family_state(review)
    if family in POSITIVE_FAMILIES:
        return positive_evidence(family, review)
    if state in RELEASE_STATES:
        closure, verdict = RELEASE_STATES[state]
        return {
            "state": closure,
            "verdict": verdict,
            "released": True,
            "requires": "لا شيء؛ التصنيف البنيوي مستنفد في المراجعة العضوية",
            "note": f"التصنيف العضوي الأخير: {state}",
            "evidence": f"حالة الأسرة في أحدث مراجعة عضوية: {state}",
            "fan_sources": [],
        }
    held, note = true_held_state(state, review)
    blocker_lines = [
        line.strip() for line in review.splitlines() if line.startswith("- عائق:")
    ]
    return {
        "state": held,
        "verdict": "غير صادر",
        "released": False,
        "requires": note,
        "note": note,
        "evidence": blocker_lines[-1] if blocker_lines else f"حالة الأسرة: {state}",
        "fan_sources": [],
    }


def apply(section: str, family: str, item: dict) -> tuple[str, dict]:
    marker = f"<!-- ARABIC-FAN-CAMPAIGN:{BATCH}:{family} -->"
    if marker in section:
        return section, {"already_applied": True}
    section, old_blocker = replace_one(
        section,
        r"^-\s*عائق:\s*.+$",
        f"- عائق: النوع={item['state']}؛ يتطلب={item['requires']}",
    )
    if "النوع=TOOL-GAP" not in old_blocker:
        raise ValueError(f"{family}: not a TOOL-GAP card")
    section, old_closure = replace_one(
        section,
        r"^-\s*حالةُ الإغلاق:\s*.+$",
        f"- حالةُ الإغلاق: {item['state']}",
    )
    if item["verdict"] == "ROOT-TRACE":
        verdict_line = (
            "- الحكم (استكشاف): ROOT-TRACE للعضو المسمى في أحدث مراجعة عضوية "
            "وحده؛ لا وراثة عبر بقية الأسرة."
        )
    elif item["verdict"] == "LOANWORD":
        verdict_line = (
            "- الحكم (استكشاف): LOANWORD للأعضاء التي سمت المراجعة مسار قرضها؛ "
            "لا حكم نسب."
        )
    else:
        verdict_line = f"- الحكم (استكشاف): غير صادر؛ {item['note']}."
    section, old_verdict = replace_one(
        section, r"^-\s*الحكم \(استكشاف\):\s*.+$", verdict_line
    )
    appendix = "\n".join(
        [
            "",
            marker,
            f"- ملحقُ مصالحةِ المروحةِ والمراجعة العضوية، {DATE}:",
            f"  - أحدث مصير عضوي: {item['state']}.",
            f"  - الدليل المختصر: {item['evidence']}",
            "  - الحسم: "
            + (
                f"{item['verdict']}؛ خرجت البطاقة من التعليق."
                if item["released"]
                else f"غير صادر؛ بقيت البطاقة معلقة بسبب {item['state']} لا TOOL-GAP."
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
    parts, records, seen = [], [], set()
    cursor = 0
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
        if family and is_target and family in reviews:
            if family in seen:
                raise ValueError(f"duplicate target card: {family}")
            seen.add(family)
            item = decision(family, reviews[family])
            section, changes = apply(section, family, item)
            records.append({"family": family, **item, "changes": changes})
        parts.append(section)
        cursor = end
    parts.append(text[cursor:])

    if not POSITIVE_FAMILIES.issubset(seen):
        raise ValueError(
            f"positive review cards missing: {sorted(POSITIVE_FAMILIES - seen)}"
        )
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
                "# محضر حملة فك الحبس، الآرامية، الدفعة 05",
                "",
                f"**التاريخ:** {DATE}.",
                "",
                "صالحَت هذه الدفعة البطاقة الأصلية مع أحدث مراجعة عضوية لها. لم تعد إشارة TOOL-GAP التاريخية تعلو المصير العضوي الأحدث.",
                "",
                "## الرقمان المطلوبان",
                "",
                f"- خرج من التعليق: {len(released)}.",
                f"- توزيع الأحكام والتصنيفات الخارجة: {released_text}.",
                "",
                "## الباقي بعد استنفاد المروحة",
                "",
                f"- أعيد توصيفه بسبب حقيقي: {held_text}.",
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
