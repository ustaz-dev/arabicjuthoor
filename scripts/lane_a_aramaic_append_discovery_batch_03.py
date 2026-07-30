#!/usr/bin/env python3
"""Append lane A Aramaic discovery batch 03 with manual sense anchors."""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
COMMON_PATH = ROOT / "scripts" / "lane_a_aramaic_append_discovery_batch_02.py"
START = "<!-- LANE-A-ARAMAIC-DISCOVERY-2026-07-29-B03:START -->"
END = "<!-- LANE-A-ARAMAIC-DISCOVERY-2026-07-29-B03:END -->"
BATCH_NO = "3"
BATCH_TITLE = "عشرون حسًا مباشرًا"
BATCH_SCOPE = "أعضاء من الجرد المرخص ذي التطابق الجذري أو الطي المثبت، مع شاهدين قديمين اختير حسهما يدويًّا. لا يستعمل تطابق السلسلة لإصدار الحكم."
PARKED = {
    230: "الشاهدان يسمّيان الجمال في عائلة جمل، لكنهما لا يصرحان بحس صاحب الإبل أو سائقها.",
    704: "الشاهدان يثبتان حدث الحلم، لا اسم الفاعل بمعنى صاحب الرؤيا؛ والحالم في المداخل القديمة يلتبس بذي الحلم والأناة.",
}


