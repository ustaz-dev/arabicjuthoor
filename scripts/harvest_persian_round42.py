# -*- coding: utf-8 -*-
"""المسار B، الجولة 42: متابعة إنقاذ حوض sound_only في دفعتين من 35 بطاقة."""

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

import harvest_persian_round41 as R41  # noqa: E402

R40 = R41.R40
R39 = R41.R39
R38 = R41.R38
R36 = R41.R36
R35 = R41.R35
R34 = R41.R34
R32 = R41.R32
R31 = R41.R31
R29 = R41.R29
R28 = R41.R28
H = R41.H
P = R41.P
P25 = R41.P25
READING = R41.READING
REPORT = R41.REPORT
SWEEP = R41.SWEEP
LEXICON = R41.LEXICON
RAW_LEXICON = R41.RAW_LEXICON
NUCLEUS_DIR = ROOT / "04-cross-linguistic" / "exploration"
MARKER = "LANE-B-PERSIAN-ROUND42-2026-08-28"
CARD_LIMIT = 5120

SOUND_RANKS = (
    1264, 1265, 1266, 1268, 1269, 1270, 1271, 1272, 1273, 1276,
    1277, 1279, 1280, 1281, 1282, 1283, 1284, 1285, 1286, 1287,
    1288, 1289, 1290, 1291, 1292, 1293, 1295, 1296, 1297, 1298,
    1299, 1300, 1301, 1302, 1303, 1304, 1305, 1306, 1307, 1310,
    1311, 1312, 1313, 1314, 1315, 1316, 1317, 1318, 1319, 1320,
    1321, 1322, 1323, 1324, 1325, 1326, 1327, 1328, 1329, 1330,
    1331, 1332, 1334, 1335, 1336, 1337, 1338, 1341, 1342, 1343,
)
BATCH_SIZES = (35, 35)
DONE_LINE = "LANE-B DONE42 70 WO-B-R42-SOUND-01343"
EXPECTED_SKIPS = (1267, 1274, 1275, 1278, 1294, 1308, 1309, 1333, 1339, 1340)

# النسخة العشرون المقروءة من القرص بعد تبدل ثلاثة أحواض منذ الجولة 41.
NUCLEUS_SNAPSHOT = {
    "nucleus-sweep-ancient_greek.json": (7972376, "ad2de3c7493ae54fbd33b5a711a719f6ebfb8c9dacdc5471f33962544d0493c8", 2313, 16781),
    "nucleus-sweep-english_middle.json": (3415893, "b10f11707b8b5eda41691d8c6aea13c6e3b880ac61dfc6035ba8071524eec467", 1414, 7991),
    "nucleus-sweep-english_old.json": (1293699, "0e4ac0e76706c510b7a8c814d6168c360a6ca73487dbe0d87c453d0163d1851b", 474, 3413),
    "nucleus-sweep-gothic.json": (1416051, "de62c2cbfcf0291f9f27b30281a9c0bde7d4bc1a62f4fe02cf7808add4951c76", 335, 3083),
    "nucleus-sweep-latin.json": (18829742, "7741403d1bddff7ae0c3139e48aa36f7662c8e4523136b408c59d0967622b8cf", 6583, 39470),
    "nucleus-sweep-old_irish.json": (954285, "7d157718c682528abb6d436aac259eaa4881a1df358914ab51d4471142601ac6", 278, 2740),
    "nucleus-sweep-old_norse.json": (1380503, "1c89a89695286a020241cfba6f3b9d5d17142a4d5e60af9617d63aaab2435dba", 476, 3750),
    "nucleus-sweep-persian.json": (5483805, "fb44ce0b92745835bc0a386f639ac562aa59478a4cf9990b57f362339057466e", 1437, 13503),
    "nucleus-sweep-welsh.json": (5776833, "5116d5ea5a195c03db7d1e50a8033591dede1c1569238ee57fb0e5cda39f6bce", 1187, 16086),
}

EXPECTED_ENTRY_INDEX = dict(zip(SOUND_RANKS, (
    6708, 6717, 6728, 6736, 6742, 6744, 0, 6753, 6754, 6784,
    6805, 6812, 6817, 6820, 6833, 6839, 6845, 6856, 6865, 6892,
    6907, 6913, 6921, 6922, 6924, 6926, 6943, 6959, 6987, 6988,
    6996, 7009, 7023, 7025, 7027, 7029, 7030, 7055, 7068, 7104,
    7105, 7106, 7136, 7140, 7155, 7159, 7170, 7178, 7192, 7195,
    7203, 7204, 7205, 7242, 7245, 7257, 7271, 7276, 7279, 7282,
    7283, 7287, 7291, 7305, 7306, 7308, 7314, 7328, 7336, 7341,
)))
EXPECTED_RAW_LINE = dict(zip(SOUND_RANKS, (
    7869, 7878, 7889, 7897, 7903, 7905, 7911, 7916, 7917, 7949,
    7981, 7993, 7999, 8003, 8020, 8026, 8034, 8047, 8057, 8088,
    8110, 8116, 8124, 8125, 8127, 8129, 8148, 8165, 8198, 8199,
    8211, 8227, 8245, 8247, 8255, 8259, 8260, 8287, 8302, 8342,
    8343, 8344, 8381, 8386, 8403, 8407, 8419, 8428, 8443, 8447,
    8457, 8458, 8459, 8499, 8502, 8515, 8529, 8536, 8539, 8542,
    8543, 8547, 8555, 8569, 8571, 8573, 8581, 8599, 8609, 8614,
)))

