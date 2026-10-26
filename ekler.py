#!/usr/bin/env python3
"""Günlük paylaşımlar için ek veri kaynakları.

  namaz()          Diyanet (yedek: Aladhan, Diyanet yöntemi): Düzce namaz vakitleri
  tarihte_bugun()  Vikipedi: bugünün tarihî olayları ve özel günleri
  depremler()      Kandilli Rasathanesi: son depremler (Düzce ve çevresi süzülür deprem.py'de)
"""
import html, json, re, urllib.parse, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Istanbul")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"}
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
TURKIYE = re.compile(r"Türk|Osmanlı|Atatürk|Mustafa Kemal|TBMM|Ankara|İstanbul|İzmir|Düzce|Cumhuriyet|Anadolu|Kurtuluş")


def getir(url, ua=UA):
    with urllib.request.urlopen(urllib.request.Request(url, headers=ua), timeout=25) as r:
        return r.read()


def namaz():
    """Önce Diyanet; iki denemede de olmazsa Aladhan (Diyanet hesap yöntemi, en fazla ~1 dk fark)."""
    for deneme in range(2):
        try:
            return namaz_diyanet()
        except Exception as hata:
            son_hata = hata
    try:
        return namaz_aladhan()
    except Exception:
        raise son_hata


def namaz_aladhan():
    bugun = datetime.now(TZ).strftime("%d-%m-%Y")
    v = json.loads(getir(f"https://api.aladhan.com/v1/timings/{bugun}?latitude=40.8438&longitude=31.1565&method=13"))["data"]["timings"]
    return [[ad, v[k][:5]] for ad, k in [("İmsak", "Fajr"), ("Güneş", "Sunrise"), ("Öğle", "Dhuhr"),
                                         ("İkindi", "Asr"), ("Akşam", "Maghrib"), ("Yatsı", "Isha")]]


def namaz_diyanet():
    # 9414 = Düzce merkez (9378 Osmancık'tır, karıştırma)
    s = getir("https://namazvakitleri.diyanet.gov.tr/tr-TR/9414/duzce-namaz-vakitleri").decode("utf-8", "replace")
    vakit = {html.unescape(a).strip(): b.strip() for a, b in re.findall(
        r'<div class="tpt-title">\s*([^<]+?)\s*</div>\s*<div class="tpt-time">\s*([^<]+?)\s*</div>', s)}
    if "İmsak" not in vakit:  # imsak tabloda değil, sayfanın soru-cevap kısmında yazıyor
        m = re.search(r"imsak vakti (\d{2}:\d{2})", s)
        if m:
            vakit["İmsak"] = m.group(1)
    if "Düzce" not in s[:5000]:
        raise ValueError("Diyanet sayfası Düzce'ye ait değil")
    sira = ["İmsak", "Güneş", "Öğle", "İkindi", "Akşam", "Yatsı"]
    liste = [[ad, vakit[ad]] for ad in sira if ad in vakit]
    if len(liste) < 5:
        raise ValueError("namaz vakitleri okunamadı")
    return liste


def _vikimetin(satir):
    satir = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", satir)          # [[a|b]] -> b
    satir = re.sub(r"\{\{[^}]*\}\}|<ref[^>]*>.*?</ref>|<ref[^/]*/>|'''?", "", satir)
    return html.unescape(re.sub(r"<[^>]+>", "", satir)).strip()


def tarihte_bugun(gun=None):
    gun = gun or datetime.now(TZ)
    sayfa = urllib.parse.quote(f"{gun.day}_{AYLAR[gun.month - 1]}")
    w = json.loads(getir(f"https://tr.wikipedia.org/w/api.php?action=parse&page={sayfa}&prop=wikitext&format=json&formatversion=2",
                         {"User-Agent": "DuzceAbisiBot/1.0 (Telegram bildirim botu)"}))["parse"]["wikitext"]

    def bolum(ad):
        m = re.search(rf"==\s*{ad}\s*==(.*?)(?:\n==[^=]|\Z)", w, re.S)
        return [l[1:].strip() for l in (m.group(1).splitlines() if m else []) if l.startswith("*")]

    olaylar = []
    for l in bolum("Olaylar"):
        m = re.match(r"\[\[(\d{3,4})\]\]\s*[-–]\s*(.+)", l)
        if m:
            olaylar.append([m.group(1), _vikimetin(m.group(2))])
    tr = [o for o in olaylar if TURKIYE.search(o[1])]
    diger = [o for o in olaylar if o not in tr]
    secim = sorted((tr[-4:] + diger[-6:])[-7:] if len(tr) >= 4 else (tr + diger[-(7 - len(tr)):]), key=lambda o: int(o[0]))
    secim = [[y, (m[:150] + "…") if len(m) > 150 else m] for y, m in secim]
    return {"olaylar": secim, "gunler": [_vikimetin(g) for g in bolum("Tatiller ve özel günler")][:4]}


def depremler():
    """Kandilli son 500 deprem listesi."""
    s = getir("http://www.koeri.boun.edu.tr/scripts/lst0.asp").decode("windows-1254", "replace")
    out = []
    for m in re.finditer(r"^(\d{4}\.\d{2}\.\d{2}) (\d{2}:\d{2}:\d{2})\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(.+?)\s{2,}",
                         s, re.M):
        tarih, saat, enlem, boylam, derinlik, md, ml, mw, yer = m.groups()
        buyukluk = max(float(x) for x in (md, ml, mw) if re.match(r"^\d", x))
        out.append({"id": f"{tarih} {saat}", "zaman": f"{tarih} {saat}", "enlem": float(enlem), "boylam": float(boylam),
                    "derinlik": float(derinlik), "buyukluk": buyukluk, "yer": yer.strip()})
    return out


if __name__ == "__main__":
    print(namaz())
    t = tarihte_bugun()
    print(*t["olaylar"], sep="\n")
    print(t["gunler"])
    print(depremler()[:3])
