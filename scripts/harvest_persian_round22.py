# -*- coding: utf-8 -*-
"""المسار B، الجولة 22: دفعتان من الحوض الفارسي المضاعف بعد الرتبة 139."""

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

import harvest_persian_round21 as H  # noqa: E402

READING = ROOT / "04-cross-linguistic" / "readings" / "persian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-B.md"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-persian.json"
LEXICON = ROOT / "data" / "branch-lexicons" / "persian.json"
RAW_LEXICON = ROOT / "Resources" / "persian" / "kaikki.org-dictionary-Persian.jsonl"
MARKER = "LANE-B-PERSIAN-ROUND22-2026-08-18"
BATCH_SIZE = 35
CARD_LIMIT = 5120

EXPECTED_RANKS = (
    147, 148, 155, 158, 159, 170, 173, 174, 179, 181, 183, 186, 192,
    195, 196, 197, 198, 200, 201, 202, 203, 204, 205, 206, 207, 208,
    209, 211, 212, 214, 215, 216, 217, 218, 219, 220, 221, 222, 223,
    224, 225, 226, 227, 228, 229, 230, 233, 234, 235, 236, 237, 238,
    239, 240, 241, 242, 245, 246, 247, 248, 249, 250, 251, 252, 253,
    254, 255, 256, 257, 260,
)

CANDIDATE_OVERRIDES = {
    147: "لكد", 170: "قسس", 183: "جرش", 186: "فسد", 207: "زور",
    214: "حبب", 219: "خير", 222: "بهي", 227: "بزي",
    234: "رخ", 235: "دين", 236: "جيل", 239: "جوز", 247: "غور",
    252: "طيب", 253: "جام", 254: "وقر", 257: "صكك",
}

VERDICTS = {
    147: "ROOT-TRACE", 148: "LAW-GAP", 155: "OPEN-CANDIDATE",
    158: "COMPOUND-BOUNDARY", 159: "COMPOUND-BOUNDARY",
    170: "SEMITIC-SOURCE-TRANSMISSION", 173: "COMPOUND-BOUNDARY",
    174: "LAW-GAP", 179: "COMPOUND-BOUNDARY", 181: "LAW-GAP",
    183: "OPEN-CANDIDATE", 186: "LAW-GAP", 192: "LAW-GAP",
    195: "SOURCE-GAP", 196: "OPEN-CANDIDATE", 197: "OPEN-CANDIDATE",
    198: "OPEN-CANDIDATE", 200: "LAW-GAP", 201: "OPEN-CANDIDATE",
    202: "OPEN-CANDIDATE", 203: "LAW-GAP", 204: "LAW-GAP",
    205: "OPEN-CANDIDATE", 206: "COMPOUND-BOUNDARY", 207: "ROOT-TRACE",
    208: "OPEN-CANDIDATE", 209: "LAW-GAP", 211: "OPEN-CANDIDATE",
    212: "OPEN-CANDIDATE", 214: "OPEN-CANDIDATE", 215: "SOURCE-GAP",
    216: "COMPOUND-BOUNDARY", 217: "LAW-GAP", 218: "LAW-GAP",
    219: "LOANWORD-NON-ARABIC-TO-ARABIC", 220: "OPEN-CANDIDATE",
    221: "SOURCE-GAP", 222: "ROOT-TRACE", 223: "OPEN-CANDIDATE",
    224: "LAW-GAP", 225: "OPEN-CANDIDATE", 226: "LAW-GAP",
    227: "SOURCE-GAP", 228: "OPEN-CANDIDATE", 229: "OPEN-CANDIDATE",
    230: "OPEN-CANDIDATE", 233: "LAW-GAP",
    234: "LOANWORD-NON-ARABIC-TO-ARABIC", 235: "ROOT-TRACE",
    236: "ROOT-TRACE", 237: "SOURCE-GAP", 238: "OPEN-CANDIDATE",
    239: "LOANWORD-NON-ARABIC-TO-ARABIC", 240: "LAW-GAP",
    241: "LAW-GAP", 242: "OPEN-CANDIDATE", 245: "LAW-GAP",
    246: "LAW-GAP", 247: "LAW-GAP", 248: "OPEN-CANDIDATE",
    249: "SOURCE-GAP", 250: "OPEN-CANDIDATE", 251: "SOURCE-GAP",
    252: "ROOT-TRACE", 253: "SOURCE-GAP", 254: "ROOT-TRACE",
    255: "OPEN-CANDIDATE", 256: "LAW-GAP", 257: "LAW-GAP",
    260: "OPEN-CANDIDATE",
}

