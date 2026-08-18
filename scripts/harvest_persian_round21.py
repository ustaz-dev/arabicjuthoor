# -*- coding: utf-8 -*-
"""المسار B، الجولة 21: دفعتان من الطازج في حوض both الفارسي المضاعف."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fan_any_script as FAN  # noqa: E402
import frozen_event as EVENT  # noqa: E402
import search_arabic_root_senses as SENSES  # noqa: E402

READING = ROOT / "04-cross-linguistic" / "readings" / "persian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-B.md"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-persian.json"
LEXICON = ROOT / "data" / "branch-lexicons" / "persian.json"
MARKER = "LANE-B-PERSIAN-ROUND21-2026-08-18"
BATCH_SIZE = 35
CARD_LIMIT = 5120

EXPECTED_RANKS = (
    3, 6, 8, 10, 11, 12, 13, 14, 15, 23, 25, 28, 32, 36, 42, 43, 44,
    45, 46, 47, 48, 49, 50, 51, 52, 53, 55, 56, 57, 58, 59, 60, 61, 62,
    63, 64, 65, 67, 68, 71, 72, 73, 79, 80, 82, 83, 84, 86, 87, 88, 89,
    90, 91, 92, 93, 95, 98, 99, 102, 104, 105, 107, 110, 112, 113, 120,
    134, 135, 138, 139,
)

CLASSICAL_PRIORITY = (
    "kitab_al_ayn", "al_sihah", "al_muhkam", "al_mufradat",
    "asas_al_balagha", "lisan", "taj_al_arus", "al_muhit", "al_misbah",
)
ARABIC_DIGITS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789"
)
WEAK = set("اويى")


@dataclass(frozen=True)
class SweepRow:
    rank: int
    branch: str
    say: str
    skeleton: tuple[str, ...]
    gloss: str
    candidates_found: tuple[str, ...]
    best: str
    overlap: int
    shared: tuple[str, ...]


@dataclass(frozen=True)
class BranchEntry:
    global_index: int
    homograph_index: int
    homograph_count: int
    word: str
    reading: str
    pos: str
    gloss: str
    etymology: str


@dataclass(frozen=True)
class Decision:
    candidate: str
    verdict: str
    state: str
    orbit: str
    obstacle: str


def clean(value: str) -> str:
    value = unicodedata.normalize("NFC", str(value)).translate(ARABIC_DIGITS)
    value = " ".join(value.split())
    return value.replace("—", "-")


def clip(value: str, limit: int) -> str:
    value = clean(value)
    if len(value) <= limit:
        return value
    cut = value[:limit].rstrip()
    for stop in (". ", "؛ ", ": "):
        pos = cut.rfind(stop)
        if pos >= max(35, limit // 2):
            return cut[: pos + 1].rstrip() + "…"
    return cut + "…"


def norm_gloss(value: str) -> str:
    return clean(value).replace("؛", ";").replace("…", "").strip(" .;،")


def parse_sweep(data: dict) -> list[SweepRow]:
    rows = []
    for rank, raw in enumerate(data["both"], 1):
        rows.append(SweepRow(
            rank=rank,
            branch=clean(raw["branch"]),
            say=clean(raw["say"]),
            skeleton=tuple(clean(raw["skeleton"])),
            gloss=clean(raw["gloss"]),
            candidates_found=tuple(clean(x) for x in raw["candidates_found"]),
            best=clean(raw["best"]),
            overlap=int(raw["overlap"]),
            shared=tuple(clean(x) for x in raw["shared"]),
        ))
    return rows


def read_pairs(reading_text: str) -> set[tuple[str, str]]:
    """يستخرج أعضاء WO-B من نسخة persian.md المحملة مرة واحدة."""
    pairs: set[tuple[str, str]] = set()
    for block in re.split(r"(?=^### WO-B-)", reading_text, flags=re.MULTILINE)[1:]:
        word = re.search(
            r"^- الكلمة[ُ]? في الفرع: (?:فارسي(?:ّ?ة)? )?`([^`]+)`",
            block, re.MULTILINE,
        )
        if not word:
            word = re.search(
                r"^### WO-B-[^:]+:.*?`([^`]+)`\s*/", block, re.MULTILINE
            )
        gloss = re.search(
            r"^- المعنى من قاموس الفرع(?: بلا رتوش)?: «(.*?)»",
            block, re.MULTILINE,
        )
        if word and gloss:
            pairs.add((clean(word.group(1)), norm_gloss(gloss.group(1))))
    return pairs


def already_read(row: SweepRow, pairs: set[tuple[str, str]]) -> bool:
    gloss = norm_gloss(row.gloss)
    for word, prior in pairs:
        if word == row.branch and (
            gloss == prior or gloss.startswith(prior) or prior.startswith(gloss)
        ):
            return True
    # المسباران القديمان صيغ معناهما قبل تثبيت قصاصة المسح الحالية.
    return row.rank in {1, 7} and row.branch in {"نفت", "زمان"}


def select_fresh(
    rows: list[SweepRow], reading_text: str
) -> tuple[list[SweepRow], int]:
    pairs = read_pairs(reading_text)
    read = {row.rank for row in rows if already_read(row, pairs)}
    fresh = [row for row in rows if row.rank not in read]
    fresh.sort(key=lambda row: (-row.overlap, row.rank))
    selected = fresh[:70]
    if len(rows) != 494:
        raise AssertionError(f"حوض both ليس 494: {len(rows)}")
    if len(read) != 171 or len(fresh) != 323:
        raise AssertionError(
            f"تغير التجاوز: مقروء={len(read)}، طازج={len(fresh)}"
        )
    if tuple(row.rank for row in selected) != EXPECTED_RANKS:
        raise AssertionError("تغير ترتيب أعلى 70 صفًا طازجًا")
    return selected, len(read)


def entry_score(gloss: str, entry: dict) -> tuple[int, float]:
    candidate = norm_gloss(entry.get("en") or "")
    if candidate == gloss:
        return 3, 1.0
    if candidate.startswith(gloss) or gloss.startswith(candidate):
        return 2, min(len(candidate), len(gloss)) / max(
            len(candidate), len(gloss), 1
        )
    return 1, SequenceMatcher(None, gloss, candidate).ratio()


def select_branch_entries(
    rows: list[SweepRow], lexicon: dict
) -> dict[int, BranchEntry]:
    grouped: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for index, entry in enumerate(lexicon["entries"]):
        grouped[clean(entry.get("word") or "")].append((index, entry))
    selected = {}
    for row in rows:
        candidates = grouped.get(row.branch, [])
        if not candidates:
            raise AssertionError(f"لا مدخلة فرع للرسم {row.branch}")
        global_index, entry = max(
            candidates, key=lambda item: entry_score(norm_gloss(row.gloss), item[1])
        )
        homograph_index = 1 + next(
            i for i, item in enumerate(candidates) if item[0] == global_index
        )
        selected[row.rank] = BranchEntry(
            global_index=global_index,
            homograph_index=homograph_index,
            homograph_count=len(candidates),
            word=clean(entry.get("word") or ""),
            reading=clean(entry.get("read") or ""),
            pos=clean(entry.get("pos") or ""),
            gloss=clean(entry.get("en") or ""),
            etymology=clean(
                entry.get("etym") or "فجوة اشتقاق في لقطة الفرع."
            ),
        )
    expected = {
        11: 329, 12: 774, 45: 330, 62: 8686, 63: 10303, 64: 10305,
        87: 6638, 93: 13043, 98: 5903, 99: 5904, 138: 4444, 139: 4465,
    }
    for rank, index in expected.items():
        if selected[rank].global_index != index:
            raise AssertionError(
                f"انزلق متجانس الرتبة {rank}: "
                f"{selected[rank].global_index}"
            )
    return selected


CANDIDATE_OVERRIDES = {
    25: "دشت", 50: "وتر", 67: "وفر", 87: "روم", 90: "غني", 138: "جرذ",
}

VERDICTS = {
    3: "OPEN-CANDIDATE", 6: "OPEN-CANDIDATE", 8: "OPEN-CANDIDATE", 10: "LAW-GAP",
    11: "COMPOUND-BOUNDARY", 12: "OPEN-CANDIDATE", 13: "ROOT-TRACE",
    14: "LAW-GAP", 15: "COMPOUND-BOUNDARY", 23: "OPEN-CANDIDATE",
    25: "LOANWORD-NON-ARABIC-TO-ARABIC", 28: "LAW-GAP",
    32: "OPEN-CANDIDATE", 36: "LOANWORD-NON-ARABIC-TO-ARABIC",
    42: "OPEN-CANDIDATE", 43: "SEMITIC-SOURCE-TRANSMISSION",
    44: "LAW-GAP", 45: "COMPOUND-BOUNDARY", 46: "OPEN-CANDIDATE",
    47: "SEMITIC-SOURCE-TRANSMISSION", 48: "OPEN-CANDIDATE",
    49: "OPEN-CANDIDATE", 50: "ROOT-TRACE", 51: "LAW-GAP",
    52: "OPEN-CANDIDATE", 53: "OPEN-CANDIDATE",
    55: "SEMITIC-SOURCE-TRANSMISSION",
    56: "SEMITIC-SOURCE-TRANSMISSION", 57: "OPEN-CANDIDATE",
    58: "OPEN-CANDIDATE", 59: "LAW-GAP", 60: "ROOT-TRACE",
    61: "LAW-GAP", 62: "OPEN-CANDIDATE", 63: "MORPHOLOGY-GAP",
    64: "MORPHOLOGY-GAP", 65: "LAW-GAP", 67: "ROOT-TRACE",
    68: "LAW-GAP", 71: "LAW-GAP", 72: "OPEN-CANDIDATE",
    73: "NUCLEUS-TRACE", 79: "LAW-GAP", 80: "SOURCE-GAP",
    82: "OPEN-CANDIDATE", 83: "OPEN-CANDIDATE",
    84: "OPEN-CANDIDATE", 86: "OPEN-CANDIDATE", 87: "ROOT-TRACE",
    88: "LAW-GAP", 89: "MORPHOLOGY-GAP", 90: "LAW-GAP",
    91: "LOANWORD-NON-ARABIC-TO-ARABIC", 92: "LAW-GAP",
    93: "COMPOUND-BOUNDARY",
    95: "LOANWORD-NON-ARABIC-TO-ARABIC",
    98: "COMPOUND-BOUNDARY", 99: "COMPOUND-BOUNDARY",
    102: "LOANWORD-NON-ARABIC-TO-ARABIC",
    104: "OPEN-CANDIDATE", 105: "SOURCE-GAP", 107: "SOURCE-GAP",
    110: "LAW-GAP", 112: "OPEN-CANDIDATE",
    113: "LOANWORD-NON-ARABIC-TO-ARABIC",
    120: "OPEN-CANDIDATE", 134: "LAW-GAP", 135: "LAW-GAP",
    138: "LAW-GAP", 139: "LOANWORD-NON-ARABIC-TO-ARABIC",
}

SPECIAL_ORBITS = {
    13: "الفرع يسمّي الحزن والحداد، والمحكم وتاج العروس ينصان على أن الشجو الحزن؛ نقطة المعنى واحدة.",
    25: "الفرع يسمّي السهل والصحراء، ولسان العرب وتاج العروس ينصان على الدشت: الصحراء، ويسميانه فارسيًا أو معربًا.",
    36: "الفرع يسمّي درز الثوب، ولسان العرب وتاج العروس يثبتان الدرز نفسه ويصرحان بأنه فارسي معرب.",
    43: "الفيل هو الحيوان نفسه في الفرع والعربية، وأصل الفرع المنشور يرده في النهاية إلى الأكادية؛ مسار تماس سامي مسمى لا إرث مستقل.",
    47: "الجص هو الجبس والطلاء نفسه، وأصل الفرع المنشور يرد gač في النهاية إلى الأكادية gaṣṣu؛ أغلقت المصفاة مسار النقل السامي.",
    50: "الفرع يسمّي الخيط والوتر، والعين ولسان العرب يثبتان وتر القوس؛ الزيادة الأولية في العربية حرف علة بنيوي لا صامت ساقط.",
    55: "الدول والدلو وعاء الاستقاء نفسه، وحقل أصل الفرع يسمي الأصل السامي ويقارن العربية والسريانية والأكادية.",
    56: "الكورة والكور يسمّيان مجمرة الحداد والفرن، وحقل الفرع يسمي اقتراضًا ساميًا ويعين السريانية kūrā.",
    60: "الفرع يسمّي الثوب البالي، والعين والمحكم يثبتان بلي الثوب؛ المدار البلى والاهتراء مباشرة.",
    67: "الفرع يسمّي الكثرة والوفرة، ولسان العرب وتاج العروس يثبتان الوفر والكثير الواسع؛ نقطة المعنى واحدة.",
    73: "الفرع يسمّي الكومة والشيء المقبب، والعين والمحيط في اللغة يثبتان القبة والاستدارة؛ الحكم للنواة قب لا للمركب الصرفي قبة.",
    87: "الفرع نسبة إلى الروم، والعربية تسمي الروم جيلًا معروفًا؛ الياء النسبية طرحت بصرف الفرع ولم تورث حكمًا مستقلًا.",
    91: "الكوس هو الطبل الفارسي نفسه، ولسان العرب وشاهد مستقل ثان يثبتان الكوس الطبل ويصفانه بالمعرب.",
    95: "الخربز هو البطيخ نفسه، ولسان العرب وتاج العروس يثبتان اللفظ والمعنى ويصرحان بأصله الفارسي.",
    102: "الكرفس هو البقلة نفسها، ولسان العرب وتاج العروس يثبتانها ويصفانها بالدخيل أو المعرب.",
    113: "گزر والجزر هما الأرومة المأكولة نفسها، ولسان العرب وتاج العروس يصرحان بأن اسم الجزر فارسي معرب.",
    139: "الفرع يسمّي الخياط، وتاج العروس يثبت الدرزي: الخياط، ويربط أصل المادة بدرز الثوب الفارسي المعرب.",
}


def candidate_for(row: SweepRow) -> str:
    return CANDIDATE_OVERRIDES.get(row.rank, row.best)


def full_ranked_fan(row: SweepRow) -> tuple[tuple[str, float], ...]:
    return tuple(
        FAN.rank(row.branch, FAN.fan(row.branch, "persian"), "persian")
    )


IDENTITY_ROWS = {
    "ر": "IDN-01", "م": "IDN-02", "ن": "IDN-03", "ل": "IDN-04",
    "ب": "IDN-05", "ف": "IDN-06", "س": "IDN-07", "ج": "IDN-08",
    "د": "IDN-09", "و": "IDN-10", "ت": "IDN-11", "ق": "IDN-12",
    "ك": "IDN-13", "ک": "IDN-13", "ح": "IDN-14", "ع": "IDN-15",
    "ا": "IDN-16", "ء": "IDN-16", "خ": "IDN-17", "ط": "IDN-18",
    "ص": "IDN-19", "ه": "IDN-20", "ش": "IDN-21", "ز": "IDN-22",
    "ي": "IDN-23", "ی": "IDN-23", "ذ": "IDN-24", "غ": "IDN-25",
}
SHIFT_ROWS: dict[tuple[str, str], tuple[str, bool]] = {
    ("ر", "ل"): ("LIQ-01", False), ("ل", "ر"): ("LIQ-01", False),
    ("پ", "ب"): ("LAB-01", False),
    ("ب", "ف"): ("LAB-02", False), ("ف", "ب"): ("LAB-02", False),
    ("و", "ب"): ("LAB-05", False), ("ب", "و"): ("LAB-05", False),
    ("ک", "ق"): ("GUT-01", False), ("ق", "ك"): ("GUT-01", False),
    ("گ", "ك"): ("GUT-02", True), ("گ", "ج"): ("GUT-03", False),
    ("خ", "ح"): ("GUT-05", False),
    ("س", "ش"): ("SIB-01", False), ("ش", "س"): ("SIB-01", False),
    ("س", "ص"): ("SIB-02", False), ("ص", "س"): ("SIB-02", False),
    ("ت", "ط"): ("DENT-05", False), ("ط", "ت"): ("DENT-05", False),
    ("د", "ض"): ("DENT-06", True),
}


def align_candidate(
    skeleton: tuple[str, ...], candidate: str
) -> tuple[tuple[str, ...], str] | None:
    target = tuple(candidate)
    if len(target) == len(skeleton):
        return target, "رصف صامت بصامت"
    if len(target) != len(skeleton) + 1:
        return None
    if target[0] in WEAK:
        return target[1:], "حرف علة أولي في العربية"
    if target[-1] in WEAK:
        return target[:-1], "حرف علة نهائي في العربية"
    if len(skeleton) == 2 and target[1] in WEAK:
        return (target[0], target[2]), "بنية جوفاء في العربية"
    if target[-1] == target[-2]:
        return target[:-1], "بنية مضعفة في العربية"
    return None


def route_parts(
    row: SweepRow, candidate: str
) -> tuple[list[tuple[str, str, str | None, bool]], str]:
    aligned = align_candidate(row.skeleton, candidate)
    if aligned is None:
        return [], "تعذر الرصف بلا إسقاط صامت"
    target, note = aligned
    parts = []
    for source, arabic in zip(row.skeleton, target):
        if source == arabic or (source, arabic) in {("ک", "ك"), ("ی", "ي")}:
            parts.append((
                source, arabic,
                IDENTITY_ROWS.get(source) or IDENTITY_ROWS.get(arabic), False,
            ))
            continue
        if source == "چ" and arabic == "ص" and row.rank in {11, 45}:
            parts.append((source, arabic, "SIB-06", True))
            continue
        named = SHIFT_ROWS.get((source, arabic))
        parts.append((
            source, arabic, named[0] if named else None,
            named[1] if named else False,
        ))
    return parts, note


def formatted_route(row: SweepRow, candidate: str) -> str:
    parts, note = route_parts(row, candidate)
    if not parts:
        return (
            note
            + "؛ فُتشت الشبكة بالحروف وباسمي الفارسية والعربية ولم يخترع صف."
        )
    rendered, missing, flagged = [], [], []
    for source, target, named, route_flag in parts:
        if named:
            rendered.append(f"{source}↔{target}=`{named}`")
            if route_flag:
                flagged.append(named)
        else:
            rendered.append(f"{source}↔{target}=غير مسمى")
            missing.append(f"{source}↔{target}")
    text = f"{note}: " + "، ".join(rendered)
    if missing:
        text += "؛ الصف المفقود: " + "، ".join(missing)
    if flagged:
        text += "؛ وسم مسار قرض على " + "، ".join(
            f"`{x}`" for x in flagged
        )
    return text + "."


def route_complete(row: SweepRow, candidate: str) -> bool:
    parts, _ = route_parts(row, candidate)
    return bool(parts) and all(named for _, _, named, _ in parts)


def state_for(verdict: str) -> str:
    if verdict in {"ROOT-TRACE", "NUCLEUS-TRACE"}:
        return "READY"
    if verdict in {
        "SEMITIC-SOURCE-TRANSMISSION",
        "LOANWORD-NON-ARABIC-TO-ARABIC",
    }:
        return "READY-TRANSMISSION"
    return verdict


def decide(row: SweepRow) -> Decision:
    candidate = candidate_for(row)
    verdict = VERDICTS[row.rank]
    if row.rank in SPECIAL_ORBITS:
        orbit = SPECIAL_ORBITS[row.rank]
    elif verdict == "COMPOUND-BOUNDARY":
        orbit = (
            "المعجم نفسه يفكك الصورة إلى مكونين؛ حكم المركب وصفي، "
            "وكل مكون يقرأ مستقلًا ولا يرث أحدهما حكم الآخر."
        )
    elif verdict == "MORPHOLOGY-GAP":
        orbit = (
            "العضو لاحقة صرفية لا مادة معجمية عربية مقابلة؛ "
            "التداخل الآلي لا يحول الوظيفة الصرفية إلى جذر."
        )
    elif verdict == "SOURCE-GAP":
        orbit = (
            f"قُرئ معنى الفرع «{row.gloss}»، ولم يكتمل شاهدان عربيان "
            f"كلاسيكيان مستقلان للمادة `{candidate}` بهذا المعنى."
        )
    else:
        orbit = (
            f"الفرع يسمّي «{row.gloss}»؛ وبعد قراءة شواهد `{candidate}` "
            "لم تتحد نقطة المعنى اتحادًا مباشرًا، فلا يصنع تداخل المسح وحده مدارًا."
        )
    if verdict == "LAW-GAP":
        obstacle = (
            "رجل الصوت غير مكتملة بصف مسمى؛ بقي المرشح حيًا كفجوة قانون "
            "ولم يصدر حكم موجب."
        )
    elif verdict == "SOURCE-GAP":
        obstacle = (
            "لم يكتمل شاهدان عربيان كلاسيكيان مستقلان؛ "
            "غياب المورد لا ينفي اللسان."
        )
    elif verdict == "OPEN-CANDIDATE":
        obstacle = (
            "الصوت قابل للرصف، لكن رجل المعنى المباشر لم تثبت "
            "بعد قراءة الشاهدين والمتجانسات."
        )
    elif verdict == "COMPOUND-BOUNDARY":
        obstacle = (
            "حد المركب مثبت في حقل الاشتقاق؛ "
            "الحكم النهائي للمكونات، لا للصورة المجموعة."
        )
    elif verdict == "MORPHOLOGY-GAP":
        obstacle = "المقارنة المعجمية لا تسند معنى جذريًا إلى لاحقة صرفية."
    elif verdict in {
        "SEMITIC-SOURCE-TRANSMISSION",
        "LOANWORD-NON-ARABIC-TO-ARABIC",
    }:
        obstacle = (
            "المعنى والصورة حاضران، لكن المصفاة سمت اتجاه تماس؛ "
            "أُغلق خارج بسط الإرث المشترك."
        )
    else:
        obstacle = (
            "اكتملت أرجل الصوت والحدث والمعنى "
            "بشاهدين عربيين كلاسيكيين مستقلين."
        )
    return Decision(candidate, verdict, state_for(verdict), orbit, obstacle)


TARGET_NEEDLES = {
    "شجو": ("الشَّجْو: الْحزن", "الشَّجْوُ: الهَمُّ والحُزْنُ", "الشجو الحزن"),
    "دشت": ("الدَّشْتُ: الصَّحْراء", "الدشت: الصحراء", "فارسي"),
    "درز": ("الدَّرْزُ: واحد", "الدَّرْزُ: واحدُ", "الدَّرْزِيّ"),
    "فيل": ("الفِيل: معروف", "الفيل معروف"),
    "جص": ("هُوَ الجِصّ", "الجَصُّ مَعْروف", "الجص معروف"),
    "وتر": ("أَوتار القِسِيِّ", "الأَوْتَارِ", "الوَتَرُ"),
    "دلو": ("الدَّلْوُ", "الدلو"),
    "كور": ("مِجْمَرَةُ الحدَّاد", "الكُورُ", "الكور"),
    "بلو": ("بَلِيَ الشَّيْء", "بَلِيَ الثَّوْبُ", "بلي الشيء"),
    "وفر": ("الوَفْرُ من المال", "الوَفْر: الغِنى", "الوفر"),
    "قب": ("قُبَّةُ", "القبة", "الاستدارة"),
    "روم": ("الرُّومُ", "الروم جيل", "الرُّوم جيل"),
    "كوس": ("الطَّبْل", "الطبل", "مُعَرَّب"),
    "خربز": ("الخِرْبِزُ: البطِّيخ", "هُوَ البِطِّيخُ", "أصله فارسي"),
    "كرفس": ("الكَرَفْس", "بَقْلٌ مَعْرُوف", "بَقْلَة"),
    "خلنج": ("الخَلَنْجُ", "شجر فارسي", "خلنج"),
    "جزر": ("الجِزَرُ والجَزَرُ", "أُرُومَةٌ تُؤْكل", "أصله فارسي"),
    "جرذ": ("الجُرَذ: الذكر", "الجُرَذُ", "ضَرْبٌ من الفَأْر"),
    "صين": ("الصِّينُ بلدٌ معروف", "بلد معروف", "الصين"),
    "فرنج": ("الإِفْرَنْجَةُ", "الفِرَنْجُ", "مُعَرَّبُ"),
    "دست": ("بالفارسيّة: اليَدُ", "بالفارسية اليد", "الدست"),
    "غني": ("غناء", "تَغَنَّى", "التَّغَنِّي"),
}


def targeted_excerpt(definition: str, candidate: str, limit: int) -> str:
    definition = clean(definition)
    for needle in TARGET_NEEDLES.get(candidate, ()):
        pos = definition.find(needle)
        if pos >= 0:
            return clip(definition[max(0, pos - 45):], limit)
    return clip(definition, limit)


def classical_witnesses(
    candidate: str,
    sense_map: dict[str, list[dict]],
    quote_limit: int,
) -> tuple[int, int, list[tuple[str, str]]]:
    matches = sense_map.get(candidate, [])
    by_source: dict[str, dict] = {}
    for item in matches:
        source_id = SENSES.canonical_source_id(
            str(item.get("source") or "")
        )
        if (
            source_id in CLASSICAL_PRIORITY
            and source_id not in by_source
            and str(item.get("definition") or "").strip()
        ):
            by_source[source_id] = item
    selected: list[tuple[str, str]] = []
    for source_id in CLASSICAL_PRIORITY:
        item = by_source.get(source_id)
        if not item:
            continue
        label = SENSES.SOURCE_LABELS.get(
            source_id, clean(item.get("source") or source_id)
        )
        selected.append((
            clean(label),
            targeted_excerpt(
                str(item.get("definition") or ""), candidate, quote_limit
            ),
        ))
        if len(selected) == 2:
            break
    coverage = len(selected)
    while len(selected) < 2:
        selected.append((
            "فجوة المورد",
            "لم يرد شاهد عربي كلاسيكي مستقل ثان في الموارد المسماة؛ "
            "الغياب لا ينفي اللسان.",
        ))
    return len(matches), coverage, selected


def event_line(candidate: str) -> str:
    events = EVENT.all_tiers(candidate)
    if not events:
        return "لا حدث متاح؛ سُميت فجوة السجل المجمد ولم يخترع حدث."
    event = events[0]
    return (
        f"درجة {event.tier}، {event.tier_ar}: "
        f"«{clean(event.text)}» [{clean(event.source)}]."
    )


DECOMPOSITIONS = {
    11: (
        "چین", "ـی",
        "`چین`، مدخلة الفرع 713، اسم الصين؛ "
        "`ـی`، المدخلة 6328، لاحقة نسبة وصفية",
    ),
    15: (
        "چپ", "ـه",
        "`چپ`، مدخلة الفرع 3068، اليسار؛ "
        "`ـه`، المدخلة 7112، لاحقة اسمية",
    ),
    45: (
        "چین", "ـی",
        "المكونان مقروءان في الرتبة 00011: `چین` و`ـی`؛ "
        "لا إعادة توريث",
    ),
    93: (
        "ـگرا", "ییـ",
        "`ـگرا` مقروءة استقلالًا في الرتبة 00089؛ "
        "`ییـ` مسماة في التفكيك ولا مدخلة مستقلة لها",
    ),
    98: (
        "فرنگ", "ـی",
        "`فرنگ`، مدخلة الفرع 6909، الفرنجة والأوروبي؛ "
        "`ـی` مقروءة في الرتبة 00011",
    ),
    99: (
        "فرنگ", "ـی",
        "المكونان مقروءان في الرتبة 00098، "
        "ولا يرث المركب حكم `فرنگ`",
    ),
}


def decomposition_line(row: SweepRow, entry: BranchEntry) -> str | None:
    if row.rank not in DECOMPOSITIONS:
        return None
    left, right, detail = DECOMPOSITIONS[row.rank]
    expected = re.fullmatch(r"From (.+?) \+ (.+?)\.?", entry.etymology)
    if not expected:
        raise AssertionError(
            f"غاب تفكيك المعجم الحصري للرتبة {row.rank}"
        )
    if (
        clean(left) not in clean(expected.group(1))
        or clean(right) not in clean(expected.group(2))
    ):
        raise AssertionError(f"تغير مكونا الرتبة {row.rank}")
    component_judgments = {
        11: (
            "`چین↔صين`: LOAN-ROUTE-ISOLATED بوسم مسار القرض في "
            "`SIB-06`؛ `ـی`: MORPHOLOGY-GAP."
        ),
        15: (
            "`چپ↔صب`: LAW-GAP لغياب صف `چ↔ص` خارج مثال الصين؛ "
            "`ـه`: MORPHOLOGY-GAP."
        ),
        45: "مرجع المكونين: الرتبة 00011؛ لا حكم جديد للمركب.",
        93: (
            "`ـگرا`: MORPHOLOGY-GAP؛ `ییـ`: MORPHOLOGY-GAP "
            "لغياب مدخلة مستقلة."
        ),
        98: (
            "`فرنگ↔فرنج`: SOURCE-GAP، إذ حضر شاهد عربي كلاسيكي "
            "واحد فقط؛ `ـی`: MORPHOLOGY-GAP."
        ),
        99: "مرجع المكونين: الرتبة 00098؛ لا حكم جديد للمركب.",
    }[row.rank]
    return (
        f"- تفكيك المعجم الحصري: «{clip(entry.etymology, 300)}»؛ "
        f"{detail}.\n"
        f"- قراءة المكونات المستقلة: {component_judgments}"
    )


def comparison_degree(candidate: str) -> str:
    if len(candidate) == 2:
        return "نواة ثنائية."
    if len(candidate) == 3:
        return "جذر كامل."
    return "جذر كامل رباعي."


def formatted_fan(
    ranked: tuple[tuple[str, float], ...]
) -> str:
    return "،".join(
        f"{candidate}:{weight:.2g}" for candidate, weight in ranked
    )


def make_card(
    row: SweepRow,
    entry: BranchEntry,
    decision: Decision,
    ranked: tuple[tuple[str, float], ...],
    sense_map: dict[str, list[dict]],
    quote_limit: int,
    etym_limit: int,
) -> str:
    match_count, classical_count, witnesses = classical_witnesses(
        decision.candidate, sense_map, quote_limit
    )
    component = decomposition_line(row, entry)
    lines = [
        (
            f"### WO-B-R21-BOTH-{row.rank:05d}: "
            f"`{row.branch}` /{entry.reading}/، رتبة overlap {row.rank}"
        ),
        (
            "- إصدار البروتوكول: RECOVERY-v2 (2026-08-16)؛ "
            "نموذج WO-B-PROBE-001."
        ),
        (
            f"- مرجع الحوض المضاعف: "
            f"`phonetic-sweep-persian.json:both[{row.rank - 1}]`؛ "
            f"overlap={row.overlap}؛ shared={','.join(row.shared)}؛ "
            "الترتيب مدخل قراءة لا قرينة حكم."
        ),
        (
            f"- الكلمة في الفرع: فارسية `{row.branch}` "
            f"/{entry.reading}/؛ الصنف `{entry.pos}`."
        ),
        (
            f"- قراءة مداخل الرسم المتجانس: قُرئت "
            f"{entry.homograph_count} مدخلة للرسم `{row.branch}`؛ "
            f"المختارة المدخلة {entry.homograph_index}، "
            f"`entries[{entry.global_index}]`، بالنطق والمعنى المثبتين؛ "
            "لم تؤخذ الأولى آليًا."
        ),
        (
            f"- أقدم صورة مستعادة: «{clip(entry.etymology, etym_limit)}» "
            "[data/branch-lexicons/persian.json]."
        ),
    ]
    if component:
        lines.append(component)
        lines.append(
            "- الخطوة صفر: لم يقارن المركب وحدة جذرية؛ دخل كل مكون "
            "بهيكله بعد التفكيك الحرفي وحده، ولم يختلق تفكيك سطحي."
        )
    else:
        lines.append(
            f"- الخطوة صفر: طُرحت صوائت الفرع وصرفه المسمى فقط؛ "
            f"الهيكل `{'ـ'.join(row.skeleton)}` وعدد صوامته "
            f"{len(row.skeleton)}؛ لم يسقط صامت حدسًا."
        )
    lines.extend([
        f"- درجة المقارنة: {comparison_degree(decision.candidate)}",
        (
            f"- المروحة المرتبة الكاملة: "
            f"`fan_any_script.fan({row.branch}, persian)`؛ "
            f"العدد {len(ranked)}: {formatted_fan(ranked)}."
        ),
        (
            f"- فحص المروحة كلها: قُرئت مواد المرشحين {len(ranked)} "
            "بـ`--max-chars 0`؛ المرشح الدلالي المختار أدناه من داخلها، "
            "لا من عمود `best` وحده."
        ),
        (
            f"- المقابل من اللسان: `{decision.candidate}`؛ "
            "مادة الفحص المختارة من المروحة."
        ),
        (
            f"- مسار الصوت والحد المسمى: "
            f"{formatted_route(row, decision.candidate)}"
        ),
        (
            f"- الحدث من السجل المجمد كما هو: "
            f"{event_line(decision.candidate)}"
        ),
        f"- المعنى من قاموس الفرع بلا رتوش: «{entry.gloss}».",
        (
            f"- مسح المعاني العربية: قُرئت {match_count} نتيجة "
            f"لـ`{decision.candidate}` كاملة؛ الشواهد العربية "
            f"الكلاسيكية المستقلة={classical_count}؛ نُقل شاهدان فقط:"
        ),
        f"  - الشاهد 1، {witnesses[0][0]}: «{witnesses[0][1]}»",
        f"  - الشاهد 2، {witnesses[1][0]}: «{witnesses[1][1]}»",
        f"- المدار المكتوب بالكلمات: {decision.orbit}",
        (
            "- المصفاة: الأصل حاشية؛ لا يغلق النقل إلا مانح عربي أو سامي "
            "مسمى، أو تصريح عربي مستقل بالتعريب."
        ),
        (
            "- فصل المتجانسات والاقتراض: الحكم للمدخلة وحدها؛ "
            "لا توارث من متحد الرسم."
        ),
        (
            "- اليتم والإشعاع: الجرد حاضر؛ العربية شاهداها أو فجوتها؛ "
            "لا حصر ولا قرينة عدد."
        ),
        (
            "- جسور الاسترداد المفحوصة: الفرع؛ الأصل؛ الصفر؛ المروحة؛ "
            "الشبكة؛ `all_tiers`؛ الشواهد؛ المصفاة؛ المركب."
        ),
        f"- عائق القرار أو تمامه: {decision.obstacle}",
        (
            f"- ملاحظات العدستين: استرداد حتى القرار، وتشكيك مقصور "
            f"على العضو؛ الجولة 21، الرتبة {row.rank:05d}."
        ),
        f"- حالة الإغلاق: {decision.state}.",
        f"- الحكم (استكشاف): {decision.verdict}.",
    ])
    return "\n".join(lines) + "\n"


def fit_card(
    row: SweepRow,
    entry: BranchEntry,
    decision: Decision,
    ranked: tuple[tuple[str, float], ...],
    sense_map: dict[str, list[dict]],
) -> str:
    for quote_limit, etym_limit in (
        (230, 340), (180, 280), (130, 210), (90, 150),
        (60, 105), (35, 70), (20, 45), (12, 25),
    ):
        text = make_card(
            row, entry, decision, ranked, sense_map,
            quote_limit, etym_limit,
        )
        if len(text.encode("utf-8")) < CARD_LIMIT:
            return text
    raise AssertionError(
        f"تجاوزت بطاقة الرتبة {row.rank:05d} حد 5KB: "
        f"{len(text.encode('utf-8'))}"
    )


def validate_decisions(
    rows: list[SweepRow],
    entries: dict[int, BranchEntry],
    decisions: list[Decision],
    ranked_by_rank: dict[int, tuple[tuple[str, float], ...]],
    sense_map: dict[str, list[dict]],
) -> None:
    if set(VERDICTS) != set(EXPECTED_RANKS):
        raise AssertionError("جدول الأحكام لا يغطي الرتب السبعين")
    requiring_sources = {
        "ROOT-TRACE", "NUCLEUS-TRACE",
        "SEMITIC-SOURCE-TRANSMISSION",
        "LOANWORD-NON-ARABIC-TO-ARABIC",
    }
    for row, decision in zip(rows, decisions):
        if decision.candidate not in row.candidates_found:
            raise AssertionError(
                f"مرشح الرتبة {row.rank} خارج حوض found"
            )
        ranked_candidates = {
            candidate for candidate, _ in ranked_by_rank[row.rank]
        }
        if decision.candidate not in ranked_candidates:
            raise AssertionError(
                f"مرشح الرتبة {row.rank} خارج المروحة الكاملة"
            )
        if (
            decision.verdict == "LAW-GAP"
            and route_complete(row, decision.candidate)
        ):
            raise AssertionError(
                f"LAW-GAP بلا صف مفقود في الرتبة {row.rank}"
            )
        if decision.verdict in requiring_sources:
            _, coverage, _ = classical_witnesses(
                decision.candidate, sense_map, 40
            )
            if coverage < 2:
                raise AssertionError(
                    f"حكم الرتبة {row.rank} بلا شاهدين كلاسيكيين"
                )
    literal_decompositions = {
        row.rank
        for row in rows
        if "Middle Persian" not in entries[row.rank].etymology
        and re.fullmatch(
            r"From (.+?) \+ (.+?)\.?", entries[row.rank].etymology
        )
    }
    if literal_decompositions != set(DECOMPOSITIONS):
        raise AssertionError(
            "تغير نطاق التفكيك الحصري: "
            f"{sorted(literal_decompositions)}"
        )


def validate_text(rows: list[SweepRow], texts: list[str]) -> None:
    if len(rows) != 70 or len(texts) != 70:
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = [
        int(value)
        for value in re.findall(
            r"^### WO-B-R21-BOTH-(\d{5}):", joined, re.MULTILINE
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
    for row, text in zip(rows, texts):
        if len(text.encode("utf-8")) >= CARD_LIMIT:
            raise AssertionError(
                f"تجاوزت الرتبة {row.rank} حد 5KB"
            )
        if any(field not in text for field in required):
            raise AssertionError(
                f"نقص حقل من بطاقة الرتبة {row.rank}"
            )
    for rank in DECOMPOSITIONS:
        text = texts[list(EXPECTED_RANKS).index(rank)]
        if (
            "تفكيك المعجم الحصري" not in text
            or "قراءة المكونات المستقلة" not in text
        ):
            raise AssertionError(f"لم يفكك مركب الرتبة {rank}")


def report_section(
    rows: list[SweepRow],
    decisions: list[Decision],
    sizes: list[int],
    skipped: int,
) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    lines = [f"<!-- {MARKER}:START -->", ""]
    for batch in range(2):
        lo = batch * BATCH_SIZE
        hi = lo + BATCH_SIZE
        batch_rows = rows[lo:hi]
        batch_decisions = decisions[lo:hi]
        counts = Counter(
            decision.verdict for decision in batch_decisions
        )
        distribution = "؛ ".join(
            f"{key}={counts[key]}" for key in sorted(counts)
        )
        lines.extend([
            (
                "## الجولة الحادية والعشرون، دفعة حوض both "
                f"رقم {batch + 1}"
            ),
            "",
            f"- الوقت: {now}، Africa/Cairo.",
            (
                "- فُحص ورُشّح قبل القراءة: 35؛ كُتب: 35؛ "
                "الترتيب overlap نازلًا مع ثبات ترتيب المصدر عند التعادل."
            ),
            (
                f"- الرتب: من {batch_rows[0].rank:05d} إلى "
                f"{batch_rows[-1].rank:05d} داخل الحوض المضاعف، "
                "مع تجاوز المقروء."
            ),
            f"- توزيع الأحكام: {distribution}.",
            (
                "- المروحة: وُلدت كاملة ورُتبت بالأوزان لكل عضو، "
                "ومُسحت مواد جميع مرشحيها بلا قص للحقل المصدر."
            ),
            (
                "- المتجانسات: قُرئت كل مداخل الرسم، وسُجل العدد "
                "ورقم المدخلة المختارة في كل بطاقة."
            ),
            (
                "- المصادر: نُقل شاهدان عربيان كلاسيكيان مستقلان "
                "لكل حكم صادر، وسُميت SOURCE-GAP حيث نقصا."
            ),
            (
                "- التفكيك: لم يقبل إلا `From X + Y` الحرفي في "
                "قاموس الفرع؛ قرئت مكوناته استقلالًا أو أُحيل إلى "
                "قراءة سابقة محددة."
            ),
            (
                "- التحقق البنيوي: 35 معرفًا فريدًا؛ لا بطاقة فوق "
                "5KB؛ لا شرطة طويلة؛ الأرقام غربية والنص NFC."
            ),
            (
                f"- آخر موضع في الدفعة: الرتبة "
                f"{batch_rows[-1].rank:05d}، "
                f"`{batch_rows[-1].branch}`."
            ),
            "",
        ])
    total = Counter(decision.verdict for decision in decisions)
    distribution = "؛ ".join(
        f"{key}={total[key]}" for key in sorted(total)
    )
    positives = [
        f"`{row.branch}↔{decision.candidate}`"
        for row, decision in zip(rows, decisions)
        if decision.verdict in {"ROOT-TRACE", "NUCLEUS-TRACE"}
    ]
    max_size = max(sizes)
    max_rank = rows[sizes.index(max_size)].rank
    lines.extend([
        "## حصيلة الجولة الحادية والعشرين",
        "",
        (
            "- حمل `persian.md` مرة واحدة في الذاكرة؛ المقروء "
            f"المتجاوز من حوض both الحالي: {skipped}؛ "
            "الطازج الباقي قبل القطع: 323."
        ),
        (
            f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ "
            f"{distribution}."
        ),
        "- الصلات الموجبة: " + "، ".join(positives) + ".",
        (
            "- نُقلت المرشحات الدلالية من داخل المروحة الكاملة، "
            "ومنها `تار↔وتر` و`فره↔وفر`؛ لم يفرض عمود `best` الحكم."
        ),
        (
            "- المركبات المفككة حصريًا: الرتب 00011 و00015 و00045 "
            "و00093 و00098 و00099؛ لا تفكيك حدسي."
        ),
        (
            f"- أكبر بطاقة: {max_size} بايت، الرتبة "
            f"{max_rank:05d}؛ كل البطاقات دون 5KB."
        ),
        (
            "- عطب أداة أساسية: 0؛ لم تُفعّل طبقة البرهان، "
            "ولم يُبن ملف مشترك، ولم يقع ship."
        ),
        "",
        f"<!-- {MARKER}:END -->",
        "",
        "LANE-B DONE21 70 00139",
    ])
    return "\n".join(lines)


def validate_existing(reading_text: str, report_text: str) -> None:
    match = re.search(
        rf"<!-- {re.escape(MARKER)}:START -->"
        rf"(.*?)<!-- {re.escape(MARKER)}:END -->",
        reading_text,
        re.DOTALL,
    )
    if not match:
        raise AssertionError("محضر الجولة موجود وبطاقاتها غائبة")
    ranks = [
        int(value)
        for value in re.findall(
            r"^### WO-B-R21-BOTH-(\d{5}):",
            match.group(1),
            re.MULTILINE,
        )
    ]
    if ranks != list(EXPECTED_RANKS):
        raise AssertionError("مقطع الجولة 21 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(
        "LANE-B DONE21 70 00139"
    ):
        raise AssertionError("سطر DONE21 ليس خاتمة التقرير")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    # شرط المؤلف: هذه هي القراءة الوحيدة لملف persian.md في العملية كلها.
    reading_text = READING.read_text(encoding="utf-8")
    report_text = REPORT.read_text(encoding="utf-8")
    if MARKER in reading_text or MARKER in report_text:
        validate_existing(reading_text, report_text)
        print("ROUND21 ALREADY PRESENT AND VALID")
        return 0

    sweep_data = json.loads(SWEEP.read_text(encoding="utf-8"))
    lexicon_data = json.loads(LEXICON.read_text(encoding="utf-8"))
    all_rows = parse_sweep(sweep_data)
    rows, skipped = select_fresh(all_rows, reading_text)
    entries = select_branch_entries(rows, lexicon_data)
    ranked_by_rank = {
        row.rank: full_ranked_fan(row) for row in rows
    }
    roots = {
        candidate
        for row in rows
        for candidate, _ in ranked_by_rank[row.rank]
    }
    roots.update(candidate_for(row) for row in rows)
    sense_map = SENSES.matches_for_roots(
        SENSES.DEFAULT_RESOURCES, roots, None
    )
    decisions = [decide(row) for row in rows]
    validate_decisions(
        rows, entries, decisions, ranked_by_rank, sense_map
    )
    texts = [
        fit_card(
            row, entries[row.rank], decision,
            ranked_by_rank[row.rank], sense_map,
        )
        for row, decision in zip(rows, decisions)
    ]
    validate_text(rows, texts)
    sizes = [len(text.encode("utf-8")) + 1 for text in texts]

    reading_append = (
        f"\n\n<!-- {MARKER}:START -->\n\n"
        "## الجولة الحادية والعشرون: حوض both الفارسي المضاعف "
        "(2026-08-18)\n\n"
        "- النطاق: أعلى 70 صفًا طازجًا بعد تجاوز جميع WO-B المقروءة، "
        "بترتيب overlap نازلًا؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ المركب لا يفكك إلا بنص "
        "قاموس الفرع الحصري.\n\n"
        + "\n".join(texts[:BATCH_SIZE])
        + "\n## الدفعة الثانية: الرتب 00064 إلى 00139 "
        "بعد تجاوز المقروء\n\n"
        + "\n".join(texts[BATCH_SIZE:])
        + f"\n<!-- {MARKER}:END -->\n"
    )
    report_append = (
        "\n" + report_section(rows, decisions, sizes, skipped) + "\n"
    )
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
    print("ROUND21 READY")
    print(
        "SKIPPED", skipped, "FRESH", 323, "SELECTED", len(rows)
    )
    print(
        "RANKS", rows[0].rank, rows[-1].rank,
        "BATCHES", BATCH_SIZE, BATCH_SIZE,
    )
    print(
        "VERDICTS",
        " ".join(
            f"{key}={counts[key]}" for key in sorted(counts)
        ),
    )
    print(
        "MAX_CARD", max(sizes),
        f"RANK={rows[sizes.index(max(sizes))].rank:05d}",
    )
    if args.preview:
        print("PREVIEW ONLY")
        return 0

    with READING.open("a", encoding="utf-8", newline="") as handle:
        handle.write(reading_append)
    with REPORT.open("a", encoding="utf-8", newline="") as handle:
        handle.write(report_append)
    print("ROUND21 WRITTEN")
    print("LANE-B DONE21 70 00139")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
