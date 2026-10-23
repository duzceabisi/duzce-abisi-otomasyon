#!/usr/bin/env python3
"""Bir klasördeki PNG'leri Telegram'a albüm olarak gönderir.

Kullanım:  python3 gonder.py cikti/2026-10-22-sabah "Açıklama metni"
Ayarlar:   TELEGRAM_BOT_TOKEN ve TELEGRAM_CHAT_ID (virgülle ayrılmış) ortam
           değişkenlerinden, yoksa .env dosyasından okunur.
"""
import json, os, sys, urllib.request, uuid
from pathlib import Path

KOK = Path(__file__).resolve().parent


def ayar(ad):
    if os.environ.get(ad):
        return os.environ[ad]
    env = KOK / ".env"
    if env.exists():
        for satir in env.read_text(encoding="utf-8-sig").splitlines():
            if satir.startswith(ad + "="):
                return satir.split("=", 1)[1].strip()
    sys.exit(f"{ad} bulunamadı (.env ya da ortam değişkeni)")


def deneme_modu():
    """DENEME=1: Telegram'a gönderme, ne gönderileceğini yazdır (kurulum ve test için)."""
    return os.environ.get("DENEME") == "1"


def cok_parcali(alanlar, dosyalar):
    sinir = uuid.uuid4().hex
    govde = b""
    for ad, deger in alanlar.items():
        govde += f'--{sinir}\r\nContent-Disposition: form-data; name="{ad}"\r\n\r\n{deger}\r\n'.encode()
    for ad, yol in dosyalar.items():
        govde += (f'--{sinir}\r\nContent-Disposition: form-data; name="{ad}"; filename="{yol.name}"\r\n'
                  f"Content-Type: image/png\r\n\r\n").encode() + yol.read_bytes() + b"\r\n"
    return govde + f"--{sinir}--\r\n".encode(), f"multipart/form-data; boundary={sinir}"


def gonder(klasor, aciklama):
    token = ayar("TELEGRAM_BOT_TOKEN")
    pngler = sorted(Path(klasor).glob("*.png"))
    if not pngler:
        sys.exit(f"{klasor} içinde PNG yok")
    if deneme_modu():
        print(f"[DENEME] albüm: {len(pngler)} görsel ({klasor}) | {aciklama[:80]!r}")
        return
    for chat in ayar("TELEGRAM_CHAT_ID").split(","):
        for bas in range(0, len(pngler), 10):  # Telegram albümü en fazla 10 görsel alır
            grup = pngler[bas:bas + 10]
            medya = [{"type": "photo", "media": f"attach://p{i}"} for i in range(len(grup))]
            if bas == 0:
                medya[0]["caption"] = aciklama
            govde, tur = cok_parcali({"chat_id": chat.strip(), "media": json.dumps(medya, ensure_ascii=False)},
                                     {f"p{i}": p for i, p in enumerate(grup)})
            istek = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMediaGroup",
                                           data=govde, headers={"Content-Type": tur})
            with urllib.request.urlopen(istek, timeout=60) as r:
                sonuc = json.load(r)
            print(chat.strip(), "ok" if sonuc.get("ok") else sonuc)


if __name__ == "__main__":
    gonder(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "")