SPECIAL_ORBITS = {
    147: (
        "الفرع يسمّي الركلة والدفع الراجع، ولسان العرب وتاج العروس يثبتان "
        "أن لكده ضربه أو دفعه، بل ينقل التاج استعمال العامة للرجل؛ "
        "نقطة الحركة الصادمة واحدة."
    ),
    170: (
        "الفرع يسمّي الكاهن النصراني، وأصله المنشور يرده إلى السريانية "
        "qaššīšā؛ والصحاح والمفردات يثبتان القس والقسيس رئيسا عابدا من "
        "رؤساء النصارى؛ أغلقت المصفاة الجسر السامي المسمى."
    ),
    183: (
        "قاموس الفرع يذكر أن گوارش الفارسية الوسطى انتقلت إلى العربية "
        "في صورة جوارش، لكن هذه الصورة ليست مرشحا في المروحة الحالية؛ "
        "أما جرش العربي فيسمي الحك والدق لا الدواء أو الهضم مباشرة، "
        "فلم يورث خبر الأصل حكما خارج الحوض."
    ),
    207: (
        "الفرع يسمّي الكذب والباطل، والمحكم ولسان العرب ينصان على أن الزور "
        "الكذب؛ حفظ الجذر الأجوف صامتي ز ور ونقطة المعنى نفسها."
    ),
    219: (
        "الفرع يسمّي القثاء، والصحاح ولسان العرب يثبتان الخيار للقتاء "
        "وينصان على أنه ليس بعربي؛ مع أصل فارسي أوسط في قاموس الفرع، "
        "فهذا نقل فارسي إلى العربية لا بسط إرث."
    ),
    222: (
        "الفرع يسمّي الجيد الممتاز والأفضل، وأساس البلاغة والمحكم يثبتان "
        "بهي الشيء لحسنه وروعته؛ نقطة الحسن والامتياز واحدة."
    ),
    227: (
        "الفرع يسمّي الباز والصقر، والمرشح بزي يثبت البازي في شاهد "
        "كلاسيكي واحد فقط؛ لم يُستكمل شاهد ثان فلا يصدر حكم نقل."
    ),
    234: (
        "الرخ هو حجر الشطرنج نفسه في الفرع والعربية؛ العين والمحيط "
        "يثبتانه ويصفانه بأنه من كلام العجم أو عجمي، فالمسار نقل مسمى."
    ),
    235: (
        "الفرع يسمّي الدين، والعين والمفردات يثبتان الدين للطاعة "
        "والشريعة والملة؛ الصورة والمعنى مباشران مع حفظ الجذر الأجوف."
    ),
    236: (
        "الفرع يسمّي جماعة من البلدان أو الناس، والعين ولسان العرب "
        "يثبتان الجيل لكل صنف أو أمة من الناس؛ نقطة الجماعة البشرية واحدة."
    ),
    239: (
        "الفرع يسمّي الجوز المأكول، والصحاح والعين يثبتانه ويصرح الصحاح "
        "بأنه فارسي معرب وأصله كوز؛ أُغلق مسار النقل خارج بسط الإرث."
    ),
    252: (
        "الفرع يسمّي الجيد والمستحسن، والعين والصحاح يثبتان الطيب خلاف "
        "الخبيث وما لذ وزكا؛ نقطة الجودة والاستحسان واحدة."
    ),
    253: (
        "الفرع يسمّي الكأس والزجاج، والمرشح جام مطابق صورة ومعنى، لكن "
        "الموارد المسماة لم تعط شاهدين عربيين كلاسيكيين مستقلين."
    ),
    254: (
        "الفرع يسمّي الأصم، والصحاح ولسان العرب يثبتان وقر الأذن أي "
        "ثقل سمعها أو صمت؛ نقطة ذهاب السمع واحدة."
    ),
    257: (
        "الفرع يسمّي الوثيقة القانونية، والصحاح والمصباح يثبتان الصك "
        "الكتاب الفارسي المعرب؛ لكن چ↔ص خارج مثال صين المرخص حصرا، "
        "فبقيت الصلة فجوة قانون ولم تستعمل شاهدا."
    ),
}

