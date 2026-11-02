import os
import html
import logging
from typing import Dict, Any

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton
)
import database
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters
)

from themes import THEMES, get_theme, generate_catalog_image
from slide_builder import build_presentation_full, TEMP_DIR

logger = logging.getLogger(__name__)

# Suhbat holatlari (States)
(
    STATE_SELECT_THEME,
    STATE_INPUT_LOGO,
    STATE_INPUT_AUTHOR,
    STATE_INPUT_GROUP,
    STATE_INPUT_UNIVERSITY,
    STATE_INPUT_TOPIC,
    STATE_INPUT_SLIDE_COUNT,
    STATE_INPUT_FILL_MODE,
    STATE_INPUT_MANUAL_SLIDE_TITLE,
    STATE_INPUT_MANUAL_SLIDE_BODY
) = range(10)

CATALOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "previews", "catalog.png")

# ==========================================
# KEYBOARD BUILDERS
# ==========================================

def find_default_logo() -> str | None:
    """logotiv/ papkasida mavjud logotip rasmini topadi."""
    logotiv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logotiv")
    if os.path.isdir(logotiv_dir):
        for f in os.listdir(logotiv_dir):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')):
                return os.path.join(logotiv_dir, f)
    return None

def get_back_cancel_keyboard(show_skip: bool = False, skip_data: str = "btn_skip", show_default_logo: bool = False) -> InlineKeyboardMarkup:
    """Orqaga va Bekor qilish (hamda ixtiyoriy O'tkazib yuborish va Standart logotip) tugmalari."""
    buttons = []
    if show_default_logo and find_default_logo():
        buttons.append([InlineKeyboardButton("📁 Standart logotipdan foydalanish", callback_data="btn_use_default_logo")])
    if show_skip:
        buttons.append([InlineKeyboardButton("⏩ O'tkazib yuborish", callback_data=skip_data)])
    buttons.append([
        InlineKeyboardButton("⬅️ Orqaga", callback_data="btn_back"),
        InlineKeyboardButton("❌ Bekor qilish", callback_data="btn_cancel")
    ])
    return InlineKeyboardMarkup(buttons)

