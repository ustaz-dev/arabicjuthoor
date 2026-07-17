from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
FAMILY_REVIEW_STATE = ROOT / "data" / "family-review-states.json"
FAMILY_REVIEW_STATUSES = {"unreviewed", "reviewed", "loan-isolated", "suspended", "closed"}
FAMILY_METADATA_VERSION = "3"
DEFAULT_MAX_LEMMAS_PER_FAMILY = 256
AFFIX_POS_MARKERS = (
    "affix", "combining_form", "infix", "interfix", "prefix", "suffix", "präfix",
)


FAMILY_SCHEMA = """
CREATE TABLE IF NOT EXISTS form_links (
    form_entry_id TEXT NOT NULL REFERENCES entries(entry_id) ON DELETE CASCADE,
    target_text TEXT NOT NULL,
    link_type TEXT NOT NULL,
    candidate_entry_ids_json TEXT NOT NULL,
    resolved_target_entry_id TEXT REFERENCES entries(entry_id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    match_method TEXT NOT NULL,
    PRIMARY KEY(form_entry_id, target_text, link_type)
);
CREATE INDEX IF NOT EXISTS form_links_status ON form_links(status, form_entry_id);
CREATE INDEX IF NOT EXISTS form_links_resolved_target ON form_links(resolved_target_entry_id);
CREATE TABLE IF NOT EXISTS relation_links (
    source_entry_id TEXT NOT NULL REFERENCES entries(entry_id) ON DELETE CASCADE,
    target_text TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    candidate_entry_ids_json TEXT NOT NULL,
    resolved_target_entry_id TEXT REFERENCES entries(entry_id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    match_method TEXT NOT NULL,
    PRIMARY KEY(source_entry_id, target_text, relation_type)
);
CREATE INDEX IF NOT EXISTS relation_links_status ON relation_links(status, relation_type);
CREATE INDEX IF NOT EXISTS relation_links_resolved_target ON relation_links(resolved_target_entry_id);
CREATE TABLE IF NOT EXISTS family_edges (
    language TEXT NOT NULL,
    left_entry_id TEXT NOT NULL REFERENCES entries(entry_id) ON DELETE CASCADE,
    right_entry_id TEXT NOT NULL REFERENCES entries(entry_id) ON DELETE CASCADE,
    link_type TEXT NOT NULL,
    evidence TEXT NOT NULL,
    PRIMARY KEY(left_entry_id, right_entry_id, link_type)
);
CREATE INDEX IF NOT EXISTS family_edges_right_entry ON family_edges(right_entry_id);
CREATE TABLE IF NOT EXISTS families (
    family_id TEXT PRIMARY KEY,
    language TEXT NOT NULL,
    anchor_entry_id TEXT NOT NULL REFERENCES entries(entry_id) ON DELETE CASCADE,
    anchor_headword TEXT NOT NULL,
    construction TEXT NOT NULL,
    member_count INTEGER NOT NULL,
    lemma_count INTEGER NOT NULL,
    form_count INTEGER NOT NULL,
    nonlexical_count INTEGER NOT NULL,
    candidate_bearing_member_count INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS families_language ON families(language, construction, family_id);
CREATE INDEX IF NOT EXISTS families_anchor_entry ON families(anchor_entry_id);
CREATE TABLE IF NOT EXISTS family_members (
    entry_id TEXT PRIMARY KEY REFERENCES entries(entry_id) ON DELETE CASCADE,
    family_id TEXT NOT NULL REFERENCES families(family_id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    link_types_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS family_members_family ON family_members(family_id, entry_id);
"""


class UnionFind:
    def __init__(self, values: Iterable[str]):
        self.parent = {value: value for value in values}
        self.rank = {value: 0 for value in values}

    def find(self, value: str) -> str:
        parent = self.parent[value]
        if parent != value:
            self.parent[value] = self.find(parent)
        return self.parent[value]

    def union(self, left: str, right: str) -> None:
        a, b = self.find(left), self.find(right)
        if a == b:
            return
        if self.rank[a] < self.rank[b]:
            a, b = b, a
        self.parent[b] = a
        if self.rank[a] == self.rank[b]:
            self.rank[a] += 1


