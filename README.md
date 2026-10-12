# Retail Category Weekly Forecast

Учебный проект по дисциплине «Проектный практикум»: прогноз недельных продаж по товарным категориям розничной сети на основе X5 RetailHero или прозрачного синтетического fallback.

## Быстрый старт

```bash
python -m pip install -r requirements.txt
make demo
make test
```

Если `make` недоступен:

```bash
python scripts/download_x5_dataset.py
python scripts/run_demo.py
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
- `make demo`: полный локальный pipeline.
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

В текущей среде был создан fallback: 15967 транзакций, 3840 недельных агрегатов, 3808 строк признаков. Лучшая модель demo-запуска - Ridge, WAPE около 39.6%.

## Защита проекта

Покажите `make demo`, `make test`, `docs/architecture.md`, `docs/self_check.md` и дашборд. Отдельно подчеркните защиту от утечки: все rolling-признаки строятся со сдвигом, а тест проверяет `as_of_date < target_week`.
