# -*- coding: utf-8 -*-
"""حصادُ معاجمِ خشيم المقارِنة (2026-08-10، بأمرِ المؤلّف)

**مَن هو:** الليبيُّ **علي فهمي خشيم**، وكتبُه عناوينُها بنفسِها دعوانا:
«الأكّاديّةُ عربيّة» و«القبطيّةُ عربيّة» و«اللاتينيّةُ عربيّة» و«البرهانُ على
عروبةِ اللغةِ المصريّةِ القديمة» و«الوحدةُ والتنوّعُ في اللهجاتِ العروبيّةِ
القديمة». **وهي ألسنُنا بعينِها**: الأكّاديّةُ والقبطيّةُ والمصريّةُ واللاتينيّة.

**وبنيةُ كتبِه معجميّةٌ لا مقاليّة**، وهذا ما يجعلُها تُحصَدُ آليًّا:

    شمت : قدر، مصير. (من «شم»)
    ع : سمي. سمّى: عيّن، أي قرّر قدره ومصيره، خصّص.

    شزب : لبن.
    ع : شخب. الشّخب: ما خرج من الضرع من اللبن إذا احتُلب.

فالسطرُ الأوّلُ الكلمةُ الأجنبيّةُ بحروفٍ عربيّةٍ ومعناها، والسطرُ الذي يبدأُ
بـ`ع :` فيه **الجذرُ العربيُّ ونصُّ معجمِه**. والعلامةُ `ع` مرساةٌ ثابتةٌ في
الكتابِ كلِّه.

**وعقبتانِ في الاستخراجِ عولِجَتا:**

1. **النصُّ يخرجُ بترتيبٍ بصريٍّ معكوس** لأنّ ملفَّ المسحِ لا يحملُ ترتيبًا
   منطقيًّا: تخرجُ «والعبريين» هكذا «نييربعلاو». فتُقلَبُ حروفُ كلِّ كلمةٍ
   ويُقلَبُ ترتيبُ الكلماتِ في السطر.
2. **المسحُ الضوئيُّ عربيٌّ فقط**، فالحروفُ اللاتينيّةُ في كتابِ اللاتينيّةِ
   سقطَت كلَّها (صفرُ حرفٍ لاتينيٍّ في 234 صفحة). فيُحصَدُ ما كتبَه هو بالعربيّة،
   ويبقى نصُّ الكلمةِ الأجنبيّةِ بالحرفِ الأصليِّ نقصًا مسمًّى يُسَدُّ بمسحٍ ثانٍ.

**ولا حكمَ هنا على زوج.** أمرُ المؤلّف: «استعملْ أعمالَه، لا تحكمْ عليها، واحصدْ
أقصى ما يمكنُ من الصلات».

الاستعمال:
    python scripts/harvest_khashim.py
"""
from __future__ import annotations

import difflib
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORE = pathlib.Path.home() / "AI Projects" / "Resources" / "prior-art"
OUT = ROOT / "data" / "khashim-pairs.json"
SHEET = ROOT / "04-cross-linguistic" / "exploration" / "khashim-harvest.md"

BOOKS = {
    "khashim-akkadian": ("الأكّاديّة", "akkadian"),
    "khashim-coptic": ("القبطيّة", "coptic"),
    "khashim-latin": ("اللاتينيّة", "old-latin"),
    "khashim-dialects": ("اللهجاتُ العروبيّةُ القديمة", "semitic"),
}

AR = re.compile(r"[؀-ۿ]")
# **مرساتانِ لا واحدة**: في «الأكّاديّةُ عربيّة» يكتبُ `ع :` مختصرًا، وفي
# «اللاتينيّةُ عربيّة» يكتبُ `في العربية :` كاملةً ويُخرِجُها المسحُ ناقصةَ
# الصدرِ هكذا `د العربية :` و`بد العربية :`. فمن طلبَ العينَ المفردةَ وحدَها
# خرجَ من كتابِ اللاتينيّةِ بصفر.
RX_AR_LINE = re.compile(r"^\s*(?:ع|[ء-ي]{0,3}\s*العربية)\s*[:：]\s*(.+)$")
# الجذرُ أوّلُ كلمةٍ عربيّةٍ في السطر، وقد يليها شرحُها
RX_ROOT = re.compile(r"^([ء-ي]{2,6})\b")
# الكلمةُ الأجنبيّةُ ومعناها: `شمت : قدر، مصير`
RX_ENTRY = re.compile(r"^\s*([ء-ي][ء-يـ\s]{0,14}?)\s*[:：]\s*(.{2,90})$")
NOISE = ("انظر", "المرجع", "الصفحة", "الفصل", "الباب", "المصدر", "الهامش")


def unmirror(line: str) -> str:
    """يُعادُ السطرُ إلى ترتيبِه المنطقيّ. المسحُ يخرجُه بترتيبِ العينِ لا العقل."""
    if not AR.search(line):
        return line
    return " ".join(w[::-1] for w in line.split()[::-1])


def clean(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"[ـ‌‏‫‬]", "", s)   # تطويلٌ وعلاماتُ اتّجاه
    s = re.sub(r"[«»\"'‘’]", "", s)
    return re.sub(r"\s+", " ", s).strip(" .,؛:،")


