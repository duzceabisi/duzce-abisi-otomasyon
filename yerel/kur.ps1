# Düzce Abisi yerel sunucu kurulumu (Windows 10/11).
# Çalıştırma: yerel\windows-kur.bat dosyasına çift tıklayın (ya da: powershell -ExecutionPolicy Bypass -File yerel\kur.ps1)
#   -Deneme   görevi kaydeder ama başlatmaz (otomatik test için)
param([switch]$Deneme)
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$KOK = Split-Path -Parent $PSScriptRoot
Set-Location $KOK
$GOREV = "DuzceAbisiBot"
Write-Host "== Düzce Abisi kurulumu: $KOK"

function Var($komut) { [bool](Get-Command $komut -ErrorAction SilentlyContinue) }

function Eksik($ad, $winget) {
    Write-Host "!! $ad bulunamadı." -ForegroundColor Yellow
    if ((Var winget) -and -not $Deneme) {
        $c = Read-Host "$ad şimdi kurulsun mu? (E/h)"
        if ($c -ne "h") {
            winget install -e --id $winget
            Write-Host "$ad kuruldu. Bu pencereyi kapatıp windows-kur.bat'ı yeniden çalıştırın." -ForegroundColor Green
            exit 1
        }
    }
    Write-Host "Kurup tekrar deneyin:  winget install -e --id $winget"
    exit 1
}

# 1) Python 3.9+ (py başlatıcısı ya da python)
$PY = $null
if (Var py) {
    foreach ($v in "-3.12", "-3.13", "-3.11", "-3") {
        & py $v -c "import sys; assert sys.version_info >= (3, 9)" 2>$null
        if ($LASTEXITCODE -eq 0) { $PY = @("py", $v); break }
    }
}
if (-not $PY -and (Var python)) {
    & python -c "import sys; assert sys.version_info >= (3, 9)" 2>$null
    if ($LASTEXITCODE -eq 0) { $PY = @("python") }
}
if (-not $PY) { Eksik "Python 3" "Python.Python.3.12" }
if (-not (Var git)) { Eksik "Git" "Git.Git" }

# 2) Sanal ortam ve tek bağımlılık (Windows'ta saat dilimi verisi)
Write-Host "== Python ortamı hazırlanıyor"
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    if ($PY.Count -gt 1) { & $PY[0] $PY[1] -m venv .venv } else { & $PY[0] -m venv .venv }
}
$VPY = Join-Path $KOK ".venv\Scripts\python.exe"
$VPYW = Join-Path $KOK ".venv\Scripts\pythonw.exe"
if (-not (Test-Path $VPY)) { Write-Host "!! Python ortamı oluşturulamadı." -ForegroundColor Red; exit 1 }
& $VPY -m pip install -q --disable-pip-version-check tzdata
$env:PYTHONUTF8 = "1"

# 3) Chrome (yoksa Edge kullanılır; ikisi de görselleri çizer)
$CHROME = (& $VPY -c "from ciz import CHROME; print(CHROME or '')").Trim()
if (-not $CHROME) { Eksik "Google Chrome" "Google.Chrome" }
Write-Host "   tarayıcı: $CHROME"

# 4) Anahtarlar (.env; ekrana yazılmaz, yalnızca bu bilgisayarda kalır)
function Gizli($soru) {
    $s = Read-Host $soru -AsSecureString
    [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($s))
}
if (-not (Test-Path ".env")) {
    if ($env:TELEGRAM_BOT_TOKEN) {
        $TG = $env:TELEGRAM_BOT_TOKEN; $CHAT = $env:TELEGRAM_CHAT_ID; $GEM = $env:GEMINI_API_KEY
    } else {
        $TG = Gizli "Telegram bot anahtarı (BotFather)"
        $CHAT = Read-Host "Telegram sohbet kimlikleri (virgülle)"
        $GEM = Gizli "Gemini API anahtarı (aistudio.google.com/apikey)"
    }
    $icerik = "TELEGRAM_BOT_TOKEN=$TG`nTELEGRAM_CHAT_ID=$CHAT`nGEMINI_API_KEY=$GEM`nGORSEL_MOTORU=`n"
    [IO.File]::WriteAllText((Join-Path $KOK ".env"), $icerik, (New-Object Text.UTF8Encoding($false)))
    Write-Host "   .env oluşturuldu"
}

# 5) Deneme turu: Telegram'a hiçbir şey gönderilmez
Write-Host "== Deneme turu (Telegram'a gönderilmez, birkaç dakika sürebilir)"
$env:DENEME = "1"
& $VPY yerel\dongu.py --bir-tur
Remove-Item Env:DENEME

# 6) Windows açılıp oturum açılınca kendiliğinden başlayan, penceresiz görev
Write-Host "== Otomatik başlatma görevi kaydediliyor: $GOREV"
$eylem = New-ScheduledTaskAction -Execute $VPYW -Argument "`"$KOK\yerel\dongu.py`"" -WorkingDirectory $KOK
$tetik = New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$ayar = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $GOREV -Action $eylem -Trigger $tetik -Settings $ayar -Force `
    -Description "Düzce Abisi: haber, günlük paylaşım ve duyuruları Telegram'a gönderir" | Out-Null
if (-not (Get-ScheduledTask -TaskName $GOREV -ErrorAction SilentlyContinue)) {
    Write-Host "!! Görev kaydedilemedi. windows-kur.bat'a sağ tıklayıp 'Yönetici olarak çalıştır' deneyin." -ForegroundColor Red
    exit 1
}
if (-not $Deneme) { Start-ScheduledTask -TaskName $GOREV }

Write-Host ""
Write-Host "== Kurulum tamam. Bot arka planda çalışıyor (pencere açılmaz)." -ForegroundColor Green
Write-Host "   Kayıtlar : $KOK\kayit\dongu.log"
Write-Host "   Durdurma : Görev Zamanlayıcı > $GOREV > Sonlandır   (ya da: schtasks /End /TN $GOREV)"
Write-Host "   Kaldırma : schtasks /Delete /TN $GOREV /F"
Write-Host "   ÖNEMLİ   : Ayarlar > Sistem > Güç'te uyku 'Hiçbir zaman' olmalı; bilgisayar kapanırsa bot da durur."
