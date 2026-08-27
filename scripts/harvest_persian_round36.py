# -*- coding: utf-8 -*-
"""المسار B، الجولة 36: متابعة حوض sound_only في دفعتين من 35 بطاقة."""

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

import harvest_persian_round35 as R35  # noqa: E402

R34 = R35.R34
R32 = R35.R32
R31 = R35.R31
R29 = R35.R29
R28 = R35.R28
H = R35.H
P = R35.P
P25 = R35.P25
READING = R35.READING
REPORT = R35.REPORT
SWEEP = R35.SWEEP
NUCLEUS_DIR = R35.NUCLEUS_DIR
LEXICON = R35.LEXICON
RAW_LEXICON = R35.RAW_LEXICON
MARKER = "LANE-B-PERSIAN-ROUND36-2026-08-27"
CARD_LIMIT = 5120
SOUND_RANKS = (
    790, 791, 792, 793, 794, 795, 796, 797, 798, 799, 800, 801, 802,
    803, 804, 805, 806, 807, 809, 810, 811, 813, 815, 816, 817, 818,
    819, 820, 821, 822, 823, 824, 825, 826, 827, 828, 829, 830, 831,
    833, 834, 835, 836, 837, 838, 839, 840, 841, 842, 843, 844, 845,
    848, 849, 850, 851, 852, 853, 854, 855, 856, 857, 858, 859, 861,
    862, 863, 864, 865, 866,
)
BATCH_SIZES = (35, 35)
DONE_LINE = "LANE-B DONE36 70 WO-B-R36-SOUND-00866"
EXPECTED_SKIPS = (808, 812, 814, 832, 846, 847, 860)

# النسخة السادسة عشرة المقروءة من القرص.
NUCLEUS_SNAPSHOT = {
    "nucleus-sweep-ancient_greek.json": (7983192, "c901c6fed37c93e88d51649138a46b1cbbb6897bfb1303c7c90a24f3098f37b5", 2329, 16776),
    "nucleus-sweep-english_middle.json": (3415749, "2021380b896c6d046b8334adeb7064d8f36ffb9a8e17213e254cfbbedcada5c4", 1414, 7991),
    "nucleus-sweep-english_old.json": (1294040, "c3b57ccf376f9e71f09adff122f5bbbe3590644ed51dfed8f691f3f3ecff7e0b", 474, 3414),
    "nucleus-sweep-gothic.json": (1449007, "2acbe506a035ccddbbf6738c82b43c00ed89149329de0c4b9f73f7dbe0d301f4", 338, 3080),
    "nucleus-sweep-latin.json": (18838317, "96a83a11cced3a313843d8250ce9bf6d82934c4f37cbfb35e938b57e99dc1ca5", 6591, 39467),
    "nucleus-sweep-old_irish.json": (952787, "7aaa1d45242c3dd011824434105ab36d92db10fe23d7f466f7f2e96d95f88153", 278, 2740),
    "nucleus-sweep-old_norse.json": (1381006, "9ecb7bdeef6a54820847126f4508c6bd97e36788a0384b90daa01ff3997faa56", 476, 3751),
    "nucleus-sweep-persian.json": (5462749, "00fe23b5389b8589dfbbfaa266c7226bd4e3ce8c75568e2dcf8cd79e0405d87c", 1448, 13498),
    "nucleus-sweep-welsh.json": (5776914, "1a8a1bc3659854c954955effd359303b8b18d3cd4001331c6d6e6979e309aabb", 1187, 16088),
}

EXPECTED_ENTRY_INDEX = dict(zip(SOUND_RANKS, (
    3722, 3726, 3730, 3733, 3737, 3748, 3757, 3772, 3774, 3776, 3777,
    3784, 3785, 3787, 3790, 3796, 3803, 3804, 3822, 3824, 3832, 3835,
    3840, 3845, 3852, 3860, 3869, 3881, 3882, 3884, 3885, 3886, 3909,
    3913, 3926, 3927, 3928, 3931, 3937, 3984, 3985, 3990, 4016, 4038,
    4041, 4063, 4077, 4078, 4113, 4114, 4123, 4124, 4127, 4128, 4148,
    4155, 4161, 4165, 4184, 4186, 4187, 4188, 4189, 4190, 4206, 4207,
    4212, 4213, 4214, 4217,
)))
EXPECTED_RAW_LINE = dict(zip(SOUND_RANKS, (
    4158, 4163, 4168, 4172, 4176, 4189, 4199, 4215, 4217, 4219, 4220,
    4227, 4229, 4231, 4236, 4246, 4253, 4254, 4274, 4276, 4284, 4287,
    4292, 4297, 4305, 4313, 4322, 4336, 4337, 4339, 4340, 4341, 4368,
    4373, 4386, 4387, 4388, 4391, 4397, 4450, 4451, 4458, 4485, 4512,
    4515, 4540, 4554, 4555, 4591, 4592, 4602, 4603, 4606, 4607, 4631,
    4638, 4644, 4648, 4669, 4672, 4673, 4674, 4675, 4676, 4694, 4695,
    4700, 4701, 4702, 4705,
)))

