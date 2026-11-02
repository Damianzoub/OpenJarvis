.PHONY: frontend backend eval_gate run_evals qdrant index test fake_device agent_stop agent_start

frontend:
	cd frontend && npm run dev

backend:
	cd backend && uvicorn main:app --reload

eval_gate:
	python evals/evaluators/retrieval_gate.py

run_evals:
	cd evals/evaluators && python run_evals.py

qdrant: 
	colima start
	cd backend/vectorDB && docker compose up -d

index:
	cd backend && python -m rag.offline

test:
	cd backend && pytest

fake_device:
	python evals/test/fake_device.py

agent_stop:
	launchctl bootout gui/$$(id -u)/com.openjarvis.backend

agent_start:
	launchctl bootstrap gui/$$(id -u) ~/Library/LaunchAgents/com.openjarvis.backend.plist