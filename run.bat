@echo off
REM Скрипт запуска GUI приложения MicroIDE Recorder
REM Убедитесь, что виртуальное окружение создано: python -m venv .venv
REM И зависимости установлены: .venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python.exe run_gui.py
pause
