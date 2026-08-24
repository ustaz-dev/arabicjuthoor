# -*- coding: utf-8 -*-
"""المسار B، الجولة 23: دفعتان من حوض both الفارسي بدءا من الرتبة 261."""

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

import harvest_persian_round22 as P  # noqa: E402

H = P.H
READING = ROOT / "04-cross-linguistic" / "readings" / "persian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-B.md"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-persian.json"
LEXICON = ROOT / "data" / "branch-lexicons" / "persian.json"
RAW_LEXICON = ROOT / "Resources" / "persian" / "kaikki.org-dictionary-Persian.jsonl"
MARKER = "LANE-B-PERSIAN-ROUND23-2026-08-24"
BATCH_SIZE = 35
CARD_LIMIT = 5120

EXPECTED_RANKS = (
    261, 262, 263, 264, 265, 266, 267, 268, 269, 270, 271, 272, 273,
    274, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284, 285, 286,
    287, 288, 289, 290, 292, 293, 294, 295, 296, 298, 299, 302, 305,
    306, 309, 310, 312, 313, 315, 316, 317, 318, 319, 320, 322, 323,
    324, 326, 327, 328, 329, 330, 331, 332, 333, 334, 335, 337, 338,
    339, 340, 341, 342, 343,
)

CANDIDATE_OVERRIDES = {
    261: "طرو", 263: "ولي", 270: "وبل", 272: "كون", 274: "جني",
    277: "باج", 278: "سور", 280: "تف", 285: "بد", 286: "وحد",
    287: "وحد", 293: "وجن", 310: "قز", 312: "زيج", 318: "خز",
    319: "جول", 322: "بول", 323: "سرو", 324: "صور", 326: "خور",
    328: "جيش", 340: "قلل", 341: "تبب",
}

VERDICTS = {
    261: "ROOT-TRACE", 262: "LAW-GAP", 263: "LAW-GAP",
    264: "OPEN-CANDIDATE", 265: "OPEN-CANDIDATE",
    266: "OPEN-CANDIDATE", 267: "LAW-GAP", 268: "OPEN-CANDIDATE",
    269: "LAW-GAP", 270: "ROOT-TRACE", 271: "OPEN-CANDIDATE",
    272: "OPEN-CANDIDATE", 273: "OPEN-CANDIDATE", 274: "ROOT-TRACE",
    275: "OPEN-CANDIDATE", 276: "OPEN-CANDIDATE", 277: "LAW-GAP",
    278: "OPEN-CANDIDATE", 279: "OPEN-CANDIDATE",
    280: "OPEN-CANDIDATE", 281: "LAW-GAP", 282: "OPEN-CANDIDATE",
    283: "OPEN-CANDIDATE", 284: "OPEN-CANDIDATE", 285: "ROOT-TRACE",
    286: "ROOT-TRACE", 287: "ROOT-TRACE", 288: "COMPOUND-BOUNDARY",
    289: "LAW-GAP", 290: "COMPOUND-BOUNDARY",
    292: "OPEN-CANDIDATE", 293: "ROOT-TRACE", 294: "OPEN-CANDIDATE",
    295: "OPEN-CANDIDATE", 296: "LAW-GAP", 298: "OPEN-CANDIDATE",
    299: "COMPOUND-BOUNDARY", 302: "OPEN-CANDIDATE",
    305: "OPEN-CANDIDATE", 306: "OPEN-CANDIDATE", 309: "LAW-GAP",
    310: "LAW-GAP", 312: "SOURCE-GAP", 313: "OPEN-CANDIDATE",
    315: "LAW-GAP", 316: "OPEN-CANDIDATE", 317: "OPEN-CANDIDATE",
    318: "OPEN-CANDIDATE", 319: "OPEN-CANDIDATE",
    320: "OPEN-CANDIDATE", 322: "ROOT-TRACE", 323: "SOURCE-GAP",
    324: "ROOT-TRACE", 326: "ROOT-TRACE", 327: "OPEN-CANDIDATE",
    328: "ROOT-TRACE", 329: "OPEN-CANDIDATE", 330: "LAW-GAP",
    331: "COMPOUND-BOUNDARY", 332: "LAW-GAP", 333: "LAW-GAP",
    334: "MORPHOLOGY-GAP", 335: "LAW-GAP", 337: "OPEN-CANDIDATE",
    338: "LAW-GAP", 339: "COMPOUND-BOUNDARY", 340: "SOURCE-GAP",
    341: "ROOT-TRACE", 342: "OPEN-CANDIDATE", 343: "OPEN-CANDIDATE",
}

