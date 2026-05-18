import time
import re
from enum import Enum, auto


# Поля, в которых приложение отображает частоту с нулями
_FREQ_EXPAND_PARAMS = {
    "Center Frequency", "Span", "Start Frequency", "Stop Frequency", "CF Step",}

# Количество знаков после запятой для каждой единицы измерения частоты
_FREQ_DECIMAL_PLACES = {"GHz": 9, "MHz": 6, "kHz": 3}

# Преобразует введённое значение в отображаемый формат
def _expand_freq_value(value_str, dim):
    places = _FREQ_DECIMAL_PLACES.get(dim)
    if places is None:
        return value_str  # не частотная единица — оставляем как есть

    # Убираем пробелы внутри числа, заменяем запятую на точку
    normalized = value_str.replace(" ", "").replace(",", ".")
    try:
        val = float(normalized)
    except ValueError:
        return value_str  # не число — оставляем как есть

    # Форматируем с нужным количеством знаков после точки
    formatted = f"{val:.{places}f}" # например "13.000000000"
    int_part, frac_part = formatted.split(".")

    # Группируем дробную часть по 3 цифры через пробел
    groups = [frac_part[i:i+3] for i in range(0, len(frac_part), 3)]
    return f"{int_part},{' '.join(groups)}" # "13,000 000 000"


# Вспомогательные функции для извлечения имени элемента
def _is_numeric_value(s):
    if not s:
        return False
    cleaned = s.replace(" ", "").replace(",", ".").replace("−", "-")
    return bool(re.match(r'^-?\d+\.?\d*$', cleaned))


def _extract_name_from_auto_id(auto_id):
    if not auto_id:
        return None
    
    # Убираем суффиксы
    base_id = re.sub(r'\.(Value|Title|Dimensions|ComboBox|First|Second|Variant\d*)$', '', auto_id)
    parts = base_id.split(".")
    
    if parts:
        name = parts[-1].replace("_", " ")
        # CamelCase → "Camel Case"
        name = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', name)
        name = re.sub(r'([a-z])([A-Z])', r'\1 \2', name)
        return name.title()
    
    return None


def get_element_name(ctrl):
    if not ctrl:
        return None
    
    # Title - имя из соседнего .Title элемента
    title_name = ctrl.get("TitleName")
    if title_name:
        return title_name
    
    # Name - если не пустой и не числовое значение
    name = ctrl.get("Name", "")
    if name and not _is_numeric_value(name):
        return name
    
    # Fallback - вырезаем имя из AutomationId
    auto_id = ctrl.get("AutomationId", "")
    return _extract_name_from_auto_id(auto_id)


class Token:
    def __init__(self, token_type: str, value=None, control=None, timestamp=None):
        self.type = token_type  # KP, KR, CLICK, SCROLL, CHECK, CHECK_*
        self.value = value
        self.control = control or {}
        self.timestamp = timestamp or time.time()
        self.current_menu_section = None
    
    def __repr__(self):
        name = self.control.get("Name") or self.control.get("AutomationId") or ""
        
        if self.type in ("KP", "KR"):
            return f"{self.type} {self.value}"
        if self.type == "CLICK":
            return f"CLICK [{name}]" if name else "CLICK"
        if self.type == "SCROLL":
            return f"SCROLL {self.value}"
        if self.type in ("CHECK_ACTIVE", "CHECK_FOCUS", "CHECK_SELECTED", "CLOSE_TAB"):
            return f"{self.type} [{name}]" if name else self.type
        
        return f"{self.type} {self.value}"
    
    def to_dict(self):
        return {
            "type": self.type,
            "value": self.value,
            "control": self.control,
            "timestamp": self.timestamp
        }
        

class TokenCollector:
    def __init__(self):
        self.tokens = []
    
    def add(self, token: Token):
        self.tokens.append(token)
        print(f"[{len(self.tokens)}] {token}")
    
    def clear(self):
        self.tokens.clear()
    
    def to_dict_list(self):
        return [t.to_dict() for t in self.tokens]
    
    def print_all(self):
        print("\n" + "=" * 40)
        print("ТОКЕНЫ:")
        for i, t in enumerate(self.tokens, 1):
            print(f"  {i}. {t}")
        print("=" * 40)
    
    def __len__(self):
        return len(self.tokens)
    
    def __iter__(self):
        return iter(self.tokens)


