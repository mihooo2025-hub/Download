import os
import logging
from threading import Thread
from flask import Flask
import telebot
from yt_dlp import YoutubeDL

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running fine!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "ضع_التوكن_هنا")
bot = telebot.TeleBot(BOT_TOKEN)

# البحث الآلي عن ملف الكوكيز بغض النظر عن حالة الأحرف أو الامتداد
def get_cookie_path():
    possible_paths = [
        '/etc/secrets/Download',
        '/etc/secrets/download',
        '/etc/secrets/Download.txt',
        '/etc/secrets/download.txt',
        '/etc/secrets/cookies.txt',
        'Download',
        'download'
    ]
    for path in possible_paths:
        if os.path.exists(path):
            logging.info(f"✅ FOUND COOKIE FILE AT: {path}")
            return path
    logging.warning("⚠️ NO COOKIE FILE FOUND IN /etc/secrets/")
    return None

COOKIE_PATH = get_cookie_path()

# إعدادات yt-dlp
YDL_OPTS = {
    'format': 'best',
    'quiet': True,
    'no_warnings': True,
    'outtmpl': '%(title)s.%(ext)s',
    'cookiefile': COOKIE_PATH,
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'ios', 'web'],
        }
    },
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
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
        # إعادة فحص الملف قبل كل عملية تحميل للتأكد
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
    t.start()
    bot.polling(non_stop=True)
