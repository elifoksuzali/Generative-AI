# region 13 Kasım Kod Değiştirilmedne önceki halidir
import os
import subprocess
import math
import tempfile
import logging
import time
import requests
import gc
from threading import Lock
from flask import Flask, request, jsonify
from urllib.parse import urlparse
from faster_whisper import WhisperModel
import torch
# hisper
# === Speaker Diarization için - PYANNOTE ===
import numpy as np
if not hasattr(np, "bool"):
    np.bool = np.bool_

from pyannote.audio import Pipeline
# ==========================================

# Logging
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)

# GPU kontrolü
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# Whisper model (faster-whisper) - Türkçe için en iyi model
model = WhisperModel(
    "large-v3",  # En iyi kalite için large-v3
    device=device,
    compute_type="float16"
)

# Pyannote Diarization Pipeline (GPU üzerinde)
print("[INIT] Loading Pyannote diarization pipeline...")
diarization_pipeline = Pipeline.from_pretrained(
    "pyannote/speaker-diarization-3.1",
    use_auth_token=True  # ~/.cache/huggingface/token kullanır
)
diarization_pipeline.to(torch.device(device))
print(f"[INIT] Pyannote loaded on {device}")

# İstekleri sıraya almak için Lock (CUDA out of memory önleme)
processing_lock = Lock()


def cleanup_gpu_memory():
    """GPU belleğini temizler - her istek sonunda çağrılmalı"""
    if device == "cuda":
        torch.cuda.empty_cache()
        gc.collect()
        print("[GPU] Memory cleaned")

# ==================================================
# 1) DİARİZASYON YARDIMCI FONKSİYONLARI (PYANNOTE)
# ==================================================

def run_speaker_diarization(audio_path, n_speakers=2, min_speakers=2, max_speakers=2):
    """
    Pyannote ile GPU üzerinde speaker diarization yapar.
    
    Args:
        audio_path: Ses dosyası yolu
        n_speakers: Konuşmacı sayısı (varsayılan 2 - temsilci ve müşteri)
        min_speakers: Minimum konuşmacı sayısı
        max_speakers: Maksimum konuşmacı sayısı
    
    Telefon görüşmeleri için varsayılan 2 speaker:
        - SPEAKER_00: Temsilci
        - SPEAKER_01: Müşteri
    """
    print(f"[DIAR] Running diarization on {device}: {audio_path} (n_speakers={n_speakers})")
    
    # Konuşmacı sayısı belirtilmişse kullan
    diarization = diarization_pipeline(
        audio_path,
        num_speakers=n_speakers
    )
    
    segments = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append({
            "start": turn.start,
            "end": turn.end,
            "speaker": speaker
        })
    
    # Konuşmacı istatistikleri
    unique_speakers = set(seg["speaker"] for seg in segments)
    print(f"[DIAR] Found {len(segments)} segments, {len(unique_speakers)} speakers: {unique_speakers}")
    
    return segments


def merge_short_segments(diar_segments, min_duration=0.5):
    """
    Çok kısa segmentleri bir önceki veya sonraki segment ile birleştirir.
    Bu, speaker geçişlerindeki tutarsızlıkları azaltır.
    """
    if not diar_segments:
        return diar_segments
    
    merged = []
    for seg in diar_segments:
        duration = seg["end"] - seg["start"]
        
        if duration < min_duration and merged:
            # Çok kısa segment - önceki segment ile birleştir
            merged[-1]["end"] = seg["end"]
        else:
            merged.append(seg.copy())
    
    return merged


def smooth_speaker_transitions(result, min_gap=1.0):
    """
    Aynı speaker'ın kısa aralıklarla tekrar konuştuğu durumları düzeltir.
    Örn: A -> B -> A (B çok kısa) -> A olarak birleştirilir.
    """
    if len(result) < 3:
        return result
    
    smoothed = [result[0]]
    
    for i in range(1, len(result) - 1):
        prev_seg = smoothed[-1]
        curr_seg = result[i]
        next_seg = result[i + 1]
        
        # Eğer önceki ve sonraki aynı speaker ise ve mevcut segment kısa ise
        curr_duration = curr_seg["end"] - curr_seg["start"]
        
        if (prev_seg["speaker"] == next_seg["speaker"] and 
            curr_duration < min_gap and
            prev_seg["speaker"] != curr_seg["speaker"]):
            # Mevcut segmenti önceki speaker'a ata
            curr_seg = curr_seg.copy()
            curr_seg["speaker"] = prev_seg["speaker"]
        
        smoothed.append(curr_seg)
    
    # Son segmenti ekle
    if len(result) > 1:
        smoothed.append(result[-1])
    
    return smoothed


