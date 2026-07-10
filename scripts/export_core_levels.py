#!/usr/bin/env python3
"""Export the three core levels of the Juthoor system into one portable JSON:
level 1 (the 28 letter charges), level 2 (the binary nuclei with their readings),
level 3 (the eleven native composition modes + LOANWORD).

Built ONLY from the canonical in-repo sources; every record carries its source.
Output: data/juthoor-core-levels.json

Run:  python scripts/export_core_levels.py
"""
import json, re, os, sys, subprocess
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

AR_LETTERS = 'ءاأإآبتثجحخدذرزسشصضطظعغفقكلمنهوي'

# ---------------- level 1: the letter charges ----------------
letters = []
txt = open('03-scholar-extracts/consensus-letter-charges.md', encoding='utf-8').read()
for m in re.finditer(r'^\|\s*\*\*([^*|]+)\*\*[^|]*\|\s*([^|]+)\|\s*([^|]*)\|\s*([^|]*)\|', txt, re.M):
    label = m.group(1).strip()
    first = next((ch for ch in label if ch in AR_LETTERS), None)
    if not first:
        continue
    letters.append({
        'letter': first,
        'label': label,
        'charge_ar': m.group(2).strip(),
        'phonetic_note_en': m.group(3).strip(),
        'gloss_en': m.group(4).strip(),
    })
# keep first occurrence per letter (main table before variants section)
seen = set(); L1 = []
for r in letters:
    if r['letter'] not in seen:
        seen.add(r['letter']); L1.append(r)

# ---------------- level 2: the binary nuclei ----------------
nuclei = {}
def norm(n): return n.replace(' ', '').replace('-', '').strip()

# catalog: | **نواة** | letters | jabal lexicon reading | count |
cat = open('03-scholar-extracts/jabal-nuclei-catalog.md', encoding='utf-8').read()
for m in re.finditer(r'^\|\s*\*\*([^*|]+)\*\*[^|]*\|\s*([^|]*)\|\s*([^|]*)\|\s*(\d*)\s*\|', cat, re.M):
    k = norm(m.group(1))
    rec = nuclei.setdefault(k, {'nucleus': m.group(1).strip(), 'sources': []})
    rec['letters'] = m.group(2).strip()
    rec['jabal_lexicon_reading_ar'] = m.group(3).strip()
    if m.group(4): rec['root_count'] = int(m.group(4))
    rec['sources'].append('jabal-nuclei-catalog.md')

# extended: | **نواة** | EN reading | «AR reading» | roots | anchors_n | anchor verses |
ext = open('03-scholar-extracts/jabal-nuclei-extended.md', encoding='utf-8').read()
for m in re.finditer(r'^\|\s*\*\*([^*|]+)\*\*[^|]*\|\s*([^|]+)\|\s*«([^»]*)»\s*\|\s*(\d*)\s*\|\s*(\d*)\s*\|\s*([^|]*)\|', ext, re.M):
    k = norm(m.group(1))
    rec = nuclei.setdefault(k, {'nucleus': m.group(1).strip(), 'sources': []})
    rec['composed_reading_en'] = m.group(2).strip()
    rec['composed_reading_ar'] = m.group(3).strip()
    if m.group(4): rec.setdefault('root_count', int(m.group(4)))
    if m.group(6).strip(): rec['quran_anchors'] = m.group(6).strip()
    rec['sources'].append('jabal-nuclei-extended.md')

# undocumented: rows vary; take nucleus + first non-empty reading cell
und = open('03-scholar-extracts/jabal-nuclei-undocumented.md', encoding='utf-8').read()
for m in re.finditer(r'^\|\s*\*\*([^*|]+)\*\*[^|]*\|\s*([^|]*)\|', und, re.M):
    k = norm(m.group(1))
    rec = nuclei.setdefault(k, {'nucleus': m.group(1).strip(), 'sources': []})
    val = m.group(2).strip()
    if val and val not in ('—', '-') and 'jabal_lexicon_reading_ar' not in rec:
        rec['jabal_lexicon_reading_ar'] = val
    if 'jabal-nuclei-undocumented.md' not in rec['sources']:
        rec['sources'].append('jabal-nuclei-undocumented.md')

# fallback: loose pass over catalog + undocumented for rows my strict patterns missed
def has_ar(s): return any(ch in AR_LETTERS for ch in s)
for src, body in (('jabal-nuclei-catalog.md', cat), ('jabal-nuclei-undocumented.md', und)):
    for m in re.finditer(r'^\|\s*\*\*([^*|]+)\*\*[^|]*\|\s*([^|]*)\|\s*([^|]*)\|', body, re.M):
        k = norm(m.group(1))
        if k in nuclei: continue
        c2, c3 = m.group(2).strip(), m.group(3).strip()
        reading = c3 if (has_ar(c3) and len(c3) > 3) else (c2 if (has_ar(c2) and len(c2) > 3) else '')
        rec = {'nucleus': m.group(1).strip(), 'sources': [src + ' (loose parse)']}
        if reading: rec['jabal_lexicon_reading_ar'] = reading
        nuclei[k] = rec

