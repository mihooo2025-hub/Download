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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "ضع_التوكن_هنا_إن_لم_تستخدم_Environment_Variables")
bot = telebot.TeleBot(BOT_TOKEN)

# مسار ملف الكوكيز المرفوع في Secret Files على Render
COOKIE_PATH = '/etc/secrets/Download'
if not os.path.exists(COOKIE_PATH):
    COOKIE_PATH = '/etc/secrets/download'
    if not os.path.exists(COOKIE_PATH):
        COOKIE_PATH = 'Download'

# إعدادات yt-dlp المتطورة لتجاوز حجب IP الخوادم
YDL_OPTS = {
    'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
    'quiet': True,
    'no_warnings': True,
    'outtmpl': '%(title)s.%(ext)s',
    'cookiefile': COOKIE_PATH if os.path.exists(COOKIE_PATH) else None,
    # استخدام مشغلات الأجهزة الذكية (TV/VR) لتفادي كشف السيرفرات السحابية
    'extractor_args': {
        'youtube': {
            'player_client': ['tv', 'android_vr', 'ios', 'mweb'],
            'player_skip': ['webpage', 'configs'],
        }
    },
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (SmartHub; SMART-TV; U; Linux/SmartTV) AppleWebKit/537.42 (KHTML, like Gecko) Safari/537.42',
        'Accept-Language': 'en-US,en;q=0.9',
    }
}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "مرحباً بك! أرسل لي رابط الفيديو وسأقوم بتحميله لك.")

@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text.strip()
    
    if not (url.startswith("http://") or url.startswith("https://")):
        return

    msg = bot.reply_to(message, "⏳ جاري التحميل، يرجى الانتظار...")
    
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
        # حذف الفيديو بعد الإرسال لتوفير المساحة على السيرفر
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.start()
    bot.polling(non_stop=True)
