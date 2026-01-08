"""Telegram Video Editor Bot - Main bot logic - Production Optimized"""

import os
import shutil
from datetime import datetime
from enum import Enum
import logging
import traceback

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    Application, ConversationHandler, MessageHandler,
    CommandHandler, ContextTypes, filters
)
from telegram.constants import ChatAction

from config import (
    BOT_TOKEN, TEMP_DIR, LOGO_PATH, SUPPORTED_IMAGE_FORMATS,
    SUPPORTED_VIDEO_FORMATS, MAX_IMAGE_SIZE, MAX_VIDEO_SIZE, 
    MAX_TOTAL_SESSION, DEBUG_KEEP_TEMP
)
from image_processor import (
    create_headline_banner, create_image_collage, create_static_frame
)
from video_composer import compose_final_video, check_ffmpeg_installed

# Enable logging with more detail
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ensure temp directory exists
os.makedirs(TEMP_DIR, exist_ok=True)

# Conversation states
WAITING_HEADLINE = 1
WAITING_IMAGES = 2
WAITING_VIDEO = 3
PROCESSING = 4


class BotSession:
    """Store user session data with size tracking"""
    def __init__(self):
        self.headline = None
        self.images = []
        self.video = None
        self.user_id = None
        self.temp_dir = None
        self.total_size = 0  # Track total session size
    
    def create_temp_dir(self):
        """Create user-specific temp directory"""
        self.temp_dir = os.path.join(TEMP_DIR, f"user_{self.user_id}_{datetime.now().timestamp()}")
        os.makedirs(self.temp_dir, exist_ok=True)
        logger.info(f"Created temp dir: {self.temp_dir}")
    
    def cleanup(self):
        """Clean up temp files"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                if DEBUG_KEEP_TEMP:
                    logger.info(f"Keeping temp files for debugging: {self.temp_dir}")
                else:
                    shutil.rmtree(self.temp_dir)
                    logger.info(f"Cleaned up temp dir: {self.temp_dir}")
            except Exception as e:
                logger.error(f"Error cleaning up temp dir: {e}")
    
    def add_file_size(self, size_bytes):
        """Track file size"""
        self.total_size += size_bytes
        if self.total_size > MAX_TOTAL_SESSION * (1024 * 1024):
            raise Exception(f"Session size exceeded {MAX_TOTAL_SESSION}MB limit")


class ConvState(Enum):
    WAITING_HEADLINE = 1
    WAITING_IMAGES = 2
    WAITING_VIDEO = 3
    PROCESSING = 4


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and ask for headline"""
    
    try:
        # Check FFmpeg availability
        if not check_ffmpeg_installed():
            await update.message.reply_text(
                "❌ <b>System Error</b>\n\n"
                "FFmpeg is not installed on the server.\n"
                "The admin needs to install FFmpeg to enable video processing.\n\n"
                "Contact: @admin"
            )
            return ConversationHandler.END
        
        # Initialize session
        session = BotSession()
        session.user_id = update.effective_user.id
        session.create_temp_dir()
        context.user_data['session'] = session
        
        logger.info(f"User {session.user_id} started bot")
        
        welcome_text = (
            "🎬 <b>Instagram Video Editor</b> 🎬\n\n"
            "Create professional Instagram videos (1080x1350px) with:\n"
            "✅ Headline text\n"
            "✅ Image collage (auto-stacking)\n"
            "✅ Video clip\n"
            "✅ Logo watermark\n\n"
            "<b>⚡ Features:</b>\n"
            "• AI upscaling for quality\n"
            "• Fast processing\n"
            "• High quality output\n\n"
            "📝 Send your headline text:"
        )
        
        await update.message.reply_text(welcome_text, parse_mode='HTML')
        return WAITING_HEADLINE
        
    except Exception as e:
        logger.error(f"Error in start: {e}\n{traceback.format_exc()}")
        await update.message.reply_text("❌ Error starting bot. Please try again.")
        return ConversationHandler.END


