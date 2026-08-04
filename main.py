import os
import time
import shutil
import logging
from threading import Thread
from flask import Flask
import telebot
from yt_dlp import YoutubeDL

# إعداد التسجيل (Logging)
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running fine!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("❌ BOT_TOKEN environment variable is missing!")

bot = telebot.TeleBot(BOT_TOKEN)

def get_cookie_path():
    possible_paths = [
        '/etc/secrets/Download',
        '/etc/secrets/download',
        '/etc/secrets/Download.txt',
        'Download',
        'download'
    ]
    for path in possible_paths:
        if os.path.exists(path):
            tmp_cookie_path = '/tmp/Download'
            try:
                shutil.copy(path, tmp_cookie_path)
                logging.info(f"✅ COPIED COOKIE FILE FROM {path} TO {tmp_cookie_path}")
                return tmp_cookie_path
            except Exception as e:
                logging.error(f"Failed to copy cookie file: {e}")
                return path
                
    logging.warning("⚠️ NO COOKIE FILE FOUND IN /etc/secrets/")
    return None

COOKIE_PATH = get_cookie_path()

# خيارات سحرية تتجاوز حظر يوتيوب ولا تتطلب ffmpeg نهائياً
YDL_OPTS = {
    # طلب ملف سينجل مدمج من الأصل (فيديو + صوت) أو أحدث صيغة متاحة للموبايل
    'format': 'best[vcodec!=none][acodec!=none]/best',
    'quiet': True,
    'no_warnings': True,
    'noplaylist': True,
    'outtmpl': '%(title)s.%(ext)s',
    'cookiefile': COOKIE_PATH,
    # خداع يوتيوب بأن الطلب قادم من تطبيق iOS أو TV لتجاوز حظر IP السيرفرات
    'extractor_args': {
        'youtube': {
            'player_client': ['ios', 'android', 'mweb'],
            'skip': ['hls', 'dash'] # تخطي الصيغ المقسمة التي تحتاج ffmpeg
        }
    },
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
    }
}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    logging.info(f"Received start command from {message.from_user.id}")
    bot.reply_to(message, "مرحباً بك! البوت يعمل الآن وجاهز لتحميل الفيديوهات. أرسل رابط الفيديو:")

@bot.message_handler(func=lambda message: True)
def download_video(message):
    url = message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return

    logging.info(f"Processing URL: {url}")
    msg = bot.reply_to(message, "⏳ جاري التحميل، يرجى الانتظار...")
    
    file_path = None
    try:
        current_cookie = get_cookie_path()
        opts = YDL_OPTS.copy()
        opts['cookiefile'] = current_cookie

        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)
            
        with open(file_path, 'rb') as video:
            bot.send_video(message.chat.id, video, caption=info.get('title', ''))
            
        bot.delete_message(message.chat.id, msg.message_id)

    except Exception as e:
        logging.error(f"Error downloading video: {e}")
        bot.edit_message_text(f"❌ حدث خطأ أثناء التحميل:\n`{str(e)}`", message.chat.id, msg.message_id, parse_mode="Markdown")
        
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    while True:
        try:
            try:
                bot.remove_webhook()
            except Exception:
                pass

            logging.info("🤖 Bot polling started successfully...")
            
            bot.polling(
                non_stop=True, 
                skip_pending=True, 
                timeout=90, 
                long_polling_timeout=90
            )

        except Exception as e:
            logging.error(f"⚠️ Polling error occurred: {e}")
            logging.info("🔄 Reconnecting in 5 seconds...")
            time.sleep(5)
