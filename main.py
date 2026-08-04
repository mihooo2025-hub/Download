import os
import logging
from threading import Thread
from flask import Flask
import telebot
from yt_dlp import YoutubeDL

# إعداد التسجيل (Logging)
logging.basicConfig(level=logging.INFO)

# إنشاء تطبيق Flask لإبقاء السيرفر نشطاً على Render
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running fine!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# توكن البوت الخاص بك
BOT_TOKEN = os.environ.get("BOT_TOKEN", "ضع_التوكن_هنا_إن_لم_تستخدم_متغيرات_البيئة")
bot = telebot.TeleBot(BOT_TOKEN)

# تحديد مسار ملف الكوكيز باسم Download كما هو محدد في Render
COOKIE_PATH = '/etc/secrets/Download'
if not os.path.exists(COOKIE_PATH):
    # محاولة مطابقة الاسم بالحروف الصغيرة في حال وجود اختلاف بالحالة
    COOKIE_PATH = '/etc/secrets/download'
    if not os.path.exists(COOKIE_PATH):
        COOKIE_PATH = 'Download' # للمحيط المحلي

# إعدادات yt-dlp المتطورة
YDL_OPTS = {
    'format': 'best',
    'quiet': True,
    'no_warnings': True,
    'outtmpl': '%(title)s.%(ext)s',
    'cookiefile': COOKIE_PATH if os.path.exists(COOKIE_PATH) else None,
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web'],
        }
    },
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36',
    }
}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً بك! أرسل لي رابط فيديو من يوتيوب، إنستغرام، أو تيك توك وسأقوم بتحميله لك.")

@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text.strip()
    
    if not (url.startswith("http://") or url.startswith("https://")):
        return

    msg = bot.reply_to(message, "⏳ جاري جلب الفيديو والتحميل...")
    
    file_path = None
    try:
        with YoutubeDL(YDL_OPTS) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
        with open(file_path, 'rb') as video:
            bot.send_video(message.chat.id, video, caption=info.get('title', ''))
            
        bot.delete_message(message.chat.id, msg.message_id)

    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        bot.edit_message_text(f"❌ حدث خطأ أثناء التحميل:\n`{str(e)}`", message.chat.id, msg.message_id, parse_mode="Markdown")
        
    finally:
        # حذف الفيديو بعد الإرسال لتوفير المساحة
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    # تشغيل Flask في Thread منفصل
    t = Thread(target=run_flask)
    t.start()
    
    # تشغيل البوت
    bot.polling(non_stop=True)
