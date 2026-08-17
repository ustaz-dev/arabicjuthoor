#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 11 completion cards.

Round ten was accepted and consolidated.  The short live-open Aramaic queue
is rechecked first; once its exhaustion is confirmed, this append-only round
continues the registered Egyptian queue in two forty-card batches beginning
at WO-C-OPEN-COMP-00286.  Every AED lookup is unlimited, its path and selected
inventory entry are named, and all disagreement and homographs are retained.
The deferred Egyptian ḏ row remains excluded.  No git, publication, or
shipping command is run.
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import harvest_lane_c_round9 as R9  # noqa: E402
import harvest_lane_c_round10 as R10  # noqa: E402
import search_arabic_root_senses as AR  # noqa: E402


ARAMAIC = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
EGYPTIAN = ROOT / "04-cross-linguistic" / "readings" / "egyptian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-C.md"
MARKER = "LANE-C-ROUND11-2026-08-17"
FIRST_SERIAL = 286
BATCH_SIZE = 40
CARD_COUNT = 80
TRANSITION = (
    "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
    "EGYPTIAN-RECORDED-OPEN-CONTINUED"
)


# Decisions are member-level.  A named gap is a completed reading, not a
# negative claim.  Grammatical formatives without a sourced lexical analysis
# are closed OUT-OF-SCOPE rather than being forced into an Arabic root.  The
# one positive in this window is limited to the explicitly preserved binary
# nucleus; the adjacent uncertain homograph does not inherit it.
DECISIONS: tuple[R9.Decision, ...] = (
    R9.gap("aed-v1.0:167750", "قر", "LAW-GAP",
           "be silent/quiet يلتقي قرار قرّ وسكونه، لكن g المصرية ↔ ق العربية لا يملك صفًا مصريًا موقعًا لهذه البطاقة.",
           sound="r↔ر هوية؛ الموضع g↔ق هو العائق، فلا يصدر الحكم من المروحة وحدها.",
           orbit="الدلالة مباشرة في السكون، وبقيت رجل الصوت وحدها ناقصة.",
           keywords="سكن|ساكن|القرار|الاستقرار"),
    R9.gap("aed-v1.0:172920", "ثي", "MORPHOLOGY-GAP",
           "go astray/transgress/damage لا يطابق مادة ثي، وتيه العربية يحتاج هاء غير موجودة في الرسم المصري."),
    R9.gap("aed-v1.0:175090", "ثوب", "SEMANTIC-GAP",
           "be shod/provide sandals لا يطابق حواس ثوب العربية؛ اللباس العام لا يساوي النعل."),
    R9.gap("aed-v1.0:177080", "ثس", "MORPHOLOGY-GAP",
           "sit يلتقي جلوسًا دلاليًا، لكن جيم جلس ولامه غير موجودتين في الرسم ṯs ولا في صرف مسمى."),
    R9.gap("aed-v1.0:179620", "دن", "SEMANTIC-GAP",
           "cut off/kill لا يطابق حواس دن/ضن العربية في المروحة المقروءة."),
    R9.gap("aed-v1.0:180350", "دح", "SEMANTIC-GAP",
           "hang down/be low لا يطابق حواس دح/ضح مباشرة، ولا تُستعار دلالة متجانس آخر."),
    R9.gap("aed-v1.0:180630", "دس", "SEMANTIC-GAP",
           "cut/be sharp لا يطابق حواس دس/دش/دص العربية بمدار مباشر."),
    R9.gap("aed-v1.0:400964", "روع", "SOURCE-GAP",
           "be afraid يلتقي روع العربية، لكن معنى AED نفسه موسوم بعلامة الشك؛ لا يصدر حكم موجب من مدخل غير مستقر."),
    R9.gap("aed-v1.0:450616", "ءو", "SEMANTIC-GAP",
           "be evil لا يطابق حواس ءو/يو العربية، ولا يُدخل سوء بصامت زائد من خارج الرسم."),
    R9.gap("aed-v1.0:600384", "قح", "SEMANTIC-GAP",
           "break stones as punishment لا يطابق حواس قح العربية في الشواهد المقروءة."),
    R9.gap("aed-v1.0:863852", "رم", "SEMANTIC-GAP",
           "be high/exalted في الأسماء السامية لا يطابق حواس رم العربية، ولا يكفي سياق الاسم الشخصي لإصدار جذر."),
    R9.terminal("aed-v1.0:10080", "∅", "OUT-OF-SCOPE",
                "ضمير لاحق للمثنى المتكلم؛ لا تحليل جذري معجمي منشور يجيز إدخاله في قياس الجذور."),
    R9.gap("aed-v1.0:34760", "علا", "LAW-GAP",
           "great one/elder/leader يلتقي العلو والرفعة، لكن ꜣ الثانية ↔ ل العربية بلا صف مصري موقع لهذا العضو.",
           sound="ꜥ↔ع ظاهر؛ ꜣ↔ل هو الموضع المانع.",
           orbit="الرفعة مدار دلالي مباشر، والصوت لم يكتمل.",
           keywords="الرفعة|الشرف|علا|علي"),
    R9.gap("aed-v1.0:44150", "وع", "MORPHOLOGY-GAP",
           "one/sole يقترح واحدًا، لكن حاء وحد وداله صامتان جذريان غير موجودين في wꜥ."),
    R9.gap("aed-v1.0:47280", "ور", "SEMANTIC-GAP",
           "great one/magnate لا يطابق حواس ور/ول العربية في المروحة."),
    R9.gap("aed-v1.0:47340", "ور", "SEMANTIC-GAP",
           "great one بوصفه ثورًا لا يطابق حواس ور العربية، ولا يرث معنى متجانس wr العام."),
    R9.gap("aed-v1.0:50060", "وش", "MORPHOLOGY-GAP",
           "push one's way through لا يطابق وش/وس؛ والوشج المحتمل يحتاج جيمًا غير موجودة."),
    R9.gap("aed-v1.0:51060", "وت", "SEMANTIC-GAP",
           "embalmed one لا يطابق حواس وت/وط العربية على الهيكل المعروض."),
    R9.gap("aed-v1.0:94720", "رن", "SEMANTIC-GAP",
           "young one of animals لا يطابق حواس رن/لن العربية، ولا يُدخل رضيع أو فصيل من خارج الرسم."),
    R9.gap("aed-v1.0:116000", "خفي", "SEMANTIC-GAP",
           "departed one/deceased يقترب من الخفاء والغياب، لكنه لا يثبت تسمية الميت في مادة خفي بشاهدين مباشرين."),
    R9.gap("aed-v1.0:140140", "شف", "SEMANTIC-GAP",
           "govern the Two Lands لا يطابق حواس شف/سب/سف العربية، والبادئة السببية لا تنشئ مادة سياسة."),
    R9.gap("aed-v1.0:155190", "شن", "SEMANTIC-GAP",
           "عدد ضخم غير محدد لا يطابق حواس شن/سن العربية ولا اسم عدد بعينه."),
    R9.terminal("aed-v1.0:170100", "∅", "OUT-OF-SCOPE",
                "ضمير لاحق غير شخصي بمعنى one؛ لا تحليل جذري معجمي منشور للّاصقة."),
    R9.gap("aed-v1.0:400101", "وع", "MORPHOLOGY-GAP",
           "one/sole one يقترح واحدًا، لكن صامتي ح ود غير محمولين في wꜥ."),
    R9.gap("aed-v1.0:401002", "ثنا", "SEMANTIC-GAP",
           "venerable one لا يساوي الثناء نفسه، ولا يثبت أن ṯn مشتق من مدار التعظيم العربي."),
    R9.gap("aed-v1.0:600041", "وع", "MORPHOLOGY-GAP",
           "one of many/sole يقترح واحدًا، لكن اختلاف عدد الصوامت يمنع الحكم."),
    R9.terminal("aed-v1.0:10060", "∅", "OUT-OF-SCOPE",
                "ضمير ملكية لاحق بعد المثنى؛ لا جذر معجمي مستقل في المصدر."),
    R9.terminal("aed-v1.0:10130", "∅", "OUT-OF-SCOPE",
                "ضمير لاحق للمخاطبين؛ لا تحليل جذري معجمي منشور."),
    R9.terminal("aed-v1.0:44000", "∅", "OUT-OF-SCOPE",
                "ضمير منفصل تابع للمتكلم؛ لا يُعامل مادة معجمية لمجرد شبه سطحي."),
    R9.terminal("aed-v1.0:46020", "∅", "OUT-OF-SCOPE",
                "ضمير المتكلمين؛ لا تحليل جذري معجمي منشور."),
    R9.terminal("aed-v1.0:127770", "∅", "OUT-OF-SCOPE",
                "ضمير الغائبة؛ لا جذر معجمي مستقل في المدخل."),
    R9.terminal("aed-v1.0:129490", "∅", "OUT-OF-SCOPE",
                "ضمير الغائب؛ لا جذر معجمي مستقل في المدخل."),
    R9.terminal("aed-v1.0:136190", "∅", "OUT-OF-SCOPE",
                "ضمير الغائبين؛ لا تحليل جذري معجمي منشور."),
    R9.terminal("aed-v1.0:147350", "∅", "OUT-OF-SCOPE",
                "ضمير غير شخصي؛ لا مادة جذرية مستقلة في المصدر."),
    R9.terminal("aed-v1.0:174900", "∅", "OUT-OF-SCOPE",
                "ضمير المخاطب المفرد؛ لا تحليل جذري معجمي منشور."),
    R9.terminal("aed-v1.0:175410", "∅", "OUT-OF-SCOPE",
                "ضمير المخاطبة المفردة؛ لا تحليل جذري معجمي منشور."),
    R9.terminal("aed-v1.0:175640", "∅", "OUT-OF-SCOPE",
                "ضمير المخاطبة المفردة ببديل كتابي؛ لا جذر معجمي مستقل."),
    R9.terminal("aed-v1.0:175650", "∅", "OUT-OF-SCOPE",
                "ضمير المخاطبين؛ لا تحليل جذري معجمي منشور."),
    R9.terminal("aed-v1.0:400960", "∅", "OUT-OF-SCOPE",
                "ضمير الغائبين؛ لا تحليل جذري معجمي منشور."),
    R9.terminal("aed-v1.0:600043", "∅", "OUT-OF-SCOPE",
                "أداة تنكير متولدة من one؛ البطاقة وظيفية ولا تدعي جذرًا معجميًا."),
    R9.terminal("aed-v1.0:30740", "∅", "OUT-OF-SCOPE",
                "اسم استفهام what؛ لا تحليل جذري معجمي منشور في AED."),
    R9.terminal("aed-v1.0:33490", "∅", "OUT-OF-SCOPE",
                "اسم استفهام which/where؛ لا جذر معجمي مستقل في المصدر."),
    R9.terminal("aed-v1.0:59750", "∅", "OUT-OF-SCOPE",
                "اسم استفهام who/what؛ لا تحليل جذري معجمي منشور."),
    R9.terminal("aed-v1.0:59880", "∅", "OUT-OF-SCOPE",
                "اسم إشارة للمفرد المذكر؛ لا مادة جذرية مستقلة في المدخل."),
    R9.terminal("aed-v1.0:59920", "∅", "OUT-OF-SCOPE",
                "اسم إشارة للمفرد المذكر؛ لا مادة جذرية مستقلة في المدخل."),
    R9.terminal("aed-v1.0:100160", "∅", "OUT-OF-SCOPE",
                "أداة تمنٍّ would that؛ لا تحليل جذري معجمي منشور."),
    R9.terminal("aed-v1.0:127760", "∅", "OUT-OF-SCOPE",
                "اسم استفهام who/what/which؛ لا جذر معجمي مستقل في المصدر."),
    R9.terminal("aed-v1.0:171730", "∅", "OUT-OF-SCOPE",
                "اسم إشارة للمفرد المؤنث؛ لا مادة جذرية مستقلة في المدخل."),
    R9.terminal("aed-v1.0:172360", "∅", "OUT-OF-SCOPE",
                "اسم إشارة للمفرد المؤنث؛ لا مادة جذرية مستقلة في المدخل."),
    R9.gap("aed-v1.0:7", "ءء", "SOURCE-GAP",
           "mound of ruins نفسه موسوم بعلامة الشك، ولا يُنتق معنى عربي لموافقة مدخل غير مستقر."),
    R9.gap("aed-v1.0:131", "ءم", "SEMANTIC-GAP",
           "mutilate/destroy لا يطابق حواس ءم/أم/لم/رم مباشرة."),
    R9.gap("aed-v1.0:156", "ءر", "SOURCE-GAP",
           "need/Bedrängnis معنى مشكوك في AED؛ لا يصدر مدار عربي من الاحتمال."),
    R9.gap("aed-v1.0:185", "ءح", "SEMANTIC-GAP",
           "field لا يطابق حواس ءح/أح/لح/رح، ولا يُدخل فلاح أو حقل من خارج الرسم."),
    R9.gap("aed-v1.0:203", "ءخ", "SEMANTIC-GAP",
           "akh-spirit/glorified deceased لا يطابق حواس ءخ/أخ/لخ/رخ العربية، ولا يكفي تشابه اسم الروح."),
    R9.gap("aed-v1.0:10270", "ءب", "SEMANTIC-GAP",
           "fingernail لا يطابق حواس ءب/أب/لب/رب، ولا يُدخل ظفر من خارج الرسم."),
    R9.gap("aed-v1.0:21280", "يي", "SOURCE-GAP",
           "to agree معنى AED محاط بعلامة الشك؛ لا يصدر حكم من مدخل غير مستقر."),
    R9.gap("aed-v1.0:21470", "يع", "SEMANTIC-GAP",
           "bowl/basin for washing لا يطابق حواس يع/ءع، ولا يُدخل وعاء بصامت غير محمول."),
    R9.gap("aed-v1.0:21950", "يو", "SOURCE-GAP",
           "livestock معنى مشكوك في AED؛ لا يثبت مدار عربي مستقل."),
    R9.gap("aed-v1.0:22000", "يو", "SEMANTIC-GAP",
           "wail لا يطابق حواس يو/ءو، ولا يُدخل عوى بعين غير موجودة."),
    R9.gap("aed-v1.0:23370", "يب", "SEMANTIC-GAP",
           "wish/suppose لا يطابق حواس يب/ءب العربية بمدار مباشر."),
    R9.gap("aed-v1.0:24670", "يم", "SEMANTIC-GAP",
           "side/side of ribs لا يطابق حواس يم/ءم، ولا يكفي قرب اليمين بلا نون."),
    R9.gap("aed-v1.0:24720", "يم", "SEMANTIC-GAP",
           "Haut/skin لا يطابق حواس يم/ءم؛ وحُفظ نقص الترجمة الإنجليزية بلا اختراع معنى آخر."),
    R9.terminal("aed-v1.0:28170", "∅", "OUT-OF-SCOPE",
                "أداة توكيد لاحقة؛ لا تحليل جذري معجمي منشور."),
    R9.gap("aed-v1.0:30430", "يح", "SOURCE-GAP",
           "المدخل لا يسمي نوع الشجرة ولا معنى معجميًا أدق؛ لا يُنتق جذر عربي من تسمية مجهولة."),
    R9.gap("aed-v1.0:33820", "يد", "SEMANTIC-GAP",
           "bull لا يطابق حواس يد/يض/ءد/ءض، ولا يرث حكم عضو hand المتجانس."),
    R9.gap("aed-v1.0:34800", "علا", "SEMANTIC-GAP",
           "column/pillar/beam لا يساوي العلو نفسه ولا يسمي جسمًا مطابقًا في مادة علا."),
    R9.gap("aed-v1.0:35040", "زا", "SEMANTIC-GAP",
           "swelling/tumor لا يطابق حواس زا/زر/سا/سر العربية مباشرة."),
    R9.gap("aed-v1.0:36330", "عب", "NAME-ROOT-OPEN",
           "Ab اسم أو تسمية محتملة لكلب صيد؛ لا يُرد اسم العلم إلى جذر بلا اشتقاق منشور."),
    R9.gap("aed-v1.0:38050", "عن", "SEMANTIC-GAP",
           "again/already لا يطابق حواس عن/ضن/غن العربية في المروحة."),
    R9.gap("aed-v1.0:39180", "عر", "SEMANTIC-GAP",
           "pebble/stone لا يطابق حواس عر/عل/ضر/غر، ولا يُدخل حجر من خارج الرسم."),
    R9.gap("aed-v1.0:40730", "عخ", "SOURCE-GAP",
           "نوع الطائر غير مسمى في AED؛ لا يُنتق مقابل عربي من تصنيف عام مجهول."),
    R9.pos("aed-v1.0:40910", "عشا", "NUCLEUS-TRACE",
           "العشاء|الطعام|طعام",
           "ꜥ↔ع هوية حلقية، وš↔ش هوية صفيرية؛ الحكم للنواة الثنائية ꜥ-š ولا يفترض صامتًا مصريًا للألف العربية.",
           "meal هو العشاء: الطعام بعينه وخلاف الغداء في شاهدين عربيين مستقلين.",
           "الصلة للنواة والمعنى المباشر فقط؛ لا يرثها متجانس الثمرة المشكوك المجاور.",
           zero="حُفظ الرسم ꜥš كاملًا؛ قُرئت عشا على درجة النواة عش، والألف العربية حدث الدرجة المسجل لا صامت مصري ساقط."),
    R9.gap("aed-v1.0:40960", "عشا", "SOURCE-GAP",
           "fruit/food معنى مشكوك وغير معين؛ لا يرث موجب meal المجاور رغم اتحاد الرسم ꜥš."),
    R9.gap("aed-v1.0:42430", "وء", "SOURCE-GAP",
           "conspiracy/illoyalty كلاهما محاط بعلامة الشك؛ لا يصدر مدار من معنى غير مستقر."),
    R9.gap("aed-v1.0:42641", "ور", "SEMANTIC-GAP",
           "far/remote لا يطابق حواس ور/ول مباشرة؛ ووراء يحتاج بناءً ورجلًا لينة غير مثبتين لهذا العضو."),
    R9.gap("aed-v1.0:44010", "وي", "SEMANTIC-GAP",
           "mummy case لا يطابق حواس وي/وء العربية ولا يُدخل وعاء من خارج الرسم."),
    R9.gap("aed-v1.0:47290", "ور", "SEMANTIC-GAP",
           "greatness لا يطابق حواس ور/ول العربية على الهيكل الثنائي."),
    R9.gap("aed-v1.0:47370", "ور", "SEMANTIC-GAP",
           "fledgling لا يطابق حواس ور/ول، ولا يرث معنى متجانسات wr الدالة على العظمة."),
    R9.gap("aed-v1.0:49430", "وس", "SEMANTIC-GAP",
           "height of a pyramid مصطلح رياضي لا يطابق حواس وس/وش/وص العربية مباشرة."),
    R9.gap("aed-v1.0:50950", "وت", "SOURCE-GAP",
           "الاسم ومعنى roaring كلاهما غير متعينين في AED؛ لا يصدر مدار عربي من الاحتمال."),
)


