#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 35 completion cards without shipping or git.

The live short Aramaic queue is checked before the registered Egyptian open
queue continues. The script completes WO-C-OPEN-COMP-02063..02142 in two
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

import harvest_lane_c_round34 as R34


R9 = R34.R9
AR = R34.AR
ROOT = R34.ROOT
ARAMAIC = R34.ARAMAIC
EGYPTIAN = R34.EGYPTIAN
REPORT = R34.REPORT

MARKER = "LANE-C-ROUND35-2026-08-26"
FIRST_SERIAL = 2063
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)
LEGAL_CLOSURES = R34.LEGAL_CLOSURES


def gap(member_id: str, candidate: str, state: str, reason: str,
        sound: str = "المروحة بنيوية فقط؛ لا يرقى التشابه إلى قانون أو نسب.",
        orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
        keywords: str = "", zero: str = "") -> R9.Decision:
    return R34.gap(
        member_id, candidate, state, reason, sound, orbit, keywords, zero,
    )


def pos(member_id: str, candidate: str, verdict: str, keywords: str,
        sound: str, orbit: str, reason: str,
        zero: str = "") -> R9.Decision:
    return R34.pos(
        member_id, candidate, verdict, keywords, sound, orbit, reason, zero,
    )


def terminal(member_id: str, candidate: str, verdict: str, reason: str,
             zero: str = "") -> R9.Decision:
    return R34.terminal(member_id, candidate, verdict, reason, zero)


