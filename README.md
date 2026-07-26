# Progress Report

Generates BPMN process flow diagrams and progress reports from meeting notes, transcripts, and shared documents.

## Structure

- `frontend/` - React app (Vite)
- `backend/` - Python FastAPI backend
- `data/` - local SQLite database and uploaded files (gitignored)

## Development

Backend:

    cd backend
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload

Frontend:

    cd frontend
    npm install
    npm run dev

See `AGENTS.md` for architecture, conventions, and workflow.
