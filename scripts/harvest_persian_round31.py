# -*- coding: utf-8 -*-
"""المسار B، الجولة 31: متابعة حوض sound_only في دفعتين من 35 بطاقة."""

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

import harvest_persian_round30 as R30  # noqa: E402

R29 = R30.R29
R28 = R30.R28
H = R30.H
P = R30.P
P25 = R30.P25
READING = ROOT / "04-cross-linguistic" / "readings" / "persian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-B.md"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-persian.json"
NUCLEUS_DIR = ROOT / "04-cross-linguistic" / "exploration"
LEXICON = ROOT / "data" / "branch-lexicons" / "persian.json"
RAW_LEXICON = ROOT / "Resources" / "persian" / "kaikki.org-dictionary-Persian.jsonl"
MARKER = "LANE-B-PERSIAN-ROUND31-2026-08-26"
CARD_LIMIT = 5120
SOUND_RANKS = (
    414, 415, 416, 417, 418, 419, 420, 421, 422, 423, 424, 425, 426, 427,
    428, 429, 430, 431, 432, 433, 434, 435, 436, 437, 438, 439, 440, 442,
    443, 444, 445, 446, 447, 448, 449, 450, 451, 452, 453, 454, 455, 456,
    457, 458, 459, 460, 461, 462, 463, 464, 465, 466, 467, 468, 469, 470,
    471, 472, 473, 475, 476, 477, 480, 481, 482, 483, 485, 486, 487, 488,
)
BATCH_SIZES = (35, 35)
DONE_LINE = "LANE-B DONE31 70 WO-B-R31-SOUND-00488"
EXPECTED_SKIPS = (441, 474, 478, 479, 484)

NUCLEUS_SNAPSHOT = {
    "nucleus-sweep-ancient_greek.json": (7978449, "321bd4d5839088a4028394ce83c2ea5e16d43d4ac3a0e1b67983cf5491ff6024", 2526, 16555),
    "nucleus-sweep-english_middle.json": (3485629, "0975798b1b19548fd476271e0000e23a41312889fc53da73e069b96e1776ae75", 1658, 7746),
    "nucleus-sweep-english_old.json": (1317589, "7525889e4a2eae94c3ffa612ed538b4d825c430a2065237a827434341d5902ce", 515, 3372),
    "nucleus-sweep-gothic.json": (1438327, "a89d63397b0240bc5593e58d407ea6c31b58e7757257156a5421696822c8000d", 379, 3038),
    "nucleus-sweep-latin.json": (19045264, "d8e5c63b46c297e2592e23fda27fe6e3759228233a8404d30fa4ee55893ca557", 7413, 38640),
    "nucleus-sweep-old_irish.json": (962467, "8af0da2777c1049cee1422c30f6be3196f87b546198ecd23c5841f6e4cd9f2cd", 314, 2704),
    "nucleus-sweep-old_norse.json": (1389955, "3a32fe170d89b069e23262eb6532d77b0a5ea406bca917c800aae9d700a6a728", 518, 3706),
    "nucleus-sweep-persian.json": (5506779, "88a70b7d91917ca7ee9b1b7a0bb7dddf618538ecc9899b9c6fa838a82536fa8d", 1714, 13219),
    "nucleus-sweep-welsh.json": (5865541, "c91fb40dcb00978f898a7598d39240915f1a12a762598404152b866c6f5415ff", 1508, 15765),
}

EXPECTED_ENTRY_INDEX = dict(zip(SOUND_RANKS, (
    1766, 1767, 1769, 1777, 1784, 1787, 1799, 1801, 1802, 1806,
    1813, 1815, 1816, 1817, 1827, 1829, 1831, 1832, 1833, 1835,
    1836, 1846, 1856, 1859, 1860, 1865, 1868, 1877, 1880, 1882,
    1888, 1890, 1891, 1892, 1893, 1901, 1906, 1908, 1909, 1917,
    1925, 1929, 1938, 1945, 1951, 1952, 1954, 1959, 1960, 1961,
    1967, 1968, 1979, 1982, 1998, 1999, 2002, 2027, 2028, 2034,
    2036, 2037, 2061, 2062, 2063, 2066, 2080, 2082, 2084, 2091,
)))

EXPECTED_RAW_LINE = dict(zip(SOUND_RANKS, (
    1859, 1860, 1862, 1870, 1878, 1881, 1893, 1895, 1896, 1900,
    1907, 1911, 1912, 1913, 1923, 1925, 1927, 1929, 1930, 1932,
    1933, 1944, 1954, 1957, 1958, 1964, 1967, 1976, 1980, 1982,
    1988, 1990, 1991, 1992, 1993, 2001, 2006, 2008, 2009, 2017,
    2025, 2029, 2038, 2045, 2051, 2052, 2054, 2059, 2060, 2061,
    2070, 2071, 2082, 2085, 2101, 2102, 2105, 2130, 2131, 2137,
    2140, 2141, 2165, 2166, 2167, 2170, 2185, 2188, 2190, 2197,
)))

