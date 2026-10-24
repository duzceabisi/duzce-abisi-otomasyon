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
import collections, html, json, re, sys, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from gonder import ayar, cok_parcali, deneme_modu, sessiz_saat
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
ILLER = ("adana adıyaman afyon ağrı amasya ankara antalya artvin balıkesir bilecik bingöl bitlis burdur bursa "
         "çanakkale çankırı çorum denizli diyarbakır edirne elazığ erzincan erzurum eskişehir gaziantep giresun gümüşhane "
         "hakkari hatay ısparta mersin istanbul izmir kars kastamonu kayseri kırklareli kırşehir kocaeli konya kütahya malatya "
         "manisa kahramanmaraş mardin muğla muş nevşehir niğde ordu rize sakarya samsun siirt sinop sivas tekirdağ tokat "
         "trabzon tunceli şanlıurfa uşak van yozgat zonguldak aksaray bayburt karaman kırıkkale batman şırnak bartın ardahan "
         "ığdır yalova karabük kilis osmaniye").split()
BASKA_IL = re.compile(r"\b(" + "|".join(ILLER) + r")(?:['’]|\b)(?!\s*(?:cad|sok|bulv|mah|yolu|kavş))")  # "İstanbul Caddesi" Düzce'de
DUZCE = re.compile(r"düzce|akçakoca|cumayeri|çilimli|gölyaka|gümüşova|kaynaşlı|yığılca|konuralp|beyciler|efteni|melen")


def duzce_disi(h):
    """Başka bir il açıkça geçiyor, Düzce hiç geçmiyorsa haber Düzce'nin değildir (Kahramanmaraş'ta ceset, Zonguldak'ta kaza)."""
    t = f"{h['baslik']} {h.get('aciklama', '')}".replace("İ", "i").replace("I", "ı").lower()
    return not DUZCE.search(t) and bool(BASKA_IL.search(t))


HABER_DEGIL = re.compile(r"ihale|alım işi|yapım işi|satış ilanı|kiralama ilanı", re.I)  # ilanlar haber değil
DOLGU = {"ve", "ile", "de", "da", "bir", "bu", "için", "olan", "oldu", "düzce", "düzcede", "düzceli", "sonra", "son", "dakika"}


def kelimeler(baslik):
    """Başlığın kelime kökleri: Türkçe ekler yüzünden "kaldırıma" ile "kaldırım" aynı sayılsın diye ilk 5 harf."""
    b = baslik.replace("İ", "i").replace("I", "ı").lower()
    return {k[:5] for k in re.findall(r"\w+", b) if len(k) > 2 and k not in DOLGU}


ILCELER = {"akçak", "cumay", "çilim", "gölya", "gümüş", "kayna", "yığıl", "konur"}
GENEL_YER = {"düzce", "türki", "ankar", "istan", "sakar", "bolu", "zongu", "tem", "anado", "karad", "merke",
             "cadde", "mahal", "köyü", "köyün", "kavşa", "sokağ", "sokak", "bulva", "mevki", "yolu", "ilçes", "beled", "valil"}
YER_EKI = r"(?:Mahallesi|Mah\.|Caddesi|Cad\.|Köyü|Köyünde|Kavşağı|Kavşağında|Sokağı|Sokak|Bulvarı|Mevkii|Mevkiinde|Yolu|Köprüsü|Sitesi|ilçesi|ilçesinde|beldesi|beldesinde)"


def yerler(metin):
    """Yer adları: kesme işaretli özel adlar ("Aydınpınar'da") ve mahalle/köy/cadde adları. İlk 5 harf, küçük harf."""
    metin = metin.replace("’", "'")
    adlar = re.findall(r"([A-ZÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ]+)'", metin) + \
            re.findall(rf"([A-ZÇĞİÖŞÜ][\wçğıöşüÇĞİÖŞÜ]+)\s+{YER_EKI}", metin)
    out = {a.replace("İ", "i").replace("I", "ı").lower()[:5] for a in adlar}
    return {a for a in out if len(a) > 2 and a not in GENEL_YER}


def olay_imzasi(h):
    metin = f"{h['baslik']}. {h.get('aciklama', '')}"
    return {"kat": sinifla(h["baslik"])["kod"], "yer": yerler(metin), "kok": kelimeler(metin)}


AILE = {"olum": "kaza", "asayis": "kaza", "kayip": "kaza"}  # ölüm/asayiş haberi çoğu zaman aynı kazanın devamı


