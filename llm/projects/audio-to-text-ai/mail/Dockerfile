# Temiz ve hafif bir Python tabanlı image
FROM python:3.11-slim


# Sistem bağımlılıkları (yalnızca gerekli olanlar)
RUN apt-get update && apt-get install -y \
    build-essential \
    default-libmysqlclient-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Çalışma dizini
WORKDIR /app

# Gereksinimleri yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyaları
COPY . .

# Uygulama başlangıcı
CMD ["python", "ollama_mail.py"]

# 4242 portunu expose ediyoruz
EXPOSE 4242
