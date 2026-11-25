# region ESKİ ANA KOD
# # region 🛠️ Kütüphaneler   
# from datetime import datetime, time as dt_time
# import logging,sys,smtplib, os,traceback,time
# from email.mime.text import MIMEText

# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# from database.db import prompts, create_connection, get_ollama_api_key
# # endregion


# # region 🛠️ Log Ayarları
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# # endregion

# # region 🛠️ Veri Tabanı Bağlantı Bilgileri
# from database.db import get_hostname
# from openai import OpenAI


# # Son mail gönderim tarihini tutmak için değişken
# last_mail_sent_date = None

# # endregion


# def process_daily_summaries(cursor):
#     try:
#         cursor.execute("SELECT t.cagriid, t.ozet, t.arayan, t.aranan FROM cagritakip t WHERE  DATE(t.tarih) = CURDATE() limit 5")
#         #cursor.execute("SELECT t.cagriid, t.ozet, t.arayan, t.aranan FROM cagritakip t WHERE t.tarih = '2025-09-09 14:58:18'")
#         #cursor.execute("SELECT t.cagriid, t.ozet, t.arayan, t.aranan FROM cagritakip t WHERE DATE(tarih) = DATE_SUB(CURDATE(), INTERVAL 11 DAY) lIMIT 3")
#         #cursor.execute("SELECT ozet FROM cagritakip WHERE DATE(tarih) = CURDATE() and cagriid='sip1-1739516545.15926'")  
        
#         records = cursor.fetchall()
        
#         if not records:
#             logging.info("ℹ️ Bugün için işlenecek kayıt bulunamadı.")
#             return []

#         return records
        
#     except Exception as e:
#         logging.error(f"❌ Günlük özet işlenirken hata: {e}")
#         logging.error(traceback.format_exc())
#         return []

# def collect_and_format_data(records):
#     formatted_data = []
#     for record in records:
#         formatted_data.append({
#             "cagriid": record[0],
#             "ozet": record[1],
#             "arayan": record[2],
#             "aranan": record[3]
#         })
#     return formatted_data

# def process_with_ollama(hostname,ollama_api_key,formatted_data,system_prompt):
    
#     all_analysis_results = {"items": []}
#     client_ollama = OpenAI(api_key=ollama_api_key,base_url=f"http://{hostname}:11434/v1")
    
#     for data in formatted_data:
#         try:
#             logging.info(f"İşleniyor: Çağrı ID: {data['cagriid']}")
#             logging.info(f"Arayan: {data['arayan']} | Aranan: {data['aranan']}")
            
#             prompt = f"{system_prompt}\n\nTranskript:\n{data['ozet']}"
#             response = client_ollama.chat.completions.create(
#                 model="gpt-oss:20b",
#                 messages=[{"role": "user", "content": prompt}]
#             )
            
#             response_text = response.choices[0].message.content
#             logging.info(f"Ollama Response: {response_text}")
            
#             if response and response_text:
#                 items = []
#                 current_item = None
                
#                 for line in response_text.split('\n'):
#                     line = line.strip()
#                     if not line:
#                         continue
                    
#                     # Sadece gerçek başlık formatlarını yakala
#                     if (line.startswith('[') and line.endswith(']')) or \
#                         line.startswith('Issue ') or \
#                         line.startswith('**[') or \
#                         (line.startswith('1. **') or line.startswith('2. **') or line.startswith('3. **') or line.startswith('4. **') or line.startswith('5. **')) or \
#                         (line.startswith('**') and '**' in line and not line.startswith('**Issues:**') and not line.startswith('**Content:**') and not line.startswith('**Solution Proposal:**')):
                        
#                         if current_item:
#                             items.append(current_item)
                        
#                         # Başlığı temizle
#                         if line.startswith('Issue '):
#                             title = line.split(':', 1)[1].strip() if ':' in line else line
#                         elif line.startswith('**['):
#                             title = line[3:-3]  # **[Title]** -> Title
#                         elif line.startswith('[') and line.endswith(']'):
#                             title = line[1:-1]  # [Title] -> Title
#                         elif line.startswith('1. **') or line.startswith('2. **') or line.startswith('3. **') or line.startswith('4. **') or line.startswith('5. **'):
#                             # 1. **Title** -> Title
#                             title = line.split('**', 2)[1] if '**' in line else line
#                         else:
#                             title = line.replace('**', '').strip()
                        
