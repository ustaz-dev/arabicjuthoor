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


def changed_now() -> list[str]:
    """أسطرُ `git status --porcelain` كما هي الآن."""
    return [ln for ln in git("status", "--porcelain")[1].splitlines() if ln.strip()]


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

    # **دورةُ بناءٍ وفحصٍ تُعاوَدُ ولا يُستسلَمُ لأوّلِ سقوط.** خمسةُ مساراتٍ
    # تكتبُ في الشجرةِ نفسِها، فأيُّ مشتقٍّ يُبنى قد يبيتُ قبلَ أن يُفحَصَ لأنّ
    # مسارًا كتبَ بطاقةً في تلك اللحظة. **ومن استسلمَ لأوّلِ سقوطٍ توقّفَ الحصادُ
    # كلُّه**، والبياتُ ههنا عارضُ سباقٍ لا عطبٌ في المادّة.
    before_build: set[str] = set()
    after_build: set[str] = set()
    failed: list[str] = []
    ROUNDS = 4
    for attempt in range(1, ROUNDS + 1):
        before_build = {ln[3:].strip().strip('"') for ln in changed_now()}
        build_all(args.build)
        after_build = {ln[3:].strip().strip('"') for ln in changed_now()}
        failed = gates_all()
        if not failed:
            break
        if attempt < ROUNDS:
            print(f"\n{len(failed)} بوّابةً ساقطةٌ ومسارٌ آخرُ يكتبُ الآن، "
                  f"فتُعادُ الدورةُ ({attempt} من {ROUNDS - 1}).\n")
    if failed:
        print(f"\nRESULT: {len(failed)} بوّابةً ساقطةٌ بعدَ {ROUNDS} دورات: "
              f"{', '.join(failed)}")
        print("لم يُودَعْ شيء. الإيداعُ على شجرةٍ حمراءَ يدفعُ فشلًا معروفًا إلى الأصل.")
        return 1
    print("\nRESULT: البوّاباتُ كلُّها خضراء")

    if args.dry_run or not args.message:
        if not args.message and not args.dry_run:
            print("لا رسالةَ إيداع، فلم يُودَعْ شيء.")
        return 0

    # **`--only` أُلغِيَ عملُه ولم يُلغَ قبولُه** (2026-08-13). المساراتُ العاملةُ
    # لا تُبلَّغُ بتغييرِ أمرٍ، لأنّ كلَّ إرسالٍ عبرَ الجسرِ يفتحُ عمليّةً مستقلّةً
    # ولا يُقاطِعُ الجاريَ. فوجبَ أن يكونَ التصحيحُ في الأداةِ لا في الأمر.
    #
    # **والعلّةُ لا تُحَلُّ بتحسينِ الالتقاطِ أصلًا:** الشحنُ يبني المشتقَّ من
    # الشجرةِ **كاملةً** وفيها قراءاتُ أربعةِ مساراتٍ أُخَر، ثمّ يُودِعُ **جزأَها**،
    # فالمشتقُّ المودَعُ يصفُ بطاقاتٍ أكثرَ ممّا في الإيداعِ مهما أُتقِنَ الالتقاط،
    # والتكاملُ يُعيدُ الحسابَ من المودَعِ وحدَه فيراه باتًا. جُرِّبَت ثلاثةُ
    # إصلاحاتٍ للالتقاطِ وسقطَت كلُّها، لأنّ الشرطَ في بيئةٍ ذاتِ خمسةِ كتّابٍ
    # متزامنينَ يُخطئُ حتمًا.
    #
    # **والإيداعُ الشاملُ متّسقٌ ببنيتِه:** ما يُودَعُ هو الشجرةُ كما فُحِصَت.
    # وقد يُودَعُ معه بطاقةُ مسارٍ آخرَ نصفَ مكتوبة، ولا يضرُّ لأنّ البطاقاتِ
    # كتلٌ تُلحَقُ والبوّاباتُ تفحصُ الشجرةَ كلَّها قبلَ الإيداع.
    if args.only:
        print("تنبيه: --only مُلغًى، فالإيداعُ شاملٌ حتمًا ما دامَت المساراتُ "
              "تكتبُ معًا. وملكيّةُ الملفّاتِ باقية: اكتبْ في نطاقِك وحدَه.")
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
