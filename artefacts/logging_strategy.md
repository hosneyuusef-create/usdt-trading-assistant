# Logging and Audit Trail Strategy — Stage 23 (M23)

**تاریخ:** 2025-10-24
**نسخه:** v1.0
**مسئول:** Codex Agent

---

## 1. مرور کلی (Overview)

این سند استراتژی Logging و Audit Trail سامانه را تعریف می‌کند. تمام رویدادهای کسب‌وکار به صورت ساختاریافته، immutable و قابل ردیابی ثبت می‌شوند تا:
- **Audit Trail کامل:** بازپخش کامل سناریوهای خرید/فروش از روی لاگ‌ها
- **Compliance:** رعایت الزامات ممیزی و قابلیت اثبات تصمیمات
- **Debugging:** ردیابی مشکلات و خطاها با Trace ID
- **Analytics:** استخراج متریک‌ها و گزارش‌ها از رویدادها

---

## 2. معماری Logging

### 2.1 Unified Event Schema

تمام رویدادها باید مطابق schema تعریف شده در `artefacts/event_schema_spec.json` ثبت شوند.

**فیلدهای الزامی:**
- `event_id` (UUID): شناسه یکتای رویداد
- `event_type`: نوع رویداد (rfq_created, award_selected_auto, ...)
- `actor_id`: شناسه کسی که عمل را انجام داد
- `actor_role`: نقش (customer, provider, admin, system)
- `trace_id` (UUID): شناسه مسیر کامل معامله
- `created_at`: زمان ثبت (ISO 8601 UTC)
- `event_hash`: SHA-256 hash برای immutability

**فیلدهای اختیاری:**
- `previous_status`: وضعیت قبلی (برای state transition)
- `new_status`: وضعیت جدید
- `decision_reason`: دلیل تصمیم
- `evidence_links[]`: لینک‌های مدارک
- `metadata`: اطلاعات اختصاصی رویداد

### 2.2 Immutability و Event Sourcing

**قوانین Immutability:**
1. رویدادها **هرگز** حذف یا تغییر نمی‌شوند
2. هر اصلاح نیازمند یک **Compensating Event** است
   - مثال: برای لغو RFQ → رویداد `rfq_cancelled` ثبت شود
3. Hash رویداد برای تأیید یکپارچگی محاسبه می‌شود:
   ```
   event_hash = SHA256(event_id + event_type + actor_id + trace_id + created_at + JSON(metadata))
   ```

### 2.3 Trace ID Strategy

**یک Trace ID برای کل چرخه حیات RFQ:**
```
trace_id = UUID  # تولید شده هنگام RFQ creation
```

**تمام رویدادهای مرتبط همان trace_id را دارند:**
- rfq_created
- quote_submitted (همه quotes)
- award_selected
- settlement_started
- settlement_completed / dispute_opened
- dispute_resolved

**Query سناریو کامل:**
```sql
SELECT * FROM audit_events
WHERE trace_id = '7c3a4f21-1234-5678-9abc-def012345678'
ORDER BY created_at ASC;
```

---

## 3. ساختار ذخیره‌سازی

### 3.1 File Format

**JSON Lines (`.jsonl`):**
- یک رویداد در هر خط
- هر خط یک JSON object معتبر
- مناسب برای streaming و log rotation

**مثال (`logs/audit_events.json`):**
```json
{"event_id":"550e8400-e29b-41d4-a716-446655440000","event_type":"rfq_created","actor_id":"telegram:123456","actor_role":"customer","trace_id":"7c3a4f21-1234-5678-9abc-def012345678","created_at":"2025-10-24T12:00:00+00:00","event_hash":"a1b2c3...","metadata":{"rfq_id":"uuid","rfq_type":"buy","amount":100.0}}
{"event_id":"661f9511-f3ac-52e5-b827-557766551111","event_type":"quote_submitted","actor_id":"telegram:789012","actor_role":"provider","trace_id":"7c3a4f21-1234-5678-9abc-def012345678","created_at":"2025-10-24T12:05:00+00:00","event_hash":"d4e5f6...","metadata":{"quote_id":"uuid","rfq_id":"uuid","unit_price":82400.0}}
```

