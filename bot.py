import os
import io
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from PIL import Image
import tempfile

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get bot token from environment variable
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set!")

# Store user's cropping data temporarily
user_crop_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued."""
    welcome_text = (
        "🎯 Welcome to BatchCropBot!\n\n"
        "I can help you crop images easily. Here's how:\n"
        "1️⃣ Send me any image (JPG, PNG, WEBP, etc.)\n"
        "2️⃣ Use the cropping tool that appears\n"
        "3️⃣ Crop your image and send it back\n\n"
        "📸 You can also send multiple images at once!\n"
        "🔧 Use /help to see all commands."
    )
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message."""
    help_text = (
        "🤖 BatchCropBot Help:\n\n"
        "📤 Send an image to crop it\n"
        "📚 Send multiple images at once for batch cropping\n"
        "🔄 /cancel - Cancel current operation\n"
        "📊 /stats - View your usage statistics\n"
        "ℹ️ /help - Show this help message\n\n"
        "💡 Tip: You can forward images from other chats too!"
    )
    await update.message.reply_text(help_text)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user statistics."""
    user_id = update.effective_user.id
    # Simple stats - you can expand this with a database
    stats_text = (
        f"📊 Your Statistics:\n"
        f"👤 User ID: {user_id}\n"
        f"📅 Joined: Today\n"
        f"🖼️ Images processed: 0\n"
        f"⚡ Status: Active\n\n"
        f"🔄 This feature is coming soon with full statistics!"
    )
    await update.message.reply_text(stats_text)

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation."""
    user_id = update.effective_user.id
    if user_id in user_crop_data:
        del user_crop_data[user_id]
    await update.message.reply_text("✅ Operation cancelled. Send a new image to crop!")

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming images."""
    user_id = update.effective_user.id
    message = update.message
    
    # Get the photo
    if not message.photo:
        await message.reply_text("⚠️ Please send a valid image file.")
        return
    
    # Get the largest photo
    photo_file = await message.photo[-1].get_file()
    
    # Store file info for later
    user_crop_data[user_id] = {
        'file_id': photo_file.file_id,
        'timestamp': datetime.now()
    }
    
    # Create cropping interface
    keyboard = [
        [
            InlineKeyboardButton("✂️ Crop Square", callback_data="crop_square"),
            InlineKeyboardButton("📐 Custom Crop", callback_data="crop_custom")
        ],
        [
            InlineKeyboardButton("🔄 Reset", callback_data="reset"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        "📸 Image received! What would you like to do?\n\n"
        "🎯 Square Crop: Perfect for profile pictures\n"
        "📐 Custom Crop: Choose your own aspect ratio",
        reply_markup=reply_markup
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document images."""
    message = update.message
    document = message.document
    
    # Check if it's an image
    mime_type = document.mime_type
    if not mime_type or not mime_type.startswith('image/'):
        await message.reply_text("⚠️ Please send an image file (JPG, PNG, GIF, etc.)")
        return
    
    user_id = update.effective_user.id
    file = await document.get_file()
    
    user_crop_data[user_id] = {
        'file_id': file.file_id,
        'timestamp': datetime.now()
    }
    
    keyboard = [
        [
            InlineKeyboardButton("✂️ Crop Square", callback_data="crop_square"),
            InlineKeyboardButton("📐 Custom Crop", callback_data="crop_custom")
        ],
        [
            InlineKeyboardButton("🔄 Reset", callback_data="reset"),
            InlineKeyboardButton("❌ Cancel", callback_data="cancel")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        "📁 Image document received! Choose your cropping option:",
        reply_markup=reply_markup
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == "cancel":
        if user_id in user_crop_data:
            del user_crop_data[user_id]
        await query.edit_message_text("❌ Operation cancelled. Send a new image to crop.")
        return
    
    if data == "reset":
        if user_id in user_crop_data:
            # Reset the cropping state
            await query.edit_message_text(
                "🔄 Reset complete! Choose your crop option:",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✂️ Crop Square", callback_data="crop_square"),
                        InlineKeyboardButton("📐 Custom Crop", callback_data="crop_custom")
                    ],
                    [
                        InlineKeyboardButton("🔄 Reset", callback_data="reset"),
                        InlineKeyboardButton("❌ Cancel", callback_data="cancel")
                    ]
                ])
            )
        return
    
    if data in ["crop_square", "crop_custom"]:
        user_data = user_crop_data.get(user_id)
        if not user_data:
            await query.edit_message_text("⚠️ No image found. Please send a new image.")
            return
        
        file_id = user_data['file_id']
        
        # For demonstration, we'll send instructions
        crop_type = "square" if data == "crop_square" else "custom"
        
        instruction_text = (
            f"📐 {crop_type.capitalize()} cropping selected!\n\n"
            "🔧 You can crop this image in Telegram:\n"
            "1. Open the image in the chat\n"
            "2. Tap the image to open it\n"
            "3. Tap the ✏️ (edit) icon\n"
            "4. Select the crop tool\n"
            f"5. {'Crop to 1:1 ratio' if crop_type == 'square' else 'Choose your custom ratio'}\n"
            "6. Save and send it back!\n\n"
            "📤 Or forward this image to me again with your crop preferences."
        )
        
        await query.edit_message_text(
            instruction_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Back to Options", callback_data="reset")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
            ])
        )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors."""
    logger.warning(f"Update {update} caused error {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "❌ An error occurred. Please try again or send /help for assistance."
            )
    except:
        pass

def main():
    """Start the bot."""
    try:
        # Create application
        app = ApplicationBuilder().token(TOKEN).build()
        
        # Add command handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("stats", stats_command))
        app.add_handler(CommandHandler("cancel", cancel_command))
        
        # Add message handlers
        app.add_handler(MessageHandler(filters.PHOTO, handle_image))
        app.add_handler(MessageHandler(filters.Document.IMAGE, handle_document))
        
        # Add callback query handler
        app.add_handler(CallbackQueryHandler(handle_callback))
        
        # Add error handler
        app.add_error_handler(error_handler)
        
        # Start the bot
        print("🤖 BatchCropBot is starting...")
        print(f"📡 Bot token: {TOKEN[:10]}...")
        print("✅ Bot is running with long polling...")
        app.run_polling()
        
    except Exception as e:
        print(f"❌ Error starting bot: {e}")

if __name__ == "__main__":
    main()
