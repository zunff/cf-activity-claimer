@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set "PY=%~dp0.venv\Scripts\python.exe"

if not exist "%PY%" (
  echo ==^> 首次运行：正在创建虚拟环境并安装依赖（约一两分钟）
  where uv >nul 2>nul
  if %errorlevel%==0 (
    uv venv .venv --python 3.12
    uv pip install --python .venv -r requirements.txt
  ) else (
    where python >nul 2>nul
    if not %errorlevel%==0 (
      echo 找不到 python，请先安装 Python 3.10+ 并勾选 Add to PATH
      pause
      exit /b 1
    )
    python -m venv .venv
    "%PY%" -m pip install --upgrade pip >nul
    "%PY%" -m pip install -r requirements.txt
  )
)

echo ==^> 启动 UI，浏览器会自动打开…
"%PY%" "%~dp0ui.py" %*
pause
