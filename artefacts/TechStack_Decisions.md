# Stage 2 – Tech Stack Decisions (v1.0 – 2025-10-23)

## خلاصه تصمیمات کلیدی
| لایه | فناوری منتخب | نسخه/پیکربندی | دلیل انتخاب | ارجاع الزامات |
|------|--------------|----------------|-------------|----------------|
| زبان اصلی | Python | 3.11.2 (مطابق استاندارد تیم) | پشتیبانی از async، سازگاری با کتابخانه‌های تلگرام و FastAPI، هزینه نگه‌داری پایین | `dastoor.txt` بخش‌های 5 تا 12 |
| فریم‌ورک سرویس | FastAPI | 0.110 | عملکرد بالا، پشتیبانی از OpenAPI برای قراردادهای Stage 6، همخوانی با Async IO | RTM: M01-REQ-001، M01-REQ-005، M01-REQ-017 |
| پلتفرم بات | python-telegram-bot | >=20,<21 | پوشش کامل API تلگرام و پشتیبانی از webhook native روی Windows | `dastoor.txt` بخش 12 |
| پایگاه داده | PostgreSQL | 15 (Windows x64) | ACID، پشتیبانی از Partial-Fill و تراکنش‌ها؛ نصب Native روی Windows امکان‌پذیر است | RTM: M01-REQ-010، M01-REQ-017 |
| صف پیام | RabbitMQ | 3.13 (Windows Service) | هماهنگی رویدادهای تسویه و اعلان؛ سازگاری با pika و Windows Service | RTM: M01-REQ-012، M01-REQ-022 |
| ORM/دسترسی داده | SQLAlchemy + Alembic | 2.0 / 1.13 | پشتیبانی از migration‌ها (Stage 5) و async | مرحله 5 – طراحی دیتابیس |
| لاگینگ ساختاریافته | structlog | 23.2.0 | تولید لاگ JSON با Trace ID؛ پشتیبانی از الزامات ممیزی | RTM: M01-REQ-022 |
| تست | pytest + pytest-cov | 8.0.0 / 4.1.0 | استاندارد سازمانی، سازگار با CI؛ گزارش پوشش به 80٪+ | Stage 24 |
| کانفیگ و اسرار | python-dotenv + Windows Credential Manager | python-dotenv 1.0.0 | مدیریت ایمن متغیرهای محیطی، سازگار با Native Windows | RTM: M01-REQ-016 |
| استقرار | Windows Server 2019 Native Services | PowerShell Scripts | الزام منع Docker؛ اسکریپت‌های PowerShell برای setup و CI | RTM: M01-REQ-020 |

> نسخه‌ها مطابق `requirements.txt` و محدودیت‌های Stage 2 تعیین شده‌اند. هر تغییر باید در ADR ثبت و به‌روزرسانی گردد.

## جزئیات تصمیم‌گیری
1. **Python 3.11.2 در برابر 3.10**  
   - *مزایا:* بهبود عملکرد async و pattern matching؛ پشتیبانی کامل کتابخانه‌های مورد نیاز.  
   - *ریسک:* وابستگی به بسته‌هایی که ممکن است هنوز با 3.11 سازگار نباشند؛ با بررسی مستندات رسمی حل شد.

2. **FastAPI در برابر Django**  
   - *انتخاب:* FastAPI 0.110  
   - *استدلال:* حجم کمتر، پاسخگویی بالا برای Webhook تلگرام، تولید خودکار OpenAPI. Django برای پروژه‌های monolithic سنگین‌تر است و به mixinهای اضافی نیاز دارد.

3. **RabbitMQ (Windows Service)**  
   - *علت:* سناریوهای اختلاف و اعلان‌ها به صف قابل اعتماد نیاز دارند. RabbitMQ نسخه Windows رسمی دارد و با PowerShell نصب می‌شود. Kafka به دلیل پیچیدگی استقرار Native رد شد.

4. **PostgreSQL 15**  
   - *علت:* ویژگی‌های advanced (JSONB، transactional DDL) برای Partial-Fill، مانیتورینگ و Audit ضروری است. SQL Server Express گزینه جایگزین بود ولی نیاز به مجوز و ابزار اضافه داشت.

5. **python-telegram-bot 20.x**  
   - *علت:* پشتیبانی از Bot API 7+ و webhook. کتابخانه Telethon نیاز به session و key management دارد؛ برای این پروژه اضافه است.

6. **CI/Build بدون Docker**  
   - استفاده از PowerShell و GitHub Actions با Windows runners. اسکریپت‌های `scripts/setup/zero_to_dev.ps1` پایه کار را انجام خواهند داد و در مرحله 8 تکمیل می‌شوند.

## POCهای برنامه‌ریزی‌شده
| POC | شرح | نتیجه فعلی (Stage 2) | مسیر Artefact |
|-----|------|----------------------|---------------|
| اتصال PostgreSQL | اجرای اسکریپت Python برای برقراری اتصال و اجرای کوئری سلامت | **Passed** – پس از فراهم شدن بسته آفلاین، اتصال با موفقیت برقرار شد (Log: `artefacts/test_reports/M02_db_poc.log`) | `artefacts/test_reports/M02_db_poc.log` |
| ارسال پیام تلگرام | استفاده از `python-telegram-bot` برای ارسال پیام آزمایشی به Bot sandbox | **Passed** – پیام آزمایشی با Bot متصل به چت 277000838 ارسال شد (Log: `artefacts/test_reports/M02_telegram_poc.log`) | `artefacts/test_reports/M02_telegram_poc.log` |

اقدام اصلاحی برای هر دو POC طبق فرض AL-004 در Assumptions Log ثبت شد و در تاریخ 2025-10-23 انجام و بسته شد.

## وابستگی‌ها و گام‌های بعد
- تهیه بسته‌های آفلاین برای `psycopg2-binary`, `python-telegram-bot`, `pika`, `structlog`, `pytest-cov` و قرار دادن آن‌ها در Mirror داخلی یا پوشه اشتراکی.
- نگارش اسکریپت نصب PowerShell (Stage 8) برای اعمال وابستگی‌ها بدون اینترنت.
- تعریف pipeline GitHub Actions برای اجرای pytest روی Windows runner (مرحله 8/24).

## ارجاعات
- `dastoor.txt` – بخش‌های 3 تا 19 (الزامات نقش‌ها، اعلان‌ها، تسویه، محدودیت Native)
- `marahel.txt` – Stage 2 مشخصات خروجی و معیار پذیرش
- `requirements.txt` – نسخه‌های مصوب
- `global_playbook.md` – بندهای 2، 3، 5 مربوط به کنترل کیفیت و ثبت تغییرات

---
*تهیه‌شده توسط Codex Agent – Stage 2 (2025-10-23)*
