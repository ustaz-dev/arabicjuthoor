#!/usr/bin/env python3
"""Deposit the six consecutive lane-C basic-first review batches.

The ranking is non-random and denominator-preserving.  This lane-owned
finalizer reads the frozen ranking, records every basic candidate that passed
the distinctive-orbit machine gate, issues only the two human-positive cards,
and moves those two members from the non-issuance ledger to the issued ledger.
It does not call a shared builder and is safe to rerun.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-08-01"
MARKER = "LANE-C-BASIC-FIRST-2026-08-01"
RANKING = ROOT / "04-cross-linguistic" / "data" / "lane_c_nucleus_reread_ranked.json"
REVIEWS = ROOT / "04-cross-linguistic" / "data" / "lane_c_basic_first_reviews.jsonl"
PROMOTIONS = ROOT / "04-cross-linguistic" / "data" / "lane_c_two_layer_semantic_promotions.jsonl"
COVERAGE = ROOT / "04-cross-linguistic" / "data" / "lane_c_coverage.jsonl"
CORE = ROOT / "data" / "juthoor-core-levels.json"
NETWORK = ROOT / "04-cross-linguistic" / "shift-network-draft.md"
ARABIC = ROOT / "Resources" / "arabic_roots_hf" / "train-00000-of-00001.parquet"
AUDIT = ROOT / "05-audits" / "lane-c-2026-08-01-basic-first-batches.md"

SOURCE_NAMES = {
    "لسان العرب لابن منظور",
    "تاج العروس لمرتضى الزبيدي",
}
CARD_FIELDS = (
    "- إصدارُ البروتوكول:",
    "- الكلمةُ في الفرع:",
    "- أقدمُ صورةٍ مستعادة:",
    "- الخطوةُ صفر (التعرية بصرف الفرع):",
    "- درجةُ المقارنة:",
    "- مسحُ المعاني العربيّة:",
    "- المقابلُ من اللسان:",
    "- مسارُ الصوت:",
    "- المعنى من قاموس الفرع:",
    "- المدار:",
    "- المصفاة:",
    "- فصلُ المتجانسات والاقتراض:",
    "- مؤشر اليتم:",
    "- إشعاع الأسرة في الفرع:",
    "- إشعاع الأسرة في العربية:",
    "- جسورُ الاسترداد المفحوصة:",
    "- حالةُ الإغلاق:",
    "- الحكم (استكشاف):",
    "- ملاحظات:",
)

LANGUAGES: dict[str, dict[str, Any]] = {
    "ancient_greek": {
        "label": "اليونانية القديمة",
        "reading": "ancient-greek.md",
        "denominator": 56058,
        "batch": "BASIC-FIRST-01-ANCIENT-GREEK",
    },
    "latin": {
        "label": "اللاتينية",
        "reading": "old-latin.md",
        "denominator": 883915,
        "batch": "BASIC-FIRST-02-LATIN",
    },
    "persian": {
        "label": "الفارسية",
        "reading": "persian.md",
        "denominator": 19361,
        "batch": "BASIC-FIRST-03-PERSIAN",
    },
    "gothic": {
        "label": "القوطية",
        "reading": "gothic.md",
        "denominator": 23005,
        "batch": "BASIC-FIRST-04-GOTHIC",
    },
    "old_norse": {
        "label": "النوردية القديمة",
        "reading": "old-norse.md",
        "denominator": 11169,
        "batch": "BASIC-FIRST-05-OLD-NORSE",
    },
    "welsh": {
        "label": "الويلزية",
        "reading": "welsh.md",
        "denominator": 27715,
        "batch": "BASIC-FIRST-06-WELSH",
    },
}


def reject(status: str, reason: str) -> tuple[str, str]:
    return status, reason


# These are the complete human decisions for the basic-vocabulary candidates
# that passed the distinctive-orbit machine gate in this frozen run.  Matching
# is by language and exact source form; the finalizer requires a one-to-one
# match against the member IDs in the ranking before writing anything.
FORM_DECISIONS: dict[str, dict[str, tuple[str, str]]] = {
    "ancient_greek": {
        "ῥύγχος": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "حمل لفظ muzzle الاسترجاع إلى رمح، لكن الأنف نفسه لا يقع في مدار رم المجمّد."),
        "αἷμα": reject("SOURCE-GAP", "حقل الأصل يصرح بأن الاشتقاق متنازع وفيه نظريات متنافسة، ومدار عن لا يميز الدم."),
        "ὄνυξ": ("NUCLEUS-ECHO", "مدار مادّي مميز: ظفر أو مخلب أو ظلف صلب مدبب، وتقابله أسرة نق بالنقر والثقب بأداة مدببة."),
        "ὕλη": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "الخشب والغابة لا يثبتان مدار عر؛ جاء التقارب من جوار عرضي في شروح المواد."),
        "μορύσσω": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "التلويث والتلطيخ لا يميزان مدار مر عن منافسيه."),
        "ἀγρυπνέω": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "السهر معنى حال عام، ولا يثبت جوار جلد ولا قراءة جل المجمّدة."),
        "ἧμαι": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "الجلوس والكون في موضع من أكثر الأفعال الثنائية عمومًا، ولم يثبت له مدار عم مميز."),
    },
    "latin": {
        "pantex": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "البطن مجاور للأكل والبلع لكنه ليس مدار بن المجمّد ولا شاهدًا مميزًا له."),
        "spolium": ("NUCLEUS-ECHO", "مدار مادّي مميز: جلد الحيوان المنزوع، وفي أسرة سب سلب الثوب والقشر وتجرد الجلد."),
        "baca": reject("SOURCE-GAP", "المصدر يسوق أصولًا متنافسة ومشكلات صوتية، ومدار الثمرة لا يثبت بق."),
        "silva": reject("SOURCE-GAP", "المصدر نفسه متحفظ في الاشتقاق التقليدي، والخشب لا يثبت مدار سل المجمّد."),
        "mare": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "البحر مجال واسع يطابق مواد الحركة والاختلاط عرضًا ولا يميز مر."),
        "pascua": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "المرعى لا يثبت مدار بس؛ التشابه جاء من جوار معجمي غير خاص."),
        "pascuum": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "صيغة ثانية للمرعى نفسه، ولا تزيد شاهدًا دلاليًا مستقلًا."),
        "falsidicus": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "الكذب لا يقع في مدار فل المجمّد، ولا تكفي دلالة الانفصال العامة."),
        "sopor": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "وافق سبت في النوم، لكن قراءة سب المجمّدة لا تدور على النوم أو السكون؛ تطابق الجذر المفرد لا يكفي."),
    },
    "persian": {
        "کوه": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "الجبل لا يساوي العمق أو القعر، ولم يثبت جوار قع مميز."),
        "مزنه": reject("LOANWORD-THIRD-PARTY", "المصدر يصرح بأن العربية مزنة اقتراض إيراني؛ فلا يعد شاهد وراثة مستقلًا."),
        "مردن": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "الموت من أعم المدارات، وتقارب برد عرضي لا يثبت نواة بر."),
        "مر": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "أداة نحوية بلا مدار معجمي مميز يقابل برح أو قراءة بر."),
    },
    "gothic": {
        "𐌷𐌰𐌻𐍃": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "العنق لا يثبت مدار غل؛ جوار الغلبة أو الطوق ليس معنى العضو نفسه."),
        "𐌼𐌰𐍂𐌴𐌹": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "البحر مجال عام، ولا يميز مر عن كل مواد الحركة والاختلاط."),
    },
    "old_norse": {
        "hals": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "العنق لا يثبت مدار غل المجمّد."),
        "konr": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "الابن والنسل لا يثبتان مدار جن؛ القرابة العامة لا تكفي."),
        "fold": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "الأرض والحقل لا يثبتان مدار فل؛ معنى الانفلاق أوسع من العضو."),
        "elfr": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "النهر لا يثبت مدار رف؛ الجريان معنى عام غير مميز."),
        "holt": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "الخشب لا يثبت مدار عر؛ تقارب السقف أو العريش مجاورة لا ترجمة."),
        "grund": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "الأرض لا تقع في مدار جل المجمّد، والصلابة العامة لا تكفي."),
        "hníga": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "السقوط والحركة من المدارات العامة، ولا يثبتان عن."),
    },
    "welsh": {
        "gwŷdd": reject("SEMANTIC-ORBIT-NOT-DISTINCTIVE", "الأشجار لا تثبت مدار جب أو الجبل؛ المسار الصوتي وحده لا يحكم."),
        "gweryd": reject("SOURCE-GAP", "حقل الاشتقاق فارغ، والأرض لا تثبت مدار جب المجمّد."),
    },
}

POSITIVE_SPECS: dict[str, dict[str, Any]] = {
    "kaikki_ancient_greek:1165:en-ὄνυξ-grc-noun-QUXCOZYD": {
        "nucleus": "نق",
        "support_root": "نقر",
        "comparison_tokens": ["n", "k"],
        "licensed_rules": ["GUT-01"],
        "oldest_form": "Proto-Indo-European *h₃negʰ- (nail)",
        "zero_step": "فُكّت ξ إلى k+s، ثم جُرّدت -s الاسمية اليونانية؛ بقي الصامتان الجذعيان n-k.",
        "orbit": "مادّي مميز: طرف جسدي صلب ومدبب ينقر أو يثقب؛ لا يستعمل معنى القطع أو الحركة العام.",
        "arabic_evidence": "لسان العرب: «نقرت الشيء: ثقبته بالمنقار» والمنقار مقدّم الخف؛ وتاج العروس: النقر ضرب الشيء، ونقر البيضة نقبها.",
        "arabic_family": "نقر، نقب",
    },
    "kaikki_latin:78381:en-spolium-la-noun-kK6b0Qbv": {
        "nucleus": "سب",
        "support_root": "سلب",
        "comparison_tokens": ["s", "p"],
        "licensed_rules": ["LAB-01"],
        "oldest_form": "Proto-Indo-European *(s)pel-",
        "zero_step": "نُزعت النهاية الاسمية اللاتينية -um قبل العد؛ بقي s-p-l، وأُخذت النواة s-p دون طلب الصامت الثالث.",
        "orbit": "مادّي مميز: جلد حيوان نُزع عن جسده؛ لا يستعمل معنى الفصل العام وحده.",
        "arabic_evidence": "لسان العرب: سلبه ثوبه، والأَسلاب قصب قد قشر؛ وتاج العروس: سلب الشيء اختلسه، والشجرة السليب سلبت ورقها وأغصانها.",
        "arabic_family": "سلب، سبأ",
    },
}


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_arabic(value: str) -> str:
    value = re.sub(r"[^ء-ي]", "", nfc(value))
    return value.translate(str.maketrans({"أ": "ء", "إ": "ء", "آ": "ء"}))


def core_rows() -> dict[str, dict[str, Any]]:
    payload = json.loads(CORE.read_text(encoding="utf-8"))
    return {
        normalize_arabic(str(row["nucleus"])): row
        for row in payload["levels"]["level_2_binary_nuclei"]["nuclei"]
        if len(normalize_arabic(str(row["nucleus"]))) == 2
    }


def arabic_sources() -> dict[str, set[str]]:
    table = pq.read_table(ARABIC, columns=["root", "book_name"])
    result: dict[str, set[str]] = defaultdict(set)
    for row in table.to_pylist():
        source = nfc(str(row["book_name"]))
        if source in SOURCE_NAMES:
            result[normalize_arabic(str(row["root"]))].add(source)
    return result


def load_decisions(ranking: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    matched_forms: dict[str, set[str]] = defaultdict(set)
    for language, block in ranking["languages"].items():
        for candidate in block["ranked"]:
            form = candidate["form"]
            if form not in FORM_DECISIONS[language]:
                continue
            if candidate["reading_priority_band"] != 0:
                continue
            if candidate["semantic_orbit_gate"] != "DISTINCTIVE-ORBIT-REVIEW":
                continue
            if form in matched_forms[language]:
                raise RuntimeError(f"duplicate basic decision form {language} {form}")
            matched_forms[language].add(form)
            disposition, reason = FORM_DECISIONS[language][form]
            rows.append(
                {
                    "schema": "lane-c-basic-first-review-v1",
                    "date": DATE,
                    "batch_id": LANGUAGES[language]["batch"],
                    "language": language,
                    "member_id": candidate["member_id"],
                    "form": form,
                    "branch_gloss": candidate["branch_gloss"],
                    "reading_priority": "basic-vocabulary",
                    "basic_categories": candidate["basic_categories"],
                    "reading_order": candidate["reading_order"],
                    "morphology_gate": candidate["morphology_gate"],
                    "morphology_note": candidate["morphology_note"],
                    "comparison_pair": candidate["comparison_tokens"][:2],
                    "nucleus": candidate["nucleus"],
                    "support_root_ranked": candidate["support_root"],
                    "semantic_root_neighbourhood_score": candidate["semantic_root_neighbourhood_score"],
                    "semantic_orbit_margin": candidate["semantic_orbit_margin"],
                    "human_disposition": disposition,
                    "human_reason_ar": reason,
                    "denominator_fate": (
                        "issued-reading-and-promotion-ledgers"
                        if disposition == "NUCLEUS-ECHO"
                        else "retained-in-lane_c_coverage.jsonl"
                    ),
                    "order_policy": "basic-first; explicit; not-random",
                }
            )
    expected = {language: set(items) for language, items in FORM_DECISIONS.items()}
    if dict(matched_forms) != expected:
        missing = {
            language: sorted(expected[language] - matched_forms[language])
            for language in expected
            if expected[language] != matched_forms[language]
        }
        raise RuntimeError(f"basic decision set drift: {missing}")
    if len({row["member_id"] for row in rows}) != len(rows):
        raise RuntimeError("duplicate reviewed member")
    return rows


def validate_positives(
    decisions: list[dict[str, Any]],
    cores: dict[str, dict[str, Any]],
    sources: dict[str, set[str]],
) -> list[dict[str, Any]]:
    positives = [row for row in decisions if row["human_disposition"] == "NUCLEUS-ECHO"]
    if {row["member_id"] for row in positives} != set(POSITIVE_SPECS):
        raise RuntimeError("positive member set drift")
    network_ids = set(re.findall(r"^\| ([A-Z]+-[A-Z0-9-]+) \|", NETWORK.read_text(encoding="utf-8"), re.MULTILINE))
    for row in positives:
        spec = POSITIVE_SPECS[row["member_id"]]
        if row["nucleus"] != spec["nucleus"]:
            raise RuntimeError(f"positive nucleus drift {row['member_id']}")
        if row["comparison_pair"] != spec["comparison_tokens"]:
            raise RuntimeError(f"positive morphology drift {row['member_id']}")
        if not set(spec["licensed_rules"]) <= network_ids:
            raise RuntimeError(f"missing signed route {row['member_id']}")
        core = cores.get(spec["nucleus"])
        if not core or not (core.get("jabal_lexicon_reading_ar") or core.get("composed_reading_ar")):
            raise RuntimeError(f"unread nucleus {spec['nucleus']}")
        if sources.get(normalize_arabic(spec["support_root"])) != SOURCE_NAMES:
            raise RuntimeError(f"Arabic source gap {spec['support_root']}")
    return positives


def route_text(spec: dict[str, Any]) -> str:
    return "هوية حرفية" if not spec["licensed_rules"] else " + ".join(spec["licensed_rules"])


def render_card(row: dict[str, Any], spec: dict[str, Any], core: dict[str, Any]) -> str:
    reading = nfc(str(core.get("jabal_lexicon_reading_ar") or core.get("composed_reading_ar")))
    pair = "-".join(spec["comparison_tokens"])
    arabic_pair = "-".join(spec["nucleus"])
    return nfc(f"""### بطاقة: `{row['member_id']}`، {row['form']} (دفعة الأساسي أولا)
- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14) + SECTION28-TWO-LAYER (2026-08-01) + BASIC-FIRST-v1؛ خط البرهان مجمد.
- الكلمةُ في الفرع: {row['form']} [{row['branch_gloss']}؛ `{row['member_id']}`].
- أقدمُ صورةٍ مستعادة: {spec['oldest_form']} [حقل الاشتقاق في مصدر الفرع].
- الخطوةُ صفر (التعرية بصرف الفرع): {spec['zero_step']}
- درجةُ المقارنة: النواة الثنائية مستقلة من أول القراءة؛ لا يشترط توافق الصامت الثالث.
- نتيجةُ طبقة الجذر: غير صادر؛ لم تستعمل زيادة صامت ثالث لرفع الحكم.
- نتيجةُ طبقة النواة: `{pair} ↔ {arabic_pair}`؛ النواة المجمدة `{spec['nucleus']}` «{reading}»؛ الحكم `NUCLEUS-ECHO`.
- مسحُ المعاني العربيّة: {spec['arabic_evidence']} [لسان العرب لابن منظور؛ تاج العروس لمرتضى الزبيدي].
- المقابلُ من اللسان: `{spec['nucleus']}` بشاهد المادة `{spec['support_root']}` ومروحة الأسرة `{spec['arabic_family']}`.
- مسارُ الصوت: {route_text(spec)}؛ المقارنة بعد التعرية الصرفية؛ لا مرساة فمية ولا صف جديد.
- المعنى من قاموس الفرع: «{row['branch_gloss']}» [سجل Kaikki المحلي المثبت].
- المدار: {spec['orbit']}
- المصفاة: لا قرض صريح إلى الفرع ولا مانح سامي مسمى؛ فُحص اتجاه النقل قبل الإصدار.
- فصلُ المتجانسات والاقتراض: الحكم لهذا العضو ومعناه وحده؛ لا يرثه متحد الرسم ولا القريب الدلالي.
- مؤشر اليتم: غير مستعمل في إصدار الحكم.
- إشعاع الأسرة في الفرع: عضو معجمي مدعوم=1؛ سلسلة معنى مدعومة=1؛ حُد الدعم بهذا العضو.
- إشعاع الأسرة في العربية: مروحة مادية متعددة الجذور (`{spec['arabic_family']}`)؛ شاهد المادة الرئيس `{spec['support_root']}` في المصدرين.
- جسورُ الاسترداد المفحوصة: ترتيب الأساسي؛ التعرية؛ الصورة الأقدم؛ أول صامتين؛ النواة المجمدة؛ الطريق الموقع؛ مروحة المصدرين؛ تميز المدار؛ اتجاه الاقتراض.
- حالةُ الإغلاق: READY على طبقة النواة.
- الحكم (استكشاف): NUCLEUS-ECHO.
- عدسة الاسترداد: رفع الترتيب الأساسي هذا العضو قبل المشتق والمصطلح من غير تغيير المقام.
- عدسة التشكيك: خُفّض الحكم إلى صدى لأن النواة الثنائية أوسع من العضو، مع بقاء المدار المادي مميزًا عن المنافسين.
- ملاحظات: ترتيب القراءة أساسي لا عشوائي؛ العضو انتقل من سجل عدم الإصدار إلى سجل الحكم، وبقي مقام المصدر معلومًا باتحاد السجلين.
""").strip()


def promotion_row(row: dict[str, Any], spec: dict[str, Any], core_hash: str, network_hash: str) -> dict[str, Any]:
    return {
        "member_id": row["member_id"],
        "language": row["language"],
        "form": row["form"],
        "layer": "nucleus",
        "verdict": "NUCLEUS-ECHO",
        "nucleus": spec["nucleus"],
        "support_root": spec["support_root"],
        "branch_source_form": spec["oldest_form"],
        "branch_meaning": row["branch_gloss"],
        "comparison_tokens": spec["comparison_tokens"],
        "comparison_basis": "basic-first; surface-after-branch-morphology",
        "licensed_rules": spec["licensed_rules"],
        "orbit": spec["orbit"],
        "classical_sources": sorted(SOURCE_NAMES),
        "semantic_orbit_gate": "DISTINCTIVE-ORBIT-REVIEW + HUMAN-DISTINCTIVE",
        "batch_id": LANGUAGES[row["language"]]["batch"],
        "core_sha256": core_hash,
        "network_sha256": network_hash,
        "date": DATE,
    }


def append_reading_cards(positives: list[dict[str, Any]], cores: dict[str, dict[str, Any]]) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in positives:
        grouped[row["language"]].append(row)
    for language, rows in grouped.items():
        path = ROOT / "04-cross-linguistic" / "readings" / LANGUAGES[language]["reading"]
        marker = f"<!-- {MARKER}:{language} -->"
        text = path.read_text(encoding="utf-8")
        if marker in text:
            if text.count(marker) != 1:
                raise RuntimeError(f"duplicate basic-first marker {language}")
            continue
        cards = "\n\n".join(
            render_card(row, POSITIVE_SPECS[row["member_id"]], cores[row["nucleus"]])
            for row in rows
        )
        block = nfc(
            f"\n\n{marker}\n"
            f"## دفعة المعجم الأساسي: {LANGUAGES[language]['label']}\n\n"
            "الترتيب أساسي لا عشوائي، ولا يغير مقام المصدر. لا تصدر هنا إلا المدارات المميزة بعد التعرية الصرفية.\n\n"
            f"{cards}\n\n<!-- /{MARKER}:{language} -->\n"
        )
        with path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(block)


def append_promotions(rows: list[dict[str, Any]]) -> None:
    existing = [json.loads(line) for line in PROMOTIONS.read_text(encoding="utf-8").splitlines() if line.strip()]
    counts = Counter(row["member_id"] for row in existing)
    additions = [row for row in rows if counts[row["member_id"]] == 0]
    bad = {member_id: count for member_id, count in counts.items() if member_id in POSITIVE_SPECS and count > 1}
    if bad:
        raise RuntimeError(f"duplicate prior promotions {bad}")
    if additions:
        with PROMOTIONS.open("a", encoding="utf-8", newline="\n") as handle:
            for row in additions:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def remove_promoted_from_nonissuance(member_ids: set[str]) -> None:
    promotion_counts = Counter()
    for line in PROMOTIONS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            member_id = json.loads(line)["member_id"]
            if member_id in member_ids:
                promotion_counts[member_id] += 1
    if promotion_counts != Counter({member_id: 1 for member_id in member_ids}):
        raise RuntimeError(f"promotion multiplicity mismatch {promotion_counts}")

    lines = COVERAGE.read_text(encoding="utf-8").splitlines(keepends=True)
    hits = Counter()
    kept: list[str] = []
    for line in lines:
        match = re.match(r'^\{"member_id":"([^"]+)"', line)
        if match and match.group(1) in member_ids:
            hits[match.group(1)] += 1
        else:
            kept.append(line)
    bad = {member_id: count for member_id, count in hits.items() if count != 1}
    missing = member_ids - set(hits)
    if bad:
        raise RuntimeError(f"coverage multiplicity mismatch {bad}")
    if hits and missing:
        raise RuntimeError(f"mixed coverage state; missing {sorted(missing)}")
    if hits:
        temporary = COVERAGE.with_suffix(".basic-first.tmp")
        temporary.write_text("".join(kept), encoding="utf-8", newline="\n")
        temporary.replace(COVERAGE)


def render_audit(ranking: dict[str, Any], decisions: list[dict[str, Any]]) -> str:
    by_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in decisions:
        by_language[row["language"]].append(row)
    table: list[str] = []
    for language, metadata in LANGUAGES.items():
        block = ranking["languages"][language]
        rows = by_language[language]
        basic_ranked = sum(
            item["reading_priority_band"] == 0 and not item["already_has_reading_card"]
            for item in block["ranked"]
        )
        issued = sum(row["human_disposition"] == "NUCLEUS-ECHO" for row in rows)
        priority = block["reading_priority_counts"]
        morphology = block["morphology_gate_counts"]
        table.append(
            f"| {metadata['label']} | {metadata['denominator']:,} | "
            f"{priority.get('basic-vocabulary', 0):,} | {priority.get('general-lexicon', 0):,} | "
            f"{priority.get('late-derived-technical-or-compound', 0):,} | "
            f"{morphology.get('MORPHOLOGY-BLOCKED', 0):,} | "
            f"{morphology.get('REDIRECTED-TO-BASE-MEMBER', 0):,} | "
            f"{basic_ranked:,} | {len(rows)} | {issued} |"
        )
    rejection_counts = Counter(
        row["human_disposition"]
        for row in decisions
        if row["human_disposition"] != "NUCLEUS-ECHO"
    )
    batches = "\n".join(
        f"- `{metadata['batch']}`: {metadata['label']}، راجع {len(by_language[language])}، أصدر "
        f"{sum(row['human_disposition'] == 'NUCLEUS-ECHO' for row in by_language[language])}."
        for language, metadata in LANGUAGES.items()
    )
    rejections = "، ".join(f"`{key}`={value}" for key, value in sorted(rejection_counts.items()))
    return nfc(f"""# محضر المسار ج: دفعات المعجم الأساسي أولا

