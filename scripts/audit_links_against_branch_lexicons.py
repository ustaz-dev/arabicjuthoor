# -*- coding: utf-8 -*-
"""كم صلةً صادرةً لم تُعرَضْ على قاموسِ فرعِها بعدُ؟ (2026-08-14)

**السؤالُ الذي يجيبُ عنه، وهو للمؤلّفِ وحدَه.** الميثاقُ يشترطُ في الرِّجلِ
الثالثةِ معنى **قاموسِ الفرع**، وقد تبيّنَ أنّ المساراتِ كانت تقرؤُه من عمودِ
باحثٍ سابقٍ مكانَه. ولمّا عُرِضَت دفعتانِ مصريّتانِ على قاموسِهما: تحوّلَت 9
بطاقاتٍ إلى موجب، **ونُسِخَت 12 بطاقةً موجبةً** لأنّ القاموسَ لا يُسنِدُ معناها.
وفي مسودّةِ دفعةٍ أخرى سقطَ **10 من 11 موجبًا** بالعرضِ نفسِه.

فالسؤالُ: أتُعادُ الصلاتُ كلُّها على قواميسِ فروعِها؟ وثمنُه أنّ العددَ المنشورَ
سينزل. **وهذه الأداةُ تقيسُ حجمَ المراجعةِ ولا تُغيِّرُ حكمًا واحدًا.**

**والقياسُ قاطعٌ لا تخميني.** المساراتُ تكتبُ منذُ اليومِ حقولًا صريحةً في كلِّ
بطاقةٍ تعرضُها على القاموس: `قاموس الفرع` و`قائمة مداخل الصورة كلها`
و`المدخلة المختارة بسياق الصف` و`معنى قاموس الفرع المعتمد بلا رتوش`
و`الخلاف المدون`. فوجودُ الحقلِ من عدمِه يفصلُ فصلًا، ولا حاجةَ إلى مقايسةِ
معانٍ بكلماتٍ مشتركةٍ وهي مقايسةٌ خشنةٌ تُخطئ.

**والحكمُ المنسوخُ لا يُعَدُّ صلة**: البطاقةُ التي فيها «غير صادر [كان
NUCLEUS-TRACE]» بطاقةٌ مسحوبةٌ يُحفَظُ نصُّها، وعدُّها موجبةً غلطٌ أوقعَتْني
فيه قراءةٌ أولى للملفّات.

الاستعمال:
    python scripts/audit_links_against_branch_lexicons.py
"""
from __future__ import annotations

import collections
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
READINGS = ROOT / "04-cross-linguistic" / "readings"

POSITIVE = ("ROOT-TRACE", "NUCLEUS-TRACE", "ROOT-ECHO", "NUCLEUS-ECHO", "FLOOR-TRACE")
VERDICT = re.compile(r"^- الحكم[^:：\n]*[:：]\s*(.{0,70})", re.M)
LEXICON_FIELDS = ("معنى قاموس الفرع المعتمد", "قائمة مداخل الصورة كلها",
                  "المدخلة المختارة بسياق الصف")


def verdict_of(card: str) -> str:
    """الحكمُ الحيُّ للبطاقة، أو سلسلةٌ فارغةٌ إن لم يكنْ موجبًا حيًّا."""
    m = VERDICT.search(card)
    if not m:
        return ""
    line = m.group(1)
    if "غير صادر" in line or "لم يصدر" in line:
        return ""                       # مسحوبٌ أو غيرُ صادر، ولو ذُكِرَ وسمُه
    return next((v for v in POSITIVE if v in line), "")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows = []
    tot = collections.Counter()
    for path in sorted(READINGS.glob("*.md")):
        text = path.read_text(encoding="utf-8", errors="replace")
        seen = checked = 0
        for card in text.split("\n### ")[1:]:
            if not verdict_of(card):
                continue
            seen += 1
            if any(f in card for f in LEXICON_FIELDS):
                checked += 1
        if seen:
            rows.append((path.stem, seen, checked, seen - checked))
            tot["صلات"] += seen
            tot["معروضة"] += checked
            tot["تنتظر"] += seen - checked

    print(f"{'اللسان':18}{'صلاتٌ حيّة':>11}{'عُرِضَت':>9}{'تنتظرُ العرض':>13}")
    for lang, seen, ok, wait in sorted(rows, key=lambda r: -r[3]):
        print(f"{lang:18}{seen:>11}{ok:>9}{wait:>13}")
    print(f"\n{'الجملة':18}{tot['صلات']:>11}{tot['معروضة']:>9}{tot['تنتظر']:>13}")

    if tot["صلات"]:
        pct = 100 * tot["تنتظر"] / tot["صلات"]
        print(f"\nينتظرُ العرضَ على قاموسِ فرعِه {pct:.0f}% من الصلاتِ الصادرة.")
        print("وقياسُ المصريّةِ على عيّنتِها: من 21 موجبًا قديمًا سقطَ 12،")
        print("ومن 11 موجبًا في مسودّةٍ سقطَ 10. فإن قاربَت النسبةُ ذلك في غيرِها")
        print("**نزلَ العددُ المنشورُ نزولًا ظاهرًا**، والقرارُ للمؤلّفِ وحدَه.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
