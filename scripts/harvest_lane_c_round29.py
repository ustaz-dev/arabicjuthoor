#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 29 completion cards without shipping or git.

The live short Aramaic queue is checked before the registered Egyptian open
queue continues. The script completes WO-C-OPEN-COMP-01583..01662 in two
forty-card batches and accepts only the current closed closure vocabulary.
"""

from __future__ import annotations

import argparse
import bisect
import collections
import json
import re
import sys
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

import harvest_lane_c_round28 as R28


R9 = R28.R9
AR = R28.AR
ROOT = R28.ROOT
ARAMAIC = R28.ARAMAIC
EGYPTIAN = R28.EGYPTIAN
REPORT = R28.REPORT

MARKER = "LANE-C-ROUND29-2026-08-26"
FIRST_SERIAL = 1583
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)
LEGAL_CLOSURES = R28.LEGAL_CLOSURES


def gap(member_id: str, candidate: str, state: str, reason: str,
        sound: str = "المروحة بنيوية فقط؛ لا يرقى التشابه إلى قانون أو نسب.",
        orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
        keywords: str = "", zero: str = "") -> R9.Decision:
    return R28.gap(
        member_id, candidate, state, reason, sound, orbit, keywords, zero,
    )


def terminal(member_id: str, candidate: str, verdict: str, reason: str,
             zero: str = "") -> R9.Decision:
    return R28.terminal(member_id, candidate, verdict, reason, zero)


# No positive is issued in this window. Close semantic contacts remain named
# gaps when the Egyptian sound route or the transfer direction is incomplete.
# Uncertain and unnamed AED referents remain source gaps, and the preposition
# is isolated structurally rather than forced into an Arabic lexical root.
DECISIONS: tuple[R9.Decision, ...] = (
    gap("aed-v1.0:111040", "حتا", "OPEN-CANDIDATE", "shabby/worn clothing لا يطابق حتا أو حتل أو حتر ولا حطا وحطل وحطر، ولا يدخل بلي أو رث من خارج الرسم."),
    gap("aed-v1.0:111130", "حتي", "OPEN-CANDIDATE", "smoke rising from an offering table لا يطابق حتي أو حطي ولا نوى حت وحط، ولا يكفي الارتفاع لإثبات دخان من خارج الرسم."),
    gap("aed-v1.0:111310", "حطب", "OPEN-CANDIDATE", "floral offering لا يطابق الحطب اليابس المعد للوقود، ولا تسوي فئة النبات بين الزهور والحطب."),
    gap("aed-v1.0:111590", "حتم", "OPEN-CANDIDATE", "provide with/complete لا يطابق حتم الأمر بمعنى أوجبه وقضاه، ولا تسقط الحاء لإدخال تم من النواة."),
    gap("aed-v1.0:111850", "حتر", "OPEN-CANDIDATE", "lashings لا يجد في حتر أو حتل أو حطر أو حطل اسما للرباط أو الحبل عاملا."),
    gap("aed-v1.0:111940", "حتس", "OPEN-CANDIDATE", "complete لا يطابق حتس أو حتش أو حتص ولا نظائر الطاء، ولا يدخل تم بإسقاط صامتين."),
    gap("aed-v1.0:112040", "حثت", "OPEN-CANDIDATE", "hyena لا يجد في حثت أو حتت أو حطت اسما للضبع عاملا، ولا ينتخب حيوانا من الهيكل وحده."),
    gap("aed-v1.0:112170", "حدي", "OPEN-CANDIDATE", "spread out/encircle لا يطابق حدي أو حضي ولا حواس الحد والحوض، ولا يحول الإحاطة إلى بسط بلا شاهد."),
    gap("aed-v1.0:113220", "خاي", "SOURCE-GAP", "AED يتردد بين مقياس مساحة ومقياس سعة وكلاهما بين الأقواس؛ لا وحدة واحدة مسماة يقوم عليها مدار عربي."),
    gap("aed-v1.0:113330", "خاو", "OPEN-CANDIDATE", "ingredients من نبات وزهور وبخور لا تطابق خاو أو خلو أو خرو، ولا يختزل الخليط في مادة عربية واحدة."),
    gap("aed-v1.0:113450", "خاي", "SOURCE-GAP", "جزء السفينة غير مسمى؛ لا ينتخب اسم عضو بحري عربي من خاي أو خلي أو خري."),
    gap("aed-v1.0:113650", "خاو", "OPEN-CANDIDATE", "meat pieces as an offering لا تطابق خاو أو خلو أو خرو، ولا يكفي سياق القربان لإثبات اسم اللحم."),
    gap("aed-v1.0:113800", "خات", "OPEN-CANDIDATE", "become ecstatic/rage لا يطابق خات أو خاط أو خلت أو خلط بدلالة معجمية مباشرة، ولا يسوى الوجد باختلاط مفترض."),
    gap("aed-v1.0:114100", "خار", "SOURCE-GAP", "نوع الإوزة نفسه بين الأقواس وغير محسوم؛ لا ينتخب اسم طائر عربي من خار أو خال."),
    gap("aed-v1.0:114380", "خاد", "OPEN-CANDIDATE", "pluck fowl لا يطابق خاد أو خاض أو خلد أو خرد، ولا يدخل نتف من خارج الرسم."),
    gap("aed-v1.0:114670", "خعت", "OPEN-CANDIDATE", "primeval hill لا يجد في خعت أو خضت أو خغت اسما للتل الأول عاملا، ولا يدخل ربوة من خارج الرسم."),
    gap("aed-v1.0:114850", "خعو", "OPEN-CANDIDATE", "crowns لا تطابق خعو أو خضو أو خغو، ولا يورث الظهور معنى التاج."),
    gap("aed-v1.0:115110", "خوي", "OPEN-CANDIDATE", "protect/prevent لا يطابق خوي أو خوء، ولا يدخل حمى أو وقى بصامتين مغايرين."),
    gap("aed-v1.0:115340", "خوض", "SOURCE-GAP", "فعل الصيد بالشبكة نفسه موسوم بالشك؛ وخاض الماء لا يثبت صيد السمك أو أداة الشبكة."),
    gap("aed-v1.0:115560", "خبي", "OPEN-CANDIDATE", "dance لا يطابق خبي أو خبء، ولا يدخل رقص من خارج الرسم."),
    gap("aed-v1.0:115630", "خبو", "SOURCE-GAP", "النبات الطبي غير مسمى؛ لا ينتخب اسم نبات عربي من خبو أو خب أو خيب."),
    gap("aed-v1.0:115860", "خبس", "SOURCE-GAP", "نوع الطائر غير محسوم وcormorant اقتراح بين الأقواس؛ لا ينتخب اسم طائر عربي من خبس أو خبش."),
    gap("aed-v1.0:116440", "خبش", "OPEN-CANDIDATE", "كوكبة الدب الأكبر لا تطابق خبش أو خفس، ولا يثبت اسم الحيوان اسما عربيا للكوكبة من الهيكل."),
    gap("aed-v1.0:116550", "فخذ", "LAW-GAP", "الفخذ عضو مجاور للردف لا هو إياه، وḫ-p-d بإزاء ف-خ-ذ يحتاج قلبا وتقابلين مصريين غير موقعين.", sound="المقابلة المرفوعة ḫ-p-d↔ف-خ-ذ تحتاج قلب الأولين وḫ↔خ وd↔ذ؛ لا يجتمع ذلك في مسار مصري موقع.", orbit="الفخذ وصل ما بين الساق والورك؛ يجاور buttock/rear part ولا يساويه، فبقيت الدلالة والصوت مانعين.", keywords="الفخذ|الساق|الورك|أفخاذ"),
    gap("aed-v1.0:116640", "خفع", "OPEN-CANDIDATE", "fist/grasp لا يطابق خفع أو خفض أو خفغ، ولا يحول القبض إلى مادة من الهيكل بلا شاهد."),
    terminal("aed-v1.0:116761", "∅", "OUT-OF-SCOPE", "حرف جر وظيفي بلا معنى معجمي معين في AED؛ لا مادة جذرية مستقلة قابلة لحكم النسب."),
    gap("aed-v1.0:117020", "خمي", "OPEN-CANDIDATE", "overthrow/demolish/oppose لا يطابق خمي أو خمء، ولا يدخل هدم أو قلب من خارج الرسم."),
    gap("aed-v1.0:117170", "خمو", "OPEN-CANDIDATE", "تسمية أعداء مصر بالذين لا يعرفون لا تطابق خمو أو خم، ولا تورث الجهل معنى العداوة لجذر عربي."),
    gap("aed-v1.0:117300", "خمت", "OPEN-CANDIDATE", "spear/harpoon لا يجد في خمت أو خمط اسما للرمح أو الحربة عاملا."),
    gap("aed-v1.0:117420", "خمت", "SOURCE-GAP", "نوع المعالجة الطبية غير مسمى؛ لا مدار قبل تعيين الفعل أو المادة العلاجية."),
    gap("aed-v1.0:117810", "خنو", "SOURCE-GAP", "الإنجليزية تسمي كائنا إلهيا والألمانية تقترح castanets؛ اختلاف المرجعين يمنع مدار عضو واحد."),
    gap("aed-v1.0:117960", "خنف", "SOURCE-GAP", "AED لا يثبت إلا فعلا في طقس قرباني، بينما الألمانية تتردد بين الإبعاد والأخذ؛ لا حدث واحدا محسوما."),
    gap("aed-v1.0:118080", "خنم", "OPEN-CANDIDATE", "rear/care for divine children لا يطابق خنم في المروحة، ولا يدخل حضن أو رعى من خارج الرسم."),
    gap("aed-v1.0:118320", "خنر", "OPEN-CANDIDATE", "restrain/imprison لا يطابق خنر أو خنل في العربية، ولا يكفي المنع لإثبات حبس من خارج الرسم."),
    gap("aed-v1.0:118380", "خنر", "DIRECTION-GAP", "وسم Sem. loan word في fangs لا يسمي لغة مانحة أو طريق انتقال، ولا يطابق خنر أو خنل اسما للناب."),
    gap("aed-v1.0:118740", "خنش", "SOURCE-GAP", "النبات الطبي غير مسمى؛ لا ينتخب اسم نبات عربي من خنش أو خنس."),
    gap("aed-v1.0:119850", "خري", "OPEN-CANDIDATE", "الديمونيم Syrian لا يطابق خري أو خلي مادة عربية مسماة، ولا يستخرج من اسم النسبة جذر بحدس."),
    gap("aed-v1.0:119960", "خرو", "OPEN-CANDIDATE", "enemy لا يطابق خرو أو خلو وحواس خر أو خل، ولا يدخل عدو من خارج الرسم."),
    gap("aed-v1.0:120380", "خرر", "OPEN-CANDIDATE", "bundle لا يطابق خرر أو خلل ولا يثبت السقوط أو الانهدام معنى الحزمة."),
    gap("aed-v1.0:120460", "خرش", "OPEN-CANDIDATE", "bundle of herbs/vegetables لا يطابق خرش أو خرس أو خلش أو خلس، ولا يختزل المجموع في نوع النبات."),
    gap("aed-v1.0:121160", "خشب", "OPEN-CANDIDATE", "mutilate لا يطابق الخشب أو الخسب، ولا يكفي إتلاف العضو لإثبات مادة القطع أو التشويه."),
    gap("aed-v1.0:121590", "ختو", "SOURCE-GAP", "attendants نفسها موسومة بالشك؛ لا وظيفة أو رتبة محققة تنتخب من ختو أو خطو."),
    gap("aed-v1.0:121750", "ختم", "DIRECTION-GAP", "ḫtm والختم متطابقان في الرسم ومدار seal، لكن احتمال القرض الإداري الثقافي بلا اتجاه محكوم يمنع حكم الإرث أو الانتقال.", sound="الهيكل الكامل ḫ-t-m↔خ-ت-م محفوظ بلا إسقاط؛ العائق ليس التشابه الصوتي بل اتجاه النقل التاريخي.", orbit="ختم الشيء أي طبعه وغطاه واستوثق منه؛ وهو مدار seal مباشرة، وبقي اتجاه النقل مانعا.", keywords="ختمه|طبعه|الخاتم|الختم|التغطية"),
    gap("aed-v1.0:121870", "ختر", "SOURCE-GAP", "AED لا يثبت إلا verb بلا معنى معجمي؛ لا يمكن كتابة مدار أو انتخاب مقابل."),
    gap("aed-v1.0:122220", "خات", "OPEN-CANDIDATE", "corpse لا يطابق خات أو خاط أو خرت ولا حات أو حرت، ولا يدخل جثة من خارج الرسم."),
    gap("aed-v1.0:122460", "خاب", "OPEN-CANDIDATE", "clavicle لا يطابق خاب أو خلب أو خرب ولا حاب وحلب وحرب، ولا يدخل ترقوة من خارج الرسم."),
    gap("aed-v1.0:122770", "خعو", "SOURCE-GAP", "نوع الجرة غير محسوم وكونها للخمر اقتراح؛ لا ينتخب اسم إناء عربي من خعو أو حعو."),
    gap("aed-v1.0:122860", "خبت", "OPEN-CANDIDATE", "flock of animals لا يطابق خبت أو خفت ولا حبت أو حفت، ولا يدخل قطيع من خارج الرسم."),
    gap("aed-v1.0:123020", "خمس", "OPEN-CANDIDATE", "incense لا يطابق خمس أو خمش أو حمص، ولا يدخل بخور بصامتين مغايرين."),
    gap("aed-v1.0:123410", "خنم", "SOURCE-GAP", "الإناء الحجري أو المعدني غير مسمى النوع والوظيفة؛ لا مدار لمادة خنم أو حنم."),
    gap("aed-v1.0:123740", "خنن", "SOURCE-GAP", "الإنجليزية لا تعين إلا noun طبيا والألمانية تجمع الغبار والركام؛ لا مرجع واحدا محسوما."),
    gap("aed-v1.0:123850", "خنك", "SOURCE-GAP", "قطعة اللباس غير مسماة؛ لا ينتخب اسم ثوب عربي من خنك أو حنك."),
    gap("aed-v1.0:123950", "خرت", "OPEN-CANDIDATE", "hereafter لا يطابق خرت أو خلط ولا حرت وحلت، ولا يدخل آخرة من خارج الرسم."),
    gap("aed-v1.0:124660", "خسو", "OPEN-CANDIDATE", "lower eyelid لا يطابق خسو أو خشو أو حشو، ولا يكفي جوار العين لإثبات جفن من خارج الرسم."),
    gap("aed-v1.0:124930", "ختي", "OPEN-CANDIDATE", "pluck plants/strip hide لا يطابق ختي أو خطي ولا حتي أو حطي، ولا يخلط نتف النبات بسلخ الجلد في مقابل مفترض."),
    gap("aed-v1.0:126290", "سرو", "OPEN-CANDIDATE", "guard/heed/guard against لا يطابق زاو أو زرو ولا ساو أو سرو، ولا يدخل حرس أو وقى بصامت مغاير."),
    gap("aed-v1.0:126610", "سرب", "LAW-GAP", "سرب في الأرض بمعنى ذهب يطابق traverse/roam، لكن z-ꜣ-b لا يسوي س-r-b بمسار مصري كامل موقع.", sound="b↔ب في IDN-05؛ z↔س وꜣ↔ر هما الرجلان المصريتان غير الموقعين في هذا العضو.", orbit="سرب في الأرض أي ذهب وخرج في طريقه؛ وهو مدار traverse/roam مباشرة، وبقي الصوت مانعا.", keywords="سرب في الأرض|ذهب|خرج|الطريق"),
    gap("aed-v1.0:126850", "سار", "OPEN-CANDIDATE", "catfish لا يجد في سار أو سال ولا شار أو صار اسما للسمك عاملا، ولا ينتخب النوع من حركة السباحة."),
    gap("aed-v1.0:126980", "ساح", "OPEN-CANDIDATE", "reach/arrive لا يساوي ساح في الأرض بمعنى ذهب وامتد، ولا يثبت الوصول إلى غاية من السير وحده."),
    gap("aed-v1.0:127060", "ساح", "OPEN-CANDIDATE", "awl/borer لا يطابق ساح أو سلح أو سرح ولا شاح وصاح، ولا يدخل مثقاب من خارج الرسم."),
    gap("aed-v1.0:127520", "ساق", "OPEN-CANDIDATE", "let sprout لا يطابق ساق أو سلق أو سرج، ولا يسوي إخراج النبات بسوقه أو ساقه الاسمية."),
    gap("aed-v1.0:127630", "زات", "OPEN-CANDIDATE", "libation stone لا يطابق زات أو زلط أو سلط، ولا يثبت سكب الشراب اسما للحجر."),
    gap("aed-v1.0:127850", "سير", "OPEN-CANDIDATE", "perception/knowledge لا يطابق سير أو سيل ولا شير أو صير، ولا يدخل شعور أو علم من خارج المسار الموقع."),
    gap("aed-v1.0:128670", "سعا", "OPEN-CANDIDATE", "great لا يطابق سعا أو سعر ولا شعا أو شعر ولا صغر بضده، ولا ينتخب العظم من الهيكل وحده."),
    gap("aed-v1.0:128760", "شعب", "LAW-GAP", "شعب الشيء في معنى فرقه يلتقي saw off/castrate في الفصل، لكن s المصرية بإزاء ش العربية بلا صف مصري فردي موقع لهذا العضو.", sound="ꜥ↔ع في IDN-15 وb↔ب في IDN-05؛ s↔ش هي الرجل المصرية غير الموقعة.", orbit="شعب الشيء أي فرقه وشتته؛ وهو مدار القطع والفصل الجامع لنشْر الخشب والخصاء، وبقي الصوت مانعا.", keywords="شعبه|التفريق|فرقه|شتته"),
    gap("aed-v1.0:128840", "سعم", "OPEN-CANDIDATE", "swallow/wash down medicine لا يطابق سعم أو شعم أو صعم، ولا يدخل بلع من خارج الرسم."),
    gap("aed-v1.0:130090", "زون", "OPEN-CANDIDATE", "arrow لا يطابق زون أو سون ولا يجد فيهما اسما للسهم عاملا."),
    gap("aed-v1.0:130450", "سور", "DIRECTION-GAP", "وسم Sem. loan word لا يسمي مانحا أو طريق انتقال، وchariot equipment نفسه غير معين فلا يطابق سور أو شور أو صور."),
    gap("aed-v1.0:131210", "سبر", "OPEN-CANDIDATE", "teach/tend لا يطابق سبر أو صبر ولا شبر، ولا يدخل علم أو ربى من خارج الرسم."),
    gap("aed-v1.0:131780", "سبن", "OPEN-CANDIDATE", "crown لا يطابق سبن أو شبن أو صبن، ولا يدخل توج من خارج الرسم."),
    gap("aed-v1.0:131900", "سبح", "SOURCE-GAP", "الجذر s-b-ḥ مطابق بنيويا، لكن المعاجم العربية تثبت التسبيح للتنزيه والذكر لا الصياح العام؛ رفع الصوت جسر غير معجمي.", sound="s↔س وb↔ب وḥ↔ح ظاهرة في الهيكل، لكن التطابق الصامتي لا يعوض غياب المدار المعجمي.", orbit="التسبيح تنزيه وذكر مخصوص؛ لا يساوي cry out العام بلا شاهد عربي صريح.", keywords="سبحان|التسبيح|التنزيه|الذكر"),
    gap("aed-v1.0:131940", "سبخ", "OPEN-CANDIDATE", "enclose/enfold with the arms لا يطابق سبخ أو شبخ أو صبخ، ولا يدخل عانق من خارج الرسم."),
    gap("aed-v1.0:132210", "سبق", "OPEN-CANDIDATE", "Mercury the planet لا يطابق سبق أو سبغ ولا شبق أو صبغ، ولا يستخرج اسم الكوكب من الهيكل."),
    gap("aed-v1.0:132480", "زبو", "SOURCE-GAP", "الإنجليزية تسمي piece في سياق طبي والألمانية حالة مرض؛ اختلاف المرجعين يمنع مدار مادة واحدا."),
    gap("aed-v1.0:132630", "زبا", "OPEN-CANDIDATE", "centipede لا يجد في زبا أو زبر ولا سبا أو سفر اسما لأم أربعة وأربعين عاملا."),
    gap("aed-v1.0:132850", "سبر", "SOURCE-GAP", "نوع الخضار غير مسمى وموسوم بالشك؛ لا ينتخب سبر أو سفر أو صبر اسما لنبات بعينه."),
    gap("aed-v1.0:133110", "سبس", "OPEN-CANDIDATE", "build لا يطابق سبس أو سفس ولا شبش أو صفص، ولا يدخل بنى من خارج الرسم."),
    gap("aed-v1.0:133240", "صفد", "OPEN-CANDIDATE", "grain ration لا يطابق سبد أو صفد ولا سفض، ولا يحول القيد أو الصفد إلى مؤونة حبوب."),
    gap("aed-v1.0:133540", "سفا", "SOURCE-GAP", "hatred نفسها موسومة بالشك؛ لا يصدر مدار من سفا أو شفا أو صفا قبل حسم معنى العضو."),
    gap("aed-v1.0:133630", "سفن", "OPEN-CANDIDATE", "mercifulness/gentleness لا يطابق سفن أو زبن، ولا يحول تسوية الخشب أو ركوب السفينة إلى رفق ورحمة."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT
assert {item.state for item in DECISIONS} <= LEGAL_CLOSURES
assert {item.verdict for item in DECISIONS} <= LEGAL_CLOSURES

OUTSIDE_FAN = {"aed-v1.0:116550"}

WITNESS_NOTES = {
    "aed-v1.0:116550": "قال لسان العرب: «الفخذ وصل ما بين الساق والورك»؛ وأثبت تاج العروس الحد نفسه. الردف والفخذ متجاوران لا عضو واحد، وبقي القلب والصوت مانعين.",
    "aed-v1.0:121750": "قال لسان العرب: «ختمه: طبعه» وفسر الختم بالتغطية والاستيثاق؛ وأثبت تاج العروس الختم والطبع. بقي اتجاه القرض الإداري الثقافي غير محكوم.",
    "aed-v1.0:126610": "قال لسان العرب: «سرب في الأرض: ذهب» و«سرب: خرج»؛ وأثبت تاج العروس السرب والطريق والذهاب. بقي z-ꜣ↔س-r بلا مسار مصري موقع.",
    "aed-v1.0:128760": "قال لسان العرب: «شعب الرجل أمره إذا شتته وفرقه»؛ وأثبت تاج العروس الشعب في التفريق. بقي s↔ش بلا صف مصري فردي موقع.",
    "aed-v1.0:131900": "قرأ لسان العرب وتاج العروس كاملين؛ كلاهما يثبت التسبيح في التنزيه والذكر ولا يثبت cry out العام لهذا الجذر.",
}


def select_egyptian_fast(text: str, exact: dict[str, dict]) -> list[dict]:
    """Equivalent to R9.select_egyptian without repeated whole-text counts."""
    newline_positions = [match.start() for match in re.finditer("\n", text)]
    first_snapshot: dict[str, dict] = {}
    latest: dict[str, dict] = {}
    completed_ids: set[str] = set()
    for block_match in re.finditer(r"(?ms)^### .*?(?=^### |\Z)", text):
        position = block_match.start()
        block = block_match.group()
        ids = list(dict.fromkeys(re.findall(r"aed-v1\.0:\d+", block)))
        if not ids:
            continue
        if block.startswith("### WO-C-OPEN-COMP-"):
            completed = re.search(r"`(aed-v1\.0:\d+)`", block)
            if completed:
                completed_ids.add(completed.group(1))
        states = re.findall(r"^- حالةُ? الإغلاق:\s*([^\n]+)", block, re.M)
        verdicts = re.findall(
            r"^- الحكم \(استكشاف\):\s*([^\n]+)", block, re.M,
        )
        status_text = " ".join(states[-1:] + verdicts[-1:])
        heading = block.splitlines()[0]
        for member_id in ids:
            latest[member_id] = {
                "latest_position": position,
                "latest_status": status_text,
                "latest_heading": heading,
            }
            if f"EGYPTIAN-LEXICAL-SNAPSHOT-v1:{member_id}" in block:
                first_snapshot.setdefault(member_id, {
                    "snapshot_position": position,
                    "snapshot_line": (
                        bisect.bisect_left(newline_positions, position) + 1
                    ),
                    "snapshot_heading": heading,
                    "snapshot_inventory_id": (
                        f"EGYPTIAN-LEXICAL-SNAPSHOT-v1:{member_id}"
                    ),
                })
    selected = []
    open_tokens = tuple(R9.OPEN_STATES) + ("غير صادر", "غيرُ صادر")
    for member_id, snapshot in first_snapshot.items():
        if member_id in completed_ids:
            continue
        current = latest.get(member_id) or {}
        if not any(
            token in str(current.get("latest_status") or "")
            for token in open_tokens
        ):
            continue
        entry = exact.get(member_id)
        if not entry or "ḏ" in str(entry["headword"]):
            continue
        tokens = R9.FAN.skeleton(str(entry["headword"]), "egyptian")
        fan = R9.FAN.fan(str(entry["headword"]), "egyptian")
        if 2 <= len(tokens) <= 4 and fan:
            selected.append({
                **entry,
                **snapshot,
                **current,
                "skeleton_tokens": tokens,
                "fan": fan,
            })
    selected.sort(key=lambda item: (
        len(item["skeleton_tokens"]), int(item["snapshot_position"]),
    ))
    return selected


def round29_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R28.round28_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND28-COMPLETION", "ROUND29-COMPLETION")
    card = card.replace(
        f"round28-egyptian-rank={rank}/{CARD_COUNT}",
        f"round29-egyptian-rank={rank}/{CARD_COUNT}",
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
        replacement = (
            f"- مسح المعاني العربية: قرئت {count} نتيجة للجذر `{root}` "
            f"بما يكافئ `--max-chars 0`؛ {note}"
        )
        card = re.sub(r"(?m)^- مسح المعاني العربية:.*$", replacement, card)
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
        raise SystemExit("Round-twenty-nine marker already exists; append refused.")

    aramaic_exact, _ = R9.load_entries("aramaic")
    aramaic_queue = R9.select_aramaic(aramaic_text, aramaic_exact)
    assert not aramaic_queue, (
        "Aramaic short live-open queue is no longer exhausted: "
        f"{[item['entry_id'] for item in aramaic_queue[:10]]}"
    )

    egyptian_exact, _ = R9.load_entries("egyptian")
    queue = select_egyptian_fast(egyptian_text, egyptian_exact)
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
        round29_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة التاسعة والعشرون: استمرار المخزون المصري المسجل المفتوح (2026-08-26)", "",
        (
            "أعيد فحص الآرامية أولا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرا، فسجل الانتقال المسمى `{TRANSITION}`. انتقيت ثمانين "
            "بطاقة مصرية بدءا من `WO-C-OPEN-COMP-01583` بقصر الهيكل ثم موضع "
            "اللقطة. استبعد صف ḏ المؤجل. في كل بطاقة عرضت إصابات AED كلها بلا "
            "حد، وكتب وسم الطريق والرسم والمدخل المختار، وحفظ الاختلاف "
            "والمتجانسات بلا محو. فحصت حالة الإغلاق والحكم آليا على القائمة "
            "القانونية وحدها في `data/closure-vocabulary.json`."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-01583 إلى WO-C-OPEN-COMP-01622", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-01623 إلى WO-C-OPEN-COMP-01662", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([
                f"<!-- LANE-C-R29-EGYPTIAN-CHUNK-{rank:03d}:END -->", "",
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
        "## الجولة التاسعة والعشرون: المسار C، الساميات والمصرية (2026-08-26)", "",
        f"- الوقت: {now}.",
        "- أعيد فحص الساميات أولا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01583` إلى `WO-C-OPEN-COMP-01622`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01623` إلى `WO-C-OPEN-COMP-01662`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طبق الانضباط الثلاثي: لم يصدر موجب في هذه النافذة؛ وكل بطاقة لها عائق شريف مسمى.",
        "- قاموس الإغلاق المغلق وحده مطبق: كل حالات الإغلاق والأحكام اجتازت القائمة القانونية في `data/closure-vocabulary.json`.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ لا حكم موجب جديد.",
        "- المطابقات الدلالية المرفوعة بقيت فجوات قانون: `ḫpd↔فخذ` لاختلاف العضو والقلب الصوتي، و`zꜣb↔سرب` و`sꜥb↔شعب` لرجل صوتية مصرية غير موقعة.",
        "- `ḫtm↔ختم` بقي `DIRECTION-GAP` مع تطابق الجذر ومدار الختم؛ ووسما القرض السامي في `ḫnr` و`swr` بقيا بلا مانح مسمى أو طريق فردي.",
        "- الألفاظ والمراجع المشكوكة أو غير المسماة بقيت `SOURCE-GAP`، ولم يرث متجانس معنى جاره.",
        "- حرف الجر `ḫft` أغلق `OUT-OF-SCOPE`، وصف ḏ المصري المؤجل بقي مستبعدا.",
        "- لم يحدث شحن أو إيداع أو إعداد مرحلي، ولم يستعمل git أو تحدث مشتقات النشر.", "",
        f"LANE-C DONE29 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
        R28.R27.R26.R25.R24.R23.R20.R10.append(
            EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian,
        )
        R28.R27.R26.R25.R24.R23.R20.R10.append(
            REPORT, f"{MARKER}:REPORT", report,
        )
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
