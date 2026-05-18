from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLabel, QHeaderView, QAbstractItemView,
    QFileDialog, QMessageBox, QGroupBox, QListWidget, QListWidgetItem,
    QDialog, QLineEdit, QFormLayout, QDialogButtonBox, QTextEdit, QApplication,
    QTextBrowser, QStyledItemDelegate, QComboBox
)
from PySide6.QtCore import QThread, Signal, Qt, QTimer, QSettings
from PySide6.QtGui import QShortcut, QKeySequence, QColor, QKeyEvent, QFont, QTextCursor
import keyboard as kb_global
from microide_app.service import RecorderService
import re
import os
import sys
import copy
import subprocess
import traceback
import tempfile


_RF_KEYWORDS_RECORDER = [
    # Recorder-generated - always at top
    "Check Active",
    "Check Focus",
    "Check Selected",
    "Click Element",
    "Keyboard Input",
    "Mouse Click",
    "Mouse Scroll",
]

_RF_KEYWORDS_PROJECT = sorted([
    "Change Configuration",
    "Change Menu Section",
    "Check Configuration",
    "Check If Not Active",
    "Check Name Of Element",
    "Check Part Name Of Element",
    "Check Selected Value",
    "Check Selected Value In Group",
    "Check Table On",
    "Click",
    "Click Down ScrollBar",
    "Click Tab",
    "Click Up ScrollBar",
    "Click Without Common Check",
    "Common Checks",
    "Deinitialize Suite",
    "Deinitialize Test",
    "Do Screenshot",
    "Do Screenshot Of Element",
    "Drop-Down List Set",
    "Find Message Window",
    "Get Dimension And Check",
    "Get Focus And Check",
    "Get Value",
    "Get Value And Check",
    "Get Value With Dimension",
    "Get Value With Dimension And Check",
    "Initialize Suite",
    "Initialize Test",
    "Is Element Active",
    "Is Element Selected",
    "Is Element Visible",
    "Is Value In Range",
    "Log",
    "Run Keyword And Continue On Failure",
    "Run Keyword And Ignore Error",
    "Run Keyword If Test Passed",
    "Select ComboBox",
    "Send Command",
    "Set Focus",
    "Set Mode Preset",
    "Set Mode Preset Configuration",
    "Set Mode Preset P",
    "Set Selected Value In Group",
    "Set Suite Variable",
    "Set Value",
    "Set Value With Dimension",
    "Set Variable",
    "Set Variant Combobox",
    "Should Be Equal",
    "Should Be Equal As Strings",
    "Should Not Match Regexp",
    "Sleep",
    "Wait Correct Value With Dimension",
    "Wait For Message",
    "Wait Until Keyword Succeeds",
])

_RF_KEYWORDS = _RF_KEYWORDS_RECORDER + _RF_KEYWORDS_PROJECT

_PLACEHOLDER_CMD = "Keyword"
_PLACEHOLDER_COLOR = QColor("#aaaaaa")


# Колонка Command с выпадающим списком для ввода киворда
class _CommandDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if index.data() == _PLACEHOLDER_CMD:
            option.text = ""   # скрываем текст, чтобы super().paint не рисовал его

    def paint(self, painter, option, index):
        super().paint(painter, option, index)   # рисуем фон 
        if index.data() == _PLACEHOLDER_CMD:
            # рисуем placeholder серым поверх пустой ячейки
            painter.save()
            painter.setPen(_PLACEHOLDER_COLOR)
            rect = option.rect.adjusted(6, 0, -4, 0)
            painter.drawText(rect,
                             Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                             _PLACEHOLDER_CMD)
            painter.restore()

    def createEditor(self, parent, option, index):
        # Редактируемый комбобокс со списком всех кивордов
        combo = QComboBox(parent)
        combo.setEditable(True)
        combo.addItems(_RF_KEYWORDS)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        return combo

    def setEditorData(self, editor, index):
        # Заполняем редактор текущим значением ячейки
        val = index.data() or ""
        if val == _PLACEHOLDER_CMD:
            editor.setEditText("")
            editor.lineEdit().setPlaceholderText(_PLACEHOLDER_CMD)
        else:
            i = editor.findText(val)
            if i >= 0:
                editor.setCurrentIndex(i)
            else:
                editor.setEditText(val)  # значение не из списка - вводим как текст

    def setModelData(self, editor, model, index):
        # Сохраняем выбранное значение (пустая строка -> возвращаем placeholder)
        text = editor.currentText().strip()
        model.setData(index, text if text else _PLACEHOLDER_CMD)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


# Переводы
_TR = {
    "en": {
        # Sidebar groups
        "g_suite": "Suite", "g_tests": "Tests",
        "g_recording": "Recording", "g_run": "Run Tests",
        # Suite buttons
        "btn_new": "New", "btn_open": "Open", "btn_save": "Save",
        "tip_new": "New scenario",
        "tip_open": "Open .robot file (Ctrl+O)",
        "tip_save": "Save file (Ctrl+S)",
        # Test buttons
        "tip_add_test": "Add new test",
        "tip_rename_test": "Rename test",
        "tip_delete_test": "Delete test",
        # Recording
        "btn_record": "⬤ Record", "btn_stop": "■ Stop",
        "tip_record": "Start recording (F6)",
        "tip_stop": "Stop recording (F7)",
        "lbl_paused": "Paused",
        # Run
        "btn_run": "▶ Run All", "tip_run": "Run all tests (F5)",
        "btn_run_one": "▶ Run Test", "tip_run_one": "Run selected test only",
        # Hotkeys button
        "btn_hotkeys": "Hotkeys", "tip_hotkeys": "Show hotkeys",
        # Step buttons
        "tip_add_step": "Add new step (Ctrl+N)",
        "tip_dup_step": "Duplicate selected step (Ctrl+D)",
        "tip_up": "Move step up (Alt+Up)",
        "tip_down": "Move step down (Alt+Down)",
        "tip_del_step": "Delete selected step (Del)",
        "tip_clear": "Delete all steps in current test",
        # Table headers
        "col_num": "#", "col_cmd": "Command",
        "col_tgt": "Target", "col_val": "Value",
        # Labels / status
        "no_test": "No test selected",
        "no_suite": "No suite loaded",
        "test_label": "Test: {}",
        "suite_status": "Suite: {} | Tests: {}",
        "st_recording": "⬤ Recording... (ESC to pause, ESC×2 to stop)",
        "st_paused": "Paused",
        "st_stopping": "Stopping...",
        "st_saved": "Recording saved to {}",
        # Messages
        "msg_no_suite_t": "No Suite",
        "msg_no_suite": "Create a suite first with 'New' button.",
        "msg_suite_ok_t": "Suite Created",
        "msg_suite_ok": "Suite '{}' created.\nFile: {}\nNow add tests with '+' button.",
        "msg_del_test_t": "Delete Test",
        "msg_del_test": "Delete test '{}'?",
        "msg_del_step_t": "Delete Step",
        "msg_del_step_1": "Delete this row?",
        "msg_del_step_n": "Delete these rows?",
        "msg_clear_t": "Clear Test",
        "msg_clear": "Delete all steps in '{}'?",
        "msg_saved_t": "Saved",
        "msg_saved": "Saved to:\n{}",
        "msg_no_file_t": "No File",
        "msg_no_file": "Please choose where to save the suite file.",
        "msg_no_resource_t": "No Resource File",
        "msg_no_resource": "Setup/Teardown keywords (e.g. 'Initialize Suite') are set, but no Resource file is specified.\n\nThese keywords must be defined somewhere - usually in a resource file like common.robot.\n\nWithout it, Robot Framework will fail at runtime.\n\nContinue anyway?",
        "btn_continue": "Continue",
        "btn_ok": "OK",
        "btn_cancel": "Cancel",
        "btn_yes": "Yes",
        "btn_no": "No",
        "msg_no_tests_t": "No Tests",
        "msg_no_tests": "Add at least one test to run.",
        "msg_err_t": "Error",
        "msg_load_err": "Failed to load file:\n{}",
        # Dialogs
        "dlg_new_suite": "New Robot Suite",
        "dlg_workdir": "Working Dir:",
        "dlg_workdir_ph": "Project working directory...",
        "dlg_workdir_tip": "Choose folder",
        "dlg_suite_lbl": "Suite:",
        "dlg_suite_ph": "Name and location of .robot file...",
        "dlg_suite_tip": "Save as...",
        "dlg_resource": "Resource:",
        "dlg_resource_ph": "Resource file (optional)...",
        "dlg_resource_tip": "Choose resource file",
        "dlg_setup": "Suite Setup:",
        "dlg_teardown": "Suite Teardown:",
        "dlg_test_setup": "Test Setup:",
        "dlg_test_teardown": "Test Teardown:",
        "btn_settings": "⚙ Settings",
        "tip_settings": "Edit suite settings",
        "dlg_run_settings": "Run Settings",
        "dlg_python_tip": "Choose python.exe from venv",
        "dlg_python": "Python:",
        "dlg_variables": "Variables (-v):",
        "dlg_exclude": "Exclude tags (-e):",
        "dlg_outdir": "Output Dir:",
        "dlg_outdir_ph": "Default – suite file folder...",
        "dlg_outdir_tip": "Choose folder for test logs",
        "dlg_new_test": "Add New Test",
        "dlg_rename_test": "Rename Test",
        "dlg_test_name": "Test Name:",
        "dlg_test_name_ph": "e.g. Change RBW Value",
        "dlg_tags": "Tags:",
        "dlg_tags_ph": "e.g. daily, smoke (comma separated)",
        # Hotkeys HTML content
        "hk_title": "Hotkeys",
        "hk_rec": "Recording & Run",
        "hk_run_t": "Run tests",
        "hk_start_t": "Start recording",
        "hk_stop_t": "Stop recording",
        "hk_pause_t": "Pause",
        "hk_resume_t": "Resume",
        "hk_stop2_t": "Stop",
        "hk_during": "During Recording",
        "hk_check": "Check last value",
        "hk_active": "Is Element Active",
        "hk_focus": "Get Focus And Check",
        "hk_sel": "Is Element Selected",
        "hk_steps": "Steps Editing",
        "hk_add_s": "Add step",
        "hk_dup_s": "Duplicate step",
        "hk_up_s": "Move up",
        "hk_down_s": "Move down",
        "hk_del_s": "Delete step",
        "hk_copy_s": "Copy steps",
        "hk_paste_s": "Paste steps",
        "hk_undo_s": "Undo",
        "hk_redo_s": "Redo",
        "hk_file": "File",
        "hk_save_s": "Save",
        "hk_open_s": "Open",
        # Run dialog
        "run_title": "Running: {}",
        "run_running": "Running tests...",
        "run_test_n": "Running test {} / {}...",
        "run_failed": "✖ Some tests failed",
        "run_passed": "✔ All tests passed!",
        "run_close": "Close",
        "run_open_report": "Open Report",
        "run_not_found": "Robot Framework is not installed or not in PATH.",
        "run_err_notfound": "✖ Error: robot not found",
        # File dialogs
        "fd_open": "Open Robot Suite",
        "fd_save": "Save Robot Suite",
        "fd_preview": "Preview: {}",
        # Variable button
        "tip_var_btn": "Save cell value as variable (${VAR})",
        "dlg_var_title": "Add as Variable",
        "dlg_var_label": "Variable name:",
        "dlg_var_ph": "e.g. MY_VAR",
        # Unsaved changes
        "msg_unsaved_t": "Unsaved Changes",
        "msg_unsaved": "There are unsaved changes.\nSave before closing?",
        "btn_save_close": "Save",
        "btn_discard_close": "Discard",
        "btn_cancel_close": "Cancel",
    },
    "ru": {
        # Sidebar groups
        "g_suite": "Набор", "g_tests": "Тесты",
        "g_recording": "Запись тестов", "g_run": "Запуск тестов",
        # Suite buttons
        "btn_new": "Создать", "btn_open": "Открыть", "btn_save": "Сохранить",
        "tip_new": "Новый сценарий",
        "tip_open": "Открыть .robot файл (Ctrl+O)",
        "tip_save": "Сохранить файл (Ctrl+S)",
        # Test buttons
        "tip_add_test": "Добавить тест",
        "tip_rename_test": "Переименовать тест",
        "tip_delete_test": "Удалить тест",
        # Recording
        "btn_record": "⬤ Запись", "btn_stop": "■ Стоп",
        "tip_record": "Начать запись (F6)",
        "tip_stop": "Остановить запись (F7)",
        "lbl_paused": "Пауза",
        # Run
        "btn_run": "▶ Все тесты", "tip_run": "Запустить все тесты (F5)",
        "btn_run_one": "▶ Тест", "tip_run_one": "Запустить выбранный тест",
        # Hotkeys button
        "btn_hotkeys": "Горячие клавиши",
        "tip_hotkeys": "Горячие клавиши",
        # Step buttons
        "tip_add_step": "Добавить новый шаг (Ctrl+N)",
        "tip_dup_step": "Дублировать выбранный шаг (Ctrl+D)",
        "tip_up": "Переместить шаг вверх (Alt+Up)",
        "tip_down": "Переместить шаг вниз (Alt+Down)",
        "tip_del_step": "Удалить выбранный шаг (Del)",
        "tip_clear": "Удалить все шаги текущего теста",
        # Table headers
        "col_num": "#", "col_cmd": "Команда",
        "col_tgt": "Элемент", "col_val": "Значение",
        # Labels / status
        "no_test": "Тест не выбран",
        "no_suite": "Набор не загружен",
        "test_label": "Тест: {}",
        "suite_status": "Набор: {} | Тестов: {}",
        "st_recording": "𒊹 Запись... (ESC – пауза, ESC×2 – стоп)",
        "st_paused": "Пауза",
        "st_stopping": "Остановка...",
        "st_saved": "Запись сохранена: {}",
        # Messages
        "msg_no_suite_t": "Нет набора",
        "msg_no_suite": "Сначала создайте набор кнопкой «Новый».",
        "msg_suite_ok_t": "Набор создан",
        "msg_suite_ok": "Набор «{}» создан.\nФайл: {}\nДобавьте тесты кнопкой «+».",
        "msg_del_test_t": "Удалить тест",
        "msg_del_test": "Удалить тест «{}»?",
        "msg_del_step_t": "Удалить шаг",
        "msg_del_step_1": "Удалить эту строку?",
        "msg_del_step_n": "Удалить эти строки?",
        "msg_clear_t": "Очистить тест",
        "msg_clear": "Удалить все шаги в «{}»?",
        "msg_saved_t": "Сохранено",
        "msg_saved": "Сохранено:\n{}",
        "msg_no_file_t": "Не выбран файл",
        "msg_no_file": "Укажите, куда сохранить .robot файл.",
        "msg_no_resource_t": "Не указан Resource файл",
        "msg_no_resource": "Заданы ключевые слова Setup/Teardown (например, 'Initialize Suite'), но не указан Resource файл.\n\nЭти ключевые слова должны быть определены где-то - обычно в resource файле, например common.robot.\n\nБез него Robot Framework завершится ошибкой при запуске.\n\nПродолжить всё равно?",
        "btn_continue": "Продолжить",
        "btn_ok": "ОК",
        "btn_cancel": "Отмена",
        "btn_yes": "Да",
        "btn_no": "Нет",
        "msg_no_tests_t": "Нет тестов",
        "msg_no_tests": "Добавьте хотя бы один тест.",
        "msg_err_t": "Ошибка",
        "msg_load_err": "Не удалось загрузить файл:\n{}",
        # Dialogs
        "dlg_new_suite": "Новая Robot Suite",
        "dlg_workdir": "Рабочая папка:",
        "dlg_workdir_ph": "Рабочая папка проекта...",
        "dlg_workdir_tip": "Выбрать папку",
        "dlg_suite_lbl": "Suite:",
        "dlg_suite_ph": "Имя и место сохранения .robot файла...",
        "dlg_suite_tip": "Сохранить как...",
        "dlg_resource": "Resource:",
        "dlg_resource_ph": "Resource файл (необязательно)...",
        "dlg_resource_tip": "Выбрать resource файл",
        "dlg_setup": "Suite Setup:",
        "dlg_teardown": "Suite Teardown:",
        "dlg_test_setup": "Test Setup:",
        "dlg_test_teardown": "Test Teardown:",
        "btn_settings": "⚙ Настройки",
        "tip_settings": "Редактировать настройки набора",
        "dlg_run_settings": "Настройки запуска",
        "dlg_python_tip": "Выбрать python.exe из нужного venv",
        "dlg_python": "Python:",
        "dlg_variables": "Переменные (-v):",
        "dlg_exclude": "Исключить теги (-e):",
        "dlg_outdir": "Папка вывода:",
        "dlg_outdir_ph": "По умолчанию – папка suite файла...",
        "dlg_outdir_tip": "Выбрать папку для логов теста",
        "dlg_new_test": "Добавить тест",
        "dlg_rename_test": "Переименовать тест",
        "dlg_test_name": "Название:",
        "dlg_test_name_ph": "прим. Установить значение RBW",
        "dlg_tags": "Теги:",
        "dlg_tags_ph": "прим. daily, smoke (через запятую)",
        # Hotkeys HTML content
        "hk_title": "Горячие клавиши",
        "hk_rec": "Запись и запуск",
        "hk_run_t": "Запустить тесты",
        "hk_start_t": "Начать запись",
        "hk_stop_t": "Остановить запись",
        "hk_pause_t": "Пауза",
        "hk_resume_t": "Продолжить",
        "hk_stop2_t": "Стоп",
        "hk_during": "Во время записи",
        "hk_check": "Проверить последнее значение",
        "hk_active": "Is Element Active",
        "hk_focus": "Get Focus And Check",
        "hk_sel": "Is Element Selected",
        "hk_steps": "Редактирование шагов",
        "hk_add_s": "Добавить шаг",
        "hk_dup_s": "Дублировать шаг",
        "hk_up_s": "Переместить вверх",
        "hk_down_s": "Переместить вниз",
        "hk_del_s": "Удалить шаг",
        "hk_copy_s": "Копировать шаги",
        "hk_paste_s": "Вставить шаги",
        "hk_undo_s": "Отмена",
        "hk_redo_s": "Повтор",
        "hk_file": "Файл",
        "hk_save_s": "Сохранить",
        "hk_open_s": "Открыть",
        # Run dialog
        "run_title": "Запуск: {}",
        "run_running": "Запуск тестов...",
        "run_test_n": "Тест {} из {}...",
        "run_failed": "✖ Некоторые тесты упали",
        "run_passed": "✔ Все тесты прошли!",
        "run_close": "Закрыть",
        "run_open_report": "Открыть отчёт",
        "run_not_found": "Robot Framework не установлен или не в PATH.",
        "run_err_notfound": "✖ Ошибка: robot не найден",
        # File dialogs
        "fd_open": "Открыть Robot Suite",
        "fd_save": "Сохранить Robot Suite",
        "fd_preview": "Предпросмотр: {}",
        # Variable button
        "tip_var_btn": "Сохранить значение ячейки как переменную (${VAR})",
        "dlg_var_title": "Добавить как переменную",
        "dlg_var_label": "Имя переменной:",
        "dlg_var_ph": "прим. MY_VAR",
        # Unsaved changes
        "msg_unsaved_t": "Несохранённые изменения",
        "msg_unsaved": "Есть несохранённые изменения.\nСохранить перед закрытием?",
        "btn_save_close": "Сохранить",
        "btn_discard_close": "Не сохранять",
        "btn_cancel_close": "Отмена",
    },
}


