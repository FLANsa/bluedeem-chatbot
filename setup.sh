#!/bin/bash

echo "🚀 إعداد مشروع شات بوت بلو ديم..."
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 غير مثبت"
    exit 1
fi

echo "✅ Python موجود: $(python3 --version)"

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 إنشاء ملف .env..."
    cp .env.example .env
    echo "⚠️  يرجى تعديل ملف .env وإضافة OPENAI_API_KEY"
else
    echo "✅ ملف .env موجود"
fi

# Check OPENAI_API_KEY
if grep -q "OPENAI_API_KEY=sk-" .env 2>/dev/null; then
    echo "✅ OPENAI_API_KEY موجود في .env"
else
    echo "⚠️  OPENAI_API_KEY غير موجود - يرجى إضافته في .env"
fi

# Install dependencies
echo ""
echo "📦 تثبيت المتطلبات..."
pip3 install -r requirements.txt

# Initialize database
echo ""
echo "🗄️  تهيئة قاعدة البيانات..."
python3 -c "from data.db import init_db; init_db()" 2>/dev/null

if [ -f bluedeem.db ]; then
    echo "✅ قاعدة البيانات جاهزة"
else
    echo "⚠️  قاعدة البيانات لم يتم إنشاؤها"
fi

# Check CSV files
echo ""
echo "📄 التحقق من ملفات CSV..."
if [ -f data_samples/01_doctors.csv ] && [ -f data_samples/02_branches.csv ] && [ -f data_samples/03_services.csv ] && [ -f data_samples/04_doctor_availability.csv ]; then
    echo "✅ جميع ملفات CSV موجودة"
else
    echo "⚠️  بعض ملفات CSV مفقودة"
fi

echo ""
echo "✨ الإعداد مكتمل!"
echo ""
echo "لتشغيل المشروع:"
echo "  uvicorn app:app --reload"
echo ""
echo "لفتح الواجهة:"
echo "  http://localhost:8000/chat/ui"
echo ""