def calculate_overlap(seg_start, seg_end, diar_start, diar_end):
    """
    İki zaman aralığının örtüşme miktarını hesaplar.
    """
    overlap_start = max(seg_start, diar_start)
    overlap_end = min(seg_end, diar_end)
    overlap = max(0, overlap_end - overlap_start)
    return overlap


def format_speaker_label(speaker):
    """
    SPEAKER_00 -> Speaker 1, SPEAKER_01 -> Speaker 2 formatına dönüştürür.
    """
    if speaker and speaker.startswith("SPEAKER_"):
        # SPEAKER_00 -> 00 -> 0 -> 1, SPEAKER_01 -> 01 -> 1 -> 2
        number = int(speaker.replace("SPEAKER_", "").lstrip("0") or "0") + 1
        return f"Speaker {number}"
    return speaker


def assign_speakers_to_segments(audio_path, whisper_segments, n_speakers=None):
    """
    Whisper segmentlerini pyannote diarization ile eşleştirir.
    
    Gelişmiş eşleştirme:
    1. Kısa diarization segmentlerini birleştir
    2. En çok örtüşen speaker'ı bul
    3. Örtüşme yoksa en yakın speaker'ı bul
    4. Speaker geçişlerini düzelt
    """
    if not whisper_segments:
        return []
    
    diar_segments = run_speaker_diarization(audio_path, n_speakers)
    
    if not diar_segments:
        print("[DIAR] Warning: No diarization segments found!")
        return [{
            "start": float(start),
            "end": float(end),
            "speaker": "Speaker 1",  # 0 yerine 1
            "text": text
        } for (start, end, text) in whisper_segments]
    
    # Kısa segmentleri birleştir (gürültü azaltma)
    diar_segments = merge_short_segments(diar_segments, min_duration=0.3)
    print(f"[DIAR] After merging short segments: {len(diar_segments)} segments")
    
    result = []
    last_speaker = None
    
    for (start, end, text) in whisper_segments:
        best_speaker = None
        best_overlap = 0
        
        # 1. En çok örtüşen speaker'ı bul
        for seg in diar_segments:
            overlap = calculate_overlap(start, end, seg["start"], seg["end"])
            if overlap > best_overlap:
                best_overlap = overlap
                best_speaker = seg["speaker"]
        
        # 2. Örtüşme yoksa, orta noktaya en yakın speaker'ı bul
        if best_speaker is None:
            mid_t = (start + end) / 2.0
            min_distance = float('inf')
            
            for seg in diar_segments:
                # Segment'in orta noktasına uzaklık
                seg_mid = (seg["start"] + seg["end"]) / 2.0
                distance = abs(mid_t - seg_mid)
                
                if distance < min_distance:
                    min_distance = distance
                    best_speaker = seg["speaker"]
        
        # 3. Hala bulunamadıysa, önceki speaker'ı kullan
        if best_speaker is None:
            best_speaker = last_speaker if last_speaker else "SPEAKER_00"
        
        last_speaker = best_speaker
        
        result.append({
            "start": float(start),
            "end": float(end),
            "speaker": format_speaker_label(best_speaker),
            "text": text
        })
    
    # Speaker geçişlerini düzelt (A -> B -> A gibi kısa geçişleri temizle)
    result = smooth_speaker_transitions(result, min_gap=1.5)
    
    # İstatistikler
    unique_speakers = set(r["speaker"] for r in result)
    print(f"[DIAR] Final result: {len(result)} segments, {len(unique_speakers)} unique speakers")
    
    return result

# ==================================================
# 2) LOCAL UPLOAD: Dosyayı geçici klasöre kaydet
# ==================================================

def download_and_convert_audio(file, temp_dir):
    mp3_path = os.path.join(temp_dir, f"recording_{file.filename}_.mp3")

    file.save(mp3_path)

    file_format = mp3_path.split('.')[-1]
    print(f"İndirilen Dosyanın Formatı: {file_format}")
    return mp3_path

# ==================================================
# 3) Netgsm / Container: Audio İndirme
# ==================================================