def ensure_family_schema(connection: sqlite3.Connection) -> None:
    form_link_columns = {row[1] for row in connection.execute("PRAGMA table_info(form_links)")}
    if form_link_columns and "link_type" not in form_link_columns:
        connection.executescript("""
            DROP TABLE IF EXISTS family_members;
            DROP TABLE IF EXISTS families;
            DROP TABLE IF EXISTS family_edges;
            DROP TABLE IF EXISTS relation_links;
            DROP TABLE IF EXISTS form_links;
        """)
    connection.executescript(FAMILY_SCHEMA)


def clear_language_families(connection: sqlite3.Connection, language: str) -> None:
    connection.execute("DELETE FROM family_edges WHERE language=?", (language,))
    connection.execute(
        "DELETE FROM form_links WHERE form_entry_id IN "
        "(SELECT entry_id FROM entries WHERE language=?)",
        (language,),
    )
    connection.execute(
        "DELETE FROM relation_links WHERE source_entry_id IN "
        "(SELECT entry_id FROM entries WHERE language=?)",
        (language,),
    )
    connection.execute("DELETE FROM families WHERE language=?", (language,))


ORTHOGRAPHIC_TRANSLATION = str.maketrans({"ς": "σ", "ך": "כ", "ם": "מ", "ן": "נ", "ף": "פ", "ץ": "צ"})


def orthographic_key(value: str) -> str:
    text = unicodedata.normalize("NFD", value or "").casefold().translate(ORTHOGRAPHIC_TRANSLATION)
    return "".join(char for char in text if not unicodedata.combining(char) and char.isalnum())


def target_alternatives(value: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(part.strip() for part in re.split(r"\+|/", value or "") if part.strip()))


def is_affix_entry(headword: str, pos: str) -> bool:
    word = (headword or "").strip()
    normalized_pos = (pos or "").casefold().replace("-", "_").replace(" ", "_")
    return bool(
        word.startswith("-") or word.endswith("-")
        or any(marker in normalized_pos for marker in AFFIX_POS_MARKERS)
    )


def _review_event_is_complete(state: dict[str, Any], family_id: str) -> None:
    status = state.get("status", "")
    if status not in FAMILY_REVIEW_STATUSES:
        raise ValueError(f"Invalid family review status for {family_id}: {status}")
    if status == "suspended" and not state.get("blocker"):
        raise ValueError(f"Suspended family lacks blocker: {family_id}")
    if status in {"reviewed", "loan-isolated", "closed"}:
        if not state.get("recovery_review") or not state.get("skeptical_review"):
            raise ValueError(f"Finalized family lacks both review lenses: {family_id}")
        skeptic = state["skeptical_review"]
        required = ("loan_screen", "homonym_screen", "source_check", "result")
        if any(key not in skeptic for key in required):
            raise ValueError(f"Incomplete skeptical review for family {family_id}")


def load_family_review_states(path: Path = FAMILY_REVIEW_STATE) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("version") != 1 or not isinstance(payload.get("families"), dict):
        raise ValueError(f"Invalid family-review file: {path}")
    if not isinstance(payload.get("member_overrides"), dict):
        raise ValueError(f"Invalid family member overrides: {path}")
    for family_id, state in payload["families"].items():
        _review_event_is_complete(state, family_id)
    for entry_id, override in payload["member_overrides"].items():
        required = ("family_id", "decision", "reason", "reviewer", "date")
        if any(not override.get(field) for field in required):
            raise ValueError(f"Incomplete member override for {entry_id}")
        if override["decision"] not in {"uphold", "reject", "suspend"}:
            raise ValueError(f"Invalid member override decision for {entry_id}: {override['decision']}")
    return payload