def get_theme_selection_keyboard() -> InlineKeyboardMarkup:
    """8 ta mashhur PowerPoint shablonlari tugmalari."""
    keyboard = [
        [
            InlineKeyboardButton("🏛 Ion (Klassik)", callback_data="theme_ion"),
            InlineKeyboardButton("💎 Facet (Zamonaviy)", callback_data="theme_facet")
        ],
        [
            InlineKeyboardButton("🌿 Savon (Zumrad)", callback_data="theme_savon"),
            InlineKeyboardButton("👑 Madison (Qizil-Oltin)", callback_data="theme_madison")
        ],
        [
            InlineKeyboardButton("⚪ Atlas (Minimal)", callback_data="theme_atlas"),
            InlineKeyboardButton("🌙 Celestial (Tungi Neon)", callback_data="theme_celestial")
        ],
        [
            InlineKeyboardButton("💼 Retrospect (Biznes)", callback_data="theme_retrospect"),
            InlineKeyboardButton("☀️ Studio (Ijodiy)", callback_data="theme_studio")
        ],
        [
            InlineKeyboardButton("❌ Bekor qilish", callback_data="btn_cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_slide_count_keyboard() -> InlineKeyboardMarkup:
    """Slaydlar sonini tanlash tugmalari."""
    keyboard = [
        [
            InlineKeyboardButton("5 ta slayd", callback_data="count_5"),
            InlineKeyboardButton("8 ta slayd", callback_data="count_8")
        ],
        [
            InlineKeyboardButton("10 ta slayd", callback_data="count_10"),
            InlineKeyboardButton("15 ta slayd", callback_data="count_15")
        ],
        [
            InlineKeyboardButton("⬅️ Orqaga", callback_data="btn_back"),
            InlineKeyboardButton("❌ Bekor qilish", callback_data="btn_cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_fill_mode_keyboard() -> InlineKeyboardMarkup:
    """To'ldirish rejimi tugmalari."""
    keyboard = [
        [
            InlineKeyboardButton("⚡ Avtomatik to'ldirish (Tavsiya)", callback_data="fill_auto")
        ],
        [
            InlineKeyboardButton("✍️ Slaydlarni qo'lda kiritish", callback_data="fill_manual")
        ],
        [
            InlineKeyboardButton("⬅️ Orqaga", callback_data="btn_back"),
            InlineKeyboardButton("❌ Bekor qilish", callback_data="btn_cancel")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Pastdagi doimiy bosh menyu tugmalari (Reply Keyboard)."""
    keyboard = [
        [KeyboardButton("📊 Yangi taqdimot yaratish")],
        [KeyboardButton("📑 AUDIT (mustaqil ish)"), KeyboardButton("🎓 DIREKTOR.UZ (sertifikat)")],
        [KeyboardButton("💰 Balans"), KeyboardButton("💳 Hisobni to'ldirish")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_finish_keyboard() -> InlineKeyboardMarkup:
    """Taqdimot tayyor bo'lgandan keyingi harakatlar."""
    keyboard = [
        [
            InlineKeyboardButton("🎨 Boshqa dizaynda qayta yaratish", callback_data="action_retheme")
        ],
        [
            InlineKeyboardButton("➕ Yangi taqdimot yaratish", callback_data="action_new")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


# ==========================================
# ASOSIY HANDLERLAR
# ==========================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """1. /start bosilganda kutib olish, pastki doimiy menyu va balans ma'lumotlari."""
    user = update.effective_user
    first_name = html.escape(user.first_name) if user and user.first_name else "Talaba"
    logger.info(f"Foydalanuvchi /start yubordi: {user.id if user else 'Unknown'} ({user.full_name if user else ''})")

    # Foydalanuvchini bazada ro'yxatga olish / yangilash (yangi foydalanuvchiga 15 000 so'm / 3 ta bepul taqdimot)
    db_user = database.get_or_create_user(user.id, user.username, user.full_name) if user else {}
    balance = db_user.get("balance", 0)
    available_slides = balance // 5000

    welcome_text = (
        f"Assalomu alaykum, {first_name}! 👋\n\n"
        f"🎓 <b>ZeptoSlaydBot</b> ga xush kelibsiz!\n"
        f"Men akademik va professional taqdimotlar (.pptx) tayyorlab beruvchi aqlli botman.\n\n"
        f"💰 <b>Sizning balansingiz:</b> <b>{balance:,} so'm</b> ({available_slides} ta taqdimot)\n"
        f"🎁 <i>Yangi foydalanuvchilar uchun 3 ta bepul taqdimot (15 000 so'm) taqdim etiladi!</i>\n\n"
        f"✨ <b>Asosiy imkoniyatlar:</b>\n"
        f"• <b>8 xil PowerPoint dizaynlari:</b> Ion, Facet, Savon, Madison, Atlas, Celestial, Retrospect, Studio\n"
        f"• <b>10 ta slaydda roppa-rosa 5 ta rasm:</b> Matnli va rasmli slaydlar navbatma-navbat almashadi\n"
        f"• <b>Silliq yumaloq burchakli</b> yuqori sifatli fotosuratlar va nozik ramkalar\n"
        f"• Qat'iy akademik <b>Times New Roman</b> shrifti\n"
        f"• <b>⚡ Avtomatik to'ldirish:</b> Mavzuni yozsangiz, bot to'liq ilmiy reja va matnlarni o'zi yozib beradi!\n\n"
        f"Boshlash uchun quyidagi tugmalardan birini tanlang:"
    )

    inline_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Yangi taqdimot yaratish", callback_data="start_creation")],
        [
            InlineKeyboardButton("💰 Balans", callback_data="btn_show_balance"),
            InlineKeyboardButton("💳 Hisobni to'ldirish", callback_data="btn_pay_start")
        ]
    ])

    if update.callback_query:
        await update.callback_query.answer()

    msg = update.effective_message
    if msg:
        await msg.reply_text(
            welcome_text,
            reply_markup=get_main_reply_keyboard(),
            parse_mode="HTML"
        )

    return ConversationHandler.END


async def handle_balance_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Pastdagi '💰 Balans' tugmasi bosilganda."""
    user = update.effective_user
    logger.info(f"Foydalanuvchi Balansni so'radi: {user.id if user else 'Unknown'} ({user.full_name if user else ''})")
    db_user = database.get_or_create_user(user.id, user.username, user.full_name) if user else {}
    balance = db_user.get("balance", 0)
    available_slides = balance // 5000
    user_name = html.escape(user.full_name) if user and user.full_name else "Foydalanuvchi"

    text = (
        f"👤 <b>Foydalanuvchi:</b> {user_name}\n"
        f"🆔 <b>Sizning ID:</b> <code>{user.id if user else ''}</code>\n\n"
        f"💰 <b>Mavjud balans:</b> <b>{balance:,} so'm</b> ({available_slides} ta taqdimot)\n\n"
        f"<i>1 ta to'liq taqdimot narxi: 5 000 so'm.</i>\n"
        f"<i>🎁 Har bir yangi foydalanuvchiga 3 ta bepul taqdimot sovg'a qilingan!</i>\n\n"
        f"Hisobingizni to'ldirish uchun pastdagi <b>«💳 Hisobni to'ldirish»</b> tugmasini bosing:"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Hisobni to'ldirish", callback_data="btn_pay_start")]
    ])
    msg = update.effective_message
    if msg:
        await msg.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def handle_payment_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """'💳 Hisobni to'ldirish' bosilganda karta ma'lumotlarini berish va chek so'rash."""
    context.user_data["waiting_for_payment_receipt"] = True
    card_number = os.getenv("CARD_NUMBER", "5614682115402218")
    card_owner = os.getenv("CARD_OWNER", "Norqoziyev Ahrorbek")
    price = "5 000"

    text = (
        f"💳 <b>Hisobni to'ldirish uchun to'lov qiling:</b>\n\n"
        f"Karta raqami: <code>{card_number}</code>\n"
        f"Egasi: <b>{card_owner}</b>\n"
        f"1 ta taqdimot narxi: <b>{price} so'm</b>\n\n"
        f"<i>To'lovni amalga oshirgach, to'lov cheki (skrinshot)ni shu yerga rasm sifatida yuboring.</i>\n"
        f"<i>Chek adminga yuboriladi va to'lovingiz tez fursatda hisobingizga qo'shiladi!</i>"
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, parse_mode="HTML")
    elif update.message:
        await update.message.reply_text(text, parse_mode="HTML")


async def handle_audit_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """📑 AUDIT (mustaqil ish) xizmati haqida ma'lumot va buyurtma berish."""
    user = update.effective_user
    logger.info(f"Foydalanuvchi AUDIT xizmatini tanladi: {user.id} ({user.full_name})")
    db_user = database.get_or_create_user(user.id, user.username, user.full_name)
    balance = db_user.get("balance", 0)
    price = 59000

    text = (
        "📑 <b>AUDIT (Mustaqil ish) xizmati</b>\n\n"
        "Professional darajada, barcha oliygoh talablariga to'liq mos keladigan mustaqil ish, referat, kurs ishi yoki hisobot tayyorlab berish xizmati.\n\n"
        "✨ <b>Xizmat afzalliklari:</b>\n"
        "• To'liq ilmiy va professional matn\n"
        "• Barcha qoidalarga mos rasmiylashtirish (mundarija, kirish, asosiy boblar, xulosa, foydalanilgan adabiyotlar)\n"
        "• Antiplagiatdan kafolatli o'tish\n"
        "• Qisqa muddatda sifatli va tayyor holda topshirish\n\n"
        f"💵 <b>Xizmat narxi:</b> <b>59 000 so'm</b>\n"
        f"💰 <b>Sizning balansingiz:</b> <b>{balance:,} so'm</b>\n\n"
    )

    buttons = []
    if balance >= price:
        text += "✅ Balansingizda ushbu xizmat uchun yetarli mablag' mavjud! Buyurtma berish uchun quyidagi tugmani bosing:"
        buttons.append([InlineKeyboardButton("🛒 Buyurtma berish (59 000 so'm)", callback_data="order_service_audit")])
    else:
        diff = price - balance
        text += (
            f"⚠️ Buyurtma berish uchun hisobingizda yana <b>{diff:,} so'm</b> yetishmayapti.\n"
            "Iltimos, hisobingizni to'ldiring yoki to'g'ridan-to'g'ri administratorga murojaat qiling:"
        )
        buttons.append([InlineKeyboardButton("💳 Hisobni to'ldirish", callback_data="btn_pay_start")])

    buttons.append([InlineKeyboardButton("👨‍💼 Administratorga yozish", url="https://t.me/ZeptoSlayd")])
    keyboard = InlineKeyboardMarkup(buttons)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
    elif update.message:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def handle_direktor_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """🎓 DIREKTOR.UZ (sertifikat) xizmati haqida ma'lumot va buyurtma berish."""
    user = update.effective_user
    logger.info(f"Foydalanuvchi DIREKTOR.UZ xizmatini tanladi: {user.id} ({user.full_name})")
    db_user = database.get_or_create_user(user.id, user.username, user.full_name)
    balance = db_user.get("balance", 0)
    price = 159000

    text = (
        "🎓 <b>DIREKTOR.UZ (Sertifikat) xizmati</b>\n\n"
        "Direktor.uz milliy platformasi orqali rasmiy malaka sertifikatini olish, test sinovlari va talablarni muvaffaqiyatli topshirishda kafolatlangan professional yordam.\n\n"
        "✨ <b>Xizmat afzalliklari:</b>\n"
        "• 100% ishonchli va kafolatlangan natija\n"
        "• Qisqa vaqt ichida sertifikatni rasmiylashtirish\n"
        "• Rasmiy tasdiqlangan davlat darajasidagi sertifikatga ega bo'lish\n\n"
        f"💵 <b>Xizmat narxi:</b> <b>159 000 so'm</b>\n"
        f"💰 <b>Sizning balansingiz:</b> <b>{balance:,} so'm</b>\n\n"
    )

    buttons = []
    if balance >= price:
        text += "✅ Balansingizda ushbu xizmat uchun yetarli mablag' mavjud! Buyurtma berish uchun quyidagi tugmani bosing:"
        buttons.append([InlineKeyboardButton("🛒 Buyurtma berish (159 000 so'm)", callback_data="order_service_direktor")])
    else:
        diff = price - balance
        text += (
            f"⚠️ Buyurtma berish uchun hisobingizda yana <b>{diff:,} so'm</b> yetishmayapti.\n"
            "Iltimos, hisobingizni to'ldiring yoki to'g'ridan-to'g'ri administratorga murojaat qiling:"
        )
        buttons.append([InlineKeyboardButton("💳 Hisobni to'ldirish", callback_data="btn_pay_start")])

    buttons.append([InlineKeyboardButton("👨‍💼 Administratorga yozish", url="https://t.me/ZeptoSlayd")])
    keyboard = InlineKeyboardMarkup(buttons)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
    elif update.message:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=keyboard)


async def handle_order_service_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Foydalanuvchi xizmatga buyurtma berganda balansdan yechish va adminga xabar yuborish."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    data = query.data

    is_audit = "audit" in data
    service_name = "AUDIT (Mustaqil ish)" if is_audit else "DIREKTOR.UZ (Sertifikat)"
    price = 59000 if is_audit else 159000

    bal = database.get_balance(user.id)
    if bal < price:
        await query.message.reply_text(
            f"⚠️ Balansingizda mablag' yetarli emas. Xizmat narxi: <b>{price:,} so'm</b>, sizda: <b>{bal:,} so'm</b>.",
            parse_mode="HTML"
        )
        return

    # Balansdan yechish
    database.deduct_balance(user.id, price)
    new_bal = database.get_balance(user.id)
    avail_slides = new_bal // 5000

    await query.message.reply_text(
        f"✅ <b>Buyurtmangiz muvaffaqiyatli qabul qilindi!</b>\n\n"
        f"📌 <b>Tanlangan xizmat:</b> {service_name}\n"
        f"💵 <b>To'langan summa:</b> <b>{price:,} so'm</b>\n"
        f"💰 <b>Qolgan balansingiz:</b> <b>{new_bal:,} so'm</b> ({avail_slides} ta taqdimot)\n\n"
        f"Batafsil ma'lumot olish yoki topshiriq mavzusini yuborish uchun administrator bilan bog'laning: @ZeptoSlayd",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("👨‍💼 Administratorga yozish", url="https://t.me/ZeptoSlayd")]
        ])
    )

    # Adminga buyurtma haqida ma'lumot yuborish
    admin_id = os.getenv("ADMIN_ID") or database.get_setting("admin_id")
    if admin_id:
        try:
            admin_msg = (
                f"🚨 <b>YANGI XIZMAT BUYURTMASI KELDI!</b>\n\n"
                f"📌 <b>Xizmat:</b> {service_name}\n"
                f"💵 <b>Summa:</b> {price:,} so'm (balansdan yechildi)\n\n"
                f"👤 <b>Mijoz:</b> {user.full_name}\n"
                f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
                f"Username: @{user.username or 'yo\'q'}\n"
            )
            await context.bot.send_message(
                chat_id=int(admin_id),
                text=admin_msg,
                parse_mode="HTML"
            )
        except Exception as e:
            logger.error(f"Adminga buyurtma xabari yuborishda xatolik: {e}")


async def handle_photo_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Foydalanuvchi to'lov cheki (rasm) yuborganda uni adminga tasdiqlash uchun yuborish."""
    user = update.effective_user
    if not update.message or not update.message.photo:
        return

    photo = update.message.photo[-1]
    photo_file_id = photo.file_id
    context.user_data["waiting_for_payment_receipt"] = False

    payment_id = database.create_payment(user.id, photo_file_id, 5000)

    await update.message.reply_text(
        "✅ <b>To'lov chekingiz qabul qilindi!</b>\n\n"
        "Chek administratorga tekshirish uchun yuborildi. "
        "To'lovingiz tasdiqlanishi bilan hisobingiz to'ldiriladi va sizga bildirishnoma keladi. ⏳",
        parse_mode="HTML",
        reply_markup=get_main_reply_keyboard()
    )

    # Adminga yuborish
    admin_id = os.getenv("ADMIN_ID") or database.get_setting("admin_id")
    if admin_id:
        try:
            admin_text = (
                f"🔔 <b>YANGI TO'LOV CHEKI KELDI!</b>\n\n"
                f"👤 <b>Foydalanuvchi:</b> {user.full_name}\n"
                f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
                f"Username: @{user.username or 'yo\'q'}\n"
                f"To'lov kodi: #{payment_id}\n\n"
                f"Tasdiqlash uchun summani tanlang:"
            )
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("✅ +5 000", callback_data=f"pay_approve_{payment_id}_5000"),
                    InlineKeyboardButton("✅ +10 000", callback_data=f"pay_approve_{payment_id}_10000"),
                    InlineKeyboardButton("✅ +15 000", callback_data=f"pay_approve_{payment_id}_15000")
                ],
                [
                    InlineKeyboardButton("✅ +30 000", callback_data=f"pay_approve_{payment_id}_30000"),
                    InlineKeyboardButton("✅ +50 000", callback_data=f"pay_approve_{payment_id}_50000"),
                    InlineKeyboardButton("✅ +59 000 (Audit)", callback_data=f"pay_approve_{payment_id}_59000")
                ],
                [
                    InlineKeyboardButton("✅ +159 000 (Direktor)", callback_data=f"pay_approve_{payment_id}_159000"),
                    InlineKeyboardButton("✏️ Boshqa summa kiritish", callback_data=f"pay_custom_{payment_id}")
                ],
                [
                    InlineKeyboardButton("❌ Rad etish", callback_data=f"pay_reject_{payment_id}")
                ]
            ])
            await context.bot.send_photo(
                chat_id=int(admin_id),
                photo=photo_file_id,
                caption=admin_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            logger.info(f"To'lov #{payment_id} adminga ({admin_id}) yuborildi.")
        except Exception as e:
            logger.error(f"Adminga to'lov chekini yuborishda xatolik: {e}")
    else:
        logger.warning(f"ADMIN_ID aniqlanmagan! To'lov #{payment_id} saqlandi, lekin adminga yuborilmadi.")


async def handle_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin tomonidan to'lovni tasdiqlash yoki rad etish."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("pay_approve_"):
        parts = data.split("_")
        pay_id = int(parts[2])
        amount = int(parts[3]) if len(parts) > 3 else 5000
        target_user_id = database.approve_payment(pay_id, amount)
        if target_user_id:
            new_bal = database.get_balance(target_user_id)
            avail = new_bal // 5000
            await query.edit_message_caption(
                caption=(
                    f"✅ <b>TO'LOV TASDIQLANDI!</b>\n\n"
                    f"Foydalanuvchi: ID <code>{target_user_id}</code>\n"
                    f"Hisobiga: <b>+{amount:,} so'm</b> qo'shildi.\n"
                    f"Mavjud balansi: <b>{new_bal:,} so'm</b> ({avail} ta taqdimot)."
                ),
                parse_mode="HTML"
            )
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=(
                        "🎉 <b>To'lovingiz tasdiqlandi!</b>\n\n"
                        f"Hisobingizga <b>+{amount:,} so'm</b> qo'shildi. "
                        f"Hozirgi balansingiz: <b>{new_bal:,} so'm</b> ({avail} ta taqdimot).\n\n"
                        "Endi pastdagi <b>«📊 Yangi taqdimot yaratish»</b> tugmasini bosib taqdimot yaratishingiz mumkin! 🚀"
                    ),
                    parse_mode="HTML",
                    reply_markup=get_main_reply_keyboard()
                )
            except Exception as e:
                logger.warning(f"Foydalanuvchiga tasdiqlash xabari yuborilmadi: {e}")
        else:
            await query.message.reply_text("⚠️ Ushbu to'lov cheki allaqachon ko'rib chiqilgan.")

    elif data.startswith("pay_custom_"):
        pay_id = int(data.replace("pay_custom_", ""))
        context.user_data["admin_custom_pay_id"] = pay_id
        await query.message.reply_text(
            f"✍️ <b>#{pay_id}-sonli to'lov uchun summani kiriting:</b>\n\n"
            f"Ixtiyoriy summani (masalan: <code>30000</code> yoki <code>50000</code>) shunchaki raqam shaklida yozib yuboring:",
            parse_mode="HTML"
        )

    elif data.startswith("pay_reject_"):
        pay_id = int(data.replace("pay_reject_", ""))
        target_user_id = database.reject_payment(pay_id)
        if target_user_id:
            await query.edit_message_caption(
                caption=f"❌ <b>TO'LOV RAD ETILDI!</b>\n\nFoydalanuvchi: ID <code>{target_user_id}</code>",
                parse_mode="HTML"
            )
            try:
                await context.bot.send_message(
                    chat_id=target_user_id,
                    text=(
                        "❌ <b>Kechirasiz, to'lov chekingiz tasdiqlanmadi.</b>\n\n"
                        "Iltimos, to'lov ma'lumotlarini tekshirib, qaytadan to'g'ri chekni yuboring yoki administratorga murojaat qiling."
                    ),
                    parse_mode="HTML",
                    reply_markup=get_main_reply_keyboard()
                )
            except Exception as e:
                logger.warning(f"Foydalanuvchiga rad xabari yuborilmadi: {e}")
        else:
            await query.message.reply_text("⚠️ Ushbu to'lov cheki allaqachon ko'rib chiqilgan.")


async def handle_admin_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin to'lov summasini qo'lda raqam qilib yozganda (masalan: 30000, 50000 va h.k.)."""
    user = update.effective_user
    if not update.message or not update.message.text:
        return

    admin_id = os.getenv("ADMIN_ID") or database.get_setting("admin_id")
    if not admin_id or str(user.id) != str(admin_id):
        return

    text = update.message.text.strip().replace(" ", "").replace("so'm", "").replace("som", "").replace(",", "")
    if not text.isdigit():
        return

    amount = int(text)
    if amount <= 0:
        return

    pay_id = context.user_data.get("admin_custom_pay_id")
    
    # Agar admin chek xabariga reply qilgan bo'lsa
    if not pay_id and update.message.reply_to_message:
        reply = update.message.reply_to_message
        caption = reply.caption or reply.text or ""
        if "To'lov kodi: #" in caption:
            try:
                code_part = caption.split("To'lov kodi: #")[1].split()[0].replace("\n", "")
                pay_id = int(code_part)
            except Exception:
                pass

    # Agar hali ham aniqlanmagan bo'lsa, eng oxirgi kutilayotgan (pending) to'lovni olamiz
    if not pay_id:
        with database.get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM payments WHERE status = 'pending' ORDER BY id DESC LIMIT 1")
            row = cursor.fetchone()
            if row:
                pay_id = row["id"]

    if not pay_id:
        # Hech qanday to'lov kutilmayotgan bo'lsa, xalaqit bermaymiz
        return

    # Kutilayotgan holatni tozalaymiz
    context.user_data.pop("admin_custom_pay_id", None)

    # To'lovni tasdiqlash
    target_user_id = database.approve_payment(pay_id, amount)
    if target_user_id:
        new_bal = database.get_balance(target_user_id)
        avail = new_bal // 5000
        await update.message.reply_text(
            f"✅ <b>TO'LOV TASDIQLANDI!</b>\n\n"
            f"To'lov kodi: #{pay_id}\n"
            f"Foydalanuvchi: ID <code>{target_user_id}</code>\n"
            f"Hisobiga qo'shildi: <b>+{amount:,} so'm</b>\n"
            f"Mavjud balansi: <b>{new_bal:,} so'm</b> ({avail} ta taqdimot).",
            parse_mode="HTML"
        )
        try:
            await context.bot.send_message(
                chat_id=target_user_id,
                text=(
                    "🎉 <b>To'lovingiz tasdiqlandi!</b>\n\n"
                    f"Hisobingizga <b>+{amount:,} so'm</b> qo'shildi. "
                    f"Hozirgi balansingiz: <b>{new_bal:,} so'm</b> ({avail} ta taqdimot).\n\n"
                    "Endi botdan bemalol taqdimot yoki xizmatlarga buyurtma berishingiz mumkin! 🚀"
                ),
                parse_mode="HTML",
                reply_markup=get_main_reply_keyboard()
            )
        except Exception as e:
            logger.warning(f"Foydalanuvchiga tasdiqlash xabari yuborilmadi: {e}")
    else:
        await update.message.reply_text(f"⚠️ #{pay_id}-sonli to'lov allaqachon ko'rib chiqilgan yoki topilmadi.")


async def cmd_myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Foydalanuvchining shaxsiy Telegram ID sini ko'rsatish."""
    user = update.effective_user
    await update.message.reply_text(
        f"🆔 <b>Sizning Telegram ID raqamingiz:</b> <code>{user.id}</code>\n"
        f"👤 <b>Ism:</b> {user.full_name}",
        parse_mode="HTML"
    )


async def cmd_setadmin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Bot yaratuvchisi o'zini admin qilib tayinlashi."""
    user = update.effective_user
    current_admin = os.getenv("ADMIN_ID") or database.get_setting("admin_id")
    if not current_admin:
        database.set_setting("admin_id", str(user.id))
        database.add_balance(user.id, 500000)
        await update.message.reply_text(
            f"👑 <b>Tabriklaymiz! Siz bot administratori sifatida tayinlandingiz!</b>\n\n"
            f"ID: <code>{user.id}</code>\n"
            f"Barcha to'lov cheklari endi to'g'ridan-to'g'ri sizga keladi.\n"
            f"Hisobingizga erkin test uchun 500 000 so'm (100 ta taqdimot) balansi biriktirildi.",
            parse_mode="HTML"
        )
    elif str(current_admin) == str(user.id):
        await update.message.reply_text(f"👑 Siz allaqachon bot administratorisiz (ID: <code>{user.id}</code>).", parse_mode="HTML")
    else:
        await update.message.reply_text("⛔ Administrator allaqachon tayinlangan.", parse_mode="HTML")


async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Administrator paneli."""
    user = update.effective_user
    admin_id = os.getenv("ADMIN_ID") or database.get_setting("admin_id")
    if not admin_id:
        await update.message.reply_text(
            "⚠️ Administrator hali belgilanmagan.\n"
            "O'zingizni admin qilish uchun /setadmin buyrug'ini bosing.",
            parse_mode="HTML"
        )
        return

    if str(user.id) != str(admin_id):
        await update.message.reply_text("⛔ Siz bot administratori emassiz.")
        return

    user_count = database.get_users_count()
    card_number = os.getenv("CARD_NUMBER", "5614682115402218")
    card_owner = os.getenv("CARD_OWNER", "Norqoziyev Ahrorbek")

    text = (
        f"👑 <b>ADMINISTRATOR BOSHQARUV PANELI</b>\n\n"
        f"👥 <b>Jami foydalanuvchilar:</b> {user_count} nafar\n"
        f"💵 <b>1 ta slayd narxi:</b> 5 000 so'm\n"
        f"💳 <b>Karta:</b> <code>{card_number}</code> ({card_owner})\n\n"
        f"<b>Buyruqlar:</b>\n"
        f"• <code>/addbalance &lt;user_id&gt; &lt;summa&gt;</code> — Foydalanuvchiga pul balansi qo'shish\n"
        f"<i>(Masalan: /addbalance {user.id} 15000)</i>"
    )
    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_addbalance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Adminga ixtiyoriy foydalanuvchiga balans qo'shish imkoniyati."""
    user = update.effective_user
    admin_id = os.getenv("ADMIN_ID") or database.get_setting("admin_id")
    if not admin_id or str(user.id) != str(admin_id):
        await update.message.reply_text("⛔ Bu buyruq faqat administrator uchun.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Format: <code>/addbalance &lt;user_id&gt; &lt;summa_so'mda&gt;</code>\nMasalan: <code>/addbalance 1234567 15000</code>", parse_mode="HTML")
        return

    try:
        target_uid = int(args[0])
        amount = int(args[1])
        new_b = database.add_balance(target_uid, amount)
        avail = new_b // 5000
        await update.message.reply_text(
            f"✅ Foydalanuvchi (ID: <code>{target_uid}</code>) balansiga <b>+{amount:,} so'm</b> qo'shildi.\nJami balansi: <b>{new_b:,} so'm</b> ({avail} ta taqdimot).",
            parse_mode="HTML"
        )
        try:
            await context.bot.send_message(
                chat_id=target_uid,
                text=f"🎁 <b>Administrator hisobingizga +{amount:,} so'm qo'shdi!</b>\nHozirgi balansingiz: <b>{new_b:,} so'm</b> ({avail} ta taqdimot).",
                parse_mode="HTML",
                reply_markup=get_main_reply_keyboard()
            )
        except Exception:
            pass
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")


async def start_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """2. Dizayn tanlash bosqichiga o'tish (Balans tekshiruvi bilan)."""
    query = update.callback_query
    if query:
        await query.answer()

    user = update.effective_user
    admin_id = os.getenv("ADMIN_ID") or database.get_setting("admin_id")
    is_admin = bool(admin_id and str(user.id) == str(admin_id))

    bal = database.get_balance(user.id)
    if bal < 5000 and not is_admin:
        text = (
            "⚠️ <b>Hisobingizda yetarli mablag' mavjud emas!</b>\n\n"
            f"💰 Sizning balansingiz: <b>{bal:,} so'm</b>\n"
            f"1 ta akademik taqdimot narxi: <b>5 000 so'm</b>\n\n"
            "Yangi taqdimot yaratish uchun iltimos, hisobingizni to'ldiring.\n"
            "Pastdagi <b>«💳 Hisobni to'ldirish»</b> tugmasini bosing:"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Hisobni to'ldirish", callback_data="btn_pay_start")]
        ])
        target_msg = query.message if query else update.message
        await target_msg.reply_text(text, parse_mode="HTML", reply_markup=keyboard)
        return ConversationHandler.END

    # Ma'lumotlarni boshlang'ich holatga keltirish
    context.user_data["pres_data"] = {
        "theme_id": "ion",
        "logo_path": None,
        "author_name": "",
        "group_name": "",
        "university_name": None,
        "topic": "",
        "slide_count": 5,
        "slides_content": None,
        "manual_slides": [],
        "current_manual_idx": 2,
        "temp_files": [],
        "is_retheme": False
    }

    # Katalog rasmi mavjud bo'lmasa, generatsiya qilamiz
    if not os.path.exists(CATALOG_PATH):
        generate_catalog_image(CATALOG_PATH)

    caption = (
        "🎨 <b>1-QADAM: Dizaynni tanlang</b>\n\n"
        "Taqdimotingiz qaysi rang va uslubda bo'lishini xohlaysiz? "
        "PowerPoint'ning eng mashhur 8 ta shablonidan birini tanlang:"
    )

    target_msg = query.message if query else update.message
    try:
        with open(CATALOG_PATH, "rb") as photo_file:
            await target_msg.reply_photo(
                photo=photo_file,
                caption=caption,
                parse_mode="HTML",
                reply_markup=get_theme_selection_keyboard()
            )
    except Exception as e:
        logger.error(f"Katalog rasmini yuborishda xatolik: {e}")
        await target_msg.reply_text(caption, parse_mode="HTML", reply_markup=get_theme_selection_keyboard())

    return STATE_SELECT_THEME


