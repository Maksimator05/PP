# Самопроверка по критериям проекта

| Требование | Статус | Доказательство | Где проверить |
|---|---|---|---|
| Режимы X5 и synthetic | Выполнено | `DATA_SOURCE=x5` блокирует silent fallback; `synthetic` маркируется в summary и dashboard | `retail_forecast/downloader.py`, `make verify-x5` |
| Ручная папка X5 | Выполнено | Локальная папка проверяется до скачивания и fallback | `data/raw/x5_retailhero/`, `make verify-x5` |
| Автозагрузка и fallback | Выполнено | HuggingFace/Kaggle с retry; fallback имеет manifest | `scripts/download_x5_dataset.py`, `logs/download.log` |
| PostgreSQL как основной путь | Выполнено в коде, не проверено runtime | Docker Compose и SQL schema готовы; Docker Desktop недоступен в среде | `docker-compose.yml`, `sql/001_schema.sql`, `make demo` |
| Локальный SQL fallback | Выполнено и проверено | SQLite хранит ключевые таблицы, строковые счетчики сохранены | `make demo-local`, `artifacts/db_row_counts.json` |
| Полный перечень SQL-таблиц | Выполнено | Raw, sales, features, forecasts, metrics, monitoring, logs, state | `sql/001_schema.sql` |
| Инкрементальность | Выполнено | `pipeline_state.last_processed_week`; второй запуск сообщает «новых данных нет» | `retail_forecast/pipeline.py`, `tests/test_incremental_etl.py` |
| Идемпотентность | Выполнено | Уникальные ключи SQL и тесты; `sales_raw` остается 3840 | `sql/001_schema.sql`, `tests/test_etl_idempotency.py` |
| Качество данных | Выполнено | Проверка отрицательных продаж, даты, категории, дублей, аномалий; 4 записи отклонены | `retail_forecast/quality.py`, `data_quality_issues` |
| Признаки | Выполнено | Лаги 1/2/3/4/8/12/52, rolling, EWMA, календарь, промо и текст | `retail_forecast/features.py` |
| Защита от утечки | Выполнено | Проверка `as_of_date < target_week` и тест | `tests/test_feature_leakage.py` |
| Отбор признаков | Выполнено | Удаление констант и коррелирующих признаков; 40 -> 37 | `artifacts/selected_features.json` |
| Модели | Выполнено | Seasonal naive, Ridge, CatBoost или HistGradientBoosting fallback | `retail_forecast/models.py`, `artifacts/model_metrics.json` |
| CatBoost | Частично | Код использует CatBoost при установке; текущая среда использовала HistGradientBoosting fallback | `requirements.txt`, `docs/limitations.md` |
| Горизонты 1-4 | Выполнено | 128 прогнозов с границами интервала | `data/processed/forecasts.csv`, `forecasts` |
| Бизнес-метрики | Выполнено | Ошибка в рублях, risks understock/overstock, доля ошибок >20% | `artifacts/business_metrics.json` |
| Интерпретируемость | Выполнено с fallback | Feature importance и local explanations | `artifacts/feature_importance.csv`, `artifacts/local_explanations.csv` |
| Мониторинг | Выполнено | PSI, alerts, рекомендация retrain | `retail_forecast/monitoring.py`, `monitoring_alerts` |
| MLflow/эксперименты | Частично | JSON журнал работает; MLflow подключится при установке | `artifacts/model_metrics.json`, `retail_forecast/experiments.py` |
| Prefect orchestration | Выполнено с fallback | 11 именованных flow; Prefect-native режим доступен при установке | `retail_forecast/prefect_flows.py`, `make prefect-all` |
| Dashboard | Выполнено в коде | Шесть разделов, источник данных, экспорт, качество и объяснимость | `dashboard/app.py`, `tests/test_dashboard_smoke.py` |
| Тесты | Выполнено | 12 tests passed | `pytest -q` |
| Git история | Частично | Скрипт логичных коммитов подготовлен; коммиты не созданы без явного запроса пользователя | `scripts/create_git_history.sh` |
