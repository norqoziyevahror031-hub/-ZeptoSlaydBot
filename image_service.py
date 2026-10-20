import os
import re
import asyncio
import logging
from typing import List, Set, Optional, Tuple
from PIL import Image, ImageDraw, ImageFont
import httpx

from themes import Theme

logger = logging.getLogger(__name__)

TEMP_IMG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "temp", "images")
os.makedirs(TEMP_IMG_DIR, exist_ok=True)

# O'zbekcha atamalarni inglizcha qidiruv so'zlariga moslashtirish lug'ati
UZ_TO_EN_MAP = {
    # Mavzular
    "sun'iy intellekt": "artificial intelligence technology",
    "suniy intellekt": "artificial intelligence technology",
    "ai": "artificial intelligence computer",
    "kiberxavfsizlik": "cybersecurity digital security",
    "axborot texnologiyalari": "information technology software",
    "dasturlash": "computer programming code developer",
    "iqtisodiyot": "economy finance business stock market",
    "iqtisodiy": "economy business finance investment",
    "moliya": "finance banking investment money",
    "menejment": "business management corporate team",
    "marketing": "digital marketing advertising growth",
    "buxgalteriya": "accounting finance audit report",
    "pedagogika": "education teaching school classroom",
    "psixologiya": "psychology brain mental health science",
    "tibbiyot": "medicine medical healthcare doctor",
    "huquqshunoslik": "law justice court lawyer gavel",
    "huquq": "law courtroom justice legal",
    "ekologiya": "ecology environment green nature earth",
    "fizika": "physics quantum science laboratory",
    "kimyo": "chemistry science molecules laboratory",
    "biologiya": "biology cell dna nature research",
    "tarix": "ancient history museum architecture historical",
    "falsafa": "philosophy thinker books library wisdom",
    "adabiyot": "literature books library reading poetry",
    "arxitektura": "modern architecture building construction",
    "energetika": "green energy solar power electric power",
    "avtomobil": "modern automotive car technology engineering",
    "robototexnika": "robotics automation cyber technology",
    "tilshunoslik": "linguistics language communication library",
    "xalqaro munosabatlar": "international diplomacy flags conference",
    "turizm": "tourism travel landscape vacation resort",
    "sport": "sports athlete fitness competition",
    "geografiya": "geography globe planet earth mountains",
    "matematika": "mathematics equations science data",
    "statistika": "data analytics graph statistics business",

    # Slayd turlari
    "kirish": "introduction overview concept",
    "asosiy tushunchalar": "fundamental concept theoretical basis",
    "tushuncha": "concept definition architecture",
    "tarixi": "history timeline evolution origin",
    "rivojlanish bosqichlari": "development evolution roadmap",
    "turlari": "categories types classification",
    "tasnifi": "classification types categories",
    "qo'llanilishi": "practical application industry use",
    "amaliyot": "practical execution hands-on workplace",
    "afzallik": "advantages benefits positive growth",
    "afzallik va kamchiliklar": "pros and cons comparison analysis",
    "kamchilik": "challenges limitations problem analysis",
    "muammolar": "challenges issues barriers research",
    "yechimlar": "solutions innovation strategy breakthrough",
    "innovatsiyalar": "innovation modern breakthrough invention",
    "natijalar": "results data graph success achievement",
    "istiqbol": "future vision tomorrow trend technology",
    "kelajak": "future futuristic technology trends",
    "xulosa": "conclusion summary final decision",
    "adabiyotlar": "books library research academic bibliography",
    "foydalanilgan adabiyotlar": "books academic publications study"
}

def translate_query_to_english(topic: str, slide_title: str) -> str:
    """
    Slayd sarlavhasi va umumiy mavzu asosida inglizcha qidiruv so'zini hosil qiladi.
    """
    cleaned_topic = topic.lower().strip()
    cleaned_title = slide_title.lower().strip()

    en_topic_parts = []
    en_title_parts = []

    # Mavzuni qidirish
    for uz_word, en_trans in UZ_TO_EN_MAP.items():
        if uz_word in cleaned_topic:
            en_topic_parts.append(en_trans)
            break

    # Sarlavhani qidirish
    for uz_word, en_trans in UZ_TO_EN_MAP.items():
        if uz_word in cleaned_title:
            en_title_parts.append(en_trans)
            break

    # Agar topilmasa, mavzudan tozalangan kalit so'zlarni olamiz
    if not en_topic_parts:
        topic_words = re.findall(r'[a-zA-Z0-9]+', cleaned_topic)
        en_topic_parts.append(" ".join(topic_words[:3]) or "technology science research")

    if not en_title_parts:
        title_words = re.findall(r'[a-zA-Z0-9]+', cleaned_title)
        en_title_parts.append(" ".join(title_words[:2]) or "concept overview")

    query = f"{en_topic_parts[0]} {en_title_parts[0]}".strip()
    # Ortiqcha so'zlarni olib tashlash va 4-5 ta eng muhim so'zni qoldirish
    words = query.split()
    seen = set()
    dedup = [w for w in words if not (w in seen or seen.add(w))]
    return " ".join(dedup[:4])