async def handle_theme_picked(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Dizayn tanlanganda: agar retheme bo'lsa to'g'ridan-to'g'ri qayta yasaydi, aks holda logotip so'raydi."""
    data = context.user_data.get("pres_data", {})
    if data.get("is_retheme"):
        return await handle_retheme_selection(update, context)

    query = update.callback_query
    await query.answer()

    theme_id = query.data.replace("theme_", "")
    theme = get_theme(theme_id)
    data["theme_id"] = theme_id

    text = (
        f"Siz <b>«{theme.name}»</b> dizaynini tanladingiz! ✨\n\n"
        f"🏛 <b>2-QADAM: Universitet logotipi</b>\n\n"
        f"Agar logotip bo'lsa, uni <b>rasm (foto)</b> sifatida yuboring.\n"
        f"Agar logotip kerak bo'lmasa, quyidagi «⏩ O'tkazib yuborish» tugmasini bosing:"
    )

    await query.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=get_back_cancel_keyboard(show_skip=True, show_default_logo=True)
    )
    return STATE_INPUT_LOGO


async def handle_logo_default(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Foydalanuvchi mavjud standart logotipni tanlaganda."""
    query = update.callback_query
    await query.answer()
    default_logo = find_default_logo()
    data = context.user_data.setdefault("pres_data", {})
    data["logo_path"] = default_logo
    await query.message.reply_text("✅ Standart logotip muvaffaqiyatli tanlandi!")
    return await ask_author_name(update, context, via_query=True)


async def handle_logo_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Foydalanuvchi logotip rasmini yuborganda saqlash."""
    user_id = update.effective_user.id
    photo = update.message.photo[-1]

    os.makedirs(TEMP_DIR, exist_ok=True)
    logo_file_path = os.path.join(TEMP_DIR, f"logo_{user_id}_{photo.file_unique_id}.png")

    file = await photo.get_file()
    await file.download_to_drive(logo_file_path)

    data = context.user_data.setdefault("pres_data", {})
    data["logo_path"] = logo_file_path
    data.setdefault("temp_files", []).append(logo_file_path)

    await update.message.reply_text("✅ Logotip muvaffaqiyatli qabul qilindi!")
    return await ask_author_name(update, context)


async def handle_logo_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Logotipni o'tkazib yuborish."""
    query = update.callback_query
    await query.answer()
    data = context.user_data.setdefault("pres_data", {})
    data["logo_path"] = None
    return await ask_author_name(update, context, via_query=True)


async def handle_logo_invalid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Logotip o'rniga matn yuborilsa do'stona xabar."""
    await update.message.reply_text(
        "⚠️ Iltimos, logotipni <b>rasm (foto)</b> sifatida yuboring yoki quyidagi «⏩ O'tkazib yuborish» tugmasini bosing:",
        parse_mode="HTML",
        reply_markup=get_back_cancel_keyboard(show_skip=True)
    )
    return STATE_INPUT_LOGO


async def ask_author_name(update: Update, context: ContextTypes.DEFAULT_TYPE, via_query: bool = False) -> int:
    """Ism va familiyani so'rash."""
    text = (
        "👤 <b>3-QADAM: Ism va familiyangiz</b>\n\n"
        "Titul varaqda 'Bajardi:' qismida aks etadigan ism va familiyangizni kiriting:\n"
        "<i>(Masalan: Aziz Rahimov)</i>"
    )
    kb = get_back_cancel_keyboard(show_skip=False)

    if via_query and update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        target = update.callback_query.message if update.callback_query else update.message
        await target.reply_text(text, parse_mode="HTML", reply_markup=kb)

    return STATE_INPUT_AUTHOR


async def handle_author_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Ism-familiya kiritilganda guruhni so'rash."""
    text_val = update.message.text.strip()
    if len(text_val) < 3 or len(text_val) > 70:
        await update.message.reply_text(
            "⚠️ Iltimos, ism va familiyangizni to'liq kiriting (kamida 3 ta belgi):",
            reply_markup=get_back_cancel_keyboard(show_skip=False)
        )
        return STATE_INPUT_AUTHOR

    context.user_data["pres_data"]["author_name"] = text_val

    await update.message.reply_text(
        f"Qabul qilindi: <b>{text_val}</b>\n\n"
        f"🏫 <b>4-QADAM: Guruh nomi</b>\n\n"
        f"Guruhingiz nomini kiriting:\n"
        f"<i>(Masalan: 301-guruh yoki DI-22)</i>",
        parse_mode="HTML",
        reply_markup=get_back_cancel_keyboard(show_skip=False)
    )
    return STATE_INPUT_GROUP


async def handle_group_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guruh nomi kiritilgach universitet nomini so'rash."""
    group_val = update.message.text.strip()
    context.user_data["pres_data"]["group_name"] = group_val

    await update.message.reply_text(
        f"Qabul qilindi: <b>{group_val}</b>\n\n"
        f"🏛 <b>5-QADAM: Universitet / Ta'lim muassasasi nomi</b>\n\n"
        f"Universitet nomini kiriting (masalan: <i>Toshkent Davlat Universiteti</i>)\n"
        f"yoki «⏩ O'tkazib yuborish» tugmasini bosing:",
        parse_mode="HTML",
        reply_markup=get_back_cancel_keyboard(show_skip=True)
    )
    return STATE_INPUT_UNIVERSITY


async def handle_university_skip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Universitet nomini o'tkazib yuborish."""
    query = update.callback_query
    await query.answer()
    context.user_data["pres_data"]["university_name"] = None
    return await ask_topic(update, context, via_query=True)


async def handle_university_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Universitet nomi kiritilgach mavzuni so'rash."""
    uni_val = update.message.text.strip()
    context.user_data["pres_data"]["university_name"] = uni_val
    return await ask_topic(update, context, via_query=False)


async def ask_topic(update: Update, context: ContextTypes.DEFAULT_TYPE, via_query: bool = False) -> int:
    """Taqdimot mavzusini so'rash."""
    text = (
        "📌 <b>6-QADAM: Taqdimot mavzusi</b>\n\n"
        "Taqdimotingizning asosiy mavzusini kiriting:\n"
        "<i>(Masalan: Suniy Intellekt Asoslari va Rivojlanish Bosqichlari)</i>"
    )
    kb = get_back_cancel_keyboard(show_skip=False)

    if via_query and update.callback_query:
        await update.callback_query.message.reply_text(text, parse_mode="HTML", reply_markup=kb)
    else:
        target = update.callback_query.message if update.callback_query else update.message
        await target.reply_text(text, parse_mode="HTML", reply_markup=kb)

    return STATE_INPUT_TOPIC


async def handle_topic_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mavzu kiritilgach slaydlar sonini so'rash."""
    topic_val = update.message.text.strip()
    if len(topic_val) < 3:
        await update.message.reply_text(
            "⚠️ Mavzu juda qisqa. Iltimos, taqdimot mavzusini to'liqroq kiriting:",
            reply_markup=get_back_cancel_keyboard(show_skip=False)
        )
        return STATE_INPUT_TOPIC

    context.user_data["pres_data"]["topic"] = topic_val

    await update.message.reply_text(
        f"Mavzu: <b>«{topic_val}»</b>\n\n"
        f"📊 <b>7-QADAM: Slaydlar soni</b>\n\n"
        f"Taqdimotingiz jami nechta slayddan iborat bo'lsin? Kerakli miqdorni tanlang:",
        parse_mode="HTML",
        reply_markup=get_slide_count_keyboard()
    )
    return STATE_INPUT_SLIDE_COUNT


async def handle_slide_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Slaydlar soni tanlangach to'ldirish rejimini so'rash."""
    query = update.callback_query
    await query.answer()

    count = int(query.data.replace("count_", ""))
    context.user_data["pres_data"]["slide_count"] = count

    await query.message.reply_text(
        f"Slaydlar soni: <b>{count} ta</b>\n\n"
        f"⚙️ <b>8-QADAM: To'ldirish tartibi</b>\n\n"
        f"Slaydlar qanday to'ldirilishini tanlang:\n\n"
        f"• <b>⚡ Avtomatik to'ldirish:</b> Mavzuingiz bo'yicha ilmiy reja (Kirish, Asosiy qismlar, Xulosa, Adabiyotlar) va tayyor professional punktlar bilan taqdimot darhol shakllantiriladi.\n"
        f"• <b>✍️ Slaydlarni qo'lda kiritish:</b> Har bir slayd sarlavhasi va matnini o'zingiz birma-bir kiritasiz.",
        parse_mode="HTML",
        reply_markup=get_fill_mode_keyboard()
    )
    return STATE_INPUT_FILL_MODE


async def handle_fill_auto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Avtomatik to'ldirish tanlanganda taqdimotni generatsiya qilish."""
    query = update.callback_query
    await query.answer()

    status_msg = await query.message.reply_text(
        "⏳ <b>Taqdimot tayyorlanmoqda... 5%</b>\n"
        "<code>░░░░░░░░░░ 5%</code>",
        parse_mode="HTML"
    )

    data = context.user_data["pres_data"]
    user_id = update.effective_user.id
    gemini_key = os.getenv("GEMINI_API_KEY")
    pexels_key = os.getenv("PEXELS_API_KEY")

    async def on_progress(percent: int, text: str):
        try:
            bar_filled = percent // 10
            bar_empty = 10 - bar_filled
            progress_bar = f"<code>{'█' * bar_filled}{'░' * bar_empty} {percent}%</code>"
            await status_msg.edit_text(
                f"<b>{text}</b>\n\nJarayon: {progress_bar}",
                parse_mode="HTML"
            )
        except Exception:
            pass

    try:
        pptx_path, temp_images = await build_presentation_full(
            user_id=user_id,
            theme_id=data["theme_id"],
            topic=data["topic"],
            author_name=data["author_name"],
            group_name=data["group_name"],
            university_name=data["university_name"],
            logo_path=data["logo_path"],
            slide_count=data["slide_count"],
            custom_slides=None,
            progress_callback=on_progress,
            gemini_api_key=gemini_key,
            pexels_api_key=pexels_key
        )
        data["temp_files"].append(pptx_path)
        data["temp_files"].extend(temp_images)

        theme = get_theme(data["theme_id"])

        # Balansdan 5 000 so'm yechish
        admin_id = os.getenv("ADMIN_ID") or database.get_setting("admin_id")
        if not (admin_id and str(user_id) == str(admin_id)):
            database.deduct_balance(user_id, 5000)
        rem_balance = database.get_balance(user_id)
        rem_slides = rem_balance // 5000

        caption = (
            f"🎉 <b>Taqdimotingiz muvaffaqiyatli tayyorlandi!</b>\n\n"
            f"📌 <b>Mavzu:</b> {data['topic']}\n"
            f"🎨 <b>Dizayn:</b> {theme.name}\n"
            f"📊 <b>Slaydlar:</b> {data['slide_count']} ta\n"
            f"🖼 <b>Tuzilishi:</b> Matnli va yarim-rasmli muvozanatli slaydlar\n"
            f"📝 <b>Matn:</b> Har slaydda boyitilgan matn (Times New Roman)\n"
            f"👤 <b>Bajardi:</b> {data['author_name']}\n"
            f"🏫 <b>Guruh:</b> {data['group_name']}\n\n"
            f"💰 <b>Qolgan balansingiz:</b> {rem_balance:,} so'm ({rem_slides} ta taqdimot)\n\n"
            f"<i>Faylni yuklab olib, bemalol tahrirlashingiz yoki namoyish etishingiz mumkin.</i>"
        )

        with open(pptx_path, "rb") as doc_file:
            await query.message.reply_document(
                document=doc_file,
                filename=os.path.basename(pptx_path),
                caption=caption,
                parse_mode="HTML",
                reply_markup=get_finish_keyboard()
            )

        try:
            await status_msg.delete()
        except Exception:
            pass

        _cleanup_temp_files(data)
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Taqdimot yaratishda xatolik: {e}", exc_info=True)
        await status_msg.edit_text(
            f"❌ Kechirasiz, taqdimotni shakllantirishda xatolik yuz berdi.\n"
            f"Iltimos, /start buyrug'i orqali qayta urinib ko'ring."
        )
        _cleanup_temp_files(data)
        return ConversationHandler.END


async def handle_fill_manual(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Qo'lda kiritish rejimi."""
    query = update.callback_query
    await query.answer()

    data = context.user_data["pres_data"]
    data["manual_slides"] = []
    data["current_manual_idx"] = 2

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Qolganlarini avtomatik to'ldirish", callback_data="manual_auto_complete")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="btn_cancel")]
    ])

    await query.message.reply_text(
        f"✍️ <b>2-slayd sarlavhasini kiriting:</b>\n"
        f"<i>(Jami slaydlar: {data['slide_count']} ta)</i>\n\n"
        f"Misol: <i>Mavzuning dolzarbligi</i>",
        parse_mode="HTML",
        reply_markup=kb
    )
    return STATE_INPUT_MANUAL_SLIDE_TITLE


