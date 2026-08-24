#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 23; emit patches only, never commit or ship."""

from __future__ import annotations

from collections import Counter
import argparse
import json
from pathlib import Path
import re
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import harvest_ancient_greek_round22 as R22  # noqa: E402
import harvest_ancient_greek_round7 as R7  # noqa: E402


R21 = R22.R21
R2 = R21.R2
R2.ROUTES.update(R7.NEW_ROUTES)
SWEEP, READING, PROPOSAL, REPORT = R22.SWEEP, R22.READING, R22.PROPOSAL, R22.REPORT
DATE = "2026-08-24"
EXPECTED_POOL = 1_098
SCAN_FROM = 654
EXPECTED_FRESH = 166
EXPECTED_EXISTING = 279
EXPECTED_SOURCE_DUPLICATES = 0
EXPECTED_FIRST_RANK = 655
EXPECTED_LAST_RANK = 996
EXPECTED_FIRST_WORD = "λύται"
EXPECTED_LAST_WORD = "Οὐϊκετία"
BATCH_SIZE = 50
CARD_COUNT = 100
Outcome = R21.Outcome
ORIGINAL_CHOSEN_ENTRY = R2.chosen_entry


def chosen_entry_with_sweep_fallback(row: dict) -> tuple[list[dict], dict, str]:
    """Keep inflected source rows readable when the surface index omits them."""
    entries, how = R2.LEX.look("ancient-greek", str(row["branch"]))
    if entries:
        selected = R2.BASE.select_lexicon(entries, str(row.get("gloss") or ""))
        return entries, entries[selected], how
    if row.get("gloss"):
        read = str(row.get("say") or "").split("  (")[0]
        entry = {
            "word": str(row["branch"]), "read": read, "pos": "inflected form",
            "en": str(row["gloss"]), "etym": "",
        }
        return [entry], entry, "صف المسح القاموسي المسمى؛ فهرس الرسم لا يعيد الصيغة"
    return ORIGINAL_CHOSEN_ENTRY(row)


R2.chosen_entry = chosen_entry_with_sweep_fallback


