from retail_forecast.pipeline import run_demo


def test_second_local_run_has_no_new_weeks(tmp_path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'test_incremental.sqlite').as_posix()}"
    first = run_demo(database_url=database_url)
    second = run_demo(database_url=database_url)
    assert first["row_counts"]["sales_raw"] == second["row_counts"]["sales_raw"]
    assert second["new_week_rows"] == 0
    assert second["promo_text_source"] == "synthetic_promo_calendar"
    assert second["row_counts"]["promo_texts_raw"] > 0
