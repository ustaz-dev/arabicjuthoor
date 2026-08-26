# -*- coding: utf-8 -*-
"""المسار B، الجولة 34: متابعة حوض sound_only في دفعتين من 35 بطاقة."""

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

import harvest_persian_round33 as R33  # noqa: E402

R32 = R33.R32
R31 = R33.R31
R30 = R33.R30
R29 = R33.R29
R28 = R33.R28
H = R33.H
P = R33.P
P25 = R33.P25
READING = ROOT / "04-cross-linguistic" / "readings" / "persian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-B.md"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-persian.json"
NUCLEUS_DIR = ROOT / "04-cross-linguistic" / "exploration"
LEXICON = ROOT / "data" / "branch-lexicons" / "persian.json"
RAW_LEXICON = ROOT / "Resources" / "persian" / "kaikki.org-dictionary-Persian.jsonl"
MARKER = "LANE-B-PERSIAN-ROUND34-2026-08-26"
CARD_LIMIT = 5120
SOUND_RANKS = (
    642, 643, 645, 646, 647, 648, 649, 650, 651, 652, 653, 654, 655, 656,
    657, 658, 659, 660, 661, 662, 663, 664, 665, 666, 667, 669, 671, 672,
    673, 674, 675, 676, 677, 678, 679, 680, 682, 683, 684, 685, 686, 687,
    688, 689, 690, 691, 692, 694, 695, 696, 697, 698, 699, 700, 701, 702,
    703, 704, 705, 706, 707, 708, 709, 711, 712, 713, 714, 715, 716, 717,
)
BATCH_SIZES = (35, 35)
DONE_LINE = "LANE-B DONE34 70 WO-B-R34-SOUND-00717"
EXPECTED_SKIPS = (641, 644, 668, 670, 681, 693, 710)

# النسخة الرابعة عشرة المقروءة من القرص. أعيد بناء ملفي الإنجليزية القديمة
# والقوطية، وبقيت عدادات الأحواض الكلية على حالها.
NUCLEUS_SNAPSHOT = {
    "nucleus-sweep-ancient_greek.json": (7976093, "4c2eafc719b56438c68b775988845e2412d980b6d75f2830111f63d8f15423d9", 2330, 16775),
    "nucleus-sweep-english_middle.json": (3417949, "799770fad28e1e45a1dc62de5368513aa7adf1aaf00fe8966e888fbacaa63bf7", 1414, 7991),
    "nucleus-sweep-english_old.json": (1306320, "6b4a839394566e9dc99087022fb07534ce891d6513a2029fa0f75510ad3baec5", 474, 3414),
    "nucleus-sweep-gothic.json": (1449160, "97af20713264091a25165c30c40f3ea7232c61770344b7aca5a6d703a097c069", 340, 3078),
    "nucleus-sweep-latin.json": (18840240, "5ff34ddf45aa660c6cba65d2046e18c42d92fd0cfe4ea93fd853df54b8d000c9", 6598, 39460),
    "nucleus-sweep-old_irish.json": (952787, "7aaa1d45242c3dd011824434105ab36d92db10fe23d7f466f7f2e96d95f88153", 278, 2740),
    "nucleus-sweep-old_norse.json": (1380179, "89b882b5692764f349a52de93c23665324733c498edde6d435e7423f4d99ab4b", 476, 3751),
    "nucleus-sweep-persian.json": (5458517, "555593ff42aa888d8c4095a68acee7eb1c86725df7a7a15b9312a0c999377908", 1448, 13498),
    "nucleus-sweep-welsh.json": (5777180, "740410bd00fb9b720c420b85c283eb3be04893828a72b97f3c48554d1654292b", 1188, 16087),
}

EXPECTED_ENTRY_INDEX = dict(zip(SOUND_RANKS, (
    2989, 3003, 3016, 3018, 3020, 3025, 3030, 3033, 3037, 3041,
    3044, 3070, 3071, 3078, 3083, 3091, 3094, 3097, 3099, 3100,
    3102, 3104, 3114, 3115, 3116, 3126, 3128, 3133, 3140, 3141,
    3143, 3149, 3150, 3151, 3155, 3159, 3175, 3176, 3193, 3207,
    3210, 3211, 3220, 3221, 3223, 3226, 3227, 3233, 3253, 3255,
    3256, 3269, 3270, 3278, 3288, 3289, 3290, 3291, 3292, 3305,
    3311, 3313, 3324, 3333, 3335, 3337, 3340, 3341, 3342, 3359,
)))

EXPECTED_RAW_LINE = dict(zip(SOUND_RANKS, (
    3290, 3304, 3319, 3321, 3323, 3328, 3335, 3339, 3344, 3349,
    3353, 3402, 3403, 3412, 3418, 3430, 3433, 3437, 3439, 3440,
    3442, 3444, 3461, 3463, 3464, 3479, 3481, 3486, 3493, 3495,
    3497, 3503, 3504, 3506, 3510, 3514, 3530, 3531, 3550, 3569,
    3576, 3577, 3588, 3589, 3591, 3595, 3596, 3602, 3623, 3625,
    3626, 3639, 3640, 3649, 3660, 3661, 3662, 3663, 3664, 3678,
    3685, 3687, 3698, 3707, 3709, 3711, 3715, 3717, 3718, 3735,
)))

