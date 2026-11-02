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

# O'zbekcha va ruscha atamalarni inglizcha aniq mavzuli kalit so'zlarga moslashtirish (kengaytirilgan ilmiy baza)
UZ_TO_EN_MAP = {
    # Moliya va Iqtisodiyot
    "moliya": "finance financial market",
    "iqtisod": "economy economic market",
    "bank": "banking investment wealth",
    "biznes": "business corporate meeting",
    "buxgalteriya": "accounting financial audit",
    "marketing": "digital marketing advertising",
    "menejment": "management leadership team",
    "valyuta": "currency foreign exchange money",
    "daromad": "revenue profit income investment",
    "kapital": "capital money investment",
    "soliq": "taxation taxation finance revenue",
    "investitsiya": "investment stock trading growth",
    "savdo": "commerce trading business market",
    "sug'urta": "insurance protection financial security",
    "bozor": "market commerce trading",

    # O'zbekiston mavzulari
    "o'zbekiston": "Uzbekistan Tashkent architecture culture",
    "ozbekiston": "Uzbekistan Tashkent architecture culture",
    "samarqand": "Samarkand Registan Uzbekistan architecture",
    "buxoro": "Bukhara Uzbekistan historical monument",
    "xiva": "Khiva Ichan Kala Uzbekistan",
    "toshkent": "Tashkent city Uzbekistan modern",
    "amir temur": "Amir Timur history monument",
    "al-xorazmiy": "history mathematics science ancient",
    "alisher navoiy": "literature poetry library ancient manuscript",
    "orol": "Aral Sea ecology environmental water",

    # Axborot Texnologiyalari va Dasturlash
    "sun'iy intellekt": "artificial intelligence neural network",
    "suniy intellekt": "artificial intelligence neural network",
    "ai": "artificial intelligence technology robot",
    "kiberxavfsizlik": "cybersecurity network digital safety",
    "dasturlash": "computer programming code software",
    "axborot texnologiyalari": "information technology data network",
    "robototexnika": "robotics cyber automation machine",
    "algoritm": "computer algorithm code software",
    "ma'lumotlar bazasi": "database server cloud storage data",
    "bulutli": "cloud computing server network",
    "veb": "web development coding internet design",
    "kompyuter": "computer hardware technology laptop",

    # Tibbiyot va Salomatlik
    "tibbiyot": "medicine medical healthcare doctor hospital",
    "shifokor": "doctor physician medical hospital",
    "jarrohlik": "surgery medical operation hospital",
    "anesteziya": "anesthesia medical hospital surgery",
    "yurak": "heart cardiology cardiovascular medical",
    "qon": "blood cell hematology medical laboratory",
    "farmatsevtika": "pharmacy medicine pills pharmacology",
    "dorishunoslik": "pharmacy pills medicine laboratory",
    "anatomiya": "human anatomy biology medical science",
    "stomatologiya": "dentistry dentist dental clinic teeth",
    "pediatriya": "pediatrics child healthcare doctor",
    "salomatlik": "healthy lifestyle fitness healthcare",
    "virus": "virus microbiology medical research",
    "vaksina": "vaccine immunization injection medical",

    # Tabiat, Ekologiya va Qishloq xo'jaligi
    "ekologiya": "ecology green nature environmental protection",
    "tabiat": "nature green forest landscape mountain",
    "atrof-muhit": "environment planet ecology green",
    "energetika": "energy power plant electricity generator",
    "quyosh": "solar panels renewable green energy",
    "shamol": "wind turbine renewable energy",
    "qishloq xo'jaligi": "agriculture farming crops harvest tractor",
    "dehqonchilik": "farming agriculture field crops",
    "agronomiya": "agronomy agriculture plants field",
    "paxta": "cotton field agriculture harvest",
    "suv": "water irrigation river fresh water",
    "gidrologiya": "hydrology water river dam",
    "o'rmon": "forest trees nature green forestry",
    "iqlim": "climate change planet weather ecology",

    # Fan va Ta'lim
    "fizika": "physics quantum mechanics laboratory atom",
    "kimyo": "chemistry chemical laboratory flask science",
    "biologiya": "biology genetics DNA laboratory cell",
    "genetika": "genetics DNA molecular biology laboratory",
    "astronomiya": "astronomy space planets telescope cosmos",
    "kosmos": "space galaxy planet universe astronaut",
    "pedagogika": "education teaching classroom school teacher",
    "ta'lim": "education classroom university learning study",
    "talaba": "students university library books study",
    "maktab": "school classroom students education",
    "universitet": "university campus college graduation",
    "psixologiya": "psychology brain mental thinking mind",

    # Jamiyat, Madaniyat va Huquq
    "huquq": "law courtroom justice gavel courthouse",
    "sud": "court courtroom judge justice legal",
    "konstitutsiya": "constitution law legal document justice",
    "advokat": "lawyer legal legal consultation office",
    "xalqaro": "international diplomacy united nations globe",
    "tarix": "history museum ancient archaeological monument",
    "arxitektura": "architecture modern building design construction",
    "qurilish": "construction architecture building site engineer",
    "adabiyot": "literature books library poetry author",
    "san'at": "art painting museum gallery artist",
    "musiqa": "music instruments orchestra concert acoustic",
    "sport": "sports stadium athlete fitness championship",
    "turizm": "tourism travel vacation sightseeing hotel",
    "logistika": "logistics transportation shipping cargo truck",
    "avtomobil": "automobile car engine automotive engineering",
    "mashinasozlik": "mechanical engineering machinery factory"
}


