"""Run Prefect-named flows locally, with a fallback when Prefect is not installed."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from retail_forecast.prefect_flows import run_named_flow


if __name__ == "__main__":
    flow_name = sys.argv[1] if len(sys.argv) > 1 else "weekly_pipeline_flow"
    print(run_named_flow(flow_name))
