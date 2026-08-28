# -*- coding: utf-8 -*-
"""المسار B، الجولة 41: متابعة إنقاذ حوض sound_only في دفعتين من 35 بطاقة."""

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

import harvest_persian_round40 as R40  # noqa: E402

R39 = R40.R39
R38 = R40.R38
R36 = R40.R36
R35 = R40.R35
R34 = R40.R34
R32 = R40.R32
R31 = R40.R31
R29 = R40.R29
R28 = R40.R28
H = R40.H
P = R40.P
P25 = R40.P25
READING = R40.READING
REPORT = R40.REPORT
SWEEP = R40.SWEEP
LEXICON = R40.LEXICON
RAW_LEXICON = R40.RAW_LEXICON
NUCLEUS_DIR = ROOT / "04-cross-linguistic" / "exploration"
MARKER = "LANE-B-PERSIAN-ROUND41-2026-08-27"
CARD_LIMIT = 5120

SOUND_RANKS = (
    1183, 1184, 1185, 1186, 1187, 1188, 1189, 1190, 1191, 1192,
    1193, 1194, 1195, 1196, 1198, 1199, 1201, 1202, 1203, 1204,
    1205, 1207, 1208, 1209, 1210, 1211, 1212, 1213, 1214, 1215,
    1216, 1217, 1218, 1219, 1221, 1222, 1223, 1224, 1225, 1226,
    1227, 1228, 1230, 1231, 1232, 1233, 1234, 1236, 1237, 1238,
    1239, 1240, 1241, 1243, 1244, 1245, 1246, 1247, 1250, 1251,
    1252, 1254, 1255, 1256, 1257, 1258, 1259, 1260, 1261, 1263,
)
BATCH_SIZES = (35, 35)
DONE_LINE = "LANE-B DONE41 70 WO-B-R41-SOUND-01263"
EXPECTED_SKIPS = (1197, 1200, 1206, 1220, 1229, 1235, 1242, 1248, 1249, 1253, 1262)

# النسخة التاسعة عشرة المقروءة من القرص بعد تبدل الأحواض الذي تلا الجولة 40.
NUCLEUS_SNAPSHOT = {
    "nucleus-sweep-ancient_greek.json": (7972376, "ad2de3c7493ae54fbd33b5a711a719f6ebfb8c9dacdc5471f33962544d0493c8", 2313, 16781),
    "nucleus-sweep-english_middle.json": (3415893, "b10f11707b8b5eda41691d8c6aea13c6e3b880ac61dfc6035ba8071524eec467", 1414, 7991),
    "nucleus-sweep-english_old.json": (1293699, "0e4ac0e76706c510b7a8c814d6168c360a6ca73487dbe0d87c453d0163d1851b", 474, 3413),
    "nucleus-sweep-gothic.json": (1416304, "9445c83f4c3aa1ddc71d7f485750760647d673f6d32994ab132ed95540290c39", 335, 3083),
    "nucleus-sweep-latin.json": (18829628, "12c85584226aa4dd6693a08f776df8d412ba40433ac6125158d969a06a49e892", 6583, 39470),
    "nucleus-sweep-old_irish.json": (954285, "7d157718c682528abb6d436aac259eaa4881a1df358914ab51d4471142601ac6", 278, 2740),
    "nucleus-sweep-old_norse.json": (1380615, "ad6e6b28730566fc3b4457e9e3c1e799c90c14ed4f4952ab47df9cf635830352", 476, 3750),
    "nucleus-sweep-persian.json": (5483805, "fb44ce0b92745835bc0a386f639ac562aa59478a4cf9990b57f362339057466e", 1437, 13503),
    "nucleus-sweep-welsh.json": (5776833, "5116d5ea5a195c03db7d1e50a8033591dede1c1569238ee57fb0e5cda39f6bce", 1187, 16086),
}

EXPECTED_ENTRY_INDEX = dict(zip(SOUND_RANKS, (
    6298, 6300, 6301, 6322, 6323, 6335, 6336, 6342, 6356, 6361,
    6372, 6376, 6377, 6379, 6397, 6404, 6409, 6414, 6420, 6421,
    6430, 6434, 6443, 6445, 6455, 6456, 6458, 6461, 6466, 6469,
    6471, 6472, 6473, 6475, 6481, 6483, 6484, 6485, 6486, 6487,
    6491, 6496, 6516, 6517, 6518, 6525, 6529, 6553, 6561, 6565,
    6568, 6570, 6571, 6583, 6600, 6602, 6604, 6605, 6636, 6640,
    6651, 6665, 6676, 6677, 6678, 6679, 6680, 6700, 6701, 6707,
)))
EXPECTED_RAW_LINE = dict(zip(SOUND_RANKS, (
    7387, 7389, 7390, 7414, 7415, 7429, 7430, 7436, 7452, 7459,
    7471, 7477, 7481, 7485, 7504, 7511, 7516, 7521, 7528, 7529,
    7538, 7542, 7552, 7554, 7566, 7567, 7569, 7572, 7577, 7580,
    7582, 7583, 7584, 7586, 7592, 7595, 7596, 7597, 7598, 7599,
    7603, 7608, 7630, 7631, 7632, 7642, 7647, 7684, 7699, 7704,
    7707, 7712, 7713, 7728, 7747, 7749, 7751, 7752, 7789, 7793,
    7807, 7821, 7832, 7833, 7834, 7835, 7837, 7861, 7862, 7868,
)))

