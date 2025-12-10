# دليل النشر السريع - شات بوت بلو ديم

## 🚀 الطريقة السريعة: ngrok (للاختبار)

### الخطوة 1: تثبيت ngrok
```bash
# macOS
brew install ngrok

# أو من الموقع: https://ngrok.com/download
```

### الخطوة 2: تشغيل المشروع
```bash
cd "/Users/manaf/Desktop/bluedeem AI chatbot "
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000
```

### الخطوة 3: تشغيل ngrok (في terminal جديد)
```bash
ngrok http 8000
```

### الخطوة 4: الحصول على الرابط
ستحصل على رابط مثل:
```
Forwarding  https://abc123.ngrok.io -> http://localhost:8000
```

**الرابط للواجهة:**
```
https://abc123.ngrok.io/chat/ui
```

---

## 🌐 الطريقة الدائمة: Render

### الخطوة 1: إنشاء حساب
1. اذهب إلى: https://render.com
2. سجل حساب جديد (مجاني)

### الخطوة 2: رفع المشروع على GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/username/bluedeem-chatbot.git
git push -u origin main
```

### الخطوة 3: إنشاء Web Service في Render
1. **New** > **Web Service**
2. اختر GitHub repository
3. الإعدادات:
   - **Name:** `bluedeem-chatbot`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free

### الخطوة 4: إضافة Environment Variables
في Render Dashboard > Environment:
```env
OPENAI_API_KEY=your_key_here
GOOGLE_SHEETS_ENABLED=true
GOOGLE_SHEETS_ID=1JJGLZc_LMSNuonZSPC1r_qpcQp2hqCSIIQPld5edEOk
GOOGLE_SHEETS_CREDENTIALS=google-credentials.json
DATABASE_URL=sqlite:///bluedeem.db
```

### الخطوة 5: رفع google-credentials.json
- في Render Dashboard > Environment > Secret Files
- ارفع `google-credentials.json`

### الخطوة 6: Deploy
- اضغط **Deploy**
- انتظر حتى يكتمل
- ستحصل على رابط: `https://bluedeem-chatbot.onrender.com`

---

## 📋 ملفات جاهزة للنشر

✅ `Procfile` - جاهز  
✅ `runtime.txt` - جاهز  
✅ `requirements.txt` - جاهز  
✅ `app.py` - محدث لدعم PORT

---

## 🔗 الروابط بعد النشر

- **الواجهة:** `https://your-app.onrender.com/chat/ui`
- **API:** `https://your-app.onrender.com/chat/api/chat`
- **Health:** `https://your-app.onrender.com/health`

---

## ⚡ نصيحة سريعة

**للاختبار السريع:** استخدم **ngrok** (5 دقائق)  
**للنشر الدائم:** استخدم **Render** (15 دقيقة)

