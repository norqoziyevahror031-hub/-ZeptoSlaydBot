FROM python:3.11-slim

# Tizim paketlari
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-liberation \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Talab etiladigan paketlar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Loyiha fayllarini nusxalash
COPY . .

# Botni ishga tushirish
CMD ["python", "main.py"]
