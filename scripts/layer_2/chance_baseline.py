#!/usr/bin/env python3
"""Skeleton-collision chance baseline for the cross-linguistic four-bar rubric.

Question answered: under Khshim's substitution classes (the first bar), how often
would TWO UNRELATED words share a consonant skeleton by pure chance? This bounds
the false-positive rate of the skeleton bar alone, and shows why a 2-consonant
match (e.g. Gemini G-M) is cheap while a 3-consonant match (qarn Q-R-N) is rare.

Method (all assumptions stated, first-order):
  1. Partition the 28 Arabic consonants into Khshim substitution SETS (laws 1-9
     plus the empirically-surfaced tenth). Overlapping membership is allowed and
     is what makes the laws permissive; subs(a) = union of every set containing a.
  2. Per-consonant frequency f(a) is measured from the pooled Arabic forms in the
     nine cross-linguistic rosters (a real, in-domain distribution).
  3. Two independently drawn consonants "match" iff each is in the other's subs
     set. Per-position match probability  q = sum_a sum_b f(a) f(b) [match].
     Modelling BOTH draws from the Arabic inventory/frequency is the stated
     simplification (a fuller model would use each target language's inventory).
  4. An aligned skeleton of length L matches by chance ~ q**L.

Run: python scripts/layer_2/chance_baseline.py
"""
import json, glob, os, sys, unicodedata
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA = os.path.join(ROOT, '04-cross-linguistic', 'data')

CONS = set('ابتثجحخدذرزسشصضطظعغفقكلمنهوي') | {'ء'}
# Khshim substitution sets (laws 1-9) + tenth (t10). Identity is implicit.
SETS = [
    set('ءهحعغخ'),   # L6 gutturals / laryngeals
    set('قكج'),      # L1 K<->Q, L3 j<->K/G
    set('سزشصث'),    # L7 sibilant clade
    set('دتطضذظ'),   # L4 d<->D-emphatic, t10 t<->T, interdental/emphatic dentals
    set('لرنم'),     # L8 liquids / nasals
    set('بمفو'),     # L9 labials
    set('وي'),       # glides
]

def strip(s):
    out = []
    for ch in unicodedata.normalize('NFC', s):
        if ch in 'أإآ': out.append('ء')
        elif ch == 'ؤ' or ch == 'ئ': out.append('ء')
        elif ch == 'ة': out.append('ت')
        elif ch == 'ى': out.append('ي')
        elif ch in CONS: out.append(ch)
        # else: drop diacritics, vowels marks, spaces, latin, punctuation
    return out

def arabic_first_form(field):
    # take the first surface form before a separator, strip the article ال
    f = field.split('/')[0].split('،')[0].split(' ')[0].strip()
    cs = strip(f)
    if len(cs) >= 3 and cs[0] == 'ا' and cs[1] == 'ل':  # leading article
        cs = cs[2:]
    return cs

# 1. frequency from pooled roster Arabic forms
freq = Counter()
n_forms = 0
for fp in glob.glob(os.path.join(DATA, '*.json')):
    d = json.load(open(fp, encoding='utf-8'))
    for e in d.get('entries', []):
        ar = e.get('arabic')
        if not ar: continue
        cs = arabic_first_form(ar)
        if cs:
            freq.update(cs); n_forms += 1
total = sum(freq.values())
f = {c: freq[c] / total for c in freq}

# subs(a): union of every SET containing a, plus identity
def subs(a):
    s = {a}
    for S in SETS:
        if a in S: s |= S
    return s

# 2. per-position match probability q  (frequency-weighted, and uniform for comparison)
letters = [c for c in CONS if c in f]
def match(a, b):
    return (b in subs(a)) and (a in subs(b))

q_freq = 0.0
for a in letters:
    sa = subs(a)
    for b in letters:
        if b in sa and a in subs(b):
            q_freq += f[a] * f[b]

# uniform baseline over the 29-symbol inventory actually seen
U = len(letters)
q_unif = sum(1 for a in letters for b in letters if match(a, b)) / (U * U)

# average substitution-set size (permissiveness)
avg_subs = sum(len(subs(a) & set(letters)) for a in letters) / U

print(f"pooled Arabic forms: {n_forms}   distinct consonants: {U}   total consonant tokens: {total}")
print(f"avg substitution-set size (of {U}): {avg_subs:.1f}  ->  a consonant is 'allowed' to match ~{avg_subs/U*100:.0f}% of the inventory")
print()
print(f"per-position match probability q:")
print(f"   frequency-weighted : q = {q_freq:.3f}")
print(f"   uniform            : q = {q_unif:.3f}")
print()
print("chance that an aligned skeleton matches under the substitution rules (q**L):")
for q, lab in [(q_freq, 'freq-weighted'), (q_unif, 'uniform')]:
    print(f"   [{lab:13s}]  L2 = {q**2*100:5.1f}%   L3 = {q**3*100:5.1f}%   L4 = {q**4*100:5.2f}%")
print()
# how much rarer is a 3-consonant match than a 2-consonant one
print(f"a 3-consonant match is ~{(q_freq**2)/(q_freq**3):.1f}x rarer than a 2-consonant match (freq-weighted).")

# skeleton lengths of the current dashboard windows (for context)
windows = {'qarn':'قرن','thawr':'ثور','zawj':'زوج','jamal':'جمل','sabʿ':'سبع','thalath':'ثلاث','salam':'سلم','rabb':'ربب'}
print("\ndashboard windows, skeleton length:")
for k,v in windows.items():
    print(f"   {k:8s} {v}  len={len(strip(v))}")
