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
import ctypes
import os
import pathlib
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import rebuild_derived as R  # noqa: E402

PY = sys.executable

# **القفلُ ينهي حلقةً كادت تُوقِفُ المشروعَ يومًا كاملًا (2026-08-14).** خمسةُ
# مساراتٍ تُودِعُ بعدَ كلِّ دفعة، ويُودِعُ معها المنسِّق، فاجتمعَ **تسعةُ إيداعاتٍ
# تعملُ معًا**، كلُّ واحدٍ يبني الشجرةَ كاملةً في أربعِ دوراتٍ ويتزاحمُ على
# المعالج. وكلَّما ازدحمَت طالت الدورةُ، وكلَّما طالت كتبَ مسارٌ في أثنائها
# فلزِمَت دورةٌ أخرى. **حلقةٌ تُطعِمُ نفسَها: سبعُ ساعاتٍ بلا إيداعٍ واحد.**
#
# **والمخرَجُ أنّ الإيداعَ شاملٌ أصلًا.** من يحملُ القفلَ يُودِعُ الشجرةَ كلَّها
# بـ`git add -A`، فعملُ المنتظِرِ داخلٌ في إيداعِه حتمًا. فلا معنى لأن ينتظرَ
# المنتظِرُ دورةَ بناءٍ ثانيةً لنفسِ الشجرة: يُسلِّمُ رسالتَه وينصرف.
LOCK = ROOT / ".git" / "ship.lock"
LOCK_STALE_MINUTES = 45


def process_alive(pid: int) -> bool:
    """اختبار حياة العملية، بباب ويندوز المباشر حيث لا يوثق بـos.kill(pid, 0)."""
    if os.name == "nt":
        process_query_limited_information = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(
            process_query_limited_information, False, pid
        )
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def lock_holder() -> tuple[int, float] | None:
    """صاحبُ القفلِ إن كان حيًّا، وإلّا None ويُكسَرُ القفلُ الميّت."""
    try:
        pid_s, stamp_s = LOCK.read_text(encoding="utf-8").split()
        pid, stamp = int(pid_s), float(stamp_s)
    except (OSError, ValueError):
        return None
    alive = process_alive(pid)
    age = (time.time() - stamp) / 60
    # **الميّتُ يُكسَرُ قفلُه فورًا، والعمرُ لا يُنتظَرُ به (2026-08-15).** كانت
    # القاعدةُ تشترطُ الموتَ **و**مضيَّ 45 دقيقة، فبقيَ قفلُ عمليّةٍ ماتَت بعدَ
    # إحدى عشرةَ دقيقةً معطِّلًا كلَّ إيداعٍ أربعًا وثلاثينَ دقيقةً بلا سبب.
    # فالموتُ وحدَه كافٍ، وإنّما يُعتَدُّ بالعمرِ حينَ تتعذَّرُ معرفةُ الحياة.
    if not alive:
        print(f"صاحبُ القفلِ ميّتٌ (pid {pid}، عمرُ القفلِ {int(age)} دقيقة)، يُكسَر.")
        LOCK.unlink(missing_ok=True)
        return None
    # وقفلُ عمليّةٍ حيّةٍ لا يُكسَرُ بالعمر: بعضُ البناةِ يتجاوزُ 45 دقيقةً بحقّ.
    return pid, stamp


def take_lock() -> bool:
    """يُؤخَذُ القفلُ ذرّيًّا، أو يُردُّ False إن كان بيدِ غيرِنا."""
    holder = lock_holder()
    if holder:
        pid, stamp = holder
        print(f"إيداعٌ آخرُ يعملُ منذُ {int((time.time() - stamp) / 60)} دقيقةً "
              f"(pid {pid}).\nوالإيداعُ شاملٌ فعملُك داخلٌ في إيداعِه، "
              "فلا يُبنى مرّتَينِ لنفسِ الشجرة.")
        return False
    try:
        with open(LOCK, "x", encoding="utf-8") as fh:
            fh.write(f"{os.getpid()} {time.time()}")
        return True
    except FileExistsError:
        print("سبقَنا إيداعٌ آخرُ إلى القفلِ في هذه اللحظة.")
        return False