async def get_thematic_queries(topic: str, slide_title: str) -> List[str]:
    """
    Mavzu va slayd sarlavhasi asosida 100% mavzuga mos aniq qidiruv so'zlarini shakllantiradi.
    Avval Google Translate orqali tabiiy tarjima qiladi, so'ngra asosiy kalit terminlarni oladi.
    """
    queries: List[str] = []

    # Shovqinli so'zlarni tozalash
    clean_topic = re.sub(r'^(mavzu|taqdimot|referat|reja)[:\s-]*', '', topic, flags=re.I).strip()
    clean_title = re.sub(r'^(slayd|\d+)[.:\s-]*', '', slide_title, flags=re.I).strip()

    # 1. Google Translate orqali tabiiy inglizcha tarjima
    async def translate_text(text: str) -> str:
        if not text:
            return ""
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q={text}"
            async with httpx.AsyncClient(timeout=3.5) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    return res.json()[0][0][0].strip()
        except Exception:
            pass
        return ""

    en_topic = await translate_text(clean_topic)
    en_title = await translate_text(clean_title)

    stop_words = {
        'the', 'of', 'and', 'in', 'on', 'at', 'to', 'for', 'a', 'an',
        'its', 'their', 'with', 'by', 'is', 'are', 'about', 'from', 'as'
    }

    def extract_keywords(en_str: str) -> str:
        words = [w for w in re.findall(r'[a-zA-Z]+', en_str) if w.lower() not in stop_words]
        return " ".join(words[:2])

    t_kw = extract_keywords(en_topic) if en_topic else ""
    s_kw = extract_keywords(en_title) if en_title else ""

    skip_words = {'introduction', 'conclusion', 'summary', 'overview', 'slide', 'content', 'plan'}
    if s_kw and s_kw.lower() not in skip_words:
        if t_kw:
            queries.append(f"{t_kw} {s_kw}".strip())
        queries.append(s_kw)

    if t_kw:
        queries.append(t_kw)

    # 2. Agar tarjima ishlamasa, ichki boyitilgan lug'atdan qidirish
    combined_uz = f"{clean_topic} {clean_title}".lower()
    for uz_key, en_val in UZ_TO_EN_MAP.items():
        if uz_key in combined_uz:
            if en_val not in queries:
                queries.append(en_val)

    if not queries:
        queries.append("science research technology education")

    return queries


