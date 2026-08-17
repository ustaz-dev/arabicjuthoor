#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 15 completion cards without shipping.

Round fourteen was accepted and consolidated. This append-only round rechecks
the exhausted short live-open Aramaic queue, records the continued transition
to the registered Egyptian queue, and completes two forty-card batches from
WO-C-OPEN-COMP-00606. AED is read without a hit limit and the deferred
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

import harvest_lane_c_round14 as R14  # noqa: E402


R9 = R14.R9
R10 = R14.R10
AR = R14.AR
ARAMAIC = R14.ARAMAIC
EGYPTIAN = R14.EGYPTIAN
REPORT = R14.REPORT
MARKER = "LANE-C-ROUND15-2026-08-17"
FIRST_SERIAL = 606
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)


# Decisions are member-scoped. Direct translations remain open whenever the
# complete Egyptian-to-Arabic sound path, frozen event, two Arabic witnesses,
# morphology, or named transmission route is missing. The two transparent
# multiword formations are closed only as out of the single-root scope; this
# is not a negative comparative judgment.
DECISIONS: tuple[R9.Decision, ...] = (
    R9.gap("aed-v1.0:147710", "ستي", "SEMANTIC-GAP",
           "leg of Osiris لا يطابق حواس ستي/سطي العربية، ولا يُدخل ساق من خارج الرسم."),
    R9.gap("aed-v1.0:149840", "صدم", "SEMANTIC-GAP",
           "eye-paint لا يطابق حواس صدم العربية، ولا يُدخل كحل من خارج الرسم."),
    R9.gap("aed-v1.0:151240", "شات", "SEMANTIC-GAP",
           "upper chest لا يطابق حواس شات/شاط العربية، ولا يُدخل صدر من خارج الرسم."),
    R9.gap("aed-v1.0:151250", "شات", "SEMANTIC-GAP",
           "talon أو قدم الطائر الجارح لا يطابق حواس شات/شاط، ولا يرث upper chest المتجانس."),
    R9.gap("aed-v1.0:152840", "شوت", "SEMANTIC-GAP",
           "side of the body لا يطابق حواس شوت/سوت العربية، ولا يُدخل جنب من خارج الرسم."),
    R9.gap("aed-v1.0:152890", "شوت", "SEMANTIC-GAP",
           "empty eye لا يطابق حواس شوت/سوت العربية، ولا يرث side المتجانس."),
    R9.gap("aed-v1.0:155420", "نبر", "SOURCE-GAP",
           "AED يتردد بين شعر مستعار وشعره وضفيرة؛ لا يُنتق مدار عربي قبل حسم الشيء."),
    R9.gap("aed-v1.0:155510", "شن", "SEMANTIC-GAP",
           "hair العام لا يطابق حواس شن العربية، ولا يُدخل شعر من خارج الرسم."),
    R9.gap("aed-v1.0:155740", "شنع", "SEMANTIC-GAP",
           "breast لا يطابق حواس شنع/سنع العربية، ولا يُدخل ثدي من خارج الرسم."),
    R9.gap("aed-v1.0:156610", "شر", "SEMANTIC-GAP",
           "nose/nostril لا يطابق حواس شر/سر العربية، ولا يُدخل أنف من خارج الرسم."),
    R9.gap("aed-v1.0:157910", "شجر", "SOURCE-GAP",
           "المسطح المائي نفسه مشكوك بين ditch وdyke، ووسم القرض السامي لا يسمي المانح؛ لا يصدر مدار شجر."),
    R9.gap("aed-v1.0:158640", "شن", "LAW-GAP",
           "skin/water skin يطابق الشن، أي السقاء الخلق، لكن d المصرية لا تسوي ن العربية وw بلا مقابل عربي.",
           sound="š↔ش ظاهر؛ d↔ن غير موقع، وw المصرية محفوظة بلا صامت عربي يحملها.",
           orbit="السقاء الجلدي هو الشن نفسه؛ رجل الصوت والبنية تمنعان الحكم.",
           keywords="الشن|السقاء|القربة|الجلد"),
    R9.gap("aed-v1.0:159810", "قعح", "SEMANTIC-GAP",
           "bend the hand/arm لا يطابق حواس قعح العربية، ولا يُدخل عطف من خارج الرسم."),
    R9.gap("aed-v1.0:159830", "قعح", "SEMANTIC-GAP",
           "arm/shoulder لا يطابق حواس قعح العربية، ولا يرث فعل الانثناء المتجانس."),
    R9.gap("aed-v1.0:160230", "قبح", "SEMANTIC-GAP",
           "lower leg with foot لا يطابق حواس قبح العربية، ولا يُدخل ساق أو قدم من خارج الرسم."),
    R9.gap("aed-v1.0:160470", "قفن", "SEMANTIC-GAP",
           "bake/clot blood لا يطابق حواس قفن العربية، ولا يُدخل خبز أو جمد من خارج الرسم."),
    R9.gap("aed-v1.0:161020", "قن", "SOURCE-GAP",
           "fat بوصفه عرض مرض عين غير معين المادة أو الهيئة؛ لا يُنتق مقابله العربي."),
    R9.gap("aed-v1.0:166900", "جبر", "SEMANTIC-GAP",
           "arm/upper arm لا يطابق حواس جبر/قبر/غبر العربية، ولا يُدخل عضد من خارج الرسم."),
    R9.gap("aed-v1.0:167200", "جمر", "SEMANTIC-GAP",
           "temple of the head لا يطابق حواس جمر/قمر/غمر العربية، ولا يُدخل صدغ من خارج الرسم."),
    R9.gap("aed-v1.0:167280", "قمح", "SEMANTIC-GAP",
           "eye لا يطابق حواس جمح/قمح/غمح العربية، ولا يُدخل عين من خارج الرسم."),
    R9.gap("aed-v1.0:168350", "قص", "SOURCE-GAP",
           "glut في مشكلة الثدي لا يثبت نوع العرض، والألمانية لا تعيد تعيينه؛ لا يصدر مدار طبي."),
    R9.gap("aed-v1.0:170670", "تبن", "SEMANTIC-GAP",
           "head/top لا يطابق حواس تبن/طبن العربية، ولا يُدخل رأس من خارج الرسم."),
    R9.gap("aed-v1.0:170690", "تبن", "SEMANTIC-GAP",
           "bone marrow لا يطابق حواس تبن/طبن العربية، ولا يرث head المتجانس."),
    R9.gap("aed-v1.0:170920", "تبت", "SEMANTIC-GAP",
           "head as body part لا يطابق حواس تبت/طبت العربية، ولا يُدخل رأس من خارج الرسم."),
    R9.gap("aed-v1.0:172250", "طمم", "LAW-GAP",
           "close the mouth يلتقي طم الفجوة وملأها حتى استوت، لكن t المصرية ↔ ط العربية غير موقع لهذا العضو.",
           sound="m-m↔م-م هويتان؛ t↔ط هو الموضع المانع.",
           orbit="إغلاق الفجوة بالملء يجاور إغلاق الفم، ولا تكفي الدلالة لإكمال الصوت.",
           keywords="طم|ملأ|دفن|سوى"),
    R9.gap("aed-v1.0:172270", "تمم", "SEMANTIC-GAP",
           "wooden chest لا يطابق حواس تمم/طمم العربية، ولا يرث فعل إغلاق الفم المتجانس."),
    R9.gap("aed-v1.0:172310", "طمس", "SEMANTIC-GAP",
           "turn the face toward someone لا يطابق طمس الوجه أو حواس تمس العربية."),
    R9.gap("aed-v1.0:173260", "تخن", "SOURCE-GAP",
           "injury to the eye تعريف عام بلا نوع إصابة أو حدث؛ لا يُنتق مدار عربي من الموضع وحده."),
    R9.gap("aed-v1.0:176230", "ثور", "SEMANTIC-GAP",
           "blood/gore لا يطابق الثوران نفسه في مادة ثور، ولا يُدخل دم من خارج الرسم."),
    R9.gap("aed-v1.0:176820", "طرز", "SEMANTIC-GAP",
           "neck/vessel neck لا يطابق حواس طرز/ترس/ثلس العربية، ولا يُدخل عنق من خارج الرسم."),
    R9.gap("aed-v1.0:176830", "ضرس", "LAW-GAP",
           "tooth يطابق الضرس، لكن ṯ-ꜣ-z لا يسوي ض-r-s بمسار مصري كامل.",
           sound="الدلالة تعين ضرس؛ مواضع ṯ↔ض وꜣ↔ر وz↔س غير مجتمعة في صفوف موقعة.",
           orbit="الضرس سن بعينه؛ اكتمال الدلالة لا يجيز إعادة بناء الصوامت.",
           keywords="الضرس|السن|الطاحن"),
    R9.gap("aed-v1.0:176990", "تست", "SEMANTIC-GAP",
           "chest on legs بوصفه أثاثًا لا يطابق حواس تست/طست العربية، ولا يكفي معنى الصندوق العام."),
    R9.gap("aed-v1.0:177260", "تس", "SOURCE-GAP",
           "AED يجمع تيبس العنق والتراكم الطبي من غير فصل الحس أو العضو؛ لا يصدر مدار واحد."),
    R9.gap("aed-v1.0:181260", "دعس", "LAW-GAP",
           "foot print يطابق الدعس، أي شدة الوطء والأثر، لكن g المصرية ↔ ع العربية بلا صف موقع.",
           sound="d↔د وs↔س هويتان؛ g↔ع هو الموضع المانع.",
           orbit="أثر القدم نتيجة الدعس المباشرة، ورجل الصوت وحدها ناقصة.",
           keywords="الدعس|الوطء|الأثر|القدم"),
    R9.gap("aed-v1.0:450149", "بسش", "SEMANTIC-GAP",
           "سكين الصوان الطقسية ذات ذيل السمكة لا تطابق حواس بسش/بشش العربية، ولا يُدخل سكين من خارج الرسم."),
    R9.terminal("aed-v1.0:600636", "∅", "OUT-OF-SCOPE",
                "Hot-mouth تركيب وصفي من šm وrʾ لا مادة جذرية مفردة منشورة تصلح لحكم النسب."),
    R9.gap("aed-v1.0:850153", "مند", "SOURCE-GAP",
           "الأداة المستعملة في طقس فتح الفم غير مسماة ولا موصوفة الهيئة؛ لا مقابل عربي معينًا."),
    R9.gap("aed-v1.0:850185", "يعو", "SOURCE-GAP",
           "washing والمضمضة والفطور حزمة شعائرية معجمية لا تعين فعلًا جذريًا عربيًا واحدًا."),
    R9.gap("aed-v1.0:850291", "يد", "SEMANTIC-GAP",
           "uterus/womb لا يطابق حواس يد/يض العربية، ولا يُدخل رحم من خارج الرسم."),
    R9.gap("aed-v1.0:850443", "بلع", "SEMANTIC-GAP",
           "throat لا يساوي فعل البلع ولا تحمله صوامت bꜣ.t؛ لا يُصدر التشابه الدلالي وحده حكمًا."),
    R9.gap("aed-v1.0:855517", "حتو", "SEMANTIC-GAP",
           "throat لا يطابق حواس حتو/حطو العربية، ولا يُدخل حلق من خارج الرسم."),
    R9.gap("aed-v1.0:857580", "قلب", "MORPHOLOGY-GAP",
           "belly/womb يجاور باطن الجسد، لكن لام قلب العربية لا يحملها qꜣb ولا صرف مصري مسمى.",
           sound="q↔ق وb↔ب ظاهران؛ اللام العربية بلا مقابل، وꜣ لا يسد موضعها بقانون.",
           orbit="البطن والرحم باطنان حاويان، والبنية تمنع الحكم.",
           keywords="القلب|الباطن|الفؤاد"),
    R9.gap("aed-v1.0:67", "ابو", "LAW-GAP",
           "family تلتقي الأب أصل الأسرة، لكن ꜣ المصرية ↔ همزة أبو والواو العربية لا يكتملان في مسار موقع.",
           sound="b↔ب هوية؛ ꜣ↔ء غير موقع، والواو العربية بلا مقابل بعد حفظ تاء التأنيث المصرية.",
           orbit="الأب عضو أصل في الأسرة، لا الأسرة كلها؛ الصوت وحدود المدار كلاهما محتاجان تثبيتًا.",
           keywords="الأب|الوالد|الأسرة"),
    R9.gap("aed-v1.0:335", "أتي", "SEMANTIC-GAP",
           "mind/rear a child لا يطابق حواس أتى العربية، ولا يُدخل ربى من خارج الرسم."),
    R9.gap("aed-v1.0:20380", "يرو", "SEMANTIC-GAP",
           "old man لا يطابق حواس يرو/ءرو العربية، ولا يُدخل شيخ من خارج الرسم."),
    R9.gap("aed-v1.0:21000", "ياك", "SEMANTIC-GAP",
           "old experienced man لا يطابق حواس ياك/ءاك العربية، ولا يرث old man المتجانس المختلف."),
    R9.gap("aed-v1.0:28070", "يند", "SEMANTIC-GAP",
           "afflicted man لا يطابق حواس يند/ءند العربية، ولا يُدخل مبتلى من خارج الرسم."),
    R9.gap("aed-v1.0:32820", "أتي", "SEMANTIC-GAP",
           "father/grandfather لا يطابق حواس أتي العربية، ولا تكفي الوظيفة القرابية لتغيير الصوامت."),
    R9.gap("aed-v1.0:33780", "يدو", "SEMANTIC-GAP",
           "male child/youth لا يطابق حواس يدو/ءدو العربية، ولا يُدخل ولد من خارج الرسم."),
    R9.gap("aed-v1.0:51120", "وت", "SEMANTIC-GAP",
           "eldest son لا يطابق حواس وت/وط العربية، ولا يُدخل بكر من خارج الرسم."),
    R9.gap("aed-v1.0:55710", "بنب", "SOURCE-GAP",
           "تعيين الرجل بأنه من أرض المر نفسها مشكوك؛ لا يصدر مدار اسم جنس أو نسبة من قراءة غير مستقرة."),
    R9.gap("aed-v1.0:56480", "ضرر", "LAW-GAP",
           "blind man يطابق الضرير، لكن b المصرية ↔ ض العربية بلا صف مصري موقع.",
           sound="r-r↔ر-ر هويتان؛ b↔ض هو الموضع المانع.",
           orbit="الضرير هو الأعمى نفسه؛ رجل الصوت تمنع الحكم.",
           keywords="الضرير|الأعمى|البصر"),
    R9.gap("aed-v1.0:66470", "مرع", "SEMANTIC-GAP",
           "just man لا يطابق حواس مرع/مرض/مرغ العربية، ولا يُدخل عدل من خارج الرسم."),
    R9.gap("aed-v1.0:69040", "موت", "SEMANTIC-GAP",
           "mother لا يطابق مادة موت العربية، ولا يُصدر تقارب الرسم قرابة معجمية."),
    R9.gap("aed-v1.0:70350", "منع", "SEMANTIC-GAP",
           "nurse/rear a child لا يساوي منع أو حماية الجار؛ الرعاية أوسع ولا يثبت المصدر حدث الحجز.",
           sound="m-n-ꜥ↔م-ن-ع منتظم سطحيًا، لكن تمام الصوت لا يعالج عائق المدار.",
           orbit="تربية الطفل قد تتضمن حمايته، لكنها لا تختزل في المنع والحجز.",
           keywords="منع|حماية|الجار"),
    R9.gap("aed-v1.0:73250", "مهر", "SEMANTIC-GAP",
           "suckling/child للإنسان لا يساوي المهر، وهو ولد الفرس؛ تخصيص النوع لا يثبته المصدر.",
           sound="m-h-r↔م-ه-ر هويات صامتية ظاهرة.",
           orbit="الصغير الرضيع والمهر يشتركان في حداثة السن، لكن مدار الإنسان لا يطابق صغير الفرس.",
           keywords="المهر|ولد الفرس|الفلو"),
    R9.gap("aed-v1.0:84560", "نون", "SEMANTIC-GAP",
           "child لا يطابق حواس نون العربية، ولا يُدخل ولد من خارج الرسم."),
    R9.gap("aed-v1.0:87260", "نخن", "SEMANTIC-GAP",
           "be/become a child لا يطابق حواس نخن العربية، ولا يُدخل صغر من خارج الرسم."),
    R9.gap("aed-v1.0:94530", "رمث", "SEMANTIC-GAP",
           "human being/man لا يطابق حواس رمث/رمت العربية، ولا يُدخل إنسان من خارج الرسم."),
    R9.gap("aed-v1.0:98760", "حنو", "SEMANTIC-GAP",
           "associates/family لا يطابق حواس حنو/هنو العربية، ولا يرث صندوق hnw المتجانس."),
    R9.gap("aed-v1.0:101050", "عري", "LAW-GAP",
           "naked man يطابق العري، لكن ḥ-ꜣ-w لا يسوي ع-r-j بطريق مصري كامل.",
           sound="الدلالة تعين عري؛ الصوامت المصرية الثلاثة لا تقابل ع-ر-ي بصفوف موقعة.",
           orbit="العاري هو naked بعينه، واختلال الصوت مانع.",
           keywords="العري|عريان|التجرد"),
    R9.gap("aed-v1.0:102050", "حعا", "SEMANTIC-GAP",
           "child لا يطابق حواس حعا/حضا/حغا العربية، ولا يُدخل ولد من خارج الرسم."),
    R9.gap("aed-v1.0:104730", "حمو", "SEMANTIC-GAP",
           "woman/wife لا تساوي الحمو أو الحماة، وهما قرابة بالمصاهرة لا الزوجة نفسها.",
           sound="ḥ-m↔ح-م نواة ظاهرة؛ تاء المؤنث المصرية والواو العربية لا تتبادلان آليًا.",
           orbit="المصاهرة مدار قرابي مجاور، لكنه لا يطابق المرأة أو الزوجة.",
           keywords="الحمو|الحماة|الزوج"),
    R9.gap("aed-v1.0:110550", "حقر", "SEMANTIC-GAP",
           "hungry man لا يطابق الحقر أو حواس حقل العربية، ولا يُدخل جوع من خارج الرسم."),
    R9.gap("aed-v1.0:115320", "خود", "SEMANTIC-GAP",
           "rich man لا يطابق حواس خود/خوض العربية، ولا يُدخل غني من خارج الرسم."),
    R9.gap("aed-v1.0:117780", "خنو", "SEMANTIC-GAP",
           "child لا يطابق حواس خنو العربية، ولا يُدخل ولد من خارج الرسم."),
    R9.gap("aed-v1.0:124500", "خرد", "LAW-GAP",
           "daughter تلتقي الخريدة، أي البكر والفتاة، لكن ẖ المصرية ↔ خ العربية بلا صف مصري موقع.",
           sound="r↔ر وd↔د هويتان؛ ẖ↔خ هو الموضع المانع.",
           orbit="البنت والخريدة تلتقيان في الفتاة، ولا يساوي ذلك كل بنت بالبكر.",
           keywords="الخريدة|البكر|الجارية|العذراء"),
    R9.gap("aed-v1.0:124510", "خرد", "SEMANTIC-GAP",
           "be a child لا يساوي خردت المرأة بمعنى بقيت بكرًا أو استحيت؛ لا يرث الاسم السابق حكمًا.",
           sound="الرسم ẖ-r-d قريب من خ-ر-د سطحيًا، ولا يعمل مع اختلاف الحدث.",
           orbit="الطفولة والبكارة مرحلتان متجاورتان لا حدث واحدًا.",
           keywords="خردت|البكر|الحياء"),
    R9.gap("aed-v1.0:125630", "ذات", "SEMANTIC-GAP",
           "daughter لا يطابق ذات العربية ولا معنى صاحبة، وتاء التأنيث المصرية لا تنشئ الجذر العربي."),
    R9.terminal("aed-v1.0:126080", "∅", "OUT-OF-SCOPE",
                "zꜣ-z تركيب son of a man ذو مكونين منشورين، لا مادة جذرية مفردة تصلح لحكم النسب."),
    R9.gap("aed-v1.0:126170", "سار", "SEMANTIC-GAP",
           "wise man لا يطابق حواس سار/صار العربية، ولا يُدخل حكيم من خارج الرسم."),
    R9.gap("aed-v1.0:126820", "سار", "SEMANTIC-GAP",
           "needy man لا يطابق حواس سار/صار العربية، ولا يرث wise man المتجانس."),
    R9.gap("aed-v1.0:133600", "صفي", "SEMANTIC-GAP",
           "child/babe/son لا يطابق الصفي المختار أو حواس سفي/شفي، ولا يُدخل ولد من خارج الرسم."),
    R9.gap("aed-v1.0:136260", "صنو", "LAW-GAP",
           "sister تطابق الصنو في معنى الشقيق، لكن s المصرية ↔ ص العربية والواو الجذرية لا يكتملان في مسار واحد.",
           sound="n↔ن هوية؛ s↔ص غير موقع، وتاء المؤنث المصرية لا تحمل واو صنو العربية.",
           orbit="الأخت صنو وشقيقة مباشرة؛ الصوت والبنية وحدهما يمنعان الحكم.",
           keywords="الصنو|الشقيق|الأخ|الأخت"),
    R9.gap("aed-v1.0:137930", "سنخ", "SEMANTIC-GAP",
           "bring up/protect a child لا يطابق حواس سنخ/شنخ/صنخ العربية، ولا يُدخل ربى من خارج الرسم."),
    R9.gap("aed-v1.0:139900", "سري", "DIRECTIONAL-TRANSMISSION",
           "captive woman موسومة قرضًا ساميًا، لكن AED لا يسمي المانح أو طريقه، ولا تكفي السرية العربية لحسم الاتجاه.",
           sound="جذع s-r ظاهر قبل تاء المؤنث؛ الياء العربية الضعيفة ومسار النقل غير مثبتين.",
           orbit="الأسيرة والسرية تلتقيان في المرأة المملوكة، وبقي تعيين المانح والاتجاه لازمًا.",
           keywords="السرية|الأمة|الجارية"),
    R9.gap("aed-v1.0:140420", "نصح", "LAW-GAP",
           "counselor يطابق الناصح، لكن النون العربية بلا مقابل وz↔ص غير موقع في طريق مصري كامل.",
           sound="ḥ↔ح ظاهر؛ الرسم z-ḥ لا يحمل نون نصح ولا يوقع z↔ص.",
           orbit="رجل المشورة هو الناصح نفسه، ورجل الصوت مانعة.",
           keywords="الناصح|النصيحة|المشورة"),
    R9.gap("aed-v1.0:156650", "شري", "SEMANTIC-GAP",
           "child/son/lad لا يطابق حواس شري/سري العربية، ولا يُدخل ولد من خارج الرسم."),
    R9.gap("aed-v1.0:158030", "شتا", "SEMANTIC-GAP",
           "small child لا يطابق حواس شتا/ستا/شطر العربية، ولا يُدخل صغير من خارج الرسم."),
    R9.gap("aed-v1.0:164400", "كم", "SOURCE-GAP",
           "woman's ailment غير مسمى ولا موصوف بعرض؛ لا يُنتق مرض عربي من جنس المصابة وحده."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT


def round15_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R14.round14_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND14-COMPLETION", "ROUND15-COMPLETION")
    card = card.replace(
        f"round14-egyptian-rank={rank}/{CARD_COUNT}",
        f"round15-egyptian-rank={rank}/{CARD_COUNT}",
    )
    return card


def render_appendices() -> tuple[str, str, dict]:
    aramaic_text = ARAMAIC.read_text(encoding="utf-8")
    egyptian_text = EGYPTIAN.read_text(encoding="utf-8")
    report_text = REPORT.read_text(encoding="utf-8")
    if MARKER in egyptian_text or MARKER in report_text:
        raise SystemExit("Round-fifteen marker already exists; append refused.")

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
        round15_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الخامسة عشرة: استمرار المخزون المصري المسجل المفتوح (2026-08-17)", "",
        ("أُعيد فحص الآرامية أولًا فكان الطابور القصير الحي ذا المروحة غير الفارغة صفرًا. "
         f"لذلك سُجل الانتقال المسمى `{TRANSITION}`. انتُقيت البطاقات المصرية التالية "
         "بدءًا من `WO-C-OPEN-COMP-00606` بقصر الهيكل ثم موضع اللقطة. استُبعد صف ḏ "
         "المؤجل. في كل بطاقة عُرضت إصابات AED كلها بلا حد، وكُتب وسم الطريق والرسم "
         "والمدخل المختار، وحُفظ الاختلاف والمتجانسات بلا محو."), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-00606 إلى WO-C-OPEN-COMP-00645", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-00646 إلى WO-C-OPEN-COMP-00685", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([f"<!-- LANE-C-R15-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    state_counts = dict(sorted(collections.Counter(item.state for item in DECISIONS).items()))
    verdict_counts = dict(sorted(collections.Counter(item.verdict for item in DECISIONS).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة الخامسة عشرة: المسار C (2026-08-17)", "",
        "- أُعيد فحص الآرامية أولًا: المفتوح القصير الحي ذو المروحة غير الفارغة=0؛ لم تُكرر بطاقة آرامية.",
        f"- سُجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل.",
        "- كُتبت الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00606` إلى `WO-C-OPEN-COMP-00645`.",
        "- كُتبت الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00646` إلى `WO-C-OPEN-COMP-00685`.",
        "- طُبقت قواعد AED الثلاث: كل الإصابات بلا حد؛ وسم الطريق والرسم والمدخل المختار مكتوبة؛ الاختلاف والمتجانسات محفوظة بلا محو.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(state_counts, ensure_ascii=False, sort_keys=True)}؛ لا فجوة حُولت إلى نفي.",
        f"- الأحكام: {json.dumps(verdict_counts, ensure_ascii=False, sort_keys=True)}؛ لم يصدر حكم موجب، والإغلاقان البنيويان خارج نطاق الجذر المفرد لا ينفيان صلة مقارنة.",
        "- المطابقات الدلالية ذات الرجل الناقصة بقيت مفتوحة باسمها، ومنها `šd.w↔شن` و`dgs↔دعس` و`ẖrd↔خرد` و`sn.t↔صنو` للصوت أو البنية، و`sr.t↔سري` للاتجاه.",
        "- صف ḏ مؤجل بقرار المؤلف؛ استُبعد من الانتقاء وبقيت بطاقاته على حالها.",
        "- لا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE15 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
