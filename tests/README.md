# Test Execution Guide

این راهنما روش اجرای تست‌ها، محل خروجی و الزامات هر دسته را مشخص می‌کند. همه‌ی تست‌ها باید به کمک اسکریپت‌های استاندارد اجرا شوند.

## پیش‌نیازها
- Python 3.11 (مطابق Tech Stack).
- نصب ابزارهای پروژه (`scripts/setup/zero_to_dev.ps1` اجرا شده باشد).
- پایگاه داده Postgres و RabbitMQ مطابق دستور Stage 8.
- متغیرهای محیطی تست در `config/test.env` تنظیم شده باشند.

## ساختار تست‌ها
| مسیر | توضیح |
|------|-------|
| `tests/unit/` | تست‌های واحد برای ماژول‌های مستقل. |
| `tests/integration/` | تست‌هایی که چند ماژول/سرویس را کنار هم بررسی می‌کنند. |
| `tests/e2e/` | سناریوهای انتها به انتها (مطابق Stage 24). |
| `tests/data/seed/` | داده‌ی نمونه برای پر کردن پایگاه داده در تست‌ها. |

## اجرای تست‌های واحد
- دستور: `powershell.exe -ExecutionPolicy Bypass -File ..\scripts\tests\run_unit_tests.ps1`
- خروجی گزارش: `artefacts/test_reports/unit_test_report.xml`

## اجرای تست‌های یکپارچه
- دستور: `powershell.exe -ExecutionPolicy Bypass -File ..\scripts\tests\run_integration_tests.ps1`
- پیش‌نیاز: پایگاه داده تست با Seed داده آماده شده باشد (اسکریپت در `tests/data/seed/seed.ps1` اجرا می‌شود و فایل `tests/data/seed/sample_data.sql` را اعمال می‌کند).
- خروجی گزارش: `artefacts/test_reports/integration_test_report.xml`

## اجرای تست‌های E2E
- دستور: `powershell.exe -ExecutionPolicy Bypass -File ..\scripts\tests\run_e2e_tests.ps1`
- پیش‌نیاز: سرویس‌ها و Bot تلگرام در محیط تست بالا باشند؛ فایل `tests/data/e2e_scenarios.json` مسیرها را مشخص می‌کند.
- خروجی گزارش: `artefacts/test_reports/e2e_test_report.xml`

## جمع‌بندی و پوشش کد
- پس از اجرای تست‌های واحد، گزارش پوشش کد در `artefacts/test_reports/coverage.xml` ذخیره می‌شود.
- معیار پوشش: حداقل 80٪ خطوط بحرانی و 100٪ مسیرهای حیاتی (Stage 24).

## رفع خطا
- اگر تستی شکست خورد، گزارش مربوطه (XML و Log) را بررسی کن.
- در صورت شکست Seed یا فساد داده، راهنمای `docs/environment_recovery_guide.md` را دنبال کن؛ سپس اسکریپت Seed و تست مرتبط را دوباره اجرا کن.
- اصلاحات باید در همان شاخه کاری Commit شوند و مجدداً اسکریپت اجرا شود.
- در صورت نیاز به دادهٔ جدید، فایل Seed یا سناریو باید به‌روز و Commit شود.
