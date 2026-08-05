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

afro_browser = read("afro-asiatic.html")
if '[163, "شَنَف / شَنَّف", "šnf", "be angry, frown, dislike"' in afro_browser:
    fails.append("Afro-Asiatic browser: entry 163 still publishes the retracted šnf angry/frown claim")
if '[163, "شَنَف", "šnf.t", "Egyptian: fish scale; Arabic: upper lip turned upward"' not in afro_browser:
    fails.append("Afro-Asiatic browser: entry 163 lacks the corrected šnf.t recovery row")


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

recovery_marker = "<!-- RECOVERY-PROTOCOL-v2 -->"
recovery_card_fields = (
    "- إصدارُ البروتوكول:",
    "- مسحُ المعاني العربيّة:",
    "- فصلُ المتجانسات والاقتراض:",
    "- جسورُ الاسترداد المفحوصة:",
    "- حالةُ الإغلاق:",
)

radiation_marker = "<!-- RADIATION-FIELDS-v1 -->"
radiation_card_fields = (
    "- إشعاع الأسرة في الفرع:",
    "- إشعاع الأسرة في العربية:",
)
positive_verdicts = (
    "ROOT-TRACE",
    "NUCLEUS-TRACE",
    "NUCLEUS-ECHO",
    "FLOOR-TRACE",
)
verdict_field = re.compile(
    r"^-\s*(?:"
    r"الحكم"
    r"|الحسم"
    r"|حكم طبقة النواة"
    r"|حكم طبقة الجذر"
    r"|نتيجة طبقة النواة"
    r"|النتيجة"
    r")(?:\s*\([^)]*\))?\s*[:：]",
    re.MULTILINE,
)


def reading_cards_from_body(body: str) -> list[tuple[str, str]]:
    # End a card at the next peer or subordinate reading heading.  Stopping
    # only at the next spelling of ``بطاقة`` made a renamed compact record
    # swallow later supersession and protocol sections, then charged their
    # fields to the wrong card.
    starts = list(re.finditer(r"^#{3,4}\s+.*$", body, re.MULTILINE))
    cards: list[tuple[str, str]] = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(body)
        heading = match.group(0)
        if heading.startswith("### بطاقة"):
            cards.append((heading, body[match.start():end]))
    return cards


def reading_cards(path: str) -> list[tuple[str, str]]:
    return reading_cards_from_body(read(path))


reading_paths = tuple(
    path.relative_to(ROOT).as_posix()
    for path in sorted((ROOT / "04-cross-linguistic/readings").glob("*.md"))
    if path.name != "README.md"
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
        # Several historical card-heading forms are legal.  Link identity and
        # counting belong to scripts/count_links.py; this gate checks fields.
        exact_fields = sum(field in section for field in required_card_fields)
        # A renamed compact queue/supersession record is not a newly issued
        # full RECOVERY card.  Once a block substantially adopts the canonical
        # contract, the complete base contract remains mandatory.
        if exact_fields >= 7:
            for field in required_card_fields:
                if field not in section:
                    fails.append(f"card field: {path}: {heading} lacks {field}")
        elif not verdict_field.search(section):
            fails.append(
                f"compact card verdict: {path}: {heading} lacks a verdict field"
            )

    if recovery_marker not in body:
        fails.append(f"recovery protocol: {path} lacks {recovery_marker}")
        continue

    before_marker, _ = body.split(recovery_marker, 1)
    for field in recovery_card_fields:
        if field not in before_marker:
            fails.append(f"recovery template: {path} lacks {field}")

    for heading, section in cards:
        exact_fields = sum(field in section for field in required_card_fields)
        declares_recovery = "- إصدارُ البروتوكول:" in section
        if exact_fields >= 7 and declares_recovery:
            for field in required_card_fields + recovery_card_fields:
                if field not in section:
                    fails.append(f"recovery card field: {path}: {heading} lacks {field}")

        version = re.search(r"^- إصدارُ البروتوكول:\s*(.+)$", section, re.MULTILINE)
        state = re.search(r"^- حالةُ الإغلاق:\s*(.+)$", section, re.MULTILINE)
        verdict = re.search(r"^- الحكم \(استكشاف\):\s*(.+)$", section, re.MULTILINE)
        if version and not version.group(1).startswith("RECOVERY-v2"):
            fails.append(f"recovery version: {path}: {heading} is not RECOVERY-v2")
        if not state or not verdict:
            continue

        state_value = state.group(1)
        verdict_value = verdict.group(1).lstrip("*")
        closes_no_trace = verdict_value.startswith("NO-TRACE")
        if closes_no_trace and "CLOSED-NO-TRACE" not in state_value:
            fails.append(
                f"recovery closure: {path}: {heading} issues NO-TRACE without CLOSED-NO-TRACE"
            )
        if closes_no_trace and any(
            gap in state_value for gap in ("TOOL-GAP", "LAW-GAP", "SOURCE-GAP", "OPEN-CANDIDATE")
        ):
            fails.append(
                f"recovery gap: {path}: {heading} turns an unresolved gap into NO-TRACE"
            )

    if radiation_marker in body:
        for heading, section in cards:
            if not any(field in section for field in radiation_card_fields):
                continue
            verdict = re.search(
                r"^- الحكم \(استكشاف\):\s*(.+)$", section, re.MULTILINE
            )
            if not verdict or not any(
                item in verdict.group(1) for item in positive_verdicts
            ):
                continue
            for field in radiation_card_fields:
                if field not in section:
                    fails.append(
                        f"radiation field: {path}: {heading} lacks {field}"
                    )


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
if len(network_ids) != 71:
    fails.append(f"shift network: expected 71 table rows, found {len(network_ids)}")
if len(network_ids) != len(set(network_ids)):
    duplicates = sorted({item for item in network_ids if network_ids.count(item) > 1})
    fails.append(f"shift network: duplicate row IDs {duplicates}")
if network_ids.count("BR-EGYP-02") != 1:
    fails.append("shift network: BR-EGYP-02 must occur exactly once in the table")
if "الشبكةُ التشغيليّةُ الآن 71 قيدًا" not in network:
    fails.append("shift network: operative 71-entry status is missing")
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