def translate_query_to_english(topic: str, slide_title: str) -> str:
    """Moslik uchun sinxron qidiruv funksiyasi."""
    text = f"{topic} {slide_title}".lower()
    for uz_word, en_query in UZ_TO_EN_MAP.items():
        if uz_word in text:
            return en_query
    return "science technology research"


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
    headers = {"User-Agent": "SlidePresentationBot/2.0 (student.slide.generator@tift.uz; Python/3.11; httpx/0.25)"}
    short_query = " ".join(query.split()[:3])
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": short_query,
        "gsrnamespace": 6,
        "gsrlimit": 15,
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
    """Internetdan rasmni yuklab oladi (Wikimedia 403 xatosini oldini olish uchun akademik User-Agent bilan)."""
    headers = {
        "User-Agent": "SlidePresentationBot/2.0 (student.slide.generator@tift.uz; Python/3.11; httpx/0.25)"
    }
    try:
        async with httpx.AsyncClient(timeout=12.0, follow_redirects=True, headers=headers) as client:
            res = await client.get(url)
            if res.status_code == 200 and len(res.content) > 3000:
                with open(output_path, "wb") as f:
                    f.write(res.content)
                return output_path
            else:
                logger.warning(f"Rasmni yuklashda status: {res.status_code}")
    except Exception as e:
        logger.warning(f"Rasmni yuklashda xatolik ({url[:60]}...): {e}")
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

