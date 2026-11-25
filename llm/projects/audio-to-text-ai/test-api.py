# region 1 Kütüphaneler 
import time
import requests
from datetime import datetime, timedelta, time as dt_time
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
from email.header import Header
import json
# endregion

# region 2 Bağlantı Bilgileri
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

# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.basicConfig(level=logging.INFO, format="%(asctime)s.%(msecs)02d - %(levelname)s - %(message)s")

# endregion

# region 3 OpenAI API Anahtarı
openai.api_key = 'sk-REPLACE_WITH_YOUR_OPENAI_KEY'
# endregion

# region 4 Veri tabanı bağlantı isteği
def create_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        logging.info("Veri tabanına bağlantı başarılı")
        return connection
    except Error as e:
        logging.error(f"Veri tabanına bağlantı yapılırken hata '{e}' meydana geldi")
        return None
# endregion

# region 5 Netgsm Api İsteği
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

# region 6 Son İşleme Tarihini Veritabanından Al
def get_startdate(cursor):
    cursor.execute("SELECT deger FROM ayarlar WHERE anahtar = 'cagriaisonkontrol'")
    result = cursor.fetchone()
    if result and result[0]:
        startdate = datetime.strptime(result[0].strip(), "%Y-%m-%d %H:%M:%S")
        
        stopdate = startdate + timedelta(minutes=60)
        return startdate, stopdate
    else:
        raise ValueError("Veritabanında 'startdate' bulunamadı!")

# endregion

# region 7 Netgsm Api'den Dönen Hata Kontrolleri
def fetch_api_check_data(error_code, error_counter, stopdate):
    if error_code == '30':
        logging.error("Geçersiz Kullanıcı adı veya IP sınırlaması. API ayarlarını kontrol edin veya bilgileri yeniden güncelleyin.")
    elif error_code == '40':
        new_startdate = updates_new_date(stopdate)
        update_last_processed_date(cursor, new_startdate)
        db.commit()
        logging.info(f"Yeni servis isteği için startdate: '{new_startdate}' veri tabanında kaydedildi")
        
        if error_counter >= 5:
            logging.warning("5 kez sistem error_counter girdi sistem 1 saatlik uyku modunda giriyor")
            update_last_processed_date(cursor, stopdate)
            db.commit()
            error_counter = 0
            time.sleep(3600)
            return True, error_counter
        return True, error_counter
    
    elif error_code == '70':
        logging.error("Hatalı sorgulama. Gönderdiğiniz parametrelerden birisi hatalı veya zorunlu alanlardan birinin eksik olduğunu ifade eder.")
        return False, error_counter
    
    elif error_code in ['100', '101']:
        logging.error("Sistem hatası veya sınır aşımı. Bir süre bekleniyor...")
        time.sleep(120)
        return True, error_counter
    
    else:
        logging.info("Hata kodu yok")
        return False, error_counter
# endregion

# region 8 Şartları Sağlamayan Durumlar için Tarih Iterasyon Fonsk.
def updates_new_date(stopdate):
    new_startdate = stopdate
    new_stopdate = new_startdate + timedelta(minutes=60)
    logging.info(f"Yeni startdate: '{new_startdate}' ve stopdate: '{new_stopdate}'")
    return new_startdate
# endregion

#  region 9 En Son İşleme Tarihini Güncelle
def update_last_processed_date(cursor, stopdate_sleep_before):
    query = "UPDATE ayarlar SET deger = %s WHERE anahtar = 'cagriaisonkontrol'"
    cursor.execute(query, (stopdate_sleep_before,))
# endregion

# region 10 Tüm Santral Kayıtlarına Ait Uniqueid Kontrol
def check_uniqueid_exits_santral(cursor, uniqueid, format_date_santral, direction_santral):
    try:
        query = "SELECT cagriid, tarih, yon FROM cagritakip_santral WHERE cagriid = %s AND tarih = %s AND yon = %s"
        cursor.execute(query, (uniqueid, format_date_santral, direction_santral,))
        logging.info(f"Veri tabanından uniquied sorgusu başarıyla gerçekleşti")
        result = cursor.fetchall()
        return result

    except Exception as err:
        logging.error(f"Veri tabanında uniquied id bilgisi sorgulanırken '{err}' hata meydana geldi")

# endregion

