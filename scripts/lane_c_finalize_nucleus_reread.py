#!/usr/bin/env python3
"""Finalize the six-language lane C binary-nucleus rereading.

This is a lane-owned, idempotent finalizer.  It reads the frozen core,
network, Arabic lexica, and recovery inventories without changing them.  It
appends human adjudications to the six lane C reading ledgers, appends their
machine-readable verdict rows, and removes exactly those promoted members
from lane C's non-issuance ledger.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from recovery_pipeline.network import compile_network  # noqa: E402


DATE = "2026-08-01"
MARKER = "LANE-C-NUCLEUS-REREAD-2026-08-01"
CORE_PATH = ROOT / "data" / "juthoor-core-levels.json"
NETWORK_PATH = ROOT / "04-cross-linguistic" / "shift-network-draft.md"
ARABIC_PATH = ROOT / "Resources" / "arabic_roots_hf" / "train-00000-of-00001.parquet"
RANKING_PATH = ROOT / "04-cross-linguistic" / "data" / "lane_c_nucleus_reread_ranked.json"
ADJUDICATION_PATH = ROOT / "04-cross-linguistic" / "data" / "lane_c_nucleus_reread_adjudications.json"
PROMOTIONS_PATH = ROOT / "04-cross-linguistic" / "data" / "lane_c_two_layer_semantic_promotions.jsonl"
COVERAGE_PATH = ROOT / "04-cross-linguistic" / "data" / "lane_c_coverage.jsonl"
AUDIT_PATH = ROOT / "05-audits" / "lane-c-2026-08-01-nucleus-reread.md"

SOURCE_NAMES = {
    "لسان العرب لابن منظور",
    "تاج العروس لمرتضى الزبيدي",
}
LONG_DASH = chr(0x2014)

LANGUAGES: dict[str, dict[str, str | int]] = {
    "ancient_greek": {
        "label": "اليونانية القديمة",
        "source": "Kaikki Ancient Greek",
        "reading": "ancient-greek.md",
        "db": "cache/recovery_pipeline/inventory-v5.sqlite",
        "denominator": 56058,
    },
    "latin": {
        "label": "اللاتينية",
        "source": "Kaikki Latin",
        "reading": "old-latin.md",
        "db": "cache/recovery_pipeline/inventory-v5.sqlite",
        "denominator": 883915,
    },
    "persian": {
        "label": "الفارسية",
        "source": "Kaikki Persian",
        "reading": "persian.md",
        "db": "cache/recovery_pipeline/week17-day1-inventory.sqlite",
        "denominator": 19361,
    },
    "gothic": {
        "label": "القوطية",
        "source": "Kaikki Gothic",
        "reading": "gothic.md",
        "db": "cache/recovery_pipeline/week17-day1-inventory.sqlite",
        "denominator": 23005,
    },
    "old_norse": {
        "label": "النوردية القديمة",
        "source": "Kaikki Old Norse",
        "reading": "old-norse.md",
        "db": "cache/recovery_pipeline/week17-day1-inventory.sqlite",
        "denominator": 11169,
    },
    "welsh": {
        "label": "الويلزية",
        "source": "Kaikki Welsh",
        "reading": "welsh.md",
        "db": "cache/recovery_pipeline/week17-day1-inventory.sqlite",
        "denominator": 27715,
    },
}

IDENTITY: dict[str, set[str]] = {
    "ء": {"qstop"},
    "ب": {"b"},
    "ت": {"t"},
    "ث": {"th"},
    "ج": {"j"},
    "خ": {"kh"},
    "د": {"d"},
    "ذ": {"dh"},
    "ر": {"r"},
    "ز": {"z"},
    "س": {"s"},
    "ش": {"sh"},
    "ف": {"f"},
    "ق": {"q"},
    "ك": {"k"},
    "ل": {"l"},
    "م": {"m"},
    "ن": {"n"},
    "ه": {"h"},
    "و": {"w"},
    "ي": {"y", "j"},
}

ARABIC_EVIDENCE = {
    "ملح": "لسان العرب: «الملح: الرضاع»؛ وتاج العروس: «من المجاز الملح: الرضاع».",
    "زوج": "لسان العرب وتاج العروس: «الزوج: الاثنان»، ويذكران اقتران الشيئين.",
    "بطح": "لسان العرب: «البطح: البسط» و«بطحه على وجهه... ألقاه»؛ وتاج العروس: «بطحه... بسطه» و«ألقاه على وجهه».",
    "سطح": "لسان العرب وتاج العروس: «السطح: ظهر البيت»، وأنه أعلى الشيء.",
    "بتر": "لسان العرب: «البتر: استئصال الشيء قطعا»؛ وتاج العروس: «البتر... القطع قبل الإتمام».",
    "فرح": "لسان العرب: «الفرح: نقيض الحزن»؛ وتاج العروس: «الفرح... السرور».",
    "نكر": "لسان العرب: «النكر والنكراء... المنكر»؛ وتاج العروس يثبت النكر للمنكر وللأمر الشديد.",
    "برد": "لسان العرب وتاج العروس: «برد الحديد بالمبرد... سحله»، و«البرد: النحت».",
    "شقق": "لسان العرب وتاج العروس: «الشق: الصدع» في العود والحائط والزجاجة.",
    "شرب": "لسان العرب وتاج العروس: «شرب الماء وغيره».",
    "دلك": "لسان العرب وتاج العروس: «دلكت الشمس... غربت»، ومالت للغروب.",
    "عرج": "لسان العرب: «العرج والعرجة: الظلع»؛ وتاج العروس يثبت الأعرج والعرج ومشيته.",
    "عرش": "لسان العرب وتاج العروس: «العرش من البيت: سقفه».",
    "غلف": "لسان العرب وتاج العروس: «الغلاف... ما اشتمل على الشيء».",
    "غمر": "لسان العرب وتاج العروس: الغمرة زحمة الناس، وغمار الناس جمعهم المتكاثف.",
    "غلق": "لسان العرب وتاج العروس: الغلق والمغلاق ما يغلق به الباب، ويثبتان غلق الباب.",
    "طرف": "لسان العرب وتاج العروس: أصل الطرف الضرب على طرف العين ثم نقل إلى الضرب على الرأس.",
    "فند": "لسان العرب: فند الجبل شمراخه العظيم؛ وتاج العروس: «الفند... الجبل العظيم» أو رأسه.",
    "جلب": "لسان العرب وتاج العروس: «الجلب: الأصوات»، والجلبة اختلاط الصوت والصياح.",
}


def record(
    language: str,
    member_id: str,
    form: str,
    romanization: str,
    nucleus: str,
    support_root: str,
    tokens: list[str],
    rules: list[str],
    oldest: str,
    zero_step: str,
    gloss: str,
    orbit: str,
    verdict: str = "NUCLEUS-TRACE",
    comparison_basis: str = "surface-after-branch-morphology",
) -> dict[str, Any]:
    return {
        "language": language,
        "member_id": member_id,
        "form": form,
        "romanization": romanization,
        "nucleus": nucleus,
        "support_root": support_root,
        "comparison_tokens": tokens,
        "licensed_rules": rules,
        "oldest_form": oldest,
        "zero_step": zero_step,
        "branch_meaning": gloss,
        "orbit": orbit,
        "verdict": verdict,
        "comparison_basis": comparison_basis,
        "classical_sources": sorted(SOURCE_NAMES),
    }


RECORDS = [
    record("ancient_greek", "kaikki_ancient_greek:3947:en-ἀμέλγω-grc-verb-OShN5n1T", "ἀμέλγω", "amélgō", "مل", "ملح", ["m", "l"], [], "Proto-Indo-European *h₂melǵ-", "لا سابقة معجمية داخلة في اللب؛ أول صامتين في الساق m-l.", "to milk, emulge, to express milk from cows", "مباشر: الحلب واللبن/الرضاع"),
    record("ancient_greek", "kaikki_ancient_greek:13472:en-ζεῦγος-grc-noun-SrFjzctf", "ζεῦγος", "zeûgos", "زج", "زوج", ["z", "g"], ["GUT-03"], "Proto-Indo-European *yéwgos", "لا صامت صرفي قبل z-g؛ الصامت الثالث لا يدخل حكم النواة.", "pair (two things, persons or animals considered as pair)", "مباشر: الزوج والاثنان المقترنان"),
    record("ancient_greek", "kaikki_ancient_greek:9321:en-πταίω-grc-verb-VOnAPx6n", "πταίω", "ptaíō", "بط", "بطح", ["p", "t"], ["DENT-05", "LAB-01"], "probably Proto-Indo-European *p(y)eh₂w-", "اللب p-t محفوظ؛ لا تُستعمل نهاية الفعل صامتًا ثالثًا عربيًا.", "to cause to stumble, fall or fail", "مدار 5: السقوط أثر الإلقاء والبسط على الوجه"),
    record("ancient_greek", "kaikki_ancient_greek:932:en-στέγος-grc-noun-0aDW9HB0", "στέγος", "stégos", "سط", "سطح", ["s", "t"], ["DENT-05"], "Proto-Hellenic *(s)tégos < Proto-Indo-European *(s)tégos", "اللب s-t؛ بقية الصوامت لا تُطلب في نواة عربية.", "roof", "مباشر: سطح البيت وسقفه"),

    record("latin", "kaikki_latin:72052:en-mulgeo-la-verb-gnMhbPTq", "mulgeo", "", "مل", "ملح", ["m", "l"], [], "Proto-Italic *molgeō < Proto-Indo-European *h₂melǵ-", "اللب m-l قبل مادة التصريف اللاتينية.", "to milk, extract", "مباشر: الحلب واللبن/الرضاع"),
    record("latin", "kaikki_latin:58951:en-putamen-la-noun-7j0Yiqk-", "putamen", "", "بت", "بتر", ["p", "t"], ["LAB-01"], "putō + Latin nominal suffix -men", "نُزعت -men المصرح بها في الاشتقاق؛ بقي p-t.", "cutting, clipping (that which is cut away)", "مباشر: القطع والاستئصال"),
    record("latin", "kaikki_latin:8322:en-fructus-la-noun-99WiNlHv", "fructus", "", "فر", "فرح", ["f", "r"], [], "fruor + Latin action-noun suffix -tus", "نُزعت -tus المصرح بها؛ بقي f-r.", "enjoyment, delight, satisfaction", "مباشر: الفرح والسرور"),
    record("latin", "kaikki_latin:71218:en-nequitia-la-noun-UZpccHyM", "nequitia", "", "نك", "نكر", ["n", "k"], [], "Latin nēquam", "مادة الاسم المجردة لا تغير أول صامتين n-k؛ لا يُطلب صامت ثالث.", "a bad moral quality; idleness, negligence, inactivity, remissness; worthlessness; vileness, depravity, wickedness", "مدار 7: صفة المنكر والحال المذمومة", "NUCLEUS-ECHO"),

    record("persian", "kaikki_persian_2026_07_23:5131:en-بریدن-fa-verb-1M9vpHcE", "بریدن", "burīdan", "بر", "برد", ["b", "r"], [], "Middle Persian brydan, brīdan", "نهاية المصدر الفارسي لا تغير أول صامتين b-r.", "to cut", "مباشر: السحل والنحت والقطع"),
    record("persian", "kaikki_persian_2026_07_23:1448:en-شکستن-fa-verb-uvkE5ojw", "شکستن", "šekastan", "شق", "شقق", ["sh", "k"], ["GUT-01"], "Middle Persian škastan < Proto-Iranian *skand-", "نهاية المصدر لا تدخل؛ اللب الأول sh-k.", "to break", "مباشر: الشق والصدع والكسر"),
    record("persian", "kaikki_persian_2026_07_23:15135:en-شاریدن-fa-verb-~ZOa8myq", "شاریدن", "šâridan", "شر", "شرب", ["sh", "r"], [], "Proto-Iranian *gžárati < Proto-Indo-European *dʰgʷʰéreti", "نهاية المصدر لا تدخل؛ اللب الأول sh-r.", "to pour, trickle", "مدار 8: جريان السائل جزء من حدث الشرب، والنواة المجمدة انتشار"),

    record("gothic", "kaikki_gothic_2026_07_23:588:en-𐌼𐌹𐌻𐌿𐌺𐍃-got-noun-iCXnZTD4", "𐌼𐌹𐌻𐌿𐌺𐍃", "miluks", "مل", "ملح", ["m", "l"], [], "Proto-Germanic *meluks < Proto-Indo-European *h₂melǵ-", "الصورة القوطية والسلف المنشور يحفظان m-l.", "milk", "مباشر: اللبن والرضاع"),
    record("gothic", "kaikki_gothic_2026_07_23:16631:en-𐌳𐍂𐌹𐌿𐍃𐌰𐌽-got-verb-DuIlsxVc", "𐌳𐍂𐌹𐌿𐍃𐌰𐌽", "driusan", "دل", "دلك", ["d", "r"], ["LIQ-01"], "Proto-Germanic *dreusaną", "مادة المصدر القوطية لا تغير اللب d-r.", "to fall", "مباشر: الهبوط والميل إلى الغروب"),
    record("gothic", "kaikki_gothic_2026_07_23:21681:en-𐌷𐌰𐌻𐍄𐍃-got-adj-KwRUxQ5s", "𐌷𐌰𐌻𐍄𐍃", "halts", "عر", "عرج", ["h", "l"], ["GUT-04", "LIQ-01"], "Proto-Germanic *haltaz", "نهاية الصفة لا تدخل؛ اللب h-l.", "lame, limp", "مباشر: العرج والظلع"),
    record("gothic", "kaikki_gothic_2026_07_23:17097:en-𐌷𐍂𐍉𐍄-got-noun-0aDW9HB0", "𐌷𐍂𐍉𐍄", "hrōt", "عر", "عرش", ["h", "r"], ["GUT-04"], "Proto-Germanic *hrōtą", "اللب h-r؛ الصامت الثالث القوطي لا يُطلب في العربية.", "roof", "مباشر: سقف البيت"),
    record("gothic", "kaikki_gothic_2026_07_23:20195:en-𐌷𐌿𐌻𐌾𐌰𐌽-got-verb-HU5sSdEZ", "𐌷𐌿𐌻𐌾𐌰𐌽", "huljan", "غل", "غلف", ["h", "l"], ["GUT-04"], "Proto-Germanic *huljaną", "مادة المصدر لا تغير اللب h-l.", "to cover, wrap, veil", "مباشر: الغلاف والاشتمال والتغطية"),
    record("gothic", "kaikki_gothic_2026_07_23:11311:en-𐌷𐌰𐌽𐍃𐌰-got-noun-EDqxpkHG", "𐌷𐌰𐌽𐍃𐌰", "hansa", "غم", "غمر", ["h", "n"], ["GUT-04", "LIQ-02"], "Proto-Germanic *hansō", "النهاية الاسمية لا تدخل؛ اللب h-n.", "a crowd, gathering", "مباشر: زحمة الناس وجمعهم المتكاثف"),
    record("gothic", "kaikki_gothic_2026_07_23:12267:en-𐌷𐌰𐌿𐍂𐌳𐍃-got-noun-CrJPGypJ", "𐌷𐌰𐌿𐍂𐌳𐍃", "haurds", "غل", "غلق", ["h", "r"], ["GUT-04", "LIQ-01"], "Proto-Germanic *hurdiz", "اللب h-r؛ بقية الصوامت لا تدخل حكم النواة.", "a door, especially of wickerwork", "مدار 4: الباب آلة الإغلاق"),

    record("old_norse", "kaikki_old_norse_2026_07_23:3776:en-mjǫlk-non-noun-iCXnZTD4", "mjǫlk", "", "مل", "ملح", ["m", "l"], [], "Proto-Germanic *meluks < Proto-Indo-European *h₂melǵ-", "استُعملت الصورة المستعادة المنشورة *meluks، فلبها m-l؛ لم يُختلق صف لتجاوز j السطحية.", "milk", "مباشر: اللبن والرضاع", comparison_basis="published-restored-form"),
    record("old_norse", "kaikki_old_norse_2026_07_23:845:en-bita-non-verb-suWMuYsI", "bita", "", "بت", "بتر", ["b", "t"], [], "Old Norse bit or biti, internal family proposed by the source", "نهاية المصدر لا تغير اللب b-t.", "to cut into bits", "مباشر: القطع والبتر"),
    record("old_norse", "kaikki_old_norse_2026_07_23:2211:en-drjúpa-non-verb-IXANu-gK", "drjúpa", "", "دل", "دلك", ["d", "r"], ["LIQ-01"], "Proto-Germanic *dreupaną", "نهاية المصدر لا تغير اللب d-r.", "to drip, fall in drops", "مباشر: الانحدار والسقوط إلى أسفل"),
    record("old_norse", "kaikki_old_norse_2026_07_23:7436:en-haltr-non-adj-p4iQmwmq", "haltr", "", "عر", "عرج", ["h", "l"], ["GUT-04", "LIQ-01"], "Proto-Germanic *haltaz", "نهاية الصفة لا تدخل؛ اللب h-l.", "limp, lame", "مباشر: العرج والظلع"),
    record("old_norse", "kaikki_old_norse_2026_07_23:652:en-hurð-non-noun-JTTi3h3s", "hurð", "", "غل", "غلق", ["h", "r"], ["GUT-04", "LIQ-01"], "Proto-Germanic *hurdiz", "اللب h-r؛ الصامت الأخير لا يدخل حكم النواة.", "door", "مدار 4: الباب آلة الإغلاق"),
    record("old_norse", "kaikki_old_norse_2026_07_23:1522:en-hylja-non-verb-ZXf~Ytbv", "hylja", "", "غل", "غلف", ["h", "l"], ["GUT-04"], "Proto-Germanic *huljaną", "مادة المصدر لا تغير اللب h-l.", "to hide, cover", "مباشر: الغلاف والاشتمال والتغطية"),

    record("welsh", "kaikki_welsh_2026_07_23:4054:en-blith-cy-noun-kYjiFUss", "blith", "", "مل", "ملح", ["b", "l"], ["LAB-04"], "Proto-Brythonic *bliθ, with Proto-Celtic *mlixtus < Proto-Indo-European *h₂melǵ-", "السطح يعطي b-l بمسار LAB-04؛ والسلف المنشور يعيد m-l شاهدًا مستقلًا.", "milk, dairy produce", "مباشر: اللبن والرضاع"),
    record("welsh", "kaikki_welsh_2026_07_23:1623:en-taro-cy-verb-1wo8DkbM", "taro", "", "طر", "طرف", ["t", "r"], ["DENT-05"], "Proto-Indo-European *terh₁-", "نهاية الفعل لا تغير اللب t-r؛ فُصل هذا العضو عن الاسم الدخيل متحد الرسم taro.", "to strike, hit", "مباشر: الضرب"),
    record("welsh", "kaikki_welsh_2026_07_23:201:en-ban-cy-noun-OQ~bcYgd", "ban", "", "فن", "فند", ["b", "n"], ["LAB-02"], "Proto-Brythonic *bann < Proto-Celtic *bandā", "اللب b-n؛ الصامت التاريخي اللاحق لا يُطلب في العربية.", "peak, summit", "مباشر: رأس الجبل العظيم وشمراخه"),
    record("welsh", "kaikki_welsh_2026_07_23:2202:en-galar-cy-noun-S4GIRMDG", "galar", "", "جل", "جلب", ["g", "l"], ["GUT-03"], "Proto-Brythonic *galar < Proto-Celtic *galarom", "اللب g-l؛ الراء الثالثة لا تدخل حكم النواة.", "mourning, grief, sorrow, lament", "مدار 8: الندب والصياح جزء من حدث الحداد", "NUCLEUS-ECHO"),
]

REJECTIONS = [
    {"language": "ancient_greek", "form": "κάμηλος", "status": "SEMITIC-SOURCE-TRANSMISSION", "reason": "مصدره Proto-West Semitic مسمى، وبطاقته الانتقالية السابقة تبقى خارج بسط الوراثة."},
    {"language": "ancient_greek", "form": "ὅρκιον", "status": "DIRECTION-GAP", "reason": "المعنى قريب من الحلف، لكن حقل الاشتقاق لا يغلق جهة السلسلة."},
    {"language": "ancient_greek", "form": "ἐπιτομή / ἀπότομος", "status": "MORPHOLOGY-BLOCKED", "reason": "الصامتان المسترجعان يقعان في السابقة، فلا يقاسان بنواة الجذع."},
    {"language": "latin", "form": "albus", "status": "SOURCE-GAP", "reason": "معنى البياض لم يثبت بالدقة نفسها في المصدرين العربيين للمادة المرشحة."},
    {"language": "latin", "form": "con- / de- / ad- families", "status": "MORPHOLOGY-BLOCKED", "reason": "استبعدت الأسر التي امتلكت السابقة صامتَي المقارنة."},
    {"language": "persian", "form": "رنگ", "status": "TOOL-GAP", "reason": "النواة المرشحة بلا قراءة مجمدة، فلا يصدر حكم."},
    {"language": "persian", "form": "برف", "status": "SEMANTIC-PRUNED", "reason": "الثلج شاهد للبرد، لكنه لا يحقق قراءة بر المجمدة بلا خطوة زائدة."},
    {"language": "persian", "form": "تیر", "status": "HISTORICAL-STRATUM-GAP", "reason": "السهم قوي على السطح، لكن الصورة التاريخية tigr تجعل تعيين أول صامتين غير مغلق هنا."},
    {"language": "persian", "form": "فروغ", "status": "MORPHOLOGY-BLOCKED", "reason": "السابقة التاريخية *fra- تملك صامتَي المقارنة."},
    {"language": "gothic", "form": "swinþei", "status": "SEMANTIC-PRUNED", "reason": "طريق الصوت موقع، لكن حقل النواة وشاهدي العربية لا يحملان القوة بلا تليين."},
    {"language": "old_norse", "form": "flysja", "status": "DIRECTION-GAP", "reason": "معنى الشق قوي، لكن حقل الاشتقاق فارغ فلا يغلق مسار السلسلة."},
    {"language": "old_norse", "form": "drepa", "status": "LAW-GAP", "reason": "تبقى نواة دف محجوبة لغياب صف مباشر صالح لـp↔ف في هذا الفرع."},
    {"language": "welsh", "form": "estyn", "status": "LOANWORD-THIRD-PARTY-TO-BRANCH", "reason": "القرض اللاتيني مسجل سابقًا ولا يدخل بسط الوراثة."},
]


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def normalize_arabic(value: str) -> str:
    value = re.sub(r"[^ء-ي]", "", nfc(value))
    return value.translate(str.maketrans({"أ": "ء", "إ": "ء", "آ": "ء"}))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def core_rows() -> dict[str, dict[str, Any]]:
    payload = json.loads(CORE_PATH.read_text(encoding="utf-8"))
    rows = {}
    for row in payload["levels"]["level_2_binary_nuclei"]["nuclei"]:
        nucleus = normalize_arabic(str(row["nucleus"]))
        if len(nucleus) == 2:
            rows[nucleus] = row
    return rows


def route_covers_pair(tokens: list[str], nucleus: str, rule_ids: list[str]) -> bool:
    rules = {rule.row_id: rule for rule in compile_network(NETWORK_PATH)}
    graph: dict[str, set[str]] = defaultdict(set)
    for arabic, foreign_tokens in IDENTITY.items():
        for foreign in foreign_tokens:
            graph[arabic].add(foreign)
            graph[foreign].add(arabic)
    for row_id in rule_ids:
        if row_id not in rules:
            return False
        rule = rules[row_id]
        for left in rule.left_tokens:
            for right in rule.right_tokens:
                graph[left].add(right)
                graph[right].add(left)

    def reaches(source: str, target: str) -> bool:
        queue = [source]
        seen = {source}
        while queue:
            current = queue.pop()
            if current == target:
                return True
            for neighbour in graph.get(current, ()):
                if neighbour not in seen:
                    seen.add(neighbour)
                    queue.append(neighbour)
        return False

    return len(tokens) == 2 and len(nucleus) == 2 and all(
        reaches(tokens[index], letter) for index, letter in enumerate(nucleus)
    )


def arabic_sources() -> dict[str, set[str]]:
    table = pq.read_table(ARABIC_PATH, columns=["root", "book_name"])
    result: dict[str, set[str]] = defaultdict(set)
    for row in table.to_pylist():
        root = normalize_arabic(str(row["root"]))
        source = nfc(str(row["book_name"]))
        if source in SOURCE_NAMES:
            result[root].add(source)
    return result


def source_entries() -> dict[str, dict[str, Any]]:
    wanted = {row["member_id"] for row in RECORDS}
    found: dict[str, dict[str, Any]] = {}
    for language, metadata in LANGUAGES.items():
        ids = [row["member_id"] for row in RECORDS if row["language"] == language]
        con = sqlite3.connect(
            f"file:{(ROOT / str(metadata['db'])).resolve().as_posix()}?mode=ro",
            uri=True,
        )
        con.row_factory = sqlite3.Row
        try:
            for member_id in ids:
                row = con.execute(
                    "SELECT entry_id, headword, romanization, pos, gloss, etymology, "
                    "tokens_json, form_of, alternative_of, loan_hint FROM entries WHERE entry_id=?",
                    (member_id,),
                ).fetchone()
                if row is None:
                    raise RuntimeError(f"missing source member {member_id}")
                found[member_id] = dict(row)
        finally:
            con.close()
    if set(found) != wanted:
        raise RuntimeError("source member set mismatch")
    return found


def validate(records: list[dict[str, Any]]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    if len({row["member_id"] for row in records}) != len(records):
        raise RuntimeError("duplicate member adjudication")
    cores = core_rows()
    sources = arabic_sources()
    entries = source_entries()
    for row in records:
        if row["nucleus"] not in cores:
            raise RuntimeError(f"missing frozen nucleus {row['nucleus']}")
        reading = nfc(str(cores[row["nucleus"]].get("jabal_lexicon_reading_ar") or cores[row["nucleus"]].get("composed_reading_ar") or "")).strip()
        if not reading:
            raise RuntimeError(f"unread frozen nucleus {row['nucleus']}")
        row["nucleus_reading_ar"] = reading
        if sources.get(normalize_arabic(row["support_root"])) != SOURCE_NAMES:
            raise RuntimeError(f"incomplete Arabic source support {row['support_root']}")
        if row["support_root"] not in ARABIC_EVIDENCE:
            raise RuntimeError(f"missing human Arabic evidence {row['support_root']}")
        if not route_covers_pair(row["comparison_tokens"], row["nucleus"], row["licensed_rules"]):
            raise RuntimeError(f"unlicensed route {row['member_id']} {row['nucleus']}")
        entry = entries[row["member_id"]]
        if nfc(str(entry["headword"])) != row["form"]:
            raise RuntimeError(f"headword drift {row['member_id']}")
        if int(entry["form_of"] or 0) or int(entry["alternative_of"] or 0) or int(entry["loan_hint"] or 0):
            raise RuntimeError(f"filtered member leaked into verdict {row['member_id']}")
        source_gloss = nfc(str(entry["gloss"] or "")).lower()
        if row["branch_meaning"].lower() not in source_gloss and source_gloss not in row["branch_meaning"].lower():
            raise RuntimeError(f"gloss drift {row['member_id']}: {source_gloss!r}")
        if LONG_DASH in json.dumps(row, ensure_ascii=False):
            raise RuntimeError(f"long dash in published record {row['member_id']}")
    return cores, entries


def route_text(row: dict[str, Any]) -> str:
    if not row["licensed_rules"]:
        return "هوية صوتية صريحة في الصامتين"
    return " + ".join(row["licensed_rules"])


def render_card(row: dict[str, Any], entry: dict[str, Any]) -> str:
    language = LANGUAGES[row["language"]]
    display = row["form"] + (f" ({row['romanization']})" if row["romanization"] else "")
    pair = "-".join(row["comparison_tokens"])
    arabic_pair = "-".join(row["nucleus"])
    trace_softness = (
        "الرجل الدلالية ليّنة لأن قراءة النواة المجمدة أوسع من شاهد المادة؛ لذلك خُفّض الحكم إلى صدى."
        if row["verdict"] == "NUCLEUS-ECHO"
        else "الأرجل الثلاث مكتملة: مسار الصوت، وقراءة النواة، والمدار ذو الشاهدين."
    )
    return nfc(f"""