EXACT_DECOMPOSITIONS = {645, 650, 665, 669, 673, 682, 683, 690, 702}
EXPECTED_COMPONENTS = {
    645: ("پاره", "چه"),
    650: ("خواب", "گاه"),
    665: ("دَسْت", "گاه"),
    669: ("بی", "گُناه"),
    673: ("بازی", "گر"),
    682: ("زاد", "گاه"),
    683: ("پس", "وند"),
    690: ("چر", "ا"),
    702: ("ژرف", "ا"),
}
COMPONENT_READINGS = {
    645: "`پاره`: entries[7306-7307] والخام 8571-8572؛ اختير الاسم piece أو part، ومروحته 40: OPEN-CANDIDATE. `ـچه`: entries[7514] والخام 8808 لاحقة تصغير، ومروحتها 60: MORPHOLOGY-GAP.",
    650: "`خواب`: entries[551-552] والخام 592-593؛ اختير الاسم sleep أو dream، ومروحته 30: OPEN-CANDIDATE. `ـگاه`: entries[7462] والخام 8752 لاحقة مكان أو زمان، ومروحتها 72: MORPHOLOGY-GAP.",
    665: "`دست`: entries[1138-1139] والخام 1210-1211؛ اختير الاسم hand أو arm، ومروحته 27: OPEN-CANDIDATE. `ـگاه`: entries[7462] والخام 8752 لاحقة مكان أو زمان: MORPHOLOGY-GAP.",
    669: "`بیـ`: entries[14756] والخام 17675 سابقة without، ومروحتها 14: MORPHOLOGY-GAP. `گناه`: entries[2927] والخام 3216 لمعاني sin أو crime أو guilt، ومروحتها 40: OPEN-CANDIDATE.",
    673: "`بازی`: entries[1538] والخام 1620 لمعنى game، وهي نفسها مركب داخلي من `باز` و`ـی` فلا يرث المجموع حكمها؛ مروحتها 30: COMPOUND-BOUNDARY. `ـگر`: entries[10504] والخام 12956 لاحقة فاعل، ومروحتها 80: MORPHOLOGY-GAP.",
    682: "`زاد`: entries[5931] والخام 6949 لا يحملان إلا معنى luggage، وهو متجانس لا يثبت مكون birth المقصود: COMPONENT-GAP. `ـگاه`: entries[7462] والخام 8752 لاحقة مكان أو زمان: MORPHOLOGY-GAP.",
    683: "`پس`: entries[4649-4652] والخام 5166-5169؛ اختير الاسم back part أو behind، ومروحته 60: OPEN-CANDIDATE. `ـوند`: entries[14786] والخام 17709 لاحقة pertaining to أو depending on، ومروحتها 6: MORPHOLOGY-GAP.",
    690: "`چر`: entries[6083] لا يحمل إلا why، والجذع الفعلي present stem of `چریدن` حاضر في الخام 7131: FORM-LINK. `ـا`: entries[7537] والخام 8834 لاحقة صفة أو اسم، ومروحتها صفر: MORPHOLOGY-GAP.",
    702: "`ژرف`: entries[2050] والخام 2153 لمعنى deep، ومروحته 12: OPEN-CANDIDATE. `ـا`: entries[7537] والخام 8834 لاحقة صفة أو اسم، ومروحتها صفر: MORPHOLOGY-GAP.",
}

REJECTED_ANALYSES = {
    652: "يسمي الخبر تفكيكا في طبقة Proto-Iranian إلى سوابق وجذر، لا From X + Y نهائيا مباشرا للصورة الحديثة.",
    653: "يسمي الخبر مكونين في الصورة الفارسية الوسطى، لا تفكيكا نهائيا مباشرا للمدخلة الحديثة.",
    658: "يرد الخبر المدخلة إلى صورة أقدم `کویچه` ثم يحلل تلك الصورة إلى `کوی` و`ـچه`؛ لم يحول التحليل التاريخي إلى From نهائي للصورة الحالية.",
    663: "يعرض الخبر تحليلا شعبيا من `سور` و`نای` بعد قرض مجهول؛ لم يحول folk etymology إلى تفكيك نهائي.",
    675: "يسوق الخبر `پروانه` و`ـگی` بلا صيغة From X + Y النهائية المباشرة؛ حفظ الحد ولم يخترع تأهيله.",
    676: "يسمي الخبر By surface analysis مكوني `مغ` و`ـبد` بعد الصورة الوسطى الموروثة، فلا يحول التحليل السطحي إلى From نهائي.",
    679: "يسمي الخبر By surface analysis مكوني `نام` و`ـه` بعد تاريخ موروث مستقل، فلا يحول التحليل السطحي إلى From نهائي.",
    689: "يسمي الخبر By surface analysis `چه` و`رای` بعد اشتقاق تاريخي مستقل، لا From نهائيا مباشرا.",
}
TOOL_GAPS = {
    643: "الصورة `میانجی` منقوطة /miyânji/، لكن الهيكل أسقط /y/ المنطوقة.",
    646: "الصورة `روشن` منقوطة /rawšan/، لكن الهيكل أسقط /w/ المنطوقة في القراءة المختارة.",
    674: "الصورة `دیوانگی` منقوطة /divânegi/، لكن الهيكل أسقط /v/ المنطوقة.",
    675: "الصورة `پروانگی` منقوطة /parvânegi/، لكن الهيكل أسقط /v/ المنطوقة.",
    701: "الصورة `ژاویدن` منقوطة /žâvidan/، لكن الهيكل أسقط /v/ المنطوقة.",
    706: "الصورة `ایوان` منقوطة /aywān/، لكن الهيكل أسقط /y/ و/w/ المنطوقتين.",
    708: "الصورة `خوهر` منقوطة /xvahar/، لكن الهيكل أسقط /v/ المنطوقة.",
    712: "الصورة `پاییدن` منقوطة /pāyīdan/، لكن الهيكل أسقط /y/ المنطوقة.",
}
LAW_GAPS = {
    654, 655, 656, 658, 659, 664, 672, 678, 684, 685,
    689, 694, 698, 699, 703, 704, 705, 709, 711, 717,
}
SOURCE_NOTES = {
    649: "المدخلة لا تحمل إلا إحالة إلى `سفید` ولا تقدم معنى white مستقلا؛ حفظ FORM-LINK ولم يورث حكم الرأس.",
    663: "الأصل المنشور يسمي قرضا من مصدر مجهول محتمل أناضولي، ثم يفصل عنه التحليل الشعبي؛ عملت المصفاة على الخبر لا على التشابه.",
    676: "الخبر يسمي قروضا إيرانية إلى الأرمنية والسريانية، ولا يسمي العربية؛ لم يمد اتجاه النقل إلى لسان غير مذكور.",
    680: "فصلت مدخلة grain المختارة عن متجانس classifier للرسم نفسه، ولم يرث أحدهما معنى الآخر.",
    691: "حقل الاشتقاق فارغ؛ لم يستبدل بقرض إنجليزي مستنتج من الرسم الحديث.",
    692: "الشواهد العربية لـ`كرد` تسمي neck فارسيا معربا، لكن معنى knife في الفرع سلسلة أخرى؛ حفظ اتجاه النقل بلا خلط للمعنى.",
    709: "فصلت gazelle أو deer عن اسم العلم وعن متجانس defect أو imperfection في الرسم نفسه.",
    714: "الشواهد العربية لـ`درز` تسمي seam دخيلا فارسيا، أما المدخلة فتعني long ومن سلف هندوإيراني آخر؛ لم يدمج المتجانسان.",
    715: "المدخلة صورة دارية وكلاسيكية محالة إلى `اسب` horse؛ حفظ FORM-LINK ولم ينشئ أصلا ثانيا للصورة.",
    717: "متجانس اسم الإقليم يذكر العربية `فارس`، أما عضو ethnic Persian المختار فلا يسمي طريق العربية؛ لم يورث الخبر بين المتجانسين.",
}


