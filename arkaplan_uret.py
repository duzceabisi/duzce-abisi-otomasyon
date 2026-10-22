#!/usr/bin/env python3
"""Haber kartları için temsili arka plan kütüphanesi üretir (tek seferlik; .github/workflows/arkaplan.yml).

Ücretsiz, açık kaynak LCM Dreamshaper v7 modeli GitHub sunucusunun işlemcisinde çalışır
(ekran kartı yok; görsel başına ~55 sn). Çıktı: arkaplan/<kategori>-<n>.jpg
Görseller temsilidir: insan yüzü ve yazı içermez, olayı birebir canlandırmaz.

Kullanım:  python arkaplan_uret.py            hepsi
           python arkaplan_uret.py deprem     yalnızca bir kategori
"""
import sys, time
from pathlib import Path

KOK = Path(__file__).resolve().parent
HEDEF = KOK / "arkaplan"
ORTAK = ", cinematic, moody, atmospheric, high detail, no people, no faces, no text, no letters, no watermark"
ISTEMLER = {
    "kaza": ["empty wet asphalt road at night, red and blue emergency lights glowing in fog, traffic lights",
             "highway at dusk with traffic cones and flashing orange warning lights, rain reflections",
             "rainy night street, blurred ambulance lights in the distance, glossy asphalt"],
    "yangin": ["industrial building silhouette with orange fire glow and thick smoke in the night sky",
               "firefighter truck lights in the distance, smoke rising over rooftops, orange glow",
               "dark smoke clouds lit by fire from below, small town skyline at night"],
    "deprem": ["deep cracks in asphalt road, broken ground, dust floating in golden light, small town houses",
               "cracked concrete street after earthquake, debris, dusty atmosphere, dramatic light",
               "large crack splitting an empty road, fallen stones, hazy sunset light"],
    "hava": ["heavy storm clouds over a small green valley town, lightning, rain",
             "torrential rain on a street, water flowing on the road, dark sky",
             "strong wind bending trees, dark stormy sky, Black Sea coast waves"],
    "kesinti": ["dark city at night during power outage, electric poles and cables silhouette, few dim windows",
                "electricity pylons and power lines against dramatic sky, maintenance work lights",
                "water pipe repair site at night with work lights, wet ground"],
    "okul": ["empty school corridor with lockers, soft morning light", "school building exterior on a rainy morning",
             "empty classroom with desks and chalkboard, quiet morning light"],
    "kayip": ["misty forest path at dawn, soft light through trees", "foggy countryside road at dusk, lonely atmosphere",
              "search flashlight beams in a dark foggy forest"],
    "olum": ["single candle glowing in the dark with soft bokeh, white flowers, calm and respectful",
             "white lilies on a dark background, soft light, calm and respectful",
             "dark calm sky at dusk with soft light rays, peaceful and respectful"],
    "firsat": ["colorful busy market street stalls in daylight, festive atmosphere", "bright shopping bags and confetti on a warm background",
               "sunny town square with festival lights and flags"],
    "findik": ["hazelnut orchard on green hills by the Black Sea, morning sun", "close up of hazelnuts in a wooden basket, warm light",
               "rolling green hazelnut garden hills under soft clouds"],
    "asayis": ["blurred police car lights at night on a wet street", "city street at night with police tape bokeh lights",
               "night patrol lights reflecting on a rainy road"],
    "genel": ["panorama of a small Turkish city in a green valley with mountains, morning light",
              "green mountains and town rooftops at sunrise, soft fog", "town square with mosque minaret silhouette at golden hour"],
}


def main():
    import torch
    from diffusers import DiffusionPipeline
    torch.set_num_threads(4)
    pipe = DiffusionPipeline.from_pretrained("SimianLuo/LCM_Dreamshaper_v7", torch_dtype=torch.float32, safety_checker=None)
    HEDEF.mkdir(exist_ok=True)
    secili = sys.argv[1:] or list(ISTEMLER)
    for kat in secili:
        for n, istem in enumerate(ISTEMLER[kat], 1):
            t = time.time()
            img = pipe(prompt=istem + ORTAK, num_inference_steps=6, guidance_scale=8.0, width=576, height=1024).images[0]
            img.convert("RGB").save(HEDEF / f"{kat}-{n}.jpg", quality=90)
            print(f"{kat}-{n}: {time.time() - t:.0f} sn", flush=True)


if __name__ == "__main__":
    main()
