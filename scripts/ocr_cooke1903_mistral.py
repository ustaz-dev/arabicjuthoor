#!/usr/bin/env python3
"""OCR Cooke 1903 (public domain) with Mistral OCR, for the Semitic script the 1903-era archive OCR could not read.

Why this exists
---------------
The Internet Archive full text of Cooke 1903 recovers the English apparatus (translations,
commentary, CIS numbers) but renders the Hebrew-square Phoenician text as noise. A modern
OCR model reads that script far better. This script fills exactly that gap.

Source status: Cooke, G. A., *A Text-book of North-Semitic Inscriptions*, Oxford Clarendon 1903.
Published 1903, public domain by age. Local copy: `Data raw/Cooke 1903.pdf`.

Credential
----------
Needs MISTRAL_API_KEY. The script never prints it. Provide it either as an environment
variable, or in a local untracked file `Data raw/.mistral_key` containing only the key.
Never commit the key.

Usage
-----
  python scripts/ocr_cooke1903_mistral.py --sample 5      # cheap quality probe first
  python scripts/ocr_cooke1903_mistral.py --all           # full book after the probe looks good
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "Data raw" / "Cooke 1903.pdf"
OUTDIR = ROOT / "Data raw" / "cooke1903_text" / "mistral_ocr"
KEYFILE = ROOT / "Data raw" / ".mistral_key"
API = "https://api.mistral.ai/v1"
MODEL = "mistral-ocr-latest"


def load_key() -> str:
    key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if not key and KEYFILE.exists():
        key = KEYFILE.read_text(encoding="utf-8").strip()
    if not key or key.upper().startswith("REPL"):
        sys.exit(
            "No usable MISTRAL_API_KEY.\n"
            "Set the environment variable, or put the key alone in: " + str(KEYFILE) + "\n"
            "The file is untracked; never commit it."
        )
    return key


def upload(key: str, path: Path) -> str:
    """Upload the PDF for OCR, return the file id."""
    with path.open("rb") as fh:
        r = requests.post(
            f"{API}/files",
            headers={"Authorization": f"Bearer {key}"},
            files={"file": (path.name, fh, "application/pdf")},
            data={"purpose": "ocr"},
            timeout=600,
        )
    r.raise_for_status()
    return r.json()["id"]


def signed_url(key: str, file_id: str, hours: int = 24) -> str:
    r = requests.get(
        f"{API}/files/{file_id}/url",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
        params={"expiry": hours},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["url"]


def run_ocr(key: str, url: str, pages: list[int] | None) -> dict:
    payload = {
        "model": MODEL,
        "document": {"type": "document_url", "document_url": url},
        "include_image_base64": False,
    }
    if pages:
        payload["pages"] = pages  # zero-indexed page selection
    r = requests.post(
        f"{API}/ocr",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=3600,
    )
    r.raise_for_status()
    return r.json()


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--sample", type=int, help="OCR this many pages from the Phoenician section as a quality probe")
    g.add_argument("--all", action="store_true", help="OCR the whole book")
    ap.add_argument("--start", type=int, default=95, help="first page for the sample probe, 1-indexed")
    args = ap.parse_args()

    if not PDF.exists():
        sys.exit(f"missing source pdf: {PDF}")
    OUTDIR.mkdir(parents=True, exist_ok=True)

    key = load_key()
    print("uploading source pdf, size:", f"{PDF.stat().st_size:,}", "bytes")
    fid = upload(key, PDF)
    print("uploaded, file id received")
    url = signed_url(key, fid)
    print("signed url obtained")

    pages = None
    if args.sample:
        pages = [args.start - 1 + i for i in range(args.sample)]
        print(f"probe mode: pages {args.start}..{args.start + args.sample - 1}")
    else:
        print("full-book mode")

    t0 = time.time()
    result = run_ocr(key, url, pages)
    print(f"ocr returned in {time.time() - t0:.1f}s")

    got = result.get("pages", [])
    print("pages returned:", len(got))

    tag = f"sample_{args.start}" if args.sample else "full"
    raw_path = OUTDIR / f"cooke1903_{tag}_raw.json"
    raw_path.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    md_path = OUTDIR / f"cooke1903_{tag}.md"
    with md_path.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("# Cooke 1903, Mistral OCR\n")
        fh.write("# Source: Data raw/Cooke 1903.pdf (Oxford Clarendon 1903, public domain)\n\n")
        for p in got:
            fh.write(f"\n\n<!-- PAGE {p.get('index', '?')} -->\n")
            fh.write(p.get("markdown", ""))

    print("wrote:", md_path)
    print("wrote:", raw_path)

    # quick script-recovery signal: did any Hebrew-block characters survive?
    joined = "".join(p.get("markdown", "") for p in got)
    hebrew = sum(1 for ch in joined if "֐" <= ch <= "׿")
    print("hebrew-block characters recovered:", hebrew)
    print("total characters:", len(joined))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