**التاريخ:** {DATE}. **الحالة:** ست دفعات متتابعة مكتملة. **طبقة الحقيقة:** استكشاف، لا تحقق مقيس.

أُعيد ترتيب القراءة في الألسن الستة على ثلاث طبقات صريحة: المعجم الأساسي، ثم المعجم العام، ثم المشتق المتأخر والمصطلح والمركب. هذا ترتيب لا عينة ولا انتقاء؛ لم يتغير مقام مصدر واحد. يبقى مصير غير الصادر في `lane_c_coverage.jsonl`، وينتقل الصادر فقط إلى بطاقة القراءة وسجل الترقيات، فيظل المقام معلومًا باتحاد السجلين.

## نتيجة الدفعات

| اللسان | مقام المصدر | أعضاء أساسية | عامة | متأخرة | صرف محجوب | محال إلى أصل | أزواج أساسية مرتبة | راجعها الإنسان بعد تميز المدار | صدر |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(table)}

«أزواج أساسية مرتبة» عدد أزواج عضو/نواة، لا عدد أعضاء المصدر، وقد يرد العضو في أكثر من مسار صوتي. وكل الصفوف الأساسية محتفظ بها في الترتيب مهما بلغت قيمة `--top`؛ فالحد يخص الطبقتين اللاحقتين فقط.

