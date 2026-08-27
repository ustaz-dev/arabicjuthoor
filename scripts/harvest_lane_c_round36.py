#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 36 completion cards without shipping or git.

The live short Aramaic queue is checked before the registered Egyptian open
queue continues. The script completes WO-C-OPEN-COMP-02143..02222 in two
forty-card batches and accepts only the current closed closure vocabulary.
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

import harvest_lane_c_round35 as R35


R9 = R35.R9
AR = R35.AR
ROOT = R35.ROOT
ARAMAIC = R35.ARAMAIC
EGYPTIAN = R35.EGYPTIAN
REPORT = R35.REPORT

MARKER = "LANE-C-ROUND36-2026-08-27"
FIRST_SERIAL = 2143
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)
LEGAL_CLOSURES = R35.LEGAL_CLOSURES


def gap(member_id: str, candidate: str, state: str, reason: str,
        sound: str = "المروحة بنيوية فقط؛ لا يرقى التشابه إلى قانون أو نسب.",
        orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
        keywords: str = "", zero: str = "") -> R9.Decision:
    return R35.gap(
        member_id, candidate, state, reason, sound, orbit, keywords, zero,
    )


def caus_gap(member_id: str, candidate: str, state: str, reason: str,
             morphology: str, remainder: str,
             sound: str = "المروحة بنيوية فقط؛ لا يرقى التشابه إلى قانون أو نسب.",
             orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
             keywords: str = "") -> R9.Decision:
    zero = (
        f"عزلت s السابقة السببية المسماة في `{morphology}`؛ بقي "
        f"`{remainder}` كاملا بلا إسقاط صامت جذري."
    )
    return gap(
        member_id, candidate, state, reason, sound, orbit, keywords, zero,
    )


