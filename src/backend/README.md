# USDT Auction Backend Skeleton

This directory contains the structural layout for the backend services defined in the architecture (Stage 3) and domain design (Stage 4).  
The goal at Stage 9 is to make the environment **ready for implementation** while enforcing the configuration and secret-handling rules.

## Layout

```
src/backend/
├── core/
│   └── app.py             # FastAPI application factory and dependency wiring
├── config/
│   ├── __init__.py
│   └── settings.py        # Configuration loader with Windows Credential Manager support
├── services/
│   └── health.py          # Health-check helpers (placeholder)
├── main.py                # Entry-point for ASGI server (uvicorn)
└── README.md              # This file
```

## FastAPI Application
- `core/app.py` creates the FastAPI instance, registers the `/health` endpoint and wires common middleware (Trace-ID, error handling).
- `main.py` simply exposes the application via `app = create_app()` for `uvicorn`.

## Configuration & Secrets
- `config/settings.py` loads values from environment variables and, if missing, falls back to Windows Credential Manager entries named `USDT_<SECRET_NAME>`.
- See `artefacts/Secrets_Management.md` for full procedures and naming conventions.

## Health Check
- `services/health.py` contains a placeholder that future stages will extend to check Postgres, RabbitMQ and external APIs.
- Stage 9 test `tests/test_healthcheck.py` ensures the `/health` endpoint returns a 200 status with structured output.

## Next Stages
- Stage 10 onwards will add domain-specific services and expand `services/` and `core/` packages.
- CI integration can launch the app with `uvicorn src.backend.main:app --reload`.

> **Note:** No business logic is implemented yet. This skeleton provides a compliant starting point aligned with the architecture, configuration and security guidelines.

