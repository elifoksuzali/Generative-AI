# region Eski Kod

# import requests
# import openai
# import mysql.connector
# from datetime import datetime
# import os
# import subprocess
# import time
# import math


# # Şu anki zamanı stopdate olarak al
# stopdate = datetime.now()

# # OpenAI API anahtarı
# openai.api_key = 'sk-REPLACE_WITH_YOUR_OPENAI_KEY'

# # MYSQL BAĞLANTI BİLGİLERİ
# db = mysql.connector.connect(
#     host="db.example.com",
#     user="fake_db_user",
#     password="FAKE_DB_PASSWORD",
#     database="fake_db_name",
#     consume_results=True
# )
# cursor = db.cursor()


# while True:

#     # Ayarlar tablosundan son işleme tarihini (startdate) al
#     cursor.execute("SELECT deger FROM ayarlar WHERE anahtar = 'cagriaisonkontrol'")
#     result = cursor.fetchone()

#     # Eğer bir tarih varsa startdate olarak kullan, yoksa hata ver
#     if result and result[0]:
#         startdate = datetime.strptime(result[0].strip(), "%Y-%m-%d %H:%M:%S")
#         print(startdate)
#     else:
#         raise ValueError("Veritabanında 'startdate' bulunamadı!")

        
#     # Netgsm API URL ve başlık bilgileri
#     url = "https://api.netgsm.com.tr/netsantral/report"
#     headers = {
#         "Content-Type": "application/json"
#     }
#     # JSON verisi
#     json_data = {
#         "usercode": "0000000000",
#         "password": "FAKE_NETGSM_PASSWORD",
#         "startdate": startdate.strftime("%d%m%Y%H%M%S"),
#         "stopdate": stopdate.strftime("%d%m%Y%H%M%S")
#     }
#     # POST isteği gönderimi
#     response = requests.post(url, headers=headers, json=json_data)
#     # API'den başarılı cevap alındığında
#     if response.status_code == 200:
#         data = response.json()
#         print(data)
        
#         # Eğer API yanıtı 'error' içeriyorsa, hata mesajı ver ve işlemi durdur
#         if 'error' in data:
#             print("Kayıt yok. Hata mesajı:", data['error'])
#             raise SystemExit("Sistem durduruldu.")
        
        
#         total_records = len(data)  # Toplam kayıt sayısını al
#         processed_records = 0  # İşlenen kayıt sayısını tut
#         last_processed_date = None  # Son işlenen kaydın tarihini tutacak değişken
#         if total_records > 0:
#             # Her kayıt için işlemler
#             for entry in reversed(data):
#                 time.sleep(5)  # Her istek sonrası 1 dakika bekleyin
#                 uniqueid = entry.get('uniqueid')
#                 print(f"Şu anda işlem yapılan URL (uniqueid): {uniqueid}")
                
#                 for i, value in enumerate(entry.get('values', [])):
#                     # destination kontrolünü yapalım
#                     destination = value.get('destination')
#                     if "0000000000-announcement-OgleArasi" in destination or "0000000000-announcement-mesaidisi" in destination:
#                         print(f"{i}. Kayıt atlandı: {destination}")
#                         continue # Eğer bu şart sağlanıyorsa o kaydı atla
#                     if value.get('recording') and value.get('direction') in [0, 1,4]:
#                         uniqueid = entry.get('uniqueid')
#                         date = value.get('date')
#                         # API'den gelen tarih datetime çevir
#                         data_obj = datetime.strptime(date.strip(), "%d.%m.%Y %H:%M:%S")
#                         # Veri tabanına uygun formata date çevir
#                         format_date = data_obj.strftime("%Y-%m-%d %H:%M:%S")
#                         source = value.get('source')
#                         duration = value.get('duration')
#                         direction = value.get('direction')
#                         direction_text = 'GIDEN' if direction == 0 else 'GELEN' if direction == 1 else 'ICARAMA'
#                         recording_url = value.get('recording')  # Kayıt URL'sini al
#                         # Ses kaydını indir
#                         audio_response = requests.get(recording_url)
#                         audio_path = f"recordings/recording_{i}.wav"
#                         os.makedirs('recordings', exist_ok=True)
#                         with open(audio_path, "wb") as audio_file:
#                             audio_file.write(audio_response.content)
#                         print(f"{i}. Ses kaydı indirildi ve '{audio_path}' olarak kaydedildi.")
#                         time.sleep(5)  # Gereksiz yüklenmeyi önlemek için kısa bir gecikme
#                         # WAV dosyasını MP3'e dönüştür
#                         mp3_path = f"recordings/recording_{i}.mp3"
#                         subprocess.call(["ffmpeg", "-i", audio_path, "-acodec", "libmp3lame", "-y", mp3_path])
#                         print(f"{i}. Ses kaydı MP3 formatına dönüştürüldü: {mp3_path}")
                        
#                         # wav halini sil
#                         os.remove(audio_path)  # WAV dosyasını sil
#                         # MP3 dosyasını işleme
#                         max_bytes = 26214400  # Whisper dosya boyutu sınırı (25 MB)
#                         overlap_seconds = 5
#                         # MP3 dosyasının bit hızı ve süresini al
#                         bit_rate = float(subprocess.check_output(
#                             ["ffprobe", "-v", "quiet", "-show_entries", "format=bit_rate", "-of",
#                             "default=noprint_wrappers=1:nokey=1", mp3_path]).strip())
#                         chunk_duration_s = (max_bytes * 8.0) / bit_rate * 0.9
#                         audio_duration_s = float(subprocess.check_output(
#                             ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of",
#                             "default=noprint_wrappers=1:nokey=1", mp3_path]).strip())
#                         num_chunks = math.ceil(audio_duration_s / (chunk_duration_s - overlap_seconds))
#                         transcriptions = []  # Chunk başına transkripsiyon için
                    
