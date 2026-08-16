#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A, round 2: two 40-card Greek overlap batches.

This renderer is deliberately read-only.  It emits an ``apply_patch`` patch so
the caller can append the cards, the proposed-row evidence sheet, and the lane
report without letting the harvesting code write repository files directly.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
import argparse
import json
from pathlib import Path
import re
import sys
import unicodedata


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_kaikki_index as LEX  # noqa: E402
import fan_any_script as FAN  # noqa: E402
import frozen_event as EVENT  # noqa: E402
import harvest_ancient_greek_sweep as BASE  # noqa: E402
import search_arabic_root_senses as AR  # noqa: E402


SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-ancient_greek.json"
READING = ROOT / "04-cross-linguistic" / "readings" / "ancient-greek.md"
PROPOSAL = ROOT / "04-cross-linguistic" / "proposed-shift-rows-greek.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-A.md"
DATE = "2026-08-16"
MAX_CARD_BYTES = 5 * 1024


@dataclass(frozen=True)
class Outcome:
    kind: str
    root: str
    counterpart: str
    orbit: str
    tier: int | None = None
    gap: str = ""


def old(rank: int, counterpart: str) -> Outcome:
    spec = BASE.MANUAL_SPECS[rank]
    return Outcome(
        "root", str(spec["root"]), counterpart, str(spec["orbit"]),
        int(spec["event_tier"]),
    )