EXPECTED_IDS = tuple(item.member_id for item in DECISIONS)
assert len(DECISIONS) == CARD_COUNT


def round11_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    """Render with complete AED sets and retain witnesses for positives."""
    original_renderer = R9.render_aed_hits
    original_limit = R9.MAX_CARD_BYTES
    R9.render_aed_hits = R10.compact_aed_hits
    R9.MAX_CARD_BYTES = 12 * 1024
    try:
        card = R9.render_egyptian_card(serial, rank, item, decision, matches)
    finally:
        R9.render_aed_hits = original_renderer
        R9.MAX_CARD_BYTES = original_limit
    card = card.replace("ROUND9-COMPLETION", "ROUND11-COMPLETION")
    card = card.replace(
        f"round9-egyptian-rank={rank}/40",
        f"round11-egyptian-rank={rank}/{CARD_COUNT}",
    )
    if decision.verdict not in R9.POSITIVE:
        root = AR.normalize_root(decision.candidate)
        arabic_count = len(matches.get(root, []))
        card = re.sub(
            r"(?m)^- مسح المعاني العربية:.*$",
            (f"- مسح المعاني العربية: قُرئت {arabic_count} نتيجة للجذر `{root}` كاملةً "
             "بما يكافئ `--max-chars 0`؛ لم يثبت منها مدار العضو، فلم تُنسخ شواهد غير عاملة."),
            card,
        )
        card = re.sub(
            r"(?m)^- الحدث[^\n]*$",
            "- الحدث المجمّد: عُرضت درجات المرشح للفحص؛ لا تعمل مع بقاء البطاقة غير موجبة.",
            card,
        )
    elif decision.member_id == "aed-v1.0:40910":
        # The shared witness helper indexes a de-vocalized string and can put
        # the display window too far from a hit in very long vocalized entries.
        # Keep the same complete five-result scan, but pin the two independent
        # working excerpts to the exact food sense that licenses this positive.
        card = re.sub(
            r"(?m)^- مسح المعاني العربية:.*$",
            ("- مسح المعاني العربية: قُرئت 5 نتائج للجذر `عشا` كاملةً بما يكافئ "
             "`--max-chars 0`؛ قال لسان العرب لابن منظور: «عَشِيَ الرجلُ يَعْشَى "
             "وتَعَشَّى: أكلَ العَشاء؛ وهو الطعام الذي يُؤكَلُ بعد العِشاء»؛ وقال "
             "تاج اللغة وصحاح العربية للجوهري: «العشاء بالفتح والمد: الطعام بعينه، "
             "وهو خلاف الغداء»."),
            card,
        )
    size = len(card.encode("utf-8"))
    assert size <= original_limit, (
        f"Oversize WO-C-OPEN-COMP-{serial:05d}: {size} bytes"
    )
    return card


