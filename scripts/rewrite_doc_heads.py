"""Rewrite dense academic titles + opening paragraphs across key public .md files.

Each entry: (file_path, old_first_two_lines_pattern, new_first_two_blocks).
We match on the first line (the H1) and replace H1 + the first non-empty
paragraph after it. The rest of the document is untouched.
"""
from pathlib import Path
import re

VAULT = Path(r"C:\Users\yassi\AI Projects\The Arabic Tongue (nature-genome-application)")

# Each entry: file → (new_title, new_lead) replacing the existing H1 and the
# first paragraph after it (skipping blockquotes / metadata lines).
REWRITES = {
    "04-cross-linguistic/tafsir-coran-tier-a-cognates.md": (
        "# Arabic words with an echo in other languages",
        "The Qur'an does not stop at Arabic. Some of its core words carry the same consonant skeleton and the same meaning in languages far away — Greek, Latin, English, Welsh, Old Norse. Not borrowings. **Preserved echoes.**\n\n"
        "This page collects nineteen confirmed pairs, each anchored to a Qur'anic verse and tested against four strict bars of verification. The bars rest on the sound-substitution laws of Dr. **Ali Fahmi Khshim** — past president of the Libyan Arabic Language Academy, author of *رحلة الكلمات*."
    ),
    "04-cross-linguistic/tier-b-cognates.md": (
        "# The wider cognate roster · 50 curated findings",
        "Beyond the nineteen Quran-anchored pairs sits a wider band of fifty curated Arabic ↔ Indo-European matches. Each was confirmed by the project's semantic-scoring pipeline at score ≥ 0.8, then hand-picked across the seven IE branches we cover (Greek, Latin, Old Irish, Welsh, Gothic, Old English, Old Norse).\n\n"
        "Treat these as a researcher's reading list, not a verified Tier-A roster: single-rater curation, no four-bar warranty, but every entry has been re-checked under a calibrated second pass."
    ),
    "04-cross-linguistic/tier-b-cognates-ar.md": (
        "# السِّجِلُّ الأَوسَع لِلجِنَاسات · ٥٠ مَدخَلًا مُنتَقىً",
        "وَراءَ الأَزواج التِّسعةَ عَشَرَ المَرسيّةَ قُرآنيًّا يَقَع شَريطٌ أَوسَع: خَمسون جِنَاسًا عَرَبيّ-هندوأوربيّ مُنتَقىً بِاليَد. كُلٌّ مِنها أَكَّدَتها مَنظومةُ التَّسجيل الدَّلاليّ عند نُقطة ≥ ٠٫٨، ثُمَّ اختيرَ يَدويًّا مِن الفُروع السَّبعة (اليونانيّة، اللاتينيّة، الإيرلَنديّة القَديمة، الوِلزيّة، القوطيّة، الإنجليزيّة القَديمة، النَّوردِيّة القَديمة).\n\n"
        "هي قائمةُ قِراءةٍ لِلباحِث، لا روزنامةً مُؤَكَّدةً بِالضَّوابط الأَربعة: مُقَيِّمٌ واحِد، بِلا ضَمانة Tier-A، لَكِنّ كُلَّ مَدخَلٍ خَضَع لِإعادة-قِراءةٍ مُعايَرةٍ ثانية."
    ),
    "04-cross-linguistic/quranic-loanword-audit.md": (
        "# Are these Qur'anic words really 'borrowed'? · a re-reading",
        "For centuries Orientalists and some classical lexicographers flagged certain Qur'anic words as foreign — borrowed from Persian, Greek, Aramaic, Ethiopic. *Firdaws*, *qamīṣ*, *injīl*, *qalam*, *qirṭās*, *ṭāghūt*, twenty-seven cases in all.\n\n"
        "This audit re-reads each one under the operative grammar. **Twenty-six of the twenty-seven resolve as native Arabic compositions**, as reverse-borrowings *from* Arabic into the neighbour language, or as words preserved jointly with neighbour languages of the same era. Only one (*zanjabīl*) remains an honest residue."
    ),
    "04-cross-linguistic/quranic-loanword-audit-ar.md": (
        "# هل كَلِماتُ القُرآن «دَخيلة» حقًّا؟ · قِراءةٌ جَديدة",
        "قُرونًا، وَسَمَ بَعضُ المُستَشرِقين وَ بَعضُ المُعجَميّين الكلاسيكيّين كَلِماتٍ قُرآنيّةً بِأَنَّها أَجنبيّة — مِن الفارِسيّة، اليونانيّة، الآراميّة، الحَبَشيّة. فِردَوس، قَميص، إنجيل، قَلَم، قِرطاس، طاغوت، سَبعٌ وعِشرون حالةً في المَجموع.\n\n"
        "هذه المُراجَعة تُعيد قِراءة كُلٍّ مِنها تَحت النَّحو العَمَليّ. **سِتٌّ وعِشرون مِن السَّبعِ وعِشرين تَنحَلّ كَ تَركيباتٍ عَرَبيّةٍ أَصيلة**، أَو كَ استِعاراتٍ عَكسيّةٍ *مِن* العَرَبيّة إلى اللُّغة المُجاوِرة، أَو كَ كَلِماتٍ مَحفوظةٍ بَين العَرَبيّة وجارَتِها في الحِقبة نَفسِها. الباقي واحِدٌ (زَنجَبيل) بَقايا صادِقة."
    ),
    "02-architecture/lv2-operative-grammar.md": (
        "# The eleven ways a root puts a meaning together",
        "Every Arabic trilateral root works the same way: two letters form a meaning-seed, the third letter joins and shapes how the seed acts. The shape can be one of **eleven** specific operations — not three, not twenty, **eleven** — plus a twelfth label (LOANWORD) reserved for the rare non-native root.\n\n"
        "This document defines each of the eleven modes, gives examples, and records that all 2,285 attested trilaterals in the reference lexicon fit one of them, with no forcing."
    ),
    "02-architecture/lv2-operative-grammar-ar.md": (
        "# الإِحدى عَشَر طَريقةً يَبني بِها الجَذرُ مَعناه",
        "كُلُّ جَذرٍ ثُلاثيٍّ في العَرَبيّة يَعمَل بِالطَّريقة نَفسِها: حَرفان يُكَوِّنانِ بِذرةَ مَعنى، ثُمَّ يَنضَمُّ الحَرفُ الثالِث فيُشَكِّل كَيف تَعمَلُ البِذرة. والشَّكلُ يُمكِن أَن يَكون أَحَدَ **أَحَدَ عَشَرَ** عَمَلًا مُحَدَّدًا — لا ثَلاثة، لا عِشرون، **أَحَدَ عَشَر** — مَع تَسميةٍ ثانيةَ عَشَرَة (LOANWORD) مَحفوظةٍ لِلجَذرِ غَير-الأَصيل النادِر.\n\n"
        "هذه الوَثيقة تُعَرِّف كُلَّ بابٍ مِن الأَبواب الأَحَدَ عَشَر، تُعطي أَمثِلة، وتُسَجِّل أَنّ ٢٬٢٨٥ جَذرًا ثُلاثيًّا مُسَجَّلًا في المُعجَم المَرجِع يَنطَبِق عَلى أَحَدِها، بِلا تَكَلُّف."
    ),
    "05-audits/2026-05-21-opus-calibrated-770.md": (
        "# Re-scoring all 770 cognates · the calibrated second pass",
        "The original bulk-discovery pipeline produced 770 Arabic ↔ Indo-European cognate pairs at score ≥ 0.65. A separate 150-pair sample test then suggested the bulk pass was a bit lenient at the 0.65 boundary. Instead of footnoting the inflated number, we re-scored **every one of the 770 pairs** under the same calibrated rubric, blind to the original score."
    ),
    "05-audits/2026-05-21-opus-calibrated-770-ar.md": (
        "# إعادةُ تَسجيل الـ ٧٧٠ جِنَاسًا كُلّها · التَّمريرة الثانية المُعايَرة",
        "أَنتَجَ أَنبوبُ الاكتِشاف الجُمليّ الأَصليّ ٧٧٠ زَوجًا عَرَبيًّا ↔ هندوأوربيًّا عند نُقطة ≥ ٠٫٦٥. ثُمَّ أَوحى اختبارُ عَيِّنةٍ مِن ١٥٠ زَوجًا أَنّ التَّمريرة الجُمليّة كانَت مُتَساهِلةً قَليلًا عند عَتَبة الـ ٠٫٦٥. بَدَلَ أَن نَكتُبَ حاشيةً عَلى الرَّقم المُتَضَخِّم، أَعَدنا تَسجيل **كُلِّ زَوجٍ مِن السَّبعمائة والسَّبعين** تَحت الرُّبريك المُعايَر نَفسِه، أَعمى عَن النُّقطة الأَصليّة."
    ),
    "05-audits/2026-05-21-khshim-laws-audit.md": (
        "# Khshim's sound-substitution laws · tested on real cognate data",
        "Dr. Ali Fahmi Khshim's *رحلة الكلمات* catalogued nine sound-substitution laws — predictable ways Arabic consonants map to Indo-European ones (ك ↔ Q, ف ↔ P, ج ↔ K/G, ض ↔ D, ص ↔ K/S, pharyngeals, sibilants, liquids, labials).\n\n"
        "Until now those laws were cited on textbook authority. With 770 confirmed Arabic ↔ IE cognates on hand, we can ask the laws an empirical question: **how often does each one actually fire?** And: **do any patterns that aren't on Khshim's list fire so strongly they deserve a tenth-law place?**"
    ),
    "05-audits/2026-05-21-khshim-laws-audit-ar.md": (
        "# قَوانينُ خشيم الصَّوتيّة · مُختَبَرةً عَلى بَيانات حَقيقيّة",
        "كاتلَجَ الدكتور علي فهمي خشيم في «رِحلة الكلمات» تِسعةَ قَوانينَ لِلإبدال الصَّوتيّ — طُرُقًا قابِلةً لِلتَّوَقُّع تُقابِل بِها الصَّوامتُ العَرَبيّةُ الصَّوامتَ الهندوأوربيّة (ك ↔ Q، ف ↔ P، ج ↔ K/G، ض ↔ D، ص ↔ K/S، الحَلقيّات، الصَّفيريّات، السَّوائل، الشَّفويّات).\n\n"
        "حَتّى الآنَ كانَت هذه القَوانينُ مُستَشهَدًا بِها عَلى تَخويلٍ مَدرَسيّ. مَع وُجود ٧٧٠ جِنَاسًا مُؤَكَّدًا في اليَد، يُمكِن أَن نَطرَح عَلى القَوانين سُؤالًا تَجريبيًّا: **كَم مَرّةً يَنشَط كُلٌّ مِنها فِعلًا؟** وَ: **هَل مِن أَنماطٍ خارِجَ قائمة خشيم تَنشَط بِما يَكفي لِاستِحقاق مَوضِع قانونٍ عاشِر؟**"
    ),
    "05-audits/2026-05-20-coherent-gaps-held-out.md": (
        "# Sixteen unused letter-pairs · what the framework predicts they would mean",
        "A scaled-up generative test on Arabic identified sixteen two-letter combinations the framework calls **COHERENT but unattested** — pairs where the operative grammar produces a clean predicted meaning, but the reference lexicon does not catalogue any trilateral root using them.\n\n"
        "If the framework is genuinely generative, those predicted meanings should match something Arabic actually has — even if it lives in rarer, geminate, or dialectal form. This document tests that, by searching Lisān al-ʿArab, Tāj al-ʿArūs, and the wider classical record for each of the sixteen, then grading the match against the pre-registered prediction."
    ),
    "05-audits/2026-05-20-coherent-gaps-held-out-ar.md": (
        "# سِتَّةَ عَشَرَ زَوجَ حَرفَين لم تُسَمِّها العَرَبيّة · ماذا يَتَنَبَّأُ الإطار أَنّها ستَعنيه",
        "اختبارٌ تَوليديٌّ مُوَسَّع حَدَّد سِتَّةَ عَشَرَ تَوليفةً مِن حَرفَين يُسَمّيها الإطار **مُتَّسِقةً لَكِن غَير-مُسَجَّلة** — أَزواجٌ يُنتِج فيها النَّحوُ العَمَليُّ مَعنىً مُتَوَقَّعًا نَظيفًا، لَكِنّ المُعجَمَ المَرجِعَ لا يُسَجِّل أَيَّ جَذرٍ ثُلاثيٍّ يَستَخدِمُها.\n\n"
        "إن كان الإطارُ تَوليديًّا حَقًّا، فالمَعاني المُتَوَقَّعة يَجِب أَن تُطابِق شَيئًا تَملِكُه العَرَبيّةُ فِعلًا — حَتّى لَو سَكَن في صورةٍ أَنذَر، أَو مُضَعَّفة، أَو لَهجِيّة. هذه الوَثيقةُ تَختَبِر ذلك، بِالبَحث في لِسان العَرَب، تاج العَروس، والسِّجِلّ الكلاسيكيّ الأَوسَع عَن كُلٍّ مِن السِّتَّة عَشَر، ثُمَّ تَحكُم عَلى المُطابَقةِ مُقابِل التَّنبُّؤ المُسَجَّل مُسبَقًا."
    ),
    "05-audits/2026-05-21-pass3-evaluation.md": (
        "# Pass 3 · can the framework predict unused four-letter words too?",
        "The earlier sixteen-pair test confirmed the operative grammar is genuinely **generative at the binary level**: when given an unused two-letter combination, it can predict what Arabic *would* have meant there, and is right about half the time.\n\n"
        "Pass 3 asks the harder question one level up: **can it predict at the quadriliteral level?** For twenty unused four-letter skeletons the framework's grammar produces a specific semantic prediction. This document tests those predictions against classical Arabic lexicography — and reports the result honestly."
    ),
    "05-audits/2026-05-21-pass3-evaluation-ar.md": (
        "# Pass 3 · هَل يَتَنَبَّأُ الإطارُ بِكَلِماتٍ مِن أَربعةِ حُروفٍ أَيضًا؟",
        "أَكَّدَ اختبارُ الـ ١٦ زَوجًا السابِق أَنّ النَّحو العَمَليّ تَوليديٌّ حَقًّا **عَلى المُستَوى الثُّنائيّ**: حينَ يُعطى تَوليفةً مِن حَرفَين غَير-مُستَخدَمة، يُمكِنُه التَّنبُّؤ بِما *كانَت ستَعنيه* العَرَبيّة، ويُصيب حَوالي نِصف الحالات.\n\n"
        "يَطرَح Pass 3 السُّؤالَ الأَصعَب طَبَقةً أَعلى: **هَل يَستَطيع التَّنبُّؤ عَلى المُستَوى الرُّباعيّ؟** لِعِشرين هَيكَلًا مِن أَربعة حُروفٍ غَير-مُستَخدَم، يُنتِج نَحوُ الإطار تَنبُّؤًا دَلاليًّا مُحَدَّدًا. هذه الوَثيقةُ تَختَبِر تِلكَ التَّنبُّؤاتِ مُقابِل المُعجَم العَرَبيّ الكلاسيكيّ — وتُسَجِّل النَّتيجة بِنَزاهة."
    ),
}

