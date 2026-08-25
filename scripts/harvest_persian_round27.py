# -*- coding: utf-8 -*-
"""المسار B، الجولة 27: متابعة حوض sound_only في دفعتين من 35 بطاقة."""

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

import harvest_persian_round26 as R26  # noqa: E402

H = R26.H
P = R26.P
P25 = R26.P25
READING = ROOT / "04-cross-linguistic" / "readings" / "persian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-B.md"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-persian.json"
LEXICON = ROOT / "data" / "branch-lexicons" / "persian.json"
RAW_LEXICON = ROOT / "Resources" / "persian" / "kaikki.org-dictionary-Persian.jsonl"
MARKER = "LANE-B-PERSIAN-ROUND27-2026-08-25"
CARD_LIMIT = 5120
SOUND_RANKS = (
    tuple(range(104, 127))
    + tuple(range(129, 139))
    + tuple(range(140, 177))
)
BATCH_SIZES = (35, 35)
DONE_LINE = "LANE-B DONE27 70 WO-B-R27-SOUND-00176"
EXPECTED_SKIPS = (127, 128, 139)
EXACT_DECOMPOSITIONS = {130}
BLOCKED_BOUNDARIES = {
    136: (
        "يسرد Kaikki شجرة ثم يكتب `گلاب` + `ـی` بلا صيغة From X + Y "
        "النهائية المباشرة التي ألزم بها هذا الرتل."
    ),
    148: (
        "يكتب Kaikki From `هفت` + `ـه` ثم يتبعه بخبر Akin؛ لم يكن سطر "
        "From X + Y خاتمة الخبر كما يشترط كاشف الرتل."
    ),
}
TOOL_GAPS = {
    140: (
        "الصورة `شاه` منقوطة /šāh/ في المدخلة، لكن صف الحوض أعطاها الهيكل "
        "`شـا` وأسقط الهاء النهائية المنطوقة؛ لم تعوض الهاء حدسا."
    ),
    147: (
        "الصورة `ماه` منقوطة /māh/ في المدخلة، لكن صف الحوض أعطاها الهيكل "
        "`مـا` وأسقط الهاء النهائية المنطوقة؛ لم تعوض الهاء حدسا."
    ),
}
OUT_OF_SCOPE = {
    138: "المدخلة اسم علم للكوكب Earth، وطبقة الأعلام معزولة عن الحكم المعجمي العام.",
    151: "المدخلة اسم مدينة Paris وشرحها تعريف بالكيان لا معنى معجميا؛ أحيلت إلى طبقة الأعلام.",
}

EXPECTED_ENTRY_INDEX = {
    104: 550, 105: 551, 106: 552, 107: 555, 108: 557, 109: 559,
    110: 561, 111: 564, 112: 565, 113: 567, 114: 569, 115: 573,
    116: 582, 117: 586, 118: 587, 119: 588, 120: 594, 121: 599,
    122: 602, 123: 603, 124: 604, 125: 605, 126: 620, 129: 641,
    130: 650, 131: 654, 132: 663, 133: 664, 134: 674, 135: 676,
    136: 677, 137: 678, 138: 679, 140: 689, 141: 691, 142: 692,
    143: 699, 144: 702, 145: 703, 146: 712, 147: 729, 148: 731,
    149: 735, 150: 737, 151: 747, 152: 750, 153: 754, 154: 756,
    155: 760, 156: 766, 157: 769, 158: 770, 159: 772, 160: 773,
    161: 781, 162: 784, 163: 785, 164: 786, 165: 788, 166: 791,
    167: 792, 168: 793, 169: 794, 170: 798, 171: 802, 172: 803,
    173: 804, 174: 809, 175: 810, 176: 811,
}

EXPECTED_RAW_LINE = {
    104: 592, 105: 593, 106: 594, 107: 597, 108: 599, 109: 601,
    110: 604, 111: 607, 112: 608, 113: 610, 114: 612, 115: 616,
    116: 625, 117: 629, 118: 630, 119: 631, 120: 637, 121: 642,
    122: 645, 123: 646, 124: 647, 125: 648, 126: 663, 129: 685,
    130: 694, 131: 698, 132: 707, 133: 708, 134: 721, 135: 723,
    136: 724, 137: 725, 138: 726, 140: 736, 141: 738, 142: 739,
    143: 746, 144: 749, 145: 750, 146: 759, 147: 776, 148: 778,
    149: 782, 150: 784, 151: 795, 152: 798, 153: 802, 154: 804,
    155: 808, 156: 814, 157: 817, 158: 818, 159: 820, 160: 821,
    161: 829, 162: 832, 163: 834, 164: 835, 165: 837, 166: 841,
    167: 842, 168: 843, 169: 844, 170: 850, 171: 854, 172: 855,
    173: 856, 174: 861, 175: 862, 176: 863,
}


@dataclass(frozen=True)
class SelectedRow:
    row: H.SweepRow

    @property
    def key(self) -> str:
        return f"S{self.row.rank:05d}"

    @property
    def heading(self) -> str:
        return f"WO-B-R27-SOUND-{self.row.rank:05d}"


@dataclass(frozen=True)
class Review:
    candidate: str
    verdict: str
    meaning_path: str
    orbit: str


def R(candidate: str, verdict: str, meaning_path: str, orbit: str) -> Review:
    return Review(candidate, verdict, meaning_path, orbit)


