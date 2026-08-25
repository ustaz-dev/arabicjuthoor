#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 26 completion cards without shipping or git.

The live short Aramaic queue is checked before continuing the registered
Egyptian open queue.  The script completes WO-C-OPEN-COMP-01343..01422 in two
forty-card batches.  Every closure and verdict is checked against the current
closed closure vocabulary before any append is allowed.
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

import harvest_lane_c_round25 as R25


R9 = R25.R9
AR = R25.AR
ROOT = R25.ROOT
ARAMAIC = R25.ARAMAIC
EGYPTIAN = R25.EGYPTIAN
REPORT = R25.REPORT

MARKER = "LANE-C-ROUND26-2026-08-25"
FIRST_SERIAL = 1343
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)

with (ROOT / "data" / "closure-vocabulary.json").open(encoding="utf-8") as handle:
    LEGAL_CLOSURES = frozenset(json.load(handle)["legal"])


def open_gap(member_id: str, candidate: str, state: str, reason: str,
             sound: str = "المروحة بنيوية فقط؛ لا يرقى التشابه إلى قانون أو نسب.",
             orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
             keywords: str = "", zero: str = "") -> R9.Decision:
    """Create an open ruling using only a current legal closure label."""
    assert state in LEGAL_CLOSURES
    return R9.Decision(
        member_id, candidate, "OPEN-CANDIDATE", state, R9.words(keywords),
        zero, sound, orbit, reason,
    )


def positive(member_id: str, candidate: str, verdict: str, keywords: str,
             sound: str, orbit: str, reason: str,
             zero: str = "") -> R9.Decision:
    """Create a positive ruling whose closure is the legal verdict itself."""
    assert verdict in R9.POSITIVE
    assert verdict in LEGAL_CLOSURES
    return R9.Decision(
        member_id, candidate, verdict, verdict, R9.words(keywords),
        zero, sound, orbit, reason,
    )


def terminal(member_id: str, candidate: str, verdict: str, reason: str,
             zero: str = "") -> R9.Decision:
    """Create a legal terminal closure."""
    assert verdict in LEGAL_CLOSURES
    return R9.Decision(
        member_id, candidate, verdict, verdict, (), zero,
        "الإغلاق بنيوي أو وظيفي؛ لم يستعمل التشابه السطحي لإصدار نسب.",
        "المسار المسمى يعزل العضو ولا يورث حكمه لمتجانس أو مركب.",
        reason,
    )


