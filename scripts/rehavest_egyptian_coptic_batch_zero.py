# -*- coding: utf-8 -*-
"""إعادةُ حصادِ دفعةِ المقارنةِ المصريةِ والقبطيةِ الصفر.

لا تعيد هذه الأداة حساب الصوت أو توليد المدار. الرجل الثانية وحدها تُحل عبر
``frozen_event.resolve``، والمدارات الموجبة أدناه قائمة كتبها القارئ يدويّا بعد
مراجعة معنى الفرع كما ورد ومسار الصوت المحفوظ في الدفعة الأصلية.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import frozen_event as FE  # noqa: E402

SOURCE = ROOT / "data" / "comparative-egyptian-coptic-batch-001.json"
OUT = ROOT / "data" / "comparative-egyptian-coptic-reharvest-batch-000.json"
AUDIT = ROOT / "05-audits" / "2026-08-14-egyptian-coptic-reharvest-batch-000.md"
READINGS = {
    "egyptian": ROOT / "04-cross-linguistic" / "readings" / "egyptian.md",
    "coptic": ROOT / "04-cross-linguistic" / "readings" / "coptic.md",
}
MARKER = "FROZEN-EVENT-REHARVEST-BATCH-000"


# هذه المدارات كُتبت واحدا واحدا بالكلمات. لا اشتقاق لها من نص الحدث ولا من
# تشابه الألفاظ، ولا تُستعمل دعوى خشيم في arabic_gloss دليلا مستقلا.
ORBITS: dict[int, str] = {
    60: "مدار النتيجة: التجرد والخلوص يزيلان الساتر، ونتيجة ذلك ظهور الشيء؛ واللقاء مقصور على «الظاهر» من معنى الفرع.",
    93: "مدار الجزء من الكل: الإصبع امتداد لطيف خارج من أصله في الكف؛ واللقاء مقصور على «أصابع» من معنى الفرع.",
    95: "مدار الجزء من الكل: الإصبع امتداد لطيف خارج من أصله في الكف؛ واللقاء مقصور على «أصابع» من معنى الفرع.",
    141: "مدار الصفة: الصمغ والعلك مادة لاصقة تتجمع وتتضام في كتلة؛ وهذه صفة المادة المذكورة في معنى الفرع.",
    193: "مدار الفعل: الرفع المذكور في معنى الفرع هو إحداث الارتفاع نفسه، و«قائد رفيع» حامل صفة ذلك الارتفاع.",
    197: "مدار الفعل: الرفع المذكور في معنى الفرع هو إحداث الارتفاع نفسه، و«قائد رفيع» حامل صفة ذلك الارتفاع.",
    331: "مدار الفعل: «مات» في معنى الفرع هو وقوع التمدد مع الهمود والسكون وذهاب الحدة؛ ولا يرث هذا الحكم بقية المعاني المجموعة في الصف.",
    335: "مدار الفعل: «مات» في معنى الفرع هو وقوع التمدد مع الهمود والسكون وذهاب الحدة؛ ولا يرث هذا الحكم بقية المعاني المجموعة في الصف.",
    384: "مدار الفعل: التنفس في وجه الزفير اندفاع هواء مبتعدا عن مضمه في الصدر؛ واللقاء مقصور على «تنفس» من معنى الفرع.",
    412: "مدار النتيجة: الأخ صنو لأنه فرع ثان خارج من أصل واحد؛ فالتفرع من الأصل ينتج الصنو المذكور في معنى الفرع.",
    414: "مدار الفعل: النفس الخارج نفاذ وإبعاد للهواء بانتشار؛ واللقاء مقصور على فعل النفس الذي يسميه معنى الفرع.",
    461: "مدار الصفة: حدث الشين يصف تفشيا دقيقا متفرقا، وتكراره على جانبي الانفتاح الممدود يصف هيئة الشاش المنبسط من خيوط دقيقة؛ وهذا تركيب يدوي لأحداث النطق الثلاثة.",
    464: "مدار الصفة: حدث الشين يصف تفشيا دقيقا متفرقا، وتكراره على جانبي الانفتاح الممدود يصف هيئة الشاش المنبسط من خيوط دقيقة؛ وهذا تركيب يدوي لأحداث النطق الثلاثة.",
    1124: "مدار النتيجة: البنية هي ما ينتج من الامتداد والبناء؛ واللقاء مقصور على «بنية» من معنى الفرع.",
    1126: "مدار النتيجة: الامتداد والبناء ينتجان بنية قائمة، والانفتاح الممدود للحرف الثالث يخرجها ظاهرة؛ وهذا تأليف يدوي لحدث النواة وحدث الحرف الثالث.",
    1532: "مدار المحل: ما يكون تحت غيره يستره ما علاه؛ فالتغطية والإخفاء يصفان حال المحل الواقع تحته، واللقاء مقصور على «تحت».",
}

VERDICTS: dict[int, str] = {
    60: "NUCLEUS-TRACE",
    93: "NUCLEUS-TRACE",
    95: "NUCLEUS-TRACE",
    141: "NUCLEUS-TRACE",
    193: "ROOT-TRACE",
    197: "ROOT-TRACE",
    331: "ROOT-TRACE",
    335: "ROOT-TRACE",
    384: "ROOT-TRACE",
    412: "NUCLEUS-TRACE",
    414: "NUCLEUS-TRACE",
    461: "NUCLEUS-TRACE",
    464: "NUCLEUS-TRACE",
    1124: "NUCLEUS-TRACE",
    1126: "NUCLEUS-TRACE",
    1532: "NUCLEUS-TRACE",
}


# هذه أيضا أحكام يدوية، لا ناتج تقاطع لفظي. وظيفتها بيان لماذا لم يُكتب مدار
# موجب مع اكتمال الصوت والحدث، مع إبقاء المرشح مفتوحا.
REJECTED_ORBITS: dict[int, str] = {
    41: "جمع معنى الفرع الصحراء والماء والساحل، ولا يكفي حدث الحركة العام لمدار واحد يقنع من غير الاتكاء على دعوى المصدر.",
    42: "جمع معنى الفرع الصحراء والماء والساحل، ولا يكفي حدث الحركة العام لمدار واحد يقنع من غير الاتكاء على دعوى المصدر.",
    202: "البيت والقصر والقلعة والضريح لا تقع في التجرد والخلوص بمدار واحد مقنع.",
    377: "التنفس والحسن والإتيان لا يطابقها طلوع الشمس إلا بتعميم مجازي متسلسل.",
    417: "الخضرة لا تقع في الخرق الجامع بمدار واحد مقنع.",
    512: "الصف يجمع الحوض والماء وأصوات الحيوان والعنق والذبح وسوق الحصان، وأحداث نطق الصادين لا تنتخب عضوا معجميا بعينه.",
    519: "الصف يجمع الحوض والماء وأصوات الحيوان والعنق والذبح وسوق الحصان، وأحداث نطق الصادين لا تنتخب عضوا معجميا بعينه.",
    535: "حدثا نطق الخاء لا يصلان وحدهما إلى الحوض أو الماء أو الحيوان أو الذبح بمدار معجمي واحد.",
    543: "أحداث نطق التاء والياء والتاء لا تصل وحدها إلى المعاني المتباعدة المجموعة في الصف.",
    837: "معنى الفرع لا يذكر إلا الصورة «بس» بلا تعريف قاموسي يصلها بحدث الجفاف.",
    892: "النبات والشجرة والرماد لا تقع في حدث النور بمدار واحد مقنع.",
    1170: "أبو منجل والأبنوس لا يقعان في مفارقة المقر باندفاع بمدار واحد مقنع.",
    1358: "القاهر والعصا والملك لا تقع في الامتداد السطحي الخفيف بمدار واحد مقنع.",
    1530: "التحت والجنوب والفوق لا تقع في الامتداد أو النفاذ الدقيق بمدار واحد مقنع.",
    1531: "التحت والجنوب والفوق لا تقع في الامتداد الدقيق والانفتاح بمدار واحد مقنع.",
    1533: "التحت والجنوب والفوق لا تقع في الامتداد بجانب أو الانقسام بمدار واحد مقنع.",
    1560: "الجنوب وحره وقوة الريح والأمر والحرق لا تقع في الامتداد بجانب بمدار واحد مقنع.",
    1562: "الجنوب وحره وقوة الريح والأمر والحرق لا تقع في الغوص أو المخالطة الغليظة بمدار واحد مقنع.",
    1574: "أحداث نطق الواو والصاد والتاء بقيت ثلاثة أحداث منقولة، ولا ينهض منها تأليف يدوي مقنع لمعاني الصف.",
    1747: "المعنى اسم شيث وبنيه، وتكرار الاسم لا يربط أحداث نطق الشين والياء والثاء بمعنى قاموسي مستقل.",
}


def event_payload(ev: FE.Ev | None) -> dict | None:
    if ev is None:
        return None
    return {
        "text": ev.text,
        "source": ev.source,
        "tier": ev.tier,
        "tier_ar": ev.tier_ar,
        "note": ev.note,
        "line": ev.line(),
    }


def sound_line(row: dict) -> str:
    sound = row["sound"]
    rows = "؛ ".join(sound.get("rows") or [])
    misses = "؛ ".join(sound.get("misses") or [])
    if sound.get("complete"):
        return f"- الرجل الأولى، الصوت: تامة؛ {rows}."
    found = f"المسارات الموجودة: {rows}. " if rows else ""
    return f"- الرجل الأولى، الصوت: ناقصة؛ {found}ما فُتش عنه: {misses}."


def classify(row: dict, ev: FE.Ev | None) -> tuple[str | None, str, str, str]:
    idx = int(row["comparative_index"])
    if idx in VERDICTS:
        return VERDICTS[idx], "READY", ORBITS[idx], "موجب"
    if ev is None:
        return None, "TOOL-GAP", "", "غياب حدث من FE.resolve"
    if not row["sound"]["complete"]:
        return None, "LAW-GAP", "", "نقص مسار الصوت"
    if row.get("proper_name"):
        return None, "OPEN-CANDIDATE", "", "علم مفصول عن العد"
    return None, "OPEN-CANDIDATE", "", "لا مدار مقنع"


def card(row: dict, ev: FE.Ev | None, verdict: str | None, closure: str,
         orbit: str, open_reason: str) -> str:
    idx = int(row["comparative_index"])
    old = f"COMPARATIVE-TRIAGE:{idx:04d}"
    ev_line = ev.line() if ev else (
        "- الحدث من السجل المجمد: لم يرجع `FE.resolve` حدثا لهذا المرشح؛ "
        "بقيت الرجل الثانية فجوة أداة."
    )
    if verdict:
        third = (
            f"- الرجل الثالثة، معنى قاموس الفرع بلا رتوش: «{row['foreign_sense']}».\n"
            f"- المدار المكتوب باليد: {orbit}"
        )
        status = (
            "- حالة الإغلاق: READY.\n"
            f"- الحكم (استكشاف): {verdict}.\n"
            f"- سطر النسخ (2026-08-14، {MARKER}:{idx:04d}): نُسخ الحكم السابق غير صادر بالحكم {verdict} بعد رد الرجل الثانية إلى `FE.resolve`."
        )
    else:
        if idx in REJECTED_ORBITS:
            orbit_line = f"- مراجعة المدار المكتوبة باليد: {REJECTED_ORBITS[idx]}"
        elif row.get("proper_name") and row["sound"]["complete"] and ev:
            orbit_line = "- مراجعة المدار: البطاقة علم أو عنصر علم، ففُصلت عن عد الصلات ولم تستعمل دعوى المصدر دليلا مستقلا."
        else:
            orbit_line = "- مراجعة المدار: لم يُكتب مدار موجب قبل اكتمال الرجل السابقة."
        third = (
            f"- الرجل الثالثة، معنى قاموس الفرع بلا رتوش: «{row['foreign_sense']}».\n"
            f"{orbit_line}"
        )
        status = (
            f"- حالة الإغلاق: {closure}.\n"
            f"- عائق: النوع={closure}؛ يتطلب={open_reason}.\n"
            "- الحكم (استكشاف): غير صادر؛ لا تدخل البطاقة عد الصلات.\n"
            f"- سطر النسخ (2026-08-14، {MARKER}:{idx:04d}): بقي الحكم السابق غير صادر بعد إعادة الرجل الثانية عبر `FE.resolve`."
        )
    block = (
        f"### بطاقة: إعادة حصاد `comparative:{idx:04d}`؛ `{row['foreign']}` «{row['foreign_sense']}»\n"
        f"<!-- {MARKER}:{idx:04d} -->\n"
        "- إصدار البروتوكول: RECOVERY-v2؛ طبقة استكشاف.\n"
        f"- سجل البطاقة السابقة: `{old}`؛ نسبة المصدر باقية: علي فهمي خشيم، `{row['book']}`، ص {row['page']}.\n"
        f"- اللسان المحكوم: `{row['assigned_tongue']}`؛ المرشح العربي: `{row['chosen_candidate']}`؛ وزنه `{row['chosen_candidate_weight']:.6f}`.\n"
        f"{sound_line(row)}\n"
        f"{ev_line}\n"
        f"{third}\n"
        f"{status}\n"
    )
    if "—" in block:
        raise ValueError(f"شرطة طويلة في البطاقة {idx}")
    return block


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    data = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = data["rows"]
    assert len(rows) == 738
    assert len({int(r["comparative_index"]) for r in rows}) == 738
    assert set(ORBITS) == set(VERDICTS)

    out_rows: list[dict] = []
    cards: dict[str, list[str]] = {"egyptian": [], "coptic": []}
    tiers = {str(i): 0 for i in range(5)}
    reasons: dict[str, int] = {}
    verdict_counts: dict[str, int] = {}

    for row in rows:
        ev = FE.resolve(row["chosen_candidate"])
        tiers[str(ev.tier if ev else 0)] += 1
        verdict, closure, orbit, reason = classify(row, ev)
        reasons[reason] = reasons.get(reason, 0) + 1
        if verdict:
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        idx = int(row["comparative_index"])
        out_rows.append({
            "comparative_index": idx,
            "assigned_tongue": row["assigned_tongue"],
            "foreign": row["foreign"],
            "foreign_sense": row["foreign_sense"],
            "chosen_candidate": row["chosen_candidate"],
            "chosen_candidate_weight": row["chosen_candidate_weight"],
            "sound": row["sound"],
            "proper_name": bool(row.get("proper_name")),
            "event": event_payload(ev),
            "semantic_orbit": orbit or None,
            "orbit_authorship": "يدوي" if orbit else None,
            "orbit_rejection": REJECTED_ORBITS.get(idx),
            "closure": closure,
            "verdict": verdict,
            "counted_link": bool(verdict),
            "open_reason": None if verdict else reason,
        })
        cards[row["assigned_tongue"]].append(
            card(row, ev, verdict, closure, orbit, reason)
        )

    assert tiers == {"0": 128, "1": 179, "2": 126, "3": 203, "4": 102}
    assert verdict_counts == {"NUCLEUS-TRACE": 11, "ROOT-TRACE": 5}
    assert reasons == {
        "موجب": 16,
        "غياب حدث من FE.resolve": 128,
        "نقص مسار الصوت": 564,
        "علم مفصول عن العد": 10,
        "لا مدار مقنع": 20,
    }

    payload = {
        "schema": "comparative-egyptian-coptic-reharvest-v1.0",
        "generated_at": "2026-08-14",
        "source_batch": SOURCE.relative_to(ROOT).as_posix(),
        "source_commit": "c833ee9",
        "event_resolver": "scripts/frozen_event.py:FE.resolve",
        "cards_examined": 738,
        "cards_written": 738,
        "event_tiers": tiers,
        "positive_cards": 16,
        "open_cards": 722,
        "verdict_counts": verdict_counts,
        "open_reason_counts_exclusive": {k: v for k, v in reasons.items() if k != "موجب"},
        "rows": out_rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")

    for tongue, path in READINGS.items():
        text = path.read_text(encoding="utf-8")
        start = f"<!-- {MARKER}:{tongue.upper()}:START -->"
        if start in text:
            raise RuntimeError(f"القسم موجود من قبل في {path}")
        heading = "المصرية" if tongue == "egyptian" else "القبطية"
        section = (
            f"\n{start}\n"
            f"## إعادة حصاد صفوف المقارنة، الدفعة صفر: {heading} (2026-08-14)\n\n"
            "أُعيدت الرجل الثانية وحدها عبر `FE.resolve`، وبقي الصوت والمعنى كما حُسبا في الدفعة الأصلية. كل مدار موجب في هذا القسم مكتوب باليد، ولا تقوم دعوى المصدر مقامه.\n\n"
            + "\n".join(cards[tongue])
            + f"<!-- {MARKER}:{tongue.upper()}:END -->\n"
        )
        if "—" in section:
            raise ValueError(f"شرطة طويلة في قسم {tongue}")
        with path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(section)

    highlights = [
        "`pr ↔ بر` في ظهور الشيء نتيجة التجرد",
        "`bine ↔ بنن` في الإصبع الممتد من أصل الكف",
        "`bn ↔ بنن` في الإصبع الممتد من أصل الكف",
        "`qm ↔ قم` في الصمغ المتضام كتلة لاصقة",
        "`nsw ↔ نشو` في الرفع والارتفاع",
        "`nshw ↔ نشو` في الرفع والارتفاع",
        "`mwt ↔ موت` في فعل الموت",
        "`mut ↔ موت` في فعل الموت",
        "`nfr ↔ نفر` في اندفاع هواء الزفير",
        "`sn ↔ صنو` في الأخ المتفرع من أصل واحد",
    ]
    audit = f"""# محضر إعادة حصاد المصرية والقبطية، الدفعة صفر

