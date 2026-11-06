# ============================================================
#  chrome_debug.ps1 - BUKA CHROME DEBUG SEKALI KLIK
#  Inventory Adjusment Tools
# ============================================================
#  Replika tombol "Buka Chrome Debug" di UI (ui_app.py v5.5),
#  TANPA perlu membuka aplikasi/MULAI.bat:
#    1. Chrome debug sudah hidup di 9222-9225? -> tidak relaunch.
#    2. Cari chrome.exe (Program Files / x86 / LOCALAPPDATA / PATH).
#    3. Tutup instance ChromeDebugProfile lama yang tanpa port
#       (penyebab klasik port tidak pernah aktif).
#    4. Pilih port BEBAS pertama (9222 -> 9225, auto-switch).
#    5. Launch Chrome + anti-throttle flags + https://accurate.id
#    6. Poll /json/version 30 detik -> OK / FAIL + diagnosis.
#    7. Sinkronkan port ke "2. Import IA\ui_settings.json"
#       supaya UI & semua tool mengikuti port yang sama.
#
#  Dipanggil oleh: BUKA_CHROME_DEBUG.bat (double-click itu saja)
# ============================================================

$ErrorActionPreference = "Continue"
$Candidates = 9222, 9223, 9224, 9225

function Test-DevTools {
    param([int]$Port)
    # Jujur: True HANYA kalau /json/version menjawab JSON berisi "Chrome/".
    # Port TCP kebuka saja TIDAK cukup (bisa dipakai proses lain).
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/json/version" `
                -TimeoutSec 2 -UseBasicParsing
        if ($r.Content -match 'Chrome/') { return $true }
    } catch { }
    return $false
}

