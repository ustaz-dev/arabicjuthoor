#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 17 completion cards without shipping.

Round sixteen was accepted and consolidated. This append-only round rechecks
the exhausted short live-open Aramaic queue, records the continued transition
to the registered Egyptian queue, and completes two forty-card batches from
WO-C-OPEN-COMP-00766. AED is read without a hit limit and the deferred
Egyptian ḏ row remains excluded. No git, publication, or shipping command is
run.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
import re
import sys
import unicodedata


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import harvest_lane_c_round16 as R16  # noqa: E402


R9 = R16.R9
R10 = R16.R10
AR = R16.AR
ARAMAIC = R16.ARAMAIC
EGYPTIAN = R16.EGYPTIAN
REPORT = R16.REPORT
MARKER = "LANE-C-ROUND17-2026-08-17"
FIRST_SERIAL = 766
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)


# Every decision is scoped to the named AED member. Direct translations remain
# open when the complete Egyptian-to-Arabic sound path, frozen event, Arabic
# morphology, or named transmission direction is missing. In particular,
# km.t cannot borrow the Egyptian feminine t as though it were the third root
# consonant of Arabic كمت, and the two generic Semitic-loan labels do not name
# a donor or direction.
DECISIONS: tuple[R9.Decision, ...] = (
    R9.gap("aed-v1.0:111230", "حتب", "SEMANTIC-GAP",
           "be pleased/content or set of the sun لا يطابق البحت أو حواس حتب العربية، ولا يُدخل رضا أو غروب من خارج الرسم."),
    R9.gap("aed-v1.0:114550", "خيت", "SEMANTIC-GAP",
           "sky/roof لا يطابق حواس خيت العربية، ولا يُدخل سماء أو سقف من خارج الرسم."),
    R9.gap("aed-v1.0:115810", "خبس", "SEMANTIC-GAP",
           "hack up the earth/plough لا يطابق حواس خبس/خبش العربية المقروءة، ولا يُدخل حرث من خارج الرسم."),
    R9.gap("aed-v1.0:119980", "خور", "LAW-GAP",
           "low-lying land يطابق الخور، أي المنخفض من الأرض بين النشزين، لكن ḫ-r-w لا يسوي خ-w-r بلا قلب مكاني غير موقع.",
           sound="ḫ↔خ وr↔ر وw↔و ظاهرة منفردة؛ ترتيب r-w المصري بإزاء و-r العربي يحتاج قلبًا غير موقع.",
           orbit="المنخفض من الأرض هو low-lying land مباشرة؛ رجل الصوت وحدها باقية.",
           keywords="الخور|المنخفض|الأرض"),
    R9.gap("aed-v1.0:121980", "خدت", "SEMANTIC-GAP",
           "land-register اسم سجل إداري لا يطابق حواس خدت/خد العربية، ولا يُدخل كتاب أو أرض من خارج الرسم."),
    R9.gap("aed-v1.0:122920", "خبي", "SOURCE-GAP",
           "وصف sun disk encircled by uraei موضوع بين معقوفين ولا يقدم اسم الشيء أو تحليله الجذري؛ لا يصدر مدار خبي."),
    R9.gap("aed-v1.0:123160", "خنت", "SEMANTIC-GAP",
           "water-procession لا يطابق حواس خنت/حنت العربية، ولا يرث فعل التجذيف من العضو التالي."),
    R9.gap("aed-v1.0:123230", "خني", "SEMANTIC-GAP",
           "convey by water/row لا يطابق حواس خني/حني العربية، ولا يُدخل جذف أو حمل من خارج الرسم."),
    R9.gap("aed-v1.0:127010", "سرح", "SEMANTIC-GAP",
           "grant of land لا يطابق السرح بمعاني الإرسال والمال السائم، ولا يحول فعل المنح إلى مادة سرح."),
    R9.gap("aed-v1.0:128270", "سيف", "MORPHOLOGY-GAP",
           "اليوم العاشر تسمية تقويمية مشتقة من الشهر القمري، ولا تحمل سيف العربية صرف العدد أو اليوم."),
    R9.gap("aed-v1.0:130600", "سوح", "SEMANTIC-GAP",
           "wind/breath لا يطابق حواس سوح العربية، ولا يُدخل ريح أو نفس من خارج الرسم."),
    R9.gap("aed-v1.0:130850", "صوت", "SEMANTIC-GAP",
           "gust of wind ليس الصوت نفسه، ولا يكفي أن الريح قد تحدث صوتًا لنقل اسم الأثر إلى الهبة."),
    R9.gap("aed-v1.0:131180", "سبا", "SEMANTIC-GAP",
           "star لا يطابق حواس سبا/شبا/صبا العربية، ولا يُدخل نجم من خارج الرسم."),
    R9.gap("aed-v1.0:131270", "ستر", "LAW-GAP",
           "sun shade يطابق السترة التي يستتر بها، لكن s-b-ꜣ لا يسوي س-t-r بطريق مصري كامل.",
           sound="s↔س ظاهر؛ b↔ت وꜣ↔ر غير موقعين لهذا العضو.",
           orbit="الحاجز من الشمس سترة مباشرة؛ الصوت يمنع الحكم.",
           keywords="الستر|السترة|استتر"),
    R9.gap("aed-v1.0:136170", "زنت", "SOURCE-GAP",
           "ocherous earth of Wadi Natrun وصف معدني موضوع بين معقوفين ولا يعين مادة أو اسمًا؛ لا يصدر مدار زنت."),
    R9.gap("aed-v1.0:138540", "سنت", "SEMANTIC-GAP",
           "temple foundation/ground plan لا يطابق حواس سنت العربية، ولا يُدخل أساس أو رسم من خارج الهيكل."),
    R9.gap("aed-v1.0:139420", "صرف", "SEMANTIC-GAP",
           "flood water coming to rest on land لا يطابق صرف الماء وتحويله، ولا يُسوّى الاستقرار بالإبعاد."),
    R9.gap("aed-v1.0:140270", "سحت", "SEMANTIC-GAP",
           "herd of sheep treading seed لا يطابق حواس سحت العربية، ولا يرث فعل الدوس من الوصف الاعتراضي."),
    R9.gap("aed-v1.0:140630", "سبح", "SEMANTIC-GAP",
           "wind لا يطابق السبح والعوم والتصرف، ولا تكفي حركة الريح لتسمية المادة نفسها."),
    R9.gap("aed-v1.0:141220", "سحد", "NAME-ROOT-OPEN",
           "a star وصف نكرة موضوع بين معقوفين بلا اسم أو تحليل جذري؛ لا يربط بسحد العربية."),
    R9.gap("aed-v1.0:143090", "سخت", "SOURCE-GAP",
           "a stretch of water تعريف عام موضوع بين معقوفين لا يعين نوع المسطح أو حدوده؛ لا يصدر مدار سخت."),
    R9.gap("aed-v1.0:147460", "ستا", "SEMANTIC-GAP",
           "flame/lamp لا يطابق حواس ستا/سطا العربية، ولا يُدخل نار أو سراج من خارج الرسم."),
    R9.gap("aed-v1.0:148260", "ستف", "SOURCE-GAP",
           "of water pouring out وصف ناقص موضوع بين معقوفين لا يثبت اسمًا ولا حدثًا معجميًا مستقلًا."),
    R9.gap("aed-v1.0:152920", "شوو", "SEMANTIC-GAP",
           "dry land لا يطابق حواس شوو/شوا العربية، ولا يُدخل يبس أو أرض من خارج الرسم."),
    R9.gap("aed-v1.0:155700", "شنع", "SEMANTIC-GAP",
           "lion-form water spout اسم أداة مصورة لا يطابق حواس شنع العربية، ولا يرث الأسد أو الماء جذرًا."),
    R9.gap("aed-v1.0:158010", "ستر", "LAW-GAP",
           "hidden water يلتقي الستر دلاليًا، لكن š-t-ꜣ لا يسوي س-t-r بطريق مصري كامل.",
           sound="t↔ت هوية؛ š↔س وꜣ↔ر موضعان غير موقعين لهذا العضو.",
           orbit="الماء الخفي مستور، لكن وصفه لا يكمل رجل الصوت.",
           keywords="الستر|استتر|خفي"),
    R9.gap("aed-v1.0:158600", "شدت", "SEMANTIC-GAP",
           "well/water hole لا يطابق حواس شدت/شد العربية، ولا يُدخل بئر من خارج الرسم."),
    R9.gap("aed-v1.0:158780", "شدي", "SEMANTIC-GAP",
           "field/meadow/parcel of land لا يطابق حواس شدي/سدي العربية، ولا يرث معنى البئر من المتجانس السابق."),
    R9.gap("aed-v1.0:158860", "شدو", "SEMANTIC-GAP",
           "field/meadow/parcel of land لا يطابق الشدو العربي، ولا يرث معنى العضو ذي النهاية y."),
    R9.gap("aed-v1.0:159060", "قرر", "SEMANTIC-GAP",
           "hill/high ground يعاكس القرار والقرارة بوصفهما مستقر الأرض وقاعها؛ لا تُحوّل الصورة المتشابهة إلى صلة."),
    R9.gap("aed-v1.0:160130", "قبي", "SEMANTIC-GAP",
           "water/beer jar لا يطابق حواس قبي العربية، ولا يُدخل جرة أو شراب من خارج الرسم."),
    R9.gap("aed-v1.0:160190", "قبب", "SEMANTIC-GAP",
           "cool wind لا يطابق حواس قبب العربية في اليبس والضمور والصوت، ولا يُدخل برد من خارج الرسم."),
    R9.gap("aed-v1.0:161810", "قرر", "SEMANTIC-GAP",
           "fire pottery/cook food لا يطابق القرار أو القر البارد، ولا يرث معنى hill من المتجانس السابق."),
    R9.gap("aed-v1.0:165700", "ككو", "SEMANTIC-GAP",
           "flood water لا يطابق حواس ككو/كوك العربية، ولا يُدخل فيضان من خارج الرسم."),
    R9.gap("aed-v1.0:167920", "جرح", "SEMANTIC-GAP",
           "night لا يطابق حواس جرح/قرح/غرح العربية، ولا يُدخل ليل من خارج الرسم."),
    R9.gap("aed-v1.0:169520", "طرح", "LAW-GAP",
           "plunge into water يلتقي طرح الشيء وإلقاءه، لكن t-ꜣ-ḥ لا يسوي ط-r-ح بطريق مصري كامل.",
           sound="ḥ↔ح ظاهر؛ t↔ط وꜣ↔ر غير موقعين لهذا العضو.",
           orbit="الإلقاء في الماء صورة مباشرة من الطرح؛ رجل الصوت مانعة.",
           keywords="طرح|رمى|ألقى"),
    R9.gap("aed-v1.0:172480", "تني", "SEMANTIC-GAP",
           "tired land تعبير وصفي لا يطابق حواس تني/طني العربية، ولا يُدخل إعياء أو أرض من خارج الرسم."),
    R9.gap("aed-v1.0:174480", "ثور", "LAW-GAP",
           "air/wind/breath يجاور ثوران الريح والغبار، لكن ṯ-ꜣ-w لا يسوي ث-w-r بلا قلب ومسار كامل.",
           sound="ṯ↔ث ظاهر؛ ترتيب ꜣ-w بإزاء و-r يحتاج تحويلًا وقلبًا غير موقعين.",
           orbit="العربية تسمي هيجان الشيء وارتفاعه ثورانًا، لا الهواء نفسه؛ بقي الصوت والمدار دون حكم.",
           keywords="ثار|ثوران|هاج|الغبار"),
    R9.gap("aed-v1.0:175660", "ثنو", "SEMANTIC-GAP",
           "river cliffs forming a boundary لا يطابق حواس ثنو/تنو/طنو العربية، ولا يُدخل جرف أو حد من خارج الرسم."),
    R9.gap("aed-v1.0:176430", "ثرت", "DIRECTIONAL-TRANSMISSION",
           "finely ground wheat flour موسوم قرضًا ساميًا، لكن AED لا يسمي المانح أو طريق النقل، ولا تثبت ثرت العربية هذا الدقيق.",
           sound="ṯ-r-t↔ث-r-t صورة سطحية ممكنة؛ الهوية لا تحسم المانح ولا التحليل الصرفي.",
           orbit="الدقيق معين في المصرية، ولم يثبت له عضو عربي مباشر في المادة المقروءة."),
    R9.gap("aed-v1.0:177010", "ثزت", "SEMANTIC-GAP",
           "heaven/roof لا يطابق حواس ثزت/تزت العربية، ولا يُدخل سماء أو سقف من خارج الرسم."),
    R9.gap("aed-v1.0:177390", "ثكر", "NAME-ROOT-OPEN",
           "Tjeker اسم شعب من شعوب البحر، ولا يقدم AED تحليلًا جذريًا يسمح بنقله إلى مادة ثكر العربية."),
    R9.gap("aed-v1.0:179680", "دني", "SEMANTIC-GAP",
           "dam water/revet earthen banks لا يطابق دنو الشيء أو حواس دني العربية، ولا يُدخل سد من خارج الرسم."),
    R9.gap("aed-v1.0:500162", "يون", "SEMANTIC-GAP",
           "pillar of the moon لا يطابق حواس يون العربية، ولا يُدخل عمود أو قمر من خارج الرسم."),
    R9.gap("aed-v1.0:500898", "نحء", "SOURCE-GAP",
           "flame نفسها موسومة بالشك، ولا يثبت العضو مادة نحء أو نحر لمعنى النار."),
    R9.gap("aed-v1.0:850767", "كمت", "MORPHOLOGY-GAP",
           "black arable land يجاور الكمتة، وهي لون يخالط سواده حمرة، لكن t المصرية علامة تأنيث وt العربية صامت جذري أصيل فلا تُسوّيان.",
           sound="k-m↔ك-م هويتان؛ t المصرية المصنفة تأنيثًا لا تحمل التاء الجذرية في كمت العربية.",
           orbit="السواد حاضر في الكمتة العربية مع الحمرة، وفي اسم الأرض المصرية بلا حمرة؛ الصرف يمنع حكم الجذر أو النواة.",
           keywords="الكمتة|السواد|الحمرة|كميت"),
    R9.gap("aed-v1.0:856148", "وعء", "SEMANTIC-GAP",
           "star لا يطابق حواس وعء/وضء/وغء العربية، ولا يُدخل نجم من خارج الرسم."),
    R9.gap("aed-v1.0:857516", "بدو", "SEMANTIC-GAP",
           "earth almonds اسم طعام لا يطابق حواس بدو/فدو العربية، ولا يُدخل لوز أو درنة من خارج الرسم."),
    R9.gap("aed-v1.0:49", "روي", "SEMANTIC-GAP",
           "extend in width or length لا يطابق حواس روي/لوي العربية؛ اللي والانثناء لا يساويان الامتداد."),
    R9.gap("aed-v1.0:89", "لبخ", "SEMANTIC-GAP",
           "mix/join لا يطابق حواس لبخ العربية المقروءة، ولا يُدخل خلط من خارج الرسم."),
    R9.gap("aed-v1.0:199", "رخي", "SEMANTIC-GAP",
           "grow green/flourish/be inundated لا يطابق مادة رخي العربية المسجلة، ولا يجوز توريثها معاني رخاء العيش من مادة رخو أخرى."),
    R9.gap("aed-v1.0:359", "ءبخ", "SEMANTIC-GAP",
           "burn/cook لا يطابق حواس ءبخ/لبخ/ربخ العربية، ولا يجوز إدخال طبخ بصامت ط خارج المروحة."),
    R9.gap("aed-v1.0:10460", "ءرر", "SOURCE-GAP",
           "be frustrated نفسه موسوم بالشك، ولا يثبت عضوًا عربيًا في مروحة ءرر/ارر."),
    R9.gap("aed-v1.0:20900", "ياس", "SEMANTIC-GAP",
           "be bald لا يطابق اليأس أو حواس ياس العربية، ولا يُدخل صلع من خارج الرسم."),
    R9.gap("aed-v1.0:21070", "ياث", "SEMANTIC-GAP",
           "injure/be injured لا يطابق حواس ياث/يات العربية، ولا يُدخل جرح من خارج الرسم."),
    R9.gap("aed-v1.0:21140", "ياد", "SEMANTIC-GAP",
           "suffer/make suffer لا يطابق حواس ياد/ياض العربية، ولا يُدخل ألم من خارج الرسم."),
    R9.gap("aed-v1.0:21770", "يعر", "SEMANTIC-GAP",
           "mount up/touch/bring up لا يطابق حواس يعر/يعل العربية، ولا تُدخل عرج أو رفع خارج المروحة."),
    R9.gap("aed-v1.0:21930", "ءوي", "LAW-GAP",
           "come/return يلتقي أوى إلى منزله وأقام به بعد الوصول، لكن j-w-j لا يسوي ء-w-y بطريق مصري كامل.",
           sound="w↔و وj النهائية ↔ ي ظاهران؛ j الأولى ↔ ء غير موقعة لهذا العضو.",
           orbit="المجيء والرجوع ينتهيان إلى المأوى والإقامة فيه؛ هو مدار وصول واحد لا تطابق فعلين كاملين.",
           keywords="أوى|منزله|المأوى|أقام"),
    R9.gap("aed-v1.0:22560", "يون", "SOURCE-GAP",
           "carry in procession موسوم بالشك في المصدر الألماني ولا يطابق حواس يون العربية حتى يثبت الاستعمال."),
    R9.gap("aed-v1.0:22990", "يوح", "SEMANTIC-GAP",
           "load/carry لا يطابق حواس يوح/ءوح العربية، ولا يُدخل حمل من خارج الرسم."),
    R9.gap("aed-v1.0:23220", "يود", "SEMANTIC-GAP",
           "separate/lie between/be charged to لا يطابق حواس يود/يوض العربية، ولا تُدمج المعاني المتعددة في مقابل واحد."),
    R9.gap("aed-v1.0:23640", "يبي", "SEMANTIC-GAP",
           "be thirsty لا يطابق حواس يبي/ءبي العربية، ولا يُدخل ظمأ أو يبس بصامت زائد."),
    R9.gap("aed-v1.0:24820", "يام", "SEMANTIC-GAP",
           "kindly disposed/amiable لا يطابق حواس يام/ءام العربية، ولا يُدخل لطف من خارج الرسم."),
    R9.gap("aed-v1.0:26030", "يمن", "SEMANTIC-GAP",
           "hide/be hidden لا يطابق حواس يمن العربية، ولا يرث حكم عضو اليمين المتجانس السابق في السجل."),
    R9.gap("aed-v1.0:26370", "يمر", "SEMANTIC-GAP",
           "be deaf لا يطابق حواس يمر/ءمر العربية، ولا يُدخل صمم من خارج الرسم."),
    R9.gap("aed-v1.0:26400", "يمح", "SEMANTIC-GAP",
           "suck/drink لا يطابق حواس يمح/ءمح العربية، ولا يُدخل مص أو شرب من خارج الرسم."),
    R9.gap("aed-v1.0:26870", "يني", "SEMANTIC-GAP",
           "bring/bring away/buy لا يطابق حواس يني/ءني العربية، ولا تُدخل جنى أو أتى خارج المروحة."),
    R9.gap("aed-v1.0:27310", "ينب", "SOURCE-GAP",
           "be laid down/lie on the stomach موسوم بالشك في الوجهين، فلا يثبت مدار ينب العربية."),
    R9.gap("aed-v1.0:27810", "ينس", "SEMANTIC-GAP",
           "make eyes red لا يطابق حواس ينس/ءنس العربية، ولا يُدخل حمرة أو عين من خارج الرسم."),
    R9.gap("aed-v1.0:28050", "يند", "SEMANTIC-GAP",
           "be vexed/sad/sick لا يطابق حواس يند/ءند العربية، ولا تُدمج الأحوال الثلاثة في مادة مفترضة."),
    R9.gap("aed-v1.0:30560", "يحي", "SOURCE-GAP",
           "make music/music موسوم بالشك ومردد بين الفعل والاسم، فلا يصدر مدار يحي العربية."),
    R9.gap("aed-v1.0:31240", "يزي", "SEMANTIC-GAP",
           "be light in weight لا يطابق حواس يزي/يسي العربية، ولا يُدخل خفة من خارج الرسم."),
    R9.gap("aed-v1.0:31980", "يشف", "DIRECTIONAL-TRANSMISSION",
           "burn/scorch موسوم قرضًا ساميًا، لكن AED لا يسمي المانح أو الطريق، وحواس يشف/ءشف العربية لا تثبت هذا الفعل.",
           sound="j-š-f↔ي-ش-ف صورة سطحية ممكنة؛ الهوية لا تحسم المانح ولا الدلالة.",
           orbit="الإحراق معين في المصرية، ولم يثبت له عضو عربي مباشر في المادة المقروءة."),
    R9.gap("aed-v1.0:32240", "يقر", "SEMANTIC-GAP",
           "excellent/trustworthy لا يطابق مادة يقر العربية، ولا تُبدل j بواو وقار خارج المروحة."),
    R9.gap("aed-v1.0:32600", "يكن", "SEMANTIC-GAP",
           "seize/take hold of لا يطابق حواس يكن/ءكن العربية، ولا يُدخل قبض من خارج الرسم."),
    R9.gap("aed-v1.0:32910", "يتي", "SEMANTIC-GAP",
           "be king/rule as king لا يطابق حواس يتي/يطي العربية، ولا يُدخل ملك من خارج الرسم."),
    R9.gap("aed-v1.0:32980", "يتب", "SEMANTIC-GAP",
           "be useful/provided with لا يطابق حواس يتب/يطب العربية، ولا يُدخل نفع من خارج الرسم."),
    R9.gap("aed-v1.0:33530", "ءثر", "LAW-GAP",
           "steal/capture/carry off يجاور استأثر بالشيء، أي استبد به، لكن j-ṯ-ꜣ لا يسوي ء-ث-r بطريق مصري كامل.",
           sound="ṯ↔ث ظاهر؛ j↔ء وꜣ↔ر غير موقعين لهذا العضو.",
           orbit="الاستئثار انفراد بالشيء، وهو يجاور أخذه وحبسه للنفس؛ لا يساوي السرقة وحدها.",
           keywords="استأثر|الشيء|استبد|آثر"),
    R9.gap("aed-v1.0:33560", "يتي", "SEMANTIC-GAP",
           "take/seize لا يطابق حواس يتي/ءتي العربية، ولا يرث حكم عضو الملك المتجانس."),
    R9.gap("aed-v1.0:33740", "يثث", "SEMANTIC-GAP",
           "take wing لا يطابق حواس يثث/يتت العربية، ولا يُدخل طيران من خارج الرسم."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT


def round17_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R16.round16_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND16-COMPLETION", "ROUND17-COMPLETION")
    card = card.replace(
        f"round16-egyptian-rank={rank}/{CARD_COUNT}",
        f"round17-egyptian-rank={rank}/{CARD_COUNT}",
    )
    if decision.keywords:
        root = AR.normalize_root(decision.candidate)
        arabic_count = len(matches.get(root, []))
        card = re.sub(
            r"(?m)^- مسح المعاني العربية:.*$",
            (f"- مسح المعاني العربية: قُرئت {arabic_count} نتيجة للجذر `{root}` كاملةً "
             f"بما يكافئ `--max-chars 0`؛ ثبت موضع الدلالة المسجل في المدار، وبقي "
             f"العائق `{decision.state}`؛ لم يصدر حكم موجب."),
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
        raise SystemExit("Round-seventeen marker already exists; append refused.")

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
        round17_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة السابعة عشرة: استمرار المخزون المصري المسجل المفتوح (2026-08-17)", "",
        ("أُعيد فحص الآرامية أولًا فكان الطابور القصير الحي ذا المروحة غير الفارغة صفرًا. "
         f"لذلك سُجل الانتقال المسمى `{TRANSITION}`. انتُقيت البطاقات المصرية التالية "
         "بدءًا من `WO-C-OPEN-COMP-00766` بقصر الهيكل ثم موضع اللقطة. استُبعد صف ḏ "
         "المؤجل. في كل بطاقة عُرضت إصابات AED كلها بلا حد، وكُتب وسم الطريق والرسم "
         "والمدخل المختار، وحُفظ الاختلاف والمتجانسات بلا محو."), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-00766 إلى WO-C-OPEN-COMP-00805", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-00806 إلى WO-C-OPEN-COMP-00845", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([f"<!-- LANE-C-R17-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    state_counts = dict(sorted(collections.Counter(item.state for item in DECISIONS).items()))
    verdict_counts = dict(sorted(collections.Counter(item.verdict for item in DECISIONS).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة السابعة عشرة: المسار C (2026-08-17)", "",
        "- أُعيد فحص الآرامية أولًا: المفتوح القصير الحي ذو المروحة غير الفارغة=0؛ لم تُكرر بطاقة آرامية.",
        f"- سُجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل.",
        "- كُتبت الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00766` إلى `WO-C-OPEN-COMP-00805`.",
        "- كُتبت الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00806` إلى `WO-C-OPEN-COMP-00845`.",
        "- طُبقت قواعد AED الثلاث: كل الإصابات بلا حد؛ وسم الطريق والرسم والمدخل المختار مكتوبة؛ الاختلاف والمتجانسات محفوظة بلا محو.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(state_counts, ensure_ascii=False, sort_keys=True)}؛ لا فجوة حُولت إلى نفي.",
        f"- الأحكام: {json.dumps(verdict_counts, ensure_ascii=False, sort_keys=True)}؛ لم يصدر حكم موجب في هذه النافذة.",
        "- المطابقات الدلالية ذات الرجل الناقصة بقيت مفتوحة باسمها، ومنها `ḫr.w↔خور` للقلب، و`km.t↔كمت` للصرف، و`tꜣḥ↔طرح` و`jwi̯↔أوى` للصوت.",
        "- وسمَا القرض السامي في `ṯr.t` و`jšf` لا يسميان مانحًا أو طريقًا، فبقيا `DIRECTIONAL-TRANSMISSION`.",
        "- صف ḏ مؤجل بقرار المؤلف؛ استُبعد من الانتقاء وبقيت بطاقاته على حالها.",
        "- لا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE17 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
        R10.append(EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian)
        R10.append(REPORT, f"{MARKER}:REPORT", report)
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