@dataclass(frozen=True)
class SelectedRow:
    row: H.SweepRow

    @property
    def key(self) -> str:
        return f"S{self.row.rank:05d}"

    @property
    def heading(self) -> str:
        return f"WO-B-R34-SOUND-{self.row.rank:05d}"


Review = R29.Review
R = R29.R

# سجل قراءة يدوي. لا يشتق الحكم من best ولا من وزن المروحة.
REVIEWS = {
    642: R("جد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جد`: العظم والامتداد؛ لا يسمي magic أو wizardry.", "السحر فعل تأثير خفي، ولا يساوي عظم الشيء أو امتداده؛ فصلت المهنة عن الفعل وعن الحظ العربي."),
    643: R("منج", "TOOL-GAP", "جسر المعنى: mediator حاضر، لكن /miyânji/ يحمل /y/ أسقطها الهيكل.", "أوقف الصامت الساقط المقارنة قبل ربط الوساطة بالحجز أو الثبات."),
    645: R("برج", "COMPOUND-BOUNDARY", "جسر المعنى: الخبر يفكك piece أو cloth إلى `پاره` ولاحقة التصغير `ـچه`.", "قُرئ معنى القطعة على `پاره` ووظيفة التصغير على اللاحقة؛ لم تورث الصورة المجموعة حكم مكون."),
    646: R("رشن", "TOOL-GAP", "جسر المعنى: bright أو clear حاضر، لكن /rawšan/ يحمل /w/ أسقطها الهيكل.", "أوقف الصامت الساقط المقارنة قبل تحويل انتشار الدقيق إلى ضوء أو وضوح."),
    647: R("سم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سم`: نوع من الخرق الذي يضم؛ لا يسمي hoof.", "حافر الحيوان يضم طرف القدم لكنه عضو لا حدث خرق، والشواهد العربية في السم وثقب الإبرة."),
    648: R("قبتر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`قبتر`: النتوء مع تجوف وصلابة؛ لا يسمي pigeon أو dove.", "قصر الحمامة أو تجوف جسمها وصف شكلي لا معنى النوع، والشاهدان العربيان في الصغير القصير."),
    649: R("سبد", "OPEN-CANDIDATE", "جسر المعنى: المدخلة تحيل إلى `سفید` بلا نص معنى مستقل، و`سبد` لا يحمل إحالة اللون.", "حفظت الصورة الكلاسيكية FORM-LINK؛ لم تستخرج white من اسم الرأس ولم تورث له حكما."),
    650: R("خبج", "COMPOUND-BOUNDARY", "جسر المعنى: الخبر يفكك dormitory إلى `خواب` sleep و`ـگاه` place.", "مكان النوم نتيجة تركيب المكونين؛ قُرئ كل مكون وحده ولم يقارن المجموع جذرا عربيا."),
    651: R("ردن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ردن`: تراكم مترتب على صد المسترسل؛ لا يسمي defecate أو mess up.", "خروج الفضلة حركة جسدية لا معنى تراكم الرد، والشاهدان العربيان في أصل كم القميص."),
    652: R("برمس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`برمس`: التجرد والخلوص؛ لا يسمي forgotten.", "خلو الذهن من المذكور وصف عارض للنسيان، وفُصل التفكيك الإيراني الأولي عن الصورة الحديثة."),
    653: R("همش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`همش`: تسيب أثناء الشيء؛ لا يسمي always.", "دوام الزمن حكم كمي لا حركة همش أو اختلاط، وفصلت مكونات الفارسية الوسطى التاريخية."),
    654: R("جب", "LAW-GAP", "جسر المعنى: quiet أو silent حاضر، لكن صف چ↔ج غير مسمى.", "السكون قد يوقف الصوت، لكن المروحة لا تمنح طريقا مرخصا من چ قبل اختبار المدار."),
    655: R("جب", "LAW-GAP", "جسر المعنى: أمر silence حاضر، لكن صف چ↔ج غير مسمى.", "فصلت صيغة الأمر الصوتية عن الصفة السابقة، وأوقفتها فجوة القانون نفسها."),
    656: R("شكدن", "LAW-GAP", "جسر المعنى: to drip حاضر، لكن صفي چ↔ش في الأول وک↔ك في الثاني لا يكتملان بطريق مسمى.", "تتابع القطرات قد يوهم النفاذ أو السيلان، لكن رجل الصوت موقوفة قبل المدار."),
    657: R("كر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كر`: التركز تكرارا أو بقاء للنفع؛ لا يسمي blind.", "بقاء العين بلا إبصار حالة للعضو لا حدث تركز، والشواهد العربية في الكر والرجوع."),
    658: R("كج", "LAW-GAP", "جسر المعنى: alley أو lane حاضر، لكن صف چ↔ج غير مسمى.", "رفضت تفكيك الصورة الأقدم `کویچه`، ولم تحول ضيق الزقاق أو امتداده إلى معنى بلا طريق صوت."),
    659: R("اسبذ", "LAW-GAP", "جسر المعنى: cookery أو cooking حاضر، لكن مسار الهيكل `آشپز` إلى المرشح غير مكتمل بصفوف مسماة.", "فعل الطبخ لا يثبت من تداخل الرسم، وحقل الأصل الفارغ لم يعوض بتفكيك حدسي."),
    660: R("سرم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سرم`: منفذ يمتد دقيقا مع ضم؛ لا يسمي cold.", "انقباض الجسم في البرد أثر لاحق لا معنى البرودة، والشواهد العربية في مخرج الثفل."),
    661: R("سخت", "LOANWORD-NON-ARABIC-TO-ARABIC", "جسر المعنى: الصحاح يثبت `السخت: الشديد`، واللسان والتاج يثبتان الصلب ويقولان أصله فارسي.", "اتحد hard أو solid أو severe مع السخت العربي، لكن الشاهدين سميا اتجاه الفارسية إلى العربية؛ أغلق تماس لا إرثا."),
    662: R("سخت", "LOANWORD-NON-ARABIC-TO-ARABIC", "جسر المعنى: exceedingly أو very هي درجة الشدة التي يثبتها الصحاح والتاج لـ`سخت`.", "فصلت الحال عن الصفة، وحفظت مطابقة الشدة مع تصريح المصدرين بالأصل الفارسي؛ أغلق تماس لا إرثا."),
    663: R("سلن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سلن`: انسحاب ممتد برفق؛ لا يسمي zurna.", "امتداد المزمار أو الهواء فيه وصف آلة، والشاهدان العربيان في الرماح؛ عزل القرض المجهول والتحليل الشعبي."),
    664: R("شنج", "LAW-GAP", "جسر المعنى: clutch أو embrace يقارب الانقباض في `شنج`، لكن صفي چ↔ش وگ↔ج غير مكتملين.", "قبض المخالب مرشح معنى مباشر، إلا أن فجوة الصوت تمنع إصدار أثر أو صدى."),
    665: R("دستج", "COMPOUND-BOUNDARY", "جسر المعنى: الخبر يفكك machine إلى `دست` hand و`ـگاه`.", "الآلة معنى للمركب لا لليد وحدها ولا للاحقة؛ قُرئ المكونان ولم يورث أحدهما حكم الآخر."),
    666: R("زيد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زيد`: النمو والزيادة؛ لا يسمي offspring.", "زيادة الأسرة وصف للنسل لا معنى الفرد المولود، والخبر يرده إلى سلسلة الولادة الهندوإيرانية."),
    667: R("شرم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شرم`: الانتشار مع الميم؛ لا يسمي shame.", "انكشاف المرء عند الخزي استعارة غير موثقة، والشواهد العربية في الشق والخليج لا العار."),
    669: R("بجن", "COMPOUND-BOUNDARY", "جسر المعنى: الخبر يفكك innocent إلى السابقة `بیـ` without و`گناه` sin أو guilt.", "انتفاء الذنب حاصل من التركيب؛ لم يقارن innocent وحدة جذرية ولم تورث السابقة حكم الاسم."),
    671: R("كدم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كدم`: التعامل مع قشر شديد اللصوق؛ لا يسمي which.", "الاختيار بين البدائل وظيفة ضميرية لا عض أو قشر، وحفظت المدخلة الوظيفية مستقلة."),
    672: R("او", "LAW-GAP", "جسر المعنى: this حاضر، لكن انتقال ي↔و في هذا الموضع غير مسمى.", "الإشارة وظيفة معجمية قابلة للفحص، إلا أن رجل الصوت لا تكتمل قبل المدار."),
    673: R("بذقر", "COMPOUND-BOUNDARY", "جسر المعنى: الخبر يفكك actor أو acrobat إلى `بازی` game و`ـگر` agent.", "الفاعل معنى للمركب؛ و`بازی` نفسها بناء داخلي، فوقف التوريث عند الحدين."),
    674: R("دنج", "TOOL-GAP", "جسر المعنى: madness أو insanity حاضر، لكن /divânegi/ يحمل /v/ أسقطها الهيكل.", "أوقف الصامت الساقط الحكم قبل ربط الجنون بالاندساس أو الضيق."),
    675: R("برنج", "TOOL-GAP", "جسر المعنى: order أو permission حاضر، لكن /parvânegi/ يحمل /v/ أسقطها الهيكل.", "رفضت التحليل غير المؤهل ثم أوقف الصامت الساقط المقارنة قبل أي مدار للإذن."),
    676: R("مبد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مبد`: محاكم الحروف بلا معنى Zoroastrian priest.", "الموبذ لقب ديني إيراني، وفصلت التحليل السطحي والقروض المسماة إلى الأرمنية والسريانية عن العربية."),
    677: R("بشن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بشن`: الانتشار الظاهر؛ لا يسمي forehead.", "بروز الجبهة هيئة للعضو لا معناه، ولم يكتمل شاهد عربي ثان للمادة المختارة."),
    678: R("درع", "LAW-GAP", "جسر المعنى: lie أو untruth حاضر، لكن صف غ↔ع غير مسمى.", "ستر الحقيقة بالدرع وصف مجازي غير موثق، وفجوة الصوت تسبق اختبار هذا المدار."),
    679: R("نام", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`نام`: النوم؛ لا يسمي letter أو book أو writing.", "اتحاد الرسم لا ينقل معنى الكتابة إلى النوم، ورفضت surface analysis بعد التاريخ الموروث."),
    680: R("دن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دن`: محاكم حرفين بلا معنى grain أو seed.", "كون الحبة في وعاء أو دنوها وصف عارض، وفصلت grain عن متجانس classifier."),
    682: R("زدق", "COMPOUND-BOUNDARY", "جسر المعنى: الخبر يفكك birthplace إلى `زاد` و`ـگاه` place.", "مكون birth المقصود غائب كمدخلة مستقلة صحيحة المعنى؛ حفظ COMPONENT-GAP ولم يخترع من متجانس luggage."),
    683: R("بشند", "COMPOUND-BOUNDARY", "جسر المعنى: الخبر يفكك suffix إلى `پس` back و`ـوند`.", "المصطلح الصرفي نتيجة تركيب موضع الخلف واللاحقة؛ قُرئ كل مكون ولم يقارن المجموع جذرا."),
    684: R("اخر", "LAW-GAP", "جسر المعنى: manger أو stall حاضر، لكن آ↔ا في الأول غير مسمى في هذا الرصف.", "خبر الأصل يرده إلى موضع الأكل الإيراني ويذكر قروضا مجاورة، لكن المرشح العربي لا يحمل معنى المعلف."),
    685: R("حرقص", "LAW-GAP", "جسر المعنى: ever أو never حاضر، لكن مسار `هرگز` إلى `حرقص` غير مكتمل بصفوف مسماة.", "الدوام والنفي الزمني لا يستخرجان من معنى الدويبة العربية، وفجوة الصوت مانعة أولا."),
    686: R("يزد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`يزد`: محاكم الحروف بلا معنى eleven.", "العدد وحدة معجمية لا معنى اسم إقليم يزد، ولم يكتمل شاهد عربي كلاسيكي ثان."),
    687: R("كم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كم`: تغطية الشيء بغطاء زائد؛ لا يسمي few أو scarce.", "كم العربية تسأل عن العدد وقد تخبر بالكثرة، فلا تساوي القلة الفارسية ولا يثبت الحدث هذا الانعكاس."),
    688: R("ستن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ستن`: التغطية والإخفاء؛ لا يسمي column أو pillar.", "قيام العمود وستره ما خلفه وظيفتان عارضتان، والشواهد العربية في أصول الشجر البالية."),
    689: R("جر", "LAW-GAP", "جسر المعنى: why حاضر، لكن صف چ↔ج غير مسمى.", "رفضت التحليل السطحي `چه` و`رای`، ولم تحول السؤال عن السبب إلى امتداد أو جر."),
    690: R("جر", "COMPOUND-BOUNDARY", "جسر المعنى: الخبر يفكك pasturing إلى جذع `چر` من to graze ولاحقة الاسم `ـا`.", "الرعي معنى الجذع، والاسمية وظيفة اللاحقة؛ لم يقارن المجموع وحدة جذرية."),
    691: R("لج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`لج`: التراكم والكثافة؛ لا يسمي sports league.", "اجتماع الفرق داخل رابطة وصف تنظيمي لا معنى league، وحقل الأصل الفارغ لم يعوض بقرض مفترض."),
    692: R("كرد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كرد`: التركز المتكرر؛ لا يسمي knife.", "قطع العنق بالسكين فعل استعمال لا معنى الآلة، وفصلت neck الفارسي المعرب في العربية عن knife الموروثة."),
    694: R("وز", "LAW-GAP", "جسر المعنى: special أو pure أو net حاضر، لكن صف ژ↔ز غير مسمى.", "الخلوص قد يقارب pure، إلا أن فجوة القانون تمنع إصدار حكم موجب."),
    695: R("نج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`نج`: النفاذ بغلظ أو قوة؛ لا يسمي suddenly أو accidental.", "الجولة عند الفزعة قد تقع بغتة لكنها شاهد سياق لا معنى الظرف، فبقي المرشح مفتوحا."),
    696: R("زود", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زود`: الزاد المعد للسفر؛ لا يسمي early.", "الاستعداد المبكر للرحلة وصف استعمال للزاد لا معنى التبكير، وفصلت الصفة عن الظرف التالي."),
    697: R("زود", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زود`: الزاد المعد للسفر؛ لا يسمي early أو quickly.", "سرعة التزود فعل على المؤونة لا معناها، وفصلت الظرف عن الصفة السابقة بحق النقض."),
    698: R("اشن", "LAW-GAP", "جسر المعنى: acquainted أو familiar حاضر، لكن آ↔ا في الأول غير مسمى في هذا الرصف.", "المعرفة والقرب مثبتان في أصل الفرع، لكن المرشح العربي لا يحمل معناهما وفجوة الصوت قائمة."),
    699: R("اشن", "LAW-GAP", "جسر المعنى: acquaintance أو friend حاضر، لكن آ↔ا في الأول غير مسمى في هذا الرصف.", "فصلت الاسم عن الصفة السابقة، وأوقفت فجوة القانون الحكم قبل مدار الصحبة."),
    700: R("ارم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ارم`: محاكم الحروف بلا معنى arm.", "امتداد الذراع عن الجسد هيئة عامة، والشاهد المعجمي الوحيد في الاستئصال أو الأكل لا العضو."),
    701: R("زذن", "TOOL-GAP", "جسر المعنى: ruminate أو howl حاضر، لكن /žâvidan/ يحمل /v/ أسقطها الهيكل.", "أوقف الصامت الساقط المقارنة قبل فصل المضغ المتكرر عن العواء."),
    702: R("جرف", "COMPOUND-BOUNDARY", "جسر المعنى: الخبر يفكك depth إلى `ژرف` deep و`ـا` الاسمية.", "العمق معنى الصفة بعد الاسمية، فقرأ المكونان ولم تورث الصورة المجموعة حكم `ژرف`."),
    703: R("زقفل", "LAW-GAP", "جسر المعنى: patient أو meek حاضر، لكن صف ژ↔ز وک↔ق غير مكتملين بطريق مسمى.", "الشواهد العربية في السرعة تناقض الصبر، وفجوة الصوت تمنع أي حكم موجب."),
    704: R("زقفل", "LAW-GAP", "جسر المعنى: patience حاضر، لكن صف ژ↔ز وک↔ق غير مكتملين بطريق مسمى.", "فصلت اسم المعنى عن الصفة السابقة، وبقيت الشواهد العربية في السرعة لا الصبر."),
    705: R("زم", "LAW-GAP", "جسر المعنى: midwife حاضر، لكن صف ژ↔ز غير مسمى.", "ضم المولود أو إمساكه فعل للمهنة لا معناها، وفجوة القانون تسبق المدار."),
    706: R("ان", "TOOL-GAP", "جسر المعنى: palace أو iwan أو portico حاضر، لكن /aywān/ يحمل /y/ و/w/ أسقطهما الهيكل.", "أوقف الصامتان الساقطان المقارنة قبل أي مدار للمكان أو البناء."),
    707: R("دحط", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دحط`: الضغط القوي؛ لا يسمي daughter أو virgin.", "الولادة أو الحماية الاجتماعية وصفان خارجان عن معنى البنت، ولم يكتمل شاهد عربي ثان."),
    708: R("حهل", "TOOL-GAP", "جسر المعنى: sister حاضر، لكن /xvahar/ يحمل /v/ أسقطها الهيكل.", "أوقف الصامت الساقط المقارنة قبل تحويل القرابة إلى أي مدار حروفي."),
    709: R("اه", "LAW-GAP", "جسر المعنى: gazelle أو deer حاضر، لكن آ↔ا في الأول غير مسمى في هذا الرصف.", "سرعة الغزال مذكورة في أصل هندوإيراني، لكنها لا تساوي أنين `أه` وفصلت المتجانسات."),
    711: R("ارز", "LAW-GAP", "جسر المعنى: desire أو wish حاضر، لكن آ↔ا في الأول غير مسمى في هذا الرصف.", "امتداد الرغبة وصف غير معجمي، والشاهد العربي في شجر الأرز لا التمني."),
    712: R("بدن", "TOOL-GAP", "جسر المعنى: protect أو stand firm حاضر، لكن /pāyīdan/ يحمل /y/ أسقطها الهيكل.", "أوقف الصامت الساقط المقارنة قبل ربط الثبات بكتلة البدن."),
    713: R("بشن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بشن`: الانتشار الظاهر؛ لا يسمي heel ولا ثمرة محفوظة للبذر.", "فصلت معنى العضو عن معنى الثمرة، ولم يكتمل شاهد عربي ثان للمادة."),
    714: R("درز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`درز`: الجريان باسترسال أو الامتداد بتوال؛ يلامس long ولا يكفي وحده.", "الشواهد العربية تسمي seam دخيلا فارسيا من سلسلة معنى أخرى؛ فصل المتجانس منع تحويل الحدث إلى أثر."),
    715: R("اسب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`اسب`: محاكم الحروف بلا معنى horse.", "الصورة تحيل إلى رأس horse نفسه، لكن الشاهد العربي المتاح في شعر العانة لا الحيوان."),
    716: R("هشت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`هشت`: فقد التماسك مع التاء؛ لا يسمي eight.", "العدد وحدة معجمية، والشاهد العربي الوحيد في تحريش الكلب لا العد."),
    717: R("فرس", "LAW-GAP", "جسر المعنى: ethnic Persian يقابل `الفرس` العربية، لكن انتقال پ↔ف غير مسمى مباشرة في الشبكة.", "المعنى واعد، إلا أن متجانس الإقليم وحده يذكر العربية، وفجوة الصوت تمنع إصدار تماس أو أثر."),
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
            raise AssertionError(f"تغير عداد نسخة v14 في {name}")
        if len(data.get("both") or []) != expected_both or len(data.get("sound_only") or []) != expected_sound:
            raise AssertionError(f"تغير طول قوائم نسخة v14 في {name}")
        total_both += expected_both
        total_sound += expected_sound
    if total_both != 14546 or total_sound != 106794:
        raise AssertionError("تغير مجموع أحواض v14")


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
            if row.rank > 640 and len(fresh) < 70:
                internal_skips.append(row.rank)
            continue
        seen.add(key)
        if row.rank <= 640:
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
        "پاره": {7306, 7307}, "ـچه": {7514}, "خواب": {551, 552},
        "ـگاه": {7462}, "دست": {1138, 1139}, "بیـ": {14756},
        "گناه": {2927}, "بازی": {1538}, "ـگر": {10504}, "زاد": {5931},
        "پس": {4649, 4650, 4651, 4652}, "ـوند": {14786}, "چر": {6083},
        "ـا": {7536, 7537, 7538}, "ژرف": {2050},
    }
    fan_counts = {
        "پاره": 40, "ـچه": 60, "خواب": 30, "ـگاه": 72, "دست": 27,
        "بیـ": 14, "گناه": 40, "بازی": 30, "ـگر": 80, "زاد": 90,
        "پس": 60, "ـوند": 6, "چر": 60, "ـا": 0, "ژرف": 12,
    }
    for word, expected in expected_indices.items():
        actual = {index for index, _entry in grouped.get(word, [])}
        if actual != expected:
            raise AssertionError(f"تغير جرد مكون {word}: {sorted(actual)}")
        fan = tuple(H.FAN.rank(word, H.FAN.fan(word, "persian"), "persian"))
        if len(fan) != fan_counts[word]:
            raise AssertionError(f"تغيرت مروحة المكون {word}: {len(fan)}")
    expected_raw = {
        "پاره": {8571, 8572}, "ـچه": {8808}, "خواب": {592, 593},
        "ـگاه": {8752}, "دست": {1210, 1211}, "بیـ": {17675},
        "گناه": {3216}, "بازی": {1620}, "ـگر": {12956}, "زاد": {6949},
        "پس": {5166, 5167, 5168, 5169}, "ـوند": {17709},
        "چر": {7130, 7131}, "ـا": {8833, 8834, 8835}, "ژرف": {2153},
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
    if review.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC":
        return "اكتملت الصورة والمعنى والشواهد، لكنها سمت اتجاه الدخول من الفارسية إلى العربية؛ أغلق تماس لا إرثا."
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
    decomposition = P25.direct_from_plus(raw["etymology"])
    if not decomposition:
        raise AssertionError(f"غاب تفكيك From X + Y للرتبة {rank}")
    joined = H.clean(" + ".join(decomposition))
    for component in EXPECTED_COMPONENTS[rank]:
        if H.clean(component) not in joined:
            raise AssertionError(f"غاب مكون {component} من الرتبة {rank}: {decomposition}")
    return [
        f"- تفكيك Kaikki الحصري المباشر من السطر الخام {raw['line']}: «{H.clip(raw['etymology'], 420)}».",
        f"- قراءة المكونات المستقلة: {COMPONENT_READINGS[rank]}",
        "- الخطوة صفر: قبل التفكيك النهائي المباشر لم تقارن الصورة وحدة جذرية؛ قُرئ كل مكون مسمى وحده.",
    ]


BASE_MAKE_CARD = R32.make_card


def make_card(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit) -> str:
    card = BASE_MAKE_CARD(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit)
    card = card.replace("الجولة 32،", "الجولة 34،")
    rank = item.row.rank
    if rank in SOURCE_NOTES and "ملاحظة المصدر الخاصة" not in card:
        marker = "- عطب الهيكل:" if rank in TOOL_GAPS else "- الخطوة صفر:"
        card = card.replace(
            marker,
            f"- ملاحظة المصدر الخاصة: {SOURCE_NOTES[rank]}\n{marker}",
            1,
        )
    if rank in {661, 662}:
        lines = card.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("  - الشاهد 1،"):
                lines[index] = "  - الشاهد 1، تاج اللغة وصحاح العربية للجوهري: «السخت: الشديد؛ وهو معروف في كلام العرب، وهم ربما استعملوا بعض كلام العجم.»"
            elif line.startswith("  - الشاهد 2،"):
                lines[index] = "  - الشاهد 2، تاج العروس لمرتضى الزبيدي: «السخت: الشديد؛ وشيء سخت: صلب دقيق، وأصله فارسي.»"
            elif line.startswith("- المصفاة:"):
                lines[index] = "- المصفاة: الشاهدان العربيان يسمّيان الشدة نفسها، ويسمي التاج الأصل الفارسي؛ يعمل LOANWORD-NON-ARABIC-TO-ARABIC نتيجة تماس إيجابية محسوبة."
        card = "\n".join(lines) + "\n"
    return card


def validate_decisions(selected, raw_entries, decisions, ranked_by_rank, sense_map) -> None:
    if set(REVIEWS) != set(SOUND_RANKS):
        raise AssertionError("جدول المدار اليدوي لا يغطي الرتب السبعين")
    parsed = {item.row.rank for item in selected if P25.direct_from_plus(raw_entries[item.row.rank]["etymology"])}
    if parsed != EXACT_DECOMPOSITIONS:
        raise AssertionError(f"تغيرت أسطر From X + Y المباشرة: {sorted(parsed)}")
    expected_verdicts = {
        "COMPOUND-BOUNDARY": 9,
        "LAW-GAP": 20,
        "LOANWORD-NON-ARABIC-TO-ARABIC": 2,
        "OPEN-CANDIDATE": 31,
        "TOOL-GAP": 8,
    }
    if Counter(review.verdict for review in REVIEWS.values()) != Counter(expected_verdicts):
        raise AssertionError(f"تغير توزيع الأحكام اليدوي: {Counter(review.verdict for review in REVIEWS.values())}")
    for item, decision in zip(selected, decisions):
        row = item.row
        candidates = {candidate for candidate, _score in ranked_by_rank[row.rank]}
        if decision.candidate not in candidates or decision.candidate not in row.candidates_found:
            raise AssertionError(f"مرشح الرتبة {row.rank} خارج المروحة الحية أو أعضاء الحوض")
        complete = H.route_complete(row, decision.candidate)
        _count, coverage, _witnesses = P.classical_witnesses(decision.candidate, sense_map, 90)
        if decision.verdict == "LAW-GAP" and complete:
            raise AssertionError(f"LAW-GAP بلا صف مفقود في الرتبة {row.rank}")
        if decision.verdict in {"OPEN-CANDIDATE", "LOANWORD-NON-ARABIC-TO-ARABIC"} and not complete:
            raise AssertionError(f"حكم بمسار ناقص في الرتبة {row.rank}: {decision.verdict}")
        if decision.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC":
            if coverage < 2 or H.event_line(decision.candidate).startswith("لا حدث"):
                raise AssertionError(f"حكم تماس بلا حدث وشاهدين في الرتبة {row.rank}")
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
    headings = re.findall(r"^### (WO-B-R34-SOUND-\d{5}):", joined, re.MULTILINE)
    if headings != [item.heading for item in selected]:
        raise AssertionError("معرفات الجولة 34 لا تطابق النافذة")
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
    previous = 640
    for number, batch in enumerate(batches, 1):
        lo = 0 if number == 1 else 35
        hi = lo + len(batch)
        counts = Counter(decision.verdict for decision in decisions[lo:hi])
        distribution = "؛ ".join(f"{key}={counts[key]}" for key in sorted(counts))
        batch_skips = [rank for rank in stats["skipped"] if previous < rank <= batch[-1].row.rank]
        skipped = ", ".join(map(str, batch_skips)) or "0"
        lines.extend([
            f"## الجولة الرابعة والثلاثون، دفعة sound_only رقم {number}", "",
            f"- الوقت: {now}، Africa/Cairo.",
            f"- رشح وكتب: {len(batch)}؛ المواضع المقروءة المتجاوزة داخل المدى: {skipped}.",
            f"- المواضع: من {batch[0].heading} إلى {batch[-1].heading}.",
            f"- توزيع الأحكام: {distribution}.",
            "- طريق المعنى: سمي من جسر معنى صريح أو من نص الحدث المجمد في كل بطاقة.",
            "- المدار: كتب يدويا لكل عضو، وفصلت الأصداء اللينة عن الآثار المحكمة.",
            "- المروحة: ولدت حية كاملة ورتبت بالأوزان، ومسحت مواد جميع مرشحيها بلا قص للحقل المصدر.",
            "- المتجانسات: قرئت كل مداخل الرسم، وسجل العدد ورقم المدخلة المختارة في كل بطاقة.",
            "- المركب: قبل From X + Y النهائي المباشر حصرا؛ لم يخترع مكون ولم يؤهل تحليلا سطحيا أو شعبيا.",
            "- التحقق البنيوي: المعرفات فريدة؛ لا بطاقة فوق 5KB؛ لا شرطة طويلة؛ الأرقام غربية والنص NFC.",
            f"- آخر موضع في الدفعة: {batch[-1].heading}، `{batch[-1].row.branch}`.", "",
        ])
        previous = batch[-1].row.rank
    total = Counter(decision.verdict for decision in decisions)
    distribution = "؛ ".join(f"{key}={total[key]}" for key in sorted(total))
    max_size = max(sizes)
    max_item = selected[sizes.index(max_size)]
    transmissions = [item.heading for item, decision in zip(selected, decisions) if decision.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC"]
    lines.extend([
        "## حصيلة الجولة الرابعة والثلاثين", "",
        f"- حمل `persian.md` مرة واحدة؛ أزواج WO-B المقروءة={stats['pair_count']}؛ المتجاوز داخل النافذة={', '.join(map(str, stats['skipped']))}.",
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- نطاق الصوت الجديد: الرتب 642-717 بعد WO-B-R33-SOUND-00640، مع تجاوز الأزواج السبعة المقروءة فقط.",
        "- لم يصدر أثر موروث محكم جديد؛ بقيت الأصداء الوصفية مرشحات مفتوحة أو فجوات مسماة.",
        f"- اتجاه الدخول إلى العربية المسمى بالشاهدين: {', '.join(transmissions)}.",
        "- التفكيك المباشر المؤهل: S00645، S00650، S00665، S00669، S00673، S00682، S00683، S00690، S00702؛ قرئت المكونات المستقلة كلها.",
        "- التحليلات غير المؤهلة: S00652 وS00653 تاريخيان، S00658 لصورة أقدم، S00663 شعبي، S00675 بلا From نهائي، S00676 وS00679 وS00689 سطحية؛ لم تحول إلى تفكيك نهائي.",
        "- أعطاب الأداة: S00643، S00646، S00674، S00675، S00701، S00706، S00708، S00712؛ لم تعوض الصوامت المنطوقة الساقطة.",
        "- فجوات القانون: S00654، S00655، S00656، S00658، S00659، S00664، S00672، S00678، S00684، S00685، S00689، S00694، S00698، S00699، S00703، S00704، S00705، S00709، S00711، S00717.",
        "- ملاحظات المصدر والمتجانسات: S00649، S00663، S00676، S00680، S00691، S00692، S00709، S00714، S00715، S00717؛ حفظت الصور المسماة وفصلت المعاني والاتجاهات.",
        "- أحواض `nucleus-sweep-*.json` التسعة الحالية v14 قرئت كاملة من القرص؛ both=14546 وsound_only=106794؛ ثبت الحجم وSHA-256 والعدادات لكل ملف.",
        f"- أكبر بطاقة: {max_size} بايت، {max_item.heading}؛ كل البطاقات دون 5KB.",
        "- لم تفعل طبقة البرهان؛ مر حارس نقاء الشحنة وختم CLEAN؛ لم يقع ship ولم يستعمل git.",
        "", f"<!-- {MARKER}:END -->", "", DONE_LINE,
    ])
    return "\n".join(lines)


def validate_existing(reading_text: str, report_text: str) -> None:
    match = re.search(rf"<!-- {re.escape(MARKER)}:START -->(.*?)<!-- {re.escape(MARKER)}:END -->", reading_text, re.DOTALL)
    if not match:
        raise AssertionError("محضر الجولة موجود وبطاقاتها غائبة")
    headings = re.findall(r"^### (WO-B-R34-SOUND-\d{5}):", match.group(1), re.MULTILINE)
    expected = [f"WO-B-R34-SOUND-{rank:05d}" for rank in SOUND_RANKS]
    if headings != expected:
        raise AssertionError("مقطع الجولة 34 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(DONE_LINE):
        raise AssertionError("سطر DONE34 ليس خاتمة التقرير")


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
        print("ROUND34 ALREADY PRESENT AND VALID")
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
        "## الجولة الرابعة والثلاثون: متابعة حوض sound_only (2026-08-26)\n\n"
        "- النطاق: 70 عضوا طازجا بعد WO-B-R33-SOUND-00640؛ من الرتبة 642 إلى 717 مع تجاوز 641 و644 و668 و670 و681 و693 و710 لأنها مقروءة؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ طريق المعنى مسمى، والمدار اليدوي حاسم، والأصداء مفصولة عن الآثار المحكمة.\n"
        "- لقطة الأحواض: قرئت ملفات nucleus-sweep-*.json التسعة الحالية v14 من القرص؛ ثبتت بصماتها وعداداتها قبل الانتخاب.\n\n"
        + "\n".join(texts[:35])
        + "\n## الدفعة الثانية: متابعة sound_only بعد الرتبة 679\n\n"
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
    print("ROUND34 READY")
    print("NUCLEUS_V14_FILES", len(NUCLEUS_SNAPSHOT), "SHA256_AND_COUNTS_OK")
    print("NUCLEUS_V14_TOTALS", "BOTH=14546", "SOUND_ONLY=106794")
    print("SKIPPED", ",".join(map(str, stats["skipped"])))
    print("BATCHES", *BATCH_SIZES, "SELECTED", len(selected))
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("EXACT_COMPONENTS", " ".join(f"S{rank:05d}" for rank in sorted(EXACT_DECOMPOSITIONS)))
    print("TRANSMISSIONS", "S00661", "S00662")
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
    print("ROUND34 WRITTEN")
    print(DONE_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