# frozen field cards: flag the nuclei that carry a frozen pre-registered field card
cards = open('03-scholar-extracts/nucleus-field-cards-draft.md', encoding='utf-8').read()
carded = set()
for m in re.finditer(r'^### بطاقة ([^\s(]+)', cards, re.M):
    carded.add(norm(m.group(1)))
for k, rec in nuclei.items():
    if k in carded:
        rec['field_card'] = 'frozen v1.0 (03-scholar-extracts/nucleus-field-cards-draft.md)'

L2 = sorted(nuclei.values(), key=lambda r: r['nucleus'])

# ---------------- level 3: the modes ----------------
# canon definitions from lv2-operative-grammar.md
lv2 = open('02-architecture/lv2-operative-grammar.md', encoding='utf-8').read()
MODE_STANCE = {'CARRY':'POSITIVE','HOLD':'POSITIVE','RELEASE':'POSITIVE','PROJECT':'POSITIVE','INTENSIFY':'POSITIVE',
               'BLOCK':'NEGATIVE','DRAIN':'NEGATIVE',
               'CHANNEL':'TRANSFORM','OPERATE':'TRANSFORM','MIX':'TRANSFORM','REVERT':'TRANSFORM'}
modes = []
for m in re.finditer(r'^\|\s*\*\*([A-Z]+)\*\*\s*·\s*([^|]+)\|\s*([^|]+)\|\s*([^|]*)\|', lv2, re.M):
    name = m.group(1).strip()
    if name not in MODE_STANCE: continue
    modes.append({'mode': name, 'name_ar': m.group(2).strip(), 'stance': MODE_STANCE[name],
                  'definition_en': m.group(3).strip(), 'canonical_example': m.group(4).strip()})
# corpus counts from the master data
cnt = Counter()
for line in open('computational/data/layer_2_results_v2.jsonl', encoding='utf-8'):
    if line.strip(): cnt[json.loads(line)['mode']] += 1
for r in modes: r['corpus_count'] = cnt.get(r['mode'], 0)
modes.append({'mode': 'LOANWORD', 'name_ar': 'الدَّخيل', 'stance': 'EXCEPTION',
              'definition_en': 'label for the rare non-native root', 'canonical_example': '', 'corpus_count': cnt.get('LOANWORD', 0)})

# ---------------- assemble ----------------
try:
    commit = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
except Exception:
    commit = ''
out = {
 'project': 'Juthoor (The Arabic Tongue) · core three levels export',
 'author': 'Yassine Temessek · Temessek for Research, Publishing & Training',
 'source_repo': 'github.com/ustaz-dev/arabicjuthoor',
 'exported_at_commit': commit,
 'license': 'CC BY-NC-SA 4.0 · attribution required · research use',
 'levels': {
   'level_1_letter_charges': {
     'description': 'The 28 Arabic letters (plus hamza) with one ruling charge each, drawn from the physical articulation gesture. Frozen reference: 03-scholar-extracts/consensus-letter-charges.md. General dual-face rule: every letter carries two semantic faces of one articulation; the third radical selects the active face.',
     'count': len(L1), 'letters': L1,
   },
   'level_2_binary_nuclei': {
     'description': 'The binary (two-letter) nuclei: the meaning-seeds. jabal_lexicon_reading_ar = Dr. M. H. Jabal\'s lexicon-derived axial reading; composed_reading_ar/en = the project\'s charge-composed reading (Quran-anchored where quran_anchors is present). Hollow-root rule (constitutional amendment 1, 2026-07-06): hollow roots are binary in origin, the weak middle glide is a vowel-stretcher, so mawt -> m-t, mawj -> m-j, mal -> m-l, ma\' -> m-h; there is no m-w nucleus. field_card marks nuclei with a frozen pre-registered semantic-field card.',
     'count': len(L2), 'nuclei': L2,
   },
   'level_3_composition_modes': {
     'description': 'The eleven native composition modes (plus the LOANWORD exception label): how the binary nucleus acts on the third radical\'s charge. Canon: 02-architecture/lv2-operative-grammar.md. Honest status (measured 2026-07): a pre-registered blind second reading reproduces the stance at 62% and the exact mode at 38% (kappa 0.305); an example-anchored coding manual (draft: 02-architecture/mode-coding-manual-draft.md) tightens OPERATE and adds tie-break rules, with a pre-registered re-rate protocol pending the author\'s freeze. The count remains 11: the measured drift was an over-broad OPERATE default, not evidence for merging or splitting.',
     'count': len(modes), 'modes': modes,
   },
 },
}
os.makedirs('data', exist_ok=True)
json.dump(out, open('data/juthoor-core-levels.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f"letters: {len(L1)} | nuclei: {len(L2)} (carded: {sum(1 for r in L2 if 'field_card' in r)}) | modes: {len(modes)}")
print("sources per nucleus (sample):", L2[0].get('sources'), '|', L2[1].get('nucleus'))
print("written: data/juthoor-core-levels.json", f"({os.path.getsize('data/juthoor-core-levels.json')//1024} KB)")
