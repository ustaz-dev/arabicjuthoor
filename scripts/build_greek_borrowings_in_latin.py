# -*- coding: utf-8 -*-
"""Build the Greek-loan reserve removed from the Latin denominator.

The source of record is ``build_kaikki_index.look('latin', form)``.  Legacy
harvest manifests called these rows ``fan_empty``; new manifests give them the
opening reason ``greek_borrowing_in_latin``.  Neither spelling is a closure.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import Counter
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_kaikki_index as LEX  # noqa: E402

OUT = ROOT / "data" / "greek-borrowings-in-latin.json"
GREEK_SOURCE = re.compile(
    r"(?i)(?:\b(?:borrowed|derived|taken|translated|transliterated|loaned)\s+"
    r"(?:directly\s+)?from|\bfrom|\bvia)\s+(?:the\s+|a\s+)?"
    r"(?:(?:Ancient|Classical|Koine|Byzantine|Medieval|Modern|Doric|Attic|"
    r"scholarly)\s+)?Greek\b|\bof\s+(?:Ancient\s+|Classical\s+|Koine\s+)?"
    r"Greek\s+origin\b"
)
GREEK_LANGUAGE_MENTION = re.compile(
    r"(?i)\b(?:Ancient|Classical|Koine|Byzantine|Medieval|Modern)?\s*Greek\b"
)
GREEK_CALQUE = re.compile(
    r"(?i)\b(?:a\s+)?calque\s+of\s+(?:Ancient|Classical|Koine)?\s*Greek\b"
)
GREEK_TREE_SOURCE = re.compile(
    r"(?i)\b(?:Ancient|Classical|Koine|Byzantine|Medieval)\s+Greek\b"
    r".{0,120}\bbor\.\s+Latin\b"
)
GREEK_BORROWED_AS = re.compile(
    r"(?i)\bborrowed\s+from\s+(?:a\s+univerbated\s+form\s+of\s+|"
    r"or\s+formed\s+as\s+)(?:Ancient|Classical|Koine|Byzantine|Medieval)?"
    r"\s*Greek\b"
)
TRAILING_FORM_PUNCTUATION = re.compile(r"[؛;,:]+$")

# تقسيمٌ صرفيٌّ يدويٌّ لصور المركبات الاصطلاحية في الطابور.  لا يُستنبط هذا
# من موضع حرف o آليًّا، لأنّ الواو قد تكون من صلب الكلمة أو قد تسقط في النقل.
COMPOUND_ELEMENTS: dict[str, list[str]] = {
    "alexipharmacon": ["alexi", "pharmacon"],
    "amblyopia": ["ambly", "opia"],
    "amphitheatrum": ["amphi", "theatrum"],
    "anencephalia": ["an", "encephalia"],
    "antistrophe": ["anti", "strophe"],
    "antonomasia": ["anti", "onomasia"],
    "anthropologia": ["anthropo", "logia"],
    "anthropophagus": ["anthropo", "phagus"],
    "apocatastasis": ["apo", "catastasis"],
    "apodyterium": ["apo", "dyterium"],
    "archangelus": ["arch", "angelus"],
    "archiepiscopus": ["archi", "episcopus"],
    "archimandrita": ["archi", "mandrita"],
    "archetypus": ["arche", "typus"],
    "argyranche": ["argyr", "anche"],
    "astrologia": ["astro", "logia"],
    "astrologus": ["astro", "logus"],
    "astronomia": ["astro", "nomia"],
    "astronomus": ["astro", "nomus"],
    "bibliotheca": ["biblio", "theca"],
    "boustrophedon": ["bou", "strophedon"],
    "cataphractus": ["cata", "phractus"],
    "catastropha": ["cata", "stropha"],
    "catachresis": ["cata", "chresis"],
    "clepsydra": ["clepsy", "dra"],
    "cosmographia": ["cosmo", "graphia"],
    "cosmographus": ["cosmo", "graphus"],
    "cosmologia": ["cosmo", "logia"],
    "cosmopolites": ["cosmo", "polites"],
    "cryptoporticus": ["crypto", "porticus"],
    "cynocephalus": ["cyno", "cephalus"],
    "dodecaedron": ["dodeca", "edron"],
    "dryophonon": ["dryo", "phonon"],
    "dryopteris": ["dryo", "pteris"],
    "encyclopaedia": ["encyclo", "paedia"],
    "epididymis": ["epi", "didymis"],
    "epistrophe": ["epi", "strophe"],
    "etymologia": ["etymo", "logia"],
    "genioglossus": ["genio", "glossus"],
    "haemorrhagia": ["haemo", "rrhagia"],
    "halipleumon": ["hali", "pleumon"],
    "hemicrania": ["hemi", "crania"],
    "hecatombe": ["hecat", "ombe"],
    "heteroclitus": ["hetero", "clitus"],
    "heterophyllus": ["hetero", "phyllus"],
    "hexameter": ["hexa", "meter"],
    "hieroglyphicus": ["hiero", "glyphicus"],
    "hierographicus": ["hiero", "graphicus"],
    "hippocentaurus": ["hippo", "centaurus"],
    "hippotoxotae": ["hippo", "toxotae"],
    "homophylophilia": ["homo", "phylo", "philia"],
    "homosexualitas": ["homo", "sexualitas"],
    "hoplomachus": ["hoplo", "machus"],
    "hydromantia": ["hydro", "mantia"],
    "hydromantis": ["hydro", "mantis"],
    "hydromel": ["hydro", "mel"],
    "hydrophobia": ["hydro", "phobia"],
    "hydrophobicus": ["hydro", "phobicus"],
    "hydrophobus": ["hydro", "phobus"],
    "hypocaustus": ["hypo", "caustus"],
    "kilogramma": ["kilo", "gramma"],
    "macrocarpus": ["macro", "carpus"],
    "macrocephalus": ["macro", "cephalus"],
    "melanogaster": ["melano", "gaster"],
    "metropolis": ["metro", "polis"],
    "metaplasmus": ["meta", "plasmus"],
    "microcephalus": ["micro", "cephalus"],
    "microcosmus": ["micro", "cosmus"],
    "microscopium": ["micro", "scopium"],
    "necromantia": ["necro", "mantia"],
    "oxydendron": ["oxy", "dendron"],
    "paedagogatus": ["paedagogo", "atus"],
    "paedagogianus": ["paedagogo", "ianus"],
    "polygonum": ["poly", "gonum"],
    "polycephalus": ["poly", "cephalus"],
    "polyanthus": ["poly", "anthus"],
    "polysemus": ["poly", "semus"],
    "polysigma": ["poly", "sigma"],
    "polyspaston": ["poly", "spaston"],
    "pornographia": ["porno", "graphia"],
    "pharmacopola": ["pharmaco", "pola"],
    "philosophicus": ["philo", "sophicus"],
    "photomachinula": ["photo", "machinula"],
    "physiologia": ["physio", "logia"],
    "pittosporum": ["pitto", "sporum"],
    "prognosticon": ["pro", "gnosticon"],
    "pseudopropheta": ["pseudo", "propheta"],
    "pseudoprophetia": ["pseudo", "prophetia"],
    "pseudothyrum": ["pseudo", "thyrum"],
    "psychomantium": ["psycho", "mantium"],
    "pteranodon": ["pterano", "don"],
    "rhinoceros": ["rhino", "ceros"],
    "rhododendron": ["rhodo", "dendron"],
    "sarcophagus": ["sarco", "phagus"],
    "septicaemia": ["septic", "aemia"],
    "struthiocamelinus": ["struthio", "camelinus"],
    "struthiocamelus": ["struthio", "camelus"],
    "synaeresis": ["syn", "aeresis"],
    "sycophanta": ["syco", "phanta"],
    "syllepsis": ["syn", "lepsis"],
    "symphysis": ["syn", "physis"],
    "synagoga": ["syn", "agoga"],
    "synchondrosis": ["syn", "chondrosis"],
    "syndactylus": ["syn", "dactylus"],
    "syzygia": ["syn", "zygia"],
    "technologia": ["techno", "logia"],
    "tetraedrum": ["tetra", "edrum"],
    "tragelaphus": ["trago", "elaphus"],
    "triclinium": ["tri", "clinium"],
    "trigonometria": ["trigono", "metria"],
    "troglodytes": ["troglo", "dytes"],
    "tyrannosaurus": ["tyranno", "saurus"],
    "tyrotarichos": ["tyro", "tarichos"],
    "zoophthalmos": ["zoo", "phthalmos"],
    "zygostates": ["zygo", "states"],
}


def latin_form(value: Any) -> str:
    """Return the lexical form, without punctuation inherited from prose rows."""
    return TRAILING_FORM_PUNCTUATION.sub("", str(value).strip())


def has_greek_lexical_source(etym: str) -> bool:
    """Distinguish Greek lexical ancestry from a merely Greek calque target."""
    return bool(
        GREEK_SOURCE.search(etym)
        or GREEK_TREE_SOURCE.search(etym)
        or GREEK_BORROWED_AS.search(etym)
    ) and not bool(GREEK_CALQUE.search(etym))


def append_phonetic_sweep_rows(rows: list[dict[str, Any]]) -> tuple[int, Counter[int], Counter[str]]:
    """ألحق إحالات المسح الصوتي التي انتخبت مدخلة يونانية الأصل."""
    count = 0
    batch_sizes: Counter[int] = Counter()
    phase_sizes: Counter[str] = Counter()
    manifests = sorted(
        (ROOT / "data").glob("phonetic-sweep-latin-cards-batch-*.json")
    )
    for manifest in manifests:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        batch = int(payload["batch"])
        for row in payload.get("rows") or []:
            if not row.get("greek_redirect"):
                continue
            dictionary = row.get("dictionary") or {}
            entry = dictionary.get("selected_entry") or {}
            etym = str(entry.get("etym") or "")
            if not entry or not has_greek_lexical_source(etym):
                raise AssertionError(
                    f"إحالة المسح اليونانية بلا مدخلة أصل منشورة: {row.get('card_id')}"
                )
            form = latin_form(row.get("word"))
            elements = COMPOUND_ELEMENTS.get(form.casefold(), [])
            phase = str(row.get("phase") or "")
            rows.append({
                "latin_form": form,
                "greek_origin_published": etym,
                "meaning": str(entry.get("en") or ""),
                "card_id": row.get("card_id"),
                "batch": batch,
                "original_index": int(row.get("source_rank") or 0),
                "classification": (
                    "greek_terminological_compound" if elements
                    else "single_greek_loan_in_latin"
                ),
                "elements": elements,
                "lexicon_lookup": {
                    "call": dictionary.get("call"),
                    "path": dictionary.get("lookup_route"),
                    "entries_read_count": dictionary.get("entries_read_count"),
                    "selected_entry": entry,
                },
                "source_register": "phonetic-sweep-latin",
                "source_phase": phase,
                "opening_reason": (
                    "الصورةُ دخيلٌ يونانيٌّ في اللاتينيّة، ومادّتُها "
                    "تُنظَرُ في ملفِّ اليونانيّةِ لا هنا"
                ),
            })
            count += 1
            batch_sizes[batch] += 1
            phase_sizes[phase] += 1
    return count, batch_sizes, phase_sizes


def selected_look_entry(row: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Re-read the Latin branch dictionary and recover the selected entry."""
    # Use the historical query verbatim to recover the exact selected homonym;
    # ``latin_form`` below cleans only the published reserve field.
    hits, path = LEX.look("latin", str(row["form"]))
    selected = (row.get("branch_lexicon") or {}).get("selected") or {}
    if selected:
        for entry in hits:
            if all(
                str(entry.get(key) or "") == str(selected.get(key) or "")
                for key in ("word", "pos", "en")
            ):
                return entry, path
    if len(hits) == 1:
        return hits[0], path
    raise AssertionError(
        f"تعذر تعيين مدخلة قاموس الفرع للصورة {row.get('form')} "
        f"في البطاقة {row.get('card_id')}"
    )


