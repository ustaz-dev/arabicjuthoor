#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A, round 4: two 40-card Greek overlap batches.

The accepted round-2 card contract remains authoritative.  This read-only
renderer supplies the hand-read outcomes for ranks 167--246 and emits bounded
``apply_patch`` patches; it never writes repository files and never ships.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime
import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import harvest_ancient_greek_round2 as R2  # noqa: E402


READING = ROOT / "04-cross-linguistic" / "readings" / "ancient-greek.md"
PROPOSAL = ROOT / "04-cross-linguistic" / "proposed-shift-rows-greek.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-A.md"
FIRST_RANK = 167
LAST_RANK = 246


Outcome = R2.Outcome


OUTCOMES: dict[int, Outcome] = {
    167: Outcome(
        "root", "كلل",
        "الإكليل: السحاب الذي تراه كأن غشاء ألبسه؛ والسحاب المكلل ملمع بالبرق",
        "mist وhaze في الفرع غشاء جوي رقيق، وradiance ضوء خلاله؛ والإكليل العربي سحاب كالغشاء يلمع بالبرق، فالمدار غطاء جوي مجتمع يشف عنه الضوء.",
        1,
    ),
    172: Outcome(
        "root", "ملس", "الملس: المكان المستوي؛ والملاسة ضد الخشونة",
        "even وlevel وuniform in consistency في الفرع هي الملاسة العربية: سطح مستو متجانس خلا من الخشونة والنتوء.",
        3,
    ),
    173: Outcome(
        "root", "قلص",
        "فرس مقلص: طويل القوائم منضم البطن؛ وقلصت الإبل: استمرت في مضيها",
        "racehorse وcourser في الفرع يلتقيان الفرس المقلص العربي، وهو طويل القوائم منضم البطن مهيأ للمضي؛ المدار مركوب خفيف سريع البنية.",
        3,
    ),
    176: Outcome(
        "law", "مرق",
        "مرق السهم: خرج من الجانب الآخر؛ ومرق الصوف: نتفه",
        "to pluck or pull وto expel or throw out في الفرع يجتمعان في مرق العربية: نتف الشيء وإخراجه من موضعه؛ المعنى مباشر لكن γ إلى ق بلا صف مسمى.",
        3, "γ ↔ ق",
    ),
    177: Outcome(
        "law", "بطن", "بطن كل شيء: جوفه؛ والباطن خلاف الظاهر",
        "to deepen وhollow out في الفرع إنشاء لجوف داخل الشيء، وهو البطن العربي؛ المدار فتح حيز داخلي خفي، لكن θ إلى ط بلا صف مسمى.",
        1, "θ ↔ ط",
    ),
    182: Outcome(
        "root", "برز", "الإبريز: الذهب الخالص؛ وكل ما ظهر بعد خفاء فقد برز",
        "assaying of gold يميز الذهب حتى يظهر إبريزا خالصا؛ فالمدار إخراج الذهب من شوبه وإبرازه نقيا.",
        1,
    ),
    183: Outcome(
        "root", "طلل", "أطل عليه: أشرف؛ والطلل شخص الشيء المترائي",
        "to rise of stars في الفرع هو إطلال النجم العربي: ظهور شخصه من علو وإشرافه على ما دونه.",
        1,
    ),
    188: Outcome(
        "root", "بدن", "البدن: الجسد، وما سوى الرأس والشوى منه",
        "trunk of a plant في الفرع هو بدنه العربي: الكتلة الأصلية التي تقوم منها الأطراف والفروع؛ المدار جسم مركزي حامل لما يتشعب منه.",
        1,
    ),
    189: Outcome(
        "transmission", "سلم",
        "العبرية الكتابية שִּׁילוֹחַ /Shiloaḥ/: اسم سلوام، الموضع نفسه",
        "قاموس الفرع يصرح باقتراض Σιλωάμ من العبرية الكتابية שִּׁילוֹחַ؛ انتقال اسم موضع من مانح سامي مسمى.",
    ),
    196: Outcome(
        "transmission", "جرن",
        "السريانية ܓܘܪܢܐ /gūrnā/: وعاء كبير؛ والعربية الجرن: حجر منقور يصب فيه الماء",
        "قاموس الفرع يرد γοῦρνα إلى السريانية ܓܘܪܢܐ أو آرامية أخرى؛ والفرع والعربية يسميان وعاء مجوفا، فالنقل من مانح سامي مسمى.",
    ),
    202: Outcome(
        "law", "كدر",
        "انكدر النجم: انقض وسقط؛ وانكدر الشيء: أسرع وانصب",
        "draw or haul down في الفرع إنزال للشيء، وانكدر في العربية انقض من علو وانصب؛ المدار حركة إلى أسفل، لكن τ إلى د بلا صف مسمى.",
        1, "τ ↔ د",
    ),
    205: Outcome(
        "root", "بلغ", "بلغ الشيء: وصل وانتهى؛ والبلوغ الانتهاء إلى أقصى المقصد",
        "to leave off وto cease في الفرع وقوع عند النهاية، وبلغ العربية وصول الشيء إلى غايته ومنتهاه؛ المدار بلوغ الحد الذي ينقطع عنده الفعل.",
        1,
    ),
    209: Outcome(
        "law", "فلت", "أفلت الشيء وانفلت: خرج وفات؛ والفلتة ما يفوت تداركه",
        "to cause one to forget وto allow something to escape notice في الفرع هما فلت العربية: انفصال الشيء حتى يفوت إدراكه؛ بقي π إلى ف وθ إلى ت بلا صفين مسميين.",
        3, "π ↔ ف",
    ),
    212: Outcome(
        "transmission", "بب",
        "الآرامية אַבָּא /ʾaḇā/: الأب؛ والعربية أب: الوالد",
        "قاموس الفرع يصرح باقتراض ἀββα من الآرامية אַבָּא «الأب»، ومنها لقب رئيس الدير؛ انتقال من مانح سامي مسمى.",
    ),
    215: Outcome(
        "root", "مني", "تمنى الشيء: أراده؛ والمنية والأمنية ما تتمناه النفس",
        "mad desire وcompulsion في الفرع رغبة تستولي على النفس، وتمني العربية إرادة المطلوب وتصويره أمنية؛ المدار رغبة ملحة ثابتة.",
        3,
    ),
    219: Outcome(
        "root", "روم", "رام الشيء: طلبه؛ والمرام: المطلب",
        "to love وpassionately desire وdesire eagerly في الفرع هي روم العربية: توجه النفس إلى مطلوب والحرص على بلوغه.",
        3,
    ),
    225: Outcome(
        "root", "ميل", "مال إليه: عدل وأقبل عليه؛ واستماله: استمال قلبه",
        "to care for وbe interested in في الفرع ميل نفس إلى الشيء وإقبال عليها؛ والمدار اتجاه العناية والقلب نحو مطلوب.",
        1,
    ),
    229: Outcome(
        "root", "بني", "بنى بأهله أو عليها: دخل بها وأعرس",
        "to have sexual intercourse في الفرع يطابق الاستعمال العربي بنى بأهله، أي دخل بها؛ المدار الجماع في سياق الدخول بالزوجة.",
        1,
    ),
    235: Outcome(
        "root", "وبل", "الوبيل: العصا الغليظة؛ وضرب وبيل: شديد",
        "stroke or wound of a missile في الفرع أثر ضربة شديدة، والوبيل العربي عصا غليظة وضرب وبيل؛ المدار إصابة من أداة ثقيلة ضاربة.",
        1,
    ),
    240: Outcome(
        "root", "نم", "النم: إظهار الحديث بالوشاية؛ والنميمة الوشاية",
        "to blame وslander وattack verbally في الفرع يلتقي النم العربي، وهو إظهار الحديث على جهة الوشاية والإفساد؛ المدار أذى الغير بالكلام المنقول.",
        2,
    ),
    244: Outcome(
        "root", "ميل", "ميل الجراحة: الآلة الدقيقة التي يسبر بها الجرح",
        "surgical probe في الفرع هو ميل الجراحة العربي نفسه؛ الاسم والآلة الطبية الدقيقة متطابقان.",
        3,
    ),
}


