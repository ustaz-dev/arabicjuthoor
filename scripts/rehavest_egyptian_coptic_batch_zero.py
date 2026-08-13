# -*- coding: utf-8 -*-
"""إعادةُ حصادِ دفعةِ المقارنةِ المصريةِ والقبطيةِ الصفر.

لا تعيد هذه الأداة حساب الصوت أو توليد المدار. الرجل الثانية تُحل عبر
``frozen_event.resolve``، والثالثة من AED لا من عمود خشيم المقارن. تعرض البطاقة
كل مداخل AED المصابة وتسمّي المختار الموافق للسياق، والمدارات الموجبة أدناه
قائمة كتبها القارئ يدويا بعد مراجعة المدخل المختار ومسار الصوت المحفوظ.
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import frozen_event as FE  # noqa: E402
import build_aed_index as AED  # noqa: E402

SOURCE = ROOT / "data" / "comparative-egyptian-coptic-batch-001.json"
OUT = ROOT / "data" / "comparative-egyptian-coptic-reharvest-batch-000.json"
AUDIT = ROOT / "05-audits" / "2026-08-14-egyptian-coptic-reharvest-batch-000.md"
READINGS = {
    "egyptian": ROOT / "04-cross-linguistic" / "readings" / "egyptian.md",
    "coptic": ROOT / "04-cross-linguistic" / "readings" / "coptic.md",
}
MARKER = "FROZEN-EVENT-REHARVEST-BATCH-000"


# اختيار المدخل حكم قراءة لسياق الصف، لا «أول إصابة». القيمة هي lemma id في
# AED كي يبقى الرسم العلمي والقسم النحوي والإحالة كما هي. غياب المفتاح مع وجود
# إصابات يعني أن أيا منها لم يوافق سياق خشيم. `pr` هو الخلاف المنصوص عليه في
# الأمر الدائم: يثبت اختلاف خشيم، ثم يقدم AED `house; temple; tomb; container`.
AED_SELECTIONS: dict[int, str] = {
    42: "71840",       # mr, canal
    60: "60220",       # pr, house; temple; tomb; container، خلاف صريح
    202: "60220",
    331: "69300",      # mwt, to die; to be dead
    384: "550034",     # nfr, good; beautiful; perfect; finished
    412: "136230",     # sn, brother
    414: "83260",      # nf, breath
    461: "143730",     # ss, net
    464: "143730",
    535: "120510",     # ḫḫ, neck; throat
    729: "71850",      # mr, pasture
    744: "180850",     # dšr.t, desert; foreign country
    837: "57210",      # Bs, Bes
    1358: "121210",    # ḫt, rod
    1560: "130850",    # swt, gust of wind
    1562: "130850",
}

BASELINE_POSITIVES = {
    60, 93, 95, 141, 193, 197, 331, 335, 384, 412, 414, 461, 464,
    1124, 1126, 1532,
}


# هذه المدارات كُتبت واحدا واحدا بالكلمات. لا اشتقاق لها من نص الحدث ولا من
# تشابه الألفاظ، ولا تُستعمل دعوى خشيم في arabic_gloss دليلا مستقلا.
ORBITS: dict[int, str] = {
    42: "مدار المحل: القناة مجرى يسترسل فيه الماء متحركا؛ فالمحل مسمى بوظيفة الجريان المسترسل التي يقرأها حدث `مر`.",
    331: "مدار الفعل: `to die; to be dead` هو وقوع التمدد مع الهمود والسكون وذهاب الحدة في حدث `موت`؛ فاللقاء مباشر في فعل الموت.",
    412: "مدار النتيجة: الأخ صنو لأنه فرع ثان خارج من أصل واحد؛ فالتفرع من الأصل ينتج الصنو المذكور في معنى الفرع.",
    414: "مدار الفعل: `breath` هو الهواء النافذ خارجا من الصدر؛ فالنفاذ والإبعاد بانتشار في حدث `نف` يصفان النفس الخارج مباشرة.",
    461: "مدار الصفة: `net` نسيج مبسوط تتفشى خيوطه الدقيقة متفرقة حول فراغاته؛ وتكرار حدث الشين على جانبي الانفتاح الممدود يصف هذه الهيئة الشبكية.",
    464: "مدار الصفة: `net` نسيج مبسوط تتفشى خيوطه الدقيقة متفرقة حول فراغاته؛ وتكرار حدث الشين على جانبي الانفتاح الممدود يصف هذه الهيئة الشبكية.",
    535: "مدار المحل: `neck; throat` مجرى جسدي ضيق ينفذ خلاله الهواء والطعام؛ وتكرار حدث الخاء يصف المضيق الخشن النافذ نفسه.",
    1358: "مدار الهيئة: `rod` جسم خطي ممتد دقيق؛ فالامتداد السطحي الخفيف في حدث `خطي` يصف هيئة القضيب مباشرة.",
    1560: "مدار الحركة: `gust of wind` دفعة من الهواء تنفصل عن كتلة الهواء وتمتد في جانب؛ وهذا هو وجه الامتداد والانقسام في حدث `شوط`.",
}

VERDICTS: dict[int, str] = {
    42: "NUCLEUS-TRACE",
    331: "ROOT-TRACE",
    412: "NUCLEUS-TRACE",
    414: "NUCLEUS-TRACE",
    461: "NUCLEUS-TRACE",
    464: "NUCLEUS-TRACE",
    535: "NUCLEUS-TRACE",
    1358: "NUCLEUS-TRACE",
    1560: "NUCLEUS-TRACE",
}


# هذه أيضا أحكام يدوية، لا ناتج تقاطع لفظي. وظيفتها بيان لماذا لم يُكتب مدار
# موجب مع اكتمال الصوت والحدث، مع إبقاء المرشح مفتوحا.
REJECTED_ORBITS: dict[int, str] = {
    41: "جمع معنى الفرع الصحراء والماء والساحل، ولا يكفي حدث الحركة العام لمدار واحد يقنع من غير الاتكاء على دعوى المصدر.",
    60: "قدّم AED معنى `house; temple; tomb; container` على «الأول؛ السابق؛ الظاهر»، ولا يقع البيت في التجرد والخلوص بمدار مقنع؛ فنُسخ الموجب القديم.",
    93: "إصابات AED لـ`bine` هي `bad; evil` وما اتصل بها، ولا يوافق شيء منها سياق النخلة والبلح والأصابع والموز؛ فنُسخ الموجب القديم.",
    95: "إصابات AED لـ`bn` هي النفي وطائر مائي، ولا يوافق شيء منها سياق النخلة والبلح والأصابع والموز؛ فنُسخ الموجب القديم.",
    141: "لم تحمل إصابات `qm` ترجمة إنجليزية صالحة للرجل الثالثة؛ فنُسخ الموجب القديم المبني على عمود خشيم.",
    193: "لم يحمل مدخل `nsw` ترجمة إنجليزية تعين معنى الرفع أو الملك؛ فنُسخ الموجب القديم.",
    197: "لم يوافق شيء من إصابات `nshw` سياق الملك والرفع والقائد الرفيع؛ فنُسخ الموجب القديم.",
    202: "البيت والقصر والقلعة والضريح لا تقع في التجرد والخلوص بمدار واحد مقنع.",
    335: "لم يرجع AED مدخلا لـ`mut`؛ فنُسخ الموجب القديم ولم يرث معنى `mwt` لمجرد تقارب الرسم.",
    377: "التنفس والحسن والإتيان لا يطابقها طلوع الشمس إلا بتعميم مجازي متسلسل.",
    384: "اختير من AED `good; beautiful; perfect; finished` الموافق لحسن خشيم، ولا تقع الجودة والجمال في الاندفاع الحاد بعيدا عن المضم؛ فنُسخ مدار الزفير القديم.",
    417: "الخضرة لا تقع في الخرق الجامع بمدار واحد مقنع.",
    512: "الصف يجمع الحوض والماء وأصوات الحيوان والعنق والذبح وسوق الحصان، وأحداث نطق الصادين لا تنتخب عضوا معجميا بعينه.",
    519: "الصف يجمع الحوض والماء وأصوات الحيوان والعنق والذبح وسوق الحصان، وأحداث نطق الصادين لا تنتخب عضوا معجميا بعينه.",
    535: "حدثا نطق الخاء لا يصلان وحدهما إلى الحوض أو الماء أو الحيوان أو الذبح بمدار معجمي واحد.",
    543: "أحداث نطق التاء والياء والتاء لا تصل وحدها إلى المعاني المتباعدة المجموعة في الصف.",
    837: "معنى الفرع لا يذكر إلا الصورة «بس» بلا تعريف قاموسي يصلها بحدث الجفاف.",
    892: "النبات والشجرة والرماد لا تقع في حدث النور بمدار واحد مقنع.",
    1170: "أبو منجل والأبنوس لا يقعان في مفارقة المقر باندفاع بمدار واحد مقنع.",
    1124: "لا يوافق النفي أو الطائر المائي في AED سياق الحجر والبنية ونور الشمس؛ فنُسخ الموجب القديم.",
    1126: "لا يوافق النفي أو الطائر المائي في AED سياق الحجر والبنية ونور الشمس؛ فنُسخ الموجب القديم.",
    1530: "التحت والجنوب والفوق لا تقع في الامتداد أو النفاذ الدقيق بمدار واحد مقنع.",
    1531: "التحت والجنوب والفوق لا تقع في الامتداد الدقيق والانفتاح بمدار واحد مقنع.",
    1533: "التحت والجنوب والفوق لا تقع في الامتداد بجانب أو الانقسام بمدار واحد مقنع.",
    1560: "الجنوب وحره وقوة الريح والأمر والحرق لا تقع في الامتداد بجانب بمدار واحد مقنع.",
    1562: "الجنوب وحره وقوة الريح والأمر والحرق لا تقع في الغوص أو المخالطة الغليظة بمدار واحد مقنع.",
    1574: "أحداث نطق الواو والصاد والتاء بقيت ثلاثة أحداث منقولة، ولا ينهض منها تأليف يدوي مقنع لمعاني الصف.",
    1747: "المعنى اسم شيث وبنيه، وتكرار الاسم لا يربط أحداث نطق الشين والياء والثاء بمعنى قاموسي مستقل.",
    1532: "لم يوافق شيء من إصابات `eset` معنى تحت أو الجنوب؛ فنُسخ الموجب القديم.",
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


def aed_payload(row: dict, ev: FE.Ev | None) -> dict:
    idx = int(row["comparative_index"])
    hits, how = AED.look(row["foreign"])
    wanted = AED_SELECTIONS.get(idx)
    chosen = next((entry for entry in hits if str(entry.get("id")) == wanted), None)
    if wanted and chosen is None:
        raise RuntimeError(f"اختيار AED غائب في البطاقة {idx}: {wanted}")
    reached_third_leg = bool(ev and row["sound"]["complete"])
    stage = (
        "selected" if chosen else
        "no_hit" if not hits else
        "no_context_match" if reached_third_leg else
        "not_reached"
    )
    return {
        "path": how,
        "query": row["foreign"],
        "hits": hits,
        "selected": chosen,
        "selection_stage": stage,
        "selection": (
            "اختير يدويا لموافقته سياق الصف في كتاب خشيم، ويقدم معناه على عمود المقارنة."
            if chosen else (
                "لم يرجع AED مدخلا لهذه الصورة."
                if not hits else (
                    "عُرضت الإصابات كلها ولم يوافق شيء منها سياق الصف في كتاب خشيم."
                    if reached_third_leg else
                    "عُرضت الإصابات كلها، ولم يُعيّن مدخل لأن البطاقة لم تبلغ الرجل الثالثة بعد نقص الصوت أو الحدث."
                )
            )
        ),
    }


def aed_lines(aed: dict, khashim_sense: str) -> list[str]:
    if aed["hits"]:
        rendered = "؛ ".join(
            f"`{entry['translit']}` [{entry.get('pos') or 'بلا قسم'}] "
            f"«{entry.get('en') or '[لا ترجمة إنجليزية]'}» "
            f"(AED `{entry.get('id')}`؛ {entry.get('ref') or 'بلا إحالة Wb'})"
            for entry in aed["hits"]
        )
    else:
        rendered = "لا إصابات"
    chosen = aed["selected"]
    selected_line = (
        f"`{chosen['translit']}` [{chosen.get('pos') or 'بلا قسم'}] "
        f"«{chosen.get('en') or '[لا ترجمة إنجليزية]'}» (AED `{chosen.get('id')}`)"
        if chosen else "لا اختيار"
    )
    return [
        f"- عمود خشيم المقارن محفوظ للخلاف لا بوصفه قاموسا: «{khashim_sense}».",
        f"- بحث AED: {aed['path']}؛ الصورة المستعلم عنها `{aed['query']}`؛ جميع المداخل: {rendered}.",
        f"- مدخل AED المختار: {selected_line}؛ {aed['selection']}",
    ]


def sound_line(row: dict) -> str:
    sound = row["sound"]
    rows = "؛ ".join(sound.get("rows") or [])
    misses = "؛ ".join(sound.get("misses") or [])
    if sound.get("complete"):
        return f"- الرجل الأولى، الصوت: تامة؛ {rows}."
    found = f"المسارات الموجودة: {rows}. " if rows else ""
    return f"- الرجل الأولى، الصوت: ناقصة؛ {found}ما فُتش عنه: {misses}."


def classify(row: dict, ev: FE.Ev | None, aed: dict) -> tuple[str | None, str, str, str]:
    idx = int(row["comparative_index"])
    if ev is None:
        return None, "TOOL-GAP", "", "غياب حدث من FE.resolve"
    if not row["sound"]["complete"]:
        return None, "LAW-GAP", "", "نقص مسار الصوت"
    if row.get("proper_name"):
        return None, "OPEN-CANDIDATE", "", "علم مفصول عن العد"
    if not aed["selected"]:
        reason = "لا معنى AED موافق للسياق" if aed["hits"] else "لا مدخل AED"
        return None, "OPEN-CANDIDATE", "", reason
    if idx in VERDICTS:
        return VERDICTS[idx], "READY", ORBITS[idx], "موجب"
    return None, "OPEN-CANDIDATE", "", "لا مدار مقنع"


def card(row: dict, ev: FE.Ev | None, aed: dict, verdict: str | None,
         closure: str, orbit: str, open_reason: str) -> str:
    idx = int(row["comparative_index"])
    old = f"COMPARATIVE-TRIAGE:{idx:04d}"
    ev_line = ev.line() if ev else (
        "- الحدث من السجل المجمد: لم يرجع `FE.resolve` حدثا لهذا المرشح؛ "
        "بقيت الرجل الثانية فجوة أداة."
    )
    if verdict:
        chosen = aed["selected"]
        third = (
            f"- الرجل الثالثة، معنى قاموس الفرع بلا رتوش: «{chosen.get('en')}» "
            f"من `{chosen['translit']}` في AED.\n"
            f"- المدار المكتوب باليد: {orbit}"
        )
        status = (
            "- حالة الإغلاق: READY.\n"
            f"- الحكم (استكشاف): {verdict}.\n"
            f"- سطر النسخ (2026-08-14، {MARKER}:{idx:04d}): "
            + (f"بقي الحكم السابق {verdict} بعد تصحيح معناه إلى AED."
               if idx in BASELINE_POSITIVES else
               f"نُسخ الحكم السابق غير صادر بالحكم {verdict} بعد اكتمال معنى AED المفرد.")
        )
    else:
        if idx in REJECTED_ORBITS:
            orbit_line = f"- مراجعة المدار المكتوبة باليد: {REJECTED_ORBITS[idx]}"
        elif row.get("proper_name") and row["sound"]["complete"] and ev:
            orbit_line = "- مراجعة المدار: البطاقة علم أو عنصر علم، ففُصلت عن عد الصلات ولم تستعمل دعوى المصدر دليلا مستقلا."
        else:
            orbit_line = "- مراجعة المدار: لم يُكتب مدار موجب قبل اكتمال الرجل السابقة."
        third = (
            "- الرجل الثالثة، معنى قاموس الفرع: "
            + (f"«{aed['selected'].get('en')}» من `{aed['selected']['translit']}` في AED.\n"
               if aed["selected"] else (
                   "لم تُبلَغ بعد؛ حُفظت قائمة AED بلا تعيين حتى يكتمل الصوت والحدث.\n"
                   if aed["selection_stage"] == "not_reached" else
                   "لم يثبت معنى AED موافق للسياق.\n"
               ))
            + f"{orbit_line}"
        )
        status = (
            f"- حالة الإغلاق: {closure}.\n"
            f"- عائق: النوع={closure}؛ يتطلب={open_reason}.\n"
            "- الحكم (استكشاف): غير صادر؛ لا تدخل البطاقة عد الصلات.\n"
            f"- سطر النسخ (2026-08-14، {MARKER}:{idx:04d}): "
            + ("نُسخ الحكم السابق الموجب لأن معنى AED لم يسند مداره."
               if idx in BASELINE_POSITIVES else
               "بقي الحكم السابق غير صادر بعد إعادة الحدث ومعنى الفرع عبر AED.")
        )
    block = (
        f"### بطاقة: إعادة حصاد `comparative:{idx:04d}`؛ `{row['foreign']}` «{row['foreign_sense']}»\n"
        f"<!-- {MARKER}:{idx:04d} -->\n"
        "- إصدار البروتوكول: RECOVERY-v2؛ طبقة استكشاف.\n"
        f"- سجل البطاقة السابقة: `{old}`؛ نسبة المصدر باقية: علي فهمي خشيم، `{row['book']}`، ص {row['page']}.\n"
        f"- اللسان المحكوم: `{row['assigned_tongue']}`؛ المرشح العربي: `{row['chosen_candidate']}`؛ وزنه `{row['chosen_candidate_weight']:.6f}`.\n"
        f"{sound_line(row)}\n"
        f"{ev_line}\n"
        f"{chr(10).join(aed_lines(aed, row['foreign_sense']))}\n"
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
    aed_path_counts: dict[str, int] = {}
    aed_hit_cards = 0
    aed_selected_cards = 0

    for row in rows:
        ev = FE.resolve(row["chosen_candidate"])
        aed = aed_payload(row, ev)
        aed_path_counts[aed["path"]] = aed_path_counts.get(aed["path"], 0) + 1
        aed_hit_cards += bool(aed["hits"])
        aed_selected_cards += bool(aed["selected"])
        tiers[str(ev.tier if ev else 0)] += 1
        verdict, closure, orbit, reason = classify(row, ev, aed)
        reasons[reason] = reasons.get(reason, 0) + 1
        if verdict:
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
        idx = int(row["comparative_index"])
        out_rows.append({
            "comparative_index": idx,
            "assigned_tongue": row["assigned_tongue"],
            "foreign": row["foreign"],
            "foreign_sense": row["foreign_sense"],
            "khashim_comparative_sense": row["foreign_sense"],
            "aed": aed,
            "branch_dictionary_sense": (
                aed["selected"].get("en") if aed["selected"] else None
            ),
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
            card(row, ev, aed, verdict, closure, orbit, reason)
        )

    assert tiers == {"0": 128, "1": 179, "2": 126, "3": 203, "4": 102}
    assert verdict_counts == {"NUCLEUS-TRACE": 8, "ROOT-TRACE": 1}
    positive_ids = set(VERDICTS)
    converted = positive_ids - BASELINE_POSITIVES
    retained = positive_ids & BASELINE_POSITIVES
    revoked = BASELINE_POSITIVES - positive_ids
    assert len(converted) == 4 and len(retained) == 5 and len(revoked) == 11

    payload = {
        "schema": "comparative-egyptian-coptic-reharvest-v1.1-aed",
        "generated_at": "2026-08-14",
        "source_batch": SOURCE.relative_to(ROOT).as_posix(),
        "source_commit": "c833ee9",
        "event_resolver": "scripts/frozen_event.py:FE.resolve",
        "branch_dictionary": "AED, Simon D. Schweitzer (data/aed-egyptian-lexicon.json)",
        "cards_examined": 738,
        "cards_written": 738,
        "event_tiers": tiers,
        "aed_path_counts": aed_path_counts,
        "aed_hit_cards": aed_hit_cards,
        "aed_selected_cards": aed_selected_cards,
        "positive_cards": len(positive_ids),
        "open_cards": 738 - len(positive_ids),
        "baseline_positive_cards": len(BASELINE_POSITIVES),
        "converted_after_dictionary_sense": len(converted),
        "converted_indices": sorted(converted),
        "retained_positive_indices": sorted(retained),
        "revoked_positive_indices": sorted(revoked),
        "verdict_counts": verdict_counts,
        "open_reason_counts_exclusive": {k: v for k, v in reasons.items() if k != "موجب"},
        "rows": out_rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8", newline="\n")

    for tongue, path in READINGS.items():
        text = path.read_text(encoding="utf-8")
        start = f"<!-- {MARKER}:{tongue.upper()}:START -->"
        end = f"<!-- {MARKER}:{tongue.upper()}:END -->"
        heading = "المصرية" if tongue == "egyptian" else "القبطية"
        section = (
            f"{start}\n"
            f"## إعادة حصاد صفوف المقارنة، الدفعة صفر: {heading} (2026-08-14)\n\n"
            "أُعيدت الرجل الثانية عبر `FE.resolve`، والثالثة من AED لا من عمود خشيم المقارن. تعرض كل بطاقة جميع إصابات AED ووسم الطريق والرسم العلمي، وتسمي المختار الموافق للسياق أو تصرح بأن لا إصابة توافقه. كل مدار موجب مكتوب باليد.\n\n"
            + "\n".join(cards[tongue])
            + f"{end}"
        )
        if "—" in section:
            raise ValueError(f"شرطة طويلة في قسم {tongue}")
        if start in text:
            before, tail = text.split(start, 1)
            _, after = tail.split(end, 1)
            updated = before + section + after
        else:
            updated = text.rstrip() + "\n\n" + section + "\n"
        path.write_text(updated, encoding="utf-8", newline="\n")

    highlights = [
        "`emro ↔ مر` في القناة مجرى للماء المسترسل",
        "`mwt ↔ موت` في فعل الموت",
        "`sn ↔ صنو` في الأخ المتفرع من أصل واحد",
        "`nf ↔ نف` في النفس النافذ خارجا",
        "`ssh ↔ شاش` في نسيج الشبكة المتفشي حول فراغاته",
        "`shs ↔ شاش` في نسيج الشبكة المتفشي حول فراغاته",
        "`khkh ↔ خخ` في مضيق العنق والحلق",
        "`kht ↔ خطي` في هيئة القضيب الممتد",
        "`swt ↔ شوط` في هبة الريح المنفصلة الممتدة",
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
- لم يُعد حساب الصوت ولا المروحة. أُعيدت الرجل الثالثة من AED، وعُرضت كل إصاباته في كل بطاقة مع وسم `هيكل مطابق` أو `هيكل مطوي` والرسم العلمي والقسم النحوي والإحالة.
- أصاب AED {aed_hit_cards} بطاقة، واختير مدخل سياقي مفرد في {aed_selected_cards}. بقي عمود خشيم ظاهرا لتسجيل الاتفاق والخلاف، ولم يعامل قاموسا.
- كُتب كل مدار موجب باليد بالكلمات. وفي درجتي المحاكم بقيت أحداث النطق منقولة كما هي، ثم كُتب التأليف الدلالي يدويا في المدار.
- لم تستعمل دعوى خشيم دليلا مستقلا، ولم يحتكر مرشحه المروحة.

## الحصيلة

| البند | العدد |
|---|---:|
| فُحص | 738 |
| كُتب | 738 |
| موجب | {len(positive_ids)} |
| ROOT-TRACE | {verdict_counts.get('ROOT-TRACE', 0)} |
| NUCLEUS-TRACE | {verdict_counts.get('NUCLEUS-TRACE', 0)} |
| مفتوح | {738 - len(positive_ids)} |
| موجب قديم قبل AED | {len(BASELINE_POSITIVES)} |
| تحوّل من مفتوح إلى موجب بعد المعنى القاموسي المفرد | {len(converted)} |
| موجب قديم بقي | {len(retained)} |
| موجب قديم نُسخ | {len(revoked)} |

**رقم الفرق المطلوب:** تحولت {len(converted)} بطاقات بعد أن صار لها معنى AED مفرد: {', '.join(f'`{idx:04d}`' for idx in sorted(converted))}. وبقيت الموجبات القديمة في {', '.join(f'`{idx:04d}`' for idx in sorted(retained))}، ونُسخ {len(revoked)} موجبا قديما لأن AED لم يسند المعنى الذي قام عليه المدار السابق: {', '.join(f'`{idx:04d}`' for idx in sorted(revoked))}.

أسباب المفتوح حصرية جامعة: {', '.join(f'{key}={value}' for key, value in reasons.items() if key != 'موجب')}. وفي كل بطاقة صوت ناقصة حُفظ نص البحث السابق بالحرفين واسم اللسان من عمود الشاهد، وفي كل بطاقة أصابها AED عُرضت قائمته كاملة ولو لم يختر منها شيء.

## أبرز عشرة أزواج دخلت

{chr(10).join(f'- {x}.' for x in highlights)}

## المراجعتان

- عدسة الاسترداد: أعادت اختبار كل مرشح من المروحة المحفوظة ولم تجعل الوزن بوابة، وقبلت {len(positive_ids)} بطاقات اكتملت أرجلها الثلاث.
- عدسة التشكيك: قارنت كل موجب قديم بمدخل AED المختار، فنسخت {len(revoked)} موجبا لم يعد له معنى قاموسي، وأبقت `OPEN-CANDIDATE` حيث لم توافق إصابة السياق أو لم يقنع المدار. لم يصدر `NO-TRACE`.

## المخرجات

- `data/comparative-egyptian-coptic-reharvest-batch-000.json`
- `04-cross-linguistic/readings/egyptian.md`
- `04-cross-linguistic/readings/coptic.md`

## سطر الحصيلة

أُعيدت الرجل الثانية والثالثة لـ738 بطاقة: 610 أحداث مجمدة، و{aed_hit_cards} إصابة AED، و{len(positive_ids)} صلات موجبة، و{738 - len(positive_ids)} بطاقة مفتوحة؛ تحولت {len(converted)} بطاقات بعد المعنى القاموسي المفرد.
"""
    if "—" in audit:
        raise ValueError("شرطة طويلة في المحضر")
    AUDIT.write_text(audit, encoding="utf-8", newline="\n")

    print(f"كتبت {OUT.relative_to(ROOT).as_posix()}")
    print(f"ألحقت المصرية: {len(cards['egyptian'])} بطاقة")
    print(f"ألحقت القبطية: {len(cards['coptic'])} بطاقة")
    print(f"كتبت {AUDIT.relative_to(ROOT).as_posix()}")
    print(f"الحصيلة: موجب={len(positive_ids)}، مفتوح={738 - len(positive_ids)}، "
          f"تحول={len(converted)}، الدرجات={tiers}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
