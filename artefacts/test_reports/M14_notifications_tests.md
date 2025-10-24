# Stage 14 Notification & Quote Tests – Summary

- تاریخ: 2025-10-23
- فرمان: `python -m pytest tests/test_notifications.py`
- نتیجه: Passed

## سناریوهای پوشش داده‌شده
- ارسال اعلان ناشناس RFQ و ثبت رویداد در `logs/notification_events.json`.
- ثبت دو Quote موفق برای یک RFQ و مشاهده آنها توسط نقش عملیات.
- رد Quote دیرهنگام با reason=`rfq_expired` و ثبت در `logs/quote_events.json`.
- اعمال Rate Limit برای پرووایدر و بازگشت خطای `rate_limited` در درخواست‌های پشت‌سرهم.