def release_own_lock() -> None:
    """لا تحذف قفلًا استبدلته عملية أحدث أثناء سباقٍ تاريخي."""
    try:
        pid_s, _ = LOCK.read_text(encoding="utf-8").split()
    except (OSError, ValueError):
        return
    if int(pid_s) == os.getpid():
        LOCK.unlink(missing_ok=True)


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


def build_all(only: list[str] | None = None,
              skip: set[str] | None = None) -> None:
    """يبني المشتقّات. و`skip` تُسقِطُ من يُعادُ بناؤُه قبلَ الإيداعِ مباشرةً.

    **العلّةُ زمنٌ لا صحّة (2026-08-15):** أحدَ عشرَ بانيًا كلٌّ منهم يقرأُ 380
    ميجا من ملفّاتِ القراءة، فطورُ البناءِ وحدَه يزيدُ على أربعينَ دقيقة. وتسعةٌ
    من هؤلاء **يُعادُ بناؤُهم في `refresh_before_commit` قبلَ `git add -A`**،
    فبناؤُهم في أوّلِ الدورةِ عملٌ يُرمى. وإسقاطُه يُنصِّفُ زمنَ الإيداع، ولا
    يُنقِصُ صحّةً لأنّ المودَعَ في الحالَينِ هو ناتجُ التجديدِ الأخير.
    """
    print("البناء:")
    for script, argv in R.BUILD:
        if only and script not in only:
            continue
        if skip and script in skip:
            continue
        code, line = run(script, argv)
        print(f" {'  ' if code == 0 else '!!'} {script:44}{line}")


def freshness_builders() -> list[tuple[str, list[str]]]:
    """البُناةُ الذين تفحصُ بوّابةٌ طزاجةَ مشتقِّهم، وهم وحدَهم يُعادونَ قبلَ الإيداع."""
    checked = {s for s, a in R.GATES if "--check" in a}
    return [(s, a) for s, a in R.BUILD if s in checked]


def refresh_before_commit() -> None:
    """يُعادُ بناءُ المشتقّاتِ المفحوصةِ في آخرِ لحظةٍ قبلَ `git add -A`.

    **العطبُ الذي يُنهيه، وقد سقطَ به النشرُ أربعَ مرّاتٍ في ساعتَين:** بوّابةُ
    التكاملِ تُعيدُ حسابَ المشتقِّ من شجرةِ الإيداعِ وتُقابِلُه بالمودَع، وهي
    **حتميّةٌ لتلك الشجرة**. فإن كتبَ مسارٌ بطاقةً بينَ فحصِ البوّاباتِ عندَنا
    وبينَ `git add -A` بات المشتقُّ في الإيداعِ نفسِه، **وسقطَ النشرُ سقوطًا
    لا تُصلِحُه إعادةُ التشغيلِ أبدًا** لأنّها تفحصُ الشجرةَ عينَها فتصلُ إلى
    النتيجةِ عينِها. وكانت المراقبةُ تُعيدُ التشغيلَ ظنًّا أنّه عارضٌ من الخدمة.

    والنافذةُ لا تُغلَقُ إغلاقًا تامًّا ما دامَ خمسةُ كتّابٍ يعملون، لكنّها
    تنكمشُ من دقائقَ إلى ثوانٍ. وكلفةُ ذلك 20 ثانيةً لسجلِّ الاسترداد.
    """
    builders = freshness_builders()
    print(f"\nتجديدُ {len(builders)} مشتقًّا مفحوصًا قبلَ الإيداعِ مباشرةً:")
    for script, argv in builders:
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

    if not take_lock():
        return 0

    try:
        return _run(args)
    finally:
        release_own_lock()


