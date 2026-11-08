import asyncio, json, os
from telethon import TelegramClient

BASE = os.path.dirname(os.path.abspath(__file__))
c = json.load(open(os.path.join(BASE, "credentials.json"), encoding="utf-8"))

async def main():
    cl = TelegramClient(os.path.join(BASE, "me"), c["api_id"], c["api_hash"])
    await cl.start(phone=c["phone"])   # Telegram'ga kelgan kodni so'raydi
    me = await cl.get_me()
    print(f"✅ Kirdingiz: {me.first_name} (@{me.username})")
    await cl.disconnect()

asyncio.run(main())
