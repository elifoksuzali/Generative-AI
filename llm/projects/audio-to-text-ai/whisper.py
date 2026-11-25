# # region 1 Kütüphaneler 
# import time
# import requests
# from datetime import datetime, timedelta, time as dt_time
# from mysql.connector import Error
# import logging
# import smtplib
# from openai import OpenAI
# from email.mime.text import MIMEText
# from database.db import (create_connection, get_startdate, update_last_processed_date, 
#                         check_uniqueid_exits_santral, save_to_db_santral, check_uniqueid_exits, 
#                         save_to_db, get_hostname,get_ollama_api_key,prompts 
# )
# from ollama_func import ollama_speaker_analysis_prompt as ollama_speaker, ollama_transcript_summary_prompt as ollama_transcript
# # endregion

# # region 2 Bağlantı Bilgileri

# API_CREDENTIALS = {
#     "usercode": "0000000000",
#     "password": "FAKE_NETGSM_PASSWORD"
# }


# # logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# logging.basicConfig(level=logging.INFO, format="%(asctime)s.%(msecs)02d - %(levelname)s - %(message)s")

# # endregion

# # region 3 Netgsm Api İsteği
# def fetch_data_from_api(startdate, stopdate):
#     """
#     API'den veri çeker.
#     """
#     url = "https://api.netgsm.com.tr/netsantral/report"
#     headers = {"Content-Type": "application/json"}
#     json_data = {
#         "usercode": API_CREDENTIALS["usercode"],
#         "password": API_CREDENTIALS["password"],
#         "startdate": startdate.strftime("%d%m%Y%H%M%S"),
#         "stopdate": stopdate.strftime("%d%m%Y%H%M%S")
#     }

#     try:
#         response = requests.post(url, headers=headers, json=json_data)
#         if response.status_code == 200:
#             data = response.json()
#             # Eğer hata mesajı varsa direkt döndür
#             if isinstance(data, dict) and "error" in data:
#                 return data
#             # Veri varsa parçala ve işle
#             elif isinstance(data, list):
#                 new_api_list = []
#                 for entry in data:
#                     uniqueid = entry.get('uniqueid')
#                     values = entry.get('values', [])
#                     for value in values:
#                         if 'recording' in value:
#                             new_entry = {
#                                 "uniqueid": uniqueid,
#                                 "values": [value]
#                             }
#                             new_api_list.append(new_entry)
#                 return new_api_list
#             return data
#         elif response.status_code == 404:
#             logging.info(f"Veri bulunamadı:")
#             return []
#         else:
#             logging.error(f"API isteği başarısız oldu. Durum kodu: {response.status_code}")
#             return None
#     except Exception as e:
#         logging.error(f"Hata oluştu: {e}")
#         return None

# # endregion

# # region 4 Netgsm Api'den Dönen Hata Kontrolleri
# def fetch_api_check_data(error_code, error_counter, stopdate):
#     now = datetime.now()
    
#     if error_code == '40':
#         if error_counter >= 15:
#             logging.warning("15 kez üst üste error_code 40 alındı. Sistem uyku moduna hazırlanıyor.")
            
#             # Ertesi gün 8:55'i ayarla
#             next_day = now + timedelta(days=1)
#             next_run_time = next_day.replace(hour=8, minute=55, second=0, microsecond=0)
            
#             # Veritabanını güncelle
#             update_last_processed_date(cursor, next_run_time)
#             db.commit()
            
#             body = f"""
#             📌 Sistem 15 kez üst üste <code>40</code> hatası aldı.<br>
#             ⏰ Bir sonraki çalışma zamanı: <b>{next_run_time}</b><br>
#             💤 Ertesi gün 08:55'e kadar uykuya geçiliyor.<br>
#             """
#             send_daily_error_mail("⚠️ 15. Hata - Sistem Ertesi Gün 8:55'e Ayarlandı", body)

#             # Ertesi gün 08:55'e kadar uykuya geç
#             sleep_seconds = (next_run_time - now).total_seconds()
#             if sleep_seconds > 0:
#                 logging.warning(f"{sleep_seconds / 3600:.1f} saat uykuya geçiliyor.")
#                 time.sleep(sleep_seconds)
#             return True, 0  # Sayaç sıfırlanır

#         # 15'ten az hata için 5 dakika bekle ve devam et
#         logging.warning("Belirtilen aralıkta kayıt bulunamadı, 5 dakika sonra sistem yeniden istekte bulunacaktır.")
#         time.sleep(300)
#         return True, error_counter
#     else:
#         # 40 dışında hata varsa dur
#         return False, error_counter
# # endregion

# # region 5 Kurala Uyan İşlenecek Verileri Belirleme 
# def process_records(entry):
#     recordings = [
#         v for v in entry.get("values", [])
#         if v.get("recording") and v.get("destination") not in ["0000000000-announcement-OgleArasi", "0000000000-announcement-mesaidisi"]
#         and (int(v.get("duration", 0)) >= 21)
#     ]
#     directions = {0: [], 1: [], 4: []}

#     for rec in recordings:
#         direction = rec.get("direction")
#         if direction in directions:
#             directions[direction].append(rec)

#     select_recordings = []
#     for direction, recs in directions.items():
#         if recs:
#             latest_recording = max(recs, key=lambda v: datetime.strptime(v["date"].strip(), "%d.%m.%Y %H:%M:%S"))
#             select_recordings.append(latest_recording)

#     return select_recordings
# # endregion

# # region 6 Local'de çalışan enes.y dosyasına gelen yanıtı ekrana basalım
# def send_data_to_local_machine(recording_url, uniqueid,index,hostname):
#     """
#     Bu fonksiyon, verileri local bilgisayarındaki Flask API'ye gönderir.
#     """
#     try:
#         url = f"http://{hostname}:4141/receive_data" # Local bilgisayarınızın IP adresi ve portu
#         data = {

#             "uniqueid": uniqueid,
#             "url": recording_url,
#             "i": index,
#         }
        
#         response = requests.post(url, json=data)
#         logging.info(f"response data trascript: {response}")
        
#         if response.status_code == 200:
#             logging.info("127.0.0.1 sunucusundan başarıyla veri alındı.")
#             return response
#         else:
#             logging.error(f"Failed to send data to local machine. Status code: {response.status_code}")
#             return None
    
#     except Exception as e:
#         logging.error(f"Error while sending data to local machine: {e}")
#         return None
# # endregion

