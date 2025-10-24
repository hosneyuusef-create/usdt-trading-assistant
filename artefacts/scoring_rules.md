# Stage 15 Scoring Rules

## قواعد رتبه‌بندی
- **RFQ نوع خرید (buy):** Quote با کمترین `unit_price` در اولویت است. در صورت تساوی قیمت، "زمان ارسال" (submitted_at) زودتر برنده می‌شود.
- **RFQ نوع فروش (sell):** Quote با بیشترین `unit_price` اولویت دارد؛ سپس زمان ارسال.
- **Partial Fill:** اگر شرط `split_allowed` در RFQ فعال باشد، ظرفیت چند Quote به ترتیب رتبه تا پوشش کامل مقدار RFQ تخصیص داده می‌شود.

## سناریوهای رد Quote
- `rfq_expired`: Quote پس از انقضای RFQ ارسال شده است.
- `rfq_closed`: وضعیت RFQ باز نیست.
- `rate_limited`: در بازه 45 ثانیه‌ای بیش از یک Quote ارسال شده است.
- `not_selected`: Quote واجدشرایط بود اما به دلیل رتبه پایین انتخاب نشد.

## لاگ و ممیزی
- `logs/award_events.json`: شامل تمام تصمیم‌های Award با جزئیات Tie-break، reviewer/approver و میزان تخصیص.
- `artefacts/Award_Audit.xlsx`: بر اساس لاگ بالا تولید می‌شود و ستون‌های `award_id`, `rfq_id`, `selection_mode`, `reviewer`, `approver`, `decision_reason`, `tie_break_rule`, `timestamp` را نگهداری می‌کند.
