import asyncio, json, os, sys
sys.stdout.reconfigure(encoding='utf-8')
from telethon import TelegramClient

BASE = r"C:\Users\Win\tg-mcp"
c = json.load(open(os.path.join(BASE, "credentials.json"), encoding="utf-8"))

async def main():
    async with TelegramClient(os.path.join(BASE, "me"), c["api_id"], c["api_hash"]) as cl:
        print("Connected...")
        me = await cl.get_me()
        print("Logged in as:", me.first_name)
        async for m in cl.iter_messages(me, limit=10):
            print(f"Message ID={m.id}, text={m.text}, voice={bool(m.voice)}, media={type(m.media)}")
            if m.voice or m.video_note or (m.media and hasattr(m.media, 'document') and 'audio' in getattr(m.media.document, 'mime_type', '')):
                fpath = os.path.join(r"C:\Users\Win", "last_voice.ogg")
                print("Downloading media to", fpath)
                await m.download_media(file=fpath)
                print("Downloaded successfully!")
                break

asyncio.run(main())
