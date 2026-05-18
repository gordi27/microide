# Горячие клавиши:
#     ESC         - пауза
#     Enter       - продолжить
#     ESC+ESC     - стоп
#     Ctrl+G      - проверка последнего значения
#     Ctrl+J      - проверка активности элемента
#     Ctrl+R      - проверка фокуса элемента
#     Ctrl+T      - проверка состояния выбора элемента

from pynput import keyboard, mouse
import uiautomation as auto
import time
import os
import re
import queue
import threading
import ctypes
import ctypes.wintypes as _wintypes

# Win32 API для быстрой проверки (без COM)
_user32 = ctypes.windll.user32
_user32.WindowFromPoint.argtypes = [_wintypes.POINT]
_user32.WindowFromPoint.restype = _wintypes.HWND
_user32.GetWindowThreadProcessId.argtypes = [_wintypes.HWND, ctypes.POINTER(ctypes.c_ulong)]
_user32.GetWindowThreadProcessId.restype = ctypes.c_ulong

_kernel32 = ctypes.windll.kernel32
_kernel32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
_kernel32.OpenProcess.restype = _wintypes.HANDLE
_kernel32.QueryFullProcessImageNameW.argtypes = [_wintypes.HANDLE, ctypes.c_ulong, ctypes.c_wchar_p, ctypes.POINTER(ctypes.c_ulong)]
_kernel32.QueryFullProcessImageNameW.restype = ctypes.c_bool
_kernel32.CloseHandle.argtypes = [_wintypes.HANDLE]
_kernel32.CloseHandle.restype = ctypes.c_bool

from .token_fsm import Token, TokenCollector, TokenFSM


# Regex для определения суффиксов AutomationId
_SUFFIX_RE = re.compile(r'\.(Value|Dimensions|ComboBox|First|Second|Variant\d*)$')
_TITLE_SUFFIX_RE = re.compile(r'\.Title$')


