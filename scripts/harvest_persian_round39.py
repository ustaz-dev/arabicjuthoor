# -*- coding: utf-8 -*-
"""المسار B، الجولة 39: متابعة إنقاذ حوض sound_only في دفعتين من 35 بطاقة."""

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

import harvest_persian_round38 as R38  # noqa: E402

R36 = R38.R36
R35 = R38.R35
R34 = R38.R34
R32 = R38.R32
R31 = R38.R31
R29 = R38.R29
R28 = R38.R28
H = R38.H
P = R38.P
P25 = R38.P25
READING = R38.READING
REPORT = R38.REPORT
SWEEP = R38.SWEEP
NUCLEUS_DIR = R38.NUCLEUS_DIR
LEXICON = R38.LEXICON
RAW_LEXICON = R38.RAW_LEXICON
MARKER = "LANE-B-PERSIAN-ROUND39-2026-08-27"
CARD_LIMIT = 5120
SOUND_RANKS = (
    1024, 1025, 1026, 1028, 1029, 1030, 1031, 1034, 1035, 1037,
    1038, 1039, 1040, 1042, 1043, 1044, 1045, 1046, 1047, 1048,
    1049, 1050, 1051, 1052, 1054, 1055, 1056, 1057, 1058, 1059,
    1060, 1061, 1062, 1063, 1064, 1065, 1066, 1068, 1069, 1070,
    1071, 1072, 1073, 1074, 1075, 1076, 1077, 1078, 1079, 1082,
    1083, 1084, 1085, 1086, 1088, 1089, 1090, 1091, 1092, 1093,
    1095, 1097, 1098, 1099, 1100, 1101, 1102, 1104, 1106, 1107,
)
BATCH_SIZES = (35, 35)
DONE_LINE = "LANE-B DONE39 70 WO-B-R39-SOUND-01107"
EXPECTED_SKIPS = (1027, 1032, 1033, 1036, 1041, 1053, 1067, 1080, 1081, 1087, 1094, 1096, 1103, 1105)

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
    5206, 5207, 5210, 5220, 5224, 5255, 5256, 5271, 5272, 5283,
    5286, 5287, 5291, 5303, 5304, 5310, 5328, 5331, 5344, 5354,
    5363, 5378, 5382, 5384, 5427, 5446, 5449, 5454, 5469, 5471,
    5495, 5508, 5524, 5527, 5532, 5540, 5551, 5555, 5557, 5560,
    5563, 5575, 5576, 5577, 5586, 5587, 5596, 5597, 5613, 5620,
    5625, 5626, 5631, 5638, 5648, 5655, 5657, 5658, 5659, 5660,
    5668, 5672, 5673, 5674, 5676, 5686, 5706, 5725, 5730, 5733,
)))
EXPECTED_RAW_LINE = dict(zip(SOUND_RANKS, (
    6051, 6054, 6057, 6071, 6075, 6121, 6122, 6151, 6152, 6175,
    6183, 6184, 6188, 6211, 6212, 6218, 6238, 6245, 6263, 6279,
    6295, 6313, 6320, 6322, 6378, 6401, 6406, 6414, 6431, 6433,
    6457, 6472, 6490, 6493, 6500, 6510, 6523, 6527, 6531, 6534,
    6537, 6555, 6556, 6557, 6566, 6567, 6579, 6581, 6603, 6610,
    6616, 6617, 6624, 6631, 6642, 6651, 6654, 6655, 6656, 6657,
    6665, 6669, 6670, 6671, 6673, 6683, 6706, 6728, 6733, 6736,
)))

