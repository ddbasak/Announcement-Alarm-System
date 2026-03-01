import json
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from zeep import Client, Settings



WSDL_URL = 'https://api.ibb.gov.tr/iett/UlasimDinamikVeri/Duyurular.asmx?wsdl'
VERI_DOSYASI = 'kullanicilar.json'


GONDEREN_MAIL = "demirbasak222@gmail.com"
GONDEREN_SIFRE = "haafjnleztcpsevm" 
ALICI_MAIL = "demirbasak222@gmail.com"  

SMTP_SUNUCU = "smtp.gmail.com"
SMTP_PORT = 587
KONTROL_ARALIGI = 300  # Kontrol sıklığı 5 dakika



def veri_yonetimi(yaz=False, veri=None):
    """JSON dosyasından veri okur veya dosyaya veri yazar."""
    if yaz:
        with open(VERI_DOSYASI, 'w', encoding='utf-8') as f:
            json.dump(veri, f, indent=4, ensure_ascii=False)
        return
    
    try:
        with open(VERI_DOSYASI, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {} # Dosya yoksa veya bozuksa boş sözlükle başla
    
    # Gerekli anahtarlar yoksa, boş listelerle oluştur
    if 'takip_edilen_hatlar' not in data:
        data['takip_edilen_hatlar'] = []
    if 'gonderilen_duyurular' not in data:
        data['gonderilen_duyurular'] = []
    return data

def eposta_gonder(konu, govde):
    """Belirtilen konu ve gövde ile e-posta gönderir."""
    try:
        mesaj = MIMEMultipart()
        mesaj["From"] = GONDEREN_MAIL
        mesaj["To"] = ALICI_MAIL
        mesaj["Subject"] = konu
        mesaj.attach(MIMEText(govde, "plain", "utf-8"))

        server = smtplib.SMTP(SMTP_SUNUCU, SMTP_PORT)
        server.starttls()
        server.login(GONDEREN_MAIL, GONDEREN_SIFRE)
        server.sendmail(GONDEREN_MAIL, ALICI_MAIL, mesaj.as_string())
        server.quit()
        print(f"'{konu}' konulu e-posta başarıyla gönderildi.")
    except Exception as e:
        print(f"--- E-POSTA GÖNDERME HATASI: Lütfen ayarları kontrol edin. Hata: {e} ---")



def duyurulari_kontrol_et():
    """Duyuruları kontrol eder ve sonucu tek bir e-posta ile bildirir."""
    print("\nİETT duyuruları kontrol ediliyor...")
    veri = veri_yonetimi()
    takip_edilen_hatlar = veri['takip_edilen_hatlar']

    if not takip_edilen_hatlar:
        print("Takip edilecek hat bulunamadı. Lütfen programı yeniden başlatıp hat ekleyin.")
        return

    yeni_bulunan_duyurular = []
    try:
        client = Client(WSDL_URL, settings=Settings(strict=False))
        # Servisten gelen yanıtı direkt JSON'a çevir
        cevap = json.loads(client.service.GetDuyurular_json())
        
        for duyuru in cevap:
            hat_kodu = duyuru.get('HAT')
            if hat_kodu in takip_edilen_hatlar:
                # Duyuruyu benzersiz yapmak için hat kodu ve mesajı birleştir
                duyuru_kimligi = f"{hat_kodu}-{duyuru.get('MESAJ')}"
                if duyuru_kimligi not in veri['gonderilen_duyurular']:
                    print(f"Yeni duyuru bulundu: {hat_kodu}")
                    yeni_bulunan_duyurular.append(f"HAT: {hat_kodu}\nDUYURU: {duyuru.get('MESAJ')}\n")
                    veri['gonderilen_duyurular'].append(duyuru_kimligi)
    except Exception as e:
        print(f"Web servisinden veri alınamadı, kontrol atlanıyor: {e}")
        return

    # Kontrol sonunda e-posta içeriğini hazırla ve gönder
    if yeni_bulunan_duyurular:
        konu = "İETT - Takip Ettiğiniz Hatlar İçin Yeni Duyurular!"
        govde = "Merhaba,\n\nTakip ettiğiniz hatlar için aşağıdaki yeni duyurular bulundu:\n\n" + "\n".join(yeni_bulunan_duyurular)
    else:
        konu = "İETT - Yeni Duyuru Bulunmadı"
        govde = f"Merhaba,\n\nTakip ettiğiniz '{', '.join(takip_edilen_hatlar)}' hatları için yeni bir duyuru bulunamamıştır. Yeni duyuru paylaşılması durumunda tarafınıza iletilecektir."
        print("Takip edilen hatlar için yeni duyuru yok.")
        
    eposta_gonder(konu, govde)
    veri_yonetimi(yaz=True, veri=veri) # Gönderilenler listesi güncellendiği için veriyi kaydet
    print("Kontrol tamamlandı.")

# PROGRAM BAŞLANGICI

if __name__ == "__main__":
    veri = veri_yonetimi()
    mevcut_hatlar = veri['takip_edilen_hatlar']
    print(f"Mevcut takip edilen hatlar: {', '.join(mevcut_hatlar) if mevcut_hatlar else 'Hiç'}")
    
    girilen_hatlar = input("Takip edilecek hatları girin (örn: GÖKTÜRK- ALIBEYKÖY) veya mevcutu korumak için Enter'a basın: ")
    if girilen_hatlar:
        veri['takip_edilen_hatlar'] = [h.strip().upper() for h in girilen_hatlar.split(',') if h.strip()]
        veri_yonetimi(yaz=True, veri=veri)
        print(f"Takip listesi güncellendi: {', '.join(veri['takip_edilen_hatlar'])}")

    while True:
        duyurulari_kontrol_et()
        print(f"{KONTROL_ARALIGI / 60} dakika sonra tekrar kontrol edilecek...")
        time.sleep(KONTROL_ARALIGI)