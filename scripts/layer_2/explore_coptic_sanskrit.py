#!/usr/bin/env python3
"""
explore_coptic_sanskrit.py

Advanced Phonosemantic Explorer & Multi-Language Matching Engine.
Integrates equivalents from Juthoor-Linguistic-Genealogy:
- Latin, Ancient Greek, Gothic, Old English, Old Norse, Old Irish, Welsh.
Adds custom maps for:
- Coptic and Sanskrit.

Author: Yassine Temessek · The Arabic Tongue (nature-genome-application)
"""

import json
import sys
from pathlib import Path

# Force UTF-8 stdout and stdin for Windows compatibility
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stdin.encoding and sys.stdin.encoding.lower() != "utf-8":
    sys.stdin.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parents[2]

# -----------------------------------------------------------------------------
# Canonical phoneme-class mapping (used for Jaccard union collapse)
# -----------------------------------------------------------------------------
EQUIV_CLASS: dict[str, str] = {
    # Arabic consonants
    "ا": "A", "أ": "A", "إ": "A", "آ": "A", "ء": "A",
    "ب": "B", "ت": "T", "ث": "S", "ج": "G", "ح": "H",
    "خ": "X", "د": "D", "ذ": "Z", "ر": "R", "ز": "Z",
    "س": "S", "ش": "S", "ص": "S", "ض": "D", "ط": "T",
    "ظ": "Z", "ع": "H", "غ": "X", "ف": "P", "ق": "Q",
    "ك": "K", "ل": "L", "م": "M", "ن": "N", "ه": "H",
    "و": "W", "ي": "Y",
    # Latin characters
    "a": "A", "e": "A", "i": "Y", "o": "A", "u": "W",
    "b": "B", "c": "K", "d": "D", "f": "P", "g": "G",
    "h": "H", "j": "G", "k": "K", "l": "L", "m": "M",
    "n": "N", "p": "P", "q": "Q", "r": "R", "s": "S",
    "t": "T", "v": "P", "w": "W", "x": "X", "y": "Y", "z": "Z",
    # Coptic specific mappings
    "ⲁ": "A", "ⲃ": "B", "ⲅ": "G", "ⲇ": "D", "ⲉ": "A",
    "ⲍ": "Z", "ⲏ": "A", "ⲑ": "T", "ⲓ": "Y", "ⲕ": "K",
    "ⲗ": "L", "ⲙ": "M", "ⲛ": "N", "ⲝ": "X", "ⲟ": "A",
    "ⲡ": "P", "ⲣ": "R", "ⲥ": "S", "ⲧ": "T", "ⲩ": "Y",
    "ⲫ": "P", "ⲭ": "X", "ⲯ": "P", "ⲱ": "W",
    "ϣ": "S", "ϥ": "P", "ϩ": "H", "ϫ": "G", "ϭ": "G", "ϯ": "T",
}

# -----------------------------------------------------------------------------
# Core Language Equivalence Mappings (Sound Law Matrices)
# -----------------------------------------------------------------------------
LATIN_EQUIVALENTS: dict[str, tuple[str, ...]] = {
    "ا": ("a", ""), "أ": ("a", ""), "إ": ("a", ""), "آ": ("a", ""), "ء": ("a", ""),
    "ب": ("b", "p"), "ت": ("t",), "ث": ("th", "s"), "ج": ("j", "g", "c"),
    "ح": ("h",), "خ": ("kh", "h", "g"), "د": ("d", "t"), "ذ": ("dh", "z", "d"),
    "ر": ("r",), "ز": ("z", "s"), "س": ("s",), "ش": ("sh", "s"), "ص": ("s",),
    "ض": ("d",), "ط": ("t",), "ظ": ("z",), "ع": ("", "h"), "غ": ("gh", "g"),
    "ف": ("f", "p"), "ق": ("q", "k", "c", "g"), "ك": ("k", "c"), "ل": ("l",),
    "م": ("m",), "ن": ("n",), "ه": ("h",), "و": ("w", "v", "u"), "ي": ("y", "i"),
}