PARSER_FROM_PLUS = {792, 799, 800, 804, 806, 807, 813, 816, 819, 826}
EXACT_DECOMPOSITIONS = PARSER_FROM_PLUS | {815}
EXPECTED_COMPONENTS = {
    792: ("خسته", "ـگی"),
    799: ("پیچ", "ـک"),
    800: ("رنگ", "ـین"),
    804: ("ویژه", "ـگی"),
    806: ("بیـ", "رنگ"),
    807: ("سپید", "ـه"),
    813: ("راست", "ـگو"),
    815: ("ماهی", "ـچه"),
    816: ("پیش", "ـی"),
    819: ("پیاز", "ـچه"),
    826: ("نِژاد", "ـی"),
}
COMPONENT_READINGS = {
    792: "`خسته`: entry[3993] والخام 4461 لمعنى tired أو weary، ومروحتها 27: OPEN-CANDIDATE. `ـگی`: غائبة من branch-lexicons وحاضرة في الخام 17716 صورة لاحقة `ـی` بعد الهاء القصيرة، ومروحتها 56: MORPHOLOGY-GAP.",
    799: "`پیچ`: entry[3772] والخام 4215 لمعاني screw وcurve وtwist، ومروحتها 60: OPEN-CANDIDATE. `ـک`: entry[7513] والخام 8807 لاحقة تصغير أو تعريف، ومروحتها صفر: MORPHOLOGY-GAP.",
    800: "`رنگ`: entry[138] والخام 143 لمعنى colour، ومروحتها 8: OPEN-CANDIDATE. `ـین`: اختيرت entry[10309] والخام 12681 لاحقة صفة المادة أو النوع، ومروحتها 16: MORPHOLOGY-GAP.",
    804: "`ویژه`: entry[3233] والخام 3602 لمعاني special وpure وnet، ومروحتها 57: OPEN-CANDIDATE. `ـگی`: الخام 17716 لاحقة مجردة غائبة من branch-lexicons، ومروحتها 56: MORPHOLOGY-GAP.",
    806: "`بیـ`: entry[14756] والخام 17675 سابقة without، ومروحتها 14: MORPHOLOGY-GAP. `رنگ`: entry[138] والخام 143 لمعنى colour، ومروحتها 8: OPEN-CANDIDATE.",
    807: "`سپید`: entry[3030] والخام 3335 الصورة الكلاسيكية المبكرة لـ`سفید`، ومروحتها 18: FORM-LINK. `ـه`: اختيرت entry[7113] والخام 8351 لاحقة اشتقاق اسم ذي معنى متصل، ومروحتها صفر: MORPHOLOGY-GAP.",
    813: "`راست`: اختيرت entry[1393] والخام 1474 لمعنى truth بعد قراءة مدخلتي الرسم، ومروحتها 18: OPEN-CANDIDATE. `ـگو`: لا مدخلة مستقلة؛ ثبت `گو` في entries[5574-5577] والخام 6551-6557 جذعا مضارعا، ومروحته 72: FORM-LINK.",
    815: "`ماهی`: اختيرت entry[757] والخام 804 لمعنى fish بعد فصل الصفة القمرية، ومروحتها 20: OPEN-CANDIDATE. `ـچه`: entry[7514] والخام 8808 لاحقة تصغير، ومروحتها 60: MORPHOLOGY-GAP.",
    816: "`پیش`: entries[4609-4611] والخام 5126-5128 لمعاني before وfront، ومروحتها 60: OPEN-CANDIDATE. `ـی`: اختيرت entry[6330] والخام 7422 لاحقة الاسم المجرد، ومروحتها صفر: MORPHOLOGY-GAP.",
    819: "`پیاز`: entry[1088] والخام 1158 لمعنى onion أو bulb، ومروحتها 60، لكن نطقها /piyāz/ يحمل /y/ أسقطها الهيكل: TOOL-GAP. `ـچه`: entry[7514] والخام 8808 لاحقة تصغير، ومروحتها 60: MORPHOLOGY-GAP.",
    826: "`نژاد`: entry[2705] والخام 2979 لمعنى lineage أو race، ومروحتها 9: OPEN-CANDIDATE. `ـی`: اختيرت entry[6329] والخام 7421 لاحقة الصفة، ومروحتها صفر: MORPHOLOGY-GAP.",
}

REJECTED_ANALYSES = {
    790: "يأتي بهر + ـه تحت By surface analysis بعد خبر الوراثة الوسطى، لا تفكيكا نهائيا حصريا.",
    793: "يسمي الخبر مكونين في طبقة Proto-Iranian، لا مكونين نهائيين مباشرين للصورة الحديثة.",
    801: "التفكيك إلى `سی` و`مرغ` موسوم folk etymology بعد الصورة الوسطى الموروثة، فلم يؤهل.",
    811: "التحليل إلى اسم الضفة ولاحقة صفة واقع في الطبقة الفارسية الوسطى التاريخية، لا From نهائيا حديثا.",
    833: "خبر cow مع suffix مصوغ بلفظ Apparently ولا يسمي لاحقة بعينها، فلم يخترع مكون.",
    853: "وصف past participle واقع تحت By surface analysis بعد سلسلة الوراثة، فلم يحول إلى تفكيك نهائي.",
}
TOOL_GAPS = {
    791: "الصورة `بیابان` منقوطة /biyābān/، لكن الهيكل أسقط /y/ المنطوقة.",
    793: "الصورة `میان` منقوطة /miyān/، لكن الهيكل أسقط /y/ المنطوقة.",
    819: "المكون `پیاز` منقوط /piyāz/، لكن هيكله أسقط /y/ المنطوقة.",
    833: "الصورة `گون` منقوطة /gavan/، لكن الهيكل أسقط /v/ المنطوقة.",
    839: "الصورة `پگاه` منقوطة /pagāh/، لكن الهيكل أسقط /h/ النهائية المنطوقة.",
    840: "الصورة `فروهر` المختارة منقوطة /farvahar/، لكن الهيكل أسقط /v/ المنطوقة.",
}
LAW_GAPS = {797, 810, 817, 821, 825, 829, 842, 843, 853, 866}
OUT_OF_SCOPE = {
    801: "اسم طائر أسطوري بعينه في حقل name، لا معنى معجميا عاما.",
    838: "اسم برج Aquarius في حقل name، لا معنى معجميا عاما رغم خبر المصدر السامي.",
    849: "اسم نهر الغانج في حقل name، لا معنى معجميا عاما.",
}
SOURCE_NOTES = {
    796: "خبر الأصل يرجح نشأة الاستعمال في المحيط الفارسي الهندي، ويعرض `بیم` أو أصلا هنديا آريا بديلين؛ حفظ الاحتمالان.",
    798: "الخبر يسمي الأرمنية مقترضة من الإيرانية ولا يسمي العربية؛ لم يمد اتجاه النقل.",
    801: "فصلت الصورة الوسطى الموروثة عن التأثيل الشعبي thirty + bird.",
    818: "تعليل مرور الأغاني في الهواء احتمال تأثيلي لا جسر معنى جذريا معتمدا.",
    823: "الخبر يسمي الآرامية والعبرية والسريانية مقترضات إيرانية لمعنى السر، ولا يسمي العربية.",
    828: "ثبت مسار فارسي أوسط من Pali وثبت اللفظ في العربية، لكن المصدر لا يسمي اتجاه دخوله إلى العربية.",
    834: "خبر الأصل يسمي قرضا تركيا؛ لم يحوله تقارب gate مع تجوف `قب` إلى إرث.",
    838: "الخبر يسمي أصلا ساميا ويقارن العربية `دلو` والسريانية والأكادية؛ حفظ الاتجاه مع عزل اسم البرج.",
    840: "فصل معنى الرمز الزرادشتي عن مدخلتي spirit وthe Ganges المتجانستين.",
    841: "فصل معنى spirit أو essence عن الرمز وعن النهر، ولم يورث أحد المتجانسات حكم الآخر.",
    848: "حقل الاشتقاق فارغ لمعنى island؛ لم يورث خبر المتجانس mute ولا خبر اسم النهر.",
    849: "المصدر يسمي قرضا من السنسكريتية لاسم النهر؛ عزل الاسم عن بقية متجانسات `گنگ`.",
    865: "الخبر يثبت الصورة الفارسية الوسطى ويسمي السريانية والأرمنية واليونانية مقترضات إيرانية؛ العربية تسمي النبات فارسيا، لكن اتجاهها لم يغلق بشاهدين صريحين.",
}


