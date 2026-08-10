# -*- coding: utf-8 -*-
"""إعادةُ فتحِ ما أُغلِقَ بقانونٍ لا وجودَ له (2026-08-09، بأمرِ المؤلّف)

**الأمر:** «أعِدْ فتحَ كلِّ واحدةٍ منها، ولنُعامِلْها ثانيةً بالطريقةِ التي تستحقُّها».

جردُ `check_closure_vocabulary.py` أظهرَ 105 بطاقاتٍ في ثلاثةَ عشرَ لسانًا أُغلِقَت
بوسومٍ **ليست في الميثاقِ ولا في الدستور**، بل وُلِدَت في أثناءِ جولاتِ عمل:
`ORIGINAL-CONSONANT-DROP` و`MEANING-FAIL` و`NOT-IDENTICAL` و`SEMANTIC-GAP`
و`ROW-TAG-CONDITION-UNMET` وأخواتُها. وفيها من أوضحِ ما في الساميّة: الأكّاديّةُ
`pûm` «الفمُ والقول» بإزاءِ فوه وفم، و`šaptum` «الشفة» بإزاءِ شفه، و`nišū`
«الناس» بإزاءِ إنس. أُغلِقَت لأنّ صامتًا سقط، والعربيّةُ نفسُها تقولُ فمًا وأصلُها
فوه.

**ما يفعلُه هذا السكربتُ بالضبط، ولا يزيد:**
  1. يقلبُ حقلَ الحكمِ إلى `OPEN-CANDIDATE`، وهو وسمٌ مُقَرٌّ في الميثاق.
  2. **يحفظُ الحكمَ القديمَ حرفًا بحرفٍ** في سطرٍ مسمًّى، فالدستورُ يقضي ألّا
     يُمحى من السجلِّ شيء، وأنّ المستبدَلَ يُحفَظُ دائمًا.
  3. يكتبُ سببَ الرفعِ وتاريخَه ومرجِعَه، فيُقرَأُ السببُ بعدَ سنة.

**ولا يُصدِرُ حكمًا موجَبًا ولا يُرجِّحُ مرشَّحًا.** الفتحُ ردٌّ للبطاقةِ إلى الطابور
لتُقرأَ بالطريقةِ العاديّة، لا حكمٌ لها.

الاستعمال:
    python scripts/reopen_invented_closures.py --dry-run    عرضٌ بلا كتابة
    python scripts/reopen_invented_closures.py             تنفيذ
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import count_links as C  # noqa: E402
import check_closure_vocabulary as V  # noqa: E402

READINGS = ROOT / "04-cross-linguistic" / "readings"
MANIFEST = ROOT / "data" / "reopened-invented-closures.json"
RECORD = ROOT / "05-audits" / "2026-08-09-reopened-cards-closed-on-invented-labels.md"

STAMP = "الحكمُ السابقُ المرفوع (2026-08-09)"
REASON = ("أُغلِقَت هذه البطاقةُ بوسمٍ لا وجودَ له في ميثاقِ الاستكشافِ ولا في "
          "الدستور، فرُفِعَ الإغلاقُ بأمرِ المؤلّفِ وأُعيدَت إلى الطابورِ لتُقرأَ "
          "بالطريقةِ العاديّة. المرجع: "
          "05-audits/2026-08-08-cards-closed-on-invented-labels.md")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    reopened, per_lang, per_label = [], collections.Counter(), collections.Counter()
    already = 0

    for path in sorted(READINGS.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        out_parts, changed = [], False
        # يُقسَمُ النصُّ الخامُّ نفسُه، فما يُكتَبُ هو ما قُرِئَ بلا تطبيعٍ يُتلِفُ الشكل
        pieces = C.CARD_SPLIT.split(raw)
        out_parts.append(pieces[0])
        for card in pieces[1:]:
            head = card.split("\n", 1)[0]
            if C.is_template(head):
                out_parts.append(card)
                continue
            if STAMP in card:
                already += 1
                out_parts.append(card)
                continue

            new_card, card_changed = card, False
            for m in list(C.VERDICT_FIELDS.finditer(C.bare(card))):
                pass  # المطابقةُ على المجرَّدِ لتحديدِ الوجود، والاستبدالُ على الخامّ

            for line in card.split("\n"):
                mm = C.VERDICT_FIELDS.match(C.bare(line))
                if not mm:
                    continue
                value = mm.group(1)
                toks = [t for t in V.TOKEN.findall(value)
                        if not V.NOT_A_LABEL.match(t)]
                if set(toks) & V.POSITIVE:
                    continue
                invented = {x for x in toks
                            if x not in V.LEGAL
                            and (x in V.LEGACY_INVENTED or V.BLOCKING_SHAPE.search(x))}
                if not invented:
                    continue

                field = line.split(":", 1)[0] if ":" in line else "- الحكم (استكشاف)"
                replacement = (
                    f"{field}: OPEN-CANDIDATE (استكشاف)\n"
                    f"- {STAMP}: {value.strip()}\n"
                    f"- سببُ الرفع: {REASON}"
                )
                new_card = new_card.replace(line, replacement, 1)
                card_changed = True
                per_label.update(sorted(invented))
                reopened.append({
                    "language": path.stem,
                    "card": head.strip()[:120],
                    "previous_verdict": value.strip()[:180],
                    "labels": sorted(invented),
                })
                # لا يُكتفى بأوّلِ حقل: البطاقةُ قد تحملُ حكمَ طبقتَينِ (جذرًا
                # ونواةً) وكلاهما مُغلَقٌ بوسمٍ مخترَع، فيُرفَعانِ معًا وإلّا
                # بقيَت نصفُ البطاقةِ محبوسةً بقانونٍ لا وجودَ له

            if card_changed:
                changed = True
                per_lang[path.stem] += 1
            out_parts.append(new_card)

        if changed and not args.dry_run:
            text = C.CARD_SPLIT.pattern  # noqa: F841  (التقسيمُ يُفقِدُ الفاصل)
            # يُعادُ التركيبُ بالفاصلِ نفسِه الذي قُسِمَ به: `### ` أو `#### `
            rebuilt = out_parts[0]
            heads = C.CARD_SPLIT.findall(raw)
            for sep, body in zip(heads, out_parts[1:]):
                rebuilt += sep + body
            path.write_text(unicodedata.normalize("NFC", rebuilt),
                            encoding="utf-8", newline="")

    print(f"{'اللسان':26}{'فُتِحَت':>8}")
    for lang, n in per_lang.most_common():
        print(f"  {lang:26}{n:>8}")
    print(f"\nالمجموع: {len(reopened)} بطاقة" + ("  (عرضٌ بلا كتابة)" if args.dry_run else ""))
    if already:
        print(f"مفتوحةٌ سابقًا فلم تُمَسّ: {already}")
    print("\nالوسومُ التي رُفِعَت:")
    for lab, n in per_label.most_common():
        print(f"   {lab:36}{n:5}")

    if args.dry_run:
        return 0

    MANIFEST.write_text(json.dumps({
        "generated_by": "scripts/reopen_invented_closures.py",
        "date": "2026-08-09",
        "order": "أعِدْ فتحَ كلِّ واحدةٍ منها ولنُعامِلْها بالطريقةِ التي تستحقُّها",
        "reopened": len(reopened),
        "by_language": dict(per_lang),
        "by_label": dict(per_label),
        "cards": reopened,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = [
        "# البطاقاتُ المفتوحةُ بعدَ رفعِ الإغلاقاتِ المخترَعة، 2026-08-09",
        "",
        "**الطبقة:** استكشاف. **فتحٌ لا حكم.**",
        "",
        "بأمرِ المؤلّف: «أعِدْ فتحَ كلِّ واحدةٍ منها، ولنُعامِلْها ثانيةً بالطريقةِ",
        "التي تستحقُّها». فرُفِعَ الإغلاقُ عن كلِّ بطاقةٍ أُغلِقَت بوسمٍ ليس في الميثاقِ",
        "ولا في الدستور، وصارَ حكمُها `OPEN-CANDIDATE`، **والحكمُ القديمُ محفوظٌ في",
        "البطاقةِ نفسِها حرفًا بحرفٍ** كما يقضي الدستورُ بأنّ المستبدَلَ لا يُمحى.",
        "",
        f"**العدد: {len(reopened)} بطاقةً في {len(per_lang)} لسانًا.**",
        "",
        "| اللسان | البطاقة | الحكمُ المرفوع | الوسمُ المخترَع |",
        "|---|---|---|---|",
    ]
    for c in reopened:
        lines.append(f"| {c['language']} | {c['card']} | {c['previous_verdict']} | "
                     f"{' · '.join(c['labels'])} |")
    lines += [
        "",
        "---",
        "",
        "*English abstract:* On the author's order every card that had been closed under",
        "a label absent from the charter and the constitution was reopened to",
        "OPEN-CANDIDATE, with its former verdict preserved verbatim inside the card, as",
        "the constitution requires that a superseded reading is never erased. This is a",
        "reopening, not a verdict: each card returns to the queue to be read again by the",
        "ordinary method.",
    ]
    RECORD.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"\nكُتب: {MANIFEST.relative_to(ROOT).as_posix()}")
    print(f"كُتب: {RECORD.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
