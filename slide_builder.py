import os
import time
import asyncio
import logging
from typing import List, Dict, Optional, Any, Callable, Tuple
from PIL import Image

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from lxml import etree

from themes import Theme, get_theme
from image_service import get_slide_illustration
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

    try:
        rPr = run._r.get_or_add_rPr()
        for tag in ("latin", "ea", "cs"):
            full_tag = f"{{{DRAWINGML_NS}}}{tag}"
            for child in rPr.findall(full_tag):
                rPr.remove(child)
            rPr.append(etree.Element(full_tag, attrib={"typeface": "Times New Roman"}))
    except Exception as e:
        logger.debug(f"XML shrift o'rnatishda xatolik: {e}")


def sanitize_filename(name: str) -> str:
    cleaned = "".join(c for c in name if c.isalnum() or c in (" ", "_", "-")).rstrip()
    cleaned = "_".join(cleaned.split())
    return cleaned[:40] if cleaned else "Taqdimot"


def should_have_image(slide_idx: int, total_slides: int) -> bool:
    """
    Slaydda rasm bo'lishi kerakligini aniqlaydi.
    10 ta slayddan iborat taqdimotda roppa-rosa 5 ta rasm bo'ladi:
    - 2-slayd: Matn
    - 3-slayd: Rasm 1
    - 4-slayd: Matn
    - 5-slayd: Rasm 2
    - 6-slayd: Matn
    - 7-slayd: Rasm 3
    - 8-slayd: Matn
    - 9-slayd: Rasm 4
    - 10-slayd: Rasm 5 (Yakuniy infografika)
    Jami: 5 ta rasm, matn va rasm navbatma-navbat almashadi!
    """
    if total_slides == 10:
        return slide_idx in (3, 5, 7, 9, 10)
    
    if total_slides <= 5:
        return slide_idx in (3, 5)

    # Boshqa slayd sonlari uchun navbatma-navbat almashish
    return (slide_idx % 2 == 1) or (slide_idx == total_slides)


