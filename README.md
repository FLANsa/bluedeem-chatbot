# نظام شات بوت بلو ديم

نظام شات بوت ذكي متعدد المنصات لعيادة بلو ديم يستخدم GPT-4.1-mini/nano مع Responses API + Structured Outputs.

## المميزات

- **متعدد المنصات**: دعم WhatsApp, Instagram, TikTok
- **Router Layer**: يقلل استخدام LLM بنسبة 70-90%
- **Structured Outputs**: استخدام Responses API بدلاً من Chat Completions
- **قاعدة بيانات**: SQLite للحجوزات والحالة
- **أمان**: Webhook signature verification, rate limiting, deduplication
- **لهجة نجدية**: ردود بلهجة نجدية مختصرة ومباشرة

## الهيكلة

```
bluedeem-chatbot/
├── app.py                 # FastAPI application
├── config.py             # Configuration
├── core/                 # Core logic (router, intent, agent, booking, formatter)
├── data/                 # Data handling (CSV, database)
├── models/               # Database models and schemas
├── platforms/            # Platform handlers (WhatsApp, Instagram, TikTok)
├── routes/               # API routes
├── middleware/           # Rate limiting, logging, security
├── utils/                # Utilities (phone, date parser)
└── data_samples/         # Sample CSV files
```

## المتطلبات

- Python 3.9+
- OpenAI API key
- (اختياري) Meta WhatsApp API credentials

## التثبيت

1. **استنساخ المشروع**:
```bash
cd "bluedeem AI chatbot"
```

2. **تثبيت المتطلبات**:
```bash
pip install -r requirements.txt
```

3. **إعداد المتغيرات البيئية**:
```bash
cp .env.example .env
# عدّل .env وأضف OPENAI_API_KEY
```

4. **تهيئة قاعدة البيانات**:
```bash
python -c "from data.db import init_db; init_db()"
```

5. **تشغيل الخادم**:
```bash
uvicorn app:app --reload
```

## إعداد Webhooks

### WhatsApp (Meta)

1. في Meta Developer Console، أنشئ WhatsApp Business App
2. أضف webhook URL: `https://your-domain.com/webhook/whatsapp`
3. أضف Verify Token في `.env`: `WHATSAPP_VERIFY_TOKEN`
4. أضف Webhook Secret في `.env`: `WHATSAPP_WEBHOOK_SECRET`

### Instagram & TikTok

(Stub implementations - تحتاج تطوير لاحق)

## ملفات CSV

يجب وضع ملفات CSV في `data_samples/`:

- `01_doctors.csv` - بيانات الأطباء
- `02_branches.csv` - بيانات الفروع
- `03_services.csv` - بيانات الخدمات
- `04_doctor_availability.csv` - توفر الأطباء

## API Endpoints

### Health Checks

- `GET /health` - Health check أساسي
- `GET /health/data` - فحص تحميل البيانات
- `GET /health/db` - فحص قاعدة البيانات

### Webhooks

- `GET /webhook/whatsapp` - WhatsApp webhook verification
- `POST /webhook/whatsapp` - WhatsApp webhook handler
- `POST /webhook/instagram` - Instagram webhook handler
- `POST /webhook/tiktok` - TikTok webhook handler

## التدفق

1. **استقبال الرسالة**: Platform handler يستقبل webhook
2. **Deduplication**: فحص إذا كانت الرسالة معالجة مسبقاً
3. **Rate Limiting**: فحص حد الرسائل (10/دقيقة)
4. **Router**: تصنيف النية + استخراج الكيانات
5. **القرار**:
   - بيانات كافية → Formatter مباشرة (70-90%)
   - ناقص شيء → سؤال توضيحي
   - سؤال معقد → LLM (gpt-4.1-mini)
6. **إرسال الرد**: Platform handler يرسل الرسالة

## الحجز (Booking)

عملية الحجز تستخدم state machine:

1. **name** - جمع الاسم
2. **phone** - جمع رقم الجوال (مع validation)
3. **service** - اختيار الخدمة
4. **branch** - اختيار الفرع (اختياري)
5. **date_time** - اختيار التاريخ والوقت (اختياري)
6. **done** - إنشاء التذكرة وحفظها في قاعدة البيانات

## منطق "موجود اليوم؟"

- يبحث في `04_doctor_availability.csv` عن (date, doctor_id)
- إذا وجد: يعرض `available` + `note`
- إذا لم يوجد: يعرض جدول الدوام من `doctors` بدون ادعاء "موجود اليوم"

## الأمان

- ✅ Webhook signature verification (Meta)
- ✅ Rate limiting (10 messages/minute per user)
- ✅ Message deduplication
- ✅ Structured logging
- ✅ Error handling with retries

## التطوير

### إضافة منصة جديدة

1. أنشئ handler في `platforms/` يرث من `PlatformHandler`
2. أضف route في `routes/webhook.py`
3. اختبر webhook parsing و message sending

### إضافة نية جديدة

1. أضف النية في `core/intent.py` (system prompt)
2. أضف معالجة في `core/router.py`
3. أضف template في `core/formatter.py` إذا لزم

## الاختبار

```bash
# Test health endpoints
curl http://localhost:8000/health

# Test webhook (example)
curl -X POST http://localhost:8000/webhook/whatsapp \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"123","text":{"body":"مرحبا"}}]}}]}]}'
```

## الترخيص

خاص بمشروع بلو ديم

