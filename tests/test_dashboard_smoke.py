from dashboard.app import available_pages, load_csv


def test_dashboard_loader_handles_missing_file() -> None:
    frame = load_csv("missing.csv")
    assert frame.empty


def test_dashboard_declares_required_pages() -> None:
    assert set(available_pages()) == {"Обзор", "Прогноз", "Качество модели", "Качество данных", "Мониторинг", "Объяснимость"}
