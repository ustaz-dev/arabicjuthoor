#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 13 completion cards without shipping.

Round twelve was accepted and consolidated.  This append-only round rechecks
the exhausted short live-open Aramaic queue, records the named transition to
the registered Egyptian queue, and completes two forty-card batches beginning
at WO-C-OPEN-COMP-00446.  AED is read without a hit limit and the deferred
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
MARKER = "LANE-C-ROUND13-2026-08-17"
FIRST_SERIAL = 446
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)


# Decisions remain member-scoped.  Direct semantic matches with an unsigned
# Egyptian sound path or an unaccounted Arabic radical remain named gaps.  The
# two positives are limited respectively to q-d "form" and j-m-n "right";
# adjacent homographs and the other published senses do not inherit them.
DECISIONS: tuple[R9.Decision, ...] = (
    R9.gap("aed-v1.0:152770", "شو", "SEMANTIC-GAP",
           "protection/sunshade لا يطابق حواس شو/سو العربية، ولا يرث sunlight أو need من متجانسات šw."),
    R9.gap("aed-v1.0:153650", "شبب", "LAW-GAP",
           "leap/bound يطابق شَبَّ الفرس حين قمص ورفع يديه، لكن p المصرية ↔ ب العربية بلا صف مصري موقع لهذا العضو.",
           sound="š↔ش ظاهر؛ p↔ب هو الموضع المانع، والحكم النووي لا يصدر من المعنى وحده.",
           orbit="وثوب الفرس وقماصه مدار مباشر، وبقيت رجل الصوت ناقصة.",
           keywords="رفع يديه|نشاط الفرس|قمص|ينزو"),
    R9.gap("aed-v1.0:155180", "شن", "SEMANTIC-GAP",
           "رمز الحماية خلف صورة الملك لا يطابق حواس شن/سن العربية، ولا يرث ring أو ocean من متجانسات šn."),
    R9.gap("aed-v1.0:155250", "شن", "SEMANTIC-GAP",
           "tree العام لا يطابق حواس شن/سن العربية، ولا يُنتق اسم شجرة عربية من الرسم وحده."),
    R9.gap("aed-v1.0:155590", "شن", "SEMANTIC-GAP",
           "crocodile لا يطابق حواس شن/سن العربية، ولا يُدخل تمساح من خارج الرسم."),
    R9.gap("aed-v1.0:158380", "شث", "SEMANTIC-GAP",
           "to clothe لا يطابق حواس شث/شت/شط العربية، ولا يكفي معنى اللباس لإدخال كسا بصوامت أخرى."),
    R9.gap("aed-v1.0:158520", "شد", "SEMANTIC-GAP",
           "mortar اسم آلة لا يطابق حواس شد/شض/سد/سض العربية في المروحة المقروءة."),
    R9.gap("aed-v1.0:160900", "قن", "SEMANTIC-GAP",
           "fat في السياق الطبي لا يطابق حواس قن العربية، ولا يرث strong أو mat من متجانسات qn."),
    R9.gap("aed-v1.0:160980", "قن", "SEMANTIC-GAP",
           "mat لا يطابق حواس قن العربية، وبقيت معاني القوة والنهاية والنبات متجانسات مستقلة."),
    R9.gap("aed-v1.0:162350", "قق", "SOURCE-GAP",
           "الإنجليزية لا تسمي إلا شجرة، والألمانية تقترح الخروع؛ لا يصدر مدار عربي قبل حسم التعيين النباتي."),
    R9.pos("aed-v1.0:162430", "قد", "NUCLEUS-TRACE",
           "القَدُّ|التقطيع|قطع الجلد|شق الثوب",
           "q↔ق وd↔د هويتان؛ الحكم للنواة الثنائية q-d بلا صائتة معادة البناء.",
           "form يطابق القَدَّ والتقطيع الذي يعطي الشيء صورته وقده؛ nature وcharacter لا يرثان الحكم.",
           "الموجب مقصور على معنى الصورة والهيئة في العضو المختار، ولا ينتقل إلى متجانس الفعل أو المحيط.",
           zero="حُفظ الرسم qd كاملًا؛ لم تدخل صائتة ولا صامت زائد في حكم النواة."),
    R9.gap("aed-v1.0:162870", "كا", "SEMANTIC-GAP",
           "ka/spirit/essence مفهوم مصري مخصوص لا يطابق حواس كا/كء العربية، ولا يُرد إلى كيان بلا طريق منشور."),
    R9.gap("aed-v1.0:162930", "كا", "SEMANTIC-GAP",
           "bull لا يطابق حواس كا/كء العربية، ولا يرث spirit أو food أو name من متجانسات kꜣ."),
    R9.gap("aed-v1.0:163760", "كي", "SEMANTIC-GAP",
           "another لا يطابق حواس كي العربية، ولا تُحوّل الأداة العربية إلى صفة معجمية بلا اشتقاق منشور."),
    R9.gap("aed-v1.0:165630", "كك", "SEMANTIC-GAP",
           "tinkling of sistra لا يطابق حواس كك العربية، ولا تكفي محاكاة الصوت لإصدار نسب."),
    R9.gap("aed-v1.0:165920", "كث", "SEMANTIC-GAP",
           "safflower لا يطابق حواس كث/كت/كط العربية، ولا يُدخل العصفر من خارج الرسم."),
    R9.gap("aed-v1.0:166640", "جي", "SOURCE-GAP",
           "نوع الرغيف أو المخبوز غير مسمى في AED؛ لا يُنتق اسم خبز عربي من وصف loaf العام."),
    R9.gap("aed-v1.0:167760", "قر", "LAW-GAP",
           "silence يلتقي قرار قرّ وسكونه، لكن g المصرية ↔ ق العربية بلا صف مصري موقع لهذه البطاقة.",
           sound="r↔ر هوية؛ g↔ق هو الموضع المانع، ولا يرث الاسم حكم متجانس الفعل.",
           orbit="الصمت والسكون مدار مباشر، وبقيت رجل الصوت ناقصة.",
           keywords="سكن|السكون|القرار|استقرار"),
    R9.gap("aed-v1.0:168240", "جس", "SEMANTIC-GAP",
           "to mourn لا يطابق حواس جس/جش/جص أو قس/غس العربية، ولا يُدخل حزن من خارج الرسم."),
    R9.gap("aed-v1.0:168770", "جت", "SOURCE-GAP",
           "نوع الخبز غير مسمى في AED؛ لا يُنتق مقابل عربي لرغيف مجهول النوع."),
    R9.gap("aed-v1.0:168880", "تنور", "MORPHOLOGY-GAP",
           "kiln يقترب من التنور بوصفه فرنًا، لكن النون والراء العربيتين لا يحملهما الرسم tꜣ ولا صرف مصري مسمى.",
           sound="t المصرية لا تكفي لبناء ت-ن-و-ر، وꜣ لا تسوي الصوامت العربية الباقية.",
           orbit="الفرن ومدفأة الفخار مدار وظيفي مباشر، والبنية غير مكتملة.",
           keywords="التنور|الفرن|يخبز"),
    R9.terminal("aed-v1.0:169720", "∅", "OUT-OF-SCOPE",
                "أداة افتتاح جملة بلا تحليل جذري معجمي منشور؛ لا تُعامل جذرًا لمجرد قصر الرسم."),
    R9.gap("aed-v1.0:171740", "تفل", "MORPHOLOGY-GAP",
           "to spit out يطابق تفل العربية دلاليًا، لكن اللام صامت جذري لا يحمله الرسم المصري tf ولا صرف مسمى.",
           sound="t↔ت وf↔ف ظاهران؛ لام تفل بلا مقابل مصري.",
           orbit="البصق والتفل معنى مباشر، وبقيت البنية ناقصة.",
           keywords="تفل|البصاق|الريق|بصق"),
    R9.terminal("aed-v1.0:172720", "∅", "OUT-OF-SCOPE",
                "أداة لاحقة enclitic بلا تحليل جذري معجمي منشور؛ لا تدخل قياس الجذور."),
    R9.gap("aed-v1.0:173120", "تخ", "SEMANTIC-GAP",
           "intoxicating drink لا يطابق حواس تخ/طخ العربية، ولا يُدخل خمر أو سكر من خارج الرسم."),
    R9.gap("aed-v1.0:173950", "ثر", "SEMANTIC-GAP",
           "fledgling/chick لا يطابق حواس ثر/تر/طر العربية، ولا يُدخل فرخ بصوامت غير محمولة."),
    R9.gap("aed-v1.0:176790", "ثخ", "SOURCE-GAP",
           "AED لا يعطي العضو معنى يتجاوز noun/Substantiv؛ لا يمكن كتابة مدار قبل تعيين المعنى."),
    R9.gap("aed-v1.0:176890", "ثز", "SEMANTIC-GAP",
           "support لا يطابق حواس ثز/ثس/تز/تس العربية في المروحة، ولا يُدخل سند من خارج الرسم."),
    R9.gap("aed-v1.0:177440", "ثت", "SEMANTIC-GAP",
           "untie/let loose لا يطابق حواس ثت/تت/تط العربية، ولا يكفي معنى الحل لإدخال حلل بصوامت أخرى."),
    R9.gap("aed-v1.0:177580", "ثث", "SEMANTIC-GAP",
           "sparrow لا يطابق حواس ثث/تث/طط العربية، ولا يُدخل عصفور من خارج الرسم."),
    R9.gap("aed-v1.0:177830", "دي", "SEMANTIC-GAP",
           "here/there لا يطابق حواس دي/ضي العربية الجذرية، ولا يُسوّى بأسماء الإشارة العربية بلا طريق منشور."),
    R9.gap("aed-v1.0:180360", "دح", "SEMANTIC-GAP",
           "lowest part/depth لا يطابق حواس دح/ضح العربية في المروحة المقروءة."),
    R9.gap("aed-v1.0:180620", "دس", "SEMANTIC-GAP",
           "knife لا يطابق حواس دس/دش/دص العربية، ولا يُدخل سكين من خارج الرسم."),
    R9.gap("aed-v1.0:400588", "ءو", "SEMANTIC-GAP",
           "long لا يطابق حواس ءو/او/لو/رو العربية، والطول يحتاج بنية غير موجودة في ꜣw."),
    R9.gap("aed-v1.0:450187", "رش", "NAME-ROOT-OPEN",
           "ra-she اسم مؤسسة اقتصادية وعنصر في أسماء الأوقاف؛ لا تحليل اشتقاقي منشور يرده إلى جذر عربي."),
    R9.gap("aed-v1.0:450627", "بر", "SEMANTIC-GAP",
           "square on a game board لا يطابق حواس بر/بل/فر/فل العربية، ولا يُدخل مربع بصوامت زائدة."),
    R9.gap("aed-v1.0:500202", "يس", "SEMANTIC-GAP",
           "to summon لا يطابق حواس يس/يش/يص العربية، ولا يُدخل نادى أو دعا من خارج الرسم."),
    R9.gap("aed-v1.0:550122", "قن", "SEMANTIC-GAP",
           "strong/brave/capable لا يطابق حواس قن العربية، ولا يرث warrior أو lion من متجانسات qn."),
    R9.gap("aed-v1.0:600057", "يش", "SOURCE-GAP",
           "نوع الطعام غير مسمى في AED؛ لا يُنتق مقابل عربي من تعريف food العام."),
    R9.gap("aed-v1.0:600209", "شو", "SEMANTIC-GAP",
           "need/lack لا يطابق حواس شو/سو العربية، ولا يرث needy man أو dryness من متجانسات šw."),
    R9.gap("aed-v1.0:600609", "حبس", "MORPHOLOGY-GAP",
           "closed with a string يلتقي الحبس والإمساك، لكن الباء صامت جذري لا يحمله الرسم ḥs ولا صرف مصري مسمى.",
           sound="ḥ↔ح وs↔س ظاهران؛ باء حبس بلا مقابل مصري.",
           orbit="الإغلاق والمنع مدار مباشر، وبقيت البنية ناقصة.",
           keywords="الحبس|المنع|الإمساك|ضد التخلية"),
    R9.gap("aed-v1.0:800062", "عي", "SEMANTIC-GAP",
           "to have a right to لا يطابق حواس عي/ضي/غي العربية، ولا يُدخل حق بصوامت غير محمولة."),
    R9.gap("aed-v1.0:850478", "بز", "SEMANTIC-GAP",
           "secret image/cult statue لا يطابق حواس بز/بس العربية، ولا يرث secret/initiation من عضو آخر."),
    R9.terminal("aed-v1.0:850795", "∅", "OUT-OF-SCOPE",
                "حرف جر بمعنى with بلا تحليل جذري معجمي منشور؛ لا يدخل قياس الجذور."),
    R9.gap("aed-v1.0:852792", "سك", "SOURCE-GAP",
           "الإنجليزية تسمي روحًا لا تبلى، والألمانية تسمي الفناء؛ حُفظ الاختلاف ولا يصدر حكم قبل حسمه."),
    R9.gap("aed-v1.0:853498", "مع", "SOURCE-GAP",
           "النبات المتسلق نفسه مشكوك وغير مسمى؛ لا يُنتق نبات عربي من وصف creeper العام."),
    R9.gap("aed-v1.0:857648", "رو", "SEMANTIC-GAP",
           "straw لا يطابق حواس رو/لو العربية، ولا يُدخل تبن أو قش من خارج الرسم."),
    R9.gap("aed-v1.0:858493", "جش", "SOURCE-GAP",
           "AED لا يحسم بين رغوة الجعة ورواسبها؛ لا يُنتق مقابل عربي قبل تعيين الشيء."),
    R9.gap("aed-v1.0:859951", "تخ", "SEMANTIC-GAP",
           "drunkenness لا يطابق حواس تخ/طخ العربية، ولا يرث intoxicating drink المتجانس حكمًا غير صادر."),
    R9.gap("aed-v1.0:860534", "وطن", "MORPHOLOGY-GAP",
           "district/region يقترب من الوطن والناحية، لكن النون العربية لا يحملها الرسم w.t ولا صرف مصري مسمى.",
           sound="w↔و ظاهر؛ التاء/الطاء قابلة للفحص، لكن نون وطن بلا مقابل مصري.",
           orbit="الحيز الإقليمي والوطن جوار مباشر، والبنية غير مكتملة.",
           keywords="الوطن|المنزل|المقام|البلد"),
    R9.gap("aed-v1.0:862886", "يح", "SEMANTIC-GAP",
           "crocodile لا يطابق حواس يح/ءح العربية، ولا يُدخل تمساح من خارج الرسم."),
    R9.gap("aed-v1.0:863861", "سو", "SEMANTIC-GAP",
           "مقدار 1/16 من الأرورة لا يطابق حواس سو/شو/صو العربية، ولا يُنشأ اسم كيل بلا شاهد."),
    R9.gap("aed-v1.0:221", "ءخت", "SEMANTIC-GAP",
           "eye of a god لا يطابق حواس ءخت/اخت العربية، ولا يرث حكم ꜥn eye المختلف في الرسم."),
    R9.gap("aed-v1.0:352", "ءدت", "SOURCE-GAP",
           "تعيين مرض العين pterygium محاط بعلامة الشك؛ لا يصدر مدار من تشخيص غير مستقر."),
    R9.gap("aed-v1.0:20090", "يءت", "SEMANTIC-GAP",
           "spine/back لا يطابق حواس يءت/يات/يرت العربية، ولا يُدخل ظهر من خارج الرسم."),
    R9.gap("aed-v1.0:22360", "يوع", "SOURCE-GAP",
           "AED يتردد بين لحم على العظم والفخذ؛ لا يُنتق عضو عربي قبل حسم التعيين."),
    R9.gap("aed-v1.0:22520", "يوف", "SEMANTIC-GAP",
           "flesh/meat لا يطابق حواس يوف/ءوف العربية، ولا يُسوّى بجوف مع اختلاف الرسم والمعنى."),
    R9.gap("aed-v1.0:23830", "يبح", "SEMANTIC-GAP",
           "tooth لا يطابق حواس يبح/ءبح العربية، ولا يُدخل سن من خارج الرسم."),
    R9.gap("aed-v1.0:23840", "يبح", "SEMANTIC-GAP",
           "to laugh by baring the teeth لا يطابق حواس يبح/ءبح العربية، ولا يرث معنى tooth حكمًا مستقلًا."),
    R9.gap("aed-v1.0:23850", "يبح", "SEMANTIC-GAP",
           "be suffused with blood/stream with liquid لا يطابق حواس يبح/ءبح العربية، وفُصل عن tooth وlaugh."),
    R9.pos("aed-v1.0:26080", "يمن", "ROOT-TRACE",
           "اليمين|خلاف اليسار|الجارحة|اليمنى",
           "j↔ي عبر GLD-02 كما رخصه سجل المرشح؛ m↔م وn↔ن هويتان.",
           "right hand هي اليمين والجارحة اليمنى نفسها؛ western معنى مصري اتجاهي لا يرث الحكم.",
           "الجذر الكامل ومعنى اليمين المباشر مكتملان، والحكم مقصور على هذا الحس في العضو المختار."),
    R9.gap("aed-v1.0:27380", "ينف", "SOURCE-GAP",
           "AED يتردد في discharge of the divine eye بين إفراز وبخور؛ لا يُنتق معنى عربي قبل حسم الشيء."),
    R9.gap("aed-v1.0:27420", "ينم", "SEMANTIC-GAP",
           "skin/hide/skin color لا يطابق حواس ينم/ءنم العربية، ولا يُدخل أدم بصوامت غير محمولة."),
    R9.gap("aed-v1.0:27800", "ينس", "SEMANTIC-GAP",
           "red blood لا يطابق حواس ينس/ينش/ينص العربية، ولا يُدخل حمرة من خارج الرسم."),
    R9.gap("aed-v1.0:28250", "يرت", "SEMANTIC-GAP",
           "eye لا يطابق حواس يرت/يلت/ءرت العربية، ولا يرث حكم ꜥn eye المختلف في الرسم."),
    R9.gap("aed-v1.0:28290", "يرت", "SEMANTIC-GAP",
           "عين الإله أو السماء بوصفها الشمس والقمر لا تطابق حواس يرت/يلت العربية، ولا ترث متجانس العين البشرية."),
    R9.gap("aed-v1.0:29550", "يرو", "SEMANTIC-GAP",
           "eye witness لا يطابق حواس يرو/يلو/ءرو العربية، ولا يُدخل شاهد أو رأى من خارج الرسم."),
    R9.gap("aed-v1.0:31090", "يزت", "SOURCE-GAP",
           "تعيين windpipe أو throat نفسه مشكوك؛ لا يُنتق عضو عربي قبل حسم المرجع التشريحي."),
    R9.gap("aed-v1.0:31730", "يسق", "SEMANTIC-GAP",
           "linger/wait/hold back لا يطابق حواس يسق/يشق/يصق العربية في المروحة المقروءة."),
    R9.gap("aed-v1.0:32630", "يكن", "SOURCE-GAP",
           "AED لا يسمي الصفة السلبية المنسوبة إلى القلب واللسان؛ لا يمكن كتابة مدار قبل تعيينها."),
    R9.gap("aed-v1.0:34070", "أذن", "LAW-GAP",
           "ear يطابق الأذن مباشرة، لكن j المصرية ↔ همزة العربية وd المصرية ↔ ذ العربية لا يجتمعان في مسار مصري موقع.",
           sound="n↔ن هوية؛ الموضعان j↔ء وd↔ذ غير موقعين للمصرية في هذه البطاقة.",
           orbit="الأذن هي ear بعينه، ورجل الصوت مانعة.",
           keywords="الأذن|السمع|أذن"),
    R9.gap("aed-v1.0:34190", "يدر", "SEMANTIC-GAP",
           "heart لا يطابق حواس يدر/يدل/يضر العربية، ولا يُدخل قلب أو فؤاد من خارج الرسم."),
    R9.gap("aed-v1.0:34590", "عوي", "SEMANTIC-GAP",
           "hand-shaped clappers لا يطابق حواس عوي/ضوي/غوي العربية، وشكل اليد لا ينشئ مادة يد."),
    R9.gap("aed-v1.0:35190", "عءع", "SOURCE-GAP",
           "عرض المرض وصلته بسقوط الشعر كلاهما مشكوك؛ لا يصدر مدار طبي من وصف غير مستقر."),
    R9.gap("aed-v1.0:35630", "عين", "SEMANTIC-GAP",
           "to face with limestone لا يطابق حواس عين العربية، ولا يكفي انتظام الرسم ꜥ-j-n لإصدار مدار التكسية."),
    R9.gap("aed-v1.0:35750", "روع", "MORPHOLOGY-GAP",
           "be fearful/flutter of the heart يطابق الروع دلاليًا، لكن الراء العربية لا يحملها الرسم ꜥꜥw وتكرار العين المصري بلا مقابل مسمى.",
           sound="w↔و ظاهر؛ بناء ر-و-ع من ꜥ-ꜥ-w غير مكتمل.",
           orbit="الخوف واضطراب القلب مدار مباشر، وبقيت البنية مانعة.",
           keywords="الروع|الخوف|الفزع|القلب"),
    R9.gap("aed-v1.0:36430", "عبت", "SOURCE-GAP",
           "أداة abet الطقسية غير موصوفة الوظيفة أو الهيئة خارج استعمال فتح الفم؛ لا مقابل عربي معينًا يُحكم عليه."),
    R9.gap("aed-v1.0:38040", "عنن", "SEMANTIC-GAP",
           "return/turn back لا يطابق حواس عنن الدالة على العرض والاعتراض، ولا يُدخل رجع من خارج الرسم."),
    R9.gap("aed-v1.0:38260", "عني", "SOURCE-GAP",
           "العضو الجسدي غير معين وموسوم بالشك؛ لا يُنتق اسم عضو عربي من الهيكل وحده."),
    R9.gap("aed-v1.0:38390", "عنب", "SEMANTIC-GAP",
           "close the mouth لا يطابق حواس عنب/ضنب/غنب العربية، ولا يكفي فعل الإغلاق لإصدار جذر."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT


def round13_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R12.round12_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND12-COMPLETION", "ROUND13-COMPLETION")
    card = card.replace(
        f"round12-egyptian-rank={rank}/{CARD_COUNT}",
        f"round13-egyptian-rank={rank}/{CARD_COUNT}",
    )
    return card


def render_appendices() -> tuple[str, str, dict]:
    aramaic_text = ARAMAIC.read_text(encoding="utf-8")
    egyptian_text = EGYPTIAN.read_text(encoding="utf-8")
    report_text = REPORT.read_text(encoding="utf-8")
    if MARKER in egyptian_text or MARKER in report_text:
        raise SystemExit("Round-thirteen marker already exists; append refused.")

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
        round13_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الثالثة عشرة: استمرار المخزون المصري المسجل المفتوح (2026-08-17)", "",
        ("أُعيد فحص الآرامية أولًا فكان الطابور القصير الحي ذا المروحة غير الفارغة صفرًا. "
         f"لذلك سُجل الانتقال المسمى `{TRANSITION}`. انتُقيت البطاقات المصرية التالية "
         "بدءًا من `WO-C-OPEN-COMP-00446` بقصر الهيكل ثم موضع اللقطة. استُبعد صف ḏ "
         "المؤجل. في كل بطاقة عُرضت إصابات AED كلها بلا حد، وكُتب وسم الطريق والرسم "
         "والمدخل المختار، وحُفظ الاختلاف والمتجانسات بلا محو."), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-00446 إلى WO-C-OPEN-COMP-00485", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-00486 إلى WO-C-OPEN-COMP-00525", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([f"<!-- LANE-C-R13-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    state_counts = dict(sorted(collections.Counter(item.state for item in DECISIONS).items()))
    verdict_counts = dict(sorted(collections.Counter(item.verdict for item in DECISIONS).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة الثالثة عشرة: المسار C (2026-08-17)", "",
        "- أُعيد فحص الآرامية أولًا: المفتوح القصير الحي ذو المروحة غير الفارغة=0؛ لم تُكرر بطاقة آرامية.",
        f"- سُجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل.",
        "- كُتبت الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00446` إلى `WO-C-OPEN-COMP-00485`.",
        "- كُتبت الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00486` إلى `WO-C-OPEN-COMP-00525`.",
        "- طُبقت قواعد AED الثلاث: كل الإصابات بلا حد؛ وسم الطريق والرسم والمدخل المختار مكتوبة؛ الاختلاف والمتجانسات محفوظة بلا محو.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(state_counts, ensure_ascii=False, sort_keys=True)}؛ لا فجوة حُولت إلى نفي.",
        f"- الأحكام: {json.dumps(verdict_counts, ensure_ascii=False, sort_keys=True)}؛ الموجبان `qd↔قد` و`jmn↔يمن` مقصوران على معنى الصورة واليمين في العضوين المختارين.",
        "- المطابقات الدلالية ذات الرجل الناقصة بقيت مفتوحة باسمها، ومنها `šp↔شبب` للصوت، و`tf↔تفل` للبنية، و`jdn↔أذن` للمسار المصري الكامل.",
        "- صف ḏ مؤجل بقرار المؤلف؛ استُبعد من الانتقاء وبقيت بطاقاته على حالها.",
        "- لا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE13 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
