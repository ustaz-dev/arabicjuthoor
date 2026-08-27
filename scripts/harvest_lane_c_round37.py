#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 37 completion cards without shipping or git.

The live short Aramaic queue is checked before the registered Egyptian open
queue continues. The script completes WO-C-OPEN-COMP-02223..02302 in two
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

import harvest_lane_c_round36 as R36


R9 = R36.R9
AR = R36.AR
ROOT = R36.ROOT
ARAMAIC = R36.ARAMAIC
EGYPTIAN = R36.EGYPTIAN
REPORT = R36.REPORT

MARKER = "LANE-C-ROUND37-2026-08-27"
FIRST_SERIAL = 2223
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)
LEGAL_CLOSURES = R36.LEGAL_CLOSURES


def gap(member_id: str, candidate: str, state: str, reason: str,
        sound: str = "المروحة بنيوية فقط؛ لا يرقى التشابه إلى قانون أو نسب.",
        orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
        keywords: str = "", zero: str = "") -> R9.Decision:
    return R36.gap(
        member_id, candidate, state, reason, sound, orbit, keywords, zero,
    )


def pos(member_id: str, candidate: str, verdict: str, keywords: str,
        sound: str, orbit: str, reason: str,
        zero: str = "") -> R9.Decision:
    return R36.R35.pos(
        member_id, candidate, verdict, keywords, sound, orbit, reason, zero,
    )


def terminal(member_id: str, candidate: str, verdict: str, reason: str,
             zero: str = "") -> R9.Decision:
    return R36.R35.terminal(member_id, candidate, verdict, reason, zero)


def caus_gap(member_id: str, candidate: str, state: str, reason: str,
             morphology: str, remainder: str,
             sound: str = "المروحة بنيوية فقط؛ لا يرقى التشابه إلى قانون أو نسب.",
             orbit: str = "لم يثبت مدار مباشر مكتمل الأرجل.",
             keywords: str = "") -> R9.Decision:
    zero = (
        f"عزلت s السابقة السببية المسماة في `{morphology}`؛ بقي "
        f"`{remainder}` كاملا بلا إسقاط صامت جذري."
    )
    return gap(
        member_id, candidate, state, reason, sound, orbit, keywords, zero,
    )


def caus_pos(member_id: str, candidate: str, verdict: str, keywords: str,
             sound: str, orbit: str, reason: str,
             morphology: str, remainder: str) -> R9.Decision:
    zero = (
        f"عزلت s السابقة السببية المسماة في `{morphology}`؛ بقي "
        f"`{remainder}` كاملا بلا إسقاط صامت جذري."
    )
    return pos(
        member_id, candidate, verdict, keywords, sound, orbit, reason, zero,
    )