**التاريخ:** 2026-08-14  
**النطاق:** بطاقات الإيداع `c833ee9` وعددها 738.  
**الحالة:** مكتملة ومراجعة بعدستين.

## ضابط الانحدار الإلزامي

هذا أول عمل في الدفعة، وسبق كل حصاد. أُعيد حساب ست بطاقات مصرية موجبة صادرة من الرصيد القائم عبر `FE.resolve`:

| البطاقة | المرشح | الحكم السابق | الدرجة الجديدة | النتيجة |
|---|---|---|---:|---|
| `ḫtm` | `ختم` | ROOT-TRACE | 1 | سليم، لم يتغير الحكم |
| `mwt` | `موت` | ROOT-TRACE | 1 | سليم، لم يتغير الحكم |
| `smr` | `سمر` | ROOT-TRACE | 1 | سليم، لم يتغير الحكم |
| `mn` | `من` | NUCLEUS-TRACE | 2 | سليم، لم يتغير الحكم |
| `mr` | `مر` | NUCLEUS-TRACE | 2 | سليم، لم يتغير الحكم |
| `nfi̯` | `نف` | NUCLEUS-TRACE | 2 | سليم، لم يتغير الحكم |

**خلاصة الضابط:** 6 من 6 سليمة، وصفر تغير في الحكم. خُتم الضابط قبل بدء الدفعة صفر.

