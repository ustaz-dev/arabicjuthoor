#!/usr/bin/env python3
"""Recovery ledger scanner (charter step 16).

Parses every reading file's cards, extracts verdicts and closure states, and
emits data/recovery-ledger.json plus a console queue of everything suspended
(TOOL-GAP / LAW-GAP / SOURCE-GAP / OPEN-CANDIDATE). Cross-references each
blocker against the current instruments and flags cards whose blocker has
since been resolved (a signed shift row now exists, a nucleus now exists in
the catalog) so no connection is ever silently forgotten.

Run:  python scripts/scan_recovery_ledger.py
"""
from __future__ import annotations
import json, re, os, sys, glob, unicodedata

sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

GAPS = ('TOOL-GAP', 'LAW-GAP', 'SOURCE-GAP', 'OPEN-CANDIDATE', 'MORPHOLOGY-GAP')

def cards(path):
    body = open(path, encoding='utf-8').read()
    blocks = re.split(r'(?=^### (?:بطاقة|إعادةُ توسيم))', body, flags=re.M)
    for b in blocks:
        if not (b.startswith('### بطاقة') or b.startswith('### إعادةُ توسيم')):
            continue
        head = b.split('\n', 1)[0]
        title = head.replace('### بطاقة', '').replace('### إعادةُ توسيم', '(إعادةُ توسيم)').strip(' :')
        if '<' in title:
            continue  # template block, not a real card
        verdict = ''
        m = re.search(r'الحكم[^\n]*?:\s*\*{0,2}([A-Z\-]+(?:\s+[^\n*]{0,40})?)', b)
        if m:
            verdict = m.group(1).strip(' *')
        closure = ''
        m = re.search(r'حالةُ? الإغلاق[^\n]*?:\s*\*{0,2}([^\n*]+)', b)
        if m:
            closure = m.group(1).strip()
        gaps = [g for g in GAPS if g in b]
        rows = sorted(set(re.findall(r'\bBR-[A-Z]+-\d+\b', b)))
        nucs = sorted(set(re.findall(r'نواة[ُِ]?\s+\*{0,2}([ء-ي]{2,3})\*{0,2}', b)))
        yield {'file': path.replace('\\', '/'), 'card': title[:80], 'verdict': verdict,
               'closure': closure, 'gaps': gaps, 'row_refs': rows, 'nucleus_refs': nucs}

# current instruments
net = open('04-cross-linguistic/shift-network-draft.md', encoding='utf-8').read()
signed_rows = set(re.findall(r'\bBR-[A-Z]+-\d+\b', net)) | set(re.findall(r'^\|\s*([A-Z]+-\d+)\s*\|', net, re.M))
core = json.load(open('data/juthoor-core-levels.json', encoding='utf-8'))
HM = {'أ': 'ء', 'إ': 'ء', 'آ': 'ء'}
catalog = {''.join(HM.get(c, c) for c in n['nucleus'].replace('-', '').replace(' ', ''))
           for n in core['levels']['level_2_binary_nuclei']['nuclei']}

ledger, open_q, unlocked = [], [], []
for path in sorted(glob.glob('04-cross-linguistic/readings/*.md')):
    for c in cards(path):
        ledger.append(c)
        suspended = bool(c['gaps']) or any(g in c['closure'] for g in GAPS)
        if not suspended:
            continue
        open_q.append(c)
        hints = []
        for rid in c['row_refs']:
            if rid in signed_rows:
                hints.append(f'الصف {rid} موجود الآن في الشبكة')
        for nk in c['nucleus_refs']:
            if nk in catalog:
                hints.append(f'النواة {nk} موجودة الآن في الفهرس')
        if hints:
            unlocked.append((c, hints))

os.makedirs('data', exist_ok=True)
json.dump({'generated_from': 'scan_recovery_ledger.py', 'cards_total': len(ledger),
           'suspended': [c for c in open_q]},
          open('data/recovery-ledger.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print(f'بطاقات ممسوحة: {len(ledger)} | معلقة في الاسترداد: {len(open_q)}')
for c in open_q:
    tags = ','.join(c['gaps']) or c['closure'][:40]
    print(f"  [{tags}] {c['card']}  ({os.path.basename(c['file'])})")
if unlocked:
    print('\nبطاقات انفتح قيدها ويجب العودة إليها:')
    for c, hints in unlocked:
        print(f"  ← {c['card']}: " + '؛ '.join(sorted(set(hints))))
print('\nكتب: data/recovery-ledger.json')
