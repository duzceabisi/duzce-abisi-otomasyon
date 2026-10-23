#!/usr/bin/env bash
# Düzce Abisi yerel sunucu kurulumu (macOS ya da Linux). Tek komut:
#   bash yerel/kur.sh              kurulum (önerilen)
#   bash yerel/kur.sh --gorselli   yerel görsel modelini de kurar (~2 GB; varsayılan: kurulmaz)
set -euo pipefail
cd "$(dirname "$0")/.."
KOK="$(pwd)"
GORSEL=0; [ "${1:-}" = "--gorselli" ] && GORSEL=1
echo "== Düzce Abisi kurulumu: $KOK"

# Görsel modeli (torch) en yeni Python sürümlerini hemen desteklemiyor: 3.12 / 3.13 / 3.11 tercih edilir
PY=""
for v in python3.12 python3.13 python3.11 python3; do
  for yol in "$(command -v $v 2>/dev/null)" "/opt/homebrew/bin/$v" "/usr/local/bin/$v"; do
    [ -n "$yol" ] && [ -x "$yol" ] && { PY="$yol"; break 2; }
  done
done
[ -n "$PY" ] || { echo "Python 3 gerekli (macOS: brew install python@3.12; Linux: sudo apt install python3 python3-venv)"; exit 1; }
echo "== Python: $PY ($($PY --version))"
command -v git >/dev/null || { echo "git gerekli"; exit 1; }
if [ "$(uname)" = "Darwin" ]; then
  [ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ] || { echo "Google Chrome gerekli: https://www.google.com/chrome"; exit 1; }
else
  command -v google-chrome >/dev/null || command -v chromium >/dev/null || command -v chromium-browser >/dev/null || {
    echo "Chrome/Chromium gerekli (Ubuntu: sudo apt install chromium-browser fonts-noto-color-emoji)"; exit 1; }
fi

"$PY" -m venv .venv
.venv/bin/pip install -q --upgrade pip
if [ $GORSEL = 1 ]; then
  echo "== Görsel modeli kütüphaneleri kuruluyor (birkaç dakika sürebilir)"
  .venv/bin/pip install -q torch diffusers transformers accelerate || {
    echo "!! Görsel modeli kurulamadı (Python sürümü desteklenmiyor olabilir: brew install python@3.12). Görselsiz devam ediliyor."; GORSEL=0; }
fi

# Ayarlar: .env yoksa sorarak oluştur (anahtarlar ekrana yazılmaz)
if [ ! -f .env ]; then
  echo "== Ayarlar (.env) oluşturuluyor"
  read -rsp "Telegram bot anahtarı (BotFather): " TG; echo
  read -rp  "Telegram sohbet kimlikleri (virgülle): " CHAT
  read -rsp "Gemini API anahtarı (aistudio.google.com/apikey): " GEM; echo
  printf 'TELEGRAM_BOT_TOKEN=%s\nTELEGRAM_CHAT_ID=%s\nGEMINI_API_KEY=%s\n' "$TG" "$CHAT" "$GEM" > .env
  chmod 600 .env
fi
# Habere özel yapay zekâ görseli varsayılan olarak KAPALI: ücretsiz yerel model olayları yanlış çizebiliyor
# (fındığı soğan gibi, Düzce'yi şato gibi). Kartlar seçilmiş görsel kütüphanesi ve kurumsal zeminle çizilir.
# Açmak için .env içinde GORSEL_MOTORU=yerel yazın (bkz. BENIOKU.md).
grep -q '^GORSEL_MOTORU=' .env || echo "GORSEL_MOTORU=" >> .env

echo "== Deneme turu (Telegram'a gönderilmez)"
DENEME=1 .venv/bin/python yerel/dongu.py --bir-tur || true

# Servis: bilgisayar açılınca başlasın, çökerse yeniden başlasın
if [ "$(uname)" = "Darwin" ]; then
  PLIST="$HOME/Library/LaunchAgents/com.duzceabisi.bot.plist"
  mkdir -p "$HOME/Library/LaunchAgents"
  cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.duzceabisi.bot</string>
  <key>ProgramArguments</key><array><string>$KOK/.venv/bin/python</string><string>$KOK/yerel/dongu.py</string></array>
  <key>WorkingDirectory</key><string>$KOK</string>
  <key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$KOK/kayit/servis.log</string>
  <key>StandardErrorPath</key><string>$KOK/kayit/servis.log</string>
</dict></plist>
PL
  mkdir -p kayit
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST"
  echo "== Servis kuruldu (launchd). Durdurmak: launchctl unload $PLIST"
  echo "   Uyku: Sistem Ayarları > Pil/Enerji > 'ekran kapalıyken uykuya geçme' açık olmalı (ya da: sudo pmset -a sleep 0)"
else
  mkdir -p "$HOME/.config/systemd/user" kayit
  cat > "$HOME/.config/systemd/user/duzceabisi.service" <<SV
[Unit]
Description=Düzce Abisi bot
After=network-online.target
[Service]
WorkingDirectory=$KOK
ExecStart=$KOK/.venv/bin/python $KOK/yerel/dongu.py
Restart=always
RestartSec=30
[Install]
WantedBy=default.target
SV
  systemctl --user daemon-reload
  systemctl --user enable --now duzceabisi.service
  loginctl enable-linger "$USER" 2>/dev/null || true
  echo "== Servis kuruldu (systemd). Durum: systemctl --user status duzceabisi"
fi
echo "== Bitti. Kayıtlar: $KOK/kayit/dongu.log"
