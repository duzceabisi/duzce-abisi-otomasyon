# Düzce Abisi — sabah paylaşım paketi görevi

Bu dosya, her sabah 08.00'de (Türkiye saati) çalışan Claude görevinin talimatıdır.
Amaç: Düzce Abisi Instagram sayfası için günün kaydırmalı gönderisini hazırlayıp
Telegram'dan sahibine onaya göndermek.

## Adımlar

1. `python3 topla.py` çalıştır. Bugünün `veri/YYYY-MM-DD-sabah.json` dosyasını
   oluşturur: hava, döviz, altın, akaryakıt, nöbetçi eczaneler. Çıktıdaki
   `eksik` listesini not et.
2. Aşağıdaki bölümleri web'de araştırıp aynı JSON dosyasına ekle. Biçim için
   `veri/ornek-sabah.json` örneğine bak.
   - `kesinti`: Düzce için **bugünkü** planlı elektrik (SEDAŞ) ve su kesintileri,
     ilçe ilçe saat aralıklarıyla. Kesinti yoksa bu alanı hiç ekleme.
   - `etkinlik`: Bu akşam Düzce'de tarihi ve saati doğrulanmış bir etkinlik
     varsa. Yoksa ekleme.
   - `tarihte_bugun`: Bugünün tarihine ait 5–6 olay, en az biri Türkiye tarihinden.
   - `onemli_gun`: Bugün anılan, geniş kitleyi ilgilendiren bir gün (ad, ikon,
     tek cümlelik mesaj, iki cümlelik açıklama). Yoksa ekleme.
   - `manset`: Bütün bölümlerden, en çok ilgi çekecek sırayla 5 kısa başlık
     (en fazla 45 karakter).
   - `hava.not`: Meteoroloji (MGM) Düzce için bugün uyarı yayımladıysa kısa
     uyarı metni; topla.py'nin sis notu varsa koru.
3. `python3 ciz.py veri/YYYY-MM-DD-sabah.json` ile görselleri üret. Kapak ve
   en az iki görseli açıp bak: taşma, kesik yazı, kutu (bozuk) emoji olmamalı.
4. `python3 gonder.py cikti/YYYY-MM-DD-sabah "<açıklama>"` ile Telegram'a gönder.
   Açıklama: ilk satır `📲 Düzce Abisi — <tarih> sabah paketi`, ardından
   Instagram'a yapıştırılabilecek 3–4 satırlık gönderi metni ve 5–8 etiket
   (#düzce #düzcehaber ...). `eksik` boş değilse en sona
   `⚠️ Eksik: ...` satırı ekle.

## Kurallar

- Yalnızca **bugünün tarihli** ve doğrulanmış bilgiyi kullan. Eski haberi bugün
  olmuş gibi sunma. Doğrulayamadığın bölümü boş bırak; uydurma.
- Haberleri kendi cümlelerinle yaz; başka sitelerin metnini ya da fotoğrafını kopyalama.
- topla.py'nin çektiği rakamları değiştirme.
- Instagram'da kendin paylaşım yapma; onay sahibindedir.
