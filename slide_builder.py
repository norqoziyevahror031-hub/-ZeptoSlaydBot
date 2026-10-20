import os
import time
import asyncio
import logging
from typing import List, Dict, Optional, Any, Callable
from PIL import Image

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from lxml import etree

from themes import Theme, get_theme
from image_service import get_4_slide_images
from ai_service import generate_slide_content

logger = logging.getLogger(__name__)

TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

# XML namespace for OpenXML DrawingML
DRAWINGML_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"

def set_times_new_roman(
    run,
    size_pt: Optional[float] = None,
    bold: Optional[bool] = None,
    italic: Optional[bool] = None,
    color_rgb: Optional[RGBColor] = None
) -> None:
    """
    Run uchun Times New Roman shriftini ham python-pptx obyekti darajasida,
    ham XML darajasida (latin, ea, cs) qat'iy o'rnatadi.
    Bu barcha qurilmalarda (Windows, Mac, Linux, telefon) shrift Times New Roman bo'lishini kafolatlaydi.
    """
    run.font.name = "Times New Roman"
    if size_pt is not None:
        run.font.size = Pt(size_pt)
    if bold is not None:
        run.font.bold = bold
    if italic is not None:
        run.font.italic = italic
    if color_rgb is not None:
        run.font.color.rgb = color_rgb

    # OpenXML a:rPr elementiga a:latin, a:ea, a:cs teglarini Times New Roman qilib yozish
    try:
        rPr = run._r.get_or_add_rPr()
        for tag in ("latin", "ea", "cs"):
            full_tag = f"{{{DRAWINGML_NS}}}{tag}"
            for child in rPr.findall(full_tag):
                rPr.remove(child)
            rPr.append(etree.Element(full_tag, attrib={"typeface": "Times New Roman"}))
    except Exception as e:
        logger.debug(f"XML shrift o'rnatishda e'tiborga olinmas xatolik: {e}")


def sanitize_filename(name: str) -> str:
    cleaned = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).rstrip()
    cleaned = "_".join(cleaned.split())
    return cleaned[:40] if cleaned else "Taqdimot"


def get_default_outline_titles(topic: str, total_slides: int) -> List[str]:
    """
    Slaydlar soniga mos standart akademik mavzular ketma-ketligi:
    Kirish, Asosiy tushunchalar, Tarixi, Turlari, Qo'llanilishi,
    Afzallik va kamchiliklar, Kelajak istiqbollari, Xulosa, Foydalanilgan adabiyotlar.
    """
    needed_content = max(1, total_slides - 1)

    all_titles = [
        f"Kirish: {topic[:35]}",
        "Asosiy Tushunchalar va Nazariy Asoslar",
        "Tarixi va Rivojlanish Bosqichlari",
        "Turlari va Funksional Tasnifi",
        "Amaliyotda Qo'llanilishi va Ahamiyati",
        "Afzalliklari va Mavjud Kamchiliklar Tahlili",
        "Kelajak Istiqbollari va Yangi Tendensiyalar",
        "Xulosa va Ilmiy-Amaliy Tavsiyalar",
        "Foydalanilgan Adabiyotlar va Manbalar"
    ]

    if needed_content <= len(all_titles):
        # 5 ta bo'lsa: Kirish, Tushunchalar, Qo'llanilishi, Xulosa
        if needed_content == 4:
            return [all_titles[0], all_titles[1], all_titles[4], all_titles[7]]
        # 8 ta bo'lsa: dastlabki 7 ta + Xulosa/Adabiyot
        selected = all_titles[:needed_content]
        selected[-1] = all_titles[-1] # Adabiyotlar
        if needed_content >= 2:
            selected[-2] = all_titles[-2] # Xulosa
        return selected

    # Agar 10 yoki 15 ta slayd so'ralsa, qo'shimcha tahlil sarlavhalarini kiritamiz
    extended = list(all_titles)
    diff = needed_content - len(all_titles)
    for i in range(1, diff + 1):
        extended.insert(5 + i, f"Tahliliy Yo'nalish va Tadqiqotlar ({i}-qism)")

    return extended[:needed_content]


