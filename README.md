# Smart Payment Routing Engine

Picks the best payment gateway for each transaction by cost, latency and reliability,
and automatically fails over to the next best gateway when one fails or times out.
The three gateways (FastPay, QuickPay, BudgetPay) are simulated.

## Run

Requires Docker, Python 3.11+ and Node 18+. Run each command in its own terminal from the repo root:

```bash
docker compose up -d
```

```bash
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
```

```bash
cd frontend && npm install && npm run dev
```

Open http://localhost:5173. API docs are at http://localhost:8000/docs.
Run the tests with `cd backend && pytest` (they use in-memory SQLite, no Postgres needed).

## Architecture

1. `app/config.py` reads scoring weights, exploration rate, timeout and retry limits from env vars.
2. `app/models.py` defines three tables: `gateways`, `transactions`, `attempts` (created on startup).
3. `app/seed.py` inserts the three simulated gateways on first run.
4. `app/gateways.py` simulates a gateway call: jittered sleep, then random failure (much higher when degraded).
5. `app/scoring.py` is a pure function: min-max normalizes fee, latency (both inverted) and success rate, then takes a weighted sum.
6. `app/routing.py` loads each gateway's last 50 attempts, ranks gateways by score, and swaps the top two 10% of the time (epsilon-greedy) so penalized gateways can recover.
7. `process_payment` returns the stored result for a repeated idempotency key; otherwise it tries up to 3 gateways, each with a 2 s `asyncio.wait_for` timeout, recording every attempt.
8. `app/main.py` exposes `POST /payments`, `GET /gateways`, `POST /gateways/{id}/degrade`, `GET /transactions`, `GET /stats` and `POST /simulate`.
9. `POST /simulate` fires N payments concurrently with `asyncio.gather`, each using its own DB session.
10. The React frontend polls the API every 2 seconds and lets you degrade gateways and run simulations live.
