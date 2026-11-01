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
    "ion": Theme(
        id="ion",
        name="🏛 Ion (Klassik)",
        short_name="Ion",
        description="Oq fon, to'q ko'k sarlavhalar va safir ko'k aksent",
        bg_color=(255, 255, 255),
        bg_color_end=(240, 246, 255),
        title_color=(15, 45, 105),        # Deep Classic Navy
        text_color=(45, 55, 72),          # Dark Slate
        accent_color=(30, 95, 220),       # Sapphire Blue
        card_bg_color=(246, 250, 255),
        card_border_color=(205, 222, 248),
        font_heading="Times New Roman",
        font_body="Times New Roman",
        is_dark=False
    ),
    "facet": Theme(
        id="facet",
        name="💎 Facet (Zamonaviy)",
        short_name="Facet",
        description="To'q ko'k gradient fon, moviy va oq kristall aksentlar",
        bg_color=(15, 23, 42),            # Midnight Slate
        bg_color_end=(30, 41, 59),
        title_color=(255, 255, 255),      # Pure White
        text_color=(215, 230, 250),       # Light Ice Blue
        accent_color=(56, 189, 248),      # Cyan Sky
        card_bg_color=(24, 34, 60),
        card_border_color=(51, 65, 85),
        font_heading="Times New Roman",
        font_body="Times New Roman",
        is_dark=True
    ),
    "savon": Theme(
        id="savon",
        name="🌿 Savon (Zumrad)",
        short_name="Savon",
        description="Nafis zumrad va yalpiz rangli organik tabiat shabloni",
        bg_color=(244, 250, 246),         # Soft Mint
        bg_color_end=(230, 244, 235),
        title_color=(15, 75, 45),         # Emerald Deep
        text_color=(40, 60, 50),          # Forest Slate
        accent_color=(16, 185, 129),      # Vibrant Emerald
        card_bg_color=(255, 255, 255),
        card_border_color=(185, 225, 205),
        font_heading="Times New Roman",
        font_body="Times New Roman",
        is_dark=False
    ),
    "madison": Theme(
        id="madison",
        name="👑 Madison (Qizil-Oltin)",
        short_name="Madison",
        description="To'q yoqut, fil suyagi va zarhal oltin aksentlar",
        bg_color=(254, 251, 246),         # Warm Ivory
        bg_color_end=(248, 240, 230),
        title_color=(135, 20, 35),        # Royal Crimson
        text_color=(55, 45, 45),          # Warm Charcoal
        accent_color=(217, 145, 25),      # Gold
        card_bg_color=(255, 255, 255),
        card_border_color=(235, 210, 175),
        font_heading="Times New Roman",
        font_body="Times New Roman",
        is_dark=False
    ),
    "atlas": Theme(
        id="atlas",
        name="⚪ Atlas (Minimal)",
        short_name="Atlas",
        description="Ultra-toza Shveysariya uslubi, nozik korall aksent",
        bg_color=(247, 248, 250),         # Neutral light
        bg_color_end=(238, 241, 246),
        title_color=(20, 25, 35),         # Pitch Charcoal
        text_color=(70, 80, 95),          # Slate Gray
        accent_color=(235, 87, 87),       # Editorial Coral
        card_bg_color=(255, 255, 255),
        card_border_color=(225, 230, 238),
        font_heading="Times New Roman",
        font_body="Times New Roman",
        is_dark=False
    ),
    "celestial": Theme(
        id="celestial",
        name="🌙 Celestial (Tungi Neon)",
        short_name="Celestial",
        description="Obsidian qora fon, neon indigo va kiber texno aksentlar",
        bg_color=(11, 15, 25),            # Deep Obsidian
        bg_color_end=(20, 26, 42),
        title_color=(245, 248, 255),      # Bright Light
        text_color=(180, 195, 220),       # Muted Gray
        accent_color=(129, 140, 248),     # Electric Indigo
        card_bg_color=(18, 23, 38),
        card_border_color=(45, 55, 85),
        font_heading="Times New Roman",
        font_body="Times New Roman",
        is_dark=True
    ),
    "retrospect": Theme(
        id="retrospect",
        name="💼 Retrospect (Biznes)",
        short_name="Retrospect",
        description="Korporativ po'lat kulrang va firuza aksentli biznes shablon",
        bg_color=(243, 246, 249),         # Steel Mist
        bg_color_end=(232, 238, 244),
        title_color=(25, 45, 65),         # Executive Navy
        text_color=(50, 65, 80),          # Cool Charcoal
        accent_color=(13, 148, 136),      # Teal Turquoise
        card_bg_color=(255, 255, 255),
        card_border_color=(200, 215, 225),
        font_heading="Times New Roman",
        font_body="Times New Roman",
        is_dark=False
    ),
    "studio": Theme(
        id="studio",
        name="☀️ Studio (Ijodiy)",
        short_name="Studio",
        description="Iliq qahva, terrakotta va kahrabo uyg'unligi",
        bg_color=(252, 249, 244),         # Warm Linen
        bg_color_end=(245, 238, 228),
        title_color=(75, 45, 30),         # Deep Espresso
        text_color=(65, 55, 50),          # Warm Slate
        accent_color=(225, 112, 85),      # Terracotta
        card_bg_color=(255, 255, 255),
        card_border_color=(232, 215, 198),
        font_heading="Times New Roman",
        font_body="Times New Roman",
        is_dark=False
    )
}