# Also normalize remaining vendor-name leftovers in titles
TITLE_NORM = {
    "Calibrated التَّمريرة الثانية Re-Scoring": "Calibrated re-scoring",
    "التَّمريرة الأُولى ≥0.65 output": "Pass 1 ≥0.65 output",
}

count = 0
for rel, (new_h1, new_lead) in REWRITES.items():
    p = VAULT / rel
    if not p.exists():
        print(f"  ! missing: {rel}")
        continue
    text = p.read_text(encoding="utf-8")
    # Match: first H1 line + everything up to (and including) the first non-blockquote,
    # non-meta-line paragraph following it.
    lines = text.splitlines()
    if not lines or not lines[0].startswith("# "):
        print(f"  ! no H1: {rel}")
        continue

    # Find the lead paragraph: skip blockquote lines, meta lines (start with **Date:**),
    # blank lines, and HR (---). Stop at the next paragraph.
    end = 0
    state = "title"  # title -> spaces -> lead -> done
    para_start = None
    for i, line in enumerate(lines[1:], start=1):
        stripped = line.strip()
        if state == "title":
            if not stripped:
                continue
            if stripped.startswith(">") or stripped.startswith("---") or stripped.startswith("**Date:**") or stripped.startswith("**التاريخ:**"):
                # Keep these meta-lines after the new title; find the lead AFTER them
                continue
            state = "lead"
            para_start = i

        if state == "lead":
            if not stripped:
                end = i
                break

    if end == 0:
        end = len(lines)

    # Build new content
    # Keep the original metadata lines (blockquotes, **Date:**) below the new H1+lead
    meta_lines = []
    for line in lines[1:para_start] if para_start else lines[1:]:
        stripped = line.strip()
        if stripped.startswith(">") or stripped.startswith("**Date:**") or stripped.startswith("**التاريخ:**"):
            meta_lines.append(line)

    new_head = new_h1 + "\n\n" + new_lead
    if meta_lines:
        new_head += "\n\n" + "\n".join(meta_lines)

    rest = "\n".join(lines[end:])
    new_text = new_head + "\n" + rest
    if new_text != text:
        p.write_text(new_text, encoding="utf-8")
        count += 1
        print(f"  rewrote: {rel}")

# Normalize awkward titles
for md in VAULT.rglob("*.md"):
    s = md.read_text(encoding="utf-8")
    o = s
    for old, new in TITLE_NORM.items():
        s = s.replace(old, new)
    if s != o:
        md.write_text(s, encoding="utf-8")
        print(f"  normalized: {md.relative_to(VAULT)}")

print(f"\nTotal docs rewritten: {count}")
