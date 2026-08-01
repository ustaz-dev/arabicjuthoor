from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
READINGS = ROOT / "04-cross-linguistic" / "readings"
DATA_DIR = ROOT / "04-cross-linguistic" / "data"
COVERAGE_PATH = DATA_DIR / "lane_d_coverage.jsonl"
BATCH_SIZE = 500


@dataclass(frozen=True)
class SourceSpec:
    key: str
    language_ar: str
    language_en: str
    branch_ar: str
    source_path: Path
    output_path: Path
    pin: str
    expected_sha256: str
    expected_bytes: int
    expected_records: int
    expected_members: int
    expected_bad_lines: tuple[int, ...]
    expected_duplicate_ids: tuple[str, ...]


SOURCES = (
    SourceSpec(
        key="oe",
        language_ar="الإنجليزيّة القديمة",
        language_en="Old English",
        branch_ar="هندوأوروبيّة، جرمانيّة غربيّة، فرع بعيد عن العربيّة",
        source_path=ROOT
        / "Resources"
        / "english_old"
        / "kaikki.org-dictionary-OldEnglish.jsonl",
        output_path=READINGS / "old-english.md",
        pin="lane-d-old-english-kaikki-2026-07-30-85b8cbf5",
        expected_sha256="85b8cbf5ac03035e597ae97d093865bae43c6b42def79b959467f34f07f28b74",
        expected_bytes=24_493_745,
        expected_records=7_948,
        expected_members=11_694,
        expected_bad_lines=(7_949,),
        expected_duplicate_ids=("en--þ-ang-suffix-crzEsTtt1",),
    ),
    SourceSpec(
        key="oi",
        language_ar="الإيرلنديّة القديمة",
        language_en="Old Irish",
        branch_ar="هندوأوروبيّة، كلتيّة، فرع بعيد عن العربيّة",
        source_path=ROOT
        / "Resources"
        / "old_irish"
        / "kaikki.org-dictionary-OldIrish.jsonl",
        output_path=READINGS / "old-irish.md",
        pin="lane-d-old-irish-kaikki-2026-07-30-3d4fa67a",
        expected_sha256="3d4fa67a5b9369aba27f167aab549e14a3d79a8f60c266b223a0971492cd763d",
        expected_bytes=18_174_722,
        expected_records=6_429,
        expected_members=8_506,
        expected_bad_lines=(),
        expected_duplicate_ids=(),
    ),
)


ARABIC_FANS = {
    "قرن": (
        "كتاب العين، مادة قرن: «قَرْنُ الثور معروف، وموضعه من رأس الإنسان قَرْن أيضا» "
        "[Resources/Ten dictionaries for Arabic language/Ein.csv، صف المادة 3142]. "
        "المحيط في اللغة، مادة قرن: «القَرْنُ قَرْنُ الثور»، ويورد أيضا الجبل الصغير المنفرد "
        "[Resources/Ten dictionaries for Arabic language/almuheet_2.csv، صف المادة 2521]. "
        "القريب: النتوء الحيواني والرأسي. البعيد: القرن الزمني والاقتران. الرافض لهذه السلسلة: "
        "معاني الحبل والزمان لا تحمل معنى العضو."
    ),
    "برج": (
        "كتاب العين، مادة برج: «بُرْجُ سور المدينة والحصن بيوت تبنى على السور»، وتسمى البيوت "
        "على أركان القصر برجا [Resources/Ten dictionaries for Arabic language/Ein.csv، "
        "صف المادة 3931]. الصحاح، مادة برج: «بُرْجُ الحصن ركنه»، وربما سمي الحصن به "
        "[Resources/Ten dictionaries for Arabic language/Alsehah2.csv، صف المادة 148]. "
        "القريب: الحصن وركنه والبناء الدفاعي. البعيد: برج السماء والتبرج. الرافض لهذه السلسلة: "
        "بياض العين."
    ),
    "ثلث": (
        "كتاب العين، مادة ثلث: «الثلاثة من العدد»، ويورد الثلث والمثلث وما كان على ثلاثة أثْناء "
        "[Resources/Ten dictionaries for Arabic language/Ein.csv، صف المادة 5474]. الصحاح، "
        "مادة ثلث: «الثلاثة في عدد المذكر، والثلاث في عدد المؤنث» "
        "[Resources/Ten dictionaries for Arabic language/Alsehah2.csv، صف المادة 51]. "
        "القريب: العدد ثلاثة والجزء الثالث. البعيد: الورد والحبل المثلث. لا معنى رافض داخل "
        "السلسلة العددية المحكومة."
    ),
    "درك": (
        "الصحاح، مادة درك: «أدركته ببصري أي رأيته»، مع أصل اللحوق والبلوغ "
        "[Resources/Ten dictionaries for Arabic language/Alsehah6.csv، صف المادة 493]. "
        "لسان العرب، مادة درك: يورد «أدركته ببصري أي رأيته» مع اللحوق والوصول "
        "[Resources/Ten dictionaries for Arabic language/lesan_3.csv، صف المادة 733]. "
        "القريب: الرؤية والإحاطة بالبصر. البعيد: اللحوق والبلوغ والدركات. الرافض لهذه السلسلة: "
        "قطعة الحبل وقعر الشيء."
    ),
    "برق": (
        "كتاب العين، مادة برق: «كل شيء يتلألأ فهو بارق»، مع بروق السحاب "
        "[Resources/Ten dictionaries for Arabic language/Ein.csv، صف المادة 3154]. الصحاح، "
        "مادة برق: «بَرَق السيف وغيره أي تلألأ»، والبرق لمعان السماء "
        "[Resources/Ten dictionaries for Arabic language/Alsehah6.csv، صف المادة 221]. "
        "القريب: اللمعان والظهور الحاد. البعيد: الأبرق لاختلاط اللونين. الرافض: أسماء الأعلام."
    ),
    "غرس": (
        "كتاب العين، مادة غرس: الغرس الشجر الذي يغرس، والغراس فسيلة النخل "
        "[Resources/Ten dictionaries for Arabic language/Ein.csv، صف المادة 2670]. الصحاح، "
        "مادة غرس: «غَرَسْت الشجر»، والغراس فسائل النخل "
        "[Resources/Ten dictionaries for Arabic language/Alsehah4.csv، صف المادة 373]. "
        "القريب: النبات المثبت في الأرض وفعل إنباته. البعيد والرافض: الجليدة التي تخرج مع الولد."
    ),
    "سلم": (
        "كتاب العين، مادة سلم: «رجل سليم أي سالم وقد سلم سلامة»، ويجعل السلام بمعنى السلامة "
        "[Resources/Ten dictionaries for Arabic language/Ein.csv، صف المادة 4692]. "
        "أساس البلاغة، مادة سلم: «سلم من البلاء سلامة وسلاما، وسلم من المرض برئ» "
        "[Resources/Ten dictionaries for Arabic language/asas.csv، صف المادة 1541]. "
        "القريب: السلامة والصحة والتئام الشيء. البعيد: السلم والدلو والشجر. الرافض: لدغ الحية "
        "وما حمل اسمه تفاؤلا."
    ),
    "قنن": (
        "كتاب العين، مادة قن: «القُنّة الجبل المنفرد المستطيل في السماء» "
        "[Resources/Ten dictionaries for Arabic language/Ein.csv، صف المادة 2942]. تاج العروس، "
        "مادة قنن: يورد القُن «الجبل الصغير» "
        "[Resources/Ten dictionaries for Arabic language/Tag Al-‘Arus Min Gawahir "
        "Al-Qamus17.csv، صف المادة 88]. القريب المحتمل: رأس مرتفع أو قمة. البعيد والرافض: "
        "العبد والقوة من قوى الحبل."
    ),
}