# The enrichment member sqni is the sole positive. Its named causative
# stripping leaves q-n-j against Arabic q-n-y; acquisition and acquired
# property bound the "enrich" sense, while the "make fat" sense is explicitly
# excluded. Full-sound contacts whose frozen event is wrong remain TOOL-GAP.
# Strong semantic contacts with an unsigned Egyptian leg remain LAW-GAP.
DECISIONS: tuple[R9.Decision, ...] = (
    caus_gap("aed-v1.0:134570", "ماء", "OPEN-CANDIDATE", "make see لا يطابق ماء في السائل ولا بقية صور m-ꜣ-ꜣ في العربية الممسوحة؛ لا يدخل رأى أو بصر من خارج الرسم.", "verb_caus_2-gem", "m-ꜣ-ꜣ"),
    gap("aed-v1.0:135020", "سمعر", "OPEN-CANDIDATE", "cleanse/make fortunate/ankleiden لا يطابق سمعر أو سمعَل وبقية المروحة، ولم يسم AED السابقة s سببية حتى تنزع."),
    caus_gap("aed-v1.0:135360", "منح", "LAW-GAP", "منح الشيء أعطاه يطابق endow، لكن ḫ المصرية بإزاء ح العربية بلا صف مصري موقع، والمقابل خارج سطح المروحة المرخصة.", "verb_caus_3-lit", "m-n-ḫ", sound="m↔م في IDN-02 وn↔ن في IDN-03؛ ḫ↔ح هي الرجل المصرية غير الموقعة.", orbit="المنحة والعطاء يطابقان endow مباشرة؛ بقية معاني التمييز والفعالية والتزيين لا ترث هذا المدار.", keywords="منحه|أعطاه|العطاء|المنحة"),
    caus_gap("aed-v1.0:135940", "متر", "OPEN-CANDIDATE", "examine/make inquiry/bear witness لا يطابق متر في المد والقطع والاضطراب ولا مطر وبقية المروحة، ولا يدخل فحص أو شهادة من خارج الجذر.", "verb_caus_3-lit", "m-t-r"),
    caus_gap("aed-v1.0:136700", "نعم", "LAW-GAP", "نعم الشيء رق ولان يطابق make smooth، لكن ꜥ الثانية المصرية بإزاء م العربية بلا صف موقع، والمقابل خارج سطح المروحة المرخصة.", "verb_caus_3-lit", "n-ꜥ-ꜥ", sound="n↔ن في IDN-03 وꜥ الأولى ↔ع في IDN-15؛ ꜥ الثانية بإزاء م بلا صف مصري موقع.", orbit="النعومة رقة ولين وخلو من الخشونة، وهو مدار make smooth مباشرة؛ معنى الطحن مستقل ولا يرث الحكم.", keywords="نعم|النعومة|رق|لان|الخشن"),
    caus_gap("aed-v1.0:136750", "نور", "LAW-GAP", "النور ضوء يعين على الإبصار فيلامس make see، لكن ꜣ المصرية بإزاء ر العربية بلا صف مصري موقع، كما أن الأداة الضوئية ليست فعل الرؤية نفسه.", "verb_caus_3-lit", "n-w-ꜣ", sound="n↔ن في IDN-03 وw↔و في IDN-10؛ ꜣ↔ر هي الرجل المصرية غير الموقعة.", orbit="النور ضوء ظاهر يعين على الإبصار؛ ثبتت وساطة الرؤية لا مساواة الضوء بفعل see، وبقي الصوت مانعا.", keywords="النور|الضياء|يعين على الإبصار|أضاء|أنار"),
    caus_gap("aed-v1.0:136830", "نور", "TOOL-GAP", "نرت غيري وأنرته بمعنى نفرته يطابقان drive away ويجاوران make tremble، والصوت كامل بعد عزل s، لكن الحدث المجمد لنور مقصور على اللمعان والنفاذ اللطيف لا التنفير.", "verb_caus_3-lit", "n-w-r", sound="n↔ن في IDN-03 وw↔و في IDN-10 وr↔ر في IDN-01؛ الجذر كامل بعد عزل s.", orbit="التنفير إحداث نفور واضطراب يطابق vertreiben ويلامس erbeben lassen؛ بقي الحدث المجمد للضوء مانعا.", keywords="نرت غيري|نفرته|أناره|التنفير|نار"),
    caus_gap("aed-v1.0:136860", "نوخ", "OPEN-CANDIDATE", "boil/burn لا يطابق نوخ أو شوخ وبقية المروحة في العربية الممسوحة، ولا يدخل طبخ أو حرق من خارج الجذر.", "verb_caus_3-lit", "n-w-ḫ"),
    caus_gap("aed-v1.0:137350", "نفر", "OPEN-CANDIDATE", "make beautiful/embellish لا يطابق نفر في الانزعاج والتفرق ولا نفل في العطاء والغنيمة، ولا يدخل حسن أو زين من خارج الجذر.", "verb_caus_3-lit", "n-f-r"),
    caus_gap("aed-v1.0:137530", "نمح", "OPEN-CANDIDATE", "pray/make supplication لا يجد في نمح أو نماح مادة دعاء عربية عاملة، ولا يدخل صلى أو دعا من خارج الجذر.", "verb_caus_3-lit", "n-m-ḥ"),
    gap("aed-v1.0:137660", "زنني", "OPEN-CANDIDATE", "suffer/be distressed لا يطابق زنني أو سنني ولا زنن وسنن في العربية الممسوحة، ولا يدخل ألم أو كرب من خارج الرسم."),
    caus_gap("aed-v1.0:137900", "نحر", "OPEN-CANDIDATE", "frustrate أو make dangerous لا يطابق نحر في الذبح والصدر وأول النهار؛ لا يجعل إبطال السحر أو زيادة الخطر ذبحا.", "verb_caus_3-lit", "n-ḥ-ꜣ"),
    caus_gap("aed-v1.0:137970", "نخن", "OPEN-CANDIDATE", "make young لا يجد في نخن أو نحَن مادة شباب عربية عاملة، ولا يدخل فتى أو صغر من خارج الجذر.", "verb_caus_3-lit", "n-ḫ-n"),
    caus_gap("aed-v1.0:138010", "نخت", "OPEN-CANDIDATE", "make strong/strengthen/enrich لا يطابق نخت أو نخط ولا سنخ وبقية المروحة في العربية الممسوحة، ولا يدخل قوة أو غنى من خارج الجذر.", "verb_caus_3-lit", "n-ḫ-t"),
    caus_gap("aed-v1.0:139510", "رمي", "OPEN-CANDIDATE", "make weep لا يطابق رمي في الإلقاء والقذف ولا لمي وبقية المروحة، ولا يدخل بكى من خارج الجذر.", "verb_caus_3-inf", "r-m-j"),
    caus_gap("aed-v1.0:139760", "رشو", "OPEN-CANDIDATE", "make rejoice لا يطابق رشو في الرشوة والحبل ولا رسو في الثبات، ولا يدخل فرح من خارج الجذر.", "verb_caus_3-inf", "r-š-w"),
    caus_gap("aed-v1.0:140470", "حعع", "OPEN-CANDIDATE", "make glad لا يجد في حعع أو حضض وحغغ وبقية المروحة مادة فرح عربية عاملة، ولا يدخل سرور من خارج الجذر.", "verb_caus_2-gem", "ḥ-ꜥ-ꜥ"),
    caus_gap("aed-v1.0:140530", "حور", "LAW-GAP", "الحور للنقصان والهلكة والرجوع من حال إلى حال يلامس make decay وفساد الحال، لكن ꜣ المصرية بإزاء ر العربية بلا صف مصري موقع.", "verb_caus_3-lit", "ḥ-w-ꜣ", sound="ḥ↔ح في IDN-14 وw↔و في IDN-10؛ ꜣ↔ر هي الرجل المصرية غير الموقعة.", orbit="النقصان بعد الزيادة والهلكة والرجوع من حال جيد إلى رديء يلتقيان decay/desperate؛ بقي الصوت والحدث المجمد الأضيق مانعين.", keywords="الحور|النقصان|الهلكة|فساد|الحور بعد الكور"),
    caus_gap("aed-v1.0:140980", "حري", "OPEN-CANDIDATE", "drive away/exorcise/make distant لا يطابق حري في الاستحقاق والجدارة ولا حلي في الزينة، ولا يدخل طرد أو بعد من خارج الجذر.", "verb_caus_3-inf", "ḥ-r-j"),
    caus_gap("aed-v1.0:141830", "خعي", "OPEN-CANDIDATE", "make appear/appear لا يجد في خعي أو خضي وخغي مادة ظهور عربية عاملة، ولا يدخل بدا أو ظهر من خارج الجذر.", "verb_caus_3-inf", "ḫ-ꜥ-j"),
    caus_gap("aed-v1.0:141970", "خود", "OPEN-CANDIDATE", "make rich لا يطابق خود في الشابة الناعمة ولا خوض في الدخول والمخالطة، ولا يدخل مال أو غنى من خارج الجذر.", "verb_caus_3-lit", "ḫ-w-d"),
    caus_gap("aed-v1.0:141990", "خفي", "TOOL-GAP", "خفى الشيء في بعض المعاجم بمعنى أظهره واستخرجه يلامس bring، والصوت كامل بعد عزل s، لكن الحدث المجمد لخفي هو ضعف الظهور خلف ساتر لا الإحضار أو القيادة.", "verb_caus_3-inf", "ḫ-p-j", sound="ḫ↔خ في IDN-17 وp↔ف في IDN-06 وj↔ي عبر GLD-02؛ الجذر كامل بعد عزل s.", orbit="إظهار الدفين واستخراجه حركة إلى الخارج تلامس bring، لكنها لا تسمي conduct ولا كل إحضار؛ بقي الحدث المجمد مانعا.", keywords="خفى الشيء|أظهره|استخرجه|الخفي"),
    caus_gap("aed-v1.0:142700", "خنش", "OPEN-CANDIDATE", "make stink لا يطابق خنش في بقية المال والشباب ولا خنس في التأخر والاستخفاء، ولا يدخل نتن من خارج الجذر.", "verb_caus_3-lit", "ḫ-n-š"),
    caus_gap("aed-v1.0:143260", "خدي", "OPEN-CANDIDATE", "make sail northwards لا يطابق خدي أو خضي ولا حدي وحضي في العربية الممسوحة، ولا يدخل إبحار أو شمال من خارج الجذر.", "verb_caus_3-inf", "ḫ-d-j"),
    gap("aed-v1.0:143600", "سخنن", "OPEN-CANDIDATE", "make decompose أو cause inflammation لا يطابق سخنن أو شخنن وصخنن وبقية المروحة، وأبقيت s لأن AED يسجل القسم verb بلا تعرية سببية مسماة."),
    caus_gap("aed-v1.0:143690", "خرد", "LAW-GAP", "الخريدة البكر غير الممسوسة تلامس make young، والحدث المجمد يحفظ بقاء الشيء على فطرته، لكن ẖ المصرية بإزاء خ العربية بلا صف مصري موقع.", "verb_caus_3-lit", "ẖ-r-d", sound="r↔ر في IDN-01 وd↔د في IDN-09؛ ẖ↔خ هي الرجل المصرية غير الموقعة.", orbit="البكارة والشباب مرحلتان متجاورتان، وإرجاع الشيء إلى حداثته يلامس حفظ الأصل؛ لا يساوي ذلك كل شاب بالبكر، وبقي الصوت مانعا.", keywords="الخريدة|البكر|لم تمسس|عذراء|جارية"),
    caus_gap("aed-v1.0:143940", "زبط", "OPEN-CANDIDATE", "make laugh لا يطابق زبط أو زبت ولا سبت وسبط في العربية الممسوحة، ولا يدخل ضحك من خارج الجذر.", "verb_caus_3-lit", "z-b-ṯ"),
    caus_gap("aed-v1.0:143970", "صفد", "LAW-GAP", "الصفد للعطاء وأصفده إذا أعطاه مالا يلامسان supply، لكن s المصرية بإزاء ص العربية بلا صف مصري مباشر، والحدث المجمد لصفد مقصور على الشد والوثاق.", "verb_caus_3-lit", "s-p-d", sound="p↔ف في IDN-06 وd↔د في IDN-09؛ s↔ص ليست صفا مصريا موقعا لهذا العضو.", orbit="العطاء وتجهيز المرء بالمال يلامسان supply، لكن make ready أوسع، وبقي الصوت والحدث المجمد للوثاق مانعين.", keywords="الصفد|العطاء|أصفده|أعطاه مالا|وهب"),
    caus_gap("aed-v1.0:145550", "شسر", "OPEN-CANDIDATE", "make wise لا يطابق شسر أو ششر وسشر وبقية صور š-s-ꜣ في العربية الممسوحة، ولا يدخل حكمة أو عقل من خارج الجذر.", "verb_caus_3-lit", "š-s-ꜣ"),
    caus_gap("aed-v1.0:145680", "ستر", "LAW-GAP", "ستر الشيء أخفاه وغطاه يطابق make secret/be secret، لكن š المصرية بإزاء س وꜣ بإزاء ر بلا صفين مصريين موقعين.", "verb_caus_3-lit", "š-t-ꜣ", sound="t↔ت في IDN-11؛ š↔س وꜣ↔ر هما الرجلان المصريتان غير الموقعتين.", orbit="الستر إخفاء الشيء وتغطيته، وهو مدار السر والخفاء مباشرة؛ بقي الصوت وحده مانعا.", keywords="ستر الشيء|أخفاه|غطاه|الستر|استتر"),
    caus_gap("aed-v1.0:145960", "قري", "OPEN-CANDIDATE", "make high/exalt لا يطابق قري في الضيافة والجمع ولا قرء في الوقت والحيض، ولا يدخل علو أو رفع من خارج الجذر.", "verb_caus_3-inf", "q-ꜣ-j"),
    caus_gap("aed-v1.0:146030", "قرع", "OPEN-CANDIDATE", "make pour forth/vomit لا يطابق قرع في الضرب وإصابة القرعة ولا قلع وبقية المروحة، ولا يدخل قاء أو صب من خارج الجذر.", "verb_caus_3-lit", "q-ꜣ-ꜥ"),
    caus_gap("aed-v1.0:146110", "قبح", "OPEN-CANDIDATE", "refresh/give ease لا يطابق قبح في الدمامة ولا يجد معنى إنعاش أو راحة، فلا يقلب التقبيح إرواء أو تيسيرا." , "verb_caus_3-lit", "q-b-ḥ"),
    caus_pos("aed-v1.0:146140", "قني", "ROOT-ECHO", "القنية|قنى المال|اكتسبه|مال|أقنى|أغنى", "q↔ق IDN-12 وn↔ن IDN-03 وj↔ي عبر GLD-02؛ الجذر كامل بعد عزل s.", "قنى المال اكتسبه واتخذه لنفسه، وenrich جعل المرء ذا مال مكتسب؛ مدار الحيازة والغنى مباشر، أما make fat فلا يدخل الحكم.", "الحكم ECHO لعضو الإغناء وحده لأن العربية تسمي اكتساب المال وحيازته لا التسمين، ولا يرثه عضو القوة المتجانس.", "verb_caus_3-inf", "q-n-j"),
    caus_gap("aed-v1.0:146940", "كسي", "OPEN-CANDIDATE", "make bow down لا يطابق كسي في اللباس والكسوة ولا كشي وكصي، ولا يدخل ركوع أو انحناء من خارج الجذر.", "verb_caus_3-inf", "k-s-j"),
    caus_gap("aed-v1.0:147200", "قمح", "OPEN-CANDIDATE", "make see/glimpse لا يطابق قمح في الحب ورفع الرأس ولا جمح وغَمَح، ولا يدخل نظر أو لمح من خارج الجذر.", "verb_caus_3-lit", "g-m-ḥ"),
    caus_gap("aed-v1.0:147220", "جنن", "OPEN-CANDIDATE", "make weak/enfeeble لا يطابق جنن في الستر والجنون ولا قنن وغنن، ولا يدخل وهن أو ضعف من خارج الجذر.", "verb_caus_2-gem", "g-n-n"),
    caus_gap("aed-v1.0:147300", "قرح", "OPEN-CANDIDATE", "pacify/make peaceful/satisfy لا يطابق قرح في الجرح والقروح ولا جرح وبقية المروحة؛ الألم لا يصير سكينة أو رضا.", "verb_caus_3-lit", "g-r-ḥ"),
    caus_gap("aed-v1.0:147970", "توت", "OPEN-CANDIDATE", "make like/make resemble لا يطابق توت في الثمر ولا توط وطوت وبقية المروحة، ولا يدخل شبه أو مثل من خارج الجذر.", "verb_caus_3-lit", "t-w-t"),
    caus_gap("aed-v1.0:148000", "توت", "OPEN-CANDIDATE", "bring something لا يطابق توت أو توط وبقية المروحة، ولا يرث معنى make resemble من متجانسه السابق ولا يدخل أتى من خارج الجذر.", "verb_caus_3-lit", "t-w-t"),
    caus_gap("aed-v1.0:148550", "تكن", "OPEN-CANDIDATE", "make approach لا يجد في تكن أو طكن مادة دنو عربية عاملة، ولا يدخل قرب من خارج الجذر.", "verb_caus_3-lit", "t-k-n"),
    caus_gap("aed-v1.0:149370", "طحن", "OPEN-CANDIDATE", "make bright/dazzling لا يطابق طحن في السحق والدق ولا ثحن وتحن، ولا يجعل بياض الدقيق إضاءة من غير نص.", "verb_caus_3-lit", "ṯ-ḥ-n"),
    caus_gap("aed-v1.0:149720", "ضوء", "LAW-GAP", "الضوء نور وإشراق يلازمان الصباح، لكن d↔ض يحمل سند DENT-06 الاستعاري وꜣ↔ء بلا صف مصري معجمي موقع، كما أن spend the morning ليس فعل الإضاءة.", "verb_caus_3-lit", "d-w-ꜣ", sound="w↔و في IDN-10؛ d↔ض موسوم بسند استعاري، وꜣ↔ء هي الرجل المصرية غير الموقعة.", orbit="الصباح زمن ظهور الضوء، وأضاء بمعنى أنار وأشرق؛ ثبتت مجاورة الزمن والضوء لا اتحاد الفعلين، وبقي الصوت مانعا.", keywords="الضوء|الضياء|أنار|أشرق|أضاء"),
    caus_gap("aed-v1.0:149870", "ضمم", "LAW-GAP", "ضم الشيء إلى الشيء وجمعه يطابق attach/make touch، لكن j المصرية النهائية لا تقابل م العربية المضعفة بصف موقع، والمقابل خارج سطح المروحة.", "verb_caus_3-lit", "d-m-j", sound="d↔ض عبر DENT-06 وm↔م في IDN-02؛ j↔م هي الرجل غير الموقعة ولا يجيز الإدغام إسقاطها.", orbit="الضم قبض الشيء إلى الشيء وإلصاقه به، وهو مدار attach مباشر؛ بقي الصامت النهائي والوسم الاستعاري مانعين.", keywords="ضممت الشيء|انضم|الجمع|قبض الشيء|إلى الشيء"),
    caus_gap("aed-v1.0:149970", "دشر", "OPEN-CANDIDATE", "make red لا يطابق دشر أو ضشر ولا دسر وضرر في العربية الممسوحة، ولا يدخل حمرة من خارج الجذر.", "verb_caus_3-lit", "d-š-r"),
    caus_gap("aed-v1.0:150040", "دجي", "OPEN-CANDIDATE", "make see لا يطابق دجي في الدجى والظلمة ولا دقي ودغي وبقية المروحة؛ الظلام لا يصير إبصارا.", "verb_caus_3-inf", "d-g-j"),
    gap("aed-v1.0:153990", "شفطي", "OPEN-CANDIDATE", "be blown up with air لا يطابق شفطي أو شفتي وسبطي وبقية المروحة في العربية القديمة الممسوحة؛ لم يسقط j النهائي ولم تدخل مادة شفط الحديثة بالقوة."),
    gap("aed-v1.0:156220", "شنرف", "DIRECTION-GAP", "be dishevelled موسوم Sem. loan word بلا مانح سامي فردي أو طريق انتقال، ولا تسمي شنرف أو سنرف هذا الحدث.", orbit="التشعث واضطراب الشعر هو مدار العضو المصري، لكن وسم القرض العام لا يعين مادة عربية أو جهة انتقال."),
    gap("aed-v1.0:163290", "كاوت", "OPEN-CANDIDATE", "carry/support لا يطابق كاوت أو كلوت وكروت ولا الصور الأقصر في العربية الممسوحة، ولا يدخل حمل أو سند من خارج الرسم."),
    gap("aed-v1.0:163570", "كامن", "OPEN-CANDIDATE", "be blind/blind لا يطابق كامن في الاستتار ولا كلمن وكرمن، ولا يدخل كمه أو عمي من خارج الرسم."),
    gap("aed-v1.0:165240", "كاهس", "OPEN-CANDIDATE", "harsh/overbearing لا يطابق كاهس أو كاحس وبقية المروحة الرباعية، ولا يدخل قسو من خارج الرسم."),
    gap("aed-v1.0:167060", "جبجب", "OPEN-CANDIDATE", "be lame لا يطابق جبجب أو قبقب وغمغم في العربية الممسوحة، ولا يدخل عرج من خارج الرسم."),
    gap("aed-v1.0:167370", "غمغم", "OPEN-CANDIDATE", "smash/break/tear لا يطابق غمغم في الصوت غير المبين ولا قمقم وجمجم؛ الصوت أو الوعاء والرأس لا يصير كسرا وتمزيقا."),
    gap("aed-v1.0:171900", "تفنن", "OPEN-CANDIDATE", "rejoice/be glad لا يطابق تفنن في تنويع الفنون والوجوه، ولا يجعل التنوع فرحا."),
    gap("aed-v1.0:173380", "تختخ", "OPEN-CANDIDATE", "flow، ولا سيما امتلاء الضرع وجريان اللبن، لا يطابق تختخ في رخاوة البدن ولا تخطخ، ولا يدخل سيل من خارج الرسم."),
    gap("aed-v1.0:174650", "ترمس", "OPEN-CANDIDATE", "eat/devour لا يطابق ترمس في اسم الحب ولا تلمس وطرمس وبقية المروحة، ولا يدخل أكل من خارج الرسم."),
    gap("aed-v1.0:180050", "دندن", "OPEN-CANDIDATE", "be angry/rage لا يطابق دندن في ترديد الصوت الخفي ولا ضندن؛ الصوت المصاحب للغضب لا يصير الغضب نفسه."),
    caus_gap("aed-v1.0:450163", "شدو", "LAW-GAP", "شدا الإبل ساقها يلامس make leave/remove، لكن j المصرية بإزاء و العربية بلا صف مصري موقع، والمقابل خارج سطح المروحة المرخصة.", "verb_caus_3-inf", "š-d-j", sound="š↔ش في IDN-21 وd↔د في IDN-09؛ j↔و هي الرجل المصرية غير الموقعة.", orbit="سوق الإبل حملها على الانتقال يلامس الإخراج والإبعاد، لكنه لا يساوي كل إزالة؛ بقي الصوت والحدث المجمد لوثاقة شد مانعين.", keywords="شدوت الإبل|سقتها|السوق|شدا"),
    caus_gap("aed-v1.0:550241", "قني", "OPEN-CANDIDATE", "make strong لا يطابق قني في اكتساب المال والاقتناء والرضا؛ لا يرث حكم عضو enrich المتجانس ولا يدخل قوة من خارج الجذر.", "verb_caus_3-inf", "q-n-j"),
    caus_gap("aed-v1.0:650021", "وهي", "LAW-GAP", "وهى الشيء تشقق وضعف وتخرق يطابق break up، لكن ꜣ المصرية بإزاء ي العربية بلا صف مصري موقع، والمقابل خارج سطح المروحة المرخصة.", "verb_caus_3-lit", "w-h-ꜣ", sound="w↔و في IDN-10 وh↔ه في IDN-20؛ ꜣ↔ي هي الرجل المصرية غير الموقعة.", orbit="الوهي شق وتخرق واسترخاء الرباط، وهو مدار تفكك السفينة مباشرة؛ خروج الصوت المتجانس لا يرث الحكم.", keywords="الوهي|الشق|تخرق|انشق|ضعف|استرخى"),
    caus_gap("aed-v1.0:850325", "وني", "SOURCE-GAP", "drive on/make hurry موسومان بالسؤال في الإنجليزية، والألمانية تكرر الشك؛ لا حدث سوق أو تعجيل محسوما يقارن بوني في الفتور والإبطاء.", "verb_caus_3-inf", "w-n-j"),
    gap("aed-v1.0:850573", "معكر", "OPEN-CANDIDATE", "be brave لا يطابق معكر أو مضكر ومغكر وبقية المروحة في العربية الممسوحة، ولا يدخل شجاعة من خارج الرسم."),
    caus_gap("aed-v1.0:857996", "وبخ", "OPEN-CANDIDATE", "shine/illumine/be illuminated لا يطابق وبخ في اللوم والتقريع، ولا يدخل نور أو ضوء من خارج الجذر.", "verb_caus_3-lit", "w-b-ḫ"),
    terminal("aed-v1.0:23140", "∅", "OUT-OF-SCOPE", "non-existent one وصف سلبي اسمي مبني بأداة عدم ونسبة، لا جذر معجمي مستقل تصدره المروحة."),
    terminal("aed-v1.0:24620", "∅", "OUT-OF-SCOPE", "four in number اسم عدد مجرد؛ عزل أسماء الأعداد من هذه النافذة لا يصدر جذرا عربيا من قيمة العدد."),
    terminal("aed-v1.0:26310", "∅", "OUT-OF-SCOPE", "Hidden-one اسم شيطان مرضي مخصوص في الثقافة المصرية؛ الاسم الثقافي لا يرث فعل الإخفاء ولا يصدر مقابلا عربيا بالقوة."),
    terminal("aed-v1.0:26330", "∅", "OUT-OF-SCOPE", "enduring one لقب ثور مقاتل مخصوص؛ اللقب الحيواني لا يورث حكم صفة الدوام إلى جذر عربي مفرد."),
    gap("aed-v1.0:41450", "عقي", "OPEN-CANDIDATE", "servant، أي one who enters، لا يطابق عقي في العقيقة والعقي ولا ضقي وغقي، ولا يدخل خادم من خارج الجذر.", zero="عزلت .t علامة التأنيث الاسمية؛ بقي ꜥ-q-y كاملا بلا إسقاط صامت جذري."),
    gap("aed-v1.0:46780", "يمن", "LAW-GAP", "Right-side يطابق اليمن والجهة اليمنى، لكن w-n-m لا يسوي y-m-n بلا قلب صامتين ومسار مصري موقع، والمقابل خارج سطح المروحة.", sound="الدلالة تقترح يمن؛ بقي w↔ي مشروطا بفرع آخر، كما بقي قلب n-m إلى m-n بلا قانون مصري موقع.", orbit="اليمن خلاف اليسار والجهة اليمنى مدار مباشر، لكن الحكم للعضو المؤسسي المسمى وحده ولا ينتقل إلى فرقتي العمال.", keywords="اليمن|اليمين|خلاف اليسار|الجهة اليمنى", zero="عزلت .j علامة النسبة الاسمية؛ بقي w-n-m كاملا، ولم أقلب صامتين بحدس."),
    terminal("aed-v1.0:47920", "∅", "OUT-OF-SCOPE", "Great-one اسم التاج المصري الأعلى؛ اسم الشارة الملكية الثقافي لا يصدر جذرا عربيا من صفة العظمة."),
    terminal("aed-v1.0:47940", "∅", "OUT-OF-SCOPE", "great one اسم الحلزون الأمامي في التاج الأحمر؛ اسم جزء الشارة الملكية الثقافي لا يرث معنى العظمة العام."),
    gap("aed-v1.0:55170", "بوت", "OPEN-CANDIDATE", "detested one لا يطابق بوت أو بوط في العربية الممسوحة، ولا يدخل بغض أو مقت من خارج الرسم.", zero="عزلت .j علامة النسبة الاسمية؛ بقي b-w-t كاملا بلا إسقاط صامت جذري."),
    terminal("aed-v1.0:68230", "∅", "OUT-OF-SCOPE", "such a one صفة إحالية وظيفية لا مادة معجمية مستقلة قابلة لحكم النسب في هذا الرتل."),
    terminal("aed-v1.0:68690", "∅", "OUT-OF-SCOPE", "thirty اسم عدد مجرد؛ عزل العدد لا يصدر جذرا عربيا من القيمة الحسابية."),
    gap("aed-v1.0:68800", "معنن", "OPEN-CANDIDATE", "rope of two twisted skeins لا يطابق معنن أو مضنن ومغنن في العربية الممسوحة، ولا يدخل حبل أو فتل من خارج الرسم."),
    terminal("aed-v1.0:73610", "∅", "COMPOUND-BOUNDARY", "الرسم `mḥ-jb` ذو حدين موصولين ويسمي confidant؛ حد المركب يمنع حمل المجموع على جذر عربي مفرد أو توريث معنى أحد جزأيه للآخر."),
    gap("aed-v1.0:83660", "نفر", "OPEN-CANDIDATE", "beautiful one لا يطابق نفر في الانزعاج والتفرق ولا نفل في العطاء، ولا يدخل حسن أو جمال من خارج الجذر.", zero="عزلت .t علامة التأنيث الاسمية؛ بقي n-f-r كاملا بلا إسقاط صامت جذري."),
    gap("aed-v1.0:84870", "نني", "OPEN-CANDIDATE", "weary one، ولا سيما الميتة، لا يطابق نني أو ننيط في العربية الممسوحة، ولا يدخل تعب أو موت من خارج الجذر.", zero="عزلت .t علامة التأنيث الاسمية؛ بقي n-n-y كاملا بلا إسقاط صامت جذري."),
    gap("aed-v1.0:87760", "نخنم", "SOURCE-GAP", "AED لا يسمي إلا one of the seven sacred oils بين معقوفين بلا تعيين الزيت أو مادته؛ لا مرجع معجمي محكوم يقارن بنخنم أو نحنم."),
    gap("aed-v1.0:90410", "نثر", "OPEN-CANDIDATE", "divine one/sacred one لا يطابق نثر في التفريق والرمي ولا نتر ونطر وبقية المروحة، ولا يدخل قدس أو إله من خارج الجذر.", zero="عزلت .j علامة النسبة الاسمية؛ بقي n-ṯ-r كاملا بلا إسقاط صامت جذري."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT
assert {item.state for item in DECISIONS} <= LEGAL_CLOSURES
assert {item.verdict for item in DECISIONS} <= LEGAL_CLOSURES

OUTSIDE_FAN = {
    "aed-v1.0:135360", "aed-v1.0:136700", "aed-v1.0:149870",
    "aed-v1.0:450163", "aed-v1.0:650021", "aed-v1.0:46780",
}

WITNESS_NOTES = {
    "aed-v1.0:135360": "أثبت كتاب العين ولسان العرب منح الشيء بمعنى أعطاه؛ ثبت مدار endow، وبقي ḫ↔ح بلا صف مصري.",
    "aed-v1.0:136700": "أثبت الصحاح ولسان العرب نعم الشيء بمعنى رق ولان؛ ثبت مدار make smooth، وبقيت ꜥ النهائية بإزاء م بلا صف.",
    "aed-v1.0:136750": "أثبت المحكم والمفردات أن النور ضوء يعين على الإبصار؛ ثبتت الوساطة، وبقي ꜣ↔ر وفرق الأداة والفعل.",
    "aed-v1.0:136830": "أثبت الصحاح ولسان العرب نرت غيري وأنرته بمعنى نفرته؛ ثبت drive away، وبقي الحدث المجمد للضوء مانعا.",
    "aed-v1.0:140530": "أثبت الصحاح والمحكم الحور للنقصان والهلكة والرجوع من حال إلى حال؛ ثبت تماس decay، وبقي ꜣ↔ر.",
    "aed-v1.0:141990": "أثبت المحكم والمصباح خفى الشيء بمعنى أظهره واستخرجه؛ ثبت تماس bring، وبقي الحدث المجمد لضعف الظهور مانعا.",
    "aed-v1.0:143690": "أثبت الصحاح ولسان العرب الخريدة للبكر والعذراء غير الممسوسة؛ ثبت تماس الحداثة، وبقي ẖ↔خ بلا صف مصري.",
    "aed-v1.0:143970": "أثبت الصحاح والمحكم الصفد للعطاء وأصفده بمعنى أعطاه مالا؛ ثبت تماس supply، وبقي الصوت والحدث المجمد للوثاق مانعين.",
    "aed-v1.0:145680": "أثبت كتاب العين والصحاح ستر الشيء بمعنى أخفاه وغطاه؛ ثبت مدار secret، وبقيت رجلان صوتيتان.",
    "aed-v1.0:149720": "أثبت المصباح أن أضاء بمعنى أنار وأشرق؛ ثبت تماس الصباح والضوء، وبقي الصوت وفرق الزمن عن الفعل.",
    "aed-v1.0:149870": "أثبت الصحاح والمحكم ضم الشيء إلى الشيء وجمعه؛ ثبت مدار attach، وبقي j النهائي بلا مقابل.",
    "aed-v1.0:450163": "أثبت الصحاح ولسان العرب شدا الإبل بمعنى ساقها؛ ثبت تماس الإخراج بالحركة، وبقي j↔و والحدث المجمد مانعين.",
    "aed-v1.0:650021": "أثبت كتاب العين ولسان العرب الوهي للشق والتخرق والضعف؛ ثبت مدار break up، وبقي ꜣ↔ي بلا صف مصري.",
    "aed-v1.0:46780": "أثبت كتاب العين ولسان العرب اليمن واليمين خلاف اليسار؛ ثبت مدار Right-side، وبقي القلب الصوتي بلا قانون.",
}


def round37_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R36.round36_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND36-COMPLETION", "ROUND37-COMPLETION")
    card = card.replace(
        f"round36-egyptian-rank={rank}/{CARD_COUNT}",
        f"round37-egyptian-rank={rank}/{CARD_COUNT}",
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
        raise SystemExit("Round-thirty-seven marker already exists; append refused.")

    aramaic_exact, _ = R9.load_entries("aramaic")
    aramaic_queue = R9.select_aramaic(aramaic_text, aramaic_exact)
    assert not aramaic_queue, (
        "Aramaic short live-open queue is no longer exhausted: "
        f"{[item['entry_id'] for item in aramaic_queue[:10]]}"
    )

    egyptian_exact, _ = R9.load_entries("egyptian")
    queue = R36.R35.R34.R33.R32.R31.R30.R29.select_egyptian_fast(
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
        round37_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة السابعة والثلاثون: استمرار المخزون المصري المسجل المفتوح (2026-08-27)", "",
        (
            "أعيد فحص الآرامية أولا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرا، فسجل الانتقال المسمى `{TRANSITION}`. انتقيت ثمانين "
            "بطاقة مصرية بدءا من `WO-C-OPEN-COMP-02223` بقصر الهيكل ثم موضع "
            "اللقطة. استبعد صف ḏ المؤجل. في كل بطاقة عرضت إصابات AED كلها بلا "
            "حد، وكتب وسم الطريق والرسم والمدخل المختار، وحفظ الاختلاف "
            "والمتجانسات بلا محو. فحصت حالة الإغلاق والحكم آليا على القائمة "
            "القانونية وحدها في `data/closure-vocabulary.json`."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-02223 إلى WO-C-OPEN-COMP-02262", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-02263 إلى WO-C-OPEN-COMP-02302", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([
                f"<!-- LANE-C-R37-EGYPTIAN-CHUNK-{rank:03d}:END -->", "",
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
        "## الجولة السابعة والثلاثون: المسار C، الساميات والمصرية (2026-08-27)", "",
        f"- الوقت: {now}.",
        "- أعيد فحص الساميات أولا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-02223` إلى `WO-C-OPEN-COMP-02262`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-02263` إلى `WO-C-OPEN-COMP-02302`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طبق الانضباط الثلاثي: الموجب له صوت موقع وحدث مجمد ومدار مكتوب؛ وكل بطاقة أخرى لها عائق شريف مسمى.",
        "- قاموس الإغلاق المغلق وحده مطبق: كل حالات الإغلاق والأحكام اجتازت القائمة القانونية في `data/closure-vocabulary.json`.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ الموجب مقصور على العضو ومداره المكتوب.",
        "- الموجب: `sqni̯↔قني` في الإغناء واكتساب المال، بجذر كامل بعد عزل السابقة السببية؛ حكمه `ROOT-ECHO`، ولا يشمل make fat ولا عضو make strong المتجانس.",
        "- التماسان كاملا الصوت `snwr↔نور` في التنفير و`sḫpi̯↔خفي` في الإحضار بقيا `TOOL-GAP` لأن الحدثين المجمدين يثبتان الضوء وضعف الظهور لا التنفير أو الإحضار.",
        "- المطابقات الدلالية المرفوعة بقيت فجوات قانون: `smnḫ↔منح` للعطاء، و`snꜥꜥ↔نعم` للملاسة، و`sḥwꜣ↔حور` للتلف، و`sẖrd↔خرد` للحداثة، و`sštꜣ↔ستر` للإخفاء.",
        "- بقيت `sspd↔صفد` للتزويد، و`sdwꜣ↔ضوء` للصباح، و`sdmj↔ضمم` للإلصاق، و`sšdi̯↔شدو` للإبعاد، و`swhꜣ↔وهي` للتفكك فجوات قانون أو أداة مسماة بلا ترقيع.",
        "- وسم القرض السامي العام في `šnrf` بقي `DIRECTION-GAP` بلا مانح فردي أو طريق مكتمل؛ والمراجع المشكوكة أو غير المسماة بقيت `SOURCE-GAP`.",
        "- الأعداد والألقاب الثقافية والصفات الإحالية أغلقت `OUT-OF-SCOPE`، والمركب `mḥ-jb` أغلق `COMPOUND-BOUNDARY`، وصف ḏ المصري المؤجل بقي مستبعدا.",
        "- لم يحدث شحن أو إيداع أو إعداد مرحلي، ولم يستعمل git أو تحدث مشتقات النشر.", "",
        f"LANE-C DONE37 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
            R36.R35.R34.R33.R32.R31.R30.R29.R28.R27.R26.R25.R24.R23.R20.R10.append
        )
        append(EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian)
        append(REPORT, f"{MARKER}:REPORT", report)
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
