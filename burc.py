#!/usr/bin/env python3
"""Günlük burç yorumları (eğlence amaçlı).

Yapay zekâ kullanılmaz: her burç için cümle havuzundan, tarihe bağlı sabit bir
seçimle günlük yorum üretilir. Aynı gün aynı sonucu verir; her gün değişir.
Havuzlara cümle eklemek yorum çeşitliliğini artırır.
"""
import hashlib
from datetime import date

BURCLAR = [
    ("Koç", "♈", "21 Mart – 19 Nisan", "ateş"), ("Boğa", "♉", "20 Nisan – 20 Mayıs", "toprak"),
    ("İkizler", "♊", "21 Mayıs – 20 Haziran", "hava"), ("Yengeç", "♋", "21 Haziran – 22 Temmuz", "su"),
    ("Aslan", "♌", "23 Temmuz – 22 Ağustos", "ateş"), ("Başak", "♍", "23 Ağustos – 22 Eylül", "toprak"),
    ("Terazi", "♎", "23 Eylül – 22 Ekim", "hava"), ("Akrep", "♏", "23 Ekim – 21 Kasım", "su"),
    ("Yay", "♐", "22 Kasım – 21 Aralık", "ateş"), ("Oğlak", "♑", "22 Aralık – 19 Ocak", "toprak"),
    ("Kova", "♒", "20 Ocak – 18 Şubat", "hava"), ("Balık", "♓", "19 Şubat – 20 Mart", "su"),
]

GENEL = {
    "ateş": ["Enerjin yüksek; ertelediğin bir işi bugün bitirebilirsin.", "Cesur bir adım atmak için uygun bir gün.",
             "Sabırsızlığını kontrol edersen gün senin lehine döner.", "Liderlik etmen gereken bir durum çıkabilir.",
             "Yeni bir başlangıç için içinde güçlü bir istek var.", "Hızlı karar vermek bugün işine yarayabilir."],
    "toprak": ["Planlı ilerlemek bugün sana kazandırır.", "Küçük ama sağlam adımlar atmanın tam zamanı.",
               "Uzun süredir beklediğin bir haber gelebilir.", "Düzen kurmak zihnini rahatlatacak.",
               "Emeğinin karşılığını görmeye başlıyorsun.", "Bugün detaylara dikkat etmek seni öne çıkarır."],
    "hava": ["Yeni insanlarla tanışmak sana iyi gelecek.", "Aklındaki fikri paylaşmak için doğru gün.",
             "Kısa bir yolculuk ya da değişiklik moralini yükseltebilir.", "İletişim gücün bugün çok yüksek.",
             "Bir sohbetten beklemediğin bir fırsat çıkabilir.", "Merakın seni yeni bir konuya yönlendirebilir."],
    "su": ["Sezgilerine güvenirsen doğru yolu bulursun.", "Duygusal olarak toparlandığın bir gün.",
           "Yakınlarınla geçireceğin zaman sana güç verecek.", "İçinden gelen sesi dinlemenin zamanı.",
           "Eski bir konuyu kapatmak seni hafifletecek.", "Bugün anlayışlı tavrın takdir görecek."],
}
ASK = ["Aşkta sürpriz bir mesaj seni gülümsetebilir.", "İlişkinde açık konuşmak bağınızı güçlendirir.",
       "Bekarlar için ilginç bir tanışma olabilir.", "Partnerinle küçük bir planı hayata geçirin.",
       "Duygularını göstermekten çekinme.", "Kıskançlık yerine güveni seçersen gün güzel geçer.",
       "Gönül işlerinde acele etme, zaman senin lehine.", "Eski bir dosttan beklenmedik bir haber gelebilir."]
PARA = ["Harcamalarına dikkat; plansız alışverişten kaçın.", "İşte emeğin fark ediliyor.",
        "Ek bir gelir fikri aklına gelebilir.", "Ödeme ve borçları gözden geçirmek için uygun gün.",
        "Bir iş görüşmesi ya da teklif gündeme gelebilir.", "Ortak işlerde yazılı anlaşma yapmayı unutma.",
        "Tasarruf için küçük bir adım büyük fark yaratır.", "Kariyerinde yeni bir kapı aralanıyor."]
SAGLIK = ["Bol su içmeyi ihmal etme.", "Kısa bir yürüyüş enerjini toplar.", "Uykuna dikkat etmelisin.",
          "Stresi azaltmak için kendine zaman ayır.", "Beslenmene biraz daha özen göster.", "Ekran başında mola vermeyi unutma."]
RENK = ["kırmızı", "mavi", "yeşil", "sarı", "mor", "turuncu", "beyaz", "lacivert", "pembe", "turkuaz"]


def _sec(liste, *anahtar):
    h = int(hashlib.sha256("|".join(map(str, anahtar)).encode()).hexdigest(), 16)
    return liste[h % len(liste)]


def gunluk_burclar(gun=None):
    gun = gun or date.today()
    out = []
    for ad, simge, aralik, oge in BURCLAR:
        yorum = " ".join([_sec(GENEL[oge], gun, ad, "g"), _sec(ASK, gun, ad, "a"), _sec(PARA, gun, ad, "p"),
                          _sec(SAGLIK, gun, ad, "s")])
        sayi = int(hashlib.sha256(f"{gun}{ad}n".encode()).hexdigest(), 16) % 9 + 1
        out.append({"ad": ad, "simge": simge, "tarih": aralik, "yorum": yorum, "sans": f"{sayi} · {_sec(RENK, gun, ad, 'r')}"})
    return out


if __name__ == "__main__":
    for b in gunluk_burclar()[:3]:
        print(b)
