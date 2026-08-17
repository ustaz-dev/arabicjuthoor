#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Append lane C round 10 completion cards.

Round nine exhausted the short live-open Aramaic queue.  This append-only
round confirms that exhaustion, records the named transition, and writes two
forty-card batches from the registered Egyptian queue.  Every AED lookup is
unlimited, every hit is rendered, the lookup path and selected entry are
named, and homographic disagreement is retained.  The deferred Egyptian ḏ
row remains excluded.  No git, publication, or shipping command is run.
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
import search_arabic_root_senses as AR  # noqa: E402


ARAMAIC = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
EGYPTIAN = ROOT / "04-cross-linguistic" / "readings" / "egyptian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-C.md"
MARKER = "LANE-C-ROUND10-2026-08-17"
FIRST_SERIAL = 206
BATCH_SIZE = 40
CARD_COUNT = 80


# These are member-level readings, not family inheritance.  A gap remains a
# completed review card with its exact blocker named; it is not a negative.
SPECS: tuple[tuple[str, str, str, str], ...] = (
    ("aed-v1.0:97770", "هي", "SEMANTIC-GAP",
     "husband لا يطابق حواس هي/حي العربية في المروحة المقروءة."),
    ("aed-v1.0:114450", "خي", "SEMANTIC-GAP",
     "child لا يطابق حواس خي العربية، ولا يُنقل إليه معنى متجانس ḫy آخر."),
    ("aed-v1.0:116920", "خم", "SEMANTIC-GAP",
     "ignorant man لا يطابق حواس خم العربية بعد فصل shrine والجفاف وبقية المتجانسات."),
    ("aed-v1.0:125040", "زت", "SEMANTIC-GAP",
     "woman لا يطابق حواس زت/ست العربية، وتاء التأنيث المصرية لا تنشئ جذرًا عربيًا بنفسها."),
    ("aed-v1.0:125510", "زء", "SEMANTIC-GAP",
     "son/grandson لا يطابق حواس زء/زا/زر في المروحة، ولا يرث معنى protection أو land."),
    ("aed-v1.0:136230", "سن", "SEMANTIC-GAP",
     "brother لا يطابق حواس سن/شن/صن العربية، وفُصل عن smell وassociate ومتجانسات sn."),
    ("aed-v1.0:152680", "شو", "SEMANTIC-GAP",
     "needy man لا يطابق حواس شو/سو، ولا يرث معنى sunlight أو blank papyrus."),
    ("aed-v1.0:41180", "عق", "SEMANTIC-GAP",
     "enter وusher in وset لا تطابق حواس عق العربية في الشواهد المقروءة."),
    ("aed-v1.0:49060", "وخ", "SEMANTIC-GAP",
     "darkness/night لا يطابق حواس وخ العربية، مع فصل الفعل والإله والعلامة."),
    ("aed-v1.0:52890", "بء", "SEMANTIC-GAP",
     "hack up the earth/open up لا يطابق حواس بء/با/بل/بر على الهيكل المعروض بلا صامت زائد."),
    ("aed-v1.0:58710", "بت", "SEMANTIC-GAP",
     "heaven(s) لا يطابق حواس بت/بط/فت/فط، ولا يُستعار معنى اسم الإله المتجانس."),
    ("aed-v1.0:69000", "مو", "LAW-GAP",
     "water يلتقي ماء دلاليًا، لكن ماء خارج سطح المروحة ومسار w المصري إلى همزته النهائية غير موقع لهذه البطاقة."),
    ("aed-v1.0:73970", "مح", "SOURCE-GAP",
     "plot of land نفسه موسوم بعلامة الشك، ولا شاهدان عربيان مباشران في مادة مح."),
    ("aed-v1.0:79020", "نت", "SEMANTIC-GAP",
     "water/flood لا يطابق حواس نت/نط، ولا تكفي تاء التأنيث لبناء نطف أو نهر."),
    ("aed-v1.0:84620", "نن", "SEMANTIC-GAP",
     "flood water لا يطابق مادة نن العربية، ولم يُدخل صامت من خارج الرسم."),
    ("aed-v1.0:84930", "نو", "SEMANTIC-GAP",
     "water/ocean/Nile لا يطابق حواس نو في المروحة، ولا يرث حكم mw أو n.t."),
    ("aed-v1.0:89210", "نك", "SEMANTIC-GAP",
     "اسم المعاقِب/الساعة السابعة وربة الساعة لا يطابق حواس نك العربية."),
    ("aed-v1.0:99260", "هه", "SEMANTIC-GAP",
     "blast/heat of fire لا يطابق حواس هه/هح/حه/حح بشاهدين عربيين مباشرين."),
    ("aed-v1.0:113020", "خت", "SEMANTIC-GAP",
     "fire/flame لا يطابق حواس خت/خط، ولم تُستعمل حرارة متجانس آخر بدل معنى العضو."),
    ("aed-v1.0:114480", "خي", "SEMANTIC-GAP",
     "high-lying land لا يطابق حواس خي العربية، وفُصل عن child وبقية ḫy."),
    ("aed-v1.0:121220", "خت", "SOURCE-GAP",
     "administrative unit/land register معنى محاط بالشك ولا يملك مقابلًا عربيًا مباشرًا في خت/خط."),
    ("aed-v1.0:144360", "زش", "SEMANTIC-GAP",
     "marsh land/pond/nest لا يطابق حواس زش/زس/سش/سس، مع فصل writing وopen وبقية zš."),
    ("aed-v1.0:152290", "شع", "SEMANTIC-GAP",
     "parcel of land المشتق من cut off لا يطابق حواس شع العربية بوصفه اسم قطعة أرض."),
    ("aed-v1.0:152750", "شو", "SEMANTIC-GAP",
     "sunlight/sun لا يطابق حواس شو/سو، وفُصل عن needy man وprotection وبقية šw."),
    ("aed-v1.0:128", "ءم", "SEMANTIC-GAP",
     "burn/burn up لا يطابق حواس ءم/أم/لم/رم في المروحة بلا تحويل حلقي جديد."),
    ("aed-v1.0:168", "اه", "SEMANTIC-GAP",
     "be miserable/make miserable لا يطابق حواس أه/أح/له/لح مباشرة."),
    ("aed-v1.0:200", "اخ", "SEMANTIC-GAP",
     "glorious/beneficial/useful لا يطابق حواس أخ/لخ/رخ، ولا يورث معنى الاسم المتجانس."),
    ("aed-v1.0:266", "اس", "SEMANTIC-GAP",
     "rush/make rush لا يطابق حواس أس/أش/أص في الشواهد العربية المقروءة."),
    ("aed-v1.0:290", "اق", "SEMANTIC-GAP",
     "perish/come to naught لا يطابق حواس أق/لق/رق، ولم يُضف صامت للفناء أو الهلاك."),
    ("aed-v1.0:342", "اد", "SOURCE-GAP",
     "aggressive/angry لا يملك شاهدين عربيين مباشرين في مادة أد يثبتان المدار نفسه."),
    ("aed-v1.0:401", "اك", "SEMANTIC-GAP",
     "bent/bend the elbow لا يطابق حواس أك/لك/رك على الهيكل الثنائي المعروض."),
    ("aed-v1.0:23280", "يب", "SOURCE-GAP",
     "conceal/take in كلاهما في AED بعلامة الشك؛ لا يصدر مدار من معنى غير مستقر."),
    ("aed-v1.0:24070", "يب", "SEMANTIC-GAP",
     "count/assess/be cognizant لا يطابق حواس يب/يف، ولا يُدخل حاسب من خارج الرسم."),
    ("aed-v1.0:30460", "يح", "SOURCE-GAP",
     "weep/sleep احتمالان مشكوكان في المدخل نفسه؛ لم يُنتق أحدهما لموافقة مرشح عربي."),
    ("aed-v1.0:36310", "عب", "SEMANTIC-GAP",
     "purify/be pure لا يطابق حواس عب/ضب/غب العربية في المروحة المقروءة."),
    ("aed-v1.0:44850", "وو", "SOURCE-GAP",
     "sing/make music كلاهما مشكوك في AED، فلا مدار قطعي لمادة وو."),
    ("aed-v1.0:46060", "ون", "SEMANTIC-GAP",
     "open لا يطابق حواس ون العربية، مع فصل stripped/bald وبقية متجانسات wn."),
    ("aed-v1.0:46100", "ون", "SEMANTIC-GAP",
     "be stripped/bald لا يطابق حواس ون، ولا يرث معنى open من العضو المجاور."),
    ("aed-v1.0:49050", "وخ", "SEMANTIC-GAP",
     "be dark لا يطابق حواس وخ، وبقي مستقلًا عن اسم darkness رغم الاشتقاق المصري."),
    ("aed-v1.0:49420", "وس", "SEMANTIC-GAP",
     "make stop/want/lack حزمة لا يطابقها مدار واحد في حواس وس/وش/وص العربية."),
    ("aed-v1.0:50040", "وش", "SEMANTIC-GAP",
     "destroyed/destroy/empty لا يطابق حواس وش/وس مباشرة، ولم يُبن حكم من القبطي غير المحمول."),
    ("aed-v1.0:56280", "بر", "SEMANTIC-GAP",
     "see لا يطابق حواس بر/بل العربية، ولا يرث معنى متجانسات br الأخرى."),
    ("aed-v1.0:56800", "بح", "SEMANTIC-GAP",
     "compulsory labor/being obliged لا يطابق حواس بح العربية على الهيكل الثنائي."),
    ("aed-v1.0:57110", "بخ", "SEMANTIC-GAP",
     "give birth/bring forth لا يطابق حواس بخ/بح بلا صامت أو مسار صرفي إضافي."),
    ("aed-v1.0:57670", "بق", "SEMANTIC-GAP",
     "hostile/recalcitrant لا يطابق حواس بق العربية في الشواهد المقروءة."),
    ("aed-v1.0:63810", "فن", "SEMANTIC-GAP",
     "weak لا يطابق حواس فن العربية، ولا يُدخل وهن من خارج الرسم."),
    ("aed-v1.0:64060", "فك", "SEMANTIC-GAP",
     "empty/wasted/bare لا يطابق حواس فك العربية مباشرة."),
    ("aed-v1.0:67760", "مي", "SEMANTIC-GAP",
     "bring لا يطابق حواس مي/مء، ولا تُخترع همزة أو جذر إتيان خارج الرسم."),
    ("aed-v1.0:69660", "من", "SEMANTIC-GAP",
     "ill/suffer/injure لا يطابق حواس من، وفُصل عن sick man وبقية mn."),
    ("aed-v1.0:74700", "مز", "SEMANTIC-GAP",
     "bring/go/betake oneself لا يطابق حواس مز/مس على مدار عربي مباشر."),
    ("aed-v1.0:80760", "نو", "SEMANTIC-GAP",
     "weak لا يطابق حواس نو، ولا يرث معنى water من متجانس nw."),
    ("aed-v1.0:95620", "رخ", "SEMANTIC-GAP",
     "know/learn لا يطابق حواس رخ/لخ، وفُصل عن wise man المشتق ومتجانسات rḫ."),
    ("aed-v1.0:97810", "هي", "SEMANTIC-GAP",
     "fasten/wind the tow-rope لا يطابق حواس هي/حي على الهيكل الثنائي."),
    ("aed-v1.0:98370", "حم", "LAW-GAP",
     "burn/be hot يلتقي حَمَّ وحرارته دلاليًا، لكن h المصرية ↔ ح العربية بلا صف مصري موقع لهذه البطاقة."),
    ("aed-v1.0:100180", "حا", "SEMANTIC-GAP",
     "go ashore/run aground لا يطابق حواس حا/حل/حر، مع فصل الاصطلاح الملاحي عن الشاطئ العربي غير المهيكل."),
    ("aed-v1.0:105920", "حن", "SEMANTIC-GAP",
     "fresh/provide with life لا يطابق حواس حن العربية مباشرة."),
    ("aed-v1.0:107560", "حر", "MORPHOLOGY-GAP",
     "ready/make ready يقترب من حضر، لكن الضاد صامت جذري غير موجود في الرسم المصري."),
    ("aed-v1.0:109690", "حس", "SEMANTIC-GAP",
     "be cold لا يطابق حواس حس/حش/حص في الشواهد العربية المقروءة."),
    ("aed-v1.0:113140", "خا", "SEMANTIC-GAP",
     "be young لا يطابق حواس خا/خل/خر، ولا يُدخل شاب أو حدث من خارج الرسم."),
    ("aed-v1.0:116580", "خف", "SEMANTIC-GAP",
     "see/perceive لا يطابق حواس خف العربية، وفُصل عن الخفاء لأنه ضد الإدراك الظاهر لا معناه."),
    ("aed-v1.0:116860", "خم", "SEMANTIC-GAP",
     "dry as dust لا يطابق حواس خم العربية، ولا يرث معنى ignorant أو shrine."),
    ("aed-v1.0:116910", "خم", "SEMANTIC-GAP",
     "not know/be ignorant لا يطابق حواس خم، وفُصل عن اسم ignorant man وبقية ḫm."),
    ("aed-v1.0:122400", "خا", "SEMANTIC-GAP",
     "break up/batter لا يطابق حواس خا/خل/خر أو حا/حل/حر بلا صامت زائد."),
    ("aed-v1.0:123060", "خن", "SOURCE-GAP",
     "trouble/swollen belly معنى طبي ضيق لا يملك شاهدين عربيين مباشرين في خن/حن."),
    ("aed-v1.0:127740", "زي", "SEMANTIC-GAP",
     "go لا يطابق حواس زي/سي/زء/سء، ولا تُدخل مادة سير من خارج الرسم."),
    ("aed-v1.0:133390", "زف", "SEMANTIC-GAP",
     "mild/merciful لا يطابق حواس زف/سف، وفُصل عن knife وcut up ومتجانسات zf."),
    ("aed-v1.0:133410", "زف", "SEMANTIC-GAP",
     "cut up/slaughter لا يطابق حواس زف/سف مباشرة، ولا يرث معنى knife وحده حكمًا."),
    ("aed-v1.0:136070", "زن", "SEMANTIC-GAP",
     "open لا يطابق حواس زن/سن، وفُصل عن plowshare وedge وبقية zn."),
    ("aed-v1.0:143720", "سس", "SEMANTIC-GAP",
     "burn لا يطابق حواس سس/سش/سص/شش، ولا يرث معنى net المتجانس."),
    ("aed-v1.0:144300", "زش", "SEMANTIC-GAP",
     "open لا يطابق حواس زش/زس/سش/سس، وفُصل عن writing وthreshold وspread."),
    ("aed-v1.0:147080", "شق", "DIRECTIONAL-TRANSMISSION",
     "open a way/break a trail يلتقي شق الطريق، لكن AED يوسمه Semitic loan word بعلامة السؤال؛ يلزم تثبيت المصدر والاتجاه قبل حكم النقل."),
    ("aed-v1.0:149540", "سد", "SEMANTIC-GAP",
     "be clothed/adorned لا يطابق حواس سد/شد/صد، ولا يرث معنى tail أو column."),
    ("aed-v1.0:151200", "شا", "SEMANTIC-GAP",
     "go aground في الملاحة لا يطابق حواس شا/شل/شر، وفُصل عن marsh وtree وcommand."),
    ("aed-v1.0:152200", "شع", "SEMANTIC-GAP",
     "cut/cut off لا يطابق حواس شع/شض/شغ أو سع/سض/سغ بمدار عربي مباشر."),
    ("aed-v1.0:153620", "شف", "SEMANTIC-GAP",
     "blind/to blind لا يطابق حواس شف/شب/سب/سف، ولا يُقلب معنى شاف إلى ضده."),
    ("aed-v1.0:153630", "سف", "SEMANTIC-GAP",
     "flow out/depart لا يطابق حواس سف/شف/شب/سب، وفُصل عن blind وleap."),
    ("aed-v1.0:160420", "قف", "SEMANTIC-GAP",
     "be agape/astonished لا يطابق حواس قف العربية، ولا يكفي الوقوف من الدهشة دون صامت الواو."),
    ("aed-v1.0:162310", "قق", "SEMANTIC-GAP",
     "eat لا يطابق حواس قق العربية، وفُصل عن nuts وpeel وبقية qq."),
    ("aed-v1.0:162850", "كء", "SEMANTIC-GAP",
     "say/name لا يطابق حواس كء/كا/كل/كر، ولا تُبنى قال بإدخال واو ولام خارج الرسم."),
    ("aed-v1.0:165220", "خب", "SEMANTIC-GAP",
     "harm/be violent/roar لا يطابق حواس خب/حب مباشرة، وفُصل عن لقب Seth والمادة النباتية."),
)


