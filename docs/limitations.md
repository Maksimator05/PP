# Ограничения

- Синтетический fallback демонстрирует инженерный контур, но не заменяет реальные данные X5.
- Для production нужны SLA по источникам, полноценный feature store и оркестратор с расписанием.
- Текущая схема доверительных интервалов не реализует статистическую калибровку.
- Горизонты 2-4 недели строятся рекурсивно от последнего доступного feature snapshot; при реальных данных для production нужен direct multi-horizon training.
- Дашборд читает локальные processed CSV в demo-режиме; для команды лучше подключить PostgreSQL.
- SHAP указан как поддерживаемый путь, но в минимальной среде используется fallback на важности признаков.
- Календарь праздников встроенный и упрощенный.
- В текущей среде Docker Desktop, `psycopg2`, Prefect, Streamlit, CatBoost и MLflow не установлены. Поэтому проверен SQLite fallback, локальный orchestration fallback, sklearn HistGradientBoosting и JSON-журнал экспериментов. Основной PostgreSQL путь описан в Docker Compose и SQL-схеме, но не запущен в этой среде.
