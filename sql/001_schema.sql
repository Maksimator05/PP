CREATE TABLE IF NOT EXISTS x5_raw_transactions (
    transaction_id TEXT PRIMARY KEY,
    transaction_date DATE NOT NULL,
    store_id TEXT NOT NULL,
    category_id TEXT NOT NULL,
    product_id TEXT,
    sales_amount NUMERIC(14, 2) NOT NULL CHECK (sales_amount >= 0),
    sales_quantity NUMERIC(14, 3) NOT NULL CHECK (sales_quantity >= 0),
    is_promo BOOLEAN NOT NULL DEFAULT FALSE,
    promo_id TEXT,
    source_name TEXT NOT NULL,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS x5_raw_products (
    product_id TEXT PRIMARY KEY,
    category_id TEXT,
    product_name TEXT,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS x5_raw_stores (
    store_id TEXT PRIMARY KEY,
    store_name TEXT,
    region TEXT,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS x5_raw_promos (
    promo_id TEXT PRIMARY KEY,
    store_id TEXT,
    category_id TEXT,
    week_start DATE,
    promo_text TEXT,
    loaded_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sales_raw (
    store_id TEXT NOT NULL,
    category_id TEXT NOT NULL,
    week_start DATE NOT NULL,
    sales_amount NUMERIC(14, 2) NOT NULL CHECK (sales_amount >= 0),
    sales_quantity NUMERIC(14, 3) NOT NULL CHECK (sales_quantity >= 0),
    is_promo_week BOOLEAN NOT NULL DEFAULT FALSE,
    transactions_count INTEGER NOT NULL DEFAULT 0,
    source_batch_id TEXT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (store_id, category_id, week_start)
);

CREATE TABLE IF NOT EXISTS promo_texts_raw (
    promo_id TEXT,
    store_id TEXT NOT NULL,
    category_id TEXT NOT NULL,
    week_start DATE NOT NULL,
    promo_text TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS calendar_features (
    week_start DATE PRIMARY KEY,
    weekofyear INTEGER,
    month INTEGER,
    quarter INTEGER,
    is_holiday BOOLEAN
);

CREATE TABLE IF NOT EXISTS pipeline_state (
    state_key TEXT PRIMARY KEY,
    state_value TEXT NOT NULL,
    stage TEXT NOT NULL,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS etl_logs (
    run_id TEXT PRIMARY KEY,
    stage TEXT NOT NULL,
    status TEXT NOT NULL,
    rows_processed INTEGER DEFAULT 0,
    message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS data_quality_issues (
    issue_id TEXT PRIMARY KEY,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'error',
    transaction_id TEXT,
    message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS feature_store (
    store_id TEXT NOT NULL,
    category_id TEXT NOT NULL,
    week_start DATE NOT NULL,
    target_week DATE NOT NULL,
    target_sales_amount NUMERIC(14, 2),
    as_of_date DATE NOT NULL,
    PRIMARY KEY (store_id, category_id, target_week)
);

CREATE TABLE IF NOT EXISTS forecasts (
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    store_id TEXT NOT NULL,
    category_id TEXT NOT NULL,
    target_week DATE NOT NULL,
    horizon INTEGER NOT NULL,
    forecast_value NUMERIC(14, 2) NOT NULL,
    lower_bound NUMERIC(14, 2),
    upper_bound NUMERIC(14, 2),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (model_name, model_version, store_id, category_id, target_week, horizon)
);

CREATE TABLE IF NOT EXISTS metrics (
    run_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    split_name TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value NUMERIC(14, 6) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (run_id, model_name, split_name, metric_name)
);

CREATE TABLE IF NOT EXISTS monitoring_alerts (
    alert_id TEXT PRIMARY KEY,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    entity_id TEXT,
    message TEXT NOT NULL,
    metric_value NUMERIC(14, 6),
    threshold_value NUMERIC(14, 6),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
