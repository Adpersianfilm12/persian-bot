import threading
import time
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup

BOT_TOKEN = "8927708021:AAHduY6KITYe8fbtSN_rATlI0xG9cBgmvUc"
ADMIN_ID = 7067751062
CHANNELS = ["@persians_film", "@persians_serial"]
ARCHIVE_CHANNEL_ID = -1003965313357

users_database = set()
bot = telebot.TeleBot(BOT_TOKEN)


def is_user_member(user_id, channel_username):
  try:
    member = bot.get_chat_member(channel_username, user_id)
    if member.status in ["kicked", "left"]:
      return False
    return True
  except Exception:
    return False


def get_unjoined_channels(user_id):
  not_joined = []
  for channel in CHANNELS:
    if not is_user_member(user_id, channel):
      not_joined.append(channel)
  return not_joined


@bot.message_handler(commands=["start"])
def send_welcome(message):
  user_id = message.from_user.id
  chat_id = message.chat.id
  users_database.add(user_id)
  args = message.text.split()
  start_param = args[1] if len(args) > 1 else ""
  unjoined = get_unjoined_channels(user_id)
  if unjoined:
    markup = InlineKeyboardMarkup()
    for idx, channel in enumerate(CHANNELS, start=1):
      btn_text = f"📢 عضویت در کانال {idx}"
      btn_url = f"https://t.me/{channel.replace('@', '')}"
      markup.add(InlineKeyboardButton(btn_text, url=btn_url))
    markup.add(
        InlineKeyboardButton(
            "✅ بررسی عضویت / دریافت فیلم",
            callback_data=f"check_sub_{start_param}",
        )
    )
    bot.reply_to(
        message,
        (
            "⚠️ **محدودیت دسترسی!**\n\nبرای دریافت فیلم، لطفاً ابتدا در کانال‌های"
            " زیر عضو شوید:"
        ),
        reply_markup=markup,
        parse_mode="Markdown",
    )
    return
  handle_movie_delivery(chat_id, start_param)


def handle_movie_delivery(chat_id, start_param):
  if not start_param:
    bot.send_message(
        chat_id,
        (
            "✅ عضویت شما تایید شد! حالا می‌توانید از طریق لینک‌های داخل کانال"
            " فیلم‌ها را دریافت کنید."
        ),
    )
    return
  try:
    status_msg = bot.send_message(
        chat_id, "🎬 در حال دریافت فیلم از سرور آرشیو..."
    )
    copied_msg = bot.copy_message(
        chat_id=chat_id,
        from_chat_id=ARCHIVE_CHANNEL_ID,
        message_id=int(start_param),
    )
    video_msg_id = copied_msg.message_id
    try:
      bot.delete_message(chat_id, status_msg.message_id)
    except Exception:
      pass
    warning_text = (
        "⚠️ **توجه مهم:**\n📁 این فایل به زودی پاک خواهد شد، لطفاً آن را در"
        " پیام‌های ذخیره‌شده (Saved Messages) فوروارد یا ذخیره کنید! ⏳"
    )
    redownload_text = "📥 در صورت پاک شدن، از دکمه‌ی زیر استفاده کنید 👇"
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            "♻️ دانلود مجدد فیلم", callback_data=f"redownload_{start_param}"
        )
    )
    msg1 = bot.send_message(chat_id, warning_text, parse_mode="Markdown")
    msg2 = bot.send_message(chat_id, redownload_text, reply_markup=markup)

    def auto_delete():
      time.sleep(10)
      try:
        bot.delete_message(chat_id, video_msg_id)
        bot.delete_message(chat_id, msg1.message_id)
        bot.delete_message(chat_id, msg2.message_id)
      except Exception:
        pass

    threading.Thread(target=auto_delete).start()
  except Exception:
    bot.send_message(
        chat_id, "❌ خطایی در ارسال فیلم رخ داد یا لینک فیلم نامعتبر است."
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("check_sub_"))
def callback_check_sub(call):
  user_id = call.from_user.id
  start_param = (
      call.data.split("_")[2] if len(call.data.split("_")) > 2 else ""
  )
  unjoined = get_unjoined_channels(user_id)
  if unjoined:
    bot.answer_callback_query(
        call.id,
        "❌ شما هنوز در تمام کانال‌های معرفی‌شده عضو نشده‌اید!",
        show_alert=True,
    )
  else:
    bot.answer_callback_query(call.id, "✅ عضویت شما با موفقیت تایید شد!")
    try:
      bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
      pass
    handle_movie_delivery(call.message.chat.id, start_param)


@bot.callback_query_handler(
    func=lambda call: call.data.startswith("redownload_")
)
def callback_redownload(call):
  start_param = call.data.split("_")[1]
  chat_id = call.message.chat.id
  bot.answer_callback_query(call.id, "♻️ در حال ارسال مجدد فیلم...")
  handle_movie_delivery(chat_id, start_param)


