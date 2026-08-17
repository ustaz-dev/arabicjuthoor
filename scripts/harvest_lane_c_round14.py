#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 14 completion cards without shipping.

Round thirteen was accepted and consolidated.  This append-only round rechecks
the exhausted short live-open Aramaic queue, records the named transition to
the registered Egyptian queue, and completes two forty-card batches beginning
at WO-C-OPEN-COMP-00526.  AED is read without a hit limit and the deferred
Egyptian ḏ row remains excluded.  No git, publication, or shipping command is
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

import harvest_lane_c_round9 as R9  # noqa: E402
import harvest_lane_c_round10 as R10  # noqa: E402
import harvest_lane_c_round12 as R12  # noqa: E402
import search_arabic_root_senses as AR  # noqa: E402


ARAMAIC = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
EGYPTIAN = ROOT / "04-cross-linguistic" / "readings" / "egyptian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-C.md"
MARKER = "LANE-C-ROUND14-2026-08-17"
FIRST_SERIAL = 526
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)


# Decisions remain member-scoped.  A direct translation is not enough: the
# complete consonantal path, frozen event, two Arabic witnesses, and the loan
# screen must all work before a positive is issued.  The two positives below
# are limited to ḥmi̯ "repel" and sr.t "body of magistrates"; the named law,
# morphology, source, and direction gaps stay open rather than becoming
# negative claims.  The sole positive is limited to ḥmi̯ "repel"; sr.t keeps
# its dotted feminine ending and therefore cannot donate that t to Arabic سلط.
DECISIONS: tuple[R9.Decision, ...] = (
    R9.gap("aed-v1.0:39580", "عطس", "SOURCE-GAP",
           "AED لا يجزم بأن العرض الأنفي عطاس؛ وحتى على هذه القراءة يبقى r-š المصري بإزاء ط-س العربي بلا مسار كامل.",
           sound="ꜥ↔ع ظاهر؛ r↔ط وš↔س لا يجتمعان في طريق مصري موقع لهذا العضو.",
           orbit="العرض الأنفي قد يكون عطاسًا، لكن تعيين المصدر والصوت كلاهما غير مكتمل.",
           keywords="العطاس|يعطس|الأنف"),
    R9.gap("aed-v1.0:40840", "غمض", "LAW-GAP",
           "إغلاق العين يطابق غمضها، لكن ꜥ-ẖ-n لا يسوي غ-م-ض بصفوف مصرية موقعة.",
           sound="الدلالة تعين غمض؛ الصوامت الثلاثة لا تملك رصفًا مصريًا كاملًا.",
           orbit="إغماض العين هو shut the eye نفسه، ورجل الصوت مانعة.",
           keywords="غمض|أغمض|العين"),
    R9.gap("aed-v1.0:41400", "عقء", "SOURCE-GAP",
           "AED لا يسمي المسطح المائي ولا نوعه؛ لا يُنتق جذر عربي من موضعه الجغرافي وحده."),
    R9.gap("aed-v1.0:41480", "عقو", "SOURCE-GAP",
           "المسطح المائي السماوي نفسه موسوم بالشك وغير معين؛ لا يصدر مدار عربي من وصف موضعي محتمل."),
    R9.gap("aed-v1.0:44170", "وحد", "LAW-GAP",
           "Sole-one يطابق الواحد دلاليًا، لكن ꜥ-t المصريين لا يسويان ح-d العربيين في جذر وحد بصفين موقعين.",
           sound="w↔و هوية؛ ꜥ↔ح وt↔د هما موضعا المنع.",
           orbit="الوحدانية مباشرة في اللقب، مع بقاء الطريق الصوتي ناقصًا.",
           keywords="واحد|الوحدة|وحده"),
    R9.gap("aed-v1.0:45530", "وبت", "SEMANTIC-GAP",
           "horns/brow/top لا يطابق حواس وبت/وفَت العربية، ولا يُدخل قرن أو جبين من خارج الرسم."),
    R9.gap("aed-v1.0:46590", "ونب", "SOURCE-GAP",
           "جزء العين غير معين حتى في AED؛ لا يمكن اختيار اسم عضو عربي قبل حسم المرجع التشريحي."),
    R9.gap("aed-v1.0:46920", "ونخ", "SOURCE-GAP",
           "المدخل يجمع اللبس وإرخاء الشعر أو الحبل من غير فصل عضو دلالي؛ لا يُنتق مدار عربي واحد من الحزمة."),
    R9.gap("aed-v1.0:47010", "ونز", "SOURCE-GAP",
           "المسطح المائي لا يسمى ولا يوصف إلا بموضعه؛ لا مقابل عربي معينًا يُحكم عليه."),
    R9.gap("aed-v1.0:47480", "ورت", "NAME-ROOT-OPEN",
           "Great-one لقب لعين حورس؛ لا تحليل اشتقاقي منشور يرده إلى مادة عربية ولا يرث معنى العظمة من ترجمة اللقب."),
    R9.gap("aed-v1.0:47510", "ورت", "SOURCE-GAP",
           "كون الاسم مسطحًا مائيًا مقدسًا موسوم بالشك؛ لا يصدر مدار قبل تعيين المرجع."),
    R9.gap("aed-v1.0:48460", "وحم", "SEMANTIC-GAP",
           "tongue المفسرة مصريًا بـ repeater لا تطابق حواس وحم العربية، ولا تُدخل لسان من خارج الرسم."),
    R9.gap("aed-v1.0:48470", "وحم", "SEMANTIC-GAP",
           "bull's leg بوصفه جزء أثاث لا يطابق حواس وحم العربية، ولا يرث معنى tongue المتجانس."),
    R9.gap("aed-v1.0:48670", "وحء", "SOURCE-GAP",
           "المرض الجلدي لا يتجاوز اقتراح rash؛ لا يُنتق مرض عربي قبل حسم التشخيص."),
    R9.gap("aed-v1.0:50140", "حشو", "LAW-GAP",
           "علاج السن بمعنى حشوه يطابق حشو السن، لكن w-š-ꜣ لا يسوي ح-ش-و بطريق مصري كامل.",
           sound="š↔ش هوية؛ w↔ح وꜣ↔و غير موقعين لهذا العضو.",
           orbit="حشو السن هو tooth filling نفسه، والصوت يمنع الحكم.",
           keywords="حشا|حشو|السن|ملأ"),
    R9.gap("aed-v1.0:50550", "وشم", "SEMANTIC-GAP",
           "throat لا يطابق حواس وشم/وسم العربية، ولا يُدخل حلق أو بلعوم من خارج الرسم."),
    R9.gap("aed-v1.0:50560", "وسم", "SOURCE-GAP",
           "قراءة test للقلب نفسها موسومة بالشك؛ لا يرث العضو معنى throat أو awn من متجانسات wšm."),
    R9.gap("aed-v1.0:50600", "وشم", "SEMANTIC-GAP",
           "awn of grain لا يطابق حواس وشم/وسم العربية، ولا يرث test أو throat المتجانسين."),
    R9.gap("aed-v1.0:53120", "بءء", "SEMANTIC-GAP",
           "eye لا يطابق حواس بءء/باء/بار العربية في المروحة، ولا يُدخل بصر من خارج الرسم."),
    R9.gap("aed-v1.0:53180", "باي", "SEMANTIC-GAP",
           "foot-ewer اسم إناء مخصوص لا يطابق حواس باي/بري العربية، ولا تكفي وظيفته لاختيار إبريق عربي."),
    R9.gap("aed-v1.0:54930", "بعن", "SOURCE-GAP",
           "المسطح المائي السماوي غير مسمى ولا موصوف؛ لا يصدر مدار عربي من الإحالة وحدها."),
    R9.gap("aed-v1.0:55370", "ببت", "SEMANTIC-GAP",
           "throat لا يطابق حواس ببت/بب العربية، ولا يُدخل حلق من خارج الرسم."),
    R9.gap("aed-v1.0:55630", "بنو", "SOURCE-GAP",
           "AED يتردد بين الخصر والأرداف؛ لا يُنتق عضو عربي قبل حسم المرجع التشريحي."),
    R9.gap("aed-v1.0:56700", "بهء", "SEMANTIC-GAP",
           "flee/make turn back لا يطابق حواس بهء/بهر/بحر العربية في المروحة المقروءة."),
    R9.gap("aed-v1.0:57520", "بسك", "SEMANTIC-GAP",
           "entrails/heart لا يطابق حواس بسك/بشك/بصك العربية، ولا يرث معنى عضو جسدي من الترجمة وحدها."),
    R9.gap("aed-v1.0:58050", "بجز", "SEMANTIC-GAP",
           "throat لا يطابق حواس بجز/بقس/بغس العربية في المروحة المقروءة."),
    R9.gap("aed-v1.0:58240", "بتك", "SOURCE-GAP",
           "sink of the heart مفسر ألمانيًا باحتمال الحزن؛ لا يثبت الحدث بما يكفي لاختيار مادة عربية."),
    R9.gap("aed-v1.0:62590", "بشي", "SOURCE-GAP",
           "المرض الجلدي غير مسمى، واقتراح pustule نفسه مشكوك؛ لا يُنتق مرض عربي من الهيكل."),
    R9.gap("aed-v1.0:62800", "فجء", "SOURCE-GAP",
           "AED يوسم العضو قرضًا ساميًا لكنه لا يحسم الشيء بين chest وأداة ذات قضبان ولا يسمي المانح؛ فُصل عن متجانس pgꜣ فعل الفتح."),
    R9.gap("aed-v1.0:63690", "فاك", "SEMANTIC-GAP",
           "man with a shaved head لا يطابق حواس فاك/فلك/فرك العربية، ولا يُدخل أصلع من خارج الرسم."),
    R9.terminal("aed-v1.0:65950", "∅", "OUT-OF-SCOPE",
                "تركيب ظرفي m-tp بمعنى at the head/on top، لا مادة جذرية مفردة منشورة تصلح لحكم النسب."),
    R9.gap("aed-v1.0:66530", "ماع", "SEMANTIC-GAP",
           "temple of the head لا يطابق حواس ماع/مرض/مرغ العربية، ولا يُدخل صدغ من خارج الرسم."),
    R9.gap("aed-v1.0:72060", "مرت", "SEMANTIC-GAP",
           "throat/gullet لا يطابق حواس مرت/مرط/ملت العربية، ولا يرث eye أو chest من متجانسات mr.t."),
    R9.gap("aed-v1.0:72070", "مرت", "SEMANTIC-GAP",
           "eye لا يطابق حواس مرت/مرط/ملت العربية، وفُصل عن throat وchest المتجانسين."),
    R9.gap("aed-v1.0:72090", "مرت", "SEMANTIC-GAP",
           "chest/linen box لا يطابق حواس مرت/مرط/ملت العربية، وفُصل عن eye وthroat المتجانسين."),
    R9.gap("aed-v1.0:73700", "محء", "SEMANTIC-GAP",
           "back of the head لا يطابق حواس محء/محل/محر العربية، ولا يُدخل قفا من خارج الرسم."),
    R9.gap("aed-v1.0:74140", "محس", "SOURCE-GAP",
           "المرض الخارجي في الرأس غير مسمى؛ لا يُنتق تشخيص عربي من موضع الإصابة وحده."),
    R9.gap("aed-v1.0:74540", "ميل", "LAW-GAP",
           "incline one's heart يطابق الميل، لكن m-ẖ-ꜣ لا يسوي م-ي-ل بصفين مصريين موقعين.",
           sound="m↔م هوية؛ ẖ↔ي وꜣ↔ل لا يجتمعان في طريق مصري مكتمل.",
           orbit="ميل القلب هو توجيهه وانعطافه إلى الشيء، والصوت مانع.",
           keywords="مال|يميل|الميل|القلب"),
    R9.gap("aed-v1.0:79930", "نيا", "SOURCE-GAP",
           "المرض الأنفي لا يتجاوز اقتراح head cold/sneezing؛ لا يُنتق جذر عربي قبل حسم التشخيص."),
    R9.gap("aed-v1.0:81180", "نوا", "SOURCE-GAP",
           "adze أداة طقسية مخصوصة ولا يسمي AED نوعها العربي أو طريق نقلها؛ لا تكفي الوظيفة لاختيار قدوم أو فأس."),
    R9.gap("aed-v1.0:81310", "نون", "SEMANTIC-GAP",
           "dishevel the hair in mourning لا يطابق حواس نون العربية، ولا يُدخل شعث من خارج الرسم."),
    R9.gap("aed-v1.0:81760", "نبت", "SEMANTIC-GAP",
           "soft parts of the body لا يطابق حواس نبت/نبط/نب العربية، ولا يُدخل لحم من خارج الرسم."),
    R9.terminal("aed-v1.0:83460", "∅", "OUT-OF-SCOPE",
                "المدخل يصف هيئة علامة هيروغليفية heart with windpipe ولا ينشر معنى معجميًا مستقلًا للفظ nfr في هذا العضو."),
    R9.gap("aed-v1.0:84230", "نمع", "SEMANTIC-GAP",
           "lay out a bed/face a wall لا يطابق حواس نمع/نمض/نمغ العربية، ولا يدمج الفعلين بترجمة حرة."),
    R9.gap("aed-v1.0:93360", "رعم", "SOURCE-GAP",
           "جزء الجسم البشري غير معين؛ لا يُنتق اسم عضو عربي قبل حسم المرجع التشريحي."),
    R9.gap("aed-v1.0:98560", "حنو", "LAW-GAP",
           "box/cavity يطابق المحنية، أي العلبة، لكن h المصري ↔ ح العربية بلا صف مصري موقع.",
           sound="n↔ن وw↔و هويتان؛ h↔ح هو الموضع المانع كما سجلت بطاقة الحسم السابقة.",
           orbit="الصندوق والجوف والعلبة وعاء واحد؛ لا يرث العضو معنى الحنين.",
           keywords="المحنية|العلبة|جلود الإبل"),
    R9.gap("aed-v1.0:104320", "حفد", "SEMANTIC-GAP",
           "open the mouth لا يطابق حواس حفد/حفض/حبد العربية، ولا يُدخل فغر من خارج الرسم."),
    R9.gap("aed-v1.0:105050", "حما", "SEMANTIC-GAP",
           "tread/press out with the feet لا يطابق حواس حما/حمل/حمر العربية في المروحة المقروءة."),
    R9.pos("aed-v1.0:105200", "حمي", "ROOT-TRACE",
           "منعه|دفع عنه|حماه|حماية",
           "ḥ↔ح وm↔م هويتان؛ i̯/j↔ي عبر GLD-02 كما رخصه سجل المرشح.",
           "to drive back/to repel هو حمى الشيء: منعه ودفع عنه.",
           "الجذر الكامل والمعنى المباشر مكتملان؛ الحكم لهذا الفعل وحده ولا ينتقل إلى متجانسات ḥm."),
    R9.gap("aed-v1.0:109640", "حزء", "SOURCE-GAP",
           "حزأ الإبل بمعنى جمعها وساقها شاهد قديم واحد، ولا يثبت turn away/repel في مصدرين مستقلين.",
           sound="ḥ↔ح وz↔ز ظاهران؛ i̯/j المصري ↔ همزة حزأ يحتاج طريقًا فرديًا كذلك.",
           orbit="السوق والرد متجاوران، لكن رجل المصدر العربي والطرف الضعيف ناقصتان.",
           keywords="حزأ|ساقها|جمعها"),
    R9.gap("aed-v1.0:110200", "حصق", "SEMANTIC-GAP",
           "cut off the head/heart لا يثبت في حواس حصق/حسق/حشق العربية المقروءة؛ لا يُدخل حصد من خارج الرسم."),
    R9.gap("aed-v1.0:110230", "حصق", "SEMANTIC-GAP",
           "what is cut off لا يثبت في حواس حصق/حسق/حشق العربية، ولا يرث فعل العضو السابق حكمًا غير صادر."),
    R9.gap("aed-v1.0:111110", "حتي", "SOURCE-GAP",
           "AED لا يعين الفعل المتصل بالفم؛ لا يمكن كتابة مدار قبل تعيين الحدث."),
    R9.gap("aed-v1.0:114010", "خام", "SEMANTIC-GAP",
           "bend the arm/bow down لا يطابق حواس خام/خرم/خلم العربية في المروحة المقروءة."),
    R9.gap("aed-v1.0:114880", "خعم", "SEMANTIC-GAP",
           "throat/neck لا يطابق حواس خعم/خضم/خغم العربية، ولا يُدخل حلق أو عنق من خارج الرسم."),
    R9.gap("aed-v1.0:116140", "خبو", "SOURCE-GAP",
           "مرض العين غير مسمى؛ لا يُنتق تشخيص عربي من موضع الإصابة وحده."),
    R9.gap("aed-v1.0:118790", "خطم", "LAW-GAP",
           "brow/face/front يلتقي مقدم الأنف والفم في خطم، لكن قلب n-t إلى ط-m والمماثلة المقترحة غير موقعين.",
           sound="ḫ↔خ هوية؛ n-t المصريان لا يسويان ط-m العربيين بقاعدة مصرية مجمدة.",
           orbit="الوجه أوسع من مقدم الأنف والفم؛ صلة الجزء بالكل لا تعالج عائق الصوت.",
           keywords="الخطم|مقدم أنفها|فمها"),
    R9.gap("aed-v1.0:118820", "خنت", "SEMANTIC-GAP",
           "head cold/congestion لا يطابق حواس خنت/خنط/خن العربية، ولا يرث face/front من المتجانس."),
    R9.gap("aed-v1.0:119440", "خند", "SEMANTIC-GAP",
           "lower leg/calf لا يطابق حواس خند/خنض العربية، ولا يُدخل ساق من خارج الرسم."),
    R9.gap("aed-v1.0:121720", "ختم", "DIRECTIONAL-TRANSMISSION",
           "sealed chest/storehouse يطابق أثر الختم والجذر كامل، لكن صف الأصل نفسه يرفع احتمال قرض ثقافي ولا يسمي المانح أو الاتجاه.",
           sound="ḫ-t-m ↔ خ-ت-م هوية جذرية كاملة؛ العائق في مصفاة الاتجاه لا في الصوامت.",
           orbit="الصندوق القابل للختم والمخزن المختوم داخل أثر الختم؛ لا يرث العضو متجانس seal حكمًا آليًا.",
           keywords="ختمه|طبعه|التغطية|الاستيثاق"),
    R9.gap("aed-v1.0:123000", "خمص", "SEMANTIC-GAP",
           "bend the back in respect لا يطابق حواس خمص/خمس/حمص العربية مباشرة، ولا يُدخل خنع من خارج الرسم."),
    R9.gap("aed-v1.0:123010", "خمص", "SEMANTIC-GAP",
           "ear of grain لا يطابق حواس خمص/خمس/حمص العربية، ولا يرث فعل الانحناء المتجانس."),
    R9.gap("aed-v1.0:123140", "حنط", "SEMANTIC-GAP",
           "hide/skin/tube لا يطابق حواس حنط/خنط العربية، ولا يُدخل جلد من خارج الرسم."),
    R9.gap("aed-v1.0:123290", "حنو", "SOURCE-GAP",
           "المسطح المائي لا يحسم بين قناة وجدول وبئر؛ لا يرث حنو حكم صندوق hnw ولا يُنتق مقابل قبل التعيين."),
    R9.gap("aed-v1.0:125330", "سطر", "MORPHOLOGY-GAP",
           "s.t-rʾ تركيب place of the mouth/authority؛ لا سند يفصله إلى جذر سطر ولا يفسر الهمزة المصرية الأخيرة.",
           sound="الرسم الرباعي محفوظ؛ انتقاء s-t-r وحده وإسقاط rʾ أو إعادة ترتيبه غير مرخص.",
           orbit="القول والسلطة حزمة مصرية، ولا تسوي معنى السطر العربي بلا تحليل صرفي.",
           keywords="السطر|الخط|كتب"),
    R9.gap("aed-v1.0:129090", "سعح", "SOURCE-GAP",
           "حلية كهنة منف الخاصة غير مسماة المادة أو الهيئة؛ لا يُنتق اسم حلي عربي من الوظيفة الطقسية."),
    R9.gap("aed-v1.0:129600", "صوت", "SOURCE-GAP",
           "العرض المرضي على الإصبع غير معين؛ لا يرث مادة صوت لمجرد وقوعها في المروحة."),
    R9.gap("aed-v1.0:132110", "ساق", "MORPHOLOGY-GAP",
           "leg يطابق الساق، لكن الباء المصرية صامت أصلي بين s وq ولا صرف مسمى يخرجه.",
           sound="s↔س وq↔ق ظاهران؛ b المصري بلا مقابل عربي ولا يجوز إسقاطه.",
           orbit="الساق هي leg نفسها، والبنية الثلاثية المصرية تمنع الحكم.",
           keywords="الساق|الرجل|ما بين الركبة"),
    R9.gap("aed-v1.0:132440", "شفه", "LAW-GAP",
           "lip هي الشفة نفسها، لكن الجذع المصري s-p يحتاج s↔ش وp↔ف مصريين موقعين، وهاء شفه العربية محفوظة.",
           sound="تاء sp.t مؤنثة مسماة؛ بقي s-p، وصفا SIB-01 وLAB-07 ساميا النطاق لا يوقعان هذا العضو المصري.",
           orbit="الشفة مباشرة؛ edge/bank لا يرثان الحكم، وهاء العربية لا تسقط.",
           keywords="الشفة|طبقا الفم|شفهة"),
    R9.gap("aed-v1.0:133080", "زبز", "SEMANTIC-GAP",
           "tie up by the hair لا يطابق حواس زبز/زفس/سفس العربية، ولا يُدخل ضفر من خارج الرسم."),
    R9.gap("aed-v1.0:134360", "سما", "SEMANTIC-GAP",
           "scalp/temple لا يطابق حواس سما/سمر/شمر العربية، ولا يُدخل صدغ من خارج الرسم."),
    R9.gap("aed-v1.0:135850", "سمع", "LAW-GAP",
           "listener/ear يطابق السمع، لكن t المصرية أصلية في s-m-t ولا صف t↔ع مصريًا موقعًا.",
           sound="s↔س وm↔م هويتان؛ t↔ع هو الموضع المانع، ولا نزول إلى s-m مع قيام الثلاثي.",
           orbit="السامع والأذن والسمع مدار مباشر؛ تمام الدلالة لا يجيز إسقاط الصامت الثالث.",
           keywords="السمع|الأذن|سمعت"),
    R9.gap("aed-v1.0:137250", "نزف", "LAW-GAP",
           "blood يلتقي نزف الدم، لكن z-n-f المصري يحتاج قلبًا مكانيًا إلى n-z-f بلا شاهد لاحق للكلمة نفسها أو صف قلب موقع.",
           sound="n وz وf محفوظة، وترتيب الأولين معكوس؛ القلب المكاني غير مرخص فرديًا لهذا العضو.",
           orbit="الدم والمادة النازفة مدار مباشر، وبقي ترتيب الصوامت مانعًا.",
           keywords="نزف|الدم|سال"),
    R9.gap("aed-v1.0:138370", "سنك", "SEMANTIC-GAP",
           "tongue لا يطابق حواس سنك/شنك/صنك العربية، ولا يُدخل لسان أو حنك من خارج الرسم."),
    R9.gap("aed-v1.0:139060", "سلط", "MORPHOLOGY-GAP",
           "body of magistrates يقترب من هيئة أصحاب السلطة، لكن t في sr.t نهاية منقوطة؛ لا يجوز جعلها طاء جذرية لإكمال سلط.",
           sound="بعد حفظ التعرية يبقى جذع s-r؛ s↔س وr↔ل ممكنان، أما طاء سلط العربية فلا صامت جذري مصري يحملها.",
           orbit="هيئة القضاة وأصحاب السلطان مدار مؤسسي مباشر، والبنية تمنع الحكم.",
           keywords="سلطان|سلطة|القهر|تسلط"),
    R9.gap("aed-v1.0:139790", "سرق", "SOURCE-GAP",
           "المسطح المائي غير مسمى ولا موصوف؛ لا يطابق مادة سرق/شرق من مجرد الهيكل."),
    R9.gap("aed-v1.0:142470", "سخن", "SOURCE-GAP",
           "AED يجمع جزءًا مجهولًا من ذبيحة مع swelling طبيًا، والألمانية لا تثبت التورم؛ لا يصدر مدار قبل فصل الحسَّين."),
    R9.gap("aed-v1.0:142980", "سخس", "SEMANTIC-GAP",
           "tear out/pull up لا يطابق حواس زخز/سخس العربية، ولا يُدخل نتف أو قلع من خارج الرسم."),
    R9.gap("aed-v1.0:144200", "سست", "SEMANTIC-GAP",
           "calf/ankle لا يطابق حواس سست/سشط/صصط العربية، ولا يُدخل ساق من خارج الرسم."),
    R9.gap("aed-v1.0:146790", "شمط", "LAW-GAP",
           "balding/greying يطابق الشمط في الشعر، لكن s-k-m لا يسوي ش-m-ط بطريق مصري كامل.",
           sound="s↔ش باب صفير محتمل؛ k↔م وm↔ط غير موقعين، ولا يجيز المعنى قلبهما.",
           orbit="الشيب والشمط هما greying of hair؛ رجل الصوت مانعة.",
           keywords="شمط|الشيب|الشعر"),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT


def round14_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R12.round12_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND12-COMPLETION", "ROUND14-COMPLETION")
    card = card.replace(
        f"round12-egyptian-rank={rank}/{CARD_COUNT}",
        f"round14-egyptian-rank={rank}/{CARD_COUNT}",
    )
    return card


def render_appendices() -> tuple[str, str, dict]:
    aramaic_text = ARAMAIC.read_text(encoding="utf-8")
    egyptian_text = EGYPTIAN.read_text(encoding="utf-8")
    report_text = REPORT.read_text(encoding="utf-8")
    if MARKER in egyptian_text or MARKER in report_text:
        raise SystemExit("Round-fourteen marker already exists; append refused.")

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
        round14_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الرابعة عشرة: استمرار المخزون المصري المسجل المفتوح (2026-08-17)", "",
        ("أُعيد فحص الآرامية أولًا فكان الطابور القصير الحي ذا المروحة غير الفارغة صفرًا. "
         f"لذلك سُجل الانتقال المسمى `{TRANSITION}`. انتُقيت البطاقات المصرية التالية "
         "بدءًا من `WO-C-OPEN-COMP-00526` بقصر الهيكل ثم موضع اللقطة. استُبعد صف ḏ "
         "المؤجل. في كل بطاقة عُرضت إصابات AED كلها بلا حد، وكُتب وسم الطريق والرسم "
         "والمدخل المختار، وحُفظ الاختلاف والمتجانسات بلا محو."), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-00526 إلى WO-C-OPEN-COMP-00565", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-00566 إلى WO-C-OPEN-COMP-00605", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([f"<!-- LANE-C-R14-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    state_counts = dict(sorted(collections.Counter(item.state for item in DECISIONS).items()))
    verdict_counts = dict(sorted(collections.Counter(item.verdict for item in DECISIONS).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة الرابعة عشرة: المسار C (2026-08-17)", "",
        "- أُعيد فحص الآرامية أولًا: المفتوح القصير الحي ذو المروحة غير الفارغة=0؛ لم تُكرر بطاقة آرامية.",
        f"- سُجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل.",
        "- كُتبت الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00526` إلى `WO-C-OPEN-COMP-00565`.",
        "- كُتبت الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00566` إلى `WO-C-OPEN-COMP-00605`.",
        "- طُبقت قواعد AED الثلاث: كل الإصابات بلا حد؛ وسم الطريق والرسم والمدخل المختار مكتوبة؛ الاختلاف والمتجانسات محفوظة بلا محو.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(state_counts, ensure_ascii=False, sort_keys=True)}؛ لا فجوة حُولت إلى نفي.",
        f"- الأحكام: {json.dumps(verdict_counts, ensure_ascii=False, sort_keys=True)}؛ الموجب الوحيد `ḥmi̯↔حمي` مقصور على معنى الرد والمنع في العضو المختار.",
        "- المطابقات الدلالية ذات الرجل الناقصة بقيت مفتوحة باسمها، ومنها `wšꜣ↔حشو` و`sp.t↔شفه` للصوت، و`sbq↔ساق` و`sr.t↔سلط` للبنية، و`ḫtm↔ختم` للاتجاه.",
        "- صف ḏ مؤجل بقرار المؤلف؛ استُبعد من الانتقاء وبقيت بطاقاته على حالها.",
        "- لا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE14 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