EXACT_DECOMPOSITIONS = {427, 449, 466, 472}
EXPECTED_COMPONENTS = {
    427: ("فرود", "ـگاه"),
    449: ("پر", "ـش"),
    466: ("پاییز", "ـی"),
    472: ("پر", "ی"),
}
COMPONENT_READINGS = {
    427: "`فرود`: entries[8155-8156] والخام 9547-9548 لمعنيي down وlanding، ومروحتها 12: OPEN-CANDIDATE. `ـگاه`: entries[7461] والخام 8752 لاحقة مكان أو زمان، ومروحتها 72: MORPHOLOGY-GAP.",
    449: "`پر`: الجذع الفعلي حاضر في الخام 336 وغائب من branch-lexicons، ومروحتها 40: COMPONENT-GAP. `ـش`: entries[10302] والخام 12674 لاحقة اسم الحدث، ومروحتها صفر: MORPHOLOGY-GAP.",
    466: "`پاییز`: entries[1967] والخام 2070 لمعنى autumn، ومروحتها 60، لكن هيكلها أسقط /y/: TOOL-GAP. `ـی`: entries[6328] والخام 7421 لاحقة صفة، ومروحتها صفر: MORPHOLOGY-GAP.",
    472: "`پر`: entries[316] والخام 334 لمعنى full، ومروحتها 40: OPEN-CANDIDATE. `ـی`: entries[6329] والخام 7422 لاحقة اسم مجرد، ومروحتها صفر: MORPHOLOGY-GAP.",
}
BLOCKED_BOUNDARIES = {
    455: "يسمي الخبر تفكيكا في طبقة Proto-Iranian من السابقة *wi والجذر *maiH، لا From X + Y نهائيا مباشرا للمدخلة الحالية.",
    488: "يعرض الخبر احتمالا تاريخيا من `زین` و`ـدان` بصيغة Perhaps originally، لا تفكيكا نهائيا مباشرا مؤهلا.",
}
REJECTED_ANALYSES = {
    456: "يقول الخبر Composed of `پروند` + `ـه` ولا يصدر سطر From X + Y النهائي المباشر.",
    465: "يسمي الخبر تركيبا تاريخيا من *pati و*jimáh، لا From X + Y نهائيا مباشرا للكلمة الحديثة.",
}
TOOL_GAPS = {
    456: "الصورة `پرونده` منقوطة /parwanda/، لكن الهيكل أسقط /w/ المنطوقة.",
    465: "الصورة `پاییز` منقوطة /pâyiz/، لكن الهيكل أسقط /y/ المنطوقة.",
    466: "الصورة `پاییزی` منقوطة /pâyizi/، لكن هيكل المكون `پاییز` أسقط /y/ المنطوقة.",
    480: "الصورة `نود` منقوطة /navad/، لكن الهيكل أسقط /w/ المنطوقة.",
    481: "الصورة `پنجاه` منقوطة /panjâh/، لكن الهيكل أسقط /h/ النهائية المنطوقة.",
    483: "الصورة `دویست` منقوطة /devist/، لكن الهيكل أسقط /v/ المنطوقة.",
}


@dataclass(frozen=True)
class SelectedRow:
    row: H.SweepRow

    @property
    def key(self) -> str:
        return f"S{self.row.rank:05d}"

    @property
    def heading(self) -> str:
        return f"WO-B-R31-SOUND-{self.row.rank:05d}"


Review = R29.Review
R = R29.R

