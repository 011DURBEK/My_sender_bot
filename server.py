"""Telegram MCP: agent mening akkauntim orqali o'qiydi va yozadi."""
import json, os, sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from telethon import TelegramClient
from mcp.server.fastmcp import FastMCP

BASE = os.path.dirname(os.path.abspath(__file__))
c = json.load(open(os.path.join(BASE, "credentials.json"), encoding="utf-8"))
mcp = FastMCP("telegram")


def client():
    # Har chaqiruvda yangi client: .session fayli band bo'lib qolmaydi
    return TelegramClient(os.path.join(BASE, "me"), c["api_id"], c["api_hash"])


def peer(chat: str):
    # "-100123..." kabi id'ni int qilamiz, @username'ni string qoldiramiz
    s = chat.strip()
    return int(s) if s.lstrip("-").isdigit() else s


def name(e) -> str:
    n = getattr(e, "first_name", None) or getattr(e, "title", None) or ""
    u = getattr(e, "username", None)
    return f"{n} (@{u})" if u else n


@mcp.tool()
async def list_dialogs(limit: int = 30) -> str:
    """Oxirgi chatlar ro'yxati: nom | turi | id. id read/send uchun kerak."""
    async with client() as cl:
        rows = []
        async for d in cl.iter_dialogs(limit=limit):
            kind = "group" if d.is_group else "channel" if d.is_channel else "user"
            rows.append(f"{d.name} | {kind} | id={d.id}")
        return "\n".join(rows) or "(bo'sh)"


@mcp.tool()
async def read_messages(chat: str, limit: int = 30) -> str:
    """Chat tarixi (eskidan yangiga). chat = @username yoki id."""
    async with client() as cl:
        rows = []
        async for m in cl.iter_messages(peer(chat), limit=limit):
            if m.text:
                who = name(m.sender) if m.sender else m.sender_id
                rows.append(f"[{m.date:%Y-%m-%d %H:%M}] {who}: {m.text}")
        return "\n".join(reversed(rows)) or "(bo'sh)"


@mcp.tool()
async def search_messages(chat: str, query: str, limit: int = 30) -> str:
    """Chat ichida so'z bo'yicha qidirish."""
    async with client() as cl:
        rows = []
        async for m in cl.iter_messages(peer(chat), search=query, limit=limit):
            if m.text:
                rows.append(f"[{m.date:%Y-%m-%d %H:%M}] {m.text}")
        return "\n".join(reversed(rows)) or "(topilmadi)"


@mcp.tool()
async def send_message(recipient: str, text: str, confirm: bool = False) -> str:
    """
    Mening nomimdan xabar yuborish. recipient = @username yoki id.
    XAVFSIZLIK: confirm=False bo'lsa HECH NARSA yubormaydi, faqat preview qaytaradi.
    Foydalanuvchi preview'ni tasdiqlagandan keyingina confirm=True bilan qayta chaqir.
    """
    async with client() as cl:
        e = await cl.get_entity(peer(recipient))
        if not confirm:
            return f"⚠️ PREVIEW, yuborilmadi.\nKimga: {name(e)}\nMatn: {text}\n\nTo'g'ri bo'lsa confirm=true bilan qayta chaqir."
        await cl.send_message(e, text)
        return f"✅ Yuborildi → {name(e)}"


if __name__ == "__main__":
    mcp.run()