# Состояния конечного автомата
class State(Enum):
    IDLE = auto()           # Ожидание начала паттерна
    VALUE_INPUT = auto()    # Ввод значения с размерностью
    DROPDOWN = auto()       # Выбор из выпадающего списка
    MENU = auto()           # Выбор секции меню
    CONFIGURATION = auto()  # Изменение конфигурации (Mode/Measurement)


def get_control_type(ctrl):
    if not ctrl:
        return None
    
    auto_id = ctrl.get("AutomationId", "")
    class_name = ctrl.get("ClassName", "")
    ctrl_type = ctrl.get("ControlType", "")
    name = ctrl.get("Name", "")
    has_keypad = bool(ctrl.get("DialogKeyPad"))
    
    # Поле ввода значения
    if auto_id.endswith(".Value") or class_name == "QLineEdit":
        return "value_field"
    
    # Title (кликабельный label с keypad)
    if class_name == "QLabel" and (has_keypad or auto_id.endswith(".Title")):
        return "title_keypad"
    
    # Кнопка цифры
    if class_name == "NumsBtn":
        return "digit"
    if has_keypad and name and (name.isdigit() or name in ".-,−"):
        return "digit"
    
    # Кнопка размерности
    if class_name == "UnitBtn": 
        return "dimension"
    
    # MenuComboBox (главное меню секций)
    if "MenuComboBox" in auto_id:
        return "menu_combobox"
    
    # ComboBox (выпадающий список)
    if class_name != "MenuComboBox" and ("ComboBox" in ctrl_type or "50003" in ctrl_type or auto_id.endswith(".ComboBox")):
        return "combobox"
    
    # ListItem (элемент списка)
    if "ListItem" in ctrl_type or "50007" in ctrl_type:
        return "list_item"
    
    # TabItem (вкладка)
    if "TabItem" in ctrl_type or "50019" in ctrl_type:
        return "tab"
    
    # Группа радиокнопок
    if ".First" in auto_id or ".Second" in auto_id or ".Variant" in auto_id or class_name == "QRadioButton":
        return "group"
    
    return None

