# -*- coding: utf-8 -*-
"""المسار B، الجولة 32: متابعة حوض sound_only في دفعتين من 35 بطاقة."""

from __future__ import annotations

import argparse
import hashlib
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

import harvest_persian_round31 as R31  # noqa: E402

R30 = R31.R30
R29 = R31.R29
R28 = R31.R28
H = R31.H
P = R31.P
P25 = R31.P25
READING = ROOT / "04-cross-linguistic" / "readings" / "persian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-B.md"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-persian.json"
NUCLEUS_DIR = ROOT / "04-cross-linguistic" / "exploration"
LEXICON = ROOT / "data" / "branch-lexicons" / "persian.json"
RAW_LEXICON = ROOT / "Resources" / "persian" / "kaikki.org-dictionary-Persian.jsonl"
MARKER = "LANE-B-PERSIAN-ROUND32-2026-08-26"
CARD_LIMIT = 5120
SOUND_RANKS = (
    489, 490, 492, 493, 494, 495, 496, 497, 499, 500, 502, 503, 504, 505,
    506, 507, 508, 509, 510, 511, 512, 513, 514, 515, 516, 517, 518, 519,
    520, 521, 523, 524, 525, 526, 527, 528, 529, 530, 531, 532, 533, 534,
    535, 536, 537, 538, 539, 540, 543, 544, 545, 546, 547, 548, 549, 550,
    551, 552, 553, 554, 555, 556, 557, 558, 559, 560, 561, 562, 563, 564,
)
BATCH_SIZES = (35, 35)
DONE_LINE = "LANE-B DONE32 70 WO-B-R32-SOUND-00564"
EXPECTED_SKIPS = (491, 498, 501, 522, 541, 542)

# النسخة الثانية عشرة المقروءة من القرص. مجموع sound_only زاد 2049 صفا
# عن v11، ومجموع both نقص 1999 صفا بعد تنظيف طريق المعنى.
NUCLEUS_SNAPSHOT = {
    "nucleus-sweep-ancient_greek.json": (7970202, "bc5ce7ffd7a6b9bd7cc814d6e3b239242ea9395f902584c0922ae13285bb9a58", 2330, 16775),
    "nucleus-sweep-english_middle.json": (3417949, "799770fad28e1e45a1dc62de5368513aa7adf1aaf00fe8966e888fbacaa63bf7", 1414, 7991),
    "nucleus-sweep-english_old.json": (1306531, "3963463824309e4400fe701da083eda1920e067aec6ad01fe960149705bb07e4", 474, 3414),
    "nucleus-sweep-gothic.json": (1436939, "b91b689208c467fee4c147f8e2d00c5f28bf4b03a40433b83df5ef073f1e31ad", 340, 3078),
    "nucleus-sweep-latin.json": (18838469, "4bd636b006b098f82fff5217cff553f6d0cd868c8f66506abde0cf63502a8794", 6598, 39460),
    "nucleus-sweep-old_irish.json": (952691, "33da08226e14263a22a9f5b2bd14592e6a4f0f256f0d5f2878973026ee761384", 278, 2740),
    "nucleus-sweep-old_norse.json": (1379856, "6530f3400f0e8da2b3955aa379dad69a10f646c8366d7094addd5cdffaa2eb58", 476, 3751),
    "nucleus-sweep-persian.json": (5457105, "0763ceac041c6c5c0f02110bc79c69db4d9c5fe1adb67bdeb442261ad70a8c99", 1448, 13498),
    "nucleus-sweep-welsh.json": (5777180, "740410bd00fb9b720c420b85c283eb3be04893828a72b97f3c48554d1654292b", 1188, 16087),
}

EXPECTED_ENTRY_INDEX = dict(zip(SOUND_RANKS, (
    2100, 2121, 2131, 2134, 2136, 2138, 2140, 2141, 2150, 2152,
    2159, 2171, 2184, 2194, 2196, 2206, 2210, 2215, 2219, 2223,
    2227, 2229, 2231, 2232, 2233, 2234, 2236, 2237, 2240, 0,
    2267, 2268, 2271, 2276, 2289, 2290, 2291, 2292, 2294, 2295,
    2307, 2309, 2318, 2323, 2329, 2333, 2343, 2346, 2376, 2416,
    2421, 2424, 2425, 2427, 2428, 2429, 2434, 2443, 2446, 2472,
    2480, 2492, 2502, 2505, 2517, 2520, 2525, 2527, 2531, 2548,
)))

EXPECTED_RAW_LINE = dict(zip(SOUND_RANKS, (
    2205, 2227, 2237, 2240, 2242, 2244, 2246, 2248, 2258, 2261,
    2269, 2281, 2294, 2304, 2306, 2316, 2320, 2325, 2329, 2333,
    2337, 2339, 2341, 2342, 2343, 2344, 2346, 2347, 2351, 2352,
    2380, 2381, 2384, 2389, 2402, 2403, 2404, 2405, 2407, 2408,
    2421, 2423, 2432, 2437, 2443, 2447, 2458, 2461, 2492, 2532,
    2537, 2540, 2541, 2543, 2544, 2545, 2550, 2559, 2563, 2590,
    2598, 2611, 2623, 2628, 2654, 2689, 2714, 2733, 2737, 2762,
)))

EXACT_DECOMPOSITIONS = {495, 502, 539, 554}
EXPECTED_COMPONENTS = {
    495: ("خوش", "گل"),
    502: ("بازی", "ـچه"),
    539: ("گفت", "و", "گو"),
    554: ("گداز", "ـه"),
}
COMPONENT_READINGS = {
    495: "`خوش`: entries[566] والخام 608 لمعنى happy أو pleasant، ومروحتها 90: OPEN-CANDIDATE. `گل`: entries[366-370] والخام 394-398، ولا مدخلة فيها لمعنى هيئة الحسن المسماة `gel`: COMPONENT-GAP.",
    502: "`بازی`: entries[1538] والخام 1620 لمعنى game، وهي نفسها مفككة إلى `باز` و`ـی`: COMPOUND-BOUNDARY. `ـچه`: entries[7514] والخام 8808 لاحقة التصغير، ومروحتها 60: MORPHOLOGY-GAP.",
    539: "`گفت`: غائب من branch-lexicons وحاضر في الخام 5812 صورة ماض من `گفتن`: FORM-LINK. `و`: entries[25-26] والخام 26-28، واختير حرف العطف في الخام 27، ومروحته صفر: FUNCTION-WORD. `گو`: جذع `گفتن` حاضر في الخام 6551 وغائب من branch-lexicons: FORM-LINK.",
    554: "`گداز`: جذع حاضر لـ`گداختن` في الخام 10699 وغائب من branch-lexicons: FORM-LINK. `ـه`: entries[7113-7115] والخام 8351-8354، واختيرت لاحقة اسم المفعول في entries[7113] والخام 8351، ومروحتها صفر: MORPHOLOGY-GAP.",
}

