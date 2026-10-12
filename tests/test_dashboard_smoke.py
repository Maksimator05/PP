from dashboard.app import load_weekly


def test_dashboard_loader_handles_missing_file() -> None:
    frame = load_weekly("missing.csv")
    assert frame.empty