def mine(path: pathlib.Path, tongue_ar: str, tongue_key: str) -> list[dict]:
    import fitz                                             # noqa: PLC0415
    doc = fitz.open(path)
    lines: list[str] = []
    for page in doc:
        lines.extend(unmirror(x) for x in page.get_text().splitlines())

    pairs, seen = [], set()
    for i, line in enumerate(lines):
        m = RX_AR_LINE.match(line)
        if not m:
            continue
        ar_side = clean(m.group(1))
        rm = RX_ROOT.match(ar_side)
        if not rm:
            continue
        root = rm.group(1)
        gloss_ar = clean(ar_side[rm.end():])

        # المدخلُ الأجنبيُّ في السطورِ الثلاثةِ التي قبلَه، وأقربُها أولى
        foreign = foreign_sense = ""
        for back in range(1, 4):
            if i - back < 0:
                break
            prev = clean(lines[i - back])
            if not prev or RX_AR_LINE.match(lines[i - back]):
                continue
            em = RX_ENTRY.match(prev)
            if em and not any(n in prev for n in NOISE):
                foreign, foreign_sense = clean(em.group(1)), clean(em.group(2))
                break
        if not foreign:
            # **كتابُ اللاتينيّةِ لا يُخرِجُ رأسَ المدخل** لأنّ حرفَه لاتينيٌّ وقد
            # سقطَ في المسح، فيُؤخَذُ أقربُ سطرٍ عربيٍّ ذي معنًى بوصفِه شرحَ
            # المدخل. والزوجُ يُحفَظُ بنقصٍ مسمًّى لا يُطرَحُ لأجلِه.
            for back in range(1, 4):
                if i - back < 0:
                    break
                prev = clean(lines[i - back])
                if len(prev) >= 4 and AR.search(prev) and not RX_AR_LINE.match(lines[i - back]):
                    foreign_sense = prev[:90]
                    foreign = "(سقطَ حرفُه في المسح)"
                    break
        if not foreign or len(root) < 2:
            continue
        key = (foreign if "سقط" not in foreign else foreign_sense, root)
        if key in seen:
            continue
        seen.add(key)
        pairs.append({
            "tongue_ar": tongue_ar, "tongue": tongue_key,
            "foreign": foreign, "foreign_sense": foreign_sense,
            "arabic_root": root, "arabic_gloss": gloss_ar[:160],
            "source": path.stem,
        })
    return pairs


# ---------------------------------------------- المسحُ الضوئيُّ الجديدُ للكتب
# **لماذا مِعوَلٌ ثانٍ:** المسحُ القديمُ لكتابِ اللاتينيّةِ كان عربيًّا وحدَه فسقطَ
# منه كلُّ حرفٍ لاتينيّ (صفرٌ في 234 صفحة)، فلم يبقَ من المدخلِ إلّا جوابُه. وقد
# أُعيدَ مسحُه بإذنِ المؤلّفِ بمسحٍ يقرأُ الخطَّينِ، فصارَ المدخلُ كاملًا:
#
#     drappus
#     شف ، نسيج ، شاش ، خرقة .
#     * العربية : أذرب . جاء في (اللسان) تحت هذه المادة : ...
#
# فالمدخلُ سطرٌ لاتينيٌّ وحدَه، ويليه معناه بالعربيّة، ثمّ سطرُ الجوابِ الذي
# يبدأُ بنجمةٍ ثمّ «العربية :» ثمّ الجذرُ ونصُّ معجمِه.
RX_OCR_HEAD = re.compile(r"^\s*([A-Za-zĀ-ſ][A-Za-zĀ-ſ\-']{2,22})\s*$")
RX_OCR_ANSWER = re.compile(r"^[\s*·•]*(?:[ء-ي]{0,4}\s*)?العربية\s*[:：]\s*(.+)$")


def mine_ocr(md: pathlib.Path, tongue_ar: str, tongue_key: str) -> list[dict]:
    lines = [clean(x) for x in md.read_text(encoding="utf-8").splitlines()]
    pairs, seen = [], set()
    for i, line in enumerate(lines):
        m = RX_OCR_ANSWER.match(line)
        if not m:
            continue
        ar_side = clean(m.group(1))
        rm = RX_ROOT.match(ar_side)
        if not rm:
            continue
        root, gloss_ar = rm.group(1), clean(ar_side[rm.end():])

        # نص لسان العرب يمتد كثيرًا إلى الأسطر التالية بعد سطر «العربية: مادة»؛
        # لا يجوز اختزاله في ذيل السطر الأول، ولا سيما إذا كان الذيل فارغًا.
        gloss_parts = [gloss_ar] if gloss_ar else []
        for forward in range(1, 10):
            if i + forward >= len(lines):
                break
            continuation = lines[i + forward]
            if RX_OCR_ANSWER.match(continuation) or RX_OCR_HEAD.match(continuation):
                break
            if continuation and AR.search(continuation):
                gloss_parts.append(continuation)
        gloss_ar = clean(" ".join(gloss_parts))

        # المدخلُ اللاتينيُّ في عشرةِ سطورٍ قبلَه، وأقربُها أولى، ومعناه
        # أوّلُ سطرٍ عربيٍّ بعدَه مباشرةً
        foreign = foreign_sense = ""
        head_line = None
        for back in range(1, 11):
            if i - back < 0:
                break
            hm = RX_OCR_HEAD.match(lines[i - back])
            if hm:
                foreign = hm.group(1)
                head_line = i - back + 1
                for sense_line in range(i - back + 1, i):
                    candidate = lines[sense_line]
                    if candidate and AR.search(candidate) and not RX_OCR_ANSWER.match(candidate):
                        foreign_sense = candidate[:90]
                        break
                break
        if not foreign or len(root) < 2:
            continue
        key = (foreign, root)
        if key in seen:
            continue
        seen.add(key)
        pairs.append({
            "tongue_ar": tongue_ar, "tongue": tongue_key,
            "foreign": foreign, "foreign_sense": foreign_sense,
            "arabic_root": root, "arabic_gloss": gloss_ar[:600],
            "source": md.parent.name,
            "source_line": head_line,
        })
    return pairs


