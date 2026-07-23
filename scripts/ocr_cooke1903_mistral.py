#!/usr/bin/env python3
"""OCR Cooke 1903 (public domain) with the Mistral Batch API.

Why this exists
---------------
The Internet Archive full text of Cooke 1903 recovers the English apparatus (translations,
commentary, CIS numbers) but reduces the Hebrew-square Phoenician text to noise. A modern
OCR model reads that script far better. This script fills exactly that gap.

House rule: Mistral work always goes through the Batch API (author instruction, 2026-07-24).
Batch is half the price of synchronous calls and is the right shape for a 472-page book.

Source status: Cooke, G. A., *A Text-book of North-Semitic Inscriptions*, Oxford Clarendon 1903.
Public domain by age. Local copy: `Data raw/Cooke 1903.pdf`.

Credential
----------
Read from, in order: MISTRAL_API_KEY env var, `Data raw/api ocr mistral.md`, `Data raw/.mistral_key`.
The key is never printed and never leaves the local machine except as an auth header.

Usage
-----
  python scripts/ocr_cooke1903_mistral.py --submit          # build and submit the batch job
  python scripts/ocr_cooke1903_mistral.py --status          # check the running job
  python scripts/ocr_cooke1903_mistral.py --collect         # download and assemble results
  python scripts/ocr_cooke1903_mistral.py --run             # submit, wait, collect in one go
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
STATE = OUTDIR / "batch_state.json"
KEY_SOURCES = [
    ROOT / "Data raw" / "api ocr mistral.md",
    ROOT / "Data raw" / ".mistral_key",
]
API = "https://api.mistral.ai/v1"
MODEL = "mistral-ocr-latest"
PAGES_PER_REQUEST = 20  # chunk the book so one failure never costs the whole run


def load_key() -> str:
    key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if not key:
        for src in KEY_SOURCES:
            if src.exists():
                candidate = src.read_text(encoding="utf-8").strip().splitlines()
                candidate = [ln.strip() for ln in candidate if ln.strip()]
                if candidate:
                    key = candidate[-1]
                    break
    if not key or key.upper().startswith("REPL"):
        sys.exit(
            "No usable MISTRAL_API_KEY. Set the env var or place the key alone in one of:\n  "
            + "\n  ".join(str(p) for p in KEY_SOURCES)
        )
    return key


def auth(key: str) -> dict:
    return {"Authorization": f"Bearer {key}"}


def page_count(path: Path) -> int:
    try:
        import fitz

        with fitz.open(path) as doc:
            return doc.page_count
    except Exception:
        import re

        m = re.search(rb"/Count\s+(\d+)", path.read_bytes())
        return int(m.group(1)) if m else 0


def upload(key: str, path: Path, purpose: str) -> str:
    with path.open("rb") as fh:
        r = requests.post(
            f"{API}/files",
            headers=auth(key),
            files={"file": (path.name, fh)},
            data={"purpose": purpose},
            timeout=900,
        )
    r.raise_for_status()
    return r.json()["id"]


def signed_url(key: str, file_id: str, hours: int = 24) -> str:
    r = requests.get(
        f"{API}/files/{file_id}/url",
        headers={**auth(key), "Accept": "application/json"},
        params={"expiry": hours},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["url"]


def build_batch_input(url: str, total_pages: int) -> Path:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    jsonl = OUTDIR / "batch_input.jsonl"
    n = 0
    with jsonl.open("w", encoding="utf-8", newline="\n") as fh:
        for start in range(0, total_pages, PAGES_PER_REQUEST):
            pages = list(range(start, min(start + PAGES_PER_REQUEST, total_pages)))
            entry = {
                "custom_id": f"pages-{pages[0]:04d}-{pages[-1]:04d}",
                "body": {
                    "document": {"type": "document_url", "document_url": url},
                    "pages": pages,
                    "include_image_base64": False,
                },
            }
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
            n += 1
    print(f"batch input built: {n} requests covering {total_pages} pages ({PAGES_PER_REQUEST} per request)")
    return jsonl


def submit(key: str) -> dict:
    if not PDF.exists():
        sys.exit(f"missing source pdf: {PDF}")
    total = page_count(PDF)
    print(f"source: {PDF.name} | {PDF.stat().st_size:,} bytes | {total} pages")

    doc_id = upload(key, PDF, "ocr")
    print("source uploaded for ocr")
    url = signed_url(key, doc_id)
    print("signed url obtained")

    jsonl = build_batch_input(url, total)
    input_id = upload(key, jsonl, "batch")
    print("batch input uploaded")

    r = requests.post(
        f"{API}/batch/jobs",
        headers={**auth(key), "Content-Type": "application/json"},
        json={
            "input_files": [input_id],
            "model": MODEL,
            "endpoint": "/v1/ocr",
            "metadata": {"job": "cooke1903-full-book-ocr"},
        },
        timeout=180,
    )
    r.raise_for_status()
    job = r.json()
    state = {
        "job_id": job["id"],
        "document_file_id": doc_id,
        "input_file_id": input_id,
        "total_pages": total,
        "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    OUTDIR.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    print("batch job submitted, id recorded in", STATE.name)
    return state


def status(key: str, job_id: str) -> dict:
    r = requests.get(f"{API}/batch/jobs/{job_id}", headers=auth(key), timeout=120)
    r.raise_for_status()
    return r.json()


def collect(key: str, job: dict) -> None:
    out_id = job.get("output_file")
    if not out_id:
        print("no output file on the job yet; status:", job.get("status"))
        if job.get("error_file"):
            r = requests.get(f"{API}/files/{job['error_file']}/content", headers=auth(key), timeout=300)
            (OUTDIR / "batch_errors.jsonl").write_text(r.text, encoding="utf-8")
            print("errors written to batch_errors.jsonl")
        return

    r = requests.get(f"{API}/files/{out_id}/content", headers=auth(key), timeout=1800)
    r.raise_for_status()
    raw_path = OUTDIR / "batch_output.jsonl"
    raw_path.write_text(r.text, encoding="utf-8")
    print("raw batch output saved:", raw_path.name)

    pages: dict[int, str] = {}
    for line in r.text.splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        body = (rec.get("response") or {}).get("body") or rec.get("body") or {}
        for p in body.get("pages", []) or []:
            idx = p.get("index")
            if idx is None:
                continue
            pages[int(idx)] = p.get("markdown", "")

    md = OUTDIR / "cooke1903_mistral_full.md"
    with md.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write("# Cooke 1903, Mistral batch OCR\n")
        fh.write("# Source: Data raw/Cooke 1903.pdf (Oxford Clarendon 1903, public domain)\n")
        for idx in sorted(pages):
            fh.write(f"\n\n<!-- PAGE {idx + 1} -->\n{pages[idx]}")

    joined = "".join(pages.values())
    hebrew = sum(1 for ch in joined if "֐" <= ch <= "׿")
    print(f"pages assembled: {len(pages)}")
    print(f"total characters: {len(joined):,}")
    print(f"hebrew-block characters recovered: {hebrew:,}")
    print("wrote:", md)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--submit", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--run", action="store_true", help="submit, poll to completion, then collect")
    ap.add_argument("--poll-seconds", type=int, default=30)
    ap.add_argument("--max-wait", type=int, default=5400)
    args = ap.parse_args()

    key = load_key()

    if args.submit or args.run:
        state = submit(key)
    else:
        if not STATE.exists():
            sys.exit("no batch state found; run --submit first")
        state = json.loads(STATE.read_text(encoding="utf-8"))

    job_id = state["job_id"]

    if args.status:
        j = status(key, job_id)
        print(json.dumps({k: j.get(k) for k in ("id", "status", "total_requests", "completed_requests", "succeeded_requests", "failed_requests")}, indent=1))
        return 0

    if args.run:
        waited = 0
        while waited < args.max_wait:
            j = status(key, job_id)
            st = j.get("status")
            done = j.get("completed_requests", 0)
            total = j.get("total_requests", 0)
            print(f"[{waited:5d}s] status={st} {done}/{total}")
            if st in {"SUCCESS", "FAILED", "TIMEOUT_EXCEEDED", "CANCELLED"}:
                collect(key, j)
                return 0 if st == "SUCCESS" else 1
            time.sleep(args.poll_seconds)
            waited += args.poll_seconds
        print("still running after max wait; use --collect later")
        return 0

    if args.collect:
        collect(key, status(key, job_id))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