DECOMPOSITIONS = {
    158: (
        "گزار", "ـه",
        "`گزاردن`، المدخلة 9779، التعبير والتفسير والأداء، والمعجم يسمي "
        "`گزار` جذع الحاضر؛ `ـه`، المدخلة 7112، لاحقة اشتقاقية",
        "`گزار`: MORPHOLOGY-GAP لأنه جذع حاضر مسمى لا مدخلة مستقلة؛ "
        "`ـه`: MORPHOLOGY-GAP."
    ),
    159: (
        "پشت", "ـی",
        "`پشت`، المدخلة 1674، الظهر والخلف؛ `ـی`، المدخلة 6328، "
        "لاحقة وصف ونسبة",
        "`پشت↔بسط`: OPEN-CANDIDATE بعد قراءة المروحة والشاهدين؛ "
        "`ـی`: MORPHOLOGY-GAP."
    ),
    173: (
        "دول", "ـچه",
        "`دول`، المدخلة 4039، الدلو؛ `ـچه`، المدخلة 7513، لاحقة تصغير",
        "`دول`: مرجع الجولة 21، الرتبة 00055، "
        "SEMITIC-SOURCE-TRANSMISSION؛ `ـچه`: MORPHOLOGY-GAP."
    ),
    179: (
        "دست", "ـی",
        "`دست`، المدخلة 1138، اليد والذراع؛ `ـی`، المدخلة 6328، "
        "لاحقة وصف ونسبة؛ التفكيك وارد بعد خبر الفارسية الوسطى",
        "`دست`: مرجع الجولة 21، الرتبة 00120، OPEN-CANDIDATE؛ "
        "`ـی`: MORPHOLOGY-GAP."
    ),
    206: (
        "گل", "ـی",
        "`گل`، المدخلة 365، الزهرة والورد؛ `ـی`، المدخلة 6328، "
        "لاحقة وصف ونسبة",
        "`گل`: مرجع WO-B-OPEN-COMP-00027، OPEN-CANDIDATE؛ "
        "`ـی`: MORPHOLOGY-GAP."
    ),
    216: (
        "پای", "ـان",
        "`پای`، سطر Kaikki الخام 4626، صورة بديلة من `پا`، والمدخلة "
        "156 تسمي الرجل والقدم؛ قُرئت مداخل `ـان` الثلاث 10303-10305",
        "`پای`: MORPHOLOGY-GAP لأن التعرية ترده إلى صامت واحد؛ "
        "`ـان`: MORPHOLOGY-GAP."
    ),
}

