# Git Setup Guide (Baseline & Branching Strategy)

این راهنما توضیح می‌دهد چگونه مخزن گیت پروژه را مطابق Playbook آماده کنید تا ایجنت‌ها بتوانند شاخه‌ها، تگ‌ها و Commitهای لازم را بسازند.

## 1. ایجاد مخزن محلی
```bash
git init
git add .
git commit -m "baseline: initial project structure"
```

## 2. تنظیم ریموت (در صورت وجود)
```bash
git remote add origin <REMOTE_URL>
git push -u origin main
```

## 3. برچسب پایه
پس از اولین Commit و هر زمان که خروجی مرحله‌ای نهایی شد:
```bash
git tag baseline/M01/2025-10-22
git push origin baseline/M01/2025-10-22
```
*نام تگ را بر اساس Stage-ID و تاریخ واقعی تنظیم کنید.*

## 4. شاخه‌های کاری
برای هر مرحله یا تغییر مستقل:
```bash
git checkout -b feature/M13/rfq-special-conditions
```
پس از کدنویسی، تست و تکمیل چک‌لیست مرحله:
```bash
git add .
git commit -m "M13: implement RFQ special conditions validation"
git checkout main
git merge feature/M13/rfq-special-conditions
git push origin main
```

## 5. بازگشت به نسخه سالم
در صورت نیاز به بازگردانی یا بازیابی:
```bash
git checkout main
git reset --hard baseline/M13/2025-10-22
git push --force-with-lease origin main
```
*این عملیات باید با هماهنگی مدیر پروژه انجام شود (به سند `docs/change_control_and_revert.md` مراجعه کنید).*

## 6. چک‌لیست نهایی قبل از تحویل
- شاخه کاری تمیز (`git status` بدون تغییر)  
- تمامی تگ‌های baseline در ریموت  
- فرم‌های `artefacts/stage_completion_checklist.md` و `artefacts/final_delivery_checklist.md` تکمیل شده  
- RTM (`artefacts/RTM_v*.csv`) به‌روز شده و Commit شده است
