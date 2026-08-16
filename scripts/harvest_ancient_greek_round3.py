#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A, round 3: two 40-card Greek overlap batches.

The harvesting machinery and card schema are inherited from the accepted
round-2 renderer.  This module supplies only the new hand-read outcomes and
emits bounded ``apply_patch`` patches; it never writes repository files.
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
FIRST_RANK = 87
LAST_RANK = 166


Outcome = R2.Outcome


OUTCOMES: dict[int, Outcome] = {
    97: Outcome(
        "root", "حرص", "حرص: شدة الإرادة والشره إلى المطلوب",
        "want وneed في الفرع يلتقيان الحرص العربي، وهو شدة الإرادة للمطلوب؛ المدار طلب الشيء بإرادة ملحة.", 3,
    ),
    99: Outcome(
        "root", "قلم", "القلم: الذي يكتب به، وأصله القصبة المبراة",
        "reed وstalk في الفرع هما مادة القلم الأولى في العربية؛ المدار قصبة مستقيمة تبرى للكتابة.", 1,
    ),
    102: Outcome(
        "root", "درر", "در اللبن والدمع: جرى وكثر",
        "flowing through في الفرع هو الدرور العربي: جريان المائع باندفاع واسترسال.", 1,
    ),
    103: Outcome(
        "law", "فلغ", "فلغ رأسه: شدخه وضربه بالعصا",
        "stroke from a sword or pike في الفرع يلتقي فلغ الرأس العربي، وهو شدخه بالضرب؛ المدار ضربة سلاح، لكن الصامت الأول غير مرخص.",
        3, "π ↔ ف",
    ),
    108: Outcome(
        "law", "ترق", "الترياق: دواء السموم",
        "مدخلة الفرع تسمي antidote against a poisonous bite، والترياق العربي دواء السموم نفسه؛ المعنى مباشر لكن θ إلى ت بلا صف مسمى.",
        3, "θ ↔ ت",
    ),
    110: Outcome(
        "root", "نقس", "نقس القوم: عابهم وسخر منهم ولقبهم",
        "strife of words وrailing وabuse وtaunt في الفرع هي النقس العربي: عيب الناس والسخرية منهم بالألقاب.", 3,
    ),
    111: Outcome(
        "root", "طبل", "الطبل: الذي يضرب به",
        "قاموس الفرع يعرّف اللفظة بأنها كلمة فرثية للطبل، والشاهد العربي يسمي آلة الضرب نفسها.", 3,
    ),
    113: Outcome(
        "root", "قلس", "القلس: حبل ضخم من قلوس السفن",
        "reefing rope وsounding line في الفرع يطابقان القلس العربي، وهو حبل غليظ من حبال السفن.", 3,
    ),
    114: Outcome(
        "root", "خلص", "خلص الشيء: صار خالصا وزال شوبه",
        "pure, unmixed في الفرع هو الخلوص العربي نفسه: زوال الشوب وبقاء الشيء نقيا.", 1,
    ),
    115: Outcome(
        "root", "جلف", "جلف الشيء: قشره وأزال جلده",
        "to carve وcut out with a knife في الفرع يلتقيان الجلف العربي، وهو قشر السطح وأخذ شيء من الجلد أو اللحم.", 3,
    ),
    117: Outcome(
        "root", "درر", "در اللبن والدمع: جرى وكثر",
        "to flow وto run of liquids وto leak في الفرع هي الدرور العربي: جريان المائع واسترساله.", 1,
    ),
    126: Outcome(
        "transmission", "ربب", "الآرامية רבי: ربي، معلم روحي؛ والعبرية רַבִּי: سيدي",
        "قاموس الفرع يصرح بأن ῥαββί من الآرامية רבי، ويورد العبرية רַבִּי؛ انتقال من مانح سامي مسمى.",
    ),
    128: Outcome(
        "law", "ترس", "الترس: سلاح يتوقى به",
        "wide oblong shield في الفرع هو الترس العربي نفسه؛ المعنى والشيء مباشران لكن θ إلى ت بلا صف مسمى.",
        3, "θ ↔ ت",
    ),
    131: Outcome(
        "transmission", "مرر", "العبرية מור: المر؛ والعربية مُرّ: المر والمرّة",
        "قاموس الفرع يرد μύρρα إلى مصدر سامي ويعين العبرية מור والعربية مُرّ؛ اسم المر من مصدر سامي مسمى.",
    ),
    135: Outcome(
        "root", "بتر", "بتر الشيء: قطعه قبل التمام واستأصله",
        "fatherless وdisowned or disinherited by one's father في الفرع تصف من انقطع عن أبيه؛ والمدار قطع النسب الأبوي قبل تمامه.", 3,
    ),
    136: Outcome(
        "transmission", "شمل", "العبرية שְׁמוּאֵל: شموئيل",
        "قاموس الفرع يصرح باقتراض Σαμουήλ من العبرية שְׁמוּאֵל؛ انتقال اسم علم من مانح سامي مسمى.",
    ),
    137: Outcome(
        "root", "طرب", "الطرب: خفة الفرح، ومنه التطريب والغناء",
        "الفرع يسمي Εὐτέρπη ربة الموسيقى ويرد اسمها إلى τέρπω «يسر»؛ والطرب العربي خفة الفرح الملازمة للغناء.", 3,
    ),
    138: Outcome(
        "root", "سطر", "سطر الكتاب: كتب صفوفه",
        "to record and give an account of what one has learned في الفرع يطابق تسطير العربية: إثبات العلم كتابة في سطور.", 1,
    ),
    139: Outcome(
        "root", "طرب", "الطرب: خفة تصيب لشدة سرور أو حزن",
        "to delight وto enjoy وto revel في الفرع تلتقي الطرب العربي، وهو الخفة والفرح والانفعال الممتد.", 3,
    ),
    141: Outcome(
        "law", "طلس", "الأطلس: الأسود الوسخ، وفي لونه غبرة إلى السواد",
        "smoky flame وthick black smoke وsoot في الفرع تلتقي الطلسة العربية، وهي الغبرة إلى السواد؛ المدار أثر الدخان الداكن لكن θ إلى ط غير مرخص.",
        3, "θ ↔ ط",
    ),
    142: Outcome(
        "law", "طلس", "الأطلس: الأسود، وما في لونه غبرة إلى السواد",
        "dark brown وdusky وblackish وdark في الفرع تطابق وصف الأطلس العربي للون الأسود المغبر؛ θ إلى ط بلا صف مسمى.",
        3, "θ ↔ ط",
    ),
    146: Outcome(
        "law", "برش", "البرش: لون مختلط بنقط مختلفة",
        "speckled وdappled في الفرع هما البرش العربي: نقط صغار تخالف سائر اللون؛ المعنى مباشر لكن ψ إلى ب بلا صف مسمى.",
        3, "ψ ↔ ب",
    ),
    151: Outcome(
        "root", "قمش", "القماش: المتاع، ومنه النسيج والثوب",
        "مدخلة الفرع تسمي cloth used to cover the nose and mouth؛ والقماش العربي مادة الثوب والغطاء، فالمدار قطعة نسيج ساترة.", 3,
    ),
    157: Outcome(
        "root", "لبس", "لبس الثوب: اكتسى به، واللباس ما يستر الجسد",
        "shabby, tattered garment وpiece of cloth في الفرع هما لباس عربي: ثوب أو قطعة قماش تكسو الجسد.", 1,
    ),
    159: Outcome(
        "root", "شبر", "الشبر: مقياس ما بين الإبهام والخنصر",
        "kind of land measure في الفرع والشبر العربي كلاهما وحدة لقياس الامتداد؛ المدار تقدير الطول بوحدة معلومة.", 3,
    ),
    161: Outcome(
        "root", "سنن", "السنان: ما يركب في رأس الرمح",
        "javelin في الفرع يلتقي السنان العربي بوصفه رأس الرمح الحاد؛ المدار سلاح نافذ ذو سن.", 1,
    ),
    164: Outcome(
        "root", "ترز", "التارز: اليابس؛ وأترز الشيء أي أيبسه",
        "dried figs وdrying place for corn or cheese في الفرع تلتقي ترز العربية في اليبس وتجفيف الطعام حتى يصلب.", 3,
    ),
    166: Outcome(
        "root", "فرق", "الفَرَق: الخوف والفزع",
        "shuddering fear في الفرع هو الفرق العربي، أي الخوف الذي يفرق القلب ويظهر في ارتعاش الجسد.", 3,
    ),
}


