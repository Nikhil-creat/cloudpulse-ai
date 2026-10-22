up:      ; docker compose up -d --build
down:    ; docker compose down
logs:    ; docker compose logs -f api worker
test:    ; cd backend && pytest -q
train:   ; cd backend && python -m app.cnn.train
