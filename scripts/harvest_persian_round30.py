# -*- coding: utf-8 -*-
"""المسار B، الجولة 30: متابعة حوض sound_only في دفعتين من 35 بطاقة."""

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

import harvest_persian_round29 as R29  # noqa: E402

R28 = R29.R28
H = R29.H
P = R29.P
P25 = R29.P25
READING = ROOT / "04-cross-linguistic" / "readings" / "persian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-B.md"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-persian.json"
NUCLEUS_DIR = ROOT / "04-cross-linguistic" / "exploration"
LEXICON = ROOT / "data" / "branch-lexicons" / "persian.json"
RAW_LEXICON = ROOT / "Resources" / "persian" / "kaikki.org-dictionary-Persian.jsonl"
MARKER = "LANE-B-PERSIAN-ROUND30-2026-08-26"
CARD_LIMIT = 5120
SOUND_RANKS = (
    331, 333, 334, 335, 336, 337, 338, 339, 340, 341, 342, 343, 344, 345,
    346, 347, 348, 349, 351, 355, 357, 359, 361, 362, 364, 365, 366, 367,
    368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 380, 381,
    382, 383, 384, 385, 387, 388, 389, 390, 391, 392, 393, 394, 395, 396,
    397, 398, 399, 400, 401, 405, 406, 407, 408, 409, 410, 411, 412, 413,
)
BATCH_SIZES = (35, 35)
DONE_LINE = "LANE-B DONE30 70 WO-B-R30-SOUND-00413"
EXPECTED_SKIPS = (332, 350, 352, 353, 354, 356, 358, 360, 363, 386, 402, 403, 404)
EXACT_DECOMPOSITIONS = {345, 349, 355, 359, 372, 391, 398, 406}
BLOCKED_BOUNDARIES = {
    376: "يسمي الخبر اشتقاقا أوسط تاريخيا من worth واللاحقة، لا From X + Y نهائيا مباشرا للمدخلة الحالية.",
    408: "يقول الخبر From noun `جنگ` بلا تفكيك نهائي مباشر للصفة واللاحقة، فلم يخترع مكون صرفي.",
}
TOOL_GAPS = {
    345: "الصورة `هواپیما` منقوطة /hawāpaymā/، لكن الهيكل أسقط /w/ و/y/ المنطوقتين.",
    359: "الصورة `گوشواره` منقوطة /gušvâre/، لكن الهيكل أسقط /v/ المنطوقة.",
    370: "الصورة `جانور` منقوطة /jānwar/، لكن الهيكل أسقط /w/ المنطوقة.",
    384: "الصورة `جوان` منقوطة /jawān/، لكن الهيكل أسقط /w/ المنطوقة.",
    385: "الصورة `جوان` منقوطة /jawān/، لكن الهيكل أسقط /w/ المنطوقة.",
    406: "الصورة `دریاچه` منقوطة /daryāča/، لكن الهيكل أسقط /y/ المنطوقة.",
    413: "الصورة `آوردن` منقوطة /āwardan/، لكن الهيكل أسقط /w/ المنطوقة.",
}
OUT_OF_SCOPE = {
    362: "المدخلة اسم قارة Europe، فطبقة الأعلام الجغرافية معزولة عن الحكم الجذري.",
}

NUCLEUS_SNAPSHOT = {
    "nucleus-sweep-ancient_greek.json": (7978449, "321bd4d5839088a4028394ce83c2ea5e16d43d4ac3a0e1b67983cf5491ff6024", 2526, 16555),
    "nucleus-sweep-english_middle.json": (3500284, "d1eb925c6c9a4a794a8c3b4103a3db47d8ca658c8f3d05e88f85f5dcd5b8d2d7", 1658, 7746),
    "nucleus-sweep-english_old.json": (1339705, "bc6002de25e26b31ea0db0407ccfdab549554e0fa5258d28f5b978d4488c7364", 515, 3372),
    "nucleus-sweep-gothic.json": (1464517, "543079753150bd12224c272f2a9db2f899e7a65c213db4d4df34792433f776b3", 379, 3038),
    "nucleus-sweep-latin.json": (19045264, "d8e5c63b46c297e2592e23fda27fe6e3759228233a8404d30fa4ee55893ca557", 7413, 38640),
    "nucleus-sweep-old_irish.json": (962467, "8af0da2777c1049cee1422c30f6be3196f87b546198ecd23c5841f6e4cd9f2cd", 314, 2704),
    "nucleus-sweep-old_norse.json": (1394391, "f4a0eb4f67d67ac7161e2e6a20bb59a6efd9d9fa737466a4018965a58dbb3e33", 518, 3706),
    "nucleus-sweep-persian.json": (5506779, "88a70b7d91917ca7ee9b1b7a0bb7dddf618538ecc9899b9c6fa838a82536fa8d", 1714, 13219),
    "nucleus-sweep-welsh.json": (5865541, "c91fb40dcb00978f898a7598d39240915f1a12a762598404152b866c6f5415ff", 1508, 15765),
}

