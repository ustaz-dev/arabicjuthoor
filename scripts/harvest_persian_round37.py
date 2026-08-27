# -*- coding: utf-8 -*-
"""المسار B، الجولة 37: متابعة إنقاذ حوض sound_only في دفعتين من 35 بطاقة."""

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

import harvest_persian_round36 as R36  # noqa: E402

R35 = R36.R35
R34 = R36.R34
R32 = R36.R32
R31 = R36.R31
R29 = R36.R29
R28 = R36.R28
H = R36.H
P = R36.P
P25 = R36.P25
READING = R36.READING
REPORT = R36.REPORT
SWEEP = R36.SWEEP
NUCLEUS_DIR = R36.NUCLEUS_DIR
LEXICON = R36.LEXICON
RAW_LEXICON = R36.RAW_LEXICON
MARKER = "LANE-B-PERSIAN-ROUND37-2026-08-27"
CARD_LIMIT = 5120
SOUND_RANKS = (
    867, 868, 869, 870, 871, 872, 873, 875, 876, 877, 878, 879, 880,
    881, 882, 883, 884, 885, 886, 887, 888, 889, 890, 891, 892, 893,
    894, 895, 896, 897, 898, 899, 900, 901, 902, 903, 904, 906, 907,
    908, 909, 910, 911, 912, 913, 914, 915, 916, 917, 920, 921, 923,
    924, 925, 926, 927, 928, 929, 930, 931, 933, 934, 935, 936, 937,
    938, 939, 940, 941, 942,
)
BATCH_SIZES = (35, 35)
DONE_LINE = "LANE-B DONE37 70 WO-B-R37-SOUND-00942"
EXPECTED_SKIPS = (874, 905, 918, 919, 922, 932)

# النسخة السابعة عشرة المقروءة من القرص.
NUCLEUS_SNAPSHOT = {
    "nucleus-sweep-ancient_greek.json": (7985130, "d3bcfc13618d3500591d31fb2ebded97e3ef932ff1c8653dccaae2dd3136a082", 2329, 16776),
    "nucleus-sweep-english_middle.json": (3415749, "2021380b896c6d046b8334adeb7064d8f36ffb9a8e17213e254cfbbedcada5c4", 1414, 7991),
    "nucleus-sweep-english_old.json": (1294040, "c3b57ccf376f9e71f09adff122f5bbbe3590644ed51dfed8f691f3f3ecff7e0b", 474, 3414),
    "nucleus-sweep-gothic.json": (1428294, "ecfce47e37f34664f1748f82571da5b22f313d50bd20131a0a154c67e74eacc8", 338, 3080),
    "nucleus-sweep-latin.json": (18840752, "36c02a1ea3a51cc388b2349af119d3ba2334d7f5ba9a97ab9ca3f3451fd88448", 6591, 39467),
    "nucleus-sweep-old_irish.json": (952787, "7aaa1d45242c3dd011824434105ab36d92db10fe23d7f466f7f2e96d95f88153", 278, 2740),
    "nucleus-sweep-old_norse.json": (1381006, "9ecb7bdeef6a54820847126f4508c6bd97e36788a0384b90daa01ff3997faa56", 476, 3751),
    "nucleus-sweep-persian.json": (5463837, "605249f68379b18edc9ec967a6bd1bd331c1334b7d761311bfeaadff37cb0cdc", 1448, 13498),
    "nucleus-sweep-welsh.json": (5776914, "1a8a1bc3659854c954955effd359303b8b18d3cd4001331c6d6e6979e309aabb", 1187, 16088),
}

EXPECTED_ENTRY_INDEX = dict(zip(SOUND_RANKS, (
    4226, 4234, 4236, 4238, 4242, 4243, 4245, 4263, 4270, 4272, 4276,
    4300, 4303, 4312, 4323, 4338, 4339, 4344, 4356, 4361, 4364, 4365,
    4368, 4374, 4400, 4405, 4406, 4414, 4415, 4416, 4429, 4433, 4436,
    4437, 4438, 4443, 4444, 4465, 4468, 4469, 4471, 4472, 4473, 4474,
    4475, 4476, 4478, 4485, 4490, 4510, 4511, 4515, 4520, 4521, 4522,
    4524, 4530, 4534, 4535, 4536, 4543, 4544, 4545, 4548, 4549, 4551,
    4554, 4555, 4557, 4560,
)))
EXPECTED_RAW_LINE = dict(zip(SOUND_RANKS, (
    4714, 4723, 4725, 4727, 4733, 4734, 4736, 4757, 4765, 4767, 4773,
    4797, 4800, 4809, 4821, 4836, 4837, 4843, 4859, 4864, 4867, 4868,
    4871, 4877, 4905, 4910, 4911, 4920, 4921, 4922, 4935, 4939, 4942,
    4943, 4944, 4949, 4950, 4971, 4974, 4975, 4978, 4979, 4980, 4981,
    4982, 4983, 4985, 4992, 4997, 5018, 5019, 5023, 5029, 5030, 5031,
    5034, 5040, 5044, 5045, 5046, 5053, 5054, 5055, 5058, 5059, 5061,
    5064, 5065, 5067, 5071,
)))