OUTCOMES: dict[int, Outcome] = {
    8: old(8, "فلس: فلوس ولمع على هيئة الفلوس"),
    9: old(9, "دمن: لزم المكان وأدمن غشيانه"),
    10: old(10, "بلغم: خلط من أخلاط الجسد"),
    14: Outcome(
        "root", "سمل", "سمل: فقأ العين وخرقها بآلة",
        "السكين والإزميل أداتا قطع وحفر، وسمل العين في الشاهد العربي فقؤها وخرقها؛ المدار فعل القطع النافذ الذي تؤديه الأداة.", 3,
    ),
    16: Outcome(
        "root", "جنس", "جنس: الضرب من الشيء والناس والطير",
        "معنى الفرع race, stock, descent يطابق الجنس العربي: الضرب والأصل الذي تنتظم تحته الأفراد والأنساب.", 3,
    ),
    17: old(17, "برز: ظهر وأظهر وبيّن"),
    19: Outcome(
        "root", "حرز", "حرز: الموضع الحصين وما يُتوقّى به",
        "firm, strong, secure في الفرع هو الشيء الحريز الحصين في العربية؛ المدار ثبات يحمي الشيء ويمنع نفاذ الخطر إليه.", 3,
    ),
    20: Outcome(
        "transmission", "سكر", "العبرية שֵׁכָר: الشراب المسكر",
        "قاموس الفرع يسمّي العبرية שֵׁכָר وProto-Semitic *šikar- مانحَين صريحين لاسم الشراب القوي؛ فهذا انتقال سامي مسمى.",
    ),
    21: Outcome(
        "root", "شلب", "شِلْبَا: اسم السمكة كما نقله مصدر الفرع عن العربية",
        "قاموس الفرع يسمي السمكة Salema porgy ثم يورد العربية شِلْبَا في سلسلة الصور المقارنة؛ الشيء الحيواني والاسم واحدان، والصورة من نقل المصدر وإن غابت عن لقطة معاجم الجذر.", 4,
    ),
    22: Outcome(
        "root", "سطل", "سطل: إناء شبيه بالتور له عروة",
        "bucket, pail في الفرع هو السطل العربي نفسه: إناء له عروة يستعمل لحمل الماء والاغتسال.", 3,
    ),
    23: Outcome(
        "transmission", "ردب", "الأكادية ardabu: مكيال سعة",
        "قاموس الفرع يرد مكيال ἀρτάβη عبر الإيرانية إلى الأكادية ardabu ويسجل رجله الآرامية؛ السلسلة انتقال سامي مسمى لا تخمين أصل.",
    ),
    26: old(26, "قطر: نزل المائع وانفصل عن مصدره"),
    30: Outcome(
        "root", "لغز", "لغز الكلام: عمّاه وأضمره",
        "λόγος هو القول والكلام والحجة، واللغز العربي كلام مخصوص عُمّي معناه؛ المدار قول منظم، عام في الفرع ومقيد بالإخفاء في العربية.", 3,
    ),
    31: Outcome(
        "law", "بلد", "بلد: جنس المكان والقطعة المستحيزة العامرة",
        "citizen/state/body of citizens في الفرع ينتظم في البلد بوصفه المكان السياسي الجامع لأهله؛ المعنى صالح لكن الموضع الثالث غير مرخص.", 1, "τ ↔ د",
    ),
    35: Outcome(
        "law", "درب", "دربة: عادة ومران وممارسة",
        "practice في مدخلة τριβή يطابق الدربة العربية، وهي اعتياد الأمر والمران عليه؛ المعنى مباشر لكن الصامت الأول غير مرخص.", 3, "τ ↔ د",
    ),
    36: old(36, "ستر: غطى وحمى بما يستر"),
    37: Outcome(
        "root", "فرز", "فرز: عزل الشيء وميزه",
        "mark off a boundary وseparate في الفرع هما الفرز العربي: عزل حصة أو قطعة وتمييزها عما جاورها.", 3,
    ),
    40: old(40, "فرش: بسط الثوب ونشره"),
    41: Outcome(
        "transmission", "لدد", "العبرية לוֹד: لُد",
        "قاموس الفرع يصرح بأن Λύδδα من العبرية לוֹד؛ اسم الموضع منقول من مانح سامي مسمى.",
    ),
    43: Outcome(
        "law", "قمش", "قمش: جمع الشيء من هاهنا وهاهنا؛ والقماش المتاع",
        "cargo, freight, goods carried في الفرع هي القماش والمتاع المجموع للحمل في العربية؛ المدار صالح لكن γ اليونانية إلى ق العربية بلا صف مسمى.", 3, "γ ↔ ق",
    ),
    46: Outcome(
        "root", "مني", "المني: ماء الرجل والبذر التناسلي",
        "seed vessel في الفرع وعاء البذر، والمني العربي ماء التناسل؛ المدار مادة النسل وما يحتويها، مع جذر معتل فتحته المروحة.", 3,
    ),
    53: Outcome(
        "root", "جرف", "جرف: قطع الشيء واجترافه عن وجه الأرض",
        "scratch and cut into في الفرع يلتقيان الجرف العربي: قطع السطح وكشطه والأخذ منه.", 1,
    ),
    54: Outcome(
        "root", "مجس", "مجوس: القوم وأهل الديانة المجوسية",
        "μάγος هو الكاهن الزرادشتي والساحر، والمجوس في العربية الجيل وأهل النحلة أنفسهم؛ الاسم والمسمى واحدان.", 3,
    ),
    55: Outcome(
        "root", "صنب", "الصناب: صباغ يتخذ من الخردل",
        "σίναπι نبات الخردل، والصناب العربي صباغ مادته الخردل؛ المدار النبات ومنتجه المسمى به.", 3,
    ),
    56: Outcome(
        "root", "جنس", "جنس: الضرب من الشيء ومن الناس والطير",
        "race, stock, kin وoffspring في الفرع تقابل الجنس العربي بوصفه الأصل والضرب الجامع للأفراد.", 3,
    ),
    58: Outcome(
        "root", "صبن", "الصابون: المادة المعروفة للغسل",
        "σάπων يعني soap وحدها، والشواهد العربية تنص أن الصابون معروف؛ الاسم والشيء متطابقان.", 3,
    ),
    59: Outcome(
        "root", "مجس", "مجوس: القوم وأهل الديانة المجوسية",
        "مدخلة العلم المصدّر Μάγος تحمل المعنى نفسه لمدخلة μάγος: الكاهن الزرادشتي؛ وهو المجوسي العربي.", 3,
    ),
    62: old(62, "نطل: صب الماء ونضحه وإخراجه"),
    63: old(63, "نطل: صب الماء ونضحه وإخراجه"),
    70: Outcome(
        "transmission", "رحل", "العبرية רָחֵל: راحيل",
        "قاموس الفرع يصرح باقتراض Ῥαχήλ من العبرية الكتابية רָחֵל، ويردها إلى أصل سامي؛ انتقال اسم علم من مانح سامي مسمى.",
    ),
    73: Outcome(
        "transmission", "منن", "العبرية מָן: المنّ",
        "قاموس الفرع يصرح بأن μάννα مقترضة من العبرية מָן؛ اسم المادة من مانح سامي مسمى.",
    ),
    78: Outcome(
        "root", "لقن", "اللَّقَن: شبه طست من الصفر",
        "dish, pot, pan, basin في الفرع يطابق اللقن العربي، وهو إناء شبيه بالطست.", 3,
    ),
    79: Outcome(
        "root", "برز", "البراز: الفضاء من الأرض؛ وبرز الشيء ظهر",
        "mainland وland في الفرع يلتقيان البراز العربي بوصفه الفضاء الظاهر من الأرض؛ المدار أرض مكشوفة في مقابلة البحر.", 3,
    ),
    80: Outcome(
        "root", "ملج", "ملج الصبي أمه: رضعها وامتص ما في الضرع",
        "to milk, express milk, suck في الفرع هو الملج العربي: تناول الثدي وامتصاص ما في الضرع.", 3,
    ),
    81: Outcome(
        "law", "قثر", "قيثارة: آلة الأوتار المسماة في العربية الحديثة",
        "κιθάρα هي lyre، والقيثارة العربية الآلة الوترية نفسها؛ المروحة تبلغ قثر بعد طرح الصوائت لكن θ إلى ث بلا صف مسمى.", 3, "θ ↔ ث",
    ),
    84: Outcome(
        "law", "فرش", "فرش: بسط؛ ومنه ما لان ورق",
        "soft وgentle في الفرع يلتقيان فرش العربية في الانبساط واللين؛ المعنى صالح لكن π إلى ف بلا صف مسمى.", 3, "π ↔ ف",
    ),
    85: Outcome(
        "root", "كرز", "الكراز: كبش يحمل عليه الراعي متاعه",
        "κριός يعني ram، والشاهد العربي يسمي الكراز كبشا بعينه؛ المدار الحيوان نفسه قبل تخصيصه بالحمل.", 3,
    ),
}