SPECIAL_ORBITS = {
    261: (
        "الفرع يسمي الرطوبة والبلل، والعين والمحكم يثبتان طراوة الشيء "
        "وطروه حتى يكون طريا؛ نقطة الرطوبة والطراوة واحدة."
    ),
    270: (
        "الفرع يسمي الحمل والعبء، والصحاح والمفردات يثبتان في وبل الثقل "
        "والوبالة؛ نقطة الحمل الثقيل واحدة."
    ),
    274: (
        "الفرع يسمي الجريمة والذنب، والصحاح والمحكم يثبتان جنى الذنب "
        "والجناية؛ نقطة الإثم والجريمة واحدة."
    ),
    285: (
        "الفرع أداة وجوب بمعنى لا بد، والمحيط والعين يثبتان لا بد بمعنى "
        "لا محالة ولا مفر؛ نقطة الإلزام واحدة."
    ),
    286: (
        "الفرع يسمي الذات نفسها، والصحاح والمفردات يثبتان الوحدة والانفراد؛ "
        "المدار هو الذات المفردة التي لا غيرها."
    ),
    287: (
        "الفرع ضمير للذات والملك الذاتي، والصحاح والمفردات يثبتان المنفرد "
        "ووحده؛ نقطة رجوع الشيء إلى نفسه واحدة."
    ),
    293: (
        "الفرع يسمي الخد، والصحاح ولسان العرب يثبتان الوجنة لما ارتفع من "
        "الخدين؛ العضو نفسه هو المدار."
    ),
    312: (
        "الفرع يسمي الحبل والزيج، ولسان العرب يثبت الزيج خيط البناء ويصرح "
        "بأنه فارسي معرب؛ لم يرد شاهد كلاسيكي مستقل ثان."
    ),
    322: (
        "الفرع يسمي الذاكرة والعقل، والصحاح والمحكم في مادة بول يثبتان "
        "البال للقلب والخاطر؛ نقطة الذهن الباطن واحدة."
    ),
    323: (
        "الفرع يسمي شجر السرو، وتاج العروس يثبت السرو شجرا معروفا، وأصل "
        "الفرع يسمي السريانية ثم الأكادية؛ لم يكتمل شاهد عربي مستقل ثان."
    ),
    324: (
        "الفرع يسمي القرن، والصحاح والعين يثبتان الصور للقرن؛ المسمى "
        "العضوي نفسه هو المدار."
    ),
    326: (
        "الفرع يسمي السهولة والدناءة، والصحاح والمصباح يثبتان الخور للضعف "
        "والانكسار والخوارة للين والسهولة؛ نقطة الرخاوة واحدة."
    ),
    328: (
        "الفرع يسمي غليان السائل، والصحاح ولسان العرب يثبتان جاشت القدر "
        "تجيش إذا غلت؛ حركة الغليان نفسها هي المدار."
    ),
    340: (
        "الفرع يسمي الرأس وأعلى الشيء، والصحاح يثبت القلة لأعلى كل شيء "
        "ولرأس الإنسان؛ الموضع مطابق، لكن لم يرد شاهد كلاسيكي مستقل ثان."
    ),
    341: (
        "الفرع يسمي الفساد والخراب، والصحاح والمحكم يثبتان التباب للخسران "
        "والهلاك؛ نقطة الخراب المؤدي إلى الهلاك واحدة."
    ),
}

