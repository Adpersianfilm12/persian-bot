import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# تنظیمات اصلی
TOKEN = "8927708021:AAHrf_3fXFbewPqx_ZWDqO1t9Ii5AHEXNIw"
ADMIN_ID = 7067751062
ARCHIVE_CHANNEL_ID = -1003965313357

logging.basicConfig(level=logging.INFO)
router = Router()

# دیتابیس برای ذخیره کاربران و کانال‌های اجباری
db = sqlite3.connect("bot_database.db", check_same_thread=False)
cursor = db.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS forced_channels (
    channel_username TEXT PRIMARY KEY
)
""")
db.commit()

# افزودن کانال‌های پیش‌فرض اگر در دیتابیس نباشند
default_channels = ["@persians_film", "@persians_serial"]
for ch in default_channels:
  cursor.execute(
      "INSERT OR IGNORE INTO forced_channels (channel_username) VALUES (?)",
      (ch,),
  )
db.commit()


# حالت‌های FSM برای پنل مدیریت
class AdminStates(StatesGroup):
  waiting_for_broadcast = State()
  waiting_for_add_channel = State()
  waiting_for_del_channel = State()


# تابع بررسی عضویت کاربر در کانال‌های اجباری
async def check_user_membership(bot: Bot, user_id: int) -> bool:
  cursor.execute("SELECT channel_username FROM forced_channels")
  channels = [row[0] for row in cursor.fetchall()]

  for channel in channels:
    try:
      member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
      if member.status in ["left", "kicked"]:
        return False
    except Exception:
      # اگر ربات نتواند وضعیت را چک کند (مثلاً ربات ادمین نباشد)، برای احتیاط False برمی‌گرداند
      return False
  return True


# دکمه‌های شیشه‌ای عضویت اجباری
async def get_join_keyboard() -> InlineKeyboardMarkup:
  cursor.execute("SELECT channel_username FROM forced_channels")
  channels = [row[0] for row in cursor.fetchall()]

  keyboard = []
  for i, ch in enumerate(channels, start=1):
    keyboard.append(
        [InlineKeyboardButton(text=f"عضویت در کانال {i} 📢", url=f"https://t.me/{ch.lstrip('@')}")]
    )

  keyboard.append(
      [InlineKeyboardButton(text="🔄 بررسی عضویت", callback_data="check_membership")]
  )
  return InlineKeyboardMarkup(inline_keyboard=keyboard)


# دستور شروع /start
@router.message(Command("start"))
async def cmd_start(message: Message, bot: Bot):
  user_id = message.from_user.id

  # ثبت کاربر در دیتابیس
  cursor.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
  db.commit()

  # بررسی عضویت اجباری
  is_member = await check_user_membership(bot, user_id)
  if not is_member:
    await message.answer(
        "❌ برای استفاده از ربات، لطفاً ابتدا در کانال‌های زیر عضو شوید:",
        reply_markup=await get_join_keyboard(),
    )
    return

  # اگر کاربر فیلمی درخواست کرده باشد (Deep Linking) یا استارت معمولی باشد
  args = message.text.split()
  if len(args) > 1:
    file_identifier = args[1]
    await send_archive_file(message, bot, file_identifier)
  else:
    await message.answer(
        "سلام! به ربات فیلم و سریال خوش آمدید. لینک یا کد دانلود خود را ارسال"
        " کنید."
    )


# کال‌بک بررسی عضویت
@router.callback_query(F.data == "check_membership")
async def callback_check_membership(callback: CallbackQuery, bot: Bot):
  user_id = callback.from_user.id
  is_member = await check_user_membership(bot, user_id)

  if is_member:
    await callback.message.delete()
    await callback.message.answer(
        "✅ عضویت شما تایید شد! حالا می‌توانید از ربات استفاده کنید."
    )
  else:
    await callback.answer(
        "❌ هنوز در تمام کانال‌ها عضو نشده‌اید! لطفاً عضو شوید.", show_alert=True
    )


# تابع ارسال فیلم از کانال آرشیو همراه با مکانیزم پاک شدن ۱۰ ثانیه‌ای
async def send_archive_file(message: Message, bot: Bot, file_id_or_msg_id: str):
  try:
    # کپی کردن پست از کانال آرشیو به کاربر
    forwarded_msg = await bot.copy_message(
        chat_id=message.chat.id,
        from_chat_id=ARCHIVE_CHANNEL_ID,
        message_id=int(file_id_or_msg_id),
    )

    # ارسال پیام هشدار پاک شدن
    warning_msg = await message.answer(
        "پیام‌ها و فایل‌های بالا به زودی پاک خواهند شد، لطفاً آن‌ها را ذخیره کنید! ⏳"
    )

    # ارسال پیام دانلود مجدد
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(
                text="📥 دانلود مجدد",
                callback_data=f"redownload_{file_id_or_msg_id}",
            )
        ]]
    )
    download_msg = await message.answer(
        "برای دانلود مجدد، می توانید از دکمه زیر استفاده کنید! ⚡",
        reply_markup=keyboard,
    )

    # تایمر ۱۰ ثانیه‌ای برای حذف فایل و پیام‌های مربوطه
    await asyncio.sleep(10)

    try:
      await forwarded_msg.delete()
      await warning_msg.delete()
      await download_msg.delete()
    except Exception:
      pass

  except Exception as e:
    await message.answer("❌ خطا در دریافت فایل یا فیلم مورد نظر!")


# دکمه شیشه‌ای دانلود مجدد
@router.callback_query(F.data.startswith("redownload_"))
async def callback_redownload(callback: CallbackQuery, bot: Bot):
  file_msg_id = callback.data.split("_")[1]
  await callback.answer()
  await send_archive_file(callback.message, bot, file_msg_id)


# دریافت متن یا لینک‌های ارسالی از طرف کاربر برای دریافت فیلم
@router.message(F.text & ~F.text.startswith("/"))
async def handle_user_text(message: Message, bot: Bot):
  user_id = message.from_user.id
  is_member = await check_user_membership(bot, user_id)

  if not is_member:
    await message.answer(
        "❌ برای استفاده از ربات، لطفاً ابتدا در کانال‌های زیر عضو شوید:",
        reply_markup=await get_join_keyboard(),
    )
    return

  # فرض بر این است که متن ارسالی کاربر، همان آیدی یا شماره پیام در کانال آرشیو است
  text = message.text.strip()
  if text.isdigit():
    await send_archive_file(message, bot, text)
  else:
    await message.answer(
        "لطفاً کد عددی فیلم مورد نظر یا لینک صحیح را ارسال کنید."
    )


# پنل مدیریت ربات (/admin یا /panel)
@router.message(Command("admin", "panel"))
async def cmd_admin(message: Message):
  if message.from_user.id != ADMIN_ID:
    return

  cursor.execute("SELECT COUNT(*) FROM users")
  total_users = cursor.fetchone()[0]

  cursor.execute("SELECT channel_username FROM forced_channels")
  channels = [row[0] for row in cursor.fetchall()]
  channels_text = "\n".join([f"🔹 {ch}" for ch in channels])

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [InlineKeyboardButton(text="📢 ارسال همگانی", callback_data="admin_broadcast")],
          [InlineKeyboardButton(text="➕ افزودن کانال اجباری", callback_data="admin_add_ch")],
          [InlineKeyboardButton(text="➖ حذف کانال اجباری", callback_data="admin_del_ch")],
      ]
  )

  await message.answer(
      f"📊 **پنل مدیریت پیشرفته ربات**\n\n👥 تعداد کل کاربران: `{total_users}`\n\n📌"
      f" کانال‌های جوین اجباری:\n{channels_text}",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )


# مدیریت دکمه‌های پنل ادمین
@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
  if callback.from_user.id != ADMIN_ID:
    return
  await callback.message.answer(
      "پیام خود را برای ارسال همگانی به تمامی کاربران بفرستید:"
  )
  await state.set_state(AdminStates.waiting_for_broadcast)
  await callback.answer()


@router.message(AdminStates.waiting_for_broadcast)
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
  if message.from_user.id != ADMIN_ID:
    return

  cursor.execute("SELECT user_id FROM users")
  users = cursor.fetchall()
  await state.clear()

  sent_count = 0
  status_msg = await message.answer("⏳ در حال ارسال پیام همگانی...")

  for (u_id,) in users:
    try:
      await message.copy_to(chat_id=u_id)
      sent_count += 1
      await asyncio.sleep(0.05)  # جلوگیری از فلود شدن تلگرام
    except Exception:
      pass

  await status_msg.edit_text(f"✅ پیام همگانی با موفقیت به {sent_count} کاربر ارسال شد.")


@router.callback_query(F.data == "admin_add_ch")
async def admin_add_channel_start(callback: CallbackQuery, state: FSMContext):
  if callback.from_user.id != ADMIN_ID:
    return
  await callback.message.answer(
      "یوزرنیم کانال جدید را با علامت @ بفرستید (مثال: `@persians_new`):"
  )
  await state.set_state(AdminStates.waiting_for_add_channel)
  await callback.answer()


@router.message(AdminStates.waiting_for_add_channel)
async def process_add_channel(message: Message, state: FSMContext):
  if message.from_user.id != ADMIN_ID:
    return
  new_ch = message.text.strip()
  if not new_ch.startswith("@"):
    await message.answer("❌ فرمت اشتباه است. باید با @ شروع شود.")
    return

  try:
    cursor.execute(
        "INSERT INTO forced_channels (channel_username) VALUES (?)", (new_ch,)
    )
    db.commit()
    await state.clear()
    await message.answer(f"✅ کانال `{new_ch}` با موفقیت به لیست اضافه شد.")
  except Exception:
    await message.answer("❌ این کانال از قبل در لیست وجود دارد.")


@router.callback_query(F.data == "admin_del_ch")
async def admin_del_channel_start(callback: CallbackQuery, state: FSMContext):
  if callback.from_user.id != ADMIN_ID:
    return
  cursor.execute("SELECT channel_username FROM forced_channels")
  channels = [row[0] for row in cursor.fetchall()]

  keyboard = []
  for ch in channels:
    keyboard.append([InlineKeyboardButton(text=f"حذف {ch}", callback_data=f"delch_{ch}")])

  await callback.message.answer(
      "کانالی که می‌خواهید حذف کنید را انتخاب کنید:",
      reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
  )
  await state.set_state(AdminStates.waiting_for_del_channel)
  await callback.answer()


@router.callback_query(F.data.startswith("delch_"))
async def process_delete_channel(callback: CallbackQuery, state: FSMContext):
  if callback.from_user.id != ADMIN_ID:
    return
  ch_to_delete = callback.data.replace("delch_", "")

  cursor.execute(
      "DELETE FROM forced_channels WHERE channel_username = ?", (ch_to_delete,)
  )
  db.commit()
  await state.clear()
  await callback.message.edit_text(
      f"✅ کانال `{ch_to_delete}` با موفقیت از لیست حذف شد."
  )


# اجرای اصلی ربات
async def main():
  bot = Bot(token=TOKEN)
  dp = Dispatcher()
  dp.include_router(router)
  await bot.delete_webhook(drop_pending_updates=True)
  print("Bot is running...")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