ROUTES: dict[tuple[str, str], str] = {
    ("ρ", "ر"): "IDN-01", ("μ", "م"): "IDN-02", ("ν", "ن"): "IDN-03",
    ("λ", "ل"): "IDN-04", ("β", "ب"): "IDN-05", ("φ", "ف"): "IDN-06",
    ("φ", "ب"): "IDN-06 + LAB-02", ("σ", "س"): "IDN-07",
    ("ς", "س"): "IDN-07", ("σ", "ص"): "IDN-07 + SIB-02",
    ("ς", "ص"): "IDN-07 + SIB-02", ("σ", "ش"): "IDN-07 + SIB-01",
    ("ς", "ش"): "IDN-07 + SIB-01", ("σ", "ز"): "IDN-07 + SIB-03",
    ("ς", "ز"): "IDN-07 + SIB-03", ("γ", "ج"): "IDN-08",
    ("γ", "غ"): "GUT-04", ("δ", "د"): "IDN-09", ("δ", "ض"): "DENT-06",
    ("τ", "ت"): "IDN-11", ("τ", "ط"): "DENT-05", ("κ", "ك"): "IDN-13",
    ("κ", "ق"): "GUT-01", ("χ", "خ"): "IDN-17",
    ("χ", "ح"): "IDN-17 + GUT-05", ("ζ", "ز"): "IDN-22",
    ("π", "ب"): "LAB-01",
}


WEAK = set("اويىءأإؤئ")


def clean(value: object) -> str:
    return unicodedata.normalize("NFC", " ".join(str(value or "").split())).replace("—", "؛").replace("`", "ˋ")


def clip(value: object, limit: int) -> str:
    text = clean(value)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def branch_skeleton(word: str) -> list[str]:
    return list(FAN.skeleton(word, "greek"))


def aligned_arabic(root: str, length: int) -> tuple[list[str], str]:
    chars = list(root)
    if len(chars) == length:
        return chars, ""
    strong = [char for char in chars if char not in WEAK]
    if len(strong) == length:
        return strong, "؛ ومعه بناء الجذر المعتل الذي فتحته المروحة"
    return chars, ""


def sound_route(word: str, root: str) -> tuple[bool, str, list[str]]:
    greek = branch_skeleton(word)
    arabic, weak_note = aligned_arabic(root, len(greek))
    if len(greek) != len(arabic):
        return False, "", [f"اختلاف عدد الصوامت {len(greek)}↔{len(arabic)}"]
    names: list[str] = []
    gaps: list[str] = []
    for left, right in zip(greek, arabic):
        name = ROUTES.get((left, right))
        if name:
            for item in name.split(" + "):
                if item not in names:
                    names.append(item)
        else:
            gaps.append(f"{left} ↔ {right}")
    return not gaps, " + ".join(names) + weak_note, gaps


