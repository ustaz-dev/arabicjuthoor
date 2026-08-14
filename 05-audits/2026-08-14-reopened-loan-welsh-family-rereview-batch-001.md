# إعادة قراءة عائلات اللسان للحصاد الويلزي، الدفعة 001 (2026-08-14)

## الضابط الإلزامي

أعيد حساب البطاقات الست الصادرة بالمروحة الحالية وبـ`frozen_event.resolve` وحده، ولم يتغير حكم واحدة.

| الصورة | المقابل | السابق | الحالي | النتيجة |
|---|---|---|---|---|
| `mwg` | `موج` | ROOT-TRACE | ROOT-TRACE | ثابت |
| `melg` | `ملج` | ROOT-ECHO | ROOT-ECHO | ثابت |
| `senos` | `سن` | NUCLEUS-TRACE | NUCLEUS-TRACE | ثابت |
| `caer` | `قر` | NUCLEUS-TRACE | NUCLEUS-TRACE | ثابت |
| `môr` | `مور` | ROOT-ECHO | ROOT-ECHO | ثابت |
| `car` | `جر` | NUCLEUS-TRACE | NUCLEUS-TRACE | ثابت |

## سبب الإعادة

ألحقت 150 بطاقة ناسخة لأن النسخة السابقة سبقت إلزام المسار بطباعة قراءة عائلات اللسان لكل مرشح اكتمل فيه الصوت والحدث. شُغّل منطق `search_arabic_root_senses.py` بلا قطع للعرض، وبقي المدار حكمًا يدويًا.

## الحصيلة

- فُحص وكُتب: 150 بطاقة ناسخة.
- تغير الحكم: 0 بطاقة.
- موجب بالأرجل الثلاث: 3 بطاقة.
- أغلق بمانح سامي مسمى: 4 بطاقة.
- بقي OPEN-CANDIDATE: 142 بطاقة.
- سبب الفتح: 116 بطاقة، اكتمل الصوت والحدث، وقُرئت شواهد الجذور كاملة، ولم يقنع مدار يدوي.
- سبب الفتح: 11 بطاقة، لم يكتمل مسار صوتي مسمى بعد البحث بالحرفين واللسان.
- سبب الفتح: 13 بطاقة، لم تولد المروحة مرشحًا من الهيكل.
- سبب الفتح: 2 بطاقة، لم تتعين مدخلة من قاموس الفرع توافق سياق الصف.

## تغييرات الحكم

لم يتغير حكم بطاقة.

## الصلات المثبتة

1. `het` ↔ `حوط` (ROOT-TRACE)
2. `can` ↔ `كنن` (ROOT-TRACE)
3. `solid` ↔ `صلد` (ROOT-TRACE)

## الإغلاقات غير النسبية

- `lemon`: SEMITIC-SOURCE-TRANSMISSION؛ العربية لَيْمُون (laymūn)؛ 04-cross-linguistic/data/lane_d_middle_english_transmissions.jsonl، السطر 88.
- `canon`: SEMITIC-SOURCE-TRANSMISSION؛ الأكدية qanû، القصبة والمقياس؛ data/alawlaqi-prior-attempts.json، مادة قانون، ونقل باقر ص.141.
- `canon`: SEMITIC-SOURCE-TRANSMISSION؛ الأكدية qanû، القصبة والمقياس؛ data/alawlaqi-prior-attempts.json، مادة قانون، ونقل باقر ص.141.
- `canon`: SEMITIC-SOURCE-TRANSMISSION؛ الأكدية qanû، القصبة؛ 04-cross-linguistic/data/lane_d_middle_english_transmissions.jsonl، السطر 14.
