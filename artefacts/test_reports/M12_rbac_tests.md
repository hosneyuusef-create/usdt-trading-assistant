# Stage 12 RBAC Tests – Summary

- تاریخ: 2025-10-23
- فرمان: `python -m pytest tests/test_provider_management.py tests/test_rbac.py`
- نتیجه: Passed

## سناریوهای پوشش داده‌شده
- درخواست بدون هدر `X-Role` منجر به خطای 401 و ثبت رویداد `missing_role_header`.
- نقش `customer` هنگام فراخوانی `/provider/register` با خطای 403 و reason=`forbidden` رد شد.
- نقش `admin` قادر به ثبت پرووایدر واجد شرایط و نقش `operations` قادر به مشاهده فهرست پرووایدرهای مجاز بود.
- فایل ممیزی `logs/access_audit.json` شامل هر چهار رویداد (دو شکست، دو موفق) است.