FROZEN_COUNTERPARTS = {
    "قرن": (
        "قرن",
        "نتوء بشدة أو اعتصار يمتد في أعلى الجسم أو مقدمه",
        "computational/data/layer_2_results_v2.jsonl",
    ),
    "برج": (
        "برج",
        "بروز ناصع قوي من بين ما يكتنفه في ظاهر الشيء",
        "computational/data/layer_2_results_v2.jsonl",
    ),
    "ثل": (
        "ثل",
        "تجمع الدقائق وتماسكها",
        "data/juthoor-core-levels.json",
    ),
    "درك": (
        "درك",
        "لحاق أو تعلق بطرف الشيء، أو أقصاه",
        "computational/data/layer_2_results_v2.jsonl",
    ),
    "برق": (
        "برق",
        "بروز من العمق إلى الظاهر بحدة ودقة لمعان أو تميز",
        "computational/data/layer_2_results_v2.jsonl",
    ),
    "سلم": (
        "سلم",
        "صحة جرم الشيء والتئام ظاهره في ذاته، أي عدم تصدعه أو تفرع غيره",
        "computational/data/layer_2_results_v2.jsonl",
    ),
    "قنن": (
        "قنن",
        "الاحتباس في الحوزة، أو الباطن، بعمق وامتداد",
        "computational/data/layer_2_results_v2.jsonl",
    ),
}


# Signed section 26 keeps only a form whose named base is both written and
# judged. Every other form remains in recovery coverage, and proper names stay
# open for source-root extraction rather than being isolated as closures.
JUDGED_FORM_BASES = {
    "Abel",
    "Adam",
    "albe",
    "Alexander",
    "Alexandria",
    "Antiochia",
    "apostol",
    "assa",
    "asse",
    "assen",
    "burg",
    "byt",
    "camp",
    "candel",
    "canonic",
    "collecta",
    "consul",
    "cristalla",
    "Daniel",
    "dunn",
    "ele",
    "engel",
    "fals",
    "fers",
    "gombe",
    "grad",
    "horn",
    "martyr",
    "munt",
    "not",
    "Paulus",
    "Petrus",
    "pise",
    "port",
    "post",
    "purpure",
    "Salomon",
    "senatus",
    "september",
    "sole",
    "Syria",
    "tabule",
    "torr",
}


def positive(
    *,
    root: str,
    degree: str,
    sound: str,
    orbit: str,
    branch_radiation: str,
    arabic_radiation: str,
    bridges: str,
    homonym: str,
    notes: str,
) -> dict[str, str]:
    counterpart = FROZEN_COUNTERPARTS[root]
    return {
        "kind": "positive",
        "degree": degree,
        "arabic_scan": ARABIC_FANS["ثلث" if root == "ثل" else root],
        "counterpart": (
            f"{counterpart[0]} «{counterpart[1]}» [{counterpart[2]}، القراءة المجمدة]."
        ),
        "sound": sound,
        "orbit": orbit,
        "filter": "لم يسم المصدر مانحا أجنبيا، وسلسلته المعلنة موروثة في الفرع.",
        "homonym": homonym,
        "orphan": "ليست قرينة حاكمة وحدها؛ الحكم قائم على الصوت والمعنى والمصدر.",
        "branch_radiation": branch_radiation,
        "arabic_radiation": arabic_radiation,
        "bridges": bridges,
        "state": "READY",
        "judgment": (
            "NUCLEUS-ECHO" if degree == "نواة" else "ROOT-TRACE"
        ),
        "barrier": "النوع=READY؛ يتطلب=لا شيء قبل مراجعة التحقق التي يطلقها المؤلف وحده",
        "notes": notes,
    }


def candidate(
    *,
    root: str,
    degree: str,
    sound: str,
    orbit: str,
    state: str,
    barrier: str,
    bridges: str,
    homonym: str,
    notes: str,
) -> dict[str, str]:
    counterpart = FROZEN_COUNTERPARTS.get(root)
    if counterpart:
        counterpart_text = (
            f"{counterpart[0]} «{counterpart[1]}» [{counterpart[2]}، القراءة المجمدة]."
        )
    else:
        counterpart_text = (
            "(لا مقابل من الأداة المجمدة): مادة غرس حاضرة في المعجمين القديمين، "
            "لكن قراءة الجذر غير موجودة في سجل الطبقة الثانية المستعمل هنا."
        )
    return {
        "kind": "candidate",
        "degree": degree,
        "arabic_scan": ARABIC_FANS["ثلث" if root == "ثل" else root],
        "counterpart": counterpart_text,
        "sound": sound,
        "orbit": orbit,
        "filter": "لم يسم المصدر مانحا أجنبيا، فلا يعزل بصفته قرضا.",
        "homonym": homonym,
        "orphan": "مؤشر وصفي فقط؛ لا يمنح حكما مع بقاء الفجوة.",
        "branch_radiation": "غير محسوب؛ لا إشعاع مدعوم قبل الحكم الموجب.",
        "arabic_radiation": "غير محسوب؛ المروحة مسحت، لكن لا حكم موجب.",
        "bridges": bridges,
        "state": state,
        "judgment": "(لا حكم صادر)",
        "barrier": barrier,
        "notes": notes,
    }


