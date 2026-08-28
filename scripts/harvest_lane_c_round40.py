#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 40 completion cards without shipping or git.

The live short Aramaic queue is checked before the registered Egyptian open
queue continues. The script completes WO-C-OPEN-COMP-02463..02542 in two
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

import harvest_lane_c_round39 as R39


R9 = R39.R9
AR = R39.AR
ROOT = R39.ROOT
ARAMAIC = R39.ARAMAIC
EGYPTIAN = R39.EGYPTIAN
REPORT = R39.REPORT

MARKER = "LANE-C-ROUND40-2026-08-27"
FIRST_SERIAL = 2463
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)
LEGAL_CLOSURES = R39.LEGAL_CLOSURES


def pos(member_id: str, candidate: str, verdict: str, keywords: str,
        sound: str, orbit: str, reason: str, zero: str = "") -> R9.Decision:
    return R39.pos(
        member_id, candidate, verdict, keywords, sound, orbit, reason, zero,
    )


def gap(member_id: str, candidate: str, state: str, reason: str,
        sound: str = "المروحة بنيوية فقط؛ لا يرقى التشابه إلى قانون أو نسب.",
        orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
        keywords: str = "", zero: str = "") -> R9.Decision:
    return R39.gap(
        member_id, candidate, state, reason, sound, orbit, keywords, zero,
    )


def terminal(member_id: str, candidate: str, verdict: str, reason: str,
             zero: str = "") -> R9.Decision:
    return R39.terminal(member_id, candidate, verdict, reason, zero)


FEM_T = R39.FEM_T
NOM_W = R39.NOM_W
NISBE_J = R39.NISBE_J


