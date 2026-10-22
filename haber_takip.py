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

from gonder import ayar, cok_parcali
from kategori import sinifla

KOK = Path(__file__).resolve().parent
DURUM = KOK / "durum" / "gorulen.json"
TZ = ZoneInfo("Europe/Istanbul")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8"}
EN_ESKI = timedelta(hours=6)       # bundan eski haberler yeni sayılmaz
SAKLA = timedelta(days=14)         # gönderilmiş bağlantı ve başlıklar bu kadar hatırlanır; sayfada yeniden beliren eski haber tekrar gitmesin
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
    # Cloudflare bot korumalı siteler: sunucudan doğrudan açılmıyor, Google Haberler'deki siteye özel aramadan alınır
] + [(f"Google: {ad}", f"https://news.google.com/rss/search?q=site:{alan}+when:1d&hl=tr&gl=TR&ceid=TR:tr")
     for ad, alan in [("Düzce Postası", "duzcepostasi.com"), ("Düzce Parantez", "duzceparantez.com"),
                      ("Oxijen TV", "oxijen.tv"), ("Düzce'nin Sesi", "duzceninsesi.com.tr"),
                      ("Düzce Damla", "duzcedamla.com")]]
# RSS'i olmayan siteler: sayfadaki haber kartları okunur. (site, sayfa, desen, bağlantı ön eki)
# Desenin ilk grubu bağlantı, ikinci grubu başlık. Bu kartlarda saat olmadığı için zaman None kalır.
HTML_KAYNAKLAR = [
    ("Düzce Belediyesi", "https://www.duzce.bel.tr/haberler",
     r'<a href="(/haber/[^"]+)" class="related-news-card">.*?related-news-card-title">([^<]+)<', "https://www.duzce.bel.tr"),
    ("Düzce Belediyesi Duyuru", "https://www.duzce.bel.tr/duyurular",
     r'<a href="(/duyurular/[^"]+)" class="ilanlar-list-item">.*?ilanlar-list-item-title">([^<]+)<', "https://www.duzce.bel.tr"),
    ("Düzce Manşet", "https://duzcemanset.com.tr/",
     r'<a href="(https://duzcemanset\.com\.tr/[a-z0-9-]+-\d+)">\s*<img[^>]*alt="([^"]+)"', ""),
]
HABER_DEGIL = re.compile(r"ihale|alım işi|yapım işi|satış ilanı|kiralama ilanı", re.I)  # ilanlar haber değil
DOLGU = {"ve", "ile", "de", "da", "bir", "bu", "için", "olan", "oldu", "düzce", "düzcede", "düzceli", "sonra", "son", "dakika"}


def kelimeler(baslik):
    """Başlığın kelime kökleri: Türkçe ekler yüzünden "kaldırıma" ile "kaldırım" aynı sayılsın diye ilk 5 harf."""
    b = baslik.replace("İ", "i").replace("I", "ı").lower()
    return {k[:5] for k in re.findall(r"\w+", b) if len(k) > 2 and k not in DOLGU}


def benzer(a, b):
    """Aynı olay mı: kısa başlığın köklerinin %60'ı ortak ve en az 3 ortak kök."""
    ortak = len(a & b)
    return bool(a and b) and ortak >= 3 and ortak / min(len(a), len(b)) >= BENZERLIK


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
            while True:  # sondaki " - Düzce Parantez Gazete(si)" gibi site adlarını sök
                bas, _, kuyruk = baslik.rpartition(" - ")
                if not (bas and kuyruk.split()[:1] and kuyruk.split()[0].lower() in kaynak.lower()):
                    break
                baslik = bas.strip()
            if len(baslik.split()) < 4 or baslik.lower().endswith("haberleri"):  # kategori sayfası, haber değil
                continue
        link = (it.findtext("link") or "").strip()
        tarih = it.findtext("pubDate")
        try:
            zaman = parsedate_to_datetime(tarih).astimezone(TZ) if tarih else None
        except (TypeError, ValueError):
            zaman = None
        if baslik and link and "/makale/" not in link:  # köşe yazıları haber değil
            aciklama = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(it.findtext("description") or ""))).strip()
            if aciklama.startswith(baslik[:30]):  # Google Haberler açıklaması çoğu zaman başlığın tekrarı
                aciklama = ""
            yield {"site": kaynak or site, "baslik": baslik, "link": link, "zaman": zaman, "aciklama": aciklama[:600]}