async def handle_manual_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Qo'lda kiritilayotgan slayd sarlavhasi."""
    title_text = update.message.text.strip()
    data = context.user_data["pres_data"]

    data["temp_manual_title"] = title_text

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ Qolganlarini avtomatik to'ldirish", callback_data="manual_auto_complete")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="btn_cancel")]
    ])

    await update.message.reply_text(
        f"Sarlavha: <b>«{title_text}»</b>\n\n"
        f"Endi ushbu slayd uchun <b>matn yoki punktlarni</b> kiriting:\n"
        f"<i>(Har bir fikrni yangi qatordan yozishingiz mumkin)</i>",
        parse_mode="HTML",
        reply_markup=kb
    )
    return STATE_INPUT_MANUAL_SLIDE_BODY


async def handle_manual_body(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Qo'lda kiritilayotgan slayd matni va keyingi slaydga o'tish."""
    body_text = update.message.text.strip()
    data = context.user_data["pres_data"]

    bullets = [line.strip().lstrip("•-*0123456789. ") for line in body_text.split("\n") if line.strip()]
    if not bullets:
        bullets = [body_text]

    data["manual_slides"].append({
        "title": data.get("temp_manual_title", f"Slayd {data['current_manual_idx']}"),
        "bullets": bullets
    })

    data["current_manual_idx"] += 1
    total_needed = data["slide_count"]

    if data["current_manual_idx"] <= total_needed:
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ Qolganlarini avtomatik to'ldirish", callback_data="manual_auto_complete")],
            [InlineKeyboardButton("❌ Bekor qilish", callback_data="btn_cancel")]
        ])
        await update.message.reply_text(
            f"✅ Slayd saqlandi!\n\n"
            f"✍️ <b>{data['current_manual_idx']}-slayd sarlavhasini kiriting:</b>\n"
            f"<i>(Jami: {total_needed} ta slayd)</i>",
            parse_mode="HTML",
            reply_markup=kb
        )
        return STATE_INPUT_MANUAL_SLIDE_TITLE
    else:
        status_msg = await update.message.reply_text(
            "⏳ <b>Barcha slaydlar qabul qilindi. Taqdimot shakllantirilmoqda...</b>",
            parse_mode="HTML"
        )
        return await _generate_and_send_manual(update, context, status_msg)


async def handle_manual_auto_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Foydalanuvchi qolgan slaydlarni avtomatik to'ldirishni xohlasa."""
    query = update.callback_query
    await query.answer()

    data = context.user_data["pres_data"]
    status_msg = await query.message.reply_text(
        "⏳ <b>Qolgan slaydlar avtomatik to'ldirilmoqda va taqdimot yig'ilmoqda...</b>",
        parse_mode="HTML"
    )

    from slide_builder import get_automatic_slide_outline
    needed_total = data["slide_count"] - 1
    entered_count = len(data["manual_slides"])
    remaining = needed_total - entered_count

    if remaining > 0:
        auto_outline = get_automatic_slide_outline(data["topic"], data["slide_count"])
        data["manual_slides"].extend(auto_outline[entered_count:])

    return await _generate_and_send_manual(update, context, status_msg)


async def _generate_and_send_manual(update: Update, context: ContextTypes.DEFAULT_TYPE, status_msg) -> int:
    """Qo'lda kiritilgan slaydlar bilan PPTX yasash."""
    data = context.user_data["pres_data"]
    user_id = update.effective_user.id
    gemini_key = os.getenv("GEMINI_API_KEY")
    pexels_key = os.getenv("PEXELS_API_KEY")

    async def on_progress(percent: int, text: str):
        try:
            bar_filled = percent // 10
            bar_empty = 10 - bar_filled
            progress_bar = f"<code>{'█' * bar_filled}{'░' * bar_empty} {percent}%</code>"
            await status_msg.edit_text(
                f"<b>{text}</b>\n\nJarayon: {progress_bar}",
                parse_mode="HTML"
            )
        except Exception:
            pass

    try:
        pptx_path, temp_images = await build_presentation_full(
            user_id=user_id,
            theme_id=data["theme_id"],
            topic=data["topic"],
            author_name=data["author_name"],
            group_name=data["group_name"],
            university_name=data["university_name"],
            logo_path=data["logo_path"],
            slide_count=data["slide_count"],
            custom_slides=data.get("manual_slides"),
            progress_callback=on_progress,
            gemini_api_key=gemini_key,
            pexels_api_key=pexels_key
        )
        data["temp_files"].append(pptx_path)
        data["temp_files"].extend(temp_images)

        theme = get_theme(data["theme_id"])

        # Balansdan 5 000 so'm yechish
        admin_id = os.getenv("ADMIN_ID") or database.get_setting("admin_id")
        if not (admin_id and str(user_id) == str(admin_id)):
            database.deduct_balance(user_id, 5000)
        rem_balance = database.get_balance(user_id)
        rem_slides = rem_balance // 5000

        caption = (
            f"🎉 <b>Taqdimotingiz muvaffaqiyatli tayyorlandi!</b>\n\n"
            f"📌 <b>Mavzu:</b> {data['topic']}\n"
            f"🎨 <b>Dizayn:</b> {theme.name}\n"
            f"📊 <b>Slaydlar:</b> {len(data['manual_slides']) + 1} ta\n"
            f"🖼 <b>Tuzilishi:</b> Matnli va yarim-rasmli muvozanatli slaydlar\n"
            f"📝 <b>Matn:</b> Har slaydda boyitilgan matn (Times New Roman)\n"
            f"👤 <b>Bajardi:</b> {data['author_name']}\n"
            f"🏫 <b>Guruh:</b> {data['group_name']}\n\n"
            f"💰 <b>Qolgan balansingiz:</b> {rem_balance:,} so'm ({rem_slides} ta taqdimot)"
        )

        with open(pptx_path, "rb") as doc_file:
            msg_target = update.callback_query.message if update.callback_query else update.message
            await msg_target.reply_document(
                document=doc_file,
                filename=os.path.basename(pptx_path),
                caption=caption,
                parse_mode="HTML",
                reply_markup=get_finish_keyboard()
            )

        try:
            await status_msg.delete()
        except Exception:
            pass

        _cleanup_temp_files(data)
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Qo'lda kiritilgan taqdimotni yasashda xatolik: {e}", exc_info=True)
        await status_msg.edit_text("❌ Taqdimotni shakllantirishda xatolik yuz berdi. Iltimos, /start ni bosing.")
        _cleanup_temp_files(data)
        return ConversationHandler.END


# ==========================================
# RETHEME (Boshqa dizaynda qayta yaratish)
# ==========================================

async def handle_retheme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Foydalanuvchi ma'lumotlarni qayta kiritmasdan, boshqa dizaynda darhol qayta yaratish."""
    query = update.callback_query
    await query.answer()

    data = context.user_data.get("pres_data")
    if not data or not data.get("topic"):
        await query.message.reply_text(
            "Ma'lumotlar eskirgan. Yangi taqdimot yaratish uchun quyidagi tugmani bosing:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📊 Yangi taqdimot", callback_data="start_creation")]])
        )
        return ConversationHandler.END

    caption = (
        "🎨 <b>Taqdimotingiz uchun yangi dizayn tanlang:</b>\n"
        "Barcha kiritilgan ma'lumotlaringiz (mavzu, ism, guruh, slaydlar) saqlab qolingan!"
    )

    if os.path.exists(CATALOG_PATH):
        with open(CATALOG_PATH, "rb") as photo_file:
            await query.message.reply_photo(
                photo=photo_file,
                caption=caption,
                parse_mode="HTML",
                reply_markup=get_theme_selection_keyboard()
            )
    else:
        await query.message.reply_text(caption, parse_mode="HTML", reply_markup=get_theme_selection_keyboard())

    data["is_retheme"] = True
    return STATE_SELECT_THEME


