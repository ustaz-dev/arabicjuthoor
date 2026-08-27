#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 39 completion cards without shipping or git.

The live short Aramaic queue is checked before the registered Egyptian open
queue continues. The script completes WO-C-OPEN-COMP-02383..02462 in two
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

import harvest_lane_c_round38 as R38


R9 = R38.R9
AR = R38.AR
ROOT = R38.ROOT
ARAMAIC = R38.ARAMAIC
EGYPTIAN = R38.EGYPTIAN
REPORT = R38.REPORT

MARKER = "LANE-C-ROUND39-2026-08-27"
FIRST_SERIAL = 2383
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)
LEGAL_CLOSURES = R38.LEGAL_CLOSURES


def pos(member_id: str, candidate: str, verdict: str, keywords: str,
        sound: str, orbit: str, reason: str, zero: str = "") -> R9.Decision:
    return R38.R37.pos(
        member_id, candidate, verdict, keywords, sound, orbit, reason, zero,
    )


def gap(member_id: str, candidate: str, state: str, reason: str,
        sound: str = "المروحة بنيوية فقط؛ لا يرقى التشابه إلى قانون أو نسب.",
        orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
        keywords: str = "", zero: str = "") -> R9.Decision:
    return R38.gap(
        member_id, candidate, state, reason, sound, orbit, keywords, zero,
    )


def terminal(member_id: str, candidate: str, verdict: str, reason: str,
             zero: str = "") -> R9.Decision:
    return R38.terminal(member_id, candidate, verdict, reason, zero)


FEM_T = "عزلت .t علامة التأنيث الاسمية؛ بقيت الصوامت السابقة كاملة بلا إسقاط صامت جذري."
NOM_W = "عزلت .w اللاحقة الاسمية المسجلة؛ بقيت الصوامت السابقة كاملة بلا إسقاط صامت جذري."
NISBE_J = "عزلت .j ياء النسبة الاسمية المسجلة؛ بقيت الصوامت السابقة كاملة بلا إسقاط صامت جذري."


