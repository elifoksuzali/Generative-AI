

import socket
import json
import time
import uuid


# 📍 NetGSM sunucu bilgileri
HOST = 'crmsntrl.netgsm.com.tr'
PORT = 9110

# 📍 Kullanıcı bilgileriniz
USERNAME = '0000000000'  # <-- Buraya kendi santral numaranı yaz
PASSWORD = 'FAKE_NETGSM_PASSWORD'    # <-- Buraya kendi API şifreni yaz
CRM_ID = str(uuid.uuid4())  # Rastgele benzersiz crm_id üret

# 📍 Login bilgisi JSON olarak hazırlanıyor
login_data = {
    "command": "login",
    "crm_id": CRM_ID,
    "username": USERNAME,
    "password": PASSWORD
}
login_json = json.dumps(login_data)

# 📍 Socket oluşturuluyor
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(10)

try:
    print("➡️ Socket sunucuya bağlanıyor...")
    sock.connect((HOST, PORT))
    print("✅ Bağlantı başarılı.")
    
    # 📍 Login gönderiliyor
    sock.sendall(login_json.encode('utf-8'))
    print("➡️ Login isteği gönderildi.")

    # 📍 Dinleme için dosya açıyoruz
    file_name = f"santral_log_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"
    print(f"📄 Kayıt dosyası: {file_name}")
    f = open(file_name, 'a', encoding='utf-8')

    print("🛜 Santral trafiği dinleniyor...\n")

    while True:
        try:
            data = sock.recv(4096)
            if not data:
                print("❗ Sunucu bağlantıyı kapattı.")
                break
            
            decoded_data = data.decode('utf-8').strip()
            now = time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"[{now}] Gelen Veri: {decoded_data}")

            # 📄 Dosyaya her satırı ayrı ayrı JSONL formatında yazıyoruz
            f.write(decoded_data + "\n")
            f.flush()

        except socket.timeout:
            print("⌛ Bekleniyor... (timeout)")
            continue

except Exception as e:
    print(f"❌ Hata oluştu: {e}")

finally:
    print("🚪 Bağlantı kapatılıyor.")
    sock.close()
    f.close()