CUSTOM: dict[str, dict[str, str]] = {
    "en-horn-ang-noun-lUMJjxcE": positive(
        root="قرن",
        degree="جذر كامل",
        sound=(
            "قرن q-r-n، ثم GUT-01: q إلى k، ثم BR-GRIM-01: k إلى h في الجرمانية، "
            "فتأتي h-r-n؛ نطق المصدر /xorn/ و[horn]. الشاهدان مسميان في الشبكة المجمدة."
        ),
        orbit="مباشر: قرن الحيوان هو horn.",
        branch_radiation=(
            "الأعضاء المعجمية المدعومة=2؛ سلاسل المعنى المدعومة=1؛ عضوا horn وantler "
            "من المدخل نفسه، ولا يرث gable حكمهما."
        ),
        arabic_radiation=(
            "الأعضاء المعجمية المدعومة=1؛ سلاسل المعنى المدعومة=1؛ الاسم قَرْن في سلسلة "
            "النتوء الرأسي وحدها."
        ),
        bridges=(
            "الجذر قرن؛ النواة قر؛ الصورة الجرمانية الأم؛ شاهد BR-GRIM-01 العابر للفروع؛ "
            "المعنى المباشر؛ فصل معاني الزمن والاقتران."
        ),
        homonym=(
            "الهوية هي عضو horn «horn» بهذا المعرف؛ antler عضو ثان مستقل، وgable عضو ثالث "
            "لا يرث هذا الحكم."
        ),
        notes=(
            "حكم استكشافي على عضو واحد، لا دعوى اشتقاق تاريخي. لم تستعمل أرقام أي قراءة "
            "جرمانية أخرى."
        ),
    ),
    "en-horn-ang-noun-eF7ljlKs": positive(
        root="قرن",
        degree="جذر كامل",
        sound=(
            "قرن q-r-n، ثم GUT-01: q إلى k، ثم BR-GRIM-01: k إلى h في الجرمانية، "
            "فتأتي h-r-n؛ نطق المصدر /xorn/ و[horn]."
        ),
        orbit="مباشر: antler عضو قرني ناتئ من الرأس.",
        branch_radiation=(
            "الأعضاء المعجمية المدعومة=2؛ سلاسل المعنى المدعومة=1؛ horn وantler فقط."
        ),
        arabic_radiation=(
            "الأعضاء المعجمية المدعومة=1؛ سلاسل المعنى المدعومة=1؛ قَرْن الحيوان."
        ),
        bridges=(
            "الجذر قرن؛ النواة قر؛ الصورة الجرمانية الأم؛ شاهد BR-GRIM-01؛ "
            "الجسر الدلالي المباشر؛ معاني الجذر العربية الرافضة."
        ),
        homonym=(
            "العضو المحكوم antler وحده؛ لا ينقل الحكم إلى gable ولا إلى معنى زمني عربي."
        ),
        notes="عضو مستقل بحق نقض مستقل، مع بقاء السلسلة الأسرية الواحدة ظاهرة.",
    ),
    "en-burg-ang-noun-rciIbhZo": positive(
        root="برج",
        degree="جذر كامل",
        sound=(
            "ب ور محفوظان، وGUT-03 يصل ج العربية إلى g/k؛ نطق المصدر /burɡ/، "
            "فيقابل ب-r-g الجذر ب-r-j بصف واحد مسمى."
        ),
        orbit="مباشر: fortified place، fortress، castle يقابل الحصن وبرج الحصن.",
        branch_radiation=(
            "الأعضاء المعجمية المدعومة=1؛ سلاسل المعنى المدعومة=1؛ عضو المكان المحصن وحده، "
            "ولا يرثه عضو city or town."
        ),
        arabic_radiation=(
            "الأعضاء المعجمية المدعومة=1؛ سلاسل المعنى المدعومة=1؛ بُرج الحصن وركنه."
        ),
        bridges=(
            "الجذر برج؛ النواة بر؛ النطق /burɡ/؛ GUT-03؛ شاهد المعنى في العين والصحاح؛ "
            "فصل برج الفلك وبياض العين."
        ),
        homonym=(
            "هذا عضو «fortified place: fortress, castle»؛ عضو «city or town» في المدخل نفسه "
            "يبقى بلا وراثة للحكم."
        ),
        notes="تقارب الجذر والمعنى مباشر، والحكم لا يشمل المشتقات ولا أسماء الأعلام.",
    ),
    "en-þri-ang-num-i1udsME9": positive(
        root="ثل",
        degree="نواة",
        sound=(
            "الثاء /θ/ محفوظة في الإنجليزية القديمة، وLIQ-01 يصل ل إلى r؛ "
            "نطق المصدر /θriː/. لا يسقط الحرف الثالث من جذر ثلث إلا لأن درجة الحكم نواة مصرح بها."
        ),
        orbit="مباشر في الأسرة العددية: three يقابل ثلاثة.",
        branch_radiation=(
            "الأعضاء المعجمية المدعومة=1؛ سلاسل المعنى المدعومة=1؛ عضو العدد three."
        ),
        arabic_radiation=(
            "الأعضاء المعجمية المدعومة=1؛ سلاسل المعنى المدعومة=1؛ ثلاثة والثلث في السلسلة العددية."
        ),
        bridges=(
            "الجذر ثلث جرب أولا؛ ثم النواة ثل؛ LIQ-01؛ شاهد BR-GRIM-01 العابر للفروع؛ "
            "المعنى العددي المباشر؛ فصل معاني الورد والحبل."
        ),
        homonym="العضو العددي þri وحده؛ صور form-of المنفصلة لا تولد أحكاما جديدة.",
        notes=(
            "الحكم NUCLEUS-ECHO لأن معنى النواة المجمدة أوسع من العدد، مع أن معنى الأسرة "
            "العربية والفرعية مباشر."
        ),
    ),
    "en-derc-sga-noun-R8IVtfcO": positive(
        root="درك",
        degree="جذر كامل",
        sound=(
            "الهيكل d-r-k مطابق للجذر د-r-k بعد قراءة c القديمة من نطق المصدر /dʲerk/ بوصفها k؛ "
            "لا صف إبدال مستحدث."
        ),
        orbit="مدار 4: الآلة أو العضو الأداتي، العين عضو الرؤية، وهي إدراك الشيء بالبصر.",
        branch_radiation=(
            "الأعضاء المعجمية المدعومة=1؛ سلاسل المعنى المدعومة=1؛ عضو eye وحده."
        ),
        arabic_radiation=(
            "الأعضاء المعجمية المدعومة=1؛ سلاسل المعنى المدعومة=1؛ أدرك ببصره في سلسلة الرؤية."
        ),
        bridges=(
            "الجذر درك؛ النواة در؛ نطق /dʲerk/؛ الأصل الكلتي *derkom ومعناه «أن يرى»؛ "
            "الجسر LEXICON-INTERNAL من نص الصحاح ولسان العرب؛ فصل متجانس berry."
        ),
        homonym=(
            "derc «eye» من *derkom مفصول عن derc «berry» من *derkos في السطر التالي، "
            "وعن عضو hole في المدخل نفسه."
        ),
        notes=(
            "المدار خطوة واحدة من فعل الرؤية إلى عضوها. عضو hole لا يرث الحكم، ومتجانس berry "
            "له صورة أقدم أخرى."
        ),
    ),
    "en-beorht-ang-adj--f4Gpxx~": candidate(
        root="برق",
        degree="جذر كامل أولا",
        sound=(
            "ب ور ثابتان؛ ق إلى k بصف GUT-01، ثم k إلى h بصف BR-GRIM-01. تبقى t في berht "
            "بلا تعرية صرفية منشورة داخل المصدر."
        ),
        orbit="مدار 7: الصفة أو الحال، bright وclear صفة اللمعان والظهور.",
        state="MORPHOLOGY-GAP",
        barrier=(
            "النوع=MORPHOLOGY-GAP؛ يتطلب=تحليل منشور يثبت وظيفة t في *berht قبل تعريتها"
        ),
        bridges=(
            "الجذر برق؛ النواة بر؛ GUT-01 وBR-GRIM-01؛ مروحة البرق في العين والصحاح؛ "
            "الجسر الدلالي قائم، لكن التعرية الصرفية غير مكتملة."
        ),
        homonym="العضو beorht «bright, clear» وحده؛ لا يستمد حكمه من أسماء الأعلام المشتقة.",
        notes="الصوت والمعنى واعدان، لكن إزالة t اختلاق إن سبقت المصدر؛ لذلك لا حكم.",
    ),
    "en-græs-ang-noun-9sxbCFth": candidate(
        root="غرس",
        degree="جذر كامل أولا",
        sound=(
            "r وs ثابتان، لكن وصل g الإنجليزية القديمة بالغين العربية يحتاج صف g إلى غ "
            "غير موجود في الشبكة المجمدة."
        ),
        orbit="مدار 5: الأثر أو الناتج، grass نبات نام، والغرس شجر مثبت في الأرض.",
        state="TOOL-GAP",
        barrier=(
            "النوع=TOOL-GAP؛ يتطلب=قراءة مجمدة لغرس، ومعها قرار مستقل في صف g إلى غ"
        ),
        bridges=(
            "المادة غرس في العين والصحاح؛ أصل græs منشور بمعنى النمو والاخضرار؛ "
            "الجسر الدلالي ممكن، لكن الأداة تفتقد قراءة الجذر والصف الصوتي."
        ),
        homonym="العضو græs «grass» وحده؛ لا ينقل من متجانس أو مركب.",
        notes="فجوتان معلنتان تمنعان TRACE؛ لم ينشأ صف جديد لهذه الكلمة.",
    ),
    "en-trí-sga-num-i1udsME9": candidate(
        root="ثل",
        degree="نواة",
        sound=(
            "LIQ-01 يصل r إلى ل، لكن نقل t الكلتية إلى ث العربية لا يملكه صف كلتي موقع؛ "
            "DENT-01 سامي النطاق وBR-GREC-01 يوناني النطاق، فلا يمددان هنا."
        ),
        orbit="مباشر في الأسرة العددية: three يقابل ثلاثة.",
        state="LAW-GAP",
        barrier=(
            "النوع=LAW-GAP؛ يتطلب=صف كلتي منشور وموقع يصل *t في *tréyes بالثاء العربية"
        ),
        bridges=(
            "الجذر ثلث؛ النواة ثل؛ الأصل الكلتي *trīs والهندوأوروبي *tréyes؛ LIQ-01؛ "
            "مروحة العدد في العين والصحاح؛ بقيت رجل t إلى ث بلا ترخيص."
        ),
        homonym="العضو العددي trí مفصول عن حرف الجر trí ذي معرف آخر.",
        notes="تطابق المعنى لا يعوض صفا فرعيا غائبا؛ لا NUCLEUS-ECHO مع LAW-GAP.",
    ),
    "en-cenn-sga-noun-ny5tM6Nx": candidate(
        root="قنن",
        degree="نواة",
        sound=(
            "نواة q-n تبلغ k-n بصف GUT-01؛ نطق المصدر /kʲen/. لا صف إضافيا."
        ),
        orbit="مدار 8: الجزء من الكل، الرأس أعلى الجسد، والقنة ارتفاع جبلي؛ الجسر فرض رصدي فقط.",
        state="OPEN-CANDIDATE",
        barrier=(
            "النوع=OPEN-CANDIDATE؛ يتطلب=شاهد تحول دلالي منشور بين الرأس والقمة"
        ),
        bridges=(
            "النواة قن؛ GUT-01؛ *kʷennom؛ شاهد القنة في العين وتاج العروس؛ "
            "الجسر OBSERVATIONAL-HYPOTHESIS لا يمنح TRACE."
        ),
        homonym=(
            "cenn «head» من *kʷennom مفصول عن cenn «skin, covering» من *kennos، "
            "وعن عضو end في الأسرة الأولى."
        ),
        notes="الصوت مرخص، لكن تشبيه الرأس بالقمة غير موثق بعد؛ يبقى مرشحا مفتوحا.",
    ),
}