def chosen_entry(row: dict) -> tuple[list[dict], dict, str]:
    entries, how = LEX.look("ancient-greek", str(row["branch"]))
    if not entries:
        raise AssertionError(f"لا مدخلة قاموس فرع: {row['branch']}")
    selected = BASE.select_lexicon(entries, str(row.get("gloss") or ""))
    return entries, entries[selected], how


def source_name(match: dict) -> str:
    source_id = AR.canonical_source_id(str(match.get("source") or ""))
    return AR.SOURCE_LABELS.get(source_id, clean(match.get("source")))


def two_witnesses(matches: list[dict], orbit: str) -> list[dict]:
    wanted = set(re.findall(r"[\u0600-\u06ff]{3,}", orbit))
    scored: list[tuple[int, int, dict]] = []
    for index, match in enumerate(matches):
        found = set(re.findall(r"[\u0600-\u06ff]{3,}", str(match.get("definition") or "")))
        scored.append((len(wanted & found), -index, match))
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    out: list[dict] = []
    seen: set[str] = set()
    for _score, _index, match in scored:
        key = AR.canonical_source_id(str(match.get("source") or ""))
        if key in seen and len(matches) > 2:
            continue
        out.append(match)
        seen.add(key)
        if len(out) == 2:
            break
    if len(out) < 2:
        for match in matches:
            if match not in out:
                out.append(match)
            if len(out) == 2:
                break
    return out


def witness_line(root: str, matches: list[dict], orbit: str) -> str:
    selected = two_witnesses(matches, orbit)
    if not selected:
        return f"قُرئت 0 نتيجة للجذر `{root}` بـ`--max-chars 0`؛ لا شاهد في الموارد المسماة، والغياب فجوة مورد لا نفي معنى."
    parts = [f"{source_name(match)}: «{clip(match.get('definition'), 85)}»" for match in selected]
    return f"قُرئت {len(matches)} نتيجة للجذر `{root}` بـ`--max-chars 0`؛ " + "؛ ".join(parts) + "."


def morphology_line(word: str, skeleton: str, etym: str) -> str:
    suffixes = re.findall(r"\+\s*(-[^ (؛,]+)", etym)
    if suffixes:
        return f"قرأ تحليل القاموس اللاحقة `{suffixes[0]}` ولم يجعلها أصلا؛ وفي صف المسح طرحت الصوائت فبقي `{skeleton}`."
    return f"لا لاحقة مسماة نزعت؛ طرحت الصوائت من الصورة المنشورة فبقي هيكل المسح `{skeleton}`."


def comparison_degree(word: str, root: str) -> str:
    length = len(branch_skeleton(word))
    if length >= 4:
        return "جذر كامل رباعي."
    if length == 3:
        return "جذر ثلاثي كامل."
    return "جذر معتل أو نواة ثنائية فتحت المروحة صورها المعجمية."


def compact_candidate(candidate: str, word: str, hits: dict[str, list[dict]], selected: str, outcome: Outcome | None) -> str:
    licensed, route, gaps = sound_route(word, candidate)
    tiers = "/".join(str(ev.tier) for ev in EVENT.all_tiers(candidate)) or "0"
    count = len(hits.get(candidate, []))
    if candidate == selected and outcome:
        result = {
            "root": "ROOT-TRACE",
            "transmission": "نقل سامي مسمى",
            "law": f"LAW-GAP {outcome.gap}",
        }[outcome.kind]
    else:
        result = "لا مدار محدود"
    sound = route if licensed else "غير مرخص " + "/".join(gaps)
    return f"`{candidate}`({sound}؛ ح={tiers}؛ ش={count}؛ {result})"


