#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 34 completion cards without shipping or git.

The live short Aramaic queue is checked before the registered Egyptian open
queue continues. The script completes WO-C-OPEN-COMP-01983..02062 in two
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

import harvest_lane_c_round33 as R33


R9 = R33.R9
AR = R33.AR
ROOT = R33.ROOT
ARAMAIC = R33.ARAMAIC
EGYPTIAN = R33.EGYPTIAN
REPORT = R33.REPORT

MARKER = "LANE-C-ROUND34-2026-08-26"
FIRST_SERIAL = 1983
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)
LEGAL_CLOSURES = R33.LEGAL_CLOSURES


def gap(member_id: str, candidate: str, state: str, reason: str,
        sound: str = "المروحة بنيوية فقط؛ لا يرقى التشابه إلى قانون أو نسب.",
        orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
        keywords: str = "", zero: str = "") -> R9.Decision:
    return R33.gap(
        member_id, candidate, state, reason, sound, orbit, keywords, zero,
    )


def pos(member_id: str, candidate: str, verdict: str, keywords: str,
        sound: str, orbit: str, reason: str,
        zero: str = "") -> R9.Decision:
    return R33.pos(
        member_id, candidate, verdict, keywords, sound, orbit, reason, zero,
    )


def terminal(member_id: str, candidate: str, verdict: str, reason: str,
             zero: str = "") -> R9.Decision:
    return R33.terminal(member_id, candidate, verdict, reason, zero)


