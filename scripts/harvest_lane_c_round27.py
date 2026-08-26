#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 27 completion cards without shipping or git.

The live short Aramaic queue is checked before the registered Egyptian open
queue continues.  The script completes WO-C-OPEN-COMP-01423..01502 in two
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

import harvest_lane_c_round26 as R26


R9 = R26.R9
AR = R26.AR
ROOT = R26.ROOT
ARAMAIC = R26.ARAMAIC
EGYPTIAN = R26.EGYPTIAN
REPORT = R26.REPORT

MARKER = "LANE-C-ROUND27-2026-08-26"
FIRST_SERIAL = 1423
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)
LEGAL_CLOSURES = R26.LEGAL_CLOSURES


def gap(member_id: str, candidate: str, state: str, reason: str,
        sound: str = "المروحة بنيوية فقط؛ لا يرقى التشابه إلى قانون أو نسب.",
        orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
        keywords: str = "", zero: str = "") -> R9.Decision:
    return R26.open_gap(
        member_id, candidate, state, reason, sound, orbit, keywords, zero,
    )


def pos(member_id: str, candidate: str, verdict: str, keywords: str,
        sound: str, orbit: str, reason: str,
        zero: str = "") -> R9.Decision:
    return R26.positive(
        member_id, candidate, verdict, keywords, sound, orbit, reason, zero,
    )


def terminal(member_id: str, candidate: str, verdict: str, reason: str,
             zero: str = "") -> R9.Decision:
    return R26.terminal(member_id, candidate, verdict, reason, zero)


