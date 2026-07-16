# حملة مراجعة الأسر القبطية

**فُتحت:** 2026-07-15. **الحالة:** طابور محلي غير منشور، بلا أحكام مسجلة بعد.

## نقطة البدء

تبدأ الحملة بالأسر التي تضم عضوًا حالته `floor-review-required`. هذه الحالة ليست رفضًا؛ معناها أن التطبيع الآلي لم ينتج هيكلًا صالحًا للبحث وأن البطاقة تحتاج قارئًا بشريًا. اليونانيات تُعزل قبل أي حكم في مسار قرض مستقل.

## ترتيب البطاقة

1. افتح الأسرة كاملة، لا الصورة المفردة.
2. مرر عدسة الاسترداد: الجذر الكامل، والأجوف، والنواة، ومروحة المعاني، والتثليث المصري القبطي العربي.
3. مرر عدسة التشكيك بعد ذلك: القرض، والمتجانس، والمصدر القديم، وصحة القانون الصوتي.
4. لا تغلق الأسرة قبل العدستين.
5. إذا انحرف عضو عن حكم الأسرة فسجل له نقضًا مستقلًا بدل تغيير بقية الأعضاء.

## أوامر العمل

```powershell
python scripts/recovery_inventory.py family-queue --lens recovery --language coptic --processing-status floor-review-required
python scripts/recovery_inventory.py family-card --family-id "FAMILY_ID"
python scripts/recovery_family_review.py record --family-id "FAMILY_ID" --lens recovery --reviewer "NAME" --date "YYYY-MM-DD" --result "RESULT" --notes "NOTES"
python scripts/recovery_family_review.py record --family-id "FAMILY_ID" --lens skeptical --reviewer "NAME" --date "YYYY-MM-DD" --result "RESULT" --notes "NOTES" --loan-screen clear --homonym-screen clear --source-check clear
```

تبقى العدادات والبطاقات في الجرد المحلي خارج git. هذا الملف يثبت ترتيب الحملة فقط ولا ينقل أرقامها إلى النشر.
