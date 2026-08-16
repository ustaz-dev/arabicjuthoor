#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A, round 5: two 40-card Greek overlap batches.

The accepted round-2 card contract remains authoritative.  This read-only
renderer supplies the hand-read outcomes for ranks 247--326 and emits bounded
``apply_patch`` patches; it never writes repository files, commits, or ships.
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
FIRST_RANK = 247
LAST_RANK = 326


Outcome = R2.Outcome


OUTCOMES: dict[int, Outcome] = {
    252: Outcome(
        "transmission", "ترمس",
        "الأكادية tarmuš والآرامية תורמוסא / ܬܘܪܡܣܐ tūrmūsā، والعربية تُرْمُس: النبات نفسه",
        "قاموس الفرع يرد اسم نبات الترمس إلى الأكادية tarmuš، ثم يسمي قرينيه الآرامي والعربي؛ انتقال اسم نبات عبر مانح سامي مسمى، وإن كان الأصل الأبعد المسجل سومريا.",
    ),
    258: Outcome(
        "root", "جرن",
        "الجرن: حجر منقور يصب فيه الماء؛ ويقال لموضع الدق والعجن",
        "hollow vessel وkneading trough في الفرع هما الجرن العربي: وعاء أو حجر منقور مجوف يوضع فيه الماء أو يدق ويعجن فيه.",
        3,
    ),
    264: Outcome(
        "root", "بلز",
        "امرأة بلز وبلزّ: ضخمة مكنزة",
        "large وgreat في الفرع يلتقيان بلز العربية في وصف الجسم الضخم المكتنز؛ المدار عظم الجرم وكثرة حجمه.",
        3,
    ),
    274: Outcome(
        "root", "سطر",
        "السطر: الخط والكتابة؛ وسطر الكتاب كتبه",
        "written account وnarrative وhistory في الفرع سجل مكتوب، والسطر العربي هو الخط والكتابة؛ المدار تثبيت الخبر في كتابة مصطفة.",
        1,
    ),
    # The surface fan reads دنس, but the named transmission is the independent
    # Phoenician stem ʾdn.  build_card() rewrites the surface-counterpart lines
    # so the two are never represented as one comparison.
    276: Outcome(
        "transmission", "دنس",
        "الفينيقية 𐤀𐤃𐤍 /ʾdn/ «السيد»، ومنها اسم أدونيس في معنى العلم وحده",
        "قاموس الفرع يرد اسم العلم Ἄδωνις إلى الفينيقية 𐤀𐤃𐤍 /ʾdn/ من الأصل السامي؛ الحكم لنقل اسم العلم وحده، ولا يرثه معنى السمكة.",
    ),
    277: Outcome(
        "root", "حمز",
        "الحمز: حرافة الشيء؛ وشراب يحمز اللسان",
        "flavour وsavour في الفرع يدخلان طعم العصارة، وحمز العربية حرافة الطعم التي يجدها اللسان؛ المدار مذاق نافذ في سائل أو عصارة.",
        3,
    ),
    293: Outcome(
        "root", "قرن",
        "قرن الثور معروف: النابت من رأسه",
        "anything curved، ولا سيما مقبض الباب المنحني، في الفرع يلتقي القرن العربي بوصفه جسما ناتئا معقوفا؛ المدار نتوء صلب منحني يمسك أو يبرز.",
        1,
    ),
    299: Outcome(
        "root", "ستر",
        "ستر: غطى وحمى بما يستر",
        "المنقذة الحافظة تقي المحفوظ مما يؤذيه، وهي الحماية التي تحملها العربية في الستر والتغطية الواقية.",
        1,
    ),
    301: Outcome(
        "root", "ملس",
        "الملاسة ضد الخشونة؛ وشيء أملس",
        "finely ground meal في الفرع دقيق ناعم خلا من الخشونة والحب الخشن، وهو وصف الملاسة العربي؛ المدار نعومة السطح أو المادة بعد زوال الخشن.",
        3,
    ),
    313: Outcome(
        "law", "بتر",
        "بتر الشيء: قطعه قبل الإتمام؛ والانبتار الانقطاع",
        "destruction وruin وloss by death في الفرع انقطاع الشيء وذهاب تمامه، وبتر العربية قطعه قبل الإتمام؛ المدار قطع الامتداد حتى الفناء، لكن θ إلى ت بلا صف مسمى.",
        1, "θ ↔ ت",
    ),
}


