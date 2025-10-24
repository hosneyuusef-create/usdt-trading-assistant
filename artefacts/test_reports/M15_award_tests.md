# Stage 15 Award Engine Tests – Summary

- تاریخ: 2025-10-23
- فرمان: `python -m pytest tests/test_award_engine.py`
- نتیجه: Passed

## نکات کلیدی
- Tie-break: دو Quote با قیمت برابر بررسی شد و Quote ارسال‌شده زودتر انتخاب شد.
- Partial Fill: برای RFQ با `split_allowed=true` ظرفیت دو Quote به ترتیب تا سقف مقدار RFQ تخصیص داده شد.
- فایل‌های ممیزی `logs/award_events.json` و `artefacts/Award_Audit.xlsx` پس از اجرای موفق تولید شدند.
