import os
import re
import time
import asyncio
import logging
from typing import List, Set, Optional, Tuple
from PIL import Image, ImageDraw
import httpx

from themes import Theme

logger = logging.getLogger(__name__)

TEMP_IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "temp", "images")
os.makedirs(TEMP_IMG_DIR, exist_ok=True)

STOCK_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "stock")

# O'zbekcha atamalarni inglizcha aniq qidiruv kalitlariga moslashtirish
UZ_TO_EN_MAP = {
    "moliya": "finance stock market",
    "iqtisod": "economy financial market",
    "bank": "banking financial investment",
    "biznes": "business meeting corporate",
    "buxgalteriya": "accounting financial audit",
    "marketing": "digital marketing analytics",
    "menejment": "corporate management leadership",
    "valyuta": "currency foreign exchange money",
    "daromad": "revenue profit investment income",
    "kapital": "capital wealth financial accumulation",
    "o'zbekiston": "uzbekistan economy business",
    "ozbekiston": "uzbekistan economy business",
    "sun'iy intellekt": "artificial intelligence technology",
    "suniy intellekt": "artificial intelligence technology",
    "ai": "artificial intelligence computer",
    "kiberxavfsizlik": "cybersecurity network digital",
    "dasturlash": "computer programming code",
    "axborot texnologiyalari": "information technology data",
    "robototexnika": "robotics automation cyber",
    "tibbiyot": "medicine healthcare doctor",
    "shifokor": "doctor hospital medical",
    "farmatsevtika": "pharmacy medical research",
    "fizika": "physics quantum science",
    "kimyo": "chemistry science laboratory",
    "biologiya": "biology genetics laboratory",
    "ekologiya": "green energy renewable ecology",
    "tabiat": "nature planet environment",
    "energetika": "solar power electric energy",
    "pedagogika": "education university study",
    "talaba": "student learning books library",
    "huquq": "law courthouse justice gavel",
    "xalqaro": "international diplomacy world globe",
    "tarix": "history museum ancient architecture",
    "arxitektura": "modern architecture building"
}


def translate_query_to_english(topic: str, slide_title: str) -> str:
    """Mavzu va sarlavha asosida 2-3 ta aniq inglizcha kalit so'z hosil qiladi."""
    text = f"{topic} {slide_title}".lower()
    for uz_word, en_query in UZ_TO_EN_MAP.items():
        if uz_word in text:
            return en_query
    return "business technology science research"


async def fetch_pexels_image(query: str, used_ids: Set[str], api_key: str) -> Optional[str]:
    """Pexels API orqali yuqori sifatli fotosurat qidirish."""
    if not api_key:
        return None

    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": api_key}
    params = {"query": query, "per_page": 10, "orientation": "landscape"}

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            res = await client.get(url, headers=headers, params=params)
            if res.status_code == 200:
                photos = res.json().get("photos", [])
                for p in photos:
                    pid = str(p.get("id"))
                    if pid not in used_ids:
                        used_ids.add(pid)
                        src = p.get("src", {})
                        img_url = src.get("large2x") or src.get("large") or src.get("medium")
                        if img_url:
                            return img_url
    except Exception as e:
        logger.warning(f"Pexels API xatoligi: {e}")
    return None


async def fetch_wikimedia_image(query: str, used_ids: Set[str]) -> Optional[str]:
    """Wikimedia Commons orqali bepul sifatli fotosurat qidirish."""
    url = "https://commons.wikimedia.org/w/api.php"
    headers = {"User-Agent": "SlidePresentationBot/2.0 (student.slide.generator@tift.uz)"}
    short_query = " ".join(query.split()[:2])
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": short_query,
        "gsrnamespace": 6,
        "gsrlimit": 8,
        "prop": "imageinfo",
        "iiprop": "url|mime",
        "iiurlwidth": 1200,
        "format": "json"
    }

    try:
        async with httpx.AsyncClient(timeout=8.0, headers=headers, follow_redirects=True) as client:
            res = await client.get(url, params=params)
            if res.status_code == 200:
                pages = res.json().get("query", {}).get("pages", {})
                for pid, pdata in pages.items():
                    str_pid = str(pid)
                    if str_pid in used_ids:
                        continue
                    infos = pdata.get("imageinfo", [])
                    if infos:
                        mime = infos[0].get("mime", "")
                        if mime in ("image/jpeg", "image/png"):
                            u = infos[0].get("thumburl") or infos[0].get("url")
                            if u and not u.endswith(".svg.png"):
                                used_ids.add(str_pid)
                                return u
    except Exception as e:
        logger.warning(f"Wikimedia API xatoligi: {e}")
    return None


async def download_image(url: str, output_path: str) -> Optional[str]:
    """Internetdan rasmni yuklab oladi."""
    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            res = await client.get(url)
            if res.status_code == 200 and len(res.content) > 5000:
                with open(output_path, "wb") as f:
                    f.write(res.content)
                return output_path
    except Exception as e:
        logger.warning(f"Rasmni yuklashda xatolik: {e}")
    return None