# No positive is issued. The closest full-root sound and meaning contact,
# sptḫ↔فتخ, is blocked because the frozen registry descends to the nucleus فت
# and returns brittle breaking rather than the attested bodily-flexion event.
# Other semantic contacts with an unsigned Egyptian row or a required
# consonant reversal remain named gaps. Uncertain referents, calendrical
# labels, compounds, and general Semitic-loan tags remain isolated.
DECISIONS: tuple[R9.Decision, ...] = (
    gap("aed-v1.0:42800", "ورب", "OPEN-CANDIDATE", "high-lying land لا يطابق ورب في الوجار والعضو والحفرة والعرق الفاسد، ولا ولب في الدخول وفراخ الزرع؛ لا يدخل مرتفع من خارج الرسم."),
    terminal("aed-v1.0:45100", "∅", "OUT-OF-SCOPE", "Shines-forth اسم الساعة الأولى من اليوم في التقويم المصري؛ عزل اسم الساعة لا يصدر جذرا عربيا من معنى الشروق."),
    gap("aed-v1.0:45160", "وبن", "OPEN-CANDIDATE", "rays of the sun لا يطابق وبن في الأذى والجوع أو نفي أحد في الدار، ولا يرث حكم متجانس الساعة الأولى."),
    terminal("aed-v1.0:47550", "∅", "COMPOUND-BOUNDARY", "الرسم `wr-ꜥꜣ` ذو حدين موصولين ويسمي حاكما أو أميرا؛ حد اللقب المركب يمنع حمل مجموعه على جذر عربي مفرد."),
    gap("aed-v1.0:48070", "ولح", "OPEN-CANDIDATE", "plot of land غير المستعمل لا يطابق وليح العربية للجوالق والغرارة، ولا يجعل السعة في الوعاء قطعة أرض."),
    gap("aed-v1.0:48130", "ورشو", "OPEN-CANDIDATE", "spend the day/be awake لا يطابق ورشو أو ورسو ولا ولشو وولسو في العربية الممسوحة، ولا يدخل سهر أو يقظ من خارج الرسم."),
    gap("aed-v1.0:49680", "وشر", "OPEN-CANDIDATE", "mighty one بوصف النار لا يطابق وشر في نشر الخشب وتحديد الأسنان، ولا وسل ووصل في القرب والاتصال؛ لا يدخل قوة من خارج الرسم."),
    gap("aed-v1.0:49880", "وسخ", "SOURCE-GAP", "heaven(s) نفسها بين أقواس التحرير وعلامة شك؛ لا سماء واحدة محكومة تقارن بوسخ أو وشخ أو وصخ."),
    gap("aed-v1.0:50230", "وشر", "OPEN-CANDIDATE", "darkness وأشد الليل ظلمة لا يطابق وشر في نشر الخشب والأسنان ولا وشل في الماء القليل، ولا يدخل ليل من خارج الرسم."),
    gap("aed-v1.0:59090", "برع", "SOURCE-GAP", "AED لا يعين إلا region of the sky بين أقواس بلا جهة سماوية مسماة؛ لا ينتخب برع أو بلغ أو فرع قبل تعيين المرجع."),
    gap("aed-v1.0:61550", "فحو", "OPEN-CANDIDATE", "ends of the country/earth لا يطابق فحوى القول في معناه ومذهبه ولا حواس فحو الأخرى، ولا يدخل نهاية من خارج الرسم."),
    gap("aed-v1.0:66790", "مرع", "OPEN-CANDIDATE", "wind/breeze لا يطابق مرع أو ملع أو مرغ وبقية المروحة في العربية الممسوحة، ولا يدخل ريح أو نسيم من خارج الرسم."),
    gap("aed-v1.0:66830", "مرو", "LAW-GAP", "المرو والمروَراة للأرض التي لا شيء فيها يلامسان new land، لكن ꜣ المصرية بإزاء ر العربية بلا صف مصري موقع، ولا يثبت الحس العربي معنى island.", sound="m↔م في IDN-02 وw↔و في IDN-10؛ ꜣ↔ر هي الرجل المصرية غير الموقعة بعد عزل .t.", orbit="المروَراة أرض خالية لا شيء فيها، والمصرية تسمي أرضا جديدة أو جزيرة؛ تماس الأرض الخالية قائم، وبقي وصف الجدة والجزيرة والصوت مانعا.", keywords="المرو|المروَراة|الأرض التي لا شيء فيها|أرض", zero="عزلت .t علامة التأنيث الاسمية؛ بقي m-ꜣ-w كاملا بإزاء م-r-w من غير إسقاط صامت جذري."),
    gap("aed-v1.0:68370", "مين", "SOURCE-GAP", "AED يتردد بين ditch وstagnant water بعلامتي شك، والألمانية لا تسمي إلا مسطحا مائيا؛ لا خندق أو ماء راكد واحدا محسوما."),
    gap("aed-v1.0:68380", "مين", "SOURCE-GAP", "الإنجليزية لا تعين إلا kind of land بين أقواس، والألمانية تجمع الضيعة والأرض؛ لا نوع أرض واحدا محسوما يقارن بمين."),
    terminal("aed-v1.0:73690", "∅", "COMPOUND-BOUNDARY", "الرسم `mḥ-tꜣ` مركب ذو واصل ويسمي land cubit أو مقياسا أرضيا؛ حد القياس والأرض يمنع رده إلى جذر عربي مفرد."),
    gap("aed-v1.0:73860", "محي", "OPEN-CANDIDATE", "north wind لا يطابق محي العربية في إذهاب الأثر، ولا يجعل جهة الشمال فعلا للمحو."),
    gap("aed-v1.0:75000", "مسي", "SOURCE-GAP", "نوع طير الماء غير مسمى وكل التعريف بين أقواس؛ لا طائر معين يقارن بمسي للمساء أو مشي للحركة."),
    terminal("aed-v1.0:75300", "∅", "OUT-OF-SCOPE", "mspr اسم اليوم الثالث من الشهر القمري؛ عزل الاسم التقويمي لا يصدر جذرا عربيا من معنى العدد أو القمر."),
    gap("aed-v1.0:75380", "مزمز", "SOURCE-GAP", "AED لا يعين إلا verb referring to the sun بين أقواس، من غير حدث شمسي مسمى؛ لا فعل واحدا محسوما للمقارنة."),
    gap("aed-v1.0:77890", "مثاي", "SOURCE-GAP", "الإنجليزية تقترح land-heritage بعلامة شك، والألمانية تقول handed over؛ اختلاف الميراث وفعل التسليم يمنع تعيين معنى واحد."),
    gap("aed-v1.0:81260", "نوي", "OPEN-CANDIDATE", "water/flood/wave لا يطابق نوي في القصد والتحول والبعد ونواة الثمر، ولا يدخل ماء من خارج الرسم."),
    gap("aed-v1.0:82650", "نبي", "OPEN-CANDIDATE", "flame لا يطابق نبي أو نبء في العربية الممسوحة، ولا يدخل لهب أو نار من خارج الرسم."),
    gap("aed-v1.0:83430", "نفنف", "OPEN-CANDIDATE", "flood waters لا تطابق النفنف للهواء والمهواة والمفازة وأسناد الجبل، ولا يحول الفراغ بين شيئين إلى ماء فيضان."),
    gap("aed-v1.0:83930", "نفر", "OPEN-CANDIDATE", "ground-level/base لا يطابق نفر في التفرق والنفور والجماعة ولا نفل في العطية والنبات، ولا يدخل أساس من خارج الرسم."),
    gap("aed-v1.0:88300", "نشر", "OPEN-CANDIDATE", "flame لا يطابق نشر في البسط والإحياء والرائحة وانتشار الريح، ولا تجعل الريح المصاحبة للنار لهبا."),
    gap("aed-v1.0:100770", "حري", "OPEN-CANDIDATE", "sheet of shallow inundation water لا يطابق حري في النقص والناحية والالتهاب ولا حلي في الزينة، ولا يدخل غمر من خارج الرسم."),
    gap("aed-v1.0:101010", "حاعع", "OPEN-CANDIDATE", "touch of a boat on land لا يطابق حاعع أو حاضع أو حرغغ في العربية الممسوحة، ولا يدخل مس أو رسو من خارج الرسم."),
    gap("aed-v1.0:103630", "حبب", "OPEN-CANDIDATE", "حباب العربية فقاقيع تطفو على الشراب أو قطرات طل، لا fresh water أو ماء الفيضان نفسه؛ فرق الظاهرة والسائل يمنع الحكم.", sound="ḥ↔ح في IDN-14 وb↔ب في IDN-05 مع التضعيف بعد عزل .t؛ بقيت الدلالة هي العائق.", orbit="الحباب يتكون على سطح السائل، أما المصرية فتسمي الماء نفسه؛ المجاورة المادية لا تجعل الفقاقيع اسما للماء."),
    gap("aed-v1.0:104080", "حفت", "OPEN-CANDIDATE", "extreme limits of the earth لا يطابق حفت في الدق والهلاك أو حبط في الفساد والانتفاخ، ولا يدخل طرف أو حد من خارج الرسم."),
    gap("aed-v1.0:106540", "حنب", "OPEN-CANDIDATE", "measured parcel/meadow/garden لا يطابق حنب في انحناء الفرس وحنبط في الأوصاف الجسمية، ولا يدخل حقل أو روضة من خارج الرسم."),
    terminal("aed-v1.0:107960", "∅", "COMPOUND-BOUNDARY", "الرسم `ḥr-mw` وشرحه الحرفي on someone's water تركيب جرّي صريح لمعنى الوفاء؛ لا يحمل مجموع الحدين على جذر عربي واحد."),
    terminal("aed-v1.0:109030", "∅", "COMPOUND-BOUNDARY", "الرسم `ḥr.w-ꜥ` ذو واصل والتعريف يسمي شرابا من العنب والماء؛ حد المزيج المركب يمنع رده إلى جذر عربي مفرد."),
    gap("aed-v1.0:113750", "خلو", "OPEN-CANDIDATE", "night/evening لا يطابق خلو في الخلاء والانفراد ولا خرو أو خءو في العربية الممسوحة، ولا يدخل ليل أو مساء من خارج الرسم."),
    gap("aed-v1.0:114300", "خاست", "OPEN-CANDIDATE", "خاست في الشاهد العربي اسم بلدة ببلخ، لا اسما عاما للتلال أو البلاد الأجنبية أو الصحراء؛ لا يورث العلم معنى ḫꜣs.t."),
    gap("aed-v1.0:116390", "خبر", "SOURCE-GAP", "cultivated land نفسها بين أقواس ومقيدة بإقليم طيبة؛ لا نوع أرض أو حقل مسمى يقارن بخبر أو خفر قبل تعيين المرجع."),
    gap("aed-v1.0:120340", "خرب", "DIRECTION-GAP", "وسم Sem. loan word في الماء المعطر بالجلبانوم لا يسمي مانحا فرديا أو طريق انتقال، ولا يجد في خرب أو خلب مقابلا للماء المعطر."),
    gap("aed-v1.0:120350", "خرم", "SOURCE-GAP", "river or canal كلها بين أقواس التحرير؛ لا نهر أو قناة واحدة محكومة تقارن بخرم أو خلم."),
    gap("aed-v1.0:120480", "خرق", "DIRECTION-GAP", "slippery ground موسوم قرضا ساميا عاما بلا مانح فردي أو طريق مكتمل، وخرق وخلق العربية لا يسميان الأرض الزلقة."),
    gap("aed-v1.0:122530", "خابي", "SOURCE-GAP", "surge of water موسوم بالشك، والألمانية تصف جريانا غزيرا من حفرة ماء؛ لا حدث مائي واحدا محسوما للمقارنة."),
    terminal("aed-v1.0:123520", "∅", "OUT-OF-SCOPE", "one who unites لقب للعين القمرية في طور التزايد، لا فعلا معجميا عاما؛ عزل اللقب الديني الفلكي لا يصدر جذرا عربيا."),
    gap("aed-v1.0:127530", "سلقب", "OPEN-CANDIDATE", "to water لا يطابق سلقب أو سلغب أو سرقب ولا لجب ولقب في العربية الممسوحة؛ لا يدخل سقي من خارج الرسم."),
    gap("aed-v1.0:127650", "زلط", "OPEN-CANDIDATE", "زلط القديم للمشي السريع غير ثابت، واستعماله للحصى الصغار عامي متأخر؛ لا يثبت ground/floor/earth، مع بقاء ꜣ↔ل غير موقع."),
    terminal("aed-v1.0:127930", "∅", "OUT-OF-SCOPE", "sjꜣ.w اسم اليوم الرابع عشر من الشهر القمري؛ عزل الاسم التقويمي لا يصدر جذرا عربيا من معنى العدد."),
    terminal("aed-v1.0:127940", "∅", "OUT-OF-SCOPE", "sjꜣ.w اسم اليوم السابع عشر من الشهر القمري؛ فصل العضو عن متجانس اليوم الرابع عشر يمنع توريث حكمه."),
    gap("aed-v1.0:130680", "سوخا", "OPEN-CANDIDATE", "spend the night لا يطابق سوخا أو شوخا أو وخا في العربية الممسوحة، ولا يدخل بات أو سهر من خارج الرسم."),
    gap("aed-v1.0:131280", "شبا", "OPEN-CANDIDATE", "star لا يطابق شباة الشيء وحد طرفه أو شبا البرد ولا سبر وصبر وبقية المروحة، ولا يدخل نجم من خارج الرسم."),
    gap("aed-v1.0:131370", "شبا", "OPEN-CANDIDATE", "sparkle like a star لا يطابق شبا في حد الطرف والبَرَد والارتفاع، ولا يحول لمعان النجم إلى حدة السيف أو ارتفاع الشجر."),
    gap("aed-v1.0:133030", "بحر", "OPEN-CANDIDATE", "brandish weapons/cause wind to circulate لا يطابق بحر أو فخر أو فحل بعد عزل السابقة السببية، ولا تدخل إدارة أو تلويح من خارج الرسم."),
    gap("aed-v1.0:133160", "فتخ", "TOOL-GAP", "فتخ أصابع الرجل بمعنى ثناها ولينها يلتقي make writhe، والصوت كامل بعد عزل s السببية، لكن الحدث المجمد يهبط إلى نواة فت ويعطي تكسير الهش لا هيئة الثني.", sound="p↔ف في IDN-06 وt↔ت في IDN-11 وḫ↔خ في IDN-17؛ الجذر كامل بعد عزل s السببية.", orbit="فتخ أصابع رجله إذا ثناها ولينها، وفتخ الطائر جناحيه عند الانحطاط؛ وهو مدار ثني الجسد القريب من التلوي، وبقي حدث الأداة مانعا.", keywords="فتخ أصابع رجله|ثناها|لينها|فتخ جناحيها", zero="عزلت s السابقة السببية المسماة في `verb_caus_3-lit`؛ بقي p-t-ḫ كاملا بلا إسقاط صامت جذري."),
    gap("aed-v1.0:133570", "فرط", "SOURCE-GAP", "region of the sky or underworld كلها بين أقواس، ويتردد التعريف بين مجالين؛ لا جهة سماوية أو أخروية واحدة محكومة."),
    gap("aed-v1.0:135570", "محي", "OPEN-CANDIDATE", "water/flood بعد عزل s السببية لا يطابق محي في إذهاب الأثر، ولا يدخل سيل أو سقي من خارج الجذر."),
    gap("aed-v1.0:137080", "شنب", "OPEN-CANDIDATE", "heaven/sky لا يطابق شنب في ماء الأسنان وحدتها ولا سنب وصنب وبقية المروحة، ولا يدخل سماء من خارج الرسم."),
    terminal("aed-v1.0:139860", "∅", "OUT-OF-SCOPE", "Selkis اسم كوكبة مخصوصة في السماء الشمالية؛ عزل الاسم الفلكي الديني لا يصدر جذرا عربيا من معنى النجم."),
    gap("aed-v1.0:141240", "شحد", "SOURCE-GAP", "height of the starry sky نفسها موسومة بالشك، والألمانية لا تعين إلا جزءا من السماء؛ لا ارتفاع أو طبقة واحدة محكومة."),
    gap("aed-v1.0:156700", "شري", "SOURCE-GAP", "الأرض في إقليم هيراكليوبوليس غير مسماة وكل التعريف بين أقواس؛ لا نوع أرض معين يقارن بشري أو سري."),
    gap("aed-v1.0:158820", "سدي", "LAW-GAP", "السدى ندى الليل وكل رطب ندي، فيلامس flooded parcel في الرطوبة، لكن š المصرية بإزاء س العربية بلا صف مصري موقع، ولا تسمي العربية قطعة حقل مغمورة.", sound="d↔د في IDN-09 وy↔ي في IDN-23؛ š↔س هي الرجل المصرية غير الموقعة بعد عزل .t.", orbit="السدى ندى الليل ومكان سد كنَد، والمصرية تسمي قطعة أرض غمرها الماء؛ مدار البلل مباشر، وبقي اسم القطعة والصوت مانعين.", keywords="السدى|ندى الليل|كل رطب ندي|مكان سد", zero="عزلت .t علامة التأنيث الاسمية؛ بقي š-d-y كاملا بإزاء س-d-y من غير إسقاط صامت جذري."),
    gap("aed-v1.0:158870", "سود", "LAW-GAP", "سواد كل كون ما حول القرى والرساتيق يلامس field/meadow، لكن š-d-w المصرية تحتاج š↔س غير الموقع وقلب d-w إلى و-d العربية.", sound="المقابلة المرفوعة š-d-w↔س-w-d تحفظ الصوامت الثلاثة لكنها تقلب الأخيرين؛ وفوق ذلك š↔س بلا صف مصري موقع.", orbit="السواد في الشاهد العربي ريف القرى والرساتيق، والمصرية تسمي الحقل والمرعى وقطعة الأرض؛ مدار الأرض المعمورة قريب، وبقي ترتيب الصوت مانعا.", keywords="سواد كل كون|القرى|الرساتيق|سواد العراق", zero="عزلت .t علامة التأنيث الاسمية؛ بقي š-d-w، ولم يسمح العزل بقلب d-w إلى w-d."),
    gap("aed-v1.0:159160", "قري", "OPEN-CANDIDATE", "high field/high-lying land لا يطابق قري أو قلي في العربية الممسوحة، ولا يرث معنى hill من متجانسات qꜣꜣ السابقة."),
    gap("aed-v1.0:160200", "قبب", "OPEN-CANDIDATE", "cool water لا يطابق قبب في القبة واليبس والضمور والصوت، ولا يرث cool wind من المتجانس السابق أو يدخل بردا من خارج الرسم."),
    gap("aed-v1.0:160330", "قبح", "OPEN-CANDIDATE", "libation water/water لا يطابق قبح في سوء الهيئة والتنحية عن الخير، ولا يدخل ماء أو سقاية من خارج الرسم."),
    gap("aed-v1.0:160360", "قبح", "OPEN-CANDIDATE", "water fowl لا يطابق قبح، ولا يرث معنى الماء من متجانس libation المجاور أو يدخل اسم طائر من خارج الرسم."),
    gap("aed-v1.0:163420", "كاف", "OPEN-CANDIDATE", "covers of the sky لا يطابق كاف في اسم الحرف والكفاية ولا كلب وكلف وكرب، ولا يدخل قبة أو غطاء من خارج الرسم."),
    terminal("aed-v1.0:163480", "∅", "OUT-OF-SCOPE", "kꜣp.w اسم اليوم التاسع من الشهر القمري؛ عزل الاسم التقويمي لا يصدر جذرا عربيا من معنى العدد."),
    gap("aed-v1.0:167660", "جنح", "OPEN-CANDIDATE", "star لا يطابق جنح في الميل والجناح ولا قنح في العربية الممسوحة، ولا يدخل نجم من خارج الرسم."),
    gap("aed-v1.0:173620", "تكر", "OPEN-CANDIDATE", "flame/torch/candle لا يطابق تكر أو تكل وتكء في العربية الممسوحة، ولا يدخل نار أو سراج من خارج الرسم."),
    gap("aed-v1.0:179810", "ضني", "OPEN-CANDIDATE", "land register لا يطابق ضني في المرض الملازم، ولا يجعل ثبوت الداء تسجيلا للأرض."),
    gap("aed-v1.0:185600", "جسر", "OPEN-CANDIDATE", "sacred ground لا يطابق جسر في المعبر والجرأة ولا جشر وجصر وبقية المروحة، ولا يدخل قدس أو أرض من خارج الرسم."),
    gap("aed-v1.0:401162", "وشر", "SOURCE-GAP", "dry land نفسها موسومة بالشك في اللغتين؛ وشر العربية للنشر بالمنشار لا يحسم حس الأرض قبل ثبوت المرجع."),
    gap("aed-v1.0:450172", "نغض", "SOURCE-GAP", "powder نفسها موسومة بالشك، والتعريف يتردد بين شيء مطحون ومزيج؛ لا مادة مسحوقة واحدة محكومة تقارن بنغض أو نضض."),
    gap("aed-v1.0:450518", "خرا", "OPEN-CANDIDATE", "land a boat/row لا يطابق خرا أو خلا وحرر بعد حفظ s وẖꜣꜣ، ولا يدخل رسو أو تجذيف من خارج الرسم."),
    gap("aed-v1.0:500193", "حطب", "OPEN-CANDIDATE", "setting of the sun لا يطابق حطب الوقود ولا حتف الموت وحطف الاختطاف؛ لا يحول الغروب إلى مادة الوقود أو الهلاك."),
    gap("aed-v1.0:550075", "غلق", "OPEN-CANDIDATE", "settlement/foundation/newly arable land لا يطابق غلق أو قلق وجرج وبقية المروحة، ولا يدخل قرية أو تأسيس من خارج الرسم."),
    gap("aed-v1.0:600301", "ورش", "OPEN-CANDIDATE", "morning watch/day watch لا يطابق ورش أو ورس وولس في العربية الممسوحة، ولا يدخل حراسة أو صباح من خارج الرسم."),
    gap("aed-v1.0:857437", "نفي", "OPEN-CANDIDATE", "نفي الريح ما تحمله أو ترشه، لا wind/breath نفسها؛ علاقة المحمول بالحامل لا تجعل نفي اسما للريح أو النفس.", sound="n↔ن في IDN-03 وf↔ف في IDN-06؛ w المصرية بإزاء ي العربية في نفي لا يثبت اسما للريح، و.t لاحقة اسمية.", orbit="العربية تسمي أثرا تقذفه الريح أو المطر، والمصرية تسمي الريح أو النفس نفسه؛ بقي فرق السبب والأثر مانعا."),
    gap("aed-v1.0:243", "اخاخ", "OPEN-CANDIDATE", "be verdant/grow green لا يطابق اخاخ أو ءخءخ ولا صور اللام والراء في العربية الممسوحة، ولا يدخل خضر من خارج الرسم."),
    gap("aed-v1.0:10310", "لبلب", "OPEN-CANDIDATE", "be delighted/strongly desire لا يطابق لبلب في العربية الممسوحة، ولا يدخل فرح أو شوق من خارج الرسم."),
    gap("aed-v1.0:20480", "ياوي", "OPEN-CANDIDATE", "grow old/be old لا يطابق ياوي أو يروي ولا صور الهمزة واللام في العربية الممسوحة، ولا يدخل هرم من خارج الرسم."),
    gap("aed-v1.0:20870", "ياخي", "OPEN-CANDIDATE", "be flooded لا يطابق ياخي أو يرخي ولا صور الهمزة واللام في العربية الممسوحة، ولا يدخل غمر أو فيض من خارج الرسم."),
    gap("aed-v1.0:25050", "يماخ", "OPEN-CANDIDATE", "be provided for/revered/revere لا يطابق يماخ أو يملخ ويمرخ في العربية الممسوحة، ولا يدخل رزق أو كرم أو توقير من خارج الرسم."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT
assert {item.state for item in DECISIONS} <= LEGAL_CLOSURES
assert {item.verdict for item in DECISIONS} <= LEGAL_CLOSURES

WITNESS_NOTES = {
    "aed-v1.0:66830": "أثبت لسان العرب وتاج العروس المروَراة للأرض التي لا شيء فيها؛ ثبت تماس الأرض الخالية، وبقي ꜣ↔ر ووصف الجزيرة مانعين.",
    "aed-v1.0:133160": "أثبت الصحاح ولسان العرب فتخ أصابع الرجل بمعنى ثناها ولينها، وفتخ الطائر جناحيه عند الانحطاط؛ ثبت مدار الثني والتلوي بشاهدين قديمين.",
    "aed-v1.0:158820": "أثبت المحكم ولسان العرب السدى لندى الليل، ومكانا سديا بمعنى ندي؛ ثبت مدار البلل، وبقي š↔س واسم قطعة الأرض مانعين.",
    "aed-v1.0:158870": "أثبت لسان العرب وتاج العروس سواد كل كون لما حول القرى والرساتيق؛ ثبت مدار الريف والأرض المعمورة، وبقي قلب d-w وš↔س مانعين.",
}


def round35_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R34.round34_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND34-COMPLETION", "ROUND35-COMPLETION")
    card = card.replace(
        f"round34-egyptian-rank={rank}/{CARD_COUNT}",
        f"round35-egyptian-rank={rank}/{CARD_COUNT}",
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
        raise SystemExit("Round-thirty-five marker already exists; append refused.")

    aramaic_exact, _ = R9.load_entries("aramaic")
    aramaic_queue = R9.select_aramaic(aramaic_text, aramaic_exact)
    assert not aramaic_queue, (
        "Aramaic short live-open queue is no longer exhausted: "
        f"{[item['entry_id'] for item in aramaic_queue[:10]]}"
    )

    egyptian_exact, _ = R9.load_entries("egyptian")
    queue = R34.R33.R32.R31.R30.R29.select_egyptian_fast(
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
        round35_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الخامسة والثلاثون: استمرار المخزون المصري المسجل المفتوح (2026-08-26)", "",
        (
            "أعيد فحص الآرامية أولا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرا، فسجل الانتقال المسمى `{TRANSITION}`. انتقيت ثمانين "
            "بطاقة مصرية بدءا من `WO-C-OPEN-COMP-02063` بقصر الهيكل ثم موضع "
            "اللقطة. استبعد صف ḏ المؤجل. في كل بطاقة عرضت إصابات AED كلها بلا "
            "حد، وكتب وسم الطريق والرسم والمدخل المختار، وحفظ الاختلاف "
            "والمتجانسات بلا محو. فحصت حالة الإغلاق والحكم آليا على القائمة "
            "القانونية وحدها في `data/closure-vocabulary.json`."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-02063 إلى WO-C-OPEN-COMP-02102", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-02103 إلى WO-C-OPEN-COMP-02142", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([
                f"<!-- LANE-C-R35-EGYPTIAN-CHUNK-{rank:03d}:END -->", "",
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
        "## الجولة الخامسة والثلاثون: المسار C، الساميات والمصرية (2026-08-26)", "",
        f"- الوقت: {now}.",
        "- أعيد فحص الساميات أولا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-02063` إلى `WO-C-OPEN-COMP-02102`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-02103` إلى `WO-C-OPEN-COMP-02142`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طبق الانضباط الثلاثي: كل موجب له صوت موقع وحدث مجمد ومدار مكتوب؛ وكل بطاقة أخرى لها عائق شريف مسمى.",
        "- قاموس الإغلاق المغلق وحده مطبق: كل حالات الإغلاق والأحكام اجتازت القائمة القانونية في `data/closure-vocabulary.json`.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ لم يصدر موجب في هذه النافذة.",
        "- أقرب تماس `sptḫ↔فتخ` بقي `TOOL-GAP`: الصوت كامل بعد عزل السابقة السببية والمعنى يلتقيان في الثني، لكن السجل المجمد يهبط إلى نواة `فت` وحدث تكسير الهش.",
        "- المطابقات الدلالية المرفوعة بقيت فجوات قانون: `mꜣw.t↔مرو` للأرض الخالية، و`šd.yt↔سدي` للرطوبة، و`šd.wt↔سود` لأرض القرى والرساتيق.",
        "- وسما القرض السامي العامان في `ḫrp.t` و`ḫrq.t` بقيا `DIRECTION-GAP` بلا مانح فردي أو طريق مكتمل.",
        "- المركبات الأربعة أغلقت `COMPOUND-BOUNDARY`، والأسماء التقويمية والفلكية السبعة أغلقت `OUT-OF-SCOPE`.",
        "- الألفاظ والمراجع المشكوكة أو غير المسماة بقيت `SOURCE-GAP`، وصف ḏ المصري المؤجل بقي مستبعدا.",
        "- لم يحدث شحن أو إيداع أو إعداد مرحلي، ولم يستعمل git أو تحدث مشتقات النشر.", "",
        f"LANE-C DONE35 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
        R34.R33.R32.R31.R30.R29.R28.R27.R26.R25.R24.R23.R20.R10.append(
            EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian,
        )
        R34.R33.R32.R31.R30.R29.R28.R27.R26.R25.R24.R23.R20.R10.append(
            REPORT, f"{MARKER}:REPORT", report,
        )
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
