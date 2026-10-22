#!/usr/bin/env python3
"""Haber başlığını kelimelerinden tanıyıp kategoriye ayırır.

Kullanım:  from kategori import sinifla
           sinifla("Düzce'de motosiklet kaldırıma çarptı")
           -> {"kod": "kaza", "etiket": "🚨 KAZA", "onemli": True}

Yeni kelime eklemek için aşağıdaki KATEGORILER listesine yazmak yeterli. Sıra
önemlidir: bir başlık birden fazla kategoriye uyarsa listede önce gelen kazanır
(örneğin "kazada hayatını kaybetti" -> kaza, vefat değil).
Kelimeler başlığın küçük harfli halinde parça olarak aranır: "çarpış" hem
"çarpıştı" hem "çarpışma"yı yakalar. "~" ile başlayan kelime düzenli ifadedir:
"~\\bkaza(?!n)" kaza/kazada/kazası'nı yakalar ama "kazanacak"ı yakalamaz.
"""
import re

# (kod, etiket, önemli mi, kelimeler)
KATEGORILER = [
    ("deprem", "🌍 DEPREM", True, ["deprem", "sarsıntı", "artçı"]),
    ("okul", "🏫 OKUL TATİLİ", True, ["okullar tatil", "tatil edildi", "eğitime ara", "eğitime bir gün ara", "okullar kapalı"]),
    ("hava", "⛈️ HAVA UYARISI", True, ["sağanak", "fırtına", "sel ", "sel!", "selde", "taşkın", "heyelan", "kar yağışı",
                                      "dolu yağ", "meteoroloji", "turuncu kod", "sarı kod", "kırmızı kod", "hortum", "don uyarısı"]),
    ("yangin", "🔥 YANGIN", True, ["yangın", "alevler", "alev al", "itfaiye", "kül oldu", "yandı"]),
    ("kaza", "🚨 KAZA", True, ["~\\bkaza(?!n)", "çarpış", "çarptı", "devrildi", "takla", "şarampole", "refüje", "otomobil ile",
                               "motosiklet", "tır ", "kamyon", "yayaya", "makas att", "savrul", "sürücü", "yaralandı",
                               "yaralı", "kontrolden çık"]),
    ("olum", "🖤 ÖLÜM", True, ["hayatını kaybetti", "ölü bulundu", "cansız beden", "feci ölüm", "öldü", "ölümlü", "can verdi", "acı kayıp", "yaşam savaşını kaybetti", "acı haber"]),
    ("kayip", "🔎 KAYIP", True, ["kayıp", "kayboldu", "aranıyor", "haber alınamıyor", "kaybolan"]),
    ("kesinti", "⚡ KESİNTİ", True, ["elektrik kesinti", "su kesinti", "sular kesil", "elektrikler kesil", "kesinti",
                                    "doğalgaz kesinti", "arıza nedeniyle"]),
    ("asayis", "🚔 ASAYİŞ", False, ["gözaltı", "tutuklan", "operasyon", "uyuşturucu", "silahlı", "bıçak", "darp", "cinayet",
                                   "dolandır", "hırsız", "jandarma", "emniyet", "polis", "yakalandı", "kavga", "birbirine girdi"]),
    ("yol", "🚧 YOL", False, ["trafiğe kapat", "trafiğe açıl", "yol çalışma", "asfalt", "yol kapan", "güzergah", "köprü"]),
    ("vefat", "🕊️ VEFAT", False, ["vefat", "cenaze", "son yolculuğ", "toprağa verildi", "defnedildi"]),
    ("saglik", "🏥 SAĞLIK", False, ["hastane", "sağlık", "doktor", "aşı", "kan bağış", "tarama"]),
    ("ekonomi", "🌰 EKONOMİ", False, ["fındık", "fiyat", "zam", "indirim", "ücret", "maaş", "esnaf", "ihracat", "tso"]),
    ("is", "💼 İŞ / İSTİHDAM", False, ["iş ilanı", "personel alım", "işçi alım", "istihdam", "kontenjan", "iş-kur", "işkur"]),
    ("egitim", "🎓 EĞİTİM", False, ["okul", "öğrenci", "üniversite", "öğretmen", "eğitim", "lise"]),
    ("etkinlik", "🎭 ETKİNLİK", False, ["festival", "konser", "şenlik", "tiyatro", "etkinlik", "sergi", "fuar", "söyleşi", "imza günü"]),
    ("spor", "⚽ SPOR", False, ["düzcespor", "belediyespor", "maç", "galibiyet", "mağlup", "lig", "turnuva", "şampiyon"]),
    ("kurum", "🏛️ KURUM", False, ["belediye", "başkan", "vali", "kaymakam", "muhtar", "meclis", "protokol", "ziyaret"]),
]
GENEL = {"kod": "genel", "etiket": "📰 HABER", "onemli": False}


def eslesir(kelime, b):
    return re.search(kelime[1:], b) if kelime.startswith("~") else kelime in b


def kucuk(metin):
    return metin.replace("İ", "i").replace("I", "ı").lower()


def sinifla(baslik):
    b = kucuk(baslik) + " "
    for kod, etiket, onemli, kelimeler in KATEGORILER:
        if any(eslesir(k, b) for k in kelimeler):
            return {"kod": kod, "etiket": etiket, "onemli": onemli}
    return GENEL


if __name__ == "__main__":
    import sys
    for satir in sys.stdin:
        if satir.strip():
            s = sinifla(satir.strip())
            print(f"{s['etiket']:<22} {'🔴' if s['onemli'] else '  '} {satir.strip()}")