# # region 7 Whisper Sonucunu Parça Parça Speaker Analize Yapma
# def preapare_chat_chunk_transcriptions(transcription_file):
#     max_length=2000
#     chunks = []
#     current_chunk = []

#     # Splitting the transcriptions into chunks
#     for start, end, text in transcription_file:
#         # Prepare the proposed chunk
#         proposed_chunk = current_chunk + [(start, end, text)]
#         chunk_length = sum(len(t[2]) for t in proposed_chunk)  # Total length of texts in the chunk

#         if chunk_length > max_length:  # If current chunk exceeds the limit
#             chunks.append(current_chunk)  # Save the current chunk
#             current_chunk = [(start, end, text)]  # Start a new chunk
#         else:
#             current_chunk.append((start, end, text))  # Add to the current chunk

#     # Append any remaining current chunk
#     if current_chunk:
#         chunks.append(current_chunk)

#     return chunks

# # endregion

# # region 8 GPT ALANI

# # region 8 Chat Speaker Prompt
# # def speaker_analysis(chunks):
# #     all_analysis_results = []
# #def speaker_analysis(chunks):
# #    all_analysis_results = []
# #    chat_response = None  # Açıklama amacıyla buraya ekledik.
# #
# #    for chunk in chunks:
# #        # Konuşmacı ayrıştırma prompt'u
# #        prompt = ("""Please analyze the following conversations to isolate the speakers Always use Turkish language. 
# #                
# #                'Speaker 1' would typically be the operator answering the phone and 'Speaker 2' would be the customer or caller. 
# #                Also, organize the conversations in a specific format: 
# #                Speaker X: Start: <start>, End: <end>, Text: <text>. 
# #                Transcript data:\n
# #                
# #                 ***Attention***
# #                Keep responses as concise and to the point as possible and Always use Turkish language"""
# #        )
# #
# #        for start, end, text in chunk:
# #            prompt += f"Start: {start}, End: {end}, Text: {text}\n"
# #        try:
# #            # OpenAI ChatCompletion isteği gönderme
# #            chat_response = client.chat.completions.create(
# #                model="gpt-4o-mini",
# #                messages=[{"role": "user", "content": prompt}],
# #                temperature=0.8,
# #                timeout=180
# #            )
# #            analysis_result = chat_response.choices[0].message.content
# #            all_analysis_results.append(analysis_result)
# #            logging.info(f"Konuşmacı Analizi Sonucu:\n{analysis_result}")
# #            
# #        except openai.APIError as err:
# #            logging.error(f"API hatası alındı {err.status_code}, mesaj :  {str(err)}")
# #            # Hata 500 ise handle_api_error fonksiyonu çağrılacak
# #            if err.status_code == 500:
# #                handle_api_error(err,'speaker_analysis')
# #                return None, None
# #        except Exception as e:
# #            logging.error(f"Beklenmeyen Hatalar meydana geldi : {e} ")
# #
# #    final_analysis_result = '\n'.join(all_analysis_results)
# #    return final_analysis_result,chat_response
# # endregion

# # region 9 Chat Özet Prompt
# #def transcript_summary(chunks):
# # mail_prompt = prompt_gemini[0][1]  # mail_prompt metni


# #    # Özetleme prompt'u
# #    all_summary_results = []
# #    chat_summary_response = None
# #    for chunk in chunks:
# #
# #        prompt_summary = """Make a meaningful and short summary, extract important information and main points using the given text.
# #
# #                    ***Instructions***
# #                    1. Make a general explanation of the speech (purpose of the speech, main topic, etc.).
# #                    2. Identify the important points and details that give the essence of the speech.
# #                    3. Summarize the main questions and answers given in the interview.
# #                    4. Provide information about the decisions taken and their results at the end of the speech.
# #                    
# #                    ***Output***
# #                    - Create a short and understandable summary based on the speech text.
# #
# #                    ***Attention***
# #                    - Summarization should be done in Turkish.
# #                    - The summary should be directly related to the content of the text, and no extraneous information should be added.
# #                    - Answers should be clear, detailed and easily understandable.
# #        """
# #        for text in chunk:
# #            prompt_summary += f"Text: {text}\n"
# #        try:
# #            # OpenAI ChatCompletion isteği gönderme
# #            chat_summary_response = client.chat.completions.create(
# #                model="gpt-4o-mini",
# #                messages=[{"role": "user", "content": prompt_summary}],
# #                temperature=0.8,
# #                timeout=180
# #            )
# #            summary_result = chat_summary_response.choices[0].message.content
# #            all_summary_results.append(summary_result)
# #
# #            logging.info(f"Transkript Özeti:\n{summary_result}")
# #
# #        except openai.APIError as err:
# #            logging.error(f"API hatası alındı {err.status_code}, mesaj :  {str(err)}")
# #            # Hata 500 ise handle_api_error fonksiyonu çağrılacak
# #            if err.status_code == 500:
# #                handle_api_error(err,'transcript summary:')
# #                return None, None
# #            
# #        except Exception as e:
# #            logging.error(f"Beklenmeyen Hatalar meydana geldi : {e} ")
# #
# #    final_summary_result = '\n'.join(all_summary_results)
# #    return final_summary_result,chat_summary_response

# # endregion

# # region 10 Maliyet Hesaplama Fonksiyonu
# #def calculate_costs(chat_response, chat_summary_response, pricing_gpt): #whisper_cost_per_minute, pricing_gpt):
# #    # Chat Completion Speaker Cost Calculation
# #    input_tokens = chat_response['usage']['prompt_tokens']
# #    output_tokens = chat_response['usage']['completion_tokens']
# #    tokens_cached = chat_response['usage']['prompt_tokens_details']['cached_tokens']
# #
# #
# #    # Chat Completion Summary Cost Calculation
# #    input_tokens_sum = chat_summary_response['usage']['prompt_tokens']
# #    output_tokens_sum = chat_summary_response['usage']['completion_tokens']
# #    chat_cached__sum = chat_summary_response['usage']['prompt_tokens_details']['cached_tokens']
# #    logging.info(f"input chat {input_tokens} output chat: {output_tokens} cahche chat: {tokens_cached}")
# #
# #    logging.info(f"input sum {input_tokens_sum} output aum: {output_tokens_sum} cahche sum: {chat_cached__sum}")
# #
# #    # Completion Calculate
# #    input_cost = (input_tokens / 1_000_000) * pricing_gpt["gpt-4o-mini"]["input"]
# #    cached_cost = (tokens_cached / 1_000_000) * pricing_gpt["gpt-4o-mini"]["cached_input"]
# #    output_cost = (output_tokens / 1_000_000) * pricing_gpt["gpt-4o-mini"]["output"]
# #
# #    chatgpt_cost = input_cost + output_cost + cached_cost
# #
# #    # Chat Completion Summary Cost Calculation
# #
# #    input_tokens_summary = (input_tokens_sum / 1_000_000) * pricing_gpt["gpt-4o-mini"]["input"]
# #    cached_summary_cost = (chat_cached__sum / 1_000_000) * pricing_gpt["gpt-4o-mini"]["cached_input"]
# #    output_cost_summary = (output_tokens_sum / 1_000_000) * pricing_gpt["gpt-4o-mini"]["output"]
# #
# #    sum_cost = input_tokens_summary + cached_summary_cost + output_cost_summary
# #
# #    # Total costs
# #    gpt_cost = chatgpt_cost + sum_cost
# #
# #    # Log the costs
# #    logging.info(f"ChatCompletion and Summary maliyeti: ${gpt_cost:.6f}")
# #
# #    return {
# #        "gpt_cost": gpt_cost
# #    }
# # endregion