GREEK_EQUIVALENTS: dict[str, tuple[str, ...]] = {
    "ا": ("", "a"), "أ": ("", "a"), "إ": ("", "a"), "آ": ("", "a"), "ء": ("", "a"),
    "ب": ("b", "p", "ph"), "ت": ("t", "d"), "ث": ("th",), "ج": ("g", "k"),
    "ح": ("kh", "", "h"), "خ": ("kh",), "د": ("d", "t"), "ذ": ("d", "th", "z"),
    "ر": ("r",), "ز": ("z", "s", "d"), "س": ("s",), "ش": ("s", "kh"),
    "ص": ("s", "z"), "ض": ("d", "t"), "ط": ("t", "th"), "ظ": ("z", "d", "th"),
    "ع": ("", "g"), "غ": ("g",), "ف": ("ph", "p", "b"), "ق": ("k", "kh"),
    "ك": ("k", "kh"), "ل": ("l",), "م": ("m",), "ن": ("n",), "ه": ("h", ""),
    "و": ("w", "u", ""), "ي": ("y", "i"),
}

OLD_ENGLISH_EQUIVALENTS: dict[str, tuple[str, ...]] = {
    "ا": ("", "a"), "أ": ("", "a"), "إ": ("", "a"), "آ": ("", "a"), "ء": ("", "a"),
    "ب": ("b", "p"), "ت": ("t", "d"), "ث": ("þ", "th", "t", "s"), "ج": ("g", "c", "j"),
    "ح": ("h",), "خ": ("h", "k", "c"), "د": ("d", "t"), "ذ": ("ð", "th", "d", "z"),
    "ر": ("r",), "ز": ("z", "s"), "س": ("s",), "ش": ("sc", "s", "sh"),
    "ص": ("s",), "ض": ("d",), "ط": ("t",), "ظ": ("z", "d"), "ع": ("", "h"),
    "غ": ("g", ""), "ف": ("f",), "ق": ("c", "k", "cw"), "ك": ("c", "k"),
    "ل": ("l",), "م": ("m",), "ن": ("n",), "ه": ("h", ""), "و": ("w", "v"),
    "ي": ("g", "y", "i"),
}

OLD_IRISH_EQUIVALENTS: dict[str, tuple[str, ...]] = {
    "ا": ("", "a"), "أ": ("", "a"), "إ": ("", "a"), "آ": ("", "a"), "ء": ("", "a"),
    "ب": ("b",), "ت": ("t", "d"), "ث": ("th", "t"), "ج": ("g",), "ح": ("h", ""),
    "خ": ("ch", "k"), "د": ("d", "t"), "ذ": ("d", "th"), "ر": ("r",), "ز": ("s", "z"),
    "س": ("s",), "ش": ("s",), "ص": ("s",), "ض": ("d",), "ط": ("t",), "ظ": ("d", "t"),
    "ع": ("",), "غ": ("g", ""), "ف": ("f", "b"), "ق": ("c", "k"), "ك": ("c", "k"),
    "ل": ("l",), "م": ("m",), "ن": ("n",), "ه": ("h", ""), "و": ("f", "b", ""),
    "ي": ("g", "i", "y"),
}

GOTHIC_EQUIVALENTS: dict[str, tuple[str, ...]] = {
    "ا": ("", "a"), "أ": ("", "a"), "إ": ("", "a"), "آ": ("", "a"), "ء": ("", "a"),
    "ب": ("b", "f"), "ت": ("t", "d"), "ث": ("þ", "th", "t"), "ج": ("g", "k"),
    "ح": ("h",), "خ": ("h", "ƕ", "k"), "د": ("d", "t"), "ذ": ("d", "þ", "z"),
    "ر": ("r",), "ز": ("z", "s"), "س": ("s",), "ش": ("s",), "ص": ("s",),
    "ض": ("d",), "ط": ("t",), "ظ": ("z", "d"), "ع": ("", "h"), "غ": ("g", ""),
    "ف": ("f", "b"), "ق": ("q", "k", "kw"), "ك": ("k",), "ل": ("l",), "م": ("m",),
    "ن": ("n",), "ه": ("h", ""), "و": ("w", "v", "u"), "ي": ("j", "y", "i"),
}

