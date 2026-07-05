#!/usr/bin/env python3
"""Resolve the unlabelled adjudication round against the hidden A/B key, per the
pre-registration (02-architecture/pre-registration-blind-rerating.md).

Reads:  <base>/adjud_outputs/adjud_*.json   (adjudicator verdicts, options unlabelled)
        <base>/adjud_key.json               (which option was pass1 vs pass2, never shown)
        computational/data/pass2_disagreements.json
Writes: computational/data/pass2_adjudications.json  (full log: root, both modes, winner, grounds)
Prints: coverage, winner split (pass1 / pass2 / both-defensible), split by top confusion pairs.

Usage:  python scripts/layer_2/resolve_adjudication.py <scratch_base_dir>
"""
import json, sys, glob, os
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIS = os.path.join(ROOT, 'computational', 'data', 'pass2_disagreements.json')
OUT = os.path.join(ROOT, 'computational', 'data', 'pass2_adjudications.json')

def main(base):
    key = json.load(open(os.path.join(base, 'adjud_key.json'), encoding='utf-8'))
    dis = {d['tri_root']: d for d in json.load(open(DIS, encoding='utf-8'))}
    verdicts = {}
    bad = []
    for fp in sorted(glob.glob(os.path.join(base, 'adjud_outputs', 'adjud_*.json'))):
        for e in json.load(open(fp, encoding='utf-8')):
            t, v = e.get('tri_root'), str(e.get('verdict')).lower().strip()
            if v not in ('1', '2', 'both'): bad.append((t, v))
            verdicts[t] = e
    missing = [t for t in dis if t not in verdicts]
    print(f"coverage: {len(verdicts)}/{len(dis)} · missing {len(missing)} · bad-verdict {len(bad)}")
    if missing[:6]: print('  missing sample:', missing[:6])
    if bad[:6]: print('  bad verdicts:', bad[:6])

    log_rows, split = [], Counter()
    pair_split = {}
    for t, e in verdicts.items():
        if t not in dis: continue
        v = str(e.get('verdict')).lower().strip()
        if v == 'both':
            winner = 'both'
        elif v in ('1', '2'):
            winner = key[t]['option_%s' % v]
        else:
            continue
        split[winner] += 1
        d = dis[t]
        pair = (d['mode_A'], d['mode_B'])
        pair_split.setdefault(pair, Counter())[winner] += 1
        log_rows.append({'tri_root': t, 'mode_pass1': d['mode_A'], 'mode_pass2': d['mode_B'],
                         'winner': winner, 'grounds': e.get('grounds', '')})

    n = sum(split.values())
    print(f"\nresolved n = {n}")
    for k in ('pass1', 'pass2', 'both'):
        print(f"  {k:6s}: {split[k]:5d} = {split[k]/n*100:5.1f}%")

    print("\nresolution inside the top confusion pairs (pass1-mode -> pass2-mode):")
    top = sorted(pair_split.items(), key=lambda kv: -sum(kv[1].values()))[:10]
    for (a, b), c in top:
        tot = sum(c.values())
        print(f"  {a:9s} -> {b:9s} n={tot:4d} · pass1 {c['pass1']/tot*100:4.0f}% · pass2 {c['pass2']/tot*100:4.0f}% · both {c['both']/tot*100:4.0f}%")

    json.dump(sorted(log_rows, key=lambda r: r['tri_root']),
              open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f"\nwrote {OUT} ({len(log_rows)} adjudications)")

if __name__ == '__main__':
    main(sys.argv[1])
