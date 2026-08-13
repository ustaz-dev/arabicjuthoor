# -*- coding: utf-8 -*-
"""احصدْ جردَ حامد العولقي «كلمات أعجمية صارت عربية فصيحة».

تُحفَظ صفحاتُ المصدر الخام خارج Git في مجلد الموارد. يقرأ هذا الحاصد كلَّ
مدخلٍ يذكر لسانًا قديمًا صراحة، ويحفظ نصَّه كاملًا وطبقاتِ الألسن المذكورة
فيه. لا يحكم الحاصد على أي نسبة، ولا يستنتج رسمًا لم يطبعه المصدر.
"""
from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import sys

from bs4 import BeautifulSoup


ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE_DIR = (
    pathlib.Path.home()
    / "AI Projects"
    / "Resources"
    / "prior-art"
    / "hamed-alawlaqi-a3jmi"
)
OUT = ROOT / "data" / "alawlaqi-prior-attempts.json"
BASE_URL = "https://mbtda.com/language/a3jmi"

# لا يُقصَد بهذه الوسوم تقريرُ تاريخ اللسان؛ إنما هي مفاتيحُ استخراجٍ لما
# سمّاه المصدر نفسه. قد يجمع المدخل الواحد أكثر من طبقة، فنحفظها كلَّها.
LANGUAGE_MARKERS = {
    "ancient-greek": ["اليونانية القديمة", "اليوناني", "اليونانية", "الإغريقية", "الإغريقي"],
    "latin-roman": ["اللاتينية", "اللاتيني", "الرومية", "الرومي", "الرومانية"],
    "aramaic": ["الآرامية", "الارامية", "الآرامي", "الارامي"],
    "syriac": ["السريانية", "السرياني"],
    "akkadian": ["الأكادية", "الاكادية", "الأكدي", "الاكدي"],
    "sumerian": ["السومرية", "السومري"],
    "babylonian": ["البابلية", "البابلي"],
    "assyrian": ["الآشورية", "الاشورية", "الآشوري", "الاشوري"],
    "ugaritic": ["الأوغاريتية", "الاوغاريتية", "الأوغاريتي", "الاوغاريتي"],
    "phoenician": ["الفينيقية", "الفينيقي"],
    "punic": ["البونية", "البوني"],
    "hebrew": ["العبرية", "العبراني"],
    "ancient-egyptian": ["المصرية القديمة", "المصري القديم", "الهيروغليفية", "الفرعونية"],
    "coptic": ["القبطية", "القبطي"],
    "sanskrit": ["السنسكريتية", "السنسكريتي"],
}


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def clean_text(element) -> str:
    return " ".join(element.stripped_strings)


def harvest() -> dict:
    if not SOURCE_DIR.exists():
        raise SystemExit(f"مجلدُ المصدر غير موجود: {SOURCE_DIR}")

    pages = sorted(SOURCE_DIR.glob("*.html"))
    if len(pages) != 27:
        raise SystemExit(f"توقّع الحاصد 27 صفحة، فوجد {len(pages)}")

    source_files = []
    entries = []
    for path in pages:
        source_files.append(
            {
                "file": path.name,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
                "url": f"{BASE_URL}/{path.stem}.php",
            }
        )
        if path.stem in {"intro", "references"}:
            continue

        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        for paragraph in soup.select("div#nsk p"):
            text = clean_text(paragraph)
            if len(text) < 15:
                continue
            strong = paragraph.find("strong")
            if strong is None:
                continue
            head = clean_text(strong).strip()
            if not head or len(head) > 120:
                continue
            languages = [
                key
                for key, markers in LANGUAGE_MARKERS.items()
                if any(marker in text for marker in markers)
            ]
            if not languages:
                continue
            entries.append(
                {
                    "head": head,
                    "languages_mentioned": languages,
                    "page": path.stem,
                    "source_url": f"{BASE_URL}/{path.stem}.php",
                    "source_text": text,
                }
            )

    language_counts = collections.Counter(
        language
        for entry in entries
        for language in entry["languages_mentioned"]
    )
    payload = {
        "schema_version": "1.0",
        "generated_by": "scripts/harvest_alawlaqi.py",
        "title": "كلمات أعجمية صارت عربية فصيحة",
        "compiler": "حامد العولقي",
        "source_home": f"{BASE_URL}/intro.php",
        "harvest_policy": (
            "جرد منسوب خالص: كل مدخل يذكر لسانًا قديمًا صراحة محفوظ بنصه "
            "الكامل، بلا حكم على النسبة وبلا اختلاق رسم لم يطبعه المصدر."
        ),
        "source_files": source_files,
        "summary": {
            "files": len(source_files),
            "source_bytes": sum(item["bytes"] for item in source_files),
            "entries": len(entries),
            "distinct_heads": len({entry["head"] for entry in entries}),
            "language_mentions": dict(sorted(language_counts.items())),
        },
        "entries": entries,
    }
    return payload


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    payload = harvest()
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8",
    )
    summary = payload["summary"]
    print(
        f"{OUT}: {summary['entries']} مدخلًا، "
        f"{summary['distinct_heads']} رأسًا، {summary['files']} صفحة"
    )


if __name__ == "__main__":
    main()
