# -*- coding: utf-8 -*-
"""One-shot wrapper for Jassem Indo-European bridge-agree batch 004."""
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
source = source.replace("002", "004").replace("BATCH = 2", "BATCH = 4")
ns: dict[str, Any] = {"__name__": "_jassem_ie_batch_004_base", "__file__": __file__}
exec(compile(source, f"{BUILDER_COMMIT}:jassem004", "exec"), ns)
ns["READING_BASE_COMMIT"] = "0fb91a8"
B = ns["B"]
spec = ns["spec"]

ns["GREEK"] = set("""Leukemia|Machine gun|Mental|Meter|Monarch|Monarchy|Myth|Nature|Nausea|Ophthalmic|Oregano|Orgasm|Parameter|Parasite|Particle|Pathos|Pentagon|Period|Physician|Planet|Poet|Presbyter|Psalm|Psyche""".split("|"))
ns["LATIN"] = set("""Legal|Liberal|Libra|Line|List|Locative|Major|Majority|Malignant|Mass|Measure|Model|Moral|Morbid|Mortar|Move|Mucus|Navy|Negate|Noble|North|Notary|Note|Notice|Nurse|Occult|Odd|Odour|Officer|Ointment|Opposite to|Order|Ordinal|Organization|Ornate|Oven|Overalls|Palace|Pass|Past|Previous|Priority|Privilege|Probability|Profit|Prohibition|Prosecutor General|Public Opinion|Plurality|Plus|Police Officer|Port|Post|Potato|Power|Pregnant|Present|Press|Price|Prince|Prostitute""".split("|"))
ns["NORSE"] = {"Lift", "Load", "Low", "Mistake", "Near", "Needle", "Next to", "Nigh", "Night"}
ns["MIDDLE"] = set("""Lesson|Letter|Lime|Lizard|Loaf|Love|Lunch|Lust|Mad|Magna Carta|Maid|Malady|Malaise|Male|Mare|Marry|Mason|Masticate|May|Mayor|Meal|Mean|Meat|Melt|Menace|Merely|Merry|Merry Christmas|Milk|Mince|Miracle|Mix|Moan|Moor|More|Mother|Mound|Mount|Mow|Mule|Murmur|Muse|Musk|Net|Noise|Nun|Oath|Omen|Onion|Orchard|Pair|Party|Pastry|Pause|Peach|Peel|Pen|Pepper|Pickle|Pierce|Piety|Pig|Pink|Plague|Plane|Plant|Plateau|Playful|Please|Pledge|Plot|Plum|Pore|Pork|Pot|Powder|Praise|Pray|Priest|Prune|Pudding|Puke|Pull|Pulp|Pumpkin|Pure""".split("|"))


def route(*parts: str) -> str:
    return B.route(*parts)