PARSER_FROM_PLUS = {1028, 1034, 1035, 1044, 1046, 1048, 1050, 1051, 1056, 1057, 1068, 1085, 1104}
EXACT_DECOMPOSITIONS = {1028, 1034, 1035, 1042, 1043, 1044, 1046, 1048, 1050, 1051, 1056, 1057, 1068, 1085, 1104}
EXPECTED_COMPONENTS = {
    1028: ("ساده", "ـگی"), 1034: ("شب", "کور"), 1035: ("شب", "کور"),
    1042: ("فرزان", "ـه"), 1043: ("فرزان", "ـه"), 1044: ("گشاد", "ـی"),
    1046: ("پیر", "زن"), 1048: ("گل", "ـزار"), 1050: ("گریز", "ـان"),
    1051: ("بزرگ", "ـی"), 1056: ("هرزه", "ـگی"), 1057: ("به", "ویژه"),
    1068: ("خانواده", "ـگی"), 1085: ("بیـ", "پروا"), 1104: ("جدا", "ـیی"),
}
COMPONENT_READINGS = {
    1028: "`ساده`: entry[791] والخام 840 لمعنى simple أو easy، ومروحتها 90؛ خبرها يسمي العربية `ساذج`، لكن د↔ذ غير مسمى: LAW-GAP. `ـگی`: غائبة من branch-lexicons، والخام 17716 لاحقة تجريد، ومروحتها 56: MORPHOLOGY-GAP.",
    1034: "`شب`: entry[968] والخام 1026 لمعنى night، ومروحتها 30: OPEN-CANDIDATE. `کور`: entry[3083] والخام 3418 لمعنى blind، ومروحتها 40: OPEN-CANDIDATE.",
    1035: "مرجع المكونين في S01034: `شب` night و`کور` blind؛ قرئت المدخلتان والمروحتان نفسيهما، ولم يرث حس الحيوان حكم الصفة.",
    1042: "`فرزان`: غائبة من branch-lexicons والخام مستقلة، ومروحتها 12: FORM-LINK. `ـه`: اختيرت entry[7113] والخام 8351 لاحقة اسم متصل، ومروحتها صفر: MORPHOLOGY-GAP.",
    1043: "مرجع المكونين في S01042: `فرزان` و`ـه`؛ لم يرث اسم الشخص حكم الصفة المتجانسة.",
    1044: "`گشاد`: entry[3709] والخام 4144 لمعنى wide أو broad، ومروحتها 36: OPEN-CANDIDATE. `ـی`: اختيرت entry[6330] والخام 7422 لصنع الاسم المجرد، ومروحتها صفر: MORPHOLOGY-GAP.",
    1046: "`پیر`: اختيرت entry[2239] والخام 2350 لمعنى old، ومروحتها 40: OPEN-CANDIDATE. `زن`: entry[228] والخام 237 لمعنى woman، ومروحتها 30: OPEN-CANDIDATE.",
    1048: "`گل`: اختيرت entry[366] والخام 394 لمعنى flower أو rose، ومروحتها 80: OPEN-CANDIDATE. `ـزار`: entry[10307] والخام 12679 لاحقة مكان الكثرة، ومروحتها 60: MORPHOLOGY-GAP.",
    1050: "`گریز`: entry[9043] والخامان 10703-10704 للجذع واسم flight، ومروحتها 24: OPEN-CANDIDATE. `ـان`: اختيرت entry[10305] والخام 12676 لاحقة صفة، ومروحتها 20: MORPHOLOGY-GAP.",
    1051: "`بزرگ`: entry[738] والخام 784 لمعنى big أو great، ومروحتها 24: OPEN-CANDIDATE. `ـی`: entry[6330] والخام 7422 لاحقة الاسم المجرد، ومروحتها صفر: MORPHOLOGY-GAP.",
    1056: "`هرزه`: entry[5446] والخام 6401 لمعاني lewd وvain وunrestrained، ومروحتها 12: OPEN-CANDIDATE. `ـگی`: الخام 17716 لاحقة تجريد، ومروحتها 56: MORPHOLOGY-GAP.",
    1057: "`به`: اختيرت entry[1119] والخام 1191 لحرف الجر، ومروحتها 20: OPEN-CANDIDATE. `ویژه`: entry[3233] والخام 3602 لمعنى special، ومروحتها 57: OPEN-CANDIDATE.",
    1068: "`خانواده`: entry[2773] والخام 3050 لمعنى family أو household، ومروحتها 9: OPEN-CANDIDATE. `ـگی`: الخام 17716 لاحقة تجريد، ومروحتها 56: MORPHOLOGY-GAP.",
    1085: "`بیـ`: entry[14756] والخام 17675 سابقة -less، ومروحتها 14: MORPHOLOGY-GAP. `پروا`: entry[5630] والخام 6623 لمعنى fear أو care، ومروحتها 40: OPEN-CANDIDATE.",
    1104: "`جدا`: اختيرت entry[90] والخام 92 لمعنى separate، ومروحتها 60: OPEN-CANDIDATE. `ـیی`: غائبة من branch-lexicons مستقلة، والخام 6319 لاحقة الاسم، ومروحتها 20: MORPHOLOGY-GAP.",
}

TOOL_GAPS = {
    1045: "الصورة `سیاه‌چاله` منقوطة /siyāh-čāle/، لكن الهيكل أسقط /y/ المنطوقة.",
    1052: "الصورة `جگوار` منقوطة /jagvār/، لكن الهيكل أسقط /v/ المنطوقة.",
    1057: "الصورة `بویژه` منقوطة /bawēža/، لكن الهيكل أسقط /w/ المنطوقة.",
    1059: "الصورة `سیزده` منقوطة /sizdah/، لكن الهيكل أسقط الهاء النهائية المنطوقة.",
    1068: "الصورة `خانوادگی` منقوطة /xānawādagī/، لكن الهيكل أسقط /w/ المنطوقة.",
    1071: "الصورة `گراویتون` منقوطة /gerāviton/، لكن الهيكل أسقط /v/ المنطوقة.",
    1082: "الصورة `دشوار` منقوطة /došvār/، لكن الهيكل أسقط /v/ المنطوقة.",
    1085: "الصورة `بی‌پروا` منقوطة /bi-parvā/، لكن الهيكل أسقط /v/ المنطوقة.",
    1104: "الصورة `جدایی` منقوطة /judāyī/، لكن الهيكل أسقط /y/ المنطوقة.",
}
LAW_GAPS = {1030, 1031, 1037, 1038, 1039, 1058, 1064, 1069, 1078, 1088, 1089, 1095, 1097, 1098}
OUT_OF_SCOPE = {
    1060: "اسم ديني أفستي بعينه؛ لا معنى معجميا عاما في المدخلة.",
    1092: "اسم فرس رستم بعينه؛ لا معنى معجميا عاما في المدخلة.",
    1100: "اسم Persepolis بعينه؛ لا معنى معجميا عاما في المدخلة.",
}
REJECTED_ANALYSES = {
    1054: "التحليل إلى `پوش` و`ـاک` موسوم By surface analysis، فلم يؤهل تفكيكا نهائيا.",
    1059: "تفكيك Proto-Iranian إلى three وten تاريخي، لا تفكيكا نهائيا مباشرا للصورة الفارسية الحديثة.",
    1064: "التحليل إلى `چال` و`ـش` تعليل اشتقاقي مع تنبيه إلى المطابقة الصوتية الحديثة، لا From نهائيا حاسما.",
    1082: "التحليل إلى `دش` و`خوار` موسوم By surface analysis بعد الصورة الوسطى، فلم يؤهل، ثم أوقفه عطب /v/ أيضا.",
}
SOURCE_NOTES = {
    1026: "خبر الأصل يسمي انتقال اللفظ الفارسي إلى الآرامية، لا إلى العربية؛ حفظ الاتجاه ولم يعمم.",
    1028: "خبر `ساده` يسمي العربية `ساذج`، لكنه للمكون لا للصورة المشتقة `سادگی`، ومعه د↔ذ غير مسمى.",
    1052: "حقل الأصل فارغ؛ لم يعوض أصل jaguar من المعرفة العامة.",
    1058: "حقل الأصل فارغ؛ لم يعوض أصل Demiurge من المعرفة العامة.",
    1060: "خبر الأصل يرد الاسم إلى الأفستية؛ العضو اسم ديني بعينه لا معنى معجميا عاما.",
    1063: "المقارنة البعيدة مع English whale حاشية أصل؛ لا تمد طريقا عربيا.",
    1069: "خبر الأصل غير محسوم ويذكر محاكاة النفخ وصلته بـ`پوک`؛ لم يحول الاحتمال إلى نسب.",
    1075: "العربية `كركي` تسمي طائرا آخر غير السمانى؛ لم يساو بين الأنواع.",
    1076: "العربية `كركي` تسمي طائرا آخر غير الدجاجة؛ لم يرث حس hen حكم حس quail.",
    1077: "خبر الأصل يسمي الأرمنية آخذا من البارثية؛ لا يسمي العربية طرفا في النقل.",
    1079: "خبر الأصل يجعل `رم` الفارسية doublet داخل الفرع؛ لم ينقل ذلك إلى العربية.",
    1083: "ذكر `زوج` العربية doublet إتيمولوجيا، لا تصريحا بأن `جفت` العربية أخذت المعنى الفارسي.",
    1084: "فصلت الصفة عن اسم pair السابق؛ لا وراثة حكم بين المتجانسين.",
    1090: "يسمي الخبر الأرمنية والجورجية آخذتين إيرانيتين؛ لا يسمي العربية.",
    1091: "الفارسية نفسها آخذة على الأرجح من الصغدية؛ لم يخترع اتجاه إلى العربية.",
    1092: "العضو اسم فرس رستم بعينه؛ عزل من الحكم العام مع حفظ تاريخ الصورة.",
    1100: "العضو اسم Persepolis بعينه، من الفارسية القديمة Pārsa؛ عزل من الحكم العام.",
    1101: "خبر الأصل يسمي الأرمنية آخذة إيرانية؛ لا يسمي العربية طرفا.",
    1106: "المقارنة باليونانية حاشية cognate؛ والمرشح العربي `قبق` اسم جبل لا طائر.",
}
FORM_LINKS: dict[int, str] = {}


