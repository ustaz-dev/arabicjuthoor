#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
import zipfile
from pathlib import Path

from recovery_pipeline.candidates import ArabicInventory, generate_hits
from recovery_pipeline.families import (
    build_families,
    clear_language_families,
    family_review_queue,
    load_family_review_states,
    target_alternatives,
)
from recovery_pipeline.inventory import load_review_states
from recovery_pipeline.network import compile_network, rules_by_id
from recovery_pipeline.normalization import apply_zero_step, available_profiles, detect_language, load_profile, normalize
from recovery_pipeline.sources import (
    iter_aed_html_zip,
    iter_coptic_tei,
    iter_kaikki,
    verify_source_pin,
)
from recovery_pipeline.proof import load_preregistration, require_execution_authority
from export_egyptian_gap_cards import candidate_text, rank_window, sound_path_text
from search_arabic_root_senses import DEFAULT_RESOURCES, independent_fan, root_sense_fan


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "scripts" / "recovery_pipeline" / "network-fixtures.json"


def main() -> int:
    failures: list[str] = []
    fan_fixtures = {
        "صبر": [
            {
                "collection": "arabic_roots_hf",
                "source": "لسان العرب لابن منظور",
                "definition": "الصبرة الطعام المجتمع",
            },
            {
                "collection": "Ten dictionaries for Arabic language",
                "source": "Tag Al-‘Arus Min Gawahir Al-Qamus7.csv",
                "definition": "",
            },
            {
                "collection": "arabic_roots_hf",
                "source": "تاج اللغة وصِحاح العربية للجوهري",
                "definition": "الصبر الحبس والجمع",
            },
        ],
        "عين": [
            {
                "collection": "arabic_roots_hf",
                "source": "تاج العروس لمرتضى الزبيدي",
                "definition": "العين حاسة البصر",
            },
            {
                "collection": "arabic_roots_hf",
                "source": "المحكم والمحيط الأعظم لابن سيده الأندلسي",
                "definition": "العين حاسة البصر",
            },
        ],
    }
    for root, matches in fan_fixtures.items():
        fan = independent_fan(matches)
        selected = fan["selected_sources"]
        if not fan["complete"] or len(selected) != 2:
            failures.append(f"Arabic independent fan fallback incomplete for {root}")
        if not fan["fallback_used"]:
            failures.append(f"Arabic independent fan failed to name fallback for {root}")
        if len({item["source_id"] for item in selected}) != len(selected):
            failures.append(f"Arabic fan counted duplicate editions as sources for {root}")
        if any(not item["definition"].strip() for item in selected):
            failures.append(f"Arabic fan selected an empty definition for {root}")
    truncated_batn = root_sense_fan(DEFAULT_RESOURCES, "بطن", 1200)
    if not truncated_batn["truncated"] or truncated_batn["independent_fan"]["judgment_ready"]:
        failures.append("Arabic fan truncation guard failed for بطن")
    full_batn = root_sense_fan(DEFAULT_RESOURCES, "بطن", None)
    full_text = " ".join(item["definition"] for item in full_batn["matches"])
    if full_batn["truncated"] or "المرأة" not in full_text or "ولد" not in full_text:
        failures.append("Arabic fan full-text recovery regression for بطن")
    ranked_fixture = [
        {"family_id": "egyptian:family:000000000000000000000001"},
        {"family_id": "egyptian:family:000000000000000000000002"},
        {"family_id": "egyptian:family:000000000000000000000003"},
    ]
    if [
        item["family_id"] for item in rank_window(ranked_fixture, 2, 3)
    ] != [
        "egyptian:family:000000000000000000000002",
        "egyptian:family:000000000000000000000003",
    ]:
        failures.append("Egyptian rank-window regression")
    try:
        rank_window(ranked_fixture, 3, 4)
        failures.append("Egyptian rank-window accepted an incomplete range")
    except ValueError:
        pass
    candidate_fixture = [{
        "kind": "root",
        "form": "كتب",
        "reading": "test",
        "status": "licensed",
        "rule_ids": ["DENT-05"],
        "route_required": False,
    }]
    if "DENT-05" not in candidate_text(candidate_fixture, {"root"}, 3):
        failures.append("Egyptian candidate display lost retrieval provenance")
    if "DENT-05" in sound_path_text() or "لا يذكر صف حكم" not in sound_path_text():
        failures.append("Egyptian non-verdict sound path cites an unnecessary shift row")
    if target_alternatives("alpha+beta/gamma") != ("alpha", "beta", "gamma"):
        failures.append("family-target separator regression")
    rules = compile_network()
    indexed = rules_by_id(rules)
    if len(rules) != 47:
        failures.append(f"network row count: expected 47, got {len(rules)}")
    expected = json.loads(FIXTURES.read_text(encoding="utf-8"))
    for row_id, fields in expected.items():
        rule = indexed.get(row_id)
        if rule is None:
            failures.append(f"network fixture missing: {row_id}")
            continue
        for field, value in fields.items():
            got = (
                list(getattr(rule, field))
                if field in {"scopes", "left_tokens", "right_tokens"}
                else getattr(rule, field)
            )
            if got != value:
                failures.append(f"network fixture {row_id}.{field}: {got!r} != {value!r}")

    regressions = {
        ("ancient_greek", "τρεῖς"): ("t", "r", "s"),
        ("coptic", "ϣⲛϥⲉ"): ("sh", "n", "f"),
        ("egyptian", "ꜣpd"): ("qstop", "p", "d"),
        ("egyptian", "šnf.t"): ("sh", "n", "f", "t"),
        ("egyptian", "ḫf"): ("kh", "f"),
        ("egyptian", "sṯj"): ("s", "th", "j"),
        ("egyptian", "H̱nm.w"): ("kh", "n", "m", "w"),
        ("egyptian", "ḥꜣi̯"): ("hh", "qstop", "j"),
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
    aramaic_profile = load_profile("aramaic")
    aramaic_surface = normalize("דהבא", aramaic_profile)
    if aramaic_surface.tokens != ("d", "h", "b", "qstop"):
        failures.append(f"Aramaic letter-boundary regression: {aramaic_surface.tokens!r}")
    emphatic = apply_zero_step("דהבא", "noun", aramaic_profile)
    if not emphatic.applied or emphatic.comparison != "דהב":
        failures.append(f"Aramaic emphatic-aleph stripping failed: {emphatic!r}")
    emphatic_adjective = apply_zero_step("עקרא", "adj", aramaic_profile)
    if not emphatic_adjective.applied or emphatic_adjective.comparison != "עקר":
        failures.append(f"Aramaic emphatic-state adjective stripping failed: {emphatic_adjective!r}")
    verb = apply_zero_step("קטלא", "verb", aramaic_profile)
    if verb.applied or verb.comparison != "קטלא":
        failures.append(f"Aramaic verb lost final aleph: {verb!r}")
    try:
        normalize("τ@", load_profile("ancient_greek"))
        failures.append("strict normalization accepted an unknown symbol")
    except ValueError:
        pass

    inventory = ArabicInventory.load()
    dahab = normalize(emphatic.comparison, aramaic_profile)
    dahab_hits, _ = generate_hits(dahab.tokens, "aramaic", rules, inventory)
    if not any(hit.kind == "root" and hit.form == "ذهب" and hit.status == "licensed" for hit in dahab_hits):
        failures.append("Aramaic emphatic-aleph regression: דהבא did not retrieve ذهب")
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

    # DENT-08 is documentary and deliberately manual. Its branch side stays in
    # native script because the current profiles fold Hebrew tsade with samekh
    # and Aramaic tet with taw. Prove the promised generation delta is exactly
    # zero on both verified anchors and all three named negative controls.
    dent08 = indexed.get("DENT-08")
    if dent08 is None:
        failures.append("DENT-08 zero-delta guard: row missing")
    elif dent08.right_tokens or dent08.automation != "manual":
        failures.append(
            "DENT-08 zero-delta guard: row became generative "
            f"(right_tokens={dent08.right_tokens!r}, automation={dent08.automation!r})"
        )
    else:
        rules_without_dent08 = [rule for rule in rules if rule.row_id != "DENT-08"]
        dent08_delta_cases = {
            "hebrew": ("עצם", "צבי", "טורא", "טלא", "נטר"),
            "aramaic": ("עטמא", "טביא", "נטר"),
        }
        for language, forms in dent08_delta_cases.items():
            profile = load_profile(language)
            for form in forms:
                tokens = normalize(form, profile).tokens
                hits_with, unmapped_with = generate_hits(tokens, language, rules, inventory)
                hits_without, unmapped_without = generate_hits(
                    tokens, language, rules_without_dent08, inventory
                )
                if (hits_with, unmapped_with) != (hits_without, unmapped_without):
                    failures.append(
                        f"DENT-08 generation delta is nonzero for {language} {form}"
                    )
                if any("DENT-08" in hit.rule_ids for hit in hits_with):
                    failures.append(
                        f"DENT-08 leaked into automatic candidates for {language} {form}"
                    )

    load_review_states()
    load_family_review_states()
    preregistration = load_preregistration()
    try:
        require_execution_authority(preregistration)
        failures.append("proof execution gate opened without a signed preregistration and an attested run trigger")
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

    ranking_db = sqlite3.connect(":memory:")
    ranking_db.executescript("""
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE families (
            family_id TEXT PRIMARY KEY, language TEXT NOT NULL, anchor_entry_id TEXT NOT NULL,
            anchor_headword TEXT NOT NULL, construction TEXT NOT NULL, member_count INTEGER NOT NULL,
            lemma_count INTEGER NOT NULL, form_count INTEGER NOT NULL, nonlexical_count INTEGER NOT NULL,
            candidate_bearing_member_count INTEGER NOT NULL
        );
        CREATE TABLE family_members (
            entry_id TEXT PRIMARY KEY, family_id TEXT NOT NULL, role TEXT NOT NULL, link_types_json TEXT NOT NULL
        );
        CREATE TABLE entries (
            entry_id TEXT PRIMARY KEY, language TEXT NOT NULL, processing_status TEXT NOT NULL,
            source_stratum TEXT NOT NULL, source_scope_note TEXT NOT NULL, gloss TEXT NOT NULL
        );
        CREATE TABLE candidates (
            entry_id TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL,
            rule_ids_json TEXT NOT NULL, route_flag INTEGER NOT NULL
        );
    """)
    ranking_db.execute(
        "INSERT INTO meta VALUES ('family_metadata_version:aramaic','7')"
    )
    ranking_families = [
        ("exact-rich", "exact-rich", "rich meaning | second sense", "root", "licensed", "[]", 0),
        ("exact-sparse", "exact-sparse", "one", "root", "licensed", "[]", 0),
        ("shifted-root", "shifted-root", "many detailed meanings", "root", "licensed", '["ROW-1"]', 0),
        ("exact-nucleus", "exact-nucleus", "many more detailed meanings than any root", "nucleus", "licensed", "[]", 0),
        ("route-root", "route-root", "route only", "root", "licensed", "[]", 1),
    ]
    for family_id, headword, gloss, kind, status, rule_ids, route_flag in ranking_families:
        entry_id = f"entry-{family_id}"
        ranking_db.execute(
            "INSERT INTO families VALUES (?,?,?,?,?,?,?,?,?,?)",
            (family_id, "aramaic", entry_id, headword, "singleton", 1, 1, 0, 0, 1),
        )
        ranking_db.execute(
            "INSERT INTO family_members VALUES (?,?,?,?)",
            (entry_id, family_id, "lemma", "[]"),
        )
        ranking_db.execute(
            "INSERT INTO entries VALUES (?,?,?,?,?,?)",
            (entry_id, "aramaic", "candidates-generated", "", "", gloss),
        )
        ranking_db.execute(
            "INSERT INTO candidates VALUES (?,?,?,?,?)",
            (entry_id, kind, status, rule_ids, route_flag),
        )
    ranked_ids = [
        item["family_id"]
        for item in family_review_queue(
            ranking_db, "recovery", language="aramaic", limit=10, order="strength"
        )
    ]
    if ranked_ids != [
        "exact-rich", "exact-sparse", "shifted-root", "exact-nucleus", "route-root"
    ]:
        failures.append(f"family strength-order regression: {ranked_ids!r}")
    ranked_basis = family_review_queue(
        ranking_db, "recovery", language="aramaic", limit=1, order="strength"
    )[0].get("strength_basis", {})
    if (
        ranked_basis.get("licensed_full_root") != 1
        or ranked_basis.get("licensed_rule_count") != 0
        or ranked_basis.get("ordering_only") is not True
    ):
        failures.append(f"family strength-basis regression: {ranked_basis!r}")
    ranking_db.close()

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
        scout = temp / "bounded-scout.jsonl"
        scout_rows = [
            {
                "word": "𐤁𐤍", "lang": "Phoenician", "lang_code": "phn", "pos": "noun",
                "senses": [{"glosses": ["son"], "examples": [{
                    "text": "𐤁𐤍", "ref": "sarcophagus inscription", "type": "quotation",
                }]}],
            },
            {
                "word": "𐤏𐤔𐤕𐤓𐤕", "lang": "Phoenician", "lang_code": "phn", "pos": "name",
                "senses": [{"glosses": ["Astarte"]}],
            },
            {
                "word": "*𐤐𐤏𐤋", "lang": "Phoenician", "lang_code": "phn", "pos": "verb",
                "senses": [{"glosses": ["reconstructed verb"], "tags": ["reconstruction"]}],
            },
        ]
        scout.write_text(
            "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in scout_rows),
            encoding="utf-8",
        )
        scoped = list(iter_kaikki(
            scout,
            "sample-scout",
            expected_language_code="phn",
            source_scope_note="استطلاع محدود",
            expected_entries=3,
            bounded_scout=True,
        ))
        if [item.source_stratum for item in scoped] != [
            "inscription-attestation", "proper-name", "reconstruction",
        ]:
            failures.append(
                f"bounded-scout source-stratum regression: {[item.source_stratum for item in scoped]!r}"
            )
        if any(item.source_scope_note != "استطلاع محدود" for item in scoped):
            failures.append("bounded-scout scope-note regression")
        try:
            list(iter_kaikki(
                scout,
                "sample-scout",
                expected_language_code="xpu",
                source_scope_note="استطلاع محدود",
                expected_entries=3,
                bounded_scout=True,
            ))
            failures.append("bounded-scout language mismatch was not rejected")
        except ValueError as error:
            if "line 1" not in str(error):
                failures.append("bounded-scout language error omitted its line number")
        try:
            list(iter_kaikki(
                scout,
                "sample-scout",
                expected_language_code="phn",
                source_scope_note="استطلاع محدود",
                expected_entries=4,
                bounded_scout=True,
            ))
            failures.append("bounded-scout entry-count mismatch was not rejected")
        except ValueError:
            pass
        empty_senses = temp / "bounded-scout-empty-senses.jsonl"
        empty_senses.write_text(
            json.dumps({
                "word": "𐤁𐤍", "lang": "Phoenician", "lang_code": "phn",
                "pos": "noun", "senses": [],
            }, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        try:
            list(iter_kaikki(
                empty_senses,
                "sample-scout",
                expected_language_code="phn",
                source_scope_note="استطلاع محدود",
                expected_entries=1,
                bounded_scout=True,
            ))
            failures.append("bounded-scout empty senses were not rejected")
        except ValueError:
            pass
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
        aed_zip = temp / "aed.zip"
        aed_page = """<!DOCTYPE html><html><head>
<title>AED - Dictionary entry: šnf.t</title></head><body>
<h1 class="main_title">&nbsp;šnf.t</h1>
<h2 class="second_level">&nbsp;Main information</h2>
<div class="tooltip">&#x2022; Fischschuppe
<span class="tooltiptext">german translation</span></div>
<div class="tooltip">&#x2022; fish scale
<span class="tooltiptext">english translation</span></div>
<div class="tooltip">&#x2022; substantive
<span class="tooltiptext">part of speech</span></div>
<div class="tooltip">&#x2022; 7
<span class="tooltiptext">lemma id</span></div>
<div class="tooltip">&#x2022; Wb 4, 519.9
<span class="tooltiptext">bibliographical information</span></div>
<h2 class="second_level">&nbsp;Same root as</h2>
<a href="8.html">šnf, "abziehen" | "strip off"</a>
</body></html>"""
        aed_loan_page = aed_page.replace(
            "šnf.t", "šrm"
        ).replace(
            "fish scale", "peace (Sem. loan word)"
        ).replace(
            "Fischschuppe", "Friedensgruß"
        ).replace(
            "Wb 4, 519.9", "Wb 4, 529.10"
        ).replace(
            "&#x2022; 7", "&#x2022; 8"
        )
        with zipfile.ZipFile(aed_zip, "w") as archive:
            archive.writestr("aed/index.html", "<html><title>AED index</title></html>")
            archive.writestr("aed/7.html", aed_page)
            archive.writestr("aed/8.html", aed_loan_page)
        aed_bytes = aed_zip.read_bytes()
        verify_source_pin(aed_zip, {
            "expected_size_bytes": len(aed_bytes),
            "md5": hashlib.md5(aed_bytes).hexdigest(),
            "sha256": hashlib.sha256(aed_bytes).hexdigest(),
        })
        try:
            verify_source_pin(aed_zip, {"sha256": "0" * 64})
            failures.append("AED source-pin regression accepted the wrong SHA-256")
        except ValueError:
            pass
        aed_sample = list(iter_aed_html_zip(
            aed_zip,
            "sample-aed",
            expected_members=3,
            expected_html_members=3,
            expected_entries=2,
        ))
        if (
            len(aed_sample) != 2
            or aed_sample[0].entry_id != "sample-aed:7"
            or aed_sample[0].headword != "šnf.t"
            or aed_sample[0].gloss != "EN: fish scale | DE: Fischschuppe"
            or aed_sample[0].related_terms != ("šnf",)
            or aed_sample[0].etymology != "[AED bibliography] Wb 4, 519.9"
            or aed_sample[0].loan_hint
            or not aed_sample[1].loan_hint
        ):
            failures.append(f"synthetic AED parser regression: {aed_sample!r}")

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
        family_db.execute(
            "ALTER TABLE entries ADD COLUMN variants_json TEXT NOT NULL DEFAULT '[]'"
        )
        family_db.execute(
            "ALTER TABLE entries ADD COLUMN gloss TEXT NOT NULL DEFAULT ''"
        )
        family_db.executemany(
            "INSERT INTO entries "
            "(entry_id,language,headword,form_of,alternative_of,form_targets_json,"
            "alternative_targets_json,derived_terms_json,related_terms_json,skeleton,"
            "processing_status,candidate_count,pos,form_resolution_status,variants_json,gloss) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (
                    "butcher-m", "hebrew", "טבחא", 0, 0, "[]", "[]", "[]", "[]",
                    "tbhq", "candidates-generated", 1, "noun", "not-form",
                    '["טבחא", "טבחתא"]', "butcher",
                ),
                (
                    "butcher-f", "hebrew", "טבחתא", 0, 0, "[]", "[]", "[]", "[]",
                    "tbhtq", "candidates-generated", 1, "noun", "not-form",
                    '["טבחתא", "טבחא"]', "butcher",
                ),
                (
                    "father", "hebrew", "אבא", 0, 0, "[]", "[]", "[]", "[]",
                    "qbq", "candidates-generated", 1, "noun", "not-form",
                    '["אמא"]', "father",
                ),
                (
                    "mother", "hebrew", "אמא", 0, 0, "[]", "[]", "[]", "[]",
                    "qmq", "candidates-generated", 1, "noun", "not-form",
                    '["אבא"]', "mother",
                ),
                (
                    "brain", "hebrew", "מוח", 0, 0, "[]", "[]", "[]", '["רוח"]',
                    "see-also", "candidates-generated", 1, "noun", "not-form",
                    "[]", "brain",
                ),
                (
                    "spirit", "hebrew", "רוח", 0, 0, "[]", "[]", "[]", '["מוח"]',
                    "see-also", "candidates-generated", 1, "noun", "not-form",
                    "[]", "spirit",
                ),
            ],
        )
        report = build_families(family_db, "hebrew")
        if report["family_members"] != 25:
            failures.append("family membership regression: an entry disappeared")
        variant_families = dict(family_db.execute(
            "SELECT entry_id, family_id FROM family_members "
            "WHERE entry_id IN ('butcher-m','butcher-f')"
        ))
        variant_links = family_db.execute(
            "SELECT COUNT(*) FROM family_edges WHERE link_type='textual-variant' "
            "AND left_entry_id IN ('butcher-m','butcher-f') "
            "AND right_entry_id IN ('butcher-m','butcher-f')"
        ).fetchone()[0]
        if (
            len(variant_families) != 2
            or len(set(variant_families.values())) != 1
            or variant_links != 1
        ):
            failures.append(
                f"explicit head-variant family regression: "
                f"{variant_families!r}, edges={variant_links}"
            )
        gloss_guard_families = dict(family_db.execute(
            "SELECT entry_id, family_id FROM family_members "
            "WHERE entry_id IN ('father','mother')"
        ))
        gloss_guard_edges = family_db.execute(
            "SELECT COUNT(*) FROM family_edges "
            "WHERE link_type='annotation-variant-gloss-textual-variant' "
            "AND left_entry_id IN ('father','mother') "
            "AND right_entry_id IN ('father','mother')"
        ).fetchone()[0]
        if (
            len(gloss_guard_families) != 2
            or len(set(gloss_guard_families.values())) != 2
            or gloss_guard_edges != 1
        ):
            failures.append(
                f"variant gloss guard regression: "
                f"{gloss_guard_families!r}, edges={gloss_guard_edges}"
            )
        related_guard_families = dict(family_db.execute(
            "SELECT entry_id, family_id FROM family_members "
            "WHERE entry_id IN ('brain','spirit')"
        ))
        related_guard_edges = family_db.execute(
            "SELECT COUNT(*) FROM family_edges "
            "WHERE link_type='annotation-related-textual-related' "
            "AND left_entry_id IN ('brain','spirit') "
            "AND right_entry_id IN ('brain','spirit')"
        ).fetchone()[0]
        if (
            len(related_guard_families) != 2
            or len(set(related_guard_families.values())) != 2
            or related_guard_edges != 1
        ):
            failures.append(
                f"related-term family guard regression: "
                f"{related_guard_families!r}, edges={related_guard_edges}"
            )
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
        required_family_indexes = {
            "form_links_resolved_target",
            "relation_links_resolved_target",
            "family_edges_right_entry",
            "families_anchor_entry",
        }
        present_family_indexes = {
            row[1]
            for table in ("form_links", "relation_links", "family_edges", "families")
            for row in family_db.execute(f"PRAGMA index_list('{table}')")
        }
        missing_family_indexes = required_family_indexes - present_family_indexes
        if missing_family_indexes:
            failures.append(
                f"family foreign-key index regression: missing {sorted(missing_family_indexes)!r}"
            )
        clear_language_families(family_db, "hebrew")
        uncleared_family_rows = {
            table: family_db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("form_links", "relation_links", "family_edges", "families", "family_members")
        }
        if any(uncleared_family_rows.values()):
            failures.append(f"family cleanup regression: {uncleared_family_rows!r}")
        family_db.execute("DELETE FROM entries WHERE language='hebrew'")
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
        bound_db.execute(
            "ALTER TABLE entries ADD COLUMN variants_json TEXT NOT NULL DEFAULT '[]'"
        )
        bound_db.execute(
            "ALTER TABLE entries ADD COLUMN gloss TEXT NOT NULL DEFAULT ''"
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
    print(
        "recovery pipeline: CLEAN "
        f"(47 rows, {len(expected)} fixtures, DENT-08 delta zero, normalization, sources, families, proof gate)"
    )
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
