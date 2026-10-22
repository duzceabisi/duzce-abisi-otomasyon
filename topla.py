#!/usr/bin/env python3
"""Düzce Abisi sabah paketi için kesin verileri kaynaklarından toplar.

Kullanım:  python3 topla.py            -> veri/YYYY-MM-DD-sabah.json
Toplanan:  hava (Open-Meteo), döviz ve altın (Truncgil Finans), akaryakıt (Opet),
           nöbetçi eczaneler (eczaneler.gen.tr).
Manşet, elektrik kesintisi, etkinlik, tarihte bugün, önemli gün ve burçlar bu
dosyanın üstüne Claude tarafından eklenir (bkz. GOREV.md).

Bir kaynak çökerse o bölüm boş kalır ve "eksik" listesine yazılır; diğerleri
yine toplanır.
"""
import html, json, re, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

KOK = Path(__file__).resolve().parent
TZ = ZoneInfo("Europe/Istanbul")
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8"}
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

# WMO hava kodu -> (açıklama, ikon)
WMO = {0: ("Açık", "☀️"), 1: ("Az bulutlu", "🌤️"), 2: ("Parçalı bulutlu", "⛅"), 3: ("Çok bulutlu", "☁️"),
       45: ("Sisli", "🌥️"), 48: ("Kırağılı sis", "🌥️"), 51: ("Hafif çisenti", "🌦️"), 53: ("Çisenti", "🌦️"),
       55: ("Yoğun çisenti", "🌧️"), 61: ("Hafif yağmurlu", "🌦️"), 63: ("Yağmurlu", "🌧️"), 65: ("Kuvvetli yağmur", "🌧️"),
       66: ("Dondurucu yağmur", "🌧️"), 67: ("Dondurucu yağmur", "🌧️"), 71: ("Hafif kar", "🌨️"), 73: ("Karlı", "🌨️"),
       75: ("Yoğun kar", "❄️"), 77: ("Kar taneleri", "🌨️"), 80: ("Sağanak", "🌦️"), 81: ("Sağanak yağışlı", "🌧️"),
       82: ("Şiddetli sağanak", "⛈️"), 85: ("Kar sağanağı", "🌨️"), 86: ("Yoğun kar sağanağı", "❄️"),
       95: ("Gök gürültülü sağanak", "⛈️"), 96: ("Dolu ihtimalli fırtına", "⛈️"), 99: ("Dolu ihtimalli fırtına", "⛈️")}


def getir(url, json_mi=True):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        veri = r.read().decode("utf-8")
    return json.loads(veri) if json_mi else veri


def hava():
    d = getir("https://api.open-meteo.com/v1/forecast?latitude=40.8438&longitude=31.1565"
              "&hourly=temperature_2m,precipitation_probability,weather_code"
              "&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max,weather_code,wind_speed_10m_max"
              "&timezone=Europe%2FIstanbul&forecast_days=1")
    g, s = d["daily"], d["hourly"]
    kod = s["weather_code"][12]  # günün havası: öğle saati
    sisli = any(s["weather_code"][h] in (45, 48) for h in range(6, 11))
    yagis = g["precipitation_probability_max"][0] or 0
    saatlik = []
    for saat in (9, 12, 15, 18, 21):
        k = s["weather_code"][saat]
        saatlik.append([f"{saat:02d}.00", round(s["temperature_2m"][saat]), WMO.get(k, ("", "🌡️"))[1]])
    ruzgar = round(g["wind_speed_10m_max"][0])
    return {
        "durum": WMO.get(kod, ("Değişken", "🌡️"))[0], "ikon": WMO.get(kod, ("", "🌡️"))[1],
        "en_dusuk": round(g["temperature_2m_min"][0]), "en_yuksek": round(g["temperature_2m_max"][0]),
        "yagis_ihtimali": yagis,
        "yagmur": "Yağış beklenmiyor" if yagis < 30 else f"Yağış ihtimali %{yagis}",
        "semsiye": "Gerekmiyor" if yagis < 30 else ("Yanınıza alın" if yagis < 60 else "Mutlaka alın"),
        "saatlik": saatlik,
        "ruzgar": f"En fazla {ruzgar} km/sa",
        "not": "Sabah saatlerinde yer yer sis var; sürücüler dikkatli olsun." if sisli else "",
        "kaynak": "Open-Meteo",
    }


def piyasa():
    d = getir("https://finans.truncgil.com/today.json")
    doviz = [[b, ad, d[k]["Alış"], d[k]["Satış"]] for b, ad, k in
             [("🇺🇸", "Dolar", "USD"), ("🇪🇺", "Euro", "EUR"), ("🇬🇧", "Sterlin", "GBP")]]
    altin = [[ad, d[k]["Alış"], d[k]["Satış"]] for ad, k in
             [("Gram", "gram-altin"), ("Çeyrek", "ceyrek-altin"), ("Yarım", "yarim-altin"), ("Tam", "tam-altin"),
              ("Cumhuriyet", "cumhuriyet-altini"), ("Ata", "ata-altin")]]
    saat = d.get("Update_Date", "")[11:16].replace(":", ".")
    return doviz, altin, saat