# سجل قراءة يدوي. لا يشتق الحكم من best ولا من وزن المروحة.
REVIEWS = {
    414: R("رستن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رستن`: نفاذ بامتداد؛ لا يسمي escape أو free.", "النفاذ قد يصف حركة الهارب بعد الخلاص، لكنه لا يساوي التحرر أو الانفلات؛ والشاهد العربي اسم موضع."),
    415: R("رستن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رستن`: نفاذ بامتداد؛ لا يسمي grow أو sprout.", "امتداد النابت نتيجة للنمو لا معنى الإنبات نفسه؛ فصلت المتجانس عن escape السابق."),
    416: R("ددن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ددن`: محاكم حروف بلا معنى see أو look.", "عمل العين والمشاهدة لا يستخرجان من تتابع الدالين؛ والشواهد العربية في اللهو والسيف الكهام."),
    417: R("خس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خس`: القلة والنقص؛ لا يسمي wet أو soaked.", "نقص الجفاف أثر للبلل لا معنى الرطوبة نفسها؛ بقيت الصفة خارج المدار."),
    418: R("مسط", "SEMITIC-SOURCE-TRANSMISSION", "جسر المعنى: yoghurt هي المدخلة نفسها، وخبر الأصل يسمي السريانية الكلاسيكية `mastā` مانحا مباشرا.", "سمى المصدر مانحا ساميا وصورة ومعنى اللبن المخمر؛ أغلق النقل السامي نتيجة إيجابية لا إرثا مبسوطا."),
    419: R("قك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`قك`: محكمتا حرفين بلا معنى flea.", "القفز أو القرص فعل للبرغوث لا اسم النوع، ولم أستخرج الحيوان من عادته."),
    420: R("شتر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شتر`: التفرق؛ لا يسمي camel.", "تفرق أصابع الخف أو انقلاب الشفة هيئة للحيوان لا معنى الجمل؛ وشواهد العربية في جفن العين."),
    421: R("بست", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بست`: الجفاف واليبوسة؛ لا يسمي twenty.", "لم أحول تركيب العدد التاريخي إلى حدث، واتحاد الرسم لا يثبت القيمة العددية."),
    422: R("سي", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سي`: محكمتا حرفين بلا معنى thirty.", "القيمة العددية لا تستخرج من المد أو الصفير، ولا شاهد عربي يسمي الثلاثين."),
    423: R("صد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`صد`: اعتراض كثيف يوقف النفاذ؛ لا يسمي hundred.", "بلوغ المائة قد يوقف العد في سياق اصطلاحي، لكنه لا يساوي العدد؛ بقيت القيمة خارج المدار."),
    424: R("شستن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شستن`: محاكم حروف بلا معنى wash.", "انتشار الماء أثناء الغسل وصف للعمل لا حدث مجمد دقيق تحته؛ والشاهد العربي علم شخص."),
    425: R("ترش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ترش`: ابتعاد بقوة ودقة؛ لا يسمي sour أو fermented.", "انقباض الذوق عن الحامض أثر حسي على المتذوق لا معنى الطعم؛ والشواهد في الخفة والنزق."),
    426: R("لول", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`لول`: محاكم حروف جوفاء بلا معنى tube أو pipe.", "استدارة الأنبوب أو جريان المادة فيه شكل ووظيفة عامة، لا اسم الأداة؛ والشواهد في الشدة."),
    427: R("فردج", "COMPOUND-BOUNDARY", "جسر المعنى: airport مفككة مباشرة إلى `فرود` landing و`ـگاه` لاحقة المكان.", "قُرئ المكونان استقلالا؛ لم تورث المطار حكم الهبوط أو لاحقة المكان."),
    428: R("برج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`برج`: بروز ناصع قوي؛ لا يسمي leaf أو petal.", "بروز الورقة من الغصن مرحلة في نموها لا معنى الورقة؛ لم أحول الهيئة إلى اسم الجزء."),
    429: R("برج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`برج`: بروز ناصع قوي؛ لا يسمي intention أو desire.", "ظهور القصد في الفعل أثر لاحق للرغبة لا معنى النية نفسها؛ فصلت المتجانس عن الورقة."),
    430: R("جح", "LAW-GAP", "نص الحدث المجمد لـ`جح`: محكمتا حرفين بلا معنى shit، ومسار ه↔ح غير مسمى.", "الإخراج من الجوف قد يلامس فعل التغوط لا اسم الخارج، وفوقه بقي صف صوت بلا قانون."),
    431: R("ريش", "ROOT-TRACE", "جسر المعنى: beard شعر نابت منتشر على ظاهر جلد الحي، وهو نص الحدث المجمد لـ`ريش` نفسه.", "مدار 1: اللحية كسوة شعر تنبت على جلد الوجه؛ وشاهدا ريش الطائر يثبتان النبت المنتشر الكاسي مباشرة."),
    432: R("رش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رش`: انتشار أشياء دقيقة طرية؛ لا يسمي wound أو scar.", "انتشار الدم أو رشحه أثر محتمل للجرح لا معنى الجرح أو الندبة؛ فصلت المتجانس عن beard."),
    433: R("خشك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خشك`: تجمع دقاق خشنة أو حادة؛ لا يسمي dry أو arid.", "الخشونة قد ترافق الجفاف لكنها لا تساويه، وشواهد الرسم العربية أسماء وأعلام لا صفة dry."),
    434: R("جرشن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جرشن`: استرسال مع انتشار دقاق؛ لا يسمي hungry.", "حركة الجائع في طلب الطعام أو خلو بطنه سياقان خارجيان لا معنى الجوع."),
    435: R("رز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رز`: حركة مع تماسك؛ لا يسمي vine أو vineyard.", "التفاف الكرمة أو امتدادها هيئة نباتية عامة لا اسم الكرم أو موضعه."),
    436: R("جز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جز`: التميز والانفصال في الكتلة؛ لا يسمي fart.", "خروج الريح من الجوف انفصال لمادة، لكنه وصف عام للإخراج لا معنى الحدث المعجمي."),
    437: R("دج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دج`: محكمتا حرفين بلا معنى cooking pot.", "احتواء القدر للطعام وتسخينه وظيفتان لا تسميان الوعاء؛ وخبر الأصل غير سامي."),
    438: R("ته", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ته`: الفراغ والباطل؛ لا يسمي bottom أو base.", "فراغ ما تحت الشيء ممكن في وعاء لا معنى القاع أو الأساس؛ والشواهد العربية حكاية صوت."),
    439: R("لن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`لن`: محكمتا حرفين بلا معنى lair أو den.", "احتواء الوكر للحيوان وظيفة مكانية لا تستخرج من حرف النفي العربي؛ بقي اسم المسكن مفتوحا."),
    440: R("يا", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`يا`: محكمتا حرفين بلا معنى or أو either.", "الوظيفة العاطفة لا تستخرج من حرف النداء العربي؛ اتحاد الرسم لا يورث الوظيفة."),
    442: R("اشك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`اشك`: محاكم حروف بلا معنى tear from the eye.", "سريان الدمع أو تفرقه وصف للحركة لا اسم القطرة؛ والشاهد العربي في قرب الخروج."),
    443: R("بردن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بردن`: تجرد وخلوص مع حدث الدال؛ لا يسمي fly أو jump.", "انفصال القافز عن الأرض لحظة من الفعل لا معنى الطيران أو الوثب؛ والشواهد اسم موضع."),
    444: R("بردن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بردن`: تجرد وخلوص مع حدث الدال؛ لا يسمي carry أو take.", "إخراج المحمول من موضعه أثر للحمل لا معنى نقله؛ فصلت المدخلة عن fly السابقة."),
    445: R("هنز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`هنز`: رخاوة متجمع في الباطن؛ لا يسمي still أو yet.", "بقاء الزمن أو قرب الحد الوظيفي لا يتولد من الأذى المذكور في الشواهد؛ بقي الظرف مفتوحا."),
    446: R("حشتن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`حشتن`: جفاف وخشونة مع انتشار؛ لا يسمي want أو ask.", "قوة الطلب أو إلحاحه درجة في الاستعمال لا معنى الإرادة أو السؤال؛ لم أستخرج الوظيفة المستقبلية."),
    447: R("مخ", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مخ`: توسط مادة رخوة أو خروجها؛ لا يسمي nail.", "اختراق المسمار مادة رخوة وظيفة للأداة لا معنى المسمار؛ وشواهد العربية في النخاع."),
    448: R("جرج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جرج`: الاسترسال والامتداد؛ لا يسمي wolf.", "جري الذئب أو امتداد سيره فعل للحيوان لا اسم النوع؛ والشواهد في القلق والطريق."),
    449: R("برش", "COMPOUND-BOUNDARY", "جسر المعنى: jump مفككة مباشرة إلى جذع `پر` من `پریدن` و`ـش` لاحقة الحدث.", "قُرئ الجذع واللاحقة استقلالا؛ لم تورث الصورة المجموعة حكم البرش العربي."),
    450: R("بستن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بستن`: الجفاف واليبوسة؛ لا يسمي close أو bind.", "يبس الرباط بعد شده أثر عارض، وشواهد الرسم في البستان المعرب لا فعل الإغلاق."),
    451: R("رشذن", "LAW-GAP", "نص الحدث المجمد لـ`رشذن`: انتشار دقاق طرية؛ لا يسمي arrive أو reach، ود↔ذ غير مسمى.", "بلوغ الدقائق موضعا نتيجة لحركتها لا معنى الوصول، وفوقه بقي صف صوت بلا قانون."),
    452: R("جر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جر`: الاسترسال والامتداد؛ لا يسمي knot أو tie.", "العقدة توقف الاسترسال أو تجمع الطرفين، لكن التضاد أو الوظيفة لا يساوي اسم العقدة."),
    453: R("سختن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سختن`: لين يسمح بالاختراق أو الانقياد؛ لا يسمي make أو build.", "قابلية المادة للتشكيل شرط سابق للصنع لا معنى الإنشاء؛ وشواهد الرسم أعلام وصناعة جلد."),
    454: R("جز", "LAW-GAP", "نص الحدث المجمد لـ`جز`: التميز والانفصال؛ لا يسمي something، وچ↔ج غير مسمى.", "كون الشيء متميزا عن غيره لازم عام لكل موجود لا معنى الضمير، وفوقه فجوة القانون."),
    455: R("جم", "COMPOUND-BOUNDARY", "جسر المعنى: lost مردودة إلى تركيب Proto-Iranian تاريخي، لا تفكيك نهائي مؤهل.", "وقفت السابقة التاريخية والجذر عند طبقتهما؛ لم أحول decrease إلى معنى الضياع الحديث."),
    456: R("برند", "TOOL-GAP", "جسر المعنى: case أو file حاضر، لكن /parwanda/ يحمل /w/ منطوقة أسقطها الهيكل.", "رفضت Composed of غير المؤهل تفكيكا نهائيا، ثم أوقف الصامت الساقط حكم الصورة."),
    457: R("بندق", "LAW-GAP", "نص الحدث المجمد لـ`بندق`: امتداد وبناء؛ لا يسمي servitude، وگ↔ق غير مسمى.", "البند أو الرباط أصل محتمل للعبودية، لكن المدخلة لم تفكك نهائيا وفوقها فجوة قانون."),
    458: R("بنكل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بنكل`: امتداد وبناء؛ لا يسمي bungalow.", "كون البيت مبنيا وصف يشترك فيه كل مسكن، ولا خبر أصل في المدخلة يثبت اتجاها إلى العربية."),
    459: R("شح", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شح`: جفاف الجرم أو حدته مع عرض؛ لا يسمي horn أو branch.", "الصلابة والحدة تصفان القرن وبعض الأغصان، لكنهما لا تميزان العضو أو الجزء؛ بقي الصدى لينا."),
    460: R("شح", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شح`: جفاف الجرم أو حدته مع عرض؛ لا يسمي tree branch أو arm.", "امتداد الفرع أو صلابته هيئة عامة، وفصلت المدخلة عن horn السابقة بلا توارث."),
    461: R("ميي", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ميي`: محاكم حروف بلا معنى wine.", "السيولة أو المد في النطق لا يسميان الشراب المسكر، وشواهد العربية أسماء أعلام."),
    462: R("بر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بر`: التجرد والخلوص؛ لا يسمي on أو upon.", "الوظيفة المكانية للحرف لا تستخرج من البر خلاف البحر؛ بقي حرف الجر خارج المدار."),
    463: R("بر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بر`: التجرد والخلوص؛ لا يسمي chest أو side.", "انكشاف الصدر أو بروزه هيئة للجسم لا معنى العضو؛ فصلت المتجانس عن حرف الجر."),
    464: R("بر", "ROOT-ECHO", "جسر المعنى: fruit يلاقي `البرير`، ثمر الأراك، في شاهدين عربيين، لكن الحدث المجمد لـ`بر` هو التجرد والخلوص.", "مدار الاسم المعجمي مباشر في جنس الثمر، لكن رجل الحدث ألين من التطابق المعجمي؛ أغلق ROOT-ECHO لا أثرا محكما."),
    465: R("بز", "TOOL-GAP", "جسر المعنى: autumn حاضر، لكن /pâyiz/ يحمل /y/ منطوقة أسقطها الهيكل.", "رفضت تركيب Proto-Iranian التاريخي تفكيكا نهائيا، ثم أوقف الصامت الساقط الحكم."),
    466: R("بز", "TOOL-GAP", "جسر المعنى: autumnal مفككة مباشرة، لكن مكون /pâyiz/ فقد /y/ المنطوقة في الهيكل.", "قُرئ مكونا autumn واللاحقة استقلالا، ثم أوقف الصامت الساقط حكم الصورة المجموعة."),
    467: R("كشف", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كشف`: تنحي الغطاء وظهور ما تحته؛ لا يسمي tortoise أو Cancer.", "انكشاف رأس السلحفاة من الدرع حركة للعضو لا اسم الحيوان، واتحاد الرسم لا يورث معنى reveal."),
    468: R("خرد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خرد`: بقاء الشيء على أصله دون استعمال؛ لا يسمي bit أو part.", "الجزء الصغير قد يبقى من كسر شيء، لكن البقاء ليس معنى القطعة؛ والتحليل السطحي غير مؤهل."),
    469: R("كمن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كمن`: تغطية الشيء بغطاء زائد؛ لا يسمي bow أو arch.", "انحناء القوس قد يغطي حيزا، لكنه لا يميز السلاح أو الشكل؛ وشواهد العربية في الاختفاء."),
    470: R("قشنز", "LAW-GAP", "جسر المعنى: `القشنيزة` عشب يسميه شاهدان عربيان، لكن گ↔ق غير مسمى في مسار الصوت.", "اتحد اسم النبات وصورته الدلالية، ومنعت فجوة القانون إصدار أثر أو اتجاه نقل بلا صف مسمى."),
    471: R("خم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خم`: الاضطمام على مائع كثير أو خور؛ لا يسمي raw أو uncooked.", "رخاوة النيء أو مائيته صفة لبعض المواد لا معنى عدم الطبخ؛ والشواهد في تغير الرائحة والكنس."),
    472: R("بر", "COMPOUND-BOUNDARY", "جسر المعنى: fullness مفككة مباشرة إلى `پر` full و`ـی` لاحقة الاسم المجرد.", "قُرئ المكونان استقلالا؛ لم تورث الصورة المجموعة حكم `بر` العربي."),
    473: R("بر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بر`: التجرد والخلوص؛ لا يسمي day before yesterday.", "ترتيب اليوم في الماضي وظيفة زمنية لا حدث تجرد؛ فصلت المتجانس عن fullness السابق."),
    475: R("كه", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كه`: إخراج من الجوف بدفع؛ لا يسمي that أو relative conjunction.", "الربط النحوي لا يستخرج من حكاية الصوت العربية؛ بقيت الأداة خارج المدار."),
    476: R("كه", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كه`: إخراج من الجوف بدفع؛ لا يسمي small.", "خروج مقدار قليل لا يساوي صفة الصغر، وفصلت الصفة عن أداة الربط السابقة."),
    477: R("كه", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كه`: إخراج من الجوف بدفع؛ لا يسمي commoner أو insignificant person.", "الخسة الاجتماعية حكم على الشخص لا حدث إخراج؛ لم أورث الاسم صفة small السابقة."),
    480: R("ند", "TOOL-GAP", "جسر المعنى: ninety حاضر، لكن /navad/ يحمل /w/ منطوقة أسقطها الهيكل.", "أوقفت المقارنة قبل تحويل العدد إلى نون ودال؛ لا يعوض الصامت المنطوق من الأصل التاريخي."),
    481: R("بنج", "TOOL-GAP", "جسر المعنى: fifty حاضر، لكن /panjâh/ يحمل /h/ نهائية منطوقة أسقطها الهيكل.", "لم أحول العدد إلى مادة `بنج` بعد سقوط الهاء؛ توقف العضو قبل الحكم."),
    482: R("جهل", "LAW-GAP", "نص الحدث المجمد لـ`جهل`: خلو الباطن من العلم؛ لا يسمي forty، وچ↔ج غير مسمى.", "القيمة العددية لا تتولد من الجهل أو الخفة، وفوقه بقي صف الصوت الأول بلا قانون."),
    483: R("دست", "TOOL-GAP", "جسر المعنى: two hundred حاضر، لكن /devist/ يحمل /v/ منطوقة أسقطها الهيكل.", "لم أعوض الواو من معرفة العدد أو أصله؛ توقف العضو قبل انتخاب مادة عربية."),
    485: R("رنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رنج`: مادة تغطي الحس وتمنع النفاذ؛ لا يسمي colorful أو coloured.", "تغطية السطح باللون فعل ممكن، لكنه لا يميز اللون من الطلاء أو الحجاب؛ وشواهد العربية في جوز الهند."),
    486: R("سرد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سرد`: خرز متوال مع شد؛ لا يسمي cold أو lukewarm.", "تتابع البرد أو شدته سياق خارجي لا معنى انخفاض الحرارة؛ الشواهد في الخرز والتوالي."),
    487: R("خرد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خرد`: بقاء على الفطرة دون استعمال؛ لا يسمي wisdom أو intellect.", "صفاء العقل أو سلامة فطرته تأويلان عامان لا معنى الحكمة؛ الشواهد في العذراء واللؤلؤة غير المثقوبة."),
    488: R("زندن", "COMPOUND-BOUNDARY", "جسر المعنى: prison يرد احتمالا إلى weapon وholder في طبقة تاريخية غير جازمة، لا From نهائيا مؤهلا.", "وقفت صيغة Perhaps originally عند حدها؛ لم أورث السجن معنى السلاح أو الوعاء."),
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
            raise AssertionError(f"تغير عداد نسخة v11 في {name}")
        if len(data.get("both") or []) != expected_both or len(data.get("sound_only") or []) != expected_sound:
            raise AssertionError(f"تغير طول قوائم نسخة v11 في {name}")


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
            if row.rank > 413 and len(fresh) < 70:
                internal_skips.append(row.rank)
            continue
        seen.add(key)
        if row.rank <= 413:
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
        "فرود": {8155, 8156}, "ـگاه": {7461}, "پر": {316, 317},
        "ـش": {10301, 10302}, "پاییز": {1967},
        "ـی": {6327, 6328, 6329, 6330}, "ی": {406},
    }
    fan_counts = {"فرود": 12, "ـگاه": 72, "پر": 40, "ـش": 0, "پاییز": 60, "ـی": 0, "ی": 0}
    for word, expected in expected_indices.items():
        actual = {index for index, _entry in grouped.get(word, [])}
        if actual != expected:
            raise AssertionError(f"تغير جرد مكون {word}: {sorted(actual)}")
        fan = tuple(H.FAN.rank(word, H.FAN.fan(word, "persian"), "persian"))
        if len(fan) != fan_counts[word]:
            raise AssertionError(f"تغيرت مروحة المكون {word}: {len(fan)}")
    expected_raw = {
        "فرود": {9547, 9548}, "ـگاه": {8752}, "پر": {334, 335, 336},
        "ـش": {12673, 12674}, "پاییز": {2070},
        "ـی": {7420, 7421, 7422, 7423, 7424}, "ی": {437},
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
    if review.verdict == "ROOT-TRACE":
        return "اكتملت أرجل الصوت والحدث والمدار اليدوي، ومعها شاهدان عربيان كلاسيكيان مستقلان."
    if review.verdict == "ROOT-ECHO":
        return "اكتمل الصوت والشاهدان، لكن الحدث المجمد ألين من التطابق المعجمي؛ أغلق على درجة الصدى."
    if review.verdict == "SEMITIC-SOURCE-TRANSMISSION":
        return "سمى خبر الأصل مانحا ساميا مباشرا؛ أغلق نقل سامي نتيجة إيجابية محسوبة."
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
    card = card.replace("الجولة 29،", "الجولة 31،")
    if item.row.rank in REJECTED_ANALYSES and "حد التحليل غير المؤهل" not in card:
        card = card.replace(
            "- عطب الهيكل:",
            f"- حد التحليل غير المؤهل: {REJECTED_ANALYSES[item.row.rank]}\n- عطب الهيكل:",
            1,
        )
    if item.row.rank == 418:
        card = card.replace(
            "- المصفاة: الأصل حاشية؛ لا يغلق النقل إلا بمانح سامي مسمى أو تصريح بالتعريب أو باتجاه الدخول إلى العربية.",
            "- المصفاة: خبر الأصل يسمّي السريانية الكلاسيكية `mastā` مانحا مباشرا؛ يعمل SEMITIC-SOURCE-TRANSMISSION نتيجة إيجابية محسوبة.",
        )
    return card


def validate_decisions(selected, raw_entries, decisions, ranked_by_rank, sense_map) -> None:
    if set(REVIEWS) != set(SOUND_RANKS):
        raise AssertionError("جدول المدار اليدوي لا يغطي الرتب السبعين")
    parsed = {item.row.rank for item in selected if P25.direct_from_plus(raw_entries[item.row.rank]["etymology"])}
    if parsed != EXACT_DECOMPOSITIONS:
        raise AssertionError(f"تغيرت أسطر From X + Y المباشرة: {sorted(parsed)}")
    expected_verdicts = {
        "COMPOUND-BOUNDARY": 5,
        "LAW-GAP": 6,
        "OPEN-CANDIDATE": 50,
        "ROOT-ECHO": 1,
        "ROOT-TRACE": 1,
        "SEMITIC-SOURCE-TRANSMISSION": 1,
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
        if decision.verdict == "LAW-GAP" and complete:
            raise AssertionError(f"LAW-GAP بلا صف مفقود في الرتبة {row.rank}")
        if decision.verdict in {"OPEN-CANDIDATE", "ROOT-ECHO", "ROOT-TRACE", "SEMITIC-SOURCE-TRANSMISSION"} and not complete:
            raise AssertionError(f"حكم بمسار ناقص في الرتبة {row.rank}")
        if decision.verdict in {"ROOT-ECHO", "ROOT-TRACE"}:
            _matches, classical, _witnesses = P.classical_witnesses(decision.candidate, sense_map, 90)
            if classical < 2:
                raise AssertionError(f"حكم موجب بلا شاهدين في الرتبة {row.rank}")
        if row.rank in EXACT_DECOMPOSITIONS and decision.verdict not in {"COMPOUND-BOUNDARY", "TOOL-GAP"}:
            raise AssertionError(f"تفكيك مباشر بلا حد أو عطب أداة في الرتبة {row.rank}")
        if row.rank in TOOL_GAPS and decision.verdict != "TOOL-GAP":
            raise AssertionError(f"هيكل ناقص بلا TOOL-GAP في الرتبة {row.rank}")
        if not REVIEWS[row.rank].meaning_path.startswith(("جسر المعنى:", "نص الحدث المجمد")):
            raise AssertionError(f"طريق المعنى غير مسمى في الرتبة {row.rank}")
    if "Classical Syriac" not in raw_entries[418]["etymology"]:
        raise AssertionError("غاب المانح السرياني المسمى من الرتبة 418")


def validate_text(selected, texts, prior_pairs) -> None:
    if len(selected) != 70 or BATCH_SIZES != (35, 35):
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = re.findall(r"^### (WO-B-R31-SOUND-\d{5}):", joined, re.MULTILINE)
    if headings != [item.heading for item in selected]:
        raise AssertionError("معرفات الجولة 31 لا تطابق النافذة")
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
    if "السريانية الكلاسيكية `mastā` مانحا مباشرا" not in texts[SOUND_RANKS.index(418)]:
        raise AssertionError("لم يسم الإغلاق السرياني في البطاقة")


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
            f"## الجولة الحادية والثلاثون، دفعة sound_only رقم {number}", "",
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
    lines.extend([
        "## حصيلة الجولة الحادية والثلاثين", "",
        f"- حمل `persian.md` مرة واحدة؛ أزواج WO-B المقروءة={stats['pair_count']}؛ المتجاوز داخل النافذة={', '.join(map(str, stats['skipped']))}.",
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- نطاق الصوت الجديد: الرتب 414-488 بعد WO-B-R30-SOUND-00413، مع تجاوز الأزواج الخمسة المقروءة فقط.",
        "- الأثر الجذري المحكم: WO-B-R31-SOUND-00431؛ الصدى الجذري: WO-B-R31-SOUND-00464.",
        "- النقل السامي المسمى: WO-B-R31-SOUND-00418 من السريانية الكلاسيكية؛ نتيجة إيجابية محسوبة.",
        "- التطابق النباتي WO-B-R31-SOUND-00470 بقي LAW-GAP لأن صف گ↔ق غير مسمى؛ لم يلتف على القانون.",
        "- التفكيك المباشر المؤهل: S00427، S00449، S00466، S00472؛ قرئت المكونات استقلالا.",
        "- الحدود غير المباشرة: S00455، S00456، S00465، S00488؛ لم يحول التاريخ أو الاحتمال إلى From نهائي.",
        "- فجوات الأداة: S00456، S00465، S00466، S00480، S00481، S00483؛ لم تعوض الصوامت المنطوقة الساقطة.",
        "- فجوات القانون: S00430، S00451، S00454، S00457، S00470، S00482.",
        "- أحواض `nucleus-sweep-*.json` التسعة الحالية v11 قرئت كاملة من القرص، وثبت الحجم وSHA-256 والعدادات لكل ملف قبل الانتخاب.",
        f"- أكبر بطاقة: {max_size} بايت، {max_item.heading}؛ كل البطاقات دون 5KB.",
        "- لم تفعل طبقة البرهان، ولم يبن ملف مشترك، ولم يقع ship، ولم يستعمل git.",
        "", f"<!-- {MARKER}:END -->", "", DONE_LINE,
    ])
    return "\n".join(lines)


def validate_existing(reading_text: str, report_text: str) -> None:
    match = re.search(rf"<!-- {re.escape(MARKER)}:START -->(.*?)<!-- {re.escape(MARKER)}:END -->", reading_text, re.DOTALL)
    if not match:
        raise AssertionError("محضر الجولة موجود وبطاقاتها غائبة")
    headings = re.findall(r"^### (WO-B-R31-SOUND-\d{5}):", match.group(1), re.MULTILINE)
    expected = [f"WO-B-R31-SOUND-{rank:05d}" for rank in SOUND_RANKS]
    if headings != expected:
        raise AssertionError("مقطع الجولة 31 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(DONE_LINE):
        raise AssertionError("سطر DONE31 ليس خاتمة التقرير")


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
        print("ROUND31 ALREADY PRESENT AND VALID")
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
    R28.OUT_OF_SCOPE = {}
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
        "## الجولة الحادية والثلاثون: متابعة حوض sound_only (2026-08-26)\n\n"
        "- النطاق: 70 عضوا طازجا بعد WO-B-R30-SOUND-00413؛ من الرتبة 414 إلى 488 مع تجاوز 441 و474 و478 و479 و484 لأنها مقروءة؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ طريق المعنى مسمى، والمدار اليدوي حاسم، والأصداء مفصولة عن الآثار المحكمة.\n"
        "- لقطة الأحواض: قرئت ملفات nucleus-sweep-*.json التسعة الحالية v11 من القرص وثبتت بصماتها وعداداتها قبل الانتخاب.\n\n"
        + "\n".join(texts[:35])
        + "\n## الدفعة الثانية: متابعة sound_only بعد الرتبة 449\n\n"
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
    print("ROUND31 READY")
    print("NUCLEUS_V11_FILES", len(NUCLEUS_SNAPSHOT), "SHA256_AND_COUNTS_OK")
    print("SKIPPED", ",".join(map(str, stats["skipped"])))
    print("BATCHES", *BATCH_SIZES, "SELECTED", len(selected))
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("EXACT_FROM_PLUS", " ".join(f"S{rank:05d}" for rank in sorted(EXACT_DECOMPOSITIONS)))
    print("TRACES", "S00431", "ECHOES", "S00464", "TRANSMISSIONS", "S00418")
    print("BLOCKED_BOUNDARIES", len(BLOCKED_BOUNDARIES) + len(REJECTED_ANALYSES), "TOOL_GAPS", len(TOOL_GAPS))
    print("MAX_CARD", max(sizes), selected[sizes.index(max(sizes))].heading)
    if args.preview:
        print("PREVIEW ONLY")
        print(DONE_LINE)
        return 0

    with READING.open("a", encoding="utf-8", newline="") as handle:
        handle.write(reading_append)
    with REPORT.open("a", encoding="utf-8", newline="") as handle:
        handle.write(report_append)
    print("ROUND31 WRITTEN")
    print(DONE_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
