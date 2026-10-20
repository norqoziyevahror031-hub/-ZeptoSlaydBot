# 📊 Talabalar Uchun Slayd (PowerPoint) Tayyorlovchi Telegram Bot

Ushbu Telegram bot talabalar uchun professional darajadagi **PowerPoint (.pptx)** taqdimotlarini tez, oson va yuqori sifatda tayyorlab beradi.

Botning asosiy afzalligi — **to'liq soddalashtirilgan interfeys**: barcha bosqichlar qadamma-qadam inline tugmalar orqali boshqariladi, foydalanuvchiga murakkab buyruqlarni o'rganish talab etilmaydi!

---

## ✨ Asosiy Yangilanishlar va Imkoniyatlar

1. **🖼 Har bir slaydda 4 tadan mavzuga oid rasm (2x2 Setka):**
   - Titul varoqdan tashqari barcha slaydlar 2 qismga ajratilgan: bir yarmi matn, ikkinchi yarmi **4 ta rasm** (2x2 setka ko'rinishida).
   - Rasmlar sarlavha va mavzuga mos ravishda Pexels API yoki Wikimedia bepul manbalaridan avtomatik topilib, proporsiyasi buzilmagan holda markazdan kesiladi (`center-crop`).
   - Dizayn go'zalligi uchun slaydlar navbatma-navbat almashadi: **toq slaydlarda matn chapda, juft slaydlarda o'ngda**.
   - Rasmlar atrofida dizayn aksent rangida chiroyli hoshiya va ramka mavjud.

2. **📝 Boyitilgan Matn (80–120 so'z):**
   - Har bir slaydda kamida 80–120 so'zdan iborat to'liq ilmiy matn: **1 ta kirish jumla + 5–6 ta batafsil bullet punkt (har biri 1–2 jumla) + 1 ta xulosa jumlasi**.
   - Avtomatik to'ldirish rejimida matnlar Google Gemini API yoki boyitilgan akademik generator orqali noldan yuqori ilmiy saviyada yoziladi.
   - Foydalanuvchi qisqa matn kiritgan taqdirda ham, tizim uni avtomatik boyitib, to'liq shaklga keltiradi.
   - Matn slayddan chiqib ketmasligi uchun shrift o'lchami avtomatik optimallashtiriladi.

3. **🏛 Qat'iy "Times New Roman" Shrifti:**
   - Butun taqdimot (titul sahifa, sarlavhalar, matnlar, xulosalar, footerlar) **Times New Roman** shriftida bo'lishi OpenXML darajasida (`a:latin`, `a:ea`, `a:cs`) kafolatlangan.
   - Istalgan kompyuter yoki telefonda ochilganda ham shrift buzilmaydi.
   - Sarlavhalar 32–36pt (qalin), asosiy matn 14–16pt.

4. **🎨 6 xil Eksklyuziv Dizayn:**
   - 🏛 **Klassik:** Oq fon, to'q ko'k sarlavhalar va rasmiy akademik uslub.
   - 💎 **Zamonaviy:** To'q ko'k gradient fon, oppoq va moviy yorug' matnlar.
   - ⚪ **Minimal:** Och kulrang toza fon, qora matn va nozik zamonaviy chiziqlar.
   - 🌿 **Yashil tabiat:** Yumshoq yalpiz va zumrad yashil uyg'unligi.
   - 👑 **Qizil-oltin:** Rasmiy tantanali uslub, qizil va zarhal oltin aksentlar.
   - 🌙 **Qorong'i rejim:** Chuqur qora fon, neon-ko'k kiber aksentlar.

5. **⚡ Jonli Progress Xabari:**
   - Slaydlar generatsiya qilinayotganda Telegramda jonli foiz va holat xabari yangilanib turadi (`10% -> 40% -> 70% -> 100%`).
   - Asinxron arxitektura tufayli bot hech qachon qotib qolmaydi.

---

## 📂 Loyiha Tuzilishi

```text
ZEPTO BOT/
├── main.py              # Botni ishga tushiruvchi asosiy modul (python-telegram-bot v20+)
├── handlers.py          # Barcha bosqichlar, ConversationHandler va jonli progress
├── slide_builder.py     # 16:9 formatdagi PPTX dvigateli (2x2 setka, Times New Roman)
├── image_service.py     # Pexels API va Wikimedia orqali 4 ta rasm topish va crop qilish
├── ai_service.py        # Gemini API va akademik matn boyitish generatori (80-120 so'z)
├── themes.py            # 6 ta dizayn sozlamalari va Pillow preview generatori
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

## 📱 Botdan Foydalanish

1. Telegramda [@ZeptoSlaydBot](https://t.me/ZeptoSlaydBot) ga kiring va `/start` bosing.
2. **«📊 Yangi taqdimot yaratish»** tugmasini bosing.
3. 6 xil dizayn kartasidan birini tanlang.
4. Universitet logotipini yuboring (yoki *«📁 Standart logotipdan foydalanish»* / *«⏩ O'tkazib yuborish»* bosing).
5. Ism va familiyangizni, guruhingizni, universitet nomi va mavzuni kiriting.
6. Slaydlar sonini (5, 8, 10, 15) tanlang.
7. **«⚡ Avtomatik to'ldirish»** usulini tanlang.
8. Bot jonli progress foizini ko'rsatib, har bir slaydga 4 tadan rasm joylashtirib, 80-120 so'zli Times New Roman matnlari bilan tayyor `.pptx` faylni yuboradi!
