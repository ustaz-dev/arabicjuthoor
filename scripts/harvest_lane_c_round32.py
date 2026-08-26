#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 32 completion cards without shipping or git.

The live short Aramaic queue is checked before the registered Egyptian open
queue continues. The script completes WO-C-OPEN-COMP-01823..01902 in two
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

import harvest_lane_c_round31 as R31


R9 = R31.R9
AR = R31.AR
ROOT = R31.ROOT
ARAMAIC = R31.ARAMAIC
EGYPTIAN = R31.EGYPTIAN
REPORT = R31.REPORT

MARKER = "LANE-C-ROUND32-2026-08-26"
FIRST_SERIAL = 1823
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)
LEGAL_CLOSURES = R31.LEGAL_CLOSURES


def gap(member_id: str, candidate: str, state: str, reason: str,
        sound: str = "المروحة بنيوية فقط؛ لا يرقى التشابه إلى قانون أو نسب.",
        orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
        keywords: str = "", zero: str = "") -> R9.Decision:
    return R31.gap(
        member_id, candidate, state, reason, sound, orbit, keywords, zero,
    )


def pos(member_id: str, candidate: str, verdict: str, keywords: str,
        sound: str, orbit: str, reason: str,
        zero: str = "") -> R9.Decision:
    return R31.R30.R29.R28.pos(
        member_id, candidate, verdict, keywords, sound, orbit, reason, zero,
    )


def terminal(member_id: str, candidate: str, verdict: str, reason: str,
             zero: str = "") -> R9.Decision:
    return R31.R30.terminal(member_id, candidate, verdict, reason, zero)


