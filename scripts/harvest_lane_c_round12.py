#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 12 completion cards.

Round eleven was accepted and consolidated.  This append-only round rechecks
the exhausted short live-open Aramaic queue, records the named transition to
the registered Egyptian queue, and completes two forty-card batches beginning
at WO-C-OPEN-COMP-00366.  AED is read without a hit limit and the deferred
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


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import harvest_lane_c_round9 as R9  # noqa: E402
import harvest_lane_c_round10 as R10  # noqa: E402
import harvest_lane_c_round11 as R11  # noqa: E402
import search_arabic_root_senses as AR  # noqa: E402


ARAMAIC = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
EGYPTIAN = ROOT / "04-cross-linguistic" / "readings" / "egyptian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-C.md"
MARKER = "LANE-C-ROUND12-2026-08-17"
FIRST_SERIAL = 366
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)


# Every decision is scoped to the named AED member.  A gap is a completed
# reading with its missing leg named, not a negative historical claim.  The
# only positive is deliberately nucleus-scoped: Egyptian s-m is compared with
# the productive Arabic nucleus in وسم/سمة, while the Arabic initial w is not
# silently deleted.  Direct lexical temptations whose frozen event or sound
# leg does not work remain open.
DECISIONS: tuple[R9.Decision, ...] = (
    R9.gap("aed-v1.0:52810", "بء", "SOURCE-GAP",
           "stork يعيّن طائرًا، لكن المروحة المقروءة لا تسمي اللقلق أو نوعه في مادة بء، ولا يُنتق اسم طائر من خارج الرسم."),
    R9.gap("aed-v1.0:54120", "بي", "SEMANTIC-GAP",
           "groats/grütze لا يطابق حواس بي العربية، ولا يكفي كونه طعامًا أو حبوبًا لإصدار مدار."),
    R9.gap("aed-v1.0:54760", "بع", "SOURCE-GAP",
           "نوع الحَبّ المصري غير مسمى في AED؛ لا يُنتق محصول عربي بعينه من وصف cereal العام."),
    R9.gap("aed-v1.0:54820", "بع", "SEMANTIC-GAP",
           "refuse/disregard لا يطابق حواس بع العربية، ولا يرث معنى engender أو bathe من متجانسات bꜥ."),
    R9.gap("aed-v1.0:55340", "بب", "SEMANTIC-GAP",
           "collar لا يطابق حواس بب العربية في المروحة المقروءة، ولا يرث معنى tread in المتجانس."),
    R9.gap("aed-v1.0:56370", "بر", "SOURCE-GAP",
           "pellet of pigment نفسه مشكوك وغير معين المادة؛ لا يُبنى مدار عربي على وصف احتمالي لحبيبة صباغ."),
    R9.gap("aed-v1.0:56790", "بح", "SOURCE-GAP",
           "النبات غير مسمى في AED؛ لا يجوز اختيار نبات عربي من الهيكل وحده."),
    R9.gap("aed-v1.0:57170", "بز", "SEMANTIC-GAP",
           "secret/initiation لا يطابق حواس بز العربية، وبقي secret image المتجانس مستقلًا."),
    R9.gap("aed-v1.0:57250", "بس", "SOURCE-GAP",
           "نوع الخبز غير مسمى في AED، ولا مادة بس العربية تعيّن هذا الرغيف بلا اشتقاق منشور."),
    R9.gap("aed-v1.0:58120", "بت", "SOURCE-GAP",
           "قالب صنع تمثال أوزيريس آلة مخصوصة لا يسميها شاهد عربي في مادة بت، ولا يرث معنى الزيت أو الراعي."),
    R9.gap("aed-v1.0:58400", "بد", "SEMANTIC-GAP",
           "natron لا يطابق حواس بد العربية، ولا يُنقل إليه حكم الفعل المصري المجاور purify with natron."),
    R9.gap("aed-v1.0:59500", "بي", "SEMANTIC-GAP",
           "flea لا يطابق حواس بي/في العربية، ولا يُدخل برغوث من خارج الرسم."),
    R9.gap("aed-v1.0:59600", "بع", "SEMANTIC-GAP",
           "spit out/spew sparks لا يطابق حواس بع/فع في المروحة، ولا يُدخل بزق أو تفل بصوامت غير محمولة."),
    R9.gap("aed-v1.0:60220", "برأ", "LAW-GAP",
           "house/temple/tomb/container لا يساوي خلق برأ، كما أن p↔ب لا يملك صفًا مصريًا موقعًا لهذه البطاقة.",
           sound="r↔ر ظاهر؛ p↔ب هو الموضع المانع، والهمزة العربية لا مقابل مصريًا لها.",
           orbit="الخلق والبيت ليسا معنى معجميًا مباشرًا واحدًا؛ بقي الصوت والمعنى معًا غير مكتملين.",
           keywords="خلق|برأ"),
    R9.gap("aed-v1.0:61370", "فح", "SEMANTIC-GAP",
           "reach/attack لا يطابق حواس فح/بح العربية بمدار واحد مباشر."),
    R9.gap("aed-v1.0:63050", "فد", "SOURCE-GAP",
           "decking نفسه موسوم بالشك وموصوف عامة بأنه جزء سفينة؛ لا يُنتق اسم عربي لجزء غير معين."),
    R9.gap("aed-v1.0:64250", "فد", "SOURCE-GAP",
           "الزيت غير مسمى في AED؛ لا يثبت وصف an oil مادة عربية بعينها، وبقي sweat متجانسًا مستقلًا."),
    R9.gap("aed-v1.0:66140", "ما", "SOURCE-GAP",
           "styrax مجرد احتمال والنبات غير معين؛ لا يصدر مدار من تعريف معجمي مشكوك."),
    R9.gap("aed-v1.0:67780", "مي", "SEMANTIC-GAP",
           "صيغة الأمر take لا تطابق حواس مي/مء العربية، ولا ترث معنى bring أو come من متجانسات mj."),
    R9.gap("aed-v1.0:69600", "من", "SEMANTIC-GAP",
           "remaining is/rest balance لا يطابق حواس من العربية في مادة واحدة مباشرة."),
    R9.gap("aed-v1.0:69680", "من", "SOURCE-GAP",
           "المعدن المستورد من سورية غير مسمى؛ لا يمكن اختيار مادة عربية قبل تعيين المنتج."),
    R9.gap("aed-v1.0:71810", "مرض", "MORPHOLOGY-GAP",
           "illness/pain يلتقي مرض العربية دلاليًا، لكن الضاد صامت جذري لا يحمله الرسم المصري mr ولا صرف مسمى.",
           sound="m↔م وr↔ر هويتان؛ الصامت العربي ض بلا مقابل مصري.",
           orbit="المرض والألم مدار مباشر، وبقيت رجل البنية ناقصة.",
           keywords="المرض|الألم|وجع"),
    R9.gap("aed-v1.0:71880", "مر", "SEMANTIC-GAP",
           "bind في السياق الطبي لا يطابق حواس مر العربية، ولا يرث illness أو canal من متجانسات mr."),
    R9.gap("aed-v1.0:73330", "بوع", "LAW-GAP",
           "cubit يلتقي الباع مقياسًا جسديًا، لكن m↔ب وḥ↔ع بلا صفين مصريين موقعين.",
           sound="المقابل ب-و-ع لا يسويه مسار مغلق مع m-ḥ؛ لا يُنتق معنى القياس وحده.",
           orbit="المقياس الجسدي مشترك، ورجل الصوت غائبة.",
           keywords="الباع|مسافة|اليدين"),
    R9.gap("aed-v1.0:74780", "مس", "SEMANTIC-GAP",
           "grain as levy لا يطابق حواس مس/مش/مص العربية، ولا يرث معنى child أو calf من المتجانسات."),
    R9.gap("aed-v1.0:76800", "مك", "SOURCE-GAP",
           "نوع القارب غير مسمى في AED؛ لا يُنتق اسم مركب عربي من وصف boat العام."),
    R9.gap("aed-v1.0:80830", "نو", "SEMANTIC-GAP",
           "hunter/scout لا يطابق حواس نو العربية، ولا يرث معنى hunt أو time أو water من متجانسات nw."),
    R9.gap("aed-v1.0:81660", "نب", "SEMANTIC-GAP",
           "every/all لا يطابق حواس نب العربية، ولا يرث معنى lord أو collar من متحد الرسم."),
    R9.gap("aed-v1.0:83250", "نف", "SEMANTIC-GAP",
           "that which floods/refreshment لا يطابق حواس نف العربية بمدار مباشر، وفُصل عن breath وwrongdoing."),
    R9.gap("aed-v1.0:84040", "نم", "SEMANTIC-GAP",
           "produce of fields offered لا يطابق حواس نم العربية، ولا يرث معنى winery أو steal من المتجانسات."),
    R9.gap("aed-v1.0:84580", "نن", "SEMANTIC-GAP",
           "darkness لا يطابق حواس نن العربية، ولا يرث food أو flood water من بقية nn."),
    R9.gap("aed-v1.0:85020", "نر", "SEMANTIC-GAP",
           "herdsman/protector لا يطابق حواس نر/نل العربية في المروحة."),
    R9.gap("aed-v1.0:85900", "نح", "SOURCE-GAP",
           "تعيين guinea-fowl نفسه مشكوك في الإنجليزية؛ لا يُنتق اسم طائر عربي من الاحتمال."),
    R9.gap("aed-v1.0:86760", "نخو", "SOURCE-GAP",
           "protect/help لا يطابق نخوة بمعنى الكبر والعظمة في المعاجم المقروءة؛ هوية n-ḫ لا تكمل رجل المعنى."),
    R9.gap("aed-v1.0:87710", "نخ", "SOURCE-GAP",
           "الإنجليزية لا تعين السائل الجسدي، والألمانية تقترح البصاق؛ لا يُنتق معنى عربي قبل حسم هذا الاختلاف."),
    R9.gap("aed-v1.0:87810", "نس", "SEMANTIC-GAP",
           "sink in بالقدم في التربة لا يطابق حواس نس/نش/نص العربية، ولا يرث tongue المتجانس."),
    R9.gap("aed-v1.0:88470", "نش", "SEMANTIC-GAP",
           "shudder/tremble لا يطابق حواس نش/نس العربية في المروحة المقروءة."),
    R9.gap("aed-v1.0:92720", "رع", "SEMANTIC-GAP",
           "end/limit لا يطابق حواس رع/رض/رغ أو لع/لض/لغ العربية، ولا يرث state أو place من المتجانسات."),
    R9.gap("aed-v1.0:94700", "رنن", "SOURCE-GAP",
           "name لا يطابق مادة رنن التي تسمي الصوت والرنين؛ هوية r-n وحدها لا تصدر حكمًا."),
    R9.gap("aed-v1.0:97270", "حرا", "LAW-GAP",
           "roast/embers يلتقي حراوة النار دلاليًا، لكن ꜣ المصرية ↔ ر العربية بلا صف موقع، والحدث المجمد لا يسمي الشواء.",
           sound="h↔ح ممكن في GUT-04؛ الراء العربية في حر- بلا مقابل مصري.",
           orbit="الحرارة والشواء جوار مباشر، وبقي الصوت والحدث غير مكتملين.",
           keywords="حرارة|النار|حراوة"),
    R9.terminal("aed-v1.0:97760", "∅", "OUT-OF-SCOPE",
                "اعتراض غير معين بلا تحليل جذري معجمي منشور؛ لا يُعامل جذرًا لمجرد قصر الرسم."),
    R9.gap("aed-v1.0:97910", "هو", "SOURCE-GAP",
           "الزيت غير مسمى؛ لا مادة عربية معينة يحملها تعريف an oil العام."),
    R9.gap("aed-v1.0:98970", "هر", "SOURCE-GAP",
           "AED لا يعطي العضو معنى يتجاوز noun/Substantiv؛ لا يمكن كتابة مدار قبل تعيين المعنى."),
    R9.gap("aed-v1.0:100070", "حا", "SOURCE-GAP",
           "seek نفسه موسوم بعلامة الشك؛ لا يصدر حكم من مدخل غير مستقر."),
    R9.gap("aed-v1.0:100170", "حا", "SOURCE-GAP",
           "necessity/wish/lack حزمة معان موسومة بالشك، فلا يُنتق أحدها لموافقة مادة عربية."),
    R9.gap("aed-v1.0:100970", "خن", "SOURCE-GAP",
           "الإنجليزية تقترح bandage والألمانية أدوات الطبيب؛ لم يتعين الشيء الطبي الذي سيقوم عليه المدار."),
    R9.gap("aed-v1.0:102300", "حو", "NAME-ROOT-OPEN",
           "اسم أبي الهول الكبير في الجيزة تسمية عَلَمية/لقبية؛ لا اشتقاق منشور يرده إلى جذر عربي."),
    R9.gap("aed-v1.0:103990", "حب", "SOURCE-GAP",
           "نوع البطة غير مسمى في AED، ولا تسمح الصورة باختيار اسم عربي لطائر بعينه."),
    R9.gap("aed-v1.0:104680", "حم", "SEMANTIC-GAP",
           "servant/slave لا يطابق حواس حم العربية، ولا يرث majesty أو steer أو tread من متجانسات ḥm."),
    R9.gap("aed-v1.0:105890", "حن", "SEMANTIC-GAP",
           "obstruct/close لا يطابق حواس حن العربية، ولا يرث protect أو command من عضو ḥn آخر."),
    R9.terminal("aed-v1.0:107520", "∅", "OUT-OF-SCOPE",
                "AED لا يسمي إلا الجنس النحوي preposition بلا معنى فردي ولا تحليل جذري؛ لا يرث معنى face المتجانس."),
    R9.gap("aed-v1.0:109250", "حح", "SEMANTIC-GAP",
           "million لا يطابق حواس حح العربية ولا اسم عدد عربيًا في المروحة."),
    R9.gap("aed-v1.0:109700", "حس", "SEMANTIC-GAP",
           "he who is cold لا يطابق حواس حس/حش/حص العربية، ولا يكفي وصف البرودة لإدخال برد من خارج الرسم."),
    R9.gap("aed-v1.0:113100", "خوص", "MORPHOLOGY-GAP",
           "leaf يلتقي الخوص، ورق النخل، لكن السين العربية صامت جذري غير موجود في ḫꜣ ولا في صرف مصري مسمى.",
           sound="ḫ↔خ ممكن، والواو ضعيفة؛ الصامت س بلا مقابل مصري.",
           orbit="الورقة النباتية مدار مباشر، وبقيت البنية ناقصة.",
           keywords="الخوص|ورق|النخل"),
    R9.gap("aed-v1.0:114470", "خي", "SEMANTIC-GAP",
           "height لا يطابق حواس خي العربية، ولا يرث child أو high-lying land من متجانسات ḫy."),
    R9.gap("aed-v1.0:114940", "خو", "SEMANTIC-GAP",
           "protection لا يطابق حواس خو العربية، ولا يرث oneness أو fan من المتجانسات."),
    R9.gap("aed-v1.0:115410", "خب", "SEMANTIC-GAP",
           "annihilate/execute لا يطابق حواس خب العربية، ولا يرث dancer أو diminution من متحد الرسم."),
    R9.gap("aed-v1.0:116880", "خم", "SOURCE-GAP",
           "مكوّن البخور المسحوق غير مسمى؛ لا يُنتق اسم مادة عربية من وظيفته في تحضير الكيفي."),
    R9.terminal("aed-v1.0:117530", "∅", "OUT-OF-SCOPE",
                "أداة غير لاحقة في صدر الجملة بلا معنى معجمي أو تحليل جذري منشور."),
    R9.gap("aed-v1.0:119620", "خر", "SEMANTIC-GAP",
           "tomb/necropolis لا يطابق حواس خر/خل العربية، ولا يرث street أو fall أو Syria من المتجانسات."),
    R9.gap("aed-v1.0:120550", "حكك", "LAW-GAP",
           "itching يلتقي الحكة مباشرة، لكن ḫ-ḫ لا يسوي ح-ك-ك بصفوف مصرية موقعة ولا صرف يثبت الصامت الثالث.",
           sound="المعنى يعين حكك؛ مسار ḫḫ↔حكك غير مكتمل ولا يجيز حذف ك جذرية.",
           orbit="الحكة هي itching بعينه؛ رجل الصوت وحدها مانعة.",
           keywords="الحكة|حك|هرش"),
    R9.terminal("aed-v1.0:121230", "∅", "OUT-OF-SCOPE",
                "حرف جر through/throughout بلا تحليل جذري منشور؛ لا يرث wood أو fire أو Hittites من متجانسات ḫt."),
    R9.gap("aed-v1.0:121940", "خد", "SEMANTIC-GAP",
           "stream/ford/flow لا يطابق حواس خد/خض العربية بمدار مباشر، ولا يُدخل خوض بصامت واو غير محمول."),
    R9.gap("aed-v1.0:123110", "حنو", "SOURCE-GAP",
           "approach لا يطابق مادة حنو التي تسمي العطف والانحناء؛ كما أن ترتيب الصوامت والطريق الحلقي غير موقع."),
    R9.gap("aed-v1.0:125060", "زت", "SOURCE-GAP",
           "pintail duck طائر مخصوص ولا تسمي المروحة العربية هذا النوع؛ لا يرث معنى woman المتجانس."),
    R9.gap("aed-v1.0:125530", "زا", "SEMANTIC-GAP",
           "inflammation/swelling لا يطابق حواس زا/زر/سا/سر العربية، ولا يرث swelling المتجانس رقم 35040 بلا حكم عضو مستقل."),
    R9.gap("aed-v1.0:125680", "سوح", "MORPHOLOGY-GAP",
           "outside يقترب من الساحة والفضاء الخارجي، لكن الحاء العربية صامت جذري لا يحمله sꜣ ولا صرف مسمى.",
           sound="s↔س ظاهر؛ الحاء في سوح/ساحة بلا مقابل مصري.",
           orbit="الخارج والساحة جوار مكاني، والبنية غير مكتملة.",
           keywords="الساحة|الفضاء|الخارج"),
    R9.gap("aed-v1.0:129550", "سو", "SOURCE-GAP",
           "الزيت غير مسمى؛ لا يُنتق نبات أو دهن عربي من تعريف عام، وبقيت بقية متجانسات sw مفصولة."),
    R9.gap("aed-v1.0:131070", "سب", "SOURCE-GAP",
           "الأداة الطقسية المعدنية غير مسماة ولا موصوفة الوظيفة إلا بفتح الفم؛ لا مقابل عربي معينًا يُحكم عليه."),
    R9.gap("aed-v1.0:133400", "سيف", "DIRECTIONAL-TRANSMISSION",
           "knife/sword يطابق السيف، لكن المقارنة المنشورة المسمّاة تخص zft وتترك z غير المتوقعة والاتجاه الثقافي مفتوحين؛ يلزم تثبيت عضو zf وطريق النقل قبل حكم.",
           sound="النواة z-f تقابل س-ف عبر صف الصفير والمماثلة الشفوية المحتملين؛ الياء العربية رجل جوفاء، لكن مسار العضو والاتجاه غير محسومين.",
           orbit="السلاح القاطع نفسه مباشر، وتبقى هوية العضو واتجاه النقل هما العائق.",
           keywords="السيف|يضرب|السيوف"),
    R9.pos("aed-v1.0:134100", "وسم", "NUCLEUS-ECHO",
           "الكي",
           "s↔س وm↔م هويتان في النواة المصرية s-m؛ الحكم نووي ولا يسقط الواو العربية الجذرية.",
           "image/likeness هي هيئة دالة، والسمة والوسم أثر وصورة يُعرف بها الشيء.",
           "صلة مدارية واحدة من الأثر المصور الدال إلى الهيئة والصورة؛ لذلك ECHO لا تطابق جذر كامل.",
           zero="حُفظ s-m كاملًا؛ الواو في وسم خارج حكم النواة ولم تُدعَ صامتًا مصريًا ساقطًا."),
    R9.gap("aed-v1.0:138940", "زرافة", "MORPHOLOGY-GAP",
           "giraffe يطابق اسم الزرافة دلاليًا، لكن بنية ز-ر-ف لا تستخرج من sr: الفاء زائدة وs↔ز بلا مسار عضو موقع.",
           sound="الرسم المصري s-r ثنائي؛ المقابل ز-ر-ف ثلاثي ولا يكتمل بالهوية الدلالية.",
           orbit="الحيوان نفسه مباشر، والبنية الصوتية مانعة.",
           keywords="الزرافة|حيوان"),
    R9.gap("aed-v1.0:140020", "شعث", "MORPHOLOGY-GAP",
           "damage/disorder يقترب من شعث الشيء واضطرابه، لكن العين والثاء صامتان لا يحملهما shꜣ ولا صرف مصري مسمى.",
           sound="الشين ممكنة؛ بقية ش-ع-ث لا يقابلها الرسم المصري المختار.",
           orbit="إفساد النظام والشعث جوار مباشر، والبنية ساقطة.",
           keywords="شعث|تفرق|فساد"),
    R9.gap("aed-v1.0:140260", "نصح", "LAW-GAP",
           "counsel يطابق النصح، لكن النون العربية بلا مقابل وz↔ص غير موقع مع ḥ↔ح في مسار مصري كامل.",
           sound="المعنى يعين ن-ص-ح؛ الرسم z-ḥ لا يحمل النون ولا صفه الأول مكتملًا.",
           orbit="المشورة والنصيحة مدار مباشر، ورجل الصوت مانعة.",
           keywords="النصح|المشورة|نصيحة"),
    R9.gap("aed-v1.0:143730", "سس", "SEMANTIC-GAP",
           "net لا يطابق حواس سس/سش/سص/شش العربية، ولا يرث burn المتجانس."),
    R9.gap("aed-v1.0:144270", "زش", "SEMANTIC-GAP",
           "writing/writings لا يطابق حواس زش/زس/سش/سس العربية، ولا يُدخل نقش أو كتب من خارج الرسم."),
    R9.gap("aed-v1.0:144380", "زش", "SEMANTIC-GAP",
           "rope لا يطابق حواس زش/زس/سش/سس، ولا يرث writing أو open أو marsh من متجانسات zš."),
    R9.gap("aed-v1.0:146420", "شكو", "LAW-GAP",
           "accusation/complaint يطابق الشكوى، والصوت النووي ممكن، لكن الحدث المجمد الأعلى لشكو هو فجوة في جدار لا فعل الشكاية.",
           sound="s↔ش عبر صف الصفير المرخص في المروحة وk↔ك هوية؛ الواو العربية خارج النواة.",
           orbit="الشكوى والإخبار بسوء الفعل يطابقان accusation/complaint؛ رجل الحدث المعلنة لا تعمل.",
           keywords="الشكوى|شكا|سوء فعله"),
    R9.gap("aed-v1.0:151110", "شع", "SEMANTIC-GAP",
           "marsh/meadow لا يطابق حواس شع/شا/شر العربية، ولا يرث tree أو vine أو wine من متجانسات šꜣ."),
    R9.gap("aed-v1.0:151220", "شيأ", "LAW-GAP",
           "command/ordain يقترب من شاء وأراد، لكن y-ʾ العربيين لا يحملهما šꜣ، والحدث المجمد لشيأ لا يسمي الإرادة.",
           sound="š↔ش ظاهر؛ بقية ش-ي-ء لا يسويها ꜣ المصرية بمسار كامل.",
           orbit="الإرادة والأمر والتقدير جوار مباشر، وبقي الصوت والحدث ناقصين.",
           keywords="شاء|أراد|المشيئة"),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT


def round12_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R11.round11_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND11-COMPLETION", "ROUND12-COMPLETION")
    card = card.replace(
        f"round11-egyptian-rank={rank}/{CARD_COUNT}",
        f"round12-egyptian-rank={rank}/{CARD_COUNT}",
    )
    return card


def render_appendices() -> tuple[str, str, dict]:
    aramaic_text = ARAMAIC.read_text(encoding="utf-8")
    egyptian_text = EGYPTIAN.read_text(encoding="utf-8")
    report_text = REPORT.read_text(encoding="utf-8")
    if MARKER in egyptian_text or MARKER in report_text:
        raise SystemExit("Round-twelve marker already exists; append refused.")

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
        round12_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الثانية عشرة: استمرار المخزون المصري المسجل المفتوح (2026-08-17)", "",
        ("أُعيد فحص الآرامية أولًا فكان الطابور القصير الحي ذا المروحة غير الفارغة صفرًا. "
         f"لذلك سُجل الانتقال المسمى `{TRANSITION}`. انتُقيت البطاقات المصرية التالية "
         "بدءًا من `WO-C-OPEN-COMP-00366` بقصر الهيكل ثم موضع اللقطة. استُبعد صف ḏ "
         "المؤجل. في كل بطاقة عُرضت إصابات AED كلها بلا حد، وكُتب وسم الطريق والرسم "
         "والمدخل المختار، وحُفظ الاختلاف والمتجانسات بلا محو."), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-00366 إلى WO-C-OPEN-COMP-00405", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-00406 إلى WO-C-OPEN-COMP-00445", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([f"<!-- LANE-C-R12-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    state_counts = dict(sorted(collections.Counter(item.state for item in DECISIONS).items()))
    verdict_counts = dict(sorted(collections.Counter(item.verdict for item in DECISIONS).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة الثانية عشرة — المسار C (2026-08-17)", "",
        "- أُعيد فحص الآرامية أولًا: المفتوح القصير الحي ذو المروحة غير الفارغة=0؛ لم تُكرر بطاقة آرامية.",
        f"- سُجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل.",
        "- كُتبت الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00366` إلى `WO-C-OPEN-COMP-00405`.",
        "- كُتبت الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00406` إلى `WO-C-OPEN-COMP-00445`.",
        "- طُبقت قواعد AED الثلاث: كل الإصابات بلا حد؛ وسم الطريق والرسم والمدخل المختار مكتوبة؛ الاختلاف والمتجانسات محفوظة بلا محو.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(state_counts, ensure_ascii=False, sort_keys=True)}؛ لا فجوة حُولت إلى نفي.",
        f"- الأحكام: {json.dumps(verdict_counts, ensure_ascii=False, sort_keys=True)}؛ موجب النواة `sm↔وسم` مقصور على الأثر المصور الدال ولا يسقط الواو العربية.",
        "- المطابقات الدلالية التي لم تكتمل أرجلها بقيت مفتوحة باسمها: `zf↔سيف` للاتجاه، و`sk↔شكو` للحدث، و`šꜣ↔شيأ` للصوت والحدث.",
        "- صف ḏ مؤجل بقرار المؤلف؛ استُبعد من الانتقاء وبقيت بطاقاته على حالها.",
        "- لا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE12 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
    return "\n".join(body).rstrip() + "\n", report, diagnostics


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