OLD_NORSE_EQUIVALENTS: dict[str, tuple[str, ...]] = {
    "ا": ("", "a"), "أ": ("", "a"), "إ": ("", "a"), "آ": ("", "a"), "ء": ("", "a"),
    "ب": ("b", "f"), "ت": ("t", "d"), "ث": ("þ", "th", "t"), "ج": ("g", "k"),
    "ح": ("h",), "خ": ("h", "k", "g"), "د": ("d", "t"), "ذ": ("ð", "d", "z"),
    "ر": ("r",), "ز": ("r", "z", "s"), "س": ("s",), "ش": ("s",), "ص": ("s",),
    "ض": ("d",), "ط": ("t",), "ظ": ("z", "d"), "ع": ("", "h"), "غ": ("g", ""),
    "ف": ("f", "v"), "ق": ("k", "kv"), "ك": ("k", "g"), "ل": ("l",), "م": ("m",),
    "ن": ("n",), "ه": ("h", ""), "و": ("v", "w", "u"), "ي": ("j", "g", "i"),
}

WELSH_EQUIVALENTS: dict[str, tuple[str, ...]] = {
    "ا": ("", "a"), "أ": ("", "a"), "إ": ("", "a"), "آ": ("", "a"), "ء": ("", "a"),
    "ب": ("b", "p"), "ت": ("t", "d"), "ث": ("th", "t"), "ج": ("g", "c"),
    "ح": ("h", ""), "خ": ("ch", "h"), "د": ("d", "t"), "ذ": ("dd", "d", "th"),
    "ر": ("r", "rh"), "ز": ("s", "z"), "س": ("s",), "ش": ("s",), "ص": ("s",),
    "ض": ("d", "dd"), "ط": ("t",), "ظ": ("dd", "d"), "ع": ("", "h"), "غ": ("g", ""),
    "ف": ("f", "ff", "p", "b"), "ق": ("c", "g"), "ك": ("c", "k"), "ل": ("l", "ll"),
    "م": ("m",), "ن": ("n", "ng"), "ه": ("h", ""), "و": ("w", "f", ""),
    "ي": ("i", "y", "j"),
}

COPTIC_EQUIVALENTS: dict[str, tuple[str, ...]] = {
    "ا": ("ⲁ", "ⲉ", "ⲏ", "ⲟ", ""), "أ": ("ⲁ", "ⲉ", "ⲏ", "ⲟ", ""), "إ": ("ⲁ", "ⲉ", "ⲏ", "ⲟ", ""),
    "آ": ("ⲁ", "ⲉ", "ⲏ", "ⲟ", ""), "ء": ("ⲁ", "ⲉ", "ⲏ", "ⲟ", ""),
    "ب": ("ⲃ", "ⲡ", "ⲫ", "ϥ", "ⲙ"), "ت": ("ⲧ", "ⲑ", "ϯ"), "ث": ("ⲥ", "ⲧ", "ⲑ"),
    "ج": ("ϫ", "ⲅ", "ⲕ", "ϭ"), "ح": ("ϩ", ""), "خ": ("ⲭ", "ⲝ"), "د": ("ⲇ", "ⲧ"),
    "ذ": ("ⲇ", "ⲧ", "ⲍ"), "ر": ("ⲣ", "ⲗ"), "ز": ("ⲍ", "ⲥ"), "س": ("ⲥ",), "ش": ("ϣ", "ⲥ"),
    "ص": ("ⲥ", "ⲍ"), "ض": ("ⲇ",), "ط": ("ⲧ",), "ظ": ("ⲍ", "ⲇ"), "ع": ("", "ϩ"),
    "غ": ("ⲅ", "ⲭ"), "ف": ("ϥ", "ⲫ", "ⲃ", "ⲡ"), "ق": ("ⲕ", "ϭ", "ⲭ"), "ك": ("ⲕ",),
    "ل": ("ⲗ", "ⲣ"), "م": ("ⲙ",), "ن": ("ⲛ",), "ه": ("ϩ", ""), "و": ("ⲱ", "ⲟ", "ⲃ", ""),
    "ي": ("ⲓ", "ⲩ", "ⲏ", ""),
}

