# -*- coding: utf-8 -*-
"""المسار B، الجولة 38: متابعة إنقاذ حوض sound_only في دفعتين من 35 بطاقة."""

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

import harvest_persian_round37 as R37  # noqa: E402

R36 = R37.R36
R35 = R37.R35
R34 = R37.R34
R32 = R37.R32
R31 = R37.R31
R29 = R37.R29
R28 = R37.R28
H = R37.H
P = R37.P
P25 = R37.P25
READING = R37.READING
REPORT = R37.REPORT
SWEEP = R37.SWEEP
NUCLEUS_DIR = R37.NUCLEUS_DIR
LEXICON = R37.LEXICON
RAW_LEXICON = R37.RAW_LEXICON
MARKER = "LANE-B-PERSIAN-ROUND38-2026-08-27"
CARD_LIMIT = 5120
SOUND_RANKS = (
    944, 945, 946, 947, 948, 949, 950, 951, 952, 953, 954, 955, 957,
    958, 959, 960, 961, 962, 963, 964, 965, 966, 967, 968, 970, 972,
    973, 974, 975, 976, 978, 979, 980, 981, 983, 984, 985, 986, 987,
    988, 989, 990, 991, 992, 993, 994, 995, 996, 997, 998, 999, 1000,
    1001, 1002, 1003, 1004, 1005, 1007, 1008, 1009, 1010, 1011, 1012,
    1013, 1014, 1015, 1016, 1019, 1022, 1023,
)
BATCH_SIZES = (35, 35)
DONE_LINE = "LANE-B DONE38 70 WO-B-R38-SOUND-01023"
EXPECTED_SKIPS = (943, 956, 969, 971, 977, 982, 1006, 1017, 1018, 1020, 1021)

# النسخة الثامنة عشرة المقروءة من القرص.
NUCLEUS_SNAPSHOT = {
    "nucleus-sweep-ancient_greek.json": (7950313, "41db2b57a42a9b23a7a998e719c4c4ec6535609edde29ef3754af903dfb49bfe", 2312, 16782),
    "nucleus-sweep-english_middle.json": (3415626, "63f8b3cba8f8bfa58035ae26efaec138fa002f68610ee5d1a0e697bac43797d2", 1414, 7991),
    "nucleus-sweep-english_old.json": (1293699, "0e4ac0e76706c510b7a8c814d6168c360a6ca73487dbe0d87c453d0163d1851b", 474, 3413),
    "nucleus-sweep-gothic.json": (1419643, "320ba7d92d203bd09640d53ba62226d4418f098c1579630cb88bdd1a242a1401", 335, 3083),
    "nucleus-sweep-latin.json": (18828082, "8481977d36a04142a640fc852426ea2510227e653528fd5193522064bf6283a3", 6583, 39470),
    "nucleus-sweep-old_irish.json": (952662, "34957efec07c8e05673898db0e2463a6aff4090453c68c04b58d9b10c47852fb", 278, 2740),
    "nucleus-sweep-old_norse.json": (1380108, "49b89904d90160b5434aabe483a6dc524dc85505054d84ac0311deac1a43a8e3", 476, 3750),
    "nucleus-sweep-persian.json": (5447611, "f3227154322a5626b8ea13281199abb949a6702b319aa6d3b857370aa60f3d2a", 1437, 13503),
    "nucleus-sweep-welsh.json": (5775473, "c52b3631b4a66f8c3171439891e47e30aabcfe2bb160e46193617df9dc1e1163", 1187, 16086),
}

EXPECTED_ENTRY_INDEX = dict(zip(SOUND_RANKS, (
    4564, 4573, 4581, 4593, 4597, 4601, 4602, 4603, 4609, 4610, 4611,
    4613, 4616, 4621, 4622, 4629, 4641, 4642, 4647, 4649, 4650, 4652,
    4658, 4663, 4674, 4678, 4687, 4703, 4704, 4727, 4742, 4752, 4753,
    4755, 4783, 4787, 4809, 4819, 4822, 4823, 4827, 4828, 4835, 4851,
    4882, 4883, 4894, 4895, 4896, 4897, 4905, 4914, 4920, 4939, 0,
    4999, 5025, 5046, 5048, 5049, 5075, 5076, 5092, 5093, 5119, 5126,
    5134, 5165, 5185, 5192,
)))
EXPECTED_RAW_LINE = dict(zip(SOUND_RANKS, (
    5075, 5086, 5095, 5108, 5112, 5117, 5119, 5120, 5126, 5127, 5128,
    5130, 5133, 5138, 5139, 5146, 5158, 5159, 5164, 5166, 5167, 5169,
    5176, 5181, 5194, 5198, 5209, 5227, 5228, 5251, 5266, 5276, 5277,
    5279, 5308, 5312, 5338, 5359, 5382, 5383, 5387, 5390, 5404, 5513,
    5599, 5603, 5614, 5615, 5616, 5617, 5626, 5635, 5645, 5672, 5741,
    5779, 5807, 5832, 5834, 5835, 5872, 5873, 5893, 5898, 5933, 5940,
    5949, 5988, 6013, 6035,
)))

