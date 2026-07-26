#!/usr/bin/env python3
"""Reconcile the three pre-rank Egyptian TOOL-GAP cards."""
from __future__ import annotations

import json
import re
import tempfile
import unicodedata
from pathlib import Path

from search_arabic_root_senses import DEFAULT_RESOURCES, root_sense_fan


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "egyptian.md"
SECTION = re.compile(r"(?=^### )", re.MULTILINE)
BLOCKER = re.compile(r"^-\s*عائق:\s*.+$", re.MULTILINE)
CLOSURE = re.compile(r"^-\s*حالةُ الإغلاق:\s*.+$", re.MULTILINE)
VERDICT = re.compile(r"^-\s*الحكم \(استكشاف\):\s*.+$", re.MULTILINE)
BATCH = "EGYPTIAN-LEGACY-003"
DATE = "2026-07-25"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
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
    return (
        section[: match.start()] + replacement + section[match.end() :],
        match.group(0),
    )


def apply(
    section: str,
    key: str,
    state: str,
    verdict: str,
    note: str,
) -> tuple[str, dict[str, str]]:
    marker = f"<!-- ARABIC-FAN-CAMPAIGN:{BATCH}:{key} -->"
    if marker in section:
        return section, {"already_applied": "true"}
    section, old_blocker = replace_one(
        section, BLOCKER, f"- عائق: النوع={state}؛ يتطلب={note}؛"
    )
    if "النوع=TOOL-GAP" not in old_blocker:
        raise ValueError(f"{key}: target no longer TOOL-GAP")
    section, old_closure = replace_one(
        section, CLOSURE, f"- حالةُ الإغلاق: {state}"
    )
    section, old_verdict = replace_one(
        section, VERDICT, f"- الحكم (استكشاف): {verdict}"
    )
    appendix = "\n".join(
        [
            "",
            marker,
            f"- مصالحة البطاقات المصرية السابقة للترتيب، {DATE}:",
            f"  - المصير: `{state}`؛ {note}.",
            "  - السجل التاريخي المحفوظ:",
            f"    - `{old_blocker}`",
            f"    - `{old_closure}`",
            f"    - `{old_verdict}`",
        ]
    )
    return section.rstrip() + "\n" + appendix + "\n\n", {
        "old_blocker": old_blocker,
        "old_closure": old_closure,
        "old_verdict": old_verdict,
    }


def main() -> int:
    fan = root_sense_fan(DEFAULT_RESOURCES, "خفع", None)["independent_fan"]
    if not fan["judgment_ready"] or len(fan["selected_sources"]) < 2:
        raise ValueError("خفع: two-source fan is incomplete")
    if any(
        any(term in str(source["definition"]) for term in ("قبض", "أمسك", "إمساك"))
        for source in fan["selected_sources"]
    ):
        raise ValueError("خفع: grip sense appeared; manual re-review required")

    text = READING.read_text(encoding="utf-8")
    output: list[str] = []
    records: list[dict[str, object]] = []
    khafa_seen = 0
    for section in SECTION.split(text):
        heading = section.split("\n", 1)[0] if section else ""
        if heading.startswith(
            "### بطاقة: šnf.t «scale (of fish)»، إعادةُ فتحٍ"
        ):
            changed, history = apply(
                section,
                "SHNFT",
                "READY",
                "NUCLEUS-ECHO؛ حكم التوأم المثبت في القراءة القبطية؛ لا حكم جديد مضاعف",
                "ربط البطاقة التاريخية بحكم التوأم المثبت في coptic.md",
            )
            output.append(changed)
            records.append(
                {
                    "card": "šnf.t",
                    "positive": True,
                    "closure": False,
                    "state": "READY",
                    "verdict": "NUCLEUS-ECHO",
                    "history": history,
                }
            )
            continue
        if heading.startswith("### بطاقة: ḫfꜥ «"):
            khafa_seen += 1
            if khafa_seen == 1:
                state = "OPEN-CANDIDATE"
                verdict = (
                    "غير صادر؛ مروحة خفع كاملة في اللسان والتاج، "
                    "ولا تسجل القبض أو الإمساك؛ بقي المرشح مفتوحا لا TOOL-GAP"
                )
                note = "جسر دلالي منشور يصل الضعف أو السقوط بالقبض"
                closure = False
            else:
                state = "REFERRED"
                verdict = (
                    "غير صادر؛ إحالة إلى بطاقة ḫfꜥ الكاملة السابقة، "
                    "ولا تضاعف وحدة المراجعة"
                )
                note = "محسوم بالإحالة إلى بطاقة ḫfꜥ السابقة"
                closure = True
            changed, history = apply(
                section, f"KHAFA-{khafa_seen}", state, verdict, note
            )
            output.append(changed)
            records.append(
                {
                    "card": f"ḫfꜥ-{khafa_seen}",
                    "positive": False,
                    "closure": closure,
                    "state": state,
                    "verdict": "غير صادر",
                    "fan_sources": [
                        row["source_label"] for row in fan["selected_sources"]
                    ],
                    "history": history,
                }
            )
            continue
        output.append(section)

    if len(records) != 3 or khafa_seen != 2:
        raise ValueError(
            f"expected šnf.t plus two ḫfꜥ cards, got {len(records)}"
        )
    updated = "".join(output)
    if unicodedata.normalize("NFC", updated) != updated:
        raise ValueError("Egyptian reading is not NFC")
    atomic_write(READING, updated)

    payload = {
        "schema": "arabic-fan-campaign-egyptian-legacy-v1",
        "status": "LOCAL-THIRD-LENS-REVIEW-REQUIRED",
        "date": DATE,
        "batch": BATCH,
        "summary": {
            "cards_reviewed": 3,
            "positive_connections": 1,
            "positive_note": "مصالحة بحكم مثبت سابقا، لا حكم جديد مضاعف",
            "closures": 1,
            "held_states": {"OPEN-CANDIDATE": 1},
        },
        "records": records,
    }
    cache = (
        ROOT
        / "cache"
        / "recovery_pipeline"
        / "arabic-fan-campaign-egyptian-legacy-003.json"
    )
    audit = (
        ROOT
        / "05-audits"
        / "2026-07-25-arabic-fan-campaign-egyptian-legacy-003.md"
    )
    atomic_write(cache, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    atomic_write(
        audit,
        "\n".join(
            [
                "# حملة المروحة المصرية، البطاقات الثلاث السابقة للترتيب",
                "",
                "## الرقمان المفصولان",
                "",
                "- الصلات الموجبة: 1، وهي مصالحة بطاقة شنف التاريخية مع حكم التوأم المثبت، لا حكم جديد مضاعف.",
                "- الإغلاقات: 1، إحالة نسخة خفع المكررة إلى بطاقتها الكاملة.",
                "",
                "- بقيت بطاقة خفع الأصلية `OPEN-CANDIDATE`: المروحة كاملة في اللسان والتاج ولا تحمل معنى القبض، فزال `TOOL-GAP` ولم يصدر نفي.",
                "- الدفعة محلية للمراجعة المضادة الثالثة، ولا رقم للنشر.",
                "",
            ]
        ),
    )
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
