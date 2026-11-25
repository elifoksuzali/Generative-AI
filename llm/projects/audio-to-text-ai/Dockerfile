# Base image
FROM python:3.11-slim

# Çalışma dizinini belirlet.
WORKDIR /app


# Sistem bağımlılıklarını yükle
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    libsndfile1 \
    build-essential \
    libasound2-dev \
    ffmpeg \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# pip'i güncelle ve gerekli araçları yükle
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Bağımlılık dosyasını kopyala
COPY requirements.txt .

# Bağımlılıkları yükle
RUN pip install --no-cache-dir -r requirements.txt

# Tüm proje dosyalarını kopyala
COPY . .

# Çalışma izinlerini ayarla
RUN chmod +x /app/whisper.py

# Konteyner çalıştırıldığında hangi komutun çalıştırılacağını belirle
CMD ["python", "whisper.py"]
