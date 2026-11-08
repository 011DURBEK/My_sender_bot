"""
Telegram Super Controller Bot (Personal Account Relay + Voice-to-Text + Stealth Reader + Custom Auto-Responder)
Developed for 011ᵈᵘʳᵇᵉᵏ
"""
import asyncio
import json
import os
import re
import sys
import tempfile
import time
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import requests
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
except ImportError:
    pass

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE, "credentials.json")


def load_config():
    data = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    if "auto_reply" not in data:
        data["auto_reply"] = {
            "enabled": False,
            "text": "Assalomu alaykum! Hozir bandman / darsdaman, bo'shaganimda o'zim aloqaga chiqaman.",
            "cooldown_minutes": 30
        }
    return data


def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: could not save config to {CONFIG_FILE}: {e}")


c = load_config()
API_ID = int(os.getenv("API_ID") or c.get("api_id", 35767080))
API_HASH = os.getenv("API_HASH") or c.get("api_hash", "86b054da0f4792a43b12e7b90b186f7d")
BOT_TOKEN = os.getenv("BOT_TOKEN") or c.get("bot_token", "9151838519:AAEzkrXTohU3RwX6yYmnD94gy4sXzUfO7nY")
ALLOWED_USER_ID = int(os.getenv("ALLOWED_USER_ID") or c.get("allowed_user_id", 6482449125))

SESSION_STRING = (os.getenv("SESSION_STRING") or c.get("session_string", "")).strip()
if SESSION_STRING:
    user_client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
else:
    user_client = TelegramClient(os.path.join(BASE, "me"), API_ID, API_HASH)

bot = TelegramClient(StringSession(), API_ID, API_HASH)

user_states = {}
last_auto_replied = {}  # user_id -> timestamp (float)


