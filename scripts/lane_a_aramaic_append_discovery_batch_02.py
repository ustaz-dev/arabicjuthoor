#!/usr/bin/env python3
"""Append twenty manually anchored Aramaic discovery cards for lane A.

Each Arabic witness and its semantic anchor is named in the specification
below.  String location is used only to copy the already chosen passage, never
to decide whether a semantic match exists.
"""

from __future__ import annotations

import importlib.util
import re
import sqlite3
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
FAN_TOOL = ROOT / "scripts" / "search_arabic_root_senses.py"
START = "<!-- LANE-A-ARAMAIC-DISCOVERY-2026-07-29-B02:START -->"
END = "<!-- LANE-A-ARAMAIC-DISCOVERY-2026-07-29-B02:END -->"
PARKED = {
    1277: "الفخذ والورك عضو تشريحي، لكن انتقال المدار منهما إلى العظم عام لا يثبت حسًا واحدًا بالضبط الكافي."
}
ARABIC_MARKS = re.compile("[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]")
ARABIC_DIGITS = str.maketrans("0123456789۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


@dataclass(frozen=True)
class Witness:
    source_id: str
    anchor: str
    human_reading: str


@dataclass(frozen=True)
class Item:
    ordinal: int
    root: str
    counterpart: str
    verdict: str
    degree: str
    sound: str
    branch_neighborhood: str
    arabic_neighborhood: str
    meeting: str
    witness_a: Witness
    witness_b: Witness


def w(source_id: str, anchor: str, human_reading: str) -> Witness:
    return Witness(source_id, anchor, human_reading)


ITEMS = (
    Item(560, "ثمر", "ثمر", "ROOT-ECHO", "الجذر الكامل", "ت ↔ ث على الصف الموقّع DENT-01؛ الميم والراء هويتان، وألف الحالة خارج الجذر.", "التمر، وهو ثمرة مخصوصة تؤكل", "الثمر ونتاج الشجر والفاكهة", "التمر فرد من جوار الثمر لا ترجمة منفصلة عنه", w("lisan", "الثمر", "يعرّف الثمر بما يحمله الشجر ويؤكل من نتاجه"), w("taj_al_arus", "الثمر", "يسمي الثمر ونتاج الشجر تسمية صريحة")),
    Item(607, "بصل", "بصل", "ROOT-TRACE", "الجذر الكامل", "بعد إسقاط ألف الحالة تبقى ب ص ل مطابقة ذاتيًّا؛ لا صف إبدال لازم.", "البصل، النبات المعروف", "البصل، النبات والبقلة المعروفة", "المسمّى النباتي نفسه", w("lisan", "البصل", "يسمي نبات البصل تعريفًا مباشرًا"), w("taj_al_arus", "البصل", "يثبت البصل بوصفه النبات المعروف")),
    Item(804, "ظبي", "ظبي", "ROOT-TRACE", "الجذر الكامل", "ט ↔ ظ على الصف الموقّع DENT-08 في مرساته المسماة ظبي؛ الباء والياء هويتان.", "الظبي أو الغزال", "الظبي، الحيوان المعروف من الغزلان", "المسمّى الحيواني نفسه", w("taj_al_arus", "الظبي", "يعرّف الظبي بالحيوان المعروف"), w("al_muhkam", "الظبي", "يسمي الظبي ويصف جنسه الحيواني")),
    Item(692, "حمم", "حمى", "NUCLEUS-TRACE", "النواة بعد فشل الجذر الكامل", "تاء التأنيث الآرامية والتضعيف العربي خارج النواة؛ النواة ح م مطابقة ذاتيًّا، ولا صف إبدال لازم.", "الحرارة والحمّى في الجسد", "الحمّى وحرارة الجسد واشتعالها", "الحالة الحرارية المرضية نفسها عند النواة ح م", w("lisan", "علة يستحر", "ينص على أن الحمى علة يستحر بها الجسم"), w("taj_al_arus", "علة يستحر", "يعرّف الحمى بأنها علة ذات حرارة مفرطة")),
    Item(923, "بني", "بنى", "ROOT-TRACE", "الجذر الكامل المستعاد في المصدر", "المصدر يثبت الأصل *b-n-y؛ ألف الرسم الآرامي تحمل الضعف النهائي، وب ن ي مطابق ذاتيًّا، بلا صف إبدال.", "البناء والإنشاء وإقامة الشيء", "بناء البيت والإنشاء والضم بعضه إلى بعض", "حدث الإنشاء والبناء نفسه", w("al_muhkam", "البناء المبني", "يفصل البناء المبني وصانع البنيان"), w("kitab_al_ayn", "البناء البناء", "يسند مادة بنى إلى البناء مباشرة")),
    Item(2006, "عمق", "عمق", "ROOT-TRACE", "الجذر الكامل المسمى في المقارنة المنشورة", "الواو في الرسم الآرامي حامل حركة في هذه الصورة؛ المصدر نفسه يقابل ع م ق بالعربية، والصوامت الجذرية هويات.", "العمق والبعد إلى الداخل", "العمق وما بعد قعره وبعد غوره", "صفة البعد الداخلي نفسها", w("lisan", "العمق", "يسمي العمق وبعد القعر"), w("taj_al_arus", "العمق", "يعرف العمق والغور تعريفًا مباشرًا")),
    Item(2059, "موت", "مات", "ROOT-TRACE", "درجة الجذر الأجوف", "و العربية ↔ ي الشمالية على GLD-01 في اتجاهه الموقّع؛ الجعزية ሞተ والمصرية mwt في المصدر ضابطان خارجيان غير شماليين غربيين.", "الموت وانتهاء الحياة", "الموت ومفارقة الحياة", "حدث الموت نفسه", w("al_sihah", "الموت", "يبدأ بتعريف الموت بأنه ضد الحياة"), w("lisan", "الموت والموتان", "ينص على أن الموت والموتان ضد الحياة")),
    Item(2149, "ليث", "ليث", "ROOT-TRACE", "الجذر الكامل", "ת المنطوقة ṯ ↔ ث على DENT-01؛ اللام والياء هويتان، وألف الحالة خارج الجذر.", "الليث، الأسد", "الليث، اسم الأسد", "المسمّى الحيواني نفسه", w("taj_al_arus", "الليث", "يصرح بأن الليث الأسد"), w("al_sihah", "الليث", "يسمي الليث من أسماء الأسد")),
    Item(626, "كهن", "كاهن", "ROOT-ECHO", "الجذر الكامل", "بعد إسقاط ألف الحالة تبقى ك ه ن مطابقة ذاتيًّا؛ ألف كاهن حركة طويلة لا صامت جذري، ولا صف إبدال لازم.", "الكاهن وصاحب الوظيفة الدينية", "الكاهن والعراف وصاحب الخبر الديني", "صاحب الوظيفة الدينية أو الغيبية في العائلتين", w("lisan", "الكاهن", "يعرّف الكاهن بصاحب الكهانة والخبر"), w("taj_al_arus", "الكاهن", "يسمي الكاهن ووظيفته صراحة")),
    Item(107, "نفح", "نفح", "ROOT-TRACE", "الجذر الكامل", "p الآرامية ↔ ف العربية على LAB-07؛ النون والحاء هويتان.", "النفخ وإخراج النفس والهواء", "نفح الريح وهبوبها وخروج الرائحة أو النفس", "حركة الهواء الخارجة نفسها", w("lisan", "نفحت", "يسمي نفح الريح وهبوبها"), w("taj_al_arus", "نفحت", "يثبت فعل النفح للريح والهواء")),
    Item(216, "ألف", "ألف", "ROOT-TRACE", "الجذر الكامل", "p الآرامية ↔ ف العربية على LAB-07؛ الهمزة واللام هويتان، وألف الحالة خارج الجذر.", "العدد ألف", "الألف، العدد المعروف بعد تسع مئة وتسعة وتسعين", "القيمة العددية نفسها", w("lisan", "الألف", "يعرف الألف بوصفه العدد المعروف"), w("taj_al_arus", "الألف", "يسمي الألف وقيمته العددية")),
    Item(269, "ثلث", "ثلاثة", "ROOT-TRACE", "الجذر الكامل", "ת ↔ ث في الموضعين على DENT-01؛ اللام هوية، وألف الحالة خارج الجذر.", "العدد ثلاثة", "الثلاثة والثلث من عائلة العدد نفسها", "القيمة العددية ثلاثة نفسها", w("lisan", "الثلاثة", "يسمي العدد ثلاثة ومشتقاته"), w("taj_al_arus", "الثلاثة", "يثبت القيمة العددية ثلاثة")),
    Item(2072, "ثلث", "ثلاثة", "ROOT-TRACE", "الجذر الكامل", "𐡕 المنطوقة ṯ ↔ ث على DENT-01 في الموضعين؛ اللام هوية.", "العدد ثلاثة في الرسم الآرامي القديم", "الثلاثة والثلث من عائلة العدد نفسها", "القيمة العددية ثلاثة نفسها", w("lisan", "الثلاثة", "يسمي العدد ثلاثة ومشتقاته"), w("taj_al_arus", "الثلاثة", "يثبت القيمة العددية ثلاثة")),
    Item(270, "ربع", "أربعة", "ROOT-TRACE", "الجذر الكامل", "بعد إسقاط ألف الحالة تبقى أ ر ب ع مطابقة ذاتيًّا؛ لا صف إبدال لازم.", "العدد أربعة", "الأربعة والربع من عائلة العدد نفسها", "القيمة العددية أربعة نفسها", w("lisan", "الأربعة", "يسمي العدد أربعة ومشتقاته"), w("taj_al_arus", "الأربعة", "يثبت القيمة العددية أربعة")),
    Item(275, "ثمن", "ثمانية", "ROOT-TRACE", "الجذر الكامل", "ת ↔ ث في أول الجذر على DENT-01؛ الميم والنون هويتان، وياء الصيغة العددية ليست صامتًا جذريًّا.", "العدد ثمانية", "الثمانية والثمن من عائلة العدد نفسها", "القيمة العددية ثمانية نفسها", w("lisan", "الثمانية", "يسمي العدد ثمانية ومشتقاته"), w("taj_al_arus", "الثمانية", "يثبت القيمة العددية ثمانية")),
    Item(1277, "عظم", "عظم", "ROOT-ECHO", "الجذر الكامل المستعاد في المصدر", "ṯ̣ الآرامية ↔ ظ العربية على DENT-08 في مرساة عظم الموقّعة؛ العين والميم هويتان.", "الفخذ والورك، موضع العظم الكبير", "العظم، قوام البدن الصلب", "العضو التشريحي في الفرع يلتقي مادته العظمية في العربية", w("lisan", "العظم", "يعرّف العظم بوصفه قوام الجسد الصلب"), w("taj_al_arus", "العظم", "يسمي العظم وموضعه من البدن")),
    Item(1052, "ثور", "ثور", "ROOT-TRACE", "الجذر الكامل", "ת ↔ ث على DENT-01؛ الواو والراء هويتان.", "الثور أو البقر الذكر", "الثور، ذكر البقر", "المسمّى الحيواني نفسه", w("al_sihah", "الثور الذكر من البقر", "ينص حرفيًّا على أن الثور ذكر البقر"), w("al_muhkam", "الثور الذكر من البقر", "يكرر تعريف الثور بذكر البقر")),
    Item(1099, "كفف", "كف", "ROOT-TRACE", "الجذر الكامل المضعّف المستعاد", "p الآرامية ↔ ف العربية على LAB-07؛ الكاف هوية، والتضعيف محفوظ في الأصل *kapp- والجذر ك ف ف.", "راحة اليد والكف", "الكف، راحة اليد وما تقبض به", "جزء اليد نفسه", w("lisan", "الكف", "يعرف الكف براحة اليد"), w("taj_al_arus", "الكف", "يسمي الكف وجانب اليد")),
    Item(1647, "طحن", "طحن", "ROOT-TRACE", "الجذر الكامل", "الطاء والحاء والنون هويات في الجذر الكامل؛ لا صف إبدال لازم.", "الطحن والدق حتى يصير الشيء دقيقًا", "الطحن والدق وإصارة الحب دقيقًا", "حدث الطحن نفسه", w("lisan", "الطحن", "يعرّف الطحن بالدق وصنع الدقيق"), w("taj_al_arus", "الطحن", "يسمي الطحن وإدارة الرحى")),
    Item(2024, "صبع", "إصبع", "ROOT-TRACE", "الجذر الكامل", "الهمزة والصاد والباء والعين هويات؛ ألف الحالة خارج الجذر ولا صف إبدال لازم.", "الإصبع من اليد أو الرجل", "الإصبع، العضو المعروف من اليد أو الرجل", "العضو الجسدي نفسه", w("lisan", "الإصبع", "يعرف الإصبع بالعضو المعروف"), w("taj_al_arus", "الإصبع", "يسمي الإصبع وموضعه من اليد")),
)


def clean(value: str) -> str:
    value = unicodedata.normalize("NFC", str(value or ""))
    value = value.translate(ARABIC_DIGITS)
    return " ".join(value.replace("،", "،").replace("–", "-").split())


def folded_with_map(value: str) -> tuple[str, list[int]]:
    folded: list[str] = []
    mapping: list[int] = []
    for index, char in enumerate(value):
        if ARABIC_MARKS.fullmatch(char):
            continue
        folded.append(char)
        mapping.append(index)
    return "".join(folded), mapping


def extract_chosen_passage(value: str, anchor: str, radius: int = 320) -> str:
    value = clean(value)
    folded, mapping = folded_with_map(value)
    anchor_folded = ARABIC_MARKS.sub("", anchor)
    position = folded.find(anchor_folded)
    if position < 0:
        raise ValueError(f"المرساة المختارة غير موجودة: {anchor}")
    start_folded = max(0, position - radius)
    end_folded = min(len(mapping), position + len(anchor_folded) + radius)
    start = mapping[start_folded]
    end = mapping[end_folded - 1] + 1
    return (
        ("…" if start else "")
        + value[start:end].strip()
        + ("…" if end < len(value) else "")
    )


def load_fan_module():
    spec = importlib.util.spec_from_file_location("lane_a_fan_reader_b02", FAN_TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError("تعذر تحميل أداة المروحة")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def chosen_witness(module, matches: list[dict], witness: Witness) -> dict:
    for item in matches:
        if module.canonical_source_id(str(item.get("source") or "")) != witness.source_id:
            continue
        try:
            excerpt = extract_chosen_passage(str(item["definition"]), witness.anchor)
        except ValueError:
            continue
        return {
            "source_label": module.SOURCE_LABELS[witness.source_id],
            "excerpt": excerpt,
            "human_reading": witness.human_reading,
        }
    raise ValueError(
        f"لم توجد المرساة {witness.anchor} في المصدر {witness.source_id}"
    )


def main() -> None:
    current = TARGET.read_text(encoding="utf-8")
    if START in current and END in current:
        before, remainder = current.split(START, 1)
        _old, after = remainder.split(END, 1)
        current = before.rstrip() + "\n" + after.lstrip()
    elif START in current or END in current:
        raise SystemExit("حد واحد للدفعة الثانية موجود دون الآخر")

    fan_module = load_fan_module()
    matches = fan_module.matches_for_roots(
        ROOT / "Resources", {item.root for item in ITEMS}, None
    )

    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    wanted = {item.ordinal for item in ITEMS}
    entries = {}
    for row in connection.execute(
        "select entry_id, headword, romanization, pos, gloss, etymology, "
        "loan_hint from entries where language='aramaic'"
    ):
        ordinal = int(str(row["entry_id"]).split(":")[1])
        if ordinal in wanted:
            entries[ordinal] = row
    entry_ids = [str(row["entry_id"]) for row in entries.values()]
    placeholders = ",".join("?" for _ in entry_ids)
    families = {
        str(row["entry_id"]): str(row["family_id"])
        for row in connection.execute(
            f"select entry_id, family_id from family_members "
            f"where entry_id in ({placeholders})",
            entry_ids,
        )
    }
    connection.close()
    if len(entries) != len(ITEMS) or len(families) != len(ITEMS):
        raise SystemExit("تعذر تعيين كل المداخل أو الأسر في الدفعة الثانية")

    blocks = [
        START,
        "",
        "## دفعة الاكتشاف الآرامية أ 2: عشرون مرساة دلالية بشرية",
        "",
        "- بيان النطاق، الخطوة 14: عشرون عضوًا تاليًا من الجرد الغني بالمصدر، اختير لكل واحد منهما شاهدان قديمان بعد قراءة الحس المقصود يدويًّا. موضع السلسلة في النص يستخرج المقتطف فقط، ولا يصدر الحكم من مطابقة محارف.",
        "",
    ]
    for rank, item in enumerate(ITEMS, 1):
        entry = entries[item.ordinal]
        entry_id = clean(entry["entry_id"])
        family_id = clean(families[entry_id])
        witness_a = chosen_witness(fan_module, matches[item.root], item.witness_a)
        witness_b = chosen_witness(fan_module, matches[item.root], item.witness_b)
        headword = clean(entry["headword"])
        romanization = clean(entry["romanization"]) or "بلا رومنة منشورة"
        gloss = clean(entry["gloss"])
        etymology = clean(entry["etymology"]) or "لا حقل اشتقاق مستقل"
        loan = "نعم" if entry["loan_hint"] else "لا"
        parked_reason = PARKED.get(item.ordinal, "")
        blocker_state = "OPEN-CANDIDATE" if parked_reason else "READY"
        blocker_requirement = parked_reason or "المراجعة المضادة الثالثة"
        live_state = "OPEN-CANDIDATE" if parked_reason else "READY"
        verdict_line = (
            f"غير صادر؛ OPEN-CANDIDATE للعضو `{entry_id}`؛ {parked_reason}"
            if parked_reason
            else (
                f"{item.verdict}؛ العضو `{entry_id}` وحده؛ "
                "التقاء الدرجة والمدار مسند أعلاه."
            )
        )
        heading_label = "بطاقة" if parked_reason else "مراجعة عضوية"
        blocks.extend(
            [
                f"### {heading_label}: `{family_id}`، {headword}، دفعة الاكتشاف الآرامية أ 2، الرتبة {rank}، العضو `{entry_id}`",
                f"- عائق: النوع={blocker_state}؛ يتطلب={blocker_requirement}؛ العضو=`{entry_id}`.",
                "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)",
                f"- الصورة الصامتة في الفرع: `{headword}`؛ الرومنة المنشورة: `{romanization}`.",
                f"- الكلمةُ في الفرع: {headword} `{romanization}`، {clean(entry['pos'])}، «{gloss}» [Kaikki Aramaic، `{entry_id}`].",
                f"- أقدمُ صورة أو مقارنة منشورة: {etymology}",
                "- الخطوةُ صفر (التعرية بصرف الفرع): لا تدخل ألف الحالة ولا اللاحقة التي يسميها المصدر في الجذر؛ لا تنزع زيادة بالتخمين، والعضو المسمى وحده وحدة الحكم.",
                f"- درجةُ المقارنة: {item.degree}؛ لم يقفز الحكم فوق الدرجة الناجحة.",
                f"- مسحُ المعاني العربيّة: مروحة `{item.root}` قُرئت كاملة، واختير الحس يدويًّا في مصدرين قديمين مستقلين.",
                f"  - {clean(witness_a['source_label'])}: «{clean(witness_a['excerpt'])}»",
                f"  - المرساة الدلالية البشرية في المصدر الأول: {item.witness_a.human_reading}.",
                f"  - {clean(witness_b['source_label'])}: «{clean(witness_b['excerpt'])}»",
                f"  - المرساة الدلالية البشرية في المصدر الثاني: {item.witness_b.human_reading}.",
                f"- المقابلُ من اللسان: `{item.counterpart}`؛ الشاهدان يسندان الحس ولا يولدان الحكم آليًّا.",
                f"- مسارُ الصوت: {item.sound}",
                f"- المعنى من قاموس الفرع: «{gloss}» [Kaikki Aramaic، `{entry_id}`].",
                f"- المدار: جوار المعنى في الفرع: {item.branch_neighborhood}؛ جوار المعنى في العربية: {item.arabic_neighborhood}؛ موضع الالتقاء: {item.meeting}.",
                f"- المصفاة: loan_hint={loan}؛ لا مانح أجنبي مسمى في المصدر، وفُصل العضو عن الأعلام والأدوات والمتجانسات.",
                f"- فصلُ المتجانسات والاقتراض: العضو `{entry_id}` وحده؛ لا يرث حكم عضو آخر أو مركب.",
                "- إشعاع الأسرة في الفرع: سلسلة المعنى المسماة وحدها، ولكل عضو حق نقض.",
                "- إشعاع الأسرة في العربية: الحس المستشهد به وحده، بلا وراثة لسائر المروحة.",
                "- جسورُ الاسترداد المفحوصة: الأصل المنشور؛ الجذر؛ الأجوف؛ النواة؛ المدار؛ الشاهدان؛ القرض؛ المتجانس.",
                f"- حالةُ الإغلاق: {live_state}.",
                f"- الحكم (استكشاف): {verdict_line}",
                *(
                    [
                        "- مراجعة المصير: فُحص العضو منفردًا بمروحة المصدرين والمدار؛ الحكم السابق، إن وجد، محفوظ أعلاه."
                    ]
                    if not parked_reason
                    else []
                ),
                "- عدسة الاسترداد: بدأت بالجذر الكامل ثم نزلت فقط حيث سمّى المصدر الضعف أو النواة.",
                "- عدسة التشكيك: اختبرت الصرف والقرض والمتجانس والصفوف اللازمة وحدها.",
                "- ملاحظات: محلي للمراجعة المضادة الثالثة؛ لا سجل مركزي ولا خط برهان.",
                "",
            ]
        )
    blocks.extend([END, ""])
    TARGET.write_text(
        current.rstrip() + "\n\n" + "\n".join(blocks),
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"appended=20 positives={len(ITEMS) - len(PARKED)} "
        f"closures=0 pending={len(PARKED)}"
    )


if __name__ == "__main__":
    main()
