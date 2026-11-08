"""Check Yayoi Kusama Museum tickets for 12-15 Nov 2026 every 15 s for ~4.5 min.

Alerts once each time a target day goes from sold out to available, and keeps
watching. LAST_OPEN carries the days already open from the previous run.
Exits with code 10 once the last target day has passed.
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
    return {d for d in TARGET_DAYS if d in available}


def notify(message):
    topic = os.environ["NTFY_TOPIC"]
    req = urllib.request.Request(
        f"https://ntfy.sh/{topic}",
        data=message.encode(),
        headers={"Title": "Kusama tickets open!", "Priority": "urgent", "Tags": "art", "Click": BOOK},
    )
    urllib.request.urlopen(req, timeout=20)


def save_state(open_now):
    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        with open(out, "a") as f:
            f.write(f"state={','.join(sorted(open_now, key=int)) or 'none'}\n")


if __name__ == "__main__":
    if datetime.date.today() > LAST_DAY:
        print("Last target day passed; nothing to watch.")
        sys.exit(10)
    last = {d for d in os.environ.get("LAST_OPEN", "").split(",") if d and d != "none"}
    end = time.time() + RUN_SECONDS
    while time.time() < end:
        try:
            open_now = open_days()
        except Exception as e:
            print(f"error: {e}", flush=True)
            open_now = last
        new = open_now - last
        if new:
            days = ", ".join(d + ".11" for d in sorted(new, key=int))
            msg = f"Tickets open on {days} (want 13.11 15:00 first). Book now: {BOOK}"
            print(msg, flush=True)
            try:
                notify(msg)
            except Exception as e:
                print(f"notify failed: {e}", flush=True)
                open_now = open_now - new  # retry the alert next check
        last = open_now
        time.sleep(INTERVAL)
    save_state(last)
    print(f"Open at end of run: {sorted(last, key=int) or 'none'}")