# The two jmn.t members alone have a complete signed sound route, a frozen
# event, two independent old Arabic witnesses, and a bounded right-side orbit.
# Direct semantic contacts with a missing sound leg remain named gaps. Uncertain
# referents, one-source contacts, compounds, function words, and named cultural
# labels are kept outside the positive count.
DECISIONS: tuple[R9.Decision, ...] = (
    gap("aed-v1.0:142410", "سخمخ", "OPEN-CANDIDATE", "distract the heart/entertain لا يطابق سخمخ أو شخمخ أو صخمخ في العربية الممسوحة، ولا يدخل لهو أو فرح من خارج الرسم."),
    gap("aed-v1.0:143230", "سخت", "SOURCE-GAP", "لحم طير الماء المصيد بالشراك موسوم بالشك في الإنجليزية والألمانية؛ لا يثبت هل المرجع لحم نوع بعينه أو وصف صيد محكوم."),
    gap("aed-v1.0:145100", "سسم", "SOURCE-GAP", "تعيين العين بالقمر نفسه مشكوك، والألمانية تضع Mondauge كلها بين أقواس؛ لا عضو عيني محسوما يقارن بسشم أو سسم."),
    gap("aed-v1.0:145200", "حمم", "LAW-GAP", "حم الماء أي سخنه يطابق warm، لكن بعد عزل s السببية تبقى š المصرية بإزاء ح العربية بلا صف مصري موقع.", sound="m↔م في IDN-02 في الموضعين الأخيرين؛ š↔ح هي الرجل المصرية غير الموقعة بعد عزل السابقة السببية.", orbit="حم الماء أي سخنه، والحميم الماء الحار؛ وهو مدار warm مباشرة، وبقي الصوت الأول من الجذر مانعا.", keywords="حممت الماء|سخنته|الحميم|الماء الحار", zero="عزلت s الأولى بوصفها السابقة السببية المسماة في `verb_caus_2-gem`؛ بقي š-m-m كاملا ولم تسقط صامتة جذرية."),
    gap("aed-v1.0:147310", "سجرج", "SOURCE-GAP", "yard arm نفسها موسومة بالشك في الإنجليزية؛ لا يثبت AED أي ذراع صارية أو قطعة سفينة بعينها تقارن بسجرج أو صور المروحة."),
    gap("aed-v1.0:148820", "سثءت", "SOURCE-GAP", "الصندوق الخشبي والجر على مزلاق كلاهما بين أقواس التحرير؛ لا وعاء أو وسيلة نقل واحدة محكومة للمقارنة."),
    terminal("aed-v1.0:149080", "∅", "COMPOUND-BOUNDARY", "الرسم `sṯj-rʾ` ذو حدين موصولين ويعرّف fragrance of the mouth؛ حد تركيب الرائحة والفم يمنع حمل العبارة على جذر عربي مفرد."),
    gap("aed-v1.0:149440", "سثءز", "OPEN-CANDIDATE", "lie stretched out on the back لا يطابق سثءز ولا تلز أو ترس أو طرس في المروحة المقروءة، ولا يدخل بسط أو استلقاء من خارج الرسم."),
    gap("aed-v1.0:151860", "شءرو", "SOURCE-GAP", "علة العين غير مسماة، واقتراح العشى الليلي نفسه موسوم بالشك؛ لا مرض عيني واحدا محسوما للمقارنة."),
    gap("aed-v1.0:156060", "شنب", "OPEN-CANDIDATE", "الصدر الأمامي أو الحلق لا يطابق شنب الذي يدور على ماء الأسنان وحدتها وعذوبتها، ولا تسوي مجاورة الفم عضوي الصدر والحلق."),
    gap("aed-v1.0:156340", "سنط", "OPEN-CANDIDATE", "hair لا يطابق سنط الذي يصف انعدام شعر الوجه، ولا يحول نفي اللحية إلى اسم للشعر نفسه."),
    gap("aed-v1.0:157110", "شسا", "OPEN-CANDIDATE", "tongue لا يطابق شسا أو شسل أو شصر ولا نظائر السين والصاد في العربية الممسوحة، ولا يدخل لسان من خارج الرسم."),
    gap("aed-v1.0:158090", "سطا", "OPEN-CANDIDATE", "سطا البيطار على الناقة إذا أدخل يده في رحمها حدث علاجي واقع في الرحم، لكنه لا يجعل سطا اسما للرحم أو البطن ولا يحسم صوت štꜣ.t.", sound="التماس الدلالي واقع خارج اسم العضو؛ ولا يجتمع štꜣ.t↔س-ط-ا في مسار مصري كامل موقع.", orbit="العربية تسمي فعلا يجري داخل رحم الناقة، والمصرية تسمي الرحم أو البطن نفسه؛ بقي فرق الحدث والعضو مانعا.", keywords="سطا على الناقة|أدخل يده في رحمها|الرحم"),
    gap("aed-v1.0:159290", "قلب", "OPEN-CANDIDATE", "القلب عضو داخل الصدر لا الصدر نفسه، وq-ꜣ-b المصرية لا تحمل لام قلب على أنها اسم للوعاء التشريحي كله."),
    gap("aed-v1.0:160220", "قبب", "OPEN-CANDIDATE", "throat لا يطابق قبب في القبة والتقبيب وحواسها، ولا يدخل حلق أو نحر من خارج الرسم."),
    gap("aed-v1.0:161250", "قني", "SOURCE-GAP", "إصابة العين الطبية غير مسماة وكل التعريف بين أقواس؛ لا جرح أو علة معينة تقارن بقني أو قنء."),
    gap("aed-v1.0:164990", "كنكن", "SOURCE-GAP", "الإنجليزية لا تعين إلا حالة مرضية في ثدي المرأة، والألمانية تتردد بين الترهل والنبض بعلامتي شك؛ لا عرض طبي واحدا محسوما."),
    gap("aed-v1.0:166370", "جلب", "OPEN-CANDIDATE", "arm لا يطابق جلب أو جرب أو قلب وقرب في المروحة المقروءة، ولا يدخل ذراع أو عضد من خارج الرسم."),
    gap("aed-v1.0:166760", "جوا", "OPEN-CANDIDATE", "chest/box لا يطابق جوا في الجوى ومرض الصدر ولا جول وقول وغور؛ ورود الصدر في علة الجوى لا يسمي صندوقا أو وعاء."),
    gap("aed-v1.0:167320", "جمح", "OPEN-CANDIDATE", "الضفيرة أو خصلة الشعر لا تطابق جمح في جموح الفرس، والجمة العربية مجتمع شعر الرأس لا صفة ضفر ولا تحمل ḥ المصرية."),
    terminal("aed-v1.0:171300", "∅", "COMPOUND-BOUNDARY", "الرسم `tp-sd` يفصل حدين بواصلة والتعريف يسمي رباطا مخصصا للرأس؛ لا يعامل مجموع الحدين مادة جذرية عربية واحدة."),
    gap("aed-v1.0:171390", "تبر", "SOURCE-GAP", "علة الرأس غير مسماة واقتراح Kopfgrind موسوم بالشك؛ التبرية العربية لقشور أصول الشعر لا تحسم أن المرجع المصري هو القشرة نفسها.", sound="t↔ت وp↔ب ظاهران؛ ꜣ المصرية بإزاء راء تبر بلا صف مصري موقع، و.w باقية على السطح.", orbit="التبرية قشور كالنخالة في أصول الشعر فتلامس جرب الرأس، لكن تعيين المرض المصري نفسه غير محسوم.", keywords="تبرية|أصول الشعر|النخالة|الرأس"),
    gap("aed-v1.0:175160", "ثبو", "OPEN-CANDIDATE", "sole/sandal لا يطابق ثبو أو ثوب؛ الثوب لباس البدن لا نعل القدم ولا باطنها."),
    gap("aed-v1.0:176290", "ثرين", "DIRECTION-GAP", "وسم Sem. loan word في body armor لا يسمي لغة مانحة أو طريق انتقال، ولا تنتخب مروحة ثرين مادة عربية للدرع."),
    gap("aed-v1.0:176420", "ترس", "SOURCE-GAP", "AED لا يعين إلا part of the body بين أقواس، والألمانية تزيد أنه يؤكل؛ لا عضو تشريحي واحدا يقارن بترس أو طرس."),
    gap("aed-v1.0:177060", "ثءزت", "OPEN-CANDIDATE", "tooth لا يطابق ثءزت أو ترس وطرس في المروحة المقروءة، ولا يدخل سن أو ضرس من خارج الرسم."),
    terminal("aed-v1.0:177410", "∅", "OUT-OF-SCOPE", "Tjukten اسم طبقة عسكرية من أصل ليبي، والألمانية نفسها تتردد في وظيفتها بين الكشاف والحارس؛ عزل الاسم الثقافي لا يصدر جذرا معجميا عربيا."),
    gap("aed-v1.0:178630", "ضبن", "OPEN-CANDIDATE", "lock of hair لا يطابق ضبن في الإبط وما يليه وحمل الشيء تحته، ولا يدخل خصلة أو ضفيرة من خارج الرسم."),
    gap("aed-v1.0:180870", "دشر", "OPEN-CANDIDATE", "blood المفسر داخليا بأنه الأحمر لا يطابق دشر أو دسر في العربية الممسوحة، ولا يجعل وصف الحمرة مادة دم عربية."),
    terminal("aed-v1.0:500089", "∅", "OUT-OF-SCOPE", "AED يصنف `m-ḫnt` حرف جر مكاني متعدد الوظائف؛ عزل الأداة الوظيفية سابق على أي مقارنة جذرية."),
    pos("aed-v1.0:500247", "يمن", "ROOT-TRACE", "اليمنة|خلاف اليسرة|اليمين|اليمنى", "j↔ي عبر GLD-02، وm↔م في IDN-02، وn↔ن في IDN-03؛ الجذر الكامل محفوظ بعد عزل .t.", "right eye هي العين الواقعة في الجهة اليمنى، والعربية تسمي اليمنة واليمين خلاف اليسرة؛ المدار الجانبي مباشر.", "TRACE مقصور على وسم الجهة اليمنى في هذا العضو؛ لا يساوي جذر يمن اسم العين نفسها.", zero="عزلت .t علامة التأنيث الاسمية؛ بقي j-m-n كاملا ولم تسقط صامتة جذرية."),
    terminal("aed-v1.0:850363", "∅", "COMPOUND-BOUNDARY", "AED يحلل fan صراحة إلى waving arm ويحفظ الواصل في `ꜥ-ẖn.w`؛ حد الذراع الملوح يمنع رد اسم الأداة المركب إلى جذر مفرد."),
    gap("aed-v1.0:850407", "ونن", "OPEN-CANDIDATE", "child in the womb لا يطابق ونن في العربية الممسوحة، ولا يدخل جنين أو ولد من خارج الرسم."),
    gap("aed-v1.0:20400", "يءوت", "OPEN-CANDIDATE", "old woman لا يطابق يءوت أو ياوت ولا حواس ويل ويول في المروحة، ولا يدخل عجوز من خارج الرسم."),
    gap("aed-v1.0:22970", "يورت", "OPEN-CANDIDATE", "pregnant woman لا يطابق يورت أو يول وءول في العربية الممسوحة، ولا يدخل حمل أو حبل من خارج الرسم."),
    gap("aed-v1.0:24770", "يمتي", "OPEN-CANDIDATE", "child/stripling لا يطابق يمتي أو ءمتي ولا مادة أمت في العربية الممسوحة، ولا يدخل غلام أو صبي من خارج الرسم."),
    gap("aed-v1.0:27350", "ينف", "OPEN-CANDIDATE", "royal child لا يطابق ينف أو ءنف، ولا يورث صفة الملك معنى ابن أو أمير لمادة المروحة."),
    gap("aed-v1.0:34220", "يدح", "OPEN-CANDIDATE", "man of the Delta نسبة جغرافية مصرية لا تطابق يدح أو يضح في العربية الممسوحة، ولا يدخل ساكن أو دلتا من خارج الرسم."),
    gap("aed-v1.0:41150", "عشوت", "OPEN-CANDIDATE", "crying of a child لا يطابق عشوت أو عسوت ونظائر الضاد والغين، ولا يجعل سياق الطفل بكاء في جذر المروحة."),
    gap("aed-v1.0:48730", "وحي", "OPEN-CANDIDATE", "kin/tribe لا يطابق وحي في الإعلام والإشارة والإلهام، ولا تدخل عشيرة أو قرابة من خارج الرسم."),
    gap("aed-v1.0:49710", "وصل", "OPEN-CANDIDATE", "powerful rich woman لا يطابق وصل في الاتصال ولا وشر ووشل وصر في المروحة، ولا يدخل غنى أو قوة من خارج الرسم."),
    gap("aed-v1.0:51310", "وتث", "OPEN-CANDIDATE", "begetter/father لا يطابق وتث أو وتت ووطط في العربية الممسوحة، ولا يدخل أب أو والد من خارج الرسم."),
    gap("aed-v1.0:51320", "وتث", "OPEN-CANDIDATE", "offspring/son لا يطابق وتث أو وتت ووطط؛ فُصل العضو عن متجانسه الذي يسمي الأب ولم يرث معناه."),
    gap("aed-v1.0:57840", "بكر", "OPEN-CANDIDATE", "البكر في العربية من لم تلد أو من ولدت بطنا واحدا، ولا يعني المرأة الحامل الآن؛ لا تسوي القرابة الولادية حالة الحمل."),
    gap("aed-v1.0:57850", "بكر", "OPEN-CANDIDATE", "البكر والبكرة يدوران على الأول والفتوة لا mother cow المرضعة؛ لا يجعل سبق الولادة أو السن أمومة بقرة محكومة."),
    gap("aed-v1.0:58010", "بجر", "OPEN-CANDIDATE", "shipwrecked man لا يطابق بجر أو بقر أو بغل في المروحة، ولا يدخل غرق أو سفينة من خارج الرسم."),
    gap("aed-v1.0:73130", "مهو", "OPEN-CANDIDATE", "family/kin لا يطابق مهو أو محو وميح في العربية الممسوحة، ولا تدخل أسرة أو قرابة من خارج الرسم."),
    gap("aed-v1.0:77910", "مثءم", "SOURCE-GAP", "ثوب المرأة أو الفتاة غير مسمى وكل التعريف بين أقواس؛ لا نوع لباس أو مادة نسيج معينة تقارن بمثءم."),
    gap("aed-v1.0:84370", "نمح", "OPEN-CANDIDATE", "free man of lower status/orphan لا يطابق نمح في العربية الممسوحة، ولا يجمع الحر والفقير واليتيم في مادة عربية مفترضة."),
    gap("aed-v1.0:87250", "نخن", "OPEN-CANDIDATE", "child لا يطابق نخن في العربية الممسوحة، ولا يدخل ولد أو صبي من خارج الرسم."),
    gap("aed-v1.0:94110", "ربوت", "OPEN-CANDIDATE", "figure/statue of a woman لا يطابق ربوت أو لبوت ولا حواس رب ورف ولب، ولا يدخل تمثال من خارج الرسم."),
    gap("aed-v1.0:103020", "حون", "OPEN-CANDIDATE", "child/youth/young man لا يطابق حون في العربية الممسوحة، ولا يدخل صبي أو شاب من خارج الرسم."),
    gap("aed-v1.0:103150", "حور", "OPEN-CANDIDATE", "humble man/wretch لا يطابق حور أو حول؛ وصف ضعيف الحوار في شاهد عارض لا يسمي الرجل الضعيف أو البائس."),
    gap("aed-v1.0:113590", "خلع", "SOURCE-GAP", "الإفراز في علة نسائية موسوم بالشك ولا يعين نوع السائل أو العرض؛ الخلع والنزع العامان لا يحسمان مرجعا طبيا واحدا."),
    gap("aed-v1.0:125660", "زءتي", "OPEN-CANDIDATE", "son في لقب ابن جب أو الملك لا يطابق زءتي أو سلط وسرط في المروحة، ولا يورث اللقب معنى الابن لمادة عربية غير عاملة."),
    terminal("aed-v1.0:126130", "∅", "COMPOUND-BOUNDARY", "AED يحلل snake صراحة إلى son of the earth ويحفظ الواصل في `zꜣ-tꜣ`؛ لا يحمل المركب الوصفي على جذر عربي واحد."),
    gap("aed-v1.0:133690", "زفن", "OPEN-CANDIDATE", "kindly/gentle man لا يطابق زفن في الرقص والدفع ولا سفن في القشر والسفينة، ولا يدخل رفق أو حلم من خارج الرسم."),
    gap("aed-v1.0:135690", "شمس", "OPEN-CANDIDATE", "eldest daughter لا تطابق الشمس ولا سمس ومشط في العربية الممسوحة، ولا يحول الكبر في الرتبة إلى معنى الجرم السماوي."),
    gap("aed-v1.0:135700", "مسي", "SOURCE-GAP", "تاج العروس وحده يذكر مسي الناقة بإخراج ولدها، أما المصدر القديم المستقل الثاني فلا يثبت هذا الحس؛ كما أن الفعل البيطري لا يحسم ولادة المرأة.", sound="بعد عزل السابقة السببية: m↔م في IDN-02 وs↔س في IDN-07 وi̯/j↔ي عبر GLD-02؛ نواة m-s-j كاملة.", orbit="مسي الناقة بإخراج ولدها يلامس التوليد، لكن الشاهد المعجمي المستقل الوحيد بيطري والمصرية تسمي توليد المرأة.", keywords="مسى الناقة|رحمها|إخراج ولدها|الماسي", zero="عزلت s الأولى بوصفها السابقة السببية المسماة في `verb_caus_3-inf`؛ بقي m-s-j كاملا ولم تسقط صامتة جذرية."),
    gap("aed-v1.0:137100", "شنب", "SOURCE-GAP", "barren نفسها موسومة بالشك؛ شنب العربية لبرد الفم والأسنان لا يثبت عقم المرأة، ولا يحسم AED علة خصوبة واحدة."),
    gap("aed-v1.0:142050", "خبر", "OPEN-CANDIDATE", "create/bring into being/rear a child لا يطابق خبر في العلم والنبأ والاختبار، ولا يدخل خلق أو تربية من خارج الرسم."),
    gap("aed-v1.0:144030", "سسم", "SOURCE-GAP", "مرض الطفل غير مسمى وكل التعريف بين أقواس؛ لا علة معينة تقارن بسسم أو شصم أو صمي."),
    gap("aed-v1.0:153020", "شوا", "OPEN-CANDIDATE", "poor man لا يطابق شوا في الشواء والشاة، وورود رديء المال في شرح عرضي لا يسمي الإنسان الفقير؛ والمصدر المستقل لهذا الجذر واحد."),
    gap("aed-v1.0:156680", "شري", "OPEN-CANDIDATE", "girl/daughter لا يطابق شري أو سري ولا ريط وليط في العربية الممسوحة، ولا يدخل بنت أو فتاة من خارج الرسم."),
    gap("aed-v1.0:172190", "تمر", "OPEN-CANDIDATE", "ancestress/mother لا يطابق تمر أو تمل وطمر في العربية الممسوحة، ولا يدخل أم أو والدة من خارج الرسم."),
    terminal("aed-v1.0:450515", "∅", "COMPOUND-BOUNDARY", "AED يحلل watchman صراحة إلى son of the house ويحفظ الواصل في `zꜣ-pr`؛ حد الابن والبيت يعزل اسم الوظيفة المركب."),
    gap("aed-v1.0:859037", "كحكح", "SOURCE-GAP", "كحكح مطابق صامتا ويقارب الشيخ المسن، لكن الشاهد العربي المستقل الوحيد يسمي العجوز الهرمة والناقة الهرمة؛ غاب شاهد قديم ثان للرجل.", sound="k↔ك في IDN-13 وḥ↔ح في IDN-14 في الموضعين؛ الهيكل المضعف كامل بلا إسقاط.", orbit="الكحكح في الشاهد العربي العجوز الهرمة، والمصرية old man؛ مدار الهرم الإنساني قريب، وبقي الجنس وتغطية المصدر مانعين.", keywords="الكحكح|العجوز الهرمة|هرمت"),
    gap("aed-v1.0:10590", "ءسرت", "SOURCE-GAP", "sky نفسها موسومة بالشك وكل التعريف بين أقواس؛ لا سماء أو سقف معين يقارن بءسرت أو رسل."),
    gap("aed-v1.0:20880", "يءخو", "OPEN-CANDIDATE", "sunshine/radiance لا يطابق يءخو أو ياخو وءرخ في العربية الممسوحة، ولا يدخل نور أو ضوء من خارج الرسم."),
    gap("aed-v1.0:21180", "يءدت", "OPEN-CANDIDATE", "AED يجمع الندى والرائحة الطيبة والمطر المنصب، ولا يطابق يءدت أو أرض ويرد مادة عربية تغطي هذه الحواس الثلاثة."),
    pos("aed-v1.0:26140", "يمن", "ROOT-TRACE", "اليمنة|خلاف اليسرة|اليمين|اليمنى", "j↔ي عبر GLD-02، وm↔م في IDN-02، وn↔ن في IDN-03؛ الجذر الكامل محفوظ بعد عزل .t.", "right side هي اليمنة واليمين خلاف اليسرة مباشرة؛ west وland of the dead حسان مصريان لا يرثان الحكم.", "TRACE مقصور على الجهة اليمنى في العضو المختار؛ لا يساوي جهة الغرب أو عالم الموتى بجذر يمن.", zero="عزلت .t علامة التأنيث الاسمية؛ بقي j-m-n كاملا ولم تسقط صامتة جذرية."),
    gap("aed-v1.0:30620", "يحيح", "SOURCE-GAP", "الصوت المائي نفسه غير مسمى بين الفقاقيع والخرير وكله بين أقواس؛ لا حدث سمعي واحدا محسوما للمقارنة."),
    gap("aed-v1.0:30870", "يخم", "OPEN-CANDIDATE", "bank of river/fortress لا يطابق يخم أو ءخم في العربية الممسوحة، ولا يدخل شاطئ أو حافة من خارج الرسم."),
    gap("aed-v1.0:31770", "يزكن", "SOURCE-GAP", "موضع السماء غير مسمى واقتراح zenith موسوم بالشك؛ لا جهة سماوية واحدة تقارن بيزكن أو يسكن."),
    gap("aed-v1.0:33370", "يتر", "OPEN-CANDIDATE", "river/Nile/canal لا يطابق يتر أو يتل وءتر في العربية الممسوحة، ولا يدخل نهر أو قناة من خارج الرسم."),
    terminal("aed-v1.0:37200", "∅", "OUT-OF-SCOPE", "Aperu اسم اليوم الحادي والعشرين من الشهر القمري؛ عزل الاسم التقويمي لا يصدر جذرا عربيا من معنى العدد أو القمر."),
    gap("aed-v1.0:37740", "عمعت", "OPEN-CANDIDATE", "mud/muddy ground لا يطابق عمعت أو عمض وغمض في العربية الممسوحة، ولا يجعل انخفاض الأرض طينا أو وحلا."),
    gap("aed-v1.0:38770", "عنخت", "OPEN-CANDIDATE", "Ankhet تسمية تصويرية للنار لا تطابق عنخت أو عنخ ونظائر الضاد والغين، ولا تدخل نار أو لهب من خارج الرسم."),
    gap("aed-v1.0:39320", "عريت", "SOURCE-GAP", "AED يتردد بين heaven وroof بعلامتي شك، والألمانية لا تسمي إلا تعبيرا للسماء بين أقواس؛ لا مرجع علوي واحدا محسوما."),
    gap("aed-v1.0:39740", "عرق", "OPEN-CANDIDATE", "month's end/last day لا يطابق عرق أو علق وغرق وغلق في العربية الممسوحة، ولا يدخل آخر أو نهاية من خارج الرسم."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT
assert {item.state for item in DECISIONS} <= LEGAL_CLOSURES
assert {item.verdict for item in DECISIONS} <= LEGAL_CLOSURES

OUTSIDE_FAN = {"aed-v1.0:145200"}

WITNESS_NOTES = {
    "aed-v1.0:145200": "أثبت لسان العرب وتاج العروس حم الماء وتسخينه والحميم الماء الحار؛ ثبت مدار warm، وبقي š↔ح بلا صف مصري موقع.",
    "aed-v1.0:171390": "أثبت الصحاح ولسان العرب التبرية في الرأس كالنخالة في أصول الشعر؛ ثبت تماس جرب الرأس، وبقي تعيين المرض المصري وصوته مفتوحين.",
    "aed-v1.0:500247": "أثبت لسان العرب وتاج العروس اليمنة واليمين خلاف اليسرة؛ ثبت وسم الجهة اليمنى للعين بشاهدين مستقلين.",
    "aed-v1.0:135700": "وجد الحس البيطري في تاج العروس وحده: مسي الناقة بإخراج ولدها؛ لم يثبته مصدر قديم مستقل ثان، فبقي SOURCE-GAP.",
    "aed-v1.0:859037": "وجد الكحكح للعجوز الهرمة في لسان العرب ونسخته المكررة فقط؛ لا شاهد معجمي مستقل ثان ولا نص صريح في الرجل المسن.",
    "aed-v1.0:26140": "أثبت لسان العرب وتاج العروس اليمنة واليمين خلاف اليسرة؛ ثبت مدار right side، وبقي west وعالم الموتى خارج الحكم.",
}


def round34_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R33.round33_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND33-COMPLETION", "ROUND34-COMPLETION")
    card = card.replace(
        f"round33-egyptian-rank={rank}/{CARD_COUNT}",
        f"round34-egyptian-rank={rank}/{CARD_COUNT}",
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
        raise SystemExit("Round-thirty-four marker already exists; append refused.")

    aramaic_exact, _ = R9.load_entries("aramaic")
    aramaic_queue = R9.select_aramaic(aramaic_text, aramaic_exact)
    assert not aramaic_queue, (
        "Aramaic short live-open queue is no longer exhausted: "
        f"{[item['entry_id'] for item in aramaic_queue[:10]]}"
    )

    egyptian_exact, _ = R9.load_entries("egyptian")
    queue = R33.R32.R31.R30.R29.select_egyptian_fast(
        egyptian_text, egyptian_exact,
    )
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
        round34_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الرابعة والثلاثون: استمرار المخزون المصري المسجل المفتوح (2026-08-26)", "",
        (
            "أعيد فحص الآرامية أولا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرا، فسجل الانتقال المسمى `{TRANSITION}`. انتقيت ثمانين "
            "بطاقة مصرية بدءا من `WO-C-OPEN-COMP-01983` بقصر الهيكل ثم موضع "
            "اللقطة. استبعد صف ḏ المؤجل. في كل بطاقة عرضت إصابات AED كلها بلا "
            "حد، وكتب وسم الطريق والرسم والمدخل المختار، وحفظ الاختلاف "
            "والمتجانسات بلا محو. فحصت حالة الإغلاق والحكم آليا على القائمة "
            "القانونية وحدها في `data/closure-vocabulary.json`."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-01983 إلى WO-C-OPEN-COMP-02022", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-02023 إلى WO-C-OPEN-COMP-02062", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([
                f"<!-- LANE-C-R34-EGYPTIAN-CHUNK-{rank:03d}:END -->", "",
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
        "## الجولة الرابعة والثلاثون: المسار C، الساميات والمصرية (2026-08-26)", "",
        f"- الوقت: {now}.",
        "- أعيد فحص الساميات أولا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01983` إلى `WO-C-OPEN-COMP-02022`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-02023` إلى `WO-C-OPEN-COMP-02062`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طبق الانضباط الثلاثي: كل موجب له صوت موقع وحدث مجمد ومدار مكتوب؛ وكل بطاقة أخرى لها عائق شريف مسمى.",
        "- قاموس الإغلاق المغلق وحده مطبق: كل حالات الإغلاق والأحكام اجتازت القائمة القانونية في `data/closure-vocabulary.json`.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ الموجبان مقصوران على العضوين ومداريهما المكتوبين.",
        "- الموجبان: `jmn.t↔يمن` في وسم العين اليمنى للعضو `500247`، وفي الجهة اليمنى للعضو `26140`؛ كلاهما `ROOT-TRACE` بعد عزل .t.",
        "- المطابقة الدلالية المرفوعة `sšmm↔حمم` بقيت `LAW-GAP` للحرارة بعد عزل السابقة السببية، لأن š↔ح بلا صف مصري موقع.",
        "- تماسّات `tpꜣ.w↔تبر` في قشور الرأس، و`smsi̯↔مسي` في استخراج الولد، و`kḥkḥ↔كحكح` في الهرم بقيت `SOURCE-GAP` لنقص تعيين المرجع أو الشاهد المستقل الثاني.",
        "- وسم القرض السامي العام في `ṯryn` بقي `DIRECTION-GAP` بلا مانح فردي أو طريق مكتمل.",
        "- المركبات الخمسة أغلقت `COMPOUND-BOUNDARY`، وحرف الجر والاسمان الثقافي والتقويمي أغلقت `OUT-OF-SCOPE`.",
        "- الألفاظ والمراجع المشكوكة أو غير المسماة بقيت `SOURCE-GAP`، وصف ḏ المصري المؤجل بقي مستبعدا.",
        "- لم يحدث شحن أو إيداع أو إعداد مرحلي، ولم يستعمل git أو تحدث مشتقات النشر.", "",
        f"LANE-C DONE34 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
        R33.R32.R31.R30.R29.R28.R27.R26.R25.R24.R23.R20.R10.append(
            EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian,
        )
        R33.R32.R31.R30.R29.R28.R27.R26.R25.R24.R23.R20.R10.append(
            REPORT, f"{MARKER}:REPORT", report,
        )
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
