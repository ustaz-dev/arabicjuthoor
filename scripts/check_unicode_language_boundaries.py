#!/usr/bin/env python3
"""Check language-separating character tables against Unicode names."""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / "data" / "unicode-language-boundaries.json"
sys.path.insert(0, str(ROOT / "scripts"))

from recovery_pipeline.sources import _script_lemma_candidate  # noqa: E402


def codepoint(value: str) -> int:
    if not value.startswith("U+"):
        raise ValueError(f"invalid code point: {value}")
    return int(value[2:], 16)


def main() -> int:
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    errors: list[str] = []
    checked = 0
    for boundary in policy["boundaries"]:
        first = codepoint(boundary["first"])
        last = codepoint(boundary["last"])
        prefix = str(boundary["required_name_prefix"])
        for value in range(first, last + 1):
            character = chr(value)
            name = unicodedata.name(character, "")
            checked += 1
            if not name.startswith(prefix):
                errors.append(f"U+{value:04X}: {name!r} does not start with {prefix!r}")
            if _script_lemma_candidate(character, "ancient greek"):
                errors.append(f"U+{value:04X}: legacy Coptic accepted as Ancient Greek")
        for letter in boundary.get("letters", []):
            if not isinstance(letter, dict):
                errors.append(f"{boundary['id']}: legacy letter entry is not explicit")
                continue
            expected = str(letter["name"])
            for case in ("capital", "small"):
                character = str(letter[case])
                name = unicodedata.name(character, "")
                if expected not in name or not name.startswith("COPTIC "):
                    errors.append(
                        f"{boundary['id']}: {case} {character!r} is {name!r}, expected COPTIC {expected}"
                    )
                if _script_lemma_candidate(character, "ancient greek"):
                    errors.append(
                        f"{boundary['id']}: {case} {character!r} accepted as Ancient Greek"
                    )

    for control in policy["positive_controls"]:
        text = str(control["text"])
        language = str(control["language"])
        if not _script_lemma_candidate(text, language):
            errors.append(f"positive control rejected: {language} {text!r}")
    for control in policy["negative_controls"]:
        text = str(control["text"])
        language = str(control["language"])
        if _script_lemma_candidate(text, language):
            errors.append(f"negative control accepted: {language} {text!r}")

    forbidden = "\\u0370-" + "\\u03ff"
    for path in (ROOT / "scripts").rglob("*.py"):
        if path == Path(__file__):
            continue
        if forbidden.casefold() in path.read_text(encoding="utf-8").casefold():
            errors.append(
                f"{path.relative_to(ROOT)}: unsplit Greek-and-Coptic legacy range"
            )

    if errors:
        print("\n".join(f"FAIL: {error}" for error in errors))
        return 1
    print(
        "Unicode language boundaries: CLEAN "
        f"({checked} named legacy Coptic code points, "
        f"{len(policy['positive_controls'])} positive and "
        f"{len(policy['negative_controls'])} negative controls)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
