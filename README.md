# 📊 Talabalar Uchun Slayd (PowerPoint) Tayyorlovchi Telegram Bot

Ushbu Telegram bot talabalar uchun professional darajadagi **PowerPoint (.pptx)** taqdimotlarini tez, oson va yuqori sifatda tayyorlab beradi.

Botning asosiy afzalligi — **to'liq soddalashtirilgan interfeys**: barcha bosqichlar qadamma-qadam inline tugmalar orqali boshqariladi, foydalanuvchiga murakkab buyruqlarni o'rganish talab etilmaydi!

---

## ✨ Asosiy Yangilanishlar va Imkoniyatlar

1. **🖼 Muvozanatli Slaydlar (Yarim Rasm + Matn va Faqat Matn):**
   - Taqdimotdagi slaydlar tartibli almashadi: **bitta slaydda faqat matn (2 ta ustunli tahlil), ikkinchisida yarmida rasm va yarmida matn**.
   - 10 ta slayddan iborat taqdimotda **roppa-rosa 5 ta tematik rasm** bo'ladi.
   - Rasmlarni botning o'zi Pillow orqali yuqori sifatli (1200x900) ilmiy infografika, diagramma va modellar ko'rinishida noldan generatsiya qiladi.
   - Slaydlarda matn va rasm o'rni navbatma-navbat almashib, taqdimotga jonli vizual dinamika beradi.

