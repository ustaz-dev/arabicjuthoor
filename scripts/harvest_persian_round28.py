# -*- coding: utf-8 -*-
"""المسار B، الجولة 28: متابعة حوض sound_only في دفعتين من 35 بطاقة."""

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

import harvest_persian_round27 as R27  # noqa: E402

H = R27.H
P = R27.P
P25 = R27.P25
READING = ROOT / "04-cross-linguistic" / "readings" / "persian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-B.md"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-persian.json"
NUCLEUS_DIR = ROOT / "04-cross-linguistic" / "exploration"
LEXICON = ROOT / "data" / "branch-lexicons" / "persian.json"
RAW_LEXICON = ROOT / "Resources" / "persian" / "kaikki.org-dictionary-Persian.jsonl"
MARKER = "LANE-B-PERSIAN-ROUND28-2026-08-26"
CARD_LIMIT = 5120
SKIPPED_RANKS = {179, 181, 219, 232}
SOUND_RANKS = tuple(rank for rank in range(178, 252) if rank not in SKIPPED_RANKS)
BATCH_SIZES = (35, 35)
DONE_LINE = "LANE-B DONE28 70 WO-B-R28-SOUND-00251"
EXPECTED_SKIPS = (177, 179, 181, 219, 232)
EXACT_DECOMPOSITIONS = {200, 201, 202, 208, 213, 235, 245, 246, 247}

NUCLEUS_SNAPSHOT = {
    "nucleus-sweep-ancient_greek.json": (7479302, "96a492a1ab2a2ee64e17542fd1929b75d74b3be63a0b9c1772d552ff8cd80420"),
    "nucleus-sweep-english_middle.json": (3486542, "19debf148f966f63be107a95d54db40565e16ae1685bcca559d586535e5aff54"),
    "nucleus-sweep-english_old.json": (1334553, "db547705af4156c2f5ab598bb774e1135aae5be6cab6818b67e9abbb22a52da2"),
    "nucleus-sweep-gothic.json": (1415736, "5ed62f330d87fb1a832b296e943329fbf249e45760695b4eaac8c609de8e307f"),
    "nucleus-sweep-latin.json": (18179381, "de5ec160bb33e32f2cc3d9a02f171fb0ba1177a22cba3a8696e0f7607076f986"),
    "nucleus-sweep-old_irish.json": (956826, "cbe9d91ead4a4027399178992460fefe42288cf1a489f14a42fac3658d209b3a"),
    "nucleus-sweep-old_norse.json": (1393717, "ed7b25614d109bdd4e091021c3d790fc0727624ec1e6fe7ccf8c929888479fe5"),
    "nucleus-sweep-persian.json": (5473313, "2a9cfd8ac0c6e272d4950cc8136f2636b87b421bd099673a9740cd46b68aa7ff"),
    "nucleus-sweep-welsh.json": (5825087, "6ae026040eb02099b31125bb354ba33d6c4c262c8d9da100c59e0776ae4ba4a2"),
}

BLOCKED_BOUNDARIES = {
    190: "يكتب Kaikki `نارنگ` + `ـی` بلا صيغة From X + Y النهائية المباشرة التي ألزم بها الرتل.",
    191: "يكرر Kaikki `نارنگ` + `ـی` في مدخلة الثمرة بلا صيغة From X + Y النهائية المباشرة.",
    214: "يقول الخبر Equivalent to `دان` + `ـا` بعد سلسلة تاريخية، لا From X + Y النهائي المباشر.",
    215: "مدخلة الاسم تكرر Equivalent to `دان` + `ـا`، فلم يحول Equivalent إلى From.",
    228: "يسمي الخبر مركبا فارسيا أوسط من عنصرين تاريخيين، ولا يعطي تفكيك From X + Y لمدخلة الفرع الحالية.",
}

TOOL_GAPS = {
    183: "الصورة `کوه` منقوطة /kōh/، لكن صف الحوض أعطاها الهيكل `کـو` وأسقط الهاء النهائية المنطوقة.",
    199: "الصورة `گهگاه` منقوطة /gahgâh/، لكن الهيكل `گـهـگ` أسقط الهاء النهائية المنطوقة.",
    243: "الصورة `نانوا` منقوطة /nānwā/، لكن الهيكل `نـن` أسقط الواو المنطوقة /w/ من اسم الصانع.",
}

OUT_OF_SCOPE = {
    229: "المدخلة اسم شهر January من الفرنسية، وطبقة أسماء الشهور معزولة عن الحكم المعجمي الجذري.",
    234: "المدخلة اسم شهر June من الفرنسية، وطبقة أسماء الشهور معزولة عن الحكم المعجمي الجذري.",
}

EXPECTED_ENTRY_INDEX = dict(zip(SOUND_RANKS, (
    813, 816, 818, 825, 827, 828, 829, 832, 833, 838,
    839, 840, 843, 845, 847, 853, 861, 865, 868, 870,
    871, 872, 873, 874, 875, 888, 892, 895, 896, 899,
    907, 912, 915, 920, 926, 927, 932, 935, 936, 939,
    950, 959, 960, 961, 963, 967, 970, 972, 974, 978,
    980, 982, 983, 995, 996, 997, 998, 999, 1001, 1003,
    1004, 1013, 1020, 1028, 1029, 1030, 1033, 1036, 1044, 1045,
)))

EXPECTED_RAW_LINE = dict(zip(SOUND_RANKS, (
    865, 870, 872, 880, 882, 884, 886, 889, 890, 895,
    896, 897, 900, 902, 904, 910, 918, 922, 925, 927,
    928, 929, 930, 931, 932, 946, 950, 953, 954, 957,
    965, 970, 973, 978, 984, 985, 990, 993, 994, 997,
    1009, 1018, 1019, 1020, 1022, 1026, 1030, 1032, 1035, 1040,
    1042, 1044, 1046, 1059, 1060, 1061, 1062, 1063, 1065, 1067,
    1068, 1077, 1084, 1092, 1093, 1094, 1097, 1102, 1110, 1111,
)))

EXPECTED_COMPONENTS = {
    200: ("گرد", "ـو"),
    201: ("گل", "ـدان"),
    202: ("صورت", "ـی"),
    208: ("دوسْت", "ـی"),
    213: ("پر", "ـنده"),
    235: ("هزار", "پا"),
    245: ("ژاپن", "ـی"),
    246: ("ژاپن", "ـی"),
    247: ("ژاپن", "ـی"),
}