ns["POSITIVE"] = {
    "loaf": [spec(
        "لف", "NUCLEUS-ECHO", "`loaf` في رغيف أو لفافة خبز تتجمع مادتها في كتلة ملتفة كثيفة",
        "لفافة الخبز تُلوى مادتها على ظاهرها حتى توجد كتلة كثيفة؛ فهذا مدار صناعي واحد إلى حدث `لف`.",
        route("l↔ل=`IDN-04`", "f↔ف=`IDN-06`"),
        ["`l` + `ل` + «الإنجليزيّة القديمة/Old English»", "`f` + `ف` + «الإنجليزيّة القديمة/Old English»"],
    )],
    "letter": [spec(
        "رتل", "ROOT-ECHO", "`letter`، وحدة كتابية تنتظم مع نظائرها متواليةً على السطر أو في الأبجدية",
        "الحروف أفراد متوالية بينها مسافات مضبوطة، تنتظم في السطر أو ترتيب الأبجدية؛ فهذا مدار ترتيبي واحد إلى حدث `رتل`.",
        route("l↔ر=`LIQ-01`", "t↔ت=`IDN-11`", "r↔ل=`LIQ-01`"),
        ["`l` + `ر` + «الإنجليزيّة الوسطى/Middle English»", "`t` + `ت` + «الإنجليزيّة الوسطى/Middle English»", "`r` + `ل` + «الإنجليزيّة الوسطى/Middle English»"],
    )],
    "pass": [spec(
        "فوز", "ROOT-ECHO", "`pass` في العبور من جانب إلى آخر ومجاوزة المسافة",
        "المرور عبور امتداد حتى الخروج من طرفه؛ وحدث `فوز` يخصص هذا المدار بعبور مسافة قفر طويلة، فيبقى الصدى الحركي واحدًا مع فرق البيئة.",
        route("p↔ف=`IDN-06`", "s↔ز=`SIB-03`", "باب المعتل المسمى يثبت الواو في الجوف"),
        ["`p` + `ف` + «اللاتينيّة القديمة/Old Latin»", "`s` + `ز` + «اللاتينيّة القديمة/Old Latin»"],
    )],
    "pen": [spec(
        "بن", "NUCLEUS-ECHO", "`pen`، حظيرة مبنية تحدد حيزًا يمتد فيه الحيوان ويُحبس",
        "الحظيرة بناء ممتد يحد حيزًا للإقامة؛ فهذا مدار مكاني واحد إلى حدث `بن` في الامتداد والبناء.",
        route("p↔ب=`LAB-01`", "n↔ن=`IDN-03`"),
        ["`p` + `ب` + «الإنجليزيّة الوسطى/Middle English»", "`n` + `ن` + «الإنجليزيّة الوسطى/Middle English»"],
    )],
    "praise": [spec(
        "برز", "ROOT-ECHO", "`praise` في إظهار محاسن شخص أو عمل وإبرازها للسامع",
        "الثناء يخرج المحاسن من الخفاء إلى بروز قوي ظاهر؛ فهذا مدار خطابي واحد إلى حدث `برز`.",
        route("p↔ب=`LAB-01`", "r↔ر=`IDN-01`", "s↔ز=`SIB-03`"),
        ["`p` + `ب` + «الإنجليزيّة الوسطى/Middle English»", "`r` + `ر` + «الإنجليزيّة الوسطى/Middle English»", "`s` + `ز` + «الإنجليزيّة الوسطى/Middle English»"],
    )],
    "pull": [spec(
        "بل", "NUCLEUS-ECHO", "`pull` في القبض على الشيء باليد وجذبه نحو القابض",
        "الجذب يبدأ بتمكن اليد من الشيء وحوزه بشدة كيلا يفلت؛ فهذا مدار حركي واحد إلى حدث `بل`.",
        route("p↔ب=`LAB-01`", "ll↔ل=`IDN-04` بعد قراءة الإدغام صوتًا واحدًا"),
        ["`p` + `ب` + «الإنجليزيّة الوسطى/Middle English»", "`l` + `ل` + «الإنجليزيّة الوسطى/Middle English»"],
    )],
    "pure": [spec(
        "بر", "NUCLEUS-TRACE", "`pure` في الشيء المتجرد من الشوائب والخالص منها",
        "الطهارة تجرد وخلوص من المخالط؛ وهذا نص حدث `بر` مباشرة.",
        route("p↔ب=`LAB-01`", "r↔ر=`IDN-01`"),
        ["`p` + `ب` + «الإنجليزيّة الوسطى/Middle English»", "`r` + `ر` + «الإنجليزيّة الوسطى/Middle English»"],
    )],
}


