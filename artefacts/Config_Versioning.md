# Configuration Versioning Strategy — Stage 22 (M22)

**تاریخ:** 2025-10-24
**نسخه:** v1.0
**مسئول:** Codex Agent

---

## 1. مرور کلی (Overview)

این سند استراتژی مدیریت تنظیمات نسخه‌دار سامانه را تعریف می‌کند. تنظیمات قابل تغییر بدون نیاز به بازنشر (redeploy) یا راه‌اندازی مجدد اپلیکیشن اعمال می‌شوند و امکان بازگشت به نسخه‌های قبلی (rollback) فراهم است.

**اهداف:**
- مدیریت تنظیمات به صورت نسخه‌دار با Audit Trail کامل
- اعمال تغییرات بدون نیاز به راه‌اندازی مجدد یا redeploy
- امکان rollback به نسخه‌های قبلی در صورت بروز مشکل
- ثبت تاریخچه کامل تغییرات با ذکر زمان، مسئول و دلیل

---

## 2. معماری Versioned Config Store

### 2.1 ساختار ذخیره‌سازی

تنظیمات در مسیر `config/versions/` ذخیره می‌شوند:

```
config/versions/
├── current.json         # تنظیمات فعلی فعال
├── history.json         # تاریخچه تمام نسخه‌ها
```

### 2.2 Schema نسخه‌دار

هر نسخه تنظیمات شامل فیلدهای زیر است:

```json
{
  "version": 1,
  "configuration": { ... },
  "created_at": "2025-10-24T12:00:00",
  "created_by": "admin_user",
  "rollback_token": "unique_secure_token",
  "change_reason": "Initial system configuration"
}
```

**فیلدهای کلیدی:**
- `version`: شماره نسخه (Sequential و یکتا)
- `configuration`: Snapshot کامل تنظیمات
- `created_at`: زمان ایجاد نسخه (UTC)
- `created_by`: نام کاربری Admin ایجادکننده
- `rollback_token`: Token امنیتی برای rollback
- `change_reason`: دلیل تغییر (الزامی برای Audit)

---

## 3. تنظیمات قابل مدیریت

### 3.1 تنظیمات RFQ و مناقصه

- **bidding_deadline_minutes** (default: 10): مهلت ارسال پیشنهاد
- **min_valid_quotes** (default: 2): حداقل پیشنهادهای معتبر
- **allow_deadline_extension** (default: true): مجاز بودن تمدید یک‌باره

### 3.2 تنظیمات تسویه (Settlement)

- **settlement_order** (default: fiat_first): ترتیب گام‌های تسویه (fiat_first | crypto_first)
- **fiat_settlement_timeout_minutes** (default: 15): مهلت تسویه ریالی
- **crypto_settlement_timeout_minutes** (default: 15): مهلت تسویه USDT
- **min_blockchain_confirmations** (default: 1): حداقل تأییدات بلاک‌چین

### 3.3 تنظیمات شبکه و امنیت

- **allowed_networks** (default: ["TRC20", "BEP20", "ERC20"]): شبکه‌های مجاز

### 3.4 تنظیمات Eligibility پرووایدر

- **min_provider_score** (default: 60): حداقل امتیاز پرووایدر
- **min_provider_collateral** (default: 0): حداقل وثیقه پرووایدر

### 3.5 وزن‌های امتیازدهی (Scoring Weights)

- **success_rate** (default: 0.4): وزن نرخ موفقیت
- **on_time_settlement** (default: 0.3): وزن تسویه به‌موقع
- **dispute_ratio** (default: 0.2): وزن نسبت اختلاف
- **manual_alerts** (default: 0.1): وزن هشدارهای دستی

**نکته:** مجموع وزن‌ها باید برابر 1.0 باشد (اعتبارسنجی در سمت سرور).

### 3.6 تنظیمات Dispute و SLA

- **dispute_evidence_deadline_minutes** (default: 30): مهلت ارسال مدارک اختلاف
- **dispute_resolution_deadline_hours** (default: 4): مهلت رأی ادمین

### 3.7 تنظیمات Telemetry

- **notification_latency_warning_ms** (default: 5000): آستانه هشدار تأخیر اعلان
- **notification_failure_warning_rate** (default: 0.05): آستانه هشدار شکست اعلان

