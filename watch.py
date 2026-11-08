"""Check Sagano Torokko seats for 2026-12-02 (2 adults) every 15 s for ~4.5 min.

Alerts once each time a target train goes from full to having seats, and keeps
watching. LAST_OPEN carries the trains already open from the previous run.
Exits with code 10 once the trip date is reached.
"""
import datetime, json, os, sys, time, urllib.request

URL = "https://common-api.sagano.linktivity.io/v1/search-inventory"
DATE = "2026-12-02"
BOOK = "https://ars-saganokanko.triplabo.jp/activity/ja/LINKTIVITY-YRBTL"
# (label, from_station, to_station, product_id, target departures)
LEGS = [
    ("Saga->Kameoka", 1, 4, 51, ["15:02"]),
    ("Kameoka->Saga", 4, 1, 52, ["15:30"]),
]
RUN_SECONDS = 270
INTERVAL = 15


def check(frm, to, product):
    body = json.dumps({"date": DATE, "from_station_id": frm, "to_station_id": to, "total": 2, "product_id": product}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    data = json.load(urllib.request.urlopen(req, timeout=20))
    return {s["departure_hhmm"]: s.get("available") for s in data.get("services", [])}


def notify(message):
    topic = os.environ["NTFY_TOPIC"]
    req = urllib.request.Request(
        f"https://ntfy.sh/{topic}",
        data=message.encode(),
        headers={"Title": "Sagano train seats open!", "Priority": "urgent", "Tags": "train", "Click": BOOK},
    )
    urllib.request.urlopen(req, timeout=20)


def save_state(open_now):
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"state={','.join(sorted(open_now)) or 'none'}\n")


if __name__ == "__main__":
    if "--test" in sys.argv:
        notify("Test: the Sagano watcher can reach your phone.")
        sys.exit(0)
    if datetime.date.today() >= datetime.date.fromisoformat(DATE):
        print("Trip date reached; nothing to watch.")
        sys.exit(10)
    last = {s for s in os.environ.get("LAST_OPEN", "").split(",") if s and s != "none"}
    end = time.time() + RUN_SECONDS
    while time.time() < end:
        open_now = set()
        for label, frm, to, product, targets in LEGS:
            try:
                avail = check(frm, to, product)
                open_now |= {f"{label} {t}" for t in targets if avail.get(t)}
            except Exception as e:
                print(f"error {label}: {e}", flush=True)
                # Keep a leg's last known state when its check fails.
                open_now |= {s for s in last if s.startswith(label)}
        new = open_now - last
        if new:
            msg = f"2.12, 2 seats: {', '.join(sorted(new))}. Book now: {BOOK}"
            print(msg, flush=True)
            try:
                notify(msg)
            except Exception as e:
                print(f"notify failed: {e}", flush=True)
                open_now -= new  # retry the alert next check
        last = open_now
        time.sleep(INTERVAL)
    save_state(last)
    print(f"Open at end of run: {sorted(last) or 'none'}")