SLAN_ORBITS = {
    "en-slán-sga-adj-qctnr6FV": "مدار 7: الصفة أو الحال، healthy وsound صفتا السلامة والصحة.",
    "en-slán-sga-adj-izNplE3S": "مدار 7: الصفة أو الحال، safe صفة السلامة.",
    "en-slán-sga-adj-XVdmzy14": "مدار 7: الصفة أو الحال، whole صفة التئام الشيء وكماله.",
    "en-slán-sga-noun-gMNfS~2x": "مباشر: immunity وsafety في حقل السلامة.",
    "en-slán-sga-noun-MnKcuCAC": "مباشر: wholeness وhealth في حقل السلامة والصحة.",
    "en-slán-sga-noun-JBwwIBN8": (
        "مدار 5: الأثر أو الناتج، security وguarantee أثران يثبتان السلامة."
    ),
}


for sense_id, slan_orbit in SLAN_ORBITS.items():
    CUSTOM[sense_id] = candidate(
        root="سلم",
        degree="جذر كامل",
        sound=(
            "s وl ثابتان، ويبقى n الكلتية مقابل m العربية. LIQ-02 موثق في لاحقة الجمع "
            "بين الساميات، ولا يملك نطاقا كلتيا يبيح استعماله هنا."
        ),
        orbit=slan_orbit,
        state="LAW-GAP",
        barrier=(
            "النوع=LAW-GAP؛ يتطلب=صف كلتي منشور وموقع يجيز n إلى m"
        ),
        bridges=(
            "الجذر سلم؛ النواة سل؛ *slānos «whole»؛ مروحة السلامة في العين وأساس البلاغة؛ "
            "الجسر الدلالي مباشر، لكن الرجل الصوتية الأخيرة غير مرخصة."
        ),
        homonym=(
            "كل عضو من slán يحكم بمعرفه وحده؛ challenge وindemnity وsound person لا يرثون "
            "مرشح السلامة تلقائيا."
        ),
        notes="أبقيت الأسرة مرئية، ومنعت وراثة الحكم؛ صف واحد غائب يوقف كل عضو على حدة.",
    )


SISTER_DONORS_OE = (
    "old norse",
    "old high german",
    "old saxon",
    "old frisian",
    "gothic",
)
SISTER_DONORS_OI = (
    "welsh",
    "old welsh",
    "middle welsh",
    "brittonic",
    "proto-brittonic",
    "breton",
    "cornish",
)
EXTERNAL_DONOR_MARKERS = (
    "latin",
    "greek",
    "french",
    "anglo-norman",
    "hebrew",
    "arabic",
    "old english",
    "middle english",
    "old irish",
    "irish",
    "scottish gaelic",
)


def clean(value: Any, limit: int | None = None) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\u2014", "،").replace("\u2013", "-")
    text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if limit and len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def iter_records(spec: SourceSpec) -> Iterable[tuple[int, dict[str, Any] | None, str | None]]:
    with spec.source_path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, 1):
            try:
                yield line_no, json.loads(line), None
            except json.JSONDecodeError as exc:
                yield line_no, None, clean(f"{exc.msg} at column {exc.colno}")


def sense_gloss(sense: dict[str, Any]) -> str:
    glosses = sense.get("glosses") or sense.get("raw_glosses") or []
    if not glosses:
        return "(لا يورد العضو glosses)"
    return "; ".join(clean(x) for x in glosses)


def form_targets(sense: dict[str, Any], key: str) -> list[str]:
    result = []
    for item in sense.get(key) or []:
        if isinstance(item, dict) and item.get("word"):
            result.append(clean(item["word"]))
        elif isinstance(item, str):
            result.append(clean(item))
    return result


def first_ipa(entry: dict[str, Any]) -> str:
    for sound in entry.get("sounds") or []:
        if isinstance(sound, dict) and sound.get("ipa"):
            return clean(sound["ipa"])
    return ""


IPA_TOKENS = (
    "t͡ʃ",
    "d͡ʒ",
    "tʃ",
    "dʒ",
    "t̠",
    "d̠",
    "θ",
    "ð",
    "ʃ",
    "ʒ",
    "ɣ",
    "β",
    "ɸ",
    "χ",
    "ʁ",
    "ħ",
    "ʕ",
    "ʔ",
    "ŋ",
    "ɲ",
    "ʍ",
    "ɰ",
    "ɫ",
    "ɾ",
    "ç",
    "ɡ",
    "p",
    "b",
    "t",
    "d",
    "k",
    "g",
    "f",
    "v",
    "s",
    "z",
    "x",
    "h",
    "m",
    "n",
    "l",
    "r",
    "j",
    "w",
    "c",
    "q",
)


def ipa_skeleton(ipa: str) -> str:
    if not ipa:
        return "(لا نطق IPA في المصدر)"
    work = ipa
    tokens: list[str] = []
    i = 0
    while i < len(work):
        matched = None
        for token in IPA_TOKENS:
            if work.startswith(token, i):
                matched = token
                break
        if matched:
            canonical = {
                "t͡ʃ": "tʃ",
                "d͡ʒ": "dʒ",
                "t̠": "t",
                "d̠": "d",
                "ɡ": "g",
                "ɾ": "r",
                "ɫ": "l",
            }.get(matched, matched)
            tokens.append(canonical)
            i += len(matched)
        else:
            i += 1
    return "-".join(tokens) if tokens else "(لم يستخرج هيكل صامت من IPA)"


def etymology(entry: dict[str, Any]) -> str:
    text = clean(entry.get("etymology_text"), 900)
    if not text:
        return "(لم يورد حقل etymology_text صورة أقدم)"
    return f"«{text}»"


def form_relation(sense: dict[str, Any]) -> tuple[str | None, list[str]]:
    tags = set(sense.get("tags") or [])
    targets = form_targets(sense, "form_of")
    if "form-of" in tags or targets:
        return "form", targets
    alternatives = form_targets(sense, "alt_of")
    if "alt-of" in tags or alternatives:
        return "alternative", alternatives
    return None, []


