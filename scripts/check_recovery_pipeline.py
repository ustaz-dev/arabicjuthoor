#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

from recovery_pipeline.candidates import ArabicInventory, generate_hits
from recovery_pipeline.families import build_families, load_family_review_states, target_alternatives
from recovery_pipeline.inventory import load_review_states
from recovery_pipeline.network import compile_network, rules_by_id
from recovery_pipeline.normalization import available_profiles, detect_language, load_profile, normalize
from recovery_pipeline.sources import iter_coptic_tei, iter_kaikki
from recovery_pipeline.proof import load_preregistration, require_execution_authority


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "scripts" / "recovery_pipeline" / "network-fixtures.json"


def main() -> int:
    failures: list[str] = []
    if target_alternatives("alpha+beta/gamma") != ("alpha", "beta", "gamma"):
        failures.append("family-target separator regression")
    rules = compile_network()
    indexed = rules_by_id(rules)
    if len(rules) != 44:
        failures.append(f"network row count: expected 44, got {len(rules)}")
    expected = json.loads(FIXTURES.read_text(encoding="utf-8"))
    for row_id, fields in expected.items():
        rule = indexed.get(row_id)
        if rule is None:
            failures.append(f"network fixture missing: {row_id}")
            continue
        for field, value in fields.items():
            got = list(getattr(rule, field)) if field == "scopes" else getattr(rule, field)
            if got != value:
                failures.append(f"network fixture {row_id}.{field}: {got!r} != {value!r}")

    regressions = {
        ("ancient_greek", "τρεῖς"): ("t", "r", "s"),
        ("coptic", "ϣⲛϥⲉ"): ("sh", "n", "f"),
        ("egyptian", "ꜣpd"): ("qstop", "p", "d"),
        ("latin", "cornu"): ("k", "r", "n"),
        ("latin", "quattuor"): ("k", "w", "t", "t", "r"),
        ("hebrew", "𐤁𐤉𐤕"): ("b", "y", "t"),
        ("aramaic", "𐡀𐡓𐡌𐡉𐡀"): ("qstop", "r", "m", "y", "qstop"),
        ("aramaic", "ܡܫܝܚܐ"): ("m", "sh", "y", "hh", "qstop"),
    }
    detections = {
        "τρεῖς": "ancient_greek",
        "ϣⲛϥⲉ": "coptic",
        "ꜣpd": "egyptian",
        "snf": "generic",
    }
    for value, language in detections.items():
        if detect_language(value) != language:
            failures.append(f"language detection {value}: {detect_language(value)!r} != {language!r}")
    for (language, value), tokens in regressions.items():
        result = normalize(value, load_profile(language))
        if result.tokens != tokens:
            failures.append(f"normalization {language} {value}: {result.tokens!r} != {tokens!r}")
    try:
        normalize("τ@", load_profile("ancient_greek"))
        failures.append("strict normalization accepted an unknown symbol")
    except ValueError:
        pass

    inventory = ArabicInventory.load()
    greek = normalize("τρεῖς", load_profile("ancient_greek"))
    greek_hits, _ = generate_hits(greek.tokens, "ancient_greek", rules, inventory)
    if not any(hit.form == "ثر" and hit.status == "scope-gap" for hit in greek_hits):
        failures.append("treis regression: ثر scope-gap was not retained")
    if any(hit.form == "ثر" and hit.status == "licensed" for hit in greek_hits):
        failures.append("treis regression: DENT-01 escaped its Aramaic scope")
    coptic = normalize("ϣⲛϥⲉ", load_profile("coptic"))
    coptic_hits, _ = generate_hits(coptic.tokens, "coptic", rules, inventory)
    if not any(hit.form == "شن" and hit.status == "licensed" for hit in coptic_hits):
        failures.append("Coptic shnfe regression: exact شن nucleus missing")
    latin = normalize("cornu", load_profile("latin"))
    latin_hits, _ = generate_hits(latin.tokens, "latin", rules, inventory)
    if not any(hit.kind == "root" and hit.form == "قرن" and hit.status == "licensed" for hit in latin_hits):
        failures.append("Latin cornu regression: قرن root missing")
    multi_rule_inventory = ArabicInventory(roots={}, nuclei={"بذ": "test"})
    multi_rule_hits, _ = generate_hits(("p", "z"), "ancient_greek", rules, multi_rule_inventory)
    if not any(hit.form == "بذ" and hit.rule_ids == ("DENT-04", "LAB-01") for hit in multi_rule_hits):
        failures.append("multi-row retrieval regression: direct correspondences in two slots were lost")

    load_review_states()
    load_family_review_states()
    preregistration = load_preregistration()
    try:
        require_execution_authority(preregistration)
        failures.append("locked proof preregistration opened its execution gate")
    except PermissionError:
        pass
    required_profile_fields = {
        "profile_version", "language", "preferred_input", "script_map", "vowels", "multi_tokens",
        "single_tokens", "ignored_characters", "zero_step", "relevant_branch_rules",
        "family_max_lemma_count",
    }
    for language in available_profiles():
        profile = load_profile(language)
        missing = required_profile_fields - set(profile)
        if missing:
            failures.append(f"profile {language} missing: {sorted(missing)}")
        if not isinstance(profile.get("family_max_lemma_count"), int) or profile.get("family_max_lemma_count", 0) < 1:
            failures.append(f"profile {language} has invalid family_max_lemma_count")

    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        kaikki = temp / "sample.jsonl"
        row = json.dumps({
            "word": "τρεῖς", "lang": "Ancient Greek", "pos": "num",
            "forms": [{"form": "treîs", "tags": ["romanization"]}],
            "etymology_text": "Inherited", "derived": [{"word": "τριάς"}],
            "related": [{"word": "τρία"}],
            "senses": [{"id": "sample-1", "glosses": ["three"], "tags": ["form-of"],
                        "form_of": [{"word": "τρεῖς including a source gloss"},
                                    {"word": "defective spelling"}],
                        "links": [["τρεῖς", "τρεῖς#Ancient_Greek"]]},
                       {"tags": ["alt-of"], "alt_of": [{"word": "τρία"}],
                        "links": [["τρία", "τρία#Ancient_Greek"]]},
                       {"tags": ["form-of"], "form_of": [{"word": "τριάς. source prose"}]}],
        }, ensure_ascii=False)
        kaikki.write_text(row + "\n" + row + "\n", encoding="utf-8")
        sample = list(iter_kaikki(kaikki, "sample"))
        if len(sample) != 2 or sample[0].entry_id == sample[1].entry_id:
            failures.append("synthetic Kaikki duplicate-ID regression")
        if sample[0].romanization != "treîs" or sample[0].gloss != "three":
            failures.append("synthetic Kaikki parser regression")
        if sample[0].form_targets != ("τρεῖς", "τριάς"):
            failures.append(f"Kaikki form-target recovery regression: {sample[0].form_targets!r}")
        if sample[0].alternative_targets != ("τρία",):
            failures.append(f"Kaikki alternative-target recovery regression: {sample[0].alternative_targets!r}")
        if not sample[0].form_of or not sample[0].alternative_of:
            failures.append("Kaikki form/alternative distinction regression")
        if sample[0].derived_terms != ("τριάς",) or sample[0].related_terms != ("τρία",):
            failures.append("Kaikki lexical-relation parser regression")
        latin = temp / "latin.jsonl"
        latin_rows = [
            {
                "word": "movet", "lang": "Latin", "pos": "verb",
                "senses": [{"id": "latin-1", "tags": ["form-of"],
                            "links": [["moveō", "moveo#Latin"], ["moves", "moves"]],
                            "form_of": [{"word": "moveō# source prose"}, {"word": "he/she/it moves"}]}],
            },
            {
                "word": "pastus", "lang": "Latin", "pos": "verb",
                "senses": [{"id": "latin-2", "tags": ["form-of"],
                            "form_of": [{"word": "pāscor and perfect passive participle of pāscō"}]}],
            },
            {
                "word": "obtenturus", "lang": "Latin", "pos": "verb",
                "senses": [{"id": "latin-3", "tags": ["form-of"],
                            "form_of": [{"word": "obtendō\nFuture active participle of obtineo"}]}],
            },
            {
                "word": "academicus", "lang": "Latin", "pos": "adj",
                "senses": [{"id": "latin-4", "tags": ["alt-of"],
                            "alt_of": [{"word": "or pertaining to an adjective"}]}],
            },
            {
                "word": "nomen", "lang": "Latin", "pos": "noun",
                "senses": [{"id": "latin-5", "tags": ["form-of"],
                            "links": [["substantive", "substantive#English"],
                                      ["adjective", "adjective#English"],
                                      ["numeral", "numeral#English"]],
                            "form_of": [{"word": "substantives"}, {"word": "adjectives"},
                                        {"word": "and numerals"}]}],
            },
            {
                "word": "fluorescens", "lang": "Latin", "pos": "verb",
                "senses": [{"id": "latin-6", "tags": ["form-of"],
                            "form_of": [{"word": "frequentative of fluō"}]}],
            },
            {
                "word": "frendendus", "lang": "Latin", "pos": "verb",
                "senses": [{"id": "latin-7", "tags": ["form-of"],
                            "form_of": [{"word": "frendeō and frendō"}]}],
            },
        ]
        latin.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in latin_rows), encoding="utf-8"
        )
        latin_sample = list(iter_kaikki(latin, "sample-latin"))
        if latin_sample[0].form_targets != ("moveō",):
            failures.append(f"Latin linked-target recovery regression: {latin_sample[0].form_targets!r}")
        if latin_sample[1].form_targets != ("pāscor", "pāscō"):
            failures.append(f"Latin compound-target recovery regression: {latin_sample[1].form_targets!r}")
        if latin_sample[2].form_targets != ("obtendō", "obtineo"):
            failures.append(f"Latin multiline-target recovery regression: {latin_sample[2].form_targets!r}")
        if latin_sample[3].alternative_targets:
            failures.append(f"Latin prose-target rejection regression: {latin_sample[3].alternative_targets!r}")
        if latin_sample[4].form_targets:
            failures.append(f"Latin foreign-link rejection regression: {latin_sample[4].form_targets!r}")
        if latin_sample[5].form_targets != ("fluō",):
            failures.append(f"Latin named-lemma recovery regression: {latin_sample[5].form_targets!r}")
        if latin_sample[6].form_targets != ("frendeō", "frendō"):
            failures.append(f"Latin paired-lemma recovery regression: {latin_sample[6].form_targets!r}")
        broken = temp / "broken.jsonl"
        broken.write_text("{not-json}\n", encoding="utf-8")
        try:
            list(iter_kaikki(broken, "broken"))
            failures.append("malformed Kaikki row was dropped instead of stopping coverage")
        except ValueError as error:
            if "line 1" not in str(error):
                failures.append("malformed Kaikki error omitted its line number")
        coptic_xml = temp / "sample.xml"
        coptic_xml.write_text("""<?xml version='1.0' encoding='UTF-8'?>
<TEI xmlns='http://www.tei-c.org/ns/1.0'><text><body><entry xml:id='C1'>
<form type='lemma'><orth>ϣⲛϥⲉ</orth></form><gramGrp><pos>Subst.</pos></gramGrp>
<etym><ref type='greek_lemma::grl_lemma'>λέξις</ref></etym>
<sense><cit type='translation'><quote xml:lang='en'>scale</quote></cit></sense>
</entry></body></text></TEI>""", encoding="utf-8")
        sample = list(iter_coptic_tei(coptic_xml, "sample-coptic"))
        if len(sample) != 1 or sample[0].headword != "ϣⲛϥⲉ" or not sample[0].loan_hint:
            failures.append("synthetic Coptic TEI parser regression")

        family_db = sqlite3.connect(":memory:")
        family_db.execute("PRAGMA foreign_keys=ON")
        family_db.execute(
            "CREATE TABLE entries (entry_id TEXT PRIMARY KEY, language TEXT NOT NULL, headword TEXT NOT NULL, "
            "form_of INTEGER NOT NULL, alternative_of INTEGER NOT NULL, "
            "form_targets_json TEXT NOT NULL, alternative_targets_json TEXT NOT NULL, "
            "derived_terms_json TEXT NOT NULL, related_terms_json TEXT NOT NULL, "
            "skeleton TEXT NOT NULL, processing_status TEXT NOT NULL, candidate_count INTEGER NOT NULL, "
            "pos TEXT NOT NULL, form_resolution_status TEXT NOT NULL)"
        )
        family_db.executemany(
            "INSERT INTO entries VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                ("noun", "hebrew", "אב", 0, 0, "[]", "[]", "[]", "[]", "qb", "candidates-generated", 1, "noun", "not-form"),
                ("verb", "hebrew", "אב", 0, 0, "[]", "[]", "[]", "[]", "qb", "candidates-generated", 1, "verb", "not-form"),
                ("form", "hebrew", "אבות", 1, 0, '["אָב"]', "[]", "[]", "[]", "qbwt", "form-pending-link", 0, "noun", "pending"),
                ("alternative", "hebrew", "אָב", 0, 1, "[]", '["אב"]', "[]", "[]", "qb", "candidates-generated", 1, "noun", "pending"),
                ("mixed", "hebrew", "אב׳", 1, 1, '["אָב"]', '["אב"]', "[]", "[]", "qb", "candidates-generated", 1, "noun", "pending"),
                ("orphan", "hebrew", "יתום", 1, 0, '["חסר"]', "[]", "[]", "[]", "ytwm", "form-pending-link", 0, "noun", "pending"),
                ("desolo", "hebrew", "dēsōlō", 0, 0, "[]", "[]", "[]", "[]", "dsl", "candidate-search-complete-zero", 0, "verb", "not-form"),
                ("desolatus", "hebrew", "dēsōlātus", 1, 0, '["dēsōlō"]', "[]", "[]", "[]", "dslt", "form-pending-link", 0, "verb", "pending"),
                ("desolatum", "hebrew", "dēsōlātum", 1, 0, '["dēsōlātus"]', "[]", "[]", "[]", "dsltm", "form-pending-link", 0, "verb", "pending"),
                ("reversans", "hebrew", "reversans", 0, 0, "[]", "[]", "[]", '["-alia"]', "rwrsns", "candidate-search-complete-zero", 0, "verb", "not-form"),
                ("asso", "hebrew", "assō", 0, 0, "[]", "[]", "[]", '["-alia"]', "ss", "candidate-search-complete-zero", 0, "verb", "not-form"),
                ("alia", "hebrew", "-alia", 0, 0, "[]", "[]", "[]", "[]", "ql", "candidate-search-complete-zero", 0, "suffix", "not-form"),
                ("play", "hebrew", "play", 0, 0, "[]", "[]", '["playful", "playhouse"]', "[]", "ply", "candidate-search-complete-zero", 0, "verb", "not-form"),
                ("playful", "hebrew", "playful", 0, 0, "[]", "[]", "[]", "[]", "plyfl", "candidate-search-complete-zero", 0, "adj", "not-form"),
                ("house", "hebrew", "house", 0, 0, "[]", "[]", '["playhouse"]', "[]", "hws", "candidate-search-complete-zero", 0, "noun", "not-form"),
                ("playhouse", "hebrew", "playhouse", 0, 0, "[]", "[]", "[]", "[]", "plyhws", "candidate-search-complete-zero", 0, "noun", "not-form"),
                ("dego", "hebrew", "dēgō", 0, 0, "[]", "[]", "[]", "[]", "dg", "candidate-search-complete-zero", 0, "verb", "not-form"),
                ("degero", "hebrew", "dēgerō", 0, 0, "[]", "[]", "[]", "[]", "dgr", "candidate-search-complete-zero", 0, "verb", "not-form"),
                ("degeret", "hebrew", "dēgeret", 1, 0, '["dēgō", "dēgerō"]', "[]", "[]", "[]", "dgrt", "form-pending-link", 0, "verb", "pending"),
            ],
        )
        report = build_families(family_db, "hebrew")
        if report["family_members"] != 19:
            failures.append("family membership regression: an entry disappeared")
        linked = family_db.execute(
            "SELECT status, resolved_target_entry_id, match_method FROM form_links WHERE form_entry_id='form'"
        ).fetchone()
        if linked != ("linked", "alternative", "exact"):
            failures.append(f"family POS-resolution regression: {linked!r}")
        alternative = family_db.execute(
            "SELECT link_type, status FROM form_links WHERE form_entry_id='alternative'"
        ).fetchone()
        alternative_entry = family_db.execute(
            "SELECT processing_status, form_resolution_status FROM entries WHERE entry_id='alternative'"
        ).fetchone()
        if alternative != ("alt-of", "linked") or alternative_entry != ("candidates-generated", "linked"):
            failures.append(f"alternative-family regression: {alternative!r}, {alternative_entry!r}")
        mixed = family_db.execute(
            "SELECT link_type, status FROM form_links WHERE form_entry_id='mixed' ORDER BY link_type"
        ).fetchall()
        mixed_entry = family_db.execute(
            "SELECT processing_status, candidate_count FROM entries WHERE entry_id='mixed'"
        ).fetchone()
        if mixed != [("alt-of", "linked"), ("form-of", "linked")] or mixed_entry != ("candidates-generated", 1):
            failures.append(f"mixed lexical/form regression: {mixed!r}, {mixed_entry!r}")
        orphan = family_db.execute(
            "SELECT status FROM form_links WHERE form_entry_id='orphan'"
        ).fetchone()
        if orphan != ("orphan-form",):
            failures.append("explicit orphan-form regression")
        via_form = family_db.execute(
            "SELECT status, resolved_target_entry_id, match_method FROM form_links "
            "WHERE form_entry_id='desolatum'"
        ).fetchone()
        chained_families = family_db.execute(
            "SELECT COUNT(DISTINCT family_id) FROM family_members "
            "WHERE entry_id IN ('desolo','desolatus','desolatum')"
        ).fetchone()[0]
        if via_form != ("linked", "desolatus", "via-form-exact") or chained_families != 1:
            failures.append(f"two-hop form-chain regression: {via_form!r}, families={chained_families}")
        affix_families = dict(family_db.execute(
            "SELECT entry_id, family_id FROM family_members WHERE entry_id IN ('reversans','asso','alia')"
        ))
        affix_edges = family_db.execute(
            "SELECT COUNT(*) FROM family_edges WHERE link_type='annotation-affix-textual-related'"
        ).fetchone()[0]
        if len(set(affix_families.values())) != 3 or affix_edges != 2:
            failures.append(f"affix-hub isolation regression: {affix_families!r}, edges={affix_edges}")
        derivation_families = dict(family_db.execute(
            "SELECT entry_id, family_id FROM family_members "
            "WHERE entry_id IN ('play','playful','house','playhouse')"
        ))
        multiparent_edges = family_db.execute(
            "SELECT COUNT(*) FROM family_edges WHERE link_type='annotation-multiparent-textual-derived'"
        ).fetchone()[0]
        if (
            derivation_families["play"] != derivation_families["playful"]
            or derivation_families["play"] == derivation_families["house"]
            or derivation_families["playhouse"] in {
                derivation_families["play"], derivation_families["house"]
            }
            or multiparent_edges != 2
        ):
            failures.append(
                f"multi-parent compound bridge regression: {derivation_families!r}, edges={multiparent_edges}"
            )
        homograph_families = dict(family_db.execute(
            "SELECT entry_id, family_id FROM family_members "
            "WHERE entry_id IN ('dego','degero','degeret')"
        ))
        homograph_edges = family_db.execute(
            "SELECT COUNT(*) FROM family_edges "
            "WHERE link_type='annotation-multiparent-form-form-of'"
        ).fetchone()[0]
        homograph_status = family_db.execute(
            "SELECT processing_status, form_resolution_status FROM entries WHERE entry_id='degeret'"
        ).fetchone()
        homograph_construction = family_db.execute(
            "SELECT f.construction FROM family_members fm JOIN families f ON f.family_id=fm.family_id "
            "WHERE fm.entry_id='degeret'"
        ).fetchone()
        if (
            len(set(homograph_families.values())) != 3
            or homograph_edges != 2
            or homograph_status != ("multi-parent-form", "multi-parent-form")
            or homograph_construction != ("ambiguous-form",)
        ):
            failures.append(
                f"multi-parent form bridge regression: {homograph_families!r}, "
                f"edges={homograph_edges}, status={homograph_status!r}, "
                f"construction={homograph_construction!r}"
            )
        family_db.close()

        bound_db = sqlite3.connect(":memory:")
        bound_db.execute("PRAGMA foreign_keys=ON")
        bound_db.execute(
            "CREATE TABLE entries (entry_id TEXT PRIMARY KEY, language TEXT NOT NULL, headword TEXT NOT NULL, "
            "form_of INTEGER NOT NULL, alternative_of INTEGER NOT NULL, "
            "form_targets_json TEXT NOT NULL, alternative_targets_json TEXT NOT NULL, "
            "derived_terms_json TEXT NOT NULL, related_terms_json TEXT NOT NULL, "
            "skeleton TEXT NOT NULL, processing_status TEXT NOT NULL, candidate_count INTEGER NOT NULL, "
            "pos TEXT NOT NULL, form_resolution_status TEXT NOT NULL)"
        )
        bound_db.executemany(
            "INSERT INTO entries VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (str(index), "hebrew", f"lemma{index}", 0, 0, "[]", "[]", "[]", "[]", "hub", "candidate-search-complete-zero", 0, "noun", "not-form")
                for index in range(3)
            ],
        )
        try:
            build_families(bound_db, "hebrew", max_lemma_count=2)
            failures.append("family lemma-count guard failed to stop an oversized family")
        except ValueError as error:
            if "profile limit is 2" not in str(error):
                failures.append(f"family lemma-count guard raised the wrong error: {error}")
        bound_db.close()

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("recovery pipeline: CLEAN (44 rows, 10 fixtures, normalization, sources, families, proof gate)")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