def ayni_olay(a, b, yaygin):
    """Başlığı farklı yazılmış aynı olay. yaygin: bu taramada çok geçen (ayırt etmeyen) kökler."""
    if AILE.get(a["kat"], a["kat"]) != AILE.get(b["kat"], b["kat"]):
        return False
    ortak_yer = a["yer"] & b["yer"]
    nadir = (a["kok"] & b["kok"]) - yaygin - ortak_yer
    ozel = ortak_yer - ILCELER
    if ozel:                    # aynı mahalle/köy/cadde
        return len(nadir) >= 2
    if ortak_yer:               # yalnızca aynı ilçe
        return len(nadir) >= 4
    return len(nadir) >= 5 and len(nadir) >= 0.5 * min(len(a["kok"]), len(b["kok"]))


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


def haber_metni(url):
    """Haber sayfasının gövde metni (yapay zekâ ayrıntılı özet yazsın diye). Google yönlendirmesi ve hata -> boş."""
    if "news.google.com" in url:
        return ""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
            s = r.read().decode("utf-8", "replace")
    except Exception:
        return ""
    s = re.sub(r"<script.*?</script>|<style.*?</style>|<aside.*?</aside>|<nav.*?</nav>|<footer.*?</footer>", " ", s, flags=re.S)
    govde = s[s.find("articleBody"):] if "articleBody" in s else s
    paragraflar = [html.unescape(re.sub(r"<[^>]+>", " ", p)) for p in re.findall(r"<p[^>]*>(.*?)</p>", govde, re.S)]
    paragraflar = [re.sub(r"\s+", " ", p).strip() for p in paragraflar]
    metin = " ".join(p for p in paragraflar if len(p) > 50 and "çerez" not in p.lower() and "yorum" not in p.lower()[:20])
    return metin[:4000]


def telegram(metin):
    if deneme_modu():
        print("[DENEME] telegram:", str(metin)[:90].replace("\n", " ")); return
    if sessiz_saat():
        print("[SESSİZ SAAT] gönderilmedi:", str(metin)[:90].replace("\n", " ")); return
    token = ayar("TELEGRAM_BOT_TOKEN")
    for chat in ayar("TELEGRAM_CHAT_ID").split(","):
        veri = json.dumps({"chat_id": chat.strip(), "text": metin, "parse_mode": "HTML",
                           "disable_web_page_preview": False}).encode()
        istek = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=veri,
                                       headers={"Content-Type": "application/json"})
        urllib.request.urlopen(istek, timeout=20).read()


def telegram_foto(png, metin):
    if deneme_modu():
        print("[DENEME] telegram:", str(png)[:90].replace("\n", " ")); return
    if sessiz_saat():
        print("[SESSİZ SAAT] gönderilmedi:", str(png)[:90].replace("\n", " ")); return
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
    if deneme_modu():
        print("[DENEME] telegram:", str(url)[:90].replace("\n", " ")); return
    if sessiz_saat():
        print("[SESSİZ SAAT] gönderilmedi:", str(url)[:90].replace("\n", " ")); return

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
    if deneme_modu():
        print("[DENEME] telegram:", str(urller)[:90].replace("\n", " ")); return
    if sessiz_saat():
        print("[SESSİZ SAAT] gönderilmedi:", str(urller)[:90].replace("\n", " ")); return

    token = ayar("TELEGRAM_BOT_TOKEN")
    medya = [{"type": "photo", "media": u} for u in urller[:10]]
    medya[0].update({"caption": metin, "parse_mode": "HTML"})
    for chat in ayar("TELEGRAM_CHAT_ID").split(","):
        veri = json.dumps({"chat_id": chat.strip(), "media": medya}).encode()
        urllib.request.urlopen(urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMediaGroup", data=veri,
                               headers={"Content-Type": "application/json"}), timeout=90).read()


AI_SINIRI = 25
GORSEL_SINIRI = 3      # bir taramada habere özel üretilecek en fazla görsel (yalnızca önemli haberler; yerel sunucu)
_gorsel_sayac = {"n": 0}         # bir taramada önemli olmayan haberlerden en fazla bu kadarı yapay zekâyla özetlenir (ücretsiz kota)
_ai_sayac = {"n": 0}