@bot.message_handler(commands=["panel"])
def admin_panel(message):
  if message.from_user.id != ADMIN_ID:
    return
  markup = InlineKeyboardMarkup()
  markup.add(InlineKeyboardButton("📊 آمار کاربران", callback_data="admin_stats"))
  markup.add(
      InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast")
  )
  markup.add(
      InlineKeyboardButton("➕ افزودن کانال جوین", callback_data="admin_add_chan")
  )
  markup.add(
      InlineKeyboardButton("➖ حذف کانال جوین", callback_data="admin_del_chan")
  )
  bot.reply_to(
      message,
      "⚙️ **پنل مدیریت پیشرفته ربات**\n\nلطفاً گزینه مورد نظر را انتخاب کنید:",
      reply_markup=markup,
      parse_mode="Markdown",
  )


@bot.callback_query_handler(
    func=lambda call: call.data
    in [
        "admin_stats",
        "admin_broadcast",
        "admin_add_chan",
        "admin_del_chan",
        "list_for_del",
    ]
    or call.data.startswith("delchan_")
)
def admin_buttons(call):
  if call.from_user.id != ADMIN_ID:
    bot.answer_callback_query(call.id, "❌ شما دسترسی ندارید!", show_alert=True)
    return

  if call.data == "admin_stats":
    total_users = len(users_database)
    bot.answer_callback_query(call.id, f"👥 تعداد کل کاربران: {total_users}")
    bot.edit_message_text(
        f"📊 **آمار ربات شما:**\n\n👥 تعداد کل کاربران ربات: `{total_users}` نفر",
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown",
    )

  elif call.data == "admin_broadcast":
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        "📢 لطفاً پیام خود را برای ارسال همگانی به تمام کاربران بفرستید:",
    )
    bot.register_next_step_handler(msg, process_broadcast)

  elif call.data == "admin_add_chan":
    bot.answer_callback_query(call.id)
    msg = bot.send_message(
        call.message.chat.id,
        (
            "➕ لطفاً یوزرنیم کانال جدید را با علامت @ بفرستید (مثلا:"
            " `@my_channel`):"
        ),
    )
    bot.register_next_step_handler(msg, process_add_channel)

  elif call.data == "admin_del_chan":
    bot.answer_callback_query(call.id)
    if not CHANNELS:
      bot.send_message(call.message.chat.id, "❌ هیچ کانالی در لیست وجود ندارد.")
      return
    markup = InlineKeyboardMarkup()
    for ch in CHANNELS:
      markup.add(
          InlineKeyboardButton(f"🗑 حذف {ch}", callback_data=f"delchan_{ch}")
      )
    bot.send_message(
        call.message.chat.id,
        "➖ روی کانالی که می‌خواهید حذف شود بزنید:",
        reply_markup=markup,
    )

  elif call.data.startswith("delchan_"):
    ch_to_remove = call.data.replace("delchan_", "")
    if ch_to_remove in CHANNELS:
      CHANNELS.remove(ch_to_remove)
      bot.answer_callback_query(
          call.id, f"✅ کانال {ch_to_remove} با موفقیت حذف شد!"
      )
      bot.edit_message_text(
          f"✅ کانال **{ch_to_remove}** از لیست جوین اجباری حذف شد.\n\nلیست"
          f" فعلی کانال‌ها: `{CHANNELS}`",
          call.message.chat.id,
          call.message.message_id,
          parse_mode="Markdown",
      )
    else:
      bot.answer_callback_query(call.id, "❌ کانال مورد نظر پیدا نشد!")


def process_add_channel(message):
  if message.from_user.id != ADMIN_ID:
    return
  new_chan = message.text.strip()
  if not new_chan.startswith("@"):
    bot.send_message(
        message.chat.id,
        "❌ یوزرنیم باید با `@` شروع شود. دوباره از طریق پنل تلاش کنید.",
    )
    return
  if new_chan in CHANNELS:
    bot.send_message(message.chat.id, "⚠️ این کانال از قبل در لیست وجود دارد!")
    return
  CHANNELS.append(new_chan)
  bot.send_message(
      message.chat.id,
      f"✅ کانال **{new_chan}** با موفقیت به لیست جوین اجباری اضافه"
      f" شد!\n\nلیست جدید کانال‌ها: `{CHANNELS}`",
      parse_mode="Markdown",
  )


def process_broadcast(message):
  if message.from_user.id != ADMIN_ID:
    return
  broadcast_text = message.text
  success = 0
  failed = 0
  status_msg = bot.send_message(
      message.chat.id, "⏳ در حال ارسال پیام همگانی..."
  )
  for user_id in users_database:
    try:
      bot.send_message(user_id, broadcast_text)
      success += 1
      time.sleep(0.1)
    except Exception:
      failed += 1
  bot.edit_message_text(
      f"✅ **ارسال همگانی به پایان رسید!**\n\n📤 ارسال شده:"
      f" {success}\n❌ ناموفق (بلاک کرده‌اند): {failed}",
      message.chat.id,
      status_msg.message_id,
      parse_mode="Markdown",
  )


if __name__ == "__main__":
  print("Ultimate Bot is running successfully...")
  bot.infinity_polling()
