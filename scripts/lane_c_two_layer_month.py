#!/usr/bin/env python3
"""Lane C's section-28 two-layer month.

This is a lane-owned, append-oriented reader.  It never rebuilds a shared
inventory and never writes to the frozen proof line, shift network, Arabic
root inventory, or nucleus index.  It reads every source member, including
forms, alternatives, function words, affixes, characters, romanizations, and
proper names.  Root/hollow-root retrieval and nucleus retrieval are executed
independently for every member; neither layer is a fallback for the other.

Members that already have a prose verdict retain it.  Members without a
verdict retain or receive exactly one row in lane_c_coverage.jsonl.  The
separate names inventory remains the root-extraction record required by
section 26.  Each committed batch appends a compact receipt to the language
reading and to a lane-C audit; no prose card is created for an unissued
judgment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import lane_c_ie_discovery as discovery
import lane_c_ie_week2_coverage as week2
from lane_c_section27_direction import (
    CLASS_NO_DIRECTION,
    CLASS_SEMITIC,
    CLASS_THIRD,
    CLASS_TO_ARABIC,
    LANGUAGES as DIRECTION_LANGUAGES,
    TAG_SEMITIC,
    TAG_THIRD,
    TAG_TO_ARABIC,
    direction_decision,
)
from recovery_pipeline.candidates import ArabicInventory, CandidateHit, generate_hits
from recovery_pipeline.network import compile_network


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
READINGS = ROOT / "04-cross-linguistic" / "readings"
DATA = ROOT / "04-cross-linguistic" / "data"
COVERAGE = DATA / "lane_c_coverage.jsonl"
NAMES = DATA / "lane_c_names_inventory.jsonl"
PROGRESS = DATA / "lane_c_two_layer_progress.json"
REVIEW = DATA / "lane_c_two_layer_review.tsv"
PROMOTIONS = DATA / "lane_c_two_layer_promotions.jsonl"
RETRACTIONS = DATA / "lane_c_two_layer_retractions.jsonl"
SEMANTIC_PROMOTIONS = DATA / "lane_c_two_layer_semantic_promotions.jsonl"
AUTHOR_QUESTIONS = DATA / "lane_c_two_layer_author_questions.jsonl"
ROUTE_FLAGS = DATA / "lane_c_two_layer_route_flags.jsonl"
AUDIT = ROOT / "05-audits" / "lane-c-2026-08-01-two-layer-month.md"
CORE = ROOT / "data" / "juthoor-core-levels.json"
NETWORK = ROOT / "04-cross-linguistic" / "shift-network-draft.md"
DATE = "2026-08-01"
SCHEMA = "lane-c-two-layer-month-v1"
MARKER = f"LANE-C-TWO-LAYER-{DATE}"

COVERAGE_FIELDS = (
    "member_id",
    "language",
    "form",
    "branch_meaning",
    "non_issuance_reason",
    "batch_number",
)
NAME_POS = {"name", "proper noun"}
FUNCTION_POS = {
    "article",
    "conj",
    "conjunction",
    "det",
    "determiner",
    "intj",
    "num",
    "numeral",
    "particle",
    "postp",
    "prep",
    "pron",
    "pronoun",
}
NONLEXICAL_POS = {
    "abbrev",
    "character",
    "circumfix",
    "contraction",
    "infix",
    "interfix",
    "letter",
    "phrase",
    "prefix",
    "proverb",
    "punct",
    "romanization",
    "suffix",
    "symbol",
}
ENTRY_RE = re.compile(
    r"(?:kaikki_[^:`\s]+(?::\d{4}_\d{2}_\d{2})?|kaikki_[^:`\s]+):"
    r"\d+:[^`\s\]]+"
)
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z-]+")


@dataclass(frozen=True)
class Language:
    key: str
    reading_file: str
    db_path: str
    source_label: str


LANGUAGES = tuple(
    Language(item.key, item.reading_file, item.db_path, item.source_label)
    for item in week2.LANGUAGES
)
LANGUAGE_BY_KEY = {item.key: item for item in LANGUAGES}
DIRECTION_BY_KEY = {item.key: item for item in DIRECTION_LANGUAGES}


def nfc(value: str | None) -> str:
    return unicodedata.normalize("NFC", value or "")


def compact(value: str | None, limit: int = 360) -> str:
    text = re.sub(r"\s+", " ", nfc(value)).strip()
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ro_connection(relative: str) -> sqlite3.Connection:
    path = (ROOT / relative).resolve()
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def source_ordinal(entry_id: str) -> int:
    match = re.search(r":(\d+):", entry_id)
    return int(match.group(1)) if match else 2**63 - 1


def load_first_field_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    pattern = re.compile(br'^\{"member_id":"([^"]+)"')
    result: set[str] = set()
    with path.open("rb") as handle:
        for line_number, line in enumerate(handle, 1):
            match = pattern.match(line)
            if not match:
                raise RuntimeError(f"{path}:{line_number}: malformed first field")
            entry_id = match.group(1).decode("utf-8")
            if entry_id in result:
                raise RuntimeError(f"{path}:{line_number}: duplicate {entry_id}")
            result.add(entry_id)
    return result


def load_card_ids() -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for language in LANGUAGES:
        ids: set[str] = set()
        path = READINGS / language.reading_file
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.startswith("- الكلمةُ في الفرع:"):
                    ids.update(ENTRY_RE.findall(line))
        result[language.key] = ids
    if RETRACTIONS.exists():
        with RETRACTIONS.open(encoding="utf-8") as handle:
            for line in handle:
                row = json.loads(line)
                result.get(str(row["language"]), set()).discard(
                    nfc(str(row["member_id"]))
                )
    return result


def load_names_by_language() -> dict[str, set[str]]:
    by_language: dict[str, set[str]] = defaultdict(set)
    with NAMES.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            row = json.loads(line)
            entry_id = nfc(str(row["member_id"]))
            language = str(row["language"])
            if entry_id in by_language[language]:
                raise RuntimeError(f"{NAMES}:{line_number}: duplicate {entry_id}")
            by_language[language].add(entry_id)
    return dict(by_language)


def core_rows() -> dict[str, dict[str, Any]]:
    payload = json.loads(CORE.read_text(encoding="utf-8"))
    output: dict[str, dict[str, Any]] = {}
    hamza = {"أ": "ء", "إ": "ء", "آ": "ء"}
    for row in payload["levels"]["level_2_binary_nuclei"]["nuclei"]:
        key = "".join(
            hamza.get(char, char)
            for char in row["nucleus"].replace("-", "").replace(" ", "")
        )
        # Mirror ArabicInventory.load(): orthographic hamza variants may
        # collapse to one retrieval key, and the later frozen row is the
        # operative reading for that normalized key.
        output[key] = row
    return output


def nucleus_sample_roots() -> dict[str, tuple[str, ...]]:
    path = ROOT / "03-scholar-extracts" / "jabal-nuclei-catalog.md"
    output: dict[str, tuple[str, ...]] = {}
    hamza = str.maketrans({"أ": "ء", "إ": "ء", "آ": "ء"})
    row_re = re.compile(r"^\| \*\*(?P<nucleus>[^*]+)\*\*.*\|\s*\d+\s*\|\s*(?P<roots>[^|]+?)\s*\|\s*$")
    for line in path.read_text(encoding="utf-8").splitlines():
        match = row_re.match(line)
        if not match:
            continue
        nucleus = re.sub(r"[^ء-ي]", "", match.group("nucleus")).translate(hamza)
        roots = []
        for item in re.split(r"[،,]", match.group("roots")):
            root = re.sub(r"[^ء-ي]", "", item).translate(hamza)
            if root:
                roots.append(root)
        output[nucleus] = tuple(dict.fromkeys(roots))
    return output


def validate_frozen_nuclei(inventory: ArabicInventory, core: dict[str, dict[str, Any]]) -> None:
    if set(inventory.nuclei) != set(core):
        missing = sorted(set(core) - set(inventory.nuclei))
        extra = sorted(set(inventory.nuclei) - set(core))
        raise RuntimeError(f"nucleus inventory drift: missing={missing}; extra={extra}")
    for form, reading in inventory.nuclei.items():
        row = core[form]
        expected = row.get("jabal_lexicon_reading_ar") or row.get("composed_reading_ar") or ""
        if reading != expected:
            raise RuntimeError(f"frozen nucleus reading drift for {form}")


def base_progress() -> dict[str, Any]:
    languages: dict[str, Any] = {}
    for language in LANGUAGES:
        con = ro_connection(language.db_path)
        try:
            total = int(
                con.execute(
                    "SELECT count(*) FROM entries indexed by entries_language_status WHERE language=?",
                    (language.key,),
                ).fetchone()[0]
            )
        finally:
            con.close()
        languages[language.key] = {
            "total": total,
            "processed": 0,
            "last_rowid": 0,
            "last_member_id": "",
            "batches": 0,
            "positive": 0,
            "closures": 0,
            "transmissions": 0,
            "promotions": 0,
            "promotions_finalized": False,
            "promotion_rows_removed": 0,
            "coverage_added": 0,
            "names_seen": 0,
            "root_candidate_members": 0,
            "nucleus_candidate_members": 0,
        }
    return {
        "schema": SCHEMA,
        "date": DATE,
        "contract": {
            "root_and_nucleus": "parallel_per_member_never_fallback",
            "core_index": "data/juthoor-core-levels.json read-only",
            "proof_line": "frozen",
            "shared_builders": "not invoked",
            "coverage": "cards union lane_c_coverage plus names inventory",
        },
        "pins": {
            "core_sha256": sha256(CORE),
            "network_sha256": sha256(NETWORK),
            "databases": {
                language.key: {
                    "path": language.db_path,
                    "bytes": (ROOT / language.db_path).stat().st_size,
                }
                for language in LANGUAGES
            },
        },
        "languages": languages,
    }


def load_progress(create: bool = False) -> dict[str, Any]:
    if not PROGRESS.exists():
        return base_progress()
    payload = json.loads(PROGRESS.read_text(encoding="utf-8"))
    if payload.get("schema") != SCHEMA:
        raise RuntimeError(f"unexpected progress schema: {payload.get('schema')}")
    expected = base_progress()
    if payload["pins"] != expected["pins"]:
        raise RuntimeError("pinned nucleus/network/database inputs changed")
    for key in LANGUAGE_BY_KEY:
        if payload["languages"][key]["total"] != expected["languages"][key]["total"]:
            raise RuntimeError(f"source denominator changed for {key}")
    return payload


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def tokens_for(row: sqlite3.Row) -> tuple[str, ...]:
    try:
        tokens = tuple(json.loads(row["tokens_json"] or "[]"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"{row['entry_id']}: malformed tokens_json") from error
    return tuple(nfc(str(token)) for token in tokens if token)


class TwoLayerRetriever:
    def __init__(self) -> None:
        self.inventory = ArabicInventory.load(ROOT)
        self.core = core_rows()
        validate_frozen_nuclei(self.inventory, self.core)
        self.rules = compile_network(NETWORK)

    @lru_cache(maxsize=None)
    def pair(self, language: str, left: str, right: str) -> tuple[CandidateHit, ...]:
        hits, unmapped = generate_hits((left, right), language, self.rules, self.inventory)
        if unmapped:
            return ()
        return tuple(
            hit
            for hit in hits
            if hit.status == "licensed" and not hit.route_flag
        )

    @lru_cache(maxsize=None)
    def triple(self, language: str, tokens: tuple[str, ...]) -> tuple[CandidateHit, ...]:
        hits, unmapped = generate_hits(tokens, language, self.rules, self.inventory)
        if unmapped:
            return ()
        return tuple(
            hit
            for hit in hits
            if hit.status == "licensed" and not hit.route_flag
        )

    def layers(self, language: str, tokens: tuple[str, ...]) -> tuple[list[CandidateHit], list[CandidateHit]]:
        # One Arabic form is one retrieval candidate here.  When the frozen
        # network offers several licensed routes to it, retain the shortest
        # named route for display without inflating the candidate count.
        root_hits: dict[str, CandidateHit] = {}
        nucleus_hits: dict[str, CandidateHit] = {}

        def retain(bucket: dict[str, CandidateHit], hit: CandidateHit) -> None:
            old = bucket.get(hit.form)
            if old is None or (len(hit.rule_ids), hit.rule_ids) < (
                len(old.rule_ids),
                old.rule_ids,
            ):
                bucket[hit.form] = hit

        if len(tokens) == 3:
            for hit in self.triple(language, tokens):
                if hit.kind == "root":
                    retain(root_hits, hit)
        if len(tokens) == 2:
            for hit in self.pair(language, tokens[0], tokens[1]):
                if hit.kind == "hollow-root":
                    retain(root_hits, hit)
        for left in range(len(tokens)):
            for right in range(left + 1, len(tokens)):
                for hit in self.pair(language, tokens[left], tokens[right]):
                    if hit.kind != "nucleus":
                        continue
                    retain(nucleus_hits, hit)
        roots = sorted(root_hits.values(), key=lambda item: (item.form, item.rule_ids))
        nuclei = sorted(nucleus_hits.values(), key=lambda item: (item.form, item.rule_ids))
        return roots, nuclei


def stem(token: str) -> str:
    word = token.casefold().strip("-")
    for suffix in ("ization", "ation", "ingly", "edly", "ment", "ness", "ing", "ied", "ies", "ed", "es", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            if suffix in {"ied", "ies"}:
                return word[: -len(suffix)] + "y"
            return word[: -len(suffix)]
    return word


def semantic_tokens(text: str) -> set[str]:
    return {
        stem(token)
        for token in TOKEN_RE.findall(text)
        if token.casefold() not in discovery.ENGLISH_STOP_WORDS
    }


def overlap_score(left: str, right: str) -> float:
    a = semantic_tokens(left)
    b = semantic_tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / math.sqrt(len(a) * len(b))


def overlap_sets(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / math.sqrt(len(a) * len(b))


class SemanticReview:
    def __init__(self, core: dict[str, dict[str, Any]]) -> None:
        self.definitions = discovery.load_arabic_english_definitions()
        self.source_counts = discovery.load_classical_source_counts()
        self.sample_roots = nucleus_sample_roots()
        self.core = core
        self.definition_tokens = {
            root: semantic_tokens(text) for root, text in self.definitions.items()
        }
        self.source_names = {
            root: tuple(sorted(counts))
            for root, counts in self.source_counts.items()
        }
        self.core_tokens = {
            nucleus: semantic_tokens(nfc(row.get("composed_reading_en")))
            for nucleus, row in core.items()
        }
        self.support = {
            nucleus: tuple(
                (
                    root,
                    self.definition_tokens.get(root, set()),
                    self.source_names.get(root, ()),
                )
                for root in roots
                if len(self.source_names.get(root, ())) >= 2
            )
            for nucleus, roots in self.sample_roots.items()
        }

    def sources(self, root: str) -> tuple[str, ...]:
        return self.source_names.get(root, ())

    def best(self, row: sqlite3.Row, roots: list[CandidateHit], nuclei: list[CandidateHit]) -> list[dict[str, Any]]:
        gloss = nfc(row["gloss"])
        gloss_tokens = semantic_tokens(gloss)
        output: list[dict[str, Any]] = []
        for hit in roots:
            sources = self.sources(hit.form)
            if len(sources) < 2:
                continue
            score = overlap_sets(
                gloss_tokens,
                self.definition_tokens.get(hit.form, set()),
            )
            if score:
                output.append(
                    {
                        "layer": "root",
                        "form": hit.form,
                        "reading": self.definitions.get(hit.form, ""),
                        "support_root": hit.form,
                        "sources": sources,
                        "rules": hit.rule_ids,
                        "score": score,
                    }
                )
        for hit in nuclei:
            core_row = self.core[hit.form]
            core_english = nfc(core_row.get("composed_reading_en"))
            best_root = ""
            best_root_text = ""
            best_root_score = 0.0
            best_sources: tuple[str, ...] = ()
            for root, root_tokens, sources in self.support.get(hit.form, ()):
                text = self.definitions.get(root, "")
                score = overlap_sets(gloss_tokens, root_tokens)
                if score > best_root_score:
                    best_root = root
                    best_root_text = text
                    best_root_score = score
                    best_sources = sources
            core_score = overlap_sets(
                gloss_tokens,
                self.core_tokens.get(hit.form, set()),
            )
            score = max(core_score, best_root_score)
            if score and best_sources:
                output.append(
                    {
                        "layer": "nucleus",
                        "form": hit.form,
                        "reading": nfc(core_row.get("jabal_lexicon_reading_ar")) or nfc(core_row.get("composed_reading_ar")),
                        "support_root": best_root,
                        "support_root_text": best_root_text,
                        "sources": best_sources,
                        "rules": hit.rule_ids,
                        "score": score,
                    }
                )
        output.sort(key=lambda item: (item["score"], item["layer"] == "nucleus"), reverse=True)
        return output[:4]


def fetch_batch(con: sqlite3.Connection, language: str, after_rowid: int, size: int) -> list[sqlite3.Row]:
    return con.execute(
        """
        SELECT rowid AS source_rowid, entry_id, headword, romanization, pos,
               gloss, etymology, source_stratum, source_scope_note, loan_hint,
               form_of, alternative_of, form_targets_json,
               alternative_targets_json, selected_input, skeleton, tokens_json,
               unknown_original_json, unknown_romanization_json,
               processing_status, morphology_status
        FROM entries
        WHERE language = ? AND rowid > ?
        ORDER BY rowid
        LIMIT ?
        """,
        (language, after_rowid, size),
    ).fetchall()


def direction(row: sqlite3.Row, language: Language) -> dict[str, str]:
    decision = direction_decision(
        DIRECTION_BY_KEY[language.key],
        nfc(row["entry_id"]),
        nfc(row["etymology"]),
    )
    if decision["direction_class"] == CLASS_NO_DIRECTION:
        return decision
    etymology = compact(row["etymology"], 4000)
    lowered = etymology.casefold()
    # A directional closure needs a direct source chain, not a possibility,
    # an alternative proposal, or an explicitly unexplained item.  The older
    # generic parser is intentionally broader because it inventories cases;
    # this lane-level gate decides whether a verdict may issue.
    direct = re.match(
        r"^(?:borrowed from|learned borrowing from|calque of|from|"
        r"ultimately from|via)\b",
        lowered,
    )
    hedge = re.search(
        r"\b(?:unknown|unexplained|uncertain|possibly|probably|perhaps|"
        r"alternatively|according to|theory|may be|might be|could be|"
        r"disputed|attempts? to connect|regards? .{0,80} as)\b",
        lowered,
    )
    contradiction = re.search(r"\b(?:but|however|though|rather)\b", lowered)
    if not direct or hedge or contradiction:
        return {
            "direction_class": CLASS_NO_DIRECTION,
            "direction_tag": "SECTION27-ORDINARY-JUDGMENT-REOPENED",
            "named_donor": "",
            "direction_evidence": (
                "الاتجاه غير صالح للحكم: سلسلة المصدر غير مباشرة أو محوطة بالشك"
            ),
        }
    return decision


def layer_summary(hits: list[CandidateHit], limit: int = 6) -> str:
    if not hits:
        return "لا مرشح مرخص"
    items = []
    for hit in hits[:limit]:
        rules = "+".join(hit.rule_ids) or "ANCHOR"
        items.append(f"{hit.form}[{rules}]")
    suffix = f"؛ وغيرها {len(hits) - limit}" if len(hits) > limit else ""
    return "، ".join(items) + suffix


def direction_card(
    language: Language,
    row: sqlite3.Row,
    roots: list[CandidateHit],
    nuclei: list[CandidateHit],
    decision: dict[str, str],
    ordinal: int,
    semantic: SemanticReview,
) -> str:
    entry_id = nfc(row["entry_id"])
    display = nfc(row["headword"])
    romanization = nfc(row["romanization"])
    if romanization and romanization != display:
        display += f" ({romanization})"
    klass = decision["direction_class"]
    tag = {
        CLASS_SEMITIC: TAG_SEMITIC,
        CLASS_THIRD: TAG_THIRD,
        CLASS_TO_ARABIC: TAG_TO_ARABIC,
    }[klass]
    oldest = compact(row["etymology"], 600) or compact(row["source_stratum"], 300) or "لا صورة أقدم مسماة في حقل المصدر"
    form_targets = json.loads(row["form_targets_json"] or "[]")
    alt_targets = json.loads(row["alternative_targets_json"] or "[]")
    zero_bits = []
    if row["form_of"]:
        zero_bits.append("form_of=" + ("، ".join(map(nfc, form_targets)) or "هدف غير مسمى"))
    if row["alternative_of"]:
        zero_bits.append("alt_of=" + ("، ".join(map(nfc, alt_targets)) or "هدف غير مسمى"))
    if not zero_bits:
        zero_bits.append("لا نزع صرفي حدسي؛ استعملت tokens_json المثبتة في لقطة المصدر")
    root_two_sources = [
        hit.form for hit in roots if len(semantic.sources(hit.form)) >= 2
    ]
    core_readings = []
    for hit in nuclei[:4]:
        item = semantic.core[hit.form]
        reading = nfc(item.get("jabal_lexicon_reading_ar")) or nfc(item.get("composed_reading_ar")) or "بلا قراءة معتمدة"
        core_readings.append(f"{hit.form} «{reading}»")
    filter_text = compact(decision.get("direction_evidence") or decision.get("direction_source") or row["etymology"], 650)
    name_note = "؛ العلم خارج البسط الإحصائي" if nfc(row["pos"]).casefold() in NAME_POS else ""
    return nfc(
        f"""

