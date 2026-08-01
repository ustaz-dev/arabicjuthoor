#!/usr/bin/env python3
"""Lane D, month scan: Old English, Old Irish, and Middle English.

This is a lane-local retrieval and coverage writer.  It reads the frozen Arabic
inventory and the frozen shift network, but it does not rebuild either shared
artifact and it never writes to the proof line.  Its job is deliberately
narrow:

* pin and walk every member in the three Kaikki snapshots;
* inspect the full-root and binary-nucleus layers together for every member;
* preserve every non-issued member in ``lane_d_coverage.jsonl``;
* keep source, morphology, name-root, and direction gaps open;
* write short, deterministic 500-unit batch minutes with two separate counts.

The machine output is retrieval evidence, not a semantic verdict.  Positive
judgments continue to live in the reading files and must meet the two-old-
Arabic-sources rule there.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from recovery_pipeline.candidates import ArabicInventory, CandidateHit, generate_hits
from recovery_pipeline.network import compile_network


ROOT = Path(__file__).resolve().parents[1]
READINGS = ROOT / "04-cross-linguistic" / "readings"
DATA_DIR = ROOT / "04-cross-linguistic" / "data"
AUDIT_DIR = ROOT / "05-audits"
COVERAGE_PATH = DATA_DIR / "lane_d_coverage.jsonl"
MANIFEST_PATH = DATA_DIR / "lane_d_month_scan_manifest.json"
ISSUED_SCANS_PATH = DATA_DIR / "lane_d_issued_layer_scans.jsonl"
ME_TRANSMISSIONS_PATH = DATA_DIR / "lane_d_middle_english_transmissions.jsonl"
BATCH_AUDIT_PATH = AUDIT_DIR / "lane-d-month-batches.md"
BATCH_SIZE = 500


@dataclass(frozen=True)
class SourceSpec:
    key: str
    language: str
    language_ar: str
    scope: str
    source_path: Path
    reading_path: Path
    expected_sha256: str
    expected_bytes: int
    expected_records: int
    expected_members: int
    expected_bad_lines: tuple[int, ...]
    pin: str


SOURCES = (
    SourceSpec(
        key="oe",
        language="Old English",
        language_ar="الإنجليزية القديمة",
        scope="germanic",
        source_path=ROOT / "Resources/english_old/kaikki.org-dictionary-OldEnglish.jsonl",
        reading_path=READINGS / "old-english.md",
        expected_sha256="85b8cbf5ac03035e597ae97d093865bae43c6b42def79b959467f34f07f28b74",
        expected_bytes=24_493_745,
        expected_records=7_948,
        expected_members=11_694,
        expected_bad_lines=(7_949,),
        pin="lane-d-old-english-kaikki-2026-07-30-85b8cbf5",
    ),
    SourceSpec(
        key="oi",
        language="Old Irish",
        language_ar="الإيرلندية القديمة",
        scope="celtic",
        source_path=ROOT / "Resources/old_irish/kaikki.org-dictionary-OldIrish.jsonl",
        reading_path=READINGS / "old-irish.md",
        expected_sha256="3d4fa67a5b9369aba27f167aab549e14a3d79a8f60c266b223a0971492cd763d",
        expected_bytes=18_174_722,
        expected_records=6_429,
        expected_members=8_506,
        expected_bad_lines=(),
        pin="lane-d-old-irish-kaikki-2026-07-30-3d4fa67a",
    ),
    SourceSpec(
        key="me",
        language="Middle English",
        language_ar="الإنجليزية الوسطى",
        scope="germanic",
        source_path=ROOT / "Resources/english_middle/kaikki.org-dictionary-MiddleEnglish.jsonl",
        reading_path=READINGS / "middle-english.md",
        expected_sha256="4e9ea08eba8e2ff35cf7cb84dd06ad513db6ed75d0f611f0ed2cb475caf6ad67",
        expected_bytes=56_368_387,
        expected_records=49_779,
        expected_members=62_971,
        expected_bad_lines=(),
        pin="lane-d-middle-english-kaikki-2026-08-01-4e9ea08e",
    ),
)


POSITIVE_RE = re.compile(
    r"^(?:ROOT-TRACE|ROOT-ECHO|NUCLEUS-TRACE|NUCLEUS-ECHO|FLOOR-TRACE)$"
)
FINAL_CLOSURE_RE = re.compile(
    r"^(?:LOANWORD|NO-TRACE|FORM-OF-JUDGED-BASE|THIRD-PARTY-TO-BRANCH)$"
)
CARD_RE = re.compile(r"(?ms)^### بطاقة:.*?(?=^### بطاقة:|^## |\Z)")
JUDGMENT_RE = re.compile(r"^- الحكم \(استكشاف\):\s*(.+?)\.?$", re.MULTILINE)
IDENTITY_RE = re.compile(r"المعرّف المركب=([^\n]+?)\.?$", re.MULTILINE)
TABLE_ID_RE = re.compile(r"^\|\s*([^|`\s][^|]*?@L\d+S\d+)\s*\|", re.MULTILINE)
SEMITIC_MARKER_RE = re.compile(
    r"Arabic|Hebrew|Aramaic|Syriac|Phoenician|Punic|Akkadian|Semitic", re.I
)
SEMITIC_DIRECTION_RE = re.compile(
    r"(?:borrowed\s+from|from|via|calque\s+of|of)\s+"
    r"(?:Andalusian\s+Arabic|dialectal\s+Arabic|Arabic|Biblical\s+Hebrew|Hebrew|"
    r"Aramaic|Syriac|Phoenician|Punic|Akkadian|a\s+Semitic\s+language|Semitic)",
    re.I,
)
SEMITIC_ORIGIN_RE = re.compile(r"(?:of Semitic origin|Semitic borrowing)", re.I)
SPECULATIVE_RE = re.compile(r"\b(?:possibly|perhaps|maybe|uncertain)\b", re.I)
THIRD_PARTY_RE = re.compile(
    r"\b(?:borrowed from|from)\s+(?:Old French|Anglo-Norman|Latin|Medieval Latin|"
    r"Ancient Greek|Old Norse|Middle French|Old Spanish|Italian|Middle Dutch|"
    r"Proto-Brythonic|Welsh|Sanskrit|Persian)\b",
    re.I,
)

ISSUED_CARD_FIELDS = (
    "- إصدارُ البروتوكول:",
    "- الكلمةُ في الفرع:",
    "- أقدمُ صورةٍ مستعادة:",
    "- الخطوةُ صفر (التعرية بصرف الفرع):",
    "- درجةُ المقارنة:",
    "- مسحُ المعاني العربيّة:",
    "- المقابلُ من اللسان:",
    "- مسارُ الصوت:",
    "- المعنى من قاموس الفرع:",
    "- المدار:",
    "- المصفاة:",
    "- فصلُ المتجانسات والاقتراض:",
    "- مؤشر اليتم:",
    "- إشعاع الأسرة في الفرع:",
    "- إشعاع الأسرة في العربية:",
    "- جسورُ الاسترداد المفحوصة:",
    "- حالةُ الإغلاق:",
    "- الحكم (استكشاف):",
    "- ملاحظات:",
)


VOWELS = set("aeiouyæœøəɛɪʊɔɑɒʌɨɯ")
IGNORED = set(" -_.,;:·'’ʼ()[]/\\?*!+|{}<>")


@dataclass(frozen=True)
class Normalized:
    tokens: tuple[str, ...]
    unknown: tuple[str, ...]
    ambiguities: tuple[str, ...]
    folded: str

    @property
    def skeleton(self) -> str:
        return "-".join(self.tokens)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            value.update(chunk)
    return value.hexdigest()


def clean(value: Any, limit: int | None = None) -> str:
    text = " ".join(str(value or "").split())
    if limit is not None and len(text) > limit:
        return text[: max(0, limit - 1)].rstrip() + "…"
    return text


def sense_gloss(sense: dict[str, Any]) -> str:
    values = sense.get("glosses") or sense.get("raw_glosses") or []
    return clean("؛ ".join(str(value) for value in values), 700) or "(بلا شرح معجمي)"


def relation_targets(sense: dict[str, Any]) -> tuple[str, ...]:
    values: list[str] = []
    for field in ("form_of", "alt_of"):
        for item in sense.get(field) or []:
            value = item.get("word") if isinstance(item, dict) else item
            value = clean(value)
            if value and value not in values:
                values.append(value)
    return tuple(values)


def _preprocess(word: str, language_key: str) -> tuple[str, list[str]]:
    text = unicodedata.normalize("NFC", word or "").casefold()
    ambiguities: list[str] = []
    if language_key == "oe":
        text = text.replace("ċ", "ch").replace("ġ", "j")
        text = text.replace("þ", "th").replace("ð", "th").replace("ƿ", "w")
        text = text.replace("ȝ", "gh")
    elif language_key == "oi":
        # Digraphs are preserved as their written consonant values.  Lenition
        # is not reversed and therefore cannot silently create a root.
        pass
    else:
        if "ȝ" in text:
            ambiguities.append("ȝ له قيم وسطى متعددة؛ حُفظ gh للاسترجاع ولم يصدر به حكم")
        text = text.replace("þ", "th").replace("ð", "th").replace("ȝ", "gh")
        if re.search(r"c(?=[eiy])", text):
            ambiguities.append("c قبل e/i/y محتملة اللين؛ طيها الكتابي k لا يمنح حكما")
    return text, ambiguities


def normalize(word: str, language_key: str) -> Normalized:
    text, ambiguities = _preprocess(word, language_key)
    folded_parts: list[str] = []
    for char in unicodedata.normalize("NFD", text):
        if unicodedata.combining(char):
            continue
        folded_parts.append(char)
    folded = "".join(folded_parts)

    tokens: list[str] = []
    unknown: list[str] = []
    index = 0
    multi = {
        "th": ("th",),
        "dh": ("dh",),
        "ch": (("kh",) if language_key == "oi" else ("ch",)),
        "ph": ("f",),
        "qu": ("k", "w"),
        "kw": ("k", "w"),
        "gh": ("gh",),
    }
    while index < len(folded):
        char = folded[index]
        if char.isdigit() or char in IGNORED or char.isspace():
            index += 1
            continue
        match = next((item for item in sorted(multi, key=len, reverse=True)
                      if folded.startswith(item, index)), None)
        if match:
            tokens.extend(multi[match])
            index += len(match)
            continue
        if char in VOWELS:
            index += 1
            continue
        if char == "c" or char == "q":
            tokens.append("k")
        elif char == "x":
            tokens.extend(("k", "s"))
        elif char in "bdfghjklmnpqrstvwz":
            tokens.append(char)
        else:
            unknown.append(f"{char} (U+{ord(char):04X})")
        index += 1
    return Normalized(tuple(tokens), tuple(sorted(set(unknown))),
                      tuple(ambiguities), folded)


def candidate_dict(hit: CandidateHit) -> dict[str, Any]:
    return {
        "kind": hit.kind,
        "form": hit.form,
        "reading": clean(hit.reading, 240),
        "positions": hit.positions,
        "status": hit.status,
        "rule_ids": list(hit.rule_ids),
        "route_flag": bool(hit.route_flag),
    }


class CandidateScanner:
    def __init__(self) -> None:
        self.inventory = ArabicInventory.load()
        self.rules = compile_network()
        self.root_cache: dict[tuple[str, tuple[str, ...]], tuple[CandidateHit, ...]] = {}
        self.pair_cache: dict[tuple[str, str, str], tuple[CandidateHit, ...]] = {}

    def root_hits(self, tokens: tuple[str, ...], scope: str) -> list[CandidateHit]:
        key = (scope, tokens)
        if key not in self.root_cache:
            if len(tokens) not in (2, 3):
                self.root_cache[key] = ()
            else:
                hits, _ = generate_hits(tokens, scope, self.rules, self.inventory)
                self.root_cache[key] = tuple(
                    hit for hit in hits if hit.kind in ("root", "hollow-root")
                )
        return list(self.root_cache[key])

    def nucleus_hits(self, tokens: tuple[str, ...], scope: str) -> list[CandidateHit]:
        unique: dict[tuple[Any, ...], CandidateHit] = {}
        for left in range(len(tokens)):
            for right in range(left + 1, len(tokens)):
                pair = (tokens[left], tokens[right])
                key = (scope, *pair)
                if key not in self.pair_cache:
                    hits, _ = generate_hits(pair, scope, self.rules, self.inventory)
                    self.pair_cache[key] = tuple(hit for hit in hits if hit.kind == "nucleus")
                for hit in self.pair_cache[key]:
                    positioned = replace(hit, positions=f"{left + 1}-{right + 1}")
                    identity = (
                        positioned.form,
                        positioned.status,
                        positioned.rule_ids,
                        positioned.positions,
                    )
                    unique.setdefault(identity, positioned)
        rank = {"licensed": 0, "manual-condition": 1, "scope-gap": 2}
        return sorted(unique.values(), key=lambda hit: (
            rank.get(hit.status, 9), hit.form, hit.positions, hit.rule_ids
        ))


def scan_summary(hits: list[CandidateHit], limit: int = 8) -> dict[str, Any]:
    counts = Counter(hit.status for hit in hits)
    return {
        "candidate_count": len(hits),
        "licensed_count": counts["licensed"],
        "manual_condition_count": counts["manual-condition"],
        "scope_gap_count": counts["scope-gap"],
        "candidates": [candidate_dict(hit) for hit in hits[:limit]],
        "truncated": max(0, len(hits) - limit),
    }


def old_coverage_ids() -> set[str]:
    if not COVERAGE_PATH.exists():
        return set()
    result: set[str] = set()
    with COVERAGE_PATH.open("r", encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            member_id = clean(row.get("member_id"))
            if member_id:
                result.add(member_id)
    return result


def reading_judgments(spec: SourceSpec, reopened: set[str]) -> dict[str, str]:
    if not spec.reading_path.exists():
        return {}
    text = spec.reading_path.read_text(encoding="utf-8")
    judgments: dict[str, str] = {}
    for block in CARD_RE.findall(text):
        identity = IDENTITY_RE.search(block)
        judgment = JUDGMENT_RE.search(block)
        if not identity or not judgment:
            continue
        member_id = identity.group(1).strip().rstrip(".")
        value = judgment.group(1).strip().rstrip(".")
        month_issued = "<!-- LANE-D-MONTH-ISSUED -->" in block
        if month_issued:
            missing = [field for field in ISSUED_CARD_FIELDS if field not in block]
            if missing:
                raise RuntimeError(
                    f"{spec.key}: generated card {member_id} lacks complete contract: "
                    + ", ".join(missing)
                )
        if (member_id not in reopened or month_issued) and not value.startswith("(لا حكم"):
            judgments[member_id] = value

    # The direction appendices are keyed tables.  Their rows supersede the
    # older generic LOANWORD label, but the member identity remains the same.
    if "SEMITIC-SOURCE-TRANSMISSION" in text:
        semitic_start = text.find("### من السامية إلى")
        third_start = text.find("### من طرف ثالث إلى", semitic_start + 1)
        if semitic_start >= 0:
            semitic_text = text[semitic_start: third_start if third_start >= 0 else None]
            for member_id in TABLE_ID_RE.findall(semitic_text):
                member_id = member_id.strip()
                if member_id not in reopened:
                    judgments[member_id] = "SEMITIC-SOURCE-TRANSMISSION"
    return judgments


def is_semitic_transmission(etymology: str) -> tuple[bool, str]:
    text = clean(etymology)
    if not text or not SEMITIC_MARKER_RE.search(text):
        return False, ""
    if SPECULATIVE_RE.search(text) and not re.search(r"\bfrom\s+(?:Arabic|Hebrew|Aramaic|Phoenician|Akkadian)\b", text, re.I):
        return False, "SPECULATIVE-SEMITIC-SOURCE"
    if SEMITIC_DIRECTION_RE.search(text) or SEMITIC_ORIGIN_RE.search(text):
        explicit_source = re.search(
            r"(?:borrowed\s+from|from|via|calque\s+of|alteration\s+of|"
            r"modification\s+of|derived\s+from|deriving\s+from|ultimately\s+from)\s+"
            r"(?:Andalusian\s+Arabic|dialectal\s+Arabic|Arabic|Biblical\s+Hebrew|"
            r"Hebrew|Aramaic|Syriac|Phoenician|Punic|Akkadian|a\s+Semitic\s+language|Semitic)",
            text,
            re.I,
        ) or SEMITIC_ORIGIN_RE.search(text)
        subtype = "SEMITIC-SOURCE" if explicit_source else "SEMITIC-INFLUENCE"
        return True, subtype
    return False, "SEMITIC-BACKGROUND-ONLY"


def extraction_for_name(etymology: str) -> str:
    text = clean(etymology, 1_200)
    if not text:
        return ""
    match = re.search(r"(?:from|deriving from|derived from)\s+(.+)", text, re.I)
    return clean(match.group(1) if match else text, 600)


def status_for_member(
    *,
    spec: SourceSpec,
    entry: dict[str, Any],
    sense: dict[str, Any],
    normalized: Normalized,
    root_scan: dict[str, Any],
    nucleus_scan: dict[str, Any],
    semitic_note: str,
) -> tuple[str, str]:
    targets = relation_targets(sense)
    etymology = clean(entry.get("etymology_text"))
    pos = clean(entry.get("pos"))
    if pos == "name":
        extracted = extraction_for_name(etymology)
        if extracted:
            return "NAME-ROOT-OPEN", f"العلم لم يستبعد؛ استخرج أصله المنشور: {extracted}"
        return "NAME-ROOT-SOURCE-GAP", "العلم لم يستبعد؛ يحتاج أصلا منشورا مسمى"
    if targets:
        return "FORM-LINKED-OPEN", (
            "إحالة صرفية أو بديلة إلى " + ", ".join(targets)
            + "؛ لا إغلاق حتى يحمل الأصل حكما صالحا لهذا العضو"
        )
    if normalized.unknown:
        return "NORMALIZATION-GAP", "رموز غير مطبعة: " + ", ".join(normalized.unknown)
    if semitic_note:
        return "TRANSMISSION-SOURCE-GAP", semitic_note
    root_count = root_scan["candidate_count"]
    nucleus_count = nucleus_scan["candidate_count"]
    if root_count or nucleus_count:
        return "OPEN-CANDIDATE", (
            "مرشحات صوتية فقط؛ يلزم فحص المعنى ومروحة مصدرين عربيين قديمين "
            "والمصفاة والعدستان قبل أي حكم"
        )
    if len(normalized.tokens) > 3:
        return "MORPHOLOGY-GAP", (
            "فحص النواة اكتمل صفريا على السطح؛ الجذر يحتاج تعرية صرفية منشورة "
            "ولا يصدر NO-TRACE"
        )
    return "SOUND-SCAN-ZERO-OPEN", (
        "اكتمل الاسترجاع السطحي للجذر والنواة بلا مرشح؛ لم تكتمل بوابة المعنى "
        "والخلف والمصفاة، فلا يصدر NO-TRACE"
    )


def iter_records(spec: SourceSpec) -> Iterable[tuple[int, dict[str, Any] | None, str | None]]:
    with spec.source_path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            try:
                yield line_no, json.loads(line), None
            except json.JSONDecodeError as error:
                yield line_no, None, f"JSON-DECODE: {error.msg} at column {error.colno}"


def scan_source(
    spec: SourceSpec,
    scanner: CandidateScanner,
    judgments: dict[str, str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    before_hash = digest(spec.source_path)
    before_stat = spec.source_path.stat()
    if before_hash != spec.expected_sha256 or before_stat.st_size != spec.expected_bytes:
        raise RuntimeError(f"{spec.key}: source pin mismatch before scan")

    coverage: list[dict[str, Any]] = []
    units: list[dict[str, Any]] = []
    members = records = 0
    bad_lines: list[int] = []
    status_counts: Counter[str] = Counter()
    root_candidate_members = nucleus_candidate_members = both_candidate_members = 0
    semitic_members = 0
    sequence = 0

    for line_no, entry, error in iter_records(spec):
        if error:
            bad_lines.append(line_no)
            sequence += 1
            unit_id = f"SOURCE-LINE-L{line_no}"
            row = {
                "schema": "lane-d-coverage-v2",
                "member_id": unit_id,
                "unit_type": "source-gap",
                "language": spec.language,
                "source_line": line_no,
                "sense_index": 0,
                "form": "(سطر مصدر غير قابل للتحليل)",
                "part_of_speech": "",
                "branch_meaning": error,
                "normalized_skeleton": "",
                "normalization_ambiguities": [],
                "root_scan": scan_summary([]),
                "nucleus_scan": scan_summary([]),
                "transmission": {"status": "SOURCE-GAP", "source": ""},
                "chronology_bridge": "",
                "non_issuance_status": "SOURCE-GAP",
                "non_issuance_reason": error,
                "batch_number": (sequence - 1) // BATCH_SIZE + 1,
            }
            coverage.append(row)
            units.append({
                "sequence": sequence,
                "member_id": unit_id,
                "line": line_no,
                "judgment": "",
                "coverage": True,
                "root_candidates": False,
                "nucleus_candidates": False,
                "status": "SOURCE-GAP",
            })
            status_counts["SOURCE-GAP"] += 1
            continue

        assert entry is not None
        records += 1
        word = clean(entry.get("word") or "(بلا لمة)")
        normalized = normalize(word, spec.key)
        root_hits = scanner.root_hits(normalized.tokens, spec.scope) if not normalized.unknown else []
        nucleus_hits = scanner.nucleus_hits(normalized.tokens, spec.scope) if not normalized.unknown else []
        root_scan = scan_summary(root_hits)
        nucleus_scan = scan_summary(nucleus_hits)
        etymology = clean(entry.get("etymology_text"), 1_500)
        semitic, semitic_note = is_semitic_transmission(etymology)
        transmission = {
            "status": "SEMITIC-SOURCE-TRANSMISSION" if semitic else (
                "THIRD-PARTY-DIRECTION-OPEN" if THIRD_PARTY_RE.search(etymology) else "NO-DIRECTION-ISSUED"
            ),
            "subtype": semitic_note if semitic else "",
            "source": etymology if semitic else "",
        }

        for sense_index, sense in enumerate(entry.get("senses") or [], 1):
            members += 1
            sequence += 1
            sense_id = clean(sense.get("id")) or f"NO-SENSE-ID-L{line_no}S{sense_index}"
            member_id = f"{sense_id}@L{line_no}S{sense_index}"
            issued = judgments.get(member_id, "")
            if spec.key == "me" and semitic:
                issued = "SEMITIC-SOURCE-TRANSMISSION"
            if issued:
                semitic_members += int(issued == "SEMITIC-SOURCE-TRANSMISSION")
                units.append({
                    "sequence": sequence,
                    "member_id": member_id,
                    "line": line_no,
                    "judgment": issued,
                    "coverage": False,
                    "root_candidates": bool(root_hits),
                    "nucleus_candidates": bool(nucleus_hits),
                    "status": "ISSUED",
                    "form": word,
                    "part_of_speech": clean(entry.get("pos")),
                    "branch_meaning": sense_gloss(sense),
                    "etymology": etymology,
                    "transmission_subtype": semitic_note if semitic else "",
                    "normalized_skeleton": normalized.skeleton,
                    "root_scan": root_scan,
                    "nucleus_scan": nucleus_scan,
                })
                continue

            status, reason = status_for_member(
                spec=spec,
                entry=entry,
                sense=sense,
                normalized=normalized,
                root_scan=root_scan,
                nucleus_scan=nucleus_scan,
                semitic_note=semitic_note,
            )
            root_candidate_members += int(bool(root_hits))
            nucleus_candidate_members += int(bool(nucleus_hits))
            both_candidate_members += int(bool(root_hits) and bool(nucleus_hits))
            status_counts[status] += 1
            bridge = ""
            if spec.key == "me" and re.search(r"\b(?:from|inherited from) Old English\b", etymology, re.I):
                bridge = clean(etymology, 700)
            row = {
                "schema": "lane-d-coverage-v2",
                "member_id": member_id,
                "unit_type": "member",
                "language": spec.language,
                "source_line": line_no,
                "sense_index": sense_index,
                "form": word,
                "part_of_speech": clean(entry.get("pos")),
                "branch_meaning": sense_gloss(sense),
                "normalized_skeleton": normalized.skeleton,
                "normalization_ambiguities": list(normalized.ambiguities),
                "root_scan": root_scan,
                "nucleus_scan": nucleus_scan,
                "transmission": transmission,
                "chronology_bridge": bridge,
                "name_root_extraction": extraction_for_name(etymology) if clean(entry.get("pos")) == "name" else "",
                "non_issuance_status": status,
                "non_issuance_reason": (
                    f"النوع={status}؛ فحص الجذر={root_scan['candidate_count']} مرشح؛ "
                    f"فحص النواة={nucleus_scan['candidate_count']} مرشح؛ {reason}"
                ),
                "batch_number": (sequence - 1) // BATCH_SIZE + 1,
            }
            coverage.append(row)
            units.append({
                "sequence": sequence,
                "member_id": member_id,
                "line": line_no,
                "judgment": "",
                "coverage": True,
                "root_candidates": bool(root_hits),
                "nucleus_candidates": bool(nucleus_hits),
                "status": status,
            })

    after_hash = digest(spec.source_path)
    after_stat = spec.source_path.stat()
    if before_hash != after_hash or before_stat.st_size != after_stat.st_size or before_stat.st_mtime_ns != after_stat.st_mtime_ns:
        raise RuntimeError(f"{spec.key}: source changed during scan")
    if records != spec.expected_records or members != spec.expected_members:
        raise RuntimeError(
            f"{spec.key}: counts records={records}/{spec.expected_records}, members={members}/{spec.expected_members}"
        )
    if tuple(bad_lines) != spec.expected_bad_lines:
        raise RuntimeError(f"{spec.key}: bad lines {bad_lines} != {spec.expected_bad_lines}")
    expected_units = members + len(bad_lines)
    if len(units) != expected_units:
        raise RuntimeError(f"{spec.key}: unit coverage mismatch")

    judgment_counts = Counter(unit["judgment"] for unit in units if unit["judgment"])
    positive = sum(count for judgment, count in judgment_counts.items() if POSITIVE_RE.match(judgment))
    closures = sum(count for judgment, count in judgment_counts.items() if FINAL_CLOSURE_RE.match(judgment))
    chronology_bridges = judgment_counts["CHRONOLOGY-BRIDGE-OLD"]
    summary = {
        "key": spec.key,
        "language": spec.language,
        "language_ar": spec.language_ar,
        "snapshot": spec.pin,
        "source_path": spec.source_path.relative_to(ROOT).as_posix(),
        "sha256": before_hash,
        "bytes": before_stat.st_size,
        "records": records,
        "members": members,
        "source_gaps": len(bad_lines),
        "inventory_units": len(units),
        "issued_members": sum(bool(unit["judgment"]) for unit in units),
        "coverage_rows": len(coverage),
        "registered_units": len(coverage) + sum(bool(unit["judgment"]) for unit in units),
        "remaining_inventory": 0,
        "root_candidate_members_in_coverage": root_candidate_members,
        "nucleus_candidate_members_in_coverage": nucleus_candidate_members,
        "both_candidate_members_in_coverage": both_candidate_members,
        "positive": positive,
        "closures": closures,
        "chronology_bridges": chronology_bridges,
        "semitic_source_transmissions": semitic_members,
        "judgments": dict(sorted(judgment_counts.items())),
        "coverage_statuses": dict(sorted(status_counts.items())),
    }
    return coverage, units, summary


def batch_minutes(spec: SourceSpec, units: list[dict[str, Any]]) -> str:
    sections: list[str] = []
    total = len(units)
    for offset in range(0, total, BATCH_SIZE):
        batch = units[offset: offset + BATCH_SIZE]
        number = offset // BATCH_SIZE + 1
        positives = sum(
            bool(POSITIVE_RE.match(unit["judgment"])) for unit in batch if unit["judgment"]
        )
        closures = sum(
            bool(FINAL_CLOSURE_RE.match(unit["judgment"])) for unit in batch if unit["judgment"]
        )
        transmissions = sum(
            unit["judgment"] == "SEMITIC-SOURCE-TRANSMISSION" for unit in batch
        )
        root_candidates = sum(unit["root_candidates"] for unit in batch)
        nucleus_candidates = sum(unit["nucleus_candidates"] for unit in batch)
        coverage_rows = sum(unit["coverage"] for unit in batch)
        remaining = total - batch[-1]["sequence"]
        sections.append(
            f"## {spec.language_ar}: الدفعة {number:03d}\n\n"
            f"- محضر: فُحصت الوحدات {batch[0]['sequence']} إلى {batch[-1]['sequence']} "
            f"بالجذر والنواة معا؛ أعضاء مرشحي الجذر={root_candidates}؛ "
            f"أعضاء مرشحي النواة={nucleus_candidates}؛ أسطر التغطية={coverage_rows}.\n"
            f"- الرقم الأول، الصلات الموجبة: {positives}.\n"
            f"- الرقم الثاني، الإغلاقات النهائية: {closures}.\n"
            f"- عدد مستقل لا يضاف إليهما، انتقالات `SEMITIC-SOURCE-TRANSMISSION`: {transmissions}.\n"
            f"- سطر الموضع: بدأت عند `{batch[0]['member_id']}` في سطر المصدر "
            f"{batch[0]['line']}، وانتهت عند `{batch[-1]['member_id']}` في سطر المصدر "
            f"{batch[-1]['line']}؛ بقي في الجرد: {remaining}.\n"
        )
    return "\n".join(sections)


def verify_partition(
    specs: tuple[SourceSpec, ...],
    all_units: dict[str, list[dict[str, Any]]],
    coverage: list[dict[str, Any]],
) -> dict[str, Any]:
    coverage_ids = [row["member_id"] for row in coverage]
    if len(coverage_ids) != len(set((row["language"], row["member_id"]) for row in coverage)):
        # Sense identifiers may repeat within a source; composite identifiers
        # include line and sense and therefore must be unique per language.
        raise RuntimeError("duplicate coverage identity")
    checks: dict[str, Any] = {}
    for spec in specs:
        units = all_units[spec.key]
        judged = {unit["member_id"] for unit in units if unit["judgment"]}
        covered = {
            row["member_id"] for row in coverage if row["language"] == spec.language
        }
        expected = {unit["member_id"] for unit in units}
        if judged & covered or judged | covered != expected:
            raise RuntimeError(f"{spec.key}: judgment/coverage partition failed")
        checks[spec.key] = {
            "expected_units": len(expected),
            "judged_units": len(judged),
            "coverage_units": len(covered),
            "overlap": len(judged & covered),
            "missing": len(expected - judged - covered),
            "complete": True,
        }
    return checks


def write_outputs(
    coverage: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
    all_units: dict[str, list[dict[str, Any]]],
    batch_text: str,
) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    partition = verify_partition(SOURCES, all_units, coverage)
    coverage_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in coverage
    )
    issued_scans: list[dict[str, Any]] = []
    for spec in SOURCES:
        for unit in all_units[spec.key]:
            if not unit["judgment"]:
                continue
            issued_scans.append({
                "schema": "lane-d-issued-layer-scan-v1",
                "language": spec.language,
                "member_id": unit["member_id"],
                "source_line": unit["line"],
                "form": unit.get("form", ""),
                "part_of_speech": unit.get("part_of_speech", ""),
                "branch_meaning": unit.get("branch_meaning", ""),
                "etymology_text": unit.get("etymology", ""),
                "name_root_extraction": (
                    extraction_for_name(unit.get("etymology", ""))
                    if unit.get("part_of_speech") == "name" else ""
                ),
                "judgment": unit["judgment"],
                "normalized_skeleton": unit.get("normalized_skeleton", ""),
                "root_scan": unit.get("root_scan", scan_summary([])),
                "nucleus_scan": unit.get("nucleus_scan", scan_summary([])),
            })
    issued_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in issued_scans
    )
    me_transmissions = [
        {
            "schema": "lane-d-middle-english-transmission-v1",
            "member_id": unit["member_id"],
            "source_line": unit["line"],
            "form": unit.get("form", ""),
            "part_of_speech": unit.get("part_of_speech", ""),
            "branch_meaning": unit.get("branch_meaning", ""),
            "judgment": unit["judgment"],
            "subtype": unit.get("transmission_subtype", ""),
            "etymology_text": unit.get("etymology", ""),
            "name_root_extraction": (
                extraction_for_name(unit.get("etymology", ""))
                if unit.get("part_of_speech") == "name" else ""
            ),
        }
        for unit in all_units["me"]
        if unit["judgment"] == "SEMITIC-SOURCE-TRANSMISSION"
    ]
    me_transmissions_text = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
        for row in me_transmissions
    )
    COVERAGE_PATH.write_text(coverage_text, encoding="utf-8", newline="\n")
    ISSUED_SCANS_PATH.write_text(issued_text, encoding="utf-8", newline="\n")
    ME_TRANSMISSIONS_PATH.write_text(
        me_transmissions_text, encoding="utf-8", newline="\n"
    )
    BATCH_AUDIT_PATH.write_text(
        "# المسار د: محاضر شهر الطبقتين\n\n"
        "كل دفعة تقرأ الجذر والنواة معا. الرقمان مفصولان ولا يجمعان، "
        "والانتقالات السامية عدد مستقل. لا يصدر حكم من هذا السجل الآلي.\n\n"
        + batch_text,
        encoding="utf-8",
        newline="\n",
    )
    manifest = {
        "schema": "lane-d-month-scan-v1",
        "generated_utc": datetime.now(tz=UTC).isoformat(),
        "batch_size": BATCH_SIZE,
        "coverage_path": COVERAGE_PATH.relative_to(ROOT).as_posix(),
        "coverage_sha256": hashlib.sha256(coverage_text.encode("utf-8")).hexdigest(),
        "coverage_rows": len(coverage),
        "issued_layer_scans_path": ISSUED_SCANS_PATH.relative_to(ROOT).as_posix(),
        "issued_layer_scans_sha256": hashlib.sha256(issued_text.encode("utf-8")).hexdigest(),
        "issued_layer_scans_rows": len(issued_scans),
        "middle_english_transmissions_path": ME_TRANSMISSIONS_PATH.relative_to(ROOT).as_posix(),
        "middle_english_transmissions_sha256": hashlib.sha256(
            me_transmissions_text.encode("utf-8")
        ).hexdigest(),
        "middle_english_transmissions_rows": len(me_transmissions),
        "batch_audit_path": BATCH_AUDIT_PATH.relative_to(ROOT).as_posix(),
        "proof_line_touched": False,
        "shared_rebuild_run": False,
        "partition": partition,
        "languages": summaries,
    }
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Scan and verify without writing outputs.")
    parser.add_argument(
        "--card-template",
        action="store_true",
        help="Print the complete Lane D issued-card contract and exit.",
    )
    args = parser.parse_args()

    if args.card_template:
        print("### بطاقة: <اللمة> «<معنى العضو>»")
        print("<!-- LANE-D-MONTH-ISSUED -->")
        print("\n".join(ISSUED_CARD_FIELDS))
        return 0

    reopened = old_coverage_ids()
    judgments = {
        spec.key: reading_judgments(spec, reopened) for spec in SOURCES
    }
    scanner = CandidateScanner()
    all_coverage: list[dict[str, Any]] = []
    all_units: dict[str, list[dict[str, Any]]] = {}
    summaries: list[dict[str, Any]] = []
    batch_parts: list[str] = []
    for spec in SOURCES:
        coverage, units, summary = scan_source(spec, scanner, judgments[spec.key])
        all_coverage.extend(coverage)
        all_units[spec.key] = units
        summaries.append(summary)
        batch_parts.append(batch_minutes(spec, units))
    partition = verify_partition(SOURCES, all_units, all_coverage)
    if not args.check:
        write_outputs(all_coverage, summaries, all_units, "\n".join(batch_parts))
    print(json.dumps({
        "check_only": args.check,
        "partition": partition,
        "coverage_rows": len(all_coverage),
        "languages": summaries,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