H.EXPECTED_RANKS = EXPECTED_RANKS
H.CANDIDATE_OVERRIDES = CANDIDATE_OVERRIDES
H.VERDICTS = VERDICTS
H.SPECIAL_ORBITS = SPECIAL_ORBITS
H.DECOMPOSITIONS = DECOMPOSITIONS
H.TARGET_NEEDLES.update({
    "لكد": ("لَكَدَه", "لَكْداً", "ضَرَبَه", "دَفَعَه"),
    "قسس": ("القَسُّ أيضاً", "القِسُّ", "القِسِّيسُ"),
    "زور": ("والزُّورُ: الكَذِب", "والزُّور: الكذب والباطل", "الزُّورُ الْكَذِب"),
    "خير": ("الخيار: الثقاء", "نبات يشبه القِثَّاءَ", "ليس بعربي"),
    "بهي": ("شيء بهي", "بَهِىَ", "حسنه وروعته"),
    "بزي": ("كالبازي", "البازي"),
    "رخ": ("الرُّخُّ من أدوات الشطرنج", "الرخ معروف عجمي", "كلام العجم"),
    "دين": ("الدِّينُ يقال للطاعة", "والدِّينُ جمعه الأديانُ", "الدِّينُ كالملّة"),
    "جيل": ("الجِيل", "كل صِنْف من الناس", "كل صنف من الناس"),
    "جوز": ("الجوز فارسي", "الجَوْزُ الْمَأْكُول", "فارسي مُعَرَّب"),
    "طيب": ("الطَيِّب: خلاف الخبيث", "طابَ", "لَذَّ أو زَكَا"),
    "وقر": ("الوَقْرُ بالفتح", "ثِقَلٌ في الأُذن", "صَمَّتْ"),
    "صكك": ("والصك: كتاب", "الصَّكُّ الْكِتَاب", "فارسيٌّ معرّب"),
})

WITNESS_PRIORITY = {
    "لكد": ("lisan", "taj_al_arus"),
    "قسس": ("al_sihah", "al_mufradat"),
    "زور": ("al_muhkam", "lisan"),
    "خير": ("al_sihah", "lisan"),
    "بهي": ("al_muhkam", "asas_al_balagha"),
    "رخ": ("kitab_al_ayn", "al_muhit"),
    "دين": ("al_mufradat", "kitab_al_ayn"),
    "جيل": ("kitab_al_ayn", "lisan"),
    "جوز": ("al_sihah", "kitab_al_ayn"),
    "طيب": ("kitab_al_ayn", "al_sihah"),
    "وقر": ("al_sihah", "lisan"),
}


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
        definition = str(item.get("definition") or "")
        if source_id not in H.CLASSICAL_PRIORITY or not definition.strip():
            continue
        incumbent = by_source.get(source_id)
        hit_count = sum(needle in definition for needle in needles)
        incumbent_hits = (
            sum(needle in str(incumbent.get("definition") or "") for needle in needles)
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
            H.targeted_excerpt(str(item.get("definition") or ""), candidate, quote_limit),
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


def candidate_for(row: H.SweepRow) -> str:
    return CANDIDATE_OVERRIDES.get(row.rank, row.best)


def select_fresh(rows: list[H.SweepRow], reading_text: str) -> tuple[list[H.SweepRow], int, int]:
    pairs = H.read_pairs(reading_text)
    pair_read = {row.rank for row in rows if H.already_read(row, pairs)}
    id_read = {
        int(value) for value in re.findall(
            r"^### WO-B-R(?:21|22)-BOTH-(\d{5}):", reading_text, re.MULTILINE
        )
    }
    read = pair_read | id_read
    fresh = [row for row in rows if row.rank >= 140 and row.rank not in read]
    fresh.sort(key=lambda row: (-row.overlap, row.rank))
    selected = fresh[:70]
    if len(rows) != 494:
        raise AssertionError(f"حوض both ليس 494: {len(rows)}")
    if tuple(row.rank for row in selected) != EXPECTED_RANKS:
        raise AssertionError("تغير ترتيب السبعين التالية بعد الرتبة 139")
    return selected, len(read), len(fresh)


def raw_rank_204() -> H.BranchEntry:
    with RAW_LEXICON.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line_number == 535:
                raw = json.loads(line)
                if H.clean(raw.get("word") or "") != "چار":
                    break
                gloss = H.clean(raw["senses"][0]["glosses"][0])
                return H.BranchEntry(
                    global_index=535, homograph_index=1, homograph_count=1,
                    word="چار", reading="čār / čâr", pos=H.clean(raw["pos"]),
                    gloss=gloss,
                    etymology=H.clean(
                        raw.get("etymology_text")
                        or "See the etymology of the corresponding lemma form."
                    ),
                )
    raise AssertionError("غاب سطر Kaikki الخام 535 للرتبة 204")


def select_branch_entries(rows: list[H.SweepRow], lexicon: dict) -> dict[int, H.BranchEntry]:
    grouped: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for index, entry in enumerate(lexicon["entries"]):
        grouped[H.clean(entry.get("word") or "")].append((index, entry))
    selected: dict[int, H.BranchEntry] = {}
    for row in rows:
        candidates = grouped.get(row.branch, [])
        if not candidates:
            if row.rank != 204:
                raise AssertionError(f"لا مدخلة فرع للرسم {row.branch}")
            selected[row.rank] = raw_rank_204()
            continue
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
            etymology=H.clean(entry.get("etym") or "فجوة اشتقاق في لقطة الفرع."),
        )
    expected = {
        148: 6216, 155: 9002, 170: 11250, 179: 12440, 192: 3,
        196: 223, 200: 336, 201: 365, 207: 560, 214: 949, 219: 1089,
        221: 1118, 222: 1120, 223: 1130, 224: 1131, 227: 1326,
        234: 1551, 235: 1561, 239: 1855, 247: 2154, 248: 2155,
        251: 2327, 252: 2329, 253: 2440, 254: 2726, 257: 2901,
    }
    for rank, index in expected.items():
        if selected[rank].global_index != index:
            raise AssertionError(f"انزلق متجانس الرتبة {rank}: {selected[rank].global_index}")
    return selected


