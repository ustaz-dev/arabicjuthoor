# -*- coding: utf-8 -*-
"""أعد فتح النقوض التي جعلت اقتراض الطرف العربي علة وجذره قرآني.

قرار المؤلف في 2026-08-06 يجعل كل جذر وارد في القرآن عربيًا محضًا. لذلك
تنسخ علة اقتراض الطرف العربي وحدها، وتعود البطاقة إلى OPEN-CANDIDATE من غير
استعادة آلية للحكم السابق. تبقى علل الصوت والصرف والمصدر والمدار ظاهرة.
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
import quranic_roots as Q  # noqa: E402


REGISTRY = ROOT / "data" / "recorded-retractions.json"
QURANIC = ROOT / "data" / "quranic-roots.json"
DATA = ROOT / "data" / "quranic-loan-retraction-rescreen.json"
AUDIT = ROOT / "05-audits" / "2026-08-06-quranic-loan-retraction-rescreen.md"

TARGETS = (
    {
        "audit_id": "RET-N-003",
        "copy_id": "RET-REOPEN-QUR-001",
        "root": "زوج",
        "cue": "العربيّةُ تُنسبُ",
        "remaining": "يبقى فحص الصامت d في الصورة الأقدم وصحة المسار الصوتي واستقلال الشاهدين العربيين",
    },
    {
        "audit_id": "RET-N-012",
        "copy_id": "RET-REOPEN-QUR-002",
        "root": "منى",
        "canonical_root": "مني",
        "cue": "فالطرفُ العربيُّ نفسُه مقترضٌ",
        "remaining": "يبقى تعيين المعجم العربي الثاني وضبط مدار النواة وفصل وحدة الوزن عن مواد مني ومنن",
    },
    {
        "audit_id": "RET-N-014",
        "copy_id": "RET-REOPEN-QUR-003",
        "root": "تجر",
        "cue": "العربيّةِ مقترضةٌ من الآراميّةِ",
        "remaining": "يبقى فحص وزن qattāl واللاحقة وأصالة الجيم وحكم النواة الحسي",
    },
    {
        "audit_id": "RET-R-008",
        "copy_id": "RET-REOPEN-QUR-004",
        "root": "تجر",
        "cue": "الاتجاه نفسه المقرر في תגר",
        "remaining": "يبقى استيفاء الصوامت الثلاثة والنص المنقول من كل معجم قبل إعادة الحكم الجذري",
    },
    {
        "audit_id": "RET-R-011",
        "copy_id": "RET-REOPEN-QUR-005",
        "root": "تجر",
        "cue": "العربية تاجر مقترضة من الآرامية",
        "remaining": "يبقى إعادة فحص العضو والصرف والاتجاه البديل من العربية أو الأصل المشترك قبل استعادة ROOT-TRACE",
    },
    {
        "audit_id": "RET-R-060",
        "copy_id": "RET-REOPEN-QUR-006",
        "root": "نحس",
        "cue": "نُحاسَ العربيّةِ مرشَّحٌ قائمٌ للانتقالِ من الآراميّة",
        "remaining": "يبقى توثيق المصدر العربي الثاني وفحص الرجل الصوتية الفردية من غير إنشاء صف عام",
    },
    {
        "audit_id": "RET-N-020",
        "copy_id": "RET-REOPEN-QUR-007",
        "root": "تقن",
        "cue": "مادةُ تقن متأخّرةٌ مطعونٌ في أصالتِها",
        "remaining": "يبقى نزع السابقة القبطية وفحص النون الأصلية ومسار الترجمة الكنسية",
    },
    {
        "audit_id": "RET-R-058",
        "copy_id": "RET-REOPEN-QUR-008",
        "root": "سبط",
        "cue": "وهذا وسمُ اتّجاهٍ صريح",
        "remaining": "يبقى فصل معنى القبيلة عن معنى الشعر المسترسل وفحص المدار والمصدرين",
    },
)


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def blocks(text: str) -> list[str]:
    return re.split(r"(?m)(?=^### )", text)


def load_registry() -> tuple[list[dict], dict[str, dict]]:
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    records = payload["records"]
    if len(records) != 146:
        raise RuntimeError(f"تغير سجل النقوض: {len(records)}")
    by_id = {record["audit_id"]: record for record in records}
    if len(by_id) != len(records):
        raise RuntimeError("تكرر معرف نقض")
    return records, by_id


def quranic_index() -> dict[str, tuple[str, int]]:
    payload = json.loads(QURANIC.read_text(encoding="utf-8"))
    return {
        Q.bare(root): (root, int(count))
        for root, count in payload["by_root"].items()
    }


def copy_line(target: dict, canonical: str, occurrences: int) -> str:
    return nfc(
        f"- سطر النسخ (2026-08-06، {target['copy_id']}): علة الحكم بأن الطرف "
        f"العربي في الجذر `{target['root']}` مقترض منسوخة بقرار المؤلف؛ الجذر "
        f"القرآني الموحّد `{canonical}` مشهود في {occurrences} موضعًا، فهو عربي "
        "محض لا يحكم عليه بالاقتراض؛ عادت البطاقة إلى OPEN-CANDIDATE ولا تستعيد "
        f"درجتها السابقة آليًا؛ {target['remaining']}."
    )


def verdict_line(target: dict, canonical: str) -> str:
    return nfc(
        "- الحكم (إعادة فرز الأصالة القرآنية، 2026-08-06): OPEN-CANDIDATE؛ "
        f"سقطت علة اقتراض الطرف العربي في `{canonical}` وحدها، وبقيت بقية "
        "بوابات البطاقة للفحص العضوي."
    )


def apply_target(
    record: dict,
    target: dict,
    canonical: str,
    occurrences: int,
    apply: bool,
) -> dict[str, object]:
    reason = " | ".join(record["reasons"])
    if target["cue"] not in reason:
        raise RuntimeError(f"تغيرت علة {target['audit_id']}")
    path = ROOT / record["source_file"]
    text = path.read_text(encoding="utf-8")
    old_marker = nfc(f"سطر النسخ (2026-08-05، {target['audit_id']})")
    new_marker = nfc(f"سطر النسخ (2026-08-06، {target['copy_id']})")
    parts = blocks(text)
    matches = [index for index, part in enumerate(parts) if old_marker in nfc(part)]
    if len(matches) != 1:
        raise RuntimeError(
            f"اختل حضور جسم {target['audit_id']}: {len(matches)}"
        )
    index = matches[0]
    part = parts[index]
    present = new_marker in nfc(part)
    if not present and apply:
        lines = part.splitlines()
        old_lines = [i for i, line in enumerate(lines) if old_marker in nfc(line)]
        if len(old_lines) != 1:
            raise RuntimeError(f"اختل سطر النقض في {target['audit_id']}")
        insert_at = old_lines[0] + 1
        lines[insert_at:insert_at] = [
            copy_line(target, canonical, occurrences),
            verdict_line(target, canonical),
        ]
        parts[index] = "\n".join(lines) + ("\n" if part.endswith("\n") else "")
        updated = "".join(parts)
        before_dashes = text.count("—") + text.count("–")
        after_dashes = updated.count("—") + updated.count("–")
        if after_dashes > before_dashes:
            raise RuntimeError("تسربت شرطة طويلة جديدة إلى ملف القراءة")
        path.write_text(updated, encoding="utf-8", newline="\n")
        present = True
    return {
        "audit_id": target["audit_id"],
        "copy_id": target["copy_id"],
        "layer": record["layer"],
        "language": record["language"],
        "source_file": record["source_file"],
        "heading": record["heading"],
        "root_as_recorded": target["root"],
        "quranic_root": canonical,
        "quranic_occurrences": occurrences,
        "removed_reason": "ARABIC-SIDE-LOAN",
        "remaining_review": target["remaining"],
        "decision": "OPEN-CANDIDATE",
        "copy_line_present": present,
    }


def write_outputs(records: list[dict], results: list[dict]) -> None:
    by_layer = collections.Counter(result["layer"] for result in results)
    by_root = collections.Counter(result["quranic_root"] for result in results)
    payload = {
        "schema_version": "1.0",
        "date": "2026-08-06",
        "rule": "كل جذر ورد في القرآن عربي محض، فلا يحكم عليه بالاقتراض من فرع آخر.",
        "summary": {
            "retractions_screened": len(records),
            "reopened": len(results),
            "positive_verdicts_restored": 0,
            "by_layer": dict(sorted(by_layer.items())),
            "by_quranic_root": dict(sorted(by_root.items())),
        },
        "records": results,
    }
    data_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if "—" in data_text or "–" in data_text:
        raise RuntimeError("تسربت شرطة طويلة إلى بيانات إعادة الفرز")
    DATA.write_text(data_text, encoding="utf-8", newline="\n")

    lines = [
        "# محضر إعادة فرز النقوض بقاعدة الأصالة القرآنية، 2026-08-06",
        "",
        "## القانون",
        "",
        "كل جذر ورد في القرآن عربي محض بقرار المؤلف، فلا يحكم عليه بالاقتراض "
        "من فرع آخر. ينسخ هذا القرار علة اقتراض الطرف العربي فقط، ولا يستعيد "
        "حكم نسب موجبًا ولا يرفع علة صوت أو صرف أو مصدر أو مدار.",
        "",
        "## النتيجة",
        "",
        f"فحص سجل النقوض كله، وعدده {len(records)}، وأعيدت {len(results)} بطاقات "
        "إلى `OPEN-CANDIDATE`. لم تستعد أي بطاقة درجتها السابقة آليًا.",
        "",
        "| رقم النسخ | النقض | الطبقة | اللسان | الجذر القرآني | المواضع | ما بقي للفحص |",
        "|---|---|---|---|---|---:|---|",
    ]
    for result in results:
        lines.append(
            f"| `{result['copy_id']}` | `{result['audit_id']}` | {result['layer']} | "
            f"{result['language']} | `{result['quranic_root']}` | "
            f"{result['quranic_occurrences']} | {result['remaining_review']} |"
        )
    lines += [
        "",
        "## التحقق الجسدي",
        "",
        "ثبت في جسم كل بطاقة سطر نسخ واحد بعد النقض المؤرخ 2026-08-05، ويليه "
        "حكم حي واحد `OPEN-CANDIDATE`. بقي النقض التاريخي في موضعه ولم يحذف حرف.",
        "",
    ]
    audit_text = "\n".join(lines)
    if "—" in audit_text or "–" in audit_text:
        raise RuntimeError("تسربت شرطة طويلة إلى المحضر")
    AUDIT.write_text(audit_text, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    records, by_id = load_registry()
    quranic = quranic_index()
    results = []
    for target in TARGETS:
        query = Q.bare(target.get("canonical_root", target["root"]))
        if query not in quranic:
            raise RuntimeError(f"الجذر غير قرآني في الجرد: {target['root']}")
        canonical, occurrences = quranic[query]
        results.append(
            apply_target(
                by_id[target["audit_id"]],
                target,
                canonical,
                occurrences,
                args.apply,
            )
        )
    if args.apply:
        if not all(result["copy_line_present"] for result in results):
            raise RuntimeError("لم تثبت سطور النسخ كلها")
        write_outputs(records, results)
    print(json.dumps({
        "screened": len(records),
        "reopened": len(results),
        "copy_lines_present": sum(r["copy_line_present"] for r in results),
        "applied": args.apply,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
