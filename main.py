import os
import time
import shutil
import logging
import imageio_ffmpeg
from threading import Thread
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
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
                return tmp_cookie_path
            except Exception:
                return path
    return None

COOKIE_PATH = get_cookie_path()

try:
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_PATH = None

# قاموس لتخزين روابط الأزرار المؤقتة
user_requests = {}

def format_duration(seconds):
    if not seconds:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def format_size(bytes_size):
    if not bytes_size:
        return "غير معروف"
    mb = bytes_size / (1024 * 1024)
    return f"{mb:.1f} M"

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    welcome_text = (
        "✨ **مرحباً بك في بوت التحميل الشامل!**\n\n"
        "أرسل رابط الفيديو من (YouTube, TikTok, Instagram) وسأقوم باستخراج خيارات التحميل المتاحة لك فوراً 🎬"
    )
    bot.reply_to(message, welcome_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: True)
def process_url(message):
    url = message.text.strip()
    if not (url.startswith("http://") or url.startswith("https://")):
        return

    msg = bot.reply_to(message, "🔍 جاري جلب معلومات المقطع...")

    opts = {
        'quiet': True,
        'no_warnings': True,
        'cookiefile': get_cookie_path(),
        'extractor_args': {
            'youtube': {
                'player_client': ['mweb', 'android', 'ios'],
            }
        }
    }

    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)

        title = info.get('title', 'فيديو بدون عنوان')
        duration = format_duration(info.get('duration'))
        filesize = format_size(info.get('filesize') or info.get('filesize_approx'))
        thumbnail = info.get('thumbnail')

        caption = f"🎬 **{title}**\n\n⏱ {duration} - 💾 {filesize}"

        # حفظ الرابط في الذاكرة باسم المستخدم
        req_id = f"{message.from_user.id}_{int(time.time())}"
        user_requests[req_id] = url

        # إنشاء الأزرار التفاعلية مثل البوت الاحترافي
        markup = InlineKeyboardMarkup()
        btn_video = InlineKeyboardButton("مقطع فيديو 🎥", callback_data=f"vid_{req_id}")
        btn_audio_file = InlineKeyboardButton("ملف صوتي 📁", callback_data=f"audfile_{req_id}")
        btn_audio_voice = InlineKeyboardButton("مقطع صوتي 🎧", callback_data=f"audvoice_{req_id}")

        markup.row(btn_audio_file, btn_audio_voice)
        markup.row(btn_video)

        bot.delete_message(message.chat.id, msg.message_id)

        if thumbnail:
            bot.send_photo(message.chat.id, photo=thumbnail, caption=caption, reply_markup=markup, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, text=caption, reply_markup=markup, parse_mode="Markdown")

    except Exception as e:
        logging.error(f"Extract Info Error: {e}")
        bot.edit_message_text(f"❌ تعذر جلب معلومات هذا الرابط.\nالسبب: `{str(e)}`", message.chat.id, msg.message_id, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_download_action(call):
    data = call.data
    action, req_id = data.split("_", 1)

    url = user_requests.get(req_id)
    if not url:
        bot.answer_callback_query(call.id, "❌ انتهت صلاحية هذا الطلب، يرجى إرسال الرابط مجدداً.", show_alert=True)
        return

    bot.answer_callback_query(call.id, "⏳ جاري بدء التحميل المعالج...")
    status_msg = bot.send_message(call.message.chat.id, "⬇️ جاري تحضير الملف وإرساله...")

    out_template = f"/tmp/{req_id}_%(title)s.%(ext)s"
    
    opts = {
        'quiet': True,
        'no_warnings': True,
        'outtmpl': out_template,
        'cookiefile': get_cookie_path(),
        'extractor_args': {
            'youtube': {
                'player_client': ['mweb', 'android', 'ios'],
                'skip': ['hls', 'dash']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        }
    }

    if FFMPEG_PATH:
        opts['ffmpeg_location'] = FFMPEG_PATH

    if action == "vid":
        opts['format'] = 'b/bestvideo+bestaudio/best'
    else: # الصوت
        opts['format'] = 'bestaudio/best'

    file_path = None
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info)

        with open(file_path, 'rb') as f:
            if action == "vid":
                bot.send_video(call.message.chat.id, f, caption=info.get('title', ''))
            elif action == "audfile":
                bot.send_document(call.message.chat.id, f, caption=info.get('title', ''))
            elif action == "audvoice":
                bot.send_audio(call.message.chat.id, f, caption=info.get('title', ''))

        bot.delete_message(call.message.chat.id, status_msg.message_id)

    except Exception as e:
        logging.error(f"Download Error: {e}")
        bot.edit_message_text(f"❌ حدث خطأ أثناء التحميل:\n`{str(e)}`", call.message.chat.id, status_msg.message_id, parse_mode="Markdown")

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
            try:
                bot.remove_webhook()
            except Exception:
                pass

            logging.info("🤖 Bot polling started successfully...")
            bot.polling(non_stop=True, skip_pending=True, timeout=90, long_polling_timeout=90)
        except Exception as e:
            logging.error(f"⚠️ Polling error: {e}")
            time.sleep(5)