def decomposition_line(row: H.SweepRow, entry: H.BranchEntry) -> str | None:
    if row.rank not in DECOMPOSITIONS:
        return None
    left, right, detail, judgments = DECOMPOSITIONS[row.rank]
    etymology = H.clean(entry.etymology)
    if row.rank in {158, 159, 173, 206, 216}:
        if "+" not in etymology or left not in etymology or right not in etymology:
            raise AssertionError(f"تغير تفكيك المعجم للرتبة {row.rank}")
    elif row.rank == 179:
        if "newly formed from دست" not in etymology or "+ ـی" not in etymology:
            raise AssertionError("تغير تفكيك دستی القاموسي")
    return (
        f"- تفكيك المعجم الحصري: «{H.clip(entry.etymology, 300)}»؛ {detail}.\n"
        f"- قراءة المكونات المستقلة: {judgments}"
    )


def formatted_fan(ranked: tuple[tuple[str, float], ...]) -> str:
    if len(ranked) > 100:
        return "،".join(candidate for candidate, _ in ranked)
    return H.formatted_fan(ranked)


H.decomposition_line = decomposition_line


def decide(row: H.SweepRow) -> H.Decision:
    candidate = candidate_for(row)
    verdict = VERDICTS[row.rank]
    if row.rank in SPECIAL_ORBITS:
        orbit = SPECIAL_ORBITS[row.rank]
    elif verdict == "COMPOUND-BOUNDARY":
        orbit = (
            "المعجم نفسه يفكك الصورة إلى مكونين؛ حكم المركب وصفي، "
            "وكل مكون قُرئ استقلالا أو أُحيل إلى بطاقة سابقة محددة."
        )
    elif verdict == "SOURCE-GAP":
        orbit = (
            f"قُرئ معنى الفرع «{row.gloss}»، ولم يكتمل شاهدان عربيان "
            f"كلاسيكيان مستقلان للمادة `{candidate}` بهذا المعنى."
        )
    else:
        orbit = (
            f"الفرع يسمّي «{row.gloss}»؛ وبعد قراءة شواهد `{candidate}` "
            "لم تتحد نقطة المعنى اتحادا مباشرا، فلا يصنع تداخل المسح وحده مدارا."
        )
    if verdict == "LAW-GAP":
        obstacle = (
            "رجل الصوت غير مكتملة بصف مسمى؛ بقي المرشح فجوة قانون "
            "ولم يصدر حكم موجب."
        )
    elif verdict == "SOURCE-GAP":
        obstacle = "لم يكتمل شاهدان عربيان كلاسيكيان مستقلان؛ غياب المورد لا ينفي اللسان."
    elif verdict == "OPEN-CANDIDATE":
        obstacle = "الصوت قابل للرصف، لكن رجل المعنى المباشر لم تثبت بعد قراءة الشاهدين والمتجانسات."
    elif verdict == "COMPOUND-BOUNDARY":
        obstacle = "حد المركب مثبت في حقل الاشتقاق؛ الحكم النهائي للمكونات، لا للصورة المجموعة."
    elif verdict in {"SEMITIC-SOURCE-TRANSMISSION", "LOANWORD-NON-ARABIC-TO-ARABIC"}:
        obstacle = "المعنى والصورة حاضران، لكن المصفاة سمت اتجاه تماس؛ أُغلق خارج بسط الإرث المشترك."
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
    match_count, classical_count, witnesses = H.classical_witnesses(
        decision.candidate, sense_map, quote_limit
    )
    component = decomposition_line(row, entry)
    entry_ref = (
        "سطر Kaikki الخام 535؛ فجوة التصدير المختصر موسومة"
        if row.rank == 204 else f"entries[{entry.global_index}]"
    )
    lines = [
        f"### WO-B-R22-BOTH-{row.rank:05d}: `{row.branch}` /{entry.reading}/، رتبة overlap {row.rank}",
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
            f"{entry_ref}، بالنطق والمعنى المثبتين؛ لم تؤخذ الأولى آليا."
        ),
        (
            f"- أقدم صورة مستعادة: «{H.clip(entry.etymology, etym_limit)}» "
            + (
                "[Resources/persian/kaikki.org-dictionary-Persian.jsonl]."
                if row.rank == 204 else "[data/branch-lexicons/persian.json]."
            )
        ),
    ]
    if component:
        lines.extend([
            component,
            "- الخطوة صفر: لم يقارن المركب وحدة جذرية؛ دخل كل مكون بعد التفكيك القاموسي الصريح وحده.",
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
            f"العدد {len(ranked)}: {formatted_fan(ranked)}."
        ),
        (
            f"- فحص المروحة كلها: قُرئت مواد المرشحين {len(ranked)} بـ`--max-chars 0`؛ "
            "المرشح الدلالي المختار أدناه من داخلها، لا من عمود `best` وحده."
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
        f"- ملاحظات العدستين: استرداد حتى القرار، وتشكيك مقصور على العضو؛ الجولة 22، الرتبة {row.rank:05d}.",
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
        raise AssertionError("جدول الأحكام لا يغطي الرتب السبعين")
    source_verdicts = {
        "ROOT-TRACE", "NUCLEUS-TRACE", "SEMITIC-SOURCE-TRANSMISSION",
        "LOANWORD-NON-ARABIC-TO-ARABIC",
    }
    for row, decision in zip(rows, decisions):
        ranked_candidates = {candidate for candidate, _ in ranked_by_rank[row.rank]}
        if decision.candidate not in row.candidates_found or decision.candidate not in ranked_candidates:
            raise AssertionError(f"مرشح الرتبة {row.rank} خارج المروحة الكاملة")
        if decision.verdict == "LAW-GAP" and H.route_complete(row, decision.candidate):
            raise AssertionError(f"LAW-GAP بلا صف مفقود في الرتبة {row.rank}")
        _, coverage, _ = H.classical_witnesses(decision.candidate, sense_map, 40)
        if decision.verdict in source_verdicts and coverage < 2:
            raise AssertionError(f"حكم الرتبة {row.rank} بلا شاهدين كلاسيكيين")
        if decision.verdict == "SOURCE-GAP" and coverage >= 2:
            raise AssertionError(f"SOURCE-GAP مع شاهدين في الرتبة {row.rank}")
    for rank in DECOMPOSITIONS:
        decomposition_line(next(row for row in rows if row.rank == rank), entries[rank])


def validate_text(rows: list[H.SweepRow], texts: list[str]) -> None:
    if len(rows) != 70 or len(texts) != 70:
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = [
        int(value) for value in re.findall(
            r"^### WO-B-R22-BOTH-(\d{5}):", joined, re.MULTILINE
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
            raise AssertionError(f"تجاوزت الرتبة {row.rank} حد 5KB")
        if any(field not in text for field in required):
            raise AssertionError(f"نقص حقل من بطاقة الرتبة {row.rank}")
    for rank in DECOMPOSITIONS:
        text = texts[list(EXPECTED_RANKS).index(rank)]
        if "تفكيك المعجم الحصري" not in text or "قراءة المكونات المستقلة" not in text:
            raise AssertionError(f"لم يفكك مركب الرتبة {rank}")


def report_section(
    rows: list[H.SweepRow], decisions: list[H.Decision], sizes: list[int],
    skipped: int, fresh_count: int,
) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    lines = [f"<!-- {MARKER}:START -->", ""]
    for batch in range(2):
        lo = batch * BATCH_SIZE
        hi = lo + BATCH_SIZE
        batch_rows = rows[lo:hi]
        counts = Counter(decision.verdict for decision in decisions[lo:hi])
        distribution = "؛ ".join(f"{key}={counts[key]}" for key in sorted(counts))
        lines.extend([
            f"## الجولة الثانية والعشرون، دفعة حوض both رقم {batch + 1}", "",
            f"- الوقت: {now}، Africa/Cairo.",
            "- فُحص ورُشّح قبل القراءة: 35؛ كُتب: 35؛ الترتيب overlap نازلا مع ثبات ترتيب المصدر عند التعادل.",
            (
                f"- الرتب: من {batch_rows[0].rank:05d} إلى {batch_rows[-1].rank:05d} "
                "داخل الحوض المضاعف، مع تجاوز المقروء والتكرار المفحوص."
            ),
            f"- توزيع الأحكام: {distribution}.",
            "- المروحة: وُلدت كاملة ورُتبت بالأوزان لكل عضو، ومُسحت مواد جميع مرشحيها بلا قص للحقل المصدر.",
            "- المتجانسات: قُرئت كل مداخل الرسم، وسُجل العدد ورقم المدخلة المختارة في كل بطاقة.",
            "- المصادر: نُقل شاهدان عربيان كلاسيكيان مستقلان لكل حكم صادر، وسُميت SOURCE-GAP حيث نقصا.",
            "- التفكيك: لم يقبل إلا التفكيك الصريح بعلامة الجمع في قاموس الفرع؛ قرئت المكونات استقلالا أو أُحيل إلى قراءة سابقة محددة.",
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
    transmissions = [
        f"`{row.branch}↔{decision.candidate}`"
        for row, decision in zip(rows, decisions)
        if decision.verdict in {"SEMITIC-SOURCE-TRANSMISSION", "LOANWORD-NON-ARABIC-TO-ARABIC"}
    ]
    max_size = max(sizes)
    max_rank = rows[sizes.index(max_size)].rank
    lines.extend([
        "## حصيلة الجولة الثانية والعشرين", "",
        (
            f"- حمل `persian.md` مرة واحدة في الذاكرة؛ المقروء المتجاوز في حوض both={skipped}؛ "
            f"الطازج من الرتبة 00140 فما دون قبل القطع={fresh_count}."
        ),
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- صلات الجذر والنواة الموجبة: " + "، ".join(traces) + ".",
        "- مسارات النقل المغلقة: " + "، ".join(transmissions) + ".",
        "- المركبات المفككة قاموسيا: الرتب 00158 و00159 و00173 و00179 و00206 و00216؛ لا تفكيك حدسي.",
        "- فجوة التصدير: الرتبة 00204 قُرئت من سطر Kaikki الخام 535 لأن صورتها غابت عن `branch-lexicons/persian.json`؛ لم تُملأ من الحدس.",
        "- انضباط الأدوات: جوارش بقيت خارج الحكم لأن صورتها الفعلية خارج المروحة، وصك بقي LAW-GAP لأن چ↔ص غير مرخص خارج مثال صين.",
        f"- أكبر بطاقة: {max_size} بايت، الرتبة {max_rank:05d}؛ كل البطاقات دون 5KB.",
        "- عطب أداة أساسية: 0؛ لم تُفعّل طبقة البرهان، ولم يُبن ملف مشترك، ولم يقع ship.",
        "", f"<!-- {MARKER}:END -->", "", "LANE-B DONE22 70 00260",
    ])
    return "\n".join(lines)


def validate_existing(reading_text: str, report_text: str) -> None:
    match = re.search(
        rf"<!-- {re.escape(MARKER)}:START -->(.*?)<!-- {re.escape(MARKER)}:END -->",
        reading_text, re.DOTALL,
    )
    if not match:
        raise AssertionError("محضر الجولة موجود وبطاقاتها غائبة")
    ranks = [
        int(value) for value in re.findall(
            r"^### WO-B-R22-BOTH-(\d{5}):", match.group(1), re.MULTILINE
        )
    ]
    if ranks != list(EXPECTED_RANKS):
        raise AssertionError("مقطع الجولة 22 الموجود غير مكتمل")
    if not report_text.rstrip().endswith("LANE-B DONE22 70 00260"):
        raise AssertionError("سطر DONE22 ليس خاتمة التقرير")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    reading_text = READING.read_text(encoding="utf-8")
    report_text = REPORT.read_text(encoding="utf-8")
    if MARKER in reading_text or MARKER in report_text:
        validate_existing(reading_text, report_text)
        print("ROUND22 ALREADY PRESENT AND VALID")
        return 0

    all_rows = H.parse_sweep(json.loads(SWEEP.read_text(encoding="utf-8")))
    rows, skipped, fresh_count = select_fresh(all_rows, reading_text)
    entries = select_branch_entries(rows, json.loads(LEXICON.read_text(encoding="utf-8")))
    ranked_by_rank = {row.rank: H.full_ranked_fan(row) for row in rows}
    roots = {candidate for row in rows for candidate, _ in ranked_by_rank[row.rank]}
    roots.update(candidate_for(row) for row in rows)
    sense_map = H.SENSES.matches_for_roots(H.SENSES.DEFAULT_RESOURCES, roots, None)
    decisions = [decide(row) for row in rows]
    validate_decisions(rows, entries, decisions, ranked_by_rank, sense_map)
    texts = [
        H.fit_card(row, entries[row.rank], decision, ranked_by_rank[row.rank], sense_map)
        for row, decision in zip(rows, decisions)
    ]
    validate_text(rows, texts)
    sizes = [len(text.encode("utf-8")) + 1 for text in texts]

    reading_append = (
        f"\n\n<!-- {MARKER}:START -->\n\n"
        "## الجولة الثانية والعشرون: حوض both الفارسي المضاعف (2026-08-18)\n\n"
        "- النطاق: السبعون الطازجة التالية من الرتبة 00140 فما دون، بعد تجاوز المقروء والتكرار المفحوص؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ المركب لا يفكك إلا بنص قاموس الفرع الصريح.\n\n"
        + "\n".join(texts[:BATCH_SIZE])
        + f"\n## الدفعة الثانية: الرتب {rows[BATCH_SIZE].rank:05d} إلى {rows[-1].rank:05d} بعد تجاوز المقروء\n\n"
        + "\n".join(texts[BATCH_SIZE:])
        + f"\n<!-- {MARKER}:END -->\n"
    )
    report_append = "\n" + report_section(rows, decisions, sizes, skipped, fresh_count) + "\n"
    reading_append = unicodedata.normalize("NFC", reading_append)
    report_append = unicodedata.normalize("NFC", report_append)
    combined_reading = reading_text + reading_append
    combined_report = report_text + report_append
    if "—" in reading_append + report_append or re.search(r"[۰-۹٠-٩]", reading_append + report_append):
        raise AssertionError("فشل حارس الشرطة أو الأرقام قبل الكتابة")
    validate_existing(combined_reading, combined_report)

    counts = Counter(decision.verdict for decision in decisions)
    print("ROUND22 READY")
    print("SKIPPED", skipped, "FRESH_GE140", fresh_count, "SELECTED", len(rows))
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
    print("ROUND22 WRITTEN")
    print("LANE-B DONE22 70 00260")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