def akaryakit():
    d = getir("https://api.opet.com.tr/api/fuelprices/prices?ProvinceCode=81")
    merkez = next((r for r in d if r["districtName"] == "MERKEZ"), d[0])
    istenen = [("Benzin", "Kurşunsuz Benzin 95"), ("Motorin", "Motorin EcoForce"), ("LPG", "Otogaz")]
    fiyat = {p["productName"]: p["amount"] for p in merkez["prices"]}
    liste = [[ad, f"{fiyat[urun]:.2f}".replace(".", ",")] for ad, urun in istenen if urun in fiyat]
    return {"ilce": merkez["districtName"].title(), "liste": liste, "kaynak": "Opet"}


def eczaneler():
    """Bu akşamın Düzce Merkez nöbetçileri: önce Eczacı Odası, olmazsa eczaneler.gen.tr."""
    try:
        return eczaneler_oda()
    except Exception as hata:
        try:
            return eczaneler_gentr()
        except Exception:
            raise hata


def eczaneler_oda():
    bugun = datetime.now(TZ)
    istek = urllib.request.Request("https://www.duzceeo.org/nobetkarti", headers=UA, data=urllib.parse.urlencode(
        {"tarihk": f"{bugun:%Y-%m-%d}", "ilce": "1292", "gnr": "NÖBET ARA"}).encode())  # 1292 = Merkez
    with urllib.request.urlopen(istek, timeout=20) as r:
        s = r.read().decode("utf-8")
    # oda sitesi İ yerine çoğu yerde I yazıyor; küçük harfe çevirmek "Demır" gibi bozuk sonuç verir, olduğu gibi bırak
    liste = [[ad.strip(), re.sub(r"\s+", " ", adres).strip(), tel.strip()] for ad, adres, tel in re.findall(
        r'class="adi"[^>]*>\s*([^<]+?)\s*</div>.*?class="adres">\s*(.*?)\s*<br>\s*<b>TEL:</b>\s*([^<]+)</div>', s, re.S)]
    if not liste:
        raise ValueError("Eczacı Odası listesi boş")
    yarin = bugun + timedelta(days=1)
    return {"donem": f"{bugun.day} {AYLAR[bugun.month - 1]} {GUNLER[bugun.weekday()]} akşamı → "
                     f"{yarin.day} {AYLAR[yarin.month - 1]} {GUNLER[yarin.weekday()]} sabahı",
            "bolge": "Düzce Merkez", "liste": liste, "kaynak": "Düzce Eczacı Odası"}


def eczaneler_gentr():
    s = getir("https://www.eczaneler.gen.tr/nobetci-duzce", json_mi=False)
    bas = s.index('id="nav-bugun"')
    bit = s.find('id="nav-yarin"', bas)
    p = s[bas:bit if bit > 0 else None]
    donem = re.search(r"alert-warning[^>]*>([^<]+)<", p).group(1).strip().rstrip(".")
    liste = []
    for satir in re.findall(r"<tr>(.*?)</tr>", p, re.S):
        ad = re.search(r'class="isim">([^<]+)<', satir)
        if not ad:
            continue
        adres = re.search(r"<div class='col-lg-6'>([^<]+)<", satir)
        ilce = re.search(r"bg-info text-white[^>]*>([^<]+)<", satir)
        tel = re.search(r"<div class='col-lg-3 py-lg-2'>([^<]+)<", satir)
        liste.append({"ad": html.unescape(ad.group(1)).strip(),
                      "adres": html.unescape(adres.group(1)).replace(" / Düzce", "").strip() if adres else "",
                      "ilce": ilce.group(1).strip() if ilce else "",
                      "tel": tel.group(1).replace("0 (", "0").replace(") ", " ").replace("-", " ").strip() if tel else ""})
    merkez = [[e["ad"], e["adres"], e["tel"]] for e in liste if e["ilce"] == "Merkez"]
    return {"donem": donem.replace("akşamından", "akşamı →").replace(" kadar", "").replace("sabahına", "sabahı"),
            "bolge": "Düzce Merkez", "liste": merkez,
            "diger_ilceler": [[e["ilce"], e["ad"], e["tel"]] for e in liste if e["ilce"] != "Merkez"],
            "kaynak": "eczaneler.gen.tr"}


def main():
    simdi = datetime.now(TZ)
    out = {"tarih": f"{simdi.day} {AYLAR[simdi.month - 1]} {simdi.year}", "gun": GUNLER[simdi.weekday()],
           "toplandi": simdi.strftime("%Y-%m-%d %H:%M"), "eksik": []}
    for ad, is_ in [("hava", hava), ("piyasa", piyasa), ("akaryakit", akaryakit), ("eczaneler", eczaneler)]:
        try:
            sonuc = is_()
            if ad == "piyasa":
                out["doviz"], out["altin"], out["piyasa_saat"] = sonuc
                out["piyasa_kaynak"] = "Truncgil Finans"
            else:
                out[ad] = sonuc
        except Exception as hata:  # bir kaynak çökerse diğerleri yine toplansın
            out["eksik"].append(f"{ad}: {hata}")
    hedef = KOK / "veri" / f"{simdi:%Y-%m-%d}-sabah.json"
    if len(sys.argv) > 1:
        hedef = Path(sys.argv[1])
    hedef.parent.mkdir(exist_ok=True)
    hedef.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(hedef)
    if out["eksik"]:
        print("EKSİK:", *out["eksik"], sep="\n  ", file=sys.stderr)


if __name__ == "__main__":
    main()
