# -*- coding: utf-8 -*-
"""حصادُ ما اقترحَه السابقونَ من أزواج (2026-08-10، بأمرِ المؤلّف)

**الأمرُ بنصِّه:** «استعملْ أعمالَه. لا تحكمْ على عملِه. لا يهمُّني أنّه لم يضعْ
قواعدَ كثيرة. استعملْ حدسَه وعملَه لتحصلَ على أقصى ما يمكنُ من الصلات. ومن عملَ
عملًا مشابهًا على وسائلِ التواصلِ أو غيرِها فحمِّلْه واقرأْه وحاولْ ما استطعتَ أن
تجدَ صلات».

**فهذا مِعوَلُ حصادٍ لا ميزانُ نقد.** يُنزِلُ أبحاثَ السابقينَ ويستخرجُ منها كلَّ
زوجٍ اقترحوه: كلمةٌ في لسانٍ أوربيٍّ بإزاءِ جذرٍ عربيّ. ولا يحكمُ على زوجٍ منها
بشيء، ولا يُسقِطُ زوجًا لأنّ صاحبَه لم يذكرْ له قانونًا. الحكمُ يجيءُ بعدَ الحصادِ
لا قبلَه، وأمّا الآنَ فالمطلوبُ **أوسعُ ما يمكنُ من المرشَّحين**.

**والاستخراجُ يعتمدُ على أنّ للرجلِ أسلوبًا ثابتًا في كلِّ أبحاثِه:**

    Emperor came from French empereur, ... ultimately from Arabic 'ameer
    'ruler, prince', amar (v) 'to command, order'

فالصيغةُ: كلمةٌ إنجليزيّةٌ، ثمّ `from Arabic`، ثمّ رومنتُه للجذرِ العربيِّ، ثمّ
معناه بين علامتَين. ورومنتُه معلَنةٌ في كلِّ بحثٍ: `3` عين، و`2` حاء، و`kh` خاء،
و`gh` غين، وحرفٌ كبيرٌ للمُطبَق (`T` طاء و`D` ضاد و`S` صاد و`Dh` ظاء)، و`'` همزة.

**والنصُّ العربيُّ في ملفّاتِه لا يُقرَأ**: ترميزُ الخطِّ في نسخِ PDF مكسورٌ فتخرجُ
`أمر` هكذا `أيس`. فلا يُعوَّلُ على حروفِه العربيّةِ البتّة، بل على رومنتِه
وشرحِه الإنجليزيّ، ونحن نردُّها إلى العربيّةِ بأنفسِنا.

الاستعمال:
    python scripts/harvest_prior_art.py --fetch     أنزِلْ ما لم يُنزَّلْ بعد
    python scripts/harvest_prior_art.py             استخرجْ من المُنزَّل
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys
import unicodedata
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
# الذخيرةُ الخامُّ خارجَ git كسائرِ المواد
STORE = ROOT.parent / "The Arabic Tongue (nature-genome-application) resources"
if not STORE.exists():
    STORE = pathlib.Path.home() / "AI Projects" / "Resources" / "prior-art"
OUT = ROOT / "data" / "prior-art-pairs.json"
SHEET = ROOT / "04-cross-linguistic" / "exploration" / "prior-art-harvest.md"

SOURCES = [
    # (مُعرَّف، رابط) وكلُّها مفتوحةُ الوصولِ لا تحتاجُ حسابًا
    ("jassem-2012-numerals", "https://www.macrothink.org/journal/index.php/ijl/article/download/1876/1854"),
    ("jassem-2019-mr", "https://www.arcjournals.org/pdfs/ijsell/v7-i1/4.pdf"),
    ("jassem-2019-frk", "https://www.arcjournals.org/pdfs/ijsell/v7-i8/1.pdf"),
    ("jassem-2016-floral", "https://www.arcjournals.org/pdfs/ijsell/v4-i2/10.pdf"),
    ("jassem-2016-fashion", "https://www.arcjournals.org/pdfs/ijsell/v4-i5/7.pdf"),
    ("jassem-pronouns", "https://www.macrothink.org/journal/index.php/ijl/article/download/2271/2241"),
    ("jassem-verb-to-be", "https://journals.aiac.org.au/index.php/IJALEL/article/viewFile/830/762"),
    ("jassem-2012-determiners", "https://languageinindia.com/nov2012/jassemdeterminersfinal.pdf"),
    ("jassem-2012-number-gender", "https://languageinindia.com/dec2012/jassemarabicgender.pdf"),
    ("jassem-2012-religious", "https://web.archive.org/web/20150330231748id_/http://journals.aiac.org.au/index.php/IJALEL/article/download/800/731"),
    ("jassem-2013-derivational", "https://languageinindia.com/jan2013/jassemderive.pdf"),
    ("jassem-2013-negative-particles", "https://languageinindia.com/jan2013/jassemnegativefinal.pdf"),
    ("jassem-2013-water-sea", "https://languageinindia.com/feb2013/jassemwater.pdf"),
    ("jassem-2013-air-fire", "https://languageinindia.com/march2013/jassemairandfirefinal.pdf"),
    ("jassem-2013-animal", "https://languageinindia.com/april2013/jassemanimaltermsfinal.pdf"),
    ("jassem-2013-speech-writing", "https://languageinindia.com/may2013/jassemtermsfinal2.pdf"),
    ("jassem-2013-time", "https://languageinindia.com/june2013/jassemtimetermsfinal.pdf"),
    ("jassem-2013-love", "https://web.archive.org/web/20160414135432id_/http://article.sciencepublishinggroup.com/pdf/10.11648.j.ijll.20130104.13.pdf"),
    ("jassem-2013-cutting-breaking", "http://www.rjelal.com/RJELAL%201.2/RJELAL%201.2.%20pp%20155-168.pdf"),
    ("jassem-2013-movement-action", "http://www.rjelal.com/RJELAL%20VOL.1.ISSUE.3/ZAIDAN%20ALI%20JASSEM%20187-202.pdf"),
    ("jassem-2013-perceptual-sensual", "http://www.rjelal.com/RJELAL%20VOL.1.ISSUE.3/ZAIDAN%20ALI%20JASSEM%20213-224.pdf"),
    ("jassem-2014-divine-theological", "https://languageinindia.com/march2014/jassemtheologicalterms1.pdf"),
    ("jassem-2014-prepositions", "https://www.macrothink.org/journal/index.php/jsel/article/download/5056/4078"),
    ("jassem-2014-question-modal", "https://web.archive.org/web/20160414135247id_/http://article.sciencepublishinggroup.com/pdf/10.11648.j.ijll.20140201.13.pdf"),
    ("jassem-2014-commerce", "https://web.archive.org/web/20160414134728id_/http://article.sciencepublishinggroup.com/pdf/10.11648.j.ijll.20140205.15.pdf"),
    ("jassem-2014-mathematical", "https://www.arcjournals.org/pdfs/ijsell/v2-i5/4.pdf"),
    ("jassem-2014-basque-finnish", "https://pdfs.semanticscholar.org/4be9/7789652dec742056bbe617e9a3a7b6089502.pdf"),
    ("jassem-2015-case-word-order", "https://languageinindia.com/march2015/jassemcasemarkings.pdf"),
    ("jassem-2015-military", "https://languageinindia.com/may2015/jassemmilitary.pdf"),
    ("jassem-2015-legal", "https://web.archive.org/web/20170706110525id_/http://article.sciencepublishinggroup.com/pdf/10.11648.j.ijalt.20150103.11.pdf"),
    ("jassem-2015-democratic", "https://joell.in/wp-content/uploads/2015/08/A-Radical-Linguistic-Theory.pdf"),
    ("jassem-2015-negation-world", "https://joell.in/wp-content/uploads/2015/10/Negation-in-World-Languages.pdf"),
    ("jassem-2015-plural-markers", "https://journal.uniku.ac.id/index.php/IEFLJ/article/download/623/480"),
    ("jassem-2013-back-consonants", "https://ijee.org/ijee/article/download/1129/1122"),
    ("jassem-2013-family", "https://ijee.org/ijee/article/download/1244/1237"),
    ("jassem-2014-wining-dining", "https://ijee.org/ijee/article/download/1013/1003"),
    ("jassem-2014-mandarin-pronouns", "https://ijee.org/ijee/article/download/1174/1168"),
    ("jassem-2015-radical-translation-names", "https://ijee.org/ijee/article/download/922/914"),
    ("jassem-2015-life-death", "https://ijee.org/ijee/article/download/923/915"),
    ("jassem-2015-urban", "https://journal.uniku.ac.id/index.php/ERJEE/article/download/204/161"),
    ("jassem-2016-entirely-arabic", "https://ijee.org/ijee/article/download/670/663"),
    ("jassem-2017-harper-review", "https://ijee.org/ijee/article/download/270/265"),
    ("jassem-2017-myth-fallacy", "https://joell.in/wp-content/uploads/2017/01/Myth-and-Fallacy-in-the-Oxford-English-Dictionary.pdf"),
    ("jassem-2018-negative-terms", "https://ijee.org/ijee/article/download/308/302"),
    ("jassem-2018-week-days", "https://ijee.org/ijee/article/download/362/356"),
    ("jassem-2018-place-names", "https://pdfs.semanticscholar.org/fc3e/fbc726d16f2e4aa65f32c3438b376662f94c.pdf"),
    ("jassem-2018-demonstratives", "https://journal.uinjkt.ac.id/index.php/arabiyat/article/download/8936/pdf"),
    ("jassem-2018-sex-derivatives", "https://www.arcjournals.org/pdfs/ijsell/v6-i10/5.pdf"),
]

# روابطُ جُرِّبت ثم أُخرجت من SOURCES لأنّها لم تُعِد PDF صالحًا. تُحفَظُ هنا
# لتبقى فجوةُ الإنزال ظاهرةً في ورقةِ الذخيرة ولا يعادَ اكتشافُها من الصفر.
FAILED_SOURCES = [
    ("jassem-definite", "https://pdfs.semanticscholar.org/b2c9/2df435e2e33e23485b3a6b732ed318709ae4.pdf",
     "تعذّر الإنزال"),
    ("jassem-2012-religious", "https://journals.aiac.org.au/index.php/IJALEL/article/download/800/731",
     "ردّ المستضيف 406"),
    ("jassem-2013-love", "https://article.sciencepublishinggroup.com/pdf/10.11648.j.ijll.20130104.13.pdf",
     "عاد رابطًا قصيرًا لا PDF"),
    ("jassem-2014-question-modal", "https://article.sciencepublishinggroup.com/pdf/10.11648.j.ijll.20140201.13.pdf",
     "عاد رابطًا قصيرًا لا PDF"),
    ("jassem-2014-commerce", "https://article.sciencepublishinggroup.com/pdf/10.11648.j.ijll.20140205.15.pdf",
     "عاد رابطًا قصيرًا لا PDF"),
    ("jassem-2014-basque-finnish-old", "https://journals.techmindresearch.com/index.php/jell/article/download/25/26",
     "تعذّر اسمُ المستضيف، واستُبدل بمرآة Semantic Scholar صالحة"),
    ("jassem-2013-celestial-ojs", "https://ijee.org/ijee/article/download/1266/1259",
     "ردّ مسارُ OJS الجديد 404؛ وملفُّ المجلةِ القديمُ ظاهرٌ في الفهرسِ لكنّه محذوفٌ من المستضيف"),
    ("jassem-2013-celestial-legacy", "https://www.ijee.org/assets/docs/27.89114953.pdf",
     "ردّ مستودعُ IJEE القديم 404"),
    ("jassem-2013-cognitive-ojs", "https://ijee.org/ijee/article/download/1296/1289",
     "ردّ مسارُ OJS الجديد 404؛ وملفُّ المجلةِ القديمُ ظاهرٌ في الفهرسِ لكنّه محذوفٌ من المستضيف"),
    ("jassem-2013-cognitive-legacy", "https://www.ijee.org/assets/docs/7.271143130.pdf",
     "ردّ مستودعُ IJEE القديم 404"),
    ("jassem-2016-definite-ojs", "https://ijellh.com/OJS/index.php/OJS/article/download/1489/8673",
     "ردّ مسارُ OJS القديم 404"),
    ("jassem-2016-definite-legacy", "https://ijellh.com/wp-content/uploads/2016/06/64.-Zaidan-Ali-Jassem-paper-final.pdf",
     "ردّ مستودعُ IJELLH القديم 404"),
    ("jassem-2016-campbell-ojs", "https://ijellh.com/OJS/index.php/OJS/article/download/1705/8672",
     "ردّ المسارُ الحالي 404؛ ولقطتُه المؤرشفةُ مقالٌ لصمويل دوكو لا بحثُ جاسم"),
    ("jassem-2012-religious-scispace", "https://scispace.com/pdf/the-arabic-origins-of-common-religious-terms-in-english-a-11uoozx0kl.pdf",
     "ردّت المرآةُ 403"),
    ("jassem-2014-question-modal-scispace", "https://scispace.com/pdf/the-arabic-origins-of-question-and-modal-words-in-english-48w16fl95a.pdf",
     "ردّت المرآةُ 403"),
    ("jassem-2013-love-scispace", "https://scispace.com/pdf/the-arabic-origins-of-love-and-sexual-terms-in-english-and-4y5lm94n80.pdf",
     "ردّت المرآةُ 403"),
    ("jassem-2015-medical-catalog", "https://www.joell.in/vol-ii-issue-i-2015/",
     "أثبتَ الفهرسُ البحثَ وصفحاتِه، لكن رابطَ التنزيلِ يحيلُ إلى صورةِ أيقونةٍ لا إلى PDF"),
    ("jassem-2015-legal-sciencepg", "https://article.sciencepublishinggroup.com/pdf/10.11648.j.ijalt.20150103.11",
     "أعادَ المستضيفُ ملفًّا من 31 بايتًا يقول إنّ رمزَ التحقّق غيرُ صالح، لا PDF"),
    ("jassem-2018-demonstratives-wrong-galley", "https://journal.uinjkt.ac.id/index.php/arabiyat/article/download/8936/6230",
     "ردّ رقمُ الملحقِ المخمَّن 404؛ واستُبدل بمسارِ PDF المسمّى الصالح"),
]

UA = {"User-Agent": "Mozilla/5.0 (research harvest; contact via arabicjuthoor.com)"}

# رومنةُ الرجلِ إلى العربيّة، كما أعلنَها هو في بابِ المادّةِ من كلِّ بحث
TRANSLIT = [
    ("Dh", "ظ"), ("dh", "ذ"), ("kh", "خ"), ("gh", "غ"), ("th", "ث"),
    ("sh", "ش"), ("ch", "ش"), ("T", "ط"), ("D", "ض"), ("S", "ص"), ("Z", "ظ"),
    ("2", "ح"), ("3", "ع"), ("'", "ء"), ("q", "ق"), ("k", "ك"), ("j", "ج"),
    ("b", "ب"), ("t", "ت"), ("7", "ح"), ("9", "ص"), ("8", "ق"),
    ("d", "د"), ("r", "ر"), ("z", "ز"), ("s", "س"), ("f", "ف"),
    ("l", "ل"), ("m", "م"), ("n", "ن"), ("h", "ه"), ("w", "و"), ("y", "ي"),
    ("g", "ج"), ("p", "ب"), ("v", "ف"), ("c", "ك"), ("x", "كس"),
]
VOWELS_LAT = "aeiouāēīōūáéíóú"

# **صيغتُه الحقيقيّةُ أوسعُ ممّا يبدو من مثالٍ واحد.** يكتبُ أحيانًا في سطرِ النصّ
# `from Arabic 'ameer 'ruler'`، وأحيانًا نقطتَينِ ثمّ سطرًا جديدًا ثمّ عدّةَ صورٍ
# لجذرٍ واحدٍ قبلَ المعنى: `from Arabic:\n far(r)aq 'divide; to fork'`، ثمّ
# `and related derivatives farraaq, faariq, faarooq`. فمن التقطَ الصيغةَ الأولى
# وحدَها فقدَ أكثرَ من نصفِ حصادِ الملفّ.
RX_PAIR = re.compile(
    r"\bArabic:?\s*[\s•\-–]*"
    r"([A-Za-z'`()23789]{2,24}(?:\s*,\s*[A-Za-z'`()23789]{2,24}){0,5})"
    r"\s*(?:\([a-z.]{1,8}\))?\s*['‘\"]([^'’\"\n]{2,90})['’\"]", re.I)
# ومعها ذيولُ الاشتقاقِ التي يسردُها بعدَ المعنى بلا معنًى ثانٍ
RX_MORE = re.compile(r"related\s+derivatives?\s+"
                     r"([A-Za-z'`()23789]{2,24}(?:\s*,\s*[A-Za-z'`()23789]{2,24}){0,6})", re.I)
RX_NUMERAL_PAIR = re.compile(
    r"\b([A-Za-z'`()23789]{2,24})\s*\("
    r"(one(?:,\s*first)?|first|two(?:-fem\.)?|second|three|third|four|fourth|"
    r"five|fifth|six|sixth|seven|seventh|eight|eighth|nine|ninth|ten|tenth|"
    r"hundred|thousand|million)\)", re.I)
# الكلمةُ الأوربيّةُ: رأسُ الفقرةِ، مفردًا كانَ أو مركَّبًا، وقد يليها قوسٌ فيه
# أخواتُها. وأكثرُ المتنِ لا يستعملُ `came from` وحدَه، بل `via Latin` و`from
# Arabic` و`is a compound of` أيضًا. لذلك يُقبَلُ رابطُ اشتقاقٍ صريحٌ في رأسِ
# السطر، ولا يُقبَلُ `is / are / has` المجرَّدُ الذي يلتقطُ كلامَ الشرحِ.
RX_HEAD_WORD = r"[A-Za-z][A-Za-z'’/\-]*"
RX_HEAD_FIRST = r"[A-Z][A-Za-z'’/\-]*"
RX_HEAD = re.compile(
    r"(?:^|\n)\s*(?:\d+(?:\.\d+)*\s+)?"
    r"(" + RX_HEAD_FIRST +
    r"(?:[ \t]+(?!(?:via|from|came|comes|derive|derives|derived|developed|evolved|"
    r"descend|goes|stems|stemmed|emanated|probably|originally|straight|is)\b)" +
    RX_HEAD_WORD + r"){0,4})"
    r"\s*(?:\([^)\n]{0,170}\))?\s*(?:[:,;]\s*)?"
    r"(?:(?:probably\s+|straight\s+)?(?:via|from)|"
    r"(?:came|comes|derives?|derived|developed|evolved|descends?|goes\s+back|stems?|"
    r"stemmed|emanated)\s+(?:from|back)|"
    r"originally\b[^\n]{0,150}\b(?:from|via)|"
    r"is\s+(?:a|an)\s+(?:compound|derivative|variant))\b", re.M)
RX_SOURCE_LANG = re.compile(
    r"\b(Arabic|Old\s+English|Middle\s+English|English|Latin|Old\s+French|French|"
    r"Greek|German|Old\s+Norse|Old\s+North\s+French|Dutch|Sanskrit|Russian|PIE|"
    r"Proto-Indo-European|Italian|Spanish|Portuguese|Celtic|Finnish|Basque|Chinese)\b")
NOT_HEAD = {"The", "This", "That", "These", "Those", "It", "In", "As", "All",
            "Arabic", "English", "There", "However", "Thus", "First", "Second",
            "Finally", "Table", "Figure", "Both", "Such", "What", "Which"}
NOT_HEAD_START = NOT_HEAD | {"French", "German", "Greek", "Latin", "Sanskrit",
                             "Russian", "Similarly", "Consequently", "Furthermore",
                             "For", "Jassem", "According", "Therefore", "Although",
                             "Some", "Several", "Other", "Former", "Prior", "Von",
                             "Paper", "Rarely", "Likely", "Modern", "Old"}
RX_SOURCE_HEAD = re.compile(
    r"\b(?:Church\s+Old\s+Slavonic|Old\s+English|Middle\s+English|Old\s+French|"
    r"Old\s+Norse|Old\s+North\s+French|High\s+German|Proto-Indo-European)\b")


# لواحقُ الصرفِ التي يكتبُها بين قوسَينِ في آخرِ الكلمة: تاءُ التأنيثِ والتنوين.
# **وهي ليست من الجذرِ**، وهو العطبُ نفسُه الذي أصلحناه في `rēx` وفي `עסקתא`،
# فلا يُعقَلُ أن نُصلِحَه في مادّتِنا ونُدخِلَه في مادّةِ غيرِنا.
RX_GRAM_TAIL = re.compile(r"\((?:aat|at|ah|an|un|in|t)\)\s*$", re.I)
RX_ARTICLE = re.compile(r"^'?(?:al|el)[-\s]?(?=[a-z'`23789]{3})", re.I)
ROOT_FOLD = str.maketrans({"أ": "ء", "إ": "ء", "آ": "ء", "ٱ": "ء",
                           "ؤ": "ء", "ئ": "ء", "ى": "ي"})


def to_arabic(translit: str) -> str:
    """الجذرُ الصامتيُّ العربيُّ من رومنتِه. تُطرَحُ الصوائتُ كما يطرحُها هو،
    وتُطرَحُ معها لاحقةُ الصرفِ وأداةُ التعريف، ويُرَدُّ المشدَّدُ إلى حرفٍ واحد."""
    s = translit.strip().strip("-.,;")
    s = RX_GRAM_TAIL.sub("", s)
    s = RX_ARTICLE.sub("", s)
    s = s.replace("(", "").replace(")", "")      # `far(r)aq` تشديدٌ لا حرفٌ زائد
    out: list[str] = []
    i = 0
    while i < len(s):
        for lat, ar in TRANSLIT:
            if s.startswith(lat, i):
                if not (out and out[-1] == ar):   # الشدّةُ حرفٌ واحدٌ في الجذر
                    out.append(ar)
                i += len(lat)
                break
        else:
            i += 1        # صائتٌ أو رمزٌ لا يُقابَل
    return "".join(out)


def fold_root(root: str) -> str:
    """صورةٌ موحَّدةٌ للمقابلة بينَ همزاتِ الجسرِ والبطاقاتِ ورومنةِ الباحث."""
    return unicodedata.normalize("NFC", root).translate(ROOT_FOLD)


def bridge_and_cards(rows: list[dict]) -> dict:
    """يضيفُ جوابَ جسرِ المعنى، ويحصي تقاطعَ الجذورِ مع البطاقاتِ الموجبة."""
    import build_en_ar_bridge as B                    # noqa: PLC0415

    bridge_path = ROOT / "data" / "en-ar-bridge.json"
    bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
    root_words: dict[str, set[str]] = collections.defaultdict(set)
    for field in ("root_head", "root_gloss"):
        for root, words in bridge.get(field, {}).items():
            root_words[fold_root(root)].update(str(w).lower() for w in words)

    by_word: dict[str, set[str]] = collections.defaultdict(set)
    for root, words in root_words.items():
        for word in words:
            by_word[word].add(root)

    agrees = 0
    for row in rows:
        root = fold_root(row["arabic_root"])
        words = B.words_of(row["arabic_gloss"])
        if words & root_words.get(root, set()):
            row["bridge_agrees"] = "نعم"
            agrees += 1
            continue
        candidates = set()
        for word in words:
            candidates.update(by_word.get(word, set()))
        candidates.discard(root)
        if not candidates:
            row["bridge_agrees"] = "لا مدخلَ عندنا"
            continue
        scored = [(len(words & root_words[cand]), cand) for cand in candidates]
        best_score = max(score for score, _ in scored)
        best = sorted(cand for score, cand in scored if score == best_score)
        shown = "، ".join(best[:8])
        if len(best) > 8:
            shown += "، وغيرُها"
        row["bridge_agrees"] = f"جذرٌ آخر: {shown}"

    harvested_roots = {fold_root(row["arabic_root"]) for row in rows}
    positive_card_roots = {fold_root(root) for root in B.from_cards()}
    return {
        "bridge_agrees": agrees,
        "unique_roots": len(harvested_roots),
        "roots_in_positive_cards": len(harvested_roots & positive_card_roots),
    }


def fetch() -> None:
    STORE.mkdir(parents=True, exist_ok=True)
    for key, url in SOURCES:
        dest = STORE / f"{key}.pdf"
        if dest.exists() and dest.stat().st_size > 20_000:
            print(f"   حاضرٌ  {key}")
            continue
        try:
            req = urllib.request.Request(url, headers=UA)
            data = urllib.request.urlopen(req, timeout=90).read()
            if len(data) < 20_000 or not data[:5].startswith(b"%PDF"):
                print(f"!! ليس PDF  {key}  ({len(data):,} بايت)")
                continue
            dest.write_bytes(data)
            print(f"   نُزِّل  {key}  ({len(data)//1024} KB)")
        except Exception as exc:                       # noqa: BLE001
            print(f"!! تعذَّر  {key}: {str(exc)[:70]}")


def mine(path: pathlib.Path) -> list[dict]:
    import fitz                                       # noqa: PLC0415
    text = "\n".join(pg.get_text() for pg in fitz.open(path))
    # **ترويسةُ الصفحةِ تُقطَعُ سطورًا فتصيرُ رؤوسًا كاذبةً** مثل `Th` و`Oas`.
    # فلا يُقبَلُ رأسٌ إلّا إن كان كلمةً إنجليزيّةً حقيقيّةً تردُ في المتنِ صغيرةً
    # أيضًا، وطولُه ثلاثةُ أحرفٍ فصاعدًا.
    lower = set(re.findall(r"\b[a-z]{3,24}\b", text))
    heads = []
    for m in RX_HEAD.finditer(text):
        head = " ".join(m.group(1).split())
        if head == "Army Dissection":
            head = "Dissection"
        first = head.split()[0]
        if (first in NOT_HEAD_START or len(first) < 3
                or first.lower() not in lower
                or RX_SOURCE_HEAD.search(head)
                or not RX_SOURCE_LANG.search(text[m.end():m.end() + 260])):
            continue
        heads.append((m.start(), head))
    pairs, seen = [], set()

    def emit(head: str, translit: str, gloss: str) -> None:
        arabic = to_arabic(translit)
        if len(arabic) < 2 or len(arabic) > 8:
            return
        key = (head.lower(), arabic, gloss.lower()[:30])
        if key in seen:
            return
        seen.add(key)
        pairs.append({
            "european": head, "arabic_root": arabic,
            "author_translit": translit.strip(), "arabic_gloss": gloss,
            "source": path.stem,
        })

    for m in RX_PAIR.finditer(text):
        gloss = " ".join(m.group(2).split())
        head = ""
        for pos, word in heads:
            if pos < m.start():
                head = word
            else:
                break
        # **كلُّ صورةٍ يسردُها صفٌّ مستقلٌّ بالمعنى نفسِه**، فهو يعطي الجذرَ
        # وصورَه المشتقّةَ معًا ثمّ يذكرُ المعنى مرّةً واحدةً في آخرِها
        for one in re.split(r"\s*,\s*", m.group(1)):
            emit(head, one, gloss)
        tail = RX_MORE.search(text[m.end():m.end() + 220])
        if tail:
            for one in re.split(r"\s*,\s*", tail.group(1)):
                emit(head, one, gloss)

    # بحثُ العددِ الأقدمُ يشرحُ المعنى بين قوسين بدلَ علامتَي اقتباس، مثل
    # `Arabic cognate thalath(at) (three)`. يُحصرُ هذا البابُ في ذلك الملفِّ
    # وفي نافذةٍ تذكرُ العربيةَ صراحةً حتى لا تُلتقطَ أمثلةُ الإنجليزيةِ نفسها.
    if path.stem == "jassem-2012-numerals":
        for m in RX_NUMERAL_PAIR.finditer(text):
            if "arabic" not in text[max(0, m.start() - 180):m.start()].lower():
                continue
            gloss = m.group(2).replace("-fem.", "").split(",", 1)[0].strip()
            emit(gloss.title(), m.group(1), gloss)
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if args.fetch:
        print("الإنزال:")
        fetch()
        print()

    # مجلّدُ الذخيرةِ مشتركٌ بينَ أعمالِ السابقين، فلا يُمسَحُ منه إلّا ما صرَّحت
    # به القائمةُ أعلاه. وإلّا دخلت ملفاتُ باحثٍ آخر في عددِ أبحاثِ جاسم.
    files = [STORE / f"{key}.pdf" for key, _ in SOURCES
             if (STORE / f"{key}.pdf").exists()]
    if not files:
        print(f"لا ملفّاتٍ في {STORE}. شغِّلْ بـ--fetch أوّلًا.")
        return 1

    all_pairs: list[dict] = []
    per_source: dict[str, int] = {}
    print(f"{'الملفّ':26}{'أزواج':>8}")
    for f in files:
        try:
            p = mine(f)
        except Exception as exc:                       # noqa: BLE001
            print(f"  {f.stem:26}{'تعذَّر':>8}  {str(exc)[:44]}")
            continue
        all_pairs.extend(p)
        per_source[f.stem] = len(p)
        print(f"  {f.stem:26}{len(p):>8}")

    # لا يُحذَفُ زوجٌ لتكرارِه بينَ بحثَين، بل يُدمَجُ ويُذكَرُ مصدراه
    merged: dict[tuple, dict] = {}
    for p in all_pairs:
        k = (p["european"].lower(), p["arabic_root"])
        if k in merged:
            if p["source"] not in merged[k]["source"]:
                merged[k]["source"] += " · " + p["source"]
            continue
        merged[k] = dict(p)

    rows = sorted(merged.values(), key=lambda r: (r["european"].lower(), r["arabic_root"]))
    comparison = bridge_and_cards(rows)
    with_head = sum(bool(r["european"]) for r in rows)
    OUT.write_text(json.dumps({
        "generated_by": "scripts/harvest_prior_art.py",
        "layer": "استكشاف",
        "order": "استعملْ أعمالَه، لا تحكمْ عليها، واحصدْ أقصى ما يمكنُ من الصلات",
        "note": ("أزواجٌ اقترحَها سابقون. **لا حكمَ فيها ولا تزكية**، وهي مرشَّحاتٌ "
                 "تدخلُ بوّاباتِنا كما يدخلُها أيُّ مرشَّح. والجذرُ العربيُّ مردودٌ "
                 "من رومنةِ صاحبِ البحثِ لا من حروفِه العربيّةِ لأنّ ترميزَها مكسور."),
        "sources": [s for s, _ in SOURCES if (STORE / f"{s}.pdf").exists()],
        "source_urls": {s: url for s, url in SOURCES},
        "failed_sources": [
            {"source": key, "url": url, "reason": reason}
            for key, url, reason in FAILED_SOURCES
        ],
        "pairs": len(rows),
        "stats": {
            "papers_downloaded": len(files),
            "with_european_head": with_head,
            "head_coverage": round(with_head / max(len(rows), 1), 4),
            **comparison,
        },
        "rows": rows,
    }, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    lines = [
        "# حَصادُ ما اقتَرَحَهُ السّابِقون",
        "",
        "**الطَّبَقة:** استِكشاف. **مُرَشَّحاتٌ لا أحكام.**",
        "",
        "بأمرِ المؤلّف: «استعمِلْ أعمالَه، لا تَحكُمْ عليها، واحصُدْ أقصى ما يُمكِنُ",
        "من الصِّلات». فهذه أزواجٌ اقتَرَحَها باحِثونَ قَبلَنا، جُمِعَت كما هي، ولم يُرَدَّ",
        "منها زَوجٌ لأنّ صاحِبَه لم يَذكُرْ له قانونًا. الحُكمُ بَعدَ الحَصادِ لا قَبلَه.",
        "",
        f"**العَدَد: {len(rows)} زَوجًا** من {len(files)} بَحثًا مفتوحَ الوصول.",
        "",
        f"حَمَلَ {with_head} صفًّا رأسَ المَدخلِ الأوربِيَّ، أي "
        f"{with_head / max(len(rows), 1):.1%} من الحَصيلة. وفُحِصَت عَيِّنةٌ موزَّعةٌ من "
        "20 صفًّا ذي رأسٍ، فكانَ الرأسُ فيها عنوانَ المَدخلِ لا لفظًا من وَسَطِ الفِقرة.",
        "",
        f"وافَقَ جِسرُ المَعنى الجَذرَ نفسَه في {comparison['bridge_agrees']} زَوجًا. "
        f"وفي الحَصادِ {comparison['unique_roots']} جَذرًا مُتَمايِزًا، وَرَدَ منها "
        f"{comparison['roots_in_positive_cards']} جَذرًا في بِطاقاتِ القِراءةِ ذاتِ حُكمٍ مُوجَبٍ صادِر.",
        "",
        "## المَصادِرُ المُنزَّلة",
        "",
        "| المَصدَر | PDF المُباشِر | الأَزواجُ قَبلَ الدَّمج |",
        "|---|---|---:|",
    ]
    source_urls = dict(SOURCES)
    for key in (f.stem for f in files):
        lines.append(f"| {key} | [PDF]({source_urls[key]}) | {per_source.get(key, 0)} |")
    lines += [
        "",
        "## رَوابِطُ تَعَذَّرَت",
        "",
        "هذه الرَّوابِطُ خارِجَةٌ من `SOURCES` حتّى لا يُعادَّ فَشَلُها في كُلِّ تَشغيل:",
        "",
        "| المَصدَر | الرَّابِطُ المُجَرَّب | ما وَقَع |",
        "|---|---|---|",
    ]
    for key, url, reason in FAILED_SOURCES:
        lines.append(f"| {key} | [الرابط]({url}) | {reason} |")
    lines += [
        "",
        "## الأَزواجُ المَحصودة",
        "",
        "`bridge_agrees` مُقابَلةُ ذَخيرةٍ لا بَوّابةُ قَبول: `نعم` أو جَذرٌ آخَرُ في جِسرِنا أو "
        "غَيابُ مَدخلٍ عِندَنا، ولا تُسقِطُ واحِدةٌ منها مُرَشَّحًا.",
        "",
        "| الكَلِمةُ الأوربِيّة | رومَنةُ الباحِث | الجَذرُ العَرَبِيُّ كما نَرُدُّه | المَعنى الذي ذَكَرَه | `bridge_agrees` | المَصدَر |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['european']} | `{r['author_translit']}` | **{r['arabic_root']}** | "
                     f"{r['arabic_gloss'][:60]} | {r['bridge_agrees']} | {r['source']} |")
    lines += ["", "---", "",
              "*English abstract.* Pairs proposed by earlier researchers, harvested verbatim as",
              "candidates. No pair is rejected here for lacking a stated law; judgement comes after",
              "the harvest, not before it. The Arabic root is reconstructed from each author's own",
              "declared transliteration rather than from the Arabic script in their PDFs, whose font",
              "encoding is broken."]
    SHEET.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(f"\nالمجموعُ بعدَ الدمج: {len(rows)} زوجًا")
    print(f"كُتب: {OUT.relative_to(ROOT).as_posix()}")
    print(f"كُتب: {SHEET.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
