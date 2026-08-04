import os
import time
import shutil
import logging
import imageio_ffmpeg
from threading import Thread
from flask import Flask
import telebot
from yt_dlp import YoutubeDL

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

def get_cookie_path():
    possible_paths = ['/etc/secrets/Download', '/etc/secrets/download', 'Download']
    for path in possible_paths:
        if os.path.exists(path):
            tmp_path = '/tmp/Download'
            try:
                shutil.copy(path, tmp_path)
                return tmp_path
            except Exception:
                return path
    return None

try:
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_PATH = None

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "أرسل رابط الفيديو من (يوتيوب، تيك توك، إنستغرام) وسيتم تحميله فوراً.")

@bot.message_handler(func=lambda message: True)
def download(message):
    url = message.text.strip()
    if not url.startswith("http"):
        return

    msg = bot.reply_to(message, "⏳ جاري التحميل...")
    
    cookie_file = get_cookie_path()
    
    opts = {
        'format': 'b/best', # يجلب صيغة جاهزة مدمجة لتفادي مشاكل الدمج
        'outtmpl': '/tmp/%(id)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'cookiefile': cookie_file,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios']
            }
        }
    }
    
    if FFMPEG_PATH:
        opts['ffmpeg_location'] = FFMPEG_PATH

    file_path = None
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        with open(file_path, 'rb') as video:
            bot.send_video(message.chat.id, video, caption=info.get('title', ''))
            
        bot.delete_message(message.chat.id, msg.message_id)

    except Exception as e:
        bot.edit_message_text(f"❌ تعذر التحميل:\n`{str(e)}`", message.chat.id, msg.message_id, parse_mode="Markdown")
        
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

if __name__ == "__main__":
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    while True:
        try:
            bot.remove_webhook()
            bot.polling(non_stop=True, skip_pending=True, timeout=90)
        except Exception:
            time.sleep(5)
