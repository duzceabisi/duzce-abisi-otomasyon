#!/usr/bin/env python3
"""Saati gelen zamanlı paylaşımları üretir (haber takibiyle aynı sunucu işinde, 10 dakikada bir çağrılır).

Her görev günde bir kez, saati geldikten sonraki ilk taramada çalışır; 3 saatten
fazla geciktiyse o gün atlanır (örneğin sunucu saatlerce durduysa eski içerik gitmesin).

  08:00  burc       Günlük burç yorumları
  10:00  market     BİM ve ŞOK resmi kampanya afişleri (yeni olanlar)
  12:00  tarihte    Tarihte bugün ve özel günler
  13:00  is_ozet    Son 24 saatte açılan iş ilanları
  19:30  ozet       Günün öne çıkan haberleri
  Pzt 10:00  etkinlik_hafta   Son 7 günde duyurulan etkinlikler
  Cum 17:00  hafta_sonu       Hafta sonu etkinlikleri

Kullanım:  python3 zamanli.py            saati gelenleri çalıştırır
           python3 zamanli.py ozet       belirli bir görevi hemen çalıştırır (deneme için)
"""
import json, subprocess, sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

KOK = Path(__file__).resolve().parent
TZ = ZoneInfo("Europe/Istanbul")
DURUM = KOK / "durum" / "zamanli.json"
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
ETIKET = "#düzce #düzcehaber #düzceabisi"


def oku_json(ad):
    p = KOK / "durum" / ad
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def son_gunler(veri, gun_sayisi, simdi):
    sinir = (simdi - timedelta(days=gun_sayisi)).strftime("%Y-%m-%d")
    return [k for g, liste in sorted(veri.items()) if g >= sinir for k in liste]


def parcala(satirlar, n):
    return [satirlar[i:i + n] for i in range(0, len(satirlar), n)] or [[]]


# --- görevler: (sayfalar, açıklama) döndürür; içerik yoksa None -----------------

def burc(simdi):
    from burc import gunluk_burclar
    b = gunluk_burclar(simdi.date())
    satir = [[f"{x['simge']} {x['ad']}", f"{x['yorum']}  ·  Şans: {x['sans']}"] for x in b]
    sayfalar = [{"ad": f"burc-{i + 1}", "etiket": "Günlük burç yorumları", "baslik": "Bugün yıldızlar ne diyor?",
                 "alt": "Eğlence amaçlıdır.", "satirlar": p, "sinif": "burcsayfa", "boy": 56}
                for i, p in enumerate(parcala(satir, 3))]
    return sayfalar, f"🔮 Günlük burç yorumları — {simdi.day} {AYLAR[simdi.month - 1]}\n\nBurcunu bul, arkadaşını etiketle 👇\n\n{ETIKET} #burç #burçyorumları"


def tarihte(simdi):
    from ekler import tarihte_bugun
    t = tarihte_bugun(simdi)
    sayfalar = [{"ad": "tarihte", "etiket": "📜 Tarihte bugün", "baslik": f"{simdi.day} {AYLAR[simdi.month - 1]}", "satirlar": t["olaylar"]}]
    if t["gunler"]:
        sayfalar.append({"ad": "ozel-gunler", "etiket": "Bugünün özel günleri", "baslik": "Bugün dünyada",
                         "satirlar": [["📅", g] for g in t["gunler"]]})
    return sayfalar, f"📜 Tarihte bugün: {simdi.day} {AYLAR[simdi.month - 1]}\n\nKaynak: Vikipedi\n\n{ETIKET} #tarihtebugün"


def is_ozet(simdi):
    ilanlar = son_gunler(oku_json("gunluk_is.json"), 1, simdi)
    if not ilanlar:
        return None
    satir = [[i["baslik"][:22], ", ".join(x for x in [i.get("firma"), i.get("yer"), f"{i['kisi']} kişi" if i.get("kisi") else "",
                                                       f"son başvuru {i['son']}" if i.get("son") else ""] if x)] for i in ilanlar[:24]]
    sayfalar = [{"ad": f"is-{n + 1}", "etiket": "💼 Düzce iş ilanları", "baslik": "Bugün açılan ilanlar",
                 "alt": f"{len(ilanlar)} yeni ilan · başvuru bilgileri açıklamada", "satirlar": p, "boy": 60}
                for n, p in enumerate(parcala(satir, 7))]
    kaynak = ", ".join(sorted({i["kaynak"] for i in ilanlar}))
    return sayfalar, (f"💼 Düzce'de bugün {len(ilanlar)} yeni iş ilanı\n\nİş arayan tanıdıklarınızı etiketleyin 👇\n\n"
                      f"Kaynak: {kaynak}\n\n{ETIKET} #düzceişilanları #işilanı")


