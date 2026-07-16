#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from recovery_pipeline.proof import load_preregistration, require_execution_authority


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the recovery proof preregistration and its run gate.")
    parser.add_argument("command", choices=("validate", "execution-check"))
    args = parser.parse_args()
    payload = load_preregistration()
    if args.command == "validate":
        print(f"proof preregistration: VALID ({payload['status']})")
        return 0
    try:
        require_execution_authority(payload)
    except PermissionError as error:
        print(f"LOCKED: {error}")
        return 2
    print("proof preregistration: AUTHOR-SIGNED; execution gate is open")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
