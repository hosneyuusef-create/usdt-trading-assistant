# Dispute Workflow – Stage 18

## هدف
تعریف گردش کامل رسیدگی به اختلافات از زمان ثبت تا صدور رأی نهایی، با رعایت SLAهای زمانی، اصل Non-custodial و قابلیت ممیزی کامل.

## مخاطبان
- **طرفین اختلاف:** مشتری (Claimant) و پرووایدر (Respondent)
- **ادمین/داور:** مسئول بررسی مدارک و صدور رأی
- **سیستم:** مسئول اعمال SLA، ثبت رویدادها و Escalation خودکار

## اصول کلیدی
1. **Non-custodial Principle:** سیستم فقط هش و متادیتای مدارک را ذخیره می‌کند؛ فایل‌های اصلی نزد طرفین باقی می‌ماند.
2. **SLA سخت‌گیرانه:** رعایت مهلت‌های 30 دقیقه، 60 دقیقه و 4 ساعت الزامی است.
3. **Audit Trail کامل:** تمام اقدامات با actor، زمان، دلیل و ارجاع به مدارک ثبت می‌شود.
4. **Transparency:** طرفین در تمام مراحل از وضعیت و مهلت‌ها مطلع می‌شوند.

## SLA Timeline

```
Time: 0min              +30min              +90min              +240min (4hr)
      │                 │                   │                   │
      ▼                 ▼                   ▼                   ▼
   [File Dispute]   [Evidence      [Review           [Final Decision
                     Deadline]       Deadline]         Deadline]
      │                 │                   │                   │
      │◄────────────────┤                   │                   │
      │  Evidence       │                   │                   │
      │  Submission     │                   │                   │
      │  Window         │                   │                   │
      │                 │◄──────────────────┤                   │
      │                 │  Admin Review     │                   │
      │                 │  Window           │                   │
      │                 │                   │◄──────────────────┤
      │                 │                   │  Extended Window  │
      │                 │                   │  (if needed)      │
```

### مهلت‌های زمانی:
1. **Evidence Submission:** 30 دقیقه از زمان ثبت اختلاف
2. **Review Window:** 60 دقیقه (30-90 دقیقه از ثبت)
3. **Final Decision:** حداکثر 4 ساعت از زمان ثبت اختلاف

## وضعیت‌های Dispute

| وضعیت | شرح | مهلت فعال | مجاز برای |
|-------|-----|-----------|-----------|
| `open` | اختلاف ثبت شده، منتظر درخواست مدارک | - | System |
| `awaiting_evidence` | درخواست مدارک ارسال شده | Evidence Deadline | Customer, Provider |
| `under_review` | بررسی توسط ادمین | Review/Decision Deadline | Admin |
| `resolved` | رأی صادر شده | - | - |
| `escalated` | Escalate به سطح بالاتر | - | Admin |

## Transition Diagram

```
[Settlement Escalation] ──┐
                          │
                          ▼
                      ┌────────┐
                      │  open  │
                      └────┬───┘
                           │ file_dispute()
                           ▼
                  ┌─────────────────────┐
                  │ awaiting_evidence   │◄────┐
                  └─────────┬───────────┘     │
                            │                  │
              ┌─────────────┼─────────────┐   │
              │ submit_evidence() (30min)  │   │
              └─────────────┼─────────────┘   │
                            │                  │
                            ▼                  │
                    ┌──────────────┐           │
                    │ under_review │           │
                    └──────┬───────┘           │
                           │                   │
            ┌──────────────┼──────────────┐   │
            │  make_decision() (≤4hr)      │   │
            └──────────────┼──────────────┘   │
                           │                   │
                ┌──────────┴──────────┐        │
                │                     │        │
                ▼                     ▼        │
         ┌──────────┐          ┌───────────┐  │
         │ resolved │          │ escalated │──┘
         └──────────┘          └───────────┘
```

## گردش کامل (Step-by-Step)

### مرحله 1: ثبت اختلاف (Dispute Filing)
**Actor:** Customer یا Provider (طرف مدعی)
**Endpoint:** `POST /dispute/file`