def legacy_or_current_greek_row(row: dict[str, Any], etym: str) -> bool:
    if row.get("open_reason") == "greek_borrowing_in_latin":
        # A few historical rows were opened by the former broad test merely
        # because their etymology named Greek as a calque target.
        return bool(GREEK_LANGUAGE_MENTION.search(etym)) and not bool(
            GREEK_CALQUE.search(etym)
        )
    return (
        row.get("open_reason") == "fan_empty"
        and not (row.get("fan_candidates") or [])
        and bool(GREEK_LANGUAGE_MENTION.search(etym))
        and not bool(GREEK_CALQUE.search(etym))
    )


def build() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    batch_sizes: Counter[int] = Counter()
    all_queue_rows = 0
    manifests = sorted(
        (ROOT / "data").glob("reopened-loan-old-latin-harvest-batch-*.json")
    )
    for manifest in manifests:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        batch = int(payload["batch"])
        manifest_rows = payload.get("rows") or []
        all_queue_rows += len(manifest_rows)
        for row in manifest_rows:
            if row.get("open_reason") not in {
                "fan_empty", "greek_borrowing_in_latin"
            } or (row.get("fan_candidates") or []):
                continue
            entry, path = selected_look_entry(row)
            etym = str(entry.get("etym") or "")
            if not legacy_or_current_greek_row(row, etym):
                continue
            if not GREEK_LANGUAGE_MENTION.search(etym):
                raise AssertionError(f"إحالة يونانية بلا ذكر يوناني: {row['card_id']}")
            form = latin_form(row["form"])
            queried_form = str(row["form"])
            elements = COMPOUND_ELEMENTS.get(form.casefold(), [])
            rows.append({
                "latin_form": form,
                "greek_origin_published": etym,
                "meaning": row["branch_meaning"],
                "card_id": row["card_id"],
                "batch": batch,
                "original_index": row["original_index"],
                "classification": (
                    "greek_terminological_compound" if elements
                    else "single_greek_loan_in_latin"
                ),
                "elements": elements,
                "lexicon_lookup": {
                    "call": f"build_kaikki_index.look('latin', {queried_form!r})",
                    "path": path,
                },
                "source_register": "reopened-loan-old-latin",
                "opening_reason": (
                    "الصورةُ دخيلٌ يونانيٌّ في اللاتينيّة، ومادّتُها "
                    "تُنظَرُ في ملفِّ اليونانيّةِ لا هنا"
                ),
            })
            batch_sizes[batch] += 1
    old_latin_rows = len(rows)
    sweep_rows, sweep_batch_sizes, sweep_phase_sizes = append_phonetic_sweep_rows(rows)
    rows.sort(key=lambda item: (
        item.get("source_register", ""), item["batch"],
        item["original_index"], item["card_id"]
    ))
    compounds = sum(row["classification"] == "greek_terminological_compound" for row in rows)
    return {
        "schema": "greek-borrowings-in-latin-v1",
        "source": "data/branch-lexicons/latin.json via build_kaikki_index.look('latin', form)",
        "policy": (
            "سبب فتح لا وسم إغلاق؛ لا تُطلب مروحة عربية للصورة اللاتينية، "
            "وتُنقل مادتها المنشورة إلى فحص اليونانية"
        ),
        "counts": {
            "card_rows": len(rows),
            "distinct_latin_forms": len({str(row["latin_form"]).casefold() for row in rows}),
            "old_latin_queue_card_rows": old_latin_rows,
            "phonetic_sweep_card_rows": sweep_rows,
            "phonetic_sweep_distinct_latin_forms": len({
                str(row["latin_form"]).casefold() for row in rows
                if row.get("source_register") == "phonetic-sweep-latin"
            }),
            "compound_card_rows": compounds,
            "single_loan_card_rows": len(rows) - compounds,
            "processed_old_latin_queue_rows": all_queue_rows,
            "corrected_latin_denominator": all_queue_rows - old_latin_rows,
            "by_batch": {str(key): batch_sizes[key] for key in sorted(batch_sizes)},
            "phonetic_sweep_by_batch": {
                str(key): sweep_batch_sizes[key] for key in sorted(sweep_batch_sizes)
            },
            "phonetic_sweep_by_phase": {
                key: sweep_phase_sizes[key] for key in sorted(sweep_phase_sizes)
            },
        },
        "rows": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    rendered = json.dumps(build(), ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != rendered:
            print("STALE: data/greek-borrowings-in-latin.json")
            return 1
        print("CLEAN: data/greek-borrowings-in-latin.json")
        return 0
    OUT.write_text(rendered, encoding="utf-8", newline="\n")
    payload = json.loads(rendered)
    print(
        "BUILT: Greek loans in Latin "
        f"{payload['counts']['card_rows']} cards; "
        f"Latin denominator {payload['counts']['corrected_latin_denominator']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
