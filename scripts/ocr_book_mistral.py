# -*- coding: utf-8 -*-
"""مسحٌ ضوئيٌّ بالدفعاتِ لأيِّ كتابٍ في الذخيرة (2026-08-11، بإذنِ المؤلّف)

**الحاجة:** كتابانِ من ذخيرةِ خشيم فيهما نقصٌ مسمًّى:

  1. «البرهانُ على عروبةِ اللغةِ المصريّةِ القديمة»، 914 صفحةً **صورًا بلا نصٍّ
     البتّة** (صفرُ حرفٍ مستخرَج).
  2. «اللاتينيّةُ عربيّة»، مُسِحَ بالعربيّةِ وحدَها **فسقطَ كلُّ حرفٍ لاتينيٍّ**
     من مداخلِه (صفرُ حرفٍ لاتينيٍّ في 234 صفحة)، وبقيَ الجذرُ العربيُّ ونصُّه
     بلا الكلمةِ التي يُقابِلُها.

وهذا المسحُ يسدُّ النقصَينِ لأنّه يقرأُ الخطَّينِ معًا في الصفحةِ الواحدة.

**وهو تعميمٌ لأداةِ `ocr_cooke1903_mistral.py`** التي جُرِّبَت على كوك 1903
ونجحَت، ولا يختلفُ عنها إلّا بأنّه يقبلُ أيَّ ملفٍّ ومخرَجٍ بدلَ أن يكونَ
مسمَّرًا على كتابٍ واحد.

**والمفتاحُ لا يُكتَبُ في أمرٍ ولا في مخرَجٍ ولا يُودَعُ في git.** يُقرَأُ من
متغيّرِ البيئةِ `MISTRAL_API_KEY` أو من `Data raw/api ocr mistral.md` وهو خارجَ
المستودع. والناتجُ يُكتَبُ في `Resources/` خارجَ git كذلك، فالذخيرةُ الخامُّ لا
تُودَع.

الاستعمال:
    python scripts/ocr_book_mistral.py --pdf <ملفّ> --out <مجلَّد> --submit
    python scripts/ocr_book_mistral.py --out <مجلَّد> --status
    python scripts/ocr_book_mistral.py --out <مجلَّد> --collect
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time

import requests

ROOT = pathlib.Path(__file__).resolve().parent.parent
KEY_FILES = [
    ROOT / "Data raw" / "api ocr mistral.md",
    ROOT / "Data raw" / ".mistral_key",
]
API = "https://api.mistral.ai/v1"
MODEL = "mistral-ocr-latest"
PAGES_PER_REQUEST = 40


def load_key() -> str:
    key = os.environ.get("MISTRAL_API_KEY", "").strip()
    if key:
        return key
    for p in KEY_FILES:
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip().strip("`")
                if len(line) > 20 and " " not in line and not line.startswith("#"):
                    return line
    sys.exit("لا مفتاحَ. ضعْه في MISTRAL_API_KEY أو في Data raw/api ocr mistral.md")


def auth(key: str) -> dict:
    return {"Authorization": f"Bearer {key}"}


def page_count(path: pathlib.Path) -> int:
    import fitz                                              # noqa: PLC0415
    return fitz.open(path).page_count


def upload(key: str, path: pathlib.Path, purpose: str) -> str:
    with path.open("rb") as fh:
        r = requests.post(f"{API}/files", headers=auth(key),
                          files={"file": (path.name, fh)},
                          data={"purpose": purpose}, timeout=1800)
    r.raise_for_status()
    return r.json()["id"]


def signed_url(key: str, file_id: str, hours: int = 24) -> str:
    r = requests.get(f"{API}/files/{file_id}/url",
                     headers={**auth(key), "Accept": "application/json"},
                     params={"expiry": hours}, timeout=120)
    r.raise_for_status()
    return r.json()["url"]


def submit(key: str, pdf: pathlib.Path, outdir: pathlib.Path) -> dict:
    total = page_count(pdf)
    print(f"المصدر: {pdf.name} · {pdf.stat().st_size:,} بايت · {total} صفحة")
    doc_id = upload(key, pdf, "ocr")
    url = signed_url(key, doc_id)
    outdir.mkdir(parents=True, exist_ok=True)

    jsonl = outdir / "batch_input.jsonl"
    n = 0
    with jsonl.open("w", encoding="utf-8", newline="\n") as fh:
        for start in range(0, total, PAGES_PER_REQUEST):
            pages = list(range(start, min(start + PAGES_PER_REQUEST, total)))
            fh.write(json.dumps({
                "custom_id": f"pages-{pages[0]:04d}-{pages[-1]:04d}",
                "body": {"document": {"type": "document_url", "document_url": url},
                         "pages": pages, "include_image_base64": False},
            }, ensure_ascii=False) + "\n")
            n += 1
    print(f"طلباتُ الدفعة: {n} تغطّي {total} صفحة")

    input_id = upload(key, jsonl, "batch")
    r = requests.post(f"{API}/batch/jobs",
                      headers={**auth(key), "Content-Type": "application/json"},
                      json={"input_files": [input_id], "model": MODEL,
                            "endpoint": "/v1/ocr",
                            "metadata": {"job": f"juthoor-{outdir.name}"}},
                      timeout=180)
    r.raise_for_status()
    job = r.json()
    state = {"job_id": job["id"], "pdf": str(pdf), "total_pages": total,
             "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    (outdir / "state.json").write_text(json.dumps(state, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    print(f"أُرسِلَت الدفعة: {job['id']}")
    return state


def status(key: str, job_id: str) -> dict:
    r = requests.get(f"{API}/batch/jobs/{job_id}", headers=auth(key), timeout=120)
    r.raise_for_status()
    return r.json()


def collect(key: str, job: dict, outdir: pathlib.Path) -> int:
    out_id = job.get("output_file")
    if not out_id:
        print("لا مخرَجَ بعد. الحال:", job.get("status"))
        if job.get("error_file"):
            r = requests.get(f"{API}/files/{job['error_file']}/content",
                             headers=auth(key), timeout=300)
            (outdir / "batch_errors.jsonl").write_text(r.text, encoding="utf-8")
            print("كُتبت الأخطاءُ في batch_errors.jsonl")
        return 1

    r = requests.get(f"{API}/files/{out_id}/content", headers=auth(key), timeout=3600)
    r.raise_for_status()
    (outdir / "batch_output.jsonl").write_text(r.text, encoding="utf-8")

    pages: dict[int, str] = {}
    for line in r.text.splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        body = (rec.get("response") or {}).get("body") or rec.get("body") or {}
        for p in body.get("pages", []) or []:
            if p.get("index") is not None:
                pages[int(p["index"])] = p.get("markdown", "")

    md = outdir / "full.md"
    with md.open("w", encoding="utf-8", newline="\n") as fh:
        fh.write(f"# مسحٌ ضوئيٌّ بالدفعات: {outdir.name}\n")
        for idx in sorted(pages):
            fh.write(f"\n\n<!-- صفحة {idx + 1} -->\n{pages[idx]}")

    joined = "".join(pages.values())
    arabic = sum(1 for c in joined if "؀" <= c <= "ۿ")
    latin = sum(1 for c in joined if c.isascii() and c.isalpha())
    print(f"صفحاتٌ مجموعة: {len(pages)}   حروف: {len(joined):,}")
    print(f"عربيّةٌ مستردَّة: {arabic:,}   لاتينيّةٌ مستردَّة: {latin:,}")
    print("كُتب:", md)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf")
    ap.add_argument("--out", required=True)
    ap.add_argument("--submit", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--collect", action="store_true")
    ap.add_argument("--run", action="store_true", help="أرسِلْ وانتظرْ واجمعْ")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    key = load_key()
    outdir = pathlib.Path(args.out).expanduser()
    state_path = outdir / "state.json"

    if args.submit or args.run:
        if not args.pdf:
            sys.exit("--submit يحتاجُ --pdf")
        pdf = pathlib.Path(args.pdf).expanduser()
        if not pdf.exists():
            sys.exit(f"لا ملفَّ: {pdf}")
        state = submit(key, pdf, outdir)
        if not args.run:
            return 0
        # الانتظارُ بحدٍّ أعلى، فالدفعةُ الكبيرةُ قد تطولُ والحسابُ لا يُترَكُ معلَّقًا
        for _ in range(360):
            time.sleep(30)
            job = status(key, state["job_id"])
            st = job.get("status", "?")
            done = job.get("succeeded_requests", 0)
            tot = job.get("total_requests", 0)
            print(f"   {st}  {done}/{tot}", flush=True)
            if st in {"SUCCESS", "FAILED", "CANCELLED", "TIMEOUT_EXCEEDED"}:
                return collect(key, job, outdir)
        print("طالَ الانتظار. أعِدْ بـ--collect لاحقًا.")
        return 1

    if not state_path.exists():
        sys.exit(f"لا حالةَ محفوظةٌ في {state_path}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    job = status(key, state["job_id"])
    if args.status:
        print(json.dumps({k: job.get(k) for k in
                          ("id", "status", "total_requests", "completed_requests",
                           "succeeded_requests", "failed_requests")},
                         ensure_ascii=False, indent=1))
        return 0
    if args.collect:
        return collect(key, job, outdir)
    print("اختَرْ --submit أو --status أو --collect أو --run")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
