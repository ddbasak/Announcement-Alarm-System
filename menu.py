import zeep
import json
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import time

WSDL_URL = 'https://api.ibb.gov.tr/iett/UlasimDinamikVeri/Duyurular.asmx?wsdl'

SUBSCRIPTIONS_FILE = 'subscriptions.json'

GONDEREN_MAIL = #... 
GONDEREN_SIFRE = #... 
SMTP_SUNUCU = "smtp.gmail.com"
SMTP_PORT = 587
KONTROL_ARALIGI = 900  


def clear_screen():
    """Ekranı temizler."""
    os.system('cls' if os.name == 'nt' else 'clear')

def load_data():
    """JSON dosyasından kullanıcı verilerini yükler."""
    try:
        with open(SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Dosya yoksa veya bozuksa boş bir sözlükle başla
        return {}

def save_data(data):
    """Verileri JSON dosyasına kaydeder."""
    with open(SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def eposta_gonder(alici_mail, konu, govde):
    """Belirtilen alıcıya, konu ve gövde ile e-posta gönderir."""
    try:
        mesaj = MIMEMultipart()
        mesaj["From"] = GONDEREN_MAIL
        mesaj["To"] = alici_mail
        mesaj["Subject"] = konu
        mesaj.attach(MIMEText(govde, "plain", "utf-8"))

        server = smtplib.SMTP(SMTP_SUNUCU, SMTP_PORT)
        server.starttls()
        server.login(GONDEREN_MAIL, GONDEREN_SIFRE)
        server.sendmail(GONDEREN_MAIL, alici_mail, mesaj.as_string())
        server.quit()
        print(f"-> Bilgilendirme e-postası başarıyla gönderildi: {alici_mail}")
    except Exception as e:
        print(f"--- E-POSTA GÖNDERME HATASI: Lütfen ayarları (e-posta/şifre) kontrol edin. Hata: {e} ---")


def check_and_notify():
    """
    Tüm kayıtlı kullanıcılar için duyuruları kontrol eder ve her kontrol sonunda
    bilgilendirici bir e-posta gönderir.
    """
    print("\nİETT duyuruları kontrol ediliyor...")
    subscriptions = load_data()
    if not subscriptions:
        print("Takip listesinde kayıtlı kullanıcı bulunamadı.")
        return

    try:
        settings = zeep.Settings(strict=False)
        client = zeep.Client(WSDL_URL, settings=settings)
        api_response = client.service.GetDuyurular_json()
        all_announcements = json.loads(api_response)
        print(f"{len(all_announcements)} adet genel duyuru sistemden çekildi.")
    except Exception as e:
        print(f"--- WEB SERVİSİ HATASI: Duyurular alınamadı, kontrol atlanıyor. Hata: {e} ---")
        return

    # Her bir aboneyi döngüye alındı
    for email, user_data in subscriptions.items():
        takip_edilen_hatlar = user_data.get('takip_edilen_hatlar', [])
        gonderilen_duyurular = user_data.get('gonderilen_duyurular', [])
        
        if not takip_edilen_hatlar:
            continue  # Kullanıcının takip ettiği hat yoksa atlandı

        yeni_bulunan_duyurular_mesajlari = []
        
        for duyuru in all_announcements:
            hat_kodu = duyuru.get('HAT')
            if hat_kodu in takip_edilen_hatlar:
                duyuru_kimligi = f"{hat_kodu}-{duyuru.get('MESAJ')}"
                
                if duyuru_kimligi not in gonderilen_duyurular:
                    print(f"Yeni duyuru bulundu -> E-posta: {email}, Hat: {hat_kodu}")
                    mesaj = f"HAT: {hat_kodu}\nDUYURU: {duyuru.get('MESAJ')}\n"
                    yeni_bulunan_duyurular_mesajlari.append(mesaj)
                    user_data['gonderilen_duyurular'].append(duyuru_kimligi)

        # Her kontrol sonunda kullanıcıya bilgilendirme maili gönderilir 
        if yeni_bulunan_duyurular_mesajlari:
            konu = "İETT - Takip Ettiğiniz Hatlar İçin Yeni Duyurular"
            govde = (f"Merhaba,\n\n"
                     f"Takip ettiğiniz hatlar için aşağıdaki yeni duyurular bulundu:\n\n"
                     f"---\n\n"
                     f"{'\n---\n\n'.join(yeni_bulunan_duyurular_mesajlari)}")
            eposta_gonder(email, konu, govde)
        else:
            # Yeni duyuru bulunamadıysa da bilgilendirme maili at
            konu = "İETT - Yeni Duyuru Bulunmadı"
            hatlar_str = ", ".join(takip_edilen_hatlar)
            govde = (f"Merhaba,\n\n"
                     f"Takip ettiğiniz '{hatlar_str}' hatları için yapılan son kontrolde yeni bir duyuru bulunamamıştır.\n\n"
                     f"Yeni bir gelişme olması durumunda tarafınıza bilgi verilecektir.")
            eposta_gonder(email, konu, govde)

    # Güncellenmiş "gonderilen_duyurular" listelerini dosyaya kaydet
    save_data(subscriptions)
    print("Tüm kullanıcılar için kontrol tamamlandı.")


def manage_subscriptions():
    """Kullanıcının e-posta adresini alarak takip listesini yönetmesini sağlar."""
    clear_screen()
    email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    while True:
        email = input("Lütfen e-posta adresinizi girin (Ana menüye dönmek için 'q' yazın): ").strip()
        if email.lower() == 'q':
            return
        if re.fullmatch(email_regex, email):
            break
        else:
            print("!!! Geçersiz e-posta formatı. Lütfen tekrar deneyin. !!!")

    subscriptions = load_data()
    if email not in subscriptions:
        subscriptions[email] = {'takip_edilen_hatlar': [], 'gonderilen_duyurular': []}

    while True:
        clear_screen()
        current_lines = sorted(subscriptions[email]['takip_edilen_hatlar'])
        print(f"Kullanıcı: {email}")
        print(f"Mevcut Takip Listeniz: {', '.join(current_lines) if current_lines else 'Boş'}")
        print("-" * 30)
        print("1. Takip Listeme Hat Ekle")
        print("2. Takip Listemden Hat Çıkar")
        print("3. Ana Menüye Dön")
        choice = input("\nSeçiminiz: ")

        if choice == '1':
            lines_str = input("Eklemek istediğiniz hat kodlarını aralarına virgül koyarak girin (örn: GÖKTÜRK- ALIBEYKÖY):\n-> ").upper()
            lines_to_add = {line.strip() for line in lines_str.split(',') if line.strip()}
            updated_lines = set(current_lines).union(lines_to_add)
            subscriptions[email]['takip_edilen_hatlar'] = sorted(list(updated_lines))
            print(f"\n-> Başarılı! Yeni listeniz: {', '.join(subscriptions[email]['takip_edilen_hatlar'])}")
            save_data(subscriptions)
            time.sleep(2)
        elif choice == '2':
            if not current_lines:
                print("Listenizde çıkarılacak hat bulunmuyor.")
                time.sleep(2); continue
            lines_to_remove_str = input("Çıkarmak istediğiniz hatları girin:\n-> ").upper()
            lines_to_remove = {line.strip() for line in lines_to_remove_str.split(',') if line.strip()}
            updated_lines = set(current_lines) - lines_to_remove
            subscriptions[email]['takip_edilen_hatlar'] = sorted(list(updated_lines))
            print(f"\n-> Başarılı! Yeni listeniz: {', '.join(subscriptions[email]['takip_edilen_hatlar'])}")
            save_data(subscriptions)
            time.sleep(2)
        elif choice == '3':
            break
        else:
            print("Geçersiz seçim.")
            time.sleep(1)


def main_menu():
    """Ana menüyü gösterir ve kullanıcı seçimlerine göre ilgili fonksiyonları çalıştırır."""
    while True:
        clear_screen()
        print("\n===== İETT DUYURU TAKİP SİSTEMİ =====")
        print("1. Hat Takip Listemi Yönet (Ekle/Çıkar)")
        print("2. Duyuruları Şimdi Kontrol Et")
        print(f"3. Otomatik Kontrolü Başlat ({int(KONTROL_ARALIGI / 60)} dk arayla)")
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
                    check_and_notify()
                    next_check_time = time.time() + KONTROL_ARALIGI 
                    print(f"\n--- Sonraki kontrol {time.strftime('%H:%M:%S', time.localtime(next_check_time))} saatinde yapılacak... ---")
                    time.sleep(KONTROL_ARALIGI)
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