class PresentationBuilder:
    def __init__(self, theme_id: str = "classic"):
        self.theme: Theme = get_theme(theme_id)
        self.prs = Presentation()
        # 16:9 HD Widescreen o'lchami: 13.333" x 7.5"
        self.prs.slide_width = Inches(13.333)
        self.prs.slide_height = Inches(7.5)
        self.blank_layout = self.prs.slide_layouts[6]

    def _apply_background(self, slide) -> None:
        """Slayd fonini tanlangan dizayn rangiga bo'yash."""
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(*self.theme.bg_color)

    def _add_top_accent_bar(self, slide) -> None:
        """Yuqori qismdagi nafis aksent chizig'i."""
        accent_bar = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0), Inches(0),
            self.prs.slide_width, Inches(0.12)
        )
        accent_bar.fill.solid()
        accent_bar.fill.fore_color.rgb = RGBColor(*self.theme.accent_color)
        accent_bar.line.fill.background()

    def add_title_slide(
        self,
        topic: str,
        author_name: str,
        group_name: str,
        university_name: Optional[str] = None,
        logo_path: Optional[str] = None
    ) -> None:
        """
        Titul slaydi:
        - Times New Roman shriftida
        - Yuqori o'rtada: Universitet logotipi
        - Universitet nomi
        - O'rtada: Katta mavzu sarlavhasi (36pt bold)
        - Pastda: 'Bajardi: Ism Familiya' va 'Guruh: ...'
        """
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._apply_background(slide)
        self._add_top_accent_bar(slide)

        sw = self.prs.slide_width
        sh = self.prs.slide_height

        card_margin_x = Inches(1.2)
        card_margin_y = Inches(0.8)
        card_w = sw - (card_margin_x * 2)
        card_h = sh - (card_margin_y * 2)

        card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            card_margin_x, card_margin_y, card_w, card_h
        )
        card.fill.solid()
        card.fill.fore_color.rgb = RGBColor(*self.theme.card_bg_color)
        card.line.color.rgb = RGBColor(*self.theme.accent_color if self.theme.is_dark else self.theme.card_border_color)
        card.line.width = Pt(1.5)

        current_top = card_margin_y + Inches(0.35)

        # 1. Logotip
        if logo_path and os.path.exists(logo_path):
            try:
                with Image.open(logo_path) as img:
                    orig_w, orig_h = img.size

                max_w_in = 2.4
                max_h_in = 1.3
                aspect = orig_w / max(1, orig_h)

                if aspect > (max_w_in / max_h_in):
                    final_w = max_w_in
                    final_h = max_w_in / aspect
                else:
                    final_h = max_h_in
                    final_w = max_h_in * aspect

                logo_left = (sw - Inches(final_w)) / 2
                slide.shapes.add_picture(
                    logo_path,
                    logo_left,
                    current_top,
                    width=Inches(final_w),
                    height=Inches(final_h)
                )
                current_top += Inches(final_h) + Inches(0.2)
            except Exception as e:
                logger.warning(f"Logotip qo'yishda xatolik: {e}")
                current_top += Inches(0.2)
        else:
            current_top += Inches(0.3)

        # 2. Universitet nomi (Times New Roman, 20pt)
        if university_name and university_name.strip():
            uni_box = slide.shapes.add_textbox(Inches(1.5), current_top, sw - Inches(3.0), Inches(0.6))
            tf_uni = uni_box.text_frame
            tf_uni.word_wrap = True
            p_uni = tf_uni.paragraphs[0]
            p_uni.alignment = PP_ALIGN.CENTER
            r_uni = p_uni.add_run()
            r_uni.text = university_name.strip().upper()
            set_times_new_roman(
                r_uni,
                size_pt=20,
                bold=True,
                color_rgb=RGBColor(*self.theme.accent_color)
            )
            current_top += Inches(0.7)
        else:
            current_top += Inches(0.3)

        # 3. Taqdimot Mavzusi (Times New Roman, 36pt bold)
        topic_box = slide.shapes.add_textbox(Inches(1.5), current_top, sw - Inches(3.0), Inches(1.8))
        tf_topic = topic_box.text_frame
        tf_topic.word_wrap = True
        p_topic = tf_topic.paragraphs[0]
        p_topic.alignment = PP_ALIGN.CENTER
        r_topic = p_topic.add_run()
        r_topic.text = topic.strip()
        set_times_new_roman(
            r_topic,
            size_pt=36,
            bold=True,
            color_rgb=RGBColor(*self.theme.title_color)
        )

        # Ajratuvchi chiziq
        divider_top = current_top + Inches(1.9)
        div = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            (sw - Inches(3.5)) / 2, divider_top, Inches(3.5), Inches(0.04)
        )
        div.fill.solid()
        div.fill.fore_color.rgb = RGBColor(*self.theme.accent_color)
        div.line.fill.background()

        # 4. Pastki qism: Bajardi va Guruh (Times New Roman)
        info_top = divider_top + Inches(0.25)
        info_box = slide.shapes.add_textbox(Inches(1.5), info_top, sw - Inches(3.0), Inches(1.2))
        tf_info = info_box.text_frame
        tf_info.word_wrap = True

        p_author = tf_info.paragraphs[0]
        p_author.alignment = PP_ALIGN.CENTER
        r_author = p_author.add_run()
        r_author.text = f"Bajardi: {author_name.strip()}"
        set_times_new_roman(
            r_author,
            size_pt=20,
            bold=True,
            color_rgb=RGBColor(*self.theme.title_color)
        )

        if group_name and group_name.strip():
            p_group = tf_info.add_paragraph()
            p_group.alignment = PP_ALIGN.CENTER
            r_group = p_group.add_run()
            r_group.text = f"Guruh: {group_name.strip()}"
            set_times_new_roman(
                r_group,
                size_pt=18,
                bold=False,
                color_rgb=RGBColor(*self.theme.text_color)
            )

    def add_content_slide_with_2x2_grid(
        self,
        title: str,
        intro_text: str,
        bullets: List[str],
        conclusion_text: str,
        images_4: List[str],
        current_num: int,
        total_num: int,
        footer_topic: str = "",
        student_info: str = ""
    ) -> None:
        """
        Ikki qismga bo'lingan mazmunli slayd:
        - 1-yarmi: Matn bloki (kamida 80-120 so'z, intro + 5-6 bullets + xulosa)
        - 2-yarmi: 4 ta mavzuga mos rasm (2x2 setka ko'rinishida, ramka bilan)
        - Dizayn go'zalligi uchun toq slaydlarda matn chapda, juft slaydlarda o'ngda!
        - Barcha shriftlar: Times New Roman!
        """
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._apply_background(slide)
        self._add_top_accent_bar(slide)

        sw = self.prs.slide_width
        sh = self.prs.slide_height

        # 1. Sarlavha (Times New Roman, 32pt bold)
        title_box = slide.shapes.add_textbox(
            Inches(0.8), Inches(0.4), sw - Inches(1.6), Inches(0.85)
        )
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        r_title = p_title.add_run()
        r_title.text = title.strip()
        set_times_new_roman(
            r_title,
            size_pt=32,
            bold=True,
            color_rgb=RGBColor(*self.theme.title_color)
        )

        # Sarlavha ostidagi nafis aksent chizig'i
        line = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            Inches(0.8), Inches(1.3), Inches(3.2), Inches(0.04)
        )
        line.fill.solid()
        line.fill.fore_color.rgb = RGBColor(*self.theme.accent_color)
        line.line.fill.background()

        # 2. Maydonlar koordinatalari
        # Butun ishchi soha: kengligi ~11.7", balandligi ~5.2"
        half_w = Inches(5.7)
        section_h = Inches(5.15)
        top_pos = Inches(1.5)

        # Navbatma-navbat almashish:
        # Agar current_num toq bo'lsa (2-slayd = toq kontent slaydi): matn chapda, rasmlar o'ngda
        # Agar juft bo'lsa: rasmlar chapda, matn o'ngda
        text_on_left = (current_num % 2 == 0)

        if text_on_left:
            text_x = Inches(0.8)
            img_x = Inches(6.83)
        else:
            img_x = Inches(0.8)
            text_x = Inches(6.83)

        # 3. MATN BLOKI
        # Matn kartasi
        text_card = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE,
            text_x, top_pos, half_w, section_h
        )
        text_card.fill.solid()
        text_card.fill.fore_color.rgb = RGBColor(*self.theme.card_bg_color)
        text_card.line.color.rgb = RGBColor(*self.theme.card_border_color)
        text_card.line.width = Pt(1)

        # Matn qutisi
        text_box = slide.shapes.add_textbox(
            text_x + Inches(0.25), top_pos + Inches(0.2),
            half_w - Inches(0.5), section_h - Inches(0.4)
        )
        tf_body = text_box.text_frame
        tf_body.word_wrap = True

        # So'zlar soniga qarab shrift o'lchamini optimallashtirish (sig'ishi uchun)
        all_words = len(intro_text.split()) + sum(len(b.split()) for b in bullets) + len(conclusion_text.split())
        if all_words > 115:
            body_pt = 13.5
            bullet_pt = 13.5
            space_b = Pt(3)
        elif all_words > 95:
            body_pt = 14.5
            bullet_pt = 14.5
            space_b = Pt(4)
        else:
            body_pt = 15.5
            bullet_pt = 15.0
            space_b = Pt(5)

        # A) Kirish jumlasi
        p_intro = tf_body.paragraphs[0]
        r_intro = p_intro.add_run()
        r_intro.text = intro_text.strip()
        set_times_new_roman(
            r_intro,
            size_pt=body_pt,
            bold=True,
            italic=False,
            color_rgb=RGBColor(*self.theme.title_color)
        )
        p_intro.space_after = Pt(4)

        # B) 5-6 ta bullet punktlar
        for b in bullets:
            clean_b = b.strip()
            if not clean_b:
                continue
            p_b = tf_body.add_paragraph()
            p_b.space_before = space_b
            p_b.space_after = Pt(2)
            
            # Bullet belgisi
            r_marker = p_b.add_run()
            r_marker.text = "•  "
            set_times_new_roman(
                r_marker,
                size_pt=bullet_pt,
                bold=True,
                color_rgb=RGBColor(*self.theme.accent_color)
            )

            # Matn
            r_text = p_b.add_run()
            r_text.text = clean_b
            set_times_new_roman(
                r_text,
                size_pt=bullet_pt,
                bold=False,
                color_rgb=RGBColor(*self.theme.text_color)
            )

        # C) Xulosa jumlasi
        if conclusion_text:
            p_concl = tf_body.add_paragraph()
            p_concl.space_before = Pt(6)
            r_c = p_concl.add_run()
            r_c.text = f"💡 {conclusion_text.strip()}"
            set_times_new_roman(
                r_c,
                size_pt=body_pt - 1.0,
                bold=False,
                italic=True,
                color_rgb=RGBColor(*self.theme.accent_color if not self.theme.is_dark else self.theme.text_color)
            )

        # 4. 2x2 RASMLAR SETKASI
        # 4 ta rasm o'lchamlari
        # Kenglik: (5.7 - 0.2 gap) / 2 = 2.75"
        # Balandlik: (5.15 - 0.2 gap) / 2 = 2.475"
        img_w = Inches(2.75)
        img_h = Inches(2.47)
        gap_x = Inches(0.2)
        gap_y = Inches(0.2)

        for idx, img_path in enumerate(images_4[:4]):
            row = idx // 2
            col = idx % 2
            x_pos = img_x + col * (img_w + gap_x)
            y_pos = top_pos + row * (img_h + gap_y)

            # Rasm orqasidagi ramka karta (aksent hoshiya bilan)
            frame_card = slide.shapes.add_shape(
                MSO_SHAPE.ROUNDED_RECTANGLE,
                x_pos, y_pos, img_w, img_h
            )
            frame_card.fill.solid()
            frame_card.fill.fore_color.rgb = RGBColor(*self.theme.card_bg_color)
            frame_card.line.color.rgb = RGBColor(*self.theme.accent_color)
            frame_card.line.width = Pt(1.5)

            # Rasmni joylashtirish
            if img_path and os.path.exists(img_path):
                try:
                    # Nozik 0.04" ichki chegara bilan rasm
                    pad = Inches(0.04)
                    slide.shapes.add_picture(
                        img_path,
                        x_pos + pad,
                        y_pos + pad,
                        width=img_w - (pad * 2),
                        height=img_h - (pad * 2)
                    )
                except Exception as e:
                    logger.warning(f"Rasmni slaydga qo'yishda xatolik ({img_path}): {e}")

        # 5. Pastki Footer (Times New Roman, 11pt)
        footer_box = slide.shapes.add_textbox(
            Inches(0.8), sh - Inches(0.65), sw - Inches(1.6), Inches(0.4)
        )
        tf_foot = footer_box.text_frame
        p_foot = tf_foot.paragraphs[0]
        p_foot.alignment = PP_ALIGN.RIGHT

        parts = []
        if footer_topic:
            parts.append(footer_topic[:35])
        if student_info:
            parts.append(student_info)
        parts.append(f"{current_num} / {total_num}")

        r_foot = p_foot.add_run()
        r_foot.text = "   •   ".join(parts)
        set_times_new_roman(
            r_foot,
            size_pt=11,
            bold=False,
            color_rgb=RGBColor(*self.theme.text_color)
        )

    def save(self, output_path: str) -> str:
        """Taqdimotni faylga saqlaydi."""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        self.prs.save(output_path)
        return output_path


