# Stage 1 Test Execution Summary

| اسکریپت | وضعیت | توضیح | خروجی |
|---------|-------|--------|--------|
| run_unit_tests.ps1 | Failed | اجرای pytest به علت نبود پلاگین `pytest-cov` متوقف شد (ارور unrecognized arguments). وابستگی‌های لیست شده در `requirements.txt` به دلیل محدودیت شبکه نصب نشده‌اند. | artefacts/test_reports/M01_run_unit_tests.log |
| run_integration_tests.ps1 | Failed | اسکریپت به دلیل استفاده از پارامتر رزرو شده `Host` در PowerShell اجرا نمی‌شود (`Cannot overwrite variable Host`). | artefacts/test_reports/M01_run_integration_tests.log |
| run_e2e_tests.ps1 | Failed | مسیر `tests/e2e` در مخزن فعلی وجود ندارد؛ pytest بدون تست اجرا شده خروجی خالی ایجاد کرد. | artefacts/test_reports/M01_run_e2e_tests.log |
| بازبینی دستی ۱۰ الزام | Passed | نمونه‌گیری تصادفی مطابق دستور Stage 1 انجام شد و انطباق الزامات تأیید گردید. | artefacts/test_reports/M01_manual_sampling.md |

اقدام اصلاحی پیشنهادی:
1. فراهم کردن دسترسی نصب وابستگی‌ها (pytest-cov و بسته‌های پروژه) یا تهیه نسخه آفلاین.
2. اصلاح اسکریپت `run_integration_tests.ps1` برای استفاده از نام پارامتر غیررزرو شده (مثلاً `DbHost`).
3. تکمیل مجموعه تست‌های E2E یا ایجاد مسیر جایگزین حاوی سناریوهای Stage 24.
