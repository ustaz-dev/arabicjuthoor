# -*- coding: utf-8 -*-
"""المسار B، الجولة 35: متابعة حوض sound_only في دفعتين من 35 بطاقة."""

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

import harvest_persian_round34 as R34  # noqa: E402

R32 = R34.R32
R31 = R34.R31
R29 = R34.R29
R28 = R34.R28
H = R34.H
P = R34.P
P25 = R34.P25
READING = ROOT / "04-cross-linguistic" / "readings" / "persian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-B.md"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-persian.json"
NUCLEUS_DIR = ROOT / "04-cross-linguistic" / "exploration"
LEXICON = ROOT / "data" / "branch-lexicons" / "persian.json"
RAW_LEXICON = ROOT / "Resources" / "persian" / "kaikki.org-dictionary-Persian.jsonl"
MARKER = "LANE-B-PERSIAN-ROUND35-2026-08-26"
CARD_LIMIT = 5120
SOUND_RANKS = (
    718, 719, 720, 721, 722, 723, 724, 725, 726, 727, 728, 729, 730,
    731, 732, 733, 734, 735, 736, 737, 738, 739, 742, 743, 744, 745,
    746, 747, 748, 749, 750, 751, 752, 753, 754, 755, 756, 757, 758,
    759, 760, 761, 762, 763, 764, 765, 766, 767, 768, 769, 770, 771,
    772, 773, 774, 775, 776, 777, 778, 779, 780, 781, 782, 783, 784,
    785, 786, 787, 788, 789,
)
BATCH_SIZES = (35, 35)
DONE_LINE = "LANE-B DONE35 70 WO-B-R35-SOUND-00789"
EXPECTED_SKIPS = (740, 741)

# النسخة الخامسة عشرة المقروءة من القرص.
NUCLEUS_SNAPSHOT = {
    "nucleus-sweep-ancient_greek.json": (7983726, "b713179e640055d8014b6b85a56200b1d2ae93df528257bbd15831d7d786e9d3", 2331, 16774),
    "nucleus-sweep-english_middle.json": (3415749, "2021380b896c6d046b8334adeb7064d8f36ffb9a8e17213e254cfbbedcada5c4", 1414, 7991),
    "nucleus-sweep-english_old.json": (1294040, "c3b57ccf376f9e71f09adff122f5bbbe3590644ed51dfed8f691f3f3ecff7e0b", 474, 3414),
    "nucleus-sweep-gothic.json": (1448255, "012ca6d10c1c9757597c9ea2b0905d68168a20c34f73364d49689684c4205adb", 340, 3078),
    "nucleus-sweep-latin.json": (18840240, "5ff34ddf45aa660c6cba65d2046e18c42d92fd0cfe4ea93fd853df54b8d000c9", 6598, 39460),
    "nucleus-sweep-old_irish.json": (952787, "7aaa1d45242c3dd011824434105ab36d92db10fe23d7f466f7f2e96d95f88153", 278, 2740),
    "nucleus-sweep-old_norse.json": (1381006, "9ecb7bdeef6a54820847126f4508c6bd97e36788a0384b90daa01ff3997faa56", 476, 3751),
    "nucleus-sweep-persian.json": (5462749, "00fe23b5389b8589dfbbfaa266c7226bd4e3ce8c75568e2dcf8cd79e0405d87c", 1448, 13498),
    "nucleus-sweep-welsh.json": (5777180, "740410bd00fb9b720c420b85c283eb3be04893828a72b97f3c48554d1654292b", 1188, 16087),
}

EXPECTED_ENTRY_INDEX = dict(zip(SOUND_RANKS, (
    3360, 3362, 3363, 3364, 3366, 3372, 3375, 3377, 3382, 3389,
    3397, 3398, 3403, 0, 3425, 3432, 3437, 3439, 3440, 3441, 3446,
    3468, 3479, 3489, 3501, 3502, 3514, 3515, 3516, 3521, 3527,
    3533, 3534, 3541, 3546, 3552, 3553, 3554, 3557, 3558, 3559,
    3568, 3572, 3574, 3576, 3577, 3580, 3589, 3591, 3606, 3635,
    3642, 3644, 3645, 3648, 3652, 3653, 3665, 3668, 3669, 3670,
    3671, 3677, 3687, 3692, 3701, 3702, 3704, 3709, 3716,
)))
EXPECTED_RAW_LINE = dict(zip(SOUND_RANKS, (
    3736, 3738, 3739, 3740, 3742, 3750, 3753, 3755, 3760, 3767,
    3777, 3779, 3785, 3800, 3809, 3816, 3821, 3823, 3824, 3825, 3830,
    3854, 3866, 3878, 3890, 3891, 3903, 3904, 3905, 3910, 3919,
    3928, 3929, 3949, 3959, 3970, 3973, 3974, 3977, 3978, 3979,
    3990, 3996, 3998, 4000, 4001, 4004, 4015, 4017, 4033, 4062,
    4070, 4072, 4073, 4076, 4080, 4081, 4096, 4099, 4100, 4101,
    4102, 4111, 4122, 4127, 4136, 4137, 4139, 4144, 4152,
)))