_ORIGINAL_CHOSEN_ENTRY = R2.chosen_entry


def chosen_entry(row: dict) -> tuple[list[dict], dict, str]:
    """Keep two inflected forms on their exact sweep row, not a skeleton hit."""
    word = str(row["branch"])
    if word in {"μίν", "ἐῶμεν"}:
        read = str(row.get("say") or "").split("  (")[0]
        entry = {
            "word": word,
            "read": read,
            "pos": "form",
            "en": str(row.get("gloss") or ""),
            "etym": "",
        }
        return [entry], entry, "صف المسح المثبت بنصه"
    return _ORIGINAL_CHOSEN_ENTRY(row)


def compact_to_limit(card: str, rank: int) -> tuple[str, int]:
    """Shorten descriptive lines only; never trim the acting event or orbit."""
    size = len((card + "\n").encode("utf-8"))
    if size <= R2.MAX_CARD_BYTES:
        return card, size
    card = re.sub(
        r"(^- فحص المروحة كلها: قُرئت \d+ صورة مرتبة؛ كل مرشح ذي مسار مسمى قُرئت شواهده وحُكم: )(.+)$",
        lambda match: match.group(1) + R2.clip(match.group(2), 90),
        card,
        flags=re.MULTILINE,
    )
    size = len((card + "\n").encode("utf-8"))
    if size <= R2.MAX_CARD_BYTES:
        return card, size
    card = re.sub(
        r"(^- أقدم صورة مستعادة: )(.+)$",
        lambda match: match.group(1) + R2.clip(match.group(2), 105),
        card,
        flags=re.MULTILINE,
    )
    size = len((card + "\n").encode("utf-8"))
    if size <= R2.MAX_CARD_BYTES:
        return card, size
    card = re.sub(
        r"(^- مسح المعاني العربية: )(.+)$",
        lambda match: match.group(1) + R2.clip(match.group(2), 205),
        card,
        flags=re.MULTILINE,
    )
    size = len((card + "\n").encode("utf-8"))
    if size > R2.MAX_CARD_BYTES:
        raise AssertionError(f"تجاوزت البطاقة {rank} حد 5 كيلوبايت بعد الضغط: {size}")
    return card, size


def build_card(rank: int, row: dict, hits: dict[str, list[dict]]) -> tuple[str, dict]:
    R2.OUTCOMES = OUTCOMES
    R2.chosen_entry = chosen_entry
    original_limit = R2.MAX_CARD_BYTES
    R2.MAX_CARD_BYTES = 64 * 1024
    try:
        card, record = R2.build_card(rank, row, hits)
    finally:
        R2.MAX_CARD_BYTES = original_limit
    card = card.replace("LANE-A-R2-", "LANE-A-R5-")
    if rank == 276:
        card = re.sub(
            r"^- مسح المعاني العربية:.*$",
            "- مسح المعاني العربية: قُرئت مروحة السطح كلها، ولم يثبت منها مقابل عربي؛ إغلاق البطاقة من النقل الفينيقي المسمى لا من حكم عربي.",
            card,
            flags=re.MULTILINE,
        )
        card = re.sub(
            r"^- المقابل من اللسان:.*$",
            "- المقابل السامي المسمى: الفينيقية `𐤀𐤃𐤍` /ʾdn/ «السيد»؛ لم يُتخذ `دنس` مقابلا عربيا، وإنما بقي مرشح سطح مقروءا بلا مدار.",
            card,
            flags=re.MULTILINE,
        )
        card = re.sub(
            r"^- مسار الصوت:.*$",
            "- مسار الصوت السطحي: `IDN-09 + IDN-03 + IDN-07` يقرأ `دنس` من الرسم، لكنه لا ينشئ حكما؛ النقل مستقل من حقل الأصل الفينيقي المسمى.",
            card,
            flags=re.MULTILINE,
        )
        card = card.replace("؛ نقل سامي مسمى)", "؛ لا مدار محدود)")
        card = card.replace(
            "- فصل المتجانسات والاقتراض: الحكم لهذه المدخلة وسلسلة معناها وحدهما؛ لم يرثه متحد الرسم ولا معنى مجاور.",
            "- فصل المتجانسات والاقتراض: الحكم خاص بمعنى اسم العلم `Adonis`؛ معنى السمكة في المدخلة لا يرث النقل الفينيقي، ولا يرث مرشح السطح `دنس` حكم الاسم.",
        )
        record["root"] = "𐤀𐤃𐤍"
    card, size = compact_to_limit(card, rank)
    record["bytes"] = size
    return card, record


