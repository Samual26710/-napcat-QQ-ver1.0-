Set-Location (Split-Path -Parent $PSScriptRoot)

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3.11 -m venv .venv
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python -m venv .venv
} elseif (Test-Path (Join-Path $env:LocalAppData 'Programs\Python\Python311\python.exe')) {
    & (Join-Path $env:LocalAppData 'Programs\Python\Python311\python.exe') -m venv .venv
} elseif (Test-Path 'C:\Program Files\Python311\python.exe') {
    & 'C:\Program Files\Python311\python.exe' -m venv .venv
} else {
    Write-Error "未找到 Python。请先安装 Python 3.11，并确保 python 或 py 已加入 PATH。"
    exit 1
}

& .\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -r .\requirements.txt

if (-not (Test-Path .env) -and (Test-Path .env.example)) {
    Copy-Item .env.example .env
    Write-Host "已创建 .env，请填写模型密钥和 OneBot token。"
}
