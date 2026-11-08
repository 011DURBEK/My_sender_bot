"""
Ushbu skript mavjud shaxsiy Telegram sessiyangizni (me.session)
StringSession (matnli sessiya) ko'rinishiga o'tkazib beradi.
Uni Render / Koyeb / VPS da 'SESSION_STRING' muhit o'zgaruvchisi (Environment Variable)
sifatida qo'ysangiz, hech qanday faylsiz 24/7 ishlayveradi!
"""
import os
import sys
import json

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from telethon.sync import TelegramClient
from telethon.sessions import StringSession

BASE = os.path.dirname(os.path.abspath(__file__))
cfg_path = os.path.join(BASE, "credentials.json")

if os.path.exists(cfg_path):
    c = json.load(open(cfg_path, encoding="utf-8"))
    api_id = int(c["api_id"])
    api_hash = c["api_hash"]
else:
    api_id = int(os.getenv("API_ID", 0))
    api_hash = os.getenv("API_HASH", "")

print("Sessiya yuklanmoqda...")
client = TelegramClient(os.path.join(BASE, "me"), api_id, api_hash)
with client:
    session_string = StringSession.save(client.session)
    print("\n" + "=" * 60)
    print("✅ SIZNING MAXFIY SESSION_STRING KALITINGIZ:")
    print("=" * 60)
    print(session_string)
    print("=" * 60)
    print("\n💡 Bu kalitni Render/Koyeb dagi 'SESSION_STRING' maydoniga nusxalab qo'ying.")
    print("⚠️ Hech kimga ko'rsatmang va ochiq joylarga yozmang!\n")
