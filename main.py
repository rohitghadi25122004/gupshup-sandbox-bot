from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import requests
import os
import json

app = FastAPI()

# ===============================
# ENV VARIABLES (SET IN RENDER)
# ===============================
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN")

GRAPH_URL = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"


# ===============================
# SEND MESSAGE FUNCTION
# ===============================
def send_message(to: str, text: str):
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    response = requests.post(GRAPH_URL, json=payload, headers=headers)

    print("SEND STATUS:", response.status_code)
    print("SEND RESPONSE:", response.text)


# ===============================
# WEBHOOK VERIFICATION (GET)
# ===============================
@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        # MUST return plain text (not JSON)
        return PlainTextResponse(content=challenge, status_code=200)

    return PlainTextResponse(content="Forbidden", status_code=403)


# ===============================
# WEBHOOK RECEIVER (POST)
# ===============================
@app.post("/webhook")
async def receive_webhook(request: Request):
    body = await request.json()
    print("INCOMING WEBHOOK:")
    print(json.dumps(body, indent=2))

    try:
        entry = body["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        # Ignore status-only webhooks
        if "messages" not in value:
            return {"status": "ignored"}

        message = value["messages"][0]
        sender = message["from"]
        text = message["text"]["body"]

        print(f"FROM: {sender}")
        print(f"TEXT: {text}")

        # Auto-reply
        send_message(sender, f"👋 Hi! You said: {text}")

    except Exception as e:
        print("ERROR PROCESSING WEBHOOK:", e)

    return {"status": "ok"}
