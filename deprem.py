#!/usr/bin/env python3
"""Düzce ve çevresindeki depremleri Kandilli'den izler, uyarı gönderir.

Kural (biri yeterli):
  - Düzce'ye 100 km içinde, büyüklük >= 3.0
  - Düzce'ye 300 km içinde, büyüklük >= 4.5
  - Türkiye'nin herhangi bir yerinde, büyüklük >= 6.0
İlk çalıştırmada mevcut liste yalnızca kaydedilir (eski depremler gönderilmez).
"""
import json, math, sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from ekler import depremler

KOK = Path(__file__).resolve().parent
DURUM = KOK / "durum" / "deprem.json"
TZ = ZoneInfo("Europe/Istanbul")
DUZCE = (40.8438, 31.1565)
KURALLAR = [(100, 3.0), (300, 4.5), (5000, 6.0)]  # (km, en az büyüklük)


def uzaklik(enlem, boylam):
    a1, b1, a2, b2 = map(math.radians, (DUZCE[0], DUZCE[1], enlem, boylam))
    return 6371 * 2 * math.asin(math.sqrt(math.sin((a2 - a1) / 2) ** 2 + math.cos(a1) * math.cos(a2) * math.sin((b2 - b1) / 2) ** 2))


def onemli_mi(d):
    km = uzaklik(d["enlem"], d["boylam"])
    return any(km <= sinir and d["buyukluk"] >= mag for sinir, mag in KURALLAR), km


def main():
    from haber_takip import gonder_haber, telegram
    simdi = datetime.now(TZ)
    ilk = not DURUM.exists()
    durum = json.loads(DURUM.read_text(encoding="utf-8")) if not ilk else {"gorulen": {}}
    for d in sorted(depremler(), key=lambda x: x["id"]):
        if d["id"] in durum["gorulen"]:
            continue
        durum["gorulen"][d["id"]] = simdi.strftime("%Y-%m-%d")
        uygun, km = onemli_mi(d)
        if ilk or not uygun:
            continue
        saat = d["zaman"][11:16].replace(":", ".")
        baslik = f"{d['buyukluk']:.1f} büyüklüğünde deprem: {d['yer'].title()}"
        metin = (f"Düzce'ye yaklaşık {round(km)} km uzaklıkta, {d['derinlik']:.0f} km derinlikte. "
                 f"Saat {saat}.")
        # haber kartı altyapısını kullan: deprem kategorisi önemli → kartla gider
        gonder_haber({"haberler": [{"site": "Kandilli Rasathanesi", "baslik": baslik, "zaman": simdi.replace(
            hour=int(saat[:2]), minute=int(saat[3:])), "link": "http://www.koeri.boun.edu.tr/scripts/lst0.asp"}],
            "ozet": metin}, simdi)
        print("deprem uyarısı:", baslik)
    sinir = (simdi - timedelta(days=3)).strftime("%Y-%m-%d")
    durum["gorulen"] = {k: v for k, v in durum["gorulen"].items() if v >= sinir}
    DURUM.parent.mkdir(exist_ok=True)
    DURUM.write_text(json.dumps(durum), encoding="utf-8")
    print(f"deprem: {len(durum['gorulen'])} kayıt, ilk={ilk}")


if __name__ == "__main__":
    main()
