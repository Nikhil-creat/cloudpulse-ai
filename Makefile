up:      ; docker compose up -d --build
down:    ; docker compose down
logs:    ; docker compose logs -f api worker
test:    ; cd backend && pytest -q
train:   ; cd backend && python -m app.cnn.train
seed:    ; docker compose exec api python -m scripts.seed_demo
migrate: ; docker compose exec api sh -c "alembic revision --autogenerate -m baseline && alembic upgrade head"
eval:    ; docker compose exec api python -m app.evals.harness
