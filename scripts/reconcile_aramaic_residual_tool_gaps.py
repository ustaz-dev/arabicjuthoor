#!/usr/bin/env python3
"""Remove stale Aramaic TOOL-GAP companions after the Arabic-fan campaign.

The structured blocker already records the true remaining obstacle.  Older
closure prose still mentions TOOL-GAP as a companion, which makes the ledger
report the Arabic fan as unfinished.  This pass preserves the old closure in
an audit note and makes the current closure agree with the structured field.
It also closes two dated industrial tasks that were completed later.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
REPORT = (
    ROOT
    / "cache"
    / "recovery_pipeline"
    / "arabic-fan-campaign-aramaic-batch-07.json"
)
SECTION = re.compile(r"(?=^### )", re.MULTILINE)
BLOCKER = re.compile(
    r"^-\s*عائق:\s*النوع\s*=\s*(?P<type>[A-Z\-]+)"
    r"\s*[؛;]\s*يتطلب\s*=\s*(?P<required>[^\n]+)",
    re.MULTILINE,
)
CLOSURE = re.compile(
    r"^(?P<prefix>-\s*حالةُ?\s*الإغلاق[^\n]*?:\s*)"
    r"(?P<value>[^\n]+)$",
    re.MULTILINE,
)
COMPLETED_HEADINGS = {
    "### إعادةُ توسيم: توقيعُ قاعدةِ الألفِ وانفتاحُ أسرِ النمط (2026-07-21)",
    "### إعادةُ توسيم: المراجعةُ المضادّةُ الثالثةُ لحصادِ الموجةِ ب (2026-07-21)",
}


def transform(text: str) -> tuple[str, dict[str, object]]:
    parts = SECTION.split(text)
    output: list[str] = []
    retained = Counter()
    stale_companions = 0
    closures = 0

    for part in parts:
        if not part.startswith("### "):
            output.append(part)
            continue
        heading = part.split("\n", 1)[0]
        blocker = BLOCKER.search(part)
        if not blocker:
            output.append(part)
            continue
        blocker_type = blocker.group("type")

        if heading in COMPLETED_HEADINGS and blocker_type == "TOOL-GAP":
            old_line = blocker.group(0)
            new_line = (
                "- عائق: النوع=READY؛ يتطلب=منجز في البطاقات والمحاضر "
                "اللاحقة المثبتة؛"
            )
            part = part[: blocker.start()] + new_line + part[blocker.end() :]
            part += (
                "\n- استدراك بنيوي مؤرخ 2026-07-25: أُغلق العائق الصناعي "
                f"بعد إنجاز مطلوبه؛ السطر السابق محفوظ نصًا: `{old_line}`.\n"
            )
            closures += 1
            output.append(part)
            continue

        closure = CLOSURE.search(part)
        if (
            blocker_type != "TOOL-GAP"
            and closure
            and "TOOL-GAP" in closure.group("value")
        ):
            old_value = closure.group("value").strip()
            new_closure = closure.group("prefix") + blocker_type + "."
            part = part[: closure.start()] + new_closure + part[closure.end() :]
            part += (
                "\n- استدراك بنيوي مؤرخ 2026-07-25: استُنفدت المروحة "
                f"فزال `TOOL-GAP` المصاحب؛ بقي العائق الحقيقي `{blocker_type}`. "
                f"حالة الإغلاق السابقة محفوظة: `{old_value}`.\n"
            )
            stale_companions += 1
            retained[blocker_type] += 1
        output.append(part)

    payload: dict[str, object] = {
        "schema": "arabic-fan-campaign-aramaic-batch-07-v1",
        "reviewed": stale_companions + closures,
        "positive_connections": 0,
        "closures": closures,
        "stale_tool_gap_companions_removed": stale_companions,
        "retained_true_blockers": dict(sorted(retained.items())),
    }
    return "".join(output), payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    original = PATH.read_text(encoding="utf-8")
    transformed, payload = transform(original)

    if args.check:
        if payload["reviewed"]:
            raise SystemExit(
                "FAIL: residual Aramaic TOOL-GAP reconciliation is pending"
            )
        print("Aramaic residual TOOL-GAP check: CLEAN")
        return 0

    temporary = PATH.with_suffix(PATH.suffix + ".tmp")
    temporary.write_text(transformed, encoding="utf-8")
    temporary.replace(PATH)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    temporary_report = REPORT.with_suffix(REPORT.suffix + ".tmp")
    temporary_report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_report.replace(REPORT)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
