import os
import tempfile
import requests
from telebot import TeleBot
from yt_dlp import YoutubeDL

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = TeleBot(BOT_TOKEN)

def tiktok_no_watermark(url):
    api = f"https://www.tikwm.com/api/?url={url}"
    r = requests.get(api).json()
    try:
        return r["data"]["play"]
    except:
        return None

def download_with_ytdlp(url):
    ydl_opts = {
        "format": "mp4",
        "outtmpl": "%(id)s.%(ext)s",
        "quiet": True
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        video_url = info["url"]
        return video_url

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "أرسل رابط أي فيديو وسأقوم بتحميله لك 🔥")

@bot.message_handler(func=lambda m: True)
def handle(message):
    url = message.text.strip()
    bot.reply_to(message, "⏳ جاري التحميل...")

    # TikTok بدون علامة مائية
    if "tiktok.com" in url:
        bot.send_message(message.chat.id, "🔍 محاولة إزالة العلامة المائية...")
        no_wm = tiktok_no_watermark(url)
        if no_wm:
            bot.send_video(message.chat.id, no_wm, caption="✔ بدون علامة مائية")
            return

    # fallback لجميع المنصات
    try:
        video_url = download_with_ytdlp(url)
        bot.send_video(message.chat.id, video_url)
    except:
        bot.send_message(message.chat.id, "❌ لم أستطع تحميل الفيديو. جرّب رابط آخر.")

bot.infinity_polling()