def install_family_review_overlay(connection: sqlite3.Connection, payload: dict[str, Any] | None = None) -> None:
    payload = load_family_review_states() if payload is None else payload
    connection.execute(
        "CREATE TEMP TABLE IF NOT EXISTS family_review_overlay "
        "(family_id TEXT PRIMARY KEY, status TEXT NOT NULL, blocker TEXT NOT NULL)"
    )
    connection.execute("DELETE FROM family_review_overlay")
    connection.executemany(
        "INSERT INTO family_review_overlay VALUES (?, ?, ?)",
        [
            (family_id, state.get("status", "unreviewed"), str(state.get("blocker") or ""))
            for family_id, state in payload["families"].items()
        ],
    )


def require_current_family_metadata(connection: sqlite3.Connection, languages: Iterable[str]) -> None:
    metadata = dict(connection.execute(
        "SELECT key, value FROM meta WHERE key LIKE 'family_metadata_version:%'"
    ))
    stale = sorted(
        language for language in set(languages)
        if metadata.get(f"family_metadata_version:{language}") != FAMILY_METADATA_VERSION
    )
    if stale:
        raise RuntimeError(
            "Family cards are blocked until family metadata is refreshed at version "
            f"{FAMILY_METADATA_VERSION}: {', '.join(stale)}"
        )


def _resolver(entries: list[dict[str, Any]]):
    exact: dict[str, list[str]] = defaultdict(list)
    orthographic: dict[str, list[str]] = defaultdict(list)
    form_exact: dict[str, list[str]] = defaultdict(list)
    form_orthographic: dict[str, list[str]] = defaultdict(list)
    for entry in entries:
        if entry["nonlexical"]:
            continue
        pure_form = entry["form_of"] and not entry["alternative_of"]
        exact_index = form_exact if pure_form else exact
        orthographic_index = form_orthographic if pure_form else orthographic
        exact_index[unicodedata.normalize("NFC", entry["headword"]).casefold()].append(entry["entry_id"])
        key = orthographic_key(entry["headword"])
        if key:
            orthographic_index[key].append(entry["entry_id"])

    by_id = {entry["entry_id"]: entry for entry in entries}

    def narrow_by_pos(found: list[str], source_pos: str, method: str) -> tuple[list[str], str]:
        candidates = sorted(set(found))
        if len(candidates) > 1 and source_pos:
            same_pos = [entry_id for entry_id in candidates if by_id[entry_id]["pos"] == source_pos]
            if len(same_pos) == 1:
                return same_pos, method + "-pos"
        return candidates, method

    def lookup(
        alternatives: tuple[str, ...], source_pos: str, source_entry_id: str,
        exact_index: dict[str, list[str]], orthographic_index: dict[str, list[str]], method_prefix: str,
    ) -> tuple[list[str], str]:
        found: list[str] = []
        for alternative in alternatives:
            found.extend(exact_index.get(unicodedata.normalize("NFC", alternative).casefold(), ()))
        found = [entry_id for entry_id in found if entry_id != source_entry_id]
        if found:
            return narrow_by_pos(found, source_pos, method_prefix + "exact")
        for key in {orthographic_key(item) for item in alternatives} - {""}:
            found.extend(orthographic_index.get(key, ()))
        found = [entry_id for entry_id in found if entry_id != source_entry_id]
        return narrow_by_pos(found, source_pos, method_prefix + "orthographic") if found else ([], "none")

    def resolve(target: str, source_pos: str = "", source_entry_id: str = "") -> tuple[list[str], str]:
        alternatives = target_alternatives(target) or (target.strip(),)
        found, method = lookup(
            alternatives, source_pos, source_entry_id, exact, orthographic, "",
        )
        if found:
            return found, method
        return lookup(
            alternatives, source_pos, source_entry_id, form_exact, form_orthographic, "via-form-",
        )

    return resolve


def _family_id(language: str, members: list[str]) -> str:
    digest = hashlib.sha256("\n".join(sorted(members)).encode("utf-8")).hexdigest()[:24]
    return f"{language}:family:{digest}"


