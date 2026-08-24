#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 24; emit patches only, never commit or ship."""

from __future__ import annotations

from collections import Counter
import argparse
import json
from pathlib import Path
import re
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import harvest_ancient_greek_round23 as R23  # noqa: E402


R21 = R23.R21
R2 = R23.R2
SWEEP, READING, PROPOSAL, REPORT = R23.SWEEP, R23.READING, R23.PROPOSAL, R23.REPORT
DATE = "2026-08-24"
EXPECTED_POOL = 1_098
SCAN_FROM = 997
EXPECTED_ROWS = 102
EXPECTED_MEMORY_REPEATS = 36
EXPECTED_FRESH = 66
EXPECTED_SOURCE_DUPLICATES = 0
EXPECTED_FIRST_RANK = 997
EXPECTED_LAST_RANK = 1_098
EXPECTED_FIRST_WORD = "ὅμως"
EXPECTED_LAST_WORD = "ποιήεις"
BATCH_SIZE = 51
CARD_COUNT = 102
Outcome = R23.Outcome


# A skeleton-only lexicon hit is not a homograph of an inflected sweep row.
# Keep such rows readable from their named sweep gloss, as round 23 already
# does when the surface lookup returns nothing.
def chosen_entry_with_strict_surface(row: dict) -> tuple[list[dict], dict, str]:
    entries, how = R2.LEX.look("ancient-greek", str(row["branch"]))
    if entries and how == "الصورةُ بنصِّها":
        selected = R2.BASE.select_lexicon(entries, str(row.get("gloss") or ""))
        return entries, entries[selected], how
    if row.get("gloss"):
        read = str(row.get("say") or "").split("  (")[0]
        entry = {
            "word": str(row["branch"]), "read": read, "pos": "inflected form",
            "en": str(row["gloss"]), "etym": "",
        }
        return [entry], entry, "صف المسح القاموسي المسمى؛ لا تورث مطابقة الهيكل مدخلة أخرى"
    return R23.ORIGINAL_CHOSEN_ENTRY(row)


R2.chosen_entry = chosen_entry_with_strict_surface


# Every non-open outcome is hand-read against the complete branch homograph
# set and the complete Arabic-root result set. Retrieval weight is not proof.
OUTCOMES: dict[int, Outcome] = {
    998: Outcome(
        "transmission", "منن",
        "الآرامية 𐡌𐡍𐡄 mnh، من الأكادية manû، هي مانح اسم الوزن والنقد",
        "قاموس الفرع يرد μνᾶ إلى الآرامية 𐡌𐡍𐡄 mnh ثم الأكادية manû؛ انتقال اسم مكيال ونقد من مانح سامي مسمى.",
    ),
    1011: Outcome(
        "root", "حمي", "حمى الشيء: منعه ودفع عنه؛ وحمى المكان: منعه أن يقرب",
        "hindrance وbulwark وholdfast وbuttress تلتقي الحماية والمنع في العربية؛ المدار حاجز يمسك الشيء ويدفع عنه النفاذ.", 3,
    ),
    1027: Outcome(
        "root", "زم", "زمه: شده وربطه؛ والزمام ما يزم به",
        "loincloth وband المسميان في الفرع رباطان يشدان على الجسد؛ المدار شد الشيء وربطه بما يمسكه.", 2,
    ),
    1034: Outcome(
        "root", "سل", "سل الشيء: نزعه وأخرجه؛ والإسلال السرقة الخفية",
        "right of seizure وreprisal في الفرع حق أخذ مال الغير ونزعه منه؛ المدار إخراج الشيء من يد حائزه بالأخذ.", 2,
    ),
    1046: Outcome(
        "root", "فش", "فش السقاء: حل رباطه بعد نفخه حتى خرجت الريح؛ وفش الوطب أخرج ريحه",
        "bellows وbladder وعاءان للهواء، وفش السقاء في العربية فتح الوعاء المنفوخ وإخراج ريحه؛ المدار وعاء ممتلئ بالهواء يعمل بخروجه.", 2,
    ),
    1066: Outcome(
        "root", "رف", "الرفرفة تحريك الطائر جناحه في الهواء وهو لا يبرح مكانه",
        "flapping of wings في مدخلة الفرع هو الرفرفة العربية نصا؛ وswing وsweep يحملان حركة الطرف نفسها.", 2,
    ),
    1067: Outcome(
        "transmission", "لف", "العبرية الكتابية אָלֶף ʾālep̄ هي مانح اسم الحرف",
        "قاموس الفرع يصرح باقتراض ἀλεφ من العبرية الكتابية אָלֶף؛ انتقال اسم الحرف من مانح سامي مسمى.",
    ),
    1072: Outcome(
        "law", "ذر", "ذر الشيء: فرقه ونثره فصار أجزاء متبددة",
        "divide وseparate في الفرع تلتقي تفريق الشيء ونثر أجزائه في ذر العربية؛ المدار فصل الكل إلى أجزاء، لكن δ إلى ذ بلا صف يوناني مسمى.", 2, "δ ↔ ذ",
    ),
    1074: Outcome(
        "root", "فشا", "فشا الشيء: ظهر وانتشر واتسع",
        "has sprung forth وbeen brought forth تلتقي ظهور الشيء وخروجه بعد كمونه في فشا؛ المدار بروز الموجود وانتشاره إلى الظاهر.", 3,
    ),
    1082: Outcome(
        "root", "ملل", "مللت الشيء: سئمته وبرمت به وأعرضت عنه",
        "to not care for وto disregard في الفرع هو الإعراض عن الشيء وترك الاهتمام به، وملل العربية السآمة التي تحمل صاحبها على الإعراض؛ المدار انصراف العناية عن الشيء.", 1,
    ),
    1096: Outcome(
        "root", "فتي", "استفتاه: سأله أن يفتي؛ والفتوى بيان الحكم",
        "to ask في الفرع يلتقي استفتاه في العربية، وهو سؤاله طلبا لبيان الحكم؛ المدار توجيه السؤال إلى من ينتظر منه جواب مبين.", 4,
    ),
    1098: Outcome(
        "root", "بش", "أبشت الأرض: التف نباتها؛ وقيل أنبتت أول نباتها",
        "grassy وcovered in grass في الفرع هو إبشاش الأرض في العربية: التفاف نباتها وظهور أوله؛ المدار أرض ظهر نباتها وانتشر.", 2,
    ),
}


