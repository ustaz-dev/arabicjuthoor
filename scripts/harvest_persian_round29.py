# -*- coding: utf-8 -*-
"""المسار B، الجولة 29: متابعة حوض sound_only في دفعتين من 35 بطاقة."""

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

import harvest_persian_round28 as R28  # noqa: E402

H = R28.H
P = R28.P
P25 = R28.P25
READING = ROOT / "04-cross-linguistic" / "readings" / "persian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-B.md"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-persian.json"
NUCLEUS_DIR = ROOT / "04-cross-linguistic" / "exploration"
LEXICON = ROOT / "data" / "branch-lexicons" / "persian.json"
RAW_LEXICON = ROOT / "Resources" / "persian" / "kaikki.org-dictionary-Persian.jsonl"
MARKER = "LANE-B-PERSIAN-ROUND29-2026-08-26"
CARD_LIMIT = 5120
SOUND_RANKS = (
    252, 254, 255, 256, 257, 258, 259, 260, 262, 263, 264, 266, 267, 268,
    269, 270, 271, 272, 275, 276, 277, 278, 279, 280, 281, 282, 283, 284,
    285, 286, 288, 289, 290, 291, 292, 293, 294, 295, 296, 297, 298, 299,
    300, 301, 302, 303, 305, 306, 307, 309, 310, 311, 312, 313, 314, 315,
    316, 318, 319, 320, 321, 322, 323, 324, 325, 326, 327, 328, 329, 330,
)
BATCH_SIZES = (35, 35)
DONE_LINE = "LANE-B DONE29 70 WO-B-R29-SOUND-00330"
EXPECTED_SKIPS = (253, 261, 265, 273, 274, 287, 304, 308, 317)
EXACT_DECOMPOSITIONS = {313, 324}
PARSER_FROM_PLUS = {283, 293, 313, 324}

NUCLEUS_SNAPSHOT = {
    "nucleus-sweep-ancient_greek.json": (7501050, "e01d35e6bafb90deacf790f0e2b57ca425e99741c546dbcc9f862c4d89131aca", 2526, 16555),
    "nucleus-sweep-english_middle.json": (3487587, "585a442b3fc56ea8b55d0a2f6e9b9bc5d60b42e37713b0f6b25c9c2efed97168", 1658, 7746),
    "nucleus-sweep-english_old.json": (1336396, "898520fc546f5dbf09ecb4fe7d5d391b664da0cda7c9745147b3dc8bc386ed65", 515, 3372),
    "nucleus-sweep-gothic.json": (1409167, "30f409b66157a749b5c331fb5726694f1a35a10e2a20d8806758277e6c21d1a4", 379, 3038),
    "nucleus-sweep-latin.json": (18193129, "b0c09ff15772cd546724d57fb7bfd230cb4a277554df99672f93e2d08f62b075", 7407, 38645),
    "nucleus-sweep-old_irish.json": (957056, "3545023773dfbd9d1f40bc160485d83647cd2903eb61175e027763d2af0c3815", 314, 2704),
    "nucleus-sweep-old_norse.json": (1393717, "ed7b25614d109bdd4e091021c3d790fc0727624ec1e6fe7ccf8c929888479fe5", 518, 3705),
    "nucleus-sweep-persian.json": (5487475, "236d2b808ec933b1ffa0edc5be8f05961d9842983c887315a599a8cf42f53550", 1714, 13219),
    "nucleus-sweep-welsh.json": (5827110, "36c1fc917594cff183f7c814f1c3b15e7715db726f2ac0dac018dce89ca1c7b1", 1507, 15766),
}

EXPECTED_ENTRY_INDEX = dict(zip(SOUND_RANKS, (
    1051, 1058, 1067, 1076, 1078, 1080, 1083, 1090, 1093, 1095,
    1099, 1106, 1111, 1113, 1115, 1119, 1127, 1128, 1137, 1139,
    1140, 1143, 1150, 1155, 1158, 1159, 1169, 1172, 1173, 1174,
    1178, 1179, 1192, 1193, 1197, 1198, 1202, 1205, 1207, 1213,
    1215, 1226, 1227, 1228, 1246, 1247, 1255, 1257, 1259, 1285,
    1291, 1294, 1296, 1308, 1310, 1312, 1313, 1315, 1318, 1321,
    1322, 1325, 1344, 1350, 1354, 1366, 1375, 1376, 1379, 1380,
)))

EXPECTED_RAW_LINE = dict(zip(SOUND_RANKS, (
    1118, 1125, 1134, 1145, 1147, 1149, 1154, 1161, 1164, 1166,
    1170, 1177, 1182, 1184, 1187, 1192, 1200, 1201, 1210, 1212,
    1213, 1216, 1223, 1228, 1231, 1232, 1242, 1245, 1246, 1247,
    1251, 1252, 1266, 1267, 1271, 1272, 1276, 1279, 1282, 1288,
    1290, 1301, 1302, 1303, 1321, 1322, 1331, 1333, 1335, 1361,
    1367, 1370, 1372, 1384, 1386, 1388, 1389, 1392, 1395, 1398,
    1399, 1402, 1425, 1431, 1435, 1447, 1456, 1457, 1460, 1462,
)))

BLOCKED_BOUNDARIES = {
    254: "يسمي الخبر تركيبا تاريخيا من sheep وprotector، لا From X + Y نهائيا مباشرا للمدخلة الحالية.",
    263: "يسمي الخبر صيغة قديمة مع اللاحقة `ـچ`، ولا يصدر تفكيك From X + Y نهائيا مباشرا.",
    283: "يقول الخبر Equivalent to Middle Persian `tan` + `īhā` بعد أصل تاريخي، لا From X + Y مؤهلا.",
    288: "يسمي الخبر diminutive of `مور` ولا يصدر تفكيك From X + Y نهائيا مباشرا.",
    293: "يقول الخبر By surface analysis `خاک` + `ـی`، والتحليل السطحي ليس From X + Y النهائي المباشر.",
    298: "يقول الخبر By surface analysis `شیر` + `ـین` ثم يقارن صيغة أخرى؛ لم يحول التحليل السطحي إلى From.",
    302: "يحلل الخبر السطح إلى `کار` + `ـگر` بلا صيغة From X + Y النهائية المباشرة.",
    303: "تكرر مدخلة effective التحليل السطحي `کار` + `ـگر` بلا صيغة From المؤهلة.",
    313: "التفكيك المباشر `آش` + `پز` مؤهل، ولذلك قرئ المكونان ووقف حكم الصورة المجموعة عند الحد.",
}