# One positive survives both lenses in this window: the flood ascender. The
# unsuccessful enemies have full sound and meaning but only letter-court events,
# so they remain TOOL-GAP. Unlicensed sound legs remain LAW-GAP.
DECISIONS: tuple[R9.Decision, ...] = (
    gap("aed-v1.0:32640", "يكن", "OPEN-CANDIDATE", "hoe لا يطابق يكن أو أكن في العربية الممسوحة، ولا يدخل فأس أو مسحاة من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:33010", "يتم", "OPEN-CANDIDATE", "destroyer بوصفه اسم سكين لا يطابق يتم في الانفراد وفقد الأب، ولا يورث اسم الأداة فعل التدمير.", zero=FEM_T),
    gap("aed-v1.0:34000", "يدب", "SOURCE-GAP", "AED لا يسمي إلا a mineral بين معقوفين، والألمانية تزيد احتمال حجر شبه كريم؛ لا معدن معين محكوم يقارن بيدب أو يضب.", zero=NOM_W),
    gap("aed-v1.0:34260", "يدز", "SOURCE-GAP", "AED لا يسمي إلا a plant بين معقوفين بلا نوع أو أثر؛ لا مرجع نباتي معين يقارن بيدز أو يدس.", zero=FEM_T),
    gap("aed-v1.0:35420", "عام", "SOURCE-GAP", "AED لا يسمي إلا a medical plant بين معقوفين بلا نوع أو أثر دوائي؛ لا مرجع نباتي محكوم يقارن بعام أو علم.", zero=NOM_W),
    gap("aed-v1.0:35820", "ععني", "OPEN-CANDIDATE", "to enclose لا يطابق ععني أو عضني وبقية المروحة في العربية الممسوحة، ولا يدخل حبس أو إحاطة من خارج الرسم."),
    gap("aed-v1.0:36090", "عوع", "SOURCE-GAP", "AED لا يقدم إلا noun/Substantiv بين معقوفين؛ لا شيء أو حدث محكوم يقارن بعوع أو عوض.", zero=NOM_W),
    gap("aed-v1.0:36140", "عون", "SOURCE-GAP", "AED لا يسمي إلا a tree and its timber بين معقوفين بلا نوع؛ لا شجر معين محكوم يقارن بعون أو غون.", zero=FEM_T),
    gap("aed-v1.0:37150", "عبر", "SOURCE-GAP", "AED لا يسمي إلا a jar used also as a bread mold بين معقوفين بلا مادة أو هيئة؛ لا وعاء معين محكوم يقارن بعبر أو عفر.", zero=FEM_T),
    gap("aed-v1.0:37190", "عبر", "OPEN-CANDIDATE", "jewellery لا يطابق عبر في الاجتياز والعبرة ولا عفر وبقية المروحة، ولا يدخل حلي من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:37440", "عفت", "OPEN-CANDIDATE", "brewer لا يطابق عفت أو عفط في العربية الممسوحة، ولا يدخل خمر أو جعة من خارج الرسم.", zero=NISBE_J),
    gap("aed-v1.0:37620", "عمان", "SOURCE-GAP", "garden pond موسوم بعلامة سؤال في اللغتين؛ لا حوض حديقة محكوم يقارن بعمان أو عمرن."),
    gap("aed-v1.0:37790", "عمعم", "SOURCE-GAP", "AED لا يسمي إلا a container for bread بين معقوفين بلا مادة أو هيئة؛ لا وعاء معين محكوم يقارن بعمعم."),
    gap("aed-v1.0:38310", "عنعن", "OPEN-CANDIDATE", "chin لا يطابق عنعن أو عنضن وبقية المروحة في العربية الممسوحة، ولا يدخل ذقن أو حنك من خارج الرسم."),
    gap("aed-v1.0:38760", "عنز", "LAW-GAP", "goat يطابق العنز مباشرة، لكن ḫ المصرية بإزاء ز العربية بلا صف مصري موقع، والمقابل خارج سطح المروحة.", sound="ꜥ↔ع في IDN-15 وn↔ن في IDN-03؛ بقي ḫ↔ز بلا صف مصري موقع.", orbit="العنز هي الأنثى من المعز، وهو مدار goat مباشرة؛ لا يمتد الحكم إلى herd أو flock، وبقي الصوت مانعا.", keywords="العنز|الماعزة|الأنثى من المعز|المعز", zero=FEM_T),
    gap("aed-v1.0:38940", "عنخ", "SOURCE-GAP", "AED لا يسمي إلا a product بين معقوفين بلا مادة أو وظيفة؛ لا منتج معين محكوم يقارن بعنخ.", zero=FEM_T),
    pos("aed-v1.0:39330", "علي", "ROOT-ECHO", "على السطح|صعده|الاستعلاء|اعتلاه", "ꜥ↔ع في IDN-15 وr↔ل عبر BR-EGYP-01 وy↔ي في IDN-23؛ الجذر كامل بعد عزل التاء.", "علي السطح أي صعده؛ والفيضان ascender يرتفع، فالحكم ECHO لا تطابق صيغة.", "الجذر والصعود مكتملان، والحكم للعضو الفيضي وحده.", zero="عزلت t من النهاية .yt تاء تأنيث؛ بقي ꜥ-r-y كاملا."),
    gap("aed-v1.0:39390", "عرعر", "SOURCE-GAP", "AED لا يقدم إلا وصفا بين معقوفين relating to renovation of divine barks بلا فعل أو أداة معينة؛ لا مرجع محكوم يقارن بعرعر."),
    gap("aed-v1.0:40010", "عحا", "OPEN-CANDIDATE", "battleground لا يطابق عحا أو عحل وضحا وبقية المروحة في العربية الممسوحة، ولا يدخل معركة أو قتال من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:40340", "تبت", "SOURCE-GAP", "AED لا يسمي إلا part of a boat بين معقوفين بلا موضع أو وظيفة؛ لا جزء سفينة معين محكوم يقارن بتبت أو تفت.", zero=NISBE_J),
    gap("aed-v1.0:40420", "عحع", "OPEN-CANDIDATE", "stela لا يطابق عحع أو عحض وبقية المروحة في العربية الممسوحة، ولا يدخل نصب أو حجر من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:41130", "عشعش", "OPEN-CANDIDATE", "gullet لا يطابق عشعش أو عسعس وبقية المروحة في العربية الممسوحة، ولا يدخل حلق أو مريء من خارج الرسم."),
    gap("aed-v1.0:44230", "وحد", "LAW-GAP", "sole/single يطابق الواحد والمنفرد دلاليا، لكن w-ꜥ-t لا يسوي w-ḥ-d بلا صفين مصريين موقعين، والمقابل خارج سطح المروحة.", sound="w↔و في IDN-10؛ بقي ꜥ↔ح وt↔د بلا مسار مصري فردي مكتمل.", orbit="الوحدة والانفراد مدار sole/single مباشرة؛ بقي الصوت مانعا لكل ترقية.", keywords="الواحد|الوحدة|المنفرد|وحده", zero=NISBE_J),
    gap("aed-v1.0:44550", "وعب", "OPEN-CANDIDATE", "pure place بوصفه السماوات لا يطابق وعب أو وطب ووجب في العربية الممسوحة، ولا يدخل طهر أو سماء من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:44620", "وعب", "OPEN-CANDIDATE", "pure garment لا يطابق وعب أو وطب ووجب في العربية الممسوحة، ولا يدخل طهر أو ثوب من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:44810", "وعر", "OPEN-CANDIDATE", "hastiness لا يطابق وعر في الخشونة وصعوبة المكان ولا وعل وبقية المروحة، ولا يدخل عجلة من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:45170", "وبن", "OPEN-CANDIDATE", "the east بمعنى sunrise لا يطابق وبن في العربية الممسوحة، ولا يدخل شرق أو شروق من خارج الرسم.", zero=NOM_W),
    gap("aed-v1.0:45290", "وبخ", "OPEN-CANDIDATE", "clean clothing لا يطابق وبخ في اللوم والتقريع، ولا يدخل نظافة أو لباس من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:45550", "وب", "SOURCE-GAP", "inventory وentry موسومان بالسؤال في الإنجليزية، والألمانية تتردد بين بيان مفرد وقائمة وجرد؛ لا بنية وثيقة واحدة محكومة تقارن بوب أو وف.", zero=FEM_T),
    gap("aed-v1.0:45730", "وب", "OPEN-CANDIDATE", "household وhousehold list لا يطابقان وب أو وف وبقية المروحة في العربية الممسوحة، ولا يدخل أهل أو بيت من خارج الرسم.", zero=FEM_T),
    terminal("aed-v1.0:45770", "∅", "COMPOUND-BOUNDARY", "الرسم `wpw-r` ذو حدين موصولين ويؤدي وظيفة except for؛ حد المركب يمنع حمل الجزأين على جذر عربي مفرد."),
    gap("aed-v1.0:46420", "ونو", "OPEN-CANDIDATE", "hour لا يطابق ونو أو ونن ووين في العربية الممسوحة، ولا يدخل ساعة أو حين من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:46500", "ونون", "OPEN-CANDIDATE", "to threaten لا يطابق ونون في العربية الممسوحة، ولا يدخل وعيد أو تهديد من خارج الرسم."),
    gap("aed-v1.0:46570", "ونو", "OPEN-CANDIDATE", "stars بوصفها hour-stars لا يطابق ونو أو ونن ووين في العربية الممسوحة، ولا يدخل نجم من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:46770", "يمن", "LAW-GAP", "right side يطابق اليمن والجهة اليمنى، لكن w-n-m لا يسوي y-m-n بلا قلب صامتين ومسار مصري موقع، والمقابل خارج سطح المروحة.", sound="الدلالة تقترح يمن؛ بقي w↔ي مشروطا بفرع آخر، كما بقي قلب n-m إلى m-n بلا قانون مصري موقع.", orbit="اليمن خلاف اليسار والجهة اليمنى مدار مباشر، لكن الحكم للصفة المسمى عضوها وحدها ولا ينتقل إلى متجانسات wnm.j.", keywords="اليمن|اليمين|خلاف اليسار|الجهة اليمنى", zero=NISBE_J),
    gap("aed-v1.0:47740", "وري", "OPEN-CANDIDATE", "cloth for straining liquids لا يطابق وري في إيراء النار وداء الرئة ولا ولي، ولا يدخل نسيج أو تصفية من خارج الجذر.", zero=FEM_T),
    terminal("aed-v1.0:47890", "∅", "OUT-OF-SCOPE", "Wernu اسم كاهن أو رتبة كهنوتية مخصوصة؛ اللقب الثقافي لا يصدر جذرا عربيا من وظيفة الكاهن.", zero=NOM_W),
    gap("aed-v1.0:48180", "ورش", "OPEN-CANDIDATE", "watchhouse لا يطابق ورش في النشاط أو ورس في الصبغ، ولا يدخل حراسة أو بيت من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:48360", "وهي", "TOOL-GAP", "failures يطابق وهي في السقوط والضعف، والصوت كامل، لكن الأداة لا تسجل لوهي حدث جذر أو نواة؛ محاكم الحروف وحدها لا تكفي لإصدار ROOT-ECHO.", sound="w↔و في IDN-10 وh↔ه في IDN-20 وy↔ي في IDN-23؛ الجذر كامل بعد عزل واو الجمع.", orbit="وهى الرجل إذا سقط وضعف ولم يستقم أمره؛ وهو مدار failure مباشرة، وبقي حدث الأداة مانعا.", keywords="وهى|وهي|ضعف|سقط|لا يستقيم أمره", zero="عزلت w الأخيرة من .yw علامة جمع المذكّر؛ بقي w-h-y كاملا."),
    gap("aed-v1.0:48690", "وحر", "OPEN-CANDIDATE", "cauldron لا يطابق وحر أو وحل في العربية الممسوحة، ولا يدخل قدر أو مرجل من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:48870", "وحع", "SOURCE-GAP", "AED لا يسمي إلا a duck بين معقوفين، والألمانية تقترح Bläßgans بعلامة سؤال؛ لا نوع طائر واحد محكوم يقارن بوحع.", zero=FEM_T),
    gap("aed-v1.0:48970", "وحوح", "OPEN-CANDIDATE", "to disappear أو fade لا يطابق وحوح في العربية الممسوحة، ولا يدخل محو أو خفاء من خارج الرسم."),
    gap("aed-v1.0:49600", "يسر", "LAW-GAP", "wealth يطابق اليسار والميسرة في الغنى، لكن w المصرية بإزاء ي العربية بلا صف مصري موقع، والمقابل خارج سطح المروحة.", sound="s↔س في IDN-07 وr↔ر في IDN-01؛ بقي w↔ي قيدا ساميا شماليا لا صفا مصريا موقعا.", orbit="اليسار والميسرة هما السعة والغنى، وهو مدار wealth مباشرة؛ لا يشمل strength، وبقي الصوت مانعا.", keywords="اليسار|الميسرة|السعة|الغنى|أيسر", zero=NOM_W),
    gap("aed-v1.0:49700", "وصل", "OPEN-CANDIDATE", "front hawser/prow rope اسم حبل بحري، ولا يثبت أن وظيفته مدار وصل العربي نفسه؛ لا يرث اسم الأداة فعل الربط بالقوة.", zero=FEM_T),
    gap("aed-v1.0:49870", "وسع", "LAW-GAP", "broad hall يطابق السعة والاتساع دلاليا، لكن ḫ المصرية بإزاء ع العربية بلا صف مصري موقع، والمقابل خارج سطح المروحة.", sound="w↔و في IDN-10 وs↔س في IDN-07؛ بقي ḫ↔ع بلا صف مصري موقع.", orbit="الواسع ضد الضيق، وbroad وصف السعة مباشرة؛ الحكم للوصف لا لاسم القاعة، وبقي الصوت مانعا.", keywords="وسع|واسع|السعة|اتسع|ضد الضيق", zero=FEM_T),
    gap("aed-v1.0:49970", "وزش", "OPEN-CANDIDATE", "urine لا يطابق وزش أو وزس ووسش في العربية الممسوحة، ولا يدخل بول من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:50530", "وشف", "SOURCE-GAP", "AED لا يسمي إلا a cat-like animal بين معقوفين بلا نوع أو صفات فاصلة؛ لا حيوان معين محكوم يقارن بوشف أو وسف.", zero=FEM_T),
    gap("aed-v1.0:50680", "وشت", "SOURCE-GAP", "AED لا يسمي إلا an affliction of the eyes ويقترح dryness بعلامة سؤال؛ لا مرض عين محكوم يقارن بوشت أو وسط.", zero=FEM_T),
    gap("aed-v1.0:51260", "وتش", "SOURCE-GAP", "AED لا يسمي إلا a kind of stone بين معقوفين بلا معدن أو خاصية؛ لا حجر معين محكوم يقارن بوتش أو وطش.", zero="عزلت .y ياء النسبة الاسمية المسجلة؛ بقي w-t-š كاملا بلا إسقاط صامت جذري."),
    gap("aed-v1.0:51360", "وثز", "OPEN-CANDIDATE", "throne لا يطابق وثز أو وتس ووطس في العربية الممسوحة، ولا يدخل عرش أو سرير من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:51460", "وثز", "OPEN-CANDIDATE", "accuser لا يطابق وثز أو وتس ووطس في العربية الممسوحة، ولا يدخل خصومة أو اتهام من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:51760", "ودن", "OPEN-CANDIDATE", "offering لا يطابق ودن أو وضن في العربية الممسوحة، ولا يدخل قربان أو هدية من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:51830", "ودن", "OPEN-CANDIDATE", "offerer لا يطابق ودن أو وضن في العربية الممسوحة، ولا يدخل قرب أو هبة من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:53380", "بلو", "OPEN-CANDIDATE", "battlefield of bulls لا يطابق بلو أو برو في العربية الممسوحة، ولا يدخل حرب أو ثور من خارج الرسم."),
    gap("aed-v1.0:53650", "باس", "OPEN-CANDIDATE", "beaker/pail لا يطابق باس أو بلس وبرس وبقية المروحة في العربية الممسوحة، ولا يدخل كوب أو دلو من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:53750", "باق", "SOURCE-GAP", "الإنجليزية تسمي moringa oil، لكن الألمانية تتردد بين moringa oil وolive oil بعلامتي سؤال؛ لا مادة زيت واحدة محكومة يقارن بها باق أو برق.", zero=FEM_T),
    gap("aed-v1.0:53890", "برك", "OPEN-CANDIDATE", "taxes/deliveries/pay لا يطابق برك في الثبات والبركة ولا بلك، ولا يدخل ضريبة أو أجر من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:54000", "برجس", "SOURCE-GAP", "AED لا يسمي إلا a plant بين معقوفين ويقترح thorn-bush بعلامة سؤال؛ لا نوع نبات محكوم يقارن ببرجس أو برقس."),
    gap("aed-v1.0:54070", "باد", "SOURCE-GAP", "AED لا يسمي إلا a measuring vessel بين معقوفين بلا مادة أو سعة؛ لا إناء قياس معين محكوم يقارن بباد أو بلد.", zero=FEM_T),
    terminal("aed-v1.0:54240", "∅", "OUT-OF-SCOPE", "King of Lower Egypt لقب ملكي مؤسسي مخصوص؛ اللقب الثقافي لا يصدر جذرا عربيا من اسم الإقليم.", zero=NISBE_J),
    gap("aed-v1.0:54380", "بير", "OPEN-CANDIDATE", "mining region لا يطابق بير أو بيل في العربية الممسوحة، ولا يدخل معدن أو إقليم من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:54440", "بهر", "LAW-GAP", "wonders يطابق بهر في التعجب والغلبة المدهشة دلاليا، لكن j-ꜣ لا يسوي h-r بلا صفين مصريين موقعين، والمقابل خارج سطح المروحة.", sound="b↔ب في IDN-05؛ بقي j↔ه وꜣ↔ر بلا مسار مصري فردي مكتمل.", orbit="بهر تأتي بمعنى عجبا، والباهر يغلب بحسنه أو ضوئه؛ مدار wonders مباشر، وبقي الصوت مانعا.", keywords="عجبا|التعجب|باهر|غلب|أعجب", zero=NOM_W),
    gap("aed-v1.0:54650", "بين", "OPEN-CANDIDATE", "harp لا يطابق بين في الظهور والفصل ولا بئن، ولا يدخل آلة وترية من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:55280", "بور", "SOURCE-GAP", "AED يتردد بين hill وcovert وswamp thicket بعلامات سؤال؛ لا تضريس أو غطاء أو نبات واحد محكوم يقارن ببور أو بول.", zero=FEM_T),
    gap("aed-v1.0:55430", "ببي", "SOURCE-GAP", "region of the collar bones موسوم بعلامة سؤال في الألمانية ولا يحدد حدا تشريحيا محكوما؛ لا عضو معين يقارن بببي.", zero="عزلت .t علامة الاسم الطرفية المسجلة؛ بقي b-b-y كاملا بلا إسقاط صامت جذري."),
    gap("aed-v1.0:55640", "بنن", "OPEN-CANDIDATE", "swelling/sore لا يطابق بنن في أطراف الأصابع والرائحة ولا بين وبون، ولا يدخل ورم أو التهاب من خارج الجذر.", zero=FEM_T),
    terminal("aed-v1.0:55720", "∅", "OUT-OF-SCOPE", "Benben اسم الحجر المقدس والمسلة في الثقافة المصرية؛ اسم الأثر المخصوص لا يصدر جذرا عربيا من الحجر أو القداسة."),
    gap("aed-v1.0:55910", "بنن", "OPEN-CANDIDATE", "threshold لا يطابق بنن في أطراف الأصابع والرائحة، ولا يدخل عتبة أو باب من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:56090", "بنهم", "OPEN-CANDIDATE", "jubilation لا يطابق بنهم أو بنحم في العربية الممسوحة، ولا يدخل فرح أو هتاف من خارج الرسم."),
    gap("aed-v1.0:56470", "بربس", "SOURCE-GAP", "AED لا يسمي إلا a beverage بين معقوفين ويقترح wine بعلامة سؤال؛ لا شراب معين محكوم يقارن ببربس أو بربش."),
    gap("aed-v1.0:56870", "بحن", "OPEN-CANDIDATE", "knife لا يطابق بحن في العربية الممسوحة، ولا يدخل سكين أو مدية من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:57100", "بخخ", "OPEN-CANDIDATE", "fiery breath لا يطابق بخخ في كلمة المدح وهدير البعير وسكون فور الحر؛ لا يدخل نفس أو لهب من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:57480", "بزن", "SOURCE-GAP", "الإنجليزية لا تقدم إلا verb بين معقوفين، والألمانية وحدها تسمي heed/notice؛ لا حدث ثنائي المصدر محكوم يقارن ببزن أو بسن."),
    gap("aed-v1.0:57710", "بقبق", "SOURCE-GAP", "recalcitrance موسوم بعلامة سؤال في اللغتين؛ لا عناد محكوم يقارن ببقبق."),
    gap("aed-v1.0:58000", "بغا", "OPEN-CANDIDATE", "shouting لا يطابق بغا في النظر إلى الشيء والثمر قبل نضجه ولا بجل وبقل، ولا يدخل صياح من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:58190", "بتين", "SOURCE-GAP", "AED لا يسمي إلا fishes بين معقوفين وبعلامة سؤال؛ لا نوع سمك أو جمع محكوم يقارن ببتين أو بطين."),
    gap("aed-v1.0:58880", "باور", "SOURCE-GAP", "AED لا يسمي إلا a kind of medical drink بين معقوفين، والألمانية لا تزيد إلا أنه رديء النوع؛ لا شراب معين يقارن بباور أو فاور."),
    gap("aed-v1.0:59070", "فري", "OPEN-CANDIDATE", "birds بوصفها what flies لا يطابق فري في الشق والقطع ولا بري، ولا يدخل طير من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:59160", "بلو", "LAW-GAP", "burden بمعنى suffering/disease يطابق البلاء والبلوى دلاليا، لكن ꜣ المصرية بإزاء ل العربية بلا صف مصري موقع.", sound="p↔ب عبر LAB-01 وw↔و في IDN-10؛ بقي ꜣ↔ل بلا صف مصري موقع.", orbit="البلاء والبلوى للمحنة والابتلاء في الخير والشر، وهو مدار suffering مباشرة؛ بقي الصوت الأوسط مانعا.", keywords="البلاء|البلوى|البلية|ابتلي|محنة", zero=FEM_T),
    gap("aed-v1.0:59360", "فرق", "SOURCE-GAP", "ladder موسوم بعلامة سؤال في اللغتين؛ لا أداة صعود محكومة يقارن بها فرق أو فلق.", zero=FEM_T),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT
assert {item.state for item in DECISIONS} <= LEGAL_CLOSURES
assert {item.verdict for item in DECISIONS} <= LEGAL_CLOSURES

OUTSIDE_FAN = {
    "aed-v1.0:38760", "aed-v1.0:44230", "aed-v1.0:46770",
    "aed-v1.0:49600", "aed-v1.0:49870", "aed-v1.0:54440",
}

WITNESS_NOTES = {
    "aed-v1.0:38760": "أثبت كتاب العين والصحاح أن العنز هي الأنثى من المعز؛ ثبت مدار goat، وبقي ḫ↔ز بلا صف مصري.",
    "aed-v1.0:44230": "أثبت المحكم ولسان العرب الوحدة والانفراد والواحد؛ ثبت مدار sole/single، وبقيت رجلان صوتيتان.",
    "aed-v1.0:46770": "أثبت كتاب العين ولسان العرب اليمن واليمين خلاف اليسار؛ ثبت مدار right side، وبقي القلب الصوتي بلا قانون.",
    "aed-v1.0:48360": "أثبت كتاب العين ولسان العرب وهي الرجل بمعنى سقط وضعف؛ ثبت مدار failure والصوت، وبقي حدث الجذر أو النواة غائبا من الأداة.",
    "aed-v1.0:49600": "أثبت الصحاح والمحكم أن اليسار والميسرة السعة والغنى؛ ثبت مدار wealth، وبقي w↔ي بلا صف مصري.",
    "aed-v1.0:49870": "أثبت كتاب العين ولسان العرب السعة والاتساع وضدهما الضيق؛ ثبت مدار broad، وبقي ḫ↔ع بلا صف مصري.",
    "aed-v1.0:54440": "أثبت الصحاح والمحكم بهر بمعنى عجبا والغلبة بالضوء أو الحسن؛ ثبت مدار wonders، وبقيت رجلان صوتيتان.",
    "aed-v1.0:59160": "أثبت المحكم وكتاب العين البلاء والبلوى للمحنة والابتلاء؛ ثبت مدار suffering، وبقي ꜣ↔ل بلا صف مصري.",
}


def round39_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R38.round38_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND38-COMPLETION", "ROUND39-COMPLETION")
    card = card.replace(
        f"round38-egyptian-rank={rank}/{CARD_COUNT}",
        f"round39-egyptian-rank={rank}/{CARD_COUNT}",
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
        raise SystemExit("Round-thirty-nine marker already exists; append refused.")

    aramaic_exact, _ = R9.load_entries("aramaic")
    aramaic_queue = R9.select_aramaic(aramaic_text, aramaic_exact)
    assert not aramaic_queue, (
        "Aramaic short live-open queue is no longer exhausted: "
        f"{[item['entry_id'] for item in aramaic_queue[:10]]}"
    )

    egyptian_exact, _ = R9.load_entries("egyptian")
    queue = R38.R37.R36.R35.R34.R33.R32.R31.R30.R29.select_egyptian_fast(
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
        round39_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة التاسعة والثلاثون: استمرار المخزون المصري المسجل المفتوح (2026-08-27)", "",
        (
            "أعيد فحص الآرامية أولا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرا، فسجل الانتقال المسمى `{TRANSITION}`. انتقيت ثمانين "
            "بطاقة مصرية بدءا من `WO-C-OPEN-COMP-02383` بقصر الهيكل ثم موضع "
            "اللقطة. استبعد صف ḏ المؤجل. في كل بطاقة عرضت إصابات AED كلها بلا "
            "حد، وكتب وسم الطريق والرسم والمدخل المختار، وحفظ الاختلاف "
            "والمتجانسات بلا محو. فحصت حالة الإغلاق والحكم آليا على القائمة "
            "القانونية وحدها في `data/closure-vocabulary.json`."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-02383 إلى WO-C-OPEN-COMP-02422", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-02423 إلى WO-C-OPEN-COMP-02462", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([
                f"<!-- LANE-C-R39-EGYPTIAN-CHUNK-{rank:03d}:END -->", "",
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
        "## الجولة التاسعة والثلاثون: المسار C، الساميات والمصرية (2026-08-27)", "",
        f"- الوقت: {now}.",
        "- أعيد فحص الساميات أولا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-02383` إلى `WO-C-OPEN-COMP-02422`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-02423` إلى `WO-C-OPEN-COMP-02462`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طبق الانضباط الثلاثي: كل موجب له صوت موقع وحدث مجمد ومدار مكتوب؛ وكل بطاقة أخرى لها عائق شريف مسمى.",
        "- قاموس الإغلاق المغلق وحده مطبق: كل حالات الإغلاق والأحكام اجتازت القائمة القانونية في `data/closure-vocabulary.json`.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ الموجب مقصور على العضو ومداره المكتوب.",
        "- الموجب: `ꜥr.yt↔علي` في صعود الفيضان بعد عزل تاء التأنيث وصف BR-EGYP-01؛ حكمه `ROOT-ECHO` مقصور على العضو.",
        "- بقي `wh.yw↔وهي` في الضعف والإخفاق `TOOL-GAP`: الصوت والمعنى مباشران، لكن الأداة لا تسجل حدث جذر أو نواة، ومحاكم الحروف وحدها لا تصدر ROOT-ECHO.",
        "- المطابقات الدلالية المرفوعة بقيت فجوات قانون: `ꜥnḫ.t↔عنز` للماعز، و`wꜥ.tj↔وحد` للانفراد، و`wnm.j↔يمن` لجهة اليمين، و`wsr.w↔يسر` للغنى.",
        "- وبقيت `wsḫ.t↔وسع` للعرض، و`bjꜣ.w↔بهر` للعجب، و`pꜣw.t↔بلو` للبلاء فجوات قانون لأن رجلا صوتية أو أكثر غير موقعة للمصرية.",
        "- المراجع النباتية والطبية والأدوات الموسومة بين معقوفين أو بعلامة سؤال بقيت `SOURCE-GAP`؛ لم يحسم التخمين نوع الشيء بالقوة.",
        "- اللقب الملكي والكاهن وحجر Benben أغلقت `OUT-OF-SCOPE`، والمركب `wpw-r` أغلق `COMPOUND-BOUNDARY`، وصف ḏ المصري المؤجل بقي مستبعدا.",
        "- لم يحدث شحن أو إيداع أو إعداد مرحلي، ولم يستعمل git أو تحدث مشتقات النشر.", "",
        f"LANE-C DONE39 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
            R38.R37.R36.R35.R34.R33.R32.R31.R30.R29.R28.R27.R26.R25.R24.R23.R20.R10.append
        )
        append(EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian)
        append(REPORT, f"{MARKER}:REPORT", report)
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
