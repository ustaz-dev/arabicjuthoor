# -*- coding: utf-8 -*-
"""أعد بناء سجل قول CCL في الأصل، بوصفه خبرًا لا بوابة استبعاد."""
from __future__ import annotations

import argparse
import json
import sys

import reexamine_coptic_arabic as H


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    payload = H.published_origin_payload()
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not H.ORIGIN_REGISTER.exists() or H.ORIGIN_REGISTER.read_text(encoding="utf-8") != rendered:
            print("STALE: data/non-coptic-borrowings-in-coptic.json")
            return 1
        print(
            "CLEAN: CCL published-origin register "
            f"{payload['counts']['processed_queue_cards']} cards; "
            f"denominator {payload['counts']['coptic_denominator']}; "
            f"excluded by origin {payload['counts']['excluded_by_published_origin']}"
        )
        return 0
    H.atomic_write(H.ORIGIN_REGISTER, rendered)
    print(
        "BUILT: CCL published-origin register "
        f"{payload['counts']['processed_queue_cards']} cards; "
        f"denominator {payload['counts']['coptic_denominator']}; "
        f"excluded by origin {payload['counts']['excluded_by_published_origin']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
