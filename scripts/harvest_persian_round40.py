# -*- coding: utf-8 -*-
"""المسار B، الجولة 40: متابعة إنقاذ حوض sound_only في دفعتين من 35 بطاقة."""

from __future__ import annotations

import argparse
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

import harvest_persian_round39 as R39  # noqa: E402

R38 = R39.R38
R36 = R39.R36
R35 = R39.R35
R34 = R39.R34
R32 = R39.R32
R31 = R39.R31
R29 = R39.R29
R28 = R39.R28
H = R39.H
P = R39.P
P25 = R39.P25
READING = R39.READING
REPORT = R39.REPORT
SWEEP = R39.SWEEP
LEXICON = R39.LEXICON
RAW_LEXICON = R39.RAW_LEXICON
MARKER = "LANE-B-PERSIAN-ROUND40-2026-08-27"
CARD_LIMIT = 5120
SOUND_RANKS = (
    1109, 1110, 1111, 1112, 1113, 1114, 1115, 1116, 1117, 1119,
    1120, 1121, 1122, 1124, 1125, 1126, 1127, 1128, 1129, 1130,
    1131, 1132, 1133, 1134, 1135, 1136, 1137, 1138, 1139, 1140,
    1141, 1142, 1143, 1144, 1145, 1146, 1147, 1148, 1150, 1151,
    1152, 1153, 1154, 1156, 1157, 1158, 1159, 1160, 1161, 1162,
    1163, 1164, 1165, 1166, 1167, 1168, 1169, 1170, 1171, 1172,
    1173, 1174, 1175, 1176, 1177, 1178, 1179, 1180, 1181, 1182,
)
BATCH_SIZES = (35, 35)
DONE_LINE = "LANE-B DONE40 70 WO-B-R40-SOUND-01182"
EXPECTED_SKIPS = (1108, 1118, 1123, 1149, 1155)

EXPECTED_ENTRY_INDEX = dict(zip(SOUND_RANKS, (
    5779, 5780, 5782, 5783, 5785, 5803, 5804, 5805, 5812, 5821,
    5823, 5841, 5843, 5851, 5857, 5902, 5903, 5906, 5908, 5911,
    5916, 5927, 5928, 5954, 5958, 5959, 5962, 5972, 5974, 5976,
    5977, 6022, 6070, 6076, 6083, 6085, 6108, 6119, 6121, 6122,
    6123, 6130, 6155, 6171, 6191, 6194, 6195, 6196, 6204, 6206,
    6208, 6211, 6213, 6218, 6219, 6232, 6233, 6238, 6239, 6254,
    6271, 6272, 6273, 6276, 6277, 6279, 6282, 6283, 6285, 6297,
)))
EXPECTED_RAW_LINE = dict(zip(SOUND_RANKS, (
    6783, 6784, 6786, 6787, 6789, 6807, 6808, 6809, 6817, 6829,
    6832, 6850, 6852, 6862, 6868, 6917, 6918, 6921, 6923, 6926,
    6932, 6945, 6946, 6974, 6978, 6979, 6982, 6995, 7003, 7005,
    7006, 7059, 7117, 7123, 7130, 7133, 7163, 7174, 7176, 7177,
    7178, 7191, 7221, 7240, 7263, 7267, 7268, 7269, 7279, 7281,
    7283, 7286, 7288, 7295, 7296, 7309, 7310, 7317, 7318, 7336,
    7356, 7357, 7361, 7364, 7365, 7367, 7371, 7372, 7374, 7386,
)))