def oku_html(site, url, desen, on_ek):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        sayfa = r.read().decode("utf-8", "replace")
    gorulen = set()
    for link, baslik in re.findall(desen, sayfa, re.S):
        baslik = html.unescape(re.sub(r"\s+", " ", baslik)).strip()
        if link not in gorulen and len(baslik.split()) >= 3:
            gorulen.add(link)
            yield {"site": site, "baslik": baslik, "link": on_ek + link, "zaman": None}


def telegram(metin):
    token = ayar("TELEGRAM_BOT_TOKEN")
    for chat in ayar("TELEGRAM_CHAT_ID").split(","):
        veri = json.dumps({"chat_id": chat.strip(), "text": metin, "parse_mode": "HTML",
                           "disable_web_page_preview": False}).encode()
        istek = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=veri,
                                       headers={"Content-Type": "application/json"})
        urllib.request.urlopen(istek, timeout=20).read()


def telegram_foto(png, metin):
    token = ayar("TELEGRAM_BOT_TOKEN")
    for chat in ayar("TELEGRAM_CHAT_ID").split(","):
        govde, tur = cok_parcali({"chat_id": chat.strip(), "caption": metin, "parse_mode": "HTML"}, {"photo": Path(png)})
        istek = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendPhoto", data=govde,
                                       headers={"Content-Type": tur})
        urllib.request.urlopen(istek, timeout=60).read()


GUNLUK = KOK / "durum" / "gunluk_haber.json"


def gunluk_kaydet(dosya, kayit, simdi, sakla_gun=8):
    """Günün özeti gibi zamanlı paylaşımlar için gönderilenleri gün gün tutar."""
    veri = json.loads(dosya.read_text(encoding="utf-8")) if dosya.exists() else {}
    veri.setdefault(simdi.strftime("%Y-%m-%d"), []).append(kayit)
    sinir = (simdi - timedelta(days=sakla_gun)).strftime("%Y-%m-%d")
    veri = {g: v for g, v in veri.items() if g >= sinir}
    dosya.parent.mkdir(exist_ok=True)
    dosya.write_text(json.dumps(veri, ensure_ascii=False), encoding="utf-8")


def telegram_foto_url(url, metin):
    """İnternetteki bir görseli (ör. marketin resmi afişi) Telegram'a gönderir; olmazsa dosya olarak gönderir."""
    token = ayar("TELEGRAM_BOT_TOKEN")
    for chat in ayar("TELEGRAM_CHAT_ID").split(","):
        for yontem, alan in (("sendPhoto", "photo"), ("sendDocument", "document")):
            veri = json.dumps({"chat_id": chat.strip(), alan: url, "caption": metin, "parse_mode": "HTML"}).encode()
            try:
                urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{token}/{yontem}", data=veri,
                                       headers={"Content-Type": "application/json"}), timeout=60).read()
                break
            except Exception:
                if yontem == "sendDocument":
                    raise


def telegram_album_url(urller, metin):
    """İnternetteki görselleri (ör. BİM afişleri) tek albüm olarak gönderir; açıklama ilk görselde."""
    token = ayar("TELEGRAM_BOT_TOKEN")
    medya = [{"type": "photo", "media": u} for u in urller[:10]]
    medya[0].update({"caption": metin, "parse_mode": "HTML"})
    for chat in ayar("TELEGRAM_CHAT_ID").split(","):
        veri = json.dumps({"chat_id": chat.strip(), "media": medya}).encode()
        urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMediaGroup", data=veri,
                               headers={"Content-Type": "application/json"}), timeout=90).read()


