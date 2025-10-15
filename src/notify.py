from typing import Optional
import requests
import os

TELEGRAM_API = "https://api.telegram.org"


def send_message(token: str, chat_id: str, text: str):
    """Send a text message via Telegram Bot API.

    Returns the JSON response on success, raises on HTTP/network errors.
    """
    url = f"{TELEGRAM_API}/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    # Allow HTML in messages if user supplies it
    try:
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        # Print to stderr for debugging in logs
        print(f"[notify] send_message error: {exc}", file=os.sys.stderr)
        # Optionally include response body if available
        try:
            print(resp.text, file=os.sys.stderr)
        except Exception:
            pass
        raise


def send_photo(token: str, chat_id: str, photo_path: str, caption: Optional[str] = None):
    """Send a photo file via Telegram Bot API (multipart upload).

    Returns the JSON response on success, raises on HTTP/network errors.
    """
    url = f"{TELEGRAM_API}/bot{token}/sendPhoto"
    data = {"chat_id": chat_id}
    if caption:
        data["caption"] = caption

    if not os.path.exists(photo_path):
        raise FileNotFoundError(photo_path)

    try:
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            resp = requests.post(url, data=data, files=files, timeout=60)
            resp.raise_for_status()
            return resp.json()
    except requests.RequestException as exc:
        print(f"[notify] send_photo error: {exc}", file=os.sys.stderr)
        try:
            print(resp.text, file=os.sys.stderr)
        except Exception:
            pass
        raise
