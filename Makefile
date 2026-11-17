.PHONY: install init-db download-x5 verify-x5 inspect-x5 load-x5 seed-history etl features train inference monitor retrain dashboard test demo demo-local all clean prefect-download prefect-etl prefect-features prefect-train prefect-inference prefect-monitor prefect-all db-counts

install:
	python -m pip install -r requirements.txt

download-x5:
	python scripts/download_x5_dataset.py --force

init-db:
	python scripts/init_db.py

verify-x5:
	python scripts/verify_x5_dataset.py

inspect-x5:
	python scripts/inspect_x5_dataset.py

load:
	python scripts/load_history.py

load-x5: load

seed-history:
	python scripts/run_demo.py

etl:
	python scripts/run_prefect_flow.py ingest_sales_flow

features:
	python scripts/run_prefect_flow.py build_features_flow

train:
	python scripts/train_models.py

inference:
	python scripts/run_prefect_flow.py inference_flow

monitor:
	python scripts/run_monitoring.py

retrain:
	python scripts/run_prefect_flow.py train_models_flow

dashboard:
	streamlit run dashboard/app.py

test:
	pytest -q


demo-local:
	python scripts/run_demo.py --local

demo:
	docker compose --profile core up -d
	python scripts/run_demo.py
	python scripts/db_counts.py

all: demo-local test

prefect-download:
	python scripts/run_prefect_flow.py download_x5_dataset_flow

prefect-etl:
	python scripts/run_prefect_flow.py ingest_sales_flow

prefect-features:
	python scripts/run_prefect_flow.py build_features_flow

prefect-train:
	python scripts/run_prefect_flow.py train_models_flow

prefect-inference:
	python scripts/run_prefect_flow.py inference_flow

prefect-monitor:
	python scripts/run_prefect_flow.py monitoring_flow

prefect-all:
	python scripts/run_prefect_flow.py weekly_pipeline_flow

db-counts:
	python scripts/db_counts.py

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['data/processed','models','artifacts','.pytest_cache']]"
