from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .candidates import ArabicInventory, CandidateHit, generate_hits
from .network import ShiftRule, compile_network
from .normalization import load_profile, select_form
from .sources import iter_entries, source_path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v4.sqlite"
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
    started = datetime.now(timezone.utc).isoformat()
    try:
        with connection:
            connection.execute("DELETE FROM candidates WHERE entry_id IN (SELECT entry_id FROM entries WHERE language=?)", (language,))
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
                if nonlexical:
                    processing = "ineligible-nonlexical"
                    morphology = "not-applicable-nonlexical"
                elif entry.form_of:
                    processing = "ineligible-form"
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
                    """INSERT INTO entries VALUES (
                    ?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?
                    )""",
                    (
                        entry.entry_id,
                        language,
                        entry.source_entry_id,
                        entry.headword,
                        entry.romanization,
                        json.dumps(entry.variants[:25] if not entry.form_of and not nonlexical else (), ensure_ascii=False),
                        entry.pos,
                        entry.gloss[:200] if entry.form_of or nonlexical else entry.gloss[:500],
                        "" if entry.form_of or nonlexical else entry.etymology[:1500],
                        int(entry.loan_hint),
                        int(entry.form_of),
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
            connection.execute("INSERT OR REPLACE INTO meta VALUES ('schema_version', '2')")
    finally:
        connection.close()
    return {
        "language": language,
        "database": str(db_path),
        "coverage_complete": limit is None,
        **dict(counters),
    }


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
        return {
            "sources": sources,
            "totals": dict(zip(
                ("entries", "candidate_paths", "candidate_bearing_entries", "loan_hints", "morphology_review_entries"),
                total_row,
            )),
            "processing": totals,
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
        if metadata.get("schema_version") != "2":
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

        install_review_overlay(connection)
        orphaned_reviews = [row[0] for row in connection.execute(
            "SELECT o.entry_id FROM review_overlay o LEFT JOIN entries e ON e.entry_id=o.entry_id "
            "WHERE e.entry_id IS NULL ORDER BY o.entry_id"
        )]
        report["orphaned_review_states"] = orphaned_reviews
        if orphaned_reviews:
            problems.append(f"{len(orphaned_reviews)} review states have no inventory entry")
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