def load_and_select() -> tuple[list[tuple[int, int, dict]], dict, set[str]]:
    """Select the complete 997..1098 tail and memory-check every exact form."""
    reading_text = R21.nfc(READING.read_text(encoding="utf-8"))
    if "<!-- LANE-A-GREEK-ROUND23-CHUNK-10:END -->" not in reading_text:
        raise AssertionError("الجولة الثالثة والعشرون غير مثبتة")
    if "<!-- LANE-A-GREEK-ROUND24-BATCH-1:START -->" in reading_text:
        raise AssertionError("بطاقات الجولة الرابعة والعشرين موجودة")
    if "LANE-A DONE23 100 996" not in REPORT.read_text(encoding="utf-8"):
        raise AssertionError("خاتمة DONE23 غير مثبتة")

    payload = json.loads(SWEEP.read_text(encoding="utf-8"))
    if payload.get("language") != "ancient_greek":
        raise AssertionError("اختلط لسان الحوض")
    rows = payload.get("both", [])
    if len(rows) != EXPECTED_POOL:
        raise AssertionError(f"تغير مقام الحوض: {len(rows)}")
    ordered = sorted(
        enumerate(rows, 1),
        key=lambda item: (-int(item[1].get("overlap") or 0), item[0]),
    )
    selected = [
        (expanded_rank, source_rank, row)
        for expanded_rank, (source_rank, row) in enumerate(ordered, 1)
        if expanded_rank >= SCAN_FROM
    ]
    words = [R21.nfc(item[2].get("branch")) for item in selected]
    if any(not word for word in words):
        raise AssertionError("صف بلا صورة في ذيل الحوض")
    source_duplicates = len(words) - len(set(words))
    memory_words = {word for word in words if word in reading_text}
    first = selected[0]
    last = selected[-1]
    actual = (
        len(selected), len(memory_words), len(selected) - len(memory_words),
        source_duplicates, first[0], last[0], first[2]["branch"], last[2]["branch"],
    )
    expected = (
        EXPECTED_ROWS, EXPECTED_MEMORY_REPEATS, EXPECTED_FRESH,
        EXPECTED_SOURCE_DUPLICATES, EXPECTED_FIRST_RANK, EXPECTED_LAST_RANK,
        EXPECTED_FIRST_WORD, EXPECTED_LAST_WORD,
    )
    if actual != expected:
        raise AssertionError(f"تغير ذيل الحوض أو ذاكرته: {actual!r}")
    return selected, {
        "pool": len(rows), "scan_from": SCAN_FROM, "rows": len(selected),
        "memory_repeats": len(memory_words), "fresh_rows": len(selected) - len(memory_words),
        "source_duplicates": source_duplicates, "first_rank": first[0], "last_rank": last[0],
    }, memory_words


