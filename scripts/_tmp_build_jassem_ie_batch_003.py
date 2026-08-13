# -*- coding: utf-8 -*-
"""One-shot wrapper for Jassem Indo-European bridge-agree batch 003."""
from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
BUILDER_COMMIT = "8d575e1"
source = subprocess.check_output(
    ["git", "show", f"{BUILDER_COMMIT}:scripts/_tmp_build_jassem_ie_batch_002.py"],
    cwd=ROOT, text=True, encoding="utf-8",
)
source = source.replace("002", "003").replace("BATCH = 2", "BATCH = 3")
ns: dict[str, Any] = {"__name__": "_jassem_ie_batch_003_base", "__file__": __file__}
exec(compile(source, f"{BUILDER_COMMIT}:jassem003", "exec"), ns)
ns["READING_BASE_COMMIT"] = "8d575e1"
B = ns["B"]
spec = ns["spec"]

ns["GREEK"] = set("""Galaxy|Genealogy|Gram|Graph|Hedonism|Hemoglobin|Hemorrhage|Idea""".split("|"))
ns["LATIN"] = set("""Fatal|Feminine|Fibre|Fighter aircraft|Fracture|Fungus|Furnace|Future|Generation|Generous|Govern|Horticulture|Hostility|Illusion|Imperative|Incision|Incline|Including|Increase|Incubus|Indemnity|Independence|Inflate|Influenza|Inform|Infrastructure|Ingredient|Inherit|Initial|Injury|Intellect|Inter|Intercourse|Internet|Invoke|Irrigate|Issue|Item|Junior|Jury|Justify|Lance|Language""".split("|"))
ns["NORSE"] = {"Get", "Girl", "Husband", "Kid", "Knife", "Law"}
ns["MIDDLE"] = set("""Fatigues|Fault|Fever|Fine|Fortune|Fruit|Futile|Garden|Glacier|Gloss|Grace|Grade|Grail|Grape|Group|Guilt|Guilty|Gulf|Harass|Heir|Heir Apparent|Herb|Humour|Jacket|Jail|Jewel""".split("|"))


def route(*parts: str) -> str:
    return B.route(*parts)


