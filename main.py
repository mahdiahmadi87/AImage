import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters, ConversationHandler
from together import Together

WAITING_FOR_PROMPT = 1


TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = os.getenv("ADMIN_ID")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
TOGETHER_API_KEY = os.getenv("TOGETHER_API_KEY")

together_client = Together(api_key=TOGETHER_API_KEY)



async def check_channel_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user is a member of the required channel"""
    try:
        user = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=update.effective_user.id)
        return user.status in ['member', 'administrator', 'creator']
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    if not await check_channel_membership(update, context):
        keyboard = [[InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "برای استفاده از ربات، لطفا ابتدا در کانال ما عضو شوید:",
            reply_markup=reply_markup
        )
        return

    keyboard = [[InlineKeyboardButton("ساخت تصویر", callback_data='create_image')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "به ربات تولید تصویر خوش آمدید!\n"
        "این ربات می‌تواند بر اساس توضیحات شما تصاویر جذابی تولید کند.\n"
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
        await query.message.reply_text(
            "برای استفاده از ربات، لطفا ابتدا در کانال ما عضو شوید:",
            reply_markup=reply_markup
        )
        return ConversationHandler.END

    if query.data == 'create_image':
        await query.message.reply_text("لطفاً توضیحات تصویر مورد نظر خود را وارد کنید:")
        return WAITING_FOR_PROMPT

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle image generation based on user prompt"""
    user_prompt = update.message.text
    user_id = update.effective_user.id

    # Notify user that processing has started
    await update.message.reply_text("در حال پردازش درخواست شما...")

    try:
        # Translate prompt if it's in Persian
        translation_response = together_client.chat.completions.create(
            model="meta-llama/Llama-3-8b-chat-hf",
            messages=[
                {"role": "system", "content": "You are an AI assistant. Your job is to translate Persian prompts into English prompts that are suitable for the 'flux schnell' image generation model. Ensure the output is concise and only contains the translated prompt, without any extra text."},
                {"role": "user", "content": user_prompt},
            ],
        )
        
        translated_prompt = translation_response.choices[0].message.content

        # Generate image
        image_response = together_client.images.generate(
            prompt=translated_prompt,
            model="black-forest-labs/FLUX.1-schnell",
            width=1024,
            height=768,
            steps=4,
            n=1,
            response_format="b64_json"
        )

        # Send image to user
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=image_response.data[0].b64_json
        )

        # Send notification to admin
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"New image generated:\nUser ID: {user_id}\nPrompt: {user_prompt}\nTranslated: {translated_prompt}"
        )

        # Ask if user wants to create another image
        keyboard = [[InlineKeyboardButton("ساخت تصویر جدید", callback_data='create_image')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "تصویر شما با موفقیت ساخته شد! آیا می‌خواهید تصویر دیگری بسازید؟",
            reply_markup=reply_markup
        )

    except Exception as e:
        await update.message.reply_text("متأسفانه در ساخت تصویر مشکلی پیش آمد. لطفاً دوباره تلاش کنید.")
        print(f"Error: {str(e)}")

    return ConversationHandler.END

def main():
    """Start the bot"""
    application = Application.builder().token(TOKEN).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CallbackQueryHandler(button_callback)
        ],
        states={
            WAITING_FOR_PROMPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_image)]
        },
        fallbacks=[],
    )

    application.add_handler(conv_handler)
    
    # Start the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()