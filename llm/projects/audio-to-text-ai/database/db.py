# region 1 Kütüphaneler eklendi
import time
import requests
from datetime import datetime, timedelta, time as dt_time
import mysql.connector
from mysql.connector import Error
import logging
# endregion

# region 2 Bağlantı Bilgileri

DB_CONFIG = {
    "host": "db.example.com",
    "user": "fake_db_user",
    "password": "FAKE_DB_PASSWORD",
    "database": "fake_db_name"
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s.%(msecs)02d - %(levelname)s - %(message)s")

# endregion

# region 3 Veri Tabanından Bilgileri Çekme

def create_connection():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        return connection
    except Error as e:
        logging.error(f"Veri tabanına bağlantı yapılırken hata '{e}' meydana geldi")
        return None

def get_startdate(cursor):
    cursor.execute("SELECT deger FROM ayarlar WHERE anahtar = 'cagriaisonkontrol'")
    result = cursor.fetchone()
    if result and result[0]:
        startdate = datetime.strptime(result[0].strip(), "%Y-%m-%d %H:%M:%S")
        
        stopdate = startdate + timedelta(minutes=30)
        return startdate, stopdate
    else:
        raise ValueError("Veritabanında 'startdate' bulunamadı!")

def get_hostname(cursor):
    cursor.execute("SELECT deger FROM ayarlar WHERE anahtar = 'system_room_base_url'")
    result = cursor.fetchone()
    if result and result[0]:
        hostname = result[0]
        return hostname

    else:
        raise ValueError("Veritabanında 'hostname' alınamadı!")
def get_ollama_api_key(cursor):
    cursor.execute("SELECT deger FROM ayarlar WHERE anahtar = 'ollama_api_key'")
    result = cursor.fetchone()
    if result and result[0]:
        ollama_api_key = result[0]
        return ollama_api_key

    else:
        raise ValueError("Veritabanında 'ollama_api_key' alınamadı!")

def updates_new_date(stopdate):
    new_startdate = stopdate
    new_stopdate = new_startdate + timedelta(minutes=30)
    logging.info(f"Yeni startdate: '{new_startdate}' ve stopdate: '{new_stopdate}'")
    return new_startdate


def update_last_processed_date(cursor, stopdate_sleep_before):
    query = "UPDATE ayarlar SET deger = %s WHERE anahtar = 'cagriaisonkontrol'"
    cursor.execute(query, (stopdate_sleep_before,))


def check_uniqueid_exits_santral(cursor, uniqueid, format_date_santral, direction_santral):
    try:
        query = "SELECT cagriid, tarih, yon FROM cagritakip_santral WHERE cagriid = %s AND tarih = %s AND yon = %s"
        cursor.execute(query, (uniqueid, format_date_santral, direction_santral,))
        logging.info(f"Veri tabanından uniquied sorgusu başarıyla gerçekleşti")
        result = cursor.fetchall()
        return result

    except Exception as err:
        logging.error(f"Veri tabanında uniquied id bilgisi sorgulanırken '{err}' hata meydana geldi")

# bu cagritakip_santral tablosuna kayıt ekler (Çağrı kayıtlarına dair  kayıtları içerir)
def save_to_db_santral(cursor, uniqueid, format_date, source, destination, direction, duration):
    query = """
        INSERT INTO cagritakip_santral (cagriid, tarih, arayan, aranan, yon, sure)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    values = (uniqueid, format_date, source, destination, direction, duration)
    cursor.execute(query, values)


def check_uniqueid_exits(cursor, uniqueid, format_date, direction):
    try:
        query = "SELECT cagriid, tarih, yon FROM cagritakip WHERE cagriid = %s AND tarih = %s AND yon = %s"
        cursor.execute(query, (uniqueid, format_date, direction,))
        logging.info(f"Veri tabanından uniquied sorgusu başarıyla gerçekleşti")
        result = cursor.fetchall()
        return result
    except Exception as err:
        logging.error(f"Veri tabanında uniquied id bilgisi sorgulanırken '{err}' hata meydana geldi")

# bu cagritakip tablosuna kayıt ekler (Çağrı kayıtlarına dair  kayıtlarına ait özet vb bilgileri içeren detaylı biligleri içerir)
def save_to_db(cursor, uniqueid, format_date, direction_text, source, destination, duration,final_analysis_result,summary_result,gpt_cost):
    query = """
        INSERT INTO cagritakip (cagriid, tarih, yon, arayan, aranan, sure, metin,ozet,cost)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    values = (uniqueid, format_date, direction_text, source, destination, duration,final_analysis_result,summary_result,gpt_cost)
    cursor.execute(query, values)




# endregion

# region 4 Gemini ve Openai Promptları
def get_gpt_api_key(cursor):
    cursor.execute("SELECT deger FROM ayarlar WHERE anahtar = 'gpt_api_key' or anahtar = 'gemini_api_key'")
    result = cursor.fetchall()

    if result and result[0]:
        return result[0]
    else:
        raise ValueError("Veritabanında 'gpt_api_key' bulunamadı!")
# endregion

# region 5 Maliyet Hesaplaması
def prompts(cursor):
    cursor.execute("""
                SELECT tip,prompt
                FROM kurum_ai_prompt 
                WHERE tip = 'mail_prompt' or tip = 'summary_gpt_prompt'  or tip = 'speaker_gpt_prompt' or  tip = 'gemini_mail_prompt' 
                """)
    result = cursor.fetchall()

    if result:
        return result
    else:
        raise ValueError("Veritabanında 'prompts' bulunamadı!") 

# endregion
    