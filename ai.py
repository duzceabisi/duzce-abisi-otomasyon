#!/usr/bin/env python3
"""Ücretsiz Google Gemini ile haberleri kendi cümlelerimizle özetler.

  ozetle(baslik, aciklama) -> {"baslik", "ozet", "yer"} ya da None
  gunun_ozeti(basliklar)   -> 3-4 cümlelik giriş paragrafı ya da None

Anahtar: GEMINI_API_KEY (ortam değişkeni ya da .env). Önce hızlı ve kotası geniş
flash-lite, olmazsa flash denenir. Hata, kota dolması ya da anahtar yoksa None döner;
çağıran taraf haberin kendi başlığıyla devam eder (sistem durmaz).
"""
import json, sys, time, urllib.error, urllib.request

from gonder import ayar

MODELLER = ["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-flash-latest"]
OZET_TALIMAT = (
    "EN ÖNEMLİ KURAL: Özetteki her bilgi verilen başlıkta, açıklamada ya da metinde AÇIKÇA yazmalı. Yazmayan hiçbir şeyi "
    "ekleme: sebep, ihbar, ekiplerin gelişi, hastaneye kaldırılma, hasar, soruşturma, 'belirlenemeyen neden' gibi ayrıntılar "
    "metinde yoksa yazma. Bilgi azsa özet kısa olur; bu doğrudur. "
    "Düzce'nin yerel haber ve hizmet sayfası 'Düzce Abisi' için haber yazıyorsun. Sana bir haberin başlığı ve varsa haber "
    "metni verilecek. Okuyan kişi haberi başka yere bakmadan tam anlamalı. Metin yeterliyse özet 3-4 cümle olsun; metin "
    "kısaysa 1-2 cümle yeter, uzatmak için cümle ekleme. Metinde varsa şunları "
    "MUTLAKA söylesin: ne oldu; nerede (ilçe, mahalle/köy, cadde); ne zaman; neden ve nasıl oldu; kimler (kurum, ekip; kişi "
    "adları ve yaşları metinde geçiyorsa); sonuç ne oldu ya da bundan sonra ne olacak. Kural, yasak ya da duyuru haberlerinde "
    "yeni mi olduğunu, kimi kapsadığını, ne zamandan geçerli olduğunu ve uymayanlara ne yapılacağını yaz. "
    "Yalnızca metindeki bilgiyi kullan; metinde olmayan bilgiyi UYDURMA: 'ihbar üzerine', 'nedeni belirlenemedi', "
    "'soruşturma başlatıldı', 'hasar tespiti yapılacak', 'can kaybı yok' gibi kalıp ifadeleri metinde yazmıyorsa EKLEME. Kaynak sitenin cümlelerini kopyalama, kendi "
    "cümlenle yaz. Abartısız, sade Türkçe; büyük harfle bağırma, ünlem kullanma. JSON döndür: "
    "{\"baslik\": en fazla 60 karakter, yer adını içersin, doğru ve dikkat çekici; \"ozet\": 3-4 cümle; "
    "\"kisa\": özetin karta sığacak en fazla 170 karakterlik hali (en önemli ayrıntılar: ne, nerede, sonuç); "
    "\"yer\": ilçe ve varsa mahalle/köy (ör. 'Gümüşova, Dededüzü köyü'), yoksa boş metin; "
    "\"duzce\": haber Düzce'de (ilçe, köy, mahalle dahil) geçen bir olay ya da Düzce'yi doğrudan ilgilendiren bir konuysa "
    "true; başka bir ildeki olay ya da Düzce'yle ilgisi olmayan genel/ulusal haber (dünya, magazin, ulusal spor, genel "
    "ekonomi) ise false; metinden anlaşılamıyorsa true; "
    "\"sahne\": haberi temsil eden görsel için İNGİLİZCE kısa sahne tarifi (en fazla 40 kelime): mekân, ışık, atmosfer, "
    "nesneler; insan yüzü, yazı, logo, kan ya da ceset YOK; olayın kendisini değil ortamını anlat (ör. 'rural mountain road "
    "after landslide, muddy asphalt, road workers machinery in distance, overcast morning')}")
GUN_TALIMAT = (
    "Düzce'nin yerel haber sayfası 'Düzce Abisi' için günün kısa özetini yazıyorsun. Sana bugünün haber başlıkları "
    "verilecek. Yalnızca bu başlıklardaki bilgiyi kullan; başlıkta olmayan sebep, sonuç ya da ayrıntı EKLEME. Günün öne çıkanlarını 3-4 akıcı cümlede, "
    "sade Türkçeyle anlat. Liste yapma, başlık ekleme, yalnızca paragrafı döndür.")


