# Domain Glossary – Stage 4 (v1.0)

| اصطلاح | تعریف | فیلدهای کلیدی | روابط اصلی |
|---------|--------|---------------|-------------|
| Customer | کاربر تایید شده تلگرام که درخواست خرید/فروش را ثبت می‌کند؛ شامل سطح KYC و حساب‌های پرداخت | `customer_id`, `kyc_tier`, `wallet_alias` | 1:N با RFQ، 1:N با Dispute (claimant) |
| Provider | تأمین‌کننده نقدینگی با وثیقه و امتیاز عملکرد | `provider_id`, `score`, `collateral_amount` | 1:N با Quote، 1:N با ProviderScoreSnapshot، 1:N با Dispute (respondent) |
| AdminUser | عضو تیم عملیات با نقش RBAC | `admin_id`, `role`, `last_login_at` | 1:N با DisputeAction، 1:N با ConfigVersion |
| RFQ | درخواست خرید/فروش با جزئیات شبکه، مقدار و مهلت پاسخ | `rfq_id`, `type`, `network`, `amount`, `expiry_at` | N:1 با Customer، 1:N با Quote، 1:N با Award |
| Quote | پاسخ ارائه‌شده توسط Provider با قیمت و ظرفیت | `quote_id`, `rfq_id`, `provider_id`, `unit_price`, `capacity`, `fee` | N:1 با Provider و RFQ، 1:N با SettlementLeg |
| Award | نتیجه انتخاب برنده برای یک RFQ | `award_id`, `rfq_id`, `quote_id`, `selection_mode`, `awarded_amount` | N:1 با RFQ و Quote، 1:N با Settlement |
| Settlement | شیء ترکیبی برای ثبت پیشرفت تسویه ریالی/کریپتو | `settlement_id`, `award_id`, `status`, `sla_deadline` | N:1 با Award، 1:N با SettlementLeg و Evidence |
| SettlementLeg | نمایانگر یک پا از تسویه (Fiat یا USDT) | `settlement_leg_id`, `settlement_id`, `leg_type`, `amount`, `status` | N:1 با Settlement، N:1 با Quote |
| Evidence | مدارک اثبات (رسید، هش تراکنش) | `evidence_id`, `source`, `reference_id`, `hash`, `submitted_at` | N:1 با Settlement یا Dispute |
| Dispute | پرونده اختلاف شامل طرفین، دلایل و رأی | `dispute_id`, `settlement_id`, `claimant_id`, `respondent_id`, `status`, `decision_at` | N:1 با Settlement، Customer، Provider |
| DisputeAction | رویدادهای پیگیری و تصمیمات در پرونده اختلاف | `action_id`, `dispute_id`, `actor_type`, `notes`, `action_at` | N:1 با Dispute، N:1 با AdminUser |
| NotificationTemplate | الگوهای پیام نسخه‌دار جهت اعلان‌ها | `template_id`, `channel`, `version`, `body` | 1:N با NotificationEvent |
| NotificationEvent | پیام ارسال یا در صف با وضعیت تحویل | `event_id`, `template_id`, `related_type`, `related_id`, `status`, `attempts` | N:1 با Template، N:1 با Award/Settlement/Dispute |
| ConfigVersion | عکس لحظه‌ای از تنظیمات سیستم (SLA، شبکه‌ها، ترتیب تسویه) | `config_id`, `applied_at`, `json_payload`, `approved_by` | N:1 با AdminUser، مرتبط با RFQ/Settlement |
| ProviderScoreSnapshot | وضعیت روزانه امتیاز و وثیقه Provider | `snapshot_id`, `provider_id`, `score`, `collateral_balance`, `captured_at` | N:1 با Provider |

> تمام موجودیت‌ها باید فیلدهای `created_at`, `updated_at`, `created_by`, `updated_by` برای پشتیبانی تاریخچه تغییرات داشته باشند. |