ns["POSITIVE"] = {
    "father": [spec(
        "فطر", "ROOT-ECHO", "`father` في الوالد الذي يكون منه بدء خروج الولد إلى الوجود",
        "الأب مبدأ خروج الولد أول أمره من أصل النسل؛ فهذا مدار سببي واحد إلى حدث `فطر` في الخروج الأول الشاق لما فوقه.",
        route("f↔ف=`IDN-06`", "th↔ط=`DENT-05`", "r↔ر=`IDN-01`"),
        ["`f` + `ف` + «الإنجليزيّة الوسطى/Middle English»", "`th` + `ط` + «الإنجليزيّة الوسطى/Middle English»", "`r` + `ر` + «الإنجليزيّة الوسطى/Middle English»"],
    )],
    "fever": [spec(
        "فور", "ROOT-ECHO", "`fever` في اشتداد حرارة الجسد وجيشانها صعودًا",
        "الحمّى جيشان حرارة وقوة في البدن ترتفع كما يفور السائل؛ فهذا مدار جسدي واحد إلى حدث `فور`.",
        route("f↔ف=`IDN-06`", "v↔و=`LAB-06`", "r↔ر=`IDN-01`"),
        ["`f` + `ف` + «الإنجليزيّة الوسطى/Middle English»", "`v` + `و` + «الإنجليزيّة الوسطى/Middle English»", "`r` + `ر` + «الإنجليزيّة الوسطى/Middle English»"],
    )],
    "fine": [spec(
        "فن", "NUCLEUS-TRACE", "`fine` في الدقة والرقة وصغر السمك أو الحبيبات",
        "الدقيق يمتد مع رقة وضعف في السمك أو الحبيبات؛ وهذا نص حدث `فن` مباشرة، لا معنى الجودة المتجانس معه.",
        route("f↔ف=`IDN-06`", "n↔ن=`IDN-03`"),
        ["`f` + `ف` + «الإنجليزيّة الوسطى/Middle English»", "`n` + `ن` + «الإنجليزيّة الوسطى/Middle English»"],
    )],
    "froth": [spec(
        "فرث", "ROOT-ECHO", "`froth`، فقاعات ودقائق غليظة نسبيًا تتسيب على سطح السائل",
        "الرغوة اجتماع دقائق أو فقاعات ثم تسيبها بخشونة ظاهرة على السطح؛ فهذا مدار مادي واحد إلى حدث `فرث`.",
        route("f↔ف=`IDN-06`", "r↔ر=`IDN-01`", "th↔ث=`DENT-01`"),
        ["`f` + `ف` + «الإنجليزيّة القديمة/Old English»", "`r` + `ر` + «الإنجليزيّة القديمة/Old English»", "`th` + `ث` + «الإنجليزيّة القديمة/Old English»"],
    )],
    "guess": [spec(
        "وجس", "ROOT-TRACE", "`guess` في حصول إحساس دقيق في النفس من غير يقين",
        "التخمين شيء دقيق الوقع يحصل في أثناء النفس ولا يبلغ اليقين؛ وهذا نص حدث `وجس` مباشرة.",
        route("g↔ج=`IDN-08`", "s↔س=`IDN-07`", "باب المعتل المسمى يثبت الواو في الأول"),
        ["`g` + `ج` + «الإنجليزيّة القديمة/Old English»", "`s` + `س` + «الإنجليزيّة القديمة/Old English»"],
    )],
    "hold": [spec(
        "قلد", "ROOT-ECHO", "`hold` في حوز الشيء وحبسه أو حمله ومنع انفلاته",
        "الإمساك حوز بحبس شديد، وقد يكون حملًا أو نقلًا؛ وهذا مدار واحد إلى حدث `قلد`.",
        route("ق↔k=`GUT-01` ثم k→h=`BR-GRIM-01`", "l↔ل=`IDN-04`", "d↔د=`IDN-09`"),
        ["`h` + `ق` + «الإنجليزيّة القديمة/Old English»", "`l` + `ل` + «الإنجليزيّة القديمة/Old English»", "`d` + `د` + «الإنجليزيّة القديمة/Old English»"],
    )],
    "horn": [spec(
        "قرن", "ROOT-TRACE", "`horn`، النتوء الصلب الممتد في أعلى رأس الحيوان أو مقدمه",
        "القرن نتوء شديد ممتد في أعلى الجسم أو مقدمه؛ وهذا نص الحدث المجمّد نفسه.",
        route("ق↔k=`GUT-01` ثم k→h=`BR-GRIM-01`", "r↔ر=`IDN-01`", "n↔ن=`IDN-03`"),
        ["`h` + `ق` + «الإنجليزيّة الوسطى/Middle English»", "`r` + `ر` + «الإنجليزيّة الوسطى/Middle English»", "`n` + `ن` + «الإنجليزيّة الوسطى/Middle English»"],
    )],
    "kettle": [spec(
        "قدر", "ROOT-ECHO", "`kettle`، وعاء يضبط المائع القابل للتسيب ويحويه عند التسخين والصب",
        "القدر يحكم المائع ويضبط تسيبه في حيز الوعاء؛ فهذا مدار أداتي واحد إلى حدث `قدر`.",
        route("k↔ق=`GUT-01`", "t↔د=`BR-GRIM-02`", "l↔ر=`LIQ-01`"),
        ["`k` + `ق` + «الإنجليزيّة القديمة/Old English»", "`t` + `د` + «الإنجليزيّة القديمة/Old English»", "`l` + `ر` + «الإنجليزيّة القديمة/Old English»"],
    )],
}


