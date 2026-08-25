# -*- coding: utf-8 -*-
"""المسار B، الجولة 26: متابعة حوض sound_only في دفعتين من 35 بطاقة."""

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

import harvest_persian_round25 as P25  # noqa: E402

H = P25.H
P = P25.P
READING = ROOT / "04-cross-linguistic" / "readings" / "persian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-B.md"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-persian.json"
LEXICON = ROOT / "data" / "branch-lexicons" / "persian.json"
RAW_LEXICON = ROOT / "Resources" / "persian" / "kaikki.org-dictionary-Persian.jsonl"
MARKER = "LANE-B-PERSIAN-ROUND26-2026-08-25"
CARD_LIMIT = 5120
SOUND_RANKS = tuple(range(32, 66)) + tuple(range(67, 88)) + tuple(range(89, 104))
BATCH_SIZES = (35, 35)
DONE_LINE = "LANE-B DONE26 70 WO-B-R26-SOUND-00103"
OUTSIDE_FAN = {50, 52, 95}
EXACT_DECOMPOSITIONS = {32, 35, 54, 91}
FORM_OF_ISOLATED = {92}
BLOCKED_BOUNDARIES = {
    41: "قال Kaikki: By surface analysis ثم `شاه` + `ـین` بعد خبر أصل أقدم؛ لا سطر From X + Y نهائي مباشر.",
    44: "خبر الأصل يرد الصورة إلى عبارة فارسية وسطى فيها `ma` + `agar`، لا إلى سطر From X + Y نهائي مباشر للمدخلة الحالية.",
    45: "خبر الأصل يرد الصورة إلى عبارة فارسية وسطى فيها `ma` + `agar`، لا إلى سطر From X + Y نهائي مباشر للمدخلة الحالية.",
    74: "خبر الأصل يحلل صورة تاريخية إلى `anōš` + `-ag`، لا سطر From X + Y نهائي مباشر للمدخلة الحالية.",
}


@dataclass(frozen=True)
class SelectedRow:
    row: H.SweepRow

    @property
    def key(self) -> str:
        return f"S{self.row.rank:05d}"

    @property
    def heading(self) -> str:
        return f"WO-B-R26-SOUND-{self.row.rank:05d}"


@dataclass(frozen=True)
class Review:
    candidate: str
    verdict: str
    meaning_path: str
    orbit: str


def R(candidate: str, verdict: str, meaning_path: str, orbit: str) -> Review:
    return Review(candidate, verdict, meaning_path, orbit)