async def fetch_pexels_images(query: str, count: int, used_ids: Set[str], api_key: str) -> List[str]:
    """
    Pexels API orqali mavzuga doir rasmlar URL ro'yxatini oladi.
    """
    if not api_key:
        return []

    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": api_key}
    params = {
        "query": query,
        "per_page": max(15, count * 3),
        "orientation": "landscape"
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(url, headers=headers, params=params)
            if res.status_code == 200:
                data = res.json()
                photos = data.get("photos", [])
                results = []
                for p in photos:
                    p_id = str(p.get("id"))
                    if p_id not in used_ids:
                        used_ids.add(p_id)
                        # Medium yoki large rasm URL
                        src = p.get("src", {})
                        img_url = src.get("large") or src.get("medium") or src.get("original")
                        if img_url:
                            results.append(img_url)
                    if len(results) >= count:
                        break
                return results
            else:
                logger.warning(f"Pexels API javobi: {res.status_code} - {res.text[:100]}")
    except Exception as e:
        logger.error(f"Pexels API so'rovida xatolik: {e}")

    return []


async def fetch_wikimedia_images(query: str, count: int, used_ids: Set[str]) -> List[str]:
    """
    Wikimedia Commons bepul API (API kalitsiz ishlaydi).
    """
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"{query} filetype:bitmap",
        "gsrlimit": max(15, count * 3),
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": 800,
        "format": "json"
    }
    headers = {"User-Agent": "TelegramPresentationBot/2.0 (contact: support@tift.uz)"}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(url, params=params, headers=headers)
            if res.status_code == 200:
                data = res.json()
                pages = data.get("query", {}).get("pages", {})
                results = []
                for page_id, page_info in pages.items():
                    if str(page_id) in used_ids:
                        continue
                    infos = page_info.get("imageinfo", [])
                    if infos:
                        thumb_url = infos[0].get("thumburl") or infos[0].get("url")
                        if thumb_url and thumb_url.lower().endswith(('.jpg', '.jpeg', '.png')):
                            used_ids.add(str(page_id))
                            results.append(thumb_url)
                    if len(results) >= count:
                        break
                return results
    except Exception as e:
        logger.error(f"Wikimedia API so'rovida xatolik: {e}")

    return []


async def download_single_image(url: str, output_path: str) -> Optional[str]:
    """Bitta rasmni yuklab oladi."""
    try:
        async with httpx.AsyncClient(timeout=12.0) as client:
            res = await client.get(url, follow_redirects=True)
            if res.status_code == 200 and len(res.content) > 1000:
                with open(output_path, "wb") as f:
                    f.write(res.content)
                return output_path
    except Exception as e:
        logger.warning(f"Rasm yuklashda xatolik ({url[:50]}): {e}")
    return None


def center_crop_and_resize(input_path: str, output_path: str, target_w: int = 600, target_h: int = 450) -> str:
    """
    Rasmni proporsiyasini saqlagan holda markazdan kesadi (center-crop)
    va belgilangan target_w x target_h o'lchamga keltiradi.
    """
    try:
        with Image.open(input_path) as img:
            img = img.convert("RGB")
            src_w, src_h = img.size

            target_ratio = target_w / target_h
            src_ratio = src_w / src_h

            if src_ratio > target_ratio:
                # Manba kengroq -> yon tomonlardan kesamiz
                new_w = int(src_h * target_ratio)
                left = (src_w - new_w) // 2
                box = (left, 0, left + new_w, src_h)
            else:
                # Manba balandroq -> yuqori va pastdan kesamiz
                new_h = int(src_w / target_ratio)
                top = (src_h - new_h) // 2
                box = (0, top, src_w, top + new_h)

            cropped = img.crop(box)
            resized = cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)
            resized.save(output_path, "JPEG", quality=90)
            return output_path
    except Exception as e:
        logger.error(f"Rasmni kesishda xatolik: {e}")
        return input_path