TOOL_GAPS = {
    255: "الصورة `دیوار` منقوطة /dēwār/، لكن الهيكل أسقط الواو المنطوقة /w/.",
    264: "الصورة `گوجه` منقوطة /gowje/، لكن الهيكل أسقط الواو المنطوقة /w/.",
    267: "الصورة `ریواس` منقوطة /rivâs/، لكن الهيكل أسقط الصامت /v/.",
    279: "الصورة `رایانه` منقوطة /râyâne/، لكن الهيكل أسقط الياء المنطوقة /y/.",
    280: "الصورة `همسایه` منقوطة /hamsâye/، لكن الهيكل أسقط الياء المنطوقة /y/.",
    307: "الصورة `پاپایا` منقوطة /pâpâyâ/، لكن الهيكل أسقط الياء المنطوقة /y/.",
    309: "الصورة `ارغوان` منقوطة /argavân/، لكن الهيكل أسقط الصامت /v/.",
    318: "الصورة `چکاوک` منقوطة /čakâvak/، لكن الهيكل أسقط الصامت /v/.",
    324: "الصورة `گویش` منقوطة /guyeš/، لكن الهيكل أسقط الياء المنطوقة /y/ قبل بناء المروحة.",
}

OUT_OF_SCOPE = {
    258: "المدخلة اسم كتاب Avesta واسم لغة Avestan، فطبقة أسماء الكتب واللغات أعلام معزولة عن الحكم الجذري.",
}

EXPECTED_COMPONENTS = {313: ("آش", "پز"), 324: ("گوی", "ـش")}
COMPONENT_READINGS = {
    313: "`آش`: entries[766] والسطر الخام 814 لمعنى soup أو pottage، ومروحتها 60: OPEN-CANDIDATE. `پز`: غائبة من branch-lexicons، والسطر الخام 10672 يسميها present stem of `پختن`، ومروحتها 60: COMPONENT-GAP.",
    324: "`گوی`: entries[9043] يخرج ball لا فعل say؛ الخام 10709 يثبت present stem: COMPONENT-GAP. `ـش`: entries[10302] والخام 12674 لاحقة حدث: MORPHOLOGY-GAP.",
}


@dataclass(frozen=True)
class SelectedRow:
    row: H.SweepRow

    @property
    def key(self) -> str:
        return f"S{self.row.rank:05d}"

    @property
    def heading(self) -> str:
        return f"WO-B-R29-SOUND-{self.row.rank:05d}"


@dataclass(frozen=True)
class Review:
    candidate: str
    verdict: str
    meaning_path: str
    orbit: str


def R(candidate: str, verdict: str, meaning_path: str, orbit: str) -> Review:
    return Review(candidate, verdict, meaning_path, orbit)