def gather_hits(selected: list[tuple[int, int, dict]]) -> dict[str, list[dict]]:
    R23.OUTCOMES = OUTCOMES
    return R23.gather_hits(selected)


def build_card(
    expanded_rank: int,
    source_rank: int,
    row: dict,
    hits: dict[str, list[dict]],
    memory_words: set[str],
) -> tuple[str, dict]:
    R23.OUTCOMES = OUTCOMES
    card, record = R23.build_card(expanded_rank, source_rank, row, hits)
    card = card.replace("LANE-A-R23-", "LANE-A-R24-")
    word = R21.nfc(row["branch"])
    memory_line = (
        "- فحص الذاكرة: الصورة حاضرة قبل الجولة؛ أعيد فحص الرتبة ولم ترث حكم متحد الرسم."
        if word in memory_words else
        "- فحص الذاكرة: لا صورة مطابقة قبل الجولة؛ الصف طازج."
    )
    card, substitutions = re.subn(
        r"(?m)^(- الكلمة في الفرع:.*)$",
        rf"\1\n{memory_line}",
        card,
        count=1,
    )
    if substitutions != 1:
        raise AssertionError(f"تعذر وسم فحص الذاكرة: {expanded_rank}")
    witness_overrides = {
        1072: "- مسح المعاني العربية: قُرئت نتائج الجذر `ذر` بـ`--max-chars 0`؛ كتاب العين: «الذر مصدر ذررت، وهو أخذك الشيء بأطراف أصابعك تذره ذر الملح»؛ ولسان العرب: «ذر الشيء إذا بدده؛ وذررت الحب والملح والدواء: فرقته».",
        1096: "- مسح المعاني العربية: قُرئت نتائج الجذر `فتي` بـ`--max-chars 0`؛ المصباح المنير: «الفتوى اسم من أفتى العالم إذا بين الحكم، واستفتيته: سألته أن يفتي»؛ وأساس البلاغة: «فبت أفاتيها، أي أسائلها».",
        1098: "- مسح المعاني العربية: قُرئت نتائج الجذر `بش` بـ`--max-chars 0`؛ المحيط: «أعشبت الأرض وأبشت: التف نبتها؛ وقيل أنبتت أول نباتها»؛ ولم يُتَحْ شاهد كلاسيكي ثان بهذا المعنى في الموارد المسماة.",
    }
    if expanded_rank in witness_overrides:
        card, substitutions = re.subn(
            r"(?m)^- مسح المعاني العربية:.*$",
            witness_overrides[expanded_rank],
            card,
            count=1,
        )
        if substitutions != 1:
            raise AssertionError(f"تعذر تثبيت شاهد المعنى: {expanded_rank}")
    card, size = R21.R6.compact_to_limit(card, f"R24-{expanded_rank}")
    record["bytes"] = size
    record["memory_repeat"] = word in memory_words
    return card, record


