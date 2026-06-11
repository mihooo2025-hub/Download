import os
import glob
from pyrogram import Client, filters
import yt_dlp

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")

app = Client(
    "bot",
    bot_token=BOT_TOKEN,
    api_id=API_ID,
    api_hash=API_HASH
)

@app.on_message(filters.private & filters.text)
async def download_video(client, message):

    url = message.text.strip()

    msg = await message.reply("جاري التحميل...")

    try:
        ydl_opts = {
            "outtmpl": "%(title)s.%(ext)s",
            "format": "best"
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        files = glob.glob("*.*")
        video_file = max(files, key=os.path.getctime)

        await message.reply_video(video_file)

        os.remove(video_file)

        await msg.delete()

    except Exception as e:
        await msg.edit(f"خطأ:\n{e}")

app.run()
