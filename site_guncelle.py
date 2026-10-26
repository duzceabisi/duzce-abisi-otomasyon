#!/usr/bin/env python3
"""haber.duzceabisi.com'daki günlük bilgileri günceller (döngü her 5 dakikada bir çağırır).

Telegram paylaşımlarından bağımsızdır: hafıza dosyalarına dokunmaz, sessiz saatte de çalışır.
Her bölümün kendi aralığı var; vakti gelmeyen atlanır (durum/site.json):
  deprem 5 dk · eczane, hava, piyasa, vefat, iş ilanları 30 dk · namaz 6 saat
Kullanım:  python3 site_guncelle.py           vakti gelenler
           python3 site_guncelle.py hepsi     hepsini hemen
"""
import json, sys, time, xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import haber_sitesi

KOK = Path(__file__).resolve().parent
DURUM = KOK / "durum" / "site.json"
TZ = ZoneInfo("Europe/Istanbul")
DK = 60


def eczane():
    from topla import topla
    e = topla(("eczaneler",)).get("eczaneler")
    return haber_sitesi.blok("eczane", e) if e and e.get("liste") else None


def hava():
    from topla import topla
    bugun, yarin = topla(("hava",)).get("hava"), topla(("hava",), gun=1).get("hava")
    return haber_sitesi.blok("hava", {"bugun": bugun, "yarin": yarin}) if bugun else None


def piyasa():
    from topla import topla
    p = topla(("piyasa", "akaryakit"))
    if not p.get("altin") and not p.get("doviz"):
        return None
    return haber_sitesi.blok("piyasa", {k: p.get(k) for k in ("doviz", "altin", "piyasa_saat", "piyasa_kaynak", "akaryakit")})


def namaz():
    from ekler import namaz as vakitler
    v = vakitler()
    return haber_sitesi.blok("namaz", {"tarih": datetime.now(TZ).strftime("%Y-%m-%d"), "vakitler": v}) if v else None


def vefat():
    import vefat as v
    simdi = datetime.now(TZ)
    kayitlar, gorulen = [], set()
    for it in ET.fromstring(v.getir(v.RSS)).iter("item"):
        tarih = it.findtext("pubDate")
        if "vefat" not in (it.findtext("title") or "").lower() or not tarih:
            continue
        zaman = parsedate_to_datetime(tarih)
        if simdi - zaman > v.GERI:
            continue
        for k in v.kayitlar(v.getir(it.findtext("link")).decode("utf-8", "replace")):
            a = v.anahtar(k)
            if a not in gorulen:
                gorulen.add(a)
                kayitlar.append({"anahtar": a, "zaman": zaman.isoformat(), "veri": k})
    return haber_sitesi.liste("vefat", kayitlar)


def deprem():
    from deprem import uzaklik
    from ekler import depremler
    kayitlar = []
    for d in depremler():
        km = uzaklik(d["enlem"], d["boylam"])
        if km > 300:
            continue
        zaman = datetime.strptime(d["zaman"], "%Y.%m.%d %H:%M:%S").replace(tzinfo=TZ)
        kayitlar.append({"anahtar": d["id"], "zaman": zaman.isoformat(), "veri": {
            "zaman": zaman.strftime("%d.%m %H:%M"), "buyukluk": d["buyukluk"], "yer": d["yer"].title(),
            "derinlik": d["derinlik"], "km": round(km, 1)}})
    return haber_sitesi.liste("deprem", kayitlar)


def is_ilanlari():
    from is_ilanlari import eleman, iskur
    kayitlar = []
    for kaynak in (iskur, eleman):  # biri çökerse öbürü yine gelsin
        try:
            for i in kaynak():
                kayitlar.append({"anahtar": i["anahtar"], "zaman": datetime.now(TZ).isoformat(),
                                 "veri": {k: i.get(k, "") for k in ("kaynak", "baslik", "firma", "yer", "kisi", "son", "link")}})
        except Exception as hata:
            print(f"iş ilanları ({kaynak.__name__}):", hata, file=sys.stderr)
    return haber_sitesi.liste("is", kayitlar)


ISLER = [("deprem", deprem, 5 * DK), ("eczane", eczane, 30 * DK), ("hava", hava, 30 * DK), ("piyasa", piyasa, 30 * DK),
         ("vefat", vefat, 30 * DK), ("is", is_ilanlari, 30 * DK), ("namaz", namaz, 360 * DK)]


def main():
    if not haber_sitesi.acik():
        print("SITE_URL / SITE_ANAHTAR tanımlı değil, site güncellenmedi")
        return
    hepsi = sys.argv[1:] == ["hepsi"]
    durum = json.loads(DURUM.read_text(encoding="utf-8")) if DURUM.exists() else {}
    simdi = time.time()
    for ad, is_, aralik in ISLER:
        if not hepsi and simdi - durum.get(ad, 0) < aralik - 30:
            continue
        try:
            sonuc = is_()
            print(f"site {ad}:", "tamam" if sonuc else "veri yok ya da gönderilemedi")
            if sonuc:
                durum[ad] = simdi
        except Exception as hata:  # bir bölüm çökerse diğerleri yine güncellensin
            print(f"site {ad} hatası:", hata, file=sys.stderr)
    DURUM.parent.mkdir(exist_ok=True)
    DURUM.write_text(json.dumps(durum), encoding="utf-8")


if __name__ == "__main__":
    main()
