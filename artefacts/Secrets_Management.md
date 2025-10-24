# Secrets Management Strategy – Stage 9

## هدف
این سند روش نگه‌داری و مصرف اسرار (Secrets) برای پلتفرم USDT Auction را مشخص می‌کند. مطابق Playbook، هیچ Secret نباید در مخزن Git ذخیره شود و باید یا در متغیر محیطی یا در Windows Credential Manager نگه‌داری شود.

## نام‌گذاری
تمام Credentialها باید با پیشوند `USDT_` ذخیره شوند تا با اسکریپت‌ها و کد پشتیبان هماهنگ باشند.

| Secret | Credential Manager Entry | متغیر محیطی متناظر | توضیح |
|--------|--------------------------|---------------------|-------|
| `DATABASE_URL` | `USDT_DATABASE_URL` | `DATABASE_URL` | رشته اتصال PostgreSQL (مثلاً `postgresql+psycopg2://…`). |
| `RABBITMQ_URL` | `USDT_RABBITMQ_URL` | `RABBITMQ_URL` | آدرس اتصال RabbitMQ (ampq). |
| `TELEGRAM_BOT_TOKEN` | `USDT_TELEGRAM_BOT_TOKEN` | `TELEGRAM_BOT_TOKEN` | توکن Bot تلگرام. |
| سایر اسرار (API Keys، Webhook Secrets) | `USDT_<SECRET_NAME>` | `<SECRET_NAME>` | بر اساس نیاز سرویس‌های آینده. |

## ایجاد Credential
a. **PowerShell**
```powershell
$secret = Read-Host 'Enter DATABASE_URL' -AsSecureString
$credential = New-Object System.Management.Automation.PSCredential('USDT_DATABASE_URL', $secret)
cmd /c "cmdkey /generic:USDT_DATABASE_URL /user:usdt /pass:$($credential.GetNetworkCredential().Password)"
```

ب. **ابزار گرافیکی**
1. `Credential Manager` → `Windows Credentials` → `Add a generic credential`.
2. `Internet or network address`: `USDT_DATABASE_URL`
3. `User name`: `usdt` (placeholder)
4. `Password`: مقدار Secret

## بازیابی در کد
ماژول `src/backend/config/settings.py` تابع `get_secret` را ارائه می‌کند که ابتدا متغیر محیطی و سپس Credential Manager را بررسی می‌کند. اگر هیچکدام موجود نباشند، خطای مشخصی برمی‌گرداند.

## حساب کاربری سرویس‌ها
- سرویس‌های Windows (PostgreSQL، RabbitMQ) باید با اکانت محدود اجرا شوند.
- حسابی با نام پیشنهادی `USDT_SVC` برای اجرای اپلیکیشن ایجاد شده و فقط دسترسی مورد نیاز را دریافت می‌کند.

## گردش‌کار CI/CD
1. در Agent ویندوزی CI، Credentialها با نام‌های بالا تزریق می‌شوند.
2. Pipeline قبل از اجرای تست‌ها متغیرهای محیطی را از Credential Manager استخراج و ست می‌کند.
3. در صورت نیاز به چرخش کلید، ابتدا Credential جدید ثبت، سپس Deploy انجام و Credential قدیمی حذف می‌شود.

> **یادآوری:** هیچ Secret در فایل‌های متنی (از جمله `config/test.env`) ذخیره نشود؛ مقدار آن‌ها باید یا تهی بماند یا به Credential Manager ارجاع دهد.