**ورودی:**
```json
{
  "settlement_id": "abc123...",
  "claimant_telegram_id": 123456789,
  "reason": "پرداخت ریالی انجام شد اما USDT دریافت نشد. رسید بانکی شماره 7891011 به تاریخ 2025-10-24 ساعت 14:30 موجود است."
}
```

**خروجی:**
- Dispute ID تخصیص داده می‌شود
- وضعیت: `open` → `awaiting_evidence`
- مهلت‌ها محاسبه می‌شود:
  - Evidence Deadline: now + 30min
  - Review Deadline: now + 90min
  - Decision Deadline: now + 4hr
- **Action Log:** `request_evidence` ثبت می‌شود
- **Notification:** هر دو طرف اعلان دریافت می‌کنند:
  > «اختلاف #D8291 ثبت شد. لطفاً مستندات خود را ظرف 30 دقیقه (تا 15:00) ارسال کنید.»

**Audit Log:**
```json
{
  "event": "dispute_filed",
  "dispute_id": "d8291abc...",
  "settlement_id": "abc123...",
  "claimant_telegram_id": 123456789,
  "respondent_telegram_id": 987654321,
  "reason": "...",
  "evidence_deadline": "2025-10-24T15:00:00Z",
  "review_deadline": "2025-10-24T15:30:00Z",
  "decision_deadline": "2025-10-24T18:30:00Z",
  "timestamp": "2025-10-24T14:30:00Z"
}
```

---

### مرحله 2: ارسال مدارک (Evidence Submission)
**Actor:** Customer و Provider (هر دو طرف)
**Endpoint:** `POST /dispute/evidence`
**مهلت:** 30 دقیقه از ثبت اختلاف

**ورودی (نمونه):**
```json
{
  "dispute_id": "d8291abc...",
  "submitter_telegram_id": 123456789,
  "evidence_type": "bank_receipt",
  "storage_url": "file://evidence/receipt_7891011.pdf",
  "hash": "5e88489d1b2c8a3f7c9d4e6f8a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b",
  "metadata": {
    "receipt_number": "7891011",
    "bank": "Bank Melli",
    "amount": "2050000",
    "date": "2025-10-24",
    "time": "14:30"
  },
  "notes": "رسید بانکی اصل ضمیمه است. مبلغ 2,050,000 تومان به کارت ****1234 واریز شده."
}
```

**خروجی:**
- Evidence ID تخصیص می‌شود
- فقط hash و metadata ذخیره می‌شود (Non-custodial)
- Evidence count افزایش می‌یابد

**Validation:**
- `evidence_type` در مقادیر مجاز: `bank_receipt | tx_proof | screenshot | other`
- `hash` حداقل 16 کاراکتر
- زمان ارسال ≤ Evidence Deadline

**Audit Log:**
```json
{
  "event": "evidence_submitted",
  "evidence_id": "e4567def...",
  "dispute_id": "d8291abc...",
  "submitter_telegram_id": 123456789,
  "evidence_type": "bank_receipt",
  "hash": "5e88489d1b2c8a3f...",
  "timestamp": "2025-10-24T14:45:00Z"
}
```

---

### مرحله 3: شروع بررسی (Review Start)
**Actor:** Admin
**Endpoint:** `POST /dispute/review/{dispute_id}`
**مهلت:** بین Evidence Deadline و Review Deadline (30-90 دقیقه از ثبت)

**ورودی:**
```json
{
  "admin_telegram_id": 555555555
}
```

**خروجی:**
- وضعیت: `awaiting_evidence` → `under_review`
- **Action Log:** `review_start` ثبت می‌شود
- Evidence count در نوت ثبت می‌شود

**Validation:**
- زمان فعلی ≥ Evidence Deadline
- زمان فعلی ≤ Review Deadline
- وضعیت فعلی: `awaiting_evidence`

**Audit Log:**
```json
{
  "action_id": "a9876ghi...",
  "dispute_id": "d8291abc...",
  "admin_telegram_id": 555555555,
  "action_type": "review_start",
  "evidence_count": 3,
  "timestamp": "2025-10-24T15:05:00Z"
}
```

---

### مرحله 4: صدور رأی (Decision)
**Actor:** Admin
**Endpoint:** `POST /dispute/decision`
**مهلت:** ≤4 ساعت از ثبت اختلاف

