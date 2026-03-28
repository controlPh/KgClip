# KgClip (Lightweight Repo)

This repository keeps only source code and project scripts for fast backup/recovery.

## Included
- `app.py`
- `src/`
- `scripts/`
- `requirements.txt`
- config/startup files (`config.py`, `start.bat`, `run_test.ps1`, etc.)

## Not Included (kept local)
- `nuScenes/`
- `models/`
- `derived_data/`
- `csvdata/`
- `milvus_db/`
- `generated_videos/`
- `.venv/`

These directories are excluded by `.gitignore` to keep GitHub storage and clone time small.

## Quick Restore
1. Clone this repo.
2. Create virtual env:
   - `python -m venv .venv`
   - `.\\.venv\\Scripts\\activate`
3. Install dependencies:
   - `pip install -r requirements.txt`
4. Restore local data/model directories as needed (`nuScenes`, `models`, `derived_data`, `csvdata`).
5. Run:
   - `python app.py`

## Notes
- `tools/cloudflared.exe` is intentionally not tracked.
- Runtime logs/cache files are intentionally not tracked.
