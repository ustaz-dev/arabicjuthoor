#!/usr/bin/env python3
"""Return the full local lexicographic sense fan for an Arabic root.

This is a recovery aid, not a classifier. It never proposes a reading or verdict.
It searches the independent Arabic dictionaries already indexed in Resources/ so
an exploration card cannot reduce a root to the first gloss that happened to be
present in an older roster.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESOURCES = REPO_ROOT / "Resources"
ARABIC_MARKS = re.compile(
    "[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]"
)

# These are independent lexicographic works, not file names. Several works are
# duplicated between the parquet collection and the split CSV collection, so a
# scan must collapse those copies before it claims to have two sources.
CANONICAL_SOURCES = (
    ("lisan", "لسان العرب لابن منظور"),
    ("taj_al_arus", "تاج العروس لمرتضى الزبيدي"),
    ("al_sihah", "تاج اللغة وصحاح العربية للجوهري"),
    ("al_muhkam", "المحكم والمحيط الأعظم لابن سيده"),
    ("kitab_al_ayn", "كتاب العين للخليل بن أحمد"),
    ("asas_al_balagha", "أساس البلاغة للزمخشري"),
    ("al_mufradat", "المفردات في غريب القرآن للراغب"),
    ("al_misbah", "المصباح المنير"),
    ("al_muhit", "المحيط"),
    ("arabic_english", "المعجم العربي الإنجليزي"),
)
SOURCE_LABELS = dict(CANONICAL_SOURCES)
SOURCE_PRIORITY = tuple(source_id for source_id, _ in CANONICAL_SOURCES)


def normalize_root(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = ARABIC_MARKS.sub("", value)
    value = value.strip().strip("*[](){}'").replace(" ", "")
    return value


def clipped(value: str, limit: int | None) -> str:
    value = " ".join(value.split())
    if limit is None or len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "…"


def is_clipped(value: str, limit: int | None) -> bool:
    """Say whether display clipping hid part of a lexicographic witness."""
    return limit is not None and len(" ".join(value.split())) > limit


def canonical_source_id(source: str) -> str | None:
    """Map duplicate resource labels to the independent work they represent."""
    folded = unicodedata.normalize("NFKC", source).strip().casefold()
    if source == "لسان العرب لابن منظور" or folded.startswith("lesan_"):
        return "lisan"
    if source == "تاج العروس لمرتضى الزبيدي" or folded.startswith(
        "tag al-‘arus min gawahir al-qamus"
    ):
        return "taj_al_arus"
    if source == "تاج اللغة وصِحاح العربية للجوهري" or folded.startswith("alsehah"):
        return "al_sihah"
    if source == "المحكم والمحيط الأعظم لابن سيده الأندلسي":
        return "al_muhkam"
    if source == "كتاب العين للخليل بن أحمد الفراهيدي" or folded == "ein.csv":
        return "kitab_al_ayn"
    if source == "أساس البلاغة للزمخشري" or folded == "asas.csv":
        return "asas_al_balagha"
    if source == "المفردات في غريب القرآن للراغب الأصفهاني":
        return "al_mufradat"
    if folded == "almesbah.csv":
        return "al_misbah"
    if folded.startswith("almuheet_"):
        return "al_muhit"
    if source == "المعجم العربي الإنجليزي":
        return "arabic_english"
    return None


def parquet_matches(resources: Path, root: str, limit: int | None) -> list[dict[str, Any]]:
    path = resources / "arabic_roots_hf" / "train-00000-of-00001.parquet"
    if not path.exists():
        return []

    try:
        import pyarrow.dataset as ds
    except ImportError:
        return []

    table = ds.dataset(path, format="parquet").to_table(filter=ds.field("root") == root)
    matches: list[dict[str, Any]] = []
    for row in table.to_pylist():
        definition = row.get("definition") or ""
        matches.append(
            {
                "collection": "arabic_roots_hf",
                "source": row.get("book_name") or path.name,
                "root": row.get("root") or root,
                "definition": clipped(definition, limit),
                "definition_truncated": is_clipped(definition, limit),
                "url": row.get("url") or None,
            }
        )
    return matches


def csv_matches(resources: Path, root: str, limit: int | None) -> list[dict[str, Any]]:
    directory = resources / "Ten dictionaries for Arabic language"
    if not directory.exists():
        return []

    try:
        csv.field_size_limit(sys.maxsize)
    except OverflowError:
        csv.field_size_limit(2_147_483_647)

    matches: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.csv")):
        # mukhtar.csv is a word-to-root morphology index, not a definition table.
        if path.name.lower() == "mukhtar.csv":
            continue
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.reader(handle, delimiter=";")
            for row in reader:
                if not row or normalize_root(row[0]) != root:
                    continue
                definition = row[-1] if len(row) > 1 else ""
                matches.append(
                    {
                        "collection": "Ten dictionaries for Arabic language",
                        "source": path.name,
                        "root": row[0],
                        "definition": clipped(definition, limit),
                        "definition_truncated": is_clipped(definition, limit),
                        "url": None,
                    }
                )
    return matches


def matches_for_roots(
    resources: Path, roots: set[str], limit: int | None
) -> dict[str, list[dict[str, Any]]]:
    """Scan the local collections once for a set of normalized candidate roots."""
    wanted = {normalize_root(root) for root in roots if normalize_root(root)}
    result: dict[str, list[dict[str, Any]]] = {root: [] for root in wanted}
    if not wanted:
        return result

    parquet = resources / "arabic_roots_hf" / "train-00000-of-00001.parquet"
    if parquet.exists():
        try:
            import pyarrow.dataset as ds
        except ImportError:
            pass
        else:
            table = ds.dataset(parquet, format="parquet").to_table(
                filter=ds.field("root").isin(sorted(wanted))
            )
            for row in table.to_pylist():
                root = normalize_root(row.get("root") or "")
                if root not in result:
                    continue
                definition = row.get("definition") or ""
                result[root].append(
                    {
                        "collection": "arabic_roots_hf",
                        "source": row.get("book_name") or parquet.name,
                        "root": row.get("root") or root,
                        "definition": clipped(definition, limit),
                        "definition_truncated": is_clipped(definition, limit),
                        "url": row.get("url") or None,
                    }
                )

    directory = resources / "Ten dictionaries for Arabic language"
    if directory.exists():
        try:
            csv.field_size_limit(sys.maxsize)
        except OverflowError:
            csv.field_size_limit(2_147_483_647)
        for path in sorted(directory.glob("*.csv")):
            if path.name.lower() == "mukhtar.csv":
                continue
            with path.open(
                "r", encoding="utf-8-sig", errors="replace", newline=""
            ) as handle:
                for row in csv.reader(handle, delimiter=";"):
                    if not row:
                        continue
                    root = normalize_root(row[0])
                    if root not in result:
                        continue
                    definition = row[-1] if len(row) > 1 else ""
                    result[root].append(
                        {
                            "collection": "Ten dictionaries for Arabic language",
                            "source": path.name,
                            "root": row[0],
                            "definition": clipped(definition, limit),
                            "definition_truncated": is_clipped(definition, limit),
                            "url": None,
                        }
                    )

    return {root: deduplicate(matches) for root, matches in result.items()}


def deduplicate(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, Any]] = []
    for item in matches:
        key = (str(item["source"]), str(item["definition"]))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def independent_fan(
    matches: list[dict[str, Any]], minimum_sources: int = 2
) -> dict[str, Any]:
    """Select non-empty entries from independent old lexica with fallbacks."""
    grouped: dict[str, list[dict[str, Any]]] = {
        source_id: [] for source_id in SOURCE_PRIORITY
    }
    for item in matches:
        source_id = canonical_source_id(str(item.get("source") or ""))
        if source_id:
            grouped[source_id].append(item)

    coverage: list[dict[str, str]] = []
    selected: list[dict[str, Any]] = []
    for source_id in SOURCE_PRIORITY:
        items = grouped[source_id]
        nonempty = [item for item in items if str(item.get("definition") or "").strip()]
        status = "present" if nonempty else "empty" if items else "missing"
        coverage.append(
            {
                "source_id": source_id,
                "source_label": SOURCE_LABELS[source_id],
                "status": status,
            }
        )
        if nonempty and len(selected) < minimum_sources:
            # Prefer the named parquet record over a duplicated split CSV record.
            item = sorted(
                nonempty,
                key=lambda value: (
                    0 if value.get("collection") == "arabic_roots_hf" else 1,
                    -len(str(value.get("definition") or "")),
                    str(value.get("source") or ""),
                ),
            )[0]
            selected.append(
                {
                    **item,
                    "source_id": source_id,
                    "source_label": SOURCE_LABELS[source_id],
                }
            )

    source_coverage_complete = len(selected) >= minimum_sources
    truncated = any(bool(item.get("definition_truncated")) for item in matches)
    # A displayed fan is not admissible for a linguistic verdict if any
    # lexicographic witness has been shortened.  It can still be useful as a
    # navigation aid, but the caller must rerun it without a character cap.
    complete = source_coverage_complete and not truncated
    preferred = {"lisan", "taj_al_arus"}
    return {
        "minimum_sources": minimum_sources,
        "complete": complete,
        "source_coverage_complete": source_coverage_complete,
        "truncated": truncated,
        "judgment_ready": complete,
        "fallback_used": complete
        and {item["source_id"] for item in selected} != preferred,
        "selected_sources": selected,
        "coverage": coverage,
        "missing_or_empty": [
            item for item in coverage if item["status"] != "present"
        ],
    }


def root_sense_fan(
    resources: Path, root: str, limit: int | None, minimum_sources: int = 2
) -> dict[str, Any]:
    root = normalize_root(root)
    matches = deduplicate(
        parquet_matches(resources, root, limit) + csv_matches(resources, root, limit)
    )
    return {
        "root": root,
        "match_count": len(matches),
        "truncated": any(bool(item.get("definition_truncated")) for item in matches),
        "matches": matches,
        "independent_fan": independent_fan(matches, minimum_sources),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search all local Arabic lexica for every attested sense of one root."
    )
    parser.add_argument("root", help="Unvowelled Arabic root, for example: شنف")
    parser.add_argument(
        "--resources",
        type=Path,
        default=DEFAULT_RESOURCES,
        help="Resources directory (defaults to the repository Resources/ folder).",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=1200,
        help="Maximum definition length per source; use 0 for no clipping.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    parser.add_argument(
        "--minimum-sources",
        type=int,
        default=2,
        help="Minimum number of independent non-empty old lexica required.",
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()
    root = normalize_root(args.root)
    if not root:
        raise SystemExit("The normalized root is empty.")

    limit = None if args.max_chars == 0 else args.max_chars
    payload = root_sense_fan(
        args.resources, root, limit, minimum_sources=args.minimum_sources
    )
    matches = payload["matches"]

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"الجذر: {root} | الشواهد: {len(matches)}")
        fan = payload["independent_fan"]
        source_names = "، ".join(
            item["source_label"] for item in fan["selected_sources"]
        ) or "لا مصدر مكتمل"
        print(
            f"المروحة المستقلة: {'مكتملة' if fan['complete'] else 'ناقصة'}"
            f" | المصدران المستعملان: {source_names}"
        )
        if fan["truncated"]:
            print("تحذير: المروحة مقتطعة للعرض ولا تصلح لحكم؛ أعد التشغيل بـ --max-chars 0.")
        for index, item in enumerate(matches, start=1):
            print(f"\n[{index}] {item['source']} ({item['collection']})")
            print(item["definition"])
            if item.get("url"):
                print(item["url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