PARSER_FROM_PLUS = {1186, 1187, 1188, 1204, 1216, 1221, 1232, 1244}
EXACT_DECOMPOSITIONS = PARSER_FROM_PLUS | {1225}
EXPECTED_COMPONENTS = {
    1186: ("معاف", "ـی"),
    1187: ("گرد", "ـش"),
    1188: ("پیش", "ـوند"),
    1204: ("هشت", "ده"),
    1216: ("سپاه", "ـی"),
    1221: ("کار", "آگاه"),
    1225: ("خار", "نارگیل"),
    1232: ("کیمیا", "ـگر"),
    1244: ("باد", "گیر"),
}
COMPONENT_READINGS = {
    1186: "`معاف`: entry[13670] والخام 16519 لمعنى exempt، وخبره يصرح بالقرض من العربية، ومروحته 6: SEMITIC-SOURCE-TRANSMISSION للمكون وحده. `ـی`: اختيرت entry[6330] والخام 7422 للاسم المجرد، ومروحتها صفر: MORPHOLOGY-GAP.",
    1187: "`گرد`: صورة الجذع الحاضر من turn غائبة بهذه الوظيفة من branch-lexicons وحاضرة في الخام 7294، ومروحتها 24: FORM-LINK. `ـش`: entry[10303] والخام 12674 لاحقة اسم الحدث، ومروحتها صفر: MORPHOLOGY-GAP.",
    1188: "`پیش`: قُرئت entries[4609-4611] والخام 5126-5128 لمعاني before وfront، ومروحتها 60: OPEN-CANDIDATE. `ـوند`: entry[14786] والخام 17709 لاحقة نسبة أو تعلق، ومروحتها 6: MORPHOLOGY-GAP.",
    1204: "`هشت`: entry[3342] والخام 3718 للعدد eight، ومروحتها 18: OPEN-CANDIDATE. `ده`: اختيرت entry[1045] والخام 1110 للعدد ten، ومروحتها 60: OPEN-CANDIDATE.",
    1216: "`سپاه`: entry[5675] والخام 6672 لمعنى army، ومروحتها 60: OPEN-CANDIDATE. `ـی`: اختيرت entry[6329] والخام 7421 لاحقة النسبة القابلة للاسمية، ومروحتها صفر: MORPHOLOGY-GAP.",
    1221: "`کار`: entry[797] والخام 847 لمعنى work أو affairs، ومروحتها 40: OPEN-CANDIDATE. `آگاه`: entry[10763] والخام 13254 لمعنى aware أو knowing، ومروحتها 80: OPEN-CANDIDATE.",
    1225: "`خار`: entry[2954] والخام 3246 لمعنى thorn، ومروحتها 60: OPEN-CANDIDATE. `نارگیل`: entry[1264] والخام 1339 لمعنى coconut، ومروحتها 16: OPEN-CANDIDATE.",
    1232: "`کیمیا`: اختيرت entry[7145] والخام 8392 لمعنى alchemy، وخبرها يسمي القرض من العربية، ومروحتها 20: SEMITIC-SOURCE-TRANSMISSION للمكون. `ـگر`: entry[10504] والخام 12956 لاحقة اسم الفاعل، ومروحتها 80: MORPHOLOGY-GAP.",
    1244: "`باد`: اختيرت entry[829] والخام 884 لمعنى wind، ومروحتها 30: OPEN-CANDIDATE. `گیر`: entry[5696] والخام 6695 لمعنى catch أو grasp، ومروحتها 80: OPEN-CANDIDATE.",
}