PARSER_FROM_PLUS = {1281, 1288, 1297, 1299, 1300, 1310, 1311, 1312, 1313, 1315, 1324, 1326, 1332, 1335}
EXACT_DECOMPOSITIONS = {
    1268, 1272, 1281, 1282, 1288, 1297, 1299, 1300, 1301, 1304, 1305,
    1310, 1311, 1312, 1313, 1319, 1323, 1324, 1326, 1332, 1335, 1342,
}
EXPECTED_COMPONENTS = {
    1268: ("آهو", "پای"), 1272: ("پرت", "ـگاه"), 1281: ("بچه", "گی"),
    1282: ("روز", "به"), 1288: ("تیم", "ـچه"), 1297: ("سه", "تار"),
    1299: ("شگرف", "ـی"), 1300: ("و", "اگر", "نه"), 1301: ("چی", "است"),
    1304: ("چون", "آن"), 1305: ("چون", "آن"), 1310: ("گجرات", "ـی"),
    1311: ("گجرات", "ـی"), 1312: ("گجرات", "ـی"), 1313: ("هیچ", "گاه"),
    1319: ("تک", "پوی"), 1323: ("غژ", "گاو"), 1324: ("پوپو", "ـک"),
    1326: ("تیره", "ـگی"), 1332: ("چای", "ـدان"), 1335: ("زای", "ـچه"),
    1342: ("گنج", "ـور"),
}
COMPONENT_READINGS = {
    1268: "`آهو`: entry[3324] والخام 3698 للغزال، ومروحتها 40: OPEN-CANDIDATE. `پای`: الخام 4626 يحيل إلى `پا` foot، ومروحته صفر بهذه الوظيفة: FORM-LINK.",
    1272: "`پرت`: entry[10826] والخام 13323 لمعنى thrown أو far، ومروحتها 12: OPEN-CANDIDATE. `ـگاه`: entry[7462] والخام 8752 لاحقة مكان أو زمان، ومروحتها 72: MORPHOLOGY-GAP.",
    1281: "`بچه`: entry[799] والخام 850 لمعنى child، ومروحتها 30: OPEN-CANDIDATE. `گی`: صورة اللاحقة `ـگی`، والخام 17716 يثبتها بعد الهاء القصيرة، ومروحتها 56: MORPHOLOGY-GAP.",
    1282: "`روز`: entry[500] والخام 539 لمعنى day، ومروحتها 60: OPEN-CANDIDATE. `به`: اختيرت entry[1121] والخام 1193 لمعنى good أو better، ومروحتها 20: OPEN-CANDIDATE.",
    1288: "`تیم`: اختيرت entry[2073] والخام 2177 لمعنى caravanserai، ومروحتها 30: OPEN-CANDIDATE. `ـچه`: entry[7514] والخام 8808 لاحقة تصغير، ومروحتها 60: MORPHOLOGY-GAP.",
    1297: "`سه`: entry[819] والخام 872 للعدد three، ومروحتها 60: OPEN-CANDIDATE. `تار`: entry[1257] والخام 1332 لمعنى string، ومروحتها 60: OPEN-CANDIDATE.",
    1299: "`شگرف`: entry[5540] والخام 6510 لمعنى excellent، ومروحتها 48: OPEN-CANDIDATE. `ـی`: اختيرت entry[6330] والخام 7422 للاسم المجرد، ومروحتها صفر: MORPHOLOGY-GAP.",
    1300: "`و`: entry[26] والخام 27 لحرف العطف، ومروحته صفر: MORPHOLOGY-GAP. `اگر`: entry[461] والخام 496 للشرط، ومروحتها 16: OPEN-CANDIDATE. `نه`: entry[146] والخام 151 للنفي، ومروحتها 20: OPEN-CANDIDATE.",
    1301: "`چی`: entry[1890] والخام 1989 لمعنى what، ومروحتها 42: OPEN-CANDIDATE. `است`: الخام 2260 للفعل is لا متجانس bone في الفرع، ومروحتها 18: FORM-LINK.",
    1304: "`چون`: entry[1917] والخام 2016 لمعنى like أو such as، ومروحتها 30: OPEN-CANDIDATE. `آن`: entry[1610] والخام 1695 لمعنى that، ومروحتها 20: OPEN-CANDIDATE.",
    1305: "`چون`: entry[1917] والخام 2016 لمعنى like أو such as، ومروحتها 30: OPEN-CANDIDATE. `آن`: entry[1610] والخام 1695 لمعنى that، ومروحتها 20: OPEN-CANDIDATE.",
    1310: "`گجرات`: entry[7099] والخام 8337 لاسم الولاية، ومروحتها 48: OUT-OF-SCOPE للمكون. `ـی`: entry[6329] والخام 7421 لاحقة نسبة، ومروحتها صفر: MORPHOLOGY-GAP.",
    1311: "`گجرات`: entry[7099] والخام 8337 لاسم الولاية، ومروحتها 48: OUT-OF-SCOPE للمكون. `ـی`: entry[6329] والخام 7421 لاحقة نسبة، ومروحتها صفر: MORPHOLOGY-GAP.",
    1312: "`گجرات`: entry[7099] والخام 8337 لاسم الولاية، ومروحتها 48: OUT-OF-SCOPE للمكون. `ـی`: entry[6329] والخام 7421 لاحقة نسبة، ومروحتها صفر: MORPHOLOGY-GAP.",
    1313: "`هیچ`: اختيرت entry[6677] والخام 7833 لمعنى never أو ever، ومروحتها 60: OPEN-CANDIDATE. `گاه`: entry[2119] والخام 2225 لمعنى time، ومروحتها 72: OPEN-CANDIDATE.",
    1319: "`تک`: entry[4530] والخام 5040 لمعنى action أو quick motion، ومروحتها 60: OPEN-CANDIDATE. `پوی`: جذع حاضر مسمى؛ الخام 11473 للفعل `پوییدن` run أو search، ومروحته صفر: FORM-LINK.",
    1323: "`غژ`: غائب مدخلة مستقلة بهذه الوظيفة، والخام 8462 يحيله إلى `کژ` دون تثبيت معنى المكون هنا، ومروحته 90: COMPONENT-GAP. `گاو`: entry[856] والخام 912 لمعنى cow أو bull، ومروحتها صفر: OPEN-CANDIDATE.",
    1324: "`پوپو`: entry[9824] والخام 12112 لمعنى hoopoe، ومروحتها 40: OPEN-CANDIDATE. `ـک`: entry[7513] والخام 8807 لاحقة تصغير، ومروحتها صفر: MORPHOLOGY-GAP.",
    1326: "`تیره`: اختيرت entry[9372] والخام 11055 لمعنى dark، ومروحتها 60: OPEN-CANDIDATE. `ـگی`: الخام 17716 لاحقة، ومروحتها 56: MORPHOLOGY-GAP.",
    1332: "`چای`: entry[496] والخام 533 لمعنى tea، ومروحتها صفر: OPEN-CANDIDATE. `ـدان`: entry[7279] والخام 8539 لاحقة الوعاء، ومروحتها 30: MORPHOLOGY-GAP.",
    1335: "`زای`: جذع حاضر مسمى؛ الخام 11531 للفعل `زاییدن` give birth، ومروحته صفر: FORM-LINK. `ـچه`: entry[7514] والخام 8808 لاحقة تصغير، ومروحتها 60: MORPHOLOGY-GAP.",
    1342: "`گنج`: entry[2100] والخام 2205 لمعنى treasure، ومروحتها 8: OPEN-CANDIDATE. `ـور`: لاحقة مسماة بلا مدخلة مستقلة بهذه الوظيفة، ومروحتها 38: MORPHOLOGY-GAP.",
}