async def handle_retheme_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Retheme rejimida yangi dizayn tanlanganda darhol qayta yaratish."""
    query = update.callback_query
    await query.answer()

    data = context.user_data["pres_data"]
    theme_id = query.data.replace("theme_", "")
    data["theme_id"] = theme_id
    theme = get_theme(theme_id)

    status_msg = await query.message.reply_text(
        f"⏳ Taqdimot <b>«{theme.name}»</b> dizaynida qayta shakllantirilmoqda...",
        parse_mode="HTML"
    )

    user_id = update.effective_user.id
    gemini_key = os.getenv("GEMINI_API_KEY")
    pexels_key = os.getenv("PEXELS_API_KEY")

    async def on_progress(percent: int, text: str):
        try:
            bar_filled = percent // 10
            bar_empty = 10 - bar_filled
            progress_bar = f"<code>{'█' * bar_filled}{'░' * bar_empty} {percent}%</code>"
            await status_msg.edit_text(
                f"<b>{text}</b>\n\nJarayon: {progress_bar}",
                parse_mode="HTML"
            )
        except Exception:
            pass

    try:
        pptx_path, temp_images = await build_presentation_full(
            user_id=user_id,
            theme_id=data["theme_id"],
            topic=data["topic"],
            author_name=data["author_name"],
            group_name=data["group_name"],
            university_name=data["university_name"],
            logo_path=data["logo_path"],
            slide_count=data["slide_count"],
            custom_slides=data.get("manual_slides"),
            progress_callback=on_progress,
            gemini_api_key=gemini_key,
            pexels_api_key=pexels_key
        )
        data["temp_files"].append(pptx_path)
        data["temp_files"].extend(temp_images)

        caption = (
            f"🎉 <b>Yangi dizayndagi taqdimotingiz tayyor!</b>\n\n"
            f"📌 <b>Mavzu:</b> {data['topic']}\n"
            f"🎨 <b>Yangi Dizayn:</b> {theme.name}\n"
            f"📊 <b>Slaydlar:</b> {data['slide_count']} ta\n"
            f"🖼 <b>Tuzilishi:</b> Matnli va yarim-rasmli muvozanatli slaydlar\n"
            f"📝 <b>Matn:</b> Har slaydda boyitilgan matn (Times New Roman)\n"
            f"👤 <b>Bajardi:</b> {data['author_name']}\n"
            f"🏫 <b>Guruh:</b> {data['group_name']}"
        )

        with open(pptx_path, "rb") as doc_file:
            await query.message.reply_document(
                document=doc_file,
                filename=os.path.basename(pptx_path),
                caption=caption,
                parse_mode="HTML",
                reply_markup=get_finish_keyboard()
            )

        try:
            await status_msg.delete()
        except Exception:
            pass

        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Retheme qilishda xatolik: {e}", exc_info=True)
        await status_msg.edit_text("❌ Qayta shakllantirishda xatolik yuz berdi. Iltimos, /start ni bosing.")
        return ConversationHandler.END


# ==========================================
# ANIQ ORQAGA QAYTISH BOSHQARUVI
# ==========================================

async def back_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Dizayn tanlashdan /start ga qaytish."""
    query = update.callback_query
    await query.answer()
    return await cmd_start(update, context)