# Two members have a complete signed sound route, a frozen event, two old
# Arabic witnesses, and a bounded semantic orbit. Direct semantic contacts
# with an incomplete Egyptian sound route remain named gaps; uncertain and
# unnamed AED referents remain source gaps; compounds and function words are
# isolated structurally.
DECISIONS: tuple[R9.Decision, ...] = (
    gap("aed-v1.0:179120", "دبخ", "SOURCE-GAP", "execution block موسومة بالشك، ولا يحسم AED بين عمود الإعدام وكتلته؛ لا أداة واحدة يقام عليها مدار عربي."),
    gap("aed-v1.0:179330", "ضم", "OPEN-CANDIDATE", "town/quarter/wharf لا يساوي الضم والجمع معجميا؛ كون المدينة تجمع الناس جسر تصوري لا اسم موضع في مادة ضم."),
    gap("aed-v1.0:180250", "درف", "OPEN-CANDIDATE", "writing/script/document لا يطابق درف أو دلف ولا نظائر الضاد، ولا يدخل كتب أو خط من خارج الرسم."),
    gap("aed-v1.0:180720", "دشر", "SOURCE-GAP", "نوع الشجرة وخشبها غير مسمى وكل التعريف بين أقواس؛ لا ينتخب اسم نبات عربي من دشر أو دسر."),
    gap("aed-v1.0:180760", "دشر", "OPEN-CANDIDATE", "impurity/dirt لا يطابق دشر أو دسر في العربية الممسوحة، ولا يدخل وسخ أو دنس من خارج الرسم."),
    gap("aed-v1.0:180930", "دقع", "SOURCE-GAP", "فعل shape نفسه موسوم بالشك ومقيد بالمجداف؛ لا حدث واحدا محسوما يقارن بدقع أو دقغ."),
    gap("aed-v1.0:400031", "نخت", "OPEN-CANDIDATE", "strong/victorious لا يطابق نخت في النقر والنتف واستقصاء القول، ولا يدخل قوي أو نصر من خارج الرسم."),
    gap("aed-v1.0:400111", "منخ", "OPEN-CANDIDATE", "thoroughly/excellently لا يطابق منخ في العربية الممسوحة، ولا يكفي كونه ظرف كيفية لإثبات مادة."),
    gap("aed-v1.0:400458", "نفر", "OPEN-CANDIDATE", "well/happily لا يطابق نفر في الخروج والجماعة والنفور، ولا يدخل حسن أو فرح من خارج الرسم."),
    gap("aed-v1.0:400805", "زبت", "OPEN-CANDIDATE", "expedition لا يطابق زبت أو سبت ولا صور النواة، ولا يدخل سفر أو غزو من خارج الرسم."),
    gap("aed-v1.0:400947", "نمت", "SOURCE-GAP", "الإنجليزية لا تعطي إلا noun والألمانية تجعل المرجع occupied مع علامة شك؛ لا معنى معجميا محسوما للمقارنة."),
    gap("aed-v1.0:401138", "خبب", "OPEN-CANDIDATE", "الخبب ضرب من عدو الدابة لا dance؛ اشتراكهما في حركة موزونة لا يثبت مدارا معجميا واحدا.", sound="ḫ↔خ في IDN-17 وb↔ب في IDN-05 مع التضعيف؛ بقيت الدلالة هي العائق.", orbit="العدو الراكض والرقص حركتان إيقاعيتان، لكن العربية تسمي مشية الدابة ولا تسمي الرقص."),
    terminal("aed-v1.0:450161", "∅", "OUT-OF-SCOPE", "very ظرف تقوية وظيفي لا مادة معجمية مستقلة قابلة لحكم النسب."),
    gap("aed-v1.0:450167", "شوت", "OPEN-CANDIDATE", "emptiness لا يطابق شوت أو شوط ولا نوى شو وسو، ولا يدخل خلو أو فراغ من خارج الرسم."),
    gap("aed-v1.0:450201", "توت", "SOURCE-GAP", "نوع الخبز غير مسمى وكل التعريف بين أقواس؛ لا ينتخب اسم طعام عربي من توت أو طوط."),
    gap("aed-v1.0:450451", "زمن", "OPEN-CANDIDATE", "check the quality of bread لا يطابق زمن أو سمن؛ ولا يحول قياس الجودة إلى مادة الزمن أو السمن."),
    gap("aed-v1.0:450471", "نوت", "OPEN-CANDIDATE", "quarry/product of the desert في معنى صيد البر لا يطابق نوت أو نوط ولا نوى نو، ولا يدخل طريدة من خارج الرسم."),
    gap("aed-v1.0:450571", "سخت", "OPEN-CANDIDATE", "bird trap/net/noose لا يجد في سخت أو سخط أو شخت أو صخت اسما للمصيدة أو الشبكة عاملا."),
    gap("aed-v1.0:500233", "وسو", "OPEN-CANDIDATE", "sawer لا يطابق وسو أو وشو أو وصو ولا النوى الأقصر، ولا يدخل ناشر أو نجار من خارج الرسم."),
    gap("aed-v1.0:500315", "بوء", "OPEN-CANDIDATE", "loftiness لا يطابق بوء أو بوا أو بول أو بور، ولا يدخل علو ورفعة من خارج الرسم."),
    gap("aed-v1.0:550085", "هاب", "OPEN-CANDIDATE", "letter/communication لا يطابق هاب أو هلب أو حرب ولا نظائر الحاء، ولا يدخل كتاب أو رسالة من خارج الرسم."),
    terminal("aed-v1.0:550100", "∅", "OUT-OF-SCOPE", "in front of/in the direction of حرف جر مركب وظيفي بلا مادة معجمية مستقلة قابلة لحكم النسب."),
    gap("aed-v1.0:550245", "ثنر", "OPEN-CANDIDATE", "strong/energetic/effective لا يطابق ثنر أو تنر أو طنر ولا صور اللام، ولا يدخل قوة أو نشاط من خارج الرسم."),
    gap("aed-v1.0:600033", "تور", "SOURCE-GAP", "نوع الخبز غير مسمى وكل التعريف بين أقواس؛ لا ينتخب اسم خبز عربي من تور أو طور أو طول."),
    gap("aed-v1.0:600161", "خعر", "OPEN-CANDIDATE", "thong/leather strip لا يطابق خعر أو خضر أو خغر ولا صور اللام، ولا يدخل سير أو رباط من خارج الرسم."),
    gap("aed-v1.0:600265", "نرح", "DIRECTION-GAP", "وسم Sem. loan word في revile/abuse لا يسمي مانحا ساميا فرديا أو طريق انتقال، ولا تنتخب المروحة مادة عربية للسباب."),
    gap("aed-v1.0:600375", "زخر", "OPEN-CANDIDATE", "write/paint/work as a scribe لا يطابق زخر أو زحر أو سخر أو سحر في العربية الممسوحة، ولا يدخل كتب أو رسم من خارج الهيكل."),
    gap("aed-v1.0:600478", "حصر", "LAW-GAP", "الحصير سفيفة من بردي فيطابق basketwork، لكن t المصرية بإزاء ص العربية بلا صف مصري موقع.", sound="ḥ↔ح في IDN-14 وr↔ر في IDN-01؛ t↔ص هي الرجل المصرية غير الموقعة.", orbit="الحصير سفيفة من البردي ونحوه، وهو عمل منسوج يطابق basketwork مباشرة، وبقي الصوت الأوسط مانعا.", keywords="الحصير|سفيفة|بردي|البارية"),
    gap("aed-v1.0:600578", "عبر", "SOURCE-GAP", "نوع المخبوز نفسه غير مسمى وموسوم بالشك؛ لا ينتخب اسم خبز عربي من عبر أو عبل أو غبر."),
    gap("aed-v1.0:600641", "عمر", "SOURCE-GAP", "steer موسومة بالشك في الإنجليزية وإن سمت الألمانية ثورا؛ لا مرجع حيواني واحد محسوما يقارن بعمر أو غمر."),
    gap("aed-v1.0:800009", "رتح", "OPEN-CANDIDATE", "bake لا يطابق رتح أو رطح أو لتح أو لطخ في العربية الممسوحة، ولا يدخل خبز أو شوي من خارج الرسم."),
    gap("aed-v1.0:850254", "كاي", "OPEN-CANDIDATE", "belonging to the ka نسبة لاصطلاح ديني مصري مخصوص، ولا يطابق كاي أو كري أو كل ولا بقية المروحة دلالة معجمية عربية."),
    gap("aed-v1.0:850441", "باو", "SOURCE-GAP", "الأداة الخشبية غير مسماة، والألمانية تقترح مدقة أو خاتما؛ لا أداة واحدة محكومة يقوم عليها المدار."),
    gap("aed-v1.0:850449", "بوخ", "OPEN-CANDIDATE", "باخ الحر والنار أي سكن وفتر، لكنه لا يثبت sink بمعنى الغوص والهبوط في الماء أو الأرض.", sound="b↔ب في IDN-05؛ ꜣ↔و وẖ↔خ بلا صفين مصريين موقعين لهذا العضو.", orbit="البوخ خمود وسكون بعد شدة، وهو تماس عام مع subside لا مساواة مع فعل sink المكاني.", keywords="باخ|سكن|فتر|أخمد"),
    gap("aed-v1.0:850590", "زشي", "OPEN-CANDIDATE", "tear out/pull out لا يطابق زشي أو زسي ولا نظائر السين، ولا يدخل نزع أو نتف من خارج الرسم."),
    gap("aed-v1.0:850681", "كيت", "SOURCE-GAP", "شيء مصنوع من الفاكهة غير مسمى وكل التعريف بين أقواس؛ لا مادة أو طعام واحدا للمقارنة."),
    gap("aed-v1.0:850780", "سدد", "MORPHOLOGY-GAP", "السداد هو الصواب والقصد في القول والعمل فيطابق prudence/wisdom، لكن عزل .t يترك s-ꜣ بإزاء س-d-d ولا يفسر الدالين.", sound="s↔س في IDN-07؛ ꜣ المصرية لا تحمل دالي سدد، والتضعيف العربي بلا مقابل.", orbit="السداد الاستقامة والصواب والقصد، وهو مدار الحكمة وحسن التدبير مباشرة، وبقيت البنية الصامتية مانعة.", keywords="السداد|الصواب|القصد|الاستقامة", zero="عزلت .t علامة التأنيث الاسمية المسجلة؛ بقي s-ꜣ بإزاء س-d-d من غير تعرية تفسر الدالين."),
    gap("aed-v1.0:853138", "حنو", "OPEN-CANDIDATE", "military commander لا يطابق حنو أو حنن ولا نوى حن، ولا يدخل قائد أو أمير من خارج الرسم."),
    pos("aed-v1.0:853589", "حسر", "ROOT-ECHO", "محسرون|مقصون|محسورا|لا شيء عنده", "ḥ↔ح في IDN-14، وs↔س في IDN-07، وr↔ر في IDN-01؛ جذر كامل.", "المحسرون هم المقصون، والمحسور من أنفق حتى لم يبق عنده شيء؛ وهو مدار deprived في الإقصاء والاستلاب.", "ECHO مقصور على الإقصاء والحرمان في العضو المختار؛ لا مساواة كل حسر بالحرمان."),
    gap("aed-v1.0:853890", "شزب", "OPEN-CANDIDATE", "receipt/commencement لا يطابق شزب أو شسب ولا نظائر السين والفاء، ولا يدمج الاستلام والابتداء في مادة عربية واحدة."),
    gap("aed-v1.0:856104", "ثاز", "OPEN-CANDIDATE", "knot لا يطابق ثاز أو ثاس أو تلس أو طرس ولا بقية المروحة، ولا يدخل عقد أو ربطة من خارج الرسم."),
    gap("aed-v1.0:856566", "قنت", "SOURCE-GAP", "النبات الطبي غير مسمى وكل التعريف بين أقواس؛ لا ينتخب اسم نبات عربي من قنت أو قنو أو قنا."),
    gap("aed-v1.0:856997", "عسر", "OPEN-CANDIDATE", "obnoxious بمعنى بغيض لا يساوي عسر بمعنى صعب وضد اليسر؛ صعوبة المعاملة أثر لا مدار معجميا واحدا."),
    gap("aed-v1.0:857536", "فصص", "LAW-GAP", "فصصت الشيء فصلته وانتزعته وأفص إليه من حقه شيئا يلتقي share/portion، لكن s-š المصرية بإزاء ص-ص بلا صفين مصريين موقعين.", sound="p↔ف يمر بالصف الشفوي؛ s↔ص وš↔ص هما الرجلان المصريتان غير الموقعتين.", orbit="الفص جزء مفصول، وأفص إليه من حقه شيئا أي أخرجه له؛ وهو مدار الحصة المفصولة، وبقي الصوت مانعا.", keywords="فصلته|انتزعته|من حقه|جزء"),
    gap("aed-v1.0:857753", "شدو", "OPEN-CANDIDATE", "artificial lake/well لا يطابق شدو أو سدو ولا نوى شد وسد؛ ولا تسوى السدود بالماء المحجوز أو البئر."),
    gap("aed-v1.0:857822", "شني", "SOURCE-GAP", "الإنجليزية تعطي conjuration والألمانية Streit؛ اختلاف التعويذة والنزاع يمنع مدارا واحدا محسوما للمقارنة."),
    gap("aed-v1.0:858449", "بزق", "LAW-GAP", "بزق بمعنى بصق يطابق spit مباشرة، لكن ꜥ-g المصرية بإزاء ز-ق العربية بلا صفين مصريين موقعين.", sound="p↔ب في LAB-01؛ ꜥ↔ز وg↔ق هما الرجلان المصريتان غير الموقعتين.", orbit="البزق والبصق رمي البزاق من الفم؛ وهو معنى spit نفسه، وبقي معظم المسار المصري مانعا.", keywords="البزاق|البصاق|بزق|بصق"),
    pos("aed-v1.0:859155", "خرر", "ROOT-ECHO", "خر الماء|جرى|جريانه|عين خرارة", "ḫ↔خ في IDN-17، وr↔ر في IDN-01 في الموضعين الثاني والثالث؛ جذر كامل.", "خر الماء إذا اشتد جريه، والعين الخرارة كثيرة الجريان؛ وهو مدار watercourse/channel بوصفه مجرى الماء الجاري.", "ECHO لمجرى الماء الجاري خاصة؛ لا مساواة كل قناة مصنوعة بصوت الخرير أو السقوط."),
    gap("aed-v1.0:859386", "حبن", "OPEN-CANDIDATE", "triumph لا يطابق حبن في العربية الممسوحة، ولا يدخل نصر أو ظفر من خارج الرسم."),
    gap("aed-v1.0:859730", "سون", "OPEN-CANDIDATE", "flattery لا يطابق سون أو شون أو صون، ولا يدخل مدح أو تملق من خارج الرسم."),
    gap("aed-v1.0:859866", "شفي", "OPEN-CANDIDATE", "respect لا يطابق شفي أو سفي ولا صور الهمزة، ولا يدخل وقر أو احترم من خارج الرسم."),
    gap("aed-v1.0:861067", "كري", "SOURCE-GAP", "associate with نفسها موسومة بالشك في اللغتين؛ لا حدث اجتماعي محسوما يقارن بكري أو كلي."),
    gap("aed-v1.0:861388", "كل", "LAW-GAP", "كل بمعنى الجميع والتمام يطابق entire، لكن r-ꜣ-w المصرية لا تحمل كاف كل ولامها في مسار مصري موقع.", sound="لا رجل صوتية مصرية موقعة تجمع r-ꜣ-w بإزاء ك-l؛ المطابقة دلالية محضة.", orbit="كل الشيء جميعه وتمامه، وهو معنى entire مباشرة، وبقي الصوت كله مانعا.", keywords="الجميع|جميعه|التمام|كل شيء"),
    gap("aed-v1.0:863402", "بقن", "SOURCE-GAP", "Beqen اسم شعب أجنبي بلا تحليل داخلي أو معنى معجمي؛ لا ينتخب جذر بقن من التشابه الاسمي وحده."),
    gap("aed-v1.0:863681", "جتت", "OPEN-CANDIDATE", "watering place/cistern لا يطابق جتت أو قطط أو غتت ولا النوى المختصرة، ولا يدخل بئر أو صهريج من خارج الرسم."),
    gap("aed-v1.0:865322", "ينق", "SOURCE-GAP", "AED يجمع onyx والرصاص والقصدير في عضو واحد؛ اختلاف الحجر والمعدنين يمنع مادة واحدة يقوم عليها المدار."),
    gap("aed-v1.0:865385", "هدن", "OPEN-CANDIDATE", "broom لا يطابق هدن أو هضن أو حدن أو حضن، ولا يدخل مكنسة من خارج الرسم."),
    gap("aed-v1.0:139", "ءمع", "OPEN-CANDIDATE", "ramus of the lower jaw/forked bone لا يطابق ءمع أو لمع أو رمع ولا نظائر الضاد والغين، ولا يدخل فرع أو فك من خارج الرسم."),
    gap("aed-v1.0:20530", "يابي", "OPEN-CANDIDATE", "left side/left arm لا يطابق يابي أو يلبي أو يربي ولا نظائر الهمزة، ولا يدخل يسار أو شمال من خارج الرسم."),
    gap("aed-v1.0:20560", "يابت", "OPEN-CANDIDATE", "left eye لا يطابق يابت أو يلبت أو يربت ولا نظائر الهمزة، ولا يدخل عين أو يسار من خارج الرسم."),
    gap("aed-v1.0:20750", "يارر", "OPEN-CANDIDATE", "dim of eye/weak of heart لا يطابق يارر أو يرر ولا نظائر الهمزة واللام، ولا يدمج ضعف القلب وكلال البصر في مادة عربية واحدة."),
    gap("aed-v1.0:20780", "يارت", "SOURCE-GAP", "غطاء الرأس نفسه مشكوك، واقتراح ضفيرة الشعر بين أقواس؛ لا شيء واحدا محسوما للمقارنة."),
    terminal("aed-v1.0:21500", "∅", "COMPOUND-BOUNDARY", "Washing-the-face اسم طقس مركب؛ لا يحمل المركب كله على جذر عربي واحد من مروحته."),
    terminal("aed-v1.0:21640", "∅", "COMPOUND-BOUNDARY", "breakfast محلل في AED إلى washing the mouth؛ حد المركب يفصل العبارة الطقسية عن جذر عربي مفرد."),
    gap("aed-v1.0:21700", "يعبو", "SOURCE-GAP", "علامة الحداد نفسها مشكوكة واقتراح الشعر المنفلت غير المحكم بين أقواس؛ لا إيماءة واحدة مسماة للمقارنة."),
    gap("aed-v1.0:22220", "يوات", "OPEN-CANDIDATE", "رغيف الخبز المشكل كرأس بقرة لا يطابق يوات أو يولت ولا نظائر الهمزة، ولا يكفي شكل الرغيف لإثبات مادة."),
    gap("aed-v1.0:22470", "عوض", "LAW-GAP", "العوض بدل وتعويض فيطابق reward، لكن j-w-ꜥ-w المصرية بإزاء ع-w-ḍ لا يقدم مسارا صوتيا كاملا، والعضو المصري يسمي سوارا بعينه.", sound="w↔و في IDN-10؛ j الابتدائية وꜥ-w النهائيتان لا تنتظمن بإزاء ع-ض في صفوف مصرية موقعة.", orbit="العوض ما يعطى بدلا وجزاء، وهو مدار reward؛ أما المصرية فتخصصه في سوار مكافأة، وبقي الصوت والتخصيص مانعين.", keywords="العوض|البدل|التعويض|الجزاء"),
    gap("aed-v1.0:22760", "يوني", "SOURCE-GAP", "body of water غير مسمى وكل التعريف بين أقواس؛ لا بحيرة أو قناة معينة يقوم عليها مدار عربي."),
    terminal("aed-v1.0:23460", "∅", "COMPOUND-BOUNDARY", "double-heart amulet مركب مثنى ثقافي؛ لا يرد مجموع القلبين والتميمة إلى جذر عربي مفرد."),
    terminal("aed-v1.0:23650", "∅", "COMPOUND-BOUNDARY", "heart-heart تركيب مكرر صار اسم دلال؛ لا يحمل المركب كله على جذر عربي واحد من المروحة."),
    gap("aed-v1.0:25540", "يمير", "OPEN-CANDIDATE", "tongue لا يطابق يمير أو يميل ولا نظائر الهمزة، ولا يدخل لسان من خارج الرسم."),
    gap("aed-v1.0:26910", "يني", "SOURCE-GAP", "Inyt اسم جسم مائي بلا تعيين نوعه أو وصفه؛ لا يستخرج جذر عربي من الاسم وحده."),
    gap("aed-v1.0:27820", "ينست", "OPEN-CANDIDATE", "lower leg/calf/shin لا يطابق ينست أو ينشت أو ينصت ولا نظائر الهمزة، ولا يدخل ساق أو قصبة من خارج الرسم."),
    gap("aed-v1.0:27980", "ينتي", "OPEN-CANDIDATE", "drive back/withdraw لا يطابق ينتي أو ينطي ولا نظائر الهمزة، ولا يدخل رد أو نكص من خارج الرسم."),
    gap("aed-v1.0:31670", "يسحم", "SOURCE-GAP", "body of water موسومة بالشك وغير معينة؛ لا ينتخب اسم مجرى أو بحيرة عربية من يسحم أو يصحم."),
    gap("aed-v1.0:33690", "يثنت", "SOURCE-GAP", "chest/box نفسها بين أقواس وغير محسومة؛ لا وعاء واحدا مسمى يقارن بيثنت أو يتنت."),
    gap("aed-v1.0:34010", "جنب", "LAW-GAP", "الجانب والجنبة ناحية كل شيء فيلتقيان edge of a wound or mouth، لكن d المصرية بإزاء ن العربية بلا صف مصري موقع، و.w السطحية باقية.", sound="j↔ج في IDN-08 وb↔ب في IDN-05؛ d↔ن هي الرجل المصرية غير الموقعة، و.w لا تحمل صامتا عربيا.", orbit="الجانب والجنبة هما الناحية والشق من الشيء؛ وهو مدار edge مباشرة، وبقي الصوت والصرف مانعين.", keywords="الجانب|الجنبة|الناحية|شق"),
    terminal("aed-v1.0:36830", "∅", "COMPOUND-BOUNDARY", "breakfast محلل صراحة إلى purification of the mouth؛ حد المركب يمنع حمل العبارة على جذر عربي مفرد."),
    gap("aed-v1.0:37290", "عفات", "SOURCE-GAP", "ripped out flesh موسومة بالشك، والألمانية توسعها إلى جزء جسدي؛ لا مرجع تشريحي واحدا محسوما للمقارنة."),
    gap("aed-v1.0:37610", "عمات", "SOURCE-GAP", "جزء جسد أوزير غير مسمى وكل التعريف بين أقواس؛ لا عضو تشريحي معين يقوم عليه مدار عربي."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT
assert {item.state for item in DECISIONS} <= LEGAL_CLOSURES
assert {item.verdict for item in DECISIONS} <= LEGAL_CLOSURES

OUTSIDE_FAN = {
    "aed-v1.0:600478", "aed-v1.0:850449", "aed-v1.0:850780",
    "aed-v1.0:858449", "aed-v1.0:22470", "aed-v1.0:34010",
}

WITNESS_NOTES = {
    "aed-v1.0:401138": "أثبتت المعاجم الخبب ضربا من عدو الدابة؛ ثبتت الحركة الموزونة، لكنها لم تسم الرقص.",
    "aed-v1.0:600478": "قال كتاب العين إن الحصير سفيفة من بردي ونحوه؛ ثبت عمل السفيف، وبقي t↔ص بلا صف مصري موقع.",
    "aed-v1.0:850449": "أثبتت المعاجم باخ الحر والنار بمعنى سكن وفتر؛ ثبت تماس subside العام، لا sink المكاني، وبقي الصوت ناقصا.",
    "aed-v1.0:850780": "أثبتت المعاجم السداد في الصواب والقصد والاستقامة؛ ثبت مدار prudence، وبقيت دالا سدد بلا حامل بعد عزل .t.",
    "aed-v1.0:853589": "أثبتت المعاجم المحسرين بمعنى المقصين والمحسور الذي لم يبق عنده شيء؛ ثبت مدار deprived بشاهدين مستقلين.",
    "aed-v1.0:857536": "أثبتت المعاجم فص الشيء في فصله وانتزاعه، وإفصاص جزء من الحق؛ ثبتت الحصة المفصولة، وبقي الصوت المصري ناقصا.",
    "aed-v1.0:858449": "أثبتت المعاجم أن البزق لغة في البصق؛ ثبت معنى spit نفسه، وبقي ꜥ-g↔ز-ق بلا صفين مصريين.",
    "aed-v1.0:859155": "أثبتت المعاجم خر الماء إذا اشتد جريه والعين الخرارة الكثيرة الجريان؛ ثبت مدار مجرى الماء بشاهدين مستقلين.",
    "aed-v1.0:861388": "أثبتت المعاجم كل الشيء بمعنى جميعه وتمامه؛ ثبت معنى entire، وبقي المسار الصوتي المصري كله مفتوحا.",
    "aed-v1.0:22470": "أثبتت المعاجم العوض في البدل والتعويض؛ ثبت تماس reward، وبقي تخصيص السوار والمسار الصوتي مانعين.",
    "aed-v1.0:34010": "أثبتت المعاجم الجانب والجنبة في الناحية والشق من الشيء؛ ثبت معنى edge، وبقي d↔ن و.w بلا حمل كامل.",
}


def round32_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R31.round31_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND31-COMPLETION", "ROUND32-COMPLETION")
    card = card.replace(
        f"round31-egyptian-rank={rank}/{CARD_COUNT}",
        f"round32-egyptian-rank={rank}/{CARD_COUNT}",
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
        raise SystemExit("Round-thirty-two marker already exists; append refused.")

    aramaic_exact, _ = R9.load_entries("aramaic")
    aramaic_queue = R9.select_aramaic(aramaic_text, aramaic_exact)
    assert not aramaic_queue, (
        "Aramaic short live-open queue is no longer exhausted: "
        f"{[item['entry_id'] for item in aramaic_queue[:10]]}"
    )

    egyptian_exact, _ = R9.load_entries("egyptian")
    queue = R31.R30.R29.select_egyptian_fast(egyptian_text, egyptian_exact)
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
        round32_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الثانية والثلاثون: استمرار المخزون المصري المسجل المفتوح (2026-08-26)", "",
        (
            "أعيد فحص الآرامية أولا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرا، فسجل الانتقال المسمى `{TRANSITION}`. انتقيت ثمانين "
            "بطاقة مصرية بدءا من `WO-C-OPEN-COMP-01823` بقصر الهيكل ثم موضع "
            "اللقطة. استبعد صف ḏ المؤجل. في كل بطاقة عرضت إصابات AED كلها بلا "
            "حد، وكتب وسم الطريق والرسم والمدخل المختار، وحفظ الاختلاف "
            "والمتجانسات بلا محو. فحصت حالة الإغلاق والحكم آليا على القائمة "
            "القانونية وحدها في `data/closure-vocabulary.json`."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-01823 إلى WO-C-OPEN-COMP-01862", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-01863 إلى WO-C-OPEN-COMP-01902", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([
                f"<!-- LANE-C-R32-EGYPTIAN-CHUNK-{rank:03d}:END -->", "",
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
        "## الجولة الثانية والثلاثون: المسار C، الساميات والمصرية (2026-08-26)", "",
        f"- الوقت: {now}.",
        "- أعيد فحص الساميات أولا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01823` إلى `WO-C-OPEN-COMP-01862`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01863` إلى `WO-C-OPEN-COMP-01902`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طبق الانضباط الثلاثي: كل موجب له صوت موقع وحدث مجمد ومدار مكتوب؛ وكل بطاقة أخرى لها عائق شريف مسمى.",
        "- قاموس الإغلاق المغلق وحده مطبق: كل حالات الإغلاق والأحكام اجتازت القائمة القانونية في `data/closure-vocabulary.json`.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ الموجبان مقصوران على العضوين ومداريهما المكتوبين.",
        "- الموجبان: `ḥsr↔حسر` في الإقصاء والحرمان، و`ḫrr↔خرر` في مجرى الماء الجاري؛ كلاهما `ROOT-ECHO` بجذر كامل.",
        "- المطابقات الدلالية المرفوعة بقيت فجوات: `ḥtr↔حصر` للسفيف، و`sꜣ.t↔سدد` للحكمة، و`psš↔فصص` للحصة، و`pꜥg↔بزق` للبصق، و`r-ꜣw↔كل` للتمام، و`jwꜥ.w↔عوض` للمكافأة، و`jdb.w↔جنب` للحافة.",
        "- وسم القرض السامي العام في `nrḥ` بقي `DIRECTION-GAP` بلا مانح فردي أو طريق مكتمل.",
        "- المركبات الطقسية والقلبية الخمسة أغلقت `COMPOUND-BOUNDARY`، وظرف التقوية وحرف الجر أغلِقا `OUT-OF-SCOPE`.",
        "- الألفاظ والمراجع المشكوكة أو غير المسماة بقيت `SOURCE-GAP`، وصف ḏ المصري المؤجل بقي مستبعدا.",
        "- لم يحدث شحن أو إيداع أو إعداد مرحلي، ولم يستعمل git أو تحدث مشتقات النشر.", "",
        f"LANE-C DONE32 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
        R31.R30.R29.R28.R27.R26.R25.R24.R23.R20.R10.append(
            EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian,
        )
        R31.R30.R29.R28.R27.R26.R25.R24.R23.R20.R10.append(
            REPORT, f"{MARKER}:REPORT", report,
        )
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