### بطاقة: `{entry_id}`، {display} (شهر الطبقتين ج، {ordinal})
- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14) + SECTION28-TWO-LAYER (2026-08-01)
- الكلمةُ في الفرع: {display}؛ `{entry_id}`
- أقدمُ صورةٍ مستعادة: {oldest} [{language.source_label}؛ حقل etymology/source_stratum]
- الخطوةُ صفر (التعرية بصرف الفرع): {'؛ '.join(zero_bits)} ← اللب: {nfc(row['selected_input']) or nfc(row['skeleton']) or '(لا لب صامتي مسجل)'}
- درجةُ المقارنة: الجذر والنواة معًا؛ لا ترتيب فشل بينهما
- نتيجةُ طبقة الجذر: مرشحون مرخصون مستقلون={len(roots)}؛ {layer_summary(roots)}؛ لا حكم صلة صادر من الاسترجاع وحده
- نتيجةُ طبقة النواة: مرشحون مرخصون مستقلون={len(nuclei)}؛ {('؛ '.join(core_readings) or 'لا مرشح مرخص')}؛ المصدر `data/juthoor-core-levels.json`؛ لا حكم صلة صادر من الاسترجاع وحده
- مسحُ المعاني العربيّة: الجذور المرشحة ذات شاهدين قديمين={('، '.join(root_two_sources[:8]) or 'لا شيء في هذه البطاقة')}؛ لا تُستعمل هذه القائمة صلة بلا مراجعة دلالية مستقلة [لسان العرب لابن منظور؛ تاج العروس لمرتضى الزبيدي]
- المقابلُ من اللسان: لا مقابل إرثي صادر؛ التصنيف اتجاه انتقال منشور
- مسارُ الصوت: استرجاع من الصفوف الموقعة فقط؛ الجذر={layer_summary(roots, 4)}؛ النواة={layer_summary(nuclei, 4)}
- المعنى من قاموس الفرع: «{compact(row['gloss'], 700) or '(غير مسجل في المصدر)'}» [{language.source_label}]
- المدار: لا مدار دلالي مستعمل لإصدار حكم الانتقال
- المصفاة: الصنف={klass}؛ الوسم={tag}؛ الدليل المنشور={filter_text}
- فصلُ المتجانسات والاقتراض: الحكم مقيد بهوية العضو ومعناه أعلاه؛ لا يرث من مماثل الرسم
- مؤشر اليتم: غير مستعمل في حكم الاتجاه
- إشعاع الأسرة في الفرع: الأعضاء المعجمية المدعومة=1؛ سلاسل المعنى المدعومة=1؛ هذا العضو وحده بعد حق النقض
- إشعاع الأسرة في العربية: الأعضاء المعجمية المدعومة=0؛ سلاسل المعنى المدعومة=0؛ الانتقال مفصول عن الإرث
- جسورُ الاسترداد المفحوصة: الجذر مستقلًا؛ الأجوف حيث أجازه المولد؛ النواة مستقلًا من الفهرس المجمد؛ حقل الأصل المنشور؛ اتجاه المانح
- حالةُ الإغلاق: READY؛ اتجاه منشور مسمى{name_note}
- الحكم (استكشاف): {tag}
- ملاحظات: الانتقال لا يدخل بسط الإرث؛ لم يُنشأ صف صوتي ولم تُخف النواة خلف نجاح الجذر أو فشله.
"""
    )


def coverage_row(language: Language, row: sqlite3.Row, roots: list[CandidateHit], nuclei: list[CandidateHit], batch: int) -> dict[str, Any]:
    flags = []
    pos = nfc(row["pos"]).casefold()
    if row["form_of"]:
        flags.append("SECTION26-FORM-SELF-JUDGMENT")
    if row["alternative_of"]:
        flags.append("MEMBER-INDEPENDENT-ALT")
    if pos in FUNCTION_POS:
        flags.append("SECTION26-FUNCTION-PRIORITY")
    elif pos in NONLEXICAL_POS:
        flags.append("SECTION26-NONLEXICAL-INCLUDED")
    reason = (
        "TWO-LAYER-OPEN؛ "
        f"الجذر=مرشحون مرخصون {len(roots)}؛ "
        f"النواة=مرشحون مرخصون {len(nuclei)} من الفهرس المجمد؛ "
        "قُرئا معًا لا على ترتيب الفشل؛ الحكم غير صادر"
    )
    if flags:
        reason += "؛ " + "؛ ".join(flags)
    return {
        "member_id": nfc(row["entry_id"]),
        "language": language.key,
        "form": nfc(row["headword"]) or "(رسم فارغ في المصدر)",
        "branch_meaning": nfc(row["gloss"]) or "(غير مسجل في المصدر)",
        "non_issuance_reason": reason,
        "batch_number": batch,
    }


def append_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    materialized = list(rows)
    if not materialized:
        return 0
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in materialized:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    return len(materialized)


def ledger_ids(path: Path, language: str | None = None) -> set[str]:
    if not path.exists():
        return set()
    result: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if language is not None and row.get("language") != language:
                continue
            result.add(nfc(str(row["member_id"])))
    return result


def finalize_promotions(
    language: Language,
    progress: dict[str, Any],
    coverage_ids: set[str],
) -> None:
    state = progress["languages"][language.key]
    if state.get("promotions_finalized"):
        return
    promotion_ids = ledger_ids(PROMOTIONS, language.key)
    promotion_ids.difference_update(ledger_ids(RETRACTIONS, language.key))
    targets = promotion_ids & coverage_ids
    removed = 0
    if targets:
        temporary = COVERAGE.with_suffix(COVERAGE.suffix + ".two-layer.tmp")
        with COVERAGE.open(encoding="utf-8") as source, temporary.open(
            "w", encoding="utf-8", newline="\n"
        ) as destination:
            for line_number, line in enumerate(source, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                entry_id = nfc(str(row["member_id"]))
                if entry_id in targets:
                    removed += 1
                    continue
                destination.write(line if line.endswith("\n") else line + "\n")
        if removed != len(targets):
            temporary.unlink(missing_ok=True)
            raise RuntimeError(
                f"{language.key}: promotion removal drift {removed}!={len(targets)}"
            )
        temporary.replace(COVERAGE)
        coverage_ids.difference_update(targets)
    state["promotions_finalized"] = True
    state["promotion_rows_removed"] = removed
    atomic_json(PROGRESS, progress)
    text = nfc(
        f"""