async def build_presentation_full(
    user_id: int,
    theme_id: str,
    topic: str,
    author_name: str,
    group_name: str,
    university_name: Optional[str],
    logo_path: Optional[str],
    slide_count: int,
    custom_slides: Optional[List[Dict[str, Any]]] = None,
    progress_callback: Optional[Callable[[int, str], Any]] = None,
    gemini_api_key: Optional[str] = None,
    pexels_api_key: Optional[str] = None
) -> Tuple[str, List[str]]:
    """
    To'liq yangilangan taqdimot generatori:
    - 1-slayd: Titul
    - 2..N slaydlar: 2 ga bo'lingan (matn + 4 ta rasm)
    - Times New Roman shriftida
    - 80-120 so'z boyitilgan ilmiy matn
    - Real-time progress yangilash bilan
    """
    builder = PresentationBuilder(theme_id=theme_id)
    all_temp_images: List[str] = []
    used_image_ids: set = set()

    # Progress 10%
    if progress_callback:
        await progress_callback(10, "⏳ Mavzu bo'yicha ilmiy reja tuzilmoqda...")

    # 1. Titul slayd
    builder.add_title_slide(
        topic=topic,
        author_name=author_name,
        group_name=group_name,
        university_name=university_name,
        logo_path=logo_path
    )

    # 2. Slaydlar tarkibini aniqlash
    if custom_slides:
        slides_to_generate = custom_slides
    else:
        titles = get_default_outline_titles(topic, slide_count)
        slides_to_generate = [{"title": t, "bullets": None} for t in titles]

    total_content_slides = len(slides_to_generate)
    total_slides = 1 + total_content_slides
    student_label = f"{author_name} ({group_name})" if group_name else author_name

    # 3. Har bir slayd uchun matn va 4 ta rasm tayyorlash
    for idx, slide_item in enumerate(slides_to_generate, start=2):
        s_title = slide_item.get("title", f"Slayd {idx}")
        user_draft = " ".join(slide_item.get("bullets", [])) if slide_item.get("bullets") else None

        # Progress yangilash (20% -> 80%)
        current_percent = int(20 + ((idx - 1) / total_content_slides) * 60)
        if progress_callback:
            await progress_callback(
                current_percent,
                f"⏳ {idx}-slayd tayyorlanmoqda: «{s_title[:25]}» (matn va 4 ta rasm)..."
            )

        # A) Matnni AI orqali boyitish (80-120 so'z)
        text_data = await generate_slide_content(
            topic=topic,
            slide_title=s_title,
            user_draft=user_draft,
            gemini_api_key=gemini_api_key
        )

        # B) 4 ta mavzuga mos rasm olish (parallel yuklash, 2x2 crop)
        images_4 = await get_4_slide_images(
            topic=topic,
            slide_title=s_title,
            user_id=user_id,
            slide_idx=idx,
            theme=builder.theme,
            used_ids=used_image_ids,
            pexels_api_key=pexels_api_key
        )
        all_temp_images.extend(images_4)

        # C) Slaydga joylashtirish
        builder.add_content_slide_with_2x2_grid(
            title=s_title,
            intro_text=text_data.get("intro", ""),
            bullets=text_data.get("bullets", []),
            conclusion_text=text_data.get("conclusion", ""),
            images_4=images_4,
            current_num=idx,
            total_num=total_slides,
            footer_topic=topic,
            student_info=student_label
        )

    # Progress 90%
    if progress_callback:
        await progress_callback(90, "⏳ PowerPoint (.pptx) fayli shakllantirilmoqda...")

    safe_topic = sanitize_filename(topic)
    author_last = sanitize_filename(author_name.split()[-1] if author_name.split() else "Talaba")
    timestamp = int(time.time())
    file_name = f"{safe_topic}_{author_last}_{user_id}_{timestamp}.pptx"
    output_path = os.path.join(TEMP_DIR, file_name)

    # Faylga saqlash
    await asyncio.to_thread(builder.save, output_path)

    # Progress 100%
    if progress_callback:
        await progress_callback(100, "✅ Taqdimot tayyor!")

    return output_path, all_temp_images