# The sole positive has a complete Egyptian-to-Arabic sound route, a frozen
# event, two old Arabic witnesses, and a one-step semantic orbit.  Close
# semantic comparisons with an unsigned sound or morphological leg remain
# gaps.  General Semitic-loan labels without a named donor remain direction
# gaps, and uncertain or unnamed AED referents remain source gaps.
DECISIONS: tuple[R9.Decision, ...] = (
    gap("aed-v1.0:58800", "باو", "OPEN-CANDIDATE", "primal state لا يطابق حواس باو أو بلو أو برو ولا نوى المروحة، ولا يدخل بدء بصامت زائد من خارج الرسم."),
    gap("aed-v1.0:59020", "باي", "SOURCE-GAP", "تعريف magnificent fabric كله محاط بأقواس التحرير، ولا يعين نوع النسيج أو مادته."),
    gap("aed-v1.0:59200", "فقء", "LAW-GAP", "فقأ العين يطابق scratch out عضو العين، لكن ꜣ المصرية بإزاء ق وḫ بإزاء الهمزة بلا صفين مصريين موقعين، والشاهد العربي القديم المتاح واحد.", sound="p↔ف يمر بالصف الشفوي؛ أما ꜣ↔ق وḫ↔ء فموضعان مصريان غير موقعين.", orbit="فقأ عينه أي بخسها وشقها؛ وهو مدار scratch out the eyes مباشرة، وبقي الصوت والمصدر العربي الثاني ناقصين.", keywords="فقأت عينه|بخصتها|شققتها|العين"),
    gap("aed-v1.0:59310", "باق", "SOURCE-GAP", "thin biscuit نفسها موسومة بالشك ولا يسمي AED نوع الخبز أو مادته، فلا ينتخب رقاق أو فليقة بحدس."),
    gap("aed-v1.0:59800", "بور", "SOURCE-GAP", "AED لا يثبت إلا verb، وwachsen نفسها موسومة بالشك؛ لا يصدر مدار نمو من حس غير محسوم."),
    gap("aed-v1.0:59850", "ببو", "SOURCE-GAP", "AED لا يثبت إلا noun/Substantiv بلا معنى معجمي؛ لا يمكن كتابة مدار أو انتخاب مقابل."),
    gap("aed-v1.0:60310", "برر", "MORPHOLOGY-GAP", "fruit/seed يلتقي البُر بوصفه قمحا وحبا، لكن نزع .t المؤنثة لا يفسر تضعيف الراء العربية ولا يقصر المعنى المصري العام على القمح.", sound="p↔ب في LAB-01 وr↔ر في IDN-01؛ الراء العربية المضعفة بلا تحليل صرفي فردي.", orbit="البُر قمح وحب مزروع، وهو عضو داخل fruit/seed لا مساواة لكل الثمر والذرية بالقمح.", keywords="البُر|القمح|بُرَّة", zero="عزلت .t بوصفها وسم الاسم المؤنث المسجل؛ لم ينشأ من ذلك تضعيف عربي بحدس."),
    gap("aed-v1.0:60970", "فول", "DIRECTION-GAP", "beans يطابق الفول مباشرة، لكن وسم Sem. loan word لا يسمي مانحا ساميا فرديا أو طريق انتقال، ولا يوقع p-r-j بإزاء f-w-l.", sound="الدلالة مباشرة؛ أما p-r-j المصرية بإزاء ف-و-ل العربية فلا تجتمع في مسار مصري موقع.", orbit="الفول حب كالحِمص وهو الباقلاء؛ يطابق beans، لكن جهة القرض وصوته باقيان مفتوحين.", keywords="الفول|حب|الباقلاء"),
    pos("aed-v1.0:61070", "برع", "ROOT-ECHO", "فاق|الشجاعة|السؤدد|فضيلة", "p↔ب في LAB-01، وr↔ر في IDN-01، وꜥ↔ع في IDN-15؛ جذر كامل.", "برع الرجل إذا فاق في فضيلة أو شجاعة وسؤدد؛ وهو مدار prowess/might في التفوق والقوة مباشرة.", "ECHO مقصور على البراعة والقوة المتفوقة، لا مساواة كل تفوق بالبطولة القتالية."),
    gap("aed-v1.0:61180", "برو", "SOURCE-GAP", "AED لا يعين إلا a beverage بين الأقواس؛ لا نوع شراب أو مادة مسماة يقوم عليها مدار عربي."),
    gap("aed-v1.0:61260", "برش", "SOURCE-GAP", "AED يجمع fir cone المحتمل وred ochre/ochre-earth وjuniper berries المحتملة؛ لا مرجع واحدا يحكم العضو."),
    gap("aed-v1.0:61470", "بحو", "OPEN-CANDIDATE", "the far north لا يطابق الانقطاع في بحو ولا حواس فحو أو النوى الأقصر، ولا يدخل شمال من خارج الرسم."),
    gap("aed-v1.0:61750", "بخا", "OPEN-CANDIDATE", "equip لا يطابق الرخاوة أو الرطب الرديء في بخا ولا حواس فخا وبقية المروحة."),
    gap("aed-v1.0:62180", "بسي", "OPEN-CANDIDATE", "cook/bake/heat لا يجد في بسي أو بشي أو بصي فعلا للطبخ أو الخبز أو التسخين عاملا."),
    gap("aed-v1.0:62230", "بزح", "OPEN-CANDIDATE", "bite/sting لا يجد في بزح أو بسح أو فزح أو فسح اسما للعض أو اللسع عاملا."),
    gap("aed-v1.0:62280", "فشش", "OPEN-CANDIDATE", "divide/share لا يطابق فش الوعاء لإخراج ما فيه أو الحلب؛ فتح المحتوي لا يثبت القسمة أو المشاركة."),
    gap("aed-v1.0:62620", "بشن", "OPEN-CANDIDATE", "fissure/fracture لا يجد في بشن أو بسن أو فشن أو فسن اسما للشق أو الكسر عاملا."),
    gap("aed-v1.0:62720", "فقر", "SOURCE-GAP", "ingredient in kyphi غير مسمى، ولا يثبت AED أنه فقار أو مادة فقر أو بقر؛ لا مدار قبل تعيين المكون."),
    terminal("aed-v1.0:62910", "∅", "OUT-OF-SCOPE", "صيحة تنبيه وظيفية بمعنى behold؛ لا مادة جذرية معجمية مستقلة في العضو."),
    gap("aed-v1.0:63420", "فات", "SOURCE-GAP", "AED يثبت freight ثم يورد yield باحتمال؛ لا يحسم هل العضو حمولة سفينة أم عائدا أو نتاجا."),
    gap("aed-v1.0:63490", "فاي", "OPEN-CANDIDATE", "bearer لا يطابق حواس فاي أو فلي أو فري ولا النوى الأقصر، ولا يدخل حامل من خارج الرسم."),
    gap("aed-v1.0:63770", "فعج", "OPEN-CANDIDATE", "claw لا يجد في فعج أو فعق أو فعغ وبقية المروحة اسما للمخلب أو الظفر عاملا."),
    gap("aed-v1.0:63890", "فنث", "OPEN-CANDIDATE", "snake/worm/maggot لا يطابق حواس فنث أو فنت أو فنط، ولا يدخل حنش أو دودة من خارج الرسم."),
    gap("aed-v1.0:63980", "فكك", "LAW-GAP", "فك الشيء وفصل المشتبكين يطابق loosen، لكن ḫ المصرية المضعفة بإزاء ك العربية المضعفة بلا صف مصري موقع.", sound="f↔ف في IDN-06؛ ḫ-ḫ↔ك-ك هي الرجل المصرية غير الموقعة.", orbit="فك الشيء فصله وخلصه، وكل مشتبكين فصلتهما فقد فككتهما؛ وهو مدار loosen مباشرة.", keywords="فككت|فصلتهما|خلصته|انفك"),
    gap("aed-v1.0:64020", "فقا", "OPEN-CANDIDATE", "reward/gift لا يطابق فقا لمواضع السهم أو فقر وبقية المروحة، ولا يدخل عطاء من خارج الرسم."),
    terminal("aed-v1.0:65170", "∅", "OUT-OF-SCOPE", "حرف جر مركب وظيفي بمعنى in view of/in the sight of؛ لا جذر معجمي مستقل في العضو."),
    terminal("aed-v1.0:65480", "∅", "OUT-OF-SCOPE", "ظرف وظيفي بمعنى at once/together؛ لا مادة جذرية معجمية مستقلة في العضو."),
    gap("aed-v1.0:66460", "ماع", "OPEN-CANDIDATE", "just/correct/true لا يجد في ماع أو مرع أو مرض وبقية المروحة صفة صدق أو عدل عاملة."),
    gap("aed-v1.0:66560", "∅", "SOURCE-GAP", "Maa-canal اسم مجرى سماوي، وAED لا يثبت مادة الاسم أو صفة مائية مستقلة يمكن انتخاب مقابل لها."),
    gap("aed-v1.0:67060", "ماف", "SOURCE-GAP", "النبات غير مسمى وmyrrh نفسها اقتراح بين الأقواس؛ لا ينتخب اسم نبات عربي من الهيكل."),
    gap("aed-v1.0:67170", "مار", "OPEN-CANDIDATE", "wretched person لا يطابق الذحل والعداوة في مار ولا حواس مال أو مرر وبقية المروحة."),
    gap("aed-v1.0:67230", "ماح", "OPEN-CANDIDATE", "clap the hands لا يجد في ماح أو ملح أو مرح فعلا للتصفيق أو ضرب الكفين عاملا."),
    gap("aed-v1.0:67290", "موس", "LAW-GAP", "knife يلتقي الموسى آلة الحديد التي يحلق بها، لكن ꜣ المصرية بإزاء الواو وz بإزاء السين بلا صفين مصريين موقعين، وبنية موسى نفسها مختلف فيها عربيا.", sound="m↔م في IDN-02؛ ꜣ↔و وz↔س هما الموضعان المصريان غير الموقعين.", orbit="الموسى آلة حديد قاطعة للحلق، وهي عضو مباشر في جنس knife؛ بقي الصوت وتحليل الألف المقصورة مانعين.", keywords="الموسى|آلة الحديد|يحلق"),
    gap("aed-v1.0:67340", "ماس", "SOURCE-GAP", "AED لا يعين إلا red animal ويجعل deer احتمالا؛ لا يثبت نوع الحيوان المقارن."),
    gap("aed-v1.0:67580", "مات", "OPEN-CANDIDATE", "granite لا يجد في مات أو ماط أو ملت أو مرت وبقية المروحة اسما لحجر الجرانيت عاملا."),
    gap("aed-v1.0:67910", "ميت", "OPEN-CANDIDATE", "path/road لا يطابق حواس ميت أو ميط أو موت ولا النوى الثنائية، ولا يدخل طريق من خارج الرسم."),
    gap("aed-v1.0:68970", "معق", "OPEN-CANDIDATE", "roast on a skewer/kebab لا يطابق المعق للعمق والبعد أو الشرب الشديد، ولا يجد معنى شواء عاملا."),
    gap("aed-v1.0:69100", "موو", "SOURCE-GAP", "AED يتردد بين necropolis spirits وfuneral dancers ويسم التعيين بالشك؛ لا يحسم الكائن أو الدور."),
    gap("aed-v1.0:69540", "ممي", "OPEN-CANDIDATE", "giraffe لا يجد في ممي أو مم أو موم وبقية المروحة اسما للزرافة أو وصفا معجميا لها."),
    gap("aed-v1.0:69770", "منت", "OPEN-CANDIDATE", "malady/suffering لا يجد في منت أو منط أو من وبقية المروحة اسما للمرض أو الألم عاملا."),
    gap("aed-v1.0:70480", "منو", "OPEN-CANDIDATE", "mace لا يطابق حواس منو أو من أو مني وبقية المروحة، ولا يدخل دبوس أو هراوة من خارج الرسم."),
    gap("aed-v1.0:70940", "منح", "OPEN-CANDIDATE", "youth/stripling/young animal لا يطابق المنح والعطية، ولا يرث العضو معنى المنيحة أو ولدها."),
    gap("aed-v1.0:71060", "منخ", "OPEN-CANDIDATE", "chisel لا يجد في منخ مقابلا عربيا ولا يدخل منقاش أو إزميل بصوامت زائدة."),
    gap("aed-v1.0:71260", "منز", "SOURCE-GAP", "AED لا يعين إلا a plant بين الأقواس؛ لا نوع نبات يقوم عليه مدار عربي."),
    gap("aed-v1.0:71340", "منش", "OPEN-CANDIDATE", "cartouche-shaped box لا يطابق منش أو منس، ولا يكفي شكل الخرطوش لانتخاب صندوق عربي من خارج الرسم."),
    gap("aed-v1.0:71440", "منق", "SOURCE-GAP", "AED لا يعين إلا a tree بين الأقواس؛ لا نوع شجر يقوم عليه مدار عربي."),
    gap("aed-v1.0:72000", "مرت", "OPEN-CANDIDATE", "illness/evil لا يطابق المرت للأرض القفر ولا حواس مرط أو ملت وبقية المروحة."),
    gap("aed-v1.0:72520", "مري", "DIRECTION-GAP", "وسم Sem. loan word لا يسمي مانحا ساميا فرديا أو طريق انتقال، وgroom/squire لا يطابق حواس مري العربية."),
    gap("aed-v1.0:72630", "مرو", "SOURCE-GAP", "الإنجليزية لا تثبت إلا noun والألمانية تجمع dam وharbor؛ لا يحسم AED هل العضو حاجز أم مرفأ."),
    gap("aed-v1.0:72790", "مرخ", "LAW-GAP", "مرخ الجسد بالدهن يطابق anoint، لكن ḥ المصرية بإزاء خ العربية بلا صف مصري موقع.", sound="m↔م في IDN-02 وr↔ر في IDN-01؛ ḥ↔خ هي الرجل المصرية غير الموقعة.", orbit="مرخه بالدهن أي دهنه، وتمرّخ به أي ادهن؛ وهو مدار anoint مباشرة.", keywords="مرخه بالدهن|دهنه|ادهن|تمرخ"),
    gap("aed-v1.0:72960", "مرش", "OPEN-CANDIDATE", "bright red لا يطابق المرش للخدش أو سيلان الماء، ولا البرش للون المختلط من خارج صوت العضو."),
    gap("aed-v1.0:73470", "محو", "OPEN-CANDIDATE", "crown of Lower Egypt لا يطابق المحو لإزالة الأثر ولا حواس مح أو ماح وبقية المروحة."),
    gap("aed-v1.0:73550", "محت", "SOURCE-GAP", "part of a boat غير مسمى، ومادة acacia وكونه oar كلاهما محتملان؛ لا ينتخب عضو سفينة عربي."),
    gap("aed-v1.0:75590", "مسح", "MORPHOLOGY-GAP", "crocodile يطابق التمساح معجميا، لكن العضو العربي الرباعي يزيد تاء أولى ولا يقدم المصدر تحليلا فرديا يجيز إسقاطها وربط الباقي بمسح.", sound="m↔م وḥ↔ح هويتان؛ z↔س يحتاج صفه، والتاء العربية الأولية خارج سطح mzḥ.", orbit="التمساح اسم الحيوان نفسه؛ المطابقة الدلالية تامة، وبقي تحليل التاء وصوت z مانعين.", keywords="التمساح|التماسيح", zero="حفظ mzḥ كاملا؛ لم يسقط تاء تمساح العربية ولا يحولها إلى زيادة اشتقاقية بلا سند."),
    gap("aed-v1.0:75790", "مسس", "OPEN-CANDIDATE", "totter from fear لا يطابق مس الشيء أو مساسه، ولا يحول التماس إلى ارتجاف أو ترنح."),
    gap("aed-v1.0:76400", "مشو", "OPEN-CANDIDATE", "sword/dagger لا يجد في مشو أو مسو أو مش أو مس اسما للسيف أو الخنجر عاملا."),
    gap("aed-v1.0:76570", "مشت", "SOURCE-GAP", "AED لا يعين إلا a piece of jewellery بين الأقواس؛ لا نوع حلي أو مادته يقوم عليه مدار عربي."),
    gap("aed-v1.0:77420", "متي", "OPEN-CANDIDATE", "correct/precise لا يطابق حواس متي أو مطي أو مت أو مط، ولا يدخل حق أو دقة من خارج الرسم."),
    gap("aed-v1.0:77850", "∅", "SOURCE-GAP", "الإنجليزية لا تثبت إلا verb والألمانية تسمي followers of Seth دون بيان مادة اللفظ أو معناه المعجمي."),
    gap("aed-v1.0:79680", "ناو", "OPEN-CANDIDATE", "breath لا يطابق حواس ناو أو نرو أو نور وبقية المروحة، ولا يدخل نفس بصامت زائد."),
    gap("aed-v1.0:80010", "نيو", "OPEN-CANDIDATE", "ostrich لا يجد في نيو أو نءو أو ني وبقية المروحة اسما للنعامة عاملا."),
    gap("aed-v1.0:80640", "نعخ", "OPEN-CANDIDATE", "bundle as a unit of measure لا يطابق نعخ أو نضخ أو نغخ، ولا يدخل حزمة من خارج الرسم."),
    gap("aed-v1.0:80970", "نوت", "OPEN-CANDIDATE", "adze لا يطابق النوتي والملاح أو حواس نوط، ولا يدخل قدوم من خارج الرسم."),
    gap("aed-v1.0:81030", "نوت", "SOURCE-GAP", "kind of wood غير مسمى وwood نفسها موسومة بالشك؛ لا ينتخب اسم خشب عربي من الهيكل."),
    gap("aed-v1.0:81360", "نور", "SOURCE-GAP", "نوع الطائر غير مسمى وheron نفسها احتمال؛ لا ينتخب اسم طائر عربي من نور أو نول."),
    gap("aed-v1.0:81410", "نوح", "OPEN-CANDIDATE", "bind enemies لا يطابق النواح أو تقابل الرياح في نوح، ولا يكفي اجتماع الناس لإثبات القيد."),
    gap("aed-v1.0:81530", "نود", "SOURCE-GAP", "aromatic unguent كله محاط بأقواس التحرير ولا تسمي مادته؛ لا مدار قبل تعيين الدهن."),
    gap("aed-v1.0:81740", "نبت", "OPEN-CANDIDATE", "lady/mistress لا يطابق النبات في نبت ولا حواس نبط أو نب، ولا يدخل ربة من خارج الرسم."),
    gap("aed-v1.0:82480", "نبا", "SOURCE-GAP", "to tie وroll كلاهما موسوم بالشك، ولا يحسم AED فعل الربط أو اللف الذي يمكن مقارنته."),
    gap("aed-v1.0:82540", "نبي", "MORPHOLOGY-GAP", "goldsmith اسم مهنة مشتق في المصرية، لكن اللقطة لا تقدم تحليلا صرفيا موقعا لـ.y يربطه بمادة nbw ولا تقابلا عربيا للمهنة.", zero="حفظ .y المهني في nb.y؛ لم ينزع ولم يرث العضو معنى nbw المتجانس بلا تحليل مصدر."),
    gap("aed-v1.0:82730", "نبو", "OPEN-CANDIDATE", "sin/damage لا يطابق النبو والتجافي أو النبأ والبناء في مروحة نبو، ولا يدمج الذنب والضرر في مقابل مفترض."),
    gap("aed-v1.0:82810", "نبق", "LAW-GAP", "Christ's thorn tree وfruit يطابقان السدر وثمره النبق، لكن s المصرية بإزاء ق العربية بلا صف مصري موقع.", sound="n↔ن في IDN-03 وb↔ب في IDN-05؛ s↔ق هي الرجل المصرية غير الموقعة.", orbit="النبق حمل السدر وثمره، وهو نفس fruit of the Christ's thorn tree؛ بقي الصوت وحده ناقصا.", keywords="النبق|ثمر السدر|حمل السدر"),
    gap("aed-v1.0:82880", "نبد", "SOURCE-GAP", "AED لا يعين إلا an instrument بين الأقواس؛ لا أداة مسماة يمكن فصلها من نبد ونبض."),
    gap("aed-v1.0:83410", "نفع", "SOURCE-GAP", "AED لا يعين إلا a plant بين الأقواس؛ لا يجيز الهيكل توريث معنى المنفعة أو انتخاب نبات بعينه."),
    gap("aed-v1.0:83610", "نفر", "OPEN-CANDIDATE", "lotus لا يطابق النفور أو النفر والجماعة ولا النفل، ولا يدخل نيلوفر المركب من خارج الرسم."),
    gap("aed-v1.0:84140", "نمي", "OPEN-CANDIDATE", "shout لا يطابق النماء والزيادة في نمي ولا حواس نم أو نوم وبقية المروحة."),
    gap("aed-v1.0:84250", "نمع", "SOURCE-GAP", "AED لا يعين إلا architectural space/part of a building بين الأقواس؛ لا نوع حجرة أو موضع مسمى."),
    gap("aed-v1.0:84380", "نمس", "OPEN-CANDIDATE", "cloth/nemes-headcloth لا يطابق نمس لفساد الدهن أو السر والكتمان، ولا يرث العضو اسم النمس الحيوان."),
    gap("aed-v1.0:84700", "وني", "MORPHOLOGY-GAP", "weariness يطابق الونى في التعب والفتور، لكن nnw المصرية لا تسوي و-n-y العربية بلا تحليل موقع لنقل الضعيف وتبديل موضعه.", sound="n الثانية↔ن ظاهرة؛ ترتيب n-n-w المصرية بإزاء و-n-y العربية لا يمر بمسار صوتي أو صرفي موقع.", orbit="الونى التعب والفترة والضعف والكلال؛ وهو مدار weariness مباشرة، وبقيت بنية الضعيف مانعة.", keywords="الونى|التعب|الفترة|الضعف|الفتور", zero="حفظ nnw كما نشره AED؛ لم تقلب الواو الأولى أو تنقل الضعيف النهائي إلى موضع آخر."),
    gap("aed-v1.0:85110", "نري", "SOURCE-GAP", "نوع الخشب السوري غير مسمى وكل التعريف بين الأقواس؛ لا ينتخب اسم شجر أو خشب عربي من الهيكل."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT
assert {item.state for item in DECISIONS} <= LEGAL_CLOSURES
assert {item.verdict for item in DECISIONS} <= LEGAL_CLOSURES

OUTSIDE_FAN = {
    "aed-v1.0:59200", "aed-v1.0:63980", "aed-v1.0:67290",
    "aed-v1.0:72790", "aed-v1.0:82810", "aed-v1.0:84700",
}

WITNESS_NOTES = {
    "aed-v1.0:59200": "قال المصباح المنير: «فقأت عينه: بخستها، وفقأت البثرة: شققتها»؛ لم يظهر في الحوض شاهد عربي قديم ثان، فلم يصدر موجب.",
    "aed-v1.0:60310": "قال الصحاح: «البُر جمع بُرّة من القمح»؛ وقال المصباح المنير: «البُر القمح».",
    "aed-v1.0:60970": "قال لسان العرب: «الفول حب كالحِمص، وأهل الشام يسمون الفول الباقلاء»؛ وأثبت تاج العروس المعنى نفسه.",
    "aed-v1.0:61070": "قال لسان العرب: «البارع: الذي فاق أصحابه في السؤدد»؛ وقال المصباح المنير: «برع الرجل إذا فضل في علم أو شجاعة أو غير ذلك».",
    "aed-v1.0:63980": "قال لسان العرب: «فككت الشيء: خلصته، وكل مشتبكين فصلتهما فقد فككتهما»؛ وقال تاج العروس: «فكه: فصله فانفك».",
    "aed-v1.0:67290": "قال لسان العرب: «الموسى من آلة الحديد» التي يحلق بها؛ وأثبت تاج العروس أنها «آلة الحديد التي يحلق بها».",
    "aed-v1.0:72790": "قال لسان العرب: «مرخه بالدهن: دهنه، وتمرخ به: ادهن»؛ وقال الصحاح: «مرخت جسدي بالدهن مرخا».",
    "aed-v1.0:75590": "ذكر لسان العرب التمساح في مادة مسح، وأثبت أساس البلاغة «تمساحا من التماسيح»؛ بقي تحليل التاء غير موقع.",
    "aed-v1.0:82810": "قال لسان العرب: «النبق ثمر السدر»؛ وقال تاج العروس: «النبق حمل السدر».",
    "aed-v1.0:84700": "قال لسان العرب: «الونا التعب والفترة»؛ وقال تاج العروس: «الونى الضعف والفتور والكلال والإعياء».",
}


def round27_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R26.round26_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND26-COMPLETION", "ROUND27-COMPLETION")
    card = card.replace(
        "ROUND27-COMPLETION (2026-08-25)",
        "ROUND27-COMPLETION (2026-08-26)",
    )
    card = card.replace(
        f"round26-egyptian-rank={rank}/{CARD_COUNT}",
        f"round27-egyptian-rank={rank}/{CARD_COUNT}",
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
        raise SystemExit("Round-twenty-seven marker already exists; append refused.")

    aramaic_exact, _ = R9.load_entries("aramaic")
    aramaic_queue = R9.select_aramaic(aramaic_text, aramaic_exact)
    assert not aramaic_queue, (
        "Aramaic short live-open queue is no longer exhausted: "
        f"{[item['entry_id'] for item in aramaic_queue[:10]]}"
    )

    egyptian_exact, _ = R9.load_entries("egyptian")
    queue = R9.select_egyptian(egyptian_text, egyptian_exact)
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
        round27_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة السابعة والعشرون: استمرار المخزون المصري المسجل المفتوح (2026-08-26)", "",
        (
            "أعيد فحص الآرامية أولا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرا، فسجل الانتقال المسمى `{TRANSITION}`. انتقيت ثمانين "
            "بطاقة مصرية بدءا من `WO-C-OPEN-COMP-01423` بقصر الهيكل ثم موضع "
            "اللقطة. استبعد صف ḏ المؤجل. في كل بطاقة عرضت إصابات AED كلها بلا "
            "حد، وكتب وسم الطريق والرسم والمدخل المختار، وحفظ الاختلاف "
            "والمتجانسات بلا محو. فحصت حالة الإغلاق والحكم آليا على القائمة "
            "القانونية وحدها في `data/closure-vocabulary.json`."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-01423 إلى WO-C-OPEN-COMP-01462", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-01463 إلى WO-C-OPEN-COMP-01502", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([f"<!-- LANE-C-R27-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    states = dict(sorted(collections.Counter(item.state for item in DECISIONS).items()))
    verdicts = dict(sorted(collections.Counter(item.verdict for item in DECISIONS).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    now = datetime.now(ZoneInfo("Africa/Cairo")).strftime("%Y-%m-%d %H:%M:%S %z")
    now = now[:-2] + ":" + now[-2:]
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة السابعة والعشرون: المسار C، الساميات والمصرية (2026-08-26)", "",
        f"- الوقت: {now}.",
        "- أعيد فحص الساميات أولا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01423` إلى `WO-C-OPEN-COMP-01462`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01463` إلى `WO-C-OPEN-COMP-01502`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طبق الانضباط الثلاثي: كل موجب له صوت موقع وحدث مجمد ومدار مكتوب؛ وكل بطاقة أخرى لها عائق شريف مسمى.",
        "- قاموس الإغلاق المغلق وحده مطبق: كل حالات الإغلاق والأحكام اجتازت القائمة القانونية في `data/closure-vocabulary.json`.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ الموجب مقصور على عضو AED ومداره المكتوب.",
        "- الموجب: `pr-ꜥ↔برع` في البراعة والقوة المتفوقة، بمسار الجذر الكامل `LAB-01 + IDN-01 + IDN-15`، وحكمه `ROOT-ECHO`.",
        "- المطابقات الدلالية المرفوعة بقيت فجوات: `pꜣḫ↔فقأ` و`fḫḫ↔فكك` و`mꜣz↔موس` و`mrḥ↔مرخ` و`nbs↔نبق` في `LAW-GAP`؛ و`pr.t↔برر` و`mzḥ↔مسح` و`nnw↔وني` في `MORPHOLOGY-GAP`.",
        "- وسما القرض السامي العامان في `prj` و`mrj` بقيا `DIRECTION-GAP` بلا مانح مسمى أو طريق فردي.",
        "- صيحة التنبيه وحرف الجر والظرف أغلقت `OUT-OF-SCOPE`، وصف ḏ المصري المؤجل بقي مستبعدا.",
        "- لا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE27 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
    egyptian_appendix = unicodedata.normalize("NFC", "\n".join(body).rstrip() + "\n")
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
        R26.R25.R24.R23.R20.R10.append(EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian)
        R26.R25.R24.R23.R20.R10.append(REPORT, f"{MARKER}:REPORT", report)
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