### 3.2 Log Rotation

**استراتژی:**
- **Daily Rotation:** هر روز فایل جدید
- **Naming:** `logs/audit_events_YYYY-MM-DD.json`
- **Retention:** حداقل 90 روز (compliance)
- **Archive:** بعد از 90 روز به cold storage منتقل شود

**پیاده‌سازی:**
```python
from datetime import datetime

def get_audit_log_path():
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return f"logs/audit_events_{today}.json"
```

---

## 4. نحوه ثبت رویدادها

### 4.1 Audit Module API

**ماژول:** `src/backend/audit/service.py`

```python
from src.backend.audit.service import log_event

# ثبت رویداد
log_event(
    event_type="rfq_created",
    actor_id="telegram:123456",
    actor_role="customer",
    trace_id="7c3a4f21-1234-5678-9abc-def012345678",
    metadata={
        "rfq_id": "uuid",
        "rfq_type": "buy",
        "amount": 100.0,
        "network": "TRC20"
    }
)
```

### 4.2 State Transition Events

برای رویدادهایی که state را تغییر می‌دهند:

```python
log_event(
    event_type="settlement_completed",
    actor_id="system:auto_verifier",
    actor_role="system",
    trace_id="7c3a4f21-1234-5678-9abc-def012345678",
    previous_status="pending_crypto",
    new_status="completed",
    decision_reason="Blockchain confirmation received",
    metadata={
        "settlement_id": "uuid",
        "completion_time_minutes": 12
    }
)
```

---

## 5. Event Replay و Audit Trail

### 5.1 بازپخش سناریو خرید

**هدف:** بازسازی کامل یک RFQ از روی لاگ‌ها

**الگوریتم:**
```python
def replay_rfq_scenario(trace_id: str):
    """
    Replay all events for a specific RFQ trace.
    Returns timeline of all state changes.
    """
    events = load_events_by_trace_id(trace_id)

    timeline = []
    current_state = {"status": "draft"}

    for event in sorted(events, key=lambda e: e["created_at"]):
        if "new_status" in event:
            current_state["status"] = event["new_status"]

        timeline.append({
            "timestamp": event["created_at"],
            "event_type": event["event_type"],
            "actor": f"{event['actor_role']}:{event['actor_id']}",
            "state_after": current_state.copy(),
            "decision_reason": event.get("decision_reason", "")
        })

    return timeline
```

**مثال خروجی:**
```
Timeline for trace_id: 7c3a4f21...
[12:00] rfq_created by customer:123456 → status: open
[12:05] quote_submitted by provider:789012 → status: open
[12:06] quote_submitted by provider:345678 → status: open
[12:11] award_selected_auto by system:auto_engine → status: awarded
        (Decision: Auto-selection based on lowest effective price)
[12:15] settlement_started by system:settlement_engine → status: pending_fiat
[12:20] settlement_fiat_submitted by customer:123456 → status: pending_crypto
[12:25] settlement_crypto_submitted by provider:789012 → status: verifying
[12:28] settlement_completed by system:auto_verifier → status: completed
```

### 5.2 Dispute Investigation

برای بررسی اختلاف:

```python
def investigate_dispute(trace_id: str):
    """
    Extract all evidence and decisions for dispute analysis.
    """
    events = load_events_by_trace_id(trace_id)

    evidence = []
    decisions = []

    for event in events:
        if "evidence" in event.get("event_type", ""):
            evidence.append({
                "timestamp": event["created_at"],
                "party": event["actor_role"],
                "evidence_links": event.get("evidence_links", [])
            })

        if event.get("decision_reason"):
            decisions.append({
                "timestamp": event["created_at"],
                "actor": event["actor_id"],
                "decision": event["decision_reason"]
            })

    return {"evidence": evidence, "decisions": decisions}
```