#                         whisper_cost_per_minute = 0.006  # Whisper için dakikada 0.006 USD (örnek)
#                         chatgpt_cost_per_prompt = 0.0015  # ChatGPT için her istek başına 0.0015 USD (örnek)
#                         # Toplam maliyet değişkeni
#                         whisper_cost = 0
#                         chatgpt_cost = 0
#                         for j in range(num_chunks):
#                             start_s = j * (chunk_duration_s - overlap_seconds)
#                             chunk_file = f"recordings/temp_chunk_{i}_{j}.mp3"  # Geçici chunk dosyası
#                             # ffmpeg ile chunk çıkarma
#                             subprocess.call([
#                                 "ffmpeg", "-ss", str(start_s), "-i", mp3_path, "-t",
#                                 str(chunk_duration_s), "-vn", "-acodec", "libmp3lame", "-y",
#                                 chunk_file
#                             ])
#                             print(f"{i}. Chunk {j + 1} oluşturuldu.")
#                             os.remove(mp3_path)  # MP3 dosyasını sil
#                             # Chunk'ı Whisper ile transkribe et
#                             with open(chunk_file, "rb") as file:
#                                 transcription = openai.Audio.transcribe(
#                                     file=file,
#                                     model="whisper-1",
#                                     response_format="verbose_json",
#                                     timestamp_granularities=["segment", "word"]
#                                 )
#                                 for segment in transcription['segments']:
#                                     start_time = segment['start']
#                                     end_time = segment['end']
#                                     text = segment['text']
#                                     transcriptions.append((start_time, end_time, text))
#                             os.remove(chunk_file)  # Chunk dosyasını sil
#                         # ChatCompletion ile konuşmaları ayrıştır
#                         prompt = (
#                             "Lütfen aşağıdaki konuşmaları analiz ederek konuşmacıları ayrıştırın. "
#                             "'Speaker 1' genellikle telefon yanıtlayan operatör olabilir ve 'Speaker 2' müşteri veya arayan kişi olabilir. "
#                             "Ayrıca, konuşmaları belirli bir formatta düzenleyin: "
#                             "Speaker X: Start: <start>, End: <end>, Text: <text>. "
#                             "Transkript verisi:\n"
#                         )
#                         for start, end, text in transcriptions:
#                             prompt += f"Start: {start}, End: {end}, Text: {text}\n"
#                         # ChatCompletion isteği gönder
#                         chat_response = openai.ChatCompletion.create(
#                             model="gpt-4o",
#                             messages=[{"role": "user", "content": prompt}],
#                             temperature=0.8
#                         )
#                         analysis_result = chat_response['choices'][0]['message']['content']
#                         print(f"{i}. ChatCompletion sonucu:\n{analysis_result}")
#                         # ChatCompletion ile Metni Özetle
#                         prompt_summary = (
#                             "Verilen metni kısaca özetle. Metnin ana konusunu, müşteri veya kullanıcıların sorunlarını ve çözüm önerilerini belirt."
#                             "Transkript verisi:\n"
#                         )
#                         for summary in analysis_result:
#                             prompt_summary += f"Text: {summary}\n"
#                         # ChatCompletion isteği gönder
#                         chat_summary_response = openai.ChatCompletion.create(
#                             model="gpt-4o",
#                             messages=[{"role": "user", "content": prompt_summary}],
#                             temperature=0.8
#                         )
#                         summary_result = chat_summary_response['choices'][0]['message']['content']
#                         print(f"{i}. ChatCompletion sonucu:\n{summary_result}")
#                         audio_duration_minutes = audio_duration_s / 60  # Saniye cinsinden süreyi dakikaya çevir
#                         whisper_cost = whisper_cost_per_minute * audio_duration_minutes
#                         chatgpt_cost = chatgpt_cost_per_prompt  # Tek bir istek başına maliyet
#                         toplam_maliyet = whisper_cost + chatgpt_cost
#                         print(f"Whisper maliyeti: ${whisper_cost:.4f}")
#                         print(f"ChatCompletion maliyeti: ${chatgpt_cost:.4f}")
#                         print(f"Bu kayıt için toplam maliyet: ${toplam_maliyet:.4f}")
#                         # Veritabanına transkripti kaydet
#                         insert_query = """
#                             INSERT INTO cagritakip (cagriid, tarih, yon, arayan, aranan, sure, metin,ozet,cost)
#                             VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
#                         """
#                         values = (uniqueid, format_date, direction_text, source, destination, duration, analysis_result,summary_result,toplam_maliyet)
#                         # Her kayda ait bilgileri birleştir
#                         try: 
#                             cursor.execute(insert_query, values)
#                             # Kaytıları Ekle
#                             db.commit()
#                             print("Kayıt veritabanına kaydedildi.")
#                             processed_records += 1  # Başarıyla eklenirse işlenen kaydı artır
#                             last_processed_date = format_date
#                         except mysql.connector.Error as err:
#                             print("Veri tabanına kayıt eklerken sorun yaşandı:",err)
                            
                            
#                         # En son işleme tarihini güncelle
#                         update_query = """
#                             UPDATE ayarlar
#                             SET deger = %s 
#                             WHERE anahtar = 'cagriaisonkontrol'
#                             """
#                         try:
#                             cursor.execute(update_query, (last_processed_date,))
#                             db.commit()  # Güncellemeyi kaydet
#                             print("Ayarlar tablosunda kayıt güncellendi:")
#                         except mysql.connector.Error as err:
#                             print("Ayarlar tablosunu güncellerken hata oluştu:", err)
#             # Toplam ve işlenen kayıtları yazdır
#             print(f"Toplam Kayıt: {total_records}, İşlenen Kayıt: {processed_records}")
#         else:
#             print("API isteği başarısız oldu:", response.status_code)
#         # Bağlantıyı kapat
#         cursor.close()
#         db.close()
#         print("Sistem yeniden çalışması için 10 sn bekletiliyor ")
#         time.sleep(10)


# endregion


# region 10 Ocak 2025 Kodu

# region 1 Kütüphaneler
import time
import requests
from datetime import datetime,timedelta,time as dt_time
import mysql.connector
from mysql.connector import Error
import logging
import os
import subprocess
import openai
import math
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from faster_whisper import WhisperModel
from email.header import Header
import json
# endregion

