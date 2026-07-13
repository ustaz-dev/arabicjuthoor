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

# catalog rows come in TWO formats, discriminated by cell 4:
#   classic:    | **nucleus** | letters | family reading | count |          (cell4 numeric)
#   six-column: | **nucleus** | letter1-desc | letter2-desc | family reading | count |
# taking cell3 blindly used to leak LETTER descriptions into nucleus readings
cat = open('03-scholar-extracts/jabal-nuclei-catalog.md', encoding='utf-8').read()
def _ar(s): return any(ch in AR_LETTERS for ch in s)
for m in re.finditer(r'^\|\s*\*\*([^*|]+)\*\*[^|]*\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|(?:\s*([^|]*)\|)?', cat, re.M):
    k = norm(m.group(1))
    rec = nuclei.setdefault(k, {'nucleus': m.group(1).strip(), 'sources': []})
    c2, c3, c4 = m.group(2).strip(), m.group(3).strip(), (m.group(4) or '').strip()
    c5 = (m.group(5) or '').strip()
    if re.fullmatch(r'\d+', c4):
        # classic format
        rec['letters'] = c2
        if _ar(c3): rec['jabal_lexicon_reading_ar'] = c3.rstrip('\\ ').strip()
        rec['root_count'] = int(c4)
    elif _ar(c4):
        # six-column format: the nucleus reading is cell 4
        rec['jabal_lexicon_reading_ar'] = c4.rstrip('\\ ').strip()
        rec.setdefault('jabal_letter1_desc_ar', c2)
        rec.setdefault('jabal_letter2_desc_ar', c3)
        if re.fullmatch(r'\d+', c5): rec['root_count'] = int(c5)
    else:
        # six-column with NO family reading recorded (letter descs + roots only)
        rec.setdefault('jabal_letter1_desc_ar', c2)
        rec.setdefault('jabal_letter2_desc_ar', c3)
        if re.fullmatch(r'\d+', c5): rec['root_count'] = int(c5)
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

# undocumented format: | **nucleus** | letter1-desc | letter2-desc | NUCLEUS family reading | ...
und = open('03-scholar-extracts/jabal-nuclei-undocumented.md', encoding='utf-8').read()
for m in re.finditer(r'^\|\s*\*\*([^*|]+)\*\*[^|]*\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|', und, re.M):
    k = norm(m.group(1))
    rec = nuclei.setdefault(k, {'nucleus': m.group(1).strip(), 'sources': []})
    c2, c3, c4 = m.group(2).strip(), m.group(3).strip(), m.group(4).strip()
    def ok(v): return v and v not in ('—', '-') and any(ch in AR_LETTERS for ch in v)
    # the nucleus reading is column 4; columns 2-3 are Jabal's LETTER descriptions
    val = c4 if ok(c4) else ''
    if val and not rec.get('jabal_lexicon_reading_ar'):
        rec['jabal_lexicon_reading_ar'] = val.rstrip('\\ ').strip()
    if ok(c2): rec.setdefault('jabal_letter1_desc_ar', c2)
    if ok(c3): rec.setdefault('jabal_letter2_desc_ar', c3)
    if 'jabal-nuclei-undocumented.md' not in rec['sources']:
        rec['sources'].append('jabal-nuclei-undocumented.md')

# fallback: loose pass over catalog + undocumented for rows my strict patterns missed
def has_ar(s): return any(ch in AR_LETTERS for ch in s)
for src, body in (('jabal-nuclei-catalog.md', cat), ('jabal-nuclei-undocumented.md', und)):
    for m in re.finditer(r'^\|\s*\*\*([^*|]+)\*\*[^|]*\|\s*([^|]*)\|\s*([^|]*)\|', body, re.M):
        k = norm(m.group(1))
        if k in nuclei: continue
        c2, c3 = m.group(2).strip(), m.group(3).strip()
        # for undocumented-format rows the nucleus reading sits in col 4; try it first
        m4 = re.match(r'^\|\s*\*\*[^*|]+\*\*[^|]*\|[^|]*\|[^|]*\|\s*([^|]*)\|', m.group(0)) if src.startswith('jabal-nuclei-undocumented') else None
        c4 = m4.group(1).strip() if m4 else ''
        reading = c4 if (has_ar(c4) and len(c4) > 3) else (c3 if (has_ar(c3) and len(c3) > 3) else (c2 if (has_ar(c2) and len(c2) > 3) else ''))
        rec = {'nucleus': m.group(1).strip(), 'sources': [src + ' (loose parse)']}
        if reading: rec['jabal_lexicon_reading_ar'] = reading
        nuclei[k] = rec

