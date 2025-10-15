# Price Watcher (Nike Perú)

## Local
1. `cp config/settings.example.env .env` y edita valores.
2. `python -m pip install -r requirements.txt`
3. `python -m playwright install --with-deps`
4. `python -m src.main`

## Producción (GitHub Actions)
Crea estos *secrets* en el repo:
- `QUERY` = "Nike Dunk Low Retro"
- `THRESHOLD` = "549"
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `SEND_SCREENSHOT_ALWAYS` = "true" o "false"

El workflow corre cada 8 h y puedes dispararlo manualmente.