# region 2 Bağlantı bilgileri
DB_CONFIG = {
    "host": "db.example.com",
    "user": "fake_db_user",
    "password": "FAKE_DB_PASSWORD",
    "database": "fake_db_name"
}
API_CREDENTIALS = {
    "usercode": "0000000000",
    "password": "FAKE_NETGSM_PASSWORD"
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# endregion

# region 3.1 OpenAI API anahtarı
openai.api_key = 'sk-REPLACE_WITH_YOUR_OPENAI_KEY'
# endregion

# region 3.3 Maliyet hesaplaması için gerekli bilgiler
pricing_gpt = {
    "gpt-4o-mini": {
        "input": 0.15,  # Örnek girdi maliyeti
        "cached_input": 0.075, # cahche maliyeti
        "output": 0.60  # Örnek çıktı maliyeti
    }
}
# endregion

# region 3.3 Veri tabanı bağlantısı oluşturma fonksiyonu
def create_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        logging.info("Veri tabanına bağlantı başarılı")
        return connection
    except Error as e:
        logging.error(f"Veri tabanına bağlantı yapılırken hata '{e}' meydana geldi")
        return None
# endregion

# region 4 Api isteği
def fetch_data_from_api(startdate, stopdate):
    """
    API'den veri çeker.
    """
    url = "https://api.netgsm.com.tr/netsantral/report"
    headers = {"Content-Type": "application/json"}
    json_data = {
        "usercode": API_CREDENTIALS["usercode"],
        "password": API_CREDENTIALS["password"],
        "startdate": startdate.strftime("%d%m%Y%H%M%S"),
        "stopdate": stopdate.strftime("%d%m%Y%H%M%S")
    }

    try:
        response = requests.post(url, headers=headers, json=json_data)
        if response.status_code == 200:
            data = response.json()
            return data
        elif response.status_code == 404:
            logging.info(f"Veri bulunamadı:")
            return []
        else:
            logging.error(f"API isteği başarısız oldu. Durum kodu: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Hata oluştu: {e}")
        return None

# endregion

# region 5 Prompt Alanı

system_prompt = """ You are a skilled data summarization and categorization language model.
                Your task is to analyze transcribed data, identify key problems, and organize them into a structured format.
                You should group similar problems under the same category, provide concise summaries, and offer clear solutions.

                ***Instructions***
                1. Analyze the transcribed text to identify the main problems.
                2. Group similar problems under a single title.
                3. Summarize each problem clearly and concisely.
                4. Provide applicable solutions or recommendations based on the problem context.
                5. Highlight how personnel attempted to resolve each issue.

                ***Outputs***
                - Problem Title: Clearly state the main problem or topic derived from the transcription.
                - Content: Provide a concise and clear summary of the transcription content.
                - Solution Proposal: Provide applicable solutions or suggestions, considering the identified problems and context.
                Combine similar content under a title, content, and solution, taking these structures into account.

                ### Response Format:
                
                Ensure that your response follows this step structure:
                Step 1 - Incoming Format Structure:
                    Subject headings, contents and suggested methods are separated.            

                        1. Installation and Connection Problems
                            - Content: Describe complications related to installing a specific application and any connection issues present.
                            - Solution Suggestion: Outline steps for the support team to address installation and connection challenges.

                        2. Customers difficulty connecting to the operator
                            - Content: Customers are seeking support for technical service requests and product information, but they state that they cannot reach a customer representative.
                            - Solution Suggestion: Customers are provided with a support email address, are connected to the operator, and are advised to contact the relevant sales representatives.

                        3. Difficulty connecting to operator
                            - Content: Customers are forced to wait for long periods of time and are unable to submit technical support requests because all representatives are busy.
                            - Solution Suggestion: Informing customers to forward their technical support requests to info@example.com when the lines are busy or cannot be reached.

                Step -2 Example Output Structure:
                    Issues:

                        1. Installation and Connection Problems
                            - Content: Describe complications related to installing a specific application and any connection issues present.
                            - Solution Suggestion: Outline steps for the support team to address installation and connection challenges.

                        2. Operator Connection Problems (We merged the 2nd and 3rd content when there was similar content.)
                            - Content:Customers have to wait for long periods of time and report that they cannot reach any representatives because all of them are busy.
                            - Solution Suggestion: Apologies were made for the inconveniences experienced and our customers were informed to forward their technical support requests to info@example.com when the lines are busy or unreachable.

                ***Attention***
                    Summarize the data in Turkish.
                    Ensure the response is clear, concise, and unambiguous.
                    Include only problems and solutions that are directly relevant to the transcription content.
                    Do not display example outputs to the user.
                    Keep your answers short, direct, and easy to understand.
            """

response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "listing_problems",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "items": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "problem_title": {
                                            "type": "string",
                                            "description": "The main title summarizing the issue."
                                        },
                                        "problem_content": {
                                            "type": "string",
                                            "description": "A brief description of the problem."
                                        },
                                        "solution_suggestion": {
                                            "type": "string",
                                            "description": "The proposed solution to resolve the issue."
                                        }
                                    },
                                    "required": ["problem_title", "problem_content", "solution_suggestion"],
                                    "additionalProperties": False
                                }
                            }
                        },
                        "required": ["items"],
                        "additionalProperties": False
                    }
                }
            }

# endregion

