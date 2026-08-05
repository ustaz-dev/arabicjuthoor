# -*- coding: utf-8 -*-
"""إعادة فرز إغلاقات القرض بعد تصحيح جهة المانح في 2026-08-05.

لا تحذف هذه الهجرة بطاقة. وهي تسجل الحكم القديم داخل البطاقة، وتعيد البطاقة
التي لا يسمي مسارها مانحا ساميا إلى OPEN-CANDIDATE.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
READINGS = ROOT / "04-cross-linguistic" / "readings"
AUDIT = ROOT / "05-audits" / "2026-08-05-loanword-rescreen.md"
DATA = ROOT / "data" / "loanword-rescreen.json"

sys.path.insert(0, str(ROOT / "scripts"))
from count_links import bare  # noqa: E402
from recovery_pipeline.sources import _kaikki_loan_hint  # noqa: E402


CARD_HEAD = re.compile(r"(?m)^#{3,4}\s+[^\n]+$")
SCOPED = re.compile(r"(?<![A-Z-])LOANWORD(?![A-Z-])|LOANWORD-THIRD-PARTY-TO-BRANCH")
CANCELLED = ("غير صادر", "ناسخ", "منسوخ", "غير صادرة")
VERDICT_LABEL = re.compile(
    r"(?:الحكم(?:\s*\([^)]*\))?|الحسم|حكم طبقة (?:النواة|الجذر)|"
    r"نتيجة طبقة النواة|النتيجة)"
)
EVIDENCE_LABELS = (
    "مسار النقل المنشور",
    "أقدم صورة مستعادة",
    "المانح المسمى",
    "المصدر المثبت",
    "المصفاة",
    "فصل المتجانسات والاقتراض",
)
ARABIC_SEMITIC_DONOR = re.compile(
    r"(?:المانح[^:\n]{0,20}:\s*|(?:من|عن|اصلها|مصدرها)\s+)"
    r"(?:اللغة\s+)?(?:ال)?(?:اكادية|آكادية|عربية|آرامية|ارامية|عبرية|"
    r"سريانية|فينيقية|بونية|سبئية|اوغاريتية|أوغاريتية)"
    r"|(?:ال)?(?:اكادية|آكادية|عربية|آرامية|ارامية|عبرية|سريانية|"
    r"فينيقية|بونية|سبئية|اوغاريتية|أوغاريتية)\s+(?:إلى|الى|نحو)\s+"
    r"(?:القبطية|اليونانية|اللاتينية|الفارسية|العبرية|الآرامية|الارامية)"
)
OUTBOUND_TO_ARABIC = re.compile(
    r"(?:من\s+)?(?:القبطية|الآرامية|الارامية|العبرية|الفينيقية|البونية)"
    r"\s+(?:إلى|الى|نحو)\s+العربية"
)
FROM_DONOR = re.compile(
    r"(?i)\b(?:borrowed\s+)?from\s+([^,.;()\[\]\n]{1,80})"
)
ARABIC_NONSEMITIC_DONOR = re.compile(
    r"(?:من|←|اصلها|مصدرها|مانحها)\s+(?:ال)?"
    r"(يونانية|لاتينية|فارسية|ليبية|مصرية|قبطية|جرمانية|قوطية|كلتية|"
    r"انجليزية|إنجليزية|فرنسية|تركية|هندية|ايرانية|إيرانية)"
)


def cards(text: str) -> list[tuple[int, int, str]]:
    heads = list(CARD_HEAD.finditer(text))
    return [
        (match.start(), heads[index + 1].start() if index + 1 < len(heads) else len(text),
         text[match.start():heads[index + 1].start() if index + 1 < len(heads) else len(text)])
        for index, match in enumerate(heads)
    ]


def is_verdict_line(line: str) -> bool:
    normalized = bare(line).strip()
    if not normalized.startswith("-") or ":" not in normalized:
        return False
    label = normalized.split(":", 1)[0].lstrip("- ").strip()
    return bool(VERDICT_LABEL.fullmatch(label))


def active_token(card: str) -> str:
    found: list[str] = []
    for line in card.splitlines():
        normalized = bare(line)
        if not is_verdict_line(line) or any(word in normalized for word in CANCELLED):
            continue
        if "LOANWORD-THIRD-PARTY-TO-BRANCH" in line:
            found.append("LOANWORD-THIRD-PARTY-TO-BRANCH")
        elif re.search(r"(?<![A-Z-])LOANWORD(?![A-Z-])", line):
            found.append("LOANWORD")
    if not found:
        return ""
    if len(set(found)) != 1:
        raise ValueError(f"بطاقة تحمل إغلاقين مختلفين: {card.splitlines()[0]}")
    return found[0]


def recorded_reopen(card: str) -> tuple[str, str]:
    match = re.search(
        r"سطر النسخ \(2026-08-05، (LOAN-REOPEN-[A-Z-]+-\d{5})\)", card
    )
    if not match:
        return "", ""
    old = re.search(r"\[كان (LOANWORD(?:-THIRD-PARTY-TO-BRANCH)?)\]", card)
    if not old:
        raise ValueError(f"سطر نسخ بلا حكم سابق: {card.splitlines()[0]}")
    return match.group(1), old.group(1)


def evidence_lines(card: str) -> list[str]:
    out: list[str] = []
    for line in card.splitlines():
        normalized = bare(line).strip()
        if not normalized.startswith("-") or ":" not in normalized:
            continue
        label = normalized.split(":", 1)[0]
        if any(item in label for item in EVIDENCE_LABELS):
            out.append(line.split(":", 1)[1].strip())
    return out


def compact(text: str, limit: int = 220) -> str:
    value = re.sub(r"\s+", " ", text).strip().replace("—", "،")
    return value if len(value) <= limit else value[:limit - 1].rstrip() + "…"


def classify(card: str) -> tuple[str, str, str]:
    evidence = evidence_lines(card)
    joined = " | ".join(evidence)
    normalized = bare(joined)
    if OUTBOUND_TO_ARABIC.search(normalized):
        return "keep", "انتقال من الفرع إلى العربية، لا اقتراض من مانح غير سامي إلى الفرع", compact(joined)
    if _kaikki_loan_hint(joined):
        donor = next((compact(match.group(1), 90) for match in FROM_DONOR.finditer(joined)
                      if _kaikki_loan_hint("from " + match.group(1))), "مانح سامي مسمى")
        return "keep", f"المسار يسمّي مانحا ساميا: {donor}", compact(joined)
    if ARABIC_SEMITIC_DONOR.search(normalized):
        match = ARABIC_SEMITIC_DONOR.search(normalized)
        return "keep", f"المسار العربي يسمّي مانحا ساميا: {compact(match.group(0), 90)}", compact(joined)
    if not joined:
        return "reopen", "لا يحمل الإغلاق مسارا يسمّي مانحا ساميا", "لا مسار فردي مسمى"
    donor_match = FROM_DONOR.search(joined)
    arabic_donor = ARABIC_NONSEMITIC_DONOR.search(normalized)
    donor = (
        compact(donor_match.group(1), 90) if donor_match
        else arabic_donor.group(1) if arabic_donor
        else "غير سامي أو غير مسمى"
    )
    return "reopen", f"المانح المذكور غير سامي: {donor}", compact(joined)


def card_key(language: str, card: str, ordinal: int) -> str:
    for pattern in (
        r"([a-z-]+:family:[0-9a-f]{8,})",
        r"((?:kaikki|kellia)_[a-z_]+:\d+:[^\s`،؛,]+)",
        r"(kellia_coptic_lexicon:C\d+)",
    ):
        if match := re.search(pattern, card):
            return match.group(1).rstrip("].؛،")
    title = card.splitlines()[0].lstrip("# ").strip()
    return f"{language}:card:{ordinal}:{compact(title, 100)}"


def reopen_card(card: str, migration_id: str, old_token: str, reason: str) -> str:
    lines = card.splitlines(keepends=True)
    last_verdict = -1
    changed = 0
    for index, line in enumerate(lines):
        normalized = bare(line)
        if is_verdict_line(line) and not any(word in normalized for word in CANCELLED):
            if old_token in line:
                lines[index] = line.replace(old_token, f"غير صادر [كان {old_token}]", 1)
                last_verdict = index
                changed += 1
                continue
        if normalized.strip().startswith("- عائق:") and "النوع=" in line:
            lines[index] = re.sub(
                r"النوع=([A-Z][A-Z-]*)",
                lambda match: f"النوع=OPEN-CANDIDATE [كان {match.group(1)}]",
                line,
                count=1,
            )
        elif normalized.strip().startswith(("- حالة الإغلاق:", "- حالة الاغلاق:")):
            newline = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
            lines[index] = (
                f"- حالةُ الإغلاق: OPEN-CANDIDATE [كانت قبل إعادة فرز القرض]؛ "
                f"أعيدت إلى الطابور في {migration_id}.{newline}"
            )
    if changed < 1:
        raise ValueError(f"لم يجد سطر الحكم الحي: {card.splitlines()[0]}")
    note = (
        f"- سطر النسخ (2026-08-05، {migration_id}): الحكم السابق {old_token} منسوخ؛ "
        f"سبب إعادة الفتح: {reason}، وذكر اقتراض الفرع منه لا يغلق المقارنة في الطبقة الأعمق.\n"
    )
    lines.insert(last_verdict + 1, note)
    return "".join(lines)


def audit_text(records: list[dict], before: collections.Counter) -> str:
    by_language: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for row in records:
        by_language[row["language"]]["screened"] += 1
        by_language[row["language"]][row["decision"]] += 1
        by_language[row["language"]][row["old_verdict"]] += 1
    reopened = sum(row["decision"] == "reopen" for row in records)
    kept = len(records) - reopened
    lines = [
        "# محضر إعادة فرز إغلاقات القرض، 2026-08-05",
        "",
        "## النطاق والقانون",
        "",
        f"أعيد فحص {len(records):,} بطاقة ذات حكم حي `LOANWORD` أو "
        "`LOANWORD-THIRD-PARTY-TO-BRANCH`. لا يعد ذكر الاقتراض وحده إغلاقا. "
        "لا يبقى الإغلاق إلا إذا سمى المسار مانحا ساميا بعد `from`، أو أثبت "
        "المسار المنظم مانحا ساميا، أو كان انتقالا من الفرع إلى العربية.",
        "",
        f"النتيجة: أعيد فتح {reopened:,} بطاقة، وأبقي إغلاق {kept:,} بطاقة. "
        "لم تحذف بطاقة واحدة. تحفظ كل بطاقة معادة سطر نسخ يحمل معرّفا مستقرا، "
        "والقائمة الآلية الكاملة في `data/loanword-rescreen.json`.",
        "",
        "## الحصيلة بحسب اللسان",
        "",
        "| اللسان | المفحوص | أعيد فتحه | بقي مغلقا | LOANWORD | THIRD-PARTY |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for language in sorted(by_language):
        row = by_language[language]
        lines.append(
            f"| `{language}` | {row['screened']:,} | {row['reopen']:,} | {row['keep']:,} | "
            f"{row['LOANWORD']:,} | {row['LOANWORD-THIRD-PARTY-TO-BRANCH']:,} |"
        )
    lines.extend([
        "",
        "## المصالحة",
        "",
        f"كان مجموع الإغلاقات الداخلة في هذا الفرز {sum(before.values()):,}. "
        f"بعد النسخ يبقى منها {kept:,} ويعود {reopened:,} إلى `OPEN-CANDIDATE`. "
        "الأرقام تخص الحالة الحية عند تنفيذ الهجرة، ولذلك قد تزيد على رقم الفحص السابق "
        "إذا أضيفت بطاقات بين الفحصين.",
        "",
        "## عينات تحقق",
        "",
    ])
    for language in sorted(by_language):
        sample = next(row for row in records if row["language"] == language and row["decision"] == "reopen")
        lines.append(
            f"- `{language}`، `{sample['migration_id']}`، `{sample['card_id']}`: "
            f"{sample['reason']}."
        )
    lines.extend([
        "",
        "## أثر التنفيذ",
        "",
        "صححت الدالة `_kaikki_loan_hint` واختباراتها، ونسخت الأحكام داخل ملفات القراءة "
        "من غير محو النص التاريخي. يبنى العد واللقطة من الحقول الحية بعد هذا المحضر.",
        "",
    ])
    return "\n".join(lines)


def validate_existing() -> int:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    source = "\n".join(path.read_text(encoding="utf-8") for path in sorted(READINGS.glob("*.md")))
    present = set(re.findall(r"LOAN-REOPEN-[A-Z-]+-\d{5}", source))
    expected = {
        row["migration_id"] for row in payload["records"] if row["decision"] == "reopen"
    }
    missing = sorted(expected - present)
    if missing:
        raise ValueError(f"معرفات نسخ مفقودة: {missing[:10]}")
    print(f"الهجرة مسجلة من قبل: {payload['summary']}")
    return 0


def reset_own_migration() -> None:
    """أعد أسطر هذه الهجرة وحدها، تمهيدا لإعادة تشغيل مصححة."""
    for path in sorted(READINGS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if "LOAN-REOPEN-" not in text:
            continue
        out: list[str] = []
        for line in text.splitlines(keepends=True):
            if "سطر النسخ (2026-08-05، LOAN-REOPEN-" in line:
                continue
            line = re.sub(
                r"غير صادر \[كان (LOANWORD(?:-THIRD-PARTY-TO-BRANCH)?)\]",
                lambda match: match.group(1),
                line,
            )
            line = re.sub(
                r"النوع=OPEN-CANDIDATE \[كان ([A-Z][A-Z-]*)\]",
                lambda match: f"النوع={match.group(1)}",
                line,
            )
            out.append(line)
        path.write_text("".join(out), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--repair-and-rerun", action="store_true")
    parser.add_argument("--reset-only", action="store_true")
    args = parser.parse_args()
    if args.repair_and_rerun or args.reset_only:
        reset_own_migration()
        if args.reset_only:
            print("رُدّت آثار الهجرة وحدها ولم تعد تطبق.")
            return 0
    elif DATA.exists() and not args.dry_run:
        return validate_existing()

    records: list[dict] = []
    replacements: dict[Path, list[tuple[int, int, str]]] = collections.defaultdict(list)
    before: collections.Counter = collections.Counter()
    seq_by_language: collections.Counter = collections.Counter()
    for path in sorted(READINGS.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for ordinal, (start, end, card) in enumerate(cards(text), start=1):
            if "<" in card.splitlines()[0]:
                continue
            recorded_id, recorded_token = recorded_reopen(card)
            token = active_token(card)
            if not token and not recorded_id:
                continue
            decision, reason, evidence = classify(card)
            language = path.stem
            seq_by_language[language] += 1
            migration_id = f"LOAN-REOPEN-{language.upper()}-{seq_by_language[language]:05d}"
            if recorded_id:
                if recorded_id != migration_id:
                    raise ValueError(f"اختلال تسلسل النسخ: {recorded_id} != {migration_id}")
                token = recorded_token
                decision = "reopen"
            row = {
                "migration_id": migration_id,
                "language": language,
                "file": path.relative_to(ROOT).as_posix(),
                "card_id": card_key(language, card, ordinal),
                "heading": compact(card.splitlines()[0].lstrip("# "), 160),
                "old_verdict": token,
                "decision": decision,
                "reason": reason,
                "evidence": evidence,
            }
            records.append(row)
            before[(language, token)] += 1
            if decision == "reopen" and not recorded_id:
                replacements[path].append((start, end, reopen_card(card, migration_id, token, reason)))

    if not records:
        raise ValueError("لم توجد إغلاقات حية في النطاق")
    summary = {
        "screened": len(records),
        "reopened": sum(row["decision"] == "reopen" for row in records),
        "kept": sum(row["decision"] == "keep" for row in records),
    }
    print(json.dumps(summary, ensure_ascii=False))
    for language in sorted(seq_by_language):
        selected = [row for row in records if row["language"] == language]
        print(
            f"{language}: screened={len(selected)}, "
            f"reopened={sum(row['decision'] == 'reopen' for row in selected)}, "
            f"kept={sum(row['decision'] == 'keep' for row in selected)}"
        )
    if args.dry_run:
        for decision in ("keep", "reopen"):
            print(f"\n{decision} samples:")
            for row in [item for item in records if item["decision"] == decision][:12]:
                print(f"  {row['language']} | {row['heading']} | {row['reason']}")
        return 0

    for path, edits in replacements.items():
        text = path.read_text(encoding="utf-8")
        parts: list[str] = []
        cursor = 0
        for start, end, replacement in sorted(edits):
            parts.extend((text[cursor:start], replacement))
            cursor = end
        parts.append(text[cursor:])
        path.write_text("".join(parts), encoding="utf-8", newline="\n")
    payload = {
        "schema_version": "1.0",
        "date": "2026-08-05",
        "rule": "A borrowing hint closes only when from names a Semitic donor; structured Semitic and outbound-to-Arabic routes remain closed.",
        "summary": summary,
        "records": records,
    }
    DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    AUDIT.write_text(audit_text(records, before), encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
