# -*- coding: utf-8 -*-
"""ابنِ جولةَ المصريّةِ الكبرى من حصادِ خشيم ومقّار في دفعاتٍ ثابتة.

هذا الباني يعيد استعمال قلب ``build_khashim_egyptian_cards.py`` الذي نجح في
جولة بدج: مروحة المرشحين، وتطبيع الجذر العربي، وفهرس النوى، ومسارات الشبكة.
ولا يعيد استعمال مصفاة المعاني الإنجليزية لأن المادة الجديدة عربية الشرح.

الآلة تسترجع ولا تحكم دلاليًا. كل مرشح في المروحة يدخل بيان الدفعة، ويصدر الحكم
الموجب فقط لعضو له مدار مكتوب صراحة في ``HUMAN_ORBITS`` بعد اكتمال الأرجل
الثلاث. غير ذلك يبقى ``OPEN-CANDIDATE`` ولا يتحول غياب المدار إلى اختبار آلي.

الاستعمال:
    python scripts/build_egyptian_gods_maqar_cards.py --batch 1
    python scripts/build_egyptian_gods_maqar_cards.py --check
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import unicodedata
from collections import Counter
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_khashim_egyptian_cards as K  # noqa: E402

SOURCE = ROOT / "data" / "prior-art-extended-pairs.json"
READING = ROOT / "04-cross-linguistic" / "readings" / "egyptian.md"
AUDIT = ROOT / "05-audits" / "2026-08-11-egyptian-gods-and-maqar.md"
ROOT_EVENTS_PATH = ROOT / "computational" / "data" / "layer_2_results_v2.jsonl"

BATCH_SIZE = 300
EXPECTED = 2725
EXPECTED_BOOKS = {
    "khashim-gods1": 2046,
    "maqar-egyptian-colloquial": 503,
    "khashim-hieroglyphic": 176,
}
BOOK_ORDER = tuple(EXPECTED_BOOKS)
BOOK_LABELS = {
    "khashim-gods1": "علي فهمي خشيم، «آلهة مصر العربية، الجزء الأول»",
    "maqar-egyptian-colloquial": "سامح مقّار، «أصل الألفاظ العامية من المصرية القديمة»",
    "khashim-hieroglyphic": "علي فهمي خشيم محققًا، «العرب والهيروغليفية»",
}
AUTHOR_LABELS = {
    "khashim-gods1": "علي فهمي خشيم",
    "maqar-egyptian-colloquial": "سامح مقّار",
    "khashim-hieroglyphic": "علي فهمي خشيم",
}

NAME_RE = re.compile(
    r"(?:اسم|إله|الإله|إلهة|الآلهة|معبود|معبودة|رب(?:ة| الأرباب)?|ملك|ملوك|"
    r"فرعون|حورس|رع\b|أوزير|إيزيس|آمون|أتوم|خنوم|حتحور|أنوبيس|لقب|ربة)",
    re.I,
)
FEMININE = re.compile(r"[-.]t$", re.I)


# المدار قراءة بشرية مكتوبة، لا تقاطع ألفاظ آلي. المفتاح هو رتبة الصف في الجرد
# الثابت ثم المرشح الذي صدر له الحكم. تُضاف المدارات على دفعات بعد قراءة العضو.
HUMAN_ORBITS: dict[tuple[int, str], tuple[str, str]] = {
    (0, "من"): (
        "NUCLEUS-TRACE",
        "وصفُ الاسم الملكي بالقوي يطابق وجه القوة والثبات في حدث النواة `من`؛ "
        "فالمدار مباشر في القوة، ولا يرث الاسم منه حكم مفردة معجمية عامة.",
    ),
    (449, "خرد"): (
        "ROOT-TRACE",
        "الطفل والمولود باقيان على الفطرة والأصل قبل الاستعمال والتجربة، وهو الحدث "
        "نفسه في قراءة `خرد` المجمّدة؛ فالمدار مباشر في حداثة الأصل.",
    ),
    (955, "كم"): (
        "NUCLEUS-TRACE",
        "السواد حال غشاء يحجب ظاهر الشيء، وحدث `كم` هو تغطيته بغطاء زائد؛ فالمدار "
        "حال التغطية المظلمة، مع فصل اسم الكلب عن الصفة.",
    ),
    (1491, "جن"): (
        "NUCLEUS-TRACE",
        "البستان المستور بكثافة نباته يحقق الستر والكثافة في حدث `جن`؛ فالمدار "
        "مباشر في هيئة الحديقة المحوطة المستورة.",
    ),
    (1757, "قبس"): (
        "ROOT-TRACE",
        "السطوع النجمي نور مأخوذ من أصل مضيء، والقبس تحصيل مباشر لمادة حادة من "
        "أصلها؛ فالمدار شعلة الضوء المقتبسة، والعلم الإلهي مفصول عن اسم الجنس.",
    ),
    (1807, "دب"): (
        "NUCLEUS-TRACE",
        "ثقل فرس النهر وحركته البطيئة يطابقان الثقل والضغط والدبيب في حدث `دب`؛ "
        "فالمدار مباشر في هيئة الحيوان وحركته.",
    ),
    (2147, "تف"): (
        "NUCLEUS-TRACE",
        "البصاق وسخ رطب يخرج إلى ظاهر الجلد أو الأرض، وحدث `تف` هو الوسخ على الجلد "
        "ونحوه؛ فالمدار مباشر في المادة المطرودة.",
    ),
    (2158, "شن"): (
        "NUCLEUS-TRACE",
        "النفس هواء دقيق ينتشر من الباطن إلى الخارج، وحدث `شن` انتشار الدقاق من "
        "أثناء الشيء؛ فالمدار مباشر في انتشار الزفير.",
    ),
    (2162, "موت"): (
        "ROOT-TRACE",
        "الانتقال إلى عالم الموت هو ذهاب الحياة وهمود الجسد، وهو نص حدث `موت`؛ "
        "فالمدار مباشر بلا واسطة.",
    ),
    (2187, "تم"): (
        "NUCLEUS-TRACE",
        "اكتمال الشيء يميزه وحدة مستقلة عما سواه، وحدث `تم` هو تميز الشيء مستقلًا؛ "
        "فالمدار حال التمام الناتجة.",
    ),
    (2189, "تمم"): (
        "ROOT-TRACE",
        "قول الفرع ينتهي ويكمل يطابق استيفاء جرم الشيء حجمه في حدث `تمم`؛ فالمدار "
        "مباشر في الإكمال.",
    ),
    (2203, "ختم"): (
        "ROOT-TRACE",
        "الإقفال والختم في الفرع هما إنهاء الشيء ومنع الزيادة عليه في حدث `ختم`؛ "
        "فالمدار مباشر.",
    ),
    (2238, "بيت"): (
        "ROOT-TRACE",
        "مسكن رع حيز محيط يستقر فيه ساكنه، وهو حدث `بيت` المجمّد؛ فالمدار مباشر "
        "في معنى المسكن، ولا يرثه معنى السماء على حدة.",
    ),
    (2249, "بيت"): (
        "ROOT-TRACE",
        "المسكن المذكور في معنى الفرع هو الحيز المحيط المستقر في حدث `بيت`؛ فالمدار "
        "مباشر، والياء باب المعتل المسمى لا صامت مصري محذوف.",
    ),
    (2306, "خر"): (
        "NUCLEUS-TRACE",
        "السقوط والنزول نتيجة تخلخل ما كان قائمًا وتسيب أجزائه، وهو حدث `خر`؛ "
        "فالمدار الأثر الناتج من التخلخل.",
    ),
    (2365, "زم"): (
        "NUCLEUS-TRACE",
        "الضم في الفرع هو جمع الكثير باكتناز في حدث `زم`؛ فالمدار مباشر.",
    ),
    (2468, "هد"): (
        "NUCLEUS-TRACE",
        "الضعف تضعضع القائم وتفككه، وهو حدث `هد` المجمّد؛ فالمدار مباشر في انهيار "
        "القوة.",
    ),
    (2470, "هت"): (
        "NUCLEUS-TRACE",
        "الهزيمة تفريق جمع الخصم وإنهاء تماسكه، وحدث `هت` دفع المتجمع إنهاء "
        "لتجمعه؛ فالمدار مباشر في نتيجة الدفع.",
    ),
    (2707, "تم"): (
        "NUCLEUS-TRACE",
        "وصف المعبود بالكامل يلتقي بتميز الشيء مستقلًا عند تمام حدّه في حدث `تم`؛ "
        "فالمدار حال الكمال، والبطاقة لعلم إلهي لا لمفردة معجمية عامة.",
    ),
}


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", str(value))


def selected_rows() -> list[dict[str, Any]]:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    source_rows = payload["rows"]
    out: list[dict[str, Any]] = []
    for book in BOOK_ORDER:
        if book == "khashim-gods1":
            rows = [
                row for row in source_rows
                if row.get("book") == book
                and row.get("tongue") in {"egyptian", "egyptian-greek", "egyptian-libyan"}
            ]
        elif book == "maqar-egyptian-colloquial":
            rows = [
                row for row in source_rows
                if row.get("book") == book and row.get("tongue") == "ancient-egyptian"
            ]
        else:
            rows = [row for row in source_rows if row.get("book") == book]
        if len(rows) != EXPECTED_BOOKS[book]:
            raise SystemExit(
                f"اختل جرد {book}: {len(rows)}، والمتوقع {EXPECTED_BOOKS[book]}"
            )
        out.extend(rows)
    if len(out) != EXPECTED:
        raise SystemExit(f"اختل الجرد الجامع: {len(out)}، والمتوقع {EXPECTED}")
    return out


def root_events() -> dict[str, str]:
    out: dict[str, str] = {}
    for line in ROOT_EVENTS_PATH.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        root = K.ar_bare(row.get("tri_root", ""))
        event = nfc(row.get("jabal_axial", "")).strip()
        if root and event:
            out[root] = event
    return out


ROOT_EVENTS = root_events()


def script_for(row: dict[str, Any]) -> tuple[str, str]:
    tongue = str(row.get("tongue", ""))
    word = str(row.get("foreign", ""))
    if tongue in {"egyptian", "ancient-egyptian", "egyptian-greek", "egyptian-libyan"}:
        return "egyptian", "رومنة مصرية أو وسم مختلط يبدأ بالمصرية"
    if tongue == "coptic" and any("Ⲁ" <= c <= "⳿" or "Ϣ" <= c <= "ϯ" for c in word):
        return "coptic", "رسم قبطي"
    if tongue == "greek" and any("Ͱ" <= c <= "Ͽ" for c in word):
        return "greek", "رسم يوناني"
    if tongue in {"akkadian"}:
        return "akkadian", "رومنة سامية"
    if tongue in {"hebrew", "syriac", "canaanite", "nabataean", "sabaic", "old_south_arabian"}:
        if any("֐" <= c <= "׿" for c in word):
            return "north", "رسم شمالي سامي"
        return "akkadian", "رومنة سامية محفوظة مع وسم اللسان"
    if tongue == "persian" and any("ء" <= c <= "ی" for c in word):
        return "persian", "رسم فارسي"
    return "latin", "رومنة لاتينية؛ لا تنسب الصف إلى المصرية"


def morphology(row: dict[str, Any], script: str) -> tuple[str, str, list[str]]:
    word = str(row.get("foreign", "")).strip()
    raw = K.FAN.skeleton(word, script)
    if script == "egyptian" and FEMININE.search(word):
        stem = word[:-2]
        return stem, "نزع تاء الاسم المؤنث المكتوبة `-t` أو `.t`", raw
    return word, "لا لاحقة مسماة في صف المصدر، فحُفظت الصوامت كلها", raw


def event_for(candidate: str) -> tuple[str | None, str | None]:
    if len(candidate) == 2 and candidate in K.NUCLEUS_EVENTS:
        return K.NUCLEUS_EVENTS[candidate], "data/juthoor-core-levels.json"
    if len(candidate) == 3 and candidate in ROOT_EVENTS:
        return ROOT_EVENTS[candidate], "computational/data/layer_2_results_v2.jsonl"
    return None, None


def sound_for(stem: str, candidate: str, script: str) -> tuple[bool, list[str], list[str]]:
    if script != "egyptian":
        return False, [], [
            "الصف من لسان غير مصري داخل كتاب الهيروغليفية؛ لم يُنسب إليه مسار مصري"
        ]
    return K.sound_audit(stem, candidate)


def is_name(row: dict[str, Any], ordinal: int) -> tuple[bool, str]:
    joined = " ".join(
        str(row.get(key, "")) for key in ("foreign_sense", "arabic_gloss")
    )
    if ordinal in {0, 2707} or NAME_RE.search(joined):
        return True, "عَلَم أو عنصر عَلَم بحسب معنى الصف؛ لا يعامل مفردة معجمية عامة"
    if row.get("book") == "khashim-gods1":
        return False, "مفردة في سياق كتاب الآلهة؛ لم يثبت من هذا الصف وحده أنها عَلَم"
    return False, "مفردة معجمية بحسب صف المصدر؛ لا عَلَم مصرحًا به"


def candidate_audits(
    row: dict[str, Any], ordinal: int, stem: str, script: str
) -> tuple[list[dict[str, Any]], str, int | None]:
    fan = K.FAN.fan(stem, script, limit=400)
    author = K.ar_bare(row.get("arabic_root", ""))
    candidates = list(fan)
    author_position: int | None = None
    if author:
        if author in candidates:
            author_position = candidates.index(author) + 1
        else:
            candidates.append(author)
    audits: list[dict[str, Any]] = []
    for position, candidate in enumerate(candidates, 1):
        sound_ready, sound_rows, sound_misses = sound_for(stem, candidate, script)
        event, event_source = event_for(candidate)
        orbit_spec = HUMAN_ORBITS.get((ordinal, candidate))
        audits.append({
            "candidate": candidate,
            "position": position if candidate in fan else None,
            "origin": "مروحة الأداة" if candidate in fan else "مرشح المؤلف خارج المروحة",
            "sound_ready": sound_ready,
            "sound_rows": sound_rows,
            "sound_misses": sound_misses,
            "event": event,
            "event_source": event_source,
            "branch_sense": row.get("foreign_sense", ""),
            "human_orbit": orbit_spec[1] if orbit_spec else None,
            "degree": orbit_spec[0] if orbit_spec else None,
            "positive": bool(orbit_spec and sound_ready and event),
            "state": "READY" if orbit_spec and sound_ready and event else "OPEN-CANDIDATE",
        })
    return audits, author, author_position


def compact_fan(values: list[str]) -> str:
    if not values:
        return "(لم تولد المروحة مرشحًا؛ بقي مرشح المؤلف محفوظًا)"
    return "، ".join(f"`{value}`" for value in values)


def render_card(row: dict[str, Any], ordinal: int, batch: int) -> tuple[str, dict[str, Any]]:
    script, script_note = script_for(row)
    stem, stripping, raw_skeleton = morphology(row, script)
    stem_skeleton = K.FAN.skeleton(stem, script)
    audits, author_root, author_position = candidate_audits(row, ordinal, stem, script)
    fan_values = [item["candidate"] for item in audits if item["origin"] == "مروحة الأداة"]
    positives = [item for item in audits if item["positive"]]
    if len(positives) > 1:
        raise SystemExit(f"تعددت الأحكام في الصف {ordinal} بلا بطاقة طبقة مستقلة")
    positive = positives[0] if positives else None
    focus = positive or next((x for x in audits if x["candidate"] == author_root), None)
    focus = focus or next((x for x in audits if x["event"]), None)
    focus = focus or (audits[0] if audits else None)
    is_proper, name_note = is_name(row, ordinal)
    closure = "READY" if positive else "OPEN-CANDIDATE"
    verdict = (
        f"**{positive['degree']} (استكشاف)**"
        if positive else "**غير صادر (استكشاف)**"
    )
    focus_root = focus["candidate"] if focus else "(لا مرشح قابل للرصف)"
    focus_event = focus.get("event") if focus else None
    focus_source = focus.get("event_source") if focus else None
    sound_rows = focus.get("sound_rows", []) if focus else []
    sound_misses = focus.get("sound_misses", []) if focus else []
    sound_text = "؛ ".join(sound_rows + sound_misses) or "لا رصف صوتي صادر"
    orbit = positive["human_orbit"] if positive else (
        "لم يُكتب مدار موجب لهذا العضو؛ الآلة عرضت المروحة ولم تحوّل المعنى إلى اختبار"
    )
    ready_candidates = [x for x in audits if x["event"] and x["sound_ready"]]
    eventless = sum(not x["event"] for x in audits)
    sound_open = sum(not x["sound_ready"] for x in audits)
    author_place = (
        f"الموضع {author_position} من {len(fan_values)}"
        if author_position else "خارج المروحة، فحُفظ ولم يحتكر الحكم"
    )
    required = "لا عائق معلق" if positive else (
        "مدار بشري مكتوب لمرشح تكتمل له رجل الصوت وحدث السجل؛ أو إبقاء المرشح مفتوحًا"
    )
    rid = f"extended-egyptian:{ordinal + 1:04d}"
    book = str(row["book"])
    lines = [
        f"### بطاقة: `{rid}`؛ `{row['foreign']}` «{row['foreign_sense']}»",
        f"<!-- EGYPTIAN-GODS-MAQAR:{ordinal + 1:04d} -->",
        "- إصدارُ البروتوكول: RECOVERY-v2؛ طبقةُ استكشاف.",
        f"- نسبةُ المصدر: {BOOK_LABELS[book]}، ص {row['page']}؛ حقل المصدر "
        f"`{row['source']}`. المرشح والشرح للمؤلف، والمروحة والمسار والحكم للمشروع.",
        f"- الكلمةُ في الفرع: `{row['foreign']}`؛ وسم اللسان في الحصاد "
        f"`{row['tongue']}` «{row['tongue_ar']}»؛ {script_note}.",
        f"- جردُ العَلَم: {name_note}.",
        "- أقدمُ صورةٍ مستعادة: لا تُدعى صورة أقدم من الرسم المنقول في الكتاب؛ "
        "رقم الصفحة هو سند هذه الجولة، وأي تأريخ أقدم يبقى سؤال مصدر.",
        f"- الخطوةُ صفر (التعرية بصرف الفرع): {stripping} ← اللب `{stem}`.",
        f"- حسابُ الصوامت: الخام `{' '.join(raw_skeleton) or '∅'}` = {len(raw_skeleton)}؛ "
        f"اللب `{' '.join(stem_skeleton) or '∅'}` = {len(stem_skeleton)}؛ لم يُسقط صامت أصلي بحدس.",
        "- درجةُ المقارنة: فُحص الجذر الكامل والنواة استقلالًا في عرض واحد؛ ولا "
        "تُستخرج نواة من ساق ذات صامت ثالث أصلي بلا تعرية منشورة.",
        f"- مروحةُ المرشحين من أداتنا: شُغّل `fan_any_script.py` بلسان `{script}`؛ "
        f"المرشحون ({len(fan_values)}): {compact_fan(fan_values)}.",
        f"- موضعُ مرشح المؤلف: `{author_root or '(غير مستخرج)'}`؛ {author_place}؛ "
        f"نص شرحه: «{row['arabic_gloss']}».",
        f"- مسحُ المعاني العربيّة: سجّل بيان الدفعة {len(audits)} مرشحًا عضويا؛ "
        f"منها {len(ready_candidates)} لها مسار وحدث معًا، و{eventless} بلا حدث مجمد، "
        f"و{sound_open} بقي صوتها مفتوحًا. عُرض حدث كل مرشح مع شرح المؤلف، ولم يمنح "
        "الفحص الآلي حكم معنى أو يختزل المروحة في المادة الأولى.",
        f"- المقابلُ من اللسان: `{focus_root}`؛ عرضه لا يمنحه احتكارًا، "
        "وسجل البيان يحفظ سائر المرشحين ونتيجة كل رجل.",
        f"- الحدثُ من السجل المجمد: «{focus_event}» [{focus_source}]"
        if focus_event else
        "- الحدثُ من السجل المجمد: لا حدث مجمد للمرشح المعروض؛ لذلك لا حكم موجب.",
        f"- مسارُ الصوت: {sound_text}. قبل إعلان أي صف ناقص فُتش كل موضع بالحرفين "
        "معًا وبألفاظ «المصرية» و«المصريّة» و`Egyptian` في عمود الشاهد.",
        f"- المعنى من قاموس الفرع: «{row['foreign_sense']}» بلا رتوش، وهو معنى "
        "الصف في المصدر الذي حدده نطاق الجولة "
        f"[{BOOK_LABELS[book]}، ص {row['page']}].",
        f"- المدار: {orbit}" + ("" if orbit.endswith(".") else "."),
        "- المصفاة: لا يسمّي صف الحصاد مانحًا خارجيًا ولا اتجاه قرض؛ غياب الاسم لا "
        "يثبت الوراثة، فيبقى الاتجاه مفتوحًا للجولة المقيسة.",
        "- فصلُ المتجانسات والاقتراض: الحكم، إن صدر، لهذا الصف ومعناه وحده؛ لا يرثه "
        "متحد الرسم ولا عنصر آخر من اسم مركب، ولا يرث العلم حكم مفردة عامة.",
        "- مؤشر اليتم: غير حاسم؛ لا يحمل صف الحصاد جرد أسرة الفرع، فلا يستعمل "
        "التفرد رفعًا أو إسقاطًا.",
        "- جسورُ الاسترداد المفحوصة: الجذر والنواة في عرض واحد؛ المروحة المصححة؛ "
        "مرشح المؤلف في موقعه؛ سجل الحدث؛ الشبكة بالحرفين وبأسماء اللسان؛ المعنى "
        "المنقول؛ العَلَم؛ القرض؛ المتجانسات.",
        f"- عائق: النوع={closure}؛ يتطلب={required}",
        f"- حالةُ الإغلاق: {closure}",
        f"- الحكم (استكشاف): {verdict}",
        f"- ملاحظات: عدسة الاسترداد حفظت جميع مرشحي المروحة ومرشح المؤلف؛ وعدسة "
        f"التشكيك {'أبقت وسم العَلَم خارج بسط التحقق مع إصدار حكم العنصر نفسه بالأرجل الثلاث' if positive and is_proper else 'أصدرت الحكم بعد اكتمال الأرجل الثلاث' if positive else 'منعت الحكم ولم تحول النقص إلى NO-TRACE'}.",
    ]
    summary = {
        "row_id": rid,
        "ordinal": ordinal + 1,
        "batch": batch,
        "book": book,
        "author": AUTHOR_LABELS[book],
        "page": row["page"],
        "tongue": row["tongue"],
        "foreign": row["foreign"],
        "foreign_sense": row["foreign_sense"],
        "author_root": author_root,
        "author_root_position": author_position,
        "arabic_gloss": row["arabic_gloss"],
        "proper_name": is_proper,
        "script": script,
        "raw_skeleton": raw_skeleton,
        "stem": stem,
        "stem_skeleton": stem_skeleton,
        "fan_count": len(fan_values),
        "candidates": audits,
        "closure": closure,
        "verdict": positive["degree"] if positive else None,
        "positive_root": positive["candidate"] if positive else None,
        "human_orbit": positive["human_orbit"] if positive else None,
    }
    return nfc("\n".join(lines)), summary


def marker(batch: int, side: str) -> str:
    return f"<!-- EGYPTIAN-GODS-MAQAR-BATCH-{batch:03d}:{side} -->"


def replace_batch(text: str, batch: int, block: str) -> str:
    start, end = marker(batch, "START"), marker(batch, "END")
    if start in text and end in text:
        before, rest = text.split(start, 1)
        _, after = rest.split(end, 1)
        return before.rstrip() + "\n\n" + block.rstrip() + "\n\n" + after.lstrip()
    return text.rstrip() + "\n\n" + block.rstrip() + "\n"


def report_path(batch: int) -> pathlib.Path:
    return ROOT / "data" / f"egyptian-gods-maqar-batch-{batch:03d}.json"


def write_audit(total_batches: int) -> None:
    reports = []
    for batch in range(1, total_batches + 1):
        path = report_path(batch)
        if path.exists():
            reports.append(json.loads(path.read_text(encoding="utf-8")))
    cards = [row for report in reports for row in report["rows"]]
    positives = [row for row in cards if row["verdict"]]
    opens = [row for row in cards if not row["verdict"]]
    by_book = Counter(row["book"] for row in cards)
    by_author = Counter(row["author"] for row in cards)
    proper = sum(bool(row["proper_name"]) for row in cards)
    complete = len(cards) == EXPECTED and len(reports) == total_batches
    lines = [
        "# مَحْضَرُ جَوْلَةِ المِصْرِيَّةِ: الآلِهَةُ وَمَقَّارٌ وَالهِيرُوغْلِيفِيَّةُ",
        "",
        "**التَّارِيخُ:** 2026-08-11.  ",
        "**الطَّبَقَةُ:** اِسْتِكْشَافٌ دَائِمًا.  ",
        "**الحَالَةُ:** " + ("اِكْتَمَلَ الجَرْدُ." if complete else "جَرْدٌ تَرَاكُمِيٌّ قَيْدَ التَّنْفِيذِ."),
        "",
        "## النِّطَاقُ وَالنِّسْبَةُ",
        "",
        "اِنْفَصَلَ مَصْدَرَا عَلِيٍّ فَهْمِي خُشَيْمٍ وَسَامِحٍ مَقَّارٍ فِي كُلِّ "
        "بِطَاقَةٍ وَفِي بَيَانِهَا. لَا يَرِثُ أَحَدُهُمَا حُكْمَ الآخَرِ، وَلَا يَرِثُ "
        "مُرَشَّحُ المُؤَلِّفِ حُكْمَ المَشْرُوعِ.",
        "",
        f"كُتِبَتْ حَتَّى الآنَ {len(cards)} بِطَاقَةً فِي {len(reports)} دُفْعَةٍ؛ "
        f"صَدَرَ مِنْهَا {len(positives)} حُكْمًا مُوجَبًا، وَبَقِيَ {len(opens)} "
        "`OPEN-CANDIDATE` بِحُجَجِهِ.",
        "",
        "| المَصْدَرُ | البِطَاقَاتُ المَكْتُوبَةُ |",
        "|---|---:|",
    ]
    for book in BOOK_ORDER:
        lines.append(f"| {BOOK_LABELS[book]} | {by_book[book]} |")
    lines.extend([
        "",
        "| المُؤَلِّفُ | البِطَاقَاتُ |",
        "|---|---:|",
    ])
    for author, count in sorted(by_author.items()):
        lines.append(f"| {author} | {count} |")
    lines.extend([
        "",
        "## مَا عُمِلَ فِي الأَعْلَامِ",
        "",
        f"وُسِمَ {proper} صَفًّا حَتَّى الآنَ بِأَنَّهُ عَلَمٌ أَوْ عُنْصُرُ عَلَمٍ. "
        "لَمْ يُمْنَعْ لِذَلِكَ مِنَ البِطَاقَةِ وَلَمْ يُعَامَلْ مُفْرَدَةً مَعْجَمِيَّةً "
        "عَامَّةً. يُحْكَمُ عُنْصُرُهُ إِنِ اكْتَمَلَتِ الأَرْجُلُ الثَّلَاثُ، وَيَبْقَى "
        "وَسْمُ العَلَمِ خَارِجَ بَسْطِ التَّحَقُّقِ المَقِيسِ.",
        "",
        "## عَدَسَتَا المُرَاجَعَةِ",
        "",
        "عَدَسَةُ الِاسْتِرْدَادِ حَفِظَتْ كُلَّ مُرَشَّحَاتِ المِرْوَحَةِ وَذَكَرَتْ "
        "مَوْقِعَ مُرَشَّحِ المُؤَلِّفِ وَلَوْ خَرَجَ مِنْهَا. وَعَدَسَةُ التَّشْكِيكِ "
        "مَنَعَتِ الحُكْمَ إِلَّا بِمَسَارٍ صَوْتِيٍّ مُسَمًّى، وَحَدَثٍ مِنَ السِّجِلِّ "
        "المُجَمَّدِ كَمَا هُوَ، وَمَعْنًى مَنْقُولٍ بِلَا رُتُوشٍ مَعَ مَدَارٍ مَكْتُوبٍ.",
        "",
        "## حَصِيلَةُ الدُّفَعِ",
        "",
        "| الدُّفْعَةُ | المَجَالُ | كُتِبَ | مُوجَبٌ | مَفْتُوحٌ |",
        "|---:|---|---:|---:|---:|",
    ])
    for report in reports:
        lines.append(
            f"| {report['batch']:03d} | {report['first_ordinal']:04d} إلى "
            f"{report['last_ordinal']:04d} | {report['cards_written']} | "
            f"{report['positive']} | {report['open_candidate']} |"
        )
    if complete:
        lines.extend([
            "",
            "## خَاتِمَةُ الجَرْدِ",
            "",
            "اِكْتَمَلَتِ البِطَاقَاتُ 2725/2725 بِلَا إِسْقَاطٍ. بَقِيَتْ طَبَقَةُ "
            "اِسْتِكْشَافٍ، وَبَقِيَ كُلُّ مَا لَمْ تَكْتَمِلْ لَهُ الأَرْجُلُ "
            "`OPEN-CANDIDATE`، وَلَمْ يُخْتَرَعْ وَسْمُ إِغْلَاقٍ جَدِيدٌ.",
        ])
    lines.extend([
        "",
        "---",
        "",
        "*English abstract.* This cumulative audit records the 2,725-card Egyptian "
        "exploration from Ali Fahmi Khushaim and Sameh Maqar as independent attributed "
        "sources. Every fan candidate is retained in the batch manifests. A positive "
        "verdict requires exactly the named sound path, the unchanged frozen event, and "
        "the branch meaning with a written semantic orbit. Proper names are carded and "
        "labelled, but their name status remains outside the measured verification numerator.",
        "",
    ])
    AUDIT.write_text(nfc("\n".join(lines)), encoding="utf-8", newline="\n")


def build_batch(batch: int) -> tuple[int, int, int]:
    rows = selected_rows()
    total_batches = (len(rows) + BATCH_SIZE - 1) // BATCH_SIZE
    if not 1 <= batch <= total_batches:
        raise SystemExit(f"رقم الدفعة {batch} خارج 1 إلى {total_batches}")
    start_index = (batch - 1) * BATCH_SIZE
    selected = rows[start_index:start_index + BATCH_SIZE]
    rendered: list[str] = []
    summaries: list[dict[str, Any]] = []
    for offset, row in enumerate(selected):
        card, summary = render_card(row, start_index + offset, batch)
        rendered.append(card)
        summaries.append(summary)
    positives = sum(bool(row["verdict"]) for row in summaries)
    opens = len(summaries) - positives
    by_book = Counter(row["book"] for row in summaries)
    block = [
        marker(batch, "START"),
        f"## الجولةُ المصريّةُ الكبرى، الدفعةُ {batch:03d}",
        "",
        f"**بيانُ النطاق.** الصفوف {start_index + 1:04d} إلى "
        f"{start_index + len(selected):04d} من الجرد الثابت ذي 2725 صفًّا، بترتيب "
        "خشيم في «آلهة مصر العربية»، ثم مقّار، ثم جميع صفوف «العرب والهيروغليفية».",
        "",
        "**قانونُ الحكم.** ثلاثة أرجل لا رابعة لها: مسار صوتي مسمى؛ والحدث من "
        "السجل المجمد كما هو؛ والمعنى من مصدر الفرع بلا رتوش مع مدار مكتوب. كل ما "
        "لم يستوف ذلك `OPEN-CANDIDATE` بحجته.",
        "",
        "**قانونُ المروحة.** فُحصت كل مرشحات المروحة، وسُجلت نتائجها العضوية في "
        f"`data/egyptian-gods-maqar-batch-{batch:03d}.json`. مرشح المؤلف مذكور "
        "بموقعه ولا يحتكر البحث.",
        "",
        "**الأعلام.** يكتب العَلَم وعنصر الاسم ولا يُمنع، لكنه يوسم بأنه ليس مفردة "
        "معجمية عامة، ويبقى خارج بسط التحقق المقيس.",
        "",
        f"**الحصيلة.** كُتبت {len(selected)} بطاقة؛ صدر {positives} حكمًا موجبًا، "
        f"وبقي {opens} `OPEN-CANDIDATE`.",
        "",
        *rendered,
        marker(batch, "END"),
    ]
    current = READING.read_text(encoding="utf-8")
    READING.write_text(
        nfc(replace_batch(current, batch, "\n".join(block))),
        encoding="utf-8",
        newline="\n",
    )
    report = {
        "generated_by": "scripts/build_egyptian_gods_maqar_cards.py",
        "source": "data/prior-art-extended-pairs.json",
        "layer": "استكشاف",
        "batch": batch,
        "batch_size": BATCH_SIZE,
        "total_batches": total_batches,
        "selected_total": len(rows),
        "first_ordinal": start_index + 1,
        "last_ordinal": start_index + len(selected),
        "cards_written": len(summaries),
        "positive": positives,
        "open_candidate": opens,
        "books": dict(sorted(by_book.items())),
        "rows": summaries,
    }
    report_path(batch).write_text(
        nfc(json.dumps(report, ensure_ascii=False, indent=1)),
        encoding="utf-8",
        newline="\n",
    )
    write_audit(total_batches)
    return len(selected), positives, opens


def check() -> int:
    rows = selected_rows()
    total_batches = (len(rows) + BATCH_SIZE - 1) // BATCH_SIZE
    bad = []
    all_ids: list[str] = []
    for batch in range(1, total_batches + 1):
        path = report_path(batch)
        if not path.exists():
            continue
        report = json.loads(path.read_text(encoding="utf-8"))
        if report["cards_written"] != len(report["rows"]):
            bad.append(f"اختل عدد صفوف البيان {batch}")
        for row in report["rows"]:
            all_ids.append(row["row_id"])
            if row["closure"] not in {"READY", "OPEN-CANDIDATE"}:
                bad.append(f"وسم إغلاق غير مشروع {row['row_id']}")
            if row["verdict"] and not row["human_orbit"]:
                bad.append(f"حكم موجب بلا مدار {row['row_id']}")
            if row["verdict"]:
                chosen = [c for c in row["candidates"] if c["positive"]]
                if len(chosen) != 1 or not chosen[0]["sound_ready"] or not chosen[0]["event"]:
                    bad.append(f"حكم موجب بلا الأرجل الثلاث {row['row_id']}")
    if len(all_ids) != len(set(all_ids)):
        bad.append("تكرر معرّف بطاقة بين البيانات")
    if bad:
        print("FAIL: " + "؛ ".join(bad[:12]))
        return 1
    print(
        f"CLEAN: الجرد الثابت {len(rows)}؛ البيانات المكتوبة {len(all_ids)}؛ "
        "قاموس الإغلاق READY/OPEN-CANDIDATE؛ لا موجب بلا مدار"
    )
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", type=int)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.check:
        return check()
    if not args.batch:
        raise SystemExit("سمّ رقم الدفعة: --batch N")
    written, positives, opens = build_batch(args.batch)
    print(
        f"الدفعة {args.batch:03d}: كُتب {written}؛ موجب {positives}؛ "
        f"OPEN-CANDIDATE {opens}"
    )
    print(f"كُتب: {report_path(args.batch).relative_to(ROOT).as_posix()}")
    print(f"كُتب: {AUDIT.relative_to(ROOT).as_posix()}")
    print(f"كُتب: {READING.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
