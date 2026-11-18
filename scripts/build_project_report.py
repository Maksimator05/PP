"""Build the detailed variant 3 report from the current local run artifacts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

import pandas as pd
from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "Отчет по проектному практикуму Розничная торговля.docx"
TEMPLATE = ROOT / "docs" / "report_template.docx"
REFERENCE_TEMPLATE = Path(r"C:\Users\Tamiron\Downloads\Telegram Desktop\Отчет пп.docx")
PALE_BLUE = "D9EAF7"
PALE_GREY = "F4F7FA"
GRID = "D9D9D9"


def set_font(run, name: str = "Times New Roman", size: float = 14, bold: bool | None = None) -> None:
    run.font.name = name
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    if bold is not None:
        run.bold = bold


def clear_body(document: Document) -> None:
    body = document._element.body
    section_properties = body.sectPr
    for child in list(body):
        if child is not section_properties:
            body.remove(child)


def clean_document_properties(document: Document) -> None:
    props = document.core_properties
    props.title = "Отчет по проектному практикуму. Вариант 3"
    props.subject = "Недельное прогнозирование продаж товарных категорий"
    props.author = ""
    props.last_modified_by = ""
    props.keywords = "розничная торговля, недельные продажи, прогнозирование"
    props.comments = ""
    settings = document.settings._element
    update_fields = settings.find(qn("w:updateFields"))
    if update_fields is None:
        update_fields = OxmlElement("w:updateFields")
        settings.append(update_fields)
    update_fields.set(qn("w:val"), "true")


def get_document() -> Document:
    if TEMPLATE.exists():
        document = Document(TEMPLATE)
    elif REFERENCE_TEMPLATE.exists():
        document = Document(REFERENCE_TEMPLATE)
        clear_body(document)
        clean_document_properties(document)
        TEMPLATE.parent.mkdir(parents=True, exist_ok=True)
        document.save(TEMPLATE)
        document = Document(TEMPLATE)
    else:
        raise FileNotFoundError(
            "Не найден чистый шаблон docs/report_template.docx и исходный образец "
            "Отчет пп.docx. Укажите или восстановите шаблон отчета."
        )
    clear_body(document)
    clean_document_properties(document)
    return document


def setup_styles(document: Document) -> None:
    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(3)
    section.right_margin = Cm(1.5)
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.header_distance = Cm(1.27)
    section.footer_distance = Cm(1.27)
    section.different_first_page_header_footer = True


def add_body(document: Document, value: str, first_line: bool = True) -> None:
    paragraph = document.add_paragraph(style="Normal")
    paragraph.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    paragraph.paragraph_format.first_line_indent = Cm(1.25) if first_line else Cm(0)
    paragraph.paragraph_format.line_spacing = 1.5
    paragraph.add_run(value.replace("`", ""))


def add_bullet(document: Document, value: str, numbered: bool = False) -> None:
    paragraph = document.add_paragraph(style="List Number" if numbered else "List Bullet")
    paragraph.paragraph_format.left_indent = Cm(1.25)
    paragraph.paragraph_format.first_line_indent = Cm(-0.5)
    paragraph.paragraph_format.line_spacing = 1.25
    paragraph.paragraph_format.space_after = Pt(3)
    paragraph.add_run(value)


def add_heading(document: Document, value: str, level: int = 1) -> None:
    document.add_heading(value, level=level)


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = tc_pr.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        tc_pr.append(shading)
    shading.set(qn("w:fill"), fill)


def set_cell_margins(cell, top: int = 90, start: int = 110, bottom: int = 90, end: int = 110) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin_name, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin_name}"))
        if node is None:
            node = OxmlElement(f"w:{margin_name}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_table_borders(table) -> None:
    tbl_pr = table._tbl.tblPr
    borders = tbl_pr.first_child_found_in("w:tblBorders")
    if borders is None:
        borders = OxmlElement("w:tblBorders")
        tbl_pr.append(borders)
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        tag = qn(f"w:{edge}")
        element = borders.find(tag)
        if element is None:
            element = OxmlElement(f"w:{edge}")
            borders.append(element)
        element.set(qn("w:val"), "single")
        element.set(qn("w:sz"), "4")
        element.set(qn("w:space"), "0")
        element.set(qn("w:color"), GRID)


def add_table(document: Document, headers: list[str], rows: list[list[object]], widths: list[float] | None = None) -> None:
    table = document.add_table(rows=1, cols=len(headers))
    table.autofit = False
    table.style = "Table Grid"
    set_table_borders(table)
    if widths is None:
        page_width = 16.5
        widths = [page_width / len(headers)] * len(headers)
    for column, width in enumerate(widths):
        table.columns[column].width = Cm(width)
    for row in table.rows:
        row_properties = row._tr.get_or_add_trPr()
        row_properties.append(OxmlElement("w:cantSplit"))
    header_row = table.rows[0]
    repeat = OxmlElement("w:tblHeader")
    repeat.set(qn("w:val"), "true")
    header_row._tr.get_or_add_trPr().append(repeat)
    for column, value in enumerate(headers):
        cell = header_row.cells[column]
        cell.width = Cm(widths[column])
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_shading(cell, PALE_BLUE)
        set_cell_margins(cell)
        paragraph = cell.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.line_spacing = 1.0
        paragraph.paragraph_format.space_after = Pt(0)
        run = paragraph.add_run(str(value))
        set_font(run, size=9.5, bold=True)

    for row_index, values in enumerate(rows):
        cells = table.add_row().cells
        row_properties = table.rows[-1]._tr.get_or_add_trPr()
        row_properties.append(OxmlElement("w:cantSplit"))
        for column, value in enumerate(values):
            cell = cells[column]
            cell.width = Cm(widths[column])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            set_cell_margins(cell)
            if row_index % 2:
                set_cell_shading(cell, PALE_GREY)
            paragraph = cell.paragraphs[0]
            text = str(value).replace("`", "")
            paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT if column == 0 or len(text) > 24 else WD_ALIGN_PARAGRAPH.CENTER
            paragraph.paragraph_format.line_spacing = 1.05
            paragraph.paragraph_format.space_after = Pt(0)
            run = paragraph.add_run(text)
            set_font(run, size=9.5)
    document.add_paragraph()


def add_code(document: Document, lines: list[str]) -> None:
    for line in lines:
        paragraph = document.add_paragraph()
        paragraph.paragraph_format.left_indent = Cm(0.6)
        paragraph.paragraph_format.first_line_indent = Cm(0)
        paragraph.paragraph_format.line_spacing = 1.0
        paragraph.paragraph_format.space_after = Pt(1)
        run = paragraph.add_run(line)
        set_font(run, name="Consolas", size=9.5)


def add_cover(document: Document) -> None:
    header_lines = [
        "МИНИСТЕРСТВО ЦИФРОВОГО РАЗВИТИЯ, СВЯЗИ И МАССОВЫХ КОММУНИКАЦИЙ РОССИЙСКОЙ ФЕДЕРАЦИИ",
        "Ордена Трудового Красного Знамени федеральное государственное бюджетное образовательное учреждение высшего образования",
        "«Московский технический университет связи и информатики»",
        "(МТУСИ)",
        "Кафедра «Математическая кибернетика и информационные технологии»",
    ]
    for index, value in enumerate(header_lines):
        paragraph = document.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.paragraph_format.first_line_indent = Cm(0)
        paragraph.paragraph_format.line_spacing = 1.0
        paragraph.paragraph_format.space_after = Pt(2)
        run = paragraph.add_run(value)
        set_font(run, size=11 if index < 2 else 12, bold=index in (0, 4))
    for _ in range(3):
        document.add_paragraph()
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.paragraph_format.space_before = Pt(16)
    paragraph.paragraph_format.space_after = Pt(8)
    paragraph.add_run("ОТЧЕТ ПО ПРОЕКТНОМУ ПРАКТИКУМУ")
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.line_spacing = 1.2
    paragraph.paragraph_format.space_after = Pt(6)
    run = paragraph.add_run("Вариант 3. Розничная торговля\nНедельные продажи по товарным категориям сети")
    set_font(run, size=14, bold=True)
    for _ in range(2):
        document.add_paragraph()
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.line_spacing = 1.3
    paragraph.paragraph_format.space_after = Pt(3)
    paragraph.add_run("Выполнил: студент группы __________________\nФ.И.О.: _________________________________")
    for _ in range(3):
        document.add_paragraph()
    paragraph = document.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    paragraph.paragraph_format.first_line_indent = Cm(0)
    paragraph.paragraph_format.space_before = Pt(40)
    paragraph.paragraph_format.line_spacing = 1.0
    paragraph.add_run("Москва\n2026")
    document.add_page_break()


def clear_cached_page_statistics(path: Path) -> None:
    """Remove the template's stale page/word totals; Word recalculates on open."""
    with ZipFile(path, "r") as source:
        entries = [(info, source.read(info.filename)) for info in source.infolist()]
    updated_entries = []
    for info, content in entries:
        if info.filename == "docProps/app.xml":
            root = ET.fromstring(content)
            for child in list(root):
                if child.tag.rsplit("}", 1)[-1] in {
                    "Pages", "Words", "Characters", "CharactersWithSpaces", "Paragraphs", "Lines"
                }:
                    root.remove(child)
            content = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        updated_entries.append((info, content))
    temporary_path = path.with_suffix(".tmp.docx")
    with ZipFile(temporary_path, "w", compression=ZIP_DEFLATED) as target:
        for info, content in updated_entries:
            target.writestr(info, content)
    os.replace(temporary_path, path)