def _bare_ar(value: str) -> str:
    value = unicodedata.normalize("NFKC", value or "")
    value = re.sub(r"[\u064b-\u065fـ]", "", value).replace("ٱ", "ا")
    return re.sub(r"[^ء-ي]", "", value)


def _ocr_similarity(left: str, right: str) -> float:
    left, right = _bare_ar(left), _bare_ar(right)
    if not left or not right:
        return 0.0
    return difflib.SequenceMatcher(None, left, right, autojunk=False).ratio()


def recover_latin_heads(rows: list[dict]) -> tuple[list[dict], dict[str, int]]:
    """ردّ رؤوس المسح العربي القديم إلى المسح الجديد بلا إعادة استعمال.

    الرصف عالمي رتيب: لا يطابق إلا الجذر العربي نفسه، ويرجّح داخل التكرار
    اتفاق نص لسان العرب ثم معنى المدخل. وبذلك لا يستطيع رأس متأخر أن يقفز فوق
    رأس سابق، ولا يستطيع صفان قديمان سرقة الرأس الجديد نفسه.
    """
    new = [row for row in rows if row.get("source") == "ocr-latin"]
    old_positions = [
        index for index, row in enumerate(rows)
        if row.get("source") == "khashim-latin"
    ]
    old = [rows[index] for index in old_positions]
    if (len(new), len(old)) != (515, 560):
        raise SystemExit(
            f"تغيّر جرد رصف اللاتينية: الجديد/القديم={len(new)}/{len(old)}"
        )

    n, m, gap = len(old), len(new), -2.0
    scores = [[0.0] * (m + 1) for _ in range(n + 1)]
    paths = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        scores[i][0], paths[i][0] = i * gap, 1
    for j in range(1, m + 1):
        scores[0][j], paths[0][j] = j * gap, 2
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if _bare_ar(old[i - 1]["arabic_root"]) == _bare_ar(new[j - 1]["arabic_root"]):
                match = (
                    7.0
                    + 6.0 * _ocr_similarity(old[i - 1].get("arabic_gloss", ""),
                                             new[j - 1].get("arabic_gloss", ""))
                    + 4.0 * _ocr_similarity(old[i - 1].get("foreign_sense", ""),
                                             new[j - 1].get("foreign_sense", ""))
                )
            else:
                match = -8.0
            choices = (
                scores[i - 1][j - 1] + match,
                scores[i - 1][j] + gap,
                scores[i][j - 1] + gap,
            )
            choice = max(range(3), key=lambda key: choices[key])
            scores[i][j], paths[i][j] = choices[choice], choice

    aligned: list[tuple[int, int]] = []
    i, j = n, m
    while i or j:
        choice = paths[i][j]
        if i and j and choice == 0:
            if _bare_ar(old[i - 1]["arabic_root"]) == _bare_ar(new[j - 1]["arabic_root"]):
                aligned.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i and (not j or choice == 1):
            i -= 1
        else:
            j -= 1
    aligned.reverse()

    repaired = [dict(row) for row in rows]
    recovered = 0
    for old_index, new_index in aligned:
        old_row, new_row = old[old_index], new[new_index]
        if old_row.get("foreign") != "(سقطَ حرفُه في المسح)":
            continue
        target = repaired[old_positions[old_index]]
        target["foreign"] = new_row["foreign"]
        if new_row.get("foreign_sense"):
            target["foreign_sense"] = new_row["foreign_sense"]
        target["ocr_recovery"] = {
            "old_head": "(سقطَ حرفُه في المسح)",
            "old_foreign_sense": old_row.get("foreign_sense", ""),
            "matched_source": "Resources/prior-art/ocr-latin/full.md",
            "source_line": new_row.get("source_line"),
            "matched_new_row": new_index,
            "contract": "الجذر نفسه + رصف رتيب + ترجيح معنى المدخل ونص لسان العرب",
        }
        recovered += 1
    if recovered != 290:
        raise SystemExit(f"تغيّر عدد رؤوس اللاتينية المستردة: {recovered}، والمتوقع 290")
    return repaired, {
        "old_rows_with_fallen_head": 513,
        "heads_recovered": recovered,
        "heads_still_fallen": 513 - recovered,
    }



# ------------------------------------------- «الأكّاديّةُ عربيّة» بعدَ مسحِها الجديد
# **العطبُ الذي يُغلِقُه:** المسحُ القديمُ أسقطَ رأسَ المدخلِ في 242 صفًّا من 588
# (41%)، فكانت ورقةُ الأذُنِ تعرضُ على المؤلّفِ معنًى بلا كلمةٍ يقرؤُها. والمسحُ
# الجديدُ يُخرِجُ المدخلَ مشكولًا كاملًا:
#
#     بِرَاشُ : طَارَ .
#     ع : فَرَشَ . ومنها فَرَاشَةٌ: حشرةٌ تطير... وأفرشَ: ارتفعَ وأقلعَ، أي طار.
RX_AKK_ENTRY = re.compile(r"^\s*([ء-يًٌٍَُِّْـ][ء-يًٌٍَُِّْـ\s]{0,16}?)\s*[:：]\s*(.{2,90})$")


