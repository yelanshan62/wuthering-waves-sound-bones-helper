param(
    [string]$OkwwPath = 'D:\ok-wuthering-waves'
)

$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$python = Join-Path $OkwwPath '.venv\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw "找不到 ok-ww 的 Python：$python"
}

& $python -c "import sys; sys.path.insert(0, r'$repo'); from echo_helper.install import ensure_installed; print('已安装：' + str(ensure_installed(okww=__import__('pathlib').Path(r'$OkwwPath'))))"
