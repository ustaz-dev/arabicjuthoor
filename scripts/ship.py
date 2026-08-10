# -*- coding: utf-8 -*-
"""البناءُ والفحصُ والإيداعُ في خطوةٍ واحدةٍ لا تنفصل (2026-08-10)

**العطبُ الذي يُنهيه، وقد وقعَ ثلاثَ مرّاتٍ في ثلاثةِ أيّام:** المشتقّاتُ تُبنى
باليدِ واحدًا واحدًا قبلَ الإيداع، فيُنسى واحدٌ منها أو تكتبُ المساراتُ بطاقةً
بينَ البناءِ والإيداع، فيبيتُ مشتقٌّ ويرفضُ التكاملُ المستمرُّ النشر:

    2026-08-08   سجلُّ مساراتِ القرض     بايتٌ فسقطَ النشر
    2026-08-09   سجلُّ مساراتِ القرض     بايتٌ فسقطَ النشر
    2026-08-10   سجلُّ الاسترداد         بايتٌ فسقطَ النشر

**والسببُ الجذريُّ ليس النسيان، بل أنّ الاختيارَ متروكٌ للذاكرة.** فمن بنى ثمانيةً
من عشرةٍ ظنَّ أنّه بنى، ولا حارسَ يقولُ له إنّ اثنَينِ بقيا.

**فالقاعدةُ هنا:** لا يُنتقى بانٍ بعدَ اليوم. تُبنى المشتقّاتُ **كلُّها** بترتيبِ
تبعيّتِها، ثمّ تُفحَصُ البوّاباتُ **كلُّها**، ثمّ يُودَعُ **إن خضِرَت وحدَها**.
وإن سقطَت بوّابةٌ لم يُودَعْ شيءٌ ويُطبَعُ سببُ السقوط، فالإيداعُ على شجرةٍ حمراءَ
يدفعُ فشلًا معروفًا إلى الأصل.

**وتُعادُ الدورةُ مرّةً واحدةً** إن كتبَ مسارٌ في أثناءِ البناء، لأنّ ذلك هو
سيناريو السباقِ الفعليّ: المساراتُ تعملُ ونحنُ نبني.

الاستعمال:
    python scripts/ship.py -m "رسالةُ الإيداع"
    python scripts/ship.py --dry-run        بناءٌ وفحصٌ بلا إيداع
"""
from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import rebuild_derived as R  # noqa: E402

PY = sys.executable


def run(script: str, args: list[str]) -> tuple[int, str]:
    path = ROOT / "scripts" / script
    if not path.exists():
        return 0, "غير موجود"
    p = subprocess.run([PY, str(path), *args], cwd=ROOT, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    lines = [x for x in (p.stdout or "").splitlines() if x.strip()]
    return p.returncode, (lines[-1] if lines else "")[:74]


def git(*args: str) -> tuple[int, str]:
    p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def tree_hash() -> str:
    """بصمةُ ما تحتَ اليدِ الآن، ليُعرَفَ هل كتبَ مسارٌ أثناءَ البناء."""
    git("add", "-A")
    return git("write-tree")[1].strip()


def build_all(only: list[str] | None = None) -> None:
    print("البناء:")
    for script, argv in R.BUILD:
        if only and script not in only:
            continue
        code, line = run(script, argv)
        print(f" {'  ' if code == 0 else '!!'} {script:44}{line}")


def gates_all() -> list[str]:
    print("\nالبوّابات:")
    failed = []
    for script, argv in R.GATES:
        code, line = run(script, argv)
        if code != 0:
            failed.append(script)
        print(f" {'  ' if code == 0 else '!!'} {script:44}{line}")
    return failed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-m", "--message", help="رسالةُ الإيداع")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--push", action="store_true", help="ادفعْ بعدَ الإيداع")
    # **الحاجةُ إلى التقييد:** المساراتُ الصناعيّةُ تعملُ معنا في الشجرةِ نفسِها،
    # فـ`git add -A` يبتلعُ عملَ مسارٍ نصفَ منتهٍ ويُودِعُه برسالةٍ ليست له. فإذا
    # عُلِمَ أنّ مسارًا يعملُ الآنَ سُمِّيَت الملفّاتُ بالاسم، والبناءُ والفحصُ
    # يبقيانِ شاملَين لأنّ باتَ مشتقٍّ واحدٍ يُسقِطُ النشرَ كيفما أُودِع.
    ap.add_argument("--only", nargs="+", metavar="PATH",
                    help="أودِعْ هذه المساراتِ وحدَها (يُستعمَلُ حينَ يعملُ مسارٌ آخرُ معك)")
    ap.add_argument("--build", nargs="+", metavar="SCRIPT",
                    help="اقصرِ البناءَ على هذه البُناةِ (لا يُقصَرُ الفحص)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    for attempt in (1, 2):
        before = tree_hash()
        build_all(args.build)
        after = tree_hash()
        if before == after or attempt == 2 or args.only:
            break
        # لم تتغيّرِ الشجرةُ بالبناءِ وحدَه؟ إذًا كتبَ مسارٌ في أثنائِه
        print("\nتغيّرَت الشجرةُ أثناءَ البناء، فتُعادُ الدورةُ مرّةً واحدة.\n")

    failed = gates_all()
    if failed:
        print(f"\nRESULT: {len(failed)} بوّابةً ساقطة: {', '.join(failed)}")
        print("لم يُودَعْ شيء. الإيداعُ على شجرةٍ حمراءَ يدفعُ فشلًا معروفًا إلى الأصل.")
        return 1
    print("\nRESULT: البوّاباتُ كلُّها خضراء")

    if args.dry_run or not args.message:
        if not args.message and not args.dry_run:
            print("لا رسالةَ إيداع، فلم يُودَعْ شيء.")
        return 0

    if args.only:
        git("reset", "-q")
        git("add", "--", *args.only)
        print("مقصورٌ على: " + " · ".join(args.only))
    else:
        git("add", "-A")
    code, out = git("commit", "-q", "-m", args.message)
    if code != 0 and "nothing to commit" not in out:
        print(out[:400])
        return 1
    print("أُودِعَ: " + git("log", "--oneline", "-1")[1].strip()[:90])
    if args.push:
        code, out = git("push", "-q", "origin", "main")
        print("دُفِعَ إلى الأصل" if code == 0 else out[:300])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