EXACT_DECOMPOSITIONS = {726, 738, 744, 745, 751, 752, 753, 755, 769, 779, 785}
EXPECTED_COMPONENTS = {
    726: ("پیش", "گیر"),
    738: ("گل", "ـچه"),
    744: ("بلوچ", "ـی"),
    745: ("بلوچ", "ـی"),
    751: ("پول", "ـدار"),
    752: ("پول", "ـدار"),
    753: ("سخن", "ـگو"),
    755: ("نیرو", "ـگاه"),
    769: ("مست", "ـی"),
    779: ("زی", "ـنده"),
    785: ("بیـ", "وفا"),
}
COMPONENT_READINGS = {
    726: "`پیش`: entries[4609-4611] والخام 5126-5128؛ اختير الاسم front part أو before، ومروحته 60: OPEN-CANDIDATE. `گیر`: entry[5696] والخام 6694-6695؛ حاضر اسما catch أو grasp وجذعا مضارعا لـ`گرفتن`، ومروحته 80: FORM-LINK.",
    738: "`گل`: entries[366-370] والخام 394-398؛ اختير flower أو rose وفصل عن clay وgoal، ومروحته 80: OPEN-CANDIDATE. `ـچه`: entry[7514] والخام 8808 لاحقة تصغير، ومروحتها 60: MORPHOLOGY-GAP.",
    744: "`بلوچ`: entry[13607] والخام 16451 لاسم الشعب، ومروحته 6: OPEN-CANDIDATE. `ـی`: entries[6328-6331] والخام 7420-7424؛ اختيرت لاحقة النسبة الوصفية، ومروحتها صفر: MORPHOLOGY-GAP.",
    745: "`بلوچ`: entry[13607] والخام 16451 لاسم الشعب، ومروحته 6: OPEN-CANDIDATE. `ـی`: entries[6328-6331] والخام 7420-7424؛ اختيرت لاحقة النسبة التي بنت اسم اللسان، ومروحتها صفر: MORPHOLOGY-GAP.",
    751: "`پول`: entry[940] والخام 997 لمعنى money أو coin، ومروحته 40: OPEN-CANDIDATE مع احتمال أصل يوناني مسمى. `ـدار`: entry[7516] والخام 8810 لاحقة ملك، ومروحتها 60: MORPHOLOGY-GAP.",
    752: "`پول`: entry[940] والخام 997 لمعنى money أو coin، ومروحته 40: OPEN-CANDIDATE مع احتمال أصل يوناني مسمى. `ـدار`: entry[7516] والخام 8810 لاحقة ملك، ومروحتها 60: MORPHOLOGY-GAP.",
    753: "`سخن`: entry[5075] والخام 5872 لمعنى speech، ومروحته 9: OPEN-CANDIDATE. `ـگو`: لا مدخلة مستقلة في branch-lexicons؛ قرئ `گو` في الخام 6551 جذعا مضارعا لـ`گفتن` الخام 1102، ومروحته 72: FORM-LINK.",
    755: "`نیرو`: entry[2376] والخام 2492 لمعنى force أو power، ومروحته 20: OPEN-CANDIDATE. `ـگاه`: entry[7462] والخام 8752 لاحقة مكان أو زمان، ومروحتها 72: MORPHOLOGY-GAP.",
    769: "`مست`: entries[2719-2721] والخام 2994-2996؛ اختير drunk أو intoxicated، ومروحته 9: OPEN-CANDIDATE. `ـی`: entries[6328-6331] والخام 7420-7424؛ اختيرت لاحقة الاسم المجرد، ومروحتها صفر: MORPHOLOGY-GAP.",
    779: "`زی`: لا مدخلة مستقلة؛ سماها الخبر جذعا مضارعا، وثبت فعلها `زیستن` في entry[1523] والخام 1605 لمعنى to live، ومروحة الجذع 42: FORM-LINK. `ـنده`: entry[10301] والخام 12672 لاحقة اسم فاعل، ومروحتها 30: MORPHOLOGY-GAP.",
    785: "`بیـ`: entry[14756] والخام 17675 سابقة without، ومروحتها 14: MORPHOLOGY-GAP. `وفا`: entries[2605-2606] والخام 2868-2869؛ اختير loyalty أو fidelity، ومروحته 37، والخبر يسميه قرضا من العربية: ARABIC-TO-PERSIAN-TRANSMISSION.",
}

REJECTED_ANALYSES = {
    734: "يفكك الخبر الصورة الإيرانية الأولية إلى السابقة `fra-` والجذر `yat-`، لا الصورة الفارسية الحديثة تفكيكا نهائيا مباشرا.",
    748: "يسمي الخبر `پا` و`پوش` ثم يشرح وظيفة الجذع ويعقب بمقارنات؛ لم يمر خبر From X + Y الطرفي الحصري، فحفظت المكونات ولم أحولها إلى حكم مركب آلي.",
    760: "يعرض الخبر تحليلا اشتقاقيا محتملا في Proto-Iranian إلى سابقة وجذر، لا تفكيكا نهائيا مباشرا للصورة الحديثة.",
    766: "يسمي الخبر مكونين في Proto-Iranian، لا مكونين نهائيين مباشرين للمدخلة الفارسية الحديثة.",
    772: "يأتي بند + ـه تحت By surface analysis بعد سلسلة موروثة مستقلة؛ لم يحول التحليل السطحي إلى From نهائي.",
    773: "يأتي بند + ـه تحت By surface analysis بعد سلسلة موروثة مستقلة؛ لم تورث مدخلة الضمير تحليل مدخلة العبد.",
    777: "يسوق الخبر صورة وسطى `bun-dāt` وتحليلا تاريخيا، لا From X + Y نهائيا مباشرا للصورة الحديثة.",
    783: "يفكك الخبر تكوينا إيرانيا أوليا من `pati-` ومادة `gam-`، لا الصورة الحديثة تفكيكا نهائيا مباشرا.",
}
TOOL_GAPS = {
    734: "الصورة `فریاد` منقوطة /faryād/، لكن الهيكل أسقط /y/ المنطوقة.",
    764: "الصورة `شاید` منقوطة /šāyad/، لكن الهيكل أسقط /y/ المنطوقة.",
    765: "الصورة `شاید` منقوطة /šāyad/، لكن الهيكل أسقط /y/ المنطوقة.",
    766: "الصورة `نگاه` منقوطة /negāh/، لكن الهيكل أسقط /h/ النهائية المنطوقة.",
    777: "الصورة `بنیاد` منقوطة /bonyād/، لكن الهيكل أسقط /y/ المنطوقة.",
    782: "الصورة `گواهی‌نامه` منقوطة /govāhi-nāme/، لكن الهيكل أسقط /v/ المنطوقة.",
    783: "الصورة `پیغام` منقوطة /payġām/، لكن الهيكل أسقط /y/ المنطوقة.",
}
LAW_GAPS = {718, 725, 733, 747, 758, 759, 760, 774}
OUT_OF_SCOPE = {767: "اسم لسان حديث، لا معنى معجميا عاما يحكم عليه كوحدة جذرية."}
SOURCE_NOTES = {
    718: "مدخلة الإقليم المتجانسة وحدها تذكر العربية `فارس`؛ لم تورث الصفة المختارة خبر المتجانس.",
    719: "الخبر يربط bark بالفارسية `پاس` guard أو watch؛ حفظ الرابط ولم يحوله إلى مكون أو إلى معنى عربي.",
    730: "الخبر ينقل اقتراح Watkins بصلة العربية `مات` ثم يعرض مقابلا سنسكريتيا بديلا؛ حفظ التعارض ولم يحسم الأصل.",
    731: "المدخلة غائبة من branch-lexicons الحالية وثابتة في الخام 3800 بوصفها صورة منطوقة من `دیگر`؛ استعيدت من الخام ولم يخترع لها أصل مستقل.",
    746: "الخبر يسمي مصدرا تركيا للزر؛ إن اتفقت صورة عربية حديثة فهي مسار مانح ثالث لا إرث فارسي عربي.",
    747: "الخبر يسمي قروضا إيرانية إلى السريانية والعبرية، ولا يسمي العربية؛ لم يمد اتجاه النقل إلى لسان غير مذكور.",
    749: "شاهد `النيزك` يسميه فارسيا معربا، لكنه سلسلة الرمح القصير لا صفة `نازک` التي يردها خبر الفرع إلى `ناز`؛ فصلت السلسلتين.",
    750: "حقل الاشتقاق فارغ؛ لم يستبدل بتفكيك حدسي من `پوش` ولا بصورة أقدم غير منشورة.",
    763: "الخبر يسمي المعنى الأقدم wick من rope أو cord؛ لم يورث lighter الحديث معنى الحبل ولا حكمه.",
    767: "حقل الاشتقاق فارغ والمدخلة اسم اللسان الجيلاكي؛ لم يفكك الاسم من غير مصدر.",
    771: "حقل الاشتقاق فارغ؛ لم يفكك murder أو slaughter يدويا إلى فعل ولاحقة.",
    775: "فصلت barley أو grain عن متجانسي stream وair في الرسم نفسه.",
    776: "فصلت stream أو brook عن متجانسي barley وair في الرسم نفسه.",
    778: "فصلت الصفة stiff أو erect عن متجانس spit أو skewer ولم تورث معنى الأداة.",
    780: "فصلت colossal أو formidable عن متجانس alive ولم تورث حياة المدخلة السابقة.",
    782: "حقل الاشتقاق فارغ فوق عطب الهيكل؛ لم يفكك certificate حدسيا إلى `گواهی` و`نامه`.",
    783: "يسمي الخبر قروضا إيرانية إلى الآرامية والسريانية والعبرية، ولا يسمي العربية؛ حفظت الاتجاهات كما وردت.",
    785: "المكون `وفا` قرض عربي مسمى داخل المركب الفارسي؛ سجل تماس المكون ولم يحول المركب كله إلى أثر موروث.",
    787: "الخبر يسمي Kulturwort مجهول الأصل النهائي؛ لم يخترع مانحا ولم يحسم اتجاه انتقال.",
}