def ozet(simdi):
    haberler = son_gunler(oku_json("gunluk_haber.json"), 0, simdi)
    if not haberler:
        return None
    sirali = sorted(haberler, key=lambda h: (h["onemli"], len(h["siteler"])), reverse=True)[:10]
    satir = [[h["etiket"].split(" ", 1)[0] + " " + h["saat"], h["baslik"]] for h in sirali]
    sayfalar = [{"ad": f"ozet-{n + 1}", "etiket": "📰 Günün özeti", "baslik": f"Düzce'de bugün ({simdi.day} {AYLAR[simdi.month - 1]})",
                 "satirlar": p, "boy": 56} for n, p in enumerate(parcala(satir, 5))]
    kaynak = ", ".join(sorted({s for h in sirali for s in h["siteler"]}))
    from ai import gunun_ozeti
    giris = gunun_ozeti([h["baslik"] for h in sirali])
    return sayfalar, (f"📰 Düzce'de bugün neler oldu? {simdi.day} {AYLAR[simdi.month - 1]} {GUNLER[simdi.weekday()]}\n\n"
                      + (f"{giris}\n\n" if giris else "")
                      + "\n".join(f"• {h['baslik']}" for h in sirali) + f"\n\nKaynaklar: {kaynak}\n\n{ETIKET} #düzcegündem")


def _etkinlik(simdi, baslik, ac):
    etk = [h for h in son_gunler(oku_json("gunluk_haber.json"), 7, simdi) if h["kod"] in ("etkinlik", "firsat")]
    if not etk:
        return None
    satir = [["🎭" if h["kod"] == "etkinlik" else "⭐", h["baslik"]] for h in etk[-10:]]
    sayfalar = [{"ad": f"etkinlik-{n + 1}", "etiket": "Düzce'de etkinlik ve fırsatlar", "baslik": baslik, "satirlar": p, "boy": 60}
                for n, p in enumerate(parcala(satir, 5))]
    kaynak = ", ".join(sorted({s for h in etk for s in h["siteler"]}))
    return sayfalar, f"{ac}\n\n" + "\n".join(f"• {h['baslik']}" for h in etk[-10:]) + f"\n\nKaynaklar: {kaynak}\n\n{ETIKET} #düzceetkinlik"


def etkinlik_hafta(simdi):
    return _etkinlik(simdi, "Bu hafta Düzce'de", "🎭 Bu hafta Düzce'de etkinlikler ve fırsatlar")


def hafta_sonu(simdi):
    return _etkinlik(simdi, "Hafta sonu Düzce'de", "🎉 Hafta sonu Düzce'de ne var?")


def market(simdi):
    """BİM/ŞOK/A101 kampanyaları kendi içinde gönderilir (bkz. market.py); burada sayfa döndürülmez."""
    from haber_takip import telegram, telegram_album_url, telegram_foto_url
    from market import market_kampanyalari
    print("market kampanyası:", market_kampanyalari(simdi, paylas, telegram, telegram_foto_url, telegram_album_url))
    return None


# (görev, saat, dakika, haftanın günleri: None = her gün, 0 = Pazartesi)
GOREVLER = [
    ("burc", 8, 0, None, burc),
    ("market", 10, 0, None, market),
    ("tarihte", 12, 0, None, tarihte),
    ("is_ozet", 13, 0, None, is_ozet),
    ("ozet", 19, 30, None, ozet),
    ("etkinlik_hafta", 10, 0, {0}, etkinlik_hafta),
    ("hafta_sonu", 17, 0, {4}, hafta_sonu),
]


