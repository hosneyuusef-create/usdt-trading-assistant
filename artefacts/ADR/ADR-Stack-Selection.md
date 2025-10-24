# Architecture Decision Record – Stack Selection

- **ADR ID:** ADR-20251023-01
- **عنوان:** انتخاب استک فنی اصلی (Python 3.11 + FastAPI + PostgreSQL + RabbitMQ)
- **زمینه / مسئله:** سیستم مناقصه USDT باید Native روی Windows اجرا شود و در عین حال پاسخگوی الزامات عملکردی (RFQ، Award، Settlement، Dispute) و غیرعملکردی (Traceability، Audit، SLA) باشد. لازم است پشته‌ای انتخاب شود که با محدودیت منع Docker، اجرای Bot تلگرام، صف رویداد و عملیات تسویه سازگار باشد.
- **گزینه‌های بررسی‌شده:**
  1. Python 3.11 + FastAPI + PostgreSQL + RabbitMQ (پیشنهادی)
  2. .NET 8 + ASP.NET Core + SQL Server + Azure Service Bus
  3. Node.js 20 + NestJS + MongoDB + Redis Streams
- **تصمیم:** گزینه 1 (Python 3.11، FastAPI، PostgreSQL، RabbitMQ) پذیرفته شد.
- **استدلال (Trade-offs):**
  - Python و FastAPI قابلیت پیاده‌سازی سریع وب‌هوک تلگرام و APIهای Stage 6 را دارند؛ همچنین برای Partial-Fill و تسویه async مناسب‌اند.
  - PostgreSQL 15 روی Windows نصب رسمی دارد و از تراکنش‌های پیچیده برای Partial-Fill/Dispute پشتیبانی می‌کند؛ SQL Server نیازمند مجوز و پیکربندی اضافه بود.
  - RabbitMQ Windows Service اجازه مدیریت صف اعلان و Settlement را بدون اتکا به Docker می‌دهد؛ Azure Service Bus نیاز به اتصال ابری داشت و سیاست Native را نقض می‌کرد.
  - کتابخانه python-telegram-bot در اکوسیستم Python بالغ است؛ در .NET نیاز به wrapper غیراستاندارد و در Node.js پیاده‌سازی‌های پراکنده وجود دارد.
  - تیم فنی تجربه عملی با Python/FastAPI دارد که ریسک تحویل را کاهش می‌دهد.
- **تأثیرات (مثبت / منفی):**
  - معماری: معماری سرویس‌محور سبک با async امکان‌پذیر می‌شود؛ نیازمند طراحی دقیق کانکارنسی و صف‌بندی است.
  - API: FastAPI تولید خودکار OpenAPI می‌دهد و Stage 6 را تسهیل می‌کند؛ اما نیاز به مدیریت dependency injection دستی دارد.
  - داده: PostgreSQL امکانات JSONB و transaction-level را فراهم می‌کند؛ مدیریت replication روی Windows باید در مرحله 25 بررسی شود.
  - تست: ابزار pytest و pytest-cov برای این پشته استاندارد است؛ باید بسته‌ها به‌صورت آفلاین فراهم شوند (Assumption AL-001/AL-004).
  - استقرار: اسکریپت‌های PowerShell برای نصب PostgreSQL/RabbitMQ لازم است؛ نیاز به پایش سرویس‌ها روی Windows Service Manager وجود دارد.
- **آیتم‌های پیگیری:**
  - تهیه بسته‌های آفلاین ماژول‌های Python (مرحله 8).
  - نوشتن اسکریپت نصب PostgreSQL/RabbitMQ و مستندسازی rollback (مرحله 8/25).
  - ارزیابی مانیتورینگ RabbitMQ/PostgreSQL در مرحله 23.
- **مرحله مرتبط (M#):** M02
- **وضعیت (Proposed / Accepted / Superseded):** Accepted
- **تاریخ تصمیم:** 2025-10-23
- **تأثیر بر NFR:** پشتیبانی از SLA اعلان (RabbitMQ + Async)، انطباق امنیتی (Trace ID با structlog)، قابلیت بازیابی (PostgreSQL + backup native)، توسعه‌پذیری ماژولار (FastAPI).

---