COMPONENT_READINGS = {
    200: "`گرد`: اختيرت entries[6216] لمعنى round والسطر الخام 7293، ومروحتها 24: OPEN-CANDIDATE. `ـو`: غائبة من branch-lexicons ومن الخام، ومروحتها صفر: MORPHOLOGY-GAP.",
    201: "`گل`: اختيرت entries[365] لمعنى flower والسطر الخام 394، ومروحتها 80: OPEN-CANDIDATE. `ـدان`: entries[7278] والسطر 8539 لاحقة holder أو container، ومروحتها 30: MORPHOLOGY-GAP.",
    202: "`صورت`: entries[1338] والسطر 1419 لمعنى face، وخبرها يصرح بالقرض من العربية: SEMITIC-SOURCE-TRANSMISSION للمكون. `ـی`: entries[6328] والسطر 7421، ومروحتها صفر: MORPHOLOGY-GAP.",
    208: "`دوست`: مرجع WO-B-R26-SOUND-00100، entries[540] والسطر 582 لمعنى friend، ومروحتها 27: OPEN-CANDIDATE. `ـی`: entries[6329] للاسم المجرد، ومروحتها صفر: MORPHOLOGY-GAP.",
    213: "`پر`: السطر الخام 336 يسميه present stem of `پریدن`، لكن branch-lexicons لا يصدر هذا الحس بين entries[316,317]؛ مروحة الرسم 40 وسمت COMPONENT-GAP. `ـنده`: entries[10300] والسطر 12672 لاحقة اسم فاعل، ومروحتها 30: MORPHOLOGY-GAP.",
    235: "`هزار`: entries[1407] والسطر 1489 لمعنى thousand، ومروحتها 12: OPEN-CANDIDATE. `پا`: اختيرت entries[156] والسطر 162 لمعنى foot، ومروحتها 36 ومرجعها السابق OPEN-CANDIDATE.",
    245: "`ژاپن`: entries[956] والسطر 1015 اسم علم لليابان، ومروحته 6: OUT-OF-SCOPE. `ـی`: entries[6328] والسطر 7421 لاحقة نسبة، ومروحتها صفر: MORPHOLOGY-GAP.",
    246: "مرجع المكونين في S00245: `ژاپن` OUT-OF-SCOPE و`ـی` MORPHOLOGY-GAP؛ لم ترث مدخلة الشخص حكما.",
    247: "مرجع المكونين في S00245: `ژاپن` OUT-OF-SCOPE و`ـی` MORPHOLOGY-GAP؛ لم ترث مدخلة اللغة حكما.",
}


@dataclass(frozen=True)
class SelectedRow:
    row: H.SweepRow

    @property
    def key(self) -> str:
        return f"S{self.row.rank:05d}"

    @property
    def heading(self) -> str:
        return f"WO-B-R28-SOUND-{self.row.rank:05d}"


@dataclass(frozen=True)
class Review:
    candidate: str
    verdict: str
    meaning_path: str
    orbit: str


def R(candidate: str, verdict: str, meaning_path: str, orbit: str) -> Review:
    return Review(candidate, verdict, meaning_path, orbit)


