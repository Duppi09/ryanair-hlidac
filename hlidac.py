#!/usr/bin/env python3
"""Hlídač cen letenek Ryanair: Praha (PRG) -> Barcelona (BCN), 1. 2. 2027 tam, 5. 2. 2027 zpět.

Používá veřejné API Ryanairu (stejné, které volá jejich web). Jen standardní knihovna Pythonu.
Při každém spuštění zjistí aktuální nejnižší cenu, uloží ji do historie
a pošle notifikaci, když cena klesne (nebo spadne pod limit).

Konfigurace přes proměnné prostředí (vše volitelné):
  CENOVY_LIMIT     - notifikovat vždy, když je cena za zpáteční let <= této částky (CZK)
  NTFY_TOPIC       - téma na ntfy.sh pro push notifikace do mobilu (aplikace ntfy)
  TELEGRAM_TOKEN, TELEGRAM_CHAT_ID - notifikace přes Telegram bota
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ORIGIN, DEST = "PRG", "BCN"
DATE_OUT, DATE_BACK = "2027-02-01", "2027-02-05"
CURRENCY = "CZK"
HISTORY = Path(__file__).parent / "data" / "historie.json"

API = ("https://services-api.ryanair.com/farfnd/v4/oneWayFares/{o}/{d}/cheapestPerDay"
       "?outboundMonthOfDate={month}&currency={cur}")
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36",
           "Accept": "application/json"}


def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def cheapest_fare(origin, dest, date):
    """Vrátí dict s cenou a časem odletu pro daný den, nebo None (vyprodáno / zatím neprodává se)."""
    data = fetch_json(API.format(o=origin, d=dest, month=date[:8] + "01", cur=CURRENCY))
    for fare in data.get("outbound", {}).get("fares", []):
        if fare.get("day") == date:
            if fare.get("unavailable") or fare.get("soldOut") or not fare.get("price"):
                return None
            return {"cena": fare["price"]["value"], "odlet": fare.get("departureDate"),
                    "prilet": fare.get("arrivalDate")}
    return None


def notify(msg):
    print("NOTIFIKACE:", msg)
    topic = os.environ.get("NTFY_TOPIC")
    if topic:
        req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=msg.encode(),
                                     headers={"Title": "Ryanair PRG-BCN", "Tags": "airplane"})
        urllib.request.urlopen(req, timeout=15)
    token, chat = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if token and chat:
        body = json.dumps({"chat_id": chat, "text": msg}).encode()
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body,
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15)


def main():
    tam = cheapest_fare(ORIGIN, DEST, DATE_OUT)
    zpet = cheapest_fare(DEST, ORIGIN, DATE_BACK)
    now = datetime.now(timezone.utc).isoformat(timespec="minutes")

    if not tam or not zpet:
        print(f"[{now}] Let zatím není v prodeji nebo je vyprodaný (tam: {tam}, zpět: {zpet}).")
        return

    celkem = round(tam["cena"] + zpet["cena"], 2)
    zaznam = {"cas": now, "tam": tam, "zpet": zpet, "celkem": celkem}

    historie = json.loads(HISTORY.read_text()) if HISTORY.exists() else []
    minule = historie[-1]["celkem"] if historie else None
    minimum = min((h["celkem"] for h in historie), default=None)
    historie.append(zaznam)
    HISTORY.parent.mkdir(exist_ok=True)
    HISTORY.write_text(json.dumps(historie, ensure_ascii=False, indent=2))

    text = (f"PRG→BCN {DATE_OUT} ({tam['odlet'][11:16]}): {tam['cena']:.0f} {CURRENCY}\n"
            f"BCN→PRG {DATE_BACK} ({zpet['odlet'][11:16]}): {zpet['cena']:.0f} {CURRENCY}\n"
            f"Celkem: {celkem:.0f} {CURRENCY}")
    print(f"[{now}]\n{text}")

    duvody = []
    limit = os.environ.get("CENOVY_LIMIT")
    if limit and celkem <= float(limit):
        duvody.append(f"pod limitem {float(limit):.0f}")
    if minule is not None and celkem < minule:
        duvody.append(f"zlevnění o {minule - celkem:.0f} (z {minule:.0f})")
    if minimum is not None and celkem < minimum:
        duvody.append("nové historické minimum")
    if minule is None:
        duvody.append("první měření")
    if duvody:
        notify(text + "\n→ " + ", ".join(duvody))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("Chyba:", e, file=sys.stderr)
        sys.exit(1)
