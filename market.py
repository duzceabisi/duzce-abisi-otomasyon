#!/usr/bin/env python3
"""Market kampanyaları: BİM aktüel/indirim, ŞOK haftalık afişleri, A101 aktüel haberleri.

zamanli.py her gün 10:00'da market_kampanyalari() çağırır; her kampanya bir kez gönderilir.
  BİM   bim.com.tr          O gün başlayan aktüel ürünler + o gün başlayan haftalık indirim (tasarımlı sayfa)
  ŞOK   kurumsal.sokmarket  Resmi "Haftanın Fırsatları" / "Hafta Sonu" afişi (afişin kendisi)
  A101  Google Haberler     a101.com.tr sunucuyu engelliyor; "A101 aktüel" haberinin başlığı ve bağlantısı
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


def a101_haberleri():
    q = urllib.parse.quote("A101 aktüel")
    s = getir(f"https://news.google.com/rss/search?q={q}+when:2d&hl=tr&gl=TR&ceid=TR:tr")
    for baslik, link in re.findall(r"<item><title>(.*?)</title><link>(.*?)</link>", s):
        baslik = html.unescape(baslik).rsplit(" - ", 1)[0]
        if "a101" in baslik.lower() and ("aktüel" in baslik.lower() or "katalog" in baslik.lower()):
            yield {"baslik": baslik, "link": html.unescape(link)}


def market_kampanyalari(simdi, paylas, telegram, telegram_foto_url):
    """Yeni kampanyaları gönderir. paylas(ad, sayfalar, aciklama, simdi) zamanli.py'den gelir."""
    durum = json.loads(DURUM.read_text(encoding="utf-8")) if DURUM.exists() else {"gonderilen": {}}
    g = durum["gonderilen"]
    bugun = simdi.strftime("%Y-%m-%d")
    say = 0

    try:
        for ad, anahtar, tur in bugun_bim(simdi):
            if f"bim:{anahtar}" in g:
                continue
            urunler = bim_urunler(anahtar)
            if not urunler:
                continue
            satir = [[u["fiyat"], " ".join(x for x in [u["marka"], tr_baslik(u["ad"])] if x)
                      + (f"  ({u['eski']} yerine, {u['indirim']} indirim)" if tur == "indirim" and u["indirim"] else "")]
                     for u in urunler[:24]]
            baslik = "BİM'de bugün aktüel" if tur == "aktuel" else "BİM haftalık indirim"
            sayfalar = [{"ad": f"bim-{n // 8 + 1}", "etiket": f"🛒 BİM · {ad}", "baslik": baslik, "satirlar": satir[n:n + 8], "boy": 64}
                        for n in range(0, len(satir), 8)]
            aciklama = (f"🛒 {baslik}! {ad}\n\n" + "\n".join(f"• {tr_baslik(u['ad'])} — {u['fiyat']}" for u in urunler[:15])
                        + ("\n…" if len(urunler) > 15 else "") + "\n\nStoklarla sınırlıdır.\nKaynak: bim.com.tr\n\n#düzce #bim #aktüel #indirim #düzceabisi")
            paylas(f"bim-{anahtar}", sayfalar, aciklama[:1024], simdi)
            g[f"bim:{anahtar}"] = bugun
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

    try:
        for a in list(a101_haberleri())[:2]:
            if f"a101:{a['baslik']}" in g:
                continue
            telegram(f"🛒 <b>A101 aktüel</b>\n{html.escape(a['baslik'])}\n📰 <a href=\"{html.escape(a['link'])}\">Haberi oku</a>")
            g[f"a101:{a['baslik']}"] = bugun
            say += 1
    except Exception as hata:
        print("A101 hatası:", hata)

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
