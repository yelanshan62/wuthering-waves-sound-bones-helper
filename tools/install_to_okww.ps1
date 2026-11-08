param(
    [string]$OkwwPath = 'D:\ok-wuthering-waves'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot

if (-not (Test-Path -LiteralPath (Join-Path $OkwwPath 'main.py'))) {
    throw "找不到 ok-ww：$OkwwPath"
}

$taskFolder = Join-Path $OkwwPath 'ok_tasks'
New-Item -ItemType Directory -Force -Path $taskFolder | Out-Null

$entry = @"
import sys

_REPO = r"$repo"
if _REPO not in sys.path:
    sys.path.insert(0, _REPO)

from echo_helper.okww_task import EchoHelperTask as _EchoHelperTask


class EchoHelperTask(_EchoHelperTask):
    pass
"@

$target = Join-Path $taskFolder 'EchoHelperTask.py'
Set-Content -LiteralPath $target -Value $entry -Encoding UTF8
Write-Host "已安装：$target"
