# -*- coding: utf-8 -*-
"""أعد فتح نقوض زال عائقها الصوتي بدخول صفوف SEM-01 إلى SEM-05.

لا تستعيد هذه الهجرة حكم نسب موجبًا. وهي تحفظ النقض القديم في موضعه،
وتضيف سطر نسخ يعيد البطاقة إلى OPEN-CANDIDATE للقراءة العضوية.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "data" / "recorded-retractions.json"
DATA = ROOT / "data" / "semitic-row-retraction-rescreen.json"
AUDIT = ROOT / "05-audits" / "2026-08-06-semitic-row-retraction-rescreen.md"
NETWORK = ROOT / "04-cross-linguistic" / "shift-network-draft.md"

TARGETS = (
    {
        "audit_id": "RET-N-008",
        "copy_id": "RET-REOPEN-SEM-001",
        "rows": ("SEM-03", "SEM-02"),
        "correspondence": "ع ↔ ע، مع ذكر الوجه البديل غ ↔ ע",
        "basis": "صار لعين الفرع صفان صريحان يفرقان وجهي *ʕ و*ġ بدل دعوى الهوية بلا صف",
    },
    {
        "audit_id": "RET-R-056",
        "copy_id": "RET-REOPEN-SEM-002",
        "rows": ("SEM-02",),
        "correspondence": "غ ↔ ע",
        "basis": "دخلت مقابلة الغين العربية بالعين العبرية في SEM-02",
    },
    {
        "audit_id": "RET-R-057",
        "copy_id": "RET-REOPEN-SEM-003",
        "rows": ("SEM-02",),
        "correspondence": "غ ↔ ע",
        "basis": "دخلت مقابلة الغين العربية بالعين العبرية في SEM-02",
    },
    {
        "audit_id": "RET-R-059",
        "copy_id": "RET-REOPEN-SEM-004",
        "rows": ("SEM-01",),
        "correspondence": "ض ↔ ץ",
        "basis": "دخلت مقابلة الضاد العربية بالصاد العبرية النهائية في SEM-01",
    },
    {
        "audit_id": "RET-R-061",
        "copy_id": "RET-REOPEN-SEM-005",
        "rows": ("SEM-02",),
        "correspondence": "غ ↔ ע",
        "basis": "دخلت مقابلة الغين العربية بالعين العبرية في SEM-02",
    },
)


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def plain(value: str) -> str:
    return "".join(
        char
        for char in unicodedata.normalize("NFD", value)
        if unicodedata.category(char) != "Mn"
    )


def card_blocks(text: str) -> list[str]:
    return re.split(r"(?m)(?=^### )", text)


def network_counts() -> tuple[int, int, int]:
    text = NETWORK.read_text(encoding="utf-8")
    rows = set(re.findall(r"(?m)^\| ((?:IDN|[A-Z]+(?:-[A-Z]+)*)-\d{2}) \|", text))
    core = {row for row in rows if not row.startswith("BR-")}
    branch = rows - core
    if len(core) != 62 or len(branch) != 14:
        raise RuntimeError(
            f"اختل عد الشبكة: أساسية={len(core)}، فرعية={len(branch)}"
        )
    required = {f"SEM-{number:02d}" for number in range(1, 6)} | {"SIB-07"}
    missing = sorted(required - core)
    if missing:
        raise RuntimeError(f"صفوف نافذة مفقودة: {missing}")
    return len(core), len(branch), len(rows)


def load_records() -> tuple[list[dict], dict[str, dict]]:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    records = payload["records"]
    if len(records) != 146:
        raise RuntimeError(f"سجل النقوض يحمل {len(records)} بطاقة، والمطلوب 146")
    by_id = {record["audit_id"]: record for record in records}
    if len(by_id) != len(records):
        raise RuntimeError("تكرر معرف في سجل النقوض")
    return records, by_id


def verify_target(record: dict, target: dict) -> None:
    reasons = plain(" | ".join(record["reasons"]))
    checks = {
        "RET-N-008": ("هويةٌ بلا صف", "عينِ الفرع"),
        "RET-R-056": ("ع مقابل غ بلا صف",),
        "RET-R-057": ("العينِ العبريّةِ بالغينِ العربيّةِ", "غيرُ مدرجة"),
        "RET-R-059": ("ץ مع ض بلا صف",),
        "RET-R-061": ("ع مقابل غ بلا صف",),
    }
    missing = [needle for needle in checks[target["audit_id"]] if plain(needle) not in reasons]
    if missing:
        raise RuntimeError(f"تغير سبب {target['audit_id']}: {missing}")


def copy_line(target: dict) -> str:
    rows = " و".join(target["rows"])
    return nfc(
        f"- سطر النسخ (2026-08-06، {target['copy_id']}): سبب النقض بغياب الصف "
        f"الصوتي في {target['audit_id']} زال بدخول {rows}؛ {target['basis']}؛ "
        "عادت البطاقة إلى OPEN-CANDIDATE للقراءة العضوية، ولا تستعيد الدرجة السابقة آليًا."
    )


def verdict_line(target: dict) -> str:
    return nfc(
        f"- الحكم (إعادة فرز الصفوف السامية، 2026-08-06): OPEN-CANDIDATE؛ "
        f"المسار الصوتي المرخص الآن {target['correspondence']}، والحكم الدلالي يحتاج إعادة قراءة عضوية."
    )


def apply_target(record: dict, target: dict, apply: bool) -> dict:
    path = ROOT / record["source_file"]
    text = path.read_text(encoding="utf-8")
    marker = nfc(f"سطر النسخ (2026-08-05، {target['audit_id']})")
    copy_marker = nfc(f"سطر النسخ (2026-08-06، {target['copy_id']})")
    blocks = card_blocks(text)
    matches = [index for index, block in enumerate(blocks) if marker in nfc(block)]
    if len(matches) != 1:
        raise RuntimeError(f"حضور بطاقة {target['audit_id']} في الأجساد: {len(matches)}")
    index = matches[0]
    block = blocks[index]
    existing = copy_marker in nfc(block)
    if not existing and apply:
        lines = block.splitlines()
        marker_indexes = [line_no for line_no, line in enumerate(lines) if marker in nfc(line)]
        if len(marker_indexes) != 1:
            raise RuntimeError(f"اختل سطر النقض في {target['audit_id']}")
        insert_at = marker_indexes[0] + 1
        lines[insert_at:insert_at] = [copy_line(target), verdict_line(target)]
        blocks[index] = "\n".join(lines) + ("\n" if block.endswith("\n") else "")
        path.write_text("".join(blocks), encoding="utf-8", newline="\n")
        existing = True
    return {
        "audit_id": target["audit_id"],
        "copy_id": target["copy_id"],
        "layer": record["layer"],
        "language": record["language"],
        "source_file": record["source_file"],
        "heading": record["heading"],
        "prior_degrees": record["prior_degrees"],
        "rows": list(target["rows"]),
        "correspondence": target["correspondence"],
        "basis": target["basis"],
        "decision": "OPEN-CANDIDATE",
        "copy_line_present": existing,
    }


def write_outputs(records: list[dict], results: list[dict], counts: tuple[int, int, int]) -> None:
    row_counts = collections.Counter(row for result in results for row in result["rows"])
    aramaic_dad = [
        record["audit_id"]
        for record in records
        if record["language"] == "aramaic"
        and re.search(r"(?:ע\s*↔\s*ض|ض\s*↔\s*ע|عين[^.؛]{0,40}ضاد)", " | ".join(record["reasons"]))
    ]
    if aramaic_dad:
        raise RuntimeError(f"فاتت نقوض الضاد الآرامية: {aramaic_dad}")
    payload = {
        "schema_version": "1.0",
        "date": "2026-08-06",
        "scope": "SEM-01..SEM-05 and SIB-07 against recorded retractions",
        "network": {"core_rows": counts[0], "branch_rows": counts[1], "parsed_rows": counts[2]},
        "summary": {
            "screened": len(records),
            "reopened": len(results),
            "positive_verdicts_restored": 0,
            "aramaic_ayin_to_arabic_dad_retractions": 0,
        },
        "row_references": dict(sorted(row_counts.items())),
        "records": results,
    }
    DATA.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# محضر إعادة فرز النقوض بصفوف الساميّات الجديدة، 2026-08-06",
        "",
        "## النطاق والقانون",
        "",
        f"فُحصت النقوض المسجلة كلها، وعددها {len(records)}. الشبكة النافذة تحمل "
        f"{counts[0]} صفًا أساسيًا و{counts[1]} صفًا فرعيًا، أي {counts[2]} صفًا يقرأها الجامع.",
        "",
        "القاعدة المنفذة: إذا كان غياب الصف الصوتي جزءًا مسجلًا من سبب النقض، "
        "ثم دخل الصف الذي يرخص التقابل نفسه، تنسخ علة الغياب وتعود البطاقة إلى "
        "`OPEN-CANDIDATE`. لا تستعاد الدرجة الموجبة آليًا، لأن الصف يرخص الصوت ولا يرخص الصلة.",
        "",
        "## النتيجة",
        "",
        f"أعيد فتح {len(results)} بطاقات، ولم يستعد أي حكم نسب موجب آليًا. "
        "لم يوجد في سجل النقوض سبب يسمّي انعكاس الضاد العربية عينًا آرامية، "
        "ولذلك كان عدد بطاقات `ע ↔ ض` الآرامية المعادة في هذه الدفعة 0.",
        "",
        "| رقم النسخ | النقض السابق | الطبقة | اللسان | الصف الجديد | التقابل | الحكم بعد النسخ |",
        "|---|---|---|---|---|---|---|",
    ]
    for result in results:
        lines.append(
            f"| `{result['copy_id']}` | `{result['audit_id']}` | {result['layer']} | "
            f"{result['language']} | {'، '.join(result['rows'])} | {result['correspondence']} | "
            "`OPEN-CANDIDATE` |"
        )
    lines += [
        "",
        "## الصفوف التي لم تجد نقضًا مطابقًا",
        "",
        "لم يجد الفحص نقضًا مسجلًا يزول بصفّي `SEM-04` أو `SEM-05`، ولا بالرجل "
        "الآرامية في `SIB-07`. بقي `RET-R-005` مردودًا لأن تقابله المطلوب "
        "`ס ↔ ص` لا `ס ↔ ش`.",
        "",
        "## التحقق الجسدي",
        "",
        "لكل بطاقة معادة سطر نسخ واحد في جسمها يذكر النقض السابق والصف الذي "
        "أزال عائق الصوت، ويليه حكم `OPEN-CANDIDATE`. لم تحذف بطاقة ولم يمح حكم تاريخي.",
        "",
    ]
    text = "\n".join(lines)
    if "—" in text:
        raise RuntimeError("تسربت شرطة طويلة إلى المحضر")
    AUDIT.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    counts = network_counts()
    records, by_id = load_records()
    results = []
    for target in TARGETS:
        record = by_id[target["audit_id"]]
        verify_target(record, target)
        results.append(apply_target(record, target, args.apply))
    if args.apply:
        if not all(result["copy_line_present"] for result in results):
            raise RuntimeError("لم يثبت سطر النسخ في بطاقة معادة")
        write_outputs(records, results, counts)
    print(
        json.dumps(
            {
                "screened": len(records),
                "reopened": len(results),
                "network_core_rows": counts[0],
                "network_parsed_rows": counts[2],
                "copy_lines_present": sum(result["copy_line_present"] for result in results),
                "applied": args.apply,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
