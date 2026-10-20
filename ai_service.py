import os
import json
import logging
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger(__name__)

async def generate_slide_content(
    topic: str,
    slide_title: str,
    user_draft: Optional[str] = None,
    gemini_api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Slayd uchun kamida 80-120 so'zdan iborat to'liq matn (kirish + 5-6 bullet + xulosa) yaratadi.
    Gemini API mavjud bo'lsa undan foydalanadi, aks holda yuqori sifatli akademik generator ishlaydi.
    """
    # 1. Gemini API orqali urinib ko'rish
    if gemini_api_key:
        try:
            content = await _call_gemini_api(topic, slide_title, user_draft, gemini_api_key)
            if content and len(content.get("bullets", [])) >= 4:
                # So'zlar sonini tekshirish
                total_words = len(content.get("intro", "").split()) + sum(len(b.split()) for b in content.get("bullets", [])) + len(content.get("conclusion", "").split())
                if total_words >= 70:
                    return content
        except Exception as e:
            logger.warning(f"Gemini API orqali matn olishda xatolik: {e}")

    # 2. Boyitilgan akademik fallback generator
    return _generate_fallback_content(topic, slide_title, user_draft)


async def _call_gemini_api(
    topic: str,
    slide_title: str,
    user_draft: Optional[str],
    api_key: str
) -> Optional[Dict[str, Any]]:
    """Google Gemini API orqali ilmiy matn generatsiya qilish."""
    # Gemini 1.5 Flash yoki 2.0 Flash
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    prompt = f"""
Siz talabalar uchun akademik taqdimotlar yozuvchi ilmiy mutaxassissiz.
Mavzu: {topic}
Slayd sarlavhasi: {slide_title}
Foydalanuvchi kiritgan qoralama (agar bo'lsa): {user_draft or "Yo'q, noldan yozing"}

Vazifa: O'zbek tilida (lotin yozuvida) ushbu slayd uchun kamida 80-120 so'zdan iborat professional, aniq va ma'lumotli matn yozing.
Tarkib talablari:
1. intro: 1 ta tushunarli kirish jumlasi (10-15 so'z).
2. bullets: 5-6 ta mazmunli punkt. Har bir punkt 1-2 ta to'liq jumlali tushuntirishdan iborat bo'lsin (har biri 15-20 so'z).
3. conclusion: 1 ta xulosa jumlasi (10-15 so'z).

Faqat va faqat quyidagi toza JSON formatida javob bering, hech qanday markdown teglari (```json) qo'shmang:
{{
  "intro": "...",
  "bullets": [
    "...",
    "...",
    "...",
    "...",
    "...",
    "..."
  ],
  "conclusion": "..."
}}
"""

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 800
        }
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        res = await client.post(endpoint, json=payload)
        if res.status_code == 200:
            data = res.json()
            candidates = data.get("candidates", [])
            if candidates:
                raw_text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                # Markdown tozalash
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                if raw_text.startswith("```"):
                    raw_text = raw_text[3:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                raw_text = raw_text.strip()
                return json.loads(raw_text)

    return None


def _generate_fallback_content(topic: str, slide_title: str, user_draft: Optional[str] = None) -> Dict[str, Any]:
    """
    Internet yoki API kalit bo'lmaganda ham har bir slayd uchun 80-120 so'zli
    yuqori darajadagi akademik matnni kafolatlaydi.
    """
    clean_title = slide_title.lower()

    if "kirish" in clean_title:
        intro = f"{topic} mavzusi zamonaviy ilm-fan va amaliyotning eng dolzarb hamda jadal rivojlanayotgan yo'nalishlaridan biri hisoblanadi."
        bullets = [
            f"Mazkur tadqiqotning bosh maqsadi {topic} sohasidagi fundamental tamoyillar va amaliy mexanizmlarni tizimli o'rganishdan iborat.",
            "Bugungi kunda ushbu soha barcha tarmoqlarga keng integratsiyalashib, yangi imkoniyatlar va innovatsion istiqbollarni ochmoqda.",
            "Tadqiqot doirasida zamonaviy metodologiyalar, so'nggi ilmiy yutuqlar hamda ilg'or xalqaro tajribalar har tomonlama tahlil qilinadi.",
            "Mavzuni chuqur o'rganish talabalarga nazariy bilimlarni mustahkamlash bilan birga amaliy ko'nikmalarni rivojlantirishga xizmat qiladi.",
            "Ushbu taqdimotda sohaning nazariy asoslari, amaliy qo'llanilishi hamda mavjud muammolarning samarali yechimlari ketma-ket yoritiladi."
        ]
        conclusion = "Mavzuning dolzarbligi uni har tomonlama ilmiy va amaliy jihatdan tadqiq etish zaruratini yaqqol ko'rsatmoqda."

    elif "tushuncha" in clean_title or "nazariy" in clean_title:
        intro = f"{topic} sohasini to'g'ri tushunish uchun uning tayanch ilmiy atamalari va konseptual qoidalarini aniq belgilab olish talab etiladi."
        bullets = [
            f"Asosiy tushunchalar tizimi {topic}ning mohiyati, ichki tuzilishi va qonuniyatlarini ilmiy asosda ifodalab beradi.",
            "Sohadagi xalqaro standartlar va tasdiqlangan ilmiy modellar barcha tahlillar va xulosalar uchun poydevor vazifasini o'taydi.",
            "Nazariy konsepsiyalar jarayonlarning mantiqiy ketma-ketligini hamda tizim elementlari o'rtasidagi o'zaro uzviy bog'liqlikni aks ettiradi.",
            "Amaliyotda qo'llaniladigan barcha samarali usullar ushbu fundamental nazariy qoidalarga tayanib ishlab chiqiladi va takomillashtiriladi.",
            "Konseptual yondashuv murakkab tizimlarni sodda va tushunarli modellar yordamida chuqur tahlil qilish imkonini yaratadi."
        ]
        conclusion = "Nazariy bilimlarning mustahkamligi amaliyotdagi har qanday murakkab masalani muvaffaqiyatli hal qilish garovidir."

    elif "tarix" in clean_title or "bosqich" in clean_title:
        intro = f"{topic} yo'nalishining shakllanishi va taraqqiyoti bir necha muhim tarixiy bosqichlarni bosib o'tgan qiziqarli jarayondir."
        bullets = [
            "Dastlabki bosqichlarda sohaning ilk g'oyalari va dastlabki tajribaviy modellari ilmiy jamoatchilik tomonidan ilgari surilgan.",
            "Keyingi taraqqiyot davrida texnologik inqiloblar va yangi kashfiyotlar tufayli sohada keskin sifat o'zgarishlari ro'y berdi.",
            "Zamonaviy bosqich esa raqamlashtirish, global integratsiya hamda sun'iy innovatsiyalarning keng joriy etilishi bilan xarakterlanadi.",
            "Tarixiy tajribani o'rganish o'tmishdagi kamchiliklardan to'g'ri saboq chiqarish va kelajakdagi xatolarning oldini olishga yordam beradi.",
            "O'tgan davr mobaynida to'plangan boy ilmiy meros bugungi yutuqlarimizning asosiy manbasi bo'lib xizmat qilmoqda."
        ]
        conclusion = "Tarixiy rivojlanish jarayonini bilish kelajak istiqbollarini aniq prognoz qilishda muhim omil hisoblanadi."

    elif "tur" in clean_title or "tasnif" in clean_title:
        intro = f"{topic} tizimi o'zining ko'p qirraliligi, keng qamrovi va funksional vazifalariga ko'ra bir nechta asosiy turlarga ajratiladi."
        bullets = [
            "Birinchi toifaga kiruvchi turlar o'zining soddaligi, keng tarqalganligi va universal qo'llanilishi bilan ajralib turadi.",
            "Ikkinchi toifadagi ixtisoslashtirilgan turlar esa yuqori aniqlik, maxsus resurslar va chuqur texnik bilimlarni talab qiladi.",
            "Har bir turning o'ziga xos ishlash prinsiplari, afzalliklari, foydalanish chegaralari va maqsadli auditoriyasi mavjud.",
            "Tasniflash jarayoni murakkab vazifalarni to'g'ri guruhlash hamda har bir holat uchun eng mos vositani tanlash imkonini beradi.",
            "Turli toifalarning o'zaro integratsiyasi esa amaliyotda yanada yuqori natijadorlik va moslashuvchanlikni ta'minlaydi."
        ]
        conclusion = "To'g'ri tanlangan tur va toifa qo'yilgan vazifalarni eng kam xarajat bilan samarali bajarishga olib keladi."

    elif "qo'llanil" in clean_title or "amaliyot" in clean_title:
        intro = f"{topic} bugungi kunda ishlab chiqarish, ta'lim, fan, iqtisodiyot va kundalik hayotning barcha jabhalarida faol qo'llanilmoqda."
        bullets = [
            "Amaliyotda ushbu vosita inson mehnatini yengillashtirish, mehnat unumdorligini oshirish va jarayonlarni avtomatlashtirishda qo'llaniladi.",
            "Biznes va iqtisodiy sohalarda xarajatlarni qisqartirish, resurslardan oqilona foydalanish va daromadni oshirishda yuqori samara beradi.",
            "Ta'lim va ilmiy tadqiqotlarda esa katta hajmdagi ma'lumotlarni tezkor tahlil qilish va yangi natijalarga erishishni tezlashtiradi.",
            "Har bir soha o'zining ehtiyojlariga moslashtirilgan maxsus amaliy mexanizmlarni ishlab chiqish orqali raqobatbardoshligini oshirmoqda.",
            "Ilg'or xalqaro korxonalar tajribasi ushbu sohani amaliyotga keng joriy etish yuqori iqtisodiy o'sish keltirishini isbotlamoqda."
        ]
        conclusion = "Amaliy tatbiqning kengligi ushbu sohaning jamiyat taraqqiyotidagi beqiyos o'rnini to'liq namoyon qiladi."

    elif "afzallik" in clean_title or "kamchilik" in clean_title or "muammo" in clean_title:
        intro = f"{topic} sohasining yuksak imkoniyatlari bilan bir qatorda yechilishi zarur bo'lgan bir qator dolzarb muammo va kamchiliklari ham mavjud."
        bullets = [
            "Asosiy afzalliklarga yuqori tezlik, aniqlik, xatolarning kamligi hamda resurslarni sezilarli darajada tejash imkoniyati kiradi.",
            "Shu bilan birga, texnologik infratuzilmaning qimmatligi va malakali kadrlarning yetishmasligi muayyan to'siqlarni yuzaga keltirmoqda.",
            "Xavfsizlik, axborot himoyasi va ma'lumotlarning ishonchliligi kabi muhim omillar doimiy monitoring va nazoratni talab qiladi.",
            "Mavjud kamchiliklarni bartaraf etish uchun kompleks chora-tadbirlar hamda yangi innovatsion standartlarni joriy etish zarur.",
            "Ijobiy va salbiy jihatlarning chuqur qiyosiy tahlili oqilona va muvozanatli boshqaruv qarorlarini qabul qilishga asos bo'ladi."
        ]
        conclusion = "Muammolarni o'z vaqtida aniqlash va bartaraf etish sohaning barqaror va xavfsiz rivojlanishiga zamin yaratadi."

    elif "istiqbol" in clean_title or "kelajak" in clean_title:
        intro = f"{topic} kelgusi yillarda insoniyat taraqqiyotini belgilab beruvchi eng asosiy texnologik drayverlardan biri bo'lishi kutilmoqda."
        bullets = [
            "Kelajakda ushbu sohada to'liq avtomatlashgan, sun'iy aqlga asoslangan aqlli tizimlar yanada mukammal bosqichga ko'tariladi.",
            "Yangi texnologiyalar inson hayotining barcha sohalariga chuqur kirib borib, an'anaviy kasblar va jarayonlarni tubdan o'zgartiradi.",
            "Xalqaro miqyosda ilmiy hamkorlik, ochiq manbalar va global standartlarning rivojlanishi soha taraqqiyotini yanada tezlashtiradi.",
            "Ekologik toza va barqaror resurslardan foydalanishga qaratilgan yangi ilmiy izlanishlar jadallik bilan davom etadi.",
            "O'zbekistonda ham yosh mutaxassislarni tayyorlash hamda ushbu sohaga investitsiyalarni jalb etish bo'yicha keng ko'lamli ishlar olib borilmoqda."
        ]
        conclusion = "Kelajak istiqbollariga tayyor turish yangi davr imkoniyatlaridan maksimal darajada unumli foydalanish imkonini beradi."

    elif "xulosa" in clean_title:
        intro = f"{topic} mavzusi bo'yicha olib borilgan tizimli tahlil va izlanishlar asosida quyidagi muhim ilmiy-amaliy xulosalarga kelindi."
        bullets = [
            f"O'rganishlar shuni ko'rsatdiki, {topic} sohasini rivojlantirish barcha tarmoqlar samaradorligini oshirishda hal qiluvchi rol o'ynaydi.",
            "Nazariy qoidalar va amaliy tajribaning uyg'unligi qo'yilgan maqsadlarga eng qisqa vaqt ichida erishish imkoniyatini ta'minlaydi.",
            "Sohada uchrayotgan mavjud muammolarni zamonaviy texnologik yechimlar va tizimli chora-tadbirlar orqali bartaraf etish mumkin.",
            "Kadrlar malakasini oshirish va innovatsion tashabbuslarni qo'llab-quvvatlash sohaning barqaror rivoji uchun eng muhim shartdir.",
            "Taqdimotda ilgari surilgan amaliy takliflar va tavsiyalar amaliyotga tatbiq etilsa, yuqori ijobiy natijalarga erishish kafolatlanadi."
        ]
        conclusion = "Ushbu izlanishlar kelgusidagi chuqurroq ilmiy tadqiqotlar uchun mustahkam poydevor bo'lib xizmat qiladi."

    elif "adabiyot" in clean_title:
        intro = f"{topic} mavzusini har tomonlama, xolis va ilmiy asosda yoritishda quyidagi asosiy adabiyotlar va manbalardan foydalanildi."
        bullets = [
            "O'zbekiston Respublikasining sohaga oid amaldagi qonunlari, davlat qarorlari va rasmiy me'yoriy-huquqiy hujjatlari to'plami.",
            f"Yetakchi mahalliy va xorijiy olimlarning {topic} muammolariga bag'ishlangan fundamental ilmiy monografiyalari hamda darsliklari.",
            "Xalqaro nufuzli ilmiy jurnallarda (Scopus, Web of Science) chop etilgan eng so'nggi tadqiqot natijalari va maqolalari.",
            "Oliy ta'lim muassasalarining sohaviy kafedralari tomonidan tavsiya etilgan zamonaviy o'quv-uslubiy qo'llanmalar.",
            "Yetakchi ilmiy markazlar va xalqaro tashkilotlarning rasmiy statistik axborotnomalari hamda elektron axborot-ta'lim portallari."
        ]
        conclusion = "Foydalanilgan manbalar taqdimotdagi ma'lumotlarning ishonchliligi, xolisligi va yuqori ilmiy saviyasini ta'minlaydi."

    else:
        # Umumiy tahliliy slayd
        intro = f"{slide_title} masalasi {topic} doirasida alohida diqqat va chuqur ilmiy e'tibor qaratilishi lozim bo'lgan asosiy jihatdir."
        bullets = [
            f"Mazkur yo'nalish doirasida {topic}ning o'ziga xos xususiyatlari, o'rganish usullari va ko'rsatkichlari batafsil tahlil qilindi.",
            "Sohadagi mavjud tendensiyalar va amaliy kuzatuvlar jarayonlarning doimiy yangilanib, takomillashib borayotganini ko'rsatmoqda.",
            "Ilg'or xorijiy tajribalar va innovatsion yondashuvlarni o'rganish eng maqbul samaradorlik ko'rsatkichlariga erishish imkonini beradi.",
            "Tizim faoliyatini monitoring qilish hamda sifat ko'rsatkichlarini doimiy yaxshilash eng muhim amaliy vazifalardan biridir.",
            "Ushbu masalani to'g'ri hal etish butun tizimning barqaror, xavfsiz va samarali ishlashini to'liq kafolatlaydi."
        ]
        conclusion = "Ushbu yo'nalishdagi izlanishlar sohaning amaliy samaradorligini sezilarli darajada oshirishga xizmat qiladi."

    # Agar foydalanuvchi qisqa matn kiritgan bo'lsa, uni birinchi bulletga boyitib joylaymiz
    if user_draft and len(user_draft.strip()) > 3:
        bullets.insert(0, f"Foydalanuvchi ta'kidlagan asosiy fikr: {user_draft.strip()}. Bu tushuncha sohaning amaliy taraqqiyotida muhim poydevor hisoblanadi.")
        if len(bullets) > 6:
            bullets = bullets[:6]

    return {
        "intro": intro,
        "bullets": bullets,
        "conclusion": conclusion
    }