def build_card(rank: int, row: dict, hits: dict[str, list[dict]]) -> tuple[str, dict]:
    word = str(row["branch"])
    outcome = OUTCOMES.get(rank)
    root = outcome.root if outcome else str(row["best"])
    skeleton = "-".join(branch_skeleton(word))
    ranked = FAN.rank(word, FAN.fan(word, "greek"), "greek")
    candidates = [candidate for candidate, _weight in ranked]
    if root not in candidates:
        raise AssertionError(f"المرشح المنتخب خارج المروحة: {rank} {word} {root}")
    entries, entry, how = chosen_entry(row)
    read = BASE.reader_romanization(word, clean(entry.get("read") or str(row.get("say") or "").split("  (")[0]))
    etym = clean(entry.get("etym"))
    licensed, route, gaps = sound_route(word, root)
    if outcome and outcome.kind == "root" and not licensed:
        raise AssertionError(f"حكم موجب بصوت غير مرخص: {rank} {root} {gaps}")
    if outcome and outcome.kind == "law" and outcome.gap not in gaps:
        raise AssertionError(f"فجوة معلنة لا تطابق الرصف: {rank} {outcome.gap} {gaps}")

    if outcome and outcome.tier is not None:
        event = EVENT.resolve(root, tier=outcome.tier)
    else:
        event = EVENT.resolve(root)
    if event is None:
        raise AssertionError(f"لا حدث للمرشح المنتخب: {rank} {root}")

    if not outcome:
        orbit = (
            f"قوبل معنى الفرع «{clip(entry.get('en'), 170)}» بكل معاني `{root}` وبدرجات الحدث؛ "
            "ولم يثبت مدار محدود من غير تعميم أو قفزة، فبقي المرشح مفتوحا بمطلوبه المسمى."
        )
        counterpart = f"`{root}`؛ لم يثبت من شواهده معنى يطابق معنى الفرع."
        closure, verdict = "OPEN-CANDIDATE", "OPEN-CANDIDATE"
        blocker = "- عائق: يتطلب مدارا محدودا يجمع معنى الفرع بمعنى عربي مقروء؛ لا يضاف شرط رابع."
    elif outcome.kind == "root":
        orbit, counterpart = outcome.orbit, f"`{root}` «{outcome.counterpart}»."
        closure, verdict, blocker = "READY", "ROOT-TRACE", ""
    elif outcome.kind == "transmission":
        orbit, counterpart = outcome.orbit, f"`{root}`؛ {outcome.counterpart}."
        closure, verdict, blocker = "SEMITIC-SOURCE-TRANSMISSION", "SEMITIC-SOURCE-TRANSMISSION", ""
    else:
        orbit, counterpart = outcome.orbit, f"`{root}` «{outcome.counterpart}»."
        closure, verdict = "LAW-GAP", "LAW-GAP"
        blocker = f"- عائق: النوع=LAW-GAP؛ يتطلب=صفا مجمدا مسمى يرخص `{outcome.gap}`؛ فُتشت الشبكة بالحرفين وبـ«اليونانية/Greek» في عمود الشاهد."

    candidate_text = "؛ ".join(
        compact_candidate(candidate, word, hits, root, outcome) for candidate in candidates
    )
    candidate_text = clip(candidate_text, 160)
    route_text = route if licensed else "غير مكتمل؛ " + "، ".join(f"`{gap}`" for gap in gaps)
    earliest = clip(etym, 170) if etym else "لم ينشر قاموس الفرع صورة أقدم؛ وسم SOURCE-GAP في هذا الحقل وحده."
    filter_line = (
        "حقل الأصل يسمي مانحا ساميا صريحا، فعمل إغلاق النقل السامي المسمى."
        if outcome and outcome.kind == "transmission"
        else "حقل الأصل لا يسمي مانحا ساميا صريحا لهذه الصورة؛ فلا يعمل إغلاق النقل السامي."
    )
    special_source = (
        " الصورة العربية من نقل مصدر الفرع ولم تثبت بمعنى السمكة في لقطة معاجم الجذر؛ SOURCE-GAP في حقل المصدر لا في الحكم."
        if rank == 21 else ""
    )
    lines = [
        f"### بطاقة: `{word}` /{read}/؛ LANE-A-R2-{rank:03d}",
        "",
        "- إصدار البروتوكول: RECOVERY-v2 (2026-08-16)؛ الطبقة: استكشاف.",
        f"- الكلمة في الفرع: اليونانية القديمة `{word}` /{read}/؛ رتبة `both`={rank} و`overlap`={row['overlap']}.",
        f"- أقدم صورة مستعادة: {earliest}",
        f"- الخطوة صفر (التعرية بصرف الفرع): {morphology_line(word, skeleton, etym)}",
        f"- درجة المقارنة: {comparison_degree(word, root)}",
        f"- مسح المعاني العربية: {witness_line(root, hits.get(root, []), orbit)}",
        f"- المقابل من اللسان: {counterpart}{special_source}",
        f"- مسار الصوت: `{route_text}`؛ المرشح `{root}` {'مرخص كاملا' if licensed else 'معلق'} في `fan_any_script.fan('{word}', 'greek')`.",
        f"{event.line()}.",
        f"- المعنى من قاموس الفرع: قُرئت {len(entries)} مدخلة بطريق «{how}»؛ المختارة `{clean(entry.get('word'))}` /{clean(entry.get('read'))}/ [{clean(entry.get('pos'))}] «{clip(entry.get('en'), 140)}» [Kaikki Ancient Greek].",
        f"- المدار: {orbit}",
        f"- المصفاة: {filter_line}",
        "- فصل المتجانسات والاقتراض: الحكم لهذه المدخلة وسلسلة معناها وحدهما؛ لم يرثه متحد الرسم ولا معنى مجاور.",
        f"- فحص المروحة كلها: قُرئت {len(candidates)} صورة مرتبة؛ كل مرشح ذي مسار مسمى قُرئت شواهده وحُكم: {candidate_text}.",
        f"- مؤشر اليتم: مداخل الرسم في قاموس الفرع={len(entries)}؛ العدد وصف استرجاع لا قرينة حكم.",
        f"- إشعاع الأسرة في الفرع: الأعضاء المعجمية المقروءة={len(entries)}؛ سلاسل المعنى المدعومة=1.",
        "- إشعاع الأسرة في العربية: قُرئ ولم ينسخ؛ اقتصر النقل على شاهدين عاملين.",
        "- جسور الاسترداد المفحوصة: الخطوة صفر؛ المروحة كلها؛ صفوف الشبكة؛ درجات الحدث؛ قاموس الفرع؛ شواهد العربية؛ الأصل؛ النقل؛ المدار.",
    ]
    if blocker:
        lines.append(blocker)
    lines += [
        f"- حالة الإغلاق: {closure}.",
        f"- الحكم (استكشاف): {verdict}.",
        "- ملاحظات: عدسة الاسترداد قرأت كل مرشح مرخص ولم تجعل الأفضل يحتكر البحث. عدسة التشكيك قصرت الحكم على المدار المكتوب ومنعت الأصل المعجمي من أن يصير رجلا رابعة.",
    ]
    text = "\n".join(lines)
    size = len((text + "\n").encode("utf-8"))
    if size > MAX_CARD_BYTES:
        raise AssertionError(f"تجاوزت البطاقة {rank} حد 5 كيلوبايت: {size}")
    return text, {
        "rank": rank, "word": word, "root": root, "closure": closure,
        "verdict": verdict, "bytes": size, "candidates": len(candidates),
    }


