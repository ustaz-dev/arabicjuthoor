from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import lane_d_build_old_english_old_irish as build


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "04-cross-linguistic" / "data"
AUDIT_DIR = ROOT / "05-audits"
BATCH_SIZE = 500
MANIFEST_PATH = DATA_DIR / "lane_d_source_snapshot_manifest.json"
INVENTORY_PATH = DATA_DIR / "lane_d_member_inventory.jsonl"
COVERAGE_PATH = DATA_DIR / "lane_d_coverage.jsonl"
SUMMARY_PATH = AUDIT_DIR / "lane-d-final-summary.md"
COVERAGE_FIELDS = (
    "member_id",
    "language",
    "form",
    "branch_meaning",
    "non_issuance_reason",
    "batch_number",
)

ARABIC_SOURCE_NAMES = (
    "كتاب العين",
    "المحيط في اللغة",
    "الصحاح",
    "لسان العرب",
    "أساس البلاغة",
    "تاج العروس",
)

ORBIT_CORRECTIONS = {
    "en-horn-ang-noun-lUMJjxcE@L527S1",
    "en-horn-ang-noun-eF7ljlKs@L527S2",
    "en-burg-ang-noun-rciIbhZo@L1835S2",
    "en-þri-ang-num-i1udsME9@L3245S1",
    "en-derc-sga-noun-R8IVtfcO@L1845S1",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def stable_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if current != text:
            raise RuntimeError(f"refusing to overwrite changed lane-D artifact: {path}")
        return
    path.write_text(text, encoding="utf-8", newline="\n")


def current_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def load_coverage() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    with COVERAGE_PATH.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            row = json.loads(line)
            if tuple(row) != COVERAGE_FIELDS:
                raise RuntimeError(
                    f"coverage line {line_no}: fields {tuple(row)} != {COVERAGE_FIELDS}"
                )
            member_id = row["member_id"]
            if member_id in seen:
                raise RuntimeError(
                    f"coverage line {line_no}: duplicate member_id {member_id}"
                )
            if not isinstance(row["batch_number"], int) or row["batch_number"] < 1:
                raise RuntimeError(
                    f"coverage line {line_no}: invalid batch_number"
                )
            if not all(
                isinstance(row[field], str)
                for field in COVERAGE_FIELDS
                if field != "batch_number"
            ):
                raise RuntimeError(f"coverage line {line_no}: non-string text field")
            seen.add(member_id)
            rows.append(row)
    return rows


def card_blocks(text: str) -> dict[str, str]:
    blocks: dict[str, str] = {}
    pattern = re.compile(
        r"^### بطاقة:.*?(?=^### بطاقة:|^## إقفال الجولة)",
        re.MULTILINE | re.DOTALL,
    )
    for match in pattern.finditer(text):
        block = match.group(0)
        identity = re.search(r"المعرّف المركب=([^\n]+)\.$", block, re.MULTILINE)
        if not identity:
            raise RuntimeError("card without composite identity")
        composite_id = identity.group(1)
        if composite_id in blocks:
            raise RuntimeError(f"duplicate composite card identity: {composite_id}")
        blocks[composite_id] = block
    return blocks


def positive_checks(
    spec: build.SourceSpec,
    reading_text: str,
    blocks: dict[str, str],
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    shift_network = (
        ROOT / "04-cross-linguistic" / "shift-network-draft.md"
    ).read_text(encoding="utf-8")
    results = []
    for item in items:
        if not item["positive"]:
            continue
        composite_id = item["composite_id"]
        block = blocks[composite_id]
        scan_line = re.search(r"^- مسحُ المعاني العربيّة: (.+)$", block, re.MULTILINE)
        sound_line = re.search(r"^- مسارُ الصوت: (.+)$", block, re.MULTILINE)
        if not scan_line or not sound_line:
            raise RuntimeError(f"positive card missing scan or sound: {composite_id}")
        named_sources = sorted(
            name for name in ARABIC_SOURCE_NAMES if name in scan_line.group(1)
        )
        if len(named_sources) < 2:
            raise RuntimeError(
                f"positive card has fewer than two named old Arabic sources: {composite_id}"
            )
        row_ids = sorted(
            set(
                re.findall(
                    r"(?<![A-Z0-9])[A-Z]{2,}(?:-[A-Z0-9]+)+(?![A-Z0-9])",
                    sound_line.group(1),
                )
            )
        )
        unknown_rows = [row_id for row_id in row_ids if row_id not in shift_network]
        if unknown_rows:
            raise RuntimeError(
                f"positive card cites unknown sound rows {unknown_rows}: {composite_id}"
            )
        if composite_id not in ORBIT_CORRECTIONS:
            raise RuntimeError(f"positive card lacks explicit orbit correction: {composite_id}")
        correction_marker = f"### تصحيح: `{composite_id}`"
        if correction_marker not in reading_text:
            raise RuntimeError(f"missing orbit correction text: {composite_id}")
        results.append(
            {
                "composite_id": composite_id,
                "arabic_sources": named_sources,
                "sound_rows": row_ids,
                "orbit_correction_present": True,
            }
        )
    return results


def source_items(
    spec: build.SourceSpec,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    stats = build.scan(spec)
    items: list[dict[str, Any]] = []
    sequence = 0
    for line_no, entry, error in build.iter_records(spec):
        if error:
            sequence += 1
            items.append(
                {
                    "sequence": sequence,
                    "language": spec.key,
                    "unit_type": "source-gap",
                    "line": line_no,
                    "sense_index": None,
                    "sense_id": None,
                    "composite_id": f"SOURCE-LINE-L{line_no}",
                    "word": None,
                    "gloss": None,
                    "kind": "blocked-source",
                    "state": "SOURCE-GAP",
                    "judgment": "(لا حكم صادر)",
                    "positive": False,
                    "closure": False,
                    "source_error": error,
                }
            )
            continue
        assert entry is not None
        for sense_index, sense in enumerate(entry.get("senses") or [], 1):
            sequence += 1
            sense_id = build.clean(sense.get("id"))
            assessment = build.assess(spec, entry, sense)
            items.append(
                {
                    "sequence": sequence,
                    "language": spec.key,
                    "unit_type": "member",
                    "line": line_no,
                    "sense_index": sense_index,
                    "sense_id": sense_id,
                    "composite_id": f"{sense_id}@L{line_no}S{sense_index}",
                    "word": build.clean(entry.get("word") or "(بلا لمة)"),
                    "gloss": build.sense_gloss(sense),
                    "kind": assessment["kind"],
                    "state": assessment["state"],
                    "judgment": assessment["judgment"],
                    "positive": assessment["kind"] == "positive",
                    "closure": assessment["kind"] == "closure",
                    "source_error": None,
                }
            )
    expected_inventory = stats["members"] + len(stats["bad_lines"])
    if len(items) != expected_inventory:
        raise RuntimeError(
            f"{spec.key}: inventory units {len(items)} != expected {expected_inventory}"
        )
    return items, stats


def audit_text(
    spec: build.SourceSpec,
    batch_number: int,
    batch: list[dict[str, Any]],
    inventory_total: int,
    cumulative_positive: int,
    cumulative_closure: int,
) -> str:
    start = batch[0]
    end = batch[-1]
    positives = sum(int(item["positive"]) for item in batch)
    closures = sum(int(item["closure"]) for item in batch)
    remaining = inventory_total - end["sequence"]
    blocked = sum(item["unit_type"] == "source-gap" for item in batch)
    return (
        f"# المسار د: {spec.language_ar}، الدفعة {batch_number:03d}\n\n"
        f"- اللقطة: `{spec.pin}`؛ المصدر: "
        f"`{spec.source_path.relative_to(ROOT).as_posix()}`؛ SHA-256: "
        f"`{spec.expected_sha256}`.\n"
        f"- نطاق الدفعة: من الوحدة {start['sequence']} "
        f"`{start['composite_id']}` (السطر {start['line']}) إلى الوحدة "
        f"{end['sequence']} `{end['composite_id']}` (السطر {end['line']})؛ "
        f"بقي في الجرد بعد الدفعة: {remaining}.\n"
        f"- أعضاء المعنى المفحوصون في الدفعة: "
        f"{sum(item['unit_type'] == 'member' for item in batch)}.\n"
        f"- فجوات المصدر المستهلكة من الطابور: {blocked}.\n"
        f"- الصلات الموجبة في الدفعة: {positives}.\n"
        f"- الإغلاقات في الدفعة: {closures}.\n"
        f"- الصلات الموجبة التراكمية: {cumulative_positive}.\n"
        f"- الإغلاقات التراكمية: {cumulative_closure}.\n"
        "- لم يُجمع الرقمان، ولم يصدر عن الفجوات حكم سالب.\n"
    )


def final_summary(
    manifests: list[dict[str, Any]],
    audits: list[Path],
) -> str:
    oe = next(item for item in manifests if item["language"] == "oe")
    oi = next(item for item in manifests if item["language"] == "oi")
    written = [
        "04-cross-linguistic/readings/old-english.md",
        "04-cross-linguistic/readings/old-irish.md",
        "04-cross-linguistic/data/lane_d_source_snapshot_manifest.json",
        "04-cross-linguistic/data/lane_d_member_inventory.jsonl",
        "04-cross-linguistic/data/lane_d_coverage.jsonl",
        "scripts/lane_d_build_old_english_old_irish.py",
        "scripts/lane_d_audit_old_english_old_irish.py",
        *[path.relative_to(ROOT).as_posix() for path in audits],
        "05-audits/lane-d-two-lens-review.md",
        "05-audits/lane-d-coverage-compaction-2026-07-30.md",
        "05-audits/lane-d-final-summary.md",
    ]
    written_lines = "\n".join(f"- `{path}`" for path in written)
    return (
        "# المسار د: محضر الإقفال\n\n"
        "## قياس الطابور\n\n"
        f"- الإنجليزية القديمة: بدأ الجرد من الوحدة 1 وانتهى عند الوحدة "
        f"{oe['inventory_units']}؛ بقي في الجرد: 0. فُحصت "
        f"{oe['members']} وحدة عضو، واستهلك الطابور "
        f"{len(oe['bad_lines'])} فجوة مصدر مسماة.\n"
        f"- الإيرلندية القديمة: بدأ الجرد من الوحدة 1 وانتهى عند الوحدة "
        f"{oi['inventory_units']}؛ بقي في الجرد: 0. فُحصت "
        f"{oi['members']} وحدة عضو، ولا فجوة سطر في المصدر.\n"
        "- قياس الباقي: صفر وحدة غير مفحوصة في اللقطتين المثبتتين. لا تمنح هذه العبارة "
        "شهادة parse كاملة للسطر الإنجليزي المقطوع؛ حالته باقية `SOURCE-GAP`.\n"
        "- سؤال المؤلف المسجل والمتخطى: هل يستبدل مورد الإنجليزية القديمة بلقطة كاملة "
        "تعيد السطر 7949 المقطوع؟ هذا تنزيل مصدر جديد، فلم يُنفذ ولم يوقف بقية الطابور.\n\n"
        "## الرقمان المفصولان\n\n"
        f"- الإنجليزية القديمة، الصلات الموجبة: {oe['positive']}.\n"
        f"- الإنجليزية القديمة، الإغلاقات: {oe['closures']}.\n"
        f"- الإيرلندية القديمة، الصلات الموجبة: {oi['positive']}.\n"
        f"- الإيرلندية القديمة، الإغلاقات: {oi['closures']}.\n"
        "- لا يجمع أي زوج من هذه الأرقام.\n\n"
        "## شكل التسجيل\n\n"
        f"- الإنجليزية القديمة: {oe['full_cards']} بطاقة كاملة و"
        f"{oe['coverage_records']} سطر تغطية آلي؛ المجموع "
        f"{oe['registered_members']} عضوًا مسجلًا.\n"
        f"- الإيرلندية القديمة: {oi['full_cards']} بطاقة كاملة و"
        f"{oi['coverage_records']} سطر تغطية آلي؛ المجموع "
        f"{oi['registered_members']} عضوًا مسجلًا.\n"
        "- البطاقة الكاملة مقصورة على الحكم الموجب أو الإغلاق النهائي، وسطر التغطية "
        "مقصور على العضو غير المحكوم.\n\n"
        "## حدود النتيجة\n\n"
        "- كل عضو معنى قابل للتحليل في اللقطة له مصير مسجل: بطاقة RECOVERY-v2 كاملة "
        "للحكم أو الإغلاق، أو سطر واحد في `lane_d_coverage.jsonl` لعدم الإصدار. "
        "الصورة `form_of` إغلاق هوية كامل لكنها لا تولد حكمًا مستقلا.\n"
        "- بقيت فجوات الأداة والقانون والمصدر بأسمائها، ولم تتحول إلى `NO-TRACE`.\n"
        "- لم تُفتح نتائج القوطية أو النوردية أو الويلزية في هذه الجولة، ولم تُجر مقارنة "
        "عائد الفروع بعد.\n"
        "- لم يُشغّل سكربت مشترك يعيد بناء ملفًا مشتركًا، ولم يُعدّل خط البرهان.\n\n"
        "## الملفات التي كُتب فيها\n\n"
        f"{written_lines}\n"
    )


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    all_items: list[dict[str, Any]] = []
    manifests: list[dict[str, Any]] = []
    audit_paths: list[Path] = []
    coverage_rows = load_coverage()

    for spec in build.SOURCES:
        pre_hash = digest(spec.source_path)
        pre_stat = spec.source_path.stat()
        items, stats = source_items(spec)
        post_hash = digest(spec.source_path)
        post_stat = spec.source_path.stat()
        if (
            pre_hash != post_hash
            or pre_stat.st_size != post_stat.st_size
            or pre_stat.st_mtime_ns != post_stat.st_mtime_ns
        ):
            raise RuntimeError(f"{spec.key}: source changed during lane-D scan")

        reading_text = spec.output_path.read_text(encoding="utf-8")
        blocks = card_blocks(reading_text)
        member_items = [item for item in items if item["unit_type"] == "member"]
        expected_full_ids = {
            item["composite_id"]
            for item in member_items
            if item["positive"] or item["closure"]
        }
        expected_coverage_ids = {
            item["composite_id"]
            for item in member_items
            if not item["positive"] and not item["closure"]
        }
        spec_coverage = [
            row for row in coverage_rows if row["language"] == spec.language_en
        ]
        actual_coverage_ids = {row["member_id"] for row in spec_coverage}
        if set(blocks) != expected_full_ids:
            missing = sorted(expected_full_ids - set(blocks))[:5]
            extra = sorted(set(blocks) - expected_full_ids)[:5]
            raise RuntimeError(
                f"{spec.key}: full-card/source identity mismatch; "
                f"missing={missing}, extra={extra}"
            )
        if actual_coverage_ids != expected_coverage_ids:
            missing = sorted(expected_coverage_ids - actual_coverage_ids)[:5]
            extra = sorted(actual_coverage_ids - expected_coverage_ids)[:5]
            raise RuntimeError(
                f"{spec.key}: coverage/source identity mismatch; "
                f"missing={missing}, extra={extra}"
            )
        registered_ids = set(blocks) | actual_coverage_ids
        expected_ids = {item["composite_id"] for item in member_items}
        if registered_ids != expected_ids or set(blocks) & actual_coverage_ids:
            raise RuntimeError(f"{spec.key}: member registration partition failed")
        output_checks = build.verify_output(spec, stats, spec_coverage)
        positives = positive_checks(spec, reading_text, blocks, items)

        inventory_total = len(items)
        cumulative_positive = 0
        cumulative_closure = 0
        for offset in range(0, inventory_total, BATCH_SIZE):
            batch = items[offset : offset + BATCH_SIZE]
            cumulative_positive += sum(int(item["positive"]) for item in batch)
            cumulative_closure += sum(int(item["closure"]) for item in batch)
            batch_number = offset // BATCH_SIZE + 1
            audit_path = (
                AUDIT_DIR
                / f"lane-d-{spec.key}-batch-{batch_number:03d}.md"
            )
            stable_write(
                audit_path,
                audit_text(
                    spec,
                    batch_number,
                    batch,
                    inventory_total,
                    cumulative_positive,
                    cumulative_closure,
                ),
            )
            audit_paths.append(audit_path)

        if cumulative_positive != stats["positive"]:
            raise RuntimeError(f"{spec.key}: cumulative positive mismatch")
        if cumulative_closure != stats["closures"]:
            raise RuntimeError(f"{spec.key}: cumulative closure mismatch")

        manifests.append(
            {
                "language": spec.key,
                "language_name": spec.language_en,
                "snapshot_name": spec.pin,
                "source_label": (
                    f"Kaikki.org {spec.language_en} dictionary, derived from Wiktionary"
                ),
                "source_path": spec.source_path.relative_to(ROOT).as_posix(),
                "sha256": pre_hash,
                "bytes": pre_stat.st_size,
                "mtime_utc": datetime.fromtimestamp(
                    pre_stat.st_mtime, tz=UTC
                ).isoformat(),
                "valid_json_records": stats["valid_records"],
                "members": stats["members"],
                "bad_lines": stats["bad_lines"],
                "inventory_units": inventory_total,
                "remaining_inventory": 0,
                "queue_drained": True,
                "source_parse_complete": not stats["bad_lines"],
                "positive": stats["positive"],
                "closures": stats["closures"],
                "full_cards": len(blocks),
                "coverage_records": len(spec_coverage),
                "registered_members": len(registered_ids),
                "states": stats["states"],
                "judgments": stats["judgments"],
                "reading_path": spec.output_path.relative_to(ROOT).as_posix(),
                "reading_sha256": digest(spec.output_path),
                "coverage_path": COVERAGE_PATH.relative_to(ROOT).as_posix(),
                "output_checks": output_checks,
                "positive_checks": positives,
            }
        )
        all_items.extend(items)

    created_utc = datetime.now(tz=UTC).isoformat()
    if MANIFEST_PATH.exists():
        prior_manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        created_utc = prior_manifest["created_utc"]
    manifest = {
        "schema": "lane-d-source-snapshot-v2",
        "created_utc": created_utc,
        "batch_size": BATCH_SIZE,
        "coverage_sha256": digest(COVERAGE_PATH),
        "coverage_records": len(coverage_rows),
        "languages": manifests,
        "independence_guard": (
            "No Gothic, Old Norse, or Welsh reading result was opened before both "
            "lane-D inventories were drained."
        ),
    }
    current_write(
        MANIFEST_PATH,
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    inventory_text = "".join(
        json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n"
        for item in all_items
    )
    stable_write(INVENTORY_PATH, inventory_text)
    current_write(SUMMARY_PATH, final_summary(manifests, audit_paths))

    print(
        json.dumps(
            {
                "manifest": str(MANIFEST_PATH),
                "inventory": str(INVENTORY_PATH),
                "audits": len(audit_paths),
                "summary": str(SUMMARY_PATH),
                "languages": manifests,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
