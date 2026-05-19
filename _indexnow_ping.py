"""Notify Bing + Yandex (via IndexNow) that arabicjuthoor.com content changed.

IndexNow is a free, open protocol supported by Bing, Yandex, Seznam, Naver,
and Yep. One POST → all of them re-crawl immediately. Google does NOT
support IndexNow yet (use the sitemap + GSC URL-Inspection there).

Usage:
    python _indexnow_ping.py                # ping every URL in sitemap.xml
    python _indexnow_ping.py <url1> <url2>  # ping specific URLs

Key file at https://arabicjuthoor.com/046898799ae32d0b9ac53880476e18d2.txt
must contain the exact key string. The protocol requires the key to be
discoverable at the site root so the search engines can verify ownership.
"""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

HOST = "arabicjuthoor.com"
KEY = "046898799ae32d0b9ac53880476e18d2"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"
SITEMAP = Path(__file__).parent / "sitemap.xml"
ENDPOINT = "https://api.indexnow.org/IndexNow"


def urls_from_sitemap() -> list[str]:
    text = SITEMAP.read_text(encoding="utf-8")
    return re.findall(r"<loc>([^<]+)</loc>", text)


def ping(urls: list[str]) -> None:
    if not urls:
        print("no urls to ping")
        return
    payload = {
        "host": HOST,
        "key": KEY,
        "keyLocation": KEY_LOCATION,
        "urlList": urls,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            print(f"IndexNow → {resp.status} {resp.reason} ({len(urls)} URLs)")
    except urllib.error.HTTPError as exc:
        # 200/202 = ok, 422 = URLs already received recently (still ok)
        body = exc.read().decode("utf-8", errors="replace")[:300]
        print(f"IndexNow → {exc.code} {exc.reason}\n{body}")


def main() -> None:
    urls = sys.argv[1:] if len(sys.argv) > 1 else urls_from_sitemap()
    print(f"pinging IndexNow with {len(urls)} URLs…")
    ping(urls)


if __name__ == "__main__":
    main()