EXPECTED_ENTRY_INDEX = dict(zip(SOUND_RANKS, (
    1381, 1384, 1385, 1391, 1392, 1400, 1401, 1402, 1403, 1407,
    1425, 1431, 1434, 1435, 1437, 1451, 1453, 1457, 1470, 1488,
    1494, 1496, 1505, 1513, 1531, 1543, 1545, 1546, 1547, 1548,
    1554, 1558, 1560, 1566, 1575, 1576, 1595, 1596, 1604, 1605,
    1606, 1607, 1609, 1610, 1612, 1613, 1650, 1651, 1652, 1654,
    1655, 1659, 1660, 1664, 1675, 1676, 1677, 1678, 1679, 1680,
    1681, 1712, 1716, 1721, 1727, 1735, 1747, 1754, 1755, 1765,
)))
EXPECTED_RAW_LINE = dict(zip(SOUND_RANKS, (
    1463, 1466, 1467, 1473, 1474, 1482, 1483, 1484, 1485, 1489,
    1508, 1514, 1517, 1518, 1520, 1534, 1536, 1540, 1553, 1571,
    1577, 1579, 1588, 1596, 1614, 1626, 1628, 1629, 1630, 1631,
    1637, 1641, 1643, 1649, 1658, 1659, 1680, 1681, 1689, 1690,
    1691, 1692, 1695, 1696, 1699, 1700, 1737, 1738, 1742, 1744,
    1745, 1749, 1750, 1754, 1765, 1766, 1767, 1768, 1769, 1770,
    1771, 1804, 1808, 1813, 1819, 1827, 1840, 1847, 1848, 1858,
)))

EXPECTED_COMPONENTS = {
    345: ("هوا", "پیما"),
    349: ("چاپ", "ـگر"),
    355: ("دانش", "ـگاه"),
    359: ("گوش", "ـواره"),
    372: ("پدید", "ـه"),
    391: ("باغ", "ـچه"),
    398: ("پشم", "ـالو"),
    406: ("دریا", "ـچه"),
}
COMPONENT_READINGS = {
    345: "`هوا`: entries[1232] والسطر الخام 1307 لمعاني air وwind وweather، ومروحتها 0: COMPONENT-GAP. `پیما`: غائبة من branch-lexicons ومن الخام، ومروحتها 20: COMPONENT-GAP.",
    349: "`چاپ`: entries[2363] والسطران الخامان 2479 و2480، وفصل noun printing عن جذع الفعل؛ مروحتها 60: OPEN-CANDIDATE. `ـگر`: entries[10503] والخام 12956 لاحقة فاعل: MORPHOLOGY-GAP.",
    355: "`دانش`: entries[1489] والخام 1572 لمعنى knowledge، ومروحتها 9: OPEN-CANDIDATE. `ـگاه`: entries[7461] والخام 8752 لاحقة مكان أو زمان، ومروحتها 72: MORPHOLOGY-GAP.",
    359: "`گوش`: entries[899] والخام 957 لمعنى ear، ومروحتها 120: OPEN-CANDIDATE. `ـواره`: entries[16060] والخام 19121 لاحقة خاصية، ومروحتها 38: MORPHOLOGY-GAP.",
    372: "`پدید`: entries[1566] والخام 1649 لمعنيي evident وvisible، ومروحتها 18: OPEN-CANDIDATE. `ـه`: entries[7112-7114] والخام 8351-8354 متعدد الوظائف، ومروحتها 0: MORPHOLOGY-GAP.",
    391: "`باغ`: entries[838] والخام 895 لمعنى garden أو orchard، ومروحتها 30: OPEN-CANDIDATE. `ـچه`: entries[7513] والخام 8808 لاحقة تصغير، ومروحتها 60: MORPHOLOGY-GAP.",
    398: "`پشم`: entries[1676] والخام 1766 لمعنى wool أو hair، ومروحتها 6: OPEN-CANDIDATE. `ـالو`: entries[14774] والخام 17697 لاحقة صفة، ومروحتها 40: MORPHOLOGY-GAP.",
    406: "`دریا`: entries[970-971] والخام 1030-1031؛ اختير الاسم العام sea أو ocean أو river وعزل العلم، ومروحتها 60: OPEN-CANDIDATE. `ـچه`: entries[7513] والخام 8808 لاحقة تصغير، ومروحتها 60: MORPHOLOGY-GAP.",
}


@dataclass(frozen=True)
class SelectedRow:
    row: H.SweepRow

    @property
    def key(self) -> str:
        return f"S{self.row.rank:05d}"

    @property
    def heading(self) -> str:
        return f"WO-B-R30-SOUND-{self.row.rank:05d}"


Review = R29.Review
R = R29.R