def mine_akkadian_ocr(md: pathlib.Path) -> list[dict]:
    lines = [clean(x) for x in md.read_text(encoding="utf-8").splitlines()]
    pairs, seen = [], set()
    for i, line in enumerate(lines):
        m = RX_AR_LINE.match(line)
        if not m:
            continue
        ar_side = clean(m.group(1))
        rm = RX_ROOT.match(bare_ar(ar_side))
        if not rm:
            continue
        root, gloss = rm.group(1), bare_ar(clean(ar_side))
        foreign = foreign_sense = ""
        for back in range(1, 4):
            if i - back < 0:
                break
            prev = clean(lines[i - back])
            if not prev or RX_AR_LINE.match(lines[i - back]):
                continue
            em = RX_AKK_ENTRY.match(prev)
            if em and not any(n in prev for n in NOISE):
                foreign = bare_ar(clean(em.group(1)))
                foreign_sense = bare_ar(clean(em.group(2)))
                break
        if not foreign or len(root) < 2:
            continue
        key = (foreign, root)
        if key in seen:
            continue
        seen.add(key)
        pairs.append({
            "tongue_ar": "الأكّاديّة", "tongue": "akkadian",
            "foreign": foreign, "foreign_sense": foreign_sense,
            "arabic_root": root, "arabic_gloss": gloss[:200],
            "source": "ocr-akkadian",
        })
    return pairs


OCR_BOOKS = {
    "ocr-latin": ("اللاتينيّة", "old-latin"),
}

# ------------------------------------------------------ «القبطيّةُ عربيّة» بعدَ مسحِها
# **بنيتُه هنا أقربُ ما رأيناه إلى بنيتِنا نحن**، فهو يكتبُ النواةَ الثنائيّةَ
# حروفًا مفرَّقةً في العنوان، ثمّ يردُّها إلى مادّتِها الثلاثيّةِ في المتن:
#
#     ## ب ح  وصل. جاء. حلّ بالمكان   poh
#     في معجم بدج (ص 244) تفيد 'ب ح' ومشتقاتها: بلوغ الغاية، الوصول، النهاية.
#     في مادة 'بحح' العربية (ثلاثي 'بح') : التبحج؛ التمكن في الحلول والمقام.
#
# فالعنوانُ يحملُ النواةَ والمعنى والكلمةَ القبطيّة، والمتنُ يحملُ الجذرَ الثلاثيَّ
# بنصِّ معجمِه. **وهذا لسانُنا الأعلى في نسبةِ النواة (85.6%)**، فبنيةُ كتابِه
# شاهدةٌ على ذلك من طريقٍ مستقلٍّ عنّا.
RX_COPT_HEAD = re.compile(r"^##+\s+(.{2,90}?)\s*$", re.M)
RX_COPT_LATIN = re.compile(r"([a-zàâäèéêëîïôöùûüō][a-zàâäèéêëîïôöùûüō,\s]{1,28})$")
RX_COPT_ROOT = re.compile(r"في\s*مادة\s*['\"‹«]?\s*([ء-ي]{2,6})")
RX_COPT_THREE = re.compile(r"ثلاثي\s*['\"‹«]?\s*([ء-ي]{2,4})")
RX_COPT_BINARY_AFTER = re.compile(
    r"ثنائي(?:ة)?\s*['\"‹«]?\s*([ء-ي]{2,3})(?![ء-ي])"
)
RX_COPT_BINARY_BEFORE = re.compile(
    r"['\"‹«]?\s*([ء-ي]{2,3})(?![ء-ي])\s*['\"›»]?\s*الثنائي"
)


def coptic_nucleus(body: str) -> str:
    """استخرج تسمية خشيم الثنائية، وقد تأتي قبل لفظ «الثنائي» أو بعده."""
    after = RX_COPT_BINARY_AFTER.search(body)
    before = RX_COPT_BINARY_BEFORE.search(body)
    # صيغة «الجذر الثنائي طب» ينبغي أن تعطي `طب` لا الكلمة السابقة `جذر`؛
    # لذلك تكون جهة ما بعد الصفة أولى، ولا نرجع إلى السابقة إلا عند «رم الثنائي».
    if after:
        return after.group(1)
    if before and before.group(1) != "جذر":
        return before.group(1)
    # يكتب خشيم أحيانًا الصيغة «ثلاثي بح» وهو يعني أن بح نواة بحح؛ لا يؤخذ
    # من هذا الباب إلا ما كان ثنائي الحروف فعلًا.
    three = RX_COPT_THREE.search(body)
    return three.group(1) if three and len(three.group(1)) == 2 else ""