---

## 6. PII Minimization

**هدف:** محافظت از اطلاعات شخصی کاربران مطابق GDPR و بهترین شیوه‌ها

### 6.1 قوانین

| داده | ذخیره شود | ذخیره نشود |
|------|-----------|-------------|
| **شناسه کاربر** | `telegram_id` ✅ | شماره تلفن ❌ |
| **شماره کارت** | `6037-99**-****-1234` ✅ | شماره کامل ❌ |
| **آدرس کیف‌پول** | Hash آدرس (اگر لازم نباشد) ✅ | آدرس کامل در لاگ‌های عمومی ❌ |
| **نام واقعی** | ❌ | فقط در DB کاربران، **نه** در logs |

### 6.2 مثال

**نادرست:**
```json
{
  "event_type": "settlement_fiat_submitted",
  "actor_id": "phone:+989121234567",
  "metadata": {
    "card_number": "6037997012345678",
    "customer_name": "علی احمدی"
  }
}
```

**صحیح:**
```json
{
  "event_type": "settlement_fiat_submitted",
  "actor_id": "telegram:123456",
  "metadata": {
    "card_number_masked": "6037-99**-****-5678",
    "evidence_hash": "sha256:abc123..."
  }
}
```

---

## 7. یکپارچه‌سازی با Telemetry

### 7.1 ارتباط با Telemetry Config

لاگ‌ها منبع داده برای متریک‌های تلمتری تعریف شده در `artefacts/Telemetry_Config.json` هستند:

| Metric | منبع Log | محاسبه |
|--------|----------|---------|
| `notification_latency_p95_ms` | `logs/notification_events.json` | p95(notification_sent_at - notification_created_at) |
| `notification_failure_rate` | `logs/notification_events.json` | count(status=failed) / count(total) |
| `dispute_escalation_rate` | `logs/audit_events.json` | count(event_type=dispute_opened) / count(event_type=settlement_started) |

### 7.2 Dashboard و Alerting

**Query برای p95 Latency:**
```python
def calculate_notification_p95():
    events = load_events(event_type="notification_sent", last_15_minutes=True)
    latencies = [e["metadata"]["latency_ms"] for e in events]
    return numpy.percentile(latencies, 95)
```

**Alert Trigger:**
```python
p95 = calculate_notification_p95()
if p95 > TELEMETRY_CONFIG["notification_latency_p95_ms"]["critical"]:
    send_alert("CRITICAL: Notification latency p95 exceeded 8000ms")
elif p95 > TELEMETRY_CONFIG["notification_latency_p95_ms"]["warning"]:
    send_alert("WARNING: Notification latency p95 exceeded 5000ms")
```

---

## 8. Query Patterns

### 8.1 Event Stream Query

**همه رویدادهای یک کاربر:**
```python
def get_user_events(actor_id: str, limit=100):
    return query_events(
        filter={"actor_id": actor_id},
        order_by="created_at DESC",
        limit=limit
    )
```

**رویدادهای یک نوع خاص:**
```python
def get_dispute_events(start_date, end_date):
    return query_events(
        filter={
            "event_type": {"$in": ["dispute_opened", "dispute_evidence_submitted", "dispute_resolved"]},
            "created_at": {"$gte": start_date, "$lte": end_date}
        }
    )
```

### 8.2 Aggregation

**تعداد RFQهای ساخته شده امروز:**
```python
def count_rfqs_today():
    today = datetime.utcnow().date()
    return count_events(
        filter={
            "event_type": "rfq_created",
            "created_at": {"$gte": today}
        }
    )
```

**نرخ موفقیت تسویه:**
```python
def settlement_success_rate():
    total = count_events(event_type="settlement_started")
    completed = count_events(event_type="settlement_completed")
    return completed / total if total > 0 else 0
```

---

## 9. Hash Verification

### 9.1 محاسبه Hash

