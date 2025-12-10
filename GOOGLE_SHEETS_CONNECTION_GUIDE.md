# دليل الربط مع Google Sheets - شات بوت بلو ديم

**تاريخ التحديث:** 2024

---

## 📋 نظرة عامة

النظام يستخدم Google Sheets كمصدر رئيسي للبيانات. يتطلب الربط:
1. **Service Account** من Google Cloud
2. **Spreadsheet ID** من Google Sheets
3. **مشاركة Sheet مع Service Account**
4. **إعداد متغيرات البيئة (.env)**

---

## 🔧 البيانات المطلوبة للربط

### 1. متغيرات البيئة (.env)

أضف هذه المتغيرات في ملف `.env`:

```env
# تفعيل Google Sheets
GOOGLE_SHEETS_ENABLED=true

# Spreadsheet ID (من رابط Google Sheet)
GOOGLE_SHEETS_ID=1JJGLZc_LMSNuonZSPC1r_qpcQp2hqCSIIQPld5edEOk

# مسار ملف Credentials (Service Account JSON)
GOOGLE_SHEETS_CREDENTIALS=google-credentials.json

# أسماء الـ Sheets (اختياري - القيم الافتراضية)
GOOGLE_SHEETS_DOCTORS_SHEET=01_doctors
GOOGLE_SHEETS_BRANCHES_SHEET=02_branches
GOOGLE_SHEETS_SERVICES_SHEET=03_services
GOOGLE_SHEETS_AVAILABILITY_SHEET=04_doctor_availability
```

---

## 📊 البيانات الحالية

### Spreadsheet ID
```
1JJGLZc_LMSNuonZSPC1r_qpcQp2hqCSIIQPld5edEOk
```

**الرابط الكامل:**
```
https://docs.google.com/spreadsheets/d/1JJGLZc_LMSNuonZSPC1r_qpcQp2hqCSIIQPld5edEOk/edit
```

---

### Service Account Email
```
bluedeem-chatbot@coral-hydra-456017-a0.iam.gserviceaccount.com
```

---

### ملف Credentials
**الاسم:** `google-credentials.json`  
**الموقع:** في مجلد المشروع الرئيسي

**محتوى الملف:**
```json
{
  "type": "service_account",
  "project_id": "coral-hydra-456017-a0",
  "private_key_id": "2d40a1fe13d63ab92dc45e6a0c97bb7e8a968aa3",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "bluedeem-chatbot@coral-hydra-456017-a0.iam.gserviceaccount.com",
  "client_id": "118289175276791328552",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/bluedeem-chatbot%40coral-hydra-456017-a0.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}
```

---

## 📁 هيكل Google Sheets المطلوب

يجب أن يحتوي Google Sheet على **4 Sheets** بالأسماء التالية:

### 1. Sheet: `01_doctors`
**الأعمدة المطلوبة:**
```
doctor_id, doctor_name, specialty, branch_id, days, time_from, time_to, 
phone, email, experience_years, qualifications, notes
```

### 2. Sheet: `02_branches`
**الأعمدة المطلوبة:**
```
branch_id, branch_name, address, city, phone, email, hours_weekdays, 
hours_weekend, maps_url, features, parking, accessibility
```

### 3. Sheet: `03_services`
**الأعمدة المطلوبة:**
```
service_id, service_name, specialty, description, price_sar, price_range, 
available_branch_ids, duration_minutes, preparation_required, popular
```

### 4. Sheet: `04_doctor_availability`
**الأعمدة المطلوبة:**
```
date, doctor_id, branch_id, available, note, last_updated
```

---

## 🔐 خطوات الإعداد

### الخطوة 1: إنشاء Service Account

