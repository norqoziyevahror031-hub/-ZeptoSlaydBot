import os
import sys
import time
import logging
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv

# Render / Koyeb Web Service port tekshiruvi (Health check) uchun server
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK - ZeptoSlaydBot is running 24/7!")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass  # Health check loglari konsolni to'ldirib yubormasligi uchun


def start_health_check_server() -> None:
    """Agar PORT muhit o'zgaruvchisi bo'lsa (Render Web Service), portni eshituvchi yengil serverni ishga tushiradi."""
    port_str = os.getenv("PORT")
    if not port_str:
        return
    try:
        port = int(port_str)
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        logger.info(f"Health check server {port}-portda muvaffaqiyatli ishga tushdi (Render Web Service).")
    except Exception as e:
        logger.warning(f"Health check serverni ishga tushirishda xatolik: {e}")

# Windows konsolida UTF-8 va emojilar to'g'ri ishlashi uchun
if sys.stdout:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if sys.stderr:
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass
os.environ["PYTHONIOENCODING"] = "utf-8"

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

from handlers import get_conversation_handler, cmd_start

# Loglarni sozlash: Ham konsolga, ham bot.log fayliga yozish
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logger = logging.getLogger("ZeptoSlaydBot")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(console_handler)

try:
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot.log")
    file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)
except Exception as e:
    print(f"Log faylini ochishda xatolik: {e}")

# Kutilmagan boshqa kutubxonalar loglarini boshqarish
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.INFO)


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Yordam va qo'llanma xabari."""
    help_text = (
        "💡 <b>ZeptoSlaydBot — Foydalanish Qo'llanmasi</b>\n\n"
        "Bot akademik va professional taqdimotlarni (.pptx) to'liq avtomatlashtirilgan tarzda yaratadi:\n\n"
        "🎨 <b>8 ta mashhur PowerPoint shablonlari:</b>\n"
        "• <b>Ion:</b> Qizil nafis chiziqli klassik akademik uslub\n"
        "• <b>Facet:</b> Ko'k va sariq geometrik zamonaviy dizayn\n"
        "• <b>Savon:</b> Zumrad yashil tabiat va ekologik uslub\n"
        "• <b>Madison:</b> Qizil-oltin korporativ nufuzli dizayn\n"
        "• <b>Atlas:</b> Sof oq, yengil minimalistik uslub\n"
        "• <b>Celestial:</b> To'q ko'k va neon tungi zamonaviy uslub\n"
        "• <b>Retrospect:</b> Issiq to'q sariq biznes va tahlil uslubi\n"
        "• <b>Studio:</b> Oltin-sariq ijodiy va zamonaviy dizayn\n\n"
        "🖼 <b>Rasm va matn qoidalari:</b>\n"
        "• 10 ta slayddan iborat taqdimotda roppa-rosa <b>5 ta rasm</b> joylashtiriladi (har 2 ta slayd uchun 1 ta rasm).\n"
        "• Matnli slaydlar va «yarmi matn, yarmi rasm» slaydlar navbatma-navbat almashib keladi.\n"
        "• Barcha rasmlar 1140x1030 o'lchamda silliq yumaloq burchaklar va mos ramkalar bilan formatlanadi.\n"
        "• Barcha matnlar qat'iy <b>Times New Roman</b> shriftida teriladi.\n\n"
        "⚡ <b>Qanday boshlanadi?</b>\n"
        "1. /start buyrug'ini bosing va <b>«Yangi taqdimot yaratish»</b> ni tanlang.\n"
        "2. Shablon va logotipni tanlang (yoki o'tkazib yuboring).\n"
        "3. Ism, guruh, OTM va mavzuni kiriting.\n"
        "4. Slaydlar sonini (5, 8, 10, 15) tanlang.\n"
        "5. <b>«⚡ Avtomatik to'ldirish»</b> tugmasini bosing — bot bir necha soniyada tayyor .pptx faylni taqdim etadi!"
    )
    if update.effective_message:
        await update.effective_message.reply_text(help_text, parse_mode="HTML")


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


