# -*- coding: utf-8 -*-
"""المسار B، الجولة 33: متابعة حوض sound_only في دفعتين من 35 بطاقة."""

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

import harvest_persian_round32 as R32  # noqa: E402

R31 = R32.R31
R30 = R32.R30
R29 = R32.R29
R28 = R32.R28
H = R32.H
P = R32.P
P25 = R32.P25
READING = ROOT / "04-cross-linguistic" / "readings" / "persian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-B.md"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-persian.json"
NUCLEUS_DIR = ROOT / "04-cross-linguistic" / "exploration"
LEXICON = ROOT / "data" / "branch-lexicons" / "persian.json"
RAW_LEXICON = ROOT / "Resources" / "persian" / "kaikki.org-dictionary-Persian.jsonl"
MARKER = "LANE-B-PERSIAN-ROUND33-2026-08-26"
CARD_LIMIT = 5120
SOUND_RANKS = (
    565, 566, 567, 568, 569, 570, 572, 573, 574, 576, 577, 578, 580, 581,
    582, 583, 584, 585, 586, 587, 588, 589, 590, 591, 592, 593, 594, 595,
    596, 597, 599, 600, 601, 602, 603, 604, 605, 606, 607, 608, 609, 610,
    611, 612, 613, 614, 616, 617, 618, 619, 620, 621, 622, 623, 624, 625,
    626, 627, 628, 629, 630, 631, 632, 633, 634, 635, 636, 637, 638, 640,
)
BATCH_SIZES = (35, 35)
DONE_LINE = "LANE-B DONE33 70 WO-B-R33-SOUND-00640"
EXPECTED_SKIPS = (571, 575, 579, 598, 615, 639)

# النسخة الثالثة عشرة المقروءة من القرص. العدادان الكليان لم يتغيرا عن v12،
# لكن سبعة ملفات أعيد بناؤها بعد إصلاح تحليل الصور الصرفية.
NUCLEUS_SNAPSHOT = {
    "nucleus-sweep-ancient_greek.json": (7976093, "4c2eafc719b56438c68b775988845e2412d980b6d75f2830111f63d8f15423d9", 2330, 16775),
    "nucleus-sweep-english_middle.json": (3417949, "799770fad28e1e45a1dc62de5368513aa7adf1aaf00fe8966e888fbacaa63bf7", 1414, 7991),
    "nucleus-sweep-english_old.json": (1306531, "3963463824309e4400fe701da083eda1920e067aec6ad01fe960149705bb07e4", 474, 3414),
    "nucleus-sweep-gothic.json": (1455507, "fae05087410f429023199293acf8484b4bb4f38f94e3d4b595eec32188742f46", 340, 3078),
    "nucleus-sweep-latin.json": (18840240, "5ff34ddf45aa660c6cba65d2046e18c42d92fd0cfe4ea93fd853df54b8d000c9", 6598, 39460),
    "nucleus-sweep-old_irish.json": (952787, "7aaa1d45242c3dd011824434105ab36d92db10fe23d7f466f7f2e96d95f88153", 278, 2740),
    "nucleus-sweep-old_norse.json": (1380179, "89b882b5692764f349a52de93c23665324733c498edde6d435e7423f4d99ab4b", 476, 3751),
    "nucleus-sweep-persian.json": (5458517, "555593ff42aa888d8c4095a68acee7eb1c86725df7a7a15b9312a0c999377908", 1448, 13498),
    "nucleus-sweep-welsh.json": (5777180, "740410bd00fb9b720c420b85c283eb3be04893828a72b97f3c48554d1654292b", 1188, 16087),
}

EXPECTED_ENTRY_INDEX = dict(zip(SOUND_RANKS, (
    2556, 2557, 2569, 2574, 2576, 2581, 2601, 2604, 2607, 2633,
    2635, 2640, 2656, 2657, 2658, 2659, 2675, 2686, 2693, 2705,
    2715, 2717, 2719, 2720, 2724, 2725, 2752, 2753, 2763, 2764,
    2773, 2774, 2775, 2776, 2799, 2835, 2859, 2860, 2861, 2865,
    2871, 2873, 2875, 2877, 2878, 2880, 2893, 2903, 2904, 2905,
    2909, 2910, 2912, 2917, 2918, 2921, 2930, 2933, 2935, 2936,
    2941, 2946, 2954, 2964, 2965, 2967, 2972, 2974, 2976, 2985,
)))

EXPECTED_RAW_LINE = dict(zip(SOUND_RANKS, (
    2770, 2771, 2789, 2806, 2808, 2822, 2860, 2867, 2871, 2899,
    2902, 2907, 2923, 2924, 2925, 2926, 2946, 2958, 2965, 2979,
    2990, 2992, 2994, 2995, 2999, 3000, 3027, 3028, 3039, 3040,
    3050, 3051, 3052, 3053, 3077, 3114, 3138, 3139, 3140, 3144,
    3150, 3152, 3155, 3157, 3158, 3161, 3176, 3187, 3188, 3190,
    3194, 3196, 3199, 3204, 3205, 3208, 3219, 3222, 3224, 3225,
    3231, 3237, 3246, 3258, 3260, 3262, 3267, 3270, 3274, 3286,
)))