def paylas(ad, sayfalar, aciklama, simdi):
    d = {"tarih": f"{simdi.day} {AYLAR[simdi.month - 1]} {simdi.year}", "gun": GUNLER[simdi.weekday()], "sayfalar": sayfalar}
    isim = f"{simdi:%Y-%m-%d}-{ad}"
    veri = KOK / "veri" / f"{isim}.json"
    veri.parent.mkdir(exist_ok=True)
    veri.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    subprocess.run([sys.executable, str(KOK / "ciz.py"), str(veri)], check=True)
    subprocess.run([sys.executable, str(KOK / "gonder.py"), str(KOK / "cikti" / isim), aciklama[:1024]], check=True)


def haber_kartlari(simdi, en_fazla=6):
    """Önizleme için: son 24 saatin önemli haberlerini (yapay zekâ özetli hikâye kartı) yeniden gönderir."""
    from haber_takip import gonder_haber
    haberler = [h for h in son_gunler(oku_json("gunluk_haber.json"), 1, simdi) if h["onemli"]]
    for h in sorted(haberler, key=lambda h: len(h["siteler"]), reverse=True)[:en_fazla]:
        gonder_haber({"haberler": [{"site": s, "baslik": h["baslik"], "link": h["link"], "zaman": None} for s in h["siteler"]]},
                     simdi, kaydet=False)


def onizleme(simdi):
    """Bir günün bütün paylaşımlarını saat sırasıyla hemen gönderir; hiçbir hafıza dosyasına yazmaz."""
    import tempfile
    import market as mk
    from haber_takip import telegram, telegram_album_url, telegram_foto_url

    def calistir(mod):
        subprocess.run([sys.executable, str(KOK / "calistir.py"), mod, "--onizleme"], check=False)

    adimlar = [("gunaydin", lambda: calistir("gunaydin")), ("burc", None), ("piyasa", lambda: calistir("piyasa")),
               ("market", None), ("tarihte", None), ("is_ozet", None), ("haber_kartlari", lambda: haber_kartlari(simdi)),
               ("eczane", lambda: calistir("eczane")), ("ozet", None), ("yarin", lambda: calistir("yarin")),
               ("etkinlik_hafta", None)]
    gorev = {ad: is_ for ad, _, _, _, is_ in GOREVLER}
    for ad, ozel in adimlar:
        try:
            if ozel:
                ozel()
            elif ad == "market":  # gönderilmiş sayılanları da göstermek için geçici, boş bir hafıza kullan
                mk.DURUM = Path(tempfile.mkdtemp()) / "market.json"
                mk.market_kampanyalari(simdi, paylas, telegram, telegram_foto_url, telegram_album_url)
            else:
                sonuc = gorev[ad](simdi)
                if sonuc:
                    paylas(f"onizleme-{ad}", *sonuc, simdi)
            print("önizleme:", ad)
        except Exception as hata:
            print(f"önizleme HATA {ad}: {hata}", file=sys.stderr)


def main():
    simdi = datetime.now(TZ)
    if len(sys.argv) > 1 and sys.argv[1] == "onizleme":
        onizleme(simdi)
        return
    durum = json.loads(DURUM.read_text(encoding="utf-8")) if DURUM.exists() else {}
    bugun = simdi.strftime("%Y-%m-%d")
    elle = sys.argv[1] if len(sys.argv) > 1 else None
    for ad, saat, dakika, gunler, is_ in GOREVLER:
        if elle:
            if ad != elle:
                continue
        else:
            zaman = simdi.replace(hour=saat, minute=dakika, second=0, microsecond=0)
            if durum.get(ad) == bugun or (gunler is not None and simdi.weekday() not in gunler) \
                    or not (zaman <= simdi < zaman + timedelta(hours=3)):
                continue
        try:
            sonuc = is_(simdi)
            if sonuc:
                paylas(ad, *sonuc, simdi)
                print("paylaşıldı:", ad)
            else:
                print("içerik yok, atlandı:", ad)
            durum[ad] = bugun
        except Exception as hata:  # bir görev bozulursa diğerleri çalışsın; bir sonraki taramada yeniden dener
            print(f"HATA {ad}: {hata}", file=sys.stderr)
    DURUM.parent.mkdir(exist_ok=True)
    DURUM.write_text(json.dumps(durum), encoding="utf-8")


if __name__ == "__main__":
    main()
