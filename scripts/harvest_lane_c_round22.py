#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Lane C round 22: exhaust doubled Hebrew ``both``, then resume Egyptian.

The Hebrew ledger is loaded once.  Starting at the requested ``both[1478]``
anchor, every already-present branch is skipped and every selected branch is
inserted into the same in-memory ledger before scanning continues.  The 63
remaining Hebrew branches fill the first forty-card batch and 23 cards of the
second.  The final 17 cards come from the registered Egyptian queue, with all
AED hits, lookup path, selected member, and homographic disagreement retained.

This script appends research ledgers and the lane report only.  It never
stages, commits, publishes, or ships.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

import harvest_lane_c_round20 as R20
import harvest_lane_c_round21 as R21


R9 = R20.R9
AR = R21.AR
R3 = R21.R3
ROOT = R21.ROOT
HEBREW = R21.HEBREW
EGYPTIAN = R20.EGYPTIAN
REPORT = R21.REPORT
SWEEP = R21.SWEEP

MARKER = "LANE-C-ROUND22-2026-08-18"
HEBREW_MARKER = f"{MARKER}:HEBREW"
EGYPTIAN_MARKER = f"{MARKER}:EGYPTIAN"
REPORT_MARKER = f"{MARKER}:REPORT"
ANCHOR_INDEX = 1478
POOL_EXPECTED = 1851
HEBREW_COUNT = 63
EGYPTIAN_COUNT = 17
BATCH_SIZE = 40
CARD_COUNT = 80
FIRST_EGYPTIAN_SERIAL = 1086
LAST_EGYPTIAN_SERIAL = FIRST_EGYPTIAN_SERIAL + EGYPTIAN_COUNT - 1
TRANSITION = (
    "HEBREW-DOUBLED-BOTH-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)

RT = R21.ROOT_TRACE
RE = R21.ROOT_ECHO
NE = R21.NUCLEUS_ECHO
OP = R21.OPEN
LN = R21.LOAN
SL = R21.SEMITIC_LOAN
FM = R21.FORM


# Each ruling is member-scoped and handwritten.  Retrieval overlap and the
# first fan candidate never supply a semantic verdict.  Weak-final positives
# descend to a named binary nucleus only after the full root is recorded.
HEBREW_DECISIONS: tuple[R21.Decision, ...] = (
    R21.d("صور", RT, "READY", "صورة|صور|تصوير|رسم", "ציורי صفة مشتقة صراحة من ציור، والرسم والتصوير والصورة مدار الجذر صور نفسه.", "צור"),
    R21.d("سعي", OP, "LAW-GAP", "سعى|سعي|أعان|ساعد", "المساعدة تلتقي السعي إلى قضاء الحاجة، لكن ترتيب ס־י־ע لا يسوي س־ع־ي بمسار موقع.", "סיע"),
    R21.d("نور", RT, "READY", "نور|النور|ضوء|السراج", "المصباح حامل النور، وقاموس الفرع يرد العضو إلى الأصل السامي *nūr-.", "נור"),
    R21.d("رعي", NE, "READY", "رعى|الراعي|رعي|المرعى", "قاموس الفرع يسمي راعي العربية قرينًا؛ بقيت النهاية ה↔ي غير موقعة، ثم أصدر لب رع ECHO الراعي.", "רעה", "رع"),
    R21.d("بيض", RT, "READY", "بيض|بيضة|البيض", "ביצייה مشتقة من ביצה، والمقابل العربي بيضة للشيء نفسه مع صف צ↔ض المسجل.", "ביצ"),
    R21.d("كوس", OP, "LAW-GAP", "كوسة|الكوسا|قرع", "قاموس الفرع يقارن كوسة العربية، لكن סדר קשו بإزاء كوس يحتاج قلب الواو والسين ولا صف يقيمه.", "קשו"),
    R21.d("قصو", NE, "READY", "أقصى|قصا|النهاية|البعد", "الطرف والنهاية يلتقيان أقصى الشيء؛ النهاية ה↔و لم تكتمل، ثم أصدر لب قص ECHO الحد.", "קצה", "قص"),
    R21.d("هجو", NE, "READY", "هجا|الهجاء|الحروف|النطق", "النطق وتهجية الحروف مدار واحد؛ بقيت النهاية ה↔و بلا صف، ثم أصدر لب هج ECHO.", "הגה", "هج"),
    R21.d("مين", LN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "مين|ماين|ولاية", "الحس المختار Maine علم أمريكي منقول من الإنجليزية، لا مادة من العربية.", "מינ"),
    R21.d("لوبي", LN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "لوبي|ردهة|جماعة ضغط", "lobby قرض إنجليزي حديث في الحس المختار؛ عُزل عن לובי «ليبي» المتجانس.", "לובי"),
    R21.d("موت", RT, "READY", "موت|الموت|ميت|مات", "מיתה والمِيتة العربية اسما الحال من الموت نفسه، وقاموس الفرع يسمي القرين العربي.", "מות"),
    R21.d("ليشي", LN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "ليتشي|فاكهة|شجرة", "اسم lychee دولي منقول في النهاية من الصينية؛ لا إرث سامي.", "ליצי"),
    R21.d("سوس", OP, "SEMANTIC-GAP", "سوس|فرس|أنثى", "الفرس الأنثى لا تسميها حواس سوس العربية في المادة المقروءة؛ female تغطية عامة لا مدار.", "סוס"),
    R21.d("حنو", OP, "SOURCE-GAP", "حنو|حنان|لطف|معسكر", "مدخل الجذر يجمع النزول للتخييم واللطف من غير فصل عضو؛ لم يُنتق الحنو ويُترك التخييم.", "חנה"),
    R21.d("فيض", OP, "LAW-GAP", "فاض|فيض|انتشر|تفرق", "الانتشار ظاهر دلالة، لكن פ־ו־ץ لا يسوي ف־ي־ض: ו↔ي بلا صف، وشرط צ↔ض لا يعالج الوسط.", "פוצ"),
    R21.d("ذات", OP, "MORPHOLOGY-GAP", "ذات|هوية|نفس", "זהות توليد حديث من זה ولاحقة تجريد؛ تشابه identity مع الذات لا ينشئ جذرًا موروثًا.", "זהה"),
    R21.d("قيظ", OP, "LAW-GAP", "قيظ|الصيف|حر", "summer يطابق القيظ، لكن צ↔ظ يستدعي DENT-08 المشروط ولا يعرض العضو إعادة بناء تحقق شرطه.", "קיצ"),
    R21.d("صفو", OP, "SEMANTIC-GAP", "صفا|صفو|راقب", "المراقب والكشاف لا يطابقان الصفو أو الصفاء؛ boy تغطية عارضة لحس scout.", "צפה"),
    R21.d("خيط", OP, "DIRECTIONAL-TRANSMISSION", "خياط|خيط|حاك", "tailor يطابق الخياط، لكن مدخل الفرع لا يسمي المانح أو طبقة الأخذ؛ بقي اتجاه النقل مفتوحًا.", "חיט"),
    R21.d("ريش", OP, "SOURCE-GAP", "ريش|راء|حرف", "resh اسم حرف سامي، أما ريش العربية فلا تسمي الحرف؛ لم يُدخل اسم الراء من خارج المروحة.", "ריש"),
    R21.d("دوس", RE, "READY", "داس|دوس|الدوس|وطئ", "الدوّاسة آلة تداس بالقدم؛ الحكم ECHO من فعل الدوس إلى آلته لا لكل حس للعضو.", "דוש"),
    R21.d("سوي", RT, "READY", "سوى|سوي|سواء|المساواة", "المساواة والاستواء والسواء مدار واحد في الجذر الكامل.", "שוי"),
    R21.d("صاد", OP, "SOURCE-GAP", "صاد|الحرف|الأبجدية", "tsade والصاد اسمان تاريخيان لحرفين متقابلين، لكن صورة صاد العربية لم تثبت هنا بجذر معجمي وشاهدين عاملين.", "צד"),
    R21.d("دشأ", OP, "SOURCE-GAP", "دشأ|العشب|نبت", "sprouting and grass لا يرجع له شاهد عربي عامل في مادة دشأ، ولم تُستبدل بها نشأ خارج الطريق.", "דשא"),
    R21.d("سلو", RT, "READY", "سلوى|السمانى|الطائر|السلوى", "قاموس الفرع يقارن سلوى العربية والآرامية والسريانية؛ الطائر نفسه على الجذر الضعيف سلو.", "שלו"),
    R21.d("فيينا", LN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "فيينا|النمسا|مدينة", "Vienna علم مدينة أوروبي منقول؛ لا جذر سامي.", "וינה"),
    R21.d("أوفا", LN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "أوفا|روسيا|مدينة", "الحس المختار Ufa علم مدينة روسية منقول، منفصل عن متجانسي baker.", "אופה"),
    R21.d("شوط", RT, "READY", "شوط|الأشواط|جرى|الطواف", "الحركة ذهابًا وإيابًا هي الشوط والمسافة التي يعدوها الفرس أو يطوفها الطائف.", "שוט"),
    R21.d("قصص", RT, "READY", "قص|قصص|القطع|قطع", "القطع والتقليم والبتر من فعل القص الكامل، مع צ↔ص في الموضعين.", "קצצ"),
    R21.d("فشع", OP, "SEMANTIC-GAP", "فشع|جريمة|عصيان", "felony/transgression لا تطابق حواس فشع العربية؛ شاهد Ugaritic لا يمنح العربية معنى غير مقروء.", "פשע"),
    R21.d("عطف", RE, "READY", "عطف|ثنى|لف|الرداء", "اللف والتغطية صورة من ثني الثوب وعطفه؛ الحكم ECHO للمدار المقيد لا لكل عطف.", "עטפ"),
    R21.d("تهم", OP, "SOURCE-GAP", "تهامة|العمق|البحر", "المصدر يرد תהום إلى *tihām-، لكن مادة تهم العربية المقروءة لا تثبت abyss أو sea بشاهدين عاملين.", "תהם"),
    R21.d("سوء", OP, "NAME-ROOT-OPEN", "السوء|كارثة|خراب", "الحس المختار Shoah علم للكارثة التاريخية؛ لم يرث حكم الاسم العام المتجانس ولا السوء العربي.", "שוא"),
    R21.d("سيم", OP, "SEMANTIC-GAP", "سيم|تمام|نهاية", "end/completion لا يطابق حواس سيم العربية؛ التغطية بكلمة end لا تصنع مدارًا.", "סים"),
    R21.d("لبأ", RT, "READY", "لبؤة|لبأ|الأسد|اللبوة", "قاموس الفرع يرد lion إلى *labiʔ-، والعربية تحفظ اللبؤ واللبوة من الصورة نفسها.", "לבא"),
    R21.d("عون", FM, "FORM-OF-ISOLATED", "عون|عداوة|صيغة", "العضو excessive spelling من עוין؛ حُفظت إحالة الصورة ولم تُنشأ بطاقة جذر مستقلة.", "עונ"),
    R21.d("ميش", OP, "MORPHOLOGY-GAP", "من|شخص|أحد", "מישהו مركب حديث من מי + ש־ + הוא؛ لا يُعامل سطحه جذرًا عربيًا.", "מישהו"),
    R21.d("تير", OP, "SEMANTIC-GAP", "تير|سائح|سياحة", "tourist لا يطابق حواس تير/ثير العربية، ولا يُدخل ساح من خارج المروحة.", "תיר"),
    R21.d("زكو", NE, "READY", "زكا|زكي|الزكاء|طهر|نقي", "النقاء والطهارة ظاهران؛ الرسم العبري الثنائي זך لا يحمل الواو الضعيفة، ثم أصدر لب زك ECHO.", "זך", "زك"),
    R21.d("هك", OP, "SEMANTIC-GAP", "هك|ضرب|طرق", "الضرب لا يطابق مادة هك العربية المقروءة؛ hit معنى الفرع وحده لا شاهد عربي.", "הכ"),
    R21.d("صيني", LN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "صيني|الصين|نسبة", "النسبة إلى China مبنية على اسم جغرافي ثالثي المصدر؛ لا إرث بين صيغتي النسبة.", "סיני"),
    R21.d("شد", FM, "FORM-OF-ISOLATED", "شد|اختصار|جادة", "שד׳ اختصار كتابي لـשדרות لا جذرًا معجميًا مستقلًا.", "שד"),
    R21.d("نطي", OP, "SEMANTIC-GAP", "نطي|ميل|انحناء", "tendency/inclination لا يطابق حواس نطي العربية؛ الاشتقاق العبري من נטה محفوظ بلا نقل.", "נטי"),
    R21.d("عيط", OP, "SEMANTIC-GAP", "عيط|نسر|طائر", "eagle لا تسميه حواس عيط العربية في المادة المقروءة؛ large تغطية تصنيفية لا مدار.", "עיט"),
    R21.d("رهب", OP, "NAME-ROOT-OPEN", "رهب|رهبة|وحش|بحر", "Rahab علم لوحش بحري أو لكوكب، ولا تثبت رهبة العربية هذا الاسم أو اشتقاقه.", "רהב"),
    R21.d("هك", FM, "FORM-OF-ISOLATED", "هك|ضرب|مبني للمجهول", "הוכה صيغة مبنية للمجهول من הכה؛ لم تُنشأ صلة مستقلة بعد بقاء أصلها مفتوحًا.", "הכ"),
    R21.d("شيد", OP, "SEMANTIC-GAP", "شيد|خزانة|صندوق", "خزانة الأدراج لا يطابقها التشييد أو حواس شيد العربية؛ chest تغطية إنجليزية عريضة.", "שיד"),
    R21.d("عشو", OP, "SEMANTIC-GAP", "عشو|صنع|فعل", "made/likely من الجذر العبري עשה، ولا يطابق العشو أو حواس عشو العربية.", "עשה"),
    R21.d("عشو", OP, "SEMANTIC-GAP", "عشو|صنع|فعل", "مدخل الجذر doing/making لا يثبت معنى عربيًا في مادة عشو؛ لم يُدخل صنع من خارج الصوت.", "עשה"),
    R21.d("عدي", OP, "SEMANTIC-GAP", "عدي|حلي|زينة", "ornament/jewellery لا يطابق حواس عدي العربية، والاسم الشخصي المتجانس معزول.", "עדי"),
    R21.d("عصف", OP, "LAW-GAP", "عصف|عاصفة|ريح|زوبعة", "المصدر يقارن عاصفة العربية، لكن ס־ו־פ لا يسوي ع־ص־ف: أول رجلين خارج الطريق الموقع.", "סופ"),
    R21.d("دوح", OP, "MORPHOLOGY-GAP", "دوح|خبر|تقرير", "דיווח back-formation من اختصار דו״ח؛ الاشتقاق الاختصاري يمنع معاملته جذرًا موروثًا.", "דוח"),
    R21.d("صيص", OP, "SEMANTIC-GAP", "صيص|صوت|تغريد", "tweet/chirp لا يطابق حواس صيص العربية؛ حس Twitter قرض دلالي إنجليزي معزول.", "ציץ"),
    R21.d("حيط", OP, "SEMANTIC-GAP", "حيط|عقم|تطهير", "التعقيم وقتل الجراثيم لا يطابق حواس حيط العربية؛ all تغطية تعريفية لا مدار.", "חיט"),
    R21.d("حنو", OP, "SEMANTIC-GAP", "حنو|موقف|خيم", "parking مشتق من חנה في التخييم والتوقف، ولا يطابق الحنو العربي في الحس المقروء.", "חנה"),
    R21.d("علي", FM, "FORM-OF-ISOLATED", "علي|علو|صيغة", "עילי excessive spelling من עִלִּי؛ حُفظت الصورة ولم تُعد شاهدًا مستقلًا.", "עלי"),
    R21.d("حصي", OP, "SEMANTIC-GAP", "حصي|عبور|قطع", "crossing/crosswalk لا يطابق حواس حصي العربية، ولا يُدخل عبر من خارج المروحة.", "חצי"),
    R21.d("دلهي", LN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "دلهي|الهند|مدينة", "Delhi علم منقول عبر الإنجليزية من الأردية؛ لا جذر سامي.", "דלהי"),
    R21.d("ميش", OP, "MORPHOLOGY-GAP", "من|شخص|إحداهن", "מישהי مركب من מי + ש־ + היא؛ سطح المركب لا يصير جذرًا عربيًا.", "מישהי"),
    R21.d("تيق", OP, "SEMANTIC-GAP", "تيق|ملف|وثيقة", "file documents لا يطابق حواس تيق العربية، ولا يُدخل حفظ أو قيد من خارج الصوت.", "תיק"),
    R21.d("يوت", LN, "LOANWORD-THIRD-PARTY-TO-BRANCH", "جوت|ليف|نبات", "jute قرض من البنغالية؛ وحس Utah المتجانس علم أمريكي، فكلاهما خارج الإرث السامي.", "יוט"),
    R21.d("يوم", RE, "READY", "يوم|اليوم|النهار|أيام", "כיום مركب صراحة من كاف التشبيه وأداة التعريف وיום؛ الحكم ECHO من اليوم إلى «في الزمن الحاضر» بعد نزع السوابق.", "יום"),
    R21.d("ثني", SL, "SEMITIC-SOURCE-TRANSMISSION", "ثنى|كرر|علم|تلقين", "Tanya عنوان مأخوذ من الآرامية תניא «قد عُلّم» من תנא؛ أُغلق النقل السامي المسمى دون دعوى إرث عبري مستقل.", "תנא"),
)


EXPECTED_HEBREW_INDICES = (
    1480, 1483, 1487, 1488, 1490, 1493, 1494, 1497, 1500, 1506,
    1512, 1518, 1521, 1522, 1524, 1526, 1531, 1532, 1544, 1545,
    1547, 1556, 1558, 1560, 1565, 1571, 1579, 1584, 1659, 1662,
    1664, 1711, 1725, 1735, 1747, 1749, 1757, 1760, 1775, 1777,
    1781, 1783, 1787, 1790, 1795, 1806, 1811, 1812, 1814, 1815,
    1821, 1822, 1823, 1825, 1826, 1828, 1835, 1836, 1842, 1843,
    1845, 1847, 1849,
)


EGYPTIAN_DECISIONS: tuple[R9.Decision, ...] = (
    R9.gap("aed-v1.0:162530", "قدي", "SEMANTIC-GAP", "go around/surround/return لا يطابق حواس قدي أو قضي في المروحة، ولا يُدخل دار من خارج الرسم."),
    R9.gap("aed-v1.0:163220", "كري", "SEMANTIC-GAP", "think about/plan لا يطابق حواس كري/كلي العربية، ولا يُدخل رأي من خارج المروحة."),
    R9.gap("aed-v1.0:164130", "كفا", "SEMANTIC-GAP", "be discrete لا يطابق الكفاية أو حواس كفا العربية؛ وأعضاء AED الخمسة الأخرى لا تقرضه معانيها."),
    R9.gap("aed-v1.0:164310", "كمم", "SEMANTIC-GAP", "black/dark لا يطابق حواس كمم العربية المقروءة، ولا تُسوّى التغطية بالظلمة مجازًا."),
    R9.gap("aed-v1.0:164900", "كنح", "SEMANTIC-GAP", "grow dark/make dark لا يطابق حواس كنح العربية، ومدخل shrine المتجانس معزول."),
    R9.gap("aed-v1.0:165430", "كسي", "SEMANTIC-GAP", "bow/bend/prostrate لا يطابق حواس كسي/كشي/كصي، ولا يُدخل ركع من خارج الرسم."),
    R9.gap("aed-v1.0:165620", "ككي", "SEMANTIC-GAP", "be dark لا يطابق حواس ككي العربية، ولا يُدخل ظلمة من خارج المروحة."),
    R9.gap("aed-v1.0:165880", "كتت", "SEMANTIC-GAP", "small/trifling لا يطابق حواس كتت/كطت العربية؛ أعضاء AED السبعة محفوظة بلا دمج."),
    R9.gap("aed-v1.0:166130", "جاي", "SEMANTIC-GAP", "calumniate/lie لا يطابق جاء أو حواس جاي؛ overthrow وmoisten متجانسان منفصلان."),
    R9.gap("aed-v1.0:166210", "جاو", "SEMANTIC-GAP", "narrow/lack/deprive لا يطابق حواس جاو/قاو/غاو، ولا تُجمع الأفعال الأربعة في مقابل عربي مفترض."),
    R9.gap("aed-v1.0:166480", "قرح", "SEMANTIC-GAP", "be weary لا يطابق القرح أو حواس جرح/قلح، وshoulder والعصر متجانسان لا يرثهما المختار."),
    R9.gap("aed-v1.0:166810", "غوش", "SEMANTIC-GAP", "crooked في الحس الطبي لا يطابق حواس غوش/جوش/قوش العربية؛ العضو القرضي المجاور لا يمنحه اتجاهه."),
    R9.gap("aed-v1.0:166820", "غوش", "DIRECTIONAL-TRANSMISSION", "crooked/turn away موسوم قرضًا ساميًا، لكن AED لا يسمي المانح أو الطريق، والمروحة لا تحسم عضوًا عربيًا مباشرًا."),
    R9.gap("aed-v1.0:166950", "غبي", "SEMANTIC-GAP", "weak/deficient/defraud/cheat أوسع من الغباء ولا يساويه؛ لم يُنتق deficient ويُترك الغش والضعف."),
    R9.gap("aed-v1.0:167540", "جنن", "SEMANTIC-GAP", "weak/soft لا يطابق حواس جنن/قنن/غنن العربية، وأعضاء النبات المتجانسة معزولة."),
    R9.gap("aed-v1.0:167860", "جرم", "SEMANTIC-GAP", "carry off لا يطابق الجرم أو حواس جرم العربية مباشرة، ولا تُسوّى نتيجة الحمل بالاكتساب أو القطع."),
    R9.gap("aed-v1.0:167880", "جرح", "SEMANTIC-GAP", "complete/be satisfied لا يطابق الجرح أو حواس قرح/قلح، ومدخل ending المتجانس لا يمنح المختار حكمه."),
)


EXPECTED_EGYPTIAN_IDS = tuple(item.member_id for item in EGYPTIAN_DECISIONS)
assert len(HEBREW_DECISIONS) == HEBREW_COUNT
assert len(EGYPTIAN_DECISIONS) == EGYPTIAN_COUNT


def select_hebrew(original_memory: str) -> tuple[list[tuple[int, dict]], int, int]:
    """Perform the checked single-memory de-duplication from the live ledger."""
    rows = R21.load_pool()
    assert len(rows) == POOL_EXPECTED
    assert str(rows[ANCHOR_INDEX]["branch"]) in original_memory
    assert str(rows[ANCHOR_INDEX + 1]["branch"]) in original_memory
    memory = original_memory
    fresh: list[tuple[int, dict]] = []
    skipped = 0
    for index, row in sorted(
        enumerate(rows), key=lambda item: (-int(item[1].get("overlap", 0)), item[0])
    ):
        branch = str(row["branch"])
        if branch in memory:
            skipped += 1
            continue
        fresh.append((index, row))
        memory += "\n" + branch
    actual = tuple(index for index, _ in fresh)
    assert actual == EXPECTED_HEBREW_INDICES, (
        f"Fresh Hebrew tail drifted:\nexpected={EXPECTED_HEBREW_INDICES}\nactual={actual}"
    )
    anchor_fresh = sum(1 for index, _ in fresh if index >= ANCHOR_INDEX)
    anchor_skipped = (POOL_EXPECTED - ANCHOR_INDEX) - anchor_fresh
    assert anchor_fresh == HEBREW_COUNT and anchor_skipped == 310
    return fresh, skipped, anchor_skipped


def validate_positive_witnesses(matches: dict[str, list[dict]]) -> None:
    positives = {RT, RE, NE}
    for decision in HEBREW_DECISIONS:
        if decision.verdict not in positives:
            continue
        root = AR.normalize_root(decision.candidate)
        witnesses = R3.selected_witnesses(matches.get(root, []), decision.keywords)
        assert len(witnesses) == 2, (
            f"Positive Hebrew ruling lacks two Arabic witnesses: "
            f"{decision.candidate} ({decision.verdict})"
        )


def render_hebrew_card(
    serial: int,
    index: int,
    row: dict,
    decision: R21.Decision,
    matches: dict[str, list[dict]],
) -> str:
    card = R21.render_card(serial, index, row, decision, matches)
    batch = 12 if serial <= BATCH_SIZE else 13
    within = serial if serial <= BATCH_SIZE else serial - BATCH_SIZE
    card = re.sub(
        r"(?m)^### WO-C-HEBREW-\d{3}-\d{3}:",
        f"### WO-C-HEBREW-{batch:03d}-{within:03d}:",
        card,
        count=1,
    )
    card = card.replace("ROUND21 (2026-08-18)", "ROUND22 (2026-08-18)")
    assert "ROUND21" not in card
    return card


def render_egyptian_card(
    serial: int,
    rank: int,
    item: dict,
    decision: R9.Decision,
    matches: dict[str, list[dict]],
) -> str:
    card = R20.round20_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND20-COMPLETION", "ROUND22-COMPLETION")
    card = card.replace(
        f"round20-egyptian-rank={rank}/{R20.CARD_COUNT}",
        f"round22-egyptian-rank={rank}/{EGYPTIAN_COUNT}",
    )
    assert "وسم الطريق" in card
    assert "عُرضت المداخل كلها" in card
    assert "مدخل AED المختار" in card
    assert "فصل المتجانسات والاقتراض" in card
    return card


def render_appendices() -> tuple[str, str, str, dict, tuple[str, str, str]]:
    hebrew_memory = HEBREW.read_text(encoding="utf-8")
    egyptian_memory = EGYPTIAN.read_text(encoding="utf-8")
    report_memory = REPORT.read_text(encoding="utf-8")
    if HEBREW_MARKER in hebrew_memory:
        raise SystemExit("Round-22 Hebrew marker already exists; append refused.")
    if EGYPTIAN_MARKER in egyptian_memory:
        raise SystemExit("Round-22 Egyptian marker already exists; append refused.")
    if REPORT_MARKER in report_memory:
        raise SystemExit("Round-22 report marker already exists; append refused.")

    selected_hebrew, hebrew_skipped, anchor_skipped = select_hebrew(hebrew_memory)
    hebrew_roots = {AR.normalize_root(item.candidate) for item in HEBREW_DECISIONS}
    hebrew_matches = AR.matches_for_roots(AR.DEFAULT_RESOURCES, hebrew_roots, None)
    validate_positive_witnesses(hebrew_matches)
    hebrew_cards = [
        render_hebrew_card(serial, index, row, decision, hebrew_matches)
        for serial, ((index, row), decision) in enumerate(
            zip(selected_hebrew, HEBREW_DECISIONS), 1
        )
    ]

    hebrew_body: list[str] = [
        f"<!-- {HEBREW_MARKER}:START -->", "",
        "## الجولة الثانية والعشرون: استنفاد الحوض العبري المضاعف، الدفعة 012 (2026-08-18)", "",
        (
            "الحالة: طبقة الاستكشاف؛ إلحاق فقط. بدأ الفحص من `both[1478]`، "
            "وكان `both[1478]` و`both[1479]` مكررين. حُمّل `hebrew.md` مرة واحدة، "
            "وأضيف كل رسم منتخب إلى متغير الذاكرة نفسه فورًا."
        ), "",
    ]
    for rank, card in enumerate(hebrew_cards, 1):
        if rank == BATCH_SIZE + 1:
            hebrew_body.extend([
                "## الجولة الثانية والعشرون: الجزء العبري من الدفعة 013 (2026-08-18)", "",
                (
                    "استؤنف متغير الذاكرة نفسه؛ كُتبت الرسوم العبرية الثلاثة والعشرون "
                    "الباقية، ثم ثبت نفاد الحوض قبل إكمال الدفعة الثانية."
                ), "",
            ])
        hebrew_body.extend([card.rstrip(), ""])
        if rank % 5 == 0 or rank == HEBREW_COUNT:
            hebrew_body.extend([f"<!-- LANE-C-R22-HEBREW-CHUNK-{rank:03d}:END -->", ""])
    hebrew_body.append(f"<!-- {HEBREW_MARKER}:END -->")

    egyptian_exact, _ = R9.load_entries("egyptian")
    egyptian_queue = R9.select_egyptian(egyptian_memory, egyptian_exact)
    selected_egyptian = egyptian_queue[:EGYPTIAN_COUNT]
    actual_egyptian_ids = tuple(str(item["entry_id"]) for item in selected_egyptian)
    assert actual_egyptian_ids == EXPECTED_EGYPTIAN_IDS, (
        f"Egyptian queue drifted:\nexpected={EXPECTED_EGYPTIAN_IDS}\n"
        f"actual={actual_egyptian_ids}"
    )
    assert all("ḏ" not in str(item["headword"]) for item in selected_egyptian)
    egyptian_roots = {
        AR.normalize_root(item.candidate)
        for item in EGYPTIAN_DECISIONS if item.candidate not in {"", "∅"}
    }
    egyptian_matches = AR.matches_for_roots(AR.DEFAULT_RESOURCES, egyptian_roots, None)
    egyptian_cards = [
        render_egyptian_card(
            FIRST_EGYPTIAN_SERIAL + rank - 1,
            rank,
            item,
            decision,
            egyptian_matches,
        )
        for rank, (item, decision) in enumerate(
            zip(selected_egyptian, EGYPTIAN_DECISIONS), 1
        )
    ]

    egyptian_body: list[str] = [
        f"<!-- {EGYPTIAN_MARKER}:START -->", "",
        "## الجولة الثانية والعشرون: إكمال الدفعة 013 من المصري المسجل (2026-08-18)", "",
        (
            f"نفد الحوض العبري المضاعف بعد 63 رسمًا طازجًا، فسُجل الانتقال `{TRANSITION}`. "
            "أُكملت الدفعة الثانية بسبع عشرة بطاقة مصرية من "
            "`WO-C-OPEN-COMP-01086` إلى `WO-C-OPEN-COMP-01102`. في كل بطاقة "
            "عُرضت إصابات AED كلها بلا حد، وكُتب وسم الطريق والرسم والمدخل المختار، "
            "وحُفظ الاختلاف والمتجانسات بلا محو."
        ), "",
    ]
    for rank, card in enumerate(egyptian_cards, 1):
        egyptian_body.extend([card.rstrip(), ""])
        if rank % 5 == 0 or rank == EGYPTIAN_COUNT:
            egyptian_body.extend([f"<!-- LANE-C-R22-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    egyptian_body.append(f"<!-- {EGYPTIAN_MARKER}:END -->")

    hebrew_verdicts = collections.Counter(item.verdict for item in HEBREW_DECISIONS)
    hebrew_states = collections.Counter(item.state for item in HEBREW_DECISIONS)
    egyptian_verdicts = collections.Counter(item.verdict for item in EGYPTIAN_DECISIONS)
    egyptian_states = collections.Counter(item.state for item in EGYPTIAN_DECISIONS)
    now = datetime.now(ZoneInfo("Africa/Cairo")).strftime("%Y-%m-%d %H:%M:%S %z")
    now = now[:-2] + ":" + now[-2:]
    report = "\n".join([
        "", f"<!-- {REPORT_MARKER} -->",
        "## الجولة الثانية والعشرون: المسار C، الساميات والمصرية (2026-08-18)", "",
        f"- الوقت: {now}.",
        f"- بدأ الفحص من `both[{ANCHOR_INDEX}]`: الموضعان 1478 و1479 مكرران، وأول الطازج `both[1480]`.",
        "- قانون التكرار: حُمّل `hebrew.md` كاملًا مرة واحدة، واختبر كل `branch` في الذاكرة، وأضيف كل منتخب إلى المتغير نفسه فورًا.",
        f"- حوض `both`: الحجم={POOL_EXPECTED:,}؛ الطازج الباقي={HEBREW_COUNT}؛ المتجاوز في الحوض كله={hebrew_skipped}؛ المتجاوز من المرساة إلى النهاية={anchor_skipped}.",
        "- الدفعة الأولى: 40 بطاقة عبرية من `both[1480]` إلى `both[1777]`.",
        "- الدفعة الثانية: 23 بطاقة عبرية من `both[1781]` إلى `both[1849]`، ثم 17 بطاقة مصرية من `WO-C-OPEN-COMP-01086` إلى `WO-C-OPEN-COMP-01102`.",
        f"- سُجل الانتقال `{TRANSITION}` بعد استنفاد جميع الرسوم العبرية الطازجة.",
        "- طُبقت قواعد AED الثلاث: كل الإصابات بلا حد؛ وسم الطريق والرسم والمدخل المختار مكتوبة؛ الاختلاف والمتجانسات محفوظة بلا محو.",
        f"- أحكام العبرية: {json.dumps(dict(sorted(hebrew_verdicts.items())), ensure_ascii=False)}.",
        f"- حالات العبرية: {json.dumps(dict(sorted(hebrew_states.items())), ensure_ascii=False)}؛ كل موجب له شاهدان عربيان عاملان.",
        f"- أحكام المصرية: {json.dumps(dict(sorted(egyptian_verdicts.items())), ensure_ascii=False)}.",
        f"- حالات المصرية: {json.dumps(dict(sorted(egyptian_states.items())), ensure_ascii=False)}؛ لا فجوة حُولت إلى نفي.",
        "- التذكير السامي مطبق: الجذر الكامل أولًا، ثم النواة عند الحاجة فقط؛ حدث الحرف مرجع لا شرط.",
        "- صف ḏ المصري المؤجل بقي مستبعدًا، ولا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE22 {CARD_COUNT} WO-C-OPEN-COMP-{LAST_EGYPTIAN_SERIAL:05d}",
    ]) + "\n"

    diagnostics = {
        "pool": POOL_EXPECTED,
        "anchor": f"both[{ANCHOR_INDEX}]",
        "anchor_first_fresh": "both[1480]",
        "hebrew_fresh": HEBREW_COUNT,
        "hebrew_skipped_all": hebrew_skipped,
        "hebrew_skipped_from_anchor": anchor_skipped,
        "batch_1": {"hebrew": BATCH_SIZE, "egyptian": 0, "total": BATCH_SIZE},
        "batch_2": {"hebrew": 23, "egyptian": EGYPTIAN_COUNT, "total": BATCH_SIZE},
        "total": CARD_COUNT,
        "hebrew_first": "both[1480]",
        "hebrew_last": "both[1849]",
        "egyptian_queue_before": len(egyptian_queue),
        "egyptian_first": f"WO-C-OPEN-COMP-{FIRST_EGYPTIAN_SERIAL:05d}",
        "egyptian_last": f"WO-C-OPEN-COMP-{LAST_EGYPTIAN_SERIAL:05d}",
        "hebrew_verdicts": dict(sorted(hebrew_verdicts.items())),
        "hebrew_states": dict(sorted(hebrew_states.items())),
        "egyptian_verdicts": dict(sorted(egyptian_verdicts.items())),
        "egyptian_states": dict(sorted(egyptian_states.items())),
        "max_hebrew_card_bytes": max(len(card.encode("utf-8")) for card in hebrew_cards),
        "max_egyptian_card_bytes": max(len(card.encode("utf-8")) for card in egyptian_cards),
        "final_line": f"LANE-C DONE22 {CARD_COUNT} WO-C-OPEN-COMP-{LAST_EGYPTIAN_SERIAL:05d}",
    }
    hebrew_appendix = unicodedata.normalize("NFC", "\n".join(hebrew_body).rstrip() + "\n")
    egyptian_appendix = unicodedata.normalize("NFC", "\n".join(egyptian_body).rstrip() + "\n")
    report_appendix = unicodedata.normalize("NFC", report)
    return (
        hebrew_appendix,
        egyptian_appendix,
        report_appendix,
        diagnostics,
        (hebrew_memory, egyptian_memory, report_memory),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--show-hebrew", type=int, choices=range(1, HEBREW_COUNT + 1))
    parser.add_argument(
        "--show-egyptian",
        type=int,
        choices=range(FIRST_EGYPTIAN_SERIAL, LAST_EGYPTIAN_SERIAL + 1),
    )
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    hebrew, egyptian, report, diagnostics, memories = render_appendices()
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    if args.show_hebrew:
        cards = re.findall(
            r"(?ms)^### WO-C-HEBREW-.*?(?=^### |^## |^<!-- |\Z)", hebrew
        )
        print("\n" + cards[args.show_hebrew - 1].rstrip())
    if args.show_egyptian:
        card_id = f"WO-C-OPEN-COMP-{args.show_egyptian:05d}"
        match = re.search(
            rf"(?ms)^### {re.escape(card_id)}:.*?(?=^### |^<!-- |\Z)", egyptian
        )
        assert match
        print("\n" + match.group().rstrip())
    if args.apply:
        hebrew_memory, egyptian_memory, report_memory = memories
        with HEBREW.open("a", encoding="utf-8", newline="\n") as handle:
            if not hebrew_memory.endswith("\n"):
                handle.write("\n")
            handle.write("\n" + hebrew)
        with EGYPTIAN.open("a", encoding="utf-8", newline="\n") as handle:
            if not egyptian_memory.endswith("\n"):
                handle.write("\n")
            handle.write("\n" + egyptian)
        with REPORT.open("a", encoding="utf-8", newline="\n") as handle:
            if not report_memory.endswith("\n"):
                handle.write("\n")
            handle.write(report)
        print(f"APPENDED: {HEBREW.relative_to(ROOT)}")
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
