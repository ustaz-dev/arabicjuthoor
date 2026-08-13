#!/usr/bin/env python3
"""Build the internal loan-route registry from committed-style reading cards.

This is a retrieval-only exporter.  It copies named routes and citations from
cards whose explicit exploration verdict is LOANWORD; it never infers a route,
direction, or verdict.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import unicodedata
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
READINGS = ROOT / "04-cross-linguistic" / "readings"
OUTPUT_JSON = ROOT / "data" / "recovery-loan-registry.json"
OUTPUT_MD = ROOT / "04-cross-linguistic" / "recovery-loan-registry.md"
PROJECT_TIMEZONE = ZoneInfo("Africa/Cairo")

LANGUAGE_BY_FILE = {
    "ancient-greek.md": "اليونانية القديمة",
    "aramaic.md": "الآرامية",
    "coptic.md": "القبطية",
    "egyptian.md": "المصرية",
    "hebrew.md": "العبرية",
    "old-latin.md": "اللاتينية القديمة",
}

FIELD_RE = re.compile(r"^- ([^:\n]+):\s*(.*)$", re.MULTILINE)
VERDICT_RE = re.compile(r"^- الحكم \(استكشاف\): LOANWORD(?:\s|$)", re.MULTILINE)
HEADING_RE = re.compile(r"^### (?:بطاقة(?: RECOVERY-v2)?:\s*)?(.+)$", re.MULTILINE)


def clean(value: str) -> str:
    return unicodedata.normalize("NFC", re.sub(r"\s+", " ", value).strip())


def committed_text(path: Path) -> str:
    """Read the source at HEAD so local verdicts cannot leak into the registry."""
    relative = path.relative_to(ROOT).as_posix()
    completed = subprocess.run(
        ["git", "show", f"HEAD:{relative}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return completed.stdout.decode("utf-8")


def extract_cards(text: str) -> list[str]:
    starts = [match.start() for match in re.finditer(r"^### ", text, re.MULTILINE)]
    cards: list[str] = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else len(text)
        block = text[start:end]
        if VERDICT_RE.search(block):
            cards.append(block)
    return cards


def field_map(block: str) -> dict[str, str]:
    return {clean(key): clean(value) for key, value in FIELD_RE.findall(block)}


def citations(*values: str) -> list[str]:
    found: list[str] = []
    for value in values:
        for item in re.findall(r"\[([^\]]+)\]", value):
            item = clean(item)
            if item and item not in found:
                found.append(item)
    return found


def build() -> dict[str, object]:
    entries: list[dict[str, object]] = []
    sources: list[dict[str, str]] = []
    for filename, language in LANGUAGE_BY_FILE.items():
        path = READINGS / filename
        if not path.exists():
            continue
        text = committed_text(path)
        cards = extract_cards(text)
        card_bytes = unicodedata.normalize("NFC", "\n\n".join(cards)).encode("utf-8")
        sources.append(
            {
                "path": path.relative_to(ROOT).as_posix(),
                "loan_card_blocks_sha256": hashlib.sha256(card_bytes).hexdigest(),
            }
        )
        for ordinal, block in enumerate(cards, start=1):
            fields = field_map(block)
            heading_match = HEADING_RE.search(block)
            heading = clean(heading_match.group(1)) if heading_match else f"بطاقة {ordinal}"
            route = fields.get("المصفاة", "")
            oldest = fields.get("أقدمُ صورةٍ مستعادة", fields.get("أقدم صورة مستعادة", ""))
            notes = fields.get("ملاحظات", "")
            source_list = citations(route, oldest, fields.get("المعنى من قاموس الفرع", ""))
            entries.append(
                {
                    "registry_id": f"loan-{filename.removesuffix('.md')}-{ordinal:03d}",
                    "language": language,
                    "card": heading,
                    "lexeme": fields.get("الكلمةُ في الفرع", fields.get("الكلمة في الفرع", "")),
                    "route_as_recorded": route,
                    "oldest_form_as_recorded": oldest,
                    "named_sources_as_recorded": source_list,
                    "scope_note": notes,
                    "verdict": "LOANWORD",
                    "source_path": path.relative_to(ROOT).as_posix(),
                    "source_line": text[: text.find(block)].count("\n") + 1,
                }
            )
    entries.sort(key=lambda row: (str(row["language"]), str(row["source_path"]), int(row["source_line"])))
    return {
        "schema_version": 1,
        # GitHub Actions runs in UTC while the project day is Cairo time. A
        # bare date.today() made --check disagree for the first hours after
        # Cairo midnight even when the committed cards were identical.
        "generated_on": datetime.now(PROJECT_TIMEZONE).date().isoformat(),
        "status": "internal-retrieval-only",
        "scope": "explicit LOANWORD verdict cards committed at HEAD in the named reading files",
        "non_inference_rule": "routes, directions, sources, and verdicts are copied only from the cards; missing fields remain empty",
        "source_files": sources,
        "entries_total": len(entries),
        "entries": entries,
    }


def render_markdown(payload: dict[str, object]) -> str:
    entries = payload["entries"]
    assert isinstance(entries, list)
    lines = [
        "# سجل القروض المعزولة في قراءات الاسترداد",
        "",
        f"التاريخ: {payload['generated_on']}",
        "",
        "الحالة: سجل داخلي استرجاعي. لا يستنبط قرضًا ولا اتجاهًا ولا مصدرًا، بل ينقل بطاقات `LOANWORD` الصريحة المودعة في `HEAD` كما هي. الأحكام المحلية غير المراجعة لا تدخل السجل، والحقل الفارغ يبقى فارغًا ولا يستكمل بالتخمين.",
        "",
        "| اللغة | البطاقة | اللفظ | المسار المسمى في البطاقة | المصدر المسمى | الموضع |",
        "|---|---|---|---|---|---|",
    ]
    for row in entries:
        assert isinstance(row, dict)
        source_text = "؛ ".join(row["named_sources_as_recorded"]) or "غير مفصول في حقل مستقل"
        values = [
            row["language"],
            row["card"],
            row["lexeme"],
            row["route_as_recorded"],
            source_text,
            f"`{row['source_path']}:{row['source_line']}`",
        ]
        escaped = [str(value).replace("|", "\\|") for value in values]
        lines.append("| " + " | ".join(escaped) + " |")
    lines += [
        "",
        "## حدود السجل",
        "",
        "- لا يدخل وسم القرض الآلي أو مجرد ذكر أصل أجنبي ما لم تحمل البطاقة حكم `LOANWORD` صريحًا.",
        "- يقرأ المولد نسخة `HEAD` لا شجرة العمل، حتى لا يتسرب حكم محلي ينتظر المراجعة إلى السجل البنيوي المودع.",
        "- الحكم للعضو أو سلسلة المعنى المسماة، ولا ينتقل إلى بقية الأسرة أو المركبات أو المتجانسات.",
        "- هذا سجل عزل ومحاسبة، وليس بسطًا لخط البرهان ولا رقمًا للنشر.",
        "- يعاد بناؤه بالأمر `python scripts/build_recovery_loan_registry.py --check` للتحقق، أو بلا `--check` للتحديث.",
        "",
        "## عائق فحص كفر القرية",
        "",
        "- عائق: النوع=SOURCE-GAP؛ يتطلب=نسخة محلية مشروعة من Fraenkel, *Die aramäischen Fremdwörter im Arabischen* لفحص عضو كفر بمعنى القرية.",
        "- استنفاد البحث المحلي: لم توجد نسخة من الكتاب في `Resources/` أو في ملفات المشروع. الموجود إحالة ببليوغرافية إليه فقط، فلا تعامل الإحالة نسخة مفحوصة.",
        "- النتيجة: يبقى عضو القرية الآرامي معاد الفتح، ولا يمس ذلك عضو الإنكار أو التكفير.",
        "",
    ]
    return unicodedata.normalize("NFC", "\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build()
    json_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    md_text = render_markdown(payload)
    if args.check:
        stale = []
        if not OUTPUT_JSON.exists() or OUTPUT_JSON.read_text(encoding="utf-8") != json_text:
            stale.append(str(OUTPUT_JSON.relative_to(ROOT)))
        if not OUTPUT_MD.exists() or OUTPUT_MD.read_text(encoding="utf-8") != md_text:
            stale.append(str(OUTPUT_MD.relative_to(ROOT)))
        if stale:
            print("STALE: " + ", ".join(stale))
            return 1
        print(f"CLEAN: {payload['entries_total']} explicit LOANWORD cards")
        return 0
    OUTPUT_JSON.write_text(json_text, encoding="utf-8", newline="\n")
    OUTPUT_MD.write_text(md_text, encoding="utf-8", newline="\n")
    print(f"WROTE: {payload['entries_total']} explicit LOANWORD cards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