def donor_identity(spec: SourceSpec, entry: dict[str, Any]) -> tuple[str | None, str]:
    etym = clean(entry.get("etymology_text"))
    lower = etym.lower()
    if not etym:
        return None, ""
    transfer_signal = (
        "borrowed from" in lower
        or "calque of" in lower
        or lower.startswith("from latin")
        or lower.startswith("from ancient greek")
        or lower.startswith("from old norse")
        or lower.startswith("from old english")
        or " from latin " in f" {lower} "
    )
    if not transfer_signal:
        return None, ""
    sister_markers = SISTER_DONORS_OE if spec.key == "oe" else SISTER_DONORS_OI
    if any(marker in lower for marker in sister_markers):
        return "sister", etym
    if (
        "borrowed from" in lower
        or "calque of" in lower
        or any(marker in lower for marker in EXTERNAL_DONOR_MARKERS)
    ):
        return "loan", etym
    return None, ""


def default_assessment(
    spec: SourceSpec,
    entry: dict[str, Any],
    sense: dict[str, Any],
) -> dict[str, str]:
    relation, targets = form_relation(sense)
    donor_kind, donor = donor_identity(spec, entry)
    pos = clean(entry.get("pos") or "(بلا POS)")
    ipa = first_ipa(entry)
    source_has_etymology = bool(clean(entry.get("etymology_text")))

    base = {
        "kind": "open",
        "degree": "جذر كامل أولا، ثم نواة؛ لا درجة حكم مصدرة.",
        "arabic_scan": (
            "لم ينتخب مقابل عربي للحكم في هذه البطاقة؛ عدم الانتخاب لا يعني عدم وجود مقابل."
        ),
        "counterpart": (
            "(لا مقابل من الأداة المجمدة): بقي العضو في جرد الاسترداد من غير حكم."
        ),
        "sound": (
            f"شاشة الجرد من IPA: {ipa_skeleton(ipa)}"
            if ipa
            else "لا مسار حكم؛ المصدر لا يورد IPA لهذا العضو."
        ),
        "orbit": "غير مصدر؛ لا يسمى مدار قبل قيام مرشح صوتي ودلالي.",
        "filter": "لم يسم المصدر مانحا أجنبيا لهذا العضو.",
        "homonym": (
            "ثبتت الهوية بمعرف العضو وسطر المصدر؛ لا ينقل معنى من عضو آخر يشترك في الرسم."
        ),
        "orphan": "غير محسوب قبل قيام مرشح قابل للحكم.",
        "branch_radiation": "غير محسوب؛ لا إشعاع مدعوم قبل الحكم الموجب.",
        "arabic_radiation": "غير محسوب؛ لا إشعاع مدعوم قبل الحكم الموجب.",
        "bridges": (
            "فحصت هوية العضو واللمة وPOS والمعنى وIPA والإتيمولوجيا وعلاقة form-of؛ "
            "بقي توليد المقابل العربي والجسر العابر للفروع فجوة ظاهرة."
        ),
        "state": "TOOL-GAP",
        "judgment": "(لا حكم صادر)",
        "barrier": (
            "النوع=TOOL-GAP؛ يتطلب=مرشح عربي مولد من ملف تطبيع فرعي موقع لهذا العضو"
        ),
        "notes": (
            "بطاقة تغطية كاملة للعضو على طبقة المصدر؛ لم تحول الفجوة إلى NO-TRACE."
        ),
    }

    if donor_kind == "loan":
        base.update(
            {
                "kind": "closure",
                "degree": "لم تفتح المقارنة؛ المصفاة سبقت الحكم.",
                "arabic_scan": "لم تفتح مروحة عربية لأن المانح الأجنبي مسمى في المصدر.",
                "counterpart": "(لا مقابل): العضو معزول في مسار الاقتراض.",
                "sound": "لا مسار مقارنة؛ المسار التاريخي المسمى هو الاقتراض.",
                "orbit": "غير مطبق؛ المصفاة سابقة للمدار.",
                "filter": f"يعزل مسارا: {donor}",
                "homonym": (
                    "هوية العضو مقيدة بمعرفه ومانحه المسمى؛ لا تنقل إلى متجانس موروث."
                ),
                "bridges": (
                    "فحص المانح والتسلسل الزمني وهوية العضو؛ أغلقت المصفاة المقارنة."
                ),
                "state": "READY",
                "judgment": "LOANWORD",
                "barrier": "النوع=READY؛ يتطلب=لا شيء، المانح الأجنبي مسمى",
                "notes": (
                    "إغلاق مصدري، لا سالب تاريخي ولا أثر موجب. يفحص التوأم الأصيل في بطاقة "
                    "مستقلة إن ورد في المورد."
                ),
            }
        )
        return base

    if donor_kind == "sister":
        base.update(
            {
                "kind": "closure",
                "degree": "لم تفتح شهادة مستقلة؛ النقل داخل البيت يسقط استقلال العضو.",
                "arabic_scan": "لم تفتح مروحة عربية بعد إحالة السلسلة إلى اللسان المانح.",
                "counterpart": "(لا مقابل): إحالة داخل الفرع إلى المانح المسمى.",
                "sound": "لا مسار مقارنة مستقل؛ المصدر يسمي نقلا من لسان أخت.",
                "orbit": "غير مطبق؛ المصفاة سابقة للمدار.",
                "filter": f"يعزل مسارا داخل البيت: {donor}",
                "homonym": (
                    "هوية العضو والمانح مقيدان؛ لا يحسب شاهدا مستقلا لهذا اللسان."
                ),
                "bridges": (
                    "فحص عمق النقل والمانح وهوية العضو؛ أحيل الزوج إلى المانح."
                ),
                "state": "READY",
                "judgment": "(لا حكم صادر؛ إحالة داخل البيت)",
                "barrier": "النوع=READY؛ يتطلب=فحص الزوج في ملف اللسان المانح إن كان في النطاق",
                "notes": "إغلاق استقلال لا LOANWORD أجنبي، عملا بقاعدة عمق القرض.",
            }
        )
        return base

    if relation == "form":
        target_text = "، ".join(targets) if targets else "(هدف غير مسمى)"
        if spec.key == "oe" and not any(
            target in JUDGED_FORM_BASES for target in targets
        ):
            base.update(
                {
                    "kind": "candidate",
                    "degree": "لم تفتح المقارنة؛ الأصل المحال إليه غير محكوم.",
                    "arabic_scan": "لم تفتح مروحة عربية قبل قراءة الأصل المحال إليه.",
                    "counterpart": f"(لا مقابل مستقل): الإحالة المفتوحة إلى {target_text}.",
                    "sound": "لا مسار مستقل؛ يلزم حكم الأصل أو قراءة الصورة نفسها.",
                    "orbit": "غير مطبق؛ وحدة الحكم لم تغلق بعد.",
                    "filter": f"إحالة form-of مفتوحة إلى {target_text}.",
                    "homonym": "حفظت الصورة عضوا مستقلا ولم تورث حكم أصل غير محكوم.",
                    "bridges": "فحص رابط form-of ومعرف العضو والهدف؛ بقي الأصل مفتوحا.",
                    "state": "RECOVERY-OPEN",
                    "judgment": "(لا حكم صادر؛ FORM-VOID-REOPENED)",
                    "barrier": "النوع=QUEUE؛ يتطلب=قراءة الأصل أولا أو الحكم في الصورة نفسها",
                    "notes": "عضو تغطية مفتوح بموجب القسم 26، لا إغلاق هوية ولا NO-TRACE.",
                }
            )
            return base
        base.update(
            {
                "kind": "closure",
                "degree": "لم تفتح المقارنة؛ المصدر يوسم العضو form-of.",
                "arabic_scan": "لم تفتح مروحة عربية لصورة صرفية محالة إلى لمتها.",
                "counterpart": f"(لا مقابل مستقل): الإحالة إلى {target_text}.",
                "sound": "لا مسار مستقل؛ الصورة الصرفية ترتبط بلمتها ولا تولد مرشحا جديدا.",
                "orbit": "غير مطبق؛ وحدة الحكم هي اللمة المحال إليها.",
                "filter": f"إغلاق هوية صرفية: form-of {target_text}.",
                "homonym": (
                    "حفظت الصورة عضوا في التغطية، ولم تورث حكم اللمة ولم تولد حكما مكررا."
                ),
                "bridges": "فحص رابط form-of ومعرف العضو والهدف؛ لا جسر مستقل.",
                "state": "READY",
                "judgment": "(لا حكم صادر؛ FORM-OF-ISOLATED)",
                "barrier": "النوع=READY؛ يتطلب=لا شيء، الإحالة الصرفية مسماة",
                "notes": "إغلاق هوية، لا NO-TRACE.",
            }
        )
        return base

    if pos == "name" and spec.key == "oe":
        base.update(
            {
                "kind": "candidate",
                "degree": "لم تفتح المقارنة؛ جذر اسم العلم باق في طابور الاستخراج.",
                "arabic_scan": "لم تفتح مروحة عربية قبل استخراج جذر الاسم من مصدر مسمى.",
                "counterpart": "(لا مقابل مستقل): جذر العلم لم يغلق بعد.",
                "sound": "لا مسار حكم قبل استخراج الجذر؛ التشابه الاسمي لا يكفي.",
                "orbit": "غير مطبق.",
                "filter": "اسم علم مفتوح لاستخراج الجذر؛ لا استبعاد من النظر.",
                "homonym": "العلم مفصول عن كل اسم عام يشاركه الرسم، مع بقاء جذره مفتوحا.",
                "bridges": "فحص POS وهوية العضو ووجود etymology_text؛ بقي استخراج الجذر.",
                "state": "NAME-ROOT-OPEN" if source_has_etymology else "NAME-ROOT-SOURCE-GAP",
                "judgment": "(لا حكم صادر؛ NAME-ROOT-OPEN)",
                "barrier": (
                    "النوع=NAME-ROOT-OPEN؛ يتطلب=استخراج الجذر المنشور"
                    if source_has_etymology
                    else "النوع=NAME-ROOT-SOURCE-GAP؛ يتطلب=مصدر فرعي لأصل العلم"
                ),
                "notes": "عضو تغطية مفتوح بموجب القسم 26، لا إغلاق علم ولا حكم سالب.",
            }
        )
        return base

    if relation == "alternative":
        target_text = "، ".join(targets) if targets else "(هدف غير مسمى)"
        base["notes"] = (
            f"المصدر يوسم العضو alt-of لـ {target_text}؛ بقي عضوا مرشحا ولم يغلق بوصفه form-of."
        )

    if not source_has_etymology or not ipa:
        missing = []
        if not source_has_etymology:
            missing.append("etymology_text")
        if not ipa:
            missing.append("IPA")
        needed = " و".join(missing)
        base.update(
            {
                "state": "SOURCE-GAP",
                "barrier": f"النوع=SOURCE-GAP؛ يتطلب=مصدر فرعي يثبت {needed}",
                "notes": (
                    f"العضو مفحوص ومثبت، لكن المصدر لا يورد {needed}؛ لا حكم ولا سالب."
                ),
            }
        )
    return base


