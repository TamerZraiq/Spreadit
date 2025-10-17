# Minimal Makefile with start/stop
APP = app.main:app
PID_FILE = .uvicorn.appPID_FILE

install:
	pip install -r requirements.txt

run:
	python -m uvicorn $(APP) --host 0.0.0.0 --port 8000 --reload


test:
	python -m pytest -q