# سجل قراءة يدوي. لا يشتق الحكم من best ولا من وزن المروحة.
REVIEWS = {
    331: R("مرد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مرد`: تجرد ظاهر الشيء مما ينبت؛ لا يسمي dead person.", "خلو جسد الميت من الحركة نتيجة لاحقة لا معنى الموت أو اسم الميت؛ فصلت المدخلة عن صفة dead السابقة."),
    333: R("كستن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كستن`: نقص بالدق أو القشر؛ لا يسمي kill أو murder.", "إتلاف جزء من جسم قد يقع في القتل لكنه لا يساوي إنهاء الحياة؛ لم أستخرج الفعل من أثره."),
    334: R("كستن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كستن`: نقص بالدق أو القشر؛ لا يسمي sow أو plant.", "شق التربة أو إنقاص مخزون البذر عمل سابق أو لاحق للزرع، لا معنى الزراعة نفسها."),
    335: R("رست", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رست`: نفاذ بامتداد؛ لا يغلق straight أو direct.", "امتداد الخط لازم محتمل للاستقامة، لكنه لا يميز المستقيم من المنحني الممتد؛ بقيت الصفة مفتوحة."),
    336: R("رست", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رست`: نفاذ بامتداد؛ لا يسمي truth أو المقام الموسيقي rast.", "فصلت الحقيقة والمقام عن صفة straight السابقة؛ اتحاد الرسم لا يورث معنى أو حكما."),
    337: R("بنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بنج`: امتداد وبناء؛ لا يسمي العدد five.", "عد خمسة أشياء يبني مجموعة محدودة، لكن البناء فعل في المعدود لا معنى العدد."),
    338: R("شس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شس`: محكمتا حرفين بلا معنى six.", "لم تستخرج القيمة العددية من تكرار الصوت أو ترتيب الحروف؛ بقي العدد خارج المدار."),
    339: R("شس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شس`: محكمتا حرفين بلا معنى lung.", "امتلاء الرئة بالهواء وظيفة للعضو لا اسمه؛ وفصلت المتجانس عن العدد السابق."),
    340: R("هفت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`هفت`: محاكم حروف بلا معنى seven.", "لم يحول التطابق الرسومي إلى قيمة عددية، والشواهد العربية للرسم لا تسمي العدد."),
    341: R("هزر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`هزر`: حركة خفيفة مضطربة؛ لا يسمي thousand أو nightingale.", "كثرة الحركة أو اضطراب صوت الطائر وصفان محتملان لا معنى العدد أو اسم النوع."),
    342: R("تن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تن`: ضغط على القوة الباطنية؛ لا يسمي classifier for people.", "وظيفة المصنف النحوية لا تستخرج من الجسم التاريخي ولا من ضغط باطنه؛ لم أورث الأصل حكم الأداة."),
    343: R("كشك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كشك`: خروج المتغلغل من الأثناء؛ لا يسمي pavilion أو palace.", "فتح القصر أو إخراج ساكنه فعل يقع في البناء لا معنى المبنى، وخبر الأصل لا يسمي دخولا إلى العربية."),
    344: R("سجر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سجر`: انحدار مائع حتى يمتلئ الحيز؛ لا يسمي cigarette.", "امتلاء السيجارة بالدخان أو التبغ وصف استعمالي، لا اسم الأداة ولا مادتها."),
    345: R("هبم", "TOOL-GAP", "جسر المعنى: aircraft حاضر وتفكيكه المباشر مقروء، لكن الهيكل أسقط /w/ و/y/.", "قُرئ مكونا air وtraversing stem استقلالا، ثم أوقف الصامتان الساقطان حكم الصورة المجموعة."),
    346: R("در", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`در`: جريان أو امتداد؛ لا يسمي medicine أو gunpowder.", "جريان الدواء في البدن أو انتشار البارود أثر استعمالي لا معنى المادة؛ فصلت معنيي المدخلة."),
    347: R("شنغب", "LAW-GAP", "نص الحدث المجمد لـ`شنغب`: انتشار دقاق مع غين؛ لا يسمي squirrel، وس↔ش وگ↔غ غير مكتملين.", "حركة السنجاب أو انتشار شعره وصف عارض، وفوق غياب المعنى بقي مسار الصوت ناقصا."),
    348: R("نرم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`نرم`: نفاذ لطيف حاد من الأثناء؛ لا يسمي soft أو smooth.", "لفظ اللطف في كيفية النفاذ لا يساوي رخاوة الجسم أو نعومة سطحه، والشاهد الثاني غائب."),
    349: R("شبكر", "COMPOUND-BOUNDARY", "جسر المعنى: printer مفككة مباشرة إلى `چاپ` printing و`ـگر` لاحقة الفاعل.", "قُرئ المكونان استقلالا؛ لم يحول اسم الآلة المركب إلى مادة عربية واحدة."),
    351: R("مز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مز`: جمع أو فصل وامتلاء؛ لا يسمي boot.", "ضم الحذاء للقدم وظيفة احتواء عامة تشترك فيها الملابس، فلا تميز الخف أو الحذاء الطويل."),
    355: R("دنشق", "COMPOUND-BOUNDARY", "جسر المعنى: university مفككة مباشرة إلى `دانش` knowledge و`ـگاه` لاحقة المكان.", "قُرئ المكونان استقلالا؛ لم تورث الجامعة حكم المعرفة أو لاحقة المكان."),
    357: R("دلغط", "LAW-GAP", "نص الحدث المجمد لـ`دلغط`: امتداد من أعلى مع غلظ؛ لا يسمي tree، ومسار الصوامت غير مكتمل.", "امتداد الشجرة إلى أعلى هيئة عامة للنبات، وفوق غياب اسم النوع بقيت صفوف صوت بلا قانون."),
    359: R("جشر", "TOOL-GAP", "جسر المعنى: earring حاضر وتفكيكه المباشر مقروء، لكن /gušvâre/ فقد /v/ في الهيكل.", "قُرئ ear واللاحقة استقلالا، ثم أوقف الصامت الساقط حكم الصورة المجموعة."),
    361: R("دج", "LAW-GAP", "نص الحدث المجمد لـ`دج`: محكمتا حرفين بلا معنى fortress، وژ↔ج غير مسمى.", "الإحاطة والتحصين لم يثبتا تحت المرشح، وفجوة قانون الصامت الثاني تمنع الحكم أيضا."),
    362: R("ارب", "OUT-OF-SCOPE", "جسر المعنى: Europe اسم قارة لا معنى معجميا عاما إلى `ارب`.", "عزلت العلم الجغرافي؛ لم أحول موقع القارة أو اسمها التاريخي إلى حدث جذري."),
    364: R("ترس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ترس`: ابتعاد بقوة ودقة؛ لا يسمي fear أو terror.", "الفرار أثر محتمل للخوف لا معنى الانفعال، وشواهد العربية المفحوصة في الترس والستر."),
    365: R("مشت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مشت`: نفاذ بانتشار من الأثناء؛ لا يسمي fist أو punch.", "نفاذ الضربة أثر للقبضة لا معنى العضو أو الضربة، والشواهد لا تغلق المدخلة الفارسية."),
    366: R("بست", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بست`: جفاف ويبس؛ لا يسمي skin أو flesh.", "جفاف الجلد حالة عارضة له لا معنى الغطاء الجسدي، ولم أخلط flesh بالجلد."),
    367: R("بست", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بست`: جفاف ويبس؛ لا يسمي membrane أو crust.", "اليبس قد يصنع قشرة لكنه لا يساوي الغشاء ولا كل قشرة؛ فصلت المدخلة عن skin السابقة."),
    368: R("زنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زنج`: جفاف الباطن؛ لا يسمي rust.", "الصدأ تفاعل على المعدن لا مجرد فقد البلال، ولا شاهد عربي دقيق للمادة تحت المرشح."),
    369: R("زنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زنج`: جفاف الباطن؛ لا يسمي bell أو ring.", "فصلت الجرس والاتصال عن rust السابق؛ الصوت الصادر من الجرس فعل لا معنى المادة."),
    370: R("جنر", "TOOL-GAP", "جسر المعنى: animal حاضر، لكن /jānwar/ يحمل /w/ منطوقة أسقطها الهيكل.", "رفضت التحليل السطحي life + possessor قبل الحكم، ثم أوقف الصامت الساقط مقارنة الصورة."),
    371: R("زل", "LAW-GAP", "نص الحدث المجمد لـ`زل`: انزلاق عن مستو؛ لا يسمي frost أو dew، وژ↔ز غير مسمى.", "انزلاق الندى عن السطح حركة للماء لا معنى الصقيع أو الندى، وفوقه فجوة القانون الأول."),
    372: R("بدد", "COMPOUND-BOUNDARY", "جسر المعنى: phenomenon مفككة مباشرة إلى `پدید` apparent و`ـه` اللاحقة.", "قُرئ المكونان استقلالا؛ لم تورث الظاهرة حكم الصفة أو اللاحقة متعددة الوظائف."),
    373: R("بدد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بدد`: تفريق أو إبعاد يحدث فراغا؛ لا يسمي evident أو visible.", "انكشاف الشيء بعد تفريق ساتره نتيجة ممكنة، لا معنى الظهور نفسه؛ بقيت الصفة مفتوحة."),
    374: R("ججر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ججر`: محاكم حروف بلا معنى liver أو heart.", "كون الكبد في الجوف أو نسبة العاطفة إلى القلب سياقان خارجيان لا اسم العضو."),
    375: R("شكم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شكم`: دخول أو نفاذ يلزمه الجمع؛ لا يسمي belly أو abdomen.", "جمع البطن أعضاءه وظيفة احتواء عامة لا معنى العضو، ولا شاهد عربي للتسمية."),
    376: R("الصن", "COMPOUND-BOUNDARY", "جسر المعنى: cheap يرد إلى worth ولاحقة في طبقة تاريخية لا From مباشر مؤهل.", "وقف الاشتقاق الأوسط عند حده؛ لم يحول انقلاب valuable إلى cheap إلى حكم جذري عربي."),
    377: R("ضم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ضم`: جمع بضغط ولأم؛ لا يسمي snare أو trap.", "المصيدة تضم الفريسة بوظيفتها، لكن الضم لا يميز الآلة من كل وعاء أو رباط؛ بقي الاسم مفتوحا."),
    378: R("اشن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`اشن`: محاكم حروف بلا معنى ishan.", "حفظت وسم Tajik والغموض القاموسي، ولم أستخرج معنى من الرسم أو من مدخلة الضمير التالية."),
    379: R("اشن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`اشن`: محاكم حروف بلا معنى they أو he أو she.", "الوظيفة الضميرية لا تستخرج من رصف الحروف، وفصلت الضمير عن متجانسه السابق."),
    380: R("سبس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سبس`: امتداد دقيق مع اتصال؛ لا يسمي thanks أو gratitude.", "اتصال الشاكر بمن شكره أثر اجتماعي عام لا معنى الامتنان نفسه."),
    381: R("سبس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سبس`: امتداد دقيق مع اتصال؛ لا يسمي صيحة thanks.", "فصلت صيغة الخطاب عن اسم gratitude السابق؛ اتحاد الرسم لا ينقل الحكم."),
    382: R("ان", "LAW-GAP", "نص الحدث المجمد لـ`ان`: محكمتا حرفين بلا معنى that أو those، وآ↔ا غير مسمى.", "الإشارة وظيفة نحوية لا حدث جذري، وفوق غياب المعنى بقي أول صف صوتي بلا قانون."),
    383: R("ان", "LAW-GAP", "نص الحدث المجمد لـ`ان`: محكمتا حرفين بلا معنى that أو it، وآ↔ا غير مسمى.", "فصلت الضمير عن المحدد السابق، وبقيت فجوة القانون الأول مانعة للحكم."),
    384: R("جن", "TOOL-GAP", "جسر المعنى: young أو youthful حاضر، لكن /jawān/ فقد /w/ في الهيكل.", "لم تختزل الصفة إلى جيم ونون ولم تورثها معنى الستر؛ توقف الحكم قبل المدار."),
    385: R("جن", "TOOL-GAP", "جسر المعنى: youth أو young person حاضر، لكن /jawān/ فقد /w/ في الهيكل.", "فصلت الاسم عن الصفة السابقة، ثم أوقف الصامت الساقط المقارنة قبل الحكم."),
    387: R("احن", "LAW-GAP", "نص الحدث المجمد لـ`احن`: محاكم حروف بلا معنى iron، وآ↔ا غير مسمى.", "صلابة الحديد أو صدؤه وصفان للمعدن لا اسمه، ومسار الصامت الأول ناقص."),
    388: R("ارض", "LAW-GAP", "نص الحدث المجمد لـ`ارض`: محاكم حروف بلا معنى flour، وآ↔ا وصفوف أخرى غير مكتملة.", "طحن الحبوب فعل سابق على الدقيق لا معنى المادة، وفوقه لم يكتمل مسار الصوت."),
    389: R("وجا", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`وجا`: محاكم حروف بلا معنى place أو space.", "شغل شيء حيزا مثال سياقي لكل موجود، لا معنى المكان؛ لم أختَر مرشحا ناقص المسار."),
    390: R("جكر", "LAW-GAP", "نص الحدث المجمد لـ`جكر`: محاكم حروف بلا معنى promenade، وچ↔ج غير مسمى.", "الدوران أو المشي لم يثبت تحت المرشح، وفجوة الصامت الأول تمنع الحكم أيضا."),
    391: R("بغج", "COMPOUND-BOUNDARY", "جسر المعنى: small garden مفككة مباشرة إلى `باغ` garden و`ـچه` التصغير.", "قُرئ المكونان استقلالا؛ لم تورث الحديقة المصغرة حكم الأصل أو اللاحقة."),
    392: R("بز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بز`: نفاذ من مضيق؛ لا يسمي goat.", "مرور الماعز في الممرات سلوك للكائن لا اسم النوع، والشواهد العربية لا تسمي الحيوان."),
    393: R("سرك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سرك`: امتداد أو نفاذ بدقة؛ لا يسمي vinegar.", "نفاذ طعم الخل أو رائحته وصف حسي عام لا معنى السائل، وخبر الأصل متردد في اتجاه النقل."),
    394: R("مج", "LAW-GAP", "نص الحدث المجمد لـ`مج`: امتلاء واندفاع؛ لا يسمي kiss، وچ↔ج غير مسمى.", "ملامسة الشفتين لا تساوي الامتلاء أو الاندفاع، وفوق غياب المدار بقي قانون الصامت ناقصا."),
    395: R("بشت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بشت`: انتشار ظاهر؛ لا يسمي behind.", "امتداد ما خلف الجسم علاقة مكانية لا معنى حرف الجر، ولم أورثه من عضو الظهر."),
    396: R("بشم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بشم`: انتشار ظاهر؛ لا يسمي wool أو hair.", "انتشار الشعر على الجلد صفة للغلاف لا معنى المادة أو نوع الشعر."),
    397: R("بشم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بشم`: انتشار ظاهر؛ لا يسمي woollen أو woolly.", "لم أخترع لاحقة من الصفر الاشتقاقي، وفصلت الصفة عن اسم wool السابق."),
    398: R("بسمل", "COMPOUND-BOUNDARY", "جسر المعنى: fuzzy أو hairy مفككة مباشرة إلى `پشم` wool و`ـالو` اللاحقة.", "قُرئ المكونان استقلالا؛ لم تورث الصفة المجموعة حكم المادة أو اللاحقة."),
    399: R("كجر", "LAW-GAP", "نص الحدث المجمد لـ`كجر`: محاكم حروف بلا معنى bald، وچ↔ج غير مسمى.", "غياب الشعر معنى الصفة لا يثبت من محاكم المرشح، وفجوة الصامت الأوسط تمنع الحكم."),
    400: R("كجر", "LAW-GAP", "نص الحدث المجمد لـ`كجر`: محاكم حروف بلا معنى clitoris، وچ↔ج غير مسمى.", "فصلت العضو عن صفة bald السابقة، وبقي مسار الصامت الأوسط ناقصا."),
    401: R("ابر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ابر`: محاكم حروف بلا معنى eyebrow.", "قوس الحاجب أو علوه هيئة للعضو لا اسمه، والشاهد العربي المستقل الثاني غائب."),
    405: R("شن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شن`: انتشار دقاق من الأثناء؛ لا يسمي suffix of place.", "وظيفة لاحقة المكان لا تستخرج من انتشار المادة، ولم يحول الخبر التاريخي إلى تفكيك مباشر."),
    406: R("درج", "TOOL-GAP", "جسر المعنى: lake مفككة مباشرة إلى `دریا` و`ـچه`، لكن /daryāča/ فقد /y/ في الهيكل.", "قُرئ المكونان استقلالا، ثم أوقف الصامت الساقط وفجوة المسار حكم الصورة المجموعة."),
    407: R("بلند", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بلند`: تمكن وحوز بشدة؛ لا يسمي tall أو high.", "العلو قد يمنح التمكن لكنه ليس معنى الطول أو الارتفاع، والشواهد لا تغلق الصفة."),
    408: R("جنج", "COMPOUND-BOUNDARY", "جسر المعنى: warlike أو military مشتقة من noun `جنگ` بلا From X + Y مؤهل.", "وقف الاشتقاق الاسمي عند الحد؛ لم أخترع لاحقة ولم أورث الصفة حكم الحرب."),
    409: R("كدك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كدك`: تعامل مع قشر شديد اللصوق؛ لا يسمي child أو infant.", "صغر الطفل أو تعلقه بأهله وصفان عارضان لا معنى العمر أو الشخص."),
    410: R("لغثن", "LAW-GAP", "نص الحدث المجمد لـ`لغثن`: تخلل بمائع كثيف؛ لا يسمي pour أو spill، ومسار الصوت غير مكتمل.", "وجود المائع في الحدث لا يساوي سكبه، وفوق غياب الاتجاه بقيت صفوف صوت بلا قانون."),
    411: R("شزن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شزن`: محاكم حروف بلا معنى needle.", "نفاذ الإبرة أو حدتها وظيفة وشكل للأداة لا اسمها، ولا حدث مجمد دقيق تحت المرشح."),
    412: R("خش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خش`: تجمع دقاق خشنة أو حادة في الأثناء؛ لا يغلق bunch أو cluster.", "التجمع يلامس معنى العنقود، لكن الشاهدين في الدخول والنفاذ وصغار الدواب لا يثبتان تسمية المجموعة؛ بقي صدى مفتوحا."),
    413: R("الدن", "TOOL-GAP", "جسر المعنى: bring حاضر، لكن /āwardan/ يحمل /w/ منطوقة أسقطها الهيكل.", "رفضت تركيب Proto-Iranian التاريخي prefix + root تفكيكا مباشرا، ثم أوقف الصامت الساقط الحكم."),
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
            raise AssertionError(f"تغير عداد نسخة v10 في {name}")
        if len(data.get("both") or []) != expected_both or len(data.get("sound_only") or []) != expected_sound:
            raise AssertionError(f"تغير طول قوائم نسخة v10 في {name}")


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
            if row.rank > 330 and len(fresh) < 70:
                internal_skips.append(row.rank)
            continue
        seen.add(key)
        if row.rank <= 330:
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
        "هوا": {1232}, "پیما": set(), "چاپ": {2363}, "ـگر": {10503},
        "دانش": {1489}, "ـگاه": {7461}, "گوش": {899}, "ـواره": {16060},
        "پدید": {1566}, "ـه": {7112, 7113, 7114}, "باغ": {838},
        "ـچه": {7513}, "پشم": {1676}, "ـالو": {14774}, "دریا": {970, 971},
    }
    fan_counts = {
        "هوا": 0, "پیما": 20, "چاپ": 60, "ـگر": 80, "دانش": 9,
        "ـگاه": 72, "گوش": 120, "ـواره": 38, "پدید": 18, "ـه": 0,
        "باغ": 30, "ـچه": 60, "پشم": 6, "ـالو": 40, "دریا": 60,
    }
    for word, expected in expected_indices.items():
        actual = {index for index, _entry in grouped.get(word, [])}
        if actual != expected:
            raise AssertionError(f"تغير جرد مكون {word}: {sorted(actual)}")
        fan = tuple(H.FAN.rank(word, H.FAN.fan(word, "persian"), "persian"))
        if len(fan) != fan_counts[word]:
            raise AssertionError(f"تغيرت مروحة المكون {word}: {len(fan)}")
    expected_raw = {
        "هوا": {1307}, "پیما": set(), "چاپ": {2479, 2480}, "ـگر": {12956},
        "دانش": {1572}, "ـگاه": {8752}, "گوش": {957}, "ـواره": {19121},
        "پدید": {1649}, "ـه": {8351, 8352, 8353, 8354}, "باغ": {895},
        "ـچه": {8808}, "پشم": {1766}, "ـالو": {17697}, "دریا": {1030, 1031},
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
    if review.verdict == "COMPOUND-BOUNDARY":
        return "وقف الحكم عند حد المركب؛ لم تورث الصورة المجموعة حكم مكون ولم يخترع تفكيك."
    if review.verdict == "LAW-GAP":
        return "طريق المعنى مفحوص، لكن مسار الصوت يحوي صفا غير مسمى؛ لم يصدر حكم موجب."
    if review.verdict == "TOOL-GAP":
        return "صف الحوض أسقط صامتا منطوقا؛ توقف العضو قبل الحكم ولم يعوض الصامت يدويا."
    if review.verdict == "OUT-OF-SCOPE":
        return "الشرح اسم علم جغرافي لا معنى معجميا عاما؛ أحيل العضو إلى طبقة الأعلام المنفصلة."
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
    if rank in TOOL_GAPS:
        lines.extend([
            f"- عطب الهيكل: {TOOL_GAPS[rank]}",
            "- بعد قراءة المكونات أوقف TOOL-GAP حكم الصورة المجموعة؛ لا حكم من هيكل ناقص.",
        ])
    return lines


def make_card(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit) -> str:
    card = R29.make_card(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit)
    card = card.replace("الجولة 29،", "الجولة 30،")
    card = card.replace("اسم الشهر", "اسم العلم الجغرافي")
    if item.row.rank in BLOCKED_BOUNDARIES and "بلا مكونات مخترعة" not in card:
        lines = card.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("- الخطوة صفر:"):
                lines[index] = "- الخطوة صفر: From X + Y مباشر فقط؛ COMPOUND-BOUNDARY بلا مكونات مخترعة."
                break
        card = "\n".join(lines) + "\n"
    return card


def validate_decisions(selected, raw_entries, decisions, ranked_by_rank, sense_map) -> None:
    if set(REVIEWS) != set(SOUND_RANKS):
        raise AssertionError("جدول المدار اليدوي لا يغطي الرتب السبعين")
    parsed = {item.row.rank for item in selected if P25.direct_from_plus(raw_entries[item.row.rank]["etymology"])}
    if parsed != EXACT_DECOMPOSITIONS:
        raise AssertionError(f"تغيرت أسطر From X + Y المباشرة: {sorted(parsed)}")
    expected_verdicts = {
        "COMPOUND-BOUNDARY": 7,
        "LAW-GAP": 13,
        "OPEN-CANDIDATE": 42,
        "OUT-OF-SCOPE": 1,
        "TOOL-GAP": 7,
    }
    if Counter(review.verdict for review in REVIEWS.values()) != Counter(expected_verdicts):
        raise AssertionError("تغير توزيع الأحكام اليدوي")
    for item, decision in zip(selected, decisions):
        row = item.row
        candidates = {candidate for candidate, _score in ranked_by_rank[row.rank]}
        if decision.candidate not in candidates or decision.candidate not in row.candidates_found:
            raise AssertionError(f"مرشح الرتبة {row.rank} خارج المروحة الحية أو أعضاء الحوض")
        complete = H.route_complete(row, decision.candidate)
        if decision.verdict == "LAW-GAP" and complete:
            raise AssertionError(f"LAW-GAP بلا صف مفقود في الرتبة {row.rank}")
        if decision.verdict == "OPEN-CANDIDATE" and not complete:
            raise AssertionError(f"OPEN-CANDIDATE بمسار ناقص في الرتبة {row.rank}")
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
    headings = re.findall(r"^### (WO-B-R30-SOUND-\d{5}):", joined, re.MULTILINE)
    if headings != [item.heading for item in selected]:
        raise AssertionError("معرفات الجولة 30 لا تطابق النافذة")
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
            f"## الجولة الثلاثون، دفعة sound_only رقم {number}", "",
            f"- الوقت: {now}، Africa/Cairo.",
            f"- رشح وكتب: {len(batch)}؛ المواضع المقروءة المتجاوزة داخل المدى: {skipped}.",
            f"- المواضع: من {batch[0].heading} إلى {batch[-1].heading}.",
            f"- توزيع الأحكام: {distribution}.",
            "- طريق المعنى: سمي من جسر معنى صريح أو من نص الحدث المجمد في كل بطاقة.",
            "- المدار: كتب يدويا لكل عضو، ولم يغلق صدى لين على أنه أثر محكم.",
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
    lines.extend([
        "## حصيلة الجولة الثلاثين", "",
        f"- حمل `persian.md` مرة واحدة؛ أزواج WO-B المقروءة={stats['pair_count']}؛ المتجاوز داخل النافذة={', '.join(map(str, stats['skipped']))}.",
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- نطاق الصوت الجديد: الرتب 331-413 بعد WO-B-R29-SOUND-00330، مع تجاوز الأزواج الثلاثة عشر المقروءة فقط.",
        "- لم يغلق أثر محكم أو اتجاه دخول في هذه النافذة؛ ظلت الأصداء اللينة OPEN-CANDIDATE.",
        "- التفكيك المباشر المؤهل: S00345، S00349، S00355، S00359، S00372، S00391، S00398، S00406؛ قرئت المكونات استقلالا.",
        "- الحدود غير المباشرة: S00376 اشتقاق أوسط تاريخي، وS00408 From noun بلا لاحقة مسماة؛ لم يخترع مكون.",
        "- نتائج التحليل المرفوضة قبل الحكم: S00370 surface analysis، وS00413 تركيب Proto-Iranian تاريخي؛ لم تحولا إلى From X + Y نهائي.",
        "- فجوات الأداة: S00345، S00359، S00370، S00384، S00385، S00406، S00413؛ لم تعوض الصوامت المنطوقة الساقطة.",
        "- فجوات القانون: S00347، S00357، S00361، S00371، S00382، S00383، S00387، S00388، S00390، S00394، S00399، S00400، S00410.",
        "- أحواض `nucleus-sweep-*.json` التسعة الحالية v10 قرئت كاملة من القرص، وثبت الحجم وSHA-256 والعدادات لكل ملف قبل الانتخاب.",
        f"- أكبر بطاقة: {max_size} بايت، {max_item.heading}؛ كل البطاقات دون 5KB.",
        "- لم تفعل طبقة البرهان، ولم يبن ملف مشترك، ولم يقع ship، ولم يستعمل git.",
        "", f"<!-- {MARKER}:END -->", "", DONE_LINE,
    ])
    return "\n".join(lines)


def validate_existing(reading_text: str, report_text: str) -> None:
    match = re.search(rf"<!-- {re.escape(MARKER)}:START -->(.*?)<!-- {re.escape(MARKER)}:END -->", reading_text, re.DOTALL)
    if not match:
        raise AssertionError("محضر الجولة موجود وبطاقاتها غائبة")
    headings = re.findall(r"^### (WO-B-R30-SOUND-\d{5}):", match.group(1), re.MULTILINE)
    expected = [f"WO-B-R30-SOUND-{rank:05d}" for rank in SOUND_RANKS]
    if headings != expected:
        raise AssertionError("مقطع الجولة 30 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(DONE_LINE):
        raise AssertionError("سطر DONE30 ليس خاتمة التقرير")


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
        print("ROUND30 ALREADY PRESENT AND VALID")
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
    R29.TOOL_GAPS = TOOL_GAPS

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
        "## الجولة الثلاثون: متابعة حوض sound_only (2026-08-26)\n\n"
        "- النطاق: 70 عضوا طازجا بعد WO-B-R29-SOUND-00330؛ من الرتبة 331 إلى 413 مع تجاوز 332 و350 و352 و353 و354 و356 و358 و360 و363 و386 و402 و403 و404 لأنها مقروءة؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ طريق المعنى مسمى، والمدار اليدوي حاسم، والأصداء مفصولة عن الآثار المحكمة.\n"
        "- لقطة الأحواض: قرئت ملفات nucleus-sweep-*.json التسعة الحالية v10 من القرص وثبتت بصماتها وعداداتها قبل الانتخاب.\n\n"
        + "\n".join(texts[:35])
        + "\n## الدفعة الثانية: متابعة sound_only بعد الرتبة 375\n\n"
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
    print("ROUND30 READY")
    print("NUCLEUS_V10_FILES", len(NUCLEUS_SNAPSHOT), "SHA256_AND_COUNTS_OK")
    print("SKIPPED", ",".join(map(str, stats["skipped"])))
    print("BATCHES", *BATCH_SIZES, "SELECTED", len(selected))
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("EXACT_FROM_PLUS", " ".join(f"S{rank:05d}" for rank in sorted(EXACT_DECOMPOSITIONS)))
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
    print("ROUND30 WRITTEN")
    print(DONE_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