# region 6 Günlük Özet ve SMTP ayarları E-Posta Gönderme Fonksiyon Ayarları Yapıldı
def daily_summary_and_send_email(cursor,system_prompt,response_format):
    try:
        # SMTP ayarları
        smtp_login = "info@example.com"  # SMTP kullanıcı adı
        smtp_password = "FAKE_SMTP_APP_PASSWORD"  # SMTP şifre
        smtp_host = "smtp.yandex.com"  # SMTP sunucusu
        smtp_recipients_email_to = ["agent1@example.com","agent2@example.com","agent3@example.com","agent4@example.com","agent5@example.com","agent6@example.com"]

        logging.info("SMTP ayarları alındı.")
    except Exception as e:
        logging.error(f"SMTP ayarları alınırken hata oluştu: {e}")
        return

    try:
        # Günün tarihini al
        today_date = datetime.now().strftime("%d %m %Y")
        
        # Veritabanından günlük özetleri çekme
        cursor.execute("SELECT ozet FROM cagritakip WHERE DATE(tarih) = CURDATE()")
        summaries = cursor.fetchall()

        if not summaries:
            logging.info("Bugün için özetlenecek kayıt bulunamadı.")
            subject = f'{today_date} Özeti - Veri Yok'
            body = "<p>Bugün için özetlenecek veri bulunamadı.</p>"
        else:
            # Gelen özetleri işleme
            problem_count = {}
            for summary in summaries:
                problem = summary[0]
                if problem in problem_count:
                    problem_count[problem] += 1
                else:
                    problem_count[problem] = 1

            # Özetleme ve birleştirme
            daily_summary = ""
            for problem, count in problem_count.items():
                daily_summary += f"- {problem} ({count} kez tekrarlandı)\n"
            chat_response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": daily_summary}
                ],
                response_format=response_format,  # Şema formatını API'ye ilet
                temperature=0.8
            )
            raw_summary = chat_response['choices'][0]['message']['content']
            response_data = json.loads(raw_summary)
            # Biçimlendirme
            formatted_output = format_response(response_data)

            
            # E-posta için içerik oluşturma
            subject = f'{today_date} Günlük Çağrı Özeti'
            body = f"<p>Sorunlar:</p><p>{formatted_output}</p>"

        # E-posta gönderimi
        msg = MIMEText(body, 'html', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = smtp_login
        msg['To'] = ', '.join(smtp_recipients_email_to)  # Alıcıları virgülle ayırarak ekle


        with smtplib.SMTP(smtp_host, 587, timeout=30) as smtp_server:
            smtp_server.starttls()
            smtp_server.login(smtp_login, smtp_password)
            smtp_server.sendmail(smtp_login, smtp_recipients_email_to, msg.as_string())
            logging.info("Günlük özet e-postası başarıyla gönderildi.")

    except Exception as e:
        logging.error(f"E-posta gönderimi sırasında hata oluştu: {e}")
# endregion

# region Format Daily Response
def format_response(response):
    if "items" not in response:
        return "No items found in the response."

    for i, item in enumerate(response["items"], start=1):
        problem_title = item.get("problem_title", "Başlık Bulunamadı")
        problem_content = item.get("problem_content", "Sorun bilgisi bulunamadı.")
        solution_suggestion = item.get("solution_suggestion", "Çözüm bilgisi bulunamadı.")

        formatted_output = (
            f"<strong>{i} - {problem_title}</strong><br>"
            f"<strong>  Sorun:</strong> {problem_content}<br>"
            f"<strong>  Çözüm Önerisi:</strong> {solution_suggestion}<br><br>"
        )
    return formatted_output
# endregion

# region Şartları Sağlamayan Durumlar için Tarih Iterasyon Fonsk.
def updates_new_date(stopdate):
    """
    This function updates a stop date.
    
    :param stopdate: It looks like you were about to define a function called `updates_new_date` that
    takes a parameter `stopdate`. If you need any help with completing the function or have any specific
    questions, feel free to ask!
    """

    new_startdate = stopdate  # Mevcut stopdate'ı yeni startdate olarak ayarlıyoruz
    new_stopdate = new_startdate + timedelta(minutes=60)
    logging.info(f"Yeni startdate: '{new_startdate}'  ve stopdate: '{new_stopdate}' ")

    return new_startdate # yeni stopdate döndürüyoruz
# endregion

# region 5 Api'den kaynaklı hata kontrolü
def fetch_api_check_data(error_code,error_counter,stopdate):
    if error_code == '30':
        logging.error("Geçersiz Kullanıcı adı veya IP sınırlaması. API ayarlarını kontrol edin veya bilgileri yeniden güncelleyin.")

    elif error_code == '40':
        new_startdate = updates_new_date(stopdate)
        update_last_processed_date(cursor, new_startdate)
        db.commit() # kayıttaki değişikliği kaydettik
        logging.info(f"Yeni servis isteği için startdate: '{new_startdate}' veri tabanında kaydedildi")
        
        
        if error_counter >= 5:
            logging.warning("5 kez sistem error_counter girdi sistem 1 saatlik uyku modunda giriyor")
            update_last_processed_date(cursor, stopdate)
            db.commit() # kayıttaki değişikliği kaydettik
            error_counter = 0 # değeri 0'layalım
            print(f"error_counter: {error_counter}")
            time.sleep(3600)

            return True,error_counter
        return True,error_counter
    
    elif error_code == '70':
        logging.error("Hatalı sorgulama. Gönderdiğiniz parametrelerden birisi hatalı veya zorunlu alanlardan birinin eksik olduğunu ifade eder.")
        return False,error_counter

    elif error_code in ['100', '101']:
        logging.error("Sistem hatası veya sınır aşımı. Bir süre bekleniyor...")
        time.sleep(120)
        return True,error_counter

    else:
        logging.info("Hata kodu yok")
        return False,error_counter
# endregion

# region Son işleme tarihini veritabanından al
def get_startdate(cursor):
    cursor.execute("SELECT deger FROM ayarlar WHERE anahtar = 'cagriaisonkontrol'")
    result = cursor.fetchone()
    if result and result[0]:
        startdate = datetime.strptime(result[0].strip(), "%Y-%m-%d %H:%M:%S")
        # stopdate = datetime.now().replace(microsecond=0)  # Mikro saniyeleri sıfırlayarak sadece tarih ve saat alınır
        stopdate = startdate + timedelta(minutes=60)

        return startdate,stopdate
    else:
        raise ValueError("Veritabanında 'startdate' bulunamadı!")

# endregion

# region 6 Veriyi Kurallara göre filtreleme
def process_records(entry):
    # Önce kayıtları filtreleyelim
    recordings = [
        v for v in entry.get("values", [])
        if v.get("recording") and v.get("destination") not in ["0000000000-announcement-OgleArasi", "0000000000-announcement-mesaidisi"]
        and (int(v.get("duration", 0)) >= 30)
    ]

    # direction değerlerine göre verileri ayıralım
    directions = {0: [], 1: [], 4: []}  # direction'ları 0, 1 ve 4 için kümelere ayıracağız

    for rec in recordings:
        direction = rec.get("direction")
        if direction in directions:
            directions[direction].append(rec)

    # Her direction için en son kaydı alıyoruz (tarihe göre en büyüğü)
    select_recordings = []
    for direction, recs in directions.items():
        if recs:  # Eğer direction kümesinde kayıt varsa
            # En son kaydı seç
            latest_recording = max(recs, key=lambda v: datetime.strptime(v["date"].strip(), "%d.%m.%Y %H:%M:%S"))
            select_recordings.append(latest_recording)

    return select_recordings
# endregion

# region 7 Uniqueid Aynı Kaydı Atla
def check_uniqueid_exits(cursor, uniqueid,format_date, direction):
    try:
        query = "SELECT cagriid, tarih, yon FROM cagritakip WHERE cagriid = %s AND tarih = %s AND yon = %s"

        cursor.execute(query, (uniqueid,format_date, direction,))
        logging.info(f"Veri tabanından uniquied sorgusu başarıyla gerçekleşti")
        result = cursor.fetchall()
        return  result

    except Exception as err:
        logging.error(f"Veri tabanında uniquied id bilgisi sorgulanırken '{err}' hata meydana geldi")
# endregion

# region CagriTaki Santral Uniqueid Kontrol
def check_uniqueid_exits_santral(cursor, uniqueid,format_date_santral, direction_santral):
    try:
        query = "SELECT cagriid, tarih, yon FROM cagritakip_santral WHERE cagriid = %s AND tarih = %s AND yon = %s"
        cursor.execute(query, (uniqueid,format_date_santral, direction_santral,))
        logging.info(f"Veri tabanından uniquied sorgusu başarıyla gerçekleşti")
        result = cursor.fetchall()
        return  result

    except Exception as err:
        logging.error(f"Veri tabanında uniquied id bilgisi sorgulanırken '{err}' hata meydana geldi")

# endregion

# region Filtreli Verileri MP3 Formatında İndirme
def download_and_convert_audio(recording_url, uniqueid, index):
    mp3_path = f"recordings/recording_{uniqueid}_{index}.mp3"
    os.makedirs('recordings', exist_ok=True)

    audio_response = requests.get(recording_url)
    with open(mp3_path, "wb") as audio_file:
        audio_file.write(audio_response.content)

    return mp3_path

# endregion

# region Ses kayıtlarını segmentlere bölme
def segment_audio(mp3_path):
    max_bytes = 26214400  # Whisper file size limit (25 MB)
    overlap_seconds = 5

    # Get the bit rate of the MP3 file
    bit_rate = float(subprocess.check_output(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=bit_rate", "-of",
        "default=noprint_wrappers=1:nokey=1", mp3_path]).strip())

    chunk_duration_s = (max_bytes * 8.0) / bit_rate * 0.9

    # Get the duration of the audio file
    audio_duration_s = float(subprocess.check_output(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of",
        "default=noprint_wrappers=1:nokey=1", mp3_path]).strip())

    num_chunks = math.ceil(audio_duration_s / (chunk_duration_s - overlap_seconds))

    transcriptions = []  # For storing the path of each chunk

    for j in range(num_chunks):
        start_s = j * (chunk_duration_s - overlap_seconds)
        chunk_file = f"recordings/temp_chunk_{j}.mp3"  # Temporary chunk file

        # Extract chunk using ffmpeg
        subprocess.call([
            "ffmpeg", "-ss", str(start_s), "-i", mp3_path, "-t",
            str(chunk_duration_s), "-vn", "-acodec", "libmp3lame", "-y",
            chunk_file
        ])
        transcriptions.append(chunk_file)
        logging.info(f"Chunk {j + 1} oluşturuldu: {chunk_file}")

    return transcriptions
