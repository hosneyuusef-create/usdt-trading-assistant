# Environment Recovery Guide

این سند سناریوهای خرابی و مراحل بازگردانی محیط توسعه/تست را مشخص می‌کند. در صورت هرگونه شکست یا رفتار غیرمنتظره، مطابق این راهنما عمل کنید.

## اصول کلی
1. **متوقف کردن تغییرات:** در صورت بروز خطا، قبل از هر اقدامی تغییرات محلی را Commit نکنید؛ ابتدا وضعیت را ثبت کنید.
2. **ثبت وضعیت:** پیام خطا، لاگ‌ها و شرایط وقوع (مرحله، اسکریپت، نسخه کد) را یادداشت کنید.
3. **بازگشت به شاخهٔ سالم:** اگر روی شاخهٔ `feature/...` هستید و تغییرات غیرضروری ایجاد شده، با `git status` بررسی و با `git restore` یا `git checkout -- <file>` فایل‌های ناخواسته را به حالت قبل بازگردانید.

## سناریوی 1: شکست Migration یا خرابی دیتابیس
1. اجرای اسکریپت Rollback (`db/migrations/rollback/001_initial_schema_rollback.sql`) روی پایگاه داده تست.
2. پاک‌سازی پایگاه داده تست:  
   ```powershell
   psql -d usdt_trading -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
   ```
3. اجرای مجدد Migration:  
   ```powershell
   psql -d usdt_trading -f db/migrations/001_initial_schema.sql
   ```
4. اعمال Seed داده نمونه (در صورت نیاز):  
   ```powershell
   powershell.exe -ExecutionPolicy Bypass -File tests\data\seed\seed.ps1
   ```
5. اجرای تست‌های مرتبط (`scripts/tests/run_integration_tests.ps1`) برای اطمینان از سلامت.

## سناریوی 2: خراب شدن تنظیمات یا Secrets
1. بررسی `readme_repo_structure.md` برای محل فایل‌های تنظیمات.  
2. حذف تنظیمات موقتی و بازگردانی از نسخه پشتیبان (Credential Manager برای Secrets).  
3. اجرای مجدد `scripts/setup/zero_to_dev.ps1` با پارامتر `-ResetConfig` (در صورت موجود بودن) یا بازنویسی فایل‌های کانفیگ پیش‌فرض.
4. تست Healthcheck سرویس (`/health`) جهت اطمینان از عملکرد صحیح.

## سناریوی 3: شکست سرویس یا فساد وابستگی‌ها
1. توقف سرویس‌های نصب‌شده (Service Windows) با `Stop-Service`.
2. پاک‌سازی محیط مجازی Python (`Remove-Item -Recurse -Force .venv`) و ایجاد مجدد:  
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
3. اجرای اسکریپت‌های تست واحد جهت بررسی سریع.
4. راه‌اندازی دوباره سرویس‌ها (`Start-Service`) و بررسی لاگ‌ها (`Event Viewer` یا لاگ برنامه).

## سناریوی 4: خرابی کامل محیط (راه‌اندازی صفر تا صد)
1. Snapshot یا نسخه پشتیبان سیستم را بازیابی کنید (در صورت وجود).  
2. اسکریپت `scripts/setup/zero_to_dev.ps1` را اجرا کنید تا محیط از ابتدا نصب شود.  
3. داده‌های نمونه (Seed) و تنظیمات لازم را اعمال کنید.  
4. تست‌های واحد، یکپارچه و E2E را بلافاصله اجرا کنید تا از صحت محیط مطمئن شوید.

## ثبت و گزارش
- پس از بازیابی موفق، گزارشی شامل علت خرابی، گام‌های انجام‌شده و نتیجه را در `artefacts/stage_completion_checklist.md` (قسمت Lessons Learned) بنویسید.
- اگر نیاز به تغییر دائمی در فرآیند وجود دارد، یک ADR جدید ثبت کنید و Assumptions Log را به‌روز نمایید.
