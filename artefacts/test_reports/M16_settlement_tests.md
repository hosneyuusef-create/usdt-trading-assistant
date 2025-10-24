# Stage 16 Settlement Tests – Summary

- تاریخ: 2025-10-23
- فرمان: `python -m pytest tests/test_settlement.py`
- نتیجه: Passed

## نکات کلیدی
- ایجاد Settlement از Award و تولید دو پا (Fiat/USDT) برای هر پرووایدر.
- ارسال و تایید مدارک معتبر، تغییر وضعیت به `settled`.
- تلاش ناموفق دوباره سبب Escalation و ثبت رویداد در `logs/dispute_events.json`.
- بررسی Deadline و Escalation خودکار برای پاهایی که در مهلت مقرر مدارک ندارند.
