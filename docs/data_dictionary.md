# Словарь данных

## raw_transactions

- `transaction_id`: уникальный идентификатор транзакции.
- `transaction_date`: дата покупки.
- `store_id`: магазин.
- `category_id`: товарная категория.
- `product_id`: товар или SKU.
- `sales_amount`: сумма продажи, неотрицательная.
- `sales_quantity`: количество, неотрицательное.
- `is_promo`: флаг промо.
- `promo_id`: идентификатор промо.
- `source_name`: источник данных.
- `loaded_at`: время загрузки.

## weekly_sales

- `store_id`, `category_id`, `week_start`: ключ недельного агрегата.
- `sales_amount`: недельная выручка.
- `sales_quantity`: недельное количество продаж.
- `is_promo_week`: была ли промо-активность.
- `source_batch_id`: идентификатор загрузки.

## promo_texts

- `promo_id`: идентификатор промо.
- `promo_text`: слабоструктурированное описание акции.
- `week_start`: неделя действия.

## forecasts

- `model_name`: модель.
- `horizon_weeks`: горизонт прогноза.
- `y_pred`: прогноз продаж.
- `lower_bound`, `upper_bound`: доверительный интервал или эвристический диапазон.

## model_metrics

- `metric_name`: MAE, RMSE, WAPE, sMAPE.
- `metric_value`: значение метрики.
