import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp

# إعداد السجلات (Logging)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# استدعاء توكن البوت من متغيرات البيئة
TOKEN = os.getenv("BOT_TOKEN")
# الحد الأقصى لمدّة الفيديو: 7 دقائق (420 ثانية)
MAX_DURATION = 420 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك! 🤖\nأرسل لي أي رابط فيديو من منصات التواصل، وسأقوم بتحميله لك بشرط ألا تتجاوز مدته 7 دقائق.")

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    status_msg = await update.message.reply_text("⏳ جاري الفحص والتحميل...")
    
    file_path = None
    try:
        # إعدادات yt-dlp لفحص المدة والتحميل
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': 'video_%(id)s.%(ext)s',
            'max_filesize': 50 * 1024 * 1024, # حد تلجرام للبوتات العادية هو 50MB
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # جلب معلومات الفيديو أولاً بدون تحميله
            info = ydl.extract_info(url, download=False)
            duration = info.get('duration', 0)

            # التحقق من شرط الـ 7 دقائق
            if duration and duration > MAX_DURATION:
                await status_msg.edit_text("❌ عذراً، لا يمكن تحميل الفيديو لأن مدته تتجاوز 7 دقائق!")
                return

            # تحميل الفيديو إذا كان أصلح للشروط
            await status_msg.edit_text("📥 جاري تحميل الفيديو إلى السيرفر...")
            info_data = ydl.extract_info(url, download=True)
            file_path = ydl.prepare_filename(info_data)

        # إرسال الفيديو للمستخدم
        await status_msg.edit_text("📤 جاري رفع الفيديو إليك...")
        with open(file_path, 'rb') as video_file:
            await update.message.reply_video(video=video_file, caption="تم التحميل بنجاح! 🎉")
        
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ حدث خطأ أثناء التحميل. التأكد من صحة الرابط أو جرب لاحقاً.\nالخطأ: {str(e)[:100]}")
    
    finally:
        # حذف الفيديو من السيرفر بعد الإرسال لتوفير المساحة
        if file_path and os.path.exists(file_path):
            os.remove(file_path)

def main():
    if not TOKEN:
        print("خطأ: لم يتم ضبط BOT_TOKEN!")
        return

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_video))

    print("البوت يعمل الآن...")
    app.run_polling()

if __name__ == '__main__':
    main()