<!-- {MARKER}:{language.key}:PROMOTIONS-FINALIZED -->
### تصفية ترقيات الاتجاه عند فراغ {language.source_label}

نُقلت {removed} هويةً من سطور الحكم غير الصادر إلى بطاقات اتجاه صادرة،
وحُفظ عدم التقاطع بين `lane_c_coverage.jsonl` وبطاقات القراءة. لا يدخل
`{TAG_SEMITIC}` بسط الإرث المشترك.
"""
    )
    with (READINGS / language.reading_file).open(
        "a", encoding="utf-8", newline="\n"
    ) as handle:
        handle.write(text)
    ensure_audit_header()
    with AUDIT.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def review_header() -> str:
    return "\t".join(
        (
            "language",
            "member_id",
            "form",
            "pos",
            "branch_gloss",
            "layer",
            "candidate",
            "core_or_root_reading",
            "support_root",
            "classical_sources",
            "licensed_rules",
            "score",
            "status",
        )
    ) + "\n"


def review_line(language: Language, row: sqlite3.Row, candidate: dict[str, Any]) -> str:
    values = (
        language.key,
        nfc(row["entry_id"]),
        compact(row["headword"], 120),
        compact(row["pos"], 40),
        compact(row["gloss"], 260),
        candidate["layer"],
        candidate["form"],
        compact(candidate["reading"] or candidate.get("support_root_text", ""), 260),
        candidate.get("support_root", ""),
        "+".join(candidate["sources"]),
        "+".join(candidate["rules"]) or "ANCHOR",
        f"{candidate['score']:.6f}",
        "REVIEW-CANDIDATE-NOT-VERDICT",
    )
    return "\t".join(str(value).replace("\t", " ").replace("\n", " ") for value in values) + "\n"


def batch_receipt(language: Language, batch_number: int, rows: list[sqlite3.Row], remaining: int, counts: Counter[str]) -> str:
    first, last = rows[0], rows[-1]
    marker = f"{MARKER}:{language.key}:{batch_number}:{first['source_rowid']}-{last['source_rowid']}"
    return nfc(
        f"""