PARSER_FROM_PLUS = {597, 600, 601, 602, 623, 624, 628, 640}
EXACT_DECOMPOSITIONS = PARSER_FROM_PLUS | {599}
EXPECTED_COMPONENTS = {
    597: ("پشیمان", "ـی"),
    599: ("خانه", "واده"),
    600: ("دید", "ـگاه"),
    601: ("کار", "ـگاه"),
    602: ("داد", "ـگاه"),
    623: ("گروه", "ـی"),
    624: ("گروه", "ـی"),
    628: ("خانه", "ـگی"),
    640: ("خوک", "ـچه"),
}
COMPONENT_READINGS = {
    597: "`پشیمان`: entries[2763] والخام 3039 لمعنى regretful أو penitent، ومروحتها 6: OPEN-CANDIDATE. `ـی`: قُرئت entries[6328-6331] والخام 7420-7424؛ المختارة لاحقة الاسم المجرد entries[6330] والخام 7422: MORPHOLOGY-GAP.",
    599: "`خانه`: entries[262] والخام 274 لمعنى house، ومروحتها 30: OPEN-CANDIDATE. `واده`: غائبة من branch-lexicons ومن الخام، والخبر نفسه يجعل صلتها بـ`āwādag` محتملة: COMPONENT-GAP.",
    600: "`دید`: غائبة من branch-lexicons وحاضرة في الخام 11866 صورة ماض من `دیدن`: FORM-LINK. `ـگاه`: entries[7462] والخام 8752 لاحقة مكان أو زمان، ومروحتها 72: MORPHOLOGY-GAP.",
    601: "`کار`: entries[797] والخام 847 لمعنى work أو deed، ومروحتها 40: OPEN-CANDIDATE. `ـگاه`: entries[7462] والخام 8752 لاحقة مكان أو زمان: MORPHOLOGY-GAP.",
    602: "`داد`: entries[2974] والخام 3270 لمعنى justice أو shout، ومروحتها 90: OPEN-CANDIDATE. `ـگاه`: entries[7462] والخام 8752 لاحقة مكان أو زمان: MORPHOLOGY-GAP.",
    623: "`گروه`: entries[1600] والخام 1684 لمعنى group، ومروحتها 80: OPEN-CANDIDATE. `ـی`: قُرئت entries[6328-6331] والخام 7420-7424؛ المختارة لاحقة التنكير entries[6328] والخام 7420: MORPHOLOGY-GAP.",
    624: "`گروه`: entries[1600] والخام 1684 لمعنى group، ومروحتها 80: OPEN-CANDIDATE. `ـی`: قُرئت entries[6328-6331] والخام 7420-7424؛ المختارة لاحقة الصفة entries[6329] والخام 7421: MORPHOLOGY-GAP.",
    628: "`خانه`: entries[262] والخام 274 لمعنى house، ومروحتها 30: OPEN-CANDIDATE. `ـگی`: غائبة من branch-lexicons وحاضرة في الخام 17716 صورة لاحقة `ـی` بعد الهاء القصيرة: MORPHOLOGY-GAP.",
    640: "`خوک`: entries[869] والخام 925 لمعنى pig، ومروحتها 60: OPEN-CANDIDATE. `ـچه`: entries[7514] والخام 8808 لاحقة تصغير، ومروحتها 60: MORPHOLOGY-GAP.",
}

REJECTED_ANALYSES = {
    592: "يسمي الخبر By surface analysis مكوني `دیو` و`ـانه` بعد تأثيل موروث مستقل، فلا يحول التحليل السطحي إلى From نهائي.",
    593: "يسمي الخبر By surface analysis مكوني `دیو` و`ـانه` بعد تأثيل موروث مستقل، فلا يحول التحليل السطحي إلى From نهائي.",
    606: "يسمي الخبر الصورة synchronically analyzable إلى جزأين بعد صورة موروثة، لا تفكيكا نهائيا حصريا للصورة.",
    607: "يسمي الخبر الصورة synchronically analyzable إلى جزأين بعد صورة موروثة، لا تفكيكا نهائيا حصريا للصورة.",
    613: "يعرض الخبر By surface analysis `باد` و`بان` بعد الصورة الوسطى الموروثة، لا From نهائيا مباشرا.",
    622: "يعرض الخبر By surface analysis `دار` و`چین` بعد شجرة تاريخية متعددة، لا From نهائيا مباشرا.",
    636: "يعرض الخبر By surface analysis `آباد` و`ـی` بعد الصورة الوسطى الموروثة، لا From نهائيا مباشرا.",
}
TOOL_GAPS = {
    583: "الصورة `نیاز` منقوطة /niyāz/، لكن الهيكل أسقط /y/ المنطوقة.",
    592: "الصورة `دیوانه` منقوطة /dēwāna/، لكن الهيكل أسقط /w/ المنطوقة.",
    593: "الصورة `دیوانه` منقوطة /dēwāna/، لكن الهيكل أسقط /w/ المنطوقة.",
    594: "الصورة `بسیار` منقوطة /bisyār/، لكن الهيكل أسقط /y/ المنطوقة.",
    595: "الصورة `بسیار` منقوطة /bisyār/، لكن الهيكل أسقط /y/ المنطوقة.",
    608: "الصورة `دلواپسی` منقوطة /delvāpasi/، لكن الهيكل أسقط /v/ المنطوقة.",
    612: "الصورة `دویدن` منقوطة /dawīdan/، لكن الهيكل أسقط /w/ المنطوقة.",
    629: "الصورة `پرواز` منقوطة /parwāz/، لكن الهيكل أسقط /w/ المنطوقة.",
    631: "الصورة `کاروان` منقوطة /kārwān/، لكن الهيكل أسقط /w/ المنطوقة.",
}
LAW_GAPS = {567, 587, 589, 610, 611, 613, 616, 617, 618, 619, 621, 622, 630, 635, 636}

SOURCE_NOTES = {
    568: "خبر الأصل يسمّي العربية `تَخْتَج` اقتراضا إيرانيا أوسط، لكن معنى الصف مصنف عد البطاطين والسجاد، لا وعاء الثياب العربي؛ حفظ الاتجاه حاشية بلا حكم تماس.",
    584: "خبر الأصل يسمّي `سَفَط` العربية آتية عبر الآرامية من الإيرانية الوسطى لمعنى السلة، لكن صورتها خارج المروحة الحية وتحتاج صفوف ب↔ف ود↔ط؛ لم تدخل بديلا حدسيا.",
    589: "خبر الأصل يفصل path الموروثة عن lawn وmeadow المقترضتين من التركية؛ لم يورث معنى أحد الطريقين للآخر.",
    625: "خبر الأصل يذكر العربية `شَلْجَم` في شبكة ألفاظ اللفت، لكنها خارج المروحة الحية وتحتاج غ↔ج؛ بقيت حاشية اتصال لا حكما.",
    637: "خبر الأصل يسمّي السريانية والعبرية والأرمنية مقترضات إيرانية لمعنى القانون، ولا يسمّي العربية؛ بقي اتجاه النقل حاشية لا إغلاقا عربيا.",
}


@dataclass(frozen=True)
class SelectedRow:
    row: H.SweepRow

    @property
    def key(self) -> str:
        return f"S{self.row.rank:05d}"

    @property
    def heading(self) -> str:
        return f"WO-B-R33-SOUND-{self.row.rank:05d}"


Review = R29.Review
R = R29.R

