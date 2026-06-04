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

# Language translations
TEXTS = {
    "en": {
        "welcome": "📑 *PDF Merger Bot*\n\nMerge multiple PDF files into one document.\n\n📌 *How to use:*\n1. Send me your first PDF file\n2. Continue adding more PDFs\n3. Click 'Merge Now' when done\n4. I'll send you the merged PDF\n\n✨ *Features:*\n- Merge 2-10 PDF files\n- Preserves original quality\n- Maintains page order\n\nSend me your first PDF to start!",
        "help": "📖 *Commands:*\n/start - Start merging PDFs\n/help - Show this help\n/cancel - Cancel current operation\n\n📂 *How to merge:*\n1. Send PDF files one by one\n2. Click 'Add another PDF' to continue\n3. Click 'Merge Now' to combine\n\nSend /start to begin!",
        "cancel": "❌ Operation cancelled. Send /start to begin again.",
        "add_more": "📄 Send me another PDF file.\n\nYou can send more PDFs or click 'Merge Now' when done.",
        "add_more_btn": "📄 Add another PDF",
        "merge_btn": "🔗 Merge Now",
        "cancel_btn": "❌ Cancel",
        "need_more": "❌ Need at least 2 PDF files to merge. Send more PDFs.",
        "merging": "🔄 Merging {count} PDF files...",
        "merge_success": "✅ *PDFs Merged Successfully!*\n\n📚 Files merged: {count}\n📑 Total pages: {pages}\n\nSend /start to merge more PDFs.",
        "merge_failed": "❌ Failed to merge PDFs. Please try again.",
        "invalid_pdf": "❌ Invalid PDF file. Please send a valid PDF document.",
        "max_limit": "❌ Maximum 10 PDF files per merge. Click 'Merge Now' to finish.",
        "downloading": "📥 Downloading PDF {num}...",
        "added": "✅ Added: *{name}*\n📄 Pages: {pages}\n\n📚 Total PDFs: {total}\n📑 Total pages: {total_pages}\n\nWhat would you like to do?",
        "send_pdf": "📑 Send me a PDF file to start merging.\n\nSend /start for instructions.",
        "please_send_pdf": "📄 Please send a PDF file.\n\nUse the buttons below or type /cancel to stop.",
        "unknown": "📑 Send me a PDF file to start merging.\n\nSend /start for instructions.",
        "language_selected": "✅ Language set to English. Send /start to begin.",
        "select_language": "🌐 *Select your language / Selecciona tu idioma*"
    },
    "es": {
        "welcome": "📑 *Bot Fusionador de PDF*\n\nFusiona múltiples archivos PDF en un solo documento.\n\n📌 *Cómo usar:*\n1. Envíame tu primer PDF\n2. Sigue agregando más PDFs\n3. Haz clic en 'Fusionar Ahora'\n4. Te enviaré el PDF fusionado\n\n✨ *Características:*\n- Fusiona 2-10 archivos PDF\n- Preserva la calidad original\n- Mantiene el orden de las páginas\n\n¡Envíame tu primer PDF para comenzar!",
        "help": "📖 *Comandos:*\n/start - Comenzar a fusionar PDFs\n/help - Mostrar esta ayuda\n/cancel - Cancelar operación actual\n\n📂 *Cómo fusionar:*\n1. Envía PDFs uno por uno\n2. Haz clic en 'Agregar otro PDF' para continuar\n3. Haz clic en 'Fusionar Ahora' para combinar\n\n¡Envía /start para comenzar!",
        "cancel": "❌ Operación cancelada. Envía /start para comenzar de nuevo.",
        "add_more": "📄 Envíame otro archivo PDF.\n\nPuedes enviar más PDFs o hacer clic en 'Fusionar Ahora' cuando termines.",
        "add_more_btn": "📄 Agregar otro PDF",
        "merge_btn": "🔗 Fusionar Ahora",
        "cancel_btn": "❌ Cancelar",
        "need_more": "❌ Se necesitan al menos 2 archivos PDF para fusionar. Envía más PDFs.",
        "merging": "🔄 Fusionando {count} archivos PDF...",
        "merge_success": "✅ *¡PDFs Fusionados Exitosamente!*\n\n📚 Archivos fusionados: {count}\n📑 Páginas totales: {pages}\n\nEnvía /start para fusionar más PDFs.",
        "merge_failed": "❌ Error al fusionar los PDFs. Por favor, inténtalo de nuevo.",
        "invalid_pdf": "❌ Archivo PDF inválido. Por favor, envía un documento PDF válido.",
        "max_limit": "❌ Máximo 10 archivos PDF por fusión. Haz clic en 'Fusionar Ahora' para terminar.",
        "downloading": "📥 Descargando PDF {num}...",
        "added": "✅ Agregado: *{name}*\n📄 Páginas: {pages}\n\n📚 Total PDFs: {total}\n📑 Páginas totales: {total_pages}\n\n¿Qué deseas hacer?",
        "send_pdf": "📑 Envíame un archivo PDF para comenzar a fusionar.\n\nEnvía /start para instrucciones.",
        "please_send_pdf": "📄 Por favor, envía un archivo PDF.\n\nUsa los botones de abajo o escribe /cancel para detener.",
        "unknown": "📑 Envíame un archivo PDF para comenzar a fusionar.\n\nEnvía /start para instrucciones.",
        "language_selected": "✅ Idioma configurado a Español. Envía /start para comenzar.",
        "select_language": "🌐 *Selecciona tu idioma / Select your language*"
    },
    "es-mx": {
        "welcome": "📑 *Bot para Fusionar PDFs*\n\nJunta varios archivos PDF en uno solo.\n\n📌 *Cómo usar:*\n1. Mándame tu primer PDF\n2. Sigue agregando más PDFs\n3. Haz clic en 'Fusionar Ahora'\n4. Te mandaré el PDF combinado\n\n✨ *Características:*\n- Fusiona 2-10 archivos PDF\n- Mantiene la calidad original\n- Respeta el orden de las páginas\n\n¡Mándame tu primer PDF para empezar!",
        "help": "📖 *Comandos:*\n/start - Empezar a fusionar PDFs\n/help - Mostrar esta ayuda\n/cancel - Cancelar lo que estás haciendo\n\n📂 *Cómo fusionar:*\n1. Envía PDFs uno por uno\n2. Haz clic en 'Agregar otro PDF' para continuar\n3. Haz clic en 'Fusionar Ahora' para combinarlos\n\n¡Envía /start para comenzar!",
        "cancel": "❌ Operación cancelada. Envía /start para empezar de nuevo.",
        "add_more": "📄 Mándame otro archivo PDF.\n\nPuedes mandar más PDFs o hacer clic en 'Fusionar Ahora' cuando termines.",
        "add_more_btn": "📄 Agregar otro PDF",
        "merge_btn": "🔗 Fusionar Ahora",
        "cancel_btn": "❌ Cancelar",
        "need_more": "❌ Necesitas al menos 2 archivos PDF para fusionar. Manda más PDFs.",
        "merging": "🔄 Fusionando {count} archivos PDF...",
        "merge_success": "✅ *¡PDFs Fusionados Exitosamente!*\n\n📚 Archivos fusionados: {count}\n📑 Páginas totales: {pages}\n\nEnvía /start para fusionar más PDFs.",
        "merge_failed": "❌ Error al fusionar los PDFs. Por favor, inténtalo de nuevo.",
        "invalid_pdf": "❌ Archivo PDF inválido. Por favor, manda un documento PDF válido.",
        "max_limit": "❌ Máximo 10 archivos PDF por fusión. Haz clic en 'Fusionar Ahora' para terminar.",
        "downloading": "📥 Descargando PDF {num}...",
        "added": "✅ Agregado: *{name}*\n📄 Páginas: {pages}\n\n📚 Total de PDFs: {total}\n📑 Páginas totales: {total_pages}\n\n¿Qué quieres hacer?",
        "send_pdf": "📑 Mándame un archivo PDF para empezar a fusionar.\n\nEnvía /start para instrucciones.",
        "please_send_pdf": "📄 Por favor, manda un archivo PDF.\n\nUsa los botones de abajo o escribe /cancel para detener.",
        "unknown": "📑 Mándame un archivo PDF para empezar a fusionar.\n\nEnvía /start para instrucciones.",
        "language_selected": "✅ Idioma configurado a Español (México). Envía /start para comenzar.",
        "select_language": "🌐 *Selecciona tu idioma / Select your language*"
    }
}