def download_and_convert_audio_container(recording_url, uniqueid, index, temp_dir):
    # Şema yoksa ekle
    if not recording_url.startswith("http://") and not recording_url.startswith("https://"):
        recording_url = "http://" + recording_url

    mp3_path = os.path.join(temp_dir, f"recordings/recording_{uniqueid}_{index}_.mp3")

    os.makedirs(os.path.dirname(mp3_path), exist_ok=True)

    print(f"[DOWNLOAD] Requesting: {recording_url}")

    try:
        audio_response = requests.get(recording_url, timeout=15)

        content_type = audio_response.headers.get("Content-Type", "").lower()
        print("[DOWNLOAD] Content-Type:", content_type)

        if "audio" not in content_type:
            print("[ERROR] URL audio döndürmüyor!")
            print("[ERROR] Sunucu ilk 200 byte:", audio_response.content[:200])
            return None

        with open(mp3_path, "wb") as audio_file:
            audio_file.write(audio_response.content)

        print("[DOWNLOAD] File saved:", mp3_path)
        print("[DOWNLOAD] File size:", os.path.getsize(mp3_path))

    except Exception as e:
        print("[DOWNLOAD ERROR]", e)
        return None

    return mp3_path

# ==================================================
# 4) ffprobe helper + Ses kayıtlarını segmentlere bölme
# ==================================================

def safe_ffprobe_value(cmd, default=None):
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).strip()
        return float(out)
    except Exception:
        return default