@dataclass(frozen=True)
class SelectedRow:
    row: H.SweepRow

    @property
    def key(self) -> str:
        return f"S{self.row.rank:05d}"

    @property
    def heading(self) -> str:
        return f"WO-B-R39-SOUND-{self.row.rank:05d}"


Review = R38.Review
R = R38.R

# سجل قراءة يدوي. لا يشتق الحكم من best ولا من وزن المروحة.
REVIEWS = {
    1024: R("درجل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`درجل`: جريان باسترسال؛ لا يسمي sad أو offended.", "حزن القلب وصف داخلي لا يستخرج من سير العقبة أو الرقص؛ وحقل الأصل فارغ."),
    1025: R("درجل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`درجل`: جريان باسترسال؛ لا يسمي sadness أو grief.", "فصلت الاسم عن الصفة السابقة؛ لم يرث أحد المتجانسين حكم الآخر."),
    1026: R("هزن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`هزن`: حركة خفيفة مضطربة؛ لا يسمي cost أو expense.", "خبر الآرامية اتجاه فرعي محفوظ، وشاهدا العربية في اسم قبيلة لا الثمن."),
    1028: R("سذج", "COMPOUND-BOUNDARY", "جسر المعنى: simplicity مصرح باشتقاقها من `ساده` simple و`ـگی` الاسم المجرد.", "قُرئ المكونان؛ حفظ خبر تعريب `ساذج` وفجوة د↔ذ للمكون، ولم يورثا حكم الصورة المشتقة."),
    1029: R("بشن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بشن`: محاكم الحروف؛ لا يسمي old أو former.", "شواهد العربية لا تقدم زمنا معجميا، ولم تفكك اللاحقة من الرسم بغير مصدر."),
    1030: R("جل", "LAW-GAP", "جسر المعنى: العدد forty مثبت، لكن چ↔ج غير مسمى.", "حفظت الإحالة إلى `چهل` ولم تعوض صف الصوت أو تجعل العظمة عددا."),
    1031: R("جل", "LAW-GAP", "نص النواة المجمدة لـ`جل`: الاتساع والانكشاف؛ لا تسمي penis، ومعه چ↔ج غير مسمى.", "فصلت حس العضو عن العدد السابق وعن صورة `چول` المحالة؛ بقي القانون والمعنى ناقصين."),
    1034: R("شبكر", "COMPOUND-BOUNDARY", "جسر المعنى: night blind مصرح بتكوينه من `شب` night و`کور` blind.", "قُرئ المكونان؛ لم تقارن الصفة المجموعة بجذر رباعي واحد."),
    1035: R("شبكر", "COMPOUND-BOUNDARY", "جسر المعنى: bat يحمل التفكيك نفسه `شب` و`کور` في المصدر.", "المعنى الحيواني لا يرث حكم صفة night blind، ووقف عند حد المكونين."),
    1037: R("بحثن", "LAW-GAP", "جسر المعنى: الكشف والفصل قريب من sift، لكن ت↔ث غير مسمى.", "شاهد `بحثن` العربي منفرد ويسمي التراخي؛ لم يعوض الجسر صف الصوت ولا الشاهد الثاني."),
    1038: R("دلعك", "LAW-GAP", "نص الحدث المجمد لـ`دلعك`: محاكم الحروف؛ لا يسمي liar، ومعه غ↔ع غير مسمى.", "لم أخترع تفكيك `دروغ` و`گو` من حقل أصل فارغ؛ بقي العضو مفتوحا عند القانون."),
    1039: R("دلعك", "LAW-GAP", "نص الحدث المجمد لـ`دلعك`: محاكم الحروف؛ لا يسمي lying أو deceitful.", "فصلت الصفة عن اسم الفاعل السابق؛ غ↔ع غير مسمى ولا وراثة حكم."),
    1040: R("فرجل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`فرجل`: محاكم الحروف مع استرسال؛ لا يسمي pervasive.", "الانتشار وصف محتمل للأثر لا معنى عربي معجمي، وحقل الأصل فارغ."),
    1042: R("فرزن", "COMPOUND-BOUNDARY", "جسر المعنى: wise مصرح بمكافأته إلى `فرزان` و`ـه` بعد الصورة الوسطى.", "الجذع غائب مستقلا واللاحقة مقروءة؛ وقف الحكم عند حد البنية المصرح بها."),
    1043: R("فرزن", "COMPOUND-BOUNDARY", "جسر المعنى: wise person يحمل المكونين نفسيهما `فرزان` و`ـه`.", "فصلت اسم الشخص عن الصفة السابقة ولم يورث أحدهما حكم الآخر."),
    1044: R("جشذ", "COMPOUND-BOUNDARY", "جسر المعنى: broadness مصرح باشتقاقها من `گشاد` broad و`ـی` الاسم المجرد.", "قُرئت الصفة واللاحقة؛ لم تقارن الصورة المشتقة جذرا واحدا."),
    1045: R("سهجر", "TOOL-GAP", "جسر المعنى: black hole ظاهر، لكن /siyāh-čāle/ يحمل /y/ أسقطها الهيكل.", "أوقف الصامت الساقط الصورة قبل الحكم، ولم يخترع تفكيكا من حقل أصل فارغ."),
    1046: R("برزن", "COMPOUND-BOUNDARY", "جسر المعنى: old woman مصرح بتكوينها من `پیر` old و`زن` woman.", "قُرئ المكونان استقلالا؛ لم تختزل المرأة المسنة في جذر رباعي."),
    1047: R("هست", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`هست`: محاكم الحروف؛ لا يسمي existence أو being.", "الأصل الهندوأوروبي حاشية، وشواهد العربية لا تثبت الوجود لهذا الرسم."),
    1048: R("جرصل", "COMPOUND-BOUNDARY", "جسر المعنى: rosegarden مصرح بتكوينه من `گل` flower و`ـزار` مكان الكثرة.", "قُرئ المكونان؛ لم تقارن الحديقة المجموعة جذرا رباعيا."),
    1049: R("سلن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سلن`: انسحاب ممتد برفق؛ لا يسمي buttocks.", "شواهد العربية في الرماح، و`شرن` في الشق؛ لا مادة تحمل العضو والمعنى معا."),
    1050: R("كرزن", "COMPOUND-BOUNDARY", "جسر المعنى: evasive مصرح باشتقاقها من `گریز` flight و`ـان` لاحقة الصفة.", "قُرئ الجذع واللاحقة؛ لم يورث المركب حكم الهرب لمرشح رباعي."),
    1051: R("بزرج", "COMPOUND-BOUNDARY", "جسر المعنى: bigness مصرح باشتقاقها من `بزرگ` big و`ـی` الاسم المجرد.", "قُرئت الصفة واللاحقة؛ بقي old age حسا مستقلا داخل المدخلة ولم يوسع الحكم."),
    1052: R("ججر", "TOOL-GAP", "جسر المعنى: jaguar مثبت، لكن /jagvār/ يحمل /v/ أسقطها الهيكل.", "أوقف عطب /v/ المقارنة، ولم يعوض حقل الأصل الفارغ بمعرفة عامة."),
    1054: R("بشك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بشك`: محاكم الحروف؛ لا يسمي clothes أو clothing.", "رفضت التحليل السطحي إلى `پوش` و`ـاک`، وبقيت كسوة الجسد بلا مدار عربي."),
    1055: R("هرز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`هرز`: تسيب بالغ الرقة؛ يلامس unrestrained ولا يثبت lewd أو futile.", "شواهد العربية تسمي الموت، فلا يحمل الحدث وحده المعاني الأخلاقية للفرع."),
    1056: R("هرزق", "COMPOUND-BOUNDARY", "جسر المعنى: debauchery مصرح باشتقاقها من `هرزه` و`ـگی` الاسم المجرد.", "قُرئت الصفة واللاحقة؛ لم ترث الصورة المشتقة احتمال التسيب في الرأس."),
    1057: R("بز", "TOOL-GAP", "جسر المعنى: especially مفككة إلى `به` و`ویژه`، لكن /bawēža/ فقدت /w/.", "قُرئ المكونان ثم أوقف عطب /w/ حكم الصورة المجموعة."),
    1058: R("دملج", "LAW-GAP", "نص الحدث المجمد لـ`دملج`: محاكم الحروف؛ لا يسمي Demiurge، وژ↔ج غير مسمى.", "حقل الأصل فارغ؛ لم يعوض المصطلح من المعرفة العامة أو يبتكر صفا للصوت."),
    1059: R("شذذ", "TOOL-GAP", "جسر المعنى: thirteen مثبت، لكن /sizdah/ فقدت هاءها النهائية في الهيكل.", "حفظت صيغة three وten التاريخية حاشية، وأوقف عطب الهاء الصورة الحديثة."),
    1060: R("اهل", "OUT-OF-SCOPE", "جسر المعنى: Ahura اسم ديني أفستي بعينه، لا معنى معجميا عاما في المدخلة.", "حفظت الاسم ومصدره في التغطية، وعزلته من الحكم الجذري العام."),
    1061: R("سرد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سرد`: امتداد متتابع؛ لا يسمي genus أو taxonomic kind.", "التتابع داخل الجنس احتمال تنظيمي لا معنى المعجم، وخبر النقل الأوسط لا يسمي العربية."),
    1062: R("مردن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مردن`: محاكم الحروف؛ لا يسمي rub أو massage.", "المقارنات الهندوأوروبية حواش أصل، ولم تورث Sanskrit أو Greek معنى عربيا."),
    1063: R("ول", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`ول`: محاكم الحرفين؛ لا تسمي whale.", "المقارنة البعيدة مع English whale لا تمد شاهدا عربيا، وشواهد العربية بلا حيوان بحري."),
    1064: R("شرس", "LAW-GAP", "جسر المعنى: `شرس` العربية عسير شديد الخلاف، قريب من challenge أو struggle، لكن چ↔ش غير مسمى.", "الجسر المعجمي واعد، إلا أن القانون ناقص والتحليل السطحي غير مؤهل؛ لم يصدر أثر."),
    1065: R("شكرب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شكرب`: دخول حاد مع جمع؛ لا يسمي excellent أو wonderful.", "الشاهد العربي في اسم موضع ولجاجة متجانس آخر؛ لا يحمل جودة الفرع."),
    1066: R("جل", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`جل`: الاتساع والانكشاف؛ لا تسمي throat.", "كون الحلق مجرى مفتوحا وصف تشريحي عام، والشاهدان العربيان في العظمة لا العضو."),
    1068: R("خندق", "TOOL-GAP", "جسر المعنى: familial مفككة إلى `خانواده` family و`ـگی`، لكن /xānawādagī/ فقدت /w/.", "قُرئ المكونان ثم أوقف عطب /w/ حكم الصورة المجموعة."),
    1069: R("بج", "LAW-GAP", "جسر المعنى: empty أو hollow ظاهر، لكن چ↔ج غير مسمى.", "خبر النفخ محتمل ومحاك، لا شاهد عربي للمجوف في `بج` ولا صف صوت مكتمل."),
    1070: R("بك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بك`: محكمتا الحرفين؛ لا تسمي hollow.", "الصلة المذكورة بـ`پوچ` داخل الفرع لا تمنح العربية معنى التجويف، وشواهدها متباعدة."),
    1071: R("قرطن", "TOOL-GAP", "جسر المعنى: graviton مثبت، لكن /gerāviton/ يحمل /v/ أسقطها الهيكل.", "أوقف الصامت الساقط المصطلح الفيزيائي قبل فجوة گ↔ق وقبل أي تعويض من المعرفة العامة."),
    1072: R("جو", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جو`: محكمتا الحرفين؛ لا تسمي brave أو heroic.", "فصلت الصفة عن hero وditch، ولم تجعل الهواء شجاعة أو بطولة."),
    1073: R("جو", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جو`: محكمتا الحرفين؛ لا تسمي hero.", "اسم الشخص لا يرث حكم الصفة السابقة، وشواهد العربية في الهواء والموضع."),
    1074: R("جو", "OPEN-CANDIDATE", "جسر المعنى: العين يسمي `الجو` كل ما اطمأن من الأرض، وهو قريب من ditch.", "الشاهد الثاني المختار يثبت الهواء لا الحفرة، والحدث محاكم حرفين؛ بقي الجسر بلا رجلين معجميتين مستقلتين."),
    1075: R("كرك", "OPEN-CANDIDATE", "جسر المعنى: العربية تسمي `الكركي` طائرا، لكن لا تسمي quail.", "اتحد الحقل الحيواني وافترق النوع؛ لم يحول crane إلى سمانى."),
    1076: R("كرك", "OPEN-CANDIDATE", "جسر المعنى: العربية تسمي `الكركي` طائرا، لكن لا تسمي hen.", "فصلت الدجاجة عن quail السابق وعن طائر الكركي؛ لا توارث بين الأنواع."),
    1077: R("طلل", "OPEN-CANDIDATE", "جسر المعنى: `الطلل` أثر الدار الشاخص، وهو قريب من hall أو dwelling.", "القاعة بناء مستعمل والطلل أثر دار باق؛ مدار المكان واعد لكنه لا يساوي المعنيين معجميا."),
    1078: R("بذش", "LAW-GAP", "جسر المعنى: salvation التاريخية تلامس forgiveness، لكن ز↔ذ غير مسمى.", "الشاهد العربي منفرد ولا يسمي apology؛ بقي الصوت والمعنى غير مغلقين."),
    1079: R("شهم", "OPEN-CANDIDATE", "جسر المعنى: العربية تقول `شهمه` أي أفزعه، وهو تماس مباشر مع fear.", "الشاهدان يحملان الإفعال والفزع، لكن الحدث المجمد وجود فراغ لا الخوف؛ بقي الجسر بلا رجل الحدث."),
    1082: R("دشل", "TOOL-GAP", "جسر المعنى: difficult أو hard مثبت، لكن /došvār/ يحمل /v/ أسقطها الهيكل.", "أوقف عطب /v/ الصورة، ورفض التحليل السطحي إلى `دش` و`خوار`."),
    1083: R("جفت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جفت`: الجفاف والتباعد؛ لا يسمي pair أو mate.", "الشاهد العربي المستقل واحد وفي جمع المال، وذكر `زوج` doublet لا يورث المعنى للرسم."),
    1084: R("جفت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جفت`: الجفاف والتباعد؛ لا يسمي joined أو even.", "فصلت الصفة عن الاسم السابق؛ لم يرث أحد المتجانسين معنى الآخر."),
    1085: R("ببر", "TOOL-GAP", "جسر المعنى: fearless مصرح بتكوينه من `بیـ` without و`پروا` fear، لكن /parvā/ فقدت /v/.", "قُرئ المكونان ثم أوقف عطب /v/ حكم الصورة المجموعة."),
    1086: R("بس", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`بس`: الجفاف واليبوسة؛ لا تسمي guard أو watch.", "الحراسة دوام وانتظار، لكنهما وصفان وظيفيان لا معنى `بس` المعجمي."),
    1088: R("شم", "LAW-GAP", "جسر المعنى: smell حس مخصوص، لكنه لا يساوي meaning أو sense العام، وچ↔ش غير مسمى.", "فصلت الحاسة عن الدلالة العقلية؛ بقي القانون والمعنى ناقصين."),
    1089: R("نش", "LAW-GAP", "جسر المعنى: السبخة النشاشة تنبع من النز، وهو تماس مع wet، لكن چ↔ش غير مسمى.", "الرطوبة مشهودة في مادة واحدة والصوت ناقص؛ sticky غير مثبت ولم يصدر أثر."),
    1090: R("رم", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`رم`: تجمع رخو في الأثناء؛ يلامس herd دون أن يسميه.", "شواهد العربية في إصلاح البالي والعظم والحبل، لا جماعة الحيوان أو الناس."),
    1091: R("رخش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رخش`: طراءة لتندى الأثناء؛ لا يسمي red أو spotted.", "شواهد العربية في الحركة، والفارسية نفسها آخذة من الصغدية؛ لا لون عربي مشهود."),
    1092: R("رخش", "OUT-OF-SCOPE", "جسر المعنى: Rakhsh اسم فرس رستم بعينه، لا معنى معجميا عاما في العضو.", "حفظت الاسم وخبره الصغدي في التغطية، وعزلته من الحكم العام."),
    1093: R("رخش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رخش`: طراءة متجسمة؛ لا يسمي light أو shine.", "فصلت حس الضوء عن اللون والاسم السابقين؛ شواهد العربية في الحركة لا الإضاءة."),
    1095: R("رج", "LAW-GAP", "جسر المعنى: الاضطراب قد يصاحب anger، لكن ژ↔ج غير مسمى.", "الملازمة الجسدية لا تساوي الغضب، ولا شاهد عربي مباشر؛ بقي القانون مانعا."),
    1097: R("جو", "LAW-GAP", "نص الحدث المجمد لـ`جو`: محكمتا الحرفين؛ لا تسمي rumour أو hearsay، وچ↔ج غير مسمى.", "فصلت حس الإشاعة عن wood التالي؛ لا معنى ولا قانون مكتملان."),
    1098: R("جو", "LAW-GAP", "نص الحدث المجمد لـ`جو`: محكمتا الحرفين؛ لا تسمي wood، وچ↔ج غير مسمى.", "لم يرث الخشب حكم rumour المتجانس، وشواهد العربية في الهواء والموضع."),
    1099: R("رسن", "ROOT-TRACE", "جسر المعنى: `رسن` الفارسية rope و`الرَّسَن` العربية الحبل نفسه.", "مدار 1 مباشر: الحبل الممتد؛ أثبت العين والصحاح المعنى نفسه مع صوت كامل وحدث النفاذ بامتداد."),
    1100: R("برس", "OUT-OF-SCOPE", "جسر المعنى: Persepolis اسم مكان بعينه من Pārsa، لا معنى معجميا عاما.", "حفظت الاسم وطبقته الفارسية القديمة في التغطية، وعزلته من الحكم الجذري."),
    1101: R("سبر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سبر`: امتداد دقيق متصل؛ لا يسمي shield أو bumper.", "السبر اختبار الغور لا وقاية، وخبر الأرمنية لا يسمي العربية طرفا في النقل."),
    1102: R("جكر", "OPEN-CANDIDATE", "جسر المعنى: `جكر` العربية اللجاجة، وقد تكون صفة للفool، لكنها لا تسمي fool أو idiot.", "الصفة السلوكية لا تعريف الشخص، وشاهداها لا يثبتان الغباء."),
    1104: R("جد", "TOOL-GAP", "جسر المعنى: separation مصرح باشتقاقها من `جدا` و`ـیی`، لكن /judāyī/ فقدت /y/.", "قُرئ المكونان ثم أوقف عطب /y/ حكم الصورة المجموعة."),
    1106: R("قبق", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`قبق`: نتوء مع تجوف؛ لا يسمي partridge.", "الشاهد العربي الوحيد اسم جبل، والمقارنة اليونانية حاشية؛ لا طائر عربي مشهود."),
    1107: R("راد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`راد`: تراكم صد الشيء مع انفتاح؛ لا يسمي generous أو honest.", "شواهد العربية في الغصن الرطب والحركة، لا الجود أو الاستقامة."),
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
            if row.rank > 1023 and len(fresh) < 70:
                internal_skips.append(row.rank)
            continue
        seen.add(key)
        if row.rank <= 1023:
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
        "ساده": {791}, "ـگی": set(), "شب": {968}, "کور": {3083},
        "فرزان": set(), "ـه": {7113, 7114, 7115}, "گشاد": {3709},
        "ـی": {6328, 6329, 6330, 6331}, "پیر": {2239, 2240}, "زن": {228},
        "گل": {366, 367, 368, 369, 370}, "ـزار": {10307}, "گریز": {9043},
        "ـان": {10304, 10305, 10306}, "بزرگ": {738}, "هرزه": {5446},
        "به": {1119, 1120, 1121}, "ویژه": {3233}, "خانواده": {2773},
        "بیـ": {14756}, "پروا": {5630}, "جدا": {90, 91, 92}, "ـیی": set(),
    }
    fan_counts = {
        "ساده": 90, "ـگی": 56, "شب": 30, "کور": 40, "فرزان": 12,
        "ـه": 0, "گشاد": 36, "ـی": 0, "پیر": 40, "زن": 30,
        "گل": 80, "ـزار": 60, "گریز": 24, "ـان": 20, "بزرگ": 24,
        "هرزه": 12, "به": 20, "ویژه": 57, "خانواده": 9, "بیـ": 14,
        "پروا": 40, "جدا": 60, "ـیی": 20,
    }
    for word, expected in expected_indices.items():
        actual = {index for index, _entry in grouped.get(word, [])}
        if actual != expected:
            raise AssertionError(f"تغير جرد مكون {word}: {sorted(actual)}")
        fan = tuple(H.FAN.rank(word, H.FAN.fan(word, "persian"), "persian"))
        if len(fan) != fan_counts[word]:
            raise AssertionError(f"تغيرت مروحة المكون {word}: {len(fan)}")
    expected_raw = {
        "ساده": {840}, "ـگی": {17716}, "شب": {1026}, "کور": {3418},
        "فرزان": set(), "ـه": {8351, 8352, 8353, 8354}, "گشاد": {4144},
        "ـی": {7420, 7421, 7422, 7423, 7424}, "پیر": {2350, 2351, 2352},
        "زن": {237, 238}, "گل": {394, 395, 396, 397, 398}, "ـزار": {12679},
        "گریز": {10703, 10704}, "ـان": {12675, 12676, 12677}, "بزرگ": {784},
        "هرزه": {6401}, "به": {1191, 1192, 1193}, "ویژه": {3602},
        "خانواده": {3050}, "بیـ": {17675}, "پروا": {6623},
        "جدا": {92, 93, 94}, "ـیی": {6319},
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
        return "اكتملت أرجل الصوت والحدث والمعنى بشاهدين عربيين مستقلين؛ صدر أثر استكشافي."
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
    if review.verdict == "OUT-OF-SCOPE":
        return "العضو اسم خاص لا معنى معجميا عاما؛ حفظ في التغطية وعزل من الحكم الجذري."
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


BASE_MAKE_CARD = R38.make_card


def make_card(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit) -> str:
    card = BASE_MAKE_CARD(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit)
    card = card.replace("الجولة 38،", "الجولة 39،")
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
    return card


def validate_decisions(selected, raw_entries, decisions, ranked_by_rank, sense_map) -> None:
    if set(REVIEWS) != set(SOUND_RANKS):
        raise AssertionError("جدول المدار اليدوي لا يغطي الرتب السبعين")
    parsed = {item.row.rank for item in selected if P25.direct_from_plus(raw_entries[item.row.rank]["etymology"])}
    if parsed != PARSER_FROM_PLUS:
        raise AssertionError(f"تغيرت أسطر From X + Y التي يلتقطها المحلل: {sorted(parsed)}")
    expected_verdicts = {
        "COMPOUND-BOUNDARY": 11,
        "LAW-GAP": 14,
        "OPEN-CANDIDATE": 32,
        "OUT-OF-SCOPE": 3,
        "ROOT-TRACE": 1,
        "TOOL-GAP": 9,
    }
    if Counter(review.verdict for review in REVIEWS.values()) != Counter(expected_verdicts):
        raise AssertionError(f"تغير توزيع الأحكام اليدوي: {Counter(review.verdict for review in REVIEWS.values())}")
    if {rank for rank, review in REVIEWS.items() if review.verdict == "ROOT-TRACE"} != {1099}:
        raise AssertionError("تغير الأثر الجذري لرسن")
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
            "OPEN-CANDIDATE", "OUT-OF-SCOPE", "ROOT-TRACE", "NUCLEUS-TRACE",
        } and not complete:
            raise AssertionError(f"حكم بمسار ناقص في الرتبة {row.rank}: {decision.verdict}")
        if decision.verdict in {"ROOT-TRACE", "NUCLEUS-TRACE"}:
            joined = " ".join(quote for _source, quote in witnesses)
            if coverage < 2 or "الحبل" not in joined or H.event_line(decision.candidate).startswith("لا حدث"):
                raise AssertionError(f"أثر بلا حدث وشاهدين مباشرين في الرتبة {row.rank}")
        if row.rank in EXACT_DECOMPOSITIONS and decision.verdict not in {"COMPOUND-BOUNDARY", "TOOL-GAP"}:
            raise AssertionError(f"تفكيك مباشر بلا حد مركب أو عطب أداة في الرتبة {row.rank}")
        if row.rank in TOOL_GAPS and decision.verdict != "TOOL-GAP":
            raise AssertionError(f"هيكل ناقص بلا TOOL-GAP في الرتبة {row.rank}")
        if row.rank in LAW_GAPS and decision.verdict != "LAW-GAP":
            raise AssertionError(f"مسار ناقص بلا LAW-GAP في الرتبة {row.rank}")
        if row.rank in OUT_OF_SCOPE and decision.verdict != "OUT-OF-SCOPE":
            raise AssertionError(f"اسم خاص بلا OUT-OF-SCOPE في الرتبة {row.rank}")
        if not REVIEWS[row.rank].meaning_path.startswith(("جسر المعنى:", "نص الحدث المجمد", "نص النواة المجمدة")):
            raise AssertionError(f"طريق المعنى غير مسمى في الرتبة {row.rank}")


def validate_text(selected, texts, prior_pairs) -> None:
    if len(selected) != 70 or BATCH_SIZES != (35, 35):
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = re.findall(r"^### (WO-B-R39-SOUND-\d{5}):", joined, re.MULTILINE)
    if headings != [item.heading for item in selected]:
        raise AssertionError("معرفات الجولة 39 لا تطابق النافذة")
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
    if "الحكم (استكشاف): ROOT-TRACE" not in texts[SOUND_RANKS.index(1099)]:
        raise AssertionError("غاب الأثر الجذري في بطاقة رسن")


def report_section(selected, decisions, sizes, stats) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    batches = (selected[:35], selected[35:])
    lines = [f"<!-- {MARKER}:START -->", ""]
    previous = 1023
    for number, batch in enumerate(batches, 1):
        lo = 0 if number == 1 else 35
        hi = lo + len(batch)
        counts = Counter(decision.verdict for decision in decisions[lo:hi])
        distribution = "؛ ".join(f"{key}={counts[key]}" for key in sorted(counts))
        batch_skips = [rank for rank in stats["skipped"] if previous < rank <= batch[-1].row.rank]
        skipped = ", ".join(map(str, batch_skips)) or "0"
        lines.extend([
            f"## الجولة التاسعة والثلاثون، دفعة sound_only رقم {number}", "",
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
    traces = [item.heading for item, decision in zip(selected, decisions) if decision.verdict in {"ROOT-TRACE", "NUCLEUS-TRACE"}]
    transmissions = [item.heading for item, decision in zip(selected, decisions) if decision.verdict in {"SEMITIC-SOURCE-TRANSMISSION", "LOANWORD-NON-ARABIC-TO-ARABIC"}]
    lines.extend([
        "## حصيلة الجولة التاسعة والثلاثين", "",
        f"- حمل `persian.md` مرة واحدة؛ أزواج WO-B المقروءة={stats['pair_count']}؛ المتجاوز داخل النافذة={', '.join(map(str, stats['skipped']))}.",
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- نطاق الصوت الجديد: الرتب 1024-1107 بعد WO-B-R38-SOUND-01023، مع تجاوز 1027 و1032 و1033 و1036 و1041 و1053 و1067 و1080 و1081 و1087 و1094 و1096 و1103 و1105 لأنها مقروءة.",
        f"- الأثر الجذري الاستكشافي الجديد: {', '.join(traces)}؛ S01099 يطابق `رسن` rope بالحبل العربي وشاهدين؛ لم تفعل طبقة البرهان ولم تنشر أرقاما.",
        f"- نتائج النقل المصفاة: {', '.join(transmissions) or 'لا نتيجة صادرة'}؛ حفظت أخبار النقل والاقتراض حواشي ولم توسع الاتجاه.",
        "- التفكيك النهائي المؤهل: S01028، S01034، S01035، S01042، S01043، S01044، S01046، S01048، S01050، S01051، S01056، S01057، S01068، S01085، S01104؛ قرئت المكونات مستقلة، ووقفت S01057 وS01068 وS01085 وS01104 عند عطب صوتي.",
        "- التحليلات غير المؤهلة: S01054، S01059، S01064، S01082؛ حفظت طبقتها التاريخية أو وسمها السطحي ولم تحول إلى تفكيك نهائي.",
        "- أعطاب الأداة: S01045، S01052، S01057، S01059، S01068، S01071، S01082، S01085، S01104؛ لم تعوض الصوامت المنطوقة الساقطة.",
        "- فجوات القانون: S01030، S01031، S01037، S01038، S01039، S01058، S01064، S01069، S01078، S01088، S01089، S01095، S01097، S01098.",
        "- الأسماء الخاصة المعزولة: S01060 Ahura، S01092 فرس رستم، S01100 Persepolis؛ حفظت في التغطية ولم تحسب آثارا.",
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
    headings = re.findall(r"^### (WO-B-R39-SOUND-\d{5}):", match.group(1), re.MULTILINE)
    expected = [f"WO-B-R39-SOUND-{rank:05d}" for rank in SOUND_RANKS]
    if headings != expected:
        raise AssertionError("مقطع الجولة 39 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(DONE_LINE):
        raise AssertionError("سطر DONE39 ليس خاتمة التقرير")


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
        print("ROUND39 ALREADY PRESENT AND VALID")
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
        "## الجولة التاسعة والثلاثون: متابعة حوض sound_only (2026-08-27)\n\n"
        "- النطاق: 70 عضوا طازجا بعد WO-B-R38-SOUND-01023؛ من الرتبة 1024 إلى 1107 مع تجاوز 1027 و1032 و1033 و1036 و1041 و1053 و1067 و1080 و1081 و1087 و1094 و1096 و1103 و1105 لأنها مقروءة؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ طريق المعنى مسمى، والمدار اليدوي حاسم، والأصداء مفصولة عن الأثر المحكم.\n"
        "- لقطة الأحواض: قرئت ملفات nucleus-sweep-*.json التسعة الحالية v18 من القرص؛ ثبتت بصماتها وعداداتها قبل الانتخاب.\n\n"
        + "\n".join(texts[:35])
        + "\n## الدفعة الثانية: متابعة sound_only بعد الرتبة 1064\n\n"
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
    print("ROUND39 READY")
    print("NUCLEUS_V18_FILES", len(NUCLEUS_SNAPSHOT), "SHA256_AND_COUNTS_OK")
    print("NUCLEUS_V18_TOTALS", "BOTH=14496", "SOUND_ONLY=106818")
    print("SKIPPED", ",".join(map(str, stats["skipped"])))
    print("BATCHES", *BATCH_SIZES, "SELECTED", len(selected))
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("TRACES", " ".join(f"S{rank:05d}" for rank in sorted(rank for rank, review in REVIEWS.items() if review.verdict in {"ROOT-TRACE", "NUCLEUS-TRACE"})))
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
    print("ROUND39 WRITTEN")
    print(DONE_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