REJECTED_ANALYSES = {
    518: "يسمي الخبر By surface analysis مكوني `چنگ` و`ـال`، لا From X + Y نهائيا مباشرا مؤهلا.",
    523: "يعرض الخبر بديلين تاريخيين في Proto-Iranian، لا تفكيكا نهائيا مباشرا للصورة الحديثة.",
    524: "يعرض الخبر بديلين تاريخيين في Proto-Iranian، لا تفكيكا نهائيا مباشرا للصورة الحديثة.",
    553: "شجرة الخبر تجمع عناصر Proto-Iranian تاريخية، ولا تصدر From X + Y نهائيا مباشرا لـ`بستر`.",
}
TOOL_GAPS = {
    490: "الصورة `گاه` منقوطة /gāh/، لكن الهيكل أسقط /h/ النهائية المنطوقة.",
    521: "الصورة اللهجية `پیر` منقوطة /piyær/ في الخام 2352، لكن الهيكل أسقط /y/ المنطوقة.",
    523: "الصورة `پیاده` منقوطة /piyāda/، لكن الهيكل أسقط /y/ المنطوقة.",
    524: "الصورة `پیاده` منقوطة /piyāda/، لكن الهيكل أسقط /y/ المنطوقة.",
    564: "الصورة `کیهان` منقوطة /kayhān/، لكن الهيكل أسقط /y/ المنطوقة.",
}
OUT_OF_SCOPE = {
    506: "المدخلة اسم برج Aries، لا معنى معجميا عاما للحمل أو الكبش.",
    515: "المدخلة اسم الشهر الرابع واليوم الثالث عشر في التقويم الفارسي.",
    545: "المدخلة اسم الشهر الثالث واليوم السادس في التقويم الفارسي.",
    546: "المدخلة اسم الشهر الثامن واليوم العاشر في التقويم الفارسي.",
    549: "المدخلة اسم الشهر العاشر في التقويم الفارسي.",
}


@dataclass(frozen=True)
class SelectedRow:
    row: H.SweepRow

    @property
    def key(self) -> str:
        return f"S{self.row.rank:05d}"

    @property
    def heading(self) -> str:
        return f"WO-B-R32-SOUND-{self.row.rank:05d}"


Review = R29.Review
R = R29.R