def assess(
    spec: SourceSpec,
    entry: dict[str, Any],
    sense: dict[str, Any],
) -> dict[str, str]:
    sense_id = clean(sense.get("id"))
    if sense_id in CUSTOM:
        return CUSTOM[sense_id]
    return default_assessment(spec, entry, sense)


def scan(spec: SourceSpec) -> dict[str, Any]:
    actual_sha = sha256(spec.source_path)
    actual_bytes = spec.source_path.stat().st_size
    if actual_sha != spec.expected_sha256:
        raise RuntimeError(
            f"{spec.key}: source SHA changed: {actual_sha} != {spec.expected_sha256}"
        )
    if actual_bytes != spec.expected_bytes:
        raise RuntimeError(
            f"{spec.key}: source size changed: {actual_bytes} != {spec.expected_bytes}"
        )

    valid_records = 0
    member_count = 0
    bad_lines: list[int] = []
    id_counts: dict[str, int] = {}
    positive_count = 0
    closure_count = 0
    state_counts: dict[str, int] = {}
    judgment_counts: dict[str, int] = {}

    for line_no, entry, error in iter_records(spec):
        if error:
            bad_lines.append(line_no)
            continue
        assert entry is not None
        valid_records += 1
        for sense in entry.get("senses") or []:
            member_count += 1
            sense_id = clean(sense.get("id"))
            id_counts[sense_id] = id_counts.get(sense_id, 0) + 1
            assessment = assess(spec, entry, sense)
            if assessment["kind"] == "positive":
                positive_count += 1
            if assessment["kind"] == "closure":
                closure_count += 1
            state = assessment["state"]
            judgment = assessment["judgment"]
            state_counts[state] = state_counts.get(state, 0) + 1
            judgment_counts[judgment] = judgment_counts.get(judgment, 0) + 1

    duplicate_ids = tuple(sorted(k for k, v in id_counts.items() if v > 1))
    if valid_records != spec.expected_records:
        raise RuntimeError(
            f"{spec.key}: record count changed: {valid_records} != {spec.expected_records}"
        )
    if member_count != spec.expected_members:
        raise RuntimeError(
            f"{spec.key}: member count changed: {member_count} != {spec.expected_members}"
        )
    if tuple(bad_lines) != spec.expected_bad_lines:
        raise RuntimeError(
            f"{spec.key}: bad lines changed: {tuple(bad_lines)} != {spec.expected_bad_lines}"
        )
    if duplicate_ids != spec.expected_duplicate_ids:
        raise RuntimeError(
            f"{spec.key}: duplicate ids changed: {duplicate_ids} != "
            f"{spec.expected_duplicate_ids}"
        )

    return {
        "sha256": actual_sha,
        "bytes": actual_bytes,
        "valid_records": valid_records,
        "members": member_count,
        "bad_lines": bad_lines,
        "duplicate_ids": duplicate_ids,
        "positive": positive_count,
        "closures": closure_count,
        "states": state_counts,
        "judgments": judgment_counts,
    }


def source_note(spec: SourceSpec, line_no: int, sense_index: int, sense_id: str) -> str:
    return (
        f"Kaikki.org {spec.language_en} dictionary، المورد المثبت {spec.pin}، "
        f"سطر JSONL {line_no}، عضو {sense_index}، sense.id={sense_id}"
    )


def write_card(
    handle,
    spec: SourceSpec,
    line_no: int,
    entry: dict[str, Any],
    sense_index: int,
    sense: dict[str, Any],
) -> None:
    sense_id = clean(sense.get("id"))
    word = clean(entry.get("word") or "(بلا لمة)")
    pos = clean(entry.get("pos") or "(بلا POS)")
    gloss = sense_gloss(sense)
    ipa = first_ipa(entry)
    assessment = assess(spec, entry, sense)
    relation, targets = form_relation(sense)
    relation_text = ""
    if relation:
        relation_text = (
            f"؛ علاقة المصدر={relation}"
            + (f" إلى {', '.join(targets)}" if targets else "")
        )
    lemma_display = f"{word}، IPA {ipa}" if ipa else f"{word}، بلا IPA"
    citation = source_note(spec, line_no, sense_index, sense_id)

    handle.write(f"### بطاقة: {word} «{gloss}»\n")
    handle.write("- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)\n")
    handle.write(
        f"- الكلمةُ في الفرع: {lemma_display}؛ POS={pos}؛ المعرّف المركب="
        f"{sense_id}@L{line_no}S{sense_index}.\n"
    )
    handle.write(
        f"- أقدمُ صورةٍ مستعادة: {etymology(entry)} [{citation}، حقل etymology_text].\n"
    )
    handle.write(
        "- الخطوةُ صفر (التعرية بصرف الفرع): ثبتت اللمة المصدرية ولم تنزع لاحقة على "
        f"التخمين؛ اللب الجردي={ipa_skeleton(ipa)}{relation_text}.\n"
    )
    handle.write(f"- درجةُ المقارنة: {assessment['degree']}\n")
    handle.write(f"- مسحُ المعاني العربيّة: {assessment['arabic_scan']}\n")
    handle.write(f"- المقابلُ من اللسان: {assessment['counterpart']}\n")
    handle.write(f"- مسارُ الصوت: {assessment['sound']}\n")
    handle.write(f"- المعنى من قاموس الفرع: «{gloss}» [{citation}، حقل glosses].\n")
    handle.write(f"- المدار: {assessment['orbit']}\n")
    handle.write(f"- المصفاة: {assessment['filter']}\n")
    handle.write(
        f"- فصلُ المتجانسات والاقتراض: {assessment['homonym']}\n"
    )
    handle.write(f"- مؤشر اليتم: {assessment['orphan']}\n")
    handle.write(
        f"- إشعاع الأسرة في الفرع: {assessment['branch_radiation']}\n"
    )
    handle.write(
        f"- إشعاع الأسرة في العربية: {assessment['arabic_radiation']}\n"
    )
    handle.write(
        f"- جسورُ الاسترداد المفحوصة: {assessment['bridges']}\n"
    )
    handle.write(f"- حالةُ الإغلاق: {assessment['state']}\n")
    handle.write(f"- عائق: {assessment['barrier']}\n")
    handle.write(f"- الحكم (استكشاف): {assessment['judgment']}\n")
    handle.write(f"- ملاحظات: {assessment['notes']}\n\n")


