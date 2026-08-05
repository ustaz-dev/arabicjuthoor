# -*- coding: utf-8 -*-
"""يرمم تداخل الكتابة الذي خلفته عملية إعادة فرز قديمة لم تتوقف."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TARGETS = tuple(
    ROOT / "04-cross-linguistic" / "readings" / name
    for name in ("old-norse.md", "persian.md", "welsh.md")
)
ARCHIVE = ROOT / "data" / "interrupted-loanword-duplicate-fragments.jsonl"
REPORT = ROOT / "05-audits" / "2026-08-05-interrupted-loanword-write-repair.md"

BASE_FIELDS = (
    "- الكلمةُ في الفرع:", "- أقدمُ صورةٍ مستعادة:",
    "- الخطوةُ صفر (التعرية بصرف الفرع):", "- درجةُ المقارنة:",
    "- المقابلُ من اللسان:", "- مسارُ الصوت:",
    "- المعنى من قاموس الفرع:", "- المدار:", "- المصفاة:",
    "- مؤشر اليتم:", "- الحكم (استكشاف):", "- ملاحظات:",
)
RECOVERY_FIELDS = (
    "- إصدارُ البروتوكول:", "- مسحُ المعاني العربيّة:",
    "- فصلُ المتجانسات والاقتراض:", "- جسورُ الاسترداد المفحوصة:",
    "- حالةُ الإغلاق:",
)
VERDICT = re.compile(
    r"^-(?:\s*)(?:الحكم|الحسم|حكمُ? طبقة النواة|حكمُ? طبقة الجذر|"
    r"نتيجةُ? طبقة النواة|النتيجة)(?:\s*\([^)]*\))?\s*[:：]",
    re.M,
)
HEAD = re.compile(r"(?m)^#{3,4}\s+[^\n]*$")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_blocks(text: str) -> tuple[str, list[str]]:
    matches = list(HEAD.finditer(text))
    if not matches:
        return text, []
    return text[:matches[0].start()], [
        text[match.start():matches[index + 1].start() if index + 1 < len(matches) else len(text)]
        for index, match in enumerate(matches)
    ]


def quality(block: str) -> tuple[int, int, int, int]:
    base = sum(field in block for field in BASE_FIELDS)
    recovery = sum(field in block for field in RECOVERY_FIELDS)
    valid_verdict = int(bool(VERDICT.search(block)))
    clean_protocol = int("RECOVERY-v2" in block)
    return base + recovery, valid_verdict, clean_protocol, len(block)


def normalize_and_dedupe(text: str, file_name: str) -> tuple[str, list[dict], dict]:
    embedded = len(re.findall(r"(?<!\n)###\s+", text))
    normalized = re.sub(r"(?<!\n)(###\s+)", r"\n\1", text)
    preamble, blocks = split_blocks(normalized)
    by_heading: dict[str, list[tuple[int, str]]] = collections.defaultdict(list)
    for index, block in enumerate(blocks):
        by_heading[block.splitlines()[0]].append((index, block))

    selected: dict[str, tuple[int, str]] = {}
    archive: list[dict] = []
    for heading, candidates in by_heading.items():
        chosen = max(candidates, key=lambda item: quality(item[1]))
        selected[heading] = chosen
        if len(candidates) == 1:
            continue
        for index, block in candidates:
            if index == chosen[0]:
                continue
            archive.append({
                "file": file_name,
                "heading": heading,
                "chosen_sha256": sha(chosen[1]),
                "removed_sha256": sha(block),
                "chosen_quality": quality(chosen[1]),
                "removed_quality": quality(block),
                "content": block,
            })

    emitted: set[str] = set()
    out = [preamble]
    for block in blocks:
        heading = block.splitlines()[0]
        if heading in emitted:
            continue
        emitted.add(heading)
        out.append(selected[heading][1])
    repaired = "".join(out)
    stats = {
        "embedded_headings": embedded,
        "blocks_before": len(blocks),
        "blocks_after": len(emitted),
        "duplicates_archived": len(archive),
    }
    return repaired, archive, stats


def card_issues(text: str) -> list[str]:
    _, blocks = split_blocks(text)
    issues: list[str] = []
    for block in blocks:
        heading = block.splitlines()[0]
        if not heading.startswith("### بطاقة"):
            continue
        base_count = sum(field in block for field in BASE_FIELDS)
        if base_count >= 7:
            missing = [field for field in BASE_FIELDS if field not in block]
            if "- إصدارُ البروتوكول:" in block:
                missing += [field for field in RECOVERY_FIELDS if field not in block]
            if missing:
                issues.append(f"{heading}: مفقود {', '.join(missing)}")
        elif not VERDICT.search(block):
            issues.append(f"{heading}: لا حقل حكم")
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    all_archive: list[dict] = []
    results: list[tuple[Path, str, dict, list[str]]] = []
    for path in TARGETS:
        repaired, archive, stats = normalize_and_dedupe(
            path.read_text(encoding="utf-8"), path.relative_to(ROOT).as_posix()
        )
        issues = card_issues(repaired)
        results.append((path, repaired, stats, issues))
        all_archive.extend(archive)
        print(f"{path.name}: {stats}; issues_after={len(issues)}")
        for issue in issues[:12]:
            print(f"  {issue}")
    if not args.apply:
        return 0

    for path, repaired, _, _ in results:
        path.write_text(repaired, encoding="utf-8", newline="\n")
    with ARCHIVE.open("w", encoding="utf-8", newline="\n") as handle:
        for row in all_archive:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    lines = [
        "# محضر ترميم انقطاع كتابة فرز القروض، 2026-08-05", "",
        "أوقفت عملية قديمة من الغلاف، لكن عمليتها الابنة بقيت حتى كتبت إزاحات قديمة "
        "فوق 3 ملفات تغير طولها. فُصل كل عنوان دخل في منتصف سطر، واختيرت النسخة "
        "الأكمل من كل عنوان مكرر بحسب عقد حقول النشر.", "",
        "لم تسقط الشظايا الزائدة. حفظ نص كل شظية مع بصمتها وبصمة النسخة المختارة "
        "في `data/interrupted-loanword-duplicate-fragments.jsonl`.", "",
        "| الملف | عناوين مدمجة | الكتل قبل | الكتل بعد | الشظايا المؤرشفة | عيوب العقد الباقية |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for path, _, stats, issues in results:
        lines.append(
            f"| `{path.name}` | {stats['embedded_headings']} | {stats['blocks_before']} | "
            f"{stats['blocks_after']} | {stats['duplicates_archived']} | {len(issues)} |"
        )
    lines.append("")
    REPORT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