#                         # Boş başlıkları filtrele
#                         if title and title not in ['Content:', 'Solution Proposal:', 'İŞLER:', 'İletişim Eksikliği']:
#                             current_item = {
#                                 "problem_title": title,
#                                 "problem_content": "",
#                                 "solution_suggestion": "",
#                                 "cagriid": data['cagriid'],
#                                 "arayan": data['arayan'],
#                                 "aranan": data['aranan']
#                             }
#                             logging.info(f"Yeni sorun tespit edildi: {title}")
#                         else:
#                             current_item = None
                        
#                     elif "Content:" in line or "*Content:*" in line:
#                         if current_item:
#                             content = line.split(":", 1)[1].strip() if ":" in line else line
#                             content = content.replace('*', '').strip()
#                             current_item["problem_content"] = content
#                             logging.info(f"Sorun detayı: {content[:100]}...")
                            
#                     elif "Solution Proposal:" in line or "*Solution Proposal:*" in line:
#                         if current_item:
#                             solution = line.split(":", 1)[1].strip() if ":" in line else line
#                             solution = solution.replace('*', '').strip()
#                             current_item["solution_suggestion"] = solution
#                             logging.info(f"Çözüm önerisi: {solution[:100]}...")
                
#                 if current_item:
#                     items.append(current_item)
                
#                 # Her bir öğeyi resmi dile dönüştür ve hemen ekle
#                 for item in items:
#                     formal_item = {
#                         "problem_title": item['problem_title'],
#                         "problem_content": item['problem_content'],
#                         "solution_suggestion": item['solution_suggestion'],
#                         "cagriid": item["cagriid"],
#                         "arayan": item["arayan"],
#                         "aranan": item["aranan"]
#                     }
#                     all_analysis_results["items"].append(formal_item)
                
#                 logging.info(f"Çağrı ID {data['cagriid']} için {len(items)} sorun analiz edildi.")
#                 logging.info(f"Items içeriği: {items}")  # Debug için ekle
#             else:
#                 logging.warning(f"Çağrı ID {data['cagriid']} için Ollama'den yanıt alınamadı.")
                
#         except Exception as e:
#             logging.error(f"❌ Analiz hatası (Çağrı ID: {data['cagriid']}): {e}")
#             logging.error(traceback.format_exc())
#             continue
    
#     return all_analysis_results

# def format_response(response):
#     if "items" not in response or not response["items"]:
#         return "<p>Bugün için işlenecek problem bulunamadı.</p>"
    
#     # Çağrı ID'ye göre grupla
#     grouped_items = {}
#     for item in response["items"]:
#         cagriid = item.get("cagriid", "Bilinmeyen ID")
#         if cagriid not in grouped_items:
#             grouped_items[cagriid] = {
#                 "arayan": item.get("arayan", "Bilinmeyen"),
#                 "aranan": item.get("aranan", "Bilinmeyen"),
#                 "items": []
#             }
#         grouped_items[cagriid]["items"].append(item)
    
#     formatted_sections = []
    
#     # Her çağrı için ayrı bölüm oluştur
#     for cagriid, group_data in grouped_items.items():
#         problems_html = ""
#         for i, item in enumerate(group_data["items"], start=1):
#             problem_title = item.get("problem_title", "Başlık Bulunamadı")
#             problem_content = item.get("problem_content", "Sorun bilgisi bulunamadı.")
#             solution_suggestion = item.get("solution_suggestion", "Çözüm bilgisi bulunamadı.")

#             problems_html += f"""
#                 <div style="margin-bottom: 20px;">
#                     <p style="margin: 0;"><strong>{i} - {problem_title}</strong></p>
#                     <p style="margin: 5px 0;"><strong>Sorun:</strong> {problem_content}</p>
#                     <p style="margin: 5px 0;"><strong>Çözüm Önerisi:</strong> {solution_suggestion}</p>
#                 </div>
#             """