# The one positive in this window is mwt.t: after the recorded feminine .t is
# isolated, Egyptian m-w-t and Arabic موت agree in sound and in the dead-person
# orbit. Generic or uncertain source labels remain SOURCE-GAP; general Semitic
# loan labels without a named donor and route remain DIRECTION-GAP.
DECISIONS: tuple[R9.Decision, ...] = (
    terminal("aed-v1.0:60081", "∅", "OUT-OF-SCOPE", "belonging to someone صفة إحالية مبنية على حرف جر؛ الوظيفة النحوية لا تصدر جذرا عربيا معجميا مستقلا."),
    gap("aed-v1.0:60120", "بنس", "OPEN-CANDIDATE", "clump of medication لا يطابق بنس أو فنس في العربية الممسوحة، ولا يدخل كتلة أو دواء من خارج الجذر.", zero=FEM_T),
    terminal("aed-v1.0:60430", "∅", "COMPOUND-BOUNDARY", "الرسم `pr-ꜥꜣ` ذو حدين موصولين ومحلل إلى great house؛ حد البيت والعظمة يمنع حمل palace/pharaoh على جذر عربي مفرد."),
    gap("aed-v1.0:61930", "بحر", "OPEN-CANDIDATE", "ambulatory بوصفه ممشى يحيط بمعبد لا يطابق بحر أو بخر وبقية المروحة، ولا يدخل طواف أو ممر من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:63130", "بدس", "OPEN-CANDIDATE", "small medicinal ball لا يطابق بدس أو بضس وفدس في العربية الممسوحة، ولا يدخل حبة أو كرة من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:63530", "فري", "OPEN-CANDIDATE", "bearers of a divine image لا يطابق فري في الشق والقطع، ولا يرث حامل الصورة معنى حمل من جذر خارج الرسم.", zero=FEM_T),
    gap("aed-v1.0:64170", "فتف", "OPEN-CANDIDATE", "to leap أو sprout لا يطابق فتف أو فطف في العربية الممسوحة، ولا يدخل وثب أو نبت من خارج الرسم."),
    terminal("aed-v1.0:64630", "∅", "OUT-OF-SCOPE", "`m-ꜥqꜣ` حرف جر وظيفي لمعنى بإزاء أو على؛ الوظيفة المركبة لا تعامل مادة جذرية عربية مفردة."),
    terminal("aed-v1.0:64840", "∅", "OUT-OF-SCOPE", "`m-mjn` ظرف زمان بمعنى today؛ الأداة الظرفية لا تصدر جذرا معجميا من اسم اليوم."),
    terminal("aed-v1.0:65370", "∅", "OUT-OF-SCOPE", "`m-ẖnw` حرف جر مكاني لمعاني الداخل والضمن؛ الوظيفة النحوية لا تحمل على جذر عربي مفرد."),
    gap("aed-v1.0:66230", "مات", "SOURCE-GAP", "pair of terminations ومعنى ends موسومان بالمعقوفات وعلامات السؤال، ومرجع الوتر نفسه محتمل؛ لا عضو مزدوج محكوم يقارن بمات أو ماط."),
    gap("aed-v1.0:66680", "ماع", "SOURCE-GAP", "AED لا يسمي إلا a kind of wood بين معقوفين بلا نوع أو خصائص؛ لا خشب معين محكوم يقارن بماع أو ماغ.", zero=NOM_W),
    gap("aed-v1.0:66770", "ماع", "OPEN-CANDIDATE", "regularity أو correctness لا يطابق ماع أو ماغ وبقية المروحة في العربية الممسوحة، ولا يدخل صحة أو انتظام من خارج الرسم.", zero=NOM_W),
    gap("aed-v1.0:66850", "مرو", "OPEN-CANDIDATE", "stalk of grain أو reed لا يطابق مرو في الحجر الأبيض والأرض الخالية، ولا يدخل ساق أو قصب من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:67450", "مرق", "OPEN-CANDIDATE", "ladder لا يطابق مرق في الخروج والنفاذ، ولا يحول فعل الصعود المحتمل إلى اسم للسلم.", zero=FEM_T),
    gap("aed-v1.0:67660", "ماتر", "SOURCE-GAP", "التعريف الألماني يضع weep for a dead person موضع سؤال؛ لا فعل رثاء ثنائي المصدر محكوم يقارن بماتر أو ماثر."),
    gap("aed-v1.0:68160", "ميز", "SOURCE-GAP", "spines موسوم بعلامة سؤال، والألمانية تتردد في ماهية الشيء نفسه؛ لا شوك معين محكوم يقارن بميز أو ميس."),
    terminal("aed-v1.0:68220", "∅", "OUT-OF-SCOPE", "the same as تعبير إحالي للمماثلة لا اسم شيء أو حدث معجمي؛ لا يصدر جذر عربي من وظيفة الإحالة."),
    gap("aed-v1.0:68320", "ميم", "SOURCE-GAP", "AED لا يسمي إلا a cereal بين معقوفين ويقترح durra بعلامة سؤال؛ لا نوع حبوب محكوم يقارن بميم.", zero=NISBE_J),
    terminal("aed-v1.0:68390", "∅", "OUT-OF-SCOPE", "`mj-nꜣ` ظرف إشارة مكانية بمعنى here؛ حد الأداة والإشارة يعزل الوظيفة عن الجذور المعجمية."),
    gap("aed-v1.0:68490", "ميس", "SOURCE-GAP", "AED لا يسمي إلا horned animal ويقترح antelope بعلامة سؤال؛ لا نوع حيوان محكوم يقارن بميس أو ميز.", zero=FEM_T),
    gap("aed-v1.0:68630", "معي", "OPEN-CANDIDATE", "loop أو eyelet لا يطابق معي أو مضي ومغي في العربية الممسوحة، ولا يدخل عروة أو حلقة من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:69240", "موي", "SOURCE-GAP", "liquid الطبي عام، والألمانية تتردد بين moisture وurine؛ لا سائل واحد معين محكوم يقارن بموي.", zero=FEM_T),
    pos("aed-v1.0:69330", "موت", "ROOT-TRACE", "الموت|ضد الحياة|ميت|مات", "m↔م في IDN-02 وw↔و في IDN-10 وt↔ت في IDN-11؛ الجذر كامل بعد عزل تاء التأنيث.", "الميت من فارق الحياة، وهو dead person مباشرة؛ قيد الروح المؤذية وصف ثقافي للعضو ولا يوسع الحكم.", "TRACE مقصور على اسم الميت وحالة الموت في هذا العضو؛ لا يورث التصور الثقافي للأرواح.", zero=FEM_T),
    gap("aed-v1.0:69900", "منت", "OPEN-CANDIDATE", "the two mountain ranges east and west of the Nile لا يطابق منت أو منط في العربية الممسوحة، ولا يدخل جبل أو شرق وغرب من خارج الجذر."),
    gap("aed-v1.0:70140", "مين", "OPEN-CANDIDATE", "mooring post لا يطابق مين أو مئن في العربية الممسوحة، ولا يدخل وتد أو مرسى من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:70380", "منع", "OPEN-CANDIDATE", "male nurse أو educator لا يطابق منع في خلاف الإعطاء والحماية، ولا يدخل رضاع أو تربية من خارج الجذر.", zero=NISBE_J),
    terminal("aed-v1.0:70560", "∅", "OUT-OF-SCOPE", "rich in monuments صفة ثقافية إحالية مشتقة من كثرة الآثار؛ الوصف لا يصدر جذرا عربيا من اسم الأثر أو الغنى."),
    gap("aed-v1.0:70630", "منفح", "SOURCE-GAP", "الإنجليزية تتردد بين cloth وhide والألمانية لا تقدم إلا a garment بين معقوفين؛ لا مادة لباس واحدة محكومة تقارن بمنفح."),
    gap("aed-v1.0:70720", "منمن", "OPEN-CANDIDATE", "to impregnate أو mate لا يطابق منمن في العربية الممسوحة، ولا يدخل نكاح أو حبل من خارج الرسم."),
    gap("aed-v1.0:70820", "منن", "SOURCE-GAP", "AED لا يسمي إلا part of a granite sarcophagus أو part of a tomb بين معقوفين بلا موضع أو وظيفة؛ لا جزء معماري محكوم يقارن بمنن.", zero=FEM_T),
    gap("aed-v1.0:70900", "منحس", "OPEN-CANDIDATE", "watcher أو guard لا يطابق منحس أو منهز في العربية الممسوحة، ولا يدخل حرس أو رقب من خارج الجذر."),
    gap("aed-v1.0:73120", "محي", "SOURCE-GAP", "AED لا يسمي إلا a fruit بين معقوفين بلا نوع أو صفات؛ لا ثمرة معينة محكومة تقارن بمحي أو مهي.", zero=FEM_T),
    gap("aed-v1.0:73590", "محوس", "SOURCE-GAP", "grain of Lower Egypt لا يعين نوع الحبوب أو صفاته، واللاحقة =s باقية في العضو؛ لا نبات معين محكوم يقارن بمحوس."),
    gap("aed-v1.0:73850", "محي", "OPEN-CANDIDATE", "papyrus لا يطابق محي في المحو ولا مهي، ولا يدخل بردي أو قرطاس من خارج الجذر.", zero=FEM_T),
    terminal("aed-v1.0:74000", "∅", "OUT-OF-SCOPE", "Lower Egyptian/northern صفة جغرافية إحالية إلى الإقليم؛ النسبة المكانية لا تصدر جذرا عربيا من اسم الشمال."),
    gap("aed-v1.0:74410", "مخن", "OPEN-CANDIDATE", "forehead أو countenance لا يطابق مخن في الطول والبكاء ونزح البئر، ولا يدخل جبهة أو وجه من خارج الجذر."),
    gap("aed-v1.0:74610", "محن", "OPEN-CANDIDATE", "ferry-boat لا يطابق محن في الاختبار والشدة ولا مخن، ولا يدخل سفينة أو عبور من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:74680", "محر", "OPEN-CANDIDATE", "provisions أو offerings لا يطابق محر أو محل في العربية الممسوحة، ولا يدخل زاد أو قربان من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:75060", "مسوت", "OPEN-CANDIDATE", "descendants لا يطابق مسوت أو مشوت ومصوت في العربية الممسوحة، ولا يدخل نسل أو عقب من خارج الرسم."),
    gap("aed-v1.0:75270", "مسبب", "OPEN-CANDIDATE", "turn towards أو serve أو deal with لا يطابق مسبب في إحداث السبب، ولا يدخل توجه أو خدمة من خارج الجذر."),
    gap("aed-v1.0:75500", "مسن", "OPEN-CANDIDATE", "knife لا يطابق مسن في الضرب بالسوط أو الاستلال؛ ولا يورث السكين اسم حجر السن أو فعل السن من خارج العضو.", zero=NISBE_J),
    gap("aed-v1.0:75700", "مسخع", "OPEN-CANDIDATE", "splendor of gods لا يطابق مسخع أو مشخع في العربية الممسوحة، ولا يدخل نور أو بهاء من خارج الرسم."),
    gap("aed-v1.0:75890", "مسكا", "OPEN-CANDIDATE", "leather أو hide لا يطابق مسكا ومشكا وبقية المروحة في العربية الممسوحة، ولا يدخل جلد أو أديم من خارج الجذر."),
    gap("aed-v1.0:75960", "مست", "SOURCE-GAP", "AED لا يسمي إلا a bag بين معقوفين بلا مادة أو وظيفة، واحتمال cloth نفسه غير محسوم؛ لا وعاء معين يقارن بمست.", zero=NOM_W),
    gap("aed-v1.0:76060", "مستر", "DIRECTION-GAP", "office/chancellery موسوم Sem. loan word بلا مانح سامي فردي أو طريق انتقال، ولا تسمي مستر أو مسطر هذا المكتب.", orbit="المصرية تسمي مؤسسة كتابية أو مكتبا؛ بقي المانح الفردي وطريق النقل والمعنى العربي غير محكومة."),
    gap("aed-v1.0:76290", "مشرب", "DIRECTION-GAP", "watering place يطابق المشرب موضع الشرب دلاليا، لكن وسم Sem. loan word لا يسمي المانح أو الطريق، وꜣ المصرية بإزاء ر العربية بلا صف موقع.", sound="m↔م في IDN-02 وš↔ش وb↔ب في IDN-05؛ بقي ꜣ↔ر بلا صف مصري موقع ولا مانح فردي.", orbit="المشرب موضع الشرب، وهو watering place مباشرة؛ بقي اتجاه النقل والصامت الأوسط مانعين.", keywords="المشرب|موضع الشرب|الشرب|الماء"),
    gap("aed-v1.0:76650", "مقعر", "DIRECTION-GAP", "firebox أو baker's oven موسوم Sem. loan word بلا مانح أو طريق، وتقعر الشيء لا يسمي فرن الخباز نفسه.", orbit="التقعر يصف هيئة جوفاء محتملة، أما المصرية فتسمي صندوق النار أو الفرن؛ بقي المعنى المعجمي والاتجاه مفتوحين."),
    gap("aed-v1.0:76880", "مكوت", "OPEN-CANDIDATE", "protection أو magical protection لا يطابق مكوت وبقية المروحة في العربية الممسوحة، ولا يدخل وقاية أو حفظ من خارج الجذر."),
    gap("aed-v1.0:76990", "مكا", "OPEN-CANDIDATE", "support أو pedestal أو bier لا يطابق مكا أو مكل ومكر في العربية الممسوحة، ولا يدخل سند أو نعش من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:77060", "مكر", "DIRECTION-GAP", "merchant موسوم Sem. loan word بلا مانح سامي فردي أو طريق انتقال، ومكر العربية لا يسمي التاجر.", zero=NISBE_J),
    gap("aed-v1.0:77140", "مكتر", "DIRECTION-GAP", "tower موسوم Sem. loan word بلا مانح سامي فردي أو طريق انتقال، ولا تسمي مكتر أو مكطر برج التحصين."),
    gap("aed-v1.0:77260", "مقسب", "DIRECTION-GAP", "crate/basket موسوم Sem. loan word بعلامة سؤال وبلا مانح فردي أو طريق، ولا تسمي مقسب أو مجسب صندوقا أو سلة."),
    gap("aed-v1.0:77360", "باق", "SOURCE-GAP", "AED لا يقدم إلا a cause of death بين معقوفين وبعلامة سؤال؛ لا علة وفاة معينة محكومة تقارن بباق أو برق.", zero=FEM_T),
    gap("aed-v1.0:77540", "متم", "OPEN-CANDIDATE", "to discuss أو talk back and forth لا يطابق متم في العربية الممسوحة، ولا يدخل كلام أو جدل من خارج الرسم."),
    gap("aed-v1.0:78030", "مدو", "OPEN-CANDIDATE", "word أو speech أو matter لا يطابق مدو في العربية الممسوحة، ولا يدخل قول أو أمر من خارج الجذر.", zero=FEM_T),
    terminal("aed-v1.0:79060", "∅", "COMPOUND-BOUNDARY", "الرسم `n-jb-n` تركيب جرّي ذو حدود ظاهرة لمعنى for the sake of؛ لا يحمل مجموع الأداة على جذر عربي مفرد."),
    gap("aed-v1.0:80170", "نين", "OPEN-CANDIDATE", "turn away أو move أو tremble لا يطابق نين في العربية الممسوحة، ولا يدخل حركة أو ارتجاف من خارج الرسم."),
    terminal("aed-v1.0:80300", "∅", "OUT-OF-SCOPE", "Punisher اسم تشخيصي مخصوص لسكين؛ لقب الأداة الثقافي لا يصدر جذرا عربيا من العقاب أو القطع."),
    gap("aed-v1.0:80450", "نعي", "OPEN-CANDIDATE", "mooring post لا يطابق نعي في خبر الموت والبكاء، ولا يدخل وتد أو مرسى من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:80700", "نعج", "SOURCE-GAP", "particles في الطب عام، والألمانية تقترح flour أو شيئا شبيها؛ لا مادة دقيقة محكومة تقارن بنعج أو نعق.", zero=NOM_W),
    gap("aed-v1.0:81570", "نود", "OPEN-CANDIDATE", "swaddling clothes لا يطابق نود أو نوض في العربية الممسوحة، ولا يدخل قماط أو لفافة من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:83170", "نفر", "OPEN-CANDIDATE", "flight of stairs أو stair step لا يطابق نفر في التفرق والنفور والجماعة، ولا يدخل درج من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:83530", "نفر", "OPEN-CANDIDATE", "best quality relating to cloth لا يطابق نفر في التفرق والجماعة، ولا يدخل جودة أو كتان من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:84450", "نمس", "SOURCE-GAP", "AED لا يسمي إلا a jug بين معقوفين بلا مادة أو سعة؛ لا إناء معين محكوم يقارن بنمس أو نمش.", zero=FEM_T),
    gap("aed-v1.0:84880", "نني", "OPEN-CANDIDATE", "stride أو step لا يطابق نني في العربية الممسوحة، ولا يدخل خطو أو مشي من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:84940", "نني", "OPEN-CANDIDATE", "bed لا يطابق نني في العربية الممسوحة، ولا يدخل فراش أو مضجع من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:85170", "نرو", "OPEN-CANDIDATE", "fear أو terror لا يطابق نرو أو نلو في العربية الممسوحة، ولا يدخل خوف أو رعب من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:85570", "نحب", "OPEN-CANDIDATE", "early morning لا يطابق نحب في النذر والبكاء والجد في السير، ولا يدخل صبح أو بكرة من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:86000", "نحا", "SOURCE-GAP", "AED يجمع trachoma مع a sadness، والألمانية لا تثبت إلا مرض عين بين معقوفين؛ لا حس واحد محكوم يقارن بنحا أو نحر.", zero=FEM_T),
    gap("aed-v1.0:86230", "نحب", "OPEN-CANDIDATE", "lotus blossom أو bud لا يطابق نحب في النذر والنحيب، ولا يدخل لوتس أو زهرة من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:86480", "نحن", "OPEN-CANDIDATE", "to rejoice لا يطابق نحن في العربية الممسوحة، ولا يدخل فرح أو طرب من خارج الرسم."),
    gap("aed-v1.0:86540", "نحر", "OPEN-CANDIDATE", "compulsory labor لا يطابق نحر في موضع الصدر والذبح، ولا يدخل سخرة أو عمل من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:87000", "نخوت", "OPEN-CANDIDATE", "lamentation أو complaint لا يطابق نخوت أو نخ في العربية الممسوحة، ولا يدخل شكوى أو رثاء من خارج الجذر."),
    gap("aed-v1.0:87090", "نخب", "OPEN-CANDIDATE", "to dance لا يطابق نخب في الاختيار والنخبة، ولا يدخل رقص من خارج الجذر."),
    gap("aed-v1.0:87280", "نخن", "OPEN-CANDIDATE", "little girl لا يطابق نخن إلا اسم موضع منقول في العربية الممسوحة، ولا يدخل بنت أو صبية من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:87340", "نخن", "SOURCE-GAP", "AED لا يسمي إلا a bread offering بين معقوفين، والألمانية لا تزيد إلا Breads؛ لا نوع قربان أو خبز معين يقارن بنخن.", zero=NOM_W),
    gap("aed-v1.0:87630", "نخت", "OPEN-CANDIDATE", "stronghold أو fortification لا يطابق نخت في النقر أو استقصاء القول، ولا يدخل حصن أو قلعة من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:88180", "نزف", "OPEN-CANDIDATE", "wounds لا يساوي نزف الماء أو الدم؛ النزف أثر محتمل للجرح لا اسم الجرح نفسه، فلا تحمل النتيجة على العضو بالقوة.", sound="n↔ن في IDN-03 وz↔ز وp↔ف عبر LAB-01 بعد عزل واو الجمع؛ بقيت الدلالة هي العائق.", orbit="النزف ذهاب الدم أو الماء، والجراح قد تحدثه؛ ثبتت مجاورة السبب والنتيجة لا اتحاد wounds بالنزف.", keywords="نزف الدم|ذهب دمه|نزف البئر|نزح", zero=NOM_W),
    gap("aed-v1.0:88700", "نسم", "OPEN-CANDIDATE", "green felspar لا يطابق نسم في النسيم والنفس ولا نشم في الشجر والرائحة، ولا يدخل معدن أو حجر من خارج الجذر.", zero=FEM_T),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT
assert {item.state for item in DECISIONS} <= LEGAL_CLOSURES
assert {item.verdict for item in DECISIONS} <= LEGAL_CLOSURES


WITNESS_NOTES = {
    "aed-v1.0:69330": "أثبت الصحاح والمحكم أن الموت ضد الحياة وأن الميت من فارقها؛ ثبت مدار dead person كاملا بعد عزل تاء التأنيث.",
    "aed-v1.0:76290": "أثبتت مادة شرب أن المشرب موضع الشرب؛ ثبت مدار watering place، وبقيت جهة القرض وصف ꜣ↔ر بلا حسم.",
    "aed-v1.0:88180": "أثبتت المعاجم نزف الدم وذهاب ماء البئر؛ ثبتت مجاورة النزف للجراح لا مساواة wound بالنزف.",
}


def round40_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R39.round39_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND39-COMPLETION", "ROUND40-COMPLETION")
    card = card.replace(
        f"round39-egyptian-rank={rank}/{CARD_COUNT}",
        f"round40-egyptian-rank={rank}/{CARD_COUNT}",
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
        raise SystemExit("Round-forty marker already exists; append refused.")

    aramaic_exact, _ = R9.load_entries("aramaic")
    aramaic_queue = R9.select_aramaic(aramaic_text, aramaic_exact)
    assert not aramaic_queue, (
        "Aramaic short live-open queue is no longer exhausted: "
        f"{[item['entry_id'] for item in aramaic_queue[:10]]}"
    )

    egyptian_exact, _ = R9.load_entries("egyptian")
    queue = R39.R38.R37.R36.R35.R34.R33.R32.R31.R30.R29.select_egyptian_fast(
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
        round40_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الأربعون: استمرار المخزون المصري المسجل المفتوح (2026-08-27)", "",
        (
            "أعيد فحص الآرامية أولا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرا، فسجل الانتقال المسمى `{TRANSITION}`. انتقيت ثمانين "
            "بطاقة مصرية بدءا من `WO-C-OPEN-COMP-02463` بقصر الهيكل ثم موضع "
            "اللقطة. استبعد صف ḏ المؤجل. في كل بطاقة عرضت إصابات AED كلها بلا "
            "حد، وكتب وسم الطريق والرسم والمدخل المختار، وحفظ الاختلاف "
            "والمتجانسات بلا محو. فحصت حالة الإغلاق والحكم آليا على القائمة "
            "القانونية وحدها في `data/closure-vocabulary.json`."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-02463 إلى WO-C-OPEN-COMP-02502", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-02503 إلى WO-C-OPEN-COMP-02542", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([
                f"<!-- LANE-C-R40-EGYPTIAN-CHUNK-{rank:03d}:END -->", "",
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
        "## الجولة الأربعون: المسار C، الساميات والمصرية (2026-08-27)", "",
        f"- الوقت: {now}.",
        "- أعيد فحص الساميات أولا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-02463` إلى `WO-C-OPEN-COMP-02502`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-02503` إلى `WO-C-OPEN-COMP-02542`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طبق الانضباط الثلاثي: كل موجب له صوت موقع وحدث مجمد ومدار مكتوب؛ وكل بطاقة أخرى لها عائق شريف مسمى.",
        "- قاموس الإغلاق المغلق وحده مطبق: كل حالات الإغلاق والأحكام اجتازت القائمة القانونية في `data/closure-vocabulary.json`.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ الموجب مقصور على العضو ومداره المكتوب.",
        "- الموجب: `mwt.t↔موت` في الميت ومفارقة الحياة بعد عزل تاء التأنيث؛ حكمه `ROOT-TRACE` مقصور على العضو.",
        "- بقي `mšꜣb↔مشرب` في موضع الشرب `DIRECTION-GAP`: الدلالة مباشرة، لكن وسم القرض السامي لا يسمي مانحا أو طريقا، وصف ꜣ↔ر غير موقع.",
        "- بقي `nzp.w↔نزف` مفتوحا: نزف الدم نتيجة محتملة للجراح لا اسم الجرح نفسه؛ لم تورث النتيجة حكم السبب.",
        "- المراجع النباتية والطبية والأدوات الموسومة بين معقوفين أو بعلامة سؤال بقيت `SOURCE-GAP`؛ لم يحسم التخمين نوع الشيء بالقوة.",
        "- القروض السامية العامة الستة بقيت `DIRECTION-GAP` لغياب المانح الفردي أو طريق النقل المكتمل.",
        "- الأدوات النحوية والصفات الإحالية واللقب الثقافي أغلقت `OUT-OF-SCOPE`، والمركبان `pr-ꜥꜣ` و`n-jb-n` أغلِقا `COMPOUND-BOUNDARY`، وصف ḏ المصري المؤجل بقي مستبعدا.",
        "- لم يحدث شحن أو إيداع أو إعداد مرحلي، ولم يستعمل git أو تحدث مشتقات النشر.", "",
        f"LANE-C DONE40 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
            R39.R38.R37.R36.R35.R34.R33.R32.R31.R30.R29.R28.R27.R26.R25.R24.R23.R20.R10.append
        )
        append(EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian)
        append(REPORT, f"{MARKER}:REPORT", report)
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