def rewrite_outputs() -> None:
    manifest = ROOT / "data" / "jassem-indo-european-batch-004.json"
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    # Pass and Past are two members of one pre-existing Khashim form family.
    # Collapse their source claims into one card supplement and render one
    # marker, while keeping the positive judgment scoped to the pass member.
    family = [item for item in payload["khashim_card_supplements"] if item["target_card_id"] == "KIE-M0571"]
    if len(family) != 2 or {item["head"] for item in family} != {"Pass", "Past"}:
        raise AssertionError("expected the Pass/Past KIE-M0571 family")
    pass_item = next(item for item in family if item["head"] == "Pass")
    past_item = next(item for item in family if item["head"] == "Past")
    combined = {
        **pass_item,
        "head": "Pass / Past",
        "forms": ["Pass", "Past"],
        "fan_sizes_by_form": {"Pass": pass_item["fan_size"], "Past": past_item["fan_size"]},
        "fan_size": pass_item["fan_size"] + past_item["fan_size"],
        "source_rows": sorted(pass_item["source_rows"] + past_item["source_rows"]),
        "source_claims": pass_item["source_claims"] + past_item["source_claims"],
        "reason": "two members of the same Khashim form-family card; one supplement with all Jassem claims",
    }
    payload["khashim_card_supplements"] = [
        item for item in payload["khashim_card_supplements"] if item["target_card_id"] != "KIE-M0571"
    ] + [combined]
    payload["khashim_card_supplements_count"] = len(payload["khashim_card_supplements"])
    payload["cards_touched"] = payload["new_cards_written"] + payload["jassem_card_supplements_count"] + payload["khashim_card_supplements_count"]

    target_payload = json.loads((ROOT / "data/khashim-indo-european-batch-004.json").read_text(encoding="utf-8"))
    target_card = next(card for card in target_payload["rows"] if (card.get("merged_card_id") or card.get("card_id")) == "KIE-M0571")
    prior = [item for item in target_card.get("jassem_supplements", []) if item.get("batch") != 4]
    prior.append({"batch": 4, "source": "data/prior-art-pairs.json", "source_claims": combined["source_claims"]})
    target_card["jassem_supplements"] = prior
    (ROOT / "data/khashim-indo-european-batch-004.json").write_text(
        json.dumps(target_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n",
    )
    old_latin_path = ROOT / "04-cross-linguistic/readings/old-latin.md"
    old_latin = old_latin_path.read_text(encoding="utf-8")
    root_events, nucleus_events = B.load_events()
    old_latin = ns["add_khashim_supplement"](
        old_latin, "KIE-M0571", combined, combined["rejudgments"],
        root_events, nucleus_events, target_card["closure"],
    )
    old_latin_path.write_text(old_latin, encoding="utf-8", newline="\n")

    confirmations = []
    for item in payload["khashim_card_supplements"]:
        if item["head"].casefold() == "pierce":
            item["existing_positive_confirmed"] = "فرق و فرج؛ ROOT-TRACE already issued on the exact pierce member"
            confirmations.append("Pierce")
    payload["previous_positive_confirmations"] = len(confirmations)
    manifest.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    counts = Counter(card["language"] for card in payload["rows"])
    highlights = [
        "`Loaf` دُمجت في بطاقة خشيم، وخرج `لف` في كتلة الخبز الملتفة الكثيفة؛ `NUCLEUS-ECHO`.",
        "`Letter` ↔ `رتل`: الحروف أفراد متوالية مضبوطة المسافات في السطر أو الأبجدية؛ `ROOT-ECHO`.",
        "`Pass` دُمجت في بطاقة خشيم؛ العبور العام يلتقي `فوز` في مجاوزة امتداد القفر مع فصل قيد البيئة؛ `ROOT-ECHO`.",
        "`Pen` ↔ `بن`: الحظيرة بناء ممتد يحد حيزًا للإقامة؛ `NUCLEUS-ECHO`.",
        "`Pierce` ثبّت شاهد جاسم للحكمين السابقين `فرق` و`فرج` في عضو الكلمة نفسه، بلا تكرار.",
        "`Praise` ↔ `برز`: الثناء يخرج المحاسن من الخفاء إلى بروز ظاهر؛ `ROOT-ECHO`.",
        "`Pull` ↔ `بل`: الجذب يبدأ بتمكن اليد من المقبوض وحوزه بشدة؛ `NUCLEUS-ECHO`.",
        "`Pure` ↔ `بر`: التجرد والخلوص من الشوائب هو الحدث نفسه؛ `NUCLEUS-TRACE`.",
        "`Order` بقي مفتوحًا: مروحتُه عرضت `رتل`، لكن مسار الدال إلى التاء غير مرخّص لهذا الفرع اللاتيني.",
        "`Musk` بقي مفتوحًا: تشابه الرسم مع `مسك` لم يجعل مادة الطيب حدث ضبط أو حبس.",
    ]
    audit = [
        "# محضر حصاد جاسم الهنديّ الأوربيّ، دفعة الموافقات 004 (2026-08-13)", "", "## النطاق والحصيلة", "",
        f"- انتُخبت 300 هوية موافقة غير معالجة بعد استبعاد {payload['selection']['prior_claim_keys_excluded']} مفتاحًا ثابتًا؛ كان الباقي عند التجميد {payload['selection']['eligible_unprocessed_at_freeze']}.",
        f"- انكمشت الصفوف إلى {payload['cards_touched']} كلمة: {payload['jassem_card_supplements_count']} إلحاقًا ببطاقات جاسم و{payload['khashim_card_supplements_count']} ببطاقات خشيم و{payload['new_cards_written']} بطاقة جديدة؛ فجوات المدخل={payload['selection']['source_head_gaps']}.",
        f"- صدر {payload['newly_issued_positive_cards']} حكمًا موجبًا جديدًا، وثُبّت {len(confirmations)} حكم سابق بلا تكرار؛ بقي {payload['open_new_cards']} من البطاقات الجديدة مفتوحًا.",
        "- توزيع البطاقات الجديدة: " + "، ".join(f"{B.LANG_LABELS[k]}={v}" for k, v in sorted(counts.items())) + ".",
        f"- فُحص أو روجع {payload['rank_review']['ranked_candidates_in_new_or_referenced_full_fans']} مرشحًا في المراوح الكاملة المرتبة بـ`F.rank`؛ أضاف `fan_with_dialect` {payload['rank_review']['new_card_fan_with_dialect_additions']} صورة، والوزن لم يحكم.",
        "", "## أسباب الأحكام", "",
        "- موافقة الجسر رتبت الطابور ولم تدخل الحكم؛ كل موجب جديد استوفى مسارًا مسمى وحدثًا مجمدًا ومدارًا مكتوبًا.",
        "- جُمعت المطابقات مع بطاقات خشيم، وثُبّت شاهد `Pierce` بدل إصدار حكمي البطاقة مرة أخرى.",
        "- فُحصت المروحة كلها ولو خالفت جذر المؤلف، كما في `Pure↔بر` و`Praise↔برز`.",
        "- رُفض المسار غير المرخص ولو وافق المعنى، كما في `Order↔رتل`؛ والوزن لم يرفع هذا الرد.",
        "- غياب الصورة من اللقطة لم يدخل الحكم، وأرقام الصفوف مواضع تجميد لا هويات.",
        "", "## عشرة مواضع بارزة", "",
    ] + [f"{i}. {line}" for i, line in enumerate(highlights, 1)] + [
        "", "## تحقق الإيداع", "", "- البيان: `data/jassem-indo-european-batch-004.json`.", "- القراءة: الملفات الثمانية المسموح بها وحدها، مع الإلحاق داخل البطاقة الأصلية.", "- الإيداع يُجرى بأمر `scripts/ship.py --only ... --push` بعد خضرة البوابات.",
    ]
    (ROOT / "05-audits" / "2026-08-13-jassem-indo-european-batch-004.md").write_text("\n".join(audit) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    result = ns["main"]()
    rewrite_outputs()
    raise SystemExit(result)