# Every non-open outcome was hand-read against the complete branch homograph
# set and the complete Arabic-root result set.  Retrieval weight is not proof.
OUTCOMES: dict[int, Outcome] = {
    667: Outcome(
        "root", "روس", "رُوس: بلد، وقيل طائفة من الناس",
        "Rus وKievan Rus هما الروس في العربية اسما للبلد والطائفة؛ الاسم والمسمى واحدان، وحاشية الأصل غير السامي لا تصير شرطا رابعا.", 3,
    ),
    675: Outcome(
        "root", "بز", "بزه: أخذه أو سلبه وحمله بالقوة",
        "seize وtake hold وarrest تلتقي أخذ الشيء وسلبه بالقوة؛ المدار قبض يزيل المقبوض من حيز حركته.", 2,
    ),
    677: Outcome(
        "root", "ليت", "ليت كلمة تمن؛ يقال: ليتني فعلت",
        "wish to bathe يصرح بتمني فعل مطلوب؛ المدار رغبة تتجه إلى حدث لم يقع بعد.", 1,
    ),
    683: Outcome(
        "root", "شد", "شد الشيء: جعله صلبا وربطه وثاقا",
        "make stiff or erect هو إزالة الرخاوة بالشد؛ المدار صلابة الشيء وتماسك بعضه ببعض.", 2,
    ),
    691: Outcome(
        "root", "حن", "الحنين الشوق؛ حن إليه: اشتاق ورغب",
        "crave وyearn وdesire هي الحنين إلى الشيء؛ المدار شوق باطن متجه إلى مطلوب.", 2,
    ),
    693: Outcome(
        "root", "فن", "الفن ضرب ونوع من الشيء؛ والفنون الأنواع",
        "quality وattribute تخصان ضرب الشيء ونوعه؛ المدار وصف يميز صنفا من غيره.", 2,
    ),
    694: Outcome(
        "root", "قر", "القرقرة من الأصوات؛ ويحكى صوت الطائر: قر قر",
        "a small sound or grunt يلتقي حكاية الصوت بـقر والقرقرة؛ المدار صوت قصير خافت يكرر الضربة المسموعة.", 4,
    ),
    903: Outcome(
        "root", "مد", "مددنا القوم: صرنا لهم أنصارا؛ وأمدهم: أعانهم وأغاثهم",
        "protect يلتقي إمداد المحمي بالنصرة والعون؛ المدار دفع الضرر عنه بمدد يصل إليه.", 2,
    ),
    906: Outcome(
        "root", "كد", "كده: أتعبه؛ والكد شدة العمل",
        "trouble وdistress وvex تلتقي إتعاب الشخص وإنهاكه؛ المدار مشقة تقع عليه بعمل شديد.", 2,
    ),
    922: Outcome(
        "law", "كور", "كور الشيء: أداره؛ وكل دور كور",
        "dance وchoral dance وcircling motion تلتقي إدارة الشيء في كور؛ المدار حركة دائرة متعاودة، لكن χ إلى ك بلا صف يوناني مسمى.", 1, "χ ↔ ك",
    ),
    930: Outcome(
        "root", "دين", "الدين ما ثبت في الذمة؛ ودان له: خضع وأطاع",
        "binding وneedful وright وproper تلتقي ما يثبت في الذمة ويلزم أداؤه؛ المدار حكم ملزم أو واجب مستحق.", 1,
    ),
    938: Outcome(
        "root", "ربو", "ربا الشيء: زاد ونما وعلا؛ والربوة ما ارتفع",
        "incline وpreponderate وprevail تلتقي علو الشيء وزيادته على ما يقابله؛ المدار رجحان يرتفع به طرف ويغلب.", 1,
    ),
}


def load_and_select() -> tuple[list[tuple[int, int, dict]], dict]:
    """Load the reading ledger once and select 100 fresh exact surfaces."""
    reading_text = R21.nfc(READING.read_text(encoding="utf-8"))
    if "<!-- LANE-A-GREEK-ROUND22-CHUNK-10:END -->" not in reading_text:
        raise AssertionError("الجولة الثانية والعشرون غير مثبتة")
    if "<!-- LANE-A-GREEK-ROUND23-BATCH-1:START -->" in reading_text:
        raise AssertionError("بطاقات الجولة الثالثة والعشرين موجودة")
    if "LANE-A DONE22 100 653" not in REPORT.read_text(encoding="utf-8"):
        raise AssertionError("خاتمة DONE22 غير مثبتة")

    payload = json.loads(SWEEP.read_text(encoding="utf-8"))
    if payload.get("language") != "ancient_greek":
        raise AssertionError("اختلط لسان الحوض")
    rows = payload.get("both", [])
    if len(rows) != EXPECTED_POOL:
        raise AssertionError(f"تغير مقام الحوض: {len(rows)}")
    ordered = sorted(enumerate(rows, 1), key=lambda item: (-int(item[1].get("overlap") or 0), item[0]))
    fresh: list[tuple[int, int, dict]] = []
    seen: set[str] = set()
    existing = source_duplicates = 0
    for expanded_rank, (source_rank, row) in enumerate(ordered, 1):
        if expanded_rank < SCAN_FROM:
            continue
        word = R21.nfc(row.get("branch"))
        if not word:
            raise AssertionError(f"صف بلا صورة عند {expanded_rank}")
        if word in reading_text:
            existing += 1
            continue
        if word in seen:
            source_duplicates += 1
            continue
        seen.add(word)
        fresh.append((expanded_rank, source_rank, row))

    selected = fresh[:CARD_COUNT]
    actual = (len(fresh), existing, source_duplicates, selected[0][0], selected[-1][0], selected[0][2]["branch"], selected[-1][2]["branch"])
    expected = (EXPECTED_FRESH, EXPECTED_EXISTING, EXPECTED_SOURCE_DUPLICATES, EXPECTED_FIRST_RANK, EXPECTED_LAST_RANK, EXPECTED_FIRST_WORD, EXPECTED_LAST_WORD)
    if actual != expected:
        raise AssertionError(f"تغيرت نافذة الطازج: {actual!r}")
    if len({R21.nfc(item[2]["branch"]) for item in selected}) != CARD_COUNT:
        raise AssertionError("تكررت صورة في النافذة")
    return selected, {
        "pool": len(rows), "scan_from": SCAN_FROM, "existing_rows": existing,
        "source_duplicates": source_duplicates, "fresh_rows": len(fresh),
        "first_rank": selected[0][0], "last_rank": selected[-1][0],
    }


