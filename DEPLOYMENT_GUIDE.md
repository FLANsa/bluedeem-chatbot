# دليل نشر المشروع - شات بوت بلو ديم

**تاريخ التحديث:** 2024

---

## 🚀 خيارات النشر

### 1. ngrok (للاختبار السريع) - **موصى به للاختبار**

**المميزات:**
- ✅ سريع جداً (دقائق)
- ✅ مجاني
- ✅ رابط مباشر
- ⚠️ الرابط يتغير في كل مرة (ما لم يكن لديك حساب مدفوع)

**الخطوات:**

#### أ. تثبيت ngrok
```bash
# macOS
brew install ngrok

# أو تحميل من: https://ngrok.com/download
```

#### ب. تشغيل المشروع محلياً
```bash
# في مجلد المشروع
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000
```

#### ج. تشغيل ngrok
```bash
# في terminal جديد
ngrok http 8000
```

#### د. الحصول على الرابط
ستحصل على رابط مثل:
```
https://abc123.ngrok.io
```

**الرابط الكامل للواجهة:**
```
https://abc123.ngrok.io/chat/ui
```

---

### 2. Render (للنشر الدائم) - **موصى به للإنتاج**

**المميزات:**
- ✅ مجاني (مع قيود)
- ✅ رابط دائم
- ✅ SSL تلقائي
- ✅ إعادة تشغيل تلقائي

**الخطوات:**

#### أ. إنشاء حساب على Render
1. اذهب إلى: https://render.com
2. سجل حساب جديد (مجاني)

#### ب. إنشاء Web Service
1. اضغط **New** > **Web Service**
2. اربط GitHub repository (أو ارفع الملفات)
3. الإعدادات:
   - **Name:** `bluedeem-chatbot`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free

#### ج. إضافة Environment Variables
في Render Dashboard > Environment:
```env
OPENAI_API_KEY=your_openai_key
GOOGLE_SHEETS_ENABLED=true
GOOGLE_SHEETS_ID=1JJGLZc_LMSNuonZSPC1r_qpcQp2hqCSIIQPld5edEOk
GOOGLE_SHEETS_CREDENTIALS=google-credentials.json
DATABASE_URL=sqlite:///bluedeem.db
```

#### د. رفع ملف Credentials
- ارفع `google-credentials.json` كـ Secret File في Render
- أو استخدم Environment Variable للـ JSON content

#### هـ. النشر
- اضغط **Deploy**
- انتظر حتى يكتمل النشر
- ستحصل على رابط مثل: `https://bluedeem-chatbot.onrender.com`

---

### 3. Railway (بديل سريع)

**المميزات:**
- ✅ مجاني (مع قيود)
- ✅ سهل الإعداد
- ✅ رابط دائم

**الخطوات:**
1. اذهب إلى: https://railway.app
2. سجل حساب جديد
3. **New Project** > **Deploy from GitHub**
4. اختر repository
5. أضف Environment Variables
6. Railway سيكتشف تلقائياً أنه Python project

---

### 4. Fly.io (للإنتاج)

**المميزات:**
- ✅ مجاني (مع قيود)
- ✅ سريع
- ✅ عالمي

**الخطوات:**
1. تثبيت Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. تسجيل الدخول: `fly auth login`
3. إنشاء app: `fly launch`
4. النشر: `fly deploy`

---

## 📋 متطلبات النشر

### 1. ملفات مطلوبة

تأكد من وجود:
- ✅ `requirements.txt`
- ✅ `app.py`
- ✅ `.env` (أو Environment Variables)
- ✅ `google-credentials.json` (أو كـ Secret)

### 2. Environment Variables المطلوبة

```env
# OpenAI
OPENAI_API_KEY=sk-proj-...

# Google Sheets
GOOGLE_SHEETS_ENABLED=true
GOOGLE_SHEETS_ID=1JJGLZc_LMSNuonZSPC1r_qpcQp2hqCSIIQPld5edEOk
GOOGLE_SHEETS_CREDENTIALS=google-credentials.json

# Database
DATABASE_URL=sqlite:///bluedeem.db

# Optional
CACHE_TTL=3600
TIMEZONE=Asia/Riyadh
LOG_LEVEL=INFO
```

### 3. Port Configuration

في `app.py` أو `uvicorn` command:
```python
# يجب استخدام PORT من Environment (للخدمات السحابية)
import os
port = int(os.getenv("PORT", 8000))
```

