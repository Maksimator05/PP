.PHONY: download-x5 init-db load train monitor dashboard test demo clean

download-x5:
	python scripts/download_x5_dataset.py --force

init-db:
	python scripts/init_db.py

load:
	python scripts/load_history.py

train:
	python scripts/train_models.py

monitor:
	python scripts/run_monitoring.py

dashboard:
	streamlit run dashboard/app.py

test:
	pytest -q

demo: download-x5
	python scripts/run_demo.py

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in ['data/processed','models','artifacts','.pytest_cache']]"