def gather_hits(selected: list[tuple[int, int, dict]]) -> dict[str, list[dict]]:
    R21.OUTCOMES = OUTCOMES
    return R21.gather_hits(selected)


def build_card(expanded_rank: int, source_rank: int, row: dict, hits: dict[str, list[dict]]) -> tuple[str, dict]:
    R21.OUTCOMES = OUTCOMES
    card, record = R21.build_card(expanded_rank, source_rank, row, hits)
    card = card.replace("LANE-A-R21-", "LANE-A-R23-")
    card = card.replace("RECOVERY-v2 (2026-08-18)", f"RECOVERY-v2 ({DATE})")
    card, size = R21.R6.compact_to_limit(card, f"R23-{expanded_rank}")
    record["bytes"] = size
    return card, record


def render_all() -> tuple[str, list[dict], dict]:
    selected, selection = load_and_select()
    hits = gather_hits(selected)
    sections: list[str] = []
    records: list[dict] = []
    for batch in (1, 2):
        batch_rows = selected[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        sections += [
            f"<!-- LANE-A-GREEK-ROUND23-BATCH-{batch}:START -->", "",
            f"## اليونانية، الجولة الثالثة والعشرون: الحوض المضاعف، الدفعة {batch} ({DATE})", "",
            f"- النموذج `WO-B-PROBE-001`؛ 50 بطاقة طازجة؛ الرتبة الموسعة من {batch_rows[0][0]} إلى {batch_rows[-1][0]} بعد بدء المسح من 654 وتجاوز المقروء والمكرر في الذاكرة.",
            "- الترتيب `overlap` نازل ثابت ثم موضع المصدر؛ قرئت المروحة كاملة، ولم يتحول وزن الاسترجاع إلى حكم.", "",
        ]
        for expanded_rank, source_rank, row in batch_rows:
            card, record = build_card(expanded_rank, source_rank, row, hits)
            sections += [card, ""]
            records.append(record)
        sections.append(f"<!-- LANE-A-GREEK-ROUND23-BATCH-{batch}:END -->")
        if batch == 1:
            sections.append("")
    return "\n".join(sections).rstrip(), records, selection


def proposal_addition(records: list[dict]) -> str:
    law = [record for record in records if record["closure"] == "LAW-GAP"]
    grouped: dict[str, list[dict]] = {}
    for record in law:
        _licensed, _route, gaps = R2.sound_route(record["word"], record["root"])
        for gap in dict.fromkeys(gaps):
            grouped.setdefault(gap, []).append(record)
    lines = [
        "## إلحاق شواهد الجولة الثالثة والعشرين، الحوض المضاعف", "",
        "فتشت الشبكة النافذة بكل زوج حرفي وبتسميات الحرف اليوناني وبـ«اليونانية/Greek»؛ وحسبت `BR-GREC-02..06` صفوفا مرخصة. هذه شواهد `LAW-GAP` الطازجة وحدها؛ لا توصية بإضافة صف.", "",
        "| الساق الغائبة | الشواهد الجديدة | الشاهد ومقابله | الحكم النافذ |", "|---|---:|---|---|",
    ]
    for gap, rows in grouped.items():
        examples = "؛ ".join(f"`{row['word']}`→`{row['root']}` «{OUTCOMES[row['expanded_rank']].counterpart}»" for row in rows)
        lines.append(f"| `{gap}` | {len(rows)} | {examples} | لا صف مجمد مسمى؛ تبقى البطاقات `LAW-GAP` |")
    lines += ["", "تبقى هذه البطاقات في `LAW-GAP` إلى قرار المؤلف؛ الإلحاق شاهد فقط."]
    return "\n".join(lines)


def report_addition(records: list[dict], selection: dict) -> str:
    first, second = records[:BATCH_SIZE], records[BATCH_SIZE:]

    def counts(rows: list[dict], field: str) -> str:
        return "؛ ".join(f"`{key}`={value}" for key, value in sorted(Counter(row[field] for row in rows).items()))

    law = [record for record in records if record["closure"] == "LAW-GAP"]
    return "\n".join([
        "<!-- LANE-A-GREEK-ROUND23-REPORT:START -->", "",
        f"## {DATE}، الجولة الثالثة والعشرون، الحوض المضاعف، الدفعة 1", "",
        f"- البطاقات: 50؛ الرتبة الموسعة: {first[0]['expanded_rank']} إلى {first[-1]['expanded_rank']}؛ آخر `overlap`={first[-1]['overlap']}.",
        "- توزيع الأحكام: " + counts(first, "verdict") + ".", "- توزيع الإغلاق: " + counts(first, "closure") + ".", "",
        f"## {DATE}، الجولة الثالثة والعشرون، الحوض المضاعف، الدفعة 2", "",
        f"- البطاقات: 50؛ الرتبة الموسعة: {second[0]['expanded_rank']} إلى {second[-1]['expanded_rank']}؛ آخر `overlap`={second[-1]['overlap']}.",
        "- توزيع الأحكام: " + counts(second, "verdict") + ".", "- توزيع الإغلاق: " + counts(second, "closure") + ".", "",
        "## حصيلة الجولة الثالثة والعشرين", "",
        f"- استؤنف المسح من الرتبة {selection['scan_from']}؛ تجاوزت الرتبة 654 لحضور صورتها؛ أول بطاقة طازجة={selection['first_rank']}.",
        f"- من 654 إلى آخر الحوض: المقروء={selection['existing_rows']}؛ تكرار المصدر المضبوط في الذاكرة={selection['source_duplicates']}؛ الطازج={selection['fresh_rows']}.",
        "- مجموع البطاقات: 100؛ دفعتان من 50 بطاقة بنموذج `WO-B-PROBE-001`.",
        "- الإغلاق الكلي: " + counts(records, "closure") + ".", "- الحكم الكلي: " + counts(records, "verdict") + ".",
        f"- فجوات القانون الطازجة: {len(law)}؛ ألحقت شواهدها في `proposed-shift-rows-greek.md` بعد احتساب `BR-GREC-02..06` صفوفا نافذة.",
        f"- حد الحجم: أكبر بطاقة {max(record['bytes'] for record in records)} بايت؛ لا بطاقة تجاوزت 5 كيلوبايت.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم يستعمل git إطلاقا.", "",
        "<!-- LANE-A-GREEK-ROUND23-REPORT:END -->", "", f"LANE-A DONE23 {len(records)} {records[-1]['expanded_rank']}",
    ])


def stage_patches() -> Path:
    rendered, records, selection = render_all()
    cards = [m.group(0).rstrip() for m in re.finditer(r"(?ms)^### بطاقة:.*?(?=^### بطاقة:|^<!-- LANE-A-GREEK-ROUND23-BATCH-[12]:END -->)", rendered)]
    if len(cards) != CARD_COUNT:
        raise AssertionError(f"تعذر تفكيك البطاقات: {len(cards)}")
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round23-"))
    previous_anchor = "<!-- LANE-A-GREEK-ROUND22-CHUNK-10:END -->"
    chunk_number = 0
    for batch in (1, 2):
        batch_records = records[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        batch_cards = cards[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        for offset in range(0, BATCH_SIZE, 10):
            chunk_number += 1
            lines: list[str] = []
            if offset == 0:
                lines += [f"<!-- LANE-A-GREEK-ROUND23-BATCH-{batch}:START -->", "", f"## اليونانية، الجولة الثالثة والعشرون: الحوض المضاعف، الدفعة {batch} ({DATE})", "", f"- النموذج `WO-B-PROBE-001`؛ 50 بطاقة طازجة؛ الرتبة الموسعة من {batch_records[0]['expanded_rank']} إلى {batch_records[-1]['expanded_rank']} بعد بدء المسح من 654 وتجاوز المقروء والمكرر في الذاكرة.", "- الترتيب `overlap` نازل ثابت ثم موضع المصدر؛ قرئت المروحة كاملة، ولم يتحول وزن الاسترجاع إلى حكم.", ""]
            for card in batch_cards[offset:offset + 10]:
                lines += [card, ""]
            if offset + 10 == BATCH_SIZE:
                lines += [f"<!-- LANE-A-GREEK-ROUND23-BATCH-{batch}:END -->", ""]
            marker = f"<!-- LANE-A-GREEK-ROUND23-CHUNK-{chunk_number:02d}:END -->"
            lines.append(marker)
            (stage / f"reading-{chunk_number:02d}.patch").write_text(R22.append_patch(READING, "\n".join(lines), previous_anchor), encoding="utf-8", newline="\n")
            previous_anchor = marker

    proposal_anchor = "تبقى هذه البطاقات في `LAW-GAP` إلى قرار المؤلف؛ الإلحاق شاهد فقط."
    tail = ["*** Begin Patch", "*** Update File: 04-cross-linguistic/proposed-shift-rows-greek.md", "@@", " " + proposal_anchor, "+", R22.add_lines(proposal_addition(records)), "*** Update File: _inbox/lane-reports/2026-08-16-A.md", "@@", " LANE-A DONE22 100 653", "+", R22.add_lines(report_addition(records, selection)), "*** End Patch", ""]
    (stage / "proposal-report.patch").write_text("\n".join(tail), encoding="utf-8", newline="\n")
    return stage


def verify_installed() -> dict:
    reading = READING.read_text(encoding="utf-8")
    ids = re.findall(r"^### بطاقة:.*LANE-A-R23-(\d+)$", reading, re.MULTILINE)
    markers = re.findall(r"<!-- LANE-A-GREEK-ROUND23-CHUNK-\d{2}:END -->", reading)
    done = f"LANE-A DONE23 {CARD_COUNT} {EXPECTED_LAST_RANK}"
    if len(ids) != CARD_COUNT or len(set(ids)) != CARD_COUNT or len(markers) != 10 or done not in REPORT.read_text(encoding="utf-8"):
        raise AssertionError(f"التحقق فشل: بطاقات={len(ids)} وقطع={len(markers)}")
    return {"cards": len(ids), "chunks": len(markers), "first_id": int(ids[0]), "last_id": int(ids[-1]), "done": done}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", action="store_true")
    parser.add_argument("--verify-installed", action="store_true")
    parser.add_argument("--records", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.verify_installed:
        print(json.dumps(verify_installed(), ensure_ascii=False, indent=2)); return 0
    if args.stage:
        print(stage_patches()); return 0
    _rendered, records, selection = render_all()
    print(json.dumps({**selection, "cards": len(records), "closures": dict(Counter(r["closure"] for r in records)), "verdicts": dict(Counter(r["verdict"] for r in records)), "max_bytes": max(r["bytes"] for r in records)}, ensure_ascii=False, indent=2))
    if args.records:
        for record in records:
            print(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
