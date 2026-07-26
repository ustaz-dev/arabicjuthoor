#!/usr/bin/env python3
"""Resolve the second Aramaic Arabic-fan batch by card identity.

This batch folds already completed clinic fans into their original TOOL-GAP
cards, isolates named external loans and proper names, and copies four later
organic ROOT-TRACE judgments back to the older suspended identity cards.
"""
from __future__ import annotations

from collections import Counter
import json
import re
import sys
import tempfile
import unicodedata
from pathlib import Path

from search_arabic_root_senses import DEFAULT_RESOURCES, root_sense_fan


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
AUDIT_JSON = (
    ROOT / "cache" / "recovery_pipeline"
    / "arabic-fan-campaign-aramaic-batch-02.json"
)
AUDIT_MD = (
    ROOT / "05-audits"
    / "2026-07-25-arabic-fan-campaign-aramaic-batch-02.md"
)
DATE = "2026-07-25"
BATCH = "ARAMAIC-02"
CARD_HEADING = re.compile(r"^### (?:بطاقة|إعادةُ توسيم).*$", re.MULTILINE)
FAMILY_ID = re.compile(r"aramaic:family:[0-9a-f]+")


LATER_POSITIVES = {
    "aramaic:family:9ddd43c3acf10619c517669b": (
        "قرن",
        "القرن المسمى في المعاجم يقابل קרנא في الحكم العضوي اللاحق.",
    ),
    "aramaic:family:1d39ce152c35e2ea857683da": (
        "فعل",
        "الفعل والعمل يقابلان פעלא العامل في الحكم العضوي اللاحق.",
    ),
    "aramaic:family:a3ad028fa19fcd5385d5894c": (
        "عفر",
        "العفر والتراب يقابلان עפרא في الحكم العضوي اللاحق.",
    ),
    "aramaic:family:33c94e111c52b356b8c4166e": (
        "ملك",
        "الملك يقابل מלכא في الحكم العضوي اللاحق.",
    ),
}

EXTERNAL_LOANS = {
    "aramaic:family:9b3e0dc962b76da98d7b1596":
        "اليونانية القديمة δεῖγμα بنص حقل الاشتقاق في المصدر",
    "aramaic:family:bf3a6490291e04ee9fbd60f1":
        "اليونانية القديمة λῃστής بنص حقل الاشتقاق في المصدر",
    "aramaic:family:2c14265c123cc56d93147381":
        "اليونانية القديمة σουδάριον من اللاتينية sūdārium بنص المصدر",
    "aramaic:family:be18859541d25eb26e992e01":
        "اليونانية القديمة παιδαγωγός بنص حقل الاشتقاق في المصدر",
    "aramaic:family:9de4b23fb5249a1e7c1adf11":
        "الفارسية القديمة *hammārakarah بنص حقل الاشتقاق في المصدر",
    "aramaic:family:8527050eeb125452efc38e63":
        "الإيرانية الوسطى بنص حقل الاشتقاق في المصدر",
    "aramaic:family:d9408cd2cd0e9b4ea24212eb":
        "الفارسية الوسطى *sandān بنص حقل الاشتقاق في المصدر",
}

INTRA_HOUSE_TRANSFER = {
    "aramaic:family:e80b74d5acf96c0053228a32":
        "الأكادية kibrītu مانح أخت مسمى؛ يحال الزوج إلى الأكادية ولا يعد خروجا من البيت"
}

UNRESOLVED_LOANS = {
    "aramaic:family:06b275382d77a2d0b5985ed7":
        "اتجاه انتقال ترجم بين الآرامية والعربية غير مثبت بمصدر مسمى",
    "aramaic:family:5d6730f6220806490535d980":
        "المانح الإيراني المقترح لاسم الخيل غير مثبت في حقل المصدر",
    "aramaic:family:2adbac08f555310a95ab9884":
        "اتجاه انتقال تخوم داخل البيت السامي غير مثبت بمصدر مسمى",
}


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(unicodedata.normalize("NFC", text))
        temporary = Path(handle.name)
    temporary.replace(path)


def first_line(section: str, pattern: str) -> str:
    match = re.search(pattern, section, re.MULTILINE)
    if not match:
        raise ValueError(f"missing card field: {pattern}")
    return match.group(0)


def replace_first(section: str, pattern: str, replacement: str) -> str:
    changed, count = re.subn(pattern, replacement, section, count=1, flags=re.MULTILINE)
    if count != 1:
        raise ValueError(f"expected one card field, found {count}: {pattern}")
    return changed


def clinic_helper(section: str) -> str:
    values = re.findall(r"النتيجة المساعدة=`([^`]+)`", section)
    return values[-1] if values else ""


def clinic_after(section: str) -> str:
    values = re.findall(r"الحالةُ بعد العيادة:\s*(.+)", section)
    return values[-1].strip() if values else ""