### بطاقة: `{row['member_id']}`، {display} (إعادة القراءة بعين النواة)
- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14) + SECTION28-TWO-LAYER (2026-08-01)؛ خط البرهان مجمد.
- الكلمةُ في الفرع: {display} [{entry['pos']}؛ `{row['member_id']}`].
- أقدمُ صورةٍ مستعادة: {row['oldest_form']} [{language['source']}؛ حقل الاشتقاق].
- الخطوةُ صفر (التعرية بصرف الفرع): {row['zero_step']}
- درجةُ المقارنة: النواة مستقلة من أول القراءة؛ لا يشترط توافق الصامت الثالث.
- نتيجةُ طبقة الجذر: غير صادر في هذه البطاقة؛ لم تُستعمل زيادة صامت ثالث لرفع الحكم.
- نتيجةُ طبقة النواة: `{pair} ↔ {arabic_pair}`؛ النواة المجمدة `{row['nucleus']}` «{row['nucleus_reading_ar']}»؛ الحكم `{row['verdict']}`.
- مسحُ المعاني العربيّة: {ARABIC_EVIDENCE[row['support_root']]} [لسان العرب لابن منظور؛ تاج العروس لمرتضى الزبيدي].
- المقابلُ من اللسان: `{row['nucleus']}` بشاهد المادة `{row['support_root']}` في المصدرين القديمين.
- مسارُ الصوت: {route_text(row)}؛ أساس المقارنة `{row['comparison_basis']}`؛ لا مرساة فمية ولا صف جديد.
- المعنى من قاموس الفرع: «{row['branch_meaning']}» [{language['source']}].
- المدار: {row['orbit']}.
- المصفاة: لا مانح سامي أو أجنبي بعد الافتراق مسمى لهذا العضو؛ السلف المنشور فرعي أو أقدم منه.
- فصلُ المتجانسات والاقتراض: الحكم لهذا العضو ومعناه وحده؛ لا يرثه متحد الرسم ولا المشتق ولا القريب الدلالي.
- مؤشر اليتم: غير مستعمل في إصدار الحكم.
- إشعاع الأسرة في الفرع: الأعضاء المعجمية المدعومة=1؛ سلاسل المعنى المدعومة=1؛ حُد الدعم بهذا العضو.
- إشعاع الأسرة في العربية: الأعضاء المعجمية المدعومة=1 (`{row['support_root']}`)؛ سلاسل المعنى المدعومة=1؛ الشاهدان مسميان.
- جسورُ الاسترداد المفحوصة: التعرية؛ أقدم صورة؛ أول صامتين؛ النواة المجمدة؛ الصفوف الموقعة؛ مروحة المادة في المصدرين؛ المدار؛ حقل الاقتراض.
- حالةُ الإغلاق: READY على طبقة النواة.
- الحكم (استكشاف): {row['verdict']}.
- عدسة الاسترداد: أعادت النواة الثنائية العضو من سجل `OPEN-CANDIDATE` من غير طلب الصامت الثالث.
- عدسة التشكيك: {trace_softness}
- ملاحظات: هذا حكم استكشافي لا نتيجة تحقق مقيس؛ لا يدخل أي `SEMITIC-SOURCE-TRANSMISSION` في بسطه.
""").strip()


def reading_blocks(entries: dict[str, dict[str, Any]]) -> dict[str, str]:
    blocks = {}
    for language, metadata in LANGUAGES.items():
        rows = [row for row in RECORDS if row["language"] == language]
        cards = "\n\n".join(render_card(row, entries[row["member_id"]]) for row in rows)
        blocks[language] = nfc(
            f"\n\n<!-- {MARKER}:{language} -->\n"
            f"## إعادة القراءة بعين النواة: {metadata['label']}\n\n"
            "- النطاق: الجرد المعجمي الكامل السابق بعد فراغ الطابور، مع استرجاع مستقل لأول صامتين ومراجعة بشرية للمدار.\n"
            "- الحارس: الأشكال التصريفية والبدائل والقروض الصريحة مستبعدة؛ الهوية حرفية، وكل إبدال آخر من صف موقع.\n"
            "- المصدران العربيان في كل بطاقة: لسان العرب لابن منظور وتاج العروس لمرتضى الزبيدي.\n"
            "- الطبقة: استكشاف؛ لا تُقرأ أعداد البطاقات معدل تحقق أو دليلًا إحصائيًا.\n\n"
            f"{cards}\n\n"
            f"<!-- /{MARKER}:{language} -->\n"
        )
    return blocks


def promotion_row(row: dict[str, Any], core_hash: str, network_hash: str) -> dict[str, Any]:
    return {
        "member_id": row["member_id"],
        "language": row["language"],
        "form": row["form"],
        "layer": "nucleus",
        "verdict": row["verdict"],
        "nucleus": row["nucleus"],
        "support_root": row["support_root"],
        "branch_source_form": row["oldest_form"],
        "branch_meaning": row["branch_meaning"],
        "comparison_tokens": row["comparison_tokens"],
        "comparison_basis": row["comparison_basis"],
        "licensed_rules": row["licensed_rules"],
        "orbit": row["orbit"],
        "classical_sources": sorted(SOURCE_NAMES),
        "core_sha256": core_hash,
        "network_sha256": network_hash,
        "date": DATE,
    }


def make_adjudication(ranking: dict[str, Any], core_hash: str, network_hash: str) -> dict[str, Any]:
    language_rows = {}
    for language, metadata in LANGUAGES.items():
        rows = [row for row in RECORDS if row["language"] == language]
        ranked = ranking["languages"][language]
        language_rows[language] = {
            "label": metadata["label"],
            "source_member_denominator": metadata["denominator"],
            "source_queue_remaining": 0,
            "candidate_bearing_lexical_members_after_strict_route": ranked["candidate_bearing_lexical_members_after_route_filter"],
            "entry_nucleus_pairs_after_strict_route": ranked["entry_nucleus_pairs_after_route_filter"],
            "human_positive_cards": len(rows),
            "distinct_positive_nuclei": len({row["nucleus"] for row in rows}),
            "verdicts": dict(Counter(row["verdict"] for row in rows)),
        }
    return {
        "schema": "lane-c-nucleus-reread-adjudications-v1",
        "date": DATE,
        "truth_layer": "exploration; operational counts are not verification rates",
        "contract": {
            "comparison": "binary nucleus from the start",
            "third_consonant": "not required",
            "sound": "literal identity or signed frozen rows only",
            "meaning": "one named orbit only",
            "arabic_sources": sorted(SOURCE_NAMES),
            "loans": "SEMITIC-SOURCE-TRANSMISSION remains outside inheritance numerator",
            "shared_tools": "none invoked; shared inventories read-only",
        },
        "pins": {
            "core_sha256": core_hash,
            "network_sha256": network_hash,
            "arabic_roots_sha256": sha256(ARABIC_PATH),
            "ranking_source_sha256": sha256(RANKING_PATH),
        },
        "frozen_nuclei_with_reading_and_two_graphemes": ranking["frozen_nuclei_with_reading_and_two_graphemes"],
        "frozen_nuclei_with_two_named_arabic_source_support": ranking["frozen_nuclei_with_two_named_arabic_source_support"],
        "languages": language_rows,
        "positives": RECORDS,
        "recorded_rejections": REJECTIONS,
    }


def render_audit(adjudication: dict[str, Any]) -> str:
    table_rows = []
    for language, metadata in LANGUAGES.items():
        row = adjudication["languages"][language]
        verdicts = row["verdicts"]
        table_rows.append(
            f"| {metadata['label']} | {row['source_member_denominator']} | "
            f"{row['candidate_bearing_lexical_members_after_strict_route']} | "
            f"{row['entry_nucleus_pairs_after_strict_route']} | {row['human_positive_cards']} | "
            f"{row['distinct_positive_nuclei']} | {verdicts.get('NUCLEUS-TRACE', 0)} | "
            f"{verdicts.get('NUCLEUS-ECHO', 0)} |"
        )
    rejections = "\n".join(
        f"- **{LANGUAGES[row['language']]['label']}، `{row['form']}`:** `{row['status']}`؛ {row['reason']}"
        for row in REJECTIONS
    )
    return nfc(f"""# محضر إعادة قراءة المسار ج بعين النواة