# Основной класс рекордера пользовательских действий
class InputTracker:

    # Минимальный интервал между двумя кликами по одному элементу
    CLICK_DEBOUNCE_MS = 170 # мс
    # Минимальный интервал между событиями прокрутки
    SCROLL_DEBOUNCE_MS = 300 # мс
    # Заголовки окон, клики по которым игнорируются
    IGNORE_WINDOW_TITLES = ("microide",)
    # Имена exe-файлов, клики по окнам которых игнорируются
    IGNORE_PROCESS_NAMES = ("microide.exe",)

    def __init__(self):
        self.is_tracking = False       # активна ли запись в данный момент
        self.is_paused = False         # находимся ли в режиме паузы
        self.keyboard_listener = None  # слушатель pynput для клавиатуры
        self.mouse_listener = None     # слушатель pynput для мыши

        # Хранилище токенов и конечный автомат обработки сценария
        self.tokens = TokenCollector()
        self.processor = TokenFSM()

        # Время и идентификатор последнего клика/скролла – чтобы не записывать повторения
        self._last_click_time = 0
        self._last_click_element = None
        self._last_scroll_time = 0
        self._ctrl_pressed = False     # зажат ли Ctrl прямо сейчас
        self._should_stop = False      # сигнал остановки из callback-потока

        self.on_keyword = None         # GUI подключает свою функцию, чтобы получать ключевые слова
        self.on_pause_changed = None   # GUI подключает свою функцию, чтобы реагировать на паузу
        self._my_pid = os.getpid()     # PID процесса – чтобы не захватывать клики по собственному окну

        # Очередь между callback-потоками и worker: быстро положил – worker разберёт
        self._raw_queue = queue.Queue()
        self._worker_thread = None

        # Кэш имён и типов полей – живёт одну сессию, экономит обращения к UI Automation
        self._ui_cache = {
            "title_names": {},         # по BaseId хранится читаемое имя поля
            "is_combobox": {},         # по BaseId хранится признак выпадающего списка
        }

        # Pre-fetch при нажатии: при PRESS запускаем COM-захват в фоне,
        # чтобы к моменту UP результат был готов и не тормозил приложение
        self._pending_click = {}       # ключ (x,y,button) → захваченный info или None
        self._pending_lock = threading.Lock()

    # Быстрый захват UI-элемента под курсором, тяжёлые операции отложены в worker
    def _get_ui_info_fast(self, x, y, check_focus=False, check_selected=False):
        try:
            with auto.UIAutomationInitializerInThread():  # инициализируем COM для текущего потока pynput
                # получаем элемент под курсором 
                ctl = auto.ControlFromPoint(x, y)
                ctl_class = getattr(ctl, "ClassName", "")  
                auto_id = getattr(ctl, "AutomationId", None) or ""  

                info = {
                    "Name": getattr(ctl, "Name", None),             
                    "AutomationId": auto_id,                       
                    "ControlType": str(getattr(ctl, "ControlType", None)),  
                    "ClassName": ctl_class,                         
                    "IsEnabled": getattr(ctl, "IsEnabled", True),  
                }

                # BaseId – auto_id без суффикса (.Value, .Title, .ComboBox и т.д.)
                # нужен как ключ для кэша и для группировки связанных элементов одного поля
                if _SUFFIX_RE.search(auto_id):
                    info["BaseId"] = _SUFFIX_RE.sub('', auto_id)       # убираем суффикс типа .Value / .ComboBox
                elif _TITLE_SUFFIX_RE.search(auto_id):
                    info["BaseId"] = _TITLE_SUFFIX_RE.sub('', auto_id) # убираем суффикс .Title


                # Определяем, открыт ли диалог цифровой клавиатуры (DialogKeyPad)
                try:
                    # идём вверх по дереву от кликнутого элемента
                    top = ctl.GetTopLevelControl()  # корневое окно, которому принадлежит элемент
                    if getattr(top, "ClassName", "") == "DialogKeyPad":
                        info["DialogKeyPad"] = {"Title": getattr(top, "Name", ""), "ClassName": "DialogKeyPad"}
                    else:
                        # запасной вариант - текущее активное окно
                        win = auto.GetForegroundControl()
                        if getattr(win, "ClassName", "") == "DialogKeyPad":
                            info["DialogKeyPad"] = {"Title": getattr(win, "Name", ""), "ClassName": "DialogKeyPad"}
                except Exception:
                    pass

                # Для радиокнопок запоминаем AutomationId родительской группы,
                # иначе при воспроизведении нельзя однозначно найти нужную кнопку
                if ctl_class == "QRadioButton":
                    try:
                        parent = ctl.GetParentControl()  # быстрая операция - один шаг вверх по дереву
                        if parent:
                            info["ParentAutomationId"] = getattr(parent, "AutomationId", "")
                    except Exception:
                        pass

                # Проверяем, является ли элемент кнопкой закрытия вкладки.
                # Два варианта расположения в UIA-дереве:
                #   1) кнопка - child TabItem'а (parent.ControlType == TabItem)
                #   2) кнопка - sibling TabItem'а (оба child одного TabBar/TabControl)
                # Детектируем по Name=="X", ClassName кнопки, или по анонимному Button-элементу.
                _ct_str = info.get("ControlType", "")
                _is_close_candidate = (
                    info.get("Name") == "X" or
                    ctl_class in ("QToolButton", "QAbstractButton") or
                    # анонимный Button без имени и AutomationId (кнопка закрытия вкладки в Qt)
                    (not info.get("Name") and not auto_id and
                     ("Button" in _ct_str or "50000" in _ct_str))
                )
                if _is_close_candidate:
                    try:
                        parent = ctl.GetParentControl()
                        if parent:
                            parent_ctrl_type = str(getattr(parent, "ControlType", ""))
                            # Вариант 1: родитель — TabItem
                            if "TabItem" in parent_ctrl_type or "50019" in parent_ctrl_type:
                                info["ParentTabName"] = getattr(parent, "Name", "")
                            else:
                                # Вариант 2: ищем выбранный TabItem среди siblings
                                for sibling in (parent.GetChildren() or []):
                                    sib_type = str(getattr(sibling, "ControlType", ""))
                                    if "TabItem" in sib_type or "50019" in sib_type:
                                        try:
                                            sel = sibling.GetSelectionItemPattern()
                                            if sel and sel.IsSelected:
                                                info["ParentTabName"] = getattr(sibling, "Name", "")
                                                break
                                        except Exception:
                                            pass
                    except Exception:
                        pass

                # Проверка наличия фокуса (Ctrl+R) – только по явному запросу, иначе лишний COM-вызов
                if check_focus:
                    try:
                        info["HasFocus"] = ctl.HasKeyboardFocus  # есть ли у элемента фокус клавиатуры
                    except Exception:
                        info["HasFocus"] = False

                # Проверка выбранного состояния (Ctrl+T)
                if check_selected:
                    try:
                        pattern = ctl.GetSelectionItemPattern()  # паттерн выбора (элемент в списке)
                        if pattern:
                            info["IsSelected"] = pattern.IsSelected
                        else:
                            toggle = ctl.GetTogglePattern()      # паттерн переключения (чекбокс)
                            info["IsSelected"] = toggle.ToggleState == 1 if toggle else False
                    except Exception:
                        info["IsSelected"] = False

                return info
        except Exception:
            return {}  # вернём пустой словарь, если COM недоступен или окно закрылось

    # Ищет выбранный пункт выпадающего списка по координатам клика
    def _find_list_item_in_container(self, x, y):
        try:
            with auto.UIAutomationInitializerInThread():  # инициализируем COM для текущего потока
                ctl = auto.ControlFromPoint(x, y)         # элемент под курсором в момент клика

                # Qt оборачивает выпадающий список в контейнер QComboBoxPrivateContainer –
                # ControlFromPoint возвращает именно его, а не сам пункт списка
                if getattr(ctl, "ClassName", "") == "QComboBoxPrivateContainer":
                    try:
                        children = ctl.GetChildren()  # все дочерние элементы контейнера
                        for child in children:
                            child_ctrl_type = str(getattr(child, "ControlType", None))
                            if "ListItem" in child_ctrl_type or "50007" in child_ctrl_type:
                                try:
                                    rect = child.BoundingRectangle  # экранные координаты пункта

                                    # курсор попал в пункт
                                    if rect.left <= x <= rect.right and rect.top <= y <= rect.bottom:  
                                        return {
                                            "Name": getattr(child, "Name", None),
                                            "AutomationId": getattr(child, "AutomationId", None),
                                            "ControlType": child_ctrl_type,
                                            "ClassName": getattr(child, "ClassName", ""),
                                            "IsEnabled": getattr(child, "IsEnabled", True),
                                        }
                                except Exception:
                                    continue  # пункт исчез пока итерировали – пропускаем
                    except Exception:
                        pass

                # Запасной вариант - иногда ControlFromPoint сразу возвращает ListItem, минуя контейнер
                try:
                    list_item = auto.ControlFromPoint(x, y)
                    ctrl_type = str(getattr(list_item, "ControlType", None))
                    if "ListItem" in ctrl_type or "50007" in ctrl_type:  
                        return {
                            "Name": getattr(list_item, "Name", None),
                            "AutomationId": getattr(list_item, "AutomationId", None),
                            "ControlType": ctrl_type,
                            "ClassName": getattr(list_item, "ClassName", ""),
                            "IsEnabled": getattr(list_item, "IsEnabled", True),
                        }
                except Exception:
                    pass 
        except Exception:
            pass

        return None  # пункт не найден - список уже закрылся или клик был мимо

    # Проверяем через Win32 (без COM), принадлежит ли точка окну нашего процесса
    # или процессу из списка IGNORE_PROCESS_NAMES.
    # Вызывать до ControlFromPoint - если пользователь кликнул по окну самого рекордера, то подвисание
    def _is_point_on_self(self, x, y) -> bool:
        try:
            hwnd = _user32.WindowFromPoint(_wintypes.POINT(x, y))  # окно под курсором
            if hwnd:
                pid = ctypes.c_ulong(0)
                _user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))  # PID владельца окна
                if pid.value == self._my_pid:  # совпадает с нашим PID - клик по себе
                    return True
                # Проверяем имя exe-файла процесса
                if self.IGNORE_PROCESS_NAMES:
                    buf = ctypes.create_unicode_buffer(260)
                    size = ctypes.c_ulong(260)
                    h = _kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
                    if h:
                        _kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
                        _kernel32.CloseHandle(h)
                        proc_name = os.path.basename(buf.value).lower()
                        if proc_name in {n.lower() for n in self.IGNORE_PROCESS_NAMES}:
                            return True
        except Exception:
            pass
        return False

    # Ищет выбранную (активную) вкладку в дереве корневого окна
    # Вызывается из worker-потока, где COM уже инициализирован
    def _find_active_tab_name(self):
        try:
            win = self._root_win or auto.GetForegroundControl()
            if not win:
                return None

            def is_selected_tab(ctrl, _):
                ctrl_type = str(getattr(ctrl, "ControlType", ""))
                if not ("TabItem" in ctrl_type or "50019" in ctrl_type):
                    return False
                try:
                    sel = ctrl.GetSelectionItemPattern()
                    return sel is not None and sel.IsSelected
                except Exception:
                    return False

            result = auto.FindControl(win, is_selected_tab, maxDepth=10)
            if result:
                return getattr(result, "Name", "") or None
        except Exception:
            pass
        return None

    # Проверяем, является ли активное окно игнорируемым (например, окно самого рекордера)
    # Вызывается только из worker-потока, где COM уже инициализирован
    def _is_ignored_foreground(self) -> bool:
        try:
            # текущее активное окно
            win = auto.GetForegroundControl() 
            title = getattr(win, "Name", "") or ""
            return any(t in title for t in self.IGNORE_WINDOW_TITLES)  # заголовок совпадает со списком исключений
        except Exception:
            return False

    # При нажатии (PRESS) запускает COM-захват в фоновом потоке.
    # Пока пользователь удерживает кнопку, COM успевает получить info –
    # при отпускании (UP) данные уже готовы и новый COM-запрос не нужен.
    def _prefetch_on_press(self, x, y, key):
        with auto.UIAutomationInitializerInThread():  # COM для этого потока
            info = self._get_ui_info_fast(x, y)
            with self._pending_lock:
                self._pending_click[key] = info  # кладём результат – UP его заберёт

    # Возвращает pre-fetched info по ключу (x,y,button) и удаляет из словаря
    def _pop_pending(self, key):
        with self._pending_lock:
            return self._pending_click.pop(key, None)

    #--------------------------------------------------------------------------------------
    # Обработчики событий мыши и клавиатуры (поток pynput): только координаты/коды, без COM

    def _get_key_value(self, key):
        try:
            return key.char  # обычный символ (a, b, 1, ...)
        except AttributeError:
            return str(key).replace("Key.", "")  # специальная клавиша (ctrl, alt, ...)

    # Нажатие клавиши
    # Горячие клавиши обрабатываются немедленно, остальное – в очередь
    def on_key_press(self, key):
        # Фиксируем удержание Ctrl – влияет на обработку остальных клавиш
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self._ctrl_pressed = True
            return

        # В режиме паузы игнорируем все клавиши, кроме ESC и Enter (они в on_key_release)
        if self.is_paused or key in (keyboard.Key.esc, keyboard.Key.enter):
            return

        # Ctrl+W – записать закрытие текущей вкладки (CLOSE_TAB)
        if self._ctrl_pressed and hasattr(key, 'vk') and key.vk == 0x57:
            self._raw_queue.put(("CLOSE_TAB_ACTIVE", None, time.time()))
            return
        # Ctrl+G – проверить значение последнего элемента (CHECK)
        if self._ctrl_pressed and hasattr(key, 'vk') and key.vk == 0x47:
            self._raw_queue.put(("CHECK", None, time.time())) # для безопасной передачи данных между потоками
            return
        # Ctrl+J – проверить активность элемента под курсором (CHECK_ACTIVE)
        if self._ctrl_pressed and hasattr(key, 'vk') and key.vk == 0x4A:
            x, y = mouse.Controller().position
            info = self._get_ui_info_fast(x, y)
            self._raw_queue.put(("CHECK_ACTIVE", info, time.time()))
            return
        # Ctrl+R – получить фокус и проверить элемент (CHECK_FOCUS)
        if self._ctrl_pressed and hasattr(key, 'vk') and key.vk == 0x52:
            x, y = mouse.Controller().position
            info = self._get_ui_info_fast(x, y, check_focus=True)
            self._raw_queue.put(("CHECK_FOCUS", info, time.time()))
            return
        # Ctrl+T – проверить выбран ли элемент под курсором (CHECK_SELECTED)
        if self._ctrl_pressed and hasattr(key, 'vk') and key.vk == 0x54:
            x, y = mouse.Controller().position
            info = self._get_ui_info_fast(x, y, check_selected=True)
            self._raw_queue.put(("CHECK_SELECTED", info, time.time()))
            return

        # Обычное нажатие – помещаем токен Key Press в очередь
        self._raw_queue.put(("KP", self._get_key_value(key), time.time()))

    # Отпускание клавиши
    # ESC/Enter управляют паузой, остальное – KR-токен в очередь
    def on_key_release(self, key):
        # Снимаем флаг Ctrl при его отпускании
        if key in (keyboard.Key.ctrl_l, keyboard.Key.ctrl_r):
            self._ctrl_pressed = False
            return

        # ESC: если уже на паузе – запрос остановки, иначе – переход на паузу
        if key == keyboard.Key.esc:
            if self.is_paused:
                self._should_stop = True
            else:
                self._pause()
            return

        # Enter во время паузы – возобновить запись
        if key == keyboard.Key.enter and self.is_paused:
            self._resume()
            return

        if self.is_paused or key in (keyboard.Key.esc, keyboard.Key.enter):
            return
        if self._ctrl_pressed:
            return

        # Обычное отпускание – помещаем токен Key Release в очередь
        self._raw_queue.put(("KR", self._get_key_value(key), time.time()))

    # Клик мышью: на PRESS запускаем COM-захват в фоне, на UP используем готовый результат
    def on_mouse_click(self, x, y, button, pressed):
        if self.is_paused:
            return
        if self._is_point_on_self(x, y):  # проверяем до любых COM-вызовов
            return

        key = (x, y, str(button))

        if pressed:
            # запускаем захват в фоне – пока пользователь держит кнопку, COM успеет отработать
            threading.Thread(target=self._prefetch_on_press, args=(x, y, key), daemon=True).start()
            return

        # UP: берём то, что prefetch успел захватить за время удержания кнопки
        info = self._pop_pending(key) or self._get_ui_info_fast(x, y)  # fallback если не успел
        try:
            import datetime
            _log = os.path.join(os.path.expanduser("~"), "microide_click_debug.txt")
            with open(_log, "a", encoding="utf-8") as _f:
                _f.write(f"[{datetime.datetime.now().strftime('%H:%M:%S.%f')}] name={info.get('Name') if info else None!r} aid={info.get('AutomationId') if info else None!r} cls={info.get('ClassName') if info else None!r} ct={info.get('ControlType') if info else None!r} ptn={info.get('ParentTabName') if info else None!r}\n")
        except Exception:
            pass

        # Для выпадающего списка Qt – находим в контейнере реальный выбранный элемент
        if info and info.get("ClassName") == "QComboBoxPrivateContainer":
            list_item_info = self._find_list_item_in_container(x, y)
            if list_item_info:
                info = list_item_info

        # Пропускаем клики по неидентифицируемым элементам
        # (исключение: кнопка закрытия вкладки может не иметь имени, но ParentTabName уже есть)
        if not info or (not info.get("AutomationId") and not info.get("Name") and not info.get("ParentTabName")):
            return

        # Если кликнули по тому же элементу слишком быстро - игнорируем
        now = time.time() * 1000            # текущее время в миллисекундах
        elem_id = info.get("AutomationId") or info.get("Name")  # идентификатор элемента для сравнения

        if elem_id == self._last_click_element and now - self._last_click_time < self.CLICK_DEBOUNCE_MS:
            return  # слишком быстрый повтор – пропускаем
        
        self._last_click_time = now         # запоминаем время этого клика
        self._last_click_element = elem_id  # запоминаем элемент этого клика

        self._raw_queue.put(("CLICK", info, str(button), time.time()))  # передаём клик в worker

    # Обработчик прокрутки колёсика мыши
    def on_mouse_scroll(self, x, y, dx, dy):
        if self.is_paused:
            return
        if self._is_point_on_self(x, y):  # скролл по окну рекордера – игнорируем
            return

        # Защита от слишком частых событий скролла 
        now = time.time() * 1000      # текущее время в миллисекундах
        if now - self._last_scroll_time < self.SCROLL_DEBOUNCE_MS:
            return  # прошло слишком мало времени – пропускаем
        
        self._last_scroll_time = now  # запоминаем время этого скролла

        info = self._get_ui_info_fast(x, y)  # захватываем элемент под курсором
        self._raw_queue.put(("SCROLL", info, f"dx={dx}, dy={dy}", time.time()))  # dx – горизонталь, dy – вертикаль


    # Worker-поток: забираем события из очереди, дополняем UI-данными и передаем в FSM
    # Работает отдельно от callback'ов мыши, чтобы не тормозить их тяжёлыми операциями
    def _worker_loop(self):
        try:
            with auto.UIAutomationInitializerInThread():  # инициализируем COM для worker-потока
                self.processor.start_live()  # запускаем FSM в режиме живой записи

                # Крутимся пока идёт запись или в очереди есть необработанные события
                while self.is_tracking or not self._raw_queue.empty():
                    try:
                        event = self._raw_queue.get(timeout=0.15)  # ждём следующее событие 150 мс
                    except queue.Empty:
                        continue  # ничего не пришло – проверяем условие цикла заново

                    event_type = event[0]  # тип ("CLICK", "KP", "SCROLL" и т.д.)

                    try:
                        if event_type == "KP":
                            _, key_value, ts = event
                            t = Token("KP", key_value, timestamp=ts)  # токен нажатия клавиши
                            self.tokens.add(t)
                            self._feed_and_emit(t)  # отправляем в FSM и GUI

                        elif event_type == "KR":
                            _, key_value, ts = event
                            t = Token("KR", key_value, timestamp=ts)  # токен отпускания клавиши
                            self.tokens.add(t)
                            self._feed_and_emit(t)

                        elif event_type == "CHECK":
                            # Ctrl+G – проверка значения последнего элемента
                            _, _, ts = event
                            t = Token("CHECK", timestamp=ts)
                            self.tokens.add(t)
                            self._feed_and_emit(t)

                        elif event_type == "CLICK":
                            _, info, button, ts = event
                            # Игнорируем клики на элементы с именем из IGNORE_PROCESS_NAMES
                            # (напр. кнопка microide на панели задач — окно explorer.exe, не наш процесс)
                            elem_name = info.get("Name", "") or ""
                            if any(elem_name.startswith(proc) for proc in self.IGNORE_PROCESS_NAMES):
                                continue
                            self._enrich_info(info)  # дополняем info данными из кэша (TitleName, IsComboBox)
                            t = Token("CLICK", button, info, ts)
                            self.tokens.add(t)
                            self._feed_and_emit(t)

                        elif event_type == "SCROLL":
                            _, info, scroll_val, ts = event
                            self._enrich_info(info)  # дополняем info данными из кэша
                            t = Token("SCROLL", scroll_val, info, ts)
                            self.tokens.add(t)
                            self._feed_and_emit(t)

                        elif event_type == "CLOSE_TAB_ACTIVE":
                            # Ctrl+W – закрыть текущую вкладку: ищем выбранный TabItem в дереве
                            _, _, ts = event
                            tab_name = self._find_active_tab_name()
                            if tab_name:
                                t = Token("CLOSE_TAB", None, {"ParentTabName": tab_name}, ts)
                                self.tokens.add(t)
                                self._feed_and_emit(t)

                        elif event_type in ("CHECK_ACTIVE", "CHECK_FOCUS", "CHECK_SELECTED"):
                            # Ctrl+J/R/T – спецпроверки; пропускаем элементы без имени и AutomationId
                            _, info, ts = event
                            name = info.get("Name") or info.get("AutomationId")  # есть ли хоть какой-то идентификатор
                            if name:
                                t = Token(event_type, None, info, ts)
                                self.tokens.add(t)
                                self._feed_and_emit(t)

                    except Exception:
                        pass

                # Запись остановлена – даём FSM завершить незакрытые паттерны
                final_keywords = self.processor.finalize()  # получаем итоговые ключевые слова
                if final_keywords and getattr(self, "on_keyword", None):
                    for kw in final_keywords:
                        self.on_keyword(kw)  # передаём каждое ключевое слово в GUI

        except Exception:
            pass

    # Добавляет в info TitleName и признак выпадающего списка (IsComboBox)
    # Если уже есть в кэше – берём сразу, иначе – запускаем поиск фоном и не ждём
    def _enrich_info(self, info):
        auto_id = info.get("AutomationId", "")
        base_id = info.get("BaseId")  # AutomationId без суффикса (.Value, .Title и т.д.)
        class_name = info.get("ClassName", "")

        if not base_id:
            return

        if _SUFFIX_RE.search(auto_id):
            if base_id in self._ui_cache["title_names"]:
                cached = self._ui_cache["title_names"][base_id]
                if cached:
                    info["TitleName"] = cached  # уже известно – берём из кэша
            else:
                self._ui_cache["title_names"][base_id] = None  # отмечаем что уже ищем
                threading.Thread(
                    target=self._resolve_title_name_async,
                    args=(base_id,), daemon=True
                ).start()  # ищем в фоне, не блокируя основной поток

        if auto_id.endswith(".Title") or class_name == "QLabel":
            if base_id in self._ui_cache["is_combobox"]:
                if self._ui_cache["is_combobox"][base_id]:
                    info["IsComboBox"] = True  # уже известно – берём из кэша
            else:
                self._ui_cache["is_combobox"][base_id] = False  # отмечаем что уже ищем
                threading.Thread(
                    target=self._resolve_is_combobox_async,
                    args=(base_id,), daemon=True
                ).start()  # ищем в фоне, не блокируя основной поток

    # Ищет TitleName в фоне и сохраняет в кэш – следующий клик по этому полю уже возьмёт из кэша
    def _resolve_title_name_async(self, base_id):
        title_name = self._resolve_title_name(base_id)
        self._ui_cache["title_names"][base_id] = title_name

    # -----------------------------------------------------------------------------------------------
    # Разрешение UI-свойств через дерево Automation: поиск .Title и .ComboBox (только если еще не искали)

    # Ищем sibling-элемент с суффиксом .Title для получения человеко-читаемого имени
    def _resolve_title_name(self, base_id):
        try:
            title_id = base_id + ".Title"
            win = getattr(self, "_root_win", None) or auto.GetForegroundControl()
            if not win:
                return None
            result = self._find_element_by_auto_id(win, title_id, max_depth=7)
            if result:
                name = getattr(result, "Name", "")
                if name:
                    return name
        except Exception:
            pass
        return None

    # Фоновый поиск IsComboBox – результат кладётся в кэш для следующих кликов
    def _resolve_is_combobox_async(self, base_id):
        is_cb = self._resolve_is_combobox(base_id)
        self._ui_cache["is_combobox"][base_id] = is_cb  # запишем для следующего раза

    # Проверяем наличие sibling-элемента с суффиксом .ComboBox
    def _resolve_is_combobox(self, base_id):
        try:
            combobox_id = base_id + ".ComboBox"
            win = getattr(self, "_root_win", None) or auto.GetForegroundControl()
            if not win:
                return False
            result = self._find_element_by_auto_id(win, combobox_id, max_depth=7)
            if result:
                ctl_class = getattr(result, "ClassName", "")
                ctl_type = str(getattr(result, "ControlType", ""))
                if ctl_class == "QComboBox" or "ComboBox" in ctl_type or "50003" in ctl_type:
                    return True
        except Exception:
            pass
        return False

    # Поиск элемента по AutomationId в дереве UI (обход до max_depth уровней)
    def _find_element_by_auto_id(self, root, target_auto_id, max_depth=10):
        try:
            return auto.FindControl(
                root,
                lambda c, _d: getattr(c, "AutomationId", "") == target_auto_id,
                maxDepth=max_depth
            )
        except Exception:
            return None

    # Передаем токен в FSM и немедленно отправляет новые ключевые слова в GUI
    def _feed_and_emit(self, token):
        new_keywords = self.processor.feed(token)
        if new_keywords and getattr(self, "on_keyword", None):
            for kw in new_keywords:
                self.on_keyword(kw)

    # ----------------------------------------------------------------------------------------
    # Управление жизненным циклом записи
    # Запуск слушателей и worker-потока, остановка и пауза

    # Переводит запись в режим паузы и уведомляет GUI
    def _pause(self):
        if self.is_tracking and not self.is_paused:
            self.is_paused = True
            if self.on_pause_changed:
                self.on_pause_changed(True)

    # Возобновляет запись после паузы и уведомляет GUI
    def _resume(self):
        if self.is_paused:
            self.is_paused = False
            if self.on_pause_changed:
                self.on_pause_changed(False)

    # Начинает запись: запускает фоновый поток и подписывается на события ввода
    def start_tracking(self):
        if self.is_tracking:
            return

        self.is_tracking = True

        # Запоминаем активное окно как корень дерева UI для последующего поиска элементов
        with auto.UIAutomationInitializerInThread():
            self._root_win = auto.GetForegroundControl()

        # Запускаем фоновый поток обработки (daemon – завершится вместе с основным потоком)
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()

        # Подписываемся на события клавиатуры
        self.keyboard_listener = keyboard.Listener(
            on_press=self.on_key_press,
            on_release=self.on_key_release)
        self.keyboard_listener.start()

        # Подписываемся на события мыши
        self.mouse_listener = mouse.Listener(
            on_click=self.on_mouse_click,
            on_scroll=self.on_mouse_scroll)
        self.mouse_listener.start()

    # Останавливает запись: снимает слушателей, дожидается worker, сохраняет результаты
    def stop_tracking(self):
        if not self.is_tracking:
            return

        # Сигнализируем worker-потоку о завершении (он допустит опустошение очереди)
        self.is_tracking = False

        # Останавливаем слушатель клавиатуры
        if self.keyboard_listener:
            try:
                self.keyboard_listener.stop()
                self.keyboard_listener.join(timeout=1.0)
            except Exception:
                pass
            self.keyboard_listener = None

        # Останавливаем слушатель мыши
        if self.mouse_listener:
            try:
                self.mouse_listener.stop()
                self.mouse_listener.join(timeout=1.0)
            except Exception:
                pass
            self.mouse_listener = None

        # Ждём завершения worker: он должен обработать хвост очереди и вызвать finalize()
        if self._worker_thread:
            self._worker_thread.join(timeout=10.0)
            self._worker_thread = None

    # Полный цикл записи в блокирующем режиме
    def run(self):
        self.start_tracking()
        try:
            while self.is_tracking:
                if self._should_stop:
                    break
                time.sleep(0.1)
        except Exception:
            pass
        return self.stop_tracking()

    # Программная остановка записи из внешнего кода (без хоткея ESC+ESC)
    def request_stop(self):
        if self.is_tracking:
            self._should_stop = True
