
import json
import os
import base64
import requests
from datetime import datetime
from uuid import uuid4

# --------------------------------
# TELEGRAM EINSTELLUNGEN
# --------------------------------

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

# --------------------------------
# GITHUB SPEICHERUNG
# --------------------------------

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPO = "npoa-cm/npoa-cm-boda-borg-checker"
STATE_FILE = "notified_sessions.json"
BRANCH = "main"

GITHUB_API = (
    f"https://api.github.com/repos/{GITHUB_REPO}"
    f"/contents/{STATE_FILE}"
)

GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}

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

# --------------------------------
# MELDESTATUS AUS GITHUB LADEN
# --------------------------------

def load_notified():

    response = requests.get(
        GITHUB_API,
        headers=GITHUB_HEADERS,
        params={"ref": BRANCH},
        timeout=20
    )

    if response.status_code == 404:
        print("Noch keine Statusdatei in GitHub vorhanden.")
        return set()

    response.raise_for_status()

    file_data = response.json()

    content = base64.b64decode(
        file_data["content"]
    ).decode("utf-8")

    return set(json.loads(content))


notified = load_notified()


# --------------------------------
# MELDESTATUS IN GITHUB SPEICHERN
# --------------------------------

def save_notified():

    # Aktuelle SHA abrufen, falls die Datei bereits existiert
    response = requests.get(
        GITHUB_API,
        headers=GITHUB_HEADERS,
        params={"ref": BRANCH},
        timeout=20
    )

    sha = None

    if response.status_code == 200:
        sha = response.json()["sha"]

    elif response.status_code != 404:
        response.raise_for_status()

    content = json.dumps(
        sorted(notified),
        indent=2
    )

    encoded_content = base64.b64encode(
        content.encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": "Update Boda Borg notification state",
        "content": encoded_content,
        "branch": BRANCH,
    }

    if sha:
        payload["sha"] = sha

    response = requests.put(
        GITHUB_API,
        headers=GITHUB_HEADERS,
        json=payload,
        timeout=20
    )

    response.raise_for_status()

    print("Meldestatus erfolgreich in GitHub gespeichert.")


# --------------------------------
# TELEGRAM
# --------------------------------

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


# --------------------------------
# VERFÜGBARKEIT PRÜFEN
# --------------------------------

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

                if not (1400 <= start <= 1530):
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

    # Nicht mehr verfügbare Sessions zurücksetzen

    previous = set(notified)

    notified.intersection_update(available_now)

    if notified != previous:
        save_notified()

    if not available_now:
        print("Keine passenden freien Sessions.")

    else:
        print(
            "Mögliche freie Sessions:",
            sorted(available_now)
        )


# --------------------------------
# HAUPTPROGRAMM
# --------------------------------

print("=" * 45)
print("BODA BORG CHECKER GESTARTET")
print("Produkt: Questing 2 Stunden")
print("Datum: 14.11.2026")
print("Zeitraum: 14:00–15:30")
print("Prüfung: Einzelner Durchlauf")
print("=" * 45)

print(
    "Prüfung:",
    datetime.now().strftime("%H:%M:%S")
)

try:
    check_availability()

except Exception as e:
    print("Fehler:", e)
    raise
