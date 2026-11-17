"""Create the detailed Word report from verified local project artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "Отчет по проектному практикуму Розничная торговля.docx"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:fill"), fill)
    tc_pr.append(shading)


def set_cell_text(cell, text: str, bold: bool = False) -> None:
    cell.text = ""
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = paragraph.add_run(text)
    run.bold = bold
    run.font.size = Pt(9)


def table(document: Document, headers: list[str], rows: list[list[str]]) -> None:
    tbl = document.add_table(rows=1, cols=len(headers))
    tbl.style = "Table Grid"
    for index, header in enumerate(headers):
        set_cell_text(tbl.rows[0].cells[index], header, True)
        set_cell_shading(tbl.rows[0].cells[index], "D9EAF7")
    for row in rows:
        cells = tbl.add_row().cells
        for index, value in enumerate(row):
            set_cell_text(cells[index], str(value))
    document.add_paragraph()


def add_heading(document: Document, text: str, level: int = 1) -> None:
    document.add_heading(text, level=level)


def add_body(document: Document, text: str) -> None:
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.first_line_indent = Cm(1.25)
    paragraph.paragraph_format.line_spacing = 1.5
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph.add_run(text)


def setup_styles(document: Document) -> None:
    styles = document.styles
    normal = styles["Normal"]
    normal.font.name = "Times New Roman"
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    normal.font.size = Pt(14)
    for name, size in [("Title", 18), ("Heading 1", 16), ("Heading 2", 14)]:
        style = styles[name]
        style.font.name = "Times New Roman"
        style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
        style.font.size = Pt(size)
        style.font.color.rgb = RGBColor(0, 0, 0)
    footer = document.sections[0].footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("Проектный практикум. Розничная торговля")


def title_page(document: Document) -> None:
    for _ in range(3):
        document.add_paragraph()
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("ОТЧЕТ ПО ПРОЕКТНОМУ ПРАКТИКУМУ").bold = True
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("Розничная торговля\nНедельные продажи по товарным категориям сети").bold = True
    document.add_paragraph()
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.add_run("Направление подготовки: информационные технологии\nДисциплина: Проектный практикум\nТип работы: учебный ML и data engineering проект")
    for _ in range(10):
        document.add_paragraph()
    p = document.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("Москва\n2026")
    document.add_page_break()


def build() -> None:
    summary = json.loads((ROOT / "artifacts" / "demo_summary.json").read_text(encoding="utf-8"))
    metrics = json.loads((ROOT / "artifacts" / "model_metrics.json").read_text(encoding="utf-8"))
    selected = json.loads((ROOT / "artifacts" / "selected_features.json").read_text(encoding="utf-8"))
    counts = json.loads((ROOT / "artifacts" / "db_row_counts.json").read_text(encoding="utf-8"))
    document = Document()
    section = document.sections[0]
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(3)
    section.right_margin = Cm(1.5)
    setup_styles(document)
    title_page(document)

    document.add_heading("Содержание", 1)
    for item in [
        "Введение", "1. Постановка задачи и критерии успеха", "2. Данные и источники", "3. Архитектура и хранение данных",
        "4. ETL, качество и инкрементальная загрузка", "5. Признаки и защита от утечки", "6. Модели и временная валидация",
        "7. Прогнозы, бизнес-метрики и интерпретация", "8. Мониторинг, эксперименты и дашборд", "9. Проверка требований",
        "Заключение", "Список источников", "Приложение А. Команды воспроизведения",
    ]:
        document.add_paragraph(item)
    document.add_page_break()

    add_heading(document, "Введение")
    add_body(document, "Цель работы - создать воспроизводимую систему прогнозирования недельных продаж товарных категорий розничной сети. Система предназначена для категорийного менеджера и аналитика: она помогает оценивать ожидаемую выручку, влияние промо-активностей, риск недопоставки и риск избыточного запаса. Работа охватывает полный жизненный цикл данных и модели: получение данных, контроль качества, хранение, формирование признаков, обучение, мониторинг и представление результатов в интерактивном интерфейсе.")
    add_body(document, "Проект реализован так, чтобы быть запускаемым локально. Основной производственный путь рассчитан на PostgreSQL в Docker Compose. В текущей среде Docker Desktop и PostgreSQL-драйвер отсутствуют, поэтому фактическое демо выполнено в SQLite fallback. Это ограничение зафиксировано явно: synthetic fallback не выдается за X5 RetailHero, а PostgreSQL runtime не отмечается как проверенный.")

    add_heading(document, "1. Постановка задачи и критерии успеха")
    add_body(document, "Целевая переменная - сумма продаж категории за неделю, sales_amount. Объект прогноза задается сочетанием магазина, категории и календарной недели. Основной горизонт - одна неделя, дополнительно рассчитаны прогнозы на 2, 3 и 4 недели. Качество измеряется MAE, RMSE, WAPE и sMAPE, а затем переводится в денежные риски.")
    table(document, ["Критерий", "Практическая реализация"], [
        ["Надежность данных", "Проверка обязательных полей, дат, категорий, дублей, отрицательных и аномальных продаж"],
        ["Отсутствие утечки", "Лаговые и rolling признаки сдвинуты; выполняется проверка as_of_date < target_week"],
        ["Сравнение моделей", "Seasonal naive, Ridge, CatBoost или HistGradientBoosting fallback"],
        ["Воспроизводимость", "Конфигурация, seed, Makefile, Docker Compose, тесты и журнал артефактов"],
    ])

    add_heading(document, "2. Данные и источники")
    add_body(document, "Основной источник для целевого режима - набор X5 RetailHero. Пользователь может поместить файлы в data/raw/x5_retailhero и выполнить проверку командой make verify-x5. Режим DATA_SOURCE=x5 запрещает тихий переход на синтетические данные. Для автономной демонстрации предусмотрен DATA_SOURCE=synthetic: он создает детерминированный набор, аналогичный по канонической схеме, и помечает его как synthetic fallback.")
    add_body(document, "Второй разнородный источник - слабоструктурированные описания промо-акций. Из текста извлекаются числовые признаки: длина текста, число слов, процент скидки, признаки bundle, новинки и распродажи, а также словарные признаки позитивной и негативной тональности. Такая обработка работает офлайн и не требует внешних словарей.")
    table(document, ["Показатель фактического демо", "Значение"], [
        ["Источник", "synthetic fallback, явно отмечен"], ["Исходных транзакций", str(summary["transactions"])],
        ["Отклонено контролем качества", str(summary["rejected_quality_rows"])], ["Недельных агрегатов", str(summary["weekly_rows"])],
        ["Промо-текстов", str(counts["promo_texts_raw"])],
    ])

    add_heading(document, "3. Архитектура и хранение данных")
    add_body(document, "Поток данных состоит из raw layer, канонического загрузчика, блока контроля качества, недельной агрегации, feature store, временной валидации, моделей, прогнозов, мониторинга и Streamlit-дашборда. Конфигурация хранения находится в .env и config/config.yaml. Для PostgreSQL подготовлены таблицы x5_raw_transactions, x5_raw_products, x5_raw_stores, x5_raw_promos, sales_raw, promo_texts_raw, calendar_features, pipeline_state, etl_logs, data_quality_issues, feature_store, forecasts, metrics и monitoring_alerts.")
    table(document, ["Таблица", "Строки в фактическом SQLite demo"], [[key, str(value)] for key, value in counts.items()])
    add_body(document, "Таблицы forecast и sales имеют составные ключи, которые защищают загрузку от повторного появления агрегатов. В локальном fallback данные записываются в data/processed/retail_forecast.sqlite. Для основного режима предусмотрен docker-compose.yml и схема sql/001_schema.sql.")

    add_heading(document, "4. ETL, качество и инкрементальная загрузка")
    add_body(document, "ETL-пайплайн проверяет наличие локального набора, приводит колонки к канонической схеме, удаляет дубли транзакций и агрегирует продажи по понедельникам. В pipeline_state сохраняется последняя обработанная неделя. При повторном запуске в проверенном демо новых недель не обнаружено: new_week_rows равно 0, а размер sales_raw остался равным 3840 строкам.")
    add_body(document, "Для доказательства контроля качества в demo добавляются четыре намеренно плохие записи: отрицательная продажа, пустая категория, пустая дата и дубль идентификатора. Валидатор отправил их в data_quality_issues и не включил в sales_raw. В production такие записи поступают из реального источника без искусственной генерации.")
    table(document, ["Проверка", "Результат"], [
        ["Первый запуск", "3840 недельных строк загружено"], ["Повторный запуск", "0 новых недель"],
        ["Число строк sales_raw после повторного запуска", "3840"], ["Отклоненные записи", "4"],
    ])

    add_heading(document, "5. Признаки и защита от утечки")
    add_body(document, "Единый pipeline признаков формирует лаги 1, 2, 3, 4, 8, 12 и 52 недели, скользящие средние и стандартные отклонения, EWMA, календарные признаки, признаки праздников, промо-флаги, признаки текста и взаимодействия category_x_month и promo_x_holiday. Категории кодируются техническими кодами, target encoding не используется, поэтому нет риска вычислить среднее целевой переменной на всем наборе.")
    add_body(document, "Все агрегаты строятся только на периодах до прогнозируемой недели. Автоматическая проверка требует строгое as_of_date < target_week, а отдельный pytest-тест убеждается, что лаги не обращаются к будущим наблюдениям. До отбора было сформировано {0} признаков, после удаления констант и сильно коррелирующих дублей осталось {1}. Список сохранен в artifacts/selected_features.json.".format(selected["features_before"], selected["features_after"]))

    add_heading(document, "6. Модели и временная валидация")
    add_body(document, "Случайное разбиение не используется. Финальный тест находится в конце временного ряда, а дополнительная функция rolling splits предусматривает embargo между обучением и валидацией. Это защищает оценку от попадания будущей информации в train.")
    rows = []
    for name, values in metrics.items():
        rows.append([name, f"MAE {values['MAE']:.2f}", f"RMSE {values['RMSE']:.2f}", f"WAPE {values['WAPE']:.2%}", f"sMAPE {values['sMAPE']:.2%}"])
    table(document, ["Модель", "MAE", "RMSE", "WAPE", "sMAPE"], rows)
    add_body(document, "Лучшая модель выбирается по минимальному WAPE. В фактическом запуске победила {0}. В этой среде пакет CatBoost не установлен, поэтому под именем catboost_or_histgb фактически работал HistGradientBoostingRegressor. Это явный fallback, а не подмена результата CatBoost.".format(summary["best_model"]))

    add_heading(document, "7. Прогнозы, бизнес-метрики и интерпретация")
    add_body(document, "Для каждой пары магазин-категория создаются прогнозы на горизонты 1-4 недели. Каждая запись содержит модель, версию, магазин, категорию, целевую неделю, горизонт, значение и нижнюю/верхнюю границы. Интервалы строятся из MAE тестового периода; для production необходимо заменить их калиброванными квантильными интервалами.")
    business = summary["business_metrics"]
    table(document, ["Бизнес-показатель", "Значение"], [[key, f"{value:.2f}" if isinstance(value, float) else str(value)] for key, value in business.items()])
    add_body(document, "Глобальная объяснимость реализована через importance признаков: для линейной модели используются абсолютные коэффициенты, для деревьев - встроенная feature importance. Локальные объяснения сохраняют ключевые признаки выбранной модели. При наличии SHAP его можно подключить без изменения структуры артефактов; в текущей среде применяется объяснимый fallback.")

    add_heading(document, "8. Мониторинг, эксперименты и дашборд")
    add_body(document, "Мониторинг сравнивает ранний и последний периоды feature store по PSI. При превышении порогов создаются записи monitoring_alerts. Дополнительно WAPE сравнивается с предупреждающим и критическим порогом. Команда make retrain запускает переобучение, когда мониторинг рекомендует его выполнить.")
    add_body(document, "Журнал экспериментов сохраняет параметры, метрики и результаты моделей в artifacts/model_metrics.json. Если MLflow установлен, тот же код дополнительно отправляет показатели в MLflow. В этой среде MLflow не установлен, поэтому фактически проверен JSON fallback. Дашборд включает страницы Обзор, Прогноз, Качество модели, Качество данных, Мониторинг и Объяснимость. Интерфейс показывает заметный индикатор источника данных.")

    add_heading(document, "9. Проверка требований")
    add_body(document, "Автотесты охватывают загрузчик, маппинг и агрегацию X5, идемпотентность, инкрементальность, защиту от утечки, временные split, модели и smoke-проверку дашборда. Последний запуск pytest завершился успешно: 12 passed. Полная матрица требований с доказательствами приведена в docs/self_check.md.")
    table(document, ["Категория", "Фактический статус"], [
        ["Код, тесты, документация", "Подтверждены локальным запуском"],
        ["SQLite fallback", "Подтвержден: данные, модели, прогнозы, мониторинг"],
        ["PostgreSQL Docker", "Реализован в коде, не запущен: Docker Desktop отсутствует"],
        ["Prefect server", "Есть именованные flows и local fallback; сервер не установлен"],
        ["Реальный X5", "Поддержан, но в текущем запуске недоступен; использован явный synthetic fallback"],
    ])

    add_heading(document, "Заключение")
    add_body(document, "В работе создан проверяемый инженерный ML-проект для недельного прогнозирования продаж товарных категорий. Реализованы управление источниками данных, контроль качества, инкрементальный контракт, feature store, временная валидация, несколько классов моделей, прогнозы на 1-4 недели, бизнес-метрики, мониторинг, интерпретация и дашборд. Локальное демо полностью воспроизводимо и подтверждено 12 автоматическими тестами.")
    add_body(document, "Для перехода от учебного стенда к production-режиму необходимы установка и запуск PostgreSQL/Docker, загрузка реального X5 RetailHero, запуск CatBoost и MLflow, а также калибровка доверительных интервалов. Эти пункты не скрыты и отделены в документации от фактически проверенного локального режима.")

    add_heading(document, "Список источников")
    for source in [
        "X5 RetailHero Uplift Modeling Dataset. Публичный набор данных. URL: https://huggingface.co/datasets/pytorch-lifestream/retailhero-uplift.",
        "Документация scikit-learn. URL: https://scikit-learn.org/.",
        "Документация PostgreSQL. URL: https://www.postgresql.org/docs/.",
        "Документация Prefect. URL: https://docs.prefect.io/.",
        "Документация Streamlit. URL: https://docs.streamlit.io/.",
    ]:
        document.add_paragraph(source)

    add_heading(document, "Приложение А Команды воспроизведения")
    for command in [
        "make demo-local", "make db-counts", "pytest -q", "make verify-x5", "make inspect-x5", "make prefect-all", "make dashboard", "make demo",
    ]:
        p = document.add_paragraph()
        p.add_run(command).font.name = "Courier New"
    document.add_paragraph("Команда make demo предназначена для основного PostgreSQL режима и требует запущенного Docker Desktop. В текущей среде следует использовать make demo-local.")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    document.save(OUT)
    print(OUT)


if __name__ == "__main__":
    build()