def gonder_haber(g, simdi, kaydet=True):
    """Her haber hikâye boyutunda görselli kartla gider; kategori etiketi ve kaynaklar mesaj metninde."""
    ilk = g["haberler"][0]
    saat = ilk["zaman"].strftime("%H.%M") if ilk["zaman"] else simdi.strftime("%H.%M")
    sinif = sinifla(ilk["baslik"])
    ust = sinif["etiket"] + ("  ·  🔴 ÖNEMLİ" if sinif["onemli"] else "")
    kaynaklar = "\n".join(f'📰 <a href="{html.escape(h["link"])}">{html.escape(h["site"])}</a>' for h in g["haberler"])
    ozet, baslik, yer = g.get("ozet", ""), ilk["baslik"], ""
    kart_ozet, sahne = ozet, ""
    if not ozet and (sinif["onemli"] or _ai_sayac["n"] < AI_SINIRI):  # kendi cümlelerimizle (ücretsiz Gemini)
        if not sinif["onemli"]:
            _ai_sayac["n"] += 1
        from ai import ozetle
        # doğrudan erişilebilen kaynaktan haberin tam metni (Google yönlendirmeleri ve engelli siteler atlanır)
        metin_ = next((m for m in (haber_metni(h["link"]) for h in sorted(g["haberler"], key=lambda h: "news.google" in h["link"])) if m), "")
        y = ozetle(ilk["baslik"], next((h.get("aciklama") for h in g["haberler"] if h.get("aciklama")), ""), metin_)
        if y and not y["duzce"]:  # yapay zekâ tam metni okudu: Düzce'yle ilgisi yok
            print("Düzce dışı, gönderilmedi:", ilk["baslik"])
            return False
        if y:
            baslik, ozet, yer = y["baslik"], y["ozet"], y["yer"]
            kart_ozet = y.get("kisa") or ozet
            sahne = y.get("sahne", "")
    metin = (f"{ust}\n<b>{html.escape(baslik)}</b>\n" + (f"{html.escape(ozet)}\n" if ozet else "") + f"🕒 {saat}"
             + (f" · 📍 {html.escape(yer)}" if yer else "") + f"\n{kaynaklar}"
             + (f"\n<i>Kaynak başlığı: {html.escape(ilk['baslik'])}</i>" if baslik != ilk["baslik"] else ""))
    if kaydet:
        gunluk_kaydet(GUNLUK, {"baslik": ilk["baslik"], "kod": sinif["kod"], "etiket": sinif["etiket"], "onemli": sinif["onemli"],
                           "siteler": list(dict.fromkeys(h["site"] for h in g["haberler"])), "link": ilk["link"], "saat": saat}, simdi)
    for deneme in range(2):  # her haber görselli gider; kart bir kez daha denenir
        try:
            from haber_kart import KATEGORI, ciz_kart
            from gorsel import habere_ozel
            foto = None
            if deneme == 0 and sinif["onemli"] and _gorsel_sayac["n"] < GORSEL_SINIRI:  # yalnızca yerel sunucuda (GORSEL_MOTORU)
                foto = habere_ozel(sahne, sinif["kod"])
                _gorsel_sayac["n"] += bool(foto)
            png = ciz_kart({"kategori": sinif["kod"] if sinif["kod"] in KATEGORI else "genel", "baslik": baslik,
                            "ozet": kart_ozet, "yer": yer, "saat": saat, "foto": str(foto) if foto else ""},
                           KOK / "cikti" / "kartlar" / "son.png", hikaye=True)  # Instagram hikâyesi boyutu
            telegram_foto(png, metin)
            return True
        except Exception as hata:
            print(f"kart çizilemedi ({deneme + 1}. deneme):", hata, file=sys.stderr)
    telegram(metin)  # iki denemede de kart çizilemezse haber kaybolmasın
    return True


OLAY_SAKLA = timedelta(hours=48)


def onceki_olay(imza, olaylar, yaygin):
    """Bu olay son 48 saatte gönderildi mi? Önce kural (yer adı + ortak ayrıntı), sonra yapay zekâya sorulur."""
    aile = AILE.get(imza["kat"], imza["kat"])
    adaylar = [o for o in olaylar if AILE.get(o["kat"], o["kat"]) == aile]
    for o in adaylar:
        if ayni_olay(imza, {"kat": o["kat"], "yer": set(o["yer"]), "kok": set(o["kok"])}, yaygin):
            return o
    if adaylar and aile not in ("genel", "kurum", "ekonomi", "findik"):  # olay haberlerinde yapay zekâya da sor
        try:
            from ai import ayni_olay_mu
            i = ayni_olay_mu(imza["metin"], [o["metin"] for o in adaylar[-15:]])
            if i:
                return adaylar[-15:][i - 1]
        except Exception as hata:
            print("aynı olay kontrolü atlandı:", hata, file=sys.stderr)
    return None


