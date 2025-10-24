# Workflow Walkthrough Report – Stage 7

- تاریخ: 2025-10-23
- ورودی‌ها: `artefacts/Workflow_Statecharts.pdf`, `artefacts/Workflow_BPMN.bpmn`, API Stage 6، Domain Stage 4

## سناریوی کامل (RFQ → Settlement)
1. مشتری RFQ ایجاد می‌کند (وضعیت Draft → Open).
2. Bot اعلان می‌فرستد، Quote دریافت و RFQ Award می‌شود (PartialFillPending).
3. Settlement دو پا (fiat/usdt) وارد وضعیت InProgress شده و با ارائه Evidence هر دو Settled شدند.
4. مسیر مطابق دیاگرام و API `/settlements/{id}` → `status=settled` ثبت شد.

## سناریوی «عدم دریافت پیشنهاد»
1. RFQ در حالت Open باقی ماند؛ Gateway `Quotes Received?` در BPMN مسیر `noQuote` را فعال کرد.
2. سیستم به وضعیت Cancelled رفت و NotificationEvent با SLA هشدار ایجاد شد (مطابق statechart بخش Failure).
3. Escalation ثبت شد و SLA rule در یادداشت دیاگرام مستند است.

## Observations
- Partial-Fill مسیر جایگزینی و Escalation به dispute در هر دو Artefact نمایش داده شد.
- حالت‌های Settled، Partially_Disputed، Fully_Disputed مطابق statechart هستند.
- هیچ سناریوی باز دیگری باقی نماند؛ فرضیات جدید نیاز نشد.

نتیجه: گردش‌های اصلی و سناریوی failure مطابق دستورالعمل بررسی و تایید شد.