def transcribe_audio(fpath: str, groq_key: str) -> str:
    if not groq_key or not os.path.exists(fpath):
        return None
    try:
        with open(fpath, "rb") as f:
            res = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {groq_key.strip()}"},
                files={"file": (os.path.basename(fpath), f)},
                data={"model": "whisper-large-v3", "language": "uz"},
                timeout=90,
            )
        if res.status_code == 200:
            return res.json().get("text", "").strip()
        else:
            print(f"Groq API Error: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"Transcription error: {e}")
    return None


async def get_recent_dialogs(limit=15):
    dialogs = []
    async for d in user_client.iter_dialogs(limit=limit):
        if d.is_user and getattr(d.entity, "bot", False):
            continue
        kind = "👥 " if d.is_group else "📢 " if d.is_channel else "👤 "
        dialogs.append({"id": d.id, "name": f"{kind}{d.name[:25]}"})
    return dialogs


def build_chats_markup(dialogs):
    cfg = load_config()
    auto_status = "🟢 Yoqilgan" if cfg.get("auto_reply", {}).get("enabled") else "🔴 O'chirilgan"

    buttons = []
    for d in dialogs[:8]:
        buttons.append([Button.inline(d["name"], data=f"sel_{d['id']}")])
    buttons.append([
        Button.inline("🔄 Yangilash", data="refresh"),
        Button.inline("✍️ @username / ID", data="custom")
    ])
    buttons.append([
        Button.inline(f"🤖 Avto-javob: {auto_status}", data="toggle_auto"),
        Button.inline("✏️ Matnni o'zim yozish", data="start_edit_auto")
    ])
    return buttons


# ==========================================
# 1. AKKAUNTGA KELGAN XABARLAR (GOLOS TRANSKRIPSIYA + OFLAYN AVTO-JAVOB)
# ==========================================
@user_client.on(events.NewMessage(incoming=True))
async def on_user_incoming_message(event):
    if not event.is_private:
        return

    msg = event.message
    sender = await event.get_sender()
    sender_id = event.chat_id

    # Exclude other bots
    if getattr(sender, "bot", False):
        return

    s_name = getattr(sender, "first_name", None) or getattr(sender, "title", None) or "Foydalanuvchi"
    username = f" (@{sender.username})" if getattr(sender, "username", None) else ""

    cfg = load_config()
    now = time.time()

    # --- A) OFLAYN AVTO-JAVOB ---
    auto_cfg = cfg.get("auto_reply", {})
    if auto_cfg.get("enabled"):
        cooldown_sec = int(auto_cfg.get("cooldown_minutes", 30)) * 60
        last_time = last_auto_replied.get(sender_id, 0)

        if now - last_time > cooldown_sec:
            last_auto_replied[sender_id] = now
            reply_text = auto_cfg.get("text", "Assalomu alaykum! Hozir bandman, keyinroq aloqaga chiqaman.")
            try:
                await event.reply(reply_text)
                print(f"Auto-replied to {s_name}")

                incoming_summary = msg.text or ("[🎙 Golos]" if msg.voice else "[⭕️ Dumaloq]" if msg.video_note else "[Media]")
                notify_txt = (
                    f"🤖 **Avto-javob yuborildi!**\n\n"
                    f"👤 **Kimga:** {s_name}{username}\n"
                    f"💬 **Uning xabari:** {incoming_summary[:60]}\n"
                    f"📤 **Yuborilgan javob:** *« {reply_text} »*"
                )
                btn = [[Button.inline(f"✍️ {s_name[:15]}ga yozish", data=f"sel_{sender_id}")]]
                await bot.send_message(ALLOWED_USER_ID, notify_txt, buttons=btn)
            except Exception as e:
                print(f"Failed to auto-reply: {e}")

    # --- B) GOLOS KELGANDA MATNGA O'GIRISH ---
    if msg.voice or msg.video_note:
        dur = int(getattr(getattr(msg, "file", None), "duration", 0) or 0)
        belgi = "⭕️ Dumaloq video" if msg.video_note else "🎙 Ovozli xabar"
        groq_key = cfg.get("groq_key", "").strip()
        text_out = None

        if groq_key:
            with tempfile.TemporaryDirectory() as tmp:
                ext = ".mp4" if msg.video_note else ".ogg"
                fpath = await msg.download_media(file=os.path.join(tmp, "incoming" + ext))
                text_out = transcribe_audio(fpath, groq_key)

        if text_out:
            text_notify = (
                f"🔔 **Sizga yangi {belgi} keldi!**\n"
                f"👤 **Kimdan:** {s_name}{username}\n"
                f"⏱ **Davomiyligi:** {dur} soniya\n\n"
                f"📝 **Matni:**\n> *« {text_out} »*"
            )
        else:
            text_notify = (
                f"🔔 **Sizga yangi {belgi} keldi!**\n"
                f"👤 **Kimdan:** {s_name}{username}\n"
                f"⏱ **Davomiyligi:** {dur} soniya\n\n"
                f"💡 *Matnga o'girish uchun botga `/groq <kalit>` deb Groq kalitini kiritib qo'ying.*"
            )

        btn = [[Button.inline(f"✍️ {s_name[:15]}ga javob yozish", data=f"sel_{sender_id}")]]
        await bot.send_message(ALLOWED_USER_ID, text_notify, buttons=btn)


# ==========================================
# 2. BOTGA KELGAN BUYRUQ VA XABARLAR
# ==========================================
@bot.on(events.NewMessage)
async def bot_message_handler(event):
    if event.sender_id != ALLOWED_USER_ID:
        await event.respond("⛔️ Kechirasiz, bu shaxsiy boshqaruv boti.")
        return

    text = event.text or ""
    uid = event.sender_id
    state = user_states.get(uid, {})

    # --- FOYDALANUVCHI O'ZI AVTO-JAVOB MATNINI YOZAYOTGAN BO'LSA ---
    if state.get("waiting_for_auto_text"):
        if text.startswith("/cancel"):
            user_states[uid]["waiting_for_auto_text"] = False
            await event.respond("❌ Matn kiritish bekor qilindi. Bosh menyu: /start")
            return

        user_states[uid]["waiting_for_auto_text"] = False
        new_text = text.strip()
        cfg = load_config()
        if "auto_reply" not in cfg:
            cfg["auto_reply"] = {"cooldown_minutes": 30}
        cfg["auto_reply"]["text"] = new_text
        cfg["auto_reply"]["enabled"] = True  # Automatically turn it on
        save_config(cfg)

        btn = [
            [Button.inline("✏️ Qaytadan o'zgartirish", data="start_edit_auto")],
            [Button.inline("🔴 Avto-javobni o'chirish", data="toggle_auto"), Button.inline("🔄 Bosh menyu", data="refresh")]
        ]
        await event.respond(
            f"✅ **Avto-javob matni muvaffaqiyatli saqlandi va faollashtirildi!**\n\n"
            f"📌 **Siz yozgan matn:**\n> *« {new_text} »*\n\n"
            f"🟢 **Holati:** Yoqilgan.\n"
            f"Endi sizga kimdir shaxsiyda yozsa, unga aynan mana shu xabar yuboriladi!",
            buttons=btn
        )
        return

    # 1. /start yoki /chats
    if text.startswith("/start") or text.startswith("/chats"):
        user_states[uid] = {}
        dialogs = await get_recent_dialogs()
        markup = build_chats_markup(dialogs)
        await event.respond(
            "👋 **Assalomu alaykum!**\n\n"
            "Bu sizning shaxsiy Telegram boshqaruv botingiz.\n"
            "Qaysi chatga xabar yubormoqchisiz? Tanlang:",
            buttons=markup
        )
        return

    # 2. /auto — oflayn avto-javob matnini o'rnatish yoki holatini ko'rish
    if text.startswith("/auto"):
        parts = text.split(maxsplit=1)
        cfg = load_config()
        if len(parts) > 1:
            # User passed text directly: /auto Men darsdaman...
            new_text = parts[1].strip()
            cfg["auto_reply"]["text"] = new_text
            cfg["auto_reply"]["enabled"] = True
            save_config(cfg)
            btn = [[Button.inline("🔄 Bosh menyu", data="refresh"), Button.inline("✏️ Boshqa matn yozish", data="start_edit_auto")]]
            await event.respond(
                f"✅ **Avto-javob matni saqlandi va yoqildi!**\n\n"
                f"📌 **Siz yozgan matn:**\n> *« {new_text} »*",
                buttons=btn
            )
            return

        ac = cfg.get("auto_reply", {})
        status = "🟢 Yoqilgan" if ac.get("enabled") else "🔴 O'chirilgan"
        r_text = ac.get("text", "")
        msg_body = (
            f"🤖 **Avto-javob sozlamasi:**\n\n"
            f"• **Holati:** {status}\n"
            f"• **Hozirgi matn:**\n> *« {r_text} »*\n\n"
            f"Matnni o'zingiz yozib o'zgartirish uchun quyidagi tugmani bosing:"
        )
        btns = [
            [Button.inline("✏️ Matnni o'zim yozish", data="start_edit_auto")],
            [Button.inline("🟢 Yoqish" if not ac.get("enabled") else "🔴 O'chirish", data="toggle_auto"), Button.inline("🔙 Orqaga", data="refresh")]
        ]
        await event.respond(msg_body, buttons=btns)
        return

    # 3. /help
    if text.startswith("/help"):
        await event.respond(
            "📖 **Boshqaruv boti buyruqlari:**\n\n"
            "• `/start` yoki `/chats` — Chatlar ro'yxati\n"
            "• `/auto` — Avto-javob sozlamalari\n"
            "• `/auto <yangi matn>` — Yangi avto-javob matnini tezkor yozish\n"
            "• `/search <nom>` — Chatni nomi bo'yicha qidirish\n"
            "• `/groq <kalit>` — Whisper ovoz transkripsiyasi kaliti\n"
            "• `/later <daqiqa>m <matn>` — Rejali xabar (`/later 15m Darsdaman`)\n"
            "• `/cancel` — Tanlangan chatni bekor qilish\n\n"
            "🔥 **Maxsus imkoniyatlar:**\n"
            "1. **Avto-javob:** Xohlagan matningizni o'zingiz yozasiz, oflayn bo'lganingizda sizga yozganlarga avtomatik jo'natadi.\n"
            "2. **Ghost Read:** Chatni tanlab `📖 Oxirgi xabarlar` bossangiz, ko'rilmasdan o'qiydi.\n"
            "3. **Golos transkripsiya:** Har qanday ovozli xabarni matnga o'giradi."
        )
        return

    # 4. /groq <kalit>
    if text.startswith("/groq"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await event.respond("Kalitni quyidagicha yuboring:\n`/groq gsk_bu_yerga_kalit`")
            return
        cfg = load_config()
        cfg["groq_key"] = parts[1].strip()
        save_config(cfg)
        await event.respond("✅ **Groq API kaliti saqlandi!** Barcha ovozli xabarlar avtomatik matnga o'giriladi! 🎙✨")
        return

    # 5. /search <nom>
    if text.startswith("/search"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2:
            await event.respond("Qidirish uchun: `/search <nom>` deb yozing.")
            return
        q = parts[1].strip().lower()
        found = []
        async for d in user_client.iter_dialogs(limit=100):
            if q in d.name.lower():
                kind = "👥 " if d.is_group else "📢 " if d.is_channel else "👤 "
                found.append({"id": d.id, "name": f"{kind}{d.name[:25]}"})
        if not found:
            await event.respond("❌ Chat topilmadi.")
        else:
            markup = build_chats_markup(found)
            await event.respond(f"🔍 **Topilgan chatlar (`{q}`):**", buttons=markup)
        return

    # 6. /later <daqiqa>m <matn>
    if text.startswith("/later"):
        state = user_states.get(uid, {})
        target_id = state.get("target_id")
        target_name = state.get("target_name")
        if not target_id:
            await event.respond("⚠️ Avval xabar yuborish uchun chatni tanlang (`/chats`).")
            return

        m = re.match(r"^/later\s+(\d+)([ms])\s+(.+)$", text, re.IGNORECASE | re.DOTALL)
        if not m:
            await event.respond("Format: `/later 5m Salom` (5 daqiqadan keyin yuborish).")
            return

        num = int(m.group(1))
        unit = m.group(2).lower()
        content = m.group(3)
        delay_sec = num * 60 if unit == "m" else num

        await event.respond(f"⏰ Xabar rejalashtirildi! **{num}{unit}** dan keyin `{target_name}` ga yuboriladi.")

        async def send_delayed():
            await asyncio.sleep(delay_sec)
            try:
                await user_client.send_message(target_id, content)
                await bot.send_message(ALLOWED_USER_ID, f"✅ Rejalashtirilgan xabar `{target_name}` ga yuborildi: {content[:30]}")
            except Exception as ex:
                await bot.send_message(ALLOWED_USER_ID, f"❌ Rejali xabarni yuborishda xato: {ex}")

        asyncio.create_task(send_delayed())
        return

    # 7. /cancel
    if text.startswith("/cancel"):
        user_states[uid] = {}
        await event.respond("❌ Amal bekor qilindi. Boshlash uchun: /start")
        return

    # Waiting for custom username/id
    if state.get("waiting_for_custom"):
        query = text.strip()
        try:
            entity = await user_client.get_entity(int(query) if query.lstrip("-").isdigit() else query)
            name = getattr(entity, "title", None) or getattr(entity, "first_name", None) or query
            user_states[uid] = {
                "target_id": entity.id,
                "target_name": name,
                "waiting_for_custom": False
            }
            btn = [
                [Button.inline("📖 Oxirgi xabarlar (Ko'rilmasdan)", data=f"read_{entity.id}")],
                [Button.inline("🔄 Boshqa chat", data="refresh"), Button.inline("❌ Bekor qilish", data="cancel_sel")]
            ]
            await event.respond(
                f"🎯 **Tanlandi:** `{name}`\n\n"
                f"Endi nimadir yozing yoki rasm/golos tashlang — darhol akkauntingizdan yuboriladi!",
                buttons=btn
            )
        except Exception as e:
            await event.respond(f"❌ Chat topilmadi: {e}\nQaytadan @username yoki ID yuboring (bekor qilish: /cancel):")
        return

    target_id = state.get("target_id")
    target_name = state.get("target_name")

    # If no chat selected, but user sends a voice note to the bot -> transcribe it directly!
    if not target_id:
        if event.voice or event.video_note or (event.media and hasattr(event.media, "document") and "audio" in getattr(event.media.document, "mime_type", "")):
            cfg = load_config()
            groq_key = cfg.get("groq_key", "").strip()
            if not groq_key:
                await event.respond("🎙 Ovozni matnga aylantirish uchun avval `/groq <kalit>` deb Groq API kalitini kiritishingiz kerak.")
                return
            status_m = await event.respond("🎧 Ovoz eshitilmoqda...")
            with tempfile.TemporaryDirectory() as tmp:
                ext = ".mp4" if event.video_note else ".ogg"
                fpath = await event.download_media(file=os.path.join(tmp, "voice" + ext))
                res = transcribe_audio(fpath, groq_key)
                if res:
                    await status_m.edit(f"📝 **Golos matni:**\n\n> *« {res} »*")
                else:
                    await status_m.edit("❌ Ovozni aniqlab bo'lmadi yoki Groq xatolik qaytardi.")
            return

        dialogs = await get_recent_dialogs()
        markup = build_chats_markup(dialogs)
        await event.respond(
            "⚠️ Hali xabar yuborish uchun chat tanlamadingiz!\nQuyidagi chatlardan birini tanlang:",
            buttons=markup
        )
        return

    # Relay to selected target
    status_msg = await event.respond("🚀 Akkauntingizdan yuborilmoqda...")
    try:
        if event.media:
            with tempfile.TemporaryDirectory() as tmp:
                downloaded = await event.download_media(file=tmp)
                is_voice = bool(event.voice)
                is_video_note = bool(event.video_note)
                await user_client.send_file(
                    target_id,
                    downloaded,
                    caption=event.text or None,
                    voice_note=is_voice,
                    video_note=is_video_note
                )
        else:
            await user_client.send_message(target_id, event.text)

        await status_msg.edit(
            f"✅ **Muvaffaqiyatli yuborildi!**\n"
            f"📌 **Qayerga:** {target_name}\n\n"
            f"Yana nimadir yuborsangiz, yana shu chatga ketadi.\n"
            f"Boshqa chatni tanlash uchun: /chats"
        )
    except Exception as e:
        await status_msg.edit(f"❌ Yuborishda xatolik yuz berdi: {e}")


# ==========================================
# 3. CALLBACK QUERY HANDLER
# ==========================================
@bot.on(events.CallbackQuery)
async def callback_handler(event):
    if event.sender_id != ALLOWED_USER_ID:
        await event.answer("Ruxsat berilmagan!", alert=True)
        return

    data = event.data.decode("utf-8")
    uid = event.sender_id

    # EDIT AUTO-REPLY: USER WRITES HIS OWN TEXT
    if data == "start_edit_auto":
        user_states[uid] = {"waiting_for_auto_text": True}
        await event.answer()
        await event.respond(
            "✍️ **Avto-javobda nima deb yozilishini xohlaysiz?**\n\n"
            "Matningizni shu yerga yozib yuboring:\n"
            "*(Masalan: 'Hozir darsdaman, soat 5 da aloqaga chiqaman' yoki xohlagan matningiz)*\n\n"
            "Bekor qilish uchun: /cancel"
        )
        return

    if data == "toggle_auto":
        cfg = load_config()
        if "auto_reply" not in cfg:
            cfg["auto_reply"] = {"enabled": False, "text": "Hozir bandman, keyinroq aloqaga chiqaman.", "cooldown_minutes": 30}
        curr = cfg["auto_reply"].get("enabled", False)
        cfg["auto_reply"]["enabled"] = not curr
        save_config(cfg)

        new_status = "🟢 Yoqildi!" if not curr else "🔴 O'chirildi!"
        await event.answer(f"Avto-javob {new_status}")

        dialogs = await get_recent_dialogs()
        markup = build_chats_markup(dialogs)
        try:
            await event.edit("Qaysi chatga xabar yubormoqchisiz? Tanlang:", buttons=markup)
        except Exception:
            pass
        return

    if data == "refresh":
        await event.answer("Yangilanmoqda...")
        dialogs = await get_recent_dialogs()
        markup = build_chats_markup(dialogs)
        await event.edit("Qaysi chatga xabar yubormoqchisiz? Tanlang:", buttons=markup)
        return

    if data == "custom":
        user_states[uid] = {"waiting_for_custom": True}
        await event.answer()
        await event.respond("✍️ Yubormoqchi bo'lgan chatingizning **@username** yoki **ID** sini yozing:\n*(Bekor qilish: /cancel)*")
        return

    if data == "cancel_sel":
        user_states[uid] = {}
        await event.answer("Bekor qilindi")
        await event.edit("❌ Tanlash bekor qilindi. Boshlash uchun: /start")
        return

    if data.startswith("read_"):
        cid = int(data.split("_")[1])
        await event.answer("Xabarlar olinmoqda...")
        try:
            rows = []
            entity = await user_client.get_entity(cid)
            cname = getattr(entity, "title", None) or getattr(entity, "first_name", None) or str(cid)
            async for m in user_client.iter_messages(cid, limit=6):
                if m.text or m.voice or m.media:
                    time_str = m.date.strftime("%H:%M")
                    sender_name = "Siz" if m.out else (getattr(m.sender, "first_name", "") or "U")
                    body = m.text or ("[🎙 Golos]" if m.voice else "[⭕️ Dumaloq]" if m.video_note else "[Media]")
                    rows.append(f"• `[{time_str}]` **{sender_name}:** {body[:80]}")

            if rows:
                txt = f"📬 **{cname} chatidagi oxirgi xabarlar:**\n*(Anonim o'qildi, suhbatdoshda ko'rilganlik belgisi chiqmaydi)*\n\n" + "\n".join(reversed(rows))
            else:
                txt = f"📬 **{cname}** chatida xabarlar topilmadi."

            btn = [
                [Button.inline(f"✍️ {cname[:15]}ga yozish", data=f"sel_{cid}")],
                [Button.inline("🔄 Chatlar ro'yxati", data="refresh")]
            ]
            await event.respond(txt, buttons=btn)
        except Exception as e:
            await event.respond(f"❌ Xabarlarni o'qishda xato: {e}")
        return

    if data.startswith("sel_"):
        cid = int(data.split("_")[1])
        try:
            entity = await user_client.get_entity(cid)
            name = getattr(entity, "title", None) or getattr(entity, "first_name", None) or str(cid)
        except Exception:
            name = str(cid)

        user_states[uid] = {
            "target_id": cid,
            "target_name": name,
            "waiting_for_custom": False
        }
        await event.answer("Tanlandi!")

        btn = [
            [Button.inline("📖 Oxirgi xabarlar (Ko'rilmasdan o'qish)", data=f"read_{cid}")],
            [Button.inline("🔄 Boshqa chat", data="refresh"), Button.inline("❌ Bekor qilish", data="cancel_sel")]
        ]

        await event.edit(
            f"🎯 **Tanlangan chat:** `{name}`\n\n"
            f"Endi botga nima yuborsangiz (matn, golos, rasm, fayl, video), "
            f"hammasi **sizning shaxsiy akkauntingiz nomidan** `{name}` ga yuboriladi!\n\n"
            f"💡 *Rejali xabar: `/later 10m Matn`*",
            buttons=btn
        )


async def start_health_server(port: int):
    """Bulutli platformalar (Render, Koyeb) uchun fon health-check serveri"""
    async def handle_client(reader, writer):
        try:
            await reader.readline()
            body = '{"status":"ok","bot":"online"}'
            response = (
                f"HTTP/1.1 200 OK\r\n"
                f"Content-Type: application/json; charset=utf-8\r\n"
                f"Content-Length: {len(body.encode('utf-8'))}\r\n"
                f"Connection: close\r\n\r\n"
                f"{body}"
            )
            writer.write(response.encode("utf-8"))
            await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    server = await asyncio.start_server(handle_client, "0.0.0.0", port)
    print(f"🌐 Health-check serveri {port}-portda tinglamoqda...")
    async with server:
        await server.serve_forever()


async def main():
    print("User client ishga tushmoqda...")
    await user_client.start()
    print("Bot client ishga tushmoqda...")
    await bot.start(bot_token=BOT_TOKEN)
    me = await bot.get_me()
    print(f"🤖 Bot ishga tushdi: @{me.username}")
    print("Tinglanmoqda...")

    tasks = [
        user_client.run_until_disconnected(),
        bot.run_until_disconnected()
    ]
    port_env = os.getenv("PORT")
    if port_env and port_env.isdigit():
        tasks.append(start_health_server(int(port_env)))

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