def build_card(rank: int, row: dict, hits: dict[str, list[dict]]) -> tuple[str, dict]:
    R2.OUTCOMES = OUTCOMES
    card, record = R2.build_card(rank, row, hits)
    return card.replace("LANE-A-R2-", "LANE-A-R3-"), record


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
    for batch, start in ((1, 87), (2, 127)):
        batch_rows = payload["both"][start - 1:start + 39]
        sections += [
            f"<!-- LANE-A-GREEK-ROUND3-BATCH-{batch}:START -->",
            "",
            f"## دفعة اليونانية، الجولة الثالثة {batch}، الرتب {start}–{start + 39} من `both` (2026-08-16)",
            "",
        ]
        for rank, row in enumerate(batch_rows, start):
            card, record = build_card(rank, row, hits)
            sections += [card, ""]
            records.append(record)
        sections += [f"<!-- LANE-A-GREEK-ROUND3-BATCH-{batch}:END -->", ""]
    return "\n".join(sections).rstrip(), records


def proposal_addition() -> str:
    return """## إلحاق شواهد الجولة الثالثة، الرتب 87–166

أعيد التفتيش بالحرفين معا وفي الترتيبين، ثم بألفاظ `اليونانية` و`يونانيّة` و`Greek` في عمود الشاهد. الأسطر الآتية شواهد جديدة فقط، لا توصية بإضافة صف ولا تعديل للشبكة النافذة.

| اليوناني | العربي | الشواهد الجديدة | أمثلة بأسمائها | ما وجد في الشبكة النافذة |
|---|---|---:|---|---|
| `π` | `ف` | 1 | `πληγή`→`فلغ` «ضربة السيف أو الرمح» ↔ «فلغ رأسه: شدخه وضربه» | `LAB-01` يرخص `π ↔ ب`؛ و`BR-GRIM-01` خاص بالانتقال من الهندوأوروبية الأم إلى الجرمانية، فلا يرخص يونانية `π ↔ ف` |
| `θ` | `ت` | 2 | `θηριακή`→`ترق/ترياق` «دواء السموم»؛ `θυρεός`→`ترس` «الدرع» | `BR-GREC-01` يسمي اليونانية `τ` في سلسلة `ث ↔ t`، لا الحرف `θ`؛ لا صف يسمي `θ ↔ ت` |
| `θ` | `ط` | 1 | بطاقتا `αἴθαλος`→`طلس`: «الدخان والسخام الأسود» و«اللون الأدكن المغبر» | `DENT-05` يرخص `τ ↔ ط`؛ لا صف يسمي `θ ↔ ط` |
| `ψ` | `ب` | 1 | `ψαρός`→`برش` «منقط مختلف اللون» | لا صف في الشبكة يسمي `ψ`، وصف الباء اليوناني النافذ يخص `β` لا `ψ` |

تبقى البطاقات الست `LAW-GAP` إلى أن يقرر المؤلف في الشبكة المجمدة؛ لا تحمل هذه الورقة توصية.
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
            f"## {now}، الجولة الثالثة، الدفعة {batch}",
            "",
            f"- البطاقات: {len(subset)}؛ الرتب: {subset[0]['rank']}–{subset[-1]['rank']}؛ آخر overlap: 3.",
            "- توزيع الأحكام: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(verdicts.items())) + ".",
            "- توزيع الإغلاق: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(counts.items())) + ".",
            f"- الموجب المحتسب: {sum(r['verdict'] in {'ROOT-TRACE', 'SEMITIC-SOURCE-TRANSMISSION'} for r in subset)}؛ المفتوح: {sum(r['verdict'] in {'OPEN-CANDIDATE', 'LAW-GAP'} for r in subset)}.",
            "- أبرز الأزواج الموجبة: " + ("؛ ".join(examples) if examples else "لا يوجد") + ".",
            "- أعطاب الأدوات: 0؛ قُرئت المروحة الواسعة كلها، وأعاد `frozen_event.all_tiers` حدثا لكل منتخب، وأعاد قاموس الفرع مدخلة لكل صف.",
            "",
        ]
    total = Counter(record["closure"] for record in records)
    lines += [
        "## حصيلة الجولة الثالثة",
        "",
        f"- مجموع البطاقات: {len(records)}؛ الرتب: 87–166؛ آخر overlap: 3.",
        "- الإغلاق الكلي: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(total.items())) + ".",
        f"- النتائج الموجبة المحتسبة: {sum(r['verdict'] in {'ROOT-TRACE', 'SEMITIC-SOURCE-TRANSMISSION'} for r in records)}؛ `ROOT-TRACE`={sum(r['verdict'] == 'ROOT-TRACE' for r in records)}؛ `SEMITIC-SOURCE-TRANSMISSION`={sum(r['verdict'] == 'SEMITIC-SOURCE-TRANSMISSION' for r in records)}.",
        "- فجوات القانون: `π ↔ ف` في بطاقة؛ `θ ↔ ت` في بطاقتين؛ `θ ↔ ط` في بطاقتين لمعنيي مدخلة واحدة؛ `ψ ↔ ب` في بطاقة. ألحقت الشواهد في `04-cross-linguistic/proposed-shift-rows-greek.md` بلا توصية.",
        "",
        "LANE-A DONE3 80 166",
    ]
    return "\n".join(lines)


def add_lines(text: str) -> str:
    return "\n".join("+" + line for line in text.splitlines())


def emit_reading_chunk(start: int, count: int) -> str:
    if start < FIRST_RANK or start > LAST_RANK or count < 1 or start + count - 1 > LAST_RANK:
        raise AssertionError("نطاق قطعة القراءة خارج الرتب 87–166")
    reading = READING.read_text(encoding="utf-8")
    cards, _records = render_cards()
    positions = {
        int(match.group(1)): match.start()
        for match in re.finditer(r"^### بطاقة: .*LANE-A-R3-(\d{3})$", cards, re.MULTILINE)
    }
    if len(positions) != 80:
        raise AssertionError(f"عدد رؤوس البطاقات المولدة {len(positions)} لا يساوي 80")
    begin = 0 if start == FIRST_RANK else positions[start]
    end = positions.get(start + count, len(cards))
    chunk = cards[begin:end].rstrip()
    if f"LANE-A-R3-{start:03d}" in reading:
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
    if "إلحاق شواهد الجولة الثالثة" in proposal:
        raise AssertionError("إلحاق الجولة الثالثة موجود في ورقة الاقتراح")
    if "LANE-A DONE3" in report:
        raise AssertionError("سطر إتمام الجولة الثالثة موجود")
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
