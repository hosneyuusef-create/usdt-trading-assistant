# Quote Validation Rules – Stage 14

## الزامات اصلی
- فقط پرووایدرهای واجدشرایط (امتیاز ≥70 و وثیقه ≥200,000,000 IRR، فعال) می‌توانند Quote ارسال کنند.
- مبلغ Quote باید کمتر یا مساوی مقدار RFQ باشد.
- Quote باید قبل از `expires_at` RFQ ثبت شود؛ در غیر این صورت با reason=`rfq_expired` رد و در `logs/quote_events.json` ثبت می‌شود.
- نرخ ارسال: هر پرووایدر در هر RFQ حداکثر یک Quote در بازه 45 ثانیه‌ای ارسال می‌کند (`rate_limited` در صورت تخطی).
- درخواست‌های پس از بسته‌شدن RFQ (status ≠ open) با reason=`rfq_closed` رد می‌شوند.

## لاگ و ممیزی
- `logs/notification_events.json`: ثبت اعلان‌های ناشناس ارسال‌شده به پرووایدرهای واجدشرایط همراه با Trace-ID.
- `logs/quote_events.json`: ثبت تمام Quoteها (قبول/رد) با دلیل و زمان ثبت.

## وابستگی‌ها
- ماژول RFQ (Stage 13) برای وضعیت و شرایط ویژه استفاده می‌شود.
- RBAC نقش‌های `provider`, `operations`, `admin`, `compliance` را برای ارسال و مشاهده کنترل می‌کند.
