# Zero-to-Dev Guide (Stage 8)

این راهنما مراحل آماده‌سازی محیط توسعه و CI را برای پلتفرم USDT Auction (Windows Native) توضیح می‌دهد.

## پیش‌نیازها
- Windows 10/11 یا Windows Server 2019+ با دسترسی PowerShell 5.1 یا بالاتر
- Python 3.11 (مطابق Tech Stack) و pip در PATH
- PostgreSQL 16 (Native) و سرویس در حال اجرا (`postgresql-x64-16`)
- RabbitMQ Windows Service (در صورت عدم نصب، اسکریپت هشدار می‌دهد)
- دسترسی به حساب کاربری محدود برای اجرای سرویس‌ها (غیر-Administrator)

## اجرای اسکریپت
```powershell
# از ریشه مخزن
powershell -ExecutionPolicy Bypass -File .\scripts\setup\zero_to_dev.ps1 -LogPath artefacts\zerotodev_execution.log
```

### کاری که اسکریپت انجام می‌دهد
1. بررسی نسخه PowerShell و ابزارهای کلیدی (Python، psql، RabbitMQ)
2. ایجاد یا به‌روزرسانی محیط مجازی `.venv` و نصب `requirements.txt`
3. بررسی فایل `config/test.env` و اخطار در صورت نبود مقدار برای متغیرها
4. ایجاد پایگاه داده `usdt_trading` در صورت نبود
5. اجرای Migration پایه (`db/migrations/001_initial_schema.sql`)
6. اجرای تست‌های `tests/test_migration.py` و `tests/test_performance.py`
7. اجرای Rollback و اعمال مجدد Migration جهت اطمینان از Clean State
8. ثبت زمان اجرا و جمع‌بندی در لاگ خروجی

## خروجی‌ها
- `artefacts\zerotodev_execution.log` : لاگ کامل اجرای اسکریپت (شروع با Start-Transcript)
- `artefacts\SchemaPerformanceReport.md` : گزارش کارایی حاصل از تست Performance
- `tests/test_*` : تست‌های Python برای صحت دیتابیس

## لاگ و رفع عیب
- فهرست وقایع و خطاها در `artefacts\zerotodev_execution.log` ذخیره می‌شود.
- در صورت بروز خطا، اجرای اسکریپت متوقف و پیام خطا در لاگ ثبت می‌شود.
- راهکارهای پیشنهادی:
  - **psql not found**: مسیر نصب PostgreSQL را به پارامتر `-PostgresBin` بدهید.
  - **نصب RabbitMQ**: بسته رسمی Windows را نصب و سرویس را با حساب محدود اجرا کنید.
  - **pip install 실패**: اطمینان از دسترسی اینترنت یا مخزن داخلی پکیج‌ها.

## حساب‌های کاربری توصیه‌شده
- سرویس‌های پایگاه داده و RabbitMQ باید تحت حساب محدود اجرا شوند (مثلاً `USDT_SVC`).
- متغیرهای محیطی حساس در Windows Credential Manager با پیشوند `USDT_` نگهداری شوند (مطابق Stage 9).

## اجرای مجدد
اسکریپت idempotent است؛ اجرای مجدد باعث به‌روزرسانی venv، اجرا/بازگردانی Migration و تست‌های صحت محیط می‌شود.

## ویدئو
فایل `artefacts/zerotodev_demo.mp4` شامل دموی کوتاه اجرای اسکریپت است (نمونه Placeholder؛ نسخه کامل توسط تیم عملیات ضبط می‌شود).

