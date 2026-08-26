#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 31 completion cards without shipping or git.

The live short Aramaic queue is checked before the registered Egyptian open
queue continues. The script completes WO-C-OPEN-COMP-01743..01822 in two
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

import harvest_lane_c_round30 as R30


R9 = R30.R9
AR = R30.AR
ROOT = R30.ROOT
ARAMAIC = R30.ARAMAIC
EGYPTIAN = R30.EGYPTIAN
REPORT = R30.REPORT

MARKER = "LANE-C-ROUND31-2026-08-26"
FIRST_SERIAL = 1743
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)
LEGAL_CLOSURES = R30.LEGAL_CLOSURES


def gap(member_id: str, candidate: str, state: str, reason: str,
        sound: str = "المروحة بنيوية فقط؛ لا يرقى التشابه إلى قانون أو نسب.",
        orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
        keywords: str = "", zero: str = "") -> R9.Decision:
    return R30.gap(
        member_id, candidate, state, reason, sound, orbit, keywords, zero,
    )


# No positive is issued in this window. Close semantic contacts remain named
# gaps when a sound row, morphology, or transfer direction is incomplete.
# Uncertain and unnamed AED referents remain source gaps.
DECISIONS: tuple[R9.Decision, ...] = (
    gap("aed-v1.0:158910", "شدح", "OPEN-CANDIDATE", "sweet wine لا يطابق شدح أو شضح أو سدح أو سضح؛ ولم تحمل مادة المشدح أو الانشداح اسم خمر أو شراب."),
    gap("aed-v1.0:159010", "قاو", "OPEN-CANDIDATE", "height/length/loudness لا يطابق قاو أو قلو أو قرو؛ ولا تحمل القوة أو القول معنى الارتفاع والطول وشدة الصوت معا."),
    gap("aed-v1.0:159230", "قما", "OPEN-CANDIDATE", "flour لا يطابق قما أو قمر ولا بقية المروحة؛ والقمح حب لا دقيق ولا يقع في المسار الصامتي للعضو."),
    gap("aed-v1.0:159370", "قار", "OPEN-CANDIDATE", "sack/bundle لا يطابق قار في القار أو القرار؛ ولا يدخل جوالق أو كيس من خارج الرسم."),
    gap("aed-v1.0:159470", "قوس", "TOOL-GAP", "القوس هي آلة bow، أما qꜣs ففعل bind/string ويتسع إلى تقييد الضحية؛ لا تسوى الآلة بالفعل ولا يثبت ꜣ↔و.", sound="q↔ق في IDN-12 وs↔س في IDN-07؛ ꜣ المصرية بإزاء و العربية بلا صف مصري موقع.", orbit="القوس هي آلة الرمي نفسها التي توتر، فتلتقي بعبارة string a bow، لكن العربية تسمي الآلة والمصرية الفعل الأعم.", keywords="القوس|أقواس|تقوس|انعطف"),
    gap("aed-v1.0:159980", "قور", "OPEN-CANDIDATE", "barge/cargo boat لا يطابق قور في القطع المدور أو السعة، ولا يدخل سفينة أو مركب من خارج الرسم."),
    gap("aed-v1.0:160590", "قما", "OPEN-CANDIDATE", "form/appearance/nature لا يطابق قما أو قمر في المروحة، ولا يدخل هيئة أو صورة من خارج الرسم."),
    gap("aed-v1.0:161070", "قنو", "OPEN-CANDIDATE", "the many لا يساوي القنو أو القنوان بوصفه عذق تمر، ولا يحول اجتماع الحبات إلى اسم الكثرة العام."),
    gap("aed-v1.0:161170", "قني", "OPEN-CANDIDATE", "embrace لا يطابق قني في الكسب والاقتناء، ولا يجعل الحيازة ضم الذراعين."),
    gap("aed-v1.0:161690", "قرف", "OPEN-CANDIDATE", "contract/draw together لا يطابق قرف في القشر والاقتراف والتهمة، ولا يجعل نزع القشرة انقباضا."),
    gap("aed-v1.0:161790", "قرر", "SOURCE-GAP", "AED لا يعين إلا boat بين الأقواس؛ لا نوع مركب أو وظيفة مسماة يقوم عليها مدار عربي."),
    gap("aed-v1.0:162490", "قدر", "MORPHOLOGY-GAP", "القدر والمقدار يثبتان القياس، وهو مدار وحدة الوزن kite، لكن عزل .t يترك q-d بإزاء ق-d-r ولا يفسر الراء العربية.", sound="q↔ق في IDN-12 وd↔د في IDN-09؛ الراء العربية الثالثة بلا حامل مصري بعد عزل .t.", orbit="القدر مبلغ الشيء والمقدار قدره؛ وهو مدار measure of weight، وبقيت بنية الجذر العربي أوسع بصامت أصلي.", keywords="القدر|المقدار|مبلغ الشيء|القياس", zero="عزلت .t علامة التأنيث الاسمية المسجلة؛ بقي q-d بإزاء ق-d-r من غير تعرية تفسر الراء."),
    gap("aed-v1.0:162570", "قدب", "OPEN-CANDIDATE", "lease/pacht لا يطابق قدب أو قضب، ولا يدخل أجر أو كرى من خارج الرسم."),
    gap("aed-v1.0:162990", "كوي", "OPEN-CANDIDATE", "الكوة فتحة عامة في البناء، ولا تساوي vagina/vulva عضوا تشريحيا؛ والكي حرق لا صلة له بالعضو."),
    gap("aed-v1.0:163300", "كاب", "OPEN-CANDIDATE", "censer لا يطابق كاب أو كاف ولا كلب أو كرب، ولا يدخل مبخرة أو مجمرة من خارج الرسم."),
    gap("aed-v1.0:163380", "كاب", "OPEN-CANDIDATE", "royal nursery كمؤسسة لتعليم النخبة لا يطابق كاب أو كاف أو كرب، ولا يدخل كتاب أو مدرسة من خارج الرسم."),
    gap("aed-v1.0:164000", "كبس", "SOURCE-GAP", "الشجرة المقدسة غير مسماة وكل التعريف بين أقواس التحرير؛ لا ينتخب نوع شجر عربي من كبس أو كبش."),
    gap("aed-v1.0:164080", "كفت", "SOURCE-GAP", "AED يتردد بين trustworthiness وصفة إيجابية وبين revelation، وكلها موسومة بالشك؛ لا معنى مفردا محسوما للمقارنة."),
    gap("aed-v1.0:164220", "كفع", "OPEN-CANDIDATE", "plunder/capture لا يطابق كفع أو كفض أو كفغ، ولا يدخل نهب أو أسر من خارج الرسم."),
    gap("aed-v1.0:164311", "حمم", "LAW-GAP", "الحمم والفحم والسواد يطابق black/dark مباشرة، لكن k المصرية بإزاء ح العربية بلا صف مصري موقع.", sound="m↔م في IDN-02 في الموضعين الثاني والثالث؛ k↔ح هي الرجل المصرية غير الموقعة.", orbit="الحمم الرماد والفحم المحترق، والأحم الأسود؛ وهو مدار black/dark مباشرة، وبقي الصوت الأول مانعا.", keywords="الحمم|الفحم|الأسود|السواد"),
    gap("aed-v1.0:164610", "كمو", "SOURCE-GAP", "المادة الطبية غير مسماة ويتردد AED بين جزء نبات ومعدن؛ لا مادة واحدة يقوم عليها المدار."),
    gap("aed-v1.0:165050", "كري", "DIRECTION-GAP", "وسم Sem. loan word في prison لا يسمي لغة مانحة أو طريق انتقال، ولا ينتخب كري مادة عربية للسجن."),
    gap("aed-v1.0:165100", "كرس", "OPEN-CANDIDATE", "تكرس الشيء تراكم وتلازب، لكنه لا يسمي sack أو وعاء الحزمة؛ لا يسوى المحتوى المتراكم بوعائه."),
    gap("aed-v1.0:165450", "كسو", "OPEN-CANDIDATE", "bowing/obeisance لا يطابق كسو في اللباس والتغطية، ولا يدخل ركع أو سجد من خارج الرسم."),
    gap("aed-v1.0:165970", "كسو", "DIRECTION-GAP", "الكسوة لباس فتطابق garment، لكن وسم Sem. loan word لا يسمي مانحا، وṯ↔س بلا صف مصري موقع بعد عزل .t.", sound="k↔ك في IDN-13؛ ṯ↔س غير موقع مصريا، و.t علامة تأنيث لا تحمل واو الجذر العربية.", orbit="الكسوة اللباس، وهو معنى garment مباشرة؛ بقي طريق النقل والبنية الصوتية غير محكومين.", keywords="الكسوة|اللباس|كسوته|ألبسته", zero="عزلت .t علامة تأنيث اسمية؛ لم يجعل ذلك k-ṯ جذر كسو بواوه الأصلية."),
    gap("aed-v1.0:166150", "جاي", "OPEN-CANDIDATE", "moisten في سياق ترطيب قلم البردي لا يطابق جاي أو غاي ولا صور اللام والراء، ولا يدخل رطب أو بل من خارج الرسم."),
    gap("aed-v1.0:166910", "جبا", "OPEN-CANDIDATE", "side/wall of a room لا يطابق جبا أو جبر ولا قبا أو غبا، ولا يدخل جنب أو جدار بصوامت زائدة."),
    gap("aed-v1.0:167180", "غمي", "LAW-GAP", "أغمي على فلان يطابق daze وفقد الوعي، لكن g↔غ وw↔ي بلا صفين مصريين موقعين، وweakness أوسع.", sound="m↔م في IDN-02؛ g↔غ وw↔ي هما الرجلان المصريتان غير الموقعتين لهذا العضو.", orbit="أغمي على فلان أي غشي عليه وظن أنه مات؛ وهو مدار daze مباشرة، ولا يعم كل weakness.", keywords="أغمي على فلان|غشي عليه|ظن أنه مات"),
    gap("aed-v1.0:167460", "قنو", "SOURCE-GAP", "نوع الطائر نفسه غير محسوم وgolden oriole اقتراح بين الأقواس؛ لا ينتخب اسم طائر عربي من جنو أو قنو أو غنو."),
    gap("aed-v1.0:167640", "جنح", "LAW-GAP", "جناح الطائر يطابق wing مباشرة، لكن ẖ المصرية بإزاء ح العربية بلا صف مصري موقع.", sound="g↔ج في IDN-08 وn↔ن في IDN-03؛ ẖ↔ح هي الرجل المصرية غير الموقعة.", orbit="جناح الطائر يده وما يطير به؛ وهو معنى wing نفسه، وبقي الصوت الثالث مانعا.", keywords="جناح الطائر|يده|أجنحة"),
    gap("aed-v1.0:167840", "جلب", "SOURCE-GAP", "قطعة اللباس أو النسيج غير مسماة وكل التعريف بين أقواس؛ لا يرفع قرب جلباب أو جلب قبل تعيين الثوب."),
    gap("aed-v1.0:168020", "جرج", "OPEN-CANDIDATE", "equipment لا يطابق جرج أو قرق أو غرق ولا صور اللام، ولا يدخل عدة أو جهاز من خارج الرسم."),
    gap("aed-v1.0:168070", "جرج", "SOURCE-GAP", "الإنجليزية تسمي seed grain والألمانية تتردد بين نبات وvegetation؛ لا مرجع نباتي واحد محسوما للعضو."),
    gap("aed-v1.0:168310", "جست", "OPEN-CANDIDATE", "run/course لا يطابق جست أو قسط أو غسط ولا النوى الأقصر، ولا يدخل جري أو سير من خارج الرسم."),
    gap("aed-v1.0:169480", "تلف", "OPEN-CANDIDATE", "kiln/potter oven لا يطابق تلف أو طرف ولا نظائر الطاء، ولا يدخل أتون أو تنور من خارج الرسم."),
    gap("aed-v1.0:169670", "تيت", "OPEN-CANDIDATE", "pestle لا يطابق تيت أو طيت ولا صور الهمزة، ولا يدخل مدق أو هاون من خارج الرسم."),
    gap("aed-v1.0:169890", "تيا", "OPEN-CANDIDATE", "cry out/moan/scream/jubilate لا يطابق تيا أو تيل أو تير ولا نظائر الطاء، ولا يدخل صاح أو عوى من خارج الرسم."),
    gap("aed-v1.0:169960", "تيو", "SOURCE-GAP", "النبات الطبي غير مسمى؛ لا ينتخب اسم نبات عربي من تيو أو طيو أو صور الهمزة."),
    gap("aed-v1.0:170180", "طول", "OPEN-CANDIDATE", "الطول صفة امتداد لا اسم pillar أو عمود؛ ولا يكفي كون العمود طويلا لإثبات مدار معجمي واحد."),
    gap("aed-v1.0:170320", "تور", "SOURCE-GAP", "النبات القصبي نفسه غير مسمى وكل التعريف بين أقواس؛ لا ينتخب نوع نبات عربي من تور أو طول."),
    gap("aed-v1.0:170490", "تمم", "LAW-GAP", "تم الشيء وكمل يطابق complete، لكن twt المصرية بإزاء t-m-m تحتاج رجلين مصريتين غير موقعتين.", sound="t الأولى↔ت في IDN-11؛ w↔م وt الأخيرة↔م بلا صفين مصريين موقعين.", orbit="تم الشيء أي كمل، والتمام ضد النقص؛ وهو مدار complete مباشرة، وبقي الصوت مانعا.", keywords="تم الشيء|كمل|التمام|ضد النقص"),
    gap("aed-v1.0:170610", "ثوب", "LAW-GAP", "الثواب والمثوبة يطابقان payment/reward، لكن عزل .t يترك t-b بإزاء ث-w-b، ولا يثبت t↔ث أو الواو العربية.", sound="b↔ب في IDN-05؛ t↔ث بلا صف مصري لهذا الموضع، والواو العربية بلا حامل بعد عزل .t.", orbit="المثوبة هي الثواب والجزاء؛ وهو معنى reward مباشرة، وبقيت البنية الصوتية مانعة.", keywords="المثوبة|الثواب|الجزاء|الأجر", zero="عزلت .t علامة التأنيث الاسمية؛ بقي t-b بإزاء ث-w-b مع واو عربية أصلية غير مفسرة."),
    gap("aed-v1.0:170760", "تبس", "OPEN-CANDIDATE", "prick/pierce لا يطابق تبس أو تبش أو تبص ولا نظائر الطاء، ولا يدخل وخز أو ثقب من خارج الرسم."),
    gap("aed-v1.0:171450", "تبي", "OPEN-CANDIDATE", "being upon/having authority over لا يطابق تبي أو تفي ولا نظائر الطاء، ولا يدخل علا أو ولي من خارج الرسم."),
    gap("aed-v1.0:171490", "تبي", "OPEN-CANDIDATE", "logs/large timbers لا يطابق تبي أو تفي ولا طب أو طف، ولا يدخل خشب أو جذوع من خارج الرسم."),
    gap("aed-v1.0:171850", "تفن", "OPEN-CANDIDATE", "joy لا يطابق تفن في الوسخ أو الطرد ولا طفن، ولا يدخل فرح أو طرب من خارج الرسم."),
    gap("aed-v1.0:172160", "تما", "OPEN-CANDIDATE", "sack لا يطابق تما أو تمر ولا طما أو طمر، ولا يدخل كيس أو جوالق من خارج الرسم."),
    gap("aed-v1.0:172440", "ثني", "LAW-GAP", "الثني من الدواب ما بلغ سنا تعرف بإلقاء ثنيته، فيلتقي external signs of age، لكن t↔ث وj↔ي غير موقعين مصريا.", sound="n↔ن في IDN-03؛ t↔ث وj↔ي هما الرجلان المصريتان غير الموقعتين لهذا العضو.", orbit="الثني ما ألقى ثنيته وبلغ مرحلة عمر مسماة بالعلامة الظاهرة في الأسنان؛ وهو مدار signs of age، وبقي الصوت مانعا.", keywords="الثني|ألقى ثنيته|السنة|العمر"),
    gap("aed-v1.0:172560", "تنم", "OPEN-CANDIDATE", "dirt لا يطابق تنم الذي تسمي معاجمه شجرة التنوم ولا طنم، ولا يدخل وسخ من خارج الرسم."),
    gap("aed-v1.0:172850", "تنور", "DIRECTION-GAP", "التنور فرن الخباز فيطابق oven، لكن وسم Sem. loan word لا يسمي مانحا فرديا، وبنية trr لا تحمل n-w بلا تحليل نقل.", sound="t↔ت في IDN-11 وr الأخيرة↔ر في IDN-01؛ n-w العربية والتكرار المصري لا يجتمعان في مسار مصري موقع.", orbit="التنور الموقد الذي يخبز فيه، وهو oven of the baker مباشرة؛ بقي المانح وطريق النقل والبنية الصوتية مفتوحة.", keywords="التنور|الفرن|يخبز|الموقد"),
    gap("aed-v1.0:172970", "ثخن", "LAW-GAP", "ثخن الدواء أي غلظ يطابق concentration/thickening، لكن th-b-w المصرية بإزاء ث-خ-ن لا تحمل إلا الثاء وتفقد رجلين.", sound="th↔ث يمر بالصف BR-EGYP-03؛ b↔خ وw↔ن بلا صفين مصريين موقعين.", orbit="ثخن الشيء غلظ، وهو مدار Eindickung للدواء مباشرة، وبقي معظم المسار الصوتي ناقصا.", keywords="ثخن|غلظ|ثخانة|الدواء"),
    gap("aed-v1.0:173210", "تخب", "OPEN-CANDIDATE", "dip/moisten/irrigate لا يطابق تخب أو طخب في العربية الممسوحة، ولا يدخل غمس أو رطب أو سقى من خارج الرسم."),
    gap("aed-v1.0:173250", "تخن", "OPEN-CANDIDATE", "ibis لا يجد في تخن أو طخن اسما لطائر أبي منجل عاملا."),
    gap("aed-v1.0:173350", "تخس", "OPEN-CANDIDATE", "butcher/slaughter لا يطابق تخس أو تخش أو تخص ولا نظائر الطاء، ولا يدخل ذبح أو نحر من خارج الرسم."),
    gap("aed-v1.0:173500", "تشي", "SOURCE-GAP", "نوع الحجر نفسه غير مسمى وكل التعريف بين أقواس؛ لا ينتخب اسم حجر عربي من تشي أو تسي ونظائرهما."),
    gap("aed-v1.0:173740", "دكك", "LAW-GAP", "دك الشيء ضربه وكسره يلتقي attack/injure، لكن t المصرية بإزاء د العربية بلا صف مصري موقع.", sound="k↔ك في IDN-13 في الموضعين الثاني والثالث؛ t↔د هي الرجل المصرية غير الموقعة.", orbit="دك الشيء أي ضربه وكسره حتى سواه؛ وهو مدار attack/injure في الضرب والإيذاء، وبقي الصوت الأول مانعا.", keywords="الدك|الدق|ضربه|كسره"),
    gap("aed-v1.0:174130", "ثاو", "OPEN-CANDIDATE", "fan-shaped palm leaves لا يطابق ثاو أو ثرو ولا نظائر التاء والطاء، ولا يدخل سعف أو خوص من خارج الرسم."),
    gap("aed-v1.0:174290", "ثاي", "OPEN-CANDIDATE", "reproach/fault لا يطابق ثاي أو ثلي أو ثري ولا نظائر التاء والطاء، ولا يدخل لوم أو عيب من خارج الرسم."),
    gap("aed-v1.0:174460", "ثاو", "OPEN-CANDIDATE", "collection of writings/book collection لا يطابق ثاو أو ثرو ولا نظائر التاء والطاء، ولا يدخل كتاب أو سفر من خارج الرسم."),
    gap("aed-v1.0:174600", "لثم", "LAW-GAP", "اللثام غطاء الفم والستر يلتقي cloak/swaddling/bandages، لكن ṯ-ꜣ-m بإزاء ل-ث-m يحتاج صامتا زائدا وقلبا بلا مسار موقع.", sound="m↔م في IDN-02؛ اللام العربية بلا حامل، وṯ-ꜣ لا تنتظمان بإزاء ل-ث في صف مصري موقع.", orbit="اللثام ما ستر الفم وما حوله، وهو غطاء ولفاف قريب من cloak/bandage، وبقيت البنية الصوتية مانعة.", keywords="اللثام|ستر الفم|الغطاء|تلثم"),
    gap("aed-v1.0:174820", "ثيس", "SOURCE-GAP", "فعل إعداد عجين الجعة نفسه مشكوك، والألمانية تتردد بين التفتيت ونحوه؛ لا حدث واحدا محسوما للمقارنة."),
    gap("aed-v1.0:175010", "ثوب", "LAW-GAP", "الثواب والمثوبة يطابقان reward، وṯ↔ث وw↔و موقعان، لكن n المصرية بإزاء ب العربية بلا صف.", sound="ṯ↔ث في BR-EGYP-03 وw↔و في IDN-10؛ n↔ب هي الرجل المصرية غير الموقعة.", orbit="المثوبة هي الثواب والجزاء؛ وهو مدار reward مباشرة، وبقي الصامت الأخير مانعا.", keywords="المثوبة|الثواب|الجزاء|الأجر"),
    gap("aed-v1.0:175120", "ثبو", "OPEN-CANDIDATE", "sole/sandals لا يطابق ثبو أو تبو أو طبو؛ والثوب لباس البدن لا نعل القدم ولا باطنها."),
    gap("aed-v1.0:175290", "ثبق", "DIRECTION-GAP", "وسم Sem. loan word في barracks لا يسمي لغة مانحة أو طريق انتقال، ولا ينتخب ثبق أو تفق أو طبق اسما للثكنة."),
    gap("aed-v1.0:175540", "طمس", "OPEN-CANDIDATE", "red/ruddy لا يطابق طمس في المحو ولا تمس أو ثمس، ولا يدخل حمر أو أدم من خارج الرسم."),
    gap("aed-v1.0:175830", "ثني", "LAW-GAP", "ثنى الشيء جعله اثنين والاثنان من العدد، فيلتقي number/quantity من باب العد، لكن w↔ي غير موقع مصريا والمعنى العربي أخص.", sound="ṯ↔ث في BR-EGYP-03 وn↔ن في IDN-03؛ w↔ي هي الرجل المصرية غير الموقعة.", orbit="التثنية جعل الواحد اثنين، والاثنان اسم عدد؛ وهو داخل مدار number لا مساواة لكل quantity، وبقي الصوت مانعا.", keywords="جعله اثنين|الاثنان|العدد|التثنية"),
    gap("aed-v1.0:175900", "ثنف", "SOURCE-GAP", "الإنجليزية تقترح مادة لصنع kyphi والألمانية وزنا للحبوب في الوصفات؛ اختلاف المادة والمقياس يمنع مدار عضو واحدا."),
    gap("aed-v1.0:175960", "ثنم", "SOURCE-GAP", "vat موسومة بالشك، والألمانية تتردد بين kettle وpit؛ لا وعاء أو حفرة واحدة محكومة يقوم عليها المدار."),
    gap("aed-v1.0:176250", "ثرت", "OPEN-CANDIDATE", "willow اسم نوع نبات محدد لا يطابق ثرت أو تلت أو طرت، ولا يدخل صفصاف من خارج الرسم."),
    gap("aed-v1.0:176360", "طرب", "OPEN-CANDIDATE", "الطرب خفة لشدة حزن أو سرور، ولا يساوي stumble/totter من السكر؛ الأثر النفسي ليس حركة التعثر."),
    gap("aed-v1.0:176440", "ثرت", "OPEN-CANDIDATE", "skiff/scow لا يطابق ثرت أو ترت أو طرت ولا صور اللام، ولا يدخل زورق أو سفينة من خارج الرسم."),
    gap("aed-v1.0:176530", "ثحو", "OPEN-CANDIDATE", "joy لا يطابق ثحو أو تحو أو طحو، ولا يدخل فرح أو سرور من خارج الرسم."),
    gap("aed-v1.0:176740", "ثحح", "OPEN-CANDIDATE", "exult/rejoice لا يطابق ثحح أو تحح أو طحح، ولا يدخل فرح أو هلل من خارج الرسم."),
    gap("aed-v1.0:177040", "ثزت", "SOURCE-GAP", "الإنجليزية تسمي صورة عدو معدة للإتلاف، والألمانية تسمي الخراب أو الإهلاك؛ اختلاف الشيء والحدث يمنع مدار عضو واحدا."),
    gap("aed-v1.0:177740", "دار", "OPEN-CANDIDATE", "control/suppress لا يطابق دار في الدوران ولا ضار في الضرر، ولا يجعل الإدارة الحديثة سندا لمعنى مصري قديم."),
    gap("aed-v1.0:178280", "دبي", "OPEN-CANDIDATE", "hippopotamus لا يطابق دبي أو ضبي؛ والدب والضب حيوانان آخران فلا تورث فئة الحيوان اسما لوحيد النهر."),
    gap("aed-v1.0:178370", "دبر", "OPEN-CANDIDATE", "fall down لا يطابق دبر في الخلف أو الإدبار ولا ضبر، ولا يدخل سقط من خارج الرسم."),
    gap("aed-v1.0:178580", "دبن", "OPEN-CANDIDATE", "round-topped wooden box لا يطابق الدبن بوصفه حظيرة غنم أو لقمة، ولا يدخل صندوق من خارج الرسم."),
    gap("aed-v1.0:179020", "دبت", "OPEN-CANDIDATE", "taste لا يطابق دبت أو دفت ولا نظائر الضاد، ولا يدخل ذوق أو طعم من خارج الرسم."),
    gap("aed-v1.0:179060", "دبو", "OPEN-CANDIDATE", "boat العام لا يطابق دبو أو دفو ولا نظائر الضاد، ولا يدخل سفينة أو مركب من خارج الرسم."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT
assert {item.state for item in DECISIONS} <= LEGAL_CLOSURES
assert {item.verdict for item in DECISIONS} <= LEGAL_CLOSURES

OUTSIDE_FAN = {
    "aed-v1.0:159470", "aed-v1.0:162490", "aed-v1.0:164311",
    "aed-v1.0:165970", "aed-v1.0:170490", "aed-v1.0:170610",
    "aed-v1.0:172440", "aed-v1.0:172850", "aed-v1.0:172970",
    "aed-v1.0:173740", "aed-v1.0:174600", "aed-v1.0:175010",
}

WITNESS_NOTES = {
    "aed-v1.0:159470": "أثبتت المعاجم القوس وآلة الرمي وتقوس الشيء؛ ثبت تماس string a bow، وبقي فرق الآلة والفعل وꜣ↔و مانعين.",
    "aed-v1.0:162490": "أثبت كتاب العين أن القدر مبلغ الشيء وأن الأشياء مقادير؛ ثبت مدار القياس، وبقيت راء قدر بلا حامل بعد عزل .t.",
    "aed-v1.0:164311": "أثبت الصحاح ولسان العرب الحمم والفحم والأسود والأحم؛ ثبت مدار black/dark، وبقي k↔ح بلا صف مصري موقع.",
    "aed-v1.0:165970": "قال كتاب العين إن الكسوة اللباس وإن كسوته أي ألبسته؛ ثبت معنى garment، وبقي المانح والصوت والصرف مفتوحة.",
    "aed-v1.0:167180": "قال كتاب العين: «أغمي على فلان» إذا ظن أنه مات ثم رجع؛ ثبت مدار daze، وبقي g↔غ وw↔ي بلا صفين مصريين.",
    "aed-v1.0:167640": "قال الصحاح: «جناح الطائر: يده»، وأثبت لسان العرب الجناح والأجنحة؛ ثبت معنى wing، وبقي ẖ↔ح بلا صف مصري.",
    "aed-v1.0:170490": "أثبتت المعاجم تم الشيء بمعنى كمل والتمام ضد النقص؛ ثبت معنى complete، وبقي w-t↔m-m بلا مسار.",
    "aed-v1.0:170610": "أثبت كتاب العين والصحاح أن المثوبة هي الثواب والجزاء؛ ثبت معنى reward، وبقي t-b↔ث-w-b غير مكتمل بعد عزل .t.",
    "aed-v1.0:172440": "أثبتت المعاجم الثني الذي ألقى ثنيته ودخل سنا مسماة؛ ثبتت علامة العمر الظاهرة، وبقي t↔ث وj↔ي بلا صفين مصريين.",
    "aed-v1.0:172850": "لم يرده ماسح الجذور لأنه لفظ رباعي معرب؛ وقرأ جرد المصادر في data/alawlaqi-prior-attempts.json نقل الجمهرة والمصباح والتاج أن التنور موقد الخبز؛ ثبت معنى oven، وبقي المانح الفردي وبنية trr↔تنور مفتوحين.",
    "aed-v1.0:172970": "أثبتت المعاجم ثخن الشيء بمعنى غلظ؛ ثبت مدار concentration، وبقي b-w↔خ-n بلا صفين مصريين.",
    "aed-v1.0:173740": "قال الصحاح: «الدك: الدق» وفسره بضرب الشيء وكسره حتى يسوى؛ ثبت تماس attack/injure، وبقي t↔د بلا صف مصري.",
    "aed-v1.0:174600": "أثبتت المعاجم اللثام غطاء الفم والتلثم بالستر؛ ثبت تماس الغطاء واللفاف، وبقي ترتيب الصوامت وبنيتها مانعين.",
    "aed-v1.0:175010": "أثبتت المعاجم المثوبة والثواب والجزاء؛ ثبت معنى reward، وبقي n↔ب بلا صف مصري موقع.",
    "aed-v1.0:175830": "أثبتت المعاجم أن ثنى الشيء جعله اثنين وأن الاثنين من العدد؛ ثبت تماس العد، وبقي w↔ي والمعنى العام مانعين.",
}


def round31_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R30.round30_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND30-COMPLETION", "ROUND31-COMPLETION")
    card = card.replace(
        f"round30-egyptian-rank={rank}/{CARD_COUNT}",
        f"round31-egyptian-rank={rank}/{CARD_COUNT}",
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
        raise SystemExit("Round-thirty-one marker already exists; append refused.")

    aramaic_exact, _ = R9.load_entries("aramaic")
    aramaic_queue = R9.select_aramaic(aramaic_text, aramaic_exact)
    assert not aramaic_queue, (
        "Aramaic short live-open queue is no longer exhausted: "
        f"{[item['entry_id'] for item in aramaic_queue[:10]]}"
    )

    egyptian_exact, _ = R9.load_entries("egyptian")
    queue = R30.R29.select_egyptian_fast(egyptian_text, egyptian_exact)
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
        round31_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الحادية والثلاثون: استمرار المخزون المصري المسجل المفتوح (2026-08-26)", "",
        (
            "أعيد فحص الآرامية أولا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرا، فسجل الانتقال المسمى `{TRANSITION}`. انتقيت ثمانين "
            "بطاقة مصرية بدءا من `WO-C-OPEN-COMP-01743` بقصر الهيكل ثم موضع "
            "اللقطة. استبعد صف ḏ المؤجل. في كل بطاقة عرضت إصابات AED كلها بلا "
            "حد، وكتب وسم الطريق والرسم والمدخل المختار، وحفظ الاختلاف "
            "والمتجانسات بلا محو. فحصت حالة الإغلاق والحكم آليا على القائمة "
            "القانونية وحدها في `data/closure-vocabulary.json`."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-01743 إلى WO-C-OPEN-COMP-01782", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-01783 إلى WO-C-OPEN-COMP-01822", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([
                f"<!-- LANE-C-R31-EGYPTIAN-CHUNK-{rank:03d}:END -->", "",
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
        "## الجولة الحادية والثلاثون: المسار C، الساميات والمصرية (2026-08-26)", "",
        f"- الوقت: {now}.",
        "- أعيد فحص الساميات أولا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01743` إلى `WO-C-OPEN-COMP-01782`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01783` إلى `WO-C-OPEN-COMP-01822`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طبق الانضباط الثلاثي: لم يصدر موجب في هذه النافذة؛ وكل بطاقة لها عائق شريف مسمى.",
        "- قاموس الإغلاق المغلق وحده مطبق: كل حالات الإغلاق والأحكام اجتازت القائمة القانونية في `data/closure-vocabulary.json`.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ لا حكم موجب جديد.",
        "- المطابقات الدلالية المرفوعة بقيت فجوات قانون: `kmm↔حمم` للسواد، و`gm.w↔غمي` للإغماء، و`gnẖ↔جنح` للجناح، و`twt↔تمم` للكمال، و`tkk↔دكك` للضرب والكسر.",
        "- `qd.t↔قدر` بقي `MORPHOLOGY-GAP` لبقاء الراء بعد عزل .t، و`qꜣs↔قوس` بقي `TOOL-GAP` لفصل آلة القوس عن فعل التوتير والتقييد.",
        "- موضعا الثواب في `tb.t` و`ṯwn` وموضع العدد في `ṯnw` بقيت فجوات قانون، ولم تعوض الدلالة صفا صوتيا ناقصا.",
        "- أوسمة القرض السامي العامة في `krj` و`kṯ.t` و`trr` و`ṯpg` بقيت `DIRECTION-GAP` بلا مانح فردي أو طريق مكتمل.",
        "- الألفاظ والمراجع المشكوكة أو غير المسماة بقيت `SOURCE-GAP`، وصف ḏ المصري المؤجل بقي مستبعدا.",
        "- لم يحدث شحن أو إيداع أو إعداد مرحلي، ولم يستعمل git أو تحدث مشتقات النشر.", "",
        f"LANE-C DONE31 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
        R30.R29.R28.R27.R26.R25.R24.R23.R20.R10.append(
            EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian,
        )
        R30.R29.R28.R27.R26.R25.R24.R23.R20.R10.append(
            REPORT, f"{MARKER}:REPORT", report,
        )
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
