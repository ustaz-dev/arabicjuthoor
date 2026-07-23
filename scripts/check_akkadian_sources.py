#!/usr/bin/env python3
"""Verify the pinned Akkadian inventory and, optionally, the local CAD copy."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "04-cross-linguistic/normalization-profiles/akkadian.json"
CAD_PIN_PATH = ROOT / "04-cross-linguistic/data/akkadian-cad-volume-pin.json"


def digest(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_kaikki() -> dict[str, object]:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    source = profile["source"]
    path = ROOT / source["path"]
    problems: list[str] = []
    if not path.is_file():
        return {"path": str(path), "problems": ["source file is missing"]}

    actual_size = path.stat().st_size
    if actual_size != source["expected_size_bytes"]:
        problems.append(
            f"size mismatch: {actual_size} != {source['expected_size_bytes']}"
        )
    for algorithm in ("md5", "sha256"):
        actual = digest(path, algorithm)
        if actual != source[algorithm]:
            problems.append(f"{algorithm} mismatch: {actual} != {source[algorithm]}")

    rows = 0
    words: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError as error:
                problems.append(f"invalid JSON at line {line_number}: {error}")
                continue
            rows += 1
            words.add(str(entry.get("word", "")))
            if entry.get("lang_code") != source["expected_language_code"]:
                problems.append(
                    f"language-code mismatch at line {line_number}: "
                    f"{entry.get('lang_code')!r}"
                )
            for field in ("word", "pos", "senses"):
                if not entry.get(field):
                    problems.append(f"missing {field} at line {line_number}")
    if rows != source["expected_entries"]:
        problems.append(f"row mismatch: {rows} != {source['expected_entries']}")

    return {
        "path": source["path"],
        "bytes": actual_size,
        "rows": rows,
        "distinct_words": len(words),
        "problems": problems,
    }


def verify_cad(require_local: bool) -> dict[str, object]:
    pin = json.loads(CAD_PIN_PATH.read_text(encoding="utf-8"))
    volumes = pin["volumes"]
    problems: list[str] = []
    names = [item["file"] for item in volumes]
    if len(volumes) != pin["volume_count"]:
        problems.append(
            f"volume-count mismatch: {len(volumes)} != {pin['volume_count']}"
        )
    if len(names) != len(set(names)):
        problems.append("duplicate CAD file name in pin")
    pinned_bytes = sum(int(item["bytes"]) for item in volumes)
    if pinned_bytes != pin["total_bytes"]:
        problems.append(
            f"total-byte mismatch: {pinned_bytes} != {pin['total_bytes']}"
        )

    verified = 0
    if require_local:
        directory = ROOT / pin["local_path"]
        for item in volumes:
            path = directory / item["file"]
            if not path.is_file():
                problems.append(f"missing CAD file: {item['file']}")
                continue
            if path.stat().st_size != item["bytes"]:
                problems.append(f"size mismatch for CAD file: {item['file']}")
                continue
            with path.open("rb") as handle:
                if handle.read(5) != b"%PDF-":
                    problems.append(f"invalid PDF signature: {item['file']}")
                    continue
            actual_sha256 = digest(path, "sha256")
            if actual_sha256 != item["sha256"]:
                problems.append(f"sha256 mismatch for CAD file: {item['file']}")
                continue
            verified += 1

        partials = sorted(path.name for path in directory.glob("*.download"))
        if partials:
            problems.append(f"partial CAD downloads remain: {partials}")

    return {
        "pin": str(CAD_PIN_PATH.relative_to(ROOT)),
        "volume_count": len(volumes),
        "total_bytes": pinned_bytes,
        "local_files_verified": verified,
        "local_required": require_local,
        "problems": problems,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-local-cad",
        action="store_true",
        help="verify every ignored local CAD PDF against the tracked pin",
    )
    args = parser.parse_args()

    result = {
        "kaikki": verify_kaikki(),
        "cad": verify_cad(args.require_local_cad),
    }
    problems = result["kaikki"]["problems"] + result["cad"]["problems"]
    result["passed"] = not problems
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
