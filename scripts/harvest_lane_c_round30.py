#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 30 completion cards without shipping or git.

The live short Aramaic queue is checked before the registered Egyptian open
queue continues. The script completes WO-C-OPEN-COMP-01663..01742 in two
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

import harvest_lane_c_round29 as R29


R9 = R29.R9
AR = R29.AR
ROOT = R29.ROOT
ARAMAIC = R29.ARAMAIC
EGYPTIAN = R29.EGYPTIAN
REPORT = R29.REPORT

MARKER = "LANE-C-ROUND30-2026-08-26"
FIRST_SERIAL = 1663
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)
LEGAL_CLOSURES = R29.LEGAL_CLOSURES


def gap(member_id: str, candidate: str, state: str, reason: str,
        sound: str = "المروحة بنيوية فقط؛ لا يرقى التشابه إلى قانون أو نسب.",
        orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
        keywords: str = "", zero: str = "") -> R9.Decision:
    return R29.gap(
        member_id, candidate, state, reason, sound, orbit, keywords, zero,
    )


def terminal(member_id: str, candidate: str, verdict: str, reason: str,
             zero: str = "") -> R9.Decision:
    return R29.terminal(member_id, candidate, verdict, reason, zero)


# No positive is issued in this window. Direct semantic contacts remain named
# gaps when a sound row, morphology, tool/event relation, or transfer direction
# is incomplete. Uncertain and unnamed AED referents remain source gaps.
DECISIONS: tuple[R9.Decision, ...] = (
    gap("aed-v1.0:133960", "سفت", "OPEN-CANDIDATE", "sacrifice لا يطابق حواس سفت أو زفت في العربية، ولا يكفي سياق القربان لرفع متجانس إلى نسب."),
    gap("aed-v1.0:134180", "زمل", "LAW-GAP", "زمله بمعنى أردفه وعادله يلتقي unite/join في الجمع والمصاحبة، لكن ꜣ المصرية بإزاء ل العربية بلا صف فردي موقع.", sound="z↔ز وm↔م هويتان ظاهرتان؛ ꜣ↔ل هي الرجل المصرية غير الموقعة.", orbit="زمله أي أردفه وعادله، والزميل الرفيق؛ وهو مدار الجمع والمصاحبة القريب من unite/join، وبقي الصوت مانعا.", keywords="زمله|أردفه|عادله|الزميل|الرفيق"),
    gap("aed-v1.0:134820", "سمي", "OPEN-CANDIDATE", "report/complain لا يطابق سمي ولا حواس الاسم والسمو، ولا يدخل شكا أو أخبر من خارج الرسم."),
    gap("aed-v1.0:134930", "سمي", "OPEN-CANDIDATE", "whips لا يطابق سمي ولا يجد في المروحة اسما للسياط عاملا."),
    gap("aed-v1.0:135120", "سمن", "OPEN-CANDIDATE", "mainstay/confirmation لا يطابق سمن أو زمن، ولا يحول الثبات العام إلى مادة عربية من الهيكل."),
    gap("aed-v1.0:135190", "سمن", "SOURCE-GAP", "المرض غير مسمى في AED؛ لا ينتخب اسم علة عربية من سمن أو زمن قبل تعيين المرجع."),
    gap("aed-v1.0:135440", "سمر", "OPEN-CANDIDATE", "cause pain لا يطابق سمر أو زمر، ولا يدخل ألم أو أوجع من خارج الرسم."),
    gap("aed-v1.0:135660", "سنن", "LAW-GAP", "seniority يلتقي سن الرجل بمعنى كبر وأسن، لكن s-m-s المصرية بإزاء س-n-n تحتاج رجلين مصريتين غير موقعتين.", sound="s الأولى↔س هوية؛ m↔ن وs الأخيرة↔ن لا يثبتان في مسار مصري فردي موقع.", orbit="أسن الرجل أي كبر، والسن مقدار العمر؛ وهو مدار seniority مباشرة، وبقي الصوت مانعا.", keywords="أسن الرجل|كبر|السن|العمر"),
    gap("aed-v1.0:136150", "سنت", "OPEN-CANDIDATE", "اسم لعبة senet لا يطابق سنت أو زنت دلالة معجمية عربية، ولا يستخرج اسم لعبة من التشابه الاسمي وحده."),
    gap("aed-v1.0:136270", "سنن", "MORPHOLOGY-GAP", "المسن حجر يحدد به ويصقل، وهو مدار polishing stone مباشرة، لكن مضاعفة النون العربية لا تحملها بنية sn.t بعد عزل التأنيث.", sound="s↔س وn↔ن هويتان؛ النون العربية الثانية بلا حامل مصري في العضو.", orbit="المسن حجر يسن عليه الحديد، وسن السكين أحدها وصقلها؛ وهو الأداة المصرية نفسها.", keywords="المسن|حجر|سن السكين|أحدها|الصقل", zero="عزلت .t علامة تأنيث اسمية؛ بقي s-n بإزاء س-n-n مع مضاعفة عربية غير مفسرة."),
    gap("aed-v1.0:137040", "سنب", "OPEN-CANDIDATE", "air/breath لا يطابق سنب أو زنب، ولا يدخل نفس أو هواء من خارج الرسم."),
    gap("aed-v1.0:137400", "سنم", "OPEN-CANDIDATE", "feed/consume food لا يطابق سنم أو زنم، ولا يحمل السنام معنى الإطعام أو الأكل."),
    gap("aed-v1.0:137570", "سنن", "OPEN-CANDIDATE", "copy/document/record لا يطابق سنن في معنى الطريق أو الطريقة، ولا يدخل نسخ أو كتب بقلب غير مرخص."),
    gap("aed-v1.0:138290", "سنن", "LAW-GAP", "سن فلانا بمعنى مدحه وأطراه يطابق praise، لكن q المصرية بلا مقابل والنون العربية المضاعفة بلا حامل مصري كامل.", sound="s↔س وn↔ن هويتان؛ q المصرية غير محمولة والنون العربية الثانية غير مفسرة.", orbit="سن فلانا أي مدحه وأطراه؛ وهو مدار praise مباشرة، وبقي اكتمال الصوت مانعا.", keywords="سن فلانا|مدحه|أطراه"),
    gap("aed-v1.0:139090", "سرت", "OPEN-CANDIDATE", "grey goose لا يجد في سرت أو زرت أو شرط اسما للإوزة الرمادية عاملا."),
    gap("aed-v1.0:139670", "صرخ", "OPEN-CANDIDATE", "memorial/Denkstein لا يطابق صرخ أو سرخ، ولا يكفي الذكر أو الإعلان المفترض لإثبات اسم حجر تذكاري."),
    gap("aed-v1.0:139830", "سرق", "SOURCE-GAP", "النبات غير مسمى وRaps اقتراح بين الأقواس؛ لا ينتخب اسم نبات عربي من سرق أو زرق."),
    gap("aed-v1.0:140160", "شرت", "SOURCE-GAP", "المعدن الطبي نفسه غير مسمى، والألمانية تتردد بين كهرمان أخضر وصمغ السنط؛ لا مادة واحدة يقوم عليها المدار."),
    gap("aed-v1.0:140560", "سحو", "OPEN-CANDIDATE", "grouping/assembly لا يطابق سحو أو زحو، ولا يدخل جمع أو حشد من خارج الرسم."),
    gap("aed-v1.0:140780", "شحن", "LAW-GAP", "شحن المتاع أي ملأه وحمله يلتقي provide/equip في التزويد والتحميل، لكن s المصرية بإزاء ش العربية بلا صف فردي موقع، وcommand لا يطابق.", sound="ḥ↔ح وn↔ن هويتان؛ s↔ش هي الرجل المصرية غير الموقعة.", orbit="شحن المتاع أي ملأه وحمله وجهزه؛ يلتقي provide/equip في التزويد، ولا يغطي command، وبقي الصوت مانعا.", keywords="شحن المتاع|ملأه|حمله|جهزه"),
    gap("aed-v1.0:140860", "شحن", "OPEN-CANDIDATE", "crown/adorn لا يطابق شحن في الملء والتحميل، ولا يدخل توج أو زين من خارج الرسم."),
    gap("aed-v1.0:141470", "سخت", "SOURCE-GAP", "نوع خبز القربان غير مسمى؛ لا ينتخب اسم خبز عربي من سخت أو سخط أو شخت."),
    gap("aed-v1.0:141620", "سخا", "OPEN-CANDIDATE", "call to mind/remember لا يطابق سخا أو سخر، ولا يدخل ذكر من خارج الرسم."),
    gap("aed-v1.0:142140", "سخم", "OPEN-CANDIDATE", "divine power/divine image لا يطابق سخم أو شخم، ولا يحول القوة أو الصورة الإلهية إلى جذر من الهيكل."),
    gap("aed-v1.0:142220", "سخم", "OPEN-CANDIDATE", "اسم subdivision of a phyle لا يطابق سخم أو شخم، ولا يستخرج اسم جماعة إدارية من الرسم وحده."),
    gap("aed-v1.0:142450", "سخن", "SOURCE-GAP", "الإنجليزية تعطي unite والألمانية occur؛ اختلاف الحدثين يمنع مدار عضو واحدا قبل المقارنة العربية."),
    gap("aed-v1.0:142540", "سخن", "SOURCE-GAP", "المرجع يتردد بين swelling وgathering وكلاهما مشكوك؛ لا مدار واحدا محسوما لمادة سخن."),
    gap("aed-v1.0:142800", "سخر", "OPEN-CANDIDATE", "plan/condition/nature/conduct لا يطابق سخر في التسخير والهزء، ولا تختزل الحزمة الدلالية في جذر عربي واحد."),
    gap("aed-v1.0:143100", "سخت", "SOURCE-GAP", "ambushing وmilitary storm كلاهما موسوم بالشك ومختلفان؛ لا حدث واحدا محسوما للمقارنة."),
    gap("aed-v1.0:143410", "سخي", "OPEN-CANDIDATE", "deaf person لا يطابق سخي أو زخي، ولا يدخل أصم من خارج الرسم."),
    gap("aed-v1.0:143480", "سحب", "OPEN-CANDIDATE", "swallow liquid/quaff لا يطابق سحب في الجر والجذب، ولا يدخل شرب أو جرع من خارج الرسم."),
    gap("aed-v1.0:143980", "سسف", "SOURCE-GAP", "قطعة اللباس أو النسيج غير مسماة؛ لا ينتخب اسم ثوب عربي من سسف أو سزف."),
    gap("aed-v1.0:144080", "سسن", "OPEN-CANDIDATE", "breathe/smell لا يطابق سسن أو زسن، ولا يدخل شم أو نفس من خارج الرسم."),
    gap("aed-v1.0:144840", "سشب", "OPEN-CANDIDATE", "polisher لا يجد في سشب أو زشب اسما للصاقل أو أداة الصقل عاملا."),
    gap("aed-v1.0:145060", "سشم", "OPEN-CANDIDATE", "swab لا يطابق سشم أو زشم، ولا يدخل ممسحة من خارج الرسم."),
    gap("aed-v1.0:145600", "سشش", "OPEN-CANDIDATE", "tear out papyrus لا يطابق سشش أو زشش، ولا يدخل نزع من خارج الرسم."),
    gap("aed-v1.0:145870", "سشد", "OPEN-CANDIDATE", "adorn with a fillet لا يطابق سشد أو زشد، ولا يدخل عصب أو زين من خارج الرسم."),
    gap("aed-v1.0:146610", "سكك", "TOOL-GAP", "السكة حديدة تحرث بها الأرض فتطابق آلة plough، أما skꜣ فحدث plough/cultivate؛ لا يسوى الحدث بأداته ولا تفسر ꜣ مضاعفة الكاف.", sound="s↔س وk↔ك هويتان؛ ꜣ المصرية بإزاء الكاف العربية الثانية بلا صف موقع.", orbit="السكة الحديدة التي تحرث بها الأرض؛ المدار الزراعي مباشر، لكن العربية تسمي الأداة والمصرية تسمي الحدث.", keywords="السكة|حديدة|تحرث بها الأرض|المحراث"),
    gap("aed-v1.0:146690", "سكي", "SOURCE-GAP", "أداة المرحاض نفسها غير محسومة، والألمانية تقترح straw swab؛ لا أداة واحدة مسماة للمقارنة."),
    gap("aed-v1.0:146840", "سكن", "OPEN-CANDIDATE", "greedy لا يطابق سكن في القرار والهدوء، ولا يدخل شره من خارج الرسم."),
    gap("aed-v1.0:147890", "ستو", "OPEN-CANDIDATE", "arrow/dart/spear لا يجد في ستو أو شتو اسما للسهم أو الرمح عاملا."),
    gap("aed-v1.0:148310", "ستم", "OPEN-CANDIDATE", "destroy لا يطابق ستم أو شتم، ولا يجعل الشتم هلاكا ماديا."),
    gap("aed-v1.0:148380", "ستر", "OPEN-CANDIDATE", "green plants لا يطابق ستر في الإخفاء والغطاء، ولا يكفي غطاء النبات لإثبات اسم الخضرة."),
    gap("aed-v1.0:148600", "ستت", "SOURCE-GAP", "نوع جرة الجعة ووحدة السعة غير محسمين؛ لا إناء أو مقياس عربي مسمى ينتخب من ستت."),
    gap("aed-v1.0:148660", "ستت", "OPEN-CANDIDATE", "censing لا يطابق ستت أو شتت، ولا يدخل بخر أو جمر من خارج الرسم."),
    gap("aed-v1.0:148750", "ستر", "OPEN-CANDIDATE", "passage/cavern/ramp لا يطابق ستر في الإخفاء، ولا ينتخب سردابا أو ممرا من خارج الرسم."),
    gap("aed-v1.0:149220", "ستن", "SOURCE-GAP", "AED لا يثبت إلا noun بلا معنى معجمي؛ لا مدار لمادة ستن قبل تعيين المرجع."),
    gap("aed-v1.0:149760", "سدب", "SOURCE-GAP", "قطعة اللباس نفسها غير مسماة وموسومة بالشك؛ لا ينتخب اسم ثوب عربي من سدب أو ستب."),
    gap("aed-v1.0:150020", "صدق", "OPEN-CANDIDATE", "hidden things لا تطابق صدق في الصحة والوفاء، ولا يحول الخفاء إلى سر من خارج الرسم."),
    gap("aed-v1.0:151300", "شاء", "OPEN-CANDIDATE", "destiny/good fortune لا يساوي شاء بمعنى أراد؛ الصلة المفهومية بين المشيئة والمصير لا تثبت اسما معجميا واحدا."),
    terminal("aed-v1.0:151470", "∅", "OUT-OF-SCOPE", "until أداة غاية وظيفية بلا مادة معجمية مستقلة قابلة لحكم النسب."),
    gap("aed-v1.0:152150", "شاد", "OPEN-CANDIDATE", "dig/dig out لا يطابق شاد في الرفع والبناء، ولا يدخل حفر من خارج الرسم."),
    gap("aed-v1.0:152310", "شعت", "OPEN-CANDIDATE", "knife لا يجد في شعت أو شغت أو سعت اسما للسكين عاملا."),
    gap("aed-v1.0:152480", "شعو", "SOURCE-GAP", "المشروب غير مسمى؛ لا ينتخب اسم شراب عربي من شعو أو شغو أو سعو."),
    gap("aed-v1.0:152550", "شعر", "DIRECTION-GAP", "وسم Sem. loan word لا يسمي لغة مانحة أو طريق انتقال، والحواس calculation/scheme/threat/promise لا تنتخب مادة عربية واحدة."),
    gap("aed-v1.0:152830", "شوت", "OPEN-CANDIDATE", "feather/plumage لا يطابق شوت أو شوط، ولا يدخل ريش من خارج الرسم."),
    gap("aed-v1.0:152940", "شوو", "SOURCE-GAP", "الإنجليزية تقترح خضارا مأكولا والألمانية تبنا أو عشب قصب جافا؛ اختلاف النباتين يمنع مدار عضو واحدا."),
    gap("aed-v1.0:153250", "شبت", "OPEN-CANDIDATE", "value/price/wage لا يطابق شبت أو سبت، ولا يدخل ثمن أو أجر من خارج الرسم."),
    gap("aed-v1.0:153300", "شبت", "SOURCE-GAP", "الأداة الطقسية المقدمة للإلهات غير مسماة؛ لا ينتخب اسم شيء عربي من شبت أو سبت."),
    gap("aed-v1.0:153430", "شوب", "LAW-GAP", "شاب الشيء بمعنى خلطه يطابق mix/mash، لكن b المصرية الوسطى بإزاء و العربية بلا صف فردي موقع.", sound="š↔ش وb الأخيرة↔ب هويتان؛ b الوسطى↔و هي الرجل المصرية غير الموقعة.", orbit="الشوب الخلط، وشاب الشيء خلطه؛ وهو مدار mix/mash مباشرة، وبقي الصوت مانعا.", keywords="الشوب|الخلط|شاب الشيء|خلطه"),
    gap("aed-v1.0:153490", "شبن", "OPEN-CANDIDATE", "mix/mingle لا يطابق شبن في الحواس العربية الممسوحة، ولا يسقط النون لإدخال شوب."),
    gap("aed-v1.0:153710", "سفن", "SOURCE-GAP", "النبات غير مسمى وpoppy اقتراح بين الأقواس؛ لا ينتخب اسم نبات عربي من شبن أو سفن."),
    gap("aed-v1.0:153810", "شبس", "OPEN-CANDIDATE", "tomb-chapel/gravestone لا يطابق شبس أو شفس، ولا يدخل قبر أو شاهد من خارج الرسم."),
    gap("aed-v1.0:154060", "شفو", "SOURCE-GAP", "المادة الطبية غير مسماة، والألمانية تتردد بين مخاط وجزء من الجعة؛ لا مادة واحدة يقوم عليها المدار."),
    gap("aed-v1.0:154450", "شمو", "OPEN-CANDIDATE", "movements/gait لا يطابق شمو أو سمو، ولا يجعل السمو حركة مشي مخصوصة."),
    gap("aed-v1.0:154720", "شمع", "OPEN-CANDIDATE", "spare/slender لا يطابق شمع في المادة أو السمع، ولا يدخل نحيل من خارج الرسم."),
    gap("aed-v1.0:154910", "حمم", "LAW-GAP", "حم الماء بمعنى سخن يطابق heat، لكن š المصرية بإزاء ح العربية بلا صف فردي موقع.", sound="m↔م مع المضاعفة محفوظ؛ š↔ح هي الرجل المصرية غير الموقعة.", orbit="حم الماء أي سخن، والحمى حرارة؛ وهو مدار heat مباشرة، وبقي الصوت مانعا.", keywords="حم الماء|سخن|الحمى|الحرارة"),
    gap("aed-v1.0:155360", "شنو", "OPEN-CANDIDATE", "troubles/illness/sorrow/need لا يطابق شنو أو سنو، ولا تختزل الحزمة في جذر عربي واحد."),
    gap("aed-v1.0:155530", "شنء", "OPEN-CANDIDATE", "rotten fish/stench لا يطابق شنأ بمعنى أبغض؛ النفرة من الرائحة أثر لا مدار معجميا واحدا."),
    gap("aed-v1.0:155720", "شنع", "OPEN-CANDIDATE", "enemy لا يطابق شنع في القبح والفظاعة، ولا يحول وصف العدو إلى اسم العداوة."),
    gap("aed-v1.0:156030", "شنب", "OPEN-CANDIDATE", "trumpet/tube for kohl لا يطابق شنب في الشارب، ولا يكفي الشكل الأنبوبي لإثبات عضو واحد."),
    gap("aed-v1.0:156230", "شنس", "SOURCE-GAP", "نوع المخبوزات أو الكعك غير مسمى؛ لا ينتخب اسم طعام عربي من شنس أو سنس."),
    gap("aed-v1.0:156670", "شري", "OPEN-CANDIDATE", "stop/block up لا يطابق شري أو سري، ولا يدخل سد أو حبس من خارج الرسم."),
    gap("aed-v1.0:156860", "سرح", "LAW-GAP", "سرح السيل إذا جرى جريا سهلا يلتقي brook/stream في جريان الماء، لكن š المصرية بإزاء س العربية بلا صف فردي موقع.", sound="r↔ر وḥ↔ح هويتان؛ š↔س هي الرجل المصرية غير الموقعة.", orbit="سرح السيل أي جرى جريا سهلا، فهو سيل سارح؛ وهو مدار stream الجاري مباشرة، وبقي الصوت مانعا.", keywords="سرح السيل|جرى|جريا سهلا|سيل سارح"),
    gap("aed-v1.0:157470", "شسم", "SOURCE-GAP", "الإنجليزية تقترح leather scroll والألمانية leather whip؛ اختلاف الشيئين يمنع مدار عضو واحدا."),
    gap("aed-v1.0:157580", "شسر", "OPEN-CANDIDATE", "slay لا يطابق شسر أو شسل، ولا يدخل ذبح أو قتل من خارج الرسم."),
    gap("aed-v1.0:157820", "شقب", "OPEN-CANDIDATE", "rhinoceros لا يجد في شقب أو شغب أو سقب اسما لوحيد القرن عاملا."),
    gap("aed-v1.0:157880", "شكر", "OPEN-CANDIDATE", "basket لا يطابق شكر أو شكل، ولا يدخل سلة أو قفة من خارج الرسم."),
    gap("aed-v1.0:158420", "شتت", "SOURCE-GAP", "workboard أو board to cut off كلاهما موسوم بالشك؛ لا وظيفة أداة محققة يقوم عليها المدار."),
    gap("aed-v1.0:158770", "شدي", "OPEN-CANDIDATE", "ditch/military trench لا يطابق شدي أو شذى، ولا يدخل خندق من خارج الرسم."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT
assert {item.state for item in DECISIONS} <= LEGAL_CLOSURES
assert {item.verdict for item in DECISIONS} <= LEGAL_CLOSURES

OUTSIDE_FAN = {
    "aed-v1.0:135660", "aed-v1.0:138290",
    "aed-v1.0:146610", "aed-v1.0:153430",
    "aed-v1.0:154910",
}

WITNESS_NOTES = {
    "aed-v1.0:134180": "قال لسان العرب: «زمله: أردفه وعادله» وذكر الزميل بمعنى الرفيق؛ وأثبت تاج العروس الزملة في الجماعة. بقي ꜣ↔ل بلا صف مصري موقع.",
    "aed-v1.0:135660": "أثبت لسان العرب وتاج العروس أسن الرجل بمعنى كبر، والسن في العمر. بقي s-m-s↔س-n-n بلا مسار مصري كامل موقع.",
    "aed-v1.0:136270": "قال لسان العرب في المسن إنه الحجر الذي يسن عليه الحديد، وأثبت تاج العروس سن السكين في الإحداد والصقل. بقيت مضاعفة النون بعد عزل .t.",
    "aed-v1.0:138290": "أثبتت المعاجم في سن فلانا معنى مدحه وأطراه. بقيت q المصرية والنون العربية الثانية بلا حمل صوتي كامل.",
    "aed-v1.0:140780": "أثبت لسان العرب وتاج العروس شحن المتاع في ملئه وحمله وتجهيزه. بقي s↔ش بلا صف مصري موقع، ولم يطابق معنى command.",
    "aed-v1.0:146610": "قال لسان العرب وتاج العروس إن السكة حديدة تحرث بها الأرض. ثبت مدار الحرث، لكن العربية تسمي الأداة والمصرية الحدث، وبقي ꜣ↔ك غير موقع.",
    "aed-v1.0:153430": "قال لسان العرب: «الشوب: الخلط» و«شاب الشيء: خلطه»؛ وأثبت تاج العروس المعنى نفسه. بقي b↔و الوسطى بلا صف مصري موقع.",
    "aed-v1.0:154910": "أثبت لسان العرب وتاج العروس حم الماء بمعنى سخن، والحمى في الحرارة. بقي š↔ح بلا صف مصري موقع، كما في عضوي الأسرة السابقين.",
    "aed-v1.0:156860": "قال تاج العروس: «سرح السيل ... إذا جرى جريا سهلا فهو سيل سارح». ثبت مدار جريان الماء، وبقي š↔س بلا صف مصري موقع.",
}


def round30_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R29.round29_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND29-COMPLETION", "ROUND30-COMPLETION")
    card = card.replace(
        f"round29-egyptian-rank={rank}/{CARD_COUNT}",
        f"round30-egyptian-rank={rank}/{CARD_COUNT}",
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
        raise SystemExit("Round-thirty marker already exists; append refused.")

    aramaic_exact, _ = R9.load_entries("aramaic")
    aramaic_queue = R9.select_aramaic(aramaic_text, aramaic_exact)
    assert not aramaic_queue, (
        "Aramaic short live-open queue is no longer exhausted: "
        f"{[item['entry_id'] for item in aramaic_queue[:10]]}"
    )

    egyptian_exact, _ = R9.load_entries("egyptian")
    queue = R29.select_egyptian_fast(egyptian_text, egyptian_exact)
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
        round30_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الثلاثون: استمرار المخزون المصري المسجل المفتوح (2026-08-26)", "",
        (
            "أعيد فحص الآرامية أولا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرا، فسجل الانتقال المسمى `{TRANSITION}`. انتقيت ثمانين "
            "بطاقة مصرية بدءا من `WO-C-OPEN-COMP-01663` بقصر الهيكل ثم موضع "
            "اللقطة. استبعد صف ḏ المؤجل. في كل بطاقة عرضت إصابات AED كلها بلا "
            "حد، وكتب وسم الطريق والرسم والمدخل المختار، وحفظ الاختلاف "
            "والمتجانسات بلا محو. فحصت حالة الإغلاق والحكم آليا على القائمة "
            "القانونية وحدها في `data/closure-vocabulary.json`."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-01663 إلى WO-C-OPEN-COMP-01702", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-01703 إلى WO-C-OPEN-COMP-01742", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([
                f"<!-- LANE-C-R30-EGYPTIAN-CHUNK-{rank:03d}:END -->", "",
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
        "## الجولة الثلاثون: المسار C، الساميات والمصرية (2026-08-26)", "",
        f"- الوقت: {now}.",
        "- أعيد فحص الساميات أولا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01663` إلى `WO-C-OPEN-COMP-01702`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01703` إلى `WO-C-OPEN-COMP-01742`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طبق الانضباط الثلاثي: لم يصدر موجب في هذه النافذة؛ وكل بطاقة لها عائق شريف مسمى.",
        "- قاموس الإغلاق المغلق وحده مطبق: كل حالات الإغلاق والأحكام اجتازت القائمة القانونية في `data/closure-vocabulary.json`.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ لا حكم موجب جديد.",
        "- المطابقات الدلالية المرفوعة بقيت فجوات قانون: `zmꜣ↔زمل` للجمع والمصاحبة، و`sms↔سنن` للسن، و`snq↔سنن` للمدح، و`sḥn↔شحن` للتزويد، و`šbb↔شوب` للخلط، و`šmm↔حمم` للحرارة، و`šrḥ↔سرح` لجريان الماء.",
        "- `sn.t↔سنن` بقي `MORPHOLOGY-GAP` بعد عزل .t لبقاء المضاعفة العربية، و`skꜣ↔سكك` بقي `TOOL-GAP` لأن العربية تسمي آلة الحرث والمصرية حدثه.",
        "- وسم القرض السامي في `šꜥr` بقي `DIRECTION-GAP` بلا مانح أو طريق فردي؛ والألفاظ والمراجع المشكوكة أو غير المسماة بقيت `SOURCE-GAP`.",
        "- أداة الغاية `šꜣꜥ` أغلقت `OUT-OF-SCOPE`، وصف ḏ المصري المؤجل بقي مستبعدا.",
        "- لم يحدث شحن أو إيداع أو إعداد مرحلي، ولم يستعمل git أو تحدث مشتقات النشر.", "",
        f"LANE-C DONE30 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
        R29.R28.R27.R26.R25.R24.R23.R20.R10.append(
            EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian,
        )
        R29.R28.R27.R26.R25.R24.R23.R20.R10.append(
            REPORT, f"{MARKER}:REPORT", report,
        )
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
