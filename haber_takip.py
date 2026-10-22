#!/usr/bin/env python3
"""Düzce yerel haber sitelerini tarar, yeni haberleri Telegram'a gönderir.

Kullanım:  python3 haber_takip.py
Sunucuda 10 dakikada bir çalışır (.github/workflows/haber.yml).

- Daha önce gönderilen haberler durum/gorulen.json dosyasında tutulur.
- İlk çalıştırmada (durum dosyası yoksa) mevcut haberler yalnızca kaydedilir,
  gönderilmez; böylece size 150 eski haber birden yağmaz.
- Aynı olay birden fazla sitede çıkarsa tek mesaj olarak, kaynakları
  birlikte gönderilir.
"""
import html, json, re, sys, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from gonder import ayar

KOK = Path(__file__).resolve().parent
DURUM = KOK / "durum" / "gorulen.json"
TZ = ZoneInfo("Europe/Istanbul")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8"}
EN_ESKI = timedelta(hours=6)       # bundan eski haberler yeni sayılmaz
SAKLA = timedelta(days=3)          # durum dosyasında bu kadar geriye bakılır
BENZERLIK = 0.6                    # bu orandan fazla ortak kelime = aynı haber

KAYNAKLAR = [
    ("Düzce Postası", "https://www.duzcepostasi.com/rss"),
    ("Düzce Parantez", "https://www.duzceparantez.com/rss"),
    ("Düzce Damla", "https://www.duzcedamla.com/rss"),
    ("Oxijen TV", "https://www.oxijen.tv/rss"),
    ("Düzce'nin Sesi", "https://www.duzceninsesi.com.tr/rss"),
    ("Öncü TV", "https://www.oncurtv.com/rss"),
    ("Düzce Hür Haber", "https://www.duzcehurhaber.com/rss"),
    ("Haber Düzce", "https://www.haberduzce.com/rss.xml"),
    # bazı yerel siteler yurt dışı sunucuları engelliyor; Google Haberler onların bir kısmını ve ajansları kapsıyor
    ("Google Haberler", "https://news.google.com/rss/search?q=D%C3%BCzce+when:1d&hl=tr&gl=TR&ceid=TR:tr"),
]
DOLGU = {"ve", "ile", "de", "da", "bir", "bu", "için", "olan", "oldu", "düzce", "düzcede", "düzceli", "sonra", "son", "dakika"}


def kelimeler(baslik):
    b = baslik.replace("İ", "i").replace("I", "ı").lower()
    return {k for k in re.findall(r"\w+", b) if len(k) > 2 and k not in DOLGU}


def benzer(a, b):
    if not a or not b:
        return False
    return len(a & b) / min(len(a), len(b)) >= BENZERLIK


def oku(site, url):
    for deneme in range(2):  # yerel siteler ara sıra bağlantıyı koparıyor; bir kez daha dene
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
                kok = ET.fromstring(r.read())
            break
        except Exception:
            if deneme:
                raise
    for it in kok.iter("item"):
        baslik = html.unescape((it.findtext("title") or "").strip())
        kaynak = it.findtext("source")  # yalnızca Google Haberler'de dolu
        if kaynak:
            baslik = baslik.removesuffix(" - " + kaynak).strip()
        link = (it.findtext("link") or "").strip()
        tarih = it.findtext("pubDate")
        try:
            zaman = parsedate_to_datetime(tarih).astimezone(TZ) if tarih else None
        except (TypeError, ValueError):
            zaman = None
        if baslik and link and "/makale/" not in link:  # köşe yazıları haber değil
            yield {"site": kaynak or site, "baslik": baslik, "link": link, "zaman": zaman}


def telegram(metin):
    token = ayar("TELEGRAM_BOT_TOKEN")
    for chat in ayar("TELEGRAM_CHAT_ID").split(","):
        veri = json.dumps({"chat_id": chat.strip(), "text": metin, "parse_mode": "HTML",
                           "disable_web_page_preview": False}).encode()
        istek = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=veri,
                                       headers={"Content-Type": "application/json"})
        urllib.request.urlopen(istek, timeout=20).read()


def main():
    simdi = datetime.now(TZ)
    ilk_calisma = not DURUM.exists()
    durum = json.loads(DURUM.read_text(encoding="utf-8")) if not ilk_calisma else {"linkler": {}, "basliklar": []}
    durum.setdefault("siteler", [])  # en az bir kez başarıyla okunmuş siteler
    sinir = (simdi - SAKLA).strftime("%Y-%m-%d %H:%M")
    durum["linkler"] = {k: v for k, v in durum["linkler"].items() if v >= sinir}
    durum["basliklar"] = [b for b in durum["basliklar"] if b[1] >= sinir]
    gonderilmis = [set(b[0].split()) for b in durum["basliklar"]]

    yeni, hatalar = [], []
    for site, url in KAYNAKLAR:
        try:
            haberler = list(oku(site, url))
            ilk_kez = site not in durum["siteler"]  # ilk okunuşta yalnızca kaydet, gönderme
            for h in haberler:
                if h["link"] in durum["linkler"]:
                    continue
                durum["linkler"][h["link"]] = simdi.strftime("%Y-%m-%d %H:%M")
                if ilk_kez or (h["zaman"] and simdi - h["zaman"] > EN_ESKI):
                    continue
                yeni.append(h)
            if ilk_kez:
                durum["siteler"].append(site)
        except Exception as hata:  # bir site çökerse diğerleri taransın
            hatalar.append(f"{site}: {hata}")

    # aynı olayı anlatan haberleri grupla; daha önce gönderilmiş olayları atla
    gruplar = []
    for h in sorted(yeni, key=lambda x: x["zaman"] or simdi):
        k = kelimeler(h["baslik"])
        if any(benzer(k, g) for g in gonderilmis):
            continue
        grup = next((g for g in gruplar if benzer(k, g["kelimeler"])), None)
        if grup:
            if h["site"] not in [x["site"] for x in grup["haberler"]]:
                grup["haberler"].append(h)
        else:
            gruplar.append({"kelimeler": k, "haberler": [h]})

    if ilk_calisma:
        telegram(f"✅ <b>Düzce Abisi haber takibi başladı</b>\n{len(KAYNAKLAR)} site taranıyor. "
                 f"Bundan sonra çıkan her yeni haber buraya gelecek.")
    else:
        for g in gruplar:
            ilk = g["haberler"][0]
            saat = ilk["zaman"].strftime("%H.%M") if ilk["zaman"] else simdi.strftime("%H.%M")
            kaynaklar = "\n".join(f'📰 <a href="{html.escape(h["link"])}">{html.escape(h["site"])}</a>' for h in g["haberler"])
            telegram(f"🚨 <b>{html.escape(ilk['baslik'])}</b>\n🕒 {saat}\n{kaynaklar}")
            print("gönderildi:", ilk["baslik"])

    for g in gruplar:
        durum["basliklar"].append([" ".join(sorted(g["kelimeler"])), simdi.strftime("%Y-%m-%d %H:%M")])
    DURUM.parent.mkdir(exist_ok=True)
    DURUM.write_text(json.dumps(durum, ensure_ascii=False), encoding="utf-8")
    print(f"{len(yeni)} yeni, {len(gruplar)} grup, ilk_calisma={ilk_calisma}")
    if hatalar:
        print("HATA:", *hatalar, sep="\n  ", file=sys.stderr)


if __name__ == "__main__":
    main()