---

## 🔧 إعدادات إضافية للنشر

### 1. تحديث app.py لدعم PORT

```python
# في app.py
if __name__ == "__main__":
    import uvicorn
    import os
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
```

### 2. إضافة Procfile (لـ Render/Railway)

أنشئ ملف `Procfile`:
```
web: uvicorn app:app --host 0.0.0.0 --port $PORT
```

### 3. إضافة runtime.txt (لـ Render)

أنشئ ملف `runtime.txt`:
```
python-3.9.18
```

---

## 🚨 ملاحظات مهمة

### 1. ملف google-credentials.json

**المشكلة:** معظم خدمات النشر لا تدعم رفع ملفات JSON مباشرة

**الحلول:**

#### أ. استخدام Environment Variable
```python
# في data/sources.py - تعديل ليدعم JSON من Environment
import os
import json

credentials_json = os.getenv("GOOGLE_SHEETS_CREDENTIALS_JSON")
if credentials_json:
    creds = Credentials.from_service_account_info(json.loads(credentials_json))
```

#### ب. رفع كـ Secret File
- في Render: Environment > Secret Files
- في Railway: Variables > Secret Files

#### ج. استخدام Google Cloud Secret Manager
- تخزين Credentials في Google Cloud Secret Manager
- قراءتها من الكود

---

### 2. قاعدة البيانات

**SQLite:** يعمل محلياً لكن قد يكون بطيئاً في الإنتاج

**PostgreSQL (موصى به):**
```env
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

---

### 3. CORS

تأكد من إعداد CORS بشكل صحيح:
```python
# في app.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # في الإنتاج: قائمة محددة
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📝 خطوات سريعة للنشر على Render

### 1. إعداد GitHub Repository
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/username/bluedeem-chatbot.git
git push -u origin main
```

### 2. في Render Dashboard
1. **New** > **Web Service**
2. اختر GitHub repository
3. الإعدادات:
   - **Name:** `bluedeem-chatbot`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
4. **Environment Variables:**
   - أضف جميع المتغيرات من `.env`
5. **Deploy**

### 3. رفع google-credentials.json
- في Render Dashboard > Environment > Secret Files
- ارفع `google-credentials.json`
- أو استخدم Environment Variable `GOOGLE_SHEETS_CREDENTIALS_JSON`

---

## 🔗 الروابط بعد النشر

بعد النشر، ستحصل على:

### الواجهة الرئيسية
```
https://your-app.onrender.com/
```

### واجهة الاختبار
```
https://your-app.onrender.com/chat/ui
```

### API Endpoint
```
https://your-app.onrender.com/chat/api/chat
```

### Health Check
```
https://your-app.onrender.com/health
```

---

## ✅ قائمة التحقق قبل النشر

- [ ] جميع Environment Variables محددة
- [ ] `google-credentials.json` جاهز (أو كـ Secret)
- [ ] `requirements.txt` محدث
- [ ] `Procfile` موجود (لـ Render)
- [ ] CORS مضبوط
- [ ] PORT يستخدم Environment Variable
- [ ] قاعدة البيانات جاهزة
- [ ] Google Sheets API مفعل
- [ ] Google Sheet مشارك مع Service Account

---

## 🆘 استكشاف الأخطاء

### خطأ: "Module not found"
**الحل:** تأكد من `requirements.txt` يحتوي على جميع المكتبات

### خطأ: "Port already in use"
**الحل:** استخدم `$PORT` من Environment Variable

### خطأ: "Google Sheets authentication failed"
**الحل:** تأكد من رفع `google-credentials.json` بشكل صحيح

### خطأ: "Database locked"
**الحل:** استخدم PostgreSQL بدلاً من SQLite في الإنتاج

---

## 📊 مقارنة الخدمات

| الخدمة | السعر | السهولة | الأداء | رابط دائم |
|--------|------|---------|--------|-----------|
| **ngrok** | مجاني | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ |
| **Render** | مجاني | ⭐⭐⭐⭐ | ⭐⭐⭐ | ✅ |
| **Railway** | مجاني | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ |
| **Fly.io** | مجاني | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ |

---

## 🎯 التوصية

**للاختبار السريع:** استخدم **ngrok**  
**للنشر الدائم:** استخدم **Render** أو **Railway**

---

**تم إعداد الدليل بواسطة:** نظام التوثيق الآلي  
**التاريخ:** 2024