async def back_to_theme(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Logotipdan Dizayn tanlashga qaytish."""
    return await start_creation(update, context)

async def back_to_logo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muallif nomidan Logotip kiritishga qaytish."""
    query = update.callback_query
    await query.answer()
    text = (
        "🏛 <b>2-QADAM: Universitet logotipi</b>\n\n"
        "Logotipni <b>rasm (foto)</b> sifatida yuboring yoki quyidagi tugmani bosing:"
    )
    await query.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=get_back_cancel_keyboard(show_skip=True)
    )
    return STATE_INPUT_LOGO

async def back_to_author(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guruh nomidan Muallif nomiga qaytish."""
    query = update.callback_query
    await query.answer()
    return await ask_author_name(update, context, via_query=True)

async def back_to_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Universitet nomidan Guruh nomiga qaytish."""
    query = update.callback_query
    await query.answer()
    text = (
        "🏫 <b>4-QADAM: Guruh nomi</b>\n\n"
        "Guruhingiz nomini kiriting:\n"
        "<i>(Masalan: 301-guruh yoki DI-22)</i>"
    )
    await query.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=get_back_cancel_keyboard(show_skip=False)
    )
    return STATE_INPUT_GROUP

async def back_to_university(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Mavzudan Universitet nomiga qaytish."""
    query = update.callback_query
    await query.answer()
    text = (
        "🏛 <b>5-QADAM: Universitet / Ta'lim muassasasi nomi</b>\n\n"
        "Universitet nomini kiriting yoki «⏩ O'tkazib yuborish» tugmasini bosing:"
    )
    await query.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=get_back_cancel_keyboard(show_skip=True)
    )
    return STATE_INPUT_UNIVERSITY

async def back_to_topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Slaydlar sonidan Mavzu kiritishga qaytish."""
    query = update.callback_query
    await query.answer()
    return await ask_topic(update, context, via_query=True)

async def back_to_slide_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """To'ldirish rejimidan Slaydlar soniga qaytish."""
    query = update.callback_query
    await query.answer()
    data = context.user_data.get("pres_data", {})
    text = (
        f"Mavzu: <b>«{data.get('topic', '')}»</b>\n\n"
        f"📊 <b>7-QADAM: Slaydlar soni</b>\n\n"
        f"Taqdimotingiz jami nechta slayddan iborat bo'lsin? Kerakli miqdorni tanlang:"
    )
    await query.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=get_slide_count_keyboard()
    )
    return STATE_INPUT_SLIDE_COUNT

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Har qanday bosqichda bekor qilish."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.message.reply_text(
            "❌ <b>Amal bekor qilindi.</b>\n\n"
            "Yangi taqdimot yaratish uchun quyidagi tugmani bosing:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📊 Yangi taqdimot", callback_data="start_creation")]])
        )
    elif update.message:
        await update.message.reply_text(
            "❌ <b>Amal bekor qilindi.</b>\n"
            "Yangi taqdimot yaratish uchun /start buyrug'ini bosing.",
            parse_mode="HTML"
        )

    if "pres_data" in context.user_data:
        _cleanup_temp_files(context.user_data["pres_data"])
        context.user_data.pop("pres_data", None)

    return ConversationHandler.END

