#!/usr/bin/env python3
"""Market kampanyaları: BİM aktüel/indirim, ŞOK haftalık afişleri, A101 aktüel haberleri.

zamanli.py her gün 10:00'da market_kampanyalari() çağırır; her kampanya bir kez gönderilir.
  BİM   bim.com.tr          O gün başlayan aktüel ve haftalık indirim dönemlerinin resmi afişleri (albüm)
  ŞOK   kurumsal.sokmarket  Resmi "Haftanın Fırsatları" / "Hafta Sonu" afişi (afişin kendisi)
  A101  a101.com.tr          Resmi kampanya afişleri; yalnızca yerel sunucuda (ev interneti + Chrome)
"""
import html, json, re, urllib.parse, urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

KOK = Path(__file__).resolve().parent
DURUM = KOK / "durum" / "market.json"
TZ = ZoneInfo("Europe/Istanbul")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"}
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
BIM = "https://www.bim.com.tr/Categories/100/aktuel-urunler.aspx"
SOK = "https://kurumsal.sokmarket.com.tr"


def getir(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=25) as r:
        return r.read().decode("utf-8", "replace")


def tr_baslik(metin):
    """'KARNIYARIK TENCERE' -> 'Karnıyarık Tencere'. BİM büyük harfte I/İ ayrımını doğru yazıyor; str.title() bozuyor."""
    kucuk = metin.replace("İ", "i").replace("I", "ı").lower()
    return " ".join(k[:1].replace("i", "İ").replace("ı", "I").upper() + k[1:] for k in kucuk.split())


def temiz(t):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))).strip()


def bim_sekmeler():
    """{'23 Ekim Cuma': '1688', '17-23 Ekim': '1696', ...}"""
    s = getir(BIM)
    return {temiz(t): k for k, t in re.findall(r'Bim_AktuelTarihKey=(\d+)"[^>]*>(.*?)</a>', s, re.S)}


def bim_urunler(anahtar):
    s = getir(f"{BIM}?top=1&Bim_AktuelTarihKey={anahtar}")
    urunler = []
    for kart in s.split('<div class="product ')[1:]:
        marka = re.search(r'<h2 class="subTitle">(.*?)</h2>', kart, re.S)
        ad = re.search(r'<h2 class="title">(.*?)</h2>', kart, re.S)
        fiyat = re.findall(r'class="text quantify">\s*([^<]+)</div>\s*<div class="kusurArea">\s*<span class="number">\s*([^<]+)</span>', kart)
        if not ad or not fiyat:
            continue
        fiyatlar = [f"{a.strip()}{b.strip()} TL".replace(",,", ",") for a, b in fiyat]
        eski = re.search(r'class="[^"]*(?:old|eski)[^"]*"[^>]*>\s*([\d.,]+)', kart)
        indirim = re.search(r"%\s*(\d+)", temiz(kart))
        urunler.append({"marka": temiz(marka.group(1)) if marka else "", "ad": temiz(ad.group(1)),
                        "fiyat": fiyatlar[-1], "eski": eski.group(1) + " TL" if eski else "",
                        "indirim": f"%{indirim.group(1)}" if indirim else ""})
    return urunler


BIM_AFIS = "https://www.bim.com.tr/Categories/680/afisler.aspx"


def bim_afisler(simdi):
    """Bugün başlayan BİM dönemlerinin resmi afişleri: [(etiket, anahtar, [tam boy afiş adresleri])]."""
    s = getir(BIM_AFIS)
    bloklar = re.split(r"(?=<div[^>]*afis='\d+')", s)
    gun, ay = simdi.day, AYLAR[simdi.month - 1]
    out = []
    for b in bloklar[1:]:
        anahtar = re.search(r"afis='(\d+)'", b).group(1)
        etiket = re.search(r'class="subTabArea[^"]*">\s*<span class="text">([^<]+)</span>', b)
        etiket = temiz(etiket.group(1)) if etiket else ""
        bugun_basliyor = etiket.startswith(f"{gun} {ay} ") or re.match(rf"^{gun}\s*-\s*\d+ {ay}$", etiket)
        if not bugun_basliyor:
            continue
        afisler = list(dict.fromkeys(re.findall(r'class="download" href="(https://cdn\d?\.bim\.com\.tr/uploads/afisler/[^"]+)"', b)))
        if afisler:
            out.append((etiket, anahtar, afisler))
    return out


def bugun_bim(simdi):
    """Bugün başlayan BİM sekmeleri: aktüel ('23 Ekim Cuma') ve haftalık indirim ('23-29 Ekim')."""
    gun = f"{simdi.day} {AYLAR[simdi.month - 1]}"
    for ad, anahtar in bim_sekmeler().items():
        if ad.startswith(gun + " ") or re.match(rf"^{simdi.day}\s*-\s*\d+ {AYLAR[simdi.month - 1]}$", ad):
            yield ad, anahtar, ("indirim" if "-" in ad else "aktuel")


def sok_afisler():
    s = getir(SOK + "/tr/firsatlar")
    for yol in dict.fromkeys(re.findall(r'src="(/uploads/firsatlar/[^"]+\.(?:webp|jpg|jpeg|png))"', s)):
        tur = "Hafta Sonu Fırsatları" if "haftasonu" in yol.lower() else "Haftanın Fırsatları"
        aralik = re.search(r"(\d{1,2}-\d{1,2})", yol.split("-", 1)[-1])
        yield {"url": SOK + yol, "baslik": f"ŞOK {tur}" + (f" ({aralik.group(1)} {AYLAR[datetime.now(TZ).month - 1]})" if aralik else "")}