BLOCKED_BOUNDARIES = {
    288: "قال Kaikki: By surface analysis، لا From X + Y مستقلا.",
    290: "قال Kaikki: By surface analysis، لا From X + Y مستقلا.",
    299: "قال Kaikki: Contraction ... and the direct-object particle، بلا سطر From X + Y.",
    339: "قال Kaikki: Equivalent to X + Y، لا From X + Y.",
}
EXACT_DECOMPOSITIONS = {331}
COMPONENT_FAN_COUNT = 60

EXPECTED_ENTRY_INDEX = {
    261: 3073, 262: 3147, 263: 3261, 264: 3313, 265: 3314,
    266: 3394, 267: 3398, 268: 3626, 269: 3713, 270: 3745,
    271: 3845, 272: 3982, 273: 3987, 274: 4060, 275: 4079,
    276: 4082, 277: 4236, 278: 4263, 279: 4406, 280: 4447,
    281: 4450, 282: 4453, 283: 4455, 284: 4506, 285: 4585,
    286: 4617, 287: 4618, 288: 4645, 289: 4650, 290: 5325,
    292: 5516, 293: 5517, 294: 5583, 295: 5629, 296: 5670,
    298: 5695, 299: 6100, 302: 6432, 305: 6723, 306: 6763,
    309: 7007, 310: 7205, 312: 7303, 313: 7333, 315: 7527,
    316: 8177, 317: 8463, 318: 8581, 319: 8605, 320: 8684,
    322: 8741, 323: 8849, 324: 8850, 326: 9018, 327: 9118,
    328: 9182, 329: 9371, 330: 9590, 331: 9671, 332: 9887,
    333: 10066, 334: 10306, 335: 10336, 337: 10395, 338: 10953,
    339: 11101, 340: 11132, 341: 11192, 342: 11234, 343: 11287,
}

H.TARGET_NEEDLES.update({
    "طرو": ("الطَّراوة", "طَرُوَ الشُّيءُ", "طَرُوَ الشَّيْءُ"),
    "وبل": ("الثِقلُ", "الثّقيل", "الثقل"),
    "جني": ("جَنَى الذَّنب", "جِنايَة", "أَذْنَبَ ذَنْبًا"),
    "بد": ("لا [بُد]", "لا مَحَالَة", "ليس لهذا الأمر"),
    "وحد": ("الوَحْدَةُ: الانفراد", "الوحدة: الانفراد", "المُنْفَرِدُ"),
    "وجن": ("الوَجْنَةُ: ما ارتفع", "ما ارتفع من الخَدَّيْنِ", "لَحْمِ خَدِّهِ"),
    "زيج": ("خَيْطُ البَنَّاءِ", "فارسي معرّب"),
    "بول": ("والبالُ: القلبُ", "والبَالُ الخَاطِرُ", "الْبَالُ الْقَلْبُ"),
    "سرو": ("شَجَرٌ م", "شَجَرٌ مَعْروفٌ"),
    "صور": ("الصورُ: القَرْنُ", "الصُّور: القَرْن", "القَرْنُ"),
    "خور": ("ضَعُفَ وانكسر", "خَارَ يَخُورُ ضَعُفَ", "الخَوَرُ رَخاوةٌ"),
    "جيش": ("جاشَتِ القِدْرُ", "جاشت القدر", "جاشت القِدْر"),
    "قلل": ("القلة: أعلى الجبل", "رأس الإنسان قُلّةٌ", "قُلَّةِ الطِفْلِ"),
    "تبب": ("الخُسْرانُ والهَلاكُ", "التَّبُّ: الخَسارُ", "الْهَلَاكِ"),
})

