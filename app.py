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
    logger.error("❌ BOT_TOKEN no configurado!")
    sys.exit(1)

logger.info("✅ BOT_TOKEN cargado")

# Initialize bot
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# All text in Spanish only
TEXTS = {
    "welcome": "📑 *Bot Fusionador de PDF*\n\nFusiona múltiples archivos PDF en un solo documento.\n\n📌 *Cómo usar:*\n1. Envíame tu primer PDF\n2. Sigue agregando más PDFs\n3. Haz clic en 'Fusionar Ahora' cuando termines\n4. Te enviaré el PDF fusionado\n\n✨ *Características:*\n- Fusiona 2-10 archivos PDF\n- Preserva la calidad original\n- Mantiene el orden de las páginas\n- 100% gratis\n\n¡Envíame tu primer PDF para comenzar!",
    
    "help": "📖 *Comandos:*\n/start - Comenzar a fusionar PDFs\n/help - Mostrar esta ayuda\n/cancel - Cancelar operación actual\n\n📂 *Cómo fusionar:*\n1. Envía PDFs uno por uno\n2. Haz clic en 'Agregar otro PDF' para continuar\n3. Haz clic en 'Fusionar Ahora' para combinar\n\n¡Envía /start para comenzar!",
    
    "cancel": "❌ Operación cancelada. Envía /start para comenzar de nuevo.",
    
    "add_more": "📄 Envíame otro archivo PDF.\n\nPuedes enviar más PDFs o hacer clic en 'Fusionar Ahora' cuando termines.",
    
    "add_more_btn": "📄 Agregar otro PDF",
    "merge_btn": "🔗 Fusionar Ahora",
    "cancel_btn": "❌ Cancelar",
    
    "need_more": "❌ Necesitas al menos 2 archivos PDF para fusionar. Envía más PDFs.",
    
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
    
    "error": "❌ Ocurrió un error. Por favor, inténtalo de nuevo."
}

# States for PDF collection
class MergeStates(StatesGroup):
    collecting_pdfs = State()

def get_merge_keyboard():
    """Create merge keyboard in Spanish"""
    buttons = [
        [InlineKeyboardButton(text=TEXTS["add_more_btn"], callback_data="add_more")],
        [InlineKeyboardButton(text=TEXTS["merge_btn"], callback_data="merge_now")],
        [InlineKeyboardButton(text=TEXTS["cancel_btn"], callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(Command("start"))
async def start_command(message: types.Message, state: FSMContext):
    logger.info(f"/start de usuario {message.from_user.id}")
    
    # Clear any existing state
    await state.clear()
    
    # Delete webhook to ensure polling works
    await bot.delete_webhook(drop_pending_updates=True)
    
    await message.answer(
        TEXTS["welcome"],
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
async def help_command(message: types.Message):
    await message.answer(
        TEXTS["help"],
        parse_mode="Markdown"
    )

@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(TEXTS["cancel"])

@dp.message(lambda message: message.document and message.document.mime_type == 'application/pdf')
async def handle_pdf(message: types.Message, state: FSMContext):
    try:
        # Get current data
        user_data = await state.get_data()
        pdf_files = user_data.get('pdf_files', [])
        
        # Check limits
        if len(pdf_files) >= 10:
            await message.answer(TEXTS["max_limit"])
            return
        
        # Download PDF
        processing_msg = await message.answer(TEXTS["downloading"].format(num=len(pdf_files) + 1))
        
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
                'name': message.document.file_name or f"documento_{len(pdf_files)+1}.pdf",
                'data': file_bytes.getvalue(),
                'pages': page_count
            })
            
            await state.update_data(pdf_files=pdf_files)
            await state.set_state(MergeStates.collecting_pdfs)
            
            await processing_msg.delete()
            os.unlink(temp_pdf.name)
            
            await message.answer(
                TEXTS["added"].format(
                    name=pdf_files[-1]['name'],
                    pages=page_count,
                    total=len(pdf_files),
                    total_pages=sum(p['pages'] for p in pdf_files)
                ),
                parse_mode="Markdown",
                reply_markup=get_merge_keyboard()
            )
            
        except Exception as e:
            os.unlink(temp_pdf.name)
            await processing_msg.delete()
            await message.answer(TEXTS["invalid_pdf"])
            
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.answer(TEXTS["error"])

@dp.callback_query()
async def handle_merge_actions(callback: types.CallbackQuery, state: FSMContext):
    data = callback.data
    
    if data == "cancel":
        await state.clear()
        await callback.message.edit_text(TEXTS["cancel"])
        await callback.answer()
        return
    
    elif data == "add_more":
        await callback.message.edit_text(
            TEXTS["add_more"],
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    elif data == "merge_now":
        user_data = await state.get_data()
        pdf_files = user_data.get('pdf_files', [])
        
        if len(pdf_files) < 2:
            await callback.message.edit_text(TEXTS["need_more"])
            await callback.answer()
            return
        
        await callback.message.edit_text(TEXTS["merging"].format(count=len(pdf_files)))
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
                document=BufferedInputFile(output.getvalue(), filename="fusionado.pdf"),
                caption=TEXTS["merge_success"].format(
                    count=len(pdf_files),
                    pages=len(merger.pages)
                ),
                parse_mode="Markdown"
            )
            
            await state.clear()
            
        except Exception as e:
            logger.error(f"Error al fusionar: {e}")
            await callback.message.answer(TEXTS["merge_failed"])
            await state.clear()

@dp.message()
async def unknown_message(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    
    if current_state == MergeStates.collecting_pdfs:
        await message.answer(
            TEXTS["please_send_pdf"],
            reply_markup=get_merge_keyboard()
        )
    else:
        await message.answer(
            TEXTS["unknown"],
            parse_mode="Markdown"
        )

async def main():
    logger.info("=" * 45)
    logger.info("📑 BOT FUSIONADOR DE PDF INICIADO")
    logger.info("🌐 Idioma: Español")
    
    # Delete webhook on startup
    await bot.delete_webhook(drop_pending_updates=True)
    
    me = await bot.get_me()
    logger.info(f"🤖 Bot: @{me.username}")
    logger.info(f"🆔 ID del Bot: {me.id}")
    logger.info("=" * 45)
    logger.info("✅ Bot está escuchando mensajes...")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
