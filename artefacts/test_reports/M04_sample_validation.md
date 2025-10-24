# Stage 4 Sample Data Validation

- تاریخ: 2025-10-23
- اجرا: Codex Agent
- ورودی‌ها: `artefacts/DomainEntities.xlsx`, `artefacts/domain_glossary.md`, `tests/data/seed/sample_data.sql`

## مراحل بررسی
1. **RFQ → Quote**
   - رکوردهای نمونه در `tests/data/seed/sample_data.sql` برای RFQ `RFQ-1001` و Quote‌های مربوطه بررسی شد.
   - ارتباط Customer → RFQ و Provider → Quote با ساختار DomainEntities تطبیق دارد.
2. **Quote → Award → Settlement**
   - Award نمونه برای RFQ `RFQ-1001` به Quote `Q-5001` نگاشت شده و در DomainEntities ارتباط N:1 ثبت گردید.
   - Settlement و SettlementLeg ها وضعیت `PendingFiat` و `PendingUSDT` داشتند؛ ساختار جداول Partial-Fill تأیید شد.
3. **Settlement → Dispute → Actions**
   - سناریوی dispute در seed داده با Evidence و DisputeAction بررسی شد؛ glossary تعریف نقش‌ها را پوشش می‌دهد.

نتیجه: روابط اصلی RFQ→Quote→Award→Settlement→Dispute مطابق مدل دامنه ثبت شد و عدم انطباق مشاهده نشد.
