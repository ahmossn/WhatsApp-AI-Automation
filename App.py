import os
from flask import Flask, request
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

# شحن المتغيرات البيئية من ملف .env محلياً
load_dotenv()

app = Flask(__name__)

# 1. تحديد هيكل استجابة الذكاء الاصطناعي (تحليل نية العميل)
class AIResponseSchema(BaseModel):
    reply_message: str = Field(description="الرد المناسب والودي على رسالة العميل باللغة العربية.")
    intent: str = Field(description="تصنيف نية العميل: (سؤال_عن_منتج، شكوى، طلب_شراء، تحية، غير_ذلك)")
    lead_score: int = Field(description="تقييم مدى جدية العميل لشراء منتج من 1 إلى 5.")

# إعداد عميل Gemini API
# تأكد من تعيين GEMINI_API_KEY في البيئة المحيطة بك
gemini_client = genai.Client()

@app.route("/webhook", methods=['POST'])
def whatsapp_webhook():
    # 2. استقبال الرسالة والرقم من واتساب (عبر Twilio API)
    incoming_msg = request.values.get('Body', '').strip()
    sender_number = request.values.get('From', '')
    
    print(f"📩 رسالة جديدة من {sender_number}: {incoming_msg}")

    # 3. صياغة التعليمات لـ Gemini ليقوم بدور موظف خدمة العملاء الذكي
    system_instruction = """
    أنت موظف خدمة عملاء ذكي ومحترف لمتجر إلكتروني عربي. 
    مهمتك هي الرد على استفسارات العملاء بلباقة ومساعدتهم، مع تصنيف نوع الرسالة وتحديد مدى جديتهم في الشراء.
    اجعل الردود قصيرة ومناسبة لتطبيق واتساب.
    """

    try:
        # استدعاء نموذج Gemini للحصول على رد مهيكل (Structured Output)
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"رسالة العميل: {incoming_msg}",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=AIResponseSchema,
                temperature=0.3,
            ),
        )
        
        # تحليل البيانات القادمة من الذكاء الاصطناعي
        ai_data = AIResponseSchema.model_validate_json(response.text)
        
        # طباعة التحليلات في الـ Terminal (يمكنك حفظها في قاعدة بيانات لاحقاً)
        print(f"🤖 تصنيف النية: {ai_data.intent} | درجة الجدية: {ai_data.lead_score}/5")
        final_reply = ai_data.reply_message

    except Exception as e:
        print(f"❌ خطأ في معالجة الذكاء الاصطناعي: {e}")
        final_reply = "عذراً، واجهت مشكلة في فهم الرسالة حالياً. سيتواصل معك موظف بشري قريباً."

    # 4. إرسال الرد التلقائي إلى واتساب
    twilio_response = MessagingResponse()
    twilio_response.message(final_reply)
    
    return str(twilio_response)

if __name__ == "__main__":
    # تشغيل السيرفر على منفذ 5000
    app.run(port=5000, debug=True)