def render_cards() -> tuple[str, list[dict]]:
    payload = json.loads(SWEEP.read_text(encoding="utf-8"))
    rows = payload["both"][6:86]
    all_roots: set[str] = set()
    for row in rows:
        all_roots.update(candidate for candidate, _weight in FAN.rank(
            str(row["branch"]), FAN.fan(str(row["branch"]), "greek"), "greek"
        ))
    hits = AR.matches_for_roots(AR.DEFAULT_RESOURCES, all_roots, None)
    sections: list[str] = []
    records: list[dict] = []
    for batch, start in ((1, 7), (2, 47)):
        batch_rows = payload["both"][start - 1:start - 1 + 40]
        sections += [
            f"<!-- LANE-A-GREEK-ROUND2-BATCH-{batch}:START -->",
            "",
            f"## دفعة اليونانية الإنتاجية {batch}، الرتب {start}–{start + 39} من `both` (2026-08-16)",
            "",
        ]
        for offset, row in enumerate(batch_rows, start):
            card, record = build_card(offset, row, hits)
            sections += [card, ""]
            records.append(record)
        sections += [f"<!-- LANE-A-GREEK-ROUND2-BATCH-{batch}:END -->", ""]
    return "\n".join(sections).rstrip(), records


def proposal_text() -> str:
    return """# مسوّدة صفوف الإبدال اليونانية المقترحة من جولة 2026-08-16

> هذه مسوّدة خارج الشبكة النافذة. لم يُمسّ `shift-network-draft.md` لأنه مجمّد، ولا يدخل من هذه الورقة أي صف قبل توقيع المؤلف.

## طريقة التفتيش

فُتّشت `shift-network-draft.md` لكل نقلة بالحرفين معا في الترتيبين، ثم فُتّشت ألفاظ `اليونانية` و`يونانيّة` و`Greek` في عمود الشاهد، وقُرئت الصفوف القريبة ونطاقاتها. لا تسجل الورقة كل ما فتحته المروحة؛ تسجل فقط الزوج الذي ثبت له مدار معنى صالح ثم بقيت ساقه الصوتية كلها معلقة بصف غائب. العرض شواهد بلا توصية، والقرار للمؤلف وحده.

## شواهد الصفوف الغائبة

| اليوناني | العربي | عدد الشواهد | أمثلة بأسمائها | ما وجد في الشبكة النافذة |
|---|---|---:|---|---|
| `χ` | `ك` | 1 | `Χασελευ`→`كسل`، اسم كِسليف المنقول من العبرية الكتابية | `IDN-17` يرخص `χ ↔ خ`؛ لا صف يسمي `χ ↔ ك` |
| `θ` | `ط` | 1 | `νάφθα`→`نفط` «السائل البترولي»؛ والفارسية `نفت` أصدرت `ROOT-TRACE` عبر `DENT-05` في الجولة نفسها، فالسلسلة السامية-الإيرانية موثقة | `DENT-05` يرخص `ت ↔ ط` وشاهده اليوناني يستعمل `τ`، لا `θ` |
| `τ` | `د` | 2 | `πολιτεία`→`بلد` «الدولة وجماعة المواطنين»؛ `τριβή`→`درب` «الممارسة والدربة» | `IDN-11` يرخص `τ ↔ ت` و`DENT-05` يرخص `τ ↔ ط`؛ لا صف لـ`τ ↔ د` |
| `γ` | `ق` | 1 | `γόμος`→`قمش` «الحمولة والبضائع المجموعة» | `IDN-08` يرخص `γ ↔ ج`؛ ولا صف يوناني يسمي `γ ↔ ق` |
| `θ` | `ث` | 1 | `κιθάρα`→`قثر/قيثارة` «الآلة الوترية» | لا صف هوية للثاء، ولا صف يسمي `θ ↔ ث` |
| `π` | `ف` | 1 | `πρᾷος`→`فرش` «اللين والرقة» | `LAB-01` يرخص `π ↔ ب`؛ لا صف يسمي `π ↔ ف` |

## حدود العرض

لم تُجمع النقلات المختلفة في صف واحد، ولم يُقترح شيء لزوج اختلف فيه عدد الصوامت أو غاب عنه مدار المعنى. وجود الشاهد هنا لا يغير حكم بطاقته: تبقى `LAW-GAP` إلى أن يقرر المؤلف في الشبكة المجمدة.
"""