TOOL_GAPS = {
    1188: "الصورة `پیشوند` منقوطة /pēšwand/، لكن الهيكل أسقط /w/ المنطوقة.",
    1190: "الصورة `ویران` منقوطة /wayrān/، لكن الهيكل أسقط /y/ المنطوقة.",
    1203: "الصورة `نوزده` منقوطة /nuzdah/، لكن الهيكل أسقط الهاء النهائية المنطوقة.",
    1204: "الصورة `هجده` منقوطة /hejdah/، لكن الهيكل أسقط الهاء النهائية المنطوقة.",
    1215: "الصورة `خسرو` منقوطة /xusraw/، لكن الهيكل أسقط /w/ النهائية المنطوقة.",
    1219: "الصورة `آیینه` منقوطة /āyīna/، لكن الهيكل أسقط /y/ المنطوقة.",
    1221: "الصورة `کارآگاه` منقوطة /kār-āgāh/، لكن الهيكل أسقط الهاء النهائية المنطوقة.",
    1231: "الصورة `شاهنشاه` منقوطة /šāhanšāh/، لكن الهيكل أسقط الهاء النهائية المنطوقة.",
    1232: "الصورة `کیمیاگر` منقوطة /kimiyāgar/، لكن الهيكل أسقط /y/ المنطوقة.",
    1247: "الصورة `چوگان` منقوطة /čawgān/، لكن الهيكل أسقط /w/ المنطوقة.",
    1252: "الصورة `پیوست` منقوطة /peyvast/، لكن الهيكل أسقط /y/ و/v/ المنطوقتين.",
    1254: "الصورة `پیوستن` منقوطة /peyvastan/، لكن الهيكل أسقط /y/ و/v/ المنطوقتين.",
    1260: "الصورة `آونگ` منقوطة /āvang/، لكن الهيكل أسقط /v/ المنطوقة.",
}
LAW_GAPS = {1191, 1208, 1218, 1223, 1230, 1234, 1238, 1246, 1255, 1256, 1257, 1258, 1261}
OUT_OF_SCOPE = {
    1189: "اسم إقليم Khwarazm بعينه؛ لا معنى معجميا عاما في المدخلة.",
    1201: "اسم البطل رستم بعينه؛ لا معنى معجميا عاما في المدخلة.",
    1214: "اسم قلعة وإقليم Alamut بعينه؛ لا معنى معجميا عاما في المدخلة.",
    1236: "اختصار كتابي لـpostscript لا مدخلة لفظية معجمية عامة قابلة للحكم الجذري.",
}
REJECTED_ANALYSES = {
    1198: "يعرض الخبر احتمالا بديلا من أداة النفي وصيغة من جذر هندو أوروبي للأكل؛ لم يؤهل الاحتمال تفكيكا نهائيا.",
    1201: "التأثيل الشعبي من `رستم` بمعنى I escaped لاحق للاسم التاريخي المركب؛ لم يستعمل تفكيكا حديثا.",
    1202: "التحليل إلى `بیرون` و`ـی` موسوم By surface analysis بعد الصورة الوسطى الموروثة؛ لم يؤهل تفكيكا نهائيا.",
    1205: "التحليل إلى `ترس` و`ـا` موسوم By surface analysis بعد الصورة الوسطى؛ لم يؤهل تفكيكا نهائيا.",
    1233: "تفكيك الصورة الفارسية الوسطى إلى sard وīh تاريخي، لا From نهائيا مباشرا للمدخلة الحديثة.",
    1245: "التركيب من `کاه` و`ریز` احتمال بديل بعد صورة أقدم؛ لم يحول إلى تفكيك نهائي.",
    1254: "تفكيك Proto-Iranian إلى *pati و*bándati تاريخي؛ لم ينزع صامتين من الصورة الحديثة.",
}
SOURCE_NOTES = {
    1184: "يسمي الخبر السريانية والأرمنية آخذتين إيرانيتين؛ لا يسمي العربية طرفا في النقل.",
    1186: "القرض العربي ثابت للمكون `معاف` وحده؛ لم تورث الصورة المشتقة حكم المكون.",
    1189: "حفظ تسلسل اسم الإقليم من الفارسية القديمة وعزل عن الحكم العام.",
    1192: "ذكر السريانية في خبر حس jackal لا يثبت معنى brave ولا اتجاهًا عربيًا.",
    1201: "حفظ تركيب الاسم التاريخي وعزل التأثيل الشعبي؛ المدخلة علم بطل.",
    1214: "التفكيك المذكور لاسم القلعة لا يحول العلم إلى معنى جذري عام.",
    1225: "قبل وسم Blend of الصريح حد مكونات، لا دليلا على إرث أو تماس عربي.",
    1232: "القرض العربي ثابت للمكون `کیمیا` وحده؛ لم تورث منه صورة alchemist المشتقة.",
    1236: "حقل الأصل يحيل إلى الكلمة الكاملة `پینوشت`، لكن عضو الحوض اختصار كتابي من حرفين.",
    1263: "خبر الأصل يثبت الصورة الفارسية الوسطى ولا يسمي العربية طرفا؛ الأثر الاستكشافي مستقل عن دعوى النقل.",
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
        return f"WO-B-R41-SOUND-{self.row.rank:05d}"


Review = R40.Review
R = R40.R

# سجل قراءة يدوي. لا يشتق الحكم من best ولا من وزن المروحة.
REVIEWS = {
    1183: R("بنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بنج`: الامتداد والبناء مع حدث الجيم؛ لا يسمي voice أو sound.", "خبر الصوت هندو أوروبي مستقل؛ وشواهد المرشح لا تقدم النداء أو الأذان."),
    1184: R("جرز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جرز`: تجرد الأرض ليبس باطنها؛ لا يسمي boar.", "حفظت شبكة القروض الإيرانية المسماة، ولم أحول يبوسة الأرض إلى اسم الخنزير البري."),
    1185: R("كرس", "ROOT-ECHO", "جسر المعنى: braid ضم خصل متراكبة، وشاهد `كرس` يسمي أكراس القلائد إذا ضم بعضها إلى بعض.", "مدار لين: التراكم المتلازب وضم أكراس القلائد يلامسان بنية الضفيرة، لكن الشاهد لا يسمي الشعر أو الحلقة نفسها."),
    1186: R("مغف", "COMPOUND-BOUNDARY", "جسر المعنى: exemption مصرح باشتقاقها من `معاف` exempt و`ـی` الاسم المجرد.", "قُرئ الأصل العربي واللاحقة؛ لم ترث الصورة المشتقة حكم القرض العربي للمكون."),
    1187: R("جردش", "COMPOUND-BOUNDARY", "جسر المعنى: turning مصرح باشتقاقها من `گرد` turn و`ـش` اسم الحدث.", "قُرئ الجذع واللاحقة؛ لم تقارن الصورة الرباعية المركبة بجذر واحد."),
    1188: R("بشند", "TOOL-GAP", "جسر المعنى: prefix مصرح بتكوينه من `پیش` و`ـوند`، لكن /w/ سقطت من الهيكل.", "قُرئ المكونان ثم أوقف الصامت الساقط حكم الصورة المجموعة."),
    1189: R("حرزم", "OUT-OF-SCOPE", "جسر المعنى: Khwarazm اسم إقليم بعينه لا معنى معجميا عاما.", "حفظت سلسلة الاسم التاريخية في التغطية وعزلته من الحكم الجذري."),
    1190: R("ورن", "TOOL-GAP", "جسر المعنى: ruined أو desolate حاضر، لكن /wayrān/ يحمل /y/ أسقطها الهيكل.", "أوقف عطب /y/ المقارنة؛ لم يعوضه خبر الصورة الوسطى أو المقارنة الأرمنية."),
    1191: R("كج", "LAW-GAP", "نص الحدث المجمد لـ`كج`: محاكم الحرفين لا تسمي alley، وچ↔ج غير مسمى.", "حقل الأصل فارغ؛ لم يحول ضيق الممر إلى معنى ولا يخترع صفا للصامت."),
    1192: R("تور", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تور`: الدور والرجوع بخفة؛ لا يسمي brave أو crazy.", "فصلت حسي الشجاعة والجنون عن الأناء والرسول العربيين وعن خبر jackal."),
    1193: R("نهز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`نهز`: فراغ يتخلل الشيء؛ لا يسمي he-goat.", "امتداد القرون والأرجل هيئة للحيوان لا معنى المادة، والخبر الإيراني مستقل."),
    1194: R("كب", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`كب`: التجمع كتلة متضاغطة؛ لا يسمي cow.", "كتلة جسم البقرة وصف عام للأجسام؛ حقل الأصل فارغ ولا شاهد عربي للحيوان."),
    1195: R("نجر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`نجر`: النفاذ بغلظ أو قوة؛ لا يسمي painting أو beloved.", "نحت النجار قد ينتج صورة لكنه فعل صناعة لا معنى اللوحة أو المحبوب."),
    1196: R("رزم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رزم`: التداخل الشديد؛ لا يسمي war أو battle مباشرة.", "اشتباك الحرب مثال ممكن للتداخل، لكن الشاهدين في الثبات والصوت وحزم الثياب لا القتال."),
    1198: R("نشط", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`نشط`: الخلوص مما يمسك الشيء؛ لا يسمي hungry.", "الجوع خلو المعدة وصف حالة لا معنى الخلوص، والتأثيل البديل غير حاسم."),
    1199: R("سبهل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سبهل`: الامتداد الدقيق مع الاتصال؛ لا يسمي sky أو heaven.", "امتداد السماء وصف مكاني عام، والخبر الإيراني لا يسمي العربية."),
    1201: R("رستم", "OUT-OF-SCOPE", "جسر المعنى: Rostam اسم بطل بعينه، لا معنى معجميا عاما.", "حفظت تركيب الاسم التاريخي والتأثيل الشعبي في الحاشية وعزلت العلم."),
    1202: R("برن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`برن`: التجرد والخلوص مع حدث النون؛ لا يسمي outer أو external.", "كون الخارج منكشفا وصف محتمل لا معنى معجميا؛ ورفضت التحليل السطحي."),
    1203: R("نذذ", "TOOL-GAP", "جسر المعنى: nineteen مثبت، لكن /nuzdah/ فقدت هاءها النهائية في الهيكل.", "لم يقارن العدد بهيكل ناقص ولم يعوض الصامت من الصورة الوسطى."),
    1204: R("هجد", "TOOL-GAP", "جسر المعنى: eighteen مفككة إلى `هشت` و`ده`، لكن /hejdah/ فقدت هاءها النهائية.", "قُرئ العددان ثم أوقف عطب الهاء حكم الصورة الحديثة."),
    1205: R("ترس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ترس`: الابتعاد بقوة مع دقة؛ لا يسمي Christian.", "حفظت دلالة God-fearer داخل الخبر ورفضت التحليل السطحي؛ الشاهد العربي لا يسمي النصرانية."),
    1207: R("بر", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`بر`: التجرد والخلوص؛ لا تسمي horse.", "حقل الأصل يثبت صورة فارسية وسطى، وشواهد المرشح لا تقدم الفرس."),
    1208: R("جرم", "LAW-GAP", "نص الحدث المجمد لـ`جرم`: التجريد بعد التمام؛ لا يسمي white horse، وچ↔ج غير مسمى.", "المقارنات تسمي قروضا إيرانية في ألسن أخرى؛ لم تصلح فجوة القانون أو تثبت العربية."),
    1209: R("خنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خنج`: التخلخل الممتد في الباطن؛ لا يسمي dumb أو stupid.", "ضعف الفهم لا يساوي تخلخل جرم، وحقل الأصل فارغ."),
    1210: R("بسد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بسد`: الجفاف واليبوسة مع حدث الدال؛ لا يسمي back أو rear.", "الموضع الخلفي علاقة مكانية لا يبوسة، وفصلت الاسم عن حرف الجر التالي."),
    1211: R("بسد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بسد`: الجفاف واليبوسة مع حدث الدال؛ لا يسمي behind.", "فصلت وظيفة حرف الجر عن اسم rear السابق؛ لا شاهد عربي للموقع."),
    1212: R("بيا", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بيا`: محاكم الحروف بلا معنى sinew أو track.", "فصلت الوتر والأثر والأساس داخل المدخلة؛ لم يجمعها مرشح عربي واحد."),
    1213: R("وس", "OPEN-CANDIDATE", "نص محاكم الحرفين لـ`وس` لا يسمي clan.", "خبر household الهندو أوروبي مستقل، وشواهد العربية لا تقدم العشيرة."),
    1214: R("المت", "OUT-OF-SCOPE", "جسر المعنى: Alamut اسم قلعة وإقليم بعينه، لا معنى معجميا عاما.", "حفظت تفكيك الاسم المصرح وعزلته من الحكم الجذري العام."),
    1215: R("خسر", "TOOL-GAP", "جسر المعنى: king مثبت، لكن /xusraw/ يحمل /w/ نهائية أسقطها الهيكل.", "أوقف الصامت الساقط الصورة قبل ربط الملك بالخسران أو الشهرة التاريخية."),
    1216: R("سبه", "COMPOUND-BOUNDARY", "جسر المعنى: soldier مصرح باشتقاقها من `سپاه` army و`ـی` النسبة.", "قُرئ الجيش واللاحقة؛ لم تقارن صورة الجندي جذرا واحدا."),
    1217: R("خرم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خرم`: التخلخل والنقص؛ لا يسمي merry أو blooming.", "الانتعاش أو تفتح النبات لا يساوي الخرم العربي، والخبر الإيراني مستقل."),
    1218: R("جم", "LAW-GAP", "نص النواة المجمدة لـ`جم`: التجمع والكثرة؛ لا تسمي poem، وچ↔ج غير مسمى.", "اجتماع الأبيات بنية للنص لا معنى القصيدة، وفجوة القانون تمنع الحكم."),
    1219: R("ان", "TOOL-GAP", "جسر المعنى: mirror مثبت، لكن /āyīna/ يحمل /y/ أسقطها الهيكل.", "أوقف الصامت الساقط المقارنة؛ لم يحول النظر التاريخي إلى حكم من هيكل ناقص."),
    1221: R("كرج", "TOOL-GAP", "جسر المعنى: detective مفككة إلى `کار` و`آگاه`، لكن /h/ النهائية سقطت من الهيكل.", "قُرئ العمل والعلم ثم أوقف عطب الهاء حكم الصورة المجموعة."),
    1222: R("سب", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`سب`: الامتداد الدقيق مع الاتصال؛ لا تسمي cheek.", "موضع الخد على الوجه أو امتداده وصف تشريحي عام لا معنى العضو."),
    1223: R("بخص", "LAW-GAP", "نص الحدث المجمد لـ`بخص`: النقص والاستفراغ؛ لا يسمي fly أو mosquito، وچ↔ص غير مسمى.", "حقل الأصل فارغ؛ حركة الحشرة لا تسمي نوعها وفوقها فجوة القانون."),
    1224: R("بدم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بدم`: الفراغ الممتد وبروز الشيء فيه؛ لا يسمي pennyroyal.", "نمو النبات أو بروزه وصف عام، ولا شاهد عربي يسمي هذا العشب."),
    1225: R("خرجر", "COMPOUND-BOUNDARY", "جسر المعنى: durian موسومة Blend of من `خار` thorn و`نارگیل` coconut.", "قُرئ المكونان؛ لم يحول المزج المعجمي اسم الثمرة إلى جذر رباعي."),
    1226: R("منج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`منج`: القوة والثبات مع حدث الجيم؛ لا يسمي rust.", "ثبات الصدأ على المعدن صفة التصاق لا معنى المادة؛ حقل الأصل فارغ."),
    1227: R("بشنك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بشنك`: الانتشار الظاهر مع أحداث الباقي؛ لا يسمي sprinkle.", "انتشار القطرات نتيجة الرش لا معنى الاسم، ولم يستعمل المرشح الناقص صوتيا."),
    1228: R("خنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خنج`: التخلخل الممتد في الباطن؛ لا يسمي scratch.", "الشاهدان العربيان في علم قبيلة وموضع، لا فعل الخدش؛ بقي الحدث وحده غير كاف."),
    1230: R("سج", "LAW-GAP", "نص النواة المجمدة لـ`سج`: الاعتدال والرقة؛ لا تسمي why، وچ↔ج غير مسمى.", "وظيفة الاستفهام لا تستخرج من الحدث وفوقها فجوة الصامت."),
    1231: R("سهنس", "TOOL-GAP", "جسر المعنى: shahanshah يعني king of kings، لكن /šāhanšāh/ فقدت هاءها النهائية.", "حفظت الصيغة التاريخية ولم تقارن اللقب بهيكل ناقص."),
    1232: R("كمجر", "TOOL-GAP", "جسر المعنى: alchemist مفككة إلى `کیمیا` و`ـگر`، لكن /y/ سقطت من الهيكل.", "قُرئ المكون العربي واللاحقة ثم أوقف عطب /y/ حكم الصورة المشتقة."),
    1233: R("سرد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سرد`: خرز متوال مع شد؛ لا يسمي cold أو bitterness.", "توالي البرد أو شدته وصف للحالة لا معنى البرودة، والتفكيك الأوسط تاريخي."),
    1234: R("جش", "LAW-GAP", "نص محاكم الحرفين لـ`جش` لا يسمي eye، وچ↔ج غير مسمى.", "وظيفة العين في الجس أو الرؤية لا تخلق اسما عربيا؛ بقي القانون ناقصا."),
    1236: R("بن", "OUT-OF-SCOPE", "جسر المعنى: P.S. اختصار كتابي لا معنى لفظيا عاما في العضو.", "حفظت الإحالة إلى postscript الكامل وعزلت الرمز من الحكم الجذري."),
    1237: R("نم", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`نم`: انتشار لطيف من الباطن إلى الظاهر؛ لا تسمي half.", "نصف المقدار حكم عددي لا رطوبة أو انتشار، والخبر الإيراني مستقل."),
    1238: R("بحثن", "LAW-GAP", "جسر المعنى: save أو rescue خلوص، لكن ت↔ث غير مسمى ومسار الرباعي ناقص.", "خبر التحرير الإيراني واعد دلاليا، غير أن القانون والشاهد العربي الثاني لا يكتملان."),
    1239: R("بر", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`بر`: التجرد والخلوص؛ لا تسمي jump.", "مفارقة القافز موضعه نتيجة للحركة لا معنى التجرد، فاختير المسار الكامل وبقي المدار مفتوحا."),
    1240: R("بلج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بلج`: التمكن والحوز مع حدث الجيم؛ لا يسمي leaf.", "اتصال الورقة بالغصن أو احتواؤها العروق هيئة نباتية لا معنى الورقة."),
    1241: R("كستن", "OPEN-CANDIDATE", "جسر المعنى: decrease يوافق حدث النقص في `كستن`، لكن الشاهد العربي الكلاسيكي المستقل الثاني غائب.", "مدار الحدث مباشر، غير أن المورد لا يقدم إلا الكستنة النبات؛ بقي المرشح مفتوحا بلا رجل الشاهدين."),
    1243: R("كند", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كند`: حبس الشيء ما في باطنه؛ لا يسمي moat.", "الخندق يحبس أو يحد حيزا، لكن ذلك وظيفة بنائية لا معنى المادة العربية."),
    1244: R("بدكر", "COMPOUND-BOUNDARY", "جسر المعنى: windcatcher مصرح بتكوينه من `باد` wind و`گیر` catcher.", "قُرئ المكونان؛ لم تقارن أداة العمارة جذرا رباعيا واحدا."),
    1245: R("كرز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كرز`: التركز تكرارا أو بقاء؛ لا يسمي qanat.", "حركة ماء القناة أو دوامها وصف استعمال، والتحليل البديل للمركب غير حاسم."),
    1246: R("نذذ", "LAW-GAP", "نص الحدث المجمد لـ`نذذ`: خروج حاد من خلال شيء؛ لا يسمي near، وز↔ذ غير مسمى.", "القرب علاقة موضعية لا خروج، ولم يعوض الخبر الإيراني فجوة القانون."),
    1247: R("شجن", "TOOL-GAP", "جسر المعنى: polo-stick مثبت، لكن /čawgān/ يحمل /w/ أسقطها الهيكل.", "أوقف الصامت الساقط الصورة قبل معالجة صف چ أو ربط العصا بالشجن."),
    1250: R("زهر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زهر`: البياض والإشراق؛ لا يسمي gallbladder أو gall.", "اتحاد الرسم لا ينقل معنى الصفراء، والخبر الهندو أوروبي مستقل."),
    1251: R("برجل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`برجل`: التجرد والخلوص مع أحداث الباقي؛ لا يسمي pair of compasses.", "رسم الدائرة أو فتح ساقي الأداة فعل استعمال لا معنى الأداة نفسها."),
    1252: R("بست", "TOOL-GAP", "جسر المعنى: attachment أو annexation حاضر، لكن /peyvast/ فقدت /y/ و/v/.", "أوقف الصامتان الساقطان المقارنة قبل ربط الوصل بالبسط أو البست."),
    1254: R("بستن", "TOOL-GAP", "جسر المعنى: to join مثبت، لكن /peyvastan/ فقدت /y/ و/v/ من الهيكل.", "رفضت التفكيك الإيراني التاريخي وأوقفت الصورة الحديثة عند الصامتين."),
    1255: R("هج", "LAW-GAP", "نص النواة المجمدة لـ`هج`: الغور مع حدة؛ لا تسمي tiny أو no، وچ↔ج غير مسمى.", "فصلت الصفة عن بقية متجانسات `هیچ`؛ بقي الصوت والمعنى ناقصين."),
    1256: R("هج", "LAW-GAP", "نص النواة المجمدة لـ`هج`: الغور مع حدة؛ لا تسمي never أو ever، وچ↔ج غير مسمى.", "فصلت الظرف عن الصفة؛ لا توارث حكم وفجوة القانون قائمة."),
    1257: R("هج", "LAW-GAP", "نص النواة المجمدة لـ`هج`: الغور مع حدة؛ لا تسمي nil أو naught، وچ↔ج غير مسمى.", "فصلت الاسم عن الظرف والصفة؛ الوظيفة الصفرية لا تصلح صف الصوت."),
    1258: R("هج", "LAW-GAP", "نص النواة المجمدة لـ`هج`: الغور مع حدة؛ لا تسمي nothing، وچ↔ج غير مسمى.", "فصلت الضمير عن المتجانسات الثلاثة؛ لم يصدر حكم عبر فجوة القانون."),
    1259: R("نشط", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`نشط`: الخلوص بالنزع؛ لا يسمي annihilated أو أداة النفي.", "العدم نهاية محتملة للنزع لا معناه؛ فصلت الوظيفة النحوية عن معنى المدخلة المصدرية."),
    1260: R("انق", "TOOL-GAP", "جسر المعنى: pendulum مثبت، لكن /āvang/ يحمل /v/ أسقطها الهيكل.", "أوقف عطب /v/ المقارنة قبل ربط التأرجح بالعنق أو الأنين."),
    1261: R("تقلق", "LAW-GAP", "نص الحدث المجمد لـ`تقلق`: الهوي إلى العمق مع أحداث الباقي؛ لا يسمي hail ومسار گ ناقص.", "سقوط البرد سلوك للظاهرة لا اسمها، ولا مرشح حي كامل الصوت."),
    1263: R("برز", "NUCLEUS-TRACE", "جسر المعنى: victorious أو triumphant يطابق فاق وسبق وتبرز على الأصحاب في شاهدي `برز`.", "مدار مباشر: الفوز تفوق وسبق، والحدث ظهور قوي؛ اكتمل المسار وشاهدا الفوق والسبق دون دعوى نقل."),
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
            raise AssertionError(f"تغير عداد نسخة v19 في {name}")
        if len(data.get("both") or []) != expected_both or len(data.get("sound_only") or []) != expected_sound:
            raise AssertionError(f"تغير طول قوائم نسخة v19 في {name}")
        total_both += expected_both
        total_sound += expected_sound
    if total_both != 14497 or total_sound != 106817:
        raise AssertionError("تغير مجموع أحواض v19")


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
            if row.rank > 1182 and len(fresh) < 70:
                internal_skips.append(row.rank)
            continue
        seen.add(key)
        if row.rank <= 1182:
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
        "معاف": {13670}, "ـی": {6328, 6329, 6330, 6331}, "گرد": {6217, 6218, 6219},
        "ـش": {10302, 10303}, "پیش": {4609, 4610, 4611}, "ـوند": {14786},
        "هشت": {3342}, "ده": {1045, 1046, 1047}, "سپاه": {5675}, "کار": {797},
        "آگاه": {10763}, "خار": {2954}, "نارگیل": {1264}, "کیمیا": {7145, 7146, 7147, 7148},
        "ـگر": {10504}, "باد": {829}, "گیر": {5696},
    }
    fan_counts = {
        "معاف": 6, "ـی": 0, "گرد": 24, "ـش": 0, "پیش": 60, "ـوند": 6,
        "هشت": 18, "ده": 60, "سپاه": 60, "کار": 40, "آگاه": 80, "خار": 60,
        "نارگیل": 16, "کیمیا": 20, "ـگر": 80, "باد": 30, "گیر": 80,
    }
    for word, expected in expected_indices.items():
        actual = {index for index, _entry in grouped.get(word, [])}
        if actual != expected:
            raise AssertionError(f"تغير جرد مكون {word}: {sorted(actual)}")
        fan = tuple(H.FAN.rank(word, H.FAN.fan(word, "persian"), "persian"))
        if len(fan) != fan_counts[word]:
            raise AssertionError(f"تغيرت مروحة المكون {word}: {len(fan)}")
    expected_raw = {
        "معاف": {16519}, "ـی": {7420, 7421, 7422, 7423, 7424}, "گرد": {7293, 7294, 7295, 7296},
        "ـش": {12673, 12674}, "پیش": {5126, 5127, 5128}, "ـوند": {17709},
        "هشت": {3718}, "ده": {1110, 1111, 1112, 1113}, "سپاه": {6672}, "کار": {847, 848},
        "آگاه": {13254}, "خار": {3246}, "نارگیل": {1339}, "کیمیا": {8392, 8393, 8394, 8395},
        "ـگر": {12956}, "باد": {884, 885}, "گیر": {6694, 6695},
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
    if review.verdict == "ROOT-ECHO":
        return "اكتمل الصوت وظهر تقارب حدثي، لكن المعنى المعجمي لم يتحد مباشرة؛ حفظ صدى لين لا أثر."
    if review.verdict == "COMPOUND-BOUNDARY":
        return "وقف الحكم عند حد المركب؛ لم تورث الصورة المجموعة حكم مكون ولم يخترع تفكيك."
    if review.verdict == "LAW-GAP":
        return "طريق المعنى مفحوص، لكن مسار الصوت يحوي صفا غير مسمى؛ لم يصدر حكم موجب."
    if review.verdict == "TOOL-GAP":
        return "صف الحوض أسقط صامتا منطوقا؛ توقف العضو قبل الحكم ولم يعوض الصامت يدويا."
    if review.verdict == "OUT-OF-SCOPE":
        return "العضو علم أو اختصار كتابي بلا معنى معجمي عام؛ حفظ في التغطية وعزل من الحكم الجذري."
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
        f"- تفكيك Kaikki الحصري المباشر أو المحكم من السطر الخام {raw['line']}: «{H.clip(raw['etymology'], 420)}».",
        f"- قراءة المكونات المستقلة: {COMPONENT_READINGS[rank]}",
        "- الخطوة صفر: قبل التفكيك النهائي المصرح به لم تقارن الصورة وحدة جذرية؛ قُرئ كل مكون مسمى وحده.",
    ]
    if rank in TOOL_GAPS:
        lines.extend([
            f"- عطب الهيكل: {TOOL_GAPS[rank]}",
            "- بعد قراءة المكونات أوقف TOOL-GAP حكم الصورة المجموعة؛ لا حكم من هيكل ناقص.",
        ])
    return lines


BASE_MAKE_CARD = R40.make_card


def make_card(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit) -> str:
    card = BASE_MAKE_CARD(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit)
    card = card.replace("الجولة 40،", "الجولة 41،")
    if item.row.rank == 1185:
        card = re.sub(
            r"^- المصفاة:.*$",
            "- المصفاة: شاهد أكراس القلائد وحدث التراكم يثبتان صدى بنيويا للضفيرة؛ بقي ROOT-ECHO لينا ولم يفعل طبقة البرهان.",
            card, count=1, flags=re.MULTILINE,
        )
    if item.row.rank == 1263:
        card = re.sub(
            r"^- المصفاة:.*$",
            "- المصفاة: الشاهدان يسميان الفوق والسبق والتبريز؛ يعمل NUCLEUS-TRACE استكشافيا مستقلا عن دعوى النقل.",
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
        "COMPOUND-BOUNDARY": 5,
        "LAW-GAP": 13,
        "NUCLEUS-TRACE": 1,
        "OPEN-CANDIDATE": 33,
        "OUT-OF-SCOPE": 4,
        "ROOT-ECHO": 1,
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
        if decision.verdict in {"OPEN-CANDIDATE", "NUCLEUS-TRACE", "ROOT-ECHO", "OUT-OF-SCOPE"} and not complete:
            raise AssertionError(f"حكم بمسار ناقص في الرتبة {row.rank}: {decision.verdict}")
        if decision.verdict in {"NUCLEUS-TRACE", "ROOT-ECHO"}:
            if coverage < 2 or H.event_line(decision.candidate).startswith("لا حدث"):
                raise AssertionError(f"نتيجة بلا حدث وشاهدين في الرتبة {row.rank}")
        if row.rank in EXACT_DECOMPOSITIONS and decision.verdict not in {"COMPOUND-BOUNDARY", "TOOL-GAP"}:
            raise AssertionError(f"تفكيك مؤهل بلا حد مركب أو عطب أداة في الرتبة {row.rank}")
        if row.rank in TOOL_GAPS and decision.verdict != "TOOL-GAP":
            raise AssertionError(f"هيكل ناقص بلا TOOL-GAP في الرتبة {row.rank}")
        if row.rank in LAW_GAPS and decision.verdict != "LAW-GAP":
            raise AssertionError(f"مسار ناقص بلا LAW-GAP في الرتبة {row.rank}")
        if row.rank in OUT_OF_SCOPE and decision.verdict != "OUT-OF-SCOPE":
            raise AssertionError(f"علم أو اختصار بلا OUT-OF-SCOPE في الرتبة {row.rank}")
        if not REVIEWS[row.rank].meaning_path.startswith(("جسر المعنى:", "نص الحدث المجمد", "نص النواة المجمدة", "نص محاكم")):
            raise AssertionError(f"طريق المعنى غير مسمى في الرتبة {row.rank}")
    if {rank for rank, review in REVIEWS.items() if review.verdict == "NUCLEUS-TRACE"} != {1263}:
        raise AssertionError("تغير موضع NUCLEUS-TRACE اليدوي")
    if {rank for rank, review in REVIEWS.items() if review.verdict == "ROOT-ECHO"} != {1185}:
        raise AssertionError("تغير موضع ROOT-ECHO اليدوي")


def validate_text(selected, texts, prior_pairs) -> None:
    if len(selected) != 70 or BATCH_SIZES != (35, 35):
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = re.findall(r"^### (WO-B-R41-SOUND-\d{5}):", joined, re.MULTILINE)
    if headings != [item.heading for item in selected]:
        raise AssertionError("معرفات الجولة 41 لا تطابق النافذة")
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
    if "NUCLEUS-TRACE استكشافيا" not in texts[SOUND_RANKS.index(1263)]:
        raise AssertionError("غاب إغلاق أثر پیروز")


def report_section(selected, decisions, sizes, stats) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    batches = (selected[:35], selected[35:])
    lines = [f"<!-- {MARKER}:START -->", ""]
    previous = 1182
    for number, batch in enumerate(batches, 1):
        lo = 0 if number == 1 else 35
        hi = lo + len(batch)
        counts = Counter(decision.verdict for decision in decisions[lo:hi])
        distribution = "؛ ".join(f"{key}={counts[key]}" for key in sorted(counts))
        batch_skips = [rank for rank in stats["skipped"] if previous < rank <= batch[-1].row.rank]
        skipped = ", ".join(map(str, batch_skips)) or "0"
        lines.extend([
            f"## الجولة الحادية والأربعون، دفعة sound_only رقم {number}", "",
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
    lines.extend([
        "## حصيلة الجولة الحادية والأربعين", "",
        f"- حمل `persian.md` مرة واحدة؛ أزواج WO-B المقروءة={stats['pair_count']}؛ المتجاوز داخل النافذة={', '.join(map(str, stats['skipped']))}.",
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- نطاق الصوت الجديد: الرتب 1183-1263 بعد WO-B-R40-SOUND-01182، مع تجاوز 1197 و1200 و1206 و1220 و1229 و1235 و1242 و1248 و1249 و1253 و1262 لأنها مقروءة.",
        "- الأثر الاستكشافي: WO-B-R41-SOUND-01263؛ `برز` يسمي الفوق والسبق مباشرة في شاهدين مع معنى victorious.",
        "- الصدى اللين: WO-B-R41-SOUND-01185؛ تراكم `كرس` وضم أكراس القلائد يلامسان بنية الضفيرة بلا اتحاد معجمي مباشر.",
        "- التفكيك النهائي المؤهل: S01186، S01187، S01188، S01204، S01216، S01221، S01225، S01232، S01244؛ قرئت المكونات مستقلة، ووقفت S01188 وS01204 وS01221 وS01232 عند عطب صوتي.",
        "- التحليلات غير المؤهلة: S01198، S01201، S01202، S01205، S01233، S01245، S01254؛ لم تحول الاحتمالات والتحليل السطحي والتاريخي إلى تفكيك نهائي.",
        "- أعطاب الأداة: S01188، S01190، S01203، S01204، S01215، S01219، S01221، S01231، S01232، S01247، S01252، S01254، S01260؛ لم تعوض الصوامت المنطوقة الساقطة.",
        "- فجوات القانون: S01191، S01208، S01218، S01223، S01230، S01234، S01238، S01246، S01255، S01256، S01257، S01258، S01261.",
        "- المعزول خارج النطاق: S01189 اسم إقليم، وS01201 اسم بطل، وS01214 اسم قلعة وإقليم، وS01236 اختصار كتابي.",
        "- أحواض `nucleus-sweep-*.json` التسعة الحالية v19 قرئت كاملة من القرص؛ both=14497 وsound_only=106817؛ ثبت الحجم وSHA-256 والعدادات لكل ملف.",
        f"- أكبر بطاقة: {max_size} بايت، {max_item.heading}؛ كل البطاقات دون 5KB.",
        "- لم تفعل طبقة البرهان؛ مر حارس نقاء الشحنة وختم CLEAN؛ لم يقع ship ولم يستعمل git.",
        "", f"<!-- {MARKER}:END -->", "", DONE_LINE,
    ])
    return "\n".join(lines)


def validate_existing(reading_text: str, report_text: str) -> None:
    match = re.search(rf"<!-- {re.escape(MARKER)}:START -->(.*?)<!-- {re.escape(MARKER)}:END -->", reading_text, re.DOTALL)
    if not match:
        raise AssertionError("محضر الجولة موجود وبطاقاتها غائبة")
    headings = re.findall(r"^### (WO-B-R41-SOUND-\d{5}):", match.group(1), re.MULTILINE)
    expected = [f"WO-B-R41-SOUND-{rank:05d}" for rank in SOUND_RANKS]
    if headings != expected:
        raise AssertionError("مقطع الجولة 41 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(DONE_LINE):
        raise AssertionError("سطر DONE41 ليس خاتمة التقرير")


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
        print("ROUND41 ALREADY PRESENT AND VALID")
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

    R40.SOURCE_NOTES = SOURCE_NOTES
    R40.REJECTED_ANALYSES = REJECTED_ANALYSES
    R40.FORM_LINKS = FORM_LINKS
    R39.SOURCE_NOTES = SOURCE_NOTES
    R39.REJECTED_ANALYSES = REJECTED_ANALYSES
    R39.FORM_LINKS = FORM_LINKS
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
        "## الجولة الحادية والأربعون: متابعة حوض sound_only (2026-08-27)\n\n"
        "- النطاق: 70 عضوا طازجا بعد WO-B-R40-SOUND-01182؛ من الرتبة 1183 إلى 1263 مع تجاوز 1197 و1200 و1206 و1220 و1229 و1235 و1242 و1248 و1249 و1253 و1262 لأنها مقروءة؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ طريق المعنى مسمى، والمدار اليدوي حاسم، والأصداء مفصولة عن الأثر المحكم.\n"
        "- لقطة الأحواض: قرئت ملفات nucleus-sweep-*.json التسعة الحالية v19 من القرص؛ ثبتت بصماتها وعداداتها قبل الانتخاب.\n\n"
        + "\n".join(texts[:35])
        + "\n## الدفعة الثانية: متابعة sound_only بعد الرتبة 1221\n\n"
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
    print("ROUND41 READY")
    print("NUCLEUS_V19_FILES", len(NUCLEUS_SNAPSHOT), "SHA256_AND_COUNTS_OK")
    print("NUCLEUS_V19_TOTALS", "BOTH=14497", "SOUND_ONLY=106817")
    print("SKIPPED", ",".join(map(str, stats["skipped"])))
    print("BATCHES", *BATCH_SIZES, "SELECTED", len(selected))
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("NUCLEUS_TRACE", "S01263")
    print("ROOT_ECHO", "S01185")
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
    print("ROUND41 WRITTEN")
    print(DONE_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