2. **📝 Boyitilgan Matn (80–120 so'z):**
   - Har bir slaydda kamida 80–120 so'zdan iborat to'liq ilmiy matn: **1 ta kirish jumla + 5–6 ta batafsil bullet punkt (har biri 1–2 jumla) + 1 ta xulosa jumlasi**.
   - Avtomatik to'ldirish rejimida matnlar Google Gemini API yoki boyitilgan akademik generator orqali noldan yuqori ilmiy saviyada yoziladi.
   - Foydalanuvchi qisqa matn kiritgan taqdirda ham, tizim uni avtomatik boyitib, to'liq shaklga keltiradi.
   - Matn slayddan chiqib ketmasligi uchun shrift o'lchami avtomatik optimallashtiriladi.

3. **🏛 Qat'iy "Times New Roman" Shrifti:**
   - Butun taqdimot (titul sahifa, sarlavhalar, matnlar, xulosalar, footerlar) **Times New Roman** shriftida bo'lishi OpenXML darajasida (`a:latin`, `a:ea`, `a:cs`) kafolatlangan.
   - Istalgan kompyuter yoki telefonda ochilganda ham shrift buzilmaydi.
   - Sarlavhalar 32–36pt (qalin), asosiy matn 14–16pt.

4. **🎨 8 xil Mashhur PowerPoint Dizayn Shablonlari:**
   - 🏛 **Ion (Klassik):** Oq fon, to'q ko'k sarlavhalar va safir ko'k aksent.
   - 💎 **Facet (Zamonaviy):** To'q ko'k gradient fon, moviy va oq kristall aksentlar.
   - 🌿 **Savon (Zumrad):** Nafis zumrad va yalpiz rangli organik tabiat shabloni.
   - 👑 **Madison (Qizil-Oltin):** To'q yoqut, fil suyagi va zarhal oltin aksentlar.
   - ⚪ **Atlas (Minimal):** Ultra-toza Shveysariya uslubi, nozik korall aksent.
   - 🌙 **Celestial (Tungi Neon):** Obsidian qora fon, neon indigo va kiber texno aksentlar.
   - 💼 **Retrospect (Biznes):** Korporativ po'lat kulrang va firuza aksentli biznes shablon.
   - ☀️ **Studio (Ijodiy):** Iliq qahva, terrakotta va kahrabo uyg'unligi.

5. **⚡ Jonli Progress Xabari:**
   - Slaydlar generatsiya qilinayotganda Telegramda jonli foiz va holat xabari yangilanib turadi (`10% -> 40% -> 70% -> 100%`).
   - Asinxron arxitektura tufayli bot hech qachon qotib qolmaydi.

---

## 📂 Loyiha Tuzilishi

```text
ZEPTO BOT/
├── main.py              # Botni ishga tushiruvchi asosiy modul (python-telegram-bot v20+)
├── handlers.py          # Barcha bosqichlar, ConversationHandler va jonli progress
├── slide_builder.py     # 16:9 formatdagi PPTX dvigateli (muvozanatli slaydlar, Times New Roman)
├── image_service.py     # 100% mustaqil yuqori sifatli (1200x900) ilmiy infografika generatori
├── ai_service.py        # Gemini API va akademik matn boyitish generatori (80-120 so'z)
├── themes.py            # 8 ta PowerPoint shablonlari sozlamalari va katalog generatori
├── requirements.txt     # Python kutubxonalari ro'yxati
├── .env.example         # Muhit sozlamalari namunasi
├── .env                 # Bot tokeni va API kalitlar
├── README.md            # To'liq qo'llanma
└── assets/              # Rasmlar va kesh papkasi
    ├── previews/        # Dizayn namunalari va katalogi
    └── temp/            # Vaqtinchalik rasmlar va generatsiya qilingan fayllar
```

---

## 🛠 O'rnatish va Ishga Tushirish (Qadamma-qadam)

### 1-Qadam: Kutubxonalarni o'rnatish
Terminal yoki PowerShell orqali loyiha papkasiga kiring:
```bash
pip install -r requirements.txt
```

### 2-Qadam: API kalitlarni sozlash (`.env`)
`.env` faylini oching:
```env
BOT_TOKEN=8642464907:AAGT6JQnBSz-xuedgEATkDMdIgWsrq9EHCc
PEXELS_API_KEY=
GEMINI_API_KEY=
```

#### API kalitlarni qayerdan olish mumkin?
1. **BOT_TOKEN:** [@BotFather](https://t.me/BotFather) orqali olinadi.
2. **PEXELS_API_KEY (Rasmlar uchun):**
   - [pexels.com/api](https://www.pexels.com/api/) saytiga kiring.
   - Bepul ro'yxatdan o'tib, darhol shaxsiy API kalitingizni oling.
   - *Eslatma: Agar Pexels kaliti kiritilmasa, bot avtomatik ravishda Wikimedia Commons bepul kutubxonasidan yoki dizaynga mos chiroyli grafik placeholder kartalaridan foydalanadi (bot to'xtab qolmaydi).*
3. **GEMINI_API_KEY (AI matn boyitish uchun):**
   - [aistudio.google.com](https://aistudio.google.com/) saytiga kiring.
   - Google hisobingiz bilan kirib, "Get API Key" tugmasi orqali bepul kalit yarating.
   - *Eslatma: Agar Gemini kaliti kiritilmasa, botning o'zidagi mukammal akademik fallback generatori har bir slayd uchun 80-120 so'zli matnni noldan tuzib beradi.*

### 3-Qadam: Botni ishga tushirish
Quyidagi buyruqni bering:
```bash
python main.py
```

Terminalda quyidagi yozuv paydo bo'lsa, bot faol holatda ishlamoqda:
```text
INFO - Bot muvaffaqiyatli ishga tushdi va xabarlarni qabul qilmoqda!
```

---

## 🚀 24/7 Rejimda Ishlatish Qo'llanmasi

Botni 24/7 to'xtovsiz ishlatish uchun 2 ta qulay usul tayyorlangan:

### 1-Usul: O'z kompyuteringizda 24/7 fonda ishlatish (Windows)
Loyiha papkasida tayyor boshqaruv fayllari yaratildi:
- **`start_background.vbs`** — Botni hech qanday qora konsol oynasisiz, butunlay fonda ishga tushiradi.
- **`run_bot.bat`** — Konsol oynasida ko'rib turib ishlatish (bot to'xtab qolsa avtomatik qayta ishga tushadi).
- **`status_bot.bat`** — Bot hozir ishlayaptimi yoki yo'qligini, xotira sarfini va oxirgi loglarni tekshirish.
- **`stop_bot.bat`** — Fondagi botni to'xtatish.
- **`install_autostart.bat`** — **Kompyuter yoqilishi bilan bot avtomatik ishga tushadigan qilib sozlash.** (Bir marta bosasiz va unutasiz).
- **`uninstall_autostart.bat`** — Avtomatik ishga tushirishni bekor qilish.

### 2-Usul: Bepul Bulutda (Cloud - Render.com) 24/7 ishlatish
Agar kompyuterni o'chirib qo'yganingizda ham bot 24/7 ishlashini xohlasangiz:
1. Loyihani GitHub-ga shaxsiy (private) ombor sifatida yuklang.
2. [Render.com](https://render.com) saytiga kiring va bepul ro'yxatdan o'ting.
3. **"New +" -> "Background Worker"** tugmasini bosing.
4. GitHub omboringizni tanlang.
5. Sozlamalarga:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
6. **Environment Variables** bo'limida:
   - `BOT_TOKEN`: Sizning bot tokeningiz
7. **"Create Work"** tugmasini bosing. Bot endi bulutda 24/7 to'xtovsiz ishlaydi!

---

## 📱 Botdan Foydalanish

1. Telegramda [@ZeptoSlaydBot](https://t.me/ZeptoSlaydBot) ga kiring va `/start` bosing.
2. **«📊 Yangi taqdimot yaratish»** tugmasini bosing.
3. 8 xil PowerPoint dizayn kartasidan birini tanlang.
4. Universitet logotipini yuboring (yoki *«📁 Standart logotipdan foydalanish»* / *«⏩ O'tkazib yuborish»* bosing).
5. Ism va familiyangizni, guruhingizni, universitet nomi va mavzuni kiriting.
6. Slaydlar sonini (5, 8, 10, 15) tanlang.
7. **«⚡ Avtomatik to'ldirish»** usulini tanlang.
8. Bot jonli progress foizini ko'rsatib, matnli va yarim-rasmli muvozanatli slaydlardan iborat, Times New Roman matnlari va avtomatik yaratilgan ilmiy infografikalar bilan tayyor `.pptx` faylni yuboradi!
