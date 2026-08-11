# -*- coding: utf-8 -*-
"""أتمم حصاد خشيم: 362 بطاقة لاتينية، ثم 186 بطاقة قبطية.

الرجل الثانية في اللاتينية هي نص لسان العرب الذي نقله خشيم في المدخل نفسه؛
لا تطلب الأداة معجمًا بديلًا. ولا يصدر حكم موجب في اللسانين بلا مدار مكتوب
بالكلمات. وفي القبطية تعرض البطاقة نواة خشيم الصريحة ونواة المشروع من الفهرس
المجمد، ثم تسجل الاتفاق أو الاختلاف ولا تملأ الغياب بالتخمين.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import unicodedata
from collections import Counter
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_khashim_old_latin_cards as LAT  # noqa: E402

SOURCE = ROOT / "data" / "khashim-pairs.json"
LATIN_READING = ROOT / "04-cross-linguistic" / "readings" / "old-latin.md"
COPTIC_READING = ROOT / "04-cross-linguistic" / "readings" / "coptic.md"
LATIN_REPORT = ROOT / "data" / "khashim-old-latin-batch-002.json"
COPTIC_REPORT = ROOT / "data" / "khashim-coptic-batch-001.json"
LATIN_AUDIT = ROOT / "05-audits" / "2026-08-11-khashim-old-latin-batch-002.md"
COPTIC_AUDIT = ROOT / "05-audits" / "2026-08-11-khashim-coptic-batch-001.md"

LATIN_START = "<!-- KHASHIM-OLD-LATIN-BATCH-002:START -->"
LATIN_END = "<!-- KHASHIM-OLD-LATIN-BATCH-002:END -->"
COPTIC_START = "<!-- KHASHIM-COPTIC-BATCH-001:START -->"
COPTIC_END = "<!-- KHASHIM-COPTIC-BATCH-001:END -->"

LATIN_BOOK = "علي فهمي خشيم، «اللاتينيّة عربيّة»"
COPTIC_BOOK = "علي فهمي خشيم، «القبطيّة عربيّة»"
FALLEN = "(سقطَ حرفُه في المسح)"
LATIN_BASELINE = 74
COPTIC_BASELINE = 189

LATIN_HEAD = re.compile(r"^[A-Za-zÀ-žĀ-ſæœÆŒ][A-Za-zÀ-žĀ-ſæœÆŒ' -]{1,30}$")
COPTIC_ROMAN_HEAD = re.compile(
    r"^[A-Za-zÀ-žĀ-ſæœÆŒ][A-Za-zÀ-žĀ-ſæœÆŒ,' -]{1,34}$"
)

COPTIC_ORBITS: dict[tuple[str, str, str], str] = {
    ("poh", "بحح", "ب ح وصل. جاء. حلّ بالمكان"): (
        "الوصول والمجيء والحلول بالمكان تنتهي إلى التمكن في الحلول والمقام الذي "
        "نقله خشيم في مادة `بحح`؛ فالمدار بلوغ المكان والاستقرار فيه."
    ),
    ("meini", "من", "مبانٍ. علامات"): (
        "المباني العالية تثبت بقوتها وتبرز علامات باقية؛ وهذا هو وجه القوة والثبات "
        "الذي يسميه نص العربية ومدار النواة `من`."
    ),
    ("mise", "مشي", "ولد. مولود"): (
        "الولادة في الفرع هي نفسها قول لسان العرب الذي نقله خشيم: `مشت الغنم` أي "
        "كثر أولادها، و`أمشى` أي ولد كثيرًا؛ فالمدار مباشر في التولد."
    ),
    ("mir, mer", "مر", "ربط"): (
        "الربط في الفرع يطابق نص العربية في الحبل الذي أُجيد فتله وفي `أمرّ الشيء` "
        "أي شده بالمرار؛ فالمدار شد الحبل وربطه."
    ),
}


def one_line(value: Any) -> str:
    return " ".join(str(value or "").split())


def quote(value: Any, limit: int = 620) -> str:
    text = one_line(value).replace("`", "ˋ")
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def replace_block(text: str, start: str, end: str, block: str) -> str:
    if start in text and end in text:
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        tail = after.lstrip()
        return before.rstrip() + "\n\n" + block.rstrip() + ("\n\n" + tail if tail else "\n")
    return text.rstrip() + "\n\n" + block.rstrip() + "\n"


def original_latin_inventory(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    inventory = [
        row for row in rows
        if row.get("tongue") == "old-latin"
        and (
            row.get("source") == "ocr-latin"
            or (
                row.get("source") == "khashim-latin"
                and not row.get("ocr_recovery")
                and row.get("foreign") != FALLEN
            )
        )
    ]
    if len(inventory) != 562:
        raise SystemExit(f"تغيّر مقام اللاتينية الأصلي: {len(inventory)}، والمتوقع 562")
    return inventory


def recovered_latin_by_new_row(rows: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    recovered: dict[int, dict[str, Any]] = {}
    for row in rows:
        rec = row.get("ocr_recovery") or {}
        if row.get("source") != "khashim-latin" or "matched_new_row" not in rec:
            continue
        index = int(rec["matched_new_row"])
        if index in recovered:
            raise SystemExit(f"أعيد استعمال صف المسح الجديد في الاسترداد: {index}")
        recovered[index] = row
    if len(recovered) != 290:
        raise SystemExit(f"تغيّر جرد الرؤوس المستردة: {len(recovered)}، والمتوقع 290")
    return recovered


def latin_item(
    valid_index: int,
    row: dict[str, Any],
    recovered: dict[int, dict[str, Any]],
    senses: dict[str, tuple[str, int]],
) -> dict[str, Any]:
    foreign = one_line(row.get("foreign"))
    root = LAT.ar_bare(row.get("arabic_root", ""))
    sense = one_line(row.get("foreign_sense", ""))
    recovered_sense = senses.get(foreign)
    if not sense and recovered_sense:
        sense = recovered_sense[0]
    paired_old = recovered.get(valid_index) if valid_index < 515 else None
    lisan_text = one_line(row.get("arabic_gloss", ""))
    if not lisan_text and paired_old:
        lisan_text = one_line(paired_old.get("arabic_gloss", ""))
    valid_head = bool(LATIN_HEAD.fullmatch(foreign))
    if valid_head:
        fan = LAT.candidate_fan(foreign, root)
        sound_ready, sound_rows, sound_misses = LAT.sound_audit(fan["route_skeleton"], root)
    else:
        fan = {
            "stem": foreign, "stripping": "تعذر لأن الرأس القديم ليس رسمًا لاتينيًا صالحًا",
            "raw_skeleton": [], "stem_skeleton": [], "route_skeleton": [],
            "full": [], "hit": False, "position": None, "source": "خارج المروحة",
        }
        sound_ready, sound_rows, sound_misses = (
            False, [], ["تعذر رصف الصوت قبل استرداد رسم لاتيني صالح للرأس القديم"]
        )
    loan = LAT.explicit_loan(sense)
    # لم يبق في ذيل الـ362 صف يجمع المروحة والصوت، ولذلك لا يُكتب مدار مصنوع
    # لمجرد إكمال الحكم. كل بطاقة تبقى مفتوحة بعائقها الفعلي.
    orbit = ""
    source_ready = bool(lisan_text)
    structural = bool(valid_head and fan["hit"] and len(root) in {2, 3})
    positive = bool(sound_ready and source_ready and orbit and structural and not loan)
    obstacles: list[str] = []
    if not valid_head:
        obstacles.append("استرداد الرسم اللاتيني الصالح للرأس القديم")
    if not fan["hit"]:
        obstacles.append("دخول مرشح خشيم نفسه في مروحة الأداة")
    if not sound_ready:
        obstacles.append("صفوف الشبكة أو اكتمال الرصف المبيّن في مسار الصوت")
    if not source_ready:
        obstacles.append("نص لسان العرب الذي نقله خشيم في المدخل")
    if len(root) not in {2, 3}:
        obstacles.append("تحليل يحدد درجة المادة العربية")
    if structural and sound_ready and source_ready and not orbit:
        obstacles.append("الرجل الثالثة: مدار مقنع مكتوب بالكلمات")
    if loan:
        obstacles.append(f"عزل اتجاه النقل الذي سماه النص بعبارة «{loan}»")
    return {
        "valid_index": valid_index, "row": row, "foreign": foreign, "root": root,
        "sense": sense, "lisan_text": lisan_text, "paired_old": paired_old,
        "fan": fan, "sound_ready": sound_ready, "sound_rows": sound_rows,
        "sound_misses": sound_misses, "source_ready": source_ready,
        "human_orbit": orbit, "loan_marker": loan, "positive": positive,
        "closure": "READY" if positive else "OPEN-CANDIDATE",
        "open_reasons": obstacles,
    }


def render_latin(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    foreign, root, sense = item["foreign"], item["root"], item["sense"]
    fan = item["fan"]
    degree = "NUCLEUS-TRACE" if len(root) == 2 else "ROOT-TRACE"
    verdict = f"**{degree} (استكشاف)**" if item["positive"] else "**غير صادر (استكشاف)**"
    sound = "؛ ".join(item["sound_rows"] + item["sound_misses"]) or "تعذر الرصف"
    fan_values = "، ".join(f"`{value}`" for value in fan["full"]) or "(لم تولد الأداة مرشحًا)"
    paired = item["paired_old"]
    recovery = (
        f"؛ والرأس نفسه ردّ إلى صف المسح القديم من السطر "
        f"{paired['ocr_recovery'].get('source_line')}" if paired else ""
    )
    orbit = item["human_orbit"] or "غير مكتوب؛ لم تكتمل الأرجل السابقة التي تجيز الحكم"
    required = "؛ ".join(item["open_reasons"]) or "لا عائق معلق"
    lines = [
        f"### بطاقة: `{foreign}` «{quote(sense) if sense else '(المعنى لم يسترد)' }»؛ خشيم لاتيني 002/{item['valid_index']:03d}",
        f"<!-- khashim-old-latin-batch-002:{item['valid_index']}:{root} -->",
        "- إصدار البروتوكول: RECOVERY-v2 (استكشاف).",
        f"- نسبة المصدر: المرشح `{foreign}→{root}` ومعنى الفرع ونص العربية من {LATIN_BOOK}؛ "
        "المروحة والمسار والمدار والحكم أعمال المشروع.",
        f"- الكلمة في الفرع: `{foreign}`؛ رسم المدخل في المسح الكامل المأذون{recovery}.",
        f"- موضع الصف: `data/khashim-pairs.json`؛ العضو الصالح {item['valid_index']}؛ المصدر `{item['row'].get('source')}`.",
        f"- الخطوة صفر: {fan['stripping']}؛ الخام `{''.join(fan['raw_skeleton']) or '∅'}`؛ "
        f"البديل `{''.join(fan['stem_skeleton']) or '∅'}`.",
        f"- درجة المقارنة: {'نواة' if len(root) == 2 else 'جذر كامل' if len(root) == 3 else 'مفتوحة'}؛ "
        "لا يقفز الحكم من درجة ناقصة إلى أخرى.",
        f"- مروحة المرشحات العربية من أداتنا: {fan_values}.",
        f"- موضع مرشح خشيم من المروحة: `{root}` "
        f"{'داخلها في الرتبة ' + str(fan['position']) if fan['hit'] else 'غير موجود فيها، فحُفظ ولم يُستبدل'}.",
        f"- مسح المعاني العربية: «{quote(item['lisan_text']) if item['lisan_text'] else '(لم يسلم النص في الصف)' }» "
        "[نقلَه خشيمٌ عن لسان العرب؛ هذه هي الرجل المعجمية المسماة، ولم يُطلب لها بديل].",
        f"- المقابل من اللسان: `{root}`؛ حقل خشيم نفسه لا أول مرشح من المروحة.",
        f"- مسار الصوت: {sound}. فُتش كل موضع بالحرفين وبلفظي «اللاتينيّة» و`Latin` في الشبكة المجمدة.",
        f"- المعنى من قاموس الفرع: «{quote(sense) if sense else '(فارغ)' }» [{LATIN_BOOK}؛ بلا رتوش].",
        f"- المدار: {orbit}.",
        f"- المصفاة: {'علامة الاتجاه «' + item['loan_marker'] + '» تمنع الحكم' if item['loan_marker'] else 'لا مانح صريح في سطر المعنى؛ غياب الاسم ليس إثبات أصالة'}.",
        "- فصل المتجانسات: البطاقة لهذا المدخل وهذا المعنى وحدهما.",
        "- جرد العلم ومؤشر اليتم: غير حاسمين في صف خشيم، فلا يستعملان رفعًا ولا إسقاطًا.",
        f"- إشعاع الأسرة في الفرع والعربية: الأعضاء المدعومة={1 if item['positive'] else 0}؛ المدخل المفرد وحده.",
        "- جسور الاسترداد المفحوصة: الرأس؛ المعنى؛ المروحة؛ مرشح خشيم؛ نص لسان العرب المنقول؛ "
        "الشبكة؛ المدار؛ الاتجاه؛ المتجانسات.",
        f"- عائق: النوع={item['closure']}؛ يتطلب={required}",
        f"- حالة الإغلاق: {item['closure']}",
        f"- الحكم (استكشاف): {verdict}",
        f"- ملاحظات: عدسة الاسترداد أبقت المرشح؛ وعدسة التشكيك "
        f"{'أصدرته بعد اكتمال الأرجل الثلاث' if item['positive'] else 'منعت الحكم من غير NO-TRACE'}.",
    ]
    summary = {
        "valid_index": item["valid_index"], "foreign": foreign, "sense": sense,
        "root": root, "source": item["row"].get("source"),
        "old_scan_head_recovered": bool(paired),
        "root_in_fan": fan["hit"], "fan_count": len(fan["full"]),
        "sound_ready": item["sound_ready"], "sound_rows": item["sound_rows"],
        "sound_misses": item["sound_misses"],
        "named_lexicon_ready": item["source_ready"],
        "named_lexicon_source": "نقلَه خشيمٌ عن لسان العرب" if item["source_ready"] else None,
        "human_orbit": item["human_orbit"] or None,
        "three_legs": {
            "sound": item["sound_ready"], "named_lexicon": item["source_ready"],
            "written_orbit": bool(item["human_orbit"]),
        },
        "loan_marker": item["loan_marker"], "closure": item["closure"],
        "verdict": degree if item["positive"] else None,
        "open_reasons": item["open_reasons"],
    }
    return "\n".join(lines), summary


def nucleus_registry() -> tuple[dict[str, dict[str, Any]], set[str]]:
    payload = json.loads((ROOT / "data" / "juthoor-core-levels.json").read_text(encoding="utf-8"))
    records = {
        LAT.ar_bare(row["nucleus"]): row
        for row in payload["levels"]["level_2_binary_nuclei"]["nuclei"]
    }
    return records, set(records)


NUCLEUS_RECORDS, NUCLEI = nucleus_registry()


def project_nucleus(root: str) -> tuple[str | None, str | None]:
    candidate = root if len(root) == 2 else root[:2] if len(root) >= 3 else ""
    if candidate in NUCLEI:
        record = NUCLEUS_RECORDS[candidate]
        return candidate, one_line(record.get("jabal_lexicon_reading_ar")) or None
    root_record = LAT.ROOT_RECORDS.get(root)
    if root_record and LAT.ar_bare(root_record.get("binary", "")) in NUCLEI:
        candidate = LAT.ar_bare(root_record["binary"])
        return candidate, one_line(NUCLEUS_RECORDS[candidate].get("jabal_lexicon_reading_ar")) or None
    return None, None


def coptic_comparison(khashim: str, ours: str | None) -> tuple[str, str]:
    khashim = LAT.ar_bare(khashim)
    if khashim and ours:
        if khashim == ours:
            return "AGREE", "تتوافقان"
        return "DIFFER", "تختلفان"
    if not khashim and ours:
        return "KHASHIM-NUCLEUS-NOT-RECOVERED", "لم تُسترد نواة خشيم، فلا يُصطنع اتفاق ولا اختلاف"
    if khashim and not ours:
        return "PROJECT-NUCLEUS-NOT-IN-FROZEN-INDEX", "نواة خشيم مسماة ونواتنا غائبة من الفهرس المجمد"
    return "BOTH-UNAVAILABLE", "لم تسترد نواة خشيم ولم تسجل نواتنا، فلا مقارنة"


def coptic_item(index: int, row: dict[str, Any]) -> dict[str, Any]:
    foreign, root = one_line(row.get("foreign")), LAT.ar_bare(row.get("arabic_root", ""))
    sense, source_text = one_line(row.get("foreign_sense")), one_line(row.get("arabic_gloss"))
    analysis_head = foreign.split(",", 1)[0].strip()
    roman = row.get("source") == "ocr-coptic" and bool(COPTIC_ROMAN_HEAD.fullmatch(foreign))
    if roman:
        fan = LAT.candidate_fan(analysis_head, root)
        sound_ready, sound_rows, sound_misses = LAT.sound_audit(fan["route_skeleton"], root)
    else:
        fan = {
            "stem": foreign, "stripping": "لا تعرية؛ الرأس القديم مكسور أو منقول بحرف عربي لا بالرسم القبطي",
            "raw_skeleton": [], "stem_skeleton": [], "route_skeleton": [],
            "full": [], "hit": False, "position": None, "source": "خارج المروحة",
        }
        sound_ready, sound_rows, sound_misses = False, [], [
            "الرأس القديم لا يحمل رسمًا قبطيًا أو رومنةً صالحةً للرصف"
        ]
    orbit = COPTIC_ORBITS.get((foreign, root, sense), "")
    khashim_nucleus = LAT.ar_bare(row.get("arabic_nucleus", ""))
    our_nucleus, our_event = project_nucleus(root)
    comparison, comparison_ar = coptic_comparison(khashim_nucleus, our_nucleus)
    loan = LAT.explicit_loan(sense + " " + source_text)
    structural = bool(roman and fan["hit"] and len(root) in {2, 3})
    source_ready = bool(source_text)
    positive = bool(structural and sound_ready and source_ready and orbit and not loan)
    obstacles: list[str] = []
    if not roman:
        obstacles.append("استرداد الرأس القبطي أو رومنته السليمة من المسح")
    if not fan["hit"]:
        obstacles.append("دخول مرشح خشيم نفسه في مروحة الأداة")
    if not sound_ready:
        obstacles.append("صفوف الشبكة أو اكتمال الرصف المبيّن في مسار الصوت")
    if not source_ready:
        obstacles.append("نص العربية الذي نقله خشيم في المدخل")
    if len(root) not in {2, 3}:
        obstacles.append("تحليل يحدد درجة المادة العربية")
    if structural and sound_ready and source_ready and not orbit:
        obstacles.append("الرجل الثالثة: مدار مقنع مكتوب بالكلمات")
    if loan:
        obstacles.append(f"عزل اتجاه النقل المسمى «{loan}»")
    return {
        "index": index, "row": row, "foreign": foreign, "analysis_head": analysis_head,
        "root": root, "sense": sense, "source_text": source_text, "fan": fan,
        "sound_ready": sound_ready, "sound_rows": sound_rows, "sound_misses": sound_misses,
        "source_ready": source_ready, "human_orbit": orbit, "loan_marker": loan,
        "khashim_nucleus": khashim_nucleus or None, "our_nucleus": our_nucleus,
        "our_nucleus_event": our_event, "nucleus_comparison": comparison,
        "nucleus_comparison_ar": comparison_ar,
        "positive": positive, "closure": "READY" if positive else "OPEN-CANDIDATE",
        "open_reasons": obstacles,
    }


def render_coptic(item: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    foreign, root, sense, fan = item["foreign"], item["root"], item["sense"], item["fan"]
    degree = "NUCLEUS-TRACE" if len(root) == 2 else "ROOT-TRACE"
    verdict = f"**{degree} (استكشاف)**" if item["positive"] else "**غير صادر (استكشاف)**"
    sound = "؛ ".join(item["sound_rows"] + item["sound_misses"]) or "تعذر الرصف"
    fan_values = "، ".join(f"`{value}`" for value in fan["full"]) or "(لم تولد الأداة مرشحًا)"
    orbit = item["human_orbit"] or "غير مكتوب؛ لم تكتمل الأرجل السابقة التي تجيز الحكم"
    required = "؛ ".join(item["open_reasons"]) or "لا عائق معلق"
    kh = f"`{item['khashim_nucleus']}`" if item["khashim_nucleus"] else "(لم تُسترد صريحة في الصف)"
    ours = f"`{item['our_nucleus']}`" if item["our_nucleus"] else "(غير مسجلة في الفهرس المجمد)"
    event = f"؛ مدارها «{item['our_nucleus_event']}»" if item["our_nucleus_event"] else ""
    lines = [
        f"### بطاقة: `{foreign}` «{quote(sense) if sense else '(المعنى لم يسترد)' }»؛ خشيم قبطي 001/{item['index']:03d}",
        f"<!-- khashim-coptic-batch-001:{item['index']}:{root} -->",
        "- إصدار البروتوكول: RECOVERY-v2 (استكشاف).",
        f"- نسبة المصدر: المرشح `{foreign}→{root}` وشرحه من {COPTIC_BOOK}؛ المروحة والمسار "
        "واستخراج نواتنا والمدار والحكم أعمال المشروع.",
        f"- الكلمة في الفرع: `{foreign}`؛ مصدر الصف `{item['row'].get('source')}`.",
        f"- الخطوة صفر: {fan['stripping']}؛ رأس التحليل `{item['analysis_head']}`؛ "
        f"الهيكل `{''.join(fan['route_skeleton']) or '∅'}`.",
        f"- درجة المقارنة: {'نواة' if len(root) == 2 else 'جذر كامل' if len(root) == 3 else 'مفتوحة'}؛ "
        "فُحص الجذر والنواة كل على استقلال.",
        f"- مروحة المرشحات العربية من أداتنا: {fan_values}.",
        f"- موضع مرشح خشيم من المروحة: `{root}` "
        f"{'داخلها في الرتبة ' + str(fan['position']) if fan['hit'] else 'غير موجود فيها، فحُفظ ولم يُستبدل'}.",
        f"- مسح المعاني العربية: «{quote(item['source_text']) if item['source_text'] else '(لم يسلم النص)' }» "
        f"[{COPTIC_BOOK}؛ نقل كما هو].",
        f"- المقابل من اللسان: `{root}`؛ حقل خشيم نفسه لا أول مرشح من المروحة.",
        f"- نواة خشيم ونواتنا: نواة خشيم {kh}؛ نواتنا من `data/juthoor-core-levels.json` {ours}{event}؛ "
        f"المقارنة: **{item['nucleus_comparison_ar']}** (`{item['nucleus_comparison']}`).",
        f"- مسار الصوت: {sound}. فُتش كل موضع بالحرفين وبلفظي «القبطيّة» و`Coptic` في الشبكة المجمدة.",
        f"- المعنى من قاموس الفرع: «{quote(sense) if sense else '(فارغ)' }» [{COPTIC_BOOK}؛ بلا رتوش].",
        f"- المدار: {orbit}.",
        f"- المصفاة: {'علامة الاتجاه «' + item['loan_marker'] + '» تمنع الحكم' if item['loan_marker'] else 'لا مانح صريح؛ غياب الاسم ليس إثبات أصالة'}.",
        "- فصل المتجانسات: البطاقة لهذا المدخل وهذا المعنى وحدهما.",
        "- جرد العلم ومؤشر اليتم: غير حاسمين في صف خشيم.",
        f"- إشعاع الأسرة في الفرع والعربية: الأعضاء المدعومة={1 if item['positive'] else 0}؛ المدخل المفرد وحده.",
        "- جسور الاسترداد المفحوصة: الرأس؛ المعنى؛ المروحة؛ مرشح خشيم؛ نص العربية؛ "
        "نواة خشيم؛ نواة المشروع؛ الشبكة؛ المدار؛ الاتجاه؛ المتجانسات.",
        f"- عائق: النوع={item['closure']}؛ يتطلب={required}",
        f"- حالة الإغلاق: {item['closure']}",
        f"- الحكم (استكشاف): {verdict}",
        f"- ملاحظات: عدسة الاسترداد أبقت المرشح؛ وعدسة التشكيك "
        f"{'أصدرته بعد اكتمال الأرجل الثلاث ومدار مكتوب' if item['positive'] else 'منعت الحكم من غير NO-TRACE'}.",
    ]
    summary = {
        "index": item["index"], "foreign": foreign, "sense": sense, "root": root,
        "source": item["row"].get("source"), "root_in_fan": fan["hit"],
        "fan_count": len(fan["full"]), "sound_ready": item["sound_ready"],
        "sound_rows": item["sound_rows"], "sound_misses": item["sound_misses"],
        "named_arabic_text_ready": item["source_ready"],
        "human_orbit": item["human_orbit"] or None,
        "khashim_nucleus": item["khashim_nucleus"], "our_nucleus": item["our_nucleus"],
        "our_nucleus_event": item["our_nucleus_event"],
        "nucleus_comparison": item["nucleus_comparison"],
        "three_legs": {
            "sound": item["sound_ready"], "named_lexicon": item["source_ready"],
            "written_orbit": bool(item["human_orbit"]),
        },
        "loan_marker": item["loan_marker"], "closure": item["closure"],
        "verdict": degree if item["positive"] else None,
        "open_reasons": item["open_reasons"],
    }
    return "\n".join(lines), summary


def write_latin_audit(report: dict[str, Any]) -> None:
    reasons = Counter(reason for row in report["rows"] for reason in row["open_reasons"])
    lines = [
        "# إتمام حصاد خشيم للاتينية القديمة، الدفعة 002",
        "", "## الأعداد", "",
        f"- مقام المرشحين الأصلي: {report['inventory']['original_candidates']}.",
        f"- المكتوب سابقًا: {report['inventory']['previously_written']}.",
        f"- المكتوب هنا: {report['cards_written']}.",
        f"- الرؤوس القديمة المستردة من المسح الجديد: {report['head_recovery']['recovered']} من "
        f"{report['head_recovery']['fallen']}؛ الباقي {report['head_recovery']['still_fallen']}.",
        f"- موجب استكشافي: {report['positive']}. مفتوح: {report['open_candidate']}.",
        f"- عداد اللاتينية: {report['count_links']['before']}→{report['count_links']['after']}.",
        "", "## أسباب الفتح المتداخلة", "", "| السبب | البطاقات |", "|---|---:|",
    ]
    lines.extend(f"| {reason} | {count} |" for reason, count in reasons.most_common())
    lines.extend([
        "", "## حراسة الميثاق", "",
        "نص الرجل الثانية في كل صف سالم هو نص لسان العرب الذي نقله خشيم نفسه؛ لا بحث معجمي "
        "خارجي في هذه الدفعة. لم يبق في ذيل الـ362 صف يجمع إصابة المروحة ورصف الشبكة، "
        "فلم يُكتب مدار مصنوع ولم يصدر موجب. كل بطاقة مع ذلك مكتوبة ومحفوظة OPEN-CANDIDATE.", "",
    ])
    LATIN_AUDIT.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def write_coptic_audit(report: dict[str, Any]) -> None:
    reasons = Counter(reason for row in report["rows"] for reason in row["open_reasons"])
    lines = [
        "# حصاد خشيم للقبطية، الدفعة 001", "", "## الأعداد", "",
        f"- صفوف المسح القديم: {report['inventory']['old_scan']}.",
        f"- صفوف المسح الجديد: {report['inventory']['new_scan']}.",
        f"- البطاقات المكتوبة: {report['cards_written']}.",
        f"- موجب استكشافي: {report['positive']}. مفتوح: {report['open_candidate']}.",
        f"- نواة خشيم الصريحة المستردة: {report['nucleus_comparison']['khashim_explicit']}.",
        f"- توافق نواته ونواتنا: {report['nucleus_comparison']['agree']}. اختلافهما: "
        f"{report['nucleus_comparison']['differ']}.",
        f"- غير قابل للمقارنة لغياب إحدى النواتين أو كلتيهما: {report['nucleus_comparison']['unavailable']}.",
        f"- عداد القبطية: {report['count_links']['before']}→{report['count_links']['after']}.",
        "", "## أسباب الفتح المتداخلة", "", "| السبب | البطاقات |", "|---|---:|",
    ]
    lines.extend(f"| {reason} | {count} |" for reason, count in reasons.most_common())
    lines.extend([
        "", "## شهادة النواة", "",
        "تعرض كل بطاقة نواة خشيم ونواة المشروع معًا. لا تُملأ نواة خشيم من تقسيمنا حين يغيب "
        "حقلها، ولا تُرد نواتنا إلى تقسيمه. في الصفوف السبعة التي سلم فيها نصه الثنائي اتفق "
        "التقسيمان في خمسة واختلفا في اثنين. وكل حكم موجب يحمل مدارًا مكتوبًا بالكلمات.", "",
    ])
    COPTIC_AUDIT.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = payload["rows"]
    recovery = payload.get("latin_head_recovery", {})
    recovered = recovered_latin_by_new_row(rows)

    inventory = original_latin_inventory(rows)
    prior = json.loads((ROOT / "data" / "khashim-old-latin-batch-001.json").read_text(encoding="utf-8"))
    used = {int(row["valid_index"]) for row in prior["rows"]}
    if len(used) != 200:
        raise SystemExit(f"تغيّرت عضوية الدفعة الأولى: {len(used)}")
    senses = LAT.ocr_sense_index()
    latin_items = [
        latin_item(index, row, recovered, senses)
        for index, row in enumerate(inventory) if index not in used
    ]
    if len(latin_items) != 362:
        raise SystemExit(f"لم تبلغ بقية اللاتينية 362: {len(latin_items)}")
    latin_rendered, latin_rows = [], []
    for item in latin_items:
        rendered, summary = render_latin(item)
        latin_rendered.append(rendered)
        latin_rows.append(summary)
    latin_positive = sum(bool(row["verdict"]) for row in latin_rows)
    if any(row["verdict"] and not row["human_orbit"] for row in latin_rows):
        raise SystemExit("صدر حكم لاتيني موجب بلا مدار مكتوب")
    latin_section = "\n".join([
        LATIN_START,
        "## إتمام حصاد خشيم للاتينية القديمة (362 بطاقة؛ 2026-08-11)", "",
        "**المقام.** هذه كل الصفوف الباقية من مقام الـ562 بعد الدفعة الأولى. رُد 290 رأسًا "
        "من المسح القديم إلى المسح الكامل، واستعملت نظائرها لإحكام المصدر من غير مضاعفة الدعوى.", "",
        "**الأرجل الثلاث.** الصوت من الشبكة، والرجل المعجمية نص لسان العرب الذي نقله خشيم، "
        "والرجل الثالثة مدار مكتوب. لا حكم بلا الثلاث.", "",
        f"**الحصيلة.** كُتبت {len(latin_rows)} بطاقة؛ موجب {latin_positive}؛ "
        f"مفتوح {len(latin_rows) - latin_positive}.", "", *latin_rendered, LATIN_END,
    ])
    LATIN_READING.write_text(
        unicodedata.normalize("NFC", replace_block(
            LATIN_READING.read_text(encoding="utf-8"), LATIN_START, LATIN_END, latin_section
        )), encoding="utf-8", newline="\n",
    )
    latin_report = {
        "generated_by": "scripts/build_khashim_latin_coptic_completion.py",
        "batch": "002", "source": "data/khashim-pairs.json", "book": LATIN_BOOK,
        "inventory": {"original_candidates": 562, "previously_written": 200, "remaining": 362},
        "head_recovery": {
            "fallen": recovery.get("old_rows_with_fallen_head"),
            "recovered": recovery.get("heads_recovered"),
            "still_fallen": recovery.get("heads_still_fallen"),
        },
        "cards_written": len(latin_rows), "positive": latin_positive,
        "open_candidate": len(latin_rows) - latin_positive,
        "count_links": {"before": LATIN_BASELINE, "after": LATIN_BASELINE + latin_positive},
        "rows": latin_rows,
    }
    LATIN_REPORT.write_text(
        json.dumps(latin_report, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n",
    )
    write_latin_audit(latin_report)

    coptic_source = [row for row in rows if row.get("tongue") == "coptic"]
    old_count = sum(row.get("source") == "khashim-coptic" for row in coptic_source)
    new_count = sum(row.get("source") == "ocr-coptic" for row in coptic_source)
    if (len(coptic_source), old_count, new_count) != (186, 169, 17):
        raise SystemExit(
            f"تغيّر جرد القبطية: الكل/قديم/جديد={len(coptic_source)}/{old_count}/{new_count}"
        )
    coptic_items = [coptic_item(index, row) for index, row in enumerate(coptic_source)]
    coptic_rendered, coptic_rows = [], []
    for item in coptic_items:
        rendered, summary = render_coptic(item)
        coptic_rendered.append(rendered)
        coptic_rows.append(summary)
    coptic_positive = sum(bool(row["verdict"]) for row in coptic_rows)
    if any(row["verdict"] and not row["human_orbit"] for row in coptic_rows):
        raise SystemExit("صدر حكم قبطي موجب بلا مدار مكتوب")
    comparisons = Counter(row["nucleus_comparison"] for row in coptic_rows)
    explicit = sum(bool(row["khashim_nucleus"]) for row in coptic_rows)
    agree, differ = comparisons["AGREE"], comparisons["DIFFER"]
    unavailable = len(coptic_rows) - agree - differ
    coptic_section = "\n".join([
        COPTIC_START,
        "## حصاد خشيم للقبطية (186 بطاقة؛ 2026-08-11)", "",
        "**المقام.** كُتبت صفوف المسح القديم الـ169 وصفوف المسح الجديد الـ17 كلها. "
        "تعرض كل بطاقة نواة خشيم الصريحة ونواة المشروع من الفهرس المجمد مع حكم الاتفاق.", "",
        f"**شهادة النواة.** استردت نواة خشيم صريحة في {explicit} صفوف: توافق التقسيمان في "
        f"{agree} واختلفا في {differ}؛ ولم أصطنع مقارنة حين غابت إحدى النواتين.", "",
        f"**الحصيلة.** كُتبت {len(coptic_rows)} بطاقة؛ موجب {coptic_positive}؛ "
        f"مفتوح {len(coptic_rows) - coptic_positive}.", "", *coptic_rendered, COPTIC_END,
    ])
    COPTIC_READING.write_text(
        unicodedata.normalize("NFC", replace_block(
            COPTIC_READING.read_text(encoding="utf-8"), COPTIC_START, COPTIC_END, coptic_section
        )), encoding="utf-8", newline="\n",
    )
    coptic_report = {
        "generated_by": "scripts/build_khashim_latin_coptic_completion.py",
        "batch": "001", "source": "data/khashim-pairs.json", "book": COPTIC_BOOK,
        "inventory": {"old_scan": old_count, "new_scan": new_count, "total": len(coptic_rows)},
        "cards_written": len(coptic_rows), "positive": coptic_positive,
        "open_candidate": len(coptic_rows) - coptic_positive,
        "nucleus_comparison": {
            "khashim_explicit": explicit, "agree": agree, "differ": differ,
            "unavailable": unavailable,
        },
        "count_links": {"before": COPTIC_BASELINE, "after": COPTIC_BASELINE + coptic_positive},
        "rows": coptic_rows,
    }
    COPTIC_REPORT.write_text(
        json.dumps(coptic_report, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8", newline="\n",
    )
    write_coptic_audit(coptic_report)
    print(
        f"اللاتينية: كُتب {len(latin_rows)}، موجب {latin_positive}، مفتوح {len(latin_rows)-latin_positive}؛ "
        f"استرد رأس {recovery.get('heads_recovered')}."
    )
    print(
        f"القبطية: كُتب {len(coptic_rows)} ({old_count}+{new_count})، موجب {coptic_positive}، "
        f"مفتوح {len(coptic_rows)-coptic_positive}؛ النواة توافق {agree} وتختلف {differ}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
