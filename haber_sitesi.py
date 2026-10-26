#!/usr/bin/env python3
"""haber.duzceabisi.com'a veri gönderir.

  haber(...)              bir haberi siteye ekler (aynı bağlantı iki kez eklenmez)
  blok(ad, veri)          eczane, hava, piyasa, namaz gibi günlük bir kutuyu günceller
  liste(tur, kayitlar)    vefat, deprem, iş ilanı listelerine kayıt ekler

Ayarlar: SITE_URL (ör. https://haber.duzceabisi.com) ve SITE_ANAHTAR (.env ya da ortam).
İkisinden biri yoksa hiçbir şey göndermez. Site çökse ya da yanıt vermese bile hata
fırlatmaz: Telegram gönderimi siteden bağımsız devam eder.
"""
import base64, json, os, sys, urllib.request
from pathlib import Path

from gonder import deneme_modu

KOK = Path(__file__).resolve().parent


def _ayar(ad):
    if os.environ.get(ad):
        return os.environ[ad]
    env = KOK / ".env"
    if env.exists():
        for satir in env.read_text(encoding="utf-8-sig").splitlines():
            if satir.startswith(ad + "="):
                return satir.split("=", 1)[1].strip()
    return ""


def acik():
    return bool(_ayar("SITE_URL") and _ayar("SITE_ANAHTAR"))


def _gonder(yol, veri):
    url, anahtar = _ayar("SITE_URL").rstrip("/"), _ayar("SITE_ANAHTAR")
    if not (url and anahtar):
        return None
    if deneme_modu() and not os.environ.get("SITE_DENEME"):  # DENEME=1: siteye de yazma (SITE_DENEME=1 ile yazar)
        print(f"[DENEME] site {yol}: {json.dumps(veri, ensure_ascii=False)[:200]}")
        return None
    istek = urllib.request.Request(url + yol, data=json.dumps(veri, ensure_ascii=False).encode(),
                                   headers={"Content-Type": "application/json", "Authorization": f"Bearer {anahtar}",
                                            "User-Agent": "DuzceAbisiBot/1.0"})
    try:
        with urllib.request.urlopen(istek, timeout=20) as r:
            return json.load(r)
    except Exception as hata:  # site hatası botu durdurmaz
        print(f"site {yol} gönderilemedi: {hata}", file=sys.stderr)
        return None


def haber(baslik, kategori, zaman, kaynaklar, ozet="", metin="", onemli=False, yer="", kaynak_baslik="", foto=None):
    """zaman: datetime (saat dilimli). kaynaklar: [{"site", "link"}]. foto: varsa yerel PNG/JPG yolu."""
    veri = {"baslik": baslik, "kategori": kategori, "zaman": zaman.isoformat(), "kaynaklar": kaynaklar,
            "ozet": ozet, "metin": metin, "onemli": bool(onemli), "yer": yer, "kaynak_baslik": kaynak_baslik}
    if foto and Path(foto).exists():
        veri["foto"] = base64.b64encode(Path(foto).read_bytes()).decode()
    r = _gonder("/api/haber", veri)
    if r and r.get("yeni"):
        print("sitede yayımlandı:", r.get("url"))
    return r


def blok(ad, veri):
    return _gonder(f"/api/blok/{ad}", {"veri": veri})


def liste(tur, kayitlar):
    """kayitlar: [{"anahtar", "zaman" (ISO), "veri": {...}}]"""
    return _gonder(f"/api/liste/{tur}", {"kayitlar": kayitlar}) if kayitlar else None
