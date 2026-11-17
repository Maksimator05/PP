# Retail Category Weekly Forecast

Учебный проект по дисциплине «Проектный практикум»: прогноз недельных продаж по товарным категориям розничной сети на основе X5 RetailHero или прозрачного синтетического fallback.

## Режимы данных

- `DATA_SOURCE=x5`: обязательный режим реальных данных. Поместите CSV/Parquet-файлы X5 в `data/raw/x5_retailhero/`, затем выполните `make verify-x5` и `make inspect-x5`. Если папка пуста, проект завершится понятной ошибкой и не перейдет на синтетику молча.
- `DATA_SOURCE=synthetic`: автономный режим для демонстрации. Он создает и явно маркирует `synthetic fallback`; это не X5 RetailHero.

Для автоматической попытки загрузки используйте `make download-x5`. Для ручной загрузки положите файл транзакций с распознаваемыми полями даты, магазина, категории и суммы продажи в `data/raw/x5_retailhero/`.

## Быстрый старт

```bash
python -m pip install -r requirements.txt
make demo-local
make test
```

Если `make` недоступен:

```bash
python scripts/download_x5_dataset.py
python scripts/run_demo.py --local
pytest -q
```

## Что делает проект

- автоматически проверяет и скачивает X5 RetailHero из публичных источников;
- при недоступности сети создает явный синтетический fallback;
- приводит данные к канонической схеме;
- строит недельные продажи по магазину и категории;
- извлекает признаки из слабоструктурированных промо-текстов;
- строит leakage-safe признаки;
- обучает seasonal naive, Ridge и CatBoost/fallback boosting;
- считает MAE, RMSE, WAPE и sMAPE;
- сохраняет модель, метрики, processed CSV и профиль датасета;
- запускает Streamlit-дашборд.

## Команды

- `make download-x5`: подготовить датасет.
- `make demo`: основной PostgreSQL сценарий через Docker Compose.
- `make demo-local`: полностью проверенный SQLite fallback для среды без Docker/PostgreSQL.
- `make verify-x5`: проверить локальные реальные файлы X5.
- `make inspect-x5`: построить профиль реального X5.
- `make db-counts`: показать число строк ключевых таблиц.
- `make prefect-all`: запустить именованный orchestration flow локально; с установленным Prefect flow регистрируется как Prefect flow.
- `make test`: быстрые тесты.
- `make dashboard`: открыть дашборд.
- `docker compose --profile core up`: PostgreSQL.
- `docker compose --profile full up --build`: полный профиль.

## Структура

```text
config/                 конфигурация и маппинг X5
dashboard/              Streamlit-приложение
docs/                   отчет, архитектура, словари, самопроверка
retail_forecast/        основной Python-пакет
scripts/                CLI-команды
sql/                    PostgreSQL schema
tests/                  pytest-тесты
data/processed/         созданные обработанные данные
artifacts/              метрики и summary
models/                 сохраненные модели
```

## Архитектура

Подробно описана в `docs/architecture.md`. Коротко: raw files -> canonical loader -> quality checks -> weekly aggregation -> feature engineering -> temporal validation -> models -> monitoring -> dashboard.

## Данные

Основной источник: X5 RetailHero. Поддерживаются HuggingFace и Kaggle. Второй источник: промо-тексты, реальные или детерминированно сгенерированные. Fallback не выдается за реальные данные и явно помечается.

## Результат локального запуска

В текущей среде был создан fallback: 15967 исходных транзакций, 4 намеренно плохие записи были отклонены валидатором, 3840 недельных агрегатов, 3808 строк признаков. После отбора осталось 37 из 40 признаков. Лучшая модель demo-запуска - `catboost_or_histgb`, WAPE 39.69%. Реальные показатели и числа SQL-таблиц лежат в `artifacts/demo_summary.json` и `artifacts/db_row_counts.json`.

## Защита проекта

Покажите `make demo-local`, `make db-counts`, `make test`, `docs/architecture.md`, `docs/self_check.md` и дашборд. Отдельно подчеркните защиту от утечки: все rolling-признаки строятся со сдвигом, а тест проверяет `as_of_date < target_week`.