def rewrite_audit() -> None:
    path = ROOT / "data" / "jassem-indo-european-batch-003.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    confirmations = []
    for item in payload["khashim_card_supplements"]:
        if item["head"].casefold() == "free":
            item["existing_positive_confirmed"] = "فر؛ NUCLEUS-TRACE already issued on the exact free member"
            confirmations.append("Free")
        if item["head"].casefold() == "lad":
            item["existing_positive_confirmed"] = "ولد؛ ROOT-TRACE already issued on the exact lad member"
            confirmations.append("Lad")
    payload["previous_positive_confirmations"] = len(confirmations)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    highlights = [
        "`Father` دُمجت في بطاقة خشيم، وأخرج فحص عضوها `فطر` في بدء خروج الولد؛ `ROOT-ECHO`.",
        "`Fever` ↔ `فور`: الحمّى جيشان حرارة وقوة إلى أعلى؛ `ROOT-ECHO`.",
        "`Fine` ↔ `فن`: صدر معنى الدقة والرقة وحده، وفُصل عن متجانس الجودة؛ `NUCLEUS-TRACE`.",
        "`Free` ثبّت شاهد جاسم للحكم السابق `فر` في فصل المقيد عن قيده؛ لم يتكرر الحكم.",
        "`Froth` ↔ `فرث`: فقاعات دقيقة مجتمعة تتسيب بخشونة على سطح السائل؛ `ROOT-ECHO`.",
        "`Guess` ↔ `وجس`: إحساس دقيق يقع في النفس دون يقين؛ `ROOT-TRACE`.",
        "`Hold` ↔ `قلد`: حوز الشيء بحبس شديد وحمله ومنع انفلاته؛ `ROOT-ECHO`.",
        "`Horn` دُمجت في بطاقة `cornu/corn/horn`، وحُكم عضو `horn` نفسه بمسار غريم؛ `ROOT-TRACE`.",
        "`Kettle` ↔ `قدر`: الوعاء يضبط المائع القابل للتسيب ويحكمه؛ `ROOT-ECHO`.",
        "`Lad` ثبّت شاهد جاسم للحكم السابق `ولد` على عضو الكلمة نفسه؛ لم ينشأ تكرار.",
    ]
    counts = Counter(card["language"] for card in payload["rows"])
    audit = [
        "# محضر حصاد جاسم الهنديّ الأوربيّ، دفعة الموافقات 003 (2026-08-13)", "", "## النطاق والحصيلة", "",
        f"- انتُخبت 300 هوية موافقة غير معالجة بعد استبعاد {payload['selection']['prior_claim_keys_excluded']} مفتاحًا ثابتًا؛ كان الباقي عند التجميد {payload['selection']['eligible_unprocessed_at_freeze']}.",
        f"- انكمشت الصفوف إلى {payload['cards_touched']} كلمة: {payload['jassem_card_supplements_count']} إلحاقًا ببطاقات جاسم و{payload['khashim_card_supplements_count']} ببطاقات خشيم و{payload['new_cards_written']} بطاقة جديدة؛ فجوات المدخل={payload['selection']['source_head_gaps']}.",
        f"- صدر {payload['newly_issued_positive_cards']} حكمًا موجبًا جديدًا، وثُبّت {len(confirmations)} حكم سابق بلا تكرار؛ بقي {payload['open_new_cards']} من البطاقات الجديدة مفتوحًا.",
        "- توزيع البطاقات الجديدة: " + "، ".join(f"{B.LANG_LABELS[k]}={v}" for k, v in sorted(counts.items())) + ".",
        f"- فُحص أو روجع {payload['rank_review']['ranked_candidates_in_new_or_referenced_full_fans']} مرشحًا في المراوح الكاملة المرتبة بـ`F.rank`؛ أضاف `fan_with_dialect` {payload['rank_review']['new_card_fan_with_dialect_additions']} صورة، والوزن لم يحكم.",
        "", "## أسباب الأحكام", "",
        "- موافقة الجسر رتبت الطابور ولم تدخل الحكم؛ كل موجب جديد استوفى مسارًا مسمى وحدثًا مجمدًا ومدارًا مكتوبًا.",
        "- جُمعت المطابقات مع بطاقات خشيم، وثبت شاهدا `Free` و`Lad` بدل إصدار الحكم نفسه ثانية.",
        "- فُصلت متجانسات الرسم عند الحكم، مثل `fine` الدقة لا الجودة، وبقي ما لا يوافق الحدث مفتوحًا.",
        "- غياب الصورة من اللقطة لم يدخل الحكم، وأرقام الصفوف مواضع تجميد لا هويات.",
        "", "## عشرة مواضع بارزة", "",
    ] + [f"{i}. {line}" for i, line in enumerate(highlights, 1)] + [
        "", "## تحقق الإيداع", "", "- البيان: `data/jassem-indo-european-batch-003.json`.", "- القراءة: الملفات الثمانية المسموح بها وحدها، مع الإلحاق داخل البطاقة الأصلية.", "- الإيداع يُجرى بأمر `scripts/ship.py --only ... --push` بعد خضرة البوابات.",
    ]
    (ROOT / "05-audits" / "2026-08-13-jassem-indo-european-batch-003.md").write_text("\n".join(audit) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    result = ns["main"]()
    rewrite_audit()
    raise SystemExit(result)