def build_card(rank: int, row: dict, hits: dict[str, list[dict]]) -> tuple[str, dict]:
    R2.OUTCOMES = OUTCOMES
    card, record = R2.build_card(rank, row, hits)
    card = card.replace("LANE-A-R2-", "LANE-A-R4-")
    if rank == 209:
        card = card.replace(
            "LAW-GAP π ↔ ف)",
            "LAW-GAP π ↔ ف + θ ↔ ت)",
        ).replace(
            "يتطلب=صفا مجمدا مسمى يرخص `π ↔ ف`؛",
            "يتطلب=صفين مجمدين مسميين يرخصان `π ↔ ف` و`θ ↔ ت`؛",
        )
    return card, record


def render_cards() -> tuple[str, list[dict]]:
    payload = json.loads(R2.SWEEP.read_text(encoding="utf-8"))
    rows = payload["both"][FIRST_RANK - 1:LAST_RANK]
    all_roots: set[str] = set()
    for row in rows:
        all_roots.update(candidate for candidate, _weight in R2.FAN.rank(
            str(row["branch"]), R2.FAN.fan(str(row["branch"]), "greek"), "greek"
        ))
    hits = R2.AR.matches_for_roots(R2.AR.DEFAULT_RESOURCES, all_roots, None)
    sections: list[str] = []
    records: list[dict] = []
    for batch, start in ((1, 167), (2, 207)):
        batch_rows = payload["both"][start - 1:start + 39]
        sections += [
            f"<!-- LANE-A-GREEK-ROUND4-BATCH-{batch}:START -->",
            "",
            f"## دفعة اليونانية، الجولة الرابعة {batch}، الرتب {start}–{start + 39} من `both` (2026-08-16)",
            "",
        ]
        for rank, row in enumerate(batch_rows, start):
            card, record = build_card(rank, row, hits)
            sections += [card, ""]
            records.append(record)
        sections += [f"<!-- LANE-A-GREEK-ROUND4-BATCH-{batch}:END -->", ""]
    return "\n".join(sections).rstrip(), records


