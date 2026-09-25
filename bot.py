import asyncio
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message
)

# اطلاعات کامل ربات شما
TOKEN = "8927708021:AAFP3TGc6afe4wge-K06NZv7q94MNM7e6D4"
ADMIN_ID = 7067751062
CHANNELS = ["@persians_film", "@persians_serial"]
ARCHIVE_CHANNEL_ID = -1003965313357

# راه‌اندازی کلاینت ربات
app = Client(
    "movie_bot_final",
    api_id=6110000,
    api_hash="eb06d4fabfb49d8ec21c105b4753a334",
    bot_token=TOKEN
)

bot_data = {
    "channels": CHANNELS.copy(),
    "users": set()
}

async def check_membership(client, user_id):
    for channel in bot_data["channels"]:
        try:
            member = await client.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True

def join_markup():
    buttons = []
    for ch in bot_data["channels"]:
        buttons.append([InlineKeyboardButton(f"عضویت در کانال {ch}", url=f"https://t.me/{ch.replace('@', '')}")])
    buttons.append([InlineKeyboardButton("🔄 بررسی عضویت", callback_data="check_join")])
    return InlineKeyboardMarkup(buttons)

@app.on_message(filters.command("start"))
async def start_command(client, message: Message):
    user_id = message.from_user.id
    bot_data["users"].add(user_id)
    
    is_joined = await check_membership(client, user_id)
    if not is_joined:
        await message.reply(
            "❌ برای استفاده از ربات، لطفاً ابتدا در کانال‌های زیر عضو شوید و سپس روی دکمه بررسی عضویت کلیک کنید:",
            reply_markup=join_markup()
        )
        return

    if len(message.command) > 1:
        file_code = message.command[1]
        await send_movie_file(client, message.chat.id, file_code)
    else:
        await message.reply(
            "🎬 سلام! به ربات فیلم و سریال خوش آمدید.\n\n"
            "لطفاً لینک فیلم یا سریال مورد نظر خود را از کانال انتخاب کنید تا به ربات هدایت شوید."
        )

@app.on_callback_query(filters.regex("check_join"))
async def verify_join_callback(client, callback_query):
    user_id = callback_query.from_user.id
    is_joined = await check_membership(client, user_id)
    
    if is_joined:
        await callback_query.message.delete()
        await callback_query.message.reply("✅ عضویت شما تایید شد! حالا می‌توانید فیلم خود را دریافت کنید.")
    else:
        await callback_query.answer("❌ شما هنوز در تمام کانال‌ها عضو نشده‌اید!", show_alert=True)

async def send_movie_file(client, chat_id, file_code):
    sent_msg = await client.send_message(
        chat_id, 
        f"🎬 **فیلم درخواستی شما** (کد: {file_code})\n\n⏳ این فایل پس از ۲۰ ثانیه پاک خواهد شد!"
    )
    
    warning_text = "📄 پیام ها و فایل های بالا به زودی پاک خواهند شد ، لطفاً آن ها را ذخیره کنید! ⏳"
    download_again_text = "⚡️ برای دانلود مجدد ، می توانید از دکمه زیر استفاده کنید! 👇"
    
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 دانلود مجدد ♻️", callback_data=f"redownload_{file_code}")]
    ])
    
    msg_warning = await client.send_message(chat_id, warning_text)
    msg_action = await client.send_message(chat_id, download_again_text, reply_markup=markup)
    
    await asyncio.sleep(20)
    try:
        await sent_msg.delete()
        await msg_warning.delete()
    except Exception:
        pass

@app.on_callback_query(filters.regex(r"^redownload_"))
async def redownload_callback(client, callback_query):
    file_code = callback_query.data.split("_")[1]
    await callback_query.answer("در حال ارسال مجدد فیلم...")
    await send_movie_file(client, callback_query.message.chat.id, callback_query.message.chat.id)

@app.on_message(filters.command("panel") & filters.user(ADMIN_ID))
async def panel_command(client, message: Message):
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار کاربران", callback_data="p_stats")],
        [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="p_broadcast")],
        [InlineKeyboardButton("➕ افزودن کانال جوین", callback_data="p_add_ch")],
        [InlineKeyboardButton("➖ حذف کانال جوین", callback_data="p_del_ch")]
    ])
    await message.reply("⚙️ **پنل مدیریت پیشرفته ربات**\n\nلطفاً گزینه مورد نظر را انتخاب کنید:", reply_markup=markup)

@app.on_callback_query(filters.regex("^p_"))
async def panel_callbacks(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id != ADMIN_ID:
        return

    data = callback_query.data

    if data == "p_stats":
        total_users = len(bot_data["users"])
        await callback_query.message.edit_text(
            f"📊 **آمار ربات شما:**\n\n👥 تعداد کل کاربران ربات: {total_users} نفر",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="p_back")]])
        )
    elif data == "p_back":
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 آمار کاربران", callback_data="p_stats")],
            [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="p_broadcast")],
            [InlineKeyboardButton("➕ افزودن کانال جوین", callback_data="p_add_ch")],
            [InlineKeyboardButton("➖ حذف کانال جوین", callback_data="p_del_ch")]
        ])
        await callback_query.message.edit_text("⚙️ **پنل مدیریت پیشرفته ربات**\n\nلطفاً گزینه مورد نظر را انتخاب کنید:", reply_markup=markup)

# اجرای امن ربات سازگار با رندر
if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(app.start())
    print("Movie Robot is running successfully...")
    asyncio.get_event_loop().run_forever()