def fmt_number(value: float, digits: int = 2) -> str:
    return f"{value:,.{digits}f}".replace(",", " ").replace(".", ",")


def build() -> None:
    summary = json.loads((ROOT / "artifacts" / "demo_summary.json").read_text(encoding="utf-8"))
    metrics = json.loads((ROOT / "artifacts" / "model_metrics.json").read_text(encoding="utf-8"))
    selected = json.loads((ROOT / "artifacts" / "selected_features.json").read_text(encoding="utf-8"))
    importance = pd.read_csv(ROOT / "artifacts" / "feature_importance.csv")
    counts = summary["row_counts"]
    business = summary["business_metrics"]
    model_names = {
        "seasonal_naive": "Seasonal naive",
        "ridge": "Ridge",
        "catboost_or_histgb": "HistGradientBoosting",
        "random_forest_optional": "Random Forest",
    }

    document = get_document()
    setup_styles(document)
    add_cover(document)

    add_heading(document, "Аннотация")
    add_body(
        document,
        "Отчет описывает учебную систему прогноза недельных продаж по товарным категориям розничной сети, соответствующую варианту 3 методических указаний. Реализованы загрузка и нормализация X5 RetailHero, второй слабоструктурированный поток промо-описаний, контроль качества, SQL-хранение, признаки временных рядов, сравнение моделей, прогноз на горизонты 1–4 недели, мониторинг, объяснение моделей и интерактивный дашборд. Локальная проверка выполнена на синтетических данных: она подтверждает работу инженерного контура, но не является оценкой точности на реальной сети. Для итоговой защиты остаются обязательными запуск с реальными данными и самостоятельная проверка Docker/PostgreSQL.",
    )
    add_body(document, "Ключевые слова: розничная торговля, недельный прогноз, товарная категория, X5 RetailHero, временная валидация, мониторинг дрейфа.")

    add_heading(document, "Содержание")
    for item in [
        "Введение",
        "1. Постановка задачи и требования варианта",
        "2. Источники и структура данных",
        "3. Архитектура и технологический стек",
        "4. Загрузка, обработка и качество данных",
        "5. Формирование признаков и защита от утечки",
        "6. Модели и схема временной проверки",
        "7. Результаты эксперимента",
        "8. Прогнозы и бизнес-интерпретация",
        "9. Объяснимость, мониторинг и дашборд",
        "10. Сопоставление с критериями оценки",
        "Заключение",
        "Список источников",
        "Приложение А. Локальный запуск и проверка данных",
        "Приложение Б. Команды проверки Docker/PostgreSQL",
    ]:
        add_bullet(document, item)
    document.add_page_break()

    add_heading(document, "Введение")
    add_body(
        document,
        "В розничной сети решения по запасам, заказам и календарю промо принимаются до того, как известен фактический спрос будущей недели. Ошибка прогноза может привести к дефициту товара или излишнему запасу. Поэтому полезен воспроизводимый аналитический процесс, который объединяет продажи, календарную информацию и описания промоакций, показывает прогноз вместе с качеством и позволяет отслеживать сдвиг данных.",
    )
    add_body(
        document,
        "Работа выполнена по варианту 3: «Розничная торговля — недельные продажи по товарным категориям сети». Цель — разработать полный прототип от загрузки данных до интерактивного представления прогноза и контроля его качества. В отчете отдельно указано, какие результаты измерены на локальном синтетическом запуске и какие требуют подтверждения на реальном наборе.",
    )

    add_heading(document, "1. Постановка задачи и требования варианта")
    add_body(document, "Целевая величина — сумма продаж `sales_amount` за неделю. Объект прогнозирования задается магазином, товарной категорией и неделей. Основной пользователь — категорийный менеджер; его практическая задача — планировать закупку и оценивать последствия возможного недо- или перепрогноза.")
    add_table(
        document,
        ["Элемент задачи", "Определение в проекте"],
        [
            ["Вариант", "3 — розничная торговля, недельные продажи по товарным категориям"],
            ["Ключ ряда", "Магазин × категория × неделя"],
            ["Целевая переменная", "Недельная сумма продаж, `sales_amount`"],
            ["Горизонты", "1, 2, 3 и 4 недели"],
            ["Пользователи", "Категорийный менеджер и аналитик"],
            ["Критерий выбора", "Минимум WAPE на validation-периоде; финальный test оставлен для итоговой оценки"],
        ],
        [4.2, 12.3],
    )
    add_body(document, "Критерии успеха включают корректную хронологию проверки, отсутствие утечки будущих продаж, повторяемый запуск, базовую модель и не менее трех моделей-кандидатов, совместное отображение факта/прогноза/качества, мониторинг и содержательную интерпретацию ошибки.")

    add_heading(document, "2. Источники и структура данных")
    add_heading(document, "2.1. Продажи и товарный справочник", level=2)
    add_body(document, "Основной целевой набор — публичный X5 RetailHero Uplift. Загрузчик ищет файлы рекурсивно, поддерживает сжатые CSV и варианты вложенной структуры. Файл покупок приводится к транзакционной схеме, а справочник товаров используется для получения категории. При наличии продуктовых сумм учитываются `trn_sum_from_iss` и `trn_sum_from_red`; если доступна только сумма чека, она распределяется по товарным строкам пропорционально количеству. Имена полей настраиваются в `config/x5_data_mapping.yaml`.")
    add_body(document, "Режим `DATA_SOURCE=x5` не переключается автоматически на синтетические продажи при ошибке загрузки. Режим `DATA_SOURCE=synthetic` предназначен только для автономного воспроизводимого демонстрационного прогона. В настоящем локальном эксперименте X5-файлы не использовались.")
    add_heading(document, "2.2. Слабоструктурированные промо-описания", level=2)
    add_body(document, "Второй канал — отдельный файл `promo_texts.csv` с текстом описания акции, категорией, магазином и неделей действия. Из текста извлекаются длина и количество слов, процент скидки, маркеры наборов, новинок и распродаж, а также словарные признаки положительной и отрицательной тональности. Извлечение выполняется локально, без передачи текста во внешний сервис.")
    add_body(document, "Для текущего synthetic-demo отдельный промо-календарь создается независимо от транзакционной таблицы и маркируется как `synthetic_promo_calendar`. Это демонстрирует объединение разнородных потоков, но его содержимое нельзя трактовать как реальные акции X5. Перед бизнес-применением календарь нужно заменить подтвержденным промо-источником.")

    add_heading(document, "3. Архитектура и технологический стек")
    add_body(document, "В проекте реализован поток: поиск источников → raw-файлы → канонический загрузчик → контроль качества → недельная агрегация → хранилище → признаки → временная валидация → модели → прогнозы и мониторинг → Streamlit-дашборд. Описание компонентов приведено в `docs/architecture.md`.")
    add_table(
        document,
        ["Слой", "Реализация", "Роль"],
        [
            ["Загрузка", "Python, requests/Hugging Face, локальные CSV/CSV.GZ", "Получение и проверка исходных таблиц"],
            ["Обработка", "pandas, YAML mapping, quality checks", "Канонизация, преобразования, контроль данных"],
            ["Хранение", "SQLite локально; PostgreSQL в Compose", "Raw/weekly/features/forecasts/metrics/logs"],
            ["Модели", "scikit-learn; CatBoost при наличии, HistGradientBoosting fallback", "Сравнение baseline, линейной и нелинейных моделей"],
            ["Аналитика", "Streamlit и Plotly", "Фильтры, факт, прогноз и диагностические панели"],
        ],
        [3.1, 5.5, 7.9],
    )
    add_body(document, "Настройки и пути вынесены в YAML и переменные окружения. SQL-структура находится в `sql/001_schema.sql`. Локальный режим использует SQLite; PostgreSQL и приложение запускаются через `docker-compose.yml`. Docker в этой проверке не запускался по просьбе пользователя.")

    add_heading(document, "4. Загрузка, обработка и качество данных")
    add_body(document, "До агрегации загрузчик приводит даты, магазины, товары, категории, суммы и количества к общей схеме. Отрицательные значения не маскируются автоматическим обрезанием: строки проходят через проверку и при нарушении правил попадают в отдельный журнал проблем качества. Пустые дата или категория, дубликат и недопустимые суммы выявляются до формирования витрины.")
    add_body(document, f"Локальный прогон обработал {summary['transactions']:,} транзакций. В демонстрацию намеренно включены {summary['rejected_quality_rows']} контрольные ошибочные записи; они зарегистрированы как проблемы качества и исключены из валидной недельной витрины. Получено {summary['weekly_rows']:,} агрегированных рядов магазин–категория–неделя, {summary['features_rows']:,} строк feature store и {counts['promo_texts_raw']:,} отдельных промо-описаний.".replace(",", " "))
    add_table(
        document,
        ["Таблица/артефакт", "Строки после локального прогона", "Назначение"],
        [
            ["sales_raw", fmt_number(counts["sales_raw"], 0), "Недельная витрина продаж"],
            ["promo_texts_raw", fmt_number(counts["promo_texts_raw"], 0), "Слабоструктурированные промо-описания"],
            ["feature_store", fmt_number(counts["feature_store"], 0), "Признаки для обучения и прогноза"],
            ["forecasts", fmt_number(counts["forecasts"], 0), "Прогнозы на 1–4 недели"],
            ["metrics", fmt_number(counts["metrics"], 0), "Метрики экспериментов и периодов"],
            ["data_quality_issues", fmt_number(counts["data_quality_issues"], 0), "Отклоненные строки/проблемы качества"],
            ["monitoring_alerts", fmt_number(counts["monitoring_alerts"], 0), "Сигналы мониторинга текущего прогона"],
        ],
        [4.0, 3.1, 9.4],
    )
    add_body(document, f"Повторный локальный запуск обработал 0 новых недель и сохранил {counts['sales_raw']:,} строк в `sales_raw`. Upsert по ключам недельного ряда предотвращает дублирование при повторной загрузке. Автоматические тесты проверяют повторный прогон на отдельной временной базе.".replace(",", " "))

    add_heading(document, "5. Формирование признаков и защита от утечки")
    add_body(document, "Для каждой пары магазин–категория признаки строятся относительно даты отсечения `as_of_date` и целевой `target_week`. В работе используются лаги продаж и количества на 1, 2, 3, 4, 8, 12 и 52 недели, скользящие средние и стандартные отклонения, EWMA, календарные признаки, промо-флаг целевой недели, коды магазина/категории и признаки промо-текста.")
    add_body(document, "Из 41 рассчитанного признака после удаления констант и сильно коррелированных полей оставлено 36. Отбор выполняется на обучающем периоде. Для применения используется тот же набор признаков, что и при обучении. Будущая целевая сумма продаж не используется при расчете признаков целевой недели; для промо учитывается только заранее известная информация.")
    add_body(document, "Условие проекта требует, чтобы дата отсечения предшествовала прогнозируемой неделе. Это условие проверяется в коде, а отдельный тест изменяет будущие продажи и убеждается, что признаки уже сформированной целевой недели от этого не меняются. Категориальные признаки преобразуются стабильными кодами; глобальный target encoding не используется.")
    add_table(
        document,
        ["Группа признаков", "Примеры", "Доступность"],
        [
            ["История продаж", "`sales_amount_lag_1/4/12/52`, `sales_quantity_lag_*`", "Только недели до даты отсечения"],
            ["Динамика", "`roll_mean_4/8/12`, `roll_std_4/8/12`, `ewma_4/8`", "Окна сдвинуты относительно target week"],
            ["Календарь", "Неделя года, квартал, упрощенный праздник", "Известны заранее"],
            ["Промо", "Флаг акции, скидка, bundle/new/sale, словарные тональности", "Только доступные заранее описания"],
            ["Идентификаторы", "Код магазина и категории, взаимодействие category × month", "Стабильное преобразование категорий"],
        ],
        [3.4, 7.4, 5.7],
    )

    add_heading(document, "6. Модели и схема временной проверки")
    add_body(document, "Сравниваются четыре варианта из разных классов: сезонный наивный прогноз, Ridge со стандартизацией, HistGradientBoosting и Random Forest. CatBoost используется только при наличии пакета; в фактическом окружении работал `HistGradientBoostingRegressor`. Для детерминированных компонентов применяется seed 42.")
    add_body(document, "Случайное перемешивание временного ряда не применяется. Последовательность периодов сохраняет порядок времени: модель обучается на train, выбирается на validation, затем выбранный кандидат переобучается на train вместе с validation и оценивается на закрытом test-периоде.")
    add_table(
        document,
        ["Период", "Строки", "Диапазон целевых недель", "Назначение"],
        [
            ["Train", fmt_number(summary["train_rows"], 0), f"до {metrics['run_metadata']['train_last_target_week']}", "Обучение и отбор признаков"],
            ["Validation", fmt_number(summary["validation_rows"], 0), f"{summary['validation_start']} — {summary['validation_end']}", "Выбор модели по WAPE"],
            ["Final test", fmt_number(summary["final_test_rows"], 0), f"{summary['test_start']} — {summary['test_end']}", "Однократная итоговая оценка"],
        ],
        [2.5, 2.2, 5.0, 6.8],
    )
    add_body(document, "Тестовый набор не участвует в выборе модели или параметров. В локальном ряду каждая строка соответствует недельному наблюдению одной пары магазин–категория; поэтому количество строк в каждом периоде включает несколько параллельных рядов.")

    add_heading(document, "7. Результаты эксперимента")
    add_body(document, "Основной критерий выбора — WAPE на validation-периоде: сумма абсолютных ошибок, деленная на сумму фактических продаж. В отличие от MAE в денежных единицах, WAPE удобно интерпретировать как долю недельного оборота, приходящуюся на ошибку прогноза. Дополнительно рассчитываются MAE, RMSE и sMAPE.")
    rows = []
    for model_name, values in metrics["models"].items():
        val = values["validation_metrics"]
        test = values["test_metrics"]
        rows.append(
            [
                model_names.get(model_name, model_name),
                f"{val['WAPE']:.2%}",
                f"{test['WAPE']:.2%}",
                fmt_number(test["MAE"]),
                fmt_number(test["RMSE"]),
            ]
        )
    add_table(document, ["Модель", "WAPE validation", "WAPE test", "MAE test", "RMSE test"], rows, [4.3, 2.8, 2.5, 3.3, 3.6])
    chosen_name = model_names.get(summary["best_model"], summary["best_model"])
    best = summary["best_metrics"]
    validation = summary["validation_metrics"]
    add_body(
        document,
        f"По validation WAPE выбрана модель {chosen_name}: validation WAPE {validation['WAPE']:.2%}. На закрытом тестовом периоде ее значения составили MAE {fmt_number(best['MAE'])}, RMSE {fmt_number(best['RMSE'])}, WAPE {best['WAPE']:.2%} и sMAPE {best['sMAPE']:.2%}. В synthetic-demo это сгенерированные денежные единицы; оценку нельзя переносить на реальную сеть без повторного обучения и проверки на X5-файлах.",
    )
    hgb_test = metrics["models"]["catboost_or_histgb"]["test_metrics"]["WAPE"]
    add_body(document, f"Важно, что HistGradientBoosting показал на test WAPE {hgb_test:.2%}, немного ниже значения выбранного Random Forest. Он не подменяет выбранную модель, потому что решение принимается заранее по validation WAPE. Это демонстрирует, почему нельзя выбирать модель по окончательному тесту.")

    add_heading(document, "8. Прогнозы и бизнес-интерпретация")
    add_body(document, "Для 32 комбинаций магазин–категория рассчитаны прогнозы на горизонты 1, 2, 3 и 4 недели: всего 128 записей. Горизонты 2–4 строятся рекурсивно: следующий шаг использует предыдущие прогнозные значения для обновления лагов и скользящих признаков. Такой подход обеспечивает полный демонстрационный контур, однако перед производственным использованием предпочтительно обучить и проверить отдельные модели по горизонтам.")
    add_table(
        document,
        ["Показатель holdout", "Значение", "Как читать"],
        [
            ["Средняя абсолютная ошибка", f"{fmt_number(business['average_error_rub'])} за неделю", "Типичное абсолютное отклонение одной прогнозной строки"],
            ["Сумма абсолютных ошибок", fmt_number(business["total_absolute_error_rub"]), "Сумма модулей ошибок по тестовым строкам"],
            ["Ошибки свыше 20%", f"{business['share_forecasts_error_gt_20pct']:.2%}", "Доля тестовых прогнозов, превысивших порог относительной ошибки"],
            ["Сильное занижение / завышение", f"{business['strong_underforecast_weeks']} / {business['strong_overforecast_weeks']}", "Число тестовых строк по направлению ошибки"],
            ["Сумма недопрогноза / перепрогноза", f"{fmt_number(business['understock_risk_rub'])} / {fmt_number(business['overstock_risk_rub'])}", "Грубые суммы отклонения, без учета маржи и стоимости запасов"],
        ],
        [4.0, 4.1, 8.4],
    )
    add_body(document, "Денежные суммы выше являются упрощенным переводом ошибки прогноза. В проекте нет фактических закупочных цен, маржи, списаний, стоимости хранения и штрафов за дефицит, поэтому эти оценки показывают масштаб отклонения, а не полную финансовую стоимость бизнес-решения.")
    add_body(document, "Нижняя и верхняя границы прогноза пока строятся эвристически на основе ошибки тестового периода. Это не калиброванные вероятностные интервалы и не должны трактоваться как гарантированное покрытие.")

    add_heading(document, "9. Объяснимость, мониторинг и дашборд")
    add_heading(document, "9.1. Объяснение модели", level=2)
    top_features = importance.sort_values("permutation_importance_validation", ascending=False).head(5)
    add_body(document, "Глобальная интерпретация сопоставляет встроенную важность модели с permutation importance на validation и test. В текущем запуске среди ведущих по validation-признаков оказались 12-недельное среднее продаж, код категории и лаг количества за 52 недели. Ранжирование на закрытом test публикуется как диагностика стабильности; test-важности не используются для подбора модели.")
    add_table(
        document,
        ["Признак", "Permutation importance, validation", "Ранг validation", "Ранг test"],
        [
            [row["feature"], fmt_number(float(row["permutation_importance_validation"])), int(row["validation_rank"]), int(row["test_rank"])]
            for _, row in top_features.iterrows()
        ],
        [5.5, 4.6, 3.0, 3.4],
    )
    add_body(document, "Дополнительно формируются partial-dependence срезы для пяти ведущих признаков и локальное объяснение отдельного прогноза. Локальный метод — усредненная по случайным порядкам аддитивная аппроксимация вклада признаков; это не точное значение SHAP и не причинный вывод.")
    add_heading(document, "9.2. Мониторинг качества и интерфейс", level=2)
    add_body(document, "Для признаков считается PSI между ранним и поздним периодом. Система сохраняет отчет дрейфа и предупреждения; в последнем запуске появился сигнал качества, потому что test WAPE выбранной модели превысил заданный порог 25%. Порог — демонстрационный, его следует настроить на реальных исторических данных и допустимой цене ошибки.")
    add_body(document, "Streamlit-интерфейс разделен на обзор, прогноз, качество модели, качество данных, мониторинг и объяснимость. В нем предусмотрены фильтры по магазину и категории; факт и прогноз сопоставляются с метриками, а источник данных виден пользователю. Код интерфейса проверяется smoke-тестом, но полный контейнерный запуск не выполнялся.")
    add_body(document, "Параметры и метрики моделей сохраняются в локальный JSON-журнал; при установленном MLflow предусмотрено дополнительное логирование. Модель и выбранные признаки сохраняются как артефакты с указанием версии и периода обучения.")

    add_heading(document, "10. Сопоставление с критериями оценки")
    add_body(document, "Матрица ниже показывает реализованные части и ограничения фактической проверки. Она нужна, чтобы при защите не выдавать возможности кода за результаты на данных, которых в эксперименте не было.")
    add_table(
        document,
        ["Критерий", "В проекте", "Подтверждено локально", "Что осталось"],
        [
            ["Источники, 10 баллов", "X5 loader и промо-текстовый канал", "Synthetic-продажи и отдельный synthetic-промо-календарь", "Проверить реальные X5 и промо-данные"],
            ["Обработка/признаки, 15", "ETL, качество, окно и текстовые признаки", "SQLite demo, утечка и повторная загрузка", "Повторить на реальных файлах"],
            ["Модели, 15", "Baseline и три класса моделей", "Chronological validation/test, seed 42", "Сопоставить качество на реальной сети"],
            ["Аналитика, 10", "Прогноз, метрики и Streamlit", "Код и dashboard smoke-тест", "Открыть интерфейс в Docker"],
            ["Дополнительные компоненты, 30", "Интерпретация, PSI, alerts, JSON/MLflow log", "Локальные артефакты, один warning", "Проверить MLflow и расписание в целевой среде"],
            ["Стек, 5", "SQLite/PostgreSQL, Compose, конфигурация, README", "SQLite runtime", "PostgreSQL/Docker не запускались по просьбе пользователя"],
            ["Отчет и материалы, 15", "Подробный Word-отчет и документация", "Отчет, README, архитектура, self-check", "В проекте есть текстовый план, отдельный PPTX не проверялся"],
        ],
        [3.3, 4.2, 4.6, 4.0],
    )
    add_body(document, "Основные функции и артефакты подготовлены для защиты. Однако оценка «отлично» зависит также от демонстрации реальных источников и контейнерного режима преподавателю; ее нельзя гарантировать по синтетическому тесту.")

    add_heading(document, "Заключение")
    add_body(document, "Создан воспроизводимый учебный прототип недельного прогноза продаж товарных категорий. В проекте связаны загрузка разнородных данных, контроль качества, инкрементальное хранение, защита от временной утечки, четыре модели, multi-step прогноз, оценка бизнес-ошибки, интерпретация и мониторинг. Автоматический набор из 18 тестов пройден; локальный прогон завершился и повторная загрузка не добавила новые недельные агрегаты.")
    add_body(document, "Результаты локального эксперимента рассчитаны на синтетических продажах и синтетическом промо-календаре. Чтобы обоснованно претендовать на максимальную оценку, необходимо выполнить инструкции приложений, проверить реальные X5-файлы и показать преподавателю PostgreSQL/дашборд. После замены демонстрационных данных все метрики требуется пересчитать, а выводы о точности — переписать по реальному holdout-периоду.")

    add_heading(document, "Список источников")
    for source in [
        "1. Методические указания к проектному практикуму БВТ. Приложенный PDF-документ, 8 с. Вариант 3 и шкала оценки.",
        "2. X5 RetailHero Uplift dataset. Hugging Face, pytorch-lifestream/retailhero-uplift. URL: https://huggingface.co/datasets/pytorch-lifestream/retailhero-uplift (дата обращения: 17.11.2026).",
        "3. scikit-learn: документация регрессионных моделей, временных оценок и permutation importance. URL: https://scikit-learn.org/.",
        "4. PostgreSQL: официальная документация SQL-сервера. URL: https://www.postgresql.org/docs/.",
        "5. Streamlit: документация интерфейсов и фильтров. URL: https://docs.streamlit.io/.",
    ]:
        add_body(document, source, first_line=False)

    add_heading(document, "Приложение А. Локальный запуск и проверка данных")
    add_body(document, "Локальный сценарий работает на SQLite и не требует Docker. PowerShell-команды:")
    add_code(document, [
        "Copy-Item .env.example .env",
        "python -m pip install -r requirements.txt",
        "python scripts/run_demo.py --local",
        "pytest -q",
    ])
    add_body(document, "Чтобы проверить целевой X5-режим, сначала поместите распакованные или gzip-файлы в data/raw/x5_retailhero, проверьте их схему, затем установите DATA_SOURCE=x5 в `.env` и выполните:")
    add_code(document, [
        "python scripts/verify_x5_dataset.py",
        "python scripts/inspect_x5_dataset.py",
        "python scripts/run_demo.py --local",
    ])
    add_body(document, "Фактический запуск X5 здесь не выполнялся; перед защитой нужно убедиться, что отчет источника показывает X5, а не synthetic fallback.")

    add_heading(document, "Приложение Б. Команды проверки Docker/PostgreSQL")
    add_body(document, "Docker в рамках этой проверки не запускался. Для самостоятельной проверки PostgreSQL-пути в PowerShell выполните:")
    add_code(document, [
        "Copy-Item .env.example .env",
        "docker compose --profile core up -d",
        "python -m pip install -r requirements.txt",
        "python scripts/run_demo.py --database-url postgresql+psycopg2://retail:retail@localhost:5432/retail_forecast",
        "python scripts/db_counts.py --database-url postgresql+psycopg2://retail:retail@localhost:5432/retail_forecast",
        "docker compose --profile core ps",
    ])
    add_body(document, "Ожидаемый результат — контейнер PostgreSQL в состоянии `healthy`, успешное завершение demo и непустые счетчики `sales_raw`, `feature_store`, `forecasts`, `metrics` и `etl_logs`. Для проверки полного интерфейса используйте отдельный режим:")
    add_code(document, [
        "docker compose --profile full up --build",
        "# открыть http://localhost:8501",
        "docker compose --profile full down",
    ])
    add_body(document, "Профиль `full` запускает PostgreSQL, ETL-приложение и Streamlit-дашборд. Если в `.env` задан пароль PostgreSQL со специальными символами, URL подключения следует URL-кодировать.")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document.save(OUTPUT)
    clear_cached_page_statistics(OUTPUT)
    print(OUTPUT)


if __name__ == "__main__":
    build()