async def post_init_setup(app) -> None:
    """Botning Description, About va Buyruqlar menyusini Telegramga avtomatik o'rnatadi."""
    try:
        from telegram import BotCommand
        commands = [
            BotCommand("start", "Yangi taqdimot yaratish"),
            BotCommand("help", "Botdan foydalanish qo'llanmasi")
        ]
        await app.bot.set_my_commands(commands)

        desc = (
            "🎓 ZeptoSlaydBot — Akademik va professional taqdimotlar (.pptx) yaratuvchi aqlli bot.\n\n"
            "✨ Imkoniyatlar:\n"
            "• 8 ta zamonaviy PowerPoint shablonlari\n"
            "• 10 ta slaydda roppa-rosa 5 ta tematik rasm\n"
            "• Silliq yumaloq burchakli fotosuratlar\n"
            "• Rasmiy akademik Times New Roman shrifti\n"
            "• ⚡ Avtomatik to'ldirish (tayyor reja va matn)\n\n"
            "Boshlash uchun /start buyrug'ini bosing!"
        )
        await app.bot.set_my_description(desc)

        short_desc = "Akademik taqdimotlar (.pptx) yaratuvchi bot. 8 ta shablon, 5 ta rasm va avtomatik reja."
        await app.bot.set_my_short_description(short_desc)
        logger.info("Bot profili, tavsifi va buyruqlari muvaffaqiyatli yangilandi.")
    except Exception as e:
        logger.warning(f"Bot profilini yangilashda ogohlantirish: {e}")


def run_bot() -> None:
    """Bot ilovasini qurish va pollingni ishga tushirish."""
    load_dotenv()
    token = os.getenv("BOT_TOKEN")

    if not token or token == "your_telegram_bot_token_here":
        logger.critical(
            "XATOLIK: .env faylida BOT_TOKEN topilmadi yoki noto'g'ri ko'rsatilgan! "
            "Iltimos, .env fayliga @BotFather'dan olingan tokenni kiriting."
        )
        sys.exit(1)

    logger.info("Bot ishga tushirilmoqda...")

    # Render Web Service port tekshiruvini qanoatlantirish
    start_health_check_server()

    application = (
        ApplicationBuilder()
        .token(token)
        .post_init(post_init_setup)
        .connect_timeout(30.0)
        .read_timeout(30.0)
        .write_timeout(30.0)
        .pool_timeout(30.0)
        .get_updates_connect_timeout(30.0)
        .get_updates_read_timeout(30.0)
        .get_updates_write_timeout(30.0)
        .get_updates_pool_timeout(30.0)
        .build()
    )

    # Handlerlarni ro'yxatdan o'tkazish
    application.add_handler(get_conversation_handler())
    application.add_handler(CommandHandler("help", cmd_help))

    # Global xatoliklar handlerini ulash
    application.add_error_handler(error_handler)

    # Polling rejimida ishga tushirish (24/7 rejim)
    logger.info("Bot muvaffaqiyatli ishga tushdi va xabarlarni qabul qilmoqda!")
    application.run_polling(
        drop_pending_updates=True,
        allowed_updates=Update.ALL_TYPES,
        poll_interval=1.0
    )


def main() -> None:
    """24/7 uzluksiz ishlash uchun qayta ishga tushirish (auto-restart) sikli."""
    retry_delay = 5
    while True:
        try:
            run_bot()
            break
        except KeyboardInterrupt:
            logger.info("Bot foydalanuvchi tomonidan to'xtatildi (KeyboardInterrupt).")
            break
        except SystemExit:
            break
        except Exception as e:
            logger.error(
                f"Bot kutilmaganda to'xtadi: {e}. {retry_delay} soniyadan so'ng avtomatik qayta ishga tushiriladi...",
                exc_info=True
            )
            time.sleep(retry_delay)


if __name__ == "__main__":
    main()