#         formatted_html = f'''
#             <div class="mail-box" style="width: auto; border:1px solid #dedede; box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px; padding: 10px; padding-top: 0; border-radius: 5px;">
#                 <h3 class="konu-baslik" style="color: #2a4d8f; margin-top: 10px;">Konu Başlığı: Çağrı Özeti</h3>
#                 <p class="cagri" style="font-size: 14px;"><strong>Çağrı ID:</strong> {cagriid}</p>
#                 <div class="icerik">
#                     {problems_html}
#                 </div>
#                 <div class="aranan-box" style="width: max-content; padding: 10px; display: flex; gap: 20px; margin-top: 10px; border-radius: 4px; background: #dce4ed !important;">
#                     <p class="arayan" style="margin: unset;"><strong>Arayan:</strong> {group_data['arayan']}</p>
#                     <p class="aranan" style="margin: unset;"><strong>Aranan:</strong> {group_data['aranan']}</p>
#                 </div>
#             </div>
#         '''
#         formatted_sections.append(formatted_html)
    
#     return "<br>".join(formatted_sections)

# def send_daily_summary_email(analysis_results):
#     try:
#         # SMTP ayarları
#         smtp_login = "info@example.com"
#         smtp_password = "FAKE_SMTP_APP_PASSWORD"
#         smtp_host = "smtp.yandex.com"
#         smtp_recipients_email_to = ["agent1@example.com"]#,"agent2@example.com","agent3@example.com","agent7@example.com","agent5@example.com","agent6@example.com","agent8@example.com"]

#         logging.info("SMTP ayarları alındı.")

#         # Günün tarihini al
#         today_date = datetime.now().strftime("%d %m %Y")
        
#         if not analysis_results or not analysis_results.get("items"):
#             logging.info("Bugün için özetlenecek kayıt bulunamadı.")
#             subject = f'{today_date} Özeti - Veri Yok'
#             body = "<p>Bugün için özetlenecek veri bulunamadı.</p>"
#         else:
#             # Biçimlendirme
#             formatted_output = format_response(analysis_results)
            
#             # E-posta için içerik oluşturma
#             subject = f'{today_date} Ollama Günlük Çağrı Özeti'
#             body = f"""
#             <html>
#             <head>
#                 <style>
#                     body {{ font-family: Arial, sans-serif; }}
#                     h3 {{ color: #2c3e50; }}
#                     hr {{ border: 1px solid #eee; }}
#                 </style>
#             </head>
#             <body>
#                 <h2>Ollama Günlük Çağrı Özeti</h2>
#                 {formatted_output}
#             </body>
#             </html>
#             """

#         # E-posta gönderimi
#         msg = MIMEText(body, 'html', 'utf-8')
#         msg['Subject'] = subject
#         msg['From'] = smtp_login
#         msg['To'] = ', '.join(smtp_recipients_email_to)

#         with smtplib.SMTP(smtp_host, 587, timeout=30) as smtp_server:
#             smtp_server.starttls()
#             smtp_server.login(smtp_login, smtp_password)
#             smtp_server.sendmail(smtp_login, smtp_recipients_email_to, msg.as_string())
#             logging.info("Günlük özet e-postası başarıyla gönderildi.")

#     except Exception as e:
#         logging.error(f"E-posta gönderimi sırasında hata oluştu: {e}")
#         logging.error(traceback.format_exc())

# # Ana döngü
# while True:
#     try:
#         # Veritabanı bağlantısını kontrol et
#         db = create_connection()
#         if not db:
#             logging.error("Veritabanı bağlantısı kurulamadı, 60 saniye bekleniyor...")
#             time.sleep(60)
#             continue

#         cursor = db.cursor()
#         hostname = get_hostname(cursor)
#         ollama_api_key = get_ollama_api_key(cursor)
        
#         system_prompt = prompts(cursor)[1][1]
            
#         # Hedef saat kontrolü
#         target_time = dt_time(14, 30)  # 20:30'da çalışacak
#         now = datetime.now()
#         current_time = now.time().replace(microsecond=0)
#         today = now.date()

#         try:
#             if current_time >= target_time and last_mail_sent_date != today:
#                 logging.info("Günlük özet işlemi başlatılıyor...")
                
#                 # 1. Verileri topla
#                 logging.info("Veritabanından kayıtlar alınıyor...")
#                 records = process_daily_summaries(cursor)
                    
#                 logging.info("\n" + "="*50)
#                 logging.info(f"TOPLAM KAYIT SAYISI: {len(records)}")
#                 logging.info("="*50 + "\n")
                
