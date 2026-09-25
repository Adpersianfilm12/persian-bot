import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder

# تنظیمات اولیه
TOKEN = "8927708021:AAG4vZyzcZeRt8b4i-uk3e55Oay8mEnvlTU"
ADMIN_ID = 7067751062
ARCHIVE_CHANNEL_ID = -1003965313357
REQUIRED_CHANNELS = ["@persians_film", "@persians_serial"]

logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# راه‌اندازی دیتابیس SQLite
def init_db():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    """)
    conn.commit()
    conn.close()

init_db()

def add_user(user_id: int):
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_total_users():
    conn = sqlite3.connect("bot_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

# بررسی عضویت اجباری
async def check_membership(user_id: int) -> bool:
    for channel in REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True

# دستور شروع (Start)
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    add_user(user_id)
    
    # بررسی عضویت اجباری
    if not await check_membership(user_id):
        builder = InlineKeyboardBuilder()
        for ch in REQUIRED_CHANNELS:
            builder.button(text=f"عضویت در {ch}", url=f"https://t.me/{ch.lstrip('@')}")
        builder.button(text="🔄 بررسی عضویت", callback_data="check_join")
        builder.adjust(1)
        
        await message.answer(
            "❌ برای استفاده از ربات، لطفاً ابتدا در کانال‌های زیر عضو شوید:",
            reply_markup=builder.as_markup()
        )
        return

    await message.answer("سلام! به ربات فیلم و سریال خوش آمدید. لینک دانلود خود را ارسال کنید.")

# دکمه بررسی مجدد عضویت
@dp.callback_query(F.data == "check_join")
async def callback_check_join(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await check_membership(user_id):
        await callback.message.delete()
        await callback.message.answer("✅ عضویت شما تایید شد! حالا می‌توانید از ربات استفاده کنید.")
    else:
        await callback.answer("❌ شما هنوز در همه کانال‌ها عضو نشده‌اید!", show_alert=True)

# پنل مدیریت
@dp.message(Command("panel"))
async def cmd_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    total_users = get_total_users()
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 ارسال همگانی", callback_data="broadcast")
    builder.adjust(1)
    
    await message.answer(
        f"📊 **پنل مدیریت ربات**\n\n👥 تعداد کل کاربران: `{total_users}`",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )

# اجرای ربات
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