EXPECTED_IDS = tuple(member_id for member_id, _, _, _ in SPECS)


def decisions() -> tuple[R9.Decision, ...]:
    return tuple(
        R9.gap(member_id, candidate, state, reason)
        for member_id, candidate, state, reason in SPECS
    )


def compact_aed_hits(hits: list[dict]) -> str:
    """Name every AED hit while keeping dense homograph sets under 5 KiB."""
    return "؛ ".join(
        f"`{entry.get('id')}:{entry.get('translit')}` «"
        f"{R9.clean(entry.get('en') or entry.get('de') or '[∅]', 12)}»"
        for entry in hits
    ) or "لا إصابات"


def round10_card(serial: int, rank: int, item: dict, decision: R9.Decision,
                 matches: dict[str, list[dict]]) -> str:
    original_renderer = R9.render_aed_hits
    original_limit = R9.MAX_CARD_BYTES
    R9.render_aed_hits = compact_aed_hits
    R9.MAX_CARD_BYTES = 12 * 1024
    try:
        card = R9.render_egyptian_card(serial, rank, item, decision, matches)
    finally:
        R9.render_aed_hits = original_renderer
        R9.MAX_CARD_BYTES = original_limit
    card = card.replace("ROUND9-COMPLETION", "ROUND10-COMPLETION")
    card = card.replace(
        f"round9-egyptian-rank={rank}/40",
        f"round10-egyptian-rank={rank}/{CARD_COUNT}",
    )
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
    size = len(card.encode("utf-8"))
    assert size <= original_limit, f"Oversize WO-C-OPEN-COMP-{serial:05d}: {size} bytes"
    return card


