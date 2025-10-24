# Customer Registration Tests – Stage 10

- تاریخ: 2025-10-23
- فرمان: `python -m pytest tests/test_customer_registration.py`
- نتیجه: Passed
- نکات:
  - ماسکینگ کارت (`masked_card`) بررسی شد (نمایش فقط چهار رقم آخر).
  - سقف‌های KYC بر اساس `artefacts/Verification_Policies.json` اعمال شد (Advanced = 10,000,000).
  - درخواست تکراری همان مشتری، همان شناسه را بازمی‌گرداند (idempotent).
  - سطح ناشناخته منجر به پیام خطای 400 می‌شود.
