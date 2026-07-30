# محضر المسار أ: الغوص الآرامي بالحجم

**التاريخ:** 2026-07-29  
**الحالة:** عمل محلي ينتظر المراجعة المضادة الثالثة، بلا أي أمر Git.

## النطاق والملكية

اقتصر هذا المسار على `04-cross-linguistic/readings/aramaic.md`، وعلى سكربتات تبدأ بـ`lane_a_aramaic_`. لم يمس ملف قراءة آخر، ولا ملفًا مشتركًا، ولا خط البرهان، ولا أداة مجمدة.

وحدة المسح من B09 إلى B13 نافذة متتالية بحسب الرتبة المصدرية، واستمر العمل حتى الرتبة 913 بعد استبعاد أعضاء دفعات المسار أ السابقة. لم ينتق العمل روائع، ولم يتوقف عند انخفاض العائد. كل موجب يحمل بطاقة كاملة ومدارًا صريحًا وشاهدين عربيين قديمين مستقلين، وما لم ينحسم حمل سببًا واحدًا ومضى.

## الحصيلة

| الدفعة | المفحوص | الصلات الموجبة الجديدة | الإغلاقات | غير الصادر |
|---|---:|---:|---:|---:|
| B01 | 30 | 18 | 0 | 12 |
| B02 | 20 | 19 | 0 | 1 |
| B03 | 20 | 18 | 0 | 2 |
| B04 | 25 | 25 | 0 | 0 |
| B05 | 16 | 15 | 0 | 1 |
| B06 | 10 | 10 | 0 | 0 |
| B07 | 30 | 3 | 0 | 27 |
| B08 | 30 | 3 | 0 | 27 |
| B09A | 25 | 1 | 0 | 24 |
| B09B | 75 | 7 | 0 | 68 |
| B10A | 50 | 1 | 0 | 49 |
| B10B | 50 | 6 | 0 | 44 |
| B11A | 50 | 4 | 0 | 46 |
| B11B1 | 25 | 2 | 0 | 23 |
| B11B2 | 25 | 1 | 0 | 24 |
| B12A | 50 | 6 | 0 | 44 |
| B12B | 50 | 4 | 0 | 46 |
| B13 | 100 | 22 بطاقة موجبة، منها 19 هوية جديدة | 0 | 78 |
| **المجموع الخام** | **681** | **165 بطاقة موجبة** | **0** | **516** |

العداد الصارم يعد بهوية العضو لا بعدد البطاقات. بعد حذف التكرار مع المصائر المحلية السابقة كانت الحصيلة الرسمية **162 هوية موجبة جديدة**. في B13 وحدها حررت 22 بطاقة موجبة بعد إسقاط هوية `חמם` الموجودة في خط الأساس، وكان منها 19 هوية جديدة بحسب عداد الهوية، لأن ثلاث هويات كانت ممثلة في دفعات محلية سابقة. لم تنسب الزيادة الخام إلى اكتشاف جديد.

صلات B09 الجديدة هي:

- `תמרתא` ↔ تمرة: أثر جذر مباشر.
- `בסמא` ↔ بسم: صدى جذر في جوار السرور وعلامته الوجهية.
- `סברא` ↔ سبر: صدى جذر في جوار نفاذ النظر واختبار الكنه.
- `הלל` ↔ هلل: صدى جذر في جوار الثناء الديني المنطوق.
- `זוע` ↔ زوع: أثر جذر في التحريك والاهتزاز.
- `גברותא` ↔ جبر: صدى جذر في القوة القاهرة.
- `תוב` ↔ ثوب: صدى جذر في العودة والتكرار.
- `עולא` ↔ عول: أثر جذر في الجور والميل عن الحق.

## مواضع ضبط النفس

- لم يعد المسار `ענבתא` ↔ عنب، ولا `כף` ↔ كف، ولا `רגם` ↔ رجم، ولا `דרגא` ↔ درجة، لأنها صلات صادرة سابقًا.
- أبقى `ילידותא` «الولادة» غير صادرة مع جمال المقارنة، لأن حقل المدخل لا ينشر تحليلها إلى `ילד`، فلا تنزع حروف الصيغة بالتخمين.
- أبقى `שמי` «يسمي» غير صادرة، لأن ياء الفرع النهائية تقابل واو `سمو` خارج موضع `GLD-01` الأول.
- أبقى `עורבא` «الغراب» على `LAW-GAP` السابق، ولم يخترع صفًا لانعكاس الغين في العين الآرامية.
- عزل القروض اليونانية والفارسية والعبرية المسماة، وفصل الأعلام والأدوات والمتجانسات.
- لم يحول أي نقص شاهد إلى إغلاق مصطنع، ولذلك بقي عدد الإغلاقات الجديدة صفرًا.

## الفحوص

- `python scripts/lane_a_validate_batch.py --scope new --language aramaic --strict`: نظيف، `selected=235` و`new-positive=162` و`new-closure=0` و`issues=0`.
- `python scripts/check_charge_purity.py`: نظيف.
- أصلح `scripts/lane_a_aramaic_repair_card_contract.py` عقد النشر ميكانيكيًا في أقسام المسار أ وحدها. أضاف من بيانات البطاقة نفسها أقدم صورة مستعادة، والخطوة صفر بصيغتها المعيارية، ومؤشر اليتم. وتحقق أيضًا من وجود إشعاع الأسرة في الفرع وفي العربية في الأقسام كلها. لم يغير حكمًا ولا مدارًا ولا شاهدًا.
- `python scripts/check_publication_consistency.py`: نظيف، `RESULT: CLEAN` وصفر مخالفة في `aramaic.md`.

## الملفات التي كتب فيها المسار

- `04-cross-linguistic/readings/aramaic.md`
- `scripts/lane_a_aramaic_append_discovery_batch_01.py`
- `scripts/lane_a_aramaic_repair_discovery_batch_01.py`
- `scripts/lane_a_aramaic_append_discovery_batch_02.py`
- `scripts/lane_a_aramaic_append_discovery_batch_03.py`
- `scripts/lane_a_aramaic_append_discovery_batch_04.py`
- `scripts/lane_a_aramaic_append_discovery_batch_05.py`
- `scripts/lane_a_aramaic_append_discovery_batch_06.py`
- `scripts/lane_a_aramaic_append_inventory_batch_07.py`
- `scripts/lane_a_aramaic_append_inventory_batch_08.py`
- `scripts/lane_a_aramaic_append_inventory_batch_09a.py`
- `scripts/lane_a_aramaic_append_inventory_batch_09b.py`
- `scripts/lane_a_aramaic_append_inventory_batch_10a.py`
- `scripts/lane_a_aramaic_append_inventory_batch_10b.py`
- `scripts/lane_a_aramaic_append_inventory_batch_11a.py`
- `scripts/lane_a_aramaic_append_inventory_batch_11b1.py`
- `scripts/lane_a_aramaic_append_inventory_batch_11b2.py`
- `scripts/lane_a_aramaic_append_inventory_batch_12a.py`
- `scripts/lane_a_aramaic_append_inventory_batch_12b.py`
- `scripts/lane_a_aramaic_append_inventory_batch_13.py`
- `scripts/lane_a_aramaic_inspect_window.py`
- `scripts/lane_a_aramaic_inspect_fans.py`
- `scripts/lane_a_aramaic_repair_card_contract.py`
- `05-audits/lane-a-2026-07-29-aramaic-deep-volume-report.md`

## الخاتمة العددية

- الصلات الموجبة الجديدة بحسب هوية العضو: **162**
- الإغلاقات الجديدة: **0**
