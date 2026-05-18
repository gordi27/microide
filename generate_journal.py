"""
Генератор журнала преддипломной практики
Гордеева Мария Дмитриевна, М30-411Б-22
"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

TNR = 'Times New Roman'

# ─────────────────────── helpers ───────────────────────

def _set_run_font(run, name=TNR, size=14, bold=False, italic=False, underline=False):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.underline = underline
    rPr = run._r.get_or_add_rPr()
    rf = OxmlElement('w:rFonts')
    rf.set(qn('w:ascii'), name); rf.set(qn('w:hAnsi'), name); rf.set(qn('w:cs'), name)
    # insert before existing rFonts if any
    existing = rPr.find(qn('w:rFonts'))
    if existing is not None:
        rPr.remove(existing)
    rPr.insert(0, rf)


def _para_fmt(para, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=1.25,
              before=0, after=6, ls=1.5):
    pf = para.paragraph_format
    pf.alignment = align
    pf.first_line_indent = Cm(indent) if indent else None
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = ls


def p(doc, text='', align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=1.25,
      size=14, bold=False, italic=False, underline=False,
      before=0, after=6, ls=1.5):
    para = doc.add_paragraph()
    _para_fmt(para, align, indent, before, after, ls)
    if text:
        run = para.add_run(text)
        _set_run_font(run, size=size, bold=bold, italic=italic, underline=underline)
    return para


def p_mixed(doc, parts, align=WD_ALIGN_PARAGRAPH.JUSTIFY, indent=None,
            before=0, after=6, ls=1.5):
    """parts = list of (text, bold, underline, size, italic)"""
    para = doc.add_paragraph()
    _para_fmt(para, align, indent, before, after, ls)
    for part in parts:
        text = part[0]
        bold = part[1] if len(part) > 1 else False
        underline = part[2] if len(part) > 2 else False
        size = part[3] if len(part) > 3 else 14
        italic = part[4] if len(part) > 4 else False
        run = para.add_run(text)
        _set_run_font(run, size=size, bold=bold, italic=italic, underline=underline)
    return para


def heading(doc, text, align=WD_ALIGN_PARAGRAPH.LEFT, size=14, bold=True, before=12, after=6):
    para = doc.add_paragraph()
    _para_fmt(para, align, indent=None, before=before, after=after)
    run = para.add_run(text)
    _set_run_font(run, size=size, bold=bold)
    return para


def page_break(doc):
    para = doc.add_paragraph()
    _para_fmt(para, indent=None, before=0, after=0)
    run = para.add_run()
    run.add_break(WD_BREAK.PAGE)


def sig_line(doc, label, name_u='', slash=True, date_blank=True, size=12, before=6, after=3):
    """Строка подписи: метка  имя(подчёркнутое) /___/ дата"""
    para = doc.add_paragraph()
    _para_fmt(para, align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, before=before, after=after, ls=1.2)
    run = para.add_run(label)
    _set_run_font(run, size=size)
    if name_u:
        run2 = para.add_run(name_u)
        _set_run_font(run2, size=size, underline=True)
    if slash:
        run3 = para.add_run('    /                    /    ')
        _set_run_font(run3, size=size)
    if date_blank:
        run4 = para.add_run('«___» ____________ 2026 г.')
        _set_run_font(run4, size=size)
    return para


def sig_line2(doc, label, name_u, size=12, before=3, after=3):
    """Строка подписи без даты (только имя / подпись /)"""
    para = doc.add_paragraph()
    _para_fmt(para, align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, before=before, after=after, ls=1.2)
    r1 = para.add_run(label)
    _set_run_font(r1, size=size)
    r2 = para.add_run(name_u)
    _set_run_font(r2, size=size, underline=True)
    r3 = para.add_run('    /                    /')
    _set_run_font(r3, size=size)
    return para


def caption(doc, text, size=12):
    para = doc.add_paragraph()
    _para_fmt(para, align=WD_ALIGN_PARAGRAPH.CENTER, indent=None, before=3, after=6)
    run = para.add_run(text)
    _set_run_font(run, size=size, italic=True)
    return para


def set_col_width(table, col_idx, width_cm):
    for row in table.rows:
        row.cells[col_idx].width = Cm(width_cm)


def set_margins(doc, top=2, bottom=2, left=3, right=1.5):
    s = doc.sections[0]
    s.top_margin = Cm(top)
    s.bottom_margin = Cm(bottom)
    s.left_margin = Cm(left)
    s.right_margin = Cm(right)


# ─────────────────────── main ───────────────────────

def build():
    doc = Document()
    set_margins(doc)

    # ══════════════════════════════════════════════════
    # ТИТУЛЬНЫЙ ЛИСТ
    # ══════════════════════════════════════════════════
    p(doc, 'ФЕДЕРАЛЬНОЕ ГОСУДАРСТВЕННОЕ БЮДЖЕТНОЕ ОБРАЗОВАТЕЛЬНОЕ УЧРЕЖДЕНИЕ '
           'ВЫСШЕГО ОБРАЗОВАНИЯ «МОСКОВСКИЙ АВИАЦИОННЫЙ ИНСТИТУТ '
           '(НАЦИОНАЛЬНЫЙ ИССЛЕДОВАТЕЛЬСКИЙ УНИВЕРСИТЕТ)»',
      align=WD_ALIGN_PARAGRAPH.CENTER, indent=None, bold=True, size=14, before=0, after=6)

    for _ in range(4):
        p(doc, indent=None, after=0)

    p(doc, 'Журнал по практике', align=WD_ALIGN_PARAGRAPH.CENTER,
      indent=None, bold=True, size=16, before=0, after=60)

    for _ in range(3):
        p(doc, indent=None, after=0)

    p_mixed(doc, [
        ('Обучающийся    ', False, False, 14),
        ('Гордеева Мария Дмитриевна', False, True, 14),
        ('                        (Ф.И.О.)', False, False, 12, True),
    ], align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, after=4)

    p_mixed(doc, [
        ('Институт №3 ', False, False, 14),
        ('«Системы управления, информатика и электроэнергетика»', False, True, 14),
    ], align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, after=4)

    p_mixed(doc, [
        ('Кафедра №304 ', False, False, 14),
        ('«Вычислительные машины, системы и сети»', False, True, 14),
    ], align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, after=4)

    p_mixed(doc, [
        ('Учебная группа    ', False, False, 14),
        ('М30-411Б-22', False, True, 14),
    ], align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, after=4)

    p_mixed(doc, [
        ('Направление подготовки (специальность)    ', False, False, 14),
        ('09.03.04', False, True, 14),
    ], align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, after=0)

    p(doc, '                                                                              (шифр)',
      align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, size=12, italic=True, after=0)

    # ugly but works for centered underlined name
    p_mixed(doc, [
        ('                                              ', False, False, 14),
        ('«Программная инженерия»', False, True, 14),
    ], align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, after=0)

    p(doc, '                             (наименование направления, специальности)',
      align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, size=12, italic=True, after=8)

    p_mixed(doc, [
        ('Вид практики    ', False, False, 14),
        ('Преддипломная', False, True, 14),
    ], align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, after=0)

    p(doc, '              (учебная, производственная, преддипломная или другой вид практики)',
      align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, size=12, italic=True, after=12)

    p(doc, 'Руководитель практики от МАИ', align=WD_ALIGN_PARAGRAPH.LEFT,
      indent=None, size=14, after=4)

    p_mixed(doc, [
        ('    ', False, False, 14),
        ('Ведьманов Илья Сергеевич', False, True, 14),
        ('    /                    /', False, False, 14),
    ], align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, after=0)

    p(doc, '              (фамилия, имя, отчество)                     (подпись)',
      align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, size=12, italic=True, after=12)

    p(doc, 'Обучающийся', align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, size=14, after=4)

    p_mixed(doc, [
        ('    ', False, False, 14),
        ('Гордеева Мария Дмитриевна', False, True, 14),
        ('    /                    /   ', False, False, 14),
        ('«___» ____________ 2026 г.', False, False, 14),
    ], align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, after=0)

    p(doc, '              (фамилия, имя, отчество)                     (подпись)                  (дата)',
      align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, size=12, italic=True, after=30)

    p(doc, 'Москва 2026 г.', align=WD_ALIGN_PARAGRAPH.CENTER,
      indent=None, size=14, after=0)

    page_break(doc)

    # ══════════════════════════════════════════════════
    # РАЗДЕЛ 1 — МЕСТО И СРОКИ
    # ══════════════════════════════════════════════════
    heading(doc, '1. Место и сроки проведения практики', before=6)

    p(doc, 'Сроки проведения практики:', indent=None, after=4)

    p_mixed(doc, [
        ('– дата начала практики:    ', False, False, 14),
        ('09.02.2026', False, True, 14),
    ], indent=None, after=4)

    p_mixed(doc, [
        ('– дата окончания практики:    ', False, False, 14),
        ('23.05.2026', False, True, 14),
    ], indent=None, after=4)

    p_mixed(doc, [
        ('Наименование организации:    ', False, False, 14),
        ('Федеральное государственное унитарное предприятие '
         '«Научно-производственное предприятие «Гамма»» (ФГУП «НПП «Гамма»»)', False, True, 14),
    ], indent=None, after=4)

    p_mixed(doc, [
        ('Название структурного подразделения:    ', False, False, 14),
        ('Проектно-конструкторский департамент, отдел специального программного обеспечения',
         False, True, 14),
    ], indent=None, after=8)

    # ══════════════════════════════════════════════════
    # РАЗДЕЛ 2 — ИНСТРУКТАЖ
    # ══════════════════════════════════════════════════
    heading(doc, '2. Инструктаж по технике безопасности', before=8)

    sig_line(doc, '', size=14)
    p_mixed(doc, [
        ('    (подпись проводившего)                              ', False, False, 12, True),
        ('                                               (дата проведения)', False, False, 12, True),
    ], indent=None, after=8)

    # ══════════════════════════════════════════════════
    # РАЗДЕЛ 3 — ИНДИВИДУАЛЬНОЕ ЗАДАНИЕ
    # ══════════════════════════════════════════════════
    heading(doc, '3. Индивидуальное задание студенту', before=8)

    task = (
        'Разработать подсистему генерации сценариев автоматизированного тестирования '
        'интерфейса специального программного обеспечения (СПО) анализаторов спектра '
        'СК4-МАХ4 и СК4-МАХ6 на основе захвата пользовательских действий. '
        'В рамках работы необходимо: изучить объект тестирования и требования к разрабатываемой '
        'подсистеме; спроектировать архитектуру подсистемы и выбрать инструменты разработки '
        '(Python, pynput, Windows UI Automation API, Robot Framework, PySide6); '
        'реализовать модуль захвата событий клавиатуры и мыши с идентификацией элементов '
        'графического интерфейса посредством Windows UI Automation API; '
        'реализовать модуль обработки захваченных событий на основе конечного автомата '
        'для формирования ключевых слов Robot Framework, соответствующих типовым операциям '
        'над элементами СПО; разработать графический интерфейс пользователя '
        'на базе фреймворка PySide6 для управления сеансом записи и отображения '
        'сгенерированных сценариев; провести интеграционное тестирование подсистемы '
        'на реальном объекте — СПО анализаторов спектра СК4-МАХ4 и СК4-МАХ6.'
    )
    p(doc, task, indent=1.25, after=8)

    sig_line2(doc, 'Руководитель практики от МАИ    ', 'Ведьманов Илья Сергеевич')
    sig_line(doc, 'Обучающийся    ', 'Гордеева Мария Дмитриевна')

    page_break(doc)

    # ══════════════════════════════════════════════════
    # РАЗДЕЛ 4 — ПЛАН
    # ══════════════════════════════════════════════════
    heading(doc, '4. План выполнения индивидуального задания', before=6)

    table = doc.add_table(rows=1, cols=5)
    table.style = 'Table Grid'
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    hdr = table.rows[0].cells
    for cell, txt, w in zip(hdr,
        ['№', 'Место\nпроведения', 'Содержание или наименование\nпроделанной работы',
         'Дата', 'Объём\nработы в %'],
        [0.8, 3.2, 8.5, 2.5, 1.8]):
        cell.text = ''
        pr = cell.paragraphs[0]
        pr.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = pr.add_run(txt)
        _set_run_font(run, size=12, bold=True)
        cell.width = Cm(w)

    rows_data = [
        ('1', 'ФГУП «НПП «Гамма»»',
         'Ознакомление с объектом тестирования. Изучение СПО анализаторов спектра '
         'СК4-МАХ4 и СК4-МАХ6, анализ особенностей его графического интерфейса. '
         'Анализ требований к разрабатываемой подсистеме',
         '20.02.2026', '10'),
        ('2', 'ФГУП «НПП «Гамма»»',
         'Проектирование архитектуры подсистемы. Определение состава и взаимодействия '
         'компонентов. Выбор и изучение программных библиотек: pynput, uiautomation, '
         'Robot Framework, PySide6',
         '06.03.2026', '10'),
        ('3', 'ФГУП «НПП «Гамма»»',
         'Разработка модуля захвата пользовательских действий (класс InputTracker). '
         'Реализация перехвата событий клавиатуры и мыши, идентификации элементов '
         'интерфейса через Windows UI Automation API, многопоточной обработки событий '
         'с применением очереди и фоновых потоков',
         '27.03.2026', '20'),
        ('4', 'ФГУП «НПП «Гамма»»',
         'Разработка модуля обработки событий на основе конечного автомата (класс TokenFSM). '
         'Реализация состояний автомата (IDLE, VALUE_INPUT, DROPDOWN, MENU, CONFIGURATION) '
         'и логики генерации ключевых слов Robot Framework',
         '24.04.2026', '30'),
        ('5', 'ФГУП «НПП «Гамма»»',
         'Разработка графического интерфейса пользователя на основе PySide6. '
         'Интеграция компонентов подсистемы. Реализация режимов записи, паузы и останова сеанса',
         '15.05.2026', '20'),
        ('6', 'ФГУП «НПП «Гамма»»',
         'Интеграционное тестирование и отладка подсистемы на объекте тестирования. '
         'Проверка корректности генерируемых сценариев. Оформление отчётной документации',
         '23.05.2026', '10'),
    ]

    for num, place, content, date, vol in rows_data:
        row = table.add_row()
        cells = row.cells
        for cell, txt, align, w in zip(
            cells,
            [num, place, content, date, vol],
            [WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER,
             WD_ALIGN_PARAGRAPH.JUSTIFY, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.CENTER],
            [0.8, 3.2, 8.5, 2.5, 1.8]
        ):
            cell.text = ''
            pr = cell.paragraphs[0]
            pr.alignment = align
            pf = pr.paragraph_format
            pf.space_before = Pt(2); pf.space_after = Pt(2)
            pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE; pf.line_spacing = 1.15
            run = pr.add_run(txt)
            _set_run_font(run, size=12)
            cell.width = Cm(w)

    # Итоговая строка
    tot = table.add_row()
    tot.cells[3].text = ''
    pr3 = tot.cells[3].paragraphs[0]
    pr3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r3 = pr3.add_run('Всего')
    _set_run_font(r3, size=12, bold=True)
    tot.cells[4].text = ''
    pr4 = tot.cells[4].paragraphs[0]
    pr4.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r4 = pr4.add_run('100')
    _set_run_font(r4, size=12, bold=True)

    p(doc, '', after=8)
    sig_line2(doc, 'Руководитель практики от МАИ    ', 'Ведьманов Илья Сергеевич')
    sig_line(doc, 'Обучающийся    ', 'Гордеева Мария Дмитриевна')

    page_break(doc)

    # ══════════════════════════════════════════════════
    # РАЗДЕЛ 5 — ОТЗЫВ ОТ ОРГАНИЗАЦИИ
    # ══════════════════════════════════════════════════
    heading(doc, '5. Отзыв руководителя практики от организации/предприятия', before=6)

    review_text = (
        'Студентка группы М30-411Б-22 Института №3 Гордеева Мария Дмитриевна '
        'проходила преддипломную практику в Проектно-конструкторском департаменте '
        'ФГУП «НПП «Гамма»», в отделе специального программного обеспечения, '
        'в период с 09 февраля по 23 мая 2026 года. '
        'В ходе прохождения практики студентка разработала подсистему генерации сценариев '
        'автоматизированного тестирования интерфейса специального программного обеспечения '
        'анализаторов спектра СК4-МАХ4 и СК4-МАХ6 на основе захвата пользовательских '
        'действий. Разработанная подсистема функционирует под управлением операционной '
        'системы Windows и реализована на языке высокого уровня Python. В ходе выполнения '
        'работы были реализованы следующие функции: перехват действий пользователя '
        'с элементами графического интерфейса тестируемого приложения посредством '
        'Windows UI Automation API и библиотеки pynput; распознавание типов взаимодействий '
        'и их преобразование в ключевые слова Robot Framework с применением '
        'конечного автомата; запись и редактирование полученных тестовых сценариев '
        'средствами разработанного графического интерфейса на базе фреймворка PySide6. '
        'В ходе выполнения работы Гордеева М.Д. продемонстрировала умение работать '
        'с технической документацией, разрабатывать программные модули на базе '
        'существующей архитектуры, работать с библиотеками автоматизации UI, '
        'а также самостоятельно решать поставленные технические задачи. '
        'Студентка проявила ответственность, инициативность и высокий уровень '
        'технической грамотности. '
        'Материалы, изложенные в отчёте обучающегося, полностью соответствуют '
        'индивидуальному заданию.'
    )
    p(doc, review_text, indent=1.25, after=20)

    for _ in range(3):
        p(doc, '', after=0, indent=None)

    sig_line(doc, 'Смирнова Алина Евгеньевна, ведущий инженер    ', size=14,
             slash=True, date_blank=True, before=3)
    p_mixed(doc, [
        ('         (подпись руководителя от организации/предприятия)                   '
         '                                           (дата)', False, False, 12, True),
    ], indent=None, after=8)

    page_break(doc)

    # ══════════════════════════════════════════════════
    # ОТЧЁТ ОБУЧАЮЩЕГОСЯ — ТИТУЛЬНЫЙ ЛИСТ
    # ══════════════════════════════════════════════════
    p(doc, 'ФЕДЕРАЛЬНОЕ ГОСУДАРСТВЕННОЕ БЮДЖЕТНОЕ ОБРАЗОВАТЕЛЬНОЕ УЧРЕЖДЕНИЕ '
           'ВЫСШЕГО ОБРАЗОВАНИЯ «МОСКОВСКИЙ АВИАЦИОННЫЙ ИНСТИТУТ '
           '(НАЦИОНАЛЬНЫЙ ИССЛЕДОВАТЕЛЬСКИЙ УНИВЕРСИТЕТ)»',
      align=WD_ALIGN_PARAGRAPH.CENTER, indent=None, bold=True, size=14, before=0, after=6)

    for _ in range(4):
        p(doc, indent=None, after=0)

    p(doc, '6. Отчёт обучающегося по практике',
      align=WD_ALIGN_PARAGRAPH.CENTER, indent=None, bold=True, size=16, before=0, after=40)

    for _ in range(2):
        p(doc, indent=None, after=0)

    p_mixed(doc, [
        ('Обучающийся    ', False, False, 14),
        ('Гордеева Мария Дмитриевна', False, True, 14),
    ], align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, after=4)

    p_mixed(doc, [
        ('Институт №3 ', False, False, 14),
        ('«Системы управления, информатика и электроэнергетика»', False, True, 14),
    ], align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, after=4)

    p_mixed(doc, [
        ('Кафедра №304 ', False, False, 14),
        ('«Вычислительные машины, системы и сети»', False, True, 14),
    ], align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, after=4)

    p_mixed(doc, [
        ('Учебная группа №    ', False, False, 14),
        ('М30-411Б-22', False, True, 14),
    ], align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, after=4)

    p_mixed(doc, [
        ('Направление подготовки    ', False, False, 14),
        ('09.03.04 «Программная инженерия»', False, True, 14),
    ], align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, after=4)

    p_mixed(doc, [
        ('Вид практики    ', False, False, 14),
        ('Преддипломная', False, True, 14),
    ], align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, after=0)

    p(doc, '         (учебной, производственной, преддипломной или другой вид практики)',
      align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, size=12, italic=True, after=30)

    p(doc, 'Обучающийся', align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, size=14, after=4)

    p_mixed(doc, [
        ('    ', False, False, 14),
        ('Гордеева Мария Дмитриевна', False, True, 14),
        ('    /                    /   ', False, False, 14),
        ('«___» ____________ 2026 г.', False, False, 14),
    ], align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, after=0)

    p(doc, '              (фамилия, имя, отчество)                     (подпись)                  (дата)',
      align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, size=12, italic=True, after=30)

    p(doc, 'Москва 2026 г.', align=WD_ALIGN_PARAGRAPH.CENTER,
      indent=None, size=14, after=0)

    page_break(doc)

    # ══════════════════════════════════════════════════
    # ОТЧЁТ — ОГЛАВЛЕНИЕ
    # ══════════════════════════════════════════════════
    heading(doc, 'Оглавление', align=WD_ALIGN_PARAGRAPH.CENTER, before=0)

    toc_items = [
        ('Задание', ''),
        ('ОПРЕДЕЛЕНИЯ, ОБОЗНАЧЕНИЯ И СОКРАЩЕНИЯ', ''),
        ('1  Разработка подсистемы генерации сценариев тестирования', ''),
        ('1.1  Установка и настройка необходимых компонентов', ''),
        ('1.1.1  Подготовка программной среды', ''),
        ('1.1.2  Подготовка зависимостей', ''),
        ('1.2  Анализ объекта тестирования', ''),
        ('1.3  Разработка модуля захвата пользовательских действий', ''),
        ('1.3.1  Перехват событий клавиатуры и мыши', ''),
        ('1.3.2  Идентификация элементов UI через Windows UI Automation API', ''),
        ('1.3.3  Многопоточная обработка событий и кэширование UI-данных', ''),
        ('1.4  Разработка конечного автомата обработки событий', ''),
        ('1.4.1  Структура токенов и типы событий', ''),
        ('1.4.2  Состояния конечного автомата', ''),
        ('1.4.3  Генерация ключевых слов Robot Framework', ''),
        ('1.5  Разработка графического интерфейса пользователя', ''),
        ('1.6  Интеграционное тестирование', ''),
    ]
    for item, pg in toc_items:
        para = doc.add_paragraph()
        _para_fmt(para, align=WD_ALIGN_PARAGRAPH.LEFT, indent=None, before=0, after=2, ls=1.2)
        run = para.add_run(item)
        _set_run_font(run, size=14)

    page_break(doc)

    # ══════════════════════════════════════════════════
    # ОТЧЁТ — ЗАДАНИЕ
    # ══════════════════════════════════════════════════
    heading(doc, 'Задание', align=WD_ALIGN_PARAGRAPH.CENTER, before=0)

    p(doc,
      'Разработать подсистему генерации сценариев автоматизированного тестирования '
      'интерфейса специального программного обеспечения анализаторов спектра '
      'СК4-МАХ4 и СК4-МАХ6 на основе захвата пользовательских действий. '
      'Подсистема должна обеспечивать перехват событий клавиатуры и мыши '
      'с одновременной идентификацией элементов графического интерфейса, '
      'преобразование перехваченных событий в ключевые слова Robot Framework '
      'посредством конечного автомата, а также предоставлять графический '
      'интерфейс для управления сеансом записи и редактирования '
      'сгенерированных тестовых сценариев.', after=8)

    p(doc,
      'Объектом тестирования является специальное программное обеспечение '
      'анализаторов спектра СК4-МАХ4 и СК4-МАХ6, разработанное ФГУП «НПП «Гамма»» '
      'и применяемое при проведении радиотехнических измерений. '
      'Интерфейс СПО реализован на фреймворке Qt и включает элементы '
      'нескольких типов: поля ввода числовых значений с единицами измерения, '
      'выпадающие списки, вкладки, кнопки меню и диалоговые окна цифровой клавиатуры.', after=8)

    p(doc,
      'Серверная часть разработанной подсистемы реализована на языке Python 3.11 '
      'и включает два основных модуля: модуль захвата пользовательских действий '
      '(класс InputTracker) и модуль обработки событий на основе конечного '
      'автомата (класс TokenFSM). Графический интерфейс разработан с применением '
      'фреймворка PySide6. Подсистема функционирует под управлением '
      'операционной системы Windows.', after=8)

    page_break(doc)

    # ══════════════════════════════════════════════════
    # ОТЧЁТ — ОПРЕДЕЛЕНИЯ
    # ══════════════════════════════════════════════════
    heading(doc, 'ОПРЕДЕЛЕНИЯ, ОБОЗНАЧЕНИЯ И СОКРАЩЕНИЯ',
            align=WD_ALIGN_PARAGRAPH.CENTER, before=0)

    p(doc, 'В настоящем отчёте применяют следующие термины, сокращения и обозначения.', after=6)

    heading(doc, 'Термины и определения:', size=14, bold=True, before=6, after=4)

    terms = [
        ('Анализатор спектра', '— прибор для измерения распределения мощности сигнала '
         'по частотному диапазону; в настоящей работе объектом тестирования является '
         'специальное программное обеспечение анализаторов спектра СК4-МАХ4 и СК4-МАХ6.'),
        ('Ключевое слово Robot Framework (keyword)', '— элемент тестового сценария, '
         'представляющий собой именованное действие над элементом интерфейса '
         '(например, «Set Value With Dimension», «Drop-Down List Set»). '
         'Совокупность ключевых слов образует тестовый скрипт.'),
        ('Конечный автомат (Finite State Machine, FSM)', '— вычислительная модель, '
         'описывающая поведение системы в виде конечного множества состояний '
         'и переходов между ними; в данной работе используется для преобразования '
         'последовательности перехваченных событий в ключевые слова Robot Framework.'),
        ('Токен', '— минимальная единица захваченного пользовательского действия: '
         'нажатие или отпускание клавиши (KP/KR), клик мышью (CLICK), '
         'прокрутка (SCROLL), проверочная команда (CHECK, CHECK_ACTIVE и др.).'),
        ('Windows UI Automation API (UIA)', '— программный интерфейс операционной системы '
         'Windows, предоставляющий доступ к свойствам элементов графического '
         'интерфейса (имя, тип, AutomationId, состояние) без изменения '
         'исходного кода тестируемого приложения.'),
        ('AutomationId', '— уникальный идентификатор элемента управления '
         'в дереве UI Automation, назначаемый разработчиком приложения; '
         'в данной работе используется для однозначной идентификации '
         'элементов СПО при воспроизведении тестовых сценариев.'),
    ]

    for term, definition in terms:
        p_mixed(doc, [
            (f'\t{term}', False, False, 14),
            (f' {definition}', False, False, 14),
        ], indent=None, after=4)

    heading(doc, 'Обозначения и сокращения', size=14, bold=True, before=6, after=4)

    abbrs = [
        ('API', '— Application Programming Interface (интерфейс программирования приложений)'),
        ('COM', '— Component Object Model (технология взаимодействия объектов Microsoft)'),
        ('FSM', '— Finite State Machine (конечный автомат)'),
        ('GUI', '— Graphical User Interface (графический интерфейс пользователя)'),
        ('IDE', '— Integrated Development Environment (интегрированная среда разработки)'),
        ('PID', '— Process Identifier (идентификатор процесса операционной системы)'),
        ('СПО', '— специальное программное обеспечение'),
        ('UIA', '— UI Automation (Windows UI Automation API)'),
        ('ВКР', '— выпускная квалификационная работа'),
        ('ФСМ', '— конечный автомат (Finite State Machine)'),
    ]
    for abbr, definition in abbrs:
        p_mixed(doc, [
            (f'\t{abbr}', False, False, 14),
            (f' {definition}', False, False, 14),
        ], indent=None, after=3)

    page_break(doc)

    # ══════════════════════════════════════════════════
    # ГЛАВА 1
    # ══════════════════════════════════════════════════
    heading(doc, '1  Разработка подсистемы генерации сценариев тестирования',
            align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, before=0)

    # 1.1
    heading(doc, '1.1  Установка и настройка необходимых компонентов', before=10)

    p(doc,
      'Прежде чем приступить к разработке подсистемы, необходимо подготовить '
      'программную среду: установить интерпретатор Python, необходимые библиотеки '
      'и настроить доступ к API операционной системы. Правильная конфигурация '
      'среды напрямую влияет на воспроизводимость результатов и '
      'стабильность работы модулей, взаимодействующих с системными интерфейсами Windows.')

    # 1.1.1
    heading(doc, '1.1.1  Подготовка программной среды', before=8)

    p(doc,
      'Для разработки подсистемы использовался язык программирования Python версии 3.11. '
      'Данная версия обеспечивает стабильную поддержку всех используемых библиотек '
      'и предоставляет встроенные средства асинхронного и многопоточного '
      'программирования, необходимые для реализации неблокирующего захвата событий.')

    p(doc,
      'В качестве интегрированной среды разработки применялась JetBrains PyCharm, '
      'предоставляющая инструменты автодополнения кода, статического анализа, '
      'отладчика с поддержкой точек останова, а также встроенного управления '
      'виртуальными окружениями venv. Использование виртуального окружения '
      'исключает конфликты версий зависимостей между проектами и '
      'обеспечивает воспроизводимость установки на целевой машине.')

    p(doc,
      'Разработка и тестирование выполнялись под управлением операционной системы '
      'Windows 10 Pro (версия 10.0.19045). Выбор данной ОС обусловлен тем, что '
      'ключевой компонент подсистемы — Windows UI Automation API — является '
      'специфичным для платформы Microsoft Windows и недоступен на иных ОС.')

    # 1.1.2
    heading(doc, '1.1.2  Подготовка зависимостей', before=8)

    p(doc,
      'Подсистема использует набор внешних библиотек, обеспечивающих перехват '
      'ввода, идентификацию UI-элементов, формирование тестовых сценариев '
      'и организацию графического интерфейса. Зависимости зафиксированы в файле '
      'requirements.txt и устанавливаются командой pip install -r requirements.txt.')

    p(doc, 'Основные используемые библиотеки:', after=4)

    libs = [
        ('pynput 1.7.6', '— кроссплатформенная библиотека для перехвата и генерации '
         'событий клавиатуры и мыши. Предоставляет классы keyboard.Listener '
         'и mouse.Listener, запускающие обработчики событий в фоновых потоках. '
         'Выбрана как наиболее зрелое решение для низкоуровневого мониторинга '
         'ввода на Windows без необходимости использования WinAPI-хуков напрямую.'),
        ('uiautomation 2.0.18', '— Python-обёртка над Windows UI Automation API (COM). '
         'Предоставляет функции ControlFromPoint, GetForegroundControl, FindControl '
         'и паттерны доступа к свойствам элементов управления (SelectionItem, Toggle). '
         'Каждый вызов требует инициализации COM в текущем потоке через '
         'UIAutomationInitializerInThread, что критично при многопоточном использовании.'),
        ('PySide6 6.5+', '— официальные Python-привязки к фреймворку Qt6, '
         'применяемые для построения графического интерфейса пользователя подсистемы. '
         'Обеспечивает кроссплатформенный и зрелый инструментарий создания окон, '
         'виджетов и обработки событий GUI.'),
        ('robotframework 6.0+', '— фреймворк автоматизированного тестирования, '
         'ключевые слова которого генерирует разработанная подсистема. '
         'Формат ключевых слов соответствует синтаксису Robot Framework '
         'и может быть непосредственно использован в тестовых файлах .robot.'),
    ]
    for name, desc in libs:
        p_mixed(doc, [
            (f'\t– {name}', False, False, 14),
            (f' {desc}', False, False, 14),
        ], indent=None, after=4)

    # 1.2
    heading(doc, '1.2  Анализ объекта тестирования', before=10)

    p(doc,
      'Объектом тестирования является специальное программное обеспечение '
      'анализаторов спектра СК4-МАХ4 и СК4-МАХ6, разработанное в ФГУП «НПП «Гамма»». '
      'Данное СПО обеспечивает управление аппаратным анализатором спектра: '
      'настройку режимов измерений, конфигурацию частотных диапазонов, '
      'отображение и обработку результатов.')

    p(doc,
      'Графический интерфейс СПО реализован на фреймворке Qt и включает '
      'элементы нескольких категорий:')

    items = [
        'поля ввода числовых значений (QLineEdit) — используются для ввода частот, '
        'уровней сигнала и других измеримых параметров; содержат кнопки выбора '
        'единицы измерения (UnitBtn) и цифровую клавиатуру (DialogKeyPad);',
        'выпадающие списки (QComboBox) — применяются для выбора режимов работы, '
        'профилей измерения и конфигурационных параметров;',
        'вкладки (TabItem) — организуют разделение функций анализатора '
        'по тематическим группам;',
        'меню (MenuComboBox) — обеспечивают переключение между основными '
        'разделами (секциями) СПО;',
        'радиокнопки (QRadioButton) — используются для выбора '
        'одного из нескольких взаимоисключающих вариантов.',
    ]
    for item in items:
        p_mixed(doc, [('– ' + item, False, False, 14)], indent=None, after=3)

    p(doc,
      'Идентификация элементов в дереве UI Automation осуществляется '
      'по значению AutomationId, которое в СПО имеет иерархическую структуру '
      'с суффиксами: .Value (поле числового значения), .Title (метка-заголовок), '
      '.ComboBox (выпадающий список), .Dimensions (поле единицы измерения), '
      '.First/.Second/.Variant (варианты радиокнопок). '
      'Суффиксная схема позволяет группировать связанные элементы '
      'одного параметра по общему базовому идентификатору (BaseId).')

    p(doc,
      'Анализ структуры интерфейса выявил требования к разрабатываемой подсистеме: '
      'необходимость различать тип каждого нажатого элемента, '
      'корректно обрабатывать пользовательский ввод числовых значений '
      '(последовательность нажатий цифровых клавиш и выбор единицы), '
      'а также генерировать ключевые слова, семантически соответствующие '
      'выполненным операциям, а не просто фиксировать низкоуровневые события.')

    # 1.3
    heading(doc, '1.3  Разработка модуля захвата пользовательских действий', before=10)

    p(doc,
      'Центральным компонентом подсистемы является класс InputTracker, '
      'реализованный в модуле microide_core/microide.py. Его задача — '
      'перехватывать события клавиатуры и мыши, обогащать их контекстными '
      'данными об UI-элементах и передавать в конечный автомат для '
      'формирования ключевых слов.')

    # 1.3.1
    heading(doc, '1.3.1  Перехват событий клавиатуры и мыши', before=8)

    p(doc,
      'Перехват ввода реализован посредством библиотеки pynput. '
      'В методе start_tracking() создаются и запускаются два независимых слушателя: '
      'keyboard.Listener и mouse.Listener. Каждый слушатель выполняется '
      'в собственном потоке и вызывает соответствующие обработчики '
      '(on_key_press, on_key_release, on_mouse_click, on_mouse_scroll) '
      'при возникновении событий.')

    p(doc,
      'Обработчики клавиатуры реализуют поддержку горячих клавиш управления '
      'сеансом записи:')

    hotkeys = [
        ('ESC', '— перевод в режим паузы; повторное нажатие ESC во время паузы '
         'инициирует остановку записи;'),
        ('Enter', '— возобновление записи после паузы;'),
        ('Ctrl+G', '— генерация ключевого слова проверки значения последнего '
         'введённого параметра (Get Value With Dimension And Check);'),
        ('Ctrl+J', '— проверка активности (IsEnabled) элемента под курсором;'),
        ('Ctrl+R', '— проверка наличия клавиатурного фокуса у элемента;'),
        ('Ctrl+T', '— проверка состояния выбора (IsSelected/ToggleState) элемента;'),
        ('Ctrl+W', '— фиксация закрытия текущей вкладки (Base Close Tab).'),
    ]
    for key, desc in hotkeys:
        p_mixed(doc, [
            (f'\t– {key}', False, False, 14),
            (f' {desc}', False, False, 14),
        ], indent=None, after=3)

    p(doc,
      'Для исключения случайных двойных кликов реализован механизм подавления '
      'повторов (debounce): клик по тому же элементу в течение 170 мс после '
      'предыдущего игнорируется. Аналогичный механизм с порогом 300 мс '
      'применяется для событий прокрутки (scroll).')

    p(doc,
      'Клики по собственному окну приложения исключаются с помощью Win32 API '
      '(функция WindowFromPoint из user32.dll). Сначала определяется HWND окна '
      'под курсором, затем — PID его процесса; если PID совпадает '
      'с PID рекордера или имя исполняемого файла входит в список исключений, '
      'событие отбрасывается. Эта проверка выполняется до любых COM-вызовов, '
      'что предотвращает зависание при случайном клике на заголовок '
      'собственного окна.')

    # 1.3.2
    heading(doc, '1.3.2  Идентификация элементов UI через Windows UI Automation API', before=8)

    p(doc,
      'Для каждого события мыши подсистема определяет, какой элемент интерфейса '
      'находился под курсором в момент клика, используя функцию '
      'ControlFromPoint(x, y) из библиотеки uiautomation. '
      'Результат содержит атрибуты: Name, AutomationId, ControlType, '
      'ClassName и IsEnabled.')

    p(doc,
      'Вызовы COM-функций требуют инициализации COM в текущем потоке '
      '(UIAutomationInitializerInThread). Поскольку callback-функции pynput '
      'выполняются в отдельных потоках, контекстный менеджер используется '
      'непосредственно в методе _get_ui_info_fast().')

    p(doc,
      'Для Qt-приложений значение AutomationId имеет составную структуру. '
      'Например, элемент ввода частоты может иметь AutomationId '
      '«MainWindow.CenterFreq.Value», а соответствующая метка-заголовок — '
      '«MainWindow.CenterFreq.Title». Метод _get_ui_info_fast() извлекает '
      'базовый идентификатор (BaseId = «MainWindow.CenterFreq»), '
      'убирая известные суффиксы с помощью регулярного выражения.')

    p(doc,
      'Для выпадающих списков Qt разработана специальная процедура определения '
      'выбранного пункта. При клике на контейнер QComboBoxPrivateContainer '
      'функция _find_list_item_in_container() перебирает дочерние элементы '
      'контейнера и по координатам клика находит элемент типа ListItem, '
      'попавший под курсор.')

    p(doc,
      'При закрытии вкладки через кнопку «X» или горячую клавишу Ctrl+W '
      'подсистема определяет название закрываемой вкладки: '
      'обходится дерево UIA от кнопки закрытия до родительского TabItem '
      '(прямой родитель или sibling с признаком IsSelected).')

    # 1.3.3
    heading(doc, '1.3.3  Многопоточная обработка событий и кэширование UI-данных', before=8)

    p(doc,
      'Архитектура InputTracker использует трёхпоточную схему обработки '
      'для обеспечения отзывчивости и минимальной задержки. '
      'Callback-потоки pynput немедленно помещают необработанные события '
      'в потокобезопасную очередь _raw_queue (queue.Queue), '
      'не выполняя тяжёлых COM-операций. Worker-поток читает события '
      'из очереди и выполняет обогащение данными.')

    p(doc,
      'Ключевой оптимизацией является механизм pre-fetch при нажатии кнопки мыши. '
      'В момент нажатия (PRESS) запускается дополнительный фоновый поток, '
      'который немедленно выполняет COM-запрос ControlFromPoint и сохраняет '
      'результат в словарь _pending_click по ключу (x, y, button). '
      'К моменту отпускания кнопки (UP), когда событие записывается в очередь, '
      'данные уже готовы и извлекаются методом _pop_pending() без ожидания.')

    p(doc,
      'UI-кэш (_ui_cache) сохраняет результаты поиска TitleName '
      '(читаемое имя параметра из соседнего элемента с суффиксом .Title) '
      'и признак IsComboBox (наличие связанного элемента с суффиксом .ComboBox) '
      'по значению BaseId. При первом обращении к новому BaseId '
      'поиск выполняется в фоновом потоке, не задерживая основной поток; '
      'при повторных обращениях результат берётся из кэша мгновенно.')

    # 1.4
    heading(doc, '1.4  Разработка конечного автомата обработки событий', before=10)

    p(doc,
      'Класс TokenFSM (модуль microide_core/token_fsm.py) преобразует '
      'последовательность токенов в ключевые слова Robot Framework. '
      'Автомат отслеживает контекст выполнения действий: '
      'пока пользователь набирает цифры на клавиатуре, '
      'фиксируются промежуточные KP/KR-токены; '
      'как только нажата кнопка единицы измерения, '
      'вся последовательность преобразуется в одно ключевое слово '
      'Set Value With Dimension.')

    # 1.4.1
    heading(doc, '1.4.1  Структура токенов и типы событий', before=8)

    p(doc,
      'Каждое захваченное событие представляется объектом класса Token, '
      'содержащим поля: type (тип события), value (значение — символ клавиши, '
      'кнопка мыши, строка скролла), control (словарь с атрибутами UI-элемента) '
      'и timestamp. Класс TokenCollector накапливает токены сессии '
      'и выводит их в стандартный поток для отладки.')

    p(doc, 'Поддерживаются следующие типы токенов:', after=4)

    token_types = [
        ('KP (Key Press)', '— нажатие клавиши клавиатуры (символьной или специальной);'),
        ('KR (Key Release)', '— отпускание клавиши;'),
        ('CLICK', '— клик левой или правой кнопкой мыши с привязкой к UI-элементу;'),
        ('SCROLL', '— прокрутка колёсика мыши над элементом интерфейса;'),
        ('CHECK', '— команда проверки значения последнего введённого параметра (Ctrl+G);'),
        ('CHECK_ACTIVE', '— команда проверки активности (IsEnabled) элемента (Ctrl+J);'),
        ('CHECK_FOCUS', '— команда проверки наличия фокуса у элемента (Ctrl+R);'),
        ('CHECK_SELECTED', '— команда проверки состояния выбора элемента (Ctrl+T);'),
        ('CLOSE_TAB', '— фиксация закрытия вкладки по имени (Ctrl+W).'),
    ]
    for ttype, desc in token_types:
        p_mixed(doc, [
            (f'\t– {ttype}', False, False, 14),
            (f' {desc}', False, False, 14),
        ], indent=None, after=3)

    p(doc,
      'Тип элемента определяется функцией get_control_type(), '
      'которая анализирует атрибуты ClassName, AutomationId и ControlType. '
      'Возможные возвращаемые значения: value_field, title_keypad, digit, '
      'dimension, menu_combobox, combobox, list_item, tab, group.')

    # 1.4.2
    heading(doc, '1.4.2  Состояния конечного автомата', before=8)

    p(doc,
      'Автомат находится в одном из пяти состояний, определённых '
      'в перечислении State (Enum):')

    states = [
        ('IDLE', '— начальное состояние ожидания. В этом состоянии автомат ждёт '
         'начала нового паттерна: клика на поле ввода, открытия выпадающего списка, '
         'нажатия на элемент меню или кнопку конфигурации.'),
        ('VALUE_INPUT', '— ввод числового значения с единицей измерения. '
         'Автомат входит в это состояние при клике на поле типа value_field '
         'или title_keypad. В состоянии накапливаются нажатия цифровых клавиш '
         'и символов (digits). Выход происходит при нажатии кнопки единицы '
         'измерения (dimension) — генерируется ключевое слово Set Value With Dimension.'),
        ('DROPDOWN', '— выбор из выпадающего списка. Автомат входит при клике '
         'на элемент типа combobox. Завершается при клике на list_item — '
         'генерируется Drop-Down List Set.'),
        ('MENU', '— выбор секции главного меню. Автомат входит при клике '
         'на MenuComboBox. При выборе пункта генерируется '
         'Change Menu Section.'),
        ('CONFIGURATION', '— изменение режима работы или типа измерения. '
         'Используется для группировки кликов по кнопкам-конфигураторам '
         '(Mode, Measurement). При завершении паттерна генерируется '
         'Change Configuration с указанием выбранного режима.'),
    ]
    for state, desc in states:
        p_mixed(doc, [
            (f'\t– {state}', False, False, 14),
            (f' {desc}', False, False, 14),
        ], indent=None, after=4)

    # 1.4.3
    heading(doc, '1.4.3  Генерация ключевых слов Robot Framework', before=8)

    p(doc,
      'Конечный автомат поддерживает два режима работы: пакетный (метод process()) '
      'для постобработки накопленной последовательности токенов '
      'и потоковый (методы start_live() + feed() + finalize()) '
      'для формирования ключевых слов в реальном времени по мере поступления событий. '
      'В GUI используется потоковый режим: каждый вызов feed(token) может '
      'вернуть список новых ключевых слов, которые немедленно передаются '
      'в интерфейс через callback on_keyword.')

    p(doc, 'Генерируемые ключевые слова:', after=4)

    keywords_list = [
        ('Set Value With Dimension    <имя поля>    <значение>    <единица>',
         '— устанавливает числовое значение параметра в поле ввода с указанием '
         'единицы измерения (например, «GHz», «MHz», «dB»). '
         'Для частотных значений автоматически применяется форматирование '
         'с группировкой дробной части по три цифры.'),
        ('Drop-Down List Set    <имя списка>    <значение>',
         '— выбирает элемент из выпадающего списка.'),
        ('Change Menu Section    <секция>',
         '— переключает секцию главного меню СПО.'),
        ('Change Configuration    <mode>    <measurement>',
         '— устанавливает режим работы и тип измерения.'),
        ('Click    <имя элемента>',
         '— выполняет клик по именованной кнопке или элементу интерфейса.'),
        ('Click Tab    <имя вкладки>',
         '— переключает активную вкладку.'),
        ('Base Close Tab    <имя вкладки>',
         '— закрывает вкладку (соответствует Ctrl+W или нажатию кнопки «X»).'),
        ('Set Focus    <имя элемента>',
         '— устанавливает фокус на элемент без ввода значения.'),
        ('Get Value With Dimension And Check    <имя поля>    <ожидаемое значение>    <единица>',
         '— проверяет текущее значение параметра (Ctrl+G).'),
        ('Check Active    <имя элемента>    <ожидаемое состояние>',
         '— проверяет признак активности элемента (Ctrl+J).'),
        ('Check Focus    <имя элемента>',
         '— проверяет наличие клавиатурного фокуса (Ctrl+R).'),
        ('Check Selected    <имя элемента>    <ожидаемое состояние>',
         '— проверяет состояние выбора (Ctrl+T).'),
    ]
    for kw, desc in keywords_list:
        p_mixed(doc, [
            (f'\t– ', False, False, 14),
            (f'{kw}', False, False, 12, True),
            (f' {desc}', False, False, 14),
        ], indent=None, after=4)

    p(doc,
      'CHECK-команды (Ctrl+G, Ctrl+J, Ctrl+R, Ctrl+T) обрабатываются в любом '
      'состоянии автомата независимо от текущего паттерна, '
      'поскольку относятся к немедленным проверочным действиям пользователя.')

    # 1.5
    heading(doc, '1.5  Разработка графического интерфейса пользователя', before=10)

    p(doc,
      'Графический интерфейс подсистемы реализован на базе фреймворка PySide6 '
      '(официальные Python-привязки Qt6). Точка входа приложения — '
      'модуль microide_app/main.py, создающий объект QApplication '
      'и отображающий главное окно MainWindow.')

    p(doc,
      'Главное окно MainWindow (модуль microide_app/gui/main_window.py) '
      'обеспечивает управление сеансом записи и отображение результатов. '
      'Интерфейс включает:')

    gui_features = [
        'панель управления — кнопки «Начать запись», «Пауза», «Стоп», '
        'управляющие жизненным циклом объекта InputTracker;',
        'текстовое поле — отображает ключевые слова Robot Framework '
        'по мере их генерации в реальном времени;',
        'строку состояния — информирует о текущем режиме '
        '(запись / пауза / остановлено).',
    ]
    for feat in gui_features:
        p_mixed(doc, [('– ' + feat, False, False, 14)], indent=None, after=3)

    p(doc,
      'Связь между InputTracker и MainWindow организована через callback-механизм. '
      'При инициализации экземпляра InputTracker окно подключает '
      'метод on_keyword в качестве обработчика: '
      'каждый раз, когда FSM генерирует новое ключевое слово, '
      'оно передаётся в GUI через этот callback и добавляется в текстовое поле. '
      'Аналогично работает on_pause_changed — '
      'обновляет состояние кнопок при переходе в паузу и обратно.')

    p(doc,
      'Поскольку callback вызывается из фонового worker-потока InputTracker, '
      'для обновления GUI используется потокобезопасный механизм сигналов Qt '
      '(QMetaObject.invokeMethod с Qt.QueuedConnection), '
      'исключающий прямой доступ к виджетам из не-GUI-потоков.')

    # 1.6
    heading(doc, '1.6  Интеграционное тестирование', before=10)

    p(doc,
      'Интеграционное тестирование подсистемы проводилось на реальном объекте — '
      'специальном программном обеспечении анализаторов спектра '
      'СК4-МАХ4 и СК4-МАХ6. Тестирование включало несколько сценариев, '
      'охватывающих основные типы взаимодействий пользователя с интерфейсом.')

    p(doc,
      'В рамках тестирования проверялась корректность работы всех состояний '
      'конечного автомата: ввод числовых значений с единицами измерения '
      '(состояние VALUE_INPUT) для полей «Center Frequency», «Span», '
      '«Start Frequency», «Stop Frequency» и «CF Step»; '
      'выбор элементов из выпадающих списков (DROPDOWN); '
      'переключение секций главного меню (MENU); '
      'смена режима работы и типа измерения (CONFIGURATION). '
      'Также тестировались операции с вкладками (Click Tab, Base Close Tab) '
      'и все проверочные горячие клавиши (Ctrl+G, Ctrl+J, Ctrl+R, Ctrl+T).')

    p(doc,
      'В ходе тестирования был выявлен ряд граничных случаев, '
      'потребовавших доработки: некорректная идентификация кнопки закрытия вкладки '
      'при различных вариантах расположения в UIA-дереве, '
      'ложные срабатывания при клике на заголовок окна рекордера, '
      'а также необходимость учёта особенностей форматирования частотных значений '
      '(группировка дробной части пробелами для значений в GHz, MHz, kHz). '
      'Все выявленные ошибки были устранены в процессе отладки.')

    p(doc,
      'По завершении тестирования разработанная подсистема была интегрирована '
      'в цикл разработки специального программного обеспечения ФГУП «НПП «Гамма»». '
      'Внедрение результатов разработки позволило сократить временные затраты '
      'и повысить качество тестирования СПО анализаторов спектра '
      'СК4-МАХ4 и СК4-МАХ6.')

    sig_line(doc, 'Обучающийся    ', 'Гордеева Мария Дмитриевна',
             before=20, date_blank=True)

    page_break(doc)

    # ══════════════════════════════════════════════════
    # РАЗДЕЛ 7 — ОТЗЫВ РУКОВОДИТЕЛЯ МАИ
    # ══════════════════════════════════════════════════
    heading(doc, '7. Отзыв руководителя практики', before=6)

    for _ in range(10):
        p(doc, '___________________________________________________________________________',
          indent=None, after=4)

    p(doc, '', after=20)
    sig_line2(doc, 'Руководитель практики от МАИ    ', 'Ведьманов Илья Сергеевич',
              before=6)
    p_mixed(doc, [
        ('              (фамилия, имя, отчество)                          (подпись)     ', False, False, 12, True),
        ('«___» ____________ 2026 г.', False, False, 12),
    ], indent=None, after=8)

    page_break(doc)

    # ══════════════════════════════════════════════════
    # РАЗДЕЛ 8 — РЕЗУЛЬТАТЫ ПРАКТИКИ
    # ══════════════════════════════════════════════════
    heading(doc, '8. Результаты практики.', before=6)

    for _ in range(6):
        p(doc, '___________________________________________________________________________',
          indent=None, after=4)

    p_mixed(doc, [
        ('Оценка', False, False, 14),
        ('___________', False, True, 14),
    ], indent=None, after=20)

    sig_line2(doc, 'Руководитель практики от МАИ    ', 'Ведьманов Илья Сергеевич',
              before=6)
    p_mixed(doc, [
        ('              (фамилия, имя, отчество)                          (подпись)     ', False, False, 12, True),
        ('«___» ____________ 2026 г.', False, False, 12),
    ], indent=None, after=8)

    # ══════════════════════════════════════════════════
    # Сохранение
    # ══════════════════════════════════════════════════
    out = r'c:\Users\Maria\Downloads\Журнал_практики_Гордеева.docx'
    doc.save(out)
    print(f'Сохранено: {out}')


if __name__ == '__main__':
    build()