def render_appendices() -> tuple[str, str, dict]:
    aramaic_text = ARAMAIC.read_text(encoding="utf-8")
    egyptian_text = EGYPTIAN.read_text(encoding="utf-8")
    report_text = REPORT.read_text(encoding="utf-8")
    if MARKER in egyptian_text or MARKER in report_text:
        raise SystemExit("Round-ten marker already exists; append refused.")

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

    decided = decisions()
    roots = {AR.normalize_root(item.candidate) for item in decided}
    matches = AR.matches_for_roots(AR.DEFAULT_RESOURCES, roots, None)
    cards = [
        round10_card(FIRST_SERIAL + rank - 1, rank, item, decision, matches)
        for rank, (item, decision) in enumerate(zip(selected, decided), 1)
    ]

    body = [
        f"<!-- {MARKER}:EGYPTIAN:START -->", "",
        "## الجولة العاشرة: استمرار المخزون المصري المسجل المفتوح (2026-08-17)", "",
        ("أُعيد فحص الآرامية أولًا فكان الطابور القصير الحي ذا المروحة غير الفارغة صفرًا. "
         "لذلك سُجل الانتقال `ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> "
         "EGYPTIAN-RECORDED-OPEN-CONTINUED`. انتُقيت البطاقات المصرية التالية بعد "
         "`WO-C-OPEN-COMP-00205` بقصر الهيكل ثم موضع اللقطة. استُبعد صف ḏ المؤجل. "
         "في كل بطاقة عُرضت إصابات AED كلها بلا حد، وكُتب وسم الطريق والمدخل المختار، "
         "وحُفظ الاختلاف والمتجانسات بلا محو."), "",
        "### الدفعة الأولى: WO-C-OPEN-COMP-00206 إلى WO-C-OPEN-COMP-00245", "",
    ]
    for rank, card in enumerate(cards, 1):
        if rank == BATCH_SIZE + 1:
            body.extend([
                "### الدفعة الثانية: WO-C-OPEN-COMP-00246 إلى WO-C-OPEN-COMP-00285", "",
            ])
        body.extend([card.rstrip(), ""])
        if rank % 5 == 0:
            body.extend([f"<!-- LANE-C-R10-EGYPTIAN-CHUNK-{rank:03d}:END -->", ""])
    body.append(f"<!-- {MARKER}:EGYPTIAN:END -->")

    state_counts = dict(sorted(collections.Counter(item.state for item in decided).items()))
    last_serial = FIRST_SERIAL + CARD_COUNT - 1
    report = "\n".join([
        "", f"<!-- {MARKER}:REPORT -->",
        "## الجولة العاشرة — المسار C (2026-08-17)", "",
        "- أُعيد فحص الآرامية أولًا: المفتوح القصير الحي ذو المروحة غير الفارغة=0؛ لم تُكرر بطاقة آرامية.",
        "- سُجل الانتقال `ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> EGYPTIAN-RECORDED-OPEN-CONTINUED`.",
        "- كُتبت الدفعة الأولى: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00206` إلى `WO-C-OPEN-COMP-00245`.",
        "- كُتبت الدفعة الثانية: 40 بطاقة مصرية من `WO-C-OPEN-COMP-00246` إلى `WO-C-OPEN-COMP-00285`.",
        "- طُبقت قواعد AED الثلاث: كل الإصابات بلا حد؛ وسم الطريق والرسم والمدخل المختار مكتوبة؛ الاختلاف والمتجانسات محفوظة بلا محو.",
        f"- حالات الإغلاق بعد القراءة: {json.dumps(state_counts, ensure_ascii=False, sort_keys=True)}؛ لا فجوة حُولت إلى نفي.",
        "- صف ḏ مؤجل بقرار المؤلف؛ استُبعد من الانتقاء وبقيت بطاقاته على حالها.",
        "- لا ship ولا commit ولا stage ولا تحديث مشتقات نشر.", "",
        f"LANE-C DONE10 {CARD_COUNT} WO-C-OPEN-COMP-{last_serial:05d}",
    ]) + "\n"

    diagnostics = {
        "aramaic_live_open": len(aramaic_queue),
        "transition": "ARAMAIC-SHORT-LIVE-OPEN-EXHAUSTED -> EGYPTIAN-RECORDED-OPEN-CONTINUED",
        "egyptian_queue_before": len(queue),
        "batch_1": BATCH_SIZE,
        "batch_2": CARD_COUNT - BATCH_SIZE,
        "total_cards": CARD_COUNT,
        "first_card": f"WO-C-OPEN-COMP-{FIRST_SERIAL:05d}",
        "last_card": f"WO-C-OPEN-COMP-{last_serial:05d}",
        "states": state_counts,
        "max_card_bytes": max(len(card.encode("utf-8")) for card in cards),
    }
    return "\n".join(body).rstrip() + "\n", report, diagnostics


def append(path: Path, marker: str, payload: str) -> None:
    current = path.read_text(encoding="utf-8")
    if marker in current:
        raise SystemExit(f"Marker appeared during render in {path}; append refused.")
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        if not current.endswith("\n"):
            handle.write("\n")
        handle.write("\n" + payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--show", type=int, choices=range(FIRST_SERIAL, FIRST_SERIAL + CARD_COUNT))
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    egyptian, report, diagnostics = render_appendices()
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    if args.show:
        card_id = f"WO-C-OPEN-COMP-{args.show:05d}"
        match = re.search(rf"(?ms)^### {re.escape(card_id)}:.*?(?=^### |^<!-- |\Z)", egyptian)
        assert match
        print("\n" + match.group().rstrip())
    if args.apply:
        append(EGYPTIAN, f"{MARKER}:EGYPTIAN", egyptian)
        append(REPORT, f"{MARKER}:REPORT", report)
        print(f"APPENDED: {EGYPTIAN.relative_to(ROOT)}")
        print(f"APPENDED: {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