# # endregion

# # region 9 handle_api_error 
# def handle_api_error(err, function_name):
#     error_message = f"API hatası alındı {err.status_code}, mesaj: {str(err)}"
#     logging.error(error_message)
#     send_daily_error_mail(f"Meydana gelen hata sonucu konteynırı yeniden başlatın: {function_name}", error_message)
#     time.sleep(30)  # 1.5 dakika bekle
#     send_daily_error_mail("Sistem Başarıyla Yeniden Başlatıldı", f"{function_name} işlemi 5 dakika bekledikten sonra yeniden çalıştı.")
# # endregion 

# # region 10 Günlük Hata Kontrol E-Posta Gönderme Fonksiyonu
# def send_daily_error_mail(subject,body):
#     try:
#         # SMTP ayarları
#         smtp_login = "info@example.com"  # SMTP kullanıcı adı
#         smtp_password = "FAKE_SMTP_APP_PASSWORD"  # SMTP şifre
#         smtp_host = "smtp.yandex.com"  # SMTP sunucusu
#         smtp_recipients_email_to = ["agent1@example.com"]
#         logging.info("SMTP ayarları alındı.")
#     except Exception as e:
#         logging.error(f"SMTP ayarları alınırken hata oluştu: {e}")
#         return
#     try:
#         # Günün tarihini al
#         today_date = datetime.now().strftime("%d %m %Y")
#         subject =  f'{today_date} --- {subject}'
#         # E-posta gönderimi için içerik hazırlama
#         msg = MIMEText(body, 'html', 'utf-8')
#         msg['Subject'] = subject
#         msg['From'] = smtp_login
#         msg['To'] = ', '.join(smtp_recipients_email_to)  # Alıcıları virgülle ayırarak ekle
        
#         with smtplib.SMTP(smtp_host, 587, timeout=10) as smtp_server:
#             smtp_server.starttls()
#             smtp_server.login(smtp_login, smtp_password)
#             smtp_server.sendmail(smtp_login, smtp_recipients_email_to, msg.as_string())  # Liste olarak gönder
#             logging.info("Veri yok e-postası başarıyla gönderildi.")
            
#     except Exception  as e:
#         logging.error(f"E-posta gönderimi sırasında hata oluştu: {e}")
# # endregion 

# # region 11 Maliyet hesaplaması için gerekli bilgiler
# pricing_gpt = {
#     "gpt-4o-mini": {
#         "input": 0.15,  # Örnek girdi maliyeti
#         "cached_input": 0.075, # cahche maliyeti
#         "output": 0.60  # Örnek çıktı maliyeti
#     },
#     "gemini-2.0-flash": {
#         "input": 0.00025,  # Gemini input token maliyeti
#         "output": 0.0005   # Gemini output token maliyeti
#     }
# }
# # endregion


# error_counter = 0

# while True:
#     db = create_connection()
#     if not db:
#         logging.error("Veritabanı bağlantısı kurulamadı, program sonlanıyor.")
#         continue
#     cursor = db.cursor()
    
#     startdate, stopdate = get_startdate(cursor)
    
#     # ollama api  reqirements
#     hostname = get_hostname(cursor)
#     ollama_api_key = get_ollama_api_key(cursor)
#     prompt_gemini = prompts(cursor)
#     ollama_client = OpenAI(api_key=ollama_api_key,base_url=f"http://{hostname}:11434/v1")
#     # Prompt'ları ayrı değişkenlere atama
#     summary_prompt = prompt_gemini[3][1]  # summary_gpt_prompt metni (elemanın var olduğu index ve o [adi][icerik] kısmını temsil eder )
#     speaker_prompt = prompt_gemini[2][1]  # speaker_gpt_prompt metni

#     # Container'da 3 saat geri olduğu için 3 saat ekliyoruz
#     current_date = datetime.now() + timedelta(hours=3)
    
#     # Eğer mevcut saat (3 saat eklenmiş hali), başlangıç saatinden küçük veya eşitse bekle
#     if current_date <= startdate:
#         db.close()
#         logging.info(f"Sistem saati ({current_date}) var olan başlangıç saat değerinden ({startdate}) büyük olamayacağı için 30 dk uyku modu aktifleştiriliyor ...")
#         time.sleep(1800)
#         continue
        
#     logging.info(f"startdate: {startdate} stopdate {stopdate}")

#     try:
#         data = fetch_data_from_api(startdate, stopdate)
#         if data is None:
#             logging.error("API'ye istekte bulunamadı")
#             continue
        
#         # API'den gelen hata kontrolleri
#         if "error" in data and "code" in data:
#             error_code = data["code"]
#             error_value = data["error"]
#             logging.error(f"Hata kodu '{error_code}' ve Hata Nedeni: '{error_value}'")
#             if error_code == '40':
#                 error_counter +=1
#                 logging.info(f"error_counter: {error_counter}")
                
#             should_continue, error_counter = fetch_api_check_data(error_code,error_counter,stopdate)
#             if should_continue:
#                 logging.warning("Belirtilen aralıkta kayıt bulunamadı, 5 dakika sonra sistem yeniden istekte bulunacaktır.")
#                 time.sleep(30)
#                 continue
#             else:
#                 logging.error("Hata farklı bir nedenden dolayı kaynaklanıyor veya hata limitine ulaşıldı")
#                 break
#         total_records = len(data)
        