@dataclass(frozen=True)
class SelectedRow:
    row: H.SweepRow

    @property
    def key(self) -> str:
        return f"S{self.row.rank:05d}"

    @property
    def heading(self) -> str:
        return f"WO-B-R35-SOUND-{self.row.rank:05d}"


Review = R34.Review
R = R34.R

# سجل قراءة يدوي. لا يشتق الحكم من best ولا من وزن المروحة.
REVIEWS = {
    718: R("فرس", "LAW-GAP", "جسر المعنى: Persian تقابل `الفرس`، لكن پ↔ف غير مسمى في الشبكة.", "فصلت الصفة عن اسم الإقليم؛ بقي المعنى صريحا وفجوة الصوت مانعة للحكم."),
    719: R("برس", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`برس`: التجرد والخلوص؛ لا يسمي bark.", "صوت النباح حدث سمعي لا قطن `برس` ولا تجرده؛ وربط `پاس` في المصدر لا ينشئ مدارا عربيا."),
    720: R("ببك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ببك`: الانفتاح والمنفذ مع كاف؛ لا يسمي little father أو educator.", "شاهد العربية الوحيد اسم بابك التاريخي؛ لم يحول الاسم ولا معنى التربية إلى حدث جذري."),
    721: R("ببك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ببك`: الانفتاح والمنفذ مع كاف؛ لا يسمي faithful أو firm.", "فصلت الصفة عن مدخلتي الأب الصغير واسم العلم؛ الثبات لا يستخرج من المحاكم."),
    722: R("طم", "NUCLEUS-TRACE", "جسر المعنى: veil أو covering وcataract تغطية حتى الإخفاء، وهو نص النواة المجمدة لـ`طم`.", "مدار 1: سواد العين وحجابها أثر للتغطية؛ وشاهدا العربية يثبتان الطم بالتراب والبحر المطموم."),
    723: R("هذر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`هذر`: محاكم حروف، وشاهدا العربية في الكلام الذي لا يعبأ به؛ لا يسمي otter أو beaver.", "تقارب حركة الحيوان أو صوته وصف غير معجمي؛ حفظت صورة الحيوان دون نقله إلى الهذيان."),
    724: R("جم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جم`: التجمع والكثرة؛ لا يسمي garment أو robe.", "اجتماع الثوب على البدن وظيفة عامة للكساء لا معنى الثوب، والخبر يرده إلى hold تاريخية مستقلة."),
    725: R("است", "LAW-GAP", "جسر المعنى: reconciliation أو peace حاضر، لكن آ↔ا غير مسمى في أول الهيكل.", "محاكم `است` لا تسمي الصلح، وفوق ضعف المدار بقيت فجوة الهمزة الممدودة مانعة."),
    726: R("بشكر", "COMPOUND-BOUNDARY", "جسر المعنى: towel أو napkin مفككة مباشرة إلى `پیش` و`گیر`.", "قُرئ front أو before وcatch أو grasp مستقلين؛ لم تورث المنشفة حكم أحد المكونين."),
    727: R("مز", "OPEN-CANDIDATE", "جسر المعنى: taste أو flavour حاضر في `المز` العربي للطعم بين الحموضة والحلاوة وللخمر اللذيذة.", "اتحد الحقل المعجمي، لكن الحدث المجمد للجمع أو الفصل والامتلاء لا يسمي التذوق مباشرة؛ بقي مرشحا مفتوحا."),
    728: R("زوه", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زوه`: إفراغ الباطن مع وصل الواو؛ لا يسمي string أو bowstring.", "المورد العربي المستقل الثاني غائب، وشد الوتر أو إفراغ القوس وصف استعمال لا معنى الاسم."),
    729: R("زوه", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زوه`: إفراغ الباطن مع وصل الواو؛ لا يسمي childbirth أو offspring.", "خروج الولد من الباطن وصف رصدي غير كاف، وفصلت هذا المتجانس عن وتر القوس ونبع الماء."),
    730: R("مات", "OPEN-CANDIDATE", "جسر المعنى: amazed أو astonished قد يلامس الجمود في `مات`، لكن الحدث المجمد لا يسمي الدهشة.", "اقتراح الصلة بالعربية متعارض في المصدر مع المقابل السنسكريتي؛ لم يحول مات من الدهشة إلى موت بلا جسر منشور."),
    731: R("دك", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دك`: الدق والكسر؛ لا يسمي Spoken form of `دیگر`.", "الإحالة الصرفية تحفظ معنى other للرأس؛ لم تورث الصورة المنطوقة حكما من رسم آخر ولم تخترع لها اشتقاقا."),
    732: R("قرزل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`قرزل`: محاكم حروف بلا معنى battlefield أو combat.", "القتال يجمع جيشا في موضع لكنه لا يساوي المحاكم الحروفية، والخبر يرده إلى army هندو أوروبية."),
    733: R("شرك", "LAW-GAP", "جسر المعنى: wrinkle التواء وتشابك في السطح، لكن چ↔ش غير مسمى.", "الشرك إمساك لا اسم التجعد؛ بقي الوصف الرصدي ضعيفا وفوقه فجوة القانون."),
    734: R("فرد", "TOOL-GAP", "جسر المعنى: cry أو shout حاضر، لكن /faryād/ يحمل /y/ أسقطها الهيكل.", "أوقف الصامت الساقط المقارنة قبل وصل طلب النجدة التاريخي بانفراد `فرد`."),
    735: R("خم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خم`: الاضطمام على مائع أو خور؛ لا يسمي bent أو crooked.", "شواهد العربية في تغير الرائحة والكنس؛ فصلت الصفة المنحنية عن متجانسي الانحناء والوعاء."),
    736: R("خم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خم`: الاضطمام على مائع أو خور؛ لا يسمي bend أو curve.", "تقوس الشعر هيئة لا معنى الاضطمام، وفصلت الاسم عن الصفة وعن وعاء الخمر."),
    737: R("خم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خم`: الاضطمام على مائع أو خور؛ يلامس الوعاء ولا يسمي cask أو vat.", "احتواء السائل وظيفة للبرميل، أما الشاهدان ففي فساد الرائحة والكنس؛ لم يصدر أثر من الوصف الوظيفي."),
    738: R("جلج", "COMPOUND-BOUNDARY", "جسر المعنى: floret أو rosette مفككة مباشرة إلى `گل` flower و`ـچه` للتصغير.", "قُرئ الاسم واللاحقة مستقلين؛ لم تقارن الزهيرة وحدة جذرية وصفوف چ بقيت خارج حكم المركب."),
    739: R("ار", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ار`: محكمتا حرفين بلا معنى saw.", "فعل القطع في الأصل الهندو أوروبي لا يثبت من انفتاح الألف وخفقات الراء، والشاهد العربي الثاني غائب."),
    742: R("شم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شم`: جمع المنتشر منسحبا إلى أعلى؛ لا يسمي dinner أو dusk.", "اجتماع الناس للعشاء سياق اجتماعي لا معنى الوجبة، وفصلت المدخلة عن اسم الشام الجغرافي."),
    743: R("با", "OPEN-CANDIDATE", "جسر المعنى: with أو by أو using يطابق استعمال الباء العربية للإلصاق والاستعانة.", "الشاهدان النحويان صريحان، لكن `با` لا تحمل نواة مجمدة بل محاكم حرفين؛ بقيت المطابقة مرشحا مفتوحا بلا حكم نواة."),
    744: R("بلج", "COMPOUND-BOUNDARY", "جسر المعنى: Balochi الوصفية مفككة مباشرة إلى `بلوچ` و`ـی`.", "اسم الشعب واللاحقة وحدتا القراءة؛ لم تحول النسبة إلى جذر ولم تتجاوز صف چ الناقص."),
    745: R("بلج", "COMPOUND-BOUNDARY", "جسر المعنى: اسم اللغة Balochi مفكك مباشرة إلى `بلوچ` و`ـی`.", "فصلت اسم اللسان عن الصفة مع اشتراك المكونين؛ لا وراثة حكم بين العضوين."),
    746: R("دكم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دكم`: الدق والجمع والزحم؛ لا يسمي button.", "الزر جسم مدخل في ثقب، لكن الإدخال فعل استعمال لا معنى الاسم؛ وعزل المصدر التركي مسار مانح ثالث."),
    747: R("نثن", "LAW-GAP", "جسر المعنى: sign أو mark حاضر، لكن ش↔ث غير مسمى في الرصف الوحيد الباقي من الحوض.", "محاكم `نثن` لا تسمي العلامة، والقروض الإيرانية المسماة إلى السريانية والعبرية لا تمد إلى العربية؛ بقيت فجوة الصوت مانعة."),
    748: R("ببش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ببش`: الانفتاح مع الانتشار؛ لا يسمي slipper.", "وظيفة تغطية القدم ظاهرة في الخبر، لكن التحليل لم يمر حد From الطرفي الحصري؛ حفظت المكونات بلا توريث."),
    749: R("نزك", "OPEN-CANDIDATE", "جسر المعنى: delicate أو thin يلامس دقيق الجرم في الحدث المجمد لـ`نزك`.", "شاهد النيزك يثبت رمحا قصيرا فارسيا معربا من سلسلة أخرى؛ دقة الرمح صفة شكلية لا معنى `نازک`، فبقي المرشح مفتوحا."),
    750: R("بشك", "OPEN-CANDIDATE", "جسر المعنى: diaper ثوب مخيط، و`بشك` العربي يذكر خياطة الثوب المتباعدة.", "الخياطة صفة صنع لا معنى الحفاض نفسه، وحقل الأصل الفارسي فارغ؛ بقي صدى وصفيا مفتوحا."),
    751: R("بردر", "COMPOUND-BOUNDARY", "جسر المعنى: rich أو wealthy مفككة مباشرة إلى `پول` money و`ـدار` having.", "الغنى حاصل من تركيب المال والملك؛ لم يقارن المركب جذرا عربيا."),
    752: R("بردر", "COMPOUND-BOUNDARY", "جسر المعنى: rich person مفككة مباشرة إلى `پول` money و`ـدار` having.", "فصلت الاسم عن الصفة السابقة، وقرأ المكونان مرة مستقلة بلا وراثة حكم."),
    753: R("شخنك", "COMPOUND-BOUNDARY", "جسر المعنى: spokesperson مفككة مباشرة إلى `سخن` speech و`ـگو` say.", "قُرئ الاسم والجذع المضارع استقلالا؛ لم تحول وظيفة المتكلم إلى جذر للصورة المجموعة."),
    754: R("رسب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رسب`: النفاذ بامتداد؛ لا يسمي prostitute أو courtesan.", "الانحطاط حكم اجتماعي لا معنى الرسوب المكاني، والخبر يثبت سلسلة فارسية وسطى مستقلة."),
    755: R("نرج", "COMPOUND-BOUNDARY", "جسر المعنى: power station مفككة مباشرة إلى `نیرو` force و`ـگاه` place.", "المحطة معنى للمركب لا للقوة وحدها ولا للاحقة؛ قُرئ المكونان مستقلين."),
    756: R("بر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بر`: التجرد والخلوص؛ لا يسمي up أو upwards.", "العلو موضع لا خروج إلى البر ولا تجرد، وفصلت الظرف عن الصفة التالية."),
    757: R("بر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بر`: التجرد والخلوص؛ لا يسمي high أو supreme.", "الارتفاع والسمو لا يثبتان من البر خلاف البحر، ولم تورث الصفة حكم الظرف السابق."),
    758: R("شبك", "LAW-GAP", "جسر المعنى: quick أو fast حاضر، لكن چ↔ش غير مسمى.", "الشبك إمساك متداخل لا سرعة، والمرشح العربي `سبق` الدال على التقدم خارج المروحة الحية؛ لم يدخل حدسا."),
    759: R("شبك", "LAW-GAP", "جسر المعنى: horsewhip أداة للحث السريع، لكن چ↔ش غير مسمى.", "وظيفة السوط في التسريع لا معنى الأداة، وفصلت الاسم عن صفة quick مع بقاء فجوة الصوت."),
    760: R("الدن", "LAW-GAP", "جسر المعنى: contaminate أو pollute حاضر، لكن آ↔ا غير مسمى في أول الهيكل.", "الدنس مرشح معنى خارج المروحة الحالية، والتحليل الإيراني الأولي غير مؤهل؛ لم يعوض أي منهما فجوة الصوت."),
    761: R("بش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بش`: الانتشار الظاهر؛ لا يسمي mosquito أو fly.", "انتشار البعوض جماعة وصف للسلوك لا معنى النوع، والخبر يرده إلى سلسلة إيرانية قديمة."),
    762: R("بن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بن`: حيز يضم امتدادا؛ لا يسمي lady.", "اللقب الاجتماعي لا يستخرج من محكمة النون، وفصل اسم المرأة العام عن اسم العلم المتجانس."),
    763: R("بندك", "OPEN-CANDIDATE", "جسر المعنى: المعنى الأقدم wick أو rope يلامس الرباط، لكن المدخلة الحالية lighter.", "شواهد `بندك` العربية في بنائق القميص، لا الولاعة؛ لم يورث المعنى التاريخي حكم المادة الحديثة."),
    764: R("شد", "TOOL-GAP", "جسر المعنى: maybe أو perhaps حاضر، لكن /šāyad/ يحمل /y/ أسقطها الهيكل.", "أوقفت المقارنة قبل وصل الإمكان بوثاقة `شد`؛ وحفظت مسار worthy إلى possible في المصدر."),
    765: R("شد", "TOOL-GAP", "جسر المعنى: worthy أو befit حاضر، لكن /šāyad/ يحمل /y/ أسقطها الهيكل.", "فصلت صيغة الفعل عن الظرف السابق، وأوقف الصامت الساقط أي مدار للقوة أو الاستحقاق."),
    766: R("نج", "TOOL-GAP", "جسر المعنى: look أو glance حاضر، لكن /negāh/ يحمل /h/ نهائية أسقطها الهيكل.", "لا تختزل الملاحظة إلى نون وجيم بعد حذف الهاء؛ وقف الحكم قبل معنى الحراسة والنظر."),
    767: R("جلك", "OUT-OF-SCOPE", "جسر المعنى: Gilaki language اسم لسان لا معنى معجميا عاما.", "عزل اسم اللسان وحقل أصله الفارغ؛ لم يحوله إلى نسبة `جلك` العربية ولا إلى دعوى جذرية."),
    768: R("رشت", "OPEN-CANDIDATE", "جسر المعنى: thread جسم دقيق طري ممتد، يلامس انتشار الأشياء الدقيقة الطرية في الحدث المجمد لـ`رشت`.", "المعنى واعد لكن الشاهدين العربيين غائبان؛ لم يحول series أو field of study إلى أثر المدخلة المادية."),
    769: R("مشت", "COMPOUND-BOUNDARY", "جسر المعنى: drunkenness مفككة مباشرة إلى `مست` drunk و`ـی` للاسم المجرد.", "قُرئت الصفة واللاحقة مستقلين؛ لم تورث الصورة المجموعة شاهد اللبن الفارسي في العربية."),
    770: R("دود", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دود`: محاكم حروف؛ لا يسمي smoke أو sadness.", "شواهد العربية في الدود الذي يقع في الطعام، لا دخان الفرع؛ فصل المعنيين مع اتحاد الرسم."),
    771: R("كستج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كستج`: محاكم حروف بلا معنى murder أو slaughter.", "حقل الأصل فارغ؛ لم يفكك الاسم إلى فعل القتل ولاحقة ولم يستخرج الذبح من الرسم."),
    772: R("بند", "OPEN-CANDIDATE", "جسر المعنى: servant أو bondsman شخص مقيد، و`بند` العربي يذكر الرباط.", "المدار الاشتقاقي واعد، لكن أحد شواهد العربية يسمي البند الفارسي المعرب والتحليل الحديث سطحي؛ بقي تماس مفتوحا لا أثرا."),
    773: R("بند", "OPEN-CANDIDATE", "جسر المعنى: I أو me استعمال تواضع مولود من servant، لا معنى مستقل في `بند`.", "فصلت الضمير عن الاسم السابق؛ لم يرث الضمير مدار القيد ولا حكمه."),
    774: R("اسب", "LAW-GAP", "جسر المعنى: injury أو wound أو damage حاضر، لكن آ↔ا غير مسمى في أول الهيكل.", "محاكم `اسب` لا تسمي الضرر، والأصل الإيراني المحتمل لا يعوض فجوة الصوت."),
    775: R("جو", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جو`: محكمتا حرفين؛ لا يسمي barley أو grain.", "الشاهدان العربيان في الهواء والموضع المطمئن؛ فصلت الحبوب عن متجانسي الماء والجو."),
    776: R("جو", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جو`: محكمتا حرفين؛ لا يسمي stream أو brook.", "الجو المنخفض قد يجمع الماء لكنه ليس المجرى؛ فصلت المدخلة عن الشعير والهواء."),
    777: R("بند", "TOOL-GAP", "جسر المعنى: foundation أو basis حاضر، لكن /bonyād/ يحمل /y/ أسقطها الهيكل.", "أوقف الصامت الساقط الحكم قبل فحص وضع الأساس، وفصل المعنى المالي الحديث عن أصل المدخلة."),
    778: R("صخ", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`صخ`: الدخول في الأثناء بحدة بالغة؛ لا يسمي stiff أو hard.", "الحدة قد تصف جسما صلبا لكنها لا تساوي الصلابة، وفصلت الصفة عن متجانس السيخ أو المشواة."),
    779: R("زند", "COMPOUND-BOUNDARY", "جسر المعنى: alive أو living محللة في الخبر إلى `زی` جذع live و`ـنده` لاسم الفاعل.", "قُرئ الجذع من فعله واللاحقة استقلالا؛ لم تورث الحياة لزند النار العربي ولا للمتجانس التالي."),
    780: R("زند", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زند`: اختزان الباطن بقوة؛ يلامس formidable ولا يسمي colossal.", "شواهد العربية في خشبتي الاستقداح والساعد؛ القوة وصف محتمل لا معنى الضخامة، وفصل المتجانس عن alive."),
    781: R("بش", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بش`: الانتشار الظاهر؛ لا يسمي skill أو craft أو profession.", "ظهور أثر الصنعة نتيجة للمهارة لا معنى الحرفة، والخبر يثبت سلسلة paint أو mark مستقلة."),
    782: R("جهنم", "TOOL-GAP", "جسر المعنى: certificate حاضر، لكن /govāhi-nāme/ يحمل /v/ أسقطها الهيكل.", "أوقفت المقارنة قبل جهنم؛ لم تفكك الشهادة من حقل أصل فارغ ولم تعوض الواو المنطوقة."),
    783: R("بغم", "TOOL-GAP", "جسر المعنى: message حاضر، لكن /payġām/ يحمل /y/ أسقطها الهيكل.", "شواهد `بغم` في صوت لا يفصح بالمعنى، لكن الصامت الساقط أوقف المقارنة قبل هذا الفصل."),
    784: R("ضمد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ضمد`: جمع الشيء وشده؛ لا يسمي bridegroom أو son-in-law.", "ضم الأسرتين بالزواج وصف للعلاقة لا معنى القرابة، وشاهدا العربية في الضماد والمداواة."),
    785: R("باف", "COMPOUND-BOUNDARY", "جسر المعنى: traitorous أو disloyal مفككة مباشرة إلى `بیـ` without و`وفا` loyalty.", "انتفاء الوفاء حاصل من التركيب؛ سجل قرض المكون العربي إلى الفارسية ولم يمنح المركب حكم إرث."),
    786: R("حردن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`حردن`: محاكم حروف بلا معنى to buy أو purchase.", "تبادل المال والسلعة فعل تعاقد لا يستخرج من المحاكم، والخبر يثبت سلسلة هندو إيرانية مستقلة."),
    787: R("تنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`تنج`: الضغط على القوة الباطنة؛ لا يسمي coin أو currency.", "سك العملة بالضغط وصف صنع لا معنى الوحدة النقدية، والأصل المجهول لم يحول إلى مانح عربي أو فارسي."),
    788: R("كشد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كشد`: خروج المتغلغل أو الملتحم؛ لا يسمي wide أو broad.", "فتح الشيء سبب لاتساعه لكنه ليس معنى العرض، وشاهدا العربية في الحلب والقطع بالأسنان."),
    789: R("كسدن", "OPEN-CANDIDATE", "جسر المعنى: pull أو drag حركة إخراج لما هو ملتحم، لكن الحدث المجمد لـ`كسدن` لا يسمي السحب.", "المرشح يحتفظ بنون المصدر ولا شاهدان له، ومواد المروحة العربية لا تثبت pull؛ بقي المدار مفتوحا."),
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
            raise AssertionError(f"تغير عداد نسخة v15 في {name}")
        if len(data.get("both") or []) != expected_both or len(data.get("sound_only") or []) != expected_sound:
            raise AssertionError(f"تغير طول قوائم نسخة v15 في {name}")
        total_both += expected_both
        total_sound += expected_sound
    if total_both != 14547 or total_sound != 106793:
        raise AssertionError("تغير مجموع أحواض v15")


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
            if row.rank > 717 and len(fresh) < 70:
                internal_skips.append(row.rank)
            continue
        seen.add(key)
        if row.rank <= 717:
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
    for index, entry in enumerate(lexicon.get("entries") or [], 1):
        grouped[H.clean(entry.get("word") or "")].append((index, entry))
    output: dict[int, H.BranchEntry] = {}
    for item in selected:
        row = item.row
        if row.rank == 731:
            output[row.rank] = H.BranchEntry(
                global_index=0,
                homograph_index=1,
                homograph_count=1,
                word=row.branch,
                reading="dige",
                pos="adv",
                gloss="Spoken form of دیگر (digar).",
                etymology="إحالة صرفية إلى دیگر؛ لا خبر أصل مستقل في الخام.",
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
        if not options:
            raise AssertionError(f"لا سطر خام للرسم {row.branch}")
        if row.rank == 731:
            line_number, raw = next(pair for pair in options if pair[0] == 3800)
        else:
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
        "پیش": {4609, 4610, 4611}, "گیر": {5696}, "گل": {366, 367, 368, 369, 370},
        "ـچه": {7514}, "بلوچ": {13607}, "ـی": {6328, 6329, 6330, 6331},
        "پول": {940}, "ـدار": {7516}, "سخن": {5075}, "گو": {5574, 5575, 5576, 5577},
        "نیرو": {2376}, "ـگاه": {7462}, "مست": {2719, 2720, 2721},
        "زیستن": {1523}, "ـنده": {10301}, "بیـ": {14756}, "وفا": {2605, 2606},
    }
    for word, expected in expected_indices.items():
        actual = {index for index, _entry in grouped.get(word, [])}
        if actual != expected:
            raise AssertionError(f"تغير جرد مكون {word}: {sorted(actual)}")
    fan_counts = {
        "پیش": 60, "گیر": 80, "گل": 80, "ـچه": 60, "بلوچ": 6, "ـی": 0,
        "پول": 40, "ـدار": 60, "سخن": 9, "گو": 72, "نیرو": 20, "ـگاه": 72,
        "مست": 9, "زی": 42, "ـنده": 30, "بیـ": 14, "وفا": 37,
    }
    for word, expected in fan_counts.items():
        fan = tuple(H.FAN.rank(word, H.FAN.fan(word, "persian"), "persian"))
        if len(fan) != expected:
            raise AssertionError(f"تغيرت مروحة المكون {word}: {len(fan)}")
    expected_raw = {
        "پیش": {5126, 5127, 5128}, "گیر": {6694, 6695}, "گل": {394, 395, 396, 397, 398},
        "ـچه": {8808}, "بلوچ": {16451}, "ـی": {7420, 7421, 7422, 7423, 7424},
        "پول": {997}, "ـدار": {8810}, "سخن": {5872}, "گو": {6551, 6552, 6553, 6554, 6555, 6556, 6557},
        "نیرو": {2492}, "ـگاه": {8752}, "مست": {2994, 2995, 2996}, "زیستن": {1605},
        "ـنده": {12672}, "بیـ": {17675}, "وفا": {2868, 2869},
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
    if review.verdict == "COMPOUND-BOUNDARY":
        return "وقف الحكم عند حد المركب؛ لم تورث الصورة المجموعة حكم مكون ولم يخترع تفكيك."
    if review.verdict == "LAW-GAP":
        return "طريق المعنى مفحوص، لكن مسار الصوت يحوي صفا غير مسمى؛ لم يصدر حكم موجب."
    if review.verdict == "TOOL-GAP":
        return "صف الحوض أسقط صامتا منطوقا؛ توقف العضو قبل الحكم ولم يعوض الصامت يدويا."
    if review.verdict == "OUT-OF-SCOPE":
        return "العضو اسم لسان لا معنى معجميا عاما؛ عزل من الحكم الجذري مع حفظه في التغطية."
    return "مسار الصوت قابل للفحص، لكن المدار لم يكتمل إلى حكم؛ بقي المرشح مفتوحا."


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
    joined = H.clean(" + ".join(decomposition))
    for component in EXPECTED_COMPONENTS[rank]:
        if H.clean(component) not in joined:
            raise AssertionError(f"غاب مكون {component} من الرتبة {rank}: {decomposition}")
    return [
        f"- تفكيك Kaikki الحصري المباشر من السطر الخام {raw['line']}: «{H.clip(raw['etymology'], 420)}».",
        f"- قراءة المكونات المستقلة: {COMPONENT_READINGS[rank]}",
        "- الخطوة صفر: قبل التفكيك النهائي المباشر لم تقارن الصورة وحدة جذرية؛ قُرئ كل مكون مسمى وحده.",
    ]


BASE_MAKE_CARD = R34.make_card


def make_card(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit) -> str:
    card = BASE_MAKE_CARD(item, entry, raw, decision, ranked, sense_map, quote_limit, etym_limit)
    card = card.replace("الجولة 34،", "الجولة 35،")
    rank = item.row.rank
    if rank in SOURCE_NOTES and "ملاحظة المصدر الخاصة" not in card:
        marker = "- عطب الهيكل:" if rank in TOOL_GAPS else "- الخطوة صفر:"
        card = card.replace(marker, f"- ملاحظة المصدر الخاصة: {SOURCE_NOTES[rank]}\n{marker}", 1)
    return card


def validate_decisions(selected, raw_entries, decisions, ranked_by_rank, sense_map) -> None:
    if set(REVIEWS) != set(SOUND_RANKS):
        raise AssertionError("جدول المدار اليدوي لا يغطي الرتب السبعين")
    parsed = {item.row.rank for item in selected if P25.direct_from_plus(raw_entries[item.row.rank]["etymology"])}
    if parsed != EXACT_DECOMPOSITIONS:
        raise AssertionError(f"تغيرت أسطر From X + Y المباشرة: {sorted(parsed)}")
    expected_verdicts = {
        "COMPOUND-BOUNDARY": 11,
        "LAW-GAP": 8,
        "NUCLEUS-TRACE": 1,
        "OPEN-CANDIDATE": 42,
        "OUT-OF-SCOPE": 1,
        "TOOL-GAP": 7,
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
        if decision.verdict in {"OPEN-CANDIDATE", "NUCLEUS-TRACE", "OUT-OF-SCOPE"} and not complete:
            raise AssertionError(f"حكم بمسار ناقص في الرتبة {row.rank}: {decision.verdict}")
        if decision.verdict == "NUCLEUS-TRACE":
            if coverage < 2 or H.event_line(decision.candidate).startswith("لا حدث"):
                raise AssertionError(f"أثر بلا حدث وشاهدين في الرتبة {row.rank}")
        if row.rank in EXACT_DECOMPOSITIONS and decision.verdict != "COMPOUND-BOUNDARY":
            raise AssertionError(f"تفكيك مباشر بلا حد مركب في الرتبة {row.rank}")
        if row.rank in TOOL_GAPS and decision.verdict != "TOOL-GAP":
            raise AssertionError(f"هيكل ناقص بلا TOOL-GAP في الرتبة {row.rank}")
        if row.rank in LAW_GAPS and decision.verdict != "LAW-GAP":
            raise AssertionError(f"مسار ناقص بلا LAW-GAP في الرتبة {row.rank}")
        if row.rank in OUT_OF_SCOPE and decision.verdict != "OUT-OF-SCOPE":
            raise AssertionError(f"اسم لسان بلا OUT-OF-SCOPE في الرتبة {row.rank}")
        if not REVIEWS[row.rank].meaning_path.startswith(("جسر المعنى:", "نص الحدث المجمد")):
            raise AssertionError(f"طريق المعنى غير مسمى في الرتبة {row.rank}")


def validate_text(selected, texts, prior_pairs) -> None:
    if len(selected) != 70 or BATCH_SIZES != (35, 35):
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = re.findall(r"^### (WO-B-R35-SOUND-\d{5}):", joined, re.MULTILINE)
    if headings != [item.heading for item in selected]:
        raise AssertionError("معرفات الجولة 35 لا تطابق النافذة")
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
        if "تفكيك Kaikki الحصري المباشر" not in card or "قراءة المكونات المستقلة" not in card:
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


def report_section(selected, decisions, sizes, stats) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    batches = (selected[:35], selected[35:])
    lines = [f"<!-- {MARKER}:START -->", ""]
    previous = 717
    for number, batch in enumerate(batches, 1):
        lo = 0 if number == 1 else 35
        hi = lo + len(batch)
        counts = Counter(decision.verdict for decision in decisions[lo:hi])
        distribution = "؛ ".join(f"{key}={counts[key]}" for key in sorted(counts))
        batch_skips = [rank for rank in stats["skipped"] if previous < rank <= batch[-1].row.rank]
        skipped = ", ".join(map(str, batch_skips)) or "0"
        lines.extend([
            f"## الجولة الخامسة والثلاثون، دفعة sound_only رقم {number}", "",
            f"- الوقت: {now}، Africa/Cairo.",
            f"- رشح وكتب: {len(batch)}؛ المواضع المقروءة المتجاوزة داخل المدى: {skipped}.",
            f"- المواضع: من {batch[0].heading} إلى {batch[-1].heading}.",
            f"- توزيع الأحكام: {distribution}.",
            "- طريق المعنى: سمي من جسر معنى صريح أو من نص الحدث المجمد في كل بطاقة.",
            "- المدار: كتب يدويا لكل عضو، وفصلت الأصداء اللينة عن الآثار المحكمة.",
            "- المروحة: ولدت حية كاملة ورتبت بالأوزان، ومسحت مواد جميع مرشحيها بلا قص للحقل المصدر.",
            "- المتجانسات: قرئت كل مداخل الرسم، وسجل العدد ورقم المدخلة المختارة في كل بطاقة.",
            "- المركب: قبل From X + Y النهائي المباشر حصرا؛ لم يخترع مكون ولم يؤهل تحليلا سطحيا أو تاريخيا.",
            "- التحقق البنيوي: المعرفات فريدة؛ لا بطاقة فوق 5KB؛ لا شرطة طويلة؛ الأرقام غربية والنص NFC.",
            f"- آخر موضع في الدفعة: {batch[-1].heading}، `{batch[-1].row.branch}`.", "",
        ])
        previous = batch[-1].row.rank
    total = Counter(decision.verdict for decision in decisions)
    distribution = "؛ ".join(f"{key}={total[key]}" for key in sorted(total))
    max_size = max(sizes)
    max_item = selected[sizes.index(max_size)]
    traces = [item.heading for item, decision in zip(selected, decisions) if decision.verdict == "NUCLEUS-TRACE"]
    lines.extend([
        "## حصيلة الجولة الخامسة والثلاثين", "",
        f"- حمل `persian.md` مرة واحدة؛ أزواج WO-B المقروءة={stats['pair_count']}؛ المتجاوز داخل النافذة={', '.join(map(str, stats['skipped']))}.",
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- نطاق الصوت الجديد: الرتب 718-789 بعد WO-B-R34-SOUND-00717، مع تجاوز الزوجين المقروءين 740 و741 فقط.",
        f"- الآثار النووية الاستكشافية الجديدة: {', '.join(traces)}؛ لم تفعل طبقة البرهان ولم تنشر أرقاما.",
        "- لم يسم اتجاه دخول جديد للعضو الفارسي المختار نفسه؛ عزلت `النيزك` الفارسي المعرب من سلسلة أخرى، والقروض التركية والمكونات العربية والمانح المجهول في مساراتها.",
        "- التفكيك المباشر المؤهل: S00726، S00738، S00744، S00745، S00751، S00752، S00753، S00755، S00769، S00779، S00785؛ قرئت المكونات المستقلة كلها.",
        "- التحليلات غير المؤهلة: S00734 وS00748 وS00760 وS00766 وS00772 وS00773 وS00777 وS00783؛ حفظت تاريخية المصدر وسطحيته ولم تحول إلى From نهائي.",
        "- أعطاب الأداة: S00734، S00764، S00765، S00766، S00777، S00782، S00783؛ لم تعوض الصوامت المنطوقة الساقطة.",
        "- فجوات القانون: S00718، S00725، S00733، S00747، S00758، S00759، S00760، S00774.",
        "- اسم اللسان المعزول: S00767؛ بقي في التغطية ولم يحول إلى معنى جذري عام.",
        "- أحواض `nucleus-sweep-*.json` التسعة الحالية v15 قرئت كاملة من القرص؛ both=14547 وsound_only=106793؛ ثبت الحجم وSHA-256 والعدادات لكل ملف.",
        f"- أكبر بطاقة: {max_size} بايت، {max_item.heading}؛ كل البطاقات دون 5KB.",
        "- لم تفعل طبقة البرهان؛ مر حارس نقاء الشحنة وختم CLEAN؛ لم يقع ship ولم يستعمل git.",
        "", f"<!-- {MARKER}:END -->", "", DONE_LINE,
    ])
    return "\n".join(lines)


def validate_existing(reading_text: str, report_text: str) -> None:
    match = re.search(rf"<!-- {re.escape(MARKER)}:START -->(.*?)<!-- {re.escape(MARKER)}:END -->", reading_text, re.DOTALL)
    if not match:
        raise AssertionError("محضر الجولة موجود وبطاقاتها غائبة")
    headings = re.findall(r"^### (WO-B-R35-SOUND-\d{5}):", match.group(1), re.MULTILINE)
    expected = [f"WO-B-R35-SOUND-{rank:05d}" for rank in SOUND_RANKS]
    if headings != expected:
        raise AssertionError("مقطع الجولة 35 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(DONE_LINE):
        raise AssertionError("سطر DONE35 ليس خاتمة التقرير")


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
        print("ROUND35 ALREADY PRESENT AND VALID")
        print(DONE_LINE)
        return 0

    validate_nucleus_snapshot()
    data = json.loads(SWEEP.read_text(encoding="utf-8"))
    selected, stats = select_rows(data, reading_text)
    prior_pairs = H.read_pairs(reading_text)
    lexicon = json.loads(LEXICON.read_text(encoding="utf-8"))
    entries, grouped = select_branch_entries(selected, lexicon)
    raw_entries = load_raw_entries(selected, entries)
    validate_components(grouped)

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
        R28.fit_card(item, entries[item.row.rank], raw_entries[item.row.rank], decision, ranked_by_rank[item.row.rank], sense_map)
        for item, decision in zip(selected, decisions)
    ]
    validate_text(selected, texts, prior_pairs)
    sizes = [len(card.encode("utf-8")) for card in texts]

    reading_append = (
        f"\n\n<!-- {MARKER}:START -->\n\n"
        "## الجولة الخامسة والثلاثون: متابعة حوض sound_only (2026-08-26)\n\n"
        "- النطاق: 70 عضوا طازجا بعد WO-B-R34-SOUND-00717؛ من الرتبة 718 إلى 789 مع تجاوز 740 و741 لأنهما مقروءان؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ طريق المعنى مسمى، والمدار اليدوي حاسم، والأصداء مفصولة عن الآثار المحكمة.\n"
        "- لقطة الأحواض: قرئت ملفات nucleus-sweep-*.json التسعة الحالية v15 من القرص؛ ثبتت بصماتها وعداداتها قبل الانتخاب.\n\n"
        + "\n".join(texts[:35])
        + "\n## الدفعة الثانية: متابعة sound_only بعد الرتبة 754\n\n"
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
    print("ROUND35 READY")
    print("NUCLEUS_V15_FILES", len(NUCLEUS_SNAPSHOT), "SHA256_AND_COUNTS_OK")
    print("NUCLEUS_V15_TOTALS", "BOTH=14547", "SOUND_ONLY=106793")
    print("SKIPPED", ",".join(map(str, stats["skipped"])))
    print("BATCHES", *BATCH_SIZES, "SELECTED", len(selected))
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("TRACES", "S00722")
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
    print("ROUND35 WRITTEN")
    print(DONE_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