def get_default_outline_titles(topic: str, total_slides: int) -> List[str]:
    """
    Slaydlar soniga mos standart akademik mavzular ketma-ketligi:
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
        if needed_content == 4:
            return [all_titles[0], all_titles[1], all_titles[4], all_titles[7]]
        selected = all_titles[:needed_content]
        selected[-1] = all_titles[-1]
        if needed_content >= 2:
            selected[-2] = all_titles[-2]
        return selected

    extended = list(all_titles)
    diff = needed_content - len(all_titles)
    for i in range(1, diff + 1):
        extended.insert(5 + i, f"Tahliliy Yo'nalish va Tadqiqotlar ({i}-qism)")

    return extended[:needed_content]


def get_automatic_slide_outline(topic: str, total_slides: int) -> List[Dict[str, Any]]:
    """Qo'lda to'ldirish paytida qolgan slaydlar uchun avtomatik reja."""
    titles = get_default_outline_titles(topic, total_slides)
    return [{"title": t, "bullets": None} for t in titles]


class PresentationBuilder:
    def __init__(self, theme_id: str = "ion"):
        self.theme: Theme = get_theme(theme_id)
        self.prs = Presentation()
        # 16:9 HD Widescreen o'lchami: 13.333" x 7.5"
        self.prs.slide_width = Inches(13.333)
        self.prs.slide_height = Inches(7.5)
        self.blank_layout = self.prs.slide_layouts[6]
        self._image_slide_count = 0

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
        - Universitet logotipi va nomi
        - Katta mavzu sarlavhasi (34-36pt bold)
        - Muallif va guruh
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

                max_w_in = 2.2
                max_h_in = 1.2
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
                current_top += Inches(final_h) + Inches(0.18)
            except Exception as e:
                logger.warning(f"Logotip qo'yishda xatolik: {e}")

        # 2. Universitet nomi
        if university_name and university_name.strip():
            uni_box = slide.shapes.add_textbox(Inches(1.5), current_top, sw - Inches(3.0), Inches(0.45))
            tf_uni = uni_box.text_frame
            tf_uni.word_wrap = True
            p_uni = tf_uni.paragraphs[0]
            p_uni.alignment = PP_ALIGN.CENTER
            r_uni = p_uni.add_run()
            r_uni.text = university_name.strip().upper()
            set_times_new_roman(
                r_uni,
                size_pt=14,
                bold=True,
                color_rgb=RGBColor(*self.theme.accent_color)
            )
            current_top += Inches(0.45)

        # 3. Mavzu
        topic_box = slide.shapes.add_textbox(Inches(1.5), current_top, sw - Inches(3.0), Inches(1.8))
        tf_topic = topic_box.text_frame
        tf_topic.word_wrap = True
        p_topic = tf_topic.paragraphs[0]
        p_topic.alignment = PP_ALIGN.CENTER
        r_topic = p_topic.add_run()
        r_topic.text = topic.strip()
        set_times_new_roman(
            r_topic,
            size_pt=34 if len(topic) < 45 else 28,
            bold=True,
            color_rgb=RGBColor(*self.theme.title_color)
        )

        divider_top = current_top + Inches(1.8)
        divider = slide.shapes.add_shape(
            MSO_SHAPE.RECTANGLE,
            (sw - Inches(3.5)) / 2, divider_top, Inches(3.5), Inches(0.04)
        )
        divider.fill.solid()
        divider.fill.fore_color.rgb = RGBColor(*self.theme.accent_color)
        divider.line.fill.background()

        # 4. Muallif va guruh
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
            size_pt=19,
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
                size_pt=17,
                bold=False,
                color_rgb=RGBColor(*self.theme.text_color)
            )

    def add_text_only_slide(
        self,
        title: str,
        intro_text: str,
        bullets: List[str],
        conclusion_text: str,
        current_num: int,
        total_num: int,
        footer_topic: str = "",
        student_info: str = ""
    ) -> None:
        """
        Faqat matnli slayd (2 ta muvozanatli zamonaviy ustun/karta).
        Katta 16:9 ekranda bo'sh joy qolmasligi uchun 2 ustun shaklida chiroyli taqsimlanadi.
        """
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._apply_background(slide)
        self._add_top_accent_bar(slide)

        sw = self.prs.slide_width
        sh = self.prs.slide_height

        # 1. Sarlavha
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), sw - Inches(1.6), Inches(0.85))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        r_title = p_title.add_run()
        r_title.text = title.strip()
        set_times_new_roman(r_title, size_pt=32, bold=True, color_rgb=RGBColor(*self.theme.title_color))

        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.3), Inches(3.2), Inches(0.04))
        line.fill.solid()
        line.fill.fore_color.rgb = RGBColor(*self.theme.accent_color)
        line.line.fill.background()

        # 2 ta karta o'lchamlari
        col_w = Inches(5.7)
        section_h = Inches(5.15)
        top_pos = Inches(1.5)
        left_x = Inches(0.8)
        right_x = Inches(6.83)

        # 1-Karta: Nazariy asoslar va Kirish
        card1 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left_x, top_pos, col_w, section_h)
        card1.fill.solid()
        card1.fill.fore_color.rgb = RGBColor(*self.theme.card_bg_color)
        card1.line.color.rgb = RGBColor(*self.theme.card_border_color)
        card1.line.width = Pt(1)

        box1 = slide.shapes.add_textbox(left_x + Inches(0.25), top_pos + Inches(0.2), col_w - Inches(0.5), section_h - Inches(0.4))
        tf1 = box1.text_frame
        tf1.word_wrap = True

        p1_h = tf1.paragraphs[0]
        r1_h = p1_h.add_run()
        r1_h.text = "📌 Nazariy Asoslar va Kirish"
        set_times_new_roman(r1_h, size_pt=16, bold=True, color_rgb=RGBColor(*self.theme.accent_color))
        p1_h.space_after = Pt(8)

        p1_intro = tf1.add_paragraph()
        r1_in = p1_intro.add_run()
        r1_in.text = intro_text.strip()
        set_times_new_roman(r1_in, size_pt=14.5, bold=False, color_rgb=RGBColor(*self.theme.title_color))
        p1_intro.space_after = Pt(10)

        # 1-karta uchun dastlabki 3 ta punkt
        for b in bullets[:3]:
            if not b.strip():
                continue
            p = tf1.add_paragraph()
            p.space_after = Pt(6)
            r_m = p.add_run()
            r_m.text = "• "
            set_times_new_roman(r_m, size_pt=14, bold=True, color_rgb=RGBColor(*self.theme.accent_color))
            r_t = p.add_run()
            r_t.text = b.strip()
            set_times_new_roman(r_t, size_pt=14, color_rgb=RGBColor(*self.theme.text_color))

        # 2-Karta: Amaliy Tahlil va Yakuniy Xulosa
        card2 = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, right_x, top_pos, col_w, section_h)
        card2.fill.solid()
        card2.fill.fore_color.rgb = RGBColor(*self.theme.card_bg_color)
        card2.line.color.rgb = RGBColor(*self.theme.card_border_color)
        card2.line.width = Pt(1)

        box2 = slide.shapes.add_textbox(right_x + Inches(0.25), top_pos + Inches(0.2), col_w - Inches(0.5), section_h - Inches(0.4))
        tf2 = box2.text_frame
        tf2.word_wrap = True

        p2_h = tf2.paragraphs[0]
        r2_h = p2_h.add_run()
        r2_h.text = "⚡ Amaliy Tahlil va Natijalar"
        set_times_new_roman(r2_h, size_pt=16, bold=True, color_rgb=RGBColor(*self.theme.accent_color))
        p2_h.space_after = Pt(8)

        # Keyingi punktlar
        remaining_bullets = bullets[3:] if len(bullets) > 3 else bullets[1:]
        for b in remaining_bullets[:3]:
            if not b.strip():
                continue
            p = tf2.add_paragraph()
            p.space_after = Pt(6)
            r_m = p.add_run()
            r_m.text = "• "
            set_times_new_roman(r_m, size_pt=14, bold=True, color_rgb=RGBColor(*self.theme.accent_color))
            r_t = p.add_run()
            r_t.text = b.strip()
            set_times_new_roman(r_t, size_pt=14, color_rgb=RGBColor(*self.theme.text_color))

        # Yakuniy xulosa bloki
        if conclusion_text:
            p_c = tf2.add_paragraph()
            p_c.space_before = Pt(10)
            r_c = p_c.add_run()
            r_c.text = f"💡 Xulosa: {conclusion_text.strip()}"
            set_times_new_roman(
                r_c,
                size_pt=13.5,
                italic=True,
                color_rgb=RGBColor(*self.theme.accent_color if not self.theme.is_dark else self.theme.text_color)
            )

        # Footer
        self._add_footer(slide, current_num, total_num, footer_topic, student_info)

    def add_half_image_slide(
        self,
        title: str,
        intro_text: str,
        bullets: List[str],
        conclusion_text: str,
        image_path: str,
        current_num: int,
        total_num: int,
        footer_topic: str = "",
        student_info: str = ""
    ) -> None:
        """
        Yarmida rasm, yarmida matn bo'lgan slayd:
        - 1 ta katta chiroyli infografika rasm (5.7" x 5.15")
        - Matn bloki (kamida 80-120 so'z)
        - Navbatma-navbat almashish: bir slaydda rasm o'ngda, keyingisida chapda!
        """
        slide = self.prs.slides.add_slide(self.blank_layout)
        self._apply_background(slide)
        self._add_top_accent_bar(slide)

        sw = self.prs.slide_width
        sh = self.prs.slide_height

        # Sarlavha
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), sw - Inches(1.6), Inches(0.85))
        tf_title = title_box.text_frame
        tf_title.word_wrap = True
        p_title = tf_title.paragraphs[0]
        r_title = p_title.add_run()
        r_title.text = title.strip()
        set_times_new_roman(r_title, size_pt=32, bold=True, color_rgb=RGBColor(*self.theme.title_color))

        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.3), Inches(3.2), Inches(0.04))
        line.fill.solid()
        line.fill.fore_color.rgb = RGBColor(*self.theme.accent_color)
        line.line.fill.background()

        half_w = Inches(5.7)
        section_h = Inches(5.15)
        top_pos = Inches(1.5)

        # Rasm va matnning o'rnini navbatma-navbat almashtirish
        # self._image_slide_count ga qarab: toq bo'lsa o'ngda, juft bo'lsa chapda
        self._image_slide_count += 1
        image_on_right = (self._image_slide_count % 2 == 1)

        if image_on_right:
            text_x = Inches(0.8)
            img_x = Inches(6.83)
        else:
            img_x = Inches(0.8)
            text_x = Inches(6.83)

        # 1. MATN BLOKI
        text_card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, text_x, top_pos, half_w, section_h)
        text_card.fill.solid()
        text_card.fill.fore_color.rgb = RGBColor(*self.theme.card_bg_color)
        text_card.line.color.rgb = RGBColor(*self.theme.card_border_color)
        text_card.line.width = Pt(1)

        text_box = slide.shapes.add_textbox(text_x + Inches(0.25), top_pos + Inches(0.2), half_w - Inches(0.5), section_h - Inches(0.4))
        tf_body = text_box.text_frame
        tf_body.word_wrap = True

        # Kirish
        p_intro = tf_body.paragraphs[0]
        r_intro = p_intro.add_run()
        r_intro.text = intro_text.strip()
        set_times_new_roman(r_intro, size_pt=14.5, bold=True, color_rgb=RGBColor(*self.theme.title_color))
        p_intro.space_after = Pt(6)

        # 4-5 ta punktlar
        for b in bullets:
            clean_b = b.strip()
            if not clean_b:
                continue
            p_b = tf_body.add_paragraph()
            p_b.space_before = Pt(4)
            p_b.space_after = Pt(2)
            r_marker = p_b.add_run()
            r_marker.text = "• "
            set_times_new_roman(r_marker, size_pt=14, bold=True, color_rgb=RGBColor(*self.theme.accent_color))
            r_text = p_b.add_run()
            r_text.text = clean_b
            set_times_new_roman(r_text, size_pt=14, color_rgb=RGBColor(*self.theme.text_color))

        # Xulosa
        if conclusion_text:
            p_concl = tf_body.add_paragraph()
            p_concl.space_before = Pt(8)
            r_c = p_concl.add_run()
            r_c.text = f"💡 {conclusion_text.strip()}"
            set_times_new_roman(
                r_c,
                size_pt=13,
                italic=True,
                color_rgb=RGBColor(*self.theme.accent_color if not self.theme.is_dark else self.theme.text_color)
            )

        # 2. 1 TA KATTA RASM BLOKI
        # Rasm slaydda ajratilgan joyga (half_w x section_h = 5.7" x 5.15") to'liq,
        # silliq yumaloqlangan burchaklar va uyg'un hoshiya bilan joylashadi.
        if image_path and os.path.exists(image_path):
            try:
                slide.shapes.add_picture(
                    image_path,
                    img_x,
                    top_pos,
                    width=half_w,
                    height=section_h
                )
            except Exception as e:
                logger.warning(f"Rasmni slaydga qo'yishda xatolik ({image_path}): {e}")

        # Footer
        self._add_footer(slide, current_num, total_num, footer_topic, student_info)

    def _add_footer(self, slide, current_num: int, total_num: int, footer_topic: str, student_info: str):
        sw = self.prs.slide_width
        sh = self.prs.slide_height
        footer_box = slide.shapes.add_textbox(Inches(0.8), sh - Inches(0.65), sw - Inches(1.6), Inches(0.4))
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
        set_times_new_roman(r_foot, size_pt=11, bold=False, color_rgb=RGBColor(*self.theme.text_color))

    # Backward compatibility
    def add_content_slide_with_2x2_grid(self, *args, **kwargs):
        images = kwargs.get("images_4", [])
        img = images[0] if images else ""
        return self.add_half_image_slide(
            title=kwargs.get("title", ""),
            intro_text=kwargs.get("intro_text", ""),
            bullets=kwargs.get("bullets", []),
            conclusion_text=kwargs.get("conclusion_text", ""),
            image_path=img,
            current_num=kwargs.get("current_num", 1),
            total_num=kwargs.get("total_num", 1),
            footer_topic=kwargs.get("footer_topic", ""),
            student_info=kwargs.get("student_info", "")
        )

    def save(self, output_path: str) -> str:
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
    Yangi professional taqdimot generatori:
    - 1-slayd: Titul
    - Navbatma-navbat: Bir slaydda faqat matn, keyingisida yarmida rasm, yarmida matn.
    - 10 ta slaydda roppa-rosa 5 ta rasm hosil bo'ladi.
    - Rasmlar avtomatik yuqori sifatda yaratiladi.
    - Times New Roman akademik shrifti.
    """
    builder = PresentationBuilder(theme_id=theme_id)
    all_temp_images: List[str] = []
    used_image_ids: Set[str] = set()

    # Progress 10%
    if progress_callback:
        await progress_callback(10, "⏳ Mavzu bo'yicha akademik reja tuzilmoqda...")

    # 1. Titul slayd
    builder.add_title_slide(
        topic=topic,
        author_name=author_name,
        group_name=group_name,
        university_name=university_name,
        logo_path=logo_path
    )

    # 2. Slaydlar ro'yxatini aniqlash
    if custom_slides:
        slides_to_generate = custom_slides
    else:
        titles = get_default_outline_titles(topic, slide_count)
        slides_to_generate = [{"title": t, "bullets": None} for t in titles]

    total_content_slides = len(slides_to_generate)
    total_slides = 1 + total_content_slides
    student_label = f"{author_name} ({group_name})" if group_name else author_name

    # 3. Har bir slaydni shakllantirish
    for idx, slide_item in enumerate(slides_to_generate, start=2):
        s_title = slide_item.get("title", f"Slayd {idx}")
        user_draft = " ".join(slide_item.get("bullets", [])) if slide_item.get("bullets") else None

        has_image = should_have_image(idx, total_slides)
        slide_type_label = "yarim rasm + matn" if has_image else "matnli tahlil"

        current_percent = int(15 + ((idx - 1) / total_content_slides) * 70)
        if progress_callback:
            await progress_callback(
                current_percent,
                f"⏳ {idx}/{total_slides}-slayd ({slide_type_label}): «{s_title[:24]}»..."
            )

        # Matn yaratish
        text_data = await generate_slide_content(
            topic=topic,
            slide_title=s_title,
            user_draft=user_draft,
            gemini_api_key=gemini_api_key
        )

        if has_image:
            # Tematik haqiqiy fotosuratni olish
            img_path = await get_slide_illustration(
                topic=topic,
                slide_title=s_title,
                user_id=user_id,
                slide_idx=idx,
                theme=builder.theme,
                used_ids=used_image_ids,
                pexels_api_key=pexels_api_key
            )
            all_temp_images.append(img_path)

            builder.add_half_image_slide(
                title=s_title,
                intro_text=text_data.get("intro", ""),
                bullets=text_data.get("bullets", []),
                conclusion_text=text_data.get("conclusion", ""),
                image_path=img_path,
                current_num=idx,
                total_num=total_slides,
                footer_topic=topic,
                student_info=student_label
            )
        else:
            # Faqat matnli slayd (2 ustunli zamonaviy karta)
            builder.add_text_only_slide(
                title=s_title,
                intro_text=text_data.get("intro", ""),
                bullets=text_data.get("bullets", []),
                conclusion_text=text_data.get("conclusion", ""),
                current_num=idx,
                total_num=total_slides,
                footer_topic=topic,
                student_info=student_label
            )

    # Progress 90%
    if progress_callback:
        await progress_callback(90, "⏳ PowerPoint (.pptx) fayli saqlanmoqda...")

    safe_topic = sanitize_filename(topic)
    author_last = sanitize_filename(author_name.split()[-1] if author_name.split() else "Talaba")
    timestamp = int(time.time())
    file_name = f"{safe_topic}_{author_last}_{user_id}_{timestamp}.pptx"
    output_path = os.path.join(TEMP_DIR, file_name)

    await asyncio.to_thread(builder.save, output_path)

    if progress_callback:
        await progress_callback(100, "✅ Taqdimot tayyor!")

    return output_path, all_temp_images
