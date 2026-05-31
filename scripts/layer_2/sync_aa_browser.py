#!/usr/bin/env python3
"""Regenerate the DATA array + stat cards in afro-asiatic.html from the JSON source of truth."""
import json, re, sys
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')

ROOT = 'C:/Users/yassi/AI Projects/The Arabic Tongue (nature-genome-application)/'
d = json.load(open(ROOT + '04-cross-linguistic/data/afro-asiatic-200.json', encoding='utf-8'))
ents = sorted(d['entries'], key=lambda e: e['id'])

def esc(s):
    return s.replace('\\', '\\\\').replace('"', '\\"')

rows = []
for e in ents:
    rows.append('  [%d, "%s", "%s", "%s", "%s", "%s", %d, "%s"],' % (
        e['id'], esc(e['arabic']), esc(e['egyptian']), esc(e['gloss']),
        esc(e['class']), e['verdict'], 1 if e['revelation'] else 0, e['category']))
data_block = 'const DATA = [\n' + '\n'.join(rows) + '\n];'

p = ROOT + 'afro-asiatic.html'
h = open(p, encoding='utf-8').read()
h = re.sub(r'const DATA = \[.*?\];', data_block, h, count=1, flags=re.DOTALL)

dist = Counter(e['verdict'] for e in ents)
rev = sum(1 for e in ents if e['revelation'])
for v, n in [('PERFECT', dist['PERFECT']), ('PROTO-FAMILY', dist['PROTO-FAMILY']),
             ('DUAL-FACE', dist['DUAL-FACE']), ('STRONG', dist['STRONG']),
             ('PARTIAL', dist['PARTIAL']), ('PROVISIONAL', dist['PROVISIONAL'])]:
    h = re.sub(r'(data-verdict-stat="%s"><div class="stat-num">)\d+' % re.escape(v), r'\g<1>%d' % n, h)
n_tot = len(ents)
# revelations stat card (the 🔑 card) — always second-to-last stat
h = re.sub(r'(>)\d+(</div><div class="stat-label">\U0001f511)', r'\g<1>%d\g<2>' % rev, h)
# entry-count references anywhere — make them all track the live total
h = re.sub(r'\b\d+ entries', '%d entries' % n_tot, h)
h = re.sub(r'\b\d+ worked pairs', '%d worked pairs' % n_tot, h)
h = re.sub(r'of \d+ entries', 'of %d entries' % n_tot, h)
h = re.sub(r'مِن \d+ مَدخَل', 'مِن %d مَدخَل' % n_tot, h)
h = re.sub(r'result-count">\d+<', 'result-count">%d<' % n_tot, h)
open(p, 'w', encoding='utf-8').write(h)
print('Browser regenerated: %d rows, %d revelations' % (len(ents), rev))
print('STRONG %d PARTIAL %d PROV %d' % (dist['STRONG'], dist['PARTIAL'], dist['PROVISIONAL']))
