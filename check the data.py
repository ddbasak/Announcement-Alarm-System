import json
from zeep import Client, Settings


WSDL_URL = 'https://api.ibb.gov.tr/iett/UlasimDinamikVeri/Duyurular.asmx?wsdl'

def tum_duyurulari_getir_ve_goster():
    """
    İETT web servisinden tüm güncel duyuruları alır ve ekrana listeler.
    """
    print("İETT web servisinden güncel duyurular alınıyor...")
    
    try:
        settings = Settings(strict=False)
        client = Client(WSDL_URL, settings=settings)
        
        # Servisin GetDuyurular_json metodunu çağırarak veriyi al.
        print("Servis çağrılıyor...")
        json_yaniti = client.service.GetDuyurular_json()
        print("Yanıt alındı, veriler işleniyor...")

        # Servisten dönen JSON metnini Python'un kullanabileceği bir liste/sözlük yapısına çevir.
        duyurular = json.loads(json_yaniti)
        
        # Eğer duyuru listesi boş ise kullanıcıyı bilgilendir.
        if not duyurular:
            print("API'den herhangi bir duyuru alınamadı.")
            return
            
        print(f"\n--- Toplam {len(duyurular)} Adet Güncel Duyuru Bulundu ---\n")
        
        # Her bir duyuruyu numaralandırarak ekrana yazdır.
        for i, duyuru in enumerate(duyurular, 1):
            
            hat = duyuru.get('HAT', 'Genel Duyuru')
            mesaj = duyuru.get('MESAJ', 'İçerik bulunamadı.')
            
            print(f"--- {i}. DUYURU ---")
            print(f"Hat: {hat}")
            print(f"Duyuru: {mesaj}\n")

    except Exception as e:
        # Bağlantı veya veri işleme sırasında bir hata olursa kullanıcıyı bilgilendir.
        print(f"Duyurular alınırken bir hata oluştu: {e}")

if __name__ == "__main__":
    tum_duyurulari_getir_ve_goster()