def _run(args) -> int:
    # **دورةُ بناءٍ وفحصٍ تُعاوَدُ ولا يُستسلَمُ لأوّلِ سقوط.** خمسةُ مساراتٍ
    # تكتبُ في الشجرةِ نفسِها، فأيُّ مشتقٍّ يُبنى قد يبيتُ قبلَ أن يُفحَصَ لأنّ
    # مسارًا كتبَ بطاقةً في تلك اللحظة. **ومن استسلمَ لأوّلِ سقوطٍ توقّفَ الحصادُ
    # كلُّه**، والبياتُ ههنا عارضُ سباقٍ لا عطبٌ في المادّة.
    # **العطبُ الذي أُصلِحَ هنا (2026-08-15): الدورةُ لا تلحقُ الكتّاب.**
    # صارَت ملفّاتُ القراءةِ 380 ميجا، فدورةُ بناءٍ وفحصٍ واحدةٌ تزيدُ على نصفِ
    # ساعة، وخمسةُ مساراتٍ تكتبُ في أثنائها. فكلَّما فُحِصَت بوّابةُ طزاجةٍ
    # وجدَت مشتقًّا باتَ في تلك اللحظة، فتُعادُ الدورةُ أربعًا ثمّ **لا يُودَعُ
    # شيء**. تراكمَ بذلك 300 ملفٍّ وساعتانِ بلا إيداعٍ والعملُ كلُّه غيرُ محفوظ.
    #
    # **والتفريقُ هو الحلّ، لا زيادةُ الدورات.** البوّاباتُ صنفان:
    #
    #   بوّابةُ طزاجة   تُعيدُ حسابَ مشتقٍّ من الشجرةِ وتُقابِلُه بالمودَع.
    #                  سقوطُها يعني «بات»، **و`refresh_before_commit` يُصلِحُه
    #                  بعينِه قبلَ `git add -A`**، فلا معنى لإعادةِ الدورةِ له.
    #   بوّابةٌ جوهريّة  تفحصُ المادّةَ نفسَها (نقاءُ الشحنة، قاموسُ الإغلاق).
    #                  سقوطُها عطبٌ حقيقيٌّ **لا يُودَعُ معه شيءٌ أبدًا**.
    #
    # فدورةٌ واحدةٌ تكفي: إن سقطَت بوّاباتُ طزاجةٍ وحدَها مضى الإيداعُ بعدَ
    # التجديد، وإن سقطَت جوهريّةٌ واحدةٌ وقفَ كلُّ شيء.
    fresh_names = {s for s, _ in freshness_builders()}
    before_build: set[str] = set()
    after_build: set[str] = set()
    ROUNDS = 2
    substantive: list[str] = []
    for attempt in range(1, ROUNDS + 1):
        before_build = {ln[3:].strip().strip('"') for ln in changed_now()}
        build_all(args.build, skip=fresh_names)
        after_build = {ln[3:].strip().strip('"') for ln in changed_now()}
        failed = gates_all()
        stale = [s for s in failed if s in fresh_names]
        substantive = [s for s in failed if s not in fresh_names]
        if not failed:
            break
        if not substantive:
            print(f"\n{len(stale)} بوّابةَ طزاجةٍ باتَت لأنّ مسارًا كتبَ في أثناءِ "
                  "الدورة، ويُصلِحُها التجديدُ قبلَ الإيداعِ مباشرةً فيُمضى.")
            break
        if attempt < ROUNDS:
            print(f"\n{len(substantive)} بوّابةً جوهريّةً ساقطةٌ، فتُعادُ الدورةُ مرّةً.\n")
    if substantive:
        print(f"\nRESULT: {len(substantive)} بوّابةً جوهريّةً ساقطة: "
              f"{', '.join(substantive)}")
        print("لم يُودَعْ شيء. الإيداعُ على شجرةٍ حمراءَ يدفعُ فشلًا معروفًا إلى الأصل.")
        return 1
    print("\nRESULT: لا بوّابةَ جوهريّةً ساقطة")

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
    refresh_before_commit()
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
