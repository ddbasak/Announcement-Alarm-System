import zeep
import json
import os
import re 
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time

GMAIL_USER = #...
GMAIL_APP_PASSWORD = #...
SUBSCRIPTIONS_FILE = "data.json"
SENT_ANNOUNCEMENTS_FILE = "sent_announcements.json"
WSDL_URL = "https://api.ibb.gov.tr/iett/UlasimDinamikVeri/Duyurular.asmx?wsdl"



def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def load_json_data(filename, default_type=dict):
    if not os.path.exists(filename):
        return default_type()
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return default_type()

def save_json_data(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def send_email(receiver_email, subject, body):
    if GMAIL_USER == #... or GMAIL_APP_PASSWORD == #...:
        print("!!! UYARI: Lütfen dosyadaki GMAIL_USER ve GMAIL_APP_PASSWORD değişkenlerini güncelleyin.")
        return False
    try:
        message = MIMEMultipart()
        message['From'] = GMAIL_USER
        message['To'] = receiver_email
        message['Subject'] = subject
        message.attach(MIMEText(body, 'html'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_USER, receiver_email, message.as_string())
        server.quit()
        print(f"-> E-posta başarıyla gönderildi: {receiver_email}")
        return True
    except Exception as e:
        print(f"HATA: E-posta gönderilemedi. {e}")
        return False

def get_iett_announcements():
    try:
        client = zeep.Client(wsdl=WSDL_URL)
        announcements_str = client.service.GetDuyurular_json()
        return json.loads(announcements_str) if announcements_str else []
    except Exception as e:
        print(f"HATA: İETT duyuruları alınamadı. {e}")
        return None

def is_line_in_title(line_code, title):
    normalized_title = re.sub(r'[^\w\s]', ' ', title.upper())
    normalized_line_code = line_code.upper()
    return normalized_line_code in normalized_title.split()



def check_and_notify():
    clear_screen()
    print(f"\n--- Kontrol Başladı: {time.strftime('%d-%m-%Y %H:%M:%S')} ---")
    
    subscriptions = load_json_data(SUBSCRIPTIONS_FILE, dict)
    if not subscriptions:
        print("Takip edilecek hat bulunamadı. Lütfen önce hat ekleyin.")
        return

    sent_ids = load_json_data(SENT_ANNOUNCEMENTS_FILE, list)
    all_announcements = get_iett_announcements()

    if all_announcements is None:
        return

    newly_sent_ids = []

    for email, tracked_lines in subscriptions.items():
        print(f"\n-> Kullanıcı '{email}' için kontrol ediliyor.")
        
        for line in tracked_lines:
            new_announcement = None
            most_recent_announcement = None

            for ann in all_announcements:
                ann_title = ann.get("DUYURU_BASLIK", "")
                if is_line_in_title(line, ann_title):
                    if most_recent_announcement is None:
                        most_recent_announcement = ann
                    
                    ann_id = str(ann.get("ID"))
                    if ann_id not in sent_ids:
                        new_announcement = ann
                        break
            
            if new_announcement:
                ann_id = str(new_announcement.get("ID"))
                print(f"   + YENİ DUYURU bulundu! Hat: {line}")
                subject = f"YENİ DUYURU: İETT {line} Hattı"
                body = f"""
                <html><body>
                    <h2>Merhaba,</h2>
                    <p>Takip ettiğiniz <b>{line}</b> hattı için YENİ bir duyuru yayınlandı.</p><hr>
                    <h3>{new_announcement.get("DUYURU_BASLIK")}</h3>
                    <p>{new_announcement.get("DUYURU_ICERIK")}</p><hr>
                </body></html>"""
                if send_email(email, subject, body):
                    newly_sent_ids.append(ann_id)
            
            elif most_recent_announcement:
                print(f"   - BİLGİLENDİRME: {line} hattı için yeni duyuru yok. En son bilinen duyuru gönderiliyor.")
                subject = f"ℹBİLGİLENDİRME: İETT {line} Hattı Son Duyuru"
                body = f"""
                <html><body>
                    <h2>Merhaba,</h2>
                    <p>Takip ettiğiniz <b>{line}</b> hattı için yeni bir duyuru <b>bulunmamaktadır.</b></p>
                    <p>Sistemde kayıtlı en güncel duyuru aşağıdadır:</p><hr>
                    <h3>{most_recent_announcement.get("DUYURU_BASLIK")}</h3>
                    <p>{most_recent_announcement.get("DUYURU_ICERIK")}</p><hr>
                </body></html>"""
                send_email(email, subject, body)
            
            else:
                print(f"   - UYARI: {line} hattı için sistemde HİÇ duyuru bulunamadı.")

    if newly_sent_ids:
        final_sent_list = list(set(sent_ids + newly_sent_ids))
        save_json_data(SENT_ANNOUNCEMENTS_FILE, final_sent_list)
        print("\nGönderilen yeni duyurular listesi güncellendi.")

def manage_subscriptions():
    clear_screen()
    subscriptions = load_json_data(SUBSCRIPTIONS_FILE, dict)
    email = input("Lütfen e-posta adresinizi girin: ").strip()
    if not email:
        print("E-posta adresi boş olamaz.")
        return

    if email not in subscriptions:
        subscriptions[email] = []

    while True:
        clear_screen()
        current_lines = sorted(subscriptions[email])
        print(f"E-posta: {email}")
        print(f"Mevcut takip listeniz: {', '.join(current_lines) if current_lines else 'Boş'}")
        print("-" * 30)
        print("1. Takip Listeme Hat Ekle")
        print("2. Takip Listemden Hat Çıkar")
        print("3. Ana Menüye Dön")
        choice = input("\nSeçiminiz: ")

        if choice == '1':
            lines_str = input("Eklemek istediğiniz hatları aralarına virgül koyarak girin:\n-> ").upper()
            lines_to_add = {line.strip() for line in lines_str.split(',') if line.strip()}
            updated_lines = set(current_lines).union(lines_to_add)
            subscriptions[email] = sorted(list(updated_lines))
            print(f"\n-> Başarılı! Yeni listeniz: {', '.join(subscriptions[email])}")
            save_json_data(SUBSCRIPTIONS_FILE, subscriptions)
            time.sleep(2)
        elif choice == '2':
            if not current_lines:
                print("Listenizde çıkarılacak hat bulunmuyor.")
                time.sleep(2); continue
            lines_to_remove_str = input("Çıkarmak istediğiniz hatları girin:\n-> ").upper()
            lines_to_remove = {line.strip() for line in lines_to_remove_str.split(',') if line.strip()}
            updated_lines = set(current_lines) - lines_to_remove
            subscriptions[email] = sorted(list(updated_lines))
            print(f"\n-> Başarılı! Yeni listeniz: {', '.join(subscriptions[email])}")
            save_json_data(SUBSCRIPTIONS_FILE, subscriptions)
            time.sleep(2)
        elif choice == '3':
            break
        else:
            print("Geçersiz seçim.")
            time.sleep(1)

def main_menu():
    while True:
        clear_screen()
        print("\n===== İETT DUYURU ALARM PROJESİ (Tam Sürüm) =====")
        print("1. Hat Takip Listemi Yönet (Ekle/Çıkar)")
        print("2. Duyuruları Şimdi Kontrol Et")
        print("3. Otomatik Kontrolü Başlat (15 dk arayla)")
        print("4. Çıkış")
        
        choice = input("\nSeçiminiz (1-4): ")
        
        if choice == '1':
            manage_subscriptions()
        elif choice == '2':
            check_and_notify()
            input("\nKontrol tamamlandı. Devam etmek için Enter'a basın...")
        
        
        elif choice == '3':
            try:
                clear_screen()
                print("\nOtomatik kontrol başlatıldı. Durdurmak için klavyeden CTRL+C tuşlarına basın.")
                while True:
                    # İlk kontrolü hemen yap
                    check_and_notify()
                    # Bir sonraki kontrolün zamanını hesapla ve bildir
                    next_check_time = time.time() + 900 
                    print(f"\n--- Sonraki kontrol {time.strftime('%H:%M:%S', time.localtime(next_check_time))} civarında yapılacak... ---")
                    # Bekleme süresi
                    time.sleep(900)
            except KeyboardInterrupt:
                print("\n\nOtomatik kontrol kullanıcı tarafından durduruldu. Ana menüye dönülüyor.")
                time.sleep(2)
        

        elif choice == '4':
            print("Programdan çıkılıyor...")
            break
        else:
            print("\n!!! Geçersiz seçim. Lütfen 1 ile 4 arasında bir rakam girin. !!!")
            time.sleep(2)

if __name__ == "__main__":
    main_menu()