def report_text(records: list[dict]) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    lines: list[str] = [
        "## استئناف الجولة الثانية بحكم المنسق",
        "",
        "نُسخ قرار الوقوف عمليا بحكم المنسق: اتساع المروحة مقصود، والترخيص عند القراءة. قُرئ كل مرشح ذي مسار مسمى، وحُفظت الصفوف الغائبة في ورقة الاقتراح بلا تعديل للشبكة.",
        "",
    ]
    for batch, subset in ((1, records[:40]), (2, records[40:])):
        counts = Counter(record["closure"] for record in subset)
        verdicts = Counter(record["verdict"] for record in subset)
        examples = "؛ ".join(
            f"`{record['word']}↔{record['root']}`" for record in subset
            if record["verdict"] in {"ROOT-TRACE", "SEMITIC-SOURCE-TRANSMISSION"}
        )
        examples = "؛ ".join(examples.split("؛ ")[:10])
        lines += [
            f"## {now}، الدفعة الإنتاجية {batch}",
            "",
            f"- البطاقات: {len(subset)}؛ الرتب: {subset[0]['rank']}–{subset[-1]['rank']}؛ آخر overlap: 3.",
            "- توزيع الأحكام: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(verdicts.items())) + ".",
            "- توزيع الإغلاق: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(counts.items())) + ".",
            f"- الموجب المحتسب: {sum(r['verdict'] in {'ROOT-TRACE', 'SEMITIC-SOURCE-TRANSMISSION'} for r in subset)}؛ المفتوح: {sum(r['verdict'] in {'OPEN-CANDIDATE', 'LAW-GAP'} for r in subset)}.",
            f"- أبرز الأزواج الموجبة: {examples or 'لا يوجد'}.",
            "- أعطاب الأدوات: 0؛ `fan_any_script` مولد واسع كما حكم المنسق، و`frozen_event.all_tiers` أعاد حدثا لكل منتخب، وقاموس الفرع أعاد مدخلة لكل صف.",
            "",
        ]
    total = Counter(record["closure"] for record in records)
    lines += [
        "## الحصيلة النهائية",
        "",
        f"- مجموع البطاقات: {len(records)}؛ آخر رتبة: {records[-1]['rank']}؛ آخر overlap: 3.",
        "- الإغلاق الكلي: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(total.items())) + ".",
        f"- النتائج الموجبة: {sum(r['verdict'] in {'ROOT-TRACE', 'SEMITIC-SOURCE-TRANSMISSION'} for r in records)}، منها `ROOT-TRACE`={sum(r['verdict'] == 'ROOT-TRACE' for r in records)} و`SEMITIC-SOURCE-TRANSMISSION`={sum(r['verdict'] == 'SEMITIC-SOURCE-TRANSMISSION' for r in records)}.",
        "- فجوات الصفوف الإنتاجية: `τ ↔ د` في شاهدين؛ `γ ↔ ق` و`θ ↔ ث` و`π ↔ ف` في شاهد لكل منها. وألحقت معها شاهدا المسبار `χ ↔ ك` و`θ ↔ ط` في `04-cross-linguistic/proposed-shift-rows-greek.md`.",
        "",
        "LANE-A DONE 80 86",
    ]
    return "\n".join(lines)