<!-- {marker} -->
## شهر الطبقتين: {language.source_label}، الدفعة {batch_number}

- موضع الدفعة: بدأت من {nfc(first['headword']) or '(رسم فارغ)'} (`{nfc(first['entry_id'])}`) وانتهت عند {nfc(last['headword']) or '(رسم فارغ)'} (`{nfc(last['entry_id'])}`)؛ بقي في الجرد بعدها {remaining}.
- المقام: {len(rows)} عضوًا؛ سُجّل {counts['coverage_added']} سطر تغطية جديدًا، وحُفظ {counts['existing_cards']} حكمًا سابقًا، ومرّ {counts['names']} علمًا من جرد الجذور، وكُتبت {counts['new_direction_cards']} بطاقة اتجاه.
- طبقة الجذر مستقلة: حمل {counts['root_candidate_members']} عضوًا مرشحًا مرخصًا، وعدد المرشحين المتميزين {counts['root_candidates']}.
- طبقة النواة مستقلة: حمل {counts['nucleus_candidate_members']} عضوًا مرشحًا مرخصًا من `data/juthoor-core-levels.json`، وعدد المرشحين المتميزين {counts['nucleus_candidates']}.
- الانتقال السامي المحفوظ خارج بسط الإرث: {counts['transmissions']}؛ والأسئلة المتخطاة للمؤلف: {counts['author_questions']}.
- الرقمان المفصولان: {counts['positive']} صلة موجبة جديدة؛ {counts['closures']} إغلاقًا جديدًا.
- خط البرهان مجمد، ولم يُنشأ صف صوتي ولم يُشغّل باني مشترك.

<!-- /{marker} -->
"""
    )


def ensure_audit_header() -> None:
    if AUDIT.exists():
        return
    AUDIT.write_text(
        nfc(
            f"""# المسار ج: محضر شهر الطبقتين

**التاريخ:** {DATE}. **النطاق:** اليونانية القديمة، واللاتينية، والفارسية، والقوطية، والنوردية القديمة، والويلزية.