def build_families(
    connection: sqlite3.Connection,
    language: str,
    max_lemma_count: int = DEFAULT_MAX_LEMMAS_PER_FAMILY,
) -> dict[str, Any]:
    if max_lemma_count < 1:
        raise ValueError("max_lemma_count must be positive")
    ensure_family_schema(connection)
    clear_language_families(connection, language)
    rows = connection.execute(
        "SELECT entry_id, headword, form_of, alternative_of, form_targets_json, alternative_targets_json, "
        "derived_terms_json, related_terms_json, "
        "skeleton, processing_status, candidate_count, pos FROM entries WHERE language=? ORDER BY entry_id",
        (language,),
    ).fetchall()
    fields = (
        "entry_id", "headword", "form_of", "alternative_of", "form_targets_json", "alternative_targets_json",
        "derived_terms_json", "related_terms_json", "skeleton", "processing_status", "candidate_count", "pos",
    )
    entries = [dict(zip(fields, row)) for row in rows]
    if not entries:
        raise ValueError(f"Cannot build families without entries for {language}")
    by_id = {entry["entry_id"]: entry for entry in entries}
    for entry in entries:
        entry["form_targets"] = tuple(json.loads(entry.pop("form_targets_json")))
        entry["alternative_targets"] = tuple(json.loads(entry.pop("alternative_targets_json")))
        entry["derived_terms"] = tuple(json.loads(entry.pop("derived_terms_json")))
        entry["related_terms"] = tuple(json.loads(entry.pop("related_terms_json")))
        entry["form_of"] = bool(entry["form_of"])
        entry["alternative_of"] = bool(entry["alternative_of"])
        entry["nonlexical"] = entry["pos"] in {"character", "symbol", "punct"}
        entry["affix"] = is_affix_entry(entry["headword"], entry["pos"])

    union = UnionFind(by_id)
    resolve = _resolver(entries)
    edges: dict[tuple[str, str, str], str] = {}
    form_link_rows: list[tuple[object, ...]] = []
    relation_rows: list[tuple[object, ...]] = []
    resolved_relation_edges: list[tuple[str, str, str, str]] = []
    form_statuses: dict[str, list[str]] = defaultdict(list)
    textual_entries: set[str] = set()
    multi_parent_form_sources = {
        entry["entry_id"] for entry in entries
        if entry["form_of"] and len({
            orthographic_key(target) or unicodedata.normalize("NFC", target).casefold()
            for target in entry["form_targets"] if target
        }) > 1
    }

    def edge(
        left: str, right: str, link_type: str, evidence: str, annotation_reason: str = "",
    ) -> None:
        if left == right:
            return
        annotation_only = bool(annotation_reason) or by_id[left]["affix"] or by_id[right]["affix"]
        if annotation_only:
            reason = "affix" if by_id[left]["affix"] or by_id[right]["affix"] else annotation_reason
            link_type = f"annotation-{reason}-" + link_type
        a, b = sorted((left, right))
        edges.setdefault((a, b, link_type), evidence)
        if not annotation_only:
            union.union(a, b)

    for entry in entries:
        if not entry["form_of"] and not entry["alternative_of"]:
            continue
        typed_targets = []
        if entry["form_of"]:
            typed_targets.append(("form-of", entry["form_targets"] or ("",)))
        if entry["alternative_of"]:
            typed_targets.append(("alt-of", entry["alternative_targets"] or ("",)))
        for link_type, targets in typed_targets:
            for target in targets:
                candidates, method = resolve(target, entry["pos"], entry["entry_id"]) if target else ([], "none")
                status = "linked" if len(candidates) == 1 else "ambiguous-form" if candidates else "orphan-form"
                resolved = candidates[0] if status == "linked" else None
                if (
                    resolved and link_type == "form-of"
                    and entry["entry_id"] in multi_parent_form_sources
                ):
                    status = "multi-parent-form"
                form_link_rows.append((
                    entry["entry_id"], target, link_type, json.dumps(candidates, ensure_ascii=False),
                    resolved, status, method,
                ))
                form_statuses[entry["entry_id"]].append(status)
                if resolved:
                    textual_entries.update((entry["entry_id"], resolved))
                    edge_type = "via-form" if method.startswith("via-form-") else link_type
                    annotation_reason = "multiparent-form" if status == "multi-parent-form" else ""
                    edge(entry["entry_id"], resolved, edge_type, target, annotation_reason)

    for entry in entries:
        if (entry["form_of"] and not entry["alternative_of"]) or entry["nonlexical"]:
            continue
        for relation_type, targets in (("derived", entry["derived_terms"]), ("related", entry["related_terms"])):
            for target in targets:
                candidates, method = resolve(target, source_entry_id=entry["entry_id"])
                candidates = [candidate for candidate in candidates if candidate != entry["entry_id"]]
                status = "linked" if len(candidates) == 1 else "ambiguous-relation" if candidates else "outside-snapshot"
                resolved = candidates[0] if status == "linked" else None
                relation_rows.append((
                    entry["entry_id"], target, relation_type, json.dumps(candidates, ensure_ascii=False),
                    resolved, status, method,
                ))
                if resolved:
                    textual_entries.update((entry["entry_id"], resolved))
                    resolved_relation_edges.append((
                        entry["entry_id"], resolved, f"textual-{relation_type}", target,
                    ))

    incoming_relation_sources: dict[str, set[str]] = defaultdict(set)
    for source, target, _, _ in resolved_relation_edges:
        if not by_id[source]["affix"] and not by_id[target]["affix"]:
            incoming_relation_sources[target].add(source)
    for source, target, link_type, evidence in resolved_relation_edges:
        annotation_reason = "multiparent" if len(incoming_relation_sources[target]) > 1 else ""
        edge(source, target, link_type, evidence, annotation_reason)

    if form_link_rows:
        connection.executemany("INSERT INTO form_links VALUES (?, ?, ?, ?, ?, ?, ?)", form_link_rows)
    if relation_rows:
        connection.executemany("INSERT INTO relation_links VALUES (?, ?, ?, ?, ?, ?, ?)", relation_rows)

    components_before_structure: dict[str, list[str]] = defaultdict(list)
    for entry_id in by_id:
        components_before_structure[union.find(entry_id)].append(entry_id)
    structural_groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for representative, members in components_before_structure.items():
        if any(member in textual_entries for member in members):
            continue
        lemma_members = [
            member for member in members
            if not by_id[member]["form_of"] and not by_id[member]["alternative_of"]
            and not by_id[member]["nonlexical"] and not by_id[member]["affix"]
        ]
        for skeleton in sorted({by_id[member]["skeleton"] for member in lemma_members} - {""}):
            anchor = min(member for member in lemma_members if by_id[member]["skeleton"] == skeleton)
            structural_groups[skeleton].append((representative, anchor))
    for skeleton, items in structural_groups.items():
        representatives: dict[str, str] = {}
        for representative, anchor in items:
            representatives.setdefault(union.find(representative), anchor)
        anchors = sorted(representatives.values())
        if len(anchors) > 1:
            first = anchors[0]
            for other in anchors[1:]:
                edge(first, other, "structural", skeleton)

    if edges:
        connection.executemany("INSERT INTO family_edges VALUES (?, ?, ?, ?, ?)", [
            (language, left, right, link_type, evidence)
            for (left, right, link_type), evidence in sorted(edges.items())
        ])

    status_updates: list[tuple[str, str, str]] = []
    for entry_id, statuses in form_statuses.items():
        unique = set(statuses)
        if unique == {"linked"}:
            resolution, processing = "linked", "form-linked"
        elif "orphan-form" in unique:
            resolution, processing = "orphan-form", "orphan-form"
        elif "multi-parent-form" in unique:
            resolution, processing = "multi-parent-form", "multi-parent-form"
        elif "ambiguous-form" in unique:
            resolution, processing = "ambiguous-form", "ambiguous-form"
        else:
            resolution, processing = "mixed-form-link", "mixed-form-link"
        status_updates.append((entry_id, resolution, processing))
    if status_updates:
        connection.execute("DROP TABLE IF EXISTS temp._family_status_updates")
        connection.execute(
            "CREATE TEMP TABLE _family_status_updates "
            "(entry_id TEXT PRIMARY KEY, resolution TEXT NOT NULL, processing TEXT NOT NULL)"
        )
        connection.executemany(
            "INSERT INTO _family_status_updates VALUES (?, ?, ?)", status_updates
        )
        connection.execute(
            "UPDATE entries AS e SET form_resolution_status=u.resolution, "
            "processing_status=CASE WHEN e.form_of=1 AND e.alternative_of=0 "
            "THEN u.processing ELSE e.processing_status END "
            "FROM _family_status_updates AS u WHERE e.entry_id=u.entry_id"
        )
        connection.execute("DROP TABLE _family_status_updates")

    incident: dict[str, set[str]] = defaultdict(set)
    for left, right, link_type in edges:
        if link_type.startswith("annotation-"):
            continue
        incident[left].add(link_type)
        incident[right].add(link_type)
    components: dict[str, list[str]] = defaultdict(list)
    for entry_id in by_id:
        components[union.find(entry_id)].append(entry_id)
    family_rows: list[tuple[object, ...]] = []
    member_rows: list[tuple[object, ...]] = []
    construction_counts: Counter[str] = Counter()
    for members in components.values():
        members.sort()
        family_id = _family_id(language, members)
        anchor_id = min(
            members,
            key=lambda item: (
                by_id[item]["nonlexical"],
                by_id[item]["form_of"] or by_id[item]["alternative_of"],
                by_id[item]["form_of"],
                by_id[item]["headword"], item,
            ),
        )
        types = set().union(*(incident.get(member, set()) for member in members))
        form_states = {status for member in members for status in form_statuses.get(member, ())}
        if "orphan-form" in form_states:
            construction = "orphan-form"
        elif {"ambiguous-form", "multi-parent-form"} & form_states:
            construction = "ambiguous-form"
        elif not types and all(by_id[member]["nonlexical"] for member in members):
            construction = "nonlexical"
        elif not types:
            construction = "singleton"
        elif types and types <= {"form-of", "via-form"}:
            construction = "form-of"
        elif types == {"alt-of"}:
            construction = "alternative"
        elif types == {"structural"}:
            construction = "structural"
        elif all(item.startswith("textual-") for item in types):
            construction = "textual"
        else:
            construction = "mixed"
        construction_counts[construction] += 1
        lemma_count = sum(
            not by_id[member]["form_of"] and not by_id[member]["alternative_of"]
            and not by_id[member]["nonlexical"] for member in members
        )
        form_count = sum(
            (by_id[member]["form_of"] or by_id[member]["alternative_of"])
            and not by_id[member]["nonlexical"] for member in members
        )
        nonlexical_count = sum(by_id[member]["nonlexical"] for member in members)
        candidate_members = sum(bool(by_id[member]["candidate_count"]) for member in members)
        if lemma_count > max_lemma_count:
            raise ValueError(
                f"{language}: family anchored at {by_id[anchor_id]['headword']!r} has "
                f"{lemma_count} lemmas; profile limit is {max_lemma_count}"
            )
        family_rows.append((
            family_id, language, anchor_id, by_id[anchor_id]["headword"], construction,
            len(members), lemma_count, form_count, nonlexical_count, candidate_members,
        ))
        member_rows.extend((
            member,
            family_id,
            "nonlexical" if by_id[member]["nonlexical"] else "alternative+form"
            if by_id[member]["form_of"] and by_id[member]["alternative_of"] else "form"
            if by_id[member]["form_of"] else "alternative"
            if by_id[member]["alternative_of"] else "lemma",
            json.dumps(sorted(incident.get(member, ())), ensure_ascii=False),
        ) for member in members)
    connection.executemany("INSERT INTO families VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", family_rows)
    connection.executemany("INSERT INTO family_members VALUES (?, ?, ?, ?)", member_rows)

    status_counts = Counter(status for statuses in form_statuses.values() for status in set(statuses))
    max_observed = max((row[6] for row in family_rows), default=0)
    return {
        "families": len(family_rows),
        "family_members": len(member_rows),
        "constructions": dict(construction_counts),
        "form_link_statuses": dict(status_counts),
        "form_link_rows": len(form_link_rows),
        "relation_link_rows": len(relation_rows),
        "max_lemma_count_observed": max_observed,
        "max_lemma_count_allowed": max_lemma_count,
    }