**التاريخ:** {DATE}. **طبقة الحقيقة:** استكشاف، لا تحقق مقيس.

هذا المحضر يستدرك خاتمة شهر الطبقتين التي قالت إن اللاتينية والقوطية والويلزية واليونانية لم تخرج منها نواة أخرى. كان ذلك إغلاقًا لقراءة جعلت الاسترجاع الثنائي تابعًا لترتيب الجذر. في هذه الجولة صار أول صامتين وحدة البحث من البداية، مع تعرية صرف الفرع، ثم الطريق الصوتي الموقع، ثم مدار واحد، ثم شاهد المادة في مصدرين عربيين قديمين مسميين.

## نطاق الجرد ونتيجة الإيداع

| اللسان | مقام المصدر | أعضاء بعد حارس الطريق | أزواج عضو/نواة | بطاقات صادرة | نوى متميزة | TRACE | ECHO |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(table_rows)}

الأرقام في الجدول أعداد سجل تشغيلية قابلة للتدقيق، وليست معدل صلة ولا نتيجة إحصائية. مقام المصدر هو الجرد الكامل الذي فرغ طابوره سابقًا، والباقي منه 0 في الألسن الستة. مر كل عضو معجمي صالح في استرجاع أول الصامتين؛ أمّا الحكم البشري فلم يصدر إلا للأعضاء المودعة في بطاقاتها.