def mine_coptic(md: pathlib.Path) -> list[dict]:
    text = md.read_text(encoding="utf-8")
    blocks = re.split(r"(?m)^##+\s+", text)[1:]
    pairs, seen = [], set()
    for block in blocks:
        head, _, body = block.partition("\n")
        head = clean(head)
        m = RX_COPT_LATIN.search(head)
        if not m:
            continue
        coptic = " ".join(m.group(1).split())
        gloss = clean(head[: m.start()])
        rm = RX_COPT_ROOT.search(body[:1400]) or RX_COPT_THREE.search(body[:1400])
        if not rm:
            continue
        root = rm.group(1)
        nucleus = coptic_nucleus(body[:1400])
        key = (coptic, root)
        if key in seen or len(root) < 2:
            continue
        seen.add(key)
        pairs.append({
            "tongue_ar": "القبطيّة", "tongue": "coptic",
            "foreign": coptic, "foreign_sense": gloss[:90],
            "arabic_root": root,
            "arabic_nucleus": nucleus,
            "arabic_gloss": clean(re.sub(r"\s+", " ", body[:220])),
            "source": "ocr-coptic",
        })
    return pairs

# ------------------------------------------------- «البرهانُ على عروبةِ المصريّة»
# **بنيتُه ثلاثيّةٌ لا ثنائيّة**، وهي أقربُ ما رأيناه إلى بطاقاتِنا:
#
#     skher-t 𓊖, defeat, overthrow.
#     سَخَرَتْ : هَزِيمَةٌ، قَلْبٌ.
#
#     ses-t 𓂋, Rec. 15, 152, a garment of some kind, bandlet.
#     * سست : نوع من الثياب، عصابة (شاش، شاشة).
#
# فالسطرُ الأوّلُ نطقُ الكلمةِ المصريّةِ ورمزُها ومعناها الإنجليزيُّ من بدج،
# والثاني مقابلُها العربيُّ ونصُّه. **ويُحفَظُ الرمزُ الهيروغليفيُّ نفسُه** لأنّه
# مرساةُ البطاقةِ عندَنا لا النطقُ وحدَه.
RX_EG_ENTRY = re.compile(
    r"^\s*([a-zāḏḥḫḳṣṭṯẖʿꜣꜥ][a-zāēīōūḏḥḫḳṣṭṯẖʿꜣꜥ0-9\-\.\s]{1,26}?)\s*"
    r"([\U00013000-\U0001342F]*)\s*,\s*(.{4,150})$")
RX_EG_ANSWER = re.compile(r"^[\s*·•]*([ء-ي][ء-يًٌٍَُِّْـ/\s]{0,20}?)\s*[:：]\s*(.{2,180})$")
RX_REFS = re.compile(r"\b(?:B\.?D\.?|U\.?|P\.?|N\.?|M\.?|T\.?|Rec\.?|IV|V|Peasant|Israel|"
                     r"Amen\.?|Ebers|Westc\.?|Hh\.?|Thes\.?|Mar\.?|Copt\.?)[\s\d,\.\(\)A-Za-z]{0,26}")
_TASHKEEL = dict.fromkeys(range(0x064B, 0x0653))


def bare_ar(s: str) -> str:
    return unicodedata.normalize("NFC", s).translate(_TASHKEEL).replace("ـ", "")


def mine_egyptian(md: pathlib.Path) -> list[dict]:
    lines = [x.strip() for x in md.read_text(encoding="utf-8").splitlines()]
    pairs, seen = [], set()
    for i, line in enumerate(lines):
        if AR.search(line):
            continue
        m = RX_EG_ENTRY.match(line)
        if not m:
            continue
        translit = clean(m.group(1))
        glyphs = m.group(2)
        english = clean(RX_REFS.sub("", m.group(3)))
        if len(translit) < 2 or len(english) < 4:
            continue
        # الجوابُ العربيُّ في السطرَينِ التاليَين
        for fwd in (1, 2, 3):
            if i + fwd >= len(lines):
                break
            am = RX_EG_ANSWER.match(lines[i + fwd])
            if not am:
                continue
            arabic = bare_ar(clean(am.group(1))).replace("/", "")
            gloss = bare_ar(clean(am.group(2)))
            if len(re.sub(r"[^ء-ي]", "", arabic)) < 2:
                break
            key = (translit, arabic)
            if key in seen:
                break
            seen.add(key)
            pairs.append({
                "tongue_ar": "المصريّةُ القديمة", "tongue": "egyptian",
                "foreign": translit, "glyphs": glyphs,
                "foreign_sense": english[:110],
                "arabic_root": arabic, "arabic_gloss": gloss[:180],
                "source": "ocr-egyptian2",
            })
            break
    return pairs


