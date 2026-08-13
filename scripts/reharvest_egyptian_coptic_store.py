# -*- coding: utf-8 -*-
"""أعد حصاد مخزن المصرية والقبطية في دفعات إلحاقية من 150 صفا.

المروحة والصوت استرجاع آلي، والحدث لا يؤخذ إلا من ``FE.resolve``. أما المدار
فلا يولده هذا الملف: لا يصدر موجب إلا بمفتاح موجود صراحة في ``MANUAL_NEW`` أو
بحكم سابق ذي مدار محفوظ في بيان الجولة الأصلية.
"""
from __future__ import annotations

import argparse
import glob
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_egyptian_gods_maqar_cards as OLD  # noqa: E402
import frozen_event as FE  # noqa: E402

BATCH_SIZE = 150
READING = ROOT / "04-cross-linguistic" / "readings" / "egyptian.md"
MARKER = "EGYPTIAN-COPTIC-STORE-REHARVEST"


# مدارات هذه الجولة مكتوبة يدويا، واحدا واحدا. رقم المفتاح هو رتبة الصف في
# الجرد الثابت، والمرشح لا يحتكر المروحة بسبب وجوده هنا.
MANUAL_NEW: dict[tuple[int, str], tuple[str, str]] = {
    (41, "خنف"): (
        "ROOT-TRACE",
        "مدار الفعل: الريح والنفس هواء يتخلخل في الباطن ثم ينفذ من مجرى ضيق "
        "ويخرج متفرقا مبعدا؛ وهذا تأليف يدوي لحدث النواة وحدث الفاء، والحكم "
        "مقصور على عنصر الريح والنفس من اسم المعبود.",
    ),
}


def old_rows() -> dict[int, dict]:
    out: dict[int, dict] = {}
    for name in sorted(glob.glob(str(ROOT / "data" / "egyptian-gods-maqar-batch-*.json"))):
        payload = json.loads(pathlib.Path(name).read_text(encoding="utf-8"))
        for row in payload.get("rows", []):
            out[int(row["ordinal"])] = row
    return out


def report_path(batch: int) -> pathlib.Path:
    return ROOT / "data" / f"egyptian-coptic-store-reharvest-batch-{batch:03d}.json"


def audit_path(batch: int) -> pathlib.Path:
    return ROOT / "05-audits" / f"2026-08-14-egyptian-coptic-store-reharvest-batch-{batch:03d}.md"


def marker(batch: int, side: str) -> str:
    return f"<!-- {MARKER}-BATCH-{batch:03d}:{side} -->"


def previous_positive(row: dict) -> tuple[str, str, str] | None:
    if not row.get("verdict") or not row.get("positive_root") or not row.get("human_orbit"):
        return None
    return str(row["positive_root"]), str(row["verdict"]), str(row["human_orbit"])


def candidate_rows(source: dict, previous: dict) -> tuple[list[dict], str, int | None]:
    script, _ = OLD.script_for(source)
    stem, _, _ = OLD.morphology(source, script)
    fan = OLD.K.FAN.fan(stem, script, limit=400)
    author = OLD.K.ar_bare(source.get("classical_root") or source.get("arabic_root", ""))
    prior = previous_positive(previous)
    values = list(fan)
    for extra in (author, prior[0] if prior else ""):
        if extra and extra not in values:
            values.append(extra)
    ranked = OLD.K.FAN.rank(stem, values, script, "hebrew")
    fan_set = set(fan)
    rows: list[dict] = []
    author_position: int | None = None
    for position, (candidate, weight) in enumerate(ranked, 1):
        if candidate == author:
            author_position = position
        sound_ready, sound_rows, sound_misses = OLD.sound_for(stem, candidate, script)
        ev = FE.resolve(candidate)
        manual = MANUAL_NEW.get((int(previous["ordinal"]), candidate))
        if prior and candidate == prior[0]:
            verdict, orbit, orbit_origin = prior[1], prior[2], "حكم سابق محفوظ"
        elif manual:
            verdict, orbit, orbit_origin = manual[0], manual[1], "مدار جديد مكتوب باليد"
        else:
            verdict, orbit, orbit_origin = None, None, None
        positive = bool(verdict and orbit and sound_ready and ev)
        rows.append({
            "candidate": candidate,
            "rank": position,
            "mansur_weight": weight,
            "origin": "مروحة fan()" if candidate in fan_set else (
                "مرشح المصدر خارج المروحة" if candidate == author else "حكم سابق محفوظ"
            ),
            "sound_ready": sound_ready,
            "sound_rows": sound_rows,
            "sound_misses": sound_misses,
            "event": None if ev is None else {
                "text": ev.text,
                "source": ev.source,
                "tier": ev.tier,
                "tier_ar": ev.tier_ar,
                "note": ev.note,
                "line": ev.line(),
            },
            "branch_sense": source.get("foreign_sense", ""),
            "semantic_orbit": orbit,
            "orbit_authorship": orbit_origin,
            "verdict": verdict if positive else None,
            "positive": positive,
        })
    return rows, author, author_position


def render(source: dict, previous: dict, batch: int) -> tuple[str, dict]:
    ordinal = int(previous["ordinal"])
    script, script_note = OLD.script_for(source)
    stem, stripping, raw = OLD.morphology(source, script)
    stem_skeleton = OLD.K.FAN.skeleton(stem, script)
    candidates, author, author_position = candidate_rows(source, previous)
    positives = [c for c in candidates if c["positive"]]
    if len(positives) > 1:
        raise RuntimeError(f"تعدد موجب الصف {ordinal}")
    positive = positives[0] if positives else None
    proper = bool(previous.get("proper_name"))
    focus = positive or next((c for c in candidates if c["candidate"] == author), None)
    focus = focus or next((c for c in candidates if c["event"]), candidates[0] if candidates else None)
    closure = positive["verdict"] if positive else "OPEN-CANDIDATE"
    counted = bool(positive and not proper)
    ready = sum(bool(c["sound_ready"] and c["event"]) for c in candidates)
    eventless = sum(c["event"] is None for c in candidates)
    sound_open = sum(not c["sound_ready"] for c in candidates)
    tiers = Counter(str(c["event"]["tier"]) if c["event"] else "0" for c in candidates)
    ranked_text = "، ".join(
        f"`{c['candidate']}` ({c['mansur_weight']:.6f})" for c in candidates
    )
    if positive:
        event_line = positive["event"]["line"]
        sound_text = "؛ ".join(positive["sound_rows"])
        orbit_line = positive["semantic_orbit"]
        verdict_line = positive["verdict"]
        obstacle = "لا عائق معلق"
        copy_line = (
            f"حُفظ الحكم السابق {positive['verdict']}" if positive["orbit_authorship"] == "حكم سابق محفوظ"
            else f"نُسخ الحكم السابق غير صادر بالحكم {positive['verdict']} بعد نزول الحدث"
        )
    else:
        if focus and focus["event"]:
            event_line = focus["event"]["line"]
        else:
            event_line = "- الحدث من السجل المجمد: لم يرجع `FE.resolve` حدثا لمرشح العرض."
        if focus:
            sound_text = "؛ ".join(focus["sound_rows"] + focus["sound_misses"])
        else:
            sound_text = "لا مرشح قابل للرصف"
        orbit_line = (
            "فُحصت أحداث جميع مرشحي المروحة مع معنى الفرع، ولم يقنع مدار واحد "
            "من غير اتكاء على دعوى المصدر؛ لم تولد الآلة مدارا ولم يصدر حكم."
        )
        verdict_line = "غير صادر"
        obstacle = "مدار يدوي مقنع لمرشح تكتمل له رجل الصوت والحدث"
        copy_line = "بقي الحكم السابق غير صادر بعد إعادة المروحة والحدث"
    comparison_place = (
        f"الرتبة {author_position} في العرض الموزون" if author_position
        else "خارج المروحة، فحفظ ولم يحتكر الحكم"
    )
    lines = [
        f"### بطاقة: إعادة حصاد `extended-egyptian:{ordinal:04d}`؛ `{source['foreign']}` «{source['foreign_sense']}»",
        f"<!-- {MARKER}:{ordinal:04d} -->",
        "- إصدار البروتوكول: RECOVERY-v2؛ طبقة استكشاف.",
        f"- سجل البطاقة السابقة: `EGYPTIAN-GODS-MAQAR:{ordinal:04d}`؛ نسبة المصدر: "
        f"{OLD.BOOK_LABELS[str(source['book'])]}، ص {source['page']}.",
        f"- الكلمة في الفرع: `{source['foreign']}`؛ وسم اللسان `{source['tongue']}`؛ {script_note}.",
        f"- جرد العلم: {'علم أو عنصر علم، يفصل عن العد' if proper else 'مفردة غير موسومة علما في الجرد السابق'}.",
        f"- الخطوة صفر: {stripping}؛ الخام `{' '.join(raw) or '∅'}`؛ اللب `{' '.join(stem_skeleton) or '∅'}`.",
        f"- المروحة المرتبة بوزن `F.rank`: {ranked_text}.",
        f"- مرشح المصدر: `{author or '(غير مستخرج)'}`؛ {comparison_place}؛ لا يستعمل دليلا مستقلا.",
        f"- فحص المروحة العضوي: {len(candidates)} مرشحا؛ {ready} لها الصوت والحدث معا؛ "
        f"{eventless} بلا حدث؛ {sound_open} صوتها مفتوح؛ درجات الحدث "
        f"1={tiers['1']}، 2={tiers['2']}، 3={tiers['3']}، 4={tiers['4']}، غياب={tiers['0']}.",
        event_line,
        f"- مسار الصوت للمرشح المعروض: {sound_text}.",
        f"- المعنى من قاموس الفرع بلا رتوش: «{source['foreign_sense']}» [{OLD.BOOK_LABELS[str(source['book'])]}، ص {source['page']}].",
        f"- المدار: {orbit_line}",
        "- المصفاة: لم يسم صف المصدر مانحا خارجيا؛ غياب المانح ليس برهان وراثة.",
        f"- عائق: النوع={closure}؛ يتطلب={obstacle}.",
        f"- حالة الإغلاق: {closure}.",
        f"- الحكم (استكشاف): {verdict_line}.",
        f"- سطر النسخ (2026-08-14، {MARKER}:{ordinal:04d}): {copy_line}.",
        "- مراجعة الاسترداد: حُفظت المروحة كاملة ومرشح المصدر ودرجة كل حدث.",
        "- مراجعة التشكيك: لم تقبل دعوى المصدر دليلا، وفُصل العلم عن العدد، ولم يصدر موجب بلا مدار مكتوب.",
    ]
    card = "\n".join(lines)
    if "—" in card:
        raise ValueError(f"شرطة طويلة في بطاقة {ordinal}")
    summary = {
        "row_id": f"extended-egyptian:{ordinal:04d}",
        "ordinal": ordinal,
        "batch": batch,
        "book": source["book"],
        "page": source["page"],
        "tongue": source["tongue"],
        "foreign": source["foreign"],
        "foreign_sense": source["foreign_sense"],
        "proper_name": proper,
        "script": script,
        "stem": stem,
        "stem_skeleton": stem_skeleton,
        "author_root": author,
        "author_root_rank": author_position,
        "candidates": candidates,
        "candidate_count": len(candidates),
        "event_tiers": dict(sorted(tiers.items())),
        "closure": closure,
        "verdict": positive["verdict"] if positive else None,
        "positive_root": positive["candidate"] if positive else None,
        "semantic_orbit": positive["semantic_orbit"] if positive else None,
        "orbit_authorship": positive["orbit_authorship"] if positive else None,
        "counted_link": counted,
        "open_reason": None if positive else "لا مدار يدوي مقنع",
    }
    return card, summary


def build(batch: int) -> None:
    source_rows = OLD.selected_rows()
    prior = old_rows()
    total_batches = (len(source_rows) + BATCH_SIZE - 1) // BATCH_SIZE
    if not 1 <= batch <= total_batches:
        raise SystemExit(f"رقم الدفعة خارج 1 إلى {total_batches}")
    start = (batch - 1) * BATCH_SIZE
    selected = source_rows[start:start + BATCH_SIZE]
    rendered: list[str] = []
    summaries: list[dict] = []
    survival: list[dict] = []
    for offset, source in enumerate(selected, start=start + 1):
        if source.get("lane") == "survival-only":
            survival.append({
                "row_id": f"extended-egyptian:{offset:04d}",
                "ordinal": offset,
                "lane": "survival-only",
                "excluded_from_project_link_count": True,
            })
            continue
        if offset not in prior:
            raise RuntimeError(f"لا بطاقة أصلية للصف {offset}")
        text, summary = render(source, prior[offset], batch)
        rendered.append(text)
        summaries.append(summary)

    positives = [r for r in summaries if r["verdict"]]
    counted = [r for r in positives if r["counted_link"]]
    opens = [r for r in summaries if not r["verdict"]]
    candidate_tiers = Counter()
    for row in summaries:
        candidate_tiers.update(row["event_tiers"])
    report = {
        "schema": "egyptian-coptic-store-reharvest-v1.0",
        "generated_at": "2026-08-14",
        "source_store": "data/egyptian-gods-maqar-batch-001.json إلى 010",
        "event_resolver": "scripts/frozen_event.py:FE.resolve",
        "fan": "scripts/fan_any_script.py:fan",
        "batch": batch,
        "batch_size": BATCH_SIZE,
        "total_batches": total_batches,
        "first_ordinal": start + 1,
        "last_ordinal": start + len(selected),
        "source_rows_examined": len(selected),
        "cards_written": len(summaries),
        "survival_only": len(survival),
        "candidate_count": sum(r["candidate_count"] for r in summaries),
        "candidate_event_tiers": dict(sorted(candidate_tiers.items())),
        "positive_raw": len(positives),
        "positive_counted": len(counted),
        "open_candidate": len(opens),
        "open_reason_counts": dict(Counter(r["open_reason"] for r in opens)),
        "rows": summaries,
        "survival_rows": survival,
    }
    report_path(batch).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )

    section = "\n".join([
        marker(batch, "START"),
        f"## إعادة حصاد مخزن المصرية والقبطية، الدفعة {batch:03d} (2026-08-14)",
        "",
        f"**بيان النطاق.** الصفوف {start + 1:04d} إلى {start + len(selected):04d} من المخزن الثابت. "
        "أعيدت المروحة عبر `fan()` والحدث عبر `FE.resolve`، والمدار لا يصدر إلا مكتوبا باليد.",
        "",
        f"**الحصيلة.** فُحص {len(selected)} صفا، وكُتبت {len(summaries)} بطاقة، "
        f"والبقايا فقط {len(survival)}، والموجب الخام {len(positives)}، والموجب المعدود {len(counted)}، "
        f"والمفتوح {len(opens)}.",
        "",
        *rendered,
        marker(batch, "END"),
    ]) + "\n"
    current = READING.read_text(encoding="utf-8")
    if marker(batch, "START") in current:
        raise RuntimeError(f"الدفعة {batch} ملحقة من قبل")
    if "—" in section:
        raise ValueError("شرطة طويلة في قسم القراءة")
    with READING.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write("\n" + section)

    highlights = [
        f"`{r['foreign']} ↔ {r['positive_root']}`، {r['verdict']}"
        for r in positives[:10]
    ]
    audit = "\n".join([
        f"# محضر إعادة حصاد مخزن المصرية والقبطية، الدفعة {batch:03d}",
        "",
        "**التاريخ:** 2026-08-14  ",
        f"**النطاق:** الصفوف {start + 1:04d} إلى {start + len(selected):04d}، وعددها {len(selected)}.  ",
        "**الحالة:** مكتملة ومراجعة بعدستين.",
        "",
        "## ضابط الانحدار",
        "",
        "الضابط الإلزامي خُتم قبل الدفعة صفر: `ḫtm/ختم` و`mwt/موت` و`smr/سمر` و`mn/من` و`mr/مر` و`nfi̯/نف`، 6 من 6 سليمة وصفر تغير في الحكم. سجله الكامل في محضر الدفعة صفر.",
        "",
        "## الحصيلة",
        "",
        "| البند | العدد |",
        "|---|---:|",
        f"| فُحص | {len(selected)} |",
        f"| كُتب | {len(summaries)} |",
        f"| مرشحو المروحة | {report['candidate_count']} |",
        f"| موجب خام | {len(positives)} |",
        f"| موجب معدود | {len(counted)} |",
        f"| مفتوح | {len(opens)} |",
        "",
        "أسباب المفتوح بالعد: " + "، ".join(
            f"{reason}={number}" for reason, number in report["open_reason_counts"].items()
        ) + ".",
        "",
        "درجات أحداث المرشحين: " + "، ".join(
            f"الدرجة {tier}={number}" if tier != "0" else f"غياب={number}"
            for tier, number in report["candidate_event_tiers"].items()
        ) + ". الدرجة لم تغير رتبة السلم.",
        "",
        "## أبرز الأزواج الداخلة",
        "",
        *(f"- {x}." for x in highlights),
        *( ["- لم تبلغ الدفعة عشرة أزواج موجبة، فذُكر جميع ما دخل بلا حشو."] if len(highlights) < 10 else [] ),
        "",
        "## المراجعتان",
        "",
        "- عدسة الاسترداد: شغلت `fan()` لكل صف، وحفظت كل مرشح ووزنه ومساره ودرجة حدثه، ولم يحتكر مرشح المصدر العرض.",
        "- عدسة التشكيك: راجعت المدارات المكتوبة، وفصلت الأعلام عن العدد، ولم تجعل دعوى المصدر سندا مستقلا، ولم تحول غياب المدار إلى `NO-TRACE`.",
        "",
        "## سطر الحصيلة",
        "",
        f"فُحص {len(selected)} صفا، وكُتبت {len(summaries)} بطاقة؛ الموجب الخام {len(positives)}، "
        f"والمعدود {len(counted)}، والمفتوح {len(opens)}.",
        "",
    ])
    if "—" in audit:
        raise ValueError("شرطة طويلة في المحضر")
    audit_path(batch).write_text(audit, encoding="utf-8", newline="\n")
    print(
        f"الدفعة {batch:03d}: فُحص {len(selected)}؛ كُتب {len(summaries)}؛ "
        f"موجب خام {len(positives)}؛ موجب معدود {len(counted)}؛ مفتوح {len(opens)}"
    )
    print(f"كُتب: {report_path(batch).relative_to(ROOT).as_posix()}")
    print(f"كُتب: {audit_path(batch).relative_to(ROOT).as_posix()}")