PARSER_FROM_PLUS = {957, 963, 967, 973, 986, 987, 989, 1022}
EXACT_DECOMPOSITIONS = {957, 961, 962, 967, 973, 986, 987, 989, 993, 1011, 1022}
EXPECTED_COMPONENTS = {
    957: ("هفت", "ده"),
    961: ("چون", "این"),
    962: ("چون", "این"),
    967: ("پر", "کار"),
    973: ("ژیر", "ـش"),
    986: ("ژرف", "ـی"),
    987: ("پریش", "ـان"),
    989: ("وب", "ـگاه"),
    993: ("کار", "واژه"),
    1011: ("گفتن", "ـار"),
    1022: ("شکار", "ـچی"),
}
COMPONENT_READINGS = {
    957: "`هفت`: entry[1404] والخام 1485 لمعنى seven، ومروحتها 12: OPEN-CANDIDATE. `ده`: اختيرت entry[1045] والخام 1110 لمعنى ten بعد قراءة متجانساتها، ومروحتها 60: OPEN-CANDIDATE.",
    961: "`چون`: اختيرت entry[1917] والخام 2016 لمعنى like بعد قراءة مدخلتي الرسم، ومروحتها 30: LAW-GAP. `این`: entry[202] والخام 209 لمعنى this، ومروحتها 20: OPEN-CANDIDATE.",
    962: "مرجع المكونين في S00961: `چون` بمعنى like و`این` بمعنى this؛ قرئت المدخلات والمروحتان نفسيهما ولم تورثا حكمهما للصورة المجموعة.",
    967: "`پر`: اختيرت entry[317] والخام 334 لمعنى full بعد فصل feather، ومروحتها 40: OPEN-CANDIDATE. `کار`: entry[797] والخام 847 لمعنى work أو deed، ومروحتها 40: OPEN-CANDIDATE.",
    973: "`ژیر`: غائبة من branch-lexicons والخام مستقلة، ومروحتها 60: FORM-LINK. `ـش`: اختيرت entry[10303] والخام 12674 لاحقة اسم الحدث، ومروحتها صفر: MORPHOLOGY-GAP.",
    986: "`ژرف`: entry[2050] والخام 2153 لمعنى deep، ومروحتها 12: LAW-GAP. `ـی`: اختيرت entry[6330] والخام 7422 لصنع الاسم المجرد، ومروحتها صفر: MORPHOLOGY-GAP.",
    987: "`پریش`: entry[10459] والخام 12858 للجذر الدال على scattered أو disheveled، ومروحتها 12: OPEN-CANDIDATE. `ـان`: اختيرت entry[10305] والخام 12676 لاحقة صفة، ومروحتها 20: MORPHOLOGY-GAP.",
    989: "`وب`: اختيرت entry[4992] والخام 5770 لمعنى World Wide Web بعد فصل اسم النسبة، ومروحتها 18: OPEN-CANDIDATE. `ـگاه`: entry[7462] والخام 8752 لاحقة المكان أو الزمان، ومروحتها 72: MORPHOLOGY-GAP.",
    993: "`کار`: entry[797] والخام 847 لمعنى work أو deed، ومروحتها 40: OPEN-CANDIDATE. `واژه`: entry[999] والخام 1062 لمعنى word أو term، ومروحتها 57: OPEN-CANDIDATE.",
    1011: "`گفتن`: entry[1037] والخام 1102 لمعنى say أو speak، ومروحتها 24: OPEN-CANDIDATE. `ـار`: entry[10308] والخام 12680 لاحقة اسم الفاعل أو الاسم المجرد، ومروحتها 40: MORPHOLOGY-GAP.",
    1022: "`شکار`: entry[4476] والخام 4983 لمعنى hunt أو game، ومروحتها 12: OPEN-CANDIDATE. `ـچی`: entry[7517] والخام 8811 لاحقة الفاعل، ومروحتها 42: MORPHOLOGY-GAP.",
}

TOOL_GAPS = {
    948: "الصورة `گوینده` منقوطة /guyande/، لكن الهيكل أسقط /y/ المنطوقة.",
    951: "الصورة `بیور` منقوطة /bēwar/، لكن الهيكل أسقط /w/ المنطوقة.",
    955: "الصورة `بایستن` منقوطة /bāyistan/، لكن الهيكل أسقط /y/ المنطوقة.",
    957: "الصورة `هفده` منقوطة /hefdah/، لكن الهيكل أسقط الهاء النهائية المنطوقة.",
    979: "الصورة `خوردی` منقوطة /xvardi/، لكن الهيكل أسقط /v/ المنطوقة.",
    980: "الصورة `خوراک` منقوطة /xwarāk/، لكن الهيكل أسقط /w/ المنطوقة.",
    985: "الصورة `جویدن` منقوطة /javidan/، لكن الهيكل أسقط /v/ المنطوقة.",
    989: "الصورة `وبگاه` منقوطة /veb-gāh/، لكن الهيكل أسقط الهاء النهائية المنطوقة.",
    993: "الصورة `کارواژه` منقوطة /kārvāže/، لكن الهيكل أسقط /v/ المنطوقة.",
    994: "الصورة `نیام` منقوطة /niyām/، لكن الهيكل أسقط /y/ المنطوقة.",
    1004: "الصورة `خوال` منقوطة /xvāl/، لكن الهيكل أسقط /v/ المنطوقة.",
    1008: "الصورة `پرو` في مدخلة heifer منقوطة /parow/، لكن الهيكل أسقط /w/ النهائية المنطوقة.",
    1009: "الصورة `پرو` في مدخلة trying on منقوطة /prov/، لكن الهيكل أسقط /v/ المنطوقة.",
    1014: "الصورة `پادشاه` منقوطة /pādišāh/، لكن الهيكل أسقط الهاء النهائية المنطوقة.",
}
LAW_GAPS = {974, 975, 976, 990, 995, 996, 997, 998, 999, 1019}
REJECTED_ANALYSES = {
    963: "التحليل إلى `کو` و`جا` موسوم By surface analysis بعد خبر الوراثة الوسطى، فلم يؤهل تفكيكا نهائيا.",
    980: "التحليل إلى `خور` و`ـاک` موسوم By surface analysis بعد الصورة الوسطى الموروثة، ثم أوقفه عطب /w/ أيضا.",
    983: "تفكيك الصورة الوسطى التاريخية إلى جذر الفعل و`-ag` لا يفكك الاسم الفارسي الحديث تفكيكا نهائيا.",
    1005: "المكونان `any` و`-iz` واقعان في طبقة الفارسية الوسطى، لا تفكيكا نهائيا مباشرا للصورة الحديثة.",
}
SOURCE_NOTES = {
    945: "تقول بعض المعاجم العربية إن أصل `درب` غير عربي من غير تسمية المانح؛ لم يستنتج اتجاه فارسي من اتحاد الصورة وحده.",
    947: "يسمي التاج حكاية فارسية ويذكر العلم الكبير في شاهد منفرد؛ لم يحول ذلك إلى اتجاه نقل مكتمل أو أثر موجب.",
    950: "خبر الأصل يرجح الباخترية؛ لم يستبدل ذلك بمقابل عربي ولا بمدار الخزن الموسمي.",
    978: "يسمي الخبر مقابلات سريانية وآرامية وأرمنية وجورجية قروضا إيرانية، لكنه لا يسمي العربية مانحا أو آخذا.",
    988: "المقارنة الهندوأوروبية مع light حاشية أصل؛ لا تمد طريقا إلى معنى عربي مسمى.",
    992: "الشاهد العربي يسمي `جزاف` فارسيا معربا ويطابق الأخذ بالكثرة أو بلا كيل؛ أغلق تماس لا إرث.",
    995: "خبر bread يسمي قرضا تركيا؛ فصل عن متجانسي dirty وpus الإيرانيين.",
    998: "خبر baker يسمي قرضا تركيا ولا يفكك الصورة الحديثة إلى مكونين في السطر الخام.",
    999: "خبر barley يسمي قرضا تركيا؛ لم ينقل اتجاهه إلى العربية ولا يتجاوز فجوة آ↔ا.",
    1002: "حقل الأصل فارغ؛ لم يعوض أصل zipper من المعرفة العامة.",
    1016: "خبر الأصل يسمي اقتراضا ساميا في النهاية ويقارن Proto-Semitic *mašk؛ أغلق نقل مصدر سامي لا إرثا مبسوطا.",
}
FORM_LINKS = {1003: "السطر الخام 5741 يحيل العامية `گلدون` إلى `گلدان` فقط؛ حفظت الإحالة ولم أفكك flowerpot من الذاكرة."}


