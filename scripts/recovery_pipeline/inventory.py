from __future__ import annotations

import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .candidates import ArabicInventory, CandidateHit, generate_hits
from .families import (
    FAMILY_METADATA_VERSION,
    build_families,
    clear_language_families,
    ensure_family_schema,
    family_summary,
    install_family_review_overlay,
    load_family_review_states,
)
from .network import ShiftRule, compile_network
from .normalization import load_profile, select_form
from .sources import iter_entries, source_path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
REVIEW_STATE = ROOT / "data" / "recovery-review-states.json"
REVIEW_STATUSES = {"unreviewed", "reviewed", "loan-isolated", "suspended", "closed"}


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
    language TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    mtime_ns INTEGER NOT NULL,
    coverage_complete INTEGER NOT NULL,
    entries_seen INTEGER NOT NULL,
    built_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS entries (
    entry_id TEXT PRIMARY KEY,
    language TEXT NOT NULL,
    source_entry_id TEXT NOT NULL,
    headword TEXT NOT NULL,
    romanization TEXT NOT NULL,
    variants_json TEXT NOT NULL,
    pos TEXT NOT NULL,
    gloss TEXT NOT NULL,
    etymology TEXT NOT NULL,
    loan_hint INTEGER NOT NULL,
    form_of INTEGER NOT NULL,
    alternative_of INTEGER NOT NULL,
    form_targets_json TEXT NOT NULL,
    alternative_targets_json TEXT NOT NULL,
    derived_terms_json TEXT NOT NULL,
    related_terms_json TEXT NOT NULL,
    form_resolution_status TEXT NOT NULL,
    selected_input TEXT NOT NULL,
    original_skeleton TEXT NOT NULL,
    romanization_skeleton TEXT NOT NULL,
    skeleton TEXT NOT NULL,
    tokens_json TEXT NOT NULL,
    unknown_original_json TEXT NOT NULL,
    unknown_romanization_json TEXT NOT NULL,
    ambiguities_json TEXT NOT NULL,
    processing_status TEXT NOT NULL,
    morphology_status TEXT NOT NULL,
    review_status TEXT NOT NULL,
    blocker TEXT NOT NULL,
    candidate_count INTEGER NOT NULL,
    licensed_candidate_count INTEGER NOT NULL,
    scope_gap_count INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS entries_language_status ON entries(language, review_status, processing_status);
CREATE INDEX IF NOT EXISTS entries_language_skeleton ON entries(language, skeleton);
CREATE TABLE IF NOT EXISTS candidates (
    entry_id TEXT NOT NULL REFERENCES entries(entry_id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    form TEXT NOT NULL,
    status TEXT NOT NULL,
    positions_json TEXT NOT NULL,
    rule_ids_json TEXT NOT NULL,
    route_flag INTEGER NOT NULL,
    PRIMARY KEY(entry_id, kind, form, status, rule_ids_json, route_flag)
);
CREATE INDEX IF NOT EXISTS candidates_form ON candidates(form, kind, status);
CREATE TABLE IF NOT EXISTS arabic_forms (
    form TEXT NOT NULL,
    kind TEXT NOT NULL,
    reading TEXT NOT NULL,
    PRIMARY KEY(form, kind)
);
CREATE TABLE IF NOT EXISTS network_rules (
    row_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    direction TEXT NOT NULL,
    scopes_json TEXT NOT NULL,
    automation TEXT NOT NULL,
    shift TEXT NOT NULL,
    direction_text TEXT NOT NULL,
    note TEXT NOT NULL
);
"""


def connect(path: Path = DEFAULT_DB, *, create: bool = True) -> sqlite3.Connection:
    if not create and not path.exists():
        raise FileNotFoundError(f"Recovery inventory does not exist: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.execute("PRAGMA temp_store = MEMORY")
    connection.execute("PRAGMA cache_size = -131072")
    connection.executescript(SCHEMA)
    entry_columns = {row[1] for row in connection.execute("PRAGMA table_info(entries)")}
    if "alternative_of" not in entry_columns:
        connection.execute("ALTER TABLE entries ADD COLUMN alternative_of INTEGER NOT NULL DEFAULT 0")
    if "alternative_targets_json" not in entry_columns:
        connection.execute("ALTER TABLE entries ADD COLUMN alternative_targets_json TEXT NOT NULL DEFAULT '[]'")
    ensure_family_schema(connection)
    return connection


def load_review_states(path: Path = REVIEW_STATE) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != 1 or not isinstance(payload.get("entries"), dict):
        raise ValueError(f"Invalid review-state file: {path}")
    entries: dict[str, dict[str, Any]] = payload["entries"]
    for entry_id, state in entries.items():
        status = state.get("status", "")
        if status not in REVIEW_STATUSES:
            raise ValueError(f"Invalid review status for {entry_id}: {status}")
        if status == "suspended" and not state.get("blocker"):
            raise ValueError(f"Suspended entry lacks blocker: {entry_id}")
        if status in {"reviewed", "loan-isolated", "closed"}:
            if not state.get("recovery_review") or not state.get("skeptical_review"):
                raise ValueError(f"Finalized entry lacks both review lenses: {entry_id}")
            skeptic = state["skeptical_review"]
            required = ("loan_screen", "homonym_screen", "source_check", "result")
            if any(key not in skeptic for key in required):
                raise ValueError(f"Incomplete skeptical review for {entry_id}")
    return entries


def install_review_overlay(
    connection: sqlite3.Connection,
    reviews: dict[str, dict[str, Any]] | None = None,
) -> None:
    reviews = load_review_states() if reviews is None else reviews
    connection.execute("CREATE TEMP TABLE IF NOT EXISTS review_overlay (entry_id TEXT PRIMARY KEY, status TEXT NOT NULL)")
    connection.execute("DELETE FROM review_overlay")
    connection.executemany(
        "INSERT INTO review_overlay VALUES (?, ?)",
        [(entry_id, state.get("status", "unreviewed")) for entry_id, state in reviews.items()],
    )


def _install_rules(connection: sqlite3.Connection, rules: list[ShiftRule]) -> None:
    connection.execute("DELETE FROM network_rules")
    connection.executemany(
        "INSERT INTO network_rules VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                rule.row_id,
                rule.kind,
                rule.direction,
                json.dumps(rule.scopes, ensure_ascii=False),
                rule.automation,
                rule.shift,
                rule.direction_text,
                rule.note,
            )
            for rule in rules
        ],
    )


def _candidate_rows(entry_id: str, hits: list[CandidateHit]) -> list[tuple[object, ...]]:
    grouped: dict[tuple[str, str, str, tuple[str, ...], bool], set[str]] = {}
    for hit in hits:
        key = (hit.kind, hit.form, hit.status, hit.rule_ids, hit.route_flag)
        grouped.setdefault(key, set()).add(hit.positions)
    return [
        (
            entry_id,
            kind,
            form,
            status,
            json.dumps(sorted(positions), ensure_ascii=False),
            json.dumps(rule_ids, ensure_ascii=False),
            int(route_flag),
        )
        for (kind, form, status, rule_ids, route_flag), positions in sorted(grouped.items())
    ]


def build_language(
    language: str,
    *,
    db_path: Path = DEFAULT_DB,
    limit: int | None = None,
    root: Path = ROOT,
) -> dict[str, Any]:
    profile = load_profile(language)
    path = source_path(profile, root)
    initial_stat = path.stat()
    rules = compile_network()
    arabic = ArabicInventory.load(root)
    reviews = load_review_states()
    connection = connect(db_path)
    counters: Counter[str] = Counter()
    family_report: dict[str, Any] = {}
    started = datetime.now(timezone.utc).isoformat()
    try:
        with connection:
            clear_language_families(connection, language)
            connection.execute(
                "DELETE FROM candidates AS c WHERE EXISTS ("
                "SELECT 1 FROM entries e WHERE e.entry_id=c.entry_id AND e.language=?"
                ")",
                (language,),
            )
            connection.execute("DELETE FROM entries WHERE language=?", (language,))
            _install_rules(connection, rules)
            connection.execute("DELETE FROM arabic_forms")
            connection.executemany(
                "INSERT INTO arabic_forms VALUES (?, ?, ?)",
                [(form, "root", reading) for form, reading in arabic.roots.items()]
                + [(form, "hollow-root", reading) for form, reading in arabic.roots.items()]
                + [(form, "nucleus", reading) for form, reading in arabic.nuclei.items()],
            )
            for index, entry in enumerate(iter_entries(profile, root), start=1):
                if limit is not None and index > limit:
                    break
                original, romanized, selected, selected_name = select_form(
                    entry.headword, entry.romanization, profile, strict=False
                )
                ambiguities = tuple(dict.fromkeys(original.ambiguities + romanized.ambiguities))
                hits: list[CandidateHit] = []
                unmapped: tuple[str, ...] = ()
                nonlexical = entry.pos in {"character", "symbol", "punct"}
                pure_form = entry.form_of and not entry.alternative_of
                if nonlexical:
                    processing = "ineligible-nonlexical"
                    morphology = "not-applicable-nonlexical"
                elif pure_form:
                    processing = "form-pending-link"
                    morphology = "not-applicable-form"
                elif selected.unknown:
                    processing = "blocked-normalization"
                    morphology = "unknown"
                elif not selected.tokens:
                    processing = "floor-review-required"
                    morphology = "not-applicable-consonant"
                else:
                    hits, unmapped = generate_hits(selected.tokens, language, rules, arabic)
                    processing = (
                        "blocked-mapping" if unmapped
                        else "candidates-generated" if hits
                        else "candidate-search-complete-zero"
                    )
                    morphology = "lemma-surface-ready" if len(selected.tokens) <= 3 else "morphology-review-required"
                review = reviews.get(entry.entry_id, {})
                review_status = review.get("status", "unreviewed")
                blocker = str(review.get("blocker") or "")
                candidate_rows = _candidate_rows(entry.entry_id, hits)
                licensed_count = sum(row[3] == "licensed" for row in candidate_rows)
                scope_gap_count = sum(row[3] == "scope-gap" for row in candidate_rows)
                connection.execute(
                    """INSERT INTO entries (
                    entry_id, language, source_entry_id, headword, romanization, variants_json, pos, gloss,
                    etymology, loan_hint, form_of, alternative_of, form_targets_json,
                    alternative_targets_json,
                    derived_terms_json, related_terms_json,
                    form_resolution_status, selected_input, original_skeleton, romanization_skeleton, skeleton,
                    tokens_json, unknown_original_json, unknown_romanization_json, ambiguities_json,
                    processing_status, morphology_status, review_status, blocker, candidate_count,
                    licensed_candidate_count, scope_gap_count
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        entry.entry_id,
                        language,
                        entry.source_entry_id,
                        entry.headword,
                        entry.romanization,
                        json.dumps(entry.variants[:25] if not pure_form and not nonlexical else (), ensure_ascii=False),
                        entry.pos,
                        entry.gloss[:200] if pure_form or nonlexical else entry.gloss[:500],
                        "" if pure_form or nonlexical else entry.etymology[:1500],
                        int(entry.loan_hint),
                        int(entry.form_of),
                        int(entry.alternative_of),
                        json.dumps(entry.form_targets, ensure_ascii=False),
                        json.dumps(entry.alternative_targets, ensure_ascii=False),
                        json.dumps(entry.derived_terms, ensure_ascii=False),
                        json.dumps(entry.related_terms, ensure_ascii=False),
                        "pending" if entry.form_of or entry.alternative_of else "not-form",
                        selected_name,
                        original.skeleton,
                        romanized.skeleton,
                        selected.skeleton,
                        json.dumps(selected.tokens, ensure_ascii=False),
                        json.dumps(original.unknown, ensure_ascii=False),
                        json.dumps(romanized.unknown, ensure_ascii=False),
                        json.dumps(ambiguities, ensure_ascii=False),
                        processing,
                        morphology,
                        review_status,
                        blocker,
                        len(candidate_rows),
                        licensed_count,
                        scope_gap_count,
                    ),
                )
                if candidate_rows:
                    connection.executemany(
                        "INSERT INTO candidates VALUES (?, ?, ?, ?, ?, ?, ?)",
                        candidate_rows,
                    )
                counters["entries"] += 1
                counters[processing] += 1
                counters[review_status] += 1
                counters["candidate_rows"] += len(candidate_rows)
                counters["loan_hints"] += int(entry.loan_hint)
                counters["ambiguities"] += int(bool(ambiguities))
                counters["unknown_selected"] += int(processing == "blocked-normalization")
                counters["unmapped"] += int(bool(unmapped))
            if not counters["entries"]:
                raise ValueError(f"Source produced no inventory entries: {path}")
            family_report = build_families(connection, language, int(profile["family_max_lemma_count"]))
            stat = path.stat()
            if (stat.st_size, stat.st_mtime_ns) != (initial_stat.st_size, initial_stat.st_mtime_ns):
                raise RuntimeError(f"Source changed while it was being inventoried: {path}")
            connection.execute(
                """INSERT OR REPLACE INTO sources
                (language, source_id, path, size_bytes, mtime_ns, coverage_complete, entries_seen, built_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    language,
                    profile["source"]["id"],
                    path.relative_to(root).as_posix(),
                    stat.st_size,
                    stat.st_mtime_ns,
                    int(limit is None),
                    counters["entries"],
                    started,
                ),
            )
            connection.execute("INSERT OR REPLACE INTO meta VALUES ('schema_version', '5')")
            connection.execute(
                "INSERT OR REPLACE INTO meta VALUES (?, ?)",
                (f"family_metadata_version:{language}", FAMILY_METADATA_VERSION),
            )
            processing_counts = dict(connection.execute(
                "SELECT processing_status, COUNT(*) FROM entries WHERE language=? GROUP BY processing_status",
                (language,),
            ).fetchall())
    finally:
        connection.close()
    return {
        "language": language,
        "database": str(db_path),
        "coverage_complete": limit is None,
        "entries": counters["entries"],
        "candidate_rows": counters["candidate_rows"],
        "loan_hints": counters["loan_hints"],
        "processing": processing_counts,
        "family_layer": family_report,
    }


def upgrade_family_layer_from_v2(
    language: str,
    *,
    source_db: Path,
    db_path: Path = DEFAULT_DB,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Upgrade a complete schema-v2 inventory after proving its retrieval inputs are unchanged."""
    source_db = source_db.resolve()
    db_path = db_path.resolve()
    if source_db == db_path:
        raise ValueError("The schema-v2 source and schema-v5 destination must be different databases")
    if not source_db.exists():
        raise FileNotFoundError(f"Schema-v2 recovery inventory does not exist: {source_db}")

    profile = load_profile(language)
    path = source_path(profile, root)
    initial_stat = path.stat()
    rules = compile_network()
    arabic = ArabicInventory.load(root)
    connection = connect(db_path)
    connection.execute("ATTACH DATABASE ? AS legacy", (str(source_db),))
    started = datetime.now(timezone.utc).isoformat()
    overlay_table = "_v2_family_upgrade_overlay"
    def progress(stage: str) -> None:
        print(f"upgrade-v5[{language}]: {stage}", file=sys.stderr, flush=True)

    progress("start")
    try:
        legacy_meta = dict(connection.execute("SELECT key, value FROM legacy.meta"))
        if legacy_meta.get("schema_version") != "2":
            raise ValueError(f"Expected a schema-v2 inventory, found {legacy_meta.get('schema_version')!r}")
        source_row = connection.execute(
            "SELECT source_id, path, size_bytes, mtime_ns, coverage_complete, entries_seen "
            "FROM legacy.sources WHERE language=?",
            (language,),
        ).fetchone()
        if source_row is None or not source_row[4]:
            raise ValueError(f"Legacy inventory has no complete source record for {language}")
        source_id, stored_path, size_bytes, mtime_ns, _, entries_seen = source_row
        if source_id != profile["source"]["id"] or stored_path != profile["source"]["path"]:
            raise ValueError(f"Legacy source identity differs from the current profile for {language}")
        if (size_bytes, mtime_ns) != (initial_stat.st_size, initial_stat.st_mtime_ns):
            raise ValueError(f"Legacy source fingerprint differs from the current snapshot for {language}")

        legacy_rules = [
            (row_id, kind, direction, tuple(json.loads(scopes)), automation, shift, direction_text, note)
            for row_id, kind, direction, scopes, automation, shift, direction_text, note
            in connection.execute(
                "SELECT row_id, kind, direction, scopes_json, automation, shift, direction_text, note "
                "FROM legacy.network_rules ORDER BY row_id"
            )
        ]
        current_rules = sorted([
            (
                rule.row_id, rule.kind, rule.direction, tuple(rule.scopes), rule.automation,
                rule.shift, rule.direction_text, rule.note,
            )
            for rule in rules
        ])
        if legacy_rules != current_rules:
            raise ValueError("Legacy candidate rows were built with a different compiled shift network")

        current_arabic_forms = sorted(
            [(form, "root", reading) for form, reading in arabic.roots.items()]
            + [(form, "hollow-root", reading) for form, reading in arabic.roots.items()]
            + [(form, "nucleus", reading) for form, reading in arabic.nuclei.items()]
        )
        legacy_arabic_forms = connection.execute(
            "SELECT form, kind, reading FROM legacy.arabic_forms ORDER BY form, kind, reading"
        ).fetchall()
        if legacy_arabic_forms != current_arabic_forms:
            raise ValueError("Legacy candidate rows were built with a different Arabic inventory")
        progress("pinned-inputs-proved")

        with connection:
            connection.execute(f"DROP TABLE IF EXISTS {overlay_table}")
            connection.execute(f"""
                CREATE TABLE {overlay_table} (
                    entry_id TEXT PRIMARY KEY,
                    form_of INTEGER NOT NULL,
                    alternative_of INTEGER NOT NULL,
                    form_targets_json TEXT NOT NULL,
                    alternative_targets_json TEXT NOT NULL,
                    derived_terms_json TEXT NOT NULL,
                    related_terms_json TEXT NOT NULL,
                    selected_input TEXT NOT NULL,
                    original_skeleton TEXT NOT NULL,
                    romanization_skeleton TEXT NOT NULL,
                    skeleton TEXT NOT NULL,
                    tokens_json TEXT NOT NULL,
                    unknown_original_json TEXT NOT NULL,
                    unknown_romanization_json TEXT NOT NULL,
                    ambiguities_json TEXT NOT NULL,
                    headword TEXT NOT NULL,
                    romanization TEXT NOT NULL,
                    variants_json TEXT NOT NULL,
                    gloss TEXT NOT NULL,
                    etymology TEXT NOT NULL
                )
            """)
            batch: list[tuple[object, ...]] = []
            seen = 0
            for entry in iter_entries(profile, root):
                original, romanized, selected, selected_name = select_form(
                    entry.headword, entry.romanization, profile, strict=False
                )
                ambiguities = tuple(dict.fromkeys(original.ambiguities + romanized.ambiguities))
                batch.append((
                    entry.entry_id,
                    int(entry.form_of),
                    int(entry.alternative_of),
                    json.dumps(entry.form_targets, ensure_ascii=False),
                    json.dumps(entry.alternative_targets, ensure_ascii=False),
                    json.dumps(entry.derived_terms, ensure_ascii=False),
                    json.dumps(entry.related_terms, ensure_ascii=False),
                    selected_name,
                    original.skeleton,
                    romanized.skeleton,
                    selected.skeleton,
                    json.dumps(selected.tokens, ensure_ascii=False),
                    json.dumps(original.unknown, ensure_ascii=False),
                    json.dumps(romanized.unknown, ensure_ascii=False),
                    json.dumps(ambiguities, ensure_ascii=False),
                    entry.headword,
                    entry.romanization,
                    json.dumps(entry.variants[:25], ensure_ascii=False),
                    entry.gloss[:500],
                    entry.etymology[:1500],
                ))
                seen += 1
                if len(batch) >= 5000:
                    connection.executemany(
                        f"INSERT INTO {overlay_table} VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch
                    )
                    batch.clear()
            if batch:
                connection.executemany(
                    f"INSERT INTO {overlay_table} VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", batch
                )
            if seen != entries_seen:
                raise ValueError(f"Current source yielded {seen} entries; legacy inventory recorded {entries_seen}")
            progress(f"source-overlay-built:{seen}")

            missing_current = connection.execute(
                f"SELECT COUNT(*) FROM legacy.entries e LEFT JOIN {overlay_table} o ON o.entry_id=e.entry_id "
                "WHERE e.language=? AND o.entry_id IS NULL",
                (language,),
            ).fetchone()[0]
            missing_legacy = connection.execute(
                f"SELECT COUNT(*) FROM {overlay_table} o LEFT JOIN legacy.entries e ON e.entry_id=o.entry_id "
                "WHERE e.entry_id IS NULL"
            ).fetchone()[0]
            normalization_mismatches = connection.execute(f"""
                SELECT COUNT(*) FROM {overlay_table} o
                JOIN legacy.entries e ON e.entry_id=o.entry_id
                WHERE e.language<>? OR e.headword<>o.headword OR e.romanization<>o.romanization
                   OR e.selected_input<>o.selected_input OR e.original_skeleton<>o.original_skeleton
                   OR e.romanization_skeleton<>o.romanization_skeleton OR e.skeleton<>o.skeleton
                   OR e.tokens_json<>o.tokens_json OR e.unknown_original_json<>o.unknown_original_json
                   OR e.unknown_romanization_json<>o.unknown_romanization_json
                   OR e.ambiguities_json<>o.ambiguities_json
            """, (language,)).fetchone()[0]
            if missing_current or missing_legacy or normalization_mismatches:
                raise ValueError(
                    "Legacy reuse proof failed: "
                    f"missing-current={missing_current}, missing-legacy={missing_legacy}, "
                    f"normalization-mismatches={normalization_mismatches}"
                )
            progress("entry-identity-and-normalization-proved")

            destination_missing = connection.execute(
                f"SELECT COUNT(*) FROM legacy.entries e LEFT JOIN entries d ON d.entry_id=e.entry_id "
                "WHERE e.language=? AND d.entry_id IS NULL",
                (language,),
            ).fetchone()[0]
            destination_extra = connection.execute(
                "SELECT COUNT(*) FROM entries d LEFT JOIN legacy.entries e ON e.entry_id=d.entry_id "
                "WHERE d.language=? AND e.entry_id IS NULL",
                (language,),
            ).fetchone()[0]
            if destination_missing or destination_extra:
                raise ValueError(
                    "Destination language slice cannot be upgraded in place: "
                    f"missing={destination_missing}, extra={destination_extra}"
                )
            progress("destination-entry-set-proved")

            # Maintaining the global lookup index row by row dominates large
            # migrations. The primary key still guards every copied candidate;
            # rebuild the secondary lookup index once after the bulk copy.
            connection.execute("DROP INDEX IF EXISTS candidates_form")
            clear_language_families(connection, language)
            connection.execute(
                "DELETE FROM candidates AS c WHERE EXISTS ("
                "SELECT 1 FROM entries e WHERE e.entry_id=c.entry_id AND e.language=?"
                ")",
                (language,),
            )
            progress("old-candidates-cleared")
            _install_rules(connection, rules)
            connection.execute("DELETE FROM arabic_forms")
            connection.executemany("INSERT INTO arabic_forms VALUES (?, ?, ?)", current_arabic_forms)
            connection.execute(f"""
                UPDATE entries AS d SET
                    language=e.language,
                    source_entry_id=e.source_entry_id,
                    headword=e.headword,
                    romanization=e.romanization,
                    variants_json=CASE WHEN o.form_of=1 AND o.alternative_of=0 THEN '[]' ELSE o.variants_json END,
                    pos=e.pos,
                    gloss=CASE WHEN o.form_of=1 AND o.alternative_of=0 THEN substr(o.gloss,1,200) ELSE o.gloss END,
                    etymology=CASE WHEN o.form_of=1 AND o.alternative_of=0 THEN '' ELSE o.etymology END,
                    loan_hint=e.loan_hint,
                    form_of=o.form_of,
                    alternative_of=o.alternative_of,
                    form_targets_json=o.form_targets_json,
                    alternative_targets_json=o.alternative_targets_json,
                    derived_terms_json=o.derived_terms_json,
                    related_terms_json=o.related_terms_json,
                    form_resolution_status=CASE WHEN o.form_of=1 OR o.alternative_of=1 THEN 'pending' ELSE 'not-form' END,
                    selected_input=e.selected_input,
                    original_skeleton=e.original_skeleton,
                    romanization_skeleton=e.romanization_skeleton,
                    skeleton=e.skeleton,
                    tokens_json=e.tokens_json,
                    unknown_original_json=e.unknown_original_json,
                    unknown_romanization_json=e.unknown_romanization_json,
                    ambiguities_json=e.ambiguities_json,
                    processing_status=CASE WHEN o.form_of=1 AND o.alternative_of=0 THEN 'form-pending-link' ELSE e.processing_status END,
                    morphology_status=CASE WHEN o.form_of=1 AND o.alternative_of=0 THEN 'not-applicable-form' ELSE e.morphology_status END,
                    review_status=e.review_status,
                    blocker=e.blocker,
                    candidate_count=CASE WHEN o.form_of=1 AND o.alternative_of=0 THEN 0 ELSE e.candidate_count END,
                    licensed_candidate_count=CASE WHEN o.form_of=1 AND o.alternative_of=0 THEN 0 ELSE e.licensed_candidate_count END,
                    scope_gap_count=CASE WHEN o.form_of=1 AND o.alternative_of=0 THEN 0 ELSE e.scope_gap_count END
                FROM legacy.entries AS e JOIN {overlay_table} AS o ON o.entry_id=e.entry_id
                WHERE d.entry_id=e.entry_id AND e.language=?
            """, (language,))
            progress("entries-updated-in-place")
            # Drive this join from the candidate table. It is already ordered
            # by entry_id, so one sequential pass is dramatically cheaper than
            # one legacy-index seek for every source entry.
            connection.execute(f"""
                INSERT INTO candidates
                SELECT c.entry_id, c.kind, c.form, c.status, c.positions_json, c.rule_ids_json, c.route_flag
                FROM legacy.candidates c CROSS JOIN {overlay_table} o ON o.entry_id=c.entry_id
                WHERE o.form_of=0
            """)
            progress("legacy-candidates-copied")
            for entry_id, tokens_json, selected_input, unknown_original_json, unknown_romanization_json, pos in connection.execute(
                "SELECT entry_id, tokens_json, selected_input, unknown_original_json, unknown_romanization_json, pos "
                "FROM entries WHERE language=? AND form_of=1 AND alternative_of=1",
                (language,),
            ).fetchall():
                tokens = tuple(json.loads(tokens_json))
                selected_unknown = tuple(json.loads(
                    unknown_romanization_json if selected_input == "romanization" else unknown_original_json
                ))
                if pos in {"character", "symbol", "punct"}:
                    processing = "ineligible-nonlexical"
                    morphology = "not-applicable-nonlexical"
                    hits, unmapped = [], ()
                elif selected_unknown:
                    processing = "blocked-normalization"
                    morphology = "unknown"
                    hits, unmapped = [], ()
                elif not tokens:
                    processing = "floor-review-required"
                    morphology = "not-applicable-consonant"
                    hits, unmapped = [], ()
                else:
                    hits, unmapped = generate_hits(tokens, language, rules, arabic)
                    processing = (
                        "blocked-mapping" if unmapped else "candidates-generated" if hits
                        else "candidate-search-complete-zero"
                    )
                    morphology = "lemma-surface-ready" if len(tokens) <= 3 else "morphology-review-required"
                candidate_rows_for_entry = _candidate_rows(entry_id, hits)
                if candidate_rows_for_entry:
                    connection.executemany("INSERT INTO candidates VALUES (?, ?, ?, ?, ?, ?, ?)", candidate_rows_for_entry)
                connection.execute(
                    "UPDATE entries SET processing_status=?, morphology_status=?, candidate_count=?, "
                    "licensed_candidate_count=?, scope_gap_count=? WHERE entry_id=?",
                    (
                        processing,
                        morphology,
                        len(candidate_rows_for_entry),
                        sum(row[3] == "licensed" for row in candidate_rows_for_entry),
                        sum(row[3] == "scope-gap" for row in candidate_rows_for_entry),
                        entry_id,
                    ),
                )
            progress("mixed-form-alternatives-regenerated")
            connection.execute("CREATE INDEX candidates_form ON candidates(form, kind, status)")
            progress("candidate-lookup-index-built")
            family_report = build_families(connection, language, int(profile["family_max_lemma_count"]))
            progress("families-built")
            processing_counts = dict(connection.execute(
                "SELECT processing_status, COUNT(*) FROM entries WHERE language=? GROUP BY processing_status",
                (language,),
            ).fetchall())
            candidate_rows = connection.execute(
                "SELECT COUNT(*) FROM candidates c CROSS JOIN entries e ON e.entry_id=c.entry_id "
                "WHERE e.language=?",
                (language,),
            ).fetchone()[0]
            counted_candidates = connection.execute(
                "SELECT COALESCE(SUM(candidate_count), 0) FROM entries WHERE language=?", (language,)
            ).fetchone()[0]
            if candidate_rows != counted_candidates:
                raise ValueError(
                    f"Migrated candidate count mismatch: rows={candidate_rows}, entries={counted_candidates}"
                )
            progress("candidate-count-proved")
            current_stat = path.stat()
            if (current_stat.st_size, current_stat.st_mtime_ns) != (initial_stat.st_size, initial_stat.st_mtime_ns):
                raise RuntimeError(f"Source changed while it was being upgraded: {path}")
            connection.execute(
                "INSERT OR REPLACE INTO sources VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    language, source_id, str(path.relative_to(root)).replace("\\", "/"),
                    current_stat.st_size, current_stat.st_mtime_ns, 1, seen, started,
                ),
            )
            connection.execute("INSERT OR REPLACE INTO meta VALUES ('schema_version', '5')")
            connection.execute(
                "INSERT OR REPLACE INTO meta VALUES (?, ?)",
                (f"family_metadata_version:{language}", FAMILY_METADATA_VERSION),
            )
            loan_hints = connection.execute(
                "SELECT COALESCE(SUM(loan_hint), 0) FROM entries WHERE language=?", (language,)
            ).fetchone()[0]
            connection.execute(f"DROP TABLE {overlay_table}")
            progress("ready-to-commit")
        progress("committed")
        return {
            "language": language,
            "database": str(db_path),
            "coverage_complete": True,
            "entries": seen,
            "candidate_rows": candidate_rows,
            "loan_hints": loan_hints,
            "processing": processing_counts,
            "family_layer": family_report,
            "reuse_proof": {
                "legacy_schema": 2,
                "source_fingerprint": "identical",
                "entry_identity": "identical",
                "normalization": "identical",
                "shift_network": "identical",
                "arabic_inventory": "identical",
            },
        }
    finally:
        try:
            connection.execute("DETACH DATABASE legacy")
        finally:
            connection.close()


def refresh_family_metadata(
    language: str,
    *,
    db_path: Path = DEFAULT_DB,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Refresh typed family links and recover candidate-bearing mixed form/alternative entries."""
    profile = load_profile(language)
    path = source_path(profile, root)
    initial_stat = path.stat()
    rules = compile_network()
    arabic = ArabicInventory.load(root)
    connection = connect(db_path, create=False)
    overlay = "_family_metadata_refresh"
    try:
        source_row = connection.execute(
            "SELECT source_id, path, size_bytes, mtime_ns, coverage_complete, entries_seen "
            "FROM sources WHERE language=?",
            (language,),
        ).fetchone()
        if source_row is None or not source_row[4]:
            raise ValueError(f"Inventory has no complete source record for {language}")
        if source_row[0] != profile["source"]["id"] or source_row[1] != profile["source"]["path"]:
            raise ValueError(f"Inventory source identity differs from the current profile for {language}")
        if (source_row[2], source_row[3]) != (initial_stat.st_size, initial_stat.st_mtime_ns):
            raise ValueError(f"Inventory source fingerprint differs from the current snapshot for {language}")
        with connection:
            connection.execute(f"DROP TABLE IF EXISTS {overlay}")
            connection.execute(f"""
                CREATE TEMP TABLE {overlay} (
                    entry_id TEXT PRIMARY KEY,
                    headword TEXT NOT NULL,
                    romanization TEXT NOT NULL,
                    form_of INTEGER NOT NULL,
                    alternative_of INTEGER NOT NULL,
                    form_targets_json TEXT NOT NULL,
                    alternative_targets_json TEXT NOT NULL,
                    variants_json TEXT NOT NULL,
                    gloss TEXT NOT NULL,
                    etymology TEXT NOT NULL
                )
            """)
            batch: list[tuple[object, ...]] = []
            seen = 0
            for entry in iter_entries(profile, root):
                batch.append((
                    entry.entry_id,
                    entry.headword,
                    entry.romanization,
                    int(entry.form_of),
                    int(entry.alternative_of),
                    json.dumps(entry.form_targets, ensure_ascii=False),
                    json.dumps(entry.alternative_targets, ensure_ascii=False),
                    json.dumps(entry.variants[:25], ensure_ascii=False),
                    entry.gloss[:500],
                    entry.etymology[:1500],
                ))
                seen += 1
                if len(batch) >= 5000:
                    connection.executemany(f"INSERT INTO {overlay} VALUES (?,?,?,?,?,?,?,?,?,?)", batch)
                    batch.clear()
            if batch:
                connection.executemany(f"INSERT INTO {overlay} VALUES (?,?,?,?,?,?,?,?,?,?)", batch)
            missing_current = connection.execute(
                f"SELECT COUNT(*) FROM entries e LEFT JOIN {overlay} o ON o.entry_id=e.entry_id "
                "WHERE e.language=? AND o.entry_id IS NULL",
                (language,),
            ).fetchone()[0]
            missing_inventory = connection.execute(
                f"SELECT COUNT(*) FROM {overlay} o LEFT JOIN entries e ON e.entry_id=o.entry_id "
                "WHERE e.entry_id IS NULL"
            ).fetchone()[0]
            identity_mismatches = connection.execute(
                f"SELECT COUNT(*) FROM entries e JOIN {overlay} o ON o.entry_id=e.entry_id "
                "WHERE e.language<>? OR e.headword<>o.headword OR e.romanization<>o.romanization",
                (language,),
            ).fetchone()[0]
            if seen != source_row[5] or missing_current or missing_inventory or identity_mismatches:
                raise ValueError(
                    "Family metadata refresh identity proof failed: "
                    f"seen={seen}/{source_row[5]}, missing-current={missing_current}, "
                    f"missing-inventory={missing_inventory}, identity-mismatches={identity_mismatches}"
                )
            connection.execute(f"""
                UPDATE entries AS e SET
                    form_of=o.form_of,
                    alternative_of=o.alternative_of,
                    form_targets_json=o.form_targets_json,
                    alternative_targets_json=o.alternative_targets_json,
                    variants_json=CASE WHEN o.form_of=1 AND o.alternative_of=0 THEN '[]' ELSE o.variants_json END,
                    gloss=CASE WHEN o.form_of=1 AND o.alternative_of=0 THEN substr(o.gloss,1,200) ELSE o.gloss END,
                    etymology=CASE WHEN o.form_of=1 AND o.alternative_of=0 THEN '' ELSE o.etymology END,
                    form_resolution_status=CASE WHEN o.form_of=1 OR o.alternative_of=1 THEN 'pending' ELSE 'not-form' END,
                    processing_status=CASE WHEN o.form_of=1 AND o.alternative_of=0 THEN 'form-pending-link' ELSE e.processing_status END,
                    morphology_status=CASE WHEN o.form_of=1 AND o.alternative_of=0 THEN 'not-applicable-form' ELSE e.morphology_status END,
                    candidate_count=CASE WHEN o.form_of=1 AND o.alternative_of=0 THEN 0 ELSE e.candidate_count END,
                    licensed_candidate_count=CASE WHEN o.form_of=1 AND o.alternative_of=0 THEN 0 ELSE e.licensed_candidate_count END,
                    scope_gap_count=CASE WHEN o.form_of=1 AND o.alternative_of=0 THEN 0 ELSE e.scope_gap_count END
                FROM {overlay} AS o WHERE e.entry_id=o.entry_id AND e.language=?
            """, (language,))
            connection.execute(
                "DELETE FROM candidates AS c WHERE EXISTS (SELECT 1 FROM entries e "
                "WHERE e.entry_id=c.entry_id AND e.language=? AND e.form_of=1)",
                (language,),
            )
            mixed = connection.execute(
                "SELECT entry_id, tokens_json, selected_input, unknown_original_json, unknown_romanization_json, pos "
                "FROM entries WHERE language=? AND form_of=1 AND alternative_of=1",
                (language,),
            ).fetchall()
            for entry_id, tokens_json, selected_input, unknown_original_json, unknown_romanization_json, pos in mixed:
                tokens = tuple(json.loads(tokens_json))
                selected_unknown = tuple(json.loads(
                    unknown_romanization_json if selected_input == "romanization" else unknown_original_json
                ))
                if pos in {"character", "symbol", "punct"}:
                    processing, morphology, hits = "ineligible-nonlexical", "not-applicable-nonlexical", []
                elif selected_unknown:
                    processing, morphology, hits = "blocked-normalization", "unknown", []
                elif not tokens:
                    processing, morphology, hits = "floor-review-required", "not-applicable-consonant", []
                else:
                    hits, unmapped = generate_hits(tokens, language, rules, arabic)
                    processing = (
                        "blocked-mapping" if unmapped else "candidates-generated" if hits
                        else "candidate-search-complete-zero"
                    )
                    morphology = "lemma-surface-ready" if len(tokens) <= 3 else "morphology-review-required"
                candidate_rows_for_entry = _candidate_rows(entry_id, hits)
                if candidate_rows_for_entry:
                    connection.executemany("INSERT INTO candidates VALUES (?, ?, ?, ?, ?, ?, ?)", candidate_rows_for_entry)
                connection.execute(
                    "UPDATE entries SET processing_status=?, morphology_status=?, candidate_count=?, "
                    "licensed_candidate_count=?, scope_gap_count=? WHERE entry_id=?",
                    (
                        processing,
                        morphology,
                        len(candidate_rows_for_entry),
                        sum(row[3] == "licensed" for row in candidate_rows_for_entry),
                        sum(row[3] == "scope-gap" for row in candidate_rows_for_entry),
                        entry_id,
                    ),
                )
            family_report = build_families(connection, language, int(profile["family_max_lemma_count"]))
            current_stat = path.stat()
            if (current_stat.st_size, current_stat.st_mtime_ns) != (initial_stat.st_size, initial_stat.st_mtime_ns):
                raise RuntimeError(f"Source changed while family metadata was refreshed: {path}")
            connection.execute("INSERT OR REPLACE INTO meta VALUES ('schema_version', '5')")
            connection.execute(
                "INSERT OR REPLACE INTO meta VALUES (?, ?)",
                (f"family_metadata_version:{language}", FAMILY_METADATA_VERSION),
            )
            connection.execute(f"DROP TABLE {overlay}")
        return {
            "language": language,
            "entries": seen,
            "mixed_form_alternatives": len(mixed),
            "family_layer": family_report,
            "identity_proof": "identical",
            "source_fingerprint": "identical",
        }
    finally:
        connection.close()


def summary(db_path: Path = DEFAULT_DB, language: str | None = None) -> dict[str, Any]:
    connection = connect(db_path, create=False)
    try:
        install_review_overlay(connection)
        where = " WHERE e.language=?" if language else ""
        params = (language,) if language else ()
        totals = dict(connection.execute(
            f"SELECT e.processing_status, COUNT(*) FROM entries e{where} GROUP BY e.processing_status", params
        ).fetchall())
        total_row = connection.execute(
            "SELECT COUNT(*), COALESCE(SUM(e.candidate_count), 0), "
            "COALESCE(SUM(CASE WHEN e.candidate_count > 0 THEN 1 ELSE 0 END), 0), "
            "COALESCE(SUM(e.loan_hint), 0), "
            "COALESCE(SUM(CASE WHEN e.morphology_status='morphology-review-required' THEN 1 ELSE 0 END), 0) "
            f"FROM entries e{where}", params
        ).fetchone()
        reviews = dict(connection.execute(
            "SELECT COALESCE(o.status, 'unreviewed'), COUNT(*) FROM entries e "
            "LEFT JOIN review_overlay o ON o.entry_id=e.entry_id"
            f"{where} GROUP BY COALESCE(o.status, 'unreviewed')", params
        ).fetchall())
        sources = [dict(zip(
            ("language", "source_id", "path", "size_bytes", "coverage_complete", "entries_seen", "built_at"), row
        )) for row in connection.execute(
            "SELECT language, source_id, path, size_bytes, coverage_complete, entries_seen, built_at FROM sources"
            + (" WHERE language=?" if language else " ORDER BY language"), params
        )]
        pending = reviews.get("unreviewed", 0)
        families = family_summary(connection, language)
        return {
            "sources": sources,
            "totals": dict(zip(
                ("entries", "candidate_paths", "candidate_bearing_entries", "loan_hints", "morphology_review_entries"),
                total_row,
            )),
            "processing": totals,
            "family_layer": families,
            "reviews": reviews,
            "remaining_unreviewed": pending,
        }
    finally:
        connection.close()


def verify_inventory(db_path: Path = DEFAULT_DB, root: Path = ROOT) -> dict[str, Any]:
    connection = connect(db_path, create=False)
    problems: list[str] = []
    report: dict[str, Any] = {"database": str(db_path), "sources": []}
    try:
        quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
        report["sqlite_quick_check"] = quick_check
        if quick_check != "ok":
            problems.append(f"SQLite quick_check failed: {quick_check}")
        metadata = dict(connection.execute("SELECT key, value FROM meta"))
        if metadata.get("schema_version") != "5":
            problems.append(f"unexpected schema version: {metadata.get('schema_version')!r}")
        rule_count = connection.execute("SELECT COUNT(*) FROM network_rules").fetchone()[0]
        if rule_count != 42:
            problems.append(f"network rule count is {rule_count}, expected 42")
        report["network_rules"] = rule_count

        source_rows = connection.execute(
            "SELECT language, path, size_bytes, mtime_ns, coverage_complete, entries_seen FROM sources ORDER BY language"
        ).fetchall()
        if not source_rows:
            problems.append("inventory has no source records")
        for language, relative_path, size_bytes, mtime_ns, complete, entries_seen in source_rows:
            actual_entries = connection.execute(
                "SELECT COUNT(*) FROM entries WHERE language=?", (language,)
            ).fetchone()[0]
            item = {
                "language": language,
                "path": relative_path,
                "coverage_complete": bool(complete),
                "entries_seen": entries_seen,
                "entries_in_database": actual_entries,
            }
            source = root / relative_path
            if not complete:
                problems.append(f"{language}: source coverage is incomplete")
            profile = load_profile(language)
            family_limit = int(profile["family_max_lemma_count"])
            family_version = metadata.get(f"family_metadata_version:{language}")
            item["family_metadata_version"] = family_version
            item["family_max_lemma_count_allowed"] = family_limit
            if family_version != FAMILY_METADATA_VERSION:
                problems.append(f"{language}: typed family metadata has not been refreshed")
            if actual_entries != entries_seen:
                problems.append(f"{language}: source count {entries_seen} != database count {actual_entries}")
            if not source.exists():
                problems.append(f"{language}: source is missing: {source}")
            else:
                stat = source.stat()
                unchanged = (stat.st_size, stat.st_mtime_ns) == (size_bytes, mtime_ns)
                item["source_unchanged"] = unchanged
                if not unchanged:
                    problems.append(f"{language}: source size or modification time changed after inventory")
            report["sources"].append(item)

        oversized_families = []
        for language, anchor, lemma_count in connection.execute(
            "SELECT f.language, f.anchor_headword, f.lemma_count FROM families f "
            "JOIN (SELECT language, MAX(lemma_count) AS maximum FROM families GROUP BY language) m "
            "ON m.language=f.language AND m.maximum=f.lemma_count ORDER BY f.language, f.family_id"
        ):
            family_limit = int(load_profile(language)["family_max_lemma_count"])
            if lemma_count > family_limit:
                oversized_families.append({
                    "language": language,
                    "anchor_headword": anchor,
                    "lemma_count": lemma_count,
                    "allowed": family_limit,
                })
        report["oversized_families"] = oversized_families
        if oversized_families:
            problems.append(f"{len(oversized_families)} languages exceed their lexical-family lemma limit")

        blocked = dict(connection.execute(
            "SELECT processing_status, COUNT(*) FROM entries "
            "WHERE processing_status IN ('blocked-normalization', 'blocked-mapping') GROUP BY processing_status"
        ).fetchall())
        report["blocked"] = blocked
        if blocked:
            problems.append(f"blocked automatic processing states remain: {blocked}")

        mismatched_candidates = connection.execute(
            "SELECT COUNT(*) FROM entries e LEFT JOIN "
            "(SELECT entry_id, COUNT(*) AS amount FROM candidates GROUP BY entry_id) c ON c.entry_id=e.entry_id "
            "WHERE e.candidate_count != COALESCE(c.amount, 0)"
        ).fetchone()[0]
        report["candidate_count_mismatches"] = mismatched_candidates
        if mismatched_candidates:
            problems.append(f"{mismatched_candidates} entries have stale candidate counts")

        familyless_entries = connection.execute(
            "SELECT COUNT(*) FROM entries e LEFT JOIN family_members fm ON fm.entry_id=e.entry_id "
            "WHERE fm.entry_id IS NULL"
        ).fetchone()[0]
        report["entries_without_family"] = familyless_entries
        if familyless_entries:
            problems.append(f"{familyless_entries} entries have no lexical-family membership")
        stale_family_counts = connection.execute(
            "SELECT COUNT(*) FROM families f LEFT JOIN "
            "(SELECT family_id, COUNT(*) AS amount FROM family_members GROUP BY family_id) m ON m.family_id=f.family_id "
            "WHERE f.member_count != COALESCE(m.amount, 0)"
        ).fetchone()[0]
        report["family_member_count_mismatches"] = stale_family_counts
        if stale_family_counts:
            problems.append(f"{stale_family_counts} families have stale member counts")
        forms_without_links = connection.execute(
            "SELECT COUNT(*) FROM entries e WHERE (e.form_of=1 OR e.alternative_of=1) AND NOT EXISTS "
            "(SELECT 1 FROM form_links fl WHERE fl.form_entry_id=e.entry_id)"
        ).fetchone()[0]
        report["forms_without_link_record"] = forms_without_links
        if forms_without_links:
            problems.append(f"{forms_without_links} form/alternative rows lack an explicit link or orphan record")
        pending_forms = connection.execute(
            "SELECT COUNT(*) FROM entries WHERE (form_of=1 OR alternative_of=1) "
            "AND form_resolution_status='pending'"
        ).fetchone()[0]
        report["forms_pending_resolution"] = pending_forms
        if pending_forms:
            problems.append(f"{pending_forms} forms remain in a pending resolution state")
        report["form_resolution_states"] = dict(connection.execute(
            "SELECT form_resolution_status, COUNT(*) FROM entries WHERE form_of=1 OR alternative_of=1 "
            "GROUP BY form_resolution_status"
        ).fetchall())
        candidate_bearing_pure_forms = connection.execute(
            "SELECT COUNT(*) FROM entries WHERE form_of=1 AND alternative_of=0 AND candidate_count<>0"
        ).fetchone()[0]
        report["pure_forms_with_candidates"] = candidate_bearing_pure_forms
        if candidate_bearing_pure_forms:
            problems.append(f"{candidate_bearing_pure_forms} pure inflection rows carry independent candidates")

        install_review_overlay(connection)
        orphaned_reviews = [row[0] for row in connection.execute(
            "SELECT o.entry_id FROM review_overlay o LEFT JOIN entries e ON e.entry_id=o.entry_id "
            "WHERE e.entry_id IS NULL ORDER BY o.entry_id"
        )]
        report["orphaned_review_states"] = orphaned_reviews
        if orphaned_reviews:
            problems.append(f"{len(orphaned_reviews)} review states have no inventory entry")
        family_reviews = load_family_review_states()
        known_families = set(row[0] for row in connection.execute("SELECT family_id FROM families"))
        orphaned_family_reviews = sorted(set(family_reviews["families"]) - known_families)
        report["orphaned_family_review_states"] = orphaned_family_reviews
        if orphaned_family_reviews:
            problems.append(f"{len(orphaned_family_reviews)} family review states have no family")
        invalid_overrides = []
        for entry_id, override in family_reviews["member_overrides"].items():
            row = connection.execute(
                "SELECT family_id FROM family_members WHERE entry_id=?", (entry_id,)
            ).fetchone()
            if row is None or row[0] != override["family_id"]:
                invalid_overrides.append(entry_id)
        report["invalid_member_overrides"] = sorted(invalid_overrides)
        if invalid_overrides:
            problems.append(f"{len(invalid_overrides)} member overrides do not match family membership")
    finally:
        connection.close()
    report["problems"] = problems
    report["passed"] = not problems
    return report


def profile_check(language: str, *, sample: int = 1000, root: Path = ROOT) -> dict[str, Any]:
    profile = load_profile(language)
    checked = 0
    empty_skeletons = 0
    nonlexical_entries = 0
    failures: list[dict[str, object]] = []
    for entry in iter_entries(profile, root):
        if checked >= sample:
            break
        checked += 1
        _, _, selected, selected_name = select_form(entry.headword, entry.romanization, profile, strict=False)
        if entry.pos in {"character", "symbol", "punct"}:
            nonlexical_entries += 1
            continue
        empty_skeletons += int(not selected.tokens)
        if selected.unknown:
            failures.append({
                "entry_id": entry.entry_id,
                "headword": entry.headword,
                "selected_input": selected_name,
                "unknown": selected.unknown,
            })
    return {
        "language": language,
        "sample": checked,
        "unknown_failures": failures,
        "empty_skeletons_recorded": empty_skeletons,
        "nonlexical_entries_recorded": nonlexical_entries,
        "passed": not failures,
    }


def review_queue(db_path: Path, lens: str, language: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    reviews = load_review_states()
    connection = connect(db_path, create=False)
    try:
        clauses = ["candidate_count > 0"]
        params: list[object] = []
        if language:
            clauses.append("language=?")
            params.append(language)
        rows = connection.execute(
            "SELECT entry_id, language, headword, gloss, candidate_count, loan_hint "
            f"FROM entries WHERE {' AND '.join(clauses)} ORDER BY language, entry_id LIMIT ?",
            (*params, limit * 20),
        )
        result = []
        for row in rows:
            state = reviews.get(row[0], {})
            missing = not state.get("recovery_review") if lens == "recovery" else (
                bool(state.get("recovery_review")) and not state.get("skeptical_review")
            )
            if missing:
                item = dict(zip(("entry_id", "language", "headword", "gloss", "candidate_count", "loan_hint"), row))
                item["review_status"] = state.get("status", "unreviewed")
                result.append(item)
            if len(result) >= limit:
                break
        return result
    finally:
        connection.close()
