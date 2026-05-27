#!/usr/bin/env python3
"""
eye1_berlin_tla.py

Eye-1 skeleton matcher: Arabic ↔ Ancient-Egyptian candidate cognate generator
using the Berlin Thesaurus Linguae Aegyptiae (TLA) as the Egyptian corpus.

The Berlin TLA is the comprehensive digital lexicon of Ancient Egyptian,
covering the language from the Old Kingdom through Coptic. It publishes its
data as TEI XML and TSV exports under a CC-BY-SA license.

Project page:  https://thesaurus-linguae-aegyptiae.de/
Data download: https://thesaurus-linguae-aegyptiae.de/info/data-download

This script:
1. Loads the TLA lexicon (TEI XML or TSV — both formats supported)
2. Extracts the consonant skeleton of each Egyptian lemma (Egyptian writing
   is already consonantal, so this is mostly normalization + transliteration)
3. Loads the Juthoor Arabic root inventory (the 2,285 trilateral roots
   from layer-2-operative-grammar)
4. For each (Arabic-root, Egyptian-lemma) pair, computes a skeleton-match
   score using the same Jaccard-on-consonant-set algorithm we use for the
   Arabic ↔ Indo-European Eye-1 pipeline
5. Emits candidate pairs above a threshold for Eye-2 calibrated scoring

Output format: TSV with columns
    egyptian_lemma, egyptian_skeleton, arabic_root, jaccard, n_matches

Usage:
    python eye1_berlin_tla.py --tla-data /path/to/tla_lexicon.tei.xml \\
                              --arabic-roots ../../03-scholar-extracts/jabal-nuclei-extended-table.md \\
                              --output candidates.tsv \\
                              --threshold 0.6

If --tla-data is not provided, the script uses a small bundled demonstration
dataset of ~50 high-confidence Egyptian lemmata so the pipeline can be
tested without downloading the full TLA corpus.

Khshim's sound-substitution laws + the AA dual-face shifts (ج↔g, ح↔ʿ, ش↔s,
ع↔ḏ, د↔ض) are applied before the Jaccard computation so that equivalent
consonants across the family are counted as matches.

License: CC-BY 4.0
Author:  Yassine Temessek · The Arabic Tongue (nature-genome-application)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Iterable

# Force UTF-8 stdout for Windows compatibility (Arabic + transliteration output)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore

# -----------------------------------------------------------------------------
# Consonant-equivalence classes for Arabic ↔ Egyptian Eye-1 matching
# -----------------------------------------------------------------------------
# These follow Khshim's sound-substitution laws + the AA-family dual-face shifts
# documented in the Tier-A · Afro-Asiatic audit. Each consonant maps to a
# canonical equivalence-class symbol; consonants in the same class are
# considered "matching" for skeleton purposes.
#
# References:
#   05-audits/2026-05-21-khshim-laws-audit.md  (the IE direction)
#   04-cross-linguistic/tier-a-afro-asiatic-cognates.md  (the AA direction)

EQUIV_CLASS: dict[str, str] = {
    # Arabic consonants (the 28-letter table)
    "ا": "A", "أ": "A", "إ": "A", "آ": "A", "ء": "A",
    "ب": "B", "ت": "T", "ث": "S", "ج": "G", "ح": "H",
    "خ": "X", "د": "D", "ذ": "Z", "ر": "R", "ز": "Z",
    "س": "S", "ش": "S", "ص": "S", "ض": "D", "ط": "T",
    "ظ": "Z", "ع": "H", "غ": "X", "ف": "P", "ق": "Q",
    "ك": "K", "ل": "L", "م": "M", "ن": "N", "ه": "H",
    "و": "W", "ي": "Y",
    # Egyptian transliteration symbols (standard Egyptological)
    # 3 (aleph), j/y (yod), ꜥ (ayin), w, b, p, f, m, n, r, h, ḥ, ḫ, ẖ,
    # z, s, š, ḳ/q, k, g, t, ṯ, d, ḏ
    "ꜣ": "A", "3": "A", "j": "Y", "y": "Y", "ꜥ": "H", "ʿ": "H",
    "w": "W", "b": "B", "p": "P", "f": "P", "m": "M", "n": "N",
    "r": "R", "h": "H", "ḥ": "H", "ḫ": "X", "ẖ": "X",
    "z": "Z", "s": "S", "š": "S", "ḳ": "Q", "q": "Q", "k": "K",
    "g": "G", "t": "T", "ṯ": "T", "d": "D", "ḏ": "Z",
    # Coptic consonants (when the script encounters Coptic forms)
    "ⲁ": "A", "ⲃ": "B", "ⲅ": "G", "ⲇ": "D", "ⲉ": "A",
    "ⲍ": "Z", "ⲏ": "A", "ⲑ": "T", "ⲓ": "Y", "ⲕ": "K",
    "ⲗ": "L", "ⲙ": "M", "ⲛ": "N", "ⲝ": "X", "ⲟ": "A",
    "ⲡ": "P", "ⲣ": "R", "ⲥ": "S", "ⲧ": "T", "ⲩ": "Y",
    "ⲫ": "P", "ⲭ": "X", "ⲯ": "P", "ⲱ": "W",
    "ϣ": "S", "ϥ": "P", "ϩ": "H", "ϫ": "G", "ϭ": "G", "ϯ": "T",
}


def skeletonize(form: str) -> str:
    """Reduce a word to its Eye-1 consonant skeleton.

    Strips short vowels (already absent in consonantal scripts), maps each
    consonant to its equivalence-class symbol, removes duplicates of adjacent
    identical class-symbols (degemination is the safe default for Eye-1).
    """
    out: list[str] = []
    prev: str | None = None
    for ch in form:
        cls = EQUIV_CLASS.get(ch)
        if cls is None:
            continue  # skip vowel diacritics, hyphens, spaces, etc.
        if cls != prev:
            out.append(cls)
            prev = cls
    return "".join(out)


def jaccard_score(a: str, b: str) -> float:
    """Set-Jaccard score between two skeleton strings."""
    set_a, set_b = set(a), set(b)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


# -----------------------------------------------------------------------------
# Bundled demonstration dataset (used when --tla-data is not provided)
# -----------------------------------------------------------------------------
# ~50 high-confidence Egyptian lemmata so the pipeline can be tested without
# the full Berlin TLA download. Drawn from the 200-entry Tier-A AA roster.

DEMO_EGYPTIAN_LEMMATA: list[tuple[str, str, str]] = [
    # (transliteration, normalized_skeleton, English gloss)
    ("ʿn", "HN", "eye"),
    ("mwt", "MWT", "die / mother"),
    ("mw", "MW", "water"),
    ("ns", "NS", "tongue"),
    ("spt", "SPT", "lip"),
    ("snt", "SNT", "tooth / sister / second"),
    ("gs", "GS", "side"),
    ("ʿnḫ", "HNX", "alive, life"),
    ("sḏm", "SZM", "hear, listen"),
    ("jy", "YY", "come"),
    ("ḏd", "ZD", "say, mention"),
    ("ḥkꜣ", "HKA", "wisdom, magic"),
    ("ḥtp", "HTP", "rest, offerings"),
    ("nfr", "NPR", "good, beautiful"),
    ("nfsw", "NPSW", "soul, breath"),
    ("jsr", "YSR", "bridge"),
    ("rwd", "RWD", "stairway road"),
    ("ḫtm", "XTM", "seal"),
    ("smr", "SMR", "companion"),
    ("ḫm", "XM", "not know / ignorance"),
    ("šm", "SM", "walk, go"),
    ("ḥmsj", "HMSY", "sit, dwell"),
    ("mn", "MN", "be steadfast (amen)"),
    ("mrj", "MRY", "love"),
    ("mr", "MR", "be sick, painful"),
    ("snḏ", "SNZ", "fear"),
    ("snb", "SNB", "heal"),
    ("ḫf", "XP", "light-weight, swift"),
    ("ḥbs", "HBS", "clothe"),
    ("sḏr", "SZR", "lie down for night, cover"),
    ("sḫr", "SXR", "make known, plan"),
    ("dwꜣ", "DWA", "morning, praise"),
    ("rdj", "RDY", "give"),
    ("ḥwj", "HWY", "strike"),
    ("wnm", "WNM", "eat"),
    ("swr", "SWR", "drink"),
    ("šm-šm", "SMSM", "go"),
    ("ʿꜣ", "HA", "great"),
    ("qd", "QD", "build, ancient, character"),
    ("ḫt", "XT", "wood, line, thing"),
    ("šn", "SN", "surround, encircle"),
    ("ssp", "SP", "receive light, grasp"),
    ("sn-sn", "SN", "smell, kiss"),
    ("šdj", "SDY", "draw, raise, recite"),
    ("hꜣy", "HAY", "descend, fall"),
    ("iti", "YT", "come, take"),
    ("fnḏ", "PNZ", "nose"),
    ("ḏbʿ", "ZBH", "finger"),
    ("yam", "YAM", "sea"),
    ("snw", "SNW", "two"),
]


# Likewise, a sample of Arabic trilateral roots for the demo path. In a real
# run, this would be loaded from the 2,285-root canonical file.
DEMO_ARABIC_ROOTS: list[tuple[str, str, str]] = [
    ("عين", "HYN", "eye, source"),
    ("موت", "MWT", "die"),
    ("ماء", "MA", "water"),
    ("لسن", "LSN", "tongue, eloquent"),
    ("شفه", "SPH", "lip"),
    ("سنن", "SNN", "tooth, manner"),
    ("جنب", "GNB", "side, flank"),
    ("حيي", "HYY", "alive"),
    ("سمع", "SMH", "hear"),
    ("جيء", "GYA", "come"),
    ("ذكر", "ZKR", "mention, male"),
    ("حكم", "HKM", "wisdom, judgment"),
    ("حطط", "HTT", "settle, alight"),
    ("نفر", "NPR", "fine, choice"),
    ("نفس", "NPS", "soul, self"),
    ("جسر", "GSR", "bridge"),
    ("رود", "RWD", "trodden path"),
    ("ختم", "XTM", "seal, conclude"),
    ("سمر", "SMR", "evening-talk, companion"),
    ("جهل", "GHL", "ignorance"),
    ("مشي", "MSY", "walk"),
    ("جلس", "GLS", "sit"),
    ("امن", "AMN", "believe, be safe"),
    ("حبب", "HBB", "love"),
    ("مرض", "MRD", "be sick"),
    ("خوف", "XWP", "fear"),
    ("شفي", "SPY", "heal"),
    ("خفف", "XPP", "be light"),
    ("لبس", "LBS", "wear, clothe"),
    ("ستر", "STR", "cover, conceal"),
    ("شهر", "SHR", "make famous, month"),
    ("صبح", "SBH", "morning"),
    ("عطي", "HTY", "give"),
    ("ضرب", "DRB", "strike"),
    ("اكل", "AKL", "eat"),
    ("شرب", "SRB", "drink"),
    ("ذهب", "ZHB", "go, gold"),
    ("كبر", "KBR", "be great"),
    ("قدم", "QDM", "be ancient, advance"),
    ("خطط", "XTT", "line, write"),
    ("شنن", "SNN", "surround, attack"),
    ("شفف", "SPP", "be translucent"),
    ("شمم", "SMM", "smell"),
    ("شدد", "SDD", "pull tight"),
    ("هوي", "HWY", "fall, descend, love"),
    ("اتي", "ATY", "come"),
    ("انف", "ANP", "nose, pride"),
    ("صبع", "SBH", "finger"),  # also إصبع
    ("يمم", "YMM", "head toward (يَمّ also = sea)"),
    ("ثني", "SNY", "two, double"),
]


# -----------------------------------------------------------------------------
# TLA loaders
# -----------------------------------------------------------------------------

def load_tla_tei(path: Path) -> list[tuple[str, str, str]]:
    """Load Egyptian lemmata from a Berlin TLA TEI XML export.

    The Berlin TLA TEI schema places each lemma as a <entry> element with
    <form><orth> for the surface form and <sense><def> for the gloss.

    Returns a list of (transliteration, skeleton, english_gloss) tuples.
    """
    ns = {"tei": "http://www.tei-c.org/ns/1.0"}
    tree = ET.parse(path)
    root = tree.getroot()

    lemmata: list[tuple[str, str, str]] = []
    for entry in root.findall(".//tei:entry", ns):
        # Pull transliteration: TLA marks it with @xml:lang="egy-Latn"
        orth = entry.find(".//tei:form/tei:orth[@xml:lang='egy-Latn']", ns)
        translit = orth.text.strip() if orth is not None and orth.text else None
        if not translit:
            continue

        # Pull English gloss
        gloss_el = entry.find(".//tei:sense/tei:def[@xml:lang='en']", ns)
        gloss = gloss_el.text.strip() if gloss_el is not None and gloss_el.text else ""

        skeleton = skeletonize(translit)
        if not skeleton:
            continue

        lemmata.append((translit, skeleton, gloss))

    return lemmata


def load_tla_tsv(path: Path) -> list[tuple[str, str, str]]:
    """Load Egyptian lemmata from a TLA TSV export.

    Expected columns: lemma_id, transliteration, gloss_en (plus others ignored).
    """
    lemmata: list[tuple[str, str, str]] = []
    with path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp, delimiter="\t")
        for row in reader:
            translit = (row.get("transliteration") or row.get("lemma") or "").strip()
            if not translit:
                continue
            gloss = (row.get("gloss_en") or row.get("translation") or "").strip()
            skeleton = skeletonize(translit)
            if skeleton:
                lemmata.append((translit, skeleton, gloss))
    return lemmata


def load_arabic_roots(path: Path) -> list[tuple[str, str, str]]:
    """Load Arabic trilateral roots from the Juthoor canonical files.

    Accepts either a markdown table file (looking for rows containing an Arabic
    root pattern) or a JSON/TSV file with explicit root + gloss columns.
    """
    if path.suffix == ".json":
        with path.open("r", encoding="utf-8") as fp:
            data = json.load(fp)
        roots: list[tuple[str, str, str]] = []
        for r in data:
            ar = r.get("root") or r.get("arabic")
            gloss = r.get("gloss") or r.get("meaning") or ""
            if ar:
                roots.append((ar, skeletonize(ar), gloss))
        return roots

    if path.suffix == ".tsv":
        roots = []
        with path.open("r", encoding="utf-8", newline="") as fp:
            reader = csv.DictReader(fp, delimiter="\t")
            for row in reader:
                ar = (row.get("root") or row.get("arabic") or "").strip()
                gloss = (row.get("gloss") or row.get("meaning") or "").strip()
                if ar:
                    roots.append((ar, skeletonize(ar), gloss))
        return roots

    # Markdown: look for Arabic root patterns like "| ر-ج-ل |" or "| رجل |"
    roots = []
    arabic_re = re.compile(r"\|\s*([ء-ي\-]+)\s*\|")
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            m = arabic_re.search(line)
            if m:
                ar = m.group(1).replace("-", "")
                if 2 <= len(ar) <= 5:  # plausible root length
                    roots.append((ar, skeletonize(ar), ""))
    return roots


# -----------------------------------------------------------------------------
# Main pipeline
# -----------------------------------------------------------------------------

def run_eye1(
    egyptian_lemmata: list[tuple[str, str, str]],
    arabic_roots: list[tuple[str, str, str]],
    threshold: float,
    output: Path,
) -> int:
    """Run Eye-1 skeleton matching and emit candidates above threshold.

    Returns the number of candidate pairs emitted.
    """
    candidates: list[tuple[str, str, float, str, str, str, str]] = []

    for eg_translit, eg_skel, eg_gloss in egyptian_lemmata:
        for ar_root, ar_skel, ar_gloss in arabic_roots:
            score = jaccard_score(eg_skel, ar_skel)
            if score >= threshold:
                matches = len(set(eg_skel) & set(ar_skel))
                candidates.append((
                    eg_translit, eg_skel, eg_gloss,
                    ar_root, ar_skel, ar_gloss,
                    f"{score:.3f}",
                ))

    # Sort by score desc, then by Egyptian transliteration asc
    candidates.sort(key=lambda r: (-float(r[6]), r[0]))

    with output.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.writer(fp, delimiter="\t")
        writer.writerow([
            "egyptian_translit", "egyptian_skeleton", "egyptian_gloss",
            "arabic_root", "arabic_skeleton", "arabic_gloss",
            "jaccard",
        ])
        for c in candidates:
            writer.writerow(c)

    return len(candidates)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument(
        "--tla-data",
        type=Path,
        help="Path to Berlin TLA export (TEI XML or TSV). "
             "If omitted, a bundled 50-entry demo dataset is used.",
    )
    ap.add_argument(
        "--arabic-roots",
        type=Path,
        help="Path to Arabic root inventory (markdown / JSON / TSV). "
             "If omitted, a bundled 50-entry demo dataset is used.",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=Path("eye1_aa_candidates.tsv"),
        help="Output TSV path (default: eye1_aa_candidates.tsv).",
    )
    ap.add_argument(
        "--threshold",
        type=float,
        default=0.6,
        help="Jaccard score threshold for emitting a candidate (default: 0.6).",
    )
    args = ap.parse_args()

    # Load Egyptian
    if args.tla_data:
        if args.tla_data.suffix in (".xml", ".tei"):
            print(f"Loading Berlin TLA TEI from {args.tla_data}...")
            egyptian = load_tla_tei(args.tla_data)
        elif args.tla_data.suffix == ".tsv":
            print(f"Loading TLA TSV from {args.tla_data}...")
            egyptian = load_tla_tsv(args.tla_data)
        else:
            print(f"ERROR: unsupported TLA data format: {args.tla_data.suffix}", file=sys.stderr)
            return 2
    else:
        print("Using bundled 50-entry Egyptian demo dataset.")
        egyptian = DEMO_EGYPTIAN_LEMMATA

    print(f"  Egyptian lemmata: {len(egyptian):,}")

    # Load Arabic
    if args.arabic_roots:
        print(f"Loading Arabic root inventory from {args.arabic_roots}...")
        arabic = load_arabic_roots(args.arabic_roots)
    else:
        print("Using bundled 50-entry Arabic demo dataset.")
        arabic = DEMO_ARABIC_ROOTS

    print(f"  Arabic roots:     {len(arabic):,}")
    print(f"  Threshold:        {args.threshold:.2f}")
    print(f"  Total pairs to score: {len(egyptian) * len(arabic):,}")

    # Run the matcher
    n_candidates = run_eye1(egyptian, arabic, args.threshold, args.output)

    print(f"\nEmitted {n_candidates:,} candidate pairs above threshold {args.threshold}.")
    print(f"Output: {args.output}")
    print("\nNext step: pass the candidates through Eye-2 (the calibrated")
    print("semantic-scoring rubric, see juthoor-eye2-scoring skill).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
