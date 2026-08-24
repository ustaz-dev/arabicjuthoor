#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 24 completion cards without shipping or git.

The short live-open Aramaic queue is rechecked first.  When it remains
exhausted, the script records the named transition to the registered Egyptian
open queue and completes two forty-card batches, WO-C-OPEN-COMP-01183..01262.
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

import harvest_lane_c_round23 as R23


R9 = R23.R9
AR = R23.AR
ROOT = R23.ROOT
ARAMAIC = R23.ARAMAIC
EGYPTIAN = R23.EGYPTIAN
REPORT = R23.REPORT

MARKER = "LANE-C-ROUND24-2026-08-24"
FIRST_SERIAL = 1183
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)


# Every ruling is scoped to the selected AED member.  Grammatical formatives
# without a published lexical analysis are closed OUT-OF-SCOPE.  Unidentified
# or explicitly questioned AED senses remain SOURCE-GAP, and the Semitic-loan
# label on ybr remains directional until a donor and route are named.  The one
# direct semantic comparison (gr.w ~ قر) remains LAW-GAP because g↔ق has no
# signed Egyptian leg; no semantic gap is converted into a negative verdict.
DECISIONS: tuple[R9.Decision, ...] = (
    R9.gap("aed-v1.0:155320", "شنت", "SEMANTIC-GAP", "hundred لا يجد في شنت أو شنط أو سنت أو سنط اسم العدد مئة عاملًا."),
    R9.gap("aed-v1.0:165890", "كتت", "SEMANTIC-GAP", "little one لا يطابق حواس كتت أو كت أو كط في العربية المقروءة."),
    R9.gap("aed-v1.0:167550", "جنن", "SEMANTIC-GAP", "weak one لا يطابق الستر أو الجنون في جنن، ولا يجد في قنن أو غنن شاهد الضعف نفسه."),
    R9.gap("aed-v1.0:167800", "قر", "LAW-GAP", "silent one يلتقي قرّ وسكن، لكن g المصرية ↔ ق العربية بلا صف مصري موقع لهذا العضو.", sound="r↔ر هوية؛ g↔ق هي الرجل المصرية غير الموقعة.", orbit="قرّ في مكانه ثبت وسكن؛ وهو مدار silent one مباشرة، وبقي الصوت وحده ناقصًا.", keywords="ساكن|سكن|استقر|القرار"),
    R9.terminal("aed-v1.0:175720", "∅", "OUT-OF-SCOPE", "ضمير لاحق للمخاطب المثنى؛ لا تحليل جذري معجمي منشور يجيز إدخاله في قياس الجذور."),
    R9.gap("aed-v1.0:176060", "ثنر", "SEMANTIC-GAP", "mighty one لا يطابق التنور أو حواس ثنر وثنل وتنر وطنر، ولا يُدخل القوة من خارج الرسم."),
    R9.gap("aed-v1.0:176450", "ثهء", "SEMANTIC-GAP", "lame one لا يجد في ثهء أو ثحر أو بقية المروحة شاهد العرج أو العجز عن المشي عاملًا."),
    R9.gap("aed-v1.0:177840", "ديو", "SEMANTIC-GAP", "five لا يجد في ديو أو ضيو أو الصور الأقصر اسم العدد خمسة عاملًا."),
    R9.gap("aed-v1.0:179920", "دنس", "SEMANTIC-GAP", "heavy one بوصف فرس النهر لا يطابق الدنس والقذر، ولا يرث العضو ثقلًا من وصف الحيوان."),
    R9.gap("aed-v1.0:180780", "دشر", "SEMANTIC-GAP", "red one بوصف فرس النهر لا يجد في دشر أو دسر أو ضشر شاهد الحمرة عاملًا."),
    R9.terminal("aed-v1.0:400647", "∅", "OUT-OF-SCOPE", "اسم موصول مستعمل استعمالًا اسميًا بمعنى الذي يكون؛ لا تحليل جذري معجمي مستقل في المدخل."),
    R9.gap("aed-v1.0:450654", "نبو", "SEMANTIC-GAP", "golden one لقب للمتوفى في صلته بأوزير، ولا تسمي نبو أو بقية المروحة الذهب أو هذا اللقب."),
    R9.terminal("aed-v1.0:600023", "∅", "OUT-OF-SCOPE", "صيغة حسابية مركبة للتعبير عن الجزء النوني من عدد؛ لا لفظة جذرية مفردة منشورة."),
    R9.gap("aed-v1.0:600045", "وع", "MORPHOLOGY-GAP", "sole one يقترح واحدًا، لكن حاء وحد وداله صامتان جذريان غير موجودين في wꜥ.t ولا في صرف مسمى.", sound="w↔و وꜥ↔ع ظاهران؛ ح ود في واحد بلا مقابل مصري.", orbit="الوحدة والانفراد متقاربان مباشرة، وبقيت البنية الجذرية ناقصة.", keywords="واحد|وحده|الواحد"),
    R9.gap("aed-v1.0:650002", "سكن", "SEMANTIC-GAP", "greedy one لا يطابق السكن والثبات، ولا يجد في شكن أو صكن شاهد الجشع عاملًا."),
    R9.gap("aed-v1.0:858085", "نحد", "SEMANTIC-GAP", "roar/bellow/raise the voice لا يطابق نحد للعهد والتعاهد، ولا نحض للحم والقشر والسؤال."),
    R9.terminal("aed-v1.0:27490", "∅", "OUT-OF-SCOPE", "ضمير المتكلمين المنفصل وملكيته؛ لا تحليل جذري معجمي منشور."),
    R9.terminal("aed-v1.0:27940", "∅", "OUT-OF-SCOPE", "ضمير المتكلم المفرد المنفصل؛ لا مادة جذرية مستقلة في المصدر."),
    R9.terminal("aed-v1.0:130830", "∅", "OUT-OF-SCOPE", "ضمير الغائب المفرد المذكر؛ لا تحليل جذري معجمي منشور."),
    R9.terminal("aed-v1.0:175050", "∅", "OUT-OF-SCOPE", "ضمير المخاطب المفرد المذكر؛ لا مادة جذرية مستقلة في المدخل."),
    R9.terminal("aed-v1.0:550301", "∅", "OUT-OF-SCOPE", "ضمير المخاطبة المفردة؛ لا تحليل جذري معجمي منشور."),
    R9.terminal("aed-v1.0:24430", "∅", "OUT-OF-SCOPE", "اسم إشارة لجمع المذكر؛ لا مادة جذرية مستقلة في المصدر."),
    R9.terminal("aed-v1.0:27410", "∅", "OUT-OF-SCOPE", "اسم استفهام وظيفي بمعنى من؛ لا تحليل جذري معجمي منشور."),
    R9.terminal("aed-v1.0:59890", "∅", "OUT-OF-SCOPE", "اسم إشارة للمفرد المذكر البعيد؛ لا مادة جذرية مستقلة في المدخل."),
    R9.terminal("aed-v1.0:62920", "∅", "OUT-OF-SCOPE", "اسم استفهام وظيفي بمعنى من أو ماذا؛ لا تحليل جذري معجمي منشور."),
    R9.terminal("aed-v1.0:79580", "∅", "OUT-OF-SCOPE", "بادئة ضمير ملكية للجمع؛ لا مادة جذرية مفردة مستقلة."),
    R9.terminal("aed-v1.0:83990", "∅", "OUT-OF-SCOPE", "اسم استفهام وظيفي بمعنى من؛ لا تحليل جذري معجمي منشور."),
    R9.terminal("aed-v1.0:170301", "∅", "OUT-OF-SCOPE", "اسم إشارة للمفرد المؤنث والمثنى؛ لا مادة جذرية مستقلة في المصدر."),
    R9.terminal("aed-v1.0:171770", "∅", "OUT-OF-SCOPE", "اسم إشارة للمفرد المؤنث البعيد؛ لا تحليل جذري معجمي منشور."),
    R9.terminal("aed-v1.0:175740", "∅", "OUT-OF-SCOPE", "اسم استفهام مكاني وظيفي بمعاني أين ومن أين وإلى أين؛ لا جذر معجمي مستقل."),
    R9.terminal("aed-v1.0:500001", "∅", "OUT-OF-SCOPE", "اسم إشارة للجمع؛ لا مادة جذرية مستقلة في المدخل."),
    R9.terminal("aed-v1.0:550008", "∅", "OUT-OF-SCOPE", "صفة ملكية وظيفية للجمع؛ لا تحليل جذري معجمي منشور."),
    R9.terminal("aed-v1.0:550021", "∅", "OUT-OF-SCOPE", "صفة ملكية وظيفية للمفرد المذكر؛ لا مادة جذرية مستقلة."),
    R9.terminal("aed-v1.0:550046", "∅", "OUT-OF-SCOPE", "صفة ملكية وظيفية للمفرد المؤنث؛ لا مادة جذرية مستقلة."),
    R9.gap("aed-v1.0:13", "ءيس", "SEMANTIC-GAP", "brain/viscera لا يطابق حواس ءيس أو أيس أو الصور المجاورة، ولا يُدخل مخ أو جوف من خارج الرسم."),
    R9.gap("aed-v1.0:30", "ءعز", "SOURCE-GAP", "الأداة ذات هيئة العنخ نفسها موسومة بالسؤال بين أداة وسلاح؛ لا يصدر مدار قبل تعيين الشيء."),
    R9.gap("aed-v1.0:60", "ءبو", "SEMANTIC-GAP", "brand cattle or slaves لا يطابق حواس ءبو أو أبو أو لبو أو ربو، ولا يُدخل وسم من خارج الرسم."),
    R9.gap("aed-v1.0:66", "ءبت", "SEMANTIC-GAP", "brand/branding iron لا يطابق حواس ءبت أو أبط أو لبت أو ربط، ولا تُسوّى أداة الربط بأداة الوسم."),
    R9.gap("aed-v1.0:74", "ءبي", "SEMANTIC-GAP", "leopard لا يجد في ءبي أو أبي أو لبي أو ربي اسم النمر أو الفهد عاملًا."),
    R9.gap("aed-v1.0:80", "ءبو", "SEMANTIC-GAP", "elephant لا يجد في ءبو أو أبو أو لبو أو ربو اسم الفيل عاملًا."),
    R9.gap("aed-v1.0:85", "ءبب", "SEMANTIC-GAP", "separate/move away/keep apart لا يطابق الأب للمرعى أو التهيؤ للذهاب، ولا حواس لبب أو ربب."),
    R9.gap("aed-v1.0:107", "ءبد", "SEMANTIC-GAP", "bird/fowl لا يجد في ءبد أو ءفد أو أبد أو أفد اسم الطير عاملًا."),
    R9.gap("aed-v1.0:119", "ءفي", "SEMANTIC-GAP", "gorge oneself لا يجد في ءفي أو أفي أو لفي أو رفي شاهد الأكل بنهم عاملًا."),
    R9.gap("aed-v1.0:215", "ءخو", "SOURCE-GAP", "الإنجليزية تسمي crops عامةً والألمانية تقترح محصولًا حقليًا غير معين؛ لا يُنتق نبات عربي مخصوص."),
    R9.gap("aed-v1.0:225", "ءخت", "SOURCE-GAP", "provisions موسومة بين الخبز ونوع خبز غير معين؛ لا مادة عربية محددة يقوم عليها المدار."),
    R9.gap("aed-v1.0:231", "ءخت", "SOURCE-GAP", "knife نفسها محاطة بعلامة الشك؛ لا يصدر مدار أداة قاطعة من مرجع غير محسوم."),
    R9.gap("aed-v1.0:256", "ءخف", "SOURCE-GAP", "fever مقيدة باحتمال appetite والألمانية تجعلها شهيةً مشكوكة؛ لا حس فرعي مستقر للمقارنة."),
    R9.gap("aed-v1.0:273", "ءست", "SEMANTIC-GAP", "splinter of flint or wood لا يطابق حواس ءست أو أست أو أشت أو أصت، ولا يُدخل شظية من خارج الرسم."),
    R9.gap("aed-v1.0:298", "ءقس", "SOURCE-GAP", "garment نفسها موسومة بالسؤال؛ لا يصدر مدار لباس من اسم شيء غير محسوم."),
    R9.gap("aed-v1.0:321", "ءتي", "SOURCE-GAP", "العضو لا يعين إلا جزءًا غير مسمى من مركب الشمس؛ لا مادة عربية محددة قبل تعيين الجزء."),
    R9.gap("aed-v1.0:329", "ءتف", "SEMANTIC-GAP", "incense لا يجد في ءتف أو أطف أو لطف أو رطف اسم البخور أو التبخير عاملًا."),
    R9.gap("aed-v1.0:350", "ءدو", "SEMANTIC-GAP", "smoothing or lining a pot with clay لا يطابق حواس ءدو أو أدو أو لدو أو ردو، ولا يُدخل ملاسة من خارج الرسم."),
    R9.gap("aed-v1.0:10340", "ءبو", "SEMANTIC-GAP", "wish/vow لا يطابق حواس ءبو أو أبو أو لبو أو ربو، ولا يُدخل نذر من خارج الرسم."),
    R9.gap("aed-v1.0:20100", "يءت", "SEMANTIC-GAP", "standard for a divine emblem لا يجد في يءت أو يات أو يلت أو يرت اسم الراية أو الحامل عاملًا."),
    R9.gap("aed-v1.0:20170", "يءت", "SOURCE-GAP", "النبات غير معين وvine نفسها اقتراح مشكوك؛ لا يُنتق اسم نبات عربي من الهيكل."),
    R9.gap("aed-v1.0:20240", "يءء", "SOURCE-GAP", "المعدن غير معين وgalena نفسها اقتراح؛ لا مادة عربية محددة يقوم عليها المدار."),
    R9.gap("aed-v1.0:20490", "يءو", "SEMANTIC-GAP", "old age لا يجد في يءو أو ياو أو يلو أو يرو شاهد الهرم أو الكبر عاملًا."),
    R9.gap("aed-v1.0:20770", "يءر", "SOURCE-GAP", "نبات دوائي غير مسمى؛ لا يُنتق اسم عربي لنوع لم يعينه AED."),
    R9.gap("aed-v1.0:20850", "يءخ", "SEMANTIC-GAP", "shine لا يجد في يءخ أو ياخ أو يلخ أو يرخ شاهد اللمعان عاملًا."),
    R9.gap("aed-v1.0:21150", "يءد", "SEMANTIC-GAP", "sufferer/miserable person/evildoer لا يطابق حواس يءد أو ياد أو يلد أو يرد، ولا تُدمج الأوصاف الثلاثة في مقابل مفترض."),
    R9.gap("aed-v1.0:21340", "ييت", "SEMANTIC-GAP", "what comes بوصفه كناية عن البلاء لا يطابق حواس ييت أو ءيت، ولا يُدخل الإتيان ببنية غير محمولة."),
    R9.gap("aed-v1.0:21410", "يير", "SOURCE-GAP", "field نفسها موسومة بالسؤال وموصوفة بقراءة مقطعية؛ لا يصدر مدار حقل قبل حسم المرجع."),
    R9.gap("aed-v1.0:21550", "يعي", "SEMANTIC-GAP", "wash لا يجد في يعي أو يضي أو يغي أو صور الهمزة شاهد الغسل عاملًا."),
    R9.gap("aed-v1.0:21870", "يوت", "SOURCE-GAP", "جزء تجهيز السفينة لا يتجاوز اقتراح cordage/rope؛ لا مادة عربية محددة قبل تعيين القطعة."),
    R9.gap("aed-v1.0:22190", "يوء", "SOURCE-GAP", "نوع السمك غير مسمى؛ لا يُنتق اسم عربي لسمكة من الهيكل وحده."),
    R9.gap("aed-v1.0:22300", "يوي", "SOURCE-GAP", "فعل تجهيز السفينة لا يسمي المعدة، والألمانية توسِم طريقة الاستعمال بالسؤال؛ لا مدار مستقر."),
    R9.gap("aed-v1.0:22480", "يوو", "SEMANTIC-GAP", "wailing لا يجد في يوو أو ءوو أو يو أو ءو شاهد العويل عاملًا؛ همزة أوّه وهاؤها ليستا في الرسم."),
    R9.gap("aed-v1.0:22580", "يون", "SOURCE-GAP", "nest نفسها موسومة بعلامة الشك؛ لا يصدر مدار العش من مرجع غير محسوم."),
    R9.gap("aed-v1.0:22950", "يور", "SOURCE-GAP", "مهرجان طيبي غير مسمى؛ لا معنى معجمي أدق ولا مقابل عربي معين."),
    R9.gap("aed-v1.0:23020", "يوح", "SOURCE-GAP", "destructive activity وصف عام محاط بالأقواس ولا يعين الفعل الضار؛ لا يُنتق جذر عربي مخصوص."),
    R9.gap("aed-v1.0:23440", "يبت", "SOURCE-GAP", "الجزء الليفي من نبات sewet لا يحدد النبات أو اسم جزئه العربي؛ لا مدار معجمي معين."),
    R9.gap("aed-v1.0:23670", "يبو", "SOURCE-GAP", "rope nautical itself موسومة بالسؤال؛ لا يصدر مدار حبل من قطعة غير محسومة."),
    R9.gap("aed-v1.0:23730", "يبب", "SOURCE-GAP", "beetle نفسها محاطة بالأقواس ولا يعين AED النوع؛ لا يُنتق اسم حشرة عربي."),
    R9.gap("aed-v1.0:23800", "يبر", "DIRECTIONAL-TRANSMISSION", "وسم Semitic loan word لا يسمي المانح السامي ولا طريق النقل، ومروحة يبر لا تعطي stream مباشرة.", orbit="مجرى الماء مدار العضو المصري، لكن النقل المعلن بلا مانح أو طريق مسمى لا يغلق الاتجاه."),
    R9.gap("aed-v1.0:24110", "يبت", "SEMANTIC-GAP", "number/census/account لا يطابق حواس يبت أو يفت أو ءبت أو ءفت، ولا يُدخل عدّ من خارج الرسم."),
    R9.gap("aed-v1.0:24250", "يبء", "SEMANTIC-GAP", "red vegetable dye/madder لا يجد في يبء أو يبا أو يبر أو يفا اسم الفوة أو صبغتها عاملًا."),
    R9.gap("aed-v1.0:24350", "يبو", "SOURCE-GAP", "beverage غير مسمى؛ لا يُنتق اسم شراب عربي من الهيكل وحده."),
    R9.gap("aed-v1.0:24450", "يبز", "SOURCE-GAP", "جزء السفينة غير معين؛ لا معنى معجمي أدق ولا مقابل عربي مسمى."),
    R9.gap("aed-v1.0:24810", "يءم", "SOURCE-GAP", "الشجرة وخشبها لا يحملان اسم نوع محدد في الترجمة؛ لا يُنتق اسم عربي من الرسم وحده."),
    R9.terminal("aed-v1.0:25160", "∅", "OUT-OF-SCOPE", "صفة نسب وظيفية بمعنى belonging to في تركيب حرفي؛ لا مادة جذرية معجمية مستقلة في المدخل."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT


def round24_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    card = R23.round23_card(serial, rank, item, decision, matches)
    card = card.replace("ROUND23-COMPLETION", "ROUND24-COMPLETION")
    card = card.replace(
        f"round23-egyptian-rank={rank}/{CARD_COUNT}",
        f"round24-egyptian-rank={rank}/{CARD_COUNT}",
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
        raise SystemExit("Round-twenty-four marker already exists; append refused.")

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
        round24_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الرابعة والعشرون: استمرار المخزون المصري المسجل المفتوح (2026-08-24)", "",
        (
            "أُعيد فحص الآرامية أولًا فكان الطابور القصير الحي ذا المروحة غير "
            f"الفارغة صفرًا، فسُجل الانتقال المسمى `{TRANSITION}`. انتُقيت ثمانون "
            "بطاقة مصرية بدءًا من `WO-C-OPEN-COMP-01183` بقصر الهيكل ثم موضع "
            "اللقطة. استُبعد صف ḏ المؤجل. في كل بطاقة عُرضت إصابات AED كلها بلا "
            "حد، وكُتب وسم الطريق والرسم والمدخل المختار، وحُفظ الاختلاف "
            "والمتجانسات بلا محو."
        ), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-01183 إلى WO-C-OPEN-COMP-01222", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-01223 إلى WO-C-OPEN-COMP-01262", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([f"<!-- LANE-C-R24-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    states = dict(sorted(collections.Counter(item.state for item in DECISIONS).items()))
    verdicts = dict(sorted(collections.Counter(item.verdict for item in DECISIONS).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    now = datetime.now(ZoneInfo("Africa/Cairo")).strftime("%Y-%m-%d %H:%M:%S %z")
    now = now[:-2] + ":" + now[-2:]
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة الرابعة والعشرون: المسار C، الساميات والمصرية (2026-08-24)", "",
        f"- الوقت: {now}.",
        "- أُعيد فحص الساميات أولًا: المفتوح الآرامي القصير الحي ذو المروحة غير الفارغة=0؛ لم تُكرر بطاقة سامية.",
        f"- عند نفاد قصير الهيكل الآرامي سُجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل المفتوح.",
        "- الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01183` إلى `WO-C-OPEN-COMP-01222`.",
        "- الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-01223` إلى `WO-C-OPEN-COMP-01262`.",
        "- النموذج `WO-B-PROBE-001` مطبق في 80/80 بطاقة.",
        "- طُبقت قواعد AED الثلاث: كل الإصابات بلا حد؛ وسم الطريق والرسم والمدخل المختار مكتوبة؛ الاختلاف والمتجانسات محفوظة بلا محو.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(states, ensure_ascii=False, sort_keys=True)}؛ لا فجوة حُولت إلى نفي.",
        f"- الأحكام: {json.dumps(verdicts, ensure_ascii=False, sort_keys=True)}؛ لم يصدر حكم موجب في هذه النافذة.",
        "- المطابقة الدلالية `gr.w↔قر` بقيت `LAW-GAP`: السكون مباشر، لكن g المصرية ↔ ق العربية بلا صف مصري موقع.",
        "- الضمائر وأسماء الإشارة والاستفهام وصفات الملكية الوظيفية أُغلقت `OUT-OF-SCOPE` بلا افتعال جذر معجمي.",
        "- المداخل المجهولة أو المشكوكة بقيت `SOURCE-GAP`؛ ووسم القرض في `ybr` بقي `DIRECTIONAL-TRANSMISSION` بلا مانح سامي أو طريق مسمى.",
        "- صف ḏ المصري المؤجل بقي مستبعدًا، ولا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE24 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
        R23.R20.R10.append(EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian)
        R23.R20.R10.append(REPORT, f"{MARKER}:REPORT", report)
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
