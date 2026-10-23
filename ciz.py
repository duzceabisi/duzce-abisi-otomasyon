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
W, H = 1080, 1920  # Instagram hikâyesi; üst ve alt ~250 px Instagram'ın düğmelerine bırakılır

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
.liste{list-style:none}
.liste li{display:flex;gap:26px;padding:20px 0;border-top:2px solid #E6DECF;align-items:baseline}
.liste b{font-family:'Archivo Black';font-size:32px;color:var(--findik);min-width:170px;flex-shrink:0}
.liste span{font-size:30px;line-height:1.32;font-weight:500}
.burcsayfa .liste li{padding:22px 0;flex-direction:column;gap:8px}.burcsayfa .liste b{font-size:40px}.burcsayfa .liste span{font-size:30px;line-height:1.4}
.buyuk .liste li{padding:26px 0}.buyuk .liste b{font-size:48px;min-width:300px}.buyuk .liste span{font-family:'Archivo Black';font-size:56px;color:var(--yesil)}
.koyu{background:var(--yesil);color:var(--krem)}.koyu h1,.koyu .etiket{color:var(--krem)}.koyu .liste li{border-color:rgba(245,239,227,.18)}
.koyu .alt{color:rgba(245,239,227,.7)}
.vefatsayfa{background:#ECE9E4}
.vefatsayfa .ust{background:#2A2F2C}
.vefat .kart{margin-bottom:18px;padding:26px 34px;border-left:8px solid #2A2F2C}
.vefat h3{font-family:'Archivo Black';font-size:38px;color:#2A2F2C}
.vefat p{font-size:25px;margin-top:8px;color:#3B423E;line-height:1.35}
.vefat .vab{color:var(--gri);font-size:23px;margin-top:4px}
.ecz .tel{font-family:'Archivo Black';font-size:32px;color:var(--kirmizi);white-space:nowrap}
"""


# Hikâye teması: koyu, arka planda karartılmış temsili görsel, açık renk yazı
HIKAYE = """
html,body{width:1080px;height:1920px}
body,body.kapak,body.gun,body.vefatsayfa{background:#0B1310;color:#F5EFE3}
.bg{position:absolute;inset:0;background-size:cover;background-position:center}
.ort{position:absolute;inset:0;background:linear-gradient(180deg,rgba(6,14,11,.80) 0%,rgba(6,14,11,.58) 22%,rgba(6,14,11,.72) 50%,rgba(6,14,11,.82) 78%,rgba(6,14,11,.94) 100%)}
.bg:not([style]){background:radial-gradient(ellipse at 85% 8%,rgba(227,155,45,.26) 0,transparent 50%),
  radial-gradient(ellipse at 5% 95%,rgba(31,122,77,.45) 0,transparent 60%),
  repeating-linear-gradient(135deg,rgba(255,255,255,.025) 0 2px,transparent 2px 26px),#0B1310}
.yildiz .bg{background:radial-gradient(circle at 20% 15%,rgba(255,255,255,.9) 0 2px,transparent 3px),radial-gradient(circle at 70% 8%,rgba(255,255,255,.7) 0 2px,transparent 3px),
  radial-gradient(circle at 85% 30%,rgba(255,255,255,.8) 0 1.5px,transparent 2.5px),radial-gradient(circle at 40% 40%,rgba(255,255,255,.6) 0 1.5px,transparent 2.5px),
  radial-gradient(ellipse at 50% 0%,#3B2470 0%,#14102E 55%,#070611 100%)}
.ust,.kapak .ust,.vefatsayfa .ust{position:relative;z-index:2;height:auto;padding:150px 64px 0;background:transparent}
.tarih{background:rgba(255,255,255,.14)}
.ic{position:absolute;z-index:2;left:0;right:0;top:300px;bottom:300px;padding:0 64px;display:flex;flex-direction:column;justify-content:center}
.ic>.etiket,.ic>.ikon{align-self:flex-start}
.etiket{color:#E39B2D;border-bottom-color:#E39B2D;font-size:28px}
h1,.kapak h1,.uyari h1,.gun blockquote{color:#fff}
h1{font-size:88px}
.kart{background:rgba(255,255,255,.09);border:1.5px solid rgba(255,255,255,.14);backdrop-filter:blur(6px)}
.not,.kapak .alt{color:rgba(245,239,227,.72)}
.alt{position:absolute;z-index:2;bottom:180px;color:rgba(245,239,227,.6);font-size:24px}
.derece .buyuk{color:#fff;font-size:340px}.derece .kucuk{color:rgba(245,239,227,.85);font-size:44px}
.saatlik div{background:rgba(255,255,255,.09);padding:40px 0}.saatlik .s{color:rgba(245,239,227,.7);font-size:30px}
.saatlik .i{font-size:64px}.saatlik .d{color:#fff;font-size:52px}
.rozet{background:#E39B2D;color:#1B130A;font-size:32px;padding:20px 32px}.rozet.acik{background:rgba(255,255,255,.12);color:#fff}
th{color:rgba(255,255,255,.55)}td{color:#F5EFE3;border-top-color:rgba(255,255,255,.12);font-size:40px;padding:18px 0}
td:first-child,.bolum{color:#fff}td.satis{color:#E39B2D}
.yakit .ad{color:#fff}.yakit .f{color:#E39B2D}.yakit .f small{color:rgba(255,255,255,.6)}.yakit .kart{padding:60px 48px}
.ilce h3{color:#fff}.ilce p{color:#F5EFE3;font-size:28px}
.zaman li,.liste li,.manset li{border-top-color:rgba(255,255,255,.14)}.zaman span,.liste span{color:#F5EFE3}
.zaman li{padding:22px 0}.zaman span{font-size:33px}.zaman b{font-size:44px}.liste li{padding:28px 0}.liste span{font-size:36px}.liste b{font-size:36px}
.ecz .kart{padding:40px 40px;margin-bottom:26px}.ecz h3{color:#fff;font-size:42px}.ecz p{color:rgba(255,255,255,.7);font-size:28px}.ecz .tel{color:#E39B2D;font-size:36px}
.ilc td{font-size:32px;padding:18px 0}.ilc .ead{color:#fff}.ilc .ead small{color:rgba(255,255,255,.65);font-size:23px}.ilc .etel{color:#E39B2D;font-size:30px}
.vefat .kart{border-left:8px solid rgba(255,255,255,.55);padding:34px 38px;margin-bottom:24px}.vefat h3{color:#fff;font-size:46px}
.vefat p{color:#F5EFE3;font-size:30px}.vefat .vab{color:rgba(255,255,255,.65);font-size:27px}
.burcsayfa .liste li{padding:34px 0}.burcsayfa .liste b{font-size:46px}.burcsayfa .liste span{font-size:34px;line-height:1.42}
.buyuk .liste li{padding:36px 0}.buyuk .liste b{font-size:60px}.buyuk .liste span{color:#fff;font-size:72px}
.manset li{font-size:52px;padding:40px 0}
"""

# sayfa adı -> arka plan kategorisi (arkaplan/<kategori>-<n>.jpg); "yildiz" = çizimle yıldızlı gökyüzü
ARKA = {"hava": "genel", "piyasa": "genel", "akaryakit": "genel", "eczane": "genel", "namaz": "genel", "kesinti": "kesinti",
        "vefat": "olum", "burc": "yildiz", "tarih": "genel", "ozel": "genel", "ozet": "genel", "is": "genel",
        "etkinlik": "firsat", "bim": "firsat", "kapak": "genel", "gun": "genel"}


def arka_plan(ad, d):
    anahtar = next((v for k, v in ARKA.items() if ad.startswith(k)), "genel")
    if ad.startswith("hava") and d.get("hava", {}).get("yagis_ihtimali", 0) >= 50:
        anahtar = "hava"
    if anahtar == "yildiz":
        return None, "yildiz"
    tek = KOK / "arkaplan" / f"{anahtar}.jpg"
    adaylar = [tek] if tek.exists() else sorted((KOK / "arkaplan").glob(f"{anahtar}-*.jpg"))
    if not adaylar:
        return None, ""
    secim = adaylar[sum(map(ord, ad + d.get("tarih", ""))) % len(adaylar)]
    return secim, ""


def e(s):
    return html.escape(str(s))


def sayfa(govde, d, no, top, kaynak="", sinif="", ad=""):
    sol = "Düzce Abisi · @duzceabisi"  # kaynak görselde yazmaz, Telegram metninde yazılır
    foto, ek = arka_plan(ad, d)
    bg = f'<div class="bg" style="background-image:url({foto.as_uri()})"></div>' if foto else '<div class="bg"></div>'
    return f"""<!doctype html><html lang="tr"><head><meta charset="utf-8"><style>{CSS}{HIKAYE}</style></head>
<body class="{sinif} {ek}">{bg}<div class="ort"></div><div class="ust"><div class="marka">DÜZCE <span>ABİSİ</span></div><div class="tarih">{e(d['tarih'])} · {e(d['gun'])}</div></div>
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
    for sf in d.get("sayfalar") or []:
        satir = "".join(f'<li><b>{e(b)}</b><span>{e(m)}</span></li>' for b, m in sf["satirlar"])
        alt = f'<p class="not" style="margin:-10px 0 26px;font-size:30px">{e(sf["alt"])}</p>' if sf.get("alt") else ""
        out.append((sf["ad"], f"""<div class="ic genel"><div class="etiket">{e(sf["etiket"])}</div>
<h1 style="font-size:{sf.get("boy", 64)}px">{e(sf["baslik"])}</h1>{alt}<ul class="liste">{satir}</ul></div>""", "", sf.get("sinif", "")))
    vefat = d.get("vefat") or []
    for bas in range(0, len(vefat), 4):
        kartlar = "".join(
            f'<div class="kart vkart"><h3>{e(k["ad"])}</h3><p class="vab">{e(k.get("anne_baba", ""))}</p>'
            f'<p>🕌 <b>Cenaze namazı:</b> {e(k.get("namaz") or "-")}</p>'
            f'<p>🪦 <b>Defin:</b> {e(k.get("defin") or "-")}{" · " + e(k["defin_tarihi"]) if k.get("defin_tarihi") else ""}</p></div>'
            for k in vefat[bas:bas + 4])
        out.append((f"vefat-{bas // 4 + 1}", f"""<div class="ic vefat"><div class="etiket">Vefat ve cenaze</div>
<h1 style="font-size:58px">Aramızdan ayrılanlar</h1>{kartlar}
<p class="not" style="font-size:26px">Allah rahmet eylesin; ailelerine ve sevenlerine başsağlığı dileriz.</p></div>""", "Düzce Hür Haber", "vefatsayfa"))
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
            h.write_text(sayfa(govde, d, i, len(sf), kaynak, sinif, ad), encoding="utf-8")
            png = hedef / f"{i:02d}-{ad}.png"
            subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                            f"--window-size={W},{H}", "--virtual-time-budget=4000",
                            f"--screenshot={png}", h.as_uri()],
                           check=True, capture_output=True)
            print(png.relative_to(KOK))


if __name__ == "__main__":
    main()