def process_and_round_image(
    input_path: str,
    output_path: str,
    target_w: int = 1140,
    target_h: int = 1030,
    corner_radius: int = 40,
    border_color: Tuple[int, int, int] = (210, 225, 245),
    border_width: int = 3
) -> str:
    """
    Rasmni slayddagi ajratilgan 5.7" x 5.15" o'lchamga moslab markazdan kesadi,
    burchaklarini silliq yumaloqlaydi (antialiased rounded corners) va nafis ramka chizadi.
    Natijada rasm slayd kartasi bilan 100% uyg'unlashib, chetlari chiroyli chiqadi.
    """
    try:
        with Image.open(input_path) as img:
            img = img.convert("RGB")
            src_w, src_h = img.size
            target_ratio = target_w / target_h
            src_ratio = src_w / src_h

            if src_ratio > target_ratio:
                new_w = int(src_h * target_ratio)
                left = (src_w - new_w) // 2
                box = (left, 0, left + new_w, src_h)
            else:
                new_h = int(src_w / target_ratio)
                top = (src_h - new_h) // 2
                box = (0, top, src_w, top + new_h)

            cropped = img.crop(box)
            resized = cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)

            # 2x supersampling orqali juda silliq va sifatli burchak maskasi
            scale = 2
            mask_w, mask_h = target_w * scale, target_h * scale
            mask = Image.new("L", (mask_w, mask_h), 0)
            draw_mask = ImageDraw.Draw(mask)
            draw_mask.rounded_rectangle(
                [0, 0, mask_w, mask_h],
                radius=corner_radius * scale,
                fill=255
            )
            mask = mask.resize((target_w, target_h), Image.Resampling.LANCZOS)

            rgba = resized.convert("RGBA")
            rgba.putalpha(mask)

            # Nafis chegara ramkasi (border)
            border_canvas = Image.new("RGBA", (mask_w, mask_h), (0, 0, 0, 0))
            draw_border = ImageDraw.Draw(border_canvas)
            bw_scaled = border_width * scale
            draw_border.rounded_rectangle(
                [bw_scaled // 2, bw_scaled // 2, mask_w - bw_scaled // 2, mask_h - bw_scaled // 2],
                radius=corner_radius * scale,
                outline=border_color + (255,),
                width=bw_scaled
            )
            border_resized = border_canvas.resize((target_w, target_h), Image.Resampling.LANCZOS)
            final_img = Image.alpha_composite(rgba, border_resized)

            final_img.save(output_path, "PNG")
            return output_path
    except Exception as e:
        logger.error(f"Rasmni qayta ishlashda xatolik ({input_path}): {e}")
        return input_path


def get_stock_fallback_image(topic: str, slide_idx: int, used_paths: Set[str]) -> Optional[str]:
    """
    Offline yoki zaxira uchun assets/stock papkasidan mavzuga oid
    haqiqiy professional fotosuratlarni oladi.
    """
    text = topic.lower()

    target_category = None
    if any(k in text for k in ["moliya", "iqtisod", "bank", "biznes", "buxgalter", "pul", "investitsiya"]):
        target_category = "finance"
    elif any(k in text for k in ["sun'iy", "ai", "dastur", "kiber", "texnologiya", "robot", "kompyuter"]):
        target_category = "tech"
    elif any(k in text for k in ["tibbiyot", "shifokor", "dori", "salomatlik"]):
        target_category = "medical"
    elif any(k in text for k in ["tabiat", "ekologiya", "quyosh", "energiya"]):
        target_category = "nature"
    elif any(k in text for k in ["talaba", "universitet", "kutubxona", "kitob", "pedagog"]):
        target_category = "education"
    elif any(k in text for k in ["kimyo", "fizika", "biologiya", "ilmiy", "laboratoriya"]):
        target_category = "science"

    concept_stock_images = [
        os.path.join(STOCK_DIR, "uzbekistan_digital_globe.png"),
        os.path.join(STOCK_DIR, "laptop_charts_growth_arrow.png"),
        os.path.join(STOCK_DIR, "hands_stacking_gold_coins.png"),
        os.path.join(STOCK_DIR, "isometric_market_analytics.png"),
        os.path.join(STOCK_DIR, "global_dollar_currency.png"),
        os.path.join(STOCK_DIR, "businessman_future_city_data.png"),
        os.path.join(STOCK_DIR, "hex_touch_analytics.png"),
        os.path.join(STOCK_DIR, "laptop_globe_network.png"),
        os.path.join(STOCK_DIR, "tablet_cloud_icons.png"),
        os.path.join(STOCK_DIR, "iqtisodiyot_candlestick_coins.png"),
        os.path.join(STOCK_DIR, "global_pie_finance.png"),
        os.path.join(STOCK_DIR, "tech_chart_hologram.png"),
        os.path.join(STOCK_DIR, "businessman_drawing_chart.png"),
        os.path.join(STOCK_DIR, "brain_circuit_tech.png"),
        os.path.join(STOCK_DIR, "3d_red_arrow_growth.png"),
        os.path.join(STOCK_DIR, "global_network.png"),
        os.path.join(STOCK_DIR, "robot_hand_coins.png"),
        os.path.join(STOCK_DIR, "head_profile_gears.png"),
        os.path.join(STOCK_DIR, "finance_calculator.png"),
        os.path.join(STOCK_DIR, "brain_gears_logic.png"),
        os.path.join(STOCK_DIR, "tablet_analytics.png"),
        os.path.join(STOCK_DIR, "coins_candlestick.png"),
        os.path.join(STOCK_DIR, "brain_logic_gear.png"),
        os.path.join(STOCK_DIR, "neon_brain_idea.png"),
        os.path.join(STOCK_DIR, "growth_stairs_idea.png")
    ]

    candidates = []
    candidates.extend([p for p in concept_stock_images if os.path.exists(p)])

    if target_category:
        cat_dir = os.path.join(STOCK_DIR, target_category)
        if os.path.isdir(cat_dir):
            for f in os.listdir(cat_dir):
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    candidates.append(os.path.join(cat_dir, f))

    if not candidates and os.path.isdir(STOCK_DIR):
        for root, _, files in os.walk(STOCK_DIR):
            for f in files:
                if f.lower().endswith(('.jpg', '.jpeg', '.png')):
                    candidates.append(os.path.join(root, f))

    seen_bases = set()
    unique_candidates = []
    for c in candidates:
        base = os.path.splitext(os.path.basename(c))[0].lower()
        if base not in seen_bases:
            seen_bases.add(base)
            unique_candidates.append(c)

    if not unique_candidates:
        return None

    unused = [c for c in unique_candidates if c not in used_paths]
    selected = unused[0] if unused else unique_candidates[slide_idx % len(unique_candidates)]
    used_paths.add(selected)
    return selected


async def get_slide_illustration(
    topic: str,
    slide_title: str,
    user_id: int,
    slide_idx: int,
    theme: Theme,
    used_ids: Optional[Set[str]] = None,
    pexels_api_key: Optional[str] = None
) -> str:
    """
    Slayd uchun haqiqiy, professional fotosuratni topadi, yuklaydi
    va slaydning ajratilgan joyiga 100% moslab yumaloq burchakli (PNG) qilib beradi.
    """
    if used_ids is None:
        used_ids = set()

    timestamp = int(time.time() * 1000)
    raw_path = os.path.join(TEMP_IMG_DIR, f"raw_{user_id}_{slide_idx}_{timestamp}.jpg")
    final_path = os.path.join(TEMP_IMG_DIR, f"slide_photo_{user_id}_{slide_idx}_{timestamp}.png")

    query = translate_query_to_english(topic, slide_title)
    image_url = None

    # 1. Pexels API orqali qidirish
    if pexels_api_key:
        image_url = await fetch_pexels_image(query, used_ids, pexels_api_key)

    # 2. Wikimedia Commons orqali qidirish
    if not image_url:
        image_url = await fetch_wikimedia_image(query, used_ids)

    # Ramka rangi: dizayn aksenti yoki chegara rangi
    border_color = theme.accent_color if theme.is_dark else theme.card_border_color

    # 3. Agar online rasm topilsa, yuklab silliq yumaloq burchaklar bilan kesish
    if image_url:
        dl_res = await download_image(image_url, raw_path)
        if dl_res and os.path.exists(dl_res):
            process_and_round_image(
                input_path=dl_res,
                output_path=final_path,
                target_w=1140,
                target_h=1030,
                corner_radius=40,
                border_color=border_color,
                border_width=3
            )
            try:
                os.remove(dl_res)
            except Exception:
                pass
            return final_path

    # 4. Zaxira (Stock) bankidagi fotosuratlardan foydalanish
    fallback_photo = get_stock_fallback_image(topic, slide_idx, used_ids)
    if fallback_photo and os.path.exists(fallback_photo):
        process_and_round_image(
            input_path=fallback_photo,
            output_path=final_path,
            target_w=1140,
            target_h=1030,
            corner_radius=40,
            border_color=border_color,
            border_width=3
        )
        return final_path

    return final_path


# Eski funksiyalar bilan moslik (Backward compatibility)
def center_crop_and_resize(input_path: str, output_path: str, target_w: int = 1140, target_h: int = 1030) -> str:
    return process_and_round_image(input_path, output_path, target_w, target_h)

async def get_4_slide_images(*args, **kwargs) -> List[str]:
    topic = kwargs.get("topic", "Taqdimot")
    title = kwargs.get("slide_title", "Slayd")
    user_id = kwargs.get("user_id", 0)
    slide_idx = kwargs.get("slide_idx", 1)
    theme = kwargs.get("theme")
    img_path = await get_slide_illustration(topic, title, user_id, slide_idx, theme)
    return [img_path] * 4

def create_thematic_placeholder(*args, **kwargs) -> str:
    return os.path.join(STOCK_DIR, "tech_chart_hologram.png")
