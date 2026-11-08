$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$pythonw = 'D:\ok-wuthering-waves\.venv\pythonw.exe'
$icon = Join-Path $repo 'app\assets\icon.ico'
if (-not (Test-Path -LiteralPath $pythonw)) { throw "找不到 $pythonw" }
if (-not (Test-Path -LiteralPath $icon)) { throw "找不到 $icon" }

$desktop = [Environment]::GetFolderPath('Desktop')
$lnkPath = Join-Path $desktop '声骸助手.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($lnkPath)
$shortcut.TargetPath = $pythonw
$shortcut.Arguments = "`"$repo\app\main.py`""
$shortcut.WorkingDirectory = $repo
$shortcut.IconLocation = $icon
$shortcut.Description = '鸣潮声骸助手'
$shortcut.WindowStyle = 1
$shortcut.Save()

$bytes = [System.IO.File]::ReadAllBytes($lnkPath)
$bytes[0x15] = $bytes[0x15] -bor 0x20
[System.IO.File]::WriteAllBytes($lnkPath, $bytes)
Write-Host "已创建（以管理员身份运行）：$lnkPath"