## ما غيّرته عين النواة

- أسرة الحلب ظهرت في اليونانية `ἀμέλγω`، واللاتينية `mulgeo`، والقوطية `miluks`، والنوردية `mjǫlk` من الصورة المستعادة `*meluks`، والويلزية `blith` مع شاهد `*mlixtus`. المقابل `مل/ملح`، والمصدران يقولان إن الملح الرضاع.
- لم يُطلب الصامت الثالث في `زوج` و`بطح` و`سطح` و`بتر` و`برد` و`شقق` و`دلك` و`عرج` و`عرش` و`غلف` و`غمر` و`غلق` و`طرف` و`فند` و`جلب`.
- قُيّد `nequitia` و`galar` بـ`NUCLEUS-ECHO` لأن رجل الحقل ألين من بقية الأرجل؛ لم يُرفع الصدى إلى أثر لمجرد زيادة العائد.
- بقيت بطاقة `hamr ↔ غم` السابقة نافذة، ولم تُكرر في هذه الدفعة.

## المقلّم المحفوظ

{rejections}

## الحراس

- فهرس الاسترجاع رتب المرشحين فقط، وحالته `RANKED-FOR-HUMAN-ORBIT-REVIEW; NOT-A-VERDICT`؛ الدرجة العددية لم تدخل حكمًا.
- استُبعدت الأشكال التصريفية والبدائل والقروض الصريحة قبل الاسترجاع، واستُبعد كل طريق لا يغطي الصامتين كاملين بهوية حرفية أو صف موقع.
- كل مادة عربية مودعة موجودة في **لسان العرب لابن منظور** و**تاج العروس لمرتضى الزبيدي**، والنص الدلالي نفسه مسجل في البطاقة.
- بقيت مرورات `SEMITIC-SOURCE-TRANSMISSION` السابقة، وعددها التشغيلي 4,421، خارج بسط الوراثة. لم يُعد تصنيف واحدة منها أثرًا.
- لم يُنشأ صف صوتي، ولم تعدل نواة مجمدة، ولم تشغل أداة مشتركة. فتحت قواعد الجرد للقراءة فقط.
- نُقلت الأعضاء المرقاة من `lane_c_coverage.jsonl` إلى سجل الأحكام، فلا يجتمع `OPEN-CANDIDATE` وحكم موجب على العضو نفسه.