function Get-PortOwner {
    param([int]$Port)
    # (nama proses + PID) yang LISTEN di port, atau $null.
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -State Listen `
                    -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($conn) {
            $ownerPid = $conn.OwningProcess
            $proc = Get-Process -Id $ownerPid -ErrorAction SilentlyContinue
            if ($proc) { return "$($proc.ProcessName).exe (PID $ownerPid)" }
            return "PID $ownerPid"
        }
    } catch { }
    return $null
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   BUKA CHROME DEBUG - Inventory Adjusment Tools" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# ---------- 1) Chrome debug sudah hidup di port mana pun? ----------
foreach ($p in $Candidates) {
    if (Test-DevTools -Port $p) {
        Write-Host "[OK] Chrome debug SUDAH aktif di port $p - tidak diluncurkan ulang." -ForegroundColor Green
        Write-Host "     Semua tool auto-detect port ini (scan 9222-9225). Aman dipakai." -ForegroundColor Gray
        Write-Host ""
        Write-Host "Jendela ini tutup otomatis dalam 5 detik..."
        Start-Sleep -Seconds 5
        exit 0
    }
}

# ---------- 2) Cari chrome.exe ----------
$chromePaths = @(
    (Join-Path $env:ProgramFiles "Google\Chrome\Application\chrome.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Google\Chrome\Application\chrome.exe"),
    (Join-Path $env:LOCALAPPDATA  "Google\Chrome\Application\chrome.exe")
)
$chrome = $chromePaths | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $chrome) {
    $cmd = Get-Command chrome.exe -ErrorAction SilentlyContinue
    if ($cmd) { $chrome = $cmd.Source }
}
if (-not $chrome) {
    Write-Host "[ERROR] chrome.exe tidak ditemukan." -ForegroundColor Red
    Write-Host "        Cek manual: C:\Program Files\Google\Chrome\Application\chrome.exe" -ForegroundColor Red
    Read-Host "Tekan ENTER untuk keluar"
    exit 1
}
Write-Host "[INFO] Chrome ditemukan: $chrome"

# ---------- 3) Tutup Chrome debug lama (profil sama tanpa port) ----------
$stale = Get-CimInstance Win32_Process -Filter "Name='chrome.exe'" -ErrorAction SilentlyContinue |
         Where-Object { $_.CommandLine -like '*ChromeDebugProfile*' -or
                        $_.CommandLine -like '*ChromeDebug_Accurate*' }
if ($stale) {
    $n = @($stale).Count
    Write-Host "[INFO] Menutup $n Chrome debug lama (instance tanpa port debug)..."
    $stale | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
}

# ---------- 4) Pilih port BEBAS pertama (9222 -> 9225) ----------
$chosen = $null
foreach ($p in $Candidates) {
    $owner = Get-PortOwner -Port $p
    if ($owner) {
        Write-Host "[DIAG] Port $p dipakai proses lain: $owner" -ForegroundColor Yellow
    } else {
        $chosen = $p
        break
    }
}
if (-not $chosen) {
    $chosen = $Candidates[0]
    Write-Host "[WARN] Semua port $Candidates dipakai proses lain - tetap coba port $chosen." -ForegroundColor Yellow
} elseif ($chosen -ne 9222) {
    Write-Host "[INFO] Port 9222 dipakai proses lain -> otomatis pakai port $chosen." -ForegroundColor Yellow
}

# ---------- 5) Launch Chrome (flags sama persis dengan UI v5.5) ----------
$null = Start-Process -FilePath $chrome -ArgumentList @(
    "--remote-debugging-port=$chosen",
    "--user-data-dir=C:\ChromeDebugProfile",
    "--no-first-run",
    "--no-default-browser-check",
    "--hide-crash-restore-bubble",
    "--disable-background-timer-throttling",     # JS timer full speed saat background
    "--disable-backgrounding-occluded-windows",  # window ketutup app lain tetap prioritas
    "--disable-renderer-backgrounding",          # rendering priority tetap tinggi
    "https://accurate.id"
)
Write-Host "[INFO] Chrome diluncurkan (port $chosen) - menunggu DevTools menjawab (maks 30s)..."

# ---------- 6) Poll /json/version di port terpilih ----------
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    if (Test-DevTools -Port $chosen) { $ok = $true; break }
}

if ($ok) {
    Write-Host "[OK] Chrome $chosen HIDUP - siap dipakai semua tool." -ForegroundColor Green

    # ---------- 7) Sinkronkan port ke ui_settings.json (tanpa BOM!) ----------
    try {
        $settingsPath = Join-Path $PSScriptRoot "2. Import IA\ui_settings.json"
        if (Test-Path $settingsPath) {
            $json = Get-Content $settingsPath -Raw -Encoding UTF8 | ConvertFrom-Json
            $json | Add-Member -NotePropertyName sj_debug_port `
                               -NotePropertyValue $chosen -Force
            $out = $json | ConvertTo-Json -Depth 5
            $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
            [System.IO.File]::WriteAllText($settingsPath, $out + "`n", $utf8NoBom)
            Write-Host "[OK] Port $chosen tersimpan di ui_settings.json - UI akan ikut port ini." -ForegroundColor Green
        }
    } catch {
        Write-Host "[WARNING] Gagal simpan ui_settings.json: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "          Tidak apa-apa - tool standalone tetap auto-detect 9222-9225." -ForegroundColor Yellow
    }

    Write-Host ""
    Write-Host "Login Accurate sekali di Chrome tersebut (session persist di" -ForegroundColor Gray
    Write-Host "C:\ChromeDebugProfile). Setelah itu semua tool auto-attach." -ForegroundColor Gray
    Write-Host ""
    Write-Host "Jendela ini tutup otomatis dalam 5 detik..."
    Start-Sleep -Seconds 5
    exit 0
}

# ---------- FAIL: diagnosis jujur (sama seperti UI v5.5) ----------
$owner = Get-PortOwner -Port $chosen
Write-Host "[FAIL] Chrome TIDAK menjawab http://127.0.0.1:$chosen/json/version dalam 30 detik." -ForegroundColor Red
if ($owner) {
    Write-Host "       Port $chosen dipegang: $owner" -ForegroundColor Red
} else {
    Write-Host "       Tidak ada yang listen di port $chosen (Chrome gagal bind / tidak jalan)." -ForegroundColor Red
}
Write-Host "  -> Cek manual : buka http://127.0.0.1:$chosen/json/version di browser (harus muncul JSON)."
Write-Host "  -> Solusi (1) : tutup SEMUA Chrome (Task Manager -> end task chrome.exe), klik lagi shortcut."
Write-Host "  -> Solusi (2) : cek policy kantor yang bisa memblokir debugging, jalankan di CMD:"
Write-Host "                  reg query HKLM\SOFTWARE\Policies\Google\Chrome /v DevToolsRemoteDebuggingAllowed"
Write-Host "                  (nilai 0 = diblokir IT/admin - hubungi IT)"
Write-Host "  -> Solusi (3) : jalankan manual untuk lihat error Chrome:"
Write-Host "                  chrome.exe --remote-debugging-port=$chosen --user-data-dir=""C:\ChromeDebugProfile"""
Read-Host "Tekan ENTER untuk keluar"
exit 1
