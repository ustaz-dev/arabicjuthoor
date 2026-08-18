#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 20 completion cards without shipping.

The short live-open Aramaic queue remains exhausted, so this append-only
round records the continued transition to the registered Egyptian queue and
completes two forty-card batches from WO-C-OPEN-COMP-01006.  AED is read
without a hit limit, the deferred Egyptian ḏ row remains excluded, and no
git, publication, or shipping command is run.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import unicodedata

import harvest_lane_c_round19 as R19


R9 = R19.R9
R10 = R19.R10
AR = R19.AR
ROOT = R19.ROOT
ARAMAIC = R19.ARAMAIC
EGYPTIAN = R19.EGYPTIAN
REPORT = R19.REPORT
MARKER = "LANE-C-ROUND20-2026-08-18"
FIRST_SERIAL = 1006
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)


# Every decision is scoped to the selected AED member.  The three positive
# judgments use full named/identity sound legs, a frozen event, two Arabic
# witnesses, and a handwritten orbit.  Direct semantic pairs whose Egyptian
# sound leg is not signed remain LAW-GAP; an uncertain AED gloss remains a
# SOURCE-GAP.  Homographs never lend meanings to the selected member.
DECISIONS: tuple[R9.Decision, ...] = (
    R9.gap("aed-v1.0:127110", "ساخ", "SEMANTIC-GAP",
           "glorify/make excellent لا يطابق ساخ بمعنى غاص أو لان، ولا يُدخل المجد من خارج المروحة."),
    R9.gap("aed-v1.0:127330", "سوق", "LAW-GAP",
           "pull together يلتقي سوق الشيء وجمعه في الحركة، لكن s-ꜣ-q لا يسوي s-w-q بصف مصري موقع للموضع الأوسط.",
           sound="s↔س وq↔ق هويتان؛ ꜣ↔و بلا صف مصري موقع.",
           orbit="جر الشيء وجمعه في حركة السوق مدار مباشر؛ معنى الحذر في العضو لا يرثه.",
           keywords="ساق|يسوق|سوق|جمع"),
    R9.gap("aed-v1.0:127560", "سلط", "SEMANTIC-GAP",
           "be dislocated لا يطابق حواس سلط العربية، ولا يُسوّى الخلع الطبي بالتسلط."),
    R9.gap("aed-v1.0:127610", "زفت", "SEMANTIC-GAP",
           "pour out/make a libation لا يطابق الزفت أو حواس زفت العربية، ولا يُدخل سفح من خارج الرسم."),
    R9.gap("aed-v1.0:128370", "سين", "SEMANTIC-GAP",
           "run/hurry/bring quickly لا يطابق اسم السين أو حواس سين العربية، ولا يُدخل السعي من خارج الرسم."),
    R9.gap("aed-v1.0:128710", "سعا", "SEMANTIC-GAP",
           "be in travail أو tremble لا يطابق حواس سعا/سعى مباشرة، ولا تُسوّى الولادة بالسعي."),
    R9.gap("aed-v1.0:128980", "سعر", "SEMANTIC-GAP",
           "make ascend لا يطابق تسعير النار أو السعر نفسه، ولا يُدخل صعد من خارج المروحة."),
    R9.gap("aed-v1.0:129110", "سعح", "SEMANTIC-GAP",
           "ennoble/be noble لا يطابق حواس سعح وبقية المروحة، ولا يُدخل الشرف من خارج الرسم."),
    R9.gap("aed-v1.0:129310", "سعق", "SEMANTIC-GAP",
           "make enter/send in لا يطابق حواس سعق العربية، ولا يُدخل ولج أو أدخل من خارج الرسم."),
    R9.gap("aed-v1.0:129520", "سوء", "LAW-GAP",
           "harmful يلتقي السوء والإساءة، لكن s-w-w لا يسوي س-w-ء في الجذر الكامل بصف مصري موقع للصامت الأخير.",
           sound="s↔س وw↔و هويتان؛ w المصرية الأخيرة ↔ ء العربية بلا صف موقع.",
           orbit="السوء ضرر وقبح، وهو مدار harmful مباشرة؛ بقيت الرجل الصوتية وحدها ناقصة.",
           keywords="السوء|أساء|تسؤ|سيئة|ضرر"),
    R9.gap("aed-v1.0:129730", "زول", "SEMANTIC-GAP",
           "cut down/off أو break لا يطابق الزوال في زول، ولا تُسوّى نتيجة القطع بفعل القطع نفسه."),
    R9.gap("aed-v1.0:130130", "صون", "SEMANTIC-GAP",
           "open يعاكس الصون والحفظ، ولا يُحوّل التضاد إلى مدار."),
    R9.gap("aed-v1.0:130360", "زور", "SEMANTIC-GAP",
           "drink لا يطابق الزور أو الزيارة؛ مرور الشراب بالحلق علاقة عضو بالفعل لا جذرًا واحدًا."),
    R9.gap("aed-v1.0:130430", "سور", "SEMANTIC-GAP",
           "increase/make great لا يطابق السور أو الإحاطة، ولا يُدخل الكثرة من خارج الرسم."),
    R9.gap("aed-v1.0:130750", "سوس", "SEMANTIC-GAP",
           "make into a sphere or ball لا يطابق السوس أو التسويس، ولا يُدخل التكوير من خارج الرسم."),
    R9.gap("aed-v1.0:131460", "سبي", "SEMANTIC-GAP",
           "go/conduct/send/attain أوسع من السبي، ولا يُسوّى حمل الأسير بأعضاء الحركة الأربعة في المدخل."),
    R9.pos("aed-v1.0:131760", "زبن", "ROOT-ECHO",
           "الزبن|دفع|دفعه|صدَم|منع",
           "z↔ز وb↔ب وn↔ن هويات صامتية كاملة في العضو.",
           "إزاحة الشيء عن موضعه أو مساره بالدفع تصل slide away وsteer off بقول العربية زبنه أي دفعه ومنعه.",
           "الحكم ECHO لمدار الإزاحة بالدفع، لا لتسوية كل معنى السقوط أو الملاحة بالدفع العربي."),
    R9.gap("aed-v1.0:132060", "سبش", "SEMANTIC-GAP",
           "make vomit لا يطابق حواس سبش/شبش العربية، ولا يُدخل القيء من خارج الرسم."),
    R9.gap("aed-v1.0:132120", "سبق", "SEMANTIC-GAP",
           "become knowing/be wise لا يطابق السبق، ولا تُسوّى الخبرة بالتقدم."),
    R9.gap("aed-v1.0:132710", "سبي", "SEMANTIC-GAP",
           "remain over/be left لا يطابق السبي، ولا يُدخل بقي من خارج المروحة."),
    R9.gap("aed-v1.0:133150", "سبت", "LAW-GAP",
           "cut up يلتقي السبت بمعنى القطع، لكن p المصرية ↔ ب العربية بلا صف مصري موقع في الجذر الكامل.",
           sound="s↔س وt↔ت هويتان؛ p↔ب هي الرجل غير الموقعة.",
           orbit="القطع والتفريق مدار واحد مباشر؛ لا يرثه معنى السبت الزمني.",
           keywords="السبت|القطع|قطع|سبت"),
    R9.gap("aed-v1.0:133530", "سفا", "SOURCE-GAP",
           "be sluggish موسوم بعلامة شك في الإنجليزية، والألماني يجمع الإهمال والبطء؛ لا يصدر مدار قبل حسم الحس."),
    R9.gap("aed-v1.0:133620", "سفن", "SEMANTIC-GAP",
           "gentle/merciful/make calm لا يطابق السفن أو حواس زفن العربية، ولا تُجمع الرحمة والهدوء في مقابل مفترض."),
    R9.gap("aed-v1.0:133940", "سفت", "SEMANTIC-GAP",
           "slaughter/make a sacrifice لا يطابق حواس سفت/زفت العربية، ولا يُدخل الذبح من خارج الرسم."),
    R9.gap("aed-v1.0:135730", "سنن", "LAW-GAP",
           "old/become old يلتقي أسن الرجل وكبر، لكن s-m-s لا يسوي s-n-n بصفين مصريين موقعين.",
           sound="s الأولى↔س هوية؛ m↔ن وs الأخيرة↔ن بلا صفين مصريين موقعين.",
           orbit="الكبر والهرم مباشران؛ لا يبيحان إسقاط صامت من الثلاثي المصري.",
           keywords="أسن|كبر|الهرم|السن"),
    R9.gap("aed-v1.0:135840", "سمع", "LAW-GAP",
           "hear/overhear يطابق السمع، لكن s-m-t لا يسوي s-m-ꜥ؛ تقابل t↔ع خارج الشبكة النافذة.",
           sound="s↔س وm↔م هويتان؛ t↔ع هو الصف المفقود المسمى في فجوات الشبكة.",
           orbit="السماع والإصغاء مباشران في الطرفين؛ الجذر الثلاثي الكامل يمنع حكم النواة.",
           keywords="السمع|سمعت|يسمع|الأذن"),
    R9.gap("aed-v1.0:137000", "سنب", "SEMANTIC-GAP",
           "burn لا يطابق حواس سنب/شنب/صنب العربية، ولا يُدخل الحرق من خارج الرسم."),
    R9.gap("aed-v1.0:137420", "صنم", "SEMANTIC-GAP",
           "be sad لا يطابق الصنم أو حواس سنم/شنم، ولا يُدخل الحزن من خارج الرسم."),
    R9.gap("aed-v1.0:138350", "سنك", "SEMANTIC-GAP",
           "be dark لا يطابق حواس سنك/شنك/صنك العربية، ولا يُدخل الظلمة من خارج الرسم."),
    R9.gap("aed-v1.0:138530", "زنت", "SEMANTIC-GAP",
           "be hostile لا يطابق حواس زنت/زنط/سنت العربية، ولا يُدخل العداوة من خارج الرسم."),
    R9.gap("aed-v1.0:139380", "سرف", "SEMANTIC-GAP",
           "warm/be warm لا يطابق السرف أو الشرف أو الصلف، ولا يُدخل السخونة من خارج الرسم."),
    R9.gap("aed-v1.0:139410", "سلف", "SEMANTIC-GAP",
           "make rest/to rest لا يطابق السلف أو حواس سرف/صرف، ولا يُدخل الراحة من خارج الرسم."),
    R9.gap("aed-v1.0:139590", "صرح", "LAW-GAP",
           "make known information يطابق التصريح والإظهار، لكن s-r-ḫ لا يسوي ṣ-r-ḥ بصف مصري كامل موقع.",
           sound="r↔ر هوية؛ s↔ص وḫ↔ح لهما صفوف عامة لا توقع هذا العضو المصري كاملًا.",
           orbit="التصريح إظهار ما في النفس وجعله معلومًا؛ complain/accuse أوسع ولا يرث الحكم.",
           keywords="صرح|التصريح|أظهر|مجاهرة|بما في نفسه"),
    R9.gap("aed-v1.0:139770", "شرق", "SEMANTIC-GAP",
           "open/make inhale لا يطابق شرق بالماء أو جهة الشرق، ولا يُسوّى الاختناق بفتح مجرى النفس."),
    R9.gap("aed-v1.0:139920", "سرد", "SEMANTIC-GAP",
           "make grow/to plant لا يطابق السرد والتتابع، ولا يُدخل الزرع من خارج الرسم."),
    R9.gap("aed-v1.0:140090", "شاي", "SEMANTIC-GAP",
           "bring down/make fall لا يطابق حواس شاي/سري وبقية المروحة، ولا يُدخل هوى من خارج الرسم."),
    R9.gap("aed-v1.0:140180", "سلو", "LAW-GAP",
           "make content/satisfy يلتقي سلا عن الشيء وطيب النفس دونه، لكن sh-r-w لا يسوي s-l-w بصف مصري كامل.",
           sound="w↔و هوية وr↔l يرخصه BR-EGYP-01؛ sh المصرية↔س غير موقع لهذا العضو.",
           orbit="الرضا وطيب النفس مدار مباشر؛ لا يورث معنى النسيان وحده.",
           keywords="سلا|السلو|طيب نفس|راض|content"),
    R9.gap("aed-v1.0:142520", "سخن", "SEMANTIC-GAP",
           "go to law/contend لا يطابق السخونة، ولا تُسوّى شدة الخصومة بحرارة مجازية."),
    R9.gap("aed-v1.0:143250", "سخد", "SEMANTIC-GAP",
           "upside down/in disorder لا يطابق حواس سخد/شخض العربية، ولا يُدخل قلب من خارج الرسم."),
    R9.gap("aed-v1.0:143540", "سخم", "SEMANTIC-GAP",
           "hasty/impetuous لا يطابق حواس سخم/سحم/شحم العربية، ولا يُدخل العجلة من خارج الرسم."),
    R9.gap("aed-v1.0:144070", "سزن", "SEMANTIC-GAP",
           "open doors/draw aside لا يطابق حواس سزن/سسن العربية، ولا يُدخل فتح من خارج الرسم."),
    R9.gap("aed-v1.0:144850", "شسب", "SEMANTIC-GAP",
           "bright/make bright لا يطابق حواس شسب/سسب وبقية المروحة، ولا يُدخل الضوء من خارج الرسم."),
    R9.gap("aed-v1.0:146300", "سقد", "SEMANTIC-GAP",
           "make build لا يطابق حواس سقد/شقد/صقد العربية، ولا يُدخل بنى من خارج الرسم."),
    R9.gap("aed-v1.0:146770", "شكم", "SEMANTIC-GAP",
           "make complete لا يطابق الشكيمة أو حواس سكم/صكم، ولا يُدخل التمام من خارج الرسم."),
    R9.gap("aed-v1.0:146800", "سكم", "SEMANTIC-GAP",
           "make dark/blacken لا يطابق حواس سكم/شكم/صكم، ولا يُدخل السواد من خارج الرسم."),
    R9.gap("aed-v1.0:147100", "سجي", "SEMANTIC-GAP",
           "be confused لا يطابق السجية أو السكون في سجى، ولا تُسوّى الحيرة بالشقاء."),
    R9.gap("aed-v1.0:148400", "ستر", "SEMANTIC-GAP",
           "make jewellery لا يطابق الستر أو السطر، ولا يُدخل الحلي من خارج الرسم."),
    R9.gap("aed-v1.0:148500", "سطح", "SEMANTIC-GAP",
           "open a door or bolt لا يطابق السطح، ولا يُدخل فتح من خارج المروحة."),
    R9.gap("aed-v1.0:149770", "سدب", "SEMANTIC-GAP",
           "eat/chew لا يطابق حواس سدب/شدب/صدب العربية، ولا يُدخل الأكل من خارج الرسم."),
    R9.gap("aed-v1.0:149910", "سدح", "LAW-GAP",
           "bring low يطابق سدحه أي صرعه وبطحه، لكن رسم s-dh-ḥ يحتاج صفًا مصريًا موقعًا للصامت الأوسط.",
           sound="s↔س وḥ↔ح ظاهران؛ dh المصرية↔د العربية غير موقعة لهذا العضو.",
           orbit="الصرع والبطح إنزال للجسم إلى الأرض مباشرة؛ لا يرثه معنى الإغراق الأوسع في الألماني.",
           keywords="سدح|صرع|بطح|ألقاه|الأرض"),
    R9.gap("aed-v1.0:151770", "شام", "SEMANTIC-GAP",
           "hot/burn لا يطابق شام أو حواس شأم/سلم/شرم العربية، ولا يُدخل الحمى من خارج الرسم."),
    R9.gap("aed-v1.0:151900", "شاس", "SEMANTIC-GAP",
           "travel/go/tread on لا يطابق حواس شاس/ساس العربية، ولا يُسوّى التدبير بالسير."),
    R9.gap("aed-v1.0:151950", "شاش", "SEMANTIC-GAP",
           "avoid/go through لا يطابق حواس شاش/شاس العربية، ولا تُجمع المجاوزة والتفادي في مادة مفترضة."),
    R9.gap("aed-v1.0:152420", "شعي", "SEMANTIC-GAP",
           "grainy/sandy لا يطابق حواس شعي/سعي العربية، ولا يُدخل الرمل أو الحبوب من خارج الرسم."),
    R9.gap("aed-v1.0:152600", "سعد", "SEMANTIC-GAP",
           "cut off/down لا يطابق السعد أو حواس شعد العربية، ولا يُدخل القطع من خارج الرسم."),
    R9.gap("aed-v1.0:152670", "شوي", "SEMANTIC-GAP",
           "empty/devoid لا يطابق الشواء أو الشوى، ولا يرث معنى الجفاف من العضو المتجانس التالي."),
    R9.pos("aed-v1.0:152720", "شوي", "ROOT-ECHO",
           "شوى|يشويه|انشوى|الشواء|اللحم",
           "š↔ش وw↔و هويتان؛ i̯/j↔ي عبر GLD-02 كما رخصه سجل المرشح.",
           "الشواء يذهب رطوبة اللحم بالحرارة حتى ينشوي؛ فهو جسر فعل واحد إلى dry/be dry، لا مساواة لكل حواس شوى.",
           "الحكم ECHO لمدار التجفيف الحراري في العضو المختار وحده؛ معنى empty في المتجانس لا يرثه."),
    R9.gap("aed-v1.0:152970", "سوء", "SEMANTIC-GAP",
           "be poor لا يساوي السوء أو الشر؛ الفقر قد يكون سوء حال لكنه ليس معنى الجذر نفسه."),
    R9.gap("aed-v1.0:153970", "شبط", "SEMANTIC-GAP",
           "be angry لا يطابق حواس شبط/شفت/سفت العربية، ولا يُدخل الغضب من خارج الرسم."),
    R9.gap("aed-v1.0:154160", "شفو", "SEMANTIC-GAP",
           "swell/be swollen لا يطابق حواس شفو/سفو العربية، ولا يُدخل الانتفاخ من خارج الرسم."),
    R9.gap("aed-v1.0:154340", "شمي", "SEMANTIC-GAP",
           "go/traverse لا يطابق حواس شمي/سمي العربية، ولا يُدخل المشي من خارج الرسم."),
    R9.gap("aed-v1.0:154710", "شمع", "SEMANTIC-GAP",
           "be slender لا يطابق الشمع أو السمع، ولا يُسوّى شكل الشمعة بصفة النحول."),
    R9.gap("aed-v1.0:154730", "سمع", "SEMANTIC-GAP",
           "make music/sing لا يساوي السمع؛ علاقة المسموع بفعل الأداء لا تثبت جذرًا واحدًا."),
    R9.gap("aed-v1.0:154890", "حمم", "LAW-GAP",
           "hot/become feverish يطابق حمم والحميم والحمى، لكن š-m-m لا يسوي ḥ-m-m؛ š↔ح بلا صف مصري موقع.",
           sound="m↔م والتضعيف هويتان؛ š المصرية↔ح العربية هي الرجل المفقودة.",
           orbit="السخونة والحمى مباشرتان في الطرفين؛ لا يبيحان إسقاط الصامت الأول.",
           keywords="الحميم|الماء الحار|حممت|سخن|الحمى"),
    R9.gap("aed-v1.0:155000", "شمس", "SEMANTIC-GAP",
           "follow/accompany/bring لا يطابق الشمس أو حواس شمس/سمس، ولا يُدخل التبع من خارج الرسم."),
    R9.gap("aed-v1.0:155450", "شني", "SEMANTIC-GAP",
           "round/surround/encircle لا يطابق حواس شني/سني العربية، ولا يُدخل الدور من خارج الرسم."),
    R9.gap("aed-v1.0:156250", "شنش", "SEMANTIC-GAP",
           "smelly/brackish لا يطابق حواس شنش/شنس/سنش العربية، ولا يُدخل النتن من خارج الرسم."),
    R9.gap("aed-v1.0:156570", "شرر", "SEMANTIC-GAP",
           "little/meagre لا يطابق الشرر أو السرر، ولا يُدخل القلة من خارج الرسم."),
    R9.gap("aed-v1.0:156870", "شرس", "SEMANTIC-GAP",
           "quick/rush لا يطابق الشراسة أو حواس شرش/سرس، ولا تُسوّى الحدة بالسرعة."),
    R9.gap("aed-v1.0:157030", "شسء", "SEMANTIC-GAP",
           "wise/skilled/conversant لا يطابق حواس شسء وبقية المروحة، ولا يُدخل الحكمة من خارج الرسم."),
    R9.gap("aed-v1.0:157160", "شسب", "SEMANTIC-GAP",
           "receive/take possession لا يطابق حواس شسب/شسف العربية، ولا يُدخل القبض من خارج الرسم."),
    R9.gap("aed-v1.0:157480", "شسم", "SEMANTIC-GAP",
           "red/inflamed لا يطابق حواس شسم/ششم/شصم العربية، ولا يُدخل الحمرة من خارج الرسم."),
    R9.gap("aed-v1.0:157940", "ستر", "LAW-GAP",
           "secret/hidden يطابق الستر والإخفاء، لكن š-t-ꜣ لا يسوي s-t-r بصف مصري كامل موقع.",
           sound="t↔ت هوية؛ š↔س غير موقع مصريًا، وꜣ↔ر بلا صف لهذا العضو.",
           orbit="الستر إخفاء الشيء عن الظهور، وهو hidden/secret مباشرة؛ mysterious أوسع ولا يرث الحكم.",
           keywords="ستر|أخفاه|غطاه|الاختفاء|مستور"),
    R9.pos("aed-v1.0:158350", "شتم", "ROOT-ECHO",
           "شتم|السب|قبيح الكلام|التساب|المشاتمة",
           "š↔ش وt↔ت وm↔م هويات صامتية كاملة في العضو.",
           "المخاصمة التي يتبادل أهلها قبيح الكلام هي المشاتمة والتساب في العربية؛ مدار سلوكي واحد مباشر.",
           "الحكم ECHO لصفة المشاكسة المتحققة بالمشاتمة، لا لتسوية كل عداوة بفعل الشتم."),
    R9.gap("aed-v1.0:159110", "قاي", "SEMANTIC-GAP",
           "tall/high/loud لا يطابق حواس قاي/قري العربية، ولا تُجمع الصفات الثلاث في مقابل مفترض."),
    R9.gap("aed-v1.0:160170", "قبب", "SEMANTIC-GAP",
           "cool/calm لا يطابق القبة أو حواس قبب العربية، ولا تُسوّى السكينة بالبرودة بلا نص."),
    R9.gap("aed-v1.0:160280", "قبح", "SEMANTIC-GAP",
           "die لا يطابق القبح، ولا تُسوّى نهاية الحياة بقبح الهيئة."),
    R9.gap("aed-v1.0:160890", "قني", "SEMANTIC-GAP",
           "fat/be fat لا يطابق حواس قني/قنء العربية، ولا يُدخل السمن من خارج الرسم."),
    R9.gap("aed-v1.0:161520", "قند", "SEMANTIC-GAP",
           "rage/become angry لا يطابق القند أو حواس قنض، ولا يُدخل الغضب من خارج الرسم."),
    R9.gap("aed-v1.0:162450", "قدد", "SEMANTIC-GAP",
           "sleep لا يطابق القد والقطع أو حواس قضض، ولا يُدخل النوم من خارج الرسم."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT


def round20_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R19.round19_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND19-COMPLETION", "ROUND20-COMPLETION")
    card = card.replace(
        f"round19-egyptian-rank={rank}/{CARD_COUNT}",
        f"round20-egyptian-rank={rank}/{CARD_COUNT}",
    )
    source_note = R9.clean(item.get("etymology"), 70) or "لا بيان أقدم"
    card = card.replace(
        "\n- الخطوة صفر:",
        f"\n- أقدم صورة مستعادة: رسم AED؛ {source_note}.\n- الخطوة صفر:",
        1,
    )
    card = re.sub(
        r"(?m)^(- الخطوة صفر:.*)$",
        r"\1\n- درجة المقارنة: الجذر الكامل أولًا.",
        card,
        count=1,
    )
    card = re.sub(
        r"(?m)^(- مؤشر اليتم:.*)$",
        r"\1؛ إشعاع الأسرة: العضو المختار وحده.",
        card,
        count=1,
    )
    card = card.replace(
        "- ملاحظات: صف ḏ مؤجل بقرار المؤلف ومستبعد من هذا الانتقاء؛ لا تعديل لبطاقاته.",
        "- ملاحظات العدستين: استرداد شامل وتشكيك فاصل للمتجانسات؛ صف ḏ مؤجل.",
        1,
    )
    if decision.verdict in R9.POSITIVE:
        root = AR.normalize_root(decision.candidate)
        root_matches = matches.get(root, [])
        chosen = R9.R8.witnesses(root_matches, decision.keywords)
        assert len(chosen) == 2, (
            f"Positive {decision.member_id} lacks two Arabic witnesses for "
            f"{decision.candidate}"
        )
        witness_text = "؛ ".join(
            f"قال {entry['source_label']}: «"
            f"{R9.R8.excerpt(str(entry.get('definition') or ''), decision.keywords)}»"
            for entry in chosen
        )
        card = re.sub(
            r"(?m)^- مسح المعاني العربية:.*$",
            (f"- مسح المعاني العربية: قُرئت {len(root_matches)} نتيجة للجذر "
             f"`{root}` كاملةً بما يكافئ `--max-chars 0`؛ {witness_text}."),
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
        raise SystemExit("Round-twenty marker already exists; append refused.")

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
        round20_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة العشرون: استمرار المخزون المصري المسجل المفتوح (2026-08-18)", "",
        ("أُعيد فحص الآرامية أولًا فكان الطابور القصير الحي ذا المروحة غير الفارغة صفرًا. "
         f"لذلك سُجل الانتقال المسمى `{TRANSITION}`. انتُقيت البطاقات المصرية التالية "
         "بدءًا من `WO-C-OPEN-COMP-01006` بقصر الهيكل ثم موضع اللقطة. استُبعد صف ḏ "
         "المؤجل. في كل بطاقة عُرضت إصابات AED كلها بلا حد، وكُتب وسم الطريق والرسم "
         "والمدخل المختار، وحُفظ الاختلاف والمتجانسات بلا محو."), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-01006 إلى WO-C-OPEN-COMP-01045", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-01046 إلى WO-C-OPEN-COMP-01085", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([f"<!-- LANE-C-R20-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    state_counts = dict(sorted(collections.Counter(item.state for item in DECISIONS).items()))
    verdict_counts = dict(sorted(collections.Counter(item.verdict for item in DECISIONS).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة العشرون: المسار C (2026-08-18)", "",
        "- أُعيد فحص الساميّات أولًا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تُكرر بطاقة سامية.",
        f"- عند نفاد الساميّات سُجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- كُتبت الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01006` إلى `WO-C-OPEN-COMP-01045`.",
        "- كُتبت الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01046` إلى `WO-C-OPEN-COMP-01085`.",
        "- طُبقت قواعد AED الثلاث: كل الإصابات بلا حد؛ وسم الطريق والرسم والمدخل المختار مكتوبة؛ الاختلاف والمتجانسات محفوظة بلا محو.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(state_counts, ensure_ascii=False, sort_keys=True)}؛ لا فجوة حُولت إلى نفي.",
        f"- الأحكام: {json.dumps(verdict_counts, ensure_ascii=False, sort_keys=True)}؛ الموجبات الثلاثة مقصورة على أعضاء AED المختارة ومداراتها المكتوبة.",
        "- الموجبات: `zbn↔زبن` في الإزاحة بالدفع، و`šwi̯↔شوي` في التجفيف الحراري، و`štm↔شتم` في المخاصمة بالسباب.",
        "- المطابقات الدلالية ذات الرجل الصوتية الناقصة بقيت مفتوحة، ومنها `smt↔سمع` و`šmm↔حمم` و`štꜣ↔ستر` و`sdḥ↔سدح` و`srḫ↔صرح`.",
        "- `sfꜣ` بقي `SOURCE-GAP`: معنى sluggish نفسه موسوم بالشك ولم يُسوَّ بالإهمال أو البطء قسرًا.",
        "- صف ḏ مؤجل بقرار المؤلف؛ استُبعد من الانتقاء وبقيت بطاقاته على حالها.",
        "- لا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE20 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
