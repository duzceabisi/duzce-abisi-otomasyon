# Düzce Abisi — yerel sunucu

Sürekli açık bir bilgisayarda (macOS ya da Linux) bütün sistemi çalıştırır. GitHub sunucusuna göre farkı:

- Ev interneti engellenmez: Düzce Postası, Parantez, Damla, Oxijen, Düzce'nin Sesi ve A101 afişleri doğrudan okunur.
- Günlük paylaşımlar tam saatinde gider (GitHub 30-45 dk geciktiriyordu); haberler 5 dakikada bir taranır.
- İstenirse habere özel yapay zekâ görseli de üretilebilir (varsayılan kapalı; ücretsiz model bazen yanlış çiziyor).

## Kurulum (bir kez)

1. Gerekenler: Python 3, git, Google Chrome (Linux'ta chromium + `fonts-noto-color-emoji`).
2. Terminalde:
   ```bash
   git clone https://github.com/duzceabisi/duzce-abisi-otomasyon.git ~/duzce-abisi
   cd ~/duzce-abisi
   bash yerel/kur.sh
   ```
   Betik Telegram ve Gemini anahtarlarını sorar (ekrana yazılmaz), bir deneme turu yapar (Telegram'a göndermez)
   ve programı bilgisayar açılınca kendiliğinden başlayan bir servis olarak kurar.
   Kurulum yapay zekâ görsel modelini indirmez (önerilen). Denemek isterseniz: `bash yerel/kur.sh --gorselli`
3. Bilgisayar uykuya geçmemeli (macOS: Sistem Ayarları > Enerji; ya da `sudo pmset -a sleep 0`).
4. Yerel sunucu çalışınca GitHub'daki zamanlanmış işleri kapatın (aynı haber iki kez gitmesin):
   ```bash
   gh variable set CALISMA_YERI --body yerel -R duzceabisi/duzce-abisi-otomasyon
   ```
   Geri açmak için: `gh variable delete CALISMA_YERI -R duzceabisi/duzce-abisi-otomasyon`

## Günlük kullanım

- Kayıtlar: `kayit/dongu.log`
- Durdurma (macOS): `launchctl unload ~/Library/LaunchAgents/com.duzceabisi.bot.plist`
- Durdurma (Linux): `systemctl --user stop duzceabisi`
- Güncelleme: kendiliğinden (saatte bir `git pull`).

## Görsel motoru (.env içinde `GORSEL_MOTORU`)

| Değer | Ne yapar | Ücret |
|---|---|---|
| `yerel` | Bilgisayardaki açık kaynak model habere özel görsel üretir | Ücretsiz |
| `openai` | OpenAI görsel API'si (`OPENAI_API_KEY`, hesapta kredi gerekir) | Görsel başına ücretli |
| `gemini` | Gemini görsel API'si (projede faturalandırma açık olmalı) | Görsel başına ücretli |
| boş (varsayılan) | Habere özel görsel yok; seçilmiş görsel kütüphanesi ve kurumsal zemin kullanılır | Ücretsiz |

Not: ChatGPT ve Gemini'nin web sitelerini (Pro üyelik) programla kullanmak kullanım şartlarına aykırıdır ve
hesabın kapatılmasına yol açabilir; bu yüzden sistem yalnızca resmi API'leri ya da yerel modeli kullanır.
