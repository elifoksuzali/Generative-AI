import google.generativeai as genai
import time
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s.%(msecs)02d - %(levelname)s - %(message)s")
from openai import OpenAI
# Configure the API key


def retry_with_backoff(func):
    
    def wrapper(*args, **kwargs):
        max_retries = 3
        base_delay = 40  # Base delay in seconds
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if "429" in str(e) and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    logging.warning(f"Rate limit hit, waiting {delay} seconds before retry...")
                    time.sleep(delay)
                    continue
                raise
    return wrapper


# ============================================================
# ESKİ FORMAT FONKSİYONLARI (tuple: start, end, text)
# ============================================================

@retry_with_backoff
def ollama_speaker_analysis_prompt(chunks, speaker_prompt, ollama_client):
    """
    ESKİ FORMAT - (start, end, text) tuple listesi için speaker analizi.
    """
    all_analysis_results = []
    for chunk in chunks:
        prompt = speaker_prompt 
        for start, end, text in chunk:
            prompt += f"Start: {start}, End: {end}, Text: {text}\n"
        try:
            response = ollama_client.chat.completions.create(
                model="gpt-oss:20b",
                messages=[{"role": "user", "content": prompt}]
            )
            analysis_result = response.choices[0].message.content
            all_analysis_results.append(analysis_result)
        except Exception as e:
            logging.error(f"Beklenmeyen Hatalar meydana geldi : {e}")
            return None
    final_analysis_result = '\n'.join(all_analysis_results)
    return final_analysis_result







@retry_with_backoff
def ollama_transcript_summary_prompt(chunks, summary_prompt, ollama_client):
    """
    ESKİ FORMAT - Sadece text listesi için özet.
    """
    all_summary_results = []
    
    for chunk in chunks:
        prompt_summary = summary_prompt 

        for text in chunk:
            prompt_summary += f"Text: {text}\n"

        try:
            response = ollama_client.chat.completions.create(
                model="gpt-oss:20b",
                messages=[{"role": "user", "content": prompt_summary}]
            )
            analysis_result = response.choices[0].message.content
            all_summary_results.append(analysis_result)

        except Exception as e:
            logging.error(f"Beklenmeyen Hatalar meydana geldi : {e}")
            return None

    final_summary_result = '\n'.join(all_summary_results)
    return final_summary_result


# ============================================================
# YENİ FORMAT FONKSİYONLARI (dict: {"start", "end", "speaker", "text"})
# ============================================================

@retry_with_backoff
def ollama_diarized_summary_prompt(chunks, summary_prompt, ollama_client):
    """
    YENİ FORMAT - Diarization'lı veri için özet.
    
    Input chunks: [[{"start": 3.22, "end": 5.32, "speaker": "SPEAKER_00", "text": "..."}]]
    
    Kullanım:
        from whisper import prepare_diarized_chunks_for_llm
        chunks = prepare_diarized_chunks_for_llm(transcription)
        result = ollama_diarized_summary_prompt(chunks, "Bu görüşmeyi özetle:", client)
    """
    all_summary_results = []
    
    for chunk in chunks:
        prompt_summary = summary_prompt + "\n\n"
        
        for segment in chunk:
            prompt_summary += f"{segment['speaker']}: {segment['text']}\n"

        try:
            response = ollama_client.chat.completions.create(
                model="gpt-oss:20b",
                messages=[{"role": "user", "content": prompt_summary}]
            )
            analysis_result = response.choices[0].message.content
            all_summary_results.append(analysis_result)

        except Exception as e:
            logging.error(f"Beklenmeyen Hatalar meydana geldi : {e}")
            return None

    final_summary_result = '\n'.join(all_summary_results)
    return final_summary_result


@retry_with_backoff
def ollama_diarized_analysis_prompt(chunks, analysis_prompt, ollama_client):
    """
    YENİ FORMAT - Diarization'lı veri için detaylı analiz (zaman bilgisiyle).
    
    Input chunks: [[{"start": 3.22, "end": 5.32, "speaker": "SPEAKER_00", "text": "..."}]]
    
    Kullanım:
        from whisper import prepare_diarized_chunks_for_llm
        chunks = prepare_diarized_chunks_for_llm(transcription)
        result = ollama_diarized_analysis_prompt(chunks, "Bu görüşmeyi analiz et:", client)
    """
    all_analysis_results = []
    
    for chunk in chunks:
        prompt = analysis_prompt + "\n\n"
        
        for segment in chunk:
            prompt += f"[{segment['start']:.2f}-{segment['end']:.2f}] {segment['speaker']}: {segment['text']}\n"

        try:
            response = ollama_client.chat.completions.create(
                model="gpt-oss:20b",
                messages=[{"role": "user", "content": prompt}]
            )
            analysis_result = response.choices[0].message.content
            all_analysis_results.append(analysis_result)

        except Exception as e:
            logging.error(f"Beklenmeyen Hatalar meydana geldi : {e}")
            return None

    final_analysis_result = '\n'.join(all_analysis_results)
    return final_analysis_result
