#!/usr/bin/env python3
"""Backfill machine-readable obstacles for local Aramaic gap reviews.

The gap state already chosen by the human review remains unchanged.  This
formatter only gives that state the exact obstacle syntax required by the
exploration charter and attaches the stable member identifier.  It never
turns a gap into a verdict or a verdict into a gap.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHARDS = tuple(
    ROOT / "scratch" / f"aramaic-completion-shard-{letter}.md"
    for letter in ("a", "b", "c")
)
MEMBER = re.compile(
    r"^(?P<line>- العضو:\s*`(?P<entry>kaikki_aramaic:[^`]+)`.*)$",
    re.MULTILINE,
)
RESULT = re.compile(
    r"النتيجة:\s*`?"
    r"(?P<status>OPEN-CANDIDATE|TOOL-GAP|LAW-GAP|SOURCE-GAP|"
    r"MORPHOLOGY-GAP)"
)
REQUIRES = {
    "OPEN-CANDIDATE": "جسر دلالي موثق أو شاهد أقدم يحسم المرشح",
    "TOOL-GAP": "قراءة الجذر أو النواة في الأداة المجمّدة بقرار المؤلف",
    "LAW-GAP": "صف صوتي منشور وموقع في النطاق المطلوب",
    "SOURCE-GAP": "مصدر تاريخي أو معجمي منشور يحسم المسار",
    "MORPHOLOGY-GAP": "تحليل صرفي منشور للصورة الآرامية",
}


def transform(path: Path) -> tuple[str, int]:
    text = path.read_text(encoding="utf-8")
    text = re.sub(
        r"النتيجة\s+(?=`?(?:OPEN-CANDIDATE|TOOL-GAP|LAW-GAP|"
        r"SOURCE-GAP|MORPHOLOGY-GAP|READY|ROOT-TRACE|NUCLEUS-))",
        "النتيجة: ",
        text,
    )
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        line = match.group("line")
        result = RESULT.search(line)
        if not result:
            return line
        entry = match.group("entry")
        existing = re.compile(
            r"^- عائق:\s*النوع="
            + re.escape(result.group("status"))
            + r"؛[^\n]*العضو="
            + re.escape(entry)
            + r"(?:؛|$)",
            re.MULTILINE,
        )
        if existing.search(text):
            return line
        count += 1
        status = result.group("status")
        return (
            line
            + "\n- عائق: النوع="
            + status
            + "؛ يتطلب="
            + REQUIRES[status]
            + "؛ العضو="
            + entry
            + "؛"
        )

    return MEMBER.sub(replace, text), count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    results: dict[str, int] = {}
    for path in SHARDS:
        if not path.exists():
            raise ValueError(f"missing shard: {path.relative_to(ROOT)}")
        transformed, additions = transform(path)
        results[path.name] = additions
        if args.check:
            if additions:
                raise ValueError(
                    f"{path.name} misses {additions} structured obstacles"
                )
            continue
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(transformed, encoding="utf-8")
        temporary.replace(path)
    print(json.dumps(results, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