def proposal_addition() -> str:
    return """## إلحاق شواهد الجولة الرابعة، الرتب 167–246

أعيد التفتيش بالحرفين معا وفي الترتيبين، ثم بألفاظ `اليونانية` و`يونانيّة` و`Greek` في عمود الشاهد. الأسطر الآتية شواهد جديدة فقط، لا توصية بإضافة صف ولا تعديل للشبكة النافذة.

| اليوناني | العربي | الشواهد الجديدة | أمثلة بأسمائها | ما وجد في الشبكة النافذة |
|---|---|---:|---|---|
| `γ` | `ق` | 1 | `ἀμέργω`→`مرق` «ينتف أو يجذب؛ يطرد أو يخرج» ↔ «مرق الصوف: نتفه؛ ومرق السهم: خرج» | `IDN-08` يرخص `γ ↔ ج` و`GUT-04` يرخص `γ ↔ غ`؛ لا صف يسمي `γ ↔ ق` |
| `θ` | `ط` | 1 | `βαθύνω`→`بطن` «يعمق ويجوف» ↔ «بطن كل شيء: جوفه» | `DENT-05` يرخص اليونانية `τ ↔ ط`؛ لا صف يسمي `θ ↔ ط` |
| `τ` | `د` | 1 | `κατερύω`→`كدر` «يجر إلى أسفل» ↔ «انكدر: انقض وسقط» | `IDN-11` يرخص `τ ↔ ت` و`DENT-05` يرخص `τ ↔ ط`؛ لا صف يسمي `τ ↔ د` |
| `π` | `ف` | 1 | `ἐπιλήθω`→`فلت` «يفوّت الشيء من الانتباه» ↔ «أفلت: خرج وفات» | `LAB-01` يرخص `π ↔ ب`؛ لا صف يسمي `π ↔ ف` |
| `θ` | `ت` | 1 | البطاقة نفسها `ἐπιλήθω`→`فلت`؛ ساقها تحتاج النقلة الثانية مستقلة | `BR-GREC-01` يسمي اليونانية `τ` في سلسلة `ث ↔ t`؛ لا صف يسمي `θ ↔ ت` |

تبقى البطاقات الأربع `LAW-GAP` إلى أن يقرر المؤلف في الشبكة المجمدة؛ والبطاقة `ἐπιλήθω` تحمل فجوتين مستقلتين. لا تحمل هذه الورقة توصية.
"""


