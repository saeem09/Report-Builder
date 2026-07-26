# AGENTS.md

Conventions and context for any AI coding agent working in this repository.

## Project Overview

An application that generates BPMN process flow diagrams and progress reports from meeting outcomes, shared files, meeting notes, and transcripts. Progress reports are updated after every subsequent meeting on the same topic.

MVP scope: no user accounts, single local user, dev-server only (no deployment target yet).

## Business Requirements

- Create BPMN-format process flow diagrams and progress reports
- Progress reports: user defines report fields per report; AI drafts content per field from source material; user can freely edit afterward
- Report fields are reorderable via drag-and-drop
- A list page for generated reports and diagrams, filterable by name or date
- Process flow diagrams are fully editable in-app: actors, decisions, text, box position
- Company logos can be uploaded and appear in exported outputs
- Input formats: Word, TXT, PDF, HTML
- Output formats: HTML (diagrams), PDF (reports) — both include the company logo
- UI/UX priority: sleek, modern, elegant; blues/greys/blacks/whites only (palette below)

## Architecture

```
frontend/   React SPA (Vite)
backend/    Python (FastAPI) - parsing, LLM calls, PDF rendering, storage
data/       SQLite DB file + uploaded documents/logos
```

No monorepo tooling; each app manages its own dependencies (npm in frontend/, pip/uv in backend/).

## Tech Stack

**Frontend**
- React 19 + Vite, TypeScript strict mode
- Tailwind CSS + shadcn/ui, themed with the palette below (reference tokens, never raw hex in components)
- dnd-kit for drag-and-drop field reordering
- bpmn-js for BPMN diagram rendering/editing (in-app only — exported HTML is a static, view-only rendering with the logo embedded, not a live editor)

**Backend**
- Python + FastAPI
- python-docx, pdfplumber, BeautifulSoup4 for document parsing (Word/PDF/HTML/TXT) — parsing never touches the LLM
- sqlite3 for storage (reports, diagrams, field content, file metadata)
- Anthropic Python SDK for the LLM step (see AI / Token-Cost Discipline)
- WeasyPrint for rendering the report view to PDF

## Domain Model

- **Report**: id, name, created/updated timestamps, ordered list of fields, logo reference
- **Field**: id, label (user-defined, freeform), order, content (AI-drafted rich text, user-editable)
- **Diagram**: id, name, created/updated timestamps, BPMN element graph (actors/lanes, tasks, gateways/decisions, flows, text), logo reference
- Meeting updates append/refresh the current report and diagram in place — there is no separate version history per meeting (flag if per-meeting snapshots are wanted instead)

## AI / Token-Cost Discipline

The LLM (Claude, via Anthropic Python SDK) is reserved for genuine language synthesis only:
- Drafting report field content from parsed source text
- Organizing extracted meeting content into BPMN structure (actors, decisions, flow)

Never call the LLM for: document parsing, CRUD/storage, list/filter/sort, drag-and-drop reordering, or PDF/HTML export/rendering. These are deterministic library code.

Rules:
- Preprocess before sending anything to the LLM: strip boilerplate (timestamps, filler, headers/footers), dedupe repeated text, trim to relevant content with plain string/regex logic
- Batch generation: one LLM call per report/diagram update covering all fields/elements at once, not one call per field
- Respect user edits: never regenerate a field or diagram element the user manually edited, unless they explicitly request regeneration
- Cache and reuse: if source documents are unchanged since the last generation, reuse the prior LLM output instead of re-calling the API
- Default to the cheapest capable Claude model for extraction/drafting tasks (e.g. Haiku); escalate only if quality demands it
- Use Anthropic prompt caching for repeated system instructions across calls in the same session

## Development Workflow

**Planning**: Use the `writing-plans` skill (superpowers) to turn an approved feature/design into a phased implementation plan with success criteria per phase. Use a business-analyst-style pass to draft user stories and acceptance criteria per phase. The user reviews and approves the plan/stories before implementation starts — this is the main business checkpoint.

**Execution**: Use the `subagent-driven-development` skill (superpowers) to run the build loop:
- A fresh implementer subagent per task (writes code + tests, commits, self-reviews)
- A fresh task-reviewer subagent per task (spec compliance + code quality), with a fix loop until clean
- A final whole-branch reviewer once all tasks are done
- Runs continuously without pausing for check-ins once the plan is approved

Model tiering (cost control):
- Cheap/fast model: mechanical tasks with a clear spec touching 1-2 files
- Standard model: multi-file integration or judgment calls
- Most capable model: architecture-level decisions and the final whole-branch review

User checkpoints (business only): plan/user-story approval before execution starts; a batched pre-flight conflict check if tasks contradict each other or the plan; an implementer reporting BLOCKED that cannot be resolved automatically; any change to scope or requirements mid-build. Everything else (naming, internal refactors, fixing review findings) is resolved by the agents per this file's conventions.

## Design System

Color palette (blues/greys/blacks/whites only, no other hues):
`#00496A` `#476C83` `#013554` `#5283A8` `#5282A8` `#00487F` `#0A4677` `#1C2835` `#1F497D` `#13417F` `#E9F5FF` `#E9F4FF` `#D9D9D9` `#7F7F7F` `#F2F2F2`

Wire these as named Tailwind theme tokens; never hardcode hex values in components.

## Testing

- Unit tests: Vitest + React Testing Library (frontend), pytest (backend)
- Integration tests: API endpoints, document parsing, PDF/HTML export
- E2E tests: Playwright, covering the golden path (upload docs -> generate report/diagram -> edit -> export) and edge cases
- Minimum 80% coverage; TDD (test first) for all new features
- Fix implementation, not tests, unless the test itself is wrong

## Coding Conventions

- Immutability: never mutate existing objects/state; always produce new copies
- KISS/YAGNI: simplest solution that works; no speculative abstractions or features
- Naming: camelCase (TS) / snake_case (Python) for variables/functions, PascalCase for components/types, UPPER_SNAKE_CASE for constants
- Files: many small, focused files over few large ones; extract when a file grows unwieldy
- Error handling: validate all input at system boundaries (uploads, API requests); explicit error handling everywhere; never swallow errors silently
- No hardcoded secrets: Anthropic API key via environment variable only
- No emojis anywhere in code, UI copy, or docs

## Open Decisions (flag on review, adjust as needed)

- Field model has no per-field "type" beyond freeform rich text — confirm this is sufficient
- No per-meeting version history — each update overwrites/extends the current report/diagram in place
- Exported diagrams are static/view-only HTML; re-editing requires reopening in-app
- No deployment target defined yet; MVP runs via local dev servers only