**ورودی:**
```json
{
  "dispute_id": "d8291abc...",
  "admin_telegram_id": 555555555,
  "decision": "favor_claimant",
  "decision_reason": "بر اساس بررسی مدارک:\n1. رسید بانکی #7891011 با مبلغ 2,050,000 تومان تأیید شد.\n2. TxID ارائه‌شده توسط پرووایدر معتبر نیست (تراکنش یافت نشد).\n3. نتیجه: پرداخت ریالی انجام شده اما USDT دریافت نشده.\nرأی: به نفع مشتری. پرووایدر موظف به انتقال فوری USDT یا بازپرداخت ریال است.",
  "awarded_to_claimant": "2000.00",
  "evidence_reviewed": ["e4567def...", "e8901jkl..."]
}
```

**Decision Values:**
- `favor_claimant`: به نفع مدعی
- `favor_respondent`: به نفع خوانده
- `partial_favor`: تقسیم میان طرفین
- `inconclusive`: نامعلوم، نیاز به Escalation

**خروجی:**
- وضعیت: `under_review` → `resolved`
- decision و decision_reason ثبت می‌شود
- decision_at ثبت می‌شود
- **Action Log:** `decision` ثبت می‌شود
- **Notification:** هر دو طرف اعلان دریافت می‌کنند:
  > «رأی نهایی #D8291 صادر شد. به نفع: مشتری. دلیل: [خلاصه]. جزئیات کامل در پنل قابل مشاهده است.»

**Validation:**
- زمان فعلی ≤ Decision Deadline (4hr)
- وضعیت فعلی: `under_review` یا `awaiting_evidence`
- `decision_reason` حداقل 20 کاراکتر

**Audit Log:**
```json
{
  "event": "decision_made",
  "dispute_id": "d8291abc...",
  "admin_telegram_id": 555555555,
  "decision": "favor_claimant",
  "decision_reason": "...",
  "awarded_to_claimant": "2000.00",
  "evidence_reviewed": ["e4567def...", "e8901jkl..."],
  "timestamp": "2025-10-24T16:00:00Z"
}
```

---

### مرحله 5: Escalation (اختیاری)
**Actor:** Admin
**Endpoint:** `POST /dispute/escalate/{dispute_id}`
**شرایط:** SLA Breach یا نیاز به تصمیم سطح بالاتر

**ورودی:**
```json
{
  "admin_telegram_id": 555555555,
  "reason": "SLA breach: Decision deadline passed (4hr). Escalating to senior arbitrator."
}
```

**خروجی:**
- وضعیت: → `escalated`
- **Action Log:** `escalate` ثبت می‌شود
- **Notification:** مدیر ارشد اعلان دریافت می‌کند

**Audit Log:**
```json
{
  "action_id": "a5432mno...",
  "dispute_id": "d8291abc...",
  "admin_telegram_id": 555555555,
  "action_type": "escalate",
  "reason": "SLA breach: Decision deadline passed...",
  "timestamp": "2025-10-24T19:00:00Z"
}
```

---

## مدیریت SLA

### 1. Evidence Deadline (30 دقیقه)
- **Trigger:** زمان ثبت اختلاف
- **اقدام خودکار:** پس از 30 دقیقه، submission بسته می‌شود
- **Consequence:** هر طرفی که مدرک ارسال نکرده باشد، موقعیت ضعیف‌تری در داوری دارد
- **Notification:** 5 دقیقه قبل از پایان مهلت، یادآوری ارسال می‌شود

### 2. Review Deadline (90 دقیقه)
- **Trigger:** 30 دقیقه پس از Evidence Deadline
- **اقدام دستی:** ادمین باید review را شروع کند
- **Consequence:** اگر ادمین review نکند، dispute قابل Escalation است

### 3. Decision Deadline (4 ساعت)
- **Trigger:** زمان ثبت اختلاف
- **اقدام دستی:** ادمین باید رأی صادر کند
- **Consequence:** breach این SLA باعث Escalation خودکار می‌شود
- **Notification:** 30 دقیقه قبل از پایان مهلت، هشدار به ادمین ارسال می‌شود

---

## نوع مدارک قابل قبول

| نوع | Evidence Type | توضیحات | فیلدهای Metadata |
|-----|---------------|----------|------------------|
| رسید بانکی | `bank_receipt` | رسید کاغذی یا الکترونیک | receipt_number، bank، amount، date، time |
| اثبات تراکنش کریپتو | `tx_proof` | TxID و اسکرین‌شات از explorer | tx_id، network، confirmations، explorer_url |
| اسکرین‌شات | `screenshot` | تصویر زمان‌دار از صفحه/اپلیکیشن | timestamp، app_name، description |
| سایر | `other` | هر مدرک دیگری | free-form metadata |

### الزامات فنی:
- **حجم:** حداکثر 5 MB (مطابق Evidence_Spec.md)
- **Hash:** SHA-256، حداقل 16 کاراکتر hex
- **Storage:** فقط URL و hash در سیستم ذخیره می‌شود
- **Retention:** 180 روز (مطابق Evidence_Spec.md)

---

## نقش‌ها و دسترسی‌ها (RBAC)

| Endpoint | Customer | Provider | Admin | توضیح |
|----------|----------|----------|-------|-------|
| `POST /dispute/file` | ✅ | ✅ | ✅ | ثبت اختلاف (Claimant) |
| `POST /dispute/evidence` | ✅ | ✅ | ❌ | ارسال مدارک |
| `POST /dispute/review/{id}` | ❌ | ❌ | ✅ | شروع بررسی |
| `POST /dispute/decision` | ❌ | ❌ | ✅ | صدور رأی |
| `POST /dispute/escalate/{id}` | ❌ | ❌ | ✅ | Escalation |
| `GET /dispute/{id}` | ✅* | ✅* | ✅ | مشاهده جزئیات (*فقط dispute خودشان) |
| `GET /dispute/` | ❌ | ❌ | ✅ | لیست همه disputes |
| `GET /dispute/{id}/evidence` | ❌ | ❌ | ✅ | مشاهده مدارک |

---

## لاگ‌ها و Audit Trail

### 1. Dispute Events (`logs/dispute_events.json`)
رویدادهای اصلی: `dispute_filed`، `evidence_submitted`، `decision_made`

### 2. Dispute Actions (`logs/dispute_action_events.json`)
اقدامات ادمین: `request_evidence`، `review_start`، `decision`، `escalate`

### الزامات Audit:
- **Immutability:** رویدادها قابل ویرایش نیستند (append-only)
- **Traceability:** هر رویداد شامل actor، timestamp، dispute_id، reason
- **Evidence Reference:** تصمیم‌ها شامل لیست evidence_id های بررسی‌شده
- **PII Minimization:** فقط Telegram ID ذخیره می‌شود، نه اطلاعات شخصی

---

## Integration با Settlement (Stage 16)

### Escalation از Settlement به Dispute:
```python
# در settlement/service.py
if evidence_invalid or deadline_passed:
    _log(DISPUTE_LOG, {
        "event": "escalation_from_settlement",
        "settlement_id": settlement_id,
        "reason": "Evidence rejected or deadline passed",
        "timestamp": _now().isoformat()
    })
    # فراخوانی dispute.file_dispute()
```

### Settlement Status Update پس از Decision:
```python
# پس از decision در dispute
if decision == "favor_claimant":
    settlement.status = "disputed_resolved_claimant"
elif decision == "favor_respondent":
    settlement.status = "disputed_resolved_respondent"
```

---

## مثال سناریوی کامل

### Context:
- **Settlement ID:** S12345
- **مشتری (Claimant):** TG_ID=111222333
- **پرووایدر (Respondent):** TG_ID=444555666
- **ادمین:** TG_ID=999888777

### Timeline:

**14:30 (T+0min)** – مشتری اختلاف را ثبت می‌کند:
```
POST /dispute/file
{
  "settlement_id": "S12345",
  "claimant_telegram_id": 111222333,
  "reason": "پرداخت ریالی انجام شد اما USDT دریافت نشد."
}
→ Dispute ID: D98765
→ Evidence Deadline: 15:00
→ Decision Deadline: 18:30
```

**14:35 (T+5min)** – مشتری مدرک ارسال می‌کند:
```
POST /dispute/evidence
{
  "dispute_id": "D98765",
  "submitter_telegram_id": 111222333,
  "evidence_type": "bank_receipt",
  "hash": "abc123...",
  ...
}
→ Evidence ID: E11111
```

