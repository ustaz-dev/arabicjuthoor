#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 41 completion cards without shipping or git.

The live short Aramaic queue is checked before the registered Egyptian open
queue continues. The script completes WO-C-OPEN-COMP-02543..02622 in two
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

import harvest_lane_c_round40 as R40


R9 = R40.R9
AR = R40.AR
ROOT = R40.ROOT
ARAMAIC = R40.ARAMAIC
EGYPTIAN = R40.EGYPTIAN
REPORT = R40.REPORT

MARKER = "LANE-C-ROUND41-2026-08-28"
FIRST_SERIAL = 2543
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)
LEGAL_CLOSURES = R40.LEGAL_CLOSURES


def pos(member_id: str, candidate: str, verdict: str, keywords: str,
        sound: str, orbit: str, reason: str, zero: str = "") -> R9.Decision:
    return R40.pos(
        member_id, candidate, verdict, keywords, sound, orbit, reason, zero,
    )


def gap(member_id: str, candidate: str, state: str, reason: str,
        sound: str = "المروحة بنيوية فقط؛ لا يرقى التشابه إلى قانون أو نسب.",
        orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
        keywords: str = "", zero: str = "") -> R9.Decision:
    return R40.gap(
        member_id, candidate, state, reason, sound, orbit, keywords, zero,
    )


def terminal(member_id: str, candidate: str, verdict: str, reason: str,
             zero: str = "") -> R9.Decision:
    return R40.terminal(member_id, candidate, verdict, reason, zero)


FEM_T = R40.FEM_T
NOM_W = R40.NOM_W
NISBE_J = R40.NISBE_J


