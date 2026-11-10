import json
import os
import requests
import time
from datetime import datetime
from uuid import uuid4

# --------------------------------
# TELEGRAM EINSTELLUNGEN
# --------------------------------

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# --------------------------------
# BODA BORG EINSTELLUNGEN
# --------------------------------

URL = "https://api.roller.app/api/products/availabilities/widget"

PARAMS = {
    "endDateIndex": "20261114",
    "group": "bodaborgzrichonlinecheckout",
    "startDateIndex": "20261114",
}

HEADERS = {
    "accept": "application/json",
    "origin": "https://checkout.roller.app",
    "referer": "https://checkout.roller.app/",
    "x-api-key": "bodaborgbochum",
    "x-cell-id": "e",
    "x-origin-id": "1",
}

PRODUCT_ID = 827917
INTERVAL = 300

# Bereits gemeldete Sessions
notified = set()

STATE_FILE = "notified_sessions.json"

def load_notified():
    try:
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()

def save_notified():
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(notified), f)

notified = load_notified()


def telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    try:
        response = requests.post(
            url,
            json={
                "chat_id": CHAT_ID,
                "text": message
            },
            timeout=20
        )
        response.raise_for_status()
        return True

    except requests.RequestException as e:
        print("Telegram-Fehler:", e)
        return False


def check_availability():

    headers = HEADERS.copy()
    headers["x-correlationid"] = str(uuid4())

    response = requests.get(
        URL,
        params=PARAMS,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()
    data = response.json()

    available_now = set()

    for product in data.get("products", []):

        for child in product.get("childApiProducts", []):

            if child.get("productId") != PRODUCT_ID:
                continue

            for session in child.get("sessions", []):

                start = session.get("startTime", 0)
                name = session.get("name", "Unbekannt")

                if not (1400 <= start <= 2000):
                    continue

                full = session.get("isSessionCapacityFull", True)
                restricted = session.get("isRestricted", True)

                if not full and not restricted:

                    available_now.add(name)

                    if name not in notified:

                        message = (
                            "🎉 BODA BORG – MÖGLICHE VERFÜGBARKEIT!\n\n"
                            "Datum: 14.11.2026\n"
                            f"Startzeit: {name} Uhr\n"
                            "Produkt: Questing 2 Stunden\n"
                            "Gesucht: mindestens 4 Personen\n\n"
                            "Bitte sofort im Checkout prüfen:\n"
                            "https://checkout.roller.app/bodaborgbochum/"
                            "products/bodaborgzrichonlinecheckout#/sessions"
                        )
                        
                        if telegram(message):
                            notified.add(name)
                            save_notified()

                        print("Mögliche Verfügbarkeit:", name)

    # Wieder freigewordene Meldungen zurücksetzen
    notified.intersection_update(available_now)

    if not available_now:
        print("Keine passenden freien Sessions.")

    else:
        print("Mögliche freie Sessions:", sorted(available_now))


print("=" * 45)
print("BODA BORG CHECKER GESTARTET")
print("Produkt: Questing 2 Stunden")
print("Datum: 14.11.2026")
print("Zeitraum: 14:00–15:30")
print("Prüfung alle 5 Minuten")
print("=" * 45)

telegram("✅ Boda Borg Checker wurde gestartet!")

try:
    print("Prüfung:", datetime.now().strftime("%H:%M:%S"))
    check_availability()

except Exception as e:
    print("Fehler:", e)
    raise