## الملفات المثبتة

- ترتيب الاسترجاع غير الحاكم: `04-cross-linguistic/data/lane_c_nucleus_reread_ranked.json`.
- الأحكام والمقلّم بصيغة قابلة للآلة: `04-cross-linguistic/data/lane_c_nucleus_reread_adjudications.json`.
- سطور الأحكام: `04-cross-linguistic/data/lane_c_two_layer_semantic_promotions.jsonl`.
- البطاقات: ملفات القراءات الستة في `04-cross-linguistic/readings/`.

*English abstract.* Lane C's six distant branches were reread with the binary nucleus as the initial comparison unit. Inflectional rows, alternatives, explicit loans, incomplete sound routes, prefix-owned pairs, and unsupported semantic shortcuts were excluded. Every issued card has a literal or signed sound route, one named semantic orbit, and support from both Lisan al-Arab and Taj al-Arus. Semitic-source transmissions remain outside the inheritance numerator. The counts above are operational ledger counts, not a verification result.
""")


def append_readings(blocks: dict[str, str]) -> None:
    for language, block in blocks.items():
        path = ROOT / "04-cross-linguistic" / "readings" / str(LANGUAGES[language]["reading"])
        text = path.read_text(encoding="utf-8")
        marker = f"<!-- {MARKER}:{language} -->"
        if marker not in text:
            with path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(block)
        elif text.count(marker) != 1:
            raise RuntimeError(f"duplicate reading marker {language}")


def append_promotions(rows: list[dict[str, Any]]) -> None:
    existing_lines = PROMOTIONS_PATH.read_text(encoding="utf-8").splitlines()
    existing_ids = {
        json.loads(line)["member_id"] for line in existing_lines if line.strip()
    }
    additions = [row for row in rows if row["member_id"] not in existing_ids]
    if additions:
        with PROMOTIONS_PATH.open("a", encoding="utf-8", newline="\n") as handle:
            for row in additions:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def remove_from_coverage(member_ids: set[str]) -> None:
    temporary = COVERAGE_PATH.with_suffix(".nucleus-reread.tmp")
    removed = Counter()
    with COVERAGE_PATH.open(encoding="utf-8") as source, temporary.open("w", encoding="utf-8", newline="\n") as target:
        for line in source:
            match = re.match(r'^\{"member_id":"([^"]+)"', line)
            if match and match.group(1) in member_ids:
                removed[match.group(1)] += 1
                continue
            target.write(line)
    invalid = {member_id: count for member_id, count in removed.items() if count != 1}
    missing = member_ids - set(removed)
    if invalid or missing:
        temporary.unlink(missing_ok=True)
        # An idempotent rerun after successful removal is valid only if every
        # promoted id is already absent.  Mixed state is not silently accepted.
        if not removed and missing == member_ids:
            return
        raise RuntimeError(f"coverage removal mismatch invalid={invalid} missing={sorted(missing)}")
    temporary.replace(COVERAGE_PATH)


def final_validate(member_ids: set[str]) -> None:
    promotion_ids = []
    for line in PROMOTIONS_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            member_id = json.loads(line)["member_id"]
            if member_id in member_ids:
                promotion_ids.append(member_id)
    if Counter(promotion_ids) != Counter({member_id: 1 for member_id in member_ids}):
        raise RuntimeError("promotion ledger multiplicity mismatch")
    coverage_hits = set()
    with COVERAGE_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            match = re.match(r'^\{"member_id":"([^"]+)"', line)
            if match and match.group(1) in member_ids:
                coverage_hits.add(match.group(1))
    if coverage_hits:
        raise RuntimeError(f"promotions remain in non-issuance ledger: {sorted(coverage_hits)}")
    for language in LANGUAGES:
        path = ROOT / "04-cross-linguistic" / "readings" / str(LANGUAGES[language]["reading"])
        text = path.read_text(encoding="utf-8")
        if text.count(f"<!-- {MARKER}:{language} -->") != 1:
            raise RuntimeError(f"missing or duplicate final reading block {language}")
    for path in [ADJUDICATION_PATH, AUDIT_PATH, PROMOTIONS_PATH]:
        text = path.read_text(encoding="utf-8")
        if text != nfc(text):
            raise RuntimeError(f"non-NFC output {path}")
        if LONG_DASH in text:
            raise RuntimeError(f"long dash in output {path}")


def main() -> int:
    ranking = json.loads(RANKING_PATH.read_text(encoding="utf-8"))
    core_hash = sha256(CORE_PATH)
    network_hash = sha256(NETWORK_PATH)
    if ranking["pins"]["core_sha256"] != core_hash or ranking["pins"]["network_sha256"] != network_hash:
        raise RuntimeError("ranking pins drifted")
    _, entries = validate(RECORDS)
    adjudication = make_adjudication(ranking, core_hash, network_hash)
    blocks = reading_blocks(entries)
    promotion_rows = [promotion_row(row, core_hash, network_hash) for row in RECORDS]

    ADJUDICATION_PATH.write_text(
        json.dumps(adjudication, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    AUDIT_PATH.write_text(render_audit(adjudication), encoding="utf-8", newline="\n")
    append_readings(blocks)
    append_promotions(promotion_rows)
    member_ids = {row["member_id"] for row in RECORDS}
    remove_from_coverage(member_ids)
    final_validate(member_ids)
    print(f"CLEAN\t{len(RECORDS)} lane-C nucleus adjudications across {len(LANGUAGES)} languages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