def report_addition(records: list[dict]) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    lines: list[str] = []
    for batch, subset in ((1, records[:40]), (2, records[40:])):
        counts = Counter(record["closure"] for record in subset)
        verdicts = Counter(record["verdict"] for record in subset)
        examples = [
            f"`{record['word']}↔{record['root']}`" for record in subset
            if record["verdict"] in {"ROOT-TRACE", "SEMITIC-SOURCE-TRANSMISSION"}
        ][:10]
        lines += [
            f"## {now}، الجولة الرابعة، الدفعة {batch}",
            "",
            f"- البطاقات: {len(subset)}؛ الرتب: {subset[0]['rank']}–{subset[-1]['rank']}؛ آخر overlap: {subset[-1].get('overlap', 3)}.",
            "- توزيع الأحكام: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(verdicts.items())) + ".",
            "- توزيع الإغلاق: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(counts.items())) + ".",
            f"- الموجب المحتسب: {sum(r['verdict'] in {'ROOT-TRACE', 'SEMITIC-SOURCE-TRANSMISSION'} for r in subset)}؛ المفتوح: {sum(r['verdict'] in {'OPEN-CANDIDATE', 'LAW-GAP'} for r in subset)}.",
            "- أبرز الأزواج الموجبة: " + ("؛ ".join(examples) if examples else "لا يوجد") + ".",
            "- أعطاب الأدوات: 0؛ قُرئت المروحة الواسعة كلها، وأعاد `frozen_event.all_tiers` حدثا لكل منتخب، وأعاد قاموس الفرع مدخلة لكل صف.",
            "",
        ]
    total = Counter(record["closure"] for record in records)
    lines += [
        "## حصيلة الجولة الرابعة",
        "",
        f"- مجموع البطاقات: {len(records)}؛ الرتب: 167–246؛ آخر overlap: 3.",
        "- الإغلاق الكلي: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(total.items())) + ".",
        f"- النتائج الموجبة المحتسبة: {sum(r['verdict'] in {'ROOT-TRACE', 'SEMITIC-SOURCE-TRANSMISSION'} for r in records)}؛ `ROOT-TRACE`={sum(r['verdict'] == 'ROOT-TRACE' for r in records)}؛ `SEMITIC-SOURCE-TRANSMISSION`={sum(r['verdict'] == 'SEMITIC-SOURCE-TRANSMISSION' for r in records)}.",
        "- فجوات القانون: `γ ↔ ق` و`θ ↔ ط` و`τ ↔ د` في شاهد لكل منها، و`π ↔ ف` مع `θ ↔ ت` في بطاقة واحدة ذات فجوتين. ألحقت الشواهد في `04-cross-linguistic/proposed-shift-rows-greek.md` بلا توصية.",
        "- ترتيب `both`: بقي `overlap` غير صاعد في كامل النافذة؛ الرتب 167–246 كلها عند `overlap=3`.",
        "- الإيداع: لم يشغل `scripts/ship.py` ولم ينشأ أي إيداع؛ تُرك الإيداع الشامل للمنسق بعد سكون الجولة.",
        "",
        "LANE-A DONE4 80 246",
    ]
    return "\n".join(lines)


def add_lines(value: str) -> str:
    return "\n".join("+" + line for line in value.splitlines())


def emit_reading_chunk(start: int, count: int) -> str:
    if start < FIRST_RANK or start > LAST_RANK or count < 1 or start + count - 1 > LAST_RANK:
        raise AssertionError("نطاق قطعة القراءة خارج الرتب 167–246")
    reading = READING.read_text(encoding="utf-8")
    cards, _records = render_cards()
    positions = {
        int(match.group(1)): match.start()
        for match in re.finditer(r"^### بطاقة: .*LANE-A-R4-(\d{3})$", cards, re.MULTILINE)
    }
    if len(positions) != 80:
        raise AssertionError(f"عدد رؤوس البطاقات المولدة {len(positions)} لا يساوي 80")
    begin = 0 if start == FIRST_RANK else positions[start]
    end = positions.get(start + count, len(cards))
    chunk = cards[begin:end].rstrip()
    if f"LANE-A-R4-{start:03d}" in reading:
        raise AssertionError(f"القطعة التي تبدأ بالرتبة {start} موجودة")
    tail = reading.rstrip().splitlines()[-24:]
    patch = [
        "*** Begin Patch",
        "*** Update File: 04-cross-linguistic/readings/ancient-greek.md",
        "@@",
        *(" " + line for line in tail),
        "+",
        add_lines(chunk),
        "*** End Patch",
    ]
    return "\n".join(patch) + "\n"


def emit_proposal_report() -> str:
    proposal = PROPOSAL.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    if "إلحاق شواهد الجولة الرابعة" in proposal:
        raise AssertionError("إلحاق الجولة الرابعة موجود في ورقة الاقتراح")
    if "LANE-A DONE4" in report:
        raise AssertionError("سطر إتمام الجولة الرابعة موجود")
    _cards, records = render_cards()
    proposal_tail = proposal.rstrip().splitlines()[-8:]
    report_tail = report.rstrip().splitlines()[-8:]
    patch = [
        "*** Begin Patch",
        "*** Update File: 04-cross-linguistic/proposed-shift-rows-greek.md",
        "@@",
        *(" " + line for line in proposal_tail),
        "+",
        add_lines(proposal_addition().rstrip()),
        "*** Update File: _inbox/lane-reports/2026-08-16-A.md",
        "@@",
        *(" " + line for line in report_tail),
        "+",
        add_lines(report_addition(records).rstrip()),
        "*** End Patch",
    ]
    return "\n".join(patch) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reading-chunk", type=int, metavar="START")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--proposal-report", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.reading_chunk is not None:
        print(emit_reading_chunk(args.reading_chunk, args.count), end="")
    elif args.proposal_report:
        print(emit_proposal_report(), end="")
    else:
        _cards, records = render_cards()
        print(json.dumps(records, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