def _make_t(lang: str):
    """Возвращает функцию перевода для указанного языка."""
    d = _TR.get(lang, _TR["en"])
    return lambda key, *args: d[key].format(*args) if args else d[key]


# Диалоговое окно для создания нового .robot файла
class NewSuiteDialog(QDialog):
    def __init__(self, parent=None, lang="en", initial=None):
        super().__init__(parent)
        t = _make_t(lang)
        self.setWindowTitle(t("dlg_new_suite") if not initial else (
            "Edit Suite Settings" if lang == "en" else "Настройки Suite"))
        self.setMinimumWidth(480)
        self._edit_mode = initial is not None  # True = редактирование, False = создание

        layout = QVBoxLayout(self)
        form = QFormLayout()

        workdir_row = QHBoxLayout()
        workdir_row.setSpacing(4)
        self.workdir_edit = QLineEdit()
        self.workdir_edit.setPlaceholderText(t("dlg_workdir_ph"))
        workdir_row.addWidget(self.workdir_edit)
        btn_wd = QPushButton("...")
        btn_wd.setFixedWidth(36)
        btn_wd.setToolTip(t("dlg_workdir_tip"))
        btn_wd.clicked.connect(self._browse_workdir)
        workdir_row.addWidget(btn_wd)
        form.addRow(t("dlg_workdir"), workdir_row)

        suite_row = QHBoxLayout()
        suite_row.setSpacing(4)
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText(t("dlg_suite_ph"))
        suite_row.addWidget(self.file_path_edit)
        btn_suite = QPushButton("...")
        btn_suite.setFixedWidth(36)
        btn_suite.setToolTip(t("dlg_suite_tip"))
        btn_suite.clicked.connect(self._browse_suite_file)
        suite_row.addWidget(btn_suite)
        form.addRow(t("dlg_suite_lbl"), suite_row)

        resource_row = QHBoxLayout()
        resource_row.setSpacing(4)
        self.resource_edit = QLineEdit()
        self.resource_edit.setPlaceholderText(t("dlg_resource_ph"))
        resource_row.addWidget(self.resource_edit)
        btn_res = QPushButton("...")
        btn_res.setFixedWidth(36)
        btn_res.setToolTip(t("dlg_resource_tip"))
        btn_res.clicked.connect(self._browse_resource)
        resource_row.addWidget(btn_res)
        form.addRow(t("dlg_resource"), resource_row)

        self.setup_edit = QLineEdit()
        self.setup_edit.setText("Initialize Suite")
        form.addRow(t("dlg_setup"), self.setup_edit)

        self.teardown_edit = QLineEdit()
        self.teardown_edit.setText("Deinitialize Suite")
        form.addRow(t("dlg_teardown"), self.teardown_edit)

        self.test_setup_edit = QLineEdit()
        self.test_setup_edit.setText("Initialize Test")
        form.addRow(t("dlg_test_setup"), self.test_setup_edit)

        self.test_teardown_edit = QLineEdit()
        self.test_teardown_edit.setText("Deinitialize Test")
        form.addRow(t("dlg_test_teardown"), self.test_teardown_edit)

        layout.addLayout(form)

        run_group = QGroupBox(t("dlg_run_settings"))
        run_layout = QFormLayout(run_group)

        python_row = QHBoxLayout()
        python_row.setSpacing(4)
        self.python_exe_edit = QLineEdit()
        if getattr(sys, "frozen", False):
            import shutil as _shutil
            _default_py = _shutil.which("python") or _shutil.which("python3") or ""
        else:
            _default_py = sys.executable
        self.python_exe_edit.setText(_default_py)
        python_row.addWidget(self.python_exe_edit)
        btn_py = QPushButton("...")
        btn_py.setFixedWidth(36)
        btn_py.setToolTip(t("dlg_python_tip"))
        btn_py.clicked.connect(self._browse_python_exe)
        python_row.addWidget(btn_py)
        run_layout.addRow(t("dlg_python"), python_row)

        self.variables_edit = QLineEdit()
        self.variables_edit.setText("LANGUAGE:ENG, HW:SIMULATION")
        run_layout.addRow(t("dlg_variables"), self.variables_edit)

        self.exclude_edit = QLineEdit()
        self.exclude_edit.setText("manual")
        run_layout.addRow(t("dlg_exclude"), self.exclude_edit)

        output_dir_row = QHBoxLayout()
        output_dir_row.setSpacing(4)
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText(t("dlg_outdir_ph"))
        output_dir_row.addWidget(self.output_dir_edit)
        btn_out = QPushButton("...")
        btn_out.setFixedWidth(36)
        btn_out.setToolTip(t("dlg_outdir_tip"))
        btn_out.clicked.connect(self._browse_output_dir)
        output_dir_row.addWidget(btn_out)
        run_layout.addRow(t("dlg_outdir"), output_dir_row)

        layout.addWidget(run_group)

        buttons = QDialogButtonBox()
        btn_ok = buttons.addButton(t("btn_ok"), QDialogButtonBox.ButtonRole.AcceptRole)
        btn_ok.setDefault(True)
        buttons.addButton(t("btn_cancel"), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._t = t

        # В режиме редактирования заполняем поля текущими значениями
        if initial:
            self.file_path_edit.setText(initial.get("file_path", ""))
            self.file_path_edit.setReadOnly(True)  # путь к файлу не меняем
            self.workdir_edit.setText(initial.get("workdir", ""))
            self.resource_edit.setText(initial.get("resource", ""))
            self.setup_edit.setText(initial.get("suite_setup", ""))
            self.teardown_edit.setText(initial.get("suite_teardown", ""))
            self.test_setup_edit.setText(initial.get("test_setup", ""))
            self.test_teardown_edit.setText(initial.get("test_teardown", ""))
            self.python_exe_edit.setText(initial.get("python_exe", _default_py))
            self.variables_edit.setText(initial.get("variables", ""))
            self.exclude_edit.setText(initial.get("exclude_tags", ""))
            self.output_dir_edit.setText(initial.get("output_dir", ""))

    # Диалоговое окно для выбора python.exe из нужного venv.
    def _browse_python_exe(self):
        start_dir = os.path.dirname(self.python_exe_edit.text().strip()) or os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Python Executable",
            start_dir,
            "Python (python.exe python3.exe);;All files (*)"
        )
        if path:
            self.python_exe_edit.setText(path)

    # Диалоговое окно для  выбора папки для сохранения логов теста
    def _browse_output_dir(self):
        start_dir = self.output_dir_edit.text().strip() or self.workdir_edit.text().strip() or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(
            self, "Выбрать папку для логов теста", start_dir
        )
        if path:
            self.output_dir_edit.setText(path)

    # Диалоговое окно для выбора места сохранения suite файла
    def _browse_suite_file(self):
        start_dir = self.workdir_edit.text().strip() or os.path.expanduser("~")
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить suite как...",
            start_dir,
            "Robot files (*.robot)"
        )
        if path:
            if not path.lower().endswith(".robot"):
                path += ".robot"
            self.file_path_edit.setText(path)
            if not self.workdir_edit.text().strip():
                self.workdir_edit.setText(os.path.dirname(path))

    # Диалоговое окно для выбора рабочей директории проекта
    def _browse_workdir(self):
        start_dir = self.workdir_edit.text().strip() or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(
            self, "Select Project Root (Working Directory)",
            start_dir
        )
        if not path:
            return
        self.workdir_edit.setText(path)

        # Автозаполнение Resource если поле пустое
        if not self.resource_edit.text().strip():
            candidate = os.path.join(path, "lib", "common.robot")
            if os.path.isfile(candidate):
                self.resource_edit.setText("lib/common.robot")

        # Автозаполнение Python: если в workdir есть venv - всегда берём его,
        # иначе оставляем текущее значение поля как есть
        candidates_py = [
            os.path.join(path, ".venv", "Scripts", "python.exe"),
            os.path.join(path, "venv",  "Scripts", "python.exe"),
            os.path.join(path, ".venv", "bin",     "python"),
            os.path.join(path, "venv",  "bin",     "python"),
        ]
        venv_py = next((p for p in candidates_py if os.path.isfile(p)), None)
        if venv_py:
            self.python_exe_edit.setText(venv_py)

    # Диалоговое окно для выбора resource файла
    def _browse_resource(self):
        start_dir = self.workdir_edit.text().strip() or os.path.expanduser("~")
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Resource File",
            start_dir,
            "Robot files (*.robot)"
        )
        if path:
            # Если resource внутри workdir - сохраняем относительный путь
            workdir = self.workdir_edit.text().strip()
            if workdir:
                try:
                    rel = os.path.relpath(path, workdir).replace("\\", "/")
                    self.resource_edit.setText(rel)
                    return
                except ValueError:
                    pass
            self.resource_edit.setText(path.replace("\\", "/"))

    def _on_accept(self):
        if not self.file_path_edit.text().strip():
            QMessageBox.warning(self, self._t("msg_no_file_t"), self._t("msg_no_file"))
            return
        has_setup = any([
            self.setup_edit.text().strip(),
            self.teardown_edit.text().strip(),
            self.test_setup_edit.text().strip(),
            self.test_teardown_edit.text().strip(),
        ])
        if has_setup and not self.resource_edit.text().strip():
            mb = QMessageBox(self)
            mb.setIcon(QMessageBox.Icon.Warning)
            mb.setWindowTitle(self._t("msg_no_resource_t"))
            mb.setText(self._t("msg_no_resource"))
            btn_yes = mb.addButton(self._t("btn_continue"), QMessageBox.ButtonRole.AcceptRole)
            mb.addButton(self._t("btn_cancel"), QMessageBox.ButtonRole.RejectRole)
            mb.setDefaultButton(btn_yes)
            mb.exec()
            if mb.clickedButton() is not btn_yes:
                return
        self.accept()

    # Сборка данных из всех полей в словарь
    def get_data(self):
        file_path = self.file_path_edit.text().strip()
        name = os.path.splitext(os.path.basename(file_path))[0] if file_path else "new_suite"
        workdir = self.workdir_edit.text().strip() or os.path.dirname(file_path)
        return {
            "file_path": file_path,
            "name": name,
            "resource": self.resource_edit.text().strip(),
            "suite_setup": self.setup_edit.text().strip(),
            "suite_teardown": self.teardown_edit.text().strip(),
            "test_setup": self.test_setup_edit.text().strip(),
            "test_teardown": self.test_teardown_edit.text().strip(),
            "workdir": workdir,
            "python_exe": self.python_exe_edit.text().strip() or sys.executable,
            "variables": self.variables_edit.text().strip(),
            "exclude_tags": self.exclude_edit.text().strip(),
            "output_dir": self.output_dir_edit.text().strip(),
        }


