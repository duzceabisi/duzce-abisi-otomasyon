#!/usr/bin/env python3
"""Tek bir haber için Düzce Abisi tasarımlı Instagram kartı (1080x1350) üretir.

Kullanım:  python3 haber_kart.py kart.json [cikti.png]
kart.json: {"kategori": "yangin|kaza|asayis|duyuru|hava|genel", "baslik": "...",
            "ozet": "...", "yer": "Şıralık Mahallesi", "saat": "01.09", "kaynak": "Düzce Hür Haber"}

Haber sitelerinin fotoğrafları kullanılmaz (telif); kart, kategori rengi ve simgesiyle tasarlanır.
"""
import html, json, subprocess, sys, tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from ciz import CHROME, H, W

KOK = Path(__file__).resolve().parent
TZ = ZoneInfo("Europe/Istanbul")
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]

# kategori -> (etiket, simge, ana renk, koyu renk)
KATEGORI = {
    "yangin": ("YANGIN", "🔥", "#D7412B", "#7A1E12"),
    "kaza": ("KAZA", "🚨", "#E8762B", "#7A3A10"),
    "asayis": ("ASAYİŞ", "🚔", "#2B5BD7", "#142C6B"),
    "duyuru": ("DUYURU", "📢", "#0E3B2E", "#06201A"),
    "hava": ("HAVA UYARISI", "⛈️", "#3A6E8F", "#183447"),
    "genel": ("SON DAKİKA", "📰", "#0E3B2E", "#06201A"),
    "deprem": ("DEPREM", "🌍", "#8A3FD1", "#3B1460"),
    "okul": ("OKUL TATİLİ", "🏫", "#1F8A70", "#0B3B30"),
    "kayip": ("KAYIP", "🔎", "#C9A227", "#5A4708"),
    "kesinti": ("KESİNTİ", "⚡", "#E3B02D", "#5C4508"),
    "olum": ("ACI HABER", "🖤", "#4A4F4C", "#1C1F1D"),
}

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Inter:wght@500;600;700;800&display=swap');
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1350px;overflow:hidden}
body{font-family:Inter,sans-serif;background:var(--koyu);color:#F5EFE3;position:relative}
.zemin{position:absolute;inset:0;background:radial-gradient(circle at 85% 18%,var(--ana) 0,transparent 55%),
  repeating-linear-gradient(135deg,rgba(255,255,255,.035) 0 2px,transparent 2px 18px)}
.simge{position:absolute;right:-40px;top:120px;font-size:520px;opacity:.16;transform:rotate(-8deg)}
.ust{position:relative;height:120px;padding:0 64px;display:flex;align-items:center;justify-content:space-between}
.marka{font-family:'Archivo Black';font-size:40px}.marka span{color:#E39B2D}
.saat{font-weight:700;font-size:26px;background:rgba(255,255,255,.14);padding:12px 22px;border-radius:999px}
.ic{position:absolute;left:64px;right:64px;bottom:150px}
.etiket{display:inline-flex;gap:14px;align-items:center;background:var(--ana);color:#fff;font-weight:800;
  font-size:30px;letter-spacing:4px;padding:14px 26px;border-radius:14px;margin-bottom:34px}
h1{font-family:'Archivo Black';font-size:var(--boy);line-height:1.04;margin-bottom:34px}
p{font-size:36px;line-height:1.4;font-weight:500;color:rgba(245,239,227,.88)}
.yer{margin-top:30px;font-size:30px;font-weight:700;color:#E39B2D}
.alt{position:absolute;left:64px;right:64px;bottom:48px;display:flex;justify-content:space-between;
  font-size:24px;color:rgba(245,239,227,.65);font-weight:600;border-top:2px solid rgba(245,239,227,.15);padding-top:24px}
"""


def kart_html(k):
    etiket, simge, ana, koyu = KATEGORI.get(k.get("kategori"), KATEGORI["genel"])
    boy = 92 if len(k["baslik"]) < 45 else (80 if len(k["baslik"]) < 70 else 66)
    simdi = datetime.now(TZ)
    e = html.escape
    yer = f'<div class="yer">📍 {e(k["yer"])}</div>' if k.get("yer") else ""
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><style>{CSS}</style></head>
<body style="--ana:{ana};--koyu:{koyu};--boy:{boy}px"><div class="zemin"></div><div class="simge">{simge}</div>
<div class="ust"><div class="marka">DÜZCE <span>ABİSİ</span></div><div class="saat">{simdi.day} {AYLAR[simdi.month - 1]} · {e(k.get("saat", simdi.strftime("%H.%M")))}</div></div>
<div class="ic"><div class="etiket">{simge} {etiket}</div><h1>{e(k["baslik"])}</h1><p>{e(k.get("ozet", ""))}</p>{yer}</div>
<div class="alt"><span>Kaynak: {e(k.get("kaynak", ""))}</span><span>Haberler için takip et → @duzceabisi</span></div></body></html>"""


def ciz_kart(k, png):
    png = Path(png)
    png.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        h = Path(tmp) / "kart.html"
        h.write_text(kart_html(k), encoding="utf-8")
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={W},{H}",
                        "--virtual-time-budget=4000", f"--screenshot={png}", h.as_uri()], check=True, capture_output=True)
    return png


if __name__ == "__main__":
    k = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    print(ciz_kart(k, sys.argv[2] if len(sys.argv) > 2 else KOK / "cikti" / "kartlar" / f"{Path(sys.argv[1]).stem}.png"))
