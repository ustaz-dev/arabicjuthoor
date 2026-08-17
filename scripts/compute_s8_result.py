# -*- coding: utf-8 -*-
"""كشفُ مفتاحِ جولةِ §8 وحسابُ المعدّلَينِ بعدَ إيداعِ القراءاتِ كاملةً (2026-08-17)

التسلسلُ المسجَّلُ مسبقًا (05-audits/2026-08-17-s8-preregistration.md):
تُودَعُ القراءاتُ الـ150 أوّلًا، ثمّ يُكشَفُ المفتاحُ وتُطابَقُ بصمتُه
SHA-256 المودَعةُ قبلَ القراءة، ثمّ يُحسَبُ المعدّلانِ ويُختبَرُ المعيارُ
المسجَّل: تفوُّقُ الحقيقيِّ على الضابطِ بفيشر أحاديِّ الذيلِ عندَ p < 0.05.
ولا يُدَّعى رقمٌ مطلقٌ من الجولة: الإشارةُ هي الفرقُ وحدَه بنصِّ الدستور §8.

الاستعمال:
    python scripts/compute_s8_result.py --key "<مسار المفتاح خارج المستودع>"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
READING = ROOT / "04-cross-linguistic" / "readings" / "s8-greek-round.md"
PREREG = ROOT / "05-audits" / "2026-08-17-s8-preregistration.md"
OUT = ROOT / "05-audits" / "2026-08-17-s8-results.md"

LADDER = ("ROOT-TRACE", "NUCLEUS-TRACE", "ROOT-ECHO", "NUCLEUS-ECHO",
          "FLOOR-TRACE")


def fisher_one_sided(a: int, b: int, c: int, d: int) -> float:
    """احتمالُ فيشر الدقيقُ أحاديُّ الذيل: أن يبلغَ الحقيقيُّ ما بلغَ أو أكثرَ
    لو كانت الأذرعُ سواء. الجدول: a موجبُ الحقيقيِّ، b سالبُه، c موجبُ
    الضابطِ، d سالبُه."""
    def comb(n, k):
        return math.comb(n, k)
    n = a + b + c + d
    row1, col1 = a + b, a + c
    denom = comb(n, col1)
    p = 0.0
    for k in range(a, min(row1, col1) + 1):
        p += comb(row1, k) * comb(n - row1, col1 - k) / denom
    return p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--key", required=True)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    # 1. مطابقةُ البصمةِ المودَعةِ قبلَ القراءة
    key_text = pathlib.Path(args.key).read_text(encoding="utf-8")
    digest = hashlib.sha256(key_text.encode("utf-8")).hexdigest()
    prereg = PREREG.read_text(encoding="utf-8")
    m = re.search(r"SHA-256\(المفتاح\) = `([0-9a-f]{64})`", prereg)
    if not m:
        print("!! لم أجدِ البصمةَ في التسجيلِ المسبق")
        return 1
    if digest != m.group(1):
        print(f"!! البصمةُ لا تطابق: {digest} مقابلَ {m.group(1)}")
        return 1
    key = json.loads(key_text)

    # 2. أحكامُ البطاقاتِ الـ150 من ملفِّ القراءة
    text = READING.read_text(encoding="utf-8", errors="replace")
    cards = {}
    for mm in re.finditer(
            r"### بطاقة (S8-GRC-\d{3}):(?:(?!### ).)*?"
            r"^- الحكم[^:：\n]*[:：]\s*([^\n]+)$",
            text, re.S | re.M):
        sid, verdict = mm.group(1), mm.group(2)
        cards[sid] = verdict.strip()
    if len(cards) != 150:
        print(f"!! المقروءُ {len(cards)} بطاقةً لا 150")
        return 1

    # 3. المعدّلانِ والاختبار
    arms = {"REAL": {"pos": 0, "n": 0, "hits": []},
            "CONTROL": {"pos": 0, "n": 0, "hits": []}}
    for sid, arm in key.items():
        v = cards.get(sid, "")
        arms[arm]["n"] += 1
        if any(d in v for d in LADDER):
            arms[arm]["pos"] += 1
            arms[arm]["hits"].append(f"{sid}: {v[:80]}")
    R, C = arms["REAL"], arms["CONTROL"]
    p = fisher_one_sided(R["pos"], R["n"] - R["pos"], C["pos"], C["n"] - C["pos"])
    rate_r = R["pos"] / R["n"] if R["n"] else 0.0
    rate_c = C["pos"] / C["n"] if C["n"] else 0.0
    met = (R["pos"] > C["pos"]) and (p < 0.05)

    lines = [
        "# نتيجةُ جولةِ §8 الأولى: اليونانيّةُ القديمةُ المعمّاة (2026-08-17)",
        "",
        "**طبقة: تحقُّقٌ مقيس.** التسلسلُ المسجَّلُ نُفِّذَ حرفيًّا: التسجيلُ",
        "المسبقُ فالقراءةُ المعمّاةُ كاملةً فإيداعُها فكشفُ المفتاح.",
        "",
        f"- مطابقةُ البصمة: `{digest[:16]}…` تطابقُ المودَعةَ قبلَ القراءة: نعم.",
        f"- العيّنةُ الحقيقيّة: {R['pos']} موجبًا سلَّميًّا من {R['n']}"
        f" (المعدّل {100*rate_r:.1f}%).",
        f"- العيّنةُ الضابطة: {C['pos']} موجبًا سلَّميًّا من {C['n']}"
        f" (المعدّل {100*rate_c:.1f}%).",
        f"- فيشر أحاديُّ الذيل: p = {p:.3f}.",
        f"- **المعيارُ المسجَّلُ (تفوُّقُ الحقيقيِّ عندَ p < 0.05): "
        + ("تحقَّق" if met else "لم يتحقَّقْ في هذه الجولة") + ".**",
        "",
        "## الموجباتُ بأسمائِها",
        "",
    ]
    for arm_name, arm in (("الحقيقيّة", R), ("الضابطة", C)):
        for h in arm["hits"]:
            lines.append(f"- ({arm_name}) {h}")
    if not (R["hits"] or C["hits"]):
        lines.append("- لا موجبَ في أيٍّ من الفريقَين.")
    lines += [
        "",
        "## المفتاحُ مكشوفًا",
        "",
        "```json",
        key_text.strip(),
        "```",
        "",
        "## قيودُ القراءةِ الأمينة",
        "",
        "1. لا يُدَّعى من الجولةِ رقمٌ مطلقٌ البتّة؛ الإشارةُ المسجَّلةُ هي",
        "   الفرقُ بينَ الفريقَينِ وحدَه (الدستور §8 نصًّا).",
        "2. قارئُ الجولةِ كان أشدَّ صرامةً من مساراتِ الاستكشافِ بدرجاتٍ",
        "   (موجبٌ واحدٌ في 150)، فالجولةُ تقيسُ بروتوكولَه هو على عيّنةٍ",
        "   عشوائيّةٍ غيرِ مرشَّحة، ولا تقيسُ حوضَ المرشَّحينَ المُصفّى الذي",
        "   تعملُ عليه المساراتُ ولا تنقضُه.",
        "3. قرارُ التعميمِ أو إعادةِ التصميمِ (حجمٌ أكبرُ، أو عيّنةٌ حقيقيّةٌ",
        "   من حوضِ الصوتِ+المعنى بضوابطَ مبدَّلةِ المعاني) للمؤلّفِ وحدَه.",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"الحقيقيّة: {R['pos']}/{R['n']}  الضابطة: {C['pos']}/{C['n']}  "
          f"p={p:.3f}  المعيار: {'تحقق' if met else 'لم يتحقق'}")
    print(f"كُتبت الورقة: {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