# -------------------------------- حصادُ الجُمَلِ الصريحةِ في بقيّةِ كتبِ خشيم
# «رحلةُ الكلماتِ الثانية» و«آلهةُ مصرَ العربيّةُ 2» كتابا فصولٍ لا معجمين؛
# وكذلك كتابُ الندوةِ مجموعةُ بحوثٍ لتسعةِ سابقين. فلا مرساةَ فيهما من قبيل
# `ع :`، ولكنّ صيغةَ النسبةِ صريحةٌ ومتكرّرةٌ:
#
#     في المصرية يسمّى اليوم «ه ر و» ... وهذه مقلوب العربية «وهر»
#     «ق ر» ... وهي العربية: قر
#
# نأخذُ الجملتَينِ ذواتَي الاسمِ القديمِ والمقابلِ العربيِّ ولا نحكمُ عليهما.
CLAIM_TONGUES = [
    (re.compile(r"المصري(?:ة|ه)(?:\s+القديم(?:ة|ه))?"), "المصريّةُ القديمة", "egyptian"),
    (re.compile(r"(?:الأكّادي(?:ة|ه)|الأكادي(?:ة|ه)|البابلي(?:ة|ه)|الآشوري(?:ة|ه))"),
     "الأكّاديّة", "akkadian"),
    (re.compile(r"القبطي(?:ة|ه)"), "القبطيّة", "coptic"),
    (re.compile(r"اللاتيني(?:ة|ه)"), "اللاتينيّة", "old-latin"),
    (re.compile(r"(?:اليوناني(?:ة|ه)|الإغريقي(?:ة|ه)|الاغريقي(?:ة|ه))"),
     "اليونانيّةُ القديمة", "ancient-greek"),
    (re.compile(r"السومري(?:ة|ه)"), "السومريّة", "sumerian"),
    (re.compile(r"(?:الكنعاني(?:ة|ه)|الفينيقي(?:ة|ه)|الأوغاريتي(?:ة|ه)|الاوغاريتي(?:ة|ه))"),
     "الكنعانيّة", "canaanite"),
    (re.compile(r"(?:السرياني(?:ة|ه)|الآرامي(?:ة|ه)|الارامي(?:ة|ه))"),
     "الآراميّة", "aramaic"),
    (re.compile(r"العبري(?:ة|ه)"), "العبريّة", "hebrew"),
    (re.compile(r"(?:السبئي(?:ة|ه)|المسندي(?:ة|ه)|الحميري(?:ة|ه))"),
     "العربيّةُ الجنوبيّةُ القديمة", "old-south-arabian"),
    (re.compile(r"(?:الليبي(?:ة|ه)\s+القديم(?:ة|ه)|الأمازيغي(?:ة|ه)|الامازيغي(?:ة|ه)|التماشق)"),
     "الليبيّةُ القديمة", "ancient-libyan"),
]
RX_CLAIM_MARKER = re.compile(
    r"(?:هي|هى|ذاتها|مقلوب|مكاف|يقابل|تقابل|نكاف|نقابل|يكاف|تكاف|يساو|تساو|"
    r"أصل|اصل|من|ب)\S{0,8}\s+العربي(?:ة|ه)|بالعربي(?:ة|ه)"
)
RX_GUILLEMET = re.compile(r"[«\[]\s*([^»\]\n]{1,36}?)\s*[»\]]")
RX_ARABIC_AFTER = re.compile(r"العربي(?:ة|ه)\s*[:：=]?\s*([ء-ي][ء-يًٌٍَُِّْـ\s/]{1,18})")
CLAIM_AR_NOISE = {
    "العربية", "الفصحى", "الفصيحة", "الفصبحة", "المصرية", "القديمة",
    "اصلا", "في", "من", "الى", "يطلق", "تطلق", "يشرح", "معنى", "وهي", "وهو",
}

CLAIM_BOOKS = {
    "ocr-khashim-journey2": ("علي فهمي خشيم", None),
    "ocr-khashim-gods2": ("علي فهمي خشيم", ("المصريّةُ القديمة", "egyptian")),
    "ocr-khashim-dialects": ("بحوثُ ندوةِ الوحدةِ والتنوّع", None),
}

SYMPOSIUM_AUTHORS = [
    (257, "محمد بهجت قبيسي"),
    (1162, "نائل حنون"),
    (2851, "عكاشة الدالي"),
    (3078, "لؤي محمود سعيد"),
    (4484, "أشرف محمد فتحي"),
    (4937, "سعيد بن عبدالله الدارودي"),
    (7234, "عبدالعزيز سعيد الصويعي"),
    (7489, "أحمد شحلان"),
    (8915, "محمد المختار العرباوي"),
]


def _claim_author(source: str, line: int, fallback: str) -> str:
    if source != "ocr-khashim-dialects":
        return fallback
    author = "علي فهمي خشيم"
    for start, name in SYMPOSIUM_AUTHORS:
        if line < start:
            break
        author = name
    return author


def _claim_token(value: str, *, arabic: bool = False) -> str:
    value = clean(value).strip("()[]{}=<>١٢٣٤٥٦٧٨٩٠0123456789")
    value = re.sub(r"\s+", " ", value).strip()
    if arabic:
        words = re.findall(r"[ء-ي]{2,6}", bare_ar(value))
        if not words or words[0] in CLAIM_AR_NOISE:
            return ""
        return words[0]
    if len(value) > 32 or len(value.split()) > 5:
        return ""
    return value if re.search(r"[ء-يA-Za-z]", value) else ""