# No positive is issued. The strongest semantic contacts are deliberately
# stopped at their first failed gate: nhzi and hwrw lack a licensed zero;
# sjqr lacks named causative morphology and an Egyptian j-to-w row; sjdi has
# a full sound route after named causative stripping but its frozen event is
# hand-based enabling rather than disablement; the other raised contacts lack
# one or more signed Egyptian sound legs. Every other member names its own
# lexical, source, or direction blocker.
DECISIONS: tuple[R9.Decision, ...] = (
    gap("aed-v1.0:25950", "يميم", "OPEN-CANDIDATE", "be effective/make effective لا يطابق يميم أو يمءم في العربية الممسوحة، ولا يدخل نفاذ الخطة أو نجاحها من خارج الرسم."),
    gap("aed-v1.0:26970", "ينين", "OPEN-CANDIDATE", "cut up لا يجد في ينين أو ينءن مادة قطع عربية عاملة، ولا يدخل نشر أو بتر من خارج الرسم."),
    gap("aed-v1.0:27260", "ينبء", "OPEN-CANDIDATE", "be mute لا يطابق ينبء أو ينبا وينبل وينبر في العربية الممسوحة، ولا يدخل بكم أو صمت من خارج الرسم."),
    gap("aed-v1.0:43260", "واخي", "OPEN-CANDIDATE", "flood/make verdant/rejoice لا يطابق واخي أو واخء ولا نظائر اللام والراء في المروحة؛ لم يورث أحد المعاني الثلاثة للآخر."),
    gap("aed-v1.0:43410", "واسي", "OPEN-CANDIDATE", "be ruined/fallen down لا يطابق واسي أو واشي وواصي ولا نظائر اللام والراء في العربية الممسوحة، ولا يدخل خراب من خارج الرسم."),
    gap("aed-v1.0:44420", "وعوع", "OPEN-CANDIDATE", "وعوعة الكلب والذئب وخطابة الوعوع لا تطابق cut down an enemy؛ الصوت أو المدح والذم لا يصير قتلا."),
    gap("aed-v1.0:50310", "وسوس", "OPEN-CANDIDATE", "الوسوسة حديث النفس والصوت الخفي، لا strike أو break into؛ لم يحول خفاء الصوت إلى ضربة أو اقتحام."),
    gap("aed-v1.0:53990", "باقي", "OPEN-CANDIDATE", "be weary لا يطابق باقي أو باقء ولا صور الجيم والقاف والغين في المروحة؛ البقاء ليس التعب."),
    gap("aed-v1.0:54250", "بيت", "OPEN-CANDIDATE", "be king of Lower Egypt فعل منصب ملكي مخصوص لا يطابق بيت في الدار والمبيت والعيال، ولا يورث المنصب معنى الملك لمادة بيت."),
    gap("aed-v1.0:54330", "بيري", "OPEN-CANDIDATE", "be far/remove oneself لا يطابق بيري أو بيرء ولا صور الهمزة واللام في العربية الممسوحة؛ لا يدخل بعد أو تنح من خارج الرسم."),
    gap("aed-v1.0:55080", "بعحي", "OPEN-CANDIDATE", "flood/inundate لا يطابق بعحي أو بضحي وبغحي في العربية الممسوحة، ولا يدخل غمر أو فيض من خارج الرسم."),
    gap("aed-v1.0:55770", "بنبن", "OPEN-CANDIDATE", "make the Nile flow/swell لا يجد في بنبن مادة عربية عاملة للجريان أو الانتفاخ، ولا يرث معنى الفيضان من السياق."),
    gap("aed-v1.0:56830", "بحني", "OPEN-CANDIDATE", "cut up/cut off/punish لا يطابق بحني أو بحنء في العربية الممسوحة، ولا يجمع القطع والعقوبة بجذر مدخل من خارج الرسم."),
    gap("aed-v1.0:59230", "فاخد", "OPEN-CANDIDATE", "be turned upside down/turned over لا يطابق فاخد أو فاخض ولا نظائر الباء واللام والراء في المروحة، ولا يدخل قلب من خارج الرسم."),
    gap("aed-v1.0:59300", "فلقي", "OPEN-CANDIDATE", "be thin لا يطابق فلقي؛ وفلق العربية للشق لا للنحول أو رقة السمك، فلا يسوى أثر الشق بصفة الرقة."),
    gap("aed-v1.0:59540", "بيبي", "OPEN-CANDIDATE", "make bricks/knead clay لا يطابق بيبي أو فيفي وبقية المروحة في العربية الممسوحة، ولا يدخل لبن أو عجن من خارج الرسم."),
    gap("aed-v1.0:59670", "بعبع", "OPEN-CANDIDATE", "bear/be born لا يطابق بعبع أو بعفع ولا صور الضاد والغين والفاء في المروحة، ولا يدخل ولد من خارج الرسم."),
    gap("aed-v1.0:61620", "فحط", "OPEN-CANDIDATE", "be strong لا يطابق فحط أو فحت ولا نظائر الباء في العربية الممسوحة، ولا يدخل قوة من خارج الرسم."),
    gap("aed-v1.0:66940", "مروي", "OPEN-CANDIDATE", "be new/become new لا يطابق مروي أو ملوي وماوي في العربية الممسوحة؛ الري والشرب أو الرواية لا يصيران جدة."),
    gap("aed-v1.0:67590", "مروت", "OPEN-CANDIDATE", "think up لا يطابق مروت أو ملوت وماوت في العربية الممسوحة، ولا يدخل فكر من خارج الرسم."),
    gap("aed-v1.0:69380", "مفكر", "OPEN-CANDIDATE", "be glad/rejoice لا يطابق مفكر في التفكير ولا مفكء ومفكل؛ لا يحول التفكر إلى فرح."),
    gap("aed-v1.0:76660", "مقمق", "OPEN-CANDIDATE", "sleep لا يجد في مقمق مادة نوم عربية عاملة، ولا يدخل رقد أو نعس من خارج الرسم."),
    gap("aed-v1.0:78140", "مدوي", "OPEN-CANDIDATE", "speak/claim لا يطابق مدوي أو مضوي؛ ودوي الصوت لا يرخص إسقاط m ولا يسمي الكلام أو الادعاء نفسه."),
    gap("aed-v1.0:80080", "نوي", "OPEN-CANDIDATE", "come to rest، ولا سيما وقوف الفيضان، لا يطابق نوي في القصد والتحول والبعد ونواة الثمر؛ لا يدخل سكن من خارج الرسم."),
    gap("aed-v1.0:82770", "نبنب", "OPEN-CANDIDATE", "bring forth the inundation لا يجد في نبنب مادة عربية عاملة للفيضان أو الإخراج، ولا يرث حكم بنبن المصري المجاور."),
    gap("aed-v1.0:85790", "نهز", "MORPHOLOGY-GAP", "نهز رأسه حركه ونهزت الدابة إذا نهضت بصدرها يلامسان awaken، لكن j النهائية في nhzi̯ لا تملك صفرا صرفيا مسمى، والمرشح الثلاثي خارج سطح المروحة.", sound="n↔ن وh↔ه وz↔ز ظاهرة؛ بقيت j النهائية المصرية بلا مقابل بعد المرشح نهز.", orbit="تحريك الرأس ونهوض الدابة انتقال من السكون إلى الحركة فيلامس الإيقاظ، وبقي فرق الحدث واللام الضعيفة مانعين.", keywords="نهز رأسه|حركه|نهضت بصدرها|النهوض", zero="حفظت n-h-z-j لأن AED يسجل `verb_4-inf` ولا يسمي صفرا للياء النهائية؛ عرض نهز اختبار دلالة لا تعرية مصدرة."),
    gap("aed-v1.0:88780", "نشني", "OPEN-CANDIDATE", "rage/be furious لا يطابق نشني أو نشنء ولا نسني ونسنء في العربية الممسوحة، ولا يدخل غضب من خارج الرسم."),
    gap("aed-v1.0:89190", "نقدد", "OPEN-CANDIDATE", "sleep لا يطابق نقدد أو نقدض ونقضد ونقضض؛ النقد والنقض لا يسميان النوم."),
    gap("aed-v1.0:90400", "نثري", "OPEN-CANDIDATE", "be divine/make divine لا يطابق نثري أو نتري ونطري في العربية الممسوحة، ولا يدخل إله أو قدس من خارج الرسم."),
    gap("aed-v1.0:90520", "نثري", "OPEN-CANDIDATE", "purify with natron/be pure through natron لا يطابق نثري أو نتري ونطري؛ النثر ليس التطهير ولا مادة النطرون مصدرة هنا كجذر عربي."),
    gap("aed-v1.0:94400", "رمني", "OPEN-CANDIDATE", "carry/support لا يطابق رمني أو رمنء ولا لمني ولمنء في العربية الممسوحة، ولا يدخل حمل أو سند من خارج الرسم."),
    gap("aed-v1.0:95000", "رنفي", "OPEN-CANDIDATE", "be young/become young again لا يطابق رنفي أو رنبي ولا نظائر اللام في العربية الممسوحة، ولا يدخل فتى أو شباب من خارج الرسم."),
    gap("aed-v1.0:99250", "هرثث", "SOURCE-GAP", "الإنجليزية تقول do stealthily، والألمانية تضع heimlich tun نفسها موضع سؤال؛ لا حدث خفي واحدا محسوما يقارن بهرثث أو بقية المروحة."),
    gap("aed-v1.0:101030", "حاعب", "SOURCE-GAP", "cut وmutilate كلاهما موسومان بالسؤال في AED؛ لا قطع أو تشويه محسوما يقارن بحاعب وحاضب وحاغب قبل تثبيت الحس."),
    gap("aed-v1.0:103190", "حور", "MORPHOLOGY-GAP", "الحور للنقصان والهلكة يلامس wretched/weak، لكن ḥwrw عضو رباعي ولا يملك w النهائية صفرا صرفيا مسمى؛ لم يحمل حكم الأسرة ḥwr إلى العضو بالقوة.", sound="ḥ↔ح في IDN-14 وw↔و في IDN-10 وr↔ر في IDN-01؛ بقيت w النهائية المصرية بلا مقابل مستقل.", orbit="الحور نقصان بعد زيادة وهلكة، وهو قريب من الضعف وسوء الحال؛ بقيت بنية العضو الرباعية مانعة.", keywords="الحور|النقصان|الهلكة|الحور بعد الكور", zero="حفظت ḥ-w-r-w كاملة لأن AED يسجل `verb_4-lit`؛ ورود ḥwr في الأسرة لا يسمي w النهائية لاحقة قابلة للنزع."),
    gap("aed-v1.0:103200", "حور", "SOURCE-GAP", "speak evil موسوم بالسؤال في الإنجليزية، وفصل هذا العضو عن متجانسه wretched/weak واجب؛ لا يرث الحور أو حكم الضعف لتثبيت فعل كلام غير محسوم."),
    gap("aed-v1.0:103560", "حابي", "OPEN-CANDIDATE", "be in festival لا يطابق حابي أو حابء ولا حلبي وحربي في العربية الممسوحة، ولا يدخل عيد أو احتفال من خارج الرسم."),
    gap("aed-v1.0:104530", "حفحف", "SOURCE-GAP", "الإنجليزية تقترح hear بعلامة سؤال بينما الألمانية تقول huldigend aussprechen؛ اختلاف السماع والنطق التعظيمي يمنع تعيين حدث واحد."),
    gap("aed-v1.0:105780", "حمسي", "OPEN-CANDIDATE", "sit/sit down/occupy لا يطابق حمسي أو حمشي وحمصي في العربية الممسوحة، ولا يدخل جلس أو سكن من خارج الرسم."),
    gap("aed-v1.0:106910", "حنرج", "DIRECTION-GAP", "quake/be embarrassed موسوم Sem. loan word بلا مانح سامي فردي أو طريق انتقال، ولا تسمي حنرج وحنرق وحنرغ هذا الحدث.", orbit="الارتجاف والانكسار النفسي مدارا العضو المصري، لكن وسم القرض العام لا يعين مادة عربية أو جهة انتقال."),
    gap("aed-v1.0:107400", "حنتي", "OPEN-CANDIDATE", "be covetous/greedy لا يطابق حنتي أو حنطي في العربية الممسوحة، ولا يدخل حرص أو طمع من خارج الرسم."),
    gap("aed-v1.0:109210", "حرست", "OPEN-CANDIDATE", "make the eyes red/be red with rage لا يطابق حرست أو حرشت وحرصت؛ الحرص والحرس لا يسميان حمرة العين."),
    gap("aed-v1.0:110050", "حسمن", "OPEN-CANDIDATE", "drink/eat لا يطابق حسمن أو حزمن في العربية الممسوحة، ولا يدخل شرب أو أكل من خارج الرسم."),
    gap("aed-v1.0:114360", "خاطب", "OPEN-CANDIDATE", "take pity on لا يطابق خاطب أو خاتب ولا صور الهمزة واللام والراء في المروحة؛ الخطاب ليس الشفقة."),
    gap("aed-v1.0:116990", "خمار", "SOURCE-GAP", "الإنجليزية تقترح convulsion بعلامتي سؤال بينما الألمانية تقول schrumpeln؛ اختلاف الاختلاج والانكماش يمنع تعيين حدث واحد."),
    gap("aed-v1.0:118000", "خنفر", "SOURCE-GAP", "arrogant/aggressive كلاهما موسوم بالسؤال، والعربية لا تعطي في خنفر إلا أعلاما ومواضع؛ لا صفة سلوكية محكومة للمقارنة."),
    gap("aed-v1.0:118240", "خنمس", "OPEN-CANDIDATE", "be friendly with لا يطابق خنمس أو خنمش وخنمص في العربية الممسوحة، ولا يدخل صداقة أو أنس من خارج الرسم."),
    gap("aed-v1.0:119130", "خنتي", "OPEN-CANDIDATE", "be in front of لا يطابق خنتي أو خنطي في العربية الممسوحة، ولا يدخل أمام أو صدر من خارج الرسم."),
    caus_gap("aed-v1.0:128000", "يعر", "OPEN-CANDIDATE", "make ascend/present بعد عزل السابقة السببية لا يطابق يعر في الجدي وصياح العنز والربط، ولا يدخل رفع أو تقديم من خارج الجذر.", "verb_caus_3-lit", "j-ꜥ-r"),
    gap("aed-v1.0:128050", "سيوي", "OPEN-CANDIDATE", "say loudly/announce/complain/praise لا يطابق سيوي أو سيوء في العربية الممسوحة؛ وأبقيت s لأن AED لا يسمي الفعل سببيا."),
    caus_gap("aed-v1.0:128090", "يور", "OPEN-CANDIDATE", "make pregnant/make conceive بعد عزل السابقة السببية لا يطابق يور أو يول وءور وءول في العربية الممسوحة، ولا يدخل حمل من خارج الجذر.", "verb_caus_3-lit", "j-w-r"),
    gap("aed-v1.0:128310", "سيام", "OPEN-CANDIDATE", "make well-disposed لا يطابق سيام أو سيرم ولا نظائر الشين والصاد؛ وأبقيت s لأن AED يسجل القسم verb بلا تعرية سببية مسماة."),
    caus_gap("aed-v1.0:128490", "يند", "OPEN-CANDIDATE", "make miserable بعد عزل السابقة السببية لا يطابق يند أو ينض في العربية الممسوحة، ولا يدخل حزن أو بؤس من خارج الجذر.", "verb_caus_3-lit", "j-n-d"),
    gap("aed-v1.0:128590", "وقر", "MORPHOLOGY-GAP", "وقر ووقر الرجل والتوقير يلامس enrich/make excellent في الثقل والكرامة، لكن AED يسجل القسم verb ولا يسمي s سابقة سببية؛ وفوق ذلك j↔و بلا صف مصري موقع.", sound="q↔ق في IDN-12 وr↔ر في IDN-01؛ j المصرية بإزاء و العربية غير موقعة للمصرية، وs محفوظة لغياب تعرية مسماة.", orbit="الوقار ثبات وحلم وعظمة، والتوقير التعظيم؛ وهو قريب من جعل الشخص ممتازا أو مكرما، وبقي الصرف والصوت مانعين.", keywords="الوقار|التوقير|وقر الرجل|عظمه|الحلم", zero="لم أعزل s: AED يسجل `verb` فقط، والأسرة المرتبطة jqr لا تكفي وحدها لتسمية السابقة؛ حفظت s-j-q-r كاملة."),
    caus_gap("aed-v1.0:128640", "يدي", "TOOL-GAP", "يدي فلان من يده إذا شلت يلامس make powerless والصوت كامل بعد عزل s، لكن الحدث المجمد ليدي ينزل إلى اليد والامتداد للتمكين لا إلى سلب القدرة.", "verb_caus_3-inf", "j-d-j", sound="j↔ي عبر GLD-02 وd↔د في IDN-09 وi̯/j↔ي عبر GLD-02؛ الجذر كامل بعد عزل s.", orbit="شلل اليد يضعف قدرة صاحبها مباشرة، لكن العربية تقصر الحدث على اليد والمصرية تعم سلب القدرة؛ بقي حدث الأداة المجمد مانعا.", keywords="يدي من يده|شلت|مقطوع اليد|يدي يده"),
    caus_gap("aed-v1.0:128660", "علو", "LAW-GAP", "العلا والعلو للرفعة والعظمة يطابقان make great/increase، لكن ꜣ↔ل وj↔و بلا صفين مصريين موقعين بعد عزل s.", "verb_caus_3-inf", "ꜥ-ꜣ-j", sound="ꜥ↔ع في IDN-15؛ ꜣ↔ل وj↔و هما الرجلان المصريتان غير الموقعتين.", orbit="العلو رفعة وعظمة، وأعلى الشيء وعلاه جعله عاليا؛ مدار جعل العظيم أو الأعلى مباشر، وبقي الصوت مانعا.", keywords="العلو|العلا|الرفعة|العظمة|أعلاه"),
    caus_gap("aed-v1.0:128740", "عوا", "OPEN-CANDIDATE", "cause to go bad/ferment بعد عزل السابقة السببية لا يطابق عوا أو عول وعور وضوا وغوا في العربية الممسوحة، ولا يدخل خمر أو فسد من خارج الجذر.", "verb_caus_3-lit", "ꜥ-w-ꜣ"),
    caus_gap("aed-v1.0:128910", "عنخ", "OPEN-CANDIDATE", "make live/perpetuate/nourish بعد عزل السابقة السببية لا يطابق عنخ أو ضنخ وغنخ في العربية الممسوحة، ولا يدخل حي أو غذى من خارج الجذر.", "verb_caus_3-lit", "ꜥ-n-ḫ"),
    caus_gap("aed-v1.0:129030", "عرق", "OPEN-CANDIDATE", "complete/bring to an end بعد عزل السابقة السببية لا يطابق عرق في الرشح والنسج والصف والنتاج، ولا يدخل تم أو أنهى من خارج الجذر.", "verb_caus_3-lit", "ꜥ-r-q"),
    caus_gap("aed-v1.0:129190", "عحع", "OPEN-CANDIDATE", "erect/set up/make stand بعد عزل السابقة السببية لا يجد في عحع أو عحض وعحغ مادة قيام عربية عاملة، ولا يدخل نصب من خارج الجذر.", "verb_caus_3-lit", "ꜥ-ḥ-ꜥ"),
    caus_gap("aed-v1.0:129220", "علو", "LAW-GAP", "علا الشيء وأعلاه يطابق make rise the heavens، لكن ḫ↔ل وj↔و بلا صفين مصريين موقعين بعد عزل s.", "verb_caus_3-inf", "ꜥ-ḫ-j", sound="ꜥ↔ع في IDN-15؛ ḫ↔ل وj↔و هما الرجلان المصريتان غير الموقعتين.", orbit="علا في المكان أي ارتفع، وأعلاه رفعه؛ وهو مدار رفع السماء مباشرة، وبقي الصوت مانعا.", keywords="علا|ارتفع|أعلاه|رفعه|العلو"),
    caus_gap("aed-v1.0:129260", "عشر", "LAW-GAP", "عشرت القوم إذا كانوا تسعة فجعلتهم عشرة يلامس make numerous/multiply، لكن ꜣ المصرية بإزاء ر العربية بلا صف مصري موقع بعد عزل s.", "verb_caus_3-lit", "ꜥ-š-ꜣ", sound="ꜥ↔ع في IDN-15 وš↔ش في IDN-21؛ ꜣ↔ر هي الرجل المصرية غير الموقعة.", orbit="تعشير القوم زيادة عددهم إلى عشرة، والعشر في السجل المجمد تجمع وكثرة؛ مدار التكثير مباشر ومقيد بالعدد العربي، وبقي الصوت مانعا.", keywords="عشرت القوم|جعلتهم عشرة|عشرة|التعشير|الكثرة"),
    caus_gap("aed-v1.0:129360", "عقر", "LAW-GAP", "عقر الفرس كشف قوائمه حتى سقط مائلا يلامس make capsize، لكن g↔ق وꜣ↔ر بلا صفين مصريين موقعين بعد عزل s.", "verb_caus_3-lit", "ꜥ-g-ꜣ", sound="ꜥ↔ع في IDN-15؛ g↔ق وꜣ↔ر هما الرجلان المصريتان غير الموقعتين.", orbit="إسقاط الدابة المعقورة على جانبها قريب من قلب المركب، لكنه فعل في الحيوان لا اسم انقلاب عام؛ بقي الصوت مانعا.", keywords="عقرت الفرس|قوائمها|سقطت|المائل|عقرت البعير"),
    caus_gap("aed-v1.0:129800", "وري", "OPEN-CANDIDATE", "make distant بعد عزل السابقة السببية لا يطابق وري في داء الرئة وإيراء النار، ولا يدخل بعد أو نأى من خارج الجذر.", "verb_caus_3-inf", "w-ꜣ-j"),
    caus_gap("aed-v1.0:129860", "ورح", "OPEN-CANDIDATE", "make endure/endure بعد عزل السابقة السببية لا يجد في ورح أو ولح وواح مادة دوام عربية عاملة، ولا يدخل بقي من خارج الجذر.", "verb_caus_3-lit", "w-ꜣ-ḥ"),
    caus_gap("aed-v1.0:130000", "وعي", "OPEN-CANDIDATE", "make alone بعد عزل السابقة السببية لا يطابق وعي في الحفظ والجبر والاحتواء؛ لا يجعل حفظ الشيء إفرادا له.", "verb_caus_3-inf", "w-ꜥ-j"),
    caus_gap("aed-v1.0:130040", "وبر", "OPEN-CANDIDATE", "open someone's face بعد عزل السابقة السببية لا يطابق وبر في شعر البعير والدويبة والموضع، ولا يدخل فتح من خارج الجذر.", "verb_caus_3-lit", "w-b-ꜣ"),
    caus_gap("aed-v1.0:130080", "ومت", "OPEN-CANDIDATE", "make thick بعد عزل السابقة السببية لا يطابق ومت في الشيء المعروف المقدر، ولا يدخل غلظ أو ثخن من خارج الجذر.", "verb_caus_3-lit", "w-m-t"),
    caus_gap("aed-v1.0:130730", "وسر", "OPEN-CANDIDATE", "make strong/enrich بعد عزل السابقة السببية لا يجد في وسر أو وشر ووصل مادة قوة أو غنى عاملة، ولا يدخل ثراء من خارج الجذر.", "verb_caus_3-lit", "w-s-r"),
    gap("aed-v1.0:130800", "وجل", "OPEN-CANDIDATE", "be foolish لا يطابق وجل في الخوف ولا وجر ووقر وبقية المروحة؛ الخوف ليس الحمق."),
    caus_gap("aed-v1.0:131430", "برق", "LAW-GAP", "برق السيف أي تلألأ ولمع يطابق make bright، لكن ꜣ المصرية بإزاء ر العربية بلا صف مصري موقع بعد عزل s.", "verb_caus_3-lit", "b-ꜣ-q", sound="b↔ب في IDN-05 وq↔ق في IDN-12؛ ꜣ↔ر هي الرجل المصرية غير الموقعة.", orbit="البرق والبريق لمعان ظاهر، والمصرية تسمي جعل الشيء مضيئا؛ المدار مباشر، وبقي الصوت الأوسط مانعا.", keywords="برق السيف|تلألأ|لمع|البريق|البرق"),
    caus_gap("aed-v1.0:131810", "بنن", "OPEN-CANDIDATE", "give suck بعد عزل السابقة السببية لا يطابق بنن في الرائحة وأطراف الأصابع والإقامة، ولا يدخل رضاع من خارج الجذر.", "verb_caus_2-gem", "b-n-n"),
    caus_gap("aed-v1.0:131850", "بني", "OPEN-CANDIDATE", "make sweet/pleasant بعد عزل السابقة السببية لا يطابق بني في البناء والنشأة والولد، ولا يجعل إحكام البناء حلاوة حسية أو لطفا.", "verb_caus_3-lit", "b-n-j"),
    caus_gap("aed-v1.0:131890", "بهر", "OPEN-CANDIDATE", "make flee بعد عزل السابقة السببية لا يطابق بهر في الغلبة والعجب وتتابع النفس؛ الغلبة سبب محتمل للفرار لا فعل الفرار نفسه.", "verb_caus_3-lit", "b-h-ꜣ"),
    caus_gap("aed-v1.0:132190", "بكر", "OPEN-CANDIDATE", "make pregnant لا يطابق بكر في البكارة وأول الولد والتبكير؛ تماس الولادة والأولية لا يجعل المادة فعلا للإحبال، وꜣ↔ر غير موقع.", "verb_caus_3-lit", "b-k-ꜣ", sound="b↔ب في IDN-05 وk↔ك في IDN-13؛ ꜣ↔ر غير موقع للمصرية، كما بقي فرق الحدث.", orbit="البكر المرأة التي ولدت بطنا واحدا أو العذراء قبل الولادة، والمصرية تسمي إحداث الحمل؛ المجاورة الإنجابية لا تطابق الحدث.", keywords="البكر|ولدت بطنا واحدا|العذراء|الولد"),
    caus_gap("aed-v1.0:132290", "بدش", "OPEN-CANDIDATE", "make weak بعد عزل السابقة السببية لا يجد في بدش أو بدس وبضش وبضس مادة ضعف عربية عاملة، ولا يدخل وهن من خارج الجذر.", "verb_caus_3-lit", "b-d-š"),
    caus_gap("aed-v1.0:132670", "فري", "OPEN-CANDIDATE", "make fly بعد عزل السابقة السببية لا يطابق فري في الشق والقطع والإفساد والإصلاح، ولا يدخل طير من خارج الجذر.", "verb_caus_2-lit", "p-ꜣ-j"),
    caus_gap("aed-v1.0:132930", "فري", "OPEN-CANDIDATE", "make miss/expel بعد عزل السابقة السببية لا يطابق فري في الشق والقطع؛ إخراج جزء بالقطع لا يساوي الطرد أو جعل الشيء يخطئ.", "verb_caus_3-inf", "p-r-j"),
    gap("aed-v1.0:133860", "زفزف", "SOURCE-GAP", "break موسوم بالسؤال في الإنجليزية وإن قطعت الألمانية بالترجمة؛ لا حدث كسر محسوما يقارن بزفزف أو زفسف وسفزف."),
    gap("aed-v1.0:133870", "سفسف", "OPEN-CANDIDATE", "burn up/reduce to ashes لا يطابق سفسف أو سفشف وسفصف في العربية الممسوحة، ولا يدخل حرق أو رماد من خارج الرسم."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT
assert {item.state for item in DECISIONS} <= LEGAL_CLOSURES
assert {item.verdict for item in DECISIONS} <= LEGAL_CLOSURES

OUTSIDE_FAN = {
    "aed-v1.0:85790", "aed-v1.0:128590", "aed-v1.0:128660",
    "aed-v1.0:129220",
}

WITNESS_NOTES = {
    "aed-v1.0:85790": "أثبت لسان العرب وتاج العروس نهز الرأس بمعنى حركه ونهوض الدابة بصدرها؛ ثبت تماس الحركة بعد السكون، وبقيت j النهائية بلا صفر مسمى.",
    "aed-v1.0:103190": "أثبت لسان العرب وتاج العروس الحور للنقصان والهلكة؛ ثبت تماس الضعف وسوء الحال، وبقيت w النهائية بلا تعرية مسماة.",
    "aed-v1.0:128590": "أثبت لسان العرب وتاج العروس الوقار والتوقير في الثقل والحلم والعظمة؛ ثبت تماس الامتياز، وبقيت السابقة والصوت غير محكومين.",
    "aed-v1.0:128640": "أثبت كتاب العين ولسان العرب يدي فلان من يده إذا شلت ويدي يده؛ ثبت سلب قدرة اليد، وبقي الحدث المجمد للتمكين مانعا.",
    "aed-v1.0:128660": "أثبت كتاب العين والمحكم العلو والعلا في الرفعة والعظمة وأعلاه بمعنى رفعه؛ ثبت المدار، وبقيت رجلان صوتيتان.",
    "aed-v1.0:129220": "أثبت كتاب العين والمحكم علا الشيء وارتفع وأعلاه ورفعه؛ ثبت مدار رفع السماء، وبقيت رجلان صوتيتان.",
    "aed-v1.0:129260": "أثبت أساس البلاغة وتاج العروس عشرت القوم إذا جعلت التسعة عشرة؛ ثبت مدار زيادة العدد، وبقي ꜣ↔ر بلا صف مصري.",
    "aed-v1.0:129360": "أثبت كتاب العين ولسان العرب عقر الفرس وضرب قوائمه حتى سقط مائلا؛ ثبت تماس القلب والإسقاط، وبقيت رجلان صوتيتان.",
    "aed-v1.0:131430": "أثبت لسان العرب وتاج العروس برق الشيء بمعنى لمع وتلألأ؛ ثبت مدار الإضاءة، وبقي ꜣ↔ر بلا صف مصري.",
}


def round36_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R35.round35_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND35-COMPLETION", "ROUND36-COMPLETION")
    card = card.replace(
        "ROUND36-COMPLETION (2026-08-26)",
        "ROUND36-COMPLETION (2026-08-27)",
    )
    card = card.replace(
        f"round35-egyptian-rank={rank}/{CARD_COUNT}",
        f"round36-egyptian-rank={rank}/{CARD_COUNT}",
    )
    if decision.zero:
        card = re.sub(
            r"(?m)^- الخطوة صفر:.*$",
            f"- الخطوة صفر: {decision.zero}",
            card,
        )
    if decision.member_id in OUTSIDE_FAN:
        card = card.replace(
            "المقابل خارج سطح المروحة، واستعيد من نص المصدر أو طبقة صرف مسماة",
            "المقابل خارج سطح المروحة؛ سجل بوصفه مطابقة دلالية مرفوعة لا مرشحا صوتيا مرخصا",
        )
    note = WITNESS_NOTES.get(decision.member_id)
    if note:
        root = AR.normalize_root(decision.candidate)
        count = len(matches.get(root, []))
        card = re.sub(
            r"(?m)^- مسح المعاني العربية:.*$",
            (
                f"- مسح المعاني العربية: قرئت {count} نتيجة للجذر `{root}` "
                f"بما يكافئ `--max-chars 0`؛ {note}"
            ),
            card,
        )
    size = len(card.encode("utf-8"))
    assert size <= R9.MAX_CARD_BYTES, (
        f"Oversize WO-C-OPEN-COMP-{serial:05d}: {size} bytes"
    )
    return card


def render_appendices() -> tuple[str, str, dict]:
    aramaic_text = ARAMAIC.read_text(encoding="utf-8")
    egyptian_text = EGYPTIAN.read_text(encoding="utf-8")
    report_text = REPORT.read_text(encoding="utf-8")
    if MARKER in egyptian_text or MARKER in report_text:
        raise SystemExit("Round-thirty-six marker already exists; append refused.")

    aramaic_exact, _ = R9.load_entries("aramaic")
    aramaic_queue = R9.select_aramaic(aramaic_text, aramaic_exact)
    assert not aramaic_queue, (
        "Aramaic short live-open queue is no longer exhausted: "
        f"{[item['entry_id'] for item in aramaic_queue[:10]]}"
    )

    egyptian_exact, _ = R9.load_entries("egyptian")
    queue = R35.R34.R33.R32.R31.R30.R29.select_egyptian_fast(
        egyptian_text, egyptian_exact,
    )
    selected = queue[:CARD_COUNT]
    actual_ids = tuple(str(item["entry_id"]) for item in selected)
    assert actual_ids == EXPECTED_IDS, (
        f"Egyptian queue drifted:\nexpected={EXPECTED_IDS}\nactual={actual_ids}"
    )
    assert all("ḏ" not in str(item["headword"]) for item in selected)

    roots = {
        AR.normalize_root(item.candidate)
        for item in DECISIONS if item.candidate not in {"", "∅"}
    }
    matches = AR.matches_for_roots(AR.DEFAULT_RESOURCES, roots, None)
    cards = [
        round36_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة السادسة والثلاثون: استمرار المخزون المصري المسجل المفتوح (2026-08-27)", "",
        (
            "أعيد فحص الآرامية أولا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرا، فسجل الانتقال المسمى `{TRANSITION}`. انتقيت ثمانين "
            "بطاقة مصرية بدءا من `WO-C-OPEN-COMP-02143` بقصر الهيكل ثم موضع "
            "اللقطة. استبعد صف ḏ المؤجل. في كل بطاقة عرضت إصابات AED كلها بلا "
            "حد، وكتب وسم الطريق والرسم والمدخل المختار، وحفظ الاختلاف "
            "والمتجانسات بلا محو. فحصت حالة الإغلاق والحكم آليا على القائمة "
            "القانونية وحدها في `data/closure-vocabulary.json`."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-02143 إلى WO-C-OPEN-COMP-02182", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-02183 إلى WO-C-OPEN-COMP-02222", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([
                f"<!-- LANE-C-R36-EGYPTIAN-CHUNK-{rank:03d}:END -->", "",
            ])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    states = dict(sorted(collections.Counter(
        item.state for item in DECISIONS
    ).items()))
    verdicts = dict(sorted(collections.Counter(
        item.verdict for item in DECISIONS
    ).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    now = datetime.now(ZoneInfo("Africa/Cairo")).strftime(
        "%Y-%m-%d %H:%M:%S %z"
    )
    now = now[:-2] + ":" + now[-2:]
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة السادسة والثلاثون: المسار C، الساميات والمصرية (2026-08-27)", "",
        f"- الوقت: {now}.",
        "- أعيد فحص الساميات أولا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-02143` إلى `WO-C-OPEN-COMP-02182`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-02183` إلى `WO-C-OPEN-COMP-02222`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طبق الانضباط الثلاثي: لم يصدر موجب في هذه النافذة؛ وكل بطاقة لها عائق شريف مسمى.",
        "- قاموس الإغلاق المغلق وحده مطبق: كل حالات الإغلاق والأحكام اجتازت القائمة القانونية في `data/closure-vocabulary.json`.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ لم يصدر موجب جديد.",
        "- أقرب تماس كامل الصوت بعد صرف مسمى `sjdi̯↔يدي` بقي `TOOL-GAP`: العربية تثبت شلل اليد، لكن الحدث المجمد يهبط إلى اليد والتمكين لا إلى سلب القدرة.",
        "- التماسان `nhzi̯↔نهز` و`ḥwrw↔حور` بقيا `MORPHOLOGY-GAP` لأن الصامت النهائي في كل عضو لا يملك صفرا صرفيا مسمى.",
        "- `sjqr↔وقر` بقي `MORPHOLOGY-GAP` لغياب وسم السببية في AED، مع بقاء j↔و غير موقع للمصرية.",
        "- المطابقات الدلالية المرفوعة بقيت فجوات قانون: `sꜥꜣi̯↔علو` للعظمة، و`sꜥḫi̯↔علو` للرفع، و`sꜥšꜣ↔عشر` لتكثير العدد، و`sꜥgꜣ↔عقر` للإسقاط، و`sbꜣq↔برق` للإضاءة.",
        "- وسم القرض السامي العام في `ḥnrg` بقي `DIRECTION-GAP` بلا مانح فردي أو طريق مكتمل.",
        "- الأفعال والمراجع المشكوكة أو المختلفة بين الإنجليزية والألمانية بقيت `SOURCE-GAP`، وصف ḏ المصري المؤجل بقي مستبعدا.",
        "- لم يحدث شحن أو إيداع أو إعداد مرحلي، ولم يستعمل git أو تحدث مشتقات النشر.", "",
        f"LANE-C DONE36 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
    ]) + "\n"

    diagnostics = {
        "aramaic_live_open": len(aramaic_queue),
        "transition": TRANSITION,
        "egyptian_queue_before": len(queue),
        "batch_1": BATCH_SIZE,
        "batch_2": CARD_COUNT - BATCH_SIZE,
        "total_cards": CARD_COUNT,
        "first_card": f"WO-C-OPEN-COMP-{FIRST_SERIAL:05d}",
        "last_card": f"WO-C-OPEN-COMP-{last_serial:05d}",
        "states": states,
        "verdicts": verdicts,
        "closure_vocabulary_only": True,
        "max_card_bytes": max(len(card.encode("utf-8")) for card in cards),
    }
    egyptian_appendix = unicodedata.normalize(
        "NFC", "\n".join(body).rstrip() + "\n",
    )
    report_appendix = unicodedata.normalize("NFC", report)
    return egyptian_appendix, report_appendix, diagnostics


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--show", type=int,
        choices=range(FIRST_SERIAL, FIRST_SERIAL + CARD_COUNT),
    )
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    egyptian, report, diagnostics = render_appendices()
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    if args.show:
        card_id = f"WO-C-OPEN-COMP-{args.show:05d}"
        match = re.search(
            rf"(?ms)^### {re.escape(card_id)}:.*?(?=^### |^<!-- |\Z)",
            egyptian,
        )
        assert match
        print("\n" + match.group().rstrip())
    if args.apply:
        append = (
            R35.R34.R33.R32.R31.R30.R29.R28.R27.R26.R25.R24.R23.R20.R10.append
        )
        append(EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian)
        append(REPORT, f"{MARKER}:REPORT", report)
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
