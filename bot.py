import os
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# تنظیمات لاگ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# اطلاعات ربات و ادمین (توکن اصلاح شد)
BOT_TOKEN = "8927708021:AAHduY6KITYe8fbtSN_rATlI0xG9cBgmvUc"  # توکن درست شما
ADMIN_ID = 7067751062                                         # آیدی عددی ادمین
ARCHIVE_CHANNEL_ID = -1003965313357                         # آیدی کانال آرشیو

# لیست اولیه کانال‌های جوین اجباری (قابل مدیریت از پنل)
REQUIRED_CHANNELS = ["@PersianFilmAds"]

# سرور وب بسیار سبک برای گول زدن رندر و جلوگیری از خطای Timeout
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is active and running!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# بررسی عضویت کاربر در کانال‌های اجباری
async def check_subscription(user_id, context):
    for channel in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False
        except Exception:
            # اگر کانال عمومی نباشد یا ربات دسترسی نداشته باشد
            pass
    return True

# دستور استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # بررسی جوین اجباری
    is_subscribed = await check_subscription(user_id, context)
    if not is_subscribed:
        keyboard = [[InlineKeyboardButton(" عضویت در کانال", url=f"https://t.me/{REQUIRED_CHANNELS[0].replace('@', '')}")],
                    [InlineKeyboardButton("✅ عضو شدم", callback_data="check_sub")]]
        await update.message.reply_text(
            "⚠️ برای استفاده از ربات، لطفاً ابتدا در کانال زیر عضو شوید و سپس روی دکمه «عضو شدم» بزنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await update.message.reply_text("سلام! خوش آمدید. فیلم موردنظر خود را ارسال کنید یا از امکانات ربات استفاده کنید.")

# دکمه بررسی عضویت
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "check_sub":
        user_id = query.from_user.id
        is_subscribed = await check_subscription(user_id, context)
        if is_subscribed:
            await query.edit_message_text("عضویت شما تایید شد! اکنون می‌توانید از ربات استفاده کنید. دستور /start را بفرستید.")
        else:
            await query.answer("هنوز در کانال عضو نشده‌اید!", show_alert=True)
            
    elif query.data == "admin_add_chan":
        if query.from_user.id == ADMIN_ID:
            await query.edit_message_text("برای افزودن کانال، دستور زیر را ارسال کنید:\n`/addchan @username`", parse_mode="Markdown")
            
    elif query.data == "admin_del_chan":
        if query.from_user.id == ADMIN_ID:
            channels_text = "\n".join(REQUIRED_CHANNELS)
            await query.edit_message_text(f"کانال‌های فعلی:\n{channels_text}\n\nبرای حذف دستور زیر را بفرستید:\n`/delchan @username`", parse_mode="Markdown")

# پنل مدیریت ادمین
async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    
    keyboard = [
        [InlineKeyboardButton("📊 آمار کاربران", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 ارسال پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton("➕ افزودن کانال جوین", callback_data="admin_add_chan")],
        [InlineKeyboardButton("➖ حذف کانال جوین", callback_data="admin_del_chan")]
    ]
    await update.message.reply_text("⚙️ پنل مدیریت پیشرفته ربات:\n\nلطفاً گزینه مورد نظر را انتخاب کنید:", reply_markup=InlineKeyboardMarkup(keyboard))

# دستورات افزودن و حذف کانال
async def add_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if context.args:
        new_chan = context.args[0]
        if new_chan not in REQUIRED_CHANNELS:
            REQUIRED_CHANNELS.append(new_chan)
            await update.message.reply_text(f"✅ کانال {new_chan} با موفقیت به لیست جوین اجباری اضافه شد.")
        else:
            await update.message.reply_text("⚠️ این کانال از قبل در لیست وجود دارد.")
    else:
        await update.message.reply_text("لطفاً آیدی کانال را وارد کنید:\nمثال: `/addchan @channel`", parse_mode="Markdown")

async def del_channel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if context.args:
        target_chan = context.args[0]
        if target_chan in REQUIRED_CHANNELS:
            REQUIRED_CHANNELS.remove(target_chan)
            await update.message.reply_text(f"🗑 کانال {target_chan} از لیست حذف شد.")
        else:
            await update.message.reply_text("⚠️ این کانال در لیست پیدا نشد.")
    else:
        await update.message.reply_text("لطفاً آیدی کانال را وارد کنید:\nمثال: `/delchan @channel`", parse_mode="Markdown")

def main():
    # اجرای وب‌سایت صوری در یک نخ جداگانه برای جلوگیری از خطای Timeout در رندر
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    # راه‌اندازی ربات تلگرام
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("panel", panel))
    application.add_handler(CommandHandler("addchan", add_channel_cmd))
    application.add_handler(CommandHandler("delchan", del_channel_cmd))
    application.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is starting...")
    application.run_polling()

if __name__ == '__main__':
    main()