تُقرأ طبقة الجذر/الأجوف وطبقة النواة معًا لكل عضو. فهرس النوى والشبكة وقواعد البيانات مصادر قراءة مجمدة، وخط البرهان لا يُمس. العضو غير المحكوم لا يأخذ بطاقة نثرية؛ مصيره في `lane_c_coverage.jsonl`، والأعلام في جردها المستقل.
"""
        ),
        encoding="utf-8",
        newline="\n",
    )


def process_batch(language: Language, rows: list[sqlite3.Row], progress: dict[str, Any], retriever: TwoLayerRetriever, semantic: SemanticReview, coverage_ids: set[str], card_ids: set[str], name_ids: set[str], review_top: int, write: bool) -> tuple[Counter[str], list[str], list[str], list[dict[str, Any]]]:
    state = progress["languages"][language.key]
    batch_number = int(state["batches"]) + 1
    counts: Counter[str] = Counter()
    cards: list[str] = []
    review_candidates: list[tuple[float, str]] = []
    coverage_rows: list[dict[str, Any]] = []
    promotions: list[dict[str, Any]] = []
    for offset, row in enumerate(rows, 1):
        entry_id = nfc(row["entry_id"])
        roots, nuclei = retriever.layers(language.key, tokens_for(row))
        counts["root_candidates"] += len(roots)
        counts["nucleus_candidates"] += len(nuclei)
        counts["root_candidate_members"] += bool(roots)
        counts["nucleus_candidate_members"] += bool(nuclei)
        reviewed = semantic.best(row, roots, nuclei)
        for item in reviewed:
            line = review_line(language, row, item)
            review_candidates.append((float(item["score"]), line))

        decision = direction(row, language)
        directed = decision["direction_class"] != CLASS_NO_DIRECTION
        if entry_id in card_ids:
            counts["existing_cards"] += 1
            if decision["direction_class"] == CLASS_SEMITIC:
                counts["transmissions"] += 1
            continue
        if entry_id in name_ids:
            counts["names"] += 1
            if directed:
                card = direction_card(
                    language,
                    row,
                    roots,
                    nuclei,
                    decision,
                    int(state["processed"]) + offset,
                    semantic,
                )
                cards.append(card)
                counts["new_direction_cards"] += 1
                counts["transmissions"] += decision["direction_class"] == CLASS_SEMITIC
                counts["closures"] += decision["direction_class"] != CLASS_SEMITIC
            continue
        if entry_id in coverage_ids:
            if directed:
                card = direction_card(
                    language,
                    row,
                    roots,
                    nuclei,
                    decision,
                    int(state["processed"]) + offset,
                    semantic,
                )
                cards.append(card)
                promotions.append(
                    {
                        "member_id": entry_id,
                        "language": language.key,
                        "direction_class": decision["direction_class"],
                        "direction_tag": decision["direction_tag"],
                        "batch_number": batch_number,
                        "status": "pending-coverage-removal-at-language-completion",
                    }
                )
                counts["new_direction_cards"] += 1
                counts["promotions"] += 1
                counts["transmissions"] += decision["direction_class"] == CLASS_SEMITIC
                counts["closures"] += decision["direction_class"] != CLASS_SEMITIC
            else:
                counts["existing_coverage"] += 1
            continue
        if directed:
            card = direction_card(
                language,
                row,
                roots,
                nuclei,
                decision,
                int(state["processed"]) + offset,
                semantic,
            )
            cards.append(card)
            counts["new_direction_cards"] += 1
            counts["transmissions"] += decision["direction_class"] == CLASS_SEMITIC
            counts["closures"] += decision["direction_class"] != CLASS_SEMITIC
        else:
            coverage_rows.append(coverage_row(language, row, roots, nuclei, batch_number))
            counts["coverage_added"] += 1
    review_candidates.sort(key=lambda item: item[0], reverse=True)
    review_lines = [line for _, line in review_candidates[:review_top]]
    return counts, cards, review_lines, promotions + coverage_rows


def commit_batch(language: Language, rows: list[sqlite3.Row], progress: dict[str, Any], counts: Counter[str], cards: list[str], review_lines: list[str], mixed_rows: list[dict[str, Any]], coverage_ids: set[str], card_ids: set[str]) -> None:
    state = progress["languages"][language.key]
    batch_number = int(state["batches"]) + 1
    promotions = [row for row in mixed_rows if "direction_class" in row]
    coverage_rows = [row for row in mixed_rows if "non_issuance_reason" in row]
    if any(row["member_id"] in coverage_ids for row in coverage_rows):
        raise RuntimeError("duplicate coverage identity in pending batch")
    if any(ENTRY_RE.search(card).group(0) in card_ids for card in cards):
        raise RuntimeError("duplicate direction card identity in pending batch")
    added = append_jsonl(COVERAGE, coverage_rows)
    if added != counts["coverage_added"]:
        raise RuntimeError("coverage append count drift")
    coverage_ids.update(row["member_id"] for row in coverage_rows)
    append_jsonl(PROMOTIONS, promotions)
    if cards:
        path = READINGS / language.reading_file
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write("".join(cards))
        for card in cards:
            card_ids.add(ENTRY_RE.search(card).group(0))
    if review_lines:
        if not REVIEW.exists():
            REVIEW.write_text(review_header(), encoding="utf-8", newline="\n")
        with REVIEW.open("a", encoding="utf-8", newline="\n") as handle:
            handle.writelines(review_lines)

    processed_after = int(state["processed"]) + len(rows)
    remaining = int(state["total"]) - processed_after
    receipt = batch_receipt(language, batch_number, rows, remaining, counts)
    with (READINGS / language.reading_file).open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(receipt)
    ensure_audit_header()
    with AUDIT.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(receipt)

    state["processed"] = processed_after
    state["last_rowid"] = int(rows[-1]["source_rowid"])
    state["last_member_id"] = nfc(rows[-1]["entry_id"])
    state["batches"] = batch_number
    for key in (
        "positive",
        "closures",
        "transmissions",
        "promotions",
        "coverage_added",
        "names",
        "root_candidate_members",
        "nucleus_candidate_members",
    ):
        target = "names_seen" if key == "names" else key
        state[target] = int(state.get(target, 0)) + int(counts[key])
    atomic_json(PROGRESS, progress)
    print(
        "BATCH",
        language.key,
        batch_number,
        nfc(rows[0]["entry_id"]),
        nfc(rows[-1]["entry_id"]),
        f"members={len(rows)}",
        f"root_members={counts['root_candidate_members']}",
        f"nucleus_members={counts['nucleus_candidate_members']}",
        f"positive={counts['positive']}",
        f"closures={counts['closures']}",
        f"remaining={remaining}",
        sep="\t",
        flush=True,
    )


def run(args: argparse.Namespace) -> None:
    progress = load_progress(create=True)
    retriever = TwoLayerRetriever()
    semantic = SemanticReview(retriever.core)
    coverage_ids = load_first_field_ids(COVERAGE)
    names_by_language = load_names_by_language()
    cards_by_language = load_card_ids()
    languages = (LANGUAGE_BY_KEY[args.language],) if args.language else LANGUAGES
    batches_done = 0
    for language in languages:
        state = progress["languages"][language.key]
        if int(state["processed"]) == int(state["total"]):
            finalize_promotions(language, progress, coverage_ids)
            print(f"COMPLETE\t{language.key}\tremaining=0", flush=True)
            continue
        con = ro_connection(language.db_path)
        try:
            while int(state["processed"]) < int(state["total"]):
                rows = fetch_batch(con, language.key, int(state["last_rowid"]), args.batch_size)
                if not rows:
                    raise RuntimeError(
                        f"{language.key}: source ended with {state['total'] - state['processed']} remaining"
                    )
                counts, cards, review_lines, mixed = process_batch(
                    language,
                    rows,
                    progress,
                    retriever,
                    semantic,
                    coverage_ids,
                    cards_by_language[language.key],
                    names_by_language.get(language.key, set()),
                    args.review_top,
                    True,
                )
                commit_batch(
                    language,
                    rows,
                    progress,
                    counts,
                    cards,
                    review_lines,
                    mixed,
                    coverage_ids,
                    cards_by_language[language.key],
                )
                batches_done += 1
                if int(state["processed"]) == int(state["total"]):
                    finalize_promotions(language, progress, coverage_ids)
                if args.max_batches is not None and batches_done >= args.max_batches:
                    return
        finally:
            con.close()


def review(args: argparse.Namespace) -> None:
    progress = load_progress()
    retriever = TwoLayerRetriever()
    semantic = SemanticReview(retriever.core)
    coverage_ids = load_first_field_ids(COVERAGE)
    names_by_language = load_names_by_language()
    cards_by_language = load_card_ids()
    language = LANGUAGE_BY_KEY[args.language]
    state = progress["languages"][language.key]
    con = ro_connection(language.db_path)
    try:
        rows = fetch_batch(con, language.key, int(state["last_rowid"]), args.batch_size)
        if not rows:
            print(f"COMPLETE\t{language.key}\tremaining=0")
            return
        counts, _, review_lines, mixed = process_batch(
            language,
            rows,
            progress,
            retriever,
            semantic,
            coverage_ids,
            cards_by_language[language.key],
            names_by_language.get(language.key, set()),
            args.review,
            False,
        )
        promotions = [item for item in mixed if "direction_class" in item]
        print(
            f"NEXT\t{language.key}\t{rows[0]['entry_id']}\t{rows[-1]['entry_id']}\t"
            f"members={len(rows)}\troot_members={counts['root_candidate_members']}\t"
            f"nucleus_members={counts['nucleus_candidate_members']}\t"
            f"missing_coverage={counts['coverage_added']}\tpromotions={len(promotions)}"
        )
        print(review_header().rstrip())
        for line in review_lines:
            print(line.rstrip())
    finally:
        con.close()


def plan() -> None:
    progress = load_progress()
    print(f"schema\t{SCHEMA}")
    print(f"core_sha256\t{progress['pins']['core_sha256']}")
    print(f"network_sha256\t{progress['pins']['network_sha256']}")
    for language in LANGUAGES:
        state = progress["languages"][language.key]
        print(
            "PLAN",
            language.key,
            f"processed={state['processed']}",
            f"remaining={state['total'] - state['processed']}",
            f"batches={state['batches']}",
            f"last={state['last_member_id'] or '-'}",
            sep="\t",
        )


def validate(language_key: str | None = None) -> None:
    progress = load_progress()
    errors: list[str] = []
    coverage_ids = load_first_field_ids(COVERAGE)
    names = load_names_by_language()
    cards = load_card_ids()
    languages = (
        (LANGUAGE_BY_KEY[language_key],) if language_key else LANGUAGES
    )
    for language in languages:
        state = progress["languages"][language.key]
        remaining = int(state["total"]) - int(state["processed"])
        if remaining:
            errors.append(f"{language.key}: remaining={remaining}")
        overlap = coverage_ids & cards[language.key]
        if overlap:
            errors.append(f"{language.key}: card/coverage overlap={len(overlap)}")
        con = ro_connection(language.db_path)
        try:
            missing = 0
            wrong_name = 0
            for row in con.execute(
                "SELECT entry_id, lower(pos) AS pos FROM entries indexed by entries_language_status WHERE language=?",
                (language.key,),
            ):
                entry_id = nfc(row["entry_id"])
                if row["pos"] in NAME_POS:
                    if entry_id not in names.get(language.key, set()):
                        wrong_name += 1
                elif entry_id not in coverage_ids and entry_id not in cards[language.key]:
                    missing += 1
            if missing:
                errors.append(f"{language.key}: unregistered non-name members={missing}")
            if wrong_name:
                errors.append(f"{language.key}: names absent from names inventory={wrong_name}")
        finally:
            con.close()
        print(
            "VALIDATE",
            language.key,
            f"remaining={remaining}",
            f"cards={len(cards[language.key])}",
            f"names={len(names.get(language.key, set()))}",
            sep="\t",
        )
    if errors:
        raise RuntimeError("; ".join(errors))
    print(f"VALID\tcoverage_rows={len(coverage_ids)}\tall_remaining=0")


def repair_direction_cards() -> None:
    """Append corrections for this pass's cards that fail the strict gate."""

    retriever = TwoLayerRetriever()
    semantic = SemanticReview(retriever.core)
    coverage_ids = load_first_field_ids(COVERAGE)
    name_ids = load_names_by_language()
    already = ledger_ids(RETRACTIONS)
    progress = load_progress()
    total_retracted = 0
    for language in LANGUAGES:
        path = READINGS / language.reading_file
        ids: list[str] = []
        heading = re.compile(
            r"^### بطاقة: `(?P<entry>[^`]+)`.*\(شهر الطبقتين ج، \d+\)$"
        )
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                match = heading.match(line.rstrip("\n"))
                if match and match.group("entry") not in already:
                    ids.append(nfc(match.group("entry")))
        if not ids:
            continue
        con = ro_connection(language.db_path)
        corrections: list[str] = []
        coverage_rows: list[dict[str, Any]] = []
        retraction_rows: list[dict[str, Any]] = []
        state = progress["languages"][language.key]
        try:
            for entry_id in ids:
                row = con.execute(
                    """
                    SELECT rowid AS source_rowid, entry_id, headword,
                           romanization, pos, gloss, etymology,
                           source_stratum, source_scope_note, loan_hint,
                           form_of, alternative_of, form_targets_json,
                           alternative_targets_json, selected_input,
                           skeleton, tokens_json, unknown_original_json,
                           unknown_romanization_json, processing_status,
                           morphology_status
                    FROM entries WHERE entry_id=?
                    """,
                    (entry_id,),
                ).fetchone()
                if row is None:
                    raise RuntimeError(f"missing source row for {entry_id}")
                raw = direction_decision(
                    DIRECTION_BY_KEY[language.key], entry_id, nfc(row["etymology"])
                )
                safe = direction(row, language)
                if raw["direction_class"] == CLASS_NO_DIRECTION:
                    raise RuntimeError(f"generated direction card has no raw direction: {entry_id}")
                if safe["direction_class"] != CLASS_NO_DIRECTION:
                    continue
                roots, nuclei = retriever.layers(language.key, tokens_for(row))
                if (
                    nfc(row["pos"]).casefold() not in NAME_POS
                    and entry_id not in coverage_ids
                ):
                    coverage_rows.append(
                        coverage_row(
                            language,
                            row,
                            roots,
                            nuclei,
                            int(state.get("batches", 0)) or 1,
                        )
                    )
                    coverage_ids.add(entry_id)
                prior_tag = raw["direction_tag"]
                reason = (
                    "المصدر محوط بالشك أو البدائل، فلا يثبت مانحًا مباشرًا "
                    "ولا اتجاهًا صالحًا للإغلاق"
                )
                retraction_rows.append(
                    {
                        "member_id": entry_id,
                        "language": language.key,
                        "prior_verdict": prior_tag,
                        "corrected_state": "OPEN-CANDIDATE",
                        "reason": reason,
                        "date": DATE,
                    }
                )
                corrections.append(
                    nfc(
                        f"""

### نقض اتجاه: `{entry_id}`، {nfc(row['headword'])}
- الحكم السابق: {prior_tag}؛ منسوخ بهذه الحاشية.
- سبب النقض: {reason}.
- الطبقتان: الجذر={len(roots)} مرشحًا مرخصًا؛ النواة={len(nuclei)} مرشحًا مرخصًا من الفهرس المجمد؛ لا حكم صلة صادر.
- حالةُ الإغلاق المصححة: OPEN-CANDIDATE.
- الحكم (استكشاف): غير صادر.
"""
                    )
                )
                if raw["direction_class"] == CLASS_SEMITIC:
                    state["transmissions"] = max(
                        0, int(state.get("transmissions", 0)) - 1
                    )
                else:
                    state["closures"] = max(
                        0, int(state.get("closures", 0)) - 1
                    )
                total_retracted += 1
        finally:
            con.close()
        append_jsonl(COVERAGE, coverage_rows)
        append_jsonl(RETRACTIONS, retraction_rows)
        if corrections:
            section = nfc(
                f"""

<!-- {MARKER}:{language.key}:DIRECTION-GATE-CORRECTION -->
## تصحيح حارس الاتجاه في شهر الطبقتين

نقض الحارس المشدد {len(corrections)} حكمًا آليًا كانت صياغة مصدره احتمالية
أو بديلة، وأعاد غير الأعلام منها إلى `lane_c_coverage.jsonl`. لا يتغير حكم
أي سلسلة مصدر مباشرة غير محوطة بالشك.
{''.join(corrections)}
"""
            )
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(section)
            ensure_audit_header()
            with AUDIT.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(section)
    progress.setdefault("corrections", {})["strict_direction_gate_retractions"] = (
        int(progress.get("corrections", {}).get("strict_direction_gate_retractions", 0))
        + total_retracted
    )
    atomic_json(PROGRESS, progress)
    print(f"REPAIRED\tdirection_retractions={total_retracted}")


