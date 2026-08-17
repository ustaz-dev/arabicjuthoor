#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 16 completion cards without shipping.

Round fifteen was accepted and consolidated. This append-only round rechecks
the exhausted short live-open Aramaic queue, records the continued transition
to the registered Egyptian queue, and completes two forty-card batches from
WO-C-OPEN-COMP-00686. AED is read without a hit limit and the deferred
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

import harvest_lane_c_round15 as R15  # noqa: E402


R9 = R15.R9
R10 = R15.R10
AR = R15.AR
ARAMAIC = R15.ARAMAIC
EGYPTIAN = R15.EGYPTIAN
REPORT = R15.REPORT
MARKER = "LANE-C-ROUND16-2026-08-17"
FIRST_SERIAL = 686
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)


# Every decision is member-scoped. Direct translations remain open whenever
# the complete Egyptian-to-Arabic sound path, frozen event, two Arabic
# witnesses, morphology, or named transmission route is missing. The one
# positive is an ECHO for a bounded wet patch of land, not a claim that every
# Arabic patch is a depression or pool.
DECISIONS: tuple[R9.Decision, ...] = (
    R9.gap("aed-v1.0:170120", "توء", "SEMANTIC-GAP",
           "man of low station/inferior لا يطابق حواس توء/توا العربية، ولا يُدخل فقر أو دناءة من خارج الرسم."),
    R9.gap("aed-v1.0:172430", "تني", "SEMANTIC-GAP",
           "old man لا يطابق حواس تني/تنو العربية، ولا يُدخل شيخ من خارج الرسم."),
    R9.gap("aed-v1.0:174240", "ثءي", "SEMANTIC-GAP",
           "man/male لا يطابق حواس ثءي وصور المروحة، ولا يُدخل رجل أو ذكر من خارج الرسم."),
    R9.gap("aed-v1.0:175700", "ثنت", "MORPHOLOGY-GAP",
           "bowl woman تسمية مهنية مشتقة من إناء وخدمة، ولا يثبت AED أن ثنت مادة جذرية تحمل معنى المرأة أو السقي."),
    R9.gap("aed-v1.0:177020", "ثزت", "MORPHOLOGY-GAP",
           "mourning woman اسم فاعلة شعائرية مؤنثة؛ لا يثبت من الرسم ثزت جذر عربي لمعنى النواح."),
    R9.gap("aed-v1.0:400636", "يوو", "MORPHOLOGY-GAP",
           "boatless man وصف اشتقاقي للحرمان من القارب، ولا تحمل يوو العربية بنية النفي أو اسم القارب."),
    R9.gap("aed-v1.0:850289", "يقر", "SEMANTIC-GAP",
           "trustworthy/excellent man لا يطابق مادة يقر العربية، ولا تُبدل الياء واو وقار بلا صف مصري موقع."),
    R9.gap("aed-v1.0:860260", "زير", "SEMANTIC-GAP",
           "man who acts لا يطابق الزير العربي ولا يثبت معنى الفعل العام مادة معجمية مقابلة."),
    R9.gap("aed-v1.0:9", "ءيو", "SOURCE-GAP",
           "الظاهرة الجوية نفسها موسومة بالشك، وgust of wind احتمال لا تعيين؛ لا يُنتق مدار عربي قبل حسمها."),
    R9.gap("aed-v1.0:142", "ءمو", "SEMANTIC-GAP",
           "scorching heat/flame لا يطابق حواس ءمو/ءمي العربية، ولا يُدخل لهب من خارج الرسم."),
    R9.gap("aed-v1.0:191", "ءحت", "SEMANTIC-GAP",
           "field/arable land لا يطابق حواس ءحت العربية، ولا يُدخل حقل من خارج الرسم."),
    R9.gap("aed-v1.0:223", "ءخت", "SEMANTIC-GAP",
           "flame/fire لا يطابق حواس ءخت العربية، ولا يرث معنى الحقل من المتجانس التالي."),
    R9.gap("aed-v1.0:228", "ءخت", "SEMANTIC-GAP",
           "field/arable land لا يطابق حواس ءخت العربية، وفُصل عن متجانس اللهب السابق."),
    R9.gap("aed-v1.0:21670", "يعب", "SOURCE-GAP",
           "نوع الوعاء ووظيفته بين البخور وماء الكاتب موضوعان بين معقوفين؛ لا يصدر مدار يعب قبل تثبيت الشيء."),
    R9.gap("aed-v1.0:21810", "يعح", "SEMANTIC-GAP",
           "moon لا يطابق حواس يعح العربية، ولا يُدخل قمر من خارج الرسم."),
    R9.gap("aed-v1.0:21820", "يعح", "MORPHOLOGY-GAP",
           "اليوم الثامن عشر تسمية تقويمية مشتقة من الشهر القمري، ولا تحمل يعح العربية صرف العدد أو اليوم."),
    R9.gap("aed-v1.0:22600", "يون", "SEMANTIC-GAP",
           "wind as support of heaven استعارة كونية لا تطابق حواس يون العربية، ولا تُسوّى بالعماد خارج الرسم."),
    R9.gap("aed-v1.0:23000", "يوح", "SEMANTIC-GAP",
           "sprinkle/moisten لا يطابق حواس يوح العربية، ولا يُدخل بلل أو نضح من خارج الرسم."),
    R9.gap("aed-v1.0:24180", "يبت", "NAME-ROOT-OPEN",
           "Ipet اسم للسماء في الترجمة، ولا يقدم AED تحليلًا جذريًا يربطه بمادة يبت العربية."),
    R9.gap("aed-v1.0:24570", "يفد", "SEMANTIC-GAP",
           "rectangle/square plot لا يطابق حواس يفد العربية، ولا يكفي شكل القطعة لإدخال ربع من خارج الرسم."),
    R9.gap("aed-v1.0:28230", "يرت", "SOURCE-GAP",
           "water نفسه موسوم بعلامة الشك؛ لا يُنتق مدار يرت ولا يُدخل ماء قبل حسم القراءة."),
    R9.gap("aed-v1.0:32720", "يجب", "SEMANTIC-GAP",
           "air/wind لا يطابق حواس يجب العربية، ولا يرث rain cloud من المتجانس القريب."),
    R9.gap("aed-v1.0:32730", "يجب", "SEMANTIC-GAP",
           "rain cloud لا يطابق حواس يجب العربية، ولا يرث air/wind من العضو السابق."),
    R9.gap("aed-v1.0:33080", "يتن", "SEMANTIC-GAP",
           "sun or moon disk لا يطابق حواس يتن العربية، ولا يُدخل قرص من خارج الرسم."),
    R9.gap("aed-v1.0:33090", "يتن", "SEMANTIC-GAP",
           "sun-disk mirror لا يطابق حواس يتن العربية، وفُصل عن القرص السماوي ومتجانس الأرض."),
    R9.gap("aed-v1.0:33120", "يتن", "SEMANTIC-GAP",
           "ground/earth/dust لا يطابق حواس يتن العربية، ولا يرث معنى القرص من المتجانسين السابقين."),
    R9.gap("aed-v1.0:35080", "عءي", "SEMANTIC-GAP",
           "glowing fire لا يطابق حواس عءي/عاي العربية، ولا يُدخل نار من خارج الرسم."),
    R9.gap("aed-v1.0:35140", "عءع", "SEMANTIC-GAP",
           "water hole/wet ground لا يطابق حواس عءع العربية، ولا يُدخل غدير من خارج الرسم."),
    R9.gap("aed-v1.0:38710", "عنخ", "SEMANTIC-GAP",
           "water of life في سياق عطية إيزيس لا يطابق حواس عنخ العربية، ولا ينقل معنى الحياة إلى الرسم."),
    R9.gap("aed-v1.0:38720", "عنخ", "SEMANTIC-GAP",
           "earth/land لا يطابق حواس عنخ العربية، ولا يرث water of life من المتجانس السابق."),
    R9.gap("aed-v1.0:39880", "عحت", "SEMANTIC-GAP",
           "cultivated land لا يطابق حواس عحت العربية، ولا يُدخل حرث بصامت غير محمول."),
    R9.gap("aed-v1.0:40120", "عحع", "SEMANTIC-GAP",
           "position of a star لا يطابق حواس عحع العربية، ولا يُدخل موقع من خارج الرسم."),
    R9.gap("aed-v1.0:42650", "وءو", "SEMANTIC-GAP",
           "sea wave/flood water لا يطابق حواس وءو/واو العربية، ولا يُدخل موج من خارج الرسم."),
    R9.gap("aed-v1.0:43240", "وءخ", "NAME-ROOT-OPEN",
           "Fresh-water اسم قناة في العالم السفلي، ولا يقدم AED تحليلًا جذريًا يربطه بمادة وءخ العربية."),
    R9.gap("aed-v1.0:45370", "وبس", "SEMANTIC-GAP",
           "swell of water/inundation لا يطابق حواس وبس/وبش/وبص العربية، ولا يكفي الانتفاخ العام."),
    R9.gap("aed-v1.0:45720", "وبو", "MORPHOLOGY-GAP",
           "Opener لقب اليوم الأول من الشهر القمري، ولا تحمل وبو العربية اشتقاق الفتح ولا صرف اسم اليوم."),
    R9.gap("aed-v1.0:46370", "وني", "SOURCE-GAP",
           "night's rest موسوم بالشك؛ ونى العربية يدل على الفتور ولا يثبت أن المرجع الراحة نفسها.",
           sound="w↔و وn↔ن ظاهران؛ الواو المصرية الأخيرة لا تسوي ياء وني بلا تحليل صرفي.",
           orbit="الفتور قد يسبق الراحة الليلية، لكنه لا يعين معنى الاسم المشكوك.",
           keywords="ونى|الفتور|الضعف"),
    R9.gap("aed-v1.0:47490", "وري", "MORPHOLOGY-GAP",
           "great flame يطابق وريا الزند وخروج ناره، لكن نزع t التأنيث يترك w-r ولا يثبت الياء العربية.",
           sound="w↔و وr↔ر هويتان؛ t المصرية علامة تأنيث محتملة لا تقابل ياء وري، والياء العربية بلا حامل.",
           orbit="لهب المذبح ونار الزند نار ظاهرة واحدة؛ البنية الجوفاء وحدها تمنع الحكم.",
           keywords="وري الزند|أورى|ناره"),
    R9.gap("aed-v1.0:50650", "وشر", "SEMANTIC-GAP",
           "dry land/dry area لا يطابق حواس وشر/وسر العربية، ولا يُدخل يبس من خارج الرسم."),
    R9.gap("aed-v1.0:52990", "بءت", "SOURCE-GAP",
           "الأداة الخشبية لتفتيت الأرض موسومة بالشك ومختلف في كونها مدقة أو دكاكة؛ لا يصدر مقابل قبل تعيينها."),
    R9.gap("aed-v1.0:53550", "بءخ", "SEMANTIC-GAP",
           "rise and shine of the sun لا يطابق حواس بءخ/باخ العربية، ولا يُدخل بزغ من خارج الرسم."),
    R9.pos("aed-v1.0:53790", "بقع", "ROOT-ECHO",
           "البقعة|قطعة من الأرض|ابتلت|الماء",
           "b↔ب وq↔ق وꜥ↔ع هويات صامتية كاملة في العضو.",
           "المنخفض الذي يجتمع فيه ماء الفيضان بقعة محددة من الأرض، والعربية تسمي القطعة بقعة وتصف ابتلال مواضعها.",
           "الحكم ECHO لصورة الموضع المحدد المبتل، لا دعوى أن كل بقعة عربية منخفض أو حوض."),
    R9.gap("aed-v1.0:54320", "بيء", "SEMANTIC-GAP",
           "heaven/firmament لا يطابق حواس بيء/بيا العربية، ولا يُدخل سماء من خارج الرسم."),
    R9.gap("aed-v1.0:54970", "بحر", "DIRECTIONAL-TRANSMISSION",
           "sea/river يطابق البحر دلاليًا، وAED يوسم العضو قرضًا ساميًا، لكنه لا يسمي المانح أو الطريق ولا يوقع ꜥ↔ح.",
           sound="b↔ب وr↔ر هويتان؛ ꜥ المصرية ↔ ح العربية غير موقع في طريق عضو كامل.",
           orbit="البحر والمجرى المائي الكبيران في المدار نفسه، وبقي الصوت والاتجاه التاريخي مانعين.",
           keywords="البحر|الماء|النهر"),
    R9.gap("aed-v1.0:55000", "بعح", "SEMANTIC-GAP",
           "inundated land لا يطابق حواس بعح العربية، ولا يُدخل ري أو فيضان من خارج الرسم."),
    R9.gap("aed-v1.0:59250", "بءس", "SEMANTIC-GAP",
           "scribe's water-pot لا يطابق حواس بءس/فءس العربية، ولا يُدخل كأس أو إناء من خارج الرسم."),
    R9.gap("aed-v1.0:59650", "بعت", "SOURCE-GAP",
           "bank/area of land تعريف عام لا يعين ضفة أو نوع أرض بعينه؛ لا يصدر مدار بعت قبل التحديد."),
    R9.gap("aed-v1.0:59660", "بعو", "SEMANTIC-GAP",
           "flames لا يطابق حواس بعو/فعو العربية، ولا يرث bank من المتجانس السابق."),
    R9.gap("aed-v1.0:60110", "بنس", "SEMANTIC-GAP",
           "earth بوصفها مادة طبية لا يطابق حواس بنس/فنس العربية، ولا يُدخل تراب من خارج الرسم."),
    R9.gap("aed-v1.0:62930", "بتر", "SEMANTIC-GAP",
           "two windows of heaven لا يطابق البتر أو حواس بتر/فتر/فطر العربية؛ صورة الفتحة وحدها لا تكفي."),
    R9.gap("aed-v1.0:66400", "مءي", "NAME-ROOT-OPEN",
           "Lion اسم كوكبة ساعة، ولا يقدم AED تحليلًا جذريًا يربط اسم الأسد بمادة مءي العربية."),
    R9.gap("aed-v1.0:67200", "مءر", "SEMANTIC-GAP",
           "sky لا يطابق حواس مءر/مار العربية، ولا يُدخل سماء من خارج الرسم."),
    R9.gap("aed-v1.0:69840", "منت", "SEMANTIC-GAP",
           "heaven لا يطابق حواس منت العربية، ولا يرث معنى السماء من متجانس آخر."),
    R9.gap("aed-v1.0:73740", "محي", "SEMANTIC-GAP",
           "be in water/swim/drown لا يطابق محو الشيء أو حواس محي العربية، ولا يُدخل سبح أو غرق خارج الرسم."),
    R9.gap("aed-v1.0:74660", "مخر", "SEMANTIC-GAP",
           "low-lying land لا يطابق حواس مخر العربية، ولا يكفي الانخفاض لإدخال غور من خارج الرسم."),
    R9.gap("aed-v1.0:76790", "مقق", "DIRECTIONAL-TRANSMISSION",
           "soft moist soil موسوم قرضًا ساميًا، لكن AED لا يسمي المانح ولا طريق النقل، وحواس مقق العربية لا تعين هذه التربة.",
           sound="m↔م وq-q↔ق-ق هويات سطحية؛ الهوية لا تحسم المانح ولا المعنى.",
           orbit="التربة الرطبة معينة في المصرية، ولم يثبت لها مقابل عربي مباشر في المادة المقروءة."),
    R9.gap("aed-v1.0:80950", "توت", "LAW-GAP",
           "sky/temple roof لا يطابق التوت، وفصل t التأنيث من n-w-t يترك n-w ولا ينتج t-w-t.",
           sound="المصرية n-w-t والعربية ت-w-t تختلفان في الطرف الأول، ولا يجوز إسقاط n أو قلبها t بلا صف موقع.",
           orbit="السماء وسقف المعبد استعارة واحدة في العضو المصري؛ ثمرة التوت خارج هذا المدار.",
           keywords="التوت|الفرصاد"),
    R9.gap("aed-v1.0:81240", "نوي", "SEMANTIC-GAP",
           "water/flood water لا يطابق حواس نوي/نوا العربية، ولا يُدخل ماء من خارج الرسم."),
    R9.gap("aed-v1.0:82590", "نبي", "SEMANTIC-GAP",
           "flame لا يطابق حواس نبي العربية، ولا يُدخل نار من خارج الرسم."),
    R9.gap("aed-v1.0:82850", "نبد", "SEMANTIC-GAP",
           "wind around/coil لا يطابق حواس نبد/نبض العربية؛ حركة النبض لا تساوي الالتفاف."),
    R9.gap("aed-v1.0:84660", "ننت", "SEMANTIC-GAP",
           "lower heaven لا يطابق حواس ننت العربية، ولا يُدخل سماء من خارج الرسم."),
    R9.gap("aed-v1.0:87500", "نخخ", "NAME-ROOT-OPEN",
           "Enduring-one اسم نجم مترجم بصفة، ولا يقدم AED مادة جذرية تربطه بحواس نخخ العربية."),
    R9.gap("aed-v1.0:87740", "نخن", "SEMANTIC-GAP",
           "gruel of water and earth لا يطابق حواس نخن العربية، ولا يُدخل طين من خارج الرسم."),
    R9.gap("aed-v1.0:88280", "نسر", "SEMANTIC-GAP",
           "flame لا يطابق النسر الطائر أو حواس نسر العربية، ولا يرث اسم النجم المتجانس دلاليًا."),
    R9.gap("aed-v1.0:93220", "ريت", "SEMANTIC-GAP",
           "heaven لا يطابق حواس ريت العربية، ولا يُدخل سماء من خارج الرسم."),
    R9.gap("aed-v1.0:93290", "رعو", "SEMANTIC-GAP",
           "sun لا يطابق حواس رعو العربية، ولا يُدخل شمس من خارج الرسم."),
    R9.gap("aed-v1.0:94870", "رنب", "SEMANTIC-GAP",
           "fresh water لا يطابق حواس رنب العربية، ولا يُدخل عذب من خارج الرسم."),
    R9.gap("aed-v1.0:96120", "رسو", "SEMANTIC-GAP",
           "south-wind لا يطابق الرسو أو حواس رسو العربية، ولا يكفي الاتجاه الجغرافي لتغيير المدار."),
    R9.gap("aed-v1.0:96440", "ركح", "SEMANTIC-GAP",
           "light a fire/burn up لا يطابق حواس ركح/رخح العربية، ولا يُدخل أحرق بصامت زائد."),
    R9.gap("aed-v1.0:96450", "ركح", "SEMANTIC-GAP",
           "fire لا يطابق حواس ركح/رخح العربية، ولا يرث فعل الإشعال من المتجانس السابق."),
    R9.gap("aed-v1.0:97890", "هين", "SOURCE-GAP",
           "kind of land or boundary تعريف متردد لا يعين الأرض ولا الحد؛ لا يُنتق مدار هين قبل الحسم."),
    R9.gap("aed-v1.0:97960", "هوت", "SEMANTIC-GAP",
           "flame/fire لا يطابق حواس هوت العربية، ولا يُدخل نار من خارج الرسم."),
    R9.gap("aed-v1.0:99060", "وهر", "LAW-GAP",
           "day لا يطابق وهج الحر نفسه، كما أن h-r-w المصرية لا تسوي w-h-r العربية بلا قلب مكاني.",
           sound="الصوامت الثلاثة محفوظة في الهيكلين، وترتيب h-r-w مقابل w-h-r يحتاج قلبًا غير موقع.",
           orbit="النهار زمن، والوهر توهج وقع الشمس وشدة الحر؛ المجاورة السببية لا توحد المدار.",
           keywords="الوهر|توهج|شدة الحر"),
    R9.gap("aed-v1.0:101620", "حءج", "SOURCE-GAP",
           "touch of a boat on land موصوف كذلك مع وسم الفعل الملاحي بين معقوفين؛ لا يتعين رسو أو مس قبل حسم الاستعمال."),
    R9.gap("aed-v1.0:102400", "حوت", "SEMANTIC-GAP",
           "rain/flood لا يطابق حواس حوت العربية، ولا يُدخل مطر من خارج الرسم."),
    R9.gap("aed-v1.0:106150", "حنو", "SOURCE-GAP",
           "rising of the wind موسوم بالشك، ولا يطابق حنو العربية حتى يثبت معنى الفعل واتجاه الحركة."),
    R9.gap("aed-v1.0:106480", "حنب", "SEMANTIC-GAP",
           "arable land لا يطابق حواس حنب العربية، ولا يُدخل حرث أو حقل من خارج الرسم."),
    R9.gap("aed-v1.0:107180", "حنك", "SEMANTIC-GAP",
           "donated land/donation لا يطابق حواس حنك العربية، ولا يُدخل هبة من خارج الرسم."),
    R9.gap("aed-v1.0:107670", "حرت", "SEMANTIC-GAP",
           "heaven لا يطابق حواس حرت العربية، ولا يُدخل سماء من خارج الرسم."),
    R9.gap("aed-v1.0:109330", "حزت", "SEMANTIC-GAP",
           "ritual water jar/ewer لا يطابق حواس حزت العربية، ولا يُدخل إبريق من خارج الرسم."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT


def round16_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R15.round15_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND15-COMPLETION", "ROUND16-COMPLETION")
    card = card.replace(
        f"round15-egyptian-rank={rank}/{CARD_COUNT}",
        f"round16-egyptian-rank={rank}/{CARD_COUNT}",
    )
    return card


def render_appendices() -> tuple[str, str, dict]:
    aramaic_text = ARAMAIC.read_text(encoding="utf-8")
    egyptian_text = EGYPTIAN.read_text(encoding="utf-8")
    report_text = REPORT.read_text(encoding="utf-8")
    if MARKER in egyptian_text or MARKER in report_text:
        raise SystemExit("Round-sixteen marker already exists; append refused.")

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
        round16_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة السادسة عشرة: استمرار المخزون المصري المسجل المفتوح (2026-08-17)", "",
        ("أُعيد فحص الآرامية أولًا فكان الطابور القصير الحي ذا المروحة غير الفارغة صفرًا. "
         f"لذلك سُجل الانتقال المسمى `{TRANSITION}`. انتُقيت البطاقات المصرية التالية "
         "بدءًا من `WO-C-OPEN-COMP-00686` بقصر الهيكل ثم موضع اللقطة. استُبعد صف ḏ "
         "المؤجل. في كل بطاقة عُرضت إصابات AED كلها بلا حد، وكُتب وسم الطريق والرسم "
         "والمدخل المختار، وحُفظ الاختلاف والمتجانسات بلا محو."), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-00686 إلى WO-C-OPEN-COMP-00725", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-00726 إلى WO-C-OPEN-COMP-00765", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([f"<!-- LANE-C-R16-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    state_counts = dict(sorted(collections.Counter(item.state for item in DECISIONS).items()))
    verdict_counts = dict(sorted(collections.Counter(item.verdict for item in DECISIONS).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة السادسة عشرة: المسار C (2026-08-17)", "",
        "- أُعيد فحص الآرامية أولًا: المفتوح القصير الحي ذو المروحة غير الفارغة=0؛ لم تُكرر بطاقة آرامية.",
        f"- سُجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل.",
        "- كُتبت الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00686` إلى `WO-C-OPEN-COMP-00725`.",
        "- كُتبت الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00726` إلى `WO-C-OPEN-COMP-00765`.",
        "- طُبقت قواعد AED الثلاث: كل الإصابات بلا حد؛ وسم الطريق والرسم والمدخل المختار مكتوبة؛ الاختلاف والمتجانسات محفوظة بلا محو.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(state_counts, ensure_ascii=False, sort_keys=True)}؛ لا فجوة حُولت إلى نفي.",
        f"- الأحكام: {json.dumps(verdict_counts, ensure_ascii=False, sort_keys=True)}؛ الموجب `bqꜥ↔بقع` موسوم ECHO لصورة الموضع المحدد المبتل، لا لتسوية كل بقعة بالحوض.",
        "- المطابقات الدلالية ذات الرجل الناقصة بقيت مفتوحة باسمها، ومنها `wr.t↔وري` للبنية، و`bꜥr↔بحر` للصوت والاتجاه، و`hrw↔وهر` للقلب والمدار.",
        "- صف ḏ مؤجل بقرار المؤلف؛ استُبعد من الانتقاء وبقيت بطاقاته على حالها.",
        "- لا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE16 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