# endregion

# region Whisper Transcription Bölümü
def whisper_transcribe_chunk(chunk_file):
        # region eski whsiper open ai model
        # try:
        #     transcriptions =  []
        #     with open(chunk_file, "rb") as file:
        #         transcription = openai.Audio.transcribe(
        #             file=file,
        #             model="whisper-1",
        #             response_format="verbose_json",
        #             timestamp_granularities=["segment", "word"]
        #             )
        #         # Her bir segment start - end - text çıkarma
        #         for segment in transcription['segments']:
        #             start_time = segment['start']
        #             end_time = segment['end']
        #             text = segment['text']
        #             transcriptions.append((start_time, end_time, text))
        # except openai.error.APIError as e:
        #     logging.error(f"OpenAI API Hatası: {e}")
        #     time.sleep(30)  # API hatası durumunda 30 saniye bekle
        #     return whisper_transcribe_chunk(chunk_file)  # Tekrar denemek için fonksiyonu çağır
        # except Exception  as err:
        #     logging.error(f"Geçersiz Json Yanıtı Hatası: {err}")
        #     time.sleep(30)  # Genel hata durumunda 30 saniye bekle
        #     return whisper_transcribe_chunk(chunk_file)  # Tekrar denemek için fonksiyonu çağır
        # return transcriptions
        # endregion
    try:
        # WhisperModel'ı başlatıyoruz
        model = WhisperModel("deepdml/faster-whisper-large-v3-turbo-ct2")
        transcriptions = []
        # Dosyayı okuma
        with open(chunk_file, "rb") as file:
            # WhisperModel kullanarak transkripsiyon işlemi
            segments, _ = model.transcribe(file)

            # Her bir segment start - end - text çıkarma
            for segment in segments:
                start_time = segment.start
                end_time = segment.end
                text = segment.text
                transcriptions.append((start_time, end_time, text))

    except Exception as err:
        logging.error(f"Genel Hata: {err}")

        time.sleep(120)  # Genel hata durumunda 1dk 15.sn bekle
        return whisper_transcribe_chunk(chunk_file)  # Tekrar denemek için fonksiyonu çağır

    return transcriptions

# endregion

# region Whisper Sonucunu Parça Parça Speaker Analize Yapma
def preapare_chat_chunk_transcriptions(transcription_file):
    max_length=2000
    chunks = []
    current_chunk = []

    # Splitting the transcriptions into chunks
    for start, end, text in transcription_file:
        # Prepare the proposed chunk
        proposed_chunk = current_chunk + [(start, end, text)]
        chunk_length = sum(len(t[2]) for t in proposed_chunk)  # Total length of texts in the chunk

        if chunk_length > max_length:  # If current chunk exceeds the limit
            chunks.append(current_chunk)  # Save the current chunk
            current_chunk = [(start, end, text)]  # Start a new chunk
        else:
            current_chunk.append((start, end, text))  # Add to the current chunk

    # Append any remaining current chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks
# endregion

# region Chat Speaker Prompt
def speaker_analysis(chunks):
    all_analysis_results = []
    chat_response = None  # Açıklama amacıyla buraya ekledik.

    for chunk in chunks:
        # Konuşmacı ayrıştırma prompt'u
        prompt = ("""Please analyze the following conversations to isolate the speakers Always use Turkish language. 
                
                'Speaker 1' would typically be the operator answering the phone and 'Speaker 2' would be the customer or caller. 
                Also, organize the conversations in a specific format: 
                Speaker X: Start: <start>, End: <end>, Text: <text>. 
                Transcript data:\n
                
                 ***Attention***
                Keep responses as concise and to the point as possible and Always use Turkish language"""
        )

        for start, end, text in chunk:
            prompt += f"Start: {start}, End: {end}, Text: {text}\n"
        try:
            # OpenAI ChatCompletion isteği gönderme
            chat_response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                timeout =180
            )
            analysis_result = chat_response['choices'][0]['message']['content']
            all_analysis_results.append(analysis_result)
            logging.info(f"Konuşmacı Analizi Sonucu:\n{analysis_result}")
            
        except openai.error.APIError as err:
            logging.error(f"API hatası alındı {err.http_status}, mesaj :  {str(err)}")
            # Hata 500 ise handle_api_error fonksiyonu çağrılacak
            if err.http_status == 500:
                handle_api_error(err,'speaker_analysis')
                return None, None
        except Exception as e:
            logging.error(f"Beklenmeyen Hatalar meydana geldi : {e} ")

    final_analysis_result = '\n'.join(all_analysis_results)
    return final_analysis_result,chat_response
# endregion

# region Chat Özet Prompt
def transcript_summary(chunks):
    # Özetleme prompt'u
    all_summary_results = []
    chat_summary_response = None
    for chunk in chunks:

        prompt_summary = ("""Briefly summarize the given text. 
                        Indicate the main topic of the text, the problems of the customers or users,
                        and the suggested solutions.
                        
                        ***Attention***
                        "Keep the answers as short and concise as possible and Always use Turkish language
                
                        """
            "Transcript data:\n"
        )
        for start, end, text in chunk:
            prompt_summary += f"Start: {start}, End: {end}, Text: {text}\n"
        try:
            # OpenAI ChatCompletion isteği gönderme
            chat_summary_response = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt_summary}],
                temperature= 0.8,
                timeout = 180
            )
            summary_result = chat_summary_response['choices'][0]['message']['content']
            all_summary_results.append(summary_result)

            logging.info(f"Transkript Özeti:\n{summary_result}")

        except openai.error.APIError as err:
            logging.error(f"API hatası alındı {err.http_status}, mesaj :  {str(err)}")
            # Hata 500 ise handle_api_error fonksiyonu çağrılacak
            if err.http_status == 500:
                handle_api_error(err,'transcript_summary')
                return None, None
            
        except Exception as e:
            logging.error(f"Beklenmeyen Hatalar meydana geldi : {e} ")

    final_summary_result = '\n'.join(all_summary_results)
    return final_summary_result,chat_summary_response
# endregion

# region Maliyet Hesaplama Fonksiyonu
def calculate_costs(chat_response, chat_summary_response, pricing_gpt): #whisper_cost_per_minute, pricing_gpt):

    # Chat Completion Speaker Cost Calculation
    input_tokens = chat_response['usage']['prompt_tokens']
    output_tokens = chat_response['usage']['completion_tokens']
    tokens_cached = chat_response['usage']['prompt_tokens_details']['cached_tokens']


    # Chat Completion Summary Cost Calculation
    input_tokens_sum = chat_summary_response['usage']['prompt_tokens']
    output_tokens_sum = chat_summary_response['usage']['completion_tokens']
    chat_cached__sum = chat_summary_response['usage']['prompt_tokens_details']['cached_tokens']
    logging.info(f"input chat {input_tokens} output chat: {output_tokens} cahche chat: {tokens_cached}")

    logging.info(f"input sum {input_tokens_sum} output aum: {output_tokens_sum} cahche sum: {chat_cached__sum}")

    # Completion Calculate
    input_cost = (input_tokens / 1_000_000) * pricing_gpt["gpt-4o-mini"]["input"]
    cached_cost = (tokens_cached / 1_000_000) * pricing_gpt["gpt-4o-mini"]["cached_input"]
    output_cost = (output_tokens / 1_000_000) * pricing_gpt["gpt-4o-mini"]["output"]

    chatgpt_cost = input_cost + output_cost + cached_cost

    # Chat Completion Summary Cost Calculation

    input_tokens_summary = (input_tokens_sum / 1_000_000) * pricing_gpt["gpt-4o-mini"]["input"]
    cached_summary_cost = (chat_cached__sum / 1_000_000) * pricing_gpt["gpt-4o-mini"]["cached_input"]
    output_cost_summary = (output_tokens_sum / 1_000_000) * pricing_gpt["gpt-4o-mini"]["output"]

    sum_cost = input_tokens_summary + cached_summary_cost + output_cost_summary

    # Total costs
    gpt_cost = chatgpt_cost + sum_cost
    # total_cost = gpt_cost + whisper_cost

    # Log the costs

    logging.info(f"ChatCompletion and Summary maliyeti: ${gpt_cost:.6f}")
    # logging.info(f"Toplam maliyeti: ${total_cost:.6f}")

    return {

        "gpt_cost": gpt_cost

    }
# endregion

# region Veriyi Veri Tabanına kaydet
def save_to_db(cursor, uniqueid, format_date, direction_text, source, destination, duration,final_analysis_result,summary_result,gpt_cost):
    query = """
        INSERT INTO cagritakip (cagriid, tarih, yon, arayan, aranan, sure, metin,ozet,cost)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (uniqueid, format_date, direction_text, source, destination, duration,final_analysis_result,summary_result,gpt_cost)
    cursor.execute(query, values)
# endregion

# region Veriyi Veri Tabanına kaydet
def save_to_db_santral(cursor, uniqueid, format_date,source, destination, direction, duration):
    query = """
        INSERT INTO cagritakip_santral (cagriid, tarih, arayan, aranan, yon, sure)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    values = (uniqueid, format_date,source, destination, direction, duration)
    cursor.execute(query, values)
