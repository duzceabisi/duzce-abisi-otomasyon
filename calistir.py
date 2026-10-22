#!/usr/bin/env python3
"""Düzce Abisi günlük paylaşımlarını üretir ve Telegram'a gönderir.

Kullanım:  python3 calistir.py <mod>
Modlar (sunucudaki saatleri .github/workflows/sabah.yml'de):
  gunaydin  06:30  bugünün havası
  piyasa    09:30  döviz, altın, akaryakıt (piyasa 09:00'da açılıyor)
  eczane    18:00  bu gecenin nöbetçi eczaneleri (nöbet 18:30'da başlıyor)
  yarin     21:00  yarının havası
Adımlar: topla.py (veri) -> ciz.py (görseller) -> gonder.py (Telegram)
"""
import json, subprocess, sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from topla import topla
import vefat

KOK = Path(__file__).resolve().parent
TZ = ZoneInfo("Europe/Istanbul")
ETIKET = "#düzce #düzcehaber #düzceabisi"

# mod -> (toplanacak bölümler, gün farkı, açıklama metni)
MODLAR = {
    "gunaydin": (("hava", "vefat"), 0,
                 lambda d: f"☀️ Günaydın Düzce! {d['tarih']} {d['gun']}\n\n"
                           f"Bugün hava {d['hava']['durum'].lower()}, {d['hava']['en_dusuk']}–{d['hava']['en_yuksek']}°C. "
                           f"Şemsiye: {d['hava']['semsiye'].lower()}.\n\n{ETIKET} #havadurumu"),
    "piyasa": (("piyasa", "akaryakit"), 0,
               lambda d: f"💰 Düzce'de bugün piyasa — {d['tarih']}\n\n"
                         f"Döviz, altın ve akaryakıt fiyatları 👇\n\n{ETIKET} #altın #dolar #benzin"),
    "eczane": (("eczaneler",), 0,
               lambda d: f"💊 Bu gece nöbetçi eczaneler — {d['eczaneler']['donem']}\n\n"
                         f"Merkez ve ilçelerin listesi 👇 Gitmeden önce telefonla teyit edin.\n\n{ETIKET} #nöbetçieczane"),
    "yarin": (("hava", "vefat"), 1,
              lambda d: f"🌙 Yarın Düzce'de hava nasıl? {d['tarih']} {d['gun']}\n\n"
                        f"{d['hava']['durum']}, {d['hava']['en_dusuk']}–{d['hava']['en_yuksek']}°C. "
                        f"Şemsiye: {d['hava']['semsiye'].lower()}.\n\n{ETIKET} #havadurumu"),
}


def main():
    mod = sys.argv[1] if len(sys.argv) > 1 else ""
    if mod not in MODLAR:
        sys.exit(f"Mod seçin: {', '.join(MODLAR)}")
    bolumler, gun, metin = MODLAR[mod]
    d = topla([b for b in bolumler if b != "vefat"], gun)
    if "vefat" in bolumler:  # yalnızca daha önce paylaşılmamış vefatlar
        try:
            d["vefat"] = vefat.yeni_vefatlar()
        except Exception as hata:
            d["eksik"].append(f"vefat: {hata}")
    ad = f"{datetime.now(TZ):%Y-%m-%d}-{mod}"
    veri = KOK / "veri" / f"{ad}.json"
    veri.parent.mkdir(exist_ok=True)
    veri.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    eksik = "\n\n⚠️ Eksik: " + "; ".join(d["eksik"]) if d["eksik"] else ""
    try:
        aciklama = metin(d) + (f"\n\n🕊️ Vefat ve cenaze: {', '.join(k['ad'] for k in d['vefat'])}. Allah rahmet eylesin."
                               if d.get("vefat") else "") + eksik
    except KeyError:  # bölüm hiç toplanamadıysa
        aciklama = f"⚠️ {mod} paylaşımı hazırlanamadı.{eksik}"
    subprocess.run([sys.executable, str(KOK / "ciz.py"), str(veri)], check=True)
    if any((KOK / "cikti" / ad).glob("*.png")):
        subprocess.run([sys.executable, str(KOK / "gonder.py"), str(KOK / "cikti" / ad), aciklama], check=True)
        if d.get("vefat"):
            vefat.kaydet(d["vefat"])  # yalnızca gönderim başarılıysa: gönderilemeyen bir sonraki pakete kalır
    else:
        from haber_takip import telegram
        telegram(aciklama)


if __name__ == "__main__":
    main()