def promote_reviewed_semantics() -> None:
    """Commit the final human review without relaxing the two hard gates.

    This deliberately contains only the two exceptional cases found after the
    exhaustive pass.  ``hamr`` clears both old-Arabic-source and signed-sound-
    row gates at nucleus level.  ``drepa`` does not clear the latter at nucleus
    level: the mouth-family anchor is retrieval only, and is therefore recorded
    for the author rather than converted into a verdict.
    """

    marker = f"<!-- {MARKER}:old_norse:FINAL-SEMANTIC-REVIEW -->"
    old_norse = LANGUAGE_BY_KEY["old_norse"]
    reading_path = READINGS / old_norse.reading_file
    reading_text = reading_path.read_text(encoding="utf-8")
    if marker in reading_text:
        print("REVIEWED-SEMANTICS\talready-finalized=1")
        return

    progress = load_progress()
    unfinished = {
        key: int(state["total"]) - int(state["processed"])
        for key, state in progress["languages"].items()
        if int(state["total"]) != int(state["processed"])
    }
    if unfinished:
        raise RuntimeError(f"semantic review before queue exhaustion: {unfinished}")

    hamr_id = "kaikki_old_norse_2026_07_23:4196:en-hamr-non-noun-o7fzfX9H"
    drepa_id = "kaikki_old_norse_2026_07_23:553:en-drepa-non-verb-0Xm~Y4pZ"
    rang_id = "kaikki_persian_2026_07_23:143:en-رنگ-fa-noun-1oOMNXRE"
    select = """
        SELECT rowid AS source_rowid, entry_id, headword, romanization, pos,
               gloss, etymology, source_stratum, source_scope_note, loan_hint,
               form_of, alternative_of, form_targets_json,
               alternative_targets_json, selected_input, skeleton, tokens_json,
               unknown_original_json, unknown_romanization_json,
               processing_status, morphology_status
        FROM entries WHERE entry_id=?
    """
    retriever = TwoLayerRetriever()
    semantic = SemanticReview(retriever.core)
    con = ro_connection(old_norse.db_path)
    try:
        hamr = con.execute(select, (hamr_id,)).fetchone()
        drepa = con.execute(select, (drepa_id,)).fetchone()
    finally:
        con.close()
    if hamr is None or drepa is None:
        raise RuntimeError("final semantic-review source member is absent")
    if tokens_for(hamr) != ("h", "m", "r") or "*hamô" not in nfc(hamr["etymology"]):
        raise RuntimeError("hamr source morphology drift")
    if tokens_for(drepa) != ("d", "r", "p") or "*drepaną" not in nfc(drepa["etymology"]):
        raise RuntimeError("drepa source morphology drift")

    hamr_roots, hamr_nuclei = retriever.layers("old_norse", tokens_for(hamr))
    gh_m_r = next(
        (hit for hit in hamr_roots if hit.form == "غمر" and hit.rule_ids == ("GUT-04",)),
        None,
    )
    gh_m = next(
        (hit for hit in hamr_nuclei if hit.form == "غم" and hit.rule_ids == ("GUT-04",)),
        None,
    )
    expected_sources = {
        "لسان العرب لابن منظور",
        "تاج العروس لمرتضى الزبيدي",
    }
    if gh_m_r is None or gh_m is None:
        raise RuntimeError("hamr lost its signed GUT-04 root/nucleus retrieval")
    if set(semantic.sources("غمر")) != expected_sources:
        raise RuntimeError("hamr no longer has exactly the two named old Arabic sources")
    core_gh_m = retriever.core.get("غم", {})
    if core_gh_m.get("jabal_lexicon_reading_ar") != "نوع من التغطية والحجب":
        raise RuntimeError("frozen غم reading drift")

    cards = load_card_ids()
    coverage_ids = load_first_field_ids(COVERAGE)
    if hamr_id in cards["old_norse"] or hamr_id not in coverage_ids:
        raise RuntimeError("hamr is not in the expected pre-promotion state")
    if drepa_id not in cards["old_norse"]:
        raise RuntimeError("drepa root card is absent")

    # The older drepa card hid two named rows under an anchor-only summary.
    # Confirm that the signed, route-disclosed root path really exists.  Its
    # nucleus remains unissued because p->f has no applicable direct row here.
    drepa_hits, unmapped = generate_hits(
        tokens_for(drepa), "old_norse", retriever.rules, retriever.inventory
    )
    if unmapped or not any(
        hit.form == "ضرب"
        and set(hit.rule_ids) == {"DENT-06", "LAB-01"}
        and hit.route_flag
        for hit in drepa_hits
    ):
        raise RuntimeError("drepa lost its signed DENT-06 + LAB-01 root route")
    if set(semantic.sources("دفع")) != expected_sources:
        raise RuntimeError("drepa nucleus support root lost its two old sources")

    promotion = {
        "member_id": hamr_id,
        "language": "old_norse",
        "form": "hamr",
        "layer": "nucleus",
        "verdict": "NUCLEUS-TRACE",
        "nucleus": "غم",
        "support_root": "غمر",
        "branch_source_form": "Proto-Germanic *hamô",
        "branch_meaning": "shroud, covering",
        "licensed_rules": ["GUT-04"],
        "classical_sources": sorted(expected_sources),
        "core_sha256": sha256(CORE),
        "network_sha256": sha256(NETWORK),
        "date": DATE,
    }
    questions = [
        {
            "member_id": drepa_id,
            "language": "old_norse",
            "form": "drepa",
            "layer": "nucleus",
            "candidate": "دف",
            "support_root": "دفع",
            "question": "هل يوقع صف مباشر p↔ف صالح للنوردية القديمة؟ المرساة الفمية استرجاع لا قانون، وLAB-07 خارج النطاق، وLAB-03 لا يفسر p جرمانية محفوظة.",
            "state": "LAW-GAP; no nucleus verdict issued",
            "date": DATE,
        },
        {
            "member_id": rang_id,
            "language": "persian",
            "form": "رنگ (rang)",
            "layer": "nucleus",
            "candidate": "لن",
            "support_root": "لون",
            "question": "النواة لن في الفهرس المجمد بلا قراءة معتمدة؛ هل تُقرأ قبل إعادة فتح رنگ «colour»؟",
            "state": "TOOL-GAP; no nucleus verdict issued",
            "date": DATE,
        },
    ]
    route = {
        "member_id": drepa_id,
        "language": "old_norse",
        "form": "drepa",
        "layer": "root",
        "verdict": "ROOT-TRACE (existing; sound-path correction)",
        "arabic_root": "ضرب",
        "licensed_rules": ["DENT-06", "LAB-01"],
        "route_flag": True,
        "route_note": "DENT-06 carries signed loan-route evidence; disclosed here rather than hidden under ANCHOR.",
        "date": DATE,
    }

    hamr_card = nfc(
        f"""

{marker}
## استدراك العدستين بعد فراغ الطابور: النوردية القديمة

### بطاقة: `{hamr_id}`، hamr (استدراك شهر الطبقتين ج)
- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14) + SECTION28-TWO-LAYER (2026-08-01)؛ خط البرهان مجمد.
- الكلمةُ في الفرع: hamr [noun؛ `{hamr_id}`].
- أقدمُ صورةٍ مستعادة: Proto-Germanic `*hamô` «shroud, covering» [Kaikki Old Norse؛ حقل `etymology_text`].
- الخطوةُ صفر (التعرية بصرف الفرع): الصورة المستعادة نفسها تحفظ `h-m` ولا تحفظ الراء السطحية في `hamr`؛ فاللب المقارن `h-m`، ولا تُستعمل الراء لبناء جذر كامل.
- درجةُ المقارنة: الجذر والنواة معًا؛ لا ترتيب فشل بينهما.
- نتيجةُ طبقة الجذر: غير صادر؛ `غمر` مرشح استرجاع سطحي بـ`GUT-04`، لكن راءه تعتمد على حرف لا تحفظه الصورة المستعادة `*hamô`؛ حالة الطبقة `MORPHOLOGY-BLOCKED`.
- نتيجةُ طبقة النواة: `h-m ↔ غ-م` بالصف الموقع `GUT-04`، والنواة المجمدة `غم` «نوع من التغطية والحجب»؛ الحكم `NUCLEUS-TRACE`.
- مسحُ المعاني العربيّة: لسان العرب في مادة `غمر`: «غمره الماء: علاه وغطاه»؛ وتاج العروس في المادة نفسها يصف الغمر بالماء الذي يغطي من دخله [لسان العرب لابن منظور؛ تاج العروس لمرتضى الزبيدي].
- المقابلُ من اللسان: `غم` «نوع من التغطية والحجب»، بشاهد المادة `غمر` في المصدرين القديمين.
- مسارُ الصوت: `GUT-04` وحده في `h ↔ غ`؛ الميم محفوظة بهويتها الصوتية؛ لا مرساة فمية معروضة قانونًا، ولا صف جديد.
- المعنى من قاموس الفرع: «shroud, covering» [Kaikki Old Norse، العضو المسمى].
- المدار: مباشر؛ الشيء الساتر المغطي في الفرع يلتقي حدث التغطية والحجب في النواة ومادتها العربية.
- المصفاة: السلسلة موروثة من Proto-Germanic `*hamô`، ولا مانح أجنبي بعد الافتراق مسمى في حقل الاشتقاق.
- فصلُ المتجانسات والاقتراض: الحكم لهذا العضو ذي معنى «shroud, covering» وحده؛ لا ينتقل إلى متحد الرسم ولا إلى معنى آخر.
- مؤشر اليتم: غير مستعمل في إصدار الحكم.
- إشعاع الأسرة في الفرع: الأعضاء المعجمية المدعومة=1؛ سلاسل المعنى المدعومة=1؛ حُد الدعم بالعضو المفحوص.
- إشعاع الأسرة في العربية: الأعضاء المعجمية المدعومة=1 (`غمر`)؛ سلاسل المعنى المدعومة=1 (التغطية والحجب).
- جسورُ الاسترداد المفحوصة: الصورة المستعادة؛ التعرية؛ الجذر مستقلًا؛ النواة مستقلًا من الفهرس المجمد؛ `GUT-04`؛ مروحة `غمر` في المصدرين؛ الأصل المنشور؛ القرض؛ المدار.
- حالةُ الإغلاق: READY على طبقة النواة؛ `MORPHOLOGY-BLOCKED` على طبقة الجذر.
- الحكم (استكشاف): NUCLEUS-TRACE.
- عدسة الاسترداد: أعادت النواة `غم` ما كانت عين الجذر تفقده بعد إسقاط راء السطح.
- عدسة التشكيك: لم يُسمح لمرشح `غمر` الكامل بوراثة الراء السطحية، ولم تُستعمل المرساة الفمية قانونًا تاريخيًا.
- ملاحظات: المصدران العربيان القديمان مسميان؛ صف الصوت موقع؛ لا تشغيل لخط البرهان ولا بناء لملف مشترك.

### تصحيح مسار وإتمام طبقتين: `{drepa_id}`، drepa
- المرجع: بطاقة `drepa` السابقة وحكمها الجذري `ROOT-TRACE`.
- نتيجةُ طبقة الجذر: يبقى الحكم السابق، لكن عبارة «تطابق ذاتي» في مسار الصوت منسوخة؛ المسار الصحيح `DENT-06` لـ`d↔ض` مع وسم مسار السند الاستعاري، و`LAB-01` لـ`p↔ب`، والراء محفوظة. سُجّل `route_flag=1` صراحةً.
- نتيجةُ طبقة النواة: `دف` «الضغط من الظاهر أو إليه» يوافق `to push`، ومادة `دفع` ثابتة في لسان العرب وتاج العروس، لكن لا حكم يصدر: `ANCHOR:p→ف` استرجاع لا قانون، و`LAB-07` خارج نطاق النوردية، و`LAB-03` لا يفسر `p` الجرمانية المحفوظة في `*drepaną`.
- حالةُ طبقة النواة: LAW-GAP؛ رُفع السؤال للمؤلف وتُخُطِّي الموضع.

- موضع الاستدراك: بعد فراغ النوردية عند `{progress['languages']['old_norse']['last_member_id']}`؛ بقي في جردها 0.
- الرقمان المفصولان: 1 صلة موجبة جديدة (نواة=1؛ جذر=0)؛ 0 إغلاق جديد.
- خط البرهان مجمد، ولم يُنشأ صف صوتي أو يُشغّل باني ملف مشترك.
"""
    )
    audit_section = nfc(
        f"""

{marker}
## استدراك العدستين بعد فراغ الطوابير

- رُقّي `hamr` إلى `NUCLEUS-TRACE` مع `غم/غمر`: الصورة المستعادة `*hamô`، والصف `GUT-04`، ولسان العرب وتاج العروس.
- حُجب جذر `hamr` الكامل لأن الراء السطحية لا تحفظها الصورة المستعادة.
- صُحح مسار جذر `drepa` القديم إلى `DENT-06 + LAB-01` مع إظهار `route_flag=1`؛ وبقيت نواته `دف` في `LAW-GAP` بلا حكم.
- سُجل سؤالان للمؤلف من غير إيقاف: صف `p↔ف` لـ`drepa`، وقراءة النواة المجمدة `لن` قبل `رنگ` الفارسية.
- الرقمان المفصولان: 1 صلة موجبة جديدة؛ 0 إغلاق جديد.
- الموضع: الطوابير الستة عند الصفر؛ آخر النوردية `{progress['languages']['old_norse']['last_member_id']}`.
"""
    )

    temporary = COVERAGE.with_suffix(COVERAGE.suffix + ".semantic-review.tmp")
    removed = 0
    with COVERAGE.open(encoding="utf-8") as source, temporary.open(
        "w", encoding="utf-8", newline="\n"
    ) as destination:
        for line in source:
            if not line.strip():
                continue
            row = json.loads(line)
            if nfc(str(row["member_id"])) == hamr_id:
                removed += 1
                continue
            destination.write(line if line.endswith("\n") else line + "\n")
    if removed != 1:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"hamr coverage removal drift: {removed} != 1")
    temporary.replace(COVERAGE)

    with reading_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(hamr_card)
    ensure_audit_header()
    with AUDIT.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(audit_section)
    append_jsonl(SEMANTIC_PROMOTIONS, (promotion,))
    append_jsonl(AUTHOR_QUESTIONS, questions)
    append_jsonl(ROUTE_FLAGS, (route,))

    state = progress["languages"]["old_norse"]
    state["positive"] = int(state.get("positive", 0)) + 1
    state["semantic_nucleus_links"] = 1
    state["semantic_root_links"] = 0
    state["semantic_reviewed_members"] = 2
    progress.setdefault("final_review", {}).update(
        {
            "new_positive_links": 1,
            "new_closures": 0,
            "author_questions": 2,
            "coverage_rows_removed": 1,
        }
    )
    atomic_json(PROGRESS, progress)
    print(
        "REVIEWED-SEMANTICS",
        "positive_links=1",
        "closures=0",
        "coverage_removed=1",
        "author_questions=2",
        sep="\t",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--review", type=int, metavar="N")
    mode.add_argument("--validate", action="store_true")
    mode.add_argument("--repair-direction-cards", action="store_true")
    mode.add_argument("--promote-reviewed-semantics", action="store_true")
    parser.add_argument("--language", choices=tuple(LANGUAGE_BY_KEY))
    parser.add_argument("--batch-size", type=int, default=900)
    parser.add_argument("--max-batches", type=int)
    parser.add_argument("--review-top", type=int, default=12)
    args = parser.parse_args()
    if not 1 <= args.batch_size <= 900:
        parser.error("--batch-size must be between 1 and 900")
    if args.review is not None and not args.language:
        parser.error("--review requires --language")
    if args.review is not None and args.review < 1:
        parser.error("--review must be positive")
    return args


def main() -> int:
    args = parse_args()
    if args.run:
        run(args)
    elif args.review is not None:
        review(args)
    elif args.validate:
        validate(args.language)
    elif args.repair_direction_cards:
        repair_direction_cards()
    elif args.promote_reviewed_semantics:
        promote_reviewed_semantics()
    else:
        plan()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
