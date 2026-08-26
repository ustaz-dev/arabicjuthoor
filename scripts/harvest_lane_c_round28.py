#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 28 completion cards without shipping or git.

The live short Aramaic queue is checked before the registered Egyptian open
queue continues. The script completes WO-C-OPEN-COMP-01503..01582 in two
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

import harvest_lane_c_round27 as R27


R9 = R27.R9
AR = R27.AR
ROOT = R27.ROOT
ARAMAIC = R27.ARAMAIC
EGYPTIAN = R27.EGYPTIAN
REPORT = R27.REPORT

MARKER = "LANE-C-ROUND28-2026-08-26"
FIRST_SERIAL = 1503
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)
LEGAL_CLOSURES = R27.LEGAL_CLOSURES


def gap(member_id: str, candidate: str, state: str, reason: str,
        sound: str = "المروحة بنيوية فقط؛ لا يرقى التشابه إلى قانون أو نسب.",
        orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
        keywords: str = "", zero: str = "") -> R9.Decision:
    return R27.gap(
        member_id, candidate, state, reason, sound, orbit, keywords, zero,
    )


def pos(member_id: str, candidate: str, verdict: str, keywords: str,
        sound: str, orbit: str, reason: str,
        zero: str = "") -> R9.Decision:
    return R27.pos(
        member_id, candidate, verdict, keywords, sound, orbit, reason, zero,
    )


def terminal(member_id: str, candidate: str, verdict: str, reason: str,
             zero: str = "") -> R9.Decision:
    return R27.terminal(member_id, candidate, verdict, reason, zero)


