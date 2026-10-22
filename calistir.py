#!/usr/bin/env python3
"""Düzce Abisi sabah paketini baştan sona üretir ve Telegram'a gönderir.

Kullanım:  python3 calistir.py
Adımlar:   topla.py (veri) -> manşet -> ciz.py (görseller) -> gonder.py (Telegram)

Sunucuda (GitHub Actions) her sabah bu dosya çalışır. Claude'un araştırdığı
bölümler (kesinti, etkinlik, tarihte bugün, önemli gün) varsa veri dosyasında
korunur; yoksa paket yalnızca kesin verilerle gider.
"""
import json, subprocess, sys
from pathlib import Path

KOK = Path(__file__).resolve().parent


def otomatik_manset(d):
    m = []
    if d.get("hava"):
        h = d["hava"]
        m.append(f"Hava {h['en_dusuk']}–{h['en_yuksek']}°C, {h['yagmur'].lower()}")
    altin = dict((a, s) for a, _, s in d.get("altin", []))
    if "Gram" in altin:
        m.append(f"Gram altın {altin['Gram'].split(',')[0]} TL")
    dolar = next((s for _, a, _, s in d.get("doviz", []) if a == "Dolar"), None)
    if dolar:
        m.append(f"Dolar {dolar[:5]} TL")
    yakit = dict(d.get("akaryakit", {}).get("liste", []))
    if "Benzin" in yakit:
        m.append(f"Benzin {yakit['Benzin']} TL, motorin {yakit.get('Motorin', '-')} TL")
    if d.get("eczaneler", {}).get("liste"):
        m.append(f"Bu gece nöbetçi {len(d['eczaneler']['liste'])} eczane")
    return m[:5]


def main():
    veri = Path(subprocess.run([sys.executable, str(KOK / "topla.py")], check=True,
                               capture_output=True, text=True).stdout.strip())
    d = json.loads(veri.read_text(encoding="utf-8"))
    if not d.get("manset"):
        d["manset"] = otomatik_manset(d)
        veri.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    subprocess.run([sys.executable, str(KOK / "ciz.py"), str(veri)], check=True)

    aciklama = (f"📲 Düzce Abisi — {d['tarih']} {d['gun']} sabah paketi\n\n"
                f"Düzce'de bugün: hava durumu, döviz ve altın, akaryakıt fiyatları ve nöbetçi eczaneler 👇\n\n"
                f"#düzce #düzcehaber #düzceabisi #havadurumu #altın #nöbetçieczane")
    if d.get("eksik"):
        aciklama += "\n\n⚠️ Eksik: " + "; ".join(d["eksik"])
    subprocess.run([sys.executable, str(KOK / "gonder.py"), str(KOK / "cikti" / veri.stem), aciklama], check=True)


if __name__ == "__main__":
    main()