def family_summary(connection: sqlite3.Connection, language: str | None = None) -> dict[str, Any]:
    install_family_review_overlay(connection)
    where = " WHERE f.language=?" if language else ""
    params = (language,) if language else ()
    counts = connection.execute(
        "SELECT COUNT(*), COALESCE(SUM(f.member_count),0), COALESCE(SUM(f.lemma_count),0), "
        "COALESCE(SUM(f.form_count),0), COALESCE(SUM(f.nonlexical_count),0) FROM families f" + where,
        params,
    ).fetchone()
    constructions = dict(connection.execute(
        "SELECT f.construction, COUNT(*) FROM families f" + where + " GROUP BY f.construction", params
    ).fetchall())
    reviews = dict(connection.execute(
        "SELECT COALESCE(o.status,'unreviewed'), COUNT(*) FROM families f "
        "LEFT JOIN family_review_overlay o ON o.family_id=f.family_id" + where
        + " GROUP BY COALESCE(o.status,'unreviewed')",
        params,
    ).fetchall())
    form_where = " WHERE e.language=?" if language else ""
    form_statuses = dict(connection.execute(
        "SELECT fl.status, COUNT(*) FROM form_links fl JOIN entries e ON e.entry_id=fl.form_entry_id"
        + form_where + " GROUP BY fl.status",
        params,
    ).fetchall())
    return {
        "families": counts[0],
        "entries_in_families": counts[1],
        "lemmas": counts[2],
        "forms": counts[3],
        "nonlexical": counts[4],
        "constructions": constructions,
        "family_reviews": reviews,
        "form_links": form_statuses,
    }