### 3.8 نسخه قالب‌های پیام

- **message_template_version** (default: "M19-2025-10-24"): نسخه فعال message templates

---

## 4. API Endpoints

### 4.1 دریافت تنظیمات فعلی

```http
GET /config/current
Authorization: Bearer <admin_token>
```

**پاسخ:**
```json
{
  "version": 5,
  "configuration": { ... },
  "created_at": "2025-10-24T14:30:00",
  "created_by": "admin",
  "is_latest": true
}
```

**دسترسی:** `config:view` (Admin, Operations)

### 4.2 به‌روزرسانی تنظیمات

```http
POST /config/update
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "configuration": {
    "bidding_deadline_minutes": 15,
    "min_valid_quotes": 3,
    ...
  },
  "change_reason": "Increase bidding deadline based on market feedback",
  "created_by": "admin_user"
}
```

**پاسخ:** نسخه جدید با `version` افزایش یافته

**دسترسی:** `config:update` (فقط Admin)

**نکات:**
- تغییرات بلافاصله اعمال می‌شوند (بدون نیاز به redeploy)
- نسخه جدید در history ثبت می‌شود
- `change_reason` الزامی است (حداقل 10 کاراکتر)

### 4.3 دریافت تاریخچه تنظیمات

```http
GET /config/history
Authorization: Bearer <admin_token>
```

**پاسخ:**
```json
{
  "total_versions": 5,
  "current_version": 5,
  "history": [
    {
      "version": 1,
      "created_at": "2025-10-24T10:00:00",
      "created_by": "system",
      "change_reason": "Initial system configuration",
      "rollback_token": "token_v1"
    },
    {
      "version": 2,
      "created_at": "2025-10-24T12:00:00",
      "created_by": "admin",
      "change_reason": "Increase settlement timeout",
      "rollback_token": "token_v2"
    },
    ...
  ]
}
```

**دسترسی:** `config:view` (Admin, Operations)

### 4.4 Rollback به نسخه قبلی

```http
POST /config/rollback
Authorization: Bearer <admin_token>
Content-Type: application/json

{
  "target_version": 3,
  "rollback_token": "token_from_version_3",
  "rollback_by": "admin_user",
  "rollback_reason": "Reverting due to increased dispute rate"
}
```

**پاسخ:**
```json
{
  "success": true,
  "rolled_back_from": 5,
  "rolled_back_to": 3,
  "new_version": 6,
  "message": "Successfully rolled back from v5 to v3 (new version: v6)"
}
```

**نکات مهم:**
- Rollback یک نسخه **جدید** ایجاد می‌کند (نه حذف نسخه‌های بعدی)
- `rollback_token` باید با token نسخه هدف تطابق داشته باشد (امنیت)
- تاریخچه کامل حفظ می‌شود
- تغییرات بلافاصله اعمال می‌شوند

**دسترسی:** `config:rollback` (فقط Admin)

---

## 5. اسکریپت Rollback (PowerShell)

اسکریپت `scripts/config_rollback.ps1` برای rollback از خط فرمان فراهم شده است:

**استفاده:**
```powershell
.\config_rollback.ps1 `
  -TargetVersion 3 `
  -RollbackToken "abc123..." `
  -Reason "Reverting due to performance issue"
