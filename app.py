import os
import logging
import sys
import asyncio
import io
from tempfile import NamedTemporaryFile
from PyPDF2 import PdfReader, PdfWriter
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Check for BOT_TOKEN
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    logger.error("❌ BOT_TOKEN not set!")
    sys.exit(1)

logger.info("✅ BOT_TOKEN loaded")

# Initialize bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# States for PDF collection
class MergeStates(StatesGroup):
    collecting_pdfs = State()

def get_merge_keyboard():
    buttons = [
        [InlineKeyboardButton(text="📄 Add another PDF", callback_data="add_more")],
        [InlineKeyboardButton(text="🔗 Merge Now", callback_data="merge_now")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    logger.info(f"/start from {message.from_user.id}")
    
    # Clear any existing state
    await state.clear()
    
    # Delete webhook to ensure polling works
    await bot.delete_webhook(drop_pending_updates=True)
    
    await message.answer(
        "📑 *PDF Merger Bot*\n\n"
        "Merge multiple PDF files into one document.\n\n"
        "📌 *How to use:*\n"
        "1. Send me your first PDF file\n"
        "2. Continue adding more PDFs\n"
        "3. Click 'Merge Now' when done\n"
        "4. I'll send you the merged PDF\n\n"
        "✨ *Features:*\n"
        "- Merge 2-10 PDF files\n"
        "- Preserves original quality\n"
        "- Maintains page order\n\n"
        "Send me your first PDF to start!",
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        "📖 *Commands:*\n"
        "/start - Start merging PDFs\n"
        "/help - Show this help\n"
        "/cancel - Cancel current operation\n\n"
        "📂 *How to merge:*\n"
        "1. Send PDF files one by one\n"
        "2. Click 'Add another PDF' to continue\n"
        "3. Click 'Merge Now' to combine\n\n"
        "Send /start to begin!",
        parse_mode="Markdown"
    )

@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Operation cancelled. Send /start to begin again.")

@dp.message(lambda message: message.document and message.document.mime_type == 'application/pdf')
async def handle_pdf(message: types.Message, state: FSMContext):
    try:
        # Get current data
        user_data = await state.get_data()
        pdf_files = user_data.get('pdf_files', [])
        
        # Check limits
        if len(pdf_files) >= 10:
            await message.answer("❌ Maximum 10 PDF files per merge. Click 'Merge Now' to finish.")
            return
        
        # Download PDF
        processing_msg = await message.answer(f"📥 Downloading PDF {len(pdf_files) + 1}...")
        
        file = await bot.get_file(message.document.file_id)
        file_bytes = await bot.download_file(file.file_path)
        
        # Verify it's a valid PDF
        temp_pdf = NamedTemporaryFile(suffix=".pdf", delete=False)
        temp_pdf.write(file_bytes.getvalue())
        temp_pdf.close()
        
        try:
            # Try to read it
            reader = PdfReader(temp_pdf.name)
            page_count = len(reader.pages)
            
            # Store in state
            pdf_files.append({
                'name': message.document.file_name or f"document_{len(pdf_files)+1}.pdf",
                'data': file_bytes.getvalue(),
                'pages': page_count
            })
            
            await state.update_data(pdf_files=pdf_files)
            await state.set_state(MergeStates.collecting_pdfs)
            
            await processing_msg.delete()
            os.unlink(temp_pdf.name)
            
            await message.answer(
                f"✅ Added: *{pdf_files[-1]['name']}*\n"
                f"📄 Pages: {page_count}\n\n"
                f"📚 Total PDFs: {len(pdf_files)}\n"
                f"📑 Total pages: {sum(p['pages'] for p in pdf_files)}\n\n"
                f"What would you like to do?",
                parse_mode="Markdown",
                reply_markup=get_merge_keyboard()
            )
            
        except Exception as e:
            os.unlink(temp_pdf.name)
            await processing_msg.delete()
            await message.answer("❌ Invalid PDF file. Please send a valid PDF document.")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer("❌ Failed to process PDF. Please try again.")

@dp.callback_query()
async def handle_merge_actions(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data
    
    if data == "cancel":
        await state.clear()
        await callback.message.edit_text("❌ Merge cancelled. Send /start to begin again.")
        await callback.answer()
        return
    
    elif data == "add_more":
        await callback.message.edit_text(
            "📄 Send me another PDF file.\n\n"
            "You can send more PDFs or click 'Merge Now' when done.",
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    elif data == "merge_now":
        user_data = await state.get_data()
        pdf_files = user_data.get('pdf_files', [])
        
        if len(pdf_files) < 2:
            await callback.message.edit_text("❌ Need at least 2 PDF files to merge. Send more PDFs.")
            await callback.answer()
            return
        
        await callback.message.edit_text(f"🔄 Merging {len(pdf_files)} PDF files...")
        await callback.answer()
        
        try:
            # Create merger
            merger = PdfWriter()
            
            for pdf_info in pdf_files:
                temp_path = None
                try:
                    # Write to temp file
                    with NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        tmp.write(pdf_info['data'])
                        temp_path = tmp.name
                    
                    # Read and add pages
                    reader = PdfReader(temp_path)
                    for page in reader.pages:
                        merger.add_page(page)
                        
                finally:
                    if temp_path and os.path.exists(temp_path):
                        os.unlink(temp_path)
            
            # Save merged PDF
            output = io.BytesIO()
            merger.write(output)
            output.seek(0)
            
            # Send merged file
            await callback.message.delete()
            
            await callback.message.answer_document(
                document=BufferedInputFile(output.getvalue(), filename="merged.pdf"),
                caption=f"✅ *PDFs Merged Successfully!*\n\n"
                       f"📚 Files merged: {len(pdf_files)}\n"
                       f"📑 Total pages: {len(merger.pages)}\n\n"
                       f"Send /start to merge more PDFs.",
                parse_mode="Markdown"
            )
            
            await state.clear()
            
        except Exception as e:
            logger.error(f"Merge error: {e}")
            await callback.message.answer("❌ Failed to merge PDFs. Please try again.")
            await state.clear()

@dp.message()
async def unknown_message(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state == MergeStates.collecting_pdfs:
        await message.answer(
            "📄 Please send a PDF file.\n\n"
            "Use the buttons below or type /cancel to stop.",
            reply_markup=get_merge_keyboard()
        )
    else:
        await message.answer(
            "📑 Send me a PDF file to start merging.\n\n"
            "Send /start for instructions.",
            parse_mode="Markdown"
        )

async def main():
    logger.info("=" * 45)
    logger.info("📑 PDF MERGER BOT STARTING")
    
    # Delete webhook on startup
    await bot.delete_webhook(drop_pending_updates=True)
    
    me = await bot.get_me()
    logger.info(f"🤖 Bot: @{me.username}")
    logger.info(f"🆔 Bot ID: {me.id}")
    logger.info("=" * 45)
    logger.info("✅ Bot is polling for messages...")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
