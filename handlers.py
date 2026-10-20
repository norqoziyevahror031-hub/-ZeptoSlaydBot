import os
import logging
from typing import Dict, Any

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
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
    """6 ta dizaynni 2 ustunda ko'rsatuvchi tugmalar."""
    keyboard = [
        [
            InlineKeyboardButton("🏛 Klassik", callback_data="theme_classic"),
            InlineKeyboardButton("💎 Zamonaviy", callback_data="theme_modern")
        ],
        [
            InlineKeyboardButton("⚪ Minimal", callback_data="theme_minimal"),
            InlineKeyboardButton("🌿 Yashil tabiat", callback_data="theme_nature")
        ],
        [
            InlineKeyboardButton("👑 Qizil-oltin", callback_data="theme_royal"),
            InlineKeyboardButton("🌙 Qorong'i rejim", callback_data="theme_dark")
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
    """1. /start bosilganda kutib olish va 'Yangi taqdimot' tugmasi."""
    user = update.effective_user
    first_name = user.first_name if user else "Talaba"

    welcome_text = (
        f"Assalomu alaykum, {first_name}! 👋\n\n"
        f"Men akademik taqdimotlar (.pptx) tayyorlab beruvchi botman.\n"
        f"Hech qanday murakkab buyruqlarni o'rganishingiz shart emas — "
        f"barcha amallar tugmalar orqali qulay va tez bajariladi! 🚀\n\n"
        f"Boshlash uchun quyidagi tugmani bosing:"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Yangi taqdimot yaratish", callback_data="start_creation")]
    ])

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(welcome_text, reply_markup=keyboard)
    else:
        await update.message.reply_text(welcome_text, reply_markup=keyboard)

    return ConversationHandler.END


async def start_creation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """2. Dizayn tanlash bosqichiga o'tish."""
    query = update.callback_query
    if query:
        await query.answer()

    # Ma'lumotlarni boshlang'ich holatga keltirish
    context.user_data["pres_data"] = {
        "theme_id": "classic",
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
        "Yuqoridagi namunadan o'zingizga ma'qul dizaynni tanlang:"
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
        caption = (
            f"🎉 <b>Taqdimotingiz muvaffaqiyatli tayyorlandi!</b>\n\n"
            f"📌 <b>Mavzu:</b> {data['topic']}\n"
            f"🎨 <b>Dizayn:</b> {theme.name}\n"
            f"📊 <b>Slaydlar:</b> {data['slide_count']} ta\n"
            f"🖼 <b>Rasmlar:</b> Har slaydda 4 tadan mavzuga oid rasm (2x2)\n"
            f"📝 <b>Matn:</b> Har slaydda 80-120 so'z (Times New Roman)\n"
            f"👤 <b>Bajardi:</b> {data['author_name']}\n"
            f"🏫 <b>Guruh:</b> {data['group_name']}\n\n"
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
        caption = (
            f"🎉 <b>Taqdimotingiz muvaffaqiyatli tayyorlandi!</b>\n\n"
            f"📌 <b>Mavzu:</b> {data['topic']}\n"
            f"🎨 <b>Dizayn:</b> {theme.name}\n"
            f"📊 <b>Slaydlar:</b> {len(data['manual_slides']) + 1} ta\n"
            f"🖼 <b>Rasmlar:</b> Har slaydda 4 tadan mavzuga oid rasm (2x2)\n"
            f"📝 <b>Matn:</b> Har slaydda 80-120 so'z (Times New Roman)\n"
            f"👤 <b>Bajardi:</b> {data['author_name']}\n"
            f"🏫 <b>Guruh:</b> {data['group_name']}"
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
            f"🖼 <b>Rasmlar:</b> Har slaydda 4 tadan mavzuga oid rasm (2x2)\n"
            f"📝 <b>Matn:</b> Har slaydda 80-120 so'z (Times New Roman)\n"
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
            CallbackQueryHandler(handle_retheme, pattern="^action_retheme$")
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
            CallbackQueryHandler(handle_cancel, pattern="^btn_cancel$")
        ],
        allow_reentry=True,
        per_user=True,
        per_chat=True,
        per_message=False
    )