def _cleanup_temp_files(data: Dict[str, Any]) -> None:
    """Fayllar yuborilgach, vaqtinchalik logotiplar va PPTX fayllarni xavfsiz tozalash."""
    if not data:
        return
    temp_files = data.get("temp_files", [])
    for path in temp_files:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception as e:
            logger.warning(f"Vaqtinchalik faylni o'chirishda xatolik ({path}): {e}")


# ==========================================
# CONVERSATION HANDLER FABRIKASI
# ==========================================

def get_conversation_handler() -> ConversationHandler:
    """Botning barcha bosqichlarini bog'lovchi ConversationHandler."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("start", cmd_start),
            CallbackQueryHandler(start_creation, pattern="^start_creation$"),
            CallbackQueryHandler(start_creation, pattern="^action_new$"),
            CallbackQueryHandler(handle_retheme, pattern="^action_retheme$"),
            MessageHandler(filters.Regex(r"^(📊 Yangi taqdimot yaratish|Yangi taqdimot)$"), start_creation)
        ],
        states={
            STATE_SELECT_THEME: [
                CallbackQueryHandler(handle_theme_picked, pattern="^theme_"),
                CallbackQueryHandler(handle_cancel, pattern="^btn_cancel$")
            ],
            STATE_INPUT_LOGO: [
                MessageHandler(filters.PHOTO, handle_logo_photo),
                CallbackQueryHandler(handle_logo_default, pattern="^btn_use_default_logo$"),
                CallbackQueryHandler(handle_logo_skip, pattern="^btn_skip$"),
                CallbackQueryHandler(back_to_theme, pattern="^btn_back$"),
                CallbackQueryHandler(handle_cancel, pattern="^btn_cancel$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_logo_invalid)
            ],
            STATE_INPUT_AUTHOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_author_input),
                CallbackQueryHandler(back_to_logo, pattern="^btn_back$"),
                CallbackQueryHandler(handle_cancel, pattern="^btn_cancel$")
            ],
            STATE_INPUT_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_group_input),
                CallbackQueryHandler(back_to_author, pattern="^btn_back$"),
                CallbackQueryHandler(handle_cancel, pattern="^btn_cancel$")
            ],
            STATE_INPUT_UNIVERSITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_university_input),
                CallbackQueryHandler(handle_university_skip, pattern="^btn_skip$"),
                CallbackQueryHandler(back_to_group, pattern="^btn_back$"),
                CallbackQueryHandler(handle_cancel, pattern="^btn_cancel$")
            ],
            STATE_INPUT_TOPIC: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_topic_input),
                CallbackQueryHandler(back_to_university, pattern="^btn_back$"),
                CallbackQueryHandler(handle_cancel, pattern="^btn_cancel$")
            ],
            STATE_INPUT_SLIDE_COUNT: [
                CallbackQueryHandler(handle_slide_count, pattern="^count_"),
                CallbackQueryHandler(back_to_topic, pattern="^btn_back$"),
                CallbackQueryHandler(handle_cancel, pattern="^btn_cancel$")
            ],
            STATE_INPUT_FILL_MODE: [
                CallbackQueryHandler(handle_fill_auto, pattern="^fill_auto$"),
                CallbackQueryHandler(handle_fill_manual, pattern="^fill_manual$"),
                CallbackQueryHandler(back_to_slide_count, pattern="^btn_back$"),
                CallbackQueryHandler(handle_cancel, pattern="^btn_cancel$")
            ],
            STATE_INPUT_MANUAL_SLIDE_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_title),
                CallbackQueryHandler(handle_manual_auto_complete, pattern="^manual_auto_complete$"),
                CallbackQueryHandler(handle_cancel, pattern="^btn_cancel$")
            ],
            STATE_INPUT_MANUAL_SLIDE_BODY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_manual_body),
                CallbackQueryHandler(handle_manual_auto_complete, pattern="^manual_auto_complete$"),
                CallbackQueryHandler(handle_cancel, pattern="^btn_cancel$")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", handle_cancel),
            CommandHandler("start", cmd_start),
            MessageHandler(filters.Regex(r"^(📊 Yangi taqdimot yaratish|Yangi taqdimot)$"), start_creation),
            MessageHandler(filters.Regex(r"^(💰 Balans|Balans)$"), handle_balance_button),
            MessageHandler(filters.Regex(r"^(💳 Hisobni to'ldirish|💳 To'lov|To'lov)$"), handle_payment_request),
            MessageHandler(filters.Regex(r"^(📑\s*)?AUDIT\s*\(mustaqil ish\)"), handle_audit_service),
            MessageHandler(filters.Regex(r"^(🎓\s*)?DIREKTOR\.UZ\s*\(sertifikat\)"), handle_direktor_service),
            CallbackQueryHandler(handle_cancel, pattern="^btn_cancel$")
        ],
        allow_reentry=True,
        per_user=True,
        per_chat=True,
        per_message=False
    )
