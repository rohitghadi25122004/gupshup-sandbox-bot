from fastapi import FastAPI, Request
import requests
import os

app = FastAPI()

# ===============================
# ENV VARIABLES (SET IN RENDER)
# ===============================
ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")

GRAPH_URL = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"


# ===============================
# SEND MESSAGE
# ===============================
def send_message(to, text):
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    r = requests.post(GRAPH_URL, json=payload, headers=headers)
    print("SEND STATUS:", r.status_code, r.text)


# ===============================
# WEBHOOK VERIFY (META REQUIRED)
# ===============================
@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params

    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == VERIFY_TOKEN
    ):
        return int(params.get("hub.challenge"))

    return {"status": "verification failed"}


# ===============================
# WEBHOOK RECEIVE MESSAGE
# ===============================
@app.post("/webhook")
async def receive_webhook(request: Request):
    data = await request.json()
    print("INCOMING:", data)

    try:
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        if "messages" not in value:
            return {"status": "ignored"}

        message = value["messages"][0]
        sender = message["from"]
        text = message["text"]["body"]

        print("FROM:", sender, "TEXT:", text)

        send_message(sender, f"👋 Hi! You said: {text}")

    except Exception as e:
        print("ERROR:", e)

    return {"status": "ok"}
