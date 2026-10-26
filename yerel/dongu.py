#!/usr/bin/env python3
"""Düzce Abisi yerel sunucu döngüsü: bilgisayar açık kaldığı sürece her şeyi zamanında çalıştırır.

  her 5 dk   haber_takip.py, is_ilanlari.py, deprem.py, zamanli.py (burç, market, tarihte, özetler...), site_guncelle.py
  06:30      calistir.py gunaydin      09:30  calistir.py piyasa
  18:00      calistir.py eczane        21:00  calistir.py yarin
  saatte bir git pull (GitHub'daki düzeltmeler kendiliğinden gelir)

Her iş ayrı bir süreçte çalışır; biri çökerse döngü durmaz. Kayıt: kayit/dongu.log
Deneme:  python3 yerel/dongu.py --bir-tur      (bir tur çalışır ve çıkar; DENEME=1 ile Telegram'a göndermez)
"""
import json, os, subprocess, sys, time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

KOK = Path(__file__).resolve().parent.parent
TZ = ZoneInfo("Europe/Istanbul")
DURUM = KOK / "durum" / "yerel_gunluk.json"
KAYIT = KOK / "kayit" / "dongu.log"
PY = sys.executable
if PY.lower().endswith("pythonw.exe"):  # Windows'ta pencere açmadan çalışırken alt işler de penceresiz başlasın
    PY = PY[:-len("pythonw.exe")] + "python.exe"
os.environ.setdefault("PYTHONUTF8", "1")         # Windows: Türkçe karakterli dosyalar ve çıktılar UTF-8
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
PENCERESIZ = getattr(subprocess, "CREATE_NO_WINDOW", 0)
TARAMA_ARALIGI = 300  # saniye
TARAMA = ["haber_takip.py", "is_ilanlari.py", "deprem.py", "zamanli.py", "site_guncelle.py"]  # son: haber.duzceabisi.com
GUNLUK = [("gunaydin", 6, 30), ("piyasa", 9, 30), ("eczane", 18, 0), ("yarin", 21, 0)]


def yaz(*m):
    KAYIT.parent.mkdir(exist_ok=True)
    satir = f"{datetime.now(TZ):%Y-%m-%d %H:%M:%S} " + " ".join(map(str, m))
    if sys.stdout:  # pythonw (Windows, penceresiz) altında konsol yok
        print(satir, flush=True)
    with KAYIT.open("a", encoding="utf-8") as f:
        f.write(satir + "\n")
    if KAYIT.stat().st_size > 5_000_000:  # kayıt dosyası 5 MB'ı geçerse eskisini sakla, yenisine başla
        KAYIT.replace(KAYIT.with_suffix(".eski.log"))


def calistir(*arg, sure=1500):
    t = time.time()
    try:
        s = subprocess.run([PY, *arg], cwd=KOK, capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=sure, creationflags=PENCERESIZ)
        ozet = [l for l in (s.stdout + s.stderr).splitlines() if l.strip() and "403" not in l][-6:]
        yaz(f"{' '.join(arg)} -> kod {s.returncode} ({time.time() - t:.0f} sn)", "|", " / ".join(ozet)[:600])
    except subprocess.TimeoutExpired:
        yaz(f"{' '.join(arg)} -> ZAMAN AŞIMI ({sure} sn)")


def gunluk_isler(simdi):
    durum = json.loads(DURUM.read_text(encoding="utf-8")) if DURUM.exists() else {}
    bugun = simdi.strftime("%Y-%m-%d")
    for mod, saat, dakika in GUNLUK:
        zaman = simdi.replace(hour=saat, minute=dakika, second=0, microsecond=0)
        if durum.get(mod) != bugun and zaman <= simdi < zaman.replace(hour=min(saat + 3, 23)):
            calistir("calistir.py", mod)
            durum[mod] = bugun
            DURUM.parent.mkdir(exist_ok=True)
            DURUM.write_text(json.dumps(durum), encoding="utf-8")


def guncelle(son):
    if time.time() - son < 3600 or not (KOK / ".git").exists():
        return son
    s = subprocess.run(["git", "pull", "--ff-only", "-q"], cwd=KOK, capture_output=True, text=True, creationflags=PENCERESIZ)
    yaz("git pull ->", s.returncode, (s.stdout + s.stderr).strip()[:200])
    return time.time()


def main():
    bir_tur = "--bir-tur" in sys.argv
    yaz("=== Düzce Abisi yerel sunucu başladı", "(DENEME)" if os.environ.get("DENEME") == "1" else "")
    son_guncelleme = 0.0
    while True:
        bas = time.time()
        try:  # beklenmedik bir hata (ağ, disk) döngüyü durdurmasın
            if not bir_tur:
                son_guncelleme = guncelle(son_guncelleme)
            simdi = datetime.now(TZ)
            gunluk_isler(simdi)
            for betik in TARAMA:
                calistir(betik)
        except Exception as hata:
            yaz("döngü hatası:", repr(hata)[:300])
        if bir_tur:
            break
        time.sleep(max(30, TARAMA_ARALIGI - (time.time() - bas)))


if __name__ == "__main__":
    main()
