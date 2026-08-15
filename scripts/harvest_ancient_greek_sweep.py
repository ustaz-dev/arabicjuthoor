#!/usr/bin/env python3
"""حوّل مسح اليونانية القديمة الصوتي إلى بطاقات ثلاثية الأرجل.

الصوت يولد المرشح بمروحة ``greek`` الصريحة، والحدث ينقل من
``frozen_event.all_tiers`` بلا تفصيل، والمعنى يؤخذ من فهرس Kaikki ومن
شواهد الجذر العربية المقروءة بلا قطع. لا يصدر موجب آلي: الموجبات وحدها
مسجلة في ``MANUAL_SPECS`` بمدار مكتوب، وما عداها يبقى ``OPEN-CANDIDATE``.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_kaikki_index as LEX  # noqa: E402
import fan_any_script as FAN  # noqa: E402
import frozen_event as EVENT  # noqa: E402
import harvest_reopened_loans as CONTROL  # noqa: E402
import search_arabic_root_senses as AR  # noqa: E402


DATE = "2026-08-15"
LANGUAGE = "ancient-greek"
SCRIPT = "greek"
SWEEP = ROOT / "04-cross-linguistic" / "exploration" / "phonetic-sweep-ancient_greek.json"
READING = ROOT / "04-cross-linguistic" / "readings" / "ancient-greek.md"
MAX_CARD_BYTES = 5 * 1024


# لا يكفي اجتماع كلمات الفهرسة ليصدر حكم. كل موجب هنا اختير بعد قراءة معنى
# الفرع وشواهد الجذر، وله درجة حدث معلنة ومدار خاص به مكتوب بالكلمات.
MANUAL_SPECS: dict[int, dict[str, Any]] = {
    2: {
        "root": "قرن", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "الهراوة ذات الطرف الغليظ والعصا الصلبة تحققان صورة النتوء الممتد "
            "في مقدم الجسم؛ وتذكر الشواهد العربية القرن نفسه وسنان الرمح المصنوع من القرن"
        ),
    },
    3: {
        "root": "نفط", "event_tier": 3, "verdict": "ROOT-TRACE",
        "orbit": (
            "معنى السائل البترولي واحد في الطرفين: اليونانية تسمي المادة النفطية الطبيعية، "
            "والشواهد العربية تسمي النفط دهنا وحلابة جبل تستخرج وتوقد"
        ),
    },
    8: {
        "root": "فلس", "event_tier": 3, "verdict": "ROOT-TRACE",
        "orbit": (
            "القشرة القرنية والبقعة المستديرة على الجلد صورة ناتئة رقيقة، وتقابلها في الشواهد "
            "العربية اللمع الجلدية التي تشبه الفلوس؛ فالجامع هيئة القطع الصغيرة الظاهرة على السطح"
        ),
    },
    9: {
        "root": "دمن", "event_tier": 3, "verdict": "ROOT-TRACE",
        "orbit": (
            "البقاء المتصل في اليونانية هو عين الدوام الذي تحفظه العربية في أدمن الشيء، "
            "أي لازمه ولم يقلع عنه؛ فالمدار استمرار الإقامة أو الفعل مع الزمن"
        ),
    },
    10: {
        "root": "بلغم", "event_tier": 3, "verdict": "ROOT-TRACE",
        "orbit": (
            "مدخلة الفرع تسمي البلغم الخلط البارد اللزج في أحد معانيها، والشواهد العربية "
            "تسمي البلغم خلطا من أخلاط الجسد؛ فالمادة والمعنى الطبيان واحدان"
        ),
    },
    17: {
        "root": "برز", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "جعل الشيء معلوما والإشارة إليه إخراج له من الخفاء حتى يظهر، وهو حدث البروز "
            "المجمد ومعنى ظهر وانكشف في الشواهد العربية"
        ),
    },
    26: {
        "root": "قطر", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "الهبوط والانقضاض إلى أسفل في معنى الفرع يلتقيان نزول المائع وانفصال القطرات "
            "عن مصدرها؛ فالمدار حركة نزول متتابعة من أعلى"
        ),
    },
    36: {
        "root": "ستر", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "المنقذ الحافظ يقي المحفوظ بتغطيته عما يؤذيه، وهي خطوة واحدة من الستر الحسي "
            "إلى الحماية التي يصرح بها معنى الفرع"
        ),
    },
    40: {
        "root": "فرش", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "قطعة القماش الواسعة والرداء مادة رقيقة لينة تنبسط وتنتشر، وهو حدث الفرش نفسه "
            "كما تسميه الشواهد العربية في بسط الثوب ونشره"
        ),
    },
    43: {
        "root": "قمش", "event_tier": 3, "verdict": "ROOT-TRACE",
        "orbit": (
            "الحمولة والبضائع أشياء تجمع وتضم في كتلة محمولة، والشواهد العربية تجعل القماش "
            "ما جمع من متاع؛ فالجامع ضم المتفرق للاحتياز والحمل"
        ),
    },
    62: {
        "root": "نطل", "event_tier": 3, "verdict": "ROOT-TRACE",
        "orbit": (
            "نزح ماء قعر السفينة إخراج للماء من حيزه بقوة، والشواهد العربية تسمي نطل الماء "
            "نضحه وصبه؛ فالفعل المائي الحسي واحد"
        ),
    },
    63: {
        "root": "نطل", "event_tier": 3, "verdict": "ROOT-TRACE",
        "orbit": (
            "استقاء الماء ونزحه يحركانه من مقره إلى الخارج، وهو عين النطل في الشواهد العربية "
            "حين يصب الماء أو ينضح"
        ),
    },
    79: {
        "root": "فرش", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "اليابسة والأرض المنبسطة سطح ممتد منتشر، وهو الوجه المكاني المباشر لحدث الفرش "
            "ولمعنى الأرض المفروشة في العربية"
        ),
    },
    84: {
        "root": "فرش", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "اللين والرقة يسمحان للمادة أن تنبسط وتنتشر بلا صلابة، وهو الوصف نفسه الذي "
            "يجمع معنى الفرع بحدث الفرش المجمد"
        ),
    },
    99: {
        "root": "قلم", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "القصبة والساق هي المادة التي يبرى طرفها فتكون قلما، والشواهد العربية تسمي "
            "القلم من القلم أي القطع والبري؛ فالصورة النباتية والصنعة متصلتان مباشرة"
        ),
    },
    100: {
        "root": "كمر", "event_tier": 3, "verdict": "ROOT-TRACE",
        "orbit": (
            "السقف المعقود والحجرة المقببة غطاء زائد يعلو ما تحته ويحجبه، وهو حدث الكمر "
            "المجمد ومعنى التغطية والاستتار في الشواهد العربية"
        ),
    },
    102: {
        "root": "درر", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "الجريان النافذ في الإسهال صورة صريحة لجريان المائع باندفاع واسترسال، وهو حدث "
            "الدرر المجمد وما تسميه العربية درور اللبن والماء"
        ),
    },
    114: {
        "root": "خلص", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "الخمر الصافي غير المخلوط شيء نفذ من شوائبه وبقي نقيا، وهو معنى الخلوص نفسه "
            "في الحدث المجمد والشواهد العربية"
        ),
    },
    117: {
        "root": "درر", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "جريان السوائل وانسيابها خلال الموضع هو عين الدرور: مائع يندفع ويسترسل من مصدره"
        ),
    },
    128: {
        "root": "ترس", "event_tier": 3, "verdict": "ROOT-TRACE",
        "orbit": (
            "الترس في معنى الفرع درع عريض يدفع الأذى ويبعده، والشواهد العربية تسمي الترس "
            "المجن الذي يتقى به؛ فالشيء ووظيفته واحدان"
        ),
    },
    131: {
        "root": "مرر", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "المر مادة عطرية مرة الطعم، والشواهد العربية تجمع المرارة والمر في المادة نفسها؛ "
            "فالاسم والصفة الحسية متصلان بلا قفزة"
        ),
    },
    133: {
        "root": "نسف", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "البعد والانفصال عن الموضع نتيجة مباشرة لقلع الشيء من مقره وإبعاده، وهو حدث النسف المجمد"
        ),
    },
    137: {
        "root": "طرب", "event_tier": 3, "verdict": "ROOT-TRACE",
        "orbit": (
            "موسى الموسيقى تحمل السرور وتحرك السامع، والشواهد العربية تسمي الطرب خفة الفرح "
            "وتسمي ترجيع الصوت تطريبا؛ فالمدار الموسيقى المحركة للنفس"
        ),
    },
    139: {
        "root": "طرب", "event_tier": 3, "verdict": "ROOT-TRACE",
        "orbit": (
            "الإدخال في السرور واللهو هو الطرب نفسه في الشواهد العربية: خفة تعتري النفس "
            "من شدة الفرح مع حركة وترجيع"
        ),
    },
    146: {
        "root": "برش", "event_tier": 3, "verdict": "ROOT-TRACE",
        "orbit": (
            "التبقع والتنقط بألوان مختلفة مطابق لمعنى البرش العربي، إذ تصفه الشواهد بنكت "
            "صغار تخالف سائر اللون"
        ),
    },
    157: {
        "root": "لبس", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "الثوب البالي وقطعة القماش والشراع كلها أغطية تداخل البدن أو الشيء وتلازمه، "
            "وهو حدث اللبس ومعنى الثياب في الشواهد العربية"
        ),
    },
    161: {
        "root": "سنن", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "المزراق رمح دقيق نافذ مهيأ بالطرف المسنون، والشواهد العربية تسمي السنان "
            "نصل الرمح؛ فالآلة وهيئتها النافذة واحدة"
        ),
    },
    166: {
        "root": "فرق", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "الارتعاش من الخوف هو الفزع الذي تسميه العربية الفرق، وفيه يفرق الخوف تماسُك "
            "الجسد فتظهر الرعدة؛ فمعنى الخوف مصرح به في الطرفين"
        ),
    },
    172: {
        "root": "ملس", "event_tier": 3, "verdict": "ROOT-TRACE",
        "orbit": (
            "السطح المستوي المتجانس هو الأملس الذي تجرد من الخشونة والنتوء، وهو معنى "
            "الملاسة المثبت في الشواهد العربية"
        ),
    },
    177: {
        "root": "بطن", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "تعميق الشيء وتجويفه إنشاء لباطن خفي يمتد إلى الداخل، وهو حدث البطن المجمد "
            "ومعنى الجوف الداخلي في العربية"
        ),
    },
    182: {
        "root": "برز", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "عيار الذهب يخلصه مما يخالطه حتى يخرج ظاهرا نقيا، والشواهد العربية تسمي "
            "الإبريز الذهب الخالص؛ فالمدار إخراج النفيس من غطائه وشوبه"
        ),
    },
    183: {
        "root": "طلل", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "طلوع النجم وارتفاعه إشراف من علو على ما دونه، وهو حدث الطلل المجمد ومعنى "
            "أطل عليه في الشواهد العربية"
        ),
    },
    202: {
        "root": "كدر", "event_tier": 1, "verdict": "ROOT-TRACE",
        "orbit": (
            "الجر والإنزال انتزاع للشيء من موضع رسوخه وسوق له إلى أسفل، وهو صورة حسية "
            "لانقلاع الغليظ الراسخ ومفارقته مقره"
        ),
    },
    209: {
        "root": "فلت", "event_tier": 3, "verdict": "ROOT-TRACE",
        "orbit": (
            "إفلات الشيء حتى يفوت ولا يدرك هو عين الفلت في العربية، إذ ينفصل الشيء "
            "من حابسه ويخرج من اليد أو الذاكرة"
        ),
    },
    219: {
        "root": "روم", "event_tier": 3, "verdict": "ROOT-TRACE",
        "orbit": (
            "الرغبة العاطفية وطلب المحبوب يلتقيان قول العربية رام الشيء أي طلبه وقصده؛ "
            "فالمدار توجه النفس إلى مطلوب والحرص على بلوغه"
        ),
    },
}


SEMITIC_DONOR = re.compile(
    r"(?i)\b(?:Arabic|Hebrew|Aramaic|Syriac|Akkadian|Phoenician|Punic|Semitic)\b"
)
FROM_ROUTE = re.compile(r"(?i)\b(?:from|borrowed from|derived from)\b")
TOKEN = re.compile(r"[a-z]{3,}")
STOP = {
    "and", "the", "for", "from", "into", "with", "that", "this", "used",
    "someone", "something", "form", "kind", "often", "especially", "other",
}


def clean(value: Any) -> str:
    return (
        unicodedata.normalize("NFC", " ".join(str(value or "").split()))
        .replace("`", "ˋ")
        .replace("—", "؛")
    )


def clip_bytes(value: Any, limit: int) -> str:
    """اقطع حاشية طويلة بحد البايت لا الحرف، من غير كسر UTF-8."""
    text = clean(value)
    encoded = text.encode("utf-8")
    if len(encoded) <= limit:
        return text
    clipped = encoded[: max(0, limit - len("…".encode("utf-8")))]
    while True:
        try:
            return clipped.decode("utf-8") + "…"
        except UnicodeDecodeError:
            clipped = clipped[:-1]


def atomic_write_text(path: Path, text: str) -> None:
    """اكتب النسخة الذرية في مجلد النظام المؤقت ثم انقلها إلى مقصدها."""
    handle, temporary = tempfile.mkstemp(
        prefix=f"{path.name}.", suffix=".tmp", dir=tempfile.gettempdir()
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def append_checked(path: Path, original: str, section: str) -> None:
    """ألحق فقط بعد التحقق أن الكاتب لم يتغير منذ بدء بناء الدفعة."""
    if path.read_text(encoding="utf-8") != original:
        raise AssertionError("تغير ملف القراءة أثناء بناء الدفعة")
    with path.open("a", encoding="utf-8", newline="\n") as stream:
        stream.write("\n\n" + section)


def card_bytes(lines: list[str]) -> int:
    return len(("\n".join(lines).rstrip() + "\n").encode("utf-8"))


def require_card_size(lines: list[str], card_id: str) -> int:
    size = card_bytes(lines)
    if size > MAX_CARD_BYTES:
        raise AssertionError(
            f"تجاوزت البطاقة {card_id} حد 5 كيلوبايت: {size} بايت"
        )
    return size


GREEK_READ = {
    "α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e", "ζ": "z",
    "η": "ē", "θ": "th", "ι": "i", "κ": "k", "λ": "l", "μ": "m",
    "ν": "n", "ξ": "x", "ο": "o", "π": "p", "ρ": "r", "σ": "s",
    "ς": "s", "τ": "t", "υ": "y", "φ": "ph", "χ": "kh", "ψ": "ps",
    "ω": "ō",
}


def reader_romanization(word: str, fallback: str) -> str:
    """رومنة محافظة للرسم اليوناني تجعل υ حرف y كما يقرؤه المؤلف."""
    source = unicodedata.normalize("NFD", word.casefold())
    clusters: list[tuple[str, list[str]]] = []
    for char in source:
        if unicodedata.combining(char) and clusters:
            clusters[-1][1].append(char)
        elif char in GREEK_READ:
            clusters.append((char, []))
    if not clusters:
        return clean(fallback)
    out: list[str] = []
    for position_in_word, (base, marks) in enumerate(clusters):
        mapped = (
            "u" if base == "υ" and position_in_word > 0 and clusters[position_in_word - 1][0] == "ο"
            else GREEK_READ[base]
        )
        rough = "\u0314" in marks
        if rough:
            mapped = "rh" if base == "ρ" else "h" + mapped
        accents = []
        for mark in marks:
            if mark in {"\u0300", "\u0301", "\u0304", "\u0306", "\u0308"}:
                accents.append(mark)
            elif mark == "\u0342":
                accents.append("\u0302")
        if accents:
            position = max((i for i, char in enumerate(mapped) if char in "aeiouyēō"), default=len(mapped) - 1)
            mapped = mapped[:position + 1] + "".join(accents) + mapped[position + 1:]
        if "\u0345" in marks:
            mapped += "i"
        out.append(mapped)
    return unicodedata.normalize("NFC", "".join(out))


def tokens(value: Any) -> set[str]:
    return {word for word in TOKEN.findall(str(value or "").casefold()) if word not in STOP}


def select_lexicon(entries: list[dict[str, Any]], gloss: str) -> int:
    wanted = tokens(gloss)
    scores: list[tuple[int, float, int]] = []
    for index, entry in enumerate(entries):
        found = tokens(entry.get("en"))
        shared = len(wanted & found)
        union = len(wanted | found) or 1
        scores.append((shared, shared / union, -index))
    return -max(scores)[2] if scores else 0


def phases(sweep: dict[str, Any]) -> list[list[dict[str, Any]]]:
    direct = [row for row in sweep["both"] if row.get("direct")]
    remainder = [row for row in sweep["both"] if not row.get("direct")]
    if len(direct) != 251 or len(remainder) != 157:
        raise AssertionError("تغير مقام المسح عن 251 مباشرة و157 باقية")
    return [direct[:150], direct[150:], remainder[:150], remainder[150:]]


def sound_fan(word: str) -> tuple[str, list[tuple[str, float]]]:
    skeleton = "".join(FAN.skeleton(word, SCRIPT))
    ranked = FAN.rank(word, FAN.fan(word, SCRIPT), SCRIPT)
    return skeleton, ranked


def semitic_route(entries: list[dict[str, Any]]) -> str:
    for entry in entries:
        etym = str(entry.get("etym") or "")
        if SEMITIC_DONOR.search(etym) and FROM_ROUTE.search(etym):
            return clean(etym)
    return ""


def render_event(root: str) -> list[str]:
    options = EVENT.all_tiers(root)
    if not options:
        return ["  - لا حدث في السجل المجمد."]
    return [
        f"  - الدرجة {item.tier} ({clean(item.tier_ar)}): «{clean(item.text)}»؛ "
        f"المصدر: `{clean(item.source)}`؛ الملاحظة: {clean(item.note) or 'لا ملاحظة زائدة'}."
        for item in options
    ]


def render_entry(entry: dict[str, Any]) -> str:
    read = f" /{clean(entry.get('read'))}/" if entry.get("read") else ""
    etym = (
        f"؛ حاشية الأصل: {clip_bytes(entry.get('etym'), 700)}"
        if entry.get("etym") else ""
    )
    return (
        f"`{clean(entry.get('word'))}`{read} [{clean(entry.get('pos')) or 'غير موسوم'}] "
        f"«{clip_bytes(entry.get('en'), 900)}»{etym}"
    )


def render_lexicon(entries: list[dict[str, Any]], selected: int, how: str) -> list[str]:
    competitors = [index for index in range(len(entries)) if index != selected][:2]
    lines = [
        f"- **رجل المعنى، قاموس الفرع:** قُرئت {len(entries)} مدخلة من "
        f"`build_kaikki_index.look('{LANGUAGE}', w)`؛ طريق الإصابة: {how}.",
        f"  - المختارة للسياق: {render_entry(entries[selected])}.",
    ]
    if competitors:
        lines.append(
            "  - نافسها: "
            + " | ".join(render_entry(entries[index]) for index in competitors)
            + "."
        )
    return lines


def choose_witness(matches: list[dict[str, Any]], orbit: str) -> dict[str, Any] | None:
    """اختر الشاهد الذي تسنده كلمات المدار؛ لا يغير الاختيار حكم البطاقة."""
    if not matches:
        return None
    wanted = set(re.findall(r"[\u0600-\u06ff]{3,}", orbit))
    ranked = []
    for index, match in enumerate(matches):
        found = set(re.findall(r"[\u0600-\u06ff]{3,}", str(match.get("definition") or "")))
        ranked.append((len(wanted & found), -index, match))
    return max(ranked, key=lambda row: (row[0], row[1]))[2]


def render_arabic_witnesses(
    root: str,
    matches: list[dict[str, Any]],
    used: dict[str, Any] | None = None,
) -> list[str]:
    lines = [
        f"- **شواهد الجذر العربي `{clean(root)}`:** قُرئت كاملة بتنفيذ "
        f"`python scripts/search_arabic_root_senses.py {clean(root)} --max-chars 0`؛ "
        f"الشواهد={len(matches)}؛ القطع=لا."
    ]
    if not matches:
        lines.append("  - لا شاهد في الموارد المسماة؛ الغياب فجوة مورد لا نفي معنى.")
        return lines
    if used is None:
        lines.append("  - لم يُقتبس شاهد؛ لا مدار موجب في هذه البطاقة يقوم عليه.")
        return lines
    source_id = AR.canonical_source_id(str(used.get("source") or ""))
    source = AR.SOURCE_LABELS.get(source_id, clean(used.get("source")))
    url = f" [{clean(used.get('url'))}]" if used.get("url") else ""
    lines.append(
        f"  - الشاهد الذي قام عليه المدار وحده، {source}: "
        f"«{clip_bytes(used.get('definition'), 1000)}»{url}"
    )
    return lines


def render_fan(ranked: list[tuple[str, float]], selected: str) -> str:
    chosen: list[tuple[str, float]] = []
    for item in ranked:
        if item[0] == selected:
            chosen.append(item)
            break
    chosen.extend(item for item in ranked if item[0] != selected and len(chosen) < 8)
    return (
        f"قُرئت {len(ranked)} صورة؛ المنتخب "
        + "، ".join(f"`{clean(root)}`[{weight:.6f}]" for root, weight in chosen)
        + ("؛ المعروض المنتخب و7 منافسات" if len(ranked) > len(chosen) else "")
    )


def open_orbit(gloss: str, root: str) -> str:
    return (
        f"قوبل معنى الفرع «{clean(gloss)}» بجميع معاني `{clean(root)}` المطبوعة أعلاه "
        "وبالحدث المجمد؛ ولم يثبت لي مدار محدود يجمعها من غير تعميم أو قفزة، فتظل الصورة مفتوحة"
    )


def build_card(
    sweep_rank: int,
    row: dict[str, Any],
    hits_by_root: dict[str, list[dict[str, Any]]],
) -> tuple[list[str], dict[str, Any]]:
    word = str(row["branch"])
    root = str(row["best"])
    skeleton, ranked = sound_fan(word)
    fan_roots = [candidate for candidate, _weight in ranked]
    if root not in fan_roots:
        raise AssertionError(f"خرج الجذر المنتخب من مروحة greek: {word} ↔ {root}")
    entries, how = LEX.look(LANGUAGE, word)
    if not entries:
        raise AssertionError(f"لا معنى قاموس فرع للصورة {word}")
    selected = select_lexicon(entries, str(row.get("gloss") or ""))
    chosen = entries[selected]
    published_read = clean(chosen.get("read") or str(row.get("say") or "").split("  (")[0])
    romanization = reader_romanization(word, published_read)
    spec = MANUAL_SPECS.get(sweep_rank)
    route = semitic_route(entries)
    if spec and str(spec["root"]) != root:
        raise AssertionError(f"تغير جذر المواصفة اليدوية {sweep_rank}")

    if route:
        closure = "SEMITIC-SOURCE-TRANSMISSION"
        verdict = "LOANWORD"
        orbit = (
            "سمى قاموس الفرع مانحا ساميا في طريق هذه الصورة؛ فهذا انتقال مسمى لا إغلاق "
            "بالحدس، وتبقى المقابلة الصوتية والمعنوية معروضة في مقام اليونانية"
        )
    elif spec:
        declared = EVENT.resolve(root, tier=int(spec["event_tier"]))
        if declared is None:
            raise AssertionError(f"درجة الحدث اليدوية غائبة {sweep_rank}:{root}")
        independent = AR.independent_fan(hits_by_root.get(root, []))
        if not independent["judgment_ready"]:
            raise AssertionError(f"الموجب بلا شاهدين عربيين مستقلين {sweep_rank}:{root}")
        closure = str(spec["verdict"])
        verdict = str(spec["verdict"])
        orbit = str(spec["orbit"])
    else:
        closure = "OPEN-CANDIDATE"
        verdict = "غير صادر"
        orbit = open_orbit(str(chosen.get("en") or row.get("gloss") or ""), root)

    card_id = f"PS-GREEK-{sweep_rank:05d}"
    used_witness = choose_witness(hits_by_root.get(root, []), orbit) if spec else None
    fan_text = render_fan(ranked, root)
    lines = [
        f"### بطاقة المسح: `{clean(word)}` /{romanization}/ ↔ `{clean(root)}`؛ {card_id}",
        "",
        "- **إصدار البروتوكول:** RECOVERY-v2؛ الطبقة: استكشاف.",
        f"- **الصورة والرومنة:** `{clean(word)}` /{romanization}/؛ رومنة المسح المحفوظة: "
        f"/{clean(str(row.get('say') or '').split('  (')[0])}/.",
        f"- **رجل الصوت:** استدعاء `fan_any_script.fan('{clean(word)}', 'greek')` بالخط "
        f"`greek` صريحا؛ الهيكل `{clean(skeleton)}`؛ الجذر المنتخب `{clean(root)}` حاضر في المروحة.",
        f"- **المروحة مرتبة، والوزن ترتيب لا حكم:** {fan_text}.",
        "- **رجل الحدث:** `frozen_event.all_tiers(root)` أعاد الدرجات الآتية بلا زيادة ولا تفصيل:",
        *render_event(root),
        *render_lexicon(entries, selected, how),
        *render_arabic_witnesses(root, hits_by_root.get(root, []), used_witness),
        f"- **المدار المكتوب باليد بالكلمات:** {clean(orbit)}.",
        f"- **حاشية الأصل، وليست رجلا رابعة:** {clip_bytes(chosen.get('etym'), 800) or 'لم يذكر القاموس أصلا'}.",
    ]
    if route:
        lines.append(f"- **المانح السامي المسمى:** {route}.")
    lines.extend([
        f"- حالة الإغلاق: `{closure}`.",
        f"- الحكم (استكشاف): `{verdict}`.",
        "",
    ])
    size = require_card_size(lines, card_id)
    return lines, {
        "id": card_id,
        "sweep_rank": sweep_rank,
        "word": word,
        "romanization": romanization,
        "script": SCRIPT,
        "root": root,
        "direct": bool(row.get("direct")),
        "dictionary_path": how,
        "dictionary_entry_count": len(entries),
        "arabic_witness_count": len(hits_by_root.get(root, [])),
        "event_tiers": [item.tier for item in EVENT.all_tiers(root)],
        "closure": closure,
        "verdict": verdict,
        "named_semitic_route": route,
        "card_bytes": size,
    }


def audit_text(batch: int, rows: list[dict[str, Any]], output: list[dict[str, Any]], controls: list[dict[str, Any]]) -> str:
    counts = Counter(item["closure"] for item in output)
    phase = "الشهادة المباشرة" if batch <= 2 else "بقية اجتماع الصوت والمعنى"
    lines = [
        f"# محضر بطاقات المسح الصوتي لليونانية القديمة، الدفعة {batch:03d}",
        "",
        f"- التاريخ: {DATE}.",
        f"- المقام: {phase}؛ النافذة: {len(rows)} صورة.",
        "- الأرجل ثلاث: صوت من مروحة `greek`، وحدث من `all_tiers`، ومعنى من Kaikki وشواهد الجذر العربية الكاملة.",
        "- حقل الأصل حاشية لا رجل، ولم يغلق صورة إلا مانح سامي مسمى في نص القاموس.",
        "- كل صورة تحمل رومنة مقروءة، وكل غير محسوم بقي `OPEN-CANDIDATE` بسطر مدار موجز.",
        "- لم تمس صلة صادرة حية، ولم يضف وسم إلى قاموس الإغلاق المغلق.",
        "",
        "## ضابط الست الصادرة",
        "",
        "| الصورة | الجذر | a-b | b-a | الحدث |",
        "|---|---|---|---|---|",
    ]
    for item in controls:
        lines.append(
            f"| `{clean(item['word'])}` | `{clean(item['root'])}` | "
            f"`{clean(item['a_minus_b']) or '∅'}` | `{clean(item['b_minus_a']) or '∅'}` | "
            f"{'ثابت' if item['event_available_at_declared_tier'] else 'غائب'} |"
        )
    lines.extend(["", "## الحصيلة", ""])
    for closure, count in sorted(counts.items()):
        lines.append(f"- `{closure}`: {count}.")
    return "\n".join(lines) + "\n"


def harvest(batch: int) -> dict[str, Any]:
    sweep = json.loads(SWEEP.read_text(encoding="utf-8"))
    if sweep.get("language") != "ancient_greek" or len(sweep.get("both", [])) != 408:
        raise AssertionError("اختلط لسان المسح أو تغير مقام 408")
    windows = phases(sweep)
    if not 1 <= batch <= len(windows):
        raise SystemExit("دفعات المسح الأولي هي 1 إلى 4")
    rows = windows[batch - 1]
    rank_by_identity = {id(row): index for index, row in enumerate(sweep["both"], 1)}
    marker = f"PHONETIC-SWEEP-ANCIENT-GREEK-BATCH-{batch:03d}"
    manifest = ROOT / "data" / f"phonetic-sweep-ancient-greek-harvest-batch-{batch:03d}.json"
    audit = ROOT / "05-audits" / f"{DATE}-phonetic-sweep-ancient-greek-harvest-batch-{batch:03d}.md"
    original = READING.read_text(encoding="utf-8")
    if manifest.exists() or audit.exists() or f"<!-- {marker}:START -->" in original:
        raise AssertionError(f"مخرجات الدفعة {batch:03d} موجودة")

    controls = CONTROL.control_run()
    if any(item["a_minus_b"] for item in controls):
        raise AssertionError("فقد ضابط الصادرات مرشحا")
    roots = {str(row["best"]) for row in rows}
    hits_by_root = AR.matches_for_roots(AR.DEFAULT_RESOURCES, roots, None)

    section = [
        f"<!-- {marker}:START -->",
        "",
        f"## بطاقات المسح الصوتي لليونانية القديمة، الدفعة {batch:03d} ({DATE})",
        "",
    ]
    output: list[dict[str, Any]] = []
    for row in rows:
        sweep_rank = rank_by_identity[id(row)]
        card, record = build_card(sweep_rank, row, hits_by_root)
        section.extend(card)
        output.append(record)
    section.extend([f"<!-- {marker}:END -->", ""])

    rendered_section = unicodedata.normalize("NFC", "\n".join(section)).replace("—", "؛")
    if "—" in rendered_section:
        raise AssertionError("تسربت الشرطة الطويلة إلى الدفعة")
    append_checked(READING, original, rendered_section)

    payload = {
        "schema": "phonetic-sweep-ancient-greek-harvest-v1",
        "date": DATE,
        "language": LANGUAGE,
        "script": SCRIPT,
        "batch": batch,
        "batch_size": len(rows),
        "phase": "direct" if batch <= 2 else "remaining",
        "controls": controls,
        "a_minus_b_nonempty": sum(bool(item["a_minus_b"]) for item in controls),
        "closure_counts": dict(Counter(item["closure"] for item in output)),
        "positive_cards": sum(item["verdict"] in {"ROOT-TRACE", "NUCLEUS-TRACE", "FLOOR-TRACE"} for item in output),
        "named_semitic_transmissions": sum(item["closure"] == "SEMITIC-SOURCE-TRANSMISSION" for item in output),
        "open_candidates": sum(item["closure"] == "OPEN-CANDIDATE" for item in output),
        "sound_only_deferred": len(sweep["sound_only"]),
        "rows": output,
    }
    manifest.write_text(
        unicodedata.normalize("NFC", json.dumps(payload, ensure_ascii=False, indent=2) + "\n"),
        encoding="utf-8", newline="\n",
    )
    audit.write_text(
        unicodedata.normalize("NFC", audit_text(batch, rows, output, controls)),
        encoding="utf-8", newline="\n",
    )
    return payload


def sanitize_existing(batch: int) -> None:
    """طبّع شرطة المصدر داخل دفعة مولدة غير مودعة، من غير مساس بما قبلها."""
    marker = f"PHONETIC-SWEEP-ANCIENT-GREEK-BATCH-{batch:03d}"
    text = READING.read_text(encoding="utf-8")
    start_token = f"<!-- {marker}:START -->"
    end_token = f"<!-- {marker}:END -->"
    start = text.index(start_token)
    end = text.index(end_token, start) + len(end_token)
    section = text[start:end].replace("—", "؛")
    atomic_write_text(READING, text[:start] + section + text[end:])


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, required=True)
    parser.add_argument("--sanitize-existing", action="store_true")
    args = parser.parse_args()
    if args.sanitize_existing:
        sanitize_existing(args.batch)
        print(f"CLEAN: normalized generated batch {args.batch:03d}")
        return 0
    payload = harvest(args.batch)
    print(json.dumps({key: value for key, value in payload.items() if key not in {"rows", "controls"}}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
