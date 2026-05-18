"""
Скрипт запуска GUI приложения MicroIDE Recorder
"""
import sys
import os

# Добавляем текущую директорию в PYTHONPATH
# Эта строка делает файл запускаемым из любого места
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Подавляем Qt-предупреждения о DPI и шрифтах DirectWrite (безвредные)
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.*=false")

from microide_app.main import main

if __name__ == "__main__":
    main()