# Конечный автомат для преобразования токенов в кейворды
class TokenFSM:
    def __init__(self):
        self.state = State.IDLE
        self.keywords = []
        
        # Контекст для VALUE_INPUT
        self.param_name = None
        self.digits = []
        
        # Контекст для DROPDOWN
        self.combobox_name = None
        
        # Контекст для CONFIGURATION
        self.config_mode = None
        self.config_measurement = None
        
        # Последнее установленное значение - для CHECK
        self.last_set = None
        
        # Отложенный Set Focus - генерируется только если не начался ввод
        self.pending_set_focus_element = None
    
    def reset(self):
        self.state = State.IDLE
        self.param_name = None
        self.digits = []
        self.combobox_name = None
        self.config_mode = None
        self.config_measurement = None
        self.pending_set_focus_element = None
    

    # Основной метод обработки
    def process(self, tokens):
        self.keywords = []
        self.reset()
        
        for token in tokens:
            self._handle(token)
        
        # Если запись закончилась в CONFIGURATION
        if self.state == State.CONFIGURATION:
            self._emit_configuration_keyword()
            self.reset()
        
        # Если остался отложенный Set Focus (ввод не начался), генерируем его
        if self.pending_set_focus_element:
            self.keywords.append(f"Set Focus    {self.pending_set_focus_element}")
            self.pending_set_focus_element = None
        
        return self.keywords
    
    def _handle(self, token):
        # CHECK-команды обрабатываются в любом состоянии
        if token.type == "CHECK":
            self._emit_check()
            return
        if token.type == "CHECK_ACTIVE":
            self._handle_check_active(token)
            return
        if token.type == "CHECK_FOCUS":
            self._handle_check_focus(token)
            return
        if token.type == "CHECK_SELECTED":
            self._handle_check_selected(token)
            return
        if token.type == "CLOSE_TAB":
            tab_name = token.control.get("ParentTabName", "")
            if tab_name:
                self.keywords.append(f"Base Close Tab    {tab_name}")
            return

        # Диспетчеризация по состоянию
        handlers = {
            State.IDLE: self._handle_idle,
            State.VALUE_INPUT: self._handle_value_input,
            State.DROPDOWN: self._handle_dropdown,
            State.MENU: self._handle_menu,
            State.CONFIGURATION: self._handle_configuration,
        }
        handler = handlers.get(self.state)
        if handler:
            handler(token)
    
    # Обработчики CHECK-команд
    def _emit_check(self):
        if not self.last_set:
            return
        
        t = self.last_set["type"]
        if t == "value":
            param = self.last_set['param']
            value = self.last_set['value']
            dim   = self.last_set['dim']
            # Для частотных полей преобразуем значение в формат отображения приложения
            if param in _FREQ_EXPAND_PARAMS:
                value = _expand_freq_value(value, dim)
            self.keywords.append(
                f"Get Value With Dimension And Check    {param}    {value}    {dim}"
            )
        elif t == "dropdown":
            self.keywords.append(
                f"Check Selected Value    {self.last_set['combobox']}    {self.last_set['item']}"
            )
        elif t == "group":
            self.keywords.append(
                f"Check Selected Value In Group    {self.last_set['group']}    {self.last_set['variant']}"
            )
    
    # Is Element Active
    def _handle_check_active(self, token):
        name = self._get_button_name(token.control)
        if name:
            status = "${True}" if token.control.get("IsEnabled", True) else "${False}"
            self.keywords.append(f"Is Element Active    {name}    {status}")
    
    # Get Focus And Check
    def _handle_check_focus(self, token):
        name = token.control.get("Name") or token.control.get("AutomationId")
        if name:
            status = "${True}" if token.control.get("HasFocus", False) else "${False}"
            self.keywords.append(f"Get Focus And Check    {name}    {status}")
    
    # Is Element Selected
    def _handle_check_selected(self, token):
        name = token.control.get("Name") or token.control.get("AutomationId")
        if name:
            status = "${True}" if token.control.get("IsSelected", False) else "${False}"
            self.keywords.append(f"Is Element Selected    {name}    {status}")
    
    # IDLE - ожидание начала паттерна
    def _handle_idle(self, token):
        # Обработка стрелок вверх/вниз - генерируем BasePressKey
        if token.type == "KP":
            if token.value == "up":
                self.keywords.append("BasePressKey    {VK_UP}")
                return
            if token.value == "down":
                self.keywords.append("BasePressKey    {VK_DOWN}")
                return
        
        if token.type != "CLICK":
            return
        
        ctrl = token.control
        name = ctrl.get("Name", "")
        auto_id = ctrl.get("AutomationId", "")
        parent_auto_id = ctrl.get("ParentAutomationId", "")
        
        ct = get_control_type(ctrl)
        class_name = ctrl.get("ClassName", "")
        
        # Change Configuration (LeftButton или радиокнопки Mode/Measurement)
        if "LeftButton" in auto_id or "SelectMode" in parent_auto_id or "SelectMeasurement" in parent_auto_id:
            self.state = State.CONFIGURATION
            self.config_mode = None
            self.config_measurement = None
            if "LeftButton" not in auto_id:
                self._handle_configuration(token)
            return
        
        # Set Focus для .Dimensions элементов (клик на размерность)
        if auto_id.endswith(".Dimensions"):
            element_name = get_element_name(ctrl)
            if element_name:
                self.keywords.append(f"Set Focus    {element_name}")
                return
        
        # Set Focus для кнопок параметров (.Title) - отложенная генерация
        # Если после клика начнется ввод, Set Focus не нужен
        if auto_id.endswith(".Title") or (class_name == "QLabel" and auto_id.endswith(".Title")):
            # Проверяем, является ли это частью ComboBox (выпадающий список)
            element_name = get_element_name(ctrl)
            title_name = ctrl.get("TitleName", "")
            name_to_check = element_name or title_name or ""
            
            # Главное меню секций должно идти в MENU, а не в DROPDOWN
            if ctrl.get("ClassName") == "MenuComboBox" or "MenuComboBox" in (ctrl.get("AutomationId", "") or ""):
                self.state = State.MENU
                return

            # Автоматическое определение через UI Automation API
            # Если в info есть флаг IsComboBox, значит это выпадающий список
            # Флаг устанавливается в microide.py при проверке наличия соответствующего .ComboBox элемента
            is_combobox = ctrl.get("IsComboBox", False)
            if is_combobox:
                self.state = State.DROPDOWN
                self.combobox_name = name_to_check
                return
            
            # Если не выпадающий список, обрабатываем как поле ввода
            # Если был предыдущий отложенный Set Focus, генерируем его (смена элемента)
            if self.pending_set_focus_element and self.pending_set_focus_element != element_name:
                self.keywords.append(f"Set Focus    {self.pending_set_focus_element}")
            if element_name:
                # Сохраняем элемент для возможной генерации Set Focus
                self.pending_set_focus_element = element_name
            # Переходим в состояние VALUE_INPUT для обработки следующих токенов
            # (если будет ввод - Set Focus отменится, если нет - сгенерируется)
            self.state = State.VALUE_INPUT
            self.param_name = self._extract_param_name(ctrl)
            self.digits = []
            return
        
        # Set Focus для .Value элементов (клик на поле значения)
        # После клика на .Value должен открыться keypad, переходим в VALUE_INPUT
        # Set Focus генерируем только если не начался ввод (отложенная генерация)
        if auto_id.endswith(".Value"):
            element_name = get_element_name(ctrl)
            # Если был предыдущий отложенный Set Focus, генерируем его (смена элемента)
            if self.pending_set_focus_element and self.pending_set_focus_element != element_name:
                self.keywords.append(f"Set Focus    {self.pending_set_focus_element}")
            # Сохраняем элемент для возможной генерации Set Focus
            # (будет сгенерирован только если не начался ввод)
            if element_name:
                self.pending_set_focus_element = element_name
            # Переходим в состояние VALUE_INPUT для обработки следующих токенов (цифры, размерность)
            self.state = State.VALUE_INPUT
            self.param_name = self._extract_param_name(ctrl)
            self.digits = []
            return
        
        # Начало ввода значения (только если открыт keypad)
        if ct == "title_keypad":
            self.state = State.VALUE_INPUT
            self.param_name = self.param_name or self._extract_param_name(ctrl)
            self.digits = []
            return
        
        # Начало выбора из Drop-Down
        if ct == "combobox":
            self.state = State.DROPDOWN
            self.combobox_name = self._extract_combobox_name(ctrl)
            return
        
        # Начало выбора секции меню
        if ct == "menu_combobox":
            self.state = State.MENU
            return
        
        # Группа radiobutton - сразу киворд
        if ct == "group":
            group = self._extract_group_name(ctrl)
            variant = ctrl.get("Name", "")
            if group and variant:
                self.keywords.append(f"Set Selected Value In Group    {group}    {variant}")
                self.last_set = {"type": "group", "group": group, "variant": variant}
            return
        
        # Tab - сразу сразу киворд
        if ct == "tab":
            if name == "+" or name.lower() == "new tab":
                self.keywords.append("Click    New Tab")
            else:
                self.keywords.append(f"Click Tab    {name}")
            return

        # Закрытие вкладки: кнопка (Name="X", QToolButton или пустое имя),
        # у которой microide.py определил ParentTabName через UIA-дерево
        if ctrl.get("ParentTabName"):
            self.keywords.append(f"Base Close Tab    {ctrl['ParentTabName']}")
            return
        # X без ParentTabName — кнопка диалога, молча игнорируем
        if name == "X":
            return

        # Пропускаем служебные элементы
        if ct in ("digit", "dimension", "list_item"):
            return
        
        # Обычный клик
        kw = self._make_simple_click(ctrl)
        if kw:
            self.keywords.append(kw)
    

    # VALUE_INPUT - ввод значения с размерностью
    def _handle_value_input(self, token):
        # Нажатие клавиши - добавляем цифру
        if token.type == "KP":
            if token.value and (token.value.isdigit() or token.value in ".-,−"):
                # Начался ввод - отменяем отложенный Set Focus
                self.pending_set_focus_element = None
                self.digits.append(token.value.replace(",", ".").replace("−", "-"))
            return
        
        # Отпускание клавиши - игнорируем
        if token.type == "KR":
            return
        
        # Клик
        if token.type == "CLICK":
            ctrl = token.control
            ct = get_control_type(ctrl)
            name = ctrl.get("Name", "")
            
            # Повторный клик на поле ввода или кнопку параметра (.Title)
            # Проверяем, это тот же элемент или другой
            auto_id = ctrl.get("AutomationId", "")
            class_name = ctrl.get("ClassName", "")
            current_element_name = get_element_name(ctrl)
            
            if ct in ("value_field", "title_keypad") or auto_id.endswith(".Title") or (class_name == "QLabel" and auto_id.endswith(".Title")) or auto_id.endswith(".Value"):
                # Если это другой элемент - генерируем Set Focus для предыдущего и обрабатываем новый клик в IDLE
                if self.pending_set_focus_element and current_element_name and self.pending_set_focus_element != current_element_name:
                    self.keywords.append(f"Set Focus    {self.pending_set_focus_element}")
                    # Сбрасываем состояние и обрабатываем новый клик в IDLE
                    self.reset()
                    self._handle_idle(token)
                    return
                # Если это тот же элемент - отменяем отложенный Set Focus (повторный клик для открытия keypad)
                elif self.pending_set_focus_element == current_element_name:
                    self.pending_set_focus_element = None
                # Если не было предыдущего элемента, сохраняем текущий
                elif not self.pending_set_focus_element and current_element_name:
                    self.pending_set_focus_element = current_element_name
                
                self.param_name = self.param_name or self._extract_param_name(ctrl)
                return
            
            # Клик на цифру - начался ввод, отменяем отложенный Set Focus
            if ct == "digit":
                self.pending_set_focus_element = None
                self.digits.append(name.replace(",", ".").replace("−", "-"))
                self.param_name = self.param_name or self._extract_param_name(ctrl)
                return
            
            # Клик на размерность - завершаем паттерн
            if ct == "dimension" or (ctrl.get("DialogKeyPad") and name):
                # Начался ввод (размерность) - отменяем отложенный Set Focus
                self.pending_set_focus_element = None
                self.param_name = self.param_name or self._extract_param_name(ctrl)
                value = "".join(self.digits) or "0"
                # Используем get_element_name для получения правильного имени размерности
                dim_name = get_element_name(ctrl) or name
                if not dim_name:
                    # Если имя все еще пустое, пытаемся получить из Name
                    dim_name = name or "Unknown"
                self.keywords.append(
                    f"Set Value With Dimension    {self.param_name or 'Unknown'}    {value}    {dim_name}"
                )
                self.last_set = {
                    "type": "value",
                    "param": self.param_name or "Unknown",
                    "value": value,
                    "dim": dim_name
                }
                self.reset()
                return
            
            # Другой клик - отменяем паттерн
            # Если был отложенный Set Focus, генерируем его перед reset
            pending_focus = self.pending_set_focus_element
            self.reset()
            if pending_focus:
                self.keywords.append(f"Set Focus    {pending_focus}")
            # Обрабатываем новый токен в IDLE
            self._handle_idle(token)
            return
        
        # Другой тип токена - отменяем паттерн
        # Если был отложенный Set Focus, генерируем его перед reset
        pending_focus = self.pending_set_focus_element
        self.reset()
        if pending_focus:
            self.keywords.append(f"Set Focus    {pending_focus}")
    

    # DROPDOWN - выбор из выпадающего списка
    def _handle_dropdown(self, token):
        if token.type == "CLICK":
            ctrl = token.control
            ct = get_control_type(ctrl)
            
            # Выбор элемента списка - завершаем паттерн
            if ct == "list_item":
                item_name = ctrl.get("Name", "")
                
                # Проверка: если это Selected Marker и выбран Marker N, то генерируем Select and Check Marker
                combobox_name = self.combobox_name or ""
                is_selected_marker = (
                    "Selected Marker" in combobox_name or 
                    "SelectedMarker" in combobox_name or
                    combobox_name == "Selected Marker"
                )
                is_marker_item = item_name and item_name.startswith("Marker")
                
                if is_selected_marker and is_marker_item:
                    self.keywords.append(f"Select and Check Marker    {item_name}")
                else:
                    self.keywords.append(f"Drop-Down List Set    {self.combobox_name}    {item_name}")
                
                self.last_set = {"type": "dropdown", "combobox": self.combobox_name, "item": item_name}
                self.reset()
                return
        
        # Любой другой токен - отменяем и обрабатываем заново
        self.reset()
        self._handle(token)
    

    # MENU - выбор секции меню
    def _handle_menu(self, token):
        if token.type == "CLICK":
            ctrl = token.control
            ct = get_control_type(ctrl)
            
            # Выбор элемента списка - завершаем паттерн
            if ct == "list_item":
                section_name = ctrl.get("Name", "")
                self.keywords.append(f"Change Menu Section    {section_name}")
                self.reset()
                return
        
        # Любой другой токен - отменяем и обрабатываем заново
        self.reset()
        self._handle(token)
    
    # CONFIGURATION - изменение конфигурации (Mode/Measurement)
    def _handle_configuration(self, token):
        if token.type != "CLICK":
            return
        
        ctrl = token.control
        auto_id = ctrl.get("AutomationId", "")
        parent_auto_id = ctrl.get("ParentAutomationId", "")
        name = ctrl.get("Name", "")
        class_name = ctrl.get("ClassName", "")
        
        # Клик на LeftButton - диалог закрылся
        if "LeftButton" in auto_id:
            self._emit_configuration_keyword()
            self.reset()
            return
        
        # Клик на радиокнопку Mode/Measurement
        if class_name == "QRadioButton":
            if "SelectMode" in parent_auto_id:
                self.config_mode = name
                return
            if "SelectMeasurement" in parent_auto_id:
                self.config_measurement = name
                return
        
        # Клик на OK
        if name == "OK" or "content.OK" in auto_id:
            self._emit_configuration_keyword()
            self.reset()
            return

        # Клик на X (кнопка закрытия диалога) - выходим без генерации keyword
        if name == "X":
            self._emit_configuration_keyword()
            self.reset()
            return

        # Любой другой клик - выходим и обрабатываем
        self._emit_configuration_keyword()
        self.reset()
        self._handle_idle(token)
    
    # Генерация keyword Change Configuration
    def _emit_configuration_keyword(self):
        if self.config_mode and self.config_measurement:
            self.keywords.append(f"Change Configuration    {self.config_mode}    {self.config_measurement}")
    
    
    # Вспомогательные методы
    # Извлечение имени параметра из контрола или keypad
    def _extract_param_name(self, ctrl):
        if not ctrl:
            return None
        keypad = ctrl.get("DialogKeyPad")
        if keypad:
            return keypad.get("Title")
        return ctrl.get("Name")
    
    # Получение имени комбобокса из UI
    def _extract_combobox_name(self, ctrl):
        if not ctrl:
            return ""
        return get_element_name(ctrl) or ""
    
    # Получение имени группы радиокнопок из UI
    def _extract_group_name(self, ctrl):
        if not ctrl:
            return None
        # Сначала TitleName (если есть)
        title_name = ctrl.get("TitleName")
        if title_name:
            return title_name
        # Иначе вырезаем из AutomationId
        auto_id = ctrl.get("AutomationId", "")
        return _extract_name_from_auto_id(auto_id)
    
    # Получение имени кнопки из UI
    def _get_button_name(self, ctrl):
        if not ctrl:
            return None
        return get_element_name(ctrl) or ctrl.get("AutomationId", "")
    
    # Генерация keyword для простого клика или Set Focus
    def _make_simple_click(self, ctrl):
        if not ctrl:
            return None
        
        name = ctrl.get("Name", "")
        auto_id = ctrl.get("AutomationId", "")
        ctrl_type = ctrl.get("ControlType", "")
        class_name = ctrl.get("ClassName", "")
        
        # Игнорируем служебные элементы
        if not name:
            return None
        if ctrl_type in ("ControlType.Window", "ControlType.TitleBar", "ControlType.MenuBar"):
            return None
        if name.startswith("ArkGUIViewer.exe") or name == "Menu Section" or name == "ArkGUIViewer" or name == "X":
            return None
        # Игнорируем контейнеры выпадающих списков (QComboBoxPrivateContainer)
        if class_name == "QComboBoxPrivateContainer":
            return None
        
        # Специальный случай: Mode Preset
        if "ModePreset" in auto_id or name == "Mode Preset":
            return "Set Mode Preset P"
        
        return f"Click    {name}"

    def print_keywords(self):
        print("\n" + "=" * 40)
        print("KEYWORDS:")
        for kw in self.keywords:
            print(f"    {kw}")
        print("=" * 40)

    # Подготовка FSM к потоковой обработке токенов
    def start_live(self):
        self.keywords = []
        self.reset()

    # Обработка одного токена → новые keywords
    def feed(self, token):
        before = len(self.keywords)
        self._handle(token)
        after = len(self.keywords)
        if after > before:
            return self.keywords[before:after]
        return []

    # Завершение незакрытых паттернов при остановке записи
    def finalize(self):
        new = []

        # Если запись закончилась в CONFIGURATION
        if self.state == State.CONFIGURATION:
            before = len(self.keywords)
            self._emit_configuration_keyword()
            self.reset()
            if len(self.keywords) > before:
                new.extend(self.keywords[before:])

        # Если остался отложенный Set Focus
        if getattr(self, "pending_set_focus_element", None):
            new.append(f"Set Focus    {self.pending_set_focus_element}")
            self.keywords.append(new[-1])
            self.pending_set_focus_element = None

        return new


  