```python
import hashlib
import json

def compute_event_hash(event: dict) -> str:
    """
    Compute SHA-256 hash of event for immutability verification.
    """
    # فقط فیلدهای کلیدی
    hash_input = (
        event["event_id"] +
        event["event_type"] +
        event["actor_id"] +
        event["trace_id"] +
        event["created_at"] +
        json.dumps(event.get("metadata", {}), sort_keys=True)
    )
    return hashlib.sha256(hash_input.encode()).hexdigest()
```

### 9.2 تأیید Integrity

```python
def verify_event_integrity(event: dict) -> bool:
    """
    Verify that event has not been tampered with.
    """
    stored_hash = event.get("event_hash")
    if not stored_hash:
        return False

    # حذف hash از event و محاسبه مجدد
    event_copy = event.copy()
    event_copy.pop("event_hash", None)

    computed_hash = compute_event_hash(event_copy)
    return computed_hash == stored_hash
```

---

## 10. Migration از لاگ‌های قدیمی

### 10.1 لاگ‌های موجود

لاگ‌های فعلی در فرمت‌های مختلف:
- `logs/award_events.json`
- `logs/quote_events.json`
- `logs/config_events.json`
- `logs/scoring_events.json`
- `logs/access_audit.json`

### 10.2 استراتژی Migration

**گام 1:** نگهداری لاگ‌های قدیمی (backward compatibility)
**گام 2:** همزمان ثبت در فرمت جدید (`logs/audit_events.json`)
**گام 3:** بعد از ۹۰ روز، migration کامل به فرمت جدید

**مثال Migration Script:**
```python
def migrate_award_events():
    """
    Migrate old award_events.json to new unified format.
    """
    old_events = load_json_lines("logs/award_events.json")

    for old_event in old_events:
        new_event = {
            "event_id": str(uuid.uuid4()),
            "event_type": "award_selected_auto" if old_event["selection_mode"] == "auto" else "award_selected_manual",
            "actor_id": f"system:{old_event['approver']}",
            "actor_role": "system" if old_event["selection_mode"] == "auto" else "admin",
            "trace_id": old_event["rfq_id"],  # استفاده از rfq_id به عنوان trace_id
            "created_at": old_event["timestamp"],
            "metadata": {
                "award_id": old_event["award_id"],
                "rfq_id": old_event["rfq_id"],
                "winning_quotes": [leg["quote_id"] for leg in old_event["legs"]],
                "tie_break_rule": old_event["tie_break_rule"]
            }
        }
        new_event["event_hash"] = compute_event_hash(new_event)

        append_to_audit_log(new_event)
```

---

## 11. Best Practices

### 11.1 ثبت رویدادها

✅ **انجام دهید:**
- همیشه trace_id را propagate کنید
- decision_reason را برای تصمیمات کلیدی ثبت کنید
- Hash را برای هر رویداد محاسبه کنید
- PII را Mask کنید

❌ **انجام ندهید:**
- رویدادها را حذف یا Edit نکنید
- اطلاعات حساس (password، token) را Log نکنید
- شماره تلفن یا نام واقعی کاربر را ثبت نکنید

### 11.2 Query و Performance

- برای query سریع از index روی `trace_id` و `event_type` استفاده کنید
- برای تحلیل‌های سنگین از batch processing استفاده کنید
- لاگ‌های قدیمی را به cold storage منتقل کنید

---

## 12. خلاصه

✅ **Schema واحد** برای تمام رویدادها (`event_schema_spec.json`)
✅ **Immutability** با Hash و Append-only log
✅ **Trace ID** برای ردیابی کامل مسیر معامله
✅ **Event Replay** برای بازپخش سناریوهای خرید/اختلاف
✅ **PII Minimization** برای محافظت از حریم خصوصی
✅ **Telemetry Integration** برای مانیتورینگ و alerting

**مسئول مستند:** Codex Agent
**تاریخ آخرین به‌روزرسانی:** 2025-10-24