# endregion

#  region En son işleme tarihini güncelle
def update_last_processed_date(cursor, stopdate_sleep_before):
    query = "UPDATE ayarlar SET deger = %s WHERE anahtar = 'cagriaisonkontrol'"
    cursor.execute(query, (stopdate_sleep_before,))
# endregion

# region Günlük Hata Kontrol E-Posta Gönderme Fonksiyonu
def send_daily_error_mail(subject,body):
    try:
        # SMTP ayarları
        smtp_login = "info@example.com"  # SMTP kullanıcı adı
        smtp_password = "FAKE_SMTP_APP_PASSWORD"  # SMTP şifre
        smtp_host = "smtp.yandex.com"  # SMTP sunucusu
        smtp_recipients_email_to = ["agent1@example.com"]
        logging.info("SMTP ayarları alındı.")
    except Exception as e:
        logging.error(f"SMTP ayarları alınırken hata oluştu: {e}")
        return
    try:
        # Günün tarihini al
        today_date = datetime.now().strftime("%d %m %Y")
        subject =  f'{today_date} --- {subject}'
        # E-posta gönderimi için içerik hazırlama
        msg = MIMEText(body, 'html', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = smtp_login
        msg['To'] = ', '.join(smtp_recipients_email_to)  # Alıcıları virgülle ayırarak ekle
        
        with smtplib.SMTP(smtp_host, 587, timeout=10) as smtp_server:
            smtp_server.starttls()
            smtp_server.login(smtp_login, smtp_password)
            smtp_server.sendmail(smtp_login, smtp_recipients_email_to, msg.as_string())  # Liste olarak gönder
            logging.info("Veri yok e-postası başarıyla gönderildi.")
            
    except Exception  as e:
        logging.error(f"E-posta gönderimi sırasında hata oluştu: {e}")
# endregion 

# region handle_api_error 
def handle_api_error(err, function_name):
    error_message = f"API hatası alındı {err.http_status}, mesaj: {str(err)}"
    logging.error(error_message)
    send_daily_error_mail(f"Meydana gelen hata sonucu konteynırı yeniden başlatın: {function_name}", error_message)
    time.sleep(90)  # 1.5 dakika bekle
    send_daily_error_mail("Sistem Başarıyla Yeniden Başlatıldı", f"{function_name} işlemi 1 dakika bekledikten sonra yeniden çalıştı.")
# endregion 

email_sent_today = False # günlük mail gönderimi kontrol amaçlı işaretçi
error_counter = 0

while True:


    #  Socket timeout 1440 minutes
    db = create_connection()
    if not db:
        logging.error("Veritabanı bağlantısı kurulamadı, program sonlanıyor.")
        continue
    cursor = db.cursor()
    
    startdate,stopdate = get_startdate(cursor)
    logging.info(f"startdate: {startdate} stopdate {stopdate}")

    target_time = dt_time(18, 00) # gerçek saat değeri olarak 10:30 container saat değeri olarak 6:30 sistemden kullanıcıya mail gönderilecek
    current_time = datetime.now().time().replace(microsecond=0)
    current_date = (datetime.now().replace(microsecond=0) + timedelta(hours=3))
    
    logging.info(f"Konteyner Saat Değeri: {current_time}, Gerçek Saat Değeri: {current_date}, Yeni B.Tarih Değeri:{stopdate}")
    
    if current_time >= target_time and not email_sent_today:  # Saat 00:02 veya sonrası
        logging.info("Sistem günlük özet çıkarılıyor...")
        try:
            daily_summary_and_send_email(cursor,system_prompt,response_format)
            logging.info("Günlük özet çıkarıldı ve e-posta gönderildi.")
            email_sent_today = True  # Günlük e-posta gönderildiğini işaretle

        except Exception as email_error:
            logging.error(f"Günlük özet gönderimi sırasında hata oluştu: {email_error}")
            
    if current_time == dt_time(23,59) and email_sent_today:
        logging.info("Yeni gün için e-posta gönderim değeri sıfırlanıyor.")
        email_sent_today = False

    # cumartesi ayarla yeniden
    if  current_date <= startdate:
        db.close()
        logging.info("Sistem saati var olan başlangıç saat değerinden büyük olamayacağı için 1 saatlik uyku modu aktifleştiriliyor ...")
        time.sleep(3600)

    try:
        data = fetch_data_from_api(startdate, stopdate)
        if data is None:
            logging.error("API'ye istekte bulunamadı")
            continue

        # API'den gelen hata kontrolleri
        if "error" in data and "code" in data:
            error_code = data["code"]
            error_value = data["error"]
            logging.error(f"Hata kodu '{error_code}' ve Hata Nedeni: '{error_value}'")
            if error_code =='40':
                    error_counter +=1
                    logging.info(f"error_counter : {error_counter}")
                    
            should_continue, error_counter = fetch_api_check_data(error_code, error_counter,stopdate)
            if should_continue:
                logging.warning("Belirtilen aralıkta kayıt bulunamadı, 1 dakika sonra sistem yeniden istekte bulunacaktır.")        
                continue
            else:
                logging.error("Hata farklı bir nedenden dolayı kaynaklanıyor veya hata limitine ulaşıldı.")
                break
        data_reversed = list(reversed(data))
        total_records = len(data_reversed)
        logging.info(f"Toplam kayıt sayısı başlangıçta: {total_records} ve kayıtlar: {data_reversed}")

        if not data_reversed or "error" in data_reversed:
            logging.error("Veri işleme sırasında hata meydana geldi.")
            continue
        # santral tablosunda var ama cagri tablosunda yoksa kontrol döngüsü
        for entry in data_reversed:
            uniqueid = entry.get('uniqueid')
            # Donen listedeki iç elemanlarıda kendi içinde sıralama yapmamız gerekiyor
            print(data_reversed)
            sorted_list = sorted(
                entry.get('values',[]), key=lambda x: datetime.strptime(x['date'].strip(), "%d.%m.%Y %H:%M:%S"))
            
            for values in sorted_list:
                date_santral = datetime.strptime(entry.get('date').strip(), "%d.%m.%Y %H:%M:%S")
                format_date_santral = date_santral.strftime("%Y-%m-%d %H:%M:%S")
                direction_santral = values.get('direction')
                source_santral, destination_santral, duration_santral = values.get('source'), values.get('destination'), values.get('duration')
                print(f"uniqid: {uniqueid} tarih:{format_date_santral}")
        # region Aynı uniqueid ve tarih var mı kontrol et
                exists = check_uniqueid_exits_santral(cursor, uniqueid, format_date_santral, direction_santral)
                if exists:
                    logging.info(f"Santral Tablosunda Var Atlanıyor -> UniqueID: {uniqueid}, Tarih: {format_date_santral}, Yon: {direction_santral} (Zaten mevcut)")
                else:
                    save_to_db_santral(cursor,uniqueid, format_date_santral, source_santral, destination_santral, direction_santral, duration_santral)
                    logging.info(f"Santral Tablosuna Eklendi -> UniqueID: {uniqueid}, Tarih: {format_date_santral}, Yon: {direction_santral}")

            logging.info(f"{uniqueid} işleniyor.")
            time.sleep(10)
            data_records = process_records(entry)
            logging.info(f"İşlemler sonucu elde edilen veri listesi: {data_records}")

            if data_records is not None:
                for i, value in enumerate(data_records):
                    recording_url = value.get('recording')
                    date = datetime.strptime(value.get('date').strip(), "%d.%m.%Y %H:%M:%S")
                    format_date = date.strftime("%Y-%m-%d %H:%M:%S")
                    direction = value.get('direction')
                    direction = 'GIDEN' if direction == 0 else 'GELEN' if direction == 1 else 'ICARAMA'
                    source, destination, duration = value.get('source'), value.get('destination'), value.get('duration')

                    data_db = check_uniqueid_exits(cursor, uniqueid, format_date_santral, direction)
                    if data_db:
                        logging.info("CagriTakip Tablosunda Bu kayıt zaten var, atlanıyor")
                    else:
                        logging.info(f"""CagriTakip Tablosunda Bu Kayıt yok, işleme alınıyor:
                                    uniqueid={uniqueid},
                                    date={format_date_santral},
                                    direction={direction},
                                    url={recording_url}
                                    """)

                        # Şartlara uyan ses dosyalarını indirme
                        mp3_path = download_and_convert_audio(recording_url, uniqueid, i)
                        logging.info(f"Ses kaydı {mp3_path} olarak indirildi ve kaydedildi")

                        # region Chunk Dosyası oluşturma ve ses dosyalarını bölütleme
                        chunk_file  = segment_audio(mp3_path)
                        all_transcription = []
                        for chunk_file in chunk_file:
                            transcript_file = whisper_transcribe_chunk(chunk_file)
                            all_transcription.extend(transcript_file)
                        # endregion

                        # region Transcriptions Parçala Speaker - Özetle
                        chunks = preapare_chat_chunk_transcriptions(transcript_file)
                        final_analysis_result,chat_response = speaker_analysis(chunks)
                        final_summary_result,chat_summary_response = transcript_summary(chunks)
                        # endregion
                        # region Maliyet Hesaplama ve Veri Tabanı Veri Ekleme - Kaydetme İşlemleri
                        costs = calculate_costs(chat_response,chat_summary_response,pricing_gpt) #whisper_cost_per_minute,pricing_gpt)
                        gpt_cost = costs['gpt_cost'] # Toplam Maliyet bilgisi
                        save_to_db(cursor, uniqueid, format_date, direction, source, destination, duration,final_analysis_result,final_summary_result,gpt_cost)

                        db.commit()
                        os.remove(chunk_file)
                        os.remove(mp3_path)
                        logging.info(f"Chunk File ve MP3 Dosyaları Silinmiştir: {chunk_file}, {mp3_path}")
                        # endregion
            else:
                logging.info(f"{uniqueid} şartları sağlamayan kayıtlar CagriTakip tablosuna işlenmiyor.")
                
            total_records -=1
            logging.info(f"{uniqueid} kaydı Ayarlar tablosundaki tarih kolonu değişikliği işleniyor.")
            update_last_processed_date(cursor, format_date_santral) # bu şarta uymayan verinin de tarih değeri ayarlar tablosuna eklemiş oluyoruz
            logging.info(f"total_records: {total_records}")
            time.sleep(10)
    except Error as e:
        logging.error(f"Veritabanı hatası: {e}")
    finally:
        
        # Döngü bitmeden önce, eğer veritabanına işlem yapılmamışsa stopdate güncellenmeli
        try:
            # Yeni startdate'i yeniden sorguluyoruz
            new_startdate, new_stopdate = get_startdate(cursor)
            logging.info(f"Yeni startdate: {new_startdate} yeni stopdate: {new_stopdate}")
            
            # Eğer önceki startdate ile yeni startdate aynıysa, stopdate'i güncelle
            if new_startdate == startdate:
                logging.info("Startdate aynı, stopdate güncelleniyor.")
                update_last_processed_date(cursor, new_stopdate)
                db.commit()
                logging.info(f"stopdate güncellendi: {new_stopdate}")
            else:
                logging.info("Startdate değişti, güncelleme yapılmıyor.")
        except Exception as e:
            logging.error(f"stopdate güncellenirken hata oluştu: {e}")
        
        if 'cursor' in locals() and cursor:
            try:
                cursor.close()
                logging.info("Cursor kapatıldı")
            except Exception as e:
                logging.error(f"Cursor kapatılma sırasında hata {e} meydana geldi!")
        
        if 'db' in locals() and db:
            try:
                db.close()
                logging.info("Veri tabanı kapatıldı")
            except Exception as e:
                logging.error(f"Veri tabanı kapatılma sırasında hata {e} meydana geldi!")
        
        logging.info("Veritabanı bağlantısı kapatıldı, sistem 10 dakika uykuya alınıyor...")
        time.sleep(600)
            

# endregion