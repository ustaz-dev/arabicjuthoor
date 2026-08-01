# المسار د: محضر الإقفال

## قياس الطابور

- الإنجليزية القديمة: بدأ الجرد من الوحدة 1 وانتهى عند الوحدة 11695؛ بقي في الجرد: 0. فُحصت 11694 وحدة عضو، واستهلك الطابور 1 فجوة مصدر مسماة.
- الإيرلندية القديمة: بدأ الجرد من الوحدة 1 وانتهى عند الوحدة 8506؛ بقي في الجرد: 0. فُحصت 8506 وحدة عضو، ولا فجوة سطر في المصدر.
- قياس الباقي: صفر وحدة غير مفحوصة في اللقطتين المثبتتين. لا تمنح هذه العبارة شهادة parse كاملة للسطر الإنجليزي المقطوع؛ حالته باقية `SOURCE-GAP`.
- سؤال المؤلف المسجل والمتخطى: هل يستبدل مورد الإنجليزية القديمة بلقطة كاملة تعيد السطر 7949 المقطوع؟ هذا تنزيل مصدر جديد، فلم يُنفذ ولم يوقف بقية الطابور.

## الرقمان المفصولان

- الإنجليزية القديمة، الصلات الموجبة: 4.
- الإنجليزية القديمة، الإغلاقات: 3947.
- الإيرلندية القديمة، الصلات الموجبة: 1.
- الإيرلندية القديمة، الإغلاقات: 3287.
- لا يجمع أي زوج من هذه الأرقام.

## شكل التسجيل

- الإنجليزية القديمة: 3951 بطاقة كاملة و7743 سطر تغطية آلي؛ المجموع 11694 عضوًا مسجلًا.
- الإيرلندية القديمة: 3288 بطاقة كاملة و5218 سطر تغطية آلي؛ المجموع 8506 عضوًا مسجلًا.
- البطاقة الكاملة مقصورة على الحكم الموجب أو الإغلاق النهائي، وسطر التغطية مقصور على العضو غير المحكوم.

## حدود النتيجة

- كل عضو معنى قابل للتحليل في اللقطة له مصير مسجل: بطاقة RECOVERY-v2 كاملة للحكم أو الإغلاق، أو سطر واحد في `lane_d_coverage.jsonl` لعدم الإصدار. الصورة `form_of` إغلاق هوية كامل لكنها لا تولد حكمًا مستقلا.
- بقيت فجوات الأداة والقانون والمصدر بأسمائها، ولم تتحول إلى `NO-TRACE`.
- لم تُفتح نتائج القوطية أو النوردية أو الويلزية في هذه الجولة، ولم تُجر مقارنة عائد الفروع بعد.
- لم يُشغّل سكربت مشترك يعيد بناء ملفًا مشتركًا، ولم يُعدّل خط البرهان.

## الملفات التي كُتب فيها

- `04-cross-linguistic/readings/old-english.md`
- `04-cross-linguistic/readings/old-irish.md`
- `04-cross-linguistic/data/lane_d_source_snapshot_manifest.json`
- `04-cross-linguistic/data/lane_d_member_inventory.jsonl`
- `04-cross-linguistic/data/lane_d_coverage.jsonl`
- `scripts/lane_d_build_old_english_old_irish.py`
- `scripts/lane_d_audit_old_english_old_irish.py`
- `05-audits/lane-d-oe-batch-001.md`
- `05-audits/lane-d-oe-batch-002.md`
- `05-audits/lane-d-oe-batch-003.md`
- `05-audits/lane-d-oe-batch-004.md`
- `05-audits/lane-d-oe-batch-005.md`
- `05-audits/lane-d-oe-batch-006.md`
- `05-audits/lane-d-oe-batch-007.md`
- `05-audits/lane-d-oe-batch-008.md`
- `05-audits/lane-d-oe-batch-009.md`
- `05-audits/lane-d-oe-batch-010.md`
- `05-audits/lane-d-oe-batch-011.md`
- `05-audits/lane-d-oe-batch-012.md`
- `05-audits/lane-d-oe-batch-013.md`
- `05-audits/lane-d-oe-batch-014.md`
- `05-audits/lane-d-oe-batch-015.md`
- `05-audits/lane-d-oe-batch-016.md`
- `05-audits/lane-d-oe-batch-017.md`
- `05-audits/lane-d-oe-batch-018.md`
- `05-audits/lane-d-oe-batch-019.md`
- `05-audits/lane-d-oe-batch-020.md`
- `05-audits/lane-d-oe-batch-021.md`
- `05-audits/lane-d-oe-batch-022.md`
- `05-audits/lane-d-oe-batch-023.md`
- `05-audits/lane-d-oe-batch-024.md`
- `05-audits/lane-d-oi-batch-001.md`
- `05-audits/lane-d-oi-batch-002.md`
- `05-audits/lane-d-oi-batch-003.md`
- `05-audits/lane-d-oi-batch-004.md`
- `05-audits/lane-d-oi-batch-005.md`
- `05-audits/lane-d-oi-batch-006.md`
- `05-audits/lane-d-oi-batch-007.md`
- `05-audits/lane-d-oi-batch-008.md`
- `05-audits/lane-d-oi-batch-009.md`
- `05-audits/lane-d-oi-batch-010.md`
- `05-audits/lane-d-oi-batch-011.md`
- `05-audits/lane-d-oi-batch-012.md`
- `05-audits/lane-d-oi-batch-013.md`
- `05-audits/lane-d-oi-batch-014.md`
- `05-audits/lane-d-oi-batch-015.md`
- `05-audits/lane-d-oi-batch-016.md`
- `05-audits/lane-d-oi-batch-017.md`
- `05-audits/lane-d-oi-batch-018.md`
- `05-audits/lane-d-two-lens-review.md`
- `05-audits/lane-d-coverage-compaction-2026-07-30.md`
- `05-audits/lane-d-final-summary.md`