PARSER_FROM_PLUS = {1109, 1110, 1117, 1119, 1128, 1141, 1148, 1153, 1172}
EXACT_DECOMPOSITIONS = {
    1109, 1110, 1117, 1119, 1125, 1128,
    1141, 1148, 1153, 1170, 1171, 1172,
}
EXPECTED_COMPONENTS = {
    1109: ("پالایش", "ـگاه"),
    1110: ("پالای", "ـش"),
    1117: ("سیگار", "ـی"),
    1119: ("یائسه", "ـگی"),
    1125: ("آلوده", "گی"),
    1128: ("کوشیدن", "ـش"),
    1141: ("ملی", "گرا"),
    1148: ("تازه", "ـگی"),
    1153: ("گوشت", "ـی"),
    1170: ("نیو", "ـک"),
    1171: ("نیو", "ـک"),
    1172: ("سز", "ـا"),
}
COMPONENT_READINGS = {
    1109: "`پالایش`: entry[5780] والخام 6784 لمعنى refining، ومروحتها 12، وهي نفسها مفككة إلى `پالای` و`ـش`: COMPOUND-BOUNDARY. `ـگاه`: entry[7462] والخام 8752 لاحقة مكان أو زمان، ومروحتها 72: MORPHOLOGY-GAP.",
    1110: "`پالای`: غائبة مستقلة من branch-lexicons والخام، ومروحتها 40: FORM-LINK. `ـش`: اختيرت entry[10303] والخام 12674 لصنع اسم الحدث، ومروحتها صفر: MORPHOLOGY-GAP.",
    1117: "`سیگار`: entry[1435] والخام 1517 لمعنى cigarette، ومروحتها 24: OPEN-CANDIDATE. `ـی`: اختيرت entry[6329] والخام 7421 لاحقة صفة، ومروحتها صفر: MORPHOLOGY-GAP.",
    1119: "`یائسه`: entry[15981] والخام 19037 لمعنى menopausal، وخبرها يصرح بالقرض من العربية `يائسة`، ومروحتها 48: SEMITIC-SOURCE-TRANSMISSION للمكون وحده. `ـگی`: غائبة من branch-lexicons والخام 17716 لاحقة، ومروحتها 56: MORPHOLOGY-GAP.",
    1125: "`آلوده`: entry[14146] والخام 17021 لمعنى polluted، ومروحتها 12: OPEN-CANDIDATE. `گی` هي صورة `ـگی` في التفكيك؛ الخام 17716 لاحقة، ومروحتها 56: MORPHOLOGY-GAP.",
    1128: "`کوشیدن`: entry[12147] والخام 14867 لمعنى try أو strive، ومروحتها 18: OPEN-CANDIDATE. `ـش`: entry[10303] والخام 12674 لاحقة اسم الحدث، ومروحتها صفر: MORPHOLOGY-GAP.",
    1141: "`ملی`: entry[2751] والخام 3026 لمعنى national، وخبرها يصرح بالقرض من العربية، ومروحتها 20: SEMITIC-SOURCE-TRANSMISSION للمكون. `گرا`: غائبة مستقلة، لكن `ـگرا` entry[7519] والخام 8814 لاحقة -ist، ومروحتها 80: MORPHOLOGY-GAP.",
    1148: "`تازه`: اختيرت entry[1160] والخام 1232 لمعنى fresh أو new، ومروحتها 90؛ خبرها يسمي العربية `طازج` آخذة من الصورة الوسطى: LOANWORD-NON-ARABIC-TO-ARABIC للمكون وحده. `ـگی`: الخام 17716 لاحقة، ومروحتها 56: MORPHOLOGY-GAP.",
    1153: "`گوشت`: entry[325] والخام 343 لمعنى meat، ومروحتها 36: OPEN-CANDIDATE. `ـی`: entry[6329] والخام 7421 لاحقة صفة، ومروحتها صفر: MORPHOLOGY-GAP.",
    1170: "`نیو`: entry[7945] والخام 9279 لمعنى brave أو valiant، ومروحتها صفر: FORM-LINK. `ـک`: entry[7513] والخام 8807 لاحقة تصغير، ومروحتها صفر: MORPHOLOGY-GAP.",
    1171: "مرجع المكونين في S01170: `نیو` و`ـک`؛ فصلت الحال well أو completely عن الصفة good ولم تورث حكمها.",
    1172: "`سز`: الجذع غائب مستقلا، لكن `سزیدن` entry[4267] والخام 4762 لمعنى be worthy أو deserve، ومروحة الجذع 90: FORM-LINK. `ـا`: اختيرت entry[7537] والخام 8834 لاحقة اسم أو صفة، ومروحتها صفر: MORPHOLOGY-GAP.",
}

