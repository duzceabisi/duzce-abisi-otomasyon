#!/usr/bin/env python3
"""Düzce Abisi sabah paketi: veri JSON'undan 1080x1350 Instagram görselleri üretir.

Kullanım:  python3 ciz.py veri/2026-10-22-sabah.json
Çıktı:     cikti/2026-10-22-sabah/01-kapak.png ...
"""
import glob, html, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

KOK = Path(__file__).resolve().parent
CHROME = (os.environ.get("CHROME")
          or next((p for p in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"] if os.path.exists(p)), None)
          or shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chromium-browser")
          or next(iter(sorted(glob.glob(os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome")))), None))
W, H = 1080, 1350

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Inter:wght@400;500;600;700;800&display=swap');
:root{--yesil:#0E3B2E;--krem:#F5EFE3;--findik:#E39B2D;--kirmizi:#D7412B;--murekkep:#14211C;--gri:#5E6B64;}
*{box-sizing:border-box;margin:0;padding:0}
html,body{width:1080px;height:1350px;overflow:hidden}
body{font-family:Inter,system-ui,sans-serif;color:var(--murekkep);background:var(--krem);position:relative}
.ust{height:120px;padding:0 64px;display:flex;align-items:center;justify-content:space-between;background:var(--yesil);color:var(--krem)}
.marka{font-family:'Archivo Black';font-size:40px;letter-spacing:1px}
.marka span{color:var(--findik)}
.tarih{font-weight:700;font-size:26px;background:rgba(255,255,255,.12);padding:12px 22px;border-radius:999px}
.ic{padding:56px 64px 0}
.etiket{display:inline-block;font-weight:800;font-size:24px;letter-spacing:3px;text-transform:uppercase;color:var(--yesil);border-bottom:6px solid var(--findik);padding-bottom:6px;margin-bottom:28px}
h1{font-family:'Archivo Black';font-size:76px;line-height:1.02;color:var(--yesil);margin-bottom:28px}
.alt{position:absolute;left:64px;right:64px;bottom:40px;display:flex;justify-content:space-between;font-size:22px;color:var(--gri);font-weight:500}
.kart{background:#fff;border-radius:28px;padding:30px 36px}
.not{font-size:30px;line-height:1.4;color:var(--gri);margin-top:26px}
.kapak{background:var(--yesil);color:var(--krem)}
.kapak .ust{background:transparent}
.kapak h1{color:var(--krem);font-size:150px;margin-top:50px}
.kapak h1 em{font-style:normal;color:var(--findik)}
.manset{list-style:none;margin-top:44px}
.manset li{font-size:44px;font-weight:600;padding:30px 0;border-top:2px solid rgba(245,239,227,.18);display:flex;gap:22px}
.manset li b{font-family:'Archivo Black';color:var(--findik);min-width:40px}
.kapak .alt{color:rgba(245,239,227,.7)}
.derece{display:flex;align-items:flex-end;gap:36px;margin:0 0 24px}
.derece .buyuk{font-family:'Archivo Black';font-size:280px;line-height:.85;color:var(--yesil)}
.derece .kucuk{font-size:40px;font-weight:700;color:var(--gri);padding-bottom:18px;line-height:1.5}
.saatlik{display:grid;grid-template-columns:repeat(5,1fr);gap:14px}
.saatlik div{background:#fff;border-radius:24px;text-align:center;padding:26px 0}
.saatlik .s{font-size:28px;color:var(--gri);font-weight:600}
.saatlik .i{font-size:56px;margin:14px 0}
.saatlik .d{font-family:'Archivo Black';font-size:48px;color:var(--yesil)}
.rozetler{display:flex;gap:16px;margin-top:26px;flex-wrap:wrap}
.rozet{background:var(--yesil);color:var(--krem);border-radius:999px;padding:18px 30px;font-size:30px;font-weight:700}
.rozet.acik{background:#fff;color:var(--yesil)}
table{width:100%;border-collapse:collapse}
th{font-size:22px;letter-spacing:2px;text-transform:uppercase;color:var(--gri);text-align:right;padding:0 0 12px;font-weight:700}
th:first-child{text-align:left}
td{font-size:34px;padding:11px 0;border-top:2px solid #EEE7DA;text-align:right;font-variant-numeric:tabular-nums;font-weight:600}
td:first-child{text-align:left;font-weight:800;color:var(--yesil)}
td.satis{font-family:'Archivo Black';color:var(--yesil)}
.bolum{font-family:'Archivo Black';font-size:34px;color:var(--yesil);margin:6px 0 10px}
.uyari h1{color:var(--kirmizi)}
.ilce{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.ilce .kart{padding:28px 30px}
.ilce h3{font-family:'Archivo Black';font-size:34px;color:var(--yesil);margin-bottom:10px}
.ilce p{font-size:26px;line-height:1.35;margin-top:14px}
.ilce p b{display:table;background:var(--kirmizi);color:#fff;border-radius:10px;padding:4px 12px;font-size:25px;margin-bottom:6px}
.zaman{list-style:none}
.zaman li{display:flex;gap:28px;padding:28px 0;border-top:2px solid #E6DECF;align-items:baseline}
.zaman b{font-family:'Archivo Black';font-size:44px;color:var(--findik);min-width:130px}
.zaman span{font-size:35px;line-height:1.3;font-weight:500}
.gun{background:#DDEFE3}
.gun .ikon{font-size:150px;margin:0 0 10px}
.gun blockquote{font-family:'Archivo Black';font-size:52px;line-height:1.12;color:var(--yesil);margin:10px 0 24px}
.gun p{font-size:33px;line-height:1.45}
.etk{margin-top:32px;background:var(--yesil);color:var(--krem);border-radius:28px;padding:28px 36px}
.etk .k{font-size:22px;letter-spacing:3px;font-weight:800;color:var(--findik)}
.etk .a{font-family:'Archivo Black';font-size:38px;margin:8px 0}
.etk .d{font-size:26px;opacity:.9}
.ecz .kart{margin-bottom:22px;padding:34px 36px;display:flex;justify-content:space-between;align-items:center;gap:20px}
.ecz h3{font-family:'Archivo Black';font-size:38px;color:var(--yesil)}
.ecz p{font-size:25px;color:var(--gri);margin-top:6px}
.yakit{display:grid;gap:22px;margin-top:10px}
.yakit .kart{display:flex;justify-content:space-between;align-items:center;padding:44px 48px}
.yakit .ad{font-family:'Archivo Black';font-size:56px;color:var(--yesil)}
.yakit .f{font-family:'Archivo Black';font-size:96px;color:var(--kirmizi)}
.yakit .f small{font-size:40px;color:var(--gri)}
.ilc td{font-size:27px;padding:12px 0;vertical-align:top}
.ilc td:first-child{width:200px}
.ilc .ead{text-align:left;font-weight:800;color:var(--murekkep)}
.ilc .ead small{display:block;font-size:19px;font-weight:500;color:var(--gri);margin-top:2px}
.ilc .etel{font-family:'Archivo Black';color:var(--kirmizi);white-space:nowrap;font-size:26px}
.ecz .tel{font-family:'Archivo Black';font-size:32px;color:var(--kirmizi);white-space:nowrap}
"""


def e(s):
    return html.escape(str(s))


def sayfa(govde, d, no, top, kaynak="", sinif=""):
    sol = e("Kaynak: " + kaynak) if kaynak else "Düzce Abisi"
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><style>{CSS}</style></head>
<body class="{sinif}"><div class="ust"><div class="marka">DÜZCE <span>ABİSİ</span></div><div class="tarih">{e(d['tarih'])} · {e(d['gun'])}</div></div>
{govde}<div class="alt"><span>{sol}</span><span>{no} / {top}</span></div></body></html>"""


def sayfalar(d):
    out = []
    if d.get("manset"):
        lis = "".join(f"<li><b>{i}</b>{e(m)}</li>" for i, m in enumerate(d["manset"], 1))
        out.append(("kapak", f'<div class="ic"><h1>DÜZCE\'DE<br><em>BUGÜN</em></h1><ul class="manset">{lis}</ul></div>', "", "kapak"))

    if d.get("hava"):
     h = d["hava"]
     saat = "".join(f'<div><div class="s">{e(s)}</div><div class="i">{i}</div><div class="d">{t}°</div></div>' for s, t, i in h["saatlik"])
     out.append(("hava", f"""<div class="ic"><div class="etiket">{e(h.get('baslik', 'Hava durumu'))}</div>
<div class="derece"><div class="buyuk">{h['en_yuksek']}°</div><div class="kucuk">{h['ikon']} {e(h['durum'])}<br>En düşük {h['en_dusuk']}°C</div></div>
<div class="saatlik">{saat}</div>
<div class="rozetler"><div class="rozet">☂️ Şemsiye: {e(h['semsiye'])}</div><div class="rozet acik">🌧️ {e(h['yagmur'])}</div><div class="rozet acik">💨 {e(h['ruzgar'])}</div></div>
<p class="not">{e(h['not'])}</p></div>""", h["kaynak"], ""))

    if d.get("doviz"):
     dv = "".join(f"<tr><td>{f} {e(a)}</td><td>{e(al)}</td><td class='satis'>{e(st)}</td></tr>" for f, a, al, st in d["doviz"])
     al = "".join(f"<tr><td>🟡 {e(a)}</td><td>{e(x)}</td><td class='satis'>{e(y)}</td></tr>" for a, x, y in d["altin"])
     out.append(("piyasa", f"""<div class="ic"><div class="etiket">Döviz & altın · {e(d['piyasa_saat'])}</div>
<div class="kart"><div class="bolum">💵 Döviz</div><table><tr><th></th><th>Alış</th><th>Satış</th></tr>{dv}</table></div>
<div class="kart" style="margin-top:20px"><div class="bolum">🥇 Altın</div><table><tr><th></th><th>Alış</th><th>Satış</th></tr>{al}</table></div>
<p class="not" style="font-size:22px;margin-top:16px">Fiyatlar anlık değişebilir; kuyumcu fiyatları farklı olabilir.</p></div>""", d["piyasa_kaynak"], ""))

    if d.get("akaryakit"):
     y = d["akaryakit"]
     kartlar = "".join(f'<div class="kart"><div class="ad">⛽ {e(a)}</div><div class="f">{e(f)}<small> TL</small></div></div>' for a, f in y["liste"])
     out.append(("akaryakit", f'<div class="ic"><div class="etiket">Akaryakıt · Düzce {e(y["ilce"])}</div><h1>Bugünkü pompa fiyatları</h1><div class="yakit">{kartlar}</div><p class="not">Litre fiyatıdır; istasyona göre küçük farklar olabilir.</p></div>', y["kaynak"], ""))
    if d.get("kesinti"):
     k = d["kesinti"]
     kart = "".join(f'<div class="kart"><h3>📍 {e(ad)}</h3>' + "".join(f"<p><b>{e(s)}</b>{e(y)}</p>" for s, y in sat) + "</div>" for ad, sat in k["ilceler"])
     out.append(("kesinti", f"""<div class="ic"><div class="etiket">⚡ Elektrik kesintisi</div><h1 style="font-size:68px">{e(k['baslik'])}</h1>
<div class="ilce">{kart}</div><p class="not" style="font-size:27px">{e(k['not'])}</p></div>""", k["kaynak"], "uyari"))

    if d.get("onemli_gun"):
     g, et = d["onemli_gun"], d.get("etkinlik")
     etk = f'<div class="etk"><div class="k">🎭 BU AKŞAM DÜZCE\'DE</div><div class="a">{e(et["ad"])}</div><div class="d">🕗 {e(et["saat"])} · 📍 {e(et["yer"])} · 🎟️ {e(et["fiyat"])}</div></div>' if et else ""
     out.append(("gun", f"""<div class="ic"><div class="etiket">Bugünün önemli günü</div><div class="ikon">{g['ikon']}</div>
<h1 style="font-size:56px">{e(g['ad'])}</h1><blockquote>“{e(g['mesaj'])}”</blockquote><p>{e(g['aciklama'])}</p>
{etk}</div>""", "", "gun"))

    if d.get("tarihte_bugun"):
     z = "".join(f"<li><b>{e(y)}</b><span>{e(t)}</span></li>" for y, t in d["tarihte_bugun"])
     out.append(("tarih", f'<div class="ic"><div class="etiket">📜 Tarihte bugün</div><h1>{e(d["tarih"].rsplit(" ", 1)[0])}</h1><ul class="zaman">{z}</ul></div>', "", ""))

    if d.get("eczaneler", {}).get("liste"):
     ec = d["eczaneler"]
     ek = "".join(f'<div class="kart"><div><h3>💊 {e(a)}</h3><p>{e(adr)}</p></div><div class="tel">{e(t)}</div></div>' for a, adr, t in ec["liste"])
     out.append(("eczane", f"""<div class="ic ecz"><div class="etiket">Nöbetçi eczaneler · {e(ec['bolge'])}</div>
<h1>Bu gece nöbetçi</h1><p class="not" style="margin:-10px 0 30px;font-size:30px">🌙 {e(ec['donem'])}</p>{ek}<p class="not" style="font-size:24px">Gitmeden önce telefonla açık olduklarını teyit edin.</p></div>""", ec.get("kaynak", "eczaneler.gen.tr"), ""))
    if d.get("eczaneler", {}).get("ilceler"):
     ec = d["eczaneler"]
     sat = "".join(f'<tr><td>{e(il)}</td><td class="ead">{e(a)}<small>{e(adr)}</small></td><td class="etel">{e(t)}</td></tr>' for il, a, adr, t in ec["ilceler"])
     out.append(("eczane-ilceler", f"""<div class="ic ilc"><div class="etiket">Nöbetçi eczaneler · İlçeler</div>
<h1 style="font-size:60px">Bu gece ilçelerde</h1><p class="not" style="margin:-10px 0 24px;font-size:28px">🌙 {e(ec['donem'])}</p>
<div class="kart"><table>{sat}</table></div></div>""", ec.get("kaynak", ""), ""))
    return out


def main():
    veri = Path(sys.argv[1]).resolve()
    d = json.loads(veri.read_text(encoding="utf-8"))
    hedef = KOK / "cikti" / veri.stem
    hedef.mkdir(parents=True, exist_ok=True)
    sf = sayfalar(d)
    with tempfile.TemporaryDirectory() as tmp:
        for i, (ad, govde, kaynak, sinif) in enumerate(sf, 1):
            h = Path(tmp) / f"{i:02d}.html"
            h.write_text(sayfa(govde, d, i, len(sf), kaynak, sinif), encoding="utf-8")
            png = hedef / f"{i:02d}-{ad}.png"
            subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            f"--window-size={W},{H}", "--virtual-time-budget=4000",
                            f"--screenshot={png}", h.as_uri()],
                           check=True, capture_output=True)
            print(png.relative_to(KOK))


if __name__ == "__main__":
    main()
