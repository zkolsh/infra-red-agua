VENV := .venv
PYTHON := $(VENV)/bin/python
C_DIR := graph_engine

CC := gcc

.PHONY: venv dev release build debug c-release test clean

venv:
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -r requirements.txt

dev: c-debug
	LD_PRELOAD=$$($(CC) -print-file-name=libasan.so) $(VENV)/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --log-level debug

release: c-release
	$(VENV)/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

build: c-release

c-debug:
	$(MAKE) -C $(C_DIR) clean
	$(MAKE) -C $(C_DIR) debug

c-release:
	$(MAKE) -C $(C_DIR) clean
	$(MAKE) -C $(C_DIR) release

test:
	$(PYTHON) -m pytest

clean:
	rm -rf $(VENV) .pytest_cache
	$(MAKE) -C $(C_DIR) clean
	find . -type d -name __pycache__ -exec rm -rf {} +

