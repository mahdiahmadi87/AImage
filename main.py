from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, ConversationHandler
from together import Together
from dotenv import load_dotenv
from pathlib import Path
import base64
import io
import os                                                                                                                                                                                                          

load_dotenv(Path(".env"))

# States for conversation handler
WAITING_FOR_PROMPT = 1

# Replace these with your actual values
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

# Initialize Together API client
together_client = Together(api_key=TOGETHER_API_KEY)

async def check_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is a member of the specified channel"""
    try:
        user_id = update.effective_user.id
        chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    if not await check_channel_membership(update, context):
        keyboard = [[InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "برای استفاده از ربات، لطفاً ابتدا در کانال ما عضو شوید:",
            reply_markup=reply_markup
        )
        return

    keyboard = [[InlineKeyboardButton("ساخت تصویر", callback_data='create_image')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "به ربات تولید تصویر خوش آمدید! 🎨\n"
        "این ربات می‌تواند بر اساس توضیحات شما تصاویر زیبایی تولید کند.\n"
        "برای شروع، روی دکمه زیر کلیک کنید:",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()

    if not await check_channel_membership(update, context):
        keyboard = [[InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "برای استفاده از ربات، لطفاً ابتدا در کانال ما عضو شوید:",
            reply_markup=reply_markup
        )
        return

    if query.data == 'create_image':
        await query.edit_message_text(
            "لطفاً توضیحات تصویر مورد نظر خود را به انگلیسی وارد کنید:"
        )
        return WAITING_FOR_PROMPT

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate image based on user prompt"""
    if not await check_channel_membership(update, context):
        keyboard = [[InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "برای استفاده از ربات، لطفاً ابتدا در کانال ما عضو شوید:",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    await update.message.reply_text("در حال تولید تصویر... لطفاً صبور باشید ⏳")

    try:
        response = together_client.images.generate(
            prompt=str(update.message.text),
            model="black-forest-labs/FLUX.1-schnell",
            width=1024,
            height=768,
            steps=4,
            n=1,
            response_format="b64_json"
        )
        # Convert base64 to image and send
        image_data = base64.b64decode(response.data[0].b64_json)
        bio = io.BytesIO(image_data)
        bio.name = 'generated_image.png'
        await update.message.reply_photo(
            photo=bio,
            caption="تصویر شما آماده شد! 🎨\nبرای ساخت تصویر جدید از دستور /start استفاده کنید."
        )
    except Exception as e:
        await update.message.reply_text(
            "متأسفانه در تولید تصویر خطایی رخ داد. لطفاً دوباره تلاش کنید."
        )
        print(e)

    return ConversationHandler.END
def main():
    """Start the bot"""
    application = Application.builder().token(BOT_TOKEN).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CallbackQueryHandler(button_callback)
        ],
        states={
            WAITING_FOR_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image)]
        },
        fallbacks=[CommandHandler('start', start)]
    )

    application.add_handler(conv_handler)

    # Start the bot
    application.run_polling()

if __name__ == '__main__':
    main()