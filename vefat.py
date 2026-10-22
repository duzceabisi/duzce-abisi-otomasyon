#!/usr/bin/env python3
"""Düzce vefat ve cenaze bilgilerini toplar; daha önce paylaşılmamış olanları döndürür.

Kaynak: Düzce Hür Haber'in günlük "vefat edenler" haberleri. Haberin sonundaki
"Cenaze ve defin bilgileri" bölümü (Adı soyadı / Baba adı / Anne adı / Ölüm tarihi /
Cenaze namazı / Defin yeri) okunur.

Kullanım (calistir.py içinden):
    yeniler = yeni_vefatlar()      # paylaşılmamış kayıtlar
    ...gönder...
    kaydet(yeniler)                # gönderim başarılıysa hafızaya yaz
"""
import html, json, re, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KOK = Path(__file__).resolve().parent
DURUM = KOK / "durum" / "vefat.json"
TZ = ZoneInfo("Europe/Istanbul")
RSS = "https://www.duzcehurhaber.com/rss"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"}
GERI = timedelta(days=2)  # son iki günün vefat haberlerine bakılır


def getir(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
        return r.read()


def metin(sayfa):
    i = sayfa.find("articleBody")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", sayfa[i if i > 0 else 0:], flags=re.S)
    t = re.sub(r"<(p|li|h\d|br|div)[^>]*>", "\n", t)
    return html.unescape(re.sub(r"<[^>]+>", "", t))


def alan(blok, ad):
    m = re.search(rf"{ad}\s*:\s*(.+)", blok)
    return m.group(1).strip() if m else ""


def kayitlar(sayfa):
    """Her "Baba adı:" bloğu bir kişi. İsim, "Adı soyadı:" satırından ya da
    öncesindeki "...'in evladı İSİM, 20 Ekim..." cümlesinden alınır (haberler iki biçimde de yazılıyor)."""
    t = metin(sayfa)
    bas = [m.start() for m in re.finditer(r"Baba adı\s*:", t)]
    for n, i in enumerate(bas):
        blok = t[i:bas[n + 1] if n + 1 < len(bas) else i + 800]
        once = t[max(0, i - 1500):i]
        ad = alan(once[-200:], "Adı soyadı")
        if not ad:
            evlat = re.findall(r"evladı\s+([^,\n]{3,50}?),\s*\d", once)
            ad = evlat[-1].strip() if evlat else ""
        if not ad:
            continue
        baba, anne = alan(blok, "Baba adı"), alan(blok, "Anne adı")
        yield {"ad": ad, "anne_baba": " · ".join(x for x in [f"Baba: {baba}" if baba else "", f"Anne: {anne}" if anne else ""] if x),
               "olum": alan(blok, "Ölüm tarihi"), "defin_tarihi": alan(blok, "Defin tarihi"),
               "namaz": alan(blok, "Cenaze namazı"), "defin": alan(blok, "Defin yeri")}


def anahtar(k):
    return f"{k['ad'].replace('İ', 'i').replace('I', 'ı').lower()}|{k['olum']}"


def yeni_vefatlar():
    gorulen = json.loads(DURUM.read_text(encoding="utf-8"))["gorulen"] if DURUM.exists() else {}
    simdi = datetime.now(TZ)
    kok = ET.fromstring(getir(RSS))
    yeniler, eklenen = [], set()
    for it in kok.iter("item"):
        baslik = (it.findtext("title") or "").lower()
        tarih = it.findtext("pubDate")
        if "vefat" not in baslik or not tarih or simdi - parsedate_to_datetime(tarih) > GERI:
            continue
        for k in kayitlar(getir(it.findtext("link")).decode("utf-8", "replace")):
            a = anahtar(k)
            if a not in gorulen and a not in eklenen:
                eklenen.add(a)
                yeniler.append(k)
    return yeniler


def kaydet(yeniler):
    durum = json.loads(DURUM.read_text(encoding="utf-8")) if DURUM.exists() else {"gorulen": {}}
    bugun = datetime.now(TZ)
    for k in yeniler:
        durum["gorulen"][anahtar(k)] = bugun.strftime("%Y-%m-%d")
    sinir = (bugun - timedelta(days=30)).strftime("%Y-%m-%d")
    durum["gorulen"] = {a: t for a, t in durum["gorulen"].items() if t >= sinir}
    DURUM.parent.mkdir(exist_ok=True)
    DURUM.write_text(json.dumps(durum, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    for k in yeni_vefatlar():
        print(k)