# سجل قراءة يدوي. الحكم لا يشتق من عمود best ولا من وزن المروحة.
REVIEWS = {
    178: R("دو", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دو`: محكمتا الدال والواو بلا معنى عددي.", "العدد two لا يستخرج من رصف الحرفين؛ فصلت المطابقة الصوتية عن معنى العدد."),
    180: R("يك", "LOANWORD-NON-ARABIC-TO-ARABIC", "جسر المعنى: شاهد المحكم يقول `يك` بالفارسية واحد، والمحيط يذكر استعمال العرب له كما تقوله الفرس.", "اتحد معنى one والصورة، لكن الشاهدين سميا الفارسية واتجاه الدخول؛ أغلق تماس لا إرثا."),
    182: R("سه", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سه`: الفراغ المتخلل، والشواهد العربية في الاست لا العدد.", "فصلت three عن متجانس عربي مختلف المعنى؛ لا يحول تعداد الأشياء إلى فراغ متخلل."),
    183: R("كو", "TOOL-GAP", "جسر المعنى: mountain حاضر، لكن الهيكل أسقط هاء /kōh/ قبل بناء المروحة.", "توقفت المقارنة قبل انتخاب جذر؛ لا تعويض لصامت منطوق من الرسم أو الأصل."),
    184: R("بد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بد`: الفراغ الممتد وبروز الشيء أول مرة؛ لا يسمي poorly أو badly.", "شواهد البد في المعبد واللزوم لا في رداءة الأداء؛ فصلت متجانسين."),
    185: R("بد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بد`: الفراغ والبروز؛ لا يسمي wind أو air.", "حركة الهواء في الفراغ وصف عام لا معنى الريح نفسها، فلا يقوم المدار من الحيز."),
    186: R("مرك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مرك`: الاسترسال والحركة مع حدث الكاف؛ لا يسمي death.", "توقف الحركة أثر للموت لا معنى الموت في المادة؛ وفصلت الأصل الهندي الأوروبي عن الحكم."),
    187: R("تا", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تا`: محكمتا التاء والألف؛ لا تسمي حد الغاية until أو up to.", "الإشارة العربية المؤنثة في الشواهد لا تورث وظيفة حرف الجر الفارسي."),
    188: R("تا", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تا`: محاكم حروف بلا معنى as long as أو when.", "فصلت مدخلة الرابط عن حرف الجر السابق وعن الإشارة العربية؛ الوظائف ليست معنى واحدا."),
    189: R("بغغ", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بغغ`: تزايد وفوران داخلي؛ لا يسمي garden أو orchard.", "نمو النبات داخل الحديقة حدث يقع في محتواها ولا يسمي المكان أو البستان."),
    190: R("نلنج", "COMPOUND-BOUNDARY", "جسر المعنى: الخبر يربط orange-colored بـ`نارنگ` واللاحقة، لكن بلا From X + Y مؤهل.", "وقف اللون عند حد التحليل غير المؤهل؛ لم يرث صورة الثمرة ولا اللاحقة."),
    191: R("نلنج", "COMPOUND-BOUNDARY", "جسر المعنى: خبر mandarin يكرر `نارنگ` واللاحقة بلا From X + Y النهائي المباشر.", "فصلت اسم الثمرة عن صفة اللون السابقة، ورفضت تفكيكا لا يطابق معيار الرتل."),
    192: R("بهر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بهر`: الخلو والفراغ الظاهري؛ لا يسمي spring أو blossom.", "انفتاح الزهر في الربيع وصف موسمي لا يجعل الفراغ معنى الفصل أو الزهرة."),
    193: R("ستر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ستر`: تغطية الشيء ما وراءه؛ لا يسمي star أو fate.", "ظهور النجم مقابل الستر لا تطابق معه، والقدر معنى متجانس داخل المدخلة لا جسر له."),
    194: R("از", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`از`: محكمتا الألف والزاي؛ لا تسمي of أو from أو since.", "الوظيفة النحوية لا تستخرج من حركة الحرفين، ولا شاهد عربي مستقل لها."),
    195: R("اسب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`اسب`: محاكم حروف بلا حدث معجمي موحد؛ لا يسمي horse.", "الفروسية أو حركة الحيوان ليست معنى المادة المختارة؛ بقي الحيوان خارج المدار."),
    196: R("رغل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رغل`: تخلل بمائع كثيف مع حدث اللام؛ لا يسمي skinny أو thin.", "نقص اللحم نتيجة محتملة لا معنى الحدث، ولا شاهد عربي كلاسيكي للصفة الدقيقة."),
    197: R("مش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مش`: النفاذ بانتشار من أثناء الشيء؛ لا يسمي mouse أو rat.", "حركة الفأر في الشقوق فعل للحيوان لا اسمه، ومعنى cutie متجانس فارسي ثانوي."),
    198: R("خك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خك`: محكمتا الخاء والكاف بلا معنى pig.", "صوت الحيوان أو حركته لا يثبتان اسم النوع، ولم يرد شاهد عربي كلاسيكي للمرشح."),
    199: R("كهك", "TOOL-GAP", "جسر المعنى: sometimes حاضر، لكن الهيكل أسقط هاء /gahgâh/ النهائية.", "لا تقارن الصورة المكررة بهيكل ناقص؛ أوقف عطب الأداة الحكم قبل المدار."),
    200: R("جرد", "MORPHOLOGY-GAP", "جسر المعنى: Kaikki يفكك walnut إلى `گرد` round و`ـو` تفكيكا مباشرا.", "قُرئ `گرد`، لكن `ـو` غابت من لقطة الفرع والخام؛ سميت فجوة الصرف ولم تقارن الصورة وحدة."),
    201: R("كلدن", "COMPOUND-BOUNDARY", "جسر المعنى: flowerpot هو `گل` flower مع `ـدان` holder في تفكيك مباشر.", "قُرئ المكونان، ومنع حد المركب توريث حكم flower أو holder إلى الكلمة المجموعة."),
    202: R("سرت", "COMPOUND-BOUNDARY", "جسر المعنى: pink مبني من `صورت` face واللاحقة في سطر From X + Y مباشر.", "ثبت نقل `صورت` من العربية للمكون وحده؛ لم يرث اللون أو الصفة facial حكمه."),
    203: R("ابر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ابر`: محاكم حروف بلا حدث cloud أو sponge.", "فصلت cloud عن branch of miniature وعن sponge؛ لا يربطها مدار معجمي واحد بالعربية."),
    204: R("ابر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ابر`: لا يسمي السابقة super- أو over-.", "العلو وظيفة صرفية في المدخلة، لا معنى لمادة عربية مسماة في الشواهد."),
    205: R("جرب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جرب`: الاسترسال والامتداد، وشواهده العربية في الجرب لا cat.", "مرض جلد الحيوان عرض لا اسم نوع القط؛ فصلت الحيوان عن الحالة المرضية."),
    206: R("بدن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بدن`: كتلة جسم الحي؛ لا يسمي to exist أو to be.", "كون الموجود ذا بدن لا يجعل الجسم معنى الوجود، ولا يشمل الموجودات بلا أجسام."),
    207: R("رب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رب`: الاستغلاظ والتربية أو الجمع؛ لا يسمي rap music.", "الإيقاع أو الأداء الصوتي ليس تربية ولا تملكا؛ بقي القرض الحديث بلا مدار."),
    208: R("دست", "COMPOUND-BOUNDARY", "جسر المعنى: friendship مفككة مباشرة إلى `دوست` friend و`ـی` للاسم المجرد.", "مرجع `دوست` السابق مفتوح واللاحقة صرفية؛ لم تورث الصورة المجموعة حكما."),
    209: R("جس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جس`: الاختراق الحسي أو المعنوي؛ لا يسمي ear.", "الأذن أداة حس، لكن وظيفة العضو لا تسمي العضو نفسه ولا تميزه عن العين والجلد."),
    210: R("رشذن", "LAW-GAP", "نص الحدث المجمد لـ`رشذن`: نزول إلى نواة قلة مفارقة المنشأ؛ لا يسمي to lick.", "المعنى غائب، ومسار الدال إلى الذال غير مسمى؛ لم ينزع مصدر الفعل حدسا."),
    211: R("رد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رد`: صد المسترسل وإرجاعه؛ لا يسمي river أو torrent.", "رجوع الماء عند عائق حالة محتملة للنهر لا معنى مجرى الماء نفسه."),
    212: R("حردن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`حردن`: نزول إلى التخلخل مع حدثي الدال والنون؛ لا يسمي to eat أو drink.", "الأكل يغير المادة لكنه لا يساوي التخلخل، ولا يجوز نزع `دن` بلا تفكيك منشور."),
    213: R("برند", "COMPOUND-BOUNDARY", "جسر المعنى: bird مفككة إلى present stem of fly و`ـنده` agentive suffix.", "قُرئ السطر الخام للجذع واللاحقة، وبقي حس الجذع غائبا من branch-lexicons؛ لم يرث المركب."),
    214: R("دن", "COMPOUND-BOUNDARY", "جسر المعنى: wise يرد إلى فعل know وتحليل Equivalent to، لا From X + Y المؤهل.", "وقف الحكم قبل المكونين؛ لم تحول المعرفة إلى وعاء `دن` ولا قبلت Equivalent بديلا من From."),
    215: R("دن", "COMPOUND-BOUNDARY", "جسر المعنى: مدخلة الاسم wise تكرر التحليل غير المؤهل نفسه.", "فصلت الاسم عن الصفة السابقة، ولم أورث أحد المتجانسين قرار الآخر."),
    216: R("جهر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جهر`: ظهور الشيء وانكشافه؛ لا يسمي jewel أو pearl أو essence.", "لمعان الجوهرة صفة بصرية لا اسم المادة، ويصدق الظهور على أشياء لا تحصى."),
    217: R("ترك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ترك`: مفارقة الشيء وتركه؛ لا يسمي dark أو dim.", "غياب الضوء قد يترك المكان مظلما، لكنه سبب محتمل لا معنى الظلمة أو الصفة."),
    218: R("مد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مد`: الامتداد والغاية؛ لا يسمي female.", "امتداد النسل وظيفة للكائن من الجنسين ولا يحدد الأنثى؛ لا مدار جنسي مباشر."),
    220: R("بل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بل`: التمكن والحوز بشدة؛ لا يسمي money أو coin.", "المال مما يحاز، لكن علاقة الملك بالمملوك لا تسمي النقد ولا تميزه عن سائر الممتلكات."),
    221: R("خب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خب`: تخلخل الباطن المتجمع؛ لا يسمي well أو nicely.", "حسن الأداء لا يستخرج من التخلخل، وفصلت الظرف عن مدخلة الصفة المتجانسة."),
    222: R("اسن", "LAW-GAP", "نص الحدث المجمد لـ`اسن`: محاكم حروف بلا معنى easy، وآ↔ا غير مسمى.", "سهولة الشيء لا تسوغ تسوية الهمزة الممدودة، فبقي الصوت والمعنى غير مكتملين."),
    223: R("زر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زر`: النفاذ بدقة مع إمساك؛ لا يسمي gold.", "لون الذهب أو سبكه فعل وصفة للمعدن لا معنى المعدن، وشواهد الزر في الشل والطرد."),
    224: R("زر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زر`: النفاذ والإمساك؛ لا يسمي rotation أو revolution.", "الدفع قد يسبب الدوران لكنه ليس الحركة الدائرية نفسها؛ فصلت متجانس الحركة عن الذهب."),
    225: R("تخم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تخم`: محاكم حروف، وشواهده العربية في حدود الأرض لا seed أو semen.", "فصلت الحد المكاني العربي عن البذرة والمادة التناسلية الفارسية رغم اتحاد الرسم."),
    226: R("شب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شب`: تجمع عن انتشار أو ضعف؛ لا يسمي night أو evening.", "اجتماع الظلمة وصف للزمن لا معنى الليل، وشواهد العربية في الشباب والنمو."),
    227: R("در", "NUCLEUS-TRACE", "جسر المعنى: river وtorrent جريان مسترسل، والحدث المجمد لـ`در` هو الجريان أو الامتداد بتوال.", "مدار 1: النهر ماء يجري باسترسال، وشاهدا در اللبن ودر السماء يثبتان الجريان والكثرة مباشرة."),
    228: R("برن", "COMPOUND-BOUNDARY", "جسر المعنى: خبر rain يسمي مركبا فارسيا أوسط، لا تفكيك From X + Y للمدخلة الحالية.", "لم أنقل عناصر تاريخية غير مصدرة إلى مكونات حديثة، ووقف الحكم عند الحد."),
    229: R("زن", "OUT-OF-SCOPE", "جسر المعنى: January اسم شهر مقترض من الفرنسية لا معنى معجميا إلى `زن`.", "عزلت اسم الشهر؛ لم أحول ترتيب التقويم أو برد الشتاء إلى حدث جذري."),
    230: R("مه", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مه`: الفراغ والرقة والسهولة؛ لا يسمي fog أو mist.", "رقة الضباب أو فراغ الرؤية وصف له لا اسم الظاهرة، والشواهد العربية في الزجر."),
    231: R("مه", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مه`: الفراغ والرقة؛ لا يسمي big أو great.", "الكبر لا يساوي الفراغ ولا الزجر؛ فصلت الصفة عن متجانس الضباب السابق."),
    233: R("مه", "ROOT-ECHO", "جسر المعنى: prohibitive particle تطابق `مَهْ` العربية، وشاهدان يسميانها زجرا ونهيا.", "مدار الوظيفة المعجمية مباشر، لكن الحدث المجمد للرقة والفراغ لا يحمل النهي؛ أغلق ROOT-ECHO لا أثرا محكما."),
    234: R("زن", "OUT-OF-SCOPE", "جسر المعنى: June اسم شهر مقترض من الفرنسية لا معنى معجميا إلى `زن`.", "عزلت اسم الشهر عن المدخلة السابقة وعن مواد الزاي والنون؛ لا حكم جذري للأعلام."),
    235: R("هزرب", "COMPOUND-BOUNDARY", "جسر المعنى: millipede مفككة مباشرة إلى `هزار` thousand و`پا` foot.", "قُرئ المكونان استقلالا؛ لم يحول اسم الحيوان المركب إلى جذر واحد ولا إلى قرينة عدد."),
    236: R("طوط", "OPEN-CANDIDATE", "جسر المعنى: الأصل يقارن العربية `طوطق` و`طوطك` بوصفهما اقتراضين إيرانيين، لكن المروحة لا تحمل القاف أو الكاف.", "شواهد `طوط` العربية في القطن والحية والطول لا parrot؛ لم أسقط صامت صورتي القرض لإنقاذ النقل."),
    237: R("زذن", "LAW-GAP", "نص الحدث المجمد لـ`زذن`: إضافة شيء إلى الحيز؛ لا يسمي beat أو hit، ود↔ذ غير مسمى.", "فوق غياب معنى الضرب بقي رصف الصوت ناقصا؛ لم ينزع `ن` مصدرا بلا تصريح."),
    238: R("وج", "LAW-GAP", "نص الحدث المجمد لـ`وج`: محاكم حروف لا تسمي word أو term، وژ↔ج غير مسمى.", "الكلام صوت خارج من الفم لكنه وصف إنتاج عام، ومسار الصامت الثاني ناقص."),
    239: R("جس", "LAW-GAP", "نص الحدث المجمد لـ`جس`: الاختراق الحسي؛ لا يسمي silent fart أو fizzle، وچ↔ج غير مسمى.", "الخفاء السمعي لا يساوي الجس، وفجوة القانون تمنع الحكم الصوتي أيضا."),
    240: R("شدن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شدن`: صلابة الشيء ووثاقته مع حدث النون؛ لا يسمي become أو be بإطلاق.", "شدن الصبي في الشاهد نمو مخصوص، ولا يساوي فعل التحول العام في مئات المركبات."),
    241: R("طلخ", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`طلخ`: التكديس والاتباع مع حدث الخاء؛ لا يسمي bitter.", "تراكم الطعم أو شدته تفسير حسي عام لا معنى المرارة، ولا شاهد عربي دقيق للصفة."),
    242: R("زخم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زخم`: اندفاع الشيء بقوة؛ وشواهده العربية في الرائحة والدفع لا wound.", "فصلت الجرح الفارسي عن الزخمة العربية؛ الألم أو الرائحة آثار ممكنة لا معنى المدخلة."),
    243: R("نون", "TOOL-GAP", "جسر المعنى: baker مفهوم من الصورة، لكن الحوض أسقط /w/ المنطوقة في /nānwā/.", "لم أقبل الهيكل `نـن` ممثلا لاسم الصانع، ووقفت قبل تحليل الخبز أو اللاحقة."),
    244: R("كشر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كشر`: خروج المتغلغل أو كشف الأسنان؛ لا يسمي country أو realm.", "حد الأرض المحروث في خبر الأصل تفسير تاريخي داخل الفرع، لا معنى الكشر العربي."),
    245: R("زبن", "COMPOUND-BOUNDARY", "جسر المعنى: Japanese الصفة مفككة إلى اسم العلم `ژاپن` واللاحقة النسبية.", "عزل اسم العلم وسمت اللاحقة صرفية؛ لم يصدر حكم للصورة المجموعة."),
    246: R("زبن", "COMPOUND-BOUNDARY", "جسر المعنى: Japanese الشخص يكرر `ژاپن` + `ـی` في تفكيك مباشر.", "فصلت مدخلة الشخص عن الصفة، ولم تورثها حكم المكون أو المتجانس."),
    247: R("زبن", "COMPOUND-BOUNDARY", "جسر المعنى: Japanese اللغة تكرر `ژاپن` + `ـی` في تفكيك مباشر.", "فصلت مدخلة اللغة عن الشخص والصفة، وبقي اسم العلم خارج الحكم."),
    248: R("در", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`در`: الجريان أو الامتداد؛ لا يسمي at أو in أو inside.", "كون الشيء جاريا داخل حيز مثال سياقي لا وظيفة حرف الجر؛ فصلت الأداة عن نهر S00227."),
    249: R("قفتن", "LAW-GAP", "نص الحدث المجمد لـ`قفتن`: الجفاف والتباعد مع أحداث الباقي؛ لا يسمي say أو tell، وگ↔ق غير مسمى.", "لم ينزع `تن` مصدرا بلا تحليل، ومسار أول الصامتات ناقص فوق غياب المعنى."),
    250: R("ده", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ده`: الحدر أو الدفع في فراغ؛ لا يسمي ten.", "الشواهد العربية في كلمة حث على الثأر لا العدد؛ فصلت الوظيفة والعدد."),
    251: R("ده", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ده`: الحدر أو الدفع؛ لا يسمي village.", "فصلت القرية عن متجانس العدد السابق وعن كلمة الحث العربية؛ لا مدار للمكان."),
}


def pair_key(row: H.SweepRow) -> tuple[str, str]:
    return row.branch, H.norm_gloss(row.gloss)


def validate_nucleus_snapshot() -> None:
    actual_names = {path.name for path in NUCLEUS_DIR.glob("nucleus-sweep-*.json")}
    if actual_names != set(NUCLEUS_SNAPSHOT):
        raise AssertionError(f"تغير جرد أحواض النواة الحالية: {sorted(actual_names)}")
    for name, (expected_size, expected_hash) in NUCLEUS_SNAPSHOT.items():
        raw = (NUCLEUS_DIR / name).read_bytes()
        if len(raw) != expected_size or hashlib.sha256(raw).hexdigest() != expected_hash:
            raise AssertionError(f"تغيرت نسخة القرص الحالية للحوض {name}")
        data = json.loads(raw)
        if data.get("language") != name.removeprefix("nucleus-sweep-").removesuffix(".json"):
            raise AssertionError(f"تغير وسم اللغة في {name}")


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
            if row.rank > 176 and len(fresh) < 70:
                internal_skips.append(row.rank)
            continue
        seen.add(key)
        if row.rank <= 176:
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


def select_branch_entries(selected: list[SelectedRow], lexicon: dict) -> tuple[dict[int, H.BranchEntry], dict[str, list[tuple[int, dict]]]]:
    grouped: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for index, entry in enumerate(lexicon["entries"]):
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


def load_raw_entries(selected: list[SelectedRow], entries: dict[int, H.BranchEntry]) -> dict[int, dict]:
    wanted = {item.row.branch for item in selected}
    grouped: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    with RAW_LEXICON.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            raw = json.loads(line)
            word = H.clean(raw.get("word") or "")
            if word in wanted:
                grouped[word].append((line_number, raw))
    output: dict[int, dict] = {}
    for item in selected:
        row = item.row
        entry = entries[row.rank]
        options = grouped.get(row.branch, [])
        same_pos = [pair for pair in options if H.clean(pair[1].get("pos") or "") == entry.pos]
        line_number, raw = max(
            same_pos or options,
            key=lambda pair: H.entry_score(H.norm_gloss(entry.gloss), {"en": P25.raw_gloss(pair[1])}),
        )
        if line_number != EXPECTED_RAW_LINE[row.rank]:
            raise AssertionError(f"انزلق سطر Kaikki للرتبة {row.rank}: {line_number}")
        output[row.rank] = {
            "line": line_number,
            "entry": raw,
            "gloss": P25.raw_gloss(raw),
            "etymology": H.clean(raw.get("etymology_text") or ""),
        }
    return output


def validate_components(grouped: dict[str, list[tuple[int, dict]]]) -> None:
    expected_indices = {
        "گرد": {6216, 6217, 6218}, "ـو": set(), "گل": {365, 366, 367, 368, 369},
        "ـدان": {7278}, "صورت": {1338}, "ـی": {6327, 6328, 6329, 6330},
        "دوست": {540}, "پر": {316, 317}, "ـنده": {10300}, "هزار": {1407},
        "پا": {156, 157}, "ژاپن": {956},
    }
    fan_counts = {
        "گرد": 24, "ـو": 0, "گل": 80, "ـدان": 30, "صورت": 12, "ـی": 0,
        "دوست": 27, "پر": 40, "ـنده": 30, "هزار": 12, "پا": 36, "ژاپن": 6,
    }
    for word, expected in expected_indices.items():
        actual = {index for index, _entry in grouped.get(word, [])}
        if actual != expected:
            raise AssertionError(f"تغير جرد مكون {word}: {sorted(actual)}")
        fan = tuple(H.FAN.rank(word, H.FAN.fan(word, "persian"), "persian"))
        if len(fan) != fan_counts[word]:
            raise AssertionError(f"تغيرت مروحة المكون {word}: {len(fan)}")
    expected_raw = {
        "گرد": {7293, 7294, 7295, 7296}, "ـو": set(), "گل": {394, 395, 396, 397, 398},
        "ـدان": {8539}, "صورت": {1419}, "ـی": {7420, 7421, 7422, 7423, 7424},
        "دوست": {582}, "پر": {334, 335, 336}, "ـنده": {12672}, "هزار": {1489},
        "پا": {162, 163}, "ژاپن": {1015},
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
        return "اكتملت أرجل الصوت والحدث والمدار اليدوي، ومعها شاهدان عربيان كلاسيكيان مستقلان."
    if review.verdict == "ROOT-ECHO":
        return "اكتمل الصوت والشاهدان، لكن الحدث المجمد ألين من التطابق المعجمي؛ أغلق على درجة الصدى."
    if review.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC":
        return "اكتملت الصورة والمعنى والشواهد، لكنها سمت اتجاه الدخول من الفارسية إلى العربية؛ أغلق تماس لا إرثا."
    if review.verdict == "LAW-GAP":
        return "طريق المعنى مفحوص، لكن مسار الصوت يحوي صفا غير مسمى؛ لم يصدر حكم موجب."
    if review.verdict == "COMPOUND-BOUNDARY":
        return "وقف الحكم عند حد المركب؛ لم تورث الصورة المجموعة حكم مكون ولم يخترع تفكيك."
    if review.verdict == "MORPHOLOGY-GAP":
        return "ثبت التفكيك، لكن مكونا صرفيا غاب من اللقطة؛ لم يسو من الحدس."
    if review.verdict == "TOOL-GAP":
        return "صف الحوض أسقط صامتا منطوقا؛ توقف العضو قبل الحكم ولم يعوض الصامت يدويا."
    if review.verdict == "OUT-OF-SCOPE":
        return "الشرح اسم شهر لا معنى معجميا عاما؛ أحيل العضو إلى طبقة الأعلام المنفصلة."
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
    return [
        f"- تفكيك Kaikki الحصري من السطر الخام {raw['line']}: «{H.clip(raw['etymology'], 420)}».",
        f"- قراءة المكونات المستقلة: {COMPONENT_READINGS[rank]}",
        "- الخطوة صفر: قبل التفكيك الحرفي From X + Y لم تقارن الصورة وحدة جذرية؛ قُرئ كل مكون وحده.",
    ]


def make_card(
    item: SelectedRow,
    entry: H.BranchEntry,
    raw: dict,
    decision: H.Decision,
    ranked: tuple[tuple[str, float], ...],
    sense_map: dict[str, list[dict]],
    quote_limit: int,
    etym_limit: int,
) -> str:
    row = item.row
    review = REVIEWS[row.rank]
    match_count, classical_count, witnesses = P.classical_witnesses(decision.candidate, sense_map, quote_limit)
    etymology = raw["etymology"] or entry.etymology or "فجوة اشتقاق في مدخلة Kaikki الخام."
    lines = [
        f"### {item.heading}: `{row.branch}` /{entry.reading}/، رتبة sound_only {row.rank}",
        "- إصدار البروتوكول: RECOVERY-v2 (2026-08-16)؛ نموذج WO-B-PROBE-001.",
        f"- مرجع الحوض: `phonetic-sweep-persian.json:sound_only[{row.rank - 1}]`؛ overlap=0؛ shared=فارغ؛ الترتيب مدخل قراءة لا حكم.",
        f"- الكلمة في الفرع: فارسية `{row.branch}` /{entry.reading}/؛ الصنف `{entry.pos}`.",
        f"- قراءة مداخل الرسم المتجانس: قُرئت {entry.homograph_count} مدخلة للرسم `{row.branch}`؛ المختارة {entry.homograph_index}، entries[{entry.global_index}]؛ لم تؤخذ الأولى آليا.",
        f"- أقدم صورة مستعادة: «{H.clip(etymology, etym_limit)}» [Kaikki؛ السطر الخام {raw['line']}].",
    ]
    exact = decomposition_lines(item, raw)
    if exact:
        lines.extend(exact)
    elif row.rank in BLOCKED_BOUNDARIES:
        lines.extend([
            f"- حد المركب غير المفكك: {BLOCKED_BOUNDARIES[row.rank]}",
            "- الخطوة صفر: لم يقبل إلا From X + Y النهائي المباشر؛ وقف الحكم COMPOUND-BOUNDARY بلا مكونات مخترعة.",
        ])
    elif row.rank in TOOL_GAPS:
        lines.extend([
            f"- عطب الهيكل: {TOOL_GAPS[row.rank]}",
            "- الخطوة صفر: أوقف TOOL-GAP المقارنة قبل إسقاط الصوائت أو انتخاب جذر؛ لا حكم من هيكل ناقص.",
        ])
    elif row.rank in OUT_OF_SCOPE:
        lines.extend([
            f"- عزل طبقة العلم: {OUT_OF_SCOPE[row.rank]}",
            f"- الخطوة صفر: سجل الهيكل `{'ـ'.join(row.skeleton)}` للفهرسة فقط، ولم يحول اسم الشهر إلى معنى جذري.",
        ])
    else:
        lines.append(f"- الخطوة صفر: الهيكل `{'ـ'.join(row.skeleton)}`، صوامته {len(row.skeleton)}؛ طرح المسمى فقط ولم يسقط صامت حدسا.")
    lines.extend([
        f"- درجة المقارنة: {H.comparison_degree(decision.candidate)}",
        f"- المروحة المرتبة الكاملة: `fan_any_script.fan({row.branch}, persian)`؛ العدد {len(ranked)}: {H.formatted_fan(ranked)}.",
        f"- فحص المروحة كلها: قُرئت مواد {len(ranked)} مرشحا بـ`--max-chars 0`؛ لم يحكم عمود `best`.",
        f"- المقابل من اللسان: `{decision.candidate}`؛ من المروحة الحية ومن أعضاء الحوض المصدرة.",
        f"- مسار الصوت والحد المسمى: {H.formatted_route(row, decision.candidate)}",
        f"- الحدث من السجل المجمد كما هو: {H.event_line(decision.candidate)}",
        f"- المعنى من قاموس الفرع بلا رتوش: «{entry.gloss}».",
        f"- طريق المعنى المسمى: {review.meaning_path}",
        f"- مسح المعاني العربية: قُرئت {match_count} نتيجة لـ`{decision.candidate}` كاملة؛ الشواهد العربية الكلاسيكية المستقلة={classical_count}؛ نقل شاهدان أو سميت الفجوة:",
        f"  - الشاهد 1، {witnesses[0][0]}: «{witnesses[0][1]}»",
        f"  - الشاهد 2، {witnesses[1][0]}: «{witnesses[1][1]}»",
        f"- المدار المكتوب بخط اليد: {decision.orbit}",
        "- المصفاة: الأصل حاشية؛ لا يغلق النقل إلا بمانح سامي مسمى أو تصريح بالتعريب أو باتجاه الدخول إلى العربية.",
        "- فصل المتجانسات والاقتراض: الحكم للمدخلة؛ لا توارث من متحد الرسم.",
        "- اليتم والإشعاع: الجرد والشاهدان أو فجوتاهما حاضرة؛ لا قرينة عدد.",
        "- جسور الاسترداد: الفرع؛ الأصل؛ الصفر؛ المروحة؛ الشبكة؛ الشواهد؛ المصفاة؛ المركب.",
        f"- عائق القرار أو تمامه: {decision.obstacle}",
        f"- ملاحظات العدستين: استرداد وتشكيك العضو؛ الجولة 28، {item.key}.",
        f"- حالة الإغلاق: {decision.state}.",
        f"- الحكم (استكشاف): {decision.verdict}.",
    ])
    return "\n".join(lines) + "\n"


def fit_card(item: SelectedRow, entry: H.BranchEntry, raw: dict, decision: H.Decision, ranked: tuple[tuple[str, float], ...], sense_map: dict[str, list[dict]]) -> str:
    for quote_limit, etym_limit in ((230, 340), (180, 280), (130, 210), (90, 150), (60, 105), (35, 70), (20, 45), (12, 25), (8, 15)):
        card = make_card(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit)
        if len(card.encode("utf-8")) < CARD_LIMIT:
            return card
    raise AssertionError(f"تجاوزت بطاقة {item.key} حد 5KB")


def validate_decisions(selected: list[SelectedRow], raw_entries: dict[int, dict], decisions: list[H.Decision], ranked_by_rank: dict[int, tuple[tuple[str, float], ...]], sense_map: dict[str, list[dict]]) -> None:
    if set(REVIEWS) != set(SOUND_RANKS):
        raise AssertionError("جدول المدار اليدوي لا يغطي الرتب السبعين")
    exact = {item.row.rank for item in selected if P25.direct_from_plus(raw_entries[item.row.rank]["etymology"])}
    if exact != EXACT_DECOMPOSITIONS:
        raise AssertionError(f"تغيرت أسطر From X + Y المباشرة: {sorted(exact)}")
    if {rank for rank, review in REVIEWS.items() if review.verdict == "NUCLEUS-TRACE"} != {227}:
        raise AssertionError("تغير موضع NUCLEUS-TRACE اليدوي")
    if {rank for rank, review in REVIEWS.items() if review.verdict == "ROOT-ECHO"} != {233}:
        raise AssertionError("تغير موضع ROOT-ECHO اليدوي")
    if {rank for rank, review in REVIEWS.items() if review.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC"} != {180}:
        raise AssertionError("تغير موضع حكم اتجاه الدخول")
    for item, decision in zip(selected, decisions):
        row = item.row
        candidates = {candidate for candidate, _score in ranked_by_rank[row.rank]}
        if decision.candidate not in candidates or decision.candidate not in row.candidates_found:
            raise AssertionError(f"مرشح الرتبة {row.rank} خارج المروحة الحية أو أعضاء الحوض")
        complete = H.route_complete(row, decision.candidate)
        _count, coverage, _witnesses = P.classical_witnesses(decision.candidate, sense_map, 60)
        if decision.verdict == "LAW-GAP" and complete:
            raise AssertionError(f"LAW-GAP بلا صف مفقود في الرتبة {row.rank}")
        if decision.verdict in {"OPEN-CANDIDATE", "ROOT-TRACE", "NUCLEUS-TRACE", "ROOT-ECHO", "LOANWORD-NON-ARABIC-TO-ARABIC"} and not complete:
            raise AssertionError(f"حكم بمسار ناقص في الرتبة {row.rank}: {decision.verdict}")
        if decision.verdict in {"ROOT-TRACE", "NUCLEUS-TRACE", "ROOT-ECHO", "LOANWORD-NON-ARABIC-TO-ARABIC"}:
            if coverage < 2 or H.event_line(decision.candidate).startswith("لا حدث"):
                raise AssertionError(f"حكم صادر بلا حدث وشاهدين في الرتبة {row.rank}")
        if row.rank in EXACT_DECOMPOSITIONS and decision.verdict not in {"COMPOUND-BOUNDARY", "MORPHOLOGY-GAP"}:
            raise AssertionError(f"تفكيك مباشر بلا حد مركب في الرتبة {row.rank}")
        if row.rank in BLOCKED_BOUNDARIES and decision.verdict != "COMPOUND-BOUNDARY":
            raise AssertionError(f"حد غير مؤهل بلا COMPOUND-BOUNDARY في الرتبة {row.rank}")
        if not REVIEWS[row.rank].meaning_path.startswith(("جسر المعنى:", "نص الحدث المجمد")):
            raise AssertionError(f"طريق المعنى غير مسمى في الرتبة {row.rank}")


def validate_text(selected: list[SelectedRow], texts: list[str], prior_pairs: set[tuple[str, str]]) -> None:
    if len(selected) != 70 or BATCH_SIZES != (35, 35):
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = re.findall(r"^### (WO-B-R28-SOUND-\d{5}):", joined, re.MULTILINE)
    if headings != [item.heading for item in selected]:
        raise AssertionError("معرفات الجولة 28 لا تطابق النافذة")
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
    required = ("نموذج WO-B-PROBE-001", "قراءة مداخل الرسم المتجانس", "المروحة المرتبة الكاملة", "الحدث من السجل المجمد", "طريق المعنى المسمى", "المدار المكتوب بخط اليد", "الشاهد 1", "الشاهد 2", "الحكم (استكشاف)")
    for item, card in zip(selected, texts):
        if len(card.encode("utf-8")) >= CARD_LIMIT:
            raise AssertionError(f"تجاوزت {item.key} حد 5KB")
        if any(field not in card for field in required):
            raise AssertionError(f"نقص حقل من بطاقة {item.key}")
    for rank in EXACT_DECOMPOSITIONS:
        card = texts[SOUND_RANKS.index(rank)]
        if "تفكيك Kaikki الحصري" not in card or "قراءة المكونات المستقلة" not in card:
            raise AssertionError(f"لم تقرأ مكونات الرتبة {rank} استقلالا")
    for rank in BLOCKED_BOUNDARIES:
        card = texts[SOUND_RANKS.index(rank)]
        if "حد المركب غير المفكك" not in card or "بلا مكونات مخترعة" not in card:
            raise AssertionError(f"لم يغلق حد المركب في الرتبة {rank}")
    for rank in TOOL_GAPS:
        card = texts[SOUND_RANKS.index(rank)]
        if "عطب الهيكل" not in card or "لا حكم من هيكل ناقص" not in card:
            raise AssertionError(f"لم يسم عطب الهيكل في الرتبة {rank}")


def report_section(selected: list[SelectedRow], decisions: list[H.Decision], sizes: list[int], stats: dict) -> str:
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
            f"## الجولة الثامنة والعشرون، دفعة sound_only رقم {number}", "",
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
    traces = [item.heading for item, decision in zip(selected, decisions) if decision.verdict in {"ROOT-TRACE", "NUCLEUS-TRACE"}]
    echoes = [item.heading for item, decision in zip(selected, decisions) if decision.verdict == "ROOT-ECHO"]
    transmissions = [item.heading for item, decision in zip(selected, decisions) if decision.verdict == "LOANWORD-NON-ARABIC-TO-ARABIC"]
    lines.extend([
        "## حصيلة الجولة الثامنة والعشرين", "",
        f"- حمل `persian.md` مرة واحدة؛ أزواج WO-B المقروءة={stats['pair_count']}؛ المتجاوز داخل النافذة={', '.join(map(str, stats['skipped']))}.",
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- نطاق الصوت الجديد: الرتب 178-251 بعد آخر معرف في الجولة السابقة، مع إسقاط الأزواج الخمسة المقروءة فقط.",
        f"- الأثر المحكم ذو الأرجل الثلاث والشاهدين: {', '.join(traces)}.",
        f"- الصدى المعجمي الموسوم بلين رجل الحدث: {', '.join(echoes)}.",
        f"- اتجاه الدخول إلى العربية المسمى بالشاهدين: {', '.join(transmissions)}.",
        "- التفكيك المباشر: S00200، S00201، S00202، S00208، S00213، S00235، S00245، S00246، S00247؛ قرئت المكونات استقلالا.",
        "- الحدود غير المؤهلة: S00190، S00191، S00214، S00215، S00228؛ لم يحول Equivalent أو التحليل التاريخي إلى From X + Y.",
        "- فجوات الأداة: S00183 `کوه`، S00199 `گهگاه`، S00243 `نانوا`؛ لم تعوض الصوامت المنطوقة الساقطة.",
        "- أحواض `nucleus-sweep-*.json` التسعة الحالية v8 قرئت كاملة من القرص، وثبت الحجم وSHA-256 لكل ملف قبل الجولة.",
        f"- أكبر بطاقة: {max_size} بايت، {max_item.heading}؛ كل البطاقات دون 5KB.",
        "- لم تفعل طبقة البرهان، ولم يبن ملف مشترك، ولم يقع ship، ولم يستعمل git.",
        "", f"<!-- {MARKER}:END -->", "", DONE_LINE,
    ])
    return "\n".join(lines)


def validate_existing(reading_text: str, report_text: str) -> None:
    match = re.search(rf"<!-- {re.escape(MARKER)}:START -->(.*?)<!-- {re.escape(MARKER)}:END -->", reading_text, re.DOTALL)
    if not match:
        raise AssertionError("محضر الجولة موجود وبطاقاتها غائبة")
    headings = re.findall(r"^### (WO-B-R28-SOUND-\d{5}):", match.group(1), re.MULTILINE)
    expected = [f"WO-B-R28-SOUND-{rank:05d}" for rank in SOUND_RANKS]
    if headings != expected:
        raise AssertionError("مقطع الجولة 28 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(DONE_LINE):
        raise AssertionError("سطر DONE28 ليس خاتمة التقرير")


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
        print("ROUND28 ALREADY PRESENT AND VALID")
        print(DONE_LINE)
        return 0

    data = json.loads(SWEEP.read_text(encoding="utf-8"))
    selected, stats = select_rows(data, reading_text)
    prior_pairs = H.read_pairs(reading_text)
    lexicon = json.loads(LEXICON.read_text(encoding="utf-8"))
    entries, grouped = select_branch_entries(selected, lexicon)
    raw_entries = load_raw_entries(selected, entries)
    validate_components(grouped)

    ranked_by_rank = {item.row.rank: H.full_ranked_fan(item.row) for item in selected}
    roots = {candidate for ranked in ranked_by_rank.values() for candidate, _score in ranked}
    roots.update(review.candidate for review in REVIEWS.values())
    sense_map = H.SENSES.matches_for_roots(H.SENSES.DEFAULT_RESOURCES, roots, None)
    decisions = [decide(item) for item in selected]
    validate_decisions(selected, raw_entries, decisions, ranked_by_rank, sense_map)
    texts = [fit_card(item, entries[item.row.rank], raw_entries[item.row.rank], decision, ranked_by_rank[item.row.rank], sense_map) for item, decision in zip(selected, decisions)]
    validate_text(selected, texts, prior_pairs)
    sizes = [len(card.encode("utf-8")) for card in texts]

    reading_append = (
        f"\n\n<!-- {MARKER}:START -->\n\n"
        "## الجولة الثامنة والعشرون: متابعة حوض sound_only (2026-08-26)\n\n"
        "- النطاق: 70 عضوا طازجا بعد WO-B-R27-SOUND-00176؛ من الرتبة 178 إلى 251 مع تجاوز 177 و179 و181 و219 و232 لأنها مقروءة؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ طريق المعنى مسمى، والمدار اليدوي حاسم، والأصداء مفصولة عن الآثار المحكمة.\n"
        "- لقطة الأحواض: قرئت ملفات nucleus-sweep-*.json التسعة الحالية v8 من القرص وثبتت بصماتها قبل الانتخاب.\n\n"
        + "\n".join(texts[:35])
        + "\n## الدفعة الثانية: متابعة sound_only بعد الرتبة 214\n\n"
        + "\n".join(texts[35:])
        + f"\n<!-- {MARKER}:END -->\n"
    )
    report_append = "\n" + report_section(selected, decisions, sizes, stats) + "\n"
    reading_append = unicodedata.normalize("NFC", reading_append)
    report_append = unicodedata.normalize("NFC", report_append)
    if "—" in reading_append + report_append or re.search(r"[۰-۹٠-٩]", reading_append + report_append):
        raise AssertionError("فشل حارس الشرطة أو الأرقام قبل الكتابة")
    combined_reading = reading_text + reading_append
    combined_report = report_text + report_append
    validate_existing(combined_reading, combined_report)

    counts = Counter(decision.verdict for decision in decisions)
    print("ROUND28 READY")
    print("NUCLEUS_V8_FILES", len(NUCLEUS_SNAPSHOT), "SHA256_OK")
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
    print("ROUND28 WRITTEN")
    print(DONE_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