def a101_afisler():
    """A101 kampanya afişleri. a101.com.tr veri merkezi adreslerini (GitHub) engelliyor ve afişleri tarayıcıda
    yüklüyor; bu yüzden yalnızca yerel sunucuda (ev interneti) Chrome ile sayfa çizdirilerek alınır.
    Sayfa bir doğrulama ekranı gösterirse hiçbir şey alınmaz (aşılmaya çalışılmaz)."""
    import subprocess
    from ciz import CHROME
    dom = subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--virtual-time-budget=12000",
                          f"--user-agent={UA['User-Agent']}", "--dump-dom", "https://www.a101.com.tr/"],
                         capture_output=True, text=True, timeout=90).stdout
    if "Just a moment" in dom[:3000] or len(dom) < 50000:
        raise RuntimeError("A101 sayfası açılmadı (doğrulama ekranı ya da erişim yok)")
    gorulen = {}
    for alt, src in re.findall(r'<img[^>]*alt="([^"]*kampanya afişi[^"]*)"[^>]*src="([^"]+)"', dom) + \
            [(a, s_) for s_, a in re.findall(r'<img[^>]*src="([^"]+)"[^>]*alt="([^"]*kampanya afişi[^"]*)"', dom)]:
        if "cdn2.a101.com.tr" in src:
            gorulen.setdefault(src, html.unescape(alt).replace("geçerli A101 kampanya afişi", "").strip())
    gruplar = {}
    for src, donem in gorulen.items():
        gruplar.setdefault(donem, []).append(src)
    return gruplar  # {"17-23 Ekim": [afiş adresleri], ...}


def a101_haberleri():
    q = urllib.parse.quote("A101 aktüel")
    s = getir(f"https://news.google.com/rss/search?q={q}+when:2d&hl=tr&gl=TR&ceid=TR:tr")
    for baslik, link in re.findall(r"<item><title>(.*?)</title><link>(.*?)</link>", s):
        baslik = html.unescape(baslik).rsplit(" - ", 1)[0]
        if "a101" in baslik.lower() and ("aktüel" in baslik.lower() or "katalog" in baslik.lower()):
            yield {"baslik": baslik, "link": html.unescape(link)}


def market_kampanyalari(simdi, paylas, telegram, telegram_foto_url, telegram_album_url):
    """Yeni kampanyaları gönderir. paylas(ad, sayfalar, aciklama, simdi) zamanli.py'den gelir."""
    durum = json.loads(DURUM.read_text(encoding="utf-8")) if DURUM.exists() else {"gonderilen": {}}
    g = durum["gonderilen"]
    bugun = simdi.strftime("%Y-%m-%d")
    say = 0

    try:
        for etiket, anahtar, afisler in bim_afisler(simdi):
            if f"bimafis:{anahtar}" in g:
                continue
            tur = "haftalık indirim" if "-" in etiket else "aktüel ürünler"
            telegram_album_url(afisler[:10], f"🛒 <b>BİM {tur} — {html.escape(etiket)}</b>\n\nStoklarla sınırlıdır.\n"
                                             f"Kaynak: BİM (resmi afiş)\n\n#düzce #bim #aktüel #indirim #düzceabisi")
            g[f"bimafis:{anahtar}"] = bugun
            say += 1
    except Exception as hata:
        print("BİM hatası:", hata)

    try:
        for a in sok_afisler():
            if f"sok:{a['url']}" in g:
                continue
            telegram_foto_url(a["url"], f"🛒 <b>{html.escape(a['baslik'])}</b>\n\nStoklarla sınırlıdır.\nKaynak: ŞOK Marketler (resmi afiş)")
            g[f"sok:{a['url']}"] = bugun
            say += 1
    except Exception as hata:
        print("ŞOK hatası:", hata)

    try:  # A101: yalnızca yerel sunucuda çalışır (bkz. a101_afisler); GitHub'da hata verir ve atlanır
        for donem, afisler in a101_afisler().items():
            yeni = [u for u in afisler if f"a101:{u}" not in g]
            if not yeni:
                continue
            telegram_album_url(yeni[:10], f"🛒 <b>A101 kampanya afişleri — {html.escape(donem)}</b>\n\n"
                                          f"Stoklarla sınırlıdır.\nKaynak: A101 (resmi afiş)\n\n#düzce #a101 #aktüel #düzceabisi")
            for u in yeni:
                g[f"a101:{u}"] = bugun
            say += 1
    except Exception as hata:
        print("A101 atlandı:", hata)

    sinir = (simdi - timedelta(days=21)).strftime("%Y-%m-%d")
    durum["gonderilen"] = {k: v for k, v in g.items() if v >= sinir}
    DURUM.parent.mkdir(exist_ok=True)
    DURUM.write_text(json.dumps(durum, ensure_ascii=False), encoding="utf-8")
    return say


if __name__ == "__main__":
    simdi = datetime.now(TZ)
    print(list(bugun_bim(simdi)))
    for ad, k, t in bugun_bim(simdi):
        print(ad, t, bim_urunler(k)[:3])
    print(list(sok_afisler()))
    print(list(a101_haberleri())[:3])