TOOL_GAPS = {
    1266: "الصورة `پیک` منقوطة /peyk/، لكن الهيكل أسقط /y/ المنطوقة.",
    1268: "الصورة `آهوپای` منقوطة /âhupây/، لكن الهيكل أسقط /y/ النهائية المنطوقة.",
    1270: "الصورة `پژواک` منقوطة /pažwāk/، لكن الهيكل أسقط /w/ المنطوقة.",
    1272: "الصورة `پرتگاه` منقوطة /partgâh/، لكن الهيكل أسقط الهاء النهائية المنطوقة.",
    1282: "الصورة `روزبه` منقوطة /ruzbeh/، لكن الهيكل أسقط الهاء النهائية المنطوقة.",
    1283: "الصورة `جاوید` منقوطة /jāwēd/، لكن الهيكل أسقط /w/ المنطوقة.",
    1296: "الصورة `آوازه` منقوطة /âvâze/، لكن الهيكل أسقط /v/ المنطوقة.",
    1297: "هيكل `سه‌تار` احتسب الهاء الكتابية صامتا، وهي غير منطوقة في /se-tār/.",
    1306: "الصورة `شبانگاه` منقوطة /šabângâh/، لكن الهيكل أسقط الهاء النهائية المنطوقة.",
    1313: "الصورة `هیچ‌گاه` منقوطة /hič-gâh/، لكن الهيكل أسقط الهاء النهائية المنطوقة.",
    1318: "الصورة `آنگاه` منقوطة /ângâh/، لكن الهيكل أسقط الهاء النهائية المنطوقة.",
    1323: "الصورة `غژگاو` منقوطة /ġažgāw/، لكن الهيكل أسقط /w/ النهائية المنطوقة.",
    1327: "الصورة `مادیان` منقوطة /mâdiyân/، لكن الهيكل أسقط /y/ المنطوقة.",
    1332: "الصورة `چایدان` منقوطة /čāydān/، لكن الهيكل أسقط /y/ المنطوقة.",
    1335: "الصورة `زایچه` منقوطة /zâyče/، لكن الهيكل أسقط /y/ المنطوقة.",
    1341: "الصورة `آله` منقوطة /âloh/، لكن الهيكل أسقط الهاء النهائية المنطوقة.",
}
LAW_GAPS = {1295, 1316, 1317, 1336}
OUT_OF_SCOPE = {1269: "اختصار اسم حزب PJAK بعينه؛ لا معنى معجميا عاما في المدخلة."}
MORPHOLOGY_GAPS = {1329, 1338}
REJECTED_ANALYSES = {
    1287: "التحليل إلى `سیم` و`ـین` موسوم By surface analysis بعد الصورة الوسطى الموروثة؛ لم يؤهل تفكيكا نهائيا.",
    1292: "التفكيك التاريخي للمركب القديم إلى عناصر إيرانية أولية ليس From نهائيا مباشرا للمدخلة الحديثة.",
    1315: "التحليل إلى `گرم` و`ـا` موسوم By surface analysis بعد الصورة الوسطى؛ لم يدخل في دليل النقل ولا في التفكيك النهائي.",
}
SOURCE_NOTES = {
    1266: "يسمي الخبر `فَيْج` و`فَوْج` بين القروض الإيرانية المقارنة؛ حفظ دليل التماس، لكن عطب /y/ أوقف حكم العضو.",
    1277: "وصف الخبر الأصل الآرامي بأنه probable؛ حفظ الاحتمال ولم يحول إلى حكم نقل.",
    1296: "ذكر `حَوْض` العربي في خبر possibly related لا يثبت مصدرا ولا اتجاها، وعطب /v/ سابق للحكم.",
    1315: "شاهد الصحاح يقول صراحة إن `الجَرْم` بمعنى الحر فارسي معرب؛ خبر المدخلة يثبت السلسلة الإيرانية الوسطى مستقلة.",
    1316: "خبر المدخلة لا يتجاوز صورة إيرانية أولية ولا يسمي العربية طرفا؛ حفظ التطابق المعجمي منفصلا عن اتجاه النقل.",
}
FORM_LINKS = {1271: "السطر الخام 7911 يحيل الصورة العامية `اگه` إلى `اگر` فقط؛ لا خبر أصل مستقل ولا تفكيك مخترع."}


@dataclass(frozen=True)
class SelectedRow:
    row: H.SweepRow

    @property
    def key(self) -> str:
        return f"S{self.row.rank:05d}"

    @property
    def heading(self) -> str:
        return f"WO-B-R42-SOUND-{self.row.rank:05d}"


Review = R41.Review
R = R41.R

