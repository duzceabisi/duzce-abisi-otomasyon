#!/usr/bin/env python3
"""Ücretsiz Google Gemini ile haberleri kendi cümlelerimizle özetler.

  ozetle(baslik, aciklama) -> {"baslik", "ozet", "yer"} ya da None
  gunun_ozeti(basliklar)   -> 3-4 cümlelik giriş paragrafı ya da None

Anahtar: GEMINI_API_KEY (ortam değişkeni ya da .env). Önce hızlı ve kotası geniş
flash-lite, olmazsa flash denenir. Hata, kota dolması ya da anahtar yoksa None döner;
çağıran taraf haberin kendi başlığıyla devam eder (sistem durmaz).
"""
import json, sys, urllib.error, urllib.request

from gonder import ayar

MODELLER = ["gemini-flash-lite-latest", "gemini-3.5-flash-lite", "gemini-flash-latest"]
OZET_TALIMAT = (
    "Düzce'nin yerel haber ve hizmet sayfası 'Düzce Abisi' için haber yazıyorsun. Sana bir haberin başlığı ve varsa haber "
    "metni verilecek. Okuyan kişi haberi başka yere bakmadan tam anlamalı. Özet 3-4 cümle olsun ve metinde varsa şunları "
    "MUTLAKA söylesin: ne oldu; nerede (ilçe, mahalle/köy, cadde); ne zaman; neden ve nasıl oldu; kimler (kurum, ekip; kişi "
    "adları ve yaşları metinde geçiyorsa); sonuç ne oldu ya da bundan sonra ne olacak. Kural, yasak ya da duyuru haberlerinde "
    "yeni mi olduğunu, kimi kapsadığını, ne zamandan geçerli olduğunu ve uymayanlara ne yapılacağını yaz. "
    "Yalnızca metindeki bilgiyi kullan; metinde olmayan bilgiyi UYDURMA. Kaynak sitenin cümlelerini kopyalama, kendi "
    "cümlenle yaz. Abartısız, sade Türkçe; büyük harfle bağırma, ünlem kullanma. JSON döndür: "
    "{\"baslik\": en fazla 60 karakter, yer adını içersin, doğru ve dikkat çekici; \"ozet\": 3-4 cümle; "
    "\"kisa\": özetin karta sığacak en fazla 170 karakterlik hali (en önemli ayrıntılar: ne, nerede, sonuç); "
    "\"yer\": ilçe ve varsa mahalle/köy (ör. 'Gümüşova, Dededüzü köyü'), yoksa boş metin; "
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
             "generationConfig": {"temperature": 0.3, **({"responseMimeType": "application/json"} if json_mu else {})}}
    for model in MODELLER:
        istek = urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                       data=json.dumps(govde).encode(),
                                       headers={"Content-Type": "application/json", "x-goog-api-key": anahtar})
        try:
            with urllib.request.urlopen(istek, timeout=45) as r:
                cevap = json.load(r)["candidates"][0]["content"]["parts"][0]["text"].strip()
            return json.loads(cevap) if json_mu else cevap
        except (urllib.error.URLError, KeyError, IndexError, ValueError, TimeoutError) as hata:
            print(f"yapay zekâ ({model}) cevap vermedi: {hata}", file=sys.stderr)
    return None


def ozetle(baslik, aciklama="", metin=""):
    """metin: haber sayfasının tam metni (varsa). Yoksa yalnızca başlık ve kısa açıklamayla çalışır."""
    s = _cagir(OZET_TALIMAT, f"Başlık: {baslik}\nKısa açıklama: {aciklama or '-'}\nHaber metni: {metin[:4000] or '-'}", True)
    if not isinstance(s, dict) or not s.get("baslik"):
        return None
    return {"baslik": str(s["baslik"])[:75], "ozet": str(s.get("ozet", ""))[:700], "kisa": str(s.get("kisa", ""))[:220],
            "yer": str(s.get("yer", ""))[:60], "sahne": str(s.get("sahne", ""))[:400]}


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
