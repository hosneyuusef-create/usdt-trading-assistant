# Repository Structure

| مسیر | توضیح |
|------|-------|
| `dastoor.txt` | سند الزامات و دستور کارفرما. |
| `marahel.txt` | نقشه راه مراحل با خروجی‌ها، معیارها و بخش Assumptions هر مرحله. |
| `global_playbook.md` | Playbook مدیریتی که در آغاز و پایان هر مرحله باید خوانده شود. |
| `artefacts/` | محل ذخیره خروجی‌های رسمی (RTM، گزارش‌ها، ویدئوها، فرم‌ها). |
| `artefacts/assumptions_log.md` | لاگ مرکزی فرضیات (شناسه، مرحله، اثر، وضعیت). |
| `artefacts/RTM_v*.csv` یا `artefacts/RTM_v*.xlsx` | ماتریس ردیابی الزامات به‌روز مرحله 1. |
| `artefacts/stage_completion_checklist.md` | فرم کنترل پایان مرحله. |
| `artefacts/templates/` | تمپلیت‌های استاندارد (ADR، گزارش تست، خلاصه مرحله). |
| `artefacts/Training_Kit.zip` | خروجی آموزش مرحله 24. |
| `artefacts/test_reports/` | گزارش‌های تست واحد، یکپارچه، E2E و پوشش کد. |
| `artefacts/message_templates/` | قالب‌های پیام و هشدارهای مرحله 19. |
| `artefacts/Telemetry_Config.json` | تنظیمات شاخص‌های تلمتری. |
| `artefacts/Config_Versioning.md` | راهبرد نسخه‌گذاری تنظیمات. |
| `artefacts/Prod_Deployment.md` | Runbook استقرار Production (مرحله 25). |
| `artefacts/final_delivery_checklist.md` | فرم تحویل نهایی پروژه و وضعیت Artefactهای اصلی. |
| `docs/environment_recovery_guide.md` | راهنمای بازیابی محیط در صورت خرابی یا شکست. |
| `docs/change_control_and_revert.md` | سیاست کنترل تغییر و بازگشت به نسخه سالم. |
| `docs/git_setup_guide.md` | دستورالعمل آماده‌سازی مخزن Git، ایجاد شاخه‌ها و تگ‌های baseline. |
| `db/schema/` و `db/migrations/` | شمای دیتابیس و Migrationها. |
| `scripts/setup/` | اسکریپت‌های Zero-to-Dev و Rollback. |
| `scripts/tests/` | اسکریپت‌های اجرای تست (واحد، یکپارچه، E2E). |
| `tests/` | تست‌های واحد، یکپارچه و E2E. |
| `tests/README.md` | راهنمای اجرای تست‌ها، پیش‌نیازها و مسیر خروجی‌ها. |
| `src/backend/` | کد منبع سرویس‌ها. |
| `ci/github-actions.yml` | خط لوله CI برای اجرای خودکار تست‌ها و جمع‌آوری Artefactها. |