def render_cards() -> tuple[str, list[dict]]:
    payload = json.loads(R2.SWEEP.read_text(encoding="utf-8"))
    rows = payload["both"][FIRST_RANK - 1:LAST_RANK]
    if len(rows) != 80:
        raise AssertionError(f"نافذة both أعادت {len(rows)} صفا لا 80")
    all_roots: set[str] = set()
    for row in rows:
        all_roots.update(candidate for candidate, _weight in R2.FAN.rank(
            str(row["branch"]), R2.FAN.fan(str(row["branch"]), "greek"), "greek"
        ))
    hits = R2.AR.matches_for_roots(R2.AR.DEFAULT_RESOURCES, all_roots, None)
    sections: list[str] = []
    records: list[dict] = []
    for batch, start in ((1, 247), (2, 287)):
        batch_rows = payload["both"][start - 1:start + 39]
        sections += [
            f"<!-- LANE-A-GREEK-ROUND5-BATCH-{batch}:START -->",
            "",
            f"## دفعة اليونانية، الجولة الخامسة {batch}، الرتب {start}–{start + 39} من `both` (2026-08-16)",
            "",
        ]
        for rank, row in enumerate(batch_rows, start):
            card, record = build_card(rank, row, hits)
            sections += [card, ""]
            records.append(record)
        sections += [f"<!-- LANE-A-GREEK-ROUND5-BATCH-{batch}:END -->", ""]
    return "\n".join(sections).rstrip(), records


