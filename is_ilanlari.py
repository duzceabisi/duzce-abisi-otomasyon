#!/usr/bin/env python3
"""Düzce iş ilanlarını (İŞKUR, Eleman.net) tarar, yeni ilanları Telegram'a gönderir.

Kullanım:  python3 is_ilanlari.py
Sunucuda haber takibiyle birlikte 10 dakikada bir çalışır.

- Her ilan numarasıyla tutulur; aynı ilan iki kez gönderilmez. Haberlerdeki
  benzerlik kontrolü burada yok: aynı başlıklı iki ilan farklı işyerleri olabilir.
- Bir taramada çıkan yeni ilanlar tek mesajda liste olarak gider.
- Bir kaynağın ilk taramasında mevcut ilanlar yalnızca kaydedilir.
"""
import html, json, re, sys, urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from haber_takip import UA, gunluk_kaydet, telegram

KOK = Path(__file__).resolve().parent
DURUM = KOK / "durum" / "is_ilanlari.json"
TZ = ZoneInfo("Europe/Istanbul")
SAKLA = timedelta(days=60)  # ilanlar haftalarca yayında kalır; hafıza uzun olmalı
ISKUR = "https://esube.iskur.gov.tr/Istihdam/AcikIsIlanAra.aspx?mid=2965&il=81"
ELEMAN = "https://www.eleman.net/is-ilanlari/duzce"


def getir(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def temiz(metin):
    return html.unescape(re.sub(r"<[^>]+>", " ", re.sub(r"\s+", " ", metin))).strip()


def tr_baslik(metin):
    """'DÜZCE MERKEZ' -> 'Düzce Merkez'; str.title() Türkçe İ'yi bozuyor."""
    kucuk = metin.replace("İ", "i").replace("I", "ı").lower()
    return " ".join(k[:1].replace("i", "İ").replace("ı", "I").upper() + k[1:] for k in kucuk.split())


def iskur():
    s = getir(ISKUR)
    # her ilan PopupJobDetails('ilan no', ...) bağlantısıyla başlıyor; bir sonrakine kadar olan kısım o ilanın satırı
    parcalar = re.split(r"(?=<a onclick=\"PopupJobDetails\()", s)[1:]
    for p in parcalar:
        no = re.search(r"PopupJobDetails\(&#39;(\d+)&#39;", p)
        baslik = re.search(r"style=\"font-weight:bold;\">\s*([^<]+)</a>", p)
        if not (no and baslik):
            continue
        t = temiz(p)
        yer = re.search(r"Çalışma Yeri:\s*DÜZCE\s*/\s*([^)]+)\)", t)
        kisi = re.search(r"(\d+)\s*Açık Pozisyon", t)
        son = re.search(rf"{no.group(1)}\s+(\d{{1,2}}\.\d{{1,2}}\.\d{{4}})", t)
        yield {"anahtar": "iskur:" + no.group(1), "kaynak": "İŞKUR", "baslik": baslik.group(1).strip(),
               "yer": tr_baslik(yer.group(1).strip()) if yer else "Düzce", "kisi": kisi.group(1) if kisi else "",
               "son": son.group(1) if son else "", "link": ISKUR}


def eleman():
    s = getir(ELEMAN)
    for blok in re.findall(r'<div class="c-box__body ilan_listeleme_bol[^"]*" id="ilan_id_(\d+)">(.*?)</a>', s, re.S):
        no, ic = blok
        link = re.search(r'href="([^"]+)"', ic)
        baslik = re.search(r'c-showcase-box__title[^>]*>([^<]+)<', ic)
        alt = re.search(r'c-showcase-box__subtitle">(.*?)</span>', ic, re.S)
        firma_yer = [x.strip() for x in temiz(alt.group(1).replace("<br>", "|")).split("|")] if alt else []
        if link and baslik:
            yield {"anahtar": "eleman:" + no, "kaynak": "Eleman.net",
                   "baslik": baslik.group(1).replace("(Düzce)", "").strip(),
                   "firma": firma_yer[0] if firma_yer else "", "yer": firma_yer[1] if len(firma_yer) > 1 else "Düzce",
                   "link": link.group(1)}


def satir(i):
    ek = [i.get("firma"), i.get("yer"), f"{i['kisi']} kişi" if i.get("kisi") else "",
          f"son başvuru {i['son']}" if i.get("son") else ""]
    return (f'• <a href="{html.escape(i["link"])}"><b>{html.escape(i["baslik"])}</b></a> — '
            f'{html.escape(", ".join(x for x in ek if x))} <i>({i["kaynak"]})</i>')


def main():
    simdi = datetime.now(TZ)
    durum = json.loads(DURUM.read_text(encoding="utf-8")) if DURUM.exists() else {"gorulen": {}, "kaynaklar": []}
    sinir = (simdi - SAKLA).strftime("%Y-%m-%d")
    durum["gorulen"] = {k: v for k, v in durum["gorulen"].items() if v >= sinir}

    yeni, hatalar = [], []
    for ad, okuyucu in [("İŞKUR", iskur), ("Eleman.net", eleman)]:
        try:
            ilanlar = list(okuyucu())
            if not ilanlar:
                raise ValueError("ilan bulunamadı (sayfa yapısı değişmiş olabilir)")
            ilk_kez = ad not in durum["kaynaklar"]
            for i in ilanlar:
                if i["anahtar"] not in durum["gorulen"]:
                    durum["gorulen"][i["anahtar"]] = simdi.strftime("%Y-%m-%d")
                    if not ilk_kez:
                        yeni.append(i)
            if ilk_kez:
                durum["kaynaklar"].append(ad)
        except Exception as hata:
            hatalar.append(f"{ad}: {hata}")

    for i in yeni:  # 13:00 iş ilanları özeti için
        gunluk_kaydet(KOK / "durum" / "gunluk_is.json", i, simdi)
    # Telegram mesajı 4096 karakterle sınırlı: 15'erli parçalar
    for bas in range(0, len(yeni), 15):
        parca = yeni[bas:bas + 15]
        telegram(f"💼 <b>Düzce'de yeni iş ilanı ({len(yeni)})</b>\n\n" + "\n".join(satir(i) for i in parca))
    DURUM.parent.mkdir(exist_ok=True)
    DURUM.write_text(json.dumps(durum, ensure_ascii=False), encoding="utf-8")
    print(f"{len(yeni)} yeni ilan; kayıtlı {len(durum['gorulen'])}")
    if hatalar:
        print("HATA:", *hatalar, sep="\n  ", file=sys.stderr)


if __name__ == "__main__":
    main()