def decision_for(family: str, section: str) -> dict | None:
    if family in LATER_POSITIVES:
        root, sense = LATER_POSITIVES[family]
        fan = root_sense_fan(DEFAULT_RESOURCES, root, None)["independent_fan"]
        if not fan["judgment_ready"] or len(fan["selected_sources"]) < 2:
            raise ValueError(f"{family}: later positive lacks a complete fan")
        return {
            "class": "later-positive",
            "state": "READY",
            "requires": "المراجعة المضادة الثالثة قبل الإيداع",
            "verdict": "ROOT-TRACE",
            "note": sense,
            "fan": {
                "root": root,
                "sources": [
                    item["source_label"] for item in fan["selected_sources"]
                ],
            },
        }

    helper = clinic_helper(section)
    after = clinic_after(section)
    if helper == "name":
        return {
            "class": "proper-name",
            "state": "PROPER-NAME-ISOLATED",
            "requires": "لا شيء للحكم النسبي؛ العلم معزول ولا يورث قراءة",
            "verdict": "غير صادر",
            "note": "العلم أو الاسم المركب معزول بنص القراءة العضوية.",
            "fan": None,
        }
    if helper == "loan":
        if family in EXTERNAL_LOANS:
            return {
                "class": "external-loan",
                "state": "LOAN-ROUTE-ISOLATED",
                "requires": "لا شيء؛ المانح الخارجي مسمى في المصدر",
                "verdict": "LOANWORD",
                "note": EXTERNAL_LOANS[family],
                "fan": None,
            }
        if family in INTRA_HOUSE_TRANSFER:
            return {
                "class": "intra-house-transfer",
                "state": "INTRA-HOUSE-TRANSFER",
                "requires": "إحالة السلسلة إلى زوج المانح الأخت في سجل القروض",
                "verdict": "غير صادر",
                "note": INTRA_HOUSE_TRANSFER[family],
                "fan": None,
            }
        if family in UNRESOLVED_LOANS:
            return {
                "class": "unresolved-loan-route",
                "state": "SOURCE-GAP",
                "requires": UNRESOLVED_LOANS[family],
                "verdict": "غير صادر",
                "note": "المروحة لا تحسم اتجاه الانتقال، فبقي السبب مصدريا لا أداتيا.",
                "fan": None,
            }
        raise ValueError(f"{family}: unclassified loan helper")
    if helper in {"semantic-mismatch", "gap"}:
        state = "MORPHOLOGY-GAP" if "MORPHOLOGY-GAP" in after else "OPEN-CANDIDATE"
        reason = re.sub(r"^النوع=", "", after) or (
            "المرشح يحتاج قراءة دلالية عضوية بعد المروحة"
        )
        return {
            "class": helper,
            "state": state,
            "requires": reason,
            "verdict": "غير صادر",
            "note": (
                "المروحة اكتملت ولم تمنح معنى مطابقا."
                if helper == "semantic-mismatch"
                else "استنفدت المروحة المتاحة ولم يخرج مقابل كامل صالح للحكم."
            ),
            "fan": "clinic-complete",
        }
    return None


def apply_decision(
    section: str, family: str, decision: dict
) -> tuple[str, dict]:
    marker = f"<!-- ARABIC-FAN-CAMPAIGN:{BATCH}:{family} -->"
    if marker in section:
        return section, {"already_applied": True}
    old_blocker = first_line(section, r"^-\s*عائق:\s*.+$")
    old_closure = first_line(section, r"^-\s*حالةُ الإغلاق:\s*.+$")
    old_verdict = first_line(section, r"^-\s*الحكم \(استكشاف\):\s*.+$")
    if "النوع=TOOL-GAP" not in old_blocker:
        raise ValueError(f"{family}: target card is no longer TOOL-GAP")

    blocker = f"- عائق: النوع={decision['state']}؛ يتطلب={decision['requires']}"
    closure = f"- حالةُ الإغلاق: {decision['state']}"
    if decision["verdict"] == "غير صادر":
        verdict = f"- الحكم (استكشاف): غير صادر؛ {decision['note']}"
    else:
        verdict = (
            f"- الحكم (استكشاف): {decision['verdict']} للسلسلة العضوية "
            "المسماة وحدها؛ لا وراثة عبر عضو مخالف."
        )
    section = replace_first(section, r"^-\s*عائق:\s*.+$", blocker)
    section = replace_first(section, r"^-\s*حالةُ الإغلاق:\s*.+$", closure)
    section = replace_first(
        section, r"^-\s*الحكم \(استكشاف\):\s*.+$", verdict
    )
    if isinstance(decision["fan"], dict):
        fan_text = (
            f"الجذر `{decision['fan']['root']}`؛ "
            + " + ".join(decision["fan"]["sources"])
            + "؛ مروحة كاملة غير مقتطعة"
        )
    elif decision["fan"] == "clinic-complete":
        fan_text = "المروحة الكاملة المسجلة في ملحق عيادة الكلمات الصعبة"
    else:
        fan_text = "لا يستعمل الحكم مروحة عربية موجبة"
    appendix = "\n".join(
        [
            "",
            marker,
            f"- ملحقُ حملةِ فكّ الحبس، {DATE}:",
            f"  - المروحة أو المصفاة: {fan_text}.",
            f"  - الحسم: {decision['verdict']}؛ {decision['note']}",
            "  - السجل التاريخي المحفوظ:",
            f"    - `{old_blocker}`",
            f"    - `{old_closure}`",
            f"    - `{old_verdict}`",
        ]
    )
    return section.rstrip() + "\n" + appendix + "\n\n", {
        "already_applied": False,
        "old_blocker": old_blocker,
        "new_blocker": blocker,
        "old_closure": old_closure,
        "new_closure": closure,
        "old_verdict": old_verdict,
        "new_verdict": verdict,
    }