def mine_claim_ocr(md: pathlib.Path, source: str, author: str,
                   default_tongue: tuple[str, str] | None) -> list[dict]:
    """يلتقطُ الزوجَ حيثُ سمّى النصُّ اللسانَ القديمَ والعربيّةَ في جملةٍ واحدة.

    يُحفَظُ سياقُ الجملةِ ورقمُ السطرِ لأنّ OCR أرشيفِ الإنترنتِ مؤقّتٌ، ولأنّ
    إعادةَ المسحِ بمسترال ستسمحُ لاحقًا بردِّ الرسمِ القديمِ إذا شوّهه المسحُ.
    """
    # لا نستعمل `clean` هنا لأنّه يطرحُ علامتَي « »، وهما مرساتا طرفَي الزوج.
    lines = [re.sub(r"\s+", " ", unicodedata.normalize("NFC", x)).strip()
             for x in md.read_text(encoding="utf-8").splitlines()]
    rows, seen = [], set()
    for i, line in enumerate(lines):
        if "العربي" not in line and not any(
                "العربي" in lines[j] for j in range(max(0, i - 1), min(len(lines), i + 2))):
            continue
        window = " ".join(lines[max(0, i - 1):min(len(lines), i + 2)])
        marker = RX_CLAIM_MARKER.search(window)
        if not marker:
            continue

        tongue = None
        distances = []
        for rx, tongue_ar, tongue_key in CLAIM_TONGUES:
            for tm in rx.finditer(window):
                distances.append((abs(tm.start() - marker.start()), tongue_ar, tongue_key))
        if distances:
            _, tongue_ar, tongue_key = min(distances)
            tongue = (tongue_ar, tongue_key)
        elif default_tongue:
            tongue = default_tongue
        if not tongue:
            continue

        quotes = list(RX_GUILLEMET.finditer(window))
        after_quotes = [q for q in quotes if marker.start() <= q.start() <= marker.end() + 90]
        if after_quotes:
            aq = min(after_quotes, key=lambda q: abs(q.start() - marker.end()))
            arabic = _claim_token(aq.group(1), arabic=True)
        else:
            am = RX_ARABIC_AFTER.search(window, max(0, marker.start() - 10))
            aq = am
            arabic = _claim_token(am.group(1), arabic=True) if am else ""
        if not arabic:
            continue

        others = [q for q in quotes if q is not aq and abs(q.start() - marker.start()) <= 190]
        if not others:
            continue
        before = [q for q in others if q.start() < marker.start()]
        fq = max(before, key=lambda q: q.start()) if before else min(
            others, key=lambda q: abs(q.start() - marker.end()))
        foreign = _claim_token(fq.group(1))
        if not foreign or foreign == arabic:
            continue
        key = (tongue[1], foreign, arabic, source)
        if key in seen:
            continue
        seen.add(key)
        context = window[:360]
        rows.append({
            "tongue_ar": tongue[0], "tongue": tongue[1],
            "foreign": foreign, "foreign_sense": context,
            "arabic_root": arabic, "arabic_gloss": context,
            "source": source, "source_line": i + 1,
            "author": _claim_author(source, i + 1, author),
            "harvest_kind": "نسبةٌ صريحةٌ في جملةِ المصدر",
            "ocr_source": "Internet Archive DjVuTXT؛ مؤقّتٌ حتّى يتجدّد مفتاحُ Mistral",
        })
    return rows


RX_DAWUDI_PAIR = re.compile(
    r"^\s*(?:[-–]|[٠-٩0-9]+\s*[-–])\s*"
    r"([ء-يًٌٍَُِّْـ][ء-يًٌٍَُِّْـ\s]{1,24}?)\s*[-–]\s*"
    r"([ء-يًٌٍَُِّْـ][ء-يًٌٍَُِّْـ\s]{1,24}?)\s*[:：]"
)


