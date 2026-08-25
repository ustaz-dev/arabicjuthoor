# -*- coding: utf-8 -*-
"""المسار B، الجولة 25: إغلاق both ثم بدء sound_only في دفعتين."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import harvest_persian_round24 as P  # noqa: E402

H = P.H
READING = ROOT / "04-cross-linguistic" / "readings" / "persian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-B.md"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-persian.json"
LEXICON = ROOT / "data" / "branch-lexicons" / "persian.json"
RAW_LEXICON = ROOT / "Resources" / "persian" / "kaikki.org-dictionary-Persian.jsonl"
MARKER = "LANE-B-PERSIAN-ROUND25-2026-08-25"
CARD_LIMIT = 5120

BOTH_RANKS = (
    446, 447, 448, 451, 452, 454, 455, 456, 457, 458,
    459, 460, 461, 463, 465, 466, 467, 468, 469, 471,
    472, 474, 475, 476, 477, 478, 479, 481, 482, 483,
    484, 486, 487, 488, 489, 490, 492, 493, 494,
)
SOUND_RANKS = tuple(range(1, 32))
BATCH_SIZES = (len(BOTH_RANKS), len(SOUND_RANKS))
DONE_LINE = "LANE-B DONE25 70 WO-B-R25-SOUND-00031"

CANDIDATE_OVERRIDES = {
    "B00446": "زاغ", "B00447": "بس", "B00451": "شل",
    "B00452": "بر", "B00454": "كث", "B00457": "مر",
    "B00458": "بوق", "B00461": "بر", "B00463": "جور",
    "B00465": "بال", "B00466": "وش", "B00471": "يوز",
    "B00472": "هر", "B00474": "بر", "B00476": "ار",
    "B00477": "لج", "B00479": "جاء", "B00481": "جوز",
    "B00483": "بوش", "B00487": "بيد", "B00488": "دد",
    "B00492": "تل", "B00493": "صف", "B00494": "وار",
    "S00002": "شرق", "S00003": "نام", "S00004": "جسم",
    "S00005": "جسم", "S00013": "فرس", "S00014": "فرس",
    "S00015": "فرس", "S00016": "كس", "S00017": "رنج",
    "S00019": "نه", "S00022": "با", "S00023": "با",
    "S00028": "كير",
}

EXPECTED_ENTRY_INDEX = {
    "B00446": 4223, "B00447": 4454, "B00448": 4518,
    "B00451": 4575, "B00452": 4653, "B00454": 5420,
    "B00455": 5642, "B00456": 5655, "B00457": 5967,
    "B00458": 6254, "B00459": 6458, "B00460": 6491,
    "B00461": 6565, "B00463": 6612, "B00465": 6725,
    "B00466": 7334, "B00467": 7513, "B00468": 7710,
    "B00469": 8059, "B00471": 8341, "B00472": 8388,
    "B00474": 9888, "B00475": 10300, "B00476": 10307,
    "B00477": 10383, "B00478": 10394, "B00479": 10521,
    "B00481": 10849, "B00482": 10959, "B00483": 11118,
    "B00484": 11170, "B00486": 13602, "B00487": 13859,
    "B00488": 14362, "B00489": 14755, "B00490": 14790,
    "B00492": 15465, "B00493": 15705, "B00494": 16060,
    "S00001": 13, "S00002": 23, "S00003": 44, "S00004": 52,
    "S00005": 53, "S00006": 67, "S00007": 70, "S00008": 82,
    "S00009": 107, "S00010": 108, "S00011": 118,
    "S00012": 119, "S00013": 129, "S00014": 130,
    "S00015": 131, "S00016": 132, "S00017": 137,
    "S00018": 140, "S00019": 147, "S00020": 149,
    "S00021": 150, "S00022": 156, "S00023": 157,
    "S00024": 158, "S00025": 168, "S00026": 178,
    "S00027": 179, "S00028": 180, "S00029": 185,
    "S00030": 186, "S00031": 192,
}

EXPECTED_RAW_LINE = {
    "B00446": 4712, "B00447": 4961, "B00448": 5027,
    "B00451": 5090, "B00452": 5171, "B00454": 6372,
    "B00455": 6636, "B00456": 6652, "B00457": 6990,
    "B00458": 7337, "B00459": 7570, "B00460": 7604,
    "B00461": 7705, "B00463": 7762, "B00465": 7887,
    "B00466": 8607, "B00467": 8808, "B00468": 9022,
    "B00469": 9427, "B00471": 9785, "B00472": 9844,
    "B00474": 12181, "B00475": 12672, "B00476": 12680,
    "B00477": 12769, "B00478": 12780, "B00479": 12979,
    "B00481": 13348, "B00482": 13470, "B00483": 13664,
    "B00484": 13730, "B00486": 16447, "B00487": 16723,
    "B00488": 17252, "B00489": 17675, "B00490": 17714,
    "B00492": 18441, "B00493": 18703, "B00494": 19121,
    "S00001": 15, "S00002": 25, "S00003": 47, "S00004": 55,
    "S00005": 56, "S00006": 70, "S00007": 73, "S00008": 85,
    "S00009": 111, "S00010": 112, "S00011": 124,
    "S00012": 125, "S00013": 135, "S00014": 136,
    "S00015": 137, "S00016": 138, "S00017": 143,
    "S00018": 146, "S00019": 153, "S00020": 155,
    "S00021": 156, "S00022": 162, "S00023": 163,
    "S00024": 164, "S00025": 174, "S00026": 184,
    "S00027": 185, "S00028": 186, "S00029": 192,
    "S00030": 193, "S00031": 199,
}

EXACT_DECOMPOSITIONS = {"B00455", "B00469", "B00482", "B00493"}
BLOCKED_BOUNDARIES = {
    "B00452": "قال Kaikki: By surface analysis ثم X + Y + Z، لا سطر From X + Y نهائي مباشر.",
    "B00483": "قال Kaikki: By surface analysis ثم X + Y، بعد نسب موروث مستقل؛ لا سطر From X + Y نهائي مباشر.",
    "S00006": "قال Kaikki: Equivalent to X + Y، لا سطر From X + Y مباشر.",
    "S00013": "قال Kaikki: By surface analysis ثم X + Y، لا سطر From X + Y مباشر.",
    "S00014": "قال Kaikki: By surface analysis ثم X + Y، لا سطر From X + Y مباشر.",
    "S00015": "قال Kaikki: By surface analysis ثم X + Y، لا سطر From X + Y مباشر.",
    "S00025": "قال Kaikki: equivalent to X + Y داخل خبر صورة موروثة، لا سطر From X + Y مباشر.",
}
MORPHOLOGY_KEYS = {
    "B00467", "B00475", "B00476", "B00489", "B00490", "B00494",
    "S00010", "S00023",
}
SOURCE_GAP_KEYS = {"B00446"}

COMPONENT_READINGS = {
    "B00455": (
        "`گاه`، قُرئت مداخلها 2118-2120 واختيرت 2118 لمعنى الوقت؛ "
        "مروحتها ذات 72 مرشحا كاملة، و`گاه↔جاه`: OPEN-CANDIDATE. "
        "`ـی`، قُرئت مداخلها 6327-6330 واختيرت 6327 لعلامة التنكير؛ "
        "مروحتها صفر: MORPHOLOGY-GAP."
    ),
    "B00469": (
        "`پای`، اختير سطرها 4626 المحيل إلى `پا` للرجل والقدم؛ مروحتها "
        "صفر، ومرجع `پا` في الجولة 24: OPEN-CANDIDATE. `ـگاه`، المدخلة "
        "7461 والسطر 8752، لاحقة مكان وزمان؛ مروحتها ذات 72 مرشحا: MORPHOLOGY-GAP."
    ),
    "B00482": (
        "`پوک`، المدخلة 5559 والسطر 6534، للشيء الأجوف؛ قُرئت مروحته "
        "ذات 40 مرشحا كاملة، و`پوک↔بك`: OPEN-CANDIDATE بلا مدار دلالي. "
        "`ـی`، المدخلة 6329 والسطر 7422 لصنع الاسم المجرد؛ مروحتها "
        "صفر: MORPHOLOGY-GAP."
    ),
    "B00493": (
        "`چپ`، قُرئت مداخلها 3068-3070 واختيرت 3068 لمعنى اليسار؛ "
        "مروحتها ذات 60 مرشحا كاملة، و`چپ↔صف`: LAW-GAP لغياب "
        "چ↔ص وپ↔ف. `ـه`، قُرئت مداخلها 7112-7114 واختيرت 7112 "
        "لاحقة اسمية؛ مروحتها صفر: MORPHOLOGY-GAP."
    ),
}

SPECIAL_ORBITS = {
    "B00446": (
        "الفرع يسمي طائر الزاغ، والصورة العربية المرشحة `زاغ` مطابقة، "
        "لكن موارد المعاني المسماة لم تعط شاهدا عربيا كلاسيكيا مستقلا؛ "
        "سُميت فجوة المصدر ولم يُصدر حكم موجب."
    ),
    "B00454": (
        "الفرع يسمي الكبير والعظيم، ومادة `كث` العربية تبلغ الكثاثة "
        "والكثرة الوصفية، لكن ت↔ث غير مسمى؛ وقف الحكم عند فجوة القانون."
    ),
    "B00471": (
        "الفرع يسمي الفهد الصياد، والمرشح `يوز` لم يعط في المورد "
        "الكلاسيكي إلا اسم سكة ببلخ، كما أن ی↔و غير مسمى؛ لا حكم نقل."
    ),
    "B00488": (
        "الفرع يسمي الوحش والحيوان البري، أما `دد` في الشواهد العربية "
        "فيسمي اللهو واللعب؛ اتحد الرسم وافترق المعنى."
    ),
    "S00002": (
        "خبر الأصل يسمي انتقال اللفظ الإيراني إلى العربية في صورة `سراج`، "
        "لكن `سراج` خارج المروحة الحالية، ومسار `چراغ↔شرق` ناقص؛ لم "
        "يُستعمل خبر الأصل لإصدار حكم خارج الحوض."
    ),
    "S00011": (
        "الفرع يسمي النفس والبخار، و`دم` العربية في الشواهد المسماة دم "
        "الجسد؛ اتحاد الرسم لا يوحد المدخلتين."
    ),
    "S00012": (
        "الفرع يسمي الحد والنصل، و`دم` العربية في الشواهد المسماة دم "
        "الجسد؛ فُصل هذا المتجانس عن مدخلة النفس وعن العربية."
    ),
    "S00028": (
        "الفرع يسمي العضو الجنسي، و`كير` العربية تسمي زق الحداد الذي "
        "ينفخ فيه؛ الصورة واحدة والمدار مختلف."
    ),
}


@dataclass(frozen=True)
class SelectedRow:
    pool: str
    row: H.SweepRow

    @property
    def key(self) -> str:
        return f"{self.pool}{self.row.rank:05d}"

    @property
    def pool_label(self) -> str:
        return "BOTH" if self.pool == "B" else "SOUND"

    @property
    def heading(self) -> str:
        return f"WO-B-R25-{self.pool_label}-{self.row.rank:05d}"


def sound_row(rank: int, raw: dict) -> H.SweepRow:
    return H.SweepRow(
        rank=rank,
        branch=H.clean(raw["branch"]),
        say=H.clean(raw["say"]),
        skeleton=tuple(H.clean(raw["skeleton"])),
        gloss=H.clean(raw["gloss"]),
        candidates_found=tuple(H.clean(value) for value in raw["candidates_found"]),
        best=H.clean(raw["best"]),
        overlap=0,
        shared=(),
    )


def pair_key(row: H.SweepRow) -> tuple[str, str]:
    return row.branch, H.norm_gloss(row.gloss)


def pair_was_read(row: H.SweepRow, pairs: set[tuple[str, str]]) -> bool:
    gloss = H.norm_gloss(row.gloss)
    return any(
        word == row.branch
        and (gloss == prior or gloss.startswith(prior) or prior.startswith(gloss))
        for word, prior in pairs
    )


def select_rows(data: dict, reading_text: str) -> tuple[list[SelectedRow], dict]:
    pairs = H.read_pairs(reading_text)
    both_rows = H.parse_sweep(data)
    id_read = {
        int(value)
        for value in re.findall(
            r"^### WO-B-R(?:21|22|23|24)-BOTH-(\d{5}):",
            reading_text,
            re.MULTILINE,
        )
    }
    prior_read = {
        row.rank for row in both_rows if H.already_read(row, pairs)
    } | id_read
    fresh_both = [row for row in both_rows if row.rank not in prior_read]
    fresh_both.sort(key=lambda row: (-row.overlap, row.rank))
    deduped_both: list[H.SweepRow] = []
    seen: set[tuple[str, str]] = set()
    internal_duplicates: list[int] = []
    for row in fresh_both:
        key = pair_key(row)
        if key in seen:
            internal_duplicates.append(row.rank)
            continue
        seen.add(key)
        deduped_both.append(row)

    all_sound = [
        sound_row(rank, raw)
        for rank, raw in enumerate(data.get("sound_only") or [], 1)
    ]
    prior_sound = {row.rank for row in all_sound if pair_was_read(row, pairs)}
    fresh_sound: list[H.SweepRow] = []
    sound_seen: set[tuple[str, str]] = set()
    for row in all_sound:
        key = pair_key(row)
        if row.rank in prior_sound or key in sound_seen:
            continue
        sound_seen.add(key)
        fresh_sound.append(row)
        if len(fresh_sound) == len(SOUND_RANKS):
            break

    if len(both_rows) != 494 or len(all_sound) != 2304:
        raise AssertionError("تغير حجم أحد حوضي المسح الفارسي")
    if len(prior_read) != 454 or len(fresh_both) != 40:
        raise AssertionError(
            f"تغير استئناف both: مقروء={len(prior_read)}، طازج={len(fresh_both)}"
        )
    if internal_duplicates != [462]:
        raise AssertionError(f"تغير تكرار both الداخلي: {internal_duplicates}")
    if tuple(row.rank for row in deduped_both) != BOTH_RANKS:
        raise AssertionError("تغير ترتيب بقية both بعد فحص التكرار")
    if tuple(row.rank for row in fresh_sound) != SOUND_RANKS:
        raise AssertionError("تغير بدء sound_only بعد فحص التكرار")
    selected = (
        [SelectedRow("B", row) for row in deduped_both]
        + [SelectedRow("S", row) for row in fresh_sound]
    )
    stats = {
        "pair_count": len(pairs),
        "both_prior": len(prior_read),
        "both_raw_fresh": len(fresh_both),
        "both_internal_duplicates": internal_duplicates,
        "sound_prior": len(prior_sound),
    }
    return selected, stats


def select_branch_entries(
    selected: list[SelectedRow], lexicon: dict
) -> tuple[dict[str, H.BranchEntry], dict[str, list[tuple[int, dict]]]]:
    grouped: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for index, entry in enumerate(lexicon["entries"]):
        grouped[H.clean(entry.get("word") or "")].append((index, entry))
    entries: dict[str, H.BranchEntry] = {}
    for item in selected:
        row = item.row
        options = grouped.get(row.branch, [])
        if not options:
            raise AssertionError(f"لا مدخلة فرع للرسم {row.branch}")
        global_index, entry = max(
            options,
            key=lambda pair: H.entry_score(H.norm_gloss(row.gloss), pair[1]),
        )
        homograph_index = 1 + next(
            i for i, pair in enumerate(options) if pair[0] == global_index
        )
        entries[item.key] = H.BranchEntry(
            global_index=global_index,
            homograph_index=homograph_index,
            homograph_count=len(options),
            word=H.clean(entry.get("word") or ""),
            reading=H.clean(entry.get("read") or row.say),
            pos=H.clean(entry.get("pos") or ""),
            gloss=H.clean(entry.get("en") or ""),
            etymology=H.clean(entry.get("etym") or "فجوة اشتقاق في لقطة الفرع."),
        )
        if global_index != EXPECTED_ENTRY_INDEX[item.key]:
            raise AssertionError(
                f"انزلقت مدخلة {item.key}: {global_index}"
            )
    return entries, grouped


def raw_gloss(entry: dict) -> str:
    return H.clean("; ".join(
        str(value)
        for sense in entry.get("senses") or []
        for value in sense.get("glosses") or []
    ))


def load_raw_entries(
    selected: list[SelectedRow], entries: dict[str, H.BranchEntry]
) -> dict[str, dict]:
    wanted = {item.row.branch for item in selected}
    grouped: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    with RAW_LEXICON.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            raw = json.loads(line)
            word = H.clean(raw.get("word") or "")
            if word in wanted:
                grouped[word].append((line_number, raw))
    output: dict[str, dict] = {}
    for item in selected:
        entry = entries[item.key]
        options = grouped.get(item.row.branch, [])
        same_pos = [
            pair for pair in options
            if H.clean(pair[1].get("pos") or "") == entry.pos
        ]
        if not options:
            raise AssertionError(f"غابت مدخلة Kaikki الخام لـ{item.key}")
        line_number, raw = max(
            same_pos or options,
            key=lambda pair: H.entry_score(
                H.norm_gloss(entry.gloss), {"en": raw_gloss(pair[1])}
            ),
        )
        output[item.key] = {
            "line": line_number,
            "entry": raw,
            "gloss": raw_gloss(raw),
            "etymology": H.clean(raw.get("etymology_text") or ""),
        }
        if line_number != EXPECTED_RAW_LINE[item.key]:
            raise AssertionError(
                f"انزلقت مدخلة Kaikki الخام لـ{item.key}: {line_number}"
            )
    return output


def direct_from_plus(etymology: str) -> tuple[str, str] | None:
    """يلتقط فقط خبر Kaikki النهائي المباشر From X + Y، مع أو بلا نقطة."""
    matches = list(re.finditer(r"(?:^|\s)From (.+?) \+ (.+?)(?:\.|$)", etymology))
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


def validate_components(grouped: dict[str, list[tuple[int, dict]]]) -> None:
    expected_indices = {
        "گاه": {2118, 2119, 2120}, "ـی": {6327, 6328, 6329, 6330},
        "پای": {4144}, "ـگاه": {7461}, "پوک": {5559},
        "چپ": {3068, 3069, 3070}, "ـه": {7112, 7113, 7114},
    }
    for word, expected in expected_indices.items():
        actual = {index for index, _entry in grouped.get(word, [])}
        if actual != expected:
            raise AssertionError(f"تغير جرد مكون {word}: {sorted(actual)}")
    fan_counts = {
        "گاه": 72, "ـی": 0, "پای": 0, "ـگاه": 72,
        "پوک": 40, "چپ": 60, "ـه": 0,
    }
    for word, expected in fan_counts.items():
        fan = tuple(H.FAN.rank(word, H.FAN.fan(word, "persian"), "persian"))
        if len(fan) != expected:
            raise AssertionError(f"تغيرت مروحة المكون {word}: {len(fan)}")


def candidate_for(item: SelectedRow) -> str:
    return CANDIDATE_OVERRIDES.get(item.key, item.row.best)


def verdict_for(item: SelectedRow, candidate: str) -> str:
    if item.key in EXACT_DECOMPOSITIONS | set(BLOCKED_BOUNDARIES):
        return "COMPOUND-BOUNDARY"
    if item.key in MORPHOLOGY_KEYS:
        return "MORPHOLOGY-GAP"
    if item.key in SOURCE_GAP_KEYS:
        return "SOURCE-GAP"
    return "OPEN-CANDIDATE" if H.route_complete(item.row, candidate) else "LAW-GAP"


def decide(item: SelectedRow) -> H.Decision:
    candidate = candidate_for(item)
    verdict = verdict_for(item, candidate)
    if item.key in SPECIAL_ORBITS:
        orbit = SPECIAL_ORBITS[item.key]
    elif verdict == "COMPOUND-BOUNDARY":
        if item.key in EXACT_DECOMPOSITIONS:
            orbit = (
                "قاموس Kaikki أعطى سطر From X + Y النهائي المباشر؛ قُرئ "
                "كل مكون وحده، ولم ترث الصورة المجموعة حكم أي مكون."
            )
        else:
            orbit = (
                "ظهر تركيب متعدد الأجزاء في خبر الأصل بصيغة تحليل سطحي "
                "أو مكافأة، لا بسطر From X + Y النهائي المباشر؛ وقف الحكم عند الحد."
            )
    elif verdict == "MORPHOLOGY-GAP":
        orbit = (
            "العضو أداة أو لاحقة صرفية لا مادة معجمية عربية مقابلة؛ لا "
            "يحول التداخل الآلي الوظيفة النحوية إلى جذر."
        )
    else:
        orbit = (
            f"الفرع يسمي «{item.row.gloss}»؛ وبعد قراءة مادة `{candidate}` "
            "وشواهدها لم تثبت نقطة معنى مباشرة، فلا يصنع الرصف الصوتي وحده مدارا."
        )
    if verdict == "LAW-GAP":
        obstacle = "رجل الصوت غير مكتملة بصف مسمى؛ لم يصدر حكم موجب."
    elif verdict == "SOURCE-GAP":
        obstacle = "لم يرد شاهد عربي كلاسيكي مستقل في الموارد المسماة؛ الغياب لا ينفي اللسان."
    elif verdict == "COMPOUND-BOUNDARY":
        obstacle = "الحكم وقف عند حد المركب؛ لم تورث الصورة المجموعة حكم مكون."
    elif verdict == "MORPHOLOGY-GAP":
        obstacle = "المقارنة المعجمية لا تسند معنى جذريا إلى أداة أو لاحقة صرفية."
    else:
        obstacle = "الصوت قابل للرصف، لكن رجل المعنى المباشر لم تثبت بعد قراءة الشاهدين والمتجانسات."
    return H.Decision(candidate, verdict, H.state_for(verdict), orbit, obstacle)


def decomposition_lines(item: SelectedRow, raw: dict) -> list[str]:
    decomposition = direct_from_plus(raw["etymology"])
    if item.key not in EXACT_DECOMPOSITIONS:
        return []
    if not decomposition:
        raise AssertionError(f"غاب تفكيك From X + Y لـ{item.key}")
    return [
        (
            f"- تفكيك Kaikki الحصري من السطر الخام {raw['line']}: "
            f"«{H.clip(raw['etymology'], 420)}»."
        ),
        f"- قراءة المكونات المستقلة: {COMPONENT_READINGS[item.key]}",
        "- الخطوة صفر: قبل التفكيك الحرفي From X + Y لم تقارن الصورة وحدة جذرية؛ قُرئ كل مكون وحده.",
    ]


def make_card(
    item: SelectedRow,
    entry: H.BranchEntry,
    raw: dict,
    decision: H.Decision,
    ranked: tuple[tuple[str, float], ...],
    sense_map: dict[str, list[dict]],
    quote_limit: int,
    etym_limit: int,
) -> str:
    match_count, classical_count, witnesses = P.classical_witnesses(
        decision.candidate, sense_map, quote_limit
    )
    row = item.row
    pool_key = "both" if item.pool == "B" else "sound_only"
    pool_note = (
        f"overlap={row.overlap}؛ shared={','.join(row.shared)}"
        if item.pool == "B"
        else "overlap=0؛ shared=فارغ؛ مادة الصوت وحده تنتظر القياس الدلالي ولا ترفض"
    )
    etymology = raw["etymology"] or entry.etymology or "فجوة اشتقاق في مدخلة Kaikki الخام."
    lines = [
        f"### {item.heading}: `{row.branch}` /{entry.reading}/، رتبة {pool_key} {row.rank}",
        "- إصدار البروتوكول: RECOVERY-v2 (2026-08-16)؛ نموذج WO-B-PROBE-001.",
        (
            f"- مرجع الحوض: `phonetic-sweep-persian.json:{pool_key}[{row.rank - 1}]`؛ "
            f"{pool_note}؛ الترتيب مدخل قراءة لا قرينة حكم."
        ),
        f"- الكلمة في الفرع: فارسية `{row.branch}` /{entry.reading}/؛ الصنف `{entry.pos}`.",
        (
            f"- قراءة مداخل الرسم المتجانس: قُرئت {entry.homograph_count} مدخلة "
            f"للرسم `{row.branch}`؛ المختارة المدخلة {entry.homograph_index}، "
            f"entries[{entry.global_index}]؛ لم تؤخذ الأولى آليا."
        ),
        (
            f"- أقدم صورة مستعادة: «{H.clip(etymology, etym_limit)}» "
            f"[Kaikki؛ السطر الخام {raw['line']}]."
        ),
    ]
    exact_lines = decomposition_lines(item, raw)
    if exact_lines:
        lines.extend(exact_lines)
    elif item.key in BLOCKED_BOUNDARIES:
        lines.extend([
            f"- حد المركب غير المفكك: {BLOCKED_BOUNDARIES[item.key]}",
            "- الخطوة صفر: لم يقبل تحليل سطحي أو مكافأة أو اشتقاق غير مباشر؛ وقف الحكم COMPOUND-BOUNDARY بلا مكونات مخترعة.",
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
        f"- ملاحظات العدستين: استرداد حتى القرار، وتشكيك مقصور على العضو؛ الجولة 25، الموضع {item.key}.",
        f"- حالة الإغلاق: {decision.state}.",
        f"- الحكم (استكشاف): {decision.verdict}.",
    ])
    return "\n".join(lines) + "\n"


def fit_card(
    item: SelectedRow,
    entry: H.BranchEntry,
    raw: dict,
    decision: H.Decision,
    ranked: tuple[tuple[str, float], ...],
    sense_map: dict[str, list[dict]],
) -> str:
    for quote_limit, etym_limit in (
        (230, 340), (180, 280), (130, 210), (90, 150),
        (60, 105), (35, 70), (20, 45), (12, 25), (8, 15),
    ):
        card = make_card(
            item, entry, raw, decision, ranked, sense_map,
            quote_limit, etym_limit,
        )
        if len(card.encode("utf-8")) < CARD_LIMIT:
            return card
    raise AssertionError(f"تجاوزت بطاقة {item.key} حد 5KB")


def validate_decisions(
    selected: list[SelectedRow],
    raw_entries: dict[str, dict],
    decisions: list[H.Decision],
    ranked_by_key: dict[str, tuple[tuple[str, float], ...]],
    sense_map: dict[str, list[dict]],
) -> None:
    exact = {
        item.key for item in selected
        if direct_from_plus(raw_entries[item.key]["etymology"])
    }
    if exact != EXACT_DECOMPOSITIONS:
        raise AssertionError(f"تغيرت أسطر From X + Y المباشرة: {sorted(exact)}")
    for item, decision in zip(selected, decisions):
        candidates = {candidate for candidate, _score in ranked_by_key[item.key]}
        if decision.candidate not in item.row.candidates_found or decision.candidate not in candidates:
            raise AssertionError(f"مرشح {item.key} خارج المروحة الكاملة")
        complete = H.route_complete(item.row, decision.candidate)
        if decision.verdict == "LAW-GAP" and complete:
            raise AssertionError(f"LAW-GAP بلا صف مفقود في {item.key}")
        if decision.verdict == "OPEN-CANDIDATE" and not complete:
            raise AssertionError(f"OPEN-CANDIDATE بمسار ناقص في {item.key}")
        if decision.verdict == "SOURCE-GAP":
            _count, coverage, _witnesses = P.classical_witnesses(
                decision.candidate, sense_map, 60
            )
            if not complete or coverage != 0:
                raise AssertionError(f"SOURCE-GAP غير منضبط في {item.key}")


def validate_text(
    selected: list[SelectedRow], texts: list[str], prior_pairs: set[tuple[str, str]]
) -> None:
    if len(selected) != 70 or BATCH_SIZES != (39, 31):
        raise AssertionError("لم تكتمل الدفعتان 39+31")
    joined = "\n".join(texts)
    headings = re.findall(r"^### (WO-B-R25-(?:BOTH|SOUND)-\d{5}):", joined, re.MULTILINE)
    if headings != [item.heading for item in selected]:
        raise AssertionError("معرفات الجولة 25 لا تطابق النافذة")
    keys = [pair_key(item.row) for item in selected]
    if len(keys) != len(set(keys)):
        raise AssertionError("بقي تكرار كلمة ومعنى داخل الجولة")
    for item in selected:
        if pair_was_read(item.row, prior_pairs):
            raise AssertionError(f"تسرب عضو مقروء إلى الجولة: {item.key}")
    if "—" in joined or re.search(r"[۰-۹٠-٩]", joined):
        raise AssertionError("دخلت شرطة طويلة أو أرقام غير غربية")
    if unicodedata.normalize("NFC", joined) != joined:
        raise AssertionError("النص الجديد ليس NFC")
    required = (
        "نموذج WO-B-PROBE-001", "قراءة مداخل الرسم المتجانس",
        "المروحة المرتبة الكاملة", "الحدث من السجل المجمد",
        "الشاهد 1", "الشاهد 2", "الحكم (استكشاف)",
    )
    for item, card in zip(selected, texts):
        if len(card.encode("utf-8")) >= CARD_LIMIT:
            raise AssertionError(f"تجاوزت {item.key} حد 5KB")
        if any(field not in card for field in required):
            raise AssertionError(f"نقص حقل من بطاقة {item.key}")
    for key in EXACT_DECOMPOSITIONS:
        card = texts[[item.key for item in selected].index(key)]
        if "تفكيك Kaikki الحصري" not in card or "قراءة المكونات المستقلة" not in card:
            raise AssertionError(f"لم تقرأ مكونات {key} استقلالا")
    for key in BLOCKED_BOUNDARIES:
        card = texts[[item.key for item in selected].index(key)]
        if "حد المركب غير المفكك" not in card or "بلا مكونات مخترعة" not in card:
            raise AssertionError(f"لم يغلق حد المركب في {key}")


def report_section(
    selected: list[SelectedRow],
    decisions: list[H.Decision],
    sizes: list[int],
    stats: dict,
) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    batches = (selected[:BATCH_SIZES[0]], selected[BATCH_SIZES[0]:])
    lines = [f"<!-- {MARKER}:START -->", ""]
    for number, batch in enumerate(batches, 1):
        lo = 0 if number == 1 else BATCH_SIZES[0]
        hi = lo + len(batch)
        counts = Counter(decision.verdict for decision in decisions[lo:hi])
        distribution = "؛ ".join(f"{key}={counts[key]}" for key in sorted(counts))
        pool_name = "both" if number == 1 else "sound_only"
        extra = (
            "أُغلق حوض both؛ الرتبة 00462 تكرار مطابق للرتبة 00461 فطُرحت."
            if number == 1
            else "بدأ الحوض الصوتي من أول موضع طازج بعد فحص أزواج WO-B المقروءة."
        )
        lines.extend([
            f"## الجولة الخامسة والعشرون، دفعة {pool_name} رقم {number}", "",
            f"- الوقت: {now}، Africa/Cairo.",
            f"- فُحص ورُشح قبل القراءة: {len(batch)}؛ كُتب: {len(batch)}؛ {extra}",
            (
                f"- المواضع: من {batch[0].heading} إلى {batch[-1].heading}، "
                "مع تجاوز المقروء والتكرار المفحوص."
            ),
            f"- توزيع الأحكام: {distribution}.",
            "- المروحة: وُلدت كاملة ورُتبت بالأوزان لكل عضو، ومُسحت مواد جميع مرشحيها بلا قص للحقل المصدر.",
            "- المتجانسات: قُرئت كل مداخل الرسم، وسُجل العدد ورقم المدخلة المختارة في كل بطاقة.",
            "- المركب: لم يقبل إلا سطر From X + Y النهائي المباشر من Kaikki الخام؛ قُرئ كل مكون مقبول وحده.",
            "- التحقق البنيوي: المعرفات فريدة؛ لا بطاقة فوق 5KB؛ لا شرطة طويلة؛ الأرقام غربية والنص NFC.",
            f"- آخر موضع في الدفعة: {batch[-1].heading}، `{batch[-1].row.branch}`.",
            "",
        ])
    total = Counter(decision.verdict for decision in decisions)
    distribution = "؛ ".join(f"{key}={total[key]}" for key in sorted(total))
    max_size = max(sizes)
    max_item = selected[sizes.index(max_size)]
    exact_text = "، ".join(sorted(EXACT_DECOMPOSITIONS))
    blocked_text = "، ".join(sorted(BLOCKED_BOUNDARIES))
    lines.extend([
        "## حصيلة الجولة الخامسة والعشرين", "",
        (
            f"- حمل `persian.md` مرة واحدة؛ أزواج WO-B المقروءة={stats['pair_count']}؛ "
            f"المتجاوز في both={stats['both_prior']}؛ الطازج الخام={stats['both_raw_fresh']}؛ "
            "تكرار داخلي مطروح=1."
        ),
        f"- مجموع القراءة الجديدة: 70 في دفعتين 39+31؛ {distribution}.",
        "- أُغلق حوض both عند 00494، ثم قُرئت أول 31 موضعا طازجا من sound_only.",
        f"- التفكيك الحصري: {exact_text}؛ قُرئت مكوناتها الثمانية استقلالا من Kaikki ومراوحها.",
        f"- حدود مركب بلا تفكيك مؤهل: {blocked_text}؛ لم تقبل صيغة تحليل سطحي أو مكافأة.",
        "- صلات الجذر الموجبة: لا شيء؛ لم يصنع اتحاد الرسم أو خبر الأصل حكما موجبا.",
        f"- أكبر بطاقة: {max_size} بايت، {max_item.heading}؛ كل البطاقات دون 5KB.",
        "- عطب أداة أساسية: 0؛ لم تُفعّل طبقة البرهان، ولم يُبن ملف مشترك، ولم يقع ship، ولم يستعمل git.",
        "", f"<!-- {MARKER}:END -->", "", DONE_LINE,
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
    headings = re.findall(
        r"^### (WO-B-R25-(?:BOTH|SOUND)-\d{5}):",
        match.group(1),
        re.MULTILINE,
    )
    expected = (
        [f"WO-B-R25-BOTH-{rank:05d}" for rank in BOTH_RANKS]
        + [f"WO-B-R25-SOUND-{rank:05d}" for rank in SOUND_RANKS]
    )
    if headings != expected:
        raise AssertionError("مقطع الجولة 25 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(DONE_LINE):
        raise AssertionError("سطر DONE25 ليس خاتمة التقرير")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    reading_text = READING.read_text(encoding="utf-8")
    report_text = REPORT.read_text(encoding="utf-8")
    if MARKER in reading_text or MARKER in report_text:
        validate_existing(reading_text, report_text)
        print("ROUND25 ALREADY PRESENT AND VALID")
        print(DONE_LINE)
        return 0

    data = json.loads(SWEEP.read_text(encoding="utf-8"))
    selected, stats = select_rows(data, reading_text)
    prior_pairs = H.read_pairs(reading_text)
    lexicon = json.loads(LEXICON.read_text(encoding="utf-8"))
    entries, grouped = select_branch_entries(selected, lexicon)
    raw_entries = load_raw_entries(selected, entries)
    validate_components(grouped)

    ranked_by_key = {
        item.key: H.full_ranked_fan(item.row) for item in selected
    }
    roots = {
        candidate
        for ranked in ranked_by_key.values()
        for candidate, _score in ranked
    }
    roots.update(candidate_for(item) for item in selected)
    sense_map = H.SENSES.matches_for_roots(
        H.SENSES.DEFAULT_RESOURCES, roots, None
    )
    decisions = [decide(item) for item in selected]
    validate_decisions(
        selected, raw_entries, decisions, ranked_by_key, sense_map
    )
    texts = [
        fit_card(
            item, entries[item.key], raw_entries[item.key], decision,
            ranked_by_key[item.key], sense_map,
        )
        for item, decision in zip(selected, decisions)
    ]
    validate_text(selected, texts, prior_pairs)
    sizes = [len(card.encode("utf-8")) + 1 for card in texts]

    split = BATCH_SIZES[0]
    reading_append = (
        f"\n\n<!-- {MARKER}:START -->\n\n"
        "## الجولة الخامسة والعشرون: إغلاق both وبدء sound_only (2026-08-25)\n\n"
        "- النطاق: 39 عضوا فريدا لإغلاق both بعد WO-B-OPEN-COMP-00444، ثم 31 عضوا من أول sound_only الطازج؛ دفعتان 39+31.\n"
        "- النموذج: WO-B-PROBE-001؛ المركب لا يفكك إلا بسطر Kaikki النهائي المباشر `From X + Y`، وكل مكون مقبول يقرأ وحده.\n\n"
        + "\n".join(texts[:split])
        + "\n## الدفعة الثانية: أول sound_only الطازج بعد إغلاق both\n\n"
        + "\n".join(texts[split:])
        + f"\n<!-- {MARKER}:END -->\n"
    )
    report_append = "\n" + report_section(selected, decisions, sizes, stats) + "\n"
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
    print("ROUND25 READY")
    print(
        "BOTH_PRIOR", stats["both_prior"],
        "BOTH_RAW_FRESH", stats["both_raw_fresh"],
        "DUPLICATE_RANKS", ",".join(map(str, stats["both_internal_duplicates"])),
    )
    print("BATCHES", *BATCH_SIZES, "SELECTED", len(selected))
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("EXACT_FROM_PLUS", " ".join(sorted(EXACT_DECOMPOSITIONS)))
    print("BLOCKED_BOUNDARIES", len(BLOCKED_BOUNDARIES))
    print("MAX_CARD", max(sizes), selected[sizes.index(max(sizes))].heading)
    if args.preview:
        print("PREVIEW ONLY")
        print(DONE_LINE)
        return 0

    with READING.open("a", encoding="utf-8", newline="") as handle:
        handle.write(reading_append)
    with REPORT.open("a", encoding="utf-8", newline="") as handle:
        handle.write(report_append)
    print("ROUND25 WRITTEN")
    print(DONE_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