## التنفيذ

- فُحصت 738 بطاقة، وكُتبت 738 بطاقة نسخ إلحاقية، ولم يُمح حرف من ملفي القراءة.
- حُلّت الرجل الثانية بـ`FE.resolve` وحده: الدرجة 1 لعدد 179، والدرجة 2 لعدد 126، والدرجة 3 لعدد 203، والدرجة 4 لعدد 102، ولم يرجع حدثا لعدد 128.
- لم يُعد حساب الصوت ولا المروحة ولا معنى الفرع. الصوت التام في الدفعة الأصلية 46 بطاقة.
- كُتب كل مدار موجب باليد بالكلمات. وفي درجتي المحاكم بقيت أحداث النطق منقولة كما هي، ثم كُتب التأليف الدلالي يدويا في المدار.
- لم تستعمل دعوى خشيم دليلا مستقلا، ولم يحتكر مرشحه المروحة.

## الحصيلة

| البند | العدد |
|---|---:|
| فُحص | 738 |
| كُتب | 738 |
| موجب | 16 |
| ROOT-TRACE | 5 |
| NUCLEUS-TRACE | 11 |
| مفتوح | 722 |

أسباب المفتوح حصرية جامعة: 128 لم يرجع لها `FE.resolve` حدثا، و564 لها حدث لكن مسار الصوت ناقص، و10 أعلام اكتمل صوتها وحدثها ففُصلت عن العد، و20 اكتمل صوتها وحدثها ولم يقنع لها مدار مكتوب. وفي كل بطاقة صوت ناقصة حُفظ نص البحث السابق بالحرفين واسم اللسان من عمود الشاهد.

