# -*- coding: utf-8 -*-
"""إعادةُ بناءِ المشتقّاتِ بترتيبِ تبعيّتِها، ثمّ تشغيلُ بوّاباتِ النشرِ كلِّها.

**العطبُ الذي يُنهيه:** مشتقّاتُ المستودعِ تعتمدُ بعضُها على بعض، ونشرُ الموقعِ
يفحصُها كلَّها. وكانَ إعادةُ بناءِ بعضِها دونَ بعضٍ يُبقي واحدًا بائتًا فيسقُطُ
النشر، وقد تجمّدَ الموقعُ بهذا السببِ أحدَ عشرَ يومًا (2026-07-21 إلى 2026-08-01).

الترتيبُ ليسَ اعتباطيًّا: السجلُّ يُبنى من البطاقات، وعدُّ الأسرِ المؤهَّلةِ يُبنى
من السجلّ، ولقطةُ الموقعِ تُبنى منهما جميعًا. فمن عكسَ الترتيبَ بنى على بائت.

الاستعمال:
    python scripts/rebuild_derived.py            بناءٌ ثمّ فحص
    python scripts/rebuild_derived.py --check    فحصٌ فقط، بلا كتابة
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable

# (اسمُ السكربت، وسائطُ البناء)، بترتيبِ التبعيّة
BUILD = [
    ("scan_recovery_ledger.py", []),
    ("count_links.py", ["--json", "data/link-count.json"]),
    ("count_proof_eligible_families.py", []),
    ("build_recovery_loan_registry.py", []),
    ("build_coverage_summary.py", []),
    ("build_lane_data_manifest.py", []),
    ("build_status_snapshot.py", []),
    ("build_lane_b_open_review_queue.py", []),
    ("build_links_showcase.py", []),          # معرضُ صفحةِ الصلات، من البطاقاتِ نفسِها
    ("build_discoveries.py", []),             # روزنامةُ المرشَّحين، من المسحِ نفسِه
]

# بوّاباتُ النشر، بترتيبِ deploy.yml
GATES = [
    ("check_charge_purity.py", []),
    ("check_publication_consistency.py", []),
    ("scan_recovery_ledger.py", ["--check"]),
    ("check_recovery_pipeline.py", []),
    ("check_unicode_language_boundaries.py", []),
    ("extract_hebrew_temporal_witnesses.py", ["--check"]),
    ("build_recovery_loan_registry.py", ["--check"]),
    ("layer_2/check_rosters.py", []),
    ("check_cooke1903_layer.py", []),
    ("rebuild_proof_preregistration.py", ["--check"]),
    ("count_proof_eligible_families.py", ["--check"]),
    ("open_delegated_ruling_cards.py", ["--check"]),
    ("build_blocked_northern_fan_lane_b_queue.py", ["--aggregate", "--check"]),
    ("build_lane_b_open_review_queue.py", ["--check"]),
    ("build_status_snapshot.py", ["--check"]),
    ("compare_cooke_diplomatic_passes.py", ["--check"]),
    # الجسرُ والروزنامةُ يُفحَصانِ هنا لأنّ سجلَّ القرضِ باتَ مرّةً فرُفِضَ النشر،
    # وكلُّ مشتقٍّ لا حارسَ له يبيتُ يومًا ويُوقِفُ الموقع
    ("build_en_ar_bridge.py", ["--check"]),
    ("build_discoveries.py", ["--check"]),
]


def run(script: str, args: list[str]) -> tuple[int, str]:
    path = ROOT / "scripts" / script
    if not path.exists():
        return 0, "غير موجود، تُخطّي"
    proc = subprocess.run(
        [PY, str(path), *args], cwd=ROOT, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    tail = [ln for ln in (proc.stdout or "").splitlines() if ln.strip()]
    line = tail[-1] if tail else (proc.stderr or "").strip().splitlines()[-1:] or [""]
    return proc.returncode, (line if isinstance(line, str) else line[0])[:70]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="لا تبنِ، افحصْ فقط")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if not args.check:
        print("إعادةُ البناءِ بترتيبِ التبعيّة:")
        for script, argv in BUILD:
            code, line = run(script, argv)
            mark = "  " if code == 0 else "!!"
            print(f" {mark} {script:42} {line}")

    print("\nبوّاباتُ النشر:")
    failed = []
    for script, argv in GATES:
        code, line = run(script, argv)
        if code != 0:
            failed.append(script)
        mark = "  " if code == 0 else "!!"
        print(f" {mark} {script:42} {line}")

    if failed:
        print(f"\nRESULT: {len(failed)} gate(s) failing: {', '.join(failed)}")
        return 1
    print("\nRESULT: all deploy gates pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
