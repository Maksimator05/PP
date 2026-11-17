from retail_forecast.pipeline import run_demo


def test_second_local_run_has_no_new_weeks() -> None:
    database_url = "sqlite:///data/processed/test_incremental.sqlite"
    first = run_demo(database_url=database_url)
    second = run_demo(database_url=database_url)
    assert first["row_counts"]["sales_raw"] == second["row_counts"]["sales_raw"]
    assert second["new_week_rows"] == 0