{batches}

صدر صديان محافظان فقط:

- اليونانية `ὄνυξ ↔ نق` بعد تجريد -s الاسمية من ξ: ظفر أو مخلب أو ظلف صلب مدبب، مع مروحة `نقر/نقب`، والحكم `NUCLEUS-ECHO`.
- اللاتينية `spolium ↔ سب` بعد تجريد -um: جلد حيوان منزوع، مع مروحة `سلب/سبأ`، والحكم `NUCLEUS-ECHO`.

أما ردود المراجعة البشرية فكانت: {rejections}. وسُجل كل رد مع معرّف العضو والرتبة والتعرية والدرجة والهامش وعلته في `lane_c_basic_first_reviews.jsonl`. المرشحات الأساسية التي لم تبلغ أصلًا حارس المدار المميز لم تُعرض كأحكام؛ بقيت `SEMANTIC-ORBIT-NOT-DISTINCTIVE` في الترتيب وغير صادرة في التغطية.

## حراس الصرف والمدار

- اليونانية: تُنزع النهاية الصامتية اليمنى، ومنها -s الاسمية المندمجة في ξ/ψ، قبل عد الصامتين.
- اللاتينية: تُنزع النهايات الاسمية الصامتية اليمنى مثل -um/-us/-is قبل العد.
- الويلزية: الطفرة الابتدائية المصرح بها في حقل الاشتقاق أو المعنى تحال إلى عضو الأصل، وإلا تحجب.
- الفارسية: السابقة المصرح بها تحال إلى الأصل، ومن ذلك `نبود` إلى `بود` من شرح المصدر؛ صامت السابقة لا يدخل النواة.
- لا يكفي التطابق مع ترجمة مفردة. لا يمر المرشح إلا بجوار أسرة من أكثر من جذر عربي، وهامش على أقرب نواة منافسة، ثم مراجعة بشرية لتميز المدار.
- معاني القطع والحركة والكون والسقوط والنوم رُفضت حين لم تكن قراءة النواة نفسها مميزة لها. تطابق `sopor/sofa` مع `سبت` لم يرفع لأن مدار `سب` المجمّد لا يدور على النوم.
- `مزنه` لم تُرفع رغم التطابق المباشر، لأن المصدر يصف العربية `مزنة` بأنها اقتراض إيراني؛ اتجاه النقل يمنع عدها شاهد وراثة مستقلًا.