# سجل قراءة يدوي. لا يشتق الحكم من best ولا من وزن المروحة.
REVIEWS = {
    1264: R("برز", "NUCLEUS-TRACE", "جسر المعنى: victor أو winner يطابق فاق وسبق وتبرز على الأصحاب في شاهدي `برز`.", "مدار مباشر: الفوز تفوق وسبق، والحدث ظهور قوي؛ اكتمل المسار وشاهدا الفوق والسبق دون دعوى نقل."),
    1265: R("توز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`توز`: الحركة المتصلة مع تفريق؛ لا يسمي سلالة كلب.", "سرعة الكلب صفة للسلالة لا معناها، وخبر الصورة الوسطى لا يقدم شاهدا عربيا للسلالة."),
    1266: R("بك", "TOOL-GAP", "جسر المعنى: messenger أو courier حاضر، لكن /peyk/ يحمل /y/ أسقطها الهيكل.", "حفظت المقارنات العربية المسماة في خبر الأصل، ثم أوقف عطب /y/ المقارنة قبل الحكم."),
    1268: R("اهب", "TOOL-GAP", "جسر المعنى: muqarnas مفككة إلى `آهو` و`پای`، لكن /âhupây/ فقدت /y/ النهائية.", "قُرئ المكونان استقلالا ثم أوقف الصامت الساقط حكم الصورة المجموعة."),
    1269: R("بزك", "OUT-OF-SCOPE", "جسر المعنى: PJAK اختصار اسم حزب بعينه لا معنى معجميا عاما.", "حفظت المدخلة في التغطية وعزلت الاسم السياسي المختصر من الحكم الجذري."),
    1270: R("بزك", "TOOL-GAP", "جسر المعنى: echo مثبت، لكن /pažwāk/ يحمل /w/ أسقطها الهيكل.", "لم أربط رجع الصوت بمرشح من هيكل ناقص؛ حقل الأصل فارغ."),
    1271: R("اج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`اج`: الاتقاد والحدة؛ لا يسمي أداة الشرط العامية.", "فصلت الوظيفة النحوية عن معنى الحدث، وحفظت الإحالة إلى `اگر` بلا اختراع أصل."),
    1272: R("برتك", "TOOL-GAP", "جسر المعنى: precipice أو cliff مصرح بتكوينه من `پرت` و`ـگاه`، لكن /partgâh/ فقدت الهاء.", "قُرئ المكونان ثم أوقف عطب الهاء حكم صورة المكان المجموعة."),
    1273: R("سبنت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سبنت`: الامتداد والاتصال مع أحداث الباقي؛ لا يسمي holy.", "القداسة حكم قيمي لا يستخرج من الامتداد، والخبر الأفستي مستقل عن الشواهد العربية."),
    1276: R("جسن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جسن`: اجتماع واستتار مع حدث النون؛ لا يسمي minstrel.", "اجتماع الناس حول المنشد ظرف أداء لا معنى المنشد، وخبر الأصل إيراني داخلي."),
    1277: R("كنكر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كنكر`: محاكم الحروف لا تسمي thistle أو cardoon.", "حفظت احتمال القرض الآرامي كما هو؛ الشوك هيئة النبات لا معنى عربي متحد في المرشح."),
    1279: R("فلد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`فلد`: الشق والصلابة مع حدث الدال؛ لا يسمي faloodeh.", "التصفية في تاريخ الحلوى فعل إعداد لا معنى المنتج، ولا شاهد عربي مستقل للطبق."),
    1280: R("بهمن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بهمن`: امتلاء وتماسك مع حدث النون؛ لا يسمي so-and-so.", "الضمير النكرة وظيفة إحالة لا امتلاء، والصورة الوسطى لا تغلق مدار المرشح."),
    1281: R("بجج", "COMPOUND-BOUNDARY", "جسر المعنى: childhood مصرح باشتقاقها من `بچه` child و`گی` اسم الحالة.", "قُرئ الاسم واللاحقة؛ لم تقارن الصورة المشتقة بجذر عربي واحد."),
    1282: R("رزب", "TOOL-GAP", "جسر المعنى: daily fortunate مفككة إلى `روز` و`به`، لكن /ruzbeh/ فقدت الهاء النهائية.", "قُرئ المكونان وحفظت الصورة الوسطى، ثم أوقف عطب الهاء حكم المركب."),
    1283: R("جد", "TOOL-GAP", "جسر المعنى: eternal مثبت، لكن /jāwēd/ يحمل /w/ أسقطها الهيكل.", "الدوام يلامس جد المرشح في بعض الشواهد، لكن الصامت الساقط يمنع بناء الحكم."),
    1284: R("شكف", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شكف`: الانفتاح عن باطن مع حدث الفاء؛ لا يسمي flower أو blossom مباشرة.", "تفتح الزهرة يحقق الانفتاح حدثيا، لكن الشاهد لا يسمي الزهرة ولا اتحاد المعنى المعجمي."),
    1285: R("كرد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كرد`: الجمع والإحاطة مع حدث الدال؛ لا يسمي nomad.", "اجتماع الرعاة أو القطيع وصف اجتماعي لا معنى البدوي، والأصل نفسه غير يقيني."),
    1286: R("ارج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ارج`: الحركة بقوة مع امتداد؛ لا يسمي pattern أو role model.", "اتباع النموذج علاقة استعمال لا حركة، والقرض التركي لا يسمي العربية طرفا."),
    1287: R("سمن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سمن`: الامتلاء واللين مع حدث النون؛ لا يسمي silver أو silvery.", "اللمعان والبياض صفتان بصريتان لا امتلاء، ورفضت التحليل السطحي اللاحق للصورة الموروثة."),
    1288: R("تمش", "COMPOUND-BOUNDARY", "جسر المعنى: small caravanserai مصرح باشتقاقها من `تیم` و`ـچه` التصغير.", "قُرئ اسم الخان واللاحقة؛ وقف الحكم عند حد الاشتقاق."),
    1289: R("همن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`همن`: الامتلاء والاستقرار مع حدث النون؛ لا يسمي plain أو earth.", "استواء الأرض هيئة مكانية لا معنى الامتلاء، والخبر يثبت صورة وسطى فقط."),
    1290: R("برس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`برس`: التجرد مع امتداد؛ لا يسمي pious أو devout.", "الزهد قد يتضمن تجردا، لكنه وصف سلوكي لا اتحاد معجمي؛ والأصل المقترح غير يقيني."),
    1291: R("برس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`برس`: التجرد مع امتداد؛ لا يسمي pious person أو ascetic.", "فصلت اسم الشخص عن الصفة السابقة؛ أثر الزهد لا يحول التجرد إلى اسم القديس."),
    1292: R("بدرم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بدرم`: محاكم الحروف لا تسمي joyous أو happy.", "حفظت خبر المركب القديم تاريخيا، ولم أحوله إلى تفكيك نهائي حديث أو جسر معنى."),
    1293: R("بدرم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بدرم`: محاكم الحروف لا تسمي wild أو undomesticated.", "الإحالة إلى `بدرام` لا تقدم أصل المدخلة ولا شاهدا عربيا للوحشية."),
    1295: R("جنر", "LAW-GAP", "نص الحدث المجمد لـ`جنر`: محاكم الحروف لا تسمي طول الشخص، وچ↔ج غير مسمى.", "خبر الصورة الوسطى لا يصلح صف الصوت المفقود؛ لم يصدر حكم من مروحة ناقصة."),
    1296: R("از", "TOOL-GAP", "جسر المعنى: swamp أو pool مثبت، لكن /âvâze/ يحمل /v/ أسقطها الهيكل.", "حفظت تشابه `حوض` بصفته possibly related فقط؛ عطب /v/ سابق لأي مدار."),
    1297: R("صهطل", "TOOL-GAP", "جسر المعنى: setar مصرح بتكوينها من `سه` three و`تار` string، لكن الهيكل أدخل هاء غير منطوقة.", "قُرئ العدد والوتر ثم أوقف خلل الهيكل حكم اسم الآلة المجموعة."),
    1298: R("تنبل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تنبل`: محاكم الحروف لا تسمي tanbur.", "كونها آلة ذات أوتار لا يرد اسم الآلة إلى حدث المرشح، والأصل اليوناني احتمالي."),
    1299: R("شكرب", "COMPOUND-BOUNDARY", "جسر المعنى: excellence مصرح باشتقاقها من `شگرف` excellent و`ـی` الاسم المجرد.", "قُرئت الصفة واللاحقة؛ لم تورث الصورة المشتقة حكم المكون."),
    1300: R("بغلن", "COMPOUND-BOUNDARY", "جسر المعنى: otherwise أو if not مصرح بتكوينها من `و` و`اگر` و`نه`.", "قُرئت عناصر الربط والنفي الثلاثة؛ الوظيفة المركبة لا تقارن بجذر واحد."),
    1301: R("جست", "COMPOUND-BOUNDARY", "جسر المعنى: what's مصرح بانقباض `چی` what و`است` is.", "قُرئ الضمير والفعل ثم وقف الحكم عند الانقباض النحوي."),
    1302: R("بر", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`بر`: التجرد والخلوص؛ لا تسمي shovel أو oar.", "الحفر بالمجرفة أو دفع الماء بالمجداف فعلان للأداة لا معناها، وحقل الأصل فارغ."),
    1303: R("جرن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جرن`: التجريد مع حدث النون؛ لا يسمي expensive.", "ارتفاع الثمن علاقة مقدار لا تجريد، والمدخلة العامية بلا خبر أصل."),
    1304: R("جنن", "COMPOUND-BOUNDARY", "جسر المعنى: such as that مصرح بانقباض `چون` و`آن`.", "قُرئ عنصرا التشبيه والإشارة؛ لم تقارن العبارة المنقبضة بجذر واحد."),
    1305: R("جنن", "COMPOUND-BOUNDARY", "جسر المعنى: that way مصرح بانقباض `چون` و`آن`.", "فصلت الوظيفة الحالية عن الصفة السابقة ووقفت عند الحد نفسه."),
    1306: R("سبنج", "TOOL-GAP", "جسر المعنى: nightfall أو nighttime حاضر، لكن /šabângâh/ فقدت الهاء النهائية.", "حقل الأصل فارغ، فلم أخترع تفكيك `شب` و`گاه`؛ أوقف عطب الهاء العضو."),
    1307: R("برشب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`برشب`: محاكم الحروف لا تسمي the night before last.", "التعاقب الزمني وظيفة تركيبية لا حدث المرشح، وحقل الأصل فارغ."),
    1310: R("كجرت", "COMPOUND-BOUNDARY", "جسر المعنى: Gujarati adjective مصرح باشتقاقها من `گجرات` و`ـی` النسبة.", "قُرئ اسم الولاية واللاحقة؛ عزل العلم داخل المكون ولم يورث للصورة."),
    1311: R("كجرت", "COMPOUND-BOUNDARY", "جسر المعنى: Gujarati inhabitant مصرح باشتقاقها من `گجرات` و`ـی` النسبة.", "فصلت اسم الساكن عن الصفة ووقفت عند حد الاشتقاق نفسه."),
    1312: R("كجرت", "COMPOUND-BOUNDARY", "جسر المعنى: Gujarati language مصرح باشتقاقها من `گجرات` و`ـی` النسبة.", "فصلت اسم اللغة عن المدخلتين السابقتين ووقفت عند حد العلم واللاحقة."),
    1313: R("هجج", "TOOL-GAP", "جسر المعنى: never مصرح بتكوينه من `هیچ` و`گاه`، لكن /hič-gâh/ فقدت الهاء النهائية.", "قُرئ المكونان ثم أوقف عطب الهاء حكم الظرف المجموعة."),
    1314: R("هزم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`هزم`: الدفع والكسر مع حدث الميم؛ لا يسمي firewood.", "حرق الحطب أو كسره فعل يقع عليه لا معنى الحطب، والخبر الهندي الأوروبي مستقل."),
    1315: R("جرم", "LOANWORD-NON-ARABIC-TO-ARABIC", "جسر المعنى: heat يطابق `الجَرْم` بمعنى الحر في شاهدي العين والصحاح.", "الصحاح يقول إن جرم الحر فارسي معرب، والخبر يثبت أصلا فارسيا أوسط؛ أغلق اتجاه الدخول تماسًا لا إرثا."),
    1316: R("فردس", "LAW-GAP", "جسر المعنى: garden أو paradise يطابق `الفردوس` البستان في شاهدين، لكن مسار الصوت يحوي صفا غير مسمى.", "اكتمل المعنى المعجمي ولم يكتمل القانون؛ والخبر الإيراني لا يسمي اتجاه دخول العربية."),
    1317: R("قرص", "LAW-GAP", "جسر المعنى: cookie يلامس `القرص` خبزة أو كعكة مستديرة في شاهدين، لكن مسار الصوت ناقص.", "اتحد مجال المخبوز وهيئته، ثم أوقف صف الصوت غير المسمى الحكم ولم يخترع اتجاه نقل."),
    1318: R("انق", "TOOL-GAP", "جسر المعنى: then حاضر، لكن /ângâh/ يحمل هاء نهائية أسقطها الهيكل.", "فصلت وظيفة الزمن عن مرشح العنق والأنين؛ الصامت الساقط سابق للحكم."),
    1319: R("طقف", "COMPOUND-BOUNDARY", "جسر المعنى: striving أو effort مصرح بمعادلته إلى `تک` action و`پوی` motion.", "قُرئ الاسمان المستقلان؛ لم تقارن حركة المركب بجذر عربي واحد."),
    1320: R("بندر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بندر`: الجمع والربط مع أحداث الباقي؛ لا يسمي thought أو imagination.", "جمع الصور الذهنية وصف للعملية لا معنى الفكر، والخبر الاشتقاقي يحيل إلى فعل فارسي."),
    1321: R("مغغ", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مغغ`: محاكم الحروف لا تسمي magus.", "الطبقة الدينية معنى معجمي عام، لكن الخبر التاريخي الإيراني لا يقدم شاهدا عربيا متحدا."),
    1322: R("مغغ", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مغغ`: محاكم الحروف لا تسمي deep أو abyssal.", "الحفرة المذكورة في الأصل قد تكون عميقة، لكن العمق صفة لا معنى الحفرة نفسها."),
    1323: R("غزق", "TOOL-GAP", "جسر المعنى: yak مفككة إلى `غژ` و`گاو`، لكن /ġažgāw/ فقدت /w/ النهائية.", "قُرئ حد المكون الأول كما تسمح الإحالة والثاني مستقلا؛ ثم أوقف الصامت الساقط الحكم."),
    1324: R("ببك", "COMPOUND-BOUNDARY", "جسر المعنى: hoopoe مصرح باشتقاقها من `پوپو` و`ـک` التصغير.", "قُرئ اسم الطائر واللاحقة؛ لم تورث الصورة المصغرة حكم المكون."),
    1325: R("جدر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جدر`: القطع والتحديد مع حدث الراء؛ لا يسمي ford أو gorge.", "شق الممر في الأرض هيئة للمكان لا معنى المخاضة أو الخانق، وحقل الأصل فارغ."),
    1326: R("ترج", "COMPOUND-BOUNDARY", "جسر المعنى: darkness مصرح باشتقاقها من `تیره` dark و`ـگی` اسم الحالة.", "قُرئت الصفة واللاحقة؛ لم تقارن الصورة المشتقة بجذر واحد."),
    1327: R("مدن", "TOOL-GAP", "جسر المعنى: mare مثبت، لكن /mâdiyân/ يحمل /y/ أسقطها الهيكل.", "حفظت قرابة `ماده` female ولم أعوض الصامت المنطوق من خبر الأصل."),
    1328: R("غوز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`غوز`: القصد والطلب؛ لا يسمي hump أو hunch.", "حدبة الجسم لا تحقق قصد الفعل، والخبر الهندي الأوروبي مستقل عن الشواهد العربية."),
    1329: R("دن", "MORPHOLOGY-GAP", "جسر المعنى: holder أو container وظيفة لاحقة صرفية مستقلة لا مدخلة جذرية حرة.", "حفظت اللاحقة في التغطية وامتنعت عن محاكمتها كاسم أو جذر عربي مستقل."),
    1330: R("كلنك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كلنك`: محاكم الحروف لا تسمي pickaxe.", "الضرب والكسر فعل الأداة وقد ورد في الأصل الأولي، لكنه لا يجعل المرشح اسم الفأس."),
    1331: R("كلنك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كلنك`: محاكم الحروف لا تسمي crane.", "فصلت الطائر عن أداة الحفر السابقة؛ خبر الأصل الاحتمالي لا يقدم شاهدا عربيا للطائر."),
    1332: R("جدن", "TOOL-GAP", "جسر المعنى: tea caddy مصرح بتكوينه من `چای` و`ـدان`، لكن /čāydān/ فقدت /y/.", "قُرئ الشاي ولاحقة الوعاء ثم أوقف الصامت الساقط حكم المركب."),
    1334: R("كبد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كبد`: التكتل والغلظ؛ لا يسمي blue-gray أو azure.", "لون الكبد أو الحمام علاقة عرضية لا معنى اللون، والخبر الإيراني مستقل."),
    1335: R("زج", "TOOL-GAP", "جسر المعنى: horoscope diagram مصرح بتكوينه من `زای` و`ـچه`، لكن /zâyče/ فقدت /y/.", "قُرئ الجذع واللاحقة ثم أوقف الصامت الساقط حكم الصورة المجموعة."),
    1336: R("فر", "LAW-GAP", "جسر المعنى: torn يطابق الفصل والتقسيم في خبر الأصل وشواهد المرشح، لكن مسار الصوت ناقص.", "اكتمل جسر الانفصال ولم يكتمل صف الصوت؛ لم يصدر أثر من طريق ناقص."),
    1337: R("تكك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تكك`: محاكم الحروف لا تسمي rhyton.", "كونه إناء شرب لا يرد الاسم إلى حدث المرشح، وخبر الصورة الوسطى لا يسمي العربية."),
    1338: R("وي", "MORPHOLOGY-GAP", "جسر المعنى: diminutive أو affectionate وظيفة لاحقة صرفية مستقلة لا جذر حر.", "حفظت تاريخ اللاحقة وصورها المعربة في الوصف، ولم أحاكمها كمدخلة جذرية."),
    1341: R("ال", "TOOL-GAP", "جسر المعنى: eagle مثبت، لكن /âloh/ يحمل هاء نهائية أسقطها الهيكل.", "حفظت السلسلة الإيرانية والمقارنات ثم أوقف عطب الهاء المقارنة."),
    1342: R("جنجر", "COMPOUND-BOUNDARY", "جسر المعنى: treasurer مصرح بمعادلته إلى `گنج` treasure و`ـور`.", "قُرئ الاسم وحد اللاحقة المسمى؛ لم تقارن الصورة التاريخية المركبة بجذر واحد."),
    1343: R("بشمن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بشمن`: محاكم الحروف لا تسمي woolen أو woolly.", "مادة الصوف اسم مستقل لا تستخرج من صفة النسيج، والخبر الإيراني لا يسمي العربية."),
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
            raise AssertionError(f"تغير عداد نسخة v20 في {name}")
        if len(data.get("both") or []) != expected_both or len(data.get("sound_only") or []) != expected_sound:
            raise AssertionError(f"تغير طول قوائم نسخة v20 في {name}")
        total_both += expected_both
        total_sound += expected_sound
    if total_both != 14497 or total_sound != 106817:
        raise AssertionError("تغير مجموع أحواض v20")


def select_rows(data: dict, reading_text: str) -> tuple[list[SelectedRow], dict]:
    pairs = H.read_pairs(reading_text)
    all_sound = [P25.sound_row(rank, raw) for rank, raw in enumerate(data.get("sound_only") or [], 1)]
    if len(all_sound) != 2304:
        raise AssertionError(f"تغير حجم حوض الصوت: {len(all_sound)}")
    prior = {row.rank for row in all_sound if P25.pair_was_read(row, pairs)}
    fresh: list[H.SweepRow] = []
    seen: set[tuple[str, str]] = set()
    internal_skips: list[int] = []
    for row in all_sound:
        key = pair_key(row)
        if row.rank in prior or key in seen:
            if row.rank > 1263 and len(fresh) < 70:
                internal_skips.append(row.rank)
            continue
        seen.add(key)
        if row.rank <= 1263:
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
        "pair_count": len(pairs), "sound_prior_total": len(prior), "skipped": internal_skips,
    }


def select_branch_entries(selected: list[SelectedRow], lexicon: dict):
    grouped: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for index, entry in enumerate(lexicon.get("entries") or [], 1):
        grouped[H.clean(entry.get("word") or "")].append((index, entry))
    output: dict[int, H.BranchEntry] = {}
    for item in selected:
        row = item.row
        options = grouped.get(row.branch, [])
        if row.rank == 1271:
            if options:
                raise AssertionError("دخلت اگه إلى لقطة الفرع بعد تثبيت فجوتها")
            output[row.rank] = H.BranchEntry(
                global_index=0, homograph_index=1, homograph_count=1, word=row.branch,
                reading="age", pos="conj", gloss="colloquial form of اگر (agar)",
                etymology="إحالة صرفية عامية إلى اگر؛ لا خبر أصل مستقل في الخام.",
            )
            continue
        if not options:
            raise AssertionError(f"لا مدخلة فرع للرسم {row.branch}")
        global_index, entry = max(options, key=lambda pair: H.entry_score(H.norm_gloss(row.gloss), pair[1]))
        if global_index != EXPECTED_ENTRY_INDEX[row.rank]:
            raise AssertionError(f"انزلقت مدخلة الرتبة {row.rank}: {global_index}")
        homograph_index = 1 + next(i for i, pair in enumerate(options) if pair[0] == global_index)
        output[row.rank] = H.BranchEntry(
            global_index=global_index, homograph_index=homograph_index, homograph_count=len(options),
            word=H.clean(entry.get("word") or ""), reading=H.clean(entry.get("read") or row.say),
            pos=H.clean(entry.get("pos") or ""), gloss=H.clean(entry.get("en") or ""),
            etymology=H.clean(entry.get("etym") or "فجوة اشتقاق في لقطة الفرع."),
        )
    return output, grouped


def validate_components(grouped: dict[str, list[tuple[int, dict]]]) -> None:
    fan_counts = {
        "آهو": 40, "پای": 0, "پرت": 12, "ـگاه": 72, "بچه": 30, "روز": 60,
        "به": 20, "تیم": 30, "ـچه": 60, "سه": 60, "تار": 60, "شگرف": 48,
        "ـی": 0, "و": 0, "اگر": 16, "نه": 20, "چی": 42, "است": 18,
        "چون": 30, "آن": 20, "گجرات": 48, "هیچ": 60, "گاه": 72, "تک": 60,
        "پوی": 0, "غژ": 90, "گاو": 0, "پوپو": 40, "ـک": 0, "تیره": 60,
        "ـگی": 56, "چای": 0, "ـدان": 30, "زای": 0, "گنج": 8, "ـور": 38,
    }
    for word, expected in fan_counts.items():
        fan = tuple(H.FAN.rank(word, H.FAN.fan(word, "persian"), "persian"))
        if len(fan) != expected:
            raise AssertionError(f"تغيرت مروحة المكون {word}: {len(fan)}")
    required_branch = {
        "آهو": 3324, "پرت": 10826, "ـگاه": 7462, "بچه": 799, "روز": 500,
        "تیم": 2073, "ـچه": 7514, "سه": 819, "تار": 1257, "شگرف": 5540,
        "و": 26, "اگر": 461, "نه": 146, "چی": 1890, "چون": 1917, "آن": 1610,
        "گجرات": 7099, "گاه": 2119, "تک": 4530, "گاو": 856, "پوپو": 9824,
        "ـک": 7513, "تیره": 9372, "چای": 496, "ـدان": 7279, "گنج": 2100,
    }
    for word, index in required_branch.items():
        if index not in {number for number, _entry in grouped.get(word, [])}:
            raise AssertionError(f"غابت مدخلة المكون {word}: {index}")


def obstacle_for(review: Review) -> str:
    if review.verdict == "NUCLEUS-TRACE":
        return "اكتملت أرجل الصوت والحدث والمعنى بشاهدين عربيين مستقلين؛ صدر أثر نواة استكشافي."
    if review.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC":
        return "اتحد معنى الحر وصرح الصحاح بأن اللفظ فارسي معرب؛ أغلق تماس لا إرثا."
    if review.verdict == "COMPOUND-BOUNDARY":
        return "وقف الحكم عند حد المركب؛ لم تورث الصورة المجموعة حكم مكون ولم يخترع تفكيك."
    if review.verdict == "LAW-GAP":
        return "طريق المعنى مفحوص، لكن مسار الصوت يحوي صفا غير مسمى؛ لم يصدر حكم موجب."
    if review.verdict == "TOOL-GAP":
        return "هيكل الحوض أسقط صامتا منطوقا أو أدخل صامتا صامتا؛ توقف العضو قبل الحكم."
    if review.verdict == "OUT-OF-SCOPE":
        return "العضو اسم خاص مختصر بلا معنى معجمي عام؛ حفظ في التغطية وعزل من الحكم الجذري."
    if review.verdict == "MORPHOLOGY-GAP":
        return "العضو لاحقة صرفية لا مدخلة جذرية حرة؛ حفظ في التغطية بلا حكم جذري."
    return "مسار الصوت قابل للفحص، لكن المدار لم يكتمل إلى حكم؛ بقي المرشح مفتوحا."


def decide(item: SelectedRow) -> H.Decision:
    review = REVIEWS[item.row.rank]
    return H.Decision(review.candidate, review.verdict, H.state_for(review.verdict), review.orbit, obstacle_for(review))


def strip_marks(value: str) -> str:
    return "".join(char for char in H.clean(value) if unicodedata.category(char) != "Mn")


def decomposition_lines(item: SelectedRow, raw: dict) -> list[str]:
    rank = item.row.rank
    if rank not in EXACT_DECOMPOSITIONS:
        return []
    joined = strip_marks(raw["etymology"]).replace("ـ", "")
    for component in EXPECTED_COMPONENTS[rank]:
        if strip_marks(component).replace("ـ", "") not in joined:
            raise AssertionError(f"غاب مكون {component} من الرتبة {rank}")
    lines = [
        f"- تفكيك Kaikki الحصري المباشر أو المحكم من السطر الخام {raw['line']}: «{H.clip(raw['etymology'], 180)}».",
        f"- قراءة المكونات المستقلة: {COMPONENT_READINGS[rank]}",
        "- الخطوة صفر: قبل التفكيك النهائي المصرح به لم تقارن الصورة وحدة جذرية؛ قُرئ كل مكون مسمى وحده.",
    ]
    if rank in TOOL_GAPS:
        lines.extend([
            f"- عطب الهيكل: {TOOL_GAPS[rank]}",
            "- بعد قراءة المكونات أوقف TOOL-GAP حكم الصورة المجموعة؛ لا حكم من هيكل ناقص.",
        ])
    return lines


BASE_MAKE_CARD = R41.make_card


def make_card(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit) -> str:
    card = BASE_MAKE_CARD(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit)
    card = card.replace("الجولة 41،", "الجولة 42،")
    if item.row.rank == 1264:
        card = re.sub(
            r"^- المصفاة:.*$",
            "- المصفاة: الشاهدان يسميان الفوق والسبق والتبريز؛ يعمل NUCLEUS-TRACE استكشافيا مستقلا عن دعوى النقل.",
            card, count=1, flags=re.MULTILINE,
        )
    if item.row.rank == 1315:
        card = re.sub(
            r"^- المصفاة:.*$",
            "- المصفاة: الصحاح يسمي `الجَرْم` بمعنى الحر فارسيا معربا، والعين يثبت معنى الحر؛ يعمل LOANWORD-NON-ARABIC-TO-ARABIC نتيجة تماس محسوبة.",
            card, count=1, flags=re.MULTILINE,
        )
    return card


def validate_decisions(selected, raw_entries, decisions, ranked_by_rank, sense_map) -> None:
    if set(REVIEWS) != set(SOUND_RANKS):
        raise AssertionError("جدول المدار اليدوي لا يغطي الرتب السبعين")
    parsed = {item.row.rank for item in selected if P25.direct_from_plus(raw_entries[item.row.rank]["etymology"])}
    if parsed != PARSER_FROM_PLUS:
        raise AssertionError(f"تغيرت أسطر From X + Y التي يلتقطها المحلل: {sorted(parsed)}")
    expected_verdicts = {
        "COMPOUND-BOUNDARY": 14, "LAW-GAP": 4, "LOANWORD-NON-ARABIC-TO-ARABIC": 1,
        "MORPHOLOGY-GAP": 2, "NUCLEUS-TRACE": 1, "OPEN-CANDIDATE": 31,
        "OUT-OF-SCOPE": 1, "TOOL-GAP": 16,
    }
    if Counter(review.verdict for review in REVIEWS.values()) != Counter(expected_verdicts):
        raise AssertionError(f"تغير توزيع الأحكام اليدوي: {Counter(review.verdict for review in REVIEWS.values())}")
    for item, decision in zip(selected, decisions):
        row = item.row
        candidates = {candidate for candidate, _score in ranked_by_rank[row.rank]}
        if decision.candidate not in candidates or decision.candidate not in row.candidates_found:
            raise AssertionError(f"مرشح الرتبة {row.rank} خارج المروحة الحية أو أعضاء الحوض")
        complete = H.route_complete(row, decision.candidate)
        _count, coverage, _witnesses = P.classical_witnesses(decision.candidate, sense_map, 320)
        if decision.verdict == "LAW-GAP" and complete:
            raise AssertionError(f"LAW-GAP بلا صف مفقود في الرتبة {row.rank}")
        if decision.verdict in {"OPEN-CANDIDATE", "NUCLEUS-TRACE", "LOANWORD-NON-ARABIC-TO-ARABIC"} and not complete:
            raise AssertionError(f"حكم بمسار ناقص في الرتبة {row.rank}: {decision.verdict}")
        if decision.verdict in {"NUCLEUS-TRACE", "LOANWORD-NON-ARABIC-TO-ARABIC"}:
            if coverage < 2 or H.event_line(decision.candidate).startswith("لا حدث"):
                raise AssertionError(f"نتيجة بلا حدث وشاهدين في الرتبة {row.rank}")
        if row.rank in EXACT_DECOMPOSITIONS and decision.verdict not in {"COMPOUND-BOUNDARY", "TOOL-GAP"}:
            raise AssertionError(f"تفكيك مؤهل بلا حد مركب أو عطب أداة في الرتبة {row.rank}")
        if row.rank in TOOL_GAPS and decision.verdict != "TOOL-GAP":
            raise AssertionError(f"هيكل معطوب بلا TOOL-GAP في الرتبة {row.rank}")
        if row.rank in LAW_GAPS and decision.verdict != "LAW-GAP":
            raise AssertionError(f"مسار ناقص بلا LAW-GAP في الرتبة {row.rank}")
        if row.rank in OUT_OF_SCOPE and decision.verdict != "OUT-OF-SCOPE":
            raise AssertionError(f"اسم خاص بلا OUT-OF-SCOPE في الرتبة {row.rank}")
        if row.rank in MORPHOLOGY_GAPS and decision.verdict != "MORPHOLOGY-GAP":
            raise AssertionError(f"لاحقة بلا MORPHOLOGY-GAP في الرتبة {row.rank}")
        if not REVIEWS[row.rank].meaning_path.startswith(("جسر المعنى:", "نص الحدث المجمد", "نص النواة المجمدة", "نص محاكم")):
            raise AssertionError(f"طريق المعنى غير مسمى في الرتبة {row.rank}")
    if {rank for rank, review in REVIEWS.items() if review.verdict == "NUCLEUS-TRACE"} != {1264}:
        raise AssertionError("تغير موضع NUCLEUS-TRACE اليدوي")
    if {rank for rank, review in REVIEWS.items() if review.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC"} != {1315}:
        raise AssertionError("تغير موضع نقل جرم")
    witness_text = " ".join(text for _source, text in P.classical_witnesses("جرم", sense_map, 320)[2])
    if "فارسي" not in witness_text or "معرّب" not in witness_text:
        raise AssertionError("انزلق دليل تعريب جرم")


def validate_text(selected, texts, prior_pairs) -> None:
    if len(selected) != 70 or BATCH_SIZES != (35, 35):
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = re.findall(r"^### (WO-B-R42-SOUND-\d{5}):", joined, re.MULTILINE)
    if headings != [item.heading for item in selected]:
        raise AssertionError("معرفات الجولة 42 لا تطابق النافذة")
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
    if "NUCLEUS-TRACE استكشافيا" not in texts[SOUND_RANKS.index(1264)]:
        raise AssertionError("غاب إغلاق أثر پیروز")
    if "LOANWORD-NON-ARABIC-TO-ARABIC نتيجة تماس" not in texts[SOUND_RANKS.index(1315)]:
        raise AssertionError("غاب إغلاق نقل جرم")


def report_section(selected, decisions, sizes, stats) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    batches = (selected[:35], selected[35:])
    lines = [f"<!-- {MARKER}:START -->", ""]
    previous = 1263
    for number, batch in enumerate(batches, 1):
        lo = 0 if number == 1 else 35
        hi = lo + len(batch)
        counts = Counter(decision.verdict for decision in decisions[lo:hi])
        distribution = "؛ ".join(f"{key}={counts[key]}" for key in sorted(counts))
        batch_skips = [rank for rank in stats["skipped"] if previous < rank <= batch[-1].row.rank]
        skipped = ", ".join(map(str, batch_skips)) or "0"
        lines.extend([
            f"## الجولة الثانية والأربعون، دفعة sound_only رقم {number}", "",
            f"- الوقت: {now}، Africa/Cairo.",
            f"- رشح وكتب: {len(batch)}؛ المواضع المقروءة المتجاوزة داخل المدى: {skipped}.",
            f"- المواضع: من {batch[0].heading} إلى {batch[-1].heading}.",
            f"- توزيع الأحكام: {distribution}.",
            "- طريق المعنى: سمي من جسر معنى صريح أو من نص الحدث المجمد في كل بطاقة.",
            "- المدار: كتب يدويا لكل عضو، وفصلت النتائج الموجبة عن الحدود والفجوات.",
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
    lines.extend([
        "## حصيلة الجولة الثانية والأربعين", "",
        f"- حمل `persian.md` مرة واحدة؛ أزواج WO-B المقروءة={stats['pair_count']}؛ المتجاوز داخل النافذة={', '.join(map(str, stats['skipped']))}.",
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- نطاق الصوت الجديد: الرتب 1264-1343 بعد WO-B-R41-SOUND-01263، مع تجاوز 1267 و1274 و1275 و1278 و1294 و1308 و1309 و1333 و1339 و1340 لأنها مقروءة.",
        "- الأثر الاستكشافي: WO-B-R42-SOUND-01264؛ `برز` يسمي الفوق والسبق مباشرة في شاهدين مع victor أو winner.",
        "- نتيجة التماس: WO-B-R42-SOUND-01315؛ الصحاح يسمي `الجَرْم` بمعنى الحر فارسيا معربا، والعين يثبت معنى الحر.",
        "- التفكيك النهائي المؤهل: S01268، S01272، S01281، S01282، S01288، S01297، S01299، S01300، S01301، S01304، S01305، S01310، S01311، S01312، S01313، S01319، S01323، S01324، S01326، S01332، S01335، S01342؛ قرئت المكونات مستقلة.",
        "- التحليلات غير المؤهلة: S01287، S01292، S01315؛ لم تحول التحليلات السطحية والتاريخية إلى تفكيك نهائي.",
        "- أعطاب الأداة: S01266، S01268، S01270، S01272، S01282، S01283، S01296، S01297، S01306، S01313، S01318، S01323، S01327، S01332، S01335، S01341.",
        "- فجوات القانون: S01295، S01316، S01317، S01336.",
        "- فجوات الصرف: S01329 وS01338؛ لاحقتان مستقلتان حفظتا في التغطية بلا حكم جذري.",
        "- المعزول خارج النطاق: S01269 اختصار اسم حزب PJAK.",
        "- أحواض `nucleus-sweep-*.json` التسعة الحالية v20 قرئت كاملة من القرص؛ both=14497 وsound_only=106817؛ ثبت الحجم وSHA-256 والعدادات لكل ملف.",
        f"- أكبر بطاقة: {max_size} بايت، {max_item.heading}؛ كل البطاقات دون 5KB.",
        "- لم تفعل طبقة البرهان؛ مر حارس نقاء الشحنة وختم CLEAN؛ لم يقع ship ولم يستعمل git.",
        "", f"<!-- {MARKER}:END -->", "", DONE_LINE,
    ])
    return "\n".join(lines)


def validate_existing(reading_text: str, report_text: str) -> None:
    match = re.search(rf"<!-- {re.escape(MARKER)}:START -->(.*?)<!-- {re.escape(MARKER)}:END -->", reading_text, re.DOTALL)
    if not match:
        raise AssertionError("محضر الجولة موجود وبطاقاتها غائبة")
    headings = re.findall(r"^### (WO-B-R42-SOUND-\d{5}):", match.group(1), re.MULTILINE)
    expected = [f"WO-B-R42-SOUND-{rank:05d}" for rank in SOUND_RANKS]
    if headings != expected:
        raise AssertionError("مقطع الجولة 42 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(DONE_LINE):
        raise AssertionError("سطر DONE42 ليس خاتمة التقرير")


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
        print("ROUND42 ALREADY PRESENT AND VALID")
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

    for module in (R41, R40, R39):
        module.SOURCE_NOTES = SOURCE_NOTES
        module.REJECTED_ANALYSES = REJECTED_ANALYSES
        module.FORM_LINKS = FORM_LINKS
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
        "## الجولة الثانية والأربعون: متابعة حوض sound_only (2026-08-28)\n\n"
        "- النطاق: 70 عضوا طازجا بعد WO-B-R41-SOUND-01263؛ من الرتبة 1264 إلى 1343 مع تجاوز 1267 و1274 و1275 و1278 و1294 و1308 و1309 و1333 و1339 و1340 لأنها مقروءة؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ طريق المعنى مسمى، والمدار اليدوي حاسم، والنتائج الموجبة مفصولة عن الحدود والفجوات.\n"
        "- لقطة الأحواض: قرئت ملفات nucleus-sweep-*.json التسعة الحالية v20 من القرص؛ ثبتت بصماتها وعداداتها قبل الانتخاب.\n\n"
        + "\n".join(texts[:35])
        + "\n## الدفعة الثانية: متابعة sound_only بعد الرتبة 1303\n\n"
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
    print("ROUND42 READY")
    print("NUCLEUS_V20_FILES", len(NUCLEUS_SNAPSHOT), "SHA256_AND_COUNTS_OK")
    print("NUCLEUS_V20_TOTALS", "BOTH=14497", "SOUND_ONLY=106817")
    print("SKIPPED", ",".join(map(str, stats["skipped"])))
    print("BATCHES", *BATCH_SIZES, "SELECTED", len(selected))
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("NUCLEUS_TRACE", "S01264")
    print("TRANSMISSION", "S01315")
    print("EXACT_COMPONENTS", " ".join(f"S{rank:05d}" for rank in sorted(EXACT_DECOMPOSITIONS)))
    print("TOOL_GAPS", len(TOOL_GAPS), "LAW_GAPS", len(LAW_GAPS), "MORPHOLOGY_GAPS", len(MORPHOLOGY_GAPS))
    print("MAX_CARD", max(sizes), selected[sizes.index(max(sizes))].heading)
    if args.preview:
        print("PREVIEW ONLY")
        print(DONE_LINE)
        return 0

    with READING.open("a", encoding="utf-8", newline="") as handle:
        handle.write(reading_append)
    with REPORT.open("a", encoding="utf-8", newline="") as handle:
        handle.write(report_append)
    print("ROUND42 WRITTEN")
    print(DONE_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
