# RAY — one repository, two core features

RAY is a fresh mobile-first project: **Reimagine** and **AR-guided building**. The payment layer is out of scope for this milestone.

## Responsibilities

- **Vaibhav (architecture/backend)**: FastAPI contracts, authentication verification, validated inventory, project template logic, GLB and scene JSON, integration, review and merges.
- **Sandeep (local inference/hosting)**: Qwen3-VL model in Ollama and hosting FastAPI on his Windows laptop. Qwen returns *material-observation JSON only*. It never generates arbitrary GLB or fabrication instructions.
- **Sanyam (Android)**: React Native app, material-entry flow, 3D GLB viewer, AR placement, part-specific instructions and Supabase UI integration.

## Layout

```text
ray/
├── backend/  # Tested FastAPI + 3D shelf geometry generator + Qwen adapter
├── mobile/   # Placeholder for Sanyam's native Android app (not implemented)
├── docs/     # Shared 3D/component/schema contract
└── .gitignore
```

## Windows host — Sandeep (PowerShell)

Install Git and Python 3.12, ensure Ollama is installed and Qwen model `qwen3-vl:4b-instruct-q4_K_M` is available.

```powershell
# After the GitHub repo is created and pushed by Vaibhav:
git clone https://github.com/OWNER/REPO.git ray
cd ray\backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
notepad .env
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Verify from Sandeep's Windows machine:

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/tags
Invoke-RestMethod http://127.0.0.1:8000/health
```

`.env` should keep `OLLAMA_BASE_URL=http://127.0.0.1:11434` and `OLLAMA_MODEL=qwen3-vl:4b-instruct-q4_K_M` unchanged for same-machine inference. **`GET /health` currently returns `qwen_status: not_checked`, so check `/api/tags` separately.** Protected RAY design APIs require real Supabase configuration and bearer tokens. Without that setup, the API correctly fails closed.

### Model-free geometry preview

```powershell
.\.venv\Scripts\python.exe -m scripts.generate_sample
```

Real preview assets already exist in `backend/examples/`, so Sanyam can develop 3D UI even while live Qwen/Auth integration is pending.

## Android app access to FastAPI

- On a trusted network with client connectivity, Sandeep may listen with `--host 0.0.0.0 --port 8000`, allow ONLY the expected client IPs through Windows Firewall, and Sanyam's phone calls `http://SANDEEP_LAN_IP:8000` (Android cleartext HTTP might require a development-only network config).
- If on different/isolated networks, expose **only FastAPI**, never Ollama, through a suitably secured HTTPS tunnel or deploy the backend. For private testing, a protected private VPN/tunnel can be easier; for external demo, ensure Supabase auth verification is configured first, then use HTTPS.
- Keep Ollama on `127.0.0.1:11434`. Keep FastAPI private unless auth, upload limits and access controls are verified.
- GitHub stores source code but does NOT host FastAPI, Qwen or an Android app.

## GitHub publishing (Vaibhav)

Extract this folder, then from the root:

```bash
cd RAY_GitHub_Starter
git init -b main
git add .
git status
git commit -m "Initialize RAY backend and Android integration workspace"
gh auth login
gh repo create ray --private --source=. --remote=origin --push
```

If an `ray` repo already exists in your account, use a different repository name or add the existing remote instead; do not force-push existing projects. You need GitHub CLI (`gh`) and Git installed. Review `git status` before committing. Do not commit `.env`, API tokens, user photos, generated personal models or model weights.

## Git team workflow

- Sandeep: `git checkout -b feat/qwen-integration` for AI tests, open a PR.
- Sanyam: `git checkout -b feat/android-ar` for mobile app, open a PR.
- Vaibhav: review/merge, validate API changes and run backend tests.
- Everyone: `git pull --rebase` on their working branch as appropriate; never edit Sandeep's host as a substitute for committing changes.

## Current verified scope

The original backend starter's 15 automated tests passed in the prior testing environment. After creating this monorepo structure, rerun tests on Sandeep's Windows laptop to verify installed dependencies and OS compatibility. Only `mini_shelf_v1` (four wood/plywood panels) is supported. The backend exports scene JSON, full GLB and component GLBs. Live Qwen, live Supabase and Android AR integrations are **not yet verified**.