#                 # 2. Verileri düzenle
#                 logging.info("Kayıtlar düzenleniyor...")
#                 formatted_data = collect_and_format_data(records)
#                 logging.info(f"{len(formatted_data)} kayıt düzenlendi.")
                

#                 # 3. Ollama  modelini oluştur ve 4. Verileri Ollama ile işle
#                 logging.info("Kayıtlar Ollama ile analiz ediliyor...")
#                 analysis_results = process_with_ollama(hostname,ollama_api_key,formatted_data,system_prompt)
#                 logging.info(f"Toplam {len(analysis_results['items'])} sorun analiz edildi.")
                
#                 # 5. Sonuçları e-posta olarak gönder
#                 if analysis_results["items"]:
#                     logging.info("E-posta gönderimi başlatılıyor...")
#                     send_daily_summary_email(analysis_results)
#                     logging.info("E-posta başarıyla gönderildi.")
#                     last_mail_sent_date = today  # Mail gönderim tarihini güncelle
#                 else:
#                     body_content = "<p>Bugün için işlenecek problem bulunamadı.</p>"
#                     subject = f"{today.strftime('%d-%m-%Y')} Günlük Özet - Veri Yok"
#                     logging.warning("Gönderilecek analiz sonucu bulunamadı.")
                    
#                     send_daily_summary_email(analysis_results)
#                     last_mail_sent_date = today  # Mail gönderim tarihini güncelle
                
#                 logging.info("Günlük özet işlemi tamamlandı.")
#             else:
#                 if last_mail_sent_date == today:
#                     logging.info("Bugün için mail zaten gönderilmiş. 24 saat bekleniyor...")
#                     time.sleep(86400)
#                 else:
#                     logging.info(f"Hedef saat ({target_time}) bekleniyor...")
#                     time.sleep(300)  # 5 dakika bekle
                
#         except Exception as e:
#             logging.error(f"Günlük özet işlemi sırasında hata oluştu: {e}")
#             logging.error(traceback.format_exc())
#             time.sleep(300)  # Hata durumunda 5 dakika bekle
            
#     except Exception as e:
#         logging.error(f"Ana döngüde hata: {e}")
#         logging.error(traceback.format_exc())
#         time.sleep(300)  # Hata durumunda 5 dakika bekle
        
#     finally:
#         try:
#             cursor.close()
#             db.close()
#             logging.info("Veritabanı bağlantısı kapatıldı.")
#         except Exception as e:
#             logging.error(f"Veritabanı bağlantısı kapatılırken hata: {e}")


# endregion

# region 🛠️ Kütüphaneler   
from datetime import datetime, time as dt_time
import logging, sys, smtplib, os, traceback, time, json, re
from email.mime.text import MIMEText

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import prompts, create_connection, get_ollama_api_key
# endregion

# region 🛠️ Log Ayarları
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# endregion

# region 🛠️ Veri Tabanı Bağlantı Bilgileri
from database.db import get_hostname
from openai import OpenAI
from pydantic import BaseModel, ValidationError
from typing import List
# endregion

# Pydantic şema
class ResponseItem(BaseModel):
    problem_title: str
    problem_content: str
    solution_suggestion: str

class ResponseFormat(BaseModel):
    items: List[ResponseItem]

# Son mail gönderim tarihini tutmak için değişken
last_mail_sent_date = None


def process_daily_summaries(cursor):
    try:
        cursor.execute("SELECT t.cagriid, t.ozet, t.arayan, t.aranan FROM cagritakip t WHERE DATE(t.tarih) = CURDATE()")

        records = cursor.fetchall()

        if not records:
            logging.info("ℹ️ Bugün için işlenecek kayıt bulunamadı.")
            return []

        return records

    except Exception as e:
        logging.error(f"❌ Günlük özet işlenirken hata: {e}")
        logging.error(traceback.format_exc())
        return []


def collect_and_format_data(records):
    formatted_data = []
    for record in records:
        formatted_data.append({
            "cagriid": record[0],
            "ozet": record[1],
            "arayan": record[2],
            "aranan": record[3]
        })
    return formatted_data


#region ESKİ FONKSİYON KODU
# ------------------------------------------------------
# 🔥 YENİ OLLAMA PARSER — SADECE JSON FORMATINI OKUR
# ------------------------------------------------------
# def process_with_ollama(hostname, ollama_api_key, formatted_data, system_prompt):

