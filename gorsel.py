#!/usr/bin/env python3
"""Habere özel temsili görsel üretir (yalnızca yerel sunucuda; GitHub'da kapalı).

Motor GORSEL_MOTORU ortam değişkeni / .env ile seçilir:
  yerel   Bilgisayardaki açık kaynak model (LCM Dreamshaper v7, ücretsiz). Apple çipte (mps) ya da
          NVIDIA ekran kartında (cuda) birkaç saniye; yalnız işlemcide ~1 dk.
  openai  OpenAI görsel API'si (ücretli; OPENAI_API_KEY ve hesapta kredi gerekir)
  gemini  Gemini görsel API'si (ücretli; projede faturalandırma açık olmalı)
  (boş)   Habere özel görsel üretilmez; kart arkaplan/ kütüphanesinden görsel kullanır.

habere_ozel(sahne, kategori) -> Path ya da None. Hata olursa None döner; kart kütüphane görseliyle devam eder.
"""
import base64, hashlib, json, os, sys, urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parent
HEDEF = KOK / "cikti" / "ozel"
ORTAK = (", cinematic editorial illustration, moody atmospheric light, Turkish small city setting, "
         "no people faces, no text, no letters, no logo, no watermark")
_pipe = None


def _ayar(ad):
    if os.environ.get(ad):
        return os.environ[ad]
    env = KOK / ".env"
    if env.exists():
        for satir in env.read_text(encoding="utf-8").splitlines():
            if satir.startswith(ad + "="):
                return satir.split("=", 1)[1].strip()
    return ""


def _yerel(istem, yol):
    global _pipe
    import torch
    from diffusers import DiffusionPipeline
    if _pipe is None:  # model bir kez yüklenir, döngü boyunca bellekte kalır
        cihaz = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
        tip = torch.float16 if cihaz == "cuda" else torch.float32
        _pipe = DiffusionPipeline.from_pretrained("SimianLuo/LCM_Dreamshaper_v7", torch_dtype=tip, safety_checker=None).to(cihaz)
        print(f"görsel modeli yüklendi ({cihaz})", file=sys.stderr)
    img = _pipe(prompt=istem, num_inference_steps=6, guidance_scale=8.0, width=576, height=1024).images[0]
    img.convert("RGB").save(yol, quality=92)


def _openai(istem, yol):
    govde = {"model": _ayar("OPENAI_GORSEL_MODEL") or "gpt-image-1-mini", "prompt": istem, "size": "1024x1536", "quality": "medium"}
    istek = urllib.request.Request("https://api.openai.com/v1/images/generations", data=json.dumps(govde).encode(),
                                   headers={"Authorization": "Bearer " + _ayar("OPENAI_API_KEY"), "Content-Type": "application/json"})
    with urllib.request.urlopen(istek, timeout=180) as r:
        yol.write_bytes(base64.b64decode(json.load(r)["data"][0]["b64_json"]))


def _gemini(istem, yol):
    govde = {"contents": [{"parts": [{"text": istem}]}],
             "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "9:16"}}}
    istek = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image:generateContent",
                                   data=json.dumps(govde).encode(),
                                   headers={"Content-Type": "application/json", "x-goog-api-key": _ayar("GEMINI_API_KEY")})
    with urllib.request.urlopen(istek, timeout=180) as r:
        parca = [p for p in json.load(r)["candidates"][0]["content"]["parts"] if "inlineData" in p][0]
    yol.write_bytes(base64.b64decode(parca["inlineData"]["data"]))


MOTORLAR = {"yerel": _yerel, "openai": _openai, "gemini": _gemini}


def habere_ozel(sahne, kategori=""):
    motor = _ayar("GORSEL_MOTORU").lower()
    if motor not in MOTORLAR or not sahne:
        return None
    HEDEF.mkdir(parents=True, exist_ok=True)
    yol = HEDEF / (hashlib.md5(sahne.encode()).hexdigest()[:16] + ".jpg")
    if yol.exists():
        return yol
    try:
        MOTORLAR[motor](sahne.rstrip(". ") + ORTAK, yol)
        return yol
    except Exception as hata:
        print(f"habere özel görsel üretilemedi ({motor}): {hata}", file=sys.stderr)
        return None


if __name__ == "__main__":
    os.environ.setdefault("GORSEL_MOTORU", "yerel")
    print(habere_ozel(" ".join(sys.argv[1:]) or "rural mountain road after landslide, muddy asphalt, overcast morning"))
