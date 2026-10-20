import os
import sys
import logging
from dotenv import load_dotenv

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

from handlers import get_conversation_handler, cmd_start

# Loglarni sozlash
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("ZeptoSlaydBot")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Yordam va qo'llanma xabari."""
    help_text = (
        "💡 <b>Taqdimot Botidan Foydalanish Qo'llanmasi</b>\n\n"
        "1. /start buyrug'ini bosing va <b>«Yangi taqdimot yaratish»</b> tugmasini bosing.\n"
        "2. 6 xil dizayndan birini tanlang.\n"
        "3. Logotipingizni yuboring (yoki o'tkazib yuboring).\n"
        "4. Ismingiz, guruhingiz, universitet nomi va mavzuni kiriting.\n"
        "5. Slaydlar sonini (5, 8, 10, 15) tanlang.\n"
        "6. <b>«⚡ Avtomatik to'ldirish»</b> tugmasini bossangiz, bot mavzuga doir tayyor akademik reja va punktlar bilan .pptx faylni yaratib beradi.\n\n"
        "Har qanday bosqichda <b>«⬅️ Orqaga»</b> yoki <b>«❌ Bekor qilish»</b> tugmalaridan foydalanishingiz mumkin."
    )
    await update.message.reply_text(help_text, parse_mode="HTML")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Kutilmagan xatoliklarni xavfsiz ushlash va logga yozish."""
    logger.error("Kutilmagan xatolik yuz berdi:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ Kechirasiz, kutilmagan texnik xatolik yuz berdi. "
                "Iltimos, qaytadan boshlash uchun /start buyrug'ini bosing."
            )
        except Exception:
            pass

def main() -> None:
    # 1. .env faylidan sozlamalarni yuklash
    load_dotenv()
    token = os.getenv("BOT_TOKEN")

    if not token or token == "your_telegram_bot_token_here":
        logger.critical(
            "XATOLIK: .env faylida BOT_TOKEN topilmadi yoki noto'g'ri ko'rsatilgan! "
            "Iltimos, .env fayliga @BotFather'dan olingan tokenni kiriting."
        )
        sys.exit(1)

    # 2. Telegram Bot Application qurish
    logger.info("Bot ishga tushirilmoqda...")
    application = ApplicationBuilder().token(token).build()

    # 3. Handlerlarni ro'yxatdan o'tkazish
    application.add_handler(get_conversation_handler())
    application.add_handler(CommandHandler("help", cmd_help))

    # 4. Global xatoliklar handlerini ulash
    application.add_error_handler(error_handler)

    # 5. Polling rejimida ishga tushirish
    logger.info("Bot muvaffaqiyatli ishga tushdi va xabarlarni qabul qilmoqda!")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