def summary_rows(spec: SourceSpec) -> list[tuple[str, str, str]]:
    if spec.key == "oe":
        return [
            ("horn", "horn، antler", "ROOT-TRACE على عضوين"),
            ("burg", "fortified place: fortress, castle", "ROOT-TRACE"),
            ("þri", "three", "NUCLEUS-ECHO"),
            ("beorht", "bright, clear", "MORPHOLOGY-GAP"),
            ("græs", "grass", "TOOL-GAP ومعه فجوة صف"),
        ]
    return [
        ("derc", "eye", "ROOT-TRACE"),
        ("trí", "three", "LAW-GAP"),
        ("slán", "safe، whole، healthy، safety، health، security", "LAW-GAP"),
        ("cenn", "head", "OPEN-CANDIDATE"),
    ]


def write_header(handle, spec: SourceSpec, stats: dict[str, Any]) -> None:
    handle.write(f"# قراءة {spec.language_ar}\n\n")
    handle.write(
        "**الحالة:** طبقةُ الاستكشاف، سجل الأحكام والإغلاقات الكاملة. هذه الوثيقة تثبت ما "
        "كان في لقطة المورد يوم 2026-07-30؛ ومصائر الأعضاء غير المحكومة مثبتة آليا في "
        "[`lane_d_coverage.jsonl`](../data/lane_d_coverage.jsonl).\n\n"
    )
    handle.write(
        "**مرجع البروتوكول القانوني:** "
        "[ميثاق الاستكشاف عبر الألسن](../exploration-charter.md).\n\n"
    )
    handle.write("حقول بطاقة RECOVERY-v2 المفعلة في كل بطاقة أدناه:\n\n")
    handle.write(
        "> - إصدارُ البروتوكول:\n"
        "> - الكلمةُ في الفرع:\n"
        "> - أقدمُ صورةٍ مستعادة:\n"
        "> - الخطوةُ صفر (التعرية بصرف الفرع):\n"
        "> - درجةُ المقارنة:\n"
        "> - مسحُ المعاني العربيّة:\n"
        "> - المقابلُ من اللسان:\n"
        "> - مسارُ الصوت:\n"
        "> - المعنى من قاموس الفرع:\n"
        "> - المدار:\n"
        "> - المصفاة:\n"
        "> - فصلُ المتجانسات والاقتراض:\n"
        "> - مؤشر اليتم:\n"
        "> - إشعاع الأسرة في الفرع:\n"
        "> - إشعاع الأسرة في العربية:\n"
        "> - جسورُ الاسترداد المفحوصة:\n"
        "> - حالةُ الإغلاق:\n"
        "> - عائق:\n"
        "> - الحكم (استكشاف):\n"
        "> - ملاحظات:\n\n"
        "<!-- RECOVERY-PROTOCOL-v2 -->\n"
        "<!-- RADIATION-FIELDS-v1 -->\n\n"
    )
    handle.write("## ميثاق الجولة\n\n")
    handle.write(
        f"- موقع الفرع: {spec.branch_ar}. درجة البدء المتوقعة هي النواة، مع تجربة الجذر "
        "الكامل أولا حين تحفظه الصورة.\n"
    )
    handle.write(
        "- بنية الفرع صرفية تقوم على اللمة والساق والتصريف، لا على جذر عربي ثلاثي؛ "
        "لذلك تحفظ الخطوة صفر اللمة، ولا تحيل صورة إلى غيرها إلا حين يسمي المصدر form-of.\n"
    )
    handle.write(
        "- وحدة التغطية هي عضو المعنى صاحب sense.id، لا رسم الكلمة ولا قائمة forms. "
        "يحمل الحكم الموجب أو الإغلاق النهائي بطاقة RECOVERY-v2 كاملة، ويحمل غير المحكوم "
        "سطر مصير واحدا في `../data/lane_d_coverage.jsonl`.\n"
    )
    handle.write(
        "- لم يستخدم حد محارف لاستبعاد سجل؛ دخل كل سطر JSON صالح، لذلك لا يقوم العدد على "
        "تخمين كتلة يونيكود. استعمل IPA المصدر في شاشة الجرد حيث ورد.\n"
    )
    if spec.key == "oe":
        handle.write(
            "- حارس الاستقلال: لم تفتح أرقام القوطية أو النوردية ولا أحكام ملفيهما قبل "
            "إقفال هذه القراءة. أسماء القربى التي يوردها etymology_text داخل مورد الإنجليزية "
            "القديمة بقيت بيانات مصدر، لا نتائج مستوردة.\n"
        )
    else:
        handle.write(
            "- حارس الاستقلال: بنيت القراءة من مورد الإيرلندية القديمة نفسه ومن الأدوات "
            "العربية المجمدة، بلا نقل أحكام من ملف الويلزية.\n"
        )
    handle.write(
        "- لا NO-TRACE آلي في هذه الجولة. العضو الذي لا تكتمل بوابته يبقى فجوة صريحة، "
        "والقرض لا يعزل إلا بمانح مسمى في etymology_text.\n\n"
    )
    handle.write("## تثبيت اللقطة والمصدر\n\n")
    handle.write(f"- اسم اللقطة: `{spec.pin}`.\n")
    handle.write(f"- المسار: `{spec.source_path.relative_to(ROOT).as_posix()}`.\n")
    handle.write(f"- SHA-256: `{stats['sha256']}`.\n")
    handle.write(f"- الحجم: {stats['bytes']} بايت.\n")
    handle.write(
        f"- المصدر المسمى: Kaikki.org {spec.language_en} dictionary، مشتق من Wiktionary، "
        "كما يسميه `Resources/README.md`.\n"
    )
    handle.write(
        "- قائمة الاقتراض المستعملة: عبارات المانح المسماة في etymology_text داخل اللقطة "
        "نفسها؛ تنقل العبارة المصدرية إلى بطاقة العضو، ولا تستنتج قائمة مانحين من الرسم.\n"
    )
    handle.write(
        f"- حدود التغطية: {stats['valid_records']} سجل JSON صالح، "
        f"{stats['members']} عضو معنى، ولكل عضو مصير مسجل بلا استثناء.\n"
    )
    if stats["bad_lines"]:
        lines = "، ".join(str(x) for x in stats["bad_lines"])
        handle.write(
            f"- عيب المصدر: السطر {lines} غير مكتمل نحويّا، فلا يمكن استخراج هوية عضو منه؛ "
            "سجل SOURCE-GAP في حدود اللقطة ولم يخترع له صف.\n"
        )
    else:
        handle.write("- عيب المصدر: لا سطر JSON معطوبا في اللقطة المثبتة.\n")
    if stats["duplicate_ids"]:
        ids = "، ".join(f"`{x}`" for x in stats["duplicate_ids"])
        handle.write(
            f"- تصادم هوية المصدر: المعرّف {ids} مكرر؛ لذلك يضاف سطر JSON ورقم العضو إلى "
            "المعرّف المركب، وتبقى البطاقتان مستقلتين.\n"
        )
    else:
        handle.write("- تصادم هوية المصدر: لا sense.id مكررا في اللقطة.\n")
    handle.write("\n## محاسبة الجولة، رقمان منفصلان\n\n")
    handle.write(
        f"- الأحكام الموجبة: {stats['positive']}، وهي TRACE أو ECHO فقط.\n"
    )
    handle.write(
        f"- الإغلاقات المصدرية والهوياتية: {stats['closures']}، وتشمل القرض بمانح مسمى، "
        "والنقل داخل البيت، وform-of، واسم العلم الصريح. لا يضاف الرقمان بعضهما إلى بعض.\n\n"
    )
    handle.write("## مواضع الحكم والفجوات البارزة\n\n")
    handle.write("| الصورة | معنى العضو | النتيجة |\n")
    handle.write("|---|---|---|\n")
    for word, gloss, result in summary_rows(spec):
        handle.write(f"| {word} | {gloss} | {result} |\n")
    handle.write(
        "\nالجدول دليل وصول، لا بديل من البطاقة الكاملة عند الحكم أو الإغلاق ولا من سجل "
        "التغطية الآلي عند عدم الإصدار.\n\n"
    )
    handle.write("## البطاقات العضوية الكاملة: الأحكام والإغلاقات\n\n")