## أبرز عشرة أزواج دخلت

{chr(10).join(f'- {x}.' for x in highlights)}

## المراجعتان

- عدسة الاسترداد: أعادت اختبار كل مرشح من المروحة المحفوظة ولم تجعل الوزن بوابة، وقبلت 16 بطاقة اكتملت أرجلها الثلاث.
- عدسة التشكيك: هاجمت المدارات الموجبة، وعزلت الأعلام، ورفضت 20 مدارا محتملا لأنها احتاجت تعميما أو اتكاء على دعوى المصدر. لم يصدر `NO-TRACE` في هذه الدفعة.

## المخرجات

- `data/comparative-egyptian-coptic-reharvest-batch-000.json`
- `04-cross-linguistic/readings/egyptian.md`
- `04-cross-linguistic/readings/coptic.md`

## سطر الحصيلة

أُعيدت الرجل الثانية لـ738 بطاقة: 610 أحداث مجمدة موزعة على الدرجات الأربع، و16 صلة موجبة، و722 بطاقة مفتوحة بأسبابها المعدودة.
"""
    if "—" in audit:
        raise ValueError("شرطة طويلة في المحضر")
    AUDIT.write_text(audit, encoding="utf-8", newline="\n")

    print(f"كتبت {OUT.relative_to(ROOT).as_posix()}")
    print(f"ألحقت المصرية: {len(cards['egyptian'])} بطاقة")
    print(f"ألحقت القبطية: {len(cards['coptic'])} بطاقة")
    print(f"كتبت {AUDIT.relative_to(ROOT).as_posix()}")
    print(f"الحصيلة: موجب=16، مفتوح=722، الدرجات={tiers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