#         if not data or "error" in data:
#             logging.error("Veri işleme sırasında hata meydana geldi.")
#             continue

#         # Verileri tarihe göre sırala
#         sorted_data = sorted(data, key=lambda x: datetime.strptime(x['values'][0]['date'].strip(), "%d.%m.%Y %H:%M:%S"))
#         total_records = len(sorted_data)
#         logging.info(f"Toplam kayıt sayısı başlangıçta: {total_records} ve kayıtlar: {sorted_data}")

#         for entry in sorted_data:
#             uniqueid = entry.get('uniqueid')
#             sorted_list = sorted(entry.get('values', []), key=lambda x: datetime.strptime(x['date'].strip(), "%d.%m.%Y %H:%M:%S"))
            
#             for values in sorted_list:
#                 date_str = values.get('date')
#                 if date_str:
#                     date_santral = datetime.strptime(date_str.strip(), "%d.%m.%Y %H:%M:%S")
#                     format_date_santral = date_santral.strftime("%Y-%m-%d %H:%M:%S")
#                     direction_santral = values.get('direction')
#                     source_santral, destination_santral, duration_santral = values.get('source'), values.get('destination'), values.get('duration')
#                     logging.info(f"uniqid: {uniqueid} tarih:{format_date_santral}")
                    
#                     exists = check_uniqueid_exits_santral(cursor, uniqueid, format_date_santral, direction_santral)
#                     if exists:
#                         logging.info(f"Santral Tablosunda Var Atlanıyor -> UniqueID: {uniqueid}, Tarih: {format_date_santral}, Yon: {direction_santral} (Zaten mevcut)")
#                     else:
#                         save_to_db_santral(cursor, uniqueid, format_date_santral, source_santral, destination_santral, direction_santral, duration_santral)
                        
#                         db.commit()
#                         logging.info(f"Santral Tablosuna Eklendi -> UniqueID: {uniqueid}, Tarih: {format_date_santral}, Yon: {direction_santral}")

#                 else:
#                     logging.error(f"Date bilgisi eksik: {entry}")
#                     continue  # Bu kaydı atla

#             logging.info(f"{uniqueid} işleniyor.")
#             time.sleep(5)
#             data_records = process_records(entry)
#             logging.info(f"İşlemler sonucu elde edilen veri listesi: {data_records}")

#             if data_records is not None:
#                 for i, value in enumerate(data_records):
#                     recording_url = value.get('recording')
#                     date = datetime.strptime(value.get('date').strip(), "%d.%m.%Y %H:%M:%S")
#                     format_date = date.strftime("%Y-%m-%d %H:%M:%S")
#                     direction = value.get('direction')
#                     direction = 'GIDEN' if direction == 0 else 'GELEN' if direction == 1 else 'ICARAMA'
#                     source, destination, duration = value.get('source'), value.get('destination'), value.get('duration')

#                     data_db = check_uniqueid_exits(cursor, uniqueid, format_date_santral, direction)
#                     if data_db:
#                         logging.info("CagriTakip Tablosunda Bu kayıt zaten var, atlanıyor")
#                     else:
#                         logging.info(f"""CagriTakip Tablosunda Bu Kayıt yok, işleme alınıyor:
#                                     uniqueid={uniqueid},
#                                     date={format_date_santral},
#                                     direction={direction},
#                                     url={recording_url}
#                                     """)

#                         response_local = send_data_to_local_machine(recording_url, uniqueid, i, hostname)
#                         logging.info(f"\n\n gelen transcript verisi {response_local}\n\n")
#                         try:
#                             # response_local.status_code kontrolü
#                             if response_local and response_local.status_code == 200:
#                                 try:
#                                     # JSON verisini almak
#                                     response_py = response_local.json()
                                    
#                                     # Burada gelen yanıtı logluyoruz
#                                     if 'transcription' in response_py:
#                                         transcript_file = response_py['transcription'] 
#                                         if transcript_file:
#                                             logging.info(f"127.0.0.1:4141/receive_data dönen veri: {transcript_file}")

#                                             # region Transcriptions Parçala Speaker - Özetle
#                                             logging.info(
#                                                 "Transcription type: %s, length: %s, first items: %s",
#                                                 type(transcript_file),
#                                                 len(transcript_file) if hasattr(transcript_file, "__len__") else "len_yok",
#                                                 transcript_file[:2] if isinstance(transcript_file, list) else transcript_file
#                                             )

#                                             # region Transcriptions Parçala Speaker - Özetle
#                                             chunks = preapare_chat_chunk_transcriptions(transcript_file)
#                                             print(f"\n chunks: {chunks}\n")
                                            
#                                             # region gpt - gemini kodları
#                                             #final_analysis_result,chat_response = speaker_analysis(chunks)
#                                             #final_summary_result,chat_summary_response = transcript_summary(chunks)
#                                             #logging.info(f"\n\n final_summary_result: {final_summary_result}\n\n")
                                            
                                            
#                                             # GEMİNİ API ÇAĞIRMA
#                                             #gemini_speaker_result = gemini_speaker(chunks)
#                                             #gemini_transcript_result = gemini_transcript(chunks)
                                            

#                                             #logging.info(f"Gemini Konuşmacı Analizi Sonucu: {gemini_speaker_result}")
#                                             #logging.info(f"Gemini Özet Sonucu: {gemini_transcript_result}")
#                                             # endregion
                                            
#                                             # OLLAMA API ÇAĞIRMA
#                                             ollama_speaker_result = ollama_speaker(chunks,speaker_prompt,ollama_client) 
#                                             ollama_transcript_result = ollama_transcript(chunks,summary_prompt,ollama_client)
                                            

                                            
#                                             logging.info(f"Ollama Konuşma Analiz Metni: {ollama_speaker_result}")
#                                             logging.info(f"Ollama Konuşma Özet Metni: {ollama_transcript_result}")
                                            
                                            
                                                                                        
#                                             # region Add Gemini results to list instead of saving to file
#                                             #add_gemini_results_to_list(uniqueid, format_date, gemini_analysis_result, gemini_speaker_result, gemini_transcript_result)
#                                             # endregion
                                            
#                                             # region Maliyet Hesaplama ve Veri Tabanı Veri Ekleme - Kaydetme İşlemleri
#                                             #costs = calculate_costs(pricing_gpt, gemini_speaker_result, gemini_transcript_result)
#                                             #gpt_cost = costs['total_cost'] # Total cost is now just Gemini cost
#                                             # endregion
                                            