# One positive survives all three legs in this window: ḥsb.w, after the
# recorded nominal .w is isolated, is full-sound Arabic حسب and names
# accounting/reckoning directly. The equally full-sound ḫsf.t has an Arabic
# punishment/humiliation sense, but its frozen root event records collapse of
# the supporting base rather than punitive imposition, so it remains TOOL-GAP.
# Uncertain referents remain SOURCE-GAP, explicit multi-boundary phrases are
# isolated, and a general Semitic-loan label never supplies a donor or route.
DECISIONS: tuple[R9.Decision, ...] = (
    gap("aed-v1.0:88820", "نسنس", "SOURCE-GAP", "AED لا يقدم إلا verb/Substantiv بين معقوفين ويتردد في الولادة أو الطرح؛ لا حدث واحد محكوم يقارن بنسنس."),
    gap("aed-v1.0:89790", "نتلي", "OPEN-CANDIDATE", "to run هو الحس الثابت وhurry موسوم بالشك، ولا يطابق نتلي أو بقية المروحة في العربية الممسوحة؛ لا يدخل جرى أو أسرع من خارج الرسم."),
    gap("aed-v1.0:90290", "نثر", "SOURCE-GAP", "الإنجليزية لا تعين إلا garment وتقترح جلد سنوري، والألمانية تسمي مئزر جلد فهد؛ لا لباس واحد محكوم يقارن بنثر.", zero=FEM_T),
    gap("aed-v1.0:90460", "نثر", "OPEN-CANDIDATE", "beer أو beer jug لا يطابق نثر في التفريق والطرح، ولا يدخل جعة أو إناء من خارج الجذر.", zero=NISBE_J),
    gap("aed-v1.0:90510", "نثر", "OPEN-CANDIDATE", "natron لا يطابق نثر ولا نثل ونتر في العربية الممسوحة، ولا يدخل نطرون بزيادة صامتة غير مسماة.", zero=NISBE_J),
    terminal("aed-v1.0:90570", "∅", "OUT-OF-SCOPE", "Divine اسم فرقة مخصوصة من كهنة الجنازة؛ اللقب التنظيمي الثقافي لا يصدر جذرا عربيا معجميا."),
    terminal("aed-v1.0:91960", "∅", "COMPOUND-BOUNDARY", "الرسم `r-ꜥqꜣ` ذو حدين صريحين ويؤدي وظيفة on a level with؛ حد العبارة يمنع حملها على جذر عربي مفرد."),
    terminal("aed-v1.0:92110", "∅", "COMPOUND-BOUNDARY", "الرسم `r-rw.t` تركيب اتجاهي ذو حدين لمعنى outside؛ لا تعامل العبارة الظرفية مادة جذرية مفردة."),
    terminal("aed-v1.0:92280", "∅", "COMPOUND-BOUNDARY", "الرسم `r-ḫnt` تركيب اتجاهي موصول لمعنيي outward وforward؛ حداه المكتوبان يمنعان دمجه في جذر مفرد."),
    terminal("aed-v1.0:92790", "∅", "COMPOUND-BOUNDARY", "الرسم `rʾ-ꜥ-ḫt` متعدد الحدود ويسمي combat بالمجموع؛ لا يسقط حد أو يحمل المركب على جذر عربي واحد."),
    terminal("aed-v1.0:93100", "∅", "COMPOUND-BOUNDARY", "الرسم `rʾ-sṯꜣ` ذو حدين ويسمي ممرا مائلا مخصوصا في مقبرة ملكية؛ المركب لا يصدر جذر ممر مفردا."),
    gap("aed-v1.0:93570", "روي", "SOURCE-GAP", "AED لا يحسم هل الوسم لنشاط أم رقصة أم لعبة، وكل التعريف بين معقوفين؛ لا حدث واحد محكوم يقارن بروي.", zero=FEM_T),
    gap("aed-v1.0:94200", "رمي", "OPEN-CANDIDATE", "tears لا يطابق رمي في الإلقاء والقذف، ولا يجعل خروج الدمع رميا من غير شاهد معجمي مباشر.", zero=FEM_T),
    gap("aed-v1.0:95400", "ررم", "SOURCE-GAP", "AED لا يسمي إلا a fruit بين معقوفين ويقترح mandrake بعلامة سؤال؛ لا ثمرة معينة محكومة تقارن بررم.", zero=FEM_T),
    gap("aed-v1.0:95490", "رهن", "SOURCE-GAP", "AED لا يسمي إلا symptom of an illness بين معقوفين بلا تشخيص أو وصف فاصل؛ لا عرض معين محكوم يقارن برهن.", zero=NOM_W),
    terminal("aed-v1.0:95730", "∅", "COMPOUND-BOUNDARY", "الرسم `rḫ-n=f` يضم حدا وضميرا لاحقا ويسمي تمثالا إلهيا مخصوصا؛ لا يحمل التركيب على جذر عربي مفرد."),
    gap("aed-v1.0:95930", "لخت", "OPEN-CANDIDATE", "washerman لا يطابق لخت أو لخط في العربية الممسوحة، ولا يدخل غسل أو قصارة من خارج الرسم.", zero=NISBE_J),
    terminal("aed-v1.0:96000", "∅", "COMPOUND-BOUNDARY", "الرسم `rs-tp` ذو حدين لمعنى watchful/vigilant؛ البنية الوصفية المركبة لا تختزل إلى جذر عربي واحد."),
    gap("aed-v1.0:96060", "رسي", "OPEN-CANDIDATE", "watch وguard post لا يطابقان رسي في العربية الممسوحة، ولا يدخل رصد أو حرس من خارج الرسم.", zero=FEM_T),
    gap("aed-v1.0:96130", "رسو", "OPEN-CANDIDATE", "awakening/dream لا يطابق رسو في الثبات والإرساء، ولا يسوي اليقظة في النوم برسو الشيء.", zero=FEM_T),
    gap("aed-v1.0:96280", "رشرش", "OPEN-CANDIDATE", "joy لا يطابق رشرش أو لشلش في العربية الممسوحة، ولا يدخل فرح أو سرور من خارج الرسم."),
    gap("aed-v1.0:96350", "رقو", "SOURCE-GAP", "symptom of resistance الطبي بين معقوفين، والألمانية تعلق مقاومة تورم بعلامة سؤال؛ لا عرض واحد محكوم يقارن برقو.", zero=FEM_T),
    gap("aed-v1.0:97630", "هام", "OPEN-CANDIDATE", "aviary لا يطابق هام في الذهاب أو الهمام ولا بقية المروحة، ولا يدخل حظيرة طير من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:97690", "هرهر", "SOURCE-GAP", "AED لا يقدم إلا noun/Substantiv بين معقوفين؛ لا شيء أو حدث محكوم يقارن بهرهر."),
    gap("aed-v1.0:98000", "حوتن", "SOURCE-GAP", "AED لا يسمي إلا fish(es) بين معقوفين بلا نوع أو صفة؛ لا سمك معين محكوم يقارن بحوتن."),
    gap("aed-v1.0:98200", "حبحب", "OPEN-CANDIDATE", "to traverse/to tread لا يطابق حبحب الذي تسمي به العربية جريان الماء قليلا قليلا والضعف؛ لا يحمل جريان الماء على وطء المكان."),
    terminal("aed-v1.0:98290", "∅", "OUT-OF-SCOPE", "Hepiu اسم علم لحية مخصوصة في هليوبوليس؛ الاسم الديني الثقافي لا يصدر جذر حية أو سم معجميا."),
    gap("aed-v1.0:99230", "حرن", "SOURCE-GAP", "AED لا يسمي إلا variety of spelt بين معقوفين بلا خصائص أو تعيين صنفي؛ لا حبة معينة محكومة تقارن بحرن.", zero=FEM_T),
    gap("aed-v1.0:99340", "حسمق", "OPEN-CANDIDATE", "storming/attacking في وصف دخول الملك المعركة لا يطابق حسمق في العربية الممسوحة، ولا يدخل هجوم من خارج الرسم."),
    gap("aed-v1.0:99410", "حكر", "SOURCE-GAP", "AED لا يسمي إلا a snake بين معقوفين، والألمانية لا تزيد إلا أنها أنثى؛ لا نوع حية محكوم يقارن بحكر.", zero=FEM_T),
    gap("aed-v1.0:99810", "حوت", "OPEN-CANDIDATE", "mine/quarry لا يطابق حوت في السمك والحومان، ولا يدخل معدن أو محجر من خارج الجذر.", zero="عزلت تاء التأنيث الأخيرة من `.tt`؛ بقي ḥ-w-t كاملا، ولم تسقط صامتة الجذر."),
    gap("aed-v1.0:100820", "حري", "OPEN-CANDIDATE", "malady لا يطابق حري أو حلي في العربية الممسوحة، ولا يدخل مرض أو بلاء من خارج الرسم.", zero=FEM_T),
    gap("aed-v1.0:101490", "حرم", "OPEN-CANDIDATE", "droppings/excrement لا يطابق حرم أو حلم في العربية الممسوحة، ولا يدخل روث أو عذرة من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:101550", "حاق", "OPEN-CANDIDATE", "plunder لا يطابق حاق في الإحاطة والنزول ولا حلق وحرق، ولا يدخل نهب أو سلب من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:101680", "حرت", "OPEN-CANDIDATE", "covering/garment لا يطابق حرت أو حلت في العربية الممسوحة، ولا يدخل ستر أو ثوب من خارج الرسم."),
    gap("aed-v1.0:101920", "حيم", "SOURCE-GAP", "AED لا يسمي إلا a plant بين معقوفين بلا نوع أو أثر؛ لا نبات معين محكوم يقارن بحيم."),
    gap("aed-v1.0:102170", "حضب", "OPEN-CANDIDATE", "enemy لا يطابق حضب أو حعب وحغب في العربية الممسوحة، ولا يدخل عدو أو حرب من خارج الرسم.", zero="عزلت .y اللاحقة الاسمية المسجلة؛ بقي ḥ-ꜥ-b كاملا بلا إسقاط صامت جذري."),
    gap("aed-v1.0:102790", "حوي", "OPEN-CANDIDATE", "stroke/blow لا يطابق حوي في الجمع والإحراز، ولا يدخل ضرب أو صفع من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:103160", "حور", "SOURCE-GAP", "AED لا يسمي إلا a substance used medically بين معقوفين بلا مادة أو أثر؛ لا دواء معين محكوم يقارن بحور.", zero=NOM_W),
    gap("aed-v1.0:104390", "حفر", "OPEN-CANDIDATE", "snake بالمعنى العام لا يطابق حفر ولا حفل وحفا في العربية الممسوحة، ولا يدخل حية من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:104560", "حفد", "MORPHOLOGY-GAP", "حفد العربي هو الإسراع والخفة في السير والعمل، لا climb/fly نفسيهما؛ وفوق ذلك يسجل AED `verb_4-inf` فلا يجيز إسقاط i̯ الأخيرة إلى حفد بلا تحليل صرفي فردي.", sound="ḥ↔ح في IDN-14 وf↔ف في IDN-06 وd↔د في IDN-09؛ بقيت i̯ المصرية النهائية بلا مقابل ولا صفر صرفي محكوم.", orbit="حفد البعير إذا أسرع في سيره، وهو حركة سريعة تجاور fly ولا تساوي الصعود أو الطيران؛ بقيت الدلالة والبنية مانعتين.", keywords="حفد البعير|أسرع|السرعة|خف في العمل"),
    gap("aed-v1.0:105240", "حمي", "OPEN-CANDIDATE", "steering oar لا يطابق حمي في المنع والحماية، ولا يرث اسم المجداف فعل توجيه السفينة.", zero=FEM_T),
    gap("aed-v1.0:105340", "حمو", "SOURCE-GAP", "AED لا يسمي إلا a substance used medically بين معقوفين بلا ماهية أو وظيفة؛ لا مادة طبية محكومة تقارن بحمو.", zero=FEM_T),
    gap("aed-v1.0:105470", "حمو", "OPEN-CANDIDATE", "skillful لا يطابق حمو في العربية الممسوحة، ولا يدخل مهارة أو حذق من خارج الرسم.", zero=NOM_W),
    gap("aed-v1.0:105630", "حمحم", "SOURCE-GAP", "flight وعلامة surprise كلاهما موسومان بالشك في AED؛ لا حدث واحد محكوم يقارن بحمحم."),
    gap("aed-v1.0:106140", "حنت", "SOURCE-GAP", "الإنجليزية لا تسمي إلا a boat بين معقوفين، والألمانية تجعلها سفينة رأس القنفذ في رحلة ليلية دينية؛ لا نوع سفينة واحد محكوم يقارن بحنت."),
    gap("aed-v1.0:106260", "حنع", "OPEN-CANDIDATE", "accumulation/contraction في وصف طبي لا يطابق حنع أو حنض في العربية الممسوحة، ولا يدخل تجمع أو تقلص من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:106340", "حنو", "SOURCE-GAP", "AED لا يسمي إلا jug for beer/wine بين معقوفين بلا مادة أو هيئة؛ لا إناء معين محكوم يقارن بحنو.", zero=FEM_T),
    gap("aed-v1.0:106940", "حنحن", "SOURCE-GAP", "AED لا يسمي إلا affliction of the legs بين معقوفين بلا تشخيص أو أعراض؛ لا مرض واحد محكوم يقارن بحنحن."),
    gap("aed-v1.0:107190", "حنك", "OPEN-CANDIDATE", "offerings/donation لا يطابق حنك في عضو الفم والاحتناك، ولا يدخل هبة أو قربان من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:107720", "حرتي", "OPEN-CANDIDATE", "to travel overland لا يطابق حرتي أو حرطي في العربية الممسوحة، ولا يدخل سفر أو بر من خارج الرسم."),
    terminal("aed-v1.0:108280", "∅", "COMPOUND-BOUNDARY", "الرسم `ḥr-tp` ذو حدين ويؤدي وظيفة upon/on behalf of؛ العبارة الجارية مجرى حرف الجر لا تعامل جذرا مفردا."),
    terminal("aed-v1.0:108470", "∅", "OUT-OF-SCOPE", "those-who-are-above لقب جمعي ثقافي للنجوم؛ الوصف المكاني الإحالي لا يصدر جذر نجم معجميا."),
    gap("aed-v1.0:109120", "حرر", "OPEN-CANDIDATE", "creeping/crawling creatures أو worm لا يطابق حرر في الخلوص والحرارة، ولا يدخل دودة أو حشرة من خارج الجذر.", zero=FEM_T),
    pos("aed-v1.0:109940", "حسب", "ROOT-TRACE", "حسبته|عددته|الحساب|استعمال العدد|حسابا", "ḥ↔ح في IDN-14 وs↔س في IDN-07 وb↔ب في IDN-05؛ الجذر كامل بعد عزل اللاحقة الاسمية .w.", "حسب الشيء إذا عده، والحساب استعمال العدد؛ وهو accounting/reckoning مباشرة، والحدث المجمد يجمع المنتشر في حيز مضبوط.", "TRACE مقصور على العد والحساب في هذا العضو؛ لا يورث الظن أو الحسب الاجتماعي الحكم.", zero=NOM_W),
    gap("aed-v1.0:110030", "حزمن", "OPEN-CANDIDATE", "to cleanse/to purify لا يطابق حزمن أو حسمن في العربية الممسوحة، ولا يدخل طهر أو غسل من خارج الرسم."),
    gap("aed-v1.0:110220", "حسق", "OPEN-CANDIDATE", "knife لا يطابق حسق أو حشق وحصق في العربية الممسوحة، ولا يدخل سكين أو قطع من خارج الجذر.", zero=FEM_T),
    terminal("aed-v1.0:110430", "∅", "OUT-OF-SCOPE", "المدخل اسم كاهن أو رتبة كهنوتية مخصوصة وموسوم بالشك؛ اللقب الثقافي لا يصدر جذرا عربيا من وظيفة الكاهن."),
    gap("aed-v1.0:110900", "حكحك", "SOURCE-GAP", "AED لا يقدم إلا noun/Substantiv بين معقوفين؛ لا شيء أو حدث محكوم يقارن بحكحك."),
    gap("aed-v1.0:111370", "حتف", "OPEN-CANDIDATE", "peace/happiness لا يطابق حتف في الموت ولا حطب وحطف، ولا يدخل سلم أو سعادة من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:113710", "خرو", "OPEN-CANDIDATE", "animal hide/leather لا يطابق خرو أو خلو في العربية الممسوحة، ولا يدخل جلد أو فرو من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:113880", "خابب", "OPEN-CANDIDATE", "slayers/fighters لا يطابق خابب أو خلبب وخربب في العربية الممسوحة، ولا يدخل قتل أو قتال من خارج الرسم."),
    gap("aed-v1.0:114310", "خاز", "SOURCE-GAP", "creek/runnel كلاهما موسوم بالشك، والألمانية لا تثبت إلا بركة ماء عامة؛ لا مجرى مائي واحد محكوم يقارن بخاز.", zero=NOM_W),
    gap("aed-v1.0:115780", "خبز", "OPEN-CANDIDATE", "tail لا يطابق خبز في الطعام والعجن والسوق الشديد، ولا يدخل ذنب أو ذيل من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:116090", "خفي", "SOURCE-GAP", "AED لا يقدم إلا noun/Substantiv بين معقوفين بلا مرجع معجمي؛ لا شيء أو حدث محكوم يقارن بخفي.", zero=FEM_T),
    gap("aed-v1.0:116300", "خبر", "OPEN-CANDIDATE", "mode of being/form/transformation لا يطابق خبر في العلم والنبأ والاختبار، ولا يدخل هيئة أو تحول من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:117700", "خني", "OPEN-CANDIDATE", "music makers/dancing musicians لا يطابق خني في العربية الممسوحة، ولا يدخل غناء أو رقص من خارج الرسم.", zero=FEM_T),
    gap("aed-v1.0:118270", "خنمس", "SOURCE-GAP", "AED لا يسمي إلا a kind of beer بين معقوفين بلا مادة أو صنف فاصل؛ لا شراب معين محكوم يقارن بخنمس."),
    gap("aed-v1.0:118530", "خنرف", "DIRECTION-GAP", "insult/abuse موسوم Sem. loan word بلا مانح سامي فردي أو طريق انتقال، ولا يثبت في خنرف مقابل عربي عامل.", orbit="المصرية تسمي الإهانة أو السب، لكن المانح الفردي والمسار والمعنى العربي باقية غير محكومة."),
    terminal("aed-v1.0:119030", "∅", "OUT-OF-SCOPE", "what is in front تعبير إحالي عام لما يقع أمام الشيء؛ الوظيفة المكانية لا تصدر جذرا معجميا مستقلا."),
    terminal("aed-v1.0:119090", "∅", "OUT-OF-SCOPE", "crocodile as Seth تسمية ثقافية لحيوان بوصفه الإله ست؛ اللقب الديني لا يصدر جذرا عربيا من التمساح أو التقدم."),
    gap("aed-v1.0:119400", "خنتش", "OPEN-CANDIDATE", "joy لا يطابق خنتش أو خنطش في العربية الممسوحة، ولا يدخل فرح أو سرور من خارج الرسم."),
    gap("aed-v1.0:119540", "خند", "OPEN-CANDIDATE", "seat/stool/chair/throne أو stairway لا يطابق خند في العربية الممسوحة، ولا يدخل كرسي أو درج من خارج الجذر.", zero=NOM_W),
    gap("aed-v1.0:120210", "خرب", "OPEN-CANDIDATE", "levy paid as cattle لا يطابق خرب في الفساد ولا خرف وخلف، ولا يدخل ضريبة أو ماشية من خارج الجذر.", zero=FEM_T),
    gap("aed-v1.0:120670", "خسر", "SOURCE-GAP", "AED لا يسمي إلا جزءا من شجرة غير معينة يستعمل طبيا؛ لا نبات أو جزء واحد محكوم يقارن بخسر.", zero=NOM_W),
    gap("aed-v1.0:120880", "خسف", "TOOL-GAP", "punishment يطابق الخسف في الإذلال وتحميل الإنسان ما يكره، والصوت كامل، لكن الحدث المجمد لخسف هو انخراق القاع أو الباطن الذي يقوم عليه الشيء لا فعل العقوبة أو الإكراه.", sound="ḫ↔خ في IDN-17 وs↔س في IDN-07 وf↔ف في IDN-06؛ الجذر كامل بعد عزل تاء التأنيث.", orbit="الخسف الإذلال وتحميل الإنسان ما يكره، وهو مدار punishment مباشرة؛ بقي الحدث المجمد الأضيق مانعا.", keywords="الخسف|الإذلال|تحميل الإنسان ما يكره|الظلم|ذلا", zero=FEM_T),
    gap("aed-v1.0:121000", "خسف", "SOURCE-GAP", "AED لا يسمي إلا double part of a ship بين معقوفين بلا موضع أو وظيفة؛ لا يرث جزء السفينة حكم عضو العقوبة أو مرض العين.", zero=NOM_W),
    gap("aed-v1.0:121070", "خست", "SOURCE-GAP", "AED لا يسمي إلا a sacred dog بين معقوفين بلا نوع أو دور، ولا يكفي الوصف الديني لتعيين حيوان معجمي يقارن بخست.", zero=FEM_T),
    terminal("aed-v1.0:121320", "∅", "COMPOUND-BOUNDARY", "الرسم `ḫt-ꜥꜣ` ذو حدين، والمرجع نفسه يتردد بين طائر مأكول وبط ودواجن عامة؛ حد المركب يمنع حمله على جذر مفرد."),
    gap("aed-v1.0:121630", "ختي", "SOURCE-GAP", "AED لا يسمي إلا a kind of measurement بين معقوفين، والألمانية تصفه بنسب أبعاد بناء بلا وحدة معينة؛ لا قياس محكوم يقارن بختي.", zero=NOM_W),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT
assert {item.state for item in DECISIONS} <= LEGAL_CLOSURES
assert {item.verdict for item in DECISIONS} <= LEGAL_CLOSURES

OUTSIDE_FAN = {"aed-v1.0:104560"}

WITNESS_NOTES = {
    "aed-v1.0:104560": "أثبت كتاب العين وأساس البلاغة حفد في الإسراع والخفة؛ بقي climb/fly أخص من السرعة وبقيت i̯ في عضو `verb_4-inf` بلا صفر صرفي محكوم.",
    "aed-v1.0:109940": "أثبت الصحاح أن حسب الشيء هو عده، وأثبت المفردات أن الحساب استعمال العدد؛ اكتمل مدار accounting/reckoning والحدث والصوت.",
    "aed-v1.0:120880": "أثبت الصحاح والمحكم الخسف في الإذلال وتحميل الإنسان ما يكره؛ اكتمل مدار punishment والصوت، وبقي حدث الجذر المجمد أضيق منه.",
}


def round41_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R40.round40_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND40-COMPLETION", "ROUND41-COMPLETION")
    card = card.replace(
        "ROUND41-COMPLETION (2026-08-27)",
        "ROUND41-COMPLETION (2026-08-28)",
    )
    card = card.replace(
        f"round40-egyptian-rank={rank}/{CARD_COUNT}",
        f"round41-egyptian-rank={rank}/{CARD_COUNT}",
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
        raise SystemExit("Round-forty-one marker already exists; append refused.")

    aramaic_exact, _ = R9.load_entries("aramaic")
    aramaic_queue = R9.select_aramaic(aramaic_text, aramaic_exact)
    assert not aramaic_queue, (
        "Aramaic short live-open queue is no longer exhausted: "
        f"{[item['entry_id'] for item in aramaic_queue[:10]]}"
    )

    egyptian_exact, _ = R9.load_entries("egyptian")
    queue = (
        R40.R39.R38.R37.R36.R35.R34.R33.R32.R31.R30.R29
        .select_egyptian_fast(egyptian_text, egyptian_exact)
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
        round41_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الحادية والأربعون: استمرار المخزون المصري المسجل المفتوح (2026-08-28)", "",
        (
            "أعيد فحص الآرامية أولا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرا، فسجل الانتقال المسمى `{TRANSITION}`. انتقيت ثمانين "
            "بطاقة مصرية بدءا من `WO-C-OPEN-COMP-02543` بقصر الهيكل ثم موضع "
            "اللقطة. استبعد صف ḏ المؤجل. في كل بطاقة عرضت إصابات AED كلها بلا "
            "حد، وكتب وسم الطريق والرسم والمدخل المختار، وحفظ الاختلاف "
            "والمتجانسات بلا محو. فحصت حالة الإغلاق والحكم آليا على القائمة "
            "القانونية وحدها في `data/closure-vocabulary.json`."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-02543 إلى WO-C-OPEN-COMP-02582", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-02583 إلى WO-C-OPEN-COMP-02622", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([
                f"<!-- LANE-C-R41-EGYPTIAN-CHUNK-{rank:03d}:END -->", "",
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
        "## الجولة الحادية والأربعون: المسار C، الساميات والمصرية (2026-08-28)", "",
        f"- الوقت: {now}.",
        "- أعيد فحص الساميات أولا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-02543` إلى `WO-C-OPEN-COMP-02582`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-02583` إلى `WO-C-OPEN-COMP-02622`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طبق الانضباط الثلاثي: كل موجب له صوت موقع وحدث مجمد ومدار مكتوب؛ وكل بطاقة أخرى لها عائق شريف مسمى.",
        "- قاموس الإغلاق المغلق وحده مطبق: كل حالات الإغلاق والأحكام اجتازت القائمة القانونية في `data/closure-vocabulary.json`.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ الموجب مقصور على العضو ومداره المكتوب.",
        "- الموجب: `ḥsb.w↔حسب` في الحساب والعد بعد عزل اللاحقة الاسمية .w؛ حكمه `ROOT-TRACE` مقصور على العضو.",
        "- بقي `ḫsf.t↔خسف` في العقوبة `TOOL-GAP`: ثبت الخسف في الإذلال وتحميل المكروه وتم الصوت، لكن الحدث المجمد يسجل انخراق القاع لا فعل العقوبة.",
        "- بقي `ḥfdi̯↔حفد` `MORPHOLOGY-GAP`: ثبت حفد في الإسراع والخفة لا climb/fly، وبقيت i̯ في عضو `verb_4-inf` بلا صفر صرفي محكوم.",
        "- المراجع النباتية والطبية والحيوانية والأدوات الموسومة بين معقوفين أو بعلامة سؤال بقيت `SOURCE-GAP`؛ لم يحسم التخمين نوع الشيء بالقوة.",
        "- وسم القرض السامي العام في `ḫnrf` بقي `DIRECTION-GAP` بلا مانح فردي أو طريق نقل مكتمل.",
        "- العبارات متعددة الحدود أغلقت `COMPOUND-BOUNDARY`، والألقاب والصفات الإحالية الثقافية أغلقت `OUT-OF-SCOPE`، وصف ḏ المصري المؤجل بقي مستبعدا.",
        "- لم يحدث شحن أو إيداع أو إعداد مرحلي، ولم يستعمل git أو تحدث مشتقات النشر.", "",
        f"LANE-C DONE41 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
            R40.R39.R38.R37.R36.R35.R34.R33.R32.R31.R30.R29.R28.R27
            .R26.R25.R24.R23.R20.R10.append
        )
        append(EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian)
        append(REPORT, f"{MARKER}:REPORT", report)
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
