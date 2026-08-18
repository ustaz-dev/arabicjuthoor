#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 21 from the expanded Ancient Greek ``both`` pool.

The reading ledger is loaded once, normalized to NFC, and retained in memory
while every expanded-pool form is deduplicated by exact surface occurrence.
The remaining rows are stably ordered by descending overlap and source order.
Only the first one hundred fresh rows are read, as two batches of fifty, under
the WO-B-PROBE-001 full-card contract.  This renderer emits patches only; it
does not commit, push, or invoke the shipping workflow.
"""

from __future__ import annotations

from collections import Counter
import argparse
import json
from pathlib import Path
import re
import sys
import tempfile
import unicodedata


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import harvest_ancient_greek_round2 as R2  # noqa: E402
import harvest_ancient_greek_round6 as R6  # noqa: E402


SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-ancient_greek.json"
READING = ROOT / "04-cross-linguistic" / "readings" / "ancient-greek.md"
PROPOSAL = ROOT / "04-cross-linguistic" / "proposed-shift-rows-greek.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-A.md"
DATE = "2026-08-18"
EXPECTED_POOL = 1_098
BATCH_SIZE = 50
CARD_COUNT = 100


Outcome = R2.Outcome


# Hand-read outcomes are keyed by the stable rank in the expanded pool after
# descending-overlap sorting.  Retrieval alone never fills this table.
OUTCOMES: dict[int, Outcome] = {
    5: Outcome(
        "law", "ردد", "رد الشيء: صرفه ورجعه ومنعه من وجهه",
        "keep back وrestrain وkeep away هي رد الشيء وصرفه عن وجهه في الشواهد العربية؛ المعنى مباشر، لكن τ إلى د بلا صف يوناني مسمى.",
        1, "τ ↔ د",
    ),
    12: Outcome(
        "root", "حسس", "الحس والحسيس: الصوت الخفي",
        "sound وnoise وecho في الفرع تقع في الحس والحسيس العربيين؛ المدار صوت يصل إلى الحس، والشاهد العربي يسمي الصوت نفسه.",
        1,
    ),
    19: Outcome(
        "law", "وفق", "وفق الشيء: ما لاءمه؛ والوفاق الموافقة",
        "to suit وfit وproper تطابق وفق الشيء وملاءمته؛ المعنى مباشر، لكن π إلى ف بلا صف يوناني مسمى.",
        1, "π ↔ ف",
    ),
    20: Outcome(
        "root", "ورد", "ورد الماء: بلغه؛ وأورده غيره وسقاه",
        "to water وirrigate وgive drink to cattle هي إيراد الماء وبلوغ الماشية مورده؛ المدار بلوغ الماء أو إبلاغه إلى الشارب.",
        1,
    ),
    41: Outcome(
        "law", "قدس", "القدس: الطهر؛ والتقديس التطهير والتنزيه",
        "holiness وsanctity تطابقان القدس والتقديس في العربية؛ المعنى مباشر، لكن γ إلى ق وτ إلى د كلاهما بلا صف يوناني مسمى.",
        1, "γ ↔ ق",
    ),
    55: Outcome(
        "root", "شم", "شم الشيء: أدرك رائحته؛ والشم حاسة الرائحة",
        "smell وscent وodour هي الشم العربي نفسه؛ المدار جمع أثر الرائحة المنتشر إلى الحاسة.",
        2,
    ),
    70: Outcome(
        "transmission", "دن", "الأكادية dannu والأوغاريتية dn والآرامية صور مسماة لإناء الخزن",
        "قاموس الفرع يصرح بأن اسم جرة الخمر اقتراض سامي من الأكادية مع شاهد أوغاريتي وآرامي؛ انتقال مسمى لا حكم إرث.",
    ),
    104: Outcome(
        "transmission", "سام", "العبرية الكتابية שֵׁם šēm هي المانح المسمى لاسم سام",
        "قاموس الفرع يصرح باقتراض Σήμ من العبرية الكتابية שֵׁם؛ انتقال اسم علم من مانح سامي مسمى.",
    ),
    119: Outcome(
        "law", "صوف", "الصوف للضأن؛ والصوفة أخص منه",
        "lanolin شحم مستخرج من صوف الغنم، فالمادة ومصدرها الليفي في مدار واحد؛ لكن π إلى ف بلا صف يوناني مسمى.",
        1, "π ↔ ف",
    ),
    120: Outcome(
        "root", "طول", "طال الشيء: امتد؛ والطول خلاف القصر",
        "at a distance وfar away هما بعد ناشئ من امتداد المسافة؛ المدار الطول المكاني المباشر.",
        1,
    ),
    265: Outcome(
        "law", "سدد", "السد إغلاق الخلل وردم الثلم حتى يمنع النفاذ",
        "stuff full وcram وpack وpress close هي ملء الفراغ بمادة متراكمة حتى ينسد؛ المعنى والحدث مباشران، لكن موضعي τ إلى د بلا صف يوناني مسمى.",
        1, "τ ↔ د",
    ),
    346: Outcome(
        "transmission", "ريح", "العبرية الكتابية יְרִיחוֹ Yərīḥō هي مانح اسم أريحا",
        "قاموس الفرع يصرح باقتراض Ἰεριχώ من العبرية الكتابية יְרִיחוֹ؛ انتقال اسم موضع من مانح سامي مسمى.",
    ),
    375: Outcome(
        "root", "وجس", "الوجس فزعة القلب؛ وأوجس في نفسه خيفة",
        "awe وdread في الفرع يلتقيان فزعة القلب والخيفة المضمرة في الوجس العربي؛ المدار أثر دقيق يقع في النفس.",
        1,
    ),
    384: Outcome(
        "root", "وطر", "الوطر كل حاجة تكون فيها همة ورغبة",
        "heart بوصفه seat of passion and desire يحمل الحاجة والرغبة نفسها التي تسميها العربية وطرا؛ المدار رغبة محدودة في مطلوب.",
        1,
    ),
    422: Outcome(
        "law", "ذل", "الذل ضد العز؛ والذلول المنقاد",
        "female slave هي المستذلة المنقادة في مدار الذل العربي؛ المعنى مباشر، لكن δ إلى ذ بلا صف يوناني مسمى.",
        2, "δ ↔ ذ",
    ),
    439: Outcome(
        "law", "ذل", "ذل: انقاد وخضع؛ والتذليل إخضاع الشيء",
        "to be a slave وserve وbe subject تطابق الانقياد والخضوع في الذل العربي؛ المعنى مباشر، لكن δ إلى ذ بلا صف يوناني مسمى.",
        2, "δ ↔ ذ",
    ),
}


def nfc(value: object) -> str:
    return unicodedata.normalize("NFC", str(value or ""))


def load_and_select() -> tuple[list[tuple[int, int, dict]], dict]:
    """Load the ledger once and select the first hundred exact-form-fresh rows."""
    reading_text = nfc(READING.read_text(encoding="utf-8"))
    if "<!-- LANE-A-GREEK-ROUND21-BATCH-1:START -->" in reading_text:
        raise AssertionError("بطاقات الجولة الحادية والعشرين موجودة؛ لا يعاد انتخاب نافذة لاحقة بالمواصفات التاريخية نفسها")
    payload = json.loads(SWEEP.read_text(encoding="utf-8"))
    if payload.get("language") != "ancient_greek":
        raise AssertionError("اختلط لسان حوض المسح")
    source_rows = payload.get("both", [])
    if len(source_rows) != EXPECTED_POOL:
        raise AssertionError(f"تغير مقام الحوض المضاعف: {len(source_rows)}")
    ordered = sorted(
        enumerate(source_rows, 1),
        key=lambda item: (-int(item[1].get("overlap") or 0), item[0]),
    )
    fresh: list[tuple[int, int, dict]] = []
    skipped = 0
    for expanded_rank, (source_rank, row) in enumerate(ordered, 1):
        word = nfc(row.get("branch"))
        if not word:
            raise AssertionError(f"صف بلا صورة عند الرتبة الموسعة {expanded_rank}")
        if word in reading_text:
            skipped += 1
            continue
        fresh.append((expanded_rank, source_rank, row))
    selected = fresh[:CARD_COUNT]
    if len(selected) != CARD_COUNT:
        raise AssertionError(f"الطازج أقل من نافذة الجولة: {len(selected)}")
    if len({nfc(row[2]["branch"]) for row in selected}) != CARD_COUNT:
        raise AssertionError("تكررت صورة داخل نافذة الطازج")
    return selected, {
        "pool": len(source_rows),
        "skipped_rows": skipped,
        "fresh_rows": len(fresh),
        "last_rank": selected[-1][0],
    }


def gather_hits(selected: list[tuple[int, int, dict]]) -> dict[str, list[dict]]:
    roots: set[str] = set()
    for expanded_rank, _source_rank, row in selected:
        outcome = OUTCOMES.get(expanded_rank)
        if outcome:
            roots.add(outcome.root)
        roots.update(candidate for candidate, _weight in R2.FAN.rank(
            str(row["branch"]), R2.FAN.fan(str(row["branch"]), "greek"), "greek"
        ))
    return R2.AR.matches_for_roots(R2.AR.DEFAULT_RESOURCES, roots, None)


def build_card(
    expanded_rank: int,
    source_rank: int,
    row: dict,
    hits: dict[str, list[dict]],
) -> tuple[str, dict]:
    R2.OUTCOMES = OUTCOMES
    R2.aligned_arabic = R6.aligned_arabic
    original_limit = R2.MAX_CARD_BYTES
    R2.MAX_CARD_BYTES = 64 * 1024
    try:
        card, record = R2.build_card(expanded_rank, row, hits)
    finally:
        R2.MAX_CARD_BYTES = original_limit
    card = card.replace("LANE-A-R2-", "LANE-A-R21-")
    card = card.replace(
        "- إصدار البروتوكول: RECOVERY-v2 (2026-08-16)؛ الطبقة: استكشاف.",
        f"- إصدار البروتوكول: RECOVERY-v2 ({DATE})؛ النموذج: WO-B-PROBE-001؛ الطبقة: استكشاف.",
    )
    card = card.replace(
        f"رتبة `both`={expanded_rank}",
        f"رتبة الحوض الموسع={expanded_rank}؛ موضع المصدر={source_rank}",
    )
    if expanded_rank == 18:
        card = card.replace(
            "- المدار: قوبل معنى الفرع «to yoke or join together؛ to close or shut off؛ to bring under the yoke or subdue» بكل معاني `زوج` وبدرجات الحدث؛ ولم يثبت مدار محدود من غير تعميم أو قفزة، فبقي المرشح مفتوحا بمطلوبه المسمى.",
            "- المدار: join together يلتقي اقتران الزوجين وارتباطهما، لكن المدخلة مشتقة من `ζυγόν` التي تحمل صورتها الهيلينية الأقدم صامتا زائدا سبق أن أبقى بطاقة الأصل مفتوحة؛ لا ترث المشتقة حكما موجبا قبل حل ذلك الصامت.",
        )
        card = card.replace(
            "- عائق: يتطلب مدارا محدودا يجمع معنى الفرع بمعنى عربي مقروء؛ لا يضاف شرط رابع.",
            "- عائق: النوع=OPEN-CANDIDATE؛ يتطلب=حل الصامت الزائد في الصورة الهيلينية الأقدم لقاعدة `ζυγόν` قبل أي حكم للمشتقة.",
        )
    if expanded_rank == 20:
        named: list[dict] = []
        for source_id in ("al_sihah", "asas_al_balagha"):
            named.append(next(
                match for match in hits.get("ورد", [])
                if R2.AR.canonical_source_id(str(match.get("source") or "")) == source_id
            ))
        witness = "؛ ".join(
            f"{R2.source_name(match)}: «{R2.clip(match.get('definition'), 85)}»"
            for match in named
        )
        card = re.sub(
            r"^- مسح المعاني العربية:.*$",
            f"- مسح المعاني العربية: قُرئت {len(hits.get('ورد', []))} نتيجة للجذر `ورد` بـ`--max-chars 0`؛ {witness}.",
            card,
            flags=re.MULTILINE,
        )
    card, size = R6.compact_to_limit(card, f"R21-{expanded_rank}")
    record.update({
        "bytes": size,
        "expanded_rank": expanded_rank,
        "source_rank": source_rank,
        "overlap": int(row.get("overlap") or 0),
    })
    return card, record


def render_all() -> tuple[str, list[dict], dict]:
    selected, selection = load_and_select()
    hits = gather_hits(selected)
    sections: list[str] = []
    records: list[dict] = []
    for batch in (1, 2):
        batch_rows = selected[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        first_rank, last_rank = batch_rows[0][0], batch_rows[-1][0]
        sections += [
            f"<!-- LANE-A-GREEK-ROUND21-BATCH-{batch}:START -->",
            "",
            f"## اليونانية، الجولة الحادية والعشرون: الحوض المضاعف، الدفعة {batch} ({DATE})",
            "",
            f"- النموذج `WO-B-PROBE-001`؛ 50 بطاقة طازجة؛ الرتبة الموسعة من {first_rank} إلى {last_rank} مع تجاوز كل صف صورتُه حاضرة في سجل القراءة.",
            "- الترتيب `overlap` نازل ثابت ثم موضع المصدر؛ قُرئت المروحة كاملة، ولم يتحول وزن الاسترجاع إلى حكم.",
            "",
        ]
        for expanded_rank, source_rank, row in batch_rows:
            card, record = build_card(expanded_rank, source_rank, row, hits)
            sections += [card, ""]
            records.append(record)
        sections.append(f"<!-- LANE-A-GREEK-ROUND21-BATCH-{batch}:END -->")
        if batch == 1:
            sections.append("")
    if len(records) != CARD_COUNT:
        raise AssertionError(f"عدد بطاقات الجولة {len(records)}")
    return "\n".join(sections).rstrip(), records, selection


def proposal_addition(records: list[dict]) -> str:
    law = [record for record in records if record["closure"] == "LAW-GAP"]
    if not law:
        return ""
    grouped: dict[str, list[dict]] = {}
    for record in law:
        _licensed, _route, gaps = R2.sound_route(record["word"], record["root"])
        if not gaps:
            raise AssertionError(f"بطاقة LAW-GAP بلا ساق غائبة: {record['expanded_rank']}")
        for gap in dict.fromkeys(gaps):
            grouped.setdefault(gap, []).append(record)
    lines = [
        "## إلحاق شواهد الجولة الحادية والعشرين، الحوض المضاعف",
        "",
        "هذه شواهد `LAW-GAP` الطازجة وحدها من دفعتَي `WO-B-PROBE-001`؛ لا توصية بإضافة صف، ولا تعديل للشبكة النافذة.",
        "",
        "| الساق الغائبة | الشواهد الجديدة | أمثلة بأسمائها | الحكم النافذ |",
        "|---|---:|---|---|",
    ]
    for gap, rows in grouped.items():
        examples = "؛ ".join(
            f"`{row['word']}`→`{row['root']}` «{OUTCOMES[row['expanded_rank']].counterpart}»"
            for row in rows
        )
        lines.append(
            f"| `{gap}` | {len(rows)} | {examples} | لا صف مجمد مسمى؛ تبقى البطاقات `LAW-GAP` |"
        )
    lines += [
        "",
        "تبقى هذه البطاقات في `LAW-GAP` إلى قرار المؤلف؛ الإلحاق شاهد فقط.",
    ]
    return "\n".join(lines)


def report_addition(records: list[dict], selection: dict) -> str:
    first, second = records[:BATCH_SIZE], records[BATCH_SIZE:]

    def counts(rows: list[dict], field: str) -> str:
        return "؛ ".join(
            f"`{key}`={value}" for key, value in sorted(Counter(row[field] for row in rows).items())
        )

    law = [record for record in records if record["closure"] == "LAW-GAP"]
    lines = [
        "<!-- LANE-A-GREEK-ROUND21-REPORT:START -->",
        "",
        f"## {DATE}، الجولة الحادية والعشرون، الحوض المضاعف، الدفعة 1",
        "",
        f"- البطاقات: 50؛ الرتبة الموسعة: {first[0]['expanded_rank']} إلى {first[-1]['expanded_rank']}؛ آخر `overlap`={first[-1]['overlap']}.",
        "- توزيع الأحكام: " + counts(first, "verdict") + ".",
        "- توزيع الإغلاق: " + counts(first, "closure") + ".",
        "",
        f"## {DATE}، الجولة الحادية والعشرون، الحوض المضاعف، الدفعة 2",
        "",
        f"- البطاقات: 50؛ الرتبة الموسعة: {second[0]['expanded_rank']} إلى {second[-1]['expanded_rank']}؛ آخر `overlap`={second[-1]['overlap']}.",
        "- توزيع الأحكام: " + counts(second, "verdict") + ".",
        "- توزيع الإغلاق: " + counts(second, "closure") + ".",
        "",
        "## حصيلة الجولة الحادية والعشرين",
        "",
        f"- الحوض: {selection['pool']} صفا؛ المتجاوز بصورته الموجودة={selection['skipped_rows']}؛ الطازج المتبقي={selection['fresh_rows']}.",
        "- مجموع البطاقات: 100؛ دفعتان من 50 بطاقة بنموذج `WO-B-PROBE-001`.",
        "- الترتيب: `overlap` نازل ثابت ثم موضع المصدر؛ لا صف مكرر الصورة دخل النافذة.",
        "- الإغلاق الكلي: " + counts(records, "closure") + ".",
        "- الحكم الكلي: " + counts(records, "verdict") + ".",
        f"- فجوات القانون الطازجة: {len(law)}؛ ألحقت شواهدها في `proposed-shift-rows-greek.md` بلا توصية ولا تعديل للشبكة.",
        f"- حد الحجم: أكبر بطاقة {max(record['bytes'] for record in records)} بايت؛ لا بطاقة تجاوزت 5 كيلوبايت.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم ينشأ إيداع، ولم يجر شحن.",
        "",
        "<!-- LANE-A-GREEK-ROUND21-REPORT:END -->",
        "",
        f"LANE-A DONE21 {len(records)} {records[-1]['expanded_rank']}",
    ]
    return "\n".join(lines)


def add_lines(value: str) -> str:
    return "\n".join("+" + line for line in value.splitlines())


def append_patch(path: Path, fragment: str, anchor: str) -> str:
    return "\n".join([
        "*** Begin Patch",
        f"*** Update File: {path.relative_to(ROOT).as_posix()}",
        "@@",
        f" {anchor}",
        "+",
        add_lines(fragment.rstrip()),
        "*** End Patch",
        "",
    ])


def combined_patch() -> str:
    cards, records, selection = render_all()
    proposal = proposal_addition(records)
    report = report_addition(records, selection)
    patch = [
        "*** Begin Patch",
        "*** Update File: 04-cross-linguistic/readings/ancient-greek.md",
        "@@",
        " <!-- LANE-A-GREEK-ROUND20-BATCH-2:END -->",
        "+",
        add_lines(cards),
    ]
    if proposal:
        patch += [
            "*** Update File: 04-cross-linguistic/proposed-shift-rows-greek.md",
            "@@",
            " تبقى البطاقتان في `LAW-GAP` إلى أن يقرر المؤلف في الشبكة المجمدة؛ لا تحمل هذه الورقة توصية.",
            "+",
            add_lines(proposal),
        ]
    patch += [
        "*** Update File: _inbox/lane-reports/2026-08-16-A.md",
        "@@",
        " LANE-A DONE20 100 LANE-A-OPEN-COMP-01320",
        "+",
        add_lines(report),
        "*** End Patch",
        "",
    ]
    return "\n".join(patch)


def stage_patches() -> Path:
    """Render once, then stage bounded apply_patch inputs in the system temp."""
    rendered, records, selection = render_all()
    cards = [match.group(0).rstrip() for match in re.finditer(
        r"(?ms)^### بطاقة:.*?(?=^### بطاقة:|^<!-- LANE-A-GREEK-ROUND21-BATCH-[12]:END -->)",
        rendered,
    )]
    if len(cards) != CARD_COUNT:
        raise AssertionError(f"تعذر تفكيك البطاقات المرحلية: {len(cards)}")
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round21-"))
    previous_anchor = "<!-- LANE-A-GREEK-ROUND20-BATCH-2:END -->"
    chunk_number = 0
    for batch in (1, 2):
        batch_records = records[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        batch_cards = cards[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        for offset in range(0, BATCH_SIZE, 10):
            chunk_number += 1
            chunk_cards = batch_cards[offset:offset + 10]
            lines: list[str] = []
            if offset == 0:
                lines += [
                    f"<!-- LANE-A-GREEK-ROUND21-BATCH-{batch}:START -->",
                    "",
                    f"## اليونانية، الجولة الحادية والعشرون: الحوض المضاعف، الدفعة {batch} ({DATE})",
                    "",
                    f"- النموذج `WO-B-PROBE-001`؛ 50 بطاقة طازجة؛ الرتبة الموسعة من {batch_records[0]['expanded_rank']} إلى {batch_records[-1]['expanded_rank']} مع تجاوز كل صف صورتُه حاضرة في سجل القراءة.",
                    "- الترتيب `overlap` نازل ثابت ثم موضع المصدر؛ قُرئت المروحة كاملة، ولم يتحول وزن الاسترجاع إلى حكم.",
                    "",
                ]
            for card in chunk_cards:
                lines += [card, ""]
            if offset + 10 == BATCH_SIZE:
                lines += [f"<!-- LANE-A-GREEK-ROUND21-BATCH-{batch}:END -->", ""]
            chunk_marker = f"<!-- LANE-A-GREEK-ROUND21-CHUNK-{chunk_number:02d}:END -->"
            lines.append(chunk_marker)
            patch = append_patch(READING, "\n".join(lines), previous_anchor)
            (stage / f"reading-{chunk_number:02d}.patch").write_text(
                patch, encoding="utf-8", newline="\n"
            )
            previous_anchor = chunk_marker

    proposal = proposal_addition(records)
    report = report_addition(records, selection)
    tail_patch = ["*** Begin Patch"]
    if proposal:
        tail_patch += [
            "*** Update File: 04-cross-linguistic/proposed-shift-rows-greek.md",
            "@@",
            " تبقى البطاقتان في `LAW-GAP` إلى أن يقرر المؤلف في الشبكة المجمدة؛ لا تحمل هذه الورقة توصية.",
            "+",
            add_lines(proposal),
        ]
    tail_patch += [
        "*** Update File: _inbox/lane-reports/2026-08-16-A.md",
        "@@",
        " LANE-A DONE20 100 LANE-A-OPEN-COMP-01320",
        "+",
        add_lines(report),
        "*** End Patch",
        "",
    ]
    (stage / "proposal-report.patch").write_text(
        "\n".join(tail_patch), encoding="utf-8", newline="\n"
    )
    return stage


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", action="store_true")
    parser.add_argument("--records", action="store_true")
    parser.add_argument("--patch", action="store_true")
    parser.add_argument("--stage", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.selection:
        selected, meta = load_and_select()
        print(json.dumps(meta, ensure_ascii=False, sort_keys=True))
        for fresh_number, (expanded_rank, source_rank, row) in enumerate(selected, 1):
            print(json.dumps({
                "fresh": fresh_number,
                "expanded_rank": expanded_rank,
                "source_rank": source_rank,
                "branch": row.get("branch"),
                "say": row.get("say"),
                "skeleton": row.get("skeleton"),
                "gloss": row.get("gloss"),
                "best": row.get("best"),
                "overlap": row.get("overlap"),
                "shared": row.get("shared"),
                "direct": row.get("direct"),
                "loan_suspect": row.get("loan_suspect"),
                "candidates": list(row.get("candidates_found") or [])[:20],
            }, ensure_ascii=False, separators=(",", ":")))
        return 0
    if args.patch:
        print(combined_patch(), end="")
        return 0
    if args.stage:
        print(stage_patches())
        return 0
    _cards, records, selection = render_all()
    print(json.dumps({
        **selection,
        "cards": len(records),
        "closures": dict(Counter(record["closure"] for record in records)),
        "verdicts": dict(Counter(record["verdict"] for record in records)),
        "max_bytes": max(record["bytes"] for record in records),
    }, ensure_ascii=False, indent=2))
    if args.records:
        for record in records:
            print(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