def proposal_addition() -> str:
    return """## إلحاق شواهد الجولة الخامسة، الرتب 247–326

أعيد التفتيش بالحرفين معا وفي الترتيبين، ثم بألفاظ `اليونانية` و`يونانيّة` و`Greek` في عمود الشاهد. السطر الآتي شاهد جديد فقط، لا توصية بإضافة صف ولا تعديل للشبكة النافذة.

| اليوناني | العربي | الشواهد الجديدة | أمثلة بأسمائها | ما وجد في الشبكة النافذة |
|---|---|---:|---|---|
| `θ` | `ت` | 1 | `φθορά`→`بتر` «هلاك وخراب وفقد بالموت» ↔ «بتر الشيء: قطعه قبل الإتمام» | `BR-GREC-01` يسمي اليونانية `τ` في سلسلة `ث ↔ t`؛ لا صف يسمي `θ ↔ ت` |

تبقى البطاقة `φθορά` في `LAW-GAP` إلى أن يقرر المؤلف في الشبكة المجمدة؛ لا تحمل هذه الورقة توصية.
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
            f"## {now}، الجولة الخامسة، الدفعة {batch}",
            "",
            f"- البطاقات: {len(subset)}؛ الرتب: {subset[0]['rank']}–{subset[-1]['rank']}؛ آخر overlap: {subset[-1].get('overlap', 1)}.",
            "- توزيع الأحكام: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(verdicts.items())) + ".",
            "- توزيع الإغلاق: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(counts.items())) + ".",
            f"- الموجب المحتسب: {sum(r['verdict'] in {'ROOT-TRACE', 'SEMITIC-SOURCE-TRANSMISSION'} for r in subset)}؛ المفتوح: {sum(r['verdict'] in {'OPEN-CANDIDATE', 'LAW-GAP'} for r in subset)}.",
            "- أبرز الأزواج الموجبة: " + ("؛ ".join(examples) if examples else "لا يوجد") + ".",
            "- أعطاب الأدوات المصححة: 2؛ أعاد فهرس القاموس تطابقين هيكليين مضللين في الرتبتين 248 و251، فصُححا بالرجوع إلى صف المسح المثبت؛ أما المروحة و`frozen_event.all_tiers` فأتما قراءة كل منتخب بلا عطب.",
            "",
        ]
    total = Counter(record["closure"] for record in records)
    lines += [
        "## حصيلة الجولة الخامسة",
        "",
        f"- مجموع البطاقات: {len(records)}؛ الرتب: 247–326؛ آخر overlap: 1.",
        "- الإغلاق الكلي: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(total.items())) + ".",
        f"- النتائج الموجبة المحتسبة: {sum(r['verdict'] in {'ROOT-TRACE', 'SEMITIC-SOURCE-TRANSMISSION'} for r in records)}؛ `ROOT-TRACE`={sum(r['verdict'] == 'ROOT-TRACE' for r in records)}؛ `SEMITIC-SOURCE-TRANSMISSION`={sum(r['verdict'] == 'SEMITIC-SOURCE-TRANSMISSION' for r in records)}.",
        "- فجوات القانون: `θ ↔ ت` في بطاقة واحدة؛ ألحق شاهد `φθορά`→`بتر` في `04-cross-linguistic/proposed-shift-rows-greek.md` بلا توصية.",
        "- ترتيب `both`: استُهلكت الرتب 247–326؛ كان overlap=3 في الرتب 247–251، وoverlap=2 في 252–260، وoverlap=1 في 261–326. بقي من الحوض 82 صفا (327–408)، لذلك لم يُستعمل جرد الإتمام المفتوح في `ancient-greek.md`.",
        "- ضبط المصدر: الرتبتان 248 و251 قُرئتا من صف المسح المثبت بعد أن أعاد فهرس الهيكل مدخلين غير مطابقين؛ وبطاقة `Ἄδωνις` قصرت النقل الفينيقي على معنى اسم العلم ولم تورثه لمعنى السمكة أو لمرشح السطح `دنس`.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم ينشأ أي إيداع، ولم يجر شحن؛ تُركت البطاقات مكتوبة للمنسق.",
        "",
        "LANE-A DONE5 80 326",
    ]
    return "\n".join(lines)


def add_lines(value: str) -> str:
    return "\n".join("+" + line for line in value.splitlines())


def emit_reading_chunk(start: int, count: int) -> str:
    if start < FIRST_RANK or start > LAST_RANK or count < 1 or start + count - 1 > LAST_RANK:
        raise AssertionError("نطاق قطعة القراءة خارج الرتب 247–326")
    reading = READING.read_text(encoding="utf-8")
    cards, _records = render_cards()
    positions = {
        int(match.group(1)): match.start()
        for match in re.finditer(r"^### بطاقة: .*LANE-A-R5-(\d{3})$", cards, re.MULTILINE)
    }
    if len(positions) != 80:
        raise AssertionError(f"عدد رؤوس البطاقات المولدة {len(positions)} لا يساوي 80")
    begin = 0 if start == FIRST_RANK else positions[start]
    end = positions.get(start + count, len(cards))
    chunk = cards[begin:end].rstrip()
    if f"LANE-A-R5-{start:03d}" in reading:
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
    if "إلحاق شواهد الجولة الخامسة" in proposal:
        raise AssertionError("إلحاق الجولة الخامسة موجود في ورقة الاقتراح")
    if "LANE-A DONE5" in report:
        raise AssertionError("سطر إتمام الجولة الخامسة موجود")
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