def family_review_queue(
    connection: sqlite3.Connection,
    lens: str,
    language: str | None = None,
    processing_status: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    queue_languages = [language] if language else [
        row[0] for row in connection.execute("SELECT DISTINCT language FROM families")
    ]
    require_current_family_metadata(connection, queue_languages)
    states = load_family_review_states()["families"]
    clauses: list[str] = []
    params: list[object] = []
    if language:
        clauses.append("f.language=?")
        params.append(language)
    if processing_status:
        clauses.append("EXISTS (SELECT 1 FROM family_members fm2 JOIN entries e2 ON e2.entry_id=fm2.entry_id "
                       "WHERE fm2.family_id=f.family_id AND e2.processing_status=?)")
        params.append(processing_status)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    rows = connection.execute(
        "SELECT f.family_id, f.language, f.anchor_headword, f.construction, f.member_count, f.lemma_count, "
        "f.form_count, f.nonlexical_count, f.candidate_bearing_member_count, "
        "COALESCE((SELECT GROUP_CONCAT(DISTINCT e3.source_stratum) FROM family_members fm3 "
        "JOIN entries e3 ON e3.entry_id=fm3.entry_id WHERE fm3.family_id=f.family_id "
        "AND e3.source_stratum<>''), ''), "
        "COALESCE((SELECT MIN(e4.source_scope_note) FROM family_members fm4 "
        "JOIN entries e4 ON e4.entry_id=fm4.entry_id WHERE fm4.family_id=f.family_id "
        "AND e4.source_scope_note<>''), '') "
        "FROM families f" + where
        + " ORDER BY f.language, f.family_id LIMIT ?",
        (*params, limit * 20),
    )
    result: list[dict[str, Any]] = []
    fields = (
        "family_id", "language", "anchor_headword", "construction", "member_count", "lemma_count",
        "form_count", "nonlexical_count", "candidate_bearing_member_count",
        "source_strata", "source_scope_note",
    )
    for row in rows:
        state = states.get(row[0], {})
        missing = not state.get("recovery_review") if lens == "recovery" else (
            bool(state.get("recovery_review")) and not state.get("skeptical_review")
        )
        if missing:
            item = dict(zip(fields, row))
            item["review_status"] = state.get("status", "unreviewed")
            result.append(item)
        if len(result) >= limit:
            break
    return result


def family_card(connection: sqlite3.Connection, family_id: str, candidate_limit: int = 200) -> dict[str, Any]:
    payload = load_family_review_states()
    state = payload["families"].get(family_id, {})
    row = connection.execute(
        "SELECT family_id, language, anchor_entry_id, anchor_headword, construction, member_count, lemma_count, "
        "form_count, nonlexical_count, candidate_bearing_member_count FROM families WHERE family_id=?",
        (family_id,),
    ).fetchone()
    if row is None:
        raise KeyError(f"Unknown family: {family_id}")
    fields = (
        "family_id", "language", "anchor_entry_id", "anchor_headword", "construction", "member_count",
        "lemma_count", "form_count", "nonlexical_count", "candidate_bearing_member_count",
    )
    family = dict(zip(fields, row))
    require_current_family_metadata(connection, [family["language"]])
    family["review_status"] = state.get("status", "unreviewed")
    family["review_record"] = state or {"status": "unreviewed"}
    members = []
    for member in connection.execute(
        "SELECT e.entry_id, e.headword, e.romanization, e.pos, e.gloss, e.processing_status, e.form_resolution_status, "
        "e.loan_hint, e.source_stratum, e.source_scope_note, fm.role, fm.link_types_json "
        "FROM family_members fm JOIN entries e ON e.entry_id=fm.entry_id "
        "WHERE fm.family_id=? ORDER BY fm.role DESC, e.entry_id",
        (family_id,),
    ):
        item = dict(zip((
            "entry_id", "headword", "romanization", "pos", "gloss", "processing_status",
            "form_resolution_status", "loan_hint", "source_stratum", "source_scope_note",
            "role", "link_types",
        ), member))
        item["link_types"] = json.loads(item["link_types"])
        override = payload["member_overrides"].get(item["entry_id"])
        item["review_inheritance"] = "member-override" if override else "family"
        item["effective_review"] = override or {"status": family["review_status"]}
        members.append(item)
    candidate_rows = connection.execute(
        "SELECT c.kind, c.form, a.reading, c.status, c.rule_ids_json, c.route_flag, "
        "COUNT(DISTINCT c.entry_id) FROM family_members fm JOIN candidates c ON c.entry_id=fm.entry_id "
        "LEFT JOIN arabic_forms a ON a.form=c.form AND a.kind=c.kind WHERE fm.family_id=? "
        "GROUP BY c.kind, c.form, a.reading, c.status, c.rule_ids_json, c.route_flag "
        "ORDER BY CASE c.status WHEN 'licensed' THEN 0 WHEN 'manual-condition' THEN 1 ELSE 2 END, c.kind, c.form LIMIT ?",
        (family_id, candidate_limit + 1),
    ).fetchall()
    candidates = []
    for candidate in candidate_rows[:candidate_limit]:
        item = dict(zip((
            "kind", "form", "reading", "status", "rule_ids", "route_required", "contributing_members",
        ), candidate))
        item["rule_ids"] = json.loads(item["rule_ids"])
        item["route_required"] = bool(item["route_required"])
        candidates.append(item)
    return {
        "family": family,
        "members": members,
        "unified_candidates": candidates,
        "candidate_list_truncated": len(candidate_rows) > candidate_limit,
    }
