"""Build feed.xml (Atom 1.0) from /05-audits/*.md.

Each audit file becomes one <entry>. Title comes from the first H1; date
from the file name (YYYY-MM-DD prefix) or mtime as fallback.

Run: python _build_feed.py
"""

from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).parent
AUDITS = ROOT / "05-audits"
SITE = "https://arabicjuthoor.com"
FEED_URL = f"{SITE}/feed.xml"
FEED_TITLE = "Juthoor · Audits & Research Notes"
FEED_SUB = "Lab notebook for The Arabic Tongue: data audits, anomaly investigations, structural deltas."
AUTHOR_NAME = "Yassine Temessek"

DATE_RX = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def entry_for(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    h1 = re.search(r"^# +(.+)$", text, re.M)
    title = h1.group(1).strip() if h1 else path.stem.replace("-", " ")
    title = re.sub(r"[`*_]", "", title)

    # First paragraph for summary
    body = re.sub(r"^#.*$", "", text, flags=re.M)
    body = re.sub(r"^>.*$", "", body, flags=re.M)
    body = re.sub(r"^---$", "", body, flags=re.M)
    paras = [p.strip() for p in re.split(r"\n\n+", body) if p.strip()]
    summary = (paras[0] if paras else "").replace("\n", " ").strip()[:400]

    # Date: prefer YYYY-MM-DD prefix in filename, else file mtime
    m = DATE_RX.match(path.name)
    if m:
        d = datetime.strptime(m.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
    else:
        d = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)

    rel = path.relative_to(ROOT).as_posix()
    url = f"{SITE}/{rel}"
    return {"title": title, "summary": summary, "date": d, "url": url, "id": url}


def main() -> None:
    files = sorted(
        [p for p in AUDITS.glob("*.md") if p.name != "README.md" and not p.name.startswith("_")],
        key=lambda p: p.name,
        reverse=True,
    )
    entries = [entry_for(p) for p in files]
    updated = max((e["date"] for e in entries), default=datetime.now(timezone.utc))

    out = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en">',
        f"  <title>{escape(FEED_TITLE)}</title>",
        f"  <subtitle>{escape(FEED_SUB)}</subtitle>",
        f'  <link href="{SITE}/" />',
        f'  <link rel="self" type="application/atom+xml" href="{FEED_URL}" />',
        f"  <id>{FEED_URL}</id>",
        f"  <updated>{iso(updated)}</updated>",
        f"  <author><name>{escape(AUTHOR_NAME)}</name></author>",
        f"  <rights>© Temessek for Research, Publishing &amp; Training</rights>",
        "",
    ]
    for e in entries:
        out += [
            "  <entry>",
            f"    <title>{escape(e['title'])}</title>",
            f'    <link href="{e["url"]}" />',
            f"    <id>{e['id']}</id>",
            f"    <updated>{iso(e['date'])}</updated>",
            f"    <published>{iso(e['date'])}</published>",
            f"    <summary>{escape(e['summary'])}</summary>",
            "  </entry>",
        ]
    out.append("</feed>")
    (ROOT / "feed.xml").write_text("\n".join(out), encoding="utf-8")
    print(f"feed.xml -> {len(entries)} entries, latest {iso(updated)}")


if __name__ == "__main__":
    main()
