# NEPSE AI — ML Service (Phase 4)

Standalone FastAPI microservice that adds the intelligence layer: price
prediction, trend & volatility classification, and fused trading signals — kept
separate from the core backend for independent scaling.

## Stack
FastAPI · XGBoost (primary) · scikit-learn (RandomForest baseline) · pandas /
numpy · joblib model registry · Redis (cache + rate limit) · shared-JWT auth.

## Pipeline

```
OHLCV history (Postgres or synthetic)
   → feature engineering (SMA/EMA/RSI/MACD/Bollinger/momentum/volatility)
   → training (XGBoost; time-ordered split; RF baseline logged)
   → versioned model registry (joblib + meta.json with RMSE/F1/accuracy)
   → FastAPI serving (cache + rate limit + fallback)
```

## Endpoints (JWT access token **or** `X-API-Key`)

| Method | Path | Purpose |
|---|---|---|
| GET  | `/health` | liveness |
| GET  | `/models` | registry versions + metrics |
| POST | `/models/reload` | hot-reload latest models after retrain |
| POST | `/predict/price` | next-bar price + confidence |
| POST | `/predict/trend` | UPTREND / DOWNTREND / SIDEWAYS |
| POST | `/predict/volatility` | LOW / MEDIUM / HIGH |
| POST | `/signal/stock` | fused BUY / SELL / HOLD (+ reasons) |
| POST | `/predict/batch` | many symbols at once |

`features` and `history` are optional in every request — omit them and the
service loads recent history for the symbol itself.

```bash
curl -X POST localhost:8100/predict/price -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"symbol":"NABIL","features":{"open":520,"high":530,"low":515,"close":525,"volume":120000}}'
# {"symbol":"NABIL","predicted_price":528.97,"predicted_return":0.00756,"confidence":0.508,...}
```

## Run

```bash
cd ml_service
cp .env.example .env          # set SECRET_KEY == the core backend's SECRET_KEY
python -m venv .venv && source .venv/Scripts/activate
pip install -r requirements.txt
python -m training.train      # writes model_store/
uvicorn app:app --port 8100   # http://localhost:8100/docs
pytest                        # 9 tests, no DB/Redis needed
```

## Design notes

- **Auth**: validates JWTs with the *same* `SECRET_KEY` as the core backend, so
  a logged-in user's access token works directly — no separate login.
- **Resilience**: prediction cache + rate limiter fail open if Redis is down; a
  missing/insufficient model degrades to a deterministic heuristic
  (`fallback: true`) so the API never hard-fails.
- **Data**: `USE_DB=true` reads real OHLCV from the platform's Postgres; default
  uses a seeded synthetic generator so the service trains/serves standalone.
- **Confidence**: classifiers report `max(predict_proba)`; price reports the
  validation directional accuracy (a calibrated proxy).
- Metrics on synthetic data hover near baseline by design (it is close to a
  random walk) — the pipeline is what's validated; real NEPSE history carries
  more signal. Retrain with `python -m training.train` then `POST /models/reload`.

## Future (per spec)
LSTM/Transformer price models, FinBERT news sentiment, RL trading agent,
portfolio optimization — all slot in as new registry model names.