# Foydalanuvchi yuklagan 25 ta rasmlar katalogi va ularning mavzuviy belgilari (keywords)
USER_IMAGES_CATALOG = [
    {
        "filename": "uzbekistan_digital_globe.png",
        "keywords": [
            "o'zbekiston", "ozbekiston", "respublika", "davlat", "milliy", "vatan", "toshkent",
            "samarqand", "buxoro", "xiva", "islohot", "strategiya", "jamiyat", "qonun", "tarix"
        ],
        "weight": 10
    },
    {
        "filename": "hands_stacking_gold_coins.png",
        "keywords": [
            "daromad", "jamg'arma", "kapital", "oltin", "tanga", "boylik", "fond", "mablag'",
            "investitsiya", "pul", "jamg'arish", "iqtisodiy o'sish", "moliyalashtirish", "moliya"
        ],
        "weight": 9
    },
    {
        "filename": "coins_candlestick.png",
        "keywords": [
            "moliya", "narx", "kotirovka", "birja", "aksiya", "bozor", "moliyaviy", "bank",
            "valyuta", "kurs", "kriptovalyuta", "fond bozori", "savdo", "iqtisod"
        ],
        "weight": 9
    },
    {
        "filename": "iqtisodiyot_candlestick_coins.png",
        "keywords": [
            "iqtisod", "iqtisodiyot", "makroiqtisodiyot", "mikroiqtisodiyot", "tizim",
            "iqtisodiy nazariya", "soliq", "byudjet", "iqtisodiy mexanizm", "moliya"
        ],
        "weight": 10
    },
    {
        "filename": "global_dollar_currency.png",
        "keywords": [
            "valyuta", "dollar", "xalqaro", "jahon", "global", "eksport", "import",
            "tashqi savdo", "valyuta kursi", "xalqaro moliya", "dunyo", "pul"
        ],
        "weight": 9
    },
    {
        "filename": "global_pie_finance.png",
        "keywords": [
            "ulush", "sektor", "taqsimot", "foiz", "diagramma", "statistika", "hisobot",
            "buxgalteriya", "audit", "tahliliy", "ko'rsatkich", "moliya"
        ],
        "weight": 8
    },
    {
        "filename": "finance_calculator.png",
        "keywords": [
            "hisob", "kalkulyator", "buxgalter", "audit", "soliq", "xarajat", "foyda",
            "balans", "hisob-kitob", "moliyaviy hisobot", "reja", "jadval"
        ],
        "weight": 8
    },
    {
        "filename": "laptop_charts_growth_arrow.png",
        "keywords": [
            "grafik", "diagramma", "o'sish", "dinamika", "noutbuk", "kompyuter", "tahlil",
            "monitoring", "statistika", "natija", "samaradorlik", "ko'rsatkichlar"
        ],
        "weight": 9
    },
    {
        "filename": "isometric_market_analytics.png",
        "keywords": [
            "tahlilchi", "ekspert", "monitoring", "marketing", "bozor tahlili", "lupa",
            "izlanish", "tadqiqot", "prognoz", "strategiya", "tashxis"
        ],
        "weight": 8
    },
    {
        "filename": "tablet_analytics.png",
        "keywords": [
            "planshet", "mobil", "tahlil", "raqamli", "boshqaruv", "menejment", "nazorat",
            "monitoring", "hisobot", "boshqarish", "ko'rsatkich"
        ],
        "weight": 8
    },
    {
        "filename": "tech_chart_hologram.png",
        "keywords": [
            "gologramma", "zamonaviy", "futuristik", "yuqori texnologiya", "tahlil",
            "raqamlashtirish", "kelajak", "monitoring", "avtomatlashtirish"
        ],
        "weight": 8
    },
    {
        "filename": "businessman_future_city_data.png",
        "keywords": [
            "kelajak", "shahar", "smart", "aqlli", "infratuzilma", "istiqbol", "taraqqiyot",
            "global", "innovatsiya", "raqamli iqtisodiyot", "texnologik"
        ],
        "weight": 9
    },
    {
        "filename": "hex_touch_analytics.png",
        "keywords": [
            "sensor", "interaktiv", "interfeys", "texnologiya", "ekran", "axborot",
            "tizim", "integratsiya", "raqamli tizim", "zamonaviy texnologiya"
        ],
        "weight": 8
    },
    {
        "filename": "laptop_globe_network.png",
        "keywords": [
            "internet", "tarmoq", "noutbuk", "global tarmoq", "axborot", "veb", "aloqa",
            "onlayn", "platforma", "dasturiy", "xalqaro aloqa"
        ],
        "weight": 8
    },
    {
        "filename": "tablet_cloud_icons.png",
        "keywords": [
            "bulut", "xizmatlar", "ilovalar", "mobil ilova", "dastur", "xizmat ko'rsatish",
            "ekotizim", "raqamli xizmatlar", "kommunikatsiya", "funksiya"
        ],
        "weight": 8
    },
    {
        "filename": "global_network.png",
        "keywords": [
            "global", "yer shari", "xalqaro", "dunyo", "hamkorlik", "integratsiya",
            "tizim", "tarmoq", "infratuzilma", "xalqaro munosabatlar"
        ],
        "weight": 8
    },
    {
        "filename": "robot_hand_coins.png",
        "keywords": [
            "robot", "sun'iy intellekt", "ai", "avtomatlashtirish", "kiber", "texnologik",
            "aqlli tizim", "neyron", "mashinali o'rganish", "algoritm"
        ],
        "weight": 9
    },
    {
        "filename": "brain_circuit_tech.png",
        "keywords": [
            "neyro", "sun'iy intellekt", "mikrosxema", "chipli", "texnologiya", "aqlli",
            "kognitiv", "kompyuter", "dasturlash", "kiberxavfsizlik"
        ],
        "weight": 9
    },
    {
        "filename": "neon_brain_idea.png",
        "keywords": [
            "g'oya", "fikr", "kreativ", "ijod", "innovatsiya", "startap", "miya",
            "yangi g'oyalar", "loyihalar", "kontseptsiya"
        ],
        "weight": 8
    },
    {
        "filename": "brain_gears_logic.png",
        "keywords": [
            "mantiq", "fikrlash", "tahliliy fikr", "psixologiya", "ta'lim", "pedagogika",
            "intellekt", "mexanizm", "ong", "aql", "tushuncha"
        ],
        "weight": 8
    },
    {
        "filename": "brain_logic_gear.png",
        "keywords": [
            "mantiqiy", "strukturaviy", "tizimli", "tamoyil", "qonuniyat", "nazariya",
            "uslub", "metodologiya", "asos", "falsafa"
        ],
        "weight": 8
    },
    {
        "filename": "head_profile_gears.png",
        "keywords": [
            "inson", "shaxs", "mutaxassis", "kadrlar", "inson kapitali", "xodim",
            "rahbar", "menejer", "aql", "kompetensiya", "bilim"
        ],
        "weight": 8
    },
    {
        "filename": "3d_red_arrow_growth.png",
        "keywords": [
            "o'sish", "yuqoriga", "sur'at", "jadallashuv", "yutuq", "maqsad",
            "natijadorlik", "muvaffaqiyat", "ko'rsatkich", "rivojlanish"
        ],
        "weight": 9
    },
    {
        "filename": "businessman_drawing_chart.png",
        "keywords": [
            "rejalashtirish", "biznes reja", "strategiya", "loyiha", "boshqarish",
            "chizma", "yo'l xaritasi", "istiqbol", "tadbirkor"
        ],
        "weight": 8
    },
    {
        "filename": "growth_stairs_idea.png",
        "keywords": [
            "bosqich", "pog'ona", "taraqqiyot", "rivoj", "chora-tadbirlar",
            "tavsiyalar", "xulosa", "istiqbol", "yo'nalish"
        ],
        "weight": 8
    }
]