def mine_dawudi_list(md: pathlib.Path) -> list[dict]:
    """قائمةُ سعيد الدارودي: اللفظُ الأمازيغيُّ ثمّ مقابلُه العربيُّ في سطرٍ ثابت."""
    lines = md.read_text(encoding="utf-8").splitlines()
    rows, seen = [], set()
    # حدودُ بحثِه مطبوعةٌ في الكتاب: من العنوان عند السطر 4937 إلى البحث التالي.
    for line_no in range(4937, min(7234, len(lines) + 1)):
        line = unicodedata.normalize("NFC", lines[line_no - 1])
        match = RX_DAWUDI_PAIR.match(line)
        if not match:
            continue
        foreign = clean(match.group(1))
        arabic = _claim_token(match.group(2), arabic=True)
        if not foreign or not arabic:
            continue
        key = (foreign, arabic)
        if key in seen:
            continue
        seen.add(key)
        context = clean(" ".join(lines[line_no - 1:min(line_no + 2, len(lines))]))[:360]
        rows.append({
            "tongue_ar": "الأمازيغيّة", "tongue": "amazigh",
            "foreign": foreign, "foreign_sense": context,
            "arabic_root": arabic, "arabic_gloss": context,
            "source": "ocr-khashim-dialects", "source_line": line_no,
            "author": "سعيد بن عبدالله الدارودي",
            "harvest_kind": "قائمةٌ ثنائيّةُ العمودِ في بحثِ المصدر",
            "ocr_source": "Internet Archive DjVuTXT؛ مؤقّتٌ حتّى يتجدّد مفتاحُ Mistral",
        })
    return rows


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if not STORE.exists():
        print(f"لا ذخيرةَ في {STORE}")
        return 1

    rows: list[dict] = []
    print(f"{'الكتاب':24}{'أزواج':>8}")
    for folder, (ar, key) in OCR_BOOKS.items():
        md = STORE / folder / "full.md"
        if not md.exists():
            continue
        got = mine_ocr(md, ar, key)
        rows.extend(got)
        print(f"  {folder:24}{len(got):>8}   (مسحٌ جديد)")
    akk = STORE / "ocr-akkadian" / "full.md"
    if akk.exists():
        got = mine_akkadian_ocr(akk)
        rows.extend(got)
        print(f"  {'ocr-akkadian':24}{len(got):>8}   (مسحٌ جديد)")
    cop = STORE / "ocr-coptic" / "full.md"
    if cop.exists():
        got = mine_coptic(cop)
        rows.extend(got)
        print(f"  {'ocr-coptic':24}{len(got):>8}   (مسحٌ جديد)")
    eg = STORE / "ocr-egyptian2" / "full.md"
    if eg.exists():
        got = mine_egyptian(eg)
        rows.extend(got)
        print(f"  {'ocr-egyptian2':24}{len(got):>8}   (مسحٌ جديد)")
    for folder, (author, default_tongue) in CLAIM_BOOKS.items():
        md = STORE / folder / "full.md"
        if not md.exists():
            continue
        got = mine_claim_ocr(md, folder, author, default_tongue)
        rows.extend(got)
        print(f"  {folder:24}{len(got):>8}   (نِسَبٌ صريحة)")
        if folder == "ocr-khashim-dialects":
            listed = mine_dawudi_list(md)
            rows.extend(listed)
            print(f"  {'dialects-dawudi-list':24}{len(listed):>8}   (قائمةٌ صريحة)")
    for stem, (ar, key) in BOOKS.items():
        p = STORE / f"{stem}.pdf"
        if not p.exists():
            print(f"  {stem:24}{'غائب':>8}")
            continue
        got = mine(p, ar, key)
        rows.extend(got)
        print(f"  {stem:24}{len(got):>8}")

    rows, latin_recovery = recover_latin_heads(rows)

    OUT.write_text(json.dumps({
        "generated_by": "scripts/harvest_khashim.py",
        "layer": "استكشاف",
        "author": "علي فهمي خشيم، ومعه باحثو ندوة الوحدة والتنوّع",
        "order": "استعملْ أعمالَه، لا تحكمْ عليها، واحصدْ أقصى ما يمكنُ من الصلات",
        "note": ("أزواجٌ اقترحَها خشيم في معاجمِه المقارِنة. **مرشَّحاتٌ لا أحكام.** "
                 "والكلمةُ الأجنبيّةُ بحروفٍ عربيّةٍ كما كتبَها هو، لأنّ المسحَ الضوئيَّ "
                 "عربيٌّ فقط فسقطَ الحرفُ الأصليُّ، وهو نقصٌ مسمًّى يُسَدُّ بمسحٍ ثانٍ."),
        "pairs": len(rows),
        "latin_head_recovery": latin_recovery,
        "rows": rows,
    }, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    by_tongue: dict[str, int] = {}
    for r in rows:
        by_tongue[r["tongue_ar"]] = by_tongue.get(r["tongue_ar"], 0) + 1
    lines = [
        "# حَصادُ مَعاجِمِ خَشيم المُقارِنة",
        "",
        "**الطَّبَقة:** استِكشاف. **مُرَشَّحاتٌ لا أحكام.**",
        "",
        "علي فهمي خشيم، وكُتُبُه: «الأكّادِيّةُ عَرَبِيّة» و«القِبطِيّةُ عَرَبِيّة»",
        "و«اللّاتينِيّةُ عَرَبِيّة» و«الوَحدةُ والتَّنَوُّعُ في اللَّهَجاتِ العَروبِيّةِ القَديمة».",
        "وزِيدَت «رِحلةُ الكَلِماتِ الثّانِيَة» و«آلِهَةُ مِصرَ العَرَبِيَّة 2»،",
        "ومَقالَاتُ تِسعَةِ باحِثينَ في كِتابِ النَّدوة؛ وكلُّ صَفٍّ مَنسوبٌ إلى صاحِبِه.",
        "وبِنيةُ كُتُبِه مُعجَمِيّةٌ، فالسَّطرُ الأوّلُ الكَلِمةُ الأجنَبِيّةُ ومَعناها،",
        "ويَليه سَطرٌ يَبدَأُ بـ`ع :` فيه الجَذرُ العَرَبِيُّ ونَصُّ مُعجَمِه.",
        "",
        "**الكَلِمةُ الأجنَبِيّةُ هنا بحُروفٍ عَرَبِيّةٍ كما كَتَبَها هو**، لأنّ المَسحَ",
        "الضَّوئِيَّ للكُتُبِ عَرَبِيٌّ فقط فسَقَطَ الحَرفُ الأصلِيّ. وهذا نَقصٌ مُسَمًّى.",
        "",
        f"**العَدَد: {len(rows)} زَوجًا.**  " + " · ".join(f"{k}: {v}" for k, v in by_tongue.items()),
        "",
        "| اللِّسان | الكَلِمةُ عندَه | مَعناها | الجَذرُ العَرَبِيّ | نَصُّه |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['tongue_ar']} | `{r['foreign']}` | {r['foreign_sense'][:44]} | "
                     f"**{r['arabic_root']}** | {r['arabic_gloss'][:70]} |")
    lines += ["", "---", "",
              "*English abstract.* Pairs harvested from Ali Fahmi Khashim's comparative",
              "dictionaries, whose titles state the thesis directly: Akkadian is Arabic, Coptic is",
              "Arabic, Latin is Arabic. The harvest also includes Journey of Words II, Gods of",
              "Arabic Egypt II, and nine attributed papers in the Unity and Diversity symposium.",
              "His dictionary entries are lexicographic, so each foreign headword and",
              "its sense is followed by a line marked with the Arabic letter ain giving the Arabic",
              "root and its lexical text. These are candidates, not verdicts. The foreign words",
              "appear in Arabic transcription because the available scans were OCRed for Arabic",
              "only and dropped every Latin character; that is a named gap, not a choice."]
    SHEET.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"\nالمجموع: {len(rows)} زوجًا")
    print(f"كُتب: {OUT.relative_to(ROOT).as_posix()}")
    print(f"كُتب: {SHEET.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
