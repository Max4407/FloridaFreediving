# Florida Freediving

Club dive registration and officer coordination application.

## Local development

Backend (Python 3.12+):

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
alembic upgrade head
uvicorn main:app --reload
```

Frontend:

```powershell
cd frontend
npm install
npm run dev
```

Vite proxies `/api` and `/health` to `http://localhost:8000`. The backend defaults to a local SQLite database; set `DATABASE_URL` to use PostgreSQL.

Copy `.env.example` to `.env`, generate the bcrypt password hash described there, and never commit the resulting file.

## Verification

```powershell
cd backend
pytest
ruff check .

cd ../frontend
npm test
npm run build
```

See `docs/PLAN.md` for product decisions and `infra/README.md` for AWS deployment.