def load_common():
    spec = importlib.util.spec_from_file_location("lane_a_aramaic_b02_common", COMMON_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("تعذر تحميل مساعد المسار أ")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


C = load_common()
W = C.Witness
I = C.Item


def w(source_id: str, anchor: str, human_reading: str) -> W:
    return W(source_id, anchor, human_reading)


ITEMS = (
    I(638, "عبد", "عبد", "ROOT-TRACE", "الجذر الكامل", "الصوامت ع ب د متطابقة ذاتيًّا؛ ألف الحالة خارج الجذر ولا صف إبدال لازم.", "الخادم أو العبد", "العبد المملوك خلاف الحر", "الشخص الخاضع للخدمة نفسه", w("lisan", "المملوك", "ينص على أن العبد المملوك خلاف الحر"), w("taj_al_arus", "المملوك", "يكرر تعريف العبد بالمملوك")),
    I(8, "عبر", "عبر", "ROOT-TRACE", "الجذر الكامل", "العين والباء والراء هويات؛ لا صف إبدال لازم.", "المرور والعبور من جانب إلى جانب", "قطع النهر أو الطريق من عبر إلى عبر", "حدث الاجتياز نفسه", w("al_muhkam", "عبر السبيل", "يسند العبور إلى شق السبيل واجتيازه"), w("lisan", "عبرت النهر والطريق", "ينص على قطع النهر والطريق من جانب إلى جانب")),
    I(993, "بزز", "بز", "ROOT-TRACE", "الجذر الكامل المضعّف", "الباء والزاي المضعّفة هويات؛ لا صف إبدال لازم.", "السلب والنهب وأخذ المال", "البز والسلب والانتزاع بالقهر", "حدث السلب نفسه", w("lisan", "السلب", "يعرّف البز بالسلب والغلبة"), w("taj_al_arus", "السلب", "يسمي البز نزعًا وسلبًا")),
    I(1837, "عقر", "عاقر", "ROOT-TRACE", "الجذر الكامل", "بعد إسقاط ألف الحالة تبقى ع ق ر مطابقة ذاتيًّا؛ لا صف إبدال لازم.", "العقم وعدم القدرة على الإنجاب", "العاقر التي انقطع حملها", "حالة العقم نفسها", w("lisan", "وهي عاقر", "ينص على المرأة التي لا تحمل وأنها عاقر"), w("taj_al_arus", "وهي عاقر", "يثبت انقطاع الحمل في وصف العاقر")),
    I(196, "عين", "عين", "ROOT-TRACE", "الجذر الكامل", "بعد إسقاط ألف الحالة تبقى ع ي ن مطابقة ذاتيًّا؛ لا صف إبدال لازم.", "العين وحاسة البصر", "العين حاسة الرؤية والبصر", "عضو الإبصار نفسه", w("al_sihah", "حاسة الرؤية", "يعرف العين بحاسة الرؤية"), w("al_muhkam", "حاسة البصر", "يعرف العين بحاسة البصر")),
    I(197, "عين", "عين", "ROOT-TRACE", "الجذر الكامل", "بعد إسقاط ألف الحالة تبقى ع ي ن مطابقة ذاتيًّا؛ لا صف إبدال لازم.", "عين الماء والنبع", "عين الماء ومفجر ماء الركية", "منبع الماء نفسه", w("al_sihah", "عين الماء", "يسمي عين الماء صراحة"), w("al_muhkam", "عين الماء", "يعرف عين الماء ومفجرها")),
    I(1787, "بعل", "بعل", "ROOT-TRACE", "الجذر الكامل", "بعد إسقاط ألف الحالة تبقى ب ع ل مطابقة ذاتيًّا؛ لا صف إبدال لازم.", "السيد والرب والمالك", "البعل رب الشيء وصاحبه", "صاحب السلطان والملكية نفسه", w("al_sihah", "ربها وصاحبها", "يفسر بعل الناقة بربها وصاحبها"), w("lisan", "ربها وصاحبها", "يسند إلى البعل معنى الرب والصاحب")),
    I(1628, "بلع", "بلع", "ROOT-TRACE", "الجذر الكامل", "الباء واللام والعين هويات؛ لا صف إبدال لازم.", "ابتلاع الطعام أو الشراب", "بلع الشيء وجرعه وابتلعه", "حدث الابتلاع نفسه", w("lisan", "بلع الشيء", "يعرف البلع بجرع الشيء وابتلاعه"), w("taj_al_arus", "بلعه", "يسند البلع إلى الجرع والابتلاع")),
    I(1629, "بلع", "بلع", "ROOT-TRACE", "الجذر الكامل", "بعد إسقاط ألف الحالة تبقى ب ل ع مطابقة ذاتيًّا؛ لا صف إبدال لازم.", "البلع بوصفه حدثًا أو مصدرًا", "البلع والابتلاع والجرع", "مصدر الحدث نفسه", w("al_sihah", "بلعت", "يسند الفعل بلع إلى ابتلاع الشيء"), w("al_muhkam", "بلع الشيء", "يعرف المصدر بفعل الجرع والابتلاع")),
    I(1428, "دمع", "دمع", "ROOT-TRACE", "الجذر الكامل", "الدال والميم والعين هويات؛ لا صف إبدال لازم.", "البكاء وسيلان الدمع", "الدمع ماء العين وسيلانه", "سائل العين وحدث خروجه نفسه", w("lisan", "الدمع", "يعرف الدمع بماء العين"), w("taj_al_arus", "الدمع", "ينص على أن الدمع ماء العين")),
    I(285, "ملح", "ملح", "ROOT-TRACE", "الجذر الكامل", "بعد إسقاط ألف الحالة تبقى م ل ح مطابقة ذاتيًّا؛ لا صف إبدال لازم.", "الملح، المادة المعروفة", "الملح والطعم المالح والمادة المعروفة", "المادة نفسها", w("lisan", "الملح", "يعرف الملح بالمادة المعروفة"), w("taj_al_arus", "الملح", "يسمي الملح وطعمه")),
    I(477, "جلد", "جلد", "ROOT-TRACE", "الجذر الكامل", "g الآرامية ↔ ج العربية في طي التطبيع المثبت؛ اللام والدال هويتان ولا صف إضافي.", "الجلد وغطاء البدن", "الجلد، مسك الحيوان وغطاء بدنه", "غطاء البدن نفسه", w("lisan", "الجلد والجلد", "يعرف الجلد بمسك الحيوان"), w("taj_al_arus", "الجلد", "يسمي الجلد وواحد الجلود")),
    I(229, "جمل", "جمل", "ROOT-TRACE", "الجذر الكامل", "g الآرامية ↔ ج العربية في طي التطبيع المثبت؛ الميم واللام هويتان.", "الجمل، ذكر الإبل", "الجمل، الذكر من الإبل", "المسمّى الحيواني نفسه", w("lisan", "الجمل", "يعرف الجمل بذكر الإبل"), w("taj_al_arus", "ذكر الإبل", "ينص على أن الجمل ذكر الإبل")),
    I(230, "جمل", "جمال", "ROOT-TRACE", "الجذر الكامل", "g الآرامية ↔ ج العربية في طي التطبيع المثبت؛ الميم واللام هويتان، والتضعيف صرف المهنة.", "الجمال، سائق الجمال وصاحبها", "الجمال وصاحب الإبل وراعيها", "صاحب المهنة المتصلة بالجمل نفسه", w("lisan", "الجمال", "يسمي الجمال في عائلة الجمل"), w("taj_al_arus", "الجمال", "يثبت صيغة الجمال المتصلة بالإبل")),
    I(703, "حلم", "حلم", "ROOT-TRACE", "الجذر الكامل", "بعد إسقاط ألف الحالة تبقى ح ل م مطابقة ذاتيًّا؛ لا صف إبدال لازم.", "الحلم أو الرؤيا في النوم", "الحلم، الرؤيا التي يراها النائم", "خبر النوم نفسه", w("lisan", "الرؤيا", "يعرف الحلم بالرؤيا"), w("taj_al_arus", "الرؤيا", "ينص على أن الحلم ما يراه النائم")),
    I(704, "حلم", "حالم", "ROOT-ECHO", "الجذر الكامل", "بعد إسقاط ألف الحالة ولاحقة الفاعل تبقى ح ل م مطابقة ذاتيًّا؛ لا صف إبدال لازم.", "الحالم، صاحب الرؤيا", "من حلم في نومه ورأى رؤيا", "فاعل حدث الحلم نفسه", w("al_sihah", "ما يراه النائم", "يسند الحلم إلى ما يراه النائم"), w("al_muhkam", "حلم في نومه", "يسمي فاعل الرؤيا بفعل حلم")),
    I(1334, "حلم", "حلم", "ROOT-TRACE", "الجذر الكامل", "الحاء واللام والميم هويات؛ لا صف إبدال لازم.", "فعل رؤية الحلم", "حلم في نومه ورأى رؤيا", "حدث الرؤيا نفسه", w("al_muhkam", "حلم في نومه", "ينص على فعل الحلم في النوم"), w("lisan", "حلم في نومه", "يسند الفعل إلى الرؤيا في المنام")),
    I(538, "حنك", "حنك", "ROOT-TRACE", "الجذر الكامل", "بعد إسقاط ألف الحالة تبقى ح ن ك مطابقة ذاتيًّا؛ لا صف إبدال لازم.", "الحنك، سقف الفم", "الحنك، باطن أعلى الفم", "العضو الفموي نفسه", w("lisan", "الحنك من الإنسان", "يعرف الحنك بباطن أعلى الفم"), w("taj_al_arus", "الحنك", "يعرف الحنك في الإنسان والدابة")),
    I(1272, "حرر", "حرر", "ROOT-TRACE", "الجذر الكامل المضعّف", "الحاء والراء المضعّفة هويات؛ لا صف إبدال لازم.", "تحرير الشخص وإخراجه من الرق", "حرره فأعتقه وجعله من العبيد حرًا", "حدث الإعتاق نفسه", w("lisan", "حرره", "ينص على أن حرره أعتقه"), w("taj_al_arus", "جعل من العبيد حرا", "يعرف المحرر بمن جعل من العبيد حرًا")),
    I(342, "برق", "برق", "ROOT-TRACE", "الجذر الكامل", "بعد إسقاط ألف الحالة تبقى ب ر ق مطابقة ذاتيًّا؛ لا صف إبدال لازم.", "البرق في السماء", "البرق الذي يلمع في الغيم", "الظاهرة الجوية نفسها", w("lisan", "البرق الذي يلمع في الغيم", "يعرف البرق بلمعانه في الغيم"), w("taj_al_arus", "البرق", "يسمي بروق السحاب واللمعان")),
)


def main() -> None:
    current = TARGET.read_text(encoding="utf-8")
    if START in current and END in current:
        before, remainder = current.split(START, 1)
        _old, after = remainder.split(END, 1)
        current = before.rstrip() + "\n" + after.lstrip()
    elif START in current or END in current:
        raise SystemExit("حد واحد للدفعة الثالثة موجود دون الآخر")

    fan_module = C.load_fan_module()
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
        raise SystemExit("تعذر تعيين كل المداخل أو الأسر في الدفعة الثالثة")

    blocks = [
        START,
        "",
        f"## دفعة الاكتشاف الآرامية أ {BATCH_NO}: {BATCH_TITLE}",
        "",
        f"- بيان النطاق، الخطوة 14: {BATCH_SCOPE}",
        "",
    ]
    for rank, item in enumerate(ITEMS, 1):
        entry = entries[item.ordinal]
        entry_id = C.clean(entry["entry_id"])
        family_id = C.clean(families[entry_id])
        a = C.chosen_witness(fan_module, matches[item.root], item.witness_a)
        b = C.chosen_witness(fan_module, matches[item.root], item.witness_b)
        headword = C.clean(entry["headword"])
        romanization = C.clean(entry["romanization"]) or "بلا رومنة منشورة"
        gloss = C.clean(entry["gloss"])
        etymology = C.clean(entry["etymology"]) or "لا حقل اشتقاق مستقل؛ معنى الفرع منشور في المدخل"
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
                "التقاء الجذر والمدار مسند أعلاه."
            )
        )
        heading_label = "بطاقة" if parked_reason else "مراجعة عضوية"
        blocks.extend(
            [
                f"### {heading_label}: `{family_id}`، {headword}، دفعة الاكتشاف الآرامية أ {BATCH_NO}، الرتبة {rank}، العضو `{entry_id}`",
                f"- عائق: النوع={blocker_state}؛ يتطلب={blocker_requirement}؛ العضو=`{entry_id}`.",
                "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)",
                f"- الصورة الصامتة في الفرع: `{headword}`؛ الرومنة المنشورة: `{romanization}`.",
                f"- الكلمةُ في الفرع: {headword} `{romanization}`، {C.clean(entry['pos'])}، «{gloss}» [Kaikki Aramaic، `{entry_id}`].",
                f"- أقدمُ صورة أو مقارنة منشورة: {etymology}",
                "- الخطوةُ صفر: لا تدخل ألف الحالة أو لاحقة الفاعل المسماة في المصدر الجذر؛ لا تنزع زيادة بالتخمين، والعضو وحده وحدة الحكم.",
                f"- درجةُ المقارنة: {item.degree}؛ لم ينزل الحكم ما دام الجذر ناجحًا.",
                f"- مسحُ المعاني العربيّة: مروحة `{item.root}` قُرئت، واختير الحس يدويًّا في مصدرين مستقلين.",
                f"  - {C.clean(a['source_label'])}: «{C.clean(a['excerpt'])}»",
                f"  - المرساة الدلالية البشرية في المصدر الأول: {item.witness_a.human_reading}.",
                f"  - {C.clean(b['source_label'])}: «{C.clean(b['excerpt'])}»",
                f"  - المرساة الدلالية البشرية في المصدر الثاني: {item.witness_b.human_reading}.",
                f"- المقابلُ من اللسان: `{item.counterpart}`؛ الشاهدان يسندان الحس ولا يولدان الحكم آليًّا.",
                f"- مسارُ الصوت: {item.sound}",
                f"- المعنى من قاموس الفرع: «{gloss}» [Kaikki Aramaic، `{entry_id}`].",
                f"- المدار: جوار المعنى في الفرع: {item.branch_neighborhood}؛ جوار المعنى في العربية: {item.arabic_neighborhood}؛ موضع الالتقاء: {item.meeting}.",
                f"- المصفاة: loan_hint={loan}؛ لا مانح أجنبي مسمى، وفُصل العضو عن المتجانسات.",
                f"- فصلُ المتجانسات والاقتراض: العضو `{entry_id}` وحده؛ لا وراثة.",
                "- إشعاع الأسرة في الفرع: سلسلة المعنى المسماة وحدها، ولكل عضو حق نقض.",
                "- إشعاع الأسرة في العربية: الحس المستشهد به وحده، بلا وراثة لسائر المروحة.",
                "- جسورُ الاسترداد المفحوصة: المصدر؛ الجذر؛ المدار؛ الشاهدان؛ الصوت؛ القرض؛ المتجانس.",
                f"- حالةُ الإغلاق: {live_state}.",
                f"- الحكم (استكشاف): {verdict_line}",
                *(
                    [
                        "- مراجعة المصير: فُحص العضو منفردًا بمروحة المصدرين والمدار؛ الحكم السابق، إن وجد، محفوظ أعلاه."
                    ]
                    if not parked_reason
                    else []
                ),
                "- عدسة الاسترداد: بدأت بالجذر الكامل وبالحس لا بالرسم وحده.",
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
        f"appended={len(ITEMS)} positives={len(ITEMS) - len(PARKED)} "
        f"closures=0 pending={len(PARKED)}"
    )


if __name__ == "__main__":
    main()