def main():
    simdi = datetime.now(TZ)
    ilk_calisma = not DURUM.exists()
    durum = json.loads(DURUM.read_text(encoding="utf-8")) if not ilk_calisma else {"linkler": {}, "basliklar": []}
    durum.setdefault("siteler", [])  # en az bir kez başarıyla okunmuş siteler
    sinir = (simdi - SAKLA).strftime("%Y-%m-%d %H:%M")
    durum["linkler"] = {k: v for k, v in durum["linkler"].items() if v >= sinir}
    durum["basliklar"] = [b for b in durum["basliklar"] if b[1] >= sinir]
    gonderilmis = [{k[:5] for k in b[0].split()} for b in durum["basliklar"]]
    olay_sinir = (simdi - OLAY_SAKLA).strftime("%Y-%m-%d %H:%M")
    durum["olaylar"] = [o for o in durum.get("olaylar", []) if o["t"] >= olay_sinir]
    hepsi = []  # bu taramada okunan tüm haberler (hangi kelimelerin yaygın olduğunu bulmak için)

    yeni, hatalar = [], []
    kaynaklar = [(site, lambda s=site, u=url: oku(s, u)) for site, url in KAYNAKLAR] + \
                [(a[0], lambda a=a: oku_html(*a)) for a in HTML_KAYNAKLAR]
    for site, okuyucu in kaynaklar:
        try:
            haberler = list(okuyucu())
            hepsi += haberler
            ilk_kez = site not in durum["siteler"]  # ilk okunuşta yalnızca kaydet, gönderme
            for h in haberler:
                if h["link"] in durum["linkler"]:
                    continue
                if HABER_DEGIL.search(h["baslik"].replace("İ", "i").replace("I", "ı")):
                    durum["linkler"][h["link"]] = simdi.strftime("%Y-%m-%d %H:%M")
                    continue
                durum["linkler"][h["link"]] = simdi.strftime("%Y-%m-%d %H:%M")
                if ilk_kez or (h["zaman"] and simdi - h["zaman"] > EN_ESKI) or duzce_disi(h):
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

    # başlığı farklı yazılmış aynı olay: bu taramadaki gruplar birleştirilir, son 48 saatte gönderilmişse atlanır
    sayac = collections.Counter(k for x in hepsi for k in olay_imzasi(x)["kok"])
    yaygin = {k for k, c in sayac.items() if c >= max(6, len(hepsi) * 0.015)}
    birlesik = []
    for g in gruplar:
        h0 = g["haberler"][0]
        g["imza"] = olay_imzasi(h0)
        g["imza"]["metin"] = f"{h0['baslik']} — {h0.get('aciklama', '')[:200]}"
        es = next((b for b in birlesik if ayni_olay(g["imza"], b["imza"], yaygin)), None)
        if es:
            es["haberler"] += [x for x in g["haberler"] if x["site"] not in [y["site"] for y in es["haberler"]]]
            continue
        o = onceki_olay(g["imza"], durum["olaylar"], yaygin) if not ilk_calisma else None
        if o:
            print("daha önce gönderildi, atlandı:", h0["baslik"], "≈", o["metin"][:70])
            durum["basliklar"].append([" ".join(sorted(g["kelimeler"])), simdi.strftime("%Y-%m-%d %H:%M")])
            continue
        birlesik.append(g)
    gruplar = birlesik

    if ilk_calisma:
        telegram(f"✅ <b>Düzce Abisi haber takibi başladı</b>\n{len(KAYNAKLAR) + len(HTML_KAYNAKLAR)} kaynak taranıyor. "
                 f"Bundan sonra çıkan her yeni haber buraya gelecek.")
    else:
        for g in gruplar:
            if gonder_haber(g, simdi):
                print("gönderildi:", g["haberler"][0]["baslik"])

    for g in gruplar:
        durum["basliklar"].append([" ".join(sorted(g["kelimeler"])), simdi.strftime("%Y-%m-%d %H:%M")])
        durum["olaylar"].append({"t": simdi.strftime("%Y-%m-%d %H:%M"), "kat": g["imza"]["kat"], "yer": sorted(g["imza"]["yer"]),
                                 "kok": sorted(g["imza"]["kok"]), "metin": g["imza"]["metin"]})
    DURUM.parent.mkdir(exist_ok=True)
    DURUM.write_text(json.dumps(durum, ensure_ascii=False), encoding="utf-8")
    print(f"{len(yeni)} yeni, {len(gruplar)} grup, ilk_calisma={ilk_calisma}")
    if hatalar:
        print("HATA:", *hatalar, sep="\n  ", file=sys.stderr)


if __name__ == "__main__":
    main()