PARSER_FROM_PLUS = {879, 881, 893, 936}
EXACT_DECOMPOSITIONS = {869, 873, 879, 881, 893, 904, 929}
EXPECTED_COMPONENTS = {
    869: ("درود", "ـگر"),
    873: ("خایه", "ـگین"),
    879: ("چای", "خانه"),
    881: ("گرا", "ـیش"),
    893: ("پوش", "ـش"),
    904: ("گرز", "ـه"),
    929: ("دست", "ـه"),
}
COMPONENT_READINGS = {
    869: "`درود`: entries[587-589] والخام 629-631، واختير معنى timber أو plank، ومروحته 18: OPEN-CANDIDATE. `ـگر`: entry[10504] والخام 12956 لاحقة الفاعل، ومروحتها 80: MORPHOLOGY-GAP.",
    873: "`خایه`: entry[182] والخام 187 لمعنى egg، ومروحتها صفر: OPEN-CANDIDATE. `ـگین`: entry[14793] والخام 17717 لاحقة -ful، ومروحتها 40: MORPHOLOGY-GAP.",
    879: "`چای`: entry[496] والخام 533 لمعنى tea، ومروحتها صفر، لكن /čāy/ يحمل /y/ أسقطها الهيكل: TOOL-GAP. `خانه`: entry[262] والخام 274 لمعنى house، ومروحتها 30: OPEN-CANDIDATE.",
    881: "`گرا`: غائبة من branch-lexicons والخام مستقلة، ومروحتها 80: FORM-LINK. `ـیش`: غائبة من اللقطتين مستقلة، ومروحتها 48: MORPHOLOGY-GAP؛ /-yeš/ يحمل /y/ أسقطها الهيكل.",
    893: "`پوش`: غائبة من branch-lexicons وحاضرة في الخام 10688 جذعا مضارعا لـ`پوشیدن`، ومروحتها 60: FORM-LINK. `ـش`: اختيرت entry[10303] والخام 12674 لاحقة اسم الحدث، ومروحتها صفر: MORPHOLOGY-GAP.",
    904: "`گرز`: entry[4443] والخام 4949 لمعنى mace أو club، ومروحتها 24: OPEN-CANDIDATE. `ـه`: اختيرت entry[7113] والخام 8351 لاحقة اشتقاق اسم متصل، ومروحتها صفر: MORPHOLOGY-GAP.",
    929: "`دست`: entries[1138-1139] والخام 1210-1211 لمعنى hand أو set، ومروحتها 27: OPEN-CANDIDATE. `ـه`: اختيرت entry[7113] والخام 8351 لاحقة اشتقاق، ومروحتها صفر: MORPHOLOGY-GAP.",
}

TOOL_GAPS = {
    876: "الصورة `زیان` منقوطة /ziyān/، لكن الهيكل أسقط /y/ المنطوقة.",
    879: "المكون `چای` منقوط /čāy/، لكن هيكله داخل المركب أسقط /y/ المنطوقة.",
    880: "الصورة `همایون` منقوطة /homāyun/، لكن الهيكل أسقط /y/ المنطوقة.",
    881: "اللاحقة `ـیش` منقوطة /-yeš/، لكن هيكل الصورة المجموعة أسقط /y/ المنطوقة.",
    885: "الصورة `خور` منقوطة /xwar/، لكن الهيكل أسقط /w/ المنطوقة.",
    916: "الصورة `ویرایش` منقوطة /wīrāyiš/، لكن الهيكل أسقط /y/ المنطوقة.",
    920: "الصورة `گوازه` منقوطة /gavāza/، لكن الهيكل أسقط /v/ المنطوقة.",
    921: "الصورة `گاوزنه` منقوطة /gāvzane/، لكن الهيكل أسقط /v/ المنطوقة.",
    926: "الصورة `خاور` منقوطة /xāvar/، لكن الهيكل أسقط /v/ المنطوقة.",
    927: "الصورة `پیکر` منقوطة /paykar/، لكن الهيكل أسقط /y/ المنطوقة.",
    930: "الصورة `دستیار` منقوطة /dastyār/، لكن الهيكل أسقط /y/ المنطوقة.",
    936: "الصورة `داور` منقوطة /dāvar/، لكن الهيكل أسقط /v/ المنطوقة.",
    940: "الصورة `ساگوارو` منقوطة /sāguāro/ وتحمل واوا وسطى منطوقة، لكن الهيكل أسقطها.",
}
LAW_GAPS = {867, 868, 870, 877, 884, 902, 903, 907, 908, 913, 915, 923, 931}
OUT_OF_SCOPE = {938: "اسم نهر Araks أو Aras بعينه في حقل name، لا معنى معجميا عاما."}
REJECTED_ANALYSES = {
    886: "التحليل إلى `در` court و`ـی` صفة موسوم By surface analysis بعد الصورة الوسطى الموروثة، فلم يؤهل تفكيكا نهائيا.",
    930: "one who holds the hand تفسير على طبقة Proto-Iranian بعد خبر الوراثة الوسطى، لا From نهائيا مباشرا للصورة الحديثة.",
    933: "التحليل إلى `شب` night و`ـی` موسوم By surface analysis بعد خبر القميص الأوسط، فلم يحول إلى مركب حديث.",
    936: "التحليل إلى `داد` justice و`ـور` موسوم By surface analysis بعد الصورة الوسطى الموروثة، ثم أوقفه عطب /v/ أيضا.",
    941: "التحليل إلى `هن` و`گام` موسوم by surface analysis بعد الصورة الوسطى الموروثة، فلم يؤهل.",
}
SOURCE_NOTES = {
    868: "خبر الأصل يسمي قرضا تركيا ويعدد قروضا غير عربية؛ لم يمد الاتجاه إلى العربية.",
    871: "معنى first income مرتبط تاريخيا باليد اليمنى؛ فصل عن شاهد `دشت` العربي الذي يصرح بأنه فارسي في معنى plain.",
    872: "مدخلة evil أو wicked مستقلة؛ لم ترث شاهد `دشت` العربي لمعنى plain ولا حكم المتجانس السابق.",
    878: "خبر الأصل يرجح ركيزة BMAC ويعدد مقابلات هندوأوروبية؛ الشاهد العربي اسم شخص لا معنى brick.",
    895: "الخبر يذكر حضور `بورق` في العربية ضمن سلسلة borax، لكن القاف الزائدة ليست في هيكل العضو ولا مروحته؛ حفظ الاتجاه ولم يصدر حكم جذري.",
    896: "حقل أصل sugar يكرر خبر borax حرفيا؛ عزل التعارض ولم يورث معنى المتجانس السابق.",
    904: "قصر تفكيك `گرز` + `ـه` على الحس الذي يفسره المصدر، ولم يورث club أو penis أو serpent حكما واحدا.",
    925: "عزل حس name of a man؛ الحكم الاستكشافي للحس العام beardless youth أو servant boy وحده.",
    938: "حفظ خبر الاسم الإيراني وقروضه المسماة في الأرمنية واليونانية والجورجية بلا تعميم معجمي.",
    940: "حقل الاشتقاق فارغ؛ لم يعوض أصل اسم الصبار من المعرفة العامة.",
    942: "المصدر يسمي العربية `دشنج` قرضا إيرانيا لمعنى dagger، لكن الجيم الزائدة خارج هيكل `دشن` وشاهدا `دشن` العربيان لمعنى الجديد؛ حفظ الخبر بلا تسوية.",
}


