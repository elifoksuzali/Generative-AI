# NVIDIA CUDA Docker imajını kullanıyoruz
FROM nvidia/cuda:12.4.0-runtime-ubuntu22.04

# Çalışma dizini ayarlaması yapılmıştır
WORKDIR /app
# hisper
# Sistem güncellemesi ve gerekli paketlerin kurulumu
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    python3-setuptools \
    ffmpeg \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
ENV VIRTUAL_ENV=/env 
RUN python3 -m venv ${VIRTUAL_ENV}
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6
RUN which ffprobe && ffprobe -version


# requirements.txt dosyasını kopyala ve bağımlılıkları kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# Flask uygulamasını çalıştırmak için komut
CMD ["python3", "enes.py"]

# 6161 portunu expose et
EXPOSE 4141
