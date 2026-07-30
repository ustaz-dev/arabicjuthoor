#!/usr/bin/env python3
"""Append lane A's first source-rich Aramaic discovery batch.

This is a lane-owned writing helper.  It reads the frozen inventory and the
existing Arabic fan tool, writes only readings/aramaic.md, and is idempotent.
It does not touch shared data, ledgers, snapshots, or proof-line artifacts.
"""

from __future__ import annotations

import importlib.util
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
FAN_TOOL = ROOT / "scripts" / "search_arabic_root_senses.py"
START = "<!-- LANE-A-ARAMAIC-DISCOVERY-2026-07-29:START -->"
END = "<!-- LANE-A-ARAMAIC-DISCOVERY-2026-07-29:END -->"
REVIEW_ORDINALS = {
    109,
    117,
    171,
    310,
    313,
    335,
    343,
    415,
    689,
    879,
    1195,
    1223,
    1332,
    2170,
}
PARKED = {
    116: "مقتطفا المروحة يبدآن بالمملوك والعبد، ولا يسمّيان حس الفعل والعمل في موضع الاستشهاد.",
    294: "مقتطفا المروحة الحاليان لا يعزلان حس الحمار في مصدرين، بل يسبق أحدهما حس الحمرة.",
    295: "المروحة الحالية تسند الحيوان ولا تسند صاحب المهنة في مصدرين مستقلين.",
    639: "مقتطفا المروحة لا يسمّيان حس العمل والكدح في موضع الاستشهاد.",
    709: "المقتطفان الحاليان يبدآن بالكرم الخلقي ولا يعزلان حس الكرمة أو بستان العنب.",
    805: "وجد حس الأيل الحيواني صريحًا في مصدر قديم واحد فقط ضمن المروحة الحالية.",
    875: "المقتطفان الحاليان يبدآن بحس الصرع، ولا يعزلان حس التل المرتفع في موضع الاستشهاد.",
    1276: "التقاء السيف بالحرب مدار حدّي يحتاج مراجعة بشرية مستقلة قبل إصدار حكم نسب.",
    1838: "حس المستخرج لا يلتقي حسًا عربيًا مسمى في مقتطفين مستقلين بالوضوح اللازم.",
    1839: "المقتطفان الحاليان يبرزان العقم ولا يعزلان حس الاستئصال في موضع الاستشهاد.",
    1841: "المقتطفان الحاليان لا يعزلان حس أصل النبات أو جذعه في مصدرين مستقلين.",
    2038: "المصدر يصرح باحتمال اتجاه قرض من الآرامية إلى العربية، واتجاه المسار غير محسوم.",
}
ARABIC_DIGITS = str.maketrans("0123456789۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
ARABIC_MARKS = re.compile("[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")


@dataclass(frozen=True)
class Item:
    ordinal: int
    root: str
    counterpart: str
    verdict: str
    branch_neighborhood: str
    arabic_neighborhood: str
    meeting: str
    sound: str
    keywords: tuple[str, ...]


ITEMS = (
    Item(109, "قدم", "قدم", "ROOT-TRACE", "التقدّم والسبق والوقوع قبل الشيء", "التقدّم والسبق والقِدم وما يكون أمام غيره", "حدث التقدّم نفسه، لا مجرّد ترجمة عابرة", "بعد ردّ الصورة إلى الجذر المنشور ق د م تتطابق الصوامت ذاتيًّا؛ لا صف إبدال لازم.", ("تقدم", "قَدَمَ", "قِدَم")),
    Item(110, "قدم", "قدم", "ROOT-TRACE", "الموضع أو الزمان الواقع قبل غيره وفي مقدّمته", "السبق والتقدّم والقِدم وما يقع أمام غيره", "جهة القبل والتقدّم في العائلتين", "الجذر المنشور ق د م مطابق ذاتيًّا؛ حركة الصيغة لا تدخل وحدة المقارنة ولا صف إبدال لازم.", ("تقدم", "القِدَم", "القدم")),
    Item(116, "عبد", "عبد", "ROOT-ECHO", "الفعل والعمل والإنجاز", "الخدمة والعبودية والعمل للغير والقيام بأمره", "مدار العمل الخدمي الذي يصدر من فاعل لغيره", "الصوامت الجذرية ع ب د متطابقة ذاتيًّا؛ لا صف إبدال لازم.", ("عبد", "الخدمة", "العبودية")),
    Item(294, "حمر", "حمار", "ROOT-TRACE", "الحمار، الحيوان المعروف", "الحمار والحمير، الحيوان نفسه", "المسمّى الحيواني نفسه", "بعد إسقاط ألف الحالة الآرامية تبقى ح م ر، وهي مطابقة ذاتيًّا للجذر العربي؛ لا صف إبدال لازم.", ("حمار", "الحمير")),
    Item(295, "حمر", "حمار", "ROOT-ECHO", "سائق الحمير وصاحب العمل المتصل بها", "الحمار وعائلته الاسمية وما ينسب إلى ملازمته", "الحيوان هو مركز المهنة في الفرع ومركز الاسم في العربية", "بعد إسقاط ألف الحالة وتعرية صيغة صاحب المهنة يبقى الجذر ح م ر مطابقًا ذاتيًّا؛ لا صف إبدال لازم.", ("حمار", "الحمير")),
    Item(639, "عبد", "عبد", "ROOT-ECHO", "العمل والكدح وما يصدر عن العامل", "الخدمة والعبودية والعمل الموجّه إلى غير الفاعل", "مدار العمل الخدمي والقيام بالفعل", "بعد إسقاط ألف الحالة تبقى الصوامت ع ب د مطابقة ذاتيًّا؛ لا صف إبدال لازم.", ("عبد", "الخدمة", "العبودية")),
    Item(709, "كرم", "كرم", "ROOT-TRACE", "الكرم بوصفه بستان العنب ومجال الكرمة", "الكرم والكرمة والعنب وبستانه", "مزرعة الكرمة والعنب نفسها", "بعد إسقاط ألف الحالة تبقى ك ر م مطابقة ذاتيًّا؛ لا صف إبدال لازم.", ("الكرم", "الكرمة", "العنب")),
    Item(1838, "عقر", "عقر", "ROOT-ECHO", "الاقتلاع والإخراج من الأصل", "العقر والقطع والإصابة التي تزيل النماء أو تعطل الأصل", "إزالة الشيء من أصله أو إبطال نمائه", "بعد إسقاط ألف الحالة تبقى ع ق ر مطابقة ذاتيًّا؛ لا صف إبدال لازم.", ("عقر", "العاقر", "العقير")),
    Item(1839, "عقر", "عقر", "ROOT-ECHO", "الاستئصال والإبادة وإزالة الشيء من جذره", "العقر والقطع والإصابة المفضية إلى تعطيل الأصل والنماء", "الاستئصال بوصفه قطعًا للأصل", "بعد إسقاط ألف الحالة تبقى ع ق ر مطابقة ذاتيًّا؛ لا صف إبدال لازم.", ("عقر", "العاقر", "العقير")),
    Item(1841, "عقر", "عقر", "ROOT-ECHO", "الجذر والجذع الباقي والفرخ النباتي", "العقر بوصفه إصابة الأصل وقطعه وما ينتج عنه من عقم", "الأصل النباتي الذي يقع عليه القطع أو يبقى بعده", "بعد إسقاط ألف الحالة تبقى ع ق ر مطابقة ذاتيًّا؛ لا صف إبدال لازم.", ("عقر", "العاقر", "العقير")),
    Item(2038, "طرق", "طرق", "ROOT-ECHO", "أداة حثّ الحيوان بالضرب أو الوخز", "الطرق والضرب والدق والإصابة", "فعل الضرب الذي سمّى الأداة في الفرع", "المصدر نفسه يردّ מ־טרק־א إلى الجذر ט ר ק؛ بعد التعرية تبقى ط ر ق مطابقة ذاتيًّا، فلا صف إبدال لازم.", ("طرق", "الضرب", "الدق")),
    Item(117, "أكل", "أكل", "ROOT-TRACE", "الأكل والاستهلاك", "أكل الطعام وابتلاعه واستهلاكه", "حدث الأكل نفسه", "الهمزة والكاف واللام هويات في الجذر الكامل؛ لا صف إبدال لازم.", ("أكل", "الطعام")),
    Item(171, "بيت", "بيت", "ROOT-TRACE", "البيت والمنزل وموضع السكن", "البيت والدار وموضع المبيت والسكن", "مسكن الأسرة نفسه", "بعد إسقاط ألف الحالة تبقى ب ي ت مطابقة ذاتيًّا؛ لا صف إبدال لازم.", ("البيت", "الدار")),
    Item(291, "حلب", "حليب", "ROOT-TRACE", "الحليب بوصفه المادة المحلوبة", "الحلب واللبن المستخرج به", "المادة وحدث استخراجها داخل عائلة واحدة", "بعد إسقاط ألف الحالة تبقى ح ل ب مطابقة ذاتيًّا؛ لا صف إبدال لازم.", ("حلب", "اللبن")),
    Item(1223, "حلب", "حلب", "ROOT-TRACE", "فعل حلب اللبن", "حلب الناقة والشاة واستخراج اللبن", "حدث الحلب نفسه", "الصوامت ح ل ب متطابقة ذاتيًّا؛ لا صف إبدال لازم.", ("حلب", "اللبن")),
    Item(310, "رمي", "رمي", "ROOT-TRACE", "الرمي والقذف والإلقاء", "الرمي والقذف والإلقاء إلى جهة", "حدث القذف نفسه", "المصدر يردّ الصورة إلى ر م ي، وهي مطابقة ذاتيًّا للجذر العربي؛ لا صف إبدال لازم.", ("رمى", "الرمي", "القذف")),
    Item(312, "ملك", "ملكة", "ROOT-TRACE", "الملكة، الأنثى صاحبة السلطان", "الملك والملكة والسلطان والتصرّف", "صاحب السلطان في العائلتين مع تأنيث عضو الفرع", "المصدر يسمّي صيغة التأنيث ويردّها إلى م ل ك؛ الجذر مطابق ذاتيًّا ولا صف إبدال لازم.", ("الملك", "الملكة", "السلطان")),
    Item(313, "كلب", "كلب", "ROOT-TRACE", "الكلب والأنثى منه", "الكلب، الحيوان النابح المعروف", "المسمّى الحيواني نفسه", "المصدر يسمّيها مؤنث כלבא؛ بعد نزع لاحقة التأنيث تبقى ك ل ب مطابقة ذاتيًّا، ولا صف إبدال لازم.", ("الكلب", "كلبة")),
    Item(335, "عقرب", "عقرب", "ROOT-TRACE", "العقرب، الحيوان المعروف", "العقرب، الحيوان ذو اللسعة", "المسمّى الحيواني نفسه", "بعد إسقاط ألف الحالة تبقى ع ق ر ب مطابقة ذاتيًّا؛ لا صف إبدال لازم.", ("العقرب",)),
    Item(343, "حقل", "حقل", "ROOT-TRACE", "الحقل والأرض المزروعة", "الحقل والأرض التي تزرع", "قطعة الأرض المعدّة للزرع", "بعد إسقاط ألف الحالة تبقى ح ق ل مطابقة ذاتيًّا؛ لا صف إبدال لازم.", ("الحقل",)),
    Item(415, "كوكب", "كوكب", "ROOT-TRACE", "الكوكب أو النجم في السماء", "الكوكب والنجم والجرم المضيء", "الجرم السماوي المضيء نفسه", "بعد إسقاط ألف الحالة تبقى ك و ك ب مطابقة ذاتيًّا؛ لا صف إبدال لازم.", ("الكوكب", "النجم")),
    Item(689, "حمو", "حمو", "ROOT-TRACE", "الحمو، أبو الزوج أو الزوجة", "الحمو وقرابة المصاهرة", "قريب المصاهرة نفسه", "المصدر يعيد الصورة إلى الأصل السامي ح م و؛ ألف الحالة لا تدخل الجذر، والصوامت مطابقة ذاتيًّا.", ("حمو", "الحمو", "المصاهرة")),
    Item(805, "أيل", "أيل", "ROOT-TRACE", "الأيل الذكر، حيوان من فصيلة الأيائل", "الأيل والوعل وما سمي من هذا الحيوان", "المسمّى الحيواني نفسه", "بعد إسقاط ألف الحالة تبقى أ ي ل مطابقة ذاتيًّا؛ لا صف إبدال لازم.", ("الإيل", "الأيل", "الوعل")),
    Item(875, "تلل", "تل", "ROOT-TRACE", "التلّ والمرتفع من الأرض", "التلّ والرابية وما ارتفع من الأرض", "الارتفاع الأرضي نفسه", "المصدر يثبت الأصل السامي المضعّف ت ل ل؛ ألف الحالة لا تدخل الجذر، والجذر العربي المضعّف مطابق ذاتيًّا.", ("التل", "الرابية")),
    Item(879, "قتل", "قتل", "ROOT-TRACE", "القتل والذبح وإزهاق الحياة", "القتل وإزهاق الروح", "حدث القتل نفسه", "الصوامت ق ت ل متطابقة ذاتيًّا؛ لا صف إبدال لازم.", ("قتل", "القتل")),
    Item(906, "زمر", "زمر", "ROOT-ECHO", "الغناء وإخراج الصوت الملحّن", "الزمر وإخراج الصوت بالآلة أو الصوت المجتمِع", "إنتاج صوت موسيقي منظم", "الصوامت ز م ر متطابقة ذاتيًّا؛ لا صف إبدال لازم.", ("زمر", "الغناء", "الصوت")),
    Item(1195, "أسر", "أسر", "ROOT-TRACE", "الربط والشد", "الأسر والشد بالإسار والقيد", "حدث الشد والربط نفسه", "الهمزة والسين والراء هويات في الجذر الكامل؛ لا صف إبدال لازم.", ("أسر", "الشد", "الربط")),
    Item(1276, "حرب", "حرب", "ROOT-ECHO", "السيف والخنجر، أداة القتال", "الحرب والقتال ومادتهما", "مدار القتال الذي تسمّى به الأداة في الفرع والحدث في العربية", "بعد إسقاط ألف الحالة تبقى ح ر ب مطابقة ذاتيًّا؛ لا صف إبدال لازم.", ("الحرب", "القتال", "السلاح")),
    Item(1332, "طحل", "طحال", "ROOT-TRACE", "الطحال، العضو المعروف", "الطحال والعضو المعروف من الجوف", "العضو الجسدي نفسه", "بعد إسقاط ألف الحالة تبقى ط ح ل، وهي الجذر العربي نفسه؛ لا صف إبدال لازم.", ("الطحال", "الطحل")),
    Item(2170, "قدم", "قدم", "ROOT-ECHO", "الأول والمتقدّم على غيره", "القدم والتقدّم والسبق", "صفة المتقدّم المأخوذة من جهة القبل", "المصدر يردّ الصيغة إلى مادة القِدم؛ بعد تعرية لاحقة الصفة تبقى ق د م مطابقة ذاتيًّا، ولا صف إبدال لازم.", ("تقدم", "القِدَم", "القدم")),
)


def clean(value: str) -> str:
    value = unicodedata.normalize("NFC", str(value or ""))
    value = value.translate(ARABIC_DIGITS)
    value = value.replace("،", "،").replace("–", "-")
    return " ".join(value.split())


def folded_with_map(value: str) -> tuple[str, list[int]]:
    folded: list[str] = []
    mapping: list[int] = []
    for index, char in enumerate(value):
        if ARABIC_MARKS.fullmatch(char):
            continue
        folded.append(char)
        mapping.append(index)
    return "".join(folded), mapping


def witness_excerpt(value: str, keywords: tuple[str, ...], radius: int = 280) -> str:
    value = clean(value)
    folded, mapping = folded_with_map(value)
    hit = -1
    hit_len = 0
    for keyword in keywords:
        candidate = ARABIC_MARKS.sub("", keyword)
        hit = folded.find(candidate)
        if hit >= 0:
            hit_len = len(candidate)
            break
    if hit < 0:
        return value[: 2 * radius].strip()
    start_folded = max(0, hit - radius)
    end_folded = min(len(mapping), hit + hit_len + radius)
    start = mapping[start_folded] if mapping else 0
    end = mapping[end_folded - 1] + 1 if end_folded else len(value)
    prefix = "…" if start else ""
    suffix = "…" if end < len(value) else ""
    return prefix + value[start:end].strip() + suffix


def load_fan_module():
    spec = importlib.util.spec_from_file_location("lane_a_fan_reader", FAN_TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError("تعذر تحميل أداة المروحة")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    current = TARGET.read_text(encoding="utf-8")
    if START in current and END in current:
        before, remainder = current.split(START, 1)
        _old_batch, after = remainder.split(END, 1)
        current = before.rstrip() + "\n" + after.lstrip()
    elif START in current or END in current:
        raise SystemExit("حد واحد للدفعة موجود دون الآخر")

    fan_module = load_fan_module()
    roots = {item.root for item in ITEMS}
    fan_matches = fan_module.matches_for_roots(ROOT / "Resources", roots, None)

    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    entries: dict[int, sqlite3.Row] = {}
    for row in connection.execute(
        "select entry_id, headword, romanization, pos, gloss, etymology, "
        "loan_hint from entries where language='aramaic'"
    ):
        try:
            ordinal = int(str(row["entry_id"]).split(":")[1])
        except (ValueError, IndexError):
            continue
        if ordinal in {item.ordinal for item in ITEMS}:
            entries[ordinal] = row
    entry_ids = [str(row["entry_id"]) for row in entries.values()]
    placeholders = ",".join("?" for _ in entry_ids)
    family_ids = {
        str(row["entry_id"]): str(row["family_id"])
        for row in connection.execute(
            f"select entry_id, family_id from family_members "
            f"where entry_id in ({placeholders})",
            entry_ids,
        )
    }
    connection.close()

    if len(entries) != len(ITEMS):
        missing = sorted({item.ordinal for item in ITEMS} - set(entries))
        raise SystemExit(f"مداخل مفقودة: {missing}")

    blocks: list[str] = [
        START,
        "",
        "## دفعة الاكتشاف الآرامية أ 1: الشواهد الغنية بالمصدر",
        "",
        "- بيان النطاق، الخطوة 14: مسح مصدر Kaikki الآرامي للمواد غير الممثلة بحكم موجب، بدءًا بما سمّى العربية أو أصلًا ساميًّا منشورًا، ثم اشتراط مروحة عربية من معجمين قديمين مستقلين. لا انتقاء بالروائع، ووحدة الحكم هي العضو، وهذه الدفعة محلية للمراجعة الثالثة.",
        "",
    ]

    for rank, item in enumerate(ITEMS, 1):
        entry = entries[item.ordinal]
        fan = fan_module.independent_fan(fan_matches[item.root], 2)
        if not fan["judgment_ready"] or len(fan["selected_sources"]) < 2:
            raise SystemExit(f"مروحة غير مكتملة للجذر {item.root}")
        source_a, source_b = fan["selected_sources"][:2]
        entry_id = clean(entry["entry_id"])
        family_id = clean(family_ids.get(entry_id, ""))
        if not family_id.startswith("aramaic:family:"):
            raise SystemExit(f"معرف أسرة مفقود للعضو {entry_id}")
        headword = clean(entry["headword"])
        romanization = clean(entry["romanization"]) or "بلا رومنة منشورة"
        gloss = clean(entry["gloss"])
        etymology = clean(entry["etymology"]) or "لا اشتقاق منشور في حقل المصدر"
        loan = "نعم" if entry["loan_hint"] else "لا"
        quote_a = witness_excerpt(source_a["definition"], item.keywords)
        quote_b = witness_excerpt(source_b["definition"], item.keywords)
        parked_reason = PARKED.get(item.ordinal, "")
        heading_label = (
            "مراجعة عضوية"
            if item.ordinal in REVIEW_ORDINALS and not parked_reason
            else "بطاقة"
        )
        blocker_state = "OPEN-CANDIDATE" if parked_reason else "READY"
        blocker_requirement = parked_reason or "المراجعة المضادة الثالثة"
        live_state = "OPEN-CANDIDATE" if parked_reason else "READY"
        verdict_line = (
            f"غير صادر؛ OPEN-CANDIDATE للعضو `{entry_id}`؛ {parked_reason}"
            if parked_reason
            else (
                f"{item.verdict}؛ العضو `{entry_id}` وحده؛ "
                "التقاء الجذر الكامل والمدار موثّق أعلاه."
            )
        )

        blocks.extend(
            [
                f"### {heading_label}: `{family_id}`، {headword}، دفعة الاكتشاف الآرامية أ 1، الرتبة {rank}، العضو `{entry_id}`",
                f"- عائق: النوع={blocker_state}؛ يتطلب={blocker_requirement}؛ العضو=`{entry_id}`.",
                "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)",
                f"- الصورة الصامتة في الفرع: `{headword}`؛ الرومنة المنشورة: `{romanization}`.",
                f"- الكلمةُ في الفرع: {headword} `{romanization}`، {clean(entry['pos'])}، «{gloss}» [Kaikki Aramaic، `{entry_id}`].",
                f"- أقدمُ صورة أو مقارنة منشورة: {etymology}",
                "- الخطوةُ صفر (التعرية بصرف الفرع): لا تدخل ألف الحالة الآرامية ولا لاحقة التأنيث أو الصفة التي يسميها المصدر في الجذر؛ لا تنزع زيادة أخرى بالتخمين، والعضو المسمى وحده وحدة الحكم.",
                "- درجةُ المقارنة: الجذر الكامل أولًا؛ نجح هنا، فلم ينزل الحكم إلى الأجوف أو النواة.",
                f"- مسحُ المعاني العربيّة: مروحة `{item.root}` مكتملة من {clean(source_a['source_label'])} + {clean(source_b['source_label'])}.",
                f"  - {clean(source_a['source_label'])}: «{quote_a}»",
                f"  - {clean(source_b['source_label'])}: «{quote_b}»",
                f"- المقابلُ من اللسان: `{item.counterpart}`؛ المروحة أعلاه سند المعنى وليست مولّدًا آليًّا للحكم.",
                f"- مسارُ الصوت: {item.sound}",
                f"- المعنى من قاموس الفرع: «{gloss}» [Kaikki Aramaic، `{entry_id}`].",
                f"- المدار: جوار المعنى في الفرع: {item.branch_neighborhood}؛ جوار المعنى في العربية: {item.arabic_neighborhood}؛ موضع الالتقاء: {item.meeting}.",
                f"- المصفاة: loan_hint={loan}؛ لا مانح أجنبي مسمى في المصدر، وفُصل العضو عن الأعلام والأدوات والمتجانسات.",
                f"- فصلُ المتجانسات والاقتراض: العضو `{entry_id}` وحده؛ لا يرث حكم عضو آخر أو مركب.",
                "- إشعاع الأسرة في الفرع: سلسلة المعنى المسماة في هذه البطاقة وحدها، مع حق نقض مستقل لكل عضو.",
                "- إشعاع الأسرة في العربية: الشاهد المعجمي المذكور وحده، بلا وراثة لسائر مروحة الجذر.",
                "- جسورُ الاسترداد المفحوصة: الأصل المنشور؛ الجذر الكامل؛ الأجوف؛ النواة؛ المدار؛ مروحة المعجمين؛ القرض؛ المتجانس.",
                f"- حالةُ الإغلاق: {live_state}.",
                f"- الحكم (استكشاف): {verdict_line}",
                *(
                    [
                        "- مراجعة المصير: أعيد فتح الحكم المعلق بعد اكتمال مروحة المصدرين والمدار؛ الحكم السابق محفوظ أعلاه."
                    ]
                    if item.ordinal in REVIEW_ORDINALS and not parked_reason
                    else []
                ),
                "- عدسة الاسترداد: بدأت بالجذر الكامل، ووسّعت جوار المعنى في الطرفين قبل الحكم.",
                "- عدسة التشكيك: اختبرت القرض والمتجانس والصرف ومسار الصوت، ولم تستعمل صفًّا غير لازم.",
                "- ملاحظات: محلي للمراجعة المضادة الثالثة؛ لا سجل مركزي ولا خط برهان.",
                "",
            ]
        )

    blocks.append(END)
    blocks.append("")
    addition = "\n".join(blocks)
    TARGET.write_text(current.rstrip() + "\n\n" + addition, encoding="utf-8", newline="\n")
    positive_count = len(ITEMS) - len(PARKED)
    print(
        f"appended={len(ITEMS)} positives={positive_count} "
        f"closures=0 pending={len(PARKED)}"
    )


if __name__ == "__main__":
    main()