# States for PDF collection
class MergeStates(StatesGroup):
    collecting_pdfs = State()

# Store user language preferences
user_languages = {}

def get_language_keyboard():
    """Create inline keyboard with language options"""
    buttons = [
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton(text="🇪🇸 Español", callback_data="lang_es")],
        [InlineKeyboardButton(text="🇲🇽 Español (México)", callback_data="lang_es-mx")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_merge_keyboard(lang):
    """Get merge keyboard in user's language"""
    buttons = [
        [InlineKeyboardButton(text=TEXTS[lang]["add_more_btn"], callback_data="add_more")],
        [InlineKeyboardButton(text=TEXTS[lang]["merge_btn"], callback_data="merge_now")],
        [InlineKeyboardButton(text=TEXTS[lang]["cancel_btn"], callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_user_language(user_id):
    """Get user's preferred language, default to English"""
    return user_languages.get(user_id, "en")

@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    logger.info(f"/start from {message.from_user.id}")
    
    # Clear any existing state
    await state.clear()
    
    # Delete webhook to ensure polling works
    await bot.delete_webhook(drop_pending_updates=True)
    
    # Check if user already selected a language
    user_id = message.from_user.id
    if user_id not in user_languages:
        # Show language selection
        await message.answer(
            TEXTS["en"]["select_language"],
            parse_mode="Markdown",
            reply_markup=get_language_keyboard()
        )
    else:
        lang = user_languages[user_id]
        await message.answer(
            TEXTS[lang]["welcome"],
            parse_mode="Markdown"
        )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    await message.answer(
        TEXTS[lang]["help"],
        parse_mode="Markdown"
    )

@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    await state.clear()
    await message.answer(TEXTS[lang]["cancel"])

@dp.callback_query(lambda c: c.data and c.data.startswith("lang_"))
async def handle_language_selection(callback: types.CallbackQuery, state: FSMContext):
    lang_code = callback.data.replace("lang_", "")
    user_id = callback.from_user.id
    
    # Store user's language preference
    user_languages[user_id] = lang_code
    
    await callback.message.edit_text(
        TEXTS[lang_code]["language_selected"],
        parse_mode="Markdown"
    )
    
    # Send welcome message in selected language
    await callback.message.answer(
        TEXTS[lang_code]["welcome"],
        parse_mode="Markdown"
    )
    
    await callback.answer()

@dp.message(lambda message: message.document and message.document.mime_type == 'application/pdf')
async def handle_pdf(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    # Check if user has selected language
    if user_id not in user_languages:
        await message.answer(
            TEXTS["en"]["select_language"],
            parse_mode="Markdown",
            reply_markup=get_language_keyboard()
        )
        return
    
    try:
        # Get current data
        user_data = await state.get_data()
        pdf_files = user_data.get('pdf_files', [])
        
        # Check limits
        if len(pdf_files) >= 10:
            await message.answer(TEXTS[lang]["max_limit"])
            return
        
        # Download PDF
        processing_msg = await message.answer(TEXTS[lang]["downloading"].format(num=len(pdf_files) + 1))
        
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
                TEXTS[lang]["added"].format(
                    name=pdf_files[-1]['name'],
                    pages=page_count,
                    total=len(pdf_files),
                    total_pages=sum(p['pages'] for p in pdf_files)
                ),
                parse_mode="Markdown",
                reply_markup=get_merge_keyboard(lang)
            )
            
        except Exception as e:
            os.unlink(temp_pdf.name)
            await processing_msg.delete()
            await message.answer(TEXTS[lang]["invalid_pdf"])
            
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer(TEXTS[lang]["invalid_pdf"])

@dp.callback_query()
async def handle_merge_actions(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = get_user_language(user_id)
    data = callback.data
    
    if data == "cancel":
        await state.clear()
        await callback.message.edit_text(TEXTS[lang]["cancel"])
        await callback.answer()
        return
    
    elif data == "add_more":
        await callback.message.edit_text(
            TEXTS[lang]["add_more"],
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    elif data == "merge_now":
        user_data = await state.get_data()
        pdf_files = user_data.get('pdf_files', [])
        
        if len(pdf_files) < 2:
            await callback.message.edit_text(TEXTS[lang]["need_more"])
            await callback.answer()
            return
        
        await callback.message.edit_text(TEXTS[lang]["merging"].format(count=len(pdf_files)))
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
                caption=TEXTS[lang]["merge_success"].format(
                    count=len(pdf_files),
                    pages=len(merger.pages)
                ),
                parse_mode="Markdown"
            )
            
            await state.clear()
            
        except Exception as e:
            logger.error(f"Merge error: {e}")
            await callback.message.answer(TEXTS[lang]["merge_failed"])
            await state.clear()

@dp.message()
async def unknown_message(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    lang = get_user_language(user_id)
    
    current_state = await state.get_state()
    
    if current_state == MergeStates.collecting_pdfs:
        await message.answer(
            TEXTS[lang]["please_send_pdf"],
            reply_markup=get_merge_keyboard(lang)
        )
    else:
        await message.answer(
            TEXTS[lang]["unknown"],
            parse_mode="Markdown"
        )

async def main():
    logger.info("=" * 45)
    logger.info("📑 PDF MERGER BOT STARTING (Multi-Language)")
    
    # Delete webhook on startup
    await bot.delete_webhook(drop_pending_updates=True)
    
    me = await bot.get_me()
    logger.info(f"🤖 Bot: @{me.username}")
    logger.info(f"🆔 Bot ID: {me.id}")
    logger.info("=" * 45)
    logger.info("✅ Bot is polling for messages...")
    logger.info("🌐 Languages: English, Spanish, Spanish (Mexico)")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