def render_all() -> tuple[str, list[dict], dict]:
    selected, selection, memory_words = load_and_select()
    hits = gather_hits(selected)
    sections: list[str] = []
    records: list[dict] = []
    for batch in (1, 2):
        batch_rows = selected[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        sections += [
            f"<!-- LANE-A-GREEK-ROUND24-BATCH-{batch}:START -->", "",
            f"## اليونانية، الجولة الرابعة والعشرون: ذيل الحوض المضاعف، الدفعة {batch} ({DATE})", "",
            f"- النموذج `WO-B-PROBE-001`؛ 51 بطاقة؛ الرتبة الموسعة من {batch_rows[0][0]} إلى {batch_rows[-1][0]}؛ فُحص حضور كل صورة في ذاكرة السجل قبل الجولة.",
            "- الترتيب `overlap` نازل ثابت ثم موضع المصدر؛ قرئت المروحة كاملة، ولم يتحول وزن الاسترجاع ولا حكم متحد الرسم إلى حكم الصف.", "",
        ]
        for expanded_rank, source_rank, row in batch_rows:
            card, record = build_card(expanded_rank, source_rank, row, hits, memory_words)
            sections += [card, ""]
            records.append(record)
        sections.append(f"<!-- LANE-A-GREEK-ROUND24-BATCH-{batch}:END -->")
        if batch == 1:
            sections.append("")
    if len(records) != CARD_COUNT:
        raise AssertionError(f"عدد بطاقات الجولة: {len(records)}")
    return "\n".join(sections).rstrip(), records, selection


def proposal_addition(records: list[dict]) -> str:
    law = [record for record in records if record["closure"] == "LAW-GAP"]
    if not law:
        return ""
    grouped: dict[str, list[dict]] = {}
    for record in law:
        _licensed, _route, gaps = R2.sound_route(record["word"], record["root"])
        if not gaps:
            raise AssertionError(f"بطاقة LAW-GAP بلا ساق غائبة: {record['expanded_rank']}")
        for gap in dict.fromkeys(gaps):
            grouped.setdefault(gap, []).append(record)
    lines = [
        "## إلحاق شواهد الجولة الرابعة والعشرين، ذيل الحوض المضاعف", "",
        "فُتشت الشبكة النافذة بكل زوج حرفي وبتسميات الحرف اليوناني وبـ«اليونانية/Greek»؛ وحُسبت `BR-GREC-02..06` صفوفا مرخصة. هذه شواهد `LAW-GAP` وحدها؛ لا توصية بإضافة صف.", "",
        "| الساق الغائبة | الشواهد | الشاهد ومقابله | الحكم النافذ |", "|---|---:|---|---|",
    ]
    for gap, rows in grouped.items():
        examples = "؛ ".join(
            f"`{row['word']}`→`{row['root']}` «{OUTCOMES[row['expanded_rank']].counterpart}»"
            for row in rows
        )
        lines.append(f"| `{gap}` | {len(rows)} | {examples} | لا صف مجمد مسمى؛ تبقى البطاقات `LAW-GAP` |")
    lines += ["", "تبقى هذه البطاقات في `LAW-GAP` إلى قرار المؤلف؛ الإلحاق شاهد فقط."]
    return "\n".join(lines)


def report_addition(records: list[dict], selection: dict) -> str:
    first, second = records[:BATCH_SIZE], records[BATCH_SIZE:]

    def counts(rows: list[dict], field: str) -> str:
        return "؛ ".join(f"`{key}`={value}" for key, value in sorted(Counter(row[field] for row in rows).items()))

    law = [record for record in records if record["closure"] == "LAW-GAP"]
    return "\n".join([
        "<!-- LANE-A-GREEK-ROUND24-REPORT:START -->", "",
        f"## {DATE}، الجولة الرابعة والعشرون، ذيل الحوض المضاعف، الدفعة 1", "",
        f"- البطاقات: 51؛ الرتبة الموسعة: {first[0]['expanded_rank']} إلى {first[-1]['expanded_rank']}؛ آخر `overlap`={first[-1]['overlap']}.",
        "- توزيع الأحكام: " + counts(first, "verdict") + ".", "- توزيع الإغلاق: " + counts(first, "closure") + ".", "",
        f"## {DATE}، الجولة الرابعة والعشرون، ذيل الحوض المضاعف، الدفعة 2", "",
        f"- البطاقات: 51؛ الرتبة الموسعة: {second[0]['expanded_rank']} إلى {second[-1]['expanded_rank']}؛ آخر `overlap`={second[-1]['overlap']}.",
        "- توزيع الأحكام: " + counts(second, "verdict") + ".", "- توزيع الإغلاق: " + counts(second, "closure") + ".", "",
        "## حصيلة الجولة الرابعة والعشرين", "",
        f"- استؤنف الذيل من الرتبة {selection['scan_from']} إلى {selection['last_rank']} واستُنفد الحوض المضاعف كله.",
        f"- فحص الذاكرة قبل الجولة: حاضر الصورة={selection['memory_repeats']}؛ طازج الصورة={selection['fresh_rows']}؛ تكرار داخل الذيل={selection['source_duplicates']}.",
        "- مجموع البطاقات: 102؛ دفعتان من 51 بطاقة بنموذج `WO-B-PROBE-001`.",
        "- كل صف حاضر الصورة في الذاكرة أعيد فحصه مستقلا ولم يرث حكم متحد الرسم.",
        "- الإغلاق الكلي: " + counts(records, "closure") + ".", "- الحكم الكلي: " + counts(records, "verdict") + ".",
        f"- فجوات القانون: {len(law)}؛ ألحقت شواهدها في `proposed-shift-rows-greek.md` بعد احتساب `BR-GREC-02..06` صفوفا نافذة.",
        f"- حد الحجم: أكبر بطاقة {max(record['bytes'] for record in records)} بايت؛ لا بطاقة تجاوزت 5 كيلوبايت.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم يستعمل git إطلاقا.", "",
        "<!-- LANE-A-GREEK-ROUND24-REPORT:END -->", "", f"LANE-A DONE24 {len(records)} {records[-1]['expanded_rank']}",
    ])


def stage_patches() -> Path:
    rendered, records, selection = render_all()
    cards = [
        match.group(0).rstrip()
        for match in re.finditer(
            r"(?ms)^### بطاقة:.*?(?=^### بطاقة:|^<!-- LANE-A-GREEK-ROUND24-BATCH-[12]:END -->)",
            rendered,
        )
    ]
    if len(cards) != CARD_COUNT:
        raise AssertionError(f"تعذر تفكيك البطاقات: {len(cards)}")
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round24-"))
    previous_anchor = "<!-- LANE-A-GREEK-ROUND23-CHUNK-10:END -->"
    chunk_number = 0
    for batch in (1, 2):
        batch_records = records[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        batch_cards = cards[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        for offset in range(0, BATCH_SIZE, 10):
            chunk_number += 1
            chunk_cards = batch_cards[offset:offset + 10]
            lines: list[str] = []
            if offset == 0:
                lines += [
                    f"<!-- LANE-A-GREEK-ROUND24-BATCH-{batch}:START -->", "",
                    f"## اليونانية، الجولة الرابعة والعشرون: ذيل الحوض المضاعف، الدفعة {batch} ({DATE})", "",
                    f"- النموذج `WO-B-PROBE-001`؛ 51 بطاقة؛ الرتبة الموسعة من {batch_records[0]['expanded_rank']} إلى {batch_records[-1]['expanded_rank']}؛ فُحص حضور كل صورة في ذاكرة السجل قبل الجولة.",
                    "- الترتيب `overlap` نازل ثابت ثم موضع المصدر؛ قرئت المروحة كاملة، ولم يتحول وزن الاسترجاع ولا حكم متحد الرسم إلى حكم الصف.", "",
                ]
            for card in chunk_cards:
                lines += [card, ""]
            if offset + len(chunk_cards) == BATCH_SIZE:
                lines += [f"<!-- LANE-A-GREEK-ROUND24-BATCH-{batch}:END -->", ""]
            marker = f"<!-- LANE-A-GREEK-ROUND24-CHUNK-{chunk_number:02d}:END -->"
            lines.append(marker)
            patch = R23.R22.append_patch(READING, "\n".join(lines), previous_anchor)
            (stage / f"reading-{chunk_number:02d}.patch").write_text(patch, encoding="utf-8", newline="\n")
            previous_anchor = marker

    proposal = proposal_addition(records)
    tail = ["*** Begin Patch"]
    if proposal:
        tail += [
            "*** Update File: 04-cross-linguistic/proposed-shift-rows-greek.md", "@@",
            " | `χ ↔ ك` | 1 | `χορεία`→`كور` «كور الشيء: أداره؛ وكل دور كور» | لا صف مجمد مسمى؛ تبقى البطاقات `LAW-GAP` |",
            " ",
            " تبقى هذه البطاقات في `LAW-GAP` إلى قرار المؤلف؛ الإلحاق شاهد فقط.", "+",
            R23.R22.add_lines(proposal),
        ]
    tail += [
        "*** Update File: _inbox/lane-reports/2026-08-16-A.md", "@@", " LANE-A DONE23 100 996", "+",
        R23.R22.add_lines(report_addition(records, selection)), "*** End Patch", "",
    ]
    (stage / "proposal-report.patch").write_text("\n".join(tail), encoding="utf-8", newline="\n")
    return stage


def verify_installed() -> dict:
    reading = READING.read_text(encoding="utf-8")
    ids = [int(value) for value in re.findall(r"^### بطاقة:.*LANE-A-R24-(\d+)$", reading, re.MULTILINE)]
    markers = re.findall(r"<!-- LANE-A-GREEK-ROUND24-CHUNK-\d{2}:END -->", reading)
    section = reading.split("<!-- LANE-A-GREEK-ROUND24-BATCH-1:START -->", 1)[-1]
    section = section.split("<!-- LANE-A-GREEK-ROUND24-CHUNK-12:END -->", 1)[0]
    batch_counts = [
        len(re.findall(r"^### بطاقة:", section.split(f"<!-- LANE-A-GREEK-ROUND24-BATCH-{batch}:START -->", 1)[-1].split(f"<!-- LANE-A-GREEK-ROUND24-BATCH-{batch}:END -->", 1)[0], re.MULTILINE))
        for batch in (1, 2)
    ]
    cards = re.findall(
        r"(?ms)^### بطاقة:.*?(?=^### بطاقة:|^<!-- LANE-A-GREEK-ROUND24-(?:BATCH|CHUNK)-)",
        section,
    )
    max_bytes = max(len(card.rstrip().encode("utf-8")) for card in cards)
    required_fields = (
        "إصدار البروتوكول:", "الكلمة في الفرع:", "فحص الذاكرة:", "أقدم صورة مستعادة:",
        "الخطوة صفر", "درجة المقارنة:", "مسح المعاني العربية:", "المقابل من اللسان:",
        "مسار الصوت:", "الحدثُ من السجلِّ", "المعنى من قاموس الفرع:", "المدار:",
        "المصفاة:", "فصل المتجانسات والاقتراض:", "فحص المروحة كلها:", "مؤشر اليتم:",
        "إشعاع الأسرة في الفرع:", "إشعاع الأسرة في العربية:", "جسور الاسترداد المفحوصة:",
        "حالة الإغلاق:", "الحكم (استكشاف):", "ملاحظات:",
    )
    incomplete = sum(any(field not in card for field in required_fields) for card in cards)
    truncation_markers = len(re.findall(r"tokens truncated|chars truncated|lines truncated", section))
    present = section.count("فحص الذاكرة: الصورة حاضرة قبل الجولة")
    fresh = section.count("فحص الذاكرة: لا صورة مطابقة قبل الجولة")
    done = f"LANE-A DONE24 {CARD_COUNT} {EXPECTED_LAST_RANK}"
    expected_ids = list(range(EXPECTED_FIRST_RANK, EXPECTED_LAST_RANK + 1))
    proposal = PROPOSAL.read_text(encoding="utf-8")
    proposal_ok = (
        proposal.count("إلحاق شواهد الجولة الرابعة والعشرين") == 1
        and "`διαιρῶ`→`ذر`" in proposal
        and "`δ ↔ ذ`" in proposal
    )
    if (ids != expected_ids or len(markers) != 12 or batch_counts != [BATCH_SIZE, BATCH_SIZE]
            or len(cards) != CARD_COUNT or max_bytes > 5_120 or incomplete or truncation_markers
            or present != EXPECTED_MEMORY_REPEATS or fresh != EXPECTED_FRESH
            or not proposal_ok or done not in REPORT.read_text(encoding="utf-8")):
        raise AssertionError(
            f"التحقق فشل: بطاقات={len(ids)} دفعتان={batch_counts} قطع={len(markers)} "
            f"أكبر={max_bytes} ناقص={incomplete} اقتطاع={truncation_markers} "
            f"حاضر={present} طازج={fresh} شاهد={proposal_ok}"
        )
    return {
        "cards": len(ids), "batches": batch_counts, "chunks": len(markers),
        "first_id": ids[0], "last_id": ids[-1], "max_bytes": max_bytes,
        "incomplete_cards": incomplete, "truncation_markers": truncation_markers,
        "memory_repeats": present, "fresh": fresh, "law_gap_witness": proposal_ok, "done": done,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", action="store_true")
    parser.add_argument("--verify-installed", action="store_true")
    parser.add_argument("--records", action="store_true")
    parser.add_argument("--selection", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.verify_installed:
        print(json.dumps(verify_installed(), ensure_ascii=False, indent=2)); return 0
    if args.selection:
        selected, meta, memory_words = load_and_select()
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        for expanded_rank, source_rank, row in selected:
            print(json.dumps({
                "expanded_rank": expanded_rank, "source_rank": source_rank,
                "branch": row.get("branch"), "say": row.get("say"), "gloss": row.get("gloss"),
                "best": row.get("best"), "overlap": row.get("overlap"),
                "memory_repeat": R21.nfc(row.get("branch")) in memory_words,
                "candidates": list(row.get("candidates_found") or []),
            }, ensure_ascii=False, separators=(",", ":")))
        return 0
    if args.stage:
        print(stage_patches()); return 0
    _rendered, records, selection = render_all()
    print(json.dumps({
        **selection, "cards": len(records),
        "closures": dict(Counter(record["closure"] for record in records)),
        "verdicts": dict(Counter(record["verdict"] for record in records)),
        "max_bytes": max(record["bytes"] for record in records),
    }, ensure_ascii=False, indent=2))
    if args.records:
        for record in records:
            print(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
