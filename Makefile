.PHONY: test backend frontend install

install:
	pip install -e ".[dev]"
	cd frontend && npm install

backend:
	PYTHONPATH=backend uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

test:
	PYTHONPATH=backend pytest -q
	cd frontend && npm run typecheck
