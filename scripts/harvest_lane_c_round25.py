#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 25 completion cards without shipping or git.

The short live-open Aramaic queue is rechecked first.  When it remains
exhausted, the script records the named transition to the registered Egyptian
open queue and completes two forty-card batches, WO-C-OPEN-COMP-01263..01342.
All AED homographs are retained, the deferred Egyptian ḏ row stays excluded,
and the output follows the WO-B-PROBE-001 field contract.
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

import harvest_lane_c_round24 as R24


R9 = R24.R9
AR = R24.AR
ROOT = R24.ROOT
ARAMAIC = R24.ARAMAIC
EGYPTIAN = R24.EGYPTIAN
REPORT = R24.REPORT

MARKER = "LANE-C-ROUND25-2026-08-25"
FIRST_SERIAL = 1263
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)


# Every ruling is scoped to the selected AED member.  Unidentified or
# explicitly questioned AED senses remain SOURCE-GAP.  Direct semantic
# comparisons whose Egyptian sound leg is unsigned remain LAW-GAP.  The sole
# positive, ꜥrq "sack" ~ Arabic عرق "woven basket", has three named identity
# rows, a frozen event, two old Arabic witnesses, and a handwritten container
# orbit.  No gap is converted into a negative verdict.
DECISIONS: tuple[R9.Decision, ...] = (
    R9.gap("aed-v1.0:26020", "يمن", "SEMANTIC-GAP", "create/fashion لا يطابق اليمن للبركة والجهة واليمين، ولا أمن للأمان."),
    R9.gap("aed-v1.0:26620", "ينت", "SOURCE-GAP", "AED لا يعين إلا garment عامة؛ لا نوع للباس يقوم عليه مدار عربي مخصوص."),
    R9.gap("aed-v1.0:26720", "أني", "LAW-GAP", "tarry/delay يطابق أني وتأنى للتأخر والإبطاء، لكن قيمة j المصرية في الموضعين لا صف مصريا موقعا لها.", sound="n↔ن هوية IDN-03؛ j الأولى↔ء وj الأخيرة↔ي هما الموضعان المؤجلان في الصف المصري.", orbit="أني الرجل تأخر وأبطأ، وتأنى تمكث ولم يعجل؛ وهو مدار tarry/delay مباشرة، وبقي الصوت وحده ناقصا.", keywords="تأخر|أبطأ|تأنى|تمكث|لم يعجل"),
    R9.gap("aed-v1.0:26890", "يني", "SEMANTIC-GAP", "cordage البحري لا يطابق حواس يني أو أني أو الصور الأقصر، ولا يدخل حبل من خارج الرسم."),
    R9.gap("aed-v1.0:27040", "ينو", "SEMANTIC-GAP", "gifts/produce/tribute لا يجد في ينو أو أنو أو النواة شاهد هدية أو نتاج أو أتاوة عاملا."),
    R9.gap("aed-v1.0:27150", "ينب", "SOURCE-GAP", "الطائر غير مسمى في AED؛ لا ينتق اسم طائر عربي من الهيكل وحده."),
    R9.gap("aed-v1.0:27200", "ينب", "SOURCE-GAP", "النبات غير مسمى في AED؛ لا ينتق اسم نبات عربي من الهيكل وحده."),
    R9.gap("aed-v1.0:27330", "ينب", "SOURCE-GAP", "papyrus skiff نفسها موسومة بالشك في اللغتين؛ لا يصدر مدار قارب من مرجع غير محسوم."),
    R9.terminal("aed-v1.0:27460", "∅", "OUT-OF-SCOPE", "أداة شرط وظيفية بمعنى if؛ لا مادة جذرية معجمية مستقلة في المدخل."),
    R9.gap("aed-v1.0:27570", "ينر", "SEMANTIC-GAP", "bowl للخمر أو الزيت لا يطابق حواس ينر أو ينل، ولا يدخل قدح من خارج الرسم."),
    R9.gap("aed-v1.0:27710", "ينح", "SEMANTIC-GAP", "surround/enclose/border لا يجد في ينح أو أنح شاهد إحاطة أو تطويق عاملا."),
    R9.gap("aed-v1.0:27970", "ينت", "SOURCE-GAP", "صفة الورق نفسها موسومة بالشك بين الملاسة ومشابهة الزجاج؛ لا مدار قبل تعيينها."),
    R9.gap("aed-v1.0:28060", "يند", "SEMANTIC-GAP", "misery لا يطابق حواس يند أو ينض أو أند أو أنض، ولا يدخل البؤس من خارج الرسم."),
    R9.gap("aed-v1.0:28520", "يري", "SOURCE-GAP", "AED يتردد بين ointment وjar for ointment ويسم كليهما بالشك؛ لا يحدد مادة أو إناء."),
    R9.gap("aed-v1.0:28580", "يرت", "SEMANTIC-GAP", "purpose/duty لا يطابق حواس يرت أو يلت أو الصور الهمزية، ولا يدخل القصد من خارج الرسم."),
    R9.gap("aed-v1.0:29520", "سدخ", "SEMANTIC-GAP", "commit sacrilege لا يطابق حواس سدخ أو سضخ أو الصور الصفيرية المجاورة."),
    R9.gap("aed-v1.0:29630", "يرو", "SOURCE-GAP", "الطعام غير مسمى في AED؛ لا ينتق قوت عربي من الهيكل وحده."),
    R9.gap("aed-v1.0:29890", "يرخ", "SOURCE-GAP", "الحجر شبه الكريم غير مسمى، وberg crystal اقتراح؛ لا ينتق اسم معدن عربي."),
    R9.gap("aed-v1.0:30060", "يرث", "SOURCE-GAP", "نوع السمك غير مسمى؛ لا ينتق اسم سمكة عربية من الهيكل وحده."),
    R9.gap("aed-v1.0:30200", "يهي", "SOURCE-GAP", "نوع الحبوب غير مسمى في AED؛ لا ينتق اسم زرع عربي من الهيكل وحده."),
    R9.gap("aed-v1.0:30240", "يهب", "SEMANTIC-GAP", "ritual dancer لا يطابق حواس يهب أو يحب أو الصور الهمزية، ولا يدخل رقص من خارج الرسم."),
    R9.gap("aed-v1.0:30290", "يهم", "SEMANTIC-GAP", "jubilation لا يجد في يهم أو يحم أو الصور الهمزية شاهد فرح أو تهليل عاملا."),
    R9.gap("aed-v1.0:30540", "يحي", "SOURCE-GAP", "darken للنجوم موسوم بالشك في كلتا لغتي AED؛ لا يصدر مدار ظلام من حس غير محسوم."),
    R9.gap("aed-v1.0:30650", "يحو", "SOURCE-GAP", "وحدة المعدن مختلف فيها بين سبيكة نحاس وقطع ذهب؛ لا مرجع معينا للمدار."),
    R9.gap("aed-v1.0:30750", "يخت", "SEMANTIC-GAP", "thing/goods/offerings لا يطابق حواس يخت أو أخت أو الصور الأقصر، ولا يدخل متاع من خارج الرسم."),
    R9.gap("aed-v1.0:31050", "يزو", "SEMANTIC-GAP", "old/primeval ones لا يجد في يزو أو يسو أو صورهما الهمزية شاهد القدم أو الأولية عاملا."),
    R9.gap("aed-v1.0:31100", "يزت", "SEMANTIC-GAP", "age/decline لا يطابق حواس يزت أو يست أو المروحة المقروءة، ولا يدخل الهرم من خارج الرسم."),
    R9.gap("aed-v1.0:31330", "يسو", "SEMANTIC-GAP", "payment/equivalent لا يطابق حواس يسو أو يشو أو يصو؛ وسوي للمعادلة لا تحمل j المصرية الأولى."),
    R9.gap("aed-v1.0:31470", "يسب", "SEMANTIC-GAP", "applicator for unguent لا يطابق حواس يسب أو يسف أو الصور الصفيرية المجاورة."),
    R9.gap("aed-v1.0:31920", "يشو", "SEMANTIC-GAP", "dogs towing the solar bark لا يجد في يشو أو يسو أو نواتهما اسم الكلب عاملا."),
    R9.gap("aed-v1.0:32460", "يكت", "SOURCE-GAP", "AED لا يثبت إلا أن المدخل noun بلا معنى معجمي؛ لا يمكن كتابة مدار."),
    R9.gap("aed-v1.0:33130", "يتن", "SEMANTIC-GAP", "oppose لا يطابق حواس يتن أو يطن أو الصور الهمزية، ولا يدخل ضد أو مانع من خارج الرسم."),
    R9.gap("aed-v1.0:33260", "يتر", "SEMANTIC-GAP", "papyrus/aquatic plant for cordage لا يطابق حواس يتر أو يطر أو صورهما الهمزية."),
    R9.gap("aed-v1.0:33540", "يثا", "SEMANTIC-GAP", "thief لا يجد في يثا أو يتا أو يطا أو الفروع الهمزية شاهد سرقة عاملا."),
    R9.gap("aed-v1.0:33630", "يثو", "SEMANTIC-GAP", "thief/conqueror لا يطابق حواس يثو أو يتو أو يطو، ولا تدمج السرقة والغزو في مقابل مفترض."),
    R9.gap("aed-v1.0:33900", "يدي", "SEMANTIC-GAP", "cense/libate لا يطابق حواس يدي أو يضي أو الصور الهمزية، ولا يدخل صب أو بخر من خارج الرسم."),
    R9.gap("aed-v1.0:34080", "يدن", "SEMANTIC-GAP", "replace/act as deputy/have sway لا يطابق حواس يدن أو يضن أو الصور الهمزية، ولا تدمج الحواس الثلاثة."),
    R9.gap("aed-v1.0:34140", "يدر", "SEMANTIC-GAP", "belt/girdle لا يطابق حواس يدر أو يدل أو الصور الضادية، ولا يدخل حزام من خارج الرسم."),
    R9.gap("aed-v1.0:34890", "عات", "SEMANTIC-GAP", "stone vessel لا يطابق حواس عات أو عاط أو المروحة المقروءة، ولا يدخل إناء من خارج الرسم."),
    R9.gap("aed-v1.0:34930", "علا", "LAW-GAP", "rule/Herrschaft يلتقي علا للغلبة والقهر، لكن ꜣ المصرية الثانية↔ل العربية بلا صف مصري موقع لهذا العضو.", sound="ꜥ↔ع هوية IDN-15؛ ꜣ↔ل هو الموضع المانع؛ t الأخيرة علامة الاسم المؤنث المسجلة.", orbit="علاه غلبه وقهره؛ السيادة والغلبة مدار rule مباشر، وبقي الصوت وحده ناقصا.", keywords="علا|غلب|قهر|السلطان", zero="نزعت t الأنثوية المسجلة فقط؛ بقي الهيكل ꜥ-ꜣ بلا إسقاط آخر."),
    R9.gap("aed-v1.0:35120", "عاي", "SOURCE-GAP", "phallus نفسه موسوم بالشك في اللغتين؛ لا يصدر مدار عضو من تعيين غير محسوم."),
    R9.gap("aed-v1.0:35200", "عاع", "SEMANTIC-GAP", "reeds لا تطابق حواس عاع أو عاض أو عاغ وبقية المروحة؛ وغاغة العربية نبات آخر غير معين بالقصب."),
    R9.gap("aed-v1.0:35300", "عاب", "SOURCE-GAP", "AED يتردد بين tree وplant ويسم كليهما بالشك؛ لا ينتق نوع عربي من الرسم وحده."),
    R9.gap("aed-v1.0:35350", "عاب", "LAW-GAP", "reproach يطابق عاب الشيء ونسبه إلى العيب، لكن ꜣ المصرية وسطا ليست صائتة عربية ولا ياء عيب بصف مصري موقع.", sound="ꜥ↔ع هوية IDN-15؛ p↔ب يمر بـLAB-01؛ ꜣ الوسطى بإزاء الألف السطحية/ياء الجذر هي الموضع المانع.", orbit="عابه جعله معيبا وذكر نقصه؛ وهو مدار reproach مباشرة، وبقي صامت ꜣ بلا صف.", keywords="عاب|العيب|عيبته|معيب"),
    R9.gap("aed-v1.0:35620", "عين", "SEMANTIC-GAP", "limestone لا يطابق حواس عين أو عأن أو الصور الضادية والغينية، ولا يدخل الجير من خارج الرسم."),
    R9.gap("aed-v1.0:35760", "ععو", "SEMANTIC-GAP", "sleep لا يطابق حواس ععو أو عضو أو عغو وبقية المروحة، ولا يدخل نوم أو غفو من خارج الرسم."),
    R9.gap("aed-v1.0:35870", "عوت", "SEMANTIC-GAP", "herds/flocks لا يطابق حواس عوت أو عوط أو الصور الضادية والغينية، وعواء الذئب في الغنم ليس اسم القطيع."),
    R9.gap("aed-v1.0:35950", "عوا", "SEMANTIC-GAP", "foulness/rotting لا يطابق حواس عوا أو عور أو غوا، ولا يدخل عفن بصامتين من خارج الرسم."),
    R9.gap("aed-v1.0:36210", "عوج", "SEMANTIC-GAP", "parch/roast grain لا يطابق العوج والميل في عوج، ولا عوق للحبس أو بقية المروحة."),
    R9.gap("aed-v1.0:36390", "عبت", "SEMANTIC-GAP", "worker of horn لا يطابق حواس عبت أو عبط أو الصور الضادية والغينية، ولا يرث العامل اسم مادته."),
    R9.gap("aed-v1.0:36580", "عبا", "SEMANTIC-GAP", "pigeon لا يطابق حواس عبا أو عبر أو الصور الضادية والغينية؛ والغبرور عصفور آخر لا حمامة."),
    R9.gap("aed-v1.0:36630", "عبع", "SEMANTIC-GAP", "boast لا يجد في عبع أو عبض أو عبغ وبقية المروحة شاهد الفخر والمباهاة عاملا."),
    R9.gap("aed-v1.0:36760", "عبو", "SOURCE-GAP", "pitchfork wielder وKornaufhäufer كلاهما موسوم بالشك؛ لا يحسم AED المهنة أو الأداة."),
    R9.gap("aed-v1.0:36860", "عبب", "SEMANTIC-GAP", "use a pitchfork لا يطابق حواس عبب أو ضبب أو غبب؛ واقتراح harvest الألماني لا ينشئ مقابلا."),
    R9.gap("aed-v1.0:36920", "عبش", "SEMANTIC-GAP", "wine jug لا يطابق حواس عبش أو عبس أو الصور الضادية والغينية، ولا يدخل إبريق من خارج الرسم."),
    R9.gap("aed-v1.0:36990", "عبر", "LAW-GAP", "stride through/by يطابق عبر وجاز من ضفة إلى أخرى، لكن j المصرية الأخيرة↔ر العربية بلا صف موقع.", sound="ꜥ↔ع هوية IDN-15؛ p↔ب عبر LAB-01؛ j النهائية↔ر هي الرجل المصرية غير الموقعة.", orbit="عبر المكان قطعه من جانب إلى جانب؛ وهو مدار stride through/by مباشرة، وبقي الصوت وحده ناقصا.", keywords="عبر|جاز|من جانب|قطع"),
    R9.gap("aed-v1.0:37110", "عبر", "SOURCE-GAP", "cult object لا يعين نوع الشيء المقدم، ووصف السياق الطقسي لا يسمي الجسم المقارن."),
    R9.gap("aed-v1.0:37280", "عفا", "SOURCE-GAP", "devour موسوم بالشك إنجليزيا، والألمانية تجمع tear off وdevour؛ لا يدمج الفعلان في مدار مفترض."),
    R9.gap("aed-v1.0:37540", "عمت", "NAME-ROOT-OPEN", "Amet اسم مؤسسة في الألقاب، وAED يتردد في كونها مؤسسة أو معبدا؛ لا يثبت جذر الاسم."),
    R9.gap("aed-v1.0:37710", "عمع", "SOURCE-GAP", "AED يتردد بين جزء تابوت وعصا رمي، ويسم التعيين كله بالشك؛ لا مدار قبل تعيين الشيء."),
    R9.gap("aed-v1.0:37860", "عمم", "SOURCE-GAP", "AED لا يسمي إلا some part of an animal؛ لا ينتق عضو عربي من هيكل وموضع طبي عام."),
    R9.gap("aed-v1.0:37930", "عمق", "SEMANTIC-GAP", "mount sexually/couple لا يطابق العمق والبعد في عمق، ولا تعطي ضمق أو غمق شاهد النكاح والسفاد."),
    R9.gap("aed-v1.0:38130", "عنت", "SEMANTIC-GAP", "claw/talon/thumb لا يطابق حواس عنت أو عنط أو الصور الضادية والغينية، ولا يدخل ظفر من خارج الرسم."),
    R9.gap("aed-v1.0:38240", "عني", "SOURCE-GAP", "قطعة لحم البقر غير مسماة تشريحيا؛ لا ينتق اسم قطعة عربية من الهيكل وحده."),
    R9.gap("aed-v1.0:38370", "عنب", "SOURCE-GAP", "alfa-grass موسوم بالشك في AED؛ لا يصدر مدار نبات معين من تعيين محتمل."),
    R9.gap("aed-v1.0:38540", "عنخ", "SEMANTIC-GAP", "life لا يطابق حواس عنخ أو ضنخ أو غنخ، ولا يدخل حياة بصوامت أخرى."),
    R9.gap("aed-v1.0:38630", "عنخ", "SEMANTIC-GAP", "life بوصفها اسما للمرآة لا يطابق حواس عنخ أو ضنخ أو غنخ، ولا يرث الجسم معنى الاسم."),
    R9.gap("aed-v1.0:38670", "عنخ", "SEMANTIC-GAP", "livelihood لا يطابق حواس عنخ أو ضنخ أو غنخ، ولا يدخل رزق أو معاش من خارج الرسم."),
    R9.gap("aed-v1.0:39240", "عرت", "SEMANTIC-GAP", "jaw لا يطابق حواس عرت أو عرط أو الصور اللامية والضادية والغينية، ولا يدخل فك من خارج الرسم."),
    R9.gap("aed-v1.0:39500", "غلف", "LAW-GAP", "pack/wrap يطابق غلف وأحاط الشيء بغلاف، لكن ꜥ المصرية↔غ العربية بلا صف مصري موقع.", sound="f↔ف هوية IDN-06؛ r المصرية تقرأ /l/ في BR-EGYP-01؛ ꜥ↔غ هي الرجل غير الموقعة.", orbit="غلف الشيء أدخله في الغلاف وغطاه؛ وهو مدار pack/wrap مباشرة، وبقي الصوت وحده ناقصا.", keywords="غلف|غلاف|غطاه|أحاط"),
    R9.pos("aed-v1.0:39660", "عرق", "ROOT-ECHO", "الخوص|سفيفة|زبيل", "ꜥ↔ع في IDN-15، وr↔ر في IDN-01، وq↔ق في IDN-12؛ جذر كامل.", "العرق في العربية السفيفة المنسوجة من الخوص ومنها الزبيل؛ وهو وعاء منسوج يلتقي sack في وظيفة الحمل والاحتواء.", "ECHO لوعاء الحمل المنسوج، لا دعوى أن كل sack زبيل خوص."),
    R9.gap("aed-v1.0:39700", "عرق", "SEMANTIC-GAP", "bandage لا يطابق حواس عرق أو علق أو الصور الضادية والغينية؛ والسفيفة والزبيل في عرق ليسا ضمادا."),
    R9.gap("aed-v1.0:39870", "عحت", "SEMANTIC-GAP", "net stretched for the hunt لا يطابق حواس عحت أو عحط أو الصور الضادية والغينية، ولا يدخل شبك من خارج الرسم."),
    R9.gap("aed-v1.0:39940", "وغي", "LAW-GAP", "warrior يلتقي الوغى وحومة الحرب في مدار المحارب، لكن ꜥ-ḥ-ꜣ المصرية لا تسوي w-gh-y بأي صف مصري موقع.", sound="صوامت الفرع ꜥ-ḥ-ꜣ كاملة؛ لا هوية ولا صف مصري موقع لمواضع و-غ-ي.", orbit="الوغى الحرب وغمغمة الأبطال فيها؛ المحارب حامل حدث الحرب في مدار واحد، وعائق الصوت كامل.", keywords="الوغى|الحرب|الأبطال|حومة"),
    R9.gap("aed-v1.0:40160", "عحع", "SEMANTIC-GAP", "quantity لا يطابق حواس عحع أو عحض أو عحغ وبقية المروحة، ولا يدخل كم أو مقدار من خارج الرسم."),
    R9.gap("aed-v1.0:40230", "عحع", "SEMANTIC-GAP", "height لا يطابق حواس عحع أو عحض أو عحغ وبقية المروحة، ولا يدخل علو بصوامت أخرى."),
    R9.gap("aed-v1.0:40570", "عخي", "SEMANTIC-GAP", "raise/rise up لا يطابق حواس عخي أو عخأ أو الصور الضادية والغينية، ولا يدخل علا بصامت بلا صف."),
    R9.gap("aed-v1.0:40640", "عخم", "SOURCE-GAP", "combustible material غير مسمى وwick نفسها اقتراح بين الأقواس؛ لا مدار قبل تعيين المادة."),
    R9.gap("aed-v1.0:40790", "عخم", "SEMANTIC-GAP", "cause to shudder/inspire fear لا يطابق حواس عخم أو عحم أو الصور الضادية والغينية، ولا يدخل روع من خارج الرسم."),
    R9.gap("aed-v1.0:41030", "عشا", "SOURCE-GAP", "نوع الطائر غير مسمى وdove نفسها موسومة بالشك؛ لا ينتق اسم طائر عربي من الهيكل وحده."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT


def round25_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R24.round24_card(serial, rank, item, decision, matches)
    if decision.member_id == "aed-v1.0:39660":
        witness_line = (
            "- مسح المعاني العربية: قُرئت نتائج الجذر `عرق` الأربع عشرة كاملةً "
            "بما يكافئ `--max-chars 0`؛ قال لسان العرب: «العَرَقُ: "
            "السَّفِيفةُ المنسوجة من الخوص قبل أَن تجعل زَبِيلاً؛ والعَرَقُ "
            "والعَرَقةُ: الزَّبيل مشتق من ذلك»؛ وقال الصحاح: «العَرَقُ: "
            "السفيفةُ المنسوجةُ من الخوص وغيره قبل أن يُجعَلَ منه الزَبيلُ، "
            "ومنه قيل للزبيل عَرَقٌ»."
        )
        card = re.sub(r"(?m)^- مسح المعاني العربية:.*$", witness_line, card)
    card = card.replace("ROUND24-COMPLETION", "ROUND25-COMPLETION")
    card = card.replace(
        "ROUND25-COMPLETION (2026-08-24)",
        "ROUND25-COMPLETION (2026-08-25)",
    )
    card = card.replace(
        f"round24-egyptian-rank={rank}/{CARD_COUNT}",
        f"round25-egyptian-rank={rank}/{CARD_COUNT}",
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
        raise SystemExit("Round-twenty-five marker already exists; append refused.")

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
        round25_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الخامسة والعشرون: استمرار المخزون المصري المسجل المفتوح (2026-08-25)", "",
        (
            "أعيد فحص الآرامية أولا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرا، فسجل الانتقال المسمى `{TRANSITION}`. انتقيت ثمانون "
            "بطاقة مصرية بدءا من `WO-C-OPEN-COMP-01263` بقصر الهيكل ثم موضع "
            "اللقطة. استبعد صف ḏ المؤجل. في كل بطاقة عرضت إصابات AED كلها بلا "
            "حد، وكتب وسم الطريق والرسم والمدخل المختار، وحفظ الاختلاف "
            "والمتجانسات بلا محو."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-01263 إلى WO-C-OPEN-COMP-01302", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-01303 إلى WO-C-OPEN-COMP-01342", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([f"<!-- LANE-C-R25-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    states = dict(sorted(collections.Counter(item.state for item in DECISIONS).items()))
    verdicts = dict(sorted(collections.Counter(item.verdict for item in DECISIONS).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    now = datetime.now(ZoneInfo("Africa/Cairo")).strftime("%Y-%m-%d %H:%M:%S %z")
    now = now[:-2] + ":" + now[-2:]
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة الخامسة والعشرون: المسار C، الساميات والمصرية (2026-08-25)", "",
        f"- الوقت: {now}.",
        "- أعيد فحص الساميات أولا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01263` إلى `WO-C-OPEN-COMP-01302`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01303` إلى `WO-C-OPEN-COMP-01342`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طبقت قواعد AED الثلاث: كل الإصابات بلا حد؛ وسم الطريق والرسم والمدخل المختار مكتوبة؛ الاختلاف والمتجانسات محفوظة بلا محو.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}؛ لا فجوة حولت إلى نفي.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ الموجب مقصور على عضو AED المختار ومداره المكتوب.",
        "- الموجب: `ꜥrq↔عرق` في وعاء الحمل المنسوج، بمسار الجذر الكامل `IDN-15 + IDN-01 + IDN-12`.",
        "- المطابقات الدلالية ذوات الرجل الصوتية الناقصة بقيت مفتوحة: `jnj↔أني` و`ꜥꜣ.t↔علا` و`ꜥꜣp↔عاب` و`ꜥpi̯↔عبر` و`ꜥrf↔غلف` و`ꜥḥꜣ↔وغي`.",
        "- أداة الشرط `jnn` أغلقت `OUT-OF-SCOPE`، والأعلام والمداخل المجهولة أو المشكوكة بقيت بأوسمتها المفتوحة.",
        "- صف ḏ المصري المؤجل بقي مستبعدا، ولا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE25 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
        R24.R23.R20.R10.append(EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian)
        R24.R23.R20.R10.append(REPORT, f"{MARKER}:REPORT", report)
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
