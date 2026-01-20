from fastapi import FastAPI, Request, Query
import requests
import os

app = FastAPI()

# ===============================
# META CONFIG (ENV VARIABLES)
# ===============================
META_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
META_VERIFY_TOKEN = os.environ.get("META_VERIFY_TOKEN")

if not META_ACCESS_TOKEN or not PHONE_NUMBER_ID or not META_VERIFY_TOKEN:
    raise RuntimeError("Missing required Meta environment variables")

# In-memory state (OK for demo/testing)
user_state = {}
user_data = {}

# ===============================
# SEND MESSAGE (META CLOUD API)
# ===============================
def send_message(to: str, text: str):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    res = requests.post(url, json=payload, headers=headers)
    print("SEND:", res.status_code, res.text)

# ===============================
# META WEBHOOK VERIFICATION (GET)
# ===============================
@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == META_VERIFY_TOKEN:
        return int(hub_challenge)
    return "Verification failed"

# ===============================
# HELPER: EXTRACT META MESSAGE
# ===============================
def extract_meta_message(data: dict):
    try:
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        if "messages" not in value:
            return None, None

        message = value["messages"][0]
        sender = message["from"]
        text = message["text"]["body"]

        return sender, text.strip()
    except Exception as e:
        print("PARSE ERROR:", e)
        return None, None

# ===============================
# WEBHOOK ENDPOINT (POST)
# ===============================
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    print("INCOMING:", data)

    user, text = extract_meta_message(data)

    if not user or not text:
        return {"status": "ignored"}

    text_lower = text.lower()

    # INIT USER
    if user not in user_state:
        user_state[user] = "START"
        user_data[user] = {}

        send_message(
            user,
            "👋 Welcome!\nWhat are you looking for?\n\n1️⃣ Buy Property\n2️⃣ Rent Property"
        )
        return {"status": "ok"}

    # ===============================
    # FLOW LOGIC
    # ===============================
    state = user_state[user]

    if state == "START":
        if text_lower == "1":
            user_state[user] = "BUDGET"
            user_data[user]["type"] = "Buy"
            send_message(user, "💰 What is your budget?")
        elif text_lower == "2":
            user_state[user] = "CITY"
            user_data[user]["type"] = "Rent"
            send_message(user, "📍 Which city are you looking in?")
        else:
            send_message(user, "Please reply with 1 or 2")

    elif state == "BUDGET":
        user_data[user]["budget"] = text
        user_state[user] = "CITY"
        send_message(user, "📍 Which city are you looking in?")

    elif state == "CITY":
        user_data[user]["city"] = text

        summary = (
            f"✅ Details received:\n"
            f"Type: {user_data[user].get('type')}\n"
            f"Budget: {user_data[user].get('budget', 'N/A')}\n"
            f"City: {user_data[user].get('city')}\n\n"
            f"Our agent will contact you shortly."
        )

        send_message(user, summary)

        # CLEAR STATE
        user_state.pop(user, None)
        user_data.pop(user, None)

    return {"status": "ok"}