@dataclass(frozen=True)
class SelectedRow:
    row: H.SweepRow

    @property
    def key(self) -> str:
        return f"S{self.row.rank:05d}"

    @property
    def heading(self) -> str:
        return f"WO-B-R37-SOUND-{self.row.rank:05d}"


Review = R36.Review
R = R36.R

# سجل قراءة يدوي. لا يشتق الحكم من best ولا من وزن المروحة.
REVIEWS = {
    867: R("جلجل", "LAW-GAP", "جسر المعنى: شدّة الصوت في `جلجل` تلائم نداء الطائر، لكن چ↔ج غير مسمى مرتين.", "مدار الصوت المباشر مقروء، وشاهد الجلجلة واحد فقط؛ بقي القانون مانعا."),
    868: R("جبر", "LAW-GAP", "نص الحدث المجمد لـ`جبر`: إصلاح الكسر أو الإغناء؛ لا يسمي البريد أو الساعي، ومعه چ↔ج غير مسمى.", "فصلت مهنة الساعي عن الجبر، وحفظت الأصل التركي خارج حكم العربية."),
    869: R("دركل", "COMPOUND-BOUNDARY", "جسر المعنى: carpenter مصرح بتكوينه من `درود` timber و`ـگر` لاحقة الفاعل.", "قُرئ المكونان استقلالا؛ لم تقارن الصورة الرباعية بجذر عربي واحد."),
    870: R("بذبن", "LAW-GAP", "نص الحدث المجمد لـ`بذبن`: التفرق والنثر؛ لا يسمي جابي الخراج، وژ↔ذ غير مسمى.", "ذكر `باژ` وحده لا يفكك `ـبان`، فبقي الصوت والمعنى غير مغلقين."),
    871: R("دشت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دشت`: محاكم الحروف بلا معنى first income أو handsel.", "فصلت دخل البداية عن plain الفارسي المشهود في العربية وعن حس wicked المتجانس."),
    872: R("دشت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دشت`: محاكم الحروف بلا معنى evil أو wicked.", "لم يورث المتجانس السابق ولا شاهد plain، وبقي الأصل الإيراني مستقلا."),
    873: R("حقن", "COMPOUND-BOUNDARY", "جسر المعنى: scrambled egg مصرح برده إلى `خایه` egg و`ـگین` -ful في الصورة الأقدم.", "قُرئ المكونان وحدهما؛ لم يحول تجمع البيض في الطبخ إلى حكم `حقن`."),
    875: R("قفتن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`قفتن`: ارتفاع مع صلابة؛ لا يسمي الضرب أو الكسر.", "المعنى الإيراني للمطرقة مستقل، وشاهد القفنان لا يبني مدار beat."),
    876: R("زن", "TOOL-GAP", "جسر المعنى: damage أو loss حاضر في الفرع، لكن /ziyān/ يحمل /y/ أسقطها الهيكل.", "أوقف الصامت الساقط المقارنة قبل ربط الضرر بحدث `زن`."),
    877: R("بحثن", "LAW-GAP", "جسر المعنى: loss أو defeat مقروء، لكن ت↔ث غير مسمى في المسار المنتخب.", "تراخي `بحثن` لا يساوي الخسارة، وفجوة الصوت كافية للوقف."),
    878: R("خشت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خشت`: تجمع دقاق خشنة؛ لا يسمي adobe أو brick مباشرة.", "تماسك الطين وصف مادة محتمل لا تطابق معجمي، والمصدر لا يسمي العربية."),
    879: R("شحن", "TOOL-GAP", "جسر المعنى: teahouse مفككة إلى `چای` tea و`خانه` house، لكن /y/ في المكون الأول ساقطة.", "قُرئ المكونان ثم أوقف عطب `چای` حكم الصورة المجموعة."),
    880: R("همن", "TOOL-GAP", "جسر المعنى: blessed أو sacred حاضر، لكن /homāyun/ يحمل /y/ أسقطها الهيكل.", "لم يعوض الصامت، ولم يحول التركيب التاريخي hu + māyā إلى تفكيك حديث."),
    881: R("غرس", "TOOL-GAP", "جسر المعنى: inclination أو desire مفككة إلى `گرا` و`ـیش`، لكن /y/ في اللاحقة ساقطة.", "قُرئ المكونان ووقف الحكم عند عطب اللاحقة، قبل فجوة گ↔غ أيضا."),
    882: R("غو", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`غو`: الانجذاب مع فساد؛ لا يسمي cry أو clamor أو thunder.", "الغوغاء شاهد قريب من الضجيج لكنه منفرد ولا يكمل الحدث والمعنى بشاهدين."),
    883: R("كستن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كستن`: نقص بالدق أو القشر؛ لا يسمي rotate أو turn.", "الحركة الدائرية لا تساوي النقص، ووسم القرض الصوتي لا يثبت اتجاها."),
    884: R("اس", "LAW-GAP", "جسر المعنى: millstone حجر، لكن آ↔ا غير مسمى، و`اس` لا يسمي حجر الرحى.", "حفظت مقارنة stone الهندوأوروبية حاشية ولم تستبدل صف الصوت."),
    885: R("خور", "TOOL-GAP", "جسر المعنى: sun حاضر، لكن /xwar/ يحمل /w/ أسقطها الهيكل.", "أوقف الصامت الساقط البنية الجوفاء المصطنعة قبل الحكم."),
    886: R("در", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`در`: جريان ووفرة؛ لا يسمي courtly.", "رفضت التحليل السطحي court + suffix بعد الخبر الموروث."),
    887: R("جلد", "NUCLEUS-TRACE", "جسر المعنى: nimble أو agile قدرة القوي الجَلْد على العمل والسير، وهو حاضر في الشاهدين.", "مدار 1: الخفة أثر لقوة البدن وتماسكه؛ اكتمل الصوت والحدث وشاهدا القوة والسير."),
    888: R("بمل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بمل`: امتساك أو تجمع؛ لا يسمي sick person.", "فصل الاسم عن الصفة المتجانسة، ولم يحول vomit في الأصل إلى معنى عربي."),
    889: R("بمل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بمل`: امتساك أو تجمع؛ لا يسمي sick أو ill.", "فصلت الصفة عن اسم المريض السابق؛ لا وراثة بين المدخلتين."),
    890: R("لس", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`لس`: امتداد دقيق أو نفاذ؛ لا يسمي lazy.", "خبر slow الهندوأوروبي حاشية، ولم يجد شاهدين عربيين لمعنى الكسل."),
    891: R("تغ", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تغ`: محكمتا الحرفين؛ لا يسمي blade أو razor أو sword.", "حدة النصل وصف وظيفي لا معنى المادة العربية، والأصل الإيراني محتمل."),
    892: R("دستر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دستر`: نفاذ بدفع؛ لا يسمي command أو method أو rule.", "فصلت الدستور العربي المعرب من دعويي الأصل البديلتين في المدخلة."),
    893: R("بشش", "COMPOUND-BOUNDARY", "جسر المعنى: cover أو coating مفككة مباشرة إلى `پوش` و`ـش` لاحقة اسم الحدث.", "قُرئ الجذع واللاحقة استقلالا؛ لم تقارن الصورة المجموعة بجذر واحد."),
    894: R("كش", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`كش`: قطع أو جذب؛ لا يسمي corner أو angle.", "تشبيه الزاوية بطرف الأذن في المصدر لا يساوي حدث الكش."),
    895: R("بور", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بور`: بوار الجدوى؛ لا يسمي borax.", "حفظت سلسلة `بورق` المنقولة إلى العربية، لكن القاف خارج هيكل العضو ومروحته."),
    896: R("بور", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بور`: بوار الجدوى؛ لا يسمي sugar.", "عزلت معنى السكر عن خبر borax المكرر في حقل الأصل."),
    897: R("بنب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بنب`: محاكم الحروف بلا معنى cotton.", "الصورة الوسطى الموروثة لا تسمي مقابلا عربيا ولا مدار قطن."),
    898: R("بها", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بها`: الخلو والفراغ الظاهري؛ لا يسمي price أو value.", "البهاء والحسن قد يرفعان القيمة لكنهما لا يساويان السعر، فبقي مفتوحا."),
    899: R("جمر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جمر`: تجمع الشيء بحرارة أو كثافة؛ لا يسمي cattle fold.", "اجتماع الماشية داخل الحظيرة سياق مكاني لا معنى الحظيرة نفسها."),
    900: R("برز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`برز`: الظهور والخلوص؛ لا يسمي sown field أو seed.", "الزرع يبرز من الأرض نتيجة لاحقة لا معنى الحقل أو البذر."),
    901: R("برز", "NUCLEUS-TRACE", "جسر المعنى: high أو tall بروز وظهور فوق المحيط، والشاهدان يسميان الفوق والجلالة والظهور.", "مدار 1: العلو نتيجة البروز القوي؛ اكتملت الهوية والحدث وشاهدا البروز."),
    902: R("خذعن", "LAW-GAP", "نص الحدث المجمد لـ`خذعن`: محاكم الحروف بلا معنى kettle، ومعه ژ↔ذ وغ↔ع غير مسميين.", "حفظ القرض التركي ولم يستعمله لتوقيع صفين صوتيين."),
    903: R("غرز", "LAW-GAP", "جسر المعنى: mace آلة تضرب أو تغرز، لكن گ↔غ غير مسمى.", "المعنى الأداتي محتمل لا مباشر، وفجوة الصوت تمنع أي أثر."),
    904: R("غرز", "COMPOUND-BOUNDARY", "جسر المعنى: الحس المفسر في المصدر مفكك إلى `گرز` mace و`ـه` لاحقة.", "قُرئ المكونان وفصلت الحواس المتجانسة؛ لم تورث الصورة حكم `غرز`."),
    906: R("وشم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`وشم`: أثر ثابت في الظاهر؛ لا يسمي quail.", "هوية الرسم لا تنقل معنى الوشم إلى اسم الطائر، والمصدر فارسي أوسط فقط."),
    907: R("جش", "LAW-GAP", "نص النواة المجمدة لـ`جش`: انكشاف أو خشونة؛ لا يسمي lunch، ومعه چ↔ج غير مسمى.", "خبر الأرمنية akin لا يمد طريقا عربيا ولا يصلح صف الصوت."),
    908: R("جست", "LAW-GAP", "جسر المعنى: morning meal أو midday مقروء، لكن چ↔ج غير مسمى.", "فصلت اسم الزمن من وجبة `چاش` السابقة، وحفظت القرض الأرمني حاشية."),
    909: R("سنن", "NUCLEUS-TRACE", "جسر المعنى: kind أو manner يطابق `السَنَن` الطريقة والوجه في الشاهدين.", "مدار مباشر: الهيئة والطريقة معنى واحد؛ اكتمل التضعيف والحدث والشاهدان."),
    910: R("سن", "NUCLEUS-TRACE", "جسر المعنى: whetstone هو `المِسَن` الحجر الذي يسن عليه السكين في الشاهدين.", "مدار مباشر: الأداة وحَدُّ السن من حدث النفاذ مع الحدة؛ اكتملت الأرجل."),
    911: R("تب", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`تب`: الضعف أو ذهاب الغلظ؛ لا يسمي fever.", "الحمى تورث ضعفا لكنها سبب لا معنى التباب؛ بقي المدار لينا."),
    912: R("تبت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تبت`: صندوق للحفظ والثبات؛ لا يسمي heat أو warmth.", "الأصل يرجع الحرارة إلى tep، لكن المروحة لا تقدم مقابلا عربيا مباشرا."),
    913: R("طرمش", "LAW-GAP", "نص الحدث المجمد لـ`طرمش`: محاكم الحروف بلا معنى interpreter، ومعه چ↔ش غير مسمى.", "القرض التركي المجمل لا يفكك الكلمة ولا يسمي العربية."),
    914: R("شكر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شكر`: امتلاء بطيب وظهوره؛ لا يسمي hunt أو prey.", "المطاردة الإيرانية لا تساوي الثناء أو الامتلاء، ولا cognates غير إيرانية للمصدر."),
    915: R("ذذخ", "LAW-GAP", "جسر المعنى: hell حاضر، لكن د↔ذ وز↔ذ غير مسميين.", "قرأ المركب الإيراني التاريخي bad existence ولم يحوله إلى تفكيك فارسي حديث."),
    916: R("ورش", "TOOL-GAP", "جسر المعنى: edit أو revision حاضر، لكن /wīrāyiš/ يحمل /y/ أسقطها الهيكل.", "أوقف الصامت الساقط أي ربط بالورش أو التعديل."),
    917: R("كين", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كين`: محاكم الحروف في بنية جوفاء؛ لا يسمي hatred أو revenge.", "الأصل الإيراني للعقوبة مستقل، ولم يجد مدار عربي محكم."),
    920: R("غز", "TOOL-GAP", "جسر المعنى: ox-goad عصا للسوق، لكن /gavāza/ يحمل /v/ أسقطها الهيكل.", "أوقف العطب المقارنة قبل فجوة گ↔غ وقبل تشبيه الوخز بالغزو."),
    921: R("غزن", "TOOL-GAP", "جسر المعنى: ox-goad حاضر، لكن /gāvzane/ يحمل /v/ أسقطها الهيكل.", "فصلت الصورة عن المتجانس السابق وأوقفتها عند الصامت الساقط."),
    923: R("دجم", "LAW-GAP", "جسر المعنى: sad أو gloomy يطابق `دَجِم` حزن في شاهدين، لكن ژ↔ج غير مسمى.", "المعنى المباشر محفوظ، وفجوة الصوت وحدها منعت أثر النواة."),
    924: R("دبر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دبر`: الامتداد إلى الخلف أو التدبير؛ لا يسمي scribe أو teacher.", "كون الكاتب مدبرا للنص وظيفة عامة لا معنى المهنة، والأصل مستقل."),
    925: R("ردك", "NUCLEUS-TRACE", "جسر المعنى: beardless youth يطابق غلام `رودك` في عنفوان شبابه في شاهدين.", "مدار مباشر: الفتى الناعم الشاب هو الحس نفسه؛ اكتمل الصوت والحدث والشاهدان."),
    926: R("خور", "TOOL-GAP", "جسر المعنى: east موضع طلوع الشمس، لكن /xāvar/ يحمل /v/ أسقطها الهيكل.", "أوقف الصامت قبل ربط جهة الشرق بالشمس أو بالبنية الجوفاء."),
    927: R("بكر", "TOOL-GAP", "جسر المعنى: face أو form أو figure حاضر، لكن /paykar/ يحمل /y/ أسقطها الهيكل.", "لم يعوض الصامت، وحفظ الأصل الإيراني للصورة مستقلا عن `بكر`."),
    928: R("تك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تك`: محكمتا الحرفين؛ لا يسمي attack أو raid.", "الاندفاع في الهجوم محتمل حركيا لكنه لا يساوي التكة أو الهزال العربي."),
    929: R("دست", "COMPOUND-BOUNDARY", "جسر المعنى: handle أو group مصرح بتكوينه من `دست` hand و`ـه` لاحقة.", "قُرئ المكونان، وفصل handle عن group ولم تقارن الصورة المجموعة جذرا واحدا."),
    930: R("دستر", "TOOL-GAP", "جسر المعنى: assistant أو helper حاضر، لكن /dastyār/ يحمل /y/ أسقطها الهيكل.", "أوقف العطب التحليل التاريخي إلى حامل اليد قبل أي حكم."),
    931: R("جسن", "LAW-GAP", "جسر المعنى: taste أو seasoning حاضر، لكن چ↔ج غير مسمى.", "خبر الصلة بـ`چشیدن` لا يوقع الصف ولا يساوي مادة `جسن`."),
    933: R("شب", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`شب`: تجمع مع تركز؛ لا يسمي nightshirt.", "رفضت التحليل السطحي night + suffix وحفظت معنى undershirt الموروث."),
    934: R("باز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`باز`: النفاذ من مضيق؛ لا يسمي beet أو beetroot.", "القرض الأرمني المسمى يمنع بناء إرث من تشابه الرسم."),
    935: R("زال", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زال`: الانزلاق عن مستو؛ لا يسمي leech.", "التصاق العلقة ثم زوالها وصف عارض لا معنى الاسم الإيراني."),
    936: R("دور", "TOOL-GAP", "جسر المعنى: referee أو judge حاضر، لكن /dāvar/ يحمل /v/ أسقطها الهيكل.", "أوقف العطب التحليل السطحي justice + suffix، ولم يستبدل `دور` به."),
    937: R("ارش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ارش`: محاكم الحروف بلا معنى tear.", "الأرش تعويض الجرح لا الدمع، ولم يصدر معنى من التطابق الصوتي وحده."),
    938: R("ارش", "OUT-OF-SCOPE", "جسر المعنى: Araks أو Aras اسم نهر بعينه، لا معنى معجميا عاما.", "عزل الاسم وقروضه التاريخية؛ لم يورثه حس tear المتجانس."),
    939: R("زرك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زرك`: نفاذ بدقة مع إمساك؛ لا يسمي leech.", "الإمساك بالجلد من فعل الحيوان لا معنى اسمه، وشاهد العربية منفرد."),
    940: R("سجر", "TOOL-GAP", "جسر المعنى: saguaro اسم نبات، لكن الواو الوسطى المنطوقة أسقطها الهيكل.", "أوقف العطب تشبيه الصبار بالشجر، وحقل الأصل فارغ."),
    941: R("هنكم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`هنكم`: رخاوة متجمعة في الباطن؛ لا يسمي moment أو time أو season.", "الشاهد العربي اسم جزيرة، والتحليل السطحي step غير مؤهل."),
    942: R("دشن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دشن`: محاكم الحروف؛ لا يسمي dagger أو sword.", "حفظ قرض `دشنج` العربي المسمى، لكن الجيم خارج الهيكل وشاهدا `دشن` لمعنى الجديد."),
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
            raise AssertionError(f"تغير عداد نسخة v17 في {name}")
        if len(data.get("both") or []) != expected_both or len(data.get("sound_only") or []) != expected_sound:
            raise AssertionError(f"تغير طول قوائم نسخة v17 في {name}")
        total_both += expected_both
        total_sound += expected_sound
    if total_both != 14535 or total_sound != 106805:
        raise AssertionError("تغير مجموع أحواض v17")


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
            if row.rank > 866 and len(fresh) < 70:
                internal_skips.append(row.rank)
            continue
        seen.add(key)
        if row.rank <= 866:
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
        "درود": {587, 588, 589}, "ـگر": {10504}, "خایه": {182},
        "ـگین": {14793}, "چای": {496}, "خانه": {262}, "گرا": set(),
        "ـیش": set(), "پوش": set(), "ـش": {10302, 10303}, "گرز": {4443},
        "ـه": {7113, 7114, 7115}, "دست": {1138, 1139},
    }
    fan_counts = {
        "درود": 18, "ـگر": 80, "خایه": 0, "ـگین": 40, "چای": 0,
        "خانه": 30, "گرا": 80, "ـیش": 48, "پوش": 60, "ـش": 0,
        "گرز": 24, "ـه": 0, "دست": 27,
    }
    for word, expected in expected_indices.items():
        actual = {index for index, _entry in grouped.get(word, [])}
        if actual != expected:
            raise AssertionError(f"تغير جرد مكون {word}: {sorted(actual)}")
        fan = tuple(H.FAN.rank(word, H.FAN.fan(word, "persian"), "persian"))
        if len(fan) != fan_counts[word]:
            raise AssertionError(f"تغيرت مروحة المكون {word}: {len(fan)}")
    expected_raw = {
        "درود": {629, 630, 631}, "ـگر": {12956}, "خایه": {187},
        "ـگین": {17717}, "چای": {533}, "خانه": {274}, "گرا": set(),
        "ـیش": set(), "پوش": {10688}, "ـش": {12673, 12674}, "گرز": {4949},
        "ـه": {8351, 8352, 8353, 8354}, "دست": {1210, 1211},
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
    etymology = raw["etymology"]
    if rank in {879, 881, 893}:
        decomposition = P25.direct_from_plus(etymology)
        if not decomposition:
            raise AssertionError(f"غاب تفكيك From X + Y للرتبة {rank}")
        joined = H.clean(" + ".join(decomposition))
    else:
        joined = H.clean(etymology)
        checks = {
            869: ("Equivalent to", "درود", "ـگر"),
            873: ("Equivalent to", "خایه", "ـگین"),
            904: ("From گرز", "ـه"),
            929: ("equivalent to دست", "ـه"),
        }
        if any(H.clean(token) not in joined for token in checks[rank]):
            raise AssertionError(f"تغير التصريح المباشر المحكم للرتبة {rank}")
    for component in EXPECTED_COMPONENTS[rank]:
        if H.clean(component) not in joined:
            raise AssertionError(f"غاب مكون {component} من الرتبة {rank}")
    lines = [
        f"- تفكيك Kaikki الحصري المباشر أو المحكم من السطر الخام {raw['line']}: «{H.clip(etymology, 420)}».",
        f"- قراءة المكونات المستقلة: {COMPONENT_READINGS[rank]}",
        "- الخطوة صفر: قبل التفكيك النهائي المصرح به لم تقارن الصورة وحدة جذرية؛ قُرئ كل مكون مسمى وحده.",
    ]
    if rank in TOOL_GAPS:
        lines.extend([
            f"- عطب الهيكل: {TOOL_GAPS[rank]}",
            "- بعد قراءة المكونات أوقف TOOL-GAP حكم الصورة المجموعة؛ لا حكم من هيكل ناقص.",
        ])
    return lines


BASE_MAKE_CARD = R36.make_card


def make_card(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit) -> str:
    card = BASE_MAKE_CARD(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit)
    card = card.replace("الجولة 36،", "الجولة 37،")
    rank = item.row.rank
    if rank in SOURCE_NOTES and "ملاحظة المصدر الخاصة" not in card:
        markers = ("- عطب الهيكل:", "- حد التحليل غير المؤهل:", "- الخطوة صفر:")
        marker = next((value for value in markers if value in card), None)
        if not marker:
            raise AssertionError(f"تعذر موضع ملاحظة المصدر للرتبة {rank}")
        card = card.replace(marker, f"- ملاحظة المصدر الخاصة: {SOURCE_NOTES[rank]}\n{marker}", 1)
    if rank in REJECTED_ANALYSES and "حد التحليل غير المؤهل" not in card:
        marker = "- عطب الهيكل:" if "- عطب الهيكل:" in card else "- الخطوة صفر:"
        card = card.replace(marker, f"- حد التحليل غير المؤهل: {REJECTED_ANALYSES[rank]}\n{marker}", 1)
    return card


def validate_decisions(selected, raw_entries, decisions, ranked_by_rank, sense_map) -> None:
    if set(REVIEWS) != set(SOUND_RANKS):
        raise AssertionError("جدول المدار اليدوي لا يغطي الرتب السبعين")
    parsed = {item.row.rank for item in selected if P25.direct_from_plus(raw_entries[item.row.rank]["etymology"])}
    if parsed != PARSER_FROM_PLUS:
        raise AssertionError(f"تغيرت أسطر From X + Y التي يلتقطها المحلل: {sorted(parsed)}")
    expected_verdicts = {
        "COMPOUND-BOUNDARY": 5,
        "LAW-GAP": 13,
        "NUCLEUS-TRACE": 5,
        "OPEN-CANDIDATE": 33,
        "OUT-OF-SCOPE": 1,
        "TOOL-GAP": 13,
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
        if not REVIEWS[row.rank].meaning_path.startswith(("جسر المعنى:", "نص الحدث المجمد", "نص النواة المجمدة")):
            raise AssertionError(f"طريق المعنى غير مسمى في الرتبة {row.rank}")


def validate_text(selected, texts, prior_pairs) -> None:
    if len(selected) != 70 or BATCH_SIZES != (35, 35):
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = re.findall(r"^### (WO-B-R37-SOUND-\d{5}):", joined, re.MULTILINE)
    if headings != [item.heading for item in selected]:
        raise AssertionError("معرفات الجولة 37 لا تطابق النافذة")
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
    previous = 866
    for number, batch in enumerate(batches, 1):
        lo = 0 if number == 1 else 35
        hi = lo + len(batch)
        counts = Counter(decision.verdict for decision in decisions[lo:hi])
        distribution = "؛ ".join(f"{key}={counts[key]}" for key in sorted(counts))
        batch_skips = [rank for rank in stats["skipped"] if previous < rank <= batch[-1].row.rank]
        skipped = ", ".join(map(str, batch_skips)) or "0"
        lines.extend([
            f"## الجولة السابعة والثلاثون، دفعة sound_only رقم {number}", "",
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
        "## حصيلة الجولة السابعة والثلاثين", "",
        f"- حمل `persian.md` مرة واحدة؛ أزواج WO-B المقروءة={stats['pair_count']}؛ المتجاوز داخل النافذة={', '.join(map(str, stats['skipped']))}.",
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- نطاق الصوت الجديد: الرتب 867-942 بعد WO-B-R36-SOUND-00866، مع تجاوز المواضع المقروءة 874 و905 و918 و919 و922 و932 فقط.",
        f"- الآثار النووية الاستكشافية الجديدة: {', '.join(traces)}؛ لم تفعل طبقة البرهان ولم تنشر أرقاما.",
        "- التفكيك المباشر أو المحكم المؤهل: S00869، S00873، S00879، S00881، S00893، S00904، S00929؛ قرئت المكونات مستقلة، ووقفت S00879 وS00881 عند عطب صوتي.",
        "- التحليلات غير المؤهلة: S00886، S00930، S00933، S00936، S00941؛ حفظت تاريخية المصدر أو سطحيته ولم تحول إلى تفكيك نهائي.",
        "- أعطاب الأداة: S00876، S00879، S00880، S00881، S00885، S00916، S00920، S00921، S00926، S00927، S00930، S00936، S00940؛ لم تعوض الصوامت المنطوقة الساقطة.",
        "- فجوات القانون: S00867، S00868، S00870، S00877، S00884، S00902، S00903، S00907، S00908، S00913، S00915، S00923، S00931.",
        "- اسم النهر المعزول: S00938؛ بقي في التغطية ولم يحول إلى معنى جذري عام.",
        "- ملاحظات الاتجاه: حفظت `بورق` و`دشنج` العربيين في مساري القرض الإيراني المسمّيين، لكن صامتهما الزائد خارج هيكل العضوين ومروحتيهما، فلم يصدر حكم جذري.",
        "- أحواض `nucleus-sweep-*.json` التسعة الحالية v17 قرئت كاملة من القرص؛ both=14535 وsound_only=106805؛ ثبت الحجم وSHA-256 والعدادات لكل ملف.",
        f"- أكبر بطاقة: {max_size} بايت، {max_item.heading}؛ كل البطاقات دون 5KB.",
        "- لم تفعل طبقة البرهان؛ مر حارس نقاء الشحنة وختم CLEAN؛ لم يقع ship ولم يستعمل git.",
        "", f"<!-- {MARKER}:END -->", "", DONE_LINE,
    ])
    return "\n".join(lines)


def validate_existing(reading_text: str, report_text: str) -> None:
    match = re.search(rf"<!-- {re.escape(MARKER)}:START -->(.*?)<!-- {re.escape(MARKER)}:END -->", reading_text, re.DOTALL)
    if not match:
        raise AssertionError("محضر الجولة موجود وبطاقاتها غائبة")
    headings = re.findall(r"^### (WO-B-R37-SOUND-\d{5}):", match.group(1), re.MULTILINE)
    expected = [f"WO-B-R37-SOUND-{rank:05d}" for rank in SOUND_RANKS]
    if headings != expected:
        raise AssertionError("مقطع الجولة 37 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(DONE_LINE):
        raise AssertionError("سطر DONE37 ليس خاتمة التقرير")


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
        print("ROUND37 ALREADY PRESENT AND VALID")
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
        unicodedata.normalize(
            "NFC",
            R28.fit_card(item, entries[item.row.rank], raw_entries[item.row.rank], decision, ranked_by_rank[item.row.rank], sense_map),
        )
        for item, decision in zip(selected, decisions)
    ]
    validate_text(selected, texts, prior_pairs)
    sizes = [len(card.encode("utf-8")) for card in texts]

    reading_append = (
        f"\n\n<!-- {MARKER}:START -->\n\n"
        "## الجولة السابعة والثلاثون: متابعة حوض sound_only (2026-08-27)\n\n"
        "- النطاق: 70 عضوا طازجا بعد WO-B-R36-SOUND-00866؛ من الرتبة 867 إلى 942 مع تجاوز 874 و905 و918 و919 و922 و932 لأنها مقروءة؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ طريق المعنى مسمى، والمدار اليدوي حاسم، والأصداء مفصولة عن الأثر المحكم.\n"
        "- لقطة الأحواض: قرئت ملفات nucleus-sweep-*.json التسعة الحالية v17 من القرص؛ ثبتت بصماتها وعداداتها قبل الانتخاب.\n\n"
        + "\n".join(texts[:35])
        + "\n## الدفعة الثانية: متابعة sound_only بعد الرتبة 902\n\n"
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
    print("ROUND37 READY")
    print("NUCLEUS_V17_FILES", len(NUCLEUS_SNAPSHOT), "SHA256_AND_COUNTS_OK")
    print("NUCLEUS_V17_TOTALS", "BOTH=14535", "SOUND_ONLY=106805")
    print("SKIPPED", ",".join(map(str, stats["skipped"])))
    print("BATCHES", *BATCH_SIZES, "SELECTED", len(selected))
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("TRACES", " ".join(f"S{rank:05d}" for rank in sorted(rank for rank, review in REVIEWS.items() if review.verdict == "NUCLEUS-TRACE")))
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
    print("ROUND37 WRITTEN")
    print(DONE_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