def render_appendices() -> tuple[str, str, dict]:
    aramaic_text = ARAMAIC.read_text(encoding="utf-8")
    egyptian_text = EGYPTIAN.read_text(encoding="utf-8")
    report_text = REPORT.read_text(encoding="utf-8")
    if MARKER in egyptian_text or MARKER in report_text:
        raise SystemExit("Round-eleven marker already exists; append refused.")

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
        for item in DECISIONS if item.candidate not in {"∅", ""}
    }
    matches = AR.matches_for_roots(AR.DEFAULT_RESOURCES, roots, None)
    cards = [
        round11_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, DECISIONS), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة الحادية عشرة: استمرار المخزون المصري المسجل المفتوح (2026-08-17)", "",
        ("أُعيد فحص الآرامية أولًا فكان الطابور القصير الحي ذا المروحة غير الفارغة صفرًا. "
         f"لذلك سُجل الانتقال المسمى `{TRANSITION}`. انتُقيت البطاقات المصرية التالية "
         "بدءًا من `WO-C-OPEN-COMP-00286` بقصر الهيكل ثم موضع اللقطة. استُبعد صف ḏ "
         "المؤجل. في كل بطاقة عُرضت إصابات AED كلها بلا حد، وكُتب وسم الطريق والرسم "
         "والمدخل المختار، وحُفظ الاختلاف والمتجانسات بلا محو."), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-00286 إلى WO-C-OPEN-COMP-00325", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-00326 إلى WO-C-OPEN-COMP-00365", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([f"<!-- LANE-C-R11-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    state_counts = dict(sorted(collections.Counter(item.state for item in DECISIONS).items()))
    verdict_counts = dict(sorted(collections.Counter(item.verdict for item in DECISIONS).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة الحادية عشرة — المسار C (2026-08-17)", "",
        "- أُعيد فحص الآرامية أولًا: المفتوح القصير الحي ذو المروحة غير الفارغة=0؛ لم تُكرر بطاقة آرامية.",
        f"- سُجل الانتقال المسمى `{TRANSITION}` إلى المصري المسجل.",
        "- كُتبت الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00286` إلى `WO-C-OPEN-COMP-00325`.",
        "- كُتبت الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00326` إلى `WO-C-OPEN-COMP-00365`.",
        "- طُبقت قواعد AED الثلاث: كل الإصابات بلا حد؛ وسم الطريق والرسم والمدخل المختار مكتوبة؛ الاختلاف والمتجانسات محفوظة بلا محو.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(state_counts, ensure_ascii=False, sort_keys=True)}؛ لا فجوة حُولت إلى نفي.",
        f"- الأحكام: {json.dumps(verdict_counts, ensure_ascii=False, sort_keys=True)}؛ موجب النواة الوحيد `ꜥš↔عشا` له شاهدان عربيان وحدث مجمد، ولم يرثه متجانس الثمرة.",
        "- صف ḏ مؤجل بقرار المؤلف؛ استُبعد من الانتقاء وبقيت بطاقاته على حالها.",
        "- لا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE11 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
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
        "states": state_counts,
        "verdicts": verdict_counts,
        "max_card_bytes": max(len(card.encode("utf-8")) for card in cards),
    }
    return "\n".join(body).rstrip() + "\n", report, diagnostics


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
        R10.append(EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian)
        R10.append(REPORT, f"{MARKER}:REPORT", report)
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
