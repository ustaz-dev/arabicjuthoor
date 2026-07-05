#!/usr/bin/env python3
"""Compare the blind Pass 2 mode assignments against Pass 1, per the pre-registration
(02-architecture/pre-registration-blind-rerating.md).

Reads:  computational/data/layer_2_results_v2.jsonl        (Pass 1, master)
        <shards_dir>/shard_*.json                          (Pass 2 blind outputs)
Writes: computational/data/layer_2_pass2.jsonl             (assembled Pass 2)
        computational/data/pass2_disagreements.json        (for the adjudication round)
Prints: coverage check, raw agreement, Cohen's kappa, stance-level agreement,
        confusion pairs (descending), per-mode recall.

Usage:  python scripts/layer_2/compare_pass2.py <shards_dir>
"""
import json, sys, glob, os
from collections import Counter
sys.stdout.reconfigure(encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MASTER = os.path.join(ROOT, 'computational', 'data', 'layer_2_results_v2.jsonl')
OUT_P2 = os.path.join(ROOT, 'computational', 'data', 'layer_2_pass2.jsonl')
OUT_DIS = os.path.join(ROOT, 'computational', 'data', 'pass2_disagreements.json')

MODES = ['CARRY','HOLD','RELEASE','PROJECT','INTENSIFY','BLOCK','DRAIN',
         'CHANNEL','OPERATE','MIX','REVERT','LOANWORD']
STANCE = {**{m:'positive' for m in ['CARRY','HOLD','RELEASE','PROJECT','INTENSIFY']},
          **{m:'negative' for m in ['BLOCK','DRAIN']},
          **{m:'transform' for m in ['CHANNEL','OPERATE','MIX','REVERT']},
          'LOANWORD':'exception'}

def main(shards_dir):
    # Pass 1
    p1 = {}
    with open(MASTER, encoding='utf-8') as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                p1[r['tri_root']] = r
    # Pass 2 assembly
    p2, bad_mode, dup = {}, [], []
    for fp in sorted(glob.glob(os.path.join(shards_dir, 'shard_*.json'))):
        for e in json.load(open(fp, encoding='utf-8')):
            tr, m = e.get('tri_root'), e.get('mode_2')
            if tr in p2: dup.append(tr)
            if m not in MODES: bad_mode.append((tr, m))
            p2[tr] = e
    missing = [t for t in p1 if t not in p2]
    extra = [t for t in p2 if t not in p1]
    print(f"coverage: pass2 {len(p2)}/{len(p1)} · missing {len(missing)} · extra {len(extra)} · dup {len(dup)} · bad-mode {len(bad_mode)}")
    if missing[:8]: print('  missing sample:', missing[:8])
    if bad_mode[:8]: print('  bad modes:', bad_mode[:8])
    if missing or bad_mode or extra:
        print('FIX COVERAGE FIRST (rerun the affected shards); metrics below computed on the intersection.')

    common = [t for t in p1 if t in p2 and p2[t].get('mode_2') in MODES]
    n = len(common)
    conf = Counter()
    agree = 0
    stance_agree = 0
    for t in common:
        a, b = p1[t]['mode'], p2[t]['mode_2']
        conf[(a, b)] += 1
        if a == b: agree += 1
        if STANCE.get(a) == STANCE.get(b): stance_agree += 1

    po = agree / n
    row = Counter(); col = Counter()
    for (a, b), c in conf.items():
        row[a] += c; col[b] += c
    pe = sum(row[m] * col[m] for m in MODES) / (n * n)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float('nan')

    print(f"\nn = {n}")
    print(f"raw mode agreement : {agree}/{n} = {po*100:.1f}%")
    print(f"Cohen's kappa      : {kappa:.3f}  (chance-expected pe = {pe*100:.1f}%)")
    print(f"stance agreement   : {stance_agree}/{n} = {stance_agree/n*100:.1f}%")

    print("\ntop confusion pairs (pass1 -> pass2):")
    dis = [((a, b), c) for (a, b), c in conf.items() if a != b]
    for (a, b), c in sorted(dis, key=lambda x: -x[1])[:12]:
        print(f"  {a:9s} -> {b:9s} {c:4d}")

    print("\nper-mode recall (pass2 found the same mode):")
    for m in MODES:
        tot = row[m]
        if tot: print(f"  {m:9s} {conf[(m,m)]:4d}/{tot:4d} = {conf[(m,m)]/tot*100:5.1f}%")

    # outputs
    with open(OUT_P2, 'w', encoding='utf-8') as f:
        for t in common:
            f.write(json.dumps({'tri_root': t, 'mode_2': p2[t]['mode_2'],
                                'reason_2': p2[t].get('reason_2','')}, ensure_ascii=False) + '\n')
    disagreements = []
    for t in common:
        if p1[t]['mode'] != p2[t]['mode_2']:
            disagreements.append({
                'tri_root': t, 'binary': p1[t]['binary'], 'third': p1[t]['third'],
                'binary_reading_ar': p1[t].get('binary_reading_ar',''),
                'jabal_axial': p1[t].get('jabal_axial',''),
                'L3_charge_ar': p1[t].get('L3_charge_ar',''),
                'mode_A': p1[t]['mode'], 'mode_B': p2[t]['mode_2'],
            })
    json.dump(disagreements, open(OUT_DIS, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
    print(f"\nwrote {OUT_P2} ({n}) and {OUT_DIS} ({len(disagreements)} disagreements)")

if __name__ == '__main__':
    main(sys.argv[1])
