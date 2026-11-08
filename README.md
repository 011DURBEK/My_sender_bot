# 🚀 Telegram Super Controller & Sender Bot

Shaxsiy Telegram akkauntini bot orqali boshqarish, xabarlarni rejalashtirish, ovozli xabarlarni matnga o'girish va avto-javob tizimi.

---

## 🔒 Xavfsizlik
* **Faqat bitta foydalanuvchi:** Bot faqat `ALLOWED_USER_ID` egasining buyruqlariga javob beradi. Boshqa har qanday odam yozsa, ruxsat berilmaydi.
* **Maxfiy kalitlar:** `.env` va `.session` fayllari `.gitignore` orqali himoyalangan va Git'ga tushmaydi.
* **Repozitoriy:** Ushbu repozitoriy GitHub'da faqat **PRIVATE (Yopiq)** bo'lishi shart!

---

## 🌐 24/7 Bepul ishga tushirish (Render.com orqali)

1. [Render.com](https://render.com) saytiga kiring va GitHub akkauntingiz orqali ro'yxatdan o'ting.
2. **New +** -> **Web Service** ni tanlang.
3. Ushbu GitHub repozitoriyangizni ulang.
4. Quyidagi sozlamalarni kiriting:
   - **Name:** `telegram-sender-bot`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python controller_bot.py`
   - **Instance Type:** `Free`
5. **Environment Variables** bo'limiga quyidagilarni qo'shing:
   - `API_ID` : Telegram API ID
   - `API_HASH` : Telegram API Hash
   - `BOT_TOKEN` : BotFather'dan olingan token
   - `ALLOWED_USER_ID` : Sizning Telegram ID'ingiz
   - `SESSION_STRING` : `python export_session.py` orqali olingan matn
   - `GROQ_KEY` : (ixtiyoriy) Groq Whisper API kaliti
6. **Deploy Web Service** tugmasini bosing!
7. Bot 24/7 uxlab qolmasligi uchun Render sizga bergan URL manzilni (masalan: `https://telegram-sender-bot.onrender.com`) [cron-job.org](https://cron-job.org) yoki [uptimerobot.com](https://uptimerobot.com) ga qo'shib, har 10 daqiqada ping qildirib qo'ying.

---

## 💻 Mahalliy kompyuterda ishga tushirish

```bash
# Virtual muhit yaratish
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Kutubxonalarni o'rnatish
pip install -r requirements.txt

# Ishga tushirish
python controller_bot.py
```
