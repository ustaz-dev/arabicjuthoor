# -*- coding: utf-8 -*-
"""أعد حصاد صفوف «القبطية العربية» المستردة وحدها في دفعات من 150.

العقد هنا ثلاثي لا رباعي: مسار الصوت المسمى، ثم حدث من
``frozen_event.resolve``، ثم معنى الفرع مع مدار مكتوب يدويًا. المروحة أداة
بحث في الرجل الصوتية، ولا يولد هذا السكربت مدارًا أو معنى.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import Counter
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_khashim_latin_coptic_completion as LC  # noqa: E402
import build_khashim_old_latin_cards as LAT  # noqa: E402
import frozen_event as FE  # noqa: E402

SOURCE = ROOT / "data" / "khashim-pairs.json"
RECOVERIES = ROOT / "data" / "khashim-coptic-ocr-recoveries.json"
READING = ROOT / "04-cross-linguistic" / "readings" / "coptic.md"
REPORT = ROOT / "data" / "khashim-coptic-batch-001.json"
BATCH_SIZE = 150
FALLEN = "(سقطَ حرفُه في المسح)"
BOOK = "علي فهمي خشيم، «القبطيّة عربيّة»"
END_MARKER = "<!-- KHASHIM-COPTIC-BATCH-001:END -->"


def valid_coptic_head(value: str) -> bool:
    """اقبل حروف الرومنة اللاتينية الموسعة، ومنها ḥ التي غابت عن النمط القديم."""
    return (
        2 <= len(value) <= 40
        and value[0].isalpha()
        and not re.search(r"[\u0600-\u06ff]", value)
        and all(char.isalpha() or char in ",' -()" for char in value)
    )


def replace_card(text: str, marker: str, replacement: str) -> str:
    pattern = re.compile(
        rf"^### بطاقة:[^\n]*\n{re.escape(marker)}\n.*?"
        rf"(?=^### بطاقة:|^{re.escape(END_MARKER)})",
        re.MULTILINE | re.DOTALL,
    )
    updated, count = pattern.subn(replacement.rstrip() + "\n\n", text, count=1)
    if count != 1:
        raise SystemExit(f"لم يوجد موضع بطاقة وحيد للعلامة {marker}: {count}")
    return updated


def event_payload(event: FE.Ev | None) -> dict[str, Any] | None:
    if event is None:
        return None
    return {
        "text": event.text,
        "source": event.source,
        "tier": event.tier,
        "tier_ar": event.tier_ar,
        "note": event.note,
    }


def preserved_manual_orbits(old_card: dict[str, Any]) -> dict[str, dict[str, str]]:
    """لا يقبل إلا مدارًا سبق أن سمي يدويًا في البطاقة القديمة."""
    out: dict[str, dict[str, str]] = {}
    for candidate in old_card.get("candidate_evaluations", []):
        orbit = str(candidate.get("written_orbit") or "").strip()
        source = str(candidate.get("orbit_source") or "").strip()
        if orbit and "مراجعة بشرية" in source:
            out[str(candidate["root"])] = {"text": orbit, "source": source}
    return out


def proposal_text(proposals: list[dict[str, Any]]) -> str:
    if not proposals:
        return "(لم يسترد اقتراح عربي من صف خشيم)"
    values: list[str] = []
    for proposal in proposals:
        place = (
            f"داخل المروحة في الرتبة {proposal['fan_position']}"
            if proposal.get("fan_position") is not None
            else "خارج المروحة ومحفوظ"
        )
        text = LC.quote(proposal["texts"][0], 220) if proposal.get("texts") else "بلا نص سالم"
        values.append(f"`{proposal['root']}`: {place}؛ «{text}»")
    return " | ".join(values)


def evaluate(
    card_index: int,
    source_index: int,
    row: dict[str, Any],
    old_card: dict[str, Any],
    recovery: dict[str, Any],
) -> dict[str, Any]:
    foreign = str(row.get("foreign") or "").strip()
    sense = str(row.get("foreign_sense") or "").strip()
    valid_head = valid_coptic_head(foreign)
    analysis_head = foreign.split(",", 1)[0].strip()
    fan = LAT.candidate_fan(analysis_head, "") if valid_head else {
        "stem": analysis_head,
        "stripping": "تعذر توليد المروحة لأن الرأس المسترد ليس رومنة صالحة",
        "raw_skeleton": [],
        "stem_skeleton": [],
        "route_skeleton": [],
        "full": [],
    }
    candidates = list(fan["full"])
    manual = preserved_manual_orbits(old_card)
    proposals = LC.khashim_proposals([row])
    proposal_by_root = {str(item["root"]): item for item in proposals}

    candidate_rows: list[dict[str, Any]] = []
    for position, root in enumerate(candidates, 1):
        routed = LAT.candidate_fan(analysis_head, root)
        sound, sound_rows, sound_misses = LC.sound_audit(
            routed["route_skeleton"], root, "القبطيّة", "Coptic"
        )
        event = FE.resolve(root)
        orbit = manual.get(root)
        meaning_ready = bool(sense)
        orbit_ready = bool(meaning_ready and orbit)
        three = {
            "named_sound_path": bool(sound),
            "frozen_event": bool(event),
            "branch_meaning_with_manual_orbit": orbit_ready,
        }
        candidate_rows.append({
            "root": root,
            "fan_position": position,
            "fan_source": routed["source"],
            "route_skeleton": routed["route_skeleton"],
            "sound_ready": bool(sound),
            "sound_rows": sound_rows,
            "sound_misses": sound_misses,
            "frozen_event_ready": bool(event),
            "frozen_event": event_payload(event),
            "branch_meaning": sense or None,
            "branch_meaning_ready": meaning_ready,
            "manual_orbit_ready": orbit_ready,
            "manual_orbit": orbit["text"] if orbit else None,
            "manual_orbit_source": orbit["source"] if orbit else None,
            "three_legs": three,
        })

    by_root = {candidate["root"]: candidate for candidate in candidate_rows}
    for proposal in proposals:
        candidate = by_root.get(str(proposal["root"]))
        proposal["fan_position"] = candidate["fan_position"] if candidate else None
        proposal["fan_status"] = "IN-FAN" if candidate else "OUTSIDE-FAN-PRESERVED"
        proposal["candidate_three_legs"] = candidate["three_legs"] if candidate else None

    positives = [candidate for candidate in candidate_rows
                 if all(candidate["three_legs"].values())]
    winner = min(positives, key=lambda candidate: int(candidate["fan_position"])) \
        if positives else None
    open_reasons: list[str] = []
    if not valid_head:
        open_reasons.append("الرأس المسترد ليس رومنة صالحة لتوليد المروحة")
    elif not candidate_rows:
        open_reasons.append("لم تولد أداة الصوت مرشحًا من الرأس المسترد")
    else:
        if not any(candidate["sound_ready"] for candidate in candidate_rows):
            open_reasons.append("لا مرشح أكمل مسار الصوت المسمى")
        if not any(candidate["frozen_event_ready"] for candidate in candidate_rows):
            open_reasons.append("لا مرشح نزل له حدث من frozen_event.resolve")
        if not any(candidate["manual_orbit_ready"] for candidate in candidate_rows):
            open_reasons.append("معنى الفرع حاضر، لكن لا مدار يدوي مسمى لأي مرشح")
        if not open_reasons and not winner:
            open_reasons.append("لم تجتمع الأرجل الثلاث في مرشح واحد")

    stats = {
        "fan_candidates": len(candidate_rows),
        "sound_ready": sum(candidate["sound_ready"] for candidate in candidate_rows),
        "frozen_event_ready": sum(
            candidate["frozen_event_ready"] for candidate in candidate_rows
        ),
        "manual_orbit_ready": sum(
            candidate["manual_orbit_ready"] for candidate in candidate_rows
        ),
        "three_legs_ready": len(positives),
    }
    legacy = recovery["fields"]["foreign"]["legacy"]
    return {
        "card_index": card_index,
        "language": "coptic",
        "source": "khashim-coptic",
        "source_index": source_index,
        "foreign": foreign,
        "legacy": {"foreign": legacy},
        "sense": sense,
        "source_row_indices": [card_index],
        "source_row_count": 1,
        "source_witness_count": 1,
        "analysis_head": analysis_head,
        "valid_head": valid_head,
        "stripping": fan["stripping"],
        "raw_skeleton": fan["raw_skeleton"],
        "stem_skeleton": fan["stem_skeleton"],
        "fan": candidates,
        "fan_role": "أداة بحث داخل مسار الصوت، وليست رجلًا رابعة",
        "fan_stats": stats,
        "khashim_proposals": proposals,
        "candidate_evaluations": candidate_rows,
        "winner": winner,
        "closure": "READY" if winner else "OPEN-CANDIDATE",
        "verdict": (
            "NUCLEUS-TRACE" if winner and len(winner["root"]) == 2
            else "ROOT-TRACE" if winner else None
        ),
        "open_reasons": open_reasons,
        "ocr_recovery": {
            "legacy_foreign": legacy,
            "recovered_foreign": foreign,
            "page": int(recovery["new_location"]["page"]),
            "line": int(recovery["new_location"]["line"]),
            "alignment_score": recovery["alignment_score"],
            "alignment_evidence": recovery.get("alignment_evidence"),
        },
        "contract": (
            "ثلاث أرجل فقط: مسار الصوت المسمى؛ frozen_event.resolve؛ "
            "معنى الفرع مع مدار يدوي"
        ),
    }


def compact_candidate_scan(card: dict[str, Any]) -> str:
    if not card["candidate_evaluations"]:
        return "(لم تتولد مروحة صوتية)"
    values: list[str] = []
    for candidate in card["candidate_evaluations"]:
        legs = candidate["three_legs"]
        event = candidate["frozen_event"]
        tier = event["tier"] if event else 0
        values.append(
            f"`{candidate['root']}`[ص{'✓' if legs['named_sound_path'] else '×'}،"
            f"ح{tier if legs['frozen_event'] else '×'}،"
            f"م{'✓' if legs['branch_meaning_with_manual_orbit'] else '×'}]"
        )
    return "، ".join(values)


def render_card(card: dict[str, Any]) -> str:
    stats = card["fan_stats"]
    recovery = card["ocr_recovery"]
    marker = f"<!-- khashim-coptic-full-fan:{card['card_index']} -->"
    winner = card["winner"]
    required = "؛ ".join(card["open_reasons"]) or "لا عائق معلق"
    verdict = (
        f"**{card['verdict']} (استكشاف)** بالمقابل `{winner['root']}`"
        if winner else "**غير صادر (استكشاف)**"
    )
    selected_event = (
        FE.resolve(str(winner["root"])).line() if winner else
        "- الحدث المنتخب: لا مرشح محكوم؛ أحداث المرشحين منقولة في سجل الدفعة."
    )
    orbit = winner["manual_orbit"] if winner else (
        "لا مدار يدوي مسمى في البطاقة القديمة، ولم يولد السكربت مدارًا."
    )
    lines = [
        f"### بطاقة: `{card['foreign']}` «{LC.quote(card['sense'])}»؛ khashim-coptic-full-fan/{card['card_index']:03d}",
        marker,
        "- إصدار البروتوكول: COPTIC-OCR-RECOVERY-v1 (استكشاف).",
        f"- الاسترداد: الرأس القديم `{recovery['legacy_foreign']}` محفوظ في `legacy.foreign`؛ الرأس الجديد `{recovery['recovered_foreign']}` من الصفحة {recovery['page']}، سطر OCR {recovery['line']}.",
        f"- نسبة المصدر: معنى الفرع واقتراح خشيم من {BOOK}؛ المسار والحدث والحكم أعمال المشروع.",
        f"- معنى الفرع كما في الصف: «{LC.quote(card['sense'])}».",
        f"- الخطوة صفر: {card['stripping']}؛ الخام `{''.join(card['raw_skeleton']) or '∅'}`؛ البديل `{''.join(card['stem_skeleton']) or '∅'}`.",
        f"- اقتراحات خشيم: {proposal_text(card['khashim_proposals'])}.",
        f"- المروحة الصوتية: {', '.join(f'`{root}`' for root in card['fan']) if card['fan'] else '(فارغة)'}. هي أداة بحث داخل رجل الصوت وليست رجلًا رابعة.",
        f"- فحص المرشحين بثلاث أرجل: {compact_candidate_scan(card)}.",
        f"- الحصيلة: المرشحون={stats['fan_candidates']}؛ الصوت={stats['sound_ready']}؛ الحدث={stats['frozen_event_ready']}؛ المدار اليدوي={stats['manual_orbit_ready']}؛ مكتمل الأرجل={stats['three_legs_ready']}.",
        selected_event,
        f"- المدار اليدوي: {orbit}",
        "- حراسة المدار: معنى الفرع من المصدر، أما تأليف الحدث مع المعنى فلا يكتبه إلا القارئ بيده.",
        f"- عائق: النوع={card['closure']}؛ يتطلب={required}",
        f"- حالة الإغلاق: {card['closure']}",
        f"- الحكم (استكشاف): {verdict}",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    recovery_payload = json.loads(RECOVERIES.read_text(encoding="utf-8"))
    recoveries = sorted(recovery_payload["recoveries"], key=lambda row: int(row["source_index"]))
    total_batches = (len(recoveries) + BATCH_SIZE - 1) // BATCH_SIZE
    if args.batch < 1 or args.batch > total_batches:
        raise SystemExit(f"لا دفعة {args.batch}؛ الصفوف {len(recoveries)} في {total_batches} دفعات")
    start = (args.batch - 1) * BATCH_SIZE
    selected = recoveries[start:start + BATCH_SIZE]

    source_payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    source_rows = [row for row in source_payload["rows"] if row.get("source") == "khashim-coptic"]
    if len(source_rows) != 169:
        raise SystemExit(f"تغير مقام مصدر القبطية عند خشيم: {len(source_rows)}")
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    report_rows = report["rows"]
    offset = len(report_rows) - len(source_rows)
    if offset != 17:
        raise SystemExit(f"تغير مقام الشواهد القبطية السابقة لخشيم: {offset}")

    reading = READING.read_text(encoding="utf-8")
    rendered: list[dict[str, Any]] = []
    table_rows: list[dict[str, Any]] = []
    tiers: Counter[str] = Counter()
    for recovery in selected:
        source_index = int(recovery["source_index"])
        card_index = offset + source_index
        row = source_rows[source_index]
        recovered = recovery["fields"]["foreign"]["recovered"]
        legacy = recovery["fields"]["foreign"]["legacy"]
        if row.get("foreign") != recovered:
            raise SystemExit(f"اختلف الرأس المسترد عند صف المصدر {source_index}")
        if row.get("legacy", {}).get("foreign") != legacy or legacy != FALLEN:
            raise SystemExit(f"لم يحفظ legacy الصحيح عند صف المصدر {source_index}")
        positions = [pos for pos, item in enumerate(report_rows)
                     if int(item["card_index"]) == card_index]
        if len(positions) != 1:
            raise SystemExit(f"البطاقة {card_index} ليست وحيدة في التقرير")
        old_card = report_rows[positions[0]]
        card = evaluate(card_index, source_index, row, old_card, recovery)
        report_rows[positions[0]] = card
        reading = replace_card(
            reading, f"<!-- khashim-coptic-full-fan:{card_index} -->", render_card(card)
        )
        for candidate in card["candidate_evaluations"]:
            event = candidate["frozen_event"]
            tiers[str(event["tier"]) if event else "0"] += 1
        rendered.append(card)
        table_rows.append({
            "source_index": source_index,
            "card_index": card_index,
            "foreign": card["foreign"],
            "legacy_foreign": card["legacy"]["foreign"],
            "arabic_root": row.get("arabic_root"),
            "page": card["ocr_recovery"]["page"],
            "ocr_line": card["ocr_recovery"]["line"],
            "fan_candidates": card["fan_stats"]["fan_candidates"],
            "sound_ready": card["fan_stats"]["sound_ready"],
            "frozen_event_ready": card["fan_stats"]["frozen_event_ready"],
            "manual_orbit_ready": card["fan_stats"]["manual_orbit_ready"],
            "verdict": card["verdict"],
            "open_reasons": card["open_reasons"],
        })

    positive = sum(bool(card["verdict"]) for card in rendered)
    sound_ready = sum(card["fan_stats"]["sound_ready"] for card in rendered)
    event_ready = sum(card["fan_stats"]["frozen_event_ready"] for card in rendered)
    manual_ready = sum(card["fan_stats"]["manual_orbit_ready"] for card in rendered)
    fan_total = sum(card["fan_stats"]["fan_candidates"] for card in rendered)
    report["generated_by"] = (
        "scripts/build_khashim_latin_coptic_completion.py + "
        "scripts/build_khashim_coptic_ocr_recovery_batches.py"
    )
    report["inventory"]["usable_heads"] = sum(bool(row.get("valid_head")) for row in report_rows)
    report["cards_written"] = len(report_rows)
    report["positive"] = sum(bool(row.get("verdict")) for row in report_rows)
    report["open_candidate"] = sum(
        row.get("closure") == "OPEN-CANDIDATE" for row in report_rows
    )
    report["count_links"]["after"] = report["count_links"]["before"] + report["positive"]
    report["ocr_recovery"] = {
        "overlay_rows": len(recoveries),
        "batch_size": BATCH_SIZE,
        "reharvested_through_batch": args.batch,
        "selected_rows": len(rendered),
        "fan_candidates": fan_total,
        "sound_ready": sound_ready,
        "frozen_event_ready": event_ready,
        "manual_orbit_ready": manual_ready,
        "positive": positive,
    }

    batch_payload = {
        "schema": "khashim-coptic-ocr-recovery-batch-v1",
        "generated_by": "scripts/build_khashim_coptic_ocr_recovery_batches.py",
        "batch": args.batch,
        "batch_size": BATCH_SIZE,
        "total_recovered_rows": len(recoveries),
        "total_batches": total_batches,
        "slice": [start, start + len(selected) - 1],
        "rows": table_rows,
        "counts": {
            "rows": len(rendered),
            "restored_foreign_fields": len(rendered),
            "fan_candidates": fan_total,
            "sound_leg_ready_candidates": sound_ready,
            "frozen_event_leg_ready_candidates": event_ready,
            "frozen_event_tiers": dict(sorted(tiers.items())),
            "manual_orbit_ready_candidates": manual_ready,
            "positive_verdicts": positive,
            "open_verdicts": len(rendered) - positive,
        },
        "contract": (
            "ثلاث أرجل فقط: مسار الصوت المسمى؛ frozen_event.resolve؛ "
            "معنى الفرع مع مدار يدوي. لا يولد السكربت مدارًا"
        ),
    }
    out = ROOT / "data" / f"khashim-coptic-ocr-recovery-batch-{args.batch:03d}.json"
    audit = ROOT / "05-audits" / (
        f"2026-08-14-khashim-coptic-ocr-recovery-harvest-batch-{args.batch:03d}.md"
    )
    audit_lines = [
        f"# محضر إعادة حصاد «القبطية العربية»، دفعة الاسترداد {args.batch:03d}",
        "",
        "**التاريخ:** 2026-08-14  ",
        f"**المقام:** {len(rendered)} صفًا مستردًا وحده من أصل {len(recoveries)}؛ الحجم الثابت 150، وهذه الدفعة {args.batch} من {total_batches}.",
        "",
        "## العقد",
        "",
        "الأرجل ثلاث لا رابعة لها: مسار صوت مسمى، ثم حدث من `frozen_event.resolve`، ثم معنى الفرع مع مدار كتبه القارئ بيده. المروحة تعين البحث الصوتي ولا تنشئ رجلًا. لم يولد السكربت مدارًا واحدًا؛ المدار إما مراجعة بشرية سابقة مسماة وإما غائب والحكم مفتوح.",
        "",
        "## الحصيلة",
        "",
        f"- الصفوف المستردة المعاد حصادها: **{len(rendered)}**.",
        f"- حقول الرأس المستردة مع حفظ legacy: **{len(rendered)}**.",
        f"- مرشحو المراوح: **{fan_total}**؛ اكتمل الصوت في **{sound_ready}**.",
        f"- حدث frozen_event موجود: **{event_ready}**؛ الدرجات: " + "، ".join(f"{key}={value}" for key, value in sorted(tiers.items())) + ".",
        f"- مدار يدوي موجود: **{manual_ready}**.",
        f"- الأحكام الموجبة: **{positive}**؛ المفتوحة: **{len(rendered) - positive}**.",
        "",
        "## الصفوف",
        "",
        "| فهرس المصدر | البطاقة | الرأس المسترد | الجذر المنقول | صفحة المصدر | المرشحون | الصوت | الحدث | المدار | الحكم |",
        "|---:|---:|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for row in table_rows:
        audit_lines.append(
            f"| {row['source_index']} | {row['card_index']} | `{row['foreign']}` | `{row['arabic_root']}` | {row['page']} | {row['fan_candidates']} | {row['sound_ready']} | {row['frozen_event_ready']} | {row['manual_orbit_ready']} | {row['verdict'] or 'غير صادر'} |"
        )

    print(json.dumps(batch_payload["counts"], ensure_ascii=False, indent=1))
    if args.dry_run:
        return 0
    READING.write_text(reading, encoding="utf-8", newline="\n")
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n",
                      encoding="utf-8", newline="\n")
    out.write_text(json.dumps(batch_payload, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8", newline="\n")
    audit.write_text("\n".join(audit_lines) + "\n", encoding="utf-8", newline="\n")
    print(f"كتب: {out}")
    print(f"كتب: {audit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