def correction_tail(spec: SourceSpec) -> str:
    if not spec.output_path.exists():
        return ""
    current = spec.output_path.read_text(encoding="utf-8")
    marker = re.search(r"^## تصحيحٌ", current, re.MULTILINE)
    if not marker:
        return ""
    return current[marker.start() :].rstrip() + "\n"


def coverage_row(
    spec: SourceSpec,
    line_no: int,
    sense_index: int,
    entry: dict[str, Any],
    sense: dict[str, Any],
    assessment: dict[str, str],
    queue_sequence: int,
) -> dict[str, Any]:
    sense_id = clean(sense.get("id"))
    return {
        "member_id": f"{sense_id}@L{line_no}S{sense_index}",
        "language": spec.language_en,
        "form": clean(entry.get("word") or "(بلا لمة)"),
        "branch_meaning": sense_gloss(sense),
        "non_issuance_reason": assessment["barrier"],
        "batch_number": (queue_sequence - 1) // BATCH_SIZE + 1,
    }


def build(spec: SourceSpec) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    stats = scan(spec)
    retained_tail = correction_tail(spec)
    coverage: list[dict[str, Any]] = []
    queue_sequence = 0
    spec.output_path.parent.mkdir(parents=True, exist_ok=True)
    with spec.output_path.open("w", encoding="utf-8", newline="\n") as handle:
        write_header(handle, spec, stats)
        for line_no, entry, error in iter_records(spec):
            if error:
                queue_sequence += 1
                continue
            assert entry is not None
            for sense_index, sense in enumerate(entry.get("senses") or [], 1):
                queue_sequence += 1
                assessment = assess(spec, entry, sense)
                if assessment["kind"] in {"positive", "closure"}:
                    write_card(handle, spec, line_no, entry, sense_index, sense)
                else:
                    coverage.append(
                        coverage_row(
                            spec,
                            line_no,
                            sense_index,
                            entry,
                            sense,
                            assessment,
                            queue_sequence,
                        )
                    )
        handle.write("## إقفال الجولة\n\n")
        handle.write(
            f"- الأحكام الموجبة: {stats['positive']}.\n"
            f"- الإغلاقات المصدرية والهوياتية: {stats['closures']}.\n"
            f"- مصائر الأعضاء غير المحكومة في سجل التغطية الآلي: {len(coverage)}.\n"
            "- لم يصدر NO-TRACE؛ بقيت الفجوات تحت أسمائها، ولم ينشأ صف صوتي جديد.\n"
        )
        if retained_tail:
            handle.write("\n")
            handle.write(retained_tail)
    expected_coverage = stats["members"] - stats["positive"] - stats["closures"]
    if len(coverage) != expected_coverage:
        raise RuntimeError(
            f"{spec.key}: coverage rows {len(coverage)} != expected {expected_coverage}"
        )
    return stats, coverage


def verify_output(
    spec: SourceSpec,
    stats: dict[str, Any],
    coverage: list[dict[str, Any]],
) -> dict[str, int]:
    text = spec.output_path.read_text(encoding="utf-8")
    cards = text.count("\n### بطاقة:")
    expected_cards = stats["positive"] + stats["closures"]
    if cards != expected_cards:
        raise RuntimeError(f"{spec.key}: cards {cards} != expected {expected_cards}")
    em_dash = text.count("\u2014")
    en_dash = text.count("\u2013")
    no_trace = len(re.findall(r"^- الحكم \(استكشاف\): NO-TRACE$", text, re.M))
    if em_dash or en_dash:
        raise RuntimeError(
            f"{spec.key}: long dashes remain: em={em_dash}, en={en_dash}"
        )
    if no_trace:
        raise RuntimeError(f"{spec.key}: fabricated NO-TRACE count={no_trace}")
    required_fields = (
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
        "- عائق:",
        "- الحكم (استكشاف):",
        "- ملاحظات:",
    )
    for field in required_fields:
        count = len(re.findall(rf"^{re.escape(field)}", text, re.M))
        if count != cards:
            raise RuntimeError(
                f"{spec.key}: field {field!r} count={count} != cards={cards}"
            )
    card_ids = set(
        re.findall(r"المعرّف المركب=([^\n]+)\.$", text, re.MULTILINE)
    )
    coverage_ids = {row["member_id"] for row in coverage}
    if len(card_ids) != cards:
        raise RuntimeError(f"{spec.key}: duplicate or missing full-card identities")
    if len(coverage_ids) != len(coverage):
        raise RuntimeError(f"{spec.key}: duplicate coverage identities")
    if card_ids & coverage_ids:
        raise RuntimeError(f"{spec.key}: card/coverage identity overlap")
    if len(card_ids | coverage_ids) != stats["members"]:
        raise RuntimeError(
            f"{spec.key}: registered identities {len(card_ids | coverage_ids)} "
            f"!= members {stats['members']}"
        )
    return {
        "cards": cards,
        "coverage_rows": len(coverage),
        "registered_members": len(card_ids | coverage_ids),
        "em_dash": em_dash,
        "en_dash": en_dash,
        "no_trace": no_trace,
    }


def main() -> None:
    results = {}
    all_coverage: list[dict[str, Any]] = []
    for spec in SOURCES:
        stats, coverage = build(spec)
        checks = verify_output(spec, stats, coverage)
        all_coverage.extend(coverage)
        results[spec.key] = {
            "output": str(spec.output_path),
            "positive": stats["positive"],
            "closures": stats["closures"],
            **checks,
        }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    coverage_text = "".join(
        json.dumps(row, ensure_ascii=False) + "\n" for row in all_coverage
    )
    COVERAGE_PATH.write_text(coverage_text, encoding="utf-8", newline="\n")
    if len({row["member_id"] for row in all_coverage}) != len(all_coverage):
        raise RuntimeError("duplicate cross-language coverage identities")
    results["coverage"] = {
        "output": str(COVERAGE_PATH),
        "rows": len(all_coverage),
    }
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