## سلامة البسط

- ترتيب القراءة مسجل نصًا بأنه `basic-first; explicit; not-random` في كل سطر مراجعة.
- حجب الصرف وإحالته لا يحذفان عضوًا من مقام المصدر.
- العضوان الموجبان وحدهما انتقلا من سجل عدم الإصدار إلى سجل الترقيات وبطاقتي القراءة، وبقية الأعضاء بقيت في `lane_c_coverage.jsonl`.
- لم يُنشأ صف صوتي ولم تُعدّل نواة مجمدة ولم تُشغّل أداة مشتركة أو باني مشترك.

## الملفات

- الترتيب الكامل: `04-cross-linguistic/data/lane_c_nucleus_reread_ranked.json`.
- قرارات الدفعات: `04-cross-linguistic/data/lane_c_basic_first_reviews.jsonl`.
- الأحكام الموجبة: `04-cross-linguistic/data/lane_c_two_layer_semantic_promotions.jsonl`.
- البطاقتان: `04-cross-linguistic/readings/ancient-greek.md` و`04-cross-linguistic/readings/old-latin.md`.
""")


def final_validate(decisions: list[dict[str, Any]], positives: list[dict[str, Any]]) -> None:
    review_rows = [json.loads(line) for line in REVIEWS.read_text(encoding="utf-8").splitlines() if line.strip()]
    if [row["member_id"] for row in review_rows] != [row["member_id"] for row in decisions]:
        raise RuntimeError("review ledger drift")
    member_ids = {row["member_id"] for row in positives}
    promotion_counts = Counter()
    for line in PROMOTIONS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            member_id = json.loads(line)["member_id"]
            if member_id in member_ids:
                promotion_counts[member_id] += 1
    if promotion_counts != Counter({member_id: 1 for member_id in member_ids}):
        raise RuntimeError("final promotion multiplicity drift")
    decision_ids = {row["member_id"] for row in decisions}
    coverage_counts = Counter()
    for line in COVERAGE.read_text(encoding="utf-8").splitlines():
        match = re.match(r'^\{"member_id":"([^"]+)"', line)
        if match and match.group(1) in decision_ids:
            coverage_counts[match.group(1)] += 1
    expected_coverage = Counter(
        row["member_id"]
        for row in decisions
        if row["human_disposition"] != "NUCLEUS-ECHO"
    )
    if coverage_counts != expected_coverage:
        raise RuntimeError(
            "reviewed-member coverage drift: "
            f"expected={expected_coverage} actual={coverage_counts}"
        )
    for row in positives:
        language = row["language"]
        path = ROOT / "04-cross-linguistic" / "readings" / LANGUAGES[language]["reading"]
        text = path.read_text(encoding="utf-8")
        if text.count(f"<!-- {MARKER}:{language} -->") != 1:
            raise RuntimeError(f"reading marker drift {language}")
        heading = f"### بطاقة: `{row['member_id']}`"
        if text.count(heading) != 1:
            raise RuntimeError(f"reading card multiplicity drift {row['member_id']}")
        card = text[text.index(heading):]
        for field in CARD_FIELDS:
            if field not in card:
                raise RuntimeError(f"reading card field drift {row['member_id']}: {field}")
    for path in (REVIEWS, AUDIT, PROMOTIONS):
        text = path.read_text(encoding="utf-8")
        if text != nfc(text):
            raise RuntimeError(f"non-NFC output {path}")
        if "—" in text:
            raise RuntimeError(f"long dash in output {path}")


def main() -> int:
    ranking = json.loads(RANKING.read_text(encoding="utf-8"))
    if ranking.get("schema") != "lane-c-nucleus-reread-ranked-v2":
        raise RuntimeError("ranking schema drift")
    if set(ranking["languages"]) != set(LANGUAGES):
        raise RuntimeError("ranking does not contain all six languages")
    if ranking["contract"]["reading_order"].startswith("basic vocabulary first") is False:
        raise RuntimeError("ranking is not explicitly basic-first")
    if ranking["pins"]["core_sha256"] != sha256(CORE):
        raise RuntimeError("core pin drift")
    if ranking["pins"]["network_sha256"] != sha256(NETWORK):
        raise RuntimeError("network pin drift")

    decisions = load_decisions(ranking)
    cores = core_rows()
    positives = validate_positives(decisions, cores, arabic_sources())
    core_hash = sha256(CORE)
    network_hash = sha256(NETWORK)

    append_reading_cards(positives, cores)
    append_promotions(
        [
            promotion_row(row, POSITIVE_SPECS[row["member_id"]], core_hash, network_hash)
            for row in positives
        ]
    )
    remove_promoted_from_nonissuance({row["member_id"] for row in positives})
    REVIEWS.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in decisions),
        encoding="utf-8",
        newline="\n",
    )
    AUDIT.write_text(render_audit(ranking, decisions), encoding="utf-8", newline="\n")
    final_validate(decisions, positives)
    print(f"CLEAN\t{len(LANGUAGES)} basic-first batches; {len(decisions)} human reviews; {len(positives)} echoes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