# hygiene: a nucleus is 2-3 Arabic letters; anything else is a swallowed header or
# a mangled row -- exclude it and log it so nothing disappears silently
excluded = []
for k in list(nuclei):
    if not (2 <= len(k) <= 3) or any(ch not in AR_LETTERS for ch in k):
        excluded.append({'row': k, 'reason': 'not a 2-3 letter nucleus (mangled label or swallowed section header)'})
        del nuclei[k]
for rec in nuclei.values():
    for f in ('jabal_lexicon_reading_ar', 'composed_reading_ar'):
        if f in rec and isinstance(rec[f], str):
            rec[f] = rec[f].rstrip('\\ ').strip()

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

# legacy readings: recomposed nuclei keep their old wording as provenance
try:
    LEGACY = json.load(open('data/legacy-readings-2026-07-12.json', encoding='utf-8'))
except FileNotFoundError:
    LEGACY = {}
for k, rec in nuclei.items():
    if k in LEGACY:
        rec['legacy_reading_ar'] = LEGACY[k]

# ---------------- level 1 enrichment: the canonical face registry ----------------
# amendment 3 (2026-07-12): a letter's charge is a full-phased articulation event;
# its registered faces are the phases witnessed by Jabal's nucleus families
try:
    registry = json.load(open('data/juthoor-canonical-registry.json', encoding='utf-8'))
    REG = {r['letter']: r for r in registry['letters']}
    for r in L1:
        reg = REG.get(r['letter'])
        if not reg:
            continue
        r['gesture_event_ar'] = reg['gesture_event_ar']
        r['faces_registered'] = reg['faces']
        if reg.get('manner_ar'):
            r['manner_ar'] = reg['manner_ar']
        r['registry_status'] = registry['status']
    registry_note = registry['law']
except FileNotFoundError:
    registry_note = ''

# ---------------- assemble ----------------
try:
    # Provenance contract: this is the source-tree HEAD from which the export
    # was generated. Commit source changes first, then commit the regenerated
    # JSON separately so the recorded commit is stable and resolvable.
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
     'description': 'The 28 Arabic letters (plus hamza). charge_ar is the legacy one-line charge (frozen reference: 03-scholar-extracts/consensus-letter-charges.md). Per constitutional amendment 3 (2026-07-12, the full-event law): a letter\'s charge is a full-phased articulation event (gesture_event_ar); its registered faces (faces_registered) are the phases of that event witnessed by 2+ of Jabal\'s first-position nucleus families (weak = single witness); the nucleus partner selects the active phase at the binary level exactly as the third radical selects at the trilateral level. Canonical registry: data/juthoor-canonical-registry.json + per-letter dossiers in 03-scholar-extracts/letter-dossiers/ (status: draft pending the author\'s signature).',
     'registry_law_ar': registry_note,
     'count': len(L1), 'letters': L1,
   },
   'level_2_binary_nuclei': {
     'description': 'The binary (two-letter) nuclei: the meaning-seeds. jabal_lexicon_reading_ar = Dr. M. H. Jabal\'s lexicon-derived axial reading; composed_reading_ar/en = the project\'s charge-composed reading (Quran-anchored where quran_anchors is present). Hollow-root rule (constitutional amendment 1, 2026-07-06): hollow roots are binary in origin, the weak middle glide is a vowel-stretcher, so mawt -> m-t, mawj -> m-j, mal -> m-l, ma\' -> m-h; there is no m-w nucleus. field_card marks nuclei with a frozen pre-registered semantic-field card.',
     'count': len(L2), 'nuclei': L2,
     'excluded_rows': excluded,
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
