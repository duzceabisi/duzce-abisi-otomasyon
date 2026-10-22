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

MODELLER = ["gemini-flash-lite-latest", "gemini-flash-latest"]
OZET_TALIMAT = (
    "Düzce'nin yerel haber ve hizmet sayfası 'Düzce Abisi' için yazıyorsun. Sana bir haberin başlığı ve kısa açıklaması "
    "verilecek. Yalnızca verilen bilgiyi kullan; isim, sayı, yer ya da ayrıntı UYDURMA. Kaynak sitenin cümlelerini kopyalama, "
    "kendi cümlenle yaz. Abartısız, sade, anlaşılır Türkçe; büyük harfle bağırma, ünlem kullanma. JSON döndür: "
    "{\"baslik\": en fazla 55 karakter, doğru ve dikkat çekici; \"ozet\": en fazla 2 kısa cümle; "
    "\"yer\": geçiyorsa mahalle/köy/ilçe/yol adı, yoksa boş metin}")
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


def ozetle(baslik, aciklama=""):
    s = _cagir(OZET_TALIMAT, f"Başlık: {baslik}\nAçıklama: {aciklama or '-'}", True)
    if not isinstance(s, dict) or not s.get("baslik"):
        return None
    return {"baslik": str(s["baslik"])[:70], "ozet": str(s.get("ozet", ""))[:260], "yer": str(s.get("yer", ""))[:60]}


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
