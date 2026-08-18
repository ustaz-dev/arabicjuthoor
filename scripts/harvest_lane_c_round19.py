#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 19 completion cards without shipping.

Round eighteen was accepted and consolidated. This append-only round
rechecks the exhausted short live-open Aramaic queue, records the continued
transition to the registered Egyptian queue, and completes two forty-card
batches from WO-C-OPEN-COMP-00926. AED is read without a hit limit and the
deferred Egyptian ḏ row remains excluded. No git, publication, or shipping
command is run.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import unicodedata

import harvest_lane_c_round18 as R18


R9 = R18.R9
R10 = R18.R10
AR = R18.AR
ROOT = R18.ROOT
ARAMAIC = R18.ARAMAIC
EGYPTIAN = R18.EGYPTIAN
REPORT = R18.REPORT
MARKER = "LANE-C-ROUND19-2026-08-18"
FIRST_SERIAL = 926
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)


# Every judgment remains scoped to one AED member. The fan is a retrieval
# surface, not a correspondence law. In this window hrw/حلو and zꜢb/سرب
# have a direct semantic bridge but still lack a complete named Egyptian sound
# path; ḫnr is explicitly labelled Semitic without a named donor or direction.
# Uncertain AED events remain source gaps, and no neighbouring homograph lends
# its meaning to the selected member.
DECISIONS: tuple[R9.Decision, ...] = (
    R9.gap("aed-v1.0:71110", "منخ", "SOURCE-GAP",
           "to be joyful موسوم بالشك في الإنجليزية؛ لا يثبت حدث الفرح قبل حسم القراءة، ولا يرث معنى splendid من المتجانس."),
    R9.gap("aed-v1.0:71400", "منق", "SEMANTIC-GAP",
           "complete/come to an end لا يطابق مادة منق العربية المسجلة، ولا تُدمج معاني الإتمام والمجازاة والمنح الألمانية في مقابل مفترض."),
    R9.gap("aed-v1.0:72470", "مري", "SEMANTIC-GAP",
           "love/wish لا يطابق حواس مري/مرء/ملي/ملء العربية، ولا يُدخل الحب أو الإرادة من خارج المروحة."),
    R9.gap("aed-v1.0:73070", "مهي", "SEMANTIC-GAP",
           "be forgetful لا يطابق حواس مهي/محي العربية، ولا يُدخل النسيان من خارج الرسم."),
    R9.gap("aed-v1.0:73360", "محي", "SEMANTIC-GAP",
           "care for/be concerned about لا يطابق حواس محي العربية، ولا يُدخل الرعاية أو الهم من خارج الرسم."),
    R9.gap("aed-v1.0:74230", "مخا", "SEMANTIC-GAP",
           "make fast/bind لا يطابق التبرؤ والاعتذار في مخا ولا حواس مخل/مخر، ولا يُدخل الربط من خارج الرسم."),
    R9.gap("aed-v1.0:74280", "مخر", "SEMANTIC-GAP",
           "make level/match/be like لا يطابق شق الماء أو إرسال الماء في مخر، ولا تُدمج التسوية والمماثلة في مادة مفترضة."),
    R9.gap("aed-v1.0:74950", "مسي", "SEMANTIC-GAP",
           "give birth/fashion/create لا يطابق حواس مسي/مشي/مصي العربية، ولا تُدخل الولادة أو الخلق من خارج المروحة."),
    R9.gap("aed-v1.0:78220", "مدن", "SEMANTIC-GAP",
           "relax/be relaxed لا يطابق حواس مدن/مضن العربية، ولا يُسوّى السكون بالعمران أو الإقامة."),
    R9.gap("aed-v1.0:78280", "مدس", "SEMANTIC-GAP",
           "be sharp/do violence لا يطابق حواس مدس وبقية المروحة، ولا تُجمع الحدة والعنف في مقابل واحد."),
    R9.gap("aed-v1.0:80150", "نيم", "SEMANTIC-GAP",
           "be happy لا يطابق حواس نيم/نءم العربية، ولا يُدخل الفرح من مادة نعيم خارج المروحة."),
    R9.gap("aed-v1.0:80270", "نيك", "SEMANTIC-GAP",
           "punish/be punished لا يطابق حواس نيك/نءك العربية، ولا يُدخل العقوبة من خارج الرسم."),
    R9.gap("aed-v1.0:80800", "نور", "SEMANTIC-GAP",
           "see/look/watch لا يساوي النور الذي يعين على الإبصار؛ علاقة الوسيلة بالفعل لا تثبت جذرًا، وꜣ↔ر غير موقعة هنا."),
    R9.gap("aed-v1.0:81230", "نوي", "SEMANTIC-GAP",
           "take care of/collect لا يطابق نوى الشيء أي قصده، ولا تُسوّى العناية أو الجمع بالقصد."),
    R9.gap("aed-v1.0:81440", "نوح", "SEMANTIC-GAP",
           "drink/make drunk لا يطابق النوح أو حواس نوح العربية، ولا يُدخل الشرب من خارج الرسم."),
    R9.gap("aed-v1.0:81460", "نوخ", "SEMANTIC-GAP",
           "heat/be scorched لا يطابق حواس نوخ العربية، ولا يُدخل الطبخ أو الاحتراق من خارج الرسم."),
    R9.gap("aed-v1.0:82580", "نبي", "SEMANTIC-GAP",
           "be aflame لا يطابق حواس نبي وبقية المروحة، ولا يرث معنى flame من المتجانس الاسمي المجاور."),
    R9.gap("aed-v1.0:84240", "نمع", "SEMANTIC-GAP",
           "be biased لا يطابق حواس نمع/نمض/نمغ العربية، ولا يُدخل الميل الحزبي من خارج الرسم."),
    R9.gap("aed-v1.0:84350", "نمح", "SEMANTIC-GAP",
           "be poor لا يطابق حواس نمح العربية، ولا تُدمج معاني الفقر والبؤس واليتم الألمانية في مقابل مفترض."),
    R9.gap("aed-v1.0:84820", "نني", "SEMANTIC-GAP",
           "weary/inert/subside لا يطابق حواس نني/ننء العربية، ولا تُجمع الأحوال الثلاثة في مادة مفترضة."),
    R9.gap("aed-v1.0:85950", "نحا", "SEMANTIC-GAP",
           "fierce/unruly/abnormal لا يطابق حواس نحا/نحر/نحل العربية، ولا تُجمع الشراسة والاضطراب والمرض في مقابل واحد."),
    R9.gap("aed-v1.0:86130", "نحب", "SEMANTIC-GAP",
           "give/loan لا يطابق حواس نحب العربية، ولا يُدخل العطاء أو الإقراض من خارج الرسم."),
    R9.gap("aed-v1.0:86430", "نحم", "SEMANTIC-GAP",
           "take away/rescue لا يطابق النحيم والصوت في نحم، ولا تُسوّى النجاة بالنزع."),
    R9.gap("aed-v1.0:86500", "نحر", "SEMANTIC-GAP",
           "be like/resemble لا يطابق النحر أو حواس نحل العربية، ولا يُدخل الشبه من خارج الرسم."),
    R9.gap("aed-v1.0:86700", "نحض", "SEMANTIC-GAP",
           "be strong لا يطابق نحض اللحم بمعاني اكتنازه أو ذهابه، ولا يُدخل القوة المطلقة من خارج الاستعمال."),
    R9.gap("aed-v1.0:86830", "نخر", "SEMANTIC-GAP",
           "pendulous/dangle لا يطابق حواس نخر/نخل/نخا العربية، ولا يُدخل تدلي الثدي من خارج الرسم."),
    R9.gap("aed-v1.0:87440", "نخخ", "SEMANTIC-GAP",
           "be new born لا يطابق حواس نخخ العربية، ولا يرث معنيي طول العمر والنمو من الشرح الألماني."),
    R9.gap("aed-v1.0:87560", "نخت", "SEMANTIC-GAP",
           "strong/strengthen/protect لا يطابق حواس نخت وبقية المروحة، ولا تُجمع القوة والحماية في مادة مفترضة."),
    R9.gap("aed-v1.0:88270", "نسر", "SEMANTIC-GAP",
           "burn up/shrivel لا يطابق حواس نسر/نشر/نصر العربية، ولا يُسوّى الانكماش بالنشر أو القطع."),
    R9.gap("aed-v1.0:88350", "نسس", "SEMANTIC-GAP",
           "do damage to لا يطابق حواس نسس وبقية المروحة، ولا يُدخل الإضرار من خارج الرسم."),
    R9.gap("aed-v1.0:89260", "نكر", "SEMANTIC-GAP",
           "think about لا يطابق الإنكار أو حواس نكا/نكل العربية، ولا يُدخل الفكر من خارج الرسم."),
    R9.gap("aed-v1.0:89500", "نقر", "SEMANTIC-GAP",
           "kill/cut up لا يطابق النقر أو حواس نجر/نقل/نغر العربية مباشرة، ولا يُدخل القتل من خارج المروحة."),
    R9.gap("aed-v1.0:89530", "نقل", "SEMANTIC-GAP",
           "lack/be lacking لا يطابق النقل أو حواس نجا/نقر/نغر العربية، ولا يُدخل النقص من خارج الرسم."),
    R9.gap("aed-v1.0:89630", "نجي", "SEMANTIC-GAP",
           "break open لا يطابق حواس نجي/نقي/نغي العربية، ولا يُدخل الكسر أو الفتح من خارج المروحة."),
    R9.gap("aed-v1.0:89820", "نتي", "SEMANTIC-GAP",
           "be oppressed لا يطابق حواس نتي/نطي العربية، ولا يُدخل الضيق أو القهر من خارج الرسم."),
    R9.gap("aed-v1.0:93540", "روي", "SEMANTIC-GAP",
           "go away/expel/drive off لا يطابق الري أو الرواية في روي ولا اللي في لوي، ولا تُدمج الأفعال الثلاثة."),
    R9.gap("aed-v1.0:95560", "رحح", "SEMANTIC-GAP",
           "burn لا يطابق حواس رحح/لحح العربية، ولا يُدخل الاحتراق من خارج الرسم."),
    R9.gap("aed-v1.0:99050", "حلو", "LAW-GAP",
           "pleased/at peace/content يلتقي حلا الشيء ولذ وطاب، لكن h-r-w لا يسوي ح-l-w بطريق مصري كامل موقع.",
           sound="w↔و ظاهر؛ r↔l له صف الكتابة المصري BR-EGYP-01، أما h↔ح فليس موقعًا لهذا العضو في الشبكة النافذة.",
           orbit="الرضا والاستطابة مدار مباشر؛ at peace أوسع ولا يرث الحكم.",
           keywords="حلا|حلو|لذ|طاب|طيب"),
    R9.gap("aed-v1.0:99170", "حرب", "SEMANTIC-GAP",
           "sink/be immersed لا يطابق الحرب أو حواس هرب/حرف/حلب/حلف العربية، ولا يُدخل الغوص من خارج الرسم."),
    R9.gap("aed-v1.0:100680", "حاي", "SEMANTIC-GAP",
           "come أو blow لا يطابق حواس حاي/حري/حلي العربية، ولا تُدمج الحركة والريح في مادة مفترضة."),
    R9.gap("aed-v1.0:100710", "حري", "SEMANTIC-GAP",
           "bare/be naked لا يطابق حواس حري/حلي العربية، ولا يُدخل التجرد من خارج الرسم."),
    R9.gap("aed-v1.0:101610", "حرج", "SEMANTIC-GAP",
           "be glad لا يطابق الحرج أو حواس حلق/حرق العربية، ولا يُدخل الفرح من خارج المروحة."),
    R9.gap("aed-v1.0:102060", "حعي", "SEMANTIC-GAP",
           "rejoice/be happy لا يطابق حواس حعي/حضي/حغي العربية، ولا يُدخل الفرح من خارج الرسم."),
    R9.gap("aed-v1.0:102920", "حوع", "SEMANTIC-GAP",
           "be short لا يطابق حواس حوع/حوض/حوغ العربية، ولا يُدخل القصر من خارج الرسم."),
    R9.gap("aed-v1.0:103040", "حون", "SEMANTIC-GAP",
           "become young/be rejuvenated لا يطابق حواس حون العربية، ولا يُدخل الشباب من خارج الرسم."),
    R9.gap("aed-v1.0:104540", "حفك", "SEMANTIC-GAP",
           "drink milk from an udder لا يطابق حواس حفك العربية، ولا يُدخل الحلب أو الشرب من خارج الرسم."),
    R9.gap("aed-v1.0:104570", "حفد", "SEMANTIC-GAP",
           "sit/settle لا يطابق حواس حفد/حفض العربية، ولا يُدخل الجلوس أو الاستقرار من خارج الرسم."),
    R9.gap("aed-v1.0:105330", "حمو", "SEMANTIC-GAP",
           "be skilled/skilful لا يطابق حواس حمو العربية، ولا يُدخل الحذق من خارج الرسم."),
    R9.gap("aed-v1.0:108340", "حري", "SEMANTIC-GAP",
           "be far/remove oneself لا يطابق حواس حري/حلي العربية، ولا يُدخل البعد من خارج الرسم."),
    R9.gap("aed-v1.0:109290", "ححي", "SEMANTIC-GAP",
           "go/tread لا يطابق حواس ححي/ححء العربية، ولا يُدخل المشي أو الوطء من خارج الرسم."),
    R9.gap("aed-v1.0:109680", "حسي", "SEMANTIC-GAP",
           "sing/make music لا يطابق حواس حسي/حشي/حصي العربية، ولا يُدخل الغناء من خارج المروحة."),
    R9.gap("aed-v1.0:110540", "حقر", "SEMANTIC-GAP",
           "be hungry/fast لا يطابق حقر بمعاني الصغر والذلة ولا حقل، ولا يُدخل الجوع أو الصوم من خارج الرسم."),
    R9.gap("aed-v1.0:110650", "حقق", "SEMANTIC-GAP",
           "be provided لا يطابق تحقق الشيء أو أحكامه في حقق، ولا يُدخل التجهيز من خارج الرسم."),
    R9.gap("aed-v1.0:112230", "حدق", "SEMANTIC-GAP",
           "cut off لا يطابق الحدقة أو حواس حدق/حضق العربية، ولا يُدخل القطع من خارج الرسم."),
    R9.gap("aed-v1.0:114170", "خاخ", "SEMANTIC-GAP",
           "come in haste/be fast لا يطابق حواس خاخ/خلخ/خرخ العربية، ولا يُدخل السرعة من خارج الرسم."),
    R9.gap("aed-v1.0:114460", "خيي", "SEMANTIC-GAP",
           "be high/mount up لا يطابق حواس خيي/خيء العربية، ولا يُدخل العلو من خارج الرسم."),
    R9.gap("aed-v1.0:114740", "خعي", "SEMANTIC-GAP",
           "appear in glory/be shining لا يطابق حواس خعي/خضي/خغي العربية، ولا يُدخل الظهور أو الضياء من خارج الرسم."),
    R9.gap("aed-v1.0:115310", "خود", "SEMANTIC-GAP",
           "be rich/enrich لا يطابق حواس خود/خوض العربية، ولا يُدخل الغنى من خارج الرسم."),
    R9.gap("aed-v1.0:115660", "خبن", "SEMANTIC-GAP",
           "distort/be criminal لا يطابق حواس خبن العربية، ولا تُجمع الإمالة والجناية في مقابل واحد."),
    R9.gap("aed-v1.0:117290", "خمت", "SEMANTIC-GAP",
           "treble/do thrice لا يطابق حواس خمت العربية، ولا يُدخل العدد ثلاثة أو صيغة التكرار من خارج الرسم."),
    R9.gap("aed-v1.0:117690", "خني", "SEMANTIC-GAP",
           "make music/dance لا يطابق حواس خني/خنء العربية، ولا يُدخل العزف أو الرقص من خارج الرسم."),
    R9.gap("aed-v1.0:117860", "خنف", "SEMANTIC-GAP",
           "take in air/breathe لا يطابق حواس خنف/خنب العربية، ولا يُدخل التنفس من خارج الرسم."),
    R9.gap("aed-v1.0:118410", "خنر", "DIRECTIONAL-TRANSMISSION",
           "be hoarse موسوم قرضًا ساميًا، لكن AED لا يسمي المانح أو طريق النقل، وحواس خنر/خنل العربية لا تثبت الفعل.",
           sound="ḫ-n-r↔خ-n-r صورة سطحية ممكنة؛ الهوية الجزئية لا تحسم المانح ولا اتجاه النقل.",
           orbit="البحة معينة في المصرية، ولم يثبت لها عضو عربي مباشر في المادة المقروءة."),
    R9.gap("aed-v1.0:118760", "خنت", "SEMANTIC-GAP",
           "bring to someone لا يطابق حواس خنت وبقية المروحة، ولا يرث معنى الجبهة أو الحامل من المتجانسات."),
    R9.gap("aed-v1.0:121540", "خطي", "SEMANTIC-GAP",
           "see لا يطابق الخطأ أو حواس ختي/خطي العربية، ولا يُدخل البصر من خارج الرسم."),
    R9.gap("aed-v1.0:122320", "خلل", "SOURCE-GAP",
           "be resolute موسوم بالشك، فلا يثبت هل الحدث عزم أو قرار أو صفة أخرى، ولا يرث معنى stake من المتجانس."),
    R9.gap("aed-v1.0:122440", "خرب", "SEMANTIC-GAP",
           "be crooked لا يطابق الخراب أو حواس خلب/حرب/حلب العربية، ولا يرث تقوس المنجل أو الترقوة من الاسمين المجاورين."),
    R9.gap("aed-v1.0:122650", "حرك", "SEMANTIC-GAP",
           "cunning/hostile لا يطابق الحركة أو حواس حلك/خرك العربية، ولا تُجمع المكر والعداوة في مقابل واحد."),
    R9.gap("aed-v1.0:124570", "خسر", "SEMANTIC-GAP",
           "be unanointed لا يطابق الخسران؛ وwretched الألماني موسوم بالشك ولا يحول غياب الدهن إلى ذل عربي."),
    R9.gap("aed-v1.0:124600", "خزي", "SEMANTIC-GAP",
           "be weak/wretched يجاور الذل والهوان في خزي، لكنه لا يساوي الضعف نفسه؛ بقي مدار الحدث غير مطابق ولم يصدر حكم."),
    R9.gap("aed-v1.0:124710", "حقص", "SEMANTIC-GAP",
           "be injured، المقصور ألمانيًا على عين حورس، لا يطابق حواس حقص/خقص العربية، ولا يُدخل الجرح من خارج الرسم."),
    R9.gap("aed-v1.0:124730", "حكر", "SEMANTIC-GAP",
           "adorn/be adorned لا يطابق الاحتكار أو حواس حكر/خكر العربية، ولا يرث معنى scratch من المتجانس."),
    R9.gap("aed-v1.0:124980", "خدر", "SOURCE-GAP",
           "be in discomfort وrescue كلاهما موسوم بالشك ومتعارضان في الحدث؛ لا يصدر مدار خدر قبل حسم القراءة."),
    R9.gap("aed-v1.0:126160", "سار", "SEMANTIC-GAP",
           "wise/prudent/understand لا يطابق السير أو حواس ساء/سلل/سرر العربية، ولا تُجمع الحكمة والفهم في مقابل مفترض."),
    R9.gap("aed-v1.0:126200", "شاي", "SEMANTIC-GAP",
           "be sated/sate لا يطابق حواس شاي وبقية المروحة، ولا يُدخل الشبع بصامت باء خارج الرسم."),
    R9.gap("aed-v1.0:126330", "زرو", "SEMANTIC-GAP",
           "break/be broken لا يطابق حواس زرو/سرو العربية، ولا يرث معنى beam من المتجانس الاسمي."),
    R9.gap("aed-v1.0:126590", "سرب", "LAW-GAP",
           "flow/drip يطابق سرب الماء والدمع أي جرى وسال، لكن z-ꜣ-b لا يسوي س-r-b بطريق مصري كامل موقع.",
           sound="b↔ب هوية؛ z↔س وꜣ↔ر لا يجتمعان في مسار عضو مصري موقع في الشبكة النافذة.",
           orbit="سرب الماء جرى على وجه الأرض وسرب الدمع سال؛ مدار الجريان والتقطر مباشر.",
           keywords="سرب|الماء|جرى|سال|الدمع"),
    R9.gap("aed-v1.0:126630", "سرب", "SEMANTIC-GAP",
           "make tarry يعاكس سرب في الأرض أي ذهب وجرى، ولا يرث عضو التأخير معنى flow من المتجانس السابق."),
    R9.gap("aed-v1.0:126750", "صرم", "SEMANTIC-GAP",
           "burn up لا يطابق الصرم والقطع ولا حواس سام/سلم/شرم العربية، ولا يُدخل الاحتراق من خارج الرسم."),
    R9.gap("aed-v1.0:126800", "سرر", "SEMANTIC-GAP",
           "be wise لا يطابق السرور أو السر في سرر ولا حواس سار/سال العربية، ولا يُدخل الحكمة من خارج الرسم."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT


def round19_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R18.round18_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND18-COMPLETION", "ROUND19-COMPLETION")
    card = card.replace(
        "ROUND19-COMPLETION (2026-08-17)",
        "ROUND19-COMPLETION (2026-08-18)",
    )
    card = card.replace(
        f"round18-egyptian-rank={rank}/{CARD_COUNT}",
        f"round19-egyptian-rank={rank}/{CARD_COUNT}",
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
        raise SystemExit("Round-nineteen marker already exists; append refused.")

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
        for item in DECISIONS if item.candidate not in {"∅", ""}
    }
    matches = AR.matches_for_roots(AR.DEFAULT_RESOURCES, roots, None)
    cards = [
        round19_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة التاسعة عشرة: استمرار المخزون المصري المسجل المفتوح (2026-08-18)", "",
        ("أُعيد فحص الآرامية أولًا فكان الطابور القصير الحي ذا المروحة غير الفارغة صفرًا. "
         f"لذلك سُجل الانتقال المسمى `{TRANSITION}`. انتُقيت البطاقات المصرية التالية "
         "بدءًا من `WO-C-OPEN-COMP-00926` بقصر الهيكل ثم موضع اللقطة. استُبعد صف ḏ "
         "المؤجل. في كل بطاقة عُرضت إصابات AED كلها بلا حد، وكُتب وسم الطريق والرسم "
         "والمدخل المختار، وحُفظ الاختلاف والمتجانسات بلا محو."), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-00926 إلى WO-C-OPEN-COMP-00965", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-00966 إلى WO-C-OPEN-COMP-01005", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([f"<!-- LANE-C-R19-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    state_counts = dict(sorted(collections.Counter(item.state for item in DECISIONS).items()))
    verdict_counts = dict(sorted(collections.Counter(item.verdict for item in DECISIONS).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة التاسعة عشرة: المسار C (2026-08-18)", "",
        "- أُعيد فحص الساميّات أولًا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تُكرر بطاقة سامية.",
        f"- عند نفاد الساميّات سُجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- كُتبت الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00926` إلى `WO-C-OPEN-COMP-00965`.",
        "- كُتبت الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00966` إلى `WO-C-OPEN-COMP-01005`.",
        "- طُبقت قواعد AED الثلاث: كل الإصابات بلا حد؛ وسم الطريق والرسم والمدخل المختار مكتوبة؛ الاختلاف والمتجانسات محفوظة بلا محو.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(state_counts, ensure_ascii=False, sort_keys=True)}؛ لا فجوة حُولت إلى نفي.",
        f"- الأحكام: {json.dumps(verdict_counts, ensure_ascii=False, sort_keys=True)}؛ لم يصدر حكم موجب في هذه النافذة.",
        "- المطابقتان الدلاليتان ذواتا الرجل الصوتية الناقصة بقيتا مفتوحتين باسميهما: `hrw↔حلو` و`zꜣb↔سرب`.",
        "- `ḫnr↔خنر` بقي `DIRECTIONAL-TRANSMISSION`: وسم القرض السامي لا يسمي مانحًا أو طريقًا.",
        "- الأعضاء المشكوكة لم تُسوَّ قسرًا: `mnḫ` للفرح، و`ẖꜣꜣ` للعزم، و`ẖdr` لعدم الراحة/الإنقاذ بقيت `SOURCE-GAP`.",
        "- صف ḏ مؤجل بقرار المؤلف؛ استُبعد من الانتقاء وبقيت بطاقاته على حالها.",
        "- لا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE19 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
        "states": state_counts,
        "verdicts": verdict_counts,
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
        R10.append(EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian)
        R10.append(REPORT, f"{MARKER}:REPORT", report)
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