WITNESS_PRIORITY = dict(P.WITNESS_PRIORITY)
WITNESS_PRIORITY.update({
    "طرو": ("kitab_al_ayn", "al_muhkam"),
    "وبل": ("al_sihah", "al_mufradat"),
    "جني": ("al_muhkam", "al_sihah"),
    "بد": ("al_muhit", "kitab_al_ayn"),
    "وحد": ("al_sihah", "al_mufradat"),
    "وجن": ("al_sihah", "lisan"),
    "زيج": ("lisan",),
    "بول": ("al_sihah", "al_muhkam"),
    "سرو": ("taj_al_arus",),
    "صور": ("al_sihah", "kitab_al_ayn"),
    "خور": ("al_sihah", "al_misbah"),
    "جيش": ("al_sihah", "lisan"),
    "قلل": ("al_sihah", "lisan"),
    "تبب": ("al_sihah", "al_muhkam"),
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
        if source_id not in H.CLASSICAL_PRIORITY or not definition.strip():
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


H.classical_witnesses = classical_witnesses


def select_fresh(
    rows: list[H.SweepRow], reading_text: str
) -> tuple[list[H.SweepRow], int, int]:
    pairs = H.read_pairs(reading_text)
    pair_read = {row.rank for row in rows if H.already_read(row, pairs)}
    id_read = {
        int(value) for value in re.findall(
            r"^### WO-B-R(?:21|22|23)-BOTH-(\d{5}):",
            reading_text,
            re.MULTILINE,
        )
    }
    read = pair_read | id_read
    fresh = [row for row in rows if row.rank >= 261 and row.rank not in read]
    fresh.sort(key=lambda row: (-row.overlap, row.rank))
    selected = fresh[:70]
    if len(rows) != 494:
        raise AssertionError(f"حوض both ليس 494: {len(rows)}")
    if tuple(row.rank for row in selected) != EXPECTED_RANKS:
        raise AssertionError("تغير ترتيب السبعين الطازجة من الرتبة 261")
    return selected, len(read), len(fresh)


def select_branch_entries(
    rows: list[H.SweepRow], lexicon: dict
) -> tuple[dict[int, H.BranchEntry], dict[str, list[tuple[int, dict]]]]:
    grouped: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for index, entry in enumerate(lexicon["entries"]):
        grouped[H.clean(entry.get("word") or "")].append((index, entry))
    selected: dict[int, H.BranchEntry] = {}
    for row in rows:
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


def is_exact_from_plus(etymology: str) -> bool:
    return bool(re.fullmatch(r"From [^.]+ \+ [^.]+\.", H.clean(etymology)))


def validate_components(
    grouped: dict[str, list[tuple[int, dict]]]
) -> tuple[str, str]:
    raw_poush = None
    with RAW_LEXICON.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line_number == 10688:
                raw_poush = json.loads(line)
                break
    if not raw_poush or H.clean(raw_poush.get("word") or "") != "پوش":
        raise AssertionError("غاب مكون پوش من سطر Kaikki الخام 10688")
    gloss = H.clean(raw_poush["senses"][0]["glosses"][0])
    if gloss != "present stem form of پوشیدن":
        raise AssertionError("تغير معنى مكون پوش")
    suffixes = grouped.get("ـیه", [])
    if len(suffixes) != 1 or suffixes[0][0] != 15386:
        raise AssertionError("تغيرت مدخلة مكون ـیه")
    suffix_gloss = H.clean(suffixes[0][1].get("en") or "")
    return gloss, suffix_gloss


def decomposition_line(row: H.SweepRow, entry: H.BranchEntry) -> str | None:
    if row.rank != 331:
        return None
    if not is_exact_from_plus(entry.etymology):
        raise AssertionError("غاب سطر From X + Y الحصري للرتبة 331")
    if "پوش" not in entry.etymology or "ـیه" not in entry.etymology:
        raise AssertionError("تغير مكونا الرتبة 331")
    return (
        f"- تفكيك Kaikki الحصري: «{H.clip(entry.etymology, 300)}».\n"
        "- قراءة المكونات المستقلة: `پوش` /puš/، سطر Kaikki الخام 10688، "
        "جذع حاضر من `پوشیدن` بمعنى الارتداء والتغطية؛ قُرئت مروحته ذات "
        f"{COMPONENT_FAN_COUNT} مرشحا كاملة ولم يثبت مدار عربي مباشر، "
        "فحكمه OPEN-CANDIDATE. `ـیه` /-iyye/، `entries[15386]`، لاحقة "
        "اشتقاقية مقترضة من العربية؛ حكمها MORPHOLOGY-GAP."
    )


def decide(row: H.SweepRow) -> H.Decision:
    candidate = candidate_for(row)
    verdict = VERDICTS[row.rank]
    if row.rank in SPECIAL_ORBITS:
        orbit = SPECIAL_ORBITS[row.rank]
    elif row.rank in BLOCKED_BOUNDARIES:
        orbit = (
            "ظهرت بنية متعددة الأجزاء في خبر الأصل، لكن صيغتها لا تطابق "
            "سطر From X + Y الحصري؛ أوقف الحكم عند الحد ولم يخترع مكون."
        )
    elif row.rank in EXACT_DECOMPOSITIONS:
        orbit = (
            "قاموس Kaikki نفسه أعطى سطر From X + Y؛ قُرئ المكونان كل على "
            "حدة، وبقي حكم الصورة المجموعة COMPOUND-BOUNDARY."
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
    decision: H.Decision,
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
        f"### WO-B-R23-BOTH-{row.rank:05d}: `{row.branch}` /{entry.reading}/، رتبة overlap {row.rank}",
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
            f"`entries[{entry.global_index}]`؛ لم تؤخذ الأولى آليا."
        ),
        (
            f"- أقدم صورة مستعادة: «{H.clip(entry.etymology, etym_limit)}» "
            "[data/branch-lexicons/persian.json]."
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
            "- الخطوة صفر: لم يقبل تفكيك سطحي أو مكافأة أو عطفا؛ وقف الحكم COMPOUND-BOUNDARY بلا مكونات مخترعة.",
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
            f"العدد {len(ranked)}: {P.formatted_fan(ranked)}."
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
        f"- ملاحظات العدستين: استرداد حتى القرار، وتشكيك مقصور على العضو؛ الجولة 23، الرتبة {row.rank:05d}.",
        f"- حالة الإغلاق: {decision.state}.",
        f"- الحكم (استكشاف): {decision.verdict}.",
    ])
    return "\n".join(lines) + "\n"


H.make_card = make_card


def validate_decisions(
    rows: list[H.SweepRow],
    entries: dict[int, H.BranchEntry],
    decisions: list[H.Decision],
    ranked_by_rank: dict[int, tuple[tuple[str, float], ...]],
    sense_map: dict[str, list[dict]],
) -> None:
    if set(VERDICTS) != set(EXPECTED_RANKS):
        raise AssertionError("جدول الأحكام لا يغطي الرُتب السبعين")
    source_verdicts = {"ROOT-TRACE", "NUCLEUS-TRACE"}
    exact = {
        row.rank for row in rows if is_exact_from_plus(entries[row.rank].etymology)
    }
    if exact != EXACT_DECOMPOSITIONS:
        raise AssertionError(f"تغيرت أسطر From X + Y الحصرية: {sorted(exact)}")
    for row, decision in zip(rows, decisions):
        candidates = {candidate for candidate, _ in ranked_by_rank[row.rank]}
        if decision.candidate not in row.candidates_found or decision.candidate not in candidates:
            raise AssertionError(f"مرشح الرتبة {row.rank} خارج المروحة الكاملة")
        complete = H.route_complete(row, decision.candidate)
        _, coverage, _ = classical_witnesses(decision.candidate, sense_map, 50)
        if decision.verdict == "LAW-GAP" and complete:
            raise AssertionError(f"LAW-GAP بلا صف مفقود في الرتبة {row.rank}")
        if decision.verdict in source_verdicts:
            if not complete:
                raise AssertionError(f"حكم موجب بلا مسار مكتمل في الرتبة {row.rank}")
            if coverage < 2:
                raise AssertionError(f"حكم موجب بلا شاهدين في الرتبة {row.rank}")
        if decision.verdict == "SOURCE-GAP" and coverage >= 2:
            raise AssertionError(f"SOURCE-GAP مع شاهدين دلاليين في الرتبة {row.rank}")
    decomposition_line(
        next(row for row in rows if row.rank == 331), entries[331]
    )


def validate_text(rows: list[H.SweepRow], texts: list[str]) -> None:
    if len(rows) != 70 or len(texts) != 70:
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = [
        int(value) for value in re.findall(
            r"^### WO-B-R23-BOTH-(\d{5}):", joined, re.MULTILINE
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
    exact_card = texts[list(EXPECTED_RANKS).index(331)]
    if "تفكيك Kaikki الحصري" not in exact_card or "قراءة المكونات المستقلة" not in exact_card:
        raise AssertionError("لم تقرأ مكونات الرتبة 331 استقلالا")
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
            f"## الجولة الثالثة والعشرون، دفعة حوض both رقم {batch + 1}", "",
            f"- الوقت: {now}، Africa/Cairo.",
            "- فُحص ورُشح قبل القراءة: 35؛ كُتب: 35؛ الترتيب overlap نازلا مع ثبات ترتيب المصدر عند التعادل.",
            (
                f"- الرتب: من {batch_rows[0].rank:05d} إلى {batch_rows[-1].rank:05d} "
                "داخل الحوض المضاعف، مع تجاوز المقروء والتكرار المفحوص."
            ),
            f"- توزيع الأحكام: {distribution}.",
            "- المروحة: وُلدت كاملة ورُتبت بالأوزان لكل عضو، ومُسحت مواد جميع مرشحيها بلا قص للحقل المصدر.",
            "- المتجانسات: قُرئت كل مداخل الرسم، وسُجل العدد ورقم المدخلة المختارة في كل بطاقة.",
            "- المصادر: نُقل شاهدان دلاليان مستقلان لكل ROOT-TRACE، وسُميت SOURCE-GAP حيث نقصا.",
            "- التفكيك: لم يقبل إلا سطر From X + Y الحرفي من Kaikki؛ قُرئ كل مكون مقبول وحده، وما عداه COMPOUND-BOUNDARY.",
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
    gaps = [
        f"`{row.branch}↔{decision.candidate}`"
        for row, decision in zip(rows, decisions)
        if decision.verdict == "SOURCE-GAP"
    ]
    max_size = max(sizes)
    max_rank = rows[sizes.index(max_size)].rank
    lines.extend([
        "## حصيلة الجولة الثالثة والعشرين", "",
        (
            f"- حمل `persian.md` مرة واحدة في الذاكرة؛ المقروء المتجاوز في حوض both={skipped}؛ "
            f"الطازج من الرتبة 00261 فما فوق قبل القطع={fresh_count}."
        ),
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- صلات الجذر والنواة الموجبة: " + "، ".join(traces) + ".",
        "- فجوات الشاهد الدلالي المباشر: " + "، ".join(gaps) + ".",
        "- التفكيك الحصري: الرتبة 00331 فقط بسطر `From پوش + ـیه`؛ قُرئ `پوش` و`ـیه` استقلالا.",
        "- حدود مركب بلا تفكيك مؤهل: الرتب 00288 و00290 و00299 و00339؛ لم يقبل تحليل سطحي أو Equivalent to أو عطفا.",
        "- انضباط الأداة: `پیل↔فيل` بقي LAW-GAP لغياب صف پ↔ف، و`کژ↔قز` بقي LAW-GAP لغياب صف ژ↔ز.",
        f"- أكبر بطاقة: {max_size} بايت، الرتبة {max_rank:05d}؛ كل البطاقات دون 5KB.",
        "- عطب أداة أساسية: 0؛ لم تُفعّل طبقة البرهان، ولم يُبن ملف مشترك، ولم يقع ship، ولم يستعمل git.",
        "", f"<!-- {MARKER}:END -->", "", "LANE-B DONE23 70 00343",
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
            r"^### WO-B-R23-BOTH-(\d{5}):", match.group(1), re.MULTILINE
        )
    ]
    if ranks != list(EXPECTED_RANKS):
        raise AssertionError("مقطع الجولة 23 الموجود غير مكتمل")
    if not report_text.rstrip().endswith("LANE-B DONE23 70 00343"):
        raise AssertionError("سطر DONE23 ليس خاتمة التقرير")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    reading_text = READING.read_text(encoding="utf-8")
    report_text = REPORT.read_text(encoding="utf-8")
    if MARKER in reading_text or MARKER in report_text:
        validate_existing(reading_text, report_text)
        print("ROUND23 ALREADY PRESENT AND VALID")
        print("LANE-B DONE23 70 00343")
        return 0

    all_rows = H.parse_sweep(json.loads(SWEEP.read_text(encoding="utf-8")))
    rows, skipped, fresh_count = select_fresh(all_rows, reading_text)
    lexicon = json.loads(LEXICON.read_text(encoding="utf-8"))
    entries, grouped = select_branch_entries(rows, lexicon)
    component_gloss, suffix_gloss = validate_components(grouped)
    if not component_gloss or not suffix_gloss:
        raise AssertionError("لم تكتمل قراءة مكوني پوشیه")

    ranked_by_rank = {row.rank: H.full_ranked_fan(row) for row in rows}
    component_ranked = tuple(
        H.FAN.rank("پوش", H.FAN.fan("پوش", "persian"), "persian")
    )
    if len(component_ranked) != COMPONENT_FAN_COUNT:
        raise AssertionError("تغيرت مروحة مكون پوش")
    roots = {
        candidate
        for row in rows
        for candidate, _ in ranked_by_rank[row.rank]
    }
    roots.update(candidate_for(row) for row in rows)
    roots.update(candidate for candidate, _ in component_ranked)
    sense_map = H.SENSES.matches_for_roots(H.SENSES.DEFAULT_RESOURCES, roots, None)
    decisions = [decide(row) for row in rows]
    validate_decisions(rows, entries, decisions, ranked_by_rank, sense_map)
    texts = [
        H.fit_card(
            row, entries[row.rank], decision, ranked_by_rank[row.rank], sense_map
        )
        for row, decision in zip(rows, decisions)
    ]
    validate_text(rows, texts)
    sizes = [len(card.encode("utf-8")) + 1 for card in texts]

    reading_append = (
        f"\n\n<!-- {MARKER}:START -->\n\n"
        "## الجولة الثالثة والعشرون: حوض both الفارسي المضاعف (2026-08-24)\n\n"
        "- النطاق: السبعون الطازجة التالية من الرتبة 00261 فما فوق بعد تجاوز المقروء والتكرار؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ المركب لا يفكك إلا بسطر Kaikki الحرفي `From X + Y`، وكل مكون مقبول يقرأ وحده.\n\n"
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
    print("ROUND23 READY")
    print("SKIPPED", skipped, "FRESH_GE261", fresh_count, "SELECTED", len(rows))
    print("RANKS", rows[0].rank, rows[-1].rank, "BATCHES", BATCH_SIZE, BATCH_SIZE)
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("MAX_CARD", max(sizes), f"RANK={rows[sizes.index(max(sizes))].rank:05d}")
    if args.preview:
        print("PREVIEW ONLY")
        return 0

    with READING.open("a", encoding="utf-8", newline="") as handle:
        handle.write(reading_append)
    with REPORT.open("a", encoding="utf-8", newline="") as handle:
        handle.write(report_append)
    print("ROUND23 WRITTEN")
    print("LANE-B DONE23 70 00343")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