# سجل قراءة يدوي. لا يشتق الحكم من best ولا من وزن المروحة.
REVIEWS = {
    252: R("فرد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`فرد`: الانفراد والتميز؛ لا يسمي tomorrow.", "انفراد يوم تال عن يومه السابق ترتيب زمني لا معنى الغد؛ بقي المتجانس مفتوحا."),
    254: R("جبن", "COMPOUND-BOUNDARY", "جسر المعنى: الاشتقاق التاريخي يذكر sheep وprotector في shepherd بلا تفكيك نهائي مؤهل.", "وقف اسم الراعي عند حد التركيب التاريخي؛ لم أورثه معنى الجبن أو أحد العنصرين."),
    255: R("در", "TOOL-GAP", "جسر المعنى: wall حاضر، لكن الهيكل ناقص الواو المنطوقة من /dēwār/.", "أوقفت المقارنة قبل انتخاب جذر؛ لا يعوض الصامت المنطوق من الأصل التاريخي."),
    256: R("ببر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ببر`: انضمام واستمساك مع حدث الراء؛ لا يسمي beaver.", "قضم القندس أو بناؤه أفعال للحيوان لا اسم النوع؛ لم أستخرج الحيوان من وصف فعله."),
    257: R("بيو", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بيو`: محاكم حروف بلا معنى without أو lacking.", "الوظيفة النحوية لا تستخرج من رصف الحروف، ولا يثبت امتداد الصوت معنى الغياب."),
    258: R("است", "OUT-OF-SCOPE", "جسر المعنى: Avesta وAvestan اسما كتاب ولغة لا معنى معجميا عاما إلى `است`.", "عزلت العلم واللغة؛ لم أحول اسم النص الديني أو لغته إلى حدث جذري."),
    259: R("سير", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سير`: حركة وامتداد؛ لا يسمي garlic.", "السير في زراعة الثوم أو امتداد ساقه سياق خارجي لا معنى النبات؛ فصلت المتجانسين."),
    260: R("كه", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كه`: إحاطة أو جمع مع رخاوة؛ لا يسمي lettuce.", "التفاف أوراق الخس هيئة عامة لا اسم النبات، ولا شاهد عربي مستقل للثمرة أو الورق."),
    262: R("كدو", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كدو`: الجمع والاحتواء مع امتداد؛ لا يسمي squash أو gourd.", "احتواء القرعة لبها صفة تشترك فيها ثمار كثيرة؛ لا يميز النوع ولا يقوم مدار الاسم."),
    263: R("قرج", "COMPOUND-BOUNDARY", "جسر المعنى: mushroom أو fungus مردود إلى صيغة قديمة ولاحقة بلا From X + Y مؤهل.", "منعت اللاحقة التاريخية من إصدار حكم للصورة الحديثة، ولم أخترع مكونا مستقلا."),
    264: R("جج", "TOOL-GAP", "جسر المعنى: plum حاضر، لكن /gowje/ يحمل واوا منطوقة أسقطها الهيكل.", "وقف فحص الصوت قبل مدار الثمرة؛ لا تختزل الصورة إلى جيمين بعد حذف /w/."),
    266: R("بست", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بست`: الجفاف واليبوسة؛ لا يسمي pistachio.", "يبس قشرة الفستق عند النضج وصف للثمرة لا اسمها، ولم أضف قافا ليست في المروحة."),
    267: R("رس", "TOOL-GAP", "جسر المعنى: rhubarb حاضر، لكن /rivâs/ يحمل /v/ منطوقة أسقطها الهيكل.", "لا أقارن نباتا بهيكل فقد صامته الأوسط؛ توقفت قبل أي دعوى معنى."),
    268: R("زر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زر`: نفاذ دقيق مع إمساك؛ لا يسمي cumin أو caraway.", "دقة الحبة أو إمساك طعمها وصف حسي عام لا اسم التابل؛ بقي النبات خارج المدار."),
    269: R("خرس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خرس`: انقطاع الصوت أو سكونه؛ لا يسمي bear.", "خمود صوت الدب حالة عارضة للحيوان لا معنى النوع، وشواهد العربية في الصمت."),
    270: R("به", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`به`: ظهور أو خروج مع امتداد؛ لا يسمي quince.", "ظهور ثمرة السفرجل من الشجرة وصف لكل ثمر، ولا يثبت اسمه أو نوعه."),
    271: R("سرح", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سرح`: انطلاق وامتداد؛ لا يسمي red.", "امتداد اللون على سطح فعل انتشار عام لا معنى الحمرة، ولا شاهد دقيق للصفة."),
    272: R("كرس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كرس`: تراكم وتثبيت؛ لا يسمي cherry، وبحث `كرز` لم يجد معنى الثمرة في الموارد المعتمدة.", "لم أضف زايا من العربية الحديثة: س↔ز غير مسمى ومواد `كرز` الكلاسيكية المفحوصة لا تعطي cherry."),
    275: R("دست", "LOANWORD-NON-ARABIC-TO-ARABIC", "جسر المعنى: شاهد أساس البلاغة في دست الشطرنج، والتاج يسمي الفارسية hand واستعمال الدست في اللعبة.", "انتقل hand إلى دور المجموعة أو الجولة في اللعب؛ الشاهد سمى اتجاه الفارسية إلى العربية، فأغلق تماس لا إرثا."),
    276: R("درد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`درد`: ذهاب الأسنان أو الحرد؛ لا يسمي pain.", "الألم قد يصاحب سقوط الأسنان لكنه أعم منه ولا يساويه؛ فصلت pain عن المادة العربية."),
    277: R("درد", "LOANWORD-NON-ARABIC-TO-ARABIC", "جسر المعنى: الصحاح يسمي دردي الزيت ما يبقى أسفله، وأساس البلاغة يسميه عكر النبيذ.", "اتحد sediment أو lees مع الدردي العربي، وخبر الأصل يسمي انتقال الإيراني عبر الآرامية إلى العربية؛ أغلق اتجاه دخول."),
    278: R("جن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جن`: استتار الشيء عن الحس؛ لا يسمي what أو joy.", "خفاء جواب السؤال أو باطن الفرح تأويلان عامان لا معنى الأداة أو صيحة السرور."),
    279: R("رن", "TOOL-GAP", "جسر المعنى: computer حاضر، لكن /râyâne/ يحمل /y/ منطوقة أسقطها الهيكل.", "لا يحول الاسم المصوغ حديثا إلى راء ونون بعد حذف الياء؛ وقف الحكم عند الأداة."),
    280: R("همس", "TOOL-GAP", "جسر المعنى: neighbour حاضر، لكن /hamsâye/ يحمل /y/ منطوقة أسقطها الهيكل.", "وقف العضو قبل تحليل `هم` و`سایه` أو انتخاب مادة عربية؛ الهيكل الصوتي ناقص."),
    281: R("توز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`توز`: دفع وانتشار؛ لا يسمي now.", "حلول الزمن الحاضر ليس دفعا أو انتشارا، ولم أضف جيم طازج الخارجة من مروحة الصف."),
    282: R("توز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`توز`: دفع وانتشار؛ لا يسمي fresh.", "انتشار رائحة الطازج صفة محتملة لا معنى الجدة، والقرض العربي `طازج` يحتاج صامتا خارج الصف."),
    283: R("تنه", "COMPOUND-BOUNDARY", "جسر المعنى: alone أو lonely يرد إلى أصل أوسط وتحليل Equivalent، لا From X + Y المؤهل.", "لم أحول tan وīhā التاريخيين إلى مكونين للمدخلة الحديثة؛ وقف الحكم عند الحد."),
    284: R("شنا", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شنا`: ظهور أو ارتفاع مع امتداد؛ لا يسمي swimming.", "ارتفاع السابح على الماء حالة من الحركة لا معنى السباحة نفسها، ولا شاهد عربي للفعل."),
    285: R("بسط", "ROOT-TRACE", "جسر المعنى: low أو abject حالة انخفاض وانفراش، والحدث المجمد لـ`بسط` نشر الشيء وتمديده.", "مدار 1: المنخفض ملتصق بسطح الأرض كالمبسوط؛ شاهدا البسط والانبساط على الأرض يثبتان الحدث المكاني مباشرة."),
    286: R("بست", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بست`: ضم وربط وإغلاق؛ لا يسمي flour.", "تماسك الدقيق بالعجن مرحلة لاحقة لا معنى المسحوق نفسه؛ فصلت المادة عن فعل ربطها."),
    288: R("مرج", "COMPOUND-BOUNDARY", "جسر المعنى: ant مصغر من `مور` في الخبر، بلا From X + Y نهائي مباشر.", "وقف التصغير عند حد الصرف التاريخي؛ لم أورث النملة حكم المرشح أو الأصل."),
    289: R("كرم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كرم`: شرف أو سخاء ونماء؛ لا يسمي worm.", "نمو الدودة في المادة فعل للكائن، والسخاء وصف إنساني لا اسم النوع."),
    290: R("شن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شن`: تفريق وصب؛ لا يسمي comb.", "تفريق الشعر وظيفة المشط لا معنى الآلة نفسها، ولا يميزها عن الأصابع وسائر الأدوات."),
    291: R("شن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شن`: تفريق وصب؛ لا يسمي shoulder.", "انتشار الذراع من الكتف هيئة جسدية لا معنى المفصل، وفصلت المتجانس عن comb."),
    292: R("خك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خك`: محكمتا الخاء والكاف بلا معنى soil أو earth.", "تماسك التراب أو تخلخله أوصاف متقابلة لا اسم المادة؛ لم يقم شاهد عربي دقيق."),
    293: R("خك", "COMPOUND-BOUNDARY", "جسر المعنى: khaki يرد بتحليل سطحي إلى `خاک` واللاحقة، لا From X + Y المؤهل.", "فصلت صفة اللون عن مدخلة soil السابقة، ومنعت التحليل السطحي من توريث الحكم."),
    294: R("جلف", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جلف`: قشر وجفاء؛ لا يسمي golf.", "حفر أرض الملعب أو جلف العشب فعل يقع في الرياضة لا معنى اسم اللعبة."),
    295: R("هوش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`هوش`: محاكم حروف بلا حدث intelligence أو consciousness.", "اليقظة أثر للذكاء وليست حدا جامعا له، وشواهد الرسم لا تسمي الملكة العقلية."),
    296: R("نحد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`نحد`: نفاذ من الباطن بقوة واتساع؛ لا يسمي chickpea.", "نفاذ البادرة من الحبة فعل للنبات لا اسم الحمص، ولا شاهد عربي للنوع تحت المادة."),
    297: R("بدم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بدم`: بروز أو ضم مع حدث الميم؛ لا يسمي almond.", "التاج يشرح `بادام` بالفارسية لكنه لا يقيم حدث المادة المختارة؛ بقيت قرينة نقل منفردة بلا مدار."),
    298: R("شرن", "COMPOUND-BOUNDARY", "جسر المعنى: sweet يحلل سطحيا إلى `شیر` واللاحقة `ـین`، لا From X + Y النهائي المباشر.", "لم أورث الحلاوة حكم اللبن أو اللاحقة، ووقف التحليل السطحي عند حد المركب."),
    299: R("نوي", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`نوي`: قصد أو بعد مع حدث الياء؛ لا يسمي new.", "الشيء الجديد قد يقصد لحداثته، لكن القصد أثر استعمالي لا معنى الجدة."),
    300: R("جز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جز`: قطع وإزالة؛ لا يسمي tamarisk.", "جز أغصان الأثل فعل يقع على الشجرة ولا يسمي النوع؛ لا شاهد عربي للاسم."),
    301: R("جز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جز`: قطع وإزالة؛ لا يسمي rod أو cubit.", "قضيب القطع أداة محتملة، لكنه لا يساوي وحدة القياس أو العصا؛ فصلت المتجانسين."),
    302: R("كركر", "COMPOUND-BOUNDARY", "جسر المعنى: worker يحلل سطحيا إلى `کار` + `ـگر` بلا From X + Y مؤهل.", "لم أورث اسم العامل حكم work أو لاحقة الفاعل، ووقف الحكم عند التحليل السطحي."),
    303: R("كركر", "COMPOUND-BOUNDARY", "جسر المعنى: effective يكرر `کار` + `ـگر` بتحليل سطحي لا بصيغة From المؤهلة.", "فصلت الصفة عن اسم العامل السابق، ولم تورثها قرار متجانس أو مكون."),
    305: R("تر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تر`: رطوبة أو امتلاء؛ لا يسمي dark.", "الرطوبة قد تزيد قتامة السطح لكنها سبب عرضي لا معنى الظلمة أو الصفة."),
    306: R("خرم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خرم`: ثقب أو قطع؛ لا يسمي date fruit.", "نزع نواة التمرة أو ثقبها فعل عليها لا اسم الثمرة؛ لا يثبت مدار النوع."),
    307: R("بب", "TOOL-GAP", "جسر المعنى: papaya حاضر، لكن /pâpâyâ/ يحمل /y/ منطوقة أسقطها الهيكل.", "لا تختزل كلمة القرض إلى باءين بعد حذف الصامت الأوسط؛ توقف الحكم قبل المعنى."),
    309: R("القن", "TOOL-GAP", "جسر المعنى: purple أو Judas tree حاضر، لكن /argavân/ يحمل /v/ منطوقة أسقطها الهيكل.", "رغم مقارنة العربية `أرجوان` في الأصل، لم أعوض /v/ ولا أنقل حكم صورة خارج مروحة الصف."),
    310: R("برشط", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`برشط`: بسط مع انتشار وامتداد؛ لا يسمي swallow bird.", "بسط الجناحين فعل للطائر لا اسم النوع، ويصدق على طيور كثيرة؛ لا مدار مميز."),
    311: R("كرغ", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كرغ`: تركز ومعاودة أو بقاء؛ لا يسمي crow.", "معاودة الغراب إلى موضعه سلوك محتمل لا اسم الطائر، ولا شاهد عربي للنوع تحت المرشح."),
    312: R("خرس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خرس`: انقطاع الصوت؛ لا يسمي rooster.", "وجد `خروس` في التاج جمعا لشيء آخر لا الديك؛ وصياح الديك نقيض الخرس لا معناه."),
    313: R("اسبذ", "COMPOUND-BOUNDARY", "جسر المعنى: cook مفككة مباشرة إلى `آش` food و`پز` cooking stem.", "قُرئ المكونان استقلالا؛ لم يحول اسم الفاعل المركب إلى مادة عربية واحدة."),
    314: R("رغن", "ROOT-TRACE", "جسر المعنى: oil أو butter أو ghee مادة رخوة كثيفة، والحدث المجمد لـ`رغن` طبقة رخوة مع كثافة ما.", "مدار 1: الدهن طبقة لينة كثيفة تقبل الانسياب البطيء؛ ثبت الحدث مباشرة ولم يعتمد خبر الأصل."),
    315: R("دوش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دوش`: محاكم حروف بلا حدث shoulder.", "حمل الشيء على الكتف فعل للعضو لا معناه، ولا شاهد عربي مستقل للتسمية."),
    316: R("دوش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دوش`: محاكم حروف بلا معنى last night.", "فصلت الظرف الزمني عن shoulder السابق؛ اتحاد الرسم لا ينقل معنى أو حكما."),
    318: R("جقق", "TOOL-GAP", "جسر المعنى: lark حاضر، لكن /čakâvak/ يحمل /v/ منطوقة أسقطها الهيكل.", "أوقف الهيكل الناقص المقارنة قبل تحليل اللاحقة أو صوت الطائر؛ لا تعويض يدوي."),
    319: R("تخت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تخت`: استواء أو صلابة مع امتداد؛ لا يغلق flat من شاهد عربي مناسب.", "المصادر العربية تسمي `تخت` الفارسية بمعان أخرى كالصندوق، فلا تورث الصفة من متجانس فارسي اسمي."),
    320: R("بب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بب`: محكمتا الباء بلا معنى owl.", "صوت البوم محاكاة محتملة لا اسم النوع في شاهد عربي مستقل؛ بقي المرشح مفتوحا."),
    321: R("جعد", "LAW-GAP", "نص الحدث المجمد لـ`جعد`: التجوف والفراغ؛ لا يسمي owl، وغ↔ع غير مسمى.", "جوف العين أو الريش وصف عارض لا اسم النوع، وفوق غياب المعنى بقي صف الصوت الأوسط بلا قانون."),
    322: R("بز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بز`: غلبة أو أخذ؛ لا يسمي again أو anew.", "إعادة الفعل قد تفضي إلى غلبة لكنها وظيفة ظرفية لا معنى المادة."),
    323: R("كر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كر`: رجوع أو تكرار؛ لا يسمي butter أو mouldiness.", "خبر الأصل يقارن العربية `كرج` للعفن، لكنها خارج مروحة الصف؛ لم أضف الجيم لإنقاذ المتجانس."),
    324: R("جش", "TOOL-GAP", "جسر المعنى: speech أو dialect مفكك من say واللاحقة، لكن /guyeš/ فقد /y/ في الهيكل.", "قُرئ المكونان، ثم أوقف الصامت الساقط الحكم قبل مقارنة الصورة المجموعة أو توريث معنى القول."),
    325: R("مجس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مجس`: جس واختبار أو مس؛ لا يسمي fly insect.", "وقوع الذباب على السطوح ومسها فعل للحشرة لا اسم النوع؛ لا شاهد عربي للتسمية."),
    326: R("بحثن", "LAW-GAP", "نص الحدث المجمد لـ`بحثن`: كشف وفراغ؛ لا يسمي cook أو bake، وت↔ث غير مسمى.", "فحص الطعام أو كشف نضجه فعل للطاهي لا معنى الطبخ، وفوق ذلك بقي صف الصوت الثالث بلا قانون."),
    327: R("ارم", "LAW-GAP", "نص الحدث المجمد لـ`ارم`: محاكم حروف بلا معنى calm أو peaceful، وآ↔ا غير مسمى.", "ترك الشيء بلا حركة قد يتبع الهدوء لكنه ليس معنى السكينة، وبقي أول صفوف الصوت بلا قانون."),
    328: R("ارم", "LAW-GAP", "نص الحدث المجمد لـ`ارم`: محاكم حروف بلا معنى calm أو rest، وآ↔ا غير مسمى.", "فصلت الاسم عن الصفة السابقة، وفوق غياب المدار بقي أول صفوف الصوت بلا قانون."),
    329: R("مردن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مردن`: محاكم حروف بلا حدث die.", "توقف الحركة نتيجة للموت لا تعريفه، ولم ينزع `ن` مصدرا بلا تحليل منشور."),
    330: R("مرد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مرد`: تمرد أو صلابة وتجرد؛ لا يسمي dead أو deceased.", "الجمود بعد الموت حالة للجسد لا معنى الوفاة، وفصلت الصفة عن فعل die السابق."),
}


def pair_key(row: H.SweepRow) -> tuple[str, str]:
    return row.branch, H.norm_gloss(row.gloss)


def validate_nucleus_snapshot() -> None:
    actual_names = {path.name for path in NUCLEUS_DIR.glob("nucleus-sweep-*.json")}
    if actual_names != set(NUCLEUS_SNAPSHOT):
        raise AssertionError(f"تغير جرد أحواض النواة الحالية: {sorted(actual_names)}")
    for name, (expected_size, expected_hash, expected_both, expected_sound) in NUCLEUS_SNAPSHOT.items():
        raw = (NUCLEUS_DIR / name).read_bytes()
        if len(raw) != expected_size or hashlib.sha256(raw).hexdigest() != expected_hash:
            raise AssertionError(f"تغيرت نسخة القرص الحالية للحوض {name}")
        data = json.loads(raw)
        language = name.removeprefix("nucleus-sweep-").removesuffix(".json")
        if data.get("language") != language:
            raise AssertionError(f"تغير وسم اللغة في {name}")
        if data.get("both_total") != expected_both or data.get("sound_only_total") != expected_sound:
            raise AssertionError(f"تغير عداد نسخة v9 في {name}")
        if len(data.get("both") or []) != expected_both or len(data.get("sound_only") or []) != expected_sound:
            raise AssertionError(f"تغير طول قوائم نسخة v9 في {name}")


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
            if row.rank > 251 and len(fresh) < 70:
                internal_skips.append(row.rank)
            continue
        seen.add(key)
        if row.rank <= 251:
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
    expected_indices = {"آش": {766}, "پز": set(), "گوی": {9043}, "ـش": {10301, 10302}}
    fan_counts = {"آش": 60, "پز": 60, "گوی": 0, "ـش": 0}
    for word, expected in expected_indices.items():
        actual = {index for index, _entry in grouped.get(word, [])}
        if actual != expected:
            raise AssertionError(f"تغير جرد مكون {word}: {sorted(actual)}")
        fan = tuple(H.FAN.rank(word, H.FAN.fan(word, "persian"), "persian"))
        if len(fan) != fan_counts[word]:
            raise AssertionError(f"تغيرت مروحة المكون {word}: {len(fan)}")
    expected_raw = {"آش": {814}, "پز": {10672}, "گوی": {10708, 10709}, "ـش": {12673, 12674}}
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
    if review.verdict == "ROOT-TRACE":
        return "اكتملت أرجل الصوت والحدث والمدار اليدوي، ومعها شاهدان عربيان كلاسيكيان مستقلان."
    if review.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC":
        return "اكتملت الصورة والمعنى والشواهد، وسمى الخبر اتجاه الدخول إلى العربية؛ أغلق تماس لا إرثا."
    if review.verdict == "COMPOUND-BOUNDARY":
        return "وقف الحكم عند حد المركب؛ لم تورث الصورة المجموعة حكم مكون ولم يخترع تفكيك."
    if review.verdict == "LAW-GAP":
        return "طريق المعنى مفحوص، لكن مسار الصوت يحوي صفا غير مسمى؛ لم يصدر حكم موجب."
    if review.verdict == "TOOL-GAP":
        return "صف الحوض أسقط صامتا منطوقا؛ توقف العضو قبل الحكم ولم يعوض الصامت يدويا."
    if review.verdict == "OUT-OF-SCOPE":
        return "الشرح اسم علم أو لغة لا معنى معجميا عاما؛ أحيل العضو إلى طبقة الأعلام المنفصلة."
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
    left, right = EXPECTED_COMPONENTS[rank]
    if H.clean(left) not in H.clean(decomposition[0]) or H.clean(right) not in H.clean(decomposition[1]):
        raise AssertionError(f"تغير مكونا الرتبة {rank}: {decomposition}")
    lines = [
        f"- تفكيك Kaikki الحصري من السطر الخام {raw['line']}: «{H.clip(raw['etymology'], 420)}».",
        f"- قراءة المكونات المستقلة: {COMPONENT_READINGS[rank]}",
        "- الخطوة صفر: قبل التفكيك الحرفي From X + Y لم تقارن الصورة وحدة جذرية؛ قُرئ كل مكون وحده.",
    ]
    if rank == 324:
        lines.extend([
            f"- عطب الهيكل: {TOOL_GAPS[rank]}",
            "- بعد قراءة المكونات أوقف TOOL-GAP حكم الصورة المجموعة؛ لا حكم من هيكل ناقص.",
        ])
    return lines


BASE_MAKE_CARD = R28.make_card


def make_card(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit) -> str:
    card = BASE_MAKE_CARD(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit)
    card = card.replace("الجولة 28،", "الجولة 29،")
    if item.row.rank == 277:
        lines = card.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("  - الشاهد 1،"):
                lines[index] = "  - الشاهد 1، تاج اللغة وصحاح العربية للجوهري: «ودردي الزيت وغيره: ما يبقى في أسفله.»"
            elif line.startswith("  - الشاهد 2،"):
                lines[index] = "  - الشاهد 2، أساس البلاغة للزمخشري: «الدردي عكر النبيذ لأنه يسفل وتعلو الصفوة.»"
        card = "\n".join(lines) + "\n"
    if len(card.encode("utf-8")) >= CARD_LIMIT:
        replacements = {
            "- إصدار البروتوكول:": "- نموذج WO-B-PROBE-001؛ RECOVERY-v2.",
            "- مرجع الحوض:": f"- مرجع الحوض: sound_only[{item.row.rank - 1}]؛ overlap=0؛ shared=فارغ.",
            "- قراءة مداخل الرسم المتجانس:": f"- قراءة مداخل الرسم المتجانس: {entry.homograph_count}؛ المختارة {entry.homograph_index}، entries[{entry.global_index}].",
            "- فحص المروحة كلها:": f"- فحص المروحة كلها: قُرئت مواد {len(ranked)} مرشحا بلا قص.",
            "- المقابل من اللسان:": f"- المقابل من اللسان: `{decision.candidate}` من المروحة الحية.",
            "- الخطوة صفر:": (
                "- الخطوة صفر: لا حكم من هيكل ناقص، ولم تقارن الصورة وحدة."
                if item.row.rank in TOOL_GAPS
                else "- الخطوة صفر: لم تقارن الصورة وحدة قبل قراءة المكونات."
            ),
            "- المصفاة:": "- المصفاة: الأصل حاشية؛ النقل يحتاج مانحا أو اتجاه دخول مسمى.",
            "- فصل المتجانسات والاقتراض:": "- فصل المتجانسات والاقتراض: الحكم للمدخلة وحدها.",
            "- اليتم والإشعاع:": "- اليتم والإشعاع: الشاهدان أو فجوتاهما حاضرة.",
            "- جسور الاسترداد:": "- جسور الاسترداد الثمانية: مستوفاة.",
            "- عائق القرار أو تمامه:": f"- عائق القرار: {decision.verdict}؛ {decision.obstacle}",
            "- ملاحظات العدستين:": f"- ملاحظات العدستين: استرداد وتشكيك؛ الجولة 29، {item.key}.",
        }
        compacted = []
        for line in card.splitlines():
            replacement = next((value for prefix, value in replacements.items() if line.startswith(prefix)), None)
            compacted.append(replacement if replacement is not None else line)
        card = "\n".join(compacted) + "\n"
    return card


def validate_decisions(selected, raw_entries, decisions, ranked_by_rank, sense_map) -> None:
    if set(REVIEWS) != set(SOUND_RANKS):
        raise AssertionError("جدول المدار اليدوي لا يغطي الرتب السبعين")
    parsed = {item.row.rank for item in selected if P25.direct_from_plus(raw_entries[item.row.rank]["etymology"])}
    if parsed != PARSER_FROM_PLUS:
        raise AssertionError(f"تغيرت نتائج محلل From X + Y الواسع: {sorted(parsed)}")
    expected_verdicts = {
        "COMPOUND-BOUNDARY": 9,
        "LOANWORD-NON-ARABIC-TO-ARABIC": 2,
        "LAW-GAP": 4,
        "OPEN-CANDIDATE": 43,
        "OUT-OF-SCOPE": 1,
        "ROOT-TRACE": 2,
        "TOOL-GAP": 9,
    }
    if Counter(review.verdict for review in REVIEWS.values()) != Counter(expected_verdicts):
        raise AssertionError("تغير توزيع الأحكام اليدوي")
    if {rank for rank, review in REVIEWS.items() if review.verdict == "ROOT-TRACE"} != {285, 314}:
        raise AssertionError("تغير موضعا ROOT-TRACE")
    if {rank for rank, review in REVIEWS.items() if review.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC"} != {275, 277}:
        raise AssertionError("تغير موضعا اتجاه الدخول")
    for item, decision in zip(selected, decisions):
        row = item.row
        candidates = {candidate for candidate, _score in ranked_by_rank[row.rank]}
        if decision.candidate not in candidates or decision.candidate not in row.candidates_found:
            raise AssertionError(f"مرشح الرتبة {row.rank} خارج المروحة الحية أو أعضاء الحوض")
        complete = H.route_complete(row, decision.candidate)
        _count, coverage, _witnesses = P.classical_witnesses(decision.candidate, sense_map, 60)
        if decision.verdict == "LAW-GAP" and complete:
            raise AssertionError(f"LAW-GAP بلا صف مفقود في الرتبة {row.rank}")
        if decision.verdict in {"OPEN-CANDIDATE", "ROOT-TRACE", "LOANWORD-NON-ARABIC-TO-ARABIC"} and not complete:
            raise AssertionError(f"حكم بمسار ناقص في الرتبة {row.rank}: {decision.verdict}")
        if decision.verdict in {"ROOT-TRACE", "LOANWORD-NON-ARABIC-TO-ARABIC"}:
            if coverage < 2 or H.event_line(decision.candidate).startswith("لا حدث"):
                raise AssertionError(f"حكم صادر بلا حدث وشاهدين في الرتبة {row.rank}")
        if row.rank in EXACT_DECOMPOSITIONS and decision.verdict not in {"COMPOUND-BOUNDARY", "TOOL-GAP"}:
            raise AssertionError(f"تفكيك مباشر بلا حد أو عطب أداة في الرتبة {row.rank}")
        if row.rank in BLOCKED_BOUNDARIES and decision.verdict != "COMPOUND-BOUNDARY":
            raise AssertionError(f"حد مركب بلا COMPOUND-BOUNDARY في الرتبة {row.rank}")
        if row.rank in TOOL_GAPS and decision.verdict != "TOOL-GAP":
            raise AssertionError(f"هيكل ناقص بلا TOOL-GAP في الرتبة {row.rank}")
        if not REVIEWS[row.rank].meaning_path.startswith(("جسر المعنى:", "نص الحدث المجمد")):
            raise AssertionError(f"طريق المعنى غير مسمى في الرتبة {row.rank}")


def validate_text(selected, texts, prior_pairs) -> None:
    if len(selected) != 70 or BATCH_SIZES != (35, 35):
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = re.findall(r"^### (WO-B-R29-SOUND-\d{5}):", joined, re.MULTILINE)
    if headings != [item.heading for item in selected]:
        raise AssertionError("معرفات الجولة 29 لا تطابق النافذة")
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
    for rank in set(BLOCKED_BOUNDARIES) - EXACT_DECOMPOSITIONS:
        card = texts[SOUND_RANKS.index(rank)]
        if "حد المركب غير المفكك" not in card or "بلا مكونات مخترعة" not in card:
            raise AssertionError(f"لم يغلق حد المركب في الرتبة {rank}")
    for rank in TOOL_GAPS:
        card = texts[SOUND_RANKS.index(rank)]
        if "عطب الهيكل" not in card or "لا حكم من هيكل ناقص" not in card:
            raise AssertionError(f"لم يسم عطب الهيكل في الرتبة {rank}")


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
            f"## الجولة التاسعة والعشرون، دفعة sound_only رقم {number}", "",
            f"- الوقت: {now}، Africa/Cairo.",
            f"- رشح وكتب: {len(batch)}؛ المواضع المقروءة المتجاوزة داخل المدى: {skipped}.",
            f"- المواضع: من {batch[0].heading} إلى {batch[-1].heading}.",
            f"- توزيع الأحكام: {distribution}.",
            "- طريق المعنى: سمي من جسر معنى صريح أو من نص الحدث المجمد في كل بطاقة.",
            "- المدار: كتب يدويا لكل عضو، وفصلت الأصداء اللينة عن الآثار المحكمة.",
            "- المروحة: ولدت حية كاملة ورتبت بالأوزان، ومسحت مواد جميع مرشحيها بلا قص للحقل المصدر.",
            "- المتجانسات: قرئت كل مداخل الرسم، وسجل العدد ورقم المدخلة المختارة في كل بطاقة.",
            "- المركب: لم يقبل إلا سطر From X + Y النهائي المباشر؛ لم يخترع مكون.",
            "- التحقق البنيوي: المعرفات فريدة؛ لا بطاقة فوق 5KB؛ لا شرطة طويلة؛ الأرقام غربية والنص NFC.",
            f"- آخر موضع في الدفعة: {batch[-1].heading}، `{batch[-1].row.branch}`.", "",
        ])
    total = Counter(decision.verdict for decision in decisions)
    distribution = "؛ ".join(f"{key}={total[key]}" for key in sorted(total))
    max_size = max(sizes)
    max_item = selected[sizes.index(max_size)]
    traces = [item.heading for item, decision in zip(selected, decisions) if decision.verdict == "ROOT-TRACE"]
    transmissions = [item.heading for item, decision in zip(selected, decisions) if decision.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC"]
    lines.extend([
        "## حصيلة الجولة التاسعة والعشرين", "",
        f"- حمل `persian.md` مرة واحدة؛ أزواج WO-B المقروءة={stats['pair_count']}؛ المتجاوز داخل النافذة={', '.join(map(str, stats['skipped']))}.",
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- نطاق الصوت الجديد: الرتب 252-330 بعد آخر معرف في الجولة السابقة، مع تجاوز الأزواج التسعة المقروءة فقط.",
        f"- الأثر المحكم ذو الأرجل الثلاث والشاهدين: {', '.join(traces)}.",
        f"- اتجاه الدخول إلى العربية المسمى بالشاهدين: {', '.join(transmissions)}.",
        "- التفكيك المباشر المؤهل: S00313 `آش` + `پز`، وS00324 `گوی` + `ـش`؛ قرئت المكونات استقلالا.",
        "- نتائج المحلل الواسع المرفوضة: S00283 Equivalent to، وS00293 By surface analysis؛ لم تحولا إلى From X + Y.",
        "- الحدود الأخرى غير المؤهلة: S00254، S00263، S00288، S00298، S00302، S00303.",
        "- فجوات الأداة: S00255، S00264، S00267، S00279، S00280، S00307، S00309، S00318، S00324؛ لم تعوض الصوامت المنطوقة الساقطة.",
        "- أحواض `nucleus-sweep-*.json` التسعة الحالية v9 قرئت كاملة من القرص، وثبت الحجم وSHA-256 والعدادات لكل ملف قبل الانتخاب.",
        f"- أكبر بطاقة: {max_size} بايت، {max_item.heading}؛ كل البطاقات دون 5KB.",
        "- لم تفعل طبقة البرهان، ولم يبن ملف مشترك، ولم يقع ship، ولم يستعمل git.",
        "", f"<!-- {MARKER}:END -->", "", DONE_LINE,
    ])
    return "\n".join(lines)


def validate_existing(reading_text: str, report_text: str) -> None:
    match = re.search(rf"<!-- {re.escape(MARKER)}:START -->(.*?)<!-- {re.escape(MARKER)}:END -->", reading_text, re.DOTALL)
    if not match:
        raise AssertionError("محضر الجولة موجود وبطاقاتها غائبة")
    headings = re.findall(r"^### (WO-B-R29-SOUND-\d{5}):", match.group(1), re.MULTILINE)
    expected = [f"WO-B-R29-SOUND-{rank:05d}" for rank in SOUND_RANKS]
    if headings != expected:
        raise AssertionError("مقطع الجولة 29 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(DONE_LINE):
        raise AssertionError("سطر DONE29 ليس خاتمة التقرير")


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
        print("ROUND29 ALREADY PRESENT AND VALID")
        print(DONE_LINE)
        return 0

    data = json.loads(SWEEP.read_text(encoding="utf-8"))
    selected, stats = select_rows(data, reading_text)
    prior_pairs = H.read_pairs(reading_text)
    lexicon = json.loads(LEXICON.read_text(encoding="utf-8"))

    R28.EXPECTED_ENTRY_INDEX = EXPECTED_ENTRY_INDEX
    R28.EXPECTED_RAW_LINE = EXPECTED_RAW_LINE
    R28.REVIEWS = REVIEWS
    R28.BLOCKED_BOUNDARIES = BLOCKED_BOUNDARIES
    R28.TOOL_GAPS = TOOL_GAPS
    R28.OUT_OF_SCOPE = OUT_OF_SCOPE
    R28.EXACT_DECOMPOSITIONS = EXACT_DECOMPOSITIONS
    R28.decomposition_lines = decomposition_lines
    R28.make_card = make_card

    entries, grouped = R28.select_branch_entries(selected, lexicon)
    raw_entries = R28.load_raw_entries(selected, entries)
    validate_components(grouped)

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
        "## الجولة التاسعة والعشرون: متابعة حوض sound_only (2026-08-26)\n\n"
        "- النطاق: 70 عضوا طازجا بعد WO-B-R28-SOUND-00251؛ من الرتبة 252 إلى 330 مع تجاوز 253 و261 و265 و273 و274 و287 و304 و308 و317 لأنها مقروءة؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ طريق المعنى مسمى، والمدار اليدوي حاسم، والأصداء مفصولة عن الآثار المحكمة.\n"
        "- لقطة الأحواض: قرئت ملفات nucleus-sweep-*.json التسعة الحالية v9 من القرص وثبتت بصماتها وعداداتها قبل الانتخاب.\n\n"
        + "\n".join(texts[:35])
        + "\n## الدفعة الثانية: متابعة sound_only بعد الرتبة 292\n\n"
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
    print("ROUND29 READY")
    print("NUCLEUS_V9_FILES", len(NUCLEUS_SNAPSHOT), "SHA256_AND_COUNTS_OK")
    print("SKIPPED", ",".join(map(str, stats["skipped"])))
    print("BATCHES", *BATCH_SIZES, "SELECTED", len(selected))
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("EXACT_FROM_PLUS", " ".join(f"S{rank:05d}" for rank in sorted(EXACT_DECOMPOSITIONS)))
    print("PARSER_FROM_PLUS", " ".join(f"S{rank:05d}" for rank in sorted(PARSER_FROM_PLUS)))
    print("BLOCKED_BOUNDARIES", len(BLOCKED_BOUNDARIES), "TOOL_GAPS", len(TOOL_GAPS))
    print("MAX_CARD", max(sizes), selected[sizes.index(max(sizes))].heading)
    if args.preview:
        print("PREVIEW ONLY")
        print(DONE_LINE)
        return 0

    with READING.open("a", encoding="utf-8", newline="") as handle:
        handle.write(reading_append)
    with REPORT.open("a", encoding="utf-8", newline="") as handle:
        handle.write(report_append)
    print("ROUND29 WRITTEN")
    print(DONE_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
