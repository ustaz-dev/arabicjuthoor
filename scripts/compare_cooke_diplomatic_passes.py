#!/usr/bin/env python3
"""Compare two independent diplomatic transcriptions of Cooke records.

The active transcription lines use one shared notation. The script reports
reading disagreement separately from the original notation observations. It
never selects a reading or opens the citation gate.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import tempfile
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "04-cross-linguistic" / "data"
PASS_A = DATA / "cooke-1903-diplomatic-pass-a.json"
PASS_B = DATA / "cooke-1903-diplomatic-pass-b.json"
OUTPUT = DATA / "cooke-1903-double-transcription-comparison.json"
AUDIT = ROOT / "05-audits" / "2026-07-25-cooke-double-transcription-comparison.md"
EXPECTED_IDS = list(range(3, 13))
FRAGMENT_PREFIX = re.compile(r"^(?:a′?|b|c)\.\s*")
ALLOWED_PUNCTUATION = frozenset(" []0123456789:/.")


def fail(message: str) -> None:
    raise ValueError(message)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate_diplomatic_line(
    line: str, pass_id: str, record_id: int, line_number: int
) -> None:
    body = FRAGMENT_PREFIX.sub("", line, count=1)
    for index, char in enumerate(body):
        codepoint = ord(char)
        allowed = (
            0x05D0 <= codepoint <= 0x05EA
            or char == "\u0307"
            or char in ALLOWED_PUNCTUATION
        )
        if not allowed:
            fail(
                f"foreign or undeclared character in pass {pass_id}, "
                f"record {record_id}, line {line_number}, offset {index}: "
                f"U+{codepoint:04X} {unicodedata.name(char, 'UNKNOWN')}"
            )
        if char.isdigit() or char in ":/":
            opened = body.rfind("[", 0, index + 1)
            closed_before = body.rfind("]", 0, index + 1)
            closed_after = body.find("]", index)
            if opened <= closed_before or closed_after < 0:
                fail(
                    f"number notation outside a complete bracketed token in "
                    f"pass {pass_id}, record {record_id}, line {line_number}, "
                    f"offset {index}"
                )
        if char == "\u0307":
            if index == 0 or not (0x05D0 <= ord(body[index - 1]) <= 0x05EA):
                fail(
                    f"detached damage dot in pass {pass_id}, record "
                    f"{record_id}, line {line_number}, offset {index}"
                )


def load_pass(path: Path, expected_pass_id: str) -> dict[str, Any]:
    if not path.exists():
        fail(f"missing independent pass: {path.relative_to(ROOT)}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != "1.0":
        fail(f"unsupported pass schema: {path.relative_to(ROOT)}")
    if payload.get("pass_id") != expected_pass_id:
        fail(f"wrong pass identity: {path.relative_to(ROOT)}")
    records = payload.get("records")
    if not isinstance(records, list):
        fail(f"pass records are not a list: {path.relative_to(ROOT)}")
    ids = [record.get("record_id") for record in records]
    if ids != EXPECTED_IDS:
        fail(
            f"pass must contain records 3 through 12 in order: "
            f"{path.relative_to(ROOT)}"
        )
    for record in records:
        lines = record.get("lines")
        if (
            not isinstance(lines, list)
            or not lines
            or not all(isinstance(line, str) for line in lines)
        ):
            fail(f"invalid lines in {record.get('record_id')}")
        for line_number, line in enumerate(lines, start=1):
            if unicodedata.normalize("NFC", line) != line:
                fail(
                    f"non-NFC line in pass {expected_pass_id}, "
                    f"record {record.get('record_id')}, line {line_number}"
                )
            validate_diplomatic_line(
                line, expected_pass_id, record["record_id"], line_number
            )
    observations = payload.get("notation_observations")
    if not isinstance(observations, list) or not observations:
        fail(f"missing notation observations: {path.relative_to(ROOT)}")
    required = {"locus", "record_id", "line", "value", "observed_rendering"}
    for observation in observations:
        if not required.issubset(observation):
            fail(f"incomplete notation observation in pass {expected_pass_id}")
    return payload


def pair_notation_observations(
    pass_a: dict[str, Any], pass_b: dict[str, Any]
) -> list[dict[str, Any]]:
    observations_a = pass_a["notation_observations"]
    observations_b = pass_b["notation_observations"]
    loci_a = [row["locus"] for row in observations_a]
    loci_b = [row["locus"] for row in observations_b]
    if loci_a != loci_b or len(loci_a) != len(set(loci_a)):
        fail("notation observations must have the same unique ordered loci")
    pairs: list[dict[str, Any]] = []
    for row_a, row_b in zip(observations_a, observations_b, strict=True):
        identity_a = (
            row_a["record_id"],
            row_a["line"],
            row_a["value"],
        )
        identity_b = (
            row_b["record_id"],
            row_b["line"],
            row_b["value"],
        )
        if identity_a != identity_b:
            fail(f"notation observation identity differs at {row_a['locus']}")
        differs = row_a["observed_rendering"] != row_b["observed_rendering"]
        pairs.append(
            {
                "locus": row_a["locus"],
                "record_id": row_a["record_id"],
                "line": row_a["line"],
                "value": row_a["value"],
                "observed_rendering_a": row_a["observed_rendering"],
                "observed_rendering_b": row_b["observed_rendering"],
                "notation_differs": differs,
            }
        )
    return pairs


def levenshtein(left: str, right: str) -> int:
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def differences(left: str, right: str) -> list[dict[str, Any]]:
    matcher = difflib.SequenceMatcher(a=left, b=right, autojunk=False)
    rows: list[dict[str, Any]] = []
    for tag, a_start, a_end, b_start, b_end in matcher.get_opcodes():
        if tag == "equal":
            continue
        rows.append(
            {
                "operation": tag,
                "a_start": a_start,
                "a_end": a_end,
                "a_text": left[a_start:a_end],
                "b_start": b_start,
                "b_end": b_end,
                "b_text": right[b_start:b_end],
            }
        )
    return rows


def build() -> dict[str, Any]:
    pass_a = load_pass(PASS_A, "A")
    pass_b = load_pass(PASS_B, "B")
    notation_pairs = pair_notation_observations(pass_a, pass_b)
    by_a = {record["record_id"]: record for record in pass_a["records"]}
    by_b = {record["record_id"]: record for record in pass_b["records"]}

    results: list[dict[str, Any]] = []
    total_reading_distance = 0
    total_reading_characters = 0
    for record_id in EXPECTED_IDS:
        record_a = by_a[record_id]
        record_b = by_b[record_id]
        text_a = "\n".join(record_a["lines"])
        text_b = "\n".join(record_b["lines"])
        distance = levenshtein(text_a, text_b)
        denominator = max(len(text_a), len(text_b))
        total_reading_distance += distance
        total_reading_characters += denominator
        notation = [
            row for row in notation_pairs if row["record_id"] == record_id
        ]
        results.append(
            {
                "record_id": record_id,
                "source_pages_a": record_a.get("source_pages", []),
                "source_pages_b": record_b.get("source_pages", []),
                "line_count_a": len(record_a["lines"]),
                "line_count_b": len(record_b["lines"]),
                "reading_character_count_a": len(text_a),
                "reading_character_count_b": len(text_b),
                "reading_exact_match": text_a == text_b,
                "reading_levenshtein_distance": distance,
                "reading_disagreement_rate": (
                    distance / denominator if denominator else 0.0
                ),
                "reading_differences": differences(text_a, text_b),
                "notation_observations": notation,
                "notation_loci_total": len(notation),
                "notation_loci_differing": sum(
                    row["notation_differs"] for row in notation
                ),
                "uncertain_a": record_a.get("uncertain", []),
                "uncertain_b": record_b.get("uncertain", []),
            }
        )

    notation_total = len(notation_pairs)
    notation_differing = sum(
        row["notation_differs"] for row in notation_pairs
    )
    return {
        "schema_version": "2.0",
        "generated_by": "scripts/compare_cooke_diplomatic_passes.py",
        "scope": (
            "independent diplomatic transcriptions of Cooke records "
            "3 through 12"
        ),
        "non_judgment_rule": (
            "The comparison reports reading and notation differences only "
            "and never selects a reading or opens the citation gate."
        ),
        "shared_notation_rule": (
            "Active reading lines use one canonical bracketed Western-number "
            "notation. Original numeral renderings remain separate "
            "observations and do not inflate reading disagreement."
        ),
        "strict_character_gate": {
            "status": "enforced",
            "scope": "both independent-pass reading lines before comparison",
            "allowed": (
                "Hebrew block letters, combining dot above after a Hebrew "
                "letter, spaces, square brackets, Western digits, colon, "
                "slash, full stop, and declared initial fragment labels"
            ),
        },
        "known_common_mode_failure": {
            "record_id": 3,
            "feature": "printed damage dots above consonants",
            "finding": (
                "Both independent passes omitted at least some of the same "
                "printed damage dots, so exact agreement is not evidence of "
                "complete diplomatic fidelity."
            ),
            "gate_effect": "all first-batch records remain partial",
        },
        "retired_legacy_mixed_metric": {
            "status": "retired-mixed-reading-and-notation",
            "characters_compared": 3534,
            "levenshtein_distance_total": 234,
            "disagreement_rate": 0.066214,
            "reason": (
                "The historical number mixed reading differences with "
                "different numeral conventions. It remains an audit fact "
                "but is not a current batch metric."
            ),
        },
        "sources": {
            "pass_a": {
                "path": str(PASS_A.relative_to(ROOT)).replace("\\", "/"),
                "sha256": digest(PASS_A),
            },
            "pass_b": {
                "path": str(PASS_B.relative_to(ROOT)).replace("\\", "/"),
                "sha256": digest(PASS_B),
            },
        },
        "inventory": {
            "records_total": len(results),
            "records_exactly_agreeing_after_shared_notation": sum(
                result["reading_exact_match"] for result in results
            ),
            "records_requiring_visual_arbitration": sum(
                not result["reading_exact_match"] for result in results
            ),
            "reading_characters_compared": total_reading_characters,
            "reading_levenshtein_distance_total": total_reading_distance,
            "reading_disagreement_rate": (
                total_reading_distance / total_reading_characters
                if total_reading_characters
                else 0.0
            ),
            "notation_loci_total": notation_total,
            "notation_loci_differing": notation_differing,
            "notation_disagreement_rate": (
                notation_differing / notation_total
                if notation_total
                else 0.0
            ),
        },
        "notation_observations": notation_pairs,
        "records": results,
    }


def render_audit(payload: dict[str, Any]) -> str:
    inventory = payload["inventory"]
    lines = [
        "# محضر الكتابة المزدوجة لدفعة Cooke الأولى",
        "",
        "التاريخ: 2026-07-25",
        "",
        "الحالة: مقارنة بنيوية بلا اختيار قراءة وبلا حكم لغوي.",
        "",
        "## النطاق",
        "",
        "نسخ ناسخان مستقلان السجلات 3 إلى 12 من صور الصفحات وحدها. لم "
        "يقرأ أي منهما ملف الدفعة أو نسخة الآخر. بعد توحيد اصطلاح العدد "
        "تقارن الأداة القراءة وحدها، وتحفظ خلاف الاصطلاح في مقياس مستقل.",
        "",
        "## النتيجة المفصولة",
        "",
        "| المقياس | القيمة |",
        "|---|---:|",
        f"| السجلات | {inventory['records_total']} |",
        (
            "| المتفقة في القراءة بعد توحيد الاصطلاح | "
            f"{inventory['records_exactly_agreeing_after_shared_notation']} |"
        ),
        (
            "| المحتاجة تحكيما بصريا | "
            f"{inventory['records_requiring_visual_arbitration']} |"
        ),
        (
            "| حروف القراءة المقابلة | "
            f"{inventory['reading_characters_compared']} |"
        ),
        (
            "| مسافة تحرير القراءة | "
            f"{inventory['reading_levenshtein_distance_total']} |"
        ),
        (
            "| معدل خلاف القراءة | "
            f"{inventory['reading_disagreement_rate']:.4%} |"
        ),
        f"| مواضع الاصطلاح المرصودة | {inventory['notation_loci_total']} |",
        (
            "| مواضع الاصطلاح المختلفة | "
            f"{inventory['notation_loci_differing']} |"
        ),
        (
            "| معدل خلاف الاصطلاح | "
            f"{inventory['notation_disagreement_rate']:.4%} |"
        ),
        "",
        "## السجلات",
        "",
        "| السجل | أسطر A | أسطر B | مسافة القراءة | معدلها | خلاف الاصطلاح | الحالة |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    for record in payload["records"]:
        status = (
            "متفق"
            if record["reading_exact_match"]
            else "تحكيم بصري"
        )
        lines.append(
            f"| {record['record_id']} | {record['line_count_a']} | "
            f"{record['line_count_b']} | "
            f"{record['reading_levenshtein_distance']} | "
            f"{record['reading_disagreement_rate']:.4%} | "
            f"{record['notation_loci_differing']}/"
            f"{record['notation_loci_total']} | {status} |"
        )
    lines += [
        "",
        "## المقياس القديم",
        "",
        "الرقم 6.6214% صحيح حسابيا لمسافة التحرير القديمة، لكنه خلط خلاف "
        "القراءة بخلاف اصطلاح تمثيل العدد. حفظ هنا واقعة تدقيق متقاعدة، "
        "ولا يستعمل مقياسا حاليا.",
        "",
        "## قاعدة الاستعمال",
        "",
        "- يرفض المقارن أي محرف دخيل في سطري النسختين قبل إجراء المقارنة.",
        "- لا يرقى سجل بسبب اتفاق النسختين وحده؛ الاتفاق يضيق موضع المراجعة ولا يلغي الصورة.",
        "- كل اختلاف يراجع على الصفحة، ويسجل الحسم وسببه في حقل تغييرات الدفعة.",
        "- مقياسا القراءة والاصطلاح للضبط الداخلي، وليسا رقمين للنشر ولا جزءا من خط البرهان.",
        "",
        "## فشل مشترك لا تلتقطه المقارنة",
        "",
        "أسقط الناسخان معا بعض نقط التلف المطبوعة فوق حروف السجل 3، "
        "وأخطآ معا في هاء اسم علم. لذلك لا يعد الاتفاق الحرفي برهان "
        "اكتمال، وتبقى الدفعة كلها جزئية إلى جرد العلامات المصدرية، "
        "ومقابلة الأعلام والكلمات المفتاحية على نقحرة Cooke، ثم "
        "المراجعة الثالثة.",
        "",
    ]
    return unicodedata.normalize("NFC", "\n".join(lines))


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        delete=False,
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build()
    json_text = (
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        + "\n"
    )
    audit_text = render_audit(payload)
    if args.check:
        stale = []
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != json_text:
            stale.append(str(OUTPUT.relative_to(ROOT)))
        if not AUDIT.exists() or AUDIT.read_text(encoding="utf-8") != audit_text:
            stale.append(str(AUDIT.relative_to(ROOT)))
        if stale:
            print("STALE: " + ", ".join(stale))
            return 1
        print(
            "CLEAN: Cooke double transcription "
            f"{payload['inventory']['records_total']} records, "
            f"{payload['inventory']['records_exactly_agreeing_after_shared_notation']} "
            "reading-exact after shared notation, "
            f"{payload['inventory']['records_requiring_visual_arbitration']} "
            "requiring visual arbitration"
        )
        return 0
    atomic_write(OUTPUT, json_text)
    atomic_write(AUDIT, audit_text)
    print(json.dumps(payload["inventory"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
