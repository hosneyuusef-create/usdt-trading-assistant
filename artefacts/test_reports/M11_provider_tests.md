# Stage 11 Provider Tests – Summary

- تاریخ: 2025-10-23
- فرمان‌ها:
  - `python -m pytest tests/test_provider_management.py`
- نتیجه: Passed

## نکات کلیدی
- ثبت پرووایدر با امتیاز 88.5 و وثیقه 250,000,000 IRR منجر به eligibility کامل شد.
- پرووایدر با وثیقه 150,000,000 IRR به‌درستی با خطای `insufficient_collateral` علامت خورد.
- تابع `filter_for_rfq` تنها پرووایدرهای واجد شرایط را بازگرداند و رویداد `rfq_eligibility_evaluated` در لاگ `usdt.provider` ثبت شد.
