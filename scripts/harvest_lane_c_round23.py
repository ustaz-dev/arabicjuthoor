#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 23 completion cards without shipping or git.

The short live-open Aramaic queue is rechecked first.  Because it remains
exhausted, this round records the named transition to the registered Egyptian
open queue and completes two forty-card batches, WO-C-OPEN-COMP-01103..01182.
All AED homographs are retained, the deferred Egyptian ḏ row stays excluded,
and the output follows the WO-B-PROBE-001 field contract.
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

import harvest_lane_c_round20 as R20


R9 = R20.R9
AR = R20.AR
ROOT = R20.ROOT
ARAMAIC = R20.ARAMAIC
EGYPTIAN = R20.EGYPTIAN
REPORT = R20.REPORT

MARKER = "LANE-C-ROUND23-2026-08-24"
FIRST_SERIAL = 1103
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)


# Every ruling is scoped to the selected AED member.  The positive qsn card
# has a named full-root sound path, a frozen event, two Arabic witnesses, and
# a handwritten orbit.  Direct semantic comparisons lacking an Egyptian
# sound leg remain LAW-GAP; uncertain source glosses remain SOURCE-GAP.
DECISIONS: tuple[R9.Decision, ...] = (
    R9.gap("aed-v1.0:170480", "توت", "SEMANTIC-GAP", "like/sufficient/complete لا يطابق التوت أو التوتياء في شواهد العربية."),
    R9.gap("aed-v1.0:170730", "تبن", "SEMANTIC-GAP", "cut off لا يطابق التبن أو علف الدابة أو القدح الكبير في مادة تبن."),
    R9.gap("aed-v1.0:172420", "تني", "SEMANTIC-GAP", "old/grow old لا يجد في مادة تني العربية شاهدًا عاملًا، وبقية المروحة لا تسمي الهرم."),
    R9.gap("aed-v1.0:172860", "ترر", "SOURCE-GAP", "الحس المصري نفسه موسوم بالسؤال بين race وouting، والعربية ترر للقطع والبعد لا تحسم أيهما."),
    R9.gap("aed-v1.0:173110", "طخي", "SEMANTIC-GAP", "drunk لا يطابق طخي للظلمة والسحاب الرقيق."),
    R9.gap("aed-v1.0:173270", "تخن", "SEMANTIC-GAP", "hide/hidden لا يجد شاهدًا عاملًا في تخن أو طخن."),
    R9.gap("aed-v1.0:173490", "طشي", "SEMANTIC-GAP", "absent/missing/flee لا يطابق طشي بمعنى برئ المريض."),
    R9.gap("aed-v1.0:173610", "تكر", "SEMANTIC-GAP", "illumine/burn لا يطابق التكري القائد أو الاسم الأعجمي في مادة تكر."),
    R9.gap("aed-v1.0:173680", "تكن", "SEMANTIC-GAP", "near/draw near لا يطابق اسم المرأة أو بدل السكين في مادة تكن."),
    R9.gap("aed-v1.0:174260", "ثني", "SEMANTIC-GAP", "take/seize/don لا يطابق ثني الشيء ورد بعضه على بعض."),
    R9.gap("aed-v1.0:174590", "ترم", "SEMANTIC-GAP", "cloak/close a wound لا يجد في ترم أو بقية المروحة معنى الستر أو التأم الجرح."),
    R9.gap("aed-v1.0:175200", "تبن", "SEMANTIC-GAP", "quick لا يطابق التبن أو الفطنة المسجلة في مادة تبن."),
    R9.gap("aed-v1.0:175440", "ثمر", "SEMANTIC-GAP", "strong/mighty لا يطابق الثمر وحمل الشجر، ولا يرث العضو قوة من مجاز غير منصوص."),
    R9.gap("aed-v1.0:175750", "ثني", "SEMANTIC-GAP", "lift/distinguish لا يطابق رد الشيء بعضه على بعض أو منعطفه، والثناء عضو دلالي آخر."),
    R9.gap("aed-v1.0:175780", "ثني", "SOURCE-GAP", "feeble موسوم بالسؤال في AED؛ لا يصدر مدار ضعف من حس مصري غير محسوم."),
    R9.gap("aed-v1.0:176050", "ثنر", "SEMANTIC-GAP", "strong/grow strong لا يجد شاهدًا عاملًا في ثنر أو تنر أو طنر."),
    R9.gap("aed-v1.0:176410", "طرح", "DIRECTIONAL-TRANSMISSION", "وسم Semitic loan word لا يسمي مانحًا ساميًا ولا طريقًا، والعربية طرح لا تسمي السخرية.", orbit="السخرية والإهانة مدار العضو المصري، لكن النقل المعلن بلا مانح مسمى لا يغلق الاتجاه."),
    R9.gap("aed-v1.0:177210", "تزي", "SEMANTIC-GAP", "angry/bear a grudge لا يجد في تزي أو طزي شاهد غضب عاملًا."),
    R9.gap("aed-v1.0:178160", "دون", "SEMANTIC-GAP", "stretch out/taut لا يطابق دون للقرب أو الانحطاط عن الغاية."),
    R9.gap("aed-v1.0:178750", "دبح", "SEMANTIC-GAP", "need/ask/requisition لا يطابق دبح لانحناء الظهر وتنكيس الرأس."),
    R9.gap("aed-v1.0:179320", "ضم", "LAW-GAP", "touch/join/cleave يطابق الضم دلالة، لكن d المصرية ↔ ض لا يثبت نسبًا مصريًا، وDENT-06 سند استعاري، كما أن j النهائية لا تقابل صامتًا في ضم.", sound="m↔م هوية IDN-04؛ d↔ض لا يرخصه للمصرية DENT-06 الاستعاري، وj النهائية غير ممثلة في ضم.", orbit="ضم الشيء إلى الشيء جمعه وألصقه به؛ وهو مدار touch/be joined/cleave مباشرة، وبقيت الرجل الصوتية وحدها ناقصة.", keywords="ضم|الجمع|الشيء إلى الشيء|اتصل"),
    R9.gap("aed-v1.0:179910", "دنس", "SEMANTIC-GAP", "weighty/heavy/burdensome لا يطابق الدنس والقذر."),
    R9.gap("aed-v1.0:179970", "دنغ", "SOURCE-GAP", "الإنجليزية تسمي deaf بينما الألمانية لا تعطي إلا صفة سيئة للأذن؛ لا حس فرعي كاف لبناء المدار."),
    R9.gap("aed-v1.0:180690", "دشر", "SEMANTIC-GAP", "red/become red لا يجد في دشر أو دسر شاهد حمرة عاملًا."),
    R9.gap("aed-v1.0:181130", "دجي", "SEMANTIC-GAP", "hide/hidden لا يطابق دجي أو دقي أو دغي في الشواهد العربية المقروءة."),
    R9.gap("aed-v1.0:181140", "دجي", "SEMANTIC-GAP", "behold/see لا يطابق دجي؛ وحُفظ الفصل عن متجانسه المصري السابق بمعنى الاختفاء."),
    R9.gap("aed-v1.0:181200", "دغم", "SEMANTIC-GAP", "speechless/unconscious لا يطابق دغم لكسر الأنف أو السواد أو الإدخال."),
    R9.gap("aed-v1.0:400854", "متي", "SEMANTIC-GAP", "precise/correct لا يطابق متي التي لا تعطي إلا إحالة صرفية إلى متو."),
    R9.gap("aed-v1.0:400955", "معر", "SEMANTIC-GAP", "fortunate/successful لا يطابق معر لسقوط الشعر أو قلة النبات أو الفقر."),
    R9.gap("aed-v1.0:400975", "حنس", "SEMANTIC-GAP", "narrow/constricted لا يطابق حنس للثبات في وسط المعركة أو الورع."),
    R9.gap("aed-v1.0:450143", "بجس", "SEMANTIC-GAP", "injure/disloyal لا يطابق بجس لانفجار الماء أو شقه، ولا يُسوّى الأثر بالفعل المؤذي."),
    R9.gap("aed-v1.0:500010", "وصل", "SEMANTIC-GAP", "strong/powerful لا يطابق الوصل والاتصال، ولا يرث القوة من متجانس آخر."),
    R9.gap("aed-v1.0:500142", "صفد", "SEMANTIC-GAP", "sharp/make sharp لا يطابق صفد للشد والوثاق أو العطاء."),
    R9.pos("aed-v1.0:550033", "قسن", "ROOT-ECHO", "اقسأن|اشتد|عسا|قسأنينة|صلب", "q↔ق في IDN-12 وs↔س في IDN-07 وn↔ن في IDN-03؛ جذر كامل.", "اقسأن الشيء: اشتد وعسا؛ وهو difficult مباشرة.", "ECHO للشدة والعسر في العضو المختار."),
    R9.gap("aed-v1.0:600211", "خلو", "SEMANTIC-GAP", "say/tell لا يطابق الخلو والفراغ والانفراد."),
    R9.gap("aed-v1.0:850019", "يعر", "SEMANTIC-GAP", "speak a foreign language/interpret لا يجد في يعر أو بقية المروحة شاهد تفسير أو ترجمة عاملًا."),
    R9.gap("aed-v1.0:850126", "وجج", "SEMANTIC-GAP", "weak لا يطابق وج للموضع أو الدواء أو السرعة."),
    R9.gap("aed-v1.0:850234", "ينن", "SEMANTIC-GAP", "cut/cut up لا يجد في ينن أو ءنن شاهد قطع عاملًا."),
    R9.gap("aed-v1.0:850422", "وتت", "SEMANTIC-GAP", "old/great لا يجد في وتت أو وطط شاهد هرم أو عظمة عاملًا."),
    R9.gap("aed-v1.0:850481", "بقا", "SEMANTIC-GAP", "shipwrecked لا يطابق البقاء، ولا تُسوّى النجاة بالغرق أو تحطم السفينة."),
    R9.gap("aed-v1.0:851887", "عحع", "SEMANTIC-GAP", "stand/get ready لا يجد في عحع أو ضحع أو غحع شاهد قيام عاملًا."),
    R9.gap("aed-v1.0:853374", "وحف", "SEMANTIC-GAP", "burn لا يجد في وحف شاهد إحراق عاملًا."),
    R9.gap("aed-v1.0:858862", "منح", "SEMANTIC-GAP", "make young لا يطابق منح للعطاء والهبة."),
    R9.gap("aed-v1.0:175", "لهو", "SEMANTIC-GAP", "sufferer/anxious one لا يطابق اللهو والانشغال، وبقية المروحة لا تسمي القلق."),
    R9.gap("aed-v1.0:353", "ردو", "SEMANTIC-GAP", "aggressor/furious crocodile لا يجد في ردو أو رضو شاهد عدوان أو غضب عاملًا."),
    R9.gap("aed-v1.0:24560", "يفد", "SEMANTIC-GAP", "the four لا يجد في يفد أو ءفد شاهد عدد أربعة عاملًا."),
    R9.gap("aed-v1.0:37360", "عفع", "SEMANTIC-GAP", "greedy one لا يجد في عفع أو ضفع أو غفع شاهد جشع عاملًا."),
    R9.gap("aed-v1.0:38580", "عنخ", "SEMANTIC-GAP", "captive/bound one لا يجد في عنخ أو ضنخ أو غنخ شاهد أسر أو ربط عاملًا."),
    R9.gap("aed-v1.0:41320", "عقل", "SEMANTIC-GAP", "correct/straightforward لا يساوي العقل أو الحبس في المادة العربية؛ الاستقامة ثمرة محتملة وليست معنى الجذر نفسه."),
    R9.gap("aed-v1.0:41440", "عقي", "SEMANTIC-GAP", "priest/one who has access لا يجد في عقي أو ضقي أو غقي شاهد دخول كهنوتي عاملًا."),
    R9.gap("aed-v1.0:44180", "وعت", "NAME-ROOT-OPEN", "Sole-one لقب للصل المصري؛ لا يسمي وعت العربية الواحدة ولا يثبت جذر اللقب."),
    R9.gap("aed-v1.0:44450", "وعب", "SEMANTIC-GAP", "pure one لا يطابق وعب للاستيعاب والأخذ أجمع؛ الكمال الكمي ليس الطهارة."),
    R9.gap("aed-v1.0:47440", "ورت", "NAME-ROOT-OPEN", "great one لقب بقرة إلهية؛ لا يسمي ورت العربية العظمة ولا يثبت جذر اللقب."),
    R9.gap("aed-v1.0:47450", "ورت", "NAME-ROOT-OPEN", "Great-one اسم للصل الملكي؛ فُصل عن متجانسي البقرة والتاج وبقي جذر الاسم مفتوحًا."),
    R9.gap("aed-v1.0:47460", "ورت", "NAME-ROOT-OPEN", "Great-one اسم لتاج مصر السفلى؛ فُصل عن الصل والبقرة وبقي جذر الاسم مفتوحًا."),
    R9.gap("aed-v1.0:49610", "وصل", "SEMANTIC-GAP", "powerful one لا يطابق الوصل والبلوغ في العربية."),
    R9.gap("aed-v1.0:49630", "وصل", "SEMANTIC-GAP", "powerful one في عضو أوزير لا يطابق الوصل؛ حُفظ القيد العضوي ولم يُنقل معنى المتجانس."),
    R9.gap("aed-v1.0:51380", "وتز", "SEMANTIC-GAP", "one who elevates ritually لا يجد في وتز أو وتس أو وطز شاهد رفع عاملًا."),
    R9.gap("aed-v1.0:51740", "ودن", "SEMANTIC-GAP", "heavy one لا يطابق ودن للبل أو الضرب أو حسن القيام على العروس."),
    R9.gap("aed-v1.0:54610", "بين", "SEMANTIC-GAP", "evil one لا يطابق بين للظهور أو الفصل والبينونة."),
    R9.gap("aed-v1.0:58030", "بجب", "SOURCE-GAP", "مدخل الحركة نفسه محاط بالأقواس ويسأل make one's way to؛ لا يصدر مدار من فعل غير محسوم."),
    R9.gap("aed-v1.0:73920", "مح", "SOURCE-GAP", "drowned one خاص بأوزير، والألمانية تجعل الغرق نفسه موضع سؤال؛ لا يُسوّى بالمحو أو البلى."),
    R9.gap("aed-v1.0:78290", "مدس", "SEMANTIC-GAP", "violent one لا يطابق مدس لدلك الأديم."),
    R9.gap("aed-v1.0:81320", "نون", "SEMANTIC-GAP", "Disheveled-one لا يطابق النون للحرف أو الحوت."),
    R9.gap("aed-v1.0:83500", "نفر", "SEMANTIC-GAP", "good/beautiful one لا يطابق نفر للانزعاج والتفرق والنفور."),
    R9.gap("aed-v1.0:87460", "نخخ", "SEMANTIC-GAP", "enduring/adolescent لا يطابق نخخ للسوق العنيف أو الإناخة."),
    R9.gap("aed-v1.0:87580", "نخت", "SEMANTIC-GAP", "strong one لا يطابق نخت للنقر أو أخذ التمرة أو استقصاء القول."),
    R9.terminal("aed-v1.0:89850", "نتي", "OUT-OF-SCOPE", "العضو ضمير وصل وظيفي لا جذرًا معجميًا مفردًا؛ أُغلق خارج نطاق المقارنة الجذرية."),
    R9.gap("aed-v1.0:94740", "رنت", "SEMANTIC-GAP", "young female animal لا يجد في رنت أو لنت شاهد حيوان صغير عاملًا."),
    R9.gap("aed-v1.0:95790", "رخي", "SEMANTIC-GAP", "acquaintance/known one لا يجد في رخي أو لخي شاهد معرفة عاملًا."),
    R9.gap("aed-v1.0:104440", "حفن", "SEMANTIC-GAP", "one hundred thousand لا يطابق الحفنة وملء الكفين، بل يعاكس دلالة القلة المنصوصة."),
    R9.gap("aed-v1.0:105320", "حمو", "SEMANTIC-GAP", "forty لا يطابق حمو أو حمم أو حمي في الشواهد العربية."),
    R9.gap("aed-v1.0:109750", "حزي", "SEMANTIC-GAP", "praised one لا يطابق حزي للتكهن وخرص النخل وزجر الطير."),
    R9.gap("aed-v1.0:117240", "خمن", "SEMANTIC-GAP", "eight لا يطابق خمن للتقدير بالوهم والحدس."),
    R9.gap("aed-v1.0:128520", "سيس", "SEMANTIC-GAP", "six لا يطابق سيس لفقار الظهر أو الحارك."),
    R9.gap("aed-v1.0:130620", "سوح", "SEMANTIC-GAP", "shrouded one لا يطابق الساحة والفضاء في سوح."),
    R9.gap("aed-v1.0:133760", "سفخ", "SEMANTIC-GAP", "seven لا يجد في سفخ أو شفخ أو صفخ شاهد العدد سبعة عاملًا."),
    R9.gap("aed-v1.0:133990", "سفت", "SEMANTIC-GAP", "sacred oil لا يطابق سفت للإكثار من الشراب أو لغة الزفت، ولا يثبت نوع الزيت نفسه."),
    R9.gap("aed-v1.0:145080", "شسم", "SEMANTIC-GAP", "butcher لا يجد في شسم أو سشم أو صشم شاهد ذبح أو جزارة عاملًا."),
    R9.gap("aed-v1.0:154900", "حمم", "LAW-GAP", "hot one يطابق حمم في الحرارة، لكن š المصرية ↔ ح العربية بلا صف مصري موقع؛ بقي حكم العائلة السابق مفتوحًا.", sound="m↔م والتضعيف هويتان IDN-04؛ š المصرية↔ح العربية هي الرجل غير الموقعة.", orbit="الحرارة والحمى في حمم مدار hot one مباشرة؛ لا يرثه حس العدو في الألمانية.", keywords="الحميم|الحمة|الحار|حرارة|حمى"),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT


def round23_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R20.round20_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND20-COMPLETION", "ROUND23-COMPLETION")
    card = card.replace(
        "ROUND23-COMPLETION (2026-08-18)",
        "ROUND23-COMPLETION (2026-08-24)",
    )
    card = card.replace(
        f"round20-egyptian-rank={rank}/{R20.CARD_COUNT}",
        f"round23-egyptian-rank={rank}/{CARD_COUNT}",
    )
    card = card.replace(
        "\n- إحالة الجرد المفتوح:",
        "\n- النموذج: `WO-B-PROBE-001`؛ الطبقة: استكشاف.\n- إحالة الجرد المفتوح:",
        1,
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
        raise SystemExit("Round-twenty-three marker already exists; append refused.")

    aramaic_exact, _ = R9.load_entries("aramaic")
    aramaic_queue = R9.select_aramaic(aramaic_text, aramaic_exact)
    assert not aramaic_queue, (
        "Aramaic short live-open queue is no longer exhausted: "
        f"{[item['entry_id'] for item in aramaic_queue[:10]]}"
    )

    egyptian_exact, _ = R9.load_entries("egyptian")
    queue = R9.select_egyptian(egyptian_text, egyptian_exact)
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
        round23_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الثالثة والعشرون: استمرار المخزون المصري المسجل المفتوح (2026-08-24)", "",
        (
            "أُعيد فحص الآرامية أولًا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرًا، فسُجل الانتقال المسمى `{TRANSITION}`. انتُقيت ثمانون "
            "بطاقة مصرية بدءًا من `WO-C-OPEN-COMP-01103` بقصر الهيكل ثم موضع "
            "اللقطة. استُبعد صف ḏ المؤجل. في كل بطاقة عُرضت إصابات AED كلها بلا "
            "حد، وكُتب وسم الطريق والرسم والمدخل المختار، وحُفظ الاختلاف "
            "والمتجانسات بلا محو."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-01103 إلى WO-C-OPEN-COMP-01142", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-01143 إلى WO-C-OPEN-COMP-01182", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([f"<!-- LANE-C-R23-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    states = dict(sorted(collections.Counter(item.state for item in DECISIONS).items()))
    verdicts = dict(sorted(collections.Counter(item.verdict for item in DECISIONS).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    now = datetime.now(ZoneInfo("Africa/Cairo")).strftime("%Y-%m-%d %H:%M:%S %z")
    now = now[:-2] + ":" + now[-2:]
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة الثالثة والعشرون: المسار C، الساميات والمصرية (2026-08-24)", "",
        f"- الوقت: {now}.",
        "- أُعيد فحص الساميات أولًا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تُكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سُجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01103` إلى `WO-C-OPEN-COMP-01142`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01143` إلى `WO-C-OPEN-COMP-01182`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طُبقت قواعد AED الثلاث: كل الإصابات بلا حد؛ وسم الطريق والرسم والمدخل المختار مكتوبة؛ الاختلاف والمتجانسات محفوظة بلا محو.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}؛ لا فجوة حُولت إلى نفي.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ الموجب الوحيد مقصور على عضو AED المختار ومداره المكتوب.",
        "- الموجب: `qsn↔قسن` في الشدة والعسر، بمسار الجذر الكامل `IDN-12 + IDN-07 + IDN-03`.",
        "- المطابقتان الدلاليتان ذواتا الرجل الصوتية الناقصة بقيتا مفتوحتين: `dmj↔ضم` و`šmm↔حمم`.",
        "- الأعضاء المشكوكة `trr` و`ṯnj` و`dng` و`bgb` و`mḥ.w` بقيت `SOURCE-GAP`؛ ووسم القرض في `ṯrḥ` بقي `DIRECTIONAL-TRANSMISSION` بلا مانح سامي مسمى.",
        "- صف ḏ المصري المؤجل بقي مستبعدًا، ولا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE23 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
        "max_card_bytes": max(len(card.encode("utf-8")) for card in cards),
    }
    egyptian_appendix = unicodedata.normalize("NFC", "\n".join(body).rstrip() + "\n")
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
        R20.R10.append(EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian)
        R20.R10.append(REPORT, f"{MARKER}:REPORT", report)
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