async def receive_headline(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive headline text"""
    
    try:
        session = context.user_data.get('session')
        if not session:
            await update.message.reply_text("❌ Session error. Please /start again")
            return ConversationHandler.END
        
        session.headline = update.message.text.strip()
        
        if not session.headline or len(session.headline) < 1:
            await update.message.reply_text("⚠️ Please provide a valid headline text.")
            return WAITING_HEADLINE
        
        if len(session.headline) > 500:
            await update.message.reply_text("⚠️ Headline too long (max 500 chars). Try again:")
            return WAITING_HEADLINE
        
        logger.info(f"User {session.user_id} set headline: {session.headline[:50]}")
        
        confirm_text = (
            f"✅ <b>Headline saved:</b>\n\n"
            f"<i>\"{session.headline}\"</i>\n\n"
            f"📸 Now send <b>1 or more images</b> for the collage.\n"
            f"You can send them one by one.\n\n"
            f"When done:\n"
            f"• /done - Proceed to video\n"
            f"• /cancel - Start over"
        )
        
        await update.message.reply_text(confirm_text, parse_mode='HTML')
        return WAITING_IMAGES
        
    except Exception as e:
        logger.error(f"Error in receive_headline: {e}\n{traceback.format_exc()}")
        await update.message.reply_text("❌ Error processing headline. Please try again.")
        return WAITING_HEADLINE


async def proceed_to_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Proceed from images to video step"""
    
    try:
        session = context.user_data.get('session')
        if not session:
            await update.message.reply_text("❌ Session error. Please /start again")
            return ConversationHandler.END
        
        if not session.images:
            await update.message.reply_text(
                "⚠️ Please send at least 1 image before proceeding.\n"
                "Send images or /cancel to start over."
            )
            return WAITING_IMAGES
        
        logger.info(f"User {session.user_id} proceeding with {len(session.images)} images")
        
        await update.message.reply_text(
            f"✅ <b>{len(session.images)} image(s) saved!</b>\n\n"
            f"🎥 Now send your <b>video file</b> (MP4, MOV, AVI).\n"
            f"The video fills the right side of the final composition.\n\n"
            f"Max size: {MAX_VIDEO_SIZE}MB",
            parse_mode='HTML'
        )
        return WAITING_VIDEO
        
    except Exception as e:
        logger.error(f"Error in proceed_to_video: {e}\n{traceback.format_exc()}")
        await update.message.reply_text("❌ Error processing. Try /start again.")
        return ConversationHandler.END


async def receive_images(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive images for collage"""
    
    try:
        session = context.user_data.get('session')
        if not session:
            await update.message.reply_text("❌ Session error. Please /start again")
            return ConversationHandler.END
        
        # Handle photo
        if update.message.photo:
            try:
                photo_file = await update.message.photo[-1].get_file()
                
                # Check file size
                file_size_mb = photo_file.file_size / (1024 * 1024)
                if file_size_mb > MAX_IMAGE_SIZE:
                    await update.message.reply_text(
                        f"⚠️ Image too large ({file_size_mb:.1f}MB). Max: {MAX_IMAGE_SIZE}MB"
                    )
                    return WAITING_IMAGES
                
                # Check session size
                try:
                    session.add_file_size(photo_file.file_size)
                except Exception as e:
                    await update.message.reply_text(f"⚠️ {str(e)}")
                    return WAITING_IMAGES
                
                # Download image
                image_path = os.path.join(session.temp_dir, f"image_{len(session.images):02d}.jpg")
                await photo_file.download_to_drive(image_path)
                session.images.append(image_path)
                
                logger.info(f"User {session.user_id} uploaded image {len(session.images)}")
                
                await update.message.reply_text(
                    f"✅ Image {len(session.images)} saved ({file_size_mb:.1f}MB)\n\n"
                    f"Send more or:\n"
                    f"• /done - Proceed to video\n"
                    f"• /cancel - Start over",
                    parse_mode='HTML'
                )
                return WAITING_IMAGES
                
            except Exception as e:
                logger.error(f"Error downloading image: {e}")
                await update.message.reply_text("❌ Error downloading image. Try again.")
                return WAITING_IMAGES
        
        # Handle document
        elif update.message.document:
            try:
                doc = update.message.document
                file_ext = os.path.splitext(doc.file_name)[1].lower()
                
                if file_ext not in SUPPORTED_IMAGE_FORMATS:
                    await update.message.reply_text(
                        f"⚠️ Unsupported format: {file_ext}\n"
                        f"Supported: {', '.join(SUPPORTED_IMAGE_FORMATS)}"
                    )
                    return WAITING_IMAGES
                
                file_size_mb = doc.file_size / (1024 * 1024)
                if file_size_mb > MAX_IMAGE_SIZE:
                    await update.message.reply_text(
                        f"⚠️ Image too large ({file_size_mb:.1f}MB). Max: {MAX_IMAGE_SIZE}MB"
                    )
                    return WAITING_IMAGES
                
                # Check session size
                try:
                    session.add_file_size(doc.file_size)
                except Exception as e:
                    await update.message.reply_text(f"⚠️ {str(e)}")
                    return WAITING_IMAGES
                
                file_obj = await doc.get_file()
                image_path = os.path.join(session.temp_dir, f"image_{len(session.images):02d}{file_ext}")
                await file_obj.download_to_drive(image_path)
                session.images.append(image_path)
                
                logger.info(f"User {session.user_id} uploaded image {len(session.images)}: {doc.file_name}")
                
                await update.message.reply_text(
                    f"✅ Image {len(session.images)} saved ({file_size_mb:.1f}MB)\n\n"
                    f"Send more or:\n"
                    f"• /done - Proceed to video\n"
                    f"• /cancel - Start over"
                )
                return WAITING_IMAGES
                
            except Exception as e:
                logger.error(f"Error downloading document: {e}")
                await update.message.reply_text("❌ Error downloading image. Try again.")
                return WAITING_IMAGES
        
        else:
            await update.message.reply_text(
                "⚠️ Please send an image or:\n"
                "• /done - Proceed to video\n"
                "• /cancel - Start over"
            )
            return WAITING_IMAGES
    
    except Exception as e:
        logger.error(f"Error in receive_images: {e}\n{traceback.format_exc()}")
        await update.message.reply_text("❌ Error processing image. Try again.")
        return WAITING_IMAGES


async def receive_video(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive video file"""
    
    try:
        session = context.user_data.get('session')
        if not session:
            await update.message.reply_text("❌ Session error. Please /start again")
            return ConversationHandler.END
        
        if update.message.document:
            doc = update.message.document
            file_ext = os.path.splitext(doc.file_name)[1].lower()
            
            if file_ext not in SUPPORTED_VIDEO_FORMATS:
                await update.message.reply_text(
                    f"⚠️ Unsupported format: {file_ext}\n"
                    f"Supported: {', '.join(SUPPORTED_VIDEO_FORMATS)}"
                )
                return WAITING_VIDEO
            
            file_size_mb = doc.file_size / (1024 * 1024)
            if file_size_mb > MAX_VIDEO_SIZE:
                await update.message.reply_text(
                    f"⚠️ Video too large ({file_size_mb:.1f}MB). Max: {MAX_VIDEO_SIZE}MB"
                )
                return WAITING_VIDEO
            
            # Check session size
            try:
                session.add_file_size(doc.file_size)
            except Exception as e:
                await update.message.reply_text(f"⚠️ {str(e)}")
                return WAITING_VIDEO
            
            # Notify download starting
            await update.message.chat.send_action(ChatAction.UPLOAD_VIDEO)
            await update.message.reply_text(
                "📥 Downloading video... ⏳\n"
                "(Please wait, do not send other messages)"
            )
            
            logger.info(f"User {session.user_id} uploading video: {doc.file_name} ({file_size_mb:.1f}MB)")
            
            # Download video
            file_obj = await doc.get_file()
            video_path = os.path.join(session.temp_dir, f"video{file_ext}")
            await file_obj.download_to_drive(video_path)
            session.video = video_path
            
            logger.info(f"Video download complete: {video_path}")
            
            # Start processing
            await process_video(update, context, session)
            
        else:
            await update.message.reply_text("⚠️ Please send a video file.")
            return WAITING_VIDEO
            
    except Exception as e:
        logger.error(f"Error in receive_video: {e}\n{traceback.format_exc()}")
        await update.message.reply_text(f"❌ Error downloading video: {str(e)[:100]}")
        return WAITING_VIDEO


async def process_video(update: Update, context: ContextTypes.DEFAULT_TYPE, session: BotSession) -> int:
    """Process all files and create final video"""
    
    try:
        logger.info(f"Starting video processing for user {session.user_id}")
        logger.info(f"Headline: {session.headline[:50]}")
        logger.info(f"Images: {len(session.images)}, Video: {session.video}")
        
        # Check FFmpeg
        if not check_ffmpeg_installed():
            await update.message.reply_text(
                "❌ <b>FFmpeg Error</b>\n\n"
                "FFmpeg is not available on server.\n"
                "Contact admin to install FFmpeg."
            )
            session.cleanup()
            return ConversationHandler.END
        
        # Progress: Creating headline
        await update.message.chat.send_action(ChatAction.RECORD_VIDEO)
        progress_msg = await update.message.reply_text(
            "🎬 <b>Processing your video...</b>\n\n"
            "1️⃣ Creating headline... ⏳"
        )
        
        # Step 1: Create headline banner
        logger.info("Creating headline banner...")
        headline_img = create_headline_banner(session.headline)
        
        # Progress: Creating collage
        await progress_msg.edit_text(
            "🎬 <b>Processing your video...</b>\n\n"
            "1️⃣ Creating headline... ✅\n"
            "2️⃣ Creating collage... ⏳"
        )
        
        # Step 2: Create image collage
        logger.info(f"Creating collage with {len(session.images)} images...")
        collage_img = create_image_collage(session.images)
        
        # Progress: Combining
        await progress_msg.edit_text(
            "🎬 <b>Processing your video...</b>\n\n"
            "1️⃣ Creating headline... ✅\n"
            "2️⃣ Creating collage... ✅\n"
            "3️⃣ Composing video... ⏳"
        )
        
        # Step 3: Compose final video
        output_path = os.path.join(session.temp_dir, "final_video.mp4")
        logger.info(f"Composing video: {output_path}")
        
        success = compose_final_video(
            headline_img, collage_img, session.video, LOGO_PATH, output_path
        )
        
        if not success:
            raise Exception("Video composition failed - check logs")
        
        if not os.path.exists(output_path):
            raise Exception("Output video file was not created")
        
        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        logger.info(f"Video created successfully: {file_size_mb:.1f}MB")
        
        # Progress: Uploading
        await progress_msg.edit_text(
            "🎬 <b>Processing your video...</b>\n\n"
            "1️⃣ Creating headline... ✅\n"
            "2️⃣ Creating collage... ✅\n"
            "3️⃣ Composing video... ✅\n"
            "4️⃣ Uploading... ⏳"
        )
        
        # Step 4: Send final video
        await update.message.chat.send_action(ChatAction.UPLOAD_VIDEO)
        
        with open(output_path, 'rb') as video_file:
            await update.message.reply_video(
                video=video_file,
                caption=(
                    "✅ <b>Your Instagram video is ready!</b>\n\n"
                    "📊 <b>Specs:</b>\n"
                    f"• Size: {file_size_mb:.1f}MB\n"
                    f"• Ratio: 4:5 (1080x1350)\n"
                    f"• Quality: High\n\n"
                    "💾 Download and share on Instagram!\n\n"
                    "Use /start to create another video."
                ),
                parse_mode='HTML'
            )
        
        await progress_msg.delete()
        
        logger.info(f"Video successfully sent to user {session.user_id}")
        
    except Exception as e:
        logger.error(f"Error processing video: {e}\n{traceback.format_exc()}")
        await update.message.reply_text(
            f"❌ <b>Processing Error</b>\n\n"
            f"{str(e)[:200]}\n\n"
            f"Try again with /start or contact admin if issue persists.",
            parse_mode='HTML'
        )
    
    finally:
        # Cleanup
        session.cleanup()
    
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation and cleanup"""
    
    try:
        session = context.user_data.get('session')
        if session:
            logger.info(f"User {session.user_id} cancelled")
            session.cleanup()
        
        await update.message.reply_text(
            "❌ <b>Cancelled.</b>\n\n"
            "Use /start to begin again.",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in cancel: {e}")
        await update.message.reply_text("Session ended.")
    
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message"""
    
    help_text = (
        "📖 <b>Instagram Video Editor Help</b>\n\n"
        "Create professional Instagram videos (1080x1350px) by combining:\n\n"
        "📝 <b>Headline Text</b>\n"
        "   • Top section with bold black text\n"
        "   • Auto-wraps and sizes text\n"
        "   • Max 500 characters\n\n"
        "🖼️ <b>Image Collage (Left Side)</b>\n"
        "   • 1 image: fills left side\n"
        "   • 2+ images: auto-stack vertically\n"
        "   • AI upscaling for quality\n"
        "   • Supports JPG, PNG, WEBP\n\n"
        "🎥 <b>Video (Right Side)</b>\n"
        "   • MP4, MOV, AVI formats\n"
        "   • Audio preserved\n"
        "   • Max 1000MB\n\n"
        "🔲 <b>Logo Watermark</b>\n"
        "   • Centered with 50% opacity\n"
        "   • Auto-placed over video\n\n"
        "<b>Commands:</b>\n"
        "/start - Begin creating video\n"
        "/done - Finish adding images\n"
        "/cancel - Cancel current session\n"
        "/help - Show this message\n\n"
        "<b>⚡ Features:</b>\n"
        "✓ High-quality output\n"
        "✓ Fast processing\n"
        "✓ AI image upscaling\n"
        "✓ Automatic collage layout\n"
        "✓ Professional quality"
    )
    
    await update.message.reply_text(help_text, parse_mode='HTML')


def main():
    """Start the bot - Production optimized"""
    
    print("\n" + "="*60)
    print("🤖 INSTAGRAM VIDEO EDITOR BOT")
    print("="*60)
    print(f"📍 Starting bot...")
    print(f"🔐 Token: {BOT_TOKEN[:20]}...")
    print(f"📂 Temp dir: {TEMP_DIR}")
    print(f"🎯 Logo: {LOGO_PATH}")
    print("="*60 + "\n")
    
    try:
        # Create application
        application = Application.builder().token(BOT_TOKEN).build()
        
        logger.info("Bot application created")
        
        # Conversation handler
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                WAITING_HEADLINE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receive_headline),
                    CommandHandler('cancel', cancel),
                ],
                WAITING_IMAGES: [
                    MessageHandler(filters.PHOTO, receive_images),
                    MessageHandler(filters.Document.IMAGE, receive_images),
                    CommandHandler('done', lambda u, c: proceed_to_video(u, c)),
                    CommandHandler('next', lambda u, c: proceed_to_video(u, c)),
                    CommandHandler('cancel', cancel),
                ],
                WAITING_VIDEO: [
                    MessageHandler(filters.Document.VIDEO, receive_video),
                    MessageHandler(filters.Document.ALL, receive_video),
                    CommandHandler('cancel', cancel),
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        
        # Add handlers
        application.add_handler(conv_handler)
        application.add_handler(CommandHandler('help', help_command))
        application.add_handler(CommandHandler('start', start))
        
        logger.info("Handlers configured successfully")
        
        # Start bot
        print("✅ Bot ready! Listening for messages...")
        print("Press Ctrl+C to stop\n")
        
        application.run_polling(
            allowed_updates=["message", "edited_message"],
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.critical(f"Failed to start bot: {e}\n{traceback.format_exc()}")
        print(f"\n❌ CRITICAL ERROR: {e}")
        exit(1)


if __name__ == '__main__':
    main()