SANSKRIT_EQUIVALENTS: dict[str, tuple[str, ...]] = {
    "ا": ("a", "ā", "e", "o", ""), "أ": ("a", "ā", "e", "o", ""), "إ": ("a", "ā", "e", "o", ""),
    "آ": ("a", "ā", "e", "o", ""), "ء": ("a", "ā", "e", "o", ""),
    "ب": ("b", "bh", "p", "ph"), "ت": ("t", "th"), "ث": ("ś", "ṣ", "s", "th"),
    "ج": ("j", "jh", "c", "ch", "g", "gh", "y"), "ح": ("h", ""), "خ": ("kh", "k"),
    "د": ("d", "dh", "t"), "ذ": ("d", "dh", "s"), "ر": ("r", "l"), "ز": ("s", "ś", "ṣ", "y"),
    "س": ("s", "ś", "ṣ"), "ش": ("ś", "ṣ", "s", "c", "ch"), "ص": ("s", "ś", "ṣ"),
    "ض": ("d", "dh"), "ط": ("t", "th"), "ظ": ("d", "dh"), "ع": ("", "h"),
    "غ": ("g", "gh"), "ف": ("p", "ph", "v", "b", "bh"), "ق": ("k", "kh"), "ك": ("k", "kh"),
    "ل": ("l", "r"), "م": ("m",), "ن": ("n", "ṇ", "ñ", "ṅ"), "ه": ("h", ""),
    "و": ("v", "u", "ū", ""), "ي": ("y", "i", "ī", ""),
}

LANGUAGES = {
    "lat": ("Latin", LATIN_EQUIVALENTS),
    "grc": ("Ancient Greek", GREEK_EQUIVALENTS),
    "ang": ("Old English", OLD_ENGLISH_EQUIVALENTS),
    "sga": ("Old Irish", OLD_IRISH_EQUIVALENTS),
    "got": ("Gothic", GOTHIC_EQUIVALENTS),
    "non": ("Old Norse", OLD_NORSE_EQUIVALENTS),
    "cy": ("Welsh", WELSH_EQUIVALENTS),
    "cop": ("Coptic", COPTIC_EQUIVALENTS),
    "skt": ("Sanskrit", SANSKRIT_EQUIVALENTS)
}

def load_sanskrit_db():
    path = ROOT_DIR / "04-cross-linguistic" / "data" / "sanskrit-cognates.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                return data.get("entries", [])
        except Exception:
            pass
    return []

SANSKRIT_DB = load_sanskrit_db()

def load_egyptian_coptic_db():
    path = ROOT_DIR / "04-cross-linguistic" / "data" / "afro-asiatic-200.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                return data.get("entries", [])
        except Exception:
            pass
    return []

# Transliteration character normalization helper for foreign inputs
translit_norm = str.maketrans({
    "ꜣ": "a", "3": "a", "ꜥ": "h", "ʿ": "h", "ḥ": "h", "ḫ": "x", "ẖ": "x",
    "ḳ": "q", "ṯ": "t", "ḏ": "z", "ⲁ": "a", "ⲃ": "b", "ⲅ": "g", "ⲇ": "d",
    "ⲉ": "a", "ⲍ": "z", "ⲏ": "a", "ⲑ": "t", "ⲓ": "y", "ⲕ": "k", "ⲗ": "l",
    "ⲙ": "m", "ⲛ": "n", "ⲝ": "x", "ⲟ": "a", "ⲡ": "p", "ⲣ": "r", "ⲥ": "s",
    "ⲧ": "t", "ⲩ": "y", "ⲫ": "p", "ⲭ": "x", "ⲯ": "p", "ⲱ": "w", "ϣ": "s",
    "ϥ": "p", "ϩ": "h", "ϫ": "g", "ϭ": "g", "ϯ": "t", "ś": "s", "ṣ": "s",
    "ñ": "n", "ṅ": "n", "ṇ": "n", "ā": "a", "ī": "y", "ū": "w", "ē": "a",
    "ō": "a", "θ": "t", "ð": "d", "þ": "t"
})

def clean_arabic(word: str) -> str:
    """Keep only standard Arabic consonants."""
    valid = "ءآأؤإئابةتثجحخدذرزسشصضطظعغفقكلمنهوي"
    return "".join(ch for ch in word if ch in valid)

def clean_foreign(word: str) -> str:
    """Normalize foreign characters to lowercase simple romanized equivalents."""
    cleaned = word.lower().translate(translit_norm)
    return "".join(ch for ch in cleaned if ch.isalnum() or ch == "")

def match_word_pair(arabic_word: str, foreign_word: str, eq_table: dict[str, tuple[str, ...]], metathesis: bool = True, allow_drops: bool = True):
    """Aligns an Arabic root against a foreign target using a specific sound law map."""
    ar_cleaned = clean_arabic(arabic_word)
    for_cleaned = clean_foreign(foreign_word)
    
    if not ar_cleaned or not for_cleaned:
        return 0.0, [], (ar_cleaned, for_cleaned)
        
    matched_pairs = []
    used_for = set()
    weak_arabic = {"ا", "و", "ي", "ه", "ع", "ح", "أ", "إ", "آ", "ء"}
    
    # 1. Bipartite Metathesis check
    if metathesis:
        for i, ar_ch in enumerate(ar_cleaned):
            eqs = eq_table.get(ar_ch, (ar_ch,))
            normalized_eqs = [eq.translate(translit_norm).lower() for eq in eqs]
            
            for j, for_ch in enumerate(for_cleaned):
                if j not in used_for:
                    if for_ch in normalized_eqs or for_ch == ar_ch.translate(translit_norm).lower():
                        matched_pairs.append((ar_ch, for_ch, f"equivalent ({', '.join(eqs)})"))
                        used_for.add(j)
                        break
    else:
        # 2. Sequential in-order alignment
        curr_for = 0
        for ar_ch in ar_cleaned:
            eqs = eq_table.get(ar_ch, (ar_ch,))
            normalized_eqs = [eq.translate(translit_norm).lower() for eq in eqs]
            
            for j in range(curr_for, len(for_cleaned)):
                for_ch = for_cleaned[j]
                if for_ch in normalized_eqs or for_ch == ar_ch.translate(translit_norm).lower():
                    matched_pairs.append((ar_ch, for_ch, f"equivalent ({', '.join(eqs)})"))
                    curr_for = j + 1
                    break
                    
    # Calculate score
    matched_count = len(matched_pairs)
    
    def to_canonical(ch):
        return EQUIV_CLASS.get(ch, ch.lower())

    if allow_drops:
        # filter out unmatched weak consonants from counting against total set size
        filtered_ar = [ch for ch in ar_cleaned if ch not in weak_arabic or ch in [p[0] for p in matched_pairs]]
        filtered_for = [ch for ch in for_cleaned if ch in [p[1] for p in matched_pairs] or ch not in {"a", "e", "i", "o", "u", "h", "y", "w"}]
        
        ar_canon = {to_canonical(ch) for ch in filtered_ar}
        for_canon = {to_canonical(ch) for ch in filtered_for}
        total_set = len(ar_canon | for_canon)
    else:
        ar_canon = {to_canonical(ch) for ch in ar_cleaned}
        for_canon = {to_canonical(ch) for ch in for_cleaned}
        total_set = len(ar_canon | for_canon)
        
    score = matched_count / total_set if total_set > 0 else 0.0
    return min(1.0, score), matched_pairs, (ar_cleaned, for_cleaned)

def print_match_diagnostic(ar_word, for_word, lang_name, score, matched_pairs, skels):
    print(f"\n--- Diagnostic: {ar_word} ↔ {for_word} ({lang_name} rules) ---")
    print(f"Arabic Consonants:  {list(skels[0])}")
    print(f"Normalized Target:  {list(skels[1])}")
    print(f"Flexible Match Score: {score:.3f}")
    print("Consonant Alignments:")
    for c1, c2, reason in matched_pairs:
        print(f"  {c1} ↔ {c2} matched via: {reason}")
    unmatched_ar = [c for c in skels[0] if c not in [p[0] for p in matched_pairs]]
    unmatched_for = [c for c in skels[1] if c not in [p[1] for p in matched_pairs]]
    if unmatched_ar:
        print(f"Unmatched Arabic:   {unmatched_ar}")
    if unmatched_for:
        print(f"Unmatched Target:   {unmatched_for}")

