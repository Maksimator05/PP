# Маппинг X5

Каноническая схема задается в `config/x5_data_mapping.yaml`.

- `transaction_id`: ищется среди `transaction_id`, `receipt_id`, `purchase_id`.
- `transaction_date`: ищется среди `transaction_date`, `date`, `purchased_at`.
- `store_id`: ищется среди `store_id`, `shop_id`.
- `category_id`: ищется среди `category_id`, `level_2`, `product_category`; при отсутствии создается из SKU.
- `product_id`: ищется среди `product_id`, `sku`, `item_id`.
- `sales_amount`: ищется среди `sales_amount`, `amount`, `revenue`, `price`.
- `sales_quantity`: ищется среди `sales_quantity`, `quantity`, `qty`.
- `is_promo`: ищется среди `is_promo`, `promo`, `promotion_flag`.

Если поле отсутствует и его можно безопасно восстановить, создается техническое значение. Если отсутствует дата, загрузка прерывается.