# هذه الأسطر هي سجل القراءة اليدوية. لا يشتق الحكم من عمود best ولا من درجة المروحة.
REVIEWS = {
    32: R("جطل", "COMPOUND-BOUNDARY", "جسر المعنى: `چه` لما أو كيف، و`طور` للطريقة؛ الطريق التركيبي محجوز للمكونين.", "فككت `چطور` إلى مكونيه المصرح بهما؛ لا معنى جذريا للصورة المجموعة قبل قراءتهما استقلالا."),
    33: R("كردن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كردن`: التركز والمعاودة لحصول النفع؛ لا يسمي فعل do أو make العام.", "جربت نقل المعاودة النافعة إلى مجرد الإحداث، فاحتاج النقل إلى تعميم زائد؛ بقي المعنى بلا مدار واحد."),
    34: R("كن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كن`: الاستتار في جوف شيء؛ لا يسمي عضو anus.", "لا يجعل كون العضو في باطن البدن اسمه هو الاستتار؛ ذلك وصف عارض يصدق على أعضاء كثيرة."),
    35: R("بشب", "COMPOUND-BOUNDARY", "جسر المعنى: `پیش` للأمام أو القبل و`آب` للماء؛ طريق urine لا يفحص إلا بعد فصل المكونين.", "ثبت سطر From X + Y، فقرأت `پیش` و`آب` وحدهما ومنعت المركب من وراثة حكم أحدهما."),
    36: R("اب", "LAW-GAP", "نص الحدث المجمد لـ`اب`: لا حدث مسجل يمكن أن يسمي الماء.", "حتى قبل مدار الماء بقيت آ↔ا بلا صف صوتي مسمى؛ لا تكتمل رجل الصوت ولا ينشأ حكم موجب."),
    37: R("نمز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`نمز`: انتشار من الباطن إلى الظاهر بلطف؛ لا يسمي الصلاة المفروضة.", "اختبرت الصلاة فعلا ظاهرا عن نية باطنة، لكن ذلك شرح للشعيرة لا نقطة معنى معجمية واحدة."),
    38: R("قردن", "LAW-GAP", "نص الحدث المجمد لـ`قردن`: استقرار في قاع أو حيز؛ لا يسمي العنق ولا المسؤولية.", "لم يقم مدار للعنق، وفوق ذلك لا يملك انتقال گ إلى ق صفا موقعا؛ الحكم فجوة قانون."),
    39: R("بند", "LOANWORD-NON-ARABIC-TO-ARABIC", "جسر المعنى: البند رباط وعقد في الفارسية وفي شاهد المحيط، مع تصريح المعاجم بأنه دخيل فارسي.", "اتحد الرباط والصورة، لكن الشواهد سمت اتجاه الدخول من الفارسية إلى العربية؛ أغلق تماس لا إرث."),
    40: R("بند", "OPEN-CANDIDATE", "جسر المعنى: العربية تسمي البند رباطا أو علما، ولا تسمي الصفة الفارسية closed أو sealed.", "فصلت صفة الإغلاق عن اسم الرباط المقترض؛ القرابة الاشتقاقية داخل الفارسية لا تنقل معنى الصفة إلى العربية."),
    41: R("شهن", "COMPOUND-BOUNDARY", "نص الحدث المجمد لـ`شهن`: وجود فراغ؛ لا يفحص الصقر قبل حسم حد التركيب التاريخي.", "التحليل الوارد سطحي ومتأخر عن خبر الأصل، ولذلك لم أصنع من `شاه` و`ـین` تفكيكا نهائيا مباشرا."),
    42: R("شر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`شر`: الانتشار أو صورة منه؛ لا يسمي برج Leo.", "لا يحول انتشار رسم النجوم إلى اسم البرج؛ احتاج ذلك إلى معرفة فلكية خارج المدخلة لا إلى مدار معجمي."),
    43: R("بشر", "ROOT-TRACE", "جسر المعنى: `البشر` الإنسان والخلق؛ الابن أو الصبي فرد مسمى من البشر.", "مدار 8: الجزء من الجنس؛ الصبي عضو من البشر بلا وسيط دلالي ثان، وشاهدا الإنسان يثبتان الجسر."),
    44: R("مجر", "COMPOUND-BOUNDARY", "نص الحدث المجمد لـ`مجر`: الامتلاء والاندفاع؛ معنى except محجوز خلف حد العبارة التاريخية.", "خبر الأصل لا يقدم From X + Y نهائيا للمدخلة؛ لذلك لم أورث `ma` أو `agar` حكما للصورة."),
    45: R("مجر", "COMPOUND-BOUNDARY", "نص الحدث المجمد لـ`مجر`: الامتلاء والاندفاع؛ معنى perhaps محجوز خلف حد العبارة التاريخية.", "فصلت مدخلة الظرف عن مدخلة حرف الجر، ووقفت كلتيهما عند التحليل التاريخي غير المؤهل."),
    46: R("وخ", "LAW-GAP", "نص الحدث المجمد لـ`وخ`: لا حدث نواتي مسجل يسمي الجليد.", "لا مدار للجليد، كما أن ی↔و في أول الهيكل غير مسمى؛ سميت فجوة القانون ولم أستبدل الياء حدسا."),
    47: R("وخ", "LAW-GAP", "نص الحدث المجمد لـ`وخ`: لا حدث نواتي مسجل يسمي صفة البرد.", "فصلت صفة cold عن اسم ice، وبقي ی↔و بلا صف موقع؛ لا يكتمل الصوت ولا المعنى."),
    48: R("مدر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`مدر`: الامتداد والغاية؛ لا يسمي الأم.", "اختبار الأم بوصفها أصلا أو غاية يضيف استعارة نسبية غير منصوصة؛ لا مدار معجمي مباشر."),
    49: R("برن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`برن`: التجرد والخلوص؛ لا يسمي الفراشة أو العثة أو المروحة.", "لا يكفي خروج الفراشة من الشرنقة لرد اسم الحيوان إلى التجرد؛ هذا سرد حياتي لا معنى المدخلة."),
    50: R("صهر", "LAW-GAP", "جسر المعنى: الصهر حرمة الزواج ومن يتزوج في القوم؛ الزوج طرف مباشر في هذا الجسر.", "مدار 2: الفاعل في الزواج قائم دلاليا، وشاهداه حاضران، لكن ش↔ص غير مسمى فتعطلت رجل الصوت."),
    51: R("خن", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`خن`: التخلخل الممتد في الباطن؛ لا يسمي البيت في الشواهد العربية.", "جعل البيت حيزا باطنا يصدق على كل وعاء ومكان؛ لم يضيق المدار إلى house ولم تسنده الشواهد."),
    52: R("حول", "LAW-GAP", "جسر المعنى: `الحول` سنة بأسرها في المعاجم، وهو معنى year نفسه.", "المعنى مباشر وشاهداه تامان، لكن ی↔ح غير مسمى في الرصف الأجوف؛ بقي الحكم خلف فجوة القانون."),
    53: R("سرح", "ROOT-TRACE", "نص الحدث المجمد لـ`سرح`: انطلاق أو انفراج أو انبساط في يسر؛ الشواهد تسمي الإرسال والحل والسهولة.", "مدار 5: الأثر والمكان؛ الثقب أو التجويف موضع خلفه انفراج المادة، وهي خطوة واحدة من الحدث."),
    54: R("وكز", "COMPOUND-BOUNDARY", "جسر المعنى: `ویکی` لويكي و`واژه` للكلمة أو المصطلح؛ Wiktionary هو التركيب المصرح.", "قرأْت مكوني From X + Y من مدخلتيهما ومروحتيهما، ولم أقارن الاسم المركب بوصفه جذرا."),
    55: R("اذذ", "LAW-GAP", "نص الحدث المجمد لـ`اذذ`: محاكم حروف بلا حدث موحد؛ لا يسمي الحرية أو الاستقلال.", "معنى free غير قائم، وآ↔ا وز↔ذ ود↔ذ ليست سلسلة صفوف كاملة؛ سميت فجوة القانون."),
    56: R("اذذ", "LAW-GAP", "نص الحدث المجمد لـ`اذذ`: محاكم حروف بلا حدث موحد؛ لا يسمي الحال free أو loose.", "فصلت الظرف عن الصفة السابقة؛ لا يصل الرصف الناقص إلى معنى الانطلاق أو السعة بلا جسر."),
    57: R("بر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بر`: التجرد والخلوص؛ لا يسمي الريشة أو الجناح.", "الريشة قد تنفصل، لكن الانفصال حال عرضي ولا يميز feather أو wing عن سائر الأجزاء."),
    58: R("سب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سب`: امتداد دقيق متصل بشيء؛ لا يسمي التفاحة.", "اختبرت الساق المتصلة بالثمرة، فكان المدار إلى جزء صغير لا إلى اسم apple نفسه."),
    59: R("جبت", "LAW-GAP", "نص الحدث المجمد لـ`جبت`: ما عبد من دون الله؛ لا يسمي خبز chapati.", "افترق معنى الطعام عن الجبت، وفوق ذلك چ↔ج وپ↔ب وت↔ت لا تكون مسارا موقعا كاملا هنا."),
    60: R("جست", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جست`: الاختراق الحسي أو المعنوي؛ لا يسمي اللحم.", "لا يجعل قطع اللحم أو مضغه معنى meat؛ ذلك فعل يقع على المادة ولا يسميها."),
    61: R("ترز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`ترز`: الابتعاد بقوة مع دقة؛ لا يسمي الميزان أو التعادل.", "حركة كفتي الميزان وصف تشغيل، أما اسم balance فلا يساوي الابتعاد؛ لا مدار واحد."),
    62: R("نف", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`نف`: نفاذ أو إبعاد بانتشار؛ لا يسمي السرة.", "كون السرة أثرا لاتصال سابق يحتاج سلسلة خلقية كاملة؛ لم يثبت المدار من معنى المدخلة نفسه."),
    63: R("در", "NUCLEUS-TRACE", "نص الحدث المجمد لـ`در`: الجريان باسترسال أو الامتداد بتوال؛ البعد حال بلوغ امتداد مكاني.", "مدار 7: الصفة والحال؛ far أو distant يصف شيئا امتد الفاصل إليه، وشاهدا الدرور يثبتان الاسترسال."),
    64: R("جل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جل`: الاتساع والانكشاف؛ لا يسمي goal الرياضي المقترض.", "اتساع المرمى وصف للمكان، لا اسم الهدف أو النتيجة؛ وفصلت الأصل الإنجليزي بوصفه حاشية."),
    65: R("كل", "NUCLEUS-TRACE", "جسر المعنى: الكليل سيف لا حد له، والسيف يكل عن ضريبته؛ off أو disabled حالة انقطاع الفعل.", "مدار 7: الصفة والحال؛ فقدان الحد أو الكلال صورة مباشرة لتعطل الأداة، وشاهدان مستقلان يثبتانها."),
    67: R("ندا", "NUCLEUS-TRACE", "جسر المعنى: النداء صوت ودعاء؛ invitation والannunciation وgood news أشياء ينادى بها.", "مدار 1: الحدث المباشر؛ الدعوة أو البشارة نداء ذو مضمون، بلا سلسلة دلالية ثانية."),
    68: R("بت", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بت`: القطع والانفصال؛ لا يسمي الصنم أو المحبوب الجميل.", "تحطيم الصنم فعل لاحق عليه، والجمال صفة أخرى؛ لا تسمية مباشرة لمدخلة idol أو beloved."),
    69: R("سو", "SOURCE-GAP", "نص الحدث المجمد لـ`سو`: هيئة الشيء الظاهرة وما يعتريها؛ اللمعان هيئة ضوئية ظاهرة.", "مدار 7 واعد للصفة الظاهرة والshimmer، لكن لم يرد شاهد عربي كلاسيكي مستقل في الموارد المسماة."),
    70: R("سو", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`سو`: هيئة ظاهرة واستواء أو عيب؛ لا يسمي profit أو advantage.", "فصلت متجانس الربح عن مدخلة الضوء السابقة؛ لا يحول حسن الهيئة إلى منفعة مالية أو مزية."),
    71: R("بل", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بل`: التمكن والحوز بشدة؛ لا يسمي الجسر أو عارضة الصوت.", "الجسر يمكن العبور لكنه ليس هو الحوز؛ الوظيفة لا تختزل اسم البناء إلى هذا الحدث."),
    72: R("كم", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`كم`: تغطية الشيء بغطاء زائد؛ لا يسمي الرغبة أو القصد.", "إخفاء القصد احتمال تداولي لا معنى desire أو intention؛ بقي الصوت وحده."),
    73: R("قر", "LAW-GAP", "نص الحدث المجمد لـ`قر`: استقرار ما شأنه التسيب في حيز؛ الرهن مال يثبت ضمانا للدين.", "مدار 3: الشيء المثبت أداة ضمان معقول، لكن گ↔ق بلا صف مسمى؛ لا يمر الحكم عبر الصوت."),
    74: R("انس", "COMPOUND-BOUNDARY", "نص الحدث المجمد لـ`انس`: الألفة أو الظهور بحسب المادة؛ معنى immortal محجوز خلف التحليل التاريخي.", "الصيغة التاريخية `anōš` + `-ag` ليست From X + Y نهائيا للمدخلة، فوقف الحكم بلا مكونات مخترعة."),
    75: R("اجر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`اجر`: محاكم حروف بلا حدث موحد؛ لا يسمي أداة الشرط if.", "أداة الشرط وظيفة نحوية، ولا يحول الرصف الصوتي مادة `اجر` إلى رابط افتراضي."),
    76: R("اجر", "LAW-GAP", "نص الحدث المجمد لـ`اجر`: محاكم حروف بلا حدث موحد؛ لا يسمي المخلل أو التتبيلة.", "فوق غياب المعنى بقي چ↔ج وصف المد غير موقعين كامليْن؛ سميت فجوة القانون."),
    77: R("اجر", "LAW-GAP", "نص الحدث المجمد لـ`اجر`: محاكم حروف بلا حدث موحد؛ لا يسمي مفتاح spanner.", "فصلت أداة الربط عن مدخلة المخلل، ولم أستخرج معنى الآلة من رصف ناقص."),
    78: R("بر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بر`: التجرد والخلوص؛ لا يسمي البطل.", "كون البطل متجردا للقتال وصف قصصي لا معنى hero؛ لا مدار قاموسي مباشر."),
    79: R("بر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بر`: التجرد والخلوص؛ لا يسمي الصاعقة.", "البرق قد يجرد الشجر، لكن ذلك أثر ممكن لا تعريف thunderbolt؛ بقيت المدخلة مستقلة."),
    80: R("كن", "NUCLEUS-TRACE", "نص الحدث المجمد لـ`كن`: الاستتار في جوف شيء؛ المنجم حيز باطن والكنز شيء مستتر فيه.", "مدار 5: المكان والمحتوى؛ mine أو treasure موضع خفي أو مدفون في الجوف، وشاهدا الستر يثبتان الخطوة."),
    81: R("جوا", "LAW-GAP", "نص الحدث المجمد لـ`جوا`: محاكم حروف بلا حدث موحد؛ لا يسمي الشاي.", "چ↔ج والمد النهائي لا يملكان رصفا موقعا كاملا، كما لا يوجد جسر إلى tea."),
    82: R("رز", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`رز`: التداخل الشديد؛ لا يسمي اليوم أو ضوء النهار.", "تداخل الليل والنهار عند الحد وصف زمني، لا معنى day نفسه؛ لا مدار مباشر."),
    83: R("جر", "LAW-GAP", "نص الحدث المجمد لـ`جر`: الاسترسال والامتداد؛ لا يسمي السوار bangle.", "قد يمتد السوار حول المعصم، لكن چ↔ج غير مسمى والمعنى وصفي عام؛ وقف الحكم عند القانون."),
    84: R("جهر", "LAW-GAP", "نص الحدث المجمد لـ`جهر`: ظهور الشيء وانكشافه عيانا؛ الوجه هو الهيئة الظاهرة المرئية.", "مدار 5: الهيئة الظاهرة قائم وشاهداه مباشران، لكن چ↔ج غير مسمى؛ لم يصدر أثر موجب."),
    85: R("جند", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جند`: صلابة وغلظ بالضغط؛ لا يسمي الخصية.", "صلابة عضو أو ليونته حال مرضية متغيرة، فلا تميز testicle معجميا عن سائر الأعضاء."),
    86: R("جب", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جب`: التجسم والبروز مع القطع أو الاستواء؛ لا يسمي big أو great وحده.", "البروز قد يصاحب الكبر، لكنه لا يساويه، وشواهد المادة تذهب إلى القطع والبئر؛ المدار أوسع من المدخلة."),
    87: R("كرم", "ROOT-TRACE", "جسر المعنى: الكريم حسن وشريف ونفيس؛ من معاني الفرع المثبتة impressive وcharming.", "مدار 7: الصفة والجودة؛ charm أو impressiveness قبول حسن ونفاسة، وشاهداهما يثبتان نقطة الجودة."),
    89: R("غرم", "LAW-GAP", "جسر المعنى: الغرام شر دائم وعذاب ومصيبة؛ grief يقع في نقطة الحزن الملازم.", "مدار 7 الدلالي قائم، لكن گ↔غ غير مسمى؛ لم أحول قوة المعنى إلى استثناء صوتي."),
    90: R("غرم", "LAW-GAP", "جسر المعنى: الغرام ولوع وملازمة؛ من معاني `گرمی` المثبتة fervour.", "فصلت fervour عن warmth وheat، وبقي گ↔غ بلا صف مسمى؛ لا حكم موجب رغم الجسر."),
    91: R("جل", "COMPOUND-BOUNDARY", "جسر المعنى: `گل` للطين و`ـی` لصنع الصفة؛ muddy هو التركيب المصرح.", "اختيرت مدخلة mud من خمسة متجانسات لـ`گل` وقرئت اللاحقة وحدها؛ لم ترث الصورة حكم المكون."),
    92: R("جل", "FORM-OF-ISOLATED", "جسر المعنى: السطر الخام يسميها صورة عامية من `گلو` throat، لا مدخلة rosy المصدرة خطأ بالاختيار الآلي.", "عزلت الإحالة إلى اللمّة الأم من المقارنة الجذرية؛ يلزم فتح `گلو` في موضع مستقل قبل أي مدار."),
    93: R("قط", "LAW-GAP", "نص الحدث المجمد لـ`قط`: قطع باستواء أو توال؛ نقطة التفتيش تقطع المرور وتنظمه.", "مدار 4: checkpoint أداة قطع المرور قائم، لكن گ↔ق غير مسمى وإن كان ت↔ط موقعا؛ فجوة قانون."),
    94: R("جث", "LAW-GAP", "نص الحدث المجمد لـ`جث`: تجمع الكتلة الكثيفة؛ Earth جرم كثيف والعالم يحال إليه في المدخلة.", "مدار 3: الهيئة والجرم قائم بشاهد الجثة، لكن ت↔ث غير مسمى؛ تعطلت رجل الصوت."),
    95: R("غوط", "LAW-GAP", "جسر المعنى: الغائط أرض مطمئنة منخفضة وبئر بعيدة القعر؛ deep هو العمق نفسه.", "المعنى وشاهداه مباشران، لكن گ↔غ ود↔ط صفان غير مسميين في البنية الجوفاء؛ لا أثر موجب."),
    96: R("نمق", "ROOT-TRACE", "جسر المعنى: نمق الشيء حسنه وزينه؛ charm أو attractive quality معنى مثبت في مدخلة `نمک`.", "مدار 7: الصفة والجودة؛ الجاذبية نتيجة التحسين والتزيين في خطوة واحدة، وشاهدا التنميق مستقلان."),
    97: R("بنر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`بنر`: الامتداد والبناء؛ لا يسمي الجبن.", "بناء قالب الجبن فعل صناعة لا معنى cheese؛ لا نقطة معجمية مشتركة."),
    98: R("جنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جنج`: الستر والكثافة مع حدث ج؛ لا يسمي الحرب أو القتال.", "ضجيج الحرب أو كثافة الجند سياق خارجي، لا معنى war نفسه؛ بقي الصوت بلا مدار."),
    99: R("جنج", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`جنج`: الستر والكثافة مع حدث ج؛ لا يسمي صغير الجمل.", "فصلت متجانس young camel عن الحرب، ولم أجد في المادة العربية اسما للحيوان أو سنه."),
    100: R("دست", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`دست`: النفاذ بدفع ودقة؛ لا يسمي الصديق أو المحبوب.", "شاهد `دوست` الفارسي في معجم عربي لقب أو تفسير أجنبي، لا مدخلة عربية تورث معنى friend."),
    101: R("امد", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`امد`: محاكم حروف بلا حدث موحد؛ لا يسمي الرجاء أو الأمل.", "بلوغ الأمد قد يكون موضوعا للأمل، لكنه مفعول محتمل لا معنى hope؛ لا مدار مباشر."),
    102: R("تنر", "SEMITIC-SOURCE-TRANSMISSION", "جسر المعنى: التنور فرن الخبز نفسه في الفرع والعربية، وخبر الأصل يسمي مسارا أكاديا وفارسيا وسطا.", "اتحدت الصورة والفرن، لكن المصادر سمت اللفظ فارسيا معربا أو مشتركا في اللغات مع أصل أكادي؛ أغلق نقل سامي لا إرثا مبسوطا."),
    103: R("زهر", "OPEN-CANDIDATE", "نص الحدث المجمد لـ`زهر`: بياض وإشراق يستطاب؛ لا يسمي السم أو الزعاف.", "اتحد الرسم وافترق المعنى؛ الأصل الفارسي الوسيط للسم لا يحول الزهر العربي إلى poison."),
}


EXPECTED_ENTRY_INDEX = {
    32: 193, 33: 198, 34: 199, 35: 205, 36: 207, 37: 209, 38: 212,
    39: 213, 40: 214, 41: 215, 42: 222, 43: 228, 44: 233, 45: 234,
    46: 238, 47: 239, 48: 240, 49: 243, 50: 248, 51: 261, 52: 276,
    53: 277, 54: 280, 55: 305, 56: 306, 57: 317, 58: 321, 59: 323,
    60: 324, 61: 325, 62: 334, 63: 335, 64: 367, 65: 368, 67: 427,
    68: 434, 69: 436, 70: 437, 71: 441, 72: 444, 73: 450, 74: 455,
    75: 460, 76: 462, 77: 463, 78: 485, 79: 486, 80: 494, 81: 496,
    82: 499, 83: 500, 84: 502, 85: 503, 86: 506, 87: 511, 89: 513,
    90: 514, 91: 515, 92: -1, 93: 522, 94: 523, 95: 529, 96: 533,
    97: 534, 98: 536, 99: 538, 100: 540, 101: 542, 102: 548, 103: 549,
}

EXPECTED_RAW_LINE = {
    32: 200, 33: 205, 34: 206, 35: 213, 36: 215, 37: 217, 38: 221,
    39: 222, 40: 223, 41: 225, 42: 232, 43: 239, 44: 246, 45: 247,
    46: 251, 47: 252, 48: 253, 49: 256, 50: 261, 51: 274, 52: 293,
    53: 294, 54: 297, 55: 323, 56: 324, 57: 335, 58: 340, 59: 342,
    60: 343, 61: 344, 62: 363, 63: 364, 64: 396, 65: 397, 67: 459,
    68: 468, 69: 471, 70: 472, 71: 476, 72: 479, 73: 486, 74: 491,
    75: 496, 76: 499, 77: 500, 78: 523, 79: 524, 80: 532, 81: 534,
    82: 539, 83: 540, 84: 542, 85: 543, 86: 546, 87: 552, 89: 554,
    90: 555, 91: 556, 92: 560, 93: 564, 94: 565, 95: 571, 96: 575,
    97: 576, 98: 578, 99: 580, 100: 582, 101: 584, 102: 590, 103: 591,
}

COMPONENT_READINGS = {
    32: (
        "`چه`: قُرئت مداخل branch-lexicons ذات الفهارس 791-794 واختيرت 791 لمعنى what، "
        "والسطر الخام 841؛ مروحتها 60: OPEN-CANDIDATE. `طور`: المدخلة 9265 والسطر "
        "10938 لمعنى manner أو way؛ مروحتها 40، وخبرها يصرح بالقرض من العربية: "
        "SEMITIC-SOURCE-TRANSMISSION للمكون وحده."
    ),
    35: (
        "`پیش`: المدخلة 4608 والسطر 5126 لمعنى front أو before؛ مروحتها 60: "
        "OPEN-CANDIDATE. `آب`: المدخلة 207 والسطر 215 لمعنى water؛ مروحتها 20: "
        "LAW-GAP لمسار آ↔ا، ولا يرث المركب أيا من الحكمين."
    ),
    54: (
        "`ویکی`: المدخلة 176 والسطر 182 لمعنى wiki؛ مروحتها 38: OPEN-CANDIDATE، "
        "والأصل الإنجليزي حاشية. `واژه`: المدخلة 998 والسطر 1062 لمعنى word أو term؛ "
        "مروحتها 57: OPEN-CANDIDATE."
    ),
    91: (
        "`گل`: قُرئت مداخلها الخمس واختيرت مدخلة mud ذات الفهرس 366 والسطر 395؛ "
        "مروحتها 80: OPEN-CANDIDATE. `ـی`: اختيرت المدخلة 6328 والسطر 7421 لصنع "
        "الصفات من الأسماء؛ مروحتها صفر: MORPHOLOGY-GAP."
    ),
}


# تجعل الشاهدين المنقولين متعلقين بالمعنى المحكوم، لا بأول متجانس داخل المادة.
H.TARGET_NEEDLES.update({
    "بشر": ("البَشَرُ: الخلقُ", "الإِنسانُ", "البشر الإنسان", "البَشَرُ الإِنسان"),
    "صهر": ("أهل بيت المرأة", "تزوَّجْت فيهم", "زوج بنت الرجل"),
    "سرح": ("أرسلته", "السَراح", "سهلا سُرُحا", "إرسالك رَسُولا"),
    "در": ("دَرَّ اللَّبَنُ", "دَرَّتِ السَّمَاءُ", "مِدْراراً"),
    "كل": ("السيف الذي لا حدَّ له", "عن ضريبته كُلُولًا", "الكالّ: المعيي"),
    "ندا": ("النِداءُ: الصوت", "نادَيْتُمْ إِلَى الصَّلاةِ", "أي: دَعَوْتُمْ"),
    "كن": ("الكِنُّ: كل شيء وقى", "جعلته في كِنٍّ", "بما يستر ببيت"),
    "كرم": ("الحَسَنُ", "الشَّرِيْفُ", "شرف الرجل", "الأخلاق والأفعال المحمودة", "كل ما يُحْمَد", "نفَسَ وَعَزَّ"),
    "نمق": ("حسنته وجودته", "زَيَّنَهُ بالكتابة", "حسنه وزينه"),
    "بند": ("فارسيٌّ معرّب", "فارسي معرّب", "البَنْدُ الرِّبَاطُ", "دَخيلٌ"),
    "تنر": ("فارسي معرَّب", "فارسي معرّب", "في كُلِّ لُغَةٍ", "التَّنُّور"),
    "حول": ("الحَوْلُ: سنة", "سنة بأسرها", "الحَوْلُ سَنَةٌ"),
    "غوط": ("المطمئن من الأرض", "بعيدةالقعر", "الغَوْطُ: الحَفْرُ"),
    "جهر": ("عِياناً يكشف", "ظهر وأجهرته", "جَهْرَة: مَا ظَهَرَ"),
    "غرم": ("الشر الدائم والعذاب", "الغَرَامُ: الوَلوعُ", "شدّة ومصيبة"),
    "قط": ("قطع الشيء الصلب", "الشيء المقطوع عرضا", "قَطْعُ الشَّيْءِ"),
    "جث": ("الجُثَّةُ: خلقُ البدَنِ الجَسِيمِ", "جثَّة الشيء: شخصه الناتئ", "الجُثَّةُ خَلْقُ البَدَنِ"),
})
P.WITNESS_PRIORITY.update({
    "بشر": ("al_sihah", "al_muhkam"),
    "صهر": ("al_sihah", "al_muhkam"),
    "سرح": ("al_sihah", "al_muhkam"),
    "در": ("kitab_al_ayn", "al_muhit"),
    "كل": ("kitab_al_ayn", "al_mufradat"),
    "ندا": ("al_sihah", "al_mufradat"),
    "كن": ("kitab_al_ayn", "al_mufradat"),
    "كرم": ("al_muhit", "al_misbah"),
    "نمق": ("kitab_al_ayn", "al_sihah"),
    "بند": ("al_muhit", "al_sihah"),
    "تنر": ("al_muhkam", "lisan"),
    "حول": ("kitab_al_ayn", "al_sihah"),
    "غوط": ("al_sihah", "lisan"),
    "جهر": ("al_sihah", "asas_al_balagha"),
    "غرم": ("al_sihah", "al_mufradat"),
    "قط": ("kitab_al_ayn", "al_mufradat"),
    "جث": ("kitab_al_ayn", "al_mufradat"),
})


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
            if row.rank <= 103 and row.rank > 31:
                internal_skips.append(row.rank)
            continue
        seen.add(key)
        if row.rank <= 31:
            continue
        fresh.append(row)
        if len(fresh) == 70:
            break
    ranks = tuple(row.rank for row in fresh)
    if ranks != SOUND_RANKS:
        raise AssertionError(f"تغير استئناف sound_only: {ranks}")
    if internal_skips != [66, 88]:
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
        if row.rank == 92:
            if len(options) != 4:
                raise AssertionError("تغير جرد گلی المختصر قبل استعادة السطر الخام")
            output[row.rank] = H.BranchEntry(
                global_index=-1,
                homograph_index=5,
                homograph_count=5,
                word=row.branch,
                reading="golli",
                pos="noun",
                gloss=row.gloss,
                etymology="See the etymology of the corresponding lemma form.",
            )
            continue
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
        if row.rank == 92:
            chosen = next((pair for pair in options if pair[0] == 560), None)
            if chosen is None:
                raise AssertionError("غاب سطر گلی العامي الخام 560")
            line_number, raw = chosen
        else:
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
    expected_indices = {
        "چه": {791, 792, 793, 794}, "طور": {9265, 9266}, "پیش": {4608, 4609, 4610},
        "آب": {207, 208}, "ویکی": {176}, "واژه": {998},
        "گل": {365, 366, 367, 368, 369},
        "ـی": {6327, 6328, 6329, 6330},
    }
    for word, expected in expected_indices.items():
        actual = {index for index, _entry in grouped.get(word, [])}
        if actual != expected:
            raise AssertionError(f"تغير جرد مكون {word}: {sorted(actual)}")
    fan_counts = {
        "چه": 60, "طور": 40, "پیش": 60, "آب": 20,
        "ویکی": 38, "واژه": 57, "گل": 80, "ـی": 0,
    }
    for word, expected in fan_counts.items():
        fan = tuple(H.FAN.rank(word, H.FAN.fan(word, "persian"), "persian"))
        if len(fan) != expected:
            raise AssertionError(f"تغيرت مروحة المكون {word}: {len(fan)}")


def obstacle_for(review: Review, rank: int) -> str:
    if review.verdict in {"ROOT-TRACE", "NUCLEUS-TRACE"}:
        return "اكتملت أرجل الصوت وطريق المعنى والمدار اليدوي، ومعهما شاهدان عربيان كلاسيكيان مستقلان."
    if review.verdict in {"SEMITIC-SOURCE-TRANSMISSION", "LOANWORD-NON-ARABIC-TO-ARABIC"}:
        return "اكتملت الصورة والمعنى والشواهد، لكن المصفاة سمت اتجاه تماس؛ أغلق خارج بسط الإرث المشترك."
    if review.verdict == "LAW-GAP":
        return "طريق المعنى مسمى أو مفحوص، لكن مسار الصوت يحوي صفا غير مسمى؛ لم يصدر حكم موجب."
    if review.verdict == "SOURCE-GAP":
        return "لم يرد شاهد عربي كلاسيكي مستقل للمعنى الدقيق؛ غياب المورد لا ينفي اللسان."
    if review.verdict == "COMPOUND-BOUNDARY":
        return "وقف الحكم عند حد المركب؛ لم تورث الصورة المجموعة حكم مكون ولم يخترع تفكيك."
    if review.verdict == "FORM-OF-ISOLATED":
        return "السطر صورة عامية محيلة إلى لمّة أخرى؛ عزلت حتى تقرأ اللمّة الأم في موضعها."
    return "اكتمل ما اكتمل من الصوت، لكن المدار اليدوي لم يقم على معنى المدخلة؛ بقي المرشح مفتوحا."


def decide(item: SelectedRow) -> H.Decision:
    review = REVIEWS[item.row.rank]
    return H.Decision(
        review.candidate,
        review.verdict,
        H.state_for(review.verdict),
        review.orbit,
        obstacle_for(review, item.row.rank),
    )


def decomposition_lines(item: SelectedRow, raw: dict) -> list[str]:
    rank = item.row.rank
    if rank not in EXACT_DECOMPOSITIONS:
        return []
    decomposition = P25.direct_from_plus(raw["etymology"])
    if not decomposition:
        raise AssertionError(f"غاب تفكيك From X + Y للرتبة {rank}")
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
    match_count, classical_count, witnesses = P.classical_witnesses(
        decision.candidate, sense_map, quote_limit
    )
    entry_ref = (
        "السطر الخام 560؛ المدخلة الخامسة غائبة من branch-lexicons"
        if row.rank == 92 else f"entries[{entry.global_index}]"
    )
    etymology = raw["etymology"] or entry.etymology or "فجوة اشتقاق في مدخلة Kaikki الخام."
    lines = [
        f"### {item.heading}: `{row.branch}` /{entry.reading}/، رتبة sound_only {row.rank}",
        "- إصدار البروتوكول: RECOVERY-v2 (2026-08-16)؛ نموذج WO-B-PROBE-001.",
        (
            f"- مرجع الحوض: `phonetic-sweep-persian.json:sound_only[{row.rank - 1}]`؛ "
            "overlap=0؛ shared=فارغ؛ الصوت وحده لا يرفض؛ الترتيب مدخل قراءة لا حكم."
        ),
        f"- الكلمة في الفرع: فارسية `{row.branch}` /{entry.reading}/؛ الصنف `{entry.pos}`.",
        (
            f"- قراءة مداخل الرسم المتجانس: قُرئت {entry.homograph_count} مدخلة للرسم `{row.branch}`؛ "
            f"المختارة {entry.homograph_index}، {entry_ref}، بالنطق والمعنى المثبتين؛ لم تؤخذ الأولى آليا."
        ),
        f"- أقدم صورة مستعادة: «{H.clip(etymology, etym_limit)}» [Kaikki؛ السطر الخام {raw['line']}].",
    ]
    exact = decomposition_lines(item, raw)
    if exact:
        lines.extend(exact)
    elif row.rank in BLOCKED_BOUNDARIES:
        lines.extend([
            f"- حد المركب غير المفكك: {BLOCKED_BOUNDARIES[row.rank]}",
            "- الخطوة صفر: لم يقبل تحليل سطحي أو تاريخي غير مباشر؛ وقف الحكم COMPOUND-BOUNDARY بلا مكونات مخترعة.",
        ])
    elif row.rank in FORM_OF_ISOLATED:
        lines.extend([
            "- عزل الصورة المحيلة: السطر الخام يقول إنها صورة عامية من `گلو` throat؛ لم تستبدل بمدخلة rosy المتجانسة.",
            "- الخطوة صفر: لم تقارن صورة الإحالة وحدة جذرية؛ أغلقت FORM-OF-ISOLATED إلى أن تقرأ اللمّة الأم استقلالا.",
        ])
    else:
        lines.append(
            f"- الخطوة صفر: طُرحت صوائت الفرع وصرفه المسمى فقط؛ الهيكل `{'ـ'.join(row.skeleton)}` "
            f"وعدد صوامته {len(row.skeleton)}؛ لم يسقط صامت حدسا."
        )
    fan_choice = (
        "جاء من جسر المعنى خارج المروحة بعد مسحها كاملة؛ عضوية المروحة ليست شرطا رابعا"
        if row.rank in OUTSIDE_FAN else
        "اختير من داخلها بعد المسح الكامل لا من عمود `best` وحده"
    )
    source_note = (
        "مادة فحص من جسر المعنى خارج المروحة؛ سُجل ذلك صراحة"
        if row.rank in OUTSIDE_FAN else
        "مادة الفحص المختارة من المروحة"
    )
    lines.extend([
        f"- درجة المقارنة: {H.comparison_degree(decision.candidate)}",
        (
            f"- المروحة المرتبة الكاملة: `fan_any_script.fan({row.branch}, persian)`؛ "
            f"العدد {len(ranked)}: {H.formatted_fan(ranked)}."
        ),
        f"- فحص المروحة كلها: قُرئت مواد {len(ranked)} مرشحا بـ`--max-chars 0`؛ {fan_choice}.",
        f"- المقابل من اللسان: `{decision.candidate}`؛ {source_note}.",
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
        "- المصفاة: الأصل حاشية؛ لا يغلق النقل إلا بمانح عربي أو سامي مسمى، أو تصريح عربي بالتعريب.",
        "- فصل المتجانسات والاقتراض: الحكم للمدخلة وحدها؛ لا توارث من متحد الرسم.",
        "- اليتم والإشعاع: الجرد حاضر؛ شاهدا العربية أو فجوتها؛ لا حصر ولا قرينة عدد.",
        "- جسور الاسترداد: الفرع؛ الأصل؛ الصفر؛ المروحة؛ الشبكة؛ `all_tiers`؛ الشواهد؛ المصفاة؛ المركب.",
        f"- عائق القرار أو تمامه: {decision.obstacle}",
        f"- ملاحظات العدستين: استرداد حتى القرار، وتشكيك مقصور على العضو؛ الجولة 26، الموضع {item.key}.",
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
    positive = {"ROOT-TRACE", "NUCLEUS-TRACE"}
    transmission = {"SEMITIC-SOURCE-TRANSMISSION", "LOANWORD-NON-ARABIC-TO-ARABIC"}
    for item, decision in zip(selected, decisions):
        row = item.row
        candidates = {candidate for candidate, _score in ranked_by_rank[row.rank]}
        inside = decision.candidate in row.candidates_found and decision.candidate in candidates
        if row.rank not in OUTSIDE_FAN and not inside:
            raise AssertionError(f"مرشح الرتبة {row.rank} خارج المروحة بلا تسمية")
        if row.rank in OUTSIDE_FAN and inside:
            raise AssertionError(f"تغير وضع مرشح الجسر الخارجي في الرتبة {row.rank}")
        complete = H.route_complete(row, decision.candidate)
        _count, coverage, _witnesses = P.classical_witnesses(
            decision.candidate, sense_map, 60
        )
        if decision.verdict == "LAW-GAP" and complete:
            raise AssertionError(f"LAW-GAP بلا صف مفقود في الرتبة {row.rank}")
        if decision.verdict == "OPEN-CANDIDATE" and not complete:
            raise AssertionError(f"OPEN-CANDIDATE بمسار ناقص في الرتبة {row.rank}")
        if decision.verdict in positive:
            if not complete or coverage < 2 or H.event_line(decision.candidate).startswith("لا حدث"):
                raise AssertionError(f"حكم موجب بلا ثلاث أرجل كاملة في الرتبة {row.rank}")
        if decision.verdict in transmission and (not complete or coverage < 2):
            raise AssertionError(f"حكم نقل بلا صوت وشاهدين في الرتبة {row.rank}")
        if decision.verdict == "SOURCE-GAP" and (not complete or coverage >= 2):
            raise AssertionError(f"SOURCE-GAP غير صادق في الرتبة {row.rank}: {coverage}")
        if not REVIEWS[row.rank].meaning_path.startswith(("جسر المعنى:", "نص الحدث المجمد")):
            raise AssertionError(f"طريق المعنى غير مسمى في الرتبة {row.rank}")


def validate_text(
    selected: list[SelectedRow], texts: list[str], prior_pairs: set[tuple[str, str]]
) -> None:
    if len(selected) != 70 or BATCH_SIZES != (35, 35):
        raise AssertionError("لم تكتمل الدفعتان 35+35")
    joined = "\n".join(texts)
    headings = re.findall(r"^### (WO-B-R26-SOUND-\d{5}):", joined, re.MULTILINE)
    if headings != [item.heading for item in selected]:
        raise AssertionError("معرفات الجولة 26 لا تطابق النافذة")
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
    for rank in EXACT_DECOMPOSITIONS:
        card = texts[SOUND_RANKS.index(rank)]
        if "تفكيك Kaikki الحصري" not in card or "قراءة المكونات المستقلة" not in card:
            raise AssertionError(f"لم تقرأ مكونات الرتبة {rank} استقلالا")
    for rank in BLOCKED_BOUNDARIES:
        card = texts[SOUND_RANKS.index(rank)]
        if "حد المركب غير المفكك" not in card or "بلا مكونات مخترعة" not in card:
            raise AssertionError(f"لم يغلق حد المركب في الرتبة {rank}")
    form_card = texts[SOUND_RANKS.index(92)]
    if "السطر الخام 560" not in form_card or "FORM-OF-ISOLATED" not in form_card:
        raise AssertionError("لم تعزل صورة گلی العامية الصحيحة")


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
        skipped = "66" if number == 1 else "88"
        lines.extend([
            f"## الجولة السادسة والعشرون، دفعة sound_only رقم {number}", "",
            f"- الوقت: {now}، Africa/Cairo.",
            f"- رُشح وكُتب: {len(batch)}؛ الموضع المقروء المتجاوز داخل المدى: {skipped}.",
            f"- المواضع: من {batch[0].heading} إلى {batch[-1].heading}.",
            f"- توزيع الأحكام: {distribution}.",
            "- طريق المعنى: سُمي من جسر معنى صريح أو من نص الحدث المجمد في كل بطاقة.",
            "- المدار: كُتب يدويا لكل عضو، وهو الحاسم بعد فحص الصوت والحدث والشواهد.",
            "- المروحة: وُلدت كاملة ورُتبت بالأوزان، ومُسحت مواد جميع مرشحيها بلا قص للحقل المصدر.",
            "- المتجانسات: قُرئت كل مداخل الرسم، وسُجل العدد ورقم المدخلة المختارة في كل بطاقة.",
            "- المركب: لم يقبل إلا سطر From X + Y النهائي المباشر من Kaikki الخام؛ وقُرئ كل مكون مقبول وحده.",
            "- التحقق البنيوي: المعرفات فريدة؛ لا بطاقة فوق 5KB؛ لا شرطة طويلة؛ الأرقام غربية والنص NFC.",
            f"- آخر موضع في الدفعة: {batch[-1].heading}، `{batch[-1].row.branch}`.",
            "",
        ])
    total = Counter(decision.verdict for decision in decisions)
    distribution = "؛ ".join(f"{key}={total[key]}" for key in sorted(total))
    max_size = max(sizes)
    max_item = selected[sizes.index(max_size)]
    positive = [
        item.heading for item, decision in zip(selected, decisions)
        if decision.verdict in {"ROOT-TRACE", "NUCLEUS-TRACE"}
    ]
    transmission = [
        item.heading for item, decision in zip(selected, decisions)
        if decision.verdict in {"SEMITIC-SOURCE-TRANSMISSION", "LOANWORD-NON-ARABIC-TO-ARABIC"}
    ]
    lines.extend([
        "## حصيلة الجولة السادسة والعشرين", "",
        f"- حمل `persian.md` مرة واحدة؛ أزواج WO-B المقروءة={stats['pair_count']}؛ المتجاوز داخل النافذة=66، 88.",
        f"- مجموع القراءة الجديدة: 70 في دفعتين 35+35؛ {distribution}.",
        "- نطاق الصوت الجديد: الرتب 32-103 بعد آخر معرف في الجولة السابقة، مع إسقاط الزوجين المقروءين فقط.",
        f"- الصلات الموجبة ذات الأرجل الثلاث والشاهدين: {', '.join(positive)}.",
        f"- أحكام التماس المسماة الاتجاه: {', '.join(transmission)}.",
        "- التفكيك الحصري: S00032، S00035، S00054، S00091؛ قُرئت مكوناتها الثمانية استقلالا.",
        "- حدود غير مؤهلة: S00041، S00044، S00045، S00074؛ وصورة محيلة معزولة: S00092 من السطر الخام 560.",
        f"- أكبر بطاقة: {max_size} بايت، {max_item.heading}؛ كل البطاقات دون 5KB.",
        "- عطب أداة أساسية: 0؛ لم تُفعّل طبقة البرهان، ولم يُبن ملف مشترك، ولم يقع ship، ولم يستعمل git.",
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
        r"^### (WO-B-R26-SOUND-\d{5}):", match.group(1), re.MULTILINE
    )
    expected = [f"WO-B-R26-SOUND-{rank:05d}" for rank in SOUND_RANKS]
    if headings != expected:
        raise AssertionError("مقطع الجولة 26 الموجود غير مكتمل")
    if not report_text.rstrip().endswith(DONE_LINE):
        raise AssertionError("سطر DONE26 ليس خاتمة التقرير")


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
        print("ROUND26 ALREADY PRESENT AND VALID")
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
        "## الجولة السادسة والعشرون: متابعة حوض sound_only (2026-08-25)\n\n"
        "- النطاق: 70 عضوا طازجا بعد WO-B-R25-SOUND-00031؛ من الرتبة 32 إلى 103 مع تجاوز 66 و88 لأن زوجيهما مقروءان؛ دفعتان 35+35.\n"
        "- النموذج: WO-B-PROBE-001؛ طريق المعنى مسمى من الجسر أو نص الحدث، والمدار اليدوي حاسم، ولا موجب بلا ثلاث أرجل وشاهدين.\n\n"
        + "\n".join(texts[:35])
        + "\n## الدفعة الثانية: متابعة sound_only بعد الرتبة 67\n\n"
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
    print("ROUND26 READY")
    print("SKIPPED", ",".join(map(str, stats["skipped"])))
    print("BATCHES", *BATCH_SIZES, "SELECTED", len(selected))
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("EXACT_FROM_PLUS", " ".join(f"S{rank:05d}" for rank in sorted(EXACT_DECOMPOSITIONS)))
    print("BLOCKED_BOUNDARIES", len(BLOCKED_BOUNDARIES), "FORM_OF", len(FORM_OF_ISOLATED))
    print("MAX_CARD", max(sizes), selected[sizes.index(max(sizes))].heading)
    if args.preview:
        print("PREVIEW ONLY")
        print(DONE_LINE)
        return 0

    with READING.open("a", encoding="utf-8", newline="") as handle:
        handle.write(reading_append)
    with REPORT.open("a", encoding="utf-8", newline="") as handle:
        handle.write(report_append)
    print("ROUND26 WRITTEN")
    print(DONE_LINE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