#     all_analysis_results = {"items": [],"empty_items": 0}
#     client_ollama = OpenAI(api_key=ollama_api_key, base_url=f"http://{hostname}:11434/v1")

#     for data in formatted_data:
#         try:
#             logging.info(f"İşleniyor: Çağrı ID: {data['cagriid']}")
#             logging.info(f"Arayan: {data['arayan']} | Aranan: {data['aranan']}")

#             prompt = f"{system_prompt}\n\nTranskript:\n{data['ozet']}"

#             response = client_ollama.chat.completions.create(
#                 model="gpt-oss:20b",
#                 messages=[{"role": "user", "content": prompt}]
#             )

#             response_text = response.choices[0].message.content.strip()
#             logging.info(f"Ollama Response: {response_text}")

#             # ---------------------------
#             # 1) JSON OBJESİNİ AYIKLA
#             # ---------------------------
#             json_match = re.search(r'\[.*\]|\{.*\}', response_text, re.DOTALL)
#             if not json_match:
#                 logging.error("JSON bulunamadı.")
#                 continue

#             clean_json = json_match.group(0)

#             # ---------------------------
#             # 2) JSON PARSE ET
#             # ---------------------------
#             try:
#                 parsed_json = json.loads(clean_json)
#             except Exception as e:
#                 logging.error(f"JSON parse hatası: {e}")
#                 continue

#             # Eğer tek obje geldiyse dizi haline getir
#             if isinstance(parsed_json, dict):
#                 parsed_json = {"items": [parsed_json]}
#             else:
#                 parsed_json = {"items": parsed_json}

#             # ---------------------------
#             # 3) PYDANTIC VALIDATION
#             # ---------------------------
#             try:
#                 validated = ResponseFormat(**parsed_json)
#             except ValidationError as e:
#                 logging.error(f"Pydantic doğrulama hatası: {e}")
#                 continue

#             # ---------------------------
#             # 4) KAYDET
#             # ---------------------------
#             for item in validated.items:
#                 all_analysis_results["items"].append({
#                     "problem_title": item.problem_title,
#                     "problem_content": item.problem_content,
#                     "solution_suggestion": item.solution_suggestion,
#                     "cagriid": data["cagriid"],
#                     "arayan": data["arayan"],
#                     "aranan": data["aranan"]
#                 })

#             logging.info(f"{data['cagriid']} için {len(validated.items)} adet sorun işlendi.")

#         except Exception as e:
#             logging.error(f"İşleme hatası {data['cagriid']}: {e}")
#             logging.error(traceback.format_exc())
#             continue

#     return all_analysis_results
# endregion


