import os
import subprocess
import math
import tempfile
import logging
import time
from flask import Flask, request, jsonify
from faster_whisper import WhisperModel
import torch
# hisper code
app = Flask(__name__)

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")
model = WhisperModel("deepdml/faster-whisper-large-v3-turbo-ct2", device=device)

# region Filtreli Verileri MP3 Formatında İndirme
def download_and_convert_audio(file, temp_dir):
    mp3_path = os.path.join(temp_dir, f"recording_{file.filename}_.mp3")
    
    # Dosyayı geçici dizine kaydet
    file.save(mp3_path)
    
    # Dosyanın formatını ekrana bas
    file_format = mp3_path.split('.')[-1]
    print(f"İndirilen Dosyanın Formatı: {file_format}")
    return mp3_path

# endregion

# Ses kayıtlarını segmentlere bölme
def segment_audio(mp3_path, temp_dir):
    max_bytes = 26214400  # Whisper file size limit (25 MB)
    overlap_seconds = 5

    bit_rate = float(subprocess.check_output(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=bit_rate", "-of",
        "default=noprint_wrappers=1:nokey=1", mp3_path]).strip())

    chunk_duration_s = (max_bytes * 8.0) / bit_rate * 0.9

    audio_duration_s = float(subprocess.check_output(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of",
        "default=noprint_wrappers=1:nokey=1", mp3_path]).strip())

    num_chunks = math.ceil(audio_duration_s / (chunk_duration_s - overlap_seconds))

    transcriptions = []
    
    # Segmentleme işlemi ve chunk dosyalarının oluşturulması
    for j in range(num_chunks):
        start_s = j * (chunk_duration_s - overlap_seconds)
        chunk_file = os.path.join(temp_dir, f"temp_chunk_{j}.mp3")

        subprocess.call([
            "ffmpeg", "-ss", str(start_s), "-i", mp3_path, "-t",
            str(chunk_duration_s), "-vn", "-acodec", "libmp3lame", "-y",
            chunk_file
        ])
        transcriptions.append(chunk_file)
        print(f"Chunk {j + 1} oluşturuldu: {chunk_file}")

    return transcriptions

# Whisper transkripsiyon işlemi
def whisper_transcribe_chunk(chunk_file):
    try:
        transcriptions = []

        with open(chunk_file, "rb") as file:
            segments, _ = model.transcribe(file)

            for segment in segments:
                text = segment.text
                transcriptions.append(text)

    except Exception as err:
        logging.error(f"Genel Hata: {err}")
        time.sleep(60)  # Genel hata durumunda 60 saniye bekle
        return whisper_transcribe_chunk(chunk_file)  # Tekrar denemek için fonksiyonu çağır

    return transcriptions

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Geçici dizin oluştur
    with tempfile.TemporaryDirectory() as temp_dir:
        # Dosyayı indir ve formatını kontrol et
        mp3_file_path = download_and_convert_audio(file, temp_dir)

        # Formatını dönüştürüp ekran bas
        print(f"Dosya MP3 formatına dönüştürülüyor...")

        # Segmentlere ayır
        chunk_files = segment_audio(mp3_file_path, temp_dir)

        all_transcription = []

        # Her chunk dosyasını transkripte et
        for chunk_file in chunk_files:
            transcript_file = whisper_transcribe_chunk(chunk_file)
            all_transcription.extend(transcript_file)

        # Tüm transkriptleri tek bir paragraf haline getirme
        final_paragraph = " ".join(all_transcription)

        # Sonuçları döndür
        print(f"Tüm chunk'lar işlendi ve transkripsiyon tamamlandı.")
        
        # Sonuçları döndür
        return jsonify({'message': 'File successfully uploaded, converted to MP3, segmented, transcribed, and cleaned up',
                        'transcription': final_paragraph})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