# region 11 Veriyi Veri Tabanına Kaydet
def save_to_db_santral(cursor, uniqueid, format_date, source, destination, direction, duration):
    query = """
        INSERT INTO cagritakip_santral (cagriid, tarih, arayan, aranan, yon, sure)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    values = (uniqueid, format_date, source, destination, direction, duration)
    cursor.execute(query, values)
# endregion

# region 12 Kurala Uyan İşlenecek Verileri Belirleme 
def process_records(entry):
    recordings = [
        v for v in entry.get("values", [])
        if v.get("recording") and v.get("destination") not in ["0000000000-announcement-OgleArasi", "0000000000-announcement-mesaidisi"]
        and (int(v.get("duration", 0)) >= 30)
    ]
    directions = {0: [], 1: [], 4: []}

    for rec in recordings:
        direction = rec.get("direction")
        if direction in directions:
            directions[direction].append(rec)

    select_recordings = []
    for direction, recs in directions.items():
        if recs:
            latest_recording = max(recs, key=lambda v: datetime.strptime(v["date"].strip(), "%d.%m.%Y %H:%M:%S"))
            select_recordings.append(latest_recording)

    return select_recordings
# endregion

# region 13 CagriTaki Tablosunda Uniqueid Aynı Kaydı Atla
def check_uniqueid_exits(cursor, uniqueid, format_date, direction):
    try:
        query = "SELECT cagriid, tarih, yon FROM cagritakip WHERE cagriid = %s AND tarih = %s AND yon = %s"
        cursor.execute(query, (uniqueid, format_date, direction,))
        logging.info(f"Veri tabanından uniquied sorgusu başarıyla gerçekleşti")
        result = cursor.fetchall()
        return result
    except Exception as err:
        logging.error(f"Veri tabanında uniquied id bilgisi sorgulanırken '{err}' hata meydana geldi")
# endregion

# region 14 Local'de çalışan enes.y dosyasına gelen yanıtı ekrana basalım
def send_data_to_local_machine(recording_url, uniqueid,index):
    """
    Bu fonksiyon, verileri local bilgisayarındaki Flask API'ye gönderir.
    """
    try:
        url = "http://192.168.1.118:4141/receive_data"  # Local bilgisayarınızın IP adresi ve portu
        data = {

            "uniqueid": uniqueid,
            "url": recording_url,
            "i": index,
        }
        
        response = requests.post(url, json=data)
        logging.info(f"response data trascript: {response}")
        
        if response.status_code == 200:
            logging.info("Data successfully sent to local machine.")
            return response
        else:
            logging.error(f"Failed to send data to local machine. Status code: {response.status_code}")
            return None
    
    except Exception as e:
        logging.error(f"Error while sending data to local machine: {e}")
        return None
# endregion

# region 15 Whisper Sonucunu Parça Parça Speaker Analize Yapma
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

# region 16 Chat Speaker Prompt
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

# region 17 Chat Özet Prompt
def transcript_summary(chunks):
    # Özetleme prompt'u
    all_summary_results = []
    chat_summary_response = None
    for chunk in chunks:

        prompt_summary = """Make a meaningful and short summary, extract important information and main points using the given text.

                    ***Instructions***
                    1. Make a general explanation of the speech (purpose of the speech, main topic, etc.).
                    2. Identify the important points and details that give the essence of the speech.
                    3. Summarize the main questions and answers given in the interview.
                    4. Provide information about the decisions taken and their results at the end of the speech.
                    
                    ***Output***
                    - Create a short and understandable summary based on the speech text.

                    ***Attention***
                    - Summarization should be done in Turkish.
                    - The summary should be directly related to the content of the text, and no extraneous information should be added.
                    - Answers should be clear, detailed and easily understandable.
        """
        for text in chunk:
            prompt_summary += f"Text: {text}\n"
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
                handle_api_error(err,'transcript summary:')
                return None, None
            
        except Exception as e:
            logging.error(f"Beklenmeyen Hatalar meydana geldi : {e} ")

    final_summary_result = '\n'.join(all_summary_results)
    return final_summary_result,chat_summary_response
# endregion

# region 18 Maliyet Hesaplama Fonksiyonu
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

    # Log the costs
    logging.info(f"ChatCompletion and Summary maliyeti: ${gpt_cost:.6f}")

    return {
        "gpt_cost": gpt_cost
    }
# endregion

# region 19 Veriyi Veri Tabanına kaydet
def save_to_db(cursor, uniqueid, format_date, direction_text, source, destination, duration,final_analysis_result,summary_result,gpt_cost):
    query = """
        INSERT INTO cagritakip (cagriid, tarih, yon, arayan, aranan, sure, metin,ozet,cost)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (uniqueid, format_date, direction_text, source, destination, duration,final_analysis_result,summary_result,gpt_cost)
    cursor.execute(query, values)
# endregion

# region 20 handle_api_error 
def handle_api_error(err, function_name):
    error_message = f"API hatası alındı {err.http_status}, mesaj: {str(err)}"
    logging.error(error_message)
    send_daily_error_mail(f"Meydana gelen hata sonucu konteynırı yeniden başlatın: {function_name}", error_message)
    time.sleep(90)  # 1.5 dakika bekle
    send_daily_error_mail("Sistem Başarıyla Yeniden Başlatıldı", f"{function_name} işlemi 1 dakika bekledikten sonra yeniden çalıştı.")
# endregion 

# region 21 Günlük Hata Kontrol E-Posta Gönderme Fonksiyonu
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

# region 22 Maliyet hesaplaması için gerekli bilgiler
pricing_gpt = {
    "gpt-4o-mini": {
        "input": 0.15,  # Örnek girdi maliyeti
        "cached_input": 0.075, # cahche maliyeti
        "output": 0.60  # Örnek çıktı maliyeti
    }
}
# endregion


