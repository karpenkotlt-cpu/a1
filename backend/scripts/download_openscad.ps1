# Загрузка портативного OpenSCAD из официального репозитория
# https://github.com/openscad/openscad/ (release pinned, без установки в систему).
# Результат: backend/vendor/openscad-<version>/openscad.com — используется backend
# (порядок поиска бинарника: APP_OPENSCAD_BIN -> backend/vendor -> PATH -> Program Files).
#
# Запуск: powershell -ExecutionPolicy Bypass -File scripts\download_openscad.ps1
# Идемпотентен: при готовой проверенной установке ничего не делает.

$ErrorActionPreference = "Stop"

# Pinned Manifold-снапшот (openscad.org/snapshots): CGAL-ядро 2021.01
# рендерит реальную деталь (60 отверстий, $fn=96) ~228 c — непригодно;
# Manifold справляется за секунды. Обновление = сменить $Version/$Url.
$Version = "2026.11.01"
$Tag = "snapshot"
$Url = "https://files.openscad.org/snapshots/OpenSCAD-$Version-x86-64.zip"
$ExpectedBytes = 0  # 0 = не проверять размер (у снапшотов он плавает)

$BackendDir = Split-Path -Parent $PSScriptRoot
$VendorRoot = Join-Path $BackendDir "vendor"
$InstallDir = Join-Path $VendorRoot "openscad-$Version"

$ConsoleExe = Join-Path $InstallDir "openscad.com"

function Test-Install([string]$exe) {
    if (-not (Test-Path -LiteralPath $exe)) { return $false }
    $out = & $exe --version 2>&1 | Out-String
    return ($out -match [regex]::Escape($Version))
}

if (Test-Install $ConsoleExe) {
    Write-Output "OK: OpenSCAD $Version уже установлен в $InstallDir"
    exit 0
}

# PowerShell 5.1: явно включаем TLS 1.2 для github.com
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$TmpDir = Join-Path ([IO.Path]::GetTempPath()) ("openscad-dl-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $TmpDir | Out-Null
try {
    $ZipPath = Join-Path $TmpDir "openscad.zip"
    Write-Output "Загрузка $Url ..."
    Invoke-WebRequest -Uri $Url -OutFile $ZipPath -UseBasicParsing

    $Size = (Get-Item -LiteralPath $ZipPath).Length
    if ($ExpectedBytes -gt 0 -and $Size -ne $ExpectedBytes) {
        throw "Размер архива $Size байт не совпал с ожидаемым $ExpectedBytes (проверьте релиз $Tag)"
    }

    $ExtractDir = Join-Path $TmpDir "extract"
    Expand-Archive -LiteralPath $ZipPath -DestinationPath $ExtractDir

    # В zip префикс-каталог может отличаться — ищем каталог с openscad.com
    $BinDir = Get-ChildItem -LiteralPath $ExtractDir -Recurse -Filter "openscad.com" |
        Select-Object -First 1
    if ($null -eq $BinDir) { throw "В архиве не найден openscad.com" }
    $SrcDir = $BinDir.DirectoryName

    if (Test-Path -LiteralPath $InstallDir) {
        Remove-Item -LiteralPath $InstallDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $VendorRoot -Force | Out-Null
    Move-Item -LiteralPath $SrcDir -Destination $InstallDir
}
finally {
    if (Test-Path -LiteralPath $TmpDir) {
        Remove-Item -LiteralPath $TmpDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

if (-not (Test-Install $ConsoleExe)) {
    throw "Проверка не прошла: $ConsoleExe --version не вернул $Version"
}
Write-Output "OK: OpenSCAD $Version установлен в $InstallDir"