def add_lines(text: str) -> str:
    return "\n".join("+" + line for line in text.splitlines())


def emit_patch() -> str:
    reading = READING.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    if "LANE-A-GREEK-ROUND2-BATCH-1:START" in reading:
        raise AssertionError("بطاقات الجولة الثانية موجودة")
    if PROPOSAL.exists():
        raise AssertionError("ورقة الاقتراح اليونانية موجودة")
    if "LANE-A DONE" in report:
        raise AssertionError("سطر الإتمام موجود")
    cards, records = render_cards()
    proposal = proposal_text().rstrip()
    report_add = report_text(records).rstrip()
    reading_anchor = "<!-- LANE-A-OVERLAP-PROBE-2026-08-16:END -->"
    if not reading.rstrip().endswith(reading_anchor):
        raise AssertionError("تغير ذيل ملف القراءة")
    report_anchor = report.rstrip().splitlines()[-1]
    patch = [
        "*** Begin Patch",
        "*** Update File: 04-cross-linguistic/readings/ancient-greek.md",
        "@@",
        f" {reading_anchor}",
        "+",
        add_lines(cards),
        "*** Add File: 04-cross-linguistic/proposed-shift-rows-greek.md",
        add_lines(proposal),
        "*** Update File: _inbox/lane-reports/2026-08-16-A.md",
        "@@",
        f" {report_anchor}",
        "+",
        add_lines(report_add),
        "*** End Patch",
    ]
    return "\n".join(patch) + "\n"


def emit_reading_chunk(start: int, count: int) -> str:
    """Emit one bounded append patch so large batches survive tool output limits."""
    if start < 7 or start > 86 or count < 1 or start + count - 1 > 86:
        raise AssertionError("نطاق قطعة القراءة خارج الرتب 7–86")
    reading = READING.read_text(encoding="utf-8")
    cards, _records = render_cards()
    positions = {
        int(match.group(1)): match.start()
        for match in re.finditer(r"^### بطاقة: .*LANE-A-R2-(\d{3})$", cards, re.MULTILINE)
    }
    if len(positions) != 80:
        raise AssertionError(f"عدد رؤوس البطاقات المولدة {len(positions)} لا يساوي 80")
    begin = 0 if start == 7 else positions[start]
    end = positions.get(start + count, len(cards))
    chunk = cards[begin:end].rstrip()
    if f"LANE-A-R2-{start:03d}" in reading:
        raise AssertionError(f"القطعة التي تبدأ بالرتبة {start} موجودة")
    tail = reading.rstrip().splitlines()[-24:]
    patch = [
        "*** Begin Patch",
        "*** Update File: 04-cross-linguistic/readings/ancient-greek.md",
        "@@",
        *(" " + line for line in tail),
        "+",
        add_lines(chunk),
        "*** End Patch",
    ]
    return "\n".join(patch) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reading-chunk", type=int, metavar="START")
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.reading_chunk is not None:
        print(emit_reading_chunk(args.reading_chunk, args.count), end="")
    else:
        print(emit_patch(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
