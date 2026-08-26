#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 33 completion cards without shipping or git.

The live short Aramaic queue is checked before the registered Egyptian open
queue continues. The script completes WO-C-OPEN-COMP-01903..01982 in two
forty-card batches and accepts only the current closed closure vocabulary.
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

import harvest_lane_c_round32 as R32


R9 = R32.R9
AR = R32.AR
ROOT = R32.ROOT
ARAMAIC = R32.ARAMAIC
EGYPTIAN = R32.EGYPTIAN
REPORT = R32.REPORT

MARKER = "LANE-C-ROUND33-2026-08-26"
FIRST_SERIAL = 1903
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)
LEGAL_CLOSURES = R32.LEGAL_CLOSURES


def gap(member_id: str, candidate: str, state: str, reason: str,
        sound: str = "المروحة بنيوية فقط؛ لا يرقى التشابه إلى قانون أو نسب.",
        orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
        keywords: str = "", zero: str = "") -> R9.Decision:
    return R32.gap(
        member_id, candidate, state, reason, sound, orbit, keywords, zero,
    )


def pos(member_id: str, candidate: str, verdict: str, keywords: str,
        sound: str, orbit: str, reason: str,
        zero: str = "") -> R9.Decision:
    return R32.pos(
        member_id, candidate, verdict, keywords, sound, orbit, reason, zero,
    )


def terminal(member_id: str, candidate: str, verdict: str, reason: str,
             zero: str = "") -> R9.Decision:
    return R32.terminal(member_id, candidate, verdict, reason, zero)