def main():
    print("====================================================")
    print("  JUTHOOR: Multilingual Sound Law Matcher (LV2)     ")
    print("====================================================")
    
    metathesis = True
    allow_drops = True
    
    aa_db = load_egyptian_coptic_db()
    print(f"Loaded {len(aa_db)} Ancient Egyptian/Coptic entries from database.")
    print(f"Bundled {len(SANSKRIT_DB)} Sanskrit reference entries.")
    
    while True:
        print("\nOptions:")
        print("1. Test Custom Word Pair")
        print("2. Search Sanskrit Reference DB")
        print("3. Search Coptic/Egyptian DB")
        print("4. Toggle Options")
        print("5. Exit")
        
        choice = input("Select an option (1-5): ").strip()
        
        if choice == "1":
            ar = input("Enter Arabic word: ").strip()
            foreign = input("Enter Foreign word: ").strip()
            if not ar or not foreign:
                continue
            
            print("\nSelect target language rules:")
            for code, (name, _) in LANGUAGES.items():
                print(f"  {code}: {name}")
            lang_code = input("Enter language code (default 'lat'): ").strip().lower() or "lat"
            if lang_code not in LANGUAGES:
                lang_code = "lat"
                
            lang_name, eq_table = LANGUAGES[lang_code]
            score, matched_pairs, skels = match_word_pair(ar, foreign, eq_table, metathesis, allow_drops)
            print_match_diagnostic(ar, foreign, lang_name, score, matched_pairs, skels)
            
        elif choice == "2":
            query = input("Enter Arabic root or Sanskrit word to search: ").strip()
            print("\nMatching Sanskrit Entries:")
            found = False
            for entry in SANSKRIT_DB:
                if query in entry["arabic"] or query in entry["sanskrit"]:
                    score, matched_pairs, skels = match_word_pair(entry["arabic"], entry["sanskrit"], SANSKRIT_EQUIVALENTS, metathesis, allow_drops)
                    print(f"\n{entry['arabic']} ↔ {entry['sanskrit']} ({entry['gloss']})")
                    print(f"Notes: {entry['notes']}")
                    print(f"Match Score: {score:.3f}")
                    for c1, c2, reason in matched_pairs:
                        print(f"  {c1} ↔ {c2} ({reason})")
                    found = True
            if not found:
                print("No matches found in Sanskrit database.")
                
        elif choice == "3":
            query = input("Enter Arabic root or Egyptian/Coptic word to search: ").strip()
            print("\nMatching Egyptian/Coptic Entries:")
            found = 0
            for entry in aa_db:
                ar = entry.get("arabic", "")
                eg = entry.get("egyptian", "")
                gloss = entry.get("gloss", "")
                verdict = entry.get("verdict", "")
                category = entry.get("category", "")
                
                if query in ar or query in eg:
                    eq_table = COPTIC_EQUIVALENTS if category == "coptic" else GREEK_EQUIVALENTS # Greek overlaps strongly with Egyptological script translits
                    score, matched_pairs, skels = match_word_pair(ar, eg, eq_table, metathesis, allow_drops)
                    print(f"\n{ar} ↔ {eg} ({gloss}) [{verdict}] ({category})")
                    print(f"Match Score: {score:.3f}")
                    for c1, c2, reason in matched_pairs:
                        print(f"  {c1} ↔ {c2} ({reason})")
                    found += 1
                    if found >= 10:
                        print("\n... and more (truncated to 10).")
                        break
            if found == 0:
                print("No matches found in Egyptian/Coptic database.")
                
        elif choice == "4":
            print(f"\nCurrent Options: Metathesis={metathesis}, Allow Drops={allow_drops}")
            opt = input("Toggle Metathesis (y/n) or Toggle Drops (d)? ").strip().lower()
            if opt == 'y':
                metathesis = True
            elif opt == 'n':
                metathesis = False
            elif opt == 'd':
                allow_drops = not allow_drops
            print(f"New Options: Metathesis={metathesis}, Allow Drops={allow_drops}")
            
        elif choice == "5":
            print("Exiting explorer. Goodbye!")
            break
        else:
            print("Invalid choice, please select 1-5.")

if __name__ == "__main__":
    main()
