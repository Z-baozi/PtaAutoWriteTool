@echo off
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [信息] 未检测到 .venv，正在创建虚拟环境...
    py -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python gui_app.py

pause