#                                             save_to_db(cursor, uniqueid, format_date, direction, source, destination, duration,ollama_speaker_result,ollama_transcript_result,0)
#                                             db.commit()
#                                         else:
#                                             logging.warning(f"127.0.0.1:4141/receive_data dönen veri boş: {transcript_file}")
#                                     else:
#                                         logging.error(f"Transkript bulunamadı. API yanıtı: {transcript_file}")
#                                 except ValueError:  # Eğer JSON verisi alınmazsa
#                                     logging.error(f"127.0.0.1:4141 cevabı JSON formatında değil.")
#                             else:
#                                 logging.error(f"127.0.0.1:4141 API isteği başarısız oldu. Status code: {response_local.status_code if response_local else 'No response'}")
                                
#                         except Exception as err:   
#                             logging.error(f"127.0.0.1:4141 hata meydana geldi {err}")
#             else:
#                 logging.info(f"{uniqueid} şartları sağlamayan kayıtlar CagriTakip tablosuna işlenmiyor.")
            
#             total_records -= 1
#             logging.info(f"{uniqueid} kaydı Ayarlar tablosundaki tarih kolonu değişikliği işleniyor.")
#             update_last_processed_date(cursor, format_date_santral)
#             db.commit()
#             logging.info(f"total_records: {total_records}")
#             time.sleep(5)
        
#     except Error as e:
#         logging.error(f"Veritabanı hatası: {e}")
        
#     finally:
#         try:
#             # Önce mevcut (eski) bağlantıları güvenli şekilde kapatalım
#             if 'cursor' in locals() and cursor:
#                 cursor.close()
#                 logging.info("Önceki Cursor kapatıldı")
#             if 'db' in locals() and db:
#                 db.close()
#                 logging.info("Önceki Veri tabanı kapatıldı")
#         except Exception as e:
#             logging.error(f"Önceki bağlantılar kapatılırken hata oluştu: {e}")

#         # Yeni veritabanı bağlantısını kurup gerekli sorgulamaları yapalım
#         dbs = None  # Hata durumunda dbs tanımlı kalmalı
#         cursors = None
#         try:
#             dbs = create_connection()
#             if not dbs:
#                 logging.error("Veritabanı bağlantısı kurulamadı, program sonlanıyor.")
#             else:
#                 cursors = dbs.cursor()
#                 new_startdate, new_stopdate = get_startdate(cursors)
#                 logging.info(f"Yeni startdate: {new_startdate} yeni stopdate: {new_stopdate}")

#                 # Eğer önceki startdate ile yeni startdate aynıysa, stopdate'i güncelle
#                 if new_startdate == startdate:
#                     logging.info("Startdate aynı, stopdate güncelleniyor.")
#                     update_last_processed_date(cursors, new_stopdate)
#                     dbs.commit()
#                     logging.info(f"Stopdate güncellendi: {new_stopdate}")
#                 else:
#                     logging.info("Startdate değişti, güncelleme yapılmıyor.")
#         except Exception as e:
#             logging.error(f"Stopdate güncellenirken hata oluştu: {e}")
#         finally:
#             # Yeni bağlantıları güvenli şekilde kapat
#             try:
#                 if cursors:
#                     cursors.close()
#                     logging.info("Yeni Cursor kapatıldı")
#                 if dbs:
#                     dbs.close()
#                     logging.info("Yeni Veri tabanı kapatıldı")
#             except Exception as e:
#                 logging.error(f"Yeni bağlantılar kapatılırken hata oluştu: {e}")

#         logging.info("Veritabanı bağlantısı kapatıldı, sistem 10 dakika uykuya alınıyor...")
#         time.sleep(300)

#     # In the main loop, add check for 16:00 to send results
#     current_time = datetime.now().time().replace(microsecond=0)
#     target_time = dt_time(16, 0)  # 16:00

# region 1 Kütüphaneler
import time
import json
import requests
from datetime import datetime, timedelta, time as dt_time
from mysql.connector import Error
import logging
import smtplib
from openai import OpenAI
from email.mime.text import MIMEText
from database.db import (create_connection, get_startdate, update_last_processed_date, 
                        check_uniqueid_exits_santral, save_to_db_santral, check_uniqueid_exits, 
                        save_to_db, get_hostname,get_ollama_api_key,prompts 
)
from ollama_func import (
    ollama_speaker_analysis_prompt as ollama_speaker, 
    ollama_transcript_summary_prompt as ollama_transcript,
    ollama_diarized_summary_prompt,  # YENİ: Diarization'lı veri için
    ollama_diarized_analysis_prompt   # YENİ: Diarization'lı analiz için
)
# endregion

# region 2 Bağlantı Bilgileri

API_CREDENTIALS = {
    "usercode": "0000000000",
    "password": "FAKE_NETGSM_PASSWORD"
}


# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logging.basicConfig(level=logging.INFO, format="%(asctime)s.%(msecs)02d - %(levelname)s - %(message)s")

# endregion

# region 3 Netgsm Api İsteği
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
            # Eğer hata mesajı varsa direkt döndür
            if isinstance(data, dict) and "error" in data:
                return data
            # Veri varsa parçala ve işle
            elif isinstance(data, list):
                new_api_list = []
                for entry in data:
                    uniqueid = entry.get('uniqueid')
                    values = entry.get('values', [])
                    for value in values:
                        if 'recording' in value:
                            new_entry = {
                                "uniqueid": uniqueid,
                                "values": [value]
                            }
                            new_api_list.append(new_entry)
                return new_api_list
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

# region 4 Netgsm Api'den Dönen Hata Kontrolleri
def fetch_api_check_data(error_code, error_counter, stopdate):
    now = datetime.now()
    
    if error_code == '40':
        if error_counter >= 15:
            logging.warning("15 kez üst üste error_code 40 alındı. Sistem uyku moduna hazırlanıyor.")
            
            # Ertesi gün 8:55'i ayarla
            next_day = now + timedelta(days=1)
            next_run_time = next_day.replace(hour=8, minute=55, second=0, microsecond=0)
            
            # Veritabanını güncelle
            update_last_processed_date(cursor, next_run_time)
            db.commit()
            
            body = f"""
            📌 Sistem 15 kez üst üste <code>40</code> hatası aldı.<br>
            ⏰ Bir sonraki çalışma zamanı: <b>{next_run_time}</b><br>
            💤 Ertesi gün 08:55'e kadar uykuya geçiliyor.<br>
            """
            send_daily_error_mail("⚠️ 15. Hata - Sistem Ertesi Gün 8:55'e Ayarlandı", body)

            # Ertesi gün 08:55'e kadar uykuya geç
            sleep_seconds = (next_run_time - now).total_seconds()
            if sleep_seconds > 0:
                logging.warning(f"{sleep_seconds / 3600:.1f} saat uykuya geçiliyor.")
                time.sleep(sleep_seconds)
            return True, 0  # Sayaç sıfırlanır

        # 15'ten az hata için 5 dakika bekle ve devam et
        logging.warning("Belirtilen aralıkta kayıt bulunamadı, 5 dakika sonra sistem yeniden istekte bulunacaktır.")
        time.sleep(300)
        return True, error_counter
    else:
        # 40 dışında hata varsa dur
        return False, error_counter