# One member has a complete signed sound route, a frozen event, two old Arabic
# witnesses, and a bounded semantic orbit. Direct semantic contacts with an
# incomplete Egyptian sound route remain named gaps. Uncertain and unnamed AED
# referents remain source gaps; compounds and function-like phrases are isolated
# structurally.
DECISIONS: tuple[R9.Decision, ...] = (
    gap("aed-v1.0:37780", "عمعم", "OPEN-CANDIDATE", "rub the feet لا يطابق عمعم أو عمضم أو غمغم في العربية الممسوحة، ولا يدخل دلك أو فرك من خارج الرسم."),
    gap("aed-v1.0:38740", "عنخت", "OPEN-CANDIDATE", "living eye لقب ديني للعين الإلهية، ولا يطابق عنخت أو عنخ ولا نظائر الضاد والغين دلالة عربية عاملة."),
    gap("aed-v1.0:39790", "عرت", "SOURCE-GAP", "المسطح المائي في صعيد مصر غير مسمى وكل التعريف بين أقواس، واقتراح floodwater موسوم بالشك؛ لا مرجع مائي واحدا محسوما."),
    gap("aed-v1.0:40430", "عحع", "OPEN-CANDIDATE", "nape/spinal ridge لا يطابق عحع أو عحض ولا صور الضاد والغين، ولا يدخل قفا أو صلب من خارج الرسم."),
    gap("aed-v1.0:42810", "ورب", "OPEN-CANDIDATE", "أسفل التاج الأحمر في مقابلة curl جزء ثقافي مخصوص، ولا يطابق ورب أو ولب في العربية الممسوحة."),
    gap("aed-v1.0:44060", "ويا", "SOURCE-GAP", "عرض علة القلب غير مسمى وكل التعريف بين أقواس؛ لا حدث أو عضو مرضي معين يقارن بويا أو ويل."),
    gap("aed-v1.0:44560", "وعب", "OPEN-CANDIDATE", "meat/flesh لا يطابق وعب في الاستيعاب والأخذ أجمع، ولا يحول اكتمال الأخذ إلى اسم للحم القربان.", sound="w↔و وꜥ↔ع وb↔ب ظاهرة منفردة؛ بقيت الدلالة هي العائق.", orbit="وعب الشيء أخذه أجمع واستوعبه، أما المصرية فتسمي اللحم نفسه؛ لا مدار معجميا واحدا."),
    gap("aed-v1.0:44740", "وعر", "OPEN-CANDIDATE", "leg لا يطابق وعر في صلابة المكان وخشونته، ولا يدخل ساق أو رجل من خارج الرسم."),
    gap("aed-v1.0:44780", "وعر", "SOURCE-GAP", "المسطح المائي الأخروي غير مسمى وكل التعريف بين أقواس؛ لا نهر أو بحيرة معينة يقوم عليها مدار عربي."),
    gap("aed-v1.0:45110", "وبن", "OPEN-CANDIDATE", "webenet اسم مصري لرباط مومياء عند الرأس، ولا يطابق وبن في العربية الممسوحة ولا يورث معنى الرباط من الشرح."),
    gap("aed-v1.0:45280", "وبخ", "OPEN-CANDIDATE", "clarity of the eye لا يطابق وبخ في اللوم والتقريع، ولا يدخل صفو أو وضوح من خارج الرسم."),
    terminal("aed-v1.0:45590", "∅", "COMPOUND-BOUNDARY", "Opening-of-the-mouth اسم شعيرة مركب؛ حد العبارة الطقسية يمنع حملها على جذر عربي مفرد."),
    terminal("aed-v1.0:45620", "∅", "COMPOUND-BOUNDARY", "first-born محلل صراحة إلى opener of the womb؛ حد المركب يفصل الوصف الولادي عن جذر عربي مفرد."),
    terminal("aed-v1.0:46230", "∅", "COMPOUND-BOUNDARY", "Revealing-the-face اسم عيد أو طقس مركب؛ لا يحمل مجموع الكشف والوجه على مادة عربية واحدة."),
    gap("aed-v1.0:46750", "ونم", "OPEN-CANDIDATE", "right eye اصطلاح جانبي للعين الإلهية، ولا يطابق ونم في العربية الممسوحة ولا يدخل يمين أو عين من خارج الرسم."),
    gap("aed-v1.0:46790", "ونم", "OPEN-CANDIDATE", "right hand لا يطابق ونم في العربية الممسوحة، ولا يدخل يمين أو يد من خارج الرسم."),
    gap("aed-v1.0:47860", "ورم", "SOURCE-GAP", "جزء الجسم نفسه غير مسمى واقتراح testicles بين أقواس وعلامة شك؛ لا عضو تشريحي واحدا محسوما."),
    gap("aed-v1.0:47950", "ورر", "SOURCE-GAP", "AED لا يعين إلا part of the body مع علامة شك؛ لا ينتخب عضوا عربيا من ورر أو ورل قبل تعيين المرجع."),
    gap("aed-v1.0:48590", "وهنن", "OPEN-CANDIDATE", "crown of the head لا يطابق وهنن أو وحنن في العربية الممسوحة، ولا يدخل هامة أو قمة من خارج الرسم."),
    gap("aed-v1.0:48680", "وحر", "SOURCE-GAP", "مرض العين غير مسمى وكل التعريف بين أقواس؛ لا علة معينة تقارن بوحر أو وحل."),
    gap("aed-v1.0:49560", "وزم", "SOURCE-GAP", "جزء الجسم البشري غير مسمى، والألمانية لا تقترح إلا innards بعلامة شك؛ لا عضو واحدا محسوما."),
    gap("aed-v1.0:49650", "وصل", "OPEN-CANDIDATE", "العربية تسمي بالموصل ما بين عجز البعير وفخذه وتسمّي الأوصال المفاصل، لا neck/nape؛ التشابه التشريحي العام لا يسوي المواضع.", sound="w↔و ظاهر؛ s-r المصرية بإزاء ص-l العربية بلا مسار مصري موقع للعضو.", orbit="الموصل والمفصل موضع اتصال تشريحي، لكنه بين العجز والفخذ لا العنق؛ بقي الموضع والصوت مانعين.", keywords="الموصل|العجز|الفخذ|المفاصل"),
    gap("aed-v1.0:49690", "وصل", "OPEN-CANDIDATE", "mighty one بوصف العين لا يطابق وصل في الاتصال والمفاصل، ولا يدخل قوة أو عين من خارج الرسم."),
    gap("aed-v1.0:50000", "وستن", "SOURCE-GAP", "المسطح المائي نفسه موسوم بالشك وكل التعريف بين أقواس؛ لا مرجع مائي معين للمقارنة."),
    gap("aed-v1.0:51190", "وطن", "SOURCE-GAP", "AED يتردد بين body of water في السماء وشيء سماوي غير معين، وكلاهما بين أقواس؛ لا مرجع واحدا محسوما."),
    gap("aed-v1.0:53580", "برح", "SOURCE-GAP", "white of the eye نفسها موسومة بالشك؛ لا جزء عيني محسوما يقارن ببرح أو بلح أو باخ."),
    gap("aed-v1.0:54420", "بيا", "SOURCE-GAP", "جزء الجسم غير مسمى وكل التعريف بين أقواس؛ لا ينتخب عضو عربي من بيا أو بيل أو بير."),
    gap("aed-v1.0:54550", "بيب", "SOURCE-GAP", "تسمية الطفل في الرحم محاطة بالأقواس ولا يثبت AED هل هي اسم الجنين أو وصف مرحلي؛ لا مادة عربية محكومة."),
    gap("aed-v1.0:54750", "بيض", "SOURCE-GAP", "علة العين غير مسماة وكل التعريف بين أقواس؛ لا يجوز توريث البياض أو البيضة للعضو قبل تعيين المرض."),
    gap("aed-v1.0:61340", "بحر", "DIRECTION-GAP", "body of water يطابق البحر دلاليا وAED يوسم العضو قرضا ساميا، لكنه لا يسمي مانحا فرديا أو طريق انتقال ولا يوقع h↔ح.", sound="p↔ب في LAB-01 وr↔ر في IDN-01؛ h المصرية بإزاء ح العربية هي الرجل غير الموقعة، و.t باقية اسما.", orbit="البحر هو الماء الكثير وكل نهر عظيم بحر؛ وهو مدار body of water مباشرة، وبقي الصوت والاتجاه التاريخي مانعين.", keywords="البحر|الماء الكثير|النهر|الأنهار"),
    gap("aed-v1.0:61490", "فحو", "OPEN-CANDIDATE", "end/back لا يطابق فحوى القول في معناه ومذهبه ولا الفحا في الأبازير، ولا يدخل آخر أو خلف من خارج الرسم."),
    gap("aed-v1.0:61870", "بخبخ", "SOURCE-GAP", "الإنجليزية تسمي جريان السم في الجسد، والألمانية تجمع الدوران والتمزيق والنزع والاندفاع؛ لا حدث رباعي واحدا محسوما."),
    gap("aed-v1.0:64080", "فك", "OPEN-CANDIDATE", "one with a shaved head لقب كاهن، ولا يطابق فك في الفصل والحل ولا يجعل الحلق فكا للشيء."),
    gap("aed-v1.0:68500", "ميس", "SOURCE-GAP", "الجزء البارز خلف التاج الأحمر غير مسمى وكل التعريف بين أقواس؛ لا ينتخب اسم جزء عربي من ميس أو ميش."),
    gap("aed-v1.0:68910", "معح", "SOURCE-GAP", "fighter with the arm لا يحسم هل المرجع مقاتل أم ذراع قتال، والألمانية موسومة بالشك؛ لا اسم شخص أو عضو واحدا."),
    gap("aed-v1.0:70290", "منيء", "SOURCE-GAP", "الإنجليزية لا تعين إلا part of the body، والألمانية تسمي pulse point؛ اختلاف درجتي التعيين يمنع اختيار عضو عربي."),
    gap("aed-v1.0:75640", "مسخ", "SOURCE-GAP", "المسطح المائي غير مسمى وموسوم بالشك بين الأقواس؛ لا بحر أو حوض معين يقارن بمسخ أو مشخ."),
    gap("aed-v1.0:77100", "مكحء", "OPEN-CANDIDATE", "back of the head لا يطابق مكحء أو مكحا ولا صور اللام والراء، ولا يدخل قفا من خارج الرسم."),
    gap("aed-v1.0:79200", "نمحف", "SOURCE-GAP", "الحجر المستعمل لجعارين القلب غير مسمى وكل التعريف بين أقواس؛ لا معدن أو حجر معين يقوم عليه المدار."),
    gap("aed-v1.0:82910", "نبد", "OPEN-CANDIDATE", "plait/tresses لا يطابق نبد في السكون والركود، ولا يدخل ضفيرة أو جديلة من خارج الرسم."),
    gap("aed-v1.0:86210", "نحب", "OPEN-CANDIDATE", "neck/nape لا يطابق نحب في النذر والبكاء والسعال، ولا يكفي ورود العنق في شرح مجازي لقضاء النحب."),
    gap("aed-v1.0:88020", "نسا", "SOURCE-GAP", "إصابة فقرة العنق غير مسماة وكل التعريف بين أقواس؛ وعرق النسا يمتد من الورك إلى الرجل فلا يعين مرض العنق."),
    gap("aed-v1.0:88360", "نسسق", "SOURCE-GAP", "علة الرأس غير مسماة واقتراح hair loss موسوم بالشك؛ لا مرض واحدا محسوما للمقارنة."),
    gap("aed-v1.0:89430", "نكك", "OPEN-CANDIDATE", "wounded eye لا يطابق نكك في العربية الممسوحة، ولا يدخل جرح أو عين من خارج الرسم."),
    gap("aed-v1.0:89580", "نقر", "OPEN-CANDIDATE", "belly/womb لا يطابق نقر في الثقب والضرب والالتقاط، ولا تدخل بطن أو رحم من خارج الرسم."),
    gap("aed-v1.0:90060", "نتن", "OPEN-CANDIDATE", "skin لا يطابق نتن في تغير الرائحة والفساد، ولا يجعل فساد الجلد اسما للبشرة نفسها."),
    gap("aed-v1.0:90310", "نثر", "OPEN-CANDIDATE", "sacred eye لقب ديني، ولا يطابق نثر في التفريق والانتشار ولا نظائر التاء والطاء دلالة العين."),
    gap("aed-v1.0:90450", "نثر", "OPEN-CANDIDATE", "heart of gods or kings لا يطابق نثر أو نتر أو نطر، ولا يدخل قلب من خارج الرسم."),
    terminal("aed-v1.0:92970", "∅", "COMPOUND-BOUNDARY", "mouth of the Nile تركيب إضافي جغرافي؛ حد المركب يمنع حمل المصب كله على جذر عربي مفرد."),
    terminal("aed-v1.0:93020", "∅", "COMPOUND-BOUNDARY", "crocodile محلل صراحة إلى mouth-of-terror؛ الاسم الوصفي المركب لا يرد إلى جذر عربي مفرد."),
    terminal("aed-v1.0:93030", "∅", "COMPOUND-BOUNDARY", "lion محلل صراحة إلى mouth-of-terror؛ لا يحمل المركب كله على جذر عربي واحد ولا يورث حكم عضو التمساح المجاور."),
    gap("aed-v1.0:97980", "حوت", "OPEN-CANDIDATE", "sailer/ship's hand لا يطابق حوت اسم الحيوان البحري ولا حوط في الإحاطة، ولا يدخل ملاح من خارج الرسم."),
    gap("aed-v1.0:100400", "حرت", "OPEN-CANDIDATE", "heart لا يطابق حرت أو حلت ولا نظائر الطاء والراء، ولا يدخل قلب من خارج الرسم."),
    gap("aed-v1.0:100410", "حرت", "SOURCE-GAP", "الوسام القلبي الشكل لعمل غير عسكري غير مسمى وكل التعريف بين أقواس؛ لا قطعة حلي واحدة محكومة."),
    terminal("aed-v1.0:100480", "∅", "COMPOUND-BOUNDARY", "sorrow/sickness of heart عبارة مركبة محفوظة في الرسم ḥꜣ-jb؛ لا يحمل مجموع العلة والقلب على جذر عربي مفرد."),
    gap("aed-v1.0:101020", "حءعع", "SOURCE-GAP", "AED لا يعين إلا part of the body بين أقواس؛ لا ينتخب عضوا عربيا من حءعع أو حاعع."),
    gap("aed-v1.0:101130", "حور", "OPEN-CANDIDATE", "face of a god لا يطابق حور في شدة بياض العين وسوادها ولا بقية حواس حور، ولا تسوى العين بالوجه."),
    gap("aed-v1.0:101510", "حاحا", "SOURCE-GAP", "علة القلب أو نشاطه المرضي غير مسمى وكل التعريف بين أقواس؛ لا حدث طبي واحدا محسوما."),
    gap("aed-v1.0:107220", "حنك", "OPEN-CANDIDATE", "braided lock of hair لا يطابق الحنك في باطن الفم ولا التحنيك والرسن، ولا يدخل ضفيرة من خارج الرسم."),
    terminal("aed-v1.0:108020", "∅", "COMPOUND-BOUNDARY", "everyone محلل صراحة إلى every face؛ التركيب الكمي الوظيفي لا يحمل على جذر عربي مفرد."),
    gap("aed-v1.0:111060", "حتر", "OPEN-CANDIDATE", "blotches on the face لا تطابق حتار الشيء في كفافه وحافته، ولا تدخل بقع أو كلف من خارج الرسم."),
    gap("aed-v1.0:111160", "حتي", "OPEN-CANDIDATE", "throat لا يطابق حتي في خياطة الثوب أو فتله ولا أسماء الطعام والمتاع، ولا يدخل حلق من خارج الرسم."),
    gap("aed-v1.0:111900", "حتر", "SOURCE-GAP", "AED يجمع body of water وterritory مع hinge/junction وكلها موسومة بالشك؛ لا مرجع جغرافي واحدا محسوما."),
    gap("aed-v1.0:117840", "خنوس", "SOURCE-GAP", "علة القلب غير مسماة، واقتراح stabbing نفسه بين أقواس وعلامة شك؛ لا مرض أو حدث واحدا للمقارنة."),
    pos("aed-v1.0:120920", "خسف", "ROOT-ECHO", "خسفت العين|عين خاسفة|غابت حدقتها|فقأها", "ḫ↔خ في IDN-17 وs↔س في IDN-07 وf↔ف في IDN-06؛ الجذر الكامل محفوظ بعد عزل اللاحقة الاسمية .w.", "خسفت العين إذا ساخت أو غابت حدقتها، والعين الخاسفة مفقوءة أو غائرة؛ وهو مدار علة العين أو عرضها مباشرة.", "ECHO مقصور على غؤور العين وذهاب حدقتها في العضو الطبي المختار؛ لا مساواة كل مرض عيني بالخسف.", zero="عزلت .w بوصفها اللاحقة الاسمية المفصولة بالنقطة في رسم AED؛ بقي ḫ-s-f كاملا، ولم تسقط صامتة جذرية."),
    gap("aed-v1.0:120960", "خسف", "OPEN-CANDIDATE", "sail upstream/face/meet لا يطابق خسف في غؤور الأرض والعين، ولا يحول المقابلة المكانية إلى خسف."),
    gap("aed-v1.0:121890", "ختخ", "OPEN-CANDIDATE", "turn back/drive away لا يطابق ختخ أو خطخ في العربية الممسوحة، ولا يدخل رد أو دفع من خارج الرسم."),
    gap("aed-v1.0:122820", "سلخ", "LAW-GAP", "مسلاخ الحية هو قشرها الذي تنسلخ منه فيطابق skin shed by a snake، لكن ẖ-ꜥ-q المصرية لا تقدم مسارا إلى س-l-ḫ العربية.", sound="لا رجل صوتية مصرية موقعة تجمع ẖ-ꜥ-q بإزاء س-l-ḫ؛ المقابلة مرفوعة دلاليا خارج سطح المروحة.", orbit="سلخت الحية جلدها وانسلخت منه، ومسلاخها قشرها؛ وهو معنى الجلد المطروح نفسه، وبقي الصوت كله مانعا.", keywords="مسلاخ الحية|قشرها|سلخ جلدها|انسلخت"),
    gap("aed-v1.0:124720", "حقص", "OPEN-CANDIDATE", "injured eye of Horus لا يطابق حقص أو خقص ولا نظائر السين والشين، ولا يدخل جرح أو عين من خارج الرسم."),
    gap("aed-v1.0:126400", "وصل", "LAW-GAP", "موصل البعير ما بين عجزه وفخذه يطابق الجزء بين العمود والحوض، لكن z-ꜣ-w المصرية بإزاء w-ṣ-l تحتاج قلبا وتقابلين غير موقعين.", sound="w↔و ظاهر لكنه منقول من ثالث المصري إلى أول العربي؛ z↔ص وꜣ↔ل غير موقعين، فلا مسار عضو كامل.", orbit="الموصل بين العجز والفخذ موضع الوصلة الخلفية، وهو مدار الجزء بين العمود والحوض مباشرة، وبقي ترتيب الصوت وتقابله مانعين.", keywords="موصل البعير|العجز|الفخذ|الأوصال"),
    gap("aed-v1.0:126540", "روي", "OPEN-CANDIDATE", "keep an eye on لا يطابق روي أو لوي ولا صور ساوي وشاوي في العربية الممسوحة، ولا يدخل رعى أو راقب من خارج الرسم."),
    gap("aed-v1.0:126640", "لبي", "OPEN-CANDIDATE", "gladden the heart لا يطابق لبي أو ربي ولا صور سابي وشابي وصابي، ولا يدخل فرح أو سر من خارج الرسم."),
    gap("aed-v1.0:126780", "صرم", "OPEN-CANDIDATE", "disheveled mourning hair لا يطابق صرم في القطع ولا سرم وبقية المروحة، ولا يجعل قطع الشعر تسريحة حداد غير ممسوحة."),
    gap("aed-v1.0:127250", "سلسل", "OPEN-CANDIDATE", "drive back/repel لا يطابق سلسل أو صلصل أو رسا ورسل في المروحة المقروءة، ولا يدخل دفع أو رد من خارج الرسم."),
    gap("aed-v1.0:130060", "ثوب", "DIRECTION-GAP", "ثاب الرجل أي رجع بعد ذهابه يطابق draw back، وAED يوسم العضو قرضا ساميا، لكنه لا يسمي مانحا أو طريقا ويترك s↔ث والتضعيف الأخير بلا تفسير.", sound="w↔و وb↔ب ظاهران؛ s المصرية بإزاء ث العربية وb الأخيرة المضعفة بلا مسار مصري موقع.", orbit="ثاب الشيء رجع بعد ذهابه، وهو مدار draw back مباشرة، وبقي الصوت والاتجاه التاريخي مانعين.", keywords="ثاب|رجع|عاد|بعد ذهابه"),
    gap("aed-v1.0:130340", "ونف", "OPEN-CANDIDATE", "make the heart rejoice لا يطابق ونف أو سونف وشونف وصونف في العربية الممسوحة، ولا يدخل فرح من خارج الرسم."),
    gap("aed-v1.0:131570", "صبا", "LAW-GAP", "الصبا ريح تهب من مطلع الشمس وتستقبل القبلة فتطابق head wind، لكن s-b-y المصرية بإزاء ṣ-b-w العربية يترك s↔ص وy↔و بلا صفين موقعين.", sound="b↔ب في IDN-05؛ s↔ص وy↔واو صبا هما الرجلان غير الموقعتين، و.t علامة اسمية سطحية.", orbit="الصبا ريح المشرق المستقبلة للقبلة، وهو مدار head wind مباشرة بحسب جهة المواجهة، وبقي الصوت مانعا.", keywords="الصبا|ريح|مطلع الشمس|مستقبلة للقبلة"),
    gap("aed-v1.0:133010", "سبخ", "SOURCE-GAP", "الإنجليزية تجمع purge مع جعل الجلد sleek المشكوك، والألمانية تجمع الفتح والإسهال والتنظيف؛ لا حدث واحدا محسوما، وسبخ العربية للتخفيف لا للتطهير."),
    gap("aed-v1.0:133120", "سبسب", "SOURCE-GAP", "tie up by the hair موسومة بالشك، والألمانية تعطي tousle لا الربط؛ اختلاف الحدثين يمنع مدارا رباعيا واحدا."),
    gap("aed-v1.0:139540", "سرم", "SOURCE-GAP", "المسطح المائي غير مسمى وكل التعريف بين أقواس؛ لا نهر أو حوض معين يقارن بسرم أو صرم أو سلم."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT
assert {item.state for item in DECISIONS} <= LEGAL_CLOSURES
assert {item.verdict for item in DECISIONS} <= LEGAL_CLOSURES

OUTSIDE_FAN = {
    "aed-v1.0:122820", "aed-v1.0:126400", "aed-v1.0:130060",
    "aed-v1.0:131570",
}

WITNESS_NOTES = {
    "aed-v1.0:49650": "أثبتت المعاجم الموصل بين عجز البعير وفخذه والأوصال في المفاصل؛ ثبت تماس تشريحي عام لا neck، وبقي الموضع والصوت مانعين.",
    "aed-v1.0:61340": "أثبتت المعاجم البحر في الماء الكثير وكل نهر عظيم؛ ثبت مدار body of water، وبقي h↔ح والمانح والطريق مفتوحة.",
    "aed-v1.0:120920": "أثبت كتاب العين والصحاح خسوف العين في غؤورها وذهاب حدقتها؛ ثبت مدار العلة العينية بشاهدين قديمين مستقلين.",
    "aed-v1.0:122820": "أثبت الصحاح والمفردات مسلاخ الحية وقشرها الذي تنسلخ منه؛ ثبت الجلد المطروح، وبقي المسار الصوتي كله مفتوحا.",
    "aed-v1.0:126400": "أثبت كتاب العين والمفردات أن موصل البعير ما بين عجزه وفخذه؛ ثبت المدار التشريحي، وبقي ترتيب الصوامت وتقابلها مانعين.",
    "aed-v1.0:130060": "أثبت الصحاح ولسان العرب أن ثاب الرجل رجع بعد ذهابه؛ ثبت مدار draw back، وبقي الصوت والمانح والطريق مفتوحة.",
    "aed-v1.0:131570": "أثبت الصحاح والمفردات أن الصبا ريح المشرق المستقبلة للقبلة؛ ثبت مدار head wind، وبقي s-b-y↔ṣ-b-w غير مكتمل.",
}


def round33_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R32.round32_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND32-COMPLETION", "ROUND33-COMPLETION")
    card = card.replace(
        f"round32-egyptian-rank={rank}/{CARD_COUNT}",
        f"round33-egyptian-rank={rank}/{CARD_COUNT}",
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
        raise SystemExit("Round-thirty-three marker already exists; append refused.")

    aramaic_exact, _ = R9.load_entries("aramaic")
    aramaic_queue = R9.select_aramaic(aramaic_text, aramaic_exact)
    assert not aramaic_queue, (
        "Aramaic short live-open queue is no longer exhausted: "
        f"{[item['entry_id'] for item in aramaic_queue[:10]]}"
    )

    egyptian_exact, _ = R9.load_entries("egyptian")
    queue = R32.R31.R30.R29.select_egyptian_fast(egyptian_text, egyptian_exact)
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
        round33_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الثالثة والثلاثون: استمرار المخزون المصري المسجل المفتوح (2026-08-26)", "",
        (
            "أعيد فحص الآرامية أولا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرا، فسجل الانتقال المسمى `{TRANSITION}`. انتقيت ثمانين "
            "بطاقة مصرية بدءا من `WO-C-OPEN-COMP-01903` بقصر الهيكل ثم موضع "
            "اللقطة. استبعد صف ḏ المؤجل. في كل بطاقة عرضت إصابات AED كلها بلا "
            "حد، وكتب وسم الطريق والرسم والمدخل المختار، وحفظ الاختلاف "
            "والمتجانسات بلا محو. فحصت حالة الإغلاق والحكم آليا على القائمة "
            "القانونية وحدها في `data/closure-vocabulary.json`."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-01903 إلى WO-C-OPEN-COMP-01942", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-01943 إلى WO-C-OPEN-COMP-01982", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([
                f"<!-- LANE-C-R33-EGYPTIAN-CHUNK-{rank:03d}:END -->", "",
            ])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    states = dict(sorted(collections.Counter(
        item.state for item in DECISIONS
    ).items()))
    verdicts = dict(sorted(collections.Counter(
        item.verdict for item in DECISIONS
    ).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    now = datetime.now(ZoneInfo("Africa/Cairo")).strftime(
        "%Y-%m-%d %H:%M:%S %z"
    )
    now = now[:-2] + ":" + now[-2:]
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة الثالثة والثلاثون: المسار C، الساميات والمصرية (2026-08-26)", "",
        f"- الوقت: {now}.",
        "- أعيد فحص الساميات أولا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01903` إلى `WO-C-OPEN-COMP-01942`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01943` إلى `WO-C-OPEN-COMP-01982`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طبق الانضباط الثلاثي: الموجب له صوت موقع وحدث مجمد ومدار مكتوب؛ وكل بطاقة أخرى لها عائق شريف مسمى.",
        "- قاموس الإغلاق المغلق وحده مطبق: كل حالات الإغلاق والأحكام اجتازت القائمة القانونية في `data/closure-vocabulary.json`.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ الموجب مقصور على العضو ومداره المكتوب.",
        "- الموجب: `ḫsf.w↔خسف` في غؤور العين وذهاب حدقتها، بجذر كامل `IDN-17 + IDN-07 + IDN-06`، وحكمه `ROOT-ECHO`.",
        "- المطابقات الدلالية المرفوعة بقيت فجوات قانون: `ẖꜥq.t↔سلخ` للجلد المطروح، و`zꜣw.t↔وصل` للموصل الخلفي، و`sby.t↔صبا` لريح المواجهة.",
        "- وسما القرض السامي في `phr.t↔بحر` و`swbb↔ثوب` بقيا `DIRECTION-GAP` بلا مانح فردي أو طريق وصوت مكتملين.",
        "- المركبات الطقسية والتشريحية والوصفية الثمانية أغلقت `COMPOUND-BOUNDARY`، والألفاظ والمراجع المشكوكة أو غير المسماة بقيت `SOURCE-GAP`.",
        "- صف ḏ المصري المؤجل بقي مستبعدا؛ لم يحدث شحن أو إيداع أو إعداد مرحلي، ولم يستعمل git أو تحدث مشتقات النشر.", "",
        f"LANE-C DONE33 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
    egyptian_appendix = unicodedata.normalize(
        "NFC", "\n".join(body).rstrip() + "\n",
    )
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
        R32.R31.R30.R29.R28.R27.R26.R25.R24.R23.R20.R10.append(
            EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian,
        )
        R32.R31.R30.R29.R28.R27.R26.R25.R24.R23.R20.R10.append(
            REPORT, f"{MARKER}:REPORT", report,
        )
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