# سجل قراءة يدوي. لا يشتق الحكم من best ولا من وزن المروحة.
REVIEWS = {
    565: R("هم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`هم`: تسيب أثناء الشيء ذوبانا؛ لا يسمي all أو everyone.", "شمول الأفراد حكم كمي لا ذوبان لهم، وشاهدا العربية في الهم والحزن."),
    566: R("هم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`هم`: تسيب أثناء الشيء ذوبانا؛ لا يسمي every.", "استغراق كل عضو في الحكم لا يساوي تسيبه، وفصلت الصفة عن الضمير السابق."),
    567: R("اشب", "LAW-GAP", "نص الحدث المجمد لـ`اشب`: محاكم حروف بلا معنى riot أو turmoil، وصف آ↔ا غير مسمى.", "الاضطراب قد يشتمل على انتشار وحبس، لكن ذلك لا يثبت المعنى وفوقه فجوة القانون."),
    568: R("تخت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تخت`: محاكم حروف بلا معنى classifier.", "عد البطاطين وظيفة نحوية لا معنى الوعاء العربي، والتعريب المذكور يخص صورة ومعنى آخرين."),
    569: R("جسل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جسل`: اختراق حسي أو معنوي مع اللام؛ لا يسمي calf.", "جلوس العجل أو بروز جسمه وصف عارض لا معنى الحيوان، ولا شاهد عربي ثان للمادة."),
    570: R("بلك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بلك`: التمكن والحوز بشدة؛ لا يسمي eyelid.", "إحاطة الجفن بالعين وظيفة للعضو لا معناه، وشاهدا العربية في تحريك الأشداق."),
    572: R("جسن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جسن`: الاختراق الحسي أو المعنوي؛ لا يسمي celebration أو feast.", "اجتماع المحتفلين سياق للمهرجان لا معنى الاحتفال، وشاهدا العربية في الجنس والجسنة."),
    573: R("رز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رز`: التداخل الشديد؛ لا يسمي fast أو abstinence.", "تداخل زمن الصوم في اليوم ترتيب زمني لا معنى الإمساك عن الطعام."),
    574: R("المس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`المس`: محاكم أربعة حروف بلا معنى diamond.", "الصلابة واللمعان صفتان للألماس لا تستخرجان من المحاكم، ولا شاهدان عربيان للمادة."),
    576: R("هو", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`هو`: محكمتا الهاء والواو بلا معنى pus.", "خروج القيح من الجرح حركة لاحقة لا معنى المادة، ولا شاهد عربي ثان."),
    577: R("هم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`هم`: تسيب أثناء الشيء ذوبانا؛ لا يسمي lammergeier أو Huma bird.", "طيران الطائر في الهواء وصف للحركة لا معنى النوع، وفصل الاسم العام عن العلم المتجانس."),
    578: R("سمسر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سمسر`: خرق يضم مع الراء؛ لا يسمي sword أو scimitar.", "خرق السيف للجسم وظيفة لاستعماله، وشاهدا العربية في السمسار المعرب لا السلاح."),
    580: R("لنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`لنج`: محاكم حروف بلا معنى lame أو limp.", "اختلال المشي نتيجة العرج لا حدث حروفي محكوم، وشاهدا العربية في عود طيب."),
    581: R("لنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`لنج`: محاكم حروف بلا معنى leg.", "امتداد الرجل هيئة عامة للأعضاء الطويلة لا معنى الجارحة، وفصلت المتجانس عن العرج."),
    582: R("لنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`لنج`: محاكم حروف بلا معنى towel.", "التفاف المنشفة بالجسم فعل استعمال لا معنى النسيج، والخبر يردها إلى صورة أطول."),
    583: R("نز", "TOOL-GAP", "جسر المعنى: need أو scarcity حاضر، لكن /niyāz/ يحمل /y/ أسقطها الهيكل.", "أوقف الصامت الساقط المقارنة قبل تحويل النقص إلى نفاذ أو خفة."),
    584: R("سبد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سبد`: امتداد دقيق متصل مع الدال؛ لا يسمي basket.", "احتواء السلة لما يوضع فيها وظيفة عامة، والصورة العربية المسماة في الخبر خارج المروحة."),
    585: R("كد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كد`: التعامل مع قشر شديد اللصوق؛ لا يسمي manure أو heap.", "تكديس الحبوب فعل على الكومة لا معنى السماد، وشاهدا العربية في شدة العمل."),
    586: R("بت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بت`: القطع والانفصال؛ لا يسمي blanket.", "قطع القماش مرحلة صناعة لا معنى الغطاء، وخبر الأصل يسمي قرضا هنديا آريا."),
    587: R("نجد", "LAW-GAP", "نص الحدث المجمد لـ`نجد`: الرفع مع الشدة؛ لا يسمي lineage أو race، وصف ژ↔ج غير مسمى.", "ارتفاع النسب استعارة اجتماعية لا معنى السلالة، وفوقها فجوة القانون."),
    588: R("جرن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جرن`: الاسترسال والامتداد مع النون؛ لا يسمي expensive أو heavy.", "ثقل الشيء يقاوم الحركة ولا يساوي امتدادها، وشاهدا العربية في مقدم العنق واللين."),
    589: R("جمن", "LAW-GAP", "نص الحدث المجمد لـ`جمن`: التجمع والكثرة؛ لا يسمي path أو lawn، وصف چ↔ج غير مسمى.", "اجتماع العشب في المرج وصف للمادة لا معنى الطريق أو المرج، وفوقه فصل المصدر وفجوة القانون."),
    590: R("مصت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مصت`: استخلاص الشيء أو أخذه؛ لا يسمي drunk أو happy.", "غلبة الشراب على الشارب نتيجة سكر لا معنى الاستخلاص، وشاهدا العربية في قبض الرحم."),
    591: R("مصت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مصت`: استخلاص الشيء أو أخذه؛ لا يسمي drunkard أو Sufi.", "الاستغراق في الحب الصوفي وصف مجازي للسكر لا حدث الاستخلاص، وفصلت الاسم عن الصفة."),
    592: R("دن", "TOOL-GAP", "جسر المعنى: mad أو insane حاضر، لكن /dēwāna/ يحمل /w/ أسقطها الهيكل.", "رفضت التحليل السطحي ثم أوقف الصامت الساقط الحكم قبل أي مدار للجنون."),
    593: R("دن", "TOOL-GAP", "جسر المعنى: madman حاضر، لكن /dēwāna/ يحمل /w/ أسقطها الهيكل.", "فصلت الاسم عن الصفة ورفضت التحليل السطحي ثم أوقف الصامت الساقط الحكم."),
    594: R("بسر", "TOOL-GAP", "جسر المعنى: many حاضر، لكن /bisyār/ يحمل /y/ أسقطها الهيكل.", "أوقف الصامت الساقط المقارنة قبل ربط الكثرة بالإعجال أو القهر."),
    595: R("بسر", "TOOL-GAP", "جسر المعنى: very حاضر، لكن /bisyār/ يحمل /y/ أسقطها الهيكل.", "فصلت الظرف عن الصفة السابقة ثم أوقف الصامت الساقط الحكم."),
    596: R("بشمن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بشمن`: الانتشار الظاهر مع الميم؛ لا يسمي regret أو penitence.", "ظهور الندم على الوجه أثر للشعور لا معناه، ولا شاهد عربي ثان مستقل."),
    597: R("بشمن", "COMPOUND-BOUNDARY", "جسر المعنى: remorse مفككة مباشرة إلى `پشیمان` و`ـی`.", "قُرئ الأصل واللاحقة استقلالا؛ وقفت الصورة عند الحد الصرفي ولم تورث حكم الصفة."),
    599: R("حند", "COMPOUND-BOUNDARY", "جسر المعنى: family أو household مصرح بتركيبها من `خانه` و`واده`.", "قُرئ المنزل، وسجل غياب المكون الثاني وعدم يقين أصله؛ لم يخترع له معنى أو حكم."),
    600: R("ددق", "COMPOUND-BOUNDARY", "جسر المعنى: viewpoint مفككة مباشرة إلى `دید` و`ـگاه`.", "قُرئت صورة الماضي ولاحقة المكان استقلالا؛ لم تورث الصورة المجموعة حكم الرؤية."),
    601: R("كرج", "COMPOUND-BOUNDARY", "جسر المعنى: workshop مفككة مباشرة إلى `کار` و`ـگاه`.", "قُرئ العمل ولاحقة المكان استقلالا؛ وقف الحكم عند المركب."),
    602: R("ددق", "COMPOUND-BOUNDARY", "جسر المعنى: court مفككة مباشرة إلى `داد` و`ـگاه`.", "قُرئت العدالة ولاحقة المكان استقلالا؛ لم تورث المحكمة حكم المكون."),
    603: R("برد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`برد`: تقلص المتسيب وتجمده؛ لا يسمي curtain أو veil.", "انقباض الستارة عند جمعها هيئة عرضية لا معنى الحجاب، وشاهدا العربية في البرد."),
    604: R("بو", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بو`: الوصول؛ لا يسمي smell أو scent.", "وصول الرائحة إلى الأنف انتقال للأثر لا معنى الرائحة، ولا شاهدان عربيان مستقلان."),
    605: R("برز", "ROOT-TRACE", "جسر المعنى: victory خروج الغالب ظاهرا بقوة من بين ما يكتنفه، وهو نص الحدث المجمد لـ`برز`.", "مدار 1: الظفر بروز قوي بعد صراع؛ وشاهدا العربية يثبتان الخروج إلى الفضاء والمبارزة."),
    606: R("برن", "NUCLEUS-TRACE", "جسر المعنى: the outside هو جهة التجرد والخلوص من الداخل، وهو نص النواة التي نزل إليها `برن`.", "مدار 1: الخارج ما خلص من جوف الشيء وبرز عنه؛ الحكم نووي لأن السجل نزل من الجذر إلى `بر`."),
    607: R("برن", "NUCLEUS-TRACE", "جسر المعنى: outside أو out انتقال إلى جهة التجرد والخلوص، وهو نص النواة التي نزل إليها `برن`.", "مدار 1: الخروج تخليص للشيء من باطن محيطه؛ فصلت حرف الجر عن الاسم وحكمت بالنواة نفسها."),
    608: R("دربس", "TOOL-GAP", "جسر المعنى: worry حاضر، لكن /delvāpasi/ يحمل /v/ أسقطها الهيكل.", "أوقف الصامت الساقط الحكم قبل تحويل استمرار القلق إلى جريان أو امتداد."),
    609: R("زر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زر`: نفاذ بدقة مع إمساك؛ لا يسمي under أو beneath.", "الوقوع تحت الشيء علاقة مكانية لا نفاذ ولا إمساك، وشاهدا العربية في الطرد والزر."),
    610: R("دهقن", "LAW-GAP", "نص الحدث المجمد لـ`دهقن`: الحدر أو الدفع في فراغ؛ لا يسمي settlers، وصف گ↔ق غير مسمى.", "شاهد العربية يثبت الدهقان المعرب لكنه لا يسد صف الصوت ولا يطابق جمع السكان الحضريين."),
    611: R("ثند", "LAW-GAP", "نص الحدث المجمد لـ`ثند`: التبطن والكثرة في الداخل؛ لا يسمي fast أو spicy، وصف ت↔ث غير مسمى.", "الحدة والسرعة في قاموس الفرع لا تساوي كثرة اللحم في العربية، وفوقها فجوة القانون."),
    612: R("ددن", "TOOL-GAP", "جسر المعنى: to run حاضر، لكن /dawīdan/ يحمل /w/ أسقطها الهيكل.", "أوقف الصامت الساقط الحكم قبل ربط العدو بدفعات الدال المتوالية."),
    613: R("بذبن", "LAW-GAP", "نص الحدث المجمد لـ`بذبن`: التفرق والنثر مع النون؛ لا يسمي sail، وصف د↔ذ غير مسمى.", "انتشار الشراع بالريح هيئة تشغيل لا معنى الأداة، ورفضت التحليل السطحي وفوقه فجوة القانون."),
    614: R("زن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زن`: اختزان الباطن بقوة؛ لا يسمي saddle.", "احتواء السرج للراكب أو تثبيته وظيفة للأداة لا معناها، وشاهدا العربية في التهمة."),
    616: R("جلند", "LAW-GAP", "نص الحدث المجمد لـ`جلند`: الاتساع والانكشاف؛ لا يسمي quadruped أو grazer، وصف چ↔ج غير مسمى.", "انتشار الحيوان في المرعى سياق لا معنى النوع، وفوقه فجوة القانون."),
    617: R("جق", "LAW-GAP", "نص الحدث المجمد لـ`جق`: محكمتا حرفين بلا معنى slap، وصفا چ↔ج وك↔ق غير مسميين.", "الضربة انطباق وانفجار، لكن المحكمتين لا تسميان الصفعة وفوقهما فجوتا القانون."),
    618: R("جق", "LAW-GAP", "نص الحدث المجمد لـ`جق`: محكمتا حرفين بلا معنى chin، وصفا چ↔ج وك↔ق غير مسميين.", "بروز الذقن هيئة عضو لا معناه، وفوقها فجوتا القانون."),
    619: R("جق", "LAW-GAP", "نص الحدث المجمد لـ`جق`: محكمتا حرفين بلا معنى cheque، وصفا چ↔ج وك↔ق غير مسميين.", "فصلت الصك المالي عن slap وchin، وخبر التأثير الأوروبي لا يسد فجوتي القانون."),
    620: R("دن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دن`: اندساس الشيء في أثناء أو ثباته فيه؛ لا يسمي grain.", "اندساس الحبة في التربة طور زراعة لا معنى الحبة نفسها، وشاهدا العربية في الوعاء."),
    621: R("جلند", "LAW-GAP", "نص الحدث المجمد لـ`جلند`: الاتساع والانكشاف؛ لا يسمي grazer، وصف چ↔ج غير مسمى.", "اسم الفاعل يحيل إلى الرعي، لكن انكشاف المرعى لا يساوي آكل العشب وفوقه فجوة القانون."),
    622: R("درجن", "LAW-GAP", "نص الحدث المجمد لـ`درجن`: الجريان والامتداد؛ لا يسمي cinnamon، وصف چ↔ج غير مسمى.", "رفضت التحليل السطحي، واسم الشجرة الصينية لا يساوي امتدادها وفوقه فجوة القانون."),
    623: R("جره", "COMPOUND-BOUNDARY", "جسر المعنى: group مفككة مباشرة إلى `گروه` ولاحقة التنكير `ـی`.", "قُرئ الاسم واللاحقة استقلالا؛ لم تورث الصورة المصرفة حكم أصلها."),
    624: R("جره", "COMPOUND-BOUNDARY", "جسر المعنى: collective مفككة مباشرة إلى `گروه` ولاحقة الصفة `ـی`.", "قُرئ الاسم واللاحقة استقلالا؛ فصلت الصفة عن الاسم السابق ووقف الحكم عند الصرف."),
    625: R("سلغم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سلغم`: انسحاب ممتد من الأثناء؛ لا يسمي turnip.", "شاهد العربية للمرشح في معنى الطويل، أما `شلجم` المطابقة للنبات فخارج المروحة الحية."),
    626: R("بت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بت`: القطع والانفصال؛ لا يسمي crucible.", "فصل المعدن عن خبثه وظيفة للبوتقة لا معنى الوعاء، وشاهدا العربية في القطع."),
    627: R("مرغ", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مرغ`: الاسترسال والحركة مع الغين؛ لا يسمي hen أو chicken.", "حركة الطائر سلوك مشترك لا معنى النوع، وشاهدا العربية في التمريغ بالتراب."),
    628: R("خنج", "COMPOUND-BOUNDARY", "جسر المعنى: domestic مفككة مباشرة إلى `خانه` و`ـگی`.", "قُرئ المنزل واللاحقة استقلالا؛ لم تورث الصفة ولا معنى prostitute حكم المكون."),
    629: R("برز", "TOOL-GAP", "جسر المعنى: flight يخرج فيه الطائر إلى الفضاء، لكن /parwāz/ يحمل /w/ أسقطها الهيكل.", "أوقف الصامت الساقط بطاقة واعدة قبل الحكم؛ لم يعوضه مدار البروز يدويا."),
    630: R("جرب", "LAW-GAP", "نص الحدث المجمد لـ`جرب`: الاسترسال والامتداد؛ لا يسمي fatty أو greasy، وصف چ↔ج غير مسمى.", "انتشار الدهن على السطح أثر للاستعمال لا معنى الصفة، وفوقه فجوة القانون."),
    631: R("كرن", "TOOL-GAP", "جسر المعنى: caravan أو convoy حاضر، لكن /kārwān/ يحمل /w/ أسقطها الهيكل.", "أوقف الصامت الساقط الحكم قبل تحويل توالي القافلة إلى تركز متكرر."),
    632: R("خر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خر`: تخلخل الأثناء ونقصها؛ لا يسمي thorn.", "اختراق الشوكة للنسيج وظيفة لحدها لا معنى النبات، وشاهدا العربية في الخرير."),
    633: R("تب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تب`: ضعف المتجمع أو ذهاب غلظه؛ لا يسمي heat أو glow.", "إذابة الحرارة للمادة أثر لاحق لا معنى الدفء، وشاهدا العربية في الخسران."),
    634: R("تب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تب`: ضعف المتجمع أو ذهاب غلظه؛ لا يسمي swing أو curly lock.", "تأرجح المقعد أو التفاف الشعر حركة وهيئة لا ذهاب للغلظ، وفصلت المتجانس عن الحرارة."),
    635: R("ابد", "LAW-GAP", "نص الحدث المجمد لـ`ابد`: محاكم حروف بلا معنى inhabited، وصف آ↔ا غير مسمى.", "ثبات السكان في الموضع لا يستخرج من المحاكم، وفوقه فجوة القانون."),
    636: R("ابد", "LAW-GAP", "نص الحدث المجمد لـ`ابد`: محاكم حروف بلا معنى village أو prosperity، وصف آ↔ا غير مسمى.", "رفضت التحليل السطحي وفصلت الاسم عن الصفة السابقة، وفوق ضعف المدار فجوة القانون."),
    637: R("دد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دد`: محكمتا دالين بلا معنى justice أو equity.", "إطلاق الحكم دفعة لا يساوي العدالة، وشاهدا العربية في اللهو؛ والنقل السامي لا يسمي العربية."),
    638: R("دس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دس`: النفاذ بدفع في أثناء شيء؛ لا يسمي hand.", "دفع اليد الشيء إلى الداخل وظيفة للجارحة لا معنى اليد، وشاهدا العربية في الإخفاء والدفن."),
    640: R("خكش", "COMPOUND-BOUNDARY", "جسر المعنى: piglet مفككة مباشرة إلى `خوک` ولاحقة التصغير `ـچه`.", "قُرئ الحيوان واللاحقة استقلالا؛ لم تورث الصورة المصغرة حكم الأصل ولم تعوض فجوة صف چ."),
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
            raise AssertionError(f"تغير عداد نسخة v13 في {name}")
        if len(data.get("both") or []) != expected_both or len(data.get("sound_only") or []) != expected_sound:
            raise AssertionError(f"تغير طول قوائم نسخة v13 في {name}")
        total_both += expected_both
        total_sound += expected_sound
    if total_both != 14546 or total_sound != 106794:
        raise AssertionError("تغير مجموع أحواض v13")


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
            if row.rank > 564 and len(fresh) < 70:
                internal_skips.append(row.rank)
            continue
        seen.add(key)
        if row.rank <= 564:
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


def validate_components(grouped: dict[str, list[tuple[int, dict]]]) -> None:
    expected_indices = {
        "پشیمان": {2763}, "ـی": {6328, 6329, 6330, 6331}, "خانه": {262},
        "واده": set(), "دید": set(), "ـگاه": {7462}, "کار": {797},
        "داد": {2974}, "گروه": {1600}, "ـگی": set(), "خوک": {869}, "ـچه": {7514},
    }
    fan_counts = {
        "پشیمان": 6, "ـی": 0, "خانه": 30, "واده": 57, "دید": 90,
        "ـگاه": 72, "کار": 40, "داد": 90, "گروه": 80, "ـگی": 56,
        "خوک": 60, "ـچه": 60,
    }
    for word, expected in expected_indices.items():
        actual = {index for index, _entry in grouped.get(word, [])}
        if actual != expected:
            raise AssertionError(f"تغير جرد مكون {word}: {sorted(actual)}")
        fan = tuple(H.FAN.rank(word, H.FAN.fan(word, "persian"), "persian"))
        if len(fan) != fan_counts[word]:
            raise AssertionError(f"تغيرت مروحة المكون {word}: {len(fan)}")
    expected_raw = {
        "پشیمان": {3039}, "ـی": {7420, 7421, 7422, 7423, 7424}, "خانه": {274},
        "واده": set(), "دید": {11866}, "ـگاه": {8752}, "کار": {847, 848},
        "داد": {3270, 3271}, "گروه": {1684}, "ـگی": {17716}, "خوک": {925}, "ـچه": {8808},
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
    if review.verdict == "COMPOUND-BOUNDARY":
        return "وقف الحكم عند حد المركب؛ لم تورث الصورة المجموعة حكم مكون ولم يخترع تفكيك."
    if review.verdict == "LAW-GAP":
        return "طريق المعنى مفحوص، لكن مسار الصوت يحوي صفا غير مسمى؛ لم يصدر حكم موجب."
    if review.verdict == "TOOL-GAP":
        return "صف الحوض أسقط صامتا منطوقا؛ توقف العضو قبل الحكم ولم يعوض الصامت يدويا."
    return "مسار الصوت قابل للفحص، لكن المدار لم يقم على معنى المدخلة؛ بقي المرشح مفتوحا."


def decide(item: SelectedRow) -> H.Decision:
    review = REVIEWS[item.row.rank]
    return H.Decision(review.candidate, review.verdict, H.state_for(review.verdict), review.orbit, obstacle_for(review))


def decomposition_lines(item: SelectedRow, raw: dict) -> list[str]:
    rank = item.row.rank
    if rank not in EXACT_DECOMPOSITIONS:
        return []
    if rank == 599:
        etymology = raw["etymology"]
        if "A compound composed of" not in etymology or "خانه" not in etymology or "واده" not in etymology:
            raise AssertionError("تغير التفكيك المركب المباشر للرتبة 599")
    else:
        decomposition = P25.direct_from_plus(raw["etymology"])
        if not decomposition:
            raise AssertionError(f"غاب تفكيك From X + Y للرتبة {rank}")
        joined = " + ".join(decomposition)
        for component in EXPECTED_COMPONENTS[rank]:
            if H.clean(component) not in H.clean(joined):
                raise AssertionError(f"غاب مكون {component} من الرتبة {rank}: {decomposition}")
    return [
        f"- تفكيك Kaikki الحصري المباشر من السطر الخام {raw['line']}: «{H.clip(raw['etymology'], 420)}».",
        f"- قراءة المكونات المستقلة: {COMPONENT_READINGS[rank]}",
        "- الخطوة صفر: قبل التفكيك النهائي المباشر لم تقارن الصورة وحدة جذرية؛ قُرئ كل مكون مسمى وحده.",
    ]


BASE_MAKE_CARD = R32.make_card


def make_card(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit) -> str:
    card = BASE_MAKE_CARD(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit)
    card = card.replace("الجولة 32،", "الجولة 33،")
    rank = item.row.rank
    if rank in SOURCE_NOTES and "ملاحظة المصدر الخاصة" not in card:
        card = card.replace(
            "- الخطوة صفر:",
            f"- ملاحظة المصدر الخاصة: {SOURCE_NOTES[rank]}\n- الخطوة صفر:",
            1,
        )
    return card


def validate_decisions(selected, raw_entries, decisions, ranked_by_rank, sense_map) -> None:
    if set(REVIEWS) != set(SOUND_RANKS):
        raise AssertionError("جدول المدار اليدوي لا يغطي الرتب السبعين")
    parsed = {item.row.rank for item in selected if P25.direct_from_plus(raw_entries[item.row.rank]["etymology"])}
    if parsed != PARSER_FROM_PLUS:
        raise AssertionError(f"تغيرت أسطر From X + Y المباشرة: {sorted(parsed)}")
    expected_verdicts = {
        "COMPOUND-BOUNDARY": 9,
        "LAW-GAP": 15,
        "NUCLEUS-TRACE": 2,
        "OPEN-CANDIDATE": 34,
        "ROOT-TRACE": 1,
        "TOOL-GAP": 9,
    }
    if Counter(review.verdict for review in REVIEWS.values()) != Counter(expected_verdicts):
        raise AssertionError(f"تغير توزيع الأحكام اليدوي: {Counter(review.verdict for review in REVIEWS.values())}")
    if {rank for rank, review in REVIEWS.items() if review.verdict == "ROOT-TRACE"} != {605}:
        raise AssertionError("تغير موضع ROOT-TRACE اليدوي")
    if {rank for rank, review in REVIEWS.items() if review.verdict == "NUCLEUS-TRACE"} != {606, 607}:
        raise AssertionError("تغير موضعا NUCLEUS-TRACE اليدويان")
    for item, decision in zip(selected, decisions):
        row = item.row
        candidates = {candidate for candidate, _score in ranked_by_rank[row.rank]}
        if decision.candidate not in candidates or decision.candidate not in row.candidates_found:
            raise AssertionError(f"مرشح الرتبة {row.rank} خارج المروحة الحية أو أعضاء الحوض")
        complete = H.route_complete(row, decision.candidate)
        _count, coverage, _witnesses = P.classical_witnesses(decision.candidate, sense_map, 90)
        if decision.verdict == "LAW-GAP" and complete:
            raise AssertionError(f"LAW-GAP بلا صف مفقود في الرتبة {row.rank}")
        if decision.verdict in {"OPEN-CANDIDATE", "ROOT-TRACE", "NUCLEUS-TRACE"} and not complete:
            raise AssertionError(f"حكم بمسار ناقص في الرتبة {row.rank}: {decision.verdict}")
        if decision.verdict in {"ROOT-TRACE", "NUCLEUS-TRACE"}:
            if coverage < 2 or H.event_line(decision.candidate).startswith("لا حدث"):
                raise AssertionError(f"حكم صادر بلا حدث وشاهدين في الرتبة {row.rank}")
        if row.rank in EXACT_DECOMPOSITIONS and decision.verdict != "COMPOUND-BOUNDARY":
            raise AssertionError(f"تفكيك مباشر بلا حد مركب في الرتبة {row.rank}")
        if row.rank in TOOL_GAPS and decision.verdict != "TOOL-GAP":
            raise AssertionError(f"هيكل ناقص بلا TOOL-GAP في الرتبة {row.rank}")
        if row.rank in LAW_GAPS and decision.verdict != "LAW-GAP":
            raise AssertionError(f"مسار ناقص بلا LAW-GAP في الرتبة {row.rank}")
        if not REVIEWS[row.rank].meaning_path.startswith(("جسر المعنى:", "نص الحدث المجمد")):
            raise AssertionError(f"طريق المعنى غير مسمى في الرتبة {row.rank}")


def validate_text(selected, texts, prior_pairs) -> None:
    if len(selected) != 70 or BATCH_SIZES != (35, 35):
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = re.findall(r"^### (WO-B-R33-SOUND-\d{5}):", joined, re.MULTILINE)
    if headings != [item.heading for item in selected]:
        raise AssertionError("معرفات الجولة 33 لا تطابق النافذة")
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
        if "تفكيك Kaikki الحصري المباشر" not in card or "قراءة المكونات المستقلة" not in card:
            raise AssertionError(f"لم تقرأ مكونات الرتبة {rank} استقلالا")
    for rank in TOOL_GAPS:
        card = texts[SOUND_RANKS.index(rank)]
        if "عطب الهيكل" not in card or "لا حكم من هيكل ناقص" not in card:
            raise AssertionError(f"لم يسم عطب الهيكل في الرتبة {rank}")
    for rank in REJECTED_ANALYSES:
        if "حد التحليل غير المؤهل" not in texts[SOUND_RANKS.index(rank)]:
            raise AssertionError(f"لم يسجل التحليل غير المؤهل في الرتبة {rank}")
    for rank in SOURCE_NOTES:
        if "ملاحظة المصدر الخاصة" not in texts[SOUND_RANKS.index(rank)]:
            raise AssertionError(f"لم تسجل ملاحظة المصدر في الرتبة {rank}")


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
            f"## الجولة الثالثة والثلاثون، دفعة sound_only رقم {number}", "",
            f"- الوقت: {now}، Africa/Cairo.",
            f"- رشح وكتب: {len(batch)}؛ المواضع المقروءة المتجاوزة داخل المدى: {skipped}.",
            f"- المواضع: من {batch[0].heading} إلى {batch[-1].heading}.",
            f"- توزيع الأحكام: {distribution}.",
            "- طريق المعنى: سمي من جسر معنى صريح أو من نص الحدث المجمد في كل بطاقة.",
            "- المدار: كتب يدويا لكل عضو، وفصلت الأصداء اللينة عن الآثار المحكمة.",
            "- المروحة: ولدت حية كاملة ورتبت بالأوزان، ومسحت مواد جميع مرشحيها بلا قص للحقل المصدر.",
            "- المتجانسات: قرئت كل مداخل الرسم، وسجل العدد ورقم المدخلة المختارة في كل بطاقة.",
            "- المركب: قبل From X + Y النهائي المباشر أو تصريح A compound composed of الحصري؛ لم يخترع مكون.",
            "- التحقق البنيوي: المعرفات فريدة؛ لا بطاقة فوق 5KB؛ لا شرطة طويلة؛ الأرقام غربية والنص NFC.",
            f"- آخر موضع في الدفعة: {batch[-1].heading}، `{batch[-1].row.branch}`.", "",
        ])
    total = Counter(decision.verdict for decision in decisions)
    distribution = "؛ ".join(f"{key}={total[key]}" for key in sorted(total))
    max_size = max(sizes)
    max_item = selected[sizes.index(max_size)]
    traces = [item.heading for item, decision in zip(selected, decisions) if decision.verdict in {"ROOT-TRACE", "NUCLEUS-TRACE"}]
    lines.extend([
        "## حصيلة الجولة الثالثة والثلاثين", "",
        f"- حمل `persian.md` مرة واحدة؛ أزواج WO-B المقروءة={stats['pair_count']}؛ المتجاوز داخل النافذة={', '.join(map(str, stats['skipped']))}.",
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- نطاق الصوت الجديد: الرتب 565-640 بعد WO-B-R32-SOUND-00564، مع تجاوز الأزواج الستة المقروءة فقط.",
        f"- الآثار المحكمة ذات الأرجل الثلاث والشاهدين: {', '.join(traces)}.",
        "- التفكيك المباشر المؤهل: S00597، S00599، S00600، S00601، S00602، S00623، S00624، S00628، S00640؛ قرئت المكونات المستقلة كلها.",
        "- التحليلات غير المؤهلة: S00592 وS00593 وS00613 وS00622 وS00636 سطحية، وS00606 وS00607 تحليلان تزامنيان بعد التأثيل الموروث؛ لم تحول إلى From نهائي.",
        "- أعطاب الأداة: S00583، S00592، S00593، S00594، S00595، S00608، S00612، S00629، S00631؛ لم تعوض الصوامت المنطوقة الساقطة.",
        "- فجوات القانون: S00567، S00587، S00589، S00610، S00611، S00613، S00616، S00617، S00618، S00619، S00621، S00622، S00630، S00635، S00636.",
        "- ملاحظات الاتجاه والمصدر: S00568 وS00584 وS00589 وS00625 وS00637؛ حفظت الصور المسماة وفصلت المعاني ولم تدخل مرشحا من خارج المروحة.",
        "- أحواض `nucleus-sweep-*.json` التسعة الحالية v13 قرئت كاملة من القرص؛ both=14546 وsound_only=106794؛ ثبت الحجم وSHA-256 والعدادات لكل ملف.",
        f"- أكبر بطاقة: {max_size} بايت، {max_item.heading}؛ كل البطاقات دون 5KB.",
        "- لم تفعل طبقة البرهان؛ جدد حارس مفردات الإغلاق مشتقيه العالميين بعد الإلحاق؛ لم يقع ship ولم يستعمل git.",
        "", f"<!-- {MARKER}:END -->", "", DONE_LINE,
    ])
    return "\n".join(lines)


def validate_existing(reading_text: str, report_text: str) -> None:
    match = re.search(rf"<!-- {re.escape(MARKER)}:START -->(.*?)<!-- {re.escape(MARKER)}:END -->", reading_text, re.DOTALL)
    if not match:
        raise AssertionError("محضر الجولة موجود وبطاقاتها غائبة")
    headings = re.findall(r"^### (WO-B-R33-SOUND-\d{5}):", match.group(1), re.MULTILINE)
    expected = [f"WO-B-R33-SOUND-{rank:05d}" for rank in SOUND_RANKS]
    if headings != expected:
        raise AssertionError("مقطع الجولة 33 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(DONE_LINE):
        raise AssertionError("سطر DONE33 ليس خاتمة التقرير")


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
        print("ROUND33 ALREADY PRESENT AND VALID")
        print(DONE_LINE)
        return 0

    validate_nucleus_snapshot()
    data = json.loads(SWEEP.read_text(encoding="utf-8"))
    selected, stats = select_rows(data, reading_text)
    prior_pairs = H.read_pairs(reading_text)
    lexicon = json.loads(LEXICON.read_text(encoding="utf-8"))

    R32.EXPECTED_ENTRY_INDEX = EXPECTED_ENTRY_INDEX
    R32.EXPECTED_RAW_LINE = EXPECTED_RAW_LINE
    entries, grouped = R32.select_branch_entries(selected, lexicon)
    raw_entries = R32.load_raw_entries(selected, entries)
    validate_components(grouped)

    R28.EXPECTED_ENTRY_INDEX = EXPECTED_ENTRY_INDEX
    R28.EXPECTED_RAW_LINE = EXPECTED_RAW_LINE
    R28.REVIEWS = REVIEWS
    R28.BLOCKED_BOUNDARIES = {}
    R28.TOOL_GAPS = TOOL_GAPS
    R28.OUT_OF_SCOPE = {}
    R28.EXACT_DECOMPOSITIONS = EXACT_DECOMPOSITIONS
    R28.decomposition_lines = decomposition_lines
    R28.make_card = make_card
    R29.REVIEWS = REVIEWS
    R29.TOOL_GAPS = TOOL_GAPS
    R31.REVIEWS = REVIEWS
    R31.REJECTED_ANALYSES = REJECTED_ANALYSES
    R31.TOOL_GAPS = TOOL_GAPS
    R32.REVIEWS = REVIEWS
    R32.REJECTED_ANALYSES = REJECTED_ANALYSES
    R32.TOOL_GAPS = TOOL_GAPS
    R32.OUT_OF_SCOPE = {}
    R32.EXACT_DECOMPOSITIONS = EXACT_DECOMPOSITIONS
    R32.decomposition_lines = decomposition_lines

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
        "## الجولة الثالثة والثلاثون: متابعة حوض sound_only (2026-08-26)\n\n"
        "- النطاق: 70 عضوا طازجا بعد WO-B-R32-SOUND-00564؛ من الرتبة 565 إلى 640 مع تجاوز 571 و575 و579 و598 و615 و639 لأنها مقروءة؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ طريق المعنى مسمى، والمدار اليدوي حاسم، والأصداء مفصولة عن الآثار المحكمة.\n"
        "- لقطة الأحواض: قرئت ملفات nucleus-sweep-*.json التسعة الحالية v13 من القرص؛ ثبتت بصماتها وعداداتها قبل الانتخاب.\n\n"
        + "\n".join(texts[:35])
        + "\n## الدفعة الثانية: متابعة sound_only بعد الرتبة 603\n\n"
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
    print("ROUND33 READY")
    print("NUCLEUS_V13_FILES", len(NUCLEUS_SNAPSHOT), "SHA256_AND_COUNTS_OK")
    print("NUCLEUS_V13_TOTALS", "BOTH=14546", "SOUND_ONLY=106794")
    print("SKIPPED", ",".join(map(str, stats["skipped"])))
    print("BATCHES", *BATCH_SIZES, "SELECTED", len(selected))
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("EXACT_COMPONENTS", " ".join(f"S{rank:05d}" for rank in sorted(EXACT_DECOMPOSITIONS)))
    print("TRACES", "S00605", "S00606", "S00607")
    print("TOOL_GAPS", len(TOOL_GAPS), "LAW_GAPS", len(LAW_GAPS))
    print("MAX_CARD", max(sizes), selected[sizes.index(max(sizes))].heading)
    if args.preview:
        print("PREVIEW ONLY")
        print(DONE_LINE)
        return 0

    with READING.open("a", encoding="utf-8", newline="") as handle:
        handle.write(reading_append)
    with REPORT.open("a", encoding="utf-8", newline="") as handle:
        handle.write(report_append)
    print("ROUND33 WRITTEN")
    print(DONE_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