TOOL_GAPS = {
    1109: "الصورة `پالایشگاه` منقوطة /pâlâyešgâh/، لكن الهيكل أسقط /y/ والهاء النهائية المنطوقة.",
    1110: "الصورة `پالایش` منقوطة /pâlâyeš/، لكن الهيكل أسقط /y/ المنطوقة.",
    1119: "الصورة `یائسگی` منقوطة /yā'isagī/، لكن الهيكل أسقط الوقفة الحنجرية /ʔ/ الممثلة بالهمزة.",
    1140: "الصورة `ملی‌گرایی` منقوطة /melli-garâyi/، لكن الهيكل أسقط /y/ المنطوقة.",
    1144: "الصورة `نیایش` منقوطة /niyâyeš/، لكن الهيكل أسقط انزلاقي /y/ المنطوقين.",
    1157: "الصورة `گیان` منقوطة /goyân/، لكن الهيكل أسقط /y/ المنطوقة.",
}
LAW_GAPS = {1113, 1129, 1132, 1145, 1146, 1163, 1164, 1178}
OUT_OF_SCOPE = {
    1165: "المدخلة اسم النجم Canopus بعينه؛ لا معنى معجميا عاما في العضو.",
}
REJECTED_ANALYSES = {
    1113: "التحليل إلى `یک` و`ـانه` موسوم By surface analysis بعد الصورة الوسطى، فلم يؤهل تفكيكا نهائيا.",
    1140: "حقل الأصل الخام فارغ؛ لم يستخرج تفكيك `ملی‌گرایی` من شفافية الرسم وحدها.",
}
SOURCE_NOTES = {
    1113: "حفظت الصورة الفارسية الوسطى، ولم تحول التحليل السطحي إلى بنية نهائية.",
    1114: "سلسلة الأصل الإيرانية والهندوأوروبية لا تسمي العربية طرفا في النسب.",
    1115: "فصلت الحال exciting عن الصفة hot؛ لم يرث أحد المتجانسين حكم الآخر.",
    1116: "فصلت اسم العلامة أو الندبة عن الصفة والحال؛ لم يعوض غياب الشاهد العربي من خبر القرابة الهندوأوروبية.",
    1120: "حقل الأصل فارغ؛ لم يعوض أصل porn من المعرفة العامة.",
    1126: "خبر الأصل يسمي prominent وforward في الطبقة الإيرانية، لكنه لا يسمي صلة عربية؛ حفظ التشابه مع `برز` صدى لينا.",
    1127: "كرر الخبر الطبقة الإيرانية نفسها؛ لم يحول معنى tall أو high إلى نسب عربي.",
    1130: "المقارنات الهندوأوروبية والإيرانية حواش أصل؛ لا تسمي العربية طرفا.",
    1131: "المقارنة بالسويدية حاشية cognate بعيدة؛ لا تمد طريقا عربيا.",
    1134: "خبر الأصل يرد الصورة إلى Middle Persian *dalag ويسمي العربية `دلق` آخذة؛ لكن القاف التاريخية غائبة من الهيكل الحديث ومن مروحته الحية، فلم يصدر حكم نقل من مسار ناقص.",
    1139: "المقارنة بالإنجليزية hook حاشية هندوأوروبية؛ لا تسمي العربية.",
    1140: "حقل الأصل فارغ، ومع عطب /y/ لم يخترع تفكيك أو حكم.",
    1141: "التفكيك النهائي مقبول، لكن قرض `ملی` من العربية حكم للمكون لا للصورة المركبة nationalist.",
    1148: "خبر `تازه` يسمي العربية `طازج` آخذة، لكن الحكم للمكون؛ لم يرث `تازگی` المشتق حكمه.",
    1156: "حقل الأصل فارغ؛ لم يحول لفظ التحبب إلى محاكاة صوتية مفترضة.",
    1163: "المصدر يسمي لغة تركية مانحا؛ لا يسمي العربية ولا يصلح صف چ↔ج المفقود.",
    1168: "المقارنة المحتملة بالهندية والأردية لا تسمي العربية ولا تثبت معنى الخرطوم لها.",
    1169: "فصلت الصفة عن اسم خرطوم الفيل السابق؛ لم يرث أحد المتجانسين حكم الآخر.",
    1175: "خبر الأصل يسمي `تيغار` العربية اقتراضا إيرانيا أوسط، وتاج العروس يثبت الإجانة وصورة العامة `تغار`.",
    1181: "المقارنة باللاتينية والسلافية حاشية هندوأوروبية؛ لا تسمي العربية طرفا.",
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
        return f"WO-B-R40-SOUND-{self.row.rank:05d}"


Review = R39.Review
R = R39.R

# سجل قراءة يدوي. لا يشتق الحكم من best ولا من وزن المروحة.
REVIEWS = {
    1109: R("بلسك", "TOOL-GAP", "جسر المعنى: refinery مصرح بتكوينه من `پالایش` و`ـگاه`، لكن الهيكل فقد /y/ و/h/.", "قُرئ المكونان ثم أوقف عطب الصامتين حكم الصورة المجموعة."),
    1110: R("بلس", "TOOL-GAP", "جسر المعنى: refining مصرح باشتقاقه من `پالای` و`ـش`، لكن /y/ غابت من الهيكل.", "الجذع واللاحقة مقروءان بحدودهما، ولا حكم من صف أسقط انزلاقا منطوقا."),
    1111: R("بسبر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بسبر`: الجفاف واليبوسة مع استرسال؛ لا يسمي polymer.", "حقل الأصل فارغ، ولم يحول تماسك البوليمر إلى يبوسة عربية معجمية."),
    1112: R("برمل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`برمل`: التجرد والخلوص؛ لا يسمي polymer.", "فصلت اللفظ الدخيل المتجانس معنى عن المدخلة السابقة، وحقل الأصل فارغ."),
    1113: R("يقن", "LAW-GAP", "نص الحدث المجمد لـ`يقن`: الثبوت والاستقرار؛ لا يسمي unique، ومعه گ↔ق غير مسمى.", "اليقين ثبوت معرفة لا الوحدانية؛ والتحليل السطحي لم يصلح فجوة القانون."),
    1114: R("داغ", "OPEN-CANDIDATE", "نص محاكم الحروف لـ`داغ` لا يقدم معنى معجميا مسمى للحرارة.", "الموارد العربية الحالية لا تقدم شاهدين لـ`داغ` بمعنى hot، وخبر الأصل لا يسمي العربية."),
    1115: R("داغ", "OPEN-CANDIDATE", "نص محاكم الحروف لـ`داغ` لا يسمي exciting.", "فصلت الحال عن الصفة السابقة؛ لم يرث المتجانس حكم الحرارة ولا اختلق له شاهد."),
    1116: R("داغ", "OPEN-CANDIDATE", "نص محاكم الحروف لـ`داغ` لا يسمي brand أو scar.", "فصلت الاسم عن الصفة والحال؛ غاب الشاهد العربي الكلاسيكي ولم يعوض من القرابة البعيدة."),
    1117: R("سجر", "COMPOUND-BOUNDARY", "جسر المعنى: cigarette smoker مصرح باشتقاقه من `سیگار` cigarette و`ـی` الصفة.", "قُرئ المكونان؛ لم يختزل المدخن في حدث ملء `سجر` ولا ورث حكم المكون."),
    1119: R("يسق", "TOOL-GAP", "جسر المعنى: menopause مصرح باشتقاقه من `یائسه` و`ـگی`، لكن /ʔ/ غابت من الهيكل.", "قرض المكون العربي محفوظ، لكن الصورة المشتقة توقفت عند عطب الهمزة."),
    1120: R("برن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`برن`: التجرد والخلوص؛ لا يسمي porn.", "حقل الأصل فارغ وشواهد المرشح لا تقدم المادة الحديثة؛ لم تعوض من المعرفة العامة."),
    1121: R("بخس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بخس`: النقص في الأثناء؛ لا يسمي fly.", "البخس نقص مقدار لا اسم حشرة، ولم يوجد خبر أصل يربطهما."),
    1122: R("خج", "OPEN-CANDIDATE", "نص محاكم الحروف لـ`خج` لا يسمي egg.", "حقل الأصل فارغ، وشواهد المرشح لا تقدم البيضة أو قشرتها."),
    1124: R("لب", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`لب`: اللزوم والتداخل؛ لا يسمي cheek.", "شواهد اللب في داخل الشيء والعقل، لا الخد؛ قرب الموضع الجسدي لا يكفي."),
    1125: R("الدك", "COMPOUND-BOUNDARY", "جسر المعنى: pollution مصرح بتكوينه من `آلوده` polluted و`گی` الاسم.", "قُرئ الوصف واللاحقة؛ لم تقارن الصورة المشتقة جذرا رباعيا."),
    1126: R("برز", "ROOT-ECHO", "جسر المعنى: height أو ascent يلامس بروز الشيء وظهوره، لكن العربية لا تسمي الارتفاع نفسه.", "مدار لين: البروز خروج وسبق وظهور، والارتفاع أثر محتمل لا تطابق معجمي مباشر؛ حفظ ROOT-ECHO دون أثر."),
    1127: R("برز", "ROOT-ECHO", "جسر المعنى: tall أو high يلامس الشيء البارز، لكن شواهد `برز` تسمي الظهور والسبق لا الطول.", "فصلت الصفة عن الاسم السابق؛ بقي التقارب صدى لينا ولم يرق إلى ROOT-TRACE."),
    1128: R("كشش", "COMPOUND-BOUNDARY", "جسر المعنى: effort مصرح باشتقاقه من `کوشیدن` strive و`ـش` اسم الحدث.", "قُرئ الفعل واللاحقة؛ لم يورث المركب حدث خروج الدقيق للمرشح."),
    1129: R("جش", "LAW-GAP", "نص محاكم الحروف لـ`جش` لا يسمي eye، ومعه چ↔ج غير مسمى.", "حقل الأصل فارغ، ولم تعوض العين العربية من خارج المروحة صف الصوت المفقود."),
    1130: R("حردن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`حردن`: الخلوص من الغلظ مع ضبط؛ لا يسمي eat أو drink.", "حفظت قصة تداخل مع `خوردن` والمقارنات الإيرانية، ولم تنقلها إلى معنى عربي."),
    1131: R("سمدن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سمدن`: خرق يضم مع ضبط؛ لا يسمي faint أو confounded.", "المقارنة السويدية لا تمد طريقا عربيا، وشواهد المرشح لا تثبت الإغماء."),
    1132: R("جوغ", "LAW-GAP", "نص محاكم الحروف لـ`جوغ` لا يسمي wood، ومعه چ↔ج غير مسمى.", "الإحالة إلى `چوب` فارسية داخلية؛ لم تجعلها قانونا عربيا أو شاهدا للخشب."),
    1133: R("جوغ", "OPEN-CANDIDATE", "نص محاكم الحروف لـ`جوغ` لا يسمي stream أو brook.", "المقارنات الفارسية والإيرانية تثبت تاريخ الصورة داخل الفرع، لا جدولا عربيا للمجرى."),
    1134: R("دل", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`دل`: الامتداد إلى مقر؛ لا يسمي pine marten.", "المصدر يثبت نقل `دلق` إلى العربية، لكن القاف التاريخية خارج هيكل `دله` الحديث ومروحته؛ حفظ الخبر ولم يصدر حكم من عضو آخر."),
    1135: R("مل", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`مل`: الامتداد مع الحوز؛ لا يسمي wine.", "خبر الصغدية والبخترية والهندوأوروبية لا يسمي العربية؛ لم يورث الخمر من متحد الرسم."),
    1136: R("مل", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`مل`: الامتداد مع الحوز؛ لا يسمي neck.", "فصلت العنق عن الخمر السابق؛ الشواهد العربية لا تقدم العضو لهذا الرسم."),
    1137: R("كربك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كربك`: التركز والمعاودة؛ لا يسمي lizard.", "حقل الأصل فارغ، ولم تستخرج الزواحف من صورة المرشح أو وزنه."),
    1138: R("خو", "OPEN-CANDIDATE", "نص محاكم الحرفين لـ`خو` لا يسمي temper أو disposition.", "الصورة الوسطى والمقارنة الأرمنية حاشيتان؛ الموارد العربية لا تقدم الخلق لهذا الرسم."),
    1139: R("كج", "OPEN-CANDIDATE", "نص محاكم الحرفين لـ`كج` لا يسمي crooked.", "الخطاف الإنجليزي مقارنة بعيدة، وشواهد المرشح العربية لا تثبت الاعوجاج."),
    1140: R("مرجل", "TOOL-GAP", "جسر المعنى: nationalism ظاهر مركبا، لكن الخام لم يفككه و/ y / المنطوقة غابت من الهيكل.", "لم يخترع تفكيك من الرسم، وأوقف عطب الانزلاق الصورة قبل الحكم."),
    1141: R("مرجل", "COMPOUND-BOUNDARY", "جسر المعنى: nationalist مصرح بتكوينه من `ملی` national و`گرا` -ist.", "قُرئ المكونان؛ قرض `ملی` العربي حكم للمكون وحده، ولم يورثه المركب."),
    1142: R("نهد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`نهد`: فراغ يتخلل الشيء مع ضبط؛ لا يسمي nature أو personality.", "الأساس في الصورة الوسطى حاشية تاريخية، وشواهد النهد لا تقدم الطبع النفسي."),
    1143: R("نجر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`نجر`: نفاذ بغلظ وقوة؛ لا يسمي chart.", "حقل الأصل فارغ؛ لم يحول النقش أو النجارة إلى رسم بياني بلا شاهد."),
    1144: R("نش", "TOOL-GAP", "جسر المعنى: praise أو adoration مفحوص، لكن /niyâyeš/ فقدت انزلاقي /y/.", "أوقف عطب الهيكل المدخلة قبل إسقاط الصوائت أو انتخاب جذر."),
    1145: R("جر", "LAW-GAP", "نص النواة المجمدة لـ`جر`: الاسترسال والامتداد؛ لا يسمي why، ومعه چ↔ج غير مسمى.", "الإحالة إلى `چرا` داخل الفرع لا تصلح صفا صوتيا ولا معنى عربيا للاستفهام."),
    1146: R("جرح", "LAW-GAP", "نص الحدث المجمد لـ`جرح`: قطع ظاهر الجسم؛ لا يسمي cycle، ومعه چ↔ج غير مسمى.", "خبر العجلة الهندوإيرانية لا يسمي العربية، ولم تعوض الدورية من الجرح."),
    1147: R("بدر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بدر`: الزيادة والسبق إلى كمال؛ لا يسمي awake أو alert.", "الاستيقاظ ليس سبق البدر، والمقارنات الهندوأوروبية لا تسمي العربية."),
    1148: R("طزج", "COMPOUND-BOUNDARY", "جسر المعنى: novelty أو recency مصرح باشتقاقه من `تازه` new و`ـگی` الاسم.", "قُرئ المكونان؛ نقل `تازه` إلى العربية `طازج` حكم للمكون، لا للصورة المشتقة."),
    1150: R("جند", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جند`: الصلابة والغلظ؛ لا يسمي fetid أو rotten.", "خبر الرائحة الهندوإيراني لا يسمي العربية، وغلظ الشيء ليس نتنه."),
    1151: R("جند", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جند`: الصلابة والغلظ؛ لا يسمي large أو huge مباشرة.", "فصلت حس الضخامة عن النتن السابق؛ شواهد الجند في الجماعة لا الحجم."),
    1152: R("جند", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جند`: الصلابة والغلظ؛ لا يسمي very.", "فصلت الحال عن الصفتين السابقتين؛ لم تورث شدة الدرجة من غلظ محتمل."),
    1153: R("جست", "COMPOUND-BOUNDARY", "جسر المعنى: fleshy أو meaty مصرح باشتقاقه من `گوشت` meat و`ـی` الصفة.", "قُرئ الاسم واللاحقة؛ لم تقارن الصفة المشتقة جذر `جست`."),
    1154: R("بش", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`بش`: الانتشار الظاهر؛ لا يسمي louse.", "حقل الأصل فارغ، وشواهد المرشح لا تقدم القملة."),
    1156: R("هب", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`هب`: مفارقة المقر باندفاع؛ لا يسمي doggy.", "لفظ التحبب بلا خبر أصل؛ لم يخترع له مسار محاكاة صوتية."),
    1157: R("جن", "TOOL-GAP", "جسر المعنى: tent مفحوص، لكن /goyân/ يحمل /y/ أسقطها الهيكل.", "حفظت الصورة الإيرانية الوسطى، وأوقف عطب الانزلاق الحكم."),
    1158: R("جر", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`جر`: الاسترسال والامتداد؛ لا يسمي cleft أو canyon.", "خبر الأصل احتمالي بين الإيراني والتركي؛ لم يحول الفراغ إلى جر عربي."),
    1159: R("وز", "OPEN-CANDIDATE", "نص محاكم الحرفين لـ`وز` لا يسمي open أو open wide.", "الإحالة إلى السابقة الإيرانية لا تقدم شاهدا عربيا للفتح."),
    1160: R("جنم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جنم`: الستر والكثافة مع ضم؛ لا يسمي wheat.", "حقل الأصل فارغ؛ لم يساو القمح بالغنم أو بجمع كثيف."),
    1161: R("جس", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`جس`: الاختراق الحسي أو المعنوي؛ لا يسمي acerb أو acrid.", "الإحالة إلى `گست` لا تعطي معنى عربيا، ولم يستخرج الطعم من الاختراق."),
    1162: R("دم", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`دم`: استواء الظاهر وبروزه؛ لا يسمي face أو visage مباشرة.", "المقارنات الإيرانية والأرمنية لا تسمي العربية؛ ظل سطح الوجه صدى غير معجمي."),
    1163: R("جبق", "LAW-GAP", "نص الحدث المجمد لـ`جبق`: تجسم وبروز مع قطع؛ لا يسمي tobacco pipe، ومعه چ↔ج غير مسمى.", "خبر القرض التركي محفوظ، لكنه لا يسمي العربية ولا يصلح صف الصوت."),
    1164: R("اج", "LAW-GAP", "نص محاكم الحرفين لـ`اج` لا يسمي Cappadocian maple، ومعه چ↔ج غير مسمى.", "اسم النوع النباتي بلا أصل منشور؛ لم يخترع له قانونا أو معنى عربيا."),
    1165: R("برك", "OUT-OF-SCOPE", "جسر المعنى: Canopus اسم نجم بعينه، لا معنى معجميا عاما.", "حفظ اسم العلم في التغطية وعزل من الحكم الجذري."),
    1166: R("جرد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جرد`: تكشف ظاهر الجسم وعريه؛ لا يسمي dust أو powder.", "الغبار قد ينكشف عن الدوران، لكن المصدر لا يسمي المعنى العربي ولا نقطة تطابق مباشرة."),
    1167: R("جرد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جرد`: تكشف الظاهر؛ لا يسمي hero.", "فصلت البطل عن الغبار السابق؛ الاحتمال المتصل بكرد حاشية لا شاهد معنى."),
    1168: R("شنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شنج`: انتشار دقاق من الأثناء؛ لا يسمي elephant trunk.", "المقارنة الهندية والأردية محتملة، وشواهد الشنج في التقبض لا الخرطوم."),
    1169: R("شنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شنج`: انتشار دقاق؛ لا يسمي beautiful أو playful.", "فصلت الصفة عن اسم الخرطوم؛ لم يرث أحد المتجانسين حكم الآخر."),
    1170: R("نيك", "COMPOUND-BOUNDARY", "جسر المعنى: good مصرح بمكافأته إلى `نیو` brave و`ـک` التصغير بعد الصورة الوسطى.", "قُرئ المكونان؛ لم يورث المعنى التاريخي للمرشح العربي المتجانس."),
    1171: R("نيك", "COMPOUND-BOUNDARY", "جسر المعنى: well أو completely يحمل البنية التاريخية نفسها `نیو` و`ـک`.", "فصلت الحال عن الصفة السابقة؛ لم يرث أحدهما حكم الآخر."),
    1172: R("شز", "COMPOUND-BOUNDARY", "جسر المعنى: deserved reward مصرح باشتقاقه من جذع `سز` و`ـا` بعد الصورة الوسطى.", "قُرئ الفعل المرجعي واللاحقة؛ الجذع غائب مستقلا ولم يقارن المركب وحدة."),
    1173: R("بو", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`بو`: الوصول؛ لا يسمي leg أو foot.", "حقل الأصل فارغ، والوصول وظيفة ممكنة للرجل لا تعريف معجمي للعضو."),
    1174: R("بم", "OPEN-CANDIDATE", "نص محاكم الحرفين لـ`بم` لا يسمي cotton.", "حقل الأصل فارغ، وشواهد المرشح لا تقدم القطن أو ليفه."),
    1175: R("تغر", "LOANWORD-NON-ARABIC-TO-ARABIC", "جسر المعنى: tub أو trough يطابق `التِّيغار` الإجانة وصورة العامة `تغار` في تاج العروس.", "خبر الأصل يسمي الصيغ العربية اقتراضات إيرانية وسطى؛ أغلق اتجاه الدخول تماسًا لا إرثا."),
    1176: R("مجج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مجج`: اندفاع المائع من ضامه؛ لا يسمي eyelash.", "حقل الأصل فارغ، ولم تستخرج الرموش من حركة المائع أو تجمعه."),
    1177: R("مجج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مجج`: اندفاع المائع؛ لا يسمي tiny.", "فصلت الصفة عن اسم الرمش السابق؛ لم يرث أحد المتجانسين حكم الآخر."),
    1178: R("جزق", "LAW-GAP", "نص الحدث المجمد لـ`جزق`: التميز والانفصال في الكتلة؛ لا يسمي neck، ومعه گ↔ق غير مسمى.", "لا أصل منشور ولا شاهد للعنق؛ لم يعوض المعنى صف الصوت المفقود."),
    1179: R("بس", "OPEN-CANDIDATE", "نص النواة المجمدة لـ`بس`: الجفاف واليبوسة؛ لا يسمي boy أو son.", "حقل الأصل فارغ؛ لم يستخرج البنوة من اليبس أو من متحد الرسم."),
    1180: R("جش", "OPEN-CANDIDATE", "نص محاكم الحرفين لـ`جش` لا يسمي sheep barn.", "حقل الأصل فارغ، وشواهد المرشح لا تقدم حظيرة أو غنما."),
    1181: R("بيل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بيل`: التمكن والحوز مع امتداد؛ لا يسمي shovel أو 12 hours.", "الشاهد العربي يسمي نهرا لا مجرفة، والمقارنة الهندوأوروبية لا تسمي العربية."),
    1182: R("كلب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كلب`: العض والإمساك؛ لا يسمي beak.", "المنقار أداة عض محتملة، لكن الشواهد تسمي الكلب لا عضو الطائر؛ بقي التقارب وظيفيا لا معجميا."),
}


def pair_key(row: H.SweepRow) -> tuple[str, str]:
    return H.clean(row.branch), H.norm_gloss(row.gloss)


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
            if row.rank > 1107 and len(fresh) < 70:
                internal_skips.append(row.rank)
            continue
        seen.add(key)
        if row.rank <= 1107:
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
        "پالایش": {5780}, "ـگاه": {7462}, "پالای": set(), "ـش": {10302, 10303},
        "سیگار": {1435}, "ـی": {6328, 6329, 6330, 6331}, "یائسه": {15981},
        "ـگی": set(), "آلوده": {14146}, "کوشیدن": {12147}, "ملی": {2751},
        "ـگرا": {7519}, "تازه": {1159, 1160}, "گوشت": {325}, "نیو": {7945},
        "ـک": {7513}, "سز": set(), "سزیدن": {4267}, "ـا": {7536, 7537, 7538},
    }
    fan_counts = {
        "پالایش": 12, "ـگاه": 72, "پالای": 40, "ـش": 0, "سیگار": 24,
        "ـی": 0, "یائسه": 48, "ـگی": 56, "آلوده": 12, "کوشیدن": 18,
        "ملی": 20, "ـگرا": 80, "تازه": 90, "گوشت": 36, "نیو": 0,
        "ـک": 0, "سز": 90, "سزیدن": 27, "ـا": 0,
    }
    for word, expected in expected_indices.items():
        actual = {index for index, _entry in grouped.get(word, [])}
        if actual != expected:
            raise AssertionError(f"تغير جرد مكون {word}: {sorted(actual)}")
        fan = tuple(H.FAN.rank(word, H.FAN.fan(word, "persian"), "persian"))
        if len(fan) != fan_counts[word]:
            raise AssertionError(f"تغيرت مروحة المكون {word}: {len(fan)}")
    expected_raw = {
        "پالایش": {6784}, "ـگاه": {8752}, "پالای": set(), "ـش": {12673, 12674},
        "سیگار": {1517}, "ـی": {7420, 7421, 7422, 7423, 7424}, "یائسه": {19037},
        "ـگی": {17716}, "آلوده": {17021}, "کوشیدن": {14867}, "ملی": {3026},
        "ـگرا": {8814}, "تازه": {1231, 1232}, "گوشت": {343}, "نیو": {9279},
        "ـک": {8807}, "سز": set(), "سزیدن": {4762}, "ـا": {8833, 8834, 8835},
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
    if review.verdict == "ROOT-ECHO":
        return "اكتمل الصوت وظهر تقارب حدثي، لكن المعنى المعجمي لم يتحد مباشرة؛ حفظ صدى لين لا أثر."
    if review.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC":
        return "سمى المصدر الصيغة العربية اقتراضا إيرانيا واتفقت صورة الوعاء ومعناه؛ أغلق تماس لا إرثا."
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
    strip_marks = lambda value: "".join(  # noqa: E731
        char for char in H.clean(value) if unicodedata.category(char) != "Mn"
    )
    joined = strip_marks(raw["etymology"])
    for component in EXPECTED_COMPONENTS[rank]:
        if strip_marks(component).replace("ـ", "") not in joined.replace("ـ", ""):
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


BASE_MAKE_CARD = R39.make_card


def make_card(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit) -> str:
    card = BASE_MAKE_CARD(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit)
    card = card.replace("الجولة 39،", "الجولة 40،")
    if item.row.rank in {1126, 1127}:
        card = re.sub(
            r"^- المصفاة:.*$",
            "- المصفاة: `برز` يثبت الظهور والسبق لا الارتفاع نفسه؛ حفظ ROOT-ECHO لينا ولم يرق إلى أثر.",
            card,
            count=1,
            flags=re.MULTILINE,
        )
    if item.row.rank == 1175:
        card = re.sub(
            r"^- المصفاة:.*$",
            "- المصفاة: خبر الأصل يسمي `تيغار` العربية اقتراضا إيرانيا أوسط، والتاج يثبت الإجانة وصورة `تغار`؛ يعمل LOANWORD-NON-ARABIC-TO-ARABIC نتيجة تماس محسوبة.",
            card,
            count=1,
            flags=re.MULTILINE,
        )
    return card


def validate_decisions(selected, raw_entries, decisions, ranked_by_rank, sense_map) -> None:
    if set(REVIEWS) != set(SOUND_RANKS):
        raise AssertionError("جدول المدار اليدوي لا يغطي الرتب السبعين")
    parsed = {item.row.rank for item in selected if P25.direct_from_plus(raw_entries[item.row.rank]["etymology"])}
    if parsed != PARSER_FROM_PLUS:
        raise AssertionError(f"تغيرت أسطر From X + Y التي يلتقطها المحلل: {sorted(parsed)}")
    expected_verdicts = {
        "COMPOUND-BOUNDARY": 9,
        "LAW-GAP": 8,
        "LOANWORD-NON-ARABIC-TO-ARABIC": 1,
        "OPEN-CANDIDATE": 43,
        "OUT-OF-SCOPE": 1,
        "ROOT-ECHO": 2,
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
        _count, coverage, _witnesses = P.classical_witnesses(decision.candidate, sense_map, 320)
        if decision.verdict == "LAW-GAP" and complete:
            raise AssertionError(f"LAW-GAP بلا صف مفقود في الرتبة {row.rank}")
        if decision.verdict in {
            "OPEN-CANDIDATE", "OUT-OF-SCOPE", "ROOT-ECHO",
            "LOANWORD-NON-ARABIC-TO-ARABIC",
        } and not complete:
            raise AssertionError(f"حكم بمسار ناقص في الرتبة {row.rank}: {decision.verdict}")
        if decision.verdict in {"ROOT-ECHO", "LOANWORD-NON-ARABIC-TO-ARABIC"}:
            if coverage < 2 or H.event_line(decision.candidate).startswith("لا حدث"):
                raise AssertionError(f"نتيجة بلا حدث وشاهدين في الرتبة {row.rank}")
        if row.rank in EXACT_DECOMPOSITIONS and decision.verdict not in {"COMPOUND-BOUNDARY", "TOOL-GAP"}:
            raise AssertionError(f"تفكيك مؤهل بلا حد مركب أو عطب أداة في الرتبة {row.rank}")
        if row.rank in TOOL_GAPS and decision.verdict != "TOOL-GAP":
            raise AssertionError(f"هيكل ناقص بلا TOOL-GAP في الرتبة {row.rank}")
        if row.rank in LAW_GAPS and decision.verdict != "LAW-GAP":
            raise AssertionError(f"مسار ناقص بلا LAW-GAP في الرتبة {row.rank}")
        if row.rank in OUT_OF_SCOPE and decision.verdict != "OUT-OF-SCOPE":
            raise AssertionError(f"اسم خاص بلا OUT-OF-SCOPE في الرتبة {row.rank}")
        if not REVIEWS[row.rank].meaning_path.startswith(("جسر المعنى:", "نص الحدث المجمد", "نص النواة المجمدة", "نص محاكم")):
            raise AssertionError(f"طريق المعنى غير مسمى في الرتبة {row.rank}")
    etymology = raw_entries[1175]["etymology"]
    if "Middle Iranian borrowings" not in etymology or REVIEWS[1175].candidate != "تغر":
        raise AssertionError("انزلق دليل نقل تغار")


def validate_text(selected, texts, prior_pairs) -> None:
    if len(selected) != 70 or BATCH_SIZES != (35, 35):
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = re.findall(r"^### (WO-B-R40-SOUND-\d{5}):", joined, re.MULTILINE)
    if headings != [item.heading for item in selected]:
        raise AssertionError("معرفات الجولة 40 لا تطابق النافذة")
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
    if "LOANWORD-NON-ARABIC-TO-ARABIC نتيجة تماس" not in texts[SOUND_RANKS.index(1175)]:
        raise AssertionError("غاب إغلاق نقل تغار")


def report_section(selected, decisions, sizes, stats) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    batches = (selected[:35], selected[35:])
    lines = [f"<!-- {MARKER}:START -->", ""]
    previous = 1107
    for number, batch in enumerate(batches, 1):
        lo = 0 if number == 1 else 35
        hi = lo + len(batch)
        counts = Counter(decision.verdict for decision in decisions[lo:hi])
        distribution = "؛ ".join(f"{key}={counts[key]}" for key in sorted(counts))
        batch_skips = [rank for rank in stats["skipped"] if previous < rank <= batch[-1].row.rank]
        skipped = ", ".join(map(str, batch_skips)) or "0"
        lines.extend([
            f"## الجولة الأربعون، دفعة sound_only رقم {number}", "",
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
    echoes = [item.heading for item, decision in zip(selected, decisions) if decision.verdict == "ROOT-ECHO"]
    transmissions = [item.heading for item, decision in zip(selected, decisions) if decision.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC"]
    lines.extend([
        "## حصيلة الجولة الأربعين", "",
        f"- حمل `persian.md` مرة واحدة؛ أزواج WO-B المقروءة={stats['pair_count']}؛ المتجاوز داخل النافذة={', '.join(map(str, stats['skipped']))}.",
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- نطاق الصوت الجديد: الرتب 1109-1182 بعد WO-B-R39-SOUND-01107، مع تجاوز 1108 و1118 و1123 و1149 و1155 لأنها مقروءة.",
        f"- الأصداء اللينة: {', '.join(echoes)}؛ `برز` يلامس الارتفاع والبروز، لكنه لم يرق إلى أثر محكم ولم تفعل طبقة البرهان.",
        f"- نتائج النقل المصفاة: {', '.join(transmissions)}؛ `تغار` أغلق تماسًا إيرانيا أوسط إلى العربية بدليل المصدر والمعجم.",
        "- التفكيك النهائي المؤهل: S01109، S01110، S01117، S01119، S01125، S01128، S01141، S01148، S01153، S01170، S01171، S01172؛ قرئت المكونات مستقلة، ووقفت S01109 وS01110 وS01119 عند عطب صوتي.",
        "- التحليلات غير المؤهلة: S01113 موسوم surface analysis، وS01140 خامه خال؛ لم يحولا إلى تفكيك نهائي.",
        "- أعطاب الأداة: S01109، S01110، S01119، S01140، S01144، S01157؛ لم تعوض الصوامت المنطوقة الساقطة.",
        "- فجوات القانون: S01113، S01129، S01132، S01145، S01146، S01163، S01164، S01178.",
        "- اسم العلم المعزول: S01165 Canopus؛ حفظ في التغطية ولم يحسب أثرا.",
        "- خبر `دله` إلى العربية `دلق` حفظ في S01134، لكن القاف التاريخية خارج الهيكل الحديث ومروحته؛ لم يصدر حكم من مسار غير حي.",
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
    headings = re.findall(r"^### (WO-B-R40-SOUND-\d{5}):", match.group(1), re.MULTILINE)
    expected = [f"WO-B-R40-SOUND-{rank:05d}" for rank in SOUND_RANKS]
    if headings != expected:
        raise AssertionError("مقطع الجولة 40 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(DONE_LINE):
        raise AssertionError("سطر DONE40 ليس خاتمة التقرير")


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
        print("ROUND40 ALREADY PRESENT AND VALID")
        print(DONE_LINE)
        return 0

    R39.validate_nucleus_snapshot()
    data = json.loads(SWEEP.read_text(encoding="utf-8"))
    selected, stats = select_rows(data, reading_text)
    prior_pairs = H.read_pairs(reading_text)
    lexicon = json.loads(LEXICON.read_text(encoding="utf-8"))

    entries, grouped = select_branch_entries(selected, lexicon)
    R35.EXPECTED_RAW_LINE = EXPECTED_RAW_LINE
    raw_entries = R35.load_raw_entries(selected, entries)
    validate_components(grouped)

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
        "## الجولة الأربعون: متابعة حوض sound_only (2026-08-27)\n\n"
        "- النطاق: 70 عضوا طازجا بعد WO-B-R39-SOUND-01107؛ من الرتبة 1109 إلى 1182 مع تجاوز 1108 و1118 و1123 و1149 و1155 لأنها مقروءة؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ طريق المعنى مسمى، والمدار اليدوي حاسم، والأصداء مفصولة عن الأثر المحكم.\n"
        "- لقطة الأحواض: قرئت ملفات nucleus-sweep-*.json التسعة الحالية v18 من القرص؛ ثبتت بصماتها وعداداتها قبل الانتخاب.\n\n"
        + "\n".join(texts[:35])
        + "\n## الدفعة الثانية: متابعة sound_only بعد الرتبة 1145\n\n"
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
    print("ROUND40 READY")
    print("NUCLEUS_V18_FILES", len(R39.NUCLEUS_SNAPSHOT), "SHA256_AND_COUNTS_OK")
    print("NUCLEUS_V18_TOTALS", "BOTH=14496", "SOUND_ONLY=106818")
    print("SKIPPED", ",".join(map(str, stats["skipped"])))
    print("BATCHES", *BATCH_SIZES, "SELECTED", len(selected))
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("ECHOES", " ".join(f"S{rank:05d}" for rank in sorted(rank for rank, review in REVIEWS.items() if review.verdict == "ROOT-ECHO")))
    print("TRANSMISSIONS", " ".join(f"S{rank:05d}" for rank in sorted(rank for rank, review in REVIEWS.items() if review.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC")))
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
    print("ROUND40 WRITTEN")
    print(DONE_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