# سجل القراءة اليدوية. لا يشتق الحكم من عمود best ولا من وزن المروحة.
REVIEWS = {
    104: R("خبو", "ROOT-ECHO", "نص الحدث المجمد لـ`خبو`: خمود اللهب ونحوه، وشاهدا العربية يصرحان بسكون النار والحرب.", "مدار 7: النوم حال تسكن فيه قوى اليقظة كما تسكن الحرب أو تخبو النار؛ الخطوة مفهومة لكنها قياس حال على حال، لذلك وسمت صدى جذريا لا أثرا محكما."),
    105: R("خبو", "ROOT-ECHO", "نص الحدث المجمد لـ`خبو`: خمود اللهب ونحوه؛ asleep صفة لمن سكنت يقظته.", "مدار 7: الصفة asleep تحمل حال خبو النشاط الواعي، لكن انتقال الخبو من نار أو حرب إلى الجسد ألين من التطابق المعجمي، فأغلق ROOT-ECHO."),
    106: R("جدن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جدن`: العظم والامتداد؛ لا يسمي الجاذبية الجنسية أو قابلية الفعل.", "فصلت معنى sexually attractive عن مجرد العظم أو الامتداد؛ لا يحول وصف الجسد إلى الحدث نفسه."),
    107: R("دختر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دختر`: نزول إلى نواة التخلخل مع حدث التاء؛ لا يسمي بنتا أو فتاة.", "الصورة الكاملة حاضرة في المروحة الحية، لكن معنى القرابة والجنس لا يقوم من أحداث الحروف بلا جسر معجمي مباشر."),
    108: R("زور", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زور`: امتساك جمع بانتظام وامتداد؛ لا يسمي cool أو awesome في الاستعمال العامي.", "قوة الشيء قد تجعله مدهشا، لكن ذلك تفسير لتطور عامي داخل الفارسية لا نقطة معنى واحدة في الحدث المجمد."),
    109: R("زر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زر`: النفاذ بدقة مع إمساك؛ لا يسمي سكب القربان.", "الـlibation فعل صب، ولا يرده النفاذ مع الإمساك إلى حدث واحد؛ بقي التشابه الصوتي وحده."),
    110: R("نخن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`نخن`: نقص في الانتصاب أو إصمات البناء؛ لا يسمي ظفر اليد.", "كون الظفر صلبا وصف عارض لا يساوي النقص في البناء، ولا يميز nail عن سائر الأجزاء الصلبة."),
    111: R("بنجر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بنجر`: الامتداد والبناء مع حدث الجيم؛ لا يسمي نافذة أو مشبكا.", "النافذة جزء من بناء، لكن علاقة الجزء بالكل لا تعين هذا الجزء ولا معنى lattice؛ احتاج المدار إلى وسيط ثان."),
    112: R("خوش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خوش`: تجمع دقاق خشنة أو حادة؛ والشواهد العربية تسمي الخاصرة والهزال لا السعادة.", "فصلت الفارسية pleasant عن متجانس العربية؛ اتحاد الرسم لا ينقل معنى الفرح بين مدخلتين مختلفتين."),
    113: R("خمش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خمش`: اضطمام على مائع أو خور؛ والشواهد العربية في الخدش، لا الصمت.", "لا يجعل انقطاع الكلام خدشا ولا اضطماما؛ quiet وsilent بقيتا بلا مدار معجمي مباشر."),
    114: R("خون", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خون`: نقص خطير في خفية؛ وشواهد العربية في الخيانة لا الدم.", "فصلت blood عن متجانس الخون العربي؛ خروج الدم قد ينقص الجسد لكنه فعل لاحق لا معنى اسم المادة."),
    115: R("خهر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خهر`: تخلخل باطن مع حدث الراء؛ لا يسمي الأخت.", "صلة القرابة لا تستخرج من تخلخل أو حركة صوتية، ولم يرد جسر معجمي إلى sister."),
    116: R("سج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سج`: امتداد دقيق نافذ؛ لا يسمي الكلب أو جنس Canis.", "صفة الحركة أو النفاذ يمكن أن تقع من الحيوان ولا تسمي نوعه؛ لا مدار إلى dog."),
    117: R("درد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`درد`: جريان أو امتداد بتوال؛ لا يسمي تحية hello أو hail.", "إرسال التحية في الكلام جريان للصوت لكنه وصف أداء يصدق على كل قول، لا معنى المدخلة."),
    118: R("درد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`درد`: الجريان أو الامتداد؛ لا يسمي greeting أو well-being.", "فصلت متجانس الصحة والتحية عن timber وعن الحدث العربي؛ لا نقطة معنى واحدة تثبت السلامة أو التحية."),
    119: R("درد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`درد`: الجريان أو الامتداد بتوال؛ لا يسمي timber أو plank.", "امتداد اللوح هيئة هندسية عامة لا معنى الخشب نفسه، فلا ينهض مدار المادة من الصفة وحدها."),
    120: R("مار", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مار`: الاسترسال والحركة مع صفة؛ ولا يرد في الشواهد العربية معنى snake.", "حركة الحية استرسال ممكن، لكنه فعل من أفعال الحيوان لا اسمه المعجمي؛ بقي المرشح مفتوحا."),
    121: R("طاس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`طاس`: نزول إلى نواة الطس؛ والشواهد العربية في الإناء لا حجر النرد.", "فصلت die وdice عن الطاس بمعنى القدح؛ استعمال الإناء في لعب محتمل لا يثبت معنى المدخلة."),
    122: R("جند", "LAW-GAP", "نص الحدث المجمد لـ`جند`: الصلابة بالضغط؛ لا يسمي الكمية، وفوق ذلك چ↔ج بلا صف نافذ هنا.", "لم يقم مدار how many أو several، ومسار الصوت نفسه ناقص؛ سميت فجوة القانون من غير استبدال چ."),
    123: R("جند", "LAW-GAP", "نص الحدث المجمد لـ`جند`: الصلابة بالضغط؛ لا يسمي how much أو امتداد الزمن، وچ↔ج غير مرخص.", "فصلت مدخلة الظرف عن المحدد السابق، وبقيت الوظيفة الاستفهامية خارج الحدث ومسار الصوت."),
    124: R("شندر", "LAW-GAP", "جسر المعنى: beet يقارب صورة `شمندر` العربية، لكن المرشح `شندر` أسقط الميم وچ↔ش غير مرخص.", "الجسر النباتي نبه إلى صورة قريبة، لكنه لا يجيز إسقاط ميم العربية ولا يفتح صف چ↔ش؛ لم يصدر حكم."),
    125: R("شق", "LAW-GAP", "جسر المعنى: السكين آلة الشق والقطع، وشاهدا `شق` يسميان الخرم والانقسام مباشرة.", "مدار 4: knife أداة تحدث الشق، لكن چ↔ش وق↔ق لا يكتملان بصف مسمى في هذا الموضع؛ حفظت الدلالة وسميت LAW-GAP."),
    126: R("الو", "LAW-GAP", "نص الحدث المجمد لـ`الو`: محاكم حروف لا تسمي plum أو prune؛ وآ↔ا بلا صف موقع.", "لا مدار للثمرة، كما أن الهمزة الممدودة لم تعالج حدسا؛ بقيت فجوة القانون صريحة."),
    129: R("شكر", "LAW-GAP", "نص الحدث المجمد لـ`شكر`: ظهور أثر نعمة؛ لا يسمي servant، وچ↔ش وک↔ك لا يكونان مسارا نافذا هنا.", "الخادم قد يشكر سيده، لكن هذا فعل عرضي لا معنى المهنة؛ وفوقه رجل الصوت ناقصة."),
    130: R("زندج", "MORPHOLOGY-GAP", "جسر المعنى: Kaikki يفكك life إلى `زنده` alive و`ـگی`؛ لا تقارن الصورة قبل المكونين.", "ثبت From X + Y وقُرئت `زنده`، لكن `ـگی` غابت من لقطة الفرع؛ وقف الحكم عند فجوة الصرف."),
    131: R("شيش", "OPEN-CANDIDATE", "جسر المعنى: خبر الأصل يقارن العبرية والسريانية في alabaster وmarble، لكن شواهد `شيش` العربية في تمر لا ينعقد نواه.", "فصلت مسار المادة السامي المحتمل عن المتجانس العربي؛ صيغة probably وCompare لا تسمي مانحا محسوما ولا تثبت معنى glass في العربية."),
    132: R("اذن", "LAW-GAP", "نص الحدث المجمد لـ`اذن`: الإذن أو السماع بحسب المادة؛ لا يسمي Friday، وآ↔ا ود↔ذ غير مكتملين.", "اسم اليوم لا يرد إلى الإذن بلا سلسلة تاريخية، ورجل الصوت ناقصة؛ لم أستبدل اسم يوم عربي حدسا."),
    133: R("شنب", "OPEN-CANDIDATE", "جسر المعنى: الأصل ينتهي إلى Hebrew Sabbath، لكن المرشح العربي `شنب` لا يحمل معنى Saturday.", "سميت السامية في حاشية الأصل، لكن الطريق الصوتي المقروء هنا إلى شنب لا إلى سبت؛ لم أنقل حكم المانح إلى جذر آخر."),
    134: R("بني", "ROOT-TRACE", "جسر المعنى: shelter بناء يكن من المطر؛ وشاهدا `بني` يسميان المبناة والبيت والبناء نقيض الهدم.", "مدار 5: المأوى بنية مقامة للحماية، ونص العين يصف المبناة التي يسكن فيها من المطر؛ اكتملت الصورة والحدث والمعنى والشاهدان."),
    135: R("جلب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جلب`: الإتيان بالشيء من موضع؛ لا يسمي pear.", "جلب الثمرة إلى السوق فعل عليها لا اسم نوعها؛ لم يقم مدار نباتي مباشر."),
    136: R("جلب", "COMPOUND-BOUNDARY", "جسر المعنى: pink من `گلاب` rosewater واللاحقة الصرفية بحسب شجرة Kaikki، لا من جذر الصورة المجموعة.", "الخبر يفسر اللون بالمركب، لكنه لا يأتي بصيغة From X + Y النهائية الملزمة؛ وقف الحكم بلا تفكيك مخترع."),
    137: R("زمن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زمن`: ضم الكثير باكتناز؛ لا يسمي earth أو land أو soil.", "اكتناز التراب وصف لمادة الأرض لا تعريفها، ويصدق على أكوام كثيرة؛ لا مدار إلى المدخلة."),
    138: R("زمن", "OUT-OF-SCOPE", "جسر المعنى: Earth هنا اسم علم للكوكب لا معنى معجميا مستقلا يصل إلى `زمن`.", "عزلت اسم الكوكب في طبقة الأعلام؛ لم أورثه حكم مدخلة earth العامة ولا حكم متجانس `زمین` السابق."),
    140: R("شا", "TOOL-GAP", "جسر المعنى: king وshah في المدخلة، لكن الحوض أسقط هاء /šāh/ قبل بناء المروحة.", "لا يصح فحص شاه بهيكل `شـا`؛ توقف العضو عند عطب إسقاط صامت منطوق ولم تعوض الهاء من السياق."),
    141: R("شم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شم`: جمع منتشر منسحبا إلى أعلى؛ لا يسمي ضمير المخاطب الجمع.", "الوظيفة النحوية you لا تتحول إلى حدث جذري من الجمع العددي؛ لا مدار معجمي للضمير."),
    142: R("تو", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تو`: محكمتا التاء والواو بلا حدث معجمي موحد؛ لا يسمي ضمير المخاطب المفرد.", "اتحاد الصورة مع مادة عربية محتملة لا يثبت وظيفة you أو thou؛ أبقيت الضمير مستقلا."),
    143: R("كي", "OPEN-CANDIDATE", "جسر المعنى: `كي` العربية أداة تعليل أو نصب، والمدخلة الفارسية when أداة زمان؛ الوظيفتان غير واحدة.", "فصلت اتحاد الرسم بين أداتين نحويتين؛ لا يحول معنى الغاية العربية إلى سؤال عن الزمن."),
    144: R("لب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`لب`: اللزوم والتداخل، وشواهد العربية تسمي الداخل الخالص لا lip أو edge.", "قد يحيط الشفاه بالفم، لكن الإحاطة ليست معنى اللب العربي ولا تحدد حافة بعينها؛ بقي المتجانسان منفصلين."),
    145: R("ما", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ما`: محكمتا الميم والألف؛ لا يسمي ضمير المتكلم جمعا أو مفردا.", "الضمير وظيفة إحالية لا تستخرج من حدثي الحرفين، واتحاد الرسم مع `ما` العربية لا يوحد الوظائف."),
    146: R("شن", "LAW-GAP", "جسر المعنى: شاهد `شن` يصرح بالتشنن والتشنج في الجلد، وهو wrinkle وcrease مباشرة.", "مدار 2: التجعد هو تشنن الجلد، وشاهداه حاضران، لكن چ↔ش غير مسمى؛ حفظت رجل المعنى وأغلقت LAW-GAP."),
    147: R("ما", "TOOL-GAP", "جسر المعنى: moon وmonth في المدخلة، لكن الحوض أسقط هاء /māh/ قبل المروحة.", "الهيكل `مـا` لا يمثل الصورة المنطوقة `ماه`؛ لم أبحث عن قمر أو شهر بعد عطب الصامت الأصلي."),
    148: R("هفت", "COMPOUND-BOUNDARY", "جسر المعنى: week مبنية من seven مع لاحقة بحسب Kaikki، لكن سطر From X + Y ليس خاتمة الخبر.", "قرأت خبر `هفت` واللاحقة، لكن معيار الرتل لا يقبل التفكيك الذي يتلوه خبر Akin؛ وقف الحكم عند الحد."),
    149: R("سندن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سندن`: نزول إلى نواة الامتداد الدقيق؛ لا يسمي hear أو listen.", "حدة السمع صفة للقدرة لا فعل السماع نفسه؛ لم يثبت مدار من معنى المدخلة."),
    150: R("بزرج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بزرج`: محاكم أو نزول لا يسمي large أو great.", "كبر الحجم لا يساوي مجرد امتداد أصوات الجذر من غير شاهد عربي معجمي؛ بقي المرشح مفتوحا."),
    151: R("برس", "OUT-OF-SCOPE", "جسر المعنى: شرح Paris تعريف بمدينة فرنسا لا معنى قاموسيا يمكن وصله بـ`برس`.", "أحلت الاسم إلى طبقة الأعلام والمواقع؛ لم أحول وصف العاصمة إلى معنى للجذر."),
    152: R("رم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رم`: تجمع رخو من تحول ذي حدة؛ لا يسمي الفزع أو الانطلاق منه.", "taking off from fright حركة ناتجة من الخوف، لكنها لا تساوي التجمع الرخو ولا تحدد shying معجميا."),
    153: R("لمم", "ROOT-TRACE", "جسر المعنى: herd وassemblage جمع، وشاهدا `لمم` يقولان جمع المتفرق وأن الرجل يلم القوم.", "مدار 1: القطيع أو جماعة الناس شيء ملتئم من أفراد؛ اكتملت رجل الحدث مع الشاهدين والصوت."),
    154: R("مه", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مه`: الفراغ والرقة والسهولة؛ لا يسمي fish أو whale.", "سهولة سباحة السمك وصف حركة لا اسم الحيوان، ولا يميز الحوت من غيره؛ لا مدار مباشر."),
    155: R("برنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`برنج`: التجرد والخلوص مع حدث النون؛ وشواهد العربية تسمي جوز الهند لا brass.", "فصلت متجانس البارنج النباتي عن المعدن الفارسي؛ ذكر السريانية في الأصل حاشية اتجاه لا جسر عربي للمعنى."),
    156: R("اش", "LAW-GAP", "جسر المعنى: aush أو osh اسم طعام؛ لا حدث مجمد يسمي الحساء، وآ↔ا وش↔ش لا يكتملان بصف موقع.", "اسم الطبق بقي في مسار أصله التركي أو الإيراني المختلف عليه، ورجل الصوت العربية ناقصة؛ سميت LAW-GAP."),
    157: R("بردر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بردر`: نزول إلى نواة التجرد مع أحداث زائدة؛ لا يسمي brother أو comrade.", "صلة الأخوة لا تستخرج من التجرد أو الامتداد، وقرابة Indo-European في الأصل ليست طريقا عربيا مسمى."),
    158: R("بدر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بدر`: امتلاء أو مبادرة بحسب الشواهد؛ لا يسمي father.", "فصلت أصل father الهندي الأوروبي عن البدر العربي؛ اتحاد بعض الصوامت لا ينقل معنى الأبوة."),
    159: R("زن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زن`: تعلق لطيف مستور؛ لا يسمي knee.", "اتصال الركبة بالساق وصف تشريحي عام، لا معنى النواة ولا اسم المفصل نفسه."),
    160: R("دهن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دهن`: مائع ذو لزوجة؛ لا يسمي mouth أو opening.", "خبر الأصل يذكر تركيبا إيرانيا قديما ونظرية بديلة، فلا يجيز توريث `دم` أو غيره؛ والمتجانس العربي دهن مختلف."),
    161: R("مز", "LAW-GAP", "جسر المعنى: خبر بديل يرد eyelash إلى hair مع لاحقة تصغير، لكن ژ↔ز بلا صف مسمى.", "الأصل البديل غير حاسم ولا From X + Y نهائيا، ومسار الصامت الثاني ناقص؛ لم أبن مدار الرمش من الحدس."),
    162: R("باز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`باز`: النفاذ من مضيق؛ لا يسمي upper arm أو arm.", "نفاذ الذراع في الكم وصف موضعي يصدق على أعضاء وأشياء كثيرة؛ لا معنى تشريحي مباشر."),
    163: R("مو", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مو`: محكمتا الميم والواو بلا معنى hair، ولا شاهد عربي كلاسيكي للمادة.", "ربط الشعر أو امتداده صفة له لا اسمه؛ لم أحول مطابقة الصورة إلى حكم بلا حدث وشاهد."),
    164: R("مو", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مو`: محكمتا الميم والواو؛ لا يسمي vine.", "امتداد الكرمة والتفافها وصف نباتي عام، ولا ينهض من حدثي الحرفين معنى النوع."),
    165: R("بن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بن`: الامتداد والبناء؛ لا يسمي nose.", "بروز الأنف امتداد شكلي لا يميز العضو عن سائر البروزات؛ لم يقم مدار تشريحي مباشر."),
    166: R("جه", "LAW-GAP", "نص الحدث المجمد لـ`جه`: محاكم حروف لا تسمي what، وچ↔ج وه↔ه غير مكتملين في صف الحوض.", "الضمير الاستفهامي وظيفة نحوية، ومعها فجوة صوت؛ لم يستبدل بجذر عربي حدسا."),
    167: R("جه", "LAW-GAP", "نص الحدث المجمد لـ`جه`: لا يسمي what sort of أو التعجب، وچ↔ج غير مرخص.", "فصلت المحدد عن الضمير السابق، وبقيت الوظيفة النحوية ومسار الصوت ناقصين."),
    168: R("جه", "LAW-GAP", "نص الحدث المجمد لـ`جه`: لا يسمي how التعجبية، وچ↔ج غير مرخص.", "لم أحول شدة التعجب إلى حدث صوتي؛ سميت فجوة القانون على الصامت الأول."),
    169: R("جه", "LAW-GAP", "نص الحدث المجمد لـ`جه`: لا يسمي because، وچ↔ج غير مرخص.", "السببية وظيفة رابط لا معنى جذري، ومسار الصوت ناقص؛ بقيت المدخلة مستقلة."),
    170: R("بج", "LAW-GAP", "نص الحدث المجمد لـ`بج`: عظم أو بروز؛ لا يسمي child، وچ↔ج بلا صف نافذ.", "الصغر أو النمو صفات للطفل لا معنى الجذر، وفوق ذلك رجل الصوت ناقصة."),
    171: R("شاد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شاد`: صلابة أو وثاقة؛ لا يسمي glad أو happy أو cheerful.", "قد يقوى الفرح صاحبه، لكن القوة أثر ممكن لا معنى السرور نفسه؛ بقي المتجانسان منفصلين."),
    172: R("سنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سنج`: امتداد أو نفاذ مع دقة؛ وشواهد العربية في أثر الدخان وسنجة الميزان لا stone.", "الحجر قد يكون سنجة وزن، لكن الوظيفة لا تجعل كل stone وزنا ولا تسمي rock؛ فصلت معنى المادة."),
    173: R("سنج", "ROOT-ECHO", "جسر المعنى: weight يطابق `سنجة الميزان` في شاهدين، والحدث المجمد يذكر الدقة والنفاذ.", "مدار 5: السنجة هي الوزن المعياري نفسه، لكن صلة الحدث المجمد بالدقة في القياس ألين من التطابق المعجمي؛ أغلقت ROOT-ECHO لا ROOT-TRACE."),
    174: R("زرد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زرد`: النفاذ الدقيق مع إمساك؛ وشواهد العربية في البلع والدرع لا yellow.", "فصلت لون الذهب الذي يذكره أصل الفارسية عن الزرد العربي؛ اللون لا يساوي البلع أو تداخل الحلق."),
    175: R("سفد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سفد`: نفاذ دقاق جافة مع ظهورها؛ لا يسمي white أو fair.", "ظهور ذرات فاتحة احتمال بصري عام، لا معنى البياض نفسه ولا شاهد مباشر عليه."),
    176: R("سبز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سبز`: امتداد دقيق متصل مع حدث الزاي؛ لا يسمي green.", "النبات الأخضر يمتد وينبت، لكن النمو فعل للنبات لا معنى اللون؛ وغياب الشاهد العربي لا يعوضه اتحاد الصورة."),
}


def pair_key(row: H.SweepRow) -> tuple[str, str]:
    return row.branch, H.norm_gloss(row.gloss)


def select_rows(data: dict, reading_text: str) -> tuple[list[SelectedRow], dict]:
    pairs = H.read_pairs(reading_text)
    all_sound = [
        P25.sound_row(rank, raw)
        for rank, raw in enumerate(data.get("sound_only") or [], 1)
    ]
    if len(all_sound) != 2304:
        raise AssertionError(f"تغير حجم حوض الصوت: {len(all_sound)}")
    prior = {row.rank for row in all_sound if P25.pair_was_read(row, pairs)}
    fresh: list[H.SweepRow] = []
    seen: set[tuple[str, str]] = set()
    internal_skips: list[int] = []
    for row in all_sound:
        key = pair_key(row)
        if row.rank in prior or key in seen:
            if row.rank > 103 and len(fresh) < 70:
                internal_skips.append(row.rank)
            continue
        seen.add(key)
        if row.rank <= 103:
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


def select_branch_entries(
    selected: list[SelectedRow], lexicon: dict
) -> tuple[dict[int, H.BranchEntry], dict[str, list[tuple[int, dict]]]]:
    grouped: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for index, entry in enumerate(lexicon["entries"]):
        grouped[H.clean(entry.get("word") or "")].append((index, entry))
    output: dict[int, H.BranchEntry] = {}
    for item in selected:
        row = item.row
        options = grouped.get(row.branch, [])
        if not options:
            raise AssertionError(f"لا مدخلة فرع للرسم {row.branch}")
        global_index, entry = max(
            options,
            key=lambda pair: H.entry_score(H.norm_gloss(row.gloss), pair[1]),
        )
        if global_index != EXPECTED_ENTRY_INDEX[row.rank]:
            raise AssertionError(f"انزلقت مدخلة الرتبة {row.rank}: {global_index}")
        homograph_index = 1 + next(
            i for i, pair in enumerate(options) if pair[0] == global_index
        )
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


def load_raw_entries(
    selected: list[SelectedRow], entries: dict[int, H.BranchEntry]
) -> dict[int, dict]:
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
        same_pos = [
            pair for pair in options
            if H.clean(pair[1].get("pos") or "") == entry.pos
        ]
        line_number, raw = max(
            same_pos or options,
            key=lambda pair: H.entry_score(
                H.norm_gloss(entry.gloss), {"en": P25.raw_gloss(pair[1])}
            ),
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
    zende = {index for index, _entry in grouped.get("زنده", [])}
    if zende != {3668, 3669}:
        raise AssertionError(f"تغير جرد مكون زنده: {sorted(zende)}")
    if grouped.get("ـگی"):
        raise AssertionError("ظهرت مدخلة مستقلة للاحقة ـگی؛ يلزم إعادة حكم فجوة الصرف")
    fan = tuple(H.FAN.rank("زنده", H.FAN.fan("زنده", "persian"), "persian"))
    if len(fan) != 9:
        raise AssertionError(f"تغيرت مروحة زنده: {len(fan)}")


def obstacle_for(review: Review) -> str:
    if review.verdict == "ROOT-TRACE":
        return "اكتملت أرجل الصوت والحدث والمدار اليدوي، ومعها شاهدان عربيان كلاسيكيان مستقلان."
    if review.verdict == "ROOT-ECHO":
        return "اكتمل الصوت والشاهدان، لكن صلة الحدث بالمعنى ألين من الأثر المحكم؛ أغلقت على درجة الصدى."
    if review.verdict == "LAW-GAP":
        return "طريق المعنى مسمى أو مفحوص، لكن مسار الصوت يحوي صفا غير مسمى؛ لم يصدر حكم موجب."
    if review.verdict == "COMPOUND-BOUNDARY":
        return "وقف الحكم عند حد المركب؛ لم تورث الصورة المجموعة حكم مكون ولم يخترع تفكيك."
    if review.verdict == "MORPHOLOGY-GAP":
        return "ثبت التفكيك، لكن اللاحقة الصرفية غابت كمدخلة مستقلة من لقطة الفرع؛ لم تسو من الحدس."
    if review.verdict == "TOOL-GAP":
        return "صف الحوض أسقط صامتا منطوقا؛ توقف العضو قبل الحكم ولم يعوض الصامت يدويا."
    if review.verdict == "OUT-OF-SCOPE":
        return "الشرح تعريف بعلم لا معنى معجميا؛ أحيل العضو إلى طبقة الأعلام المنفصلة."
    return "مسار الصوت قابل للفحص، لكن المدار لم يقم على معنى المدخلة؛ بقي المرشح مفتوحا."


def decide(item: SelectedRow) -> H.Decision:
    review = REVIEWS[item.row.rank]
    return H.Decision(
        review.candidate,
        review.verdict,
        H.state_for(review.verdict),
        review.orbit,
        obstacle_for(review),
    )


def decomposition_lines(item: SelectedRow, raw: dict) -> list[str]:
    if item.row.rank != 130:
        return []
    decomposition = P25.direct_from_plus(raw["etymology"])
    if not decomposition:
        raise AssertionError("غاب تفكيك From X + Y للرتبة 130")
    return [
        f"- تفكيك Kaikki الحصري من السطر الخام {raw['line']}: «{H.clip(raw['etymology'], 420)}».",
        "- قراءة المكونات المستقلة: `زنده` مدخلتان entries[3668,3669]؛ المختارة /zende/ «alive; living»، ومروحتها 9 مرشحين قُرئت كاملة. `ـگی` غائبة من branch-lexicons؛ سميت MORPHOLOGY-GAP ولم تستبدل بـ`گی` الحديثة.",
        "- الخطوة صفر: لم تقارن الصورة وحدة جذرية؛ قُرئ `زنده` وسميت فجوة اللاحقة.",
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
    match_count, classical_count, witnesses = P.classical_witnesses(
        decision.candidate, sense_map, quote_limit
    )
    etymology = raw["etymology"] or entry.etymology or "فجوة اشتقاق في مدخلة Kaikki الخام."
    lines = [
        f"### {item.heading}: `{row.branch}` /{entry.reading}/، رتبة sound_only {row.rank}",
        "- إصدار البروتوكول: RECOVERY-v2 (2026-08-16)؛ نموذج WO-B-PROBE-001.",
        (
            f"- مرجع الحوض: `phonetic-sweep-persian.json:sound_only[{row.rank - 1}]`؛ "
            "overlap=0؛ shared=فارغ؛ الترتيب مدخل قراءة لا حكم."
        ),
        f"- الكلمة في الفرع: فارسية `{row.branch}` /{entry.reading}/؛ الصنف `{entry.pos}`.",
        (
            f"- قراءة مداخل الرسم المتجانس: قُرئت {entry.homograph_count} مدخلة للرسم `{row.branch}`؛ "
            f"المختارة {entry.homograph_index}، entries[{entry.global_index}]؛ لم تؤخذ الأولى آليا."
        ),
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
            f"- الخطوة صفر: سُجل الهيكل `{'ـ'.join(row.skeleton)}` للفهرسة فقط، ولم يحول وصف العلم إلى معنى جذري.",
        ])
    else:
        lines.append(
            f"- الخطوة صفر: الهيكل `{'ـ'.join(row.skeleton)}`، صوامته {len(row.skeleton)}؛ "
            "طُرح المسمى فقط ولم يسقط صامت حدسا."
        )
    lines.extend([
        f"- درجة المقارنة: {H.comparison_degree(decision.candidate)}",
        (
            f"- المروحة المرتبة الكاملة: `fan_any_script.fan({row.branch}, persian)`؛ "
            f"العدد {len(ranked)}: {H.formatted_fan(ranked)}."
        ),
        f"- فحص المروحة كلها: قُرئت مواد {len(ranked)} مرشحا بـ`--max-chars 0`؛ لم يحكم عمود `best`.",
        f"- المقابل من اللسان: `{decision.candidate}`؛ من المروحة الحية.",
        f"- مسار الصوت والحد المسمى: {H.formatted_route(row, decision.candidate)}",
        f"- الحدث من السجل المجمد كما هو: {H.event_line(decision.candidate)}",
        f"- المعنى من قاموس الفرع بلا رتوش: «{entry.gloss}».",
        f"- طريق المعنى المسمى: {review.meaning_path}",
        (
            f"- مسح المعاني العربية: قُرئت {match_count} نتيجة لـ`{decision.candidate}` كاملة؛ "
            f"الشواهد العربية الكلاسيكية المستقلة={classical_count}؛ نُقل شاهدان أو سميت الفجوة:"
        ),
        f"  - الشاهد 1، {witnesses[0][0]}: «{witnesses[0][1]}»",
        f"  - الشاهد 2، {witnesses[1][0]}: «{witnesses[1][1]}»",
        f"- المدار المكتوب بخط اليد: {decision.orbit}",
        "- المصفاة: الأصل حاشية؛ لا يغلق النقل إلا بمانح سامي مسمى أو تصريح بالتعريب.",
        "- فصل المتجانسات والاقتراض: الحكم للمدخلة؛ لا توارث من متحد الرسم.",
        "- اليتم والإشعاع: الجرد والشاهدان أو فجوتاهما حاضرة؛ لا قرينة عدد.",
        "- جسور الاسترداد: الفرع؛ الأصل؛ الصفر؛ المروحة؛ الشبكة؛ الشواهد؛ المصفاة؛ المركب.",
        f"- عائق القرار أو تمامه: {decision.obstacle}",
        f"- ملاحظات العدستين: استرداد وتشكيك العضو؛ الجولة 27، {item.key}.",
        f"- حالة الإغلاق: {decision.state}.",
        f"- الحكم (استكشاف): {decision.verdict}.",
    ])
    return "\n".join(lines) + "\n"


def fit_card(
    item: SelectedRow,
    entry: H.BranchEntry,
    raw: dict,
    decision: H.Decision,
    ranked: tuple[tuple[str, float], ...],
    sense_map: dict[str, list[dict]],
) -> str:
    for quote_limit, etym_limit in (
        (230, 340), (180, 280), (130, 210), (90, 150),
        (60, 105), (35, 70), (20, 45), (12, 25), (8, 15),
    ):
        card = make_card(
            item, entry, raw, decision, ranked, sense_map,
            quote_limit, etym_limit,
        )
        if len(card.encode("utf-8")) < CARD_LIMIT:
            return card
    raise AssertionError(f"تجاوزت بطاقة {item.key} حد 5KB")


def validate_decisions(
    selected: list[SelectedRow],
    raw_entries: dict[int, dict],
    decisions: list[H.Decision],
    ranked_by_rank: dict[int, tuple[tuple[str, float], ...]],
    sense_map: dict[str, list[dict]],
) -> None:
    if set(REVIEWS) != set(SOUND_RANKS):
        raise AssertionError("جدول المدار اليدوي لا يغطي الرتب السبعين")
    exact = {
        item.row.rank for item in selected
        if P25.direct_from_plus(raw_entries[item.row.rank]["etymology"])
    }
    if exact != EXACT_DECOMPOSITIONS:
        raise AssertionError(f"تغيرت أسطر From X + Y المباشرة: {sorted(exact)}")
    traces = {134, 153}
    echoes = {104, 105, 173}
    if {rank for rank, review in REVIEWS.items() if review.verdict == "ROOT-TRACE"} != traces:
        raise AssertionError("تغيرت مواضع ROOT-TRACE اليدوية")
    if {rank for rank, review in REVIEWS.items() if review.verdict == "ROOT-ECHO"} != echoes:
        raise AssertionError("تغيرت مواضع ROOT-ECHO اليدوية")
    for item, decision in zip(selected, decisions):
        row = item.row
        candidates = {candidate for candidate, _score in ranked_by_rank[row.rank]}
        if decision.candidate not in candidates:
            raise AssertionError(f"مرشح الرتبة {row.rank} خارج المروحة الحية")
        complete = H.route_complete(row, decision.candidate)
        _count, coverage, _witnesses = P.classical_witnesses(
            decision.candidate, sense_map, 60
        )
        if decision.verdict == "LAW-GAP" and complete:
            raise AssertionError(f"LAW-GAP بلا صف مفقود في الرتبة {row.rank}")
        if decision.verdict in {"OPEN-CANDIDATE", "ROOT-TRACE", "ROOT-ECHO"} and not complete:
            raise AssertionError(f"حكم بمسار ناقص في الرتبة {row.rank}: {decision.verdict}")
        if decision.verdict in {"ROOT-TRACE", "ROOT-ECHO"}:
            if coverage < 2 or H.event_line(decision.candidate).startswith("لا حدث"):
                raise AssertionError(f"حكم صادر بلا حدث وشاهدين في الرتبة {row.rank}")
        if not REVIEWS[row.rank].meaning_path.startswith(("جسر المعنى:", "نص الحدث المجمد")):
            raise AssertionError(f"طريق المعنى غير مسمى في الرتبة {row.rank}")


def validate_text(
    selected: list[SelectedRow], texts: list[str], prior_pairs: set[tuple[str, str]]
) -> None:
    if len(selected) != 70 or BATCH_SIZES != (35, 35):
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = re.findall(r"^### (WO-B-R27-SOUND-\d{5}):", joined, re.MULTILINE)
    if headings != [item.heading for item in selected]:
        raise AssertionError("معرفات الجولة 27 لا تطابق النافذة")
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
        "نموذج WO-B-PROBE-001", "قراءة مداخل الرسم المتجانس",
        "المروحة المرتبة الكاملة", "الحدث من السجل المجمد",
        "طريق المعنى المسمى", "المدار المكتوب بخط اليد",
        "الشاهد 1", "الشاهد 2", "الحكم (استكشاف)",
    )
    for item, card in zip(selected, texts):
        if len(card.encode("utf-8")) >= CARD_LIMIT:
            raise AssertionError(f"تجاوزت {item.key} حد 5KB")
        if any(field not in card for field in required):
            raise AssertionError(f"نقص حقل من بطاقة {item.key}")
    exact_card = texts[SOUND_RANKS.index(130)]
    if "تفكيك Kaikki الحصري" not in exact_card or "قراءة المكونات المستقلة" not in exact_card:
        raise AssertionError("لم تقرأ مكونات الرتبة 130 استقلالا")
    for rank in BLOCKED_BOUNDARIES:
        card = texts[SOUND_RANKS.index(rank)]
        if "حد المركب غير المفكك" not in card or "بلا مكونات مخترعة" not in card:
            raise AssertionError(f"لم يغلق حد المركب في الرتبة {rank}")
    for rank in TOOL_GAPS:
        card = texts[SOUND_RANKS.index(rank)]
        if "عطب الهيكل" not in card or "لا حكم من هيكل ناقص" not in card:
            raise AssertionError(f"لم يسم عطب الهيكل في الرتبة {rank}")


def report_section(
    selected: list[SelectedRow],
    decisions: list[H.Decision],
    sizes: list[int],
    stats: dict,
) -> str:
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
            f"## الجولة السابعة والعشرون، دفعة sound_only رقم {number}", "",
            f"- الوقت: {now}، Africa/Cairo.",
            f"- رُشح وكُتب: {len(batch)}؛ المواضع المقروءة المتجاوزة داخل المدى: {skipped}.",
            f"- المواضع: من {batch[0].heading} إلى {batch[-1].heading}.",
            f"- توزيع الأحكام: {distribution}.",
            "- طريق المعنى: سمي من جسر معنى صريح أو من نص الحدث المجمد في كل بطاقة.",
            "- المدار: كتب يدويا لكل عضو، وفصلت الأصداء اللينة عن الآثار المحكمة.",
            "- المروحة: ولدت حية كاملة ورتبت بالأوزان، ومسحت مواد جميع مرشحيها بلا قص للحقل المصدر.",
            "- المتجانسات: قرئت كل مداخل الرسم، وسجل العدد ورقم المدخلة المختارة في كل بطاقة.",
            "- المركب: لم يقبل إلا سطر From X + Y النهائي المباشر؛ لم يخترع مكون.",
            "- التحقق البنيوي: المعرفات فريدة؛ لا بطاقة فوق 5KB؛ لا شرطة طويلة؛ الأرقام غربية والنص NFC.",
            f"- آخر موضع في الدفعة: {batch[-1].heading}، `{batch[-1].row.branch}`.",
            "",
        ])
    total = Counter(decision.verdict for decision in decisions)
    distribution = "؛ ".join(f"{key}={total[key]}" for key in sorted(total))
    max_size = max(sizes)
    max_item = selected[sizes.index(max_size)]
    traces = [
        item.heading for item, decision in zip(selected, decisions)
        if decision.verdict == "ROOT-TRACE"
    ]
    echoes = [
        item.heading for item, decision in zip(selected, decisions)
        if decision.verdict == "ROOT-ECHO"
    ]
    lines.extend([
        "## حصيلة الجولة السابعة والعشرين", "",
        f"- حمل `persian.md` مرة واحدة؛ أزواج WO-B المقروءة={stats['pair_count']}؛ المتجاوز داخل النافذة={', '.join(map(str, stats['skipped']))}.",
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- نطاق الصوت الجديد: الرتب 104-176 بعد آخر معرف في الجولة السابقة، مع إسقاط الأزواج الثلاثة المقروءة فقط.",
        f"- الآثار الجذرية ذات الأرجل المحكمة والشاهدين: {', '.join(traces)}.",
        f"- الأصداء الجذرية الموسومة بلين رجل الحدث أو المدار: {', '.join(echoes)}.",
        "- إنقاذ دلالي خلف فجوة قانون: S00125 `چاقو` مع `شق`، وS00146 `چین` مع `شن`؛ لم يرقيا مع نقص صف چ.",
        "- فجوات الأداة: S00140 `شاه` وS00147 `ماه` لأن الحوض أسقط هاء منطوقة؛ لم تعوضا حدسا.",
        "- التفكيك: S00130 مباشر لكن لاحقة `ـگی` غائبة من معجم الفرع؛ S00136 وS00148 وقفا عند حد غير مؤهل.",
        "- أحواض `nucleus-sweep-*.json` الحالية على القرص فُحصت قبل الجولة؛ رتل الجولة لا يقرأ منها، ومدخله المباشر `phonetic-sweep-persian.json`.",
        f"- أكبر بطاقة: {max_size} بايت، {max_item.heading}؛ كل البطاقات دون 5KB.",
        "- لم تفعل طبقة البرهان، ولم يبن ملف مشترك، ولم يقع ship، ولم يستعمل git.",
        "", f"<!-- {MARKER}:END -->", "", DONE_LINE,
    ])
    return "\n".join(lines)


def validate_existing(reading_text: str, report_text: str) -> None:
    match = re.search(
        rf"<!-- {re.escape(MARKER)}:START -->(.*?)<!-- {re.escape(MARKER)}:END -->",
        reading_text,
        re.DOTALL,
    )
    if not match:
        raise AssertionError("محضر الجولة موجود وبطاقاتها غائبة")
    headings = re.findall(
        r"^### (WO-B-R27-SOUND-\d{5}):", match.group(1), re.MULTILINE
    )
    expected = [f"WO-B-R27-SOUND-{rank:05d}" for rank in SOUND_RANKS]
    if headings != expected:
        raise AssertionError("مقطع الجولة 27 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(DONE_LINE):
        raise AssertionError("سطر DONE27 ليس خاتمة التقرير")


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
        print("ROUND27 ALREADY PRESENT AND VALID")
        print(DONE_LINE)
        return 0

    data = json.loads(SWEEP.read_text(encoding="utf-8"))
    selected, stats = select_rows(data, reading_text)
    prior_pairs = H.read_pairs(reading_text)
    lexicon = json.loads(LEXICON.read_text(encoding="utf-8"))
    entries, grouped = select_branch_entries(selected, lexicon)
    raw_entries = load_raw_entries(selected, entries)
    validate_components(grouped)

    ranked_by_rank = {
        item.row.rank: H.full_ranked_fan(item.row) for item in selected
    }
    roots = {
        candidate
        for ranked in ranked_by_rank.values()
        for candidate, _score in ranked
    }
    roots.update(review.candidate for review in REVIEWS.values())
    sense_map = H.SENSES.matches_for_roots(H.SENSES.DEFAULT_RESOURCES, roots, None)
    decisions = [decide(item) for item in selected]
    validate_decisions(selected, raw_entries, decisions, ranked_by_rank, sense_map)
    texts = [
        fit_card(
            item, entries[item.row.rank], raw_entries[item.row.rank], decision,
            ranked_by_rank[item.row.rank], sense_map,
        )
        for item, decision in zip(selected, decisions)
    ]
    validate_text(selected, texts, prior_pairs)
    sizes = [len(card.encode("utf-8")) for card in texts]

    reading_append = (
        f"\n\n<!-- {MARKER}:START -->\n\n"
        "## الجولة السابعة والعشرون: متابعة حوض sound_only (2026-08-25)\n\n"
        "- النطاق: 70 عضوا طازجا بعد WO-B-R26-SOUND-00103؛ من الرتبة 104 إلى 176 مع تجاوز 127 و128 و139 لأن أزواجها مقروءة؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ طريق المعنى مسمى، والمدار اليدوي حاسم، والأصداء مفصولة عن الآثار المحكمة.\n\n"
        + "\n".join(texts[:35])
        + "\n## الدفعة الثانية: متابعة sound_only بعد الرتبة 140\n\n"
        + "\n".join(texts[35:])
        + f"\n<!-- {MARKER}:END -->\n"
    )
    report_append = "\n" + report_section(selected, decisions, sizes, stats) + "\n"
    reading_append = unicodedata.normalize("NFC", reading_append)
    report_append = unicodedata.normalize("NFC", report_append)
    if "—" in reading_append + report_append or re.search(
        r"[۰-۹٠-٩]", reading_append + report_append
    ):
        raise AssertionError("فشل حارس الشرطة أو الأرقام قبل الكتابة")
    combined_reading = reading_text + reading_append
    combined_report = report_text + report_append
    validate_existing(combined_reading, combined_report)

    counts = Counter(decision.verdict for decision in decisions)
    print("ROUND27 READY")
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
    print("ROUND27 WRITTEN")
    print(DONE_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
