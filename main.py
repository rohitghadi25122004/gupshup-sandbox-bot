from fastapi import FastAPI, Request
import requests
import os

app = FastAPI()

# Default configuration values (used if environment variables are not set)
DEFAULT_META_ACCESS_TOKEN = (
    "EAAQ7NuZBI7zoBQm3JYZAohAXjtGpx5qW2NVh1woF9ZBkhpHHfeeZBY1vZBnt9Y1TlR8BLYjZAWoji2yn9RhO8qNLDUDalpbwYxlOqniIB156IUx0HCX0ZBmdN7KSlb7IVTUfyg8MM1Ue9QjBMFZCRzLxsfYhn0QJgzOqf6W61syrpqv0fVtqjecdYmlhfL3uwZCtKzwLU9g9ZC9CW44MpuadlM0qaf73GPup7oG6Ha0xho01ARZAuLswi0MrGEWNnZCIzDZBHQyYI9g7lZC2GvRguTkv54tsPs"
)
DEFAULT_VERIFY_TOKEN = "wprealestatebot25"
DEFAULT_PHONE_NUMBER_ID = "927697687099353"

# Read from environment variables, falling back to the defaults above
META_TOKEN = os.getenv("META_ACCESS_TOKEN", DEFAULT_META_ACCESS_TOKEN)
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", DEFAULT_PHONE_NUMBER_ID)
# Support both VERIFY_TOKEN and META_VERIFY_TOKEN, with a default fallback
VERIFY_TOKEN = os.getenv(
    "VERIFY_TOKEN",
    os.getenv("META_VERIFY_TOKEN", DEFAULT_VERIFY_TOKEN),
)

GRAPH_URL = f"https://graph.facebook.com/v22.0/{PHONE_NUMBER_ID}/messages"


# ===============================
# SEND MESSAGE
# ===============================
def send_message(to, text):
    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {
            "body": text
        }
    }

    r = requests.post(GRAPH_URL, json=payload, headers=headers)
    print("Send response:", r.status_code, r.text)


# ===============================
# META VERIFICATION (GET)
# ===============================
@app.get("/webhook")
async def verify(
    hub_mode: str = None,
    hub_challenge: str = None,
    hub_verify_token: str = None
):
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        return int(hub_challenge)
    return "Verification failed"


# ===============================
# RECEIVE MESSAGE (POST)
# ===============================
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    print("Incoming payload:", data)

    try:
        entry = data["entry"][0]
        change = entry["changes"][0]
        value = change["value"]

        if "messages" not in value:
            return {"status": "ignored"}

        message = value["messages"][0]

        user = message["from"]
        text = message["text"]["body"]

        print("User:", user, "Message:", text)

        # ---- BOT LOGIC ----
        send_message(user, f"👋 Hello Rohit! You said: {text}")

    except Exception as e:
        print("Error:", e)

    return {"status": "ok"}