# Eski nomlar bilan moslashuvchanlik (Backward compatibility)
THEME_ALIASES: Dict[str, str] = {
    "classic": "ion",
    "modern": "facet",
    "nature": "savon",
    "royal": "madison",
    "minimal": "atlas",
    "dark": "celestial",
}

def get_theme(theme_id: str) -> Theme:
    norm_id = THEME_ALIASES.get(theme_id, theme_id)
    return THEMES.get(norm_id, THEMES["ion"])

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

    # Shriftlar
    try:
        font_title = ImageFont.truetype("timesbd.ttf", 32)
        font_subtitle = ImageFont.truetype("times.ttf", 19)
        font_body = ImageFont.truetype("times.ttf", 16)
        font_badge = ImageFont.truetype("timesbd.ttf", 14)
    except IOError:
        font_title = ImageFont.load_default()
        font_subtitle = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_badge = ImageFont.load_default()

    # 4. Shablon badge (teg)
    badge_text = f"  {theme.name}  "
    draw.rounded_rectangle(
        [pad_x + 30, pad_y + 25, pad_x + 230, pad_y + 55],
        radius=8,
        fill=theme.accent_color
    )
    badge_text_color = (10, 15, 25) if not theme.is_dark and theme.id not in ("ion", "madison") else (255, 255, 255)
    draw.text((pad_x + 40, pad_y + 30), badge_text, fill=badge_text_color, font=font_badge)

    # 5. Sarlavha namunasi
    draw.text((pad_x + 30, pad_y + 75), "PowerPoint Professional Slayd", fill=theme.title_color, font=font_title)
    draw.line([(pad_x + 30, pad_y + 118), (pad_x + 360, pad_y + 118)], fill=theme.accent_color, width=3)

    # 6. Mockup 2 qism: Chapda matn, o'ngda rasm infografika
    draw.text((pad_x + 30, pad_y + 135), theme.description, fill=theme.text_color, font=font_subtitle)

    bullets = [
        "• Muvozanatli matn va infografika",
        "• Akademik Times New Roman shrifti",
        "• PowerPoint mashhur shabloni"
    ]
    cur_y = pad_y + 175
    for b in bullets:
        draw.text((pad_x + 30, cur_y), b, fill=theme.text_color, font=font_body)
        cur_y += 32

    # O'ng tomonda infografika rasm maketi
    mock_x1 = width - pad_x - 260
    mock_y1 = pad_y + 75
    mock_x2 = width - pad_x - 30
    mock_y2 = height - pad_y - 30
    draw.rounded_rectangle(
        [mock_x1, mock_y1, mock_x2, mock_y2],
        radius=12,
        fill=theme.bg_color_end if not theme.is_dark else (28, 38, 64),
        outline=theme.accent_color,
        width=2
    )
    # Mockup ichida chizmalar
    draw.rounded_rectangle([mock_x1 + 20, mock_y2 - 60, mock_x1 + 55, mock_y2 - 20], radius=4, fill=theme.accent_color)
    draw.rounded_rectangle([mock_x1 + 75, mock_y2 - 100, mock_x1 + 110, mock_y2 - 20], radius=4, fill=theme.accent_color)
    draw.rounded_rectangle([mock_x1 + 130, mock_y2 - 140, mock_x1 + 165, mock_y2 - 20], radius=4, fill=theme.accent_color)
    draw.rounded_rectangle([mock_x1 + 185, mock_y2 - 80, mock_x1 + 220, mock_y2 - 20], radius=4, fill=theme.accent_color)

    img.save(output_path, "PNG")
    return output_path

def generate_catalog_image(output_path: str) -> str:
    """
    8 ta mashhur PowerPoint shablonlarini 4 qator x 2 ustun ko'rinishida
    birlashtirib bitta to'liq katalog rasm qiladi.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    themes = get_all_themes()

    cols = 2
    rows = (len(themes) + 1) // 2
    card_w = 720
    card_h = 380
    pad_x = 40
    pad_y = 40
    header_h = 130

    total_w = cols * card_w + (cols + 1) * pad_x
    total_h = header_h + rows * card_h + (rows + 1) * pad_y

    canvas = Image.new("RGB", (total_w, total_h), (245, 247, 250))
    draw = ImageDraw.Draw(canvas)

    # Sarlavha paneli
    draw.rectangle([0, 0, total_w, header_h], fill=(15, 23, 42))
    draw.rectangle([0, header_h - 4, total_w, header_h], fill=(56, 189, 248))

    try:
        font_head = ImageFont.truetype("timesbd.ttf", 36)
        font_sub = ImageFont.truetype("times.ttf", 20)
    except IOError:
        font_head = ImageFont.load_default()
        font_sub = ImageFont.load_default()

    draw.text((pad_x, 28), "PowerPoint Eng Mashhur Dizayn Shablonlari", fill=(255, 255, 255), font=font_head)
    draw.text((pad_x, 78), "Quyidagi 8 ta professional dizayndan birini tanlang:", fill=(148, 163, 184), font=font_sub)

    temp_dir = os.path.join(os.path.dirname(output_path), "theme_cards")
    os.makedirs(temp_dir, exist_ok=True)

    for idx, th in enumerate(themes):
        col = idx % cols
        row = idx // cols

        x = pad_x + col * (card_w + pad_x)
        y = header_h + pad_y + row * (card_h + pad_y)

        preview_file = os.path.join(temp_dir, f"{th.id}_card.png")
        generate_preview_image(th, preview_file, width=card_w, height=card_h)

        with Image.open(preview_file) as p_img:
            canvas.paste(p_img, (x, y))

    canvas.save(output_path, "PNG")
    return output_path