def segment_audio(mp3_path, temp_dir):
    max_bytes = 26214400  # 25 MB
    overlap_seconds = 5

    bit_rate = safe_ffprobe_value(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=bit_rate",
         "-of", "default=noprint_wrappers=1:nokey=1", mp3_path],
        default=128000  # fallback
    )

    audio_duration_s = safe_ffprobe_value(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", mp3_path],
        default=0
    )

    if audio_duration_s <= 0:
        print("[ERROR] Audio duration = 0. Geçersiz dosya.")
        return []

    print(f"[SEGMENT] Duration: {audio_duration_s:.2f} sec, bitrate: {bit_rate}")

    chunk_duration_s = (max_bytes * 8.0) / bit_rate * 0.9
    num_chunks = math.ceil(audio_duration_s / (chunk_duration_s - overlap_seconds))

    chunks = []

    for j in range(num_chunks):
        start_s = j * (chunk_duration_s - overlap_seconds)
        chunk_file = os.path.join(temp_dir, f"temp_chunk_{j}.mp3")

        subprocess.call([
            "ffmpeg", "-ss", str(start_s), "-i", mp3_path, "-t",
            str(chunk_duration_s), "-vn", "-acodec", "libmp3lame", "-y",
            chunk_file
        ], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

        chunks.append((chunk_file, start_s))
        print(f"[SEGMENT] Chunk {j+1}: {chunk_file} (offset={start_s:.2f})")

    return chunks

# ==================================================
# 5) Whisper transkripsiyon işlemleri
# ==================================================

def whisper_transcribe_chunk(chunk_file):
    """
    Sadece text döndürür - Türkçe optimizasyonlu.
    """
    try:
        transcriptions = []
        with open(chunk_file, "rb") as file:
            segments, _ = model.transcribe(
                file,
                language="tr",  # Türkçe dil belirtme
                beam_size=5,
                vad_filter=True
            )
            for segment in segments:
                transcriptions.append(segment.text)
    except Exception as err:
        logging.error(f"Genel Hata: {err}")
        time.sleep(60)
        return whisper_transcribe_chunk(chunk_file)
    return transcriptions


def whisper_transcribe_chunk_container(chunk_file, chunk_offset=0.0):
    """
    Her chunk için start/end + text döner,
    start/end değerleri GLOBAL zamana göre (chunk_offset eklenmiş).
    
    Türkçe için optimize edilmiş parametreler:
    - language="tr": Türkçe dil modeli
    - condition_on_previous_text=True: Bağlam kullanarak daha tutarlı çeviri
    - vad_parameters: Sessizlik ve gürültü filtresi
    """
    try:
        transcriptions = []

        with open(chunk_file, "rb") as file:
            segments, _ = model.transcribe(
                file,
                language="tr",  # TÜRKÇE - Daha doğru kelime algılama
                beam_size=5,
                condition_on_previous_text=True,  # Bağlam kullan - daha tutarlı cümleler
                word_timestamps=True,
                vad_filter=True,
                vad_parameters=dict(
                    min_silence_duration_ms=500,   # 500ms sessizlik = segment ayır
                    speech_pad_ms=400,             # Konuşma etrafına 400ms padding
                    threshold=0.5                   # Ses algılama eşiği (0.3-0.7 arası)
                )
            )

            for segment in segments:
                start_time = chunk_offset + segment.start
                end_time = chunk_offset + segment.end
                text = segment.text.strip()  # Baştaki/sondaki boşlukları temizle
                if text:  # Boş segmentleri atla
                    transcriptions.append((start_time, end_time, text))

    except Exception as err:
        logging.error(f"Genel Hata: {err}")
        time.sleep(120)
        return whisper_transcribe_chunk_container(chunk_file, chunk_offset)

    return transcriptions

# ==================================================
# 6) Container'dan Gelen Veriyi İşleme ve Geri Gönderme
# ==================================================

@app.route('/receive_data', methods=['POST'])
def receive_data_from_container():
    """
    Container'dan gelen ses dosyasını işler.
    Lock ile sıraya alınır - aynı anda sadece 1 istek işlenir (CUDA OOM önleme).
    """
    # Lock ile sıraya al - aynı anda sadece 1 istek işlensin
    with processing_lock:
        try:
            data = request.get_json()
            uniqueid = data.get('uniqueid')
            urls = data.get('url')
            index = data.get('i')
            # Konuşmacı sayısı (varsayılan 2 - temsilci ve müşteri)
            n_speakers = data.get('n_speakers', 2)

            with tempfile.TemporaryDirectory() as temp_dir:

                mp3_path = download_and_convert_audio_container(urls, uniqueid, index, temp_dir)

                if not mp3_path:
                    logging.error("MP3 file path is invalid, returning error response.")
                    return jsonify({'error': 'Failed to download or process the audio file.'}), 400

                logging.info(f"Ses kaydı {mp3_path} olarak indirildi ve kaydedildi")

                chunk_files = segment_audio(mp3_path, temp_dir)
                if not chunk_files:
                    return jsonify({'error': 'Failed to segment the audio.'}), 500

                all_segments = []  # (global_start, global_end, text)
                for chunk_file, chunk_offset in chunk_files:
                    segs = whisper_transcribe_chunk_container(chunk_file, chunk_offset)
                    all_segments.extend(segs)

                logging.info(f"Received data: uniqueid={uniqueid}, urls={urls}")

                # Varsayılan 2 speaker: Temsilci ve Müşteri
                diarized = assign_speakers_to_segments(mp3_path, all_segments, n_speakers=n_speakers)

                return jsonify({
                    'received_uniqueid': uniqueid,
                    'received_urls': urls,
                    'transcription': diarized  # [{start, end, speaker, text}, ...]
                })
        finally:
            # GPU belleğini temizle
            cleanup_gpu_memory()

# ==================================================
# 7) /upload endpoint'i — SPEAKER + TEXT döner
# ==================================================

@app.route('/upload', methods=['GET', 'POST'])
def upload_file():
    """
    Dosya yükleyerek transkripsiyon ve diarization yapar.
    Lock ile sıraya alınır - aynı anda sadece 1 istek işlenir (CUDA OOM önleme).
    """
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    # Konuşmacı sayısı (varsayılan 2 - temsilci ve müşteri)
    n_speakers = request.form.get('n_speakers') or request.args.get('n_speakers')
    n_speakers = int(n_speakers) if n_speakers else 2  # Varsayılan 2 speaker

    # Lock ile sıraya al - aynı anda sadece 1 istek işlensin
    with processing_lock:
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                mp3_file_path = download_and_convert_audio(file, temp_dir)

                print(f"Dosya MP3 formatına dönüştürülüyor...")

                chunk_files = segment_audio(mp3_file_path, temp_dir)
                if not chunk_files:
                    return jsonify({'error': 'Failed to segment the audio.'}), 500

                all_segments = []  # (global_start, global_end, text)
                for chunk_file, chunk_offset in chunk_files:
                    segs = whisper_transcribe_chunk_container(chunk_file, chunk_offset)
                    all_segments.extend(segs)

                # Varsayılan 2 speaker: Temsilci ve Müşteri
                diarized = assign_speakers_to_segments(mp3_file_path, all_segments, n_speakers=n_speakers)

                print(f"Tüm chunk'lar işlendi, transkripsiyon + diarization tamamlandı.")

                return jsonify({
                    'message': 'File successfully uploaded, converted to MP3, segmented, transcribed, diarized and cleaned up',
                    'transcription': diarized
                })
        finally:
            # GPU belleğini temizle
            cleanup_gpu_memory()

# ==================================================
# 8) APP RUN
# ==================================================

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4141, debug=False, use_reloader=False)

# endregion