def render_audit(payload: dict) -> str:
    summary = payload["summary"]
    distribution = "، ".join(
        f"{key}={value}"
        for key, value in summary["released_verdict_counts"].items()
    )
    held = "، ".join(
        f"{key}={value}" for key, value in summary["held_state_counts"].items()
    )
    return "\n".join(
        [
            "# محضر حملة فك الحبس، الآرامية، الدفعة 02",
            "",
            f"**التاريخ:** {DATE}.",
            "",
            "دفعة محلية للمراجعة المضادة الثالثة، معدودة بمعرف البطاقة.",
            "",
            "## الرقمان المطلوبان",
            "",
            f"- خرج من التعليق: {summary['released_from_suspension']}.",
            f"- توزيع أحكام الخارج: {distribution}.",
            "",
            "## الباقي بسبب حقيقي",
            "",
            f"- {held}.",
            "",
            "تعزل الأعلام بلا حكم نسب، ويعد انتقال الكبريت من الأكادية انتقالا داخل البيت لا قرضا خارجيا.",
            "",
        ]
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    text = READING.read_text(encoding="utf-8")
    starts = list(CARD_HEADING.finditer(text))
    parts = []
    cursor = 0
    records = []
    seen: set[str] = set()
    for index, heading in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        parts.append(text[cursor:heading.start()])
        section = text[heading.start():end]
        family_match = FAMILY_ID.search(heading.group(0))
        family = family_match.group(0) if family_match else ""
        is_tool_gap = bool(
            re.search(
                r"^-\s*عائق:\s*النوع\s*=\s*TOOL-GAP\b",
                section,
                re.MULTILINE,
            )
        )
        marker = f"<!-- ARABIC-FAN-CAMPAIGN:{BATCH}:{family} -->"
        if family and (is_tool_gap or marker in section):
            decision = decision_for(family, section)
            if decision:
                if family in seen:
                    raise ValueError(f"duplicate batch target: {family}")
                seen.add(family)
                section, changes = apply_decision(section, family, decision)
                released = decision["state"] not in {
                    "TOOL-GAP",
                    "LAW-GAP",
                    "SOURCE-GAP",
                    "OPEN-CANDIDATE",
                    "MORPHOLOGY-GAP",
                }
                records.append(
                    {
                        "family": family,
                        **decision,
                        "released_from_suspension": released,
                        "changes": changes,
                    }
                )
        parts.append(section)
        cursor = end
    parts.append(text[cursor:])

    expected = 4 + 7 + 11 + 19 + 33
    if len(records) != expected:
        raise ValueError(f"expected {expected} batch records, found {len(records)}")
    updated = "".join(parts)
    if unicodedata.normalize("NFC", updated) != updated:
        raise ValueError("updated Aramaic reading is not NFC")
    atomic_write(READING, updated)

    released_verdicts = Counter(
        item["verdict"] if item["verdict"] != "غير صادر" else item["state"]
        for item in records
        if item["released_from_suspension"]
    )
    held_states = Counter(
        item["state"] for item in records if not item["released_from_suspension"]
    )
    payload = {
        "schema": "arabic-fan-campaign-batch-v1",
        "status": "LOCAL-THIRD-LENS-REVIEW-REQUIRED",
        "date": DATE,
        "batch": BATCH,
        "language": "aramaic",
        "unit": "card-identity",
        "summary": {
            "cards_reviewed": len(records),
            "released_from_suspension": sum(
                item["released_from_suspension"] for item in records
            ),
            "released_verdict_counts": dict(sorted(released_verdicts.items())),
            "held_state_counts": dict(sorted(held_states.items())),
        },
        "records": records,
    }
    atomic_write(
        AUDIT_JSON,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    atomic_write(AUDIT_MD, render_audit(payload))
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
