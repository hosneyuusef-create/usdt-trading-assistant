# API Validation Report – Stage 6

- تاریخ: 2025-10-23
- Artefactها: `api/settlement_api.yaml`, `api/telegram_webhook.yaml`

## خلاصه
1. **OpenAPI ولیدیشن**
   - ابزار: `openapi-spec-validator 0.7.2`
   - نتیجه: `settlement_api.yaml` بدون خطا اعتبارسنجی شد (Trace-ID header، اسکیماهای RFQ/Quote/Award/Settlement/EvidenceProof).
2. **AsyncAPI/وب‌هوک**
   - فایل `api/telegram_webhook.yaml` با `pyyaml` parse شد و شامل الزامات HMAC، Idempotency key و Rate limiting است.

## ملاحظات امنیتی
- تمام پاسخ‌ها و درخواست‌ها Trace-ID دارند.
- داده‌های Pre-Award در `RFQMasked` ماسک شده‌اند.
- وب‌هوک از هدر `X-Signature-SHA256` برای تأیید پیام و `X-Idempotency-Key` برای جلوگیری از تکرار استفاده می‌کند.

## نتیجه
استانداردهای مرحله ۶ برای مستندسازی API و وب‌هوک رعایت شد و هیچ خطای ولیدیشن مشاهده نشد.