def _cagir(talimat, metin, json_mu):
    try:
        anahtar = ayar("GEMINI_API_KEY")
    except SystemExit:
        return None
    govde = {"systemInstruction": {"parts": [{"text": talimat}]}, "contents": [{"parts": [{"text": metin}]}],
             "generationConfig": {"temperature": 0, **({"responseMimeType": "application/json"} if json_mu else {})}}
    for model in MODELLER:
        istek = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                       data=json.dumps(govde).encode(),
                                       headers={"Content-Type": "application/json", "x-goog-api-key": anahtar})
        for tekrar in range(2):
            try:
                with urllib.request.urlopen(istek, timeout=45) as r:
                    cevap = json.load(r)["candidates"][0]["content"]["parts"][0]["text"].strip()
                return json.loads(cevap) if json_mu else cevap
            except (urllib.error.URLError, KeyError, IndexError, ValueError, TimeoutError) as hata:
                print(f"yapay zekâ ({model}) cevap vermedi: {hata}", file=sys.stderr)
                if getattr(hata, "code", None) == 429 and tekrar == 0:  # dakikalık ücretsiz sınır: biraz bekle, tekrar dene
                    time.sleep(20)
                    continue
                break
    return None


def ozetle(baslik, aciklama="", metin=""):
    """metin: haber sayfasının tam metni (varsa). Yoksa yalnızca başlık ve kısa açıklamayla çalışır."""
    s = _cagir(OZET_TALIMAT, f"Başlık: {baslik}\nKısa açıklama: {aciklama or '-'}\nHaber metni: {metin[:4000] or '-'}", True)
    if not isinstance(s, dict) or not s.get("baslik"):
        return None
    return {"baslik": str(s["baslik"])[:75], "ozet": str(s.get("ozet", ""))[:700], "kisa": str(s.get("kisa", ""))[:220],
            "yer": str(s.get("yer", ""))[:60], "duzce": s.get("duzce", True) is not False, "sahne": str(s.get("sahne", ""))[:400]}


AYNI_TALIMAT = (
    "Yerel haber sayfası için tekrar eden haberleri ayıklıyorsun. Sana YENİ bir haber ve daha önce gönderilmiş haberlerin "
    "numaralı listesi verilecek. Yeni haber listedekilerden biriyle AYNI somut olayı mı anlatıyor (aynı kaza, yangın, "
    "olay; aynı yer, kişi ya da ayrıntılar; başka bir sitenin farklı başlıkla verdiği haber ya da olayın devamı)? "
    "Siteler aynı olayı farklı kelimelerle yazar: biri yer adını verir, öbürü vermez. Araç türü, nasıl olduğu "
    "(devrilme, çarpma), yaralı/ölü sayısı, yaşlar ve isimler uyuşuyorsa ve çelişen bir ayrıntı yoksa AYNI olaydır. "
    "Ayrıntılar çelişiyorsa (farklı araç, farklı sayı, farklı yer) ya da yalnızca tür aynıysa farklı olaydır. "
    "JSON döndür: {\"ayni\": eşleşen haberin numarası ya da 0}")


def ayni_olay_mu(yeni, onceki):
    """yeni: 'başlık — açıklama'; onceki: aynı biçimde liste. Eşleşen 1'den başlayan sıra no, yoksa 0 (hata: None)."""
    if not onceki:
        return 0
    liste = "\n".join(f"{i}) {m}" for i, m in enumerate(onceki, 1))
    s = _cagir(AYNI_TALIMAT, f"YENİ: {yeni}\n\nDAHA ÖNCE GÖNDERİLENLER:\n{liste}", True)
    try:
        i = int(s.get("ayni", 0)) if isinstance(s, dict) else None
    except (TypeError, ValueError):
        return None
    return i if i is not None and 0 <= i <= len(onceki) else None


def gunun_ozeti(basliklar):
    if not basliklar:
        return None
    s = _cagir(GUN_TALIMAT, "\n".join(f"- {b}" for b in basliklar), False)
    return s[:700] if isinstance(s, str) and s else None


if __name__ == "__main__":
    print(ozetle("Düzce'de konfeksiyon atölyesinde yangın! Alevlerin yayılması önlendi",
                 "Şıralık Mahallesi'ndeki bir atölyenin elektrik panosunda çıkan yangın itfaiyenin müdahalesiyle söndürüldü."))
    print(gunun_ozeti(["Beyciler Kavşağı'nda otomobil ile motosiklet çarpıştı", "Şıralık'ta atölye yangını söndürüldü",
                       "Düzce'de 5 ilçede planlı elektrik kesintisi"]))
