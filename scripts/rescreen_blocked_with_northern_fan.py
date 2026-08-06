# -*- coding: utf-8 -*-
"""إعادة مسح بطاقات العائق كلها بمروحة الشمال إلى العربية.

يقسم الجرد الثابت ذي 851 بطاقة إلى ثلاث دفعات متجاورة. لكل بطاقة يسجل كل
رسم شمالي في عقد المستخرج، وكل جذر عربي تولده المروحة ويثبت وجوده في ذخيرة
المعاجم، مع شاهد واحد كامل من كل معجم متاح. وجود المرشح لا يصدر حكم صلة،
وذكره السابق في البطاقة يفصل عن المرشح الذي لم يفحص بعد.

الاستعمال:
    python scripts/rescreen_blocked_with_northern_fan.py --batch 1
    python scripts/rescreen_blocked_with_northern_fan.py --batch 1 --check
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fan_northern_word as F  # noqa: E402


EXPLORATION = ROOT / "04-cross-linguistic" / "exploration"
QURANIC = ROOT / "data" / "quranic-roots.json"
DATE = "2026-08-06"
TOTAL = 851
BATCH_RANGES = {
    1: (1, 284),
    2: (285, 568),
    3: (569, 851),
}

NORTHERN = re.compile(r"[\u0590-\u05ff]{2,12}")
ARABIC = re.compile(r"[ء-ي][ء-ي\u064b-\u0652ـ]{1,12}")
BLOCKER = re.compile(r"عائق: النوع=([^؛\n]+)")
VERDICT = re.compile(r"الحكم \(استكشاف\):\s*([^\n]+)")

ARABIC_NORMALIZE = str.maketrans({
    "أ": "ء",
    "إ": "ء",
    "ؤ": "ء",
    "ئ": "ء",
    "ى": "ي",
})


def normalize_arabic(value: str) -> str:
    return F.bare_ar(value).translate(ARABIC_NORMALIZE)


def no_long_dashes(value: str) -> str:
    return value.replace("—", "-").replace("–", "-")


def blocked_cards() -> list[dict[str, object]]:
    cards: list[dict[str, object]] = []
    for path in sorted(EXPLORATION.glob("blocked-*.jsonl")):
        language = path.stem.removeprefix("blocked-")
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if not line.strip():
                continue
            row = json.loads(line)
            cards.append({
                "language": language,
                "source": path.name,
                "source_line": line_number,
                "head": no_long_dashes(str(row.get("head") or "")),
                "word": no_long_dashes(str(row.get("word") or "")),
                "excerpt": no_long_dashes(str(row.get("excerpt") or "")),
            })
    if len(cards) != TOTAL:
        raise RuntimeError(
            f"تغير سكان مستخرجات العائق: الحاضر {len(cards)} والمثبت {TOTAL}"
        )
    return cards


def northern_forms(card: dict[str, object]) -> tuple[list[dict], list[str]]:
    blob = " ".join(
        str(card[key]) for key in ("head", "word", "excerpt")
    )
    found: list[dict] = []
    ignored: list[str] = []
    seen: set[tuple[str, str]] = set()
    for raw in NORTHERN.findall(blob):
        skeleton = F.skeleton(raw)
        key = (raw, skeleton)
        if key in seen:
            continue
        seen.add(key)
        if not (2 <= len(skeleton) <= 4):
            if raw not in ignored:
                ignored.append(raw)
            continue
        found.append({"form": raw, "skeleton": skeleton})
    return found, ignored


def lexicon_witnesses(entries: list[tuple[str, str]]) -> list[dict[str, str]]:
    witnesses: list[dict[str, str]] = []
    seen: set[str] = set()
    for source, definition in entries:
        source = no_long_dashes(source.strip())
        if source in seen:
            continue
        seen.add(source)
        witnesses.append({
            "source": source or "ذخيرة جذر بلا اسم معجم",
            "definition": no_long_dashes(definition.strip()),
        })
    return witnesses


def scan_card(
    card: dict[str, object],
    global_index: int,
    roots: dict[str, list[tuple[str, str]]],
    quranic: dict[str, int],
) -> dict[str, object]:
    forms, ignored = northern_forms(card)
    excerpt = str(card["excerpt"])
    mentioned = {
        normalize_arabic(token) for token in ARABIC.findall(excerpt)
    }
    form_records: list[dict[str, object]] = []
    all_candidates: set[str] = set()
    for item in forms:
        candidates: list[dict[str, object]] = []
        for root in F.fan(str(item["form"])):
            if root not in roots:
                continue
            normalized = normalize_arabic(root)
            witnesses = lexicon_witnesses(roots[root])
            candidates.append({
                "root": root,
                "mentioned_in_card": normalized in mentioned,
                "quranic": normalized in quranic,
                "quranic_occurrences": quranic.get(normalized, 0),
                "evidence_kind": (
                    "named-lexicon-witnesses" if witnesses else "root-inventory-only"
                ),
                "witnesses": witnesses,
            })
            all_candidates.add(root)
        form_records.append({**item, "candidates": candidates})

    blocker = BLOCKER.search(excerpt)
    verdicts = VERDICT.findall(excerpt)
    return {
        "global_index": global_index,
        "language": card["language"],
        "source": card["source"],
        "source_line": card["source_line"],
        "head": card["head"],
        "word": card["word"],
        "snapshot_blocker": blocker.group(1).strip() if blocker else "غير مستخرج",
        "snapshot_last_verdict": verdicts[-1].strip() if verdicts else "غير مستخرج",
        "northern_forms": form_records,
        "ignored_northern_forms": ignored,
        "candidate_roots": sorted(all_candidates),
        "candidate_count": len(all_candidates),
        "decision": "LEXICON-SCREEN-ONLY",
    }


def output_paths(batch: int) -> tuple[Path, Path]:
    suffix = f"{batch:02d}"
    return (
        ROOT / "data" / f"blocked-northern-fan-rescreen-batch-{suffix}.json",
        ROOT / "05-audits" / f"2026-08-06-blocked-northern-fan-rescreen-batch-{suffix}.md",
    )


def render_audit(payload: dict[str, object]) -> str:
    summary = payload["summary"]
    lines = [
        f"# محضر مروحة بطاقات العائق، الدفعة {payload['batch']:02d}",
        "",
        "## القانون والنطاق",
        "",
        "هذه طبقة استكشاف معجمية. وجود الجذر في المروحة لا يثبت الصلة، "
        "وعدم ذكره في البطاقة السابقة لا يثبت بطلانها. حُفظت حالة المستخرج "
        "كما هي، وفُصل المرشح المذكور سابقًا عن المرشح الذي لم يفحص.",
        "",
        f"- مجال الجرد العام: {payload['range'][0]} إلى {payload['range'][1]} من {TOTAL} بطاقة.",
        f"- البطاقات في الدفعة: {summary['cards']}.",
        f"- البطاقات ذات رسم شمالي صالح للمروحة: {summary['cards_with_forms']}.",
        f"- البطاقات ذات مرشح معجمي واحد على الأقل: {summary['cards_with_candidates']}.",
        f"- الجذور المرشحة المميزة داخل بطاقاتها: {summary['card_candidate_roots']}.",
        "- الشواهد المعجمية الكاملة لكل مرشح محفوظة في ملف JSON المرافق.",
        "",
        "## السجل بطاقة بطاقة",
        "",
        "| الرقم العام | المصدر | البطاقة | الرسوم الشمالية | كل الجذور الموجودة في المعاجم | حالة المستخرج |",
        "|---:|---|---|---|---|---|",
    ]
    for card in payload["records"]:
        forms = " · ".join(
            f"`{item['form']}` ← `{item['skeleton']}`"
            for item in card["northern_forms"]
        ) or "لا رسم صالح"
        candidates = " · ".join(
            f"`{root}`" for root in card["candidate_roots"]
        ) or "لا مرشح معجمي"
        head = str(card["head"]).replace("|", "¦")
        state = str(card["snapshot_blocker"]).replace("|", "¦")
        lines.append(
            f"| {card['global_index']} | `{card['source']}:{card['source_line']}` | "
            f"{head} | {forms} | {candidates} | `{state}` |"
        )
    lines += [
        "",
        "## قيد الحكم",
        "",
        "الحكم في هذه الدفعة `LEXICON-SCREEN-ONLY`. لا يعاد فتح بطاقة ولا تستعاد "
        "درجة موجبة إلا بسطر نسخ مستقل يختبر المعنى والصوت والصرف والقرض.",
        "",
    ]
    text = "\n".join(lines)
    if "—" in text or "–" in text:
        raise RuntimeError("تسربت شرطة طويلة إلى المحضر")
    return unicodedata.normalize("NFC", text)


def build(batch: int) -> tuple[str, str, dict[str, object]]:
    start, end = BATCH_RANGES[batch]
    cards = blocked_cards()
    roots = F.load_arabic_roots()
    quranic_payload = json.loads(QURANIC.read_text(encoding="utf-8"))
    quranic = {
        normalize_arabic(root): int(count)
        for root, count in quranic_payload["by_root"].items()
    }
    records = [
        scan_card(cards[index - 1], index, roots, quranic)
        for index in range(start, end + 1)
    ]
    by_language = collections.Counter(
        str(record["language"]) for record in records
    )
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "date": DATE,
        "batch": batch,
        "range": [start, end],
        "population": TOTAL,
        "fan": {key: list(value) for key, value in F.FAN.items()},
        "summary": {
            "cards": len(records),
            "cards_with_forms": sum(bool(r["northern_forms"]) for r in records),
            "cards_with_candidates": sum(bool(r["candidate_roots"]) for r in records),
            "card_candidate_roots": sum(int(r["candidate_count"]) for r in records),
            "by_language": dict(sorted(by_language.items())),
        },
        "records": records,
    }
    data_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    audit_text = render_audit(payload) + "\n"
    if "—" in data_text or "–" in data_text:
        raise RuntimeError("تسربت شرطة طويلة إلى بيانات الدفعة")
    return data_text, audit_text, payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, choices=sorted(BATCH_RANGES), required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    data_text, audit_text, payload = build(args.batch)
    data_path, audit_path = output_paths(args.batch)
    if args.check:
        if not data_path.is_file() or data_path.read_text(encoding="utf-8") != data_text:
            raise RuntimeError(f"بيانات الدفعة {args.batch} بائتة أو مفقودة")
        if not audit_path.is_file() or audit_path.read_text(encoding="utf-8") != audit_text:
            raise RuntimeError(f"محضر الدفعة {args.batch} بائت أو مفقود")
    else:
        data_path.write_text(data_text, encoding="utf-8", newline="\n")
        audit_path.write_text(audit_text, encoding="utf-8", newline="\n")
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
