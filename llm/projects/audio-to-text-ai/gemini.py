import google.generativeai as genai
import time
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s.%(msecs)02d - %(levelname)s - %(message)s")
from database.db import get_gpt_api_key, create_connection, prompts
# Configure the API key

db = create_connection()
cursor = db.cursor()


gemini_key = get_gpt_api_key(cursor)[0]  # Get first record from the results


genai.configure(api_key=gemini_key)

# Set up the model configuration
generation_config = {
    "temperature": 0.9,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
}

safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH", 
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    }
]
prompt_gemini = prompts(cursor)

# Prompt'ları ayrı değişkenlere atama
summary_prompt = prompt_gemini[1][1]  # summary_gpt_prompt metni
speaker_prompt = prompt_gemini[2][1]  # speaker_gpt_prompt metni



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

@retry_with_backoff
def speaker_analysis_prompt(chunks):
    all_analysis_results = []
    model = genai.GenerativeModel('gemini-2.0-flash',
                                generation_config=generation_config,
                                safety_settings=safety_settings)
    
    for chunk in chunks:
        prompt = speaker_prompt 

        for start, end, text in chunk:
            prompt += f"Start: {start}, End: {end}, Text: {text}\n"

        try:
            response = model.generate_content(prompt)
            analysis_result = response.text
            all_analysis_results.append(analysis_result)

        except Exception as e:
            logging.error(f"Beklenmeyen Hatalar meydana geldi : {e}")
            return None

    final_analysis_result = '\n'.join(all_analysis_results)
    return final_analysis_result

@retry_with_backoff
def transcript_summary_prompt(chunks):
    all_summary_results = []
    model = genai.GenerativeModel('gemini-2.0-flash',
                                generation_config=generation_config,
                                safety_settings=safety_settings)
    
    for chunk in chunks:
        prompt_summary =   summary_prompt 

        for text in chunk:
            prompt_summary += f"Text: {text}\n"

        try:
            response = model.generate_content(prompt_summary)
            summary_result = response.text
            all_summary_results.append(summary_result)

        except Exception as e:
            logging.error(f"Beklenmeyen Hatalar meydana geldi : {e}")
            return None

    final_summary_result = '\n'.join(all_summary_results)
    return final_summary_result