def process_with_ollama(hostname, ollama_api_key, formatted_data, system_prompt):

    all_analysis_results = {"items": [], "empty_items": 0}
    client_ollama = OpenAI(api_key=ollama_api_key, base_url=f"http://{hostname}:11434/v1")

    for data in formatted_data:

        # -----------------------------------------
        # 1) None veya boş özet kontrolü
        # -----------------------------------------
        if data["ozet"] is None or data["ozet"].strip() == "":
            logging.info(f"Boş veya None özet atlandı: {data['cagriid']}")
            all_analysis_results["empty_items"] += 1
            continue

        # -----------------------------------------
        # 2) Altyazı M.K. gibi gereksiz kayıtları tamamen atla
        # -----------------------------------------
        if data["ozet"].strip().lower().startswith("altyazı") or "altyazı" in data["ozet"].lower():
            logging.info(f"Gereksiz Altyazı kaydı atlandı: {data['cagriid']}")
            all_analysis_results["empty_items"] += 1
            continue

        try:
            logging.info(f"İşleniyor: Çağrı ID: {data['cagriid']}")
            logging.info(f"Arayan: {data['arayan']} | Aranan: {data['aranan']}")

            prompt = f"{system_prompt}\n\nTranskript:\n{data['ozet']}"

            response = client_ollama.chat.completions.create(
                model="gpt-oss:20b",
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = response.choices[0].message.content.strip()
            logging.info(f"Ollama Response: {response_text}")

            # ---------------------------
            # 3) JSON OBJESİNİ AYIKLA
            # ---------------------------
            json_match = re.search(r'\[.*\]|\{.*\}', response_text, re.DOTALL)
            if not json_match:
                logging.error("JSON bulunamadı.")
                all_analysis_results["empty_items"] += 1
                continue

            clean_json = json_match.group(0)

            try:
                parsed_json = json.loads(clean_json)
            except Exception as e:
                logging.error(f"JSON parse hatası: {e}")
                all_analysis_results["empty_items"] += 1
                continue

            if isinstance(parsed_json, dict):
                parsed_json = {"items": [parsed_json]}
            else:
                parsed_json = {"items": parsed_json}

            try:
                validated = ResponseFormat(**parsed_json)
            except ValidationError as e:
                logging.error(f"Pydantic doğrulama hatası: {e}")
                all_analysis_results["empty_items"] += 1
                continue

            # ---------------------------
            # 4) BOŞ VEYA EKSİK KAYITLARI FİLTRELE
            # ---------------------------
            for item in validated.items:

                title = item.problem_title.strip()
                content = item.problem_content.strip()
                solution = item.solution_suggestion.strip()

                # Eğer üçünden biri bile boşsa listeye ekleme
                if title == "" or content == "" or solution == "":
                    logging.info(f"Boş veya eksik kayıt atlandı: {data['cagriid']}")
                    all_analysis_results["empty_items"] += 1
                    continue

                # NORMAL, TAM, DOLU, GEÇERLİ KAYIT EKLE
                all_analysis_results["items"].append({
                    "problem_title": title,
                    "problem_content": content,
                    "solution_suggestion": solution,
                    "cagriid": data["cagriid"],
                    "arayan": data["arayan"],
                    "aranan": data["aranan"]
                })

            logging.info(f"{data['cagriid']} için geçerli {len(validated.items)} adet sorun işlendi.")

        except Exception as e:
            logging.error(f"İşleme hatası {data['cagriid']}: {e}")
            logging.error(traceback.format_exc())
            all_analysis_results["empty_items"] += 1
            continue

    return all_analysis_results


def format_response(response):
    if "items" not in response or not response["items"]:
        return "<p>Bugün için işlenecek problem bulunamadı.</p>"

    grouped_items = {}
    for item in response["items"]:
        cagriid = item.get("cagriid", "Bilinmeyen ID")
        if cagriid not in grouped_items:
            grouped_items[cagriid] = {
                "arayan": item.get("arayan", "Bilinmeyen"),
                "aranan": item.get("aranan", "Bilinmeyen"),
                "items": []
            }
        grouped_items[cagriid]["items"].append(item)

    formatted_sections = []

    for cagriid, group_data in grouped_items.items():
        problems_html = ""
        for i, item in enumerate(group_data["items"], start=1):
            problems_html += f"""
                <div style="margin-bottom: 20px;">
                    <p style="margin: 0;"><strong>{i} - {item['problem_title']}</strong></p>
                    <p style="margin: 5px 0;"><strong>Sorun:</strong> {item['problem_content']}</p>
                    <p style="margin: 5px 0;"><strong>Çözüm Önerisi:</strong> {item['solution_suggestion']}</p>
                </div>
            """

        formatted_html = f'''
            <div class="mail-box" style="width: auto; border:1px solid #dedede; box-shadow: rgba(50, 50, 93, 0.25) 0px 2px 5px -1px, rgba(0, 0, 0, 0.3) 0px 1px 3px -1px; padding: 10px; padding-top: 0; border-radius: 5px;">
                <h3 class="konu-baslik" style="color: #2a4d8f; margin-top: 10px;">Konu Başlığı: Çağrı Özeti</h3>
                <p class="cagri" style="font-size: 14px;"><strong>Çağrı ID:</strong> {cagriid}</p>
                <div class="icerik">
                    {problems_html}
                </div>
                <div class="aranan-box" style="width: max-content; padding: 10px; display: flex; gap: 20px; margin-top: 10px; border-radius: 4px; background: #dce4ed !important;">
                    <p class="arayan" style="margin: unset;"><strong>Arayan:</strong> {group_data['arayan']}</p>
                    <p class="aranan" style="margin: unset;"><strong>Aranan:</strong> {group_data['aranan']}</p>
                </div>
            </div>
        '''
        formatted_sections.append(formatted_html)

    return "<br>".join(formatted_sections)


def send_daily_summary_email(analysis_results):
    try:
        smtp_login = "info@example.com"
        smtp_password = "FAKE_SMTP_APP_PASSWORD"
        smtp_host = "smtp.yandex.com"
        #smtp_recipients_email_to = ["agent1@example.com"]
        smtp_recipients_email_to = ["agent1@example.com","agent2@example.com","agent3@example.com","agent4@example.com","agent5@example.com"]


        logging.info("SMTP ayarları alındı.")

        today_date = datetime.now().strftime("%d %m %Y")

        if not analysis_results or not analysis_results.get("items"):
            logging.info("Bugün için özetlenecek kayıt bulunamadı.")
            subject = f'{today_date} Özeti - Veri Yok'
            body = "<p>Bugün için özetlenecek veri bulunamadı.</p>"
        else:
            formatted_output = format_response(analysis_results)

            subject = f'{today_date} Ollama Günlük Çağrı Özeti'
            body = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; }}
                    h3 {{ color: #2c3e50; }}
                    hr {{ border: 1px solid #eee; }}
                </style>
            </head>
            <body>
                <h2>Ollama Günlük Çağrı Özeti</h2>
                {formatted_output}
            </body>
            </html>
            """

        msg = MIMEText(body, 'html', 'utf-8')
        msg['Subject'] = subject
        msg['From'] = smtp_login
        msg['To'] = ', '.join(smtp_recipients_email_to)

        with smtplib.SMTP(smtp_host, 587, timeout=30) as smtp_server:
            smtp_server.starttls()
            smtp_server.login(smtp_login, smtp_password)
            smtp_server.sendmail(smtp_login, smtp_recipients_email_to, msg.as_string())
            logging.info("Günlük özet e-postası başarıyla gönderildi.")

    except Exception as e:
        logging.error(f"E-posta gönderimi sırasında hata oluştu: {e}")
        logging.error(traceback.format_exc())


# ------------------------------------------------------
#                   🔥 MAIN LOOP
# ------------------------------------------------------
while True:
    try:
        db = create_connection()
        if not db:
            logging.error("Veritabanı bağlantısı kurulamadı, 60 saniye bekleniyor...")
            time.sleep(60)
            continue

        cursor = db.cursor()
        hostname = get_hostname(cursor)
        ollama_api_key = get_ollama_api_key(cursor)
        system_prompt = prompts(cursor)[1][1]

        target_time = dt_time(17, 30)
        now = datetime.now()
        current_time = now.time().replace(microsecond=0)
        today = now.date()

        try:
            if current_time >= target_time and last_mail_sent_date != today:
                logging.info("Günlük özet işlemi başlatılıyor...")

                logging.info("Veritabanından kayıtlar alınıyor...")
                records = process_daily_summaries(cursor)

                logging.info("\n" + "="*50)
                logging.info(f"TOPLAM KAYIT SAYISI: {len(records)}")
                logging.info("="*50 + "\n")

                formatted_data = collect_and_format_data(records)

                logging.info(f"{len(formatted_data)} kayıt düzenlendi.")

                logging.info("Kayıtlar Ollama ile analiz ediliyor...")
                analysis_results = process_with_ollama(hostname, ollama_api_key, formatted_data, system_prompt)

                logging.info(f"Toplam {len(analysis_results['items'])} sorun analiz edildi.")

                send_daily_summary_email(analysis_results)
                last_mail_sent_date = today

                logging.info("Günlük özet işlemi tamamlandı.")
            else:
                if last_mail_sent_date == today:
                    logging.info("Bugün için mail zaten gönderilmiş. 24 saat bekleniyor...")
                    time.sleep(86400)
                else:
                    logging.info(f"Hedef saat ({target_time}) bekleniyor...")
                    time.sleep(300)

        except Exception as e:
            logging.error(f"Günlük özet işlemi sırasında hata oluştu: {e}")
            logging.error(traceback.format_exc())
            time.sleep(300)

    except Exception as e:
        logging.error(f"Ana döngüde hata: {e}")
        logging.error(traceback.format_exc())
        time.sleep(300)

    finally:
        try:
            cursor.close()
            db.close()
            logging.info("Veritabanı bağlantısı kapatıldı.")
        except Exception as e:
            logging.error(f"Veritabanı bağlantısı kapatılırken hata: {e}")