# Диалоговое окно для добавления нового теста
class NewTestDialog(QDialog):
    def __init__(self, parent=None, lang="en"):
        super().__init__(parent)
        t = _make_t(lang)
        self.setWindowTitle(t("dlg_new_test"))
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(t("dlg_test_name_ph"))
        form.addRow(t("dlg_test_name"), self.name_edit)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText(t("dlg_tags_ph"))
        form.addRow(t("dlg_tags"), self.tags_edit)

        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_data(self):
        tags = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        return {
            "name": self.name_edit.text().strip() or "New Test",
            "tags": tags,
        }


# Фоновый QT-поток, чтобы GUI не зависал
class RecorderThread(QThread):
    # Сигнал с результатом записи (словарь) или None при ошибке
    finished_with_result = Signal(object)

    def __init__(self, service: RecorderService):
        super().__init__()
        self.service = service

    def run(self):
        result = None
        try:
            result = self.service.run_blocking()  # Блокировка потока до нажатия Stop
        except Exception:
            traceback.print_exc()  # Печать ошибки
        finally: # Сигнал дойдёт даже в случае ошибки
            self.finished_with_result.emit(result)  # Разблокировка GUI для активации кнопок


class MainWindow(QMainWindow):
    keyword_signal = Signal(str)       # keyword из потока записи -> в GUI
    pause_signal   = Signal(bool)      # пауза/возобновление записи -> в GUI
    global_start_signal = Signal()     # глобальный F6
    global_stop_signal  = Signal()     # глобальный F7

    def __init__(self):
        super().__init__()
        self.setWindowTitle("microide")
        self.resize(1100, 700)

        self._lang = "en"   # текущий язык
        self._recording = False  # флаг активной записи

        self.service = RecorderService()
        self.suite_data = None
        self.current_test_index = -1
        self.thread = None

        self._undo_stack = []   # стек отмены: список (test_idx, deepcopy steps)
        self._redo_stack = []   # стек повтора
        self._step_clipboard = []  # буфер копирования шагов
        self._modified = False  # True после изменений, False после явного сохранения

        self._apply_styles()

        # Корневой виджет - горизонтальная компоновка: левая панель + правая
        root = QWidget()
        main_layout = QHBoxLayout(root)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # Левая панель фиксированной ширины - все элементы управления
        left_sidebar = QWidget()
        left_sidebar.setFixedWidth(260)
        left_layout = QVBoxLayout(left_sidebar)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # Группа Suite - кнопки New/Open/Save
        self._suite_group = QGroupBox("Suite")
        suite_group = self._suite_group
        suite_layout = QVBoxLayout(suite_group)
        suite_layout.setSpacing(5)

        self.btn_new = QPushButton("New")
        self.btn_new.setToolTip("New scenario")
        self.btn_new.clicked.connect(self.on_new_suite)
        suite_layout.addWidget(self.btn_new)

        suite_open_save = QHBoxLayout()
        self.btn_open = QPushButton("Open")
        self.btn_open.setToolTip("Open .robot file (Ctrl+O)")
        self.btn_open.clicked.connect(self.on_open)
        suite_open_save.addWidget(self.btn_open)

        self.btn_save = QPushButton("Save")
        self.btn_save.setToolTip("Save file (Ctrl+S)")
        self.btn_save.clicked.connect(self.on_save)
        suite_open_save.addWidget(self.btn_save)

        suite_layout.addLayout(suite_open_save)

        self.btn_suite_settings = QPushButton("⚙ Settings")
        self.btn_suite_settings.setToolTip("Edit suite settings")
        self.btn_suite_settings.clicked.connect(self.on_edit_suite_settings)
        suite_layout.addWidget(self.btn_suite_settings)

        left_layout.addWidget(suite_group)

        # Группа Tests - список тестов + кнопки добавить/переименовать/удалить
        self._tests_group = QGroupBox("Tests")
        tests_group = self._tests_group
        tests_layout = QVBoxLayout(tests_group)
        tests_layout.setSpacing(5)

        self.tests_list = QListWidget()
        self.tests_list.currentRowChanged.connect(self._on_test_selected)
        tests_layout.addWidget(self.tests_list)

        test_btns = QHBoxLayout()
        self.btn_add_test = QPushButton("+")
        self.btn_add_test.setToolTip("Add new test")
        self.btn_add_test.setFixedHeight(28)
        self.btn_add_test.clicked.connect(self._on_add_test)
        test_btns.addWidget(self.btn_add_test)

        self.btn_rename_test = QPushButton("✎")
        self.btn_rename_test.setObjectName("renameTestBtn")
        self.btn_rename_test.setToolTip("Rename test")
        self.btn_rename_test.setFixedHeight(28)
        self.btn_rename_test.clicked.connect(self._on_rename_test)
        test_btns.addWidget(self.btn_rename_test)

        self.btn_delete_test = QPushButton("−")
        self.btn_delete_test.setToolTip("Delete test")
        self.btn_delete_test.setFixedHeight(28)
        self.btn_delete_test.clicked.connect(self._on_delete_test)
        test_btns.addWidget(self.btn_delete_test)

        tests_layout.addLayout(test_btns)
        left_layout.addWidget(tests_group, 1)  # растягивается по высоте

        # Группа Recording - запуск и остановка записи
        self._rec_group = QGroupBox("Recording")
        rec_group = self._rec_group
        rec_layout = QVBoxLayout(rec_group)

        rec_btns = QHBoxLayout()
        self.btn_start = QPushButton("𒊹 Record")
        self.btn_start.setObjectName("recordBtn")
        self.btn_start.setToolTip("Start recording (F6)")
        self.btn_start.clicked.connect(self.on_start)
        rec_btns.addWidget(self.btn_start)

        self.btn_stop = QPushButton("■ Stop")
        self.btn_stop.setObjectName("stopBtn")
        self.btn_stop.setToolTip("Stop recording (F7)")
        self.btn_stop.setEnabled(False)  # активна только во время записи
        self.btn_stop.clicked.connect(self.on_stop)
        rec_btns.addWidget(self.btn_stop)

        rec_layout.addLayout(rec_btns)

        self.lbl_pause = QLabel("Paused")
        self.lbl_pause.setAlignment(Qt.AlignCenter)
        self.lbl_pause.setStyleSheet(
            "background-color: #fff3cd; color: #856404; font-weight: bold;"
            " border: 1px solid #ffc107; border-radius: 4px; padding: 3px 6px;"
        )
        self.lbl_pause.setVisible(False)
        rec_layout.addWidget(self.lbl_pause)

        left_layout.addWidget(rec_group)

        # Группа Run - запуск тестов через Robot Framework
        self._run_group = QGroupBox("Run Tests")
        run_group = self._run_group
        run_layout = QVBoxLayout(run_group)
        run_layout.setContentsMargins(10, 2, 10, 6)

        self.btn_run = QPushButton("▷ Run All")
        self.btn_run.setObjectName("runBtn")
        self.btn_run.setToolTip("Run all tests (F5)")
        self.btn_run.clicked.connect(self.on_run_tests)
        run_layout.addWidget(self.btn_run)

        left_layout.addWidget(run_group)

        # Кнопка справки по горячим клавишам
        self.btn_hotkeys = QPushButton("Hotkeys")
        self.btn_hotkeys.setToolTip("Show hotkeys")
        self.btn_hotkeys.clicked.connect(self.on_hotkeys)
        left_layout.addWidget(self.btn_hotkeys)

        main_layout.addWidget(left_sidebar)

        # Правая панель - таблица шагов текущего теста
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(5)

        # Заголовок: название теста + кнопки редактирования шагов
        header = QHBoxLayout()

        self.current_test_label = QLabel("No test selected")
        self.current_test_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        header.addWidget(self.current_test_label)

        header.addStretch()

        # Кнопки управления шагами (добавить, дублировать, вверх, вниз, удалить)
        self.btn_add_step = QPushButton("+")
        self.btn_add_step.setObjectName("iconBtn")
        self.btn_add_step.setToolTip("Add step (Ctrl+N)")
        self.btn_add_step.clicked.connect(self.on_add)
        header.addWidget(self.btn_add_step)

        self.btn_dup_step = QPushButton("⧉")
        self.btn_dup_step.setObjectName("iconBtn")
        self.btn_dup_step.setToolTip("Duplicate (Ctrl+D)")
        self.btn_dup_step.clicked.connect(self.on_duplicate)
        header.addWidget(self.btn_dup_step)

        self.btn_var = QPushButton("${}")
        self.btn_var.setObjectName("iconBtn")
        self.btn_var.setToolTip("Add value as variable")
        self.btn_var.clicked.connect(self._promote_value_to_variable)
        header.addWidget(self.btn_var)

        self.btn_up = QPushButton("▲")
        self.btn_up.setObjectName("iconBtn")
        self.btn_up.setToolTip("Move up (Alt+Up)")
        self.btn_up.clicked.connect(self.on_move_up)
        header.addWidget(self.btn_up)

        self.btn_down = QPushButton("▼")
        self.btn_down.setObjectName("iconBtn")
        self.btn_down.setToolTip("Move down (Alt+Down)")
        self.btn_down.clicked.connect(self.on_move_down)
        header.addWidget(self.btn_down)

        self.btn_del_step = QPushButton("⌫")
        self.btn_del_step.setObjectName("iconBtn")
        self.btn_del_step.setToolTip("Delete (Del)")
        self.btn_del_step.clicked.connect(self.on_delete)
        header.addWidget(self.btn_del_step)

        self.btn_clear_test = QPushButton("🗑\uFE0E")
        self.btn_clear_test.setObjectName("iconBtn")
        self.btn_clear_test.setToolTip("Clear all steps")
        self.btn_clear_test.clicked.connect(self.on_clear_test)
        header.addWidget(self.btn_clear_test)

        right_layout.addLayout(header)

        # Таблица шагов
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["#", "Command", "Target", "Value"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Interactive)
        self.table.setColumnWidth(0, 40)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self.table.setColumnWidth(1, 270)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.table.setColumnWidth(2, 180)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Interactive)
        self.table.setColumnWidth(3, 300)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        self.table.setItemDelegateForColumn(1, _CommandDelegate(self.table))
        self.table.cellChanged.connect(self._on_cell_changed)
        self.table.verticalHeader().setDefaultSectionSize(36)

        right_layout.addWidget(self.table)

        main_layout.addWidget(right_panel, 1)

        self.setCentralWidget(root)

        # Status bar (внизу окна)
        self.status = QLabel()
        self.statusBar().addWidget(self.status, 1)  # stretch=1 – занимает всю ширину
        self.statusBar().setSizeGripEnabled(False)

        # Кнопки переключения языка – справа в статусбаре
        lang_widget = QWidget()
        lang_layout = QHBoxLayout(lang_widget)
        lang_layout.setContentsMargins(0, 0, 6, 0)
        lang_layout.setSpacing(2)
        self.btn_lang_en = QPushButton("EN")
        self.btn_lang_en.setFixedSize(34, 22)
        self.btn_lang_en.setObjectName("langBtn")
        self.btn_lang_en.clicked.connect(lambda: self._set_lang("en"))
        lang_layout.addWidget(self.btn_lang_en)
        self.btn_lang_ru = QPushButton("RU")
        self.btn_lang_ru.setFixedSize(34, 22)
        self.btn_lang_ru.setObjectName("langBtn")
        self.btn_lang_ru.clicked.connect(lambda: self._set_lang("ru"))
        lang_layout.addWidget(self.btn_lang_ru)
        self.statusBar().addPermanentWidget(lang_widget)

        # Горячие клавиши (локальные - когда окно в фокусе)
        QShortcut(QKeySequence("Ctrl+S"), self, self.on_save)
        QShortcut(QKeySequence("Ctrl+O"), self, self.on_open)
        QShortcut(QKeySequence("Ctrl+N"), self, self.on_add)
        QShortcut(QKeySequence("Ctrl+D"), self, self.on_duplicate)
        QShortcut(QKeySequence("Alt+Up"), self, self.on_move_up)
        QShortcut(QKeySequence("Alt+Down"), self, self.on_move_down)
        QShortcut(QKeySequence("Delete"), self, self.on_delete)
        QShortcut(QKeySequence("F5"), self, self.on_run_tests)
        QShortcut(QKeySequence("Ctrl+Z"), self, self.on_undo)
        QShortcut(QKeySequence("Ctrl+Y"), self, self.on_redo)
        QShortcut(QKeySequence("Ctrl+C"), self, self.on_copy)
        QShortcut(QKeySequence("Ctrl+V"), self, self.on_paste)

        # Сигналы из потока записи -> GUI
        self.keyword_signal.connect(self._add_keyword_row)
        self.service.on_keyword = self.keyword_signal.emit
        self.pause_signal.connect(self._on_pause_changed)
        self.service.on_pause_changed = self.pause_signal.emit

        # Подключаем сигналы глобальных хоткеев
        self.global_start_signal.connect(self._global_start)
        self.global_stop_signal.connect(self._global_stop)

        # Глобальные горячие клавиши (работают даже когда окно не в фокусе)
        self._start_global_hotkeys()

        # Обновляем состояние кнопок при изменении выделения
        self.table.itemSelectionChanged.connect(self._update_suite_state)

        # Начальное состояние
        self._update_suite_state()
        self._retranslate()   # применяем строки текущего языка
        self._restore_session()

    # ─────────────────────────────────────────────
    #  ЛОКАЛИЗАЦИЯ
    # ─────────────────────────────────────────────

    def _t(self, key, *args):
        """Перевод строки по ключу для текущего языка."""
        d = _TR.get(self._lang, _TR["en"])
        s = d.get(key, _TR["en"].get(key, key))
        return s.format(*args) if args else s

    def _set_lang(self, lang: str):
        if lang == self._lang:
            return
        self._lang = lang
        self._retranslate()

    def _retranslate(self):
        """Обновляет все строки интерфейса при смене языка."""
        t = self._t

        # Подсветка активной кнопки языка
        self.btn_lang_en.setProperty("active", "true" if self._lang == "en" else "false")
        self.btn_lang_ru.setProperty("active", "true" if self._lang == "ru" else "false")
        # Принудительно обновляем стиль (Qt не перечитывает property без этого)
        self.btn_lang_en.style().unpolish(self.btn_lang_en)
        self.btn_lang_en.style().polish(self.btn_lang_en)
        self.btn_lang_ru.style().unpolish(self.btn_lang_ru)
        self.btn_lang_ru.style().polish(self.btn_lang_ru)

        # GroupBox заголовки
        self._suite_group.setTitle(t("g_suite"))
        self._tests_group.setTitle(t("g_tests"))
        self._rec_group.setTitle(t("g_recording"))
        self._run_group.setTitle(t("g_run"))

        # Suite buttons
        self.btn_new.setText(t("btn_new"))
        self.btn_new.setToolTip(t("tip_new"))
        self.btn_open.setText(t("btn_open"))
        self.btn_open.setToolTip(t("tip_open"))
        self.btn_save.setText(t("btn_save"))
        self.btn_save.setToolTip(t("tip_save"))
        self.btn_suite_settings.setText(t("btn_settings"))
        self.btn_suite_settings.setToolTip(t("tip_settings"))

        # Test buttons
        self.btn_add_test.setToolTip(t("tip_add_test"))
        self.btn_rename_test.setToolTip(t("tip_rename_test"))
        self.btn_delete_test.setToolTip(t("tip_delete_test"))

        # Recording buttons
        self.btn_start.setText(t("btn_record"))
        self.btn_start.setToolTip(t("tip_record"))
        self.btn_stop.setText(t("btn_stop"))
        self.btn_stop.setToolTip(t("tip_stop"))
        self.lbl_pause.setText(t("lbl_paused"))

        # Run button
        self.btn_run.setText(t("btn_run"))
        self.btn_run.setToolTip(t("tip_run"))
        # Update tooltips on test-row run buttons
        for i in range(self.tests_list.count()):
            w = self.tests_list.itemWidget(self.tests_list.item(i))
            if w:
                btn = w.findChild(QPushButton, "testRunBtn")
                if btn:
                    btn.setToolTip(t("tip_run_one"))

        # Hotkeys button
        self.btn_hotkeys.setText(t("btn_hotkeys"))
        self.btn_hotkeys.setToolTip(t("tip_hotkeys"))

        # Step buttons
        self.btn_add_step.setToolTip(t("tip_add_step"))
        self.btn_dup_step.setToolTip(t("tip_dup_step"))
        self.btn_up.setToolTip(t("tip_up"))
        self.btn_down.setToolTip(t("tip_down"))
        self.btn_del_step.setToolTip(t("tip_del_step"))
        self.btn_clear_test.setToolTip(t("tip_clear"))
        self.btn_var.setToolTip(t("tip_var_btn"))

        # Заголовки колонок таблицы
        self.table.setHorizontalHeaderLabels([
            t("col_num"), t("col_cmd"), t("col_tgt"), t("col_val")
        ])

        # Метка теста
        if self.current_test_index < 0:
            self.current_test_label.setText(t("no_test"))
        elif self.suite_data and self.current_test_index < len(self.suite_data["tests"]):
            test = self.suite_data["tests"][self.current_test_index]
            self.current_test_label.setText(self._t("test_label", test["name"]))

        # Статус – только если не идёт запись
        if not self._recording:
            self._update_suite_state()   # обновит статусную строку через _t

    # ─────────────────────────────────────────────

    def _restore_session(self):
        last_file = QSettings("microide", "microide").value("last_file", "")
        if not last_file or not os.path.isfile(last_file):
            return
        suite_data = self._parse_robot_file(last_file)
        if not suite_data:
            return
        self.suite_data = suite_data
        for test in suite_data["tests"]:
            self._add_test_item(test)
        if suite_data["tests"]:
            self.tests_list.setCurrentRow(0)
        self._update_suite_state()
        self._modified = False

    # Создание нового Suite
    def on_new_suite(self):
        dialog = NewSuiteDialog(self, lang=self._lang)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            self.suite_data = {
                "name": data["name"],
                "file_path": data["file_path"],
                "settings": {
                    "resource": data["resource"],
                    "suite_setup": data["suite_setup"],
                    "suite_teardown": data["suite_teardown"],
                    "test_setup": data["test_setup"],
                    "test_teardown": data["test_teardown"],
                },
                "run_settings": {
                    "workdir": data["workdir"],
                    "python_exe": data["python_exe"],
                    "variables": data["variables"],
                    "exclude_tags": data["exclude_tags"],
                    "output_dir": data["output_dir"],
                },
                "tests": []
            }
            self.tests_list.clear()
            self.table.setRowCount(0)
            self.current_test_index = -1
            self.current_test_label.setText(self._t("no_test"))
            self._update_suite_state()
            self._modified = False
            QMessageBox.information(self, self._t("msg_suite_ok_t"),
                self._t("msg_suite_ok", data['name'], data['file_path']))

    # Редактирование настроек существующего Suite
    def on_edit_suite_settings(self):
        if not self.suite_data:
            QMessageBox.warning(self, self._t("msg_no_suite_t"), self._t("msg_no_suite"))
            return
        s = self.suite_data["settings"]
        r = self.suite_data["run_settings"]
        initial = {
            "file_path":       self.suite_data.get("file_path", ""),
            "resource":        s.get("resource", ""),
            "suite_setup":     s.get("suite_setup", ""),
            "suite_teardown":  s.get("suite_teardown", ""),
            "test_setup":      s.get("test_setup", ""),
            "test_teardown":   s.get("test_teardown", ""),
            "workdir":         r.get("workdir", ""),
            "python_exe":      r.get("python_exe", ""),
            "variables":       r.get("variables", ""),
            "exclude_tags":    r.get("exclude_tags", ""),
            "output_dir":      r.get("output_dir", ""),
        }
        dialog = NewSuiteDialog(self, lang=self._lang, initial=initial)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            self.suite_data["settings"]["resource"]        = data["resource"]
            self.suite_data["settings"]["suite_setup"]     = data["suite_setup"]
            self.suite_data["settings"]["suite_teardown"]  = data["suite_teardown"]
            self.suite_data["settings"]["test_setup"]      = data["test_setup"]
            self.suite_data["settings"]["test_teardown"]   = data["test_teardown"]
            self.suite_data["run_settings"]["workdir"]     = data["workdir"]
            self.suite_data["run_settings"]["python_exe"]  = data["python_exe"]
            self.suite_data["run_settings"]["variables"]   = data["variables"]
            self.suite_data["run_settings"]["exclude_tags"]= data["exclude_tags"]
            self.suite_data["run_settings"]["output_dir"]  = data["output_dir"]
            self._modified = True
            self._update_suite_state()

    # Выбор теста из списка
    def _on_test_selected(self, index):
        self.current_test_index = index
        if self.suite_data and index >= 0 and index < len(self.suite_data["tests"]):
            test = self.suite_data["tests"][index]
            self.current_test_label.setText(self._t("test_label", test['name']))
            self.table.setRowCount(0)
            for i, step in enumerate(test["steps"]):
                self._add_step_to_table(i + 1, step)
        else:
            self.current_test_label.setText(self._t("no_test"))
            self.table.setRowCount(0)
        self._update_suite_state()

    def _add_test_item(self, test):
        # Создаёт строку теста в списке: имя + кнопка ▶ для запуска
        from PySide6.QtCore import QSize
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 38))
        if test.get("tags"):
            item.setToolTip(f"Tags: {', '.join(test['tags'])}")
        widget = QWidget()
        row_layout = QHBoxLayout(widget)
        row_layout.setContentsMargins(6, 0, 4, 0)
        row_layout.setSpacing(4)
        label = QLabel(test["name"])
        label.setObjectName("testItemLabel")
        row_layout.addWidget(label, 1)
        btn = QPushButton("▷")
        btn.setFixedSize(32, 32)
        btn.setObjectName("testRunBtn")
        btn.setToolTip(self._t("tip_run_one"))
        btn.clicked.connect(lambda _=False, it=item: self._run_test_by_item(it))
        row_layout.addWidget(btn)
        self.tests_list.addItem(item)
        self.tests_list.setItemWidget(item, widget)
        return item

    # Добавление нового теста
    def _on_add_test(self):
        if not self.suite_data:
            QMessageBox.warning(self, self._t("msg_no_suite_t"), self._t("msg_no_suite"))
            return

        dialog = NewTestDialog(self, lang=self._lang)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            test = {
                "name": data["name"],
                "tags": data["tags"],
                "steps": []
            }
            self.suite_data["tests"].append(test)

            # Добавление в список
            self._add_test_item(test)

            # Выбор нового теста
            self.tests_list.setCurrentRow(len(self.suite_data["tests"]) - 1)
            self._update_suite_state()
            self._modified = True

    # Переименование теста
    def _on_rename_test(self):
        if not self.suite_data or self.current_test_index < 0:
            return

        dialog = NewTestDialog(self, lang=self._lang)
        dialog.setWindowTitle(self._t("dlg_rename_test"))
        test = self.suite_data["tests"][self.current_test_index]
        dialog.name_edit.setText(test["name"])
        dialog.tags_edit.setText(", ".join(test["tags"]))

        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_data()
            test["name"] = data["name"]
            test["tags"] = data["tags"]
            item = self.tests_list.item(self.current_test_index)
            if item:
                if data["tags"]:
                    item.setToolTip(f"Tags: {', '.join(data['tags'])}")
                widget = self.tests_list.itemWidget(item)
                if widget:
                    label = widget.findChild(QLabel, "testItemLabel")
                    if label:
                        label.setText(data["name"])
                        label.setStyleSheet("color: #495057;")  # сброс цвета статуса прогона
            self.current_test_label.setText(self._t("test_label", data['name']))
            self._modified = True

    # Удаление теста
    def _on_delete_test(self):
        if not self.suite_data or self.current_test_index < 0:
            return

        test_name = self.suite_data["tests"][self.current_test_index]["name"]
        mb = QMessageBox(self)
        mb.setWindowTitle(self._t("msg_del_test_t"))
        mb.setText(self._t("msg_del_test", test_name))
        mb.setIcon(QMessageBox.Icon.Question)
        btn_yes = mb.addButton(self._t("btn_yes"), QMessageBox.ButtonRole.YesRole)
        btn_no  = mb.addButton(self._t("btn_no"),  QMessageBox.ButtonRole.NoRole)
        mb.setDefaultButton(btn_no)
        mb.exec()
        if mb.clickedButton() is btn_yes:
            del self.suite_data["tests"][self.current_test_index]
            self.tests_list.takeItem(self.current_test_index)
            self.current_test_index = -1
            self.table.setRowCount(0)
            self.current_test_label.setText(self._t("no_test"))
            self._update_suite_state()
            self._modified = True

    def _add_step_to_table(self, num, step):
        # Добавление строки шага в таблицу
        row = self.table.rowCount()
        self.table.insertRow(row)
        num_item = QTableWidgetItem(str(num))
        num_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setItem(row, 0, num_item)
        self.table.setItem(row, 1, QTableWidgetItem(step.get("command", "")))
        self.table.setItem(row, 2, QTableWidgetItem(step.get("target", "")))
        self.table.setItem(row, 3, QTableWidgetItem(step.get("value", "")))

    # Кнопка добавить как переменную ${}
    def _promote_value_to_variable(self):
        if not self.suite_data or self.current_test_index < 0:
            return
        selected = self.table.selectedIndexes()
        if not selected:
            return
        row = selected[0].row()

        # Диалог ввода имени переменной
        dlg = QDialog(self)
        dlg.setWindowTitle(self._t("dlg_var_title"))
        dlg.setMinimumWidth(280)
        layout = QVBoxLayout(dlg)
        form = QFormLayout()
        name_edit = QLineEdit()
        name_edit.setPlaceholderText(self._t("dlg_var_ph"))
        form.addRow(self._t("dlg_var_label"), name_edit)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)

        if dlg.exec() != QDialog.Accepted:
            return

        var_name_raw = name_edit.text().strip().strip("${}")
        if not var_name_raw:
            return

        var_ref = "${" + var_name_raw + "}"

        self._snapshot()
        steps = self.suite_data["tests"][self.current_test_index]["steps"]
        steps[row]["value"] = var_ref
        self._reload_steps()
        self.table.selectRow(row)
        self._update_suite_state()
        self._auto_save()

    def _update_suite_state(self):
        # Обновление состояния кнопок и статуса
        has_suite = self.suite_data is not None
        has_test = self.current_test_index >= 0
        has_selection = len(self.table.selectedItems()) > 0
        has_tests = has_suite and len(self.suite_data["tests"]) > 0

        # Suite buttons
        self.btn_save.setEnabled(has_suite)

        # Test buttons
        self.btn_add_test.setEnabled(has_suite)
        self.btn_rename_test.setEnabled(has_test)
        self.btn_delete_test.setEnabled(has_test)

        # Recording
        self.btn_start.setEnabled(has_test)

        # Run
        self.btn_run.setEnabled(has_tests)

        # Step editing
        self.btn_add_step.setEnabled(has_test)
        self.btn_dup_step.setEnabled(has_selection)
        self.btn_up.setEnabled(has_selection)
        self.btn_down.setEnabled(has_selection)
        self.btn_del_step.setEnabled(has_selection)
        has_steps = has_test and len(self.suite_data["tests"][self.current_test_index]["steps"]) > 0
        self.btn_clear_test.setEnabled(has_steps)
        self.btn_var.setEnabled(has_selection)

        if has_suite:
            file_path = self.suite_data.get("file_path", "")
            display = os.path.basename(file_path) if file_path else f"{self.suite_data['name']}.robot"
            self.status.setText(self._t("suite_status", display, len(self.suite_data['tests'])))
        else:
            self.status.setText(self._t("no_suite"))

    def _reload_steps(self):
        # Перезагрузка таблицы шагов
        self.table.setRowCount(0)
        if self.suite_data and self.current_test_index >= 0:
            for i, step in enumerate(self.suite_data["tests"][self.current_test_index]["steps"]):
                self._add_step_to_table(i + 1, step)

    def _generate_robot_content(self):
        # Генерация содержимого .robot файла
        lines = []
        # Сохраняем run_settings как комментарии, чтобы восстанавливать при открытии
        rs = self.suite_data.get("run_settings", {})
        for key in ("python_exe", "variables", "exclude_tags", "output_dir", "workdir"):
            val = rs.get(key, "")
            if val:
                lines.append(f"# microide:{key}={val}")
        if lines:
            lines.append("")
        lines.append("*** Settings ***")

        settings = self.suite_data["settings"]
        if settings.get("resource"):
            # Нормализуем путь: заменяем \ на / для Robot Framework
            resource_path = settings['resource'].replace('\\', '/')
            lines.append(f"Resource    {resource_path}")
        if settings.get("suite_setup"):
            lines.append(f"Suite Setup       {settings['suite_setup']}")
        if settings.get("suite_teardown"):
            lines.append(f"Suite Teardown    {settings['suite_teardown']}")
        if settings.get("test_setup"):
            lines.append(f"Test Setup        {settings['test_setup']}")
        if settings.get("test_teardown"):
            lines.append(f"Test Teardown     {settings['test_teardown']}")

        lines.append("")
        lines.append("*** Test Cases ***")
        lines.append("")

        for test in self.suite_data["tests"]:
            lines.append(test["name"])
            if test["tags"]:
                lines.append(f"    [Tags]    {'    '.join(test['tags'])}")
            for step in test["steps"]:
                parts = [step["command"]]
                if step.get("target"):
                    parts.append(step["target"])
                if step.get("value"):
                    parts.append(step["value"])
                lines.append("    " + "    ".join(parts))
            lines.append("")

        return "\n".join(lines)

    def _parse_robot_file(self, path):
        # Парсинг .robot файла в структуру suite_data
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            suite_data = {
                "name": os.path.splitext(os.path.basename(path))[0],
                "file_path": path,
                "settings": {
                    "resource": "",
                    "suite_setup": "",
                    "suite_teardown": "",
                    "test_setup": "",
                    "test_teardown": "",
                },
                "run_settings": {
                    "workdir": os.path.dirname(path),
                    "python_exe": "",
                    "variables": "",
                    "exclude_tags": "manual",
                    "output_dir": "",
                },
                "tests": []
            }

            # Читаем run_settings из комментариев microide
            for line in lines:
                stripped = line.strip()
                if not stripped.startswith("# microide:"):
                    break
                kv = stripped[len("# microide:"):]
                if "=" in kv:
                    k, v = kv.split("=", 1)
                    if k in suite_data["run_settings"]:
                        suite_data["run_settings"][k] = v

            current_section = None

            for raw_line in lines:
                line = raw_line.rstrip('\n')
                stripped = line.strip()

                # Определяем секцию
                section_match = re.match(r'\*{3}\s+(.+?)\s*\*{3}', stripped)
                if section_match:
                    current_section = section_match.group(1).lower()
                    continue

                if not stripped:
                    continue

                if current_section == 'settings':
                    parts = re.split(r'  +', stripped)
                    key = parts[0].lower()
                    val = parts[1].strip() if len(parts) > 1 else ""
                    if key == 'resource':
                        suite_data["settings"]["resource"] = val
                    elif key == 'suite setup':
                        suite_data["settings"]["suite_setup"] = val
                    elif key == 'suite teardown':
                        suite_data["settings"]["suite_teardown"] = val
                    elif key == 'test setup':
                        suite_data["settings"]["test_setup"] = val
                    elif key == 'test teardown':
                        suite_data["settings"]["test_teardown"] = val

                elif current_section == 'test cases':
                    if line and not line[0].isspace() and not stripped.startswith('#'):
                        # Новый тест (без отступа)
                        test = {"name": stripped, "tags": [], "steps": []}
                        suite_data["tests"].append(test)
                    elif suite_data["tests"]:
                        current_test = suite_data["tests"][-1]
                        if stripped.startswith('[Tags]'):
                            tag_parts = re.split(r'  +', stripped)
                            current_test["tags"] = [t.strip() for t in tag_parts[1:] if t.strip()]
                        else:
                            # Шаг
                            step_parts = re.split(r'    ', stripped)
                            step_parts = [p for p in step_parts if p]
                            step = {
                                "command": step_parts[0] if len(step_parts) > 0 else "",
                                "target": step_parts[1] if len(step_parts) > 1 else "",
                                "value": "    ".join(step_parts[2:]) if len(step_parts) > 2 else "",
                            }
                            current_test["steps"].append(step)

            return suite_data

        except Exception as e:
            QMessageBox.critical(self, self._t("msg_err_t"), self._t("msg_load_err", e))
            return None

    def _start_global_hotkeys(self):
        # Запуск глобальных горячих клавиш (F6/F7) через библиотеку keyboard
        def on_key(event):
            if event.event_type == 'down':
                if event.name == 'f6':
                    self.global_start_signal.emit()
                elif event.name == 'f7':
                    self.global_stop_signal.emit()

        kb_global.hook(on_key)

    def _global_start(self):
        # Обработчик глобального F6 – начало записи
        if self.btn_start.isEnabled():
            self.on_start()

    def _global_stop(self):
        # Обработчик глобального F7 – остановка записи
        if self.btn_stop.isEnabled():
            self.on_stop()

    def _do_save_for_close(self) -> bool:
        """Сохраняет файл перед закрытием. Возвращает True при успехе, False при отмене."""
        if not self.suite_data:
            return True
        file_path = self.suite_data.get("file_path", "")
        if not file_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self, self._t("fd_save"), os.path.expanduser("~"),
                "Robot files (*.robot)"
            )
            if not file_path:
                return False
            if not file_path.lower().endswith(".robot"):
                file_path += ".robot"
            self.suite_data["file_path"] = file_path
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self._generate_robot_content())
            self._modified = False
            return True
        except Exception as e:
            QMessageBox.critical(self, self._t("msg_err_t"), str(e))
            return False

    def closeEvent(self, event):
        if self._modified and self.suite_data:
            msg = QMessageBox(self)
            msg.setWindowTitle(self._t("msg_unsaved_t"))
            msg.setText(self._t("msg_unsaved"))
            msg.setIcon(QMessageBox.Question)
            msg.setMinimumWidth(360)
            btn_save    = msg.addButton(self._t("btn_save_close"),    QMessageBox.AcceptRole)
            msg.addButton(self._t("btn_discard_close"), QMessageBox.DestructiveRole)
            btn_cancel  = msg.addButton(self._t("btn_cancel_close"),  QMessageBox.RejectRole)
            msg.setDefaultButton(btn_save)
            msg.exec()
            clicked = msg.clickedButton()
            if clicked == btn_cancel:
                event.ignore()
                return
            elif clicked == btn_save:
                if not self._do_save_for_close():
                    event.ignore()
                    return
        # Запоминаем последний открытый файл
        settings = QSettings("microide", "microide")
        file_path = self.suite_data.get("file_path", "") if self.suite_data else ""
        if file_path:
            settings.setValue("last_file", file_path)
        else:
            settings.remove("last_file")

        # Остановка глобальных хоткеев при закрытии
        try:
            kb_global.unhook_all()
        except Exception:
            pass
        super().closeEvent(event)

    def _apply_styles(self):
        # Применение стилей к интерфейсу
        self.setStyleSheet("""
            * {
                font-family: 'Segoe UI', Arial, sans-serif;
            }
            QMainWindow {
                background-color: #f0f2f5;
            }
            QPushButton {
                padding: 8px 12px;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                background-color: #ffffff;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
                border-color: #b0b0b0;
            }
            QPushButton:disabled {
                background-color: #f5f5f5;
                color: #aaa;
                border-color: #e0e0e0;
            }
            QPushButton#recordBtn {
                background-color: #d4edda;
                border-color: #28a745;
                color: #155724;
                font: bold 12px 'Segoe UI Historic', 'Segoe UI Symbol', 'Segoe UI', Arial, sans-serif;
                padding: 8px 16px 8px 20px;
                border-radius: 0px;
            }
            QPushButton#recordBtn:hover {
                background-color: #c3e6cb;
            }
            QPushButton#stopBtn {
                background-color: #f8d7da;
                border-color: #dc3545;
                color: #721c24;
                font: bold 12px 'Segoe UI Historic', 'Segoe UI Symbol', 'Segoe UI', Arial, sans-serif;
                padding: 8px 16px 8px 20px;
                border-radius: 0px;
            }
            QPushButton#stopBtn:hover {
                background-color: #f5c6cb;
            }
            QPushButton#runBtn {
                background-color: #cce5ff;
                border-color: #007bff;
                color: #004085;
                font: bold 12px 'Segoe UI Symbol', 'Segoe UI', Arial, sans-serif;
                padding: 8px 16px 8px 20px;
                border-radius: 0px;
            }
            QPushButton#runBtn:hover {
                background-color: #b8daff;
            }
            QPushButton#iconBtn {
                padding: 6px 10px;
                min-width: 28px;
                font-size: 14px;
            }
            QPushButton#langBtn {
                padding: 2px 4px;
                font-size: 11px;
                font-weight: bold;
                border-radius: 4px;
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                color: #555;
            }
            QPushButton#langBtn:hover {
                background-color: #e0e0e0;
            }
            QPushButton#langBtn[active="true"] {
                background-color: #1976d2;
                border-color: #1565c0;
                color: white;
            }
            QPushButton#testRunBtn {
                background: transparent;
                border: none;
                color: #adb5bd;
                font-size: 17px;
                padding: 0;
                border-radius: 3px;
            }
            QPushButton#testRunBtn:hover {
                background: #e3f2fd;
                color: #1976d2;
            }
            QPushButton#testRunBtn:pressed {
                background: #bbdefb;
            }
            QPushButton#renameTestBtn {
                font-size: 16px;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 12px;
                border: 1px solid #d0d0d0;
                border-radius: 8px;
                margin-top: 6px;
                padding: 10px;
                padding-top: 28px;
                background-color: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: padding;
                subcontrol-position: top left;
                top: 8px;
                left: 12px;
                padding: 0;
                color: #444;
            }
            QTableWidget {
                background-color: #ffffff;
                border: 1px solid #d0d0d0;
                gridline-color: #eee;
                outline: none;
            }
            QTableWidget::item {
                padding: 4px 6px;
                border-bottom: 1px solid #f1f3f4;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
                color: #000;
            }
            QTableWidget::item:alternate {
                background-color: #f8f9fa;
            }
            QTableWidget QLineEdit {
                padding: 4px 6px;
                font-size: 12px;
                min-height: 20px;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                border: none;
                border-bottom: 2px solid #dee2e6;
                border-right: 1px solid #eee;
                padding: 10px 12px;
                font-weight: 600;
                color: #495057;
            }
            QHeaderView::section:last {
                border-right: none;
            }
            QStatusBar::item {
                border: none;
            }
            QLabel {
                color: #495057;
                font-size: 12px;
            }
        """)
        QApplication.instance().setStyleSheet("""
            QToolTip {
                background-color: #2c2c2c;
                color: #ffffff;
                border: 1px solid #555555;
                padding: 5px 8px;
                font-size: 12px;
            }
        """)

    def _parse_keyword(self, keyword: str):
        # Парсинг keyword строки в (command, target, value)
        # Разделитель - 4 пробела (Robot Framework стиль)
        parts = re.split(r'    +', keyword.strip())
        command = parts[0] if len(parts) > 0 else ""
        target = parts[1] if len(parts) > 1 else ""
        value = "    ".join(parts[2:]) if len(parts) > 2 else ""
        return command, target, value

    def _add_keyword_row(self, keyword: str):
        # Добавление keyword в таблицу с подсветкой и в текущий тест
        command, target, value = self._parse_keyword(keyword)

        if self.suite_data and self.current_test_index >= 0:
            self._snapshot()
            step = {"command": command, "target": target, "value": value}
            self.suite_data["tests"][self.current_test_index]["steps"].append(step)

        row = self.table.rowCount()
        self.table.insertRow(row)

        highlight = QColor(200, 255, 200)  # зелёная подсветка для нового шага
        items = [
            QTableWidgetItem(str(row + 1)),
            QTableWidgetItem(command),
            QTableWidgetItem(target),
            QTableWidgetItem(value)
        ]
        for col, item in enumerate(items):
            item.setBackground(highlight)
            self.table.setItem(row, col, item)

        self.table.scrollToBottom()
        self._update_suite_state()

        QTimer.singleShot(1000, lambda r=row: self._clear_highlight(r))  # снимаем подсветку через 1 сек

    def _clear_highlight(self, row):
        # Снятие подсветки строки
        if row < self.table.rowCount():
            for col in range(4):
                item = self.table.item(row, col)
                if item:
                    item.setBackground(QColor(255, 255, 255))

    def _on_cell_changed(self, row, col):
        # Синхронизация изменений в таблице с данными suite_data
        if col == 0:
            # Колонка # только для чтения - восстанавливаем номер без рекурсии
            self.table.blockSignals(True)
            item = QTableWidgetItem(str(row + 1))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, item)
            self.table.blockSignals(False)
            return

        if not self.suite_data or self.current_test_index < 0:
            return

        steps = self.suite_data["tests"][self.current_test_index]["steps"]
        if row >= len(steps):
            return

        item = self.table.item(row, col)
        value = item.text() if item else ""

        # Записываем изменённое значение в соответствующее поле шага
        if col == 1:
            steps[row]["command"] = value
        elif col == 2:
            steps[row]["target"] = value
        elif col == 3:
            steps[row]["value"] = value
        self._auto_save()

    def _renumber_rows(self):
        # Перенумерация строк после удаления
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            item = QTableWidgetItem(str(row + 1))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, item)
        self.table.blockSignals(False)

    def keyPressEvent(self, event: QKeyEvent):
        # Обработка Delete для удаления выделенных строк
        if event.key() == Qt.Key_Delete:
            self.on_delete()
        else:
            super().keyPressEvent(event)

    def on_add(self):
        # Добавление пустой строки
        if not self.suite_data or self.current_test_index < 0:
            return
        self._snapshot()
        row = self.table.rowCount()
        selected = self.table.selectedIndexes()
        if selected:
            row = selected[0].row() + 1

        step = {"command": "Keyword", "target": "", "value": ""}
        self.suite_data["tests"][self.current_test_index]["steps"].insert(row, step)

        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(str(row + 1)))
        self.table.setItem(row, 1, QTableWidgetItem("Keyword"))
        self.table.setItem(row, 2, QTableWidgetItem(""))
        self.table.setItem(row, 3, QTableWidgetItem(""))
        self._renumber_rows()
        self._update_suite_state()
        self.table.selectRow(row)
        self.table.editItem(self.table.item(row, 1))
        self._auto_save()

    def on_duplicate(self):
        # Дублирование выделенной строки
        selected = self.table.selectedIndexes()
        if not selected or not self.suite_data or self.current_test_index < 0:
            return
        self._snapshot()

        src_row = selected[0].row()
        new_row = src_row + 1

        steps = self.suite_data["tests"][self.current_test_index]["steps"]
        if src_row < len(steps):
            new_step = steps[src_row].copy()
            steps.insert(new_row, new_step)

        self.table.insertRow(new_row)
        for col in range(4):
            src_item = self.table.item(src_row, col)
            text = src_item.text() if src_item else ""
            self.table.setItem(new_row, col, QTableWidgetItem(text))

        self._renumber_rows()
        self._update_suite_state()
        self.table.selectRow(new_row)
        self._auto_save()

    def _swap_rows(self, row1, row2):
        # Перестановка двух строк местами
        if self.suite_data and self.current_test_index >= 0:
            steps = self.suite_data["tests"][self.current_test_index]["steps"]
            if row1 < len(steps) and row2 < len(steps):
                steps[row1], steps[row2] = steps[row2], steps[row1]

        for col in range(4):
            item1 = self.table.item(row1, col)
            item2 = self.table.item(row2, col)
            text1 = item1.text() if item1 else ""
            text2 = item2.text() if item2 else ""
            self.table.setItem(row1, col, QTableWidgetItem(text2))
            self.table.setItem(row2, col, QTableWidgetItem(text1))
        self._renumber_rows()

    def on_move_up(self):
        # Перемещение выделенной строки вверх
        selected = self.table.selectedIndexes()
        if not selected:
            return
        row = selected[0].row()
        if row > 0:
            self._snapshot()
            self._swap_rows(row, row - 1)
            self.table.selectRow(row - 1)
            self._auto_save()

    def on_move_down(self):
        # Перемещение выделенной строки вниз
        selected = self.table.selectedIndexes()
        if not selected:
            return
        row = selected[0].row()
        if row < self.table.rowCount() - 1:
            self._snapshot()
            self._swap_rows(row, row + 1)
            self.table.selectRow(row + 1)
            self._auto_save()

    def on_delete(self):
        # Удаление выделенных строк
        rows = sorted(set(idx.row() for idx in self.table.selectedIndexes()), reverse=True)
        if not rows:
            return
        msg = self._t("msg_del_step_n") if len(rows) > 1 else self._t("msg_del_step_1")
        mb = QMessageBox(self)
        mb.setWindowTitle(self._t("msg_del_step_t"))
        mb.setText(msg)
        mb.setIcon(QMessageBox.Icon.Question)
        btn_yes = mb.addButton(self._t("btn_yes"), QMessageBox.ButtonRole.YesRole)
        btn_no  = mb.addButton(self._t("btn_no"),  QMessageBox.ButtonRole.NoRole)
        mb.setDefaultButton(btn_no)
        mb.exec()
        if mb.clickedButton() is not btn_yes:
            return
        self._snapshot()

        if self.suite_data and self.current_test_index >= 0:
            steps = self.suite_data["tests"][self.current_test_index]["steps"]
            for row in rows:
                if row < len(steps):
                    del steps[row]

        for row in rows:
            self.table.removeRow(row)
        self._renumber_rows()
        self._update_suite_state()
        self._auto_save()

    def _snapshot(self):
        # Сохранение текущих шагов в стек отмены
        if not self.suite_data or self.current_test_index < 0:
            return
        steps = self.suite_data["tests"][self.current_test_index]["steps"]
        self._undo_stack.append((self.current_test_index, copy.deepcopy(steps)))
        self._redo_stack.clear()
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)

    def on_undo(self):
        # Отмена последнего действия
        if not self._undo_stack:
            return
        idx, steps = self._undo_stack.pop()
        if not self.suite_data or idx >= len(self.suite_data["tests"]):
            return
        current = self.suite_data["tests"][idx]["steps"]
        self._redo_stack.append((idx, copy.deepcopy(current)))
        self.suite_data["tests"][idx]["steps"] = steps
        if idx == self.current_test_index:
            self._reload_steps()
        self._update_suite_state()
        self._auto_save()

    def on_redo(self):
        # Повтор отменённого действия
        if not self._redo_stack:
            return
        idx, steps = self._redo_stack.pop()
        if not self.suite_data or idx >= len(self.suite_data["tests"]):
            return
        current = self.suite_data["tests"][idx]["steps"]
        self._undo_stack.append((idx, copy.deepcopy(current)))
        self.suite_data["tests"][idx]["steps"] = steps
        if idx == self.current_test_index:
            self._reload_steps()
        self._update_suite_state()
        self._auto_save()

    def on_copy(self):
        # Копирование выделенных шагов в буфер
        selected = self.table.selectedIndexes()
        if not selected or not self.suite_data or self.current_test_index < 0:
            return
        rows = sorted(set(i.row() for i in selected))
        steps = self.suite_data["tests"][self.current_test_index]["steps"]
        self._step_clipboard = [copy.deepcopy(steps[r]) for r in rows if r < len(steps)]

    def on_paste(self):
        # Вставка шагов из буфера после выделенной строки
        if not self._step_clipboard or not self.suite_data or self.current_test_index < 0:
            return
        self._snapshot()
        selected = self.table.selectedIndexes()
        insert_at = selected[-1].row() + 1 if selected else self.table.rowCount()
        steps = self.suite_data["tests"][self.current_test_index]["steps"]
        for i, step in enumerate(self._step_clipboard):
            steps.insert(insert_at + i, copy.deepcopy(step))
        self._reload_steps()
        self._update_suite_state()
        self.table.selectRow(insert_at)
        self._auto_save()

    def on_clear_test(self):
        # Удаление всех шагов текущего теста
        if not self.suite_data or self.current_test_index < 0:
            return
        steps = self.suite_data["tests"][self.current_test_index]["steps"]
        if not steps:
            return
        test_name = self.suite_data["tests"][self.current_test_index]["name"]
        mb = QMessageBox(self)
        mb.setWindowTitle(self._t("msg_clear_t"))
        mb.setText(self._t("msg_clear", test_name))
        mb.setIcon(QMessageBox.Icon.Question)
        btn_yes = mb.addButton(self._t("btn_yes"), QMessageBox.ButtonRole.YesRole)
        btn_no  = mb.addButton(self._t("btn_no"),  QMessageBox.ButtonRole.NoRole)
        mb.setDefaultButton(btn_no)
        mb.exec()
        if mb.clickedButton() is btn_yes:
            self._snapshot()
            steps.clear()
            self.table.setRowCount(0)
            self._update_suite_state()

    def _update_test_result(self, test_idx, passed):
        # Обновление иконки ✓/✗ у теста в списке
        if not self.suite_data or test_idx >= len(self.suite_data["tests"]):
            return
        self.suite_data["tests"][test_idx]["last_result"] = "PASS" if passed else "FAIL"
        item = self.tests_list.item(test_idx)
        if item:
            name = self.suite_data["tests"][test_idx]["name"]
            widget = self.tests_list.itemWidget(item)
            if widget:
                label = widget.findChild(QLabel, "testItemLabel")
                if label:
                    label.setText(("✔  " if passed else "✖  ") + name)
                    label.setStyleSheet(f"color: {'#28a745' if passed else '#dc3545'};")

    def on_hotkeys(self):
        # Справка по горячим клавишам
        dialog = QDialog(self)
        dialog.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        dialog.setWindowTitle(self._t("hk_title"))
        dialog.setFixedSize(300, 420)
        layout = QVBoxLayout(dialog)

        text = QTextBrowser()
        text.setOpenExternalLinks(False)
        t = self._t
        text.setHtml(f"""
        <style>
            body {{ font-family: Segoe UI, Arial; font-size: 11px; }}
            h3 {{ margin: 8px 0 4px 0; color: #333; font-size: 12px; }}
            table {{ width: 100%; }}
            td {{ padding: 2px 5px; }}
            .key {{ font-weight: bold; color: #1976d2; white-space: nowrap; }}
        </style>
        <h3>{t("hk_rec")}</h3>
        <table>
            <tr><td class="key">F5</td><td>{t("hk_run_t")}</td></tr>
            <tr><td class="key">F6</td><td>{t("hk_start_t")}</td></tr>
            <tr><td class="key">F7</td><td>{t("hk_stop_t")}</td></tr>
            <tr><td class="key">ESC</td><td>{t("hk_pause_t")}</td></tr>
            <tr><td class="key">Enter</td><td>{t("hk_resume_t")}</td></tr>
            <tr><td class="key">ESC×2</td><td>{t("hk_stop2_t")}</td></tr>
        </table>
        <h3>{t("hk_during")}</h3>
        <table>
            <tr><td class="key">Ctrl+G</td><td>{t("hk_check")}</td></tr>
            <tr><td class="key">Ctrl+J</td><td>{t("hk_active")}</td></tr>
            <tr><td class="key">Ctrl+R</td><td>{t("hk_focus")}</td></tr>
            <tr><td class="key">Ctrl+T</td><td>{t("hk_sel")}</td></tr>
        </table>
        <h3>{t("hk_steps")}</h3>
        <table>
            <tr><td class="key">Ctrl+N</td><td>{t("hk_add_s")}</td></tr>
            <tr><td class="key">Ctrl+D</td><td>{t("hk_dup_s")}</td></tr>
            <tr><td class="key">Alt+↑</td><td>{t("hk_up_s")}</td></tr>
            <tr><td class="key">Alt+↓</td><td>{t("hk_down_s")}</td></tr>
            <tr><td class="key">Delete</td><td>{t("hk_del_s")}</td></tr>
            <tr><td class="key">Ctrl+C</td><td>{t("hk_copy_s")}</td></tr>
            <tr><td class="key">Ctrl+V</td><td>{t("hk_paste_s")}</td></tr>
            <tr><td class="key">Ctrl+Z</td><td>{t("hk_undo_s")}</td></tr>
            <tr><td class="key">Ctrl+Y</td><td>{t("hk_redo_s")}</td></tr>
        </table>
        <h3>{t("hk_file")}</h3>
        <table>
            <tr><td class="key">Ctrl+S</td><td>{t("hk_save_s")}</td></tr>
            <tr><td class="key">Ctrl+O</td><td>{t("hk_open_s")}</td></tr>
        </table>
        """)
        layout.addWidget(text)

        dialog.exec()

    def on_open(self):
        # Открытие .robot файла через диалог проводника
        path, _ = QFileDialog.getOpenFileName(
            self, self._t("fd_open"),
            os.path.expanduser("~"),
            "Robot files (*.robot);;All files (*.*)"
        )
        if not path:
            return

        suite_data = self._parse_robot_file(path)
        if suite_data is None:
            return

        self.suite_data = suite_data
        self.tests_list.clear()
        for test in suite_data["tests"]:
            self._add_test_item(test)

        self.table.setRowCount(0)
        self.current_test_index = -1
        self.current_test_label.setText(self._t("no_test"))
        self._update_suite_state()

        if suite_data["tests"]:
            self.tests_list.setCurrentRow(0)
        self._modified = False

    # Если путь уже известен, сохраняем файл
    def _auto_save(self):
        if not self.suite_data:
            return
        self._modified = True
        file_path = self.suite_data.get("file_path", "")
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self._generate_robot_content())
        except Exception:
            pass

    def on_save(self):
        # Сохранение .robot файла
        if not self.suite_data:
            QMessageBox.warning(self, self._t("msg_no_suite_t"), self._t("msg_no_suite"))
            return

        # Если путь не задан - запросить через диалог
        file_path = self.suite_data.get("file_path", "")
        if not file_path:
            file_path, _ = QFileDialog.getSaveFileName(
                self, self._t("fd_save"),
                os.path.expanduser("~"),
                "Robot files (*.robot)"
            )
            if not file_path:
                return
            if not file_path.lower().endswith(".robot"):
                file_path += ".robot"
            self.suite_data["file_path"] = file_path
            self.suite_data["name"] = os.path.splitext(os.path.basename(file_path))[0]

        content = self._generate_robot_content()

        # Превью окно
        preview = QDialog(self)
        display_name = os.path.basename(file_path)
        preview.setWindowTitle(self._t("fd_preview", display_name))
        preview.resize(600, 500)
        layout = QVBoxLayout(preview)

        text = QTextEdit()
        text.setPlainText(content)
        text.setFont(QFont("Consolas", 10))
        layout.addWidget(text)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(preview.accept)
        buttons.rejected.connect(preview.reject)
        layout.addWidget(buttons)

        if preview.exec() == QDialog.Accepted:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(text.toPlainText())
            self._modified = False
            self.status.setText(self._t("st_saved", display_name))
            QMessageBox.information(self, self._t("msg_saved_t"), self._t("msg_saved", file_path))

    def _build_robot_cmd(self, python_exe, output_dir, variables, exclude_tags, temp_file):
        # Сборка команды robot с параметрами
        cmd = [python_exe, "-u", "-m", "robot", "--outputdir", output_dir]
        if variables:
            for var in variables.split(","):
                var = var.strip()
                if var:
                    cmd.extend(["-v", var])
        if exclude_tags:
            for tag in exclude_tags.split(","):
                tag = tag.strip()
                if tag:
                    cmd.extend(["-e", tag])
        cmd.append(temp_file)
        return cmd

    def _generate_single_test_content(self, test):
        # Генерация .robot файла с одним тестом (полные settings из suite)
        lines = ["*** Settings ***"]
        settings = self.suite_data["settings"]
        if settings.get("resource"):
            resource_path = settings['resource'].replace('\\', '/')
            lines.append(f"Resource    {resource_path}")
        if settings.get("suite_setup"):
            lines.append(f"Suite Setup       {settings['suite_setup']}")
        if settings.get("suite_teardown"):
            lines.append(f"Suite Teardown    {settings['suite_teardown']}")
        if settings.get("test_setup"):
            lines.append(f"Test Setup        {settings['test_setup']}")
        if settings.get("test_teardown"):
            lines.append(f"Test Teardown     {settings['test_teardown']}")
        lines.append("")
        lines.append("*** Test Cases ***")
        lines.append("")
        lines.append(test["name"])
        if test["tags"]:
            lines.append(f"    [Tags]    {'    '.join(test['tags'])}")
        for step in test["steps"]:
            parts = [step["command"]]
            if step.get("target"):
                parts.append(step["target"])
            if step.get("value"):
                parts.append(step["value"])
            lines.append("    " + "    ".join(parts))
        lines.append("")
        return "\n".join(lines)

    def on_run_tests(self):
        # Запуск всех тестов из текущего suite
        if not self.suite_data:
            QMessageBox.warning(self, self._t("msg_no_suite_t"), self._t("msg_no_suite"))
            return
        if not self.suite_data["tests"]:
            QMessageBox.warning(self, self._t("msg_no_tests_t"), self._t("msg_no_tests"))
            return
        self._run_tests_list(list(enumerate(self.suite_data["tests"])))

    def _run_test_by_item(self, item):
        # Запуск теста по элементу списка (вызывается кнопкой ▶ в строке теста)
        idx = self.tests_list.row(item)
        if idx < 0 or not self.suite_data or idx >= len(self.suite_data["tests"]):
            return
        self.tests_list.setCurrentRow(idx)
        self._run_tests_list([(idx, self.suite_data["tests"][idx])])

    def _run_tests_list(self, indexed_tests):
        # indexed_tests: список (original_index, test) для запуска
        # Автосохранение перед запуском
        _auto_path = self.suite_data.get("file_path", "")
        if _auto_path:
            try:
                with open(_auto_path, 'w', encoding='utf-8') as _f:
                    _f.write(self._generate_robot_content())
            except Exception:
                pass

        run_settings = self.suite_data.get("run_settings", {})
        workdir = run_settings.get("workdir", "").strip()
        variables = run_settings.get("variables", "").strip()
        exclude_tags = run_settings.get("exclude_tags", "").strip()
        if getattr(sys, "frozen", False):
            import shutil
            _fallback_python = shutil.which("python") or shutil.which("python3") or ""
        else:
            _fallback_python = sys.executable
        python_exe = run_settings.get("python_exe", "").strip() or _fallback_python

        # Определяем директорию для вывода логов (output.xml, log.html, report.html)
        output_dir_setting = run_settings.get("output_dir", "").strip()
        file_path = self.suite_data.get("file_path", "")
        if output_dir_setting and os.path.isdir(output_dir_setting):
            output_dir = output_dir_setting
        elif file_path:
            output_dir = os.path.dirname(file_path)
        elif workdir and os.path.isdir(workdir):
            output_dir = workdir
        else:
            output_dir = os.path.expanduser("~")

        suite_name = self.suite_data["name"]

        # Каждый тест – отдельный robot-процесс (Suite Setup/Teardown на каждый тест)
        commands = []
        temp_files = []
        original_indices = []
        _tmp_dir = tempfile.gettempdir()
        for orig_idx, test in indexed_tests:
            safe = re.sub(r'[^\w]', '_', test["name"])[:40]
            tf = os.path.join(_tmp_dir, f"{suite_name}_{safe}.robot")
            with open(tf, "w", encoding="utf-8") as f:
                f.write(self._generate_single_test_content(test))
            temp_files.append(tf)
            commands.append(self._build_robot_cmd(python_exe, output_dir, variables, exclude_tags, tf))
            original_indices.append(orig_idx)

        run_dialog = QDialog(self)
        run_dialog.setWindowTitle(self._t("run_title", suite_name))
        run_dialog.resize(700, 500)
        layout = QVBoxLayout(run_dialog)

        status_label = QLabel(self._t("run_running"))
        status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #007bff;")
        layout.addWidget(status_label)

        output_text = QTextEdit()
        output_text.setReadOnly(True)
        output_text.setFont(QFont("Consolas", 9))
        output_text.setStyleSheet("background-color: #1e1e1e; color: #d4d4d4;")
        layout.addWidget(output_text)

        btn_layout = QHBoxLayout()
        btn_open_report = QPushButton(self._t("run_open_report"))
        btn_open_report.setVisible(False)
        log_html_path = os.path.join(output_dir, "log.html")
        btn_open_report.clicked.connect(lambda: __import__("webbrowser").open(log_html_path))
        btn_layout.addWidget(btn_open_report)
        btn_layout.addStretch()
        btn_close = QPushButton(self._t("run_close"))
        btn_close.clicked.connect(run_dialog.close)
        btn_layout.addWidget(btn_close)
        layout.addLayout(btn_layout)

        run_dialog.show()
        QApplication.processEvents()

        # Общее изменяемое состояние запуска - используется в замыканиях ниже
        run_state = {
            "cmd_index": 0,           # индекс текущей команды
            "total": len(commands),   # всего команд
            "any_failed": False,      # флаг: хотя бы один тест упал
            "log_handle": None,       # открытый файл для записи вывода
            "process": None,          # текущий subprocess.Popen
            "last_pos": 0,            # позиция чтения лог-файла
            "log_file": None,         # путь к временному лог-файлу
        }

        def start_next_command():
            # Запускает следующую команду из списка; при исчерпании - показывает итог
            idx = run_state["cmd_index"]
            if idx >= run_state["total"]:
                for tf in temp_files:
                    try:
                        os.remove(tf)  # удаляем временные .robot файлы
                    except Exception:
                        pass
                if run_state["any_failed"]:
                    status_label.setText(self._t("run_failed"))
                    status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #dc3545;")
                else:
                    status_label.setText(self._t("run_passed"))
                    status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #28a745;")
                if os.path.isfile(log_html_path):
                    btn_open_report.setVisible(True)
                return

            cmd = commands[idx]
            prefix = f"\n[{idx + 1}/{run_state['total']}] " if run_state["total"] > 1 else ""
            output_text.append(f"{prefix}$ {' '.join(cmd)}\n")
            output_text.append("-" * 50 + "\n")
            output_text.moveCursor(QTextCursor.End)
            QApplication.processEvents()

            log_file = os.path.join(_tmp_dir, f"{suite_name}_run{idx}.log")
            run_state["log_file"] = log_file
            run_state["last_pos"] = 0

            try:
                # stdout процесса пишем в файл, чтобы читать его построчно через таймер
                run_state["log_handle"] = open(log_file, "w", encoding="utf-8", buffering=1)
                env = os.environ.copy()
                env["PYTHONIOENCODING"] = "utf-8"
                env["PYTHONLEGACYWINDOWSSTDIO"] = "0"
                run_state["process"] = subprocess.Popen(
                    cmd,
                    stdout=run_state["log_handle"],
                    stderr=subprocess.STDOUT,
                    cwd=workdir if workdir and os.path.isdir(workdir) else None,
                    env=env,
                )
            except FileNotFoundError:
                status_label.setText(self._t("run_err_notfound"))
                status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #dc3545;")
                output_text.append(self._t("run_not_found") + "\n")
            except Exception as e:
                status_label.setText(f"✖ Error: {str(e)}")
                status_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #dc3545;")
                output_text.append(str(e))

        def update_output():
            # Вызывается таймером каждые 100 мс - читает новые строки из лог-файла
            process = run_state["process"]
            log_file = run_state["log_file"]
            if not process or not log_file:
                return

            try:
                run_state["log_handle"].flush()
            except Exception:
                pass

            try:
                with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(run_state["last_pos"])  # читаем только новые данные
                    new_content = f.read()
                    if new_content:
                        output_text.insertPlainText(new_content)
                        output_text.moveCursor(QTextCursor.End)
                        run_state["last_pos"] = f.tell()
            except Exception:
                pass

            returncode = process.poll()  # None - процесс ещё жив
            if returncode is not None:
                try:
                    with open(log_file, "r", encoding="utf-8", errors="replace") as f:
                        f.seek(run_state["last_pos"])
                        remaining = f.read()  # дочитываем остаток после завершения
                        if remaining:
                            output_text.insertPlainText(remaining)
                            output_text.moveCursor(QTextCursor.End)
                except Exception:
                    pass

                try:
                    run_state["log_handle"].close()
                except Exception:
                    pass
                try:
                    os.remove(log_file)  # чистим временный лог
                except Exception:
                    pass

                finished_idx = run_state["cmd_index"]
                if returncode != 0:
                    run_state["any_failed"] = True

                run_state["cmd_index"] += 1
                run_state["process"] = None
                run_state["log_file"] = None

                # Обновляем статус теста в списке
                self._update_test_result(original_indices[finished_idx], returncode == 0)

                if run_state["cmd_index"] < run_state["total"]:
                    status_label.setText(
                        self._t("run_test_n", run_state['cmd_index'] + 1, run_state['total'])
                    )
                    start_next_command()
                else:
                    timer.stop()
                    start_next_command()  # idx == total -> покажет итог

        # Таймер опрашивает лог-файл каждые 100 мс, не блокируя GUI
        timer = QTimer(run_dialog)
        timer.timeout.connect(update_output)
        timer.start(100)

        start_next_command()
        run_dialog.exec()

    def on_start(self):
        self._recording = True
        self.btn_stop.setEnabled(True)
        self.btn_stop.setStyleSheet("")        # сброс «горящего» stop при новой записи
        self.btn_start.setEnabled(False)
        self.btn_start.setStyleSheet(  # тёмно-зелёный – визуально «активна запись»
            "background-color: #1a7a35; border-color: #155d27; color: white; font-weight: bold;"
        )
        self.status.setText(self._t("st_recording"))
        self.status.setStyleSheet("background-color: #ffe0e0; color: #c0392b; font-weight: bold;")

        self.service.start()
        self.thread = RecorderThread(self.service)       # создаём поток
        self.thread.finished_with_result.connect(self.on_finished)
        self.thread.start()                              # запускаем запись

    def _on_pause_changed(self, is_paused: bool):
        self.lbl_pause.setVisible(is_paused)
        if is_paused:
            self.btn_start.setStyleSheet(      # явно серый – глобальный #recordBtn иначе перекрывает
                "background-color: #c8c8c8; border-color: #aaa; color: #777; font-weight: bold;"
            )
            self.btn_stop.setStyleSheet("")    # стоп – обычный, не горит
            self.status.setText(self._t("st_paused"))
            self.status.setStyleSheet("background-color: #fff3cd; color: #856404; font-weight: bold;")
        else:
            self.btn_start.setStyleSheet(
                "background-color: #1a7a35; border-color: #155d27; color: white; font-weight: bold;"
            )
            self.btn_stop.setStyleSheet("")
            self.status.setText(self._t("st_recording"))
            self.status.setStyleSheet("background-color: #ffe0e0; color: #c0392b; font-weight: bold;")

    def on_stop(self):
        self.btn_start.setStyleSheet("")   # record – погашена
        self.btn_stop.setStyleSheet(       # stop – горит
            "background-color: #dc3545; border-color: #a71d2a; color: white; font-weight: bold;"
        )
        self.lbl_pause.setVisible(False)
        self.status.setText(self._t("st_stopping"))
        self.service.stop()  # сигнал сервису остановиться; поток завершится сам

    def on_finished(self, result):
        # Вызывается сигналом из RecorderThread после завершения записи
        self._recording = False
        self.lbl_pause.setVisible(False)
        self.btn_stop.setEnabled(False)    # stop горит до нажатия Record (сброс в on_start)
        self.btn_start.setEnabled(True)
        self.btn_start.setStyleSheet("")   # возврат к глобальному #recordBtn стилю
        self.status.setStyleSheet("")
        self._update_suite_state()
