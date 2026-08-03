import os
import logging
from threading import Thread
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# إعداد سيرفر Flask وهمي لإبقاء Render سعيداً
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot is running fine!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_web.run(host='0.0.0.0', port=port)

# إعداد السجلات (Logging)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
MAX_DURATION = 420  # 7 دقائق
MAX_FILESIZE = 20 * 1024 * 1024  # 20 ميجابايت بالبايت

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك! 🤖\nأرسل لي أي رابط فيديو من منصات التواصل، وسأقوم بتحميله لك بشرط ألا تتجاوز مدته 7 دقائق وحجمه 20 ميجابايت.")

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    status_msg = await update.message.reply_text("⏳ جاري الفحص والتحميل...")
    
    file_path = None
    try:
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': 'video_%(id)s.%(ext)s',
            'max_filesize': MAX_FILESIZE,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android_creator', 'android', 'ios'],
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            }
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            duration = info.get('duration', 0)
            filesize = info.get('filesize') or info.get('filesize_approx')

            # التحقق من المدة (أقل من 7 دقائق)
            if duration and duration > MAX_DURATION:
                await status_msg.edit_text("❌ عذراً، لا يمكن تحميل الفيديو لأن مدته تتجاوز 7 دقائق!")
                return

            # التحقق من الحجم (أقل من 20 ميجابايت)
            if filesize and filesize > MAX_FILESIZE:
                size_mb = round(filesize / (1024 * 1024), 2)
                await status_msg.edit_text(
                    f"⚠️ **عذراً، لا يمكن تحميل هذا الفيديو!**\n\n"
                    f"📐 حجم الفيديو: `{size_mb} MB`\n"
                    f"⛔ الحد الأقصى المسموح به: `20 MB`"
                )
                return

            await status_msg.edit_text("📥 جاري تحميل الفيديو إلى السيرفر...")
            info_data = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info_data)

        await status_msg.edit_text("📤 جاري رفع الفيديو إليك...")
        with open(file_path, 'rb') as video_file:
            await update.message.reply_video(video=video_file, caption="تم التحميل بنجاح! 🎉")
        
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ حدث خطأ أثناء التحميل:\n{str(e)[:100]}")
    
    finally:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

def main():
    if not TOKEN:
        print("خطأ: لم يتم ضبط BOT_TOKEN!")
        return

    # تشغيل Flask في مسار جانبي (Thread)
    Thread(target=run_flask, daemon=True).start()

    # زيادة مهلة الاتصال لمنع أخطاء TimedOut
    application = (
        Application.builder()
        .token(TOKEN)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    print("البوت يعمل الآن...")
    application.run_polling()

if __name__ == '__main__':
    main()