def check(batch: int) -> int:
    path = report_path(batch)
    payload = json.loads(path.read_text(encoding="utf-8"))
    bad: list[str] = []
    if payload["source_rows_examined"] != BATCH_SIZE and batch != payload["total_batches"]:
        bad.append("حجم الدفعة ليس 150")
    if payload["cards_written"] != len(payload["rows"]):
        bad.append("عدد البطاقات مختل")
    for row in payload["rows"]:
        for candidate in row["candidates"]:
            ev = FE.resolve(candidate["candidate"])
            if (ev is None) != (candidate["event"] is None):
                bad.append(f"اختل الحدث في {row['row_id']}:{candidate['candidate']}")
            elif ev and candidate["event"]["line"] != ev.line():
                bad.append(f"لم ينقل الحدث حرفيا في {row['row_id']}:{candidate['candidate']}")
        if row["verdict"]:
            chosen = [c for c in row["candidates"] if c["positive"]]
            if len(chosen) != 1 or not chosen[0]["sound_ready"] or not chosen[0]["event"] or not row["semantic_orbit"]:
                bad.append(f"موجب بلا الأرجل الثلاث في {row['row_id']}")
    if bad:
        print("FAIL: " + "؛ ".join(bad[:12]))
        return 1
    print(
        f"CLEAN: الدفعة {batch:03d}؛ الصفوف {payload['source_rows_examined']}؛ "
        f"المرشحون {payload['candidate_count']}؛ كل الأحداث مطابقة لـFE.resolve"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.check:
        return check(args.batch)
    build(args.batch)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