error_counter = 0

while True:
    db = create_connection()
    if not db:
        logging.error("Veritabanı bağlantısı kurulamadı, program sonlanıyor.")
        continue
    cursor = db.cursor()
    
    startdate, stopdate = get_startdate(cursor)
    logging.info(f"startdate: {startdate} stopdate {stopdate}")
    
    try:
        data = fetch_data_from_api(startdate, stopdate)
        if data is None:
            logging.error("API'ye istekte bulunamadı")
            continue

        data_reversed = list(reversed(data))
        total_records = len(data_reversed)
        logging.info(f"Toplam kayıt sayısı başlangıçta: {total_records} ve kayıtlar: {data_reversed}")

        if not data_reversed or "error" in data_reversed:
            logging.error("Veri işleme sırasında hata meydana geldi.")
            continue
        
        for entry in data_reversed:
            uniqueid = entry.get('uniqueid')
            sorted_list = sorted(entry.get('values', []), key=lambda x: datetime.strptime(x['date'].strip(), "%d.%m.%Y %H:%M:%S"))
            
            for values in sorted_list:
                date_str = values.get('date')
                if date_str:
                    date_santral = datetime.strptime(date_str.strip(), "%d.%m.%Y %H:%M:%S")
                    format_date_santral = date_santral.strftime("%Y-%m-%d %H:%M:%S")
                    direction_santral = values.get('direction')
                    source_santral, destination_santral, duration_santral = values.get('source'), values.get('destination'), values.get('duration')
                    logging.info(f"uniqid: {uniqueid} tarih:{format_date_santral}")
                    
                    exists = check_uniqueid_exits_santral(cursor, uniqueid, format_date_santral, direction_santral)
                    if exists:
                        logging.info(f"Santral Tablosunda Var Atlanıyor -> UniqueID: {uniqueid}, Tarih: {format_date_santral}, Yon: {direction_santral} (Zaten mevcut)")
                    else:
                        save_to_db_santral(cursor, uniqueid, format_date_santral, source_santral, destination_santral, direction_santral, duration_santral)
                        db.commit()
                        logging.info(f"Santral Tablosuna Eklendi -> UniqueID: {uniqueid}, Tarih: {format_date_santral}, Yon: {direction_santral}")

                else:
                    logging.error(f"Date bilgisi eksik: {entry}")
                    continue  # Bu kaydı atla

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

                        response_local = send_data_to_local_machine(recording_url, uniqueid, i)
                        logging.info(f"gelen transcript verisi {response_local}")
                        try:
                            # response_local.status_code kontrolü
                            if response_local and response_local.status_code == 200:
                                try:
                                    # JSON verisini almak
                                    response_py = response_local.json()
                                    
                                    # Burada gelen yanıtı logluyoruz
                                    if 'transcription' in response_py:
                                        transcript_file = response_py['transcription'] 
                                        if transcript_file:
                                            logging.info(f"192.168.1.118:4141/receive_data dönen veri: {transcript_file}")

                                            # region Transcriptions Parçala Speaker - Özetle
                                            chunks = preapare_chat_chunk_transcriptions(transcript_file)
                                            print(f"\n chunks: {chunks}\n")
                                            final_analysis_result,chat_response = speaker_analysis(chunks)
                                            final_summary_result,chat_summary_response = transcript_summary(chunks)
                                            logging.info(f"\n\n final_summary_result: {final_summary_result}\n\n")
                                            # endregion
                                            
                                            # region Maliyet Hesaplama ve Veri Tabanı Veri Ekleme - Kaydetme İşlemleri
                                            costs = calculate_costs(chat_response,chat_summary_response,pricing_gpt) #whisper_cost_per_minute,pricing_gpt)
                                            gpt_cost = costs['gpt_cost'] # Toplam Maliyet bilgisi
                                            save_to_db(cursor, uniqueid, format_date, direction, source, destination, duration,final_analysis_result,final_summary_result,gpt_cost)
                                            db.commit()
                                        else:
                                            logging.warning(f"192.168.1.118:4141/receive_data dönen veri boş: {transcript_file}")
                                    else:
                                        logging.error(f"Transkript bulunamadı. API yanıtı: {transcript_file}")
                                except ValueError:  # Eğer JSON verisi alınmazsa
                                    logging.error(f"192.168.1.118:4141 cevabı JSON formatında değil.")
                            else:
                                logging.error(f"192.168.1.118:4141 API isteği başarısız oldu. Status code: {response_local.status_code if response_local else 'No response'}")
                                
                        except Exception as err:   
                            logging.error(f"192.168.1.118:4141 hata meydana geldi {err}")
            else:
                logging.info(f"{uniqueid} şartları sağlamayan kayıtlar CagriTakip tablosuna işlenmiyor.")
            
            total_records -= 1
            logging.info(f"{uniqueid} kaydı Ayarlar tablosundaki tarih kolonu değişikliği işleniyor.")
            update_last_processed_date(cursor, format_date_santral)
            db.commit()
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
