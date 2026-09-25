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
    "users": set(),
    "admin_state": {}
}

async def check_membership(client, user_id):
    if user_id == ADMIN_ID:
        return True
        
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
            "🎬 به ربات خوش آمدید.\n\nبرای ادامه ابتدا در کانال‌های زیر عضو شوید:",
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

@app.on_callback_query(filters.regex("^check_join$"))
async def verify_join_callback(client, callback_query):
    user_id = callback_query.from_user.id
    is_joined = await check_membership(client, user_id)
    
    if is_joined:
        await callback_query.message.delete()
        await callback_query.message.reply("✅ عضویت شما تأیید شد.\nحالا می‌توانید محتوای موردنظر خود را دریافت کنید.")
    else:
        await callback_query.answer("❌ شما هنوز در تمام کانال‌ها عضو نشده‌اید!", show_alert=True)

# تابع ارسال فیلم، پیام هشدار، دکمه دانلود مجدد و حذف خودکار پس از 20 ثانیه
async def send_movie_file(client, chat_id, file_code):
    # پیام اصلی فیلم
    sent_movie = await client.send_message(
        chat_id, 
        f"🎬 **فیلم درخواستی شما** (کد: {file_code})"
    )
    
    warning_text = "📄 پیام‌ها و فایل‌های بالا به زودی پاک خواهند شد، لطفاً آن‌ها را ذخیره کنید! ⏳"
    download_again_text = "⚡️ برای دانلود مجدد، می‌توانید از دکمه زیر استفاده کنید! 👇"
    
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 دانلود مجدد ♻️", callback_data=f"redownload_{file_code}")]
    ])
    
    sent_warning = await client.send_message(chat_id, warning_text)
    sent_button = await client.send_message(chat_id, download_again_text, reply_markup=markup)
    
    # تایمر 20 ثانیه‌ای برای حذف خودکار پیام فیلم و هشدار
    await asyncio.sleep(20)
    try:
        await sent_movie.delete()
        await sent_warning.delete()
    except Exception:
        pass

@app.on_callback_query(filters.regex(r"^redownload_"))
async def redownload_callback(client, callback_query):
    file_code = callback_query.data.split("_")[1]
    await callback_query.answer("در حال ارسال مجدد فیلم...")
    await send_movie_file(client, callback_query.message.chat.id, file_code)

@app.on_message(filters.command("panel") & filters.user(ADMIN_ID))
async def panel_command(client, message: Message):
    bot_data["admin_state"][ADMIN_ID] = None
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار کاربران", callback_data="p_stats")],
        [InlineKeyboardButton("➕ افزودن کانال جوین", callback_data="p_add_ch")],
        [InlineKeyboardButton("➖ حذف کانال جوین", callback_data="p_del_ch")],
        [InlineKeyboardButton("📋 لیست کانال‌ها", callback_data="p_list_ch")]
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
    
    elif data == "p_add_ch":
        bot_data["admin_state"][ADMIN_ID] = "waiting_for_add"
        await callback_query.message.reply("➕ لطفاً آیدی کانال جدید را با علامت @ بفرستید (مثلاً `@my_channel`):")
        await callback_query.answer()

    elif data == "p_del_ch":
        bot_data["admin_state"][ADMIN_ID] = "waiting_for_del"
        channels_str = "\n".join(bot_data["channels"])
        await callback_query.message.reply(f"➖ کانال‌های فعلی:\n{channels_str}\n\nآیدی کانالی که می‌خواهید حذف کنید را بفرستید:")
        await callback_query.answer()

    elif data == "p_list_ch":
        channels_str = "\n".join(bot_data["channels"]) if bot_data["channels"] else "هیچ کانالی ثبت نشده است."
        await callback_query.message.edit_text(
            f"📋 **لیست کانال‌های جوین اجباری:**\n\n{channels_str}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="p_back")]])
        )

    elif data == "p_back":
        bot_data["admin_state"][ADMIN_ID] = None
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 آمار کاربران", callback_data="p_stats")],
            [InlineKeyboardButton("➕ افزودن کانال جوین", callback_data="p_add_ch")],
            [InlineKeyboardButton("➖ حذف کانال جوین", callback_data="p_del_ch")],
            [InlineKeyboardButton("📋 لیست کانال‌ها", callback_data="p_list_ch")]
        ])
        await callback_query.message.edit_text("⚙️ **پنل مدیریت پیشرفته ربات**\n\nلطفاً گزینه مورد نظر را انتخاب کنید:", reply_markup=markup)

@app.on_message(filters.text & filters.user(ADMIN_ID))
async def admin_text_handler(client, message: Message):
    state = bot_data["admin_state"].get(ADMIN_ID)
    text = message.text.strip()

    if state == "waiting_for_add":
        if not text.startswith("@"):
            await message.reply("❌ آیدی باید با علامت @ شروع شود. دوباره تلاش کنید:")
            return
        if text in bot_data["channels"]:
            await message.reply("⚠️ این کانال از قبل در لیست وجود دارد.")
        else:
            bot_data["channels"].append(text)
            await message.reply(f"✅ کانال `{text}` با موفقیت به لیست جوین اجباری اضافه شد.")
        bot_data["admin_state"][ADMIN_ID] = None

    elif state == "waiting_for_del":
        if text in bot_data["channels"]:
            bot_data["channels"].remove(text)
            await message.reply(f"✅ کانال `{text}` با موفقیت از لیست حذف شد.")
        else:
            await message.reply("❌ چنین کانالی در لیست وجود ندارد.")
        bot_data["admin_state"][ADMIN_ID] = None

# اجرای ربات
if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print("Movie Robot is running successfully...")
    app.run()
