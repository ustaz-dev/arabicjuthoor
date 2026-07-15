#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from recovery_pipeline.candidates import ArabicInventory, generate_hits
from recovery_pipeline.inventory import load_review_states
from recovery_pipeline.network import compile_network, rules_by_id
from recovery_pipeline.normalization import available_profiles, detect_language, load_profile, normalize
from recovery_pipeline.sources import iter_coptic_tei, iter_kaikki


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "scripts" / "recovery_pipeline" / "network-fixtures.json"


def main() -> int:
    failures: list[str] = []
    rules = compile_network()
    indexed = rules_by_id(rules)
    if len(rules) != 42:
        failures.append(f"network row count: expected 42, got {len(rules)}")
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
    required_profile_fields = {
        "profile_version", "language", "preferred_input", "script_map", "vowels", "multi_tokens",
        "single_tokens", "ignored_characters", "zero_step", "relevant_branch_rules",
    }
    for language in available_profiles():
        missing = required_profile_fields - set(load_profile(language))
        if missing:
            failures.append(f"profile {language} missing: {sorted(missing)}")

    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        kaikki = temp / "sample.jsonl"
        row = json.dumps({
            "word": "τρεῖς", "pos": "num", "forms": [{"form": "treîs", "tags": ["romanization"]}],
            "etymology_text": "Inherited", "senses": [{"id": "sample-1", "glosses": ["three"]}],
        }, ensure_ascii=False)
        kaikki.write_text(row + "\n" + row + "\n", encoding="utf-8")
        sample = list(iter_kaikki(kaikki, "sample"))
        if len(sample) != 2 or sample[0].entry_id == sample[1].entry_id:
            failures.append("synthetic Kaikki duplicate-ID regression")
        if sample[0].romanization != "treîs" or sample[0].gloss != "three":
            failures.append("synthetic Kaikki parser regression")
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

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1
    print("recovery pipeline: CLEAN (42 rows, 10 fixtures, 5 normalization cases, source parsers, scoped candidates)")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
