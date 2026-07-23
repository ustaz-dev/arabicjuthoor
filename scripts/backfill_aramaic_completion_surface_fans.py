#!/usr/bin/env python3
"""Mechanically add direct-surface fan evidence to Aramaic shard member lines.

Human readers decide whether the sense matches.  This formatter only inserts
the already generated retrieval record and its named old lexica, so the final
coverage validator can prove that the anti-self-sabotage surface pass was
visible for every applicable member.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DIRECT = ROOT / "cache" / "recovery_pipeline" / "aramaic-direct-surface-fans.json"
SHARDS = tuple(
    ROOT / "scratch" / f"aramaic-completion-shard-{letter}.md"
    for letter in ("a", "b", "c")
)
MEMBER = re.compile(r"^- العضو:\s*`([^`]+)`.*$", re.MULTILINE)


def field(item: dict) -> str:
    fan = item["independent_fan"]
    sources = "، ".join(
        source["source_label"] for source in fan["selected_sources"]
    )
    registry = "مسجل مرخص" if item["already_licensed_candidate"] else "فجوة سجل"
    return (
        f" السطح المباشر={item['direct_surface_root']}؛ {registry}؛ "
        f"المروحة الكاملة={sources}؛ مرشح استرجاعي لا حكم آلي."
    )


def transform(path: Path, records: dict[str, dict]) -> tuple[str, int]:
    text = path.read_text(encoding="utf-8")
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        line = match.group(0)
        entry_id = match.group(1)
        item = records.get(entry_id)
        if not item or "السطح المباشر=" in line:
            return line
        count += 1
        return line.rstrip() + field(item)

    return MEMBER.sub(replace, text), count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = json.loads(DIRECT.read_text(encoding="utf-8"))
    records = {item["entry_id"]: item for item in payload["records"]}
    results = {}
    for path in SHARDS:
        if not path.exists():
            raise ValueError(f"missing shard: {path.relative_to(ROOT)}")
        transformed, additions = transform(path, records)
        results[path.name] = additions
        if args.check:
            if additions:
                raise ValueError(
                    f"{path.name} is missing {additions} direct-surface fields"
                )
            continue
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(transformed, encoding="utf-8")
        temporary.replace(path)
    print(json.dumps(results, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
