import os
from dataclasses import dataclass
from typing import Tuple, Dict, List
from PIL import Image, ImageDraw, ImageFont

@dataclass
class Theme:
    id: str
    name: str
    short_name: str
    description: str
    bg_color: Tuple[int, int, int]
    bg_color_end: Tuple[int, int, int]
    title_color: Tuple[int, int, int]
    text_color: Tuple[int, int, int]
    accent_color: Tuple[int, int, int]
    card_bg_color: Tuple[int, int, int]
    card_border_color: Tuple[int, int, int]
    font_heading: str
    font_body: str
    is_dark: bool = False

THEMES: Dict[str, Theme] = {
    "classic": Theme(
        id="classic",
        name="🏛 Klassik",
        short_name="Klassik",
        description="Oq fon, ko'k sarlavhalar va toza akademik uslub",
        bg_color=(255, 255, 255),
        bg_color_end=(240, 244, 250),
        title_color=(20, 50, 110),        # Deep Classic Navy
        text_color=(45, 55, 72),          # Dark Slate
        accent_color=(37, 99, 235),       # Royal Blue
        card_bg_color=(245, 248, 255),
        card_border_color=(205, 220, 245),
        font_heading="Times New Roman",
        font_body="Times New Roman",
        is_dark=False
    ),
    "modern": Theme(
        id="modern",
        name="💎 Zamonaviy",
        short_name="Zamonaviy",
        description="To'q ko'k gradient fon, oq va moviy yorug' matn",
        bg_color=(12, 25, 50),            # Deep Navy
        bg_color_end=(25, 45, 85),        # Gradient Slate Navy
        title_color=(255, 255, 255),      # Pure White
        text_color=(210, 225, 245),       # Light Ice Blue
        accent_color=(56, 189, 248),      # Cyan Sky
        card_bg_color=(20, 38, 70),
        card_border_color=(45, 75, 125),
        font_heading="Times New Roman",
        font_body="Times New Roman",
        is_dark=True
    ),
    "minimal": Theme(
        id="minimal",
        name="⚪ Minimal",
        short_name="Minimal",
        description="Och kulrang fon, qora matn va nozik chiziqlar",
        bg_color=(245, 247, 250),         # Ultra-light Neutral
        bg_color_end=(235, 239, 244),
        title_color=(24, 24, 27),         # Pitch Black/Zinc
        text_color=(75, 85, 99),          # Cool Gray
        accent_color=(15, 23, 42),        # Dark Charcoal
        card_bg_color=(255, 255, 255),
        card_border_color=(226, 232, 240),
        font_heading="Times New Roman",
        font_body="Times New Roman",
        is_dark=False
    ),
    "nature": Theme(
        id="nature",
        name="🌿 Yashil tabiat",
        short_name="Yashil tabiat",
        description="Yumshoq yashil va zumrad ranglar uyg'unligi",
        bg_color=(242, 249, 245),         # Soft Mint
        bg_color_end=(226, 242, 233),
        title_color=(16, 85, 50),         # Emerald Deep
        text_color=(40, 60, 50),          # Forest Slate
        accent_color=(16, 185, 129),      # Vibrant Emerald
        card_bg_color=(255, 255, 255),
        card_border_color=(185, 225, 205),
        font_heading="Times New Roman",
        font_body="Times New Roman",
        is_dark=False
    ),
    "royal": Theme(
        id="royal",
        name="👑 Qizil-oltin",
        short_name="Qizil-oltin",
        description="Rasmiy, tantanali uslub, to'q qizil va oltin aksentlar",
        bg_color=(253, 250, 245),         # Warm Ivory
        bg_color_end=(248, 240, 230),
        title_color=(140, 20, 30),        # Royal Crimson
        text_color=(50, 40, 40),          # Warm Charcoal
        accent_color=(217, 145, 25),      # Gold
        card_bg_color=(255, 255, 255),
        card_border_color=(235, 205, 160),
        font_heading="Times New Roman",
        font_body="Times New Roman",
        is_dark=False
    ),
    "dark": Theme(
        id="dark",
        name="🌙 Qorong'i rejim",
        short_name="Qorong'i rejim",
        description="Qora fon, neon-ko'k va binafsha aksentlar",
        bg_color=(13, 17, 23),            # Pitch Dark GitHub
        bg_color_end=(22, 27, 34),
        title_color=(240, 246, 252),      # Bright Light
        text_color=(175, 185, 200),       # Muted Gray
        accent_color=(88, 166, 255),      # Electric Neon Blue
        card_bg_color=(22, 27, 34),
        card_border_color=(48, 54, 61),
        font_heading="Times New Roman",
        font_body="Times New Roman",
        is_dark=True
    )
}

def get_theme(theme_id: str) -> Theme:
    return THEMES.get(theme_id, THEMES["classic"])

def get_all_themes() -> List[Theme]:
    return list(THEMES.values())

def generate_preview_image(theme: Theme, output_path: str, width: int = 800, height: int = 450) -> str:
    """
    Pillow yordamida 16:9 formatdagi slayd preview rasmini yaratadi.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img = Image.new("RGB", (width, height), theme.bg_color)
    draw = ImageDraw.Draw(img)

    # 1. Gradient fon chizish
    r1, g1, b1 = theme.bg_color
    r2, g2, b2 = theme.bg_color_end
    for y in range(height):
        factor = y / height
        r = int(r1 + (r2 - r1) * factor)
        g = int(g1 + (g2 - g1) * factor)
        b = int(b1 + (b2 - b1) * factor)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # 2. Yuqori dekorativ aksent chiziq
    draw.rectangle([0, 0, width, 10], fill=theme.accent_color)

    # 3. Markaziy karta ramkasi (Slide mockup)
    pad_x, pad_y = 50, 45
    card_rect = [pad_x, pad_y, width - pad_x, height - pad_y]
    draw.rounded_rectangle(
        card_rect,
        radius=16,
        fill=theme.card_bg_color,
        outline=theme.accent_color if theme.is_dark else theme.card_border_color,
        width=2
    )

    # Shriftlar (Times New Roman, fallback bilan)
    try:
        font_title = ImageFont.truetype("timesbd.ttf", 34)
        font_subtitle = ImageFont.truetype("times.ttf", 20)
        font_body = ImageFont.truetype("times.ttf", 17)
        font_badge = ImageFont.truetype("timesbd.ttf", 15)
        font_footer = ImageFont.truetype("times.ttf", 13)
    except IOError:
        try:
            font_title = ImageFont.truetype("arialbd.ttf", 34)
            font_subtitle = ImageFont.truetype("arial.ttf", 20)
            font_body = ImageFont.truetype("arial.ttf", 17)
            font_badge = ImageFont.truetype("arialbd.ttf", 15)
            font_footer = ImageFont.truetype("arial.ttf", 13)
        except IOError:
            font_title = ImageFont.load_default()
            font_subtitle = ImageFont.load_default()
            font_body = ImageFont.load_default()
            font_badge = ImageFont.load_default()
            font_footer = ImageFont.load_default()

    # 4. Shablon badge (teg)
    badge_text = f"  {theme.name}  "
    draw.rounded_rectangle(
        [pad_x + 30, pad_y + 25, pad_x + 220, pad_y + 55],
        radius=8,
        fill=theme.accent_color
    )
    badge_text_color = (10, 15, 25) if not theme.is_dark and theme.id != "classic" and theme.id != "royal" else (255, 255, 255)
    draw.text((pad_x + 40, pad_y + 30), badge_text, fill=badge_text_color, font=font_badge)

    # 5. Sarlavha namunasi
    draw.text((pad_x + 30, pad_y + 75), "Taqdimot Sarlavhasi Namunasi", fill=theme.title_color, font=font_title)
    draw.line([(pad_x + 30, pad_y + 120), (pad_x + 350, pad_y + 120)], fill=theme.accent_color, width=3)

    # 6. Qisqa tavsif va punktlar
    draw.text((pad_x + 30, pad_y + 135), theme.description, fill=theme.text_color, font=font_subtitle)

    bullets = [
        "• Asosiy ilmiy va akademik ma'lumotlar",
        "• Chiroyli va tushunarli tartiblangan fikrlar",
        "• Rasmiy va professional ko'rinishdagi slaydlar"
    ]
    cur_y = pad_y + 180
    for b in bullets:
        draw.text((pad_x + 35, cur_y), b, fill=theme.text_color, font=font_body)
        cur_y += 32

    # 7. Pastki footer namunasi
    footer_text = "Universitet nomi • Talaba Ism Familiyasi • 101-guruh • 1/10"
    draw.line([(pad_x + 30, height - pad_y - 45), (width - pad_x - 30, height - pad_y - 45)], fill=theme.card_border_color, width=1)
    draw.text((pad_x + 30, height - pad_y - 35), footer_text, fill=theme.text_color, font=font_footer)

    img.save(output_path, "PNG", quality=95)
    return output_path

def generate_catalog_image(output_path: str) -> str:
    """
    Barcha 6 ta temani 2 ustun x 3 qatorda bitta chiroyli rasmda birlashtirib ko'rsatadi.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    themes_list = list(THEMES.values())
    
    thumb_w, thumb_h = 440, 248
    margin_x, margin_y = 20, 20
    header_h = 70
    
    total_w = margin_x * 3 + thumb_w * 2
    total_h = header_h + margin_y * 4 + thumb_h * 3
    
    catalog = Image.new("RGB", (total_w, total_h), (240, 243, 246))
    draw = ImageDraw.Draw(catalog)

    # Header
    try:
        font_head = ImageFont.truetype("arialbd.ttf", 26)
        font_sub = ImageFont.truetype("arial.ttf", 16)
        font_num = ImageFont.truetype("arialbd.ttf", 18)
    except IOError:
        font_head = ImageFont.load_default()
        font_sub = ImageFont.load_default()
        font_num = ImageFont.load_default()

    draw.rectangle([0, 0, total_w, header_h], fill=(20, 30, 45))
    draw.text((25, 12), "🎨 Taqdimot Uchun Mavjud 6 Xil Dizayn", fill=(255, 255, 255), font=font_head)
    draw.text((25, 42), "O'zingizga yoqqan dizaynni quyidagi tugmalar orqali tanlang:", fill=(180, 200, 220), font=font_sub)

    temp_dir = os.path.join(os.path.dirname(output_path), "cache")
    os.makedirs(temp_dir, exist_ok=True)

    for idx, th in enumerate(themes_list):
        row = idx // 2
        col = idx % 2
        x = margin_x + col * (thumb_w + margin_x)
        y = header_h + margin_y + row * (thumb_h + margin_y)

        # Generate single preview and resize
        t_path = os.path.join(temp_dir, f"{th.id}.png")
        generate_preview_image(th, t_path, width=800, height=450)
        t_img = Image.open(t_path)
        t_thumb = t_img.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        catalog.paste(t_thumb, (x, y))

        # Add number badge on top-left of each thumb
        badge_box = [x + 8, y + 8, x + 38, y + 38]
        draw.rounded_rectangle(badge_box, radius=6, fill=(20, 30, 45), outline=(255, 255, 255), width=2)
        draw.text((x + 16, y + 12), str(idx + 1), fill=(255, 255, 255), font=font_num)

    catalog.save(output_path, "PNG", quality=95)
    return output_path
