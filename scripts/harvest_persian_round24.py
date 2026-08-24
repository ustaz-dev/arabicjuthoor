# -*- coding: utf-8 -*-
"""المسار B، الجولة 24: دفعتان من حوض both الفارسي بعد الرتبة 343."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import harvest_persian_round23 as P  # noqa: E402

H = P.H
READING = ROOT / "04-cross-linguistic" / "readings" / "persian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-B.md"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-persian.json"
LEXICON = ROOT / "data" / "branch-lexicons" / "persian.json"
RAW_LEXICON = ROOT / "Resources" / "persian" / "kaikki.org-dictionary-Persian.jsonl"
MARKER = "LANE-B-PERSIAN-ROUND24-2026-08-24"
BATCH_SIZE = 35
CARD_LIMIT = 5120

EXPECTED_RANKS = (
    344, 345, 346, 347, 348, 349, 350, 351, 352, 353,
    354, 355, 356, 357, 358, 359, 360, 361, 364, 365,
    366, 367, 369, 371, 372, 375, 376, 381, 383, 386,
    390, 391, 394, 397, 398, 400, 407, 408, 411, 413,
    414, 415, 416, 417, 418, 419, 420, 421, 422, 423,
    424, 425, 426, 427, 429, 430, 431, 432, 433, 434,
    435, 436, 437, 438, 439, 440, 441, 442, 443, 444,
)

EXPECTED_ENTRY_INDEX = {
    344: 11625, 345: 12040, 346: 12041, 347: 12320,
    348: 12956, 349: 13399, 350: 13675, 351: 14176,
    352: 14202, 353: 14318, 354: 14378, 355: 14643,
    356: 14696, 357: 14769, 358: 14783, 359: 14789,
    361: 14792, 364: 15087, 365: 15139, 366: 15262,
    367: 11536, 369: 2574, 371: 913, 372: 3674,
    375: 6345, 376: 7853, 381: 1674, 383: 2083,
    386: 2986, 390: 4114, 391: 4304, 394: 6083,
    397: 7616, 398: 7880, 400: 8603, 407: 14512,
    408: 14618, 411: 15939, 413: 221, 414: 371,
    415: 501, 416: 518, 417: 744, 418: 775,
    419: 864, 420: 1142, 421: 1328, 422: 1329,
    423: 1337, 424: 1671, 425: 1803, 426: 1915,
    427: 1916, 429: 2680, 430: 2684, 431: 2786,
    432: 2871, 433: 2937, 434: 3068, 435: 3089,
    436: 3157, 437: 3221, 438: 3554, 439: 3618,
    440: 3746, 441: 3937, 442: 4089, 443: 4129,
    444: 4138,
}

EXPECTED_RAW_LINES = {
    350: 16526, 354: 17268, 356: 17610, 360: 17716,
    367: 14176, 369: 2807, 397: 8923, 407: 17415,
    408: 17525, 411: 18996, 414: 400, 420: 1215,
    426: 2015, 427: 2016, 432: 3151, 434: 3401,
    435: 3428, 437: 3590, 438: 3975,
}

CANDIDATE_OVERRIDES = {
    344: "خيم", 349: "حير", 355: "كاف", 365: "قصو",
    366: "كوب", 371: "رود", 407: "خشك", 431: "سري",
}

EXACT_DECOMPOSITIONS = {356, 367, 397, 407}

BLOCKED_BOUNDARIES = {
    350: "قال Kaikki: By surface analysis ثم X + Y، لا سطر From X + Y مباشر.",
    354: "قال Kaikki: in its compound form، بلا سطر From X + Y مباشر.",
    369: "قال Kaikki: from X and the suffix Y، لا From X + Y مباشر.",
    408: "أعطى Kaikki X + Y مجردا من From، فلا يؤهل للتفكيك.",
    411: "قال Kaikki: By surface analysis ثم X + Y، لا From X + Y مباشر.",
    414: "قال Kaikki: with suffix attached، بلا سطر From X + Y مباشر.",
    420: "قال Kaikki: equivalent to X + Y داخل إعادة بناء أقدم، لا سطر تفكيك مباشر.",
    426: "ذكر Kaikki تركيبا تاريخيا وتحليلا تزامنيا بـX + Y، بلا From X + Y مباشر.",
    427: "ذكر Kaikki تركيبا تاريخيا وتحليلا تزامنيا بـX + Y، بلا From X + Y مباشر.",
    432: "قال Kaikki: equivalent to X + Y في الأصل القديم، لا سطر تفكيك مباشر.",
    434: "قال Kaikki: possibly a dialectal combination of X + Y، لا From X + Y مباشر.",
    435: "انتهى خبر الأصل بإعادة بناء root + suffix بعد سلسلة نسب، لا From X + Y مباشر للمدخلة.",
    437: "قال Kaikki: Ellipsis of a phrase، ولم يعط سطر From X + Y.",
    438: "ذكر Kaikki جذرا أوليا + suffix في شرح الأصل، لا سطر From X + Y مباشر.",
}

VERDICTS = {
    344: "ROOT-TRACE", 345: "OPEN-CANDIDATE", 346: "LAW-GAP",
    347: "OPEN-CANDIDATE", 348: "LAW-GAP", 349: "ROOT-TRACE",
    350: "COMPOUND-BOUNDARY", 351: "OPEN-CANDIDATE",
    352: "OPEN-CANDIDATE", 353: "LAW-GAP",
    354: "COMPOUND-BOUNDARY", 355: "OPEN-CANDIDATE",
    356: "COMPOUND-BOUNDARY", 357: "MORPHOLOGY-GAP",
    358: "MORPHOLOGY-GAP", 359: "MORPHOLOGY-GAP",
    360: "MORPHOLOGY-GAP", 361: "MORPHOLOGY-GAP",
    364: "LAW-GAP", 365: "LAW-GAP", 366: "ROOT-TRACE",
    367: "COMPOUND-BOUNDARY", 369: "COMPOUND-BOUNDARY",
    371: "OPEN-CANDIDATE", 372: "OPEN-CANDIDATE",
    375: "MORPHOLOGY-GAP", 376: "LAW-GAP", 381: "LAW-GAP",
    383: "OPEN-CANDIDATE", 386: "LAW-GAP", 390: "LAW-GAP",
    391: "LAW-GAP", 394: "LAW-GAP", 397: "COMPOUND-BOUNDARY",
    398: "LAW-GAP", 400: "LAW-GAP", 407: "COMPOUND-BOUNDARY",
    408: "COMPOUND-BOUNDARY", 411: "COMPOUND-BOUNDARY",
    413: "OPEN-CANDIDATE", 414: "COMPOUND-BOUNDARY",
    415: "LAW-GAP", 416: "LAW-GAP", 417: "OPEN-CANDIDATE",
    418: "OPEN-CANDIDATE", 419: "LAW-GAP",
    420: "COMPOUND-BOUNDARY", 421: "OPEN-CANDIDATE",
    422: "OPEN-CANDIDATE", 423: "LAW-GAP",
    424: "OPEN-CANDIDATE", 425: "LAW-GAP",
    426: "COMPOUND-BOUNDARY", 427: "COMPOUND-BOUNDARY",
    429: "OPEN-CANDIDATE", 430: "OPEN-CANDIDATE",
    431: "ROOT-TRACE", 432: "COMPOUND-BOUNDARY",
    433: "OPEN-CANDIDATE", 434: "COMPOUND-BOUNDARY",
    435: "COMPOUND-BOUNDARY", 436: "OPEN-CANDIDATE",
    437: "COMPOUND-BOUNDARY", 438: "COMPOUND-BOUNDARY",
    439: "LAW-GAP", 440: "OPEN-CANDIDATE",
    441: "OPEN-CANDIDATE", 442: "OPEN-CANDIDATE",
    443: "OPEN-CANDIDATE", 444: "OPEN-CANDIDATE",
}

SPECIAL_ORBITS = {
    344: (
        "الفرع يسمي الجوهر والطبيعة والسجية، والصحاح والعين يثبتان "
        "الخيم للسجية والطبيعة ولسعة الخلق؛ نقطة الطبع والخصلة واحدة."
    ),
    349: (
        "الفرع يسمي انبهار البصر والتحديق، والمحكم ولسان العرب يثبتان "
        "حار بصره إذا عشي عند النظر؛ نقطة تحير النظر وانبهاره واحدة."
    ),
    355: (
        "الفرع يسمي حرف گ، والمروحة تبلغ كاف العربية عبر صف گ↔ك المسمى، "
        "لكن الاسمين يحيلان إلى حرفين مختلفين؛ لم تتحول تسمية الحرف العامة إلى مدار."
    ),
    365: (
        "الفرع يسمي الإرسال والإبعاد، والعربية في قصو تسمي البعد "
        "والإقصاء، لكن گ↔ق غير مسمى؛ بقي المدار خلف فجوة القانون."
    ),
    366: (
        "الفرع يسمي كأس الحجامة، والصحاح والمفردات يثبتان الكوب كوزا "
        "أو قدحا بلا عروة؛ الوعاء الكأسي نفسه هو المدار."
    ),
    390: (
        "الفرع يسمي القطع، والمصباح والمحيط يثبتان شرط الحجام بالمشرط "
        "أي بزغه، لكن چ↔ش غير مسمى؛ لم يصدر حكم موجب."
    ),
    431: (
        "الفرع يسمي الخالص الجيد الممتاز، والتاج والمصباح يثبتان السري "
        "للنفيس وخيار المال؛ نقطة الجودة والامتياز واحدة."
    ),
}

H.TARGET_NEEDLES.update({
    "خيم": ("الخيمُ بالكسر: السجيّة والطبيعة", "الخِيمُ: سعة الخلق", "السجيّة والطبيعة", "سعة الخلق"),
    "حير": ("حارَ بَصَرُه", "حار بَصَرُه", "أَصْلُهُ أَنْ يَنْظُرَ الإِنْسَانُ", "فَعَشِيَ بَصَرُهُ"),
    "كوب": ("الكوبُ: كُوزٌ لا عُروةَ له", "الْكَوْبُ: قدح لا عروة له", "الكُوب: الَّذِي لَا عُروة لَهُ"),
    "سري": ("السَّرِيّ وَهُوَ النَّفِيس", "سَرِيُّ الْمَالِ خِيَارُهُ", "السري وهو النفيس"),
    "قصو": ("قَصَا الْمَكَانُ", "أَقْصَيْتُهُ أَبْعَدْتُهُ", "القصي، والقاصي: الْبعيد"),
    "شرط": ("شَرَطَ الْحَاجِمُ", "بَزْغُ الحَجّامِ", "بالمِشْرَطِ"),
    "خشك": ("اليابس", "الجاف", "الخبز اليابس"),
})

WITNESS_PRIORITY = dict(P.WITNESS_PRIORITY)
WITNESS_PRIORITY.update({
    "خيم": ("al_sihah", "kitab_al_ayn"),
    "حير": ("al_muhkam", "lisan"),
    "كوب": ("al_sihah", "al_mufradat"),
    "سري": ("taj_al_arus", "al_misbah"),
    "قصو": ("al_muhkam", "al_misbah"),
    "شرط": ("al_misbah", "al_muhit"),
})


def candidate_for(row: H.SweepRow) -> str:
    return CANDIDATE_OVERRIDES.get(row.rank, row.best)


def classical_witnesses(
    candidate: str,
    sense_map: dict[str, list[dict]],
    quote_limit: int,
) -> tuple[int, int, list[tuple[str, str]]]:
    matches = sense_map.get(candidate, [])
    by_source: dict[str, dict] = {}
    needles = H.TARGET_NEEDLES.get(candidate, ())
    for item in matches:
        source_id = H.SENSES.canonical_source_id(str(item.get("source") or ""))
        definition = H.clean(item.get("definition") or "")
        if source_id not in H.CLASSICAL_PRIORITY or not definition:
            continue
        hit_count = sum(needle in definition for needle in needles)
        if needles and hit_count == 0:
            continue
        incumbent = by_source.get(source_id)
        incumbent_hits = (
            sum(
                needle in H.clean(incumbent.get("definition") or "")
                for needle in needles
            )
            if incumbent else -1
        )
        if hit_count > incumbent_hits:
            by_source[source_id] = item
    preferred = WITNESS_PRIORITY.get(candidate, ())
    priority = preferred + tuple(
        source for source in H.CLASSICAL_PRIORITY if source not in preferred
    )
    selected: list[tuple[str, str]] = []
    for source_id in priority:
        item = by_source.get(source_id)
        if not item:
            continue
        label = H.SENSES.SOURCE_LABELS.get(
            source_id, H.clean(item.get("source") or source_id)
        )
        selected.append((
            H.clean(label),
            H.targeted_excerpt(
                str(item.get("definition") or ""), candidate, quote_limit
            ),
        ))
        if len(selected) == 2:
            break
    coverage = len(selected)
    while len(selected) < 2:
        selected.append((
            "فجوة المورد",
            "لم يرد شاهد عربي كلاسيكي مستقل ثان في الموارد المسماة؛ الغياب لا ينفي اللسان.",
        ))
    return len(matches), coverage, selected


def select_fresh(
    rows: list[H.SweepRow], reading_text: str
) -> tuple[list[H.SweepRow], int, int]:
    pairs = H.read_pairs(reading_text)
    pair_read = {row.rank for row in rows if H.already_read(row, pairs)}
    id_read = {
        int(value) for value in re.findall(
            r"^### WO-B-R(?:21|22|23|24)-BOTH-(\d{5}):",
            reading_text,
            re.MULTILINE,
        )
    }
    read = pair_read | id_read
    fresh = [row for row in rows if row.rank not in read]
    fresh.sort(key=lambda row: (-row.overlap, row.rank))
    selected = fresh[:70]
    if len(rows) != 494:
        raise AssertionError(f"حوض both ليس 494: {len(rows)}")
    if len(read) != 384 or len(fresh) != 110:
        raise AssertionError(
            f"تغير موضع الاستئناف: مقروء={len(read)}، طازج={len(fresh)}"
        )
    if tuple(row.rank for row in selected) != EXPECTED_RANKS:
        raise AssertionError("تغير ترتيب السبعين الطازجة بعد الرتبة 343")
    return selected, len(read), len(fresh)


def select_branch_entries(
    rows: list[H.SweepRow], lexicon: dict
) -> tuple[dict[int, H.BranchEntry], dict[str, list[tuple[int, dict]]]]:
    grouped: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for index, entry in enumerate(lexicon["entries"]):
        grouped[H.clean(entry.get("word") or "")].append((index, entry))
    selected: dict[int, H.BranchEntry] = {}
    for row in rows:
        if row.rank == 360:
            selected[row.rank] = H.BranchEntry(
                global_index=-1,
                homograph_index=1,
                homograph_count=1,
                word=row.branch,
                reading="-gi",
                pos="suffix",
                gloss=row.gloss,
                etymology="فجوة اشتقاق في مدخلة Kaikki الخام.",
            )
            continue
        candidates = grouped.get(row.branch, [])
        if not candidates:
            raise AssertionError(f"لا مدخلة فرع للرسم {row.branch}")
        global_index, entry = max(
            candidates,
            key=lambda item: H.entry_score(H.norm_gloss(row.gloss), item[1]),
        )
        homograph_index = 1 + next(
            i for i, item in enumerate(candidates) if item[0] == global_index
        )
        selected[row.rank] = H.BranchEntry(
            global_index=global_index,
            homograph_index=homograph_index,
            homograph_count=len(candidates),
            word=H.clean(entry.get("word") or ""),
            reading=H.clean(entry.get("read") or row.say),
            pos=H.clean(entry.get("pos") or ""),
            gloss=H.clean(entry.get("en") or ""),
            etymology=H.clean(
                entry.get("etym") or "فجوة اشتقاق في لقطة الفرع."
            ),
        )
    for rank, index in EXPECTED_ENTRY_INDEX.items():
        if selected[rank].global_index != index:
            raise AssertionError(
                f"انزلق متجانس الرتبة {rank}: {selected[rank].global_index}"
            )
    return selected, grouped


def raw_gloss(entry: dict) -> str:
    glosses: list[str] = []
    for sense in entry.get("senses") or []:
        glosses.extend(str(value) for value in sense.get("glosses") or [])
    return H.clean("; ".join(glosses))


def load_raw_entries(
    rows: list[H.SweepRow], entries: dict[int, H.BranchEntry]
) -> dict[int, dict]:
    wanted = {row.branch for row in rows}
    grouped: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    with RAW_LEXICON.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            item = json.loads(line)
            word = H.clean(item.get("word") or "")
            if word in wanted:
                grouped[word].append((line_number, item))
    selected: dict[int, dict] = {}
    for row in rows:
        options = grouped.get(row.branch, [])
        if not options:
            raise AssertionError(f"غابت مدخلة Kaikki الخام للرتبة {row.rank}")
        if row.rank == 360:
            line_number, item = next(
                pair for pair in options if pair[0] == EXPECTED_RAW_LINES[360]
            )
        else:
            same_pos = [
                pair for pair in options
                if H.clean(pair[1].get("pos") or "") == entries[row.rank].pos
            ]
            pool = same_pos or options
            line_number, item = max(
                pool,
                key=lambda pair: H.entry_score(
                    H.norm_gloss(entries[row.rank].gloss),
                    {"en": raw_gloss(pair[1])},
                ),
            )
        selected[row.rank] = {
            "line": line_number,
            "entry": item,
            "gloss": raw_gloss(item),
            "etymology": H.clean(item.get("etymology_text") or ""),
        }
    for rank, line_number in EXPECTED_RAW_LINES.items():
        if selected[rank]["line"] != line_number:
            raise AssertionError(
                f"انزلقت مدخلة Kaikki الخام للرتبة {rank}: "
                f"{selected[rank]['line']}"
            )
    raw_360 = selected[360]
    if (
        H.clean(raw_360["entry"].get("word") or "") != "ـگی"
        or raw_360["gloss"] != EXPECTED_GLOSS_360
    ):
        raise AssertionError("تغيرت مدخلة ـگی الخام")
    return selected


EXPECTED_GLOSS_360 = (
    "form of the suffix ـی (-ī /-i) for words that end in the short vowel ـه (-a /-e)"
)


def direct_from_plus(etymology: str) -> tuple[str, str] | None:
    """يلتقط فقط عبارة Kaikki النهائية المباشرة From X + Y."""
    matches = list(re.finditer(r"(?:^|\s)From (.+?) \+ (.+?)\.", etymology))
    for match in reversed(matches):
        if match.end() != len(etymology):
            continue
        left = H.clean(match.group(1))
        right = H.clean(match.group(2))
        lowered = left.casefold()
        if len(left) > 150 or " from " in lowered or " compare " in lowered:
            continue
        return left, right
    return None


COMPONENTS = {
    356: (
        "`گوار`، مسمى في سطر Kaikki الخام 17610 جذع حاضر من `گواریدن` للهضم، "
        "ولا مدخلة مستقلة له؛ قُرئت مروحته ذات 80 مرشحا كاملة: MORPHOLOGY-GAP. "
        "`ـا`، قُرئت مداخلها الثلاث 7535-7537 واختيرت 7536 لاحقة صفة واسم؛ "
        "مروحتها صفر: MORPHOLOGY-GAP."
    ),
    367: (
        "`پا`، قُرئت مدخلتاه 156-157 واختيرت 156 للرجل والقدم، ومروحته ذات "
        "36 مرشحا كاملة؛ `پا↔با`: OPEN-CANDIDATE. `ـچه`، المدخلة 7513، "
        "لاحقة تصغير، ومروحتها ذات 60 مرشحا: MORPHOLOGY-GAP."
    ),
    397: (
        "`گشای`، سطر Kaikki الخام 10707، جذع حاضر من `گشادن` و`گشودن`، "
        "وقُرئت مروحته ذات 120 مرشحا كاملة بلا مدار عربي مباشر: OPEN-CANDIDATE. "
        "`ـش`، قُرئت مدخلتاها 10301-10302 واختيرت 10302 لصنع اسم الحدث، "
        "ومروحتها صفر: MORPHOLOGY-GAP."
    ),
    407: (
        "`خشک`، المدخلة 1835 وسطر Kaikki الخام 1932، للجاف واليابس؛ قُرئت "
        "مروحته ذات 18 مرشحا ونتيجتا `خشك`، ولم يكتمل شاهدان دلاليان مباشران: "
        "SOURCE-GAP. `ـی`، قُرئت مداخلها الأربع 6327-6330 واختيرت 6329 "
        "لصنع الاسم المجرد، ومروحتها صفر: MORPHOLOGY-GAP."
    ),
}


def validate_component_inventory(grouped: dict[str, list[tuple[int, dict]]]) -> None:
    expected_indices = {
        "ـا": {7535, 7536, 7537},
        "پا": {156, 157},
        "ـچه": {7513},
        "ـش": {10301, 10302},
        "خشک": {1835},
        "ـی": {6327, 6328, 6329, 6330},
    }
    for word, expected in expected_indices.items():
        actual = {index for index, _ in grouped.get(word, [])}
        if actual != expected:
            raise AssertionError(f"تغير جرد مكون {word}: {sorted(actual)}")
    fan_counts = {
        "گوار": 80, "ـا": 0, "پا": 36, "ـچه": 60,
        "گشای": 120, "ـش": 0, "خشک": 18, "ـی": 0,
    }
    for word, expected in fan_counts.items():
        ranked = tuple(H.FAN.rank(word, H.FAN.fan(word, "persian"), "persian"))
        if len(ranked) != expected:
            raise AssertionError(
                f"تغيرت مروحة المكون {word}: {len(ranked)} لا {expected}"
            )


def decomposition_line(
    row: H.SweepRow, raw_entry: dict
) -> str | None:
    if row.rank not in EXACT_DECOMPOSITIONS:
        return None
    decomposition = direct_from_plus(raw_entry["etymology"])
    if not decomposition:
        raise AssertionError(f"غاب سطر From X + Y للرتبة {row.rank}")
    return (
        f"- تفكيك Kaikki الحصري من السطر الخام {raw_entry['line']}: "
        f"«{H.clip(raw_entry['etymology'], 420)}».\n"
        f"- قراءة المكونات المستقلة: {COMPONENTS[row.rank]}"
    )


def decide(row: H.SweepRow) -> H.Decision:
    candidate = candidate_for(row)
    verdict = VERDICTS[row.rank]
    if row.rank in SPECIAL_ORBITS:
        orbit = SPECIAL_ORBITS[row.rank]
    elif verdict == "COMPOUND-BOUNDARY":
        if row.rank in EXACT_DECOMPOSITIONS:
            orbit = (
                "قاموس Kaikki أعطى سطر From X + Y المباشر؛ قُرئ كل مكون "
                "وحده، ولم ترث الصورة المجموعة حكم أي مكون."
            )
        else:
            orbit = (
                "ظهرت بنية متعددة الأجزاء في خبر الأصل، لكن صيغتها لا تطابق "
                "سطر From X + Y المباشر؛ وقف الحكم عند الحد بلا مكونات مخترعة."
            )
    elif verdict == "MORPHOLOGY-GAP":
        orbit = (
            "العضو لاحقة صرفية لا مادة معجمية عربية مقابلة؛ التداخل الآلي "
            "لا يحول الوظيفة الصرفية إلى جذر."
        )
    elif verdict == "SOURCE-GAP":
        orbit = (
            f"قُرئ معنى الفرع «{row.gloss}»، ولم يكتمل شاهدان عربيان "
            f"كلاسيكيان مستقلان للمادة `{candidate}` بهذا المعنى."
        )
    else:
        orbit = (
            f"الفرع يسمي «{row.gloss}»؛ وبعد قراءة شواهد `{candidate}` "
            "لم تتحد نقطة المعنى اتحادا مباشرا، فلا يصنع تداخل المسح وحده مدارا."
        )
    if verdict == "LAW-GAP":
        obstacle = "رجل الصوت غير مكتملة بصف مسمى؛ لم يصدر حكم موجب."
    elif verdict == "SOURCE-GAP":
        obstacle = "لم يكتمل شاهدان عربيان كلاسيكيان مستقلان؛ غياب المورد لا ينفي اللسان."
    elif verdict == "OPEN-CANDIDATE":
        obstacle = "الصوت قابل للرصف، لكن رجل المعنى المباشر لم تثبت بعد قراءة الشاهدين والمتجانسات."
    elif verdict == "COMPOUND-BOUNDARY":
        obstacle = "الحكم وقف عند حد المركب؛ لم تورث الصورة المجموعة حكم مكون."
    elif verdict == "MORPHOLOGY-GAP":
        obstacle = "المقارنة المعجمية لا تسند معنى جذريا إلى لاحقة صرفية."
    else:
        obstacle = "اكتملت أرجل الصوت والحدث والمعنى بشاهدين عربيين كلاسيكيين مستقلين."
    return H.Decision(candidate, verdict, H.state_for(verdict), orbit, obstacle)


def make_card(
    row: H.SweepRow,
    entry: H.BranchEntry,
    raw_entry: dict,
    decision: H.Decision,
    ranked: tuple[tuple[str, float], ...],
    sense_map: dict[str, list[dict]],
    quote_limit: int,
    etym_limit: int,
) -> str:
    match_count, classical_count, witnesses = classical_witnesses(
        decision.candidate, sense_map, quote_limit
    )
    component = decomposition_line(row, raw_entry)
    etymology = (
        raw_entry["etymology"]
        if row.rank in EXACT_DECOMPOSITIONS | set(BLOCKED_BOUNDARIES)
        else entry.etymology
    ) or "فجوة اشتقاق في مدخلة Kaikki الخام."
    if row.rank == 360:
        entry_reference = "سطر Kaikki الخام 17716؛ غابت من لقطة branch-lexicons"
    else:
        entry_reference = f"entries[{entry.global_index}]"
    lines = [
        f"### WO-B-R24-BOTH-{row.rank:05d}: `{row.branch}` /{entry.reading}/، رتبة overlap {row.rank}",
        "- إصدار البروتوكول: RECOVERY-v2 (2026-08-16)؛ نموذج WO-B-PROBE-001.",
        (
            f"- مرجع الحوض المضاعف: `phonetic-sweep-persian.json:both[{row.rank - 1}]`؛ "
            f"overlap={row.overlap}؛ shared={','.join(row.shared)}؛ "
            "الترتيب مدخل قراءة لا قرينة حكم."
        ),
        f"- الكلمة في الفرع: فارسية `{row.branch}` /{entry.reading}/؛ الصنف `{entry.pos}`.",
        (
            f"- قراءة مداخل الرسم المتجانس: قُرئت {entry.homograph_count} مدخلة "
            f"للرسم `{row.branch}`؛ المختارة المدخلة {entry.homograph_index}، "
            f"{entry_reference}؛ لم تؤخذ الأولى آليا."
        ),
        (
            f"- أقدم صورة مستعادة: «{H.clip(etymology, etym_limit)}» "
            f"[Kaikki؛ السطر الخام {raw_entry['line']}]."
        ),
    ]
    if component:
        lines.extend([
            component,
            "- الخطوة صفر: قبل التفكيك الحرفي From X + Y لم تقارن الصورة وحدة جذرية؛ قُرئ كل مكون وحده.",
        ])
    elif row.rank in BLOCKED_BOUNDARIES:
        lines.extend([
            f"- حد المركب غير المفكك: {BLOCKED_BOUNDARIES[row.rank]}",
            "- الخطوة صفر: لم يقبل تحليل سطحي أو مكافأة أو عطفا أو اشتقاقا غير مباشر؛ وقف الحكم COMPOUND-BOUNDARY بلا مكونات مخترعة.",
        ])
    else:
        lines.append(
            f"- الخطوة صفر: طُرحت صوائت الفرع وصرفه المسمى فقط؛ الهيكل "
            f"`{'ـ'.join(row.skeleton)}` وعدد صوامته {len(row.skeleton)}؛ لم يسقط صامت حدسا."
        )
    lines.extend([
        f"- درجة المقارنة: {H.comparison_degree(decision.candidate)}",
        (
            f"- المروحة المرتبة الكاملة: `fan_any_script.fan({row.branch}, persian)`؛ "
            f"العدد {len(ranked)}: {H.formatted_fan(ranked)}."
        ),
        (
            f"- فحص المروحة كلها: قُرئت مواد المرشحين {len(ranked)} بـ`--max-chars 0`؛ "
            "المرشح المختار من داخلها لا من عمود `best` وحده."
        ),
        f"- المقابل من اللسان: `{decision.candidate}`؛ مادة الفحص المختارة من المروحة.",
        f"- مسار الصوت والحد المسمى: {H.formatted_route(row, decision.candidate)}",
        f"- الحدث من السجل المجمد كما هو: {H.event_line(decision.candidate)}",
        f"- المعنى من قاموس الفرع بلا رتوش: «{entry.gloss}».",
        (
            f"- مسح المعاني العربية: قُرئت {match_count} نتيجة لـ`{decision.candidate}` كاملة؛ "
            f"الشواهد العربية الكلاسيكية المستقلة={classical_count}؛ نُقل شاهدان فقط:"
        ),
        f"  - الشاهد 1، {witnesses[0][0]}: «{witnesses[0][1]}»",
        f"  - الشاهد 2، {witnesses[1][0]}: «{witnesses[1][1]}»",
        f"- المدار المكتوب بالكلمات: {decision.orbit}",
        "- المصفاة: الأصل حاشية؛ لا يغلق النقل إلا مانح عربي أو سامي مسمى، أو تصريح عربي مستقل بالتعريب.",
        "- فصل المتجانسات والاقتراض: الحكم للمدخلة وحدها؛ لا توارث من متحد الرسم.",
        "- اليتم والإشعاع: الجرد حاضر؛ العربية شاهداها أو فجوتها؛ لا حصر ولا قرينة عدد.",
        "- جسور الاسترداد المفحوصة: الفرع؛ الأصل؛ الصفر؛ المروحة؛ الشبكة؛ `all_tiers`؛ الشواهد؛ المصفاة؛ المركب.",
        f"- عائق القرار أو تمامه: {decision.obstacle}",
        f"- ملاحظات العدستين: استرداد حتى القرار، وتشكيك مقصور على العضو؛ الجولة 24، الرتبة {row.rank:05d}.",
        f"- حالة الإغلاق: {decision.state}.",
        f"- الحكم (استكشاف): {decision.verdict}.",
    ])
    return "\n".join(lines) + "\n"


def fit_card(
    row: H.SweepRow,
    entry: H.BranchEntry,
    raw_entry: dict,
    decision: H.Decision,
    ranked: tuple[tuple[str, float], ...],
    sense_map: dict[str, list[dict]],
) -> str:
    for quote_limit, etym_limit in (
        (230, 340), (180, 280), (130, 210), (90, 150),
        (60, 105), (35, 70), (20, 45), (12, 25),
    ):
        text = make_card(
            row, entry, raw_entry, decision, ranked, sense_map,
            quote_limit, etym_limit,
        )
        if len(text.encode("utf-8")) < CARD_LIMIT:
            return text
    raise AssertionError(
        f"تجاوزت بطاقة الرتبة {row.rank:05d} حد 5KB: "
        f"{len(text.encode('utf-8'))}"
    )


def detected_blocked_boundaries(
    rows: list[H.SweepRow], raw_entries: dict[int, dict]
) -> set[int]:
    blocked: set[int] = set()
    morphology_rows = {357, 358, 359, 360, 361, 375}
    for row in rows:
        if row.rank in morphology_rows or row.rank in EXACT_DECOMPOSITIONS:
            continue
        etymology = raw_entries[row.rank]["etymology"]
        structural = (
            "+" in etymology
            or "surface analysis" in etymology
            or "compound form" in etymology
            or "the suffix" in etymology
            or "with suffix" in etymology
            or etymology.startswith("Ellipsis of ")
        )
        if structural:
            blocked.add(row.rank)
    return blocked


def validate_decisions(
    rows: list[H.SweepRow],
    entries: dict[int, H.BranchEntry],
    raw_entries: dict[int, dict],
    decisions: list[H.Decision],
    ranked_by_rank: dict[int, tuple[tuple[str, float], ...]],
    sense_map: dict[str, list[dict]],
) -> None:
    if set(VERDICTS) != set(EXPECTED_RANKS):
        raise AssertionError("جدول الأحكام لا يغطي الرتب السبعين")
    exact = {
        row.rank for row in rows
        if direct_from_plus(raw_entries[row.rank]["etymology"])
    }
    if exact != EXACT_DECOMPOSITIONS:
        raise AssertionError(f"تغيرت أسطر From X + Y المباشرة: {sorted(exact)}")
    blocked = detected_blocked_boundaries(rows, raw_entries)
    if blocked != set(BLOCKED_BOUNDARIES):
        raise AssertionError(f"تغيرت حدود المركب غير المؤهلة: {sorted(blocked)}")
    compound_ranks = {
        row.rank for row, decision in zip(rows, decisions)
        if decision.verdict == "COMPOUND-BOUNDARY"
    }
    if compound_ranks != exact | blocked:
        raise AssertionError("أحكام المركب لا تطابق التفكيك الحصري والحدود")
    for row, decision in zip(rows, decisions):
        candidates = {candidate for candidate, _ in ranked_by_rank[row.rank]}
        if (
            decision.candidate not in row.candidates_found
            or decision.candidate not in candidates
        ):
            raise AssertionError(f"مرشح الرتبة {row.rank} خارج المروحة الكاملة")
        complete = H.route_complete(row, decision.candidate)
        _, coverage, _ = classical_witnesses(decision.candidate, sense_map, 60)
        if decision.verdict == "LAW-GAP" and complete:
            raise AssertionError(f"LAW-GAP بلا صف مفقود في الرتبة {row.rank}")
        if decision.verdict == "OPEN-CANDIDATE" and not complete:
            raise AssertionError(f"OPEN-CANDIDATE بمسار ناقص في الرتبة {row.rank}")
        if decision.verdict == "ROOT-TRACE":
            if not complete:
                raise AssertionError(f"ROOT-TRACE بلا مسار مكتمل في الرتبة {row.rank}")
            if coverage < 2:
                raise AssertionError(f"ROOT-TRACE بلا شاهدين في الرتبة {row.rank}")
    for rank in EXACT_DECOMPOSITIONS:
        decomposition_line(
            next(row for row in rows if row.rank == rank), raw_entries[rank]
        )


def validate_text(rows: list[H.SweepRow], texts: list[str]) -> None:
    if len(rows) != 70 or len(texts) != 70:
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = [
        int(value) for value in re.findall(
            r"^### WO-B-R24-BOTH-(\d{5}):", joined, re.MULTILINE
        )
    ]
    if headings != list(EXPECTED_RANKS):
        raise AssertionError("معرفات الرتب لا تطابق النافذة")
    if "—" in joined or re.search(r"[۰-۹٠-٩]", joined):
        raise AssertionError("دخلت شرطة طويلة أو أرقام غير غربية")
    if unicodedata.normalize("NFC", joined) != joined:
        raise AssertionError("النص الجديد ليس NFC")
    required = (
        "نموذج WO-B-PROBE-001", "قراءة مداخل الرسم المتجانس",
        "المروحة المرتبة الكاملة", "الحدث من السجل المجمد",
        "الشاهد 1", "الشاهد 2", "الحكم (استكشاف)",
    )
    for row, card in zip(rows, texts):
        if len(card.encode("utf-8")) >= CARD_LIMIT:
            raise AssertionError(f"تجاوزت الرتبة {row.rank} حد 5KB")
        if any(field not in card for field in required):
            raise AssertionError(f"نقص حقل من بطاقة الرتبة {row.rank}")
    for rank in EXACT_DECOMPOSITIONS:
        card = texts[list(EXPECTED_RANKS).index(rank)]
        if "تفكيك Kaikki الحصري" not in card or "قراءة المكونات المستقلة" not in card:
            raise AssertionError(f"لم تقرأ مكونات الرتبة {rank} استقلالا")
    for rank in BLOCKED_BOUNDARIES:
        card = texts[list(EXPECTED_RANKS).index(rank)]
        if "حد المركب غير المفكك" not in card or "بلا مكونات مخترعة" not in card:
            raise AssertionError(f"لم يغلق حد المركب في الرتبة {rank}")


def report_section(
    rows: list[H.SweepRow],
    decisions: list[H.Decision],
    sizes: list[int],
    skipped: int,
    fresh_count: int,
) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    lines = [f"<!-- {MARKER}:START -->", ""]
    for batch in range(2):
        lo = batch * BATCH_SIZE
        hi = lo + BATCH_SIZE
        batch_rows = rows[lo:hi]
        counts = Counter(decision.verdict for decision in decisions[lo:hi])
        distribution = "؛ ".join(
            f"{key}={counts[key]}" for key in sorted(counts)
        )
        lines.extend([
            f"## الجولة الرابعة والعشرون، دفعة حوض both رقم {batch + 1}", "",
            f"- الوقت: {now}، Africa/Cairo.",
            "- فُحص ورُشح قبل القراءة: 35؛ كُتب: 35؛ الترتيب overlap نازلا مع ثبات ترتيب المصدر عند التعادل.",
            (
                f"- الرتب: من {batch_rows[0].rank:05d} إلى {batch_rows[-1].rank:05d} "
                "داخل الحوض المضاعف، مع تجاوز المقروء والتكرار المفحوص."
            ),
            f"- توزيع الأحكام: {distribution}.",
            "- المروحة: وُلدت كاملة ورُتبت بالأوزان لكل عضو، ومُسحت مواد جميع مرشحيها بلا قص للحقل المصدر.",
            "- المتجانسات: قُرئت كل مداخل الرسم، وسُجل العدد ورقم المدخلة المختارة في كل بطاقة.",
            "- المصادر: نُقل شاهدان دلاليان مستقلان لكل ROOT-TRACE، وسُميت الفجوة حيث نقصا.",
            "- التفكيك: لم يقبل إلا سطر From X + Y المباشر من Kaikki الخام؛ قُرئ كل مكون مقبول وحده، وما عداه COMPOUND-BOUNDARY.",
            "- التحقق البنيوي: 35 معرفا فريدا؛ لا بطاقة فوق 5KB؛ لا شرطة طويلة؛ الأرقام غربية والنص NFC.",
            f"- آخر موضع في الدفعة: الرتبة {batch_rows[-1].rank:05d}، `{batch_rows[-1].branch}`.",
            "",
        ])
    total = Counter(decision.verdict for decision in decisions)
    distribution = "؛ ".join(f"{key}={total[key]}" for key in sorted(total))
    traces = [
        f"`{row.branch}↔{decision.candidate}`"
        for row, decision in zip(rows, decisions)
        if decision.verdict in {"ROOT-TRACE", "NUCLEUS-TRACE"}
    ]
    max_size = max(sizes)
    max_rank = rows[sizes.index(max_size)].rank
    exact_text = " و".join(f"{rank:05d}" for rank in sorted(EXACT_DECOMPOSITIONS))
    blocked_text = " و".join(f"{rank:05d}" for rank in sorted(BLOCKED_BOUNDARIES))
    lines.extend([
        "## حصيلة الجولة الرابعة والعشرين", "",
        (
            f"- حمل `persian.md` مرة واحدة في الذاكرة؛ المقروء المتجاوز في حوض both={skipped}؛ "
            f"الطازج قبل القطع={fresh_count}."
        ),
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- صلات الجذر الموجبة: " + "، ".join(traces) + ".",
        f"- التفكيك الحصري: الرتب {exact_text} فقط؛ قُرئت مكوناتها الثمانية استقلالا من Kaikki ومراوحها.",
        f"- حدود مركب بلا تفكيك مؤهل: الرتب {blocked_text}؛ لم تقبل صيغة تحليل سطحي أو مكافأة أو تركيب غير مباشر.",
        "- فجوة المكون الدلالية: `خشک↔خشك` بقي SOURCE-GAP داخل تفكيك الرتبة 00407؛ لم يورث المركب حكمه.",
        "- انضباط القانون: `گسی↔قصو` و`چرت↔شرط` بقيتا LAW-GAP مع حضور المعنى لغياب الصف الصوتي المسمى؛ `گاف↔كاف` بقي OPEN-CANDIDATE لاختلاف الحرفين.",
        f"- أكبر بطاقة: {max_size} بايت، الرتبة {max_rank:05d}؛ كل البطاقات دون 5KB.",
        "- عطب أداة أساسية: 0؛ لم تُفعّل طبقة البرهان، ولم يُبن ملف مشترك، ولم يقع ship، ولم يستعمل git.",
        "", f"<!-- {MARKER}:END -->", "", "LANE-B DONE24 70 00444",
    ])
    return "\n".join(lines)


def validate_existing(reading_text: str, report_text: str) -> None:
    match = re.search(
        rf"<!-- {re.escape(MARKER)}:START -->(.*?)<!-- {re.escape(MARKER)}:END -->",
        reading_text,
        re.DOTALL,
    )
    if not match:
        raise AssertionError("محضر الجولة موجود وبطاقاتها غائبة")
    ranks = [
        int(value) for value in re.findall(
            r"^### WO-B-R24-BOTH-(\d{5}):", match.group(1), re.MULTILINE
        )
    ]
    if ranks != list(EXPECTED_RANKS):
        raise AssertionError("مقطع الجولة 24 الموجود غير مكتمل")
    if not report_text.rstrip().endswith("LANE-B DONE24 70 00444"):
        raise AssertionError("سطر DONE24 ليس خاتمة التقرير")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    reading_text = READING.read_text(encoding="utf-8")
    report_text = REPORT.read_text(encoding="utf-8")
    if MARKER in reading_text or MARKER in report_text:
        validate_existing(reading_text, report_text)
        print("ROUND24 ALREADY PRESENT AND VALID")
        print("LANE-B DONE24 70 00444")
        return 0

    all_rows = H.parse_sweep(json.loads(SWEEP.read_text(encoding="utf-8")))
    rows, skipped, fresh_count = select_fresh(all_rows, reading_text)
    lexicon = json.loads(LEXICON.read_text(encoding="utf-8"))
    entries, grouped = select_branch_entries(rows, lexicon)
    raw_entries = load_raw_entries(rows, entries)
    validate_component_inventory(grouped)

    ranked_by_rank = {row.rank: H.full_ranked_fan(row) for row in rows}
    roots = {
        candidate
        for row in rows
        for candidate, _ in ranked_by_rank[row.rank]
    }
    roots.update(candidate_for(row) for row in rows)
    sense_map = H.SENSES.matches_for_roots(
        H.SENSES.DEFAULT_RESOURCES, roots, None
    )
    decisions = [decide(row) for row in rows]
    validate_decisions(
        rows, entries, raw_entries, decisions, ranked_by_rank, sense_map
    )
    texts = [
        fit_card(
            row, entries[row.rank], raw_entries[row.rank], decision,
            ranked_by_rank[row.rank], sense_map,
        )
        for row, decision in zip(rows, decisions)
    ]
    validate_text(rows, texts)
    sizes = [len(card.encode("utf-8")) + 1 for card in texts]

    reading_append = (
        f"\n\n<!-- {MARKER}:START -->\n\n"
        "## الجولة الرابعة والعشرون: حوض both الفارسي المضاعف (2026-08-24)\n\n"
        "- النطاق: السبعون الطازجة التالية بعد WO-B-OPEN-COMP-00343 وتجاوز المقروء والتكرار؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ المركب لا يفكك إلا بسطر Kaikki المباشر `From X + Y`، وكل مكون مقبول يقرأ وحده.\n\n"
        + "\n".join(texts[:BATCH_SIZE])
        + f"\n## الدفعة الثانية: الرتب {rows[BATCH_SIZE].rank:05d} إلى {rows[-1].rank:05d} بعد تجاوز المقروء\n\n"
        + "\n".join(texts[BATCH_SIZE:])
        + f"\n<!-- {MARKER}:END -->\n"
    )
    report_append = "\n" + report_section(
        rows, decisions, sizes, skipped, fresh_count
    ) + "\n"
    reading_append = unicodedata.normalize("NFC", reading_append)
    report_append = unicodedata.normalize("NFC", report_append)
    combined_reading = reading_text + reading_append
    combined_report = report_text + report_append
    if "—" in reading_append + report_append or re.search(
        r"[۰-۹٠-٩]", reading_append + report_append
    ):
        raise AssertionError("فشل حارس الشرطة أو الأرقام قبل الكتابة")
    validate_existing(combined_reading, combined_report)

    counts = Counter(decision.verdict for decision in decisions)
    print("ROUND24 READY")
    print("SKIPPED", skipped, "FRESH", fresh_count, "SELECTED", len(rows))
    print("RANKS", rows[0].rank, rows[-1].rank, "BATCHES", BATCH_SIZE, BATCH_SIZE)
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("EXACT_FROM_PLUS", " ".join(f"{rank:05d}" for rank in sorted(EXACT_DECOMPOSITIONS)))
    print("BLOCKED_BOUNDARIES", len(BLOCKED_BOUNDARIES))
    print("MAX_CARD", max(sizes), f"RANK={rows[sizes.index(max(sizes))].rank:05d}")
    if args.preview:
        print("PREVIEW ONLY")
        return 0

    with READING.open("a", encoding="utf-8", newline="") as handle:
        handle.write(reading_append)
    with REPORT.open("a", encoding="utf-8", newline="") as handle:
        handle.write(report_append)
    print("ROUND24 WRITTEN")
    print("LANE-B DONE24 70 00444")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