@dataclass(frozen=True)
class SelectedRow:
    row: H.SweepRow

    @property
    def key(self) -> str:
        return f"S{self.row.rank:05d}"

    @property
    def heading(self) -> str:
        return f"WO-B-R36-SOUND-{self.row.rank:05d}"


Review = R35.Review
R = R35.R

# سجل قراءة يدوي. لا يشتق الحكم من best ولا من وزن المروحة.
REVIEWS = {
    790: R("بهر", "OPEN-CANDIDATE", "جسر المعنى: interest أو profit حاضر في الفرع، لكن نص `بهر` العربي في الغلبة والعجز لا يسمي الحصة أو الربح.", "فصلت quotient عن profit داخل المدخلة، ورفضت التحليل السطحي؛ بقي التشابه الصوتي بلا مدار دلالي مباشر."),
    791: R("ببن", "TOOL-GAP", "جسر المعنى: desert حاضر، لكن /biyābān/ يحمل /y/ أسقطها الهيكل.", "أوقف الصامت الساقط المقارنة قبل وصل البرية بالانفتاح أو المنفذ."),
    792: R("خشتق", "COMPOUND-BOUNDARY", "جسر المعنى: fatigue مفككة مباشرة إلى `خسته` tired و`ـگی` لاحقة الاسم.", "قُرئ المكونان استقلالا؛ لم تورث الصورة المجموعة حكم أحدهما."),
    793: R("من", "TOOL-GAP", "جسر المعنى: middle أو centre حاضر، لكن /miyān/ يحمل /y/ أسقطها الهيكل.", "حفظت صلة المصدر بـ`ميدان` حاشية، وأوقف عطب الهيكل أي حكم على `من`."),
    794: R("بت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بت`: القطع والانفصال؛ لا يسمي naked.", "تجرد الجسد من الثوب نتيجة نزع لا معنى العري نفسه، وخبر الأصل احتمالي مستقل."),
    795: R("بر", "NUCLEUS-TRACE", "جسر المعنى: bank أو shore أرض تقابل الماء، وشاهدا العربية يسميان `البر` خلاف البحر.", "مدار 1: الضفة موضع البر عند حد الماء، ونواة التجرد والخلوص تصف اليابسة؛ اكتملت الأرجل بشاهدين مستقلين."),
    796: R("بم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بم`: محكمتا الباء والميم بلا معنى insurance.", "التأمين يدفع الخوف أو يحتمل الخطر، لكنه لا يساوي صوت العود ولا يختم خلاف المصدرين المحتملين."),
    797: R("بج", "LAW-GAP", "جسر المعنى: screw وcurve وtwist تشترك في الالتواء، لكن چ↔ج غير مسمى.", "معنى الالتواء مقروء، غير أن المروحة لا تمنحه مسارا صوتيا كاملا؛ لم يستبدل بمرشح خارجها."),
    798: R("رج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رج`: تحريك الشيء بقوة؛ لا يسمي vein أو blood vessel.", "جريان الدم وظيفة الوعاء لا معنى الرج، وفصل الخبر الإيراني عن الاقتراض الأرمني المسمى."),
    799: R("بشك", "COMPOUND-BOUNDARY", "جسر المعنى: ivy أو bindweed مفككة مباشرة إلى `پیچ` twist و`ـک` لاحقة.", "قُرئ الالتواء واللاحقة منفصلين؛ لم يحول شكل النبات إلى حكم جذر للصورة المجموعة."),
    800: R("رنجن", "COMPOUND-BOUNDARY", "جسر المعنى: coloured مفككة مباشرة إلى `رنگ` colour و`ـین` لاحقة صفة.", "المعنى حاصل من المكونين، فوقف الحكم عند حد التركيب."),
    801: R("سملغ", "OUT-OF-SCOPE", "جسر المعنى: Simurgh اسم مخلوق أسطوري بعينه، لا معنى معجميا عاما.", "عزلت الاسم، ورفضت التأثيل الشعبي إلى thirty وbird بعد الخبر الموروث."),
    802: R("مهن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مهن`: محاكم الحروف بلا معنى homeland أو native country.", "السكن في الوطن سياق للموطن لا معنى المادة العربية، والخبر الإيراني مستقل."),
    803: R("كت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كت`: القطع أو الجمع في محاكم حرفين؛ لا يسمي Universe.", "انتظام العالم أو جمع أجزائه وصف كلي عام لا معنى universe، فاختير مسار صوتي كامل وبقي مفتوحا."),
    804: R("وزج", "COMPOUND-BOUNDARY", "جسر المعنى: trait أو characteristic مفككة مباشرة إلى `ویژه` special و`ـگی` لاحقة الاسم.", "قُرئ المكونان ولم تقارن الصورة المجموعة بجذر عربي."),
    805: R("بلد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بلد`: إصمات ظاهر متسع؛ لا يسمي unclean أو wicked.", "كون النجاسة عالقة بالظاهر وصف محتمل لا معنى الصفة الأخلاقية أو المادية، والمصدر فارغ."),
    806: R("برنج", "COMPOUND-BOUNDARY", "جسر المعنى: colourless مفككة مباشرة إلى `بیـ` without و`رنگ` colour.", "الانتفاء من السابقة لا من حدث `برنج`؛ وقف الحكم عند حد المركب."),
    807: R("سبد", "COMPOUND-BOUNDARY", "جسر المعنى: dawn مفككة مباشرة إلى `سپید` white و`ـه` لاحقة اشتقاق.", "بياض الفجر من المكون؛ لم تورث الصورة المجموعة حكم `سبد`."),
    809: R("جج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جج`: محكمتا الجيم بلا معنى chick أو chicken.", "احتمال المحاكاة الصوتية في التركية لا يثبت اسما عربيا، والخبر يرجح أصلا صغديا."),
    810: R("جن", "LAW-GAP", "جسر المعنى: chin أو jaw عضو بارز، لكن چ↔ج غير مسمى.", "وصف البروز لا يساوي معنى الذقن، وفوق ضعف المدار بقي مسار الصوت ناقصا."),
    811: R("برك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`برك`: الاستقرار أو الثبوت؛ لا يسمي narrow أو thin.", "ضيق الضفة أو دقتها تفسير شكلي لا معنى الصفة، والتحليل التاريخي لم يؤهل كتفكيك حديث."),
    813: R("رستق", "COMPOUND-BOUNDARY", "جسر المعنى: truthful مفككة مباشرة إلى `راست` truth و`ـگو` saying.", "قُرئ الصدق وجذع القول مستقلين؛ لم يصدر حكم للصورة المركبة."),
    815: R("مهج", "COMPOUND-BOUNDARY", "جسر المعنى: muscle مفككة صراحة إلى `ماهی` fish و`ـچه` diminutive، أي little fish.", "قبلت عبارة From المباشرة مع تفسيرها الحرفي، وقرأت المكونين دون توريث حكمهما للمركب."),
    816: R("بش", "COMPOUND-BOUNDARY", "جسر المعنى: precedence مفككة مباشرة إلى `پیش` before و`ـی` لاحقة الاسم المجرد.", "المعنى الوظيفي من التركيب؛ لم يحول إلى انتشار `بش`."),
    817: R("مزق", "LAW-GAP", "جسر المعنى: marker pen أداة تحدث أثرا مكتوبا، لكن ژ↔ز غير مسمى.", "وظيفة القلم لا تساوي تمزيق `مزق`، وفوقها فجوة القانون؛ بقي الاسم الحديث مفتوحا."),
    818: R("ترن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ترن`: الابتعاد بقوة مع دقة؛ لا يسمي song أو rubai.", "مرور الصوت في الهواء تعليل للمصدر لا معنى الغناء، وشاهدا العربية في لفظ آخر."),
    819: R("بزج", "TOOL-GAP", "جسر المعنى: spring onion مفككة إلى `پیاز` onion و`ـچه` diminutive، لكن /piyāz/ يحمل /y/ أسقطها الهيكل.", "قُرئت المكونات، ثم أوقف عطب المكون الصوتي حكم المركب قبل أي مقارنة."),
    820: R("كس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كس`: نقص بالغؤور أو القشر؛ لا يسمي bowl.", "تقعر الوعاء هيئة عامة، وخبر الأصل الإيراني الهندي لا يثبت معنى عربيا في المرشح."),
    821: R("ار", "LAW-GAP", "جسر المعنى: yes أداة تصديق، لكن آ↔ا غير مسمى.", "الوظيفة النحوية لا تستخرج من محكمتي الألف والراء، وفوقها فجوة أول الهيكل."),
    822: R("مزد", "OPEN-CANDIDATE", "جسر المعنى: wage أو reward حاضر في الصورة، لكن الشواهد العربية لـ`مزد` تسمي البرد لا الأجر.", "الخبر يثبت سلسلة إيرانية هندو أوروبية؛ اتحاد الرسم لا ينشئ إرثا ولا تماسًا عربيا بلا مصدر."),
    823: R("رز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رز`: التداخل الشديد؛ لا يسمي secret أو mystery.", "استتار السر في النفس وصف رصدي، وخبر القروض الإيرانية لا يسمي العربية."),
    824: R("رز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رز`: التداخل الشديد؛ لا يسمي hornet أو bee.", "إدخال الحشرة إبرتها أو سماع الرز سلوك وصوت، لا اسم نوع الحشرة؛ فصل المتجانسان."),
    825: R("بشغ", "LAW-GAP", "جسر المعنى: answer أو response رجوع قول إلى سؤال، لكن خ↔غ غير مسمى.", "حفظت دلالة الاستجابة التاريخية، ولم تمررها عبر صف صوت غير موجود."),
    826: R("نجد", "COMPOUND-BOUNDARY", "جسر المعنى: racial مفككة مباشرة إلى `نژاد` race و`ـی` لاحقة الصفة.", "المعنى من المكونين؛ لم تقارن الصورة المركبة بجذر `نجد`."),
    827: R("جد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جد`: القطع أو شدة الاجتهاد؛ لا يسمي beggar أو miser.", "الطلب الشديد سلوك للسائل لا معنى اسم الشخص، وخبر الأصل المقارن لا يحسم السلسلة."),
    828: R("بلر", "OPEN-CANDIDATE", "جسر المعنى: crystal حاضر في `بلور` العربية، لكن حدث `بلر` لا يسمي صفاء الحجر.", "ثبت اللفظ في الشواهد وثبت مصدر الفارسية الأوسط من Pali، ولم يسم المصدر اتجاه العربية؛ بقي تماسًا مفتوحا."),
    829: R("جب", "LAW-GAP", "جسر المعنى: wood أو stick مادة صلبة ممتدة، لكن چ↔ج غير مسمى.", "الصلابة والامتداد لا يكفيان لاسم الخشب، ومسار الصوت نفسه ناقص."),
    830: R("بم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بم`: محكمتا الباء والميم؛ لا يسمي fear.", "احتباس النفس عند الخوف هيئة جسدية لا معنى الخوف، والخبر الهندو أوروبي مستقل."),
    831: R("شجرد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شجرد`: محاكم حروف بلا معنى pupil أو student.", "اتباع المعلم حاضر في الأصل الإيراني الأولي، لكنه لا يثبت معنى عربيا للمرشح الحي."),
    833: R("جن", "TOOL-GAP", "جسر المعنى: milkvetch نبات، لكن /gavan/ يحمل /v/ أسقطها الهيكل.", "التحليل الاحتمالي cow مع suffix غير مؤهل، وعطب الصامت أوقف المقارنة."),
    834: R("قب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`قب`: نتوء متجوف صلب؛ لا يسمي gate.", "تقوس الباب أو إحاطته بالمدخل هيئة بناء لا معنى gate، والخبر يسمي قرضا تركيا."),
    835: R("خن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خن`: التخلخل الممتد في الباطن؛ لا يسمي caravanserai أو rifling.", "فصلت معنى النزل عن أخاديد السلاح، ولم تورثهما معنى house التاريخي بلا جسر عربي."),
    836: R("ارز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ارز`: محاكم حروف بلا معنى currency أو value.", "الخبر يثبت سلسلة إيرانية لمعنى القيمة؛ غياب الشاهد العربي منع أي حكم تماس أو أثر."),
    837: R("زر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زر`: محاكم حرفين لا تسمي groan أو lament.", "صوت الأنين لا يساوي معنى الذهب أو الزر، والخبر الإيراني بقي مستقلا."),
    838: R("دلو", "OUT-OF-SCOPE", "جسر المعنى: Aquarius هنا اسم برج، وإن كان المصدر يسمي أصلا ساميا ويقارن `دلو` العربية.", "عزل اسم البرج كما عزلت الأعلام الفلكية السابقة؛ حفظ خبر الاتجاه ولم يصدر حكم جذري."),
    839: R("بج", "TOOL-GAP", "جسر المعنى: dawn أو morning حاضر، لكن /pagāh/ يحمل /h/ نهائية أسقطها الهيكل.", "لا يقارن الفجر بهيكل ناقص؛ توقف الحكم قبل مدار الضوء."),
    840: R("بلهر", "TOOL-GAP", "جسر المعنى: faravahar رمز بعينه، لكن /farvahar/ يحمل /v/ أسقطها الهيكل.", "فصل الرمز عن الروح وعن النهر، وأوقف الصامت الساقط الحكم."),
    841: R("بلهر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بلهر`: محاكم حروف بلا معنى spirit أو essence.", "هذه المدخلة منقوطة /foruhar/ بلا /v/ صامتة؛ بقي اختلاف المعنى عن الرمز حاسما."),
    842: R("جرت", "LAW-GAP", "جسر المعنى: nonsense كلام ساقط المعنى، لكن چ↔ج غير مسمى.", "ضعف الكلام لا يساوي حدث `جرت`، ومسار الصوت ناقص؛ فصلت المدخلة عن nap."),
    843: R("جرت", "LAW-GAP", "جسر المعنى: nap انقطاع قصير عن اليقظة، لكن چ↔ج غير مسمى.", "الراحة لا تستخرج من الجريان أو الجر، وفوقها فجوة القانون؛ فصلت المتجانسات."),
    844: R("جنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جنج`: محاكم حروف بلا معنى mute.", "خبر التطور من hum أو mock احتمالي ومحاك للصوت؛ لم يحول العجز عن الكلام إلى جذر عربي."),
    845: R("جنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جنج`: محاكم حروف بلا معنى irrational أو crooked.", "فصلت الصفة العقلية والظهر المنحني عن مدخلة mute ولم تورث أصلها."),
    848: R("جنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جنج`: محاكم حروف بلا معنى island.", "حقل الأصل فارغ؛ لم يورث island خبر mute أو اسم Ganges."),
    849: R("جنج", "OUT-OF-SCOPE", "جسر المعنى: Ganges اسم نهر لا معنى معجميا عاما.", "عزل الاسم المقترض من السنسكريتية عن island وعن صفات `گنگ`."),
    850: R("بش", "OPEN-CANDIDATE", "جسر المعنى: forest أو jungle انتشار ظاهر كثيف للنبات، وهو يلامس نواة `بش`.", "المحيط يذكر أبشت الأرض والتف نبتها، لكن الشاهد المستقل الثاني لمعنى الغابة غائب؛ بقي صدى نواة مفتوحا."),
    851: R("بشكن", "OPEN-CANDIDATE", "جسر المعنى: snapping fingers صوت قطع سريع، لكن حدث `بشكن` لا يسمي الحركة.", "وسم گ↔ك مسار قرض لا يثبت مانحا، وحقل الأصل فارغ؛ بقيت المحاكاة المحتملة مفتوحة."),
    852: R("رج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رج`: تحريك بقوة؛ لا يسمي sand أو gravel.", "جريان الرمل أو رج الحصى هيئة حركة، لا معنى المادة؛ والخبر الإيراني من flow لم يورث حكما عربيا."),
    853: R("امد", "LAW-GAP", "جسر المعنى: ready أو prepared حاضر، لكن آ↔ا غير مسمى.", "رفضت surface analysis بعد الخبر الموروث، وبقيت فجوة أول الهيكل مانعة."),
    854: R("بم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بم`: محكمتا الباء والميم بلا معنى land أو soil.", "ثبات الأرض أو احتواؤها وصف عام، والخبر الهندو إيراني مستقل؛ فصلت المدخلة عن owl."),
    855: R("بم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بم`: محكمتا الباء والميم؛ لا يسمي roof.", "تغطية السقف وظيفة بنائية لا معنى المادة، وفصلت roof عن dawn المتجانسة."),
    856: R("بم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بم`: محكمتا الباء والميم؛ لا يسمي dawn أو gleam.", "انبثاق الضوء لا يثبت من الرصف، والخبر الهندو أوروبي مستقل عن roof."),
    857: R("جرد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جرد`: تقشير أو إزالة ظاهر؛ لا يسمي pollen.", "انفصال غبار الطلع عن الزهرة وصف دورة، لا معنى pollen، وحقل الأصل فارغ."),
    858: R("جرد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جرد`: تقشير أو إزالة ظاهر؛ لا يسمي bread roll أو loaf.", "استدارة الرغيف وشقه شكل واستعمال، لا معنى المادة؛ فصل المتجانسان."),
    859: R("جرد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جرد`: تجريد الظاهر؛ لا يسمي kidney.", "تنقية الكلية للجسم وظيفة عضو لا معنى اسمه، والخبر الهندو إيراني مستقل."),
    861: R("وني", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`وني`: الفتور والتوقف؛ لا يسمي reed أو cane.", "اختير المرشح ذو المسار الكامل بدل `نوي` الناقص؛ صلابة القصبة أو فراغها لا يساوي الفتور."),
    862: R("وني", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`وني`: الفتور والتوقف؛ لا يسمي أداة النفي no.", "فصلت أداة النفي عن reed، ولم تحول الوظيفة النحوية إلى حدث جذري."),
    863: R("كنر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كنر`: الاستتار في جوف؛ لا يسمي next to أو besides.", "المجاورة عند الحافة موضع نسبي لا معنى الاستتار، وفصل حرف الجر عن بقية المتجانسات."),
    864: R("كنر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كنر`: الاستتار في جوف؛ لا يسمي aside.", "التنحي إلى جانب قد يخفي الشيء لكنه استعمال ظرفي لا معنى المادة؛ فصل المدخلة السابقة."),
    865: R("كنر", "OPEN-CANDIDATE", "جسر المعنى: Ziziphus هو `الكُنار` في العربية، والعين يسميه السدر بالفارسية.", "المصدر يثبت الفارسية الوسطى وقروضا إيرانية في ألسن أخرى، لكن شاهد اتجاه عربي صريح ثان لم يكتمل؛ بقي تماسًا مفتوحا."),
    866: R("برق", "LAW-GAP", "جسر المعنى: brightness أو lustre حاضر مباشرة في لمعان `برق` وشاهديه، لكن غ↔ق غير مسمى.", "مدار الضوء قوي، وصف ف↔ب مسمى، غير أن الرجل الأخيرة ناقصة؛ لم يصدر أثر عبر فجوة القانون."),
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
            raise AssertionError(f"تغير عداد نسخة v16 في {name}")
        if len(data.get("both") or []) != expected_both or len(data.get("sound_only") or []) != expected_sound:
            raise AssertionError(f"تغير طول قوائم نسخة v16 في {name}")
        total_both += expected_both
        total_sound += expected_sound
    if total_both != 14535 or total_sound != 106805:
        raise AssertionError("تغير مجموع أحواض v16")


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
            if row.rank > 789 and len(fresh) < 70:
                internal_skips.append(row.rank)
            continue
        seen.add(key)
        if row.rank <= 789:
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
        "خسته": {3993}, "پیچ": {3772}, "ـک": {7513}, "رنگ": {138},
        "ـین": {10309, 10310}, "ویژه": {3233}, "بیـ": {14756},
        "سپید": {3030}, "ـه": {7113, 7114, 7115}, "راست": {1392, 1393},
        "گو": {5574, 5575, 5576, 5577}, "ماهی": {757, 758},
        "ـچه": {7514}, "پیش": {4609, 4610, 4611},
        "ـی": {6328, 6329, 6330, 6331}, "پیاز": {1088}, "نژاد": {2705},
    }
    for word, expected in expected_indices.items():
        actual = {index for index, _entry in grouped.get(word, [])}
        if actual != expected:
            raise AssertionError(f"تغير جرد مكون {word}: {sorted(actual)}")
    fan_counts = {
        "خسته": 27, "ـگی": 56, "پیچ": 60, "ـک": 0, "رنگ": 8,
        "ـین": 16, "ویژه": 57, "بیـ": 14, "سپید": 18, "ـه": 0,
        "راست": 18, "گو": 72, "ماهی": 20, "ـچه": 60, "پیش": 60,
        "ـی": 0, "پیاز": 60, "نژاد": 9,
    }
    for word, expected in fan_counts.items():
        fan = tuple(H.FAN.rank(word, H.FAN.fan(word, "persian"), "persian"))
        if len(fan) != expected:
            raise AssertionError(f"تغيرت مروحة المكون {word}: {len(fan)}")
    expected_raw = {
        "خسته": {4461}, "ـگی": {17716}, "پیچ": {4214, 4215}, "ـک": {8807},
        "رنگ": {143}, "ـین": {12681, 12682}, "ویژه": {3602}, "بیـ": {17675},
        "سپید": {3335}, "ـه": {8351, 8352, 8353, 8354},
        "راست": {1473, 1474}, "گو": {6551, 6552, 6553, 6554, 6555, 6556, 6557},
        "ماهی": {804, 805}, "ـچه": {8808}, "پیش": {5126, 5127, 5128},
        "ـی": {7420, 7421, 7422, 7423, 7424}, "پیاز": {1158}, "نژاد": {2979},
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
    if review.verdict == "NUCLEUS-TRACE":
        return "اكتملت أرجل الصوت والحدث والمعنى بشاهدين عربيين مستقلين؛ صدر أثر نواة استكشافي."
    if review.verdict == "COMPOUND-BOUNDARY":
        return "وقف الحكم عند حد المركب؛ لم تورث الصورة المجموعة حكم مكون ولم يخترع تفكيك."
    if review.verdict == "LAW-GAP":
        return "طريق المعنى مفحوص، لكن مسار الصوت يحوي صفا غير مسمى؛ لم يصدر حكم موجب."
    if review.verdict == "TOOL-GAP":
        return "صف الحوض أسقط صامتا منطوقا؛ توقف العضو قبل الحكم ولم يعوض الصامت يدويا."
    if review.verdict == "OUT-OF-SCOPE":
        return "العضو اسم علم لا معنى معجميا عاما؛ عزل من الحكم الجذري مع حفظه في التغطية."
    return "مسار الصوت قابل للفحص، لكن المدار لم يكتمل إلى حكم؛ بقي المرشح مفتوحا."


def decide(item: SelectedRow) -> H.Decision:
    review = REVIEWS[item.row.rank]
    return H.Decision(review.candidate, review.verdict, H.state_for(review.verdict), review.orbit, obstacle_for(review))


def decomposition_lines(item: SelectedRow, raw: dict) -> list[str]:
    rank = item.row.rank
    if rank not in EXACT_DECOMPOSITIONS:
        return []
    if rank == 815:
        etymology = raw["etymology"]
        if "From ماهی" not in etymology or "+ ـچه" not in etymology or "little fish" not in etymology:
            raise AssertionError("تغير التفكيك المباشر للرتبة 815")
    else:
        decomposition = P25.direct_from_plus(raw["etymology"])
        if not decomposition:
            raise AssertionError(f"غاب تفكيك From X + Y للرتبة {rank}")
        joined = H.clean(" + ".join(decomposition))
        for component in EXPECTED_COMPONENTS[rank]:
            if H.clean(component) not in joined:
                raise AssertionError(f"غاب مكون {component} من الرتبة {rank}: {decomposition}")
    lines = [
        f"- تفكيك Kaikki الحصري المباشر من السطر الخام {raw['line']}: «{H.clip(raw['etymology'], 420)}».",
        f"- قراءة المكونات المستقلة: {COMPONENT_READINGS[rank]}",
        "- الخطوة صفر: قبل التفكيك النهائي المباشر لم تقارن الصورة وحدة جذرية؛ قُرئ كل مكون مسمى وحده.",
    ]
    if rank == 819:
        lines.extend([
            f"- عطب الهيكل: {TOOL_GAPS[rank]}",
            "- بعد قراءة المكونات أوقف TOOL-GAP حكم الصورة المجموعة؛ لا حكم من هيكل ناقص.",
        ])
    return lines


BASE_MAKE_CARD = R35.make_card


def make_card(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit) -> str:
    card = BASE_MAKE_CARD(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit)
    return card.replace("الجولة 35،", "الجولة 36،")


def validate_decisions(selected, raw_entries, decisions, ranked_by_rank, sense_map) -> None:
    if set(REVIEWS) != set(SOUND_RANKS):
        raise AssertionError("جدول المدار اليدوي لا يغطي الرتب السبعين")
    parsed = {item.row.rank for item in selected if P25.direct_from_plus(raw_entries[item.row.rank]["etymology"])}
    if parsed != PARSER_FROM_PLUS:
        raise AssertionError(f"تغيرت أسطر From X + Y المباشرة: {sorted(parsed)}")
    expected_verdicts = {
        "COMPOUND-BOUNDARY": 10,
        "LAW-GAP": 10,
        "NUCLEUS-TRACE": 1,
        "OPEN-CANDIDATE": 40,
        "OUT-OF-SCOPE": 3,
        "TOOL-GAP": 6,
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
        if decision.verdict in {"OPEN-CANDIDATE", "NUCLEUS-TRACE", "OUT-OF-SCOPE"} and not complete:
            raise AssertionError(f"حكم بمسار ناقص في الرتبة {row.rank}: {decision.verdict}")
        if decision.verdict == "NUCLEUS-TRACE":
            if coverage < 2 or H.event_line(decision.candidate).startswith("لا حدث"):
                raise AssertionError(f"أثر بلا حدث وشاهدين في الرتبة {row.rank}")
        if row.rank in EXACT_DECOMPOSITIONS and decision.verdict not in {"COMPOUND-BOUNDARY", "TOOL-GAP"}:
            raise AssertionError(f"تفكيك مباشر بلا حد مركب أو عطب أداة في الرتبة {row.rank}")
        if row.rank in TOOL_GAPS and decision.verdict != "TOOL-GAP":
            raise AssertionError(f"هيكل ناقص بلا TOOL-GAP في الرتبة {row.rank}")
        if row.rank in LAW_GAPS and decision.verdict != "LAW-GAP":
            raise AssertionError(f"مسار ناقص بلا LAW-GAP في الرتبة {row.rank}")
        if row.rank in OUT_OF_SCOPE and decision.verdict != "OUT-OF-SCOPE":
            raise AssertionError(f"اسم علم بلا OUT-OF-SCOPE في الرتبة {row.rank}")
        if not REVIEWS[row.rank].meaning_path.startswith(("جسر المعنى:", "نص الحدث المجمد")):
            raise AssertionError(f"طريق المعنى غير مسمى في الرتبة {row.rank}")


def validate_text(selected, texts, prior_pairs) -> None:
    if len(selected) != 70 or BATCH_SIZES != (35, 35):
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = re.findall(r"^### (WO-B-R36-SOUND-\d{5}):", joined, re.MULTILINE)
    if headings != [item.heading for item in selected]:
        raise AssertionError("معرفات الجولة 36 لا تطابق النافذة")
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
    previous = 789
    for number, batch in enumerate(batches, 1):
        lo = 0 if number == 1 else 35
        hi = lo + len(batch)
        counts = Counter(decision.verdict for decision in decisions[lo:hi])
        distribution = "؛ ".join(f"{key}={counts[key]}" for key in sorted(counts))
        batch_skips = [rank for rank in stats["skipped"] if previous < rank <= batch[-1].row.rank]
        skipped = ", ".join(map(str, batch_skips)) or "0"
        lines.extend([
            f"## الجولة السادسة والثلاثون، دفعة sound_only رقم {number}", "",
            f"- الوقت: {now}، Africa/Cairo.",
            f"- رشح وكتب: {len(batch)}؛ المواضع المقروءة المتجاوزة داخل المدى: {skipped}.",
            f"- المواضع: من {batch[0].heading} إلى {batch[-1].heading}.",
            f"- توزيع الأحكام: {distribution}.",
            "- طريق المعنى: سمي من جسر معنى صريح أو من نص الحدث المجمد في كل بطاقة.",
            "- المدار: كتب يدويا لكل عضو، وفصلت الأصداء اللينة عن الأثر المحكم.",
            "- المروحة: ولدت حية كاملة ورتبت بالأوزان، ومسحت مواد جميع مرشحيها بلا قص للحقل المصدر.",
            "- المتجانسات: قرئت كل مداخل الرسم، وسجل العدد ورقم المدخلة المختارة في كل بطاقة.",
            "- المركب: قبل From X + Y النهائي المباشر أو التصريح المباشر المحكم حصرا؛ لم يخترع مكون.",
            "- التحقق البنيوي: المعرفات فريدة؛ لا بطاقة فوق 5KB؛ لا شرطة طويلة؛ الأرقام غربية والنص NFC.",
            f"- آخر موضع في الدفعة: {batch[-1].heading}، `{batch[-1].row.branch}`.", "",
        ])
        previous = batch[-1].row.rank
    total = Counter(decision.verdict for decision in decisions)
    distribution = "؛ ".join(f"{key}={total[key]}" for key in sorted(total))
    max_size = max(sizes)
    max_item = selected[sizes.index(max_size)]
    traces = [item.heading for item, decision in zip(selected, decisions) if decision.verdict == "NUCLEUS-TRACE"]
    lines.extend([
        "## حصيلة الجولة السادسة والثلاثين", "",
        f"- حمل `persian.md` مرة واحدة؛ أزواج WO-B المقروءة={stats['pair_count']}؛ المتجاوز داخل النافذة={', '.join(map(str, stats['skipped']))}.",
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- نطاق الصوت الجديد: الرتب 790-866 بعد WO-B-R35-SOUND-00789، مع تجاوز المواضع المقروءة 808 و812 و814 و832 و846 و847 و860 فقط.",
        f"- الأثر النووي الاستكشافي الجديد: {', '.join(traces)}؛ لم تفعل طبقة البرهان ولم تنشر أرقاما.",
        "- التفكيك المباشر المؤهل: S00792، S00799، S00800، S00804، S00806، S00807، S00813، S00815، S00816، S00819، S00826؛ قرئت المكونات المستقلة كلها، ووقف S00819 عند عطب المكون الصوتي.",
        "- التحليلات غير المؤهلة: S00790، S00793، S00801، S00811، S00833، S00853؛ حفظت تاريخية المصدر أو احتماله ولم تحول إلى تفكيك نهائي.",
        "- أعطاب الأداة: S00791، S00793، S00819، S00833، S00839، S00840؛ لم تعوض الصوامت المنطوقة الساقطة.",
        "- فجوات القانون: S00797، S00810، S00817، S00821، S00825، S00829، S00842، S00843، S00853، S00866.",
        "- الأعلام المعزولة: S00801 وS00838 وS00849؛ حفظ خبر الأصل السامي لاسم الدلو وخبر القرض السنسكريتي لاسم الغانج بلا حكم جذري.",
        "- ملاحظات الاتجاه: حفظت قروض `راز` الإيرانية إلى الآرامية والعبرية والسريانية، وأصل `کنار` الإيراني وقروضه المسماة؛ لم يمد اتجاه إلى العربية بلا شاهدين صريحين.",
        "- أحواض `nucleus-sweep-*.json` التسعة الحالية v16 قرئت كاملة من القرص؛ both=14535 وsound_only=106805؛ ثبت الحجم وSHA-256 والعدادات لكل ملف.",
        f"- أكبر بطاقة: {max_size} بايت، {max_item.heading}؛ كل البطاقات دون 5KB.",
        "- لم تفعل طبقة البرهان؛ مر حارس نقاء الشحنة وختم CLEAN؛ لم يقع ship ولم يستعمل git.",
        "", f"<!-- {MARKER}:END -->", "", DONE_LINE,
    ])
    return "\n".join(lines)


def validate_existing(reading_text: str, report_text: str) -> None:
    match = re.search(rf"<!-- {re.escape(MARKER)}:START -->(.*?)<!-- {re.escape(MARKER)}:END -->", reading_text, re.DOTALL)
    if not match:
        raise AssertionError("محضر الجولة موجود وبطاقاتها غائبة")
    headings = re.findall(r"^### (WO-B-R36-SOUND-\d{5}):", match.group(1), re.MULTILINE)
    expected = [f"WO-B-R36-SOUND-{rank:05d}" for rank in SOUND_RANKS]
    if headings != expected:
        raise AssertionError("مقطع الجولة 36 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(DONE_LINE):
        raise AssertionError("سطر DONE36 ليس خاتمة التقرير")


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
        print("ROUND36 ALREADY PRESENT AND VALID")
        print(DONE_LINE)
        return 0

    validate_nucleus_snapshot()
    data = json.loads(SWEEP.read_text(encoding="utf-8"))
    selected, stats = select_rows(data, reading_text)
    prior_pairs = H.read_pairs(reading_text)
    lexicon = json.loads(LEXICON.read_text(encoding="utf-8"))

    R35.EXPECTED_ENTRY_INDEX = EXPECTED_ENTRY_INDEX
    R35.EXPECTED_RAW_LINE = EXPECTED_RAW_LINE
    entries, grouped = R35.select_branch_entries(selected, lexicon)
    raw_entries = R35.load_raw_entries(selected, entries)
    validate_components(grouped)

    R35.SOURCE_NOTES = SOURCE_NOTES
    R35.TOOL_GAPS = TOOL_GAPS
    R28.EXPECTED_ENTRY_INDEX = EXPECTED_ENTRY_INDEX
    R28.EXPECTED_RAW_LINE = EXPECTED_RAW_LINE
    R28.REVIEWS = REVIEWS
    R28.BLOCKED_BOUNDARIES = {}
    R28.TOOL_GAPS = TOOL_GAPS
    R28.OUT_OF_SCOPE = OUT_OF_SCOPE
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
    R32.OUT_OF_SCOPE = OUT_OF_SCOPE
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
        "## الجولة السادسة والثلاثون: متابعة حوض sound_only (2026-08-27)\n\n"
        "- النطاق: 70 عضوا طازجا بعد WO-B-R35-SOUND-00789؛ من الرتبة 790 إلى 866 مع تجاوز 808 و812 و814 و832 و846 و847 و860 لأنها مقروءة؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ طريق المعنى مسمى، والمدار اليدوي حاسم، والأصداء مفصولة عن الأثر المحكم.\n"
        "- لقطة الأحواض: قرئت ملفات nucleus-sweep-*.json التسعة الحالية v16 من القرص؛ ثبتت بصماتها وعداداتها قبل الانتخاب.\n\n"
        + "\n".join(texts[:35])
        + "\n## الدفعة الثانية: متابعة sound_only بعد الرتبة 827\n\n"
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
    print("ROUND36 READY")
    print("NUCLEUS_V16_FILES", len(NUCLEUS_SNAPSHOT), "SHA256_AND_COUNTS_OK")
    print("NUCLEUS_V16_TOTALS", "BOTH=14535", "SOUND_ONLY=106805")
    print("SKIPPED", ",".join(map(str, stats["skipped"])))
    print("BATCHES", *BATCH_SIZES, "SELECTED", len(selected))
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("TRACES", "S00795")
    print("EXACT_COMPONENTS", " ".join(f"S{rank:05d}" for rank in sorted(EXACT_DECOMPOSITIONS)))
    print("TOOL_GAPS", len(TOOL_GAPS), "LAW_GAPS", len(LAW_GAPS), "OUT_OF_SCOPE", len(OUT_OF_SCOPE))
    print("MAX_CARD", max(sizes), selected[sizes.index(max(sizes))].heading)
    if args.preview:
        print("PREVIEW ONLY")
        print(DONE_LINE)
        return 0

    with READING.open("a", encoding="utf-8", newline="") as handle:
        handle.write(reading_append)
    with REPORT.open("a", encoding="utf-8", newline="") as handle:
        handle.write(report_append)
    print("ROUND36 WRITTEN")
    print(DONE_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
