# -*- coding: utf-8 -*-
"""استعادة 3 ملفات من النسخة المنشورة مع حفظ الإضافات المحلية الكاملة."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
READINGS = ROOT / "04-cross-linguistic" / "readings"
NAMES = ("old-norse", "persian", "welsh")
FORENSICS = ROOT / "data" / "forensics"
AUDIT = ROOT / "05-audits" / "2026-08-05-interrupted-write-remote-restore.md"

sys.path.insert(0, str(ROOT / "scripts"))
from repair_interrupted_loanword_migration import (  # noqa: E402
    BASE_FIELDS, HEAD, VERDICT, normalize_and_dedupe, quality, split_blocks,
)

MEMBER = re.compile(r"kaikki_[a-z0-9_]+:\d+:[^\s`،؛,\]]+")
LATE_MARKERS = (
    "SECTION28-TWO-LAYER",
    "NUCLEUS-DISCIPLINE-2026-08-01",
    "2026-08-02",
    "2026-08-03",
    "2026-08-04",
    "2026-08-05",
)


def card_key(block: str) -> str:
    heading = block.splitlines()[0]
    if match := MEMBER.search(heading):
        return "member:" + match.group(0).rstrip(".؛،)")
    for line in block.splitlines():
        if line.startswith("- الكلمةُ في الفرع:") and (match := MEMBER.search(line)):
            return "member:" + match.group(0).rstrip(".؛،)")
    return "heading:" + heading


def complete_card(block: str) -> bool:
    if not block.startswith("### بطاقة"):
        return False
    return (
        sum(field in block for field in BASE_FIELDS) == len(BASE_FIELDS)
        and bool(VERDICT.search(block))
        and "RECOVERY-v2" in block
    )


def fetch(name: str) -> tuple[str, dict]:
    url = f"https://arabicjuthoor.com/04-cross-linguistic/readings/{name}.md"
    request = urllib.request.Request(url, headers={"User-Agent": "Juthoor-repair/2026-08-05"})
    with urllib.request.urlopen(request, timeout=90) as response:
        raw = response.read()
        metadata = {
            "url": url,
            "last_modified": response.headers.get("Last-Modified", ""),
            "etag": response.headers.get("ETag", ""),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        }
    return raw.decode("utf-8"), metadata


def merge(remote: str, current: str, name: str) -> tuple[str, dict]:
    normalized, archived, corruption_stats = normalize_and_dedupe(current, name + ".md")
    _, remote_blocks = split_blocks(remote)
    _, local_blocks = split_blocks(normalized)
    remote_keys = {card_key(block): block for block in remote_blocks if block.startswith("### بطاقة")}
    local_keys: dict[str, str] = {}
    for block in local_blocks:
        if not complete_card(block):
            continue
        key = card_key(block)
        previous = local_keys.get(key)
        if previous is None or quality(block) > quality(previous):
            local_keys[key] = block

    replacements: dict[str, str] = {}
    extras: list[str] = []
    for key, local in local_keys.items():
        published = remote_keys.get(key)
        if published is None:
            extras.append(local)
            continue
        locally_later = any(marker in local and marker not in published for marker in LATE_MARKERS)
        if locally_later and quality(local) >= quality(published):
            replacements[key] = local

    preamble, blocks = split_blocks(remote)
    out = [preamble]
    for block in blocks:
        if block.startswith("### بطاقة"):
            block = replacements.get(card_key(block), block)
        out.append(block)
    if extras:
        out.extend([
            "\n## بطاقات محلية كاملة حُفظت عند استعادة انقطاع الكتابة\n\n",
            "هذه البطاقات أحدث من النسخة المنشورة، وحُفظت لأنها اجتازت عقد الحقول كاملا.\n\n",
            *extras,
        ])
    merged = "".join(out)
    stats = {
        "remote_cards": sum(block.startswith("### بطاقة") for block in remote_blocks),
        "complete_local_cards": len(local_keys),
        "local_replacements": len(replacements),
        "local_extras": len(extras),
        "corrupt_fragments_observed": len(archived),
        **corruption_stats,
    }
    return merged, stats


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    rows: list[dict] = []
    outputs: dict[str, str] = {}
    originals: dict[str, bytes] = {}
    for name in NAMES:
        path = READINGS / f"{name}.md"
        original = path.read_bytes()
        current = original.decode("utf-8")
        remote, source = fetch(name)
        merged, stats = merge(remote, current, name)
        issues = []
        _, blocks = split_blocks(merged)
        for block in blocks:
            if block.startswith("### بطاقة") and not VERDICT.search(block):
                issues.append(block.splitlines()[0])
        row = {
            "language": name,
            "source": source,
            "original_sha256": hashlib.sha256(original).hexdigest(),
            "merged_sha256": hashlib.sha256(merged.encode("utf-8")).hexdigest(),
            "stats": stats,
            "cards_without_verdict": len(issues),
        }
        rows.append(row)
        outputs[name] = merged
        originals[name] = original
        print(json.dumps(row, ensure_ascii=False))
    if not args.apply:
        return 0

    FORENSICS.mkdir(parents=True, exist_ok=True)
    for name in NAMES:
        archive = FORENSICS / f"2026-08-05-{name}.interrupted.md.gz"
        with gzip.open(archive, "wb", compresslevel=9) as handle:
            handle.write(originals[name])
        (READINGS / f"{name}.md").write_text(outputs[name], encoding="utf-8", newline="\n")
    lines = [
        "# محضر استعادة ملفات القراءة بعد انقطاع الكتابة، 2026-08-05", "",
        "استعيدت الملفات الثلاثة من النسخة المنشورة المباشرة، ثم أدمجت البطاقات "
        "المحلية الأحدث التي بقيت كاملة واجتازت عقد الحقول. حُفظت النسخ المتداخلة "
        "كاملة مضغوطة في `data/forensics/` قبل الاستبدال.", "",
        "| اللسان | بطاقات المنشور | استبدالات محلية | إضافات محلية | بلا حكم بعد الدمج | SHA-256 المنشور |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        stats = row["stats"]
        lines.append(
            f"| `{row['language']}` | {stats['remote_cards']} | {stats['local_replacements']} | "
            f"{stats['local_extras']} | {row['cards_without_verdict']} | `{row['source']['sha256']}` |"
        )
    lines.append("")
    AUDIT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