@dataclass(frozen=True)
class SelectedRow:
    row: H.SweepRow

    @property
    def key(self) -> str:
        return f"S{self.row.rank:05d}"

    @property
    def heading(self) -> str:
        return f"WO-B-R38-SOUND-{self.row.rank:05d}"


Review = R37.Review
R = R37.R

# سجل قراءة يدوي. لا يشتق الحكم من best ولا من وزن المروحة.
REVIEWS = {
    944: R("جز", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`جز`: التميز والانفصال في الكتلة؛ except يفصل عضوا من مجموعة.", "الجسر الدلالي واعد، لكن الشاهد الكلاسيكي الثاني المولد لا يثبت الجز بل مادة مجاورة؛ بقي بلا أثر موجب."),
    945: R("درب", "OPEN-CANDIDATE", "جسر المعنى: `درب` العربية باب السكة والمدخل، وهو معنى gate نفسه.", "اتحد الصوت والمعنى في شاهد مباشر، لكن خبر أن الأصل غير عربي لم يسم المانح؛ حفظت جهة النقل unresolved."),
    946: R("كستن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كستن`: النقص بالدق أو القشر؛ لا يسمي sow أو plant.", "النثر أو الحرث قد يسبق الزرع لكنه ليس معنى الزرع نفسه، والشاهد العربي الوحيد اسم شجرة."),
    947: R("درفش", "OPEN-CANDIDATE", "جسر المعنى: التاج يطلق `درفش` على العلم الكبير في حكاية فارسية.", "الشاهد مستقل واحد ويسمي السياق الفارسي؛ لم أرفعه إلى أثر ولم أخمن اتجاه النقل."),
    948: R("جند", "TOOL-GAP", "جسر المعنى: speaker أو narrator حاضر، لكن /guyande/ يحمل /y/ أسقطها الهيكل.", "أوقف الصامت الساقط المقارنة قبل وصل الكلام بصلابة `جند`."),
    949: R("ورز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ورز`: محاكم الحروف بلا معنى gain أو custom أو craft.", "شاهد `ورز` العربي منفرد ومبهم؛ لم أورث work الإنجليزي أو الأصل الإيراني معنى عربيا."),
    950: R("خزن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خزن`: دس الشيء في حرز مدة طويلة؛ لا يسمي autumn.", "الخريف وقت خزن محتمل، لكن علاقة الموسم بالفعل ظرفية ولا تعرف الفصل معجميا."),
    951: R("بر", "TOOL-GAP", "جسر المعنى: ten thousand معنى عددي، لكن /bēwar/ يحمل /w/ أسقطها الهيكل.", "لا حكم عددي من `بر` بعد سقوط الصامت؛ حفظت السلسلة الإيرانية حاشية."),
    952: R("بيش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بيش`: الانتشار الظاهر؛ لا يسمي front part أو before.", "فصلت الاسم عن الصفة والحال المتجانستين، وشاهدا العربية في نبات وموضع لا التقدم."),
    953: R("بيش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بيش`: الانتشار الظاهر؛ لا يسمي past أو ago.", "لم ترث الصفة حكم الاسم السابق، ولا يحول الانتشار إلى زمن ماض."),
    954: R("بيش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بيش`: الانتشار الظاهر؛ لا يسمي previously أو in advance.", "عزلت الحال عن المتجانسين السابقين؛ التقدم الزمني غير مشهود في العربية."),
    955: R("بستن", "TOOL-GAP", "جسر المعنى: necessary أو must حاضر، لكن /bāyistan/ يحمل /y/ أسقطها الهيكل.", "أوقف عطب /y/ المقارنة قبل ربط اللزوم بجفاف `بستن`."),
    957: R("حفد", "TOOL-GAP", "جسر المعنى: seventeen مفككة إلى `هفت` seven و`ده` ten، لكن /hefdah/ فقدت هاءها النهائية.", "قُرئ العددان استقلالا ثم أوقف عطب الهاء حكم الصورة المجموعة."),
    958: R("بجن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بجن`: التفتق والتفجر الرخو؛ لا يسمي foreign أو strange.", "الغربة علاقة اجتماعية لا تستخرج من التفتق، والشاهد العربي اسم مكان."),
    959: R("بجن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بجن`: التفتق الرخو؛ لا يسمي outsider أو foreigner.", "فصلت اسم الشخص عن الصفة السابقة؛ لم يرث أحد المتجانسين حكم الآخر."),
    960: R("هنجل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`هنجل`: محاكم حروف مع امتداد؛ لا يسمي way أو rule أو custom.", "اختير مسار كامل ولم يبدل هاء بحاء؛ بقي القانون والمعيار بلا مدار عربي."),
    961: R("جنن", "COMPOUND-BOUNDARY", "جسر المعنى: such as this مصرح بانقباض `چون` like و`این` this.", "قُرئ المكونان؛ لم تقارن الصورة المجموعة بجذر عربي واحد، مع بقاء چ↔ج خارج الحكم."),
    962: R("جنن", "COMPOUND-BOUNDARY", "جسر المعنى: this way هو الانقباض نفسه من `چون` و`این`.", "فصلت الحال عن الصفة السابقة، ووقف الحكم عند حد المكونين نفسيهما."),
    963: R("كج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كج`: محكمتا الحرفين؛ لا تسمي because.", "رفضت التحليل السطحي إلى where وplace بعد الخبر الموروث؛ بقي الرابط الوظيفي بلا مدار."),
    964: R("بس", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`بس`: الجفاف واليبوسة؛ لا يسمي then أو therefore.", "فصلت أداة النتيجة عن المتجانسين المكانيين؛ الوظيفة النحوية لا تستخرج من اليبس."),
    965: R("بس", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`بس`: الجفاف واليبوسة؛ لا يسمي back part أو behind.", "كون الخلف أقل ظهورا احتمال بصري لا معنى معجميا، ولم يرث حكم الرابط السابق."),
    966: R("بس", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`بس`: الجفاف واليبوسة؛ لا يسمي behind أو afterwards.", "عزلت الحال عن الاسم والرابط؛ لا شاهد عربي على التأخر في مادة `بس`."),
    967: R("بركل", "COMPOUND-BOUNDARY", "جسر المعنى: hard-working مصرح بتكوينه من `پر` full و`کار` work.", "قُرئ المكونان استقلالا؛ لم يختزل prolific أو كثرة العمل في جذر رباعي."),
    968: R("بيد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بيد`: خلو البراح الواسع؛ لا يسمي willow.", "عيش الشجرة قرب الماء أو في أرض بعينها وصف بيئي لا معنى الشجرة."),
    970: R("ته", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`ته`: الفراغ والباطل؛ empty أو hollow جسر مباشر في الحدث.", "الشاهدان العربيان المولدان في التهتهة والتواء اللسان لا يثبتان الفراغ؛ بقي الجسر بلا شاهدين."),
    972: R("تلو", "NUCLEUS-TRACE", "جسر المعنى: التلو ولد الحمار أو الشاة الذي يتبع أمه، وهو whelp نفسه.", "مدار 1: الصغير تابع لأمه؛ أثبت العين ولد الحمار وأثبت المحيط ولد الشاة مع حدث الاتباع."),
    973: R("جرش", "COMPOUND-BOUNDARY", "جسر المعنى: action مصرح بتكوينها من `ژیر` act و`ـش` لاحقة اسم الحدث.", "الجذع غائب مستقلا واللاحقة مقروءة؛ وقف الحكم عند حد المركب ولم يسو الجذع حدسا."),
    974: R("جدن", "LAW-GAP", "نص الحدث المجمد لـ`جدن`: العظم والامتداد؛ لا يسمي gather أو arrange.", "المعنى غير مكتمل، كما أن چ↔ج غير مسمى؛ لم يعوض تقارب الجمع الصوت الناقص."),
    975: R("جذن", "LAW-GAP", "جسر المعنى: القطع الجزئي في `جذن` قريب من pick أو pluck.", "مدار القطع واعد، لكن چ↔ج ود↔ذ غير مسميين؛ لم يصدر أثر موجب."),
    976: R("نبذر", "LAW-GAP", "نص الحدث المجمد لـ`نبذر`: النبو والابتعاد؛ stepfather مركب قرابي غير مشروح في المصدر.", "لم أخترع `نا` و`پدری`، ومسار د↔ذ ناقص؛ بقيت البنية والمعنى مفتوحين."),
    978: R("سبنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سبنج`: محاكم حروف؛ لا يسمي guesthouse أو guest.", "المقابلات السامية في الأصل موسومة قروضا إيرانية لا جسرا عربيا؛ المسار الكامل وحده لا يكفي."),
    979: R("خرد", "TOOL-GAP", "جسر المعنى: eatables أو broth حاضر، لكن /xvardi/ يحمل /v/ أسقطها الهيكل.", "أوقف /v/ الساقط المقارنة قبل ربط الطعام بحدث `خرد`."),
    980: R("خرك", "TOOL-GAP", "جسر المعنى: food حاضر، لكن /xwarāk/ يحمل /w/ أسقطها الهيكل.", "رفضت التحليل السطحي بعد الوراثة، وأوقف عطب /w/ الصورة قبل الحكم."),
    981: R("باك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`باك`: الضغط والاحتباس؛ لا يسمي dread أو fear.", "الانقباض أثر جسدي للخوف لا معنى الخوف، ولا شاهد عربي كلاسيكي في المورد."),
    983: R("حند", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`حند`: محاكم الحروف؛ لا يسمي laughter.", "اختير مسار كامل، ورفض تفكيك الصورة الوسطى التاريخية؛ بقي الضحك بلا شاهد عربي."),
    984: R("جرفت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جرفت`: الاسترسال مع حدث الفاء؛ لا يسمي eclipse.", "كون الكسوف أخذا للنور تفسير للصورة الإيرانية لا معنى `جرفت` العربية، وشاهدها منفرد."),
    985: R("جدن", "TOOL-GAP", "جسر المعنى: chew أو gnaw حاضر، لكن /javidan/ يحمل /v/ أسقطها الهيكل.", "أوقف الصامت الساقط المقارنة قبل أي وصل بالعظم أو الامتداد."),
    986: R("زرف", "COMPOUND-BOUNDARY", "جسر المعنى: depth مصرح بتكوينها من `ژرف` deep و`ـی` الاسم المجرد.", "قُرئت الصفة واللاحقة؛ لم تقارن الصورة المشتقة بجذر واحد مع بقاء ژ↔ز خارج الحكم."),
    987: R("برشن", "COMPOUND-BOUNDARY", "جسر المعنى: scattered أو distressed مصرح بتكوينها من `پریش` و`ـان`.", "قُرئ الجذع واللاحقة؛ لم يورث المركب حكم الانتشار أو التجرد من مرشح عربي."),
    988: R("رشت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رشت`: انتشار دقيق طري؛ لا يسمي bright.", "خبر light الهندوأوروبي حاشية، وشواهد `رشت` العربية غائبة؛ لم يجعل الانتشار ضوءا."),
    989: R("وبق", "TOOL-GAP", "جسر المعنى: website مفككة إلى web و`ـگاه`، لكن /veb-gāh/ فقدت هاءها النهائية.", "قُرئ المكونان ثم أوقف عطب الهاء حكم الصورة المجموعة."),
    990: R("زردن", "LAW-GAP", "نص الحدث المجمد لـ`زردن`: النفاذ مع إمساك؛ لا يسمي disheveled أو chaotic.", "المعنى غائب، وژ↔ز غير مسمى؛ لم يحول related to شوریدن إلى تفكيك أو قانون."),
    991: R("جلن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جلن`: الاتساع والانكشاف؛ لا يسمي gluon.", "المصطلح الفيزيائي ذو حقل أصل فارغ؛ لم يعوضه من المعرفة العامة ولا من تشابه لفظي."),
    992: R("جزف", "LOANWORD-NON-ARABIC-TO-ARABIC", "جسر المعنى: excessive أو extravagant يطابق الأخذ بالكثرة والجزاف بلا كيل.", "العين يسميه دخيلا والصحاح يسميه فارسيا معربا؛ أغلق اتجاه الفارسية إلى العربية تماسًا لا إرثا."),
    993: R("كرز", "TOOL-GAP", "جسر المعنى: verb مفككة إلى `کار` work و`واژه` word، لكن /kārvāže/ يحمل /v/ ساقطة.", "قُرئ المكونان ثم أوقف عطب /v/ حكم الصورة المجموعة."),
    994: R("نيم", "TOOL-GAP", "جسر المعنى: sheath أو scabbard حاضر، لكن /niyām/ يحمل /y/ أسقطها الهيكل.", "أوقف الصامت الساقط المقارنة قبل وصل الغلاف بانتشار `نيم`."),
    995: R("جرك", "LAW-GAP", "نص الحدث المجمد لـ`جرك`: الاسترسال؛ لا يسمي bread.", "خبر القرض التركي محفوظ، وچ↔ج غير مسمى؛ فصلت الخبز عن متجانسي الوسخ والقيح."),
    996: R("جرك", "LAW-GAP", "نص الحدث المجمد لـ`جرك`: الاسترسال؛ لا يسمي dirty.", "المعنى الإيراني مستقل عن bread، وچ↔ج غير مسمى؛ لا أثر من اتحاد الرسم."),
    997: R("جرك", "LAW-GAP", "نص الحدث المجمد لـ`جرك`: الاسترسال؛ لا يسمي pus أو dirt.", "فصلت الاسم عن الصفة السابقة، وبقي چ↔ج مانعا صوتيا مع غياب المعنى."),
    998: R("شرقش", "LAW-GAP", "جسر المعنى: baker مرتبط بخبز `چرک` التركي، لكن المصدر لا يعطي تفكيكا نهائيا.", "چ↔ش مفقود في الموضعين، ولم أخترع لاحقة مهنة من الرسم؛ بقي القانون والبنية ناقصين."),
    999: R("ارب", "LAW-GAP", "نص الحدث المجمد لـ`ارب`: محاكم الحروف؛ لا يسمي barley.", "خبر القرض التركي لا يمد العربية باتجاه، وآ↔ا غير مسمى؛ لم يصدر حكم."),
    1000: R("بذر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بذر`: نثر الدقاق؛ لا يسمي living room.", "الضيافة أو الاستقبال فعل يقع في الغرفة ولا يساوي الغرفة؛ حقل الأصل فارغ."),
    1001: R("بخس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بخس`: نقص في الأثناء؛ part أو portion أقل من الكل.", "النقص علاقة كمية عامة لا تميز القسم الموزع، وخبر الأصل الإيراني لا يسمي العربية."),
    1002: R("زيب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زيب`: الاكتناز أو النضح؛ لا يسمي zipper.", "لم يعوض حقل الأصل الفارغ، وشاهدا العربية في ريح ونشاط لا أداة الإغلاق."),
    1003: R("كلدن", "OPEN-CANDIDATE", "جسر المعنى: السطر يحيل `گلدون` إلى الصورة المعيارية `گلدان` بلا أصل مستقل.", "حفظت FORM-LINK، ولم أفكك flowerpot من معرفة سابقة أو أورثه حكم الصورة المعيارية."),
    1004: R("خول", "TOOL-GAP", "جسر المعنى: soot حاضر، لكن /xvāl/ يحمل /v/ أسقطها الهيكل.", "أوقف الصامت الساقط المقارنة قبل ربط السخام بحيازة `خول`."),
    1005: R("نز", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`نز`: نفاذ دقيق بضغط؛ لا يسمي also أو too.", "رفضت مكونات الفارسية الوسطى كتفكيك حديث؛ الوظيفة الإضافية لا تستخرج من الحدث."),
    1007: R("كرنس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كرنس`: استقرار في قاع؛ لا يسمي gravitation.", "الاستقرار نتيجة للجاذبية لا تعريفها، وحقل الأصل لا يصرح بثقل أو لاحقة."),
    1008: R("برو", "TOOL-GAP", "جسر المعنى: heifer حاضر، لكن /parow/ يحمل /w/ نهائية أسقطها الهيكل.", "لا يقارن الحيوان بحدث `برو` من هيكل ناقص."),
    1009: R("برو", "TOOL-GAP", "جسر المعنى: trying on حاضر، لكن /prov/ يحمل /v/ أسقطها الهيكل.", "فصلت المتجانس عن heifer وأوقفت /v/ قبل أي مدار للقياس أو التجربة."),
    1010: R("سخن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سخن`: لين يسمح بالاختراق؛ لا يسمي speech.", "شواهد العربية في الحرارة، ولا يجعل خروج الهواء كلاما من غير معنى معجمي مباشر."),
    1011: R("جبتل", "COMPOUND-BOUNDARY", "جسر المعنى: speech أو discourse مصرح بتكوينه من `گفتن` say و`ـار`.", "قُرئ الفعل واللاحقة؛ لم تقارن الصورة الرباعية بجذر عربي واحد."),
    1012: R("ككك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ككك`: تكرار محكمة الكاف؛ لا يسمي human excrement.", "المقارنة الهندوأوروبية في الأصل لا تخلق شاهدا عربيا، والمورد يحوي اسم علم منفردا."),
    1013: R("منش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`منش`: قوة وثبات؛ لا يسمي character أو nature.", "ثبات الطبع احتمال وصفي لا معنى المعجم، والشاهد العربي اسم مكان منفرد."),
    1014: R("بدس", "TOOL-GAP", "جسر المعنى: king أو sovereign حاضر، لكن /pādišāh/ فقدت هاءها النهائية.", "أوقف عطب الهاء المقارنة قبل إسقاط الصوائت أو اختزال اللقب التاريخي."),
    1015: R("كيش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كيش`: خروج المتغلغل؛ لا يسمي religion أو cult.", "شواهد العربية في صفة الثوب، ولم أحول dogma الفارسية الوسطى إلى معنى عربي."),
    1016: R("مسك", "SEMITIC-SOURCE-TRANSMISSION", "جسر المعنى: `المسك` العربية الجلد، وwaterskin وعاء مصنوع من الجلد نفسه.", "خبر الأصل يسمي اقتراضا ساميا وProto-Semitic *mašk؛ اتحدت الصورة والجلد فأغلق نقل مصدر سامي لا إرثا مبسوطا."),
    1019: R("نحن", "LAW-GAP", "جسر المعنى: hidden أو secret قريب من الاحتجاب، لكن `نحن` لا يسمي الستر.", "ه↔ح غير مسمى، وشاهدا الضمير لا الخفاء؛ لم يعوض الجسر الصوت أو المعنى."),
    1022: R("سكرج", "COMPOUND-BOUNDARY", "جسر المعنى: hunter مصرح بتكوينه من `شکار` hunt و`ـچی` لاحقة الفاعل.", "قُرئ المكونان؛ لم تقارن الصورة المجموعة بجذر واحد مع بقاء چ↔ج خارج الحكم."),
    1023: R("زرنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زرنج`: نفاذ بدقة مع إمساك؛ لا يسمي clever أو sharp.", "الحدة الذهنية استعارة محتملة لا معنى معجمي، وشاهدا العربية اسم مدينة."),
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
            raise AssertionError(f"تغير عداد نسخة v18 في {name}")
        if len(data.get("both") or []) != expected_both or len(data.get("sound_only") or []) != expected_sound:
            raise AssertionError(f"تغير طول قوائم نسخة v18 في {name}")
        total_both += expected_both
        total_sound += expected_sound
    if total_both != 14496 or total_sound != 106818:
        raise AssertionError("تغير مجموع أحواض v18")


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
            if row.rank > 942 and len(fresh) < 70:
                internal_skips.append(row.rank)
            continue
        seen.add(key)
        if row.rank <= 942:
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


def select_branch_entries(selected: list[SelectedRow], lexicon: dict):
    grouped: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for index, entry in enumerate(lexicon.get("entries") or [], 1):
        grouped[H.clean(entry.get("word") or "")].append((index, entry))
    output: dict[int, H.BranchEntry] = {}
    for item in selected:
        row = item.row
        if row.rank == 1003:
            output[row.rank] = H.BranchEntry(
                global_index=0,
                homograph_index=1,
                homograph_count=1,
                word=row.branch,
                reading="goldun",
                pos="noun",
                gloss="Spoken form of گلدان (goldân).",
                etymology="إحالة صرفية عامية إلى گلدان؛ لا خبر أصل مستقل في الخام.",
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


def validate_components(grouped: dict[str, list[tuple[int, dict]]]) -> None:
    expected_indices = {
        "هفت": {1404}, "ده": {1045, 1046, 1047}, "چون": {1916, 1917},
        "این": {202}, "پر": {317, 318}, "کار": {797}, "ژیر": set(),
        "ـش": {10302, 10303}, "ژرف": {2050}, "ـی": {6328, 6329, 6330, 6331},
        "پریش": {10459}, "ـان": {10304, 10305, 10306}, "وب": {4992, 4993},
        "ـگاه": {7462}, "واژه": {999}, "گفتن": {1037}, "ـار": {10308},
        "شکار": {4476}, "ـچی": {7517},
    }
    fan_counts = {
        "هفت": 12, "ده": 60, "چون": 30, "این": 20, "پر": 40,
        "کار": 40, "ژیر": 60, "ـش": 0, "ژرف": 12, "ـی": 0,
        "پریش": 12, "ـان": 20, "وب": 18, "ـگاه": 72, "واژه": 57,
        "گفتن": 24, "ـار": 40, "شکار": 12, "ـچی": 42,
    }
    for word, expected in expected_indices.items():
        actual = {index for index, _entry in grouped.get(word, [])}
        if actual != expected:
            raise AssertionError(f"تغير جرد مكون {word}: {sorted(actual)}")
        fan = tuple(H.FAN.rank(word, H.FAN.fan(word, "persian"), "persian"))
        if len(fan) != fan_counts[word]:
            raise AssertionError(f"تغيرت مروحة المكون {word}: {len(fan)}")
    expected_raw = {
        "هفت": {1485}, "ده": {1110, 1111, 1112, 1113}, "چون": {2015, 2016},
        "این": {209}, "پر": {334, 335, 336}, "کار": {847, 848}, "ژیر": set(),
        "ـش": {12673, 12674}, "ژرف": {2153}, "ـی": {7420, 7421, 7422, 7423, 7424},
        "پریش": {12858}, "ـان": {12675, 12676, 12677}, "وب": {5770, 5771},
        "ـگاه": {8752}, "واژه": {1062}, "گفتن": {1102}, "ـار": {12680},
        "شکار": {4983}, "ـچی": {8811, 8812},
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
    if review.verdict == "SEMITIC-SOURCE-TRANSMISSION":
        return "سمى المصدر أصلا ساميا واتفقت الصورة والمعنى؛ أغلق نقل مصدر سامي لا إرثا مبسوطا."
    if review.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC":
        return "سمى الشاهد اللفظ فارسيا معربا؛ أغلق تماس من الفارسية إلى العربية لا إرثا."
    if review.verdict == "COMPOUND-BOUNDARY":
        return "وقف الحكم عند حد المركب؛ لم تورث الصورة المجموعة حكم مكون ولم يخترع تفكيك."
    if review.verdict == "LAW-GAP":
        return "طريق المعنى مفحوص، لكن مسار الصوت يحوي صفا غير مسمى؛ لم يصدر حكم موجب."
    if review.verdict == "TOOL-GAP":
        return "صف الحوض أسقط صامتا منطوقا؛ توقف العضو قبل الحكم ولم يعوض الصامت يدويا."
    return "مسار الصوت قابل للفحص، لكن المدار لم يكتمل إلى حكم؛ بقي المرشح مفتوحا."


def decide(item: SelectedRow) -> H.Decision:
    review = REVIEWS[item.row.rank]
    return H.Decision(review.candidate, review.verdict, H.state_for(review.verdict), review.orbit, obstacle_for(review))


def decomposition_lines(item: SelectedRow, raw: dict) -> list[str]:
    rank = item.row.rank
    if rank not in EXACT_DECOMPOSITIONS:
        return []
    etymology = raw["etymology"]
    strip_marks = lambda value: "".join(  # noqa: E731
        char for char in H.clean(value) if unicodedata.category(char) != "Mn"
    )
    joined = strip_marks(etymology)
    for component in EXPECTED_COMPONENTS[rank]:
        if strip_marks(component) not in joined:
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


BASE_MAKE_CARD = R37.make_card


def make_card(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit) -> str:
    card = BASE_MAKE_CARD(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit)
    card = card.replace("الجولة 37،", "الجولة 38،")
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
    if rank in FORM_LINKS and "إحالة الصورة" not in card:
        card = card.replace("- الخطوة صفر:", f"- إحالة الصورة: {FORM_LINKS[rank]}\n- الخطوة صفر:", 1)
    if rank == 992:
        card = card.replace(
            "- المصفاة: الأصل حاشية؛ لا يغلق النقل إلا بمانح سامي مسمى أو تصريح بالتعريب أو باتجاه الدخول إلى العربية.",
            "- المصفاة: العين يسمي اللفظ دخيلا والصحاح يسميه فارسيا معربا؛ يعمل LOANWORD-NON-ARABIC-TO-ARABIC نتيجة تماس إيجابية محسوبة.",
        )
    if rank == 1016:
        card = card.replace(
            "- المصفاة: الأصل حاشية؛ لا يغلق النقل إلا بمانح سامي مسمى أو تصريح بالتعريب أو باتجاه الدخول إلى العربية.",
            "- المصفاة: خبر الأصل يسمي اقتراضا ساميا ويقارن Proto-Semitic *mašk؛ يعمل SEMITIC-SOURCE-TRANSMISSION نتيجة نقل إيجابية محسوبة.",
        )
    return card


def validate_decisions(selected, raw_entries, decisions, ranked_by_rank, sense_map) -> None:
    if set(REVIEWS) != set(SOUND_RANKS):
        raise AssertionError("جدول المدار اليدوي لا يغطي الرتب السبعين")
    parsed = {item.row.rank for item in selected if P25.direct_from_plus(raw_entries[item.row.rank]["etymology"])}
    if parsed != PARSER_FROM_PLUS:
        raise AssertionError(f"تغيرت أسطر From X + Y التي يلتقطها المحلل: {sorted(parsed)}")
    expected_verdicts = {
        "COMPOUND-BOUNDARY": 8,
        "LAW-GAP": 10,
        "LOANWORD-NON-ARABIC-TO-ARABIC": 1,
        "NUCLEUS-TRACE": 1,
        "OPEN-CANDIDATE": 35,
        "SEMITIC-SOURCE-TRANSMISSION": 1,
        "TOOL-GAP": 14,
    }
    if Counter(review.verdict for review in REVIEWS.values()) != Counter(expected_verdicts):
        raise AssertionError(f"تغير توزيع الأحكام اليدوي: {Counter(review.verdict for review in REVIEWS.values())}")
    if {rank for rank, review in REVIEWS.items() if review.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC"} != {992}:
        raise AssertionError("تغير حكم النقل الفارسي إلى العربية")
    if {rank for rank, review in REVIEWS.items() if review.verdict == "SEMITIC-SOURCE-TRANSMISSION"} != {1016}:
        raise AssertionError("تغير حكم النقل السامي")
    for item, decision in zip(selected, decisions):
        row = item.row
        candidates = {candidate for candidate, _score in ranked_by_rank[row.rank]}
        if decision.candidate not in candidates or decision.candidate not in row.candidates_found:
            raise AssertionError(f"مرشح الرتبة {row.rank} خارج المروحة الحية أو أعضاء الحوض")
        complete = H.route_complete(row, decision.candidate)
        _count, coverage, witnesses = P.classical_witnesses(decision.candidate, sense_map, 320)
        if decision.verdict == "LAW-GAP" and complete:
            raise AssertionError(f"LAW-GAP بلا صف مفقود في الرتبة {row.rank}")
        if decision.verdict in {
            "OPEN-CANDIDATE", "NUCLEUS-TRACE", "LOANWORD-NON-ARABIC-TO-ARABIC",
            "SEMITIC-SOURCE-TRANSMISSION",
        } and not complete:
            raise AssertionError(f"حكم بمسار ناقص في الرتبة {row.rank}: {decision.verdict}")
        if decision.verdict == "NUCLEUS-TRACE":
            joined = " ".join(quote for _source, quote in witnesses)
            if coverage < 2 or "وَلَدُ الحمار" not in joined or H.event_line(decision.candidate).startswith("لا حدث"):
                raise AssertionError(f"أثر بلا حدث وشاهدين مباشرين في الرتبة {row.rank}")
        if decision.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC":
            joined = " ".join(quote for _source, quote in witnesses)
            if coverage < 2 or "فارسي معرب" not in joined or "دخيل" not in joined:
                raise AssertionError("نقل جزاف بلا شاهدي الاتجاه")
        if decision.verdict == "SEMITIC-SOURCE-TRANSMISSION":
            etymology = raw_entries[row.rank]["etymology"]
            if coverage < 2 or "Semitic borrowing" not in etymology or "*mašk" not in etymology:
                raise AssertionError("نقل مشک بلا خبر المصدر السامي أو شاهدين")
        if row.rank in EXACT_DECOMPOSITIONS and decision.verdict not in {"COMPOUND-BOUNDARY", "TOOL-GAP"}:
            raise AssertionError(f"تفكيك مباشر بلا حد مركب أو عطب أداة في الرتبة {row.rank}")
        if row.rank in TOOL_GAPS and decision.verdict != "TOOL-GAP":
            raise AssertionError(f"هيكل ناقص بلا TOOL-GAP في الرتبة {row.rank}")
        if row.rank in LAW_GAPS and decision.verdict != "LAW-GAP":
            raise AssertionError(f"مسار ناقص بلا LAW-GAP في الرتبة {row.rank}")
        if not REVIEWS[row.rank].meaning_path.startswith(("جسر المعنى:", "نص الحدث المجمد", "نص النواة المجمدة")):
            raise AssertionError(f"طريق المعنى غير مسمى في الرتبة {row.rank}")


def validate_text(selected, texts, prior_pairs) -> None:
    if len(selected) != 70 or BATCH_SIZES != (35, 35):
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = re.findall(r"^### (WO-B-R38-SOUND-\d{5}):", joined, re.MULTILINE)
    if headings != [item.heading for item in selected]:
        raise AssertionError("معرفات الجولة 38 لا تطابق النافذة")
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
    if "LOANWORD-NON-ARABIC-TO-ARABIC نتيجة تماس" not in texts[SOUND_RANKS.index(992)]:
        raise AssertionError("غاب مرشح النقل الفارسي في بطاقة جزاف")
    if "SEMITIC-SOURCE-TRANSMISSION نتيجة نقل" not in texts[SOUND_RANKS.index(1016)]:
        raise AssertionError("غاب مرشح النقل السامي في بطاقة مشک")
    if "إحالة الصورة" not in texts[SOUND_RANKS.index(1003)]:
        raise AssertionError("غابت إحالة گلدون إلى گلدان")


def report_section(selected, decisions, sizes, stats) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    batches = (selected[:35], selected[35:])
    lines = [f"<!-- {MARKER}:START -->", ""]
    previous = 942
    for number, batch in enumerate(batches, 1):
        lo = 0 if number == 1 else 35
        hi = lo + len(batch)
        counts = Counter(decision.verdict for decision in decisions[lo:hi])
        distribution = "؛ ".join(f"{key}={counts[key]}" for key in sorted(counts))
        batch_skips = [rank for rank in stats["skipped"] if previous < rank <= batch[-1].row.rank]
        skipped = ", ".join(map(str, batch_skips)) or "0"
        lines.extend([
            f"## الجولة الثامنة والثلاثون، دفعة sound_only رقم {number}", "",
            f"- الوقت: {now}، Africa/Cairo.",
            f"- رشح وكتب: {len(batch)}؛ المواضع المقروءة المتجاوزة داخل المدى: {skipped}.",
            f"- المواضع: من {batch[0].heading} إلى {batch[-1].heading}.",
            f"- توزيع الأحكام: {distribution}.",
            "- طريق المعنى: سمي من جسر معنى صريح أو من نص الحدث المجمد في كل بطاقة.",
            "- المدار: كتب يدويا لكل عضو، وفصلت الأصداء اللينة عن الأثر المحكم.",
            "- المروحة: ولدت حية كاملة ورتبت بالأوزان، ومسحت مواد جميع مرشحيها بلا قص للحقل المصدر.",
            "- المتجانسات: قرئت كل مداخل الرسم، وسجل العدد ورقم المدخلة المختارة في كل بطاقة.",
            "- المركب: قبل التصريح النهائي المباشر أو المحكم حصرا؛ لم يخترع مكون.",
            "- التحقق البنيوي: المعرفات فريدة؛ لا بطاقة فوق 5KB؛ لا شرطة طويلة؛ الأرقام غربية والنص NFC.",
            f"- آخر موضع في الدفعة: {batch[-1].heading}، `{batch[-1].row.branch}`.", "",
        ])
        previous = batch[-1].row.rank
    total = Counter(decision.verdict for decision in decisions)
    distribution = "؛ ".join(f"{key}={total[key]}" for key in sorted(total))
    max_size = max(sizes)
    max_item = selected[sizes.index(max_size)]
    traces = [item.heading for item, decision in zip(selected, decisions) if decision.verdict == "NUCLEUS-TRACE"]
    transmissions = [item.heading for item, decision in zip(selected, decisions) if decision.verdict in {"SEMITIC-SOURCE-TRANSMISSION", "LOANWORD-NON-ARABIC-TO-ARABIC"}]
    lines.extend([
        "## حصيلة الجولة الثامنة والثلاثين", "",
        f"- حمل `persian.md` مرة واحدة؛ أزواج WO-B المقروءة={stats['pair_count']}؛ المتجاوز داخل النافذة={', '.join(map(str, stats['skipped']))}.",
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- نطاق الصوت الجديد: الرتب 944-1023 بعد WO-B-R37-SOUND-00942، مع تجاوز 943 و956 و969 و971 و977 و982 و1006 و1017 و1018 و1020 و1021 لأنها مقروءة.",
        f"- الأثر النووي الاستكشافي الجديد: {', '.join(traces)}؛ لم تفعل طبقة البرهان ولم تنشر أرقاما.",
        f"- نتائج النقل المصفاة: {', '.join(transmissions)}؛ S00992 تماس فارسي معرب، وS01016 نقل مصدر سامي، لا إرثان مبسوطان.",
        "- التفكيك النهائي المؤهل: S00957، S00961، S00962، S00967، S00973، S00986، S00987، S00989، S00993، S01011، S01022؛ قرئت المكونات مستقلة، ووقفت S00957 وS00989 وS00993 عند عطب صوتي.",
        "- التحليلات غير المؤهلة: S00963، S00980، S00983، S01005؛ حفظت طبقتها التاريخية أو وسمها السطحي ولم تحول إلى تفكيك نهائي.",
        "- أعطاب الأداة: S00948، S00951، S00955، S00957، S00979، S00980، S00985، S00989، S00993، S00994، S01004، S01008، S01009، S01014؛ لم تعوض الصوامت المنطوقة الساقطة.",
        "- فجوات القانون: S00974، S00975، S00976، S00990، S00995، S00996، S00997، S00998، S00999، S01019.",
        "- إحالة الصورة: S01003 عامية محالة إلى `گلدان`؛ حفظ FORM-LINK ولم يفكك المركب من الذاكرة.",
        "- أحواض `nucleus-sweep-*.json` التسعة الحالية v18 قرئت كاملة من القرص؛ both=14496 وsound_only=106818؛ ثبت الحجم وSHA-256 والعدادات لكل ملف.",
        f"- أكبر بطاقة: {max_size} بايت، {max_item.heading}؛ كل البطاقات دون 5KB.",
        "- لم تفعل طبقة البرهان؛ مر حارس نقاء الشحنة وختم CLEAN؛ لم يقع ship ولم يستعمل git.",
        "", f"<!-- {MARKER}:END -->", "", DONE_LINE,
    ])
    return "\n".join(lines)


def validate_existing(reading_text: str, report_text: str) -> None:
    match = re.search(rf"<!-- {re.escape(MARKER)}:START -->(.*?)<!-- {re.escape(MARKER)}:END -->", reading_text, re.DOTALL)
    if not match:
        raise AssertionError("محضر الجولة موجود وبطاقاتها غائبة")
    headings = re.findall(r"^### (WO-B-R38-SOUND-\d{5}):", match.group(1), re.MULTILINE)
    expected = [f"WO-B-R38-SOUND-{rank:05d}" for rank in SOUND_RANKS]
    if headings != expected:
        raise AssertionError("مقطع الجولة 38 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(DONE_LINE):
        raise AssertionError("سطر DONE38 ليس خاتمة التقرير")


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
        print("ROUND38 ALREADY PRESENT AND VALID")
        print(DONE_LINE)
        return 0

    validate_nucleus_snapshot()
    data = json.loads(SWEEP.read_text(encoding="utf-8"))
    selected, stats = select_rows(data, reading_text)
    prior_pairs = H.read_pairs(reading_text)
    lexicon = json.loads(LEXICON.read_text(encoding="utf-8"))

    entries, grouped = select_branch_entries(selected, lexicon)
    R35.EXPECTED_RAW_LINE = EXPECTED_RAW_LINE
    raw_entries = R35.load_raw_entries(selected, entries)
    validate_components(grouped)

    R35.SOURCE_NOTES = SOURCE_NOTES
    R35.TOOL_GAPS = TOOL_GAPS
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
        "## الجولة الثامنة والثلاثون: متابعة حوض sound_only (2026-08-27)\n\n"
        "- النطاق: 70 عضوا طازجا بعد WO-B-R37-SOUND-00942؛ من الرتبة 944 إلى 1023 مع تجاوز 943 و956 و969 و971 و977 و982 و1006 و1017 و1018 و1020 و1021 لأنها مقروءة؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ طريق المعنى مسمى، والمدار اليدوي حاسم، والأصداء مفصولة عن الأثر المحكم.\n"
        "- لقطة الأحواض: قرئت ملفات nucleus-sweep-*.json التسعة الحالية v18 من القرص؛ ثبتت بصماتها وعداداتها قبل الانتخاب.\n\n"
        + "\n".join(texts[:35])
        + "\n## الدفعة الثانية: متابعة sound_only بعد الرتبة 981\n\n"
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
    print("ROUND38 READY")
    print("NUCLEUS_V18_FILES", len(NUCLEUS_SNAPSHOT), "SHA256_AND_COUNTS_OK")
    print("NUCLEUS_V18_TOTALS", "BOTH=14496", "SOUND_ONLY=106818")
    print("SKIPPED", ",".join(map(str, stats["skipped"])))
    print("BATCHES", *BATCH_SIZES, "SELECTED", len(selected))
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("TRACES", " ".join(f"S{rank:05d}" for rank in sorted(rank for rank, review in REVIEWS.items() if review.verdict == "NUCLEUS-TRACE")))
    print("TRANSMISSIONS", " ".join(f"S{rank:05d}" for rank in sorted(rank for rank, review in REVIEWS.items() if review.verdict in {"SEMITIC-SOURCE-TRANSMISSION", "LOANWORD-NON-ARABIC-TO-ARABIC"})))
    print("EXACT_COMPONENTS", " ".join(f"S{rank:05d}" for rank in sorted(EXACT_DECOMPOSITIONS)))
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
    print("ROUND38 WRITTEN")
    print(DONE_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