# endregion

# region 5 Kurala Uyan İşlenecek Verileri Belirleme 
def process_records(entry):
    recordings = [
        v for v in entry.get("values", [])
        if v.get("recording") and v.get("destination") not in ["0000000000-announcement-OgleArasi", "0000000000-announcement-mesaidisi"]
        and (int(v.get("duration", 0)) >= 25)
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

# region 6 Local'de çalışan enes.y dosyasına gelen yanıtı ekrana basalım
def send_data_to_local_machine(recording_url, uniqueid,index,hostname):
    """
    Bu fonksiyon, verileri local bilgisayarındaki Flask API'ye gönderir.
    """
    try:
        url = f"http://{hostname}:4141/receive_data" # Local bilgisayarınızın IP adresi ve portu
        data = {

            "uniqueid": uniqueid,
            "url": recording_url,
            "i": index,
        }
        
        response = requests.post(url, json=data)
        logging.info(f"response data trascript: {response}")
        
        if response.status_code == 200:
            logging.info("127.0.0.1 sunucusundan başarıyla veri alındı.")
            return response
        else:
            logging.error(f"Failed to send data to local machine. Status code: {response.status_code}")
            return None
    
    except Exception as e:
        logging.error(f"Error while sending data to local machine: {e}")
        return None
# endregion

# region 7 Whisper Sonucunu Parça Parça Speaker Analize Yapma

# def preapare_chat_chunk_transcriptions(transcription_file):
#     max_length = 2000
#     chunks = []
#     current_chunk = []

#     # transcription_file hem (start, end, text) listesi
#     # hem de sadece text listesi (["...", "..."]) olabilir.
#     for item in transcription_file:
#         # Eğer item zaten (start, end, text) üçlüsü ise:
#         if isinstance(item, (list, tuple)) and len(item) == 3:
#             start, end, text = item
#         else:
#             # Sadece string geldiyse start/end'i None kabul edelim
#             start, end, text = None, None, item

#         # Önerilen chunk'ı hazırla
#         proposed_chunk = current_chunk + [(start, end, text)]
#         chunk_length = sum(len(t[2]) for t in proposed_chunk)  # Toplam text uzunluğu

#         if chunk_length > max_length and current_chunk:
#             chunks.append(current_chunk)
#             current_chunk = [(start, end, text)]
#         else:
#             current_chunk.append((start, end, text))

#     if current_chunk:
#         chunks.append(current_chunk)

#     return chunks



# ESKİ FORMAT İÇİN (tuple: start, end, text)
def preapare_chat_chunk_transcriptions(transcription_file):
    """
    ESKİ FORMAT - (start, end, text) tuple listesi için chunk'lara böler.
    """
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


# YENİ FORMAT İÇİN (dict: {"start", "end", "speaker", "text"})
def prepare_diarized_chunks_for_llm(transcription, max_length=2000):
    """
    Diarization'lı transkripsiyon verisini LLM için chunk'lara böler.
    
    Input: [{"start": 3.22, "end": 5.32, "speaker": "SPEAKER_00", "text": "..."}]
    Output: Chunk'lar listesi - her chunk LLM'e gönderilebilir boyutta
    
    Kullanım:
        chunks = prepare_diarized_chunks_for_llm(transcription, max_length=2000)
        for chunk in chunks:
            text = format_chunk_for_llm(chunk)
            # LLM'e gönder...
    """
    chunks = []
    current_chunk = []
    current_length = 0
    
    for segment in transcription:
        # Her segment için metin formatı: "SPEAKER_00: Merhaba..."
        segment_text = f"{segment['speaker']}: {segment['text']}"
        segment_length = len(segment_text)
        
        if current_length + segment_length > max_length and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_length = 0
        
        current_chunk.append(segment)
        current_length += segment_length
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def format_chunk_for_llm(chunk):
    """
    Bir chunk'ı LLM'e gönderilecek metin formatına çevirir.
    
    Input: [{"start": 3.22, "end": 5.32, "speaker": "SPEAKER_00", "text": "Merhaba"}]
    Output: "SPEAKER_00: Merhaba\nSPEAKER_01: Nasılsınız..."
    """
    lines = []
    for seg in chunk:
        lines.append(f"{seg['speaker']}: {seg['text']}")
    return "\n".join(lines)


def format_chunk_for_llm_with_time(chunk):
    """
    Bir chunk'ı zaman bilgisiyle birlikte LLM'e gönderilecek metin formatına çevirir.
    
    Input: [{"start": 3.22, "end": 5.32, "speaker": "SPEAKER_00", "text": "Merhaba"}]
    Output: "[3.22-5.32] SPEAKER_00: Merhaba\n[5.40-8.18] SPEAKER_01: Nasılsınız..."
    """
    lines = []
    for seg in chunk:
        lines.append(f"[{seg['start']:.2f}-{seg['end']:.2f}] {seg['speaker']}: {seg['text']}")
    return "\n".join(lines)


def get_full_transcript_text(transcription):
    """
    Tüm transkripsiyon verisini tek bir metin olarak döndürür.
    Speaker bilgisiyle birlikte.
    
    Input: [{"start": 3.22, "end": 5.32, "speaker": "SPEAKER_00", "text": "Merhaba"}]
    Output: "SPEAKER_00: Merhaba\nSPEAKER_01: Nasılsınız..."
    """
    lines = []
    for seg in transcription:
        lines.append(f"{seg['speaker']}: {seg['text']}")
    return "\n".join(lines)





# endregion

# region 8 GPT ALANI

# region 8 Chat Speaker Prompt
# def speaker_analysis(chunks):
#     all_analysis_results = []
#def speaker_analysis(chunks):
#    all_analysis_results = []
#    chat_response = None  # Açıklama amacıyla buraya ekledik.
#
#    for chunk in chunks:
#        # Konuşmacı ayrıştırma prompt'u
#        prompt = ("""Please analyze the following conversations to isolate the speakers Always use Turkish language. 
#                
#                'Speaker 1' would typically be the operator answering the phone and 'Speaker 2' would be the customer or caller. 
#                Also, organize the conversations in a specific format: 
#                Speaker X: Start: <start>, End: <end>, Text: <text>. 
#                Transcript data:\n
#                
#                 ***Attention***
#                Keep responses as concise and to the point as possible and Always use Turkish language"""
#        )
#
#        for start, end, text in chunk:
#            prompt += f"Start: {start}, End: {end}, Text: {text}\n"
#        try:
#            # OpenAI ChatCompletion isteği gönderme
#            chat_response = client.chat.completions.create(
#                model="gpt-4o-mini",
#                messages=[{"role": "user", "content": prompt}],
#                temperature=0.8,
#                timeout=180
#            )
#            analysis_result = chat_response.choices[0].message.content
#            all_analysis_results.append(analysis_result)
#            logging.info(f"Konuşmacı Analizi Sonucu:\n{analysis_result}")
#            
#        except openai.APIError as err:
#            logging.error(f"API hatası alındı {err.status_code}, mesaj :  {str(err)}")
#            # Hata 500 ise handle_api_error fonksiyonu çağrılacak
#            if err.status_code == 500:
#                handle_api_error(err,'speaker_analysis')
#                return None, None
#        except Exception as e:
#            logging.error(f"Beklenmeyen Hatalar meydana geldi : {e} ")
#
#    final_analysis_result = '\n'.join(all_analysis_results)
#    return final_analysis_result,chat_response
# endregion

# region 9 Chat Özet Prompt
#def transcript_summary(chunks):
# mail_prompt = prompt_gemini[0][1]  # mail_prompt metni


#    # Özetleme prompt'u
#    all_summary_results = []
#    chat_summary_response = None
#    for chunk in chunks:
#
#        prompt_summary = """Make a meaningful and short summary, extract important information and main points using the given text.
#
#                    ***Instructions***
#                    1. Make a general explanation of the speech (purpose of the speech, main topic, etc.).
#                    2. Identify the important points and details that give the essence of the speech.
#                    3. Summarize the main questions and answers given in the interview.
#                    4. Provide information about the decisions taken and their results at the end of the speech.
#                    
#                    ***Output***
#                    - Create a short and understandable summary based on the speech text.
#
#                    ***Attention***
#                    - Summarization should be done in Turkish.
#                    - The summary should be directly related to the content of the text, and no extraneous information should be added.
#                    - Answers should be clear, detailed and easily understandable.
#        """
#        for text in chunk:
#            prompt_summary += f"Text: {text}\n"
#        try:
#            # OpenAI ChatCompletion isteği gönderme
#            chat_summary_response = client.chat.completions.create(
#                model="gpt-4o-mini",
#                messages=[{"role": "user", "content": prompt_summary}],
#                temperature=0.8,
#                timeout=180
#            )
#            summary_result = chat_summary_response.choices[0].message.content
#            all_summary_results.append(summary_result)
#
#            logging.info(f"Transkript Özeti:\n{summary_result}")
#
#        except openai.APIError as err:
#            logging.error(f"API hatası alındı {err.status_code}, mesaj :  {str(err)}")
#            # Hata 500 ise handle_api_error fonksiyonu çağrılacak
#            if err.status_code == 500:
#                handle_api_error(err,'transcript summary:')
#                return None, None
#            
#        except Exception as e:
#            logging.error(f"Beklenmeyen Hatalar meydana geldi : {e} ")
#
#    final_summary_result = '\n'.join(all_summary_results)
#    return final_summary_result,chat_summary_response


# endregion



# region 9 handle_api_error 
def handle_api_error(err, function_name):
    error_message = f"API hatası alındı {err.status_code}, mesaj: {str(err)}"
    logging.error(error_message)
    send_daily_error_mail(f"Meydana gelen hata sonucu konteynırı yeniden başlatın: {function_name}", error_message)
    time.sleep(30)  # 1.5 dakika bekle
    send_daily_error_mail("Sistem Başarıyla Yeniden Başlatıldı", f"{function_name} işlemi 5 dakika bekledikten sonra yeniden çalıştı.")
# endregion 

# region 10 Günlük Hata Kontrol E-Posta Gönderme Fonksiyonu
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

# region 11 Maliyet hesaplaması için gerekli bilgiler
pricing_gpt = {
    "gpt-4o-mini": {
        "input": 0.15,  # Örnek girdi maliyeti
        "cached_input": 0.075, # cahche maliyeti
        "output": 0.60  # Örnek çıktı maliyeti
    },
    "gemini-2.0-flash": {
        "input": 0.00025,  # Gemini input token maliyeti
        "output": 0.0005   # Gemini output token maliyeti
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
    
    # ollama api  reqirements
    hostname = get_hostname(cursor)
    ollama_api_key = get_ollama_api_key(cursor)
    prompt_gemini = prompts(cursor)
    ollama_client = OpenAI(api_key=ollama_api_key,base_url=f"http://{hostname}:11434/v1")
    # Prompt'ları ayrı değişkenlere atama
    summary_prompt = prompt_gemini[3][1]  # summary_gpt_prompt metni (elemanın var olduğu index ve o [adi][icerik] kısmını temsil eder )
    speaker_prompt = prompt_gemini[2][1]  # speaker_gpt_prompt metni

    # Container'da 3 saat geri olduğu için 3 saat ekliyoruz
    current_date = datetime.now() + timedelta(hours=3)
    
    # Eğer mevcut saat (3 saat eklenmiş hali), başlangıç saatinden küçük veya eşitse bekle
    if current_date <= startdate:
        db.close()
        logging.info(f"Sistem saati ({current_date}) var olan başlangıç saat değerinden ({startdate}) büyük olamayacağı için 30 dk uyku modu aktifleştiriliyor ...")
        time.sleep(1800)
        continue
        
    logging.info(f"startdate: {startdate} stopdate {stopdate}")

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
            if error_code == '40':
                error_counter +=1
                logging.info(f"error_counter: {error_counter}")
                
            should_continue, error_counter = fetch_api_check_data(error_code,error_counter,stopdate)
            if should_continue:
                logging.warning("Belirtilen aralıkta kayıt bulunamadı, 5 dakika sonra sistem yeniden istekte bulunacaktır.")
                time.sleep(30)
                continue
            else:
                logging.error("Hata farklı bir nedenden dolayı kaynaklanıyor veya hata limitine ulaşıldı")
                break
        total_records = len(data)
        
        if not data or "error" in data:
            logging.error("Veri işleme sırasında hata meydana geldi.")
            continue

        # Verileri tarihe göre sırala
        sorted_data = sorted(data, key=lambda x: datetime.strptime(x['values'][0]['date'].strip(), "%d.%m.%Y %H:%M:%S"))
        total_records = len(sorted_data)
        logging.info(f"Toplam kayıt sayısı başlangıçta: {total_records} ve kayıtlar: {sorted_data}")

        for entry in sorted_data:
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
            time.sleep(5)
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

                        response_local = send_data_to_local_machine(recording_url, uniqueid, i, hostname)
                        logging.info(f"\n\n gelen transcript verisi {response_local}\n\n")
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
                                            logging.info(f"127.0.0.1:4141/receive_data dönen veri: {transcript_file}")

                                            # region Transcriptions Parçala Speaker - Özetle
                                            # YENİ FORMAT: Diarization'lı veri için chunk'lama
                                            chunks = prepare_diarized_chunks_for_llm(transcript_file, max_length=2000)
                                            logging.info(f"Oluşturulan chunk sayısı: {len(chunks)}")
                                            
                                            
                                            # OLLAMA API ÇAĞIRMA - YENİ FORMAT
                                            ollama_transcript_result = ollama_diarized_summary_prompt(chunks, summary_prompt, ollama_client)
                                            

                                            
                                            logging.info(f"Ollama Özet Sonucu: {ollama_transcript_result}")
                                            logging.info(f"Ollama Konuşma (Spekaer) Analiz Metni: {transcript_file}")
                                            logging.info(f"Ollama Konuşma Özet Metni: {ollama_transcript_result}")
                                            
                                            
                                                                                        
                                            # region Add Gemini results to list instead of saving to file
                                            #add_gemini_results_to_list(uniqueid, format_date, gemini_analysis_result, gemini_speaker_result, gemini_transcript_result)
                                            # endregion
                                            
                                            # region Maliyet Hesaplama ve Veri Tabanı Veri Ekleme - Kaydetme İşlemleri
                                            #costs = calculate_costs(pricing_gpt, gemini_speaker_result, gemini_transcript_result)
                                            #gpt_cost = costs['total_cost'] # Total cost is now just Gemini cost
                                            # endregion
                                            
                                            # transcript_file'ı okunabilir formata çevir
                                            transcript_text = "\n".join([
                                                f"{seg['speaker']}: Start: {seg['start']:.1f}, End: {seg['end']:.1f}, Text: {seg['text']}"
                                                for seg in transcript_file
                                            ])
                                            save_to_db(cursor, uniqueid, format_date, direction, source, destination, duration, transcript_text, ollama_transcript_result, 0)
                                            db.commit()
                                        else:
                                            logging.warning(f"127.0.0.1:4141/receive_data dönen veri boş: {transcript_file}")
                                    else:
                                        logging.error(f"Transkript bulunamadı. API yanıtı: {transcript_file}")
                                except ValueError as e:  # Eğer JSON verisi alınmazsa
                                    logging.error(f"127.0.0.1:4141 cevabı işlenirken hata meydna geldi: {e}")
                            else:
                                logging.error(f"127.0.0.1:4141 API isteği başarısız oldu. Status code: {response_local.status_code if response_local else 'No response'}")
                                
                        except Exception as err:   
                            logging.error(f"127.0.0.1:4141 hata meydana geldi {err}")
            else:
                logging.info(f"{uniqueid} şartları sağlamayan kayıtlar CagriTakip tablosuna işlenmiyor.")
            
            total_records -= 1
            logging.info(f"{uniqueid} kaydı Ayarlar tablosundaki tarih kolonu değişikliği işleniyor.")
            update_last_processed_date(cursor, format_date_santral)
            db.commit()
            logging.info(f"total_records: {total_records}")
            time.sleep(5)
        
    except Error as e:
        logging.error(f"Veritabanı hatası: {e}")
        
    finally:
        try:
            # Önce mevcut (eski) bağlantıları güvenli şekilde kapatalım
            if 'cursor' in locals() and cursor:
                cursor.close()
                logging.info("Önceki Cursor kapatıldı")
            if 'db' in locals() and db:
                db.close()
                logging.info("Önceki Veri tabanı kapatıldı")
        except Exception as e:
            logging.error(f"Önceki bağlantılar kapatılırken hata oluştu: {e}")

        # Yeni veritabanı bağlantısını kurup gerekli sorgulamaları yapalım
        dbs = None  # Hata durumunda dbs tanımlı kalmalı
        cursors = None
        try:
            dbs = create_connection()
            if not dbs:
                logging.error("Veritabanı bağlantısı kurulamadı, program sonlanıyor.")
            else:
                cursors = dbs.cursor()
                new_startdate, new_stopdate = get_startdate(cursors)
                logging.info(f"Yeni startdate: {new_startdate} yeni stopdate: {new_stopdate}")

                # Eğer önceki startdate ile yeni startdate aynıysa, stopdate'i güncelle
                if new_startdate == startdate:
                    logging.info("Startdate aynı, stopdate güncelleniyor.")
                    update_last_processed_date(cursors, new_stopdate)
                    dbs.commit()
                    logging.info(f"Stopdate güncellendi: {new_stopdate}")
                else:
                    logging.info("Startdate değişti, güncelleme yapılmıyor.")
        except Exception as e:
            logging.error(f"Stopdate güncellenirken hata oluştu: {e}")
        finally:
            # Yeni bağlantıları güvenli şekilde kapat
            try:
                if cursors:
                    cursors.close()
                    logging.info("Yeni Cursor kapatıldı")
                if dbs:
                    dbs.close()
                    logging.info("Yeni Veri tabanı kapatıldı")
            except Exception as e:
                logging.error(f"Yeni bağlantılar kapatılırken hata oluştu: {e}")

        logging.info("Veritabanı bağlantısı kapatıldı, sistem 10 dakika uykuya alınıyor...")
        time.sleep(300)

    # In the main loop, add check for 16:00 to send results
    current_time = datetime.now().time().replace(microsecond=0)
    target_time = dt_time(16, 0)  # 16:00




