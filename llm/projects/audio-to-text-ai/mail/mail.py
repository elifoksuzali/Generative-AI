# region 🛠️ Kütüphaneler   
import time,os
import traceback
from datetime import datetime, timedelta, time as dt_time
import mysql.connector
from mysql.connector import Error
import logging
from datetime import date
import google.generativeai as genai
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
import json
import sys


# Add the parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db import prompts, create_connection, get_gpt_api_key
# endregion

# region 🛠️ Log Ayarları
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
# endregion

# region 🛠️ Veri Tabanı Bağlantı Bilgileri
db = create_connection()
cursor = db.cursor()
gemini_key = get_gpt_api_key(cursor)[0]  # Get first record from the results


genai.configure(api_key=gemini_key)

prompt_gemini = prompts(cursor)
system_prompt = prompt_gemini[3][1]  # gemini_mail_prompt metni

# Son mail gönderim tarihini tutmak için değişken
last_mail_sent_date = None

# endregion

# region Set up the model configuration
generation_config = {
    "temperature": 0.8,
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
# endregion

# region 🛠️ Prompt Alanı
#system_prompt = """Aşağıdaki çağrı kaydını analiz et ve içindeki tüm sorunları ayrı ayrı tespit ederek yapılandırılmış bir şekilde özetle.
#
#ÖNEMLİ KURALLAR:
#1. Her sorunu ayrı bir başlık altında analiz et:
#   - Sorun Başlığı: Sorunun kısa ve öz açıklaması
#   - Sorun Detayı: Müşterinin belirttiği sorunu resmi bir dille aktar
#   - Çözüm Önerisi: Temsilcinin verdiği cevabı resmi bir dille aktar
#
#2. Çıktı formatı şu şekilde olmalı:
#   [Sorun Başlığı]
#   Sorun: Müşteri tarafından belirtilen sorun: [Sorunun detaylı açıklaması]
#   Çözüm Önerisi: Temsilci tarafından sunulan çözüm: [Temsilcinin verdiği cevabı resmi bir dille aktar]
#
#3. Analiz kuralları:
#   - Her sorunu ayrı bir başlık altında belirt
#   - Sorunları numaralandır (1, 2, 3, ...)
#   - Temsilcinin cevaplarını resmi bir dille aktar
#   - Teknik terimleri ve özel isimleri doğru kullan
#   - Tüm çıktıyı Türkçe olarak ver
#   - Üçüncü tekil şahıs ağzıyla yaz
#   - Yorum katma, sadece gerçekleri aktar
#
#4. Örnek çıktı formatı:
#   [Domain Yönlendirme Bilgi Eksikliği]
#   Sorun: Müşteri tarafından belirtilen sorun: Domain adresi yönlendirme işlemiyle ilgili bilgi alınamamaktadır ve yönlendirilen yaprak site henüz aktif değildir.
#   Çözüm Önerisi: Temsilci tarafından sunulan çözüm: Yönlendirme işleminin kontrol edilip müşteriye e-posta ile bilgi gönderileceği belirtilmiştir.
#
#   [Bankacılık Belgelerinde Eksiklik]
#   Sorun: Müşteri tarafından belirtilen sorun: Banka işlemleri için gerekli belgelerin eksik olduğu ve bu durumun işlemlerin ilerlemesini engellediği belirtilmiştir.
#   Çözüm Önerisi: Temsilci tarafından sunulan çözüm: Eksik belgelerin tamamlanması gerektiği ve müşteriye liste halinde gönderileceği ifade edilmiştir.
#
#Transkript:
#"""
# endregion



# region 🛠️ Response Format
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


def process_daily_summaries(cursor):
    try:
        cursor.execute("SELECT t.cagriid, t.ozet, t.arayan, t.aranan FROM cagritakip t WHERE  DATE(t.tarih) = CURDATE()")
        # cursor.execute("SELECT t.cagriid, t.ozet, t.arayan, t.aranan FROM cagritakip t WHERE t.tarih BETWEEN '2025-04-25 09:20:07' AND '2025-04-25 10:56:36'")
        #cursor.execute("SELECT t.cagriid, t.ozet, t.arayan, t.aranan FROM cagritakip t WHERE DATE(tarih) = DATE_SUB(CURDATE(), INTERVAL 11 DAY) lIMIT 10")
        #cursor.execute("SELECT ozet FROM cagritakip WHERE DATE(tarih) = CURDATE() and cagriid='sip1-1739516545.15926'")  
        
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

def process_with_gemini(model, formatted_data):
    all_analysis_results = {"items": []}
    
    for data in formatted_data:
        try:
            logging.info(f"İşleniyor: Çağrı ID: {data['cagriid']}")
            logging.info(f"Arayan: {data['arayan']} | Aranan: {data['aranan']}")
            
            prompt = f"{system_prompt}\n\nTranskript:\n{data['ozet']}"
            response = model.generate_content(prompt)
            
            if response and response.text:
                items = []
                current_item = None
                
                for line in response.text.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    
                    if line.startswith('[') and line.endswith(']'):
                        if current_item:
                            items.append(current_item)
                        current_item = {
                            "problem_title": line[1:-1],
                            "problem_content": "",
                            "solution_suggestion": "",
                            "cagriid": data['cagriid'],
                            "arayan": data['arayan'],
                            "aranan": data['aranan']
                        }
                        logging.info(f"Yeni sorun tespit edildi: {line[1:-1]}")
                    elif "Sorun:" in line:
                        if current_item:
                            content = line.split(":", 1)[1].strip() if ":" in line else line
                            current_item["problem_content"] = content
                            logging.info(f"Sorun detayı: {content[:100]}...")
                    elif "Çözüm Önerisi:" in line:
                        if current_item:
                            solution = line.split(":", 1)[1].strip() if ":" in line else line
                            current_item["solution_suggestion"] = solution
                            logging.info(f"Çözüm önerisi: {solution[:100]}...")
                
                if current_item:
                    items.append(current_item)
                
                # Her bir öğeyi resmi dile dönüştür
                for item in items:
                    formal_item = {
                        "problem_title": item["problem_title"],
                        "problem_content": f"Müşteri tarafından belirtilen sorun: {item['problem_content']}",
                        "solution_suggestion": f"Temsilci tarafından sunulan çözüm: {item['solution_suggestion']}",
                        "cagriid": item["cagriid"],
                        "arayan": item["arayan"],
                        "aranan": item["aranan"]
                    }
                    all_analysis_results["items"].append(formal_item)
                
                logging.info(f"Çağrı ID {data['cagriid']} için {len(items)} sorun analiz edildi.")
            else:
                logging.warning(f"Çağrı ID {data['cagriid']} için Gemini'den yanıt alınamadı.")
                
        except Exception as e:
            logging.error(f"❌ Analiz hatası (Çağrı ID: {data['cagriid']}): {e}")
            logging.error(traceback.format_exc())
            continue
    
    return all_analysis_results

def format_response(response):
    if "items" not in response or not response["items"]:
        return "<p>Bugün için işlenecek problem bulunamadı.</p>"
    
    # Çağrı ID'ye göre grupla
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
    
    # Her çağrı için ayrı bölüm oluştur
    for cagriid, group_data in grouped_items.items():
        problems_html = ""
        for i, item in enumerate(group_data["items"], start=1):
            problem_title = item.get("problem_title", "Başlık Bulunamadı")
            problem_content = item.get("problem_content", "Sorun bilgisi bulunamadı.")
            solution_suggestion = item.get("solution_suggestion", "Çözüm bilgisi bulunamadı.")

            problems_html += f"""
                <div style="margin-bottom: 20px;">
                    <p style="margin: 0;"><strong>{i} - {problem_title}</strong></p>
                    <p style="margin: 5px 0;"><strong>Sorun:</strong> {problem_content}</p>
                    <p style="margin: 5px 0;"><strong>Çözüm Önerisi:</strong> {solution_suggestion}</p>
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
        # SMTP ayarları
        smtp_login = "info@example.com"
        smtp_password = "FAKE_SMTP_APP_PASSWORD"
        smtp_host = "smtp.yandex.com"
        smtp_recipients_email_to = ["agent1@example.com","agent2@example.com","agent3@example.com","agent7@example.com","agent5@example.com","agent6@example.com","agent8@example.com"]

        logging.info("SMTP ayarları alındı.")

        # Günün tarihini al
        today_date = datetime.now().strftime("%d %m %Y")
        
        if not analysis_results or not analysis_results.get("items"):
            logging.info("Bugün için özetlenecek kayıt bulunamadı.")
            subject = f'{today_date} Özeti - Veri Yok'
            body = "<p>Bugün için özetlenecek veri bulunamadı.</p>"
        else:
            # Biçimlendirme
            formatted_output = format_response(analysis_results)
            
            # E-posta için içerik oluşturma
            subject = f'{today_date} Gemini Günlük Çağrı Özeti'
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
                <h2>Gemini Günlük Çağrı Özeti</h2>
                {formatted_output}
            </body>
            </html>
            """

        # E-posta gönderimi
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

# Ana döngü
while True:
    try:
        # Veritabanı bağlantısını kontrol et
        db = create_connection()
        if not db:
            logging.error("Veritabanı bağlantısı kurulamadı, 60 saniye bekleniyor...")
            time.sleep(60)
            continue

        cursor = db.cursor()
        
        # Hedef saat kontrolü
        target_time = dt_time(17, 00)  # 20:00'da çalışacak
        now = datetime.now()
        current_time = now.time().replace(microsecond=0)
        today = now.date()

        try:
            if current_time >= target_time and last_mail_sent_date != today:
                logging.info("Günlük özet işlemi başlatılıyor...")
                
                # 1. Verileri topla
                logging.info("Veritabanından kayıtlar alınıyor...")
                records = process_daily_summaries(cursor)
                    
                logging.info("\n" + "="*50)
                logging.info(f"TOPLAM KAYIT SAYISI: {len(records)}")
                logging.info("="*50 + "\n")
                
                # 2. Verileri düzenle
                logging.info("Kayıtlar düzenleniyor...")
                formatted_data = collect_and_format_data(records)
                logging.info(f"{len(formatted_data)} kayıt düzenlendi.")
                
                # 3. Gemini modelini oluştur
                logging.info("Gemini modeli oluşturuluyor...")
                model = genai.GenerativeModel('gemini-2.0-flash',
                                            generation_config=generation_config,
                                            safety_settings=safety_settings)
                logging.info("Gemini modeli başarıyla oluşturuldu.")
                
                # 4. Verileri Gemini ile işle
                logging.info("Kayıtlar Gemini ile analiz ediliyor...")
                analysis_results = process_with_gemini(model, formatted_data)
                logging.info(f"Toplam {len(analysis_results['items'])} sorun analiz edildi.")
                
                # 5. Sonuçları e-posta olarak gönder
                if analysis_results["items"]:
                    logging.info("E-posta gönderimi başlatılıyor...")
                    send_daily_summary_email(analysis_results)
                    logging.info("E-posta başarıyla gönderildi.")
                    last_mail_sent_date = today  # Mail gönderim tarihini güncelle
                else:
                    body_content = "<p>Bugün için işlenecek problem bulunamadı.</p>"
                    subject = f"{today.strftime('%d-%m-%Y')} Günlük Özet - Veri Yok"
                    logging.warning("Gönderilecek analiz sonucu bulunamadı.")
                    
                    send_daily_summary_email(analysis_results)
                    last_mail_sent_date = today  # Mail gönderim tarihini güncelle
                
                logging.info("Günlük özet işlemi tamamlandı.")
            else:
                if last_mail_sent_date == today:
                    logging.info("Bugün için mail zaten gönderilmiş. 24 saat bekleniyor...")
                    time.sleep(86400)
                else:
                    logging.info(f"Hedef saat ({target_time}) bekleniyor...")
                    time.sleep(300)  # 5 dakika bekle
                
        except Exception as e:
            logging.error(f"Günlük özet işlemi sırasında hata oluştu: {e}")
            logging.error(traceback.format_exc())
            time.sleep(300)  # Hata durumunda 5 dakika bekle
            
    except Exception as e:
        logging.error(f"Ana döngüde hata: {e}")
        logging.error(traceback.format_exc())
        time.sleep(300)  # Hata durumunda 5 dakika bekle
        
    finally:
        try:
            cursor.close()
            db.close()
            logging.info("Veritabanı bağlantısı kapatıldı.")
        except Exception as e:
            logging.error(f"Veritabanı bağlantısı kapatılırken hata: {e}")