# Only ḥbs has a complete signed sound route, a frozen event, two old Arabic
# witnesses, and a one-step semantic orbit. Close meanings with an unsigned
# Egyptian sound leg remain LAW-GAP. Unnamed or uncertain referents remain
# SOURCE-GAP, and general Semitic-loan labels remain DIRECTION-GAP.
DECISIONS: tuple[R9.Decision, ...] = (
    gap("aed-v1.0:85220", "نهت", "OPEN-CANDIDATE", "protection/refuge لا يطابق حواس نهت في المروحة ولا يجيز إدخال مأمن أو ملجأ من خارج الرسم."),
    gap("aed-v1.0:85290", "نهت", "OPEN-CANDIDATE", "sycamore/tree لا يجد في نهت أو نحت أو نهث اسما للشجرة عاملا، ولا ينتخب نوع نبات من الهيكل وحده."),
    gap("aed-v1.0:85470", "نهب", "OPEN-CANDIDATE", "rise early in the morning لا يطابق النهب أو النهوض بصامت زائد، ولا يحول البكور إلى معنى في نهب."),
    gap("aed-v1.0:85690", "نهر", "DIRECTION-GAP", "وسم Sem. loan word لا يسمي مانحا فرديا أو طريق انتقال، وتعريفا flee وsail لا يحسمان فعلا واحدا للمقارنة."),
    gap("aed-v1.0:86100", "نحع", "SOURCE-GAP", "AED لا يعين إلا something harmful بين الأقواس؛ لا مرجع أو فعل مسمى يقوم عليه مدار عربي."),
    gap("aed-v1.0:86610", "نحح", "OPEN-CANDIDATE", "hippopotamus لا يجد في نحح أو نحت أو نجح اسما للحيوان عاملا، ولا يدخل فرس النهر المركب من خارج الرسم."),
    gap("aed-v1.0:86920", "نخي", "OPEN-CANDIDATE", "lament/complain لا يطابق النخوة أو النخ في مروحة نخي، ولا يثبت النواح من الرسم وحده."),
    gap("aed-v1.0:87470", "نخخ", "OPEN-CANDIDATE", "become old/endure لا يجد في نخخ أو نكك معنى الشيخوخة أو البقاء عاملا."),
    gap("aed-v1.0:87930", "نسء", "SOURCE-GAP", "part of a ship غير مسمى؛ لا ينتخب نسء أو نشء اسما لعضو بحري مجهول."),
    gap("aed-v1.0:88000", "نسو", "SOURCE-GAP", "AED لا يثبت إلا verb بلا معنى معجمي؛ لا يمكن كتابة مدار أو انتخاب مقابل."),
    gap("aed-v1.0:88260", "نسر", "SOURCE-GAP", "تعريف treat a wound في سياق طبي لا يبين نوع المعالجة أو مادتها، فلا يورث نسر معنى الكشط أو القطع."),
    gap("aed-v1.0:88520", "نشو", "SOURCE-GAP", "AED لا يعين إلا vessel بين الأقواس؛ لا نوع إناء أو مادته يقوم عليه مدار عربي."),
    gap("aed-v1.0:88640", "نشب", "OPEN-CANDIDATE", "gate لا يطابق النشوب والعلق في نشب، ولا يكفي ثبات الباب لإثبات اسم البوابة."),
    gap("aed-v1.0:88900", "نشد", "OPEN-CANDIDATE", "rend لا يطابق الطلب والإنشاد في نشد، ولا يحول رفع الصوت إلى تمزيق."),
    gap("aed-v1.0:89120", "نقر", "OPEN-CANDIDATE", "sieve لا يطابق النقر للحفر والضرب، ولا يكفي وجود الثقوب لإثبات اسم المنخل أو فعل الغربلة."),
    gap("aed-v1.0:89330", "نكن", "OPEN-CANDIDATE", "wound لا يجد في نكن أو نجـن أو نقن اسما للجرح أو فعلا للإصابة عاملا."),
    gap("aed-v1.0:89490", "نقت", "OPEN-CANDIDATE", "breach in a dam لا يطابق حواس نقت أو نقط، ولا يكفي الخرق لإدخال نقب بصامت مغاير."),
    gap("aed-v1.0:89660", "نكب", "LAW-GAP", "نكب عن الطريق يطابق turn aside، لكن g المصرية بإزاء ك العربية بلا صف مصري موقع.", sound="n↔ن في IDN-03 وb↔ب في IDN-05؛ g↔ك هي الرجل المصرية غير الموقعة.", orbit="نكب عن الطريق أي عدل وتنحى؛ وهو مدار turn aside/divert مباشرة، وبقي الصوت مانعا.", keywords="نكب عن الطريق|عدل|تنحى"),
    gap("aed-v1.0:89720", "نقق", "LAW-GAP", "نق الضفدع والدجاجة وصوتهما يطابق cackle/screech، لكن g المصرية المضعفة بإزاء ق العربية المضعفة بلا صف مصري موقع.", sound="n↔ن في IDN-03؛ g-g↔ق-ق هي الرجل المصرية غير الموقعة.", orbit="نق الحيوان ونقنق إذا صوت؛ وهو مدار cackle/screech مباشرة، وبقي الصوت مانعا.", keywords="نق الضفدع|نقنق|صوت|الدجاجة"),
    gap("aed-v1.0:90100", "نتش", "OPEN-CANDIDATE", "besprinkle لا يطابق نتش الشيء بمعنى نزعه أو استخرجه، ولا يحول النثر إلى نزع."),
    gap("aed-v1.0:90680", "نثث", "OPEN-CANDIDATE", "rope/cord لا يجد في نثث أو نتت اسما للحبل عاملا، ولا يدخل وثاق بصامت زائد."),
    terminal("aed-v1.0:92210", "∅", "OUT-OF-SCOPE", "حرف جر وظيفي بمعنى on؛ لا مادة جذرية معجمية مستقلة في العضو."),
    terminal("aed-v1.0:92870", "∅", "COMPOUND-BOUNDARY", "الرسم rʾ-pr مركب اسمي من mouth وhouse بمعنى temple/chapel؛ لا يفك إلى جذر عربي واحد."),
    terminal("aed-v1.0:92920", "∅", "COMPOUND-BOUNDARY", "الرسم rʾ-nb تركيب وظيفي بمعنى everyone؛ لا يعامل بوصفه مادة جذرية واحدة."),
    gap("aed-v1.0:93190", "ريت", "OPEN-CANDIDATE", "ink لا يجد في ريت أو ريض أو ريث اسما للمداد عاملا، ولا يدخل حبر من خارج الرسم."),
    gap("aed-v1.0:93440", "روت", "OPEN-CANDIDATE", "outside لا يطابق حواس روت أو روض أو رود، ولا يثبت الخارج من الهيكل وحده."),
    gap("aed-v1.0:93730", "رود", "OPEN-CANDIDATE", "stairway/tomb shaft لا يطابق الرود والتمهل والطلب، ولا يحسم AED بين درج وبئر قبر."),
    gap("aed-v1.0:94010", "لبس", "DIRECTION-GAP", "leather cuirass يلتقي اللباس واللبوس والدروع، لكن وسم Sem. loan word لا يسمي المانح أو طريق الانتقال، وr↔ل وš↔س بلا مسار مصري كامل موقع.", sound="b↔ب في IDN-05؛ بقية r-b-š↔ل-b-s لا تجتمع في مسار مصري موقع.", orbit="اللبوس ما يلبس من ثياب أو دروع؛ وهو يضم cuirass مباشرة، وبقي الاتجاه والصوت مانعين.", keywords="اللباس|اللبوس|الدروع|يلبس"),
    gap("aed-v1.0:94290", "رمن", "SOURCE-GAP", "وحدة طول من خمس راحات لا يثبت AED اسمها المقارن أو طريق اشتقاقها؛ لا يساوى القياس بالرمان أو الرمين."),
    gap("aed-v1.0:95080", "رنن", "OPEN-CANDIDATE", "youth لا يطابق الرنين أو حواس رنن، ولا يدخل ريعان أو شاب من خارج الرسم."),
    gap("aed-v1.0:95300", "ررت", "OPEN-CANDIDATE", "sow لا يجد في ررت أو ردد أو ررض اسما لأنثى الخنزير عاملا."),
    gap("aed-v1.0:95600", "رحس", "SOURCE-GAP", "AED لا يثبت إلا verb بلا معنى معجمي؛ لا يمكن كتابة مدار أو انتخاب مقابل."),
    gap("aed-v1.0:95840", "رخر", "SOURCE-GAP", "الإنجليزية تسمي beverage والألمانية pastry؛ اختلاف المرجعين يمنع مدار مادة واحدا."),
    gap("aed-v1.0:96180", "رشو", "OPEN-CANDIDATE", "joy لا يطابق الرشوة أو الرشو في مروحة رشو، ولا يكفي نيل العطاء لإثبات الفرح."),
    gap("aed-v1.0:96520", "رجت", "DIRECTION-GAP", "وسم Sem. loan word لا يسمي مانحا أو طريق انتقال، وcompartment لا يطابق حواس رجت في العربية."),
    gap("aed-v1.0:96630", "ردو", "SOURCE-GAP", "نوع الطائر غير مسمى؛ لا ينتخب اسم طائر عربي من ردو أو ردي."),
    gap("aed-v1.0:97350", "هوي", "LAW-GAP", "هوى وأهوى وانهوى بمعنى سقط يطابق descend/fall، لكن ꜣ المصرية بإزاء الواو العربية بلا صف مصري موقع.", sound="h↔ه في IDN-13 والياء الختامية ظاهرة؛ ꜣ↔و هي الرجل المصرية غير الموقعة.", orbit="هوى الشيء إذا سقط من علو؛ وهو مدار descend/fall مباشرة، وبقي الصوت مانعا.", keywords="هوى|أهوى|انهوى|سقط"),
    gap("aed-v1.0:97500", "هاو", "OPEN-CANDIDATE", "corvée worker لا يطابق الهوى أو الهوي أو الهاء في المروحة، ولا يدخل عامل من خارج الرسم."),
    gap("aed-v1.0:98120", "هبي", "OPEN-CANDIDATE", "ibis لا يجد في هبي أو حبي اسما لطائر أبي منجل عاملا."),
    gap("aed-v1.0:98430", "همت", "SOURCE-GAP", "AED لا يعين إلا vessel measure بين الأقواس؛ لا نوع إناء أو مقدار مسمى يقوم عليه مدار."),
    gap("aed-v1.0:98720", "هنء", "LAW-GAP", "الهنيء وما يقال في التهنئة يلتقي rejoice في البشر والسرور، لكن i̯ المصرية بإزاء الهمزة العربية بلا صف مصري موقع.", sound="h↔ه في IDN-13 وn↔ن في IDN-03؛ i̯↔ء هي الرجل المصرية غير الموقعة.", orbit="هنأه بالأمر وقال ليهنئك، والهنيء السائغ بلا مشقة؛ مدار السرور قريب مباشر، وبقي الصوت مانعا.", keywords="هنأه|ليهنئك|الهنيء|بلا مشقة"),
    gap("aed-v1.0:98830", "هنن", "OPEN-CANDIDATE", "deer لا يجد في هنن أو حنن اسما للغزال أو الأيل عاملا."),
    gap("aed-v1.0:99500", "هثهث", "OPEN-CANDIDATE", "dig up لا يطابق الهثهثة أو الحث في المروحة، ولا يدخل حفر من خارج الرسم."),
    gap("aed-v1.0:99580", "هتت", "LAW-GAP", "هت البكر وهتت قوائم البعير في الصوت يطابق screaming/noise، لكن ṯ المصرية بإزاء ت العربية بلا صف مصري موقع.", sound="h↔ه في IDN-13 وt↔ت في IDN-09؛ ṯ↔ت هي الرجل المصرية غير الموقعة.", orbit="هت البكر إذا صوت، وهتت القوائم صوت وقعها؛ وهو مدار noise مباشرة، وبقي الصوت مانعا.", keywords="هت البكر|هتيتا|صوت|قوائم البعير"),
    gap("aed-v1.0:99700", "هدن", "SOURCE-GAP", "اسم النبات غير محسوم وhare's ear اقتراح بين الأقواس؛ لا ينتخب نبات عربي من الهيكل."),
    gap("aed-v1.0:100260", "حاءت", "OPEN-CANDIDATE", "worry لا يجد في حاءت أو حوت أو حيت معنى الهم أو القلق عاملا."),
    terminal("aed-v1.0:100320", "∅", "OUT-OF-SCOPE", "حرف جر وظيفي بمعنى before؛ لا مادة جذرية معجمية مستقلة في العضو."),
    gap("aed-v1.0:100650", "حاءي", "OPEN-CANDIDATE", "mourn/screech/dance at a funeral لا يطابق حواس حاءي أو حيي، ولا يخلط النواح والرقص في مقابل مفترض."),
    gap("aed-v1.0:100700", "حاي", "OPEN-CANDIDATE", "flood لا يطابق الحي والحيا في مروحة حاي من غير صلة مصدريّة موقعة، ولا يدخل فيضان من خارج الرسم."),
    gap("aed-v1.0:101060", "حاو", "OPEN-CANDIDATE", "increase/surplus لا يجد في حاو أو حوى معنى الزيادة أو الفضل عاملا بلا إسقاط للهمزة المصرية."),
    gap("aed-v1.0:101300", "حاءب", "OPEN-CANDIDATE", "hide/keep secret لا يطابق حاءب أو حاب، ولا يدخل خبأ بقلبين صوتيين غير موقعين."),
    gap("aed-v1.0:101420", "حام", "OPEN-CANDIDATE", "net yield/catch لا يطابق الحوم أو الحمى، ولا يكفي الحوز لإثبات صيد الشبكة."),
    gap("aed-v1.0:101780", "حاد", "OPEN-CANDIDATE", "trap fish لا يطابق الحد والحدة في حاد، ولا يدخل صاد بصامت أول مغاير."),
    gap("aed-v1.0:102420", "حوت", "OPEN-CANDIDATE", "pig لا يطابق الحوت، وفئة الحيوان العامة لا تجيز مساواة الخنزير بالسمك."),
    gap("aed-v1.0:102640", "حوا", "OPEN-CANDIDATE", "rot/putrefy لا يطابق الحوا أو الحوي في المروحة، ولا يدخل حمى أو عفن من خارج الرسم."),
    gap("aed-v1.0:103060", "حون", "OPEN-CANDIDATE", "childhood/youth لا يجد في حون أو حان أو حين اسما للصبا عاملا."),
    gap("aed-v1.0:103290", "حاب", "OPEN-CANDIDATE", "tent/kiosk لا يطابق الحب أو الحاب في المروحة، ولا يدخل خباء بصامت مغاير."),
    gap("aed-v1.0:103350", "حاب", "OPEN-CANDIDATE", "catch fish/fowl لا يطابق الحب أو الحاب، ولا يكفي جمع الصيد لإثبات أخذ أو حبس."),
    gap("aed-v1.0:103530", "حباء", "SOURCE-GAP", "AED لا يعين إلا divine bark بين الأقواس؛ لا جزء مسمى من المركب المقدس يقوم عليه مدار."),
    pos("aed-v1.0:103740", "حبس", "ROOT-ECHO", "المحبس|المقرمة|الستر|سترته", "ḥ↔ح في IDN-14، وb↔ب في IDN-05، وs↔س في IDN-07؛ جذر كامل.", "حبس الفراش بالمحبس أي ستره بالمقرمة؛ وهو مدار clothe/cover في التغطية بالستر والحوز مباشرة.", "ECHO مقصور على التغطية بالمحبس والستر؛ لا مساواة كل لباس بالفعل العام حبس."),
    gap("aed-v1.0:104100", "حبع", "SOURCE-GAP", "AED يتردد بين اسم طبي وstone ولا يعين المرجع؛ لا مدار قبل حسم المادة أو العلة."),
    gap("aed-v1.0:104220", "حبت", "OPEN-CANDIDATE", "embrace/armful لا يطابق حبت أو حبط، ولا يكفي ضم الذراعين لإثبات الحب دون رجل صوتية ودلالية كاملة."),
    gap("aed-v1.0:104340", "حفا", "OPEN-CANDIDATE", "snake/twist لا يطابق الحفا والحفاء، ولا يدخل حية من خارج الرسم أو يسوي الحيوان بحركته."),
    gap("aed-v1.0:104760", "حمت", "SOURCE-GAP", "نوع السمك غير مسمى؛ لا ينتخب اسم سمكة عربية من حمت أو حمد."),
    gap("aed-v1.0:104830", "حمت", "OPEN-CANDIDATE", "majesty of a queen or goddess لا يطابق الحماة أو الحمد أو حمت، ولا يدخل جلالة من خارج الرسم."),
    gap("aed-v1.0:105580", "حمن", "OPEN-CANDIDATE", "a number of لا يطابق حمن أو حمد، ولا يثبت مقدارا عدديا محددا يمكن مقارنته."),
    gap("aed-v1.0:105700", "حمس", "SOURCE-GAP", "vessel base نفسها موسومة بالشك؛ لا يحسم AED هل العضو قاعدة إناء أو شيء آخر."),
    gap("aed-v1.0:106020", "حنت", "OPEN-CANDIDATE", "pelican لا يجد في حنت أو حند اسما للبجع عاملا."),
    gap("aed-v1.0:106490", "جنب", "LAW-GAP", "جنب الشيء ونحاه يطابق drive away، لكن ḥ المصرية بإزاء ج العربية بلا صف مصري موقع.", sound="n↔ن في IDN-03 وb↔ب في IDN-05؛ ḥ↔ج هي الرجل المصرية غير الموقعة.", orbit="جنب عنه الشر أي نحاه وأبعده؛ وهو مدار drive away مباشرة، وبقي الصوت مانعا.", keywords="جنب|نحاه|أبعده|الشر"),
    gap("aed-v1.0:106800", "حنن", "OPEN-CANDIDATE", "hoe لا يطابق الحنين أو حنن، ولا يدخل معول أو فأس من خارج الرسم."),
    gap("aed-v1.0:107110", "حنك", "OPEN-CANDIDATE", "present a gift/offer لا يطابق الحنك أو الحنكة، ولا يكفي مد اليد لإثبات الإهداء."),
    gap("aed-v1.0:107640", "حرت", "OPEN-CANDIDATE", "tomb/necropolis لا يطابق الحرث أو الحرت، ولا يدخل حرم أو قبر من خارج الرسم."),
    gap("aed-v1.0:108360", "حري", "OPEN-CANDIDATE", "dread/instill dread لا يطابق الحري والجدارة، ولا يدخل حرع أو خوف من خارج الرسم."),
    gap("aed-v1.0:109010", "حرو", "OPEN-CANDIDATE", "terror/dread/respect لا يجد في حرو أو حري مدارا يجمع الخوف والتوقير بلا خلط."),
    gap("aed-v1.0:109400", "حست", "OPEN-CANDIDATE", "singer لا يطابق الحس أو الحاسة، ولا يكفي الصوت لإثبات اسم المغني."),
    gap("aed-v1.0:109520", "حزر", "OPEN-CANDIDATE", "fierce لا يطابق الحزر للتقدير أو الاختبار أو القوة، ولا يكفي الاشتداد لإثبات الشراسة."),
    gap("aed-v1.0:110340", "حكم", "LAW-GAP", "حكم بينهم وملك أمرهم يطابق rule/govern، لكن q-ꜣ المصرية بإزاء ك-م العربية لا يمران بصفين مصريين موقعين.", sound="ḥ↔ح في IDN-14؛ q↔ك وꜣ↔م هما الرجلان المصريتان غير الموقعتين.", orbit="حكم بينهم إذا قضى وولي الأمر؛ وهو مدار rule/govern مباشرة، وبقي الصوت مانعا.", keywords="حكم بينهم|القضاء|ولي الأمر|الحكم"),
    gap("aed-v1.0:110630", "حقق", "SOURCE-GAP", "نوع الثمر غير مسمى؛ لا يجيز الهيكل انتخاب حقق أو اسم فاكهة عربي بعينه."),
    gap("aed-v1.0:110740", "حكن", "OPEN-CANDIDATE", "praise لا يطابق حكن أو حنك، ولا يدخل حمد بصامتين مغايرين."),
    gap("aed-v1.0:110790", "حكن", "OPEN-CANDIDATE", "lion-shaped door-bolt لا يطابق حكن أو حنك، وشكل الأسد لا يثبت اسم المزلاج العربي."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT
assert {item.state for item in DECISIONS} <= LEGAL_CLOSURES
assert {item.verdict for item in DECISIONS} <= LEGAL_CLOSURES

OUTSIDE_FAN = {
    "aed-v1.0:89660", "aed-v1.0:97350",
    "aed-v1.0:106490", "aed-v1.0:110340",
}

WITNESS_NOTES = {
    "aed-v1.0:89660": "قال الصحاح: «نكب عن الطريق ينكب نكوبا: عدل»؛ وقال المحكم: «نكب عن الطريق ينكب: عدل». بقي g↔ك بلا صف مصري موقع.",
    "aed-v1.0:89720": "قال الصحاح: «نق الضفدع والعقرب والدجاجة ينق نقيقا: صوت»؛ وقال المحكم: «نق الظليم والدجاجة ونقنق: صوت». بقي g↔ق بلا صف مصري موقع.",
    "aed-v1.0:94010": "قال الصحاح: «اللباس ما يلبس، وكذلك اللبوس»؛ وقال المحكم: «اللبوس ما يلبس من الثياب والدروع». بقي المانح والمسار الفردي غير مسميين.",
    "aed-v1.0:97350": "قال المحكم: «هوى وأهوى وانهوى: سقط»؛ وأثبت تاج العروس أن الهوى والمهوى والهاوية في السقوط من علو. بقي ꜣ↔و بلا صف مصري موقع.",
    "aed-v1.0:98720": "قال المحكم في التهنئة: «قال له ليهنئك»، ووصف الهنيء بأنه السائغ؛ وأثبت تاج العروس التهنئة والهنيء في البشر والقبول. بقي i̯↔ء بلا صف مصري موقع.",
    "aed-v1.0:99580": "قال الصحاح: «هت الحديث هتا» في حسن السرد وكثرة الكلام؛ وقال لسان العرب: «هت البكر يهت هتيتا» و«هتت قوائم البعير: صوت وقعها». بقي ṯ↔ت بلا صف مصري موقع.",
    "aed-v1.0:103740": "قال لسان العرب: «المحبس، وهي المقرمة التي تبسط على وجه الفراش للنوم»؛ وقال تاج العروس: «حبست الفراش بالمحبس، أي سترته».",
    "aed-v1.0:106490": "أثبت الصحاح تجنيب الشيء وإبعاده، وقال لسان العرب في جنبته الشيء إنه نحاه عنه. بقي ḥ↔ج بلا صف مصري موقع.",
    "aed-v1.0:110340": "قال الصحاح: «الحكم: القضاء» وذكر الحكم بين القوم؛ وقال المحكم: «حكم بينهم يحكم» في القضاء والولاية. بقي q-ꜣ↔ك-م بلا مسار مصري موقع.",
}


def round28_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R27.round27_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND27-COMPLETION", "ROUND28-COMPLETION")
    card = card.replace(
        f"round27-egyptian-rank={rank}/{CARD_COUNT}",
        f"round28-egyptian-rank={rank}/{CARD_COUNT}",
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
        raise SystemExit("Round-twenty-eight marker already exists; append refused.")

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
        round28_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الثامنة والعشرون: استمرار المخزون المصري المسجل المفتوح (2026-08-26)", "",
        (
            "أعيد فحص الآرامية أولا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرا، فسجل الانتقال المسمى `{TRANSITION}`. انتقيت ثمانين "
            "بطاقة مصرية بدءا من `WO-C-OPEN-COMP-01503` بقصر الهيكل ثم موضع "
            "اللقطة. استبعد صف ḏ المؤجل. في كل بطاقة عرضت إصابات AED كلها بلا "
            "حد، وكتب وسم الطريق والرسم والمدخل المختار، وحفظ الاختلاف "
            "والمتجانسات بلا محو. فحصت حالة الإغلاق والحكم آليا على القائمة "
            "القانونية وحدها في `data/closure-vocabulary.json`."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-01503 إلى WO-C-OPEN-COMP-01542", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-01543 إلى WO-C-OPEN-COMP-01582", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([f"<!-- LANE-C-R28-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    states = dict(sorted(collections.Counter(item.state for item in DECISIONS).items()))
    verdicts = dict(sorted(collections.Counter(item.verdict for item in DECISIONS).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    now = datetime.now(ZoneInfo("Africa/Cairo")).strftime("%Y-%m-%d %H:%M:%S %z")
    now = now[:-2] + ":" + now[-2:]
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة الثامنة والعشرون: المسار C، الساميات والمصرية (2026-08-26)", "",
        f"- الوقت: {now}.",
        "- أعيد فحص الساميات أولا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01503` إلى `WO-C-OPEN-COMP-01542`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01543` إلى `WO-C-OPEN-COMP-01582`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طبق الانضباط الثلاثي: كل موجب له صوت موقع وحدث مجمد ومدار مكتوب؛ وكل بطاقة أخرى لها عائق شريف مسمى.",
        "- قاموس الإغلاق المغلق وحده مطبق: كل حالات الإغلاق والأحكام اجتازت القائمة القانونية في `data/closure-vocabulary.json`.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ الموجب مقصور على عضو AED ومداره المكتوب.",
        "- الموجب: `ḥbs↔حبس` في التغطية بالمحبس والستر، بمسار الجذر الكامل `IDN-14 + IDN-05 + IDN-07`، وحكمه `ROOT-ECHO`.",
        "- المطابقات الدلالية المرفوعة بقيت فجوات قانون: `ngb↔نكب` و`ngg↔نقق` و`hꜣi̯↔هوي` و`hni̯↔هنأ` و`hṯt↔هتت` و`ḥnb↔جنب` و`ḥqꜣ↔حكم`.",
        "- أوسمة القرض السامي العامة في `nhr` و`rbš` و`rg.t` بقيت `DIRECTION-GAP` بلا مانح مسمى أو طريق فردي.",
        "- حرفا الجر أغلِقا `OUT-OF-SCOPE`، والتركيبان أغلِقا `COMPOUND-BOUNDARY`، وصف ḏ المصري المؤجل بقي مستبعدا.",
        "- لم يحدث شحن أو إيداع أو إعداد مرحلي أو تحديث لمشتقات النشر.", "",
        f"LANE-C DONE28 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
        R27.R26.R25.R24.R23.R20.R10.append(
            EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian,
        )
        R27.R26.R25.R24.R23.R20.R10.append(
            REPORT, f"{MARKER}:REPORT", report,
        )
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
