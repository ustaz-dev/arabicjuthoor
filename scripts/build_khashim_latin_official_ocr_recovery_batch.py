# -*- coding: utf-8 -*-
"""أعد حصاد رؤوس «اللاتينية العربية» المستردة وحدها، في دفعة من 150.

الأرجل ثلاث: مسار الصوت المسمى، وحدث ``frozen_event.resolve``، ومعنى الفرع
مع مدار مكتوب يدويًا. المروحة داخل الرجل الصوتية، ولا ينشئ هذا المسار مدارًا.
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
RECOVERIES = ROOT / "data" / "khashim-latin-official-ocr-recoveries.json"
READING = ROOT / "04-cross-linguistic" / "readings" / "old-latin.md"
OUT = ROOT / "data" / "khashim-latin-ocr-recovery-batch-001.json"
AUDIT = ROOT / "05-audits" / "2026-08-14-khashim-latin-ocr-recovery-harvest-batch-001.md"
START = "<!-- KHASHIM-LATIN-OFFICIAL-OCR-RECOVERY-BATCH-001:START -->"
END = "<!-- KHASHIM-LATIN-OFFICIAL-OCR-RECOVERY-BATCH-001:END -->"
BATCH_SIZE = 150
FALLEN = "(سقطَ حرفُه في المسح)"
BOOK = "علي فهمي خشيم، «اللاتينيّة عربيّة»"


def replace_block(text: str, block: str) -> str:
    if START in text and END in text:
        pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
        updated, count = pattern.subn(block, text, count=1)
        if count != 1:
            raise SystemExit(f"اختل موضع كتلة الاسترداد اللاتيني: {count}")
        return updated
    return text.rstrip() + "\n\n" + block.rstrip() + "\n"


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


def analysis_head(foreign: str) -> str:
    """المادة الأولى من رأس قد يطبع معه المؤلف تصريفاته مفصولة بفواصل."""
    return foreign.split(",", 1)[0].strip()


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
    source_index: int,
    row: dict[str, Any],
    recovery: dict[str, Any],
) -> dict[str, Any]:
    foreign = str(row.get("foreign") or "").strip()
    sense = str(row.get("foreign_sense") or "").strip()
    head = analysis_head(foreign)
    fan = LAT.candidate_fan(head, "")
    candidates = list(fan["full"])
    proposals = LC.khashim_proposals([row])
    manual: dict[str, str] = {}
    for root in candidates:
        orbit = LC.LATIN_MANUAL_ORBITS.get((foreign, root))
        if orbit is None:
            orbit = LC.LATIN_MANUAL_ORBITS.get((head, root))
        if orbit:
            manual[root] = orbit

    candidate_rows: list[dict[str, Any]] = []
    for position, root in enumerate(candidates, 1):
        routed = LAT.candidate_fan(head, root)
        sound, sound_rows, sound_misses = LC.sound_audit(
            routed["route_skeleton"], root, "اللاتينيّة", "Latin"
        )
        event = FE.resolve(root)
        orbit = manual.get(root)
        orbit_ready = bool(sense and orbit)
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
            "branch_meaning_ready": bool(sense),
            "manual_orbit_ready": orbit_ready,
            "manual_orbit": orbit,
            "manual_orbit_source": "مراجعة بشرية سابقة محفوظة" if orbit else None,
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
    winner = min(positives, key=lambda item: int(item["fan_position"])) \
        if positives else None
    reasons: list[str] = []
    if not candidate_rows:
        reasons.append("لم تولد أداة الصوت مرشحًا من الرأس المسترد")
    else:
        if not any(candidate["sound_ready"] for candidate in candidate_rows):
            reasons.append("لا مرشح أكمل مسار الصوت المسمى")
        if not any(candidate["frozen_event_ready"] for candidate in candidate_rows):
            reasons.append("لا مرشح نزل له حدث من frozen_event.resolve")
        if not any(candidate["manual_orbit_ready"] for candidate in candidate_rows):
            reasons.append("معنى الفرع حاضر، لكن لا مدار يدوي مسمى لأي مرشح")
        if not reasons and not winner:
            reasons.append("لم تجتمع الأرجل الثلاث في مرشح واحد")

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
    location = recovery["new_location"]
    return {
        "source_index": source_index,
        "language": "old-latin",
        "source": "khashim-latin",
        "foreign": foreign,
        "legacy": {"foreign": recovery["fields"]["foreign"]["legacy"]},
        "sense": sense,
        "arabic_root": row.get("arabic_root"),
        "analysis_head": head,
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
        "open_reasons": reasons,
        "ocr_recovery": {
            "page": int(location["page"]),
            "head_line": int(location["head_line"]),
            "answer_line": int(location["answer_line"]),
            "matched_new_row": int(recovery["matched_new_row"]),
            "alignment_evidence": recovery["alignment_evidence"],
        },
        "contract": (
            "ثلاث أرجل فقط: مسار الصوت المسمى؛ frozen_event.resolve؛ "
            "معنى الفرع مع مدار يدوي"
        ),
    }


def compact_scan(card: dict[str, Any]) -> str:
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
    winner = card["winner"]
    required = "؛ ".join(card["open_reasons"]) or "لا عائق معلق"
    verdict = (
        f"**{card['verdict']} (استكشاف)** بالمقابل `{winner['root']}`"
        if winner else "**غير صادر (استكشاف)**"
    )
    event_line = (
        FE.resolve(str(winner["root"])).line() if winner else
        "- الحدث المنتخب: لا مرشح محكوم؛ أحداث المرشحين منقولة في سجل الدفعة."
    )
    orbit = winner["manual_orbit"] if winner else (
        "لا مدار يدوي مسمى سابقًا، ولم يولد السكربت مدارًا."
    )
    return "\n".join([
        f"### بطاقة استرداد: `{card['foreign']}` «{LC.quote(card['sense'])}»؛ khashim-latin-official-ocr-recovery/{card['source_index']:03d}",
        f"<!-- khashim-latin-official-ocr-recovery:{card['source_index']} -->",
        "- إصدار البروتوكول: LATIN-OCR-RECOVERY-v1 (استكشاف).",
        f"- الاسترداد: الرأس القديم `{FALLEN}` محفوظ في `legacy.foreign`؛ الرأس الرسمي `{card['foreign']}` من صفحة PDF {recovery['page']}، سطر الرأس {recovery['head_line']}.",
        f"- نسبة المصدر: معنى الفرع واقتراح خشيم من {BOOK}؛ المسار والحدث والحكم أعمال المشروع.",
        f"- معنى الفرع كما في الصف القديم: «{LC.quote(card['sense'])}».",
        f"- الخطوة صفر: {card['stripping']}؛ الخام `{''.join(card['raw_skeleton']) or '∅'}`؛ البديل `{''.join(card['stem_skeleton']) or '∅'}`.",
        f"- اقتراحات خشيم: {proposal_text(card['khashim_proposals'])}.",
        f"- المروحة الصوتية: {', '.join(f'`{root}`' for root in card['fan']) if card['fan'] else '(فارغة)'}. هي أداة بحث داخل رجل الصوت وليست رجلًا رابعة.",
        f"- فحص المرشحين بثلاث أرجل: {compact_scan(card)}.",
        f"- الحصيلة: المرشحون={stats['fan_candidates']}؛ الصوت={stats['sound_ready']}؛ الحدث={stats['frozen_event_ready']}؛ المدار اليدوي={stats['manual_orbit_ready']}؛ مكتمل الأرجل={stats['three_legs_ready']}.",
        event_line,
        f"- المدار اليدوي: {orbit}",
        "- حراسة المدار: معنى الفرع من المصدر، وتأليف الحدث مع المعنى لا يكتبه إلا القارئ بيده.",
        f"- عائق: النوع={card['closure']}؛ يتطلب={required}",
        f"- حالة الإغلاق: {card['closure']}",
        f"- الحكم (استكشاف): {verdict}",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.batch != 1:
        raise SystemExit("هذه الدورة 150 صفًا في دفعة واحدة فقط")

    source_payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    source_rows = [row for row in source_payload["rows"] if row.get("source") == "khashim-latin"]
    recovery_payload = json.loads(RECOVERIES.read_text(encoding="utf-8"))
    recoveries = sorted(recovery_payload["recoveries"], key=lambda row: int(row["source_index"]))
    if len(source_rows) != 560 or len(recoveries) != BATCH_SIZE:
        raise SystemExit(f"تغير مقام اللاتينية/الدفعة: {len(source_rows)}/{len(recoveries)}")

    cards: list[dict[str, Any]] = []
    tiers: Counter[str] = Counter()
    for recovery in recoveries:
        source_index = int(recovery["source_index"])
        row = source_rows[source_index]
        change = recovery["fields"]["foreign"]
        if row.get("foreign") != change["recovered"]:
            raise SystemExit(f"اختلف الرأس المسترد عند صف {source_index}")
        if row.get("legacy", {}).get("foreign") != change["legacy"]:
            raise SystemExit(f"غاب legacy عند صف {source_index}")
        card = evaluate(source_index, row, recovery)
        cards.append(card)
        for candidate in card["candidate_evaluations"]:
            event = candidate["frozen_event"]
            tiers[str(event["tier"]) if event else "0"] += 1

    fan_total = sum(card["fan_stats"]["fan_candidates"] for card in cards)
    sound_ready = sum(card["fan_stats"]["sound_ready"] for card in cards)
    event_ready = sum(card["fan_stats"]["frozen_event_ready"] for card in cards)
    manual_ready = sum(card["fan_stats"]["manual_orbit_ready"] for card in cards)
    positives = sum(bool(card["verdict"]) for card in cards)
    counts = {
        "rows": len(cards),
        "restored_foreign_fields": len(cards),
        "fan_candidates": fan_total,
        "sound_leg_ready_candidates": sound_ready,
        "frozen_event_leg_ready_candidates": event_ready,
        "frozen_event_tiers": dict(sorted(tiers.items())),
        "manual_orbit_ready_candidates": manual_ready,
        "positive_verdicts": positives,
        "open_verdicts": len(cards) - positives,
    }
    payload = {
        "schema": "khashim-latin-official-ocr-recovery-harvest-batch-v1",
        "generated_by": "scripts/build_khashim_latin_official_ocr_recovery_batch.py",
        "batch": 1,
        "batch_size": BATCH_SIZE,
        "total_recovered_rows": len(cards),
        "counts": counts,
        "contract": (
            "ثلاث أرجل فقط: مسار الصوت المسمى؛ frozen_event.resolve؛ "
            "معنى الفرع مع مدار يدوي. لا يولد السكربت مدارًا"
        ),
        "rows": cards,
    }
    block = "\n".join([
        START,
        "## حصاد رؤوس «اللاتينية العربية» المستردة من الأصل الرسمي (2026-08-14)",
        "",
        f"**المقام.** هذه البطاقات هي الصفوف الـ{len(cards)} المستردة وحدها، في دفعة واحدة ثابتة الحجم 150.",
        "",
        "**العقد.** ثلاث أرجل فقط: مسار الصوت المسمى، وحدث من `frozen_event.resolve`، ومعنى الفرع مع مدار يدوي. المروحة أداة داخل الصوت، ولا يولد هذا المسار مدارًا.",
        "",
        f"**الحصيلة.** المرشحون {fan_total}؛ الصوت {sound_ready}؛ الحدث {event_ready}؛ المدار اليدوي {manual_ready}؛ موجب {positives}؛ مفتوح {len(cards) - positives}.",
        "",
        *[render_card(card) for card in cards],
        END,
    ])
    reading = replace_block(READING.read_text(encoding="utf-8"), block)

    audit_lines = [
        "# محضر إعادة حصاد «اللاتينية العربية»، دفعة الاسترداد 001",
        "",
        "**التاريخ:** 2026-08-14  ",
        f"**المقام:** {len(cards)} صفًا مستردًا وحده، في دفعة واحدة من الحجم الثابت 150.",
        "",
        "## العقد",
        "",
        "الأرجل ثلاث لا رابعة لها: مسار صوت مسمى، ثم حدث من `frozen_event.resolve`، ثم معنى الفرع مع مدار كتبه القارئ بيده. المروحة داخل الصوت. لم يولد السكربت مدارًا واحدًا.",
        "",
        "## الحصيلة",
        "",
        f"- الصفوف وحقول الرأس المستردة مع حفظ legacy: **{len(cards)}**.",
        f"- مرشحو المراوح: **{fan_total}**؛ اكتمل الصوت في **{sound_ready}**.",
        f"- حدث frozen_event موجود: **{event_ready}**؛ الدرجات: " + "، ".join(f"{key}={value}" for key, value in sorted(tiers.items())) + ".",
        f"- مدار يدوي موجود: **{manual_ready}**.",
        f"- الأحكام الموجبة: **{positives}**؛ المفتوحة: **{len(cards) - positives}**.",
        "",
        "## الصفوف",
        "",
        "| فهرس المصدر | الرأس المسترد | الجذر المنقول | صفحة المصدر | المرشحون | الصوت | الحدث | المدار | الحكم |",
        "|---:|---|---|---:|---:|---:|---:|---:|---|",
    ]
    for card in cards:
        stats = card["fan_stats"]
        audit_lines.append(
            f"| {card['source_index']} | `{card['foreign']}` | `{card['arabic_root']}` | {card['ocr_recovery']['page']} | {stats['fan_candidates']} | {stats['sound_ready']} | {stats['frozen_event_ready']} | {stats['manual_orbit_ready']} | {card['verdict'] or 'غير صادر'} |"
        )

    print(json.dumps(counts, ensure_ascii=False, indent=1))
    if args.dry_run:
        return 0
    READING.write_text(reading, encoding="utf-8", newline="\n")
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8", newline="\n")
    AUDIT.write_text("\n".join(audit_lines) + "\n", encoding="utf-8", newline="\n")
    print(f"كتب: {OUT}")
    print(f"كتب: {AUDIT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
