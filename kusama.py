"""Check Yayoi Kusama Museum tickets for 12-15 Nov 2026 every 15 s for ~4.5 min.

Sends an ntfy push and exits with code 10 when one of the target days has tickets.
"""
import datetime, json, os, sys, time, urllib.request

URL = "https://www.etix.com/kketix/api/onlineSale/timedEntry/2011784/monthData?year=2026&month=11"
BOOK = "https://www.e-tix.jp/yayoikusamamuseum/en/"
TARGET_DAYS = ["12", "13", "14", "15"]
LAST_DAY = datetime.date(2026, 11, 15)
RUN_SECONDS = 270
INTERVAL = 15


def open_days():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    data = json.load(urllib.request.urlopen(req, timeout=20))
    # Days with tickets left sit under the key that starts with "A-".
    available = next((v for k, v in data.items() if k.startswith("A-")), {})
    return [d for d in TARGET_DAYS if d in available]


def notify(message):
    topic = os.environ["NTFY_TOPIC"]
    req = urllib.request.Request(
        f"https://ntfy.sh/{topic}",
        data=message.encode(),
        headers={"Title": "Kusama tickets open!", "Priority": "urgent", "Tags": "art", "Click": BOOK},
    )
    urllib.request.urlopen(req, timeout=20)


if __name__ == "__main__":
    if datetime.date.today() > LAST_DAY:
        print("Last target day passed; nothing to watch.")
        sys.exit(10)
    end = time.time() + RUN_SECONDS
    while time.time() < end:
        try:
            days = open_days()
        except Exception as e:
            print(f"error: {e}", flush=True)
            days = []
        if days:
            msg = f"Tickets open on {', '.join(d + '.11' for d in days)} (want 13.11 15:00 first). Book now: {BOOK}"
            print(msg, flush=True)
            notify(msg)
            sys.exit(10)
        time.sleep(INTERVAL)
    print("Still sold out.")
