# Stage 17 Partial Fill Tests – Summary

- تاریخ: 2025-10-23
- فرمان: `python -m pytest tests/test_partial_fill.py`
- نتیجه: Passed

## نکات کلیدی
- سناریوی Reallocation: بخشی از ظرفیت از پرووایدر اولیه به پرووایدر جدید منتقل و وضعیت legs به روز شد.
- سناریوی Cancel: لغو پا موجب ثبت دلیل و به‌روزرسانی فایل `artefacts/Order_Reconciliation.xlsx` شد.
- لاگ `logs/partial_fill_events.json` تمام رویدادهای آغاز، بازتخصیص و لغو را ثبت می‌کند.