def create_thematic_placeholder(
    theme: Theme,
    topic: str,
    slide_title: str,
    index: int,
    output_path: str,
    width: int = 600,
    height: int = 450
) -> str:
    """
    Agar rasm topilmasa yoki yuklanmasa, dizayn ranglarida
    chiroyli ilmiy-grafik placeholder kartasini yaratadi.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img = Image.new("RGB", (width, height), theme.card_bg_color)
    draw = ImageDraw.Draw(img)

    # 1. Nozik gradient fon
    r1, g1, b1 = theme.card_bg_color
    r2, g2, b2 = theme.bg_color_end
    for y in range(height):
        factor = y / height
        r = int(r1 + (r2 - r1) * factor * 0.4)
        g = int(g1 + (g2 - g1) * factor * 0.4)
        b = int(b1 + (b2 - b1) * factor * 0.4)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # 2. Ichki dekorativ ramka
    draw.rounded_rectangle(
        [10, 10, width - 10, height - 10],
        radius=12,
        outline=theme.accent_color,
        width=2
    )

    # 3. Markaziy geometrik shakl / ikona o'rni
    center_x, center_y = width // 2, height // 2 - 20
    icon_box = [center_x - 45, center_y - 45, center_x + 45, center_y + 45]
    draw.rounded_rectangle(icon_box, radius=12, fill=theme.accent_color)

    # Shriftlar
    try:
        font_num = ImageFont.truetype("timesbd.ttf", 36)
        font_txt = ImageFont.truetype("times.ttf", 18)
        font_sub = ImageFont.truetype("times.ttf", 14)
    except IOError:
        font_num = ImageFont.load_default()
        font_txt = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    # Raqam
    draw.text((center_x - 12, center_y - 22), str(index + 1), fill=(255, 255, 255), font=font_num)

    # Matn
    badge_label = f"Mavzu: {topic[:28]}"
    draw.text((width // 2, height - 75), badge_label, fill=theme.title_color, font=font_txt, anchor="mm")
    
    sub_label = f"{slide_title[:32]} • Ilmiy Ko'rgazma"
    draw.text((width // 2, height - 45), sub_label, fill=theme.text_color, font=font_sub, anchor="mm")

    img.save(output_path, "JPEG", quality=90)
    return output_path


async def get_4_slide_images(
    topic: str,
    slide_title: str,
    user_id: int,
    slide_idx: int,
    theme: Theme,
    used_ids: Set[str],
    pexels_api_key: Optional[str] = None
) -> List[str]:
    """
    Slayd uchun mavzuga mos 4 ta rasm oladi (parallel yuklash, kesish va tayyorlash).
    Agar rasm yetarli bo'lmasa, o'rniga chiroyli tematik placeholder qo'yadi.
    Doimo roppa-rosa 4 ta rasm fayl yo'lini qaytaradi.
    """
    query = translate_query_to_english(topic, slide_title)
    needed = 4
    image_urls = []

    # 1. Pexels API orqali olishga urinish
    if pexels_api_key:
        image_urls = await fetch_pexels_images(query, count=needed, used_ids=used_ids, api_key=pexels_api_key)

    # 2. Agar Pexels bermasa yoki kalit bo'lmasa, Wikimedia Commons'dan olish
    if len(image_urls) < needed:
        wiki_needed = needed - len(image_urls)
        wiki_urls = await fetch_wikimedia_images(query, count=wiki_needed, used_ids=used_ids)
        image_urls.extend(wiki_urls)

    # 3. Rasmlarni parallel yuklab olish
    final_paths = []
    download_tasks = []
    target_files = []

    for i, url in enumerate(image_urls[:needed]):
        raw_out = os.path.join(TEMP_IMG_DIR, f"raw_{user_id}_{slide_idx}_{i}.jpg")
        target_files.append(raw_out)
        download_tasks.append(download_single_image(url, raw_out))

    if download_tasks:
        downloaded = await asyncio.gather(*download_tasks, return_exceptions=True)
    else:
        downloaded = []

    # 4. Yuklangan rasmlarni markazdan kesish va tayyorlash
    for i, res_path in enumerate(downloaded):
        if isinstance(res_path, str) and res_path and os.path.exists(res_path):
            cropped_out = os.path.join(TEMP_IMG_DIR, f"crop_{user_id}_{slide_idx}_{i}.jpg")
            center_crop_and_resize(res_path, cropped_out, target_w=600, target_h=450)
            final_paths.append(cropped_out)
            # Raw faylni tozalash
            try:
                os.remove(res_path)
            except Exception:
                pass

    # 5. Agar 4 tadan kam bo'lsa, qolganlarini chiroyli placeholder bilan to'ldirish
    while len(final_paths) < 4:
        idx_placeholder = len(final_paths)
        ph_path = os.path.join(TEMP_IMG_DIR, f"placeholder_{user_id}_{slide_idx}_{idx_placeholder}.jpg")
        create_thematic_placeholder(
            theme=theme,
            topic=topic,
            slide_title=slide_title,
            index=idx_placeholder,
            output_path=ph_path,
            width=600,
            height=450
        )
        final_paths.append(ph_path)

    return final_paths[:4]