def match_user_stock_image(topic: str, slide_title: str, used_paths: Set[str]) -> Optional[str]:
    """
    Faqat foydalanuvchi yuborgan 25 ta rasmlar ichidan mavzuga va slaydga
    eng mos keladigan rasmni semantik qidiruv asosida tanlaydi (takrorlanmaslik kafolatlangan).
    """
    combined = f"{topic} {slide_title}".lower()
    title_lower = slide_title.lower()

    best_candidate = None
    best_score = -1

    for item in USER_IMAGES_CATALOG:
        path = os.path.join(STOCK_DIR, item["filename"])
        if path in used_paths:
            continue
        if not os.path.exists(path):
            continue

        score = item["weight"]
        matches = 0
        for kw in item["keywords"]:
            if kw in title_lower:
                score += 15
                matches += 1
            elif kw in combined:
                score += 5
                matches += 1

        if matches > 0:
            score += matches * 4

        if score > best_score:
            best_score = score
            best_candidate = path

    # Agar maxsus kalit so'z topilmasa, zaxiradagi boshqa ishlatilmagan rasmni tanlaymiz
    if not best_candidate:
        for item in USER_IMAGES_CATALOG:
            path = os.path.join(STOCK_DIR, item["filename"])
            if path not in used_paths and os.path.exists(path):
                best_candidate = path
                break

    if best_candidate:
        used_paths.add(best_candidate)
        return best_candidate

    return None


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
    Faqat foydalanuvchi yuklagan 25 ta rasmdan foydalanadi (Internetdan olinmaydi).
    Mavzuga 100% moslab tanlaydi, 1140x1030 o'lchamga moslab silliq burchaklar va ramka bilan beradi.
    """
    if used_ids is None:
        used_ids = set()

    timestamp = int(time.time() * 1000)
    final_path = os.path.join(TEMP_IMG_DIR, f"slide_photo_{user_id}_{slide_idx}_{timestamp}.png")
    border_color = theme.accent_color if theme.is_dark else theme.card_border_color

    # 1. Faqat foydalanuvchi yuborgan 25 ta rasmdan mavzuga mosini tanlash
    selected_photo = match_user_stock_image(topic, slide_title, used_ids)
    if selected_photo and os.path.exists(selected_photo):
        process_and_round_image(
            input_path=selected_photo,
            output_path=final_path,
            target_w=1140,
            target_h=1030,
            corner_radius=40,
            border_color=border_color,
            border_width=3
        )
        return final_path

    # 2. Favqulodda holatda (fayl topilmasa) nafis karta chizish
    create_thematic_placeholder_card(
        output_path=final_path,
        topic=topic,
        slide_title=slide_title,
        slide_idx=slide_idx,
        theme=theme
    )
    return final_path


def create_thematic_placeholder_card(
    output_path: str,
    topic: str,
    slide_title: str,
    slide_idx: int,
    theme: Theme,
    target_w: int = 1140,
    target_h: int = 1030
) -> str:
    """
    Internet uzilgan va stock papkasi bo'lmaganda ham har bir slayd uchun
    100% kafolatlangan professional infografika tasvirini chizib beradi.
    """
    import math
    try:
        scale = 2
        W, H = target_w * scale, target_h * scale

        bg_col = (20, 24, 38, 255) if theme.is_dark else (248, 250, 253, 255)
        img = Image.new("RGBA", (W, H), bg_col)
        draw = ImageDraw.Draw(img)

        accent = theme.accent_color
        variant = slide_idx % 3

        if variant == 0:
            # 1. Bar Chart Infografika
            base_y = H - 350
            heights = [450, 750, 620, 950, 1150, 1400]
            for i, ht in enumerate(heights):
                x1 = 260 + i * 280
                y1 = base_y - ht
                x2 = x1 + 140
                col_alpha = 110 + i * 24
                draw.rounded_rectangle([x1, y1, x2, base_y], radius=24, fill=(*accent, col_alpha))
            # O'sish chizig'i
            pts = [(260, base_y - 450), (540, base_y - 750), (820, base_y - 620), (1100, base_y - 950), (1380, base_y - 1150), (1660, base_y - 1400)]
            for i in range(len(pts) - 1):
                draw.line([pts[i], pts[i+1]], fill=(*accent, 255), width=16)
            for p in pts:
                draw.ellipse([p[0]-24, p[1]-24, p[0]+24, p[1]+24], fill=(255, 255, 255, 255), outline=(*accent, 255), width=10)

        elif variant == 1:
            # 2. Global Network Nodes
            center_x, center_y = W // 2, H // 2
            for r in (260, 520, 780):
                draw.ellipse([center_x - r, center_y - r, center_x + r, center_y + r], outline=(*accent, 60), width=6)
            draw.ellipse([center_x - 120, center_y - 120, center_x + 120, center_y + 120], fill=(*accent, 220), outline=(255, 255, 255, 255), width=12)
            angles = [30, 85, 145, 215, 275, 335]
            for ang in angles:
                rad = math.radians(ang)
                dist = 460 if ang % 2 == 0 else 660
                nx = int(center_x + dist * math.cos(rad))
                ny = int(center_y + dist * math.sin(rad))
                draw.line([(center_x, center_y), (nx, ny)], fill=(*accent, 140), width=8)
                nr = 60 if ang % 2 == 0 else 45
                draw.ellipse([nx - nr, ny - nr, nx + nr, ny + nr], fill=(*accent, 200), outline=(255, 255, 255, 255), width=8)

        else:
            # 3. Analytics Metric Dashboard
            center_x, center_y = W // 2, H // 2
            draw.arc([center_x - 500, center_y - 500, center_x + 500, center_y + 500], start=135, end=405, fill=(*accent, 70), width=40)
            draw.arc([center_x - 500, center_y - 500, center_x + 500, center_y + 500], start=135, end=330, fill=(*accent, 240), width=40)
            draw.ellipse([center_x - 220, center_y - 220, center_x + 220, center_y + 220], fill=(*accent, 180), outline=(255, 255, 255, 255), width=14)
            draw.ellipse([center_x - 90, center_y - 90, center_x + 90, center_y + 90], fill=(255, 255, 255, 255))

        # Yumaloq maska
        mask = Image.new("L", (W, H), 0)
        draw_mask = ImageDraw.Draw(mask)
        draw_mask.rounded_rectangle([0, 0, W, H], radius=40 * scale, fill=255)
        img.putalpha(mask)

        # Chegara ramkasi
        border_canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw_border = ImageDraw.Draw(border_canvas)
        bw_scaled = 3 * scale
        draw_border.rounded_rectangle(
            [bw_scaled // 2, bw_scaled // 2, W - bw_scaled // 2, H - bw_scaled // 2],
            radius=40 * scale,
            outline=(*accent, 255),
            width=bw_scaled
        )
        final_img = Image.alpha_composite(img, border_canvas)
        res = final_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
        res.save(output_path, "PNG")
        return output_path
    except Exception as e:
        logger.error(f"Infografika generatsiyasida xatolik: {e}")
        return output_path


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