def gonder_haber(g, simdi):
    """Kategoriye göre etiketli mesaj; önemli haberler tasarım kartıyla gider."""
    ilk = g["haberler"][0]
    saat = ilk["zaman"].strftime("%H.%M") if ilk["zaman"] else simdi.strftime("%H.%M")
    sinif = sinifla(ilk["baslik"])
    ust = sinif["etiket"] + ("  ·  🔴 ÖNEMLİ" if sinif["onemli"] else "")
    kaynaklar = "\n".join(f'📰 <a href="{html.escape(h["link"])}">{html.escape(h["site"])}</a>' for h in g["haberler"])
    ozet, baslik, yer = g.get("ozet", ""), ilk["baslik"], ""
    if sinif["onemli"] and not ozet:  # önemli haberler yapay zekâyla kendi cümlelerimizle (ücretsiz Gemini)
        from ai import ozetle
        y = ozetle(ilk["baslik"], next((h.get("aciklama") for h in g["haberler"] if h.get("aciklama")), ""))
        if y:
            baslik, ozet, yer = y["baslik"], y["ozet"], y["yer"]
    metin = (f"{ust}\n<b>{html.escape(baslik)}</b>\n" + (f"{html.escape(ozet)}\n" if ozet else "") + f"🕒 {saat}"
             + (f" · 📍 {html.escape(yer)}" if yer else "") + f"\n{kaynaklar}"
             + (f"\n<i>Kaynak başlığı: {html.escape(ilk['baslik'])}</i>" if baslik != ilk["baslik"] else ""))
    gunluk_kaydet(GUNLUK, {"baslik": ilk["baslik"], "kod": sinif["kod"], "etiket": sinif["etiket"], "onemli": sinif["onemli"],
                           "siteler": list(dict.fromkeys(h["site"] for h in g["haberler"])), "link": ilk["link"], "saat": saat}, simdi)
    if sinif["onemli"]:
        try:
            from haber_kart import KATEGORI, ciz_kart
            png = ciz_kart({"kategori": sinif["kod"] if sinif["kod"] in KATEGORI else "genel", "baslik": baslik,
                            "ozet": ozet, "yer": yer, "saat": saat},
                           KOK / "cikti" / "kartlar" / "son.png", hikaye=True)  # Instagram hikâyesi boyutu
            telegram_foto(png, metin)
            return
        except Exception as hata:  # kart çizilemezse haber metin olarak yine gitsin
            print("kart çizilemedi:", hata, file=sys.stderr)
    telegram(metin)


def main():
    simdi = datetime.now(TZ)
    ilk_calisma = not DURUM.exists()
    durum = json.loads(DURUM.read_text(encoding="utf-8")) if not ilk_calisma else {"linkler": {}, "basliklar": []}
    durum.setdefault("siteler", [])  # en az bir kez başarıyla okunmuş siteler
    sinir = (simdi - SAKLA).strftime("%Y-%m-%d %H:%M")
    durum["linkler"] = {k: v for k, v in durum["linkler"].items() if v >= sinir}
    durum["basliklar"] = [b for b in durum["basliklar"] if b[1] >= sinir]
    gonderilmis = [{k[:5] for k in b[0].split()} for b in durum["basliklar"]]

    yeni, hatalar = [], []
    kaynaklar = [(site, lambda s=site, u=url: oku(s, u)) for site, url in KAYNAKLAR] + \
                [(a[0], lambda a=a: oku_html(*a)) for a in HTML_KAYNAKLAR]
    for site, okuyucu in kaynaklar:
        try:
            haberler = list(okuyucu())
            ilk_kez = site not in durum["siteler"]  # ilk okunuşta yalnızca kaydet, gönderme
            for h in haberler:
                if h["link"] in durum["linkler"]:
                    continue
                if HABER_DEGIL.search(h["baslik"].replace("İ", "i").replace("I", "ı")):
                    durum["linkler"][h["link"]] = simdi.strftime("%Y-%m-%d %H:%M")
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
        telegram(f"✅ <b>Düzce Abisi haber takibi başladı</b>\n{len(KAYNAKLAR) + len(HTML_KAYNAKLAR)} kaynak taranıyor. "
                 f"Bundan sonra çıkan her yeni haber buraya gelecek.")
    else:
        for g in gruplar:
            gonder_haber(g, simdi)
            print("gönderildi:", g["haberler"][0]["baslik"])

    for g in gruplar:
        durum["basliklar"].append([" ".join(sorted(g["kelimeler"])), simdi.strftime("%Y-%m-%d %H:%M")])
    DURUM.parent.mkdir(exist_ok=True)
    DURUM.write_text(json.dumps(durum, ensure_ascii=False), encoding="utf-8")
    print(f"{len(yeni)} yeni, {len(gruplar)} grup, ilk_calisma={ilk_calisma}")
    if hatalar:
        print("HATA:", *hatalar, sep="\n  ", file=sys.stderr)


if __name__ == "__main__":
    main()