# The two positives below alone have a complete sound path, a frozen event,
# and a one-step written semantic orbit.  Direct semantic comparisons blocked
# by an unsigned Egyptian correspondence stay LAW-GAP.  A matching sound and
# meaning with a frozen event for the wrong Arabic homonym stays TOOL-GAP.
# General "Sem. loan word" labels with no named donor stay DIRECTION-GAP.
DECISIONS: tuple[R9.Decision, ...] = (
    open_gap("aed-v1.0:41210", "معق", "SOURCE-GAP", "undergarment نفسها موسومة بالشك، ولا يعين AED نوع اللباس الذي يمكن أن يقوم عليه مدار عربي مخصوص."),
    open_gap("aed-v1.0:41330", "عقل", "OPEN-CANDIDATE", "precisely/correctly لا يطابق العقل أو الحبس في عقل، ولا حواس عقر وبقية المروحة دون إنشاء مدار ثان."),
    open_gap("aed-v1.0:41390", "عقر", "LAW-GAP", "قطعة اللحم تلتقي عقر الذبيحة والقطع، لكن ꜣ المصرية الأخيرة بإزاء ر العربية بلا صف مصري موقع.", sound="ꜥ↔ع في IDN-15، وq↔ق في IDN-12؛ ꜣ↔ر هي الرجل المصرية غير الموقعة.", orbit="العقر قطع قوائم الذبيحة حتى تسقط ثم نحرها؛ وهو مدار مباشر لقطعة اللحم الناتجة، وبقي الصوت وحده ناقصا.", keywords="عقر|قطع|نحر"),
    open_gap("aed-v1.0:41470", "عقو", "OPEN-CANDIDATE", "loaves/income يجمع حسين لا يطابقهما عقو أو عوق أو بقية المروحة بمعنى عربي عامل."),
    open_gap("aed-v1.0:41610", "عكك", "SOURCE-GAP", "AED لا يعين إلا kind of bread؛ لا نوع خبز مسمى يقوم عليه مدار عربي مخصوص."),
    open_gap("aed-v1.0:41680", "عجر", "SOURCE-GAP", "AED لا يعين إلا an ointment؛ لا مادة دهن مسماة يمكن فصلها من المتجانسات."),
    open_gap("aed-v1.0:41730", "عجن", "DIRECTION-GAP", "وسم Sem. loan word يثبت جهة سامية عامة ولا يسمي مانحا فرديا أو طريق انتقال، فلا يصدر نسب ولا عزل مانح مخصوص."),
    open_gap("aed-v1.0:41780", "عقس", "DIRECTION-GAP", "وسم Sem. loan word لا يسمي المانح أو الطريق، ومعنى baked goods نفسه محاط بأقواس الشك."),
    open_gap("aed-v1.0:41850", "عدن", "DIRECTION-GAP", "وسم Sem. loan word لا يسمي مانحا فرديا أو طريقا، وتعيين cereal/wheat نفسه محتمل لا محسوم."),
    open_gap("aed-v1.0:42480", "وات", "OPEN-CANDIDATE", "evil لا يطابق حواس وات أو واط أو الصور اللامية والراءية، ولا يدخل سوء من خارج الهيكل."),
    open_gap("aed-v1.0:42940", "وار", "OPEN-CANDIDATE", "dance لا يجد في وار أو وال أو بقية المروحة شاهد رقص عاملا."),
    open_gap("aed-v1.0:43020", "ورح", "OPEN-CANDIDATE", "wreath/garland لا يطابق حواس ورح أو ولح، ولا يدخل وشاح بصامت زائد غير مرخص."),
    open_gap("aed-v1.0:43300", "واس", "OPEN-CANDIDATE", "dominion/power لا يجد في واس أو ورس وبقية المروحة شاهد سلطان أو قوة عاملا."),
    open_gap("aed-v1.0:43500", "واج", "OPEN-CANDIDATE", "shout for joy لا يطابق حواس واج أو ورج وبقية المروحة، ولا يورث العضو أصوات متجانس آخر."),
    open_gap("aed-v1.0:44320", "وعر", "OPEN-CANDIDATE", "candle/torch لا يجد في وعر أو وغر وبقية المروحة اسم شعلة أو سراج عاملا."),
    open_gap("aed-v1.0:44490", "وعب", "OPEN-CANDIDATE", "meat offering لا يطابق الوعب للجمع والاستيعاب، ولا يستبدل بالفعل وهب مع غياب صف ꜥ↔ه مصري موقع."),
    open_gap("aed-v1.0:44690", "وعر", "OPEN-CANDIDATE", "fugitive لا يطابق الوعورة في وعر ولا الحقد في وغر، ولا يدخل فر أو هرب من خارج الرسم."),
    terminal("aed-v1.0:44940", "∅", "OUT-OF-SCOPE", "حرف جر وظيفي بمعنى opposite/against؛ لا مادة جذرية معجمية مستقلة في العضو."),
    open_gap("aed-v1.0:45420", "وبد", "SOURCE-GAP", "المادة الطبية غير مسماة، وsoot نفسها موسومة بالشك؛ لا مدار قبل تعيين المكون."),
    open_gap("aed-v1.0:45490", "وبو", "OPEN-CANDIDATE", "festival العامة لا تطابق حواس وبو أو وفو أو الصور الأقصر في العربية المقروءة."),
    open_gap("aed-v1.0:45870", "وفر", "OPEN-CANDIDATE", "discuss/support لا يطابق الوفرة أو التوفير في وفر، ولا يدمج الفعلان في مقابل مفترض."),
    open_gap("aed-v1.0:45940", "ومت", "OPEN-CANDIDATE", "the thick of the enemy لا يجد في ومت أو ومط أو النواة شاهد كثافة جماعة العدو عاملا."),
    open_gap("aed-v1.0:45980", "ومت", "SOURCE-GAP", "fodder نفسها موسومة بالشك في اللغتين؛ لا يصدر مدار علف من حس غير محسوم."),
    open_gap("aed-v1.0:46050", "ونن", "OPEN-CANDIDATE", "exist/become لا يطابق حواس ونن العربية، ولا يدخل كان أو صار بصوامت أخرى."),
    open_gap("aed-v1.0:46130", "ونت", "OPEN-CANDIDATE", "rope/cord لا يجد في ونت أو ونط أو صور النواة اسما للحبل عاملا، ولا تقلب الصوامت إلى وتن."),
    terminal("aed-v1.0:46220", "∅", "COMPOUND-BOUNDARY", "الرسم المنشور wn-rʾ مركب ذو حد ظاهر؛ لا يختزل opening/hole في جذر عربي واحد قبل تحليل جزأيه بمصدر صرفي."),
    open_gap("aed-v1.0:46320", "وني", "TOOL-GAP", "الصوت والمعنى يلتقيان في الربط بالحبل والعقد، لكن الحدث المجمد المتاح لوني مقصور على الفتور والتوقف، لا على العضو العربي الونية بمعنى العقد أو الجوالق؛ فلا تكتمل الرجل الثالثة.", sound="w↔و في IDN-10، وn↔ن في IDN-03، وi̯↔ي في IDN-23؛ جذر كامل صوتيا.", orbit="AED يثبت tow with the tow rope/binden؛ والمحكم ولسان العرب يثبتان الونية للعقد من الدر والجوالق، وهو مدار الربط بالحبل والأداة مباشرة.", keywords="الونية|العقد من الدر|الجوالق"),
    open_gap("aed-v1.0:47040", "ونش", "OPEN-CANDIDATE", "grape/raisin لا يجد في ونش أو ونس اسما للعنب أو الزبيب عاملا."),
    open_gap("aed-v1.0:47830", "ورم", "SOURCE-GAP", "poetical composition نفسها موسومة بالشك؛ لا يعين AED نوع النص أو بنيته."),
    open_gap("aed-v1.0:48040", "ورح", "OPEN-CANDIDATE", "ointment لا يجد في ورح أو ولح مادة دهن أو طيب عاملة."),
    open_gap("aed-v1.0:48090", "ورس", "OPEN-CANDIDATE", "headrest لا يطابق الورس للنبات والصبغ، ولا حواس ولس أو ورش وبقية المروحة."),
    open_gap("aed-v1.0:48440", "وحم", "OPEN-CANDIDATE", "repeat لا يطابق الوحم لشهوة الحامل أو بقية حواس وحم، ولا يدخل عاد بصوامت أخرى."),
    positive("aed-v1.0:48560", "وهن", "ROOT-ECHO", "الوهن|الضعف|أوهن", "w↔و في IDN-10، وh↔ه في IDN-20، وn↔ن في IDN-03؛ جذر كامل.", "وهن العربية ضعف التماسك والقوة؛ والسقوط في الخراب نتيجة بنيوية مباشرة لهذا الوهن، وهو ظل معنى واحد لا مساواة كل overturn بكل ضعف.", "ECHO مقصور على مدار ضعف التماسك المؤدي إلى الانهيار، لا على معنى الهدم المتعدي كله."),
    open_gap("aed-v1.0:48770", "وحع", "OPEN-CANDIDATE", "offer لا يجد في وحع أو وحض أو وحغ فعلا للعطاء أو القربان عاملا."),
    open_gap("aed-v1.0:48820", "وحع", "OPEN-CANDIDATE", "Weha اسم مهرجان تأسيس معبد؛ تعريف المناسبة لا يثبت مادة الاسم ولا يجيز توريث معنى الفعل المجاور."),
    open_gap("aed-v1.0:49110", "وخا", "OPEN-CANDIDATE", "blustering of a storm لا يطابق حواس وخا أو وخر أو وخل، ولا يدخل هبوب بصوامت أخرى."),
    open_gap("aed-v1.0:49200", "وخا", "OPEN-CANDIDATE", "column/pillar لا يجد في وخا أو وخر أو وخل اسما للدعامة عاملا."),
    open_gap("aed-v1.0:49260", "وخا", "SOURCE-GAP", "صلة المدخل بعمل الحصير نفسها موسومة بالشك؛ لا فعل محددا يقوم عليه المدار."),
    open_gap("aed-v1.0:49530", "وزف", "OPEN-CANDIDATE", "idleness لا يطابق وزف للإسراع والدنو ولا وسف لليبس، ولا يقلب التضاد صلة."),
    open_gap("aed-v1.0:49820", "وسع", "LAW-GAP", "breadth/width يطابق السعة ضد الضيق، لكن ḫ المصرية بإزاء ع العربية بلا صف مصري موقع.", sound="w↔و في IDN-10، وs↔س في IDN-07؛ ḫ↔ع هي الرجل المصرية غير الموقعة.", orbit="وسع الشيء واتسع صارت له سعة وعرض؛ وهو مدار breadth/width مباشرة، وبقي الصوت وحده ناقصا.", keywords="وسع|السعة|الضيق|اتسع"),
    open_gap("aed-v1.0:50120", "وشر", "OPEN-CANDIDATE", "feeder of animals لا يطابق حواس وشر أو وسر وبقية المروحة، ولا يرث العامل اسم العلف."),
    open_gap("aed-v1.0:50250", "وشي", "OPEN-CANDIDATE", "reduce to bits لا يطابق الوشي للنقش أو الاستخراج برفق، ولا يجد في وسي شاهد التفتيت عاملا."),
    open_gap("aed-v1.0:50320", "وسب", "LAW-GAP", "feed on يلتقي الوسب للعشب الذي ترعاه الدواب، لكن š المصرية بإزاء س العربية لا صف مصريا موقعا لها؛ SIB-01 مقيد بالفروع السامية الشمالية.", sound="w↔و في IDN-10، وb↔ب في IDN-05؛ š↔س هي الرجل المصرية غير الموقعة.", orbit="الوسب عشب الأرض ونباتها الكثير، وهو مادة تغذي الحيوان في مدار واحد مع feed on، وبقي الصوت وحده ناقصا.", keywords="الوسب|العشب|كثر عشبها|نباتها"),
    open_gap("aed-v1.0:50390", "وشب", "SOURCE-GAP", "الوعاء المعدني نفسه محاط بأقواس الشك، ومادته مرددة بين النحاس والذهب؛ لا عضو مادي معين."),
    open_gap("aed-v1.0:50590", "وسم", "SOURCE-GAP", "AED يجمع وعاء معدن محاطا بالشك ومكيال بيرة؛ لا يحدد إن كان العضو إناء أو وحدة قياس."),
    open_gap("aed-v1.0:50760", "وجر", "OPEN-CANDIDATE", "inundation لا يطابق وجر الدواء في الفم؛ اشتراك السائل لا يجعل الفيض صبا علاجيا، وꜣ↔ر غير موقع أيضا."),
    positive("aed-v1.0:50850", "وجب", "ROOT-ECHO", "سمع صوت|الوجبة|الهدة", "w↔و في IDN-10، وg↔ج في IDN-08، وb↔ب في IDN-05؛ جذر كامل.", "وجب العربية تحمل الوجبة ذات الهدة وصوت كركرة البعير المسموع؛ وcry out يحفظ بروز الصوت القوي في مدار مسموع واحد، لا نوع مصدر الصوت.", "ECHO للصوت القوي المسموع فقط؛ لا مساواة بين الصياح الإنساني وكل سقوط أو وجوب."),
    open_gap("aed-v1.0:50910", "وجس", "OPEN-CANDIDATE", "bird لا يجد في وجس أو وجش أو وقص اسما للطائر؛ وgutted نفسها محتملة لا تورث معنى القطع."),
    open_gap("aed-v1.0:51020", "وتي", "MORPHOLOGY-GAP", "wt.j اسم مهنة embalmer، لكن اللقطة لا تقدم تحليلا صرفيا موقعا يجيز نزع .j وربط الباقي بالفعل wt؛ فلا يفترض جذر المهنة."),
    open_gap("aed-v1.0:51700", "ودن", "OPEN-CANDIDATE", "offering لا يجد في ودن أو وضن اسما للقربان أو فعلا للعطاء عاملا."),
    open_gap("aed-v1.0:52960", "برت", "OPEN-CANDIDATE", "bush/shrub لا يطابق برت للفأس التي يقطع بها الشجر؛ الأداة لا ترث اسم النبات المقطوع."),
    open_gap("aed-v1.0:53130", "∅", "SOURCE-GAP", "AED لا يثبت إلا أن العضو verb بلا معنى معجمي؛ لا يمكن كتابة مدار أو انتخاب مقابل."),
    open_gap("aed-v1.0:53190", "بري", "OPEN-CANDIDATE", "hole لا يطابق البري للقطع أو البرء، ولا حواس بلي وباي وبقية المروحة."),
    open_gap("aed-v1.0:53310", "برو", "OPEN-CANDIDATE", "cargo-boat لا يجد في برو أو بلو أو بقية المروحة اسما لسفينة حمل عاملا."),
    open_gap("aed-v1.0:53560", "برح", "SOURCE-GAP", "AED لا يعين إلا a kind of baked goods؛ لا نوع طعام مسمى يمكن فصله من الرسم."),
    open_gap("aed-v1.0:53830", "برك", "OPEN-CANDIDATE", "servant/underling لا يساوي بروك البعير أو الثبات في برك؛ ومدار الخضوع المفترض يحتاج ꜣ↔ر غير الموقع ولا يكفي وحده."),
    open_gap("aed-v1.0:54170", "بيت", "SOURCE-GAP", "تعريف الوعاء الفضي كله محاط بأقواس الشك؛ لا يرقى الاحتواء العام إلى مقابل قبل تثبيت الجسم."),
    open_gap("aed-v1.0:54300", "بير", "OPEN-CANDIDATE", "meteoric mineral/ore لا يجد في بير أو بيا وبقية المروحة اسم معدن أو حجر عامل."),
    open_gap("aed-v1.0:54540", "بيو", "SOURCE-GAP", "part of a ship غير مسمى، ومادته الخشبية نفسها محتملة؛ لا ينتخب عضو سفينة عربي من الهيكل."),
    open_gap("aed-v1.0:54590", "بيف", "SOURCE-GAP", "to cry نفسها موسومة بالشك في اللغتين؛ لا يصدر مدار صوت من فعل غير محسوم."),
    open_gap("aed-v1.0:54860", "بغي", "LAW-GAP", "flood يلتقي بغي السماء في شدة المطر ومجاوزة الحد، لكن ꜥ المصرية بإزاء غ العربية بلا صف مصري موقع.", sound="b↔ب في IDN-05، وy↔ي في IDN-23؛ ꜥ↔غ هي الرجل المصرية غير الموقعة.", orbit="بغت السماء اشتد مطرها، وكل مجاوزة للحد بغي؛ وهو مدار الفيضان مباشرة، وبقي الصوت وحده ناقصا.", keywords="بغت السماء|اشتد مطرها|مجاوزة|المطر"),
    open_gap("aed-v1.0:55020", "بعح", "SOURCE-GAP", "AED يشك في كون المرجع birds وفي كونه كناية عن abundance؛ لا يثبت طائرا ولا معنى مجازيا."),
    open_gap("aed-v1.0:55160", "بوت", "SOURCE-GAP", "تعريف group of participants كله محاط بأقواس التحرير، ولا يسمي نوع الجماعة أو بنيتها المعجمية."),
    open_gap("aed-v1.0:55470", "بفن", "OPEN-CANDIDATE", "bark لا يجد في بفن مقابلا عربيا ولا يدخل نباح بصوامت أخرى."),
    open_gap("aed-v1.0:55510", "بين", "MORPHOLOGY-GAP", "escape/depart يطابق بان وبين للفراق، لكن AED يسجل bnu̯ فعلا ثالثه ضعيف نهائي، والعربية بين عائلة جوف وسطها ياء؛ لا قانون صرفي موقع ينقل شبه الصائت بين الموضعين.", sound="b↔ب في IDN-05 وn↔ن في IDN-03؛ موضع شبه الصائت مختلف بين b-n-w المصرية وب-y-n العربية.", orbit="بان يبين بينا وبينونة أي فارق وانقطع؛ وهو مدار escape/depart مباشرة، وبقي تحليل الضعيف وحده ناقصا.", keywords="البين|الفراق|بان|بينونة", zero="حفظ وسم verb_3-inf والصامت النهائي الضعيف في bnu̯؛ لم ينقل إلى جوف العربية بحدس."),
    open_gap("aed-v1.0:55820", "بنن", "OPEN-CANDIDATE", "overflow/swell لا يطابق حواس بنن للبنان أو الإقامة، ولا يدخل فاض أو ورم من خارج الرسم."),
    open_gap("aed-v1.0:55960", "بني", "OPEN-CANDIDATE", "sweetness هنا اسم قناة، ولا يطابق البناء أو البنوة في بني؛ الاسم المرجعي لا يثبت مادة عربية."),
    open_gap("aed-v1.0:56150", "بنق", "SOURCE-GAP", "abound in نفسها موسومة بالشك، ولا تعين الأطعمة التي كثر بها العضو."),
    open_gap("aed-v1.0:56240", "بند", "OPEN-CANDIDATE", "clothing/garment لا يطابق البند للعلم أو الربط، وbelt نفسها احتمال بين الأقواس لا يثبت حس الحزام."),
    open_gap("aed-v1.0:56560", "برك", "DIRECTION-GAP", "AED وHoch يسمان العضو Sem. loan word، لكن اللقطة لا تسمي مانحا ساميا فرديا أو طريقه؛ فلا يدخل gifts في بسط الوراثة ولا يعزل لمانح مفترض."),
    open_gap("aed-v1.0:56690", "بهر", "OPEN-CANDIDATE", "fan لا يطابق البهر للنبات والضياء ولا البحر، ولا يدخل مروحة بصوامت أخرى."),
    open_gap("aed-v1.0:56920", "بحث", "LAW-GAP", "hunt يلتقي البحث في الطلب والتفتيش، لكن s المصرية بإزاء ث العربية لا يمر بـBR-EGYP-03 بلا نظير سامي أم مسمى المصدر لهذا العضو.", sound="b↔ب في IDN-05 وḥ↔ح في IDN-14؛ s↔ث مشروط في BR-EGYP-03 بنظير سامي أم مسمى غير موجود هنا.", orbit="البحث طلب الشيء والتفتيش عنه؛ والصيد طلب الطريدة في مدار واحد، وبقي الصوت وحده ناقصا.", keywords="البحث|طلب|فتش|التفتيش"),
    open_gap("aed-v1.0:57020", "بخن", "OPEN-CANDIDATE", "greywacke لا يجد في بخن اسما للصخر الرمادي ولا في المروحة بديلا معجميا عاملا."),
    open_gap("aed-v1.0:57310", "بسر", "OPEN-CANDIDATE", "protect لا يطابق البسر أو البسل أو بقية المروحة، ولا يدخل حفظ أو منع من خارج الرسم."),
    open_gap("aed-v1.0:57420", "∅", "SOURCE-GAP", "AED لا يثبت إلا أن العضو noun بلا معنى معجمي؛ لا يمكن كتابة مدار أو انتخاب مقابل."),
    open_gap("aed-v1.0:57570", "بشر", "SOURCE-GAP", "malted barley نفسها موسومة بالشك؛ لا يثبت AED أن المعالجة تقشير حتى تربط ببشر الأديم."),
    open_gap("aed-v1.0:57610", "بشو", "OPEN-CANDIDATE", "vomit لا يجد في بشو أو بسو أو الصور الأقصر اسما للقيء أو فعلا له عاملا."),
    open_gap("aed-v1.0:57770", "بقس", "OPEN-CANDIDATE", "iron ore لا يجد في بقس أو بقش أو بقص اسم معدن أو حجر عامل."),
    open_gap("aed-v1.0:57920", "بكن", "OPEN-CANDIDATE", "excrement of small domestic animals لا يطابق حواس بكن العربية، ولا يدخل روث أو بعر من خارج الرسم."),
    open_gap("aed-v1.0:58450", "بدي", "SOURCE-GAP", "تعريف seat كله محاط بأقواس التحرير وthrone نفسها محتملة؛ لا يثبت نوع المقعد المحكوم."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT
assert {item.state for item in DECISIONS} <= LEGAL_CLOSURES
assert {item.verdict for item in DECISIONS} <= LEGAL_CLOSURES

OUTSIDE_FAN = {
    "aed-v1.0:49820", "aed-v1.0:55510", "aed-v1.0:56920",
}

WITNESS_NOTES = {
    "aed-v1.0:41390": "قال المحكم: «عقر الفرس: قطع قوائمه»؛ وقال مفردات الراغب: «عقرت البعير: نحرته».",
    "aed-v1.0:46320": "قال المحكم: «الونية: العقد من الدر، وقيل: هي الجوالق»؛ ونقل لسان العرب المعنيين نفسيهما.",
    "aed-v1.0:48560": "قال الصحاح: «الوهن: الضعف»؛ وقال لسان العرب: «الوهن: الضعف في العمل والأمر، وكذلك في العظم ونحوه».",
    "aed-v1.0:49820": "أثبت الصحاح ولسان العرب أن السعة نقيض الضيق، وأن وسع الشيء واتسع صار ذا عرض وامتداد.",
    "aed-v1.0:50320": "قال كتاب العين: «الوسب من الأرض ما كثر عشبه»؛ وقال الصحاح: «وسبت الأرض وأوسبت: كثر عشبها».",
    "aed-v1.0:50850": "قال الصحاح: «الوجبة: السقطة مع الهدة»؛ وقال أساس البلاغة: «وجب البعير: برك حتى سمع صوت كركرته».",
    "aed-v1.0:54860": "قال الصحاح: «بغت السماء: اشتد مطرها»؛ وأثبت المحكم أن بغي السماء شدة مطرها ومعظمه.",
    "aed-v1.0:55510": "قال الصحاح: «البين: الفراق، تقول منه بان يبين بينا وبينونة»؛ وقال المحكم: «بان بينا وبينونة: انقطع».",
    "aed-v1.0:56920": "قال كتاب العين: «البحث طلبك شيئا»؛ وقال الصحاح: «بحثت عن الشيء: فتشت عنه».",
}


def round26_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R25.round25_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND25-COMPLETION", "ROUND26-COMPLETION")
    card = card.replace(
        f"round25-egyptian-rank={rank}/{CARD_COUNT}",
        f"round26-egyptian-rank={rank}/{CARD_COUNT}",
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
        raise SystemExit("Round-twenty-six marker already exists; append refused.")

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
        round26_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة السادسة والعشرون: استمرار المخزون المصري المسجل المفتوح (2026-08-25)", "",
        (
            "أعيد فحص الآرامية أولا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرا، فسجل الانتقال المسمى `{TRANSITION}`. انتقيت ثمانون "
            "بطاقة مصرية بدءا من `WO-C-OPEN-COMP-01343` بقصر الهيكل ثم موضع "
            "اللقطة. استبعد صف ḏ المؤجل. في كل بطاقة عرضت إصابات AED كلها بلا "
            "حد، وكتب وسم الطريق والرسم والمدخل المختار، وحفظ الاختلاف "
            "والمتجانسات بلا محو. فحصت حالة الإغلاق والحكم آليا على القائمة "
            "القانونية وحدها في `data/closure-vocabulary.json`."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-01343 إلى WO-C-OPEN-COMP-01382", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-01383 إلى WO-C-OPEN-COMP-01422", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([f"<!-- LANE-C-R26-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    states = dict(sorted(collections.Counter(item.state for item in DECISIONS).items()))
    verdicts = dict(sorted(collections.Counter(item.verdict for item in DECISIONS).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    now = datetime.now(ZoneInfo("Africa/Cairo")).strftime("%Y-%m-%d %H:%M:%S %z")
    now = now[:-2] + ":" + now[-2:]
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة السادسة والعشرون: المسار C، الساميات والمصرية (2026-08-25)", "",
        f"- الوقت: {now}.",
        "- أعيد فحص الساميات أولا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01343` إلى `WO-C-OPEN-COMP-01382`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01383` إلى `WO-C-OPEN-COMP-01422`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طبق الانضباط الثلاثي: كل موجب له صوت موقع وحدث مجمد ومدار مكتوب؛ وكل بطاقة أخرى لها عائق شريف مسمى.",
        "- قاموس الإغلاق المغلق وحده مطبق: كل حالات الإغلاق والأحكام اجتازت القائمة القانونية في `data/closure-vocabulary.json`، ولم يستعمل أي وسم موروث خارجها.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ الموجبان مقصوران على عضوي AED ومداريهما المكتوبين.",
        "- الموجبان: `whn↔وهن` في ضعف التماسك المؤدي إلى الخراب، و`wgb↔وجب` في الصوت القوي المسموع؛ كلاهما `ROOT-ECHO` لا دعوى تطابق تام.",
        "- الفجوات المرفوعة لا المرتجلة: `ꜥqꜣ↔عقر` و`wsḫ↔وسع` و`wšb↔وسب` و`bꜥy↔بغي` و`bḥs↔بحث` بقيت `LAW-GAP`، و`wni̯↔وني` بقيت `TOOL-GAP` لاختلاف الحدث المجمد، و`bnu̯↔بين` بقيت `MORPHOLOGY-GAP` لاختلاف موضع الضعيف.",
        "- أوسمة القرض السامي العامة بلا مانح مسمى بقيت `DIRECTION-GAP`، وصف ḏ المصري المؤجل بقي مستبعدا.",
        "- لا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE26 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
        R25.R24.R23.R20.R10.append(EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian)
        R25.R24.R23.R20.R10.append(REPORT, f"{MARKER}:REPORT", report)
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