1. اذهب إلى [Google Cloud Console](https://console.cloud.google.com/)
2. اختر المشروع: `coral-hydra-456017-a0`
3. اذهب إلى **IAM & Admin** > **Service Accounts**
4. اختر Service Account: `bluedeem-chatbot@coral-hydra-456017-a0.iam.gserviceaccount.com`
5. تأكد من وجود ملف `google-credentials.json` في المشروع

---

### الخطوة 2: تفعيل Google Sheets API

1. اذهب إلى [Google Cloud Console](https://console.cloud.google.com/)
2. اختر المشروع: `coral-hydra-456017-a0`
3. اذهب إلى **APIs & Services** > **Library**
4. ابحث عن "Google Sheets API"
5. اضغط **Enable**

---

### الخطوة 3: مشاركة Google Sheet مع Service Account

1. افتح Google Sheet:
   ```
   https://docs.google.com/spreadsheets/d/1JJGLZc_LMSNuonZSPC1r_qpcQp2hqCSIIQPld5edEOk/edit
   ```

2. اضغط على زر **Share** (مشاركة)

3. أضف Service Account Email:
   ```
   bluedeem-chatbot@coral-hydra-456017-a0.iam.gserviceaccount.com
   ```

4. اختر الصلاحية: **Editor** (محرر)

5. اضغط **Send**

---

### الخطوة 4: إعداد ملف .env

أنشئ ملف `.env` في مجلد المشروع:

```env
# Google Sheets Configuration
GOOGLE_SHEETS_ENABLED=true
GOOGLE_SHEETS_ID=1JJGLZc_LMSNuonZSPC1r_qpcQp2hqCSIIQPld5edEOk
GOOGLE_SHEETS_CREDENTIALS=google-credentials.json
```

---

## ✅ التحقق من الربط

### اختبار الاتصال

```python
# في Python shell
from data.handler import data_handler

# محاولة قراءة البيانات
doctors = data_handler.get_doctors()
print(f"عدد الأطباء: {len(doctors)}")

branches = data_handler.get_branches()
print(f"عدد الفروع: {len(branches)}")

services = data_handler.get_services()
print(f"عدد الخدمات: {len(services)}")
```

---

## 🔍 استكشاف الأخطاء

### خطأ: "Google Sheets is not enabled"
**الحل:**
- تأكد من `GOOGLE_SHEETS_ENABLED=true` في `.env`

---

### خطأ: "Failed to authenticate with Google Sheets"
**الحل:**
- تأكد من وجود ملف `google-credentials.json`
- تأكد من صحة مسار الملف في `GOOGLE_SHEETS_CREDENTIALS`
- تأكد من صحة محتوى ملف JSON

---

### خطأ: "Permission denied" أو "Access denied"
**الحل:**
- تأكد من مشاركة Google Sheet مع Service Account
- Service Account Email: `bluedeem-chatbot@coral-hydra-456017-a0.iam.gserviceaccount.com`
- تأكد من الصلاحية: **Editor**

---

### خطأ: "Google Sheets API has not been used"
**الحل:**
- تأكد من تفعيل Google Sheets API في Google Cloud Console
- اذهب إلى **APIs & Services** > **Library** > **Google Sheets API** > **Enable**

---

### خطأ: "Missing columns in doctors"
**الحل:**
- تأكد من وجود جميع الأعمدة المطلوبة في Sheet `01_doctors`
- تأكد من أن الصف الأول يحتوي على Headers (الأسماء)

---

## 📝 ملاحظات مهمة

1. **Cache:** البيانات يتم تخزينها مؤقتاً (Cache) لمدة ساعة (3600 ثانية)
   - يمكن تغييرها عبر `CACHE_TTL` في `.env`

2. **أسماء Sheets:** يمكن تغيير أسماء Sheets عبر متغيرات البيئة:
   ```env
   GOOGLE_SHEETS_DOCTORS_SHEET=01_doctors
   GOOGLE_SHEETS_BRANCHES_SHEET=02_branches
   GOOGLE_SHEETS_SERVICES_SHEET=03_services
   GOOGLE_SHEETS_AVAILABILITY_SHEET=04_doctor_availability
   ```

3. **مسار Credentials:** يمكن استخدام مسار مطلق أو نسبي:
   ```env
   # مسار نسبي (من مجلد المشروع)
   GOOGLE_SHEETS_CREDENTIALS=google-credentials.json
   
   # مسار مطلق
   GOOGLE_SHEETS_CREDENTIALS=/path/to/google-credentials.json
   ```

---

## 🔗 روابط مفيدة

- **Google Cloud Console:** https://console.cloud.google.com/
- **Google Sheets API:** https://developers.google.com/sheets/api
- **Service Accounts:** https://cloud.google.com/iam/docs/service-accounts

---

## 📊 ملخص البيانات

| المتغير | القيمة |
|---------|--------|
| **Spreadsheet ID** | `1JJGLZc_LMSNuonZSPC1r_qpcQp2hqCSIIQPld5edEOk` |
| **Service Account Email** | `bluedeem-chatbot@coral-hydra-456017-a0.iam.gserviceaccount.com` |
| **Credentials File** | `google-credentials.json` |
| **Project ID** | `coral-hydra-456017-a0` |
| **Sheet: Doctors** | `01_doctors` |
| **Sheet: Branches** | `02_branches` |
| **Sheet: Services** | `03_services` |
| **Sheet: Availability** | `04_doctor_availability` |

---

**تم إعداد الدليل بواسطة:** نظام التوثيق الآلي  
**التاريخ:** 2024