```

**پارامترها:**
- `-TargetVersion`: شماره نسخه هدف (الزامی)
- `-RollbackToken`: Token rollback نسخه هدف (الزامی)
- `-AdminUsername`: نام کاربری Admin (پیش‌فرض: کاربر جاری Windows)
- `-Reason`: دلیل rollback (الزامی، حداقل 10 کاراکتر)
- `-ApiBase`: آدرس API (پیش‌فرض: http://localhost:8000)

**گزارش:**
- خروجی Console نمایش داده می‌شود
- لاگ کامل در `logs/config_rollback.log` ذخیره می‌شود

---

## 6. Audit Trail و Logging

### 6.1 لاگ رویدادهای تنظیمات

تمام تغییرات و rollbackها در `logs/config_events.json` ثبت می‌شوند:

```json
{
  "event_type": "config_update",
  "version": 5,
  "created_at": "2025-10-24T14:30:00",
  "created_by": "admin_user",
  "change_reason": "Increase bidding deadline",
  "config_hash": "sha256_hash_of_configuration"
}
```

```json
{
  "event_type": "config_rollback",
  "new_version": 6,
  "rolled_back_to": 3,
  "created_at": "2025-10-24T15:00:00",
  "created_by": "admin_user",
  "rollback_reason": "Reverting due to issue",
  "config_hash": "sha256_hash_of_configuration"
}
```

### 6.2 تضمین یکپارچگی (Integrity)

- هر تنظیمات با SHA-256 hash محاسبه و ثبت می‌شود
- Token rollback به صورت `secrets.token_urlsafe(32)` تولید می‌شود
- تاریخچه فقط append-only است (هیچ‌گاه حذف نمی‌شود)

---

## 7. Best Practices

### 7.1 تغییر تنظیمات

1. **همیشه دلیل تغییر را مشخص کنید** (change_reason): برای Audit و troubleshooting آینده ضروری است
2. **تست تنظیمات جدید در محیط Test**: قبل از اعمال در Production
3. **Rollback token را ذخیره کنید**: برای rollback سریع در صورت مشکل
4. **تغییرات عمده را مستند کنید**: در صورتجلسه یا ADR

### 7.2 Rollback

1. **Rollback token را از history دریافت کنید**: `/config/history`
2. **دلیل rollback را مشخص کنید**: برای Audit
3. **تأیید موفقیت rollback**: با دریافت `/config/current`
4. **اعلام به تیم**: در صورت rollback در Production

### 7.3 امنیت

1. **فقط Admin دسترسی به update/rollback دارد**: طبق RBAC policy
2. **Rollback token باید محرمانه بماند**: لیک token امکان rollback غیرمجاز را فراهم می‌کند
3. **Audit logs را مرور کنید**: برای کشف تغییرات غیرمجاز

---

## 8. محدودیت‌ها و ملاحظات

### 8.1 محدودیت‌های فعلی

- **ذخیره‌سازی File-based**: در Stage 23 به DB منتقل می‌شود
- **No Diff Viewer**: نمایش تفاوت بین نسخه‌ها در نسخه‌های بعدی اضافه می‌شود
- **No Approval Workflow**: Approval چند سطحی در نسخه‌های آتی

### 8.2 برنامه آینده

- **Stage 23**: انتقال ذخیره‌سازی به PostgreSQL برای Scalability
- **Stage 24**: UI مدیریت تنظیمات در داشبورد Admin
- **Stage 25**: نمایش Diff بین نسخه‌ها و Approval Workflow

---

## 9. مثال‌های کاربردی

### مثال 1: افزایش مهلت قیمت‌دهی

```bash
# Current: 10 minutes → New: 15 minutes
curl -X POST http://localhost:8000/config/update \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "configuration": {
      "bidding_deadline_minutes": 15,
      "min_valid_quotes": 2,
      ...
    },
    "change_reason": "Increase deadline based on provider feedback",
    "created_by": "admin"
  }'
```

### مثال 2: تغییر ترتیب تسویه

```bash
# Current: fiat_first → New: crypto_first
curl -X POST http://localhost:8000/config/update \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "configuration": {
      ...
      "settlement_order": "crypto_first",
      ...
    },
    "change_reason": "Testing crypto-first settlement order",
    "created_by": "admin"
  }'
```

### مثال 3: Rollback به نسخه قبلی

```powershell
# Via PowerShell script
.\scripts\config_rollback.ps1 `
  -TargetVersion 4 `
  -RollbackToken "token_from_v4" `
  -Reason "Reverting settlement order change due to errors"
```

---

## 10. خلاصه

✅ تنظیمات به صورت نسخه‌دار مدیریت می‌شوند
✅ تغییرات بدون redeploy اعمال می‌شوند
✅ Rollback امن و ممیزی‌پذیر است
✅ History کامل با دلیل و زمان ثبت می‌شود
✅ RBAC از دسترسی غیرمجاز جلوگیری می‌کند

**مسئول مستند:** Codex Agent
**تاریخ آخرین به‌روزرسانی:** 2025-10-24
