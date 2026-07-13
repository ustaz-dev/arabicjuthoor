#!/usr/bin/env python3
"""Fail CI when public counts, reading cards, or the shift network drift.

This complements check_charge_purity.py. It deliberately distinguishes the
historical 453-entry Jabal table from the current operational registry count.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")

fails: list[str] = []


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


export = json.loads(read("data/juthoor-core-levels.json"))
level2 = export["levels"]["level_2_binary_nuclei"]
declared_count = level2["count"]
actual_count = len(level2["nuclei"])
if declared_count != actual_count:
    fails.append(
        f"core count: declared {declared_count}, actual {actual_count}"
    )

source_commit = export.get("exported_at_commit", "").strip()
if not source_commit:
    fails.append("core provenance: exported_at_commit is empty")
else:
    resolved = subprocess.run(
        ["git", "cat-file", "-e", f"{source_commit}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if resolved.returncode:
        fails.append(
            f"core provenance: exported_at_commit {source_commit!r} is not a commit"
        )


public_requirements = {
    "index.html": [
        f'<div class="stat-num">{declared_count}</div>',
        f"{declared_count} operational binary nuclei",
        f"{declared_count} نواةً ثنائيّةً تشغيليّة",
        '<div class="stat-num">1 / 2,285</div>',
        "Loanword label",
        "وسم دخيل",
    ],
    "README.md": [f"operational {declared_count}-nucleus catalog"],
    "manifest.webmanifest": [f"{declared_count} operational binary nuclei"],
    "og-image.svg": [
        f">{declared_count}</text>",
        "OPERATIONAL NUCLEI",
        "LOANWORD / 2,285",
    ],
    "_build_og_image.py": [
        f'("{declared_count}", "OPERATIONAL NUCLEI")',
        f'("{declared_count}", ar("نواةً تشغيليّة"))',
        '("1", "LOANWORD / 2,285")',
        '("1", ar("دخيل من 2,285"))',
    ],
}
for path, needles in public_requirements.items():
    body = read(path)
    for needle in needles:
        if needle not in body:
            fails.append(f"public count: {path} lacks {needle!r}")

if "NATIVE FIT" in read("og-image.svg") or "NATIVE FIT" in read("_build_og_image.py"):
    fails.append("public framing: OG assets still advertise NATIVE FIT")


required_card_fields = (
    "- الكلمةُ في الفرع:",
    "- أقدمُ صورةٍ مستعادة:",
    "- الخطوةُ صفر (التعرية بصرف الفرع):",
    "- درجةُ المقارنة:",
    "- المقابلُ من اللسان:",
    "- مسارُ الصوت:",
    "- المعنى من قاموس الفرع:",
    "- المدار:",
    "- المصفاة:",
    "- مؤشر اليتم:",
    "- الحكم (استكشاف):",
    "- ملاحظات:",
)


def reading_cards(path: str) -> list[tuple[str, str]]:
    body = read(path)
    starts = list(re.finditer(r"^### بطاقة.*$", body, re.MULTILINE))
    cards: list[tuple[str, str]] = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(body)
        cards.append((match.group(0), body[match.start():end]))
    return cards


reading_paths = (
    "04-cross-linguistic/readings/egyptian.md",
    "04-cross-linguistic/readings/coptic.md",
)
all_cards: dict[str, list[tuple[str, str]]] = {}
for path in reading_paths:
    body = read(path)
    if "../exploration-charter.md" not in body:
        fails.append(f"protocol canon: {path} lacks the charter reference")
    if "0. **تهيئةُ الملفّ:**" in body:
        fails.append(f"protocol canon: {path} embeds a stale numbered copy")

    cards = reading_cards(path)
    all_cards[path] = cards
    for heading, section in cards:
        if not heading.startswith("### بطاقة:"):
            fails.append(f"card heading: {path}: {heading}")
        for field in required_card_fields:
            if field not in section:
                fails.append(f"card field: {path}: {heading} lacks {field}")


egypt_cards = all_cards["04-cross-linguistic/readings/egyptian.md"]
for lemma, expected in (("ḫf", "**NO-TRACE**"), ("km", "**NUCLEUS-ECHO**")):
    matches = [section for heading, section in egypt_cards if heading.startswith(f"### بطاقة: {lemma} ")]
    if not matches or expected not in matches[-1]:
        fails.append(f"latest Egyptian ruling: {lemma} must end at {expected}")

egyptian = read("04-cross-linguistic/readings/egyptian.md")
if "TLA Lemma ID 163900" in egyptian:
    fails.append("Egyptian source: stale km lemma ID 163900 remains")
if "TLA Lemma ID 401218" not in egyptian:
    fails.append("Egyptian source: corrected km lemma ID 401218 is missing")


network = read("04-cross-linguistic/shift-network-draft.md")
network_ids = re.findall(r"^\| ([A-Z]+-[A-Z0-9-]+) \|", network, re.MULTILINE)
if len(network_ids) != 42:
    fails.append(f"shift network: expected 42 table rows, found {len(network_ids)}")
if len(network_ids) != len(set(network_ids)):
    duplicates = sorted({item for item in network_ids if network_ids.count(item) > 1})
    fails.append(f"shift network: duplicate row IDs {duplicates}")
if network_ids.count("BR-EGYP-02") != 1:
    fails.append("shift network: BR-EGYP-02 must occur exactly once in the table")
if "الشبكةُ التشغيليّةُ الآن 42 قيدًا" not in network:
    fails.append("shift network: operative 42-entry status is missing")
if "ما عندنا للمصريّة قيدٌ كتابيٌّ واحد" in network:
    fails.append("shift network: stale one-Egyptian-row gap claim remains")


print(
    f"checked {actual_count} nuclei, "
    f"{sum(len(cards) for cards in all_cards.values())} reading-card blocks, "
    f"{len(network_ids)} shift rows"
)
for failure in fails:
    print("FAIL:", failure)
print("RESULT:", "CLEAN" if not fails else f"{len(fails)} failure(s)")
sys.exit(1 if fails else 0)
