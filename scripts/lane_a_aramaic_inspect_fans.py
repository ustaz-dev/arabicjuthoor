#!/usr/bin/env python3
"""Read-only compact display of old-Arabic fan matches for lane A."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEARCH = ROOT / "scripts" / "search_arabic_root_senses.py"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    roots = set(sys.argv[1:])
    spec = importlib.util.spec_from_file_location("lane_a_fan_search", SEARCH)
    if spec is None or spec.loader is None:
        raise RuntimeError("تعذر تحميل أداة المروحة")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    matches = module.matches_for_roots(ROOT / "Resources", roots, 550)
    for root in sorted(roots):
        print(f"## {root}")
        for row in matches.get(root, []):
            source_id = module.canonical_source_id(str(row.get("source") or ""))
            if source_id in {
                "lisan",
                "taj_al_arus",
                "al_sihah",
                "al_muhkam",
                "kitab_al_ayn",
                "asas_al_balagha",
            }:
                print(
                    f"{source_id}\t{row.get('source')}\t"
                    f"{row.get('definition')}"
                )


if __name__ == "__main__":
    main()