**14:50 (T+20min)** – پرووایدر مدرک ارسال می‌کند:
```
POST /dispute/evidence
{
  "dispute_id": "D98765",
  "submitter_telegram_id": 444555666,
  "evidence_type": "tx_proof",
  "hash": "def456...",
  ...
}
→ Evidence ID: E22222
```

**15:00 (T+30min)** – Evidence Deadline می‌رسد (خودکار)
- وضعیت همچنان: `awaiting_evidence`

**15:05 (T+35min)** – ادمین بررسی را شروع می‌کند:
```
POST /dispute/review/D98765
{
  "admin_telegram_id": 999888777
}
→ Status: under_review
```

**16:00 (T+90min)** – ادمین رأی صادر می‌کند:
```
POST /dispute/decision
{
  "dispute_id": "D98765",
  "admin_telegram_id": 999888777,
  "decision": "favor_claimant",
  "decision_reason": "رسید بانکی معتبر است. TxID پرووایدر یافت نشد.",
  "evidence_reviewed": ["E11111", "E22222"]
}
→ Status: resolved
→ Decision at: 16:00 (1.5hr از ثبت، زیر 4hr SLA)
```

**نتیجه:** اختلاف به نفع مشتری حل شد. SLA رعایت شد (1.5hr < 4hr).

---

## Exception Handling

### 1. SLA Breach
- **Evidence Deadline Missed:** طرف بدون مدرک موقعیت ضعیف دارد اما dispute ادامه می‌یابد
- **Review Deadline Missed:** dispute قابل Escalation است
- **Decision Deadline Missed:** Escalation خودکار

### 2. Invalid Evidence
- **Hash Missing/Invalid:** رد می‌شود
- **File Size > 5MB:** رد می‌شود (مطابق Evidence_Spec)
- **Evidence Type Unknown:** رد می‌شود

### 3. Unauthorized Access
- **Customer/Provider مشاهده dispute دیگران:** 403 Forbidden
- **Customer/Provider اقدام Admin:** 403 Forbidden

### 4. Dispute Not Found
- **GET/POST به dispute نامعتبر:** 404 Not Found

---

## Maintenance و به‌روزرسانی

### تغییر SLA:
1. به‌روزرسانی ثوابت در `dispute/service.py`:
   ```python
   evidence_deadline: datetime = field(default_factory=lambda: _now() + timedelta(minutes=30))
   ```
2. به‌روزرسانی این سند (Dispute_Workflow.md)
3. ثبت Assumption در `artefacts/assumptions_log.md`
4. اطلاع‌رسانی به کاربران

### تغییر Evidence Types:
1. به‌روزرسانی `evidence_type` در `schemas.py`
2. به‌روزرسانی validation در `service.py`
3. به‌روزرسانی جدول «نوع مدارک» در این سند

---

## Testing

### Test Cases:
- **M18-E2E-1:** ثبت اختلاف و ارسال مدارک در بازه مجاز
- **M18-E2E-2:** رد مدرک خارج از مهلت (Evidence Deadline)
- **M18-E2E-3:** صدور رأی موفق در بازه SLA
- **M18-E2E-4:** Escalation در صورت breach Decision Deadline

### Test Evidence:
- `artefacts/test_reports/M18_dispute_tests.md`
- `tests/test_dispute.py`

---

## مراجع
- **Stage 18 marahel:** [marahel_utf8.txt:310-325](../marahel_utf8.txt)
- **Requirement:** [RTM M01-REQ-011](RTM_v1.1.csv)
- **dastoor بخش 11:** [dastoor_utf8.txt:64-67](../dastoor_utf8.txt)
- **Evidence Spec:** [Evidence_Spec.md](Evidence_Spec.md)
- **Settlement Service:** [src/backend/settlement/service.py](../src/backend/settlement/service.py)
- **Workflow Statecharts:** [Workflow_Statecharts.pdf](Workflow_Statecharts.pdf)

---

**نسخه:** v1.0
**تاریخ:** 2025-10-24
**مسئول:** Stage 18 Implementation Team
**وضعیت:** Approved for Production
