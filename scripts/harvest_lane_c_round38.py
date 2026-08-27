#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 38 completion cards without shipping or git.

The live short Aramaic queue is checked before the registered Egyptian open
queue continues. The script completes WO-C-OPEN-COMP-02303..02382 in two
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

import harvest_lane_c_round37 as R37


R9 = R37.R9
AR = R37.AR
ROOT = R37.ROOT
ARAMAIC = R37.ARAMAIC
EGYPTIAN = R37.EGYPTIAN
REPORT = R37.REPORT

MARKER = "LANE-C-ROUND38-2026-08-27"
FIRST_SERIAL = 2303
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)
LEGAL_CLOSURES = R37.LEGAL_CLOSURES


def gap(member_id: str, candidate: str, state: str, reason: str,
        sound: str = "المروحة بنيوية فقط؛ لا يرقى التشابه إلى قانون أو نسب.",
        orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
        keywords: str = "", zero: str = "") -> R9.Decision:
    return R37.gap(
        member_id, candidate, state, reason, sound, orbit, keywords, zero,
    )


def terminal(member_id: str, candidate: str, verdict: str, reason: str,
             zero: str = "") -> R9.Decision:
    return R37.terminal(member_id, candidate, verdict, reason, zero)


FEM_T = "عزلت .t علامة التأنيث الاسمية؛ بقيت الصوامت السابقة كاملة بلا إسقاط صامت جذري."
NOM_W = "عزلت .w اللاحقة الاسمية المسجلة؛ بقيت الصوامت السابقة كاملة بلا إسقاط صامت جذري."