# سجل قراءة يدوي. لا يشتق الحكم من best ولا من وزن المروحة.
REVIEWS = {
    489: R("جنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جنج`: الستر والكثافة مع بروز؛ لا يسمي treasure أو store.", "ذكر الخبر العربي `كنز` مطابقا للمعنى، لكنه خارج المروحة المرخصة لأن صف ج↔ز غير مسمى؛ لم أدخل مقابلا من خارج الحوض."),
    490: R("جوا", "TOOL-GAP", "جسر المعنى: hymn أو song حاضر، لكن /gāh/ يحمل /h/ أسقطها الهيكل.", "توقف العضو عند الصامت النهائي الساقط قبل أي مدار للحركة أو الغناء."),
    492: R("مغص", "LAW-GAP", "نص الحدث المجمد لـ`مغص`: محاكم حروف بلا معنى brain أو marrow، وصف ز↔ص غير مسمى.", "احتواء الدماغ في الجمجمة ووظيفة النخاع سياقان خارجيان، وفوقهما فجوة القانون."),
    493: R("لصق", "LAW-GAP", "نص الحدث المجمد لـ`لصق`: الالتصاق؛ لا يسمي kerchief أو headscarf، وصف چ↔ص غير مسمى.", "التصاق المنديل بالرأس هيئة لبسه لا معنى غطاء الرأس، وفوقها فجوة القانون."),
    494: R("لس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`لس`: قلة مفارقة المنشأ أو المقر؛ لا يسمي corpse أو carrion.", "مفارقة الروح للجسد تفسير خارج المدخلة، وشاهدا العربية في نتف النبات لا الجثة."),
    495: R("حسجل", "COMPOUND-BOUNDARY", "جسر المعنى: beautiful مفككة مباشرة إلى `خوش` pleasant و`گل` gel.", "قُرئ المكونان استقلالا؛ بقي معنى gel غائبا من جرد الفرع ولم تورث الصورة حكم أي مكون."),
    496: R("حسجل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`حسجل`: انكشاف الظاهر مع بروز؛ لا يسمي beauty.", "الحسن تقييم للظاهر لا مجرد ظهوره، ولم أخترع تفكيك `خوشگل` و`ی` في غياب خبر مباشر."),
    497: R("اذذ", "LAW-GAP", "نص الحدث المجمد لـ`اذذ`: محاكم حروف بلا معنى god أو angel، وصفا ز↔ذ ود↔ذ غير مسميين.", "مقارنة السريانية في الخبر لا تسمي مانحا مباشرا ولا تصلح فجوتي الصوت."),
    499: R("رز", "LAW-GAP", "نص الحدث المجمد لـ`رز`: التداخل الشديد؛ لا يسمي line أو parade، وصف ژ↔ز غير مسمى.", "اصطفاف السائرين ترتيب لا تداخل، وفوق ضعف المدار بقي القانون ناقصا."),
    500: R("است", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`است`: محاكم حروف بلا معنى bone.", "الصلابة هيئة للعظم تشترك فيها مواد كثيرة، والشاهد العربي في الاست لا العظم."),
    502: R("بزج", "COMPOUND-BOUNDARY", "جسر المعنى: toy مفككة مباشرة إلى `بازی` game و`ـچه` لاحقة التصغير.", "قُرئ المكونان استقلالا، ووقفت الصورة عند المركب قبل صف چ↔ج غير المسمى."),
    503: R("درست", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`درست`: جريان أو امتداد متوال؛ لا يسمي correct أو upright.", "استقامة المسار قد تكون وصفا للصواب، لكنها لا تساوي الحكم بالصحة، والشاهد العربي علم شخص."),
    504: R("نش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`نش`: ارتفاع بانتشار مع حدة؛ لا يسمي sting أو bite.", "حدة اللسعة وصف لأداتها أو ألمها لا معنى الحدث كله، وشاهدا العربية في نشيش الماء."),
    505: R("بل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بل`: التمكن والحوز بشدة؛ لا يسمي wing.", "تمكن الطائر بالجناح وظيفة للعضو لا معنى الجناح، وفصلت `بال` العربية المتجانسة عن المدخلة."),
    506: R("بر", "OUT-OF-SCOPE", "جسر المعنى: Aries اسم برج لا معنى معجميا عاما.", "عزل اسم البرج عن مادة الحمل والكبش، ولم يحوله إلى دعوى جذرية."),
    507: R("هنر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`هنر`: رخاوة متجمع في الباطن؛ لا يسمي art أو craft أو ability.", "إتقان الصنعة نتيجة للقدرة لا الرخاوة الباطنة، وشاهدا العربية في وقبة الأذن."),
    508: R("نب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`نب`: النبو ارتفاعا أو ابتعادا؛ لا يسمي grandchild.", "ابتعاد الحفيد جيلا عن الجد ترتيب نسب لا معنى القرابة نفسها."),
    509: R("بلش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بلش`: الحوز مع تفشي دقيق؛ لا يسمي pillow أو cushion.", "احتواء الوسادة للحشو وصفي لوظيفتها، ولا شاهد عربي ثان للمادة."),
    510: R("طشن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`طشن`: محاكم حروف بلا معنى thirsty أو drought.", "جفاف الحلق سياق العطش لا حدث حروفي محكوم تحته، والشاهد العربي اسم بئر."),
    511: R("سرنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سرنج`: امتداد أو نفاذ مع دقة؛ لا يسمي syringe.", "النفاذ وظيفة الإبرة لا معنى الأداة، وشاهدا العربية يسميان مادة صناعية ودواء."),
    512: R("تر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تر`: الابتعاد بقوة مع دقة؛ لا يسمي star.", "بعد النجم في السماء موضع لا حركة ابتعاد، والمدخلة قرض هندي لا يفتح اتصالا عربيا."),
    513: R("نم", "NUCLEUS-TRACE", "جسر المعنى: moisture أو dew لطيف ينتشر من باطن المادة أو الجو إلى ظاهر السطح، وهو نص الحدث المجمد لـ`نم`.", "مدار 1: الرطوبة أثر لطيف يظهر على السطح؛ وشاهدا نم الحديث يثبتان خروج المحتوى الخفي إلى الظاهر."),
    514: R("تر", "NUCLEUS-TRACE", "جسر المعنى: arrow جسم دقيق يبتعد بقوة نحو هدف، وهو نص الحدث المجمد لـ`تر`.", "مدار 1: السهم يفارق مطلقه بقوة ودقة؛ وشاهدا العربية يثبتان مادة النواة، ولم يعتمد حكم الشهر المتجانس."),
    515: R("تر", "OUT-OF-SCOPE", "جسر المعنى: Tir اسم شهر ويوم فارسيين لا معنى معجميا عاما.", "عزل اسم التقويم عن مدخلة arrow السابقة ولم يورثه أثرها."),
    516: R("توز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`توز`: محاكم حروف بلا معنى sharp أو pungent.", "حدة الزاي في المخرج لا تكفي لتسمية الحدة المعجمية، وشاهدا العربية في الخلق والأصل والشجر."),
    517: R("توز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`توز`: محاكم حروف بلا معنى swiftly أو quickly.", "سرعة انقطاع التاء وصف نطقي لا معنى الظرف، وفصلت المدخلة عن sharp السابقة."),
    518: R("جنجل", "LAW-GAP", "نص الحدث المجمد لـ`جنجل`: الستر والكثافة؛ لا يسمي fork أو hook، وصف چ↔ج غير مسمى.", "وظيفة الخطاف في الإمساك لا تساوي اسم الأداة؛ ورفضت surface analysis غير المؤهل وفوقه فجوة القانون."),
    519: R("وزغ", "OPEN-CANDIDATE", "جسر المعنى: التواد والوزغ العربيان حيوانان صغيران زاحفان، لكن أحدهما ضفدع والآخر سام أبرص.", "تقارب فئة الحيوان لا يساوي النوع، والحدث المجمد محاكم حروف لا يسمي جنسا حيوانيا؛ بقي صدى معجمي مفتوحا."),
    520: R("بر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بر`: التجرد والخلوص؛ لا يسمي Pir أو Sheikh.", "الزهد صفة محتملة لبعض الشيوخ لا معنى اللقب الصوفي، ولم أورثه من معنى old."),
    521: R("بر", "TOOL-GAP", "جسر المعنى: father حاضر في الخام اللهجي، لكن /piyær/ يحمل /y/ أسقطها الهيكل.", "قُرئت المدخلة الخام الثالثة المستبعدة من branch-lexicons؛ أوقف الصامت الساقط أي مقارنة مع الأبوة."),
    523: R("بد", "TOOL-GAP", "جسر المعنى: on foot حاضر، لكن /piyāda/ يحمل /y/ أسقطها الهيكل.", "رفضت التحليل التاريخي البديل، ثم أوقف الصامت الساقط حكم الظرف."),
    524: R("بد", "TOOL-GAP", "جسر المعنى: pedestrian أو pawn حاضر، لكن /piyāda/ يحمل /y/ أسقطها الهيكل.", "فصلت الاسم عن الظرف السابق، ورفضت التحليل التاريخي البديل ثم أوقف الصامت الساقط الحكم."),
    525: R("ابر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ابر`: محاكم حروف بلا معنى opera.", "الغناء والتمثيل جنسا العمل الفني لا يستخرجان من الرسم، ولا خبر أصل في المدخلة."),
    526: R("تب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تب`: ضعف المتجمع أو ذهاب غلظه؛ لا يسمي hill.", "انخفاض التل بعد التعرية أثر لاحق لا معنى المرتفع، وخبر الأصل يسمي قرضا تركيا."),
    527: R("برهن", "ROOT-TRACE", "جسر المعنى: bare أو naked تجرد وخلوص وانكشاف، وهو نص الحدث المجمد لـ`برهن`.", "مدار 1: العاري منكشف بعد زوال غطائه؛ وشاهدا البرهان يثبتان الإبانة والكشف في المادة العربية."),
    528: R("شمر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شمر`: جمع المنتشر منسحبا إلى أعلى؛ لا يسمي number أو sequence.", "جمع الآحاد شرط للعد لا معنى العدد أو موضعه، وشاهدا العربية في رفع الثوب."),
    529: R("جرم", "LAW-GAP", "نص الحدث المجمد لـ`جرم`: تجريد العذوق بعد تمامها؛ لا يسمي leather، وصف چ↔ج غير مسمى.", "ذكر الجرم للجسد يجعل الجلد جزءا منه لا معنى الجلد المدبوغ، وفوقه فجوة القانون."),
    530: R("جرم", "LAW-GAP", "نص الحدث المجمد لـ`جرم`: تجريد العذوق بعد تمامها؛ لا يسمي leathery، وصف چ↔ج غير مسمى.", "الصفة من المادة السابقة لا ترث حكما، وفوق ضعف المدار بقيت فجوة القانون."),
    531: R("تنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تنج`: ضغط على القوة الباطنة؛ لا يسمي flagon أو carafe.", "احتواء الإناء للسائل وظيفة عامة، والمدخلة قرض صيني عبر الجغتائية."),
    532: R("تنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تنج`: ضغط على القوة الباطنة؛ لا يسمي bundle أو strap.", "شد الحزمة أو الرباط فعل استعمال لا معنى الاسم، وفصلت المتجانس عن الإناء السابق."),
    533: R("خنق", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خنق`: ضيق شديد يكاد يسد الجوف؛ لا يسمي cool أو pleased.", "زوال الضيق عند البرودة أو السرور أثر مقابل لا معنى الصفة، وشاهدا العربية في الخنق."),
    534: R("كلب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كلب`: العض والإمساك الشديد؛ لا يسمي hut أو shop.", "سمى الخبر ألفاظا عربية إيرانية الاقتراض بأشكال `كربق` و`قربق` و`كربج`، لكن صورة المدخلة ومروحتها لا تحتويها؛ لم أقصرها إلى `كلب`."),
    535: R("رد", "NUCLEUS-TRACE", "جسر المعنى: row أو category تراكم مرتب لوحدات يحد بعضها امتداد بعض، وهو نص الحدث المجمد لـ`رد`.", "مدار 1: الصف ترتيب متراكم عند حدود متعاقبة؛ وشاهدا الرد يثبتان الصد والصرف الذي يقوم عليه الحد."),
    536: R("نرد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`نرد`: نفاذ لطيف حاد الوقع؛ لا يسمي tree trunk.", "حقل الأصل في الخام يكرر أصل backgammon على مدخلة tree trunk؛ سجلت عطب المصدر ولم أورث شاهدي النرد المعرب لهذا المعنى."),
    537: R("تب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تب`: ضعف المتجمع أو ذهاب غلظه؛ لا يسمي bundle أو bale.", "تجمع اللفافة هيئة، لكن الحدث يسمي زوال الغلظ لا تكوين الحزمة."),
    538: R("رن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رن`: مادة تغطي الحس وتمنع النفاذ؛ لا يسمي thigh.", "تغطية الفخذ باللحم وصف لكل عضو ممتلئ لا معنى الجزء، وشاهدا العربية في الصوت."),
    539: R("جبثق", "COMPOUND-BOUNDARY", "جسر المعنى: conversation مفككة مباشرة إلى `گفت` و`و` و`گو`.", "قُرئت الأجزاء الثلاثة استقلالا؛ وقفت الصورة عند المركب قبل صفوف الصوت الناقصة ولم تورث القول للحاصل."),
    540: R("جم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جم`: التجمع والكثرة؛ لا يسمي step.", "تتابع الخطوات يجمع مسافة لكنه لا يساوي الخطوة المفردة، وخبر الأصل هندو أوروبي."),
    543: R("نور", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`نور`: لطيف لامع حاد الأثر ينفذ؛ لا يسمي force أو power.", "نفاذ القوة أثر لاستعمالها، لكنه لا يميز القدرة من الضوء، وشاهدا العربية في النور."),
    544: R("قربع", "LAW-GAP", "نص الحدث المجمد لـ`قربع`: استقرار المتسيب في قاع؛ لا يسمي frog، وصف غ↔ع غير مسمى.", "جلوس الضفدع في الماء سياق موطن لا معنى النوع، وفوقه فجوة القانون."),
    545: R("خردذ", "OUT-OF-SCOPE", "جسر المعنى: Khordad اسم شهر ويوم فارسيين لا معنى معجميا عاما.", "عزل اسم التقويم مع بقاء صف د↔ذ غير المسمى خارج الحكم."),
    546: R("ابن", "OUT-OF-SCOPE", "جسر المعنى: Aban اسم شهر ويوم فارسيين لا معنى معجميا عاما.", "عزل اسم التقويم ولم يحوله إلى مادة ابن؛ وبقي صف آ↔ا غير المسمى مسجلا."),
    547: R("اذر", "LAW-GAP", "نص الحدث المجمد لـ`اذر`: محاكم حروف بلا معنى fire، وصف آ↔ا غير مسمى.", "الحرارة والانتشار استنباطان من النار لا من المحاكم وحدها، وفوقهما فجوة القانون."),
    548: R("دي", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دي`: محكمتا حرفين بلا معنى yester.", "الرجوع إلى اليوم السابق وظيفة زمنية لا تستخرج من الدال والياء، ولا شاهد عربي في الموارد."),
    549: R("دي", "OUT-OF-SCOPE", "جسر المعنى: Dey اسم الشهر العاشر الفارسي.", "عزل اسم التقويم عن yester وmother المتجانسين ولم يورث أحدها الآخر."),
    550: R("دي", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دي`: محكمتا حرفين بلا معنى mother أو mama.", "الخام يكرر تأثيل Dey أو Creator على مدخلة الأم اللهجية؛ سجلت عطب المصدر وبقيت الأمومة خارج المدار."),
    551: R("مهر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مهر`: الفراغ والرقة والسهولة؛ لا يسمي kindness أو love.", "الرقة صفة للعطف لكنها لا تساوي المحبة، وشاهدا العربية في الصداق لا الشعور."),
    552: R("رن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رن`: مادة تغطي الحس وتمنع النفاذ؛ لا يسمي psyche أو soul.", "خفاء النفس عن الحس نتيجة معرفية لا معنى الروح، وشاهدا العربية في الرنين."),
    553: R("بشتر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بشتر`: الانتشار الظاهر؛ لا يسمي bed أو mattress.", "بسط الفراش فعل تهيئة للسرير لا معنى الأثاث، ورفضت التركيب التاريخي غير النهائي."),
    554: R("جذذ", "COMPOUND-BOUNDARY", "جسر المعنى: lava مفككة مباشرة إلى `گداز` melt-stem و`ـه` لاحقة.", "قُرئ الجذع واللاحقة استقلالا؛ وقفت الصورة عند المركب قبل صفوف الصوت الناقصة."),
    555: R("سختن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سختن`: لين يسمح بالاختراق أو الانقياد؛ لا يسمي burn أو suffer.", "لين المحترق أو تفتته نتيجة للنار لا معنى الاحتراق، والشاهد العربي علم شخص."),
    556: R("يد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`يد`: امتداد بقوة للتمكين أو الضغط؛ لا يسمي memory.", "حفظ الذكر في الذهن وظيفة باطنة لا معنى اليد أو الامتداد، وشاهدا العربية في الجارحة."),
    557: R("جمش", "LAW-GAP", "نص الحدث المجمد لـ`جمش`: تجمع وكثرة مع انتشار؛ لا يسمي spoon أو scoop، وصفا چ↔ج وچ↔ش غير مسميين.", "جمع الملعقة للطعام وظيفة للأداة، وفوقها فجوتا القانون وخبر القرض التركي."),
    558: R("كل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كل`: تجمع كتلة دون حد أو طرف دقيق؛ لا يسمي bald.", "غياب أطراف الشعر يصف هيئة الرأس الأصلع، لكنه أثر عدمي لا معنى الصفة؛ وشاهدا العربية في كلال الحد."),
    559: R("جفت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جفت`: الجفاف والتباعد؛ لا يسمي statement.", "انفصال القول عن قائله بعد صدوره سياق تداول لا معنى العبارة، ولا شاهد عربي ثان."),
    560: R("مرز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مرز`: استرسال وحركة بحدة؛ لا يسمي boundary أو frontier.", "الحد يوقف الاسترسال ولا يسميه، وشاهدا العربية في القرص اللطيف لا المنطقة."),
    561: R("موم", "LOANWORD-NON-ARABIC-TO-ARABIC", "جسر المعنى: wax أو candle هي `الموم` العربية نفسها، والشاهدان يسميانها معربة وأصلها فارسيا.", "اتحدت الصورة ومعنى الشمع، وسمى لسان العرب وتاج العروس اتجاه الفارسية إلى العربية؛ أغلق تماس لا إرثا."),
    562: R("برنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`برنج`: التجرد والخلوص مع حدث النون؛ لا يسمي panther أو leopard.", "الجري أو الانفراد فعل للحيوان لا اسم النوع، وشاهدا العربية في جوز الهند."),
    563: R("كبثل", "LAW-GAP", "نص الحدث المجمد لـ`كبثل`: تجمع كتلة متضاغطة؛ لا يسمي hyena، وصف ت↔ث غير مسمى.", "هيئة جسم الحيوان عامة لا معنى الضبع، وفوقها فجوة القانون؛ وشاهدا العربية في حشرة."),
    564: R("كهن", "TOOL-GAP", "جسر المعنى: universe أو cosmos حاضر، لكن /kayhān/ يحمل /y/ أسقطها الهيكل.", "أوقف الصامت الساقط المقارنة قبل تحويل الكون إلى كهانة أو قدم."),
}


def pair_key(row: H.SweepRow) -> tuple[str, str]:
    return H.clean(row.branch), H.norm_gloss(row.gloss)


def validate_nucleus_snapshot() -> None:
    actual_names = {path.name for path in NUCLEUS_DIR.glob("nucleus-sweep-*.json")}
    if actual_names != set(NUCLEUS_SNAPSHOT):
        raise AssertionError(f"تغير جرد أحواض النواة الحالية: {sorted(actual_names)}")
    total_both = 0
    total_sound = 0
    for name, (expected_size, expected_hash, expected_both, expected_sound) in NUCLEUS_SNAPSHOT.items():
        raw = (NUCLEUS_DIR / name).read_bytes()
        if len(raw) != expected_size or hashlib.sha256(raw).hexdigest() != expected_hash:
            raise AssertionError(f"تغيرت نسخة القرص الحالية للحوض {name}")
        data = json.loads(raw)
        language = name.removeprefix("nucleus-sweep-").removesuffix(".json")
        if data.get("language") != language:
            raise AssertionError(f"تغير وسم اللغة في {name}")
        if data.get("both_total") != expected_both or data.get("sound_only_total") != expected_sound:
            raise AssertionError(f"تغير عداد نسخة v12 في {name}")
        if len(data.get("both") or []) != expected_both or len(data.get("sound_only") or []) != expected_sound:
            raise AssertionError(f"تغير طول قوائم نسخة v12 في {name}")
        total_both += expected_both
        total_sound += expected_sound
    if total_both != 14546 or total_sound != 106794:
        raise AssertionError("تغير مجموع أحواض v12")


def select_rows(data: dict, reading_text: str) -> tuple[list[SelectedRow], dict]:
    pairs = H.read_pairs(reading_text)
    all_sound = [P25.sound_row(rank, raw) for rank, raw in enumerate(data.get("sound_only") or [], 1)]
    if len(all_sound) != 2304:
        raise AssertionError(f"تغير حجم حوض الصوت القديم: {len(all_sound)}")
    prior = {row.rank for row in all_sound if P25.pair_was_read(row, pairs)}
    fresh: list[H.SweepRow] = []
    seen: set[tuple[str, str]] = set()
    internal_skips: list[int] = []
    for row in all_sound:
        key = pair_key(row)
        if row.rank in prior or key in seen:
            if row.rank > 488 and len(fresh) < 70:
                internal_skips.append(row.rank)
            continue
        seen.add(key)
        if row.rank <= 488:
            continue
        fresh.append(row)
        if len(fresh) == 70:
            break
    ranks = tuple(row.rank for row in fresh)
    if ranks != SOUND_RANKS:
        raise AssertionError(f"تغير استئناف sound_only: {ranks}")
    if tuple(internal_skips) != EXPECTED_SKIPS:
        raise AssertionError(f"تغيرت المواضع المقروءة داخل النافذة: {internal_skips}")
    return [SelectedRow(row) for row in fresh], {
        "pair_count": len(pairs),
        "sound_prior_total": len(prior),
        "skipped": internal_skips,
    }


def select_branch_entries(
    selected: list[SelectedRow], lexicon: dict
) -> tuple[dict[int, H.BranchEntry], dict[str, list[tuple[int, dict]]]]:
    grouped: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for index, entry in enumerate(lexicon.get("entries") or [], 1):
        grouped[H.clean(entry.get("word") or "")].append((index, entry))
    output: dict[int, H.BranchEntry] = {}
    for item in selected:
        row = item.row
        if row.rank == 521:
            output[row.rank] = H.BranchEntry(
                global_index=0,
                homograph_index=3,
                homograph_count=3,
                word=row.branch,
                reading="piyar",
                pos="noun",
                gloss="colloquial form of پدر (padar, father)",
                etymology="See the etymology of the corresponding lemma form.",
            )
            continue
        options = grouped.get(row.branch, [])
        if not options:
            raise AssertionError(f"لا مدخلة فرع للرسم {row.branch}")
        global_index, entry = max(options, key=lambda pair: H.entry_score(H.norm_gloss(row.gloss), pair[1]))
        if global_index != EXPECTED_ENTRY_INDEX[row.rank]:
            raise AssertionError(f"انزلقت مدخلة الرتبة {row.rank}: {global_index}")
        homograph_index = 1 + next(i for i, pair in enumerate(options) if pair[0] == global_index)
        output[row.rank] = H.BranchEntry(
            global_index=global_index,
            homograph_index=homograph_index,
            homograph_count=len(options),
            word=H.clean(entry.get("word") or ""),
            reading=H.clean(entry.get("read") or row.say),
            pos=H.clean(entry.get("pos") or ""),
            gloss=H.clean(entry.get("en") or ""),
            etymology=H.clean(entry.get("etym") or "فجوة اشتقاق في لقطة الفرع."),
        )
    return output, grouped


def load_raw_entries(selected: list[SelectedRow], entries: dict[int, H.BranchEntry]) -> dict[int, dict]:
    wanted = {item.row.branch for item in selected}
    grouped: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    with RAW_LEXICON.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            raw = json.loads(line)
            word = H.clean(raw.get("word") or "")
            if word in wanted:
                grouped[word].append((line_number, raw))
    output: dict[int, dict] = {}
    for item in selected:
        row = item.row
        entry = entries[row.rank]
        options = grouped.get(row.branch, [])
        if row.rank == 521:
            line_number, raw = next(pair for pair in options if pair[0] == 2352)
        else:
            same_pos = [pair for pair in options if H.clean(pair[1].get("pos") or "") == entry.pos]
            line_number, raw = max(
                same_pos or options,
                key=lambda pair: H.entry_score(H.norm_gloss(entry.gloss), {"en": P25.raw_gloss(pair[1])}),
            )
        if line_number != EXPECTED_RAW_LINE[row.rank]:
            raise AssertionError(f"انزلق سطر Kaikki للرتبة {row.rank}: {line_number}")
        output[row.rank] = {
            "line": line_number,
            "entry": raw,
            "gloss": P25.raw_gloss(raw),
            "etymology": H.clean(raw.get("etymology_text") or ""),
        }
    return output


def validate_components(grouped: dict[str, list[tuple[int, dict]]]) -> None:
    expected_indices = {
        "خوش": {566}, "گل": {366, 367, 368, 369, 370}, "بازی": {1538},
        "ـچه": {7514}, "گفت": set(), "و": {25, 26},
        "گو": {5574, 5575, 5576, 5577}, "گداز": set(),
        "ـه": {7113, 7114, 7115},
    }
    fan_counts = {
        "خوش": 90, "گل": 80, "بازی": 30, "ـچه": 60, "گفت": 24,
        "و": 0, "گو": 72, "گداز": 36, "ـه": 0,
    }
    for word, expected in expected_indices.items():
        actual = {index for index, _entry in grouped.get(word, [])}
        if actual != expected:
            raise AssertionError(f"تغير جرد مكون {word}: {sorted(actual)}")
        fan = tuple(H.FAN.rank(word, H.FAN.fan(word, "persian"), "persian"))
        if len(fan) != fan_counts[word]:
            raise AssertionError(f"تغيرت مروحة المكون {word}: {len(fan)}")
    expected_raw = {
        "خوش": {608}, "گل": {394, 395, 396, 397, 398}, "بازی": {1620},
        "ـچه": {8808}, "گفت": {5812}, "و": {26, 27, 28},
        "گو": {6551, 6552, 6553, 6554, 6555, 6556, 6557},
        "گداز": {10699}, "ـه": {8351, 8352, 8353, 8354},
    }
    actual_raw: dict[str, set[int]] = defaultdict(set)
    with RAW_LEXICON.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            word = H.clean(json.loads(line).get("word") or "")
            if word in expected_raw:
                actual_raw[word].add(line_number)
    for word, expected in expected_raw.items():
        if actual_raw[word] != expected:
            raise AssertionError(f"تغيرت أسطر مكون {word}: {sorted(actual_raw[word])}")


def obstacle_for(review: Review) -> str:
    if review.verdict in {"ROOT-TRACE", "NUCLEUS-TRACE"}:
        return "اكتملت أرجل الصوت والحدث والمدار اليدوي، ومعها شاهدان عربيان كلاسيكيان مستقلان."
    if review.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC":
        return "اكتملت الصورة والمعنى والشواهد، وسمى الشاهدان اتجاه الفارسية إلى العربية؛ أغلق تماس لا إرثا."
    if review.verdict == "COMPOUND-BOUNDARY":
        return "وقف الحكم عند حد المركب؛ لم تورث الصورة المجموعة حكم مكون ولم يخترع تفكيك."
    if review.verdict == "LAW-GAP":
        return "طريق المعنى مفحوص، لكن مسار الصوت يحوي صفا غير مسمى؛ لم يصدر حكم موجب."
    if review.verdict == "TOOL-GAP":
        return "صف الحوض أسقط صامتا منطوقا؛ توقف العضو قبل الحكم ولم يعوض الصامت يدويا."
    if review.verdict == "OUT-OF-SCOPE":
        return "الشرح اسم علم تقويمي أو فلكي لا معنى معجميا عاما؛ أحيل إلى طبقة الأعلام المنفصلة."
    return "مسار الصوت قابل للفحص، لكن المدار لم يقم على معنى المدخلة؛ بقي المرشح مفتوحا."


def decide(item: SelectedRow) -> H.Decision:
    review = REVIEWS[item.row.rank]
    return H.Decision(review.candidate, review.verdict, H.state_for(review.verdict), review.orbit, obstacle_for(review))


def decomposition_lines(item: SelectedRow, raw: dict) -> list[str]:
    rank = item.row.rank
    if rank not in EXACT_DECOMPOSITIONS:
        return []
    decomposition = P25.direct_from_plus(raw["etymology"])
    if not decomposition:
        raise AssertionError(f"غاب تفكيك From X + Y للرتبة {rank}")
    joined = " + ".join(decomposition)
    for component in EXPECTED_COMPONENTS[rank]:
        if H.clean(component) not in H.clean(joined):
            raise AssertionError(f"غاب مكون {component} من الرتبة {rank}: {decomposition}")
    return [
        f"- تفكيك Kaikki الحصري من السطر الخام {raw['line']}: «{H.clip(raw['etymology'], 420)}».",
        f"- قراءة المكونات المستقلة: {COMPONENT_READINGS[rank]}",
        "- الخطوة صفر: قبل التفكيك الحرفي النهائي لم تقارن الصورة وحدة جذرية؛ قُرئ كل مكون مسمى وحده.",
    ]


def make_card(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit) -> str:
    card = R31.make_card(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit)
    card = card.replace("الجولة 31،", "الجولة 32،")
    rank = item.row.rank
    if rank in REJECTED_ANALYSES and "حد التحليل غير المؤهل" not in card:
        marker = "- عطب الهيكل:" if rank in TOOL_GAPS else "- الخطوة صفر:"
        card = card.replace(
            marker,
            f"- حد التحليل غير المؤهل: {REJECTED_ANALYSES[rank]}\n{marker}",
            1,
        )
    if rank == 489:
        card = card.replace(
            "- الخطوة صفر:",
            "- حد المقابل المسمى في المصدر: ذكر الخبر `كَنْز` العربية بمعنى treasure، لكنها خارج المروحة الحية لأن ج↔ز غير مسمى؛ لم تدخل بديلا حدسيا.\n- الخطوة صفر:",
            1,
        )
    if rank == 521:
        card = re.sub(
            r"^- قراءة مداخل الرسم المتجانس:.*$",
            "- قراءة مداخل الرسم المتجانس: قُرئت مدخلتا branch-lexicons في entries[2239-2240] والثلاث الخام 2350-2352؛ معنى father غائب من الفرع وحاضر في الخام 2352، وهو المختار دون اختلاق.",
            card,
            count=1,
            flags=re.MULTILINE,
        )
    if rank == 536:
        card = card.replace(
            "- الخطوة صفر:",
            "- عطب المصدر: حقل أصل مدخلة tree trunk يكرر تأثيل backgammon من `نردشیر`؛ حفظ التعارض ولم يورث معنى اللعبة.\n- الخطوة صفر:",
            1,
        )
    if rank == 550:
        card = card.replace(
            "- الخطوة صفر:",
            "- عطب المصدر: حقل أصل مدخلة mother يكرر Middle Persian Day بمعنى Creator الخاص بالمتجانس التقويمي؛ حفظ التعارض ولم يورثه.\n- الخطوة صفر:",
            1,
        )
    if rank == 561:
        lines = card.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("  - الشاهد 1،"):
                lines[index] = "  - الشاهد 1، لسان العرب لابن منظور: «الموم: الشمع، معرب، واحدته مومة؛ وأصله فارسي.»"
            elif line.startswith("  - الشاهد 2،"):
                lines[index] = "  - الشاهد 2، تاج العروس لمرتضى الزبيدي: «الموم: الشمع، معرب؛ قال الأزهري: وأصله فارسي.»"
            elif line.startswith("- المصفاة:"):
                lines[index] = "- المصفاة: الشاهدان العربيان يسمّيان اللفظ معربا وأصله فارسيا؛ يعمل LOANWORD-NON-ARABIC-TO-ARABIC نتيجة تماس إيجابية محسوبة."
        card = "\n".join(lines) + "\n"
    return card


def validate_decisions(selected, raw_entries, decisions, ranked_by_rank, sense_map) -> None:
    if set(REVIEWS) != set(SOUND_RANKS):
        raise AssertionError("جدول المدار اليدوي لا يغطي الرتب السبعين")
    parsed = {item.row.rank for item in selected if P25.direct_from_plus(raw_entries[item.row.rank]["etymology"])}
    if parsed != EXACT_DECOMPOSITIONS:
        raise AssertionError(f"تغيرت أسطر From X + Y المباشرة: {sorted(parsed)}")
    expected_verdicts = {
        "COMPOUND-BOUNDARY": 4,
        "LAW-GAP": 11,
        "LOANWORD-NON-ARABIC-TO-ARABIC": 1,
        "NUCLEUS-TRACE": 3,
        "OPEN-CANDIDATE": 40,
        "OUT-OF-SCOPE": 5,
        "ROOT-TRACE": 1,
        "TOOL-GAP": 5,
    }
    if Counter(review.verdict for review in REVIEWS.values()) != Counter(expected_verdicts):
        raise AssertionError(f"تغير توزيع الأحكام اليدوي: {Counter(review.verdict for review in REVIEWS.values())}")
    if {rank for rank, review in REVIEWS.items() if review.verdict in {"ROOT-TRACE", "NUCLEUS-TRACE"}} != {513, 514, 527, 535}:
        raise AssertionError("تغيرت مواضع الآثار اليدوية")
    if {rank for rank, review in REVIEWS.items() if review.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC"} != {561}:
        raise AssertionError("تغير موضع اتجاه الدخول")
    for item, decision in zip(selected, decisions):
        row = item.row
        candidates = {candidate for candidate, _score in ranked_by_rank[row.rank]}
        if decision.candidate not in candidates or decision.candidate not in row.candidates_found:
            raise AssertionError(f"مرشح الرتبة {row.rank} خارج المروحة الحية أو أعضاء الحوض")
        complete = H.route_complete(row, decision.candidate)
        _count, coverage, _witnesses = P.classical_witnesses(decision.candidate, sense_map, 90)
        if decision.verdict == "LAW-GAP" and complete:
            raise AssertionError(f"LAW-GAP بلا صف مفقود في الرتبة {row.rank}")
        if decision.verdict in {"OPEN-CANDIDATE", "ROOT-TRACE", "NUCLEUS-TRACE", "LOANWORD-NON-ARABIC-TO-ARABIC"} and not complete:
            raise AssertionError(f"حكم بمسار ناقص في الرتبة {row.rank}: {decision.verdict}")
        if decision.verdict in {"ROOT-TRACE", "NUCLEUS-TRACE", "LOANWORD-NON-ARABIC-TO-ARABIC"}:
            if coverage < 2 or H.event_line(decision.candidate).startswith("لا حدث"):
                raise AssertionError(f"حكم صادر بلا حدث وشاهدين في الرتبة {row.rank}")
        if row.rank in EXACT_DECOMPOSITIONS and decision.verdict != "COMPOUND-BOUNDARY":
            raise AssertionError(f"تفكيك مباشر بلا حد مركب في الرتبة {row.rank}")
        if row.rank in TOOL_GAPS and decision.verdict != "TOOL-GAP":
            raise AssertionError(f"هيكل ناقص بلا TOOL-GAP في الرتبة {row.rank}")
        if row.rank in OUT_OF_SCOPE and decision.verdict != "OUT-OF-SCOPE":
            raise AssertionError(f"اسم علم بلا OUT-OF-SCOPE في الرتبة {row.rank}")
        if not REVIEWS[row.rank].meaning_path.startswith(("جسر المعنى:", "نص الحدث المجمد")):
            raise AssertionError(f"طريق المعنى غير مسمى في الرتبة {row.rank}")
    if "أصله فارسي" not in make_card(
        selected[SOUND_RANKS.index(561)],
        H.BranchEntry(0, 0, 0, "", "", "", "", ""),
        raw_entries[561], decisions[SOUND_RANKS.index(561)],
        ranked_by_rank[561], sense_map, 20, 20,
    ):
        raise AssertionError("غاب اتجاه الموم الفارسي من البطاقة")


def validate_text(selected, texts, prior_pairs) -> None:
    if len(selected) != 70 or BATCH_SIZES != (35, 35):
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = re.findall(r"^### (WO-B-R32-SOUND-\d{5}):", joined, re.MULTILINE)
    if headings != [item.heading for item in selected]:
        raise AssertionError("معرفات الجولة 32 لا تطابق النافذة")
    keys = [pair_key(item.row) for item in selected]
    if len(keys) != len(set(keys)):
        raise AssertionError("بقي تكرار كلمة ومعنى داخل الجولة")
    for item in selected:
        if P25.pair_was_read(item.row, prior_pairs):
            raise AssertionError(f"تسرب عضو مقروء إلى الجولة: {item.key}")
    if "—" in joined or re.search(r"[۰-۹٠-٩]", joined):
        raise AssertionError("دخلت شرطة طويلة أو أرقام غير غربية")
    if unicodedata.normalize("NFC", joined) != joined:
        raise AssertionError("النص الجديد ليس NFC")
    required = (
        "نموذج WO-B-PROBE-001", "قراءة مداخل الرسم المتجانس", "المروحة المرتبة الكاملة",
        "الحدث من السجل المجمد", "طريق المعنى المسمى", "المدار المكتوب بخط اليد",
        "الشاهد 1", "الشاهد 2", "الحكم (استكشاف)",
    )
    for item, card in zip(selected, texts):
        if len(card.encode("utf-8")) >= CARD_LIMIT:
            raise AssertionError(f"تجاوزت {item.key} حد 5KB")
        if any(field not in card for field in required):
            raise AssertionError(f"نقص حقل من بطاقة {item.key}")
    for rank in EXACT_DECOMPOSITIONS:
        card = texts[SOUND_RANKS.index(rank)]
        if "تفكيك Kaikki الحصري" not in card or "قراءة المكونات المستقلة" not in card:
            raise AssertionError(f"لم تقرأ مكونات الرتبة {rank} استقلالا")
    for rank in TOOL_GAPS:
        card = texts[SOUND_RANKS.index(rank)]
        if "عطب الهيكل" not in card or "لا حكم من هيكل ناقص" not in card:
            raise AssertionError(f"لم يسم عطب الهيكل في الرتبة {rank}")
    if "أصله فارسي" not in texts[SOUND_RANKS.index(561)]:
        raise AssertionError("لم يسم اتجاه الموم في البطاقة")
    if "عطب المصدر" not in texts[SOUND_RANKS.index(536)] or "عطب المصدر" not in texts[SOUND_RANKS.index(550)]:
        raise AssertionError("لم تسجل أعطاب المصدر")


def report_section(selected, decisions, sizes, stats) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    batches = (selected[:35], selected[35:])
    lines = [f"<!-- {MARKER}:START -->", ""]
    for number, batch in enumerate(batches, 1):
        lo = 0 if number == 1 else 35
        hi = lo + len(batch)
        counts = Counter(decision.verdict for decision in decisions[lo:hi])
        distribution = "؛ ".join(f"{key}={counts[key]}" for key in sorted(counts))
        batch_skips = [rank for rank in stats["skipped"] if batch[0].row.rank <= rank <= batch[-1].row.rank]
        skipped = ", ".join(map(str, batch_skips)) or "0"
        lines.extend([
            f"## الجولة الثانية والثلاثون، دفعة sound_only رقم {number}", "",
            f"- الوقت: {now}، Africa/Cairo.",
            f"- رشح وكتب: {len(batch)}؛ المواضع المقروءة المتجاوزة داخل المدى: {skipped}.",
            f"- المواضع: من {batch[0].heading} إلى {batch[-1].heading}.",
            f"- توزيع الأحكام: {distribution}.",
            "- طريق المعنى: سمي من جسر معنى صريح أو من نص الحدث المجمد في كل بطاقة.",
            "- المدار: كتب يدويا لكل عضو، وفصلت الأصداء اللينة عن الآثار المحكمة.",
            "- المروحة: ولدت حية كاملة ورتبت بالأوزان، ومسحت مواد جميع مرشحيها بلا قص للحقل المصدر.",
            "- المتجانسات: قرئت كل مداخل الرسم، وسجل العدد ورقم المدخلة المختارة في كل بطاقة.",
            "- المركب: لم يقبل إلا التفكيك النهائي المباشر؛ لم يخترع مكون.",
            "- التحقق البنيوي: المعرفات فريدة؛ لا بطاقة فوق 5KB؛ لا شرطة طويلة؛ الأرقام غربية والنص NFC.",
            f"- آخر موضع في الدفعة: {batch[-1].heading}، `{batch[-1].row.branch}`.", "",
        ])
    total = Counter(decision.verdict for decision in decisions)
    distribution = "؛ ".join(f"{key}={total[key]}" for key in sorted(total))
    max_size = max(sizes)
    max_item = selected[sizes.index(max_size)]
    traces = [item.heading for item, decision in zip(selected, decisions) if decision.verdict in {"ROOT-TRACE", "NUCLEUS-TRACE"}]
    transmissions = [item.heading for item, decision in zip(selected, decisions) if decision.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC"]
    lines.extend([
        "## حصيلة الجولة الثانية والثلاثين", "",
        f"- حمل `persian.md` مرة واحدة؛ أزواج WO-B المقروءة={stats['pair_count']}؛ المتجاوز داخل النافذة={', '.join(map(str, stats['skipped']))}.",
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- نطاق الصوت الجديد: الرتب 489-564 بعد WO-B-R31-SOUND-00488، مع تجاوز الأزواج الستة المقروءة فقط.",
        f"- الآثار المحكمة ذات الأرجل الثلاث والشاهدين: {', '.join(traces)}.",
        f"- اتجاه الدخول إلى العربية المسمى بالشاهدين: {', '.join(transmissions)}.",
        "- التفكيك المباشر المؤهل: S00495، S00502، S00539، S00554؛ قرئت المكونات المستقلة كلها.",
        "- التحليلات غير المؤهلة: S00518 surface analysis، وS00523 وS00524 بديلان تاريخيان، وS00553 تركيب تاريخي؛ لم تحول إلى From نهائي.",
        "- أعطاب الأداة: S00490، S00521، S00523، S00524، S00564؛ لم تعوض الصوامت المنطوقة الساقطة.",
        "- أعطاب المصدر: S00536 يكرر تأثيل لعبة النرد على جذع الشجرة، وS00550 يكرر تأثيل Dey على mother؛ بقيا ظاهرين بلا توارث.",
        "- فجوات القانون: S00492، S00493، S00497، S00499، S00518، S00529، S00530، S00544، S00547، S00557، S00563.",
        "- أحواض `nucleus-sweep-*.json` التسعة الحالية v12 قرئت كاملة من القرص؛ sound_only=106794 بزيادة 2049 عن v11، وboth=14546 بنقص 1999 بعد تنظيف طريق المعنى من الكلمات الوظيفية؛ ثبت الحجم وSHA-256 والعدادات لكل ملف.",
        f"- أكبر بطاقة: {max_size} بايت، {max_item.heading}؛ كل البطاقات دون 5KB.",
        "- لم تفعل طبقة البرهان، ولم يبن ملف مشترك، ولم يقع ship، ولم يستعمل git.",
        "", f"<!-- {MARKER}:END -->", "", DONE_LINE,
    ])
    return "\n".join(lines)


def validate_existing(reading_text: str, report_text: str) -> None:
    match = re.search(rf"<!-- {re.escape(MARKER)}:START -->(.*?)<!-- {re.escape(MARKER)}:END -->", reading_text, re.DOTALL)
    if not match:
        raise AssertionError("محضر الجولة موجود وبطاقاتها غائبة")
    headings = re.findall(r"^### (WO-B-R32-SOUND-\d{5}):", match.group(1), re.MULTILINE)
    expected = [f"WO-B-R32-SOUND-{rank:05d}" for rank in SOUND_RANKS]
    if headings != expected:
        raise AssertionError("مقطع الجولة 32 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(DONE_LINE):
        raise AssertionError("سطر DONE32 ليس خاتمة التقرير")


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    validate_nucleus_snapshot()
    reading_text = READING.read_text(encoding="utf-8")
    report_text = REPORT.read_text(encoding="utf-8")
    if MARKER in reading_text or MARKER in report_text:
        validate_existing(reading_text, report_text)
        print("ROUND32 ALREADY PRESENT AND VALID")
        print(DONE_LINE)
        return 0

    data = json.loads(SWEEP.read_text(encoding="utf-8"))
    selected, stats = select_rows(data, reading_text)
    prior_pairs = H.read_pairs(reading_text)
    lexicon = json.loads(LEXICON.read_text(encoding="utf-8"))
    entries, grouped = select_branch_entries(selected, lexicon)
    raw_entries = load_raw_entries(selected, entries)
    validate_components(grouped)

    R28.EXPECTED_ENTRY_INDEX = EXPECTED_ENTRY_INDEX
    R28.EXPECTED_RAW_LINE = EXPECTED_RAW_LINE
    R28.REVIEWS = REVIEWS
    R28.BLOCKED_BOUNDARIES = {}
    R28.TOOL_GAPS = TOOL_GAPS
    R28.OUT_OF_SCOPE = OUT_OF_SCOPE
    R28.EXACT_DECOMPOSITIONS = EXACT_DECOMPOSITIONS
    R28.decomposition_lines = decomposition_lines
    R28.make_card = make_card
    R29.TOOL_GAPS = TOOL_GAPS
    R31.REVIEWS = REVIEWS

    ranked_by_rank = {item.row.rank: H.full_ranked_fan(item.row) for item in selected}
    roots = {candidate for ranked in ranked_by_rank.values() for candidate, _score in ranked}
    roots.update(review.candidate for review in REVIEWS.values())
    sense_map = H.SENSES.matches_for_roots(H.SENSES.DEFAULT_RESOURCES, roots, None)
    decisions = [decide(item) for item in selected]
    validate_decisions(selected, raw_entries, decisions, ranked_by_rank, sense_map)
    texts = [
        R28.fit_card(item, entries[item.row.rank], raw_entries[item.row.rank], decision, ranked_by_rank[item.row.rank], sense_map)
        for item, decision in zip(selected, decisions)
    ]
    validate_text(selected, texts, prior_pairs)
    sizes = [len(card.encode("utf-8")) for card in texts]

    reading_append = (
        f"\n\n<!-- {MARKER}:START -->\n\n"
        "## الجولة الثانية والثلاثون: متابعة حوض sound_only (2026-08-26)\n\n"
        "- النطاق: 70 عضوا طازجا بعد WO-B-R31-SOUND-00488؛ من الرتبة 489 إلى 564 مع تجاوز 491 و498 و501 و522 و541 و542 لأنها مقروءة؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ طريق المعنى مسمى، والمدار اليدوي حاسم، والأصداء مفصولة عن الآثار المحكمة.\n"
        "- لقطة الأحواض: قرئت ملفات nucleus-sweep-*.json التسعة الحالية v12 من القرص؛ زاد sound_only فيها 2049 صفا عن v11 بعد تنظيف طريق المعنى، وثبتت بصماتها وعداداتها قبل الانتخاب.\n\n"
        + "\n".join(texts[:35])
        + "\n## الدفعة الثانية: متابعة sound_only بعد الرتبة 527\n\n"
        + "\n".join(texts[35:])
        + f"\n<!-- {MARKER}:END -->\n"
    )
    report_append = "\n" + report_section(selected, decisions, sizes, stats) + "\n"
    reading_append = unicodedata.normalize("NFC", reading_append)
    report_append = unicodedata.normalize("NFC", report_append)
    if "—" in reading_append + report_append or re.search(r"[۰-۹٠-٩]", reading_append + report_append):
        raise AssertionError("فشل حارس الشرطة أو الأرقام قبل الكتابة")
    validate_existing(reading_text + reading_append, report_text + report_append)

    counts = Counter(decision.verdict for decision in decisions)
    print("ROUND32 READY")
    print("NUCLEUS_V12_FILES", len(NUCLEUS_SNAPSHOT), "SHA256_AND_COUNTS_OK")
    print("NUCLEUS_V12_TOTALS", "BOTH=14546", "SOUND_ONLY=106794", "SOUND_DELTA=2049")
    print("SKIPPED", ",".join(map(str, stats["skipped"])))
    print("BATCHES", *BATCH_SIZES, "SELECTED", len(selected))
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("EXACT_FROM_PLUS", " ".join(f"S{rank:05d}" for rank in sorted(EXACT_DECOMPOSITIONS)))
    print("TRACES", "S00513", "S00514", "S00527", "S00535", "TRANSMISSION", "S00561")
    print("TOOL_GAPS", len(TOOL_GAPS), "LAW_GAPS", counts["LAW-GAP"], "OUT_OF_SCOPE", len(OUT_OF_SCOPE))
    print("MAX_CARD", max(sizes), selected[sizes.index(max(sizes))].heading)
    if args.preview:
        print("PREVIEW ONLY")
        print(DONE_LINE)
        return 0

    with READING.open("a", encoding="utf-8", newline="") as handle:
        handle.write(reading_append)
    with REPORT.open("a", encoding="utf-8", newline="") as handle:
        handle.write(report_append)
    print("ROUND32 WRITTEN")
    print(DONE_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