# No positive is issued in this window. Grammatical formatives and culturally
# bound labels are isolated; uncertain AED referents remain SOURCE-GAP; the
# two explicit Semitic-loan flags remain DIRECTION-GAP without a named donor.
# Exact semantic contacts outside the licensed fan are retained as LAW-GAP.
DECISIONS: tuple[R9.Decision, ...] = (
    terminal("aed-v1.0:90470", "∅", "OUT-OF-SCOPE", "the divine one هنا تسمية مخصوصة للمبخرة؛ اسم الأداة الثقافي لا يرث حكم الصفة الإلهية ولا يصدر جذرا عربيا من اللقب."),
    gap("aed-v1.0:105380", "حمو", "OPEN-CANDIDATE", "skilled one/expert لا يطابق حمو أو حمي في العربية الممسوحة، ولا يدخل خبرة أو مهارة من خارج الرسم.", zero=FEM_T),
    gap("aed-v1.0:109660", "حزي", "OPEN-CANDIDATE", "praised one لا يطابق حزي في التكهن وخرص النخل وزجر الطير، ولا يدخل حمد أو ثناء من خارج الجذر.", zero=FEM_T),
    terminal("aed-v1.0:110710", "∅", "OUT-OF-SCOPE", "The magical one لقب تاج مصر العليا؛ اسم الشارة الملكية الثقافي لا يصدر جذرا عربيا من صفة السحر."),
    terminal("aed-v1.0:125650", "∅", "OUT-OF-SCOPE", "the two daughters تسمية ثنائية نسبية لشخصيتين مخصوصتين؛ العدد والقرابة لا يؤلفان مادة جذرية مستقلة في هذا العضو."),
    terminal("aed-v1.0:125880", "∅", "OUT-OF-SCOPE", "gold two-thirds fine اسم درجة عيار حسابية لمادة؛ نسبة الثلثين لا تصدر جذرا عربيا من قيمة القياس."),
    terminal("aed-v1.0:128530", "∅", "OUT-OF-SCOPE", "six-weave linen اسم نسيج مصنف بعدد خيوطه؛ التركيب العددي الصناعي لا يعامل جذرا معجميا مفردا."),
    terminal("aed-v1.0:136380", "∅", "OUT-OF-SCOPE", "the two/the two contenders إحالة مثناة إلى طرفين؛ الصيغة الوظيفية لا تمنح مادة معجمية مستقلة."),
    terminal("aed-v1.0:136480", "∅", "OUT-OF-SCOPE", "the second عدد ترتيبي مجرد؛ عزل الأعداد من هذه النافذة لا يصدر جذرا من القيمة الحسابية."),
    terminal("aed-v1.0:142270", "∅", "OUT-OF-SCOPE", "powerful one تسمية مخصوصة للهب؛ لقب الظاهرة الثقافي لا يرث معنى القدرة العام ولا يصدر مقابلا بالقوة."),
    terminal("aed-v1.0:144910", "∅", "OUT-OF-SCOPE", "bright one تسمية مخصوصة للسماء؛ اللقب الكوني لا يحول صفة السطوع إلى جذر عربي في هذا العضو."),
    terminal("aed-v1.0:146550", "∅", "SOURCE-GAP", "الإنجليزية تقترح perishing one بعلامة سؤال، والألمانية تقترح guardian of the body بعلامة سؤال؛ لا مرجع دلالي واحد محكوم للمقارنة."),
    terminal("aed-v1.0:158630", "∅", "OUT-OF-SCOPE", "one of Shedet نسبة موضعية مخصوصة للإله سوبك؛ اسم النسبة الثقافي لا يصدر جذرا عربيا من اسم الموضع."),
    terminal("aed-v1.0:163440", "∅", "OUT-OF-SCOPE", "Hidden-one اسم شيطان مرضي مخصوص؛ الاسم الثقافي لا يرث فعل الإخفاء العام ولا يصدر مقابلا عربيا بالقوة."),
    terminal("aed-v1.0:163470", "∅", "OUT-OF-SCOPE", "hidden one لقب تمويهي للتمساح؛ اسم الحيوان بالكناية لا يساوي فعل الإخفاء ولا يورثه إلى جذر عربي."),
    terminal("aed-v1.0:172940", "∅", "COMPOUND-BOUNDARY", "الرسم `th-mṯn` ذو حدين موصولين ويسمي متجاوز الطريق؛ حد المركب يمنع حمل المجموع على جذر عربي مفرد."),
    gap("aed-v1.0:176490", "ثهثه", "OPEN-CANDIDATE", "lame one لا يطابق ثهثه أو تهته وطهطه في العربية الممسوحة، ولا يدخل عرج أو عوق من خارج الرسم."),
    terminal("aed-v1.0:177870", "∅", "OUT-OF-SCOPE", "fiver/troop of five workers اسم فرقة مهنية مبني على العدد خمسة؛ اللقب المؤسسي العددي لا يصدر جذرا من العدد."),
    terminal("aed-v1.0:600040", "∅", "OUT-OF-SCOPE", "each one صفة توزيعية وظيفية مكررة؛ لا مادة جذرية معجمية مستقلة قابلة لحكم النسب."),
    terminal("aed-v1.0:600044", "∅", "COMPOUND-BOUNDARY", "الرسم `wꜥ-nb` مركب توزيعي بمعنى each one؛ حد المركب يمنع تسوية الجزأين بجذر عربي مفرد."),
    terminal("aed-v1.0:850571", "∅", "OUT-OF-SCOPE", "four اسم عدد مجرد؛ عزل العدد لا يصدر جذرا عربيا من القيمة الحسابية."),
    terminal("aed-v1.0:860191", "∅", "OUT-OF-SCOPE", "the double plume/Two Feather Crown اسم شارة ملكية ثنائية مخصوصة؛ اسم التاج لا يصدر جذرا عربيا من الريش أو التثنية."),
    terminal("aed-v1.0:22030", "∅", "OUT-OF-SCOPE", "who not/which not ضمير وصل منفي وظيفي؛ لا تحليل جذري معجمي منشور يجيز إدخاله في قياس الجذور."),
    terminal("aed-v1.0:90020", "∅", "OUT-OF-SCOPE", "he ضمير شخصي منفصل للغائب المفرد؛ لا مادة جذرية مستقلة في المدخل."),
    terminal("aed-v1.0:90120", "∅", "OUT-OF-SCOPE", "you ضمير شخصي منفصل للمخاطب المفرد؛ لا مادة جذرية مستقلة في المدخل."),
    terminal("aed-v1.0:32050", "∅", "OUT-OF-SCOPE", "what ضمير استفهام وظيفي؛ لا تحليل جذري معجمي منشور يحوله إلى اسم شيء."),
    terminal("aed-v1.0:97660", "∅", "OUT-OF-SCOPE", "O that جزيء تمن واستحسان وظيفي؛ الأداة الخطابية لا تعامل جذرا معجميا لمجرد المروحة السطحية."),
    terminal("aed-v1.0:450730", "∅", "OUT-OF-SCOPE", "those ضمير إشارة لجمع المؤنث؛ لا مادة جذرية مفردة مستقلة في المصدر."),
    terminal("aed-v1.0:550018", "∅", "OUT-OF-SCOPE", "that أداة ربط ومصدرية؛ الوظيفة النحوية لا تصدر جذرا معجميا من الرسم."),
    terminal("aed-v1.0:550052", "∅", "OUT-OF-SCOPE", "she of بادئة ملكية للمفرد المؤنث؛ لا مادة جذرية مستقلة قابلة للمقارنة."),
    gap("aed-v1.0:24", "أعع", "OPEN-CANDIDATE", "container/jar لا يطابق أعع أو أضع وأغع في العربية الممسوحة، ولا يدخل وعاء أو جرة من خارج الرسم.", zero=FEM_T),
    gap("aed-v1.0:97", "أبد", "OPEN-CANDIDATE", "monthly لا يطابق أبد في الدهر والدوام؛ الشهر الدوري المحدود لا يصير خلودا لمجرد التشابه.", zero=NOM_W),
    gap("aed-v1.0:141", "أمع", "SOURCE-GAP", "AED لا يسمي إلا a mash طبي بين معقوفين بلا مادة أو تركيب محكوم؛ لا مرجع دلالي معين يقارن بأمع أو أمعط.", zero=FEM_T),
    gap("aed-v1.0:146", "أمم", "OPEN-CANDIDATE", "grasp/grip لا يطابق أمم في القصد والتقدم والأمة، ولا يدخل قبض أو مسك من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:167", "أرك", "OPEN-CANDIDATE", "clay لا يطابق أرك أو ألك في العربية الممسوحة، ولا يدخل طين أو صلصال من خارج الرسم.", zero=FEM_T),
    gap("aed-v1.0:250", "ياخي", "OPEN-CANDIDATE", "sweep the harvest together لا يطابق ياخي أو يرخى في المروحة، ولا يدخل كنس أو جمع من خارج الجذر."),
    gap("aed-v1.0:261", "أخع", "OPEN-CANDIDATE", "scratch/scar لا يطابق أخع أو أحع وبقية المروحة، ولا يدخل خدش أو ندبة من خارج الرسم.", zero=FEM_T),
    gap("aed-v1.0:286", "أشي", "SOURCE-GAP", "AED لا يفسر إلا worsening condition of a wound بين معقوفين بلا تعيين الظاهرة؛ لا حدث مرضي محكوم يقارن بأشي.", zero=FEM_T),
    gap("aed-v1.0:314", "أغب", "OPEN-CANDIDATE", "flood/abundance لا يطابق أغب أو أقب وأجب في العربية الممسوحة، ولا يدخل فيض أو كثرة من خارج الرسم.", zero=NOM_W),
    gap("aed-v1.0:336", "أثي", "OPEN-CANDIDATE", "nurse/attendant لا يطابق أثي أو أتي وأطي في العربية الممسوحة، ولا يدخل رضاع أو خدمة من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:20320", "ياي", "OPEN-CANDIDATE", "tresses في وصف الراقصات لا يطابق ياي أو يلي ويري في العربية الممسوحة، ولا يدخل ضفيرة أو شعر من خارج الرسم.", zero=NOM_W),
    terminal("aed-v1.0:20420", "∅", "OUT-OF-SCOPE", "the emblem of Min's cult اسم شارة عبادية غير معينة؛ الأثر الثقافي لا يصدر جذرا عربيا من اسم المعبود."),
    gap("aed-v1.0:20690", "ياب", "SOURCE-GAP", "AED يتردد بين pole وplank بعلامتي سؤال؛ لا نوع أداة واحد محكوم يقارن بياب أو ياف.", zero=FEM_T),
    gap("aed-v1.0:20990", "ياق", "OPEN-CANDIDATE", "leeks/vegetables لا يطابق ياق أو يلق ويرق في العربية الممسوحة، ولا يدخل كراث أو بقل من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:21080", "أذى", "LAW-GAP", "الأذى هو المكروه والضرر فيطابق injury دلاليا، لكن المقابل خارج سطح المروحة وj-ꜣ-ṯ لا يسوي ء-ذ-y بلا ثلاثة صفوف مصرية موقعة.", sound="ثبت مدار أذى دلاليا؛ بقي j↔ء وꜣ↔ي وṯ↔ذ بلا مسار مصري فردي مكتمل.", orbit="الأذى مكروه وضرر يصيب المرء، وهو مدار injury مباشرة؛ بقي الصوت مانعا لكل ترقية.", keywords="الأذى|الضرر|المكروه|آذاه", zero=FEM_T),
    gap("aed-v1.0:21650", "يعب", "SOURCE-GAP", "AED يتردد بين bunch وheap للقرابين بعلامتي سؤال؛ لا بنية مادية واحدة محكومة تقارن بيعب أو يغب.", zero=FEM_T),
    gap("aed-v1.0:21750", "يعن", "OPEN-CANDIDATE", "grief/woe لا يطابق يعن أو يضن ويغن في العربية الممسوحة، ولا يقلب إلى عناء بإسقاط الصامت الأول ونقل الواو.", zero=NOM_W),
    gap("aed-v1.0:22250", "يوا", "OPEN-CANDIDATE", "removal/transport away لا يطابق يوا أو يول ويور في العربية الممسوحة، ولا يدخل نزع أو نقل من خارج الرسم.", zero=NOM_W),
    gap("aed-v1.0:22680", "يون", "SOURCE-GAP", "AED لا يعين إلا something made of cloth ويتردد بين bag وclothing؛ لا شيء مادي واحد محكوم يقارن بيون.", zero=FEM_T),
    terminal("aed-v1.0:22860", "∅", "OUT-OF-SCOPE", "He-of-Heliopolis تسمية موضعية مخصوصة لعصا؛ اسم الأداة المنسوبة لا يصدر جذرا من اسم المدينة."),
    gap("aed-v1.0:23530", "يبا", "OPEN-CANDIDATE", "dance/entertainment لا يطابق يبا أو يبل ويبر في العربية الممسوحة، ولا يدخل رقص أو لهو من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:23880", "يبخ", "SOURCE-GAP", "AED لا يسمي إلا a medical liquid بين معقوفين بلا مادة أو وظيفة؛ لا مرجع دوائي معين يقارن بيبخ.", zero="عزلت .j اللاحقة الاسمية المسجلة؛ بقي j-b-ḫ كاملا بلا إسقاط صامت جذري."),
    gap("aed-v1.0:23940", "يبس", "SOURCE-GAP", "AED يتردد بين catafalque وcoffin بعلامتي سؤال؛ لا نوع صندوق جنائزي واحد محكوم يقارن بيبس أو يبش.", zero=NOM_W),
    gap("aed-v1.0:23990", "يبث", "OPEN-CANDIDATE", "bird-trap لا يطابق يبث أو يبت ويبط في العربية الممسوحة، ولا يدخل فخ أو شبكة من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:24510", "يبد", "OPEN-CANDIDATE", "furniture في العموم لا يطابق يبد أو يفد وبقية المروحة، ولا يدخل أثاث أو متاع من خارج الرسم.", zero=NOM_W),
    gap("aed-v1.0:24590", "يفد", "OPEN-CANDIDATE", "sheet/linen garment لا يطابق يفد أو يفض في العربية الممسوحة، ولا يدخل ثوب أو نسيج من خارج الجذر.", zero="عزلت .j اللاحقة الاسمية المسجلة؛ بقي j-f-d كاملا بلا إسقاط صامت جذري."),
    gap("aed-v1.0:25030", "يماخ", "SOURCE-GAP", "AED لا يسمي إلا a kind of incense بين معقوفين بلا تعيين مادته؛ لا مرجع عطري محكوم يقارن بيماخ أو يمرخ."),
    terminal("aed-v1.0:25560", "∅", "COMPOUND-BOUNDARY", "الرسم `jm.j-rʾ` ذو حدين موصولين ويسمي utterance؛ حد المركب يمنع حمل المجموع على جذر عربي مفرد."),
    gap("aed-v1.0:25930", "يميم", "SOURCE-GAP", "AED لا يقدم إلا verb، والألمانية تقترح negative action بعلامة سؤال؛ لا حدث معجمي محكوم يقارن بيميم."),
    gap("aed-v1.0:26340", "يمنح", "OPEN-CANDIDATE", "butcher لا يطابق يمنح في العطاء ولا أمنح، ولا يدخل ذبح أو جزر من خارج الرسم."),
    gap("aed-v1.0:26500", "يمتر", "SOURCE-GAP", "AED لا يسمي إلا a bird بعلامة سؤال؛ لا نوع طائر أو صفة محكومة تقارن بيمتر أو يمطر."),
    gap("aed-v1.0:27090", "ينو", "SOURCE-GAP", "freight/shipload موسومان بعلامة سؤال؛ لا حمولة بحرية محكومة يقارن بها ينو أو يون.", zero=FEM_T),
    gap("aed-v1.0:27520", "يننك", "SOURCE-GAP", "AED يتردد في النبات بين thyme وKonyza بعلامتي سؤال؛ لا نوع نبات واحد محكوم يقارن بيننك."),
    gap("aed-v1.0:27670", "ينرن", "DIRECTION-GAP", "المصدر لا يعطي إلا وسم Semitic loan word وإحالة Hoch رقم 11؛ لا مانح سامي فردي ولا طريق نقل مكتمل إلى المصرية أو العربية.", sound="الرسم المصري محفوظ، لكن وسم السامية العام لا يوقع صفوف ينرن مع جذر عربي بعينه.", orbit="oak نوع شجر محدد؛ غاب اسم مانح فردي ومسار انتقال يربط اللفظ بمادة عربية محكومة."),
    gap("aed-v1.0:27830", "ينس", "SOURCE-GAP", "AED لا يسمي إلا a medical plant بين معقوفين بلا نوع أو أثر دوائي؛ لا مرجع نباتي محكوم يقارن بينس أو ينش.", zero=FEM_T),
    gap("aed-v1.0:27910", "ينق", "OPEN-CANDIDATE", "net بمعنى encloser لا يطابق ينق أو أنق في العربية الممسوحة، ولا يدخل شبكة أو إحاطة من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:29570", "يرو", "SOURCE-GAP", "AED لا يسمي إلا a vessel بين معقوفين بلا نوع أو وظيفة؛ لا وعاء معين محكوم يقارن بيرو أو يلو.", zero=FEM_T),
    gap("aed-v1.0:29940", "يرجس", "SOURCE-GAP", "AED لا يسمي إلا a basket بين معقوفين بلا نوع أو مادة؛ لا سلة محكومة يقارن بها يرجس أو يرقس."),
    gap("aed-v1.0:30000", "يرت", "OPEN-CANDIDATE", "purple cloth لا يطابق يرت أو يلت في العربية الممسوحة، ولا يدخل أرجوان أو نسيج من خارج الرسم.", zero=NOM_W),
    gap("aed-v1.0:30370", "يهح", "OPEN-CANDIDATE", "festival of jubilation لا يطابق يهح أو يهه ويحح في العربية الممسوحة، ولا يدخل عيد أو فرح من خارج الجذر."),
    gap("aed-v1.0:30960", "يخخ", "OPEN-CANDIDATE", "twilight/darkness لا يطابق يخخ في العربية الممسوحة، ولا يدخل غسق أو ظلمة من خارج الرسم.", zero=NOM_W),
    gap("aed-v1.0:31420", "يسبر", "DIRECTION-GAP", "المصدر لا يعطي إلا وسم Semitic loan word وإحالة Hoch رقم 28؛ لا مانح فردي أو اتجاه نقل مكتمل، وسبر العربية للاختبار لا يثبت whip.", sound="وسم القرض السامي عام؛ لا يوقع j-s-b-r مع العربية س-b-r ولا يفسر الصامت الأول.", orbit="المصرية تسمي whip، والعربية في سبر تسمي الاختبار وقياس غور الجرح؛ لا مدار أداة ضرب مباشر ولا طريق قرض فردي."),
    gap("aed-v1.0:31580", "يزن", "SOURCE-GAP", "AED لا يقدم إلا noun/Substantiv بلا تعيين المعنى؛ لا حدث أو شيء محكوم يقارن بيزن أو يسن.", zero=NOM_W),
    gap("aed-v1.0:31620", "أثل", "LAW-GAP", "الأثل شجر يشبه الطرفاء فيطابق tamarisk دلاليا، لكن المقابل خارج سطح المروحة وj-z-r لا يسوي ء-ث-l بلا صفوف مصرية موقعة مكتملة.", sound="ثبت اسم الأثل العربي للشجر الشبيه بالطرفاء؛ بقي z↔ث وr↔ل، ومعهما الابتداء j↔ء، بلا مسار مصري مكتمل.", orbit="الأثل هو شجر الطرفاء أو شجر يشبهها، وهو مدار tamarisk مباشرة؛ بقي الصوت مانعا لكل ترقية.", keywords="الأثل|شجر|الطرفاء|شجرة", zero=FEM_T),
    gap("aed-v1.0:32040", "يشر", "OPEN-CANDIDATE", "hoe لا يطابق يشر؛ المعجم لا يثبت فيه إلا اسم موضع، ولا يدخل فأس أو مسحاة من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:32120", "يشكن", "OPEN-CANDIDATE", "sash/girdle لا يطابق يشكن أو يسكن في العربية الممسوحة، ولا يدخل حزام أو وشاح من خارج الرسم."),
    gap("aed-v1.0:32170", "يشد", "OPEN-CANDIDATE", "ished-fruit/fruit لا يطابق يشد أو يسد في العربية الممسوحة، ولا يدخل ثمر من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:32220", "يقم", "OPEN-CANDIDATE", "sadness/sorrow لا يطابق يقم أو أقم في العربية الممسوحة، ولا يدخل حزن أو غم من خارج الرسم.", zero=NOM_W),
    gap("aed-v1.0:32310", "يقر", "SOURCE-GAP", "AED لا يسمي إلا a medical tree بين معقوفين بلا نوع أو أثر؛ لا شجر معين محكوم يقارن بيقر أو يقل.", zero=NOM_W),
    gap("aed-v1.0:32530", "يكب", "SOURCE-GAP", "AED لا يسمي إلا a mineral pigment بين معقوفين بلا معدن أو لون؛ لا صباغ معين محكوم يقارن بيكب.", zero=NOM_W),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT
assert {item.state for item in DECISIONS} <= LEGAL_CLOSURES
assert {item.verdict for item in DECISIONS} <= LEGAL_CLOSURES

OUTSIDE_FAN = {"aed-v1.0:21080", "aed-v1.0:31620"}

WITNESS_NOTES = {
    "aed-v1.0:21080": "أثبت تاج العروس الأذى للمكروه والضرر الخفيف؛ ثبت مدار injury، وبقيت صفوف j-ꜣ-ṯ بإزاء ء-ذ-y غير موقعة.",
    "aed-v1.0:31620": "أثبت المحكم ولسان العرب أن الأثل شجر يشبه الطرفاء؛ ثبت مدار tamarisk، وبقيت صفوف j-z-r بإزاء ء-ث-l غير موقعة.",
}


def round38_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R37.round37_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND37-COMPLETION", "ROUND38-COMPLETION")
    card = card.replace(
        f"round37-egyptian-rank={rank}/{CARD_COUNT}",
        f"round38-egyptian-rank={rank}/{CARD_COUNT}",
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
        card = re.sub(
            r"(?m)^- مسح المعاني العربية:.*$",
            (
                f"- مسح المعاني العربية: قرئت {count} نتيجة للجذر `{root}` "
                f"بما يكافئ `--max-chars 0`؛ {note}"
            ),
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
        raise SystemExit("Round-thirty-eight marker already exists; append refused.")

    aramaic_exact, _ = R9.load_entries("aramaic")
    aramaic_queue = R9.select_aramaic(aramaic_text, aramaic_exact)
    assert not aramaic_queue, (
        "Aramaic short live-open queue is no longer exhausted: "
        f"{[item['entry_id'] for item in aramaic_queue[:10]]}"
    )

    egyptian_exact, _ = R9.load_entries("egyptian")
    queue = R37.R36.R35.R34.R33.R32.R31.R30.R29.select_egyptian_fast(
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
        round38_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الثامنة والثلاثون: استمرار المخزون المصري المسجل المفتوح (2026-08-27)", "",
        (
            "أعيد فحص الآرامية أولا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرا، فسجل الانتقال المسمى `{TRANSITION}`. انتقيت ثمانين "
            "بطاقة مصرية بدءا من `WO-C-OPEN-COMP-02303` بقصر الهيكل ثم موضع "
            "اللقطة. استبعد صف ḏ المؤجل. في كل بطاقة عرضت إصابات AED كلها بلا "
            "حد، وكتب وسم الطريق والرسم والمدخل المختار، وحفظ الاختلاف "
            "والمتجانسات بلا محو. فحصت حالة الإغلاق والحكم آليا على القائمة "
            "القانونية وحدها في `data/closure-vocabulary.json`."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-02303 إلى WO-C-OPEN-COMP-02342", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-02343 إلى WO-C-OPEN-COMP-02382", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([
                f"<!-- LANE-C-R38-EGYPTIAN-CHUNK-{rank:03d}:END -->", "",
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
        "## الجولة الثامنة والثلاثون: المسار C، الساميات والمصرية (2026-08-27)", "",
        f"- الوقت: {now}.",
        "- أعيد فحص الساميات أولا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-02303` إلى `WO-C-OPEN-COMP-02342`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-02343` إلى `WO-C-OPEN-COMP-02382`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طبق الانضباط الثلاثي: لم يصدر موجب في هذه النافذة؛ وكل بطاقة لها عائق شريف مسمى.",
        "- قاموس الإغلاق المغلق وحده مطبق: كل حالات الإغلاق والأحكام اجتازت القائمة القانونية في `data/closure-vocabulary.json`.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ لم يصدر موجب جديد.",
        "- المطابقتان الدلاليتان المرفوعتان `jꜣṯ.t↔أذى` للإصابة و`jzr.t↔أثل` للطرفاء بقيتا `LAW-GAP`: المعنى مباشر، لكن المقابلين خارج سطح المروحة وصفوف الصوت غير موقعة.",
        "- وسما القرض السامي في `jnrn` لشجر البلوط و`jsbr` للسوط بقيا `DIRECTION-GAP`: لا مانح فردي ولا طريق نقل مكتمل، ولم يرث سبر العربية معنى whip.",
        "- المراجع النباتية والطبية والأدوات الموسومة بين معقوفين أو بعلامة سؤال بقيت `SOURCE-GAP`؛ لم يحسم التخمين نوع الشيء بالقوة.",
        "- الضمائر والأعداد والأدوات والألقاب الثقافية أغلقت `OUT-OF-SCOPE`، والمركبات ذات الحدود المكتوبة أغلقت `COMPOUND-BOUNDARY`.",
        "- لم يحدث شحن أو إيداع أو إعداد مرحلي، ولم يستعمل git أو تحدث مشتقات النشر.", "",
        f"LANE-C DONE38 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
        append = (
            R37.R36.R35.R34.R33.R32.R31.R30.R29.R28.R27.R26.R25.R24.R23.R20.R10.append
        )
        append(EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian)
        append(REPORT, f"{MARKER}:REPORT", report)